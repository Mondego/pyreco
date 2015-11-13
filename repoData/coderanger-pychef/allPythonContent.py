__FILENAME__ = api
import copy
import datetime
import itertools
import logging
import os
import re
import socket
import subprocess
import threading
import urllib2
import urlparse
import weakref

import pkg_resources

from chef.auth import sign_request
from chef.exceptions import ChefServerError
from chef.rsa import Key
from chef.utils import json
from chef.utils.file import walk_backwards

api_stack = threading.local()
log = logging.getLogger('chef.api')

config_ruby_script = """
require 'chef'
Chef::Config.from_file('%s')
puts Chef::Config.configuration.to_json
""".strip()

def api_stack_value():
    if not hasattr(api_stack, 'value'):
        api_stack.value = []
    return api_stack.value


class UnknownRubyExpression(Exception):
    """Token exception for unprocessed Ruby expressions."""


class ChefRequest(urllib2.Request):
    """Workaround for using PUT/DELETE with urllib2."""
    def __init__(self, *args, **kwargs):
        self._method = kwargs.pop('method', None)
        # Request is an old-style class, no super() allowed.
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self):
        if self._method:
            return self._method
        return urllib2.Request.get_method(self)


class ChefAPI(object):
    """The ChefAPI object is a wrapper for a single Chef server.

    .. admonition:: The API stack

        PyChef maintains a stack of :class:`ChefAPI` objects to be use with
        other methods if an API object isn't given explicitly. The first
        ChefAPI created will become the default, though you can set a specific
        default using :meth:`ChefAPI.set_default`. You can also use a ChefAPI
        as a context manager to create a scoped default::

            with ChefAPI('http://localhost:4000', 'client.pem', 'admin'):
                n = Node('web1')
    """

    ruby_value_re = re.compile(r'#\{([^}]+)\}')
    env_value_re = re.compile(r'ENV\[(.+)\]')
    ruby_string_re = re.compile(r'^\s*(["\'])(.*?)\1\s*$')

    def __init__(self, url, key, client, version='0.10.8', headers={}):
        self.url = url.rstrip('/')
        self.parsed_url = urlparse.urlparse(self.url)
        if not isinstance(key, Key):
            key = Key(key)
        self.key = key
        self.client = client
        self.version = version
        self.headers = dict((k.lower(), v) for k, v in headers.iteritems())
        self.version_parsed = pkg_resources.parse_version(self.version)
        self.platform = self.parsed_url.hostname == 'api.opscode.com'
        if not api_stack_value():
            self.set_default()

    @classmethod
    def from_config_file(cls, path):
        """Load Chef API paraters from a config file. Returns None if the
        config can't be used.
        """
        log.debug('Trying to load from "%s"', path)
        if not os.path.isfile(path) or not os.access(path, os.R_OK):
            # Can't even read the config file
            log.debug('Unable to read config file "%s"', path)
            return
        url = key_path = client_name = None
        for line in open(path):
            if not line.strip() or line.startswith('#'):
                continue # Skip blanks and comments
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue # Not a simple key/value, we can't parse it anyway
            key, value = parts
            md = cls.ruby_string_re.search(value)
            if md:
                value = md.group(2)
            else:
                # Not a string, don't even try
                log.debug('Value for %s does not look like a string: %s'%(key, value))
                continue
            def _ruby_value(match):
                expr = match.group(1).strip()
                if expr == 'current_dir':
                    return os.path.dirname(path)
                envmatch = cls.env_value_re.match(expr)
                if envmatch:
                    envmatch = envmatch.group(1).strip('"').strip("'")
                    return os.environ.get(envmatch) or ''
                log.debug('Unknown ruby expression in line "%s"', line)
                raise UnknownRubyExpression
            try:
                value = cls.ruby_value_re.sub(_ruby_value, value)
            except UnknownRubyExpression:
                continue
            if key == 'chef_server_url':
                log.debug('Found URL: %r', value)
                url = value
            elif key == 'node_name':
                log.debug('Found client name: %r', value)
                client_name = value
            elif key == 'client_key':
                log.debug('Found key path: %r', value)
                key_path = value
                if not os.path.isabs(key_path):
                    # Relative paths are relative to the config file
                    key_path = os.path.abspath(os.path.join(os.path.dirname(path), key_path))
        if not (url and client_name and key_path):
            # No URL, no chance this was valid, try running Ruby
            log.debug('No Chef server config found, trying Ruby parse')
            url = key_path = client_name = None
            proc = subprocess.Popen('ruby', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            script = config_ruby_script % path.replace('\\', '\\\\').replace("'", "\\'")
            out, err = proc.communicate(script)
            if proc.returncode == 0 and out.strip():
                data = json.loads(out)
                log.debug('Ruby parse succeeded with %r', data)
                url = data.get('chef_server_url')
                client_name = data.get('node_name')
                key_path = data.get('client_key')
            else:
                log.debug('Ruby parse failed with exit code %s: %s', proc.returncode, out.strip())
        if not url:
            # Still no URL, can't use this config
            log.debug('Still no Chef server URL found')
            return
        if not key_path:
            # Try and use ./client.pem
            key_path = os.path.join(os.path.dirname(path), 'client.pem')
        if not os.path.isfile(key_path) or not os.access(key_path, os.R_OK):
            # Can't read the client key
            log.debug('Unable to read key file "%s"', key_path)
            return
        if not client_name:
            client_name = socket.getfqdn()
        return cls(url, key_path, client_name)

    @staticmethod
    def get_global():
        """Return the API on the top of the stack."""
        while api_stack_value():
            api = api_stack_value()[-1]()
            if api is not None:
                return api
            del api_stack_value()[-1]

    def set_default(self):
        """Make this the default API in the stack. Returns the old default if any."""
        old = None
        if api_stack_value():
            old = api_stack_value().pop(0)
        api_stack_value().insert(0, weakref.ref(self))
        return old

    def __enter__(self):
        api_stack_value().append(weakref.ref(self))
        return self

    def __exit__(self, type, value, traceback):
        del api_stack_value()[-1]

    def _request(self, method, url, data, headers):
        # Testing hook, subclass and override for WSGI intercept
        request = ChefRequest(url, data, headers, method=method)
        return urllib2.urlopen(request).read()

    def request(self, method, path, headers={}, data=None):
        auth_headers = sign_request(key=self.key, http_method=method,
            path=self.parsed_url.path+path.split('?', 1)[0], body=data,
            host=self.parsed_url.netloc, timestamp=datetime.datetime.utcnow(),
            user_id=self.client)
        request_headers = {}
        request_headers.update(self.headers)
        request_headers.update(dict((k.lower(), v) for k, v in headers.iteritems()))
        request_headers['x-chef-version'] = self.version
        request_headers.update(auth_headers)
        try:
            response = self._request(method, self.url+path, data, dict((k.capitalize(), v) for k, v in request_headers.iteritems()))
        except urllib2.HTTPError, e:
            e.content = e.read()
            try:
                e.content = json.loads(e.content)
                raise ChefServerError.from_error(e.content['error'], code=e.code)
            except ValueError:
                pass
            raise e
        return response

    def api_request(self, method, path, headers={}, data=None):
        headers = dict((k.lower(), v) for k, v in headers.iteritems())
        headers['accept'] = 'application/json'
        if data is not None:
            headers['content-type'] = 'application/json'
            data = json.dumps(data)
        response = self.request(method, path, headers, data)
        return json.loads(response)

    def __getitem__(self, path):
        return self.api_request('GET', path)


def autoconfigure(base_path=None):
    """Try to find a knife or chef-client config file to load parameters from,
    starting from either the given base path or the current working directory.

    The lookup order mirrors the one from Chef, first all folders from the base
    path are walked back looking for .chef/knife.rb, then ~/.chef/knife.rb,
    and finally /etc/chef/client.rb.

    The first file that is found and can be loaded successfully will be loaded
    into a :class:`ChefAPI` object.
    """
    base_path = base_path or os.getcwd()
    # Scan up the tree for a knife.rb or client.rb. If that fails try looking
    # in /etc/chef. The /etc/chef check will never work in Win32, but it doesn't
    # hurt either.
    for path in walk_backwards(base_path):
        config_path = os.path.join(path, '.chef', 'knife.rb')
        api = ChefAPI.from_config_file(config_path)
        if api is not None:
            return api

    # The walk didn't work, try ~/.chef/knife.rb
    config_path = os.path.expanduser(os.path.join('~', '.chef', 'knife.rb'))
    api = ChefAPI.from_config_file(config_path)
    if api is not None:
        return api

    # Nothing in the home dir, try /etc/chef/client.rb
    config_path = os.path.join(os.path.sep, 'etc', 'chef', 'client.rb')
    api = ChefAPI.from_config_file(config_path)
    if api is not None:
        return api

########NEW FILE########
__FILENAME__ = auth
import base64
import datetime
import hashlib
import re

def _ruby_b64encode(value):
    """The Ruby function Base64.encode64 automatically breaks things up
    into 60-character chunks.
    """
    b64 = base64.b64encode(value)
    for i in xrange(0, len(b64), 60):
        yield b64[i:i+60]

def ruby_b64encode(value):
    return '\n'.join(_ruby_b64encode(value))

def sha1_base64(value):
    """An implementation of Mixlib::Authentication::Digester."""
    return ruby_b64encode(hashlib.sha1(value).digest())

class UTC(datetime.tzinfo):
    """UTC timezone stub."""
    
    ZERO = datetime.timedelta(0)

    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return self.ZERO

utc = UTC()

def canonical_time(timestamp):
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(utc).replace(tzinfo=None)
    return timestamp.replace(microsecond=0).isoformat() + 'Z'

canonical_path_regex = re.compile(r'/+')
def canonical_path(path):
    path = canonical_path_regex.sub('/', path)
    if len(path) > 1:
        path = path.rstrip('/')
    return path

def canonical_request(http_method, path, hashed_body, timestamp, user_id):
    # Canonicalize request parameters
    http_method = http_method.upper()
    path = canonical_path(path)
    if isinstance(timestamp, datetime.datetime):
        timestamp = canonical_time(timestamp)
    hashed_path = sha1_base64(path)
    return ('Method:%(http_method)s\n'
            'Hashed Path:%(hashed_path)s\n'
            'X-Ops-Content-Hash:%(hashed_body)s\n'
            'X-Ops-Timestamp:%(timestamp)s\n'
            'X-Ops-UserId:%(user_id)s' % vars())

def sign_request(key, http_method, path, body, host, timestamp, user_id):
    """Generate the needed headers for the Opscode authentication protocol."""
    timestamp = canonical_time(timestamp)
    hashed_body = sha1_base64(body or '')
    
    # Simple headers
    headers = {
        'x-ops-sign': 'version=1.0',
        'x-ops-userid': user_id,
        'x-ops-timestamp': timestamp,
        'x-ops-content-hash': hashed_body,
    }
    
    # Create RSA signature
    req = canonical_request(http_method, path, hashed_body, timestamp, user_id)
    sig = _ruby_b64encode(key.private_encrypt(req))
    for i, line in enumerate(sig):
        headers['x-ops-authorization-%s'%(i+1)] = line
    return headers

########NEW FILE########
__FILENAME__ = base
import collections

import pkg_resources

from chef.api import ChefAPI
from chef.exceptions import *

class ChefQuery(collections.Mapping):
    def __init__(self, obj_class, names, api):
        self.obj_class = obj_class
        self.names = names
        self.api = api

    def __len__(self):
        return len(self.names)

    def __contains__(self, key):
        return key in self.names

    def __iter__(self):
        return iter(self.names)

    def __getitem__(self, name):
        if name not in self:
            raise KeyError('%s not found'%name)
        return self.obj_class(name, api=self.api)


class ChefObjectMeta(type):
    def __init__(cls, name, bases, d):
        super(ChefObjectMeta, cls).__init__(name, bases, d)
        if name != 'ChefObject':
            ChefObject.types[name.lower()] = cls
        cls.api_version_parsed = pkg_resources.parse_version(cls.api_version)


class ChefObject(object):
    """A base class for Chef API objects."""

    __metaclass__ = ChefObjectMeta
    types = {}

    url = ''
    attributes = {}

    api_version = '0.9'

    def __init__(self, name, api=None, skip_load=False):
        self.name = name
        self.api = api or ChefAPI.get_global()
        self._check_api_version(self.api)

        self.url = self.__class__.url + '/' + self.name
        self.exists = False
        data = {}
        if not skip_load:
            try:
                data = self.api[self.url]
            except ChefServerNotFoundError:
                pass
            else:
                self.exists = True
        self._populate(data)

    def _populate(self, data):
        for name, cls in self.__class__.attributes.iteritems():
            if name in data:
                value = cls(data[name])
            else:
                value = cls()
            setattr(self, name, value)

    @classmethod
    def from_search(cls, data, api=None):
        obj = cls(data.get('name'), api=api, skip_load=True)
        obj.exists = True
        obj._populate(data)
        return obj

    @classmethod
    def list(cls, api=None):
        """Return a :class:`ChefQuery` with the available objects of this type.
        """
        api = api or ChefAPI.get_global()
        cls._check_api_version(api)
        names = [name for name, url in api[cls.url].iteritems()]
        return ChefQuery(cls, names, api)

    @classmethod
    def create(cls, name, api=None, **kwargs):
        """Create a new object of this type. Pass the initial value for any
        attributes as keyword arguments.
        """
        api = api or ChefAPI.get_global()
        cls._check_api_version(api)
        obj = cls(name, api, skip_load=True)
        for key, value in kwargs.iteritems():
            setattr(obj, key, value)
        api.api_request('POST', cls.url, data=obj)
        return obj

    def save(self, api=None):
        """Save this object to the server. If the object does not exist it
        will be created.
        """
        api = api or self.api
        try:
            api.api_request('PUT', self.url, data=self)
        except ChefServerNotFoundError, e:
            # If you get a 404 during a save, just create it instead
            # This mirrors the logic in the Chef code
            api.api_request('POST', self.__class__.url, data=self)

    def delete(self, api=None):
        """Delete this object from the server."""
        api = api or self.api
        api.api_request('DELETE', self.url)

    def to_dict(self):
        d = {
            'name': self.name,
            'json_class': 'Chef::'+self.__class__.__name__,
            'chef_type': self.__class__.__name__.lower(),
        }
        for attr in self.__class__.attributes.iterkeys():
            d[attr] = getattr(self, attr)
        return d

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s %s>'%(type(self).__name__, self)

    @classmethod
    def _check_api_version(cls, api):
        # Don't enforce anything if api is None, since there is sometimes a
        # use for creating Chef objects without an API connection (just for
        # serialization perhaps).
        if api and cls.api_version_parsed > api.version_parsed:
            raise ChefAPIVersionError, "Class %s is not compatible with API version %s" % (cls.__name__, api.version)

########NEW FILE########
__FILENAME__ = client
from chef.api import ChefAPI
from chef.base import ChefObject

class Client(ChefObject):
    """A Chef client object."""

    url = '/clients'

    def _populate(self, data):
        self.platform = self.api and self.api.platform
        self.private_key = None
        if self.platform:
            self.orgname = data.get('orgname')
            self.validator = bool(data.get('validator', False))
            self.public_key = data.get('certificate')
            self.admin = False
        else:
            self.admin = bool(data.get('admin', False))
            self.public_key = data.get('public_key')
            self.orgname = None
            self.validator = False

    @property
    def certificate(self):
        return self.public_key

    def to_dict(self):
        d = super(Client, self).to_dict()
        d['json_class'] = 'Chef::ApiClient'
        if self.platform:
            d.update({
                'orgname': self.orgname,
                'validator': self.validator,
                'certificate': self.certificate,
                'clientname': self.name,
            })
        else:
            d.update({
                'admin': self.admin,
                'public_key': self.public_key,
            })
        return d

    @classmethod
    def create(cls, name, api=None, admin=False):
        api = api or ChefAPI.get_global()
        obj = cls(name, api, skip_load=True)
        obj.admin = admin
        d = api.api_request('POST', cls.url, data=obj)
        obj.private_key = d['private_key']
        return obj

    def rekey(self, api=None):
        api = api or self.api
        d_in = {'name': self.name, 'private_key': True}
        d_out = api.api_request('PUT', self.url, data=d_in)
        self.private_key = d_out['private_key']

########NEW FILE########
__FILENAME__ = data_bag
import abc
import collections

from chef.api import ChefAPI
from chef.base import ChefObject, ChefQuery, ChefObjectMeta
from chef.exceptions import ChefError, ChefServerNotFoundError

class DataBagMeta(ChefObjectMeta, abc.ABCMeta):
    """A metaclass to allow DataBag to use multiple inheritance."""


class DataBag(ChefObject, ChefQuery):
    """A Chef data bag object.

    Data bag items are available via the mapping API. Evaluation works in the
    same way as :class:`ChefQuery`, so requesting only the names will not
    cause the items to be loaded::

        bag = DataBag('versions')
        item = bag['web']
        for name, item in bag.iteritems():
            print item['qa_version']
    """

    __metaclass__ = DataBagMeta

    url = '/data'

    def _populate(self, data):
        self.names = data.keys()

    def obj_class(self, name, api):
        return DataBagItem(self, name, api=api)


class DataBagItem(ChefObject, collections.MutableMapping):
    """A Chef data bag item object.

    Data bag items act as normal dicts and can contain arbitrary data.
    """

    __metaclass__ = DataBagMeta

    url = '/data'
    attributes = {
        'raw_data': dict,
    }

    def __init__(self, bag, name, api=None, skip_load=False):
        self._bag = bag
        super(DataBagItem, self).__init__(str(bag)+'/'+name, api=api, skip_load=skip_load)
        self.name = name

    @property
    def bag(self):
        """The :class:`DataBag` this item is a member of."""
        if not isinstance(self._bag, DataBag):
            self._bag = DataBag(self._bag, api=self.api)
        return self._bag

    @classmethod
    def from_search(cls, data, api):
        bag = data.get('data_bag')
        if not bag:
            raise ChefError('No data_bag key in data bag item information')
        name = data.get('name')
        if not name:
            raise ChefError('No name key in the data bag item information')
        item = name[len('data_bag_item_' + bag + '_'):]
        obj = cls(bag, item, api=api, skip_load=True)
        obj.exists = True
        obj._populate(data)
        return obj

    def _populate(self, data):
        if 'json_class' in data:
            self.raw_data = data['raw_data']
        else:
            self.raw_data = data

    def __len__(self):
        return len(self.raw_data)

    def __iter__(self):
        return iter(self.raw_data)

    def __getitem__(self, key):
        return self.raw_data[key]

    def __setitem__(self, key, value):
        self.raw_data[key] = value

    def __delitem__(self, key):
        del self.raw_data[key]

    @classmethod
    def create(cls, bag, name, api=None, **kwargs):
        """Create a new data bag item. Pass the initial value for any keys as
        keyword arguments."""
        api = api or ChefAPI.get_global()
        obj = cls(bag, name, api, skip_load=True)
        for key, value in kwargs.iteritems():
            obj[key] = value
        obj['id'] = name
        api.api_request('POST', cls.url+'/'+str(bag), data=obj.raw_data)
        if isinstance(bag, DataBag) and name not in bag.names:
            # Mutate the bag in-place if possible, so it will return the new
            # item instantly
            bag.names.append(name)
        return obj

    def save(self, api=None):
        """Save this object to the server. If the object does not exist it
        will be created.
        """
        api = api or self.api
        self['id'] = self.name
        try:
            api.api_request('PUT', self.url, data=self.raw_data)
        except ChefServerNotFoundError, e:
            api.api_request('POST', self.__class__.url+'/'+str(self._bag), data=self.raw_data)

########NEW FILE########
__FILENAME__ = environment
from chef.base import ChefObject

class Environment(ChefObject):
    """A Chef environment object.

    .. versionadded:: 0.2
    """

    url = '/environments'
    
    api_version = '0.10'

    attributes = {
        'description': str,
        'cookbook_versions': dict,
        'default_attributes': dict,
        'override_attributes': dict,
    }

########NEW FILE########
__FILENAME__ = exceptions
# Exception hierarchy for chef
# Copyright (c) 2010 Noah Kantrowitz <noah@coderanger.net>

class ChefError(Exception):
    """Top-level Chef error."""


class ChefServerError(ChefError):
    """An error from a Chef server. May include a HTTP response code."""

    def __init__(self, message, code=None):
        self.raw_message = message
        if isinstance(message, list):
            message = u', '.join(m for m in message if m)
        super(ChefError, self).__init__(message)
        self.code = code

    @staticmethod
    def from_error(message, code=None):
        cls = {
            404: ChefServerNotFoundError,
        }.get(code, ChefServerError)
        return cls(message, code)


class ChefServerNotFoundError(ChefServerError):
    """A 404 Not Found server error."""


class ChefAPIVersionError(ChefError):
    """An incompatible API version error"""

########NEW FILE########
__FILENAME__ = fabric
from __future__ import absolute_import

import functools

from chef.api import ChefAPI, autoconfigure
from chef.environment import Environment
from chef.exceptions import ChefError, ChefAPIVersionError
from chef.search import Search

try:
    from fabric.api import env, task, roles, output
except ImportError, e:
    env = {}
    task = lambda *args, **kwargs: lambda fn: fn
    roles = task

__all__ = ['chef_roledefs', 'chef_environment', 'chef_query', 'chef_tags']

# Default environment name
DEFAULT_ENVIRONMENT = '_default'

# Default hostname attributes
DEFAULT_HOSTNAME_ATTR = ['cloud.public_hostname', 'fqdn']

# Sentinel object to trigger defered lookup
_default_environment = object()

def _api(api):
    api = api or ChefAPI.get_global() or autoconfigure()
    if not api:
        raise ChefError('Unable to load Chef API configuration')
    return api


class Roledef(object):
    """Represents a Fabric roledef for a Chef role."""
    def __init__(self, query, api, hostname_attr, environment=None):
        self.query = query
        self.api = api
        self.hostname_attr = hostname_attr
        if isinstance(self.hostname_attr, basestring):
            self.hostname_attr = (self.hostname_attr,)
        self.environment = environment

    def __call__(self):
        query = self.query
        environment = self.environment
        if environment is _default_environment:
            environment = env.get('chef_environment', DEFAULT_ENVIRONMENT)
        if environment:
            query += ' AND chef_environment:%s' % environment
        for row in Search('node', query, api=self.api):
            if row:
                if callable(self.hostname_attr):
                    val = self.hostname_attr(row.object)
                    if val:
                        yield val
                else:
                    for attr in self.hostname_attr:
                        try:
                            val =  row.object.attributes.get_dotted(attr)
                            if val: # Don't ever give out '' or None, since it will error anyway
                                yield val
                                break
                        except KeyError:
                            pass # Move on to the next
                    else:
                        raise ChefError('Cannot find a usable hostname attribute for node %s', row.object)


def chef_roledefs(api=None, hostname_attr=DEFAULT_HOSTNAME_ATTR, environment=_default_environment):
    """Build a Fabric roledef dictionary from a Chef server.

    Example::

        from fabric.api import env, run, roles
        from chef.fabric import chef_roledefs

        env.roledefs = chef_roledefs()

        @roles('web_app')
        def mytask():
            run('uptime')

    ``hostname_attr`` can either be a string that is the attribute in the chef
    node that holds the hostname or IP to connect to, an array of such keys to
    check in order (the first which exists will be used), or a callable which
    takes a :class:`~chef.Node` and returns the hostname or IP to connect to.

    To refer to a nested attribute, separate the levels with ``'.'`` e.g. ``'ec2.public_hostname'``

    ``environment`` is the Chef :class:`~chef.Environment` name in which to
    search for nodes. If set to ``None``, no environment filter is added. If
    set to a string, it is used verbatim as a filter string. If not passed as
    an argument at all, the value in the Fabric environment dict is used,
    defaulting to ``'_default'``.

    .. note::

        ``environment`` must be set to ``None`` if you are emulating Chef API
        version 0.9 or lower.

    .. versionadded:: 0.1

    .. versionadded:: 0.2
        Support for iterable and callable values for  the``hostname_attr``
        argument, and the ``environment`` argument.
    """
    api = _api(api)
    if api.version_parsed < Environment.api_version_parsed and environment is not None:
        raise ChefAPIVersionError('Environment support requires Chef API 0.10 or greater')
    roledefs = {}
    for row in Search('role', api=api):
        name = row['name']
        roledefs[name] =  Roledef('roles:%s' % name, api, hostname_attr, environment)
    return roledefs


@task(alias=env.get('chef_environment_task_alias', 'env'))
def chef_environment(name, api=None):
    """A Fabric task to set the current Chef environment context.

    This task works alongside :func:`~chef.fabric.chef_roledefs` to set the
    Chef environment to be used in future role queries.

    Example::

        from chef.fabric import chef_environment, chef_roledefs
        env.roledefs = chef_roledefs()

    .. code-block:: bash

        $ fab env:production deploy

    The task can be configured slightly via Fabric ``env`` values.

    ``env.chef_environment_task_alias`` sets the task alias, defaulting to "env".
    This value must be set **before** :mod:`chef.fabric` is imported.

    ``env.chef_environment_validate`` sets if :class:`~chef.Environment` names
    should be validated before use. Defaults to True.

    .. versionadded:: 0.2
    """
    if env.get('chef_environment_validate', True):
        api = _api(api)
        chef_env = Environment(name, api=api)
        if not chef_env.exists:
            raise ChefError('Unknown Chef environment: %s' % name)
    env['chef_environment'] = name


def chef_query(query, api=None, hostname_attr=DEFAULT_HOSTNAME_ATTR, environment=_default_environment):
    """A decorator to use an arbitrary Chef search query to find nodes to execute on.

    This is used like Fabric's ``roles()`` decorator, but accepts a Chef search query.

    Example::

        from chef.fabric import chef_query

        @chef_query('roles:web AND tags:active')
        @task
        def deploy():
            pass

    .. versionadded:: 0.2.1
    """
    api = _api(api)
    if api.version_parsed < Environment.api_version_parsed and environment is not None:
        raise ChefAPIVersionError('Environment support requires Chef API 0.10 or greater')
    rolename = 'query_'+query
    env.setdefault('roledefs', {})[rolename] = Roledef(query, api, hostname_attr, environment)
    return lambda fn: roles(rolename)(fn)


def chef_tags(*tags, **kwargs):
    """A decorator to use Chef node tags to find nodes to execute on.

    This is used like Fabric's ``roles()`` decorator, but accepts a list of tags.

    Example::

        from chef.fabric import chef_tags

        @chef_tags('active', 'migrator')
        @task
        def migrate():
            pass

    .. versionadded:: 0.2.1
    """
    # Allow passing a single iterable
    if len(tags) == 1 and not isinstance(tags[0], basestring):
        tags = tags[0]
    query = ' AND '.join('tags:%s'%tag.strip() for tag in tags)
    return chef_query(query, **kwargs)

########NEW FILE########
__FILENAME__ = node
import collections

from chef.base import ChefObject
from chef.exceptions import ChefError

class NodeAttributes(collections.MutableMapping):
    """A collection of Chef :class:`~chef.Node` attributes.

    Attributes can be accessed like a normal python :class:`dict`::

        print node['fqdn']
        node['apache']['log_dir'] = '/srv/log'

    When writing to new attributes, any dicts required in the hierarchy are
    created automatically.

    .. versionadded:: 0.1
    """

    def __init__(self, search_path=[], path=None, write=None):
        if not isinstance(search_path, collections.Sequence):
            search_path = [search_path]
        self.search_path = search_path
        self.path = path or ()
        self.write = write

    def __iter__(self):
        keys = set()
        for d in self.search_path:
            keys |= set(d.iterkeys())
        return iter(keys)

    def __len__(self):
        l = 0
        for key in self:
            l += 1
        return l

    def __getitem__(self, key):
        for d in self.search_path:
            if key in d:
                value = d[key]
                break
        else:
            raise KeyError(key)
        if not isinstance(value, dict):
            return value
        new_search_path = []
        for d in self.search_path:
            new_d = d.get(key, {})
            if not isinstance(new_d, dict):
                # Structural mismatch
                new_d = {}
            new_search_path.append(new_d)
        return self.__class__(new_search_path, self.path+(key,), write=self.write)

    def __setitem__(self, key, value):
        if self.write is None:
            raise ChefError('This attribute is not writable')
        dest = self.write
        for path_key in self.path:
            dest = dest.setdefault(path_key, {})
        dest[key] = value

    def __delitem__(self, key):
        if self.write is None:
            raise ChefError('This attribute is not writable')
        dest = self.write
        for path_key in self.path:
            dest = dest.setdefault(path_key, {})
        del dest[key]

    def has_dotted(self, key):
        """Check if a given dotted key path is present. See :meth:`.get_dotted`
        for more information on dotted paths.

        .. versionadded:: 0.2
        """
        try:
            self.get_dotted(key)
        except KeyError:
            return False
        else:
            return True

    def get_dotted(self, key):
        """Retrieve an attribute using a dotted key path. A dotted path
        is a string of the form `'foo.bar.baz'`, with each `.` separating
        hierarcy levels.

        Example::

            node.attributes['apache']['log_dir'] = '/srv/log'
            print node.attributes.get_dotted('apache.log_dir')
        """
        value = self
        for k in key.split('.'):
            if not isinstance(value, NodeAttributes):
                raise KeyError(key)
            value = value[k]
        return value

    def set_dotted(self, key, value):
        """Set an attribute using a dotted key path. See :meth:`.get_dotted`
        for more information on dotted paths.

        Example::

            node.attributes.set_dotted('apache.log_dir', '/srv/log')
        """
        dest = self
        keys = key.split('.')
        last_key = keys.pop()
        for k in keys:
            if k not in dest:
                dest[k] = {}
            dest = dest[k]
            if not isinstance(dest, NodeAttributes):
                raise ChefError
        dest[last_key] = value

    def to_dict(self):
        merged = {}
        for d in reversed(self.search_path):
            merged.update(d)
        return merged


class Node(ChefObject):
    """A Chef node object.

    The Node object can be used as a dict-like object directly, as an alias for
    the :attr:`.attributes` data::

        >>> node = Node('name')
        >>> node['apache']['log_dir']
        '/var/log/apache2'

    .. versionadded:: 0.1

    .. attribute:: attributes

        :class:`~chef.node.NodeAttributes` corresponding to the composite of all
        precedence levels. This only uses the stored data on the Chef server,
        it does not merge in attributes from roles or environments on its own.

        ::

            >>> node.attributes['apache']['log_dir']
            '/var/log/apache2'

    .. attribute:: run_list

        The run list of the node. This is the unexpanded list in ``type[name]``
        format.

        ::

            >>> node.run_list
            ['role[base]', 'role[app]', 'recipe[web]']

    .. attribute:: chef_environment

        The name of the Chef :class:`~chef.Environment` this node is a member
        of. This value will still be present, even if communicating with a Chef
        0.9 server, but will be ignored.

        .. versionadded:: 0.2

    .. attribute:: default

        :class:`~chef.node.NodeAttributes` corresponding to the ``default``
        precedence level.

    .. attribute:: normal

        :class:`~chef.node.NodeAttributes` corresponding to the ``normal``
        precedence level.

    .. attribute:: override

        :class:`~chef.node.NodeAttributes` corresponding to the ``override``
        precedence level.

    .. attribute:: automatic

        :class:`~chef.node.NodeAttributes` corresponding to the ``automatic``
        precedence level.
    """

    url = '/nodes'
    attributes = {
        'default': NodeAttributes,
        'normal': lambda d: NodeAttributes(d, write=d),
        'override': NodeAttributes,
        'automatic': NodeAttributes,
        'run_list': list,
        'chef_environment': str
    }

    def has_key(self, key):
      return self.attributes.has_dotted(key)

    def get(self, key, default=None):
        return self.attributes.get(key, default)

    def __getitem__(self, key):
        return self.attributes[key]

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def _populate(self, data):
        if not self.exists:
            # Make this exist so the normal<->attributes cross-link will
            # function correctly
            data['normal'] = {}
        data.setdefault('chef_environment', '_default')
        super(Node, self)._populate(data)
        self.attributes = NodeAttributes((data.get('automatic', {}),
                                          data.get('override', {}),
                                          data['normal'], # Must exist, see above
                                          data.get('default', {})), write=data['normal'])

    def cookbooks(self, api=None):
        api = api or self.api
        return api[self.url + '/cookbooks']

########NEW FILE########
__FILENAME__ = role
from chef.base import ChefObject

class Role(ChefObject):
    """A Chef role object."""

    url = '/roles'
    attributes = {
        'description': str,
        'run_list': list,
        'default_attributes': dict,
        'override_attributes': dict,
        'env_run_lists': dict
    }

########NEW FILE########
__FILENAME__ = rsa
import sys
from ctypes import *

if sys.platform == 'win32' or sys.platform == 'cygwin':
    _eay = CDLL('libeay32.dll')
elif sys.platform == 'darwin':
    _eay = CDLL('libcrypto.dylib')
else:
    _eay = CDLL('libcrypto.so')

#unsigned long ERR_get_error(void);
ERR_get_error = _eay.ERR_get_error
ERR_get_error.argtypes = []
ERR_get_error.restype = c_ulong

#void ERR_error_string_n(unsigned long e, char *buf, size_t len);
ERR_error_string_n = _eay.ERR_error_string_n
ERR_error_string_n.argtypes = [c_ulong, c_char_p, c_size_t]
ERR_error_string_n.restype = None

class SSLError(Exception):
    """An error in OpenSSL."""

    def __init__(self, message, *args):
        message = message%args
        err = ERR_get_error()
        if err:
            message += ':'
        while err:
            buf = create_string_buffer(120)
            ERR_error_string_n(err, buf, 120)
            message += '\n%s'%string_at(buf, 119)
            err = ERR_get_error()
        super(SSLError, self).__init__(message)


#BIO *   BIO_new(BIO_METHOD *type);
BIO_new = _eay.BIO_new
BIO_new.argtypes = [c_void_p]
BIO_new.restype = c_void_p

# BIO *BIO_new_mem_buf(void *buf, int len);
BIO_new_mem_buf = _eay.BIO_new_mem_buf
BIO_new_mem_buf.argtypes = [c_void_p, c_int]
BIO_new_mem_buf.restype = c_void_p

#BIO_METHOD *BIO_s_mem(void);
BIO_s_mem = _eay.BIO_s_mem
BIO_s_mem.argtypes = []
BIO_s_mem.restype = c_void_p

#long    BIO_ctrl(BIO *bp,int cmd,long larg,void *parg);
BIO_ctrl = _eay.BIO_ctrl
BIO_ctrl.argtypes = [c_void_p, c_int, c_long, c_void_p]
BIO_ctrl.restype = c_long

#define BIO_CTRL_RESET          1  /* opt - rewind/zero etc */
BIO_CTRL_RESET = 1
##define BIO_CTRL_INFO           3  /* opt - extra tit-bits */
BIO_CTRL_INFO = 3

#define BIO_reset(b)            (int)BIO_ctrl(b,BIO_CTRL_RESET,0,NULL)
def BIO_reset(b):
    return BIO_ctrl(b, BIO_CTRL_RESET, 0, None)

##define BIO_get_mem_data(b,pp)  BIO_ctrl(b,BIO_CTRL_INFO,0,(char *)pp)
def BIO_get_mem_data(b, pp):
    return BIO_ctrl(b, BIO_CTRL_INFO, 0, pp)

# int    BIO_free(BIO *a)
BIO_free = _eay.BIO_free
BIO_free.argtypes = [c_void_p]
BIO_free.restype = c_int
def BIO_free_errcheck(result, func, arguments):
    if result == 0:
        raise SSLError('Unable to free BIO')
BIO_free.errcheck = BIO_free_errcheck

#RSA *PEM_read_bio_RSAPrivateKey(BIO *bp, RSA **x,
#                                        pem_password_cb *cb, void *u);
PEM_read_bio_RSAPrivateKey = _eay.PEM_read_bio_RSAPrivateKey
PEM_read_bio_RSAPrivateKey.argtypes = [c_void_p, c_void_p, c_void_p, c_void_p]
PEM_read_bio_RSAPrivateKey.restype = c_void_p

#RSA *PEM_read_bio_RSAPublicKey(BIO *bp, RSA **x,
#                                        pem_password_cb *cb, void *u);
PEM_read_bio_RSAPublicKey = _eay.PEM_read_bio_RSAPublicKey
PEM_read_bio_RSAPublicKey.argtypes = [c_void_p, c_void_p, c_void_p, c_void_p]
PEM_read_bio_RSAPublicKey.restype = c_void_p

#int PEM_write_bio_RSAPrivateKey(BIO *bp, RSA *x, const EVP_CIPHER *enc,
#                                        unsigned char *kstr, int klen,
#                                        pem_password_cb *cb, void *u);
PEM_write_bio_RSAPrivateKey = _eay.PEM_write_bio_RSAPrivateKey
PEM_write_bio_RSAPrivateKey.argtypes = [c_void_p, c_void_p, c_void_p, c_char_p, c_int, c_void_p, c_void_p]
PEM_write_bio_RSAPrivateKey.restype = c_int

#int PEM_write_bio_RSAPublicKey(BIO *bp, RSA *x);
PEM_write_bio_RSAPublicKey = _eay.PEM_write_bio_RSAPublicKey
PEM_write_bio_RSAPublicKey.argtypes = [c_void_p, c_void_p]
PEM_write_bio_RSAPublicKey.restype = c_int

#int RSA_private_encrypt(int flen, unsigned char *from,
#    unsigned char *to, RSA *rsa,int padding);
RSA_private_encrypt = _eay.RSA_private_encrypt
RSA_private_encrypt.argtypes = [c_int, c_void_p, c_void_p, c_void_p, c_int]
RSA_private_encrypt.restype = c_int

#int RSA_public_decrypt(int flen, unsigned char *from,
#   unsigned char *to, RSA *rsa, int padding);
RSA_public_decrypt = _eay.RSA_public_decrypt
RSA_public_decrypt.argtypes = [c_int, c_void_p, c_void_p, c_void_p, c_int]
RSA_public_decrypt.restype = c_int

RSA_PKCS1_PADDING = 1
RSA_NO_PADDING = 3

# int RSA_size(const RSA *rsa);
RSA_size = _eay.RSA_size
RSA_size.argtypes = [c_void_p]
RSA_size.restype = c_int

#RSA *RSA_generate_key(int num, unsigned long e,
#    void (*callback)(int,int,void *), void *cb_arg);
RSA_generate_key = _eay.RSA_generate_key
RSA_generate_key.argtypes = [c_int, c_ulong, c_void_p, c_void_p]
RSA_generate_key.restype = c_void_p

##define RSA_F4  0x10001L
RSA_F4 = 0x10001

# void RSA_free(RSA *rsa);
RSA_free = _eay.RSA_free
RSA_free.argtypes = [c_void_p]

class Key(object):
    """An OpenSSL RSA key."""

    def __init__(self, fp=None):
        self.key = None
        self.public = False
        if not fp:
            return
        if isinstance(fp, basestring):
            if fp.startswith('-----'):
                # PEM formatted text
                self.raw = fp
            else:
                self.raw = open(fp, 'rb').read()
        else:
            self.raw = fp.read()
        self._load_key()

    def _load_key(self):
        if '\0' in self.raw:
            # Raw string has embedded nulls, treat it as binary data
            buf = create_string_buffer(self.raw, len(self.raw))
        else:
            buf = create_string_buffer(self.raw)
        
        bio = BIO_new_mem_buf(buf, len(buf))
        try:
            self.key = PEM_read_bio_RSAPrivateKey(bio, 0, 0, 0)
            if not self.key:
                BIO_reset(bio)
                self.public = True
                self.key = PEM_read_bio_RSAPublicKey(bio, 0, 0, 0)
            if not self.key:
                raise SSLError('Unable to load RSA key')
        finally:
            BIO_free(bio)

    @classmethod
    def generate(cls, size=1024, exp=RSA_F4):
        self = cls()
        self.key = RSA_generate_key(size, exp, None, None)
        return self

    def private_encrypt(self, value, padding=RSA_PKCS1_PADDING):
        if self.public:
            raise SSLError('private method cannot be used on a public key')
        buf = create_string_buffer(value, len(value))
        size = RSA_size(self.key)
        output = create_string_buffer(size)
        ret = RSA_private_encrypt(len(buf), buf, output, self.key, padding)
        if ret <= 0:
            raise SSLError('Unable to encrypt data')
        return output.raw[:ret]

    def public_decrypt(self, value, padding=RSA_PKCS1_PADDING):
        buf = create_string_buffer(value, len(value))
        size = RSA_size(self.key)
        output = create_string_buffer(size)
        ret = RSA_public_decrypt(len(buf), buf, output, self.key, padding)
        if ret <= 0:
            raise SSLError('Unable to decrypt data')
        return output.raw[:ret]

    def private_export(self):
        if self.public:
            raise SSLError('private method cannot be used on a public key')
        out = BIO_new(BIO_s_mem())
        PEM_write_bio_RSAPrivateKey(out, self.key, None, None, 0, None, None)
        buf = c_char_p()
        count = BIO_get_mem_data(out, byref(buf))
        pem = string_at(buf, count)
        BIO_free(out)
        return pem

    def public_export(self):
        out = BIO_new(BIO_s_mem())
        PEM_write_bio_RSAPublicKey(out, self.key)
        buf = c_char_p()
        count = BIO_get_mem_data(out, byref(buf))
        pem = string_at(buf, count)
        BIO_free(out)
        return pem

    def __del__(self):
        if self.key and RSA_free:
            RSA_free(self.key)

########NEW FILE########
__FILENAME__ = search
import collections
import copy
import urllib

from chef.api import ChefAPI
from chef.base import ChefQuery, ChefObject

class SearchRow(dict):
    """A single row in a search result."""

    def __init__(self, row, api):
        super(SearchRow, self).__init__(row)
        self.api = api
        self._object = None

    @property
    def object(self):
        if self._object is  None:
            # Decode Chef class name
            chef_class = self.get('json_class', '')
            if chef_class.startswith('Chef::'):
                chef_class = chef_class[6:]
            if chef_class == 'ApiClient':
                chef_class = 'Client' # Special case since I don't match the Ruby name.
            cls = ChefObject.types.get(chef_class.lower())
            if not cls:
                raise ValueError('Unknown class %s'%chef_class)
            self._object = cls.from_search(self, api=self.api)
        return self._object


class Search(collections.Sequence):
    """A search of the Chef index.
    
    The only required argument is the index name to search (eg. node, role, etc).
    The second, optional argument can be any Solr search query, with the same semantics
    as Chef.
    
    Example::
    
        for row in Search('node', 'roles:app'):
            print row['roles']
            print row.object.name
    
    .. versionadded:: 0.1
    """

    url = '/search'

    def __init__(self, index, q='*:*', rows=1000, start=0, api=None):
        self.name = index
        self.api = api or ChefAPI.get_global()
        self._args = dict(q=q, rows=rows, start=start)
        self.url = self.__class__.url + '/' + self.name + '?' + urllib.urlencode(self._args)

    @property
    def data(self):
        if not hasattr(self, '_data'):
            self._data = self.api[self.url]
        return self._data

    @property
    def total(self):
        return self.data['total']

    def query(self, query):
        args = copy.copy(self._args)
        args['q'] = query
        return self.__class__(self.name, api=self.api, **args)

    def rows(self, rows):
        args = copy.copy(self._args)
        args['rows'] = rows
        return self.__class__(self.name, api=self.api, **args)

    def start(self, start):
        args = copy.copy(self._args)
        args['start'] = start
        return self.__class__(self.name, api=self.api, **args)

    def __len__(self):
        return len(self.data['rows'])

    def __getitem__(self, value):
        if isinstance(value, slice):
            if value.step is not None and value.step != 1:
                raise ValueError('Cannot use a step other than 1')
            return self.start(self._args['start']+value.start).rows(value.stop-value.start)
        if isinstance(value, basestring):
            return self[self.index(value)]
        row_value = self.data['rows'][value]
        # Check for null rows, just in case
        if row_value is None:
            return None
        return SearchRow(row_value, self.api)

    def __contains__(self, name):
        for row in self:
            if row.object.name == name:
                return True
        return False

    def index(self, name):
        for i, row in enumerate(self):
            if row.object.name == name:
                return i
        raise ValueError('%s not in search'%name)

    def __call__(self, query):
        return self.query(query)

    @classmethod
    def list(cls, api=None):
        api = api or ChefAPI.get_global()
        names = [name for name, url in api[cls.url].iteritems()]
        return ChefQuery(cls, names, api)

########NEW FILE########
__FILENAME__ = test_api
import os

import unittest2

from chef.api import ChefAPI

class APITestCase(unittest2.TestCase):
    def load(self, path):
        path = os.path.join(os.path.dirname(__file__), 'configs', path)
        return ChefAPI.from_config_file(path)

    def test_basic(self):
        api = self.load('basic.rb')
        self.assertEqual(api.url, 'http://chef:4000')
        self.assertEqual(api.client, 'test_1')

    def test_current_dir(self):
        api = self.load('current_dir.rb')
        path = os.path.join(os.path.dirname(__file__), 'configs', 'test_1')
        self.assertEqual(api.client, path)

    def test_env_variables(self):
        try:
            os.environ['_PYCHEF_TEST_'] = 'foobar'
            api = self.load('env_values.rb')
            self.assertEqual(api.client, 'foobar')
        finally:
            del os.environ['_PYCHEF_TEST_']

########NEW FILE########
__FILENAME__ = test_client
import unittest2

from chef import Client
from chef.tests import ChefTestCase

class ClientTestCase(ChefTestCase):
    def test_list(self):
        self.assertIn('test_1', Client.list())

    def test_get(self):
        client = Client('test_1')
        self.assertTrue(client.platform)
        self.assertEqual(client.orgname, 'pycheftest')
        self.assertTrue(client.public_key)
        self.assertTrue(client.certificate)
        self.assertEqual(client.private_key, None)

    @unittest2.skip('Unknown failure, skipping until tomorrow morning <NPK 2012-03-22>')
    def test_create(self):
        name = self.random()
        client = Client.create(name)
        self.register(client)
        self.assertEqual(client.name, name)
        #self.assertEqual(client.orgname, 'pycheftest') # See CHEF-2019
        self.assertTrue(client.private_key)

        self.assertIn(name, Client.list())

        client2 = Client(name)
        client2.rekey()
        self.assertNotEqual(client.private_key, client2.private_key)

    @unittest2.skip('Unknown failure, skipping until tomorrow morning <NPK 2012-03-22>')
    def test_delete(self):
        name = self.random()
        client = Client.create(name)
        client.delete()
        self.assertNotIn(name, Client.list())

########NEW FILE########
__FILENAME__ = test_data_bag
from chef import DataBag, DataBagItem, Search
from chef.exceptions import ChefError
from chef.tests import ChefTestCase

class DataBagTestCase(ChefTestCase):
    def test_list(self):
        bags = DataBag.list()
        self.assertIn('test_1', bags)
        self.assertIsInstance(bags['test_1'], DataBag)

    def test_keys(self):
        bag = DataBag('test_1')
        self.assertItemsEqual(bag.keys(), ['item_1', 'item_2'])
        self.assertItemsEqual(iter(bag), ['item_1', 'item_2'])

    def test_item(self):
        bag = DataBag('test_1')
        item = bag['item_1']
        self.assertEqual(item['test_attr'], 1)
        self.assertEqual(item['other'], 'foo')

    def test_search_item(self):
        self.assertIn('test_1', Search.list())
        q = Search('test_1')
        self.assertIn('item_1', q)
        self.assertIn('item_2', q)
        self.assertEqual(q['item_1']['raw_data']['test_attr'], 1)
        item = q['item_1'].object
        self.assertIsInstance(item, DataBagItem)
        self.assertEqual(item['test_attr'], 1)

    def test_direct_item(self):
        item = DataBagItem('test_1', 'item_1')
        self.assertEqual(item['test_attr'], 1)
        self.assertEqual(item['other'], 'foo')

    def test_direct_item_bag(self):
        bag = DataBag('test_1')
        item = DataBagItem(bag, 'item_1')
        self.assertEqual(item['test_attr'], 1)
        self.assertEqual(item['other'], 'foo')

    def test_create_bag(self):
        name = self.random()
        bag = DataBag.create(name)
        self.register(bag)
        self.assertIn(name, DataBag.list())

    def test_create_item(self):
        value = self.random()
        bag_name = self.random()
        bag = DataBag.create(bag_name)
        self.register(bag)
        item_name = self.random()
        item = DataBagItem.create(bag, item_name, foo=value)
        self.assertIn('foo', item)
        self.assertEqual(item['foo'], value)
        self.assertIn(item_name, bag)
        bag2 = DataBag(bag_name)
        self.assertIn(item_name, bag2)
        item2 = bag2[item_name]
        self.assertIn('foo', item)
        self.assertEqual(item['foo'], value)

    def test_set_item(self):
        value = self.random()
        value2 = self.random()
        bag_name = self.random()
        bag = DataBag.create(bag_name)
        self.register(bag)
        item_name = self.random()
        item = DataBagItem.create(bag, item_name, foo=value)
        item['foo'] = value2
        item.save()
        self.assertEqual(item['foo'], value2)
        item2 = DataBagItem(bag, item_name)
        self.assertEqual(item2['foo'], value2)

########NEW FILE########
__FILENAME__ = test_environment
from chef import Environment
from chef.exceptions import ChefAPIVersionError
from chef.tests import ChefTestCase, test_chef_api

class EnvironmentTestCase(ChefTestCase):
    def test_version_error_list(self):
        with test_chef_api(version='0.9.0'):
            with self.assertRaises(ChefAPIVersionError):
                Environment.list()

    def test_version_error_create(self):
        with test_chef_api(version='0.9.0'):
            with self.assertRaises(ChefAPIVersionError):
                Environment.create(self.random())

    def test_version_error_init(self):
        with test_chef_api(version='0.9.0'):
            with self.assertRaises(ChefAPIVersionError):
                Environment(self.random())

########NEW FILE########
__FILENAME__ = test_fabric
import mock

from chef.fabric import chef_roledefs
from chef.tests import ChefTestCase, mockSearch

class FabricTestCase(ChefTestCase):
    @mock.patch('chef.search.Search')
    def test_roledef(self, MockSearch):
        search_data = {
            ('role', '*:*'): {},
        }
        search_mock_memo = {}
        def search_mock(index, q='*:*', *args, **kwargs):
            data = search_data[index, q]
            search_mock_inst = search_mock_memo.get((index, q))
            if search_mock_inst is None:
                search_mock_inst = search_mock_memo[index, q] = mock.Mock()
                search_mock_inst.data = data
            return search_mock_inst
        MockSearch.side_effect = search_mock
        print MockSearch('role').data
        

    @mockSearch({('role', '*:*'): {1:2}})
    def test_roledef2(self, MockSearch):
        print MockSearch('role').data

########NEW FILE########
__FILENAME__ = test_node
from unittest2 import TestCase, skip

from chef import Node
from chef.exceptions import ChefError
from chef.node import NodeAttributes
from chef.tests import ChefTestCase

class NodeAttributeTestCase(TestCase):
    def test_getitem(self):
        attrs = NodeAttributes([{'a': 1}])
        self.assertEqual(attrs['a'], 1)
    
    def test_setitem(self):
        data = {'a': 1}
        attrs = NodeAttributes([data], write=data)
        attrs['a'] = 2
        self.assertEqual(attrs['a'], 2)
        self.assertEqual(data['a'], 2)

    def test_getitem_nested(self):
         attrs = NodeAttributes([{'a': {'b': 1}}])
         self.assertEqual(attrs['a']['b'], 1)
    
    def test_set_nested(self):
        data = {'a': {'b': 1}}
        attrs = NodeAttributes([data], write=data)
        attrs['a']['b'] = 2
        self.assertEqual(attrs['a']['b'], 2)
        self.assertEqual(data['a']['b'], 2)
    
    def test_search_path(self):
        attrs = NodeAttributes([{'a': 1}, {'a': 2}])
        self.assertEqual(attrs['a'], 1)
    
    def test_search_path_nested(self):
        data1 = {'a': {'b': 1}}
        data2 = {'a': {'b': 2}}
        attrs = NodeAttributes([data1, data2])
        self.assertEqual(attrs['a']['b'], 1)
    
    def test_read_only(self):
        attrs = NodeAttributes([{'a': 1}])
        with self.assertRaises(ChefError):
            attrs['a'] = 2

    def test_get(self):
        attrs = NodeAttributes([{'a': 1}])
        self.assertEqual(attrs.get('a'), 1)

    def test_get_default(self):
        attrs = NodeAttributes([{'a': 1}])
        self.assertEqual(attrs.get('b'), None)

    def test_getitem_keyerror(self):
        attrs = NodeAttributes([{'a': 1}])
        with self.assertRaises(KeyError):
            attrs['b']

    def test_iter(self):
        attrs = NodeAttributes([{'a': 1, 'b': 2}])
        self.assertEqual(set(attrs), set(['a', 'b']))

    def test_iter2(self):
        attrs = NodeAttributes([{'a': {'b': 1, 'c': 2}}])
        self.assertEqual(set(attrs['a']), set(['b', 'c']))

    def test_len(self):
        attrs = NodeAttributes([{'a': 1, 'b': 2}])
        self.assertEqual(len(attrs), 2)

    def test_len2(self):
        attrs = NodeAttributes([{'a': {'b': 1, 'c': 2}}])
        self.assertEqual(len(attrs), 1)
        self.assertEqual(len(attrs['a']), 2)

    def test_get_dotted(self):
        attrs = NodeAttributes([{'a': {'b': 1}}])
        self.assertEqual(attrs.get_dotted('a.b'), 1)

    def test_get_dotted_keyerror(self):
        attrs = NodeAttributes([{'a': {'b': 1}}])
        with self.assertRaises(KeyError):
            attrs.get_dotted('a.b.c')

    def test_set_dotted(self):
        data = {'a': {'b': 1}}
        attrs = NodeAttributes([data], write=data)
        attrs.set_dotted('a.b', 2)
        self.assertEqual(attrs['a']['b'], 2)
        self.assertEqual(attrs.get_dotted('a.b'), 2)
        self.assertEqual(data['a']['b'], 2)

    def test_set_dotted2(self):
        data = {'a': {'b': 1}}
        attrs = NodeAttributes([data], write=data)
        attrs.set_dotted('a.c.d', 2)
        self.assertEqual(attrs['a']['c']['d'], 2)
        self.assertEqual(attrs.get_dotted('a.c.d'), 2)
        self.assertEqual(data['a']['c']['d'], 2)


class NodeTestCase(ChefTestCase):
    def setUp(self):
        super(NodeTestCase, self).setUp()
        self.node = Node('test_1')

    def test_default_attr(self):
        self.assertEqual(self.node.default['test_attr'], 'default')

    def test_normal_attr(self):
        self.assertEqual(self.node.normal['test_attr'], 'normal')

    def test_override_attr(self):
        self.assertEqual(self.node.override['test_attr'], 'override')

    def test_composite_attr(self):
        self.assertEqual(self.node.attributes['test_attr'], 'override')

    def test_getitem(self):
        self.assertEqual(self.node['test_attr'], 'override')

    def test_create(self):
        name = self.random()
        node = Node.create(name, run_list=['recipe[foo]'])
        self.register(node)
        self.assertEqual(node.run_list, ['recipe[foo]'])

        node2 = Node(name)
        self.assertTrue(node2.exists)
        self.assertEqual(node2.run_list, ['recipe[foo]'])

    def test_create_crosslink(self):
        node = Node.create(self.random())
        self.register(node)
        node.normal['foo'] = 'bar'
        self.assertEqual(node['foo'], 'bar')
        node.attributes['foo'] = 'baz'
        self.assertEqual(node.normal['foo'], 'baz')

########NEW FILE########
__FILENAME__ = test_role
from chef import Role
from chef.exceptions import ChefError
from chef.tests import ChefTestCase

class RoleTestCase(ChefTestCase):
    def test_get(self):
        r = Role('test_1')
        self.assertTrue(r.exists)
        self.assertEqual(r.description, 'Static test role 1')
        self.assertEqual(r.run_list, [])
        self.assertEqual(r.default_attributes['test_attr'], 'default')
        self.assertEqual(r.default_attributes['nested']['nested_attr'], 1)
        self.assertEqual(r.override_attributes['test_attr'], 'override')

    def test_create(self):
        name = self.random()
        r = Role.create(name, description='A test role', run_list=['recipe[foo]'],
                        default_attributes={'attr': 'foo'}, override_attributes={'attr': 'bar'})
        self.register(r)
        self.assertEqual(r.description, 'A test role')
        self.assertEqual(r.run_list, ['recipe[foo]'])
        self.assertEqual(r.default_attributes['attr'], 'foo')
        self.assertEqual(r.override_attributes['attr'], 'bar')

        r2 = Role(name)
        self.assertTrue(r2.exists)
        self.assertEqual(r2.description, 'A test role')
        self.assertEqual(r2.run_list, ['recipe[foo]'])
        self.assertEqual(r2.default_attributes['attr'], 'foo')
        self.assertEqual(r2.override_attributes['attr'], 'bar')

    def test_delete(self):
        name = self.random()
        r = Role.create(name)
        r.delete()
        for n in Role.list():
            self.assertNotEqual(n, name)
        self.assertFalse(Role(name).exists)
        
########NEW FILE########
__FILENAME__ = test_rsa
import os

import unittest2

from chef.rsa import Key, SSLError
from chef.tests import TEST_ROOT, skipSlowTest

class RSATestCase(unittest2.TestCase):
    def test_load_private(self):
        key = Key(os.path.join(TEST_ROOT, 'client.pem'))
        self.assertFalse(key.public)

    def test_load_public(self):
        key = Key(os.path.join(TEST_ROOT, 'client_pub.pem'))
        self.assertTrue(key.public)

    def test_private_export(self):
        key = Key(os.path.join(TEST_ROOT, 'client.pem'))
        raw = open(os.path.join(TEST_ROOT, 'client.pem'), 'rb').read()
        self.assertTrue(key.private_export().strip(), raw.strip())

    def test_public_export(self):
        key = Key(os.path.join(TEST_ROOT, 'client.pem'))
        raw = open(os.path.join(TEST_ROOT, 'client_pub.pem'), 'rb').read()
        self.assertTrue(key.public_export().strip(), raw.strip())

    def test_private_export_pubkey(self):
        key = Key(os.path.join(TEST_ROOT, 'client_pub.pem'))
        with self.assertRaises(SSLError):
            key.private_export()

    def test_public_export_pubkey(self):
        key = Key(os.path.join(TEST_ROOT, 'client_pub.pem'))
        raw = open(os.path.join(TEST_ROOT, 'client_pub.pem'), 'rb').read()
        self.assertTrue(key.public_export().strip(), raw.strip())

    def test_encrypt_decrypt(self):
        key = Key(os.path.join(TEST_ROOT, 'client.pem'))
        msg = 'Test string!'
        self.assertEqual(key.public_decrypt(key.private_encrypt(msg)), msg)

    def test_encrypt_decrypt_pubkey(self):
        key = Key(os.path.join(TEST_ROOT, 'client.pem'))
        pubkey = Key(os.path.join(TEST_ROOT, 'client_pub.pem'))
        msg = 'Test string!'
        self.assertEqual(pubkey.public_decrypt(key.private_encrypt(msg)), msg)

    def test_generate(self):
        key = Key.generate()
        msg = 'Test string!'
        self.assertEqual(key.public_decrypt(key.private_encrypt(msg)), msg)

    def test_generate_load(self):
        key = Key.generate()
        key2 = Key(key.private_export())
        self.assertFalse(key2.public)
        key3 = Key(key.public_export())
        self.assertTrue(key3.public)

    def test_load_pem_string(self):
        key = Key(open(os.path.join(TEST_ROOT, 'client.pem'), 'rb').read())
        self.assertFalse(key.public)

    def test_load_public_pem_string(self):
        key = Key(open(os.path.join(TEST_ROOT, 'client_pub.pem'), 'rb').read())
        self.assertTrue(key.public)

########NEW FILE########
__FILENAME__ = test_search
from unittest2 import skip

from chef import Search, Node
from chef.exceptions import ChefError
from chef.tests import ChefTestCase, mockSearch

class SearchTestCase(ChefTestCase):
    def test_search_all(self):
        s = Search('node')
        self.assertGreaterEqual(len(s), 3)
        self.assertIn('test_1', s)
        self.assertIn('test_2', s)
        self.assertIn('test_3', s)

    def test_search_query(self):
        s = Search('node', 'role:test_1')
        self.assertGreaterEqual(len(s), 2)
        self.assertIn('test_1', s)
        self.assertNotIn('test_2', s)
        self.assertIn('test_3', s)

    def test_list(self):
        searches = Search.list()
        self.assertIn('node', searches)
        self.assertIn('role', searches)

    def test_search_set_query(self):
        s = Search('node').query('role:test_1')
        self.assertGreaterEqual(len(s), 2)
        self.assertIn('test_1', s)
        self.assertNotIn('test_2', s)
        self.assertIn('test_3', s)

    def test_search_call(self):
        s = Search('node')('role:test_1')
        self.assertGreaterEqual(len(s), 2)
        self.assertIn('test_1', s)
        self.assertNotIn('test_2', s)
        self.assertIn('test_3', s)

    def test_rows(self):
        s = Search('node', rows=1)
        self.assertEqual(len(s), 1)
        self.assertGreaterEqual(s.total, 3)

    def test_start(self):
        s = Search('node', start=1)
        self.assertEqual(len(s), s.total-1)
        self.assertGreaterEqual(s.total, 3)

    def test_slice(self):
        s = Search('node')[1:2]
        self.assertEqual(len(s), 1)
        self.assertGreaterEqual(s.total, 3)

        s2 = s[1:2]
        self.assertEqual(len(s2), 1)
        self.assertGreaterEqual(s2.total, 3)
        self.assertNotEqual(s[0]['name'], s2[0]['name'])

        s3 = Search('node')[2:3]
        self.assertEqual(len(s3), 1)
        self.assertGreaterEqual(s3.total, 3)
        self.assertEqual(s2[0]['name'], s3[0]['name'])

    def test_object(self):
        s = Search('node', 'name:test_1')
        self.assertEqual(len(s), 1)
        node = s[0].object
        self.assertEqual(node.name, 'test_1')
        self.assertEqual(node.run_list, ['role[test_1]'])


class MockSearchTestCase(ChefTestCase):
    @mockSearch({
        ('node', '*:*'): [Node('fake_1', skip_load=True).to_dict()]
    })
    def test_single_node(self, MockSearch):
        import chef.search
        s = chef.search.Search('node')
        self.assertEqual(len(s), 1)
        self.assertIn('fake_1', s)

########NEW FILE########
__FILENAME__ = file
import os

def walk_backwards(path):
    while 1:
        yield path
        next_path = os.path.dirname(path)
        if path == next_path:
            break
        path = next_path

########NEW FILE########
__FILENAME__ = json
from __future__ import absolute_import
import types
try:
    import json
except ImportError:
    import simplejson as json

def maybe_call(x):
    if callable(x):
        return x()
    return x

class JSONEncoder(json.JSONEncoder):
    """Custom encoder to allow arbitrary classes."""

    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return maybe_call(obj.to_dict)
        elif hasattr(obj, 'to_list'):
            return maybe_call(obj.to_list)
        elif isinstance(obj, types.GeneratorType):
            return list(obj)
        return super(JSONEncoder, self).default(obj)

loads = json.loads
dumps = lambda obj, **kwargs: json.dumps(obj, cls=JSONEncoder, **kwargs)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyChef documentation build configuration file, created by
# sphinx-quickstart on Sat Aug 14 18:14:46 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'PyChef'
copyright = u'2010-2012, Noah Kantrowitz'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
import pkg_resources
try:
    release = pkg_resources.get_distribution('PyChef').version
except pkg_resources.DistributionNotFound:
    print 'To build the documentation, The distribution information of PyChef'
    print 'Has to be available.  Either install the package into your'
    print 'development environment or run "setup.py develop" to setup the'
    print 'metadata.  A virtualenv is recommended!'
    sys.exit(1)
del pkg_resources

if 'dev' in release:
    release = release.split('dev')[0] + 'dev'
version = '.'.join(release.split('.')[:2])

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyChefdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'PyChef.tex', u'PyChef Documentation',
   u'Noah Kantrowitz', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'pychef', u'PyChef Documentation',
     [u'Noah Kantrowitz'], 1)
]

########NEW FILE########
__FILENAME__ = versiontools_support
# Copyright (C) 2012 Linaro Limited
#
# Author: Zygmunt Krynicki <zygmunt.krynicki@linaro.org>
#
# This file is part of versiontools.
#
# versiontools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation
#
# versiontools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with versiontools.  If not, see <http://www.gnu.org/licenses/>.

"""
versiontools.versiontools_support
=================================

A small standalone module that allows any package to use versiontools.

Typically you should copy this file verbatim into your source distribution.

Historically versiontools was depending on a exotic feature of setuptools to
work. Setuptools has so-called setup-time dependencies, that is modules that
need to be downloaded and imported/interrogated for setup.py to run
successfully. Versiontools supports this by installing a handler for the
'version' keyword of the setup() function.

This approach was always a little annoying as this setuptools feature is rather
odd and very few other packages made any use of it. In the future the standard
tools for python packaging (especially in python3 world) this feature may be
removed or have equivalent thus rendering versiontools completely broken.

Currently the biggest practical issue is the apparent inability to prevent
setuptools from downloading packages designated as setup_requires. This is
discussed in this pip issue: https://github.com/pypa/pip/issues/410

To counter this issue I've redesigned versiontools to be a little smarter. The
old mode stays as-is for compatibility. The new mode works differently, without
the need for using setup_requires in your setup() call. Instead it requires
each package that uses versiontools to ship a verbatim copy of this module and
to import it in their setup.py script. This module helps setuptools find
package version in the standard PKG-INFO file that is created for all source
distributions. Remember that you only need this mode when you don't want to add
a dependency on versiontools. This will still allow you to use versiontools (in
a limited way) in your setup.py file.

Technically this module defines an improved version of one of
distutils.dist.DistributionMetadata class and monkey-patches distutils to use
it. To retain backward compatibility the new feature is only active when a
special version string is passed to the setup() call.
"""

__version__ = (1, 0, 0, "final", 0)

import distutils.dist
import distutils.errors


class VersiontoolsEnchancedDistributionMetadata(distutils.dist.DistributionMetadata):
    """
    A subclass of distutils.dist.DistributionMetadata that uses versiontools

    Typically you would not instantiate this class directly. It is constructed
    by distutils.dist.Distribution.__init__() method. Since there is no other
    way to do it, this module monkey-patches distutils to override the original
    version of DistributionMetadata
    """

    # Reference to the original class. This is only required because distutils
    # was created before the introduction of new-style classes to python.
    __base = distutils.dist.DistributionMetadata

    def get_version(self): 
        """
        Get distribution version.

        This method is enhanced compared to original distutils implementation.
        If the version string is set to a special value then instead of using
        the actual value the real version is obtained by querying versiontools.

        If versiontools package is not installed then the version is obtained
        from the standard section of the ``PKG-INFO`` file. This file is
        automatically created by any source distribution. This method is less
        useful as it cannot take advantage of version control information that
        is automatically loaded by versiontools. It has the advantage of not
        requiring versiontools installation and that it does not depend on
        ``setup_requires`` feature of ``setuptools``.
        """
        if (self.name is not None and self.version is not None
            and self.version.startswith(":versiontools:")):
            return (self.__get_live_version() or self.__get_frozen_version()
                    or self.__fail_to_get_any_version())
        else:
            return self.__base.get_version(self)

    def __get_live_version(self):
        """
        Get a live version string using versiontools
        """
        try:
            import versiontools
        except ImportError:
            return None
        else:
            return str(versiontools.Version.from_expression(self.name))

    def __get_frozen_version(self):
        """
        Get a fixed version string using an existing PKG-INFO file
        """
        try:
            return self.__base("PKG-INFO").version
        except IOError:
            return None

    def __fail_to_get_any_version(self):
        """
        Raise an informative exception
        """
        raise SystemExit(
"""This package requires versiontools for development or testing.

See http://versiontools.readthedocs.org/ for more information about
what versiontools is and why it is useful.

To install versiontools now please run:
    $ pip install versiontools

Note: versiontools works best when you have additional modules for
integrating with your preferred version control system. Refer to
the documentation for a full list of required modules.""")


# If DistributionMetadata is not a subclass of
# VersiontoolsEnhancedDistributionMetadata then monkey patch it. This should
# prevent a (odd) case of multiple imports of this module.
if not issubclass(
    distutils.dist.DistributionMetadata,
    VersiontoolsEnchancedDistributionMetadata):
    distutils.dist.DistributionMetadata = VersiontoolsEnchancedDistributionMetadata

########NEW FILE########
