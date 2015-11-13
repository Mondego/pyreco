__FILENAME__ = api
# -*- coding: utf-8 -*-

"""
heroku.api
~~~~~~~~~~

This module provides the basic API interface for Heroku.
"""

from .compat import json
from .helpers import is_collection
from .models import *
from .structures import KeyedListResource
from heroku.models import Feature
from requests.exceptions import HTTPError
import requests

HEROKU_URL = 'https://api.heroku.com'


class HerokuCore(object):
    """The core Heroku class."""
    def __init__(self, session=None):
        super(HerokuCore, self).__init__()
        if session is None:
            session = requests.session()

        #: The User's API Key.
        self._api_key = None
        self._api_key_verified = None
        self._heroku_url = HEROKU_URL
        self._session = session

        # We only want JSON back.
        self._session.headers.update({'Accept': 'application/json'})

    def __repr__(self):
        return '<heroku-core at 0x%x>' % (id(self))

    def authenticate(self, api_key):
        """Logs user into Heroku with given api_key."""
        self._api_key = api_key

        # Attach auth to session.
        self._session.auth = ('', self._api_key)

        return self._verify_api_key()

    def request_key(self, username, password):
        r = self._http_resource(
            method='POST',
            resource=('login'),
            data={'username': username, 'password': password}
        )
        r.raise_for_status()

        return json.loads(r.content.decode("utf-8")).get('api_key')

    @property
    def is_authenticated(self):
        if self._api_key_verified is None:
            return self._verify_api_key()
        else:
            return self._api_key_verified

    def _verify_api_key(self):
        r = self._session.get(self._url_for('apps'))

        self._api_key_verified = True if r.ok else False

        return self._api_key_verified

    def _url_for(self, *args):
        args = map(str, args)
        return '/'.join([self._heroku_url] + list(args))

    @staticmethod
    def _resource_serialize(o):
        """Returns JSON serialization of given object."""
        return json.dumps(o)

    @staticmethod
    def _resource_deserialize(s):
        """Returns dict deserialization of a given JSON string."""

        try:
            return json.loads(s)
        except ValueError:
            raise ResponseError('The API Response was not valid.')

    def _http_resource(self, method, resource, params=None, data=None):
        """Makes an HTTP request."""

        if not is_collection(resource):
            resource = [resource]

        url = self._url_for(*resource)
        r = self._session.request(method, url, params=params, data=data)

        if r.status_code == 422:
            http_error = HTTPError('%s Client Error: %s' %
                                   (r.status_code, r.content.decode("utf-8")))
            http_error.response = r
            raise http_error

        r.raise_for_status()

        return r

    def _get_resource(self, resource, obj, params=None, **kwargs):
        """Returns a mapped object from an HTTP resource."""
        r = self._http_resource('GET', resource, params=params)
        item = self._resource_deserialize(r.content.decode("utf-8"))

        return obj.new_from_dict(item, h=self, **kwargs)

    def _get_resources(self, resource, obj, params=None, map=None, **kwargs):
        """Returns a list of mapped objects from an HTTP resource."""
        r = self._http_resource('GET', resource, params=params)
        d_items = self._resource_deserialize(r.content.decode("utf-8"))

        items =  [obj.new_from_dict(item, h=self, **kwargs) for item in d_items]

        if map is None:
            map = KeyedListResource

        list_resource = map(items=items)
        list_resource._h = self
        list_resource._obj = obj
        list_resource._kwargs = kwargs

        return list_resource


class Heroku(HerokuCore):
    """The main Heroku class."""

    def __init__(self, session=None):
        super(Heroku, self).__init__(session=session)

    def __repr__(self):
        return '<heroku-client at 0x%x>' % (id(self))

    @property
    def account(self):
        return self._get_resource(('account'), Account)

    @property
    def addons(self):
        return self._get_resources(('addons'), Addon)

    @property
    def apps(self):
        return self._get_resources(('apps'), App)

    @property
    def keys(self):
        return self._get_resources(('user', 'keys'), Key, map=SSHKeyListResource)

    @property
    def labs(self):
        return self._get_resources(('features'), Feature, map=filtered_key_list_resource_factory(lambda obj: obj.kind == 'user'))



class ResponseError(ValueError):
    """The API Response was unexpected."""

########NEW FILE########
__FILENAME__ = compat
# -*- coding: utf-8 -*-

"""
heroku.compat
~~~~~~~~~~~~~

Compatiblity for heroku.py.
"""

try:
    import json
except ImportError:
    import simplejson as json
########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

"""
heroku.core
~~~~~~~~~~~

This module provides the base entrypoint for heroku.py.
"""

from .api import Heroku

def from_key(api_key, **kwargs):
    """Returns an authenticated Heroku instance, via API Key."""

    h = Heroku(**kwargs)

    # Login.
    h.authenticate(api_key)

    return h

def from_pass(username, password):
    """Returns an authenticated Heroku instance, via password."""

    key = get_key(username, password)
    return from_key(key)

def get_key(username, password):
    """Returns an API Key, fetched via password."""

    return Heroku().request_key(username, password)
########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-

"""
heroku.helpers
~~~~~~~~~~~~~~

This module contians the helpers.
"""

from datetime import datetime

from dateutil.parser import parse as parse_datetime

import sys

if sys.version_info > (3, 0):
    basestring = (str, bytes)

def is_collection(obj):
    """Tests if an object is a collection."""

    col = getattr(obj, '__getitem__', False)
    val = False if (not col) else True

    if isinstance(obj, basestring):
        val = False

    return val



# from kennethreitz/python-github3
def to_python(obj,
    in_dict,
    str_keys=None,
    date_keys=None,
    int_keys=None,
    object_map=None,
    bool_keys=None,
    dict_keys=None,
    **kwargs):
    """Extends a given object for API Consumption.

    :param obj: Object to extend.
    :param in_dict: Dict to extract data from.
    :param string_keys: List of in_dict keys that will be extracted as strings.
    :param date_keys: List of in_dict keys that will be extrad as datetimes.
    :param object_map: Dict of {key, obj} map, for nested object results.
    """

    d = dict()

    if str_keys:
        for in_key in str_keys:
            d[in_key] = in_dict.get(in_key)

    if date_keys:
        for in_key in date_keys:
            in_date = in_dict.get(in_key)
            try:
                out_date = parse_datetime(in_date)
            except TypeError as e:
                raise e
                out_date = None

            d[in_key] = out_date

    if int_keys:
        for in_key in int_keys:
            if (in_dict is not None) and (in_dict.get(in_key) is not None):
                d[in_key] = int(in_dict.get(in_key))

    if bool_keys:
        for in_key in bool_keys:
            if in_dict.get(in_key) is not None:
                d[in_key] = bool(in_dict.get(in_key))

    if dict_keys:
        for in_key in dict_keys:
            if in_dict.get(in_key) is not None:
                d[in_key] = dict(in_dict.get(in_key))

    if object_map:
        for (k, v) in object_map.items():
            if in_dict.get(k):
                d[k] = v.new_from_dict(in_dict.get(k))

    obj.__dict__.update(d)
    obj.__dict__.update(kwargs)

    # Save the dictionary, for write comparisons.
    # obj._cache = d
    # obj.__cache = in_dict

    return obj


# from kennethreitz/python-github3
def to_api(in_dict, int_keys=None, date_keys=None, bool_keys=None):
    """Extends a given object for API Production."""

    # Cast all int_keys to int()
    if int_keys:
        for in_key in int_keys:
            if (in_key in in_dict) and (in_dict.get(in_key, None) is not None):
                in_dict[in_key] = int(in_dict[in_key])

    # Cast all date_keys to datetime.isoformat
    if date_keys:
        for in_key in date_keys:
            if (in_key in in_dict) and (in_dict.get(in_key, None) is not None):

                _from = in_dict[in_key]

                if isinstance(_from, basestring):
                    dtime = parse_datetime(_from)

                elif isinstance(_from, datetime):
                    dtime = _from

                in_dict[in_key] = dtime.isoformat()

            elif (in_key in in_dict) and in_dict.get(in_key, None) is None:
                del in_dict[in_key]

    # Remove all Nones
    for k, v in in_dict.items():
        if v is None:
            del in_dict[k]

    return in_dict

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

"""
heroku.models
~~~~~~~~~~~~~

This module contains the models that comprise the Heroku API.
"""

from .helpers import to_python
from .structures import *
import json
import requests
import sys

if sys.version_info > (3, 0):
    from urllib.parse import quote
else:
    from urllib import quote


class BaseResource(object):

    _strs = []
    _ints = []
    _dates = []
    _bools = []
    _dicts = []
    _map = {}
    _pks = []

    def __init__(self):
        self._bootstrap()
        self._h = None
        super(BaseResource, self).__init__()

    def __repr__(self):
        return "<resource '{0}'>".format(self._id)

    def _bootstrap(self):
        """Bootstraps the model object based on configured values."""

        for attr in self._keys():
            setattr(self, attr, None)

    def _keys(self):
        return self._strs + self._ints + self._dates + self._bools + list(self._map.keys())

    @property
    def _id(self):
        try:
            return getattr(self, self._pks[0])
        except IndexError:
            return None

    @property
    def _ids(self):
        """The list of primary keys to validate against."""
        for pk in self._pks:
            yield getattr(self, pk)

        for pk in self._pks:

            try:
                yield str(getattr(self, pk))
            except ValueError:
                pass


    def dict(self):
        d = dict()
        for k in self.keys():
            d[k] = self.__dict__.get(k)

        return d

    @classmethod
    def new_from_dict(cls, d, h=None, **kwargs):

        d = to_python(
            obj=cls(),
            in_dict=d,
            str_keys=cls._strs,
            int_keys=cls._ints,
            date_keys=cls._dates,
            bool_keys=cls._bools,
            dict_keys= cls._dicts,
            object_map=cls._map,
            _h = h
        )

        d.__dict__.update(kwargs)

        return d


class Account(BaseResource):

    _strs = ['email' ,'id']
    _bools = ['allow_tracking', 'beta', 'confirmed', 'verified']
    _pks = ['id']
    _dates = ['confirmed_at', 'created_at', 'last_login', 'updated_at']

    def __repr__(self):
        return "<account '{0}'>".format(self.email)


class AvailableAddon(BaseResource):
    """Heroku Addon."""

    _strs = ['name', 'description', 'url', 'state']
    _bools = ['beta',]
    _pks = ['name']

    def __repr__(self):
        return "<available-addon '{0}'>".format(self.name)

    @property
    def type(self):
        return self.name.split(':')[0]


class Addon(AvailableAddon):
    """Heroku Addon."""

    _pks = ['name', 'type']
    _strs = ['name', 'description', 'url', 'state', 'attachment_name']

    def __repr__(self):
        return "<addon '{0}'>".format(self.name)

    def delete(self):
        addon_name = self.name
        try:
            addon_name = self.attachment_name
        except:
            pass
        r = self._h._http_resource(
            method='DELETE',
            resource=('apps', self.app.name, 'addons', addon_name)
        )
        return r.ok

    def new(self, name, params=None):
        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.app.name, 'addons', name),
            params=params
        )
        r.raise_for_status()
        return self.app.addons[name]

    def upgrade(self, name, params=None):
        """Upgrades an addon to the given tier."""
        # Allow non-namespaced upgrades. (e.g. advanced vs logging:advanced)
        if ':' not in name:
            name = '{0}:{1}'.format(self.type, name)

        r = self._h._http_resource(
            method='PUT',
            resource=('apps', self.app.name, 'addons', quote(name)),
            params=params,
            data=' '   # Server weirdness.
        )
        r.raise_for_status()
        return self.app.addons[name]


class App(BaseResource):
    """Heroku App."""

    _strs = ['name', 'create_status', 'stack', 'repo_migrate_status']
    _ints = ['id', 'slug_size', 'repo_size', 'dynos', 'workers']
    _dates = ['created_at',]
    _pks = ['name', 'id']

    def __init__(self):
        super(App, self).__init__()

    def __repr__(self):
        return "<app '{0}'>".format(self.name)

    def new(self, name=None, stack='cedar'):
        """Creates a new app."""

        payload = {}

        if name:
            payload['app[name]'] = name

        if stack:
            payload['app[stack]'] = stack

        r = self._h._http_resource(
            method='POST',
            resource=('apps',),
            data=payload
        )

        name = json.loads(r.content).get('name')
        return self._h.apps.get(name)

    @property
    def addons(self):
        return self._h._get_resources(
            resource=('apps', self.name, 'addons'),
            obj=Addon, app=self
        )

    @property
    def collaborators(self):
        """The collaborators for this app."""
        return self._h._get_resources(
            resource=('apps', self.name, 'collaborators'),
            obj=Collaborator, app=self
        )

    @property
    def domains(self):
        """The domains for this app."""
        return self._h._get_resources(
            resource=('apps', self.name, 'domains'),
            obj=Domain, app=self
        )

    @property
    def releases(self):
        """The releases for this app."""
        return self._h._get_resources(
            resource=('apps', self.name, 'releases'),
            obj=Release, app=self
        )

    @property
    def processes(self):
        """The proccesses for this app."""
        return self._h._get_resources(
            resource=('apps', self.name, 'ps'),
            obj=Process, app=self, map=ProcessListResource
        )

    @property
    def config(self):
        """The envs for this app."""

        return self._h._get_resource(
            resource=('apps', self.name, 'config_vars'),
            obj=ConfigVars, app=self
        )

    @property
    def info(self):
        """Returns current info for this app."""

        return self._h._get_resource(
            resource=('apps', self.name),
            obj=App,
        )

    @property
    def labs(self):
        return self._h._get_resources(
            resource=('features'),
            obj=Feature, params={'app': self.name}, app=self, map=filtered_key_list_resource_factory(lambda item: item.kind == 'app')
        )

    def rollback(self, release):
        """Rolls back the release to the given version."""
        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.name, 'releases'),
            data={'rollback': release}
        )
        return self.releases[-1]


    def rename(self, name):
        """Renames app to given name."""

        r = self._h._http_resource(
            method='PUT',
            resource=('apps', self.name),
            data={'app[name]': name}
        )
        return r.ok

    def transfer(self, user):
        """Transfers app to given username's account."""

        r = self._h._http_resource(
            method='PUT',
            resource=('apps', self.name),
            data={'app[transfer_owner]': user}
        )
        return r.ok

    def maintenance(self, on=True):
        """Toggles maintenance mode."""

        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.name, 'server', 'maintenance'),
            data={'maintenance_mode': int(on)}
        )
        return r.ok

    def destroy(self):
        """Destoys the app. Do be careful."""

        r = self._h._http_resource(
            method='DELETE',
            resource=('apps', self.name)
        )
        return r.ok

    def logs(self, num=None, source=None, ps=None, tail=False):
        """Returns the requested log."""

        # Bootstrap payload package.
        payload = {'logplex': 'true'}

        if num:
            payload['num'] = num

        if source:
            payload['source'] = source

        if ps:
            payload['ps'] = ps

        if tail:
            payload['tail'] = 1

        # Grab the URL of the logplex endpoint.
        r = self._h._http_resource(
            method='GET',
            resource=('apps', self.name, 'logs'),
            data=payload
        )

        # Grab the actual logs.
        r = requests.get(r.content.decode("utf-8"), verify=False, stream=True)

        if not tail:
            return r.content
        else:
            # Return line iterator for tail!
            return r.iter_lines()



class Collaborator(BaseResource):
    """Heroku Collaborator."""

    _strs = ['access', 'email']
    _pks = ['email']

    def __init__(self):
        self.app = None
        super(Collaborator, self).__init__()

    def __repr__(self):
        return "<collaborator '{0}'>".format(self.email)

    def new(self, email):
        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.app.name, 'collaborators'),
            data={'collaborator[email]': email}
        )

        return self.app.collaborators[email]

    def delete(self):
        r = self._h._http_resource(
            method='DELETE',
            resource=('apps', self.app.name, 'collaborators', self.email)
        )

        return r.ok


class ConfigVars(object):
    """Heroku ConfigVars."""

    def __init__(self):

        self.data = {}
        self.app = None
        self._h = None

        super(ConfigVars, self).__init__()

    def __repr__(self):
        return repr(self.data)

    def __setitem__(self, key, value):
        # API expects JSON.
        payload = json.dumps({key: value})

        r = self._h._http_resource(
            method='PUT',
            resource=('apps', self.app.name, 'config_vars'),
            data=payload
        )

        return r.ok

    def __delitem__(self, key):
        r = self._h._http_resource(
            method='DELETE',
            resource=('apps', self.app.name, 'config_vars', key),
        )

        return r.ok

    @classmethod
    def new_from_dict(cls, d, h=None, **kwargs):
        # Override normal operation because of crazy api.
        c = cls()
        c.data = d
        c._h = h
        c.app = kwargs.get('app')

        return c


class Domain(BaseResource):
    """Heroku Domain."""

    _ints = ['id', 'app_id', ]
    _strs = ['domain', 'base_domain', 'default']
    _dates = ['created_at', 'updated_at']
    _pks = ['domain', 'id']


    def __init__(self):
        self.app = None
        super(Domain, self).__init__()

    def __repr__(self):
        return "<domain '{0}'>".format(self.domain)

    def delete(self):
        r = self._h._http_resource(
            method='DELETE',
            resource=('apps', self.app.name, 'domains', self.domain)
        )

        return r.ok

    def new(self, name):
        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.app.name, 'domains'),
            data={'domain_name[domain]': name}
        )

        return self.app.domains[name]


class Key(BaseResource):
    """Heroku SSH Key."""

    _strs = ['email', 'contents']
    _pks = ['id',]

    def __init__(self):
        super(Key, self).__init__()

    def __repr__(self):
        return "<key '{0}'>".format(self.id)

    @property
    def id(self):
        """Returns the username@hostname description field of the key."""

        return self.contents.split()[-1]

    def new(self, key):
        r = self._h._http_resource(
            method='POST',
            resource=('user', 'keys'),
            data=key
        )

        return self._h.keys.get(key.split()[-1])

    def delete(self):
        """Deletes the key."""
        r = self._h._http_resource(
            method='DELETE',
            resource=('user', 'keys', self.id)
        )

        r.raise_for_status()


class Log(BaseResource):
    def __init__(self):
        self.app = None
        super(Log, self).__init__()


class Process(BaseResource):

    _strs = [
        'app_name', 'slug', 'command', 'upid', 'process', 'action',
        'rendezvous_url', 'pretty_state', 'state'
    ]

    _ints = ['elapsed']
    _bools = ['attached']
    _dates = []
    _pks = ['process', 'upid']


    def __init__(self):
        self.app = None
        super(Process, self).__init__()

    def __repr__(self):
        return "<process '{0}'>".format(self.process)

    def new(self, command, attach=""):
        """
        Creates a new Process
        Attach: If attach=True it will return a rendezvous connection point, for streaming stdout/stderr
        Command: The actual command it will run
        """
        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.app.name, 'ps',),
            data={'attach': attach, 'command': command}
        )

        r.raise_for_status()
        return self.app.processes[r.json['process']]

    @property
    def type(self):
        return self.process.split('.')[0]

    def restart(self, all=False):
        """Restarts the given process."""

        if all:
            data = {'type': self.type}

        else:
            data = {'ps': self.process}

        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.app.name, 'ps', 'restart'),
            data=data
        )

        r.raise_for_status()

    def stop(self, all=False):
        """Stops the given process."""

        if all:
            data = {'type': self.type}

        else:
            data = {'ps': self.process}

        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.app.name, 'ps', 'stop'),
            data=data
        )

        r.raise_for_status()

    def scale(self, quantity):
        """Scales the given process to the given number of dynos."""

        r = self._h._http_resource(
            method='POST',
            resource=('apps', self.app.name, 'ps', 'scale'),
            data={'type': self.type, 'qty': quantity}
        )

        r.raise_for_status()

        if self.type in self.app.processes:
            return self.app.processes[self.type]
        else:
            return ProcessListResource()



class Release(BaseResource):
    _strs = ['name', 'descr', 'user', 'commit', 'addons']
    _dicts = ['env', 'pstable']
    _dates = ['created_at']
    _pks = ['name']

    def __init__(self):
        self.app = None
        super(Release, self).__init__()

    def __repr__(self):
        return "<release '{0}'>".format(self.name)

    def rollback(self):
        """Rolls back the application to this release."""

        return self.app.rollback(self.name)



class Stack(BaseResource):
    def __init__(self):
        super(Stack, self).__init__()


class Feature(BaseResource):
    _strs = ['name', 'kind', 'summary', 'docs',]
    _bools = ['enabled']
    _pks = ['name']

    def __init__(self):
        self.app = None
        super(Feature, self).__init__()

    def __repr__(self):
        return "<feature '{0}'>".format(self.name)

    def enable(self):
        r = self._h._http_resource(
            method='POST',
            resource=('features', self.name),
            params={'app': self.app.name if self.app else ''}
        )
        return r.ok

    def disable(self):
        r = self._h._http_resource(
            method='DELETE',
            resource=('features', self.name),
            params={'app': self.app.name if self.app else ''}
        )
        return r.ok

########NEW FILE########
__FILENAME__ = structures
# -*- coding: utf-8 -*-

"""
heroku.structures
~~~~~~~~~~~~~~~~~

This module contains the specific Heroku.py data types.
"""


class KeyedListResource(object):
    """docstring for ListResource"""

    def __init__(self, items=None):
        super(KeyedListResource, self).__init__()

        self._h = None
        self._items = items or list()
        self._obj = None
        self._kwargs = {}

    def __repr__(self):
        return repr(self._items)

    def __iter__(self):
        for item in self._items:
            yield item

    def __getitem__(self, key):

        # Support index operators.
        if isinstance(key, int):
            if abs(key) <= len(self._items):
                return self._items[key]

        v = self.get(key)

        if v is None:
            raise KeyError(key)

        return v

    def add(self, *args, **kwargs):

        try:
            return self[0].new(*args, **kwargs)
        except IndexError:
            o = self._obj()
            o._h = self._h
            o.__dict__.update(self._kwargs)

            return o.new(*args, **kwargs)


    def remove(self, key):
        if hasattr(self[0], 'delete'):
            return self[key].delete()

    def get(self, key):
        for item in self:
            if key in item._ids:
                return item

    def __delitem__(self, key):
        self[key].delete()



class ProcessListResource(KeyedListResource):
    """KeyedListResource with basic filtering for process types."""

    def __init__(self, *args, **kwargs):
        super(ProcessListResource, self).__init__(*args, **kwargs)

    def __getitem__(self, key):

        try:
            return super(ProcessListResource, self).__getitem__(key)
        except KeyError as why:

            c = [p for p in self._items if key == p.type]

            if c:
                return ProcessTypeListResource(items=c)
            else:
                raise why


class ProcessTypeListResource(ProcessListResource):
    """KeyedListResource with basic filtering for process types."""

    def __init__(self, *args, **kwargs):

        super(ProcessTypeListResource, self).__init__(*args, **kwargs)

    def scale(self, quantity):
        return self[0].scale(quantity)



class SSHKeyListResource(KeyedListResource):
    """KeyedListResource with clearing for ssh keys."""

    def __init__(self, *args, **kwargs):

        super(SSHKeyListResource, self).__init__(*args, **kwargs)

    def clear(self):
        """Removes all SSH keys from a user's system."""

        r = self._h._http_resource(
            method='DELETE',
            resource=('user', 'keys'),
        )

        return r.ok


class FilteredListResource(KeyedListResource):
    filter_func = staticmethod(lambda item: True)
    
    def __init__(self, items=None):
        items = [item for item in items if self.filter_func(item)] if items else []
        super(FilteredListResource, self).__init__(items)

def filtered_key_list_resource_factory(filter_func):
    return type('FilteredListResource', (FilteredListResource,), {'filter_func': staticmethod(filter_func)})

########NEW FILE########
