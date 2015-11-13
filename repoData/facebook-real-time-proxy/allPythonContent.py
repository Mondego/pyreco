__FILENAME__ = apps
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" A container for app-specific data and functionality."""
import threading
import logging


class App(object):
    """ Manages Facebook Application-specific settings and policies

    This class serves two purposes. First, it serves as a repository of
    information about an application (such as the users we have seen for it
    and the configuration settings for it). Second, it exposes two methods
    which are used in making cache-eligibilty decisions in ProxyRequestHandler,
     check_user and check_request. check_user adds the requestor to the app's
    list of seen users, and then sees if the user whose data we're requesting
    has been seen before (only users who we are sure have added an app will be
    updated by realtime updates, so we only cache requests for those users'
    data. check_request ensures that the request is only for data which is
    part of the app's realtime update subscription, and is not blacklisted.
    """

    def __init__(self, config):
        self.id = config['app_id']
        self.bad_fields = set()
        self.bad_conns = set()
        self.good_fields = set()
        self.good_conns = set()
        self.users = set()
        self.lock = threading.Lock()
        self.cred = config.get('app_cred')
        self.secret = config.get('app_secret')
        if 'blacklist_fields' in config:
            self.bad_fields.update(config['blacklist_fields'])
        if 'blacklist_connections' in config:
            self.bad_conns.update(config['blacklist_connections'])
        if 'whitelist_fields' in config:
            self.good_fields = set(config['whitelist_fields'])
        if 'whitelist_connections' in config:
            self.good_conns = set(config['whitelist_connections'])
        self.good_fields -= self.bad_fields
        self.good_conns -= self.bad_conns

    def check_user(self, requestor, requestee, default=None):
        """ Check a request's users.

        Adds the requestor to the known users for the app, and checks
        if the requestee is a known user of the app. Also adds the user
        to the default app, since we'll get updates for them.
        """
        self.lock.acquire()
        self.users.add(requestor)
        ok = requestee in self.users
        self.lock.release()

        # if this isn't the default app, also add the user to the default app
        if default != self and default != None:
            default.check_user(requestor, requestee)

        return ok

    def check_request(self, pathparts, fields=None):
        """ Returns whether a request is cacheable."""
        if not fields:
            fields = []
        if len(pathparts) == 1:  # this is a request for direct profile fields
            if len(set(fields) - self.good_fields) == 0:
                return True
            logging.info('got fields ' + repr(fields) + ' but only '
                         + repr(self.good_fields) + ' is ok')
        elif len(pathparts) == 2:  # this is a request for a connection
            return pathparts[1] in self.good_conns
        return False  # safety: if we're not certain about it, fall back to
                      # passthrough behavior


def init(configapps):
    """ Initializes the mapping of app ids to the App objects from config"""
    apps = dict((str(x['app_id']), App(x)) for x in configapps)
    if 'default' not in apps:  # Add the default app if settings haven't been
                               # defined for it already.
        default_app = App({'app_id': 'default'})
        intersect = lambda x, y: x & y
        default_app.good_fields = reduce(intersect, [x.good_fields for x
                                                     in apps.itervalues()])
        default_app.good_conns = reduce(intersect, [x.good_conns for x in
                                                    apps.itervalues()])
        apps['default'] = default_app
    return apps


def get_app(app_id, app_set):
    """Look up the given app in the app_set, using the default if needed."""
    if app_id in app_set:
        return app_set[app_id]
    if 'default' in app_set:
        return app_set['default']
    return None

########NEW FILE########
__FILENAME__ = cache
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" This module simply contains the ProxyLruCache class."""
import urllib
import json
import threading
import logging
from fbproxy.lru import LRU
from fbproxy.requesthandler import ProxyRequestHandler
from fbproxy.hashdict import HashedDictionary


SCALAR_TABLE = 1
VECTOR_TABLE = 2


class ProxyLruCache(object):
    """Implement a cache for Facebook Graph API Requests.

    This cache stores entries in a multi-tiered fashion. First requests are
    indexed by the app and path (aka the part of the URL before the ?). At most
    'size' such entries are maintained in an LRU cache. Underneath this, up to
    `width` views of this URL are stored (again in an LRU). Finally, underneath
    this is a mapping from access-token-less query strings to results.

    This implementation can be replaced. The relevant functions to implement
    are handle_request and invalidate.
    """
    def __init__(self, size):
        self.cache = LRU(size)
        self.lock = threading.Lock()

    def handle_request(self, query, path, querystring, app, server):
        """ handle a cacheable request. returns (status, headers, data) tuple.

        If it is found in the cache, just return the result directly from the
        cache. Otherwise make a request to the graph api server and return the
        result. If it is a 200 OK response, it gets saved in the cache, also.
        """
        accesstoken_parts = None
        accesstoken = None
        if 'access_token' in query:
            accesstoken = query['access_token'][0]
            accesstoken_parts = ProxyRequestHandler.parse_access_token(
                    query['access_token'][0])
            del query['access_token']
        appid = accesstoken_parts[0] if accesstoken_parts else '0'
        uid = accesstoken_parts[2] if accesstoken_parts else '0'

        usetable = '/' not in path  # use table for user directly
        # usetable = False
        fields = None
        if 'fields' in query and usetable:
            fields = query['fields'][0]
            del query['fields']

        key = path + "__" + appid
        subkey = uid + "__" + urllib.urlencode(query)
        value = None
        hashdict = None
        logging.debug('cache handling request with key ' + key +
                      ', and subkey ' + subkey + ' for user ' + uid)

        self.lock.acquire()
        if key in self.cache:
            # step 1. acquire the dictionary
            hashdict = self.cache[key]
            if subkey in hashdict:  # step 2: grab the relevant data if there
                value = hashdict[subkey]
        else:
            hashdict = HashedDictionary()
            self.cache[key] = hashdict
        self.lock.release()

        if value:  # step 3: return the data if available
            if usetable:
                (statusline, headers, table) = value
                return (statusline, headers, get_response(table, fields))
            else:
                return value

        # at this point, we have a cache miss
        # step 4: fetch data
        if usetable:
            (statusline, headers, table, status) = _fetchtable(query,
                    path, accesstoken, app, hashdict, subkey, server)
            # step 4.5: form a response body from the table
            if status != 200:
                # fetchtable returns body instead of table on error
                body = table
            else:
                for header in headers:
                    if header[0].upper() == 'CONTENT-LENGTH':
                        headers.remove(header)
                        break
                body = get_response(table, fields)
        else:
            (statusline, headers, body, status) = fetch_tuple(path,
                    querystring, server)
            if status == 200:
                hashdict[subkey] = ((statusline, headers, body), body)
        return (statusline, headers, body)

    def invalidate(self, appid, url):
        """ Invalidate a URL in an application's context.

        This removes all cache entries for the given applicaton and path.
        """
        key = url + "__" + appid
        logging.debug('invalidating' + key)
        self.lock.acquire()
        if key in self.cache:
            del self.cache[key]
        # also invalidate the URL for the null app
        key = url + "__0"
        if key in self.cache:
            del self.cache[key]
        self.lock.release()


def _response_to_table(body):
    """ Takes a JSON response body and converts into a key-value store."""
    table = {}
    try:
        bodyjson = json.loads(body)
        for (key, value) in bodyjson.iteritems():
            table[key] = value
    except ValueError:
        pass
    return table


def get_response(table, fields):
    """ Fetches the given fields from the table and returns it as JSON."""
    ret = {}
    if fields:
        fieldlist = fields.split(',')
        for field in fieldlist:
            if field in table:
                ret[field] = table[field]
    else:
        for key, value in table.iteritems():
            if key[0] != '_':
                ret[key] = value

    return json.dumps(ret)


def _fetchtable(query, path, accesstoken, app, hashdict, key, server):
    """ Fetches the requested object, returning it as a field-value table.

    In addition, it will make use of the hash dict to avoid parsing the
    body if possible (and store the response there as appropriate.
    """
    fields = ','.join(app.good_fields)
    query['fields'] = fields
    query['access_token'] = accesstoken
    (statusline, headers, data, statuscode) = fetch_tuple(path, \
            urllib.urlencode(query), server)
    # error = send the raw response instead of a table
    if statuscode != 200:
        return (statusline, headers, data, statuscode)
    # hash miss = have to parse the file
    elif not hashdict.contains_hash(data):
        hashdict[key] = ((statusline, headers, _response_to_table(data)), data)
    else:  # statuscode == 200 and hashdict has the hash of the data
        hashdict[key] = (None, data)  # the stored data arg is ignored
                                      # since the hash is in the dict
    (statusline, headers, table) = hashdict[key]
    return (statusline, headers, table, 200)


def fetch_tuple(path, querystring, server):
    """ Fetches the requested object as (status, headers, body, status num)"""
    response = ProxyRequestHandler.fetchurl('GET', path, querystring, server)
    statusline = str(response.status) + " " + response.reason
    headers = response.getheaders()
    body = response.read()
    response.close()
    return (statusline, headers, body, response.status)

########NEW FILE########
__FILENAME__ = config
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" Central configuration location for the proxy.

The load function must be called before attempting to use this module."""
import imp


def load(cfgfile):
    """ Loads the specified configuration into this module."""
    local_config = imp.load_source('local_config', cfgfile)
    mydict = globals()

    for key in local_config.__dict__:
        mydict[key] = local_config.__dict__[key]

########NEW FILE########
__FILENAME__ = hashdict
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" This module contains the HashedDictionary class.

This is a smart dictionary which stores values that have identical hashes only
once, to save space.
"""

import hashlib


class HashedDictionary(object):
    """ A smarter dictionary. Stores responses with identical body only once.

    This dictionary stores (nonhashed_data, hashed_data) tuples, hashing by
    body. The goal is to only store responses which are identical once. We
    do this by mapping from the key to a hash of the response. From there,
    we access the actual response in a second dictionary. Note that parts
    of requests are significant, while others are not. Consumers are expected
    to partition their data into nonhashed and hashed data for insertion and
    retrieval.
    """
    def __init__(self):
        self.content = {}
        self.keymap = {}

    def __getitem__(self, key):
        """ Fetch the tuple for the given key."""
        if key in self.keymap:
            valhash = self.keymap[key]
            return self.content[valhash]
        return None

    def __setitem__(self, key, data):
        """ Store the given response in the dictionary with the given key.

        Takes values as (data, hashed_data). hashes hash_data, and then stores
        data if that hash is unique. If that hash is not unique, then this will
        point key at the existing entry with that hash.
        """
        (stored_data, valhashed) = data
        valhash = hashlib.sha1(valhashed).digest()
        self.keymap[key] = valhash
        if not valhash in self.content:
            self.content[valhash] = stored_data

    def __contains__(self, key):
        return key in self.keymap

    def contains_hash(self, valhashdata):
        """ Determines if the data has a matching hash already in the dict."""
        return hashlib.sha1(valhashdata).digest() in self.content

########NEW FILE########
__FILENAME__ = launcher
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" main driver for the Facebook Graph API Proxy with Real-time Update support

All configuration is done by editing config.py. This file simply launches two
web servers. one for the realtime update endpoint, and one for the proxy
itself. The realtime endpoint needs to be accessible publically, while the
proxy endpoint should be accessible only from a small set of machines
(ideally the web servers that would otherwise be making direct Facebook Graph
API calls).
"""
import threading
import time
from cherrypy import wsgiserver
from fbproxy import config, apps
from fbproxy.requesthandler import ProxyRequestHandlerFactory
from fbproxy.cache import ProxyLruCache
from fbproxy.rtendpoint import RealtimeUpdateHandlerFactory


GRAPH_SERVER = "graph.facebook.com"


def launch(config_file):
    """ Launch the Graph Proxy with the specified config_file."""
    config.load(config_file)
    cache = ProxyLruCache(config.cache_entries)
    appdict = apps.init(config.apps)

    request_handler_factory = ProxyRequestHandlerFactory(None,
            cache, appdict, GRAPH_SERVER)
    realtime_handler_factory = RealtimeUpdateHandlerFactory(cache, None,
                                                            appdict)
    endpoint = "http://" + config.public_hostname + ":" + str(
            config.realtime_port) + "/"

    proxyserver = wsgiserver.CherryPyWSGIServer((config.proxy_interface,
        config.proxy_port), request_handler_factory)
    rtuserver = wsgiserver.CherryPyWSGIServer((config.realtime_interface,
        config.realtime_port), realtime_handler_factory)

    realtime_port_thread = threading.Thread(target=rtuserver.start)
    realtime_port_thread.daemon = True
    realtime_port_thread.start()
    time.sleep(2)  # give the server time to come up

    realtime_handler_factory.register_apps(endpoint, GRAPH_SERVER)

    try:
        proxyserver.start()
    except KeyboardInterrupt:
        proxyserver.stop()
        rtuserver.stop()

########NEW FILE########
__FILENAME__ = lru
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" This module contains a simple LRU cache."""


class Node(object):
    """ An LRU node storing a key-value pair."""
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = None
        self.successor = None

    def remove(self):
        """ Remove this node from the linked list."""
        if self.prev:
            self.prev.successor = self.successor
        if self.successor:
            self.successor.prev = self.prev
        self.prev = None
        self.successor = None

    def setnext(self, next):
        """ Move this node in the linked list (or insert it."""
        self.successor = next
        if next:
            self.prev = next.prev
            next.prev = self
            if self.prev:
                self.prev.successor = self
        else:
            self.prev = None

    def __repr__(self):
        return "(" + repr(self.key) + "," + repr(self.value) + ")"


class LRU(object):
    """ A simple Least-recently-used cache.

    This LRU cache functions by containing a linked list of nodes holding
    key-value pairs, and a dictionary index into this linked list. Changes
    to the size field will get reflected the next time the list's size
    changes (whether by a new insert or a deletion).
    """
    def __init__(self, size=10000):
        self.count = 0
        self.size = size
        self.head = None
        self.tail = None
        self.index = {}

    def __getitem__(self, key):
        """ fetch an item from the list, and update it's access time."""
        if key in self.index:
            node = self.index[key]
            node.remove()
            node.setnext(self.head)
            return self.index[key].value
        return None

    def __setitem__(self, key, value):
        """ update a value or insert a new value. Also checks for fullness."""
        node = None
        if key in self.index:
            node = self.index[key]
            node.remove()
            node.setnext(self.head)
            self.head = node
            node.value = value
        else:
            node = Node(key, value)
            self.index[key] = node
            if not self.head:
                self.tail = node
            node.setnext(self.head)
            self.head = node
            self.count += 1
        self.checksize()

    def __contains__(self, key):
        """ existence check. This does NOT update the access time."""
        return key in self.index

    def __delitem__(self, key):
        """ remove the item from the cache. does nothing if it not found."""
        if key in self.index:
            node = self.index[key]
            if node == self.tail:
                self.tail = node.prev
            if node == self.head:
                self.head = node.successor
            del self.index[key]
            self.count -= 1
            node.remove()
        self.checksize()

    def checksize(self):
        """ Prunes the LRU down to 'count' entries."""
        print "checksize called. Current count is " + str(self.count) + " of " \
                + str(self.size)
        while self.count > self.size:
            node = self.tail
            del self.index[node.key]
            self.tail = node.prev
            node.remove()
            self.count -= 1

########NEW FILE########
__FILENAME__ = requesthandler
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" WSGI application for the proxy endpoint."""
import httplib
import urlparse
import logging

USER_FIELDS = ['first_name', 'last_name', 'name', 'hometown', 'location',
               'about', 'bio', 'relationship_status', 'significant_other',
               'work', 'education', 'gender']
INVALIDATE_MAP = {'feed': ['statuses', 'feed', 'links'],
                  'links': ['feed', 'links']}


class ProxyRequestHandler(object):
    """ WSGI application for handling a graph API request

    This takes requests, and either passes them through to config.graph_server
    or fulfills them from a cache. There are multiple reasons that a request
    might not be eligible to be cached, though. Specifically, these are:

    1. The request contains a field which is not enabled for realtime updates.
    2. The request is not a GET request
    3. The application has not seen a request from the targeted user before
        (based on access_token). Note that this will never prevent caching
        of a request for information about the current user. (see App.check_user
        in AppStateHandler for details)
    4. The request fails the application's check_request() verification.
    5. The request is not for a user or a direct connection of user
    6. A validator is present and the request fails its validation

    For requests which are not GET requests, we also proactively invalidate
    cache entries which are likely to be affected by such requests. See
    ProxyLruCache for details about the caching strategy.
    """
    def __init__(self, environ, start_response, validator, cache, appdict,
                 server):
        self.start = start_response
        self.env = environ
        self.cache = cache
        self.apps = appdict
        self.server = server
        # the following fields will be set in __iter__
        self.uriparts = None
        self.acctoken_pieces = None
        self.query_parms = None
        if validator:
            self.validate = validator

    def __iter__(self):
        """ fulfills a graph API request."""
        # parse the request
        self.uriparts = self.env['PATH_INFO'].strip('/').split('/')
        self.query_parms = urlparse.parse_qs(self.env['QUERY_STRING'])
        app = None
        if hasattr(self, 'validate'):
            if not self.validate(self.env):
                return self.forbidden()
        # determine the viewer context and application, if access token exists
        if 'access_token' in self.query_parms:
            self.acctoken_pieces = self.parse_access_token(
                    self.query_parms['access_token'][0])
            if self.acctoken_pieces:
                app = self.apps[self.acctoken_pieces[0]] \
                        if self.acctoken_pieces[0] in self.apps \
                        else None
            else:
                app = self.apps['default'] if 'default' in self.apps \
                    else None
        else:
            self.acctoken_pieces = ['', '', '', '']

        self.fixurl()  # replace /me with the actual UID, to enable sane caching
        self.env['PATH_INFO'] = '/'.join(self.uriparts)

        # last chance to load an app to handle this
        if not app and 'default' in self.apps:
            app = self.apps['default']
        if not app:
            logging.info('bypassing cache due to missing application settings')
            return self.pass_through()  # app is missing from config, so don't
                                        # cache
        # non-GETs typically change the results of subsequent GETs. Thus we
        # invalidate opportunistically.
        if self.env['REQUEST_METHOD'] != 'GET':
            self.invalidate_for_post(app)
            return self.pass_through()
        fields = USER_FIELDS  # default fields if not specified
        if 'fields' in self.query_parms:
            fields = self.query_parms['fields'][0].split(',')
        if not app.check_user(self.acctoken_pieces[2], self.uriparts[0],
                              self.apps.get('default')):
            logging.info('bypassing cache since user not known to be app user')
            return self.pass_through()
        if self.cannotcache():
            logging.info('bypassing cache because the URI is not cacheable')
            return self.pass_through()
        if not app.check_request(self.uriparts, fields):
            logging.info('bypassing cache since the app rejected the request')
            return self.pass_through()

        if self.cache:
            return self.do_cache(app, self.server)
        else:
            logging.warning('cache does not exist. passing request through')
            return self.pass_through()

    @staticmethod
    def parse_access_token(acctok):
        """ Split up an access_token into 4 parts.

        This fails on non-user access tokens.
        """
        try:
            acctoken_firstsplit = acctok.split('-', 1)
            acctoken_all = acctoken_firstsplit[0].split('|')
            acctoken_all.extend(acctoken_firstsplit[1].split('|'))
            if len(acctoken_all) != 4:
                return False
            return acctoken_all
        except IndexError:
            return False

    @staticmethod
    def fetchurl(reqtype, path, querystring, server):
        """ fetch the requested object from the Facebook Graph API server."""
        conn = httplib.HTTPSConnection(server)
        conn.request(reqtype, path + "?" + querystring)
        response = conn.getresponse()
        return response

    # connections which are known not to work with the Graph API.
    # See http://developers.facebook.com/docs/api/realtime for details
    connections_blacklist = ['home', 'tagged', 'posts', 'likes', 'photos', \
            'albums', 'videos', 'groups', 'notes', 'events', 'inbox', 'outbox',
            'updates']

    def cannotcache(self):
        """ A set of simple rules for ruling out some requests from caching."""
        # rule 0: Only GET requests can be fetched.
        # All others are assumed to have side effects
        if self.env['REQUEST_METHOD'] != 'GET':
            return True

        # rule 1: Reject if the request is not realtime-enabled.
        #    Specifically, it must either be a request for an item directly, or
        #    for an object which is not a blacklisted connection of users
        if len(self.uriparts) > 2:
            return True
        if len(self.uriparts) == 2:
            if self.uriparts[1] in ProxyRequestHandler.connections_blacklist:
                return True
        return False

    def fixurl(self):
        """ Replace "me" with the user's actual UID."""
        if self.uriparts[0].upper() == "ME":
            if self.acctoken_pieces[2] != '':
                self.uriparts[0] = self.acctoken_pieces[2]

    def pass_through(self):
        """ Satisfy a request by just proxying it to the Graph API server."""
        response = self.fetchurl(self.env['REQUEST_METHOD'],
                self.env['PATH_INFO'], self.env['QUERY_STRING'], self.server)
        self.start(str(response.status) + " " +
                response.reason, response.getheaders())
        data = response.read()
        response.close()
        yield data

    def do_cache(self, app, server):
        """ Satisfy a request by passing it to the Cache."""
        cached_response = self.cache.handle_request(self.query_parms,
                self.env['PATH_INFO'], self.env['QUERY_STRING'], app, server)
        self.start(cached_response[0], cached_response[1])
        yield cached_response[2]

    def forbidden(self):
        self.start('403 Forbidden', [('Content-type', 'text/plain')])
        yield "Failed to validate request\n"

    def internal_error(self):
        self.start('500 Internal Server Error',
                [('Content-type', 'text/plain')])
        yield "An internal error occurred\n"

    def invalidate_for_post(self, app):
        """ Invalidates possibly affected URLs after a non-GET.

        The behavior of this is controlled by invalidate_map in config.py
        """
        if len(self.uriparts) != 2:
            return
        if not self.uriparts[1] in INVALIDATE_MAP:
            return
        for field in INVALIDATE_MAP[self.uriparts[1]]:
            logging.debug('invalidating ' + self.uriparts[0] + '/' + field)
            self.cache.invalidate(app.id, "/" + self.uriparts[0] + "/" + field)


class ProxyRequestHandlerFactory(object):
    """ factory for request handlers.

    This is called by WSGI for each request. Note that this and any code
    called by it can be running in multiple threads at once.
    """
    def __init__(self, validator, cache, apps, server):
        self.validator = validator
        self.cache = cache
        self.apps = apps
        self.server = server

    def __call__(self, environ, start_response):
        return ProxyRequestHandler(environ, start_response,
                self.validator, self.cache, self.apps, self.server)

########NEW FILE########
__FILENAME__ = rtendpoint
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" WSGI application for realtime update handler endpoint."""
import json
import urlparse
import hmac
import hashlib
import logging
from fbproxy import rturegister


class RealtimeUpdateHandler(object):
    """ WSGI application for handling a realtime update.

    This responds to two types of requests: validation requests (GET), and
    realtime updates (POST). For each user change entry in the update, if
    at least one change is for a field directly on user, that user's entry is
    invalidated. Any connections are invalidated one by one.
    """
    def __init__(self, environ, start_response, validator, cache, apps):
        self.start = start_response
        self.env = environ
        self.cache = cache
        self.apps = apps
        if validator:
            self.validate = validator

    def __iter__(self):
        if self.env['REQUEST_METHOD'] == 'GET':
            return self.handle_validate()
        elif self.env['REQUEST_METHOD'] == 'POST':
            return self.handle_update()
        else:
            return self.forbidden()

    def bad_request(self, message=None):
        self.start('400 Bad Request', [('Content-type', 'text/plain')])
        if not message:
            yield "This is not a valid update"
        else:
            yield message

    def forbidden(self):
        self.start('403 Forbidden', [('Content-type', 'text/plain')])
        yield "Request validation failed"

    def not_found(self):
        self.start('404 Not Found', [('Content-type', 'text/plain')])
        yield "The requested application was not found on this server"

    def handle_validate(self):
        """ Performs Realtime Update endpoint validation.

        See http://developers.facebook.com/docs/api/realtime for details.
        """
        req_data = urlparse.parse_qs(self.env['QUERY_STRING'])
        logging.info('Validating subscription')
        if not 'hub.mode' in req_data or req_data['hub.mode'][0] != 'subscribe':
            return self.bad_request('expecting hub.mode')
        if not 'hub.verify_token' in req_data or \
                req_data['hub.verify_token'][0] == rturegister.randtoken:
            return self.forbidden()
        if not 'hub.challenge' in req_data:
            return self.bad_request('Missing challenge')
        return self.success(req_data['hub.challenge'][0])

    def handle_update(self):
        """ Respond to a Realtime Update POST.

        The APPID for which the update is performed is the path portion of the
        URL. This simply loops over every 'entry' in the update JSON and
        passes them off to the cache to invalidate.
        """
        app_id = self.env['PATH_INFO'][1:]
        app = self.apps.get(app_id)
        if not app:
            return self.not_found()
        if not 'CONTENT_LENGTH' in self.env:
            return self.bad_request('Missing content length')
        data = self.env['wsgi.input'].read(int(self.env['CONTENT_LENGTH']))
        sig = self.env.get('HTTP_X_HUB_SIGNATURE')
        if sig == None or sig == '':
            logging.info('received request with missing signature')
            return self.forbidden()
        if sig.startswith('sha1='):
            sig = sig[5:]
        if app.secret != None:
            hash = hmac.new(app.secret, data, hashlib.sha1)
            expected_sig = hash.hexdigest()
            if sig != expected_sig:
                logging.warn('Received request with invalid signature')
                logging.warn('sig is ' + sig)
                logging.warn('expected ' + expected_sig)
                logging.warn('key is ' + app.secret)
                logging.warn('data is ' + data)
                return self.bad_request('Invalid signature.')
        try:
            updates = json.loads(data)
        except ValueError:
            return self.bad_request('Expected JSON.')
        logging.info('received a realtime update')

        try:  # loop over all entries in the update message
            for entry in updates['entry']:
                uid = entry['uid']
                if len(app.good_fields.intersection(
                        entry['changed_fields'])) > 0:
                    self.cache.invalidate(app_id, uid)
                conns = app.good_conns.intersection(entry['changed_fields'])
                for conn in conns:
                    self.cache.invalidate(app_id, uid + "/" + conn)
        except KeyError:
            return self.bad_request('Missing fields caused key error')
        return self.success('Updates successfully handled')

    def success(self, message):
        self.start('200 OK', [('Content-type', 'text/plain')])
        yield message


class RealtimeUpdateHandlerFactory:
    """ Creates RealtimeUpdateHandlers for the given cache and app dictionary.
    """
    def __init__(self, cache, validator, appdict):
        self.cache = cache
        self.validator = validator
        self.appdict = appdict

    def register_apps(self, endpoint, server):
        """ Registers applications for realtime updates.

        This method must be called AFTER the realtime update endpoint is
        ready to accept connections. This means that the realtime update
        endpoint should probably be run on a different thread.
        """
        for app in self.appdict.itervalues():
            rturegister.register(app, endpoint + app.id, server)

    def __call__(self, environ, start_response):
        return RealtimeUpdateHandler(environ, start_response,
                self.validator, self.cache, self.appdict)

########NEW FILE########
__FILENAME__ = rturegister
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" Module enabling registration for realtime updates.

The most commonly used method is register, which takes the endpoint URL
and the app object, and registers for realtime updates if either the app's
cred or secret is available and valid.
"""
import httplib
import urllib
import random


randtoken = 0


def register_with_secret(appid, secret, fields, callback, server):
    """ Register the given application for realtime updates.

    Creates a subscription for user fields for the given application
    at the specified callback URL. This method takes the application secret
    as the second argument. Only one of register_with_secret and
    register_with_token needs to be called. In most cases, this should be
    taken care of by register().
    """
    token = appid + '|' + secret
    return register_with_token(appid, token, fields, callback, server)


def register_with_token(appid, token, fields, callback, server):
    """ Register the given application for realtime updates.

    Creates a subscription for user fields for the given application
    at the specified callback URL. This method takes an application's client
    credential access token as the second argument. Only one of
    register_with_secret and register_with_token needs to be called. In most
    cases, this should be taken care of by register().
    """
    fieldstr = ",".join(fields)
    headers = {'Content-type': 'applocation/x-www-form-urlencoded'}
    # use a random number as our verification token
    global randtoken
    if not randtoken:
        randtoken = random.randint(1, 1000000000)

    # make a POST to the graph API to register the endpoint
    postfields = {'object': 'user',
                  'fields': fieldstr,
                  'callback_url': callback,
                  'verify_token': randtoken}
    conn = httplib.HTTPSConnection(server)
    conn.request('POST', appid + '/subscriptions?access_token=' + token,
            urllib.urlencode(postfields), headers)
    response = conn.getresponse()
    if response.status == 200:
        return True
    else:
        print 'Error subscribing: graph server\'s response follows'
        print str(response.status) + " " + response.reason
        data = response.read()
        print data
        return False


def register(app, callback, server):
    """ Registers the given App, if possible.

    For registration to be possible, at least one of app.cred or app.secret
    must be defined.
    """
    subscribefields = app.good_fields | app.good_conns
    if app.cred:
        register_with_token(app.id, app.cred, subscribefields, callback, server)
    elif app.secret:
        register_with_secret(app.id, app.secret, subscribefields, callback,
                             server)

########NEW FILE########
