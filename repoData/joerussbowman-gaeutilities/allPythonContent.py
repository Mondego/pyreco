__FILENAME__ = cache
# -*- coding: utf-8 -*-
"""
Copyright (c) 2008, appengine-utilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the appengine-utilities project nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# main python imports
import datetime
import pickle
import random
import sys

# google appengine import
from google.appengine.ext import db
from google.appengine.api import memcache

# settings
try:
    import settings_default
    import settings

    if settings.__name__.rsplit('.', 1)[0] != settings_default.__name__.rsplit('.', 1)[0]:
        settings = settings_default
except:
    settings = settings_default
    
class _AppEngineUtilities_Cache(db.Model):
    cachekey = db.StringProperty()
    createTime = db.DateTimeProperty(auto_now_add=True)
    timeout = db.DateTimeProperty()
    value = db.BlobProperty()


class Cache(object):
    """
    Cache is used for storing pregenerated output and/or objects in the Big
    Table datastore to minimize the amount of queries needed for page
    displays. The idea is that complex queries that generate the same
    results really should only be run once. Cache can be used to store
    pregenerated value made from queries (or other calls such as
    urlFetch()), or the query objects themselves.

    Cache is a standard dictionary object and can be used as such. It attesmpts
    to store data in both memcache, and the datastore. However, should a
    datastore write fail, it will not try again. This is for performance
    reasons.
    """

    def __init__(self, clean_check_percent = settings.cache["CLEAN_CHECK_PERCENT"],
      max_hits_to_clean = settings.cache["MAX_HITS_TO_CLEAN"],
        default_timeout = settings.cache["DEFAULT_TIMEOUT"]):
        """
        Initializer

        Args:
            clean_check_percent: how often cache initialization should
                run the cache cleanup
            max_hits_to_clean: maximum number of stale hits to clean
            default_timeout: default length a cache item is good for
        """
        self.clean_check_percent = clean_check_percent
        self.max_hits_to_clean = max_hits_to_clean
        self.default_timeout = default_timeout

        if random.randint(1, 100) < self.clean_check_percent:
            try:
                self._clean_cache()
            except:
                pass

        if 'AEU_Events' in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event('cacheInitialized')

    def _clean_cache(self):
        """
        _clean_cache is a routine that is run to find and delete cache
        items that are old. This helps keep the size of your over all
        datastore down.

        It only deletes the max_hits_to_clean per attempt, in order
        to maximize performance. Default settings are 20 hits, 50%
        of requests. Generally less hits cleaned on more requests will
        give you better performance.

        Returns True on completion
        """
        query = _AppEngineUtilities_Cache.all()
        query.filter('timeout < ', datetime.datetime.now())
        results = query.fetch(self.max_hits_to_clean)
        db.delete(results)

        return True

    def _validate_key(self, key):
        """
        Internal method for key validation. This can be used by a superclass
        to introduce more checks on key names.
        
        Args:
            key: Key name to check

        Returns True is key is valid, otherwise raises KeyError.
        """
        if key == None:
            raise KeyError
        return True

    def _validate_value(self, value):
        """
        Internal method for value validation. This can be used by a superclass
        to introduce more checks on key names.

        Args:
            value: value to check

        Returns True is value is valid, otherwise raises ValueError.
        """
        if value == None:
            raise ValueError
        return True

    def _validate_timeout(self, timeout):
        """
        Internal method to validate timeouts. If no timeout
        is passed, then the default_timeout is used.

        Args:
            timeout: datetime.datetime format

        Returns the timeout
        """
        if timeout == None:
            timeout = datetime.datetime.now() +\
            datetime.timedelta(seconds=self.default_timeout)
        if type(timeout) == type(1):
            timeout = datetime.datetime.now() + \
                datetime.timedelta(seconds = timeout)
        if type(timeout) != datetime.datetime:
            raise TypeError
        if timeout < datetime.datetime.now():
            raise ValueError

        return timeout

    def add(self, key = None, value = None, timeout = None):
        """
        Adds an entry to the cache, if one does not already exist. If they key
        already exists, KeyError will be raised.

        Args:
            key: Key name of the cache object
            value: Value of the cache object
            timeout: timeout value for the cache object.

        Returns the cache object.
        """
        self._validate_key(key)
        self._validate_value(value)
        timeout = self._validate_timeout(timeout)

        if key in self:
            raise KeyError

        cacheEntry = _AppEngineUtilities_Cache()
        cacheEntry.cachekey = key
        cacheEntry.value = pickle.dumps(value)
        cacheEntry.timeout = timeout

        # try to put the entry, if it fails silently pass
        # failures may happen due to timeouts, the datastore being read
        # only for maintenance or other applications. However, cache
        # not being able to write to the datastore should not
        # break the application
        try:
            cacheEntry.put()
        except:
            pass

        memcache_timeout = timeout - datetime.datetime.now()
        memcache.set('cache-%s' % (key), value, int(memcache_timeout.seconds))

        if 'AEU_Events' in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event('cacheAdded')

        return self.get(key)

    def set(self, key = None, value = None, timeout = None):
        """
        Sets an entry to the cache, overwriting an existing value
        if one already exists.

        Args:
            key: Key name of the cache object
            value: Value of the cache object
            timeout: timeout value for the cache object.

        Returns the cache object.
        """
        self._validate_key(key)
        self._validate_value(value)
        timeout = self._validate_timeout(timeout)

        cacheEntry = self._read(key)
        if not cacheEntry:
            cacheEntry = _AppEngineUtilities_Cache()
            cacheEntry.cachekey = key
        cacheEntry.value = pickle.dumps(value)
        cacheEntry.timeout = timeout

        try:
            cacheEntry.put()
        except:
            pass

        memcache_timeout = timeout - datetime.datetime.now()
        memcache.set('cache-%s' % (key), value, int(memcache_timeout.seconds))

        if 'AEU_Events' in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event('cacheSet')

        return value

    def _read(self, key = None):
        """
        _read is an internal method that will get the cache entry directly
        from the datastore, and return the entity. This is used for datastore
        maintenance within the class.

        Args:
            key: The key to retrieve

        Returns the cache entity
        """
        query = _AppEngineUtilities_Cache.all()
        query.filter('cachekey', key)
        query.filter('timeout > ', datetime.datetime.now())
        results = query.fetch(1)
        if len(results) is 0:
            return None

        if 'AEU_Events' in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event('cacheReadFromDatastore')
        if 'AEU_Events' in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event('cacheRead')

        return results[0]

    def delete(self, key = None):
        """
        Deletes a cache object.

        Args:
            key: The key of the cache object to delete.

        Returns True.
        """
        memcache.delete('cache-%s' % (key))
        result = self._read(key)
        if result:
            if 'AEU_Events' in sys.modules['__main__'].__dict__:
                sys.modules['__main__'].AEU_Events.fire_event('cacheDeleted')
            result.delete()
        return True

    def get(self, key):
        """
        Used to return the cache value associated with the key passed.

        Args:
            key: The key of the value to retrieve.

        Returns the value of the cache item.
        """
        mc = memcache.get('cache-%s' % (key))
        if mc:
            if 'AEU_Events' in sys.modules['__main__'].__dict__:
                sys.modules['__main__'].AEU_Events.fire_event('cacheReadFromMemcache')
            if 'AEU_Events' in sys.modules['__main__'].__dict__:
                sys.modules['__main__'].AEU_Events.fire_event('cacheRead')
            return mc
        result = self._read(key)
        if result:
            timeout = result.timeout - datetime.datetime.now()
            memcache.set('cache-%s' % (key), pickle.loads(result.value),
               int(timeout.seconds))
            if 'AEU_Events' in sys.modules['__main__'].__dict__:
                sys.modules['__main__'].AEU_Events.fire_event('cacheRead')
            return pickle.loads(result.value)
        else:
            raise KeyError

    def get_many(self, keys):
        """
        Returns a dict mapping each key in keys to its value. If the given
        key is missing, it will be missing from the response dict.

        Args:
            keys: A list of keys to retrieve.

        Returns a dictionary of key/value pairs.
        """
        dict = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                dict[key] = value
        return dict

    def __getitem__(self, key):
        """
        __getitem__ is necessary for this object to emulate a container.
        """
        return self.get(key)

    def __setitem__(self, key, value):
        """
        __setitem__ is necessary for this object to emulate a container.
        """
        return self.set(key, value)

    def __delitem__(self, key):
        """
        Implement the 'del' keyword
        """
        return self.delete(key)

    def __contains__(self, key):
        """
        Implements "in" operator
        """
        try:
            self.__getitem__(key)
        except KeyError:
            return False
        return True

    def has_key(self, keyname):
        """
        Equivalent to k in a, use that form in new code
        """
        return self.__contains__(keyname)

########NEW FILE########
__FILENAME__ = middleware
import Cookie
import os

from common.appengine_utilities import sessions


class SessionMiddleware(object):
    TEST_COOKIE_NAME = 'testcookie'
    TEST_COOKIE_VALUE = 'worked'

    def process_request(self, request):
        """
        Check to see if a valid session token exists, if not,
        then use a cookie only session. It's up to the application
        to convert the session to a datastore session. Once this
        has been done, the session will continue to use the datastore
        unless the writer is set to "cookie".

        Setting the session to use the datastore is as easy as resetting
        request.session anywhere if your application.

        Example:
            from common.appengine_utilities import sessions
            request.session = sessions.Session()
        """
        self.request = request
        if sessions.Session.check_token():
            request.session = sessions.Session()
        else:
            request.session = sessions.Session(writer="cookie")
        request.session.set_test_cookie = self.set_test_cookie
        request.session.test_cookie_worked = self.test_cookie_worked
        request.session.delete_test_cookie = self.delete_test_cookie
        request.session.save = self.save
        return None

    def set_test_cookie(self):
        string_cookie = os.environ.get('HTTP_COOKIE', '')

        self.cookie = Cookie.SimpleCookie()
        self.cookie.load(string_cookie)
        self.cookie[self.TEST_COOKIE_NAME] = self.TEST_COOKIE_VALUE
        print self.cookie

    def test_cookie_worked(self):
        string_cookie = os.environ.get('HTTP_COOKIE', '')

        self.cookie = Cookie.SimpleCookie()
        self.cookie.load(string_cookie)

        return self.cookie.get(self.TEST_COOKIE_NAME)

    def delete_test_cookie(self):
        string_cookie = os.environ.get('HTTP_COOKIE', '')

        self.cookie = Cookie.SimpleCookie()
        self.cookie.load(string_cookie)
        self.cookie[self.TEST_COOKIE_NAME] = ''
        self.cookie[self.TEST_COOKIE_NAME]['path'] = '/'
        self.cookie[self.TEST_COOKIE_NAME]['expires'] = 0

    def save(self):
        self.request.session = sessions.Session()

    def process_response(self, request, response):
        if hasattr(request, "session"):
            response.cookies= request.session.output_cookie
        return response

########NEW FILE########
__FILENAME__ = event
"""
Copyright (c) 2008, appengine-utilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the appengine-utilities project nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import sys


class Event(object):
    """
    Event is a simple publish/subscribe based event dispatcher. It's a way
    to add, or take advantage of, hooks in your application. If you want to
    tie actions in with lower level classes you're developing within your
    application, you can set events to fire, and then subscribe to them with
    callback methods in other methods in your application.

    It sets itself to the sys.modules['__main__'] function. In order to use it,
    you must import it with your sys.modules['__main__'] method, and make sure
    you import sys.modules['__main__'] and it's accessible for the methods where
    you want to use it.

    For example, from sessions.py

            # if the event class has been loaded, fire off the sessionDeleted
            # event
        if u"AEU_Events" in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event(u"sessionDelete")

    You can the subscribe to session delete events, adding a callback

        if u"AEU_Events" in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.subscribe(u"sessionDelete", \
            clear_user_session)
    """

    def __init__(self):
        self.events = []

    def subscribe(self, event, callback, args = None):
        """
        This method will subscribe a callback function to an event name.

        Args:
            event: The event to subscribe to.
            callback: The callback method to run.
            args: Optional arguments to pass with the callback.

        Returns True
        """
        if not {"event": event, "callback": callback, "args": args, } \
            in self.events:
            self.events.append({"event": event, "callback": callback, \
                "args": args, })
        return True

    def unsubscribe(self, event, callback, args = None):
        """
        This method will unsubscribe a callback from an event.

        Args:
            event: The event to subscribe to.
            callback: The callback method to run.
            args: Optional arguments to pass with the callback.

        Returns True
        """
        if {"event": event, "callback": callback, "args": args, }\
            in self.events:
            self.events.remove({"event": event, "callback": callback,\
                "args": args, })

        return True

    def fire_event(self, event = None):
        """
        This method is what a method uses to fire an event,
        initiating all registered callbacks

        Args:
            event: The name of the event to fire.

        Returns True
        """
        for e in self.events:
            if e["event"] == event:
                if type(e["args"]) == type([]):
                    e["callback"](*e["args"])
                elif type(e["args"]) == type({}):
                    e["callback"](**e["args"])
                elif e["args"] == None:
                    e["callback"]()
                else:
                    e["callback"](e["args"])
        return True
"""
Assign to the event class to sys.modules['__main__']
"""
sys.modules['__main__'].AEU_Events = Event()

########NEW FILE########
__FILENAME__ = flash
"""
Copyright (c) 2008, appengine-utilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the appengine-utilities project nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os
import Cookie
from time import strftime

from django.utils import simplejson

# settings
try:
    import settings_default
    import settings

    if settings.__name__.rsplit('.', 1)[0] != settings_default.__name__.rsplit('.', 1)[0]:
        settings = settings_default
except:
    settings = settings_default

COOKIE_NAME = settings.flash["COOKIE_NAME"]


class Flash(object):
    """
    Send messages to the user between pages.

    When you instantiate the class, the attribute 'msg' will be set from the
    cookie, and the cookie will be deleted. If there is no flash cookie, 'msg'
    will default to None.

    To set a flash message for the next page, simply set the 'msg' attribute.

    Example psuedocode:

        if new_entity.put():
            flash = Flash()
            flash.msg = 'Your new entity has been created!'
            return redirect_to_entity_list()

    Then in the template on the next page:

        {% if flash.msg %}
            <div class="flash-msg">{{ flash.msg }}</div>
        {% endif %}
    """

    def __init__(self, cookie=None):
        """
        Load the flash message and clear the cookie.
        """
        print self.no_cache_headers()
       # load cookie
        if cookie is None:
            browser_cookie = os.environ.get('HTTP_COOKIE', '')
            self.cookie = Cookie.SimpleCookie()
            self.cookie.load(browser_cookie)
        else:
            self.cookie = cookie
        # check for flash data
        if self.cookie.get(COOKIE_NAME):
            # set 'msg' attribute
            cookie_val = self.cookie[COOKIE_NAME].value
            # we don't want to trigger __setattr__(), which creates a cookie
            try:
                self.__dict__['msg'] = simplejson.loads(cookie_val)
            except:
                # not able to load the json, so do not set message. This should
                # catch for when the browser doesn't delete the cookie in time for
                # the next request, and only blanks out the content.
                pass
            # clear the cookie
            self.cookie[COOKIE_NAME] = ''
            self.cookie[COOKIE_NAME]['path'] = '/'
            self.cookie[COOKIE_NAME]['expires'] = 0
            print self.cookie[COOKIE_NAME]
        else:
            # default 'msg' attribute to None
            self.__dict__['msg'] = None

    def __setattr__(self, name, value):
        """
        Create a cookie when setting the 'msg' attribute.
        """
        if name == 'cookie':
            self.__dict__['cookie'] = value
        elif name == 'msg':
            self.__dict__['msg'] = value
            self.__dict__['cookie'][COOKIE_NAME] = simplejson.dumps(value)
            self.__dict__['cookie'][COOKIE_NAME]['path'] = '/'
            print self.cookie
        else:
            raise ValueError('You can only set the "msg" attribute.')

    def no_cache_headers(self):
        """
        Generates headers to avoid any page caching in the browser.
        Useful for highly dynamic sites.

        Returns a unicode string of headers.
        """
        return u"".join([u"Expires: Tue, 03 Jul 2001 06:00:00 GMT",
            strftime("Last-Modified: %a, %d %b %y %H:%M:%S %Z").decode("utf-8"),
            u"Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
            u"Cache-Control: post-check=0, pre-check=0",
            u"Pragma: no-cache",
        ])

########NEW FILE########
__FILENAME__ = main
'''
Copyright (c) 2008, appengine-utilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
Neither the name of the appengine-utilities project nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

import os, cgi, __main__
from google.appengine.ext.webapp import template
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db

from appengine_utilities import cron

class MainPage(webapp.RequestHandler):
    def get(self):
        c = cron.Cron()
        query = cron._AppEngineUtilities_Cron.all()
        results = query.fetch(1000) 
        template_values = {"cron_entries" : results}
        path = os.path.join(os.path.dirname(__file__), 'templates/scheduler_form.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        if str(self.request.get('action')) == 'Add':
            cron.Cron().add_cron(str(self.request.get('cron_entry')))
        elif str(self.request.get('action')) == 'Delete':
            entry = db.get(db.Key(str(self.request.get('key'))))
            entry.delete()
        query = cron._AppEngineUtilities_Cron.all()
        results = query.fetch(1000) 
        template_values = {"cron_entries" : results}
        path = os.path.join(os.path.dirname(__file__), 'templates/scheduler_form.html')
        self.response.out.write(template.render(path, template_values))

def main():
    application = webapp.WSGIApplication(
                                       [('/gaeutilities/', MainPage)],
                                       debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()
########NEW FILE########
__FILENAME__ = rotmodel
"""
Copyright (c) 2008, appengine-utilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the appengine-utilities project nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import time
from google.appengine.api import datastore
from google.appengine.ext import db

# settings
try:
    import settings_default
    import settings

    if settings.__name__.rsplit('.', 1)[0] != settings_default.__name__.rsplit('.', 1)[0]:
        settings = settings_default
except:
    settings = settings_default

class ROTModel(db.Model):
    """
    ROTModel overrides the db.Model functions, retrying each method each time
    a timeout exception is raised.

    Methods superclassed from db.Model are:
        get(cls, keys)
        get_by_id(cls, ids, parent)
        get_by_key_name(cls, key_names, parent)
        get_or_insert(cls, key_name, kwargs)
        put(self)
    """

    @classmethod
    def get(cls, keys):
        count = 0
        while count < settings.rotmodel["RETRY_ATTEMPTS"]:
            try:
                return db.Model.get(keys)
            except db.Timeout:
                count += 1
                time.sleep(count * settings.rotmodel["RETRY_INTERVAL"])
        else:
            raise db.Timeout()

    @classmethod
    def get_by_id(cls, ids, parent=None):
        count = 0
        while count < settings.rotmodel["RETRY_ATTEMPTS"]:
            try:
                return db.Model.get_by_id(ids, parent)
            except db.Timeout:
                count += 1
                time.sleep(count * settings.rotmodel["RETRY_INTERVAL"])
        else:
            raise db.Timeout()

    @classmethod
    def get_by_key_name(cls, key_names, parent=None):
        if isinstance(parent, db.Model):
            parent = parent.key()
        key_names, multiple = datastore.NormalizeAndTypeCheck(key_names, basestring)
        keys = [datastore.Key.from_path(cls.kind(), name, parent=parent)
                for name in key_names]
        count = 0
        if multiple:
            while count < settings.rotmodel["RETRY_ATTEMPTS"]:
                try:
                    return db.get(keys)
                except db.Timeout:
                    count += 1
                    time.sleep(count * settings.rotmodel["RETRY_INTERVAL"])
        else:
            while count < settings.rotmodel["RETRY_ATTEMPTS"]:
                try:
                    return db.get(*keys)
                except db.Timeout:
                    count += 1
                    time.sleep(count * settings.rotmodel["RETRY_INTERVAL"])

    @classmethod
    def get_or_insert(cls, key_name, **kwargs):
        def txn():
            entity = cls.get_by_key_name(key_name, parent=kwargs.get('parent'))
            if entity is None:
                entity = cls(key_name=key_name, **kwargs)
                entity.put()
            return entity
        return db.run_in_transaction(txn)

    def put(self):
        count = 0
        while count < settings.rotmodel["RETRY_ATTEMPTS"]:
            try:
                return db.Model.put(self)
            except db.Timeout:
                count += 1
                time.sleep(count * settings.rotmodel["RETRY_INTERVAL"])
        else:
            raise db.Timeout()

    def delete(self):
        count = 0
        while count < settings.rotmodel["RETRY_ATTEMPTS"]:
            try:
                return db.Model.delete(self)
            except db.Timeout:
                count += 1
                time.sleep(count * settings.rotmodel["RETRY_INTERVAL"])
        else:
            raise db.Timeout()



########NEW FILE########
__FILENAME__ = sessions
# -*- coding: utf-8 -*-
"""
Copyright (c) 2008, appengine-utilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the appengine-utilities project nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# main python imports
import os
import time
import datetime
import random
import hashlib
import Cookie
import pickle
import sys
import logging
from time import strftime

# google appengine imports
from google.appengine.ext import db
from google.appengine.api import memcache

from django.utils import simplejson

# settings
try:
    import settings_default
    import settings

    if settings.__name__.rsplit('.', 1)[0] != settings_default.__name__.rsplit('.', 1)[0]:
        settings = settings_default
except:
    settings = settings_default




class _AppEngineUtilities_Session(db.Model):
    """
    Model for the sessions in the datastore. This contains the identifier and
    validation information for the session.
    """

    sid = db.StringListProperty()
    ip = db.StringProperty()
    ua = db.StringProperty()
    last_activity = db.DateTimeProperty()
    dirty = db.BooleanProperty(default=False)
    working = db.BooleanProperty(default=False)
    deleted = db.BooleanProperty(default=False) 

    def put(self):
        """
        Extends put so that it writes vaules to memcache as well as the
        datastore, and keeps them in sync, even when datastore writes fails.

        Returns the session object.
        """
        try:
            memcache.set(u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())), self)
        except:
            # new session, generate a new key, which will handle the
            # put and set the memcache
            db.put(self)

        self.last_activity = datetime.datetime.now()

        try:
            self.dirty = False
            db.put(self)
            memcache.set(u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())), self)
        except:
            self.dirty = True
            memcache.set(u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())), self)

        return self

    @classmethod
    def get_session(cls, session_obj=None):
        """
        Uses the passed objects sid to get a session object from memcache,
        or datastore if a valid one exists.

        Args:
            session_obj: a session object

        Returns a validated session object.
        """
        if session_obj.sid == None:
            return None
        session_key = session_obj.sid.rsplit(u'_', 1)[0]
        session = memcache.get(u"_AppEngineUtilities_Session_%s" % \
            (str(session_key)))
        if session:
            if session.deleted == True:
                session.delete()
                return None
            if session.dirty == True and session.working != False:
                # the working bit is used to make sure multiple requests,
                # which can happen with ajax oriented sites, don't try to put
                # at the same time
                session.working = True
                memcache.set(u"_AppEngineUtilities_Session_%s" % \
                    (str(session_key)), session)
                session.put()
            if session_obj.sid in session.sid:
                sessionAge = datetime.datetime.now() - session.last_activity
                if sessionAge.seconds > session_obj.session_expire_time:
                    session.delete()
                    return None
                return session
            else:
                return None
 
        # Not in memcache, check datastore
        
        try:
            ds_session = db.get(str(session_key))
        except:
            ds_session = None
        if ds_session:
          sessionAge = datetime.datetime.now() - ds_session.last_activity
          if sessionAge.seconds > session_obj.session_expire_time:
              ds_session.delete()
              return None
          memcache.set(u"_AppEngineUtilities_Session_%s" % \
              (str(session_key)), ds_session)
          memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
              (str(session_key)), ds_session.get_items_ds())
        return ds_session


    def get_items(self):
        """
        Returns all the items stored in a session. Queries memcache first
        and will try the datastore next.
        """
        items = memcache.get(u"_AppEngineUtilities_SessionData_%s" % \
            (str(self.key())))
        if items:
            for item in items:
                if item.deleted == True:
                    item.delete()
                    items.remove(item)
            return items

        query = _AppEngineUtilities_SessionData.all()
        query.filter(u"session", self)
        results = query.fetch(1000)
        return results

    def get_item(self, keyname = None):
        """
        Returns a single session data item from the memcache or datastore

        Args:
            keyname: keyname of the session data object

        Returns the session data object if it exists, otherwise returns None
        """
        mc = memcache.get(u"_AppEngineUtilities_SessionData_%s" % \
            (str(self.key())))
        if mc:
            for item in mc:
                if item.keyname == keyname:
                    if item.deleted == True:
                        item.delete()
                        return None
                    return item
        query = _AppEngineUtilities_SessionData.all()
        query.filter(u"session = ", self)
        query.filter(u"keyname = ", keyname)
        results = query.fetch(1)
        if len(results) > 0:
            memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
                (str(self.key())), self.get_items_ds())
            return results[0]
        return None

    def get_items_ds(self):
        """
        This gets all session data objects from the datastore, bypassing
        memcache.

        Returns a list of session data entities.
        """
        query = _AppEngineUtilities_SessionData.all()
        query.filter(u"session", self)
        results = query.fetch(1000)
        return results

    def delete(self):
        """
        Deletes a session and all it's associated data from the datastore and
        memcache.

        Returns True
        """
        try:
            query = _AppEngineUtilities_SessionData.all()
            query.filter(u"session = ", self)
            results = query.fetch(1000)
            db.delete(results)
            db.delete(self)
            memcache.delete_multi([u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())), \
                u"_AppEngineUtilities_SessionData_%s" % \
                (str(self.key()))])
        except:
            mc = memcache.get(u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())))
            if mc:
                mc.deleted = True
            else:
                # not in the memcache, check to see if it should be
                query = _AppEngineUtilities_Session.all()
                query.filter(u"sid = ", self.sid)
                results = query.fetch(1)
                if len(results) > 0:
                    results[0].deleted = True
                    memcache.set(u"_AppEngineUtilities_Session_%s" % \
                        (unicode(self.key())), results[0])
        return True
            
class _AppEngineUtilities_SessionData(db.Model):
    """
    Model for the session data in the datastore.
    """

    # session_key = db.FloatProperty()
    keyname = db.StringProperty()
    content = db.BlobProperty()
    model = db.ReferenceProperty()
    session = db.ReferenceProperty(_AppEngineUtilities_Session)
    dirty = db.BooleanProperty(default=False)
    deleted = db.BooleanProperty(default=False)

    def put(self):
        """
        Adds a keyname/value for session to the datastore and memcache

        Returns the key from the datastore put or u"dirty"
        """
        # update or insert in datastore
        try:
            return_val = db.put(self)
            self.dirty = False
        except:
            return_val = u"dirty"
            self.dirty = True

        # update or insert in memcache
        mc_items = memcache.get(u"_AppEngineUtilities_SessionData_%s" % \
            (str(self.session.key())))
        if mc_items:
            value_updated = False
            for item in mc_items:
                if value_updated == True:
                    break
                if item.keyname == self.keyname:
                    item.content = self.content
                    item.model = self.model
                    memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
                        (str(self.session.key())), mc_items)
                    value_updated = True
                    break
            if value_updated == False:
                mc_items.append(self)
                memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
                    (str(self.session.key())), mc_items)
        return return_val

    def delete(self):
        """
        Deletes an entity from the session in memcache and the datastore

        Returns True
        """
        try:
            db.delete(self)
        except:
            self.deleted = True
        mc_items = memcache.get(u"_AppEngineUtilities_SessionData_%s" % \
            (str(self.session.key())))
        value_handled = False
        for item in mc_items:
            if value_handled == True:
                break
            if item.keyname == self.keyname:
                if self.deleted == True:
                    item.deleted = True
                else:
                    mc_items.remove(item)
                memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
                    (str(self.session.key())), mc_items)
        return True
        

class _DatastoreWriter(object):

    def put(self, keyname, value, session):
        """
        Insert a keyname/value pair into the datastore for the session.

        Args:
            keyname: The keyname of the mapping.
            value: The value of the mapping.

        Returns the model entity key
        """
        keyname = session._validate_key(keyname)
        if value is None:
            raise ValueError(u"You must pass a value to put.")

        # datestore write trumps cookie. If there is a cookie value
        # with this keyname, delete it so we don't have conflicting
        # entries.
        if session.cookie_vals.has_key(keyname):
            del(session.cookie_vals[keyname])
            session.output_cookie["%s_data" % (session.cookie_name)] = \
                simplejson.dumps(session.cookie_vals)
            session.output_cookie["%s_data" % (session.cookie_name)]["path"] = \
                session.cookie_path
            if session.cookie_domain:
                session.output_cookie["%s_data" % \
                    (session.cookie_name)]["domain"] = session.cookie_domain
            print session.output_cookie.output()

        sessdata = session._get(keyname=keyname)
        if sessdata is None:
            sessdata = _AppEngineUtilities_SessionData()
            # sessdata.session_key = session.session.key()
            sessdata.keyname = keyname
        try:
            db.model_to_protobuf(value)
            if not value.is_saved():
                value.put()
            sessdata.model = value
        except:
            sessdata.content = pickle.dumps(value)
            sessdata.model = None
        sessdata.session = session.session
            
        session.cache[keyname] = value
        return sessdata.put()


class _CookieWriter(object):
    def put(self, keyname, value, session):
        """
        Insert a keyname/value pair into the datastore for the session.

        Args:
            keyname: The keyname of the mapping.
            value: The value of the mapping.

        Returns True
        """
        keyname = session._validate_key(keyname)
        if value is None:
            raise ValueError(u"You must pass a value to put.")

        # Use simplejson for cookies instead of pickle.
        session.cookie_vals[keyname] = value
        # update the requests session cache as well.
        session.cache[keyname] = value
        # simplejson will raise any error I'd raise about an invalid value
        # so let it raise exceptions
        session.output_cookie["%s_data" % (session.cookie_name)] = \
            simplejson.dumps(session.cookie_vals)
        session.output_cookie["%s_data" % (session.cookie_name)]["path"] = \
            session.cookie_path
        if session.cookie_domain:
            session.output_cookie["%s_data" % \
                (session.cookie_name)]["domain"] = session.cookie_domain
        print session.output_cookie.output()
        return True

class Session(object):
    """
    Sessions are used to maintain user presence between requests.

    Sessions can either be stored server side in the datastore/memcache, or
    be kept entirely as cookies. This is set either with the settings file
    or on initialization, using the writer argument/setting field. Valid
    values are "datastore" or "cookie".

    Session can be used as a standard dictionary object.
        session = appengine_utilities.sessions.Session()
        session["keyname"] = "value" # sets keyname to value
        print session["keyname"] # will print value

    Datastore Writer:
        The datastore writer was written with the focus being on security,
        reliability, and performance. In that order.

        It is based off of a session token system. All data is stored
        server side in the datastore and memcache. A token is given to
        the browser, and stored server side. Optionally (and on by default),
        user agent and ip checking is enabled. Tokens have a configurable
        time to live (TTL), which defaults to 5 seconds. The current token,
        plus the previous 2, are valid for any request. This is done in order
        to manage ajax enabled sites which may have more than on request
        happening at a time. This means any token is valid for 15 seconds.
        A request with a token who's TTL has passed will have a new token
        generated.

        In order to take advantage of the token system for an authentication
        system, you will want to tie sessions to accounts, and make sure
        only one session is valid for an account. You can do this by setting
        a db.ReferenceProperty(_AppEngineUtilities_Session) attribute on
        your user Model, and use the get_ds_entity() method on a valid
        session to populate it on login.

        Note that even with this complex system, sessions can still be hijacked
        and it will take the user logging in to retrieve the account. In the
        future an ssl only cookie option may be implemented for the datastore
        writer, which would further protect the session token from being
        sniffed, however it would be restricted to using cookies on the
        .appspot.com domain, and ssl requests are a finite resource. This is
        why such a thing is not currently implemented.

        Session data objects are stored in the datastore pickled, so any
        python object is valid for storage.

    Cookie Writer:
        Sessions using the cookie writer are stored entirely in the browser
        and no interaction with the datastore is required. This creates
        a drastic improvement in performance, but provides no security for
        session hijack. This is useful for requests where identity is not
        important, but you wish to keep state between requests.

        Information is stored in a json format, as pickled data from the
        server is unreliable.

        Note: There is no checksum validation of session data on this method,
        it's streamlined for pure performance. If you need to make sure data
        is not tampered with, use the datastore writer which stores the data
        server side.

    django-middleware:
        Included with the GAEUtilties project is a
        django-middleware.middleware.SessionMiddleware which can be included in
        your settings file. This uses the cookie writer for anonymous requests,
        and you can switch to the datastore writer on user login. This will
        require an extra set in your login process of calling
        request.session.save() once you validated the user information. This
        will convert the cookie writer based session to a datastore writer.
    """

    # cookie name declaration for class methods
    COOKIE_NAME = settings.session["COOKIE_NAME"]

    def __init__(self, cookie_path=settings.session["DEFAULT_COOKIE_PATH"],
            cookie_domain=settings.session["DEFAULT_COOKIE_DOMAIN"],
            cookie_name=settings.session["COOKIE_NAME"],
            session_expire_time=settings.session["SESSION_EXPIRE_TIME"],
            clean_check_percent=settings.session["CLEAN_CHECK_PERCENT"],
            integrate_flash=settings.session["INTEGRATE_FLASH"],
            check_ip=settings.session["CHECK_IP"],
            check_user_agent=settings.session["CHECK_USER_AGENT"],
            set_cookie_expires=settings.session["SET_COOKIE_EXPIRES"],
            session_token_ttl=settings.session["SESSION_TOKEN_TTL"],
            last_activity_update=settings.session["UPDATE_LAST_ACTIVITY"],
            writer=settings.session["WRITER"]):
        """
        Initializer

        Args:
          cookie_path: The path setting for the cookie.
          cookie_domain: The domain setting for the cookie. (Set to False
                        to not use)
          cookie_name: The name for the session cookie stored in the browser.
          session_expire_time: The amount of time between requests before the
              session expires.
          clean_check_percent: The percentage of requests the will fire off a
              cleaning routine that deletes stale session data.
          integrate_flash: If appengine-utilities flash utility should be
              integrated into the session object.
          check_ip: If browser IP should be used for session validation
          check_user_agent: If the browser user agent should be used for
              sessoin validation.
          set_cookie_expires: True adds an expires field to the cookie so
              it saves even if the browser is closed.
          session_token_ttl: Number of sessions a session token is valid
              for before it should be regenerated.
        """

        self.cookie_path = cookie_path
        self.cookie_domain = cookie_domain
        self.cookie_name = cookie_name
        self.session_expire_time = session_expire_time
        self.integrate_flash = integrate_flash
        self.check_user_agent = check_user_agent
        self.check_ip = check_ip
        self.set_cookie_expires = set_cookie_expires
        self.session_token_ttl = session_token_ttl
        self.last_activity_update = last_activity_update
        self.writer = writer

        # make sure the page is not cached in the browser
        print self.no_cache_headers()
        # Check the cookie and, if necessary, create a new one.
        self.cache = {}
        string_cookie = os.environ.get(u"HTTP_COOKIE", u"")
        self.cookie = Cookie.SimpleCookie()
        self.output_cookie = Cookie.SimpleCookie()
        if string_cookie == "":
          self.cookie_vals = {}
        else:
            self.cookie.load(string_cookie)
            try:
                self.cookie_vals = \
                    simplejson.loads(self.cookie["%s_data" % (self.cookie_name)].value)
                    # sync self.cache and self.cookie_vals which will make those
                    # values available for all gets immediately.
                for k in self.cookie_vals:
                    self.cache[k] = self.cookie_vals[k]
                    # sync the input cookie with the output cookie
                    self.output_cookie["%s_data" % (self.cookie_name)] = \
                        simplejson.dumps(self.cookie_vals) #self.cookie["%s_data" % (self.cookie_name)]
            except Exception, e:
                self.cookie_vals = {}


        if writer == "cookie":
            pass
        else:
            self.sid = None
            new_session = True

            # do_put is used to determine if a datastore write should
            # happen on this request.
            do_put = False

            # check for existing cookie
            if self.cookie.get(cookie_name):
                self.sid = self.cookie[cookie_name].value
                # The following will return None if the sid has expired.
                self.session = _AppEngineUtilities_Session.get_session(self)
                if self.session:
                    new_session = False

            if new_session:
                # start a new session
                self.session = _AppEngineUtilities_Session()
                self.session.put()
                self.sid = self.new_sid()
                if u"HTTP_USER_AGENT" in os.environ:
                    self.session.ua = os.environ[u"HTTP_USER_AGENT"]
                else:
                    self.session.ua = None
                if u"REMOTE_ADDR" in os.environ:
                    self.session.ip = os.environ["REMOTE_ADDR"]
                else:
                    self.session.ip = None
                self.session.sid = [self.sid]
                # do put() here to get the session key
                self.session.put()
            else:
                # check the age of the token to determine if a new one
                # is required
                duration = datetime.timedelta(seconds=self.session_token_ttl)
                session_age_limit = datetime.datetime.now() - duration
                if self.session.last_activity < session_age_limit:
                    self.sid = self.new_sid()
                    if len(self.session.sid) > 2:
                        self.session.sid.remove(self.session.sid[0])
                    self.session.sid.append(self.sid)
                    do_put = True
                else:
                    self.sid = self.session.sid[-1]
                    # check if last_activity needs updated
                    ula = datetime.timedelta(seconds=self.last_activity_update)
                    if datetime.datetime.now() > self.session.last_activity + \
                        ula:
                        do_put = True

            self.output_cookie[cookie_name] = self.sid
            self.output_cookie[cookie_name]["path"] = self.cookie_path
            if self.cookie_domain:
                self.output_cookie[cookie_name]["domain"] = self.cookie_domain
            if self.set_cookie_expires:
                self.output_cookie[cookie_name]["expires"] = \
                    self.session_expire_time

            self.cache[u"sid"] = self.sid

            if do_put:
                if self.sid != None or self.sid != u"":
                    self.session.put()

        # Only set the "_data" cookie if there is actual data
        if self.output_cookie.has_key("%s_data" % (cookie_name)):
            # Set the path of the "_data" cookie
            self.output_cookie["%s_data" % (cookie_name)]["path"] = cookie_path
            if self.set_cookie_expires:
                self.output_cookie["%s_data" % (cookie_name)]["expires"] = \
                    self.session_expire_time
        print self.output_cookie.output()

        # fire up a Flash object if integration is enabled
        if self.integrate_flash:
            import flash
            self.flash = flash.Flash(cookie=self.cookie)

        # randomly delete old stale sessions in the datastore (see
        # CLEAN_CHECK_PERCENT variable)
        if random.randint(1, 100) < clean_check_percent:
            self._clean_old_sessions() 

    def new_sid(self):
        """
        Create a new session id.

        Returns session id as a unicode string.
        """
        sid = u"%s_%s" % (str(self.session.key()),
            hashlib.md5(repr(time.time()) + \
            unicode(random.random())).hexdigest()
        )
        #sid = unicode(self.session.session_key) + "_" + \
        #        hashlib.md5(repr(time.time()) + \
        #        unicode(random.random())).hexdigest()
        return sid

    def _get(self, keyname=None):
        """
        private method
        
        Return all of the SessionData object data from the datastore only,
        unless keyname is specified, in which case only that instance of 
        SessionData is returned.

        Important: This does not interact with memcache and pulls directly
        from the datastore. This also does not get items from the cookie
        store.

        Args:
            keyname: The keyname of the value you are trying to retrieve.

        Returns a list of datastore entities.
        """
        if hasattr(self, 'session'):
            if keyname != None:
                return self.session.get_item(keyname)
            return self.session.get_items()
        return None
    
    def _validate_key(self, keyname):
        """
        private method
        
        Validate the keyname, making sure it is set and not a reserved name.

        Returns the validated keyname.
        """
        if keyname is None:
            raise ValueError(
                u"You must pass a keyname for the session data content."
            )
        elif keyname in (u"sid", u"flash"):
            raise ValueError(u"%s is a reserved keyname." % keyname)

        if type(keyname) != type([str, unicode]):
            return unicode(keyname)
        return keyname

    def _put(self, keyname, value):
        """
        Insert a keyname/value pair into the datastore for the session.

        Args:
            keyname: The keyname of the mapping.
            value: The value of the mapping.

        Returns the value from the writer put operation, varies based on writer.
        """
        if self.writer == "datastore":
            writer = _DatastoreWriter()
        else:
            writer = _CookieWriter()

        return writer.put(keyname, value, self)

    def _delete_session(self):
        """
        private method
        
        Delete the session and all session data.

        Returns True.
        """
        # if the event class has been loaded, fire off the preSessionDelete event
        if u"AEU_Events" in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event(u"preSessionDelete")
        if hasattr(self, u"session"):
            self.session.delete()
        self.cookie_vals = {}
        self.cache = {}
        self.output_cookie["%s_data" % (self.cookie_name)] = \
            simplejson.dumps(self.cookie_vals)
        self.output_cookie["%s_data" % (self.cookie_name)]["path"] = \
            self.cookie_path
        if self.cookie_domain:
            self.output_cookie["%s_data" % \
                (self.cookie_name)]["domain"] = self.cookie_domain
        # Delete the cookies (session & data) in the browser
        self.output_cookie[self.cookie_name]["expires"] = 0
        self.output_cookie["%s_data" % (self.cookie_name)]["expires"] = 0

        print self.output_cookie.output()
        # if the event class has been loaded, fire off the sessionDelete event
        if u"AEU_Events" in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event(u"sessionDelete")
        return True

    def delete(self):
        """
        Delete the current session and start a new one.

        This is useful for when you need to get rid of all data tied to a
        current session, such as when you are logging out a user.

        Returns True
        """
        self._delete_session()

    @classmethod
    def delete_all_sessions(cls):
        """
        Deletes all sessions and session data from the data store. This
        does not delete the entities from memcache (yet). Depending on the
        amount of sessions active in your datastore, this request could
        timeout before completion and may have to be called multiple times.

        NOTE: This can not delete cookie only sessions as it has no way to
        access them. It will only delete datastore writer sessions.

        Returns True on completion.
        """
        all_sessions_deleted = False

        while not all_sessions_deleted:
            query = _AppEngineUtilities_Session.all()
            results = query.fetch(75)
            if len(results) is 0:
                all_sessions_deleted = True
            else:
                for result in results:
                    result.delete()
        return True


    def _clean_old_sessions(self):
        """
        Delete 50 expired sessions from the datastore.

        This is only called for CLEAN_CHECK_PERCENT percent of requests because
        it could be rather intensive.

        Returns True on completion
        """
        self.clean_old_sessions(self.session_expire_time, 50)


    @classmethod
    def clean_old_sessions(cls, session_expire_time, count=50):
        """
        Delete expired sessions from the datastore.

        This is a class method which can be used by applications for
        maintenance if they don't want to use the built in session
        cleaning.

        Args:
          count: The amount of session to clean.
          session_expire_time: The age in seconds to determine outdated
                               sessions.

        Returns True on completion
        """
        duration = datetime.timedelta(seconds=session_expire_time)
        session_age = datetime.datetime.now() - duration
        query = _AppEngineUtilities_Session.all()
        query.filter(u"last_activity <", session_age)
        results = query.fetch(50)
        for result in results:
            result.delete()
        return True

    def cycle_key(self):
        """
        Changes the session id/token.

        Returns new token.
        """
        self.sid = self.new_sid()
        if len(self.session.sid) > 2:
            self.session.sid.remove(self.session.sid[0])
        self.session.sid.append(self.sid)
        
        return self.sid

    def flush(self):
        """
        Delete's the current session, creating a new one.

        Returns True
        """
        self._delete_session()
        self.__init__()
        return True

    def no_cache_headers(self):
        """
        Generates headers to avoid any page caching in the browser.
        Useful for highly dynamic sites.

        Returns a unicode string of headers.
        """
        return u"".join([u"Expires: Tue, 03 Jul 2001 06:00:00 GMT",
            strftime("Last-Modified: %a, %d %b %y %H:%M:%S %Z").decode("utf-8"),
            u"Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
            u"Cache-Control: post-check=0, pre-check=0",
            u"Pragma: no-cache",
        ])

    def clear(self):
        """
        Removes session data items, doesn't delete the session. It does work
        with cookie sessions, and must be called before any output is sent
        to the browser, as it set cookies.

        Returns True
        """
        sessiondata = self._get()
        # delete from datastore
        if sessiondata is not None:
            for sd in sessiondata:
                sd.delete()
        # delete from memcache
        self.cache = {}
        self.cookie_vals = {}
        self.output_cookie["%s_data" % (self.cookie_name)] = \
            simplejson.dumps(self.cookie_vals)
        self.output_cookie["%s_data" % (self.cookie_name)]["path"] = \
            self.cookie_path
        if self.cookie_domain:
            self.output_cookie["%s_data" % \
                (self.cookie_name)]["domain"] = self.cookie_domain
        # Delete the "_data" cookie in the browser
        self.output_cookie["%s_data" % (self.cookie_name)]["expires"] = 0

        print self.output_cookie.output()
        return True

    def has_key(self, keyname):
        """
        Equivalent to k in a, use that form in new code

        Args:
            keyname: keyname to check

        Returns True/False
        """
        return self.__contains__(keyname)

    def items(self):
        """
        Creates a copy of just the data items.

        Returns dictionary of session data objects.
        """
        op = {}
        for k in self:
            op[k] = self[k]
        return op

    def keys(self):
        """
        Returns a list of keys.
        """
        l = []
        for k in self:
            l.append(k)
        return l

    def update(self, *dicts):
        """
        Updates with key/value pairs from b, overwriting existing keys

        Returns None
        """
        for dict in dicts:
            for k in dict:
                self._put(k, dict[k])
        return None

    def values(self):
        """
        Returns a list object of just values in the session.
        """
        v = []
        for k in self:
            v.append(self[k])
        return v

    def get(self, keyname, default = None):
        """
        Returns either the value for the keyname or a default value
        passed.

        Args:
            keyname: keyname to look up
            default: (optional) value to return on keyname miss

        Returns value of keyname, or default, or None
        """
        try:
            return self.__getitem__(keyname)
        except KeyError:
            if default is not None:
                return default
            return None

    def setdefault(self, keyname, default = None):
        """
        Returns either the value for the keyname or a default value
        passed. If keyname lookup is a miss, the keyname is set with
        a value of default.

        Args:
            keyname: keyname to look up
            default: (optional) value to return on keyname miss

        Returns value of keyname, or default, or None
        """
        try:
            return self.__getitem__(keyname)
        except KeyError:
            if default is not None:
                self.__setitem__(keyname, default)
                return default
            return None

    @classmethod
    def check_token(cls, cookie_name=COOKIE_NAME, delete_invalid=True):
        """
        Retrieves the token from a cookie and validates that it is
        a valid token for an existing cookie. Cookie validation is based
        on the token existing on a session that has not expired.

        This is useful for determining if datastore or cookie writer
        should be used in hybrid implementations.

        Args:
            cookie_name: Name of the cookie to check for a token.
            delete_invalid: If the token is not valid, delete the session
                            cookie, to avoid datastore queries on future
                            requests.

        Returns True/False
        """

        string_cookie = os.environ.get(u"HTTP_COOKIE", u"")
        cookie = Cookie.SimpleCookie()
        cookie.load(string_cookie)
        if cookie.has_key(cookie_name):
            query = _AppEngineUtilities_Session.all()
            query.filter(u"sid", cookie[cookie_name].value)
            results = query.fetch(1)
            if len(results) > 0:
                return True
            else:
                if delete_invalid:
                    output_cookie = Cookie.SimpleCookie()
                    output_cookie[cookie_name] = cookie[cookie_name]
                    output_cookie[cookie_name][u"expires"] = 0
                    print output_cookie.output()
        return False

    def get_ds_entity(self):
        """
        Will return the session entity from the datastore if one
        exists, otherwise will return None (as in the case of cookie writer
        session.
        """
        if hasattr(self, u"session"):
            return self.session
        return None

    # Implement Python container methods

    def __getitem__(self, keyname):
        """
        Get item from session data.

        keyname: The keyname of the mapping.
        """
        # flash messages don't go in the datastore

        if self.integrate_flash and (keyname == u"flash"):
            return self.flash.msg
        if keyname in self.cache:
            return self.cache[keyname]
        if keyname in self.cookie_vals:
            return self.cookie_vals[keyname]
        if hasattr(self, u"session"):
            data = self._get(keyname)
            if data:
                # TODO: It's broke here, but I'm not sure why, it's
                # returning a model object, but I can't seem to modify
                # it.
                try:
                    if data.model != None:
                        self.cache[keyname] = data.model
                        return self.cache[keyname]
                    else:
                        self.cache[keyname] = pickle.loads(data.content)
                        return self.cache[keyname]
                except:
                    self.delete_item(keyname)

            else:
                raise KeyError(unicode(keyname))
        raise KeyError(unicode(keyname))

    def __setitem__(self, keyname, value):
        """
        Set item in session data.

        Args:
            keyname: They keyname of the mapping.
            value: The value of mapping.
        """

        if self.integrate_flash and (keyname == u"flash"):
            self.flash.msg = value
        else:
            keyname = self._validate_key(keyname)
            self.cache[keyname] = value
            return self._put(keyname, value)

    def delete_item(self, keyname, throw_exception=False):
        """
        Delete item from session data, ignoring exceptions if
        necessary.

        Args:
            keyname: The keyname of the object to delete.
            throw_exception: false if exceptions are to be ignored.
        Returns:
            Nothing.
        """
        if throw_exception:
            self.__delitem__(keyname)
            return None
        else:
            try:
                self.__delitem__(keyname)
            except KeyError:
                return None

    def __delitem__(self, keyname):
        """
        Delete item from session data.

        Args:
            keyname: The keyname of the object to delete.
        """
        bad_key = False
        sessdata = self._get(keyname = keyname)
        if sessdata is None:
            bad_key = True
        else:
            sessdata.delete()
        if keyname in self.cookie_vals:
            del self.cookie_vals[keyname]
            bad_key = False
            self.output_cookie["%s_data" % (self.cookie_name)] = \
                simplejson.dumps(self.cookie_vals)
            self.output_cookie["%s_data" % (self.cookie_name)]["path"] = \
                self.cookie_path
            if self.cookie_domain:
                self.output_cookie["%s_data" % \
                    (self.cookie_name)]["domain"] = self.cookie_domain

            print self.output_cookie.output()
        if bad_key:
            raise KeyError(unicode(keyname))
        if keyname in self.cache:
            del self.cache[keyname]

    def __len__(self):
        """
        Return size of session.
        """
        # check memcache first
        if hasattr(self, u"session"):
            results = self._get()
            if results is not None:
                return len(results) + len(self.cookie_vals)
            else:
                return 0
        return len(self.cookie_vals)

    def __contains__(self, keyname):
        """
        Check if an item is in the session data.

        Args:
            keyname: The keyname being searched.
        """
        try:
            self.__getitem__(keyname)
        except KeyError:
            return False
        return True

    def __iter__(self):
        """
        Iterate over the keys in the session data.
        """
        # try memcache first
        if hasattr(self, u"session"):
            vals = self._get()
            if vals is not None:
                for k in vals:
                    yield k.keyname
        for k in self.cookie_vals:
            yield k

    def __str__(self):
        """
        Return string representation.
        """
        return u"{%s}" % ', '.join(['"%s" = "%s"' % (k, self[k]) for k in self])

########NEW FILE########
__FILENAME__ = sessions2
# -*- coding: utf-8 -*-
"""
Copyright (c) 2010, gaeutilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the appengine-utilities project nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# main python imports
import os
import time
import datetime
import random
import hashlib
import Cookie
import pickle
import sys
import logging
from time import strftime

# google appengine imports
from google.appengine.ext import db
from google.appengine.api import memcache

from django.utils import simplejson

# settings
try:
    import settings_default
    import settings

    if settings.__name__.rsplit('.', 1)[0] != settings_default.__name__.rsplit('.', 1)[0]:
        settings = settings_default
except:
    settings = settings_default




class _AppEngineUtilities_Session(db.Model):
    """
    Model for the sessions in the datastore. This contains the identifier and
    validation information for the session.
    """

    sid = db.StringListProperty()
    ip = db.StringProperty()
    ua = db.StringProperty()
    last_activity = db.DateTimeProperty()
    dirty = db.BooleanProperty(default=False)
    working = db.BooleanProperty(default=False)
    deleted = db.BooleanProperty(default=False) 

    def put(self):
        """
        Extends put so that it writes vaules to memcache as well as the
        datastore, and keeps them in sync, even when datastore writes fails.

        Returns the session object.
        """
        try:
            memcache.set(u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())), self)
        except:
            # new session, generate a new key, which will handle the
            # put and set the memcache
            db.put(self)

        self.last_activity = datetime.datetime.now()

        try:
            self.dirty = False
            db.put(self)
            memcache.set(u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())), self)
        except:
            self.dirty = True
            memcache.set(u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())), self)

        return self

    @classmethod
    def get_session(cls, session_obj=None):
        """
        Uses the passed objects sid to get a session object from memcache,
        or datastore if a valid one exists.

        Args:
            session_obj: a session object

        Returns a validated session object.
        """
        if session_obj.sid == None:
            return None
        session_key = session_obj.sid.rsplit(u'_', 1)[0]
        session = memcache.get(u"_AppEngineUtilities_Session_%s" % \
            (str(session_key)))
        if session:
            if session.deleted == True:
                session.delete()
                return None
            if session.dirty == True and session.working != False:
                # the working bit is used to make sure multiple requests,
                # which can happen with ajax oriented sites, don't try to put
                # at the same time
                session.working = True
                memcache.set(u"_AppEngineUtilities_Session_%s" % \
                    (str(session_key)), session)
                session.put()
            if session_obj.sid in session.sid:
                sessionAge = datetime.datetime.now() - session.last_activity
                if sessionAge.seconds > session_obj.session_expire_time:
                    session.delete()
                    return None
                return session
            else:
                return None
 
        # Not in memcache, check datastore
        
        try:
            ds_session = db.get(str(session_key))
        except:
            ds_session = None
        if ds_session:
          sessionAge = datetime.datetime.now() - ds_session.last_activity
          if sessionAge.seconds > session_obj.session_expire_time:
              ds_session.delete()
              return None
          memcache.set(u"_AppEngineUtilities_Session_%s" % \
              (str(session_key)), ds_session)
          memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
              (str(session_key)), ds_session.get_items_ds())
        return ds_session


    def get_items(self):
        """
        Returns all the items stored in a session. Queries memcache first
        and will try the datastore next.
        """
        items = memcache.get(u"_AppEngineUtilities_SessionData_%s" % \
            (str(self.key())))
        if items:
            for item in items:
                if item.deleted == True:
                    item.delete()
                    items.remove(item)
            return items

        query = _AppEngineUtilities_SessionData.all()
        query.filter(u"session", self)
        results = query.fetch(1000)
        return results

    def get_item(self, keyname = None):
        """
        Returns a single session data item from the memcache or datastore

        Args:
            keyname: keyname of the session data object

        Returns the session data object if it exists, otherwise returns None
        """
        mc = memcache.get(u"_AppEngineUtilities_SessionData_%s" % \
            (str(self.key())))
        if mc:
            for item in mc:
                if item.keyname == keyname:
                    if item.deleted == True:
                        item.delete()
                        return None
                    return item
        query = _AppEngineUtilities_SessionData.all()
        query.filter(u"session = ", self)
        query.filter(u"keyname = ", keyname)
        results = query.fetch(1)
        if len(results) > 0:
            memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
                (str(self.key())), self.get_items_ds())
            return results[0]
        return None

    def get_items_ds(self):
        """
        This gets all session data objects from the datastore, bypassing
        memcache.

        Returns a list of session data entities.
        """
        query = _AppEngineUtilities_SessionData.all()
        query.filter(u"session", self)
        results = query.fetch(1000)
        return results

    def delete(self):
        """
        Deletes a session and all it's associated data from the datastore and
        memcache.

        Returns True
        """
        try:
            query = _AppEngineUtilities_SessionData.all()
            query.filter(u"session = ", self)
            results = query.fetch(1000)
            db.delete(results)
            db.delete(self)
            memcache.delete_multi([u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())), \
                u"_AppEngineUtilities_SessionData_%s" % \
                (str(self.key()))])
        except:
            mc = memcache.get(u"_AppEngineUtilities_Session_%s" % \
                (str(self.key())))
            if mc:
                mc.deleted = True
            else:
                # not in the memcache, check to see if it should be
                query = _AppEngineUtilities_Session.all()
                query.filter(u"sid = ", self.sid)
                results = query.fetch(1)
                if len(results) > 0:
                    results[0].deleted = True
                    memcache.set(u"_AppEngineUtilities_Session_%s" % \
                        (unicode(self.key())), results[0])
        return True
            
class _AppEngineUtilities_SessionData(db.Model):
    """
    Model for the session data in the datastore.
    """

    # session_key = db.FloatProperty()
    keyname = db.StringProperty()
    content = db.BlobProperty()
    model = db.ReferenceProperty()
    session = db.ReferenceProperty(_AppEngineUtilities_Session)
    dirty = db.BooleanProperty(default=False)
    deleted = db.BooleanProperty(default=False)

    def put(self):
        """
        Adds a keyname/value for session to the datastore and memcache

        Returns the key from the datastore put or u"dirty"
        """
        # update or insert in datastore
        try:
            return_val = db.put(self)
            self.dirty = False
        except:
            return_val = u"dirty"
            self.dirty = True

        # update or insert in memcache
        mc_items = memcache.get(u"_AppEngineUtilities_SessionData_%s" % \
            (str(self.session.key())))
        if mc_items:
            value_updated = False
            for item in mc_items:
                if value_updated == True:
                    break
                if item.keyname == self.keyname:
                    item.content = self.content
                    item.model = self.model
                    memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
                        (str(self.session.key())), mc_items)
                    value_updated = True
                    break
            if value_updated == False:
                mc_items.append(self)
                memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
                    (str(self.session.key())), mc_items)
        return return_val

    def delete(self):
        """
        Deletes an entity from the session in memcache and the datastore

        Returns True
        """
        try:
            db.delete(self)
        except:
            self.deleted = True
        mc_items = memcache.get(u"_AppEngineUtilities_SessionData_%s" % \
            (str(self.session.key())))
        value_handled = False
        for item in mc_items:
            if value_handled == True:
                break
            if item.keyname == self.keyname:
                if self.deleted == True:
                    item.deleted = True
                else:
                    mc_items.remove(item)
                memcache.set(u"_AppEngineUtilities_SessionData_%s" % \
                    (str(self.session.key())), mc_items)
        return True
        

class _DatastoreWriter(object):

    def write_session(self, session, keys):
        vals = []
        for keyname in keys:
            sessdata = session._get(keyname=keyname)
            if sessdata is None:
                sessdata = _AppEngineUtilities_SessionData()
                sessdata.keyname = keyname

            try:
                db.model_to_protobuf(value)
                if not value.is_saved():
                    value.put()
                sessdata.model = value
            except:
                sessdata.content = pickle.dumps(value)
                sessdata.model = None
            sessdata.session = session.session
            vals.append(sessdata)
            #TODO working here, need to move putting into memcache here,
            # the _AppEngineUtilities_SessionData model will become a standard
            # model and lose the put() override.
        db.put(vals)

    def put(self, keyname, value, session):
        """
        Insert a keyname/value pair into the datastore for the session.

        Args:
            keyname: The keyname of the mapping.
            value: The value of the mapping.

        Returns the model entity key
        """
        keyname = session._validate_key(keyname)
        if value is None:
            raise ValueError(u"You must pass a value to put.")

        sessdata = session._get(keyname=keyname)
        if sessdata is None:
            sessdata = _AppEngineUtilities_SessionData()
            # sessdata.session_key = session.session.key()
            sessdata.keyname = keyname
        try:
            db.model_to_protobuf(value)
            if not value.is_saved():
                value.put()
            sessdata.model = value
        except:
            sessdata.content = pickle.dumps(value)
            sessdata.model = None
        sessdata.session = session.session
            
        session.cache[keyname] = value
        return sessdata.put()


class _CookieWriter(object):
    def put(self, keyname, value, session):
        """
        Insert a keyname/value pair into the datastore for the session.

        Args:
            keyname: The keyname of the mapping.
            value: The value of the mapping.

        Returns True
        """
        keyname = session._validate_key(keyname)
        if value is None:
            raise ValueError(u"You must pass a value to put.")

        # Use simplejson for cookies instead of pickle.
        session.cookie_vals[keyname] = value
        # update the requests session cache as well.
        session.cache[keyname] = value
        # simplejson will raise any error I'd raise about an invalid value
        # so let it raise exceptions
        session.output_cookie["%s_data" % (session.cookie_name)] = \
            simplejson.dumps(session.cookie_vals)
        session.output_cookie["%s_data" % (session.cookie_name)]["path"] = \
            session.cookie_path
        if session.cookie_domain:
            session.output_cookie["%s_data" % \
                (session.cookie_name)]["domain"] = session.cookie_domain
        print session.output_cookie.output()
        return True

class Session(object):
    """
    Sessions are used to maintain user presence between requests.

    Sessions can either be stored server side in the datastore/memcache, or
    be kept entirely as cookies. This is set either with the settings file
    or on initialization, using the writer argument/setting field. Valid
    values are "datastore" or "cookie".

    Session can be used as a standard dictionary object.
        session = appengine_utilities.sessions.Session()
        session["keyname"] = "value" # sets keyname to value
        print session["keyname"] # will print value

    Datastore Writer:
        The datastore writer was written with the focus being on security,
        reliability, and performance. In that order.

        It is based off of a session token system. All data is stored
        server side in the datastore and memcache. A token is given to
        the browser, and stored server side. Optionally (and on by default),
        user agent and ip checking is enabled. Tokens have a configurable
        time to live (TTL), which defaults to 5 seconds. The current token,
        plus the previous 2, are valid for any request. This is done in order
        to manage ajax enabled sites which may have more than on request
        happening at a time. This means any token is valid for 15 seconds.
        A request with a token who's TTL has passed will have a new token
        generated.

        In order to take advantage of the token system for an authentication
        system, you will want to tie sessions to accounts, and make sure
        only one session is valid for an account. You can do this by setting
        a db.ReferenceProperty(_AppEngineUtilities_Session) attribute on
        your user Model, and use the get_ds_entity() method on a valid
        session to populate it on login.

        Note that even with this complex system, sessions can still be hijacked
        and it will take the user logging in to retrieve the account. In the
        future an ssl only cookie option may be implemented for the datastore
        writer, which would further protect the session token from being
        sniffed, however it would be restricted to using cookies on the
        .appspot.com domain, and ssl requests are a finite resource. This is
        why such a thing is not currently implemented.

        Session data objects are stored in the datastore pickled, so any
        python object is valid for storage.

    Cookie Writer:
        Sessions using the cookie writer are stored entirely in the browser
        and no interaction with the datastore is required. This creates
        a drastic improvement in performance, but provides no security for
        session hijack. This is useful for requests where identity is not
        important, but you wish to keep state between requests.

        Information is stored in a json format, as pickled data from the
        server is unreliable.

        Note: There is no checksum validation of session data on this method,
        it's streamlined for pure performance. If you need to make sure data
        is not tampered with, use the datastore writer which stores the data
        server side.

    django-middleware:
        Included with the GAEUtilties project is a
        django-middleware.middleware.SessionMiddleware which can be included in
        your settings file. This uses the cookie writer for anonymous requests,
        and you can switch to the datastore writer on user login. This will
        require an extra set in your login process of calling
        request.session.save() once you validated the user information. This
        will convert the cookie writer based session to a datastore writer.
    """

    # cookie name declaration for class methods
    COOKIE_NAME = settings.session["COOKIE_NAME"]

    def __init__(self, cookie_path=settings.session["DEFAULT_COOKIE_PATH"],
            cookie_domain=settings.session["DEFAULT_COOKIE_DOMAIN"],
            cookie_name=settings.session["COOKIE_NAME"],
            session_expire_time=settings.session["SESSION_EXPIRE_TIME"],
            clean_check_percent=settings.session["CLEAN_CHECK_PERCENT"],
            integrate_flash=settings.session["INTEGRATE_FLASH"],
            check_ip=settings.session["CHECK_IP"],
            check_user_agent=settings.session["CHECK_USER_AGENT"],
            set_cookie_expires=settings.session["SET_COOKIE_EXPIRES"],
            session_token_ttl=settings.session["SESSION_TOKEN_TTL"],
            last_activity_update=settings.session["UPDATE_LAST_ACTIVITY"],
            writer=settings.session["WRITER"]):
        """
        Initializer

        Args:
          request: The request handler being decorated.
          cookie_path: The path setting for the cookie.
          cookie_domain: The domain setting for the cookie. (Set to False
                        to not use)
          cookie_name: The name for the session cookie stored in the browser.
          session_expire_time: The amount of time between requests before the
              session expires.
          clean_check_percent: The percentage of requests the will fire off a
              cleaning routine that deletes stale session data.
          integrate_flash: If appengine-utilities flash utility should be
              integrated into the session object.
          check_ip: If browser IP should be used for session validation
          check_user_agent: If the browser user agent should be used for
              sessoin validation.
          set_cookie_expires: True adds an expires field to the cookie so
              it saves even if the browser is closed.
          session_token_ttl: Number of sessions a session token is valid
              for before it should be regenerated.
        """

        self.cookie_path = cookie_path
        self.cookie_domain = cookie_domain
        self.cookie_name = cookie_name
        self.session_expire_time = session_expire_time
        self.integrate_flash = integrate_flash
        self.check_user_agent = check_user_agent
        self.check_ip = check_ip
        self.set_cookie_expires = set_cookie_expires
        self.session_token_ttl = session_token_ttl
        self.last_activity_update = last_activity_update
        self.writer = writer

    def __call__(self, f):
        # make sure the page is not cached in the browser
        print self.no_cache_headers()

        # cache object is used to store write items as the session is processed.
        # This avoids multiple calls to the datastore or cookie processing if
        # session variable has already been accessed.
        self.cache = {}
        
        # Check the cookie and, if necessary, create a new one.
        string_cookie = os.environ.get(u"HTTP_COOKIE", u"")
        self.cookie = Cookie.SimpleCookie()
        self.output_cookie = Cookie.SimpleCookie()
        if string_cookie == "":
          self.cookie_vals = {}
        else:
            self.cookie.load(string_cookie)
            try:
                self.cookie_vals = \
                    simplejson.loads(self.cookie["%s_data" % (self.cookie_name)].value)
                    # sync self.cache and self.cookie_vals which will make those
                    # values available for all gets immediately.
                for k in self.cookie_vals:
                    self.cache[k] = self.cookie_vals[k]
                    # sync the input cookie with the output cookie
                    self.output_cookie["%s_data" % (self.cookie_name)] = \
                        simplejson.dumps(self.cookie_vals) #self.cookie["%s_data" % (self.cookie_name)]
            except Exception:
                self.cookie_vals = {}


        if self.writer == "cookie":
            pass
        else:
            # write_cache and del_cache are used for batch write operations
            # after the request has been processed for datastore sessions.
            # Objects may also exist in self.cache meaning the value is stored
            # in multiple locations in memory, however session data should be
            # small so this should not create much overhead in most use cases.
            self.write_cache = {}
            self.del_cache = []
            
            self.sid = None
            new_session = True

            # do_put is used to determine if a datastore write should
            # happen on this request.
            do_put = False

            # check for existing cookie
            if self.cookie.get(cookie_name):
                self.sid = self.cookie[cookie_name].value
                
                # The following will return None if the sid has expired.
                self.session = _AppEngineUtilities_Session.get_session(self)
                if self.session:
                    new_session = False

            if new_session:
                # start a new session
                self.session = _AppEngineUtilities_Session()
                self.session.put()
                self.sid = self.new_sid()
                if u"HTTP_USER_AGENT" in os.environ:
                    self.session.ua = os.environ[u"HTTP_USER_AGENT"]
                else:
                    self.session.ua = None
                if u"REMOTE_ADDR" in os.environ:
                    self.session.ip = os.environ["REMOTE_ADDR"]
                else:
                    self.session.ip = None
                self.session.sid = [self.sid]
                # do put() here to get the session key
                self.session.put()
            else:
                # check the age of the token to determine if a new one
                # is required
                duration = datetime.timedelta(seconds=self.session_token_ttl)
                session_age_limit = datetime.datetime.now() - duration
                if self.session.last_activity < session_age_limit:
                    self.sid = self.new_sid()
                    if len(self.session.sid) > 2:
                        self.session.sid.remove(self.session.sid[0])
                    self.session.sid.append(self.sid)
                    do_put = True
                else:
                    self.sid = self.session.sid[-1]
                    # check if last_activity needs updated
                    ula = datetime.timedelta(seconds=self.last_activity_update)
                    if datetime.datetime.now() > self.session.last_activity + \
                        ula:
                        do_put = True

            self.output_cookie[cookie_name] = self.sid
            self.output_cookie[cookie_name]["path"] = self.cookie_path
            if self.cookie_domain:
                self.output_cookie[cookie_name]["domain"] = self.cookie_domain
            if self.set_cookie_expires:
                self.output_cookie[cookie_name]["expires"] = \
                    self.session_expire_time

            self.cache[u"sid"] = self.sid

            #TODO See if this write can deferred. Since the cookie token
            # is being set in the headers, it may not be the case. Need to
            # at lease validate self.put() still does this write once I
            # am done making changes.
            #
            # It's a result of the security created by rotating tokens that
            # requires this write on requests where the session token changes.
            if do_put:
                if self.sid != None or self.sid != u"":
                    self.session.put()

        # Only set the "_data" cookie if there is actual data
        if self.output_cookie.has_key("%s_data" % (cookie_name)):
            # Set the path of the "_data" cookie
            self.output_cookie["%s_data" % (cookie_name)]["path"] = cookie_path
            if self.set_cookie_expires:
                self.output_cookie["%s_data" % (cookie_name)]["expires"] = \
                    self.session_expire_time
        print self.output_cookie.output()

        # fire up a Flash object if integration is enabled
        if self.integrate_flash:
            import flash
            self.flash = flash.Flash(cookie=self.cookie)

        # Run the request
        f.gaeusession = self
        f()
        
        # randomly delete old stale sessions in the datastore (see
        # CLEAN_CHECK_PERCENT variable)
        if random.randint(1, 100) < clean_check_percent:
            self._clean_old_sessions() 



    def new_sid(self):
        """
        Create a new session id.

        Returns session id as a unicode string.
        """
        sid = u"%s_%s" % (str(self.session.key()),
            hashlib.md5(repr(time.time()) + \
            unicode(random.random())).hexdigest()
        )
        return sid

    def _get(self, keyname=None):
        """
        private method
        
        Return all of the SessionData object data from the datastore only,
        unless keyname is specified, in which case only that instance of 
        SessionData is returned.

        Important: This does not interact with memcache and pulls directly
        from the datastore. This also does not get items from the cookie
        store.

        Args:
            keyname: The keyname of the value you are trying to retrieve.

        Returns a list of datastore entities.
        """
        if hasattr(self, 'session'):
            if keyname != None:
                return self.session.get_item(keyname)
            return self.session.get_items()
        return None
    
    def _validate_key(self, keyname):
        """
        private method
        
        Validate the keyname, making sure it is set and not a reserved name.

        Returns the validated keyname.
        """
        if keyname is None:
            raise ValueError(
                u"You must pass a keyname for the session data content."
            )
        elif keyname in (u"sid", u"flash"):
            raise ValueError(u"%s is a reserved keyname." % keyname)

        if type(keyname) != type([str, unicode]):
            return unicode(keyname)
        return keyname

    def _put(self, keyname, value):
        """
        Insert a keyname/value pair into the datastore for the session.

        Args:
            keyname: The keyname of the mapping.
            value: The value of the mapping.

        Returns the value from the writer put operation, varies based on writer.
        """
        if self.writer == "datastore":
        # datestore write trumps cookie. If there is a cookie value
        # with this keyname, delete it so we don't have conflicting
        # entries.
            if self.cookie_vals.has_key(keyname):
                del(self.cookie_vals[keyname])
                self.output_cookie["%s_data" % (self.cookie_name)] = \
                    simplejson.dumps(self.cookie_vals)
                self.output_cookie["%s_data" % (self.cookie_name)]["path"] = \
                    self.cookie_path
                if self.cookie_domain:
                    self.output_cookie["%s_data" % \
                        (self.cookie_name)]["domain"] = self.cookie_domain
                print self.output_cookie.output()
            self.write_cache[keyname] = value
            return True
        else:
            writer = _CookieWriter()
            return writer.put(keyname, value, self)

    def _delete_session(self):
        """
        private method
        
        Delete the session and all session data.

        Returns True.
        """
        # if the event class has been loaded, fire off the preSessionDelete event
        if u"AEU_Events" in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event(u"preSessionDelete")
        if hasattr(self, u"session"):
            self.session.delete()
        self.cookie_vals = {}
        self.cache = {}
        self.output_cookie["%s_data" % (self.cookie_name)] = \
            simplejson.dumps(self.cookie_vals)
        self.output_cookie["%s_data" % (self.cookie_name)]["path"] = \
            self.cookie_path
        if self.cookie_domain:
            self.output_cookie["%s_data" % \
                (self.cookie_name)]["domain"] = self.cookie_domain
        # Delete the cookies (session & data) in the browser
        self.output_cookie[self.cookie_name]["expires"] = 0
        self.output_cookie["%s_data" % (self.cookie_name)]["expires"] = 0

        print self.output_cookie.output()
        # if the event class has been loaded, fire off the sessionDelete event
        if u"AEU_Events" in sys.modules['__main__'].__dict__:
            sys.modules['__main__'].AEU_Events.fire_event(u"sessionDelete")
        return True

    def delete(self):
        """
        Delete the current session and start a new one.

        This is useful for when you need to get rid of all data tied to a
        current session, such as when you are logging out a user.

        Returns True
        """
        self._delete_session()

    @classmethod
    def delete_all_sessions(cls):
        """
        Deletes all sessions and session data from the data store. This
        does not delete the entities from memcache (yet). Depending on the
        amount of sessions active in your datastore, this request could
        timeout before completion and may have to be called multiple times.

        NOTE: This can not delete cookie only sessions as it has no way to
        access them. It will only delete datastore writer sessions.

        Returns True on completion.
        """
        all_sessions_deleted = False

        while not all_sessions_deleted:
            query = _AppEngineUtilities_Session.all()
            results = query.fetch(75)
            if len(results) is 0:
                all_sessions_deleted = True
            else:
                for result in results:
                    result.delete()
        return True


    def _clean_old_sessions(self):
        """
        Delete 50 expired sessions from the datastore.

        This is only called for CLEAN_CHECK_PERCENT percent of requests because
        it could be rather intensive.

        Returns True on completion
        """
        self.clean_old_sessions(self.session_expire_time, 50)


    @classmethod
    def clean_old_sessions(cls, session_expire_time, count=50):
        """
        Delete expired sessions from the datastore.

        This is a class method which can be used by applications for
        maintenance if they don't want to use the built in session
        cleaning.

        Args:
          count: The amount of session to clean.
          session_expire_time: The age in seconds to determine outdated
                               sessions.

        Returns True on completion
        """
        duration = datetime.timedelta(seconds=session_expire_time)
        session_age = datetime.datetime.now() - duration
        query = _AppEngineUtilities_Session.all()
        query.filter(u"last_activity <", session_age)
        results = query.fetch(50)
        for result in results:
            result.delete()
        return True

    def cycle_key(self):
        """
        Changes the session id/token.

        Returns new token.
        """
        self.sid = self.new_sid()
        if len(self.session.sid) > 2:
            self.session.sid.remove(self.session.sid[0])
        self.session.sid.append(self.sid)
        
        return self.sid

    def flush(self):
        """
        Delete's the current session, creating a new one.

        Returns True
        """
        self._delete_session()
        self.__init__()
        return True

    def no_cache_headers(self):
        """
        Generates headers to avoid any page caching in the browser.
        Useful for highly dynamic sites.

        Returns a unicode string of headers.
        """
        return u"".join([u"Expires: Tue, 03 Jul 2001 06:00:00 GMT",
            strftime("Last-Modified: %a, %d %b %y %H:%M:%S %Z").decode("utf-8"),
            u"Cache-Control: no-store, no-cache, must-revalidate, max-age=0",
            u"Cache-Control: post-check=0, pre-check=0",
            u"Pragma: no-cache",
        ])

    def clear(self):
        """
        Removes session data items, doesn't delete the session. It does work
        with cookie sessions, and must be called before any output is sent
        to the browser, as it set cookies.

        Returns True
        """
        sessiondata = self._get()
        # delete from datastore
        if sessiondata is not None:
            for sd in sessiondata:
                sd.delete()
        # delete from memcache
        self.cache = {}
        self.cookie_vals = {}
        self.output_cookie["%s_data" % (self.cookie_name)] = \
            simplejson.dumps(self.cookie_vals)
        self.output_cookie["%s_data" % (self.cookie_name)]["path"] = \
            self.cookie_path
        if self.cookie_domain:
            self.output_cookie["%s_data" % \
                (self.cookie_name)]["domain"] = self.cookie_domain
        # Delete the "_data" cookie in the browser
        self.output_cookie["%s_data" % (self.cookie_name)]["expires"] = 0

        print self.output_cookie.output()
        return True

    def has_key(self, keyname):
        """
        Equivalent to k in a, use that form in new code

        Args:
            keyname: keyname to check

        Returns True/False
        """
        return self.__contains__(keyname)

    def items(self):
        """
        Creates a copy of just the data items.

        Returns dictionary of session data objects.
        """
        op = {}
        for k in self:
            op[k] = self[k]
        return op

    def keys(self):
        """
        Returns a list of keys.
        """
        l = []
        for k in self:
            l.append(k)
        return l

    def update(self, *dicts):
        """
        Updates with key/value pairs from b, overwriting existing keys

        Returns None
        """
        for dict in dicts:
            for k in dict:
                self._put(k, dict[k])
        return None

    def values(self):
        """
        Returns a list object of just values in the session.
        """
        v = []
        for k in self:
            v.append(self[k])
        return v

    def get(self, keyname, default = None):
        """
        Returns either the value for the keyname or a default value
        passed.

        Args:
            keyname: keyname to look up
            default: (optional) value to return on keyname miss

        Returns value of keyname, or default, or None
        """
        try:
            return self.__getitem__(keyname)
        except KeyError:
            if default is not None:
                return default
            return None

    def setdefault(self, keyname, default = None):
        """
        Returns either the value for the keyname or a default value
        passed. If keyname lookup is a miss, the keyname is set with
        a value of default.

        Args:
            keyname: keyname to look up
            default: (optional) value to return on keyname miss

        Returns value of keyname, or default, or None
        """
        try:
            return self.__getitem__(keyname)
        except KeyError:
            if default is not None:
                self.__setitem__(keyname, default)
                return default
            return None

    @classmethod
    def check_token(cls, cookie_name=COOKIE_NAME, delete_invalid=True):
        """
        Retrieves the token from a cookie and validates that it is
        a valid token for an existing cookie. Cookie validation is based
        on the token existing on a session that has not expired.

        This is useful for determining if datastore or cookie writer
        should be used in hybrid implementations.

        Args:
            cookie_name: Name of the cookie to check for a token.
            delete_invalid: If the token is not valid, delete the session
                            cookie, to avoid datastore queries on future
                            requests.

        Returns True/False
        """

        string_cookie = os.environ.get(u"HTTP_COOKIE", u"")
        cookie = Cookie.SimpleCookie()
        cookie.load(string_cookie)
        if cookie.has_key(cookie_name):
            query = _AppEngineUtilities_Session.all()
            query.filter(u"sid", cookie[cookie_name].value)
            results = query.fetch(1)
            if len(results) > 0:
                return True
            else:
                if delete_invalid:
                    output_cookie = Cookie.SimpleCookie()
                    output_cookie[cookie_name] = cookie[cookie_name]
                    output_cookie[cookie_name][u"expires"] = 0
                    print output_cookie.output()
        return False

    def get_ds_entity(self):
        """
        Will return the session entity from the datastore if one
        exists, otherwise will return None (as in the case of cookie writer
        session.
        """
        if hasattr(self, u"session"):
            return self.session
        return None

    def delete_item(self, keyname, throw_exception=False):
        """
        Delete item from session data, ignoring exceptions if
        necessary.

        Args:
            keyname: The keyname of the object to delete.
            throw_exception: false if exceptions are to be ignored.
        Returns:
            Nothing.
        """
        if throw_exception:
            self.__delitem__(keyname)
            return None
        else:
            try:
                self.__delitem__(keyname)
            except KeyError:
                return None

    # Implement Python container methods

    def __getitem__(self, keyname):
        """
        Get item from session data.

        keyname: The keyname of the mapping.
        """
        # flash messages don't go in the datastore

        if self.integrate_flash and (keyname == u"flash"):
            return self.flash.msg
        if keyname in self.cache:
            return self.cache[keyname]
        if keyname in self.cookie_vals:
            return self.cookie_vals[keyname]
        if hasattr(self, u"session"):
            data = self._get(keyname)
            if data:
                try:
                    if data.model != None:
                        self.cache[keyname] = data.model
                        return self.cache[keyname]
                    else:
                        self.cache[keyname] = pickle.loads(data.content)
                        return self.cache[keyname]
                except:
                    self.delete_item(keyname)

            else:
                raise KeyError(unicode(keyname))
        raise KeyError(unicode(keyname))

    def __setitem__(self, keyname, value):
        """
        Set item in session data.

        Args:
            keyname: They keyname of the mapping.
            value: The value of mapping.
        """

        if self.integrate_flash and (keyname == u"flash"):
            self.flash.msg = value
        else:
            keyname = self._validate_key(keyname)
            self.cache[keyname] = value
            return self._put(keyname, value)

    def __delitem__(self, keyname):
        """
        Delete item from session data.

        Args:
            keyname: The keyname of the object to delete.
        """
        bad_key = False
        sessdata = self._get(keyname = keyname)
        if sessdata is None:
            bad_key = True
        else:
            self.del_cache.append(keyname)
        if keyname in self.cookie_vals:
            del self.cookie_vals[keyname]
            bad_key = False
            self.output_cookie["%s_data" % (self.cookie_name)] = \
                simplejson.dumps(self.cookie_vals)
            self.output_cookie["%s_data" % (self.cookie_name)]["path"] = \
                self.cookie_path
            if self.cookie_domain:
                self.output_cookie["%s_data" % \
                    (self.cookie_name)]["domain"] = self.cookie_domain

            print self.output_cookie.output()
        if bad_key:
            raise KeyError(unicode(keyname))
        if keyname in self.cache:
            del self.cache[keyname]

    def __len__(self):
        """
        Return size of session.
        """
        # check memcache first
        if hasattr(self, u"session"):
            results = self._get()
            if results is not None:
                return len(results) + len(self.cookie_vals)
            else:
                return 0
        return len(self.cookie_vals)

    def __contains__(self, keyname):
        """
        Check if an item is in the session data.

        Args:
            keyname: The keyname being searched.
        """
        try:
            self.__getitem__(keyname)
        except KeyError:
            return False
        return True

    def __iter__(self):
        """
        Iterate over the keys in the session data.
        """
        # try memcache first
        if hasattr(self, u"session"):
            vals = self._get()
            if vals is not None:
                for k in vals:
                    yield k.keyname
        for k in self.cookie_vals:
            yield k

    def __str__(self):
        """
        Return string representation.
        """
        return u"{%s}" % ', '.join(['"%s" = "%s"' % (k, self[k]) for k in self])

########NEW FILE########
__FILENAME__ = settings_default
"""
Copyright (c) 2008, appengine-utilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
- Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the appengine-utilities project nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

__author__="jbowman"
__date__ ="$Sep 11, 2009 4:20:11 PM$"


# Configuration settings for the session class.
session = {    
    "COOKIE_NAME": "gaeutilities_session",
    "DEFAULT_COOKIE_PATH": "/",
    "DEFAULT_COOKIE_DOMAIN": False, # Set to False if you do not want this value
                                    # set on the cookie, otherwise put the
                                    # domain value you wish used.
    "SESSION_EXPIRE_TIME": 7200,    # sessions are valid for 7200 seconds
                                    # (2 hours)
    "INTEGRATE_FLASH": True,        # integrate functionality from flash module?
    "SET_COOKIE_EXPIRES": True,     # Set to True to add expiration field to
                                    # cookie
    "WRITER":"datastore",           # Use the datastore writer by default. 
                                    # cookie is the other option.
    "CLEAN_CHECK_PERCENT": 50,      # By default, 50% of all requests will clean
                                    # the datastore of expired sessions
    "CHECK_IP": True,               # validate sessions by IP
    "CHECK_USER_AGENT": True,       # validate sessions by user agent
    "SESSION_TOKEN_TTL": 5,         # Number of seconds a session token is valid
                                    # for.
    "UPDATE_LAST_ACTIVITY": 60,     # Number of seconds that may pass before
                                    # last_activity is updated
}

# Configuration settings for the cache class
cache = {
    "DEFAULT_TIMEOUT": 3600, # cache expires after one hour (3600 sec)
    "CLEAN_CHECK_PERCENT": 50, # 50% of all requests will clean the database
    "MAX_HITS_TO_CLEAN": 20, # the maximum number of cache hits to clean
}

# Configuration settings for the flash class
flash = {
    "COOKIE_NAME": "appengine-utilities-flash",
}

# Configuration settings for the paginator class
paginator = {
    "DEFAULT_COUNT": 10,
    "CACHE": 10,
    "DEFAULT_SORT_ORDER": "ASC",
}

rotmodel = {
    "RETRY_ATTEMPTS": 3,
    "RETRY_INTERVAL": .2,
}
if __name__ == "__main__":
    print "Hello World";


########NEW FILE########
__FILENAME__ = main
'''
Copyright (c) 2008, appengine-utilities project
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
Neither the name of the appengine-utilities project nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

import os
import __main__
import time
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from appengine_utilities import sessions
from appengine_utilities import flash
from appengine_utilities import event
from appengine_utilities import cache
from appengine_utilities.rotmodel import ROTModel
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db
from django.utils import simplejson

class MainPage(webapp.RequestHandler):
  def __init__(self):
    self.test = "event not fired"

  def get(self):
    template_values = {}

    path = os.path.join(os.path.dirname(__file__), 'templates/index-new.html')
    self.response.out.write(template.render(path, template_values))

class FlashPage(webapp.RequestHandler):
  def get(self):
    self.flash = flash.Flash()
    if self.request.get('setflash') == "true":
        self.flash.msg = 'You set a flash message! <a href="/flash">Refresh this page</a> and this message is gone!'
        print "Location: /flash\n\n"
    else:
        template_values = {
            'flash': self.flash,
        }
        path = os.path.join(os.path.dirname(__file__), 'templates/flash-new.html')
        self.response.out.write(template.render(path, template_values))

class AjaxSessionPage(webapp.RequestHandler):
  def get(self):
    self.sess = sessions.Session()
    if not 'viewCount' in self.sess:
      self.sess['viewCount'] = 1
    else:
      self.sess['viewCount'] = int(self.sess['viewCount']) + 1
    self.response.out.write('viewcount is ' + str(self.sess['viewCount']))

class SessionTestModel(db.Model):
    testval = db.StringProperty()

class SessionPage(webapp.RequestHandler):
  def get(self):
    self.sess = sessions.Session()
    if not self.sess.has_key("model_test"):
        self.sess["model_test"] = SessionTestModel(testval="test")
        self.sess["model_test"].put()
        # give the datastore time to submit the commit
        time.sleep(1)
    self.cookie_sess = sessions.Session(writer="cookie")
    if self.request.get('deleteSession') == "true":
        self.sess.delete()
        print "Location: /session\n\n"
    elif self.request.get('setflash') == "true":
        self.sess['flash'] = 'You set a flash message! <a href="/session">Refresh this page</a> and this message is gone!'
        print "Location: /session\n\n"
    elif self.request.get('setTestKey') == "true":
        self.sess['DeletableKey'] = 'delete me'
        print "Location: /session\n\n"
    elif self.request.get('clearTestKey') == "true":
        self.sess.delete_item('DeletableKey')
        print "Location: /session\n\n"
    else:
        keyname = 'testKey'
        self.sess[keyname] = "test"
        self.sess[keyname + '2'] = "test2"
        self.sess[3] = "test3"
        self.cookie_sess['cookie_test'] = "testing cookie values"
        self.sess[u"unicode_key"] = u"unicode_value"

        if not 'viewCount' in self.sess:
            self.sess['viewCount'] = 1
        else:
            self.sess['viewCount'] = int(self.sess['viewCount']) + 1
        self.sess["model_test"].testval = unicode(self.sess['viewCount'])
        testkey = self.sess["model_test"].put()
        session_length = len(self.sess)
        self.memcacheStats = memcache.get_stats()
        template_values = {
            'sess': self.sess,
            'sess_str': str(self.sess),
            'cookie_sess': self.cookie_sess,
            'session_length': session_length,
            'memcacheStats': self.memcacheStats,
            'model_test': self.sess["model_test"].testval,
            'testkey': testkey,
        }
        path = os.path.join(os.path.dirname(__file__), 'templates/session-new.html')
        self.response.out.write(template.render(path, template_values))

class CookieSessionPage(webapp.RequestHandler):
  def get(self):
    self.sess = sessions.Session(writer="cookie")
    if self.request.get('deleteSession') == "true":
        self.sess.delete()
        print "Location: /cookiesession\n\n"
    elif self.request.get('setflash') == "true":
        self.sess['flash'] = 'You set a flash message! <a href="/cookiesession">Refresh this page</a> and this message is gone!'
        print "Location: /cookiesession\n\n"
    else:
        keyname = 'testKey'
        self.sess[keyname] = "test"
        self.sess[keyname + '2'] = "test2"
        self.sess[3] = "test3"
        if not 'viewCount' in self.sess:
            self.sess['viewCount'] = 1
        else:
            self.sess['viewCount'] = int(self.sess['viewCount']) + 1
        self.sess[u"unicode_key"] = u"unicode_value"
        session_length = len(self.sess)
        self.memcacheStats = memcache.get_stats()
        template_values = {
            'sess': self.sess,
            'sess_str': str(self.sess),
            'session_length': session_length,
            'memcacheStats': self.memcacheStats
        }
        path = os.path.join(os.path.dirname(__file__), 'templates/cookie_session-new.html')
        self.response.out.write(template.render(path, template_values))


class EventPage(webapp.RequestHandler):
  def __init__(self):
        self.msg = ""
        self.triggermsg = "I have not been triggered"

  def get(self):
    if self.request.get('trigger') == "true":
        AEU_Events.subscribe("myTriggeredEventFired", self.myTriggeredCallback, {"msg": "Triggered!"})
    AEU_Events.subscribe("myEventFired", self.myCallback, {"msg": "This message was set in myCallback."})
    AEU_Events.fire_event("myEventFired")
    AEU_Events.fire_event("myTriggeredEventFired")
    template_values = {
        'msg': self.msg,
        'triggermsg': self.triggermsg,
    }
    AEU_Events.subscribe("myEventFired", self.myCallback, {"msg": "You will never see this message because the event to set it is fired after the template_values have already been set."})
    AEU_Events.fire_event("myEventFired")
    path = os.path.join(os.path.dirname(__file__), 'templates/event-new.html')
    self.response.out.write(template.render(path, template_values))

  def myCallback(self, msg):
    self.msg = msg

  def myTriggeredCallback(self, msg):
    self.triggermsg = msg

class CachePage(webapp.RequestHandler):
  def get(self):
    self.cache = cache.Cache()
    # test deleting a cache object
    del self.cache["sampleStr"]
    # set a string
    if not "sampleStr" in self.cache:
        self.cache["sampleStr"] = "This is a string passed to the cache"
    # store an object
    if not "sampleObj" in self.cache:
        self.cache["sampleObj"] = ["this was set up as a list to test object caching"]
    keyname = 'dynamic' + 'key'
    if not keyname in self.cache:
        self.cache[keyname] = 'this is a dynamically created keyname'
    self.memcacheStats = memcache.get_stats()
    template_values = {
        'cacheItemStr': self.cache["sampleStr"],
        'cacheItemObj': self.cache["sampleObj"],
        'dynamickey': self.cache["dynamickey"],
        'memcacheStats': self.memcacheStats,
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/cache-new.html')
    self.response.out.write(template.render(path, template_values))


class TestROTModel(ROTModel):
    testval = db.IntegerProperty()

class ROTModelPage(webapp.RequestHandler):
  def get(self):
      template_values = {}

      # create a model test
      model1 = TestROTModel(key_name="testmodel1", testval=1)
      if model1:
          template_values["modelcreate"] = "OK"
      else:
          template_values["modelcreate"] = "ERROR"

      # is_saved test 1
      if model1.is_saved() is False:
          template_values["savedtest1"] = "OK"
      else:
          template_values["savedtest1"] = "ERROR"

      # model put test
      model_key = model1.put()
      if model_key:
          template_values["puttest"] = "OK"
      else:
          template_values["puttest"] = "ERROR"

      # is_saved test 2
      if model1.is_saved() == True:
          template_values["savedtest2"] = "OK"
      else:
          template_values["savedtest2"] = "ERROR"

      # get test single
      singletest = TestROTModel.get(model_key)
      if singletest:
          template_values["singleget"] = "OK"
      else:
          template_values["singleget"] = "ERROR"

      # get_or_insert test
      model2 = TestROTModel.get_or_insert("testmodel2", parent=model1, testval=2)
      if model2:
          template_values["get_or_insert"] = "OK"
          model2_key = model2.put()
      else:
          template_values["get_or_insert"] = "ERROR"

      # get test multi
      multitest = TestROTModel.get([model_key, model2_key])
      if len(multitest) > 1:
          template_values["multiget"] = "OK"
      else:
          template_values["multiget"] = "ERROR"

      # key test
      model2_key = model2.key()
      if model2_key:
          template_values["keytest"] = "OK"
      else:
          template_values["keytest"] = "ERROR"

      # set strings for key names
      model_keyname = "testmodel1"
      model2_keyname = "testmodel2"

      # get_by_key_name single
      singlekeyname = TestROTModel.get_by_key_name(model_keyname)
      if singlekeyname:
          template_values["getbykeynamesingle"] = "OK"
      else:
          template_values["getbykeynamesingle"] = "ERROR"

      # get_by_key_name multi
      multikeyname = TestROTModel.get_by_key_name([model_keyname, model2_keyname])
      if multikeyname:
          template_values["getbykeynamemulti"] = "OK"
      else:
          template_values["getbykeynamemulti"] = "ERROR"

      # all test
      alltest = TestROTModel.all()
      results = alltest.fetch(20)
      if len(results) > 0:
          template_values["alltest"] = "OK"
      else:
          template_values["alltest"] = "ERROR"

      # gql test
      gqltest = TestROTModel.gql("WHERE testval = :1", 1)
      results = gqltest.fetch(20)
      if len(results) > 0:
          template_values["gqltest"] = "OK"
      else:
          template_values["gqltest"] = "ERROR"

      # parent test
      parenttest = model2.parent()
      if parenttest:
          template_values["parenttest"] = "OK"
      else:
          template_values["parenttest"] = "ERROR"

      # parent_key test
      parentkeytest = model2.parent_key()
      if parentkeytest == model_key:
          template_values["parentkeytest"] = "OK"
      else:
          template_values["parentkeytest"] = "ERROR"

      # delete test
      model1.delete()
      model2.delete()

      if TestROTModel.get(model_key) == None:
          template_values["deletetest"] = "OK"
      else:
          template_values["deletetest"] = "ERROR"


      path = os.path.join(os.path.dirname(__file__), 'templates/rotmodel-new.html')
      self.response.out.write(template.render(path, template_values))


class PageTestModel(db.Model):
    testval = db.IntegerProperty()

class PaginatorPage(webapp.RequestHandler):
  def get(self):
        template_values = {}

        query = PageTestModel.all()
        results = query.fetch(20)
        if len(results) < 20:
            for i in range(0, 20):
                model = PageTestModel(testval=i)
                model.put()
            time.sleep(1)

        
        page1 = Paginator.get(model=PageTestModel, count=10)
        page2 = Paginator.get(model=PageTestModel, count=10, start=page1["next"])

        template_values["page1"] = page1
        template_values["page2"] = page2
        template_values["page_1_results"] = page1["results"]
        template_values["page_1_previous"] = page1["previous"]
        template_values["page_1_next"] = page1["next"]
        template_values["page_2_results"] = page2["results"]
        template_values["page_2_previous"] = page2["previous"]
        template_values["page_2_next"] = page2["next"]

        path = os.path.join(os.path.dirname(__file__), 'templates/paginator.html')
        self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication(
                                       [('/', MainPage),
                                       ('/session', SessionPage),
                                       ('/cookiesession', CookieSessionPage),
                                       ('/ajaxsession', AjaxSessionPage),
                                       ('/flash', FlashPage),
                                       ('/event', EventPage),
                                       ('/cache', CachePage),
                                       ('/paginator', PaginatorPage),
                                       ('/rotmodel', ROTModelPage)],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()

########NEW FILE########
