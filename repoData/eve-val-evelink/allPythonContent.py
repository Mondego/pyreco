__FILENAME__ = .travis-pre-run
#!/usr/bin/env python
#
#   Download and extract the last Google App Engine SDK.
#

import argparse
import logging
import os
import re
import sys
from evelink.thirdparty.six.moves import urllib
from xml.etree import ElementTree as ET
from zipfile import ZipFile


GAE_FEED_URL = 'https://code.google.com/feeds/p/googleappengine/downloads/basic'
SDK_PATTERN = r'http://googleappengine.googlecode.com/files/google_appengine_(\d\.)+zip'
DEFAULT_URL = 'http://googleappengine.googlecode.com/files/google_appengine_1.8.9.zip'

_log = logging.getLogger('travis.prerun')
logging.basicConfig(level=logging.INFO)


def get_args_parser():
    """Build the command line argument parser

    """
    parser = argparse.ArgumentParser(
        description='Download and extract the last Google App Engine SDK to.'
    )
    parser.add_argument(
        'gae_lib_dst',
        nargs='?',
        default='/usr/local',
        help='directory to extract Google App Engine SDK '
            '(default to "/usr/local").'
    )
    return parser


def get_sdk_url(feed, pattern):
    try:
        _log.info("Fetching atom feed for GAE sdk releases...")
        f = urllib.request.urlopen(feed)
        tree = ET.fromstring(f.read())
    finally:
        f.close()

    ns = {'a': 'http://www.w3.org/2005/Atom'}
    for link in tree.findall("a:entry/a:link[@rel='direct']", namespaces=ns):
        url = link.get('href')
        if re.match(SDK_PATTERN, url):
            _log.info("Found last release: %s", url)
            return url
    raise ValueError("No download links found!")


def download_sdk(url):
    _log.info("downloading SDK from %s ...", url)
    return urllib.request.urlretrieve(url)[0]


def unzip(file, dst):
    _log.info("Extracting SDK to %s ...", dst)
    with ZipFile(file) as z:
        for name in z.namelist():
            if '/' in name and name[0] == '/':
                raise ValueError("a SDK archive member has an absolute path")
            if '..' in name:
                raise ValueError("Found two dots in a member of the SDK archive")
        z.extractall(dst)


def main(gae_lib_dst):
    if sys.version_info[0:2] != (2, 7,):
        _log.info("Python 2.7 is required to run AppEngine.")
        return

    try:
        url = get_sdk_url(GAE_FEED_URL, SDK_PATTERN)
        _log.info("Found GAE SDK url: %s", url)
    except Exception:
        url = DEFAULT_URL
        _log.info(
            "Failed finding GAE SDK url at %s; Will use default url (%s)",
            GAE_FEED_URL,
            url
        )

    try:
        if not os.path.exists(gae_lib_dst):
            _log.info("Creating %s directory", gae_lib_dst)
            os.makedirs(gae_lib_dst)

        sdk_path = download_sdk(url)
        unzip(sdk_path, gae_lib_dst)
        _log.info("GAE SDK available at %s/google_engine", gae_lib_dst)
    except Exception as e:
        _log.error("failed downloading the sdk: %s", str(e))


if __name__ == '__main__':
    parser = get_args_parser()
    args = parser.parse_args()
    main(args.gae_lib_dst)

########NEW FILE########
__FILENAME__ = .travis-runner
#!/usr/bin/env python
#
# Test runner for Travis
# 
from __future__ import print_function

import sys

import argparse
if sys.version_info[0] < 3:
    import unittest2 as unittest
else:
    import unittest


def get_args_parser():
    """Build the command line argument parser

    """
    parser = argparse.ArgumentParser(
        description='Load GAE and run the test modules '
            'found in the target directory.'
    )
    parser.add_argument(
        'start_dir',
        nargs='?',
        default='./tests',
        help='directory to find test modules from (default to "./tests").'
    )
    parser.add_argument(
        '--gae-lib-root', '-l',
        default='/usr/local/google_appengine',
        help='directory where to find Google App Engine SDK '
            '(default to "/usr/local/google_appengine")'
    )
    return parser

def setup_gae(gae_lib_root):
    """Try to load Google App Engine SDK on Python 2.7.

    It shouldn't try to import to load it with Pyhton 2.6; 
    dev_appserver exit on load with any other version than 2.7.

    setup_gae will fail quietly if it can't find the SDK.

    """
    if sys.version_info[0:2] != (2, 7,):
        return

    try:
        sys.path.insert(0, gae_lib_root)
        import dev_appserver
    except ImportError:
        print("Failed to load Google App Engine SDK.")
        print("Google App Engine related tests will be skipped.")
    else:
        dev_appserver.fix_sys_path()

def main(gae_lib_root, start_dir):
    """Try to load Google App Engine SDK and then to run any tests found with 
    unittest2 discovery feature.
    
    If a test fail, it will exit with a status code of 1.

    """
    setup_gae(gae_lib_root)
    suite = unittest.loader.TestLoader().discover(start_dir)
    results = unittest.TextTestRunner(verbosity=2, buffer=True).run(suite)
    if not results.wasSuccessful():
        sys.exit(1)

if __name__ == '__main__':
    parser = get_args_parser()
    args = parser.parse_args()
    main(args.gae_lib_root, args.start_dir)

########NEW FILE########
__FILENAME__ = account
from evelink import api
from evelink import constants

class Account(object):
    """Wrapper around /account/ of the EVE API.

    Note that a valid API key is required.
    """

    def __init__(self, api):
        self.api = api

    @api.auto_call('account/AccountStatus')
    def status(self, api_result=None):
        """Returns the account's subscription status."""
        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)

        result = {
            'paid_ts': _ts('paidUntil'),
            'create_ts': _ts('createDate'),
            'logins': _int('logonCount'),
            'minutes_played': _int('logonMinutes'),
        }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call('account/APIKeyInfo')
    def key_info(self, api_result=None):
        """Returns the details of the API key being used to auth."""
        key = api_result.result.find('key')
        result = {
            'access_mask': int(key.attrib['accessMask']),
            'type': constants.APIKey.key_types[key.attrib['type']],
            'expire_ts': api.parse_ts(key.attrib['expires']) if key.attrib['expires'] else None,
            'characters': {},
        }

        rowset = key.find('rowset')
        for row in rowset.findall('row'):
            character = {
                'id': int(row.attrib['characterID']),
                'name': row.attrib['characterName'],
                'corp': {
                    'id': int(row.attrib['corporationID']),
                    'name': row.attrib['corporationName'],
                },
            }
            result['characters'][character['id']] = character

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call('account/Characters')
    def characters(self, api_result=None):
        """Returns all of the characters on an account."""
        rowset = api_result.result.find('rowset')
        result = {}
        for row in rowset.findall('row'):
            character = {
                'id': int(row.attrib['characterID']),
                'name': row.attrib['name'],
                'corp': {
                    'id': int(row.attrib['corporationID']),
                    'name': row.attrib['corporationName'],
                },
            }
            result[character['id']] = character

        return api.APIResult(result, api_result.timestamp, api_result.expires)

########NEW FILE########
__FILENAME__ = api
import calendar
import collections
import functools
import zlib
import inspect
import logging
import re
import time
from xml.etree import ElementTree

from evelink.thirdparty import six
from evelink.thirdparty.six.moves import urllib

_log = logging.getLogger('evelink.api')

# Allows zlib.decompress to decompress gzip-compressed strings as well.
# From zlib.h header file, not documented in Python.
ZLIB_DECODE_AUTO = 32 + zlib.MAX_WBITS

try:
    import requests
    _has_requests = True
except ImportError:
    _log.info('`requests` not available, falling back to urllib2')
    _has_requests = None

def _clean(v):
    """Convert parameters into an acceptable format for the API."""
    if isinstance(v, (list, set, tuple)):
        return ",".join(str(i) for i in v)
    else:
        return str(v)

def decompress(s):
    """Decode a gzip compressed string."""
    return zlib.decompress(s, ZLIB_DECODE_AUTO)


def parse_ts(v):
    """Parse a timestamp from EVE API XML into a unix-ish timestamp."""
    if v == '':
        return None
    ts = calendar.timegm(time.strptime(v, "%Y-%m-%d %H:%M:%S"))
    # Deal with EVE's nonexistent 0001-01-01 00:00:00 timestamp
    return ts if ts > 0 else None


def get_named_value(elem, field):
    """Returns the string value of the named child element."""
    try:
        return elem.find(field).text
    except AttributeError:
        return None


def get_ts_value(elem, field):
    """Returns the timestamp value of the named child element."""
    val = get_named_value(elem, field)
    if val:
        return parse_ts(val)
    return None


def get_int_value(elem, field):
    """Returns the integer value of the named child element."""
    val = get_named_value(elem, field)
    if val:
        return int(val)
    return val


def get_float_value(elem, field):
    """Returns the float value of the named child element."""
    val = get_named_value(elem, field)
    if val:
        return float(val)
    return val


def get_bool_value(elem, field):
    """Returns the boolean value of the named child element."""
    val = get_named_value(elem, field)
    if val == 'True':
        return True
    elif val == 'False':
        return False
    return None


def elem_getters(elem):
    """Returns a tuple of (_str, _int, _float, _bool, _ts) functions.

    These are getters closed around the provided element.
    """
    _str = lambda key: get_named_value(elem, key)
    _int = lambda key: get_int_value(elem, key)
    _float = lambda key: get_float_value(elem, key)
    _bool = lambda key: get_bool_value(elem, key)
    _ts = lambda key: get_ts_value(elem, key)

    return _str, _int, _float, _bool, _ts


def parse_keyval_data(data_string):
    """Parse 'key: value' lines from a LF-delimited string."""
    keyval_pairs = data_string.strip().split('\n')
    results = {}
    for pair in keyval_pairs:
        key, _, val = pair.strip().partition(': ')

        if 'Date' in key:
            val = parse_ms_date(val)
        elif val == 'null':
            val = None
        elif re.match(r"^-?\d+$", val):
            val = int(val)
        elif re.match(r"-?\d+\.\d+", val):
            val = float(val)

        results[key] = val
    return results

def parse_ms_date(date_string):
    """Convert MS date format into epoch"""

    return int(date_string)/10000000 - 11644473600;

class APIError(Exception):
    """Exception raised when the EVE API returns an error."""

    def __init__(self, code=None, message=None, timestamp=None, expires=None):
        self.code = code
        self.message = message
        self.timestamp = timestamp
        self.expires = expires

    def __repr__(self):
        return "APIError(%r, %r, timestamp=%r, expires=%r)" % (
            self.code, self.message, self.timestamp, self.expires)

    def __str__(self):
        return "%s (code=%d)" % (self.message, int(self.code))

class APICache(object):
    """Minimal interface for caching API requests.

    This very basic implementation simply stores values in
    memory, with no other persistence. You can subclass it
    to define a more complex/featureful/persistent cache.
    """

    def __init__(self):
        self.cache = {}

    def get(self, key):
        """Return the value referred to by 'key' if it is cached.

        key:
            a result from the Python hash() function.
        """
        result = self.cache.get(key)
        if not result:
            return None
        value, expiration = result
        if expiration < time.time():
            del self.cache[key]
            return None
        return value

    def put(self, key, value, duration):
        """Cache the provided value, referenced by 'key', for the given duration.

        key:
            a result from the Python hash() function.
        value:
            an xml.etree.ElementTree.Element object
        duration:
            a number of seconds before this cache entry should expire.
        """
        expiration = time.time() + duration
        self.cache[key] = (value, expiration)


APIResult = collections.namedtuple("APIResult", [
        "result",
        "timestamp",
        "expires",
    ])


class API(object):
    """A wrapper around the EVE API."""

    def __init__(self, base_url="api.eveonline.com", cache=None, api_key=None):
        self.base_url = base_url

        cache = cache or APICache()
        if not isinstance(cache, APICache):
            raise ValueError("The provided cache must subclass from APICache.")
        self.cache = cache
        self.CACHE_VERSION = '1'

        if api_key and len(api_key) != 2:
            raise ValueError("The provided API key must be a tuple of (keyID, vCode).")
        self.api_key = api_key
        self._set_last_timestamps()

    def _set_last_timestamps(self, current_time=0, cached_until=0):
        self.last_timestamps = {
            'current_time': current_time,
            'cached_until': cached_until,
        }

    def _cache_key(self, path, params):
        sorted_params = sorted(params.items())
        # Paradoxically, Shelve doesn't like integer keys.
        return '%s-%s' % (self.CACHE_VERSION, hash((path, tuple(sorted_params))))

    def get(self, path, params=None):
        """Request a specific path from the EVE API.

        The supplied path should be a slash-separated path
        frament, e.g. "corp/AssetList". (Basically, the portion
        of the API url in between the root / and the .xml bit.)
        """

        params = params or {}
        params = dict((k, _clean(v)) for k,v in params.items())

        _log.debug("Calling %s with params=%r", path, params)
        if self.api_key:
            _log.debug("keyID and vCode added")
            params['keyID'] = self.api_key[0]
            params['vCode'] = self.api_key[1]

        key = self._cache_key(path, params)
        response = self.cache.get(key)
        cached = response is not None

        if not cached:
            # no cached response body found, call the API for one.
            params = urllib.parse.urlencode(params)
            full_path = "https://%s/%s.xml.aspx" % (self.base_url, path)
            response = self.send_request(full_path, params)
        else:
            _log.debug("Cache hit, returning cached payload")

        tree = ElementTree.fromstring(response)
        current_time = get_ts_value(tree, 'currentTime')
        expires_time = get_ts_value(tree, 'cachedUntil')
        self._set_last_timestamps(current_time, expires_time)

        if not cached:
            # Have to split this up from above as timestamps have to be
            # extracted.
            self.cache.put(key, response, expires_time - current_time)

        error = tree.find('error')
        if error is not None:
            code = error.attrib['code']
            message = error.text.strip()
            exc = APIError(code, message, current_time, expires_time)
            _log.error("Raising API error: %r" % exc)
            raise exc

        result = tree.find('result')
        return APIResult(result, current_time, expires_time)

    def send_request(self, full_path, params):
        if _has_requests:
            return self.requests_request(full_path, params)
        else:
            return self.urllib2_request(full_path, params)

    def urllib2_request(self, full_path, params):
        r = None
        try:
            if params:
                # POST request
                _log.debug("POSTing request")
                req = urllib.request.Request(full_path, data=params.encode())
            else:
                # GET request
                req = urllib.request.Request(full_path)
                _log.debug("GETting request")

            req.add_header('Accept-Encoding', 'gzip')
            r = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            # urllib2 handles non-2xx responses by raising an exception that
            # can also behave as a file-like object. The EVE API will return
            # non-2xx HTTP codes on API errors (since Odyssey, apparently)
            r = e
        except urllib.error.URLError as e:
            # TODO: Handle this better?
            raise e

        try:
            if r.info().get('Content-Encoding') == 'gzip':
                return decompress(r.read())
            else:
                return r.read()
        finally:
            r.close()

    def requests_request(self, full_path, params):
        session = getattr(self, 'session', None)
        if not session:
            session = requests.Session()
            self.session = session

        try:
            if params:
                # POST request
                _log.debug("POSTing request")
                r = session.post(full_path, params=params)
            else:
                # GET request
                _log.debug("GETting request")
                r = session.get(full_path)
            return r.content
        except requests.exceptions.RequestException as e:
            # TODO: Handle this better?
            raise e


def auto_api(func):
    """A decorator to automatically provide an API instance.

    Functions decorated with this will have the api= kwarg
    automatically supplied with a default-initialized API()
    object if no other API object is supplied.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'api' not in kwargs:
            kwargs['api'] = API()
        return func(*args, **kwargs)
    return wrapper


def translate_args(args, mapping=None):
    """Translate python name variable into API parameter name."""
    mapping = mapping if mapping else {}
    return dict((mapping[k], v,) for k, v in args.items())

# TODO: needs better name
def get_args_and_defaults(func):
    """Return the list of argument names and a dict of default values"""
    specs = inspect.getargspec(func)
    return (
        specs.args,
        dict(zip(specs.args[-len(specs.defaults):], specs.defaults)),
    )


def map_func_args(args, kw, args_names, defaults):
    """Associate positional (*args) and key (**kw) arguments values 
    with their argument names.

    'args_names' should be the list of argument names and 'default' 
    should be a dict associating the keyword arguments to their 
    defaults.

    Similar to inspect.getcallargs() but compatible with python 2.6.

    """
    if (len(args)+len(kw)) > len(args_names):
        raise TypeError('Too many arguments.')

    map_ = dict(zip(args_names, args))
    for k, v in kw.items():
        if k in map_:
            raise TypeError(
                "got multiple values for keyword argument '%s'" % k
            )
        map_[k] = v

    for k, v in defaults.items():
        map_.setdefault(k, v)

    required_args = args_names[0:-len(defaults)]
    for k in required_args:
        if k not in map_:
            raise TypeError("Too few arguments")
    return map_


class auto_call(object):
    """A decorator to automatically provide an api response to a method.

    The object the method will be bound to should have an api attribute 
    and the method should have a keyword argument named 'api_result'.

    The decorated method will have a '_request_specs' dict attribute 
    holding:

    - 'path': path of the request needs to be queried.

    - 'args': method argument names.

    - 'defaults': method keyword arguments and theirs default value.

    - 'prop_to_param': properties of the instance the method is bound 
    to to add as parameter of api request.

    - 'map_params': dictionary associating argument name to a 
    paramater name. They will be added to 'evelink.api._args_map' to 
    translate argument names to parameter names.

    """
    
    def __init__(self, path, prop_to_param=tuple(), map_params=None):
        self.method = None

        self.path = path
        self.args = None
        self.defaults = None
        self.prop_to_param = prop_to_param
        self.map_params = map_params if map_params else {}

    def __call__(self, method):
        if self.method is not None:
            raise TypeError("This decorator method cannot be shared.")
        self.method = method
        
        wrapper = self._wrapped_method()
        
        args, self.defaults = get_args_and_defaults(self.method)

        self.args = args[1:]
        self.args.remove('api_result')
        self.defaults.pop('api_result')  # TODO: better exception

        wrapper._request_specs = {
            'path': self.path,
            'args': self.args,
            'defaults': self.defaults,
            'prop_to_param': self.prop_to_param,
            'map_params': self.map_params
        }

        return wrapper

    def _wrapped_method(self):
        
        @functools.wraps(self.method)
        def wrapper(client, *args, **kw):
            if 'api_result' in kw:
                return self.method(client, *args, **kw)
                
            args_map = map_func_args(args, kw, self.args, self.defaults)
            for attr_name in self.prop_to_param:
                args_map[attr_name] = getattr(client, attr_name, None)

            params = translate_args(args_map, self.map_params)
            params =  dict((k, v,) for k, v in params.items() if v is not None)
            
            kw['api_result'] = client.api.get(self.path, params=params)
            return self.method(client, *args, **kw)

        return wrapper
        

# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = account
from evelink import account
from evelink.appengine.api import auto_async

@auto_async
class Account(account.Account):
    __doc__ = account.Account.__doc__

    def __init__(self, api):
        self.api = api

########NEW FILE########
__FILENAME__ = api
import functools
import inspect
import time
from urllib import urlencode
from xml.etree import ElementTree

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from evelink import api



class AppEngineAPI(api.API):
    """Subclass of api.API that is compatible with Google Appengine."""

    def __init__(self, base_url="api.eveonline.com", cache=None, api_key=None):
        cache = cache or AppEngineCache()
        super(AppEngineAPI, self).__init__(base_url=base_url,
                cache=cache, api_key=api_key)

    @ndb.tasklet
    def get_async(self, path, params=None):
        """Asynchronous request a specific path from the EVE API.
        
        TODO: refactor evelink.api.API.get
        """

        params = params or {}
        params = dict((k, api._clean(v)) for k,v in params.items())

        if self.api_key:
            params['keyID'] = self.api_key[0]
            params['vCode'] = self.api_key[1]

        key = self._cache_key(path, params)
        response = yield self.cache.get_async(key)
        cached = response is not None

        if not cached:
            # no cached response body found, call the API for one.
            params = urlencode(params)
            full_path = "https://%s/%s.xml.aspx" % (self.base_url, path)
            response = yield self.send_request_async(full_path, params)

        tree = ElementTree.fromstring(response)
        current_time = api.get_ts_value(tree, 'currentTime')
        expires_time = api.get_ts_value(tree, 'cachedUntil')
        self._set_last_timestamps(current_time, expires_time)

        if not cached:
            yield self.cache.put_async(key, response, expires_time - current_time)

        error = tree.find('error')
        if error is not None:
            code = error.attrib['code']
            message = error.text.strip()
            exc = api.APIError(code, message, current_time, expires_time)
            raise exc

        result = tree.find('result')
        raise ndb.Return(api.APIResult(result, current_time, expires_time))

    def send_request(self, url, params):
        """Send a request via the urlfetch API.

        url:
            The url to fetch
        params:
            URL encoded parameters to send. If set, will use a form POST,
            otherwise a GET.
        """
        return self.send_request_async(url, params).get_result()

    @ndb.tasklet
    def send_request_async(self, url, params):
        ctx = ndb.get_context()
        result = yield ctx.urlfetch(
            url=url,
            payload=params,
            method=urlfetch.POST if params else urlfetch.GET,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
                    if params else {}
        )
        raise ndb.Return(result.content)


class AppEngineCache(api.APICache):
    """Memcache backed APICache implementation."""
    
    def get(self, key):
        return memcache.get(key)

    @ndb.tasklet
    def get_async(self, key):
        """Dummy async method.

        Memcache doesn't have an async get method.
        """
        raise ndb.Return(self.get(key))


    def put(self, key, value, duration):
        if duration < 0:
            duration = time.time() + duration
        memcache.set(key, value, time=duration)

    @ndb.tasklet
    def put_async(self, key,  value, duration):
        """Dummy async method (see get_async)."""
        self.put(key, value, duration)


class EveLinkCache(ndb.Model):
    value = ndb.PickleProperty()
    expiration = ndb.IntegerProperty()


class AppEngineDatastoreCache(api.APICache):
    """An implementation of APICache using the AppEngine datastore."""

    def __init__(self):
        super(AppEngineDatastoreCache, self).__init__()

    def get(self, cache_key):
        return self.get_async(cache_key).get_result()

    @ndb.tasklet
    def get_async(self, cache_key):
        db_key = ndb.Key(EveLinkCache, cache_key)
        result = yield db_key.get_async()

        if not result:
            raise ndb.Return(None)
        
        if result.expiration < time.time():
            yield db_key.delete_async()
            raise ndb.Return(None)
        
        raise ndb.Return(result.value)

    def put(self, cache_key, value, duration):
        self.put_async(cache_key, value, duration).get_result()

    @ndb.tasklet
    def put_async(self, cache_key, value, duration):
        expiration = int(time.time() + duration)
        cache = EveLinkCache(id=cache_key, value=value, expiration=expiration)
        yield cache.put_async()


def auto_gae_api(func):
    """A decorator to automatically provide an AppEngineAPI instance."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'api' not in kwargs:
            kwargs['api'] = AppEngineAPI()
        return func(*args, **kwargs)
    return wrapper


def _make_async(method):
    def _async(self, *args, **kw):
        # method specs
        path = method._request_specs['path']
        args_names = method._request_specs['args']
        defaults = method._request_specs['defaults']
        prop_to_param = method._request_specs['prop_to_param']
        map_params = method._request_specs['map_params']

        # build parameter map
        args_map = api.map_func_args(args, kw, args_names, defaults)
        for attr_name in prop_to_param:
            args_map[attr_name] = getattr(self, attr_name, None)

        # fix params name and remove params with None values
        params = api.translate_args(args_map, map_params)
        params =  dict((k, v,) for k, v in params.items() if v is not None)
        
        kw['api_result'] = yield self.api.get_async(path, params=params)
        raise ndb.Return(method(self, *args, **kw))
    return ndb.tasklet(_async)


def auto_async(cls):
    """Class decoration which add a async version of any method with a
    a '_request_specs' attribute (metadata added by api.auto_add).
    """
    for method_name, method in inspect.getmembers(cls, inspect.ismethod):
        if not hasattr(method, '_request_specs'):
            continue
        
        async_method = _make_async(method)
        async_method.__doc__ = """Asynchronous version of %s.""" % method_name
        async_method.__name__ = '%s_async' % method_name
        setattr(cls, async_method.__name__, async_method)
        
    return cls

########NEW FILE########
__FILENAME__ = char
from google.appengine.ext import ndb

from evelink import char, api
from evelink.appengine.api import auto_async

@auto_async
class Char(char.Char):
    __doc__ = char.Char.__doc__

    @ndb.tasklet
    def wallet_balance_async(self):
        """Asynchronous version of wallet_balance."""
        api_result = yield self.wallet_info_async()
        raise ndb.Return(
            api.APIResult(
                api_result.result['balance'],
                api_result.timestamp,
                api_result.expires
            )
        )

    @ndb.tasklet
    def event_attendees_async(self, event_id, api_result=None):
        """Asynchronous version of event_attendees."""
        api_result = yield self.calendar_attendees_async([event_id])
        raise ndb.Return(
            api.APIResult(
                api_result.result[int(event_id)],
                api_result.timestamp,
                api_result.expires
            )
        )

########NEW FILE########
__FILENAME__ = corp
from google.appengine.ext import ndb

from evelink import corp
from evelink.appengine.api import auto_async


@auto_async
class Corp(corp.Corp):
    __doc__ = corp.Corp.__doc__

    @ndb.tasklet
    def members_async(self, extended=True):
        """Returns details about each member of the corporation."""
        args = {}
        if extended:
            args['extended'] = 1
        
        api_result = yield self.api.get_async(
        	'corp/MemberTracking', params=args
        )
        raise ndb.Return(
        	self.members(extended=extended, api_result=api_result)
        )
########NEW FILE########
__FILENAME__ = eve
from google.appengine.ext import ndb

from evelink import eve, api
from evelink.appengine.api import auto_async, auto_gae_api

@auto_async
class EVE(eve.EVE):
    __doc__ = eve.EVE.__doc__

    @auto_gae_api
    def __init__(self, api=None):
        self.api = api

    @ndb.tasklet
    def character_name_from_id_async(self, char_id):
        """Asynchronous version of character_name_from_id."""
        resp = yield self.character_names_from_ids_async([char_id])
        raise ndb.Return(
            api.APIResult(
                resp.result.get(char_id), resp.timestamp, resp.expires
            )
        )

    @ndb.tasklet
    def character_id_from_name_async(self, name):
        """Asynchronous version of character_id_from_name."""
        resp = yield self.character_ids_from_names_async([name])
        raise ndb.Return(
            api.APIResult(resp.result.get(name), resp.timestamp, resp.expires)
        )

########NEW FILE########
__FILENAME__ = map
from evelink import map as map_
from evelink.appengine.api import auto_async, auto_gae_api


@auto_async
class Map(map_.Map):
    __doc__ = map_.Map.__doc__

    @auto_gae_api
    def __init__(self, api=None):
        self.api = api

########NEW FILE########
__FILENAME__ = server
from evelink import server
from evelink.appengine.api import auto_async, auto_gae_api

@auto_async
class Server(server.Server):
    __doc__ = server.Server.__doc__

    @auto_gae_api
    def __init__(self, api=None):
        self.api = api

########NEW FILE########
__FILENAME__ = shelf
import shelve

from evelink import api

class ShelveCache(api.APICache):
    """An implementation of APICache using shelve."""

    def __init__(self, path):
        super(ShelveCache, self).__init__()
        self.cache = shelve.open(path)

########NEW FILE########
__FILENAME__ = sqlite
import pickle
import time
import sqlite3

from evelink import api

class SqliteCache(api.APICache):
    """An implementation of APICache using sqlite."""

    def __init__(self, path):
        super(SqliteCache, self).__init__()
        self.connection = sqlite3.connect(path)
        cursor = self.connection.cursor()
        cursor.execute('create table if not exists cache ("key" text primary key on conflict replace,'
                       'value blob, expiration integer)')

    def get(self, key):
        cursor = self.connection.cursor()
        cursor.execute('select value, expiration from cache where "key"=?',(key,))
        result = cursor.fetchone()
        if not result:
            return None
        value, expiration = result
        if expiration < time.time():
            cursor.execute('delete from cache where "key"=?', (key,))
            self.connection.commit()
            return None
        cursor.close()
        return pickle.loads(value)

    def put(self, key, value, duration):
        expiration = time.time() + duration
        value_tuple = (key, sqlite3.Binary(pickle.dumps(value, 2)), expiration)
        cursor = self.connection.cursor()
        cursor.execute('insert into cache values (?, ?, ?)', value_tuple)
        self.connection.commit()
        cursor.close()

########NEW FILE########
__FILENAME__ = char
from evelink import api, constants
from evelink.parsing.assets import parse_assets
from evelink.parsing.contact_list import parse_contact_list
from evelink.parsing.contract_bids import parse_contract_bids
from evelink.parsing.contract_items import parse_contract_items
from evelink.parsing.contracts import parse_contracts
from evelink.parsing.industry_jobs import parse_industry_jobs
from evelink.parsing.kills import parse_kills
from evelink.parsing.orders import parse_market_orders
from evelink.parsing.wallet_journal import parse_wallet_journal
from evelink.parsing.wallet_transactions import parse_wallet_transactions


class auto_call(api.auto_call):
    """Extends 'evelink.api.auto_call' to add 'Char.char_id' as an api 
    request argument.
    """

    def __init__(self, path, map_params=None, **kw):
        map_params = map_params if map_params else {}
        map_params['char_id'] = 'characterID'

        super(auto_call, self).__init__(
            path, prop_to_param=('char_id',), map_params=map_params, **kw
        )


class Char(object):
    """Wrapper around /char/ of the EVE API.

    Note that a valid API key is required.
    """

    def __init__(self, char_id, api):
        self.api = api
        self.char_id = char_id

    @auto_call('char/AssetList')
    def assets(self, api_result=None):
        """Get information about corp assets.

        Each item is a dict, with keys 'id', 'item_type_id',
        'quantity', 'location_id', 'location_flag', and 'packaged'.
        'location_flag' denotes additional information about the
        item's location; see
        http://wiki.eve-id.net/API_Inventory_Flags for more details.

        If the item corresponds to a container, it will have a key
        'contents', which is itself a list of items in the same format
        (potentially recursively holding containers of its own).  If
        the contents do not have 'location_id's of their own, they
        inherit the 'location_id' of their parent container, for
        convenience.

        At the top level, the result is a dict mapping location ID
        (typically a solar system) to a dict containing a 'contents'
        key, which maps to a list of items.  That is, you can think of
        the top-level values as "containers" with no fields except for
        "contents" and "location_id".
        """

        return api.APIResult(parse_assets(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/ContractBids')
    def contract_bids(self, api_result=None):
        """Lists the latest bids that have been made to any recent auctions."""
        return api.APIResult(parse_contract_bids(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/ContractItems', map_params={'contract_id': 'contractID'})
    def contract_items(self, contract_id, api_result=None):
        """Lists items that a specified contract contains"""
        return api.APIResult(parse_contract_items(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/Contracts')
    def contracts(self, api_result=None):
        """Returns a record of all contracts for a specified character"""
        return api.APIResult(parse_contracts(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/WalletJournal', map_params={'before_id': 'fromID', 'limit': 'rowCount'})
    def wallet_journal(self, before_id=None, limit=None, api_result=None):
        """Returns a complete record of all wallet activity for a specified character"""
        return api.APIResult(parse_wallet_journal(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/AccountBalance')
    def wallet_info(self, api_result=None):
        """Return a given character's wallet."""
        rowset = api_result.result.find('rowset')
        row = rowset.find('row')
        result = {
            'balance': float(row.attrib['balance']),
            'id': int(row.attrib['accountID']),
            'key': int(row.attrib['accountKey']),
        }
        return api.APIResult(result, api_result.timestamp, api_result.expires)

    def wallet_balance(self):
        """Helper to return just the balance from a given character wallet"""
        api_result = self.wallet_info()
        return api.APIResult(api_result.result['balance'], api_result.timestamp, api_result.expires)

    @auto_call('char/WalletTransactions', map_params={'before_id': 'fromID', 'limit': 'rowCount'})
    def wallet_transactions(self, before_id=None, limit=None, api_result=None):
        """Returns wallet transactions for a character."""
        return api.APIResult(parse_wallet_transactions(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/IndustryJobs')
    def industry_jobs(self, api_result=None):
        """Get a list of jobs for a character"""
        return api.APIResult(parse_industry_jobs(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/KillLog', map_params={'before_kill': 'beforeKillID'})
    def kills(self, before_kill=None, api_result=None):
        """Look up recent kills for a character.

        before_kill:
            Optional. Only show kills before this kill id. (Used for paging.)
        """

        return api.APIResult(parse_kills(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/Notifications')
    def notifications(self, api_result=None):
        """Returns the message headers for notifications."""
        result = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            notification_id = int(a['notificationID'])
            result[notification_id] = {
                'id': notification_id,
                'type_id': int(a['typeID']),
                'sender_id': int(a['senderID']),
                'timestamp': api.parse_ts(a['sentDate']),
                'read': a['read'] == '1',
            }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/NotificationTexts', map_params={'notification_ids': 'IDs'})
    def notification_texts(self, notification_ids, api_result=None):
        """Returns the message bodies for notifications."""
        result = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            notification_id = int(row.attrib['notificationID'])
            notification = {'id': notification_id}
            notification.update(api.parse_keyval_data(row.text))
            result[notification_id] = notification

        missing_ids = api_result.result.find('missingIDs')
        if missing_ids is not None:
            for missing_id in missing_ids.text.split(","):
                result[missing_id] = None

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/Standings')
    def standings(self, api_result=None):
        """Returns the standings towards a character from NPC entities."""
        result = {}
        rowsets = {}
        for rowset in api_result.result.find('characterNPCStandings').findall('rowset'):
            rowsets[rowset.attrib['name']] = rowset

        _name_map = {
            'agents': 'agents',
            'corps': 'NPCCorporations',
            'factions': 'factions',
        }

        for key, rowset_name in _name_map.items():
            result[key] = {}
            for row in rowsets[rowset_name].findall('row'):
                a = row.attrib
                from_id = int(a['fromID'])
                result[key][from_id] = {
                    'id': from_id,
                    'name': a['fromName'],
                    'standing': float(a['standing']),
                }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/CharacterSheet')
    def character_sheet(self, api_result=None):
        """Returns attributes relating to a specific character."""
        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)
        result = {
            'id': _int('characterID'),
            'name': _str('name'),
            'create_ts': _ts('DoB'),
            'race': _str('race'),
            'bloodline': _str('bloodLine'),
            'ancestry': _str('ancestry'),
            'gender': _str('gender'),
            'corp': {
                'id': _int('corporationID'),
                'name': _str('corporationName'),
            },
            'alliance': {
                'id': _int('allianceID') or None,
                'name': _str('allianceName'),
            },
            'clone': {
                'name': _str('cloneName'),
                'skillpoints': _int('cloneSkillPoints'),
            },
            'balance': _float('balance'),
            'attributes': {},
        }

        for attr in ('intelligence', 'memory', 'charisma', 'perception', 'willpower'):
            result['attributes'][attr] = {}
            base = int(api_result.result.findtext('attributes/%s' % attr))
            result['attributes'][attr]['base'] = base
            result['attributes'][attr]['total'] = base
            bonus = api_result.result.find('attributeEnhancers/%sBonus' % attr)
            if bonus is not None:
                mod = int(bonus.findtext('augmentatorValue'))
                result['attributes'][attr]['total'] += mod
                result['attributes'][attr]['bonus'] = {
                    'name': bonus.findtext('augmentatorName'),
                    'value': mod,
                }

        rowsets = {}
        for rowset in api_result.result.findall('rowset'):
            key = rowset.attrib['name']
            rowsets[key] = rowset

        result['skills'] = []
        result['skillpoints'] = 0
        for skill in rowsets['skills']:
            a = skill.attrib
            sp = int(a['skillpoints'])
            result['skills'].append({
                'id': int(a['typeID']),
                'skillpoints': sp,
                'level': int(a['level']),
                'published': a['published'] == '1',
            })
            result['skillpoints'] += sp

        result['certificates'] = set()
        for cert in rowsets['certificates']:
            result['certificates'].add(int(cert.attrib['certificateID']))

        result['roles'] = {}
        for our_role, ccp_role in constants.Char().corp_roles.items():
            result['roles'][our_role] = {}
            for role in rowsets[ccp_role]:
                a = role.attrib
                role_id = int(a['roleID'])
                result['roles'][our_role][role_id] = {
                    'id': role_id,
                    'name': a['roleName'],
                }

        result['titles'] = {}
        for title in rowsets['corporationTitles']:
            a = title.attrib
            title_id = int(a['titleID'])
            result['titles'][title_id] = {
                'id': title_id,
                'name': a['titleName'],
            }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/ContactList')
    def contacts(self, api_result=None):
        """Return a character's personal, corp and alliance contact lists."""
        return api.APIResult(parse_contact_list(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/MarketOrders')
    def orders(self, api_result=None):
        """Return a given character's buy and sell orders."""
        return api.APIResult(parse_market_orders(api_result.result), api_result.timestamp, api_result.expires)

    @auto_call('char/Research')
    def research(self, api_result=None):
        """Returns information about the agents with whom the character is doing research."""
        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')
        result = {}
        for row in rows:
            a = row.attrib
            id = int(a['agentID'])
            result[id] = {
                'id': id,
                'skill_id': int(a['skillTypeID']),
                'timestamp': api.parse_ts(a['researchStartDate']),
                'per_day': float(a['pointsPerDay']),
                'remaining': float(a['remainderPoints']),
            }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/SkillInTraining')
    def current_training(self, api_result=None):
        """Returns the skill that is currently being trained by a specified character"""
        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)
        result = {
            'start_ts': _ts('trainingStartTime'),
            'end_ts': _ts('trainingEndTime'),
            'type_id': _int('trainingTypeID'),
            'start_sp': _int('trainingStartSP'),
            'end_sp': _int('trainingDestinationSP'),
            'current_ts': _ts('currentTQTime'),
            'level': _int('trainingToLevel'),
            'active': _bool('skillInTraining'),
        }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/SkillQueue')
    def skill_queue(self, api_result=None):
        """returns the skill queue of the character"""
        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')
        result = []
        for row in rows:
            a = row.attrib
            line = {
                'position': int(a['queuePosition']),
                'type_id': int(a['typeID']),
                'level': int(a['level']),
                'start_sp': int(a['startSP']),
                'end_sp': int(a['endSP']),
                'start_ts': api.parse_ts(a['startTime']),
                'end_ts': api.parse_ts(a['endTime']),
            }

            result.append(line)

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/MailMessages')
    def messages(self, api_result=None):
        """Returns a list of headers for a character's mail."""
        rowset = api_result.result.find('rowset')
        results = []
        for row in rowset.findall('row'):
            a = row.attrib
            message = {
                'id': int(a['messageID']),
                'sender_id': int(a['senderID']),
                'timestamp': api.parse_ts(a['sentDate']),
                'title': a['title'],
                'to': {},
            }

            org_id = a['toCorpOrAllianceID']
            message['to']['org_id'] = int(org_id) if org_id else None

            char_ids = a['toCharacterIDs']
            message['to']['char_ids'] = [int(i) for i in char_ids.split(',')] if char_ids else None

            list_ids = a['toListID']
            message['to']['list_ids'] = [int(i) for i in list_ids.split(',')] if list_ids else None

            results.append(message)

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @auto_call('char/MailBodies', map_params={'message_ids': 'ids'})
    def message_bodies(self, message_ids, api_result=None):
        """Returns the actual body content of a set of mail messages.

        NOTE: You *must* have recently looked up the headers of
        any messages you are requesting bodies for (via the 'messages'
        method) or else this call will fail.
        """

        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            message_id = int(row.attrib['messageID'])
            results[message_id] = row.text

        missing_set = api_result.result.find('missingMessageIDs')
        if missing_set is not None:
            missing_ids = [int(i) for i in missing_set.text.split(',')]
            for missing_id in missing_ids:
                results[missing_id] = None

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @auto_call('char/MailingLists')
    def mailing_lists(self, api_result=None):
        """Returns the mailing lists to which a character is subscribed."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            results[int(a['listID'])] = a['displayName']

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @auto_call('char/UpcomingCalendarEvents')
    def calendar_events(self, api_result=None):
        """Returns the list of upcoming calendar events for a character."""
        results = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            event = {
                'id': int(a['eventID']),
                'owner': {
                    'id': int(a['ownerID']),
                    'name': a['ownerName'] or None,
                },
                'start_ts': api.parse_ts(a['eventDate']),
                'title': a['eventTitle'],
                'duration': int(a['duration']),
                'important': a['importance'] == '1',
                'description': a['eventText'],
                'response': a['response'],
            }
            results[event['id']] = event

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @auto_call('char/CalendarEventAttendees', map_params={'event_ids': 'eventIDs'})
    def calendar_attendees(self, event_ids, api_result=None):
        """Returns the list of attendees for the specified calendar event.

        This function takes a list of event IDs and returns a dict of dicts,
        with the top-level dict being keyed by event ID and the children
        keyed by the character IDs of the attendees.

        NOTE: You must have recently fetched the list of calendar events
        (using the 'calendar_events' method) before calling this method.
        """

        results = dict((int(i),{}) for i in event_ids)
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            attendee = {
                'id': int(a['characterID']),
                'name': a['characterName'],
                'response': a['response'],
            }
            results[int(a['eventID'])][attendee['id']] = attendee

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    def event_attendees(self, event_id, api_result=None):
        """Returns the attendees for a single event.

        (This is a convenience wrapper around 'calendar_attendees'.)

        NOTE: You must have recently fetched the list of calendar events
        (using the 'calendar_events' method) before calling this method.
        """

        api_result = self.calendar_attendees([event_id])
        return api.APIResult(api_result.result[int(event_id)], api_result.timestamp, api_result.expires)

    @auto_call('char/FacWarStats')
    def faction_warfare_stats(self, api_result=None):
        """Returns FW stats for this character, if enrolled in FW.

        NOTE: This will return an error instead if the character
        is not enrolled in Faction Warfare.

        """
        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)

        result = {
            'faction': {
                'id': _int('factionID'),
                'name': _str('factionName'),
            },
            'enlist_ts': _ts('enlisted'),
            'rank': {
                'current': _int('currentRank'),
                'highest': _int('highestRank'),
            },
            'kills': {
                'yesterday': _int('killsYesterday'),
                'week': _int('killsLastWeek'),
                'total': _int('killsTotal'),
            },
            'points': {
                'yesterday': _int('victoryPointsYesterday'),
                'week': _int('victoryPointsLastWeek'),
                'total': _int('victoryPointsTotal'),
            },
        }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/Medals')
    def medals(self, api_result=None):
        """Returns a list of medals the character has."""
        result = {'current': {}, 'other': {}}
        _map = {
            'currentCorporation': 'current',
            'otherCorporations': 'other',
        }

        for rowset in api_result.result.findall('rowset'):
            name = _map[rowset.attrib['name']]
            for row in rowset.findall('row'):
                a = row.attrib
                medal_id = int(a['medalID'])
                result[name][medal_id] = {
                    'id': medal_id,
                    'reason': a['reason'],
                    'public': a['status'] == 'public',
                    'issuer_id': int(a['issuerID']),
                    'corp_id': int(a['corporationID']),
                    'title': a['title'],
                    'description': a['description'],
                }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @auto_call('char/ContactNotifications')
    def contact_notifications(self, api_result=None):
        """Returns pending contact notifications."""
        results = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            note = {
                'id': int(a['notificationID']),
                'sender': {
                    'id': int(a['senderID']),
                    'name': a['senderName'],
                },
                'timestamp': api.parse_ts(a['sentDate']),
                'data': api.parse_keyval_data(a['messageData']),
            }
            results[note['id']] = note

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @auto_call('char/Locations', map_params={'location_list': 'IDs'})
    def locations(self, location_list, api_result=None):
        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')

        results = {}
        for row in rows:
            name = row.attrib['itemName'] or None
            id = int(row.attrib['itemID']) or None
            x = float(row.attrib['x']) or None
            y = float(row.attrib['y']) or None
            z = float(row.attrib['z']) or None

            results[id] = {
                'name': name,
                'id' : id,
                'x' : x,
                'y' : y,
                'z' : z,
            }
        return api.APIResult(results, api_result.timestamp, api_result.expires)


# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = constants
ACCOUNT = 'account'
CHARACTER = 'char'
CORPORATION = 'corp'

BLUEPRINT_ORIGINAL = -1
BLUEPRINT_COPY = -2

_role_type_bases = {
    'global': '',
    'at_hq': 'AtHQ',
    'at_base': 'AtBase',
    'at_other': 'AtOther',
}

class Char(object):
    corp_roles = dict((k, 'corporationRoles' + v) for k,v in _role_type_bases.items())

class Corp(object):
    role_types = dict((k, 'roles' + v) for k,v in _role_type_bases.items())
    grantable_types = dict((k, 'grantableRoles' + v) for k,v in _role_type_bases.items())

    pos_states = ('unanchored', 'anchored', 'onlining', 'reinforced', 'online')

    pos_permission_entities = (
            'Starbase Config',
            'Starbase Fuel Tech',
            'Corporation Members',
            'Alliance Members',
        )

class Industry(object):
    job_status = ('failed', 'delivered', 'aborted', 'gm-aborted', 'inflight-unanchored', 'destroyed')

class Market(object):
    order_status = ('active', 'closed', 'expired', 'cancelled', 'pending', 'deleted')

class APIKey(object):
    key_types = {
        # This maps from EVE API values (keys) to our local constants (values)
        'Account': ACCOUNT,
        'Character': CHARACTER,
        'Corporation': CORPORATION,
    }

########NEW FILE########
__FILENAME__ = corp
from evelink import api, constants
from evelink.parsing.assets import parse_assets
from evelink.parsing.contact_list import parse_contact_list
from evelink.parsing.contract_bids import parse_contract_bids
from evelink.parsing.contract_items import parse_contract_items
from evelink.parsing.contracts import parse_contracts
from evelink.parsing.industry_jobs import parse_industry_jobs
from evelink.parsing.kills import parse_kills
from evelink.parsing.orders import parse_market_orders
from evelink.parsing.wallet_journal import parse_wallet_journal
from evelink.parsing.wallet_transactions import parse_wallet_transactions


class Corp(object):
    """Wrapper around /corp/ of the EVE API.

    Note that a valid corp API key is required.
    """

    def __init__(self, api):
        self.api = api

    @api.auto_call('corp/CorporationSheet', map_params={'corp_id': 'corporationID'})
    def corporation_sheet(self, corp_id=None, api_result=None):
        """Get information about a corporation.

        NOTE: This method may be called with or without specifying
        a corporation ID. If a corporation ID is specified, the public
        information for that corporation will be returned, and no api
        key is necessary. If a corporation ID is *not* specified,
        a corp api key *must* be provided, and the private information
        for that corporation will be returned along with the public info.
        """

        def get_logo_details(logo_result):
            _str, _int, _float, _bool, _ts = api.elem_getters(logo_result)
            return {
                'graphic_id': _int('graphicID'),
                'shapes': [
                    {'id': _int('shape1'), 'color': _int('color1')},
                    {'id': _int('shape2'), 'color': _int('color2')},
                    {'id': _int('shape3'), 'color': _int('color3')},
                ],
            }

        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)

        result = {
            'id': _int('corporationID'),
            'name': _str('corporationName'),
            'ticker': _str('ticker'),
            'ceo': {
                'id': _int('ceoID'),
                'name': _str('ceoName'),
            },
            'hq': {
                'id': _int('stationID'),
                'name': _str('stationName'),
            },
            'description': _str('description'),
            'url': _str('url'),
            'alliance': {
                'id': _int('allianceID') or None,
                'name': _str('allianceName') or None,
            },
            'tax_percent': _float('taxRate'),
            'members': {
                'current': _int('memberCount'),
            },
            'shares': _int('shares'),
            'logo': get_logo_details(api_result.result.find('logo')),
        }

        if corp_id is None:
            result['members']['limit'] = _int('memberLimit')

            rowsets = dict((r.attrib['name'], r) for r in api_result.result.findall('rowset'))

            division_types = {
                'hangars': 'divisions',
                'wallets': 'walletDivisions',
            }

            for key, rowset_name in division_types.items():
                divisions = {}
                for row in rowsets[rowset_name].findall('row'):
                    a = row.attrib
                    divisions[int(a['accountKey'])] = a['description']

                result[key] = divisions

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/IndustryJobs')
    def industry_jobs(self, api_result=None):
        """Get a list of jobs for a corporation."""
        return api.APIResult(parse_industry_jobs(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/Standings')
    def npc_standings(self, api_result=None):
        """Returns information about the corporation's standings towards NPCs.

        NOTE: This is *only* NPC standings. Player standings are accessed
        via the 'contacts' method.
        """

        container = api_result.result.find('corporationNPCStandings')

        rowsets = dict((r.attrib['name'], r) for r in container.findall('rowset'))
        results = {
            'agents': {},
            'corps': {},
            'factions': {},
        }

        _standing_types = {
            'agents': 'agents',
            'corps': 'NPCCorporations',
            'factions': 'factions',
        }

        for key, rowset_name in _standing_types.items():
            for row in rowsets[rowset_name].findall('row'):
                a = row.attrib
                standing = {
                    'id': int(a['fromID']),
                    'name': a['fromName'],
                    'standing': float(a['standing']),
                }
                results[key][standing['id']] = standing

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/KillLog', map_params={'before_kill': 'beforeKillID'})
    def kills(self, before_kill=None, api_result=None):
        """Look up recent kills for a corporation.

        before_kill:
            Optional. Only show kills before this kill id. (Used for paging.)
        """

        return api.APIResult(parse_kills(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/AccountBalance')
    def wallet_info(self, api_result=None):
        """Get information about corp wallets."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            wallet = {
                'balance': float(row.attrib['balance']),
                'id': int(row.attrib['accountID']),
                'key': int(row.attrib['accountKey']),
            }
            results[wallet['key']] = wallet

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/WalletJournal', map_params={'before_id': 'fromID', 'limit': 'rowCount', 'account': 'accountKey'})
    def wallet_journal(self, before_id=None, limit=None, account=None, api_result=None):
        """Returns wallet journal for a corporation."""
        return api.APIResult(parse_wallet_journal(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/WalletTransactions', map_params={'before_id': 'fromID', 'limit': 'rowCount', 'account': 'accountKey'})
    def wallet_transactions(self, before_id=None, limit=None, account=None, api_result=None):
        """Returns wallet transactions for a corporation."""
        return api.APIResult(parse_wallet_transactions(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/MarketOrders')
    def orders(self, api_result=None):
        """Return a corporation's buy and sell orders."""
        return api.APIResult(parse_market_orders(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/AssetList')
    def assets(self, api_result=None):
        """Get information about corp assets.

        Each item is a dict, with keys 'id', 'item_type_id',
        'quantity', 'location_id', 'location_flag', and 'packaged'.
        'location_flag' denotes additional information about the
        item's location; see
        http://wiki.eve-id.net/API_Inventory_Flags for more details.

        If the item corresponds to a container, it will have a key
        'contents', which is itself a list of items in the same format
        (potentially recursively holding containers of its own).  If
        the contents do not have 'location_id's of their own, they
        inherit the 'location_id' of their parent container, for
        convenience.

        At the top level, the result is a dict mapping location ID
        (typically a solar system) to a dict containing a 'contents'
        key, which maps to a list of items.  That is, you can think of
        the top-level values as "containers" with no fields except for
        "contents" and "location_id".
        """

        return api.APIResult(parse_assets(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/FacWarStats')
    def faction_warfare_stats(self, api_result=None):
        """Returns stats from faction warfare if this corp is enrolled.

        NOTE: This will raise an APIError if the corp is not enrolled in
        Faction Warfare.
        """

        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)

        result = {
            'faction': {
                'id': _int('factionID'),
                'name': _str('factionName'),
            },
            'start_ts': _ts('enlisted'),
            'pilots': _int('pilots'),
            'kills': {
                'yesterday': _int('killsYesterday'),
                'week': _int('killsLastWeek'),
                'total': _int('killsTotal'),
            },
            'points': {
                'yesterday': _int('victoryPointsYesterday'),
                'week': _int('victoryPointsLastWeek'),
                'total': _int('victoryPointsTotal'),
            },
        }

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/ContractBids')
    def contract_bids(self, api_result=None):
        """Lists the latest bids that have been made to any recent auctions."""
        return api.APIResult(parse_contract_bids(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/ContractItems', map_params={'contract_id': 'contractID'})
    def contract_items(self, contract_id, api_result=None):
        """Lists items that a specified contract contains"""
        return api.APIResult(parse_contract_items(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/Contracts')
    def contracts(self, api_result=None):
        """Get information about corp contracts."""
        return api.APIResult(parse_contracts(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/Shareholders')
    def shareholders(self, api_result=None):
        """Get information about a corp's shareholders."""
        results = {
            'char': {},
            'corp': {},
        }
        rowsets = dict((r.attrib['name'], r) for r in api_result.result.findall('rowset'))

        for row in rowsets['characters'].findall('row'):
            a = row.attrib
            holder = {
                'id': int(a['shareholderID']),
                'name': a['shareholderName'],
                'corp': {
                    'id': int(a['shareholderCorporationID']),
                    'name': a['shareholderCorporationName'],
                },
                'shares': int(a['shares']),
            }
            results['char'][holder['id']] = holder

        for row in rowsets['corporations'].findall('row'):
            a = row.attrib
            holder = {
                'id': int(a['shareholderID']),
                'name': a['shareholderName'],
                'shares': int(a['shares']),
            }
            results['corp'][holder['id']] = holder

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/ContactList')
    def contacts(self, api_result=None):
        """Return the corp's corp and alliance contact lists."""
        return api.APIResult(parse_contact_list(api_result.result), api_result.timestamp, api_result.expires)

    @api.auto_call('corp/Titles')
    def titles(self, api_result=None):
        """Returns information about the corporation's titles."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            title = {
                'id': int(a['titleID']),
                'name': a['titleName'],
                'roles': {},
                'can_grant': {},
            }
            rowsets = dict((r.attrib['name'], r) for r in row.findall('rowset'))

            def get_roles(rowset_name):
                roles = {}
                for role_row in rowsets[rowset_name].findall('row'):
                    ra = role_row.attrib
                    role = {
                        'id': int(ra['roleID']),
                        'name': ra['roleName'],
                        'description': ra['roleDescription'],
                    }
                    roles[role['id']] = role
                return roles

            for key, rowset_name in constants.Corp.role_types.items():
                roles = get_roles(rowset_name)
                title['roles'][key] = roles

            for key, rowset_name in constants.Corp.grantable_types.items():
                roles = get_roles(rowset_name)
                title['can_grant'][key] = roles

            results[title['id']] = title

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/StarbaseList')
    def starbases(self, api_result=None):
        """Returns information about the corporation's POSes."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            starbase = {
                'id': int(a['itemID']),
                'type_id': int(a['typeID']),
                'location_id': int(a['locationID']),
                'moon_id': int(a['moonID']),
                'state': constants.Corp.pos_states[int(a['state'])],
                'state_ts': api.parse_ts(a['stateTimestamp']),
                'online_ts': api.parse_ts(a['onlineTimestamp']),
                'standings_owner_id': int(a['standingOwnerID']),
            }
            results[starbase['id']] = starbase

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/StarbaseDetail', map_params={'starbase_id': 'itemID'})
    def starbase_details(self, starbase_id, api_result=None):
        """Returns details about the specified POS."""
        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)

        general_settings = api_result.result.find('generalSettings')
        combat_settings = api_result.result.find('combatSettings')

        def get_fuel_bay_perms(settings):
            # Two 2-bit fields
            usage_flags = int(settings.find('usageFlags').text)
            take_value = usage_flags % 4
            view_value = (usage_flags >> 2) % 4
            return {
                'view': constants.Corp.pos_permission_entities[view_value],
                'take': constants.Corp.pos_permission_entities[take_value],
            }

        def get_deploy_perms(settings):
            # Four 2-bit fields
            deploy_flags = int(settings.find('deployFlags').text)
            anchor_value = (deploy_flags >> 6) % 4
            unanchor_value = (deploy_flags >> 4) % 4
            online_value = (deploy_flags >> 2) % 4
            offline_value = deploy_flags % 4
            return {
                'anchor': constants.Corp.pos_permission_entities[anchor_value],
                'unanchor': constants.Corp.pos_permission_entities[unanchor_value],
                'online': constants.Corp.pos_permission_entities[online_value],
                'offline': constants.Corp.pos_permission_entities[offline_value],
            }

        def get_combat_settings(settings):
            result = {
                'standings_owner_id': int(settings.find('useStandingsFrom').attrib['ownerID']),
                'hostility': {},
            }

            hostility = result['hostility']

            # TODO(ayust): The fields returned by the API don't completely match up with
            # the fields available in-game. May want to revisit this in the future.

            standing = settings.find('onStandingDrop')
            hostility['standing'] = {
                'threshold': float(standing.attrib['standing']) / 100,
                'enabled': standing.attrib.get('enabled') != '0',
            }

            sec_status = settings.find('onStatusDrop')
            hostility['sec_status'] = {
                'threshold': float(sec_status.attrib['standing']) / 100,
                'enabled': sec_status.attrib.get('enabled') != '0',
            }

            hostility['aggression'] = {
                'enabled': settings.find('onAggression').get('enabled') != '0',
            }

            hostility['war'] = {
                'enabled': settings.find('onCorporationWar').get('enabled') != '0',
            }

            return result

        result = {
            'state': constants.Corp.pos_states[_int('state')],
            'state_ts': _ts('stateTimestamp'),
            'online_ts': _ts('onlineTimestamp'),
            'permissions': {
                'fuel': get_fuel_bay_perms(general_settings),
                'deploy': get_deploy_perms(general_settings),
                'forcefield': {
                    'corp': general_settings.find('allowCorporationMembers').text == '1',
                    'alliance': general_settings.find('allowAllianceMembers').text == '1',
                },
            },
            'combat': get_combat_settings(combat_settings),
            'fuel': {},
        }

        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            result['fuel'][int(a['typeID'])] = int(a['quantity'])

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    def members(self, extended=True, api_result=None):
        """Returns details about each member of the corporation."""
        if api_result is None:
            args = {}
            if extended:
                args['extended'] = 1
            api_result = self.api.get('corp/MemberTracking', params=args)

        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            member = {
                'id': int(a['characterID']),
                'name': a['name'],
                'join_ts': api.parse_ts(a['startDateTime']),
                'base': {
                    # TODO(aiiane): Maybe remove this?
                    # It doesn't seem to ever have a useful value.
                    'id': int(a['baseID']),
                    'name': a['base'],
                },
                # Note that title does not include role titles,
                # only ones like 'CEO'
                'title': a['title'],
            }
            if extended:
                member.update({
                    'logon_ts': api.parse_ts(a['logonDateTime']),
                    'logoff_ts': api.parse_ts(a['logoffDateTime']),
                    'location': {
                        'id': int(a['locationID']),
                        'name': a['location'],
                    },
                    'ship_type': {
                        # "Not available" = -1 ship id; we change to None
                        'id': max(int(a['shipTypeID']), 0) or None,
                        'name': a['shipType'] or None,
                    },
                    'roles': int(a['roles']),
                    'can_grant': int(a['grantableRoles']),
                })

            results[member['id']] = member

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/MemberSecurity')
    def permissions(self, api_result=None):
        """Returns information about corporation member permissions."""
        results = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            member = {
                'id': int(a['characterID']),
                'name': a['name'],
                'titles': {},
            }

            rowsets = dict((r.attrib['name'], r) for r in row.findall('rowset'))

            for title_row in rowsets['titles'].findall('row'):
                a = title_row.attrib
                member['titles'][int(a['titleID'])] = a['titleName']

            def get_roleset(roles_dict):
                roles_group = {}
                for key, rowset_name in roles_dict.items():
                    roles = {}
                    roles_rowset = rowsets[rowset_name]
                    for role_row in roles_rowset.findall('row'):
                        a = role_row.attrib
                        roles[int(a['roleID'])] = a['roleName']
                    roles_group[key] = roles
                return roles_group

            member['roles'] = get_roleset(constants.Corp.role_types)
            member['can_grant'] = get_roleset(constants.Corp.grantable_types)

            results[member['id']] = member

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/MemberSecurityLog')
    def permissions_log(self, api_result=None):
        """Returns information about changes to member permissions."""
        inverse_role_types = dict((v,k) for k,v in constants.Corp.role_types.items())

        results = []
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            a = row.attrib
            change = {
                'timestamp': api.parse_ts(a['changeTime']),
                'recipient': {
                    'id': int(a['characterID']),
                    'name': a['characterName'],
                },
                'issuer': {
                    'id': int(a['issuerID']),
                    'name': a['issuerName'],
                },
                'role_type': inverse_role_types[a['roleLocationType']],
                'roles': {
                    'before': {},
                    'after': {},
                },
            }

            rowsets = dict((r.attrib['name'], r) for r in row.findall('rowset'))
            old, new = change['roles']['before'], change['roles']['after']

            for role_row in rowsets['oldRoles'].findall('row'):
                a = role_row.attrib
                old[int(a['roleID'])] = a['roleName']

            for role_row in rowsets['newRoles'].findall('row'):
                a = role_row.attrib
                new[int(a['roleID'])] = a['roleName']

            results.append(change)

        results.sort(key=lambda r: r['timestamp'], reverse=True)
        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/OutpostList')
    def stations(self, api_result=None):
        """Returns information about the corporation's (non-POS) stations."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            station = {
                'id': int(a['stationID']),
                'owner_id': int(a['ownerID']),
                'name': a['stationName'],
                'system_id': int(a['solarSystemID']),
                'docking_fee_per_volume': float(a['dockingCostPerShipVolume']),
                'office_fee': int(a['officeRentalCost']),
                'type_id': int(a['stationTypeID']),
                'reprocessing': {
                    'efficiency': float(a['reprocessingEfficiency']),
                    'cut': float(a['reprocessingStationTake']),
                },
                'standing_owner_id': int(a['standingOwnerID']),
            }
            results[station['id']] = station

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/OutpostServiceDetail', map_params={'station_id': 'itemID'})
    def station_services(self, station_id, api_result=None):
        """Returns information about a given station's services."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            service = {
                'name': a['serviceName'],
                'owner_id': int(a['ownerID']),
                'standing': {
                    'minimum': float(a['minStanding']),
                    'bad_surcharge': float(a['surchargePerBadStanding']),
                    'good_discount': float(a['discountPerGoodStanding']),
                },
            }
            results[service['name']] = service

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/Medals')
    def medals(self, api_result=None):
        """Returns information about the medals created by a corporation."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            medal = {
                'id': int(a['medalID']),
                'creator_id': int(a['creatorID']),
                'title': a['title'],
                'description': a['description'],
                'create_ts': api.parse_ts(a['created']),
            }
            results[medal['id']] = medal

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/MemberMedals')
    def member_medals(self, api_result=None):
        """Returns information about medals assigned to corporation members."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            award = {
                'medal_id': int(a['medalID']),
                'char_id': int(a['characterID']),
                'reason': a['reason'],
                'public': a['status'] == 'public',
                'issuer_id': int(a['issuerID']),
                'timestamp': api.parse_ts(a['issued']),
            }
            results.setdefault(award['char_id'], {})[award['medal_id']] = award

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/ContainerLog')
    def container_log(self, api_result=None):
        """Returns a log of actions performed on corporation containers."""
        results = []
        rowset = api_result.result.find('rowset')

        def int_or_none(val):
            return int(val) if val else None

        for row in rowset.findall('row'):
            a = row.attrib
            action = {
                'timestamp': api.parse_ts(a['logTime']),
                'item': {
                    'id': int(a['itemID']),
                    'type_id': int(a['itemTypeID']),
                },
                'actor': {
                    'id': int(a['actorID']),
                    'name': a['actorName'],
                },
                'location_id': int(a['locationID']),
                'action': a['action'],
                'details': {
                    # TODO(aiiane): Find a translation for this flag field
                    'flag': int(a['flag']),
                    'password_type': a['passwordType'] or None,
                    'type_id': int_or_none(a['typeID']),
                    'quantity': int_or_none(a['quantity']),
                    'config': {
                        'old': int_or_none(a['oldConfiguration']),
                        'new': int_or_none(a['newConfiguration']),
                    },
                },
            }
            results.append(action)

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('corp/Locations', map_params={'location_list': 'IDs'})
    def locations(self, location_list, api_result=None):
        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')

        results = {}
        for row in rows:
            name = row.attrib['itemName'] or None
            id = int(row.attrib['itemID']) or None
            x = float(row.attrib['x']) or None
            y = float(row.attrib['y']) or None
            z = float(row.attrib['z']) or None

            results[id] = {
                'name': name,
                'id' : id,
                'x' : x,
                'y' : y,
                'z' : z,
            }

        return api.APIResult(results, api_result.timestamp, api_result.expires)



# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = eve
from evelink import api

class EVE(object):
    """Wrapper around /eve/ of the EVE API."""

    @api.auto_api
    def __init__(self, api=None):
        self.api = api

    @api.auto_call('eve/CertificateTree')
    def certificate_tree(self, api_result=None):
        """Returns a list of certificates in eve."""

        result = {}
        rowset = api_result.result.find('rowset')
        categories = rowset.findall('row')

        for category in categories:
            cat_attr = category.attrib
            cat_name = cat_attr['categoryName']
            cat_tree = {
                'name': cat_name,
                'id': int(cat_attr['categoryID']),
                'classes': {},
            }

            cls_rowset = category.find('rowset')
            classes = cls_rowset.findall('row')
            for cls in classes:
                cls_attr = cls.attrib
                cls_name = cls_attr['className']
                cls_def = {
                    'name': cls_name,
                    'id': int(cls_attr['classID']),
                    'certificates': {}
                }

                cert_rowset = cls.find('rowset')
                certificates = cert_rowset.findall('row')
                for cert in certificates:
                    cert_attr = cert.attrib
                    cert_id = int(cert_attr['certificateID'])
                    cert_entry = {
                      'id': cert_id,
                      'grade': int(cert_attr['grade']),
                      'corp_id': int(cert_attr['corporationID']),
                      'description': cert_attr['description'],
                      'required_skills': {},
                      'required_certs': {}
                    }

                    req_rowsets = {}
                    for rowset in cert.findall('rowset'):
                      req_rowsets[rowset.attrib['name']] = rowset

                    req_skills = req_rowsets['requiredSkills'].findall('row')
                    for skill in req_skills:
                        cert_entry['required_skills'][
                          int(skill.attrib['typeID'])
                        ] = int(skill.attrib['level'])

                    req_certs = req_rowsets['requiredCertificates'].findall('row')
                    for req_cert in req_certs:
                        cert_entry['required_certs'][
                          int(req_cert.attrib['certificateID'])
                        ] = int(req_cert.attrib['grade'])


                    cls_def['certificates'][cert_id] = cert_entry

                cat_tree['classes'][cls_name] = cls_def

            result[cat_name] = cat_tree

        return api.APIResult(result, api_result.timestamp, api_result.expires)

    @api.auto_call('eve/CharacterName', map_params={'id_list': 'IDs'})
    def character_names_from_ids(self, id_list, api_result=None):
        """Retrieve a dict mapping character IDs to names.

        id_list:
            A list of ids to retrieve names.

        NOTE: *ALL* character IDs passed to this function
        must be valid - an invalid character ID will cause
        the entire call to fail.
        """
        
        if api_result is None:
            # The API doesn't actually tell us which character IDs are invalid
            msg = "One or more of these character IDs are invalid: %r"
            raise ValueError(msg % id_list)

        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')

        results = {}
        for row in rows:
            name = row.attrib['name']
            char_id = int(row.attrib['characterID'])
            results[char_id] = name

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    def character_name_from_id(self, char_id):
        """Retrieve the character's name based on ID.

        Convenience wrapper around character_names_from_ids().
        """
        api_result = self.character_names_from_ids([char_id])
        return api.APIResult(api_result.result.get(char_id), api_result.timestamp, api_result.expires)

    @api.auto_call('eve/CharacterID', map_params={'name_list': 'names'})
    def character_ids_from_names(self, name_list, api_result=None):
        """Retrieve a dict mapping character names to IDs.

        name_list:
            A list of names to retrieve character IDs.

        Names of unknown characters will map to None.
        """

        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')

        results = {}
        for row in rows:
            name = row.attrib['name']
            char_id = int(row.attrib['characterID']) or None
            results[name] = char_id

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    def character_id_from_name(self, name):
        """Retrieve the named character's ID.

        Convenience wrapper around character_ids_from_names().
        """
        api_result = self.character_ids_from_names([name])
        return api.APIResult(api_result.result.get(name), api_result.timestamp, api_result.expires)

    @api.auto_call('eve/CharacterAffiliation', map_params={'id_list': 'ids'})
    def affiliations_for_characters(self, id_list, api_result=None):
        """Retrieve the affiliations for a set of character IDs, returned as a dictionary.

        name_list:
            A list of names to retrieve IDs for.

        IDs for anything not a character will be returned with a name, but nothing else.
        """

        rowset = api_result.result.find('rowset')
        rows = rowset.findall('row')

        results = {}
        for row in rows:
            char_id = int(row.attrib['characterID'])
            char_name = row.attrib['characterName']
            corp_id = int(row.attrib['corporationID']) or None
            corp_name = row.attrib['corporationName'] or None
            faction_id = int(row.attrib['factionID']) or None
            faction_name = row.attrib['factionName'] or None
            alliance_id = int(row.attrib['allianceID']) or None
            alliance_name = row.attrib['allianceName'] or None
            results[char_id] = {
                'id': char_id,
                'name': char_name,
                'corp': {
                    'id': corp_id,
                    'name': corp_name
                }
            }

            if faction_id is not None:
                results[char_id]['faction'] = {
                    'id': faction_id,
                    'name': faction_name
                }

            if alliance_id is not None:
                results[char_id]['alliance'] = {
                    'id': alliance_id,
                    'name': alliance_name
                }

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    def affiliations_for_character(self, char_id):
        """Retrieve the affiliations of a single character

        Convenience wrapper around owner_ids_from_names().
        """

        api_result = self.affiliations_for_characters([char_id])
        return api.APIResult(api_result.result[char_id], api_result.timestamp, api_result.expires)

    @api.auto_call('eve/CharacterInfo', map_params={'char_id': 'characterID'})
    def character_info_from_id(self, char_id, api_result=None):
        """Retrieve a dict of info about the designated character."""
        if api_result is None:
            raise ValueError("Unable to fetch info for character %r" % char_id)

        _str, _int, _float, _bool, _ts = api.elem_getters(api_result.result)

        results = {
            'id': _int('characterID'),
            'name': _str('characterName'),
            'race': _str('race'),
            'bloodline': _str('bloodline'),
            'sec_status': _float('securityStatus'),
            'skillpoints': _int('skillPoints'),
            'location': _str('lastKnownLocation'),
            'isk': _float('accountBalance'),

            'corp': {
                'id': _int('corporationID'),
                'name': _str('corporation'),
                'timestamp': _ts('corporationDate'),
            },

            'alliance': {
                'id': _int('allianceID'),
                'name': _str('alliance'),
                'timestamp': _ts('allianceDate'),
            },

            'ship': {
                'name': _str('shipName'),
                'type_id': _int('shipTypeID'),
                'type_name': _str('shipTypeName'),
            },

            'history': [],
        }

        # Add in corp history
        history = api_result.result.find('rowset')
        for row in history.findall('row'):
            corp_id = int(row.attrib['corporationID'])
            start_date = api.parse_ts(row.attrib['startDate'])
            results['history'].append({
                    'corp_id': corp_id,
                    'start_ts': start_date,
                })

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('eve/AllianceList')
    def alliances(self, api_result=None):
        """Return a dict of all alliances in EVE."""
        results = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            alliance = {
                'name': row.attrib['name'],
                'ticker': row.attrib['shortName'],
                'id': int(row.attrib['allianceID']),
                'executor_id': int(row.attrib['executorCorpID']),
                'member_count': int(row.attrib['memberCount']),
                'timestamp': api.parse_ts(row.attrib['startDate']),
                'member_corps': {},
            }

            corp_rowset = row.find('rowset')
            for corp_row in corp_rowset.findall('row'):
                corp_id = int(corp_row.attrib['corporationID'])
                corp_ts = api.parse_ts(corp_row.attrib['startDate'])
                alliance['member_corps'][corp_id] = {
                    'id': corp_id,
                    'timestamp': corp_ts,
                }

            results[alliance['id']] = alliance

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('eve/ErrorList')
    def errors(self, api_result=None):
        """Return a mapping of error codes to messages."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            code = int(row.attrib['errorCode'])
            message = row.attrib['errorText']
            results[code] = message

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('eve/FacWarStats')
    def faction_warfare_stats(self, api_result=None):
        """Return various statistics from Faction Warfare."""
        totals = api_result.result.find('totals')
        rowsets = dict((r.attrib['name'], r) for r in api_result.result.findall('rowset'))

        _str, _int, _float, _bool, _ts = api.elem_getters(totals)
        results = {
            'kills': {
                'yesterday': _int('killsYesterday'),
                'week': _int('killsLastWeek'),
                'total': _int('killsTotal'),
            },
            'points': {
                'yesterday': _int('victoryPointsYesterday'),
                'week': _int('victoryPointsLastWeek'),
                'total': _int('victoryPointsTotal'),
            },
            'factions': {},
            'wars': [],
        }

        for row in rowsets['factions'].findall('row'):
            a = row.attrib
            faction = {
                'id': int(a['factionID']),
                'name': a['factionName'],
                'pilots': int(a['pilots']),
                'systems': int(a['systemsControlled']),
                'kills': {
                    'yesterday': int(a['killsYesterday']),
                    'week': int(a['killsLastWeek']),
                    'total': int(a['killsTotal']),
                },
                'points': {
                    'yesterday': int(a['victoryPointsYesterday']),
                    'week': int(a['victoryPointsLastWeek']),
                    'total': int(a['victoryPointsTotal']),
                },
            }
            results['factions'][faction['id']] = faction

        for row in rowsets['factionWars'].findall('row'):
            a = row.attrib
            war = {
                'faction': {
                    'id': int(a['factionID']),
                    'name': a['factionName'],
                },
                'against': {
                    'id': int(a['againstID']),
                    'name': a['againstName'],
                },
            }
            results['wars'].append(war)

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('eve/SkillTree')
    def skill_tree(self, api_result=None):
        """Return a dict of all available skill groups."""
        rowset = api_result.result.find('rowset') # skillGroups

        results = {}
        name_cache = {}
        for row in rowset.findall('row'):

            # the skill group data
            g = row.attrib
            group = {
                'id': int(g['groupID']),
                'name': g['groupName'],
                'skills': {}
                }
            # Because :ccp: groups can sometimes be listed
            # multiple times with different skills, and the
            # correct result is to add the contents together
            group = results.get(group['id'], group)

            # now get the actual skill data
            skills_rs = row.find('rowset') # skills
            for skill_row in skills_rs.findall('row'):
                a = skill_row.attrib
                _str, _int, _float, _bool, _ts = api.elem_getters(skill_row)

                req_attrib = skill_row.find('requiredAttributes')

                skill = {
                    'id': int(a['typeID']),
                    'group_id': int(a['groupID']),
                    'name': a['typeName'],
                    'published': (a['published'] == '1'),
                    'description': _str('description'),
                    'rank': _int('rank'),
                    'required_skills': {},
                    'bonuses': {},
                    'attributes': {
                        'primary': api.get_named_value(req_attrib, 'primaryAttribute'),
                        'secondary': api.get_named_value(req_attrib, 'secondaryAttribute'),
                        }
                    }

                name_cache[skill['id']] = skill['name']

                # Check each rowset inside the skill, and branch based on the name attribute
                for sub_rs in skill_row.findall('rowset'):

                    if sub_rs.attrib['name'] == 'requiredSkills':
                        for sub_row in sub_rs.findall('row'):
                            b = sub_row.attrib
                            req = {
                                'level': int(b['skillLevel']),
                                'id': int(b['typeID']),
                                }
                            skill['required_skills'][req['id']] = req

                    elif sub_rs.attrib['name'] == 'skillBonusCollection':
                        for sub_row in sub_rs.findall('row'):
                            b = sub_row.attrib
                            bonus = {
                                'type': b['bonusType'],
                                'value': float(b['bonusValue']),
                                }
                            skill['bonuses'][bonus['type']] = bonus

                group['skills'][skill['id']] = skill

            results[group['id']] = group

        # Second pass to fill in required skill names
        for group in results.values():
            for skill in group['skills'].values():
                for skill_id, skill_info in skill['required_skills'].items():
                    skill_info['name'] = name_cache.get(skill_id)

        return api.APIResult(results, api_result.timestamp, api_result.expires)


    @api.auto_call('eve/RefTypes')
    def reference_types(self, api_result=None):
        """Return a dict containing id -> name reference type mappings."""
        rowset = api_result.result.find('rowset')

        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            results[int(a['refTypeID'])] = a['refTypeName']

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('eve/FacWarTopStats')
    def faction_warfare_leaderboard(self, api_result=None):
        """Return top-100 lists from Faction Warfare."""

        def parse_top_100(rowset, prefix, attr, attr_name):
            top100 = []
            id_field = '%sID' % prefix
            name_field = '%sName' % prefix
            for row in rowset.findall('row'):
                a = row.attrib
                top100.append({
                    'id': int(a[id_field]),
                    'name': a[name_field],
                    attr_name: int(a[attr]),
                })
            return top100

        def parse_section(section, prefix):
            section_result = {}
            rowsets = dict((r.attrib['name'], r) for r in section.findall('rowset'))

            section_result['kills'] = {
                'yesterday': parse_top_100(rowsets['KillsYesterday'], prefix, 'kills', 'kills'),
                'week': parse_top_100(rowsets['KillsLastWeek'], prefix, 'kills', 'kills'),
                'total': parse_top_100(rowsets['KillsTotal'], prefix, 'kills', 'kills'),
            }

            section_result['points'] = {
                'yesterday': parse_top_100(rowsets['VictoryPointsYesterday'],
                    prefix, 'victoryPoints', 'points'),
                'week': parse_top_100(rowsets['VictoryPointsLastWeek'],
                    prefix, 'victoryPoints', 'points'),
                'total': parse_top_100(rowsets['VictoryPointsTotal'],
                    prefix, 'victoryPoints', 'points'),
            }

            return section_result

        results = {
            'char': parse_section(api_result.result.find('characters'), 'character'),
            'corp': parse_section(api_result.result.find('corporations'), 'corporation'),
            'faction': parse_section(api_result.result.find('factions'), 'faction'),
        }

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('eve/ConquerableStationlist')
    def conquerable_stations(self, api_result=None):
        results = {}
        rowset = api_result.result.find('rowset')
        for row in rowset.findall('row'):
            station = {
                'id': int(row.attrib['stationID']),
                'name': row.attrib['stationName'],
                'type_id': int(row.attrib['stationTypeID']),
                'system_id': int(row.attrib['solarSystemID']),
                'corp': {
                    'id': int(row.attrib['corporationID']),
                    'name': row.attrib['corporationName'] }
                }
            results[station['id']] = station

        return api.APIResult(results, api_result.timestamp, api_result.expires)



# vim: set ts=4 sts=4 sw=4 et:

########NEW FILE########
__FILENAME__ = map
from evelink import api

class Map(object):
    """Wrapper around /map/ of the EVE API."""

    @api.auto_api
    def __init__(self, api=None):
        self.api = api

    @api.auto_call('map/Jumps')
    def jumps_by_system(self, api_result=None):
        """Get jump counts for systems in the last hour.

        Returns a tuple of ({system:jumps...}, timestamp).

        NOTE: Systems with 0 jumps in the last hour are not included!
        """

        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            system = int(row.attrib['solarSystemID'])
            jumps = int(row.attrib['shipJumps'])
            results[system] = jumps

        data_time = api.parse_ts(api_result.result.find('dataTime').text)

        return api.APIResult((results, data_time), api_result.timestamp, api_result.expires)

    @api.auto_call('map/Kills')
    def kills_by_system(self, api_result=None):
        """Get kill counts for systems in the last hour.

        Returns a tuple of ({system:{killdata}, timestamp).

        Each {killdata} is {'faction':count, 'ship':count, 'pod':count}.
        """
        
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            system = int(row.attrib['solarSystemID'])
            faction_kills = int(row.attrib['factionKills'])
            ship_kills = int(row.attrib['shipKills'])
            pod_kills = int(row.attrib['podKills'])

            results[system] = {
                'id': system,
                'faction': faction_kills,
                'ship': ship_kills,
                'pod': pod_kills,
            }

        data_time = api.parse_ts(api_result.result.find('dataTime').text)

        return api.APIResult((results, data_time), api_result.timestamp, api_result.expires)

    @api.auto_call('map/FacWarSystems')
    def faction_warfare_systems(self, api_result=None):
        """Get a dict of factional warfare systems and their info."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            system = int(row.attrib['solarSystemID'])
            name = row.attrib['solarSystemName']
            faction_id = int(row.attrib['occupyingFactionID']) or None
            faction_name = row.attrib['occupyingFactionName'] or None
            contested = (row.attrib['contested'] == 'True')

            results[system] = {
                'id': system,
                'name': name,
                'faction': {
                    'id': faction_id,
                    'name': faction_name,
                },
                'contested': contested,
            }

        return api.APIResult(results, api_result.timestamp, api_result.expires)

    @api.auto_call('map/Sovereignty')
    def sov_by_system(self, api_result=None):
        """Get sovereignty info keyed by system."""
        rowset = api_result.result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            system = int(row.attrib['solarSystemID'])
            name = row.attrib['solarSystemName']
            faction_id = int(row.attrib['factionID']) or None
            alliance_id = int(row.attrib['allianceID']) or None
            corp_id = int(row.attrib['corporationID']) or None

            results[system] = {
                'id': system,
                'name': name,
                'faction_id': faction_id,
                'alliance_id': alliance_id,
                'corp_id': corp_id,
            }

        data_time = api.parse_ts(api_result.result.find('dataTime').text)

        return api.APIResult((results, data_time), api_result.timestamp, api_result.expires)

########NEW FILE########
__FILENAME__ = assets
def parse_assets(api_result):
    def handle_rowset(rowset, parent_location):
        results = []
        for row in rowset.findall('row'):
            item = {'id': int(row.attrib['itemID']),
                    'item_type_id': int(row.attrib['typeID']),
                    'location_id': int(row.attrib.get('locationID', parent_location)),
                    'location_flag': int(row.attrib['flag']),
                    'quantity': int(row.attrib['quantity']),
                    'packaged': row.attrib['singleton'] == '0',
            }
            raw_quantity = row.attrib.get('rawQuantity')
            if raw_quantity is not None:
                item['raw_quantity'] = int(raw_quantity)
            contents = row.find('rowset')
            if contents is not None:
                item['contents'] = handle_rowset(contents, item['location_id'])
            results.append(item)
        return results

    result_list = handle_rowset(api_result.find('rowset'), None)
    # For convenience, key the result by top-level location ID.
    result_dict = {}
    for item in result_list:
        location = item['location_id']
        result_dict.setdefault(location, {})
        result_dict[location]['location_id'] = location
        result_dict[location].setdefault('contents', [])
        result_dict[location]['contents'].append(item)
    return result_dict

########NEW FILE########
__FILENAME__ = contact_list

LABEL_MAP = {
    'allianceContactList': 'alliance',
    'corporateContactList': 'corp',
    'contactList': 'personal',
}


def parse_contact_list(api_result):
    result = {}
    for rowset in api_result.findall('rowset'):
        contact_list = result[LABEL_MAP[rowset.get('name')]] = {}
        for row in rowset.findall('row'):
            in_watchlist = (row.get('inWatchlist') == 'True'
                            if 'inWatchlist' in row.attrib
                            else None)
            contact_id = int(row.get('contactID'))
            contact_list[contact_id] = {
                'id': contact_id,
                'name': row.get('contactName'),
                'standing': float(row.get('standing')),
                'in_watchlist': in_watchlist
            }

    return result
        

########NEW FILE########
__FILENAME__ = contracts
from evelink import api
from evelink import constants
import time

def parse_contracts(api_result):
    rowset = api_result.find('rowset')
    if rowset is None:
        return

    results = {}
    for row in rowset.findall('row'):
        a = row.attrib
        contract = {
            'id': int(a['contractID']),
            'issuer': int(a['issuerID']),
            'issuer_corp': int(a['issuerCorpID']),
            'assignee': int(a['assigneeID']),
            'acceptor': int(a['acceptorID']),
            'start': int(a['startStationID']),
            'end': int(a['endStationID']),
            'type': a['type'],
            'status': a['status'],
            'corp': a['forCorp'] == '1',
            'availability': a['availability'],
            'issued': api.parse_ts(a['dateIssued']),
            'days': int(a['numDays']),
            'price': float(a['price']),
            'reward': float(a['reward']),
            'collateral': float(a['collateral']),
            'buyout': float(a['buyout']),
            'volume': float(a['volume']),
            'title': a['title']
        }
        contract['expired'] = api.parse_ts(a['dateExpired'])
        contract['accepted'] = api.parse_ts(a['dateAccepted'])
        contract['completed'] = api.parse_ts(a['dateCompleted'])
        results[contract['id']] = contract
    return results

########NEW FILE########
__FILENAME__ = contract_bids
from evelink import api

def parse_contract_bids(api_result):
    rowset = api_result.find('rowset')
    results = []
    for row in rowset.findall('row'):
        a = row.attrib

        bid = {
            'id': int(a['bidID']),
            'contract_id': int(a['contractID']),
            'bidder_id': int(a['bidderID']),
            'timestamp': api.parse_ts(a['dateBid']),
            'amount': float(a['amount']),
        }

        results.append(bid)

    return results



########NEW FILE########
__FILENAME__ = contract_items
def parse_contract_items(api_result):
    rowset = api_result.find('rowset')
    results = []
    for row in rowset.findall('row'):
        a = row.attrib
        item = {
            'id': int(a['recordID']),
            'type_id': int(a['typeID']),
            'quantity': int(a['quantity']),
            'singleton': a['singleton'] == '1',
            'action': 'offered' if a['included'] == '1' else 'requested',
        }
        if 'rawQuantity' in a:
          item['raw_quantity'] = int(a['rawQuantity'])

        results.append(item)

    return results


########NEW FILE########
__FILENAME__ = industry_jobs
from evelink import api
from evelink import constants

def parse_industry_jobs(api_result):
        rowset = api_result.find('rowset')
        result = {}

        if rowset is None:
            return

        for row in rowset.findall('row'):
            # shortcut to make the following block less painful
            a = row.attrib
            jobID = int(a['jobID'])
            completed = a['completed'] == '1'
            result[jobID] = {
                'line_id': int(a['assemblyLineID']),
                'container_id': int(a['containerID']),
                'input': {
                    'id': int(a['installedItemID']),
                    'blueprint_type': 'copy' if a['installedItemCopy'] == '1' else 'original',
                    'location_id': int(a['installedItemLocationID']),
                    'quantity': int(a['installedItemQuantity']),
                    'prod_level': int(a['installedItemProductivityLevel']),
                    'mat_level': int(a['installedItemMaterialLevel']),
                    'runs_left': int(a['installedItemLicensedProductionRunsRemaining']),
                    'item_flag': int(a['installedItemFlag']),
                    'type_id': int(a['installedItemTypeID']),
                },
                'output': {
                    'location_id': int(a['outputLocationID']),
                    'bpc_runs': int(a['licensedProductionRuns']),
                    'container_location_id': int(a['containerLocationID']),
                    'type_id': int(a['outputTypeID']),
                    'flag': int(a['outputFlag']),
                },
                'runs': int(a['runs']),
                'installer_id': int(a['installerID']),
                'system_id': int(a['installedInSolarSystemID']),
                'multipliers': {
                    'material': float(a['materialMultiplier']),
                    'char_material': float(a['charMaterialMultiplier']),
                    'time': float(a['timeMultiplier']),
                    'char_time': float(a['charTimeMultiplier']),
                },
                'container_type_id': int(a['containerTypeID']),
                'completed': completed,
                'successful': a['completedSuccessfully'] == '1',
                'status': (
                    constants.Industry.job_status[int(a['completedStatus'])]
                    if completed else 'in-progress'
                ),
                'activity_id': int(a['activityID']),
                'install_ts': api.parse_ts(a['installTime']),
                'begin_ts': api.parse_ts(a['beginProductionTime']),
                'end_ts': api.parse_ts(a['endProductionTime']),
                'pause_ts': api.parse_ts(a['pauseProductionTime']),

                # deprecated - use 'completed' instead
                'delivered': completed,
                # deprecated - use 'successful' instead
                'finished': a['completedSuccessfully'] == '1',
            }

        return result

########NEW FILE########
__FILENAME__ = kills
from evelink import api

def parse_kills(api_result):
    rowset = api_result.find('rowset')
    result = {}
    for row in rowset.findall('row'):
        a = row.attrib
        kill_id = int(a['killID'])
        result[kill_id] = {
            'id': kill_id,
            'system_id': int(a['solarSystemID']),
            'time': api.parse_ts(a['killTime']),
            'moon_id': int(a['moonID']),
        }

        victim = row.find('victim')
        a = victim.attrib
        result[kill_id]['victim'] = {
            'id': int(a['characterID']),
            'name': a['characterName'],
            'corp': {
                'id': int(a['corporationID']),
                'name': a['corporationName'],
            },
            'alliance': {
                'id': int(a['allianceID']),
                'name': a['allianceName'],
            },
            'faction': {
                'id': int(a['factionID']),
                'name': a['factionName'],
            },
            'damage': int(a['damageTaken']),
            'ship_type_id': int(a['shipTypeID']),
        }

        result[kill_id]['attackers'] = {}

        rowsets = {}
        for rowset in row.findall('rowset'):
            key = rowset.attrib['name']
            rowsets[key] = rowset

        for attacker in rowsets['attackers'].findall('row'):
            a = attacker.attrib
            attacker_id = int(a['characterID'])
            result[kill_id]['attackers'][attacker_id] = {
                'id': attacker_id,
                'name': a['characterName'],
                'corp': {
                    'id': int(a['corporationID']),
                    'name': a['corporationName'],
                },
                'alliance': {
                    'id': int(a['allianceID']),
                    'name': a['allianceName'],
                },
                'faction': {
                    'id': int(a['factionID']),
                    'name': a['factionName'],
                },
                'sec_status': float(a['securityStatus']),
                'damage': int(a['damageDone']),
                'final_blow': a['finalBlow'] == '1',
                'weapon_type_id': int(a['weaponTypeID']),
                'ship_type_id': int(a['shipTypeID']),
            }

        def _get_items(rowset):
            items = []
            for item in rowset.findall('row'):
                a = item.attrib
                type_id = int(a['typeID'])
                items.append({
                    'id': type_id,
                    'flag': int(a['flag']),
                    'dropped': int(a['qtyDropped']),
                    'destroyed': int(a['qtyDestroyed']),
                })

                containers = item.findall('rowset')
                for container in containers:
                    items.extend(_get_items(container))

            return items

        result[kill_id]['items'] = _get_items(rowsets['items'])

    return result

########NEW FILE########
__FILENAME__ = orders
from evelink import api
from evelink import constants

def parse_market_orders(api_result):
        rowset = api_result.find('rowset')
        rows = rowset.findall('row')
        result = {}
        for row in rows:
            a = row.attrib
            id = int(a['orderID'])
            result[id] = {
                'id': id,
                'char_id': int(a['charID']),
                'station_id': int(a['stationID']),
                'amount': int(a['volEntered']),
                'amount_left': int(a['volRemaining']),
                'status': constants.Market().order_status[int(a['orderState'])],
                'type_id': int(a['typeID']),
                'range': int(a['range']),
                'account_key': int(a['accountKey']),
                'duration': int(a['duration']),
                'escrow': float(a['escrow']),
                'price': float(a['price']),
                'type': 'buy' if a['bid'] == '1' else 'sell',
                'timestamp': api.parse_ts(a['issued']),
            }

        return result

########NEW FILE########
__FILENAME__ = wallet_journal
from evelink import api

def parse_wallet_journal(api_result):
    rowset = api_result.find('rowset')
    result = []

    for row in rowset.findall('row'):
        a = row.attrib
        entry = {
            'timestamp': api.parse_ts(a['date']),
            'id': int(a['refID']),
            'type_id': int(a['refTypeID']),
            'party_1': {
                'name': a['ownerName1'],
                'id': int(a['ownerID1']),
                'type':int(a['owner1TypeID']),
            },
            'party_2': {
                'name': a['ownerName2'],
                'id': int(a['ownerID2']),
                'type':int(a['owner2TypeID']),
            },
            'arg': {
                'name': a['argName1'],
                'id': int(a['argID1']),
            },
            'amount': float(a['amount']),
            'balance': float(a['balance']),
            'reason': a['reason'],
            # The tax fields might be an empty string, or not present
            # at all (e.g., for corp wallet records.)  Need to handle
            # both edge cases.
            'tax': {
                'taxer_id': int(a.get('taxReceiverID') or 0),
                'amount': float(a.get('taxAmount') or 0),
            },
        }

        result.append(entry)

    result.sort(key=lambda x: x['id'])
    return result



########NEW FILE########
__FILENAME__ = wallet_transactions
from evelink import api

def parse_wallet_transactions(api_result):
    rowset = api_result.find('rowset')
    rows = rowset.findall('row')
    result = []
    for row in rows:
        a = row.attrib
        entry = {
            'timestamp': api.parse_ts(a['transactionDateTime']),
            'id': int(a['transactionID']),
            'journal_id': int(a['journalTransactionID']),
            'quantity': int(a['quantity']),
            'type': {
                'id': int(a['typeID']),
                'name': a['typeName'],
            },
            'price': float(a['price']),
            'client': {
                'id': int(a['clientID']),
                'name': a['clientName'],
            },
            'station': {
                'id': int(a['stationID']),
                'name': a['stationName'],
            },
            'action': a['transactionType'],
            'for': a['transactionFor'],
        }
        if 'characterID' in a:
            entry['char'] = {
                'id': int(a['characterID']),
                'name': a['characterName'],
            }
        result.append(entry)

    return result

########NEW FILE########
__FILENAME__ = server
from evelink import api

class Server(object):
    """Wrapper around /server/ of the EVE API."""

    @api.auto_api
    def __init__(self, api=None):
        self.api = api

    @api.auto_call('server/ServerStatus')
    def server_status(self, api_result=None):
        """Check the current server status."""

        result = {
            'online': api.get_bool_value(api_result.result, 'serverOpen'),
            'players': api.get_int_value(api_result.result, 'onlinePlayers'),
        }

        return api.APIResult(result, api_result.timestamp, api_result.expires)


########NEW FILE########
__FILENAME__ = eve_central
import datetime
import json
from xml.etree import ElementTree

try:
    from evelink.thirdparty.six.moves import urllib
except ImportError:
    urllib2 = None

class EVECentral(object):

    def __init__(self, url_fetch_func=None,
        api_base='http://api.eve-central.com/api'):
        super(EVECentral, self).__init__()

        self.api_base = api_base

        if url_fetch_func is not None:
            self.url_fetch = url_fetch_func
        elif urllib2 is not None:
            self.url_fetch = self._default_fetch_func
        else:
            raise ValueError("urllib2 not available - specify url_fetch_func")

    def _default_fetch_func(self, url):
        """Fetches a given URL using GET and returns the response."""
        return urllib.request.urlopen(url).read()

    def market_stats(self, type_ids, hours=24, regions=None, system=None,
        quantity_threshold=None):
        """Fetches market statistics for one or more items.

        Optional filters:
            hours (int) - Time period to compute statistics for.
            regions (list of ints) - Region id(s) for which to compute stats.
            systems (int) - System id for which to compute stats.
            quantity_threshold (int) - minimum size of order to consider.
        """

        params = [('typeid', type_ids), ('hours', hours)]
        if regions:
            params.append(('regionlimit', regions))
        if system:
            params.append(('usesystem', system))
        if quantity_threshold:
            params.append(('minQ', quantity_threshold))

        query = urllib.parse.urlencode(params, True)
        url = '%s/marketstat?%s' % (self.api_base, query)

        response = self.url_fetch(url)
        api_result = ElementTree.fromstring(response)

        results = {}
        stats = api_result.find('marketstat')
        for type_section in stats.findall('type'):
            type_id = int(type_section.attrib['id'])
            type_result = {'id': type_id}
            for sub in ('all', 'buy', 'sell'):
                s = type_section.find(sub)
                sub_result = {
                    'volume': int(s.find('volume').text),
                    'avg': float(s.find('avg').text),
                    'max': float(s.find('max').text),
                    'min': float(s.find('min').text),
                    'stddev': float(s.find('stddev').text),
                    'median': float(s.find('median').text),
                    'percentile': float(s.find('percentile').text),
                }
                type_result[sub] = sub_result
            results[type_id] = type_result

        return results

    def item_market_stats(self, type_id, *args, **kwargs):
        """Fetch market statistics for a single item.

        (Convenience wrapper for market_stats.)
        """
        return self.market_stats([type_id], *args, **kwargs)[int(type_id)]

    def item_orders(self, type_id, hours=360, regions=None, system=None,
        quantity_threshold=None):
        """Fetches market orders for a given item.

        Optional filters:
            hours (int) - The time period from which to fetch posted orders.
            regions (list of ints) - Region id(s) for which to fetch orders.
            systems (int) - System id for which to fetch orders.
            quantity_threshold (int) - minimum size of order to consider.
        """

        params = [('typeid', type_id), ('sethours', hours)]
        if regions:
            params.append(('regionlimit', regions))
        if system:
            params.append(('usesystem', system))
        if quantity_threshold:
            params.append(('setminQ', quantity_threshold))

        query = urllib.parse.urlencode(params, True)
        url = '%s/quicklook?%s' % (self.api_base, query)

        response = self.url_fetch(url)
        return self._parse_item_orders(response)

    def item_orders_on_route(self, type_id, start, dest, hours=360,
        quantity_threshold=None):
        """Fetches market orders for a given item along a shortest-path route.

        Optional filters:
            hours (int) - The time period from which to fetch posted orders.
            quantity_threshold (int) - minimum size of order to consider.
        """

        params = [('sethours', hours)]
        if quantity_threshold:
            params.append(('setminQ', quantity_threshold))

        query = urllib.parse.urlencode(params, True)
        url = '%s/quicklook/onpath/from/%s/to/%s/fortype/%s?%s' % (
            self.api_base, start, dest, type_id, query)

        response = self.url_fetch(url)
        return self._parse_item_orders(response)

    def _parse_item_orders(self, response):
        """Shared parsing functionality for market order data from EVE-Central."""
        api_result = ElementTree.fromstring(response)

        res = api_result.find('quicklook')
        regions = res.find('regions').findall('region')
        results = {
            'id': int(res.find('item').text),
            'name': res.find('itemname').text,
            'hours': int(res.find('hours').text),
            'quantity_min': int(res.find('minqty').text),
            'regions': [r.text for r in regions] or None,
            'orders': {},
        }

        for act in ('buy', 'sell'):
            sub_result = {}
            for order in res.find('%s_orders' % act).findall('order'):
                order_id = int(order.attrib['id'])
                o = {
                    'id': order_id,
                    'region_id': int(order.find('region').text),
                    'station': {
                        'id': int(order.find('station').text),
                        'name': order.find('station_name').text,
                    },
                    'security': float(order.find('security').text),
                    'range': int(order.find('range').text),
                    'price': float(order.find('price').text),
                    'volume': {
                        'remaining': int(order.find('vol_remain').text),
                        'minimum': int(order.find('min_volume').text),
                    },
                    'expires': datetime.datetime.strptime(
                        order.find('expires').text,
                        "%Y-%m-%d",
                    ).date(),
                    'reported': datetime.datetime.strptime(
                        order.find('reported_time').text,
                        "%m-%d %H:%M:%S",
                    ),
                }

                # Correct errors due to EVE-Central only reporting the month
                # and day of the report, not the year. (Assumes reports are
                # never from the future and never older than a year.)
                this_year = datetime.datetime.now().year
                o['reported'] = o['reported'].replace(year=this_year)
                if o['reported'] > datetime.datetime.now():
                    previous_year = o['reported'].year - 1
                    o['reported'] = o['reported'].replace(year=previous_year)

                sub_result[order_id] = o

            results['orders'][act] = sub_result

        return results

    def route(self, start, dest):
        """Returns a shortest-path route between two systems.

        Both start and dest can be either exact system names or
        system IDs.
        """

        url = '%s/route/from/%s/to/%s' % (self.api_base, start, dest)
        response = self.url_fetch(url)

        stops = json.loads(response)

        results = []
        for stop in stops:
            results.append({
                'from': {
                    'id': stop['fromid'],
                    'name': stop['from'],
                },
                'to': {
                    'id': stop['toid'],
                    'name': stop['to'],
                },
                'security_change': stop['secchange'],
            })

        return results



# vim: set et ts=4 sts=4 sw=4:

########NEW FILE########
__FILENAME__ = eve_who
import json
import re
import logging
from time import sleep

from evelink import api

try:
    from evelink.thirdparty.six.moves import urllib
except ImportError:
    urllib2 = None

_log = logging.getLogger('evelink.thirdparty.eve_who')


class FetchError(Exception):
    """Class for exceptions if fetch failed."""
    pass


class EVEWho(object):
    def __init__(self, url_fetch_func=None, cache=None, wait=True,
                 api_base='http://evewho.com/api.php'):
        super(EVEWho, self).__init__()

        self.api_base = api_base
        self.wait = wait

        if url_fetch_func is not None:
            self.url_fetch = url_fetch_func
        elif urllib2 is not None:
            self.url_fetch = self._default_fetch_func
        else:
            raise ValueError("urllib2 not available - specify url_fetch_func")

        cache = cache or api.APICache()
        if not isinstance(cache, api.APICache):
            raise ValueError("The provided cache must subclass from APICache.")
        self.cache = cache
        self.cachetime = 3600

    def _default_fetch_func(self, url):
        """Fetches a given URL using GET and returns the response."""
        return urllib.request.urlopen(url).read()

    def _cache_key(self, path, params):
        sorted_params = sorted(params.items())
        # Paradoxically, Shelve doesn't like integer keys.
        return str(hash((path, tuple(sorted_params))))

    def _get(self, ext_id, api_type, page=0):
        """Request page from EveWho api."""
        path = self.api_base
        params = {'id': ext_id,
                  'type': api_type,
                  'page': page}

        key = self._cache_key(path, params)
        cached_result = self.cache.get(key)
        if cached_result is not None:
            # Cached APIErrors should be re-raised
            if isinstance(cached_result, api.APIError):
                _log.error("Raising cached error: %r" % cached_result)
                raise cached_result
                # Normal cached results get returned
            _log.debug("Cache hit, returning cached payload")
            return cached_result

        query = urllib.parse.urlencode(params, True)
        url = '%s?%s' % (path, query)
        response = None

        regexp = re.compile("^hammering a website isn't very nice ya know.... please wait (\d+) seconds")
        hammering = True
        while hammering:
            response = self.url_fetch(url)
            hammering = regexp.findall(response)
            if hammering:
                if self.wait:
                    _log.debug("Fetch page waiting: %s (%s)" % (url, response))
                    sleep(int(hammering[0]))
                else:
                    _log.error("Fetch page error: %s (%s)" % (url, response))
                    raise FetchError(response)

        result = json.loads(response)
        self.cache.put(key, result, self.cachetime)
        return result

    def _member_list(self, ext_id, api_type):
        """Fetches member list for corporation or alliance.

        Valid api_types: 'corplist', 'allilist'.
        """
        if api_type not in ['corplist', 'allilist']:
            raise ValueError("not valid api type - valid api types: 'corplist' and 'allilist'.")

        member_count = 0
        page = 0
        members = []
        while page <= (member_count // 200):
            data = self._get(ext_id, api_type, page)

            info = data['info']
            if info:
                member_count = int(info['member_count']) - 1    # workaround for numbers divisible by 200
            else:
                return members

            for member in data['characters']:
                members.append({'name': str(member['name']),
                                'char_id': int(member['character_id']),
                                'corp_id': int(member['corporation_id']),
                                'alli_id': int(member['alliance_id'])})
            page += 1

        return members

    def corp_member_list(self, corp_id):
        """Fetch member list for a corporation.

        (Convenience wrapper for member_list.)
        """
        return self._member_list(corp_id, api_type='corplist')

    def alliance_member_list(self, alli_id):
        """Fetch member list for a alliance.

        (Convenience wrapper for member_list.)
        """
        return self._member_list(alli_id, api_type='allilist')

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2014 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.6.1"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        try:
            result = self._resolve()
        except ImportError:
            # See the nice big comment in MovedModule.__getattr__.
            raise AttributeError("%s could not be imported " % self.name)
        setattr(obj, self.name, result) # Invokes __set__.
        # This is a bit ugly, but it avoids running this again.
        delattr(obj.__class__, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)

    def __getattr__(self, attr):
        # It turns out many Python frameworks like to traverse sys.modules and
        # try to load various attributes. This causes problems if this is a
        # platform-specific module on the wrong platform, like _winreg on
        # Unixes. Therefore, we silently pretend unimportable modules do not
        # have any attributes. See issues #51, #53, #56, and #63 for the full
        # tales of woe.
        #
        # First, if possible, avoid loading the module just to look at __file__,
        # __name__, or __path__.
        if (attr in ("__file__", "__name__", "__path__") and
            self.mod not in sys.modules):
            raise AttributeError(attr)
        try:
            _module = self._resolve()
        except ImportError:
            raise AttributeError(attr)
        value = getattr(_module, attr)
        setattr(self, attr, value)
        return value


class _LazyModule(types.ModuleType):

    def __init__(self, name):
        super(_LazyModule, self).__init__(name)
        self.__doc__ = self.__class__.__doc__

    def __dir__(self):
        attrs = ["__doc__", "__name__"]
        attrs += [attr.name for attr in self._moved_attributes]
        return attrs

    # Subclasses should override this
    _moved_attributes = []


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(_LazyModule):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("dbm_gnu", "gdbm", "dbm.gnu"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("_thread", "thread", "_thread"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_ttk", "ttk", "tkinter.ttk"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("xmlrpc_client", "xmlrpclib", "xmlrpc.client"),
    MovedModule("xmlrpc_server", "xmlrpclib", "xmlrpc.server"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
    if isinstance(attr, MovedModule):
        sys.modules[__name__ + ".moves." + attr.name] = attr
del attr

_MovedItems._moved_attributes = _moved_attributes

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")


class Module_six_moves_urllib_parse(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("SplitResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
    MovedAttribute("splitquery", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

Module_six_moves_urllib_parse._moved_attributes = _urllib_parse_moved_attributes

sys.modules[__name__ + ".moves.urllib_parse"] = sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")


class Module_six_moves_urllib_error(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

Module_six_moves_urllib_error._moved_attributes = _urllib_error_moved_attributes

sys.modules[__name__ + ".moves.urllib_error"] = sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
    MovedAttribute("proxy_bypass", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes

sys.modules[__name__ + ".moves.urllib_request"] = sys.modules[__name__ + ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

Module_six_moves_urllib_response._moved_attributes = _urllib_response_moved_attributes

sys.modules[__name__ + ".moves.urllib_response"] = sys.modules[__name__ + ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

Module_six_moves_urllib_robotparser._moved_attributes = _urllib_robotparser_moved_attributes

sys.modules[__name__ + ".moves.urllib_robotparser"] = sys.modules[__name__ + ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]

    def __dir__(self):
        return ['parse', 'error', 'request', 'response', 'robotparser']


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    # Workaround for standalone backslash
    def u(s):
        return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    exec_ = getattr(moves.builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


print_ = getattr(moves.builtins, "print", None)
if print_ is None:
    def print_(*args, **kwargs):
        """The new-style print function for Python 2.4 and 2.5."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            # If the file has an encoding, encode unicode with it.
            if (isinstance(fp, file) and
                isinstance(data, unicode) and
                fp.encoding is not None):
                errors = getattr(fp, "errors", None)
                if errors is None:
                    errors = "strict"
                data = data.encode(fp.encoding, errors)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = test_shelve
import os
import tempfile

from tests.compat import unittest

from evelink.cache.shelf import ShelveCache

class ShelveCacheTestCase(unittest.TestCase):

    def setUp(self):
        self.cache_dir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.cache_dir, 'shelf')
        self.cache = ShelveCache(self.cache_path)

    def tearDown(self):
        self.cache.cache.close()
        try:
          os.remove(self.cache_path)
        except OSError:
          pass
        try:
          os.rmdir(self.cache_dir)
        except OSError:
          pass

    def test_cache(self):
        self.cache.put('foo', 'bar', 3600)
        self.assertEqual(self.cache.get('foo'), 'bar')

    def test_expire(self):
        self.cache.put('baz', 'qux', -1)
        self.assertEqual(self.cache.get('baz'), None)

########NEW FILE########
__FILENAME__ = test_sqlite
import os
import tempfile

from tests.compat import unittest

from evelink.cache.sqlite import SqliteCache

class SqliteCacheTestCase(unittest.TestCase):

    def setUp(self):
        self.cache_dir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.cache_dir, 'sqlite')
        self.cache = SqliteCache(self.cache_path)

    def tearDown(self):
        self.cache.connection.close()
        try:
          os.remove(self.cache_path)
        except OSError:
          pass
        try:
          os.rmdir(self.cache_dir)
        except OSError:
          pass

    def test_cache(self):
        self.cache.put('foo', 'bar', 3600)
        self.cache.put('bar', 1, 3600)
        self.cache.put('baz', True, 3600)
        self.assertEqual(self.cache.get('foo'), 'bar')
        self.assertEqual(self.cache.get('bar'), 1)
        self.assertEqual(self.cache.get('baz'), True)

    def test_expire(self):
        self.cache.put('baz', 'qux', -1)
        self.assertEqual(self.cache.get('baz'), None)

########NEW FILE########
__FILENAME__ = compat
from evelink.thirdparty.six import PY2
if PY2:
    import unittest2 as unittest
else:
    import unittest

########NEW FILE########
__FILENAME__ = test_assets
from tests.compat import unittest
from tests.utils import make_api_result

from evelink.parsing import assets as evelink_a

class AssetsTestCase(unittest.TestCase):

    def test_parse_assets(self):
        api_result, _, _ = make_api_result("corp/assets.xml")

        result = evelink_a.parse_assets(api_result)

        self.assertEqual(result, {
            30003719: {
                'contents': [
                    {'contents': [
                        {'id': 1007353294812,
                         'item_type_id': 34,
                         'location_flag': 42,
                         'location_id': 30003719,
                         'packaged': True,
                         'quantity': 100},
                        {'id': 1007353294813,
                         'item_type_id': 34,
                         'location_flag': 42,
                         'location_id': 30003719,
                         'packaged': True,
                         'quantity': 200}],
                     'id': 1007222140712,
                     'item_type_id': 16216,
                     'location_flag': 0,
                     'location_id': 30003719,
                     'packaged': False,
                     'quantity': 1,
                     'raw_quantity': -1}],
                'location_id': 30003719},
            67000050: {
                'contents': [
                    {'id': 1007221285456,
                     'item_type_id': 13780,
                     'location_flag': 0,
                     'location_id': 67000050,
                     'packaged': False,
                     'quantity': 1,
                     'raw_quantity': -1},
                    {'id': 374680079,
                     'item_type_id': 973,
                     'location_flag': 0,
                     'location_id': 67000050,
                     'packaged': False,
                     'quantity': 1,
                     'raw_quantity': -2}],
                'location_id': 67000050}})

########NEW FILE########
__FILENAME__ = test_contact_list
import mock

from tests.compat import unittest
from tests.utils import make_api_result

from evelink.parsing import contact_list

class ContactsTestCase(unittest.TestCase):
    maxDiff = 1000

    def test_parse_char_contact_list(self):
        api_result, _, _ = make_api_result("char/contact_list.xml")

        result = contact_list.parse_contact_list(api_result)

        expected_result = {
            'corp': {
                1082138174: {'standing': 10.0, 'id': 1082138174,
                             'name': 'Nomad LLP',
                             'in_watchlist': None},
                1086308227: {'standing': 0.0, 'id': 1086308227,
                             'name': 'Rebel Alliance of New Eden',
                             'in_watchlist': None},
                1113838907: {'standing': -10.0, 'id': 1113838907,
                             'name': 'Significant other',
                             'in_watchlist': None}
            },
            'alliance': {
                2049763943: {'standing': -10.0, 'id': 2049763943,
                             'name': 'EntroPraetorian Aegis',
                             'in_watchlist': None},
                2067199408: {'standing': -10.0, 'id': 2067199408,
                             'name': 'Vera Cruz Alliance',
                             'in_watchlist': None},
                2081065875: {'standing': -7.5, 'id': 2081065875,
                             'name': 'TheRedMaple',
                             'in_watchlist': None}
            },
            'personal': {
                3009988: {'standing': 0.0, 'id': 3009988,
                          'name': 'Navittus Sildbena',
                          'in_watchlist': True},
                544497016: {'standing': 10.0, 'id': 544497016,
                            'name': 'Valkyries of Night',
                            'in_watchlist': False}
            }
        }

        self.assertEqual(result['personal'], expected_result['personal'])
        self.assertEqual(result['alliance'], expected_result['alliance'])
        self.assertEqual(result['corp'], expected_result['corp'])
        self.assertEqual(sorted(result.keys()), sorted(expected_result.keys()))

    def test_parse_corp_contact_list(self):
        api_result, _, _ = make_api_result("corp/contact_list.xml")

        result = contact_list.parse_contact_list(api_result)

        expected_result = {
            'corp': {
                1082138174: {'standing': 10.0, 'id': 1082138174,
                             'name': 'Nomad LLP',
                             'in_watchlist': None},
                1086308227: {'standing': 0.0, 'id': 1086308227,
                             'name': 'Rebel Alliance of New Eden',
                             'in_watchlist': None},
                1113838907: {'standing': -10.0, 'id': 1113838907,
                             'name': 'Significant other',
                             'in_watchlist': None}
            },
            'alliance': {
                2049763943: {'standing': -10.0, 'id': 2049763943,
                             'name': 'EntroPraetorian Aegis',
                             'in_watchlist': None},
                2067199408: {'standing': -10.0, 'id': 2067199408,
                             'name': 'Vera Cruz Alliance',
                             'in_watchlist': None},
                2081065875: {'standing': -10.0, 'id': 2081065875,
                             'name': 'TheRedMaple',
                             'in_watchlist': None}
            },
        }

        self.assertEqual(result['alliance'], expected_result['alliance'])
        self.assertEqual(result['corp'], expected_result['corp'])
        self.assertFalse('personal' in result)

        self.assertEqual(sorted(result.keys()), sorted(expected_result.keys()))

########NEW FILE########
__FILENAME__ = test_contracts
from tests.compat import unittest
from tests.utils import make_api_result

from evelink import api
from evelink.parsing import contracts as evelink_c

class ContractsTestCase(unittest.TestCase):
    def test_parse_contracts(self):
        api_result, _, _ = make_api_result("corp/contracts.xml")
        result = evelink_c.parse_contracts(api_result)
        self.assertEqual(result, {
                5966: {
                    'id': 5966,
                    'issuer': 154416088,
                    'issuer_corp': 154430949,
                    'assignee': 0,
                    'acceptor': 0,
                    'start': 60014659,
                    'end': 60014659,
                    'type': 'ItemExchange',
                    'status': 'Outstanding',
                    'title': '',
                    'corp': False,
                    'availability': 'Public',
                    'issued': api.parse_ts('2010-02-23 11:28:00'),
                    'expired': api.parse_ts('2010-03-24 11:28:00'),
                    'accepted': None,
                    'completed': None,
                    'days': 0,
                    'price': 5000.0,
                    'reward': 0.0,
                    'collateral': 0.0,
                    'buyout': 0.0,
                    'volume': 0.01,
                },
                5968: {
                    'id': 5968,
                    'issuer': 154416088,
                    'issuer_corp': 154430949,
                    'assignee': 154430949,
                    'acceptor': 0,
                    'start': 60003760,
                    'end': 60003760,
                    'type': 'ItemExchange',
                    'status': 'Outstanding',
                    'title': '',
                    'corp': False,
                    'availability': 'Private',
                    'issued': api.parse_ts('2010-02-25 11:33:00'),
                    'expired': api.parse_ts('2010-03-26 11:33:00'),
                    'accepted': None,
                    'completed': None,
                    'days': 0,
                    'price': 0.00,
                    'reward': 0.00,
                    'collateral': 0.00,
                    'buyout': 0.00,
                    'volume': 0.03,
                }
            })

########NEW FILE########
__FILENAME__ = test_contract_bids
from tests.compat import unittest
from tests.utils import make_api_result

from evelink.parsing import contract_bids as evelink_c

class ContractBidsTestCase(unittest.TestCase):
    def test_parse_contract_bids(self):
        api_result, _, _ = make_api_result("char/contract_bids.xml")
        result = evelink_c.parse_contract_bids(api_result)
        self.assertEqual(result, [
           {'id': 123456,
            'contract_id': 8439234,
            'bidder_id': 984127,
            'timestamp': 1178692470,
            'amount': 1958.12},
           {'id': 4025870,
            'contract_id': 58777338,
            'bidder_id': 91397530,
            'timestamp': 1345698201,
            'amount': 14.0},
        ])



########NEW FILE########
__FILENAME__ = test_contract_items
from tests.compat import unittest
from tests.utils import make_api_result

from evelink.parsing import contract_items as evelink_c

class ContractItemsTestCase(unittest.TestCase):
    def test_parse_contract_items(self):
        api_result, _, _ = make_api_result("char/contract_items.xml")
        result = evelink_c.parse_contract_items(api_result)
        self.assertEqual(result, [
            {'id': 779703190, 'quantity': 490, 'type_id': 17867, 'action': 'offered', 'singleton': False},
            {'id': 779703191, 'quantity': 60, 'type_id': 17868, 'action': 'offered', 'singleton': False},
            {'id': 779703192, 'quantity': 8360, 'type_id': 1228, 'action': 'offered', 'singleton': False},
            {'id': 779703193, 'quantity': 16617, 'type_id': 1228, 'action': 'offered', 'singleton': False},
            {'id': 779703194, 'quantity': 1, 'type_id': 973, 'action': 'offered', 'singleton': True, 'raw_quantity': -2},
        ])


########NEW FILE########
__FILENAME__ = test_industry_jobs
import mock

from tests.compat import unittest
from tests.utils import make_api_result

import evelink.parsing.industry_jobs as evelink_ij

class IndustryJobsTestCase(unittest.TestCase):

    def test_parse_industry_jobs(self):
        api_result, _, _ = make_api_result("char/industry_jobs.xml")
        result = evelink_ij.parse_industry_jobs(api_result)
        self.assertEqual(result, {
            19962573: {
                'activity_id': 4,
                'begin_ts': 1205793300,
                'delivered': False,
                'completed': False,
                'status': 'in-progress',
                'finished': False,
                'successful': False,
                'container_id': 61000139,
                'container_type_id': 21644,
                'end_ts': 1208073300,
                'input': {
                    'id': 178470781,
                    'blueprint_type': 'original',
                    'item_flag': 4,
                    'location_id': 61000139,
                    'mat_level': 0,
                    'prod_level': 0,
                    'quantity': 1,
                    'runs_left': -1,
                    'type_id': 27309},
                'install_ts': 1205423400,
                'system_id': 30002903,
                'installer_id': 975676271,
                'line_id': 100502936,
                'multipliers': {
                    'char_material': 1.25,
                    'char_time': 0.949999988079071,
                    'material': 1.0,
                    'time': 1.0},
                'output': {
                    'bpc_runs': 0,
                    'container_location_id': 30002903,
                    'flag': 0,
                    'location_id': 61000139,
                    'type_id': 27309},
                'runs': 20,
                'pause_ts': None},
            37051255: {
                'activity_id': 1,
                'begin_ts': 1233500820,
                'delivered': True,
                'completed': True,
                'status': 'failed',
                'finished': False,
                'successful': False,
                'container_id': 61000211,
                'container_type_id': 21644,
                'end_ts': 1233511140,
                'input': {
                    'id': 664432163,
                    'blueprint_type': 'original',
                    'item_flag': 4,
                    'location_id': 61000211,
                    'mat_level': 90,
                    'prod_level': 11,
                    'quantity': 1,
                    'runs_left': -1,
                    'type_id': 894},
                'install_ts': 1233500820,
                'system_id': 30001233,
                'installer_id': 975676271,
                'line_id': 101335750,
                'multipliers': {
                    'char_material': 1.25,
                    'char_time': 0.800000011920929,
                    'material': 1.0,
                    'time': 0.699999988079071},
                'output': {
                    'bpc_runs': 0,
                    'container_location_id': 30001233,
                    'flag': 4,
                    'location_id': 61000211,
                    'type_id': 193},
                'runs': 75,
                'pause_ts': None}
            }
        )

########NEW FILE########
__FILENAME__ = test_kills
from tests.compat import unittest
from tests.utils import make_api_result

import evelink.parsing.kills as evelink_k

class KillsTestCase(unittest.TestCase):

    def test_parse_kills(self):
        api_result, _, _ = make_api_result("char/kills.xml")

        result = evelink_k.parse_kills(api_result)

        self.assertEqual(result, {
            15640545: {
                'attackers': {
                    935091361: {
                        'alliance': {
                            'id': 5514808,
                            'name': 'Authorities of EVE'},
                        'corp': {
                            'id': 224588600,
                            'name': 'Inkblot Squad'},
                        'damage': 446,
                        'faction': {
                            'id': 0,
                            'name': ''},
                        'final_blow': True,
                        'id': 935091361,
                        'name': 'ICU123',
                        'sec_status': -0.441287532452161,
                        'ship_type_id': 17932,
                        'weapon_type_id': 2881}},
                'items': [
                    {'destroyed': 0, 'dropped': 1, 'flag': 0, 'id': 5531},
                    {'destroyed': 750, 'dropped': 0, 'flag': 5, 'id': 16273},
                    {'destroyed': 1, 'dropped': 0, 'flag': 0, 'id': 21096},
                    {'destroyed': 1, 'dropped': 0, 'flag': 0, 'id': 2605}],
                'id': 15640545,
                'moon_id': 0,
                'system_id': 30001160,
                'time': 1290612480,
                'victim': {
                    'alliance': {
                        'id': 1254074,
                        'name': 'EVE Gurus'},
                    'corp': {
                        'id': 1254875843,
                        'name': 'Starbase Anchoring Corp'},
                    'damage': 446,
                    'faction': {
                        'id': 0,
                        'name': ''},
                    'id': 150080271,
                    'name': 'Pilot 333',
                    'ship_type_id': 670}},
            15640551: {
                'attackers': {
                    935091361: {
                        'alliance': {
                            'id': 5514808,
                            'name': 'Authorities of EVE'},
                        'corp': {
                            'id': 224588600,
                            'name': 'Inkblot Squad'},
                        'damage': 446,
                        'faction': {
                            'id': 0,
                            'name': ''},
                        'final_blow': True,
                        'id': 935091361,
                        'name': 'ICU123',
                        'sec_status': -0.441287532452161,
                        'ship_type_id': 17932,
                        'weapon_type_id': 2881}},
                'items': [
                    {'destroyed': 1, 'dropped': 0, 'flag': 14, 'id': 1319},
                    {'destroyed': 1, 'dropped': 0, 'flag': 28, 'id': 11370},
                    {'destroyed': 1, 'dropped': 0, 'flag': 93, 'id': 31119},
                    {'destroyed': 1, 'dropped': 0, 'flag': 5, 'id': 3467},
                    {'destroyed': 1, 'dropped': 0, 'flag': 0, 'id': 819},
                    {'destroyed': 2, 'dropped': 0, 'flag': 0, 'id': 4394},
                    {'destroyed': 0, 'dropped': 1, 'flag': 5, 'id': 11489},
                    {'destroyed': 0, 'dropped': 7, 'flag': 0, 'id': 9213},
                    {'destroyed': 0, 'dropped': 1, 'flag': 0, 'id': 4260},
                    {'destroyed': 0, 'dropped': 1, 'flag': 0, 'id': 9141}],
                'id': 15640551,
                'moon_id': 0,
                'system_id': 30001160,
                'time': 1290612540,
                'victim': {
                    'alliance': {
                        'id': 1254074,
                        'name': 'EVE Gurus'},
                    'corp': {
                        'id': 1254875843,
                        'name': 'Starbase Anchoring Corp'},
                    'damage': 446,
                    'faction': {
                        'id': 0,
                        'name': ''},
                    'id': 150080271,
                    'name': 'Pilot 333',
                    'ship_type_id': 670}}
            })

########NEW FILE########
__FILENAME__ = test_orders
import mock

from tests.compat import unittest
from tests.utils import make_api_result

from evelink.parsing import orders as evelink_o

class OrdersTestCase(unittest.TestCase):

    def test_parse_market_orders(self):
        api_result, _, _ = make_api_result("char/orders.xml")

        result = evelink_o.parse_market_orders(api_result)

        self.assertEqual(result, {
            2579890411: {
                'account_key': 1000,
                'char_id': 91397530,
                'duration': 90,
                'amount': 2120,
                'escrow': 0.0,
                'id': 2579890411,
                'type': 'sell',
                'timestamp': 1340742712,
                'price': 5100.0,
                'range': 32767,
                'amount_left': 2120,
                'status': 'active',
                'station_id': 60011866,
                'type_id': 3689},
            2584848036: {
                'account_key': 1000,
                'char_id': 91397530,
                'duration': 90,
                'amount': 1,
                'escrow': 0.0,
                'id': 2584848036,
                'type': 'sell',
                'timestamp': 1341183080,
                'price': 250000.0,
                'range': 32767,
                'amount_left': 1,
                'status': 'active',
                'station_id': 60012550,
                'type_id': 16399}
            })

########NEW FILE########
__FILENAME__ = test_wallet_journal
from tests.compat import unittest
from tests.utils import make_api_result

from evelink.parsing import wallet_journal as evelink_w

class WalletJournalTestCase(unittest.TestCase):
    def test_wallet_journal(self):
        api_result, _, _ = make_api_result("char/wallet_journal.xml")

        result = evelink_w.parse_wallet_journal(api_result)

        self.assertEqual(result, [{
            'amount': -10000.0,
            'arg': {'id': 0, 'name': '35402941'},
            'balance': 985620165.53,
            'timestamp': 1291962600,
            'id': 3605301231,
            'party_1': {'id': 150337897, 'name': 'corpslave12', 'type': 2},
            'party_2': {'id': 1000132, 'name': 'Secure Commerce Commission', 'type': 1378},
            'reason': '',
            'tax': {'amount': 0.0, 'taxer_id': 0},
            'type_id': 72},
        {
            'amount': -10000.0,
            'arg': {'id': 0, 'name': '35402950'},
            'balance': 985610165.53,
            'timestamp': 1291962600,
            'id': 3605302609,
            'party_1': {'id': 150337897, 'name': 'corpslave12', 'type': 2},
            'party_2': {'id': 1000132, 'name': 'Secure Commerce Commission', 'type': 1378},
            'reason': '',
            'tax': {'amount': 0.0, 'taxer_id': 0},
            'type_id': 72},
        {
            'amount': -10000.0,
            'arg': {'id': 0, 'name': '35402956'},
            'balance': 985600165.53,
            'timestamp': 1291962660,
            'id': 3605303380,
            'party_1': {'id': 150337897, 'name': 'corpslave12', 'type': 2},
            'party_2': {'id': 1000132, 'name': 'Secure Commerce Commission', 'type': 1378},
            'reason': '',
            'tax': {'amount': 0.0, 'taxer_id': 0},
            'type_id': 72},
        {
            'amount': -10000.0,
            'arg': {'id': 0, 'name': '35402974'},
            'balance': 985590165.53,
            'timestamp': 1291962720,
            'id': 3605305292,
            'party_1': {'id': 150337897, 'name': 'corpslave12', 'type': 2},
            'party_2': {'id': 1000132, 'name': 'Secure Commerce Commission', 'type': 1378},
            'reason': '',
            'tax': {'amount': 0.0, 'taxer_id': 0},
            'type_id': 72},
        {
            'amount': -10000.0,
            'arg': {'id': 0, 'name': '35402980'},
            'balance': 985580165.53,
            'timestamp': 1291962720,
            'id': 3605306236,
            'party_1': {'id': 150337897, 'name': 'corpslave12', 'type': 2},
            'party_2': {'id': 1000132, 'name': 'Secure Commerce Commission', 'type': 1378},
            'reason': '',
            'tax': {'amount': 0.0, 'taxer_id': 0},
            'type_id': 72},
        ])

    def test_corp_wallet_journal(self):
        api_result, _, _ = make_api_result("corp/wallet_journal.xml")

        result = evelink_w.parse_wallet_journal(api_result)

        self.assertEqual(result, [{
            'amount': 3843.75,
            'balance': 119691201.37,
            'party_2': {'name': 'Varax Artrald', 'id': 92229838, 'type': 1378},
            'type_id': 85,
            'reason': '24156:1,',
            'timestamp': 1349149240,
            'tax': {'taxer_id': 0, 'amount': 0.0},
            'party_1': {'name': 'CONCORD', 'id': 1000125, 'type': 2},
            'arg': {'name': '9-F0B2', 'id': 30003704},
            'id': 6421767712},
        {
            'amount': 97500.0,
            'balance': 119802845.12,
            'party_2': {'name': 'Valkyries of Night', 'id': 544497016, 'type': 1378},
            'type_id': 60,
            'reason': '',
            'timestamp': 1349155785,
            'tax': {'taxer_id': 0, 'amount': 0.0},
            'party_1': {'name': 'Valkyries of Night', 'id': 544497016, 'type': 2},
            'arg': {'name': '153187659', 'id': 0},
            'id': 6421966585},
        {
            'amount': 6250.0,
            'balance': 119858095.12,
            'party_2': {'name': 'Valkyries of Night', 'id': 544497016, 'type': 1378},
            'type_id': 57,
            'reason': '',
            'timestamp': 1349189425,
            'tax': {'taxer_id': 0, 'amount': 0.0},
            'party_1': {'name': 'Valkyries of Night', 'id': 544497016, 'type': 2},
            'arg': {'name': '153219782', 'id': 0}, 'id': 6422968336}
        ])





########NEW FILE########
__FILENAME__ = test_wallet_transactions
import mock

from tests.compat import unittest
from tests.utils import make_api_result

from evelink.parsing import wallet_transactions as evelink_w

class TransactionsTestCase(unittest.TestCase):

    def test_parse_wallet_transactions(self):
        api_result, _, _ = make_api_result("char/wallet_transactions.xml")

        result = evelink_w.parse_wallet_transactions(api_result)

        self.assertEqual(result, [
           {'client': {'id': 1034922339, 'name': 'Elthana'},
            'id': 1309776438,
            'action': 'buy',
            'for': 'personal',
            'journal_id': 6256809868,
            'price': 34101.06,
            'quantity': 1,
            'station': {'id': 60003760,
                        'name': 'Jita IV - Moon 4 - Caldari Navy Assembly Plant'},
            'timestamp': 1265513640,
            'type': {'id': 20495, 'name': 'Information Warfare'}},
           {'client': {'id': 1979235241, 'name': 'Daeja synn'},
            'id': 1307711508,
            'action': 'buy',
            'for': 'personal',
            'journal_id': 6256808968,
            'price': 1169939.97,
            'quantity': 1,
            'station': {'id': 60015027,
                        'name': 'Uitra VI - Moon 4 - State War Academy School'},
            'timestamp': 1265392020,
            'type': {'id': 11574, 'name': 'Wing Command'}},
           {'client': {'id': 275581519, 'name': 'SPAIDERKA'},
            'char': {'id': 124, 'name': 'Bar'},
            'id': 1304203159,
            'action': 'buy',
            'for': 'personal',
            'journal_id': 6256808878,
            'price': 13012.01,
            'quantity': 2,
            'station': {'id': 60003760,
                        'name': 'Jita IV - Moon 4 - Caldari Navy Assembly Plant'},
            'timestamp': 1265135280,
            'type': {'id': 3349, 'name': 'Skirmish Warfare'}},
           {'client': {'id': 1703231064, 'name': 'Der Suchende'},
            'char': {'id': 123, 'name': 'Foo'},
            'id': 1298649939,
            'action': 'buy',
            'for': 'personal',
            'journal_id': 6256808869,
            'price': 556001.01,
            'quantity': 1,
            'station': {'id': 60004369,
                        'name': 'Ohmahailen V - Moon 7 - Corporate Police Force Assembly Plant'},
            'timestamp': 1264779900,
            'type': {'id': 2410, 'name': 'Heavy Missile Launcher II'}}
        ])


########NEW FILE########
__FILENAME__ = test_account
import mock

from tests.compat import unittest
from tests.utils import APITestCase

import evelink.account as evelink_account
from evelink import constants

class AccountTestCase(APITestCase):

    def setUp(self):
        super(AccountTestCase, self).setUp()
        self.account = evelink_account.Account(api=self.api)

    def test_status(self):
        self.api.get.return_value = self.make_api_result("account/status.xml")

        result, current, expires = self.account.status()

        self.assertEqual(result, {
                'create_ts': 1072915200,
                'logins': 1234,
                'minutes_played': 9999,
                'paid_ts': 1293840000,
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('account/AccountStatus', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_key_info(self):
        self.api.get.return_value = self.make_api_result("account/key_info.xml")

        result, current, expires = self.account.key_info()

        self.assertEqual(result, {
                'access_mask': 59760264,
                'type': constants.CHARACTER,
                'expire_ts': 1315699200,
                'characters': {
                    898901870: {
                        'id': 898901870,
                        'name': "Desmont McCallock",
                        'corp': {
                            'id': 1000009,
                            'name': "Caldari Provisions",
                        },
                    },
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('account/APIKeyInfo', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_characters(self):
        self.api.get.return_value = self.make_api_result("account/characters.xml")

        result, current, expires = self.account.characters()

        self.assertEqual(result, {
                1365215823: {
                    'corp': {
                        'id': 238510404,
                        'name': 'Puppies To the Rescue',
                    },
                    'id': 1365215823,
                    'name': 'Alexis Prey',
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('account/Characters', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_api
import sys
import zlib
import mock

from tests.compat import unittest

from evelink.thirdparty.six import BytesIO as StringIO
from evelink.thirdparty.six.moves import urllib
import evelink.api as evelink_api


def compress(s):
    return zlib.compress(s)

class HelperTestCase(unittest.TestCase):

    def test_parse_ts(self):
        self.assertEqual(
            evelink_api.parse_ts("2012-06-12 12:04:33"),
            1339502673,
        )

class CacheTestCase(unittest.TestCase):

    def setUp(self):
        self.cache = evelink_api.APICache()

    def test_cache(self):
        self.cache.put('foo', 'bar', 3600)
        self.assertEqual(self.cache.get('foo'), 'bar')

    def test_expire(self):
        self.cache.put('baz', 'qux', -1)
        self.assertEqual(self.cache.get('baz'), None)

class APITestCase(unittest.TestCase):

    def setUp(self):
        self.cache = mock.MagicMock(spec=evelink_api.APICache)
        self.api = evelink_api.API(cache=self.cache)
        # force disable requests if enabled.
        self._has_requests = evelink_api._has_requests
        evelink_api._has_requests = False

        self.test_xml = r"""
                <?xml version='1.0' encoding='UTF-8'?>
                <eveapi version="2">
                    <currentTime>2009-10-18 17:05:31</currentTime>
                    <result>
                        <rowset>
                            <row foo="bar" />
                            <row foo="baz" />
                        </rowset>
                    </result>
                    <cachedUntil>2009-11-18 17:05:31</cachedUntil>
                </eveapi>
            """.strip().encode()

        self.error_xml = r"""
                <?xml version='1.0' encoding='UTF-8'?>
                <eveapi version="2">
                    <currentTime>2009-10-18 17:05:31</currentTime>
                    <error code="123">
                        Test error message.
                    </error>
                    <cachedUntil>2009-11-18 19:05:31</cachedUntil>
                </eveapi>
            """.strip().encode()

    def tearDown(self):
        evelink_api._has_requests = self._has_requests

    def test_cache_key(self):
        assert self.api._cache_key('foo/bar', {})
        assert self.api._cache_key('foo/bar', {'baz': 'qux'})

        self.assertEqual(
            self.api._cache_key('foo/bar', {'a':1, 'b':2}),
            self.api._cache_key('foo/bar', {'b':2, 'a':1}),
        )

    def test_cache_key_variance(self):
        """Make sure that things which shouldn't have the same cache key don't."""
        self.assertNotEqual(
            self.api._cache_key('foo/bar', {'a':1}),
            self.api._cache_key('foo/bar', {'a':2}),
        )

        self.assertNotEqual(
            self.api._cache_key('foo/bar', {'a':1}),
            self.api._cache_key('foo/bar', {'b':1}),
        )

        self.assertNotEqual(
            self.api._cache_key('foo/bar', {}),
            self.api._cache_key('foo/baz', {}),
        )

    @mock.patch('evelink.thirdparty.six.moves.urllib.request.urlopen')
    def test_get(self, mock_urlopen):
        # mock up an urlopen compatible response object and pretend to have no
        # cached results; similar pattern for all test_get_* methods below.
        mock_urlopen.return_value.read.return_value = self.test_xml
        self.cache.get.return_value = None

        result = self.api.get('foo/Bar', {'a':[1,2,3]})

        self.assertEqual(len(result), 3)
        result, current, expiry = result

        rowset = result.find('rowset')
        rows = rowset.findall('row')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].attrib['foo'], 'bar')
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258563931,
        })
        self.assertEqual(current, 1255885531)
        self.assertEqual(expiry, 1258563931)

    @mock.patch('evelink.thirdparty.six.moves.urllib.request.urlopen')
    def test_cached_get(self, mock_urlopen):
        """Make sure that we don't try to call the API if the result is cached."""
        # mock up a urlopen compatible error response, and pretend to have a
        # good test response cached.
        mock_urlopen.return_value.read.return_value = self.error_xml
        self.cache.get.return_value = self.test_xml

        result = self.api.get('foo/Bar', {'a':[1,2,3]})

        # Ensure this is really not called.
        self.assertFalse(mock_urlopen.called)

        self.assertEqual(len(result), 3)
        result, current, expiry = result

        rowset = result.find('rowset')
        rows = rowset.findall('row')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].attrib['foo'], 'bar')

        # timestamp attempted to be extracted.
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258563931,
        })
        self.assertEqual(current, 1255885531)
        self.assertEqual(expiry, 1258563931)

    @mock.patch('evelink.thirdparty.six.moves.urllib.request.urlopen')
    def test_get_with_apikey(self, mock_urlopen):
        mock_urlopen.return_value.read.return_value = self.test_xml
        self.cache.get.return_value = None

        api_key = (1, 'code')
        api = evelink_api.API(cache=self.cache, api_key=api_key)

        api.get('foo', {'a':[2,3,4]})

        # Make sure the api key id and verification code were passed
        self.assertTrue(mock_urlopen.called)
        self.assertTrue(len(mock_urlopen.call_args[0]) > 0)

        request = mock_urlopen.call_args[0][0]
        self.assertEqual(
            'https://api.eveonline.com/foo.xml.aspx',
            request.get_full_url()
        )

        request_dict = urllib.parse.parse_qs(request.data.decode())
        expected_request_dict = urllib.parse.parse_qs("a=2%2C3%2C4&vCode=code&keyID=1")

        self.assertEqual(request_dict, expected_request_dict)

    @mock.patch('evelink.thirdparty.six.moves.urllib.request.urlopen')
    def test_get_with_error(self, mock_urlopen):
        # I had to go digging in the source code for urllib2 to find out
        # how to manually instantiate HTTPError instances. :( The empty
        # dict is the headers object.
        def raise_http_error(*args, **kw):
            raise urllib.error.HTTPError(
                "http://api.eveonline.com/eve/Error",
                404,
                "Not found!",
                {},
                StringIO(self.error_xml)
            )
        mock_urlopen.side_effect = raise_http_error
        self.cache.get.return_value = None

        self.assertRaises(evelink_api.APIError,
            self.api.get, 'eve/Error')
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258571131,
        })

    @mock.patch('evelink.thirdparty.six.moves.urllib.request.urlopen')
    def test_get_with_compressed_error(self, mock_urlopen):
        # I had to go digging in the source code for urllib2 to find out
        # how to manually instantiate HTTPError instances. :( The empty
        # dict is the headers object.
        def raise_http_error(*args, **kw):
            raise urllib.error.HTTPError(
                "http://api.eveonline.com/eve/Error",
                404,
                "Not found!",
                {'Content-Encoding': 'gzip'},
                StringIO(compress(self.error_xml))
            )
        mock_urlopen.side_effect = raise_http_error
        self.cache.get.return_value = None

        self.assertRaises(evelink_api.APIError,
            self.api.get, 'eve/Error')
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258571131,
        })

    @mock.patch('evelink.thirdparty.six.moves.urllib.request.urlopen')
    def test_cached_get_with_error(self, mock_urlopen):
        """Make sure that we don't try to call the API if the result is cached."""
        # mocked response is good now, with the error response cached.
        mock_urlopen.return_value.read.return_value = self.test_xml
        self.cache.get.return_value = self.error_xml

        self.assertRaises(evelink_api.APIError,
            self.api.get, 'foo/Bar', {'a':[1,2,3]})

        self.assertFalse(mock_urlopen.called)
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258571131,
        })

    @mock.patch('evelink.thirdparty.six.moves.urllib.request.urlopen')
    def test_get_request_compress_response(self, mock_urlopen):
        mock_urlopen.return_value.read.return_value = compress(self.test_xml)
        mock_urlopen.return_value.info.return_value.get.return_value = 'gzip'
        self.cache.get.return_value = None

        result = self.api.get('foo/Bar', {'a':[1,2,3]})
        self.assertTrue(mock_urlopen.called)
        self.assertTrue(len(mock_urlopen.call_args[0]) > 0)
        self.assertEqual(
            'gzip', 
            mock_urlopen.call_args[0][0].get_header('Accept-encoding')
        )

        self.assertEqual(len(result), 3)
        result, current, expiry = result

        rowset = result.find('rowset')
        rows = rowset.findall('row')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].attrib['foo'], 'bar')
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258563931,
        })
        self.assertEqual(current, 1255885531)
        self.assertEqual(expiry, 1258563931)

class AutoCallTestCase(unittest.TestCase):

    def test_python_func(self):
        def func(a, b, c=None, d=None):
            return a, b, c, d

        self.assertEqual((1, 2, 3, 4,), func(1, 2, c=3, d=4))
        self.assertEqual((1, 2, 3, 4,), func(a=1, b=2, c=3, d=4))
        self.assertEqual((1, 2, 3, 4,), func(c=3, a=1, b=2, d=4))
        self.assertEqual((1, 2, 3, 4,), func(1, b=2, c=3, d=4))
        self.assertRaises(TypeError, func, 2, a=1, c=3, d=4)

    def test_translate_args(self):
        args = {'foo': 'bar'}
        mapping = {'foo': 'baz'}
        self.assertEqual(
            {'baz': 'bar'}, 
            evelink_api.translate_args(args, mapping)
        )

    def test_get_args_and_defaults(self):
        def target(a, b, c=None, d=None):
            pass
        args_specs, defaults = evelink_api.get_args_and_defaults(target)
        self.assertEqual(['a', 'b', 'c', 'd'], args_specs)
        self.assertEqual({'c': None, 'd': None}, defaults)

    def test_map_func_args(self):
        args = [1, 2]
        kw = {'c': 3, 'd': 4}
        args_names = ('a', 'b', 'c', 'd',)
        defaults = {'c': None, 'd': None}
        map_ = evelink_api.map_func_args(args, kw, args_names, defaults)
        self.assertEqual({'a': 1, 'b': 2, 'c': 3, 'd': 4}, map_)

    def test_map_func_args_with_default(self):
        args = [1, 2]
        kw = {'c': 3}
        args_names = ('a', 'b', 'c', 'd',)
        defaults = {'c': None, 'd': None}
        map_ = evelink_api.map_func_args(args, kw, args_names, defaults)
        self.assertEqual({'a': 1, 'b': 2, 'c': 3, 'd': None}, map_)

    def test_map_func_args_with_all_positional_arguments(self):
        args = [1, 2, 3, 4]
        kw = {}
        args_names = ('a', 'b', 'c', 'd',)
        defaults = {'c': None, 'd': None}
        map_ = evelink_api.map_func_args(args, kw, args_names, defaults)
        self.assertEqual({'a': 1, 'b': 2, 'c': 3, 'd': 4}, map_)

    def test_map_func_args_with_too_many_argument(self):
        args = [1, 2, 3]
        kw = {'c': 4, 'd': 5}
        args_names = ('a', 'b', 'c', 'd',)
        defaults = {'c': None, 'd': None}
        self.assertRaises(
            TypeError,
            evelink_api.map_func_args,
            args,
            kw,
            args_names,
            defaults
        )

    def test_map_func_args_with_twice_same_argument(self):
        args = [2]
        kw = {'a': 1, 'c': 3, 'd': 4}
        args_names = ('a', 'b', 'c', 'd',)
        defaults = {'c': None, 'd': None}
        self.assertRaises(
            TypeError,
            evelink_api.map_func_args,
            args,
            kw,
            args_names,
            defaults
        )

    def test_map_func_args_with_too_few_args(self):
        args = [1, ]
        kw = {'c': 3, 'd': 4}
        args_names = ('a', 'b', 'c', 'd',)
        defaults = {'c': None, 'd': None}
        self.assertRaises(
            TypeError,
            evelink_api.map_func_args,
            args,
            kw,
            args_names,
            defaults
        )

    def test_deco_add_request_specs(self):
        
        @evelink_api.auto_call('foo/bar')
        def func(self, char_id, limit=None, before_kill=None, api_result=None):
            pass

        self.assertEqual(
            {
                'path': 'foo/bar',
                'args': [
                    'char_id', 'limit', 'before_kill'
                ],
                'defaults': dict(limit=None, before_kill=None),
                'prop_to_param': tuple(),
                'map_params': {}
            },
            func._request_specs
            )

    def test_call_wrapped_method(self):
        repeat = mock.Mock()
        client = mock.Mock(name='foo')

        @evelink_api.auto_call(
            'foo/bar', 
            map_params={'char_id': 'id', 'limit': 'limit', 'before_kill': 'prev'}
        )
        def func(self, char_id, limit=None, before_kill=None, api_result=None):
            repeat(
                self, char_id, limit=limit,
                before_kill=before_kill, api_result=api_result
            )

        func(client, 1, limit=2, before_kill=3)
        repeat.assert_called_once_with(
            client, 1, limit=2, before_kill=3, api_result=client.api.get.return_value
        )
        client.api.get.assert_called_once_with(
            'foo/bar',
            params={'id':1, 'prev': 3, 'limit': 2}
        )

    def test_call_wrapped_method_raise_key_error(self):
        repeat = mock.Mock()
        client = mock.Mock(name='foo')

        @evelink_api.auto_call('foo/bar')
        def func(self, char_id, api_result=None):
            repeat(self, char_id)

        # TODO: raise error when decorating the method
        self.assertRaises(KeyError, func, client, 1)

    def test_call_wrapped_method_none_arguments(self):
        repeat = mock.Mock()
        client = mock.Mock(name='foo')

        @evelink_api.auto_call(
            'foo/bar', map_params={'char_id': 'char_id', 'limit': 'limit'}
        )
        def func(self, char_id, limit=None, api_result=None):
            repeat(self, char_id, limit=limit, api_result=api_result)

        func(client, 1)
        repeat.assert_called_once_with(
            client, 1, limit=None, api_result=client.api.get.return_value
        )
        client.api.get.assert_called_once_with(
            'foo/bar',
            params={'char_id':1}
        )

    def test_call_wrapped_method_with_properties(self):
        repeat = mock.Mock()
        client = mock.Mock(name='client')
        client.char_id = 1

        @evelink_api.auto_call(
            'foo/bar',
            prop_to_param=('char_id',),
            map_params={'char_id': 'char_id', 'limit': 'limit'}
        )
        def func(self, limit=None, api_result=None):
            repeat(
                self, 
                limit=limit, api_result=api_result
            )

        func(client, limit=2)
        repeat.assert_called_once_with(
            client, limit=2, api_result=client.api.get.return_value
        )
        client.api.get.assert_called_once_with(
            'foo/bar',
            params={'char_id':1, 'limit': 2}
        )

    def test_call_wrapped_method_with_api_result(self):
        repeat = mock.Mock()
        client = mock.Mock(name='client')
        results = mock.Mock(name='APIResult')

        @evelink_api.auto_call('foo/bar')
        def func(self, char_id, limit=None, before_kill=None, api_result=None):
            repeat(
                self, char_id, limit=limit,
                before_kill=before_kill, api_result=api_result
            )

        func(client, 1, limit=2, before_kill=3, api_result=results)
        repeat.assert_called_once_with(
            client, 1, limit=2, before_kill=3, api_result=results
        )
        self.assertFalse(client.get.called)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_account
import mock

from tests.compat import unittest

from tests.test_appengine import (
    GAEAsyncTestCase, auto_test_async_method
)

try:
    from evelink.appengine.account import Account
except ImportError as e:
    Account = mock.Mock()

_specs = ('status','key_info','characters',)


@auto_test_async_method(Account, _specs)
class AppEngineAccountTestCase(GAEAsyncTestCase):
    pass


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_api
import mock

from tests.compat import unittest
from tests.test_appengine import GAETestCase

try:
    from google.appengine.ext import testbed
    from google.appengine.ext import ndb
    from google.appengine.api import apiproxy_stub
    from google.appengine.api import apiproxy_stub_map

except ImportError:
    apiproxy_stub = mock.Mock()
else:

    from evelink import appengine
    from evelink.api import APIError


class URLFetchServiceMock(apiproxy_stub.APIProxyStub):
    """Mock for google.appengine.api.urlfetch.

    http://blog.rebeiro.net/2012/03/mocking-appengines-urlfetch-service-in.html

    """
    
    def __init__(self, service_name='urlfetch'):
        super(URLFetchServiceMock, self).__init__(service_name)

    def set_return_values(self, **kwargs):
        self.return_values = kwargs

    def _Dynamic_Fetch(self, request, response):
        return_values = self.return_values
        response.set_content(return_values.get('content', ''))
        response.set_statuscode(return_values.get('status_code', 200))
        for header_key, header_value in return_values.get('headers', {}).items():
            new_header = response.add_header()
            new_header.set_key(header_key)
            new_header.set_value(header_value)
        response.set_finalurl(return_values.get('final_url', request.url()))
        response.set_contentwastruncated(return_values.get('content_was_truncated', False))

        self.request = request
        self.response = response


class DatastoreCacheTestCase(GAETestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_memcache_stub()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_cache_datastore(self):
        cache = appengine.AppEngineDatastoreCache()
        cache.put('foo', 'bar', 3600)
        cache.put('bar', 1, 3600)
        cache.put('baz', True, 3600)
        self.assertEqual(cache.get('foo'), 'bar')
        self.assertEqual(cache.get('bar'), 1)
        self.assertEqual(cache.get('baz'), True)

    def test_expire_datastore(self):
        cache = appengine.AppEngineDatastoreCache()
        cache.put('baz', 'qux', 3600)
        cache.put('baz', 'qux', -1)
        self.assertEqual(cache.get('baz'), None)

    def test_async_cache(self):
        cache = appengine.AppEngineDatastoreCache()
        ndb.Future.wait_all(
            [
                cache.put_async('foo', 'bar', 3600),
                cache.put_async('bar', 1, 3600),
                cache.put_async('baz', True, 3600),
            ]
        )
        self.assertEqual(cache.get_async('foo').get_result(), 'bar')
        self.assertEqual(cache.get_async('bar').get_result(), 1)
        self.assertEqual(cache.get_async('baz').get_result(), True) 


class MemcacheCacheTestCase(GAETestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_cache_memcache(self):
        cache = appengine.AppEngineCache()
        cache.put('foo', 'bar', 3600)
        cache.put('bar', 1, 3600)
        cache.put('baz', True, 3600)
        self.assertEqual(cache.get('foo'), 'bar')
        self.assertEqual(cache.get('bar'), 1)
        self.assertEqual(cache.get('baz'), True)

    def test_expire_memcache(self):
        cache = appengine.AppEngineCache()
        cache.put('baz', 'qux', 3600)
        cache.put('baz', 'qux', -1)
        self.assertEqual(cache.get('baz'), None)

    def test_async_cache(self):
        cache = appengine.AppEngineCache()
        ndb.Future.wait_all(
            [
                cache.put_async('foo', 'bar', 3600),
                cache.put_async('bar', 1, 3600),
                cache.put_async('baz', True, 3600),
            ]
        )
        self.assertEqual(cache.get_async('foo').get_result(), 'bar')
        self.assertEqual(cache.get_async('bar').get_result(), 1)
        self.assertEqual(cache.get_async('baz').get_result(), True)        


class AppEngineAPITestCase(GAETestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_memcache_stub()
        self.urlfetch_mock = URLFetchServiceMock()
        apiproxy_stub_map.apiproxy.ReplaceStub(
            'urlfetch', 
            self.urlfetch_mock
        )

        self.test_xml = r"""
            <?xml version='1.0' encoding='UTF-8'?>
            <eveapi version="2">
                <currentTime>2009-10-18 17:05:31</currentTime>
                <result>
                    <rowset>
                        <row foo="bar" />
                        <row foo="baz" />
                    </rowset>
                </result>
                <cachedUntil>2009-11-18 17:05:31</cachedUntil>
            </eveapi>
        """.strip()

        self.error_xml = r"""
            <?xml version='1.0' encoding='UTF-8'?>
            <eveapi version="2">
                <currentTime>2009-10-18 17:05:31</currentTime>
                <error code="123">
                    Test error message.
                </error>
                <cachedUntil>2009-11-18 19:05:31</cachedUntil>
            </eveapi>
        """.strip()

    def tearDown(self):
        self.testbed.deactivate()

    def test_get(self):
        self.urlfetch_mock.set_return_values(
            content=self.test_xml,
            status_code=200
        )

        api = appengine.AppEngineAPI()
        result = api.get('foo/Bar', {'a':[1,2,3]}).result

        rowset = result.find('rowset')
        rows = rowset.findall('row')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].attrib['foo'], 'bar')
        self.assertEqual(api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258563931,
        })

    def test_get_raise_api_error(self):
        self.urlfetch_mock.set_return_values(
            content=self.error_xml,
            status_code=400
        )

        api = appengine.AppEngineAPI()

        self.assertRaises(APIError, api.get, 'eve/Error')
        self.assertEqual(api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258571131,
        })

    def test_get_async(self):
        self.urlfetch_mock.set_return_values(
            content=self.test_xml,
            status_code=200
        )

        api = appengine.AppEngineAPI()
        result = api.get_async('foo/Bar', {'a':[1,2,3]}).get_result().result

        rowset = result.find('rowset')
        rows = rowset.findall('row')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].attrib['foo'], 'bar')
        self.assertEqual(api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258563931,
        })


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_char
import mock

from tests.compat import unittest

from tests.test_appengine import (
    GAEAsyncTestCase
)

try:
    from evelink.appengine import AppEngineAPI
    from evelink.appengine.char import Char
except ImportError:
    Char = mock.Mock()


class AppEngineCharTestCase(GAEAsyncTestCase):
    
    def setUp(self):
        api = AppEngineAPI()
        self.client = Char(1, api)

    def test_assets_async(self):
        self.compare(
            Char,
            'assets',
            'corp/assets.xml',
            _client=self.client
        )
    
    def test_calendar_attendees_async(self):
        self.compare(
            Char,
            'calendar_attendees',
            'char/calendar_attendees.xml',
            [123,234,],
            _client=self.client
        )
    
    def test_calendar_events_async(self):
        self.compare(
            Char,
            'calendar_events',
            'char/calendar_events.xml',
            _client=self.client
        )
    
    def test_character_sheet_async(self):
        self.compare(
            Char,
            'character_sheet',
            'char/character_sheet.xml',
            _client=self.client
        )
    
    def test_contact_notifications_async(self):
        self.compare(
            Char,
            'contact_notifications',
            'char/contact_notifications.xml',
            _client=self.client
        )
    
    def test_contacts_async(self):
        self.compare(
            Char,
            'contacts',
            'char/contact_list.xml',
            _client=self.client
        )
    
    def test_contract_bids_async(self):
        self.compare(
            Char,
            'contract_bids',
            'char/contract_bids.xml',
            _client=self.client
        )
    
    def test_contract_items_async(self):
        self.compare(
            Char,
            'contract_items',
            'char/contract_items.xml',
            1228,
            _client=self.client
        )
    
    def test_contracts_async(self):
        self.compare(
            Char,
            'contracts',
            'corp/contracts.xml',
            _client=self.client
        )
    
    def test_current_training_async(self):
        self.compare(
            Char,
            'current_training',
            'char/current_training.xml',
            _client=self.client
        )
    
    def test_event_attendees_async(self):
        self.compare(
            Char,
            'event_attendees',
            'char/calendar_attendees_by_id.xml',
            234,
            _client=self.client
        )
    
    def test_faction_warfare_stats_async(self):
        self.compare(
            Char,
            'faction_warfare_stats',
            'char/faction_warfare_stats.xml',
            _client=self.client
        )
    
    def test_industry_jobs_async(self):
        self.compare(
            Char,
            'industry_jobs',
            'char/industry_jobs.xml',
            _client=self.client
        )
    
    def test_kills_async(self):
        self.compare(
            Char,
            'kills',
            'char/kills.xml',
            _client=self.client
        )
    
    def test_locations_async(self):
        self.compare(
            Char,
            'locations',
            'char/locations.xml',
            345678,
            _client=self.client
        )
    
    def test_mailing_lists_async(self):
        self.compare(
            Char,
            'mailing_lists',
            'char/mailing_lists.xml',
            _client=self.client
        )
    
    def test_medals_async(self):
        self.compare(
            Char,
            'medals',
            'char/medals.xml',
            _client=self.client
        )
    
    def test_message_bodies_async(self):
        self.compare(
            Char,
            'message_bodies',
            'char/message_bodies.xml',
            234567,
            _client=self.client
        )
    
    def test_messages_async(self):
        self.compare(
            Char,
            'messages',
            'char/messages.xml',
            _client=self.client
        )
    
    def test_notification_texts_async(self):
        self.compare(
            Char,
            'notification_texts',
            'char/notification_texts.xml',
            123456,
            _client=self.client
        )
    
    def test_notifications_async(self):
        self.compare(
            Char,
            'notifications',
            'char/notifications.xml',
            _client=self.client
        )
    
    def test_orders_async(self):
        self.compare(
            Char,
            'orders',
            'char/orders.xml',
            _client=self.client
        )
    
    def test_research_async(self):
        self.compare(
            Char,
            'research',
            'char/research.xml',
            _client=self.client
        )
    
    def test_skill_queue_async(self):
        self.compare(
            Char,
            'skill_queue',
            'char/skill_queue.xml',
            _client=self.client
        )
    
    def test_standings_async(self):
        self.compare(
            Char,
            'standings',
            'char/standings.xml',
            _client=self.client
        )
    
    def test_wallet_balance_async(self):
        self.compare(
            Char,
            'wallet_balance',
            'char/wallet_balance.xml',
            _client=self.client
        )
    
    def test_wallet_info_async(self):
        self.compare(
            Char,
            'wallet_info',
            'char/wallet_info.xml',
            _client=self.client
        )
    
    def test_wallet_journal_async(self):
        self.compare(
            Char,
            'wallet_journal',
            'char/wallet_journal.xml',
            _client=self.client
        )
    
    def test_wallet_transactions_async(self):
        self.compare(
            Char,
            'wallet_transactions',
            'char/wallet_transactions.xml',
            _client=self.client
        )


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_corp
import mock

from tests.compat import unittest

from tests.test_appengine import (
    GAEAsyncTestCase, auto_test_async_method
)

try:
    from evelink.appengine.corp import Corp
except ImportError:
    Corp = mock.Mock()

@auto_test_async_method(
    Corp, 
    (
        # 'kills',
        'permissions_log',
        # 'starbase_details',
        # 'industry_jobs',
        # 'locations',
        'faction_warfare_stats',
        'titles',
        'members',
        # 'station_services',
        # 'wallet_transactions',
        'corporation_sheet',
        # 'contract_bids',
        # 'orders',
        'permissions',
        'wallet_info',
        'shareholders',
        'container_log',
        'assets',
        # 'contacts',
        'stations',
        'member_medals',
        # 'contract_items',
        'npc_standings',
        'contracts',
        'wallet_journal',
        'medals',
        'starbases',
    )
)
class AppEngineCorpTestCase(GAEAsyncTestCase):
    
    def test_wallet_transactions_async(self):
        self.compare(
            Corp,
            'wallet_transactions',
            "char/wallet_transactions.xml"
        )

    def test_station_services_async(self):
        self.compare(
            Corp,
            'station_services',
            "corp/station_services.xml",
            61000368
        )

    def test_starbase_details_async(self):
        self.compare(
            Corp,
            'starbase_details',
            "corp/starbase_details.xml",
            1234
        )

    def test_orders_async(self):
        self.compare(
            Corp,
            'orders',
            "char/orders.xml",
        )

    def test_locations_async(self):
        self.compare(
            Corp,
            'locations',
            "corp/locations.xml",
            1234
        )

    def test_kills_async(self):
        self.compare(
            Corp,
            'kills',
            "char/kills.xml",
        )
    
    def test_industry_jobs_async(self):
        self.compare(
            Corp,
            'industry_jobs',
            "char/industry_jobs.xml",
        )

    def test_contract_items_async(self):
        self.compare(
            Corp,
            'contract_items',
            "char/contract_items.xml",
            1234
        )

    def test_contract_bids_async(self):
        self.compare(
            Corp,
            'contract_bids',
            "char/contract_bids.xml",
        )

    def test_contacts_async(self):
        self.compare(
            Corp,
            'contacts',
            "char/contact_list.xml",
        )


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_eve
import mock

from tests.compat import unittest

from tests.test_appengine import (
    GAEAsyncTestCase, auto_test_async_method
)

try:
    from evelink.appengine.eve import EVE
except ImportError:
    EVE = mock.Mock()


_specs = (
    'certificate_tree', 
    'alliances', 
    'errors', 
    'faction_warfare_stats', 
    'faction_warfare_leaderboard', 
    'conquerable_stations', 
    'skill_tree',
    'reference_types',
)


@auto_test_async_method(EVE, _specs)
class AppEngineEVETestCase(GAEAsyncTestCase):

    def test_character_names_from_ids_async(self):
        self.compare(
            EVE,
            'character_names_from_ids',
            "eve/character_name.xml",
            [1,2]
        )

    def test_character_name_from_id_async(self):
        "eve/character_name_single.xml"
        self.compare(
            EVE,
            'character_name_from_id',
            "eve/character_name_single.xml",
            1
        )

    def test_character_ids_from_names_async(self):
        self.compare(
            EVE,
            'character_ids_from_names',
            "eve/character_id.xml",
            ["EVE System", "EVE Central Bank"]
        )

    def test_character_id_from_name_async(self):
        self.compare(
            EVE,
            'character_id_from_name',
            "eve/character_id_single.xml",
            "EVE System"
        )

    def test_character_info_from_id_async(self):
        
        self.compare(
            EVE,
            'character_info_from_id',
            "eve/character_info.xml",
            1234
        )


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_map
import mock

from tests.compat import unittest
from tests.test_appengine import (
    GAEAsyncTestCase, auto_test_async_method
)

try:
    from evelink.appengine.map import Map
except ImportError:
    Map = mock.Mock()

@auto_test_async_method(
    Map, 
    (
        'jumps_by_system',
        'kills_by_system',
        'faction_warfare_systems',
        'sov_by_system',
    )
)
class AppEngineMapTestCase(GAEAsyncTestCase):
    pass


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_server
import mock

from tests.compat import unittest
from tests.test_appengine import (
    GAEAsyncTestCase, auto_test_async_method
)


try:
    from evelink.appengine.server import Server
except ImportError:
    Server = mock.Mock()

@auto_test_async_method(Server, ('server_status',))
class AppEngineServerTestCase(GAEAsyncTestCase):
    pass


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_char
import mock

from tests.compat import unittest
from tests.utils import APITestCase

import evelink.api as evelink_api
import evelink.char as evelink_char


API_RESULT_SENTINEL = evelink_api.APIResult(mock.sentinel.api_result, 12345, 67890)


class CharTestCase(APITestCase):

    def setUp(self):
        super(CharTestCase, self).setUp()
        self.char = evelink_char.Char(1, api=self.api)

    @mock.patch('evelink.char.parse_assets')
    def test_assets(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_assets

        result, current, expires = self.char.assets()
        self.assertEqual(result, mock.sentinel.parsed_assets)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/AssetList', params={'characterID': 1}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.char.parse_contract_bids')
    def test_contract_bids(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_contract_bids

        result, current, expires = self.char.contract_bids()
        self.assertEqual(result, mock.sentinel.parsed_contract_bids)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/ContractBids', params={'characterID': 1}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.char.parse_contract_items')
    def test_contract_items(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_contract_items

        result, current, expires = self.char.contract_items(12345)
        self.assertEqual(result, mock.sentinel.parsed_contract_items)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/ContractItems', params={'characterID': 1, 'contractID': 12345}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.char.parse_contracts')
    def test_contracts(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_contracts

        result, current, expires = self.char.contracts()
        self.assertEqual(result, mock.sentinel.parsed_contracts)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/Contracts', params={'characterID': 1}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.char.parse_wallet_journal')
    def test_wallet_journal(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_journal

        result, current, expires = self.char.wallet_journal()
        self.assertEqual(result, mock.sentinel.parsed_journal)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/WalletJournal', params={'characterID': 1}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_wallet_paged(self):
        self.api.get.return_value = self.make_api_result("char/wallet_journal.xml")

        self.char.wallet_journal(before_id=1234)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/WalletJournal', params={'characterID': 1, 'fromID': 1234}),
            ])

    def test_wallet_limit(self):
        self.api.get.return_value = self.make_api_result("char/wallet_journal.xml")

        self.char.wallet_journal(limit=100)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/WalletJournal', params={'characterID': 1, 'rowCount': 100}),
            ])

    def test_wallet_info(self):
        self.api.get.return_value = self.make_api_result("char/wallet_info.xml")

        result, current, expires = self.char.wallet_info()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result,
            {
                'balance': 209127923.31,
                'id': 1,
                'key': 1000,
            }
        )
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/AccountBalance', params={'characterID': 1}),
            ])

    def test_wallet_balance(self):
        self.api.get.return_value = self.make_api_result("char/wallet_balance.xml")

        result, current, expires = self.char.wallet_balance()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, 209127923.31)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/AccountBalance', params={'characterID': 1}),
            ])

    @mock.patch('evelink.char.parse_wallet_transactions')
    def test_wallet_transcations(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_transactions

        result, current, expires = self.char.wallet_transactions()
        self.assertEqual(result, mock.sentinel.parsed_transactions)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/WalletTransactions', params={'characterID': 1}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_wallet_transactions_paged(self):
        self.api.get.return_value = self.make_api_result("char/wallet_transactions.xml")

        self.char.wallet_transactions(before_id=1234)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/WalletTransactions', params={'characterID': 1, 'fromID': 1234}),
            ])

    def test_wallet_transactions_limit(self):
        self.api.get.return_value = self.make_api_result("char/wallet_transactions.xml")

        self.char.wallet_transactions(limit=100)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/WalletTransactions', params={'characterID': 1, 'rowCount': 100}),
            ])

    @mock.patch('evelink.char.parse_industry_jobs')
    def test_industry_jobs(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.industry_jobs

        result, current, expires = self.char.industry_jobs()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, mock.sentinel.industry_jobs)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/IndustryJobs', params={'characterID': 1}),
            ])
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])

    @mock.patch('evelink.char.parse_kills')
    def test_kills(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.kills

        result, current, expires = self.char.kills()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, mock.sentinel.kills)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/KillLog', params={'characterID': 1}),
            ])
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])

    def test_kills_paged(self):
        self.api.get.return_value = self.make_api_result("char/kills_paged.xml")

        self.char.kills(before_kill=12345)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/KillLog', params={'characterID': 1, 'beforeKillID': 12345}),
            ])

    def test_character_sheet(self):
        self.api.get.return_value = self.make_api_result("char/character_sheet.xml")

        result, current, expires = self.char.character_sheet()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
            'id': 150337897,
            'name': 'corpslave',
            'create_ts': 1136073600,
            'race': 'Minmatar',
            'bloodline': 'Brutor',
            'ancestry': 'Slave Child',
            'gender': 'Female',
            'corp': {
                'id': 150337746,
                'name': 'corpexport Corp',
            },
            'alliance': {
                'id': None,
                'name': None
            },
            'clone': {
                'name': 'Clone Grade Pi',
                'skillpoints': 54600000,
            },
            'balance': 190210393.87,
            'attributes': {
                'charisma': {
                    'base': 7,
                    'total': 8,
                    'bonus': {'name': 'Limited Social Adaptation Chip', 'value': 1}},
                'intelligence': {
                    'base': 6,
                    'total': 9,
                    'bonus': {'name': 'Snake Delta', 'value': 3}},
                'memory': {
                    'base': 4,
                    'total': 7,
                    'bonus': {'name': 'Memory Augmentation - Basic', 'value': 3}},
                'perception': {
                    'base': 12,
                    'total': 15,
                    'bonus': {'name': 'Ocular Filter - Basic', 'value': 3}},
                'willpower': {
                    'base': 10,
                    'total': 13,
                    'bonus': {'name': 'Neural Boost - Basic', 'value': 3}}},
        'skills': [{'level': 3, 'published': True, 'skillpoints': 8000, 'id': 3431},
                   {'level': 3, 'published': True, 'skillpoints': 8000, 'id': 3413},
                   {'level': 1, 'published': True, 'skillpoints': 500, 'id': 21059},
                   {'level': 3, 'published': True, 'skillpoints': 8000, 'id': 3416},
                   {'level': 5, 'published': False, 'skillpoints': 512000, 'id': 3445}],
        'skillpoints': 536500,
        'certificates': set([1, 5, 19, 239, 282, 32, 258]),
        'roles': {'global': {1 : {'id': 1, 'name': 'roleDirector'}},
                  'at_base': {1: {'id': 1, 'name': 'roleDirector'}},
                  'at_hq': {1: {'id': 1, 'name': 'roleDirector'}},
                  'at_other': {1: {'id': 1, 'name': 'roleDirector'}}},
        'titles': {1: {'id': 1, 'name': 'Member'}},
        })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/CharacterSheet', params={'characterID': 1}),
            ])

    @mock.patch('evelink.char.parse_contact_list')
    def test_contacts(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_contacts

        result, current, expires = self.char.contacts()
        self.assertEqual(result, mock.sentinel.parsed_contacts)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/ContactList', params={'characterID': 1}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.char.parse_market_orders')
    def test_orders(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_orders

        result, current, expires = self.char.orders()
        self.assertEqual(result, mock.sentinel.parsed_orders)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/MarketOrders', params={'characterID': 1}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_notifications(self):
        self.api.get.return_value = self.make_api_result("char/notifications.xml")

        result, current, expires = self.char.notifications()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
            303795523: {'id': 303795523,
                        'read': True,
                        'sender_id': 671216635,
                        'timestamp': 1270836240,
                        'type_id': 16},
            304084087: {'id': 304084087,
                        'read': False,
                        'sender_id': 797400947,
                        'timestamp': 1271075520,
                        'type_id': 16}
            })

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/Notifications', params={'characterID': 1}),
            ])

    def test_notification_texts(self):
        self.api.get.return_value = self.make_api_result("char/notification_texts.xml")

        result, current, expires = self.char.notification_texts(1234)
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
            374044083: {'shipTypeID': 606,
                        'id': 374044083,
                        'isHouseWarmingGift': 1},
            374067406: {'dueDate': 1336342200,
                        'amount': 25000000,
                        'id': 374067406},
            374106507: {'cost': None,
                        'declaredByID': 98105019,
                        'delayHours': None,
                        'hostileState': None,
                        'againstID': 673381830,
                        'id': 374106507},
            374119034: {'aggressorCorpID': 785714366,
                        'aggressorID': 1746208390,
                        'armorValue': 1.0,
                        'hullValue': 1.0,
                        'moonID': 40264916,
                        'shieldValue': 0.995,
                        'solarSystemID': 30004181,
                        'typeID': 16688,
                        'aggressorAllianceID': 673381830,
                        'id': 374119034},
            374133265: {'itemID': 1005888572647,
                        'payout': 1,
                        'amount': 5125528.4,
                        'id': 374133265}})

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/NotificationTexts', params={'characterID': 1, 'IDs': 1234}),
            ])

    def test_standings(self):
        self.api.get.return_value = self.make_api_result("char/standings.xml")

        result, current, expires = self.char.standings()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
                'agents': {3009841: {'id': 3009841, 'name': 'Pausent Ansin', 'standing': 0.1},
                           3009846: {'id': 3009846, 'name': 'Charie Octienne', 'standing': 0.19}},
                'corps': {1000061: {'id': 1000061, 'name': 'Freedom Extension', 'standing': 0},
                          1000064: {'id': 1000064, 'name': 'Carthum Conglomerate', 'standing': 0.34},
                          1000094: {'id': 1000094, 'name': 'TransStellar Shipping', 'standing': 0.02}},
                'factions': {500003: {'id': 500003, 'name': 'Amarr Empire', 'standing': -0.1},
                             500020: {'id': 500020, 'name': 'Serpentis', 'standing': -1}}},
                )

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/Standings', params={'characterID': 1}),
            ])

    def test_research(self):
        self.api.get.return_value = self.make_api_result("char/research.xml")

        result, current, expires = self.char.research()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
            3014201: {
                'id': 3014201,
                'per_day': 59.52,
                'remaining': -41461.92,
                'skill_id': 11445,
                'timestamp': 1178692470}
            })

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/Research', params={'characterID': 1}),
            ])

    def test_current_training(self):
        self.api.get.return_value = self.make_api_result("char/current_training.xml")

        result, current, expires = self.char.current_training()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
            'current_ts': 1291690831,
            'end_sp': 2048000,
            'end_ts': 1295324413,
            'level': 5,
            'start_sp': 362039,
            'start_ts': 1291645953,
            'active': None,
            'type_id': 23950
            })

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/SkillInTraining', params={'characterID': 1}),
            ])

    def test_skill_queue(self):
        self.api.get.return_value = self.make_api_result("char/skill_queue.xml")

        result, current, expires = self.char.skill_queue()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, [
            {
                'end_ts': 1295324413,
                'level': 5,
                'type_id': 23950,
                'start_ts': 1291645953,
                'end_sp': 2048000,
                'start_sp': 362039,
                'position': 0},
            {
                'end_sp': 256000,
                'end_ts': 1342871633,
                'level': 5,
                'position': 1,
                'start_sp': 45255,
                'start_ts': 1342621219,
                'type_id': 3437},
            ])

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/SkillQueue', params={'characterID': 1}),
            ])

    def test_messages(self):
        self.api.get.return_value = self.make_api_result("char/messages.xml")

        result, current, expires = self.char.messages()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, [
                {
                    'id': 290285276,
                    'sender_id': 999999999,
                    'timestamp': 1259629440,
                    'title': 'Corp mail',
                    'to': {
                        'org_id': 999999999,
                        'char_ids': None,
                        'list_ids': None,
                    },
                },
                {
                    'id': 290285275,
                    'sender_id': 999999999,
                    'timestamp': 1259629440,
                    'title': 'Personal mail',
                    'to': {
                        'org_id': None,
                        'char_ids': [999999999],
                        'list_ids': None,
                    },
                },
                {
                    'id': 290285274,
                    'sender_id': 999999999,
                    'timestamp': 1259629440,
                    'title': 'Message to mailing list',
                    'to': {
                        'org_id': None,
                        'char_ids': None,
                        'list_ids': [999999999],
                    },
                },
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/MailMessages', params={'characterID': 1}),
            ])

    def test_message_bodies(self):
        self.api.get.return_value = self.make_api_result("char/message_bodies.xml")

        result, current, expires = self.char.message_bodies([297023723,297023208,297023210,297023211])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
                297023208: '<p>Another message</p>',
                297023210: None,
                297023211: None,
                297023723: 'Hi.<br><br>This is a message.<br><br>',
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/MailBodies', params={
                    'characterID': 1,
                    'ids': [297023723,297023208,297023210,297023211],
                }),
            ])

    def test_mailing_lists(self):
        self.api.get.return_value = self.make_api_result("char/mailing_lists.xml")

        result, current, expires = self.char.mailing_lists()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
                128250439: "EVETycoonMail",
                128783669: "EveMarketScanner",
                141157801: "Exploration Wormholes",
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/MailingLists', params={'characterID': 1}),
            ])

    def test_calendar_events(self):
        self.api.get.return_value = self.make_api_result("char/calendar_events.xml")

        result, current, expires = self.char.calendar_events()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
                93264: {
                    'description': 'Join us for <a href="http://fanfest.eveonline.com/">     '
                                   'EVE Online\'s Fanfest 2011</a>!',
                    'duration': 0,
                    'id': 93264,
                    'important': False,
                    'owner': {
                        'id': 1,
                        'name': None,
                    },
                    'response': 'Undecided',
                    'start_ts': 1301130000,
                    'title': 'EVE Online Fanfest 2011',
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/UpcomingCalendarEvents', params={
                    'characterID': 1,
                }),
            ])

    def test_calendar_attendees(self):
        self.api.get.return_value = self.make_api_result("char/calendar_attendees.xml")

        result, current, expires = self.char.calendar_attendees([123, 234, 345])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
                123: {
                    123456789: {
                        'id': 123456789,
                        'name': 'Jane Doe',
                        'response': 'Accepted',
                    },
                    987654321: {
                        'id': 987654321,
                        'name': 'John Doe',
                        'response': 'Tentative',
                    },
                },
                234: {
                    192837645: {
                        'id': 192837645,
                        'name': 'Another Doe',
                        'response': 'Declined',
                    },
                    918273465: {
                        'id': 918273465,
                        'name': 'Doe the Third',
                        'response': 'Undecided',
                    },
                },
                345: {},
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/CalendarEventAttendees', params={
                    'characterID': 1,
                    'eventIDs': [123, 234, 345],
                }),
            ])

    @mock.patch('evelink.char.Char.calendar_attendees')
    def test_event_attendees(self, mock_calendar):
        mock_calendar.return_value = evelink_api.APIResult(
            {42: mock.sentinel.attendees}, 12345, 67890)
        result, current, expires = self.char.event_attendees(42)
        self.assertEqual(result, mock.sentinel.attendees)
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_faction_warfare_stats(self):
        self.api.get.return_value = self.make_api_result("char/faction_warfare_stats.xml")

        result, current, expires = self.char.faction_warfare_stats()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
                'enlist_ts': 1213135800,
                'faction': {'id': 500001, 'name': 'Caldari State'},
                'kills': {'total': 0, 'week': 0, 'yesterday': 0},
                'points': {'total': 0, 'week': 1044, 'yesterday': 0},
                'rank': {'current': 4, 'highest': 4},
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/FacWarStats', params={'characterID': 1}),
            ])

    def test_medals(self):
        self.api.get.return_value = self.make_api_result("char/medals.xml")

        result, current, expires = self.char.medals()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
                'current': {},
                'other': {
                    4106: {
                        'corp_id': 1711141370,
                        'description': 'For taking initiative and...',
                        'id': 4106,
                        'issuer_id': 132533870,
                        'public': False,
                        'reason': 'For continued support, loyalty...',
                        'title': 'Medal of Service'}}
            })

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/Medals', params={
                    'characterID': 1
                }),
            ])

    def test_contact_notifications(self):
        self.api.get.return_value = self.make_api_result("char/contact_notifications.xml")

        result, current, expires = self.char.contact_notifications()
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(result, {
                308734131: {
                    'data': {
                        'level': 10,
                        'message': 'Hi, I want to social network with you!',
                    },
                    'id': 308734131,
                    'sender': {
                        'id': 797400947,
                        'name': 'CCP Garthagk',
                    },
                    'timestamp': 1275174240,
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/ContactNotifications', params={'characterID': 1}),
            ])

    def test_locations(self):
        self.api.get.return_value = self.make_api_result("char/locations.xml")

        result, current, expires = self.char.locations((1009661446486, 1007448817800))
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('char/Locations', params={'characterID': 1, 'IDs': (1009661446486, 1007448817800),}),
            ])
        self.assertEqual(result,
            {1009661446486:
                {
                    'id': 1009661446486,
                    'x': None,
                    'z': None,
                    'name': "Superawesome test Impairor",
                    'y': None,
                },
            1007448817800:
                {
                    'id': 1007448817800,
                    'x': -170714848271.291,
                    'z': 208419106396.3,
                    'name': "A Whale",
                    'y': -1728060949.58229,
                }
            }
        )
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_corp
import mock

from tests.compat import unittest
from tests.utils import APITestCase

import evelink.api as evelink_api
import evelink.corp as evelink_corp


API_RESULT_SENTINEL = evelink_api.APIResult(mock.sentinel.api_result, 12345, 67890)


class CorpTestCase(APITestCase):

    def setUp(self):
        super(CorpTestCase, self).setUp()
        self.corp = evelink_corp.Corp(api=self.api)

    def test_corporation_sheet_public(self):
        self.api.get.return_value = self.make_api_result("corp/corporation_sheet.xml")

        result, current, expires = self.corp.corporation_sheet(123)

        self.assertEqual(result, {
                'alliance': {'id': 150430947, 'name': 'The Dead Rabbits'},
                'ceo': {'id': 150208955, 'name': 'Mark Roled'},
                'description': "Garth's testing corp of awesome sauce, win sauce as it were. In this\n"
                    "    corp...<br><br>IT HAPPENS ALL OVER",
                'hq': {'id': 60003469,
                       'name': 'Jita IV - Caldari Business Tribunal Information Center'},
                'id': 150212025,
                'logo': {'graphic_id': 0,
                         'shapes': [{'color': 681, 'id': 448},
                                    {'color': 676, 'id': 0},
                                    {'color': 0, 'id': 418}]},
                'members': {'current': 3},
                'name': 'Banana Republic',
                'shares': 1,
                'tax_percent': 93.7,
                'ticker': 'BR',
                'url': 'some url',
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/CorporationSheet', params={'corporationID': 123}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_corporation_sheet(self):
        self.api.get.return_value = self.make_api_result("corp/corporation_sheet.xml")

        result, current, expires = self.corp.corporation_sheet()

        self.assertEqual(result, {
                'alliance': {'id': 150430947, 'name': 'The Dead Rabbits'},
                'ceo': {'id': 150208955, 'name': 'Mark Roled'},
                'description': "Garth's testing corp of awesome sauce, win sauce as it were. In this\n"
                    "    corp...<br><br>IT HAPPENS ALL OVER",
                'hangars': {1000: 'Division 1',
                              1001: 'Division 2',
                              1002: 'Division 3',
                              1003: 'Division 4',
                              1004: 'Division 5',
                              1005: 'Division 6',
                              1006: 'Division 7'},
                'hq': {'id': 60003469,
                       'name': 'Jita IV - Caldari Business Tribunal Information Center'},
                'id': 150212025,
                'logo': {'graphic_id': 0,
                         'shapes': [{'color': 681, 'id': 448},
                                    {'color': 676, 'id': 0},
                                    {'color': 0, 'id': 418}]},
                'members': {'current': 3, 'limit': 6300},
                'name': 'Banana Republic',
                'shares': 1,
                'tax_percent': 93.7,
                'ticker': 'BR',
                'url': 'some url',
                'wallets': {1000: 'Wallet Division 1',
                                     1001: 'Wallet Division 2',
                                     1002: 'Wallet Division 3',
                                     1003: 'Wallet Division 4',
                                     1004: 'Wallet Division 5',
                                     1005: 'Wallet Division 6',
                                     1006: 'Wallet Division 7'}
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/CorporationSheet', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.corp.parse_industry_jobs')
    def test_industry_jobs(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.industry_jobs

        result, current, expires = self.corp.industry_jobs()

        self.assertEqual(result, mock.sentinel.industry_jobs)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/IndustryJobs', params={}),
            ])
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_npc_standings(self):
        self.api.get.return_value = self.make_api_result("corp/npc_standings.xml")

        result, current, expires = self.corp.npc_standings()

        self.assertEqual(result, {
                'agents': {
                    3008416: {
                        'id': 3008416,
                        'name': 'Antaken Kamola',
                        'standing': 2.71,
                    },
                },
                'corps': {
                    1000003: {
                        'id': 1000003,
                        'name': 'Prompt Delivery',
                        'standing': 0.97,
                    },
                },
                'factions': {
                    500019: {
                        'id': 500019,
                        'name': "Sansha's Nation",
                        'standing': -4.07,
                    },
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/Standings', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.corp.parse_kills')
    def test_kills(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.kills

        result, current, expires = self.corp.kills()

        self.assertEqual(result, mock.sentinel.kills)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/KillLog', params={}),
            ])
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.corp.parse_contract_bids')
    def test_contract_bids(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_contract_bids

        result, current, expires = self.corp.contract_bids()
        self.assertEqual(result, mock.sentinel.parsed_contract_bids)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/ContractBids', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.corp.parse_contract_items')
    def test_contract_items(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_contract_items

        result, current, expires = self.corp.contract_items(12345)
        self.assertEqual(result, mock.sentinel.parsed_contract_items)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/ContractItems', params={'contractID': 12345}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.corp.parse_contracts')
    def test_contracts(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_contracts

        result, current, expires = self.corp.contracts()
        self.assertEqual(result, mock.sentinel.parsed_contracts)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/Contracts', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.corp.parse_contact_list')
    def test_contacts(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_contacts

        result, current, expires = self.corp.contacts()
        self.assertEqual(result, mock.sentinel.parsed_contacts)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/ContactList', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_wallet_info(self):
        self.api.get.return_value = self.make_api_result("corp/wallet_info.xml")

        result, current, expires = self.corp.wallet_info()

        self.assertEqual(result, {
            1000: {'balance': 74171957.08, 'id': 4759, 'key': 1000},
            1001: {'balance': 6.05, 'id': 5687, 'key': 1001},
            1002: {'balance': 0.0, 'id': 5688, 'key': 1002},
            1003: {'balance': 17349111.0, 'id': 5689, 'key': 1003},
            1004: {'balance': 0.0, 'id': 5690, 'key': 1004},
            1005: {'balance': 0.0, 'id': 5691, 'key': 1005},
            1006: {'balance': 0.0, 'id': 5692, 'key': 1006},
        })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/AccountBalance', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.corp.parse_wallet_journal')
    def test_wallet_journal(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_journal

        result, current, expires = self.corp.wallet_journal()
        self.assertEqual(result, mock.sentinel.parsed_journal)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/WalletJournal', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_wallet_journal_paged(self):
        self.api.get.return_value = self.make_api_result("char/wallet_journal.xml")

        self.corp.wallet_journal(before_id=1234)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/WalletJournal', params={'fromID': 1234}),
            ])

    def test_wallet_journal_limit(self):
        self.api.get.return_value = self.make_api_result("char/wallet_journal.xml")

        self.corp.wallet_journal(limit=100)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/WalletJournal', params={'rowCount': 100}),
            ])

    def test_wallet_journal_account_key(self):
        self.api.get.return_value = self.make_api_result("char/wallet_journal.xml")

        self.corp.wallet_journal(account='0003')
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/WalletJournal', params={'accountKey': '0003'}),
            ])

    @mock.patch('evelink.corp.parse_wallet_transactions')
    def test_wallet_transcations(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_transactions

        result, current, expires = self.corp.wallet_transactions()
        self.assertEqual(result, mock.sentinel.parsed_transactions)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/WalletTransactions', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_wallet_transactions_paged(self):
        self.api.get.return_value = self.make_api_result("char/wallet_transactions.xml")

        self.corp.wallet_transactions(before_id=1234)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/WalletTransactions', params={'fromID': 1234}),
            ])

    def test_wallet_transactions_limit(self):
        self.api.get.return_value = self.make_api_result("char/wallet_transactions.xml")

        self.corp.wallet_transactions(limit=100)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/WalletTransactions', params={'rowCount': 100}),
            ])

    def test_wallet_transactions_account_key(self):
        self.api.get.return_value = self.make_api_result("char/wallet_transactions.xml")

        self.corp.wallet_transactions(account='0004')
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/WalletTransactions', params={'accountKey': '0004'}),
            ])

    @mock.patch('evelink.corp.parse_market_orders')
    def test_orders(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_orders

        result, current, expires = self.corp.orders()
        self.assertEqual(result, mock.sentinel.parsed_orders)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/MarketOrders', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_faction_warfare_stats(self):
        self.api.get.return_value = self.make_api_result('corp/faction_warfare_stats.xml')

        result, current, expires = self.corp.faction_warfare_stats()

        self.assertEqual(result, {
                'faction': {'id': 500001, 'name': 'Caldari State'},
                'kills': {'total': 0, 'week': 0, 'yesterday': 0},
                'pilots': 6,
                'points': {'total': 0, 'week': 1144, 'yesterday': 0},
                'start_ts': 1213135800,
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/FacWarStats', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    @mock.patch('evelink.corp.parse_assets')
    def test_assets(self, mock_parse):
        self.api.get.return_value = API_RESULT_SENTINEL
        mock_parse.return_value = mock.sentinel.parsed_assets

        result, current, expires = self.corp.assets()
        self.assertEqual(result, mock.sentinel.parsed_assets)
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_result),
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/AssetList', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_shareholders(self):
        self.api.get.return_value = self.make_api_result("corp/shareholders.xml")

        result, current, expires = self.corp.shareholders()

        self.assertEqual(result, {
                'char': {
                    126891489: {
                        'corp': {
                            'id': 632257314,
                            'name': 'Corax.',
                        },
                        'id': 126891489,
                        'name': 'Dragonaire',
                        'shares': 1,
                    },
                },
                'corp': {
                    126891482: {
                        'id': 126891482,
                        'name': 'DragonaireCorp',
                        'shares': 1,
                    },
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/Shareholders', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_titles(self):
        self.api.get.return_value = self.make_api_result("corp/titles.xml")

        result, current, expires = self.corp.titles()

        self.assertEqual(result, {
                1: {
                    'can_grant': {'at_base': {}, 'at_hq': {}, 'at_other': {}, 'global': {}},
                    'id': 1,
                    'name': 'Member',
                    'roles': {
                        'at_base': {},
                        'at_other': {},
                        'global': {},
                        'at_hq': {
                            8192: {
                                'description': 'Can take items from this divisions hangar',
                                'id': 8192,
                                'name': 'roleHangarCanTake1',
                            },
                        },
                    },
                },
                2: {
                    'can_grant': {'at_base': {}, 'at_hq': {}, 'at_other': {}, 'global': {}},
                    'id': 2,
                    'name': 'unused 1',
                    'roles': {'at_base': {}, 'at_hq': {}, 'at_other': {}, 'global': {}},
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/Titles', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_starbases(self):
        self.api.get.return_value = self.make_api_result("corp/starbases.xml")

        result, current, expires = self.corp.starbases()

        self.assertEqual(result, {
                100449451: {
                    'id': 100449451,
                    'location_id': 30000163,
                    'moon_id': 40010395,
                    'online_ts': 1244098851,
                    'standings_owner_id': 673381830,
                    'state': 'online',
                    'state_ts': 1323374621,
                    'type_id': 27538,
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/StarbaseList', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_starbase_details(self):
        self.api.get.return_value = self.make_api_result("corp/starbase_details.xml")

        result, current, expires = self.corp.starbase_details(123)

        self.assertEqual(result, {
                'combat': {
                    'hostility': {
                        'aggression': {'enabled': False},
                        'sec_status': {'enabled': False, 'threshold': 0.0},
                        'standing': {'enabled': True, 'threshold': 9.9},
                        'war': {'enabled': True},
                    },
                    'standings_owner_id': 154683985,
                },
                'fuel': {16274: 18758, 16275: 2447},
                'online_ts': 1240097429,
                'permissions': {
                    'deploy': {
                        'anchor': 'Starbase Config',
                        'offline': 'Starbase Config',
                        'online': 'Starbase Config',
                        'unanchor': 'Starbase Config',
                    },
                    'forcefield': {'alliance': True, 'corp': True},
                    'fuel': {
                        'take': 'Alliance Members',
                        'view': 'Starbase Config',
                    },
                },
                'state': 'online',
                'state_ts': 1241299896,
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/StarbaseDetail', params={'itemID': 123}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_members(self):
        self.api.get.return_value = self.make_api_result("corp/members.xml")

        result, current, expires = self.corp.members()

        self.assertEqual(result, {
                150336922: {
                    'base': {'id': 0, 'name': ''},
                    'can_grant': 0,
                    'id': 150336922,
                    'join_ts': 1181745540,
                    'location': {
                        'id': 60011566,
                        'name': 'Bourynes VII - Moon 2 - University of Caille School',
                    },
                    'logoff_ts': 1182029760,
                    'logon_ts': 1182028320,
                    'name': 'corpexport',
                    'roles': 0,
                    'ship_type': {'id': 606, 'name': 'Velator'},
                    'title': 'asdf',
                },
                150337897: {
                    'base': {'id': 0, 'name': ''},
                    'can_grant': 0,
                    'id': 150337897,
                    'join_ts': 1181826840,
                    'location': {
                        'id': 60011566,
                        'name': 'Bourynes VII - Moon 2 - University of Caille School',
                    },
                    'logoff_ts': 1182029700,
                    'logon_ts': 1182028440,
                    'name': 'corpslave',
                    'roles': 22517998271070336,
                    'ship_type': {'id': 670, 'name': 'Capsule'},
                    'title': '',
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/MemberTracking', params={'extended': 1}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_members_not_extended(self):
        self.api.get.return_value = self.make_api_result("corp/members.xml")
        result, current, expires = self.corp.members(extended=False)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/MemberTracking', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_permissions(self):
        self.api.get.return_value = self.make_api_result("corp/permissions.xml")

        result, current, expires = self.corp.permissions()

        self.assertEqual(result, {
                123456789: {
                    'can_grant': {
                        'at_base': {4: 'Bar'},
                        'at_hq': {},
                        'at_other': {},
                        'global': {},
                    },
                    'id': 123456789,
                    'name': 'Tester',
                    'roles': {
                        'at_base': {},
                        'at_hq': {},
                        'at_other': {},
                        'global': {1: 'Foo'},
                    },
                    'titles': {
                        1: 'Member ',
                        512: 'Gas Attendant',
                    },
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/MemberSecurity', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_permissions_log(self):
        self.api.get.return_value = self.make_api_result("corp/permissions_log.xml")

        result, current, expires = self.corp.permissions_log()

        self.assertEqual(result, [
                {
                    'timestamp': 1218131820,
                    'recipient': {'id': 1234567890, 'name': 'Tester'},
                    'roles': {
                        'after': {},
                        'before': {
                            8192: 'roleHangarCanTake1',
                            4398046511104: 'roleContainerCanTake1',
                        },
                    },
                    'role_type': 'at_other',
                    'issuer': {'id': 1234567890, 'name': 'Tester'},
                },
                {
                    'timestamp': 1218131820,
                    'recipient': {'id': 1234567890, 'name': 'Tester'},
                    'roles': {
                        'after': {},
                        'before': {
                            8192: 'roleHangarCanTake1',
                        },
                    },
                    'role_type': 'at_other',
                    'issuer': {'id': 1234567890, 'name': 'Tester'},
                },
                {
                    'timestamp': 1218131820,
                    'recipient': {'id': 1234567890, 'name': 'Tester'},
                    'roles': {
                        'after': {
                            16777216: 'roleHangarCanQuery5',
                        },
                        'before': {},
                    },
                    'role_type': 'at_other',
                    'issuer': {'id': 1234567890, 'name': 'Tester'},
                },
                {
                    'timestamp': 1215452820,
                    'recipient': {'id': 1234567890, 'name': 'Tester'},
                    'roles': {
                        'after': {},
                        'before': {
                            2199023255552: 'roleEquipmentConfig',
                            4503599627370496: 'roleJuniorAccountant',
                        },
                    },
                    'role_type': 'at_other',
                    'issuer': {'id': 1234567890, 'name': 'Tester'},
                },
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/MemberSecurityLog', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_stations(self):
        self.api.get.return_value = self.make_api_result("corp/stations.xml")

        result, current, expires = self.corp.stations()

        self.assertEqual(result, {
                61000368: {
                    'docking_fee_per_volume': 0.0,
                    'id': 61000368,
                    'name': 'Station Name Goes Here',
                    'office_fee': 25000000,
                    'owner_id': 857174087,
                    'reprocessing': {'cut': 0.025, 'efficiency': 0.5},
                    'standing_owner_id': 673381830,
                    'system_id': 30004181,
                    'type_id': 21645,
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/OutpostList', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_station_services(self):
        self.api.get.return_value = self.make_api_result("corp/station_services.xml")

        result, current, expires = self.corp.station_services(123)

        self.assertEqual(result, {
                'Market': {
                    'name': 'Market',
                    'owner_id': 857174087,
                    'standing': {
                        'bad_surcharge': 10.0,
                        'good_discount': 0.0,
                        'minimum': 10.0,
                    },
                },
                'Repair Facilities': {
                    'name': 'Repair Facilities',
                    'owner_id': 857174087,
                    'standing': {
                        'bad_surcharge': 10.0,
                        'good_discount': 10.0,
                        'minimum': 10.0,
                    },
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/OutpostServiceDetail', params={'itemID': 123}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_medals(self):
        self.api.get.return_value = self.make_api_result("corp/medals.xml")

        result, current, expires = self.corp.medals()

        self.assertEqual(result, {
                1: {
                    'create_ts': 1345740633,
                    'creator_id': 2,
                    'description': 'A test medal.',
                    'id': 1,
                    'title': 'Test Medal',
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/Medals', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_member_medals(self):
        self.api.get.return_value = self.make_api_result("corp/member_medals.xml")

        result, current, expires = self.corp.member_medals()

        self.assertEqual(result, {
                1302462525: {
                    24216: {
                        'char_id': 1302462525,
                        'issuer_id': 1824523597,
                        'medal_id': 24216,
                        'public': True,
                        'reason': 'Its True',
                        'timestamp': 1241319835,
                    },
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/MemberMedals', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_container_log(self):
        self.api.get.return_value = self.make_api_result("corp/container_log.xml")

        result, current, expires = self.corp.container_log()

        self.assertEqual(result, [
                {'action': 'Set Name',
                 'actor': {'id': 783037732, 'name': 'Halo Glory'},
                 'details': {'config': {'new': None, 'old': None},
                             'flag': 4,
                             'password_type': None,
                             'quantity': None,
                             'type_id': None},
                 'item': {'id': 2051471251, 'type_id': 17366},
                 'location_id': 60011728,
                 'timestamp': 1229847000},
                {'action': 'Set Password',
                 'actor': {'id': 783037732, 'name': 'Halo Glory'},
                 'details': {'config': {'new': None, 'old': None},
                             'flag': 4,
                             'password_type': 'Config',
                             'quantity': None,
                             'type_id': None},
                 'item': {'id': 2051471251, 'type_id': 17366},
                 'location_id': 60011728,
                 'timestamp': 1229846940},
                {'action': 'Configure',
                 'actor': {'id': 783037732, 'name': 'Halo Glory'},
                 'details': {'config': {'new': 0, 'old': 0},
                             'flag': 4,
                             'password_type': None,
                             'quantity': None,
                             'type_id': None},
                 'item': {'id': 2051471251, 'type_id': 17366},
                 'location_id': 60011728,
                 'timestamp': 1229846940},
                {'action': 'Assemble',
                 'actor': {'id': 783037732, 'name': 'Halo Glory'},
                 'details': {'config': {'new': None, 'old': None},
                             'flag': 4,
                             'password_type': None,
                             'quantity': None,
                             'type_id': None},
                 'item': {'id': 2051471251, 'type_id': 17366},
                 'location_id': 60011728,
                 'timestamp': 1229846880}
            ])
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/ContainerLog', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_locations(self):
        self.api.get.return_value = self.make_api_result("corp/locations.xml")

        result, current, expires = self.corp.locations((1009661446486,1007448817800))
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('corp/Locations', params={'IDs': (1009661446486,1007448817800),}),
            ])
        self.assertEqual(result,
            {1009661446486:
                {
                    'id': 1009661446486,
                    'x': None,
                    'z': None,
                    'name': "Superawesome test Impairor",
                    'y': None,
                },
            1007448817800:
                {
                    'id': 1007448817800,
                    'x': -170714848271.291,
                    'z': 208419106396.3,
                    'name': "A Whale",
                    'y': -1728060949.58229,
                }
            }
        )
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_eve
import mock

from tests.compat import unittest
from tests.utils import APITestCase

import evelink.eve as evelink_eve

class EVETestCase(APITestCase):

    def setUp(self):
        super(EVETestCase, self).setUp()
        self.eve = evelink_eve.EVE(api=self.api)

    def test_certificate_tree(self):
        self.api.get.return_value = self.make_api_result("eve/certificate_tree.xml")

        result, current, expires = self.eve.certificate_tree()

        self.assertEqual(result, {
            'Core': {
                'classes': {
                    'Core Fitting': {
                        'certificates': {
                            5: {'corp_id': 1000125,
                                'description': 'This certificate represents a basic...',
                                'grade': 1,
                                'id': 5,
                                'required_certs': {},
                                'required_skills': {3413: 3, 3424: 2, 3426: 3, 3432: 1,}},
                            6: {'corp_id': 1000125,
                                'description': 'This certificate represents a standard...',
                                'grade': 2,
                                'id': 6,
                                'required_certs': {5: 1},
                                'required_skills': {3318: 4, 3413: 5, 3418: 4, 3426: 5, 3432: 4}},
                            292: {'corp_id': 1000125,
                                'description': 'This certificate represents an elite...',
                                'grade': 5,
                                'id': 292,
                                'required_certs': {291: 1},
                                'required_skills': {18580: 5, 16594: 5, 16597: 5, 16595: 5}}},
                        'id': 2,
                        'name': 'Core Fitting'}},
                'id': 3,
                'name': 'Core'}})
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/CertificateTree', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_character_names_from_ids(self):
        self.api.get.return_value = self.make_api_result("eve/character_name.xml")

        result, current, expires = self.eve.character_names_from_ids(set([1,2]))

        self.assertEqual(result, {1:"EVE System", 2:"EVE Central Bank"})
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/CharacterName', params={'IDs': set([1,2])}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_character_name_from_id(self):
        self.api.get.return_value = self.make_api_result("eve/character_name_single.xml")

        result, current, expires = self.eve.character_name_from_id(1)

        self.assertEqual(result, "EVE System")
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/CharacterName', params={'IDs': [1]}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_character_ids_from_names(self):
        self.api.get.return_value = self.make_api_result("eve/character_id.xml")

        result, current, expires = self.eve.character_ids_from_names(set(["EVE System", "EVE Central Bank"]))
        self.assertEqual(result, {"EVE System":1, "EVE Central Bank":2})
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/CharacterID', params={'names': set(["EVE System","EVE Central Bank"])}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_character_id_from_name(self):
        self.api.get.return_value = self.make_api_result("eve/character_id_single.xml")

        result, current, expires = self.eve.character_id_from_name("EVE System")
        self.assertEqual(result, 1)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/CharacterID', params={'names': ["EVE System"]}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_affiliations_for_characters(self):
        self.api.get.return_value = self.make_api_result("eve/character_affiliation.xml")

        result, current, expires = self.eve.affiliations_for_characters(set([92168909, 401111892, 1979087900]))
        self.assertEqual(result, {
            1979087900: {
                'id': 1979087900,
                'name': 'Marcel Devereux',
                'faction': {
                    'id': 500004,
                    'name': 'Gallente Federation'
                },
                'corp': {
                    'id': 1894214152,
                    'name': 'Aideron Robotics'
                }
            },
            401111892: {
                'id': 401111892,
                'name': 'ShadowMaster',
                'alliance': {
                    'id': 99000652,
                    'name': 'RvB - BLUE Republic'
                },
                'corp': {
                    'id': 1741770561,
                    'name': 'Blue Republic'
                }
            },
            92168909: {
                'id': 92168909,
                'name': 'CCP FoxFour',
                'alliance': {
                    'id': 434243723,
                    'name': 'C C P Alliance'
                },
                'corp': {
                    'id': 109299958,
                    'name': 'C C P'
                }
            }
        })

        self.assertEqual(self.api.mock_calls, [
            mock.call.get('eve/CharacterAffiliation', params={'ids': set([92168909, 401111892, 1979087900])})
        ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_affiliations_for_character(self):
        self.api.get.return_value = self.make_api_result("eve/character_affiliation_single.xml")

        result, current, expires = self.eve.affiliations_for_character(92168909)
        self.assertEqual(result, {
            'id': 92168909,
            'name': 'CCP FoxFour',
            'alliance': {
                'id': 434243723,
                'name': 'C C P Alliance'
            },
            'corp': {
                'id': 109299958,
                'name': 'C C P'
            }
        })

        self.assertEqual(self.api.mock_calls, [
            mock.call.get('eve/CharacterAffiliation', params={'ids': [92168909]})
        ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_character_info_from_id(self):
        self.api.get.return_value = self.make_api_result("eve/character_info.xml")

        result, current, expires = self.eve.character_info_from_id(1234)
        self.assertEqual(result, {
            'alliance': {'id': None, 'name': None, 'timestamp': None},
            'bloodline': 'Civire',
            'corp': {'id': 2345, 'name': 'Test Corporation', 'timestamp': 1338689400},
            'history': [
                {'corp_id': 1, 'start_ts': 1338603000},
                {'corp_id': 2, 'start_ts': 1318422896}
            ],
            'id': 1234,
            'isk': None,
            'location': None,
            'name': 'Test Character',
            'race': 'Caldari',
            'sec_status': 2.5,
            'ship': {'name': None, 'type_id': None, 'type_name': None},
            'skillpoints': None,
        })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/CharacterInfo', params={'characterID': 1234}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_alliances(self):
        self.api.get.return_value = self.make_api_result("eve/alliances.xml")

        result, current, expires = self.eve.alliances()
        self.assertEqual(result, {
                1: {
                    'executor_id': 2,
                    'id': 1,
                    'member_corps': {
                        2: {'id': 2, 'timestamp': 1289250660},
                        3: {'id': 3, 'timestamp': 1327728960},
                        4: {'id': 4, 'timestamp': 1292440500},
                    },
                    'member_count': 123,
                    'name': 'Test Alliance',
                    'ticker': 'TEST',
                    'timestamp': 1272717240,
                }
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/AllianceList', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_errors(self):
        self.api.get.return_value = self.make_api_result("eve/errors.xml")

        result, current, expires = self.eve.errors()
        self.assertEqual(result, {1:"Foo", 2:"Bar"})
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/ErrorList', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_faction_warfare_stats(self):
        self.api.get.return_value = self.make_api_result("eve/faction_warfare_stats.xml")

        result, current, expires = self.eve.faction_warfare_stats()
        self.assertEqual(result, {
            'kills': {'total': 232772, 'week': 3246, 'yesterday': 677},
            'points': {'total': 44045189, 'week': 414049, 'yesterday': 55087},
            'factions': {
                500001: {
                    'id': 500001,
                    'kills': {'total': 59239, 'week': 627, 'yesterday': 115},
                    'name': 'Caldari State',
                    'pilots': 5324,
                    'points': {'total': 4506493, 'week': 64548, 'yesterday': 9934},
                    'systems': 61,
                },
                500002: {
                    'id': 500002,
                    'kills': {'total': 56736, 'week': 952, 'yesterday': 213},
                    'name': 'Minmatar Republic',
                    'pilots': 4068,
                    'points': {'total': 3627522, 'week': 51211, 'yesterday': 2925},
                    'systems': 0,
                },
                500003: {
                    'id': 500003,
                    'kills': {'total': 55717, 'week': 1000, 'yesterday': 225},
                    'name': 'Amarr Empire',
                    'pilots': 3960,
                    'points': {'total': 3670190, 'week': 50518, 'yesterday': 3330},
                    'systems': 11,
                },
                500004: {
                    'id': 500004,
                    'kills': {'total': 61080, 'week': 667, 'yesterday': 124},
                    'name': 'Gallente Federation',
                    'pilots': 3663,
                    'points': {'total': 4098366, 'week': 62118, 'yesterday': 10343},
                    'systems': 0,
                },
            },
            'wars': [
                    {
                        'against': {'id': 500002, 'name': 'Minmatar Republic'},
                        'faction': {'id': 500001, 'name': 'Caldari State'},
                    },
                    {
                        'against': {'id': 500004, 'name': 'Gallente Federation'},
                        'faction': {'id': 500001, 'name': 'Caldari State'},
                    },
                    {
                        'against': {'id': 500001, 'name': 'Caldari State'},
                        'faction': {'id': 500002, 'name': 'Minmatar Republic'},
                    },
                    {
                        'against': {'id': 500003, 'name': 'Amarr Empire'},
                        'faction': {'id': 500002, 'name': 'Minmatar Republic'},
                    },
                    {
                        'against': {'id': 500002, 'name': 'Minmatar Republic'},
                        'faction': {'id': 500003, 'name': 'Amarr Empire'},
                    },
                    {
                        'against': {'id': 500004, 'name': 'Gallente Federation'},
                        'faction': {'id': 500003, 'name': 'Amarr Empire'},
                    },
                    {
                        'against': {'id': 500001, 'name': 'Caldari State'},
                        'faction': {'id': 500004, 'name': 'Gallente Federation'},
                    },
                    {
                        'against': {'id': 500003, 'name': 'Amarr Empire'},
                        'faction': {'id': 500004, 'name': 'Gallente Federation'},
                    }
                ],
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/FacWarStats', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_faction_warfare_leaderboard(self):
        self.api.get.return_value = self.make_api_result("eve/faction_warfare_leaderboard.xml")

        result, current, expires = self.eve.faction_warfare_leaderboard()
        self.assertEqual(result, {
                'char': {
                    'kills': {
                        'total': [{'id': 673662188, 'kills': 451, 'name': 'Val Erian'}],
                        'week': [{'id': 187452523,  'kills': 52, 'name': 'Tigrana Blanque'}],
                        'yesterday': [
                            {'id': 1007512845, 'kills': 14, 'name': 'StonedBoy'},
                            {'id': 646053002, 'kills': 11, 'name': 'Erick Voliffe'},
                        ],
                    },
                    'points': {
                        'total': [{'id': 395923478, 'name': 'sasawong', 'points': 197046}],
                         'week': [{'id': 161929388, 'name': 'Ankhesentapemkah', 'points': 20851}],
                         'yesterday': [{'id': 774720050, 'name': 'v3nd3tt4', 'points': 3151}],
                    },
                },
                'corp': {
                    'kills': {
                        'total': [{'id': 673662188, 'kills': 451, 'name': 'Val Erian'}],
                        'week': [{'id': 187452523,  'kills': 52, 'name': 'Tigrana Blanque'}],
                        'yesterday': [
                            {'id': 1007512845, 'kills': 14, 'name': 'StonedBoy'},
                            {'id': 646053002, 'kills': 11, 'name': 'Erick Voliffe'},
                        ],
                    },
                    'points': {
                        'total': [{'id': 395923478, 'name': 'sasawong', 'points': 197046}],
                         'week': [{'id': 161929388, 'name': 'Ankhesentapemkah', 'points': 20851}],
                         'yesterday': [{'id': 774720050, 'name': 'v3nd3tt4', 'points': 3151}],
                    },
                },
                'faction': {
                    'kills': {
                        'total': [{'id': 500004, 'kills': 104, 'name': 'Gallente Federation'}],
                        'week': [{'id': 500004, 'kills': 105, 'name': 'Gallente Federation'}],
                        'yesterday': [{'id': 500004, 'kills': 106, 'name': 'Gallente Federation'}],
                    },
                    'points': {
                        'total': [{'id': 500004, 'points': 101, 'name': 'Gallente Federation'}],
                        'week': [{'id': 500004, 'points': 102, 'name': 'Gallente Federation'}],
                        'yesterday': [{'id': 500004, 'points': 103, 'name': 'Gallente Federation'}],
                    },
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/FacWarTopStats', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_conquerable_stations(self):
        self.api.get.return_value = self.make_api_result("eve/conquerable_stations.xml")

        result, current, expires = self.eve.conquerable_stations()
        self.assertEqual(result, {
            1:{ 'id':1,
                'name':"Station station station",
                'type_id':123,
                'system_id':512,
                'corp':{
                        'id':444,
                        'name':"Valkyries of Night" }
                },
            2:{ 'id':2,
                'name':"Station the station",
                'type_id':42,
                'system_id':503,
                'corp':{
                        'id':400,
                        'name':"Deus Fides Empire"}
                }
           })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/ConquerableStationlist', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_skill_tree(self):
        self.api.get.return_value = self.make_api_result("eve/skill_tree.xml")

        result, current, expires = self.eve.skill_tree()

        self.assertEqual(result, {
                255: {
                    'id': 255,
                    'name': 'Gunnery',
                    'skills': {
                        3300: {
                            'attributes': {
                                'primary': 'perception',
                                 'secondary': 'willpower',
                            },
                            'bonuses': {
                                'turretSpeeBonus': {
                                    'type': 'turretSpeeBonus',
                                    'value': -2.0,
                                },
                            },
                            'description': "Basic turret operation skill. 2% Bonus to weapon turrets' rate of fire per skill level.",
                            'group_id': 255,
                            'id': 3300,
                            'name': 'Gunnery',
                            'published': True,
                            'rank': 1,
                            'required_skills': {},
                        },
                        3301: {
                            'attributes': {
                                'primary': 'perception',
                                'secondary': 'willpower',
                            },
                            'bonuses': {
                                'damageMultiplierBonus': {
                                    'type': 'damageMultiplierBonus',
                                    'value': 5.0,
                                },
                            },
                            'description': 'Operation of small hybrid turrets. 5% Bonus to small hybrid turret damage per level.',
                            'group_id': 255,
                            'id': 3301,
                            'name': 'Small Hybrid Turret',
                            'published': True,
                            'rank': 1,
                            'required_skills': {
                                3300: {
                                    'id': 3300,
                                    'level': 1,
                                    'name': 'Gunnery',
                                },
                            },
                        },
                    },
                },
                266: {
                    'id': 266,
                    'name': 'Corporation Management',
                    'skills': {
                        11584 : {
                            'id': 11584,
                            'group_id': 266,
                            'name': 'Anchoring',
                            'description': 'Skill at Anchoring Deployables. Can not be trained on Trial Accounts.',
                            'published': True,
                            'rank': 3,
                            'attributes': {
                                'primary': 'memory',
                                'secondary': 'charisma',
                                },
                            'required_skills': {},
                            'bonuses': {
                                'canNotBeTrainedOnTrial': {
                                    'type': 'canNotBeTrainedOnTrial',
                                    'value': 1.0,
                                    }
                                }
                            },
                        3369 : {
                            'id': 3369,
                            'group_id': 266,
                            'name': 'CFO Training',
                            'description': 'Skill at managing corp finances. 5% discount on all fees at non-hostile NPC station if acting as CFO of a corp. ',
                            'published': False,
                            'rank': 3,
                            'attributes': {
                                'primary': 'memory',
                                'secondary': 'charisma',
                                },
                            'required_skills': {
                                3363 : { 'id' : 3363, 'level' : 2, 'name' : None },
                                3444 : { 'id' : 3444, 'level' : 3, 'name' : None },
                                },
                            'bonuses': {}
                            }
                        }
                    }
                })
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/SkillTree', params={})
                ])


    def test_reference_types(self):
        self.api.get.return_value = self.make_api_result("eve/reference_types.xml")

        result, current, expires = self.eve.reference_types()

        self.assertEqual(result, {
                0: 'Undefined',
                1: 'Player Trading',
                2: 'Market Transaction',
                3: 'GM Cash Transfer',
                4: 'ATM Withdraw',
                5: 'ATM Deposit'
                })
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

        self.assertEqual(self.api.mock_calls, [
                mock.call.get('eve/RefTypes', params={})
                ])


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_map
import mock

from tests.compat import unittest
from tests.utils import APITestCase

from evelink import map as evelink_map

class MapTestCase(APITestCase):

    def setUp(self):
        super(MapTestCase, self).setUp()
        self.map = evelink_map.Map(api=self.api)

    def test_jumps_by_system(self):
        self.api.get.return_value = self.make_api_result("map/jumps_by_system.xml")

        (result, data_time), current, expires = self.map.jumps_by_system()

        self.assertEqual(result, {30001984:10})
        self.assertEqual(data_time, 1197460238)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('map/Jumps', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_kills_by_system(self):
        self.api.get.return_value = self.make_api_result("map/kills_by_system.xml")

        (result, data_time), current, expires = self.map.kills_by_system()

        self.assertEqual(result, {
                30001343: {'id':30001343, 'faction':17, 'ship':0, 'pod':0},
                30002671: {'id':30002671, 'faction':34, 'ship':1, 'pod':0},
                30005327: {'id':30005327, 'faction':21, 'ship':5, 'pod':1},
            })
        self.assertEqual(data_time, 1197802673)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('map/Kills', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_faction_warfare_systems(self):
        self.api.get.return_value = self.make_api_result("map/faction_warfare_systems.xml")

        result, current, expires = self.map.faction_warfare_systems()

        self.assertEqual(result, {
                30002056: {
                    'contested': True,
                    'faction': {'id': None, 'name': None},
                    'id': 30002056,
                    'name': 'Resbroko',
                },
                30002057: {
                    'contested': False,
                    'faction': {'id': None, 'name': None},
                    'id': 30002057,
                    'name': 'Hadozeko',
                },
                30003068: {
                    'contested': False,
                    'faction': {'id': 500002, 'name': 'Minmatar Republic'},
                    'id': 30003068,
                    'name': 'Kourmonen',
                },
            })
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('map/FacWarSystems', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)

    def test_sov_by_system(self):
        self.api.get.return_value = self.make_api_result("map/sov_by_system.xml")

        (result, data_time), current, expires = self.map.sov_by_system()

        self.assertEqual(result, {
                30000480: {
                    'alliance_id': 824518128,
                    'corp_id': 123456789,
                    'faction_id': None,
                    'id': 30000480,
                    'name': '0-G8NO',
                },
                30001597: {
                    'alliance_id': 1028876240,
                    'corp_id': 421957727,
                    'faction_id': None,
                    'id': 30001597,
                    'name': 'M-NP5O',
                },
                30023410: {
                    'alliance_id': None,
                    'corp_id': None,
                    'faction_id': 500002,
                    'id': 30023410,
                    'name': 'Embod',
                },
            })
        self.assertEqual(data_time, 1261545398)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('map/Sovereignty', params={}),
            ])
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_requests_api
import mock

from tests.compat import unittest

from evelink.thirdparty.six.moves.urllib.parse import parse_qs
import evelink.api as evelink_api


class DummyResponse(object):
    def __init__(self, content):
        self.content = content


@unittest.skipIf(not evelink_api._has_requests, '`requests` not available')
class RequestsAPITestCase(unittest.TestCase):

    def setUp(self):
        self.cache = mock.MagicMock(spec=evelink_api.APICache)
        self.api = evelink_api.API(cache=self.cache)

        self.test_xml = r"""
                <?xml version='1.0' encoding='UTF-8'?>
                <eveapi version="2">
                    <currentTime>2009-10-18 17:05:31</currentTime>
                    <result>
                        <rowset>
                            <row foo="bar" />
                            <row foo="baz" />
                        </rowset>
                    </result>
                    <cachedUntil>2009-11-18 17:05:31</cachedUntil>
                </eveapi>
            """.strip()

        self.error_xml = r"""
                <?xml version='1.0' encoding='UTF-8'?>
                <eveapi version="2">
                    <currentTime>2009-10-18 17:05:31</currentTime>
                    <error code="123">
                        Test error message.
                    </error>
                    <cachedUntil>2009-11-18 19:05:31</cachedUntil>
                </eveapi>
            """.strip()

        requests_patcher = mock.patch('requests.Session')
        requests_patcher.start()
        import requests
        self.mock_sessions = requests.Session()
        self.requests_patcher = requests_patcher

    def tearDown(self):
        self.requests_patcher.stop()

    def test_get(self):
        # mock up a sessions compatible response object and pretend to have
        # nothing chached; similar pattern below for all test_get_* methods
        self.mock_sessions.post.return_value = DummyResponse(self.test_xml)
        self.cache.get.return_value = None

        tree, current, expires = self.api.get('foo/Bar', {'a':[1,2,3]})

        rowset = tree.find('rowset')
        rows = rowset.findall('row')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].attrib['foo'], 'bar')
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258563931,
        })
        self.assertEqual(current, 1255885531)
        self.assertEqual(expires, 1258563931)

    def test_cached_get(self):
        """Make sure that we don't try to call the API if the result is cached."""
        # mock up a sessions compatible error response, and pretend to have a
        # good test response cached.
        self.mock_sessions.post.return_value = DummyResponse(self.error_xml)
        self.cache.get.return_value = self.test_xml

        result, current, expires = self.api.get('foo/Bar', {'a':[1,2,3]})

        rowset = result.find('rowset')
        rows = rowset.findall('row')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].attrib['foo'], 'bar')

        self.assertFalse(self.mock_sessions.post.called)
        # timestamp attempted to be extracted.
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258563931,
        })
        self.assertEqual(current, 1255885531)
        self.assertEqual(expires, 1258563931)

    def test_get_with_apikey(self):
        self.mock_sessions.post.return_value = DummyResponse(self.test_xml)
        self.cache.get.return_value = None

        api_key = (1, 'code')
        api = evelink_api.API(cache=self.cache, api_key=api_key)

        api.get('foo', {'a':[2,3,4]})

        # Make sure the api key id and verification code were passed
        call_args, call_kwargs = self.mock_sessions.post.mock_calls[0][1:3]
        called_url = call_args[0]
        called_param_dict = parse_qs(call_kwargs["params"])

        expected_url = 'https://api.eveonline.com/foo.xml.aspx'
        expected_param_dict = parse_qs('a=2%2C3%2C4&vCode=code&keyID=1')

        self.assertEqual(called_url, expected_url)
        self.assertEqual(called_param_dict, expected_param_dict)

    def test_get_with_error(self):
        self.mock_sessions.get.return_value = DummyResponse(self.error_xml)
        self.cache.get.return_value = None

        self.assertRaises(evelink_api.APIError,
            self.api.get, 'eve/Error')
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258571131,
        })

    def test_cached_get_with_error(self):
        """Make sure that we don't try to call the API if the result is cached."""
        # mocked response is good now, with the error response cached.
        self.mock_sessions.post.return_value = DummyResponse(self.test_xml)
        self.cache.get.return_value = self.error_xml
        self.assertRaises(evelink_api.APIError,
            self.api.get, 'foo/Bar', {'a':[1,2,3]})

        self.assertFalse(self.mock_sessions.post.called)
        self.assertEqual(self.api.last_timestamps, {
            'current_time': 1255885531,
            'cached_until': 1258571131,
        })


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_server
import mock

from tests.compat import unittest
from tests.utils import APITestCase

import evelink.server as evelink_server

class ServerTestCase(APITestCase):

    def setUp(self):
        super(ServerTestCase, self).setUp()
        self.server = evelink_server.Server(api=self.api)

    def test_server_status(self):
        self.api.get.return_value = self.make_api_result("server/server_status.xml")

        result, current, expires = self.server.server_status()

        self.assertEqual(result, {'online':True, 'players':38102})
        self.assertEqual(current, 12345)
        self.assertEqual(expires, 67890)
        self.assertEqual(self.api.mock_calls, [
                mock.call.get('server/ServerStatus', params={}),
            ])

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_eve_central
import datetime
import os
from xml.etree import ElementTree
import mock

from tests.compat import unittest

import evelink.thirdparty.eve_central as evelink_evec

class EVECentralTestCase(unittest.TestCase):

    @mock.patch('evelink.thirdparty.eve_central.EVECentral._parse_item_orders')
    def test_item_orders(self, mock_parse):
        url_fetch = mock.MagicMock()
        url_fetch.return_value = mock.sentinel.api_response
        mock_parse.return_value = mock.sentinel.parsed_results

        evec = evelink_evec.EVECentral(url_fetch_func=url_fetch)

        results = evec.item_orders(1877)

        self.assertEqual(results, mock.sentinel.parsed_results)
        self.assertEqual(url_fetch.mock_calls, [
                mock.call('%s/quicklook?typeid=1877&sethours=360' % evec.api_base),
            ])
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_response),
            ])

    @mock.patch('evelink.thirdparty.eve_central.EVECentral._parse_item_orders')
    def test_item_orders_on_route(self, mock_parse):
        url_fetch = mock.MagicMock()
        url_fetch.return_value = mock.sentinel.api_response
        mock_parse.return_value = mock.sentinel.parsed_results

        evec = evelink_evec.EVECentral(url_fetch_func=url_fetch)

        results = evec.item_orders_on_route(1877, 'Jita', 'Amarr')

        self.assertEqual(results, mock.sentinel.parsed_results)
        self.assertEqual(url_fetch.mock_calls, [
                mock.call('%s/quicklook/onpath/from/Jita/to/Amarr/fortype/1877?sethours=360'
                    % evec.api_base),
            ])
        self.assertEqual(mock_parse.mock_calls, [
                mock.call(mock.sentinel.api_response),
            ])

    def test_parse_item_orders(self):
        xml_file = os.path.join(os.path.dirname(__file__), '..',
            'xml', 'thirdparty', 'eve_central', 'item_orders.xml')
        url_fetch = mock.MagicMock()
        with open(xml_file) as f:
            response = f.read()

        evec = evelink_evec.EVECentral(url_fetch_func=url_fetch)

        results = evec._parse_item_orders(response)

        this_year = datetime.datetime.now().year
        reported = datetime.datetime(this_year, 9, 6, 22, 6, 36)
        if reported > datetime.datetime.now():
            reported = reported.replace(year=this_year - 1)

        self.assertEqual(results, {
                'hours': 360,
                'id': 1877,
                'name': 'Rapid Light Missile Launcher II',
                'orders': {
                    'buy': {
                        2534467564: {
                            'expires': datetime.date(2012, 9, 14),
                            'id': 2534467564,
                            'price': 559000.0,
                            'range': 32767,
                            'region_id': 10000012,
                            'reported': reported,
                            'security': -0.0417728879761037,
                            'station': {
                                'id': 60012904,
                                'name': 'Litom XI - Moon 2 - Guardian Angels Assembly Plant',
                            },
                            'volume': {'minimum': 1, 'remaining': 12},
                        }
                    },
                    'sell': {
                        2534467565: {
                            'expires': datetime.date(2012, 9, 14),
                            'id': 2534467565,
                            'price': 559000.0,
                            'range': 32767,
                            'region_id': 10000012,
                            'reported': reported,
                            'security': -0.0417728879761037,
                            'station': {
                                'id': 60012904,
                                'name': 'Litom XI - Moon 2 - Guardian Angels Assembly Plant',
                            },
                            'volume': {'minimum': 1, 'remaining': 12},
                        },
                    },
                },
                'quantity_min': 1,
                'regions': ['Curse'],
            })

    def test_market_stats(self):
        xml_file = os.path.join(os.path.dirname(__file__), '..',
            'xml', 'thirdparty', 'eve_central', 'market_stats.xml')
        url_fetch = mock.MagicMock()
        with open(xml_file) as f:
            url_fetch.return_value = f.read()

        evec = evelink_evec.EVECentral(url_fetch_func=url_fetch)

        results = evec.market_stats([34])

        self.assertEqual(results, {
                34: {
                    'id': 34,
                    'all': {
                        'avg': 6.56,
                        'max': 14.0,
                        'median': 6.14,
                        'min': 0.18,
                        'percentile': 4.18,
                        'stddev': 1.41,
                        'volume': 46077525904,
                    },
                    'buy': {
                        'avg': 5.78,
                        'max': 6.14,
                        'median': 6.0,
                        'min': 2.46,
                        'percentile': 6.14,
                        'stddev': 0.99,
                        'volume': 22770318895,
                    },
                    'sell': {
                        'avg': 7.43,
                        'max': 20.0,
                        'median': 6.64,
                        'min': 5.79,
                        'percentile': 6.15,
                        'stddev': 1.69,
                        'volume': 22944882136,
                    },
                },
            })
        self.assertEqual(url_fetch.mock_calls, [
                mock.call('%s/marketstat?typeid=34&hours=24' % evec.api_base),
            ])

    @mock.patch('evelink.thirdparty.eve_central.EVECentral.market_stats')
    def test_item_market_stats(self, mock_stats):
        mock_stats.return_value = {123:mock.sentinel.stats_retval}
        mock_fetch = mock.MagicMock()

        evec = evelink_evec.EVECentral(url_fetch_func=mock_fetch)

        result = evec.item_market_stats(123)

        self.assertEqual(result, mock.sentinel.stats_retval)
        self.assertEqual(mock_fetch.mock_calls, [])
        self.assertEqual(mock_stats.mock_calls, [
                mock.call([123]),
            ])

    def test_route(self):
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = """
                [{"fromid":1,"from":"Test","toid":2,"to":"Testing","secchange":false}]
            """.strip()

        evec = evelink_evec.EVECentral(url_fetch_func=mock_fetch)

        results = evec.route('Test', 2)

        self.assertEqual(results, [
                {
                    'from': {'id': 1, 'name': 'Test'},
                    'to': {'id': 2, 'name': 'Testing'},
                    'security_change': False,
                },
            ])
        self.assertEqual(mock_fetch.mock_calls, [
                mock.call('%s/route/from/Test/to/2' % evec.api_base),
            ])



# vim: set et ts=4 sts=4 sw=4:

########NEW FILE########
__FILENAME__ = test_eve_who
import mock

from tests.compat import unittest

from evelink.thirdparty.six.moves.urllib.parse import urlparse, parse_qs
import evelink.thirdparty.eve_who as evelink_evewho


class EVEWhoTestCase(unittest.TestCase):
    def test_member_list(self):
        mock_fetch = mock.MagicMock()
        mock_fetch.return_value = """
                {"info":{
                    "corporation_id":"869043665",
                    "name":"Woopatang",
                    "member_count":"3"
                    },
                "characters":[
                    {
                    "character_id":"403163173",
                    "corporation_id":"869043665",
                    "alliance_id":"99001433",
                    "name":"Aeryn Tiberius"
                    },
                    {
                    "character_id":"149932493",
                    "corporation_id":"869043665",
                    "alliance_id":"99001433",
                    "name":"Agamemon"
                    },
                    {
                    "character_id":"90464284",
                    "corporation_id":"869043665",
                    "alliance_id":"99001433",
                    "name":"Aidera Boirelle"
                    }
                ]}
            """.strip()

        evewho = evelink_evewho.EVEWho(url_fetch_func=mock_fetch)
        results = evewho._member_list(869043665, 'corplist')

        self.assertEqual(results, [
            {
                'alli_id': 99001433,
                'char_id': 403163173,
                'name': 'Aeryn Tiberius',
                'corp_id': 869043665
            },
            {
                'alli_id': 99001433,
                'char_id': 149932493,
                'name': 'Agamemon',
                'corp_id': 869043665
            },
            {
                'alli_id': 99001433,
                'char_id': 90464284,
                'name': 'Aidera Boirelle',
                'corp_id': 869043665
            }
        ])

        fetch_query_dict = parse_qs(
                urlparse(mock_fetch.mock_calls[0][1][0]).query)
        expected_query_dict = parse_qs('type=corplist&id=869043665&page=0')

        self.assertEqual(fetch_query_dict, expected_query_dict)

########NEW FILE########
__FILENAME__ = utils
import os
import unittest
from xml.etree import ElementTree

import mock

import evelink.api as evelink_api


def make_api_result(xml_path):
    xml_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xml')
    with open(os.path.join(xml_dir, xml_path)) as f:
        return evelink_api.APIResult(ElementTree.parse(f), 12345, 67890)


class APITestCase(unittest.TestCase):
    def setUp(self):
        super(APITestCase, self).setUp()
        self.api = mock.MagicMock(spec=evelink_api.API)

    def make_api_result(self, xml_path):
        return make_api_result(xml_path)

########NEW FILE########
