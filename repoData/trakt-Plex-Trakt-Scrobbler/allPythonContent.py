__FILENAME__ = cache
from core.eventing import EventHandler
from core.logger import Logger


log = Logger('core.cache')


class CacheItem(object):
    def __init__(self):
        self.invalidated = False
        self.data = None


class Cache(object):
    def __init__(self, key):
        self.key = key
        self.data_store = {}

        self.on_refresh = EventHandler('%s.on_refresh' % key)

    def exists(self, key):
        return self.is_valid(key)

    def get(self, key, default=None, refresh=False, create=True):
        if not self.is_valid(key):
            # Refresh and return data if successful
            if refresh and self.invalidate(key, refresh, create):
                return self.data_store[key].data

            return default

        return self.data_store[key].data

    def update(self, key, data):
        if key not in self.data_store:
            self.data_store[key] = CacheItem()

        self.data_store[key].data = data
        self.data_store[key].invalidated = False

    def is_valid(self, key):
        if key not in self.data_store:
            return False

        return not self.data_store[key].invalidated

    def invalidate(self, key, refresh=False, create=False):
        if key not in self.data_store:
            if not create:
                return False

            self.data_store[key] = CacheItem()

        self.data_store[key].invalidated = True

        return self.refresh(key) if refresh else True

    def refresh(self, key):
        data = self.on_refresh.fire(key, single=True)
        if not data:
            return False

        self.update(key, data)

        return True

    def remove(self, key):
        if key not in self.data_store:
            return

        self.data_store.pop(key)

########NEW FILE########
__FILENAME__ = configuration
from core.helpers import try_convert
from core.logger import Logger


log = Logger('core.configuration')

MATCHER_MAP = {
    'Plex':             'plex',
    'Plex Extended':    'plex_extended'
}

SYNC_TASK_MAP = {
    'Disabled':                     [],
    'Synchronize (Pull + Push)':    ['pull', 'push'],
    'Pull':                         ['pull'],
    'Push':                         ['push']
}


class ConfigurationProcessor(object):
    def __init__(self):
        self.preferences = None

    def run(self, preferences):
        self.preferences = preferences

        for key in Configuration.keys:
            value = Prefs[Configuration.keys_map.get(key, key)]

            # Transform value if method is available
            if hasattr(self, key):
                value = getattr(self, key)(value)

            if value is not None:
                preferences[key] = value
            else:
                preferences[key] = Configuration.defaults.get(key)
                log.warn('Invalid value specified for option "%s", using default value: %s', key, preferences[key])

    def matcher(self, value):
        return MATCHER_MAP.get(value)

    def scrobble(self, value):
        return value and self.preferences['valid']

    def scrobble_percentage(self, value):
        value = try_convert(value, int)

        if value is None:
            return None

        if 0 <= value <= 100:
            return value

        return None

    def sync_run_library(self, value):
        return value and self.preferences['valid']

    def sync_collection(self, value):
        return SYNC_TASK_MAP.get(value)

    def sync_ratings(self, value):
        return SYNC_TASK_MAP.get(value)

    def sync_watched(self, value):
        return SYNC_TASK_MAP.get(value)


class Configuration(object):
    keys = [
        'activity_mode',
        'matcher',
        'scrobble',
        'scrobble_percentage',
        'sync_run_library',
        'sync_collection',
        'sync_ratings',
        'sync_watched'
    ]

    keys_map = {
        'scrobble': 'start_scrobble'
    }

    defaults = {
        'scrobble_percentage': 80
    }

    processor = ConfigurationProcessor()

    @classmethod
    def process(cls, preferences):
        cls.processor.run(preferences)

########NEW FILE########
__FILENAME__ = eventing
from core.helpers import join_attributes
from core.logger import Logger
import traceback

# Keys of events that shouldn't be logged
SILENT_FIRE = [
    'sync.get_cache_id'
]

log = Logger('core.eventing')


class EventHandler(object):
    def __init__(self, key=None):
        self.key = key

        self.handlers = []

    def subscribe(self, handler):
        self.handlers.append(handler)
        return self

    def unsubscribe(self, handler):
        self.handlers.remove(handler)
        return self

    def fire(self, *args, **kwargs):
        single = kwargs.pop('single', False)

        results = []

        for handler in self.handlers:
            try:
                results.append(handler(*args, **kwargs))
            except Exception, e:
                log.warn(
                    'Exception in handler for event with key "%s", (%s) %s: %s',
                    self.key,
                    type(e),
                    e,
                    traceback.format_exc()
                )

        if single:
            return results[0] if results else None

        return results


class EventManager(object):
    events = {}

    @classmethod
    def ensure_exists(cls, key):
        if key in cls.events:
            return

        cls.events[key] = EventHandler(key)
        log.trace('Created event with key "%s"', key)

    @classmethod
    def subscribe(cls, key, handler):
        cls.ensure_exists(key)
        cls.events[key].subscribe(handler)

    @classmethod
    def unsubscribe(cls, key, handler):
        if key not in cls.events:
            return False

        cls.events[key].unsubscribe(handler)

        # Remove event if it doesn't have any handlers now
        if len(cls.events[key].handlers) < 1:
            cls.events.pop(key)

        return True

    @classmethod
    def fire(cls, key, *args, **kwargs):
        if key not in SILENT_FIRE:
            attributes = join_attributes(args=args, kwargs=kwargs)
            log.trace("fire '%s'%s", key, (' [%s]' % attributes) if attributes else '')

        cls.ensure_exists(key)
        return cls.events[key].fire(*args, **kwargs)

########NEW FILE########
__FILENAME__ = header
from core.plugin import PLUGIN_VERSION, PLUGIN_NAME
import sys


class Header(object):
    @staticmethod
    def line(line):
        Log.Info('| ' + str(line))

    @staticmethod
    def separator(ch):
        Log.Info(ch * 50)

    @classmethod
    def show(cls, main):
        cls.separator('=')

        cls.line(PLUGIN_NAME)
        cls.line('https://github.com/trakt/Plex-Trakt-Scrobbler')
        cls.separator('-')

        cls.print_version(main)
        cls.separator('-')

        if Dict['developer']:
            cls.line('Developer Mode: Enabled')
            cls.separator('-')

        [cls.line(module_name) for module_name in cls.get_module_names()]
        cls.separator('=')

    @classmethod
    def print_version(cls, main):
        cls.line('Current Version: v%s' % PLUGIN_VERSION)

        #update_available = main.update_checker.update_available
        #update_detail = main.update_checker.update_detail
        #
        #if update_available is None:
        #    cls.line('Update Check: unable to check for updates')
        #elif update_available:
        #    cls.line('Update Check: %s is available' % update_detail['name'])
        #else:
        #    cls.line('Update Check: up to date')

    @staticmethod
    def get_module_names():
        return sorted([
            module_name for (module_name, module) in sys.modules.items()
            if getattr(type(module), '__name__') == 'RestrictedModule'
        ])

########NEW FILE########
__FILENAME__ = helpers
import inspect
import re
import sys
import threading
import time
import unicodedata


PY25 = sys.version_info[0] == 2 and sys.version_info[1] == 5


def try_convert(value, value_type, default=None):
    try:
        return value_type(value)
    except ValueError:
        return default
    except TypeError:
        return default


def add_attribute(target, source, key, value_type=str, func=None, target_key=None):
    if target_key is None:
        target_key = key

    value = try_convert(source.get(key, None), value_type)

    if value:
        target[target_key] = func(value) if func else value


def merge(a, b):
    a.update(b)
    return a


def all(items):
    for item in items:
        if not item:
            return False
    return True


def json_import():
    try:
        import simplejson as json

        Log.Info("Using 'simplejson' module for JSON serialization")
        return json, 'json'
    except ImportError:
        pass

    # Try fallback to 'json' module
    try:
        import json

        Log.Info("Using 'json' module for JSON serialization")
        return json, 'json'
    except ImportError:
        pass

    # Try fallback to 'demjson' module
    try:
        import demjson

        Log.Info("Using 'demjson' module for JSON serialization")
        return demjson, 'demjson'
    except ImportError:
        Log.Warn("Unable to find json module for serialization")
        raise Exception("Unable to find json module for serialization")

# Import json serialization module
JSON, JSON_MODULE = json_import()


# JSON serialization wrappers to simplejson/json or demjson
def json_decode(s):
    if JSON_MODULE == 'json':
        return JSON.loads(s)

    if JSON_MODULE == 'demjson':
        return JSON.decode(s)

    raise NotImplementedError()


def json_encode(obj):
    if JSON_MODULE == 'json':
        return JSON.dumps(obj)

    if JSON_MODULE == 'demjson':
        return JSON.encode(obj)

    raise NotImplementedError()


def str_format(s, *args, **kwargs):
    """Return a formatted version of S, using substitutions from args and kwargs.

    (Roughly matches the functionality of str.format but ensures compatibility with Python 2.5)
    """

    args = list(args)

    x = 0
    while x < len(s):
        # Skip non-start token characters
        if s[x] != '{':
            x += 1
            continue

        end_pos = s.find('}', x)

        # If end character can't be found, move to next character
        if end_pos == -1:
            x += 1
            continue

        name = s[x + 1:end_pos]

        # Ensure token name is alpha numeric
        if not name.isalnum():
            x += 1
            continue

        # Try find value for token
        value = args.pop(0) if args else kwargs.get(name)

        if value:
            value = str(value)

            # Replace token with value
            s = s[:x] + value + s[end_pos + 1:]

            # Update current position
            x = x + len(value) - 1

        x += 1

    return s


def str_pad(s, length, align='left', pad_char=' ', trim=False):
    if not s:
        return s

    s = str(s)

    if len(s) == length:
        return s
    elif len(s) > length and not trim:
        return s

    if align == 'left':
        if len(s) > length:
            return s[:length]
        else:
            return s + (pad_char * (length - len(s)))
    elif align == 'right':
        if len(s) > length:
            return s[len(s) - length:]
        else:
            return (pad_char * (length - len(s))) + s
    else:
        raise ValueError("Unknown align type, expected either 'left' or 'right'")


def pad_title(value):
    """Pad a title to 30 characters to force the 'details' view."""
    return str_pad(value, 30, pad_char=' ')


def total_seconds(span):
    return (span.microseconds + (span.seconds + span.days * 24 * 3600) * 1e6) / 1e6


def sum(values):
    result = 0

    for x in values:
        result = result + x

    return result


def timestamp():
    return int(time.time())


# <bound method type.start of <class 'Scrobbler'>>
RE_BOUND_METHOD = Regex(r"<bound method (type\.)?(?P<name>.*?) of <(class '(?P<class>.*?)')?")


def get_func_name(obj):
    if inspect.ismethod(obj):
        match = RE_BOUND_METHOD.match(repr(obj))

        if match:
            cls = match.group('class')
            if not cls:
                return match.group('name')

            return '%s.%s' % (
                match.group('class'),
                match.group('name')
            )

    return None


def spawn(func, *args, **kwargs):
    thread_name = kwargs.pop('thread_name', None) or get_func_name(func)

    thread = threading.Thread(target=func, name=thread_name, args=args, kwargs=kwargs)

    thread.start()

    Log.Debug("Spawned thread with name '%s'" % thread_name)
    return thread


def schedule(func, seconds, *args, **kwargs):
    def schedule_sleep():
        time.sleep(seconds)
        func(*args, **kwargs)

    spawn(schedule_sleep)


def build_repr(obj, keys):
    key_part = ', '.join([
        ('%s: %s' % (key, repr(getattr(obj, key))))
        for key in keys
    ])

    cls = getattr(obj, '__class__')

    return '<%s %s>' % (getattr(cls, '__name__'), key_part)


def plural(value):
    if type(value) is list:
        value = len(value)

    if value == 1:
        return ''

    return 's'


def get_pref(key, default=None):
    if Dict['preferences'] and key in Dict['preferences']:
        return Dict['preferences'][key]

    return Prefs[key] or default


def join_attributes(**kwargs):
    fragments = [
        (('%s: %s' % (key, value)) if value else None)
        for (key, value) in kwargs.items()
    ]

    return ', '.join([x for x in fragments if x])


def get_filter(key):
    value = get_pref(key)
    if not value:
        return None

    value = value.strip()

    # Allow all if wildcard (*) or blank
    if not value or value == '*':
        return None

    # Split, strip and lower-case comma-separated values
    return [normalize(x) for x in value.split(',')]


def normalize(text):
    # Normalize unicode characters
    if type(text) is unicode:
        text = unicodedata.normalize('NFKD', text)

    # Ensure text is ASCII, ignore unknown characters
    text = text.encode('ascii', 'ignore')

    # Remove special characters
    text = re.sub('[^A-Za-z0-9\s]+', '', text)

    # Merge duplicate spaces
    text = ' '.join(text.split())

    # Convert to lower-case
    return text.lower()

########NEW FILE########
__FILENAME__ = logger
ENTRY_FORMAT = '[%s] %s'


class Logger(object):
    def __init__(self, tag):
        self.tag = tag

    def write(self, func, message, *args, **kwargs):
        tag = self.tag

        if 'tag' in kwargs:
            tag = kwargs.pop('tag')

        try:
            if args:
                message = str(message) % args

            func(ENTRY_FORMAT % (tag, message))
        except Exception, ex:
            self.error(
                'Error writing log entry (%s) %s [message: %s, args: %s]',
                type(ex).__name__, ex.message,
                repr(message), args
            )

    def trace(self, message, *args, **kwargs):
        if not Prefs['logging_tracing']:
            return

        self.write(Log.Debug, message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self.write(Log.Debug, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self.write(Log.Info, message, *args, **kwargs)

    def warn(self, message, *args, **kwargs):
        self.write(Log.Warn, message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self.write(Log.Error, message, *args, **kwargs)

########NEW FILE########
__FILENAME__ = method_manager
from core.helpers import spawn, plural
from core.logger import Logger
from core.plugin import ACTIVITY_MODE
import threading
import traceback

log = Logger('core.method_manager')


class Method(object):
    name = None

    def __init__(self, threaded=True):
        if threaded:
            self.thread = threading.Thread(target=self.run_wrapper, name=self.get_name())
            self.running = False

        self.threaded = threaded

    def get_name(self):
        return self.name

    @classmethod
    def test(cls):
        raise NotImplementedError()

    def start(self):
        if not self.threaded or self.running:
            return False

        self.thread.start()
        self.running = True

    def run_wrapper(self):
        # Wrap run method to catch any exceptions
        try:
            self.run()
        except Exception, ex:
            log.error(traceback.format_exc())

    def run(self):
        raise NotImplementedError()


class Manager(object):
    tag = None

    available = []
    enabled = []

    @classmethod
    def register(cls, method, weight=None):
        item = (weight, method)

        # weight = None, highest priority
        if weight is None:
            cls.available.insert(0, item)
            return

        # insert in DESC order
        for x in xrange(len(cls.available)):
            w, _ = cls.available[x]

            if w is not None and w < weight:
                cls.available.insert(x, item)
                return

        # otherwise append
        cls.available.append(item)

    @classmethod
    def filter_available(cls):
        allowed = ACTIVITY_MODE.get(Prefs['activity_mode'])

        if not allowed:
            return

        cls.available = [
            (k, v) for (k, v) in cls.available
            if v.name in allowed
        ]

    @classmethod
    def start(cls, blocking=False):
        if not blocking:
            spawn(cls.start, blocking=True)
            return

        cls.filter_available()

        # Test methods until an available method is found
        for weight, method in cls.available:
            if weight is None:
                cls.start_method(method)
            elif method.test():
                cls.start_method(method)
                break
            else:
                log.info("method '%s' not available" % method.name, tag=cls.tag)

        log.info(
            'Finished starting %s method%s: %s',
            len(cls.enabled), plural(cls.enabled),
            ', '.join([("'%s'" % m.name) for m in cls.enabled]),

            tag=cls.tag
        )

    @classmethod
    def start_method(cls, method):
        obj = method()
        cls.enabled.append(obj)

        spawn(obj.start)

########NEW FILE########
__FILENAME__ = migrator
from core.helpers import all
from core.logger import Logger
from core.plugin import PLUGIN_VERSION_BASE
from lxml import etree
import shutil
import os

log = Logger('core.migrator')


class Migrator(object):
    migrations = []

    @classmethod
    def register(cls, migration):
        cls.migrations.append(migration())

    @classmethod
    def run(cls):
        for migration in cls.migrations:
            log.debug('Running migration %s', migration)
            migration.run()


class Migration(object):
    @property
    def code_path(self):
        return Core.code_path

    @property
    def plex_path(self):
        return os.path.abspath(os.path.join(self.code_path, '..', '..', '..', '..'))

    @property
    def preferences_path(self):
        return os.path.join(self.plex_path, 'Plug-in Support', 'Preferences', 'com.plexapp.plugins.trakttv.xml')

    def get_preferences(self):
        if not os.path.exists(self.preferences_path):
            log.warn('Unable to find preferences file at "%s", unable to run migration', self.preferences_path)
            return {}

        data = Core.storage.load(self.preferences_path)
        doc = etree.fromstring(data)

        return dict([(elem.tag, elem.text) for elem in doc])

    def set_preferences(self, changes):
        if not os.path.exists(self.preferences_path):
            log.warn('Unable to find preferences file at "%s", unable to run migration', self.preferences_path)
            return False

        data = Core.storage.load(self.preferences_path)
        doc = etree.fromstring(data)

        for key, value in changes.items():
            elem = doc.find(key)

            # Ensure node exists
            if elem is None:
                elem = etree.SubElement(doc, key)

            # Update node value, ensure it is a string
            elem.text = str(value)

            log.trace('Updated preference with key "%s" to value %s', key, repr(value))

        # Write back new preferences
        Core.storage.save(self.preferences_path, etree.tostring(doc, pretty_print=True))

    @staticmethod
    def delete_file(path, conditions=None):
        if not all([c(path) for c in conditions]):
            return False

        os.remove(path)
        return True

    @staticmethod
    def delete_directory(path, conditions=None):
        if not all([c(path) for c in conditions]):
            return False

        shutil.rmtree(path)
        return True


class Clean(Migration):
    tasks_upgrade = [
        (
            'delete_file', [
                'data/dict_object.py',
                'plex/media_server.py',
                'sync.py'
            ], os.path.isfile
        )
    ]

    def run(self):
        if PLUGIN_VERSION_BASE >= (0, 8):
            self.upgrade()

    def upgrade(self):
        self.execute(self.tasks_upgrade, 'upgrade')

    def execute(self, tasks, name):
        for action, paths, conditions in tasks:
            if type(paths) is not list:
                paths = [paths]

            if type(conditions) is not list:
                conditions = [conditions]

            if not hasattr(self, action):
                log.warn('Unknown migration action "%s"', action)
                continue

            m = getattr(self, action)

            for path in paths:
                log.debug('(%s) %s: "%s"', name, action, path)

                if m(os.path.join(self.code_path, path), conditions):
                    log.debug('(%s) %s: "%s" - finished', name, action, path)


class ForceLegacy(Migration):
    """Migrates the 'force_legacy' option to the 'activity_mode' option."""

    def run(self):
        self.upgrade()

    def upgrade(self):
        if not os.path.exists(self.preferences_path):
            log.warn('Unable to find preferences file at "%s", unable to run migration', self.preferences_path)
            return

        preferences = self.get_preferences()

        # Read 'force_legacy' option from raw preferences
        force_legacy = preferences.get('force_legacy')

        if force_legacy is None:
            return

        force_legacy = force_legacy.lower() == "true"

        if not force_legacy:
            return

        # Read 'activity_mode' option from raw preferences
        activity_mode = preferences.get('activity_mode')

        # Activity mode has already been set, not changing it
        if activity_mode is not None:
            return

        self.set_preferences({
            'activity_mode': '1'
        })


class SelectiveSync(Migration):
    """Migrates the syncing task bool options to selective synchronize/push/pull enums"""

    option_keys = [
        'sync_watched',
        'sync_ratings',
        'sync_collection'
    ]

    value_map = {
        'false': '0',
        'true': '1',
    }

    def run(self):
        self.upgrade()

    def upgrade(self):
        preferences = self.get_preferences()

        # Filter to only relative preferences
        preferences = dict([
            (key, value)
            for key, value in preferences.items()
            if key in self.option_keys
        ])

        changes = {}

        for key, value in preferences.items():
            if value not in self.value_map:
                continue

            changes[key] = self.value_map[value]

        if not changes:
            return

        log.debug('Updating preferences with changes: %s', changes)
        self.set_preferences(changes)


Migrator.register(Clean)
Migrator.register(ForceLegacy)
Migrator.register(SelectiveSync)
Migrator.run()

########NEW FILE########
__FILENAME__ = model
class DictModel(object):
    root_key = None

    def __init__(self, key):
        self.key = key

    def save(self):
        if not self.root_key:
            raise ValueError()

        Dict[self.root_key][self.key] = self.to_json()

    @classmethod
    def all(cls):
        if not cls.root_key or cls.root_key not in Dict:
            return []

        items = []

        for key, value in Dict[cls.root_key].items():
            items.append((key, cls.from_json(value)))

        return items

    @classmethod
    def load(cls, key):
        if not cls.root_key:
            raise ValueError()

        if cls.root_key not in Dict:
            Dict[cls.root_key] = {}

        if key not in Dict[cls.root_key]:
            return None

        return cls.from_json(Dict[cls.root_key][key])

    def delete(self):
        if not self.root_key:
            raise ValueError()

        if self.key in Dict[self.root_key]:
            del Dict[self.root_key][self.key]


    @classmethod
    def object_from_json(cls, key, value):
        raise NotImplementedError()

    @classmethod
    def from_json(cls, data):
        obj = cls()

        for key, value in data.items():
            #Log('[DataObject.from_json] "%s" = %s' % (key, value))

            if not hasattr(obj, key):
                continue

            if isinstance(value, dict):
                value = cls.object_from_json(key, value)

            setattr(obj, key, value)

        return obj

    def to_json(self):
        data = {}

        items = [
            (key, value)
            for (key, value) in getattr(self, '__dict__').items()
            if not key.startswith('_')
        ]

        for key, value in items:
            if isinstance(value, DictModel):
                value = value.to_json()

            data[key] = value

        return data

########NEW FILE########
__FILENAME__ = network
from core.cache import Cache
from core.helpers import json_decode, json_encode, PY25
from core.logger import Logger
from lxml import etree
import urllib2
import socket
import time

HTTP_RETRY_CODES = [408, 500, (502, 504), 522, 524, (598, 599)]

log = Logger('core.network')

cache = Cache('network')


def request(url, response_type='text', data=None, data_type='application/octet-stream', retry=False,
            timeout=None, max_retries=3, retry_sleep=5, method=None, cache_id=None, **kwargs):
    """Send an HTTP Request

    :param url: Request url
    :type url: str

    :param response_type: Expected response data type
    :type response_type: str

    :param data: Data to send in the request
    :type data: str or dict

    :param data_type: Type of data to send in the request
    :type data_type: str

    :param retry: Should the request be retried on errors?
    :type retry: bool

    :param timeout: Request timeout seconds
    :type timeout: int

    :param max_retries: Number of retries before we give up on the request
    :type max_retries: int

    :param retry_sleep: Number of seconds to sleep for between requests
    :type retry_sleep: int

    :param method: HTTP method to use for this request, None = default method determined by urllib2
    :type method: str or None

    :param cache_id: Cached response can be returned if it matches this identifier
    :type cache_id: str

    :rtype: Response
    """
    req = urllib2.Request(url)

    # Set request method (a dirty hack, but urllib...)
    if method:
        req.get_method = lambda: method

    # Add request body
    if data:
        # Convert request data
        if data_type == 'json' and not isinstance(data, basestring):
            data = json_encode(data)

        if not isinstance(data, basestring):
            raise ValueError("Request data is not in a valid format, type(data) = %s, data_type = \"%s\"" % (
                type(data), data_type)
            )

        req.data = data
        req.add_header('Content-Length', len(data))

        if data_type == 'json':
            req.add_header('Content-Type', 'application/json')
        else:
            req.add_header('Content-Type', data_type)

    # (Python 2.5 urlopen doesn't support timeouts)
    if timeout and not PY25:
        kwargs['timeout'] = timeout

    return internal_retry(
        req,

        retry=retry,
        max_retries=max_retries,
        retry_sleep=retry_sleep,

        response_type=response_type,
        cache_id=cache_id,
        **kwargs
    )


def internal_log_request(req, response_type, cache_id):
    method = req.get_method()
    data = req.data

    debug_values = [
        method if method != 'GET' else None,
        ("len(data): %s" % (len(data))) if data else '',
        ('cache_id: %s' % cache_id) if cache_id else None
    ]

    # Filter empty values
    debug_values = [x for x in debug_values if x]

    log.debug("Requesting '%s' (%s) %s" % (
        req.get_full_url(),
        response_type,

        ('[%s]' % ', '.join(debug_values)) if len(debug_values) else ''
    ))


def internal_retry(req, retry=False, max_retries=3, retry_sleep=5, **kwargs):
    if not retry:
        return internal_request(req, **kwargs)

    raise_exceptions = kwargs.get('raise_exceptions', False)

    kwargs['raise_exceptions'] = True

    last_exception = None
    response = None
    retry_num = 0

    while response is None and retry_num < max_retries:
        if retry_num > 0:
            sleep_time = retry_sleep * retry_num

            log.debug('Waiting %ss before retrying request' % sleep_time)
            time.sleep(sleep_time)

            log.debug('Retrying request, try #%s' % retry_num)

        try:
            response = internal_request(req, **kwargs)
        except NetworkError, e:
            last_exception = e

            log.debug('Request returned a network error: (%s) %s' % (e.code, e))

            # If this is possibly a client error, stop retrying and just return
            if not should_retry(e.code):
                log.debug('Request error code %s is possibly client related, not retrying the request', e.code)
                break

        except RequestError, e:
            last_exception = e

            log.debug('Request returned exception: %s' % e)
            response = None

        retry_num += 1

    if response is None and raise_exceptions:
        raise last_exception or RequestError('Unknown network error')

    return response


def internal_request(req, response_type='text', raise_exceptions=False, default=None, cache_id=None, quiet=False, **kwargs):
    data = None

    if cache_id is not None:
        data = cache.get((req.get_full_url(), cache_id))

    try:
        if data is None:
            if not quiet:
                internal_log_request(req, response_type, cache_id)

            data = urllib2.urlopen(req, **kwargs).read()

            if cache_id is not None:
                cache.update((req.get_full_url(), cache_id), data)

        return Response.from_data(response_type, data)
    except RequestError, e:
        ex = e
    except Exception, e:
        ex = NetworkError.from_exception(e, response_type=response_type)

    if raise_exceptions:
        raise ex
    else:
        log.warn('Network request raised exception: %s' % ex)

    return default


def should_retry(error_code):
    # If there is no error code, assume we should retry
    if error_code is None:
        return True

    for retry_code in HTTP_RETRY_CODES:
        if type(retry_code) is tuple and len(retry_code) == 2:
            if retry_code[0] <= error_code <= retry_code[1]:
                return True
        elif type(retry_code) is int:
            if retry_code == error_code:
                return True
        else:
            raise ValueError("Invalid retry_code specified: %s" % retry_code)

    return False


class Response(object):
    def __init__(self, data):
        self.data = data

    @classmethod
    def from_data(cls, response_type, data):
        return Response(
            cls.parse_data(response_type, data)
        )

    @classmethod
    def parse_data(cls, response_type, data):
        if response_type == 'text':
            return data
        elif response_type == 'json':
            return cls.parse_json(data)
        elif response_type == 'xml':
            return cls.parse_xml(data)
        else:
            raise RequestError("Unknown response type provided")

    @classmethod
    def parse_json(cls, data):
        try:
            return json_decode(data)
        except Exception, e:
            raise ParseError.from_exception(e)

    @classmethod
    def parse_xml(cls, data):
        try:
            return etree.fromstring(data)
        except Exception, e:
            raise ParseError.from_exception(e)


class RequestError(Exception):
    def __init__(self, message, inner_exception=None):
        self.message = message
        self.inner_exception = inner_exception

    def __str__(self):
        ex_class = getattr(self.inner_exception, '__class__') if self.inner_exception else None

        if self.inner_exception:
            ex_class = getattr(ex_class, '__name__')

        return '<NetworkError%s "%s">' % (
            (' (%s)' % ex_class) if ex_class else '',
            self.message
        )


class NetworkError(RequestError):
    def __init__(self, message, code, inner_exception=None, data=None):
        super(NetworkError, self).__init__(message, inner_exception)

        self.code = code
        self.data = data

    @classmethod
    def from_exception(cls, e, response_type=None):
        code = None
        data = None

        if type(e) is urllib2.HTTPError:
            code = e.code
            data = e.read()

            # Parse data if response_type has been provided
            if data and response_type:
                data = Response.parse_data(response_type, data)

        if type(e) is socket.timeout:
            code = 408

        return NetworkError(
            e.message or str(e), code,
            inner_exception=e, data=data
        )


class ParseError(RequestError):
    @classmethod
    def from_exception(cls, e):
        return ParseError(e.message or str(e), e)

########NEW FILE########
__FILENAME__ = numeric
def ema(value, last, smoothing=0.0025):
    return smoothing * value + (1 - smoothing) * last

########NEW FILE########
__FILENAME__ = plugin
PLUGIN_NAME = 'Plex-Trakt-Scrobbler'
PLUGIN_IDENTIFIER = 'com.plexapp.plugins.trakttv'

PLUGIN_VERSION_BASE = (0, 8, 2, 7)
PLUGIN_VERSION_BRANCH = 'master'

PLUGIN_VERSION = ''.join([
    '.'.join([str(x) for x in PLUGIN_VERSION_BASE]),
    '-' + PLUGIN_VERSION_BRANCH if PLUGIN_VERSION_BRANCH else ''
])

NAME = L('Title')
ART = 'art-default.jpg'
ICON = 'icon-default.png'

ACTIVITY_MODE = {
    'Automatic':            None,
    'Logging (Legacy)':     ['LoggingActivity', 'LoggingScrobbler'],
    'WebSocket (PlexPass)': ['WebSocketActivity', 'WebSocketScrobbler']
}
########NEW FILE########
__FILENAME__ = task
from core.helpers import spawn
from core.logger import Logger
from threading import Lock
import traceback

log = Logger('core.task')


class CancelException(Exception):
    pass


class Task(object):
    def __init__(self, target, *args, **kwargs):
        self.target = target
        self.args = args
        self.kwargs = kwargs

        self.exception = None
        self.result = None

        self.complete = False
        self.started = False
        self.lock = Lock()

    def spawn(self, name):
        spawn(self.run, thread_name=name)

    def wait(self):
        if not self.started:
            return False

        if not self.complete:
            self.lock.acquire()

        if self.exception:
            raise self.exception

        return self.result

    def run(self):
        if self.started:
            return

        self.lock.acquire()
        self.started = True

        try:
            self.result = self.target(*self.args, **self.kwargs)
        except CancelException, e:
            self.exception = e

            log.debug('Task cancelled')
        except Exception, e:
            self.exception = e

            log.warn('Exception raised in triggered function %s (%s) %s: %s' % (
                self.target, type(e), e, traceback.format_exc()
            ))

        self.complete = True
        self.lock.release()

########NEW FILE########
__FILENAME__ = trakt
from core.logger import Logger
from core.network import request, RequestError, NetworkError
from core.plugin import PLUGIN_VERSION
from core.helpers import all, total_seconds
from core.trakt_objects import TraktShow, TraktEpisode, TraktMovie
from datetime import datetime


log = Logger('core.trakt')

TRAKT_URL = 'http://api.trakt.tv/%s/ba5aa61249c02dc5406232da20f6e768f3c82b28%s'


IDENTIFIERS = {
    'movies': {
        ('imdb_id', 'imdb'),
        ('tmdb_id', 'themoviedb')
    },
    'shows': [
        ('tvdb_id', 'thetvdb'),
        ('imdb_id', 'imdb'),
        ('tvrage_id', 'tvrage')
    ]
}


class Trakt(object):
    @classmethod
    def request(cls, action, values=None, params=None, authenticate=False, retry=True, max_retries=3, cache_id=None, timeout=None):
        if params is None:
            params = []
        elif isinstance(params, basestring):
            params = [params]

        params = [x for x in params if x]

        data_url = TRAKT_URL % (
            action,
            ('/' + '/'.join(params)) if params else ''
        )

        if values is None:
            values = {}

        if authenticate:
            if not Prefs['username'] or not Prefs['password']:
                return {'success': False, 'message': 'Missing username or password'}

            values['username'] = Prefs['username']
            values['password'] = Hash.SHA1(Prefs['password'])

        values['plugin_version'] = PLUGIN_VERSION
        values['media_center_version'] = Dict['server_version']

        try:
            kwargs = {
                'retry': retry,
                'max_retries': max_retries,
                'cache_id': cache_id,
                'timeout': timeout,

                'raise_exceptions': True
            }

            if values is not None:
                kwargs['data'] = values
                kwargs['data_type'] = 'json'

            response = request(data_url, 'json', **kwargs)
        except NetworkError, e:
            log.warn('Network error: (%s) message: %s data: %s' % (e, repr(e.message), repr(e.data)))
            return cls.parse_response(e)
        except RequestError, e:
            log.warn('Request error: (%s) %s' % (e, e.message))
            return {'success': False, 'exception': e, 'message': e.message}

        return cls.parse_response(response)

    @classmethod
    def parse_response(cls, response):
        if isinstance(response, RequestError) and response.data is None:
            return {'success': False, 'message': response.message}

        if response is None:
            return {'success': False, 'message': 'Unknown Failure'}

        # Return on successful results without status detail
        if type(response.data) is not dict or 'status' not in response.data:
            return {'success': True, 'data': response.data}

        status = response.data.get('status')
        result = response.data

        result.update({'success': status == 'success'})

        if status == 'success':
            result.setdefault('message', 'Unknown success')
        else:
            result.setdefault('message', response.data.get('error'))

        # Log result for debugging
        if not result.get('success'):
            log.warn('Request failure: %s' % (
                result.get('message', 'Unknown Result')
            ))

        return result

    class Account(object):
        @staticmethod
        def test():
            return Trakt.request('account/test', authenticate=True)

    class User(object):
        @classmethod
        def get_merged(cls, media, watched=True, ratings=False, collected=False, extended=None, retry=True, cache_id=None):
            start = datetime.utcnow()

            # Merge data
            items = {}

            params = {
                'authenticate': True,
                'retry': retry,
                'cache_id': cache_id
            }

            # Merge watched library
            if watched and not Trakt.merge_watched(items, media, extended, **params):
                log.warn('Failed to merge watched library')
                return None

            # Merge ratings
            if ratings and not Trakt.merge_ratings(items, media, **params):
                log.warn('Failed to merge ratings')
                return None

            # Merge collected library
            if collected and not Trakt.merge_collected(items, media, extended, **params):
                log.warn('Failed to merge collected library')
                return None

            # Generate entries table with alternative keys
            table = items.copy()

            for key, item in table.items():
                # Skip first key (because it's the root_key)
                for alt_key in item.keys[1:]:
                    table[alt_key] = item

            # Calculate elapsed time
            elapsed = datetime.utcnow() - start

            log.debug(
                'get_merged returned dictionary with %s keys for %s items in %s seconds',
                len(table), len(items), total_seconds(elapsed)
            )

            return items, table

        @staticmethod
        def get_library(media, marked, extended=None, authenticate=False, retry=True, cache_id=None):
            return Trakt.request(
                'user/library/%s/%s.json' % (media, marked),
                params=[Prefs['username'], extended],

                authenticate=authenticate,
                retry=retry,
                cache_id=cache_id
            )

        @staticmethod
        def get_ratings(media, authenticate=False, retry=True, cache_id=None):
            return Trakt.request(
                'user/ratings/%s.json' % media,
                params=Prefs['username'],

                authenticate=authenticate,
                retry=retry,
                cache_id=cache_id
            )

    class Media(object):
        @staticmethod
        def action(media_type, action, retry=False, timeout=None, max_retries=3, **kwargs):
            if not all([x in kwargs for x in ['duration', 'progress', 'title']]):
                raise ValueError()

            # Retry scrobble requests as they are important (compared to watching requests)
            if action == 'scrobble':
                # Only change these values if they aren't already set
                retry = retry or True
                timeout = timeout or 3
                max_retries = 5

            return Trakt.request(
                media_type + '/' + action,
                kwargs,
                authenticate=True,

                retry=retry,
                max_retries=max_retries,
                timeout=timeout
            )

    @staticmethod
    def get_media_keys(media, item):
        if item is None:
            return None

        result = []

        for t_key, p_key in IDENTIFIERS[media]:
            result.append((p_key, str(item.get(t_key))))

        if not len(result):
            return None, []

        return result[0], result

    @classmethod
    def create_media(cls, media, keys, info, is_watched=None, is_collected=None):
        if media == 'shows':
            return TraktShow.create(keys, info, is_watched, is_collected)

        if media == 'movies':
            return TraktMovie.create(keys, info, is_watched, is_collected)

        raise ValueError('Unknown media type')

    @classmethod
    def merge_watched(cls, result, media, extended=None, **kwargs):
        watched = cls.User.get_library(
            media, 'watched',
            extended=extended,
            **kwargs
        ).get('data')

        if watched is None:
            log.warn('Unable to fetch watched library from trakt')
            return False

        # Fill with watched items in library
        for item in watched:
            root_key, keys = Trakt.get_media_keys(media, item)

            result[root_key] = Trakt.create_media(media, keys, item, is_watched=True)

        return True

    @classmethod
    def merge_ratings(cls, result, media, **kwargs):
        ratings = cls.User.get_ratings(
            media,
            **kwargs
        ).get('data')

        episode_ratings = None

        if media == 'shows':
            episode_ratings = cls.User.get_ratings(
                'episodes',
                **kwargs
            ).get('data')

        if ratings is None or (media == 'shows' and episode_ratings is None):
            log.warn('Unable to fetch ratings from trakt')
            return False

        # Merge ratings
        for item in ratings:
            root_key, keys = Trakt.get_media_keys(media, item)

            if root_key not in result:
                result[root_key] = Trakt.create_media(media, keys, item)
            else:
                result[root_key].fill(item)

        # Merge episode_ratings
        if media == 'shows':
            for item in episode_ratings:
                root_key, keys = Trakt.get_media_keys(media, item['show'])

                if root_key not in result:
                    result[root_key] = Trakt.create_media(media, keys, item['show'])

                episode = item['episode']
                episode_key = (episode['season'], episode['number'])

                if episode_key not in result[root_key].episodes:
                    result[root_key].episodes[episode_key] = TraktEpisode.create(episode['season'], episode['number'])

                result[root_key].episodes[episode_key].fill(item)

        return True


    @classmethod
    def merge_collected(cls, result, media, extended=None, **kwargs):
        collected = Trakt.User.get_library(
            media, 'collection',
            extended=extended,
            **kwargs
        ).get('data')

        if collected is None:
            log.warn('Unable to fetch collected library from trakt')
            return False

        # Merge ratings
        for item in collected:
            root_key, keys = Trakt.get_media_keys(media, item)

            if root_key not in result:
                result[root_key] = Trakt.create_media(media, keys, item, is_collected=True)
            else:
                result[root_key].fill(item, is_collected=True)

        return True

########NEW FILE########
__FILENAME__ = trakt_objects
from core.helpers import build_repr


PRIMARY_KEY = 'imdb'


class TraktMedia(object):
    def __init__(self, keys=None):
        self.keys = keys

        self.rating = None
        self.rating_advanced = None
        self.rating_timestamp = None

        self.is_watched = None
        self.is_collected = None
        self.is_local = None

    @property
    def pk(self):
        if not self.keys:
            return None

        for key, value in self.keys:
            if key == PRIMARY_KEY:
                return value

        return None

    def update(self, info, keys):
        for key in keys:
            if key not in info:
                continue

            if getattr(self, key) is not None:
                continue

            setattr(self, key, info[key])

    def update_states(self, is_watched=None, is_collected=None):
        if is_watched is not None:
            self.is_watched = is_watched

        if is_collected is not None:
            self.is_collected = is_collected

    def fill(self, info):
        self.update(info, ['rating', 'rating_advanced'])

        if 'rating' in info:
            self.rating_timestamp = info.get('inserted')

    @staticmethod
    def get_repr_keys():
        return ['keys', 'rating', 'rating_advanced', 'rating_timestamp', 'is_watched', 'is_collected', 'is_local']

    def __repr__(self):
        return build_repr(self, self.get_repr_keys() or [])

    def __str__(self):
        return self.__repr__()


class TraktShow(TraktMedia):
    def __init__(self, keys):
        super(TraktShow, self).__init__(keys)

        self.title = None
        self.year = None
        self.tvdb_id = None

        self.episodes = {}

    def to_info(self):
        return {
            'tvdb_id': self.tvdb_id,
            'title': self.title,
            'year': self.year
        }

    def fill(self, info, is_watched=None, is_collected=None):
        TraktMedia.fill(self, info)

        self.update(info, ['title', 'year', 'tvdb_id'])

        if 'seasons' in info:
            self.update_seasons(info['seasons'], is_watched, is_collected)

        return self

    def update_seasons(self, seasons, is_watched=None, is_collected=None):
        for season, episodes in [(x.get('season'), x.get('episodes')) for x in seasons]:
            # For each episode, create if doesn't exist, otherwise just update is_watched and is_collected
            for episode in episodes:
                key = season, episode

                if key not in self.episodes:
                    self.episodes[key] = TraktEpisode.create(season, episode, is_watched, is_collected)
                else:
                    self.episodes[key].update_states(is_watched, is_collected)

    @classmethod
    def create(cls, keys, info, is_watched=None, is_collected=None):
        show = cls(keys)
        return cls.fill(show, info, is_watched, is_collected)

    @staticmethod
    def get_repr_keys():
        return TraktMedia.get_repr_keys() + ['title', 'year', 'tvdb_id', 'episodes']


class TraktEpisode(TraktMedia):
    def __init__(self, season, number):
        super(TraktEpisode, self).__init__()

        self.season = season
        self.number = number

    @property
    def pk(self):
        return self.season, self.number

    def to_info(self):
        return {
            'season': self.season,
            'episode': self.number
        }

    @classmethod
    def create(cls, season, number, is_watched=None, is_collected=None):
        episode = cls(season, number)
        episode.update_states(is_watched, is_collected)

        return episode

    @staticmethod
    def get_repr_keys():
        return TraktMedia.get_repr_keys() + ['season', 'number']


class TraktMovie(TraktMedia):
    def __init__(self, keys):
        super(TraktMovie, self).__init__(keys)

        self.title = None
        self.year = None
        self.imdb_id = None

    def to_info(self):
        return {
            'title': self.title,
            'year': self.year,
            'imdb_id': self.imdb_id
        }

    def fill(self, info, is_watched=None, is_collected=None):
        TraktMedia.fill(self, info)

        self.update(info, ['title', 'year', 'imdb_id'])
        self.update_states(is_watched, is_collected)

        return self

    @classmethod
    def create(cls, keys, info, is_watched=None, is_collected=None):
        movie = cls(keys)
        movie.update_states(is_watched, is_collected)

        return cls.fill(movie, info)

    @staticmethod
    def get_repr_keys():
        return TraktMedia.get_repr_keys() + ['title', 'year', 'imdb_id']

########NEW FILE########
__FILENAME__ = update_checker
from core.network import request, RequestError
from core.plugin import PLUGIN_VERSION_BASE, PLUGIN_VERSION_BRANCH
from threading import Timer
import random


class UpdateChecker(object):
    # interval = 24 hours + random offset between 0 - 60 minutes
    interval = (24 * 60 * 60) + (random.randint(0, 60) * 60)

    server = 'http://pts.skipthe.net'

    def __init__(self):
        self.timer = None

        self.version = {
            'base': '.'.join([str(x) for x in PLUGIN_VERSION_BASE]),
            'branch': PLUGIN_VERSION_BRANCH
        }

        self.client_id = None

        self.update_available = None
        self.update_detail = None

        # Retrieve the saved client_id if one exists
        if 'client_id' in Dict:
            self.client_id = Dict['client_id']

    def run_once(self, first_run=True, async=False):
        if async:
            Thread.Create(self.run, first_run=first_run)
        else:
            self.run(first_run=first_run)

    def request(self, first_run=False):
        data = {
            'client_id': self.client_id,
            'version': self.version,
            'platform': Platform.OS.lower()
        }

        response = request(self.server + '/api/ping', 'json', data, data_type='json')
        if not response:
            return None

        return response.data

    def reset(self, available=None):
        self.update_available = available
        self.update_detail = None

    def run(self, first_run=False):
        if Dict['developer']:
            Log.Info('Developer mode enabled, update checker disabled')
            return

        response = self.request(first_run)
        if response is None:
            # Schedule a re-check in 30 seconds on errors
            self.reset()
            self.schedule_next(30)
            return

        # Store our new client_id for later use
        if not self.client_id and 'client_id' in response:
            self.client_id = response['client_id']

            Dict['client_id'] = self.client_id
            Dict.Save()

        self.process_response(first_run, response)

        self.schedule_next()

    def process_response(self, first_run, response):
        log_func = Log.Debug if first_run else Log.Info

        if response.get('update_error'):
            self.reset()

            message = 'Unable to check for updates, ' \
                      'probably on an unsupported branch: "%s"' % response['update_error']

            # Only log the warning on the first result, no need to spam with warnings
            if first_run:
                Log.Info(message)
            else:
                Log.Debug(message)
        elif response.get('update_available'):
            self.update_available = True
            self.update_detail = response['update_available']

            log_func("Update Available: %s" % self.update_detail['name'])
        else:
            self.reset(False)

            log_func("Up to date")

    def schedule_next(self, interval=None):
        if interval is None:
            interval = self.interval

        self.timer = Timer(interval, self.run)
        self.timer.start()

        Log.Debug("Next update check scheduled to happen in %s seconds" % interval)

########NEW FILE########
__FILENAME__ = client
from core.model import DictModel


class Client(DictModel):
    def __init__(self, client_id=None, name=None, address=None):
        """
        :type client_id: str
        :type name: str
        """

        super(Client, self).__init__(client_id)

        self.name = name
        self.address = address

    def __str__(self):
        return '<Client key: "%s", name: "%s", address: "%s">' % (
            self.key,
            self.name,
            self.address
        )

    @classmethod
    def from_section(cls, section):
        if section is None:
            return None

        return Client(
            section.get('machineIdentifier'),
            section.get('name'),
            section.get('address')
        )

########NEW FILE########
__FILENAME__ = sync_status
from core.helpers import total_seconds, build_repr
from core.model import DictModel


class SyncStatus(DictModel):
    root_key = 'syncStatus'

    def __init__(self, handler_key=None):
        """Holds the status of syncing tasks

        :type handler_key: str
        """

        super(SyncStatus, self).__init__(handler_key)

        #: :type: datetime
        self.previous_timestamp = None

        #: :type: int
        self.previous_elapsed = None

        #: :type: bool
        self.previous_success = None

        #: :type: datetime
        self.last_success = None

    def update(self, success, start_time, end_time):
        self.previous_success = success
        self.previous_timestamp = start_time
        self.previous_elapsed = end_time - start_time

        if success:
            self.last_success = start_time

        self.save()

        # Save to disk
        Dict.Save()

    def __repr__(self):
        return build_repr(self, ['previous_timestamp', 'previous_elapsed', 'previous_result', 'last_success_timestamp'])

    def __str__(self):
        return self.__repr__()

########NEW FILE########
__FILENAME__ = user
from core.model import DictModel


class User(DictModel):
    def __init__(self, user_id=None, title=None):
        """
        :type user_id: str
        :type title: str
        """

        super(User, self).__init__(user_id)

        self.title = title
        self.user_id = user_id

    @staticmethod
    def from_section(section):
        """
        :type section: ?

        :rtype: User
        """

        if not section:
            Log.Debug("[User.from_section] Invalid section")
            return None

        elements = section.findall('User')
        if not len(elements):
            Log.Info('[User.from_section] Unable to find "User" element.')
            return None

        return User(
            elements[0].get('id'),
            elements[0].get('title')
        )

########NEW FILE########
__FILENAME__ = watch_session
from core.model import DictModel
from data.client import Client
from data.user import User


class WatchSession(DictModel):
    root_key = 'nowPlaying'

    def __init__(self, session_key=None, item_key=None, metadata=None, state=None, user=None, client=None):
        """
        :type metadata: ?
        :type state: str
        :type user: User
        """

        super(WatchSession, self).__init__(session_key)

        self.item_key = item_key

        # Plex
        self.metadata = metadata
        self.user = user
        self.client = client

        # States
        self.skip = False
        self.scrobbled = False
        self.watching = False

        # Multi-episode scrobbling
        self.cur_episode = None

        self.progress = None
        self.cur_state = state

        self.paused_since = None
        self.last_view_offset = 0

        self.update_required = False
        self.last_updated = Datetime.FromTimestamp(0)

    def get_type(self):
        """
        :rtype: str or None
        """

        if not self.metadata or not self.metadata.get('type'):
            return None

        media_type = self.metadata.get('type')

        if media_type == 'episode':
            return 'show'

        return media_type

    def get_title(self):
        if not self.metadata:
            return None

        if 'grandparent_title' in self.metadata:
            return self.metadata['grandparent_title']

        return self.metadata.get('title')

    def reset(self):
        self.scrobbled = False
        self.watching = False

        self.last_updated = Datetime.FromTimestamp(0)

    @classmethod
    def object_from_json(cls, key, value):
        if key == 'user':
            return User.from_json(value)

        if key == 'client':
            return Client.from_json(value)

        return value

    @staticmethod
    def from_section(section, state, metadata, client_section=None):
        """
        :type section: ?
        :type state: str

        :rtype: WatchSession or None
        """

        if not section:
            return None

        return WatchSession(
            section.get('sessionKey'),
            section.get('ratingKey'),
            metadata, state,
            user=User.from_section(section),
            client=Client.from_section(client_section)
        )

    @staticmethod
    def from_info(info, metadata, client_section):
        if not info:
            return None

        return WatchSession(
            'logging-%s' % info.get('machineIdentifier'),
            info['ratingKey'],
            metadata,
            info['state'],
            client=Client.from_section(client_section)
        )

########NEW FILE########
__FILENAME__ = main_menu
from core.helpers import pad_title, get_pref
from core.plugin import ART, NAME, ICON, PLUGIN_VERSION
from interface.sync_menu import SyncMenu


@handler('/applications/trakttv', NAME, thumb=ICON, art=ART)
def MainMenu():
    oc = ObjectContainer(no_cache=True)

    if not get_pref('valid'):
        oc.add(DirectoryObject(
            key='/applications/trakttv',
            title=L("Error: Authentication failed"),
        ))

    oc.add(DirectoryObject(
        key=Callback(SyncMenu),
        title=L("Sync"),
        summary=L("Sync the Plex library with Trakt.tv")
    ))

    oc.add(DirectoryObject(
        key=Callback(AboutMenu),
        title=L("About")
    ))

    oc.add(PrefsObject(
        title="Preferences",
        summary="Configure how to connect to Trakt.tv",
        thumb=R("icon-preferences.png")
    ))

    return oc


@route('/applications/trakttv/about')
def AboutMenu():
    oc = ObjectContainer(title2="About")

    oc.add(DirectoryObject(
        key=Callback(AboutMenu),
        title=pad_title("Version: %s" % PLUGIN_VERSION)
    ))

    return oc

########NEW FILE########
__FILENAME__ = sync_menu
from core.helpers import timestamp, pad_title, plural, get_pref, get_filter
from plex.plex_media_server import PlexMediaServer
from sync.manager import SyncManager
from datetime import datetime
from ago import human


# NOTE: pad_title(...) is used as a "hack" to force the UI to use 'media-details-list'

@route('/applications/trakttv/sync')
def SyncMenu(refresh=None):
    oc = ObjectContainer(title2=L("Sync"), no_history=True, no_cache=True)
    all_keys = []

    create_active_item(oc)

    oc.add(DirectoryObject(
        key=Callback(Synchronize),
        title=pad_title('Synchronize'),
        summary=get_task_status('synchronize'),
        thumb=R("icon-sync.png")
    ))

    sections = PlexMediaServer.get_sections(['show', 'movie'], titles=get_filter('filter_sections'))

    for _, key, title in sections:
        oc.add(DirectoryObject(
            key=Callback(Push, section=key),
            title=pad_title('Push "' + title + '" to trakt'),
            summary=get_task_status('push', key),
            thumb=R("icon-sync_up.png")
        ))
        all_keys.append(key)

    if len(all_keys) > 1:
        oc.add(DirectoryObject(
            key=Callback(Push),
            title=pad_title('Push all to trakt'),
            summary=get_task_status('push'),
            thumb=R("icon-sync_up.png")
        ))

    oc.add(DirectoryObject(
        key=Callback(Pull),
        title=pad_title('Pull from trakt'),
        summary=get_task_status('pull'),
        thumb=R("icon-sync_down.png")
    ))

    return oc


def create_active_item(oc):
    task, handler = SyncManager.get_current()
    if not task:
        return

    # Format values
    remaining = format_remaining(task.statistics.seconds_remaining)
    progress = format_percentage(task.statistics.progress)

    # Title
    title = '%s - Status' % handler.title

    if progress:
        title += ' (%s)' % progress

    # Summary
    summary = task.statistics.message or 'Working'

    if remaining:
        summary += ', ~%s second%s remaining' % (remaining, plural(remaining))

    # Create items
    oc.add(DirectoryObject(
        key=Callback(SyncMenu, refresh=timestamp()),
        title=pad_title(title),
        summary=summary + ' (click to refresh)'
    ))

    oc.add(DirectoryObject(
        key=Callback(Cancel),
        title=pad_title('%s - Cancel' % handler.title)
    ))


def format_percentage(value):
    if not value:
        return None

    return '%d%%' % (value * 100)

def format_remaining(value):
    if not value:
        return None

    return int(round(value, 0))


def get_task_status(key, section=None):
    result = []

    status = SyncManager.get_status(key, section)

    if status.previous_timestamp:
        since = datetime.utcnow() - status.previous_timestamp

        if since.seconds < 1:
            result.append('Last run just a moment ago')
        else:
            result.append('Last run %s' % human(since, precision=1))

    if status.previous_elapsed:
        if status.previous_elapsed.seconds < 1:
            result.append('taking less than a second')
        else:
            result.append('taking %s' % human(
                status.previous_elapsed,
                precision=1,
                past_tense='%s'
            ))

    if status.previous_success is True:
        result.append('was successful')
    elif status.previous_timestamp:
        # Only add 'failed' fragment if there was actually a previous run
        result.append('failed')

    if len(result):
        return ', '.join(result) + '.'

    return 'Not run yet.'


@route('/applications/trakttv/sync/synchronize')
def Synchronize():
    if not SyncManager.trigger_synchronize():
        return MessageContainer(
            'Unable to sync',
            'Syncing task already running, unable to start'
        )

    return MessageContainer(
        'Syncing started',
        'Synchronize has started and will continue in the background'
    )



@route('/applications/trakttv/sync/push')
def Push(section=None):
    if not SyncManager.trigger_push(section):
        return MessageContainer(
            'Unable to sync',
            'Syncing task already running, unable to start'
        )

    return MessageContainer(
        'Syncing started',
        'Push has been triggered and will continue in the background'
    )


@route('/applications/trakttv/sync/pull')
def Pull():
    if not SyncManager.trigger_pull():
        return MessageContainer(
            'Unable to sync',
            'Syncing task already running, unable to start'
        )

    return MessageContainer(
        'Syncing started',
        'Pull has been triggered and will continue in the background'
    )


@route('/applications/trakttv/sync/cancel')
def Cancel():
    if not SyncManager.cancel():
        return MessageContainer(
            'Unable to cancel',
            'There is no syncing task running'
        )

    return MessageContainer(
        'Syncing cancelled',
        'Syncing task has been notified to cancel'
    )

########NEW FILE########
__FILENAME__ = plex_base
from core.network import request


class PlexBase(object):
    base_url = 'http://127.0.0.1:32400'

    @classmethod
    def request(cls, path='/', response_type='xml', raise_exceptions=False, retry=True, timeout=3, **kwargs):
        if not path.startswith('/'):
            path = '/' + path

        response = request(
            cls.base_url + path,
            response_type,

            raise_exceptions=raise_exceptions,

            retry=retry,
            timeout=timeout,

            **kwargs
        )

        return response.data if response else None

########NEW FILE########
__FILENAME__ = plex_library
from core.logger import Logger
from plex.plex_base import PlexBase
from plex.plex_objects import PlexShow, PlexEpisode, PlexMovie
from plex.plex_matcher import PlexMatcher
from plex.plex_metadata import PlexMetadata
from plex.plex_media_server import PlexMediaServer

log = Logger('plex.plex_library')


class PlexLibrary(PlexBase):
    @classmethod
    def map_item(cls, table, container, media):
        # Get the key for the item
        parsed_guid, key = PlexMetadata.get_key(media.get('ratingKey'))
        if parsed_guid is None:
            return False

        if key not in table:
            table[key] = []

        # Create object for the data
        data_type = media.get('type')
        if data_type == 'movie':
            item = PlexMovie.create(container, media, parsed_guid, key)
        elif data_type == 'show':
            item = PlexShow.create(container, media, parsed_guid, key)
        else:
            log.info('Unknown item "%s" with type "%s"', media.get('ratingKey'), data_type)
            return False

        # Map item into table
        table[key].append(item)
        return True

    @classmethod
    def fetch(cls, types=None, keys=None, titles=None, cache_id=None):
        if types and isinstance(types, basestring):
            types = [types]

        # Get all sections or filter based on 'types' and 'sections'
        sections = [(type, key) for (type, key, _) in PlexMediaServer.get_sections(
            types, keys, titles,
            cache_id=cache_id
        )]

        movies = {}
        shows = {}

        for type, key in sections:
            container = PlexMediaServer.get_section(key, cache_id=cache_id)
            if container is None:
                continue

            for media in container:
                if type == 'movie':
                    cls.map_item(movies, container, media)

                if type == 'show':
                    cls.map_item(shows, container, media)

        if len(types) == 1:
            if types[0] == 'movie':
                return movies

            if types[0] == 'show':
                return shows

        return movies, shows

    @classmethod
    def fetch_episodes(cls, key, parent=None, cache_id=None):
        """Fetch the episodes for a show from the Plex library

        :param key: Key of show to fetch episodes for
        :type key: str

        :param cache_id: Cached response identifier
        :type cache_id: str

        :return: Dictionary containing the episodes in this form: {season_num: {episode_num: <PlexEpisode>}}
        :rtype: dict
        """

        result = {}

        container = cls.request('library/metadata/%s/allLeaves' % key, timeout=30, cache_id=cache_id)

        if container is None:
            log.warn('Unable to retrieve episodes (key: "%s")', key)
            return None

        for video in container:
            season, episodes = PlexMatcher.get_identifier(video)

            obj = PlexEpisode.create(container, video, season, episodes, parent=parent)

            for episode in episodes:
                result[season, episode] = obj

        # Ensure PlexMatcher cache is stored to disk
        PlexMatcher.save()

        return result

########NEW FILE########
__FILENAME__ = plex_matcher
from core.helpers import try_convert, json_encode, json_decode, get_pref
from core.logger import Logger
from plex.plex_base import PlexBase
from caper import Caper
import os

log = Logger('plex.plex_matcher')


class PlexMatcher(PlexBase):
    current = None

    cache_pending = 0
    cache_key = 'matcher_cache'
    cache = None

    @classmethod
    def get_parser(cls):
        """
        :rtype: Caper
        """
        if cls.current is None:
            log.info('Initializing caper parsing library')
            cls.current = Caper()

        return cls.current

    @classmethod
    def remove_distant(cls, l, base=None, start=0, stop=None, step=1, max_distance=1):
        s = sorted(l)
        result = []

        if base is not None:
            bx = s.index(base)

            left = s[:bx + 1]
            result.extend(cls.remove_distant(left, start=len(left) - 2, stop=-1, step=-1, max_distance=max_distance))

            result.append(base)

            right = s[bx:]
            result.extend(cls.remove_distant(right, start=1, step=1, max_distance=max_distance))

            return result

        if stop is None:
            stop = len(s)

        for x in xrange(start, stop, step):
            if abs(s[x] - s[x - step]) <= max_distance:
                result.append(s[x])
            else:
                break

        return result

    @classmethod
    def match_identifier(cls, p_season, p_episode, c_identifier):
        # Season number retrieval/validation (only except exact matches to p_season)
        if 'season' not in c_identifier:
            return

        c_season = try_convert(c_identifier['season'], int)
        if c_season != p_season:
            return

        # Episode number retrieval/validation
        c_episodes = None

        # Single or repeat-style episodes
        if 'episode' in c_identifier:
            episodes = c_identifier['episode']

            if not isinstance(episodes, (list, set)):
                episodes = [episodes]

            c_episodes = [try_convert(x, int) for x in episodes]

        # Extend-style episodes
        if 'episode_from' in c_identifier and 'episode_to' in c_identifier:
            c_from = try_convert(c_identifier['episode_from'], int)
            c_to = try_convert(c_identifier['episode_to'], int)

            if c_from is None or c_to is None:
                return

            episodes = range(c_from, c_to + 1)

            # Ensure plex episode is inside identifier episode range
            if p_episode in episodes:
                c_episodes = episodes
            else:
                return

        return c_episodes

    @classmethod
    def create_cache(cls):
        cls.cache = {
            'version': Caper.version,
            'entries': {}
        }

        log.info('Created PlexMatcher cache (version: %s)', cls.cache['version'])

    @classmethod
    def load(cls):
        # Already loaded?
        if cls.cache is not None:
            return

        if Data.Exists(cls.cache_key):
            cls.cache = json_decode(Data.Load(cls.cache_key))

            if cls.cache['version'] != Caper.version:
                Data.Remove(cls.cache_key)
                cls.cache = None
                log.info('Caper version changed, reset matcher cache')

            log.info('Loaded PlexMatcher cache (version: %s)', cls.cache['version'])

        # Create cache if one doesn't exist or is invalid
        if cls.cache is None:
            cls.create_cache()

    @classmethod
    def save(cls, force=False):
        if cls.cache_pending < 1 and not force:
            return

        Data.Save(cls.cache_key, json_encode(cls.cache))
        log.info('Saved PlexMatcher cache (pending: %s, version: %s)', cls.cache_pending, cls.cache['version'])

        cls.cache_pending = 0

    @classmethod
    def lookup(cls, file_hash):
        cls.load()
        return cls.cache['entries'].get(file_hash)

    @classmethod
    def store(cls, file_hash, identifier):
        cls.cache['entries'][file_hash] = identifier
        cls.cache_pending = cls.cache_pending + 1

    @classmethod
    def parse(cls, file_name, use_cache=True):
        identifier = None

        file_hash = Hash.MD5(file_name)

        # Try lookup identifier in cache
        if use_cache:
            identifier = cls.lookup(file_hash)

        # Parse new file_name
        if identifier is None:
            # Parse file_name with Caper
            result = cls.get_parser().parse(file_name)

            chain = result.chains[0] if result.chains else None

            # Get best identifier match from result
            identifier = chain.info.get('identifier', []) if chain else []

            # Update cache
            cls.store(file_hash, identifier)

        return identifier

    @classmethod
    def get_extended(cls, video, p_season, p_episode):
        # Ensure extended matcher is enabled
        if get_pref('matcher') != 'plex_extended':
            return []

        # Parse filename for extra info
        parts = video.find('Media').findall('Part')
        if not parts:
            log.warn('Item "%s" has no parts', video.get('ratingKey'))
            return []

        # Get just the name of the first part (without full path and extension)
        file_name = os.path.splitext(os.path.basename(parts[0].get('file')))[0]

        # Parse file_name with caper (or get cached result)
        c_identifiers = cls.parse(file_name)

        result = []
        for c_identifier in c_identifiers:
            if 'season' not in c_identifier:
                continue

            episodes = cls.match_identifier(p_season, p_episode, c_identifier)
            if episodes is None:
                continue

            # Insert any new episodes found from identifier
            for episode in episodes:
                if episode == p_episode:
                    continue

                result.append(episode)

        return result

    @classmethod
    def get_identifier(cls, video):
        # Get plex identifier
        p_season = try_convert(video.get('parentIndex'), int)
        p_episode = try_convert(video.get('index'), int)

        # Ensure plex data is valid
        if p_season is None or p_episode is None:
            log.debug('Ignoring item with key "%s", invalid season or episode attribute', video.get('ratingKey'))
            return None, []

        # Find new episodes from identifiers
        c_episodes = [p_episode]

        # Add extended episodes
        c_episodes.extend(cls.get_extended(video, p_season, p_episode))

        # Remove any episode identifiers that are more than 1 away
        c_episodes = cls.remove_distant(c_episodes, p_episode)

        return p_season, c_episodes

########NEW FILE########
__FILENAME__ = plex_media_server
from core.helpers import all
from core.logger import Logger
from core.plugin import PLUGIN_IDENTIFIER
from plex.plex_base import PlexBase
import os

log = Logger('plex.plex_media_server')


class PlexMediaServer(PlexBase):
    #
    # Server
    #

    @classmethod
    def get_info(cls, quiet=False):
        return cls.request(quiet=quiet)

    @classmethod
    def get_version(cls, default=None, quiet=False):
        server_info = cls.get_info(quiet)
        if server_info is None:
            return default

        return server_info.attrib.get('version') or default

    @classmethod
    def get_client(cls, client_id):
        if not client_id:
            log.warn('Invalid client_id provided')
            return None

        result = cls.request('clients')
        if not result:
            return None

        found_clients = []

        for section in result.xpath('//Server'):
            found_clients.append(section.get('machineIdentifier'))

            if section.get('machineIdentifier') == client_id:
                return section

        log.info("Unable to find client '%s', available clients: %s" % (client_id, found_clients))
        return None

    @classmethod
    def get_sessions(cls):
        return cls.request('status/sessions')

    @classmethod
    def get_session(cls, session_key):
        sessions = cls.get_sessions()
        if sessions is None:
            log.warn('Sessions request failed')
            return None

        for section in sessions:
            if section.get('sessionKey') == session_key and '/library/metadata' in section.get('key'):
                return section

        log.warn('Session "%s" not found', session_key)
        return None

    #
    # Collection
    #

    @classmethod
    def get_sections(cls, types=None, keys=None, titles=None, cache_id=None):
        """Get the current sections available on the server, optionally filtering by type and/or key

        :param types: Section type filter
        :type types: str or list of str

        :param keys: Section key filter
        :type keys: str or list of str

        :return: List of sections found
        :rtype: (type, key, title)
        """

        if types and isinstance(types, basestring):
            types = [types]

        if keys and isinstance(keys, basestring):
            keys = [keys]

        if titles:
            if isinstance(titles, basestring):
                titles = [titles]

            titles = [x.lower() for x in titles]

        container = cls.request('library/sections', cache_id=cache_id)

        sections = []
        for section in container:
            # Try retrieve section details - (type, key, title)
            section = (
                section.get('type', None),
                section.get('key', None),
                section.get('title', None)
            )

            # Validate section, skip over bad sections
            if not all(x for x in section):
                continue

            # Apply type filter
            if types is not None and section[0] not in types:
                continue

            # Apply key filter
            if keys is not None and section[1] not in keys:
                continue

            # Apply title filter
            if titles is not None and section[2].lower() not in titles:
                continue

            sections.append(section)

        return sections

    @classmethod
    def get_section(cls, key, cache_id=None):
        return cls.request('library/sections/%s/all' % key, timeout=10, cache_id=cache_id)

    @classmethod
    def scrobble(cls, key):
        result = cls.request(
            ':/scrobble?identifier=com.plexapp.plugins.library&key=%s' % key,
            response_type='text'
        )

        return result is not None

    @classmethod
    def rate(cls, key, value):
        value = int(round(value, 0))

        result = cls.request(
            ':/rate?key=%s&identifier=com.plexapp.plugins.library&rating=%s' % (key, value),
            response_type='text'
        )

        return result is not None

    @classmethod
    def restart_plugin(cls, identifier=None):
        if identifier is None:
            identifier = PLUGIN_IDENTIFIER

        # Touch plugin directory to update modified time
        os.utime(os.path.join(Core.code_path), None)

        cls.request(':/plugins/%s/reloadServices' % identifier)

########NEW FILE########
__FILENAME__ = plex_metadata
from core.cache import Cache
from core.eventing import EventManager
from core.helpers import try_convert
from core.logger import Logger
from plex.plex_base import PlexBase
from plex.plex_matcher import PlexMatcher
from plex.plex_objects import PlexParsedGuid, PlexShow, PlexEpisode, PlexMovie
import re

log = Logger('plex.plex_metadata')

# Mappings for agents to their compatible service
METADATA_AGENT_MAP = {
    # Multi
    'mcm':              ('thetvdb', r'MCM_TV_A_(.*)'),

    # Movie
    'xbmcnfo':          'imdb',
    'standalone':       'themoviedb',

    # TV
    'abstvdb':          'thetvdb',
    'thetvdbdvdorder':  'thetvdb',
    'xbmcnfotv':        [
        ('imdb', r'(tt\d+)'),
        'thetvdb'
    ],
}

SUPPORTED_MEDIA_TYPES = [
    'movie',
    'show',
    'episode'
]


class PlexMetadata(PlexBase):
    cache = Cache('metadata')

    @classmethod
    def initialize(cls):
        EventManager.subscribe('notifications.timeline.created', cls.timeline_created)
        EventManager.subscribe('notifications.timeline.deleted', cls.timeline_deleted)
        EventManager.subscribe('notifications.timeline.finished', cls.timeline_finished)

        cls.cache.on_refresh.subscribe(cls.on_refresh)

        # Compile agent mapping patterns
        for key, mappings in METADATA_AGENT_MAP.items():
            # Transform into list
            if type(mappings) is not list:
                mappings = [mappings]

            for x, value in enumerate(mappings):
                # Transform into tuple of length 2
                if type(value) is str:
                    value = (value, None)
                elif type(value) is tuple and len(value) == 1:
                    value = (value, None)

                # Compile pattern
                if value[1]:
                    value = (value[0], re.compile(value[1], re.IGNORECASE))

                mappings[x] = value

            METADATA_AGENT_MAP[key] = mappings

    @classmethod
    def on_refresh(cls, key):
        return cls.request('library/metadata/%s' % key, timeout=10)

    @classmethod
    def get_cache(cls, key):
        return cls.cache.get(key, refresh=True)

    @classmethod
    def get_guid(cls, key):
        metadata = cls.get_cache(key)
        if metadata is None:
            return None

        return metadata[0].get('guid')

    @classmethod
    def get(cls, key):
        if not key:
            return None

        container = cls.get_cache(key)
        if container is None:
            return None

        media = container[0]
        media_type = media.get('type')

        if media_type not in SUPPORTED_MEDIA_TYPES:
            raise NotImplementedError('Metadata with type "%s" is unsupported' % media_type)

        parsed_guid, item_key = cls.get_key(guid=media.get('guid'), required=False)

        # Create object for the data
        if media_type == 'movie':
            return PlexMovie.create(container, media, parsed_guid, item_key)

        if media_type == 'show':
            return PlexShow.create(container, media, parsed_guid, item_key)

        if media_type == 'episode':
            season, episodes = PlexMatcher.get_identifier(media)

            return PlexEpisode.create(container, media, season, episodes, parsed_guid, item_key)

        log.warn('Failed to parse item "%s" with type "%s"', key, media_type)
        return None

    #
    # GUID/key parsing
    #

    @classmethod
    def get_parsed_guid(cls, key=None, guid=None, required=True):
        if not guid:
            if key:
                guid = cls.get_guid(key)
            elif required:
                raise ValueError("Either guid or key is required")
            else:
                return None

        return PlexParsedGuid.from_guid(guid)

    @classmethod
    def get_mapping(cls, parsed_guid):
        # Strip leading key
        agent = parsed_guid.agent[parsed_guid.agent.rfind('.') + 1:]

        # Return mapped agent and sid_pattern (if present)
        mappings = METADATA_AGENT_MAP.get(agent, [])

        if type(mappings) is not list:
            mappings = [mappings]

        for mapping in mappings:
            map_agent, map_pattern = mapping

            if map_pattern is None:
                return map_agent, None, None

            match = map_pattern.match(parsed_guid.sid)
            if not match:
                continue

            return map_agent, map_pattern, match

        return agent, None, None

    @classmethod
    def get_key(cls, key=None, guid=None, required=True):
        parsed_guid = cls.get_parsed_guid(key, guid, required)

        # Ensure service id is valid
        if not parsed_guid or not parsed_guid.sid:
            log.warn('Missing GUID or service identifier for item with ratingKey "%s" (parsed_guid: %s)', key, parsed_guid)
            return None, None

        agent, sid_pattern, match = cls.get_mapping(parsed_guid)

        parsed_guid.agent = agent

        # Match sid with regex
        if sid_pattern:
            if not match:
                log.warn('Failed to match "%s" against sid_pattern for "%s" agent', parsed_guid.sid, parsed_guid.agent)
                return None, None

            # Update with new sid
            parsed_guid.sid = ''.join(match.groups())

        return parsed_guid, (parsed_guid.agent, parsed_guid.sid)

    @staticmethod
    def add_identifier(data, p_item):
        key = p_item['key'] if type(p_item) is dict else p_item.key

        # Ensure key is valid
        if not key:
            return data

        service, sid = key

        # Parse identifier and append relevant '*_id' attribute to data
        if service == 'imdb':
            data['imdb_id'] = sid
            return data

        # Convert TMDB and TVDB identifiers to integers
        if service in ['themoviedb', 'thetvdb']:
            sid = try_convert(sid, int)

            # If identifier is invalid, ignore it
            if sid is None:
                return data

        if service == 'themoviedb':
            data['tmdb_id'] = sid

        if service == 'thetvdb':
            data['tvdb_id'] = sid

        return data

    #
    # Timeline Events
    #

    @classmethod
    def timeline_created(cls, item):
        log.debug('timeline_created(%s)', item)

    @classmethod
    def timeline_deleted(cls, item):
        log.debug('timeline_deleted(%s)', item)

        cls.cache.remove(str(item['itemID']))

    @classmethod
    def timeline_finished(cls, item):
        log.debug('timeline_finished(%s)', item)

        cls.cache.invalidate(str(item['itemID']), refresh=True, create=True)

########NEW FILE########
__FILENAME__ = plex_objects
from core.helpers import build_repr, try_convert
from core.logger import Logger
from urlparse import urlparse

SHOW_AGENTS = [
    'com.plexapp.agents.thetvdb',
    'com.plexapp.agents.thetvdbdvdorder',
    'com.plexapp.agents.abstvdb',
    'com.plexapp.agents.xbmcnfotv',
    'com.plexapp.agents.mcm'
]

log = Logger('plex.plex_objects')


class PlexParsedGuid(object):
    def __init__(self, agent, sid, extra):
        self.agent = agent
        self.sid = sid
        self.extra = extra

        # Show
        self.season = None
        self.episode = None


    @classmethod
    def from_guid(cls, guid):
        if not guid:
            return None

        uri = urlparse(guid)
        agent = uri.scheme

        result = PlexParsedGuid(agent, uri.netloc, uri.query)

        # Nothing more to parse, return now
        if not uri.path:
            return result

        # Parse path component for agent-specific data
        path_fragments = uri.path.strip('/').split('/')

        if agent in SHOW_AGENTS:
            if len(path_fragments) >= 1:
                result.season = try_convert(path_fragments[0], int)

            if len(path_fragments) >= 2:
                result.episode = try_convert(path_fragments[1], int)
        else:
            log.warn('Unable to completely parse guid "%s"', guid)

        return result

    def __repr__(self):
        return build_repr(self, ['agent', 'sid', 'extra', 'season', 'episode'])

    def __str__(self):
        return self.__repr__()


class PlexMedia(object):
    def __init__(self, rating_key, key=None):
        self.rating_key = rating_key
        self.key = key

        self.type = None

        self.title = None
        self.year = None

        self.agent = None
        self.sid = None

        self.user_rating = None

        self.section_key = None
        self.section_title = None

    @staticmethod
    def fill(obj, container, video, parsed_guid=None):
        obj.type = video.get('type')

        obj.title = video.get('title')
        obj.year = try_convert(video.get('year'), int)

        obj.user_rating = try_convert(video.get('userRating'), float)

        if obj.user_rating:
            obj.user_rating = int(round(obj.user_rating, 0))

        obj.section_key = try_convert(container.get('librarySectionID'), int)
        obj.section_title = container.get('librarySectionTitle')

        if parsed_guid is not None:
            obj.agent = parsed_guid.agent
            obj.sid = parsed_guid.sid

    @staticmethod
    def get_repr_keys():
        return [
            'rating_key', 'key',
            'type',
            'title', 'year',
            'agent', 'sid',
            'user_rating',
            'section_key', 'section_title'
        ]

    def to_dict(self):
        items = []

        for key in self.get_repr_keys():
            value = getattr(self, key)

            if isinstance(value, PlexMedia):
                value = value.to_dict()

            items.append((key, value))

        return dict(items)

    def __repr__(self):
        return build_repr(self, self.get_repr_keys() or [])

    def __str__(self):
        return self.__repr__()


class PlexVideo(PlexMedia):
    def __init__(self, rating_key, key=None):
        super(PlexVideo, self).__init__(rating_key, key)

        self.view_count = 0
        self.duration = None

    @property
    def seen(self):
        return self.view_count and self.view_count > 0

    @staticmethod
    def fill(obj, container, video, parsed_guid=None):
        PlexMedia.fill(obj, container, video, parsed_guid)

        obj.view_count = try_convert(video.get('viewCount'), int)
        obj.duration = try_convert(video.get('duration'), int, 0) / float(1000 * 60)  # Convert to minutes

    @staticmethod
    def get_repr_keys():
        return PlexMedia.get_repr_keys() + ['view_count', 'duration']


class PlexShow(PlexMedia):
    def __init__(self, rating_key, key):
        super(PlexShow, self).__init__(rating_key, key)

    @classmethod
    def create(cls, container, directory, parsed_guid, key):
        if parsed_guid.season or parsed_guid.episode:
            raise ValueError('parsed_guid is not valid for PlexShow')

        show = cls(directory.get('ratingKey'), key)

        cls.fill(show, container, directory, parsed_guid)
        return show


class PlexEpisode(PlexVideo):
    def __init__(self, parent, rating_key, key):
        super(PlexEpisode, self).__init__(rating_key, key)

        self.parent = parent

        self.grandparent_title = None

        self.season = None
        self.episodes = None

    @classmethod
    def create(cls, container, video, season, episodes, parsed_guid=None, key=None, parent=None):
        obj = cls(parent, video.get('ratingKey'), key)

        obj.grandparent_title = video.get('grandparentTitle')

        obj.season = season
        obj.episodes = episodes

        cls.fill(obj, container, video, parsed_guid)
        return obj

    @staticmethod
    def get_repr_keys():
        return PlexVideo.get_repr_keys() + ['parent', 'grandparent_title', 'season', 'episodes']


class PlexMovie(PlexVideo):
    def __init__(self, rating_key, key):
        super(PlexMovie, self).__init__(rating_key, key)

    @classmethod
    def create(cls, container, video, parsed_guid, key):
        if parsed_guid and (parsed_guid.season or parsed_guid.episode):
            raise ValueError('parsed_guid is not valid for PlexMovie')

        movie = cls(video.get('ratingKey'), key)

        cls.fill(movie, container, video, parsed_guid)
        return movie

########NEW FILE########
__FILENAME__ = plex_preferences
from core.helpers import try_convert
from core.logger import Logger
from plex.plex_base import PlexBase

log = Logger('plex.plex_preferences')


class PlexPreferences(PlexBase):
    @classmethod
    def set(cls, key, value, value_type=None):
        result = cls.request(':/prefs?%s=%s' % (key, try_convert(value, value_type)), 'text', method='PUT')
        if result is None:
            return False

        return True

    @classmethod
    def get(cls, key, value_type=None):
        result = cls.request(':/prefs')
        if result is None:
            return None

        for setting in result.xpath('//Setting'):
            if setting.get('id') == key:
                return cls.convert_value(setting.get('value'), value_type)

        log.warn('Unable to find setting "%s"', key)
        return None

    @classmethod
    def convert_value(cls, value, value_type):
        if not value_type or value_type is str:
            return value

        if value_type is bool:
            return value.lower() == 'true'

        log.warn('Unsupported value type %s', value_type)
        return None

    @classmethod
    def log_debug(cls, value=None):
        if value is None:
            return cls.get('logDebug', bool)

        return cls.set('logDebug', value, int)

########NEW FILE########
__FILENAME__ = activity
from core.logger import Logger
from core.method_manager import Method, Manager

log = Logger('pts.activity')


class ActivityMethod(Method):
    def get_name(self):
        return 'Activity_%s' % self.name


class Activity(Manager):
    tag = 'pts.activity'

    available = []
    enabled = []

########NEW FILE########
__FILENAME__ = activity_logging
from core.eventing import EventManager
from core.helpers import str_format
from core.logger import Logger
from plex.plex_media_server import PlexMediaServer
from plex.plex_preferences import PlexPreferences
from pts.activity import ActivityMethod, Activity
from asio_base import SEEK_ORIGIN_CURRENT
from asio import ASIO
import time
import os

LOG_PATTERN = r'^.*?\[\w+\]\s\w+\s-\s{message}$'
REQUEST_HEADER_PATTERN = str_format(LOG_PATTERN, message=r"Request: (\[.*?\]\s)?{method} {path}.*?")

PLAYING_HEADER_REGEX = Regex(str_format(REQUEST_HEADER_PATTERN, method="GET", path="/:/(?P<type>timeline|progress)"))

IGNORE_PATTERNS = [
    r'error parsing allowedNetworks.*?',
    r'Comparing request from.*?',
    r'We found auth token (.*?), enabling token-based authentication\.',
    r'Came in with a super-token, authorization succeeded\.'
]

IGNORE_REGEX = Regex(str_format(LOG_PATTERN, message='(%s)' % ('|'.join('(%s)' % x for x in IGNORE_PATTERNS))))

PARAM_REGEX = Regex(str_format(LOG_PATTERN, message=r' \* (?P<key>.*?) =\> (?P<value>.*?)'))
RANGE_REGEX = Regex(str_format(LOG_PATTERN, message=r'Request range: \d+ to \d+'))
CLIENT_REGEX = Regex(str_format(LOG_PATTERN, message=r'Client \[(?P<machineIdentifier>.*?)\].*?'))

log = Logger('pts.activity_logging')


class LoggingActivity(ActivityMethod):
    name = 'LoggingActivity'
    required_info = ['ratingKey', 'state', 'time']
    extra_info = ['duration', 'machineIdentifier']

    log_path = None
    log_file = None

    @classmethod
    def get_path(cls):
        if not cls.log_path:
            cls.log_path = os.path.join(Core.log.handlers[1].baseFilename, '..', '..', 'Plex Media Server.log')
            cls.log_path = os.path.abspath(cls.log_path)

            log.debug('log_path = "%s"' % cls.log_path)

        return cls.log_path

    @classmethod
    def test(cls):
        # Try enable logging
        if not PlexPreferences.log_debug(True):
            log.warn('Unable to enable logging')

        # Test if logging is enabled
        if not PlexPreferences.log_debug():
            log.warn('Debug logging not enabled, unable to use logging activity method.')
            return False

        if cls.try_read_line(True):
            return True

        return False

    @classmethod
    def read_line(cls, timeout=30):
        if not cls.log_file:
            cls.log_file = ASIO.open(cls.get_path(), opener=False)
            cls.log_file.seek(cls.log_file.get_size(), SEEK_ORIGIN_CURRENT)
            cls.log_path = cls.log_file.get_path()
            log.info('Opened file path: "%s"' % cls.log_path)

        return cls.log_file.read_line(timeout=timeout, timeout_type='return')

    @classmethod
    def try_read_line(cls, start_interval=1, interval_step=1.6, max_interval=5, max_tries=4, timeout=30):
        line = None

        try_count = 0
        retry_interval = float(start_interval)

        while not line and try_count <= max_tries:
            try_count += 1

            line = cls.read_line(timeout)
            if line:
                break

            if cls.log_file.get_path() != cls.log_path:
                log.debug("Log file moved (probably rotated), closing")
                cls.close()

            # If we are below max_interval, keep increasing the interval
            if retry_interval < max_interval:
                retry_interval = retry_interval * interval_step

                # Ensure the new retry_interval is below max_interval
                if retry_interval > max_interval:
                    retry_interval = max_interval

            # Sleep if we should still retry
            if try_count <= max_tries:
                if try_count > 1:
                    log.debug('Log file read returned nothing, waiting %.02f seconds and then trying again' % retry_interval)
                    time.sleep(retry_interval)

                # Ping server to see if server is still active
                PlexMediaServer.get_info(quiet=True)

        if line and try_count > 2:
            log.debug('Successfully read the log file after retrying')
        elif not line:
            log.warn('Finished retrying, still no success')

        return line

    @classmethod
    def close(cls):
        if not cls.log_file:
            return

        cls.log_file.close()
        cls.log_file = None

    def run(self):
        line = self.try_read_line(timeout=60)
        if not line:
            log.warn('Unable to read log file')
            return

        log.debug('Ready')

        while True:
            # Grab the next line of the log
            line = self.try_read_line(timeout=60)

            if line:
                self.process(line)
            else:
                log.warn('Unable to read log file')

    def process(self, line):
        header_match = PLAYING_HEADER_REGEX.match(line)
        if not header_match:
            return

        activity_type = header_match.group('type')

        # Get a match from the activity entries
        if activity_type == 'timeline':
            match = self.timeline()
        elif activity_type == 'progress':
            match = self.progress()
        else:
            log.warn('Unknown activity type "%s"', activity_type)
            return

        # Ensure we successfully matched a result
        if not match:
            return

        # Sanitize the activity result
        info = {}

        # - Get required info parameters
        for key in self.required_info:
            if key in match and match[key] is not None:
                info[key] = match[key]
            else:
                log.warn('Invalid activity match, missing key %s (%s)', key, match)
                return

        # - Add in any extra info parameters
        for key in self.extra_info:
            if key in match:
                info[key] = match[key]
            else:
                info[key] = None

        # Update the scrobbler with the current state
        EventManager.fire('scrobbler.logging.update', info)

    def timeline(self):
        return self.read_parameters(self.client_match, self.range_match)

    def progress(self):
        data = self.read_parameters()
        if not data:
            return None

        # Translate parameters into timeline-style form
        return {
            'state': data.get('state'),
            'ratingKey': data.get('key'),
            'time': data.get('time')
        }

    def read_parameters(self, *match_functions):
        match_functions = [self.parameter_match] + list(match_functions)

        info = {}

        while True:
            line = self.try_read_line(timeout=5)
            if not line:
                log.warn('Unable to read log file')
                return None

            # Run through each match function to find a result
            match = None
            for func in match_functions:
                match = func(line)

                if match is not None:
                    break

            # Update info dict with result, otherwise finish reading
            if match:
                info.update(match)
            elif match is None and IGNORE_REGEX.match(line.strip()) is None:
                break

        return info

    @staticmethod
    def parameter_match(line):
        match = PARAM_REGEX.match(line.strip())
        if not match:
            return None

        match = match.groupdict()

        return {match['key']: match['value']}

    @staticmethod
    def range_match(line):
        match = RANGE_REGEX.match(line.strip())
        if not match:
            return None

        return match.groupdict()

    @staticmethod
    def client_match(line):
        match = CLIENT_REGEX.match(line.strip())
        if not match:
            return None

        return match.groupdict()


Activity.register(LoggingActivity, weight=1)

########NEW FILE########
__FILENAME__ = activity_websocket
from core.eventing import EventManager
from core.helpers import try_convert, all
from core.logger import Logger
from pts.activity import ActivityMethod, Activity

import websocket
import time

log = Logger('pts.activity_websocket')


TIMELINE_STATES = {
    0: 'created',
    2: 'matching',
    3: 'downloading',
    4: 'loading',
    5: 'finished',
    6: 'analyzing',
    9: 'deleted'
}

REGEX_STATUS_SCANNING = Regex('Scanning the "(?P<section>.*?)" section')
REGEX_STATUS_SCAN_COMPLETE = Regex('Library scan complete')


class WebSocketActivity(ActivityMethod):
    name = 'WebSocketActivity'

    opcode_data = (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY)

    def __init__(self):
        super(WebSocketActivity, self).__init__()

        self.ws = None
        self.reconnects = 0

    def connect(self):
        self.ws = websocket.create_connection('ws://127.0.0.1:32400/:/websockets/notifications')
        
        log.info('Connected to notifications websocket')

    def run(self):
        self.connect()

        log.debug('Ready')

        while True:
            try:
                self.process(*self.receive())

                # successfully received data, reset reconnects counter
                self.reconnects = 0

            except websocket.WebSocketConnectionClosedException:
                if self.reconnects <= 5:
                    self.reconnects = self.reconnects + 1

                    # Increasing sleep interval between reconnections
                    if self.reconnects > 1:
                        time.sleep(2 * (self.reconnects - 1))

                    log.info('WebSocket connection has closed, reconnecting...')
                    self.connect()
                else:
                    log.error('WebSocket connection unavailable, activity monitoring not available')
                    break

    def receive(self):
        frame = self.ws.recv_frame()

        if not frame:
            raise websocket.WebSocketException("Not a valid frame %s" % frame)
        elif frame.opcode in self.opcode_data:
            return frame.opcode, frame.data
        elif frame.opcode == websocket.ABNF.OPCODE_CLOSE:
            self.ws.send_close()
            return frame.opcode, None
        elif frame.opcode == websocket.ABNF.OPCODE_PING:
            self.ws.pong("Hi!")

        return None, None

    def process(self, opcode, data):
        if opcode not in self.opcode_data:
            return False

        try:
            info = JSON.ObjectFromString(data)
        except Exception, e:
            log.warn('Error decoding message from websocket: %s' % e)
            log.debug(data)
            return False

        type = info.get('type')
        process_func = getattr(self, 'process_%s' % type, None)

        # Process each notification item
        if process_func:
            results = [process_func(item) for item in info['_children']]

            if len(results) and results[0]:
                return True

        log.debug('Unable to process notification: %s', info)
        return False

    @staticmethod
    def process_playing(item):
        session_key = item.get('sessionKey')
        state = item.get('state')
        view_offset = try_convert(item.get('viewOffset'), int)

        valid = all([
            x is not None
            for x in [session_key, state, view_offset]
        ])

        if valid:
            EventManager.fire('notifications.playing', str(session_key), str(state), view_offset)
            return True

        log.warn("'playing' notification doesn't look valid, ignoring: %s" % item)
        return False

    @staticmethod
    def process_timeline(item):
        state_key = TIMELINE_STATES.get(item['state'])
        if state_key is None:
            log.warn('Unknown timeline state "%s"', item['state'])
            return False

        EventManager.fire('notifications.timeline.%s' % state_key, item)
        return True

    @staticmethod
    def process_progress(item):
        # Not using this yet, this suppresses the 'Unable to process...' messages for now though
        return True

    @staticmethod
    def process_status(item):
        if item.get('notificationName') != 'LIBRARY_UPDATE':
            log.debug('Unknown notification name "%s"', item.get('notificationName'))
            return False

        title = item.get('title')

        # Check for scan complete message
        if REGEX_STATUS_SCAN_COMPLETE.match(title):
            EventManager.fire('notifications.status.scan_complete')
            return True

        # Check for scanning message
        match = REGEX_STATUS_SCANNING.match(title)
        if match:
            section = match.group('section')

            if section:
                EventManager.fire('notifications.status.scanning', section)
                return True

        log.debug('No matches found for %s', item)
        return False

Activity.register(WebSocketActivity, weight=None)

########NEW FILE########
__FILENAME__ = scrobbler
from core.helpers import str_pad, get_filter, get_pref, normalize
from core.logger import Logger
from core.method_manager import Method, Manager
from core.trakt import Trakt
from plex.plex_metadata import PlexMetadata
import math

log = Logger('pts.scrobbler')


class ScrobblerMethod(Method):
    def __init__(self):
        super(ScrobblerMethod, self).__init__(threaded=False)

    @staticmethod
    def status_message(session, state):
        state = state[:2].upper() if state else '?'
        progress = session.progress if session.progress is not None else '?'

        status = '[%s%s]' % (
            str_pad(state, 2, trim=True),
            str_pad(progress, 3, 'right', trim=True)
        )

        metadata_key = None

        if session.metadata and session.metadata.get('key'):
            metadata_key = session.metadata['key']

            if type(metadata_key) is tuple:
                metadata_key = ', '.join(repr(x) for x in metadata_key)

        title = '%s (%s)' % (session.get_title(), metadata_key)

        def build(message_format):
            return '%s %s' % (status, message_format % title)

        return build

    def get_action(self, session, state):
        """
        :type session: WatchSession
        :type state: str

        :rtype: str or None
        """

        status_message = self.status_message(session, state)

        # State has changed
        if state not in [session.cur_state, 'buffering']:
            session.cur_state = state

            if state == 'stopped' and session.watching:
                log.info(status_message('%s stopped, watching status cancelled'))
                session.watching = False
                return 'cancelwatching'

            if state == 'paused' and not session.paused_since:
                log.info(status_message("%s just paused, waiting 15s before cancelling the watching status"))

                session.paused_since = Datetime.Now()
                return None

            if state == 'playing' and not session.watching:
                log.info(status_message('Sending watch status for %s'))
                session.watching = True
                return 'watching'

        elif state == 'playing':
            # scrobble item
            if not session.scrobbled and session.progress >= get_pref('scrobble_percentage'):
                log.info(status_message('Scrobbling %s'))
                return 'scrobble'

            # update every 10 min if media hasn't finished
            elif session.progress < 100 and (session.last_updated + Datetime.Delta(minutes=10)) < Datetime.Now():
                log.info(status_message('Updating watch status for %s'))
                session.watching = True
                return 'watching'

            # cancel watching status on items at 100% progress
            elif session.progress >= 100 and session.watching:
                log.info(status_message('Media finished, cancelling watching status for %s'))
                session.watching = False
                return 'cancelwatching'

        return None

    @staticmethod
    def get_request_parameters(session):
        values = {}

        session_type = session.get_type()
        if not session_type:
            return None

        if session_type == 'show':
            if not session.metadata.get('episodes'):
                log.warn('No episodes found in metadata')
                return None

            if session.cur_episode >= len(session.metadata['episodes']):
                log.warn('Unable to find episode at index %s, available episodes: %s', session.cur_episode, session.metadata['episodes'])
                return None

            values.update({
                'season': session.metadata['season'],
                'episode': session.metadata['episodes'][session.cur_episode],

                # Scale duration to number of episodes
                'duration': session.metadata['duration'] / len(session.metadata['episodes'])
            })
        else:
            values['duration'] = session.metadata['duration']

        # Add TVDB/TMDB identifier
        values = PlexMetadata.add_identifier(values, session.metadata)

        values.update({
            'progress': session.progress,
            'title': session.get_title()
        })

        if 'year' in session.metadata:
            values['year'] = session.metadata['year']

        return values

    @classmethod
    def handle_state(cls, session, state):
        if state == 'playing' and session.paused_since:
            session.paused_since = None
            return True

        # If stopped, delete the session
        if state == 'stopped':
            log.debug(session.get_title() + ' stopped, deleting the session')
            session.delete()
            return True

        # If paused, queue a session update when playing begins again
        if state == 'paused' and not session.update_required:
            log.debug(session.get_title() + ' paused, session update queued to run when resumed')
            session.update_required = True
            return True

        return False

    @classmethod
    def handle_action(cls, session, media_type, action, state):
        # Setup Data to send to Trakt
        parameters = cls.get_request_parameters(session)
        if not parameters:
            log.info('Invalid parameters, unable to continue')
            return False

        log.trace('Sending action "%s/%s" - parameters: %s', media_type, action, parameters)

        response = Trakt.Media.action(media_type, action, **parameters)
        if not response['success']:
            log.warn('Unable to send scrobbler action')

        session.last_updated = Datetime.Now()

        if action == 'scrobble':
            session.scrobbled = True

            # If just scrobbled, force update on next status update to set as watching again
            session.last_updated = Datetime.Now() - Datetime.Delta(minutes=20)

        session.save()

    @staticmethod
    def update_progress(session, view_offset):
        if not session or not session.metadata:
            return False

        # Ensure duration is positive
        if session.metadata.get('duration', 0) <= 0:
            return False

        media = session.get_type()
        duration = session.metadata['duration'] * 60 * 1000

        total_progress = float(view_offset) / duration

        if media == 'show':
            if 'episodes' not in session.metadata:
                return False

            cur_episode = int(math.floor(len(session.metadata['episodes']) * total_progress))

            # If episode has changed, reset the state to start new session
            if cur_episode != session.cur_episode and session.cur_episode is not None:
                log.info('Session has changed episodes, state has been reset')
                session.reset()

            session.cur_episode = cur_episode

            # Scale progress based on number of episodes
            total_progress = (len(session.metadata['episodes']) * total_progress) - session.cur_episode

        session.progress = int(round(total_progress * 100, 0))

        return True

    @staticmethod
    def valid_user(session):
        if Prefs['scrobble_names'] is None:
            return True

        # Normalize username
        username = normalize(session.user.title) if session.user else None

        # Fetch filter
        filter = get_filter('scrobble_names')
        if filter is None:
            return True

        log.trace('validate user - username: "%s", filter: %s', username, filter)

        if not session.user or username not in filter:
            log.info('Ignoring item [%s](%s) played by filtered user: %s' % (
                session.item_key,
                session.get_title(),
                session.user.title if session.user else None
            ))
            return False

        return True

    @staticmethod
    def valid_client(session):
        if Prefs['scrobble_clients'] is None:
            return True

        # Normalize client name
        client_name = normalize(session.client.name) if session.client else None

        # Fetch filter
        filter = get_filter('scrobble_clients')
        if filter is None:
            return True

        log.trace('validate client - client_name: "%s", filter: %s', client_name, filter)

        if not session.client or client_name not in filter:
            log.info('Ignoring item [%s](%s) played by filtered client: %s' % (
                session.item_key,
                session.get_title(),
                client_name
            ))
            return False

        return True

    @staticmethod
    def valid_section(session):
        title = session.metadata.get('section_title')
        if not title:
            return True

        # Fetch filter
        filter = get_filter('filter_sections')
        if filter is None:
            return True

        # Normalize title
        title = normalize(title)

        log.trace('validate section - title: "%s", filter: %s', title, filter)

        # Check section title against filter
        if title not in filter:
            log.info('Ignoring item [%s](%s) played from filtered section "%s"' % (
                session.item_key,
                session.get_title(),
                session.metadata.get('section_title')
            ))
            return False

        return True


class Scrobbler(Manager):
    tag = 'pts.scrobbler'

    available = []
    enabled = []

########NEW FILE########
__FILENAME__ = scrobbler_logging
from core.eventing import EventManager
from core.helpers import get_pref
from core.logger import Logger
from data.watch_session import WatchSession
from plex.plex_media_server import PlexMediaServer
from plex.plex_metadata import PlexMetadata
from plex.plex_preferences import PlexPreferences
from pts.scrobbler import Scrobbler, ScrobblerMethod


log = Logger('pts.scrobbler_logging')


class LoggingScrobbler(ScrobblerMethod):
    name = 'LoggingScrobbler'

    def __init__(self):
        super(LoggingScrobbler, self).__init__()

        EventManager.subscribe('scrobbler.logging.update', self.update)

    @classmethod
    def test(cls):
        # Try enable logging
        if not PlexPreferences.log_debug(True):
            log.warn('Unable to enable logging')

        # Test if logging is enabled
        if not PlexPreferences.log_debug():
            log.warn('Debug logging not enabled, unable to use logging activity method.')
            return False

        return True

    def create_session(self, info):
        if not info.get('ratingKey'):
            log.warn('Invalid ratingKey provided from activity info')
            return None

        skip = False

        # Client
        client = None
        if info.get('machineIdentifier'):
            client = PlexMediaServer.get_client(info['machineIdentifier'])
        else:
            log.info('No machineIdentifier available, client filtering not available')

        # Metadata
        metadata = None

        try:
            metadata = PlexMetadata.get(info['ratingKey'])

            if metadata:
                metadata = metadata.to_dict()
        except NotImplementedError, e:
            # metadata not supported (music, etc..)
            log.debug('%s, ignoring session' % e.message)
            skip = True

        session = WatchSession.from_info(info, metadata, client)
        session.skip = skip
        session.save()

        return session

    def session_valid(self, session, info):
        if session.item_key != info['ratingKey']:
            log.debug('Invalid Session: Media changed')
            return False

        if session.skip and info.get('state') == 'stopped':
            log.debug('Invalid Session: Media stopped')
            return False

        if not session.metadata:
            if session.skip:
                return True

            log.debug('Invalid Session: Missing metadata')
            return False

        if session.metadata.get('duration', 0) <= 0:
            log.debug('Invalid Session: Invalid duration')
            return False

        return True

    def get_session(self, info):
        session = WatchSession.load('logging-%s' % info.get('machineIdentifier'))

        if not session:
            session = self.create_session(info)

            if not session:
                return None

        if not self.session_valid(session, info):
            session.delete()
            session = None
            log.debug('Session deleted')

        if not session or session.skip:
            return None

        return session

    def valid(self, session):
        # Check filters
        if not self.valid_client(session) or\
           not self.valid_section(session):
            session.skip = True
            session.save()
            return False

        return True

    def update(self, info):
        # Ignore if scrobbling is disabled
        if not get_pref('scrobble'):
            return

        session = self.get_session(info)
        if not session:
            log.trace('Invalid or ignored session, nothing to do')
            return

        # Validate session (check filters)
        if not self.valid(session):
            return

        media_type = session.get_type()

        # Check if we are scrobbling a known media type
        if not media_type:
            log.info('Playing unknown item, will not be scrobbled: "%s"' % session.get_title())
            session.skip = True
            return

        # Calculate progress
        if not self.update_progress(session, info['time']):
            log.warn('Error while updating session progress, queued session to be updated')
            session.update_required = True
            session.save()
            return

        action = self.get_action(session, info['state'])

        if action:
            self.handle_action(session, media_type, action, info['state'])
        else:
            log.debug(self.status_message(session, info.get('state'))('Nothing to do this time for %s'))
            session.save()

        if self.handle_state(session, info['state']) or action:
            session.save()
            Dict.Save()

Scrobbler.register(LoggingScrobbler, weight=1)

########NEW FILE########
__FILENAME__ = scrobbler_websocket
from core.eventing import EventManager
from core.helpers import get_pref
from core.logger import Logger
from data.watch_session import WatchSession
from plex.plex_media_server import PlexMediaServer
from plex.plex_metadata import PlexMetadata
from pts.scrobbler import Scrobbler, ScrobblerMethod


log = Logger('pts.scrobbler_websocket')


class WebSocketScrobbler(ScrobblerMethod):
    name = 'WebSocketScrobbler'

    def __init__(self):
        super(WebSocketScrobbler, self).__init__()

        EventManager.subscribe('notifications.playing', self.update)

    @classmethod
    def test(cls):
        if PlexMediaServer.get_sessions() is None:
            log.info("Error while retrieving sessions, assuming WebSocket method isn't available")
            return False

        server_info = PlexMediaServer.get_info()
        if server_info is None:
            log.info('Error while retrieving server info for testing')
            return False

        multi_user = bool(server_info.get('multiuser', 0))
        if not multi_user:
            log.info("Server info indicates multi-user support isn't available, WebSocket method not available")
            return False

        return True

    def create_session(self, session_key, state):
        """
        :type session_key: str
        :type state: str

        :rtype: WatchSession or None
        """

        log.debug('Creating a WatchSession for the current media')

        skip = False

        info = PlexMediaServer.get_session(session_key)
        if not info:
            return None

        # Client
        player_section = info.findall('Player')
        if len(player_section):
            player_section = player_section[0]

        client = PlexMediaServer.get_client(player_section.get('machineIdentifier'))

        # Metadata
        metadata = None

        try:
            metadata = PlexMetadata.get(info.get('ratingKey'))

            if metadata:
                metadata = metadata.to_dict()
        except NotImplementedError, e:
            # metadata not supported (music, etc..)
            log.debug('%s, ignoring session' % e.message)
            skip = True

        session = WatchSession.from_section(info, state, metadata, client)
        session.skip = skip
        session.save()

        return session

    def update_session(self, session, view_offset):
        log.debug('Trying to update the current WatchSession (session key: %s)' % session.key)

        video_section = PlexMediaServer.get_session(session.key)
        if not video_section:
            log.warn('Session was not found on media server')
            return False

        log.debug('last item key: %s, current item key: %s' % (session.item_key, video_section.get('ratingKey')))

        if session.item_key != video_section.get('ratingKey'):
            log.debug('Invalid Session: Media changed')
            return False

        session.last_view_offset = view_offset
        session.update_required = False

        return True

    def session_valid(self, session):
        if not session.metadata:
            if session.skip:
                return True

            log.debug('Invalid Session: Missing metadata')
            return False

        if session.metadata.get('duration', 0) <= 0:
            log.debug('Invalid Session: Invalid duration')
            return False

        return True

    def get_session(self, session_key, state, view_offset):
        session = WatchSession.load(session_key)

        if not session:
            session = self.create_session(session_key, state)

            if not session:
                return None

        update_session = False

        # Update session when view offset goes backwards
        if session.last_view_offset and session.last_view_offset > view_offset:
            log.debug('View offset has gone backwards (last: %s, cur: %s)' % (
                session.last_view_offset, view_offset
            ))

            update_session = True

        # Update session on missing metadata + session skip
        if not session.metadata and session.skip:
            update_session = True

        # First try update the session if the media hasn't changed
        # otherwise delete the session
        if update_session and not self.update_session(session, view_offset):
            log.debug('Media changed, deleting the session')
            session.delete()
            return None

        # Delete session if invalid
        if not self.session_valid(session):
            session.delete()
            return None

        if session.skip:
            return None

        if state == 'playing' and session.update_required:
            log.debug('Session update required, updating the session...')

            if not self.update_session(session, view_offset):
                log.debug('Media changed, deleting the session')
                session.delete()
                return None

        return session

    def valid(self, session):
        # Check filters
        if not self.valid_user(session) or\
           not self.valid_client(session) or \
           not self.valid_section(session):
            session.skip = True
            session.save()
            return False

        return True

    def update(self, session_key, state, view_offset):
        # Ignore if scrobbling is disabled
        if not get_pref('scrobble'):
            return

        session = self.get_session(session_key, state, view_offset)
        if not session:
            log.trace('Invalid or ignored session, nothing to do')
            return

        # Ignore sessions flagged as 'skip'
        if session.skip:
            return

        # Validate session (check filters)
        if not self.valid(session):
            return

        media_type = session.get_type()

        # Check if we are scrobbling a known media type
        if not media_type:
            log.info('Playing unknown item, will not be scrobbled: "%s"' % session.get_title())
            session.skip = True
            return

        session.last_view_offset = view_offset

        # Calculate progress
        if not self.update_progress(session, view_offset):
            log.warn('Error while updating session progress, queued session to be updated')
            session.update_required = True
            session.save()
            return

        action = self.get_action(session, state)

        if action:
            self.handle_action(session, media_type, action, state)
        else:
            log.debug(self.status_message(session, state)('Nothing to do this time for %s'))
            session.save()

        if self.handle_state(session, state) or action:
            session.save()
            Dict.Save()

Scrobbler.register(WebSocketScrobbler, weight=10)

########NEW FILE########
__FILENAME__ = session_manager
from data.watch_session import WatchSession
from threading import Thread
import traceback
import time
from pts.scrobbler import ScrobblerMethod


class SessionManager(Thread):
    def __init__(self):
        self.active = True

        super(SessionManager, self).__init__()

    def run(self):
        while self.active:
            try:
                self.check_sessions()
            except Exception, ex:
                trace = traceback.format_exc()
                Log.Warn('Exception from SessionManager (%s): %s' % (ex, trace))

            time.sleep(2)

    def check_sessions(self):
        sessions = WatchSession.all()

        if not len(sessions):
            return

        for key, session in sessions:
            self.check_paused(session)

    def check_paused(self, session):
        if session.cur_state != 'paused' or not session.paused_since:
            return

        if session.watching and Datetime.Now() > session.paused_since + Datetime.Delta(seconds=15):
            Log.Debug("%s paused for 15s, watching status cancelled" % session.get_title())
            session.watching = False
            session.save()

            if not self.send_action(session, 'cancelwatching'):
                Log.Info('Failed to cancel the watching status')

    def send_action(self, session, action):
        media_type = session.get_type()
        if not media_type:
            return False

        if ScrobblerMethod.handle_action(session, media_type, action, session.cur_state):
            return False

        Dict.Save()
        return True

    def stop(self):
        self.active = False

########NEW FILE########
__FILENAME__ = manager
from core.eventing import EventManager
from core.helpers import total_seconds, sum, get_pref
from core.logger import Logger
from data.sync_status import SyncStatus
from sync.sync_base import CancelException
from sync.sync_statistics import SyncStatistics
from sync.sync_task import SyncTask
from sync.pull import Pull
from sync.push import Push
from sync.synchronize import Synchronize
from datetime import datetime
import threading
import traceback
import time


log = Logger('sync.manager')

HANDLERS = [Pull, Push, Synchronize]

# Maps interval option labels to their minute values (argh..)
INTERVAL_MAP = {
    'Disabled':   None,
    '15 Minutes': 15,
    '30 Minutes': 30,
    'Hour':       60,
    '3 Hours':    180,
    '6 Hours':    360,
    '12 Hours':   720,
    'Day':        1440,
    'Week':       10080,
}


class SyncManager(object):
    thread = None
    lock = None

    running = False

    cache_id = None
    current = None

    handlers = None
    statistics = None

    @classmethod
    def initialize(cls):
        cls.thread = threading.Thread(target=cls.run, name="SyncManager")
        cls.lock = threading.Lock()

        EventManager.subscribe('notifications.status.scan_complete', cls.scan_complete)
        EventManager.subscribe('sync.get_cache_id', cls.get_cache_id)

        cls.handlers = dict([(h.key, h(cls)) for h in HANDLERS])
        cls.statistics = SyncStatistics(HANDLERS, cls)

    @classmethod
    def get_cache_id(cls):
        return cls.cache_id

    @classmethod
    def get_current(cls):
        current = cls.current

        if not current:
            return None, None

        return current, cls.handlers.get(current.key)

    @classmethod
    def get_status(cls, key, section=None):
        """Retrieve the status of a task

        :rtype : SyncStatus
        """
        if section:
            key = (key, section)

        status = SyncStatus.load(key)

        if not status:
            status = SyncStatus(key)
            status.save()

        return status

    @classmethod
    def reset(cls):
        cls.current = None

    @classmethod
    def start(cls):
        cls.running = True
        cls.thread.start()

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    def acquire(cls):
        cls.lock.acquire()
        log.debug('Acquired work: %s' % cls.current)

    @classmethod
    def release(cls):
        log.debug("Work finished")
        cls.reset()

        cls.lock.release()

    @classmethod
    def check_schedule(cls):
        interval = INTERVAL_MAP.get(Prefs['sync_run_interval'])
        if not interval:
            return False

        status = cls.get_status('synchronize')
        if not status.previous_timestamp:
            return False

        since_run = total_seconds(datetime.utcnow() - status.previous_timestamp) / 60
        if since_run < interval:
            return False

        return cls.trigger_synchronize()

    @classmethod
    def run(cls):
        while cls.running:
            if not cls.current and not cls.check_schedule():
                time.sleep(3)
                continue

            cls.acquire()

            if not cls.run_work():
                if cls.current.stopping:
                    log.info('Syncing task stopped as requested')
                else:
                    log.warn('Error occurred while running work')

            cls.release()

    @classmethod
    def run_work(cls):
        # Get work details
        key = cls.current.key
        kwargs = cls.current.kwargs or {}
        section = kwargs.pop('section', None)

        # Find handler
        handler = cls.handlers.get(key)
        if not handler:
            log.warn('Unknown handler "%s"' % key)
            return False

        log.debug('Processing work with handler "%s" and kwargs: %s' % (key, kwargs))

        # Update cache_id to ensure we trigger new requests
        cls.cache_id = str(time.time())
        success = False

        try:
            success = handler.run(section=section, **kwargs)
        except CancelException, e:
            handler.update_status(False)
            log.info('Task "%s" was cancelled', key)
        except Exception, e:
            handler.update_status(False)

            log.warn('Exception raised in handler for "%s" (%s) %s: %s' % (
                key, type(e), e, traceback.format_exc()
            ))

        # Return task success result
        return success

    @classmethod
    def scan_complete(cls):
        if not get_pref('sync_run_library'):
            log.info('"Run after library updates" not enabled, ignoring')
            return

        cls.trigger_synchronize()

    # Trigger

    @classmethod
    def trigger(cls, key, blocking=False, **kwargs):
        # Ensure sync task isn't already running
        if not cls.lock.acquire(blocking):
            return False

        # Ensure account details are set
        if not get_pref('valid'):
            cls.lock.release()
            return False

        cls.reset()
        cls.current = SyncTask(key, kwargs)

        cls.lock.release()
        return True

    @classmethod
    def trigger_push(cls, section=None):
        return cls.trigger('push', section=section)

    @classmethod
    def trigger_pull(cls):
        return cls.trigger('pull')

    @classmethod
    def trigger_synchronize(cls):
        return cls.trigger('synchronize')

    # Cancel

    @classmethod
    def cancel(cls):
        if not cls.current:
            return False

        cls.current.stopping = True
        return True

########NEW FILE########
__FILENAME__ = pull
from core.helpers import plural, all, json_encode, get_pref
from core.logger import Logger
from plex.plex_media_server import PlexMediaServer
from sync.sync_base import SyncBase
from datetime import datetime


log = Logger('sync.pull')


class Base(SyncBase):
    task = 'pull'

    @staticmethod
    def get_missing(t_items, is_collected=True):
        return dict([
            (t_item.pk, t_item) for t_item in t_items.itervalues()
            if (not is_collected or t_item.is_collected) and not t_item.is_local
        ])

    def watch(self, p_items, t_item):
        if type(p_items) is not list:
            p_items = [p_items]

        if not t_item.is_watched:
            return True

        for p_item in p_items:
            # Ignore already seen movies
            if p_item.seen:
                continue

            PlexMediaServer.scrobble(p_item.rating_key)

        return True

    def rate(self, p_items, t_item):
        if type(p_items) is not list:
            p_items = [p_items]

        if t_item.rating_advanced is None:
            return True

        t_rating = t_item.rating_advanced

        for p_item in p_items:
            # Ignore already rated episodes
            if p_item.user_rating == t_rating:
                continue

            if p_item.user_rating is None or self.rate_conflict(p_item, t_item):
                PlexMediaServer.rate(p_item.rating_key, t_rating)

        return True

    def rate_conflict(self, p_item, t_item):
        status = self.get_status()

        # First run, overwrite with trakt rating
        if status.last_success is None:
            return True

        resolution = get_pref('sync_ratings_conflict')

        if resolution == 'trakt':
            return True

        if resolution == 'latest':
            t_timestamp = datetime.utcfromtimestamp(t_item.rating_timestamp)

            # If trakt rating was created after the last sync, update plex rating
            if t_timestamp > status.last_success:
                return True

        log.info(
            'Conflict when updating rating for item %s (plex: %s, trakt: %s), trakt rating will be changed on next push.',
            p_item.rating_key, p_item.user_rating, t_item.rating_advanced
        )

        return False


class Episode(Base):
    key = 'episode'
    auto_run = False

    def run(self, p_episodes, t_episodes):
        if p_episodes is None:
            return False

        enabled_funcs = self.get_enabled_functions()

        for key, t_episode in t_episodes.items():
            if key is None or key not in p_episodes:
                continue

            t_episode.is_local = True

            # TODO check result
            self.trigger(enabled_funcs, p_episode=p_episodes[key], t_episode=t_episode)

        return True

    def run_watched(self, p_episode, t_episode):
        return self.watch(p_episode, t_episode)

    def run_ratings(self, p_episode, t_episode):
        return self.rate(p_episode, t_episode)


class Show(Base):
    key = 'show'
    children = [Episode]

    def run(self, section=None):
        self.check_stopping()

        enabled_funcs = self.get_enabled_functions()
        if not enabled_funcs:
            log.info('There are no functions enabled, skipping pull.show')
            return True

        p_shows = self.plex.library('show')
        self.save('last_library', repr(p_shows), source='plex')

        # Fetch library, and only get ratings and collection if enabled
        t_shows, t_shows_table = self.trakt.merged('shows', ratings='ratings' in enabled_funcs, collected=True)
        self.save('last_library', repr(t_shows_table), source='trakt')

        if t_shows is None:
            log.warn('Unable to construct merged library from trakt')
            return False

        self.start(len(t_shows_table))

        for x, (key, t_show) in enumerate(t_shows_table.items()):
            self.check_stopping()
            self.progress(x + 1)

            if key is None or key not in p_shows or not t_show.episodes:
                continue

            log.debug('Processing "%s" [%s]', t_show.title, key)

            t_show.is_local = True

            # Trigger show functions
            self.trigger(enabled_funcs, p_shows=p_shows[key], t_show=t_show)

            # Run through each matched show and run episode functions
            for p_show in p_shows[key]:
                self.child('episode').run(
                    p_episodes=self.plex.episodes(p_show.rating_key, p_show),
                    t_episodes=t_show.episodes
                )

        self.finish()
        self.check_stopping()

        # Trigger plex missing show/episode discovery
        self.discover_missing(t_shows)

        log.info('Finished pulling shows from trakt')
        return True

    def discover_missing(self, t_shows):
        # Ensure collection cleaning is enabled
        if not Prefs['sync_clean_collection']:
            return

        log.info('Searching for shows/episodes that are missing from plex')

        # Find collected shows that are missing from Plex
        t_collection_missing = self.get_missing(t_shows, is_collected=False)

        # Discover entire shows missing
        num_shows = 0
        for key, t_show in t_collection_missing.items():
            # Ignore show if there are no collected episodes on trakt
            if all([not e.is_collected for (_, e) in t_show.episodes.items()]):
                continue

            self.store('missing.shows', t_show.to_info())
            num_shows = num_shows + 1

        # Discover episodes missing
        num_episodes = 0
        for key, t_show in t_shows.items():
            if t_show.pk in t_collection_missing:
                continue

            t_episodes_missing = self.get_missing(t_show.episodes)

            if not t_episodes_missing:
                continue

            self.store_episodes(
                'missing.episodes', t_show.to_info(),
                episodes=[x.to_info() for x in t_episodes_missing.itervalues()]
            )

            num_episodes = num_episodes + len(t_episodes_missing)

        log.info(
            'Found %s show%s and %s episode%s missing from plex',
            num_shows, plural(num_shows),
            num_episodes, plural(num_episodes)
        )

    def run_ratings(self, p_shows, t_show):
        return self.rate(p_shows, t_show)


class Movie(Base):
    key = 'movie'

    def run(self, section=None):
        self.check_stopping()

        enabled_funcs = self.get_enabled_functions()
        if not enabled_funcs:
            log.info('There are no functions enabled, skipping pull.movie')
            return True

        p_movies = self.plex.library('movie')
        self.save('last_library', repr(p_movies), source='plex')

        # Fetch library, and only get ratings and collection if enabled
        t_movies, t_movies_table = self.trakt.merged('movies', ratings='ratings' in enabled_funcs, collected=True)
        self.save('last_library', repr(t_movies_table), source='trakt')

        if t_movies is None:
            log.warn('Unable to construct merged library from trakt')
            return False

        self.start(len(t_movies_table))

        for x, (key, t_movie) in enumerate(t_movies_table.items()):
            self.check_stopping()
            self.progress(x + 1)

            if key is None or key not in p_movies:
                continue

            log.debug('Processing "%s" [%s]', t_movie.title, key)
            t_movie.is_local = True

            # TODO check result
            self.trigger(enabled_funcs, p_movies=p_movies[key], t_movie=t_movie)

        self.finish()
        self.check_stopping()

        # Trigger plex missing movie discovery
        self.discover_missing(t_movies)

        log.info('Finished pulling movies from trakt')
        return True

    def discover_missing(self, t_movies):
        # Ensure collection cleaning is enabled
        if not Prefs['sync_clean_collection']:
            return

        log.info('Searching for movies that are missing from plex')

        # Find collected movies that are missing from Plex
        t_collection_missing = self.get_missing(t_movies)

        num_movies = 0
        for key, t_movie in t_collection_missing.items():
            log.debug('Unable to find "%s" [%s] in library', t_movie.title, key)
            self.store('missing.movies', t_movie.to_info())
            num_movies = num_movies + 1

        log.info('Found %s movie%s missing from plex', num_movies, plural(num_movies))

    def run_watched(self, p_movies, t_movie):
        return self.watch(p_movies, t_movie)

    def run_ratings(self, p_movies, t_movie):
        return self.rate(p_movies, t_movie)


class Pull(Base):
    key = 'pull'
    title = 'Pull'
    children = [Show, Movie]
    threaded = True

########NEW FILE########
__FILENAME__ = push
from core.helpers import all, plural, json_encode
from core.logger import Logger
from core.trakt import Trakt
from sync.sync_base import SyncBase


log = Logger('sync.push')


class Base(SyncBase):
    task = 'push'

    def watch(self, key, p_items, t_item, include_identifier=True):
        if type(p_items) is not list:
            p_items = [p_items]

        # Ignore if trakt movie is already watched
        if t_item and t_item.is_watched:
            return True

        # Ignore if none of the plex items are watched
        if all([not x.seen for x in p_items]):
            return True

        # TODO should we instead pick the best result, instead of just the first?
        self.store('watched', self.plex.to_trakt(key, p_items[0], include_identifier))

    def rate(self, key, p_items, t_item, artifact='ratings'):
        if type(p_items) is not list:
            p_items = [p_items]

        # Filter by rated plex items
        p_items = [x for x in p_items if x.user_rating is not None]

        # Ignore if none of the plex items have a rating attached
        if not p_items:
            return True

        # TODO should this be handled differently when there are multiple ratings?
        p_item = p_items[0]

        # Ignore if rating is already on trakt
        if t_item and t_item.rating_advanced == p_item.user_rating:
            return True

        data = self.plex.to_trakt(key, p_item)

        data.update({
            'rating': p_item.user_rating
        })

        self.store(artifact, data)
        return True

    def collect(self, key, p_items, t_item, include_identifier=True):
        if type(p_items) is not list:
            p_items = [p_items]

        # Ignore if trakt movie is already collected
        if t_item and t_item.is_collected:
            return True

        self.store('collected', self.plex.to_trakt(key, p_items[0], include_identifier))
        return True

    @staticmethod
    def log_artifact(action, label, count, level='info'):
        message = '(%s) %s %s item%s' % (
            action, label, count,
            plural(count)
        )

        if level == 'info':
            return log.info(message)
        elif level == 'warn':
            return log.warn(message)

        raise ValueError('Unknown level specified')

    def send(self, action, data):
        response = Trakt.request(action, data, authenticate=True)

        # Log successful items
        if 'rated' in response:
            rated = response.get('rated')
            unrated = response.get('unrated')

            log.info(
                '(%s) Rated %s item%s and un-rated %s item%s',
                action,
                rated, plural(rated),
                unrated, plural(unrated)
            )
        elif 'message' in response:
            log.info('(%s) %s', action, response['message'])
        else:
            self.log_artifact(action, 'Inserted', response.get('inserted'))

        # Log skipped items, if there were any
        skipped = response.get('skipped', 0)

        if skipped > 0:
            self.log_artifact(action, 'Skipped', skipped, level='warn')

    def send_artifact(self, action, key, artifact):
        items = self.artifacts.get(artifact)
        if not items:
            return

        return self.send(action, {key: items})


class Episode(Base):
    key = 'episode'
    auto_run = False

    def run(self, p_episodes, t_episodes, artifacts=None):
        self.reset(artifacts)

        if p_episodes is None:
            return False

        enabled_funcs = self.get_enabled_functions()

        for key, p_episode in p_episodes.items():
            t_episode = t_episodes.get(key)

            # TODO check result
            self.trigger(enabled_funcs, key=key, p_episode=p_episode, t_episode=t_episode)

        return True

    def run_watched(self, key, p_episode, t_episode):
        return self.watch(key, p_episode, t_episode, include_identifier=False)

    def run_ratings(self, key, p_episode, t_episode):
        return self.parent.rate(key, p_episode, t_episode, 'episode_ratings')

    def run_collected(self, key, p_episode, t_episode):
        return self.collect(key, p_episode, t_episode, include_identifier=False)


class Show(Base):
    key = 'show'
    children = [Episode]

    def run(self, section=None, artifacts=None):
        self.reset(artifacts)
        self.check_stopping()

        enabled_funcs = self.get_enabled_functions()
        if not enabled_funcs:
            log.info('There are no functions enabled, skipping push.show')
            return True

        p_shows = self.plex.library('show', section)
        if not p_shows:
            # No items found, no need to continue
            return True

        # Fetch library, and only get ratings and collection if enabled
        t_shows, t_shows_table = self.trakt.merged(
            'shows',
            ratings='ratings' in enabled_funcs,
            collected='collected' in enabled_funcs
        )

        if t_shows_table is None:
            log.warn('Unable to construct merged library from trakt')
            return False

        self.start(len(p_shows))

        for x, (key, p_show) in enumerate(p_shows.items()):
            self.check_stopping()
            self.progress(x + 1)

            t_show = t_shows_table.get(key)

            log.debug('Processing "%s" [%s]', p_show[0].title if p_show else None, key)

            # TODO check result
            self.trigger(enabled_funcs, key=key, p_shows=p_show, t_show=t_show)

            for p_show in p_show:
                self.child('episode').run(
                    p_episodes=self.plex.episodes(p_show.rating_key, p_show),
                    t_episodes=t_show.episodes if t_show else {},
                    artifacts=artifacts
                )

                show = self.plex.to_trakt(key, p_show)

                self.store_episodes('collected', show)
                self.store_episodes('watched', show)

        self.finish()
        self.check_stopping()

        #
        # Push changes to trakt
        #
        for show in self.retrieve('collected'):
            self.send('show/episode/library', show)

        for show in self.retrieve('watched'):
            self.send('show/episode/seen', show)

        self.send_artifact('rate/shows', 'shows', 'ratings')
        self.send_artifact('rate/episodes', 'episodes', 'episode_ratings')

        for show in self.retrieve('missing.shows'):
            self.send('show/unlibrary', show)

        for show in self.retrieve('missing.episodes'):
            self.send('show/episode/unlibrary', show)

        self.save('last_artifacts', json_encode(self.artifacts))

        log.info('Finished pushing shows to trakt')
        return True

    def run_ratings(self, key, p_shows, t_show):
        return self.rate(key, p_shows, t_show)


class Movie(Base):
    key = 'movie'

    def run(self, section=None, artifacts=None):
        self.reset(artifacts)
        self.check_stopping()

        enabled_funcs = self.get_enabled_functions()
        if not enabled_funcs:
            log.info('There are no functions enabled, skipping push.movie')
            return True

        p_movies = self.plex.library('movie', section)
        if not p_movies:
            # No items found, no need to continue
            return True

        # Fetch library, and only get ratings and collection if enabled
        t_movies, t_movies_table = self.trakt.merged(
            'movies',
            ratings='ratings' in enabled_funcs,
            collected='collected' in enabled_funcs
        )

        if t_movies_table is None:
            log.warn('Unable to construct merged library from trakt')
            return False

        self.start(len(p_movies))

        for x, (key, p_movie) in enumerate(p_movies.items()):
            self.check_stopping()
            self.progress(x + 1)

            t_movie = t_movies_table.get(key)

            log.debug('Processing "%s" [%s]', p_movie[0].title if p_movie else None, key)

            # TODO check result
            self.trigger(enabled_funcs, key=key, p_movies=p_movie, t_movie=t_movie)

        self.finish()
        self.check_stopping()

        #
        # Push changes to trakt
        #
        self.send_artifact('movie/seen', 'movies', 'watched')
        self.send_artifact('rate/movies', 'movies', 'ratings')
        self.send_artifact('movie/library', 'movies', 'collected')
        self.send_artifact('movie/unlibrary', 'movies', 'missing.movies')

        self.save('last_artifacts', json_encode(self.artifacts))

        log.info('Finished pushing movies to trakt')
        return True

    def run_watched(self, key, p_movies, t_movie):
        return self.watch(key, p_movies, t_movie)

    def run_ratings(self, key, p_movies, t_movie):
        return self.rate(key, p_movies, t_movie)

    def run_collected(self, key, p_movies, t_movie):
        return self.collect(key, p_movies, t_movie)


class Push(Base):
    key = 'push'
    title = 'Push'
    children = [Show, Movie]
    threaded = True

    def run(self, *args, **kwargs):
        success = super(Push, self).run(*args, **kwargs)

        if kwargs.get('section') is None:
            # Update the status for each section
            for (_, k, _) in self.plex.sections():
                self.update_status(True, start_time=self.start_time, section=k)

        return success

########NEW FILE########
__FILENAME__ = synchronize
from core.logger import Logger
from sync.sync_base import SyncBase


log = Logger('sync.synchronize')


class Synchronize(SyncBase):
    key = 'synchronize'
    title = "Synchronize"

    def run(self, **kwargs):
        self.reset()

        push = self.manager.handlers.get('push')
        pull = self.manager.handlers.get('pull')

        if not push or not pull:
            log.warn("Sync handlers haven't initialized properly, unable to synchronize")
            self.update_status(False)
            return False

        self.check_stopping()

        if not pull.run():
            log.warn("Pull handler failed")
            self.update_status(False)
            return False

        # Store missing media discovery artifacts
        self.store('missing.movies', pull.child('movie').retrieve('missing.movies'), single=True)

        self.store('missing.shows', pull.child('show').retrieve('missing.shows'), single=True)
        self.store('missing.episodes', pull.child('show').retrieve('missing.episodes'), single=True)

        self.check_stopping()

        if not push.run(artifacts=self.artifacts):
            log.warn('Push handler failed')
            self.update_status(False)
            return False

        self.update_status(True)
        return True

########NEW FILE########
__FILENAME__ = sync_base
from core.eventing import EventManager
from core.helpers import all, merge, get_filter, get_pref
from core.logger import Logger
from core.task import Task, CancelException
from core.trakt import Trakt
from plex.plex_library import PlexLibrary
from plex.plex_media_server import PlexMediaServer
from plex.plex_metadata import PlexMetadata
from plex.plex_objects import PlexEpisode
from datetime import datetime


log = Logger('sync.sync_base')


class Base(object):
    @classmethod
    def get_cache_id(cls):
        return EventManager.fire('sync.get_cache_id', single=True)


class PlexInterface(Base):
    @classmethod
    def sections(cls, types=None, keys=None, titles=None):
        # Default to 'titles' filter preference
        if titles is None:
            titles = get_filter('filter_sections')

        return PlexMediaServer.get_sections(
            types, keys, titles,
            cache_id=cls.get_cache_id()
        )

    @classmethod
    def library(cls, types=None, keys=None, titles=None):
        # Default to 'titles' filter preference
        if titles is None:
            titles = get_filter('filter_sections')

        return PlexLibrary.fetch(
            types, keys, titles,
            cache_id=cls.get_cache_id()
        )

    @classmethod
    def episodes(cls, key, parent=None):
        return PlexLibrary.fetch_episodes(key, parent, cache_id=cls.get_cache_id())

    @staticmethod
    def get_root(p_item):
        if isinstance(p_item, PlexEpisode):
            return p_item.parent

        return p_item

    @staticmethod
    def add_identifier(data, p_item):
        return PlexMetadata.add_identifier(data, p_item)

    @classmethod
    def to_trakt(cls, key, p_item, include_identifier=True):
        data = {}

        # Append episode attributes if this is a PlexEpisode
        if isinstance(p_item, PlexEpisode):
            k_season, k_episode = key

            data.update({
                'season': k_season,
                'episode': k_episode
            })

        if include_identifier:
            p_root = cls.get_root(p_item)

            data.update({
                'title': p_root.title,
                'year': p_root.year
            })

            cls.add_identifier(data, p_root)

        return data


class TraktInterface(Base):
    @classmethod
    def merged(cls, media, watched=True, ratings=False, collected=False, extended='min'):
        return Trakt.User.get_merged(media, watched, ratings, collected, extended, cache_id=cls.get_cache_id())


class SyncBase(Base):
    key = None
    task = None
    title = "Unknown"
    children = []

    auto_run = True
    threaded = False

    plex = PlexInterface
    trakt = TraktInterface

    def __init__(self, manager, parent=None):
        self.manager = manager
        self.parent = parent

        # Activate children and create dictionary map
        self.children = dict([(x.key, x(manager, self)) for x in self.children])

        self.start_time = None
        self.artifacts = {}

    @classmethod
    def get_key(cls):
        if cls.task and cls.key and cls.task != cls.key:
            return '%s.%s' % (cls.task, cls.key)

        return cls.key or cls.task

    def reset(self, artifacts=None):
        self.start_time = datetime.utcnow()

        self.artifacts = artifacts.copy() if artifacts else {}

        for child in self.children.itervalues():
            child.reset(artifacts)

    def run(self, *args, **kwargs):
        self.reset(kwargs.get('artifacts'))

        # Trigger handlers and return if there was an error
        if not all(self.trigger(None, *args, **kwargs)):
            self.update_status(False)
            return False

        # Trigger children and return if there was an error
        if not all(self.trigger_children(*args, **kwargs)):
            self.update_status(False)
            return False

        self.update_status(True)
        return True

    def child(self, name):
        return self.children.get(name)

    def get_current(self):
        return self.manager.get_current()

    def is_stopping(self):
        task, _ = self.get_current()

        return task and task.stopping

    def check_stopping(self):
        if self.is_stopping():
            raise CancelException()

    @classmethod
    def get_enabled_functions(cls):
        result = []

        if cls.task in get_pref('sync_watched'):
            result.append('watched')

        if cls.task in get_pref('sync_ratings'):
            result.append('ratings')

        if cls.task in get_pref('sync_collection'):
            result.append('collected')

        return result

    #
    # Trigger
    #

    def trigger(self, funcs=None, *args, **kwargs):
        single = kwargs.pop('single', False)

        if funcs is None:
            funcs = [x[4:] for x in dir(self) if x.startswith('run_')]
        elif type(funcs) is not list:
            funcs = [funcs]

        # Get references to functions
        funcs = [(name, getattr(self, 'run_' + name)) for name in funcs if hasattr(self, 'run_' + name)]

        return self.trigger_run(funcs, single, *args, **kwargs)

    def trigger_children(self, *args, **kwargs):
        single = kwargs.pop('single', False)

        children = [
            (child.key, child.run) for (_, child) in self.children.items()
            if child.auto_run
        ]


        return self.trigger_run(children, single, *args, **kwargs)

    def trigger_run(self, funcs, single, *args, **kwargs):
        if not funcs:
            return []

        if self.threaded:
            tasks = []

            for name, func in funcs:
                task = Task(func, *args, **kwargs)
                tasks.append(task)

                task.spawn('sync.%s.%s' % (self.key, name))

            # Wait until everything is complete
            results = []

            for task in tasks:
                task.wait()
                results.append(task.result)

            return results

        # Run each task and collect results
        results = [func(*args, **kwargs) for (_, func) in funcs]

        if not single:
            return results

        return results[0]

    #
    # Status / Progress
    #

    def start(self, end, start=0):
        EventManager.fire(
            'sync.%s.started' % self.get_key(),
            start=start, end=end
        )

    def progress(self, value):
        EventManager.fire(
            'sync.%s.progress' % self.get_key(),
            value=value
        )

    def finish(self):
        EventManager.fire(
            'sync.%s.finished' % self.get_key()
        )

    def update_status(self, success, end_time=None, start_time=None, section=None):
        if end_time is None:
            end_time = datetime.utcnow()

        # Update task status
        status = self.get_status(section)
        status.update(success, start_time or self.start_time, end_time)

        log.info(
            'Task "%s" finished - success: %s, start: %s, elapsed: %s',
            status.key,
            status.previous_success,
            status.previous_timestamp,
            status.previous_elapsed
        )

    def get_status(self, section=None):
        """Retrieve the status of the current syncing task.

        :rtype : SyncStatus
        """
        if section is None:
            # Determine section from current state
            task, _ = self.get_current()
            if task is None:
                return None

            section = task.kwargs.get('section')

        return self.manager.get_status(self.task or self.key, section)

    #
    # Artifacts
    #

    def retrieve(self, key, single=False):
        if single:
            return self.artifacts.get(key)

        return self.artifacts.get(key, [])

    def store(self, key, data, single=False):
        if single:
            self.artifacts[key] = data
            return

        if key not in self.artifacts:
            self.artifacts[key] = []

        self.artifacts[key].append(data)

    def store_episodes(self, key, show, episodes=None, artifact=None):
        if episodes is None:
            episodes = self.child('episode').artifacts.get(artifact or key)

        if episodes is None:
            return

        self.store(key, merge({'episodes': episodes}, show))

    # TODO switch to a streamed format (to avoid the MemoryError)
    def save(self, group, data, source=None):
        name = '%s.%s' % (group, self.key)

        if source:
            name += '.%s' % source

        try:
            log.debug('Saving artifacts to "%s.json"', name)
            Data.Save(name + '.json', repr(data))
        except MemoryError:
            log.warn('Unable to save artifacts, out of memory')

########NEW FILE########
__FILENAME__ = sync_statistics
from core.helpers import total_seconds, sum
from core.eventing import EventManager
from core.logger import Logger
from core.numeric import ema
from sync.sync_task import SyncTaskStatistics
from datetime import datetime

log = Logger('sync.sync_statistics')


MESSAGES = {
    'pull.show': 'Pulling shows from trakt',
    'push.show': 'Pushing shows to trakt',

    'pull.movie': 'Pulling movies from trakt',
    'push.movie': 'Pushing shows to trakt'
}


class SyncStatistics(object):
    def __init__(self, handlers, manager):
        self.manager = manager

        self.active = []

        for h in handlers:
            self.bind(h)

    def bind(self, task):
        key = task.get_key()

        EventManager.subscribe(
            'sync.%s.started' % key,
            lambda start, end: self.started(key, start, end)
        )

        EventManager.subscribe(
            'sync.%s.progress' % key,
            lambda value: self.progress(key, value)
        )

        EventManager.subscribe(
            'sync.%s.finished' % key,
            lambda: self.finished(key)
        )

        # Bind child progress events
        for child in task.children:
            self.bind(child)

    def reset(self):
        if not self.manager.current:
            return

        self.manager.current.statistics = SyncTaskStatistics()

    def update(self):
        if not self.manager.current or not self.active:
            return

        st = self.manager.current.statistics
        if not st:
            return

        st.message = MESSAGES.get(self.key)

    def started(self, key, start, end):
        self.reset()

        self.active.append((key, start, end))
        self.update()

    def progress(self, key, value):
        if not self.manager.current:
            return

        if key != self.key:
            return

        stat = self.manager.current.statistics

        if not stat or self.offset is None:
            return

        value += self.offset
        progress = float(value) / self.end

        self.calculate_timing(stat, progress)

        #log.debug(
        #    '[%s] progress: %02d%%, estimated time remaining: ~%s seconds',
        #    key, progress * 100,
        #    round(stat.seconds_remaining, 2) if stat.seconds_remaining else '?'
        #)

        stat.progress = progress
        stat.last_update = datetime.utcnow()

    def calculate_timing(self, stat, cur_progress):
        if not stat.last_update:
            return

        progress_delta = cur_progress - (stat.progress or 0)
        delta_seconds = total_seconds(datetime.utcnow() - stat.last_update)

        # Calculate current speed (in [percent progress]/sec)
        cur_speed = delta_seconds / (progress_delta * 100)

        if stat.per_perc is None:
            # Start initially at first speed value
            stat.per_perc = cur_speed
        else:
            # Calculate EMA speed
            stat.per_perc = ema(cur_speed, stat.per_perc)

        # Calculate estimated time remaining
        stat.seconds_remaining = ((1 - cur_progress) * 100) * stat.per_perc

    def finished(self, key):
        self.reset()

        # Search for key in 'active' list and remove it
        for x, (k, _, _) in enumerate(self.active):
            if k != key:
                continue

            self.active.pop(x)
            break

        # Update task status (message)
        self.update()

    #
    # Active task properties
    #

    @property
    def key(self):
        if not self.active:
            return None

        key, _, _ = self.active[-1]

        return key

    @property
    def offset(self):
        if not self.active:
            return None

        _, start, _ = self.active[-1]

        return 0 - start

    @property
    def start(self):
        if not self.active:
            return None

        _, start, _ = self.active[-1]

        return start + self.offset

    @property
    def end(self):
        if not self.active:
            return None

        _, _, end = self.active[-1]

        return end + self.offset

########NEW FILE########
__FILENAME__ = sync_task
class SyncTask(object):
    def __init__(self, key, kwargs):
        self.key = key
        self.kwargs = kwargs

        self.statistics = SyncTaskStatistics()

        self.start_time = None
        self.end_time = None
        self.success = None

        self.stopping = False


class SyncTaskStatistics(object):
    def __init__(self):
        self.message = None

        self.progress = None
        self.seconds_remaining = None

        self.per_perc = None
        self.plots = []

        self.last_update = None

########NEW FILE########
__FILENAME__ = ago
from datetime import datetime
from datetime import timedelta

def delta2dict( delta ):
    """Accepts a delta, returns a dictionary of units"""
    delta = abs( delta )
    return { 
        'year'   : delta.days / 365 ,
        'day'    : delta.days % 365 ,
        'hour'   : delta.seconds / 3600 ,
        'minute' : (delta.seconds / 60) % 60 ,
        'second' : delta.seconds % 60 ,
        'microsecond' : delta.microseconds
    }

def human(dt, precision=2, past_tense='%s ago', future_tense='in %s'):
    """Accept a datetime or timedelta, return a human readable delta string"""
    delta = dt
    if type(dt) is not type(timedelta()):
        delta = datetime.now() - dt
     
    the_tense = past_tense
    if delta < timedelta(0):
        the_tense = future_tense

    d = delta2dict( delta )
    hlist = [] 
    count = 0
    units = ( 'year', 'day', 'hour', 'minute', 'second', 'microsecond' )
    for unit in units:
        if count >= precision: break # met precision
        if d[ unit ] == 0: continue # skip 0's
        s = '' if d[ unit ] == 1 else 's' # handle plurals
        hlist.append( '%s %s%s' % ( d[unit], unit, s ) )
        count += 1
    human_delta = ', '.join( hlist )
    return the_tense % human_delta


########NEW FILE########
__FILENAME__ = asio
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from asio_base import SEEK_ORIGIN_CURRENT
from asio_windows import WindowsASIO
from asio_posix import PosixASIO
import sys
import os


class ASIO(object):
    platform_handler = None

    @classmethod
    def get_handler(cls):
        if cls.platform_handler:
            return cls.platform_handler

        if os.name == 'nt':
            cls.platform_handler = WindowsASIO
        elif os.name == 'posix':
            cls.platform_handler = PosixASIO
        else:
            raise NotImplementedError()

        return cls.platform_handler

    @classmethod
    def open(cls, file_path, opener=True, parameters=None):
        """Open file

        :type file_path: str

        :param opener: Use FileOpener, for use with the 'with' statement
        :type opener: bool

        :rtype: BaseFile
        """
        if not parameters:
            parameters = OpenParameters()


        if opener:
            return FileOpener(file_path, parameters)

        return ASIO.get_handler().open(
            file_path,
            parameters=parameters.handlers.get(ASIO.get_handler())
        )


class OpenParameters(object):
    def __init__(self):
        self.handlers = {}

        # Update handler_parameters with defaults
        self.posix()
        self.windows()

    def posix(self, mode=None, buffering=None):
        """
        :type mode: str
        :type buffering: int
        """
        self.handlers.update({PosixASIO: {
            'mode': mode,
            'buffering': buffering
        }})

    def windows(self,
                desired_access=WindowsASIO.GenericAccess.READ,
                share_mode=WindowsASIO.ShareMode.ALL,
                creation_disposition=WindowsASIO.CreationDisposition.OPEN_EXISTING,
                flags_and_attributes=0):

        """
        :param desired_access: WindowsASIO.DesiredAccess
        :type desired_access: int

        :param share_mode: WindowsASIO.ShareMode
        :type share_mode: int

        :param creation_disposition: WindowsASIO.CreationDisposition
        :type creation_disposition: int

        :param flags_and_attributes: WindowsASIO.Attribute, WindowsASIO.Flag
        :type flags_and_attributes: int
        """

        self.handlers.update({WindowsASIO: {
            'desired_access': desired_access,
            'share_mode': share_mode,
            'creation_disposition': creation_disposition,
            'flags_and_attributes': flags_and_attributes
        }})


class FileOpener(object):
    def __init__(self, file_path, parameters=None):
        self.file_path = file_path
        self.parameters = parameters

        self.file = None

    def __enter__(self):
        self.file = ASIO.get_handler().open(
            self.file_path,
            self.parameters.handlers.get(ASIO.get_handler())
        )

        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.file:
            return

        self.file.close()
        self.file = None


def read(path):
    f = ASIO.open(path, opener=False)
    orig_path = f.get_path()

    size = f.get_size()
    print "Seeking to end, %s" % size
    print f.seek(size, SEEK_ORIGIN_CURRENT)

    while True:
        line = f.read_line(timeout=1, timeout_type='return')
        if not line and f.get_path() != orig_path:
            f.close()
            return

        print line

    f.close()

if __name__ == '__main__':
    log_path_components = ['Plex Media Server', 'Logs', 'Plex Media Server.log']

    path = None

    if len(sys.argv) >= 2:
        path = sys.argv[1]
    else:
        base_path = None

        if os.name == 'nt':
            base_path = os.environ.get('LOCALAPPDATA')
        elif os.name == 'posix':
            base_path = '/var/lib/plexmediaserver/Library/Application Support'

        path = os.path.join(base_path, *log_path_components)

    print 'Path: "%s"' % path

    if not os.path.exists(path):
        print 'File at "%s" not found' % path
        path = None

    if not path:
        print 'Unknown path for "%s"' % os.name
        exit()

    while True:
        read(path)
        print 'file timeout, re-opening'

########NEW FILE########
__FILENAME__ = asio_base
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

DEFAULT_BUFFER_SIZE = 4096


SEEK_ORIGIN_BEGIN = 0
SEEK_ORIGIN_CURRENT = 1
SEEK_ORIGIN_END = 2


class ReadTimeoutError(Exception):
    pass


class BaseASIO(object):
    @classmethod
    def open(cls, file_path, parameters=None):
        raise NotImplementedError()

    @classmethod
    def get_size(cls, fp):
        raise NotImplementedError()

    @classmethod
    def get_path(cls, fp):
        raise NotImplementedError()

    @classmethod
    def seek(cls, fp, pointer, distance):
        raise NotImplementedError()

    @classmethod
    def read(cls, fp, buf_size=DEFAULT_BUFFER_SIZE):
        raise NotImplementedError()

    @classmethod
    def close(cls, fp):
        raise NotImplementedError()


class BaseFile(object):
    platform_handler = None

    def get_handler(self):
        """
        :rtype: BaseASIO
        """
        if not self.platform_handler:
            raise ValueError()

        return self.platform_handler

    def get_size(self):
        """Get the current file size

        :rtype: int
        """
        return self.get_handler().get_size(self)

    def get_path(self):
        """Get the path of this file

        :rtype: str
        """
        return self.get_handler().get_path(self)

    def seek(self, offset, origin):
        """Sets a reference point of a file to the given value.

        :param offset: The point relative to origin to move
        :type offset: int

        :param origin: Reference point to seek (SEEK_ORIGIN_BEGIN, SEEK_ORIGIN_CURRENT, SEEK_ORIGIN_END)
        :type origin: int
        """
        return self.get_handler().seek(self, offset, origin)

    def read(self, buf_size=DEFAULT_BUFFER_SIZE):
        """Read a block of characters from the file

        :type buf_size: int
        :rtype: str
        """
        return self.get_handler().read(self, buf_size)

    def read_line(self, timeout=None, timeout_type='exception', empty_sleep=1000):
        """Read a single line from the file

        :rtype: str
        """

        stale_since = None
        line_buf = ""

        while not len(line_buf) or line_buf[-1] != '\n':
            ch = self.read(1)

            if not ch:
                if timeout:
                    # Check if we have exceeded the timeout
                    if stale_since and (time.time() - stale_since) > timeout:
                        # Timeout occurred, return the specified result
                        if timeout_type == 'exception':
                            raise ReadTimeoutError()
                        elif timeout_type == 'return':
                            return None
                        else:
                            raise ValueError('Unknown timeout_type "%s"' % timeout_type)

                    # Update stale_since when we hit 'None' reads
                    if not stale_since:
                        stale_since = time.time()

                time.sleep(empty_sleep / 1000)

                continue
            elif timeout:
                # Reset stale_since as we received a character
                stale_since = None

            line_buf += ch

        return line_buf[:-1]

    def close(self):
        """Close the file handle"""
        return self.get_handler().close(self)

########NEW FILE########
__FILENAME__ = asio_posix
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from asio_base import BaseASIO, DEFAULT_BUFFER_SIZE, BaseFile
import sys
import os

if os.name == 'posix':
    import select

    # fcntl is only required on darwin
    if sys.platform == 'darwin':
        import fcntl

F_GETPATH = 50


class PosixASIO(BaseASIO):
    @classmethod
    def open(cls, file_path, parameters=None):
        """
        :type file_path: str
        :rtype: PosixFile
        """
        if not parameters:
            parameters = {}

        if not parameters.get('mode'):
            parameters.pop('mode')

        if not parameters.get('buffering'):
            parameters.pop('buffering')

        fd = os.open(file_path, os.O_RDONLY | os.O_NONBLOCK)

        return PosixFile(fd)

    @classmethod
    def get_size(cls, fp):
        """
        :type fp: PosixFile
        :rtype: int
        """
        return os.fstat(fp.fd).st_size

    @classmethod
    def get_path(cls, fp):
        """
        :type fp: PosixFile
        :rtype: int
        """

        # readlink /dev/fd fails on darwin, so instead use fcntl F_GETPATH
        if sys.platform == 'darwin':
            return fcntl.fcntl(fp.fd, F_GETPATH, '\0' * 1024).rstrip('\0')

        # Use /proc/self/fd if available
        if os.path.lexists("/proc/self/fd/%s" % fp.fd):
            return os.readlink("/proc/self/fd/%s" % fp.fd)

        # Fallback to /dev/fd
        return os.readlink("/dev/fd/%s" % fp.fd)

    @classmethod
    def seek(cls, fp, offset, origin):
        """
        :type fp: PosixFile
        :type offset: int
        :type origin: int
        """
        os.lseek(fp.fd, offset, origin)

    @classmethod
    def read(cls, fp, buf_size=DEFAULT_BUFFER_SIZE):
        """
        :type fp: PosixFile
        :type buf_size: int
        :rtype: str
        """
        r, w, x = select.select([fp.fd], [], [], 5)

        if r:
            return os.read(fp.fd, buf_size)

        return None

    @classmethod
    def close(cls, fp):
        """
        :type fp: PosixFile
        """
        os.close(fp.fd)


class PosixFile(BaseFile):
    platform_handler = PosixASIO

    def __init__(self, fd):
        """
        :type file_object: FileIO
        """
        self.fd = fd

    def __str__(self):
        return "<asio_posix.PosixFile file: %s>" % self.fd

########NEW FILE########
__FILENAME__ = asio_windows
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from asio_base import BaseASIO, BaseFile, DEFAULT_BUFFER_SIZE
import os

NULL = 0

if os.name == 'nt':
    from asio_windows_interop import WindowsInterop


class WindowsASIO(BaseASIO):
    @classmethod
    def open(cls, file_path, parameters=None):
        """
        :type file_path: str
        :rtype: WindowsFile
        """
        if not parameters:
            parameters = {}

        return WindowsFile(WindowsInterop.create_file(
            file_path,
            parameters.get('desired_access', WindowsASIO.GenericAccess.READ),
            parameters.get('share_mode', WindowsASIO.ShareMode.ALL),
            parameters.get('creation_disposition', WindowsASIO.CreationDisposition.OPEN_EXISTING),
            parameters.get('flags_and_attributes', NULL)
        ))

    @classmethod
    def get_size(cls, fp):
        """
        :type fp: WindowsFile:
        :rtype: int
        """
        return WindowsInterop.get_file_size(fp.handle)

    @classmethod
    def get_path(cls, fp):
        """
        :type fp: WindowsFile:
        :rtype: str
        """

        if not fp.file_map:
            fp.file_map = WindowsInterop.create_file_mapping(fp.handle, WindowsASIO.Protection.READONLY)

        if not fp.map_view:
            fp.map_view = WindowsInterop.map_view_of_file(fp.file_map, WindowsASIO.FileMapAccess.READ, 1)

        file_name = WindowsInterop.get_mapped_file_name(fp.map_view)

        return file_name

    @classmethod
    def seek(cls, fp, offset, origin):
        """
        :type fp: WindowsFile
        :type offset: int
        :type origin: int
        :rtype: int
        """

        return WindowsInterop.set_file_pointer(
            fp.handle,
            offset,
            origin
        )

    @classmethod
    def read(cls, fp, buf_size=DEFAULT_BUFFER_SIZE):
        """
        :type fp: WindowsFile
        :type buf_size: int
        :rtype: str
        """
        return WindowsInterop.read_file(fp.handle, buf_size)

    @classmethod
    def close(cls, fp):
        """
        :type fp: WindowsFile
        :rtype: bool
        """
        if fp.map_view:
            WindowsInterop.unmap_view_of_file(fp.map_view)

        if fp.file_map:
            WindowsInterop.close_handle(fp.file_map)

        return bool(WindowsInterop.close_handle(fp.handle))

    class GenericAccess(object):
        READ = 0x80000000
        WRITE = 0x40000000
        EXECUTE = 0x20000000
        ALL = 0x10000000

    class ShareMode(object):
        READ = 0x00000001
        WRITE = 0x00000002
        DELETE = 0x00000004
        ALL = READ | WRITE | DELETE

    class CreationDisposition(object):
        CREATE_NEW = 1
        CREATE_ALWAYS = 2
        OPEN_EXISTING = 3
        OPEN_ALWAYS = 4
        TRUNCATE_EXISTING = 5

    class Attribute(object):
        READONLY = 0x00000001
        HIDDEN = 0x00000002
        SYSTEM = 0x00000004
        DIRECTORY = 0x00000010
        ARCHIVE = 0x00000020
        DEVICE = 0x00000040
        NORMAL = 0x00000080
        TEMPORARY = 0x00000100
        SPARSE_FILE = 0x00000200
        REPARSE_POINT = 0x00000400
        COMPRESSED = 0x00000800
        OFFLINE = 0x00001000
        NOT_CONTENT_INDEXED = 0x00002000
        ENCRYPTED = 0x00004000

    class Flag(object):
        WRITE_THROUGH = 0x80000000
        OVERLAPPED = 0x40000000
        NO_BUFFERING = 0x20000000
        RANDOM_ACCESS = 0x10000000
        SEQUENTIAL_SCAN = 0x08000000
        DELETE_ON_CLOSE = 0x04000000
        BACKUP_SEMANTICS = 0x02000000
        POSIX_SEMANTICS = 0x01000000
        OPEN_REPARSE_POINT = 0x00200000
        OPEN_NO_RECALL = 0x00100000
        FIRST_PIPE_INSTANCE = 0x00080000

    class Protection(object):
        NOACCESS = 0x01
        READONLY = 0x02
        READWRITE = 0x04
        WRITECOPY = 0x08
        EXECUTE = 0x10
        EXECUTE_READ = 0x20,
        EXECUTE_READWRITE = 0x40
        EXECUTE_WRITECOPY = 0x80
        GUARD = 0x100
        NOCACHE = 0x200
        WRITECOMBINE = 0x400

    class FileMapAccess(object):
        COPY = 0x0001
        WRITE = 0x0002
        READ = 0x0004
        ALL_ACCESS = 0x001f
        EXECUTE = 0x0020


class WindowsFile(BaseFile):
    platform_handler = WindowsASIO

    def __init__(self, handle):
        self.handle = handle

        self.file_map = None
        self.map_view = None

    def __str__(self):
        return "<asio_windows.WindowsFile file: %s>" % self.handle

########NEW FILE########
__FILENAME__ = asio_windows_interop
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ctypes.wintypes import *
from ctypes import *


CreateFileW = windll.kernel32.CreateFileW
CreateFileW.argtypes = (LPCWSTR, DWORD, DWORD, c_void_p, DWORD, DWORD, HANDLE)
CreateFileW.restype = HANDLE

ReadFile = windll.kernel32.ReadFile
ReadFile.argtypes = (HANDLE, c_void_p, DWORD, POINTER(DWORD), HANDLE)
ReadFile.restype = BOOL


NULL = 0
MAX_PATH = 260
DEFAULT_BUFFER_SIZE = 4096
LPSECURITY_ATTRIBUTES = c_void_p


class WindowsInterop(object):
    @classmethod
    def create_file(cls, path, desired_access, share_mode, creation_disposition, flags_and_attributes):
        h = CreateFileW(
            path,
            desired_access,
            share_mode,
            NULL,
            creation_disposition,
            flags_and_attributes,
            NULL
        )

        error = GetLastError()
        if error != 0:
            raise Exception('[WindowsASIO.open] "%s"' % FormatError(error))

        return h

    @classmethod
    def read_file(cls, handle, buf_size=DEFAULT_BUFFER_SIZE):
        buf = create_string_buffer(buf_size)
        bytes_read = c_ulong(0)

        success = ReadFile(handle, buf, buf_size, byref(bytes_read), NULL)

        error = GetLastError()
        if not success and error:
            raise Exception('[WindowsInterop.read_file] (%s) "%s"' % (error, FormatError(error)))

        # Return if we have a valid buffer
        if success and bytes_read.value:
            return buf.value

        return None

    @classmethod
    def set_file_pointer(cls, handle, distance, method):
        pos_high = DWORD(NULL)

        result = windll.kernel32.SetFilePointer(
            handle,
            c_ulong(distance),
            byref(pos_high),
            DWORD(method)
        )

        if result == -1:
            raise Exception('[WindowsASIO.seek] INVALID_SET_FILE_POINTER: "%s"' % FormatError(GetLastError()))

        return result

    @classmethod
    def get_file_size(cls, handle):
        return windll.kernel32.GetFileSize(
            handle,
            DWORD(NULL)
        )

    @classmethod
    def close_handle(cls, handle):
        return windll.kernel32.CloseHandle(handle)

    @classmethod
    def create_file_mapping(cls, handle, protect, maximum_size_high=0, maximum_size_low=1):
        return HANDLE(windll.kernel32.CreateFileMappingW(
            handle,
            LPSECURITY_ATTRIBUTES(NULL),
            DWORD(protect),
            DWORD(maximum_size_high),
            DWORD(maximum_size_low),
            LPCSTR(NULL)
        ))

    @classmethod
    def map_view_of_file(cls, map_handle, desired_access, num_bytes, file_offset_high=0, file_offset_low=0):
        return HANDLE(windll.kernel32.MapViewOfFile(
            map_handle,
            DWORD(desired_access),
            DWORD(file_offset_high),
            DWORD(file_offset_low),
            num_bytes
        ))

    @classmethod
    def unmap_view_of_file(cls, view_handle):
        return windll.kernel32.UnmapViewOfFile(view_handle)

    @classmethod
    def get_mapped_file_name(cls, view_handle, translate_device_name=True):
        buf = create_string_buffer(MAX_PATH + 1)

        result = windll.psapi.GetMappedFileNameW(
            cls.get_current_process(),
            view_handle,
            buf,
            MAX_PATH
        )

        # Raise exception on error
        error = GetLastError()
        if result == 0:
            raise Exception(FormatError(error))

        # Retrieve a clean file name (skipping over NUL bytes)
        file_name = cls.clean_buffer_value(buf)

        # If we are not translating the device name return here
        if not translate_device_name:
            return file_name

        drives = cls.get_logical_drive_strings()

        # Find the drive matching the file_name device name
        translated = False
        for drive in drives:
            device_name = cls.query_dos_device(drive)

            if file_name.startswith(device_name):
                file_name = drive + file_name[len(device_name):]
                translated = True
                break

        if not translated:
            raise Exception('Unable to translate device name')

        return file_name

    @classmethod
    def get_logical_drive_strings(cls, buf_size=512):
        buf = create_string_buffer(buf_size)

        result = windll.kernel32.GetLogicalDriveStringsW(buf_size, buf)

        error = GetLastError()
        if result == 0:
            raise Exception(FormatError(error))

        drive_strings = cls.clean_buffer_value(buf)
        return [dr for dr in drive_strings.split('\\') if dr != '']

    @classmethod
    def query_dos_device(cls, drive, buf_size=MAX_PATH):
        buf = create_string_buffer(buf_size)

        result = windll.kernel32.QueryDosDeviceA(
            drive,
            buf,
            buf_size
        )

        error = GetLastError()
        if result == 0:
            print Exception('%s (%s)' % (FormatError(error), error))

        return cls.clean_buffer_value(buf)

    @classmethod
    def get_current_process(cls):
        return HANDLE(windll.kernel32.GetCurrentProcess())

    @classmethod
    def clean_buffer_value(cls, buf):
        value = ""

        for ch in buf.raw:
            if ord(ch) != 0:
                value += ch

        return value

########NEW FILE########
__FILENAME__ = compat
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import itertools


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

basestring = basestring if PY2 else str

if PY3:
    itertools.izip_longest = itertools.zip_longest

########NEW FILE########
__FILENAME__ = constraint
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class CaptureConstraint(object):
    def __init__(self, capture_group, constraint_type, comparisons=None, target=None, **kwargs):
        """Capture constraint object

        :type capture_group: CaptureGroup
        """

        self.capture_group = capture_group

        self.constraint_type = constraint_type
        self.target = target

        self.comparisons = comparisons if comparisons else []
        self.kwargs = {}

        for orig_key, value in kwargs.items():
            key = orig_key.split('__')
            if len(key) != 2:
                self.kwargs[orig_key] = value
                continue
            name, method = key

            method = 'constraint_match_' + method
            if not hasattr(self, method):
                self.kwargs[orig_key] = value
                continue

            self.comparisons.append((name, getattr(self, method), value))

    def execute(self, parent_node, node, **kwargs):
        func_name = 'constraint_%s' % self.constraint_type

        if hasattr(self, func_name):
            return getattr(self, func_name)(parent_node, node, **kwargs)

        raise ValueError('Unknown constraint type "%s"' % self.constraint_type)

    #
    # Node Matching
    #

    def constraint_match(self, parent_node, node):
        results = []
        total_weight = 0

        for name, method, argument in self.comparisons:
            weight, success = method(node, name, argument)
            total_weight += weight
            results.append(success)

        return total_weight / (float(len(results)) or 1), all(results) if len(results) > 0 else False

    def constraint_match_eq(self, node, name, expected):
        if not hasattr(node, name):
            return 1.0, False

        return 1.0, getattr(node, name) == expected

    def constraint_match_re(self, node, name, arg):
        # Node match
        if name == 'node':
            group, minimum_weight = arg if type(arg) is tuple and len(arg) > 1 else (arg, 0)

            weight, match, num_fragments = self.capture_group.parser.matcher.fragment_match(node, group)
            return weight, weight > minimum_weight

        # Regex match
        if type(arg).__name__ == 'SRE_Pattern':
            return 1.0, arg.match(getattr(node, name)) is not None

        # Value match
        if hasattr(node, name):
            match = self.capture_group.parser.matcher.value_match(getattr(node, name), arg, single=True)
            return 1.0, match is not None

        raise ValueError("Unknown constraint match type '%s'" % name)

    #
    # Result
    #

    def constraint_result(self, parent_node, fragment):
        ctag = self.kwargs.get('tag')
        if not ctag:
            return 0, False

        ckey = self.kwargs.get('key')

        for tag, result in parent_node.captured():
            if tag != ctag:
                continue

            if not ckey or ckey in result.keys():
                return 1.0, True

        return 0.0, False

    #
    # Failure
    #

    def constraint_failure(self, parent_node, fragment, match):
        if not match or not match.success:
            return 1.0, True

        return 0, False

    #
    # Success
    #

    def constraint_success(self, parent_node, fragment, match):
        if match and match.success:
            return 1.0, True

        return 0, False

    def __repr__(self):
        return "CaptureConstraint(comparisons=%s)" % repr(self.comparisons)

########NEW FILE########
__FILENAME__ = group
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from logr import Logr
from caper import CaperClosure, CaperFragment
from caper.helpers import clean_dict
from caper.result import CaperFragmentNode, CaperClosureNode
from caper.step import CaptureStep
from caper.constraint import CaptureConstraint


class CaptureGroup(object):
    def __init__(self, parser, result):
        """Capture group object

        :type parser: caper.parsers.base.Parser
        :type result: caper.result.CaperResult
        """

        self.parser = parser
        self.result = result

        #: @type: list of CaptureStep
        self.steps = []

        #: type: str
        self.step_source = None

        #: @type: list of CaptureConstraint
        self.pre_constraints = []

        #: :type: list of CaptureConstraint
        self.post_constraints = []

    def capture_fragment(self, tag, regex=None, func=None, single=True, **kwargs):
        Logr.debug('capture_fragment("%s", "%s", %s, %s)', tag, regex, func, single)

        if self.step_source != 'fragment':
            if self.step_source is None:
                self.step_source = 'fragment'
            else:
                raise ValueError("Unable to mix fragment and closure capturing in a group")

        self.steps.append(CaptureStep(
            self, tag,
            'fragment',
            regex=regex,
            func=func,
            single=single,
            **kwargs
        ))

        return self

    def capture_closure(self, tag, regex=None, func=None, single=True, **kwargs):
        Logr.debug('capture_closure("%s", "%s", %s, %s)', tag, regex, func, single)

        if self.step_source != 'closure':
            if self.step_source is None:
                self.step_source = 'closure'
            else:
                raise ValueError("Unable to mix fragment and closure capturing in a group")

        self.steps.append(CaptureStep(
            self, tag,
            'closure',
            regex=regex,
            func=func,
            single=single,
            **kwargs
        ))

        return self

    def until_closure(self, **kwargs):
        self.pre_constraints.append(CaptureConstraint(self, 'match', target='closure', **kwargs))

        return self

    def until_fragment(self, **kwargs):
        self.pre_constraints.append(CaptureConstraint(self, 'match', target='fragment', **kwargs))

        return self

    def until_result(self, **kwargs):
        self.pre_constraints.append(CaptureConstraint(self, 'result', **kwargs))

        return self

    def until_failure(self, **kwargs):
        self.post_constraints.append(CaptureConstraint(self, 'failure', **kwargs))

        return self

    def until_success(self, **kwargs):
        self.post_constraints.append(CaptureConstraint(self, 'success', **kwargs))

        return self

    def parse_subject(self, parent_head, subject):
        Logr.debug("parse_subject (%s) subject: %s", self.step_source, repr(subject))

        if type(subject) is CaperClosure:
            return self.parse_closure(parent_head, subject)

        if type(subject) is CaperFragment:
            return self.parse_fragment(parent_head, subject)

        raise ValueError('Unknown subject (%s)', subject)

    def parse_fragment(self, parent_head, subject):
        parent_node = parent_head[0] if type(parent_head) is list else parent_head

        nodes, match = self.match(parent_head, parent_node, subject)

        # Capturing broke on constraint, return now
        if not match:
            return nodes

        Logr.debug('created fragment node with subject.value: "%s"' % subject.value)

        result = [CaperFragmentNode(
            parent_node.closure,
            list(subject.take_right(match.num_fragments)),
            parent_head,
            match
        )]

        # Branch if the match was indefinite (weight below 1.0)
        if match.result and match.weight < 1.0:
            if match.num_fragments == 1:
                result.append(CaperFragmentNode(parent_node.closure, [subject], parent_head))
            else:
                nodes.append(CaperFragmentNode(parent_node.closure, [subject], parent_head))

        nodes.append(result[0] if len(result) == 1 else result)

        return nodes

    def parse_closure(self, parent_head, subject):
        parent_node = parent_head[0] if type(parent_head) is list else parent_head

        nodes, match = self.match(parent_head, parent_node, subject)

        # Capturing broke on constraint, return now
        if not match:
            return nodes

        Logr.debug('created closure node with subject.value: "%s"' % subject.value)

        result = [CaperClosureNode(
            subject,
            parent_head,
            match
        )]

        # Branch if the match was indefinite (weight below 1.0)
        if match.result and match.weight < 1.0:
            if match.num_fragments == 1:
                result.append(CaperClosureNode(subject, parent_head))
            else:
                nodes.append(CaperClosureNode(subject, parent_head))

        nodes.append(result[0] if len(result) == 1 else result)

        return nodes

    def match(self, parent_head, parent_node, subject):
        nodes = []

        # Check pre constaints
        broke, definite = self.check_constraints(self.pre_constraints, parent_head, subject)

        if broke:
            nodes.append(parent_head)

            if definite:
                return nodes, None

        # Try match subject against the steps available
        match = None

        for step in self.steps:
            if step.source == 'closure' and type(subject) is not CaperClosure:
                pass
            elif step.source == 'fragment' and type(subject) is CaperClosure:
                Logr.debug('Closure encountered on fragment step, jumping into fragments')
                return [CaperClosureNode(subject, parent_head, None)], None

            match = step.execute(subject)

            if match.success:
                if type(match.result) is dict:
                    match.result = clean_dict(match.result)

                Logr.debug('Found match with weight %s, match: %s, num_fragments: %s' % (
                    match.weight, match.result, match.num_fragments
                ))

                step.matched = True

                break

        if all([step.single and step.matched for step in self.steps]):
            Logr.debug('All steps completed, group finished')
            parent_node.finished_groups.append(self)
            return nodes, match

        # Check post constraints
        broke, definite = self.check_constraints(self.post_constraints, parent_head, subject, match=match)
        if broke:
            return nodes, None

        return nodes, match

    def check_constraints(self, constraints, parent_head, subject, **kwargs):
        parent_node = parent_head[0] if type(parent_head) is list else parent_head

        # Check constraints
        for constraint in [c for c in constraints if c.target == subject.__key__ or not c.target]:
            Logr.debug("Testing constraint %s against subject %s", repr(constraint), repr(subject))

            weight, success = constraint.execute(parent_node, subject, **kwargs)

            if success:
                Logr.debug('capturing broke on "%s" at %s', subject.value, constraint)
                parent_node.finished_groups.append(self)

                return True, weight == 1.0

        return False, None

    def execute(self):
        heads_finished = None

        while heads_finished is None or not (len(heads_finished) == len(self.result.heads) and all(heads_finished)):
            heads_finished = []

            heads = self.result.heads
            self.result.heads = []

            for head in heads:
                node = head[0] if type(head) is list else head

                if self in node.finished_groups:
                    Logr.debug("head finished for group")
                    self.result.heads.append(head)
                    heads_finished.append(True)
                    continue

                Logr.debug('')

                Logr.debug(node)

                next_subject = node.next()

                Logr.debug('----------[%s] (%s)----------' % (next_subject, repr(next_subject.value) if next_subject else None))

                if next_subject:
                    for node_result in self.parse_subject(head, next_subject):
                        self.result.heads.append(node_result)

                    Logr.debug('Heads: %s', self.result.heads)

                heads_finished.append(self in node.finished_groups or next_subject is None)

            if len(self.result.heads) == 0:
                self.result.heads = heads

            Logr.debug("heads_finished: %s, self.result.heads: %s", heads_finished, self.result.heads)

        Logr.debug("group finished")

########NEW FILE########
__FILENAME__ = helpers
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


def is_list_type(obj, element_type):
    if not type(obj) is list:
        return False

    if len(obj) < 1:
        raise ValueError("Unable to determine list element type from empty list")

    return type(obj[0]) is element_type


def clean_dict(target, remove=None):
    """Recursively remove items matching a value 'remove' from the dictionary

    :type target: dict
    """
    if type(target) is not dict:
        raise ValueError("Target is required to be a dict")

    remove_keys = []
    for key in target.keys():
        if type(target[key]) is not dict:
            if target[key] == remove:
                remove_keys.append(key)
        else:
            clean_dict(target[key], remove)

    for key in remove_keys:
        target.pop(key)

    return target


def update_dict(a, b):
    for key, value in b.items():
        if value is None:
            continue

        if key not in a:
            a[key] = value
        elif isinstance(a[key], dict) and isinstance(value, dict):
            update_dict(a[key], value)
        elif isinstance(a[key], list):
            a[key].append(value)
        else:
            a[key] = [a[key], value]


def xrange_six(start, stop=None, step=None):
    if stop is not None and step is not None:
        if PY3:
            return range(start, stop, step)
        else:
            return xrange(start, stop, step)
    else:
        if PY3:
            return range(start)
        else:
            return xrange(start)


def delta_seconds(td):
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6

########NEW FILE########
__FILENAME__ = matcher
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from caper.helpers import update_dict, delta_seconds
from caper.objects import CaperPattern
from datetime import datetime
from logr import Logr
import caper.compat
import itertools


class Matcher(object):
    def __init__(self, pattern_groups):
        self.regex = {}

        self.construct_patterns(pattern_groups)

    def construct_patterns(self, pattern_groups):
        compile_start = datetime.now()
        compile_count = 0

        for group_name, patterns in pattern_groups:
            if group_name not in self.regex:
                self.regex[group_name] = []

            # Transform into weight groups
            if type(patterns[0]) is str or type(patterns[0][0]) not in [int, float]:
                patterns = [(1.0, patterns)]

            for weight, patterns in patterns:
                weight_patterns = []

                for pattern in [CaperPattern.construct(v) for v in patterns if v]:
                    compile_count += pattern.compile()
                    weight_patterns.append(pattern)

                self.regex[group_name].append((weight, weight_patterns))

        Logr.info("Compiled %s patterns in %ss", compile_count, delta_seconds(datetime.now() - compile_start))

    def find_group(self, name):
        for group_name, weight_groups in self.regex.items():
            if group_name and group_name == name:
                return group_name, weight_groups

        return None, None

    def value_match(self, value, group_name=None, single=True):
        result = None

        for group, weight_groups in self.regex.items():
            if group_name and group != group_name:
                continue

            # TODO handle multiple weights
            weight, patterns = weight_groups[0]

            for pattern in patterns:
                match = pattern[0].match(value)
                if not match:
                    continue

                if result is None:
                    result = {}
                if group not in result:
                    result[group] = {}

                result[group].update(match.groupdict())

                if single:
                    return result

        return result

    def fragment_match(self, fragment, group_name=None):
        """Follow a fragment chain to try find a match

        :type fragment: caper.objects.CaperFragment
        :type group_name: str or None

        :return: The weight of the match found between 0.0 and 1.0,
                  where 1.0 means perfect match and 0.0 means no match
        :rtype: (float, dict, int)
        """

        group_name, weight_groups = self.find_group(group_name)

        for weight, patterns in weight_groups:
            for pattern in patterns:
                success = True
                result = {}

                num_matched = 0

                fragment_iterator = fragment.take_right(
                    return_type='value',
                    include_separators=pattern.include_separators,
                    include_source=True
                )

                for subject, fragment_pattern in itertools.izip_longest(fragment_iterator, pattern):
                    # No patterns left to match
                    if not fragment_pattern:
                        break

                    # No fragments left to match against pattern
                    if not subject:
                        success = False
                        break

                    value, source = subject

                    matches = pattern.execute(fragment_pattern, value)

                    if matches:
                        for match in matches:
                            update_dict(result, match.groupdict())
                    else:
                        success = False
                        break

                    if source == 'subject':
                        num_matched += 1

                if success:
                    Logr.debug('Found match with weight %s using regex pattern "%s"' % (weight, [sre.pattern for sre in pattern.patterns]))
                    return float(weight), result, num_matched

        return 0.0, None, 1

########NEW FILE########
__FILENAME__ = objects
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from caper.helpers import is_list_type
from caper.compat import basestring
import re


class CaperSubject(object):
    def __init__(self, value=None):
        if value is None:
            value = ""

        #: :type: str
        self.value = value

    def take(self, direction, count=None, return_type='subject', include_self=True,
             include_separators=False, include_source=False):
        if direction not in ['left', 'right']:
            raise ValueError('Un-Expected value for "direction", expected "left" or "right".')

        def get_item(value):
            source = None

            if isinstance(value, basestring):
                source = 'separator'

            if isinstance(value, CaperSubject):
                source = 'subject'

                if return_type == 'value':
                    value = value.value

            if include_source:
                return value, source

            return value

        if include_self:
            yield get_item(self)

            if count:
                count -= 1

        cur = self
        n = 0

        while count is None or n < count:
            if cur and getattr(cur, direction):
                cur = getattr(cur, direction)

                if include_separators and hasattr(cur, 'left_sep'):
                    yield get_item(cur.left_sep)

                yield get_item(cur)
            else:
                break

            n += 1

    def take_left(self, count=None, **kwargs):
        return self.take('left', count, **kwargs)

    def take_right(self, count=None, **kwargs):
        return self.take('right', count, **kwargs)


class CaperClosure(CaperSubject):
    __key__ = 'closure'

    def __init__(self, index, value):
        super(CaperClosure, self).__init__(value)

        #: :type: int
        self.index = index

        #: :type: CaperClosure
        self.left = None
        #: :type: CaperClosure
        self.right = None

        #: :type: list of CaperFragment
        self.fragments = []

    def __str__(self):
        return "<CaperClosure value: %s" % repr(self.value)

    def __repr__(self):
        return self.__str__()


class CaperFragment(CaperSubject):
    __key__ = 'fragment'

    def __init__(self, closure=None):
        super(CaperFragment, self).__init__()

        #: :type: CaperClosure
        self.closure = closure

        #: :type: CaperFragment
        self.left = None
        #: :type: str
        self.left_sep = None

        #: :type: CaperFragment
        self.right = None
        #: :type: str
        self.right_sep = None

        #: :type: int
        self.position = None

    def __str__(self):
        return "<CaperFragment value: %s>" % repr(self.value)

    def __repr__(self):
        return self.__str__()


class CaptureMatch(object):
    def __init__(self, tag, step, success=False, weight=None, result=None, num_fragments=1):
        #: :type: bool
        self.success = success

        #: :type: float
        self.weight = weight

        #: :type: dict or str
        self.result = result

        #: :type: int
        self.num_fragments = num_fragments

        #: :type: str
        self.tag = tag

        #: :type: CaptureStep
        self.step = step

    def __str__(self):
        return "<CaperMatch result: %s>" % repr(self.result)

    def __repr__(self):
        return self.__str__()


class CaperPattern(object):
    def __init__(self, patterns, method='match', include_separators=False):
        self.patterns = patterns

        self.method = method
        self.include_separators = include_separators

    def compile(self):
        patterns = self.patterns
        self.patterns = []

        for pattern in patterns:
            if type(pattern) is tuple:
                if len(pattern) == 2:
                    # Construct OR-list pattern
                    pattern = pattern[0] % '|'.join(pattern[1])
                elif len(pattern) == 1:
                    pattern = pattern[0]

            # Compile the pattern
            self.patterns.append(re.compile(pattern, re.IGNORECASE))

        return len(patterns)

    def execute(self, fragment_pattern, value):
        if self.method == 'match':
            match = fragment_pattern.match(value)
            return [match] if match else []
        elif self.method == 'findall':
            return list(fragment_pattern.finditer(value))

        raise ValueError('Unknown pattern method "%s"' % self.method)

    def __getitem__(self, index):
        return self.patterns[index]

    def __len__(self):
        return len(self.patterns)

    def __iter__(self):
        return iter(self.patterns)

    @staticmethod
    def construct(value):
        if type(value) is CaperPattern:
            return value

        # Transform into multi-fragment patterns
        if isinstance(value, basestring):
            return CaperPattern((value,))

        if type(value) is tuple:
            if len(value) == 2 and type(value[0]) is str and is_list_type(value[1], str):
                return CaperPattern((value,))
            else:
                return CaperPattern(value)

        raise ValueError("Unknown pattern format")

########NEW FILE########
__FILENAME__ = anime
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from caper.parsers.base import Parser


REGEX_GROUP = re.compile(r'(\(|\[)(?P<group>.*?)(\)|\])', re.IGNORECASE)


PATTERN_GROUPS = [
    ('identifier', [
        r'S(?P<season>\d+)E(?P<episode>\d+)',
        r'(S(?P<season>\d+))|(E(?P<episode>\d+))',

        r'Ep(?P<episode>\d+)',
        r'$(?P<absolute>\d+)^',

        (r'Episode', r'(?P<episode>\d+)'),
    ]),
    ('video', [
        (r'(?P<h264_profile>%s)', [
            'Hi10P'
        ]),
        (r'.(?P<resolution>%s)', [
            '720p',
            '1080p',

            '960x720',
            '1920x1080'
        ]),
        (r'(?P<source>%s)', [
            'BD'
        ]),
    ]),
    ('audio', [
        (r'(?P<codec>%s)', [
            'FLAC'
        ]),
    ])
]


class AnimeParser(Parser):
    def __init__(self, debug=False):
        super(AnimeParser, self).__init__(PATTERN_GROUPS, debug)

    def capture_group(self, fragment):
        match = REGEX_GROUP.match(fragment.value)

        if not match:
            return None

        return match.group('group')

    def run(self, closures):
        """
        :type closures: list of CaperClosure
        """

        self.setup(closures)

        self.capture_closure('group', func=self.capture_group)\
            .execute(once=True)

        self.capture_fragment('show_name', single=False)\
            .until_fragment(value__re='identifier')\
            .until_fragment(value__re='video')\
            .execute()

        self.capture_fragment('identifier', regex='identifier') \
            .capture_fragment('video', regex='video', single=False) \
            .capture_fragment('audio', regex='audio', single=False) \
            .execute()

        self.result.build()
        return self.result

########NEW FILE########
__FILENAME__ = base
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from caper import Matcher
from caper.group import CaptureGroup
from caper.result import CaperResult, CaperClosureNode, CaperRootNode
from logr import Logr


class Parser(object):
    def __init__(self, matcher, debug=False):
        self.debug = debug

        self.matcher = matcher

        self.closures = None
        #: :type: caper.result.CaperResult
        self.result = None

        self._match_cache = None
        self._fragment_pos = None
        self._closure_pos = None
        self._history = None

        self.reset()

    def reset(self):
        self.closures = None
        self.result = CaperResult()

        self._match_cache = {}
        self._fragment_pos = -1
        self._closure_pos = -1
        self._history = []

    def setup(self, closures):
        """
        :type closures: list of CaperClosure
        """

        self.reset()
        self.closures = closures

        self.result.heads = [CaperRootNode(closures[0])]

    def run(self, closures):
        """
        :type closures: list of CaperClosure
        """

        raise NotImplementedError()

    #
    # Capture Methods
    #

    def capture_fragment(self, tag, regex=None, func=None, single=True, **kwargs):
        return CaptureGroup(self, self.result).capture_fragment(
            tag,
            regex=regex,
            func=func,
            single=single,
            **kwargs
        )

    def capture_closure(self, tag, regex=None, func=None, single=True, **kwargs):
        return CaptureGroup(self, self.result).capture_closure(
            tag,
            regex=regex,
            func=func,
            single=single,
            **kwargs
        )

########NEW FILE########
__FILENAME__ = scene
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from logr import Logr
from caper import Matcher
from caper.objects import CaperPattern
from caper.parsers.base import Parser
from caper.result import CaperFragmentNode


PATTERN_GROUPS = [
    ('identifier', [
        (1.0, [
            # 'S01E01-E02' or 'S01E01 to E02'
            CaperPattern(
                ('^S(?P<season>\d+)E(?P<episode_from>\d+)$', 'to|-', '^E(?P<episode_to>\d+)$'),
                include_separators=True
            ),

            # 'S03 E01 to E08' or 'S03 E01 - E09'
            ('^S(?P<season>\d+)$', '^E(?P<episode_from>\d+)$', '^(to|-)$', '^E(?P<episode_to>\d+)$'),

            # 'E01 to E08' or 'E01 - E09'
            ('^E(?P<episode_from>\d+)$', 'to|-', '^E(?P<episode_to>\d+)$'),

            # 'S01-S03' or 'S01 to S03'
            CaperPattern(
                ('^S(?P<season_from>\d+)$', 'to|-', '^S(?P<season_to>\d+)$'),
                include_separators=True
            ),

            # 'S01E01-E02', 'S01E01-02' or 'S01E01 to E02'
            CaperPattern(
                ('^S(?P<season>\d+)E(?P<episode_from>\d+)$', 'to|-', '^E?(?P<episode_to>\d+)$'),
                include_separators=True
            ),

            # S01E01E02 (repeat style)
            CaperPattern(
                ('(S(?P<season>\d+))?E(?P<episode>\d+)',),
                method='findall'
            ),


            # S02E13
            r'^S(?P<season>\d+)E(?P<episode>\d+)$',
            # S01 E13
            (r'^(S(?P<season>\d+))$', r'^(E(?P<episode>\d+))$'),
            # S02
            # E13
            r'^((S(?P<season>\d+))|(E(?P<episode>\d+)))$',
            # 3x19
            r'^(?P<season>\d+)x(?P<episode>\d+)$',

            # 2013.09.15
            (r'^(?P<year>\d{4})$', r'^(?P<month>\d{2})$', r'^(?P<day>\d{2})$'),
            # 09.15.2013
            (r'^(?P<month>\d{2})$', r'^(?P<day>\d{2})$', r'^(?P<year>\d{4})$'),
            # TODO - US/UK Date Format Conflict? will only support US format for now..
            # 15.09.2013
            #(r'^(?P<day>\d{2})$', r'^(?P<month>\d{2})$', r'^(?P<year>\d{4})$'),
            # 130915
            r'^(?P<year_short>\d{2})(?P<month>\d{2})(?P<day>\d{2})$',

            # Season 3 Episode 14
            (r'^Se(ason)?$', r'^(?P<season>\d+)$', r'^Ep(isode)?$', r'^(?P<episode>\d+)$'),
            # Season 3
            (r'^Se(ason)?$', r'^(?P<season>\d+)$'),
            # Episode 14
            (r'^Ep(isode)?$', r'^(?P<episode>\d+)$'),

            # Part.3
            # Part.1.and.Part.3
            ('^Part$', '(?P<part>\d+)'),

            r'(?P<extra>Special)',
            r'(?P<country>NZ|AU|US|UK)'
        ]),
        (0.8, [
            # 100 - 1899, 2100 - 9999 (skips 1900 to 2099 - so we don't get years my mistake)
            # TODO - Update this pattern on 31 Dec 2099
            r'^(?P<season>([1-9])|(1[0-8])|(2[1-9])|([3-9][0-9]))(?P<episode>\d{2})$'
        ]),
        (0.5, [
            # 100 - 9999
            r'^(?P<season>([1-9])|([1-9][0-9]))(?P<episode>\d{2})$'
        ])
    ]),

    ('video', [
        r'(?P<aspect>FS|WS)',

        (r'(?P<resolution>%s)', [
            '480p',
            '720p',
            '1080p'
        ]),

        #
        # Source
        #

        (r'(?P<source>%s)', [
            'DVDRiP',
            # HDTV
            'HDTV',
            'PDTV',
            'DSR',
            # WEB
            'WEBRip',
            'WEBDL',
            # BluRay
            'BluRay',
            'B(D|R)Rip',
            # DVD
            'DVDR',
            'DVD9',
            'DVD5'
        ]),

        # For multi-fragment 'WEB-DL', 'WEB-Rip', etc... matches
        ('(?P<source>WEB)', '(?P<source>DL|Rip)'),

        #
        # Codec
        #

        (r'(?P<codec>%s)', [
            'x264',
            'XViD',
            'H264',
            'AVC'
        ]),

        # For multi-fragment 'H 264' tags
        ('(?P<codec>H)', '(?P<codec>264)'),
    ]),

    ('dvd', [
        r'D(ISC)?(?P<disc>\d+)',

        r'R(?P<region>[0-8])',

        (r'(?P<encoding>%s)', [
            'PAL',
            'NTSC'
        ]),
    ]),

    ('audio', [
        (r'(?P<codec>%s)', [
            'AC3',
            'TrueHD'
        ]),

        (r'(?P<language>%s)', [
            'GERMAN',
            'DUTCH',
            'FRENCH',
            'SWEDiSH',
            'DANiSH',
            'iTALiAN'
        ]),
    ]),

    ('scene', [
        r'(?P<proper>PROPER|REAL)',
    ])
]


class SceneParser(Parser):
    matcher = None

    def __init__(self, debug=False):
        if not SceneParser.matcher:
            SceneParser.matcher = Matcher(PATTERN_GROUPS)
            Logr.info("Fragment matcher for %s created", self.__class__.__name__)

        super(SceneParser, self).__init__(SceneParser.matcher, debug)

    def capture_group(self, fragment):
        if fragment.closure.index + 1 != len(self.closures):
            return None

        if fragment.left_sep != '-' or fragment.right:
            return None

        return fragment.value

    def run(self, closures):
        """
        :type closures: list of CaperClosure
        """

        self.setup(closures)

        self.capture_fragment('show_name', single=False)\
            .until_fragment(node__re='identifier')\
            .until_fragment(node__re='video')\
            .until_fragment(node__re='dvd')\
            .until_fragment(node__re='audio')\
            .until_fragment(node__re='scene')\
            .execute()

        self.capture_fragment('identifier', regex='identifier', single=False)\
            .capture_fragment('video', regex='video', single=False)\
            .capture_fragment('dvd', regex='dvd', single=False)\
            .capture_fragment('audio', regex='audio', single=False)\
            .capture_fragment('scene', regex='scene', single=False)\
            .until_fragment(left_sep__eq='-', right__eq=None)\
            .execute()

        self.capture_fragment('group', func=self.capture_group)\
            .execute()

        self.print_tree(self.result.heads)

        self.result.build()
        return self.result

    def print_tree(self, heads):
        if not self.debug:
            return

        for head in heads:
            head = head if type(head) is list else [head]

            if type(head[0]) is CaperFragmentNode:
                for fragment in head[0].fragments:
                    Logr.debug(fragment.value)
            else:
                Logr.debug(head[0].closure.value)

            for node in head:
                Logr.debug('\t' + str(node).ljust(55) + '\t' + (
                    str(node.match.weight) + '\t' + str(node.match.result)
                ) if node.match else '')

            if len(head) > 0 and head[0].parent:
                self.print_tree([head[0].parent])

########NEW FILE########
__FILENAME__ = usenet
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from logr import Logr
from caper import Matcher
from caper.parsers.base import Parser


PATTERN_GROUPS = [
    ('usenet', [
        r'\[(?P<group>#[\w\.@]+)\]',
        r'^\[(?P<code>\w+)\]$',
        r'\[(?P<full>FULL)\]',
        r'\[\s?(?P<group>TOWN)\s?\]',
        r'(.*?\s)?[_\W]*(?P<site>www\..*?\.[a-z0-9]+)[_\W]*(.*?\s)?',
        r'(.*?\s)?[_\W]*(?P<site>(www\.)?[-\w]+\.(com|org|info))[_\W]*(.*?\s)?'
    ]),

    ('part', [
        r'.?(?P<current>\d+)/(?P<total>\d+).?'
    ]),

    ('detail', [
        r'[\s-]*\w*?[\s-]*\"(?P<file_name>.*?)\"[\s-]*\w*?[\s-]*(?P<size>[\d,\.]*\s?MB)?[\s-]*(?P<extra>yEnc)?',
        r'(?P<size>[\d,\.]*\s?MB)[\s-]*(?P<extra>yEnc)',
        r'(?P<size>[\d,\.]*\s?MB)|(?P<extra>yEnc)'
    ])
]


class UsenetParser(Parser):
    matcher = None

    def __init__(self, debug=False):
        if not UsenetParser.matcher:
            UsenetParser.matcher = Matcher(PATTERN_GROUPS)
            Logr.info("Fragment matcher for %s created", self.__class__.__name__)

        super(UsenetParser, self).__init__(UsenetParser.matcher, debug)

    def run(self, closures):
        """
        :type closures: list of CaperClosure
        """

        self.setup(closures)

        # Capture usenet or part info until we get a part or matching fails
        self.capture_closure('usenet', regex='usenet', single=False)\
            .capture_closure('part', regex='part', single=True) \
            .until_result(tag='part') \
            .until_failure()\
            .execute()

        is_town_release, has_part = self.get_state()

        if not is_town_release:
            self.capture_release_name()

        # If we already have the part (TOWN releases), ignore matching part again
        if not is_town_release and not has_part:
            self.capture_fragment('part', regex='part', single=True)\
                .until_closure(node__re='usenet')\
                .until_success()\
                .execute()

        # Capture any leftover details
        self.capture_closure('usenet', regex='usenet', single=False)\
            .capture_closure('detail', regex='detail', single=False)\
            .execute()

        self.result.build()
        return self.result

    def capture_release_name(self):
        self.capture_closure('detail', regex='detail', single=False)\
            .until_failure()\
            .execute()

        self.capture_fragment('release_name', single=False, include_separators=True) \
            .until_closure(node__re='usenet') \
            .until_closure(node__re='detail') \
            .until_closure(node__re='part') \
            .until_fragment(value__eq='-')\
            .execute()

        # Capture any detail after the release name
        self.capture_closure('detail', regex='detail', single=False)\
            .until_failure()\
            .execute()

    def get_state(self):
        # TODO multiple-chains?
        is_town_release = False
        has_part = False

        for tag, result in self.result.heads[0].captured():
            if tag == 'usenet' and result.get('group') == 'TOWN':
                is_town_release = True

            if tag == 'part':
                has_part = True

        return is_town_release, has_part

########NEW FILE########
__FILENAME__ = result
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
from logr import Logr


GROUP_MATCHES = ['identifier']


class CaperNode(object):
    def __init__(self, closure, parent=None, match=None):
        """
        :type parent: CaperNode
        :type weight: float
        """

        #: :type: caper.objects.CaperClosure
        self.closure = closure

        #: :type: CaperNode
        self.parent = parent

        #: :type: CaptureMatch
        self.match = match

        #: :type: list of CaptureGroup
        self.finished_groups = []

    def next(self):
        raise NotImplementedError()

    def captured(self):
        cur = self

        if cur.match:
            yield cur.match.tag, cur.match.result

        while cur.parent:
            cur = cur.parent

            if cur.match:
                yield cur.match.tag, cur.match.result


class CaperRootNode(CaperNode):
    def __init__(self, closure):
        """
        :type closure: caper.objects.CaperClosure or list of caper.objects.CaperClosure
        """
        super(CaperRootNode, self).__init__(closure)

    def next(self):
        return self.closure


class CaperClosureNode(CaperNode):
    def __init__(self, closure, parent=None, match=None):
        """
        :type closure: caper.objects.CaperClosure or list of caper.objects.CaperClosure
        """
        super(CaperClosureNode, self).__init__(closure, parent, match)

    def next(self):
        if not self.closure:
            return None

        if self.match:
            # Jump to next closure if we have a match
            return self.closure.right
        elif len(self.closure.fragments) > 0:
            # Otherwise parse the fragments
            return self.closure.fragments[0]

        return None

    def __str__(self):
        return "<CaperClosureNode match: %s>" % repr(self.match)

    def __repr__(self):
        return self.__str__()


class CaperFragmentNode(CaperNode):
    def __init__(self, closure, fragments, parent=None, match=None):
        """
        :type closure: caper.objects.CaperClosure
        :type fragments: list of caper.objects.CaperFragment
        """
        super(CaperFragmentNode, self).__init__(closure, parent, match)

        #: :type: caper.objects.CaperFragment or list of caper.objects.CaperFragment
        self.fragments = fragments

    def next(self):
        if len(self.fragments) > 0 and self.fragments[-1] and self.fragments[-1].right:
            return self.fragments[-1].right

        if self.closure.right:
            return self.closure.right

        return None

    def __str__(self):
        return "<CaperFragmentNode match: %s>" % repr(self.match)

    def __repr__(self):
        return self.__str__()


class CaperResult(object):
    def __init__(self):
        #: :type: list of CaperNode
        self.heads = []

        self.chains = []

    def build(self):
        max_matched = 0

        for head in self.heads:
            for chain in self.combine_chain(head):
                if chain.num_matched > max_matched:
                    max_matched = chain.num_matched

                self.chains.append(chain)

        for chain in self.chains:
            chain.weights.append(chain.num_matched / float(max_matched or chain.num_matched or 1))
            chain.finish()

        self.chains.sort(key=lambda chain: chain.weight, reverse=True)

        for chain in self.chains:
            Logr.debug("chain weight: %.02f", chain.weight)
            Logr.debug("\tInfo: %s", chain.info)

            Logr.debug("\tWeights: %s", chain.weights)
            Logr.debug("\tNumber of Fragments Matched: %s", chain.num_matched)

    def combine_chain(self, subject, chain=None):
        nodes = subject if type(subject) is list else [subject]

        if chain is None:
            chain = CaperResultChain()

        result = []

        for x, node in enumerate(nodes):
            node_chain = chain if x == len(nodes) - 1 else chain.copy()

            if not node.parent:
                result.append(node_chain)
                continue

            node_chain.update(node)
            result.extend(self.combine_chain(node.parent, node_chain))

        return result


class CaperResultChain(object):
    def __init__(self):
        #: :type: float
        self.weight = None
        self.info = {}
        self.num_matched = 0

        self.weights = []

    def update(self, subject):
        """
        :type subject: CaperFragmentNode
        """
        if not subject.match or not subject.match.success:
            return

        # TODO this should support closure nodes
        if type(subject) is CaperFragmentNode:
            self.num_matched += len(subject.fragments) if subject.fragments is not None else 0

        self.weights.append(subject.match.weight)

        if subject.match:
            if subject.match.tag not in self.info:
                self.info[subject.match.tag] = []

            self.info[subject.match.tag].insert(0, subject.match.result)

    def finish(self):
        self.weight = sum(self.weights) / len(self.weights)

    def copy(self):
        chain = CaperResultChain()

        chain.weight = self.weight
        chain.info = copy.deepcopy(self.info)

        chain.num_matched = self.num_matched
        chain.weights = copy.copy(self.weights)

        return chain
########NEW FILE########
__FILENAME__ = step
# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from caper.objects import CaptureMatch
from logr import Logr


class CaptureStep(object):
    REPR_KEYS = ['regex', 'func', 'single']

    def __init__(self, capture_group, tag, source, regex=None, func=None, single=None, **kwargs):
        #: @type: CaptureGroup
        self.capture_group = capture_group

        #: @type: str
        self.tag = tag
        #: @type: str
        self.source = source
        #: @type: str
        self.regex = regex
        #: @type: function
        self.func = func
        #: @type: bool
        self.single = single

        self.kwargs = kwargs

        self.matched = False

    def execute(self, fragment):
        """Execute step on fragment

        :type fragment: CaperFragment
        :rtype : CaptureMatch
        """

        match = CaptureMatch(self.tag, self)

        if self.regex:
            weight, result, num_fragments = self.capture_group.parser.matcher.fragment_match(fragment, self.regex)
            Logr.debug('(execute) [regex] tag: "%s"', self.tag)

            if not result:
                return match

            # Populate CaptureMatch
            match.success = True
            match.weight = weight
            match.result = result
            match.num_fragments = num_fragments
        elif self.func:
            result = self.func(fragment)
            Logr.debug('(execute) [func] %s += "%s"', self.tag, match)

            if not result:
                return match

            # Populate CaptureMatch
            match.success = True
            match.weight = 1.0
            match.result = result
        else:
            Logr.debug('(execute) [raw] %s += "%s"', self.tag, fragment.value)

            include_separators = self.kwargs.get('include_separators', False)

            # Populate CaptureMatch
            match.success = True
            match.weight = 1.0

            if include_separators:
                match.result = (fragment.left_sep, fragment.value, fragment.right_sep)
            else:
                match.result = fragment.value

        return match

    def __repr__(self):
        attribute_values = [key + '=' + repr(getattr(self, key))
                            for key in self.REPR_KEYS
                            if hasattr(self, key) and getattr(self, key)]

        attribute_string = ', ' + ', '.join(attribute_values) if len(attribute_values) > 0 else ''

        return "CaptureStep('%s'%s)" % (self.tag, attribute_string)

########NEW FILE########
__FILENAME__ = websocket
"""
websocket - WebSocket client library for Python

Copyright (C) 2010 Hiroki Ohtani(liris)

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""


import socket
from urlparse import urlparse
import os
import array
import struct
import uuid
import hashlib
import base64
import logging

"""
websocket python client.
=========================

This version support only hybi-13.
Please see http://tools.ietf.org/html/rfc6455 for protocol.
"""


# websocket supported version.
VERSION = 13

# closing frame status codes.
STATUS_NORMAL = 1000
STATUS_GOING_AWAY = 1001
STATUS_PROTOCOL_ERROR = 1002
STATUS_UNSUPPORTED_DATA_TYPE = 1003
STATUS_STATUS_NOT_AVAILABLE = 1005
STATUS_ABNORMAL_CLOSED = 1006
STATUS_INVALID_PAYLOAD = 1007
STATUS_POLICY_VIOLATION = 1008
STATUS_MESSAGE_TOO_BIG = 1009
STATUS_INVALID_EXTENSION = 1010
STATUS_UNEXPECTED_CONDITION = 1011
STATUS_TLS_HANDSHAKE_ERROR = 1015

logger = logging.getLogger()


class WebSocketException(Exception):
    """
    websocket exeception class.
    """
    pass


class WebSocketConnectionClosedException(WebSocketException):
    """
    If remote host closed the connection or some network error happened,
    this exception will be raised.
    """
    pass

default_timeout = None
traceEnabled = False


def enableTrace(tracable):
    """
    turn on/off the tracability.

    tracable: boolean value. if set True, tracability is enabled.
    """
    global traceEnabled
    traceEnabled = tracable
    if tracable:
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)


def setdefaulttimeout(timeout):
    """
    Set the global timeout setting to connect.

    timeout: default socket timeout time. This value is second.
    """
    global default_timeout
    default_timeout = timeout


def getdefaulttimeout():
    """
    Return the global timeout setting(second) to connect.
    """
    return default_timeout


def _parse_url(url):
    """
    parse url and the result is tuple of
    (hostname, port, resource path and the flag of secure mode)

    url: url string.
    """
    if ":" not in url:
        raise ValueError("url is invalid")

    scheme, url = url.split(":", 1)

    parsed = urlparse(url, scheme="http")
    if parsed.hostname:
        hostname = parsed.hostname
    else:
        raise ValueError("hostname is invalid")
    port = 0
    if parsed.port:
        port = parsed.port

    is_secure = False
    if scheme == "ws":
        if not port:
            port = 80
    elif scheme == "wss":
        is_secure = True
        if not port:
            port = 443
    else:
        raise ValueError("scheme %s is invalid" % scheme)

    if parsed.path:
        resource = parsed.path
    else:
        resource = "/"

    if parsed.query:
        resource += "?" + parsed.query

    return (hostname, port, resource, is_secure)


def create_connection(url, timeout=None, **options):
    """
    connect to url and return websocket object.

    Connect to url and return the WebSocket object.
    Passing optional timeout parameter will set the timeout on the socket.
    If no timeout is supplied, the global default timeout setting returned by getdefauttimeout() is used.
    You can customize using 'options'.
    If you set "header" dict object, you can set your own custom header.

    >>> conn = create_connection("ws://echo.websocket.org/",
         ...     header=["User-Agent: MyProgram",
         ...             "x-custom: header"])


    timeout: socket timeout time. This value is integer.
             if you set None for this value, it means "use default_timeout value"

    options: current support option is only "header".
             if you set header as dict value, the custom HTTP headers are added.
    """
    sockopt = options.get("sockopt", ())
    websock = WebSocket(sockopt=sockopt)
    websock.settimeout(timeout != None and timeout or default_timeout)
    websock.connect(url, **options)
    return websock

_MAX_INTEGER = (1 << 32) -1
_AVAILABLE_KEY_CHARS = range(0x21, 0x2f + 1) + range(0x3a, 0x7e + 1)
_MAX_CHAR_BYTE = (1<<8) -1

# ref. Websocket gets an update, and it breaks stuff.
# http://axod.blogspot.com/2010/06/websocket-gets-update-and-it-breaks.html


def _create_sec_websocket_key():
    uid = uuid.uuid4()
    return base64.encodestring(uid.bytes).strip()

_HEADERS_TO_CHECK = {
    "upgrade": "websocket",
    "connection": "upgrade",
    }


class _SSLSocketWrapper(object):
    def __init__(self, sock):
        self.ssl = socket.ssl(sock)

    def recv(self, bufsize):
        return self.ssl.read(bufsize)

    def send(self, payload):
        return self.ssl.write(payload)

    def fileno(self):
        return self.ssl.fileno()

_BOOL_VALUES = (0, 1)


def _is_bool(*values):
    for v in values:
        if v not in _BOOL_VALUES:
            return False

    return True


class ABNF(object):
    """
    ABNF frame class.
    see http://tools.ietf.org/html/rfc5234
    and http://tools.ietf.org/html/rfc6455#section-5.2
    """

    # operation code values.
    OPCODE_TEXT   = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE  = 0x8
    OPCODE_PING   = 0x9
    OPCODE_PONG   = 0xa

    # available operation code value tuple
    OPCODES = (OPCODE_TEXT, OPCODE_BINARY, OPCODE_CLOSE,
                OPCODE_PING, OPCODE_PONG)

    # opcode human readable string
    OPCODE_MAP = {
        OPCODE_TEXT: "text",
        OPCODE_BINARY: "binary",
        OPCODE_CLOSE: "close",
        OPCODE_PING: "ping",
        OPCODE_PONG: "pong"
        }

    # data length threashold.
    LENGTH_7  = 0x7d
    LENGTH_16 = 1 << 16
    LENGTH_63 = 1 << 63

    def __init__(self, fin = 0, rsv1 = 0, rsv2 = 0, rsv3 = 0,
                 opcode = OPCODE_TEXT, mask = 1, data = ""):
        """
        Constructor for ABNF.
        please check RFC for arguments.
        """
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.opcode = opcode
        self.mask = mask
        self.data = data
        self.get_mask_key = os.urandom

    @staticmethod
    def create_frame(data, opcode):
        """
        create frame to send text, binary and other data.

        data: data to send. This is string value(byte array).
            if opcode is OPCODE_TEXT and this value is uniocde,
            data value is conveted into unicode string, automatically.

        opcode: operation code. please see OPCODE_XXX.
        """
        if opcode == ABNF.OPCODE_TEXT and isinstance(data, unicode):
            data = data.encode("utf-8")
        # mask must be set if send data from client
        return ABNF(1, 0, 0, 0, opcode, 1, data)

    def format(self):
        """
        format this object to string(byte array) to send data to server.
        """
        if not _is_bool(self.fin, self.rsv1, self.rsv2, self.rsv3):
            raise ValueError("not 0 or 1")
        if self.opcode not in ABNF.OPCODES:
            raise ValueError("Invalid OPCODE")
        length = len(self.data)
        if length >= ABNF.LENGTH_63:
            raise ValueError("data is too long")

        frame_header = chr(self.fin << 7
                           | self.rsv1 << 6 | self.rsv2 << 5 | self.rsv3 << 4
                           | self.opcode)
        if length < ABNF.LENGTH_7:
            frame_header += chr(self.mask << 7 | length)
        elif length < ABNF.LENGTH_16:
            frame_header += chr(self.mask << 7 | 0x7e)
            frame_header += struct.pack("!H", length)
        else:
            frame_header += chr(self.mask << 7 | 0x7f)
            frame_header += struct.pack("!Q", length)

        if not self.mask:
            return frame_header + self.data
        else:
            mask_key = self.get_mask_key(4)
            return frame_header + self._get_masked(mask_key)

    def _get_masked(self, mask_key):
        s = ABNF.mask(mask_key, self.data)
        return mask_key + "".join(s)

    @staticmethod
    def mask(mask_key, data):
        """
        mask or unmask data. Just do xor for each byte

        mask_key: 4 byte string(byte).

        data: data to mask/unmask.
        """
        _m = array.array("B", mask_key)
        _d = array.array("B", data)
        for i in xrange(len(_d)):
            _d[i] ^= _m[i % 4]
        return _d.tostring()


class WebSocket(object):
    """
    Low level WebSocket interface.
    This class is based on
      The WebSocket protocol draft-hixie-thewebsocketprotocol-76
      http://tools.ietf.org/html/draft-hixie-thewebsocketprotocol-76

    We can connect to the websocket server and send/recieve data.
    The following example is a echo client.

    >>> import websocket
    >>> ws = websocket.WebSocket()
    >>> ws.connect("ws://echo.websocket.org")
    >>> ws.send("Hello, Server")
    >>> ws.recv()
    'Hello, Server'
    >>> ws.close()

    get_mask_key: a callable to produce new mask keys, see the set_mask_key
      function's docstring for more details
    sockopt: values for socket.setsockopt.
        sockopt must be tuple and each element is argument of sock.setscokopt.
    """

    def __init__(self, get_mask_key = None, sockopt = ()):
        """
        Initalize WebSocket object.
        """
        self.connected = False
        self.io_sock = self.sock = socket.socket()
        for opts in sockopt:
            self.sock.setsockopt(*opts)
        self.get_mask_key = get_mask_key

    def fileno(self):
        return self.io_sock.fileno()

    def set_mask_key(self, func):
        """
        set function to create musk key. You can custumize mask key generator.
        Mainly, this is for testing purpose.

        func: callable object. the fuct must 1 argument as integer.
              The argument means length of mask key.
              This func must be return string(byte array),
              which length is argument specified.
        """
        self.get_mask_key = func

    def settimeout(self, timeout):
        """
        Set the timeout to the websocket.

        timeout: timeout time(second).
        """
        self.sock.settimeout(timeout)

    def gettimeout(self):
        """
        Get the websocket timeout(second).
        """
        return self.sock.gettimeout()

    def connect(self, url, **options):
        """
        Connect to url. url is websocket url scheme. ie. ws://host:port/resource
        You can customize using 'options'.
        If you set "header" dict object, you can set your own custom header.

        >>> ws = WebSocket()
        >>> ws.connect("ws://echo.websocket.org/",
                ...     header={"User-Agent: MyProgram",
                ...             "x-custom: header"})

        timeout: socket timeout time. This value is integer.
                 if you set None for this value,
                 it means "use default_timeout value"

        options: current support option is only "header".
                 if you set header as dict value,
                 the custom HTTP headers are added.

        """
        hostname, port, resource, is_secure = _parse_url(url)
        # TODO: we need to support proxy
        self.sock.connect((hostname, port))
        if is_secure:
            self.io_sock = _SSLSocketWrapper(self.sock)
        self._handshake(hostname, port, resource, **options)

    def _handshake(self, host, port, resource, **options):
        sock = self.io_sock
        headers = []
        headers.append("GET %s HTTP/1.1" % resource)
        headers.append("Upgrade: websocket")
        headers.append("Connection: Upgrade")
        if port == 80:
            hostport = host
        else:
            hostport = "%s:%d" % (host, port)
        headers.append("Host: %s" % hostport)

        if "origin" in options:
            headers.append("Origin: %s" % options["origin"])
        else:
            headers.append("Origin: http://%s" % hostport)

        key = _create_sec_websocket_key()
        headers.append("Sec-WebSocket-Key: %s" % key)
        headers.append("Sec-WebSocket-Version: %s" % VERSION)
        if "header" in options:
            headers.extend(options["header"])

        headers.append("")
        headers.append("")

        header_str = "\r\n".join(headers)
        sock.send(header_str)
        if traceEnabled:
            logger.debug("--- request header ---")
            logger.debug(header_str)
            logger.debug("-----------------------")

        status, resp_headers = self._read_headers()
        if status != 101:
            self.close()
            raise WebSocketException("Handshake Status %d" % status)

        success = self._validate_header(resp_headers, key)
        if not success:
            self.close()
            raise WebSocketException("Invalid WebSocket Header")

        self.connected = True

    def _validate_header(self, headers, key):
        for k, v in _HEADERS_TO_CHECK.iteritems():
            r = headers.get(k, None)
            if not r:
                return False
            r = r.lower()
            if v != r:
                return False

        result = headers.get("sec-websocket-accept", None)
        if not result:
            return False
        result = result.lower()

        value = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        hashed = base64.encodestring(hashlib.sha1(value).digest()).strip().lower()
        return hashed == result

    def _read_headers(self):
        status = None
        headers = {}
        if traceEnabled:
            logger.debug("--- response header ---")

        while True:
            line = self._recv_line()
            if line == "\r\n":
                break
            line = line.strip()
            if traceEnabled:
                logger.debug(line)
            if not status:
                status_info = line.split(" ", 2)
                status = int(status_info[1])
            else:
                kv = line.split(":", 1)
                if len(kv) == 2:
                    key, value = kv
                    headers[key.lower()] = value.strip().lower()
                else:
                    raise WebSocketException("Invalid header")

        if traceEnabled:
            logger.debug("-----------------------")

        return status, headers

    def send(self, payload, opcode = ABNF.OPCODE_TEXT):
        """
        Send the data as string.

        payload: Payload must be utf-8 string or unicoce,
                  if the opcode is OPCODE_TEXT.
                  Otherwise, it must be string(byte array)

        opcode: operation code to send. Please see OPCODE_XXX.
        """
        frame = ABNF.create_frame(payload, opcode)
        if self.get_mask_key:
            frame.get_mask_key = self.get_mask_key
        data = frame.format()
        while data:
            l = self.io_sock.send(data)
            data = data[l:]
        if traceEnabled:
            logger.debug("send: " + repr(data))

    def ping(self, payload = ""):
        """
        send ping data.

        payload: data payload to send server.
        """
        self.send(payload, ABNF.OPCODE_PING)

    def pong(self, payload):
        """
        send pong data.

        payload: data payload to send server.
        """
        self.send(payload, ABNF.OPCODE_PONG)

    def recv(self):
        """
        Receive string data(byte array) from the server.

        return value: string(byte array) value.
        """
        opcode, data = self.recv_data()
        return data

    def recv_data(self):
        """
        Recieve data with operation code.

        return  value: tuple of operation code and string(byte array) value.
        """
        while True:
            frame = self.recv_frame()
            if not frame:
                # handle error:
                # 'NoneType' object has no attribute 'opcode'
                raise WebSocketException("Not a valid frame %s" % frame)
            elif frame.opcode in (ABNF.OPCODE_TEXT, ABNF.OPCODE_BINARY):
                return (frame.opcode, frame.data)
            elif frame.opcode == ABNF.OPCODE_CLOSE:
                self.send_close()
                return (frame.opcode, None)
            elif frame.opcode == ABNF.OPCODE_PING:
                self.pong(frame.data)

    def recv_frame(self):
        """
        recieve data as frame from server.

        return value: ABNF frame object.
        """
        header_bytes = self._recv_strict(2)
        if not header_bytes:
            return None
        b1 = ord(header_bytes[0])
        fin = b1 >> 7 & 1
        rsv1 = b1 >> 6 & 1
        rsv2 = b1 >> 5 & 1
        rsv3 = b1 >> 4 & 1
        opcode = b1 & 0xf
        b2 = ord(header_bytes[1])
        mask = b2 >> 7 & 1
        length = b2 & 0x7f

        length_data = ""
        if length == 0x7e:
            length_data = self._recv_strict(2)
            length = struct.unpack("!H", length_data)[0]
        elif length == 0x7f:
            length_data = self._recv_strict(8)
            length = struct.unpack("!Q", length_data)[0]

        mask_key = ""
        if mask:
            mask_key = self._recv_strict(4)
        data = self._recv_strict(length)
        if traceEnabled:
            recieved = header_bytes + length_data + mask_key + data
            logger.debug("recv: " + repr(recieved))

        if mask:
            data = ABNF.mask(mask_key, data)

        frame = ABNF(fin, rsv1, rsv2, rsv3, opcode, mask, data)
        return frame

    def send_close(self, status = STATUS_NORMAL, reason = ""):
        """
        send close data to the server.

        status: status code to send. see STATUS_XXX.

        reason: the reason to close. This must be string.
        """
        if status < 0 or status >= ABNF.LENGTH_16:
            raise ValueError("code is invalid range")
        self.send(struct.pack('!H', status) + reason, ABNF.OPCODE_CLOSE)

    def close(self, status = STATUS_NORMAL, reason = ""):
        """
        Close Websocket object

        status: status code to send. see STATUS_XXX.

        reason: the reason to close. This must be string.
        """
        if self.connected:
            if status < 0 or status >= ABNF.LENGTH_16:
                raise ValueError("code is invalid range")

            try:
                self.send(struct.pack('!H', status) + reason, ABNF.OPCODE_CLOSE)
                timeout = self.sock.gettimeout()
                self.sock.settimeout(3)
                try:
                    frame = self.recv_frame()
                    if logger.isEnabledFor(logging.ERROR):
                        recv_status = struct.unpack("!H", frame.data)[0]
                        if recv_status != STATUS_NORMAL:
                            logger.error("close status: " + repr(recv_status))
                except:
                    pass
                self.sock.settimeout(timeout)
                self.sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
        self._closeInternal()

    def _closeInternal(self):
        self.connected = False
        self.sock.close()
        self.io_sock = self.sock

    def _recv(self, bufsize):
        bytes = self.io_sock.recv(bufsize)
        if not bytes:
            raise WebSocketConnectionClosedException()
        return bytes

    def _recv_strict(self, bufsize):
        remaining = bufsize
        bytes = ""
        while remaining:
            bytes += self._recv(remaining)
            remaining = bufsize - len(bytes)

        return bytes

    def _recv_line(self):
        line = []
        while True:
            c = self._recv(1)
            line.append(c)
            if c == "\n":
                break
        return "".join(line)


class WebSocketApp(object):
    """
    Higher level of APIs are provided.
    The interface is like JavaScript WebSocket object.
    """
    def __init__(self, url, header = [],
                 on_open = None, on_message = None, on_error = None,
                 on_close = None, keep_running = True, get_mask_key = None,
                 sockopt=()):
        """
        url: websocket url.
        header: custom header for websocket handshake.
        on_open: callable object which is called at opening websocket.
          this function has one argument. The arugment is this class object.
        on_message: callbale object which is called when recieved data.
         on_message has 2 arguments.
         The 1st arugment is this class object.
         The passing 2nd arugment is utf-8 string which we get from the server.
       on_error: callable object which is called when we get error.
         on_error has 2 arguments.
         The 1st arugment is this class object.
         The passing 2nd arugment is exception object.
       on_close: callable object which is called when closed the connection.
         this function has one argument. The arugment is this class object.
       keep_running: a boolean flag indicating whether the app's main loop should
         keep running, defaults to True
       get_mask_key: a callable to produce new mask keys, see the WebSocket.set_mask_key's
         docstring for more information
        """
        self.url = url
        self.header = header
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.keep_running = keep_running
        self.get_mask_key = get_mask_key
        self.sock = None

    def send(self, data, opcode = ABNF.OPCODE_TEXT):
        """
        send message.
        data: message to send. If you set opcode to OPCODE_TEXT, data must be utf-8 string or unicode.
        opcode: operation code of data. default is OPCODE_TEXT.
        """
        if self.sock.send(data, opcode) == 0:
            raise WebSocketConnectionClosedException()

    def close(self):
        """
        close websocket connection.
        """
        self.keep_running = False
        self.sock.close()

    def run_forever(self, sockopt=()):
        """
        run event loop for WebSocket framework.
        This loop is infinite loop and is alive during websocket is available.
        sockopt: values for socket.setsockopt.
            sockopt must be tuple and each element is argument of sock.setscokopt.
        """
        if self.sock:
            raise WebSocketException("socket is already opened")
        try:
            self.sock = WebSocket(self.get_mask_key, sockopt = sockopt)
            self.sock.connect(self.url, header = self.header)
            self._run_with_no_err(self.on_open)
            while self.keep_running:
                data = self.sock.recv()
                if data is None:
                    break
                self._run_with_no_err(self.on_message, data)
        except Exception, e:
            self._run_with_no_err(self.on_error, e)
        finally:
            self.sock.close()
            self._run_with_no_err(self.on_close)
            self.sock = None

    def _run_with_no_err(self, callback, *args):
        if callback:
            try:
                callback(self, *args)
            except Exception, e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.error(e)


if __name__ == "__main__":
    enableTrace(True)
    ws = create_connection("ws://echo.websocket.org/")
    print("Sending 'Hello, World'...")
    ws.send("Hello, World")
    print("Sent")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)
    ws.close()

########NEW FILE########
