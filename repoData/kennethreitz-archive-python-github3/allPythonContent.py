__FILENAME__ = api
# -*- coding: utf-8 -*-

"""
github3.api
~~~~~~~~~~

This module provides the basic API interface for Github.
"""

import json

import requests
from .helpers import is_collection
from .structures import KeyedListResource
from .models import *

GITHUB_URL = 'https://api.github.com'


class GithubCore(object):
    """The core Github class."""
    def __init__(self):
        super(GithubCore, self).__init__()

        #: The User's API Key.
        self._api_key = None
        self._api_key_verified = None
        self._s = requests.session()
        self._github_url = GITHUB_URL

        # We only want JSON back.
        self._s.headers.update({'Accept': 'application/json'})

    def __repr__(self):
        return '<github-core at 0x%x>' % (id(self))

    def login(self, username, password):
        """Logs user into Github with given credentials."""

        # Attach auth to session.
        self._s.auth = (username.password)

        return True

    @property
    def is_authenticated(self):
        if self._api_key_verified is None:
            return self._verify_api_key()
        else:
            return self._api_key_verified

    def _url_for(self, *args):
        args = map(str, args)
        return '/'.join([self._github_url] + list(args))

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
        r = self._s.request(method, url, params=params, data=data)

        r.raise_for_status()

        return r

    def _get_resource(self, resource, obj, params=None, **kwargs):
        """Returns a mapped object from an HTTP resource."""
        r = self._http_resource('GET', resource, params=params)
        item = self._resource_deserialize(r.content)

        return obj.new_from_dict(item, h=self, **kwargs)

    def _get_resources(self, resource, obj, params=None, map=None, **kwargs):
        """Returns a list of mapped objects from an HTTP resource."""
        r = self._http_resource('GET', resource, params=params)
        d_items = self._resource_deserialize(r.content)

        items =  [obj.new_from_dict(item, h=self, **kwargs) for item in d_items]

        if map is None:
            map = KeyedListResource

        list_resource = map(items=items)
        list_resource._h = self
        list_resource._obj = obj

        return list_resource


class Github(GithubCore):
    """The main Github class."""

    def __init__(self):
        super(Github, self).__init__()

    def __repr__(self):
        return '<github-client at 0x%x>' % (id(self))

    # @property
    # def addons(self):
    #     return self._get_resources(('addons'), Addon)

    # @property
    # def apps(self):
    #     return self._get_resources(('apps'), App)

    # @property
    # def keys(self):
    #     return self._get_resources(('user', 'keys'), Key, map=SSHKeyListResource)


class ResponseError(ValueError):
    """The API Response was unexpected."""
########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

"""
github3.core
~~~~~~~~~~~~~

This module provides the base entrypoint for github3.
"""

from .api import Github

def login(username, password):
    """Returns an authenticated Github instance, via API Key."""

    gh = Github()

    # Login.
    gh.login(username, password)

    return gh

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-

"""
github3.helpers
~~~~~~~~~~~~~~~

This module contians the helpers.
"""

from datetime import datetime

from dateutil.parser import parse as parse_datetime

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
            except TypeError, e:
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
    obj._cache = d
    obj.__cache = in_dict

    return obj


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
github3.models
~~~~~~~~~~~~~~

This module contains the models that comprise the Github API.
"""

import json
from urllib import quote

import requests
from .helpers import to_python
from .structures import *


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
        return self._strs + self._ints + self._dates + self._bools + self._map.keys()

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

    def logs(self, num=None, source=None, tail=False):
        """Returns the requested log."""

        # Bootstrap payload package.
        payload = {'logplex': 'true'}

        if num:
            payload['num'] = num

        if source:
            payload['source'] = source

        if tail:
            payload['tail'] = 1

        # Grab the URL of the logplex endpoint.
        r = self._h._http_resource(
            method='GET',
            resource=('apps', self.name, 'logs'),
            data=payload
        )

        # Grab the actual logs.
        r = requests.get(r.content)

        if not tail:
            return r.content
        else:
            # Return line iterator for tail!
            return r.iter_lines()


########NEW FILE########
__FILENAME__ = structures
# -*- coding: utf-8 -*-

"""
github3.structures
~~~~~~~~~~~~~~~~~

This module contains the specific github data types.
"""


class KeyedListResource(object):
    """docstring for ListResource"""

    def __init__(self, items=None):
        super(KeyedListResource, self).__init__()

        self._h = None
        self._items = items or list()
        self._obj = None

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



# class ProcessListResource(KeyedListResource):
#     """KeyedListResource with basic filtering for process types."""

#     def __init__(self, *args, **kwargs):
#         super(ProcessListResource, self).__init__(*args, **kwargs)

#     def __getitem__(self, key):

#         try:
#             return super(ProcessListResource, self).__getitem__(key)
#         except KeyError, why:

#             c = [p for p in self._items if key == p.type]

#             if c:
#                 return ProcessTypeListResource(items=c)
#             else:
#                 raise why


# class ProcessTypeListResource(ProcessListResource):
#     """KeyedListResource with basic filtering for process types."""

#     def __init__(self, *args, **kwargs):

#         super(ProcessTypeListResource, self).__init__(*args, **kwargs)

#     def scale(self, quantity):
#         return self[0].scale(quantity)



# class SSHKeyListResource(KeyedListResource):
#     """KeyedListResource with clearing for ssh keys."""

#     def __init__(self, *args, **kwargs):

#         super(SSHKeyListResource, self).__init__(*args, **kwargs)

#     def clear(self):
#         """Removes all SSH keys from a user's system."""

#         r = self._h._http_resource(
#             method='DELETE',
#             resource=('user', 'keys'),
#         )

#         return r.ok





########NEW FILE########
