__FILENAME__ = manager
#!/usr/bin/env python
#coding=utf-8

import tornado.httpserver
import tornado.ioloop
import tornado.options

from tornado.options import define, options 

from redisadmin import Application

define("port", default=9000, help="default: 9000, required runserver", type=int)

def main():
    tornado.options.parse_command_line()

    print 'server started. port %s' % options.port
    http_server = tornado.httpserver.HTTPServer(Application(), xheaders=True)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__=='__main__':
    main()

########NEW FILE########
__FILENAME__ = cache
#!/usr/bin/env python
#coding=utf-8
"""
    extensions.cache

    Example:
    >>> from extensions.cache import SimpleCache
    >>> c = SimpleCahce()
    >>> c.set('a', 'xx')
    >>> c.get('a')
    'xx'
    >>> c.get('b') is None
    True
"""
import hashlib
from time import time
from itertools import izip
from functools import wraps
try:
    import cPickle as pickle
except ImportError:
    import pickle


class BaseCache(object):
    def __init__(self, timeout=300):
        self.timeout = timeout
    
    def get(self, key):
        return None
    
    def get_many(self, *keys):
        return map(self.get, keys)
    
    def get_dict(self, *keys):
        return dict(izip(keys, self.get_many(*keys)))
    
    def set(self, key, value, timeout=None):
        pass
    
    def delete(self, key):
        pass

    def clear(self):
        pass

    def mark_key(self, function, args, kwargs):
        try:
            key = pickle.dumps((function.func_name, args, kwargs))
        except:
            key = pickle.dumps(function.func_name)
        return hashlib.sha1(key).hexdigest()

    def cached(self, timeout=None, unless=None):
        """
        Example:
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if callable(unless) and unless() is True:
                    return f(*args, **kwargs)
    
                key = self.mark_key(f, args, kwargs)
    
                rv = self.get(key)
    
                if rv is None:
                    rv = f(*args, **kwargs)
                    self.set(key, rv, timeout=timeout)
    
                return rv
            return decorated_function
        return decorator


class SimpleCache(BaseCache):
    def __init__(self, threshold=500, timeout=300):
        BaseCache.__init__(self, timeout)
        self._cache = {}
        self._threshold = threshold
    
    def _prune(self):
        if len(self._cache) >= self._threshold:
            num = len(self._cache) - self._threshold + 1
            for key, value in sorted(self._cache.items(), key=lambda x:x[1][0])[:num]:
                self._cache.pop(key, None)
    
    def get(self, key):
        expires, value = self._cache.get(key, (0, None))
        if expires > time():
            return pickle.loads(value)
        
    def set(self, key, value, timeout=None):
        if timeout is None:
            timeout = self.timeout
        self._prune()
        self._cache[key] = (time() + timeout, pickle.dumps(value, 
            pickle.HIGHEST_PROTOCOL))
    
    def delete(self, key):
        self._cache.pop(key, None)

    def clear(self):
        for key, (expires, _) in self._cache.iteritems():
            if expires < time():
                self._cache.pop(key, None)


cache = SimpleCache()

class cached_property(object):
    def __init__(self, func, name=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, None)
        if value is None:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
#coding=utf-8
"""
    forms.py
    ~~~~~~~~~~~~~
    wtforms extensions for tornado
"""
import re

from tornado.escape import _unicode

from wtforms import Form as BaseForm, fields, validators, widgets, ext

from wtforms.fields import BooleanField, DecimalField, DateField, \
    DateTimeField, FieldList, FloatField, FormField, \
    HiddenField, IntegerField, PasswordField, RadioField, SelectField, \
    SelectMultipleField, SubmitField, TextField, TextAreaField

from wtforms.validators import ValidationError, Email, email, EqualTo, equal_to, \
    IPAddress, ip_address, Length, length, NumberRange, number_range, \
    Optional, optional, Required, required, Regexp, regexp, \
    URL, url, AnyOf, any_of, NoneOf, none_of

from wtforms.widgets import CheckboxInput, FileInput, HiddenInput, \
    ListWidget, PasswordInput, RadioInput, Select, SubmitInput, \
    TableWidget, TextArea, TextInput

try:
    import sqlalchemy
    _is_sqlalchemy = True
except ImportError:
    _is_sqlalchemy = False


if _is_sqlalchemy:
    from wtforms.ext.sqlalchemy.fields import QuerySelectField, \
        QuerySelectMultipleField

    for field in (QuerySelectField, 
                  QuerySelectMultipleField):

        setattr(fields, field.__name__, field)


class Form(BaseForm):
    """
    Example:
    >>> user = User.query.get(1)
    >>> form = LoginForm(user)
    {{ xsrf_form_html }}
    {{ form.hiden_tag() }}
    {{ form.username }}
    """

    def __init__(self, formdata=None, *args, **kwargs):
        self.obj = kwargs.get('obj', None)
        super(Form, self).__init__(formdata, *args, **kwargs)
    
    def process(self, formdata=None, *args, **kwargs):
        if formdata is not None and not hasattr(formdata, 'getlist'):
            formdata = TornadoInputWrapper(formdata)
        super(Form, self).process(formdata, *args, **kwargs)
    
    def hidden_tag(self, *fields):
        """
        Wraps hidden fields in a hidden DIV tag, in order to keep XHTML 
        compliance.
        """

        if not fields:
            fields = [f for f in self if isinstance(f, HiddenField)]

        rv = []
        for field in fields:
            if isinstance(field, basestring):
                field = getattr(self, field)
            rv.append(unicode(field))

        return u"".join(rv)
    
    
class TornadoInputWrapper(dict):
    """
    From tornado source-> RequestHandler.get_arguments
    """
    def getlist(self, name, strip=True):
        values = []
        for v in self.get(name, []):
            v = _unicode(v)
            if isinstance(v, unicode):
                # Get rid of any weird control chars (unless decoding gave
                # us bytes, in which case leave it alone)
                v = re.sub(r"[\x00-\x08\x0e-\x1f]", " ", v)
            if strip:
                v = v.strip()
            values.append(v)
        return values

########NEW FILE########
__FILENAME__ = permission
#!/usr/bin/env python
#coding=utf-8
"""
    extensions: permission.py
    permission for tornado. from flask-principal.
    :modified by laoqiu.com@gmail.com

    Example:
    >>> from extensions.permission import UserNeed, RoleNeed, ItemNeed, Permission
    >>> admin = Permission(RoleNeed('admin'))
    >>> editor = Permission(UserNeed(1)) & admin

    # handers
    ~~~~~~~~~

    @admin.require(401)
    def get(self):
        self.write('is admin')
        return
     
    def post(self):
        # or
        if editor.can(self.identity):
            print 'admin'
        # or
        editor.test(self.identity, 401)
        return

"""
import sys
import tornado.web

from functools import wraps, partial
from collections import namedtuple

__all__ = ['UserNeed', 'RoleNeed', 'ItemNeed', 'Permission', 'Identity', 'AnonymousIdentity']

Need = namedtuple('Need', ['method', 'value'])

UserNeed = partial(Need, 'user')
RoleNeed = partial(Need, 'role')
ItemNeed = namedtuple('ItemNeed', ['method', 'value', 'type'])


class PermissionDenied(RuntimeError):
    """Permission denied to the resource"""
    pass


class Identity(object):
    """
    A set of needs provided by this user
    
    example:
        identity = Identity('ali')
        identity.provides.add(('role', 'admin'))
    """
    def __init__(self, name):
        self.name = name
        self.provides = set()

    def can(self, permission):
        return permission.allows(self)


class AnonymousIdentity(Identity):
    """An anonymous identity
    :attr name: "anonymous"
    """
    def __init__(self):
        Identity.__init__(self, 'anonymous')


class IdentityContext(object):
    """The context of an identity for a permission.

    .. note:: The principal is usually created by the flaskext.Permission.require method
              call for normal use-cases.

    The principal behaves as either a context manager or a decorator. The
    permission is checked for provision in the identity, and if available the
    flow is continued (context manager) or the function is executed (decorator).
    """

    def __init__(self, permission, http_exception=None, identity=None):
        self.permission = permission
        self.http_exception = http_exception
        self.identity = identity if identity else AnonymousIdentity()

    def can(self):
        """Whether the identity has access to the permission
        """
        return self.identity.can(self.permission)

    def __call__(self, method):
        @wraps(method)
        def wrapper(handler, *args, **kwargs):
            self.identity = handler.identity
            self.__enter__()
            exc = (None, None, None)
            try:
                result = method(handler, *args, **kwargs)
            except Exception:
                exc = sys.exc_info()
            self.__exit__(*exc)
            return result
        return wrapper
    
    def __enter__(self):
        # check the permission here
        if not self.can():
            if self.http_exception:
                raise tornado.web.HTTPError(self.http_exception)
            raise PermissionDenied(self.permission)

    def __exit__(self, *exc):
        if exc != (None, None, None):
            cls, val, tb = exc
            raise cls, val, tb
        return False


class Permission(object):
    """
    Represents needs, any of which must be present to access a resource
    :param needs: The needs for this permission
    """
    def __init__(self, *needs):
        self.needs = set(needs)
        self.excludes = set()

    def __and__(self, other):
        """Does the same thing as "self.union(other)"
        """
        return self.union(other)
    
    def __or__(self, other):
        """Does the same thing as "self.difference(other)"
        """
        return self.difference(other)

    def __contains__(self, other):
        """Does the same thing as "other.issubset(self)".
        """
        return other.issubset(self)
    
    def require(self, http_exception=None, identity=None):
        return IdentityContext(self, http_exception, identity)
        
    def test(self, identity, http_exception=None):
        with self.require(http_exception, identity):
            pass
        
    def reverse(self):
        """
        Returns reverse of current state (needs->excludes, excludes->needs) 
        """

        p = Permission()
        p.needs.update(self.excludes)
        p.excludes.update(self.needs)
        return p

    def union(self, other):
        """Create a new permission with the requirements of the union of this
        and other.

        :param other: The other permission
        """
        p = Permission(*self.needs.union(other.needs))
        p.excludes.update(self.excludes.union(other.excludes))
        return p

    def difference(self, other):
        """Create a new permission consisting of requirements in this 
        permission and not in the other.
        """

        p = Permission(*self.needs.difference(other.needs))
        p.excludes.update(self.excludes.difference(other.excludes))
        return p

    def issubset(self, other):
        """Whether this permission needs are a subset of another

        :param other: The other permission
        """
        return self.needs.issubset(other.needs) and \
               self.excludes.issubset(other.excludes)

    def allows(self, identity):
        """Whether the identity can access this permission.

        :param identity: The identity
        """
        if self.needs and not self.needs.intersection(identity.provides):
            return False

        if self.excludes and self.excludes.intersection(identity.provides):
            return False

        return True
    
    def can(self, identity):
        """Whether the required context for this permission has access

        This creates an identity context and tests whether it can access this
        permission
        """
        return self.require(identity=identity).can()

########NEW FILE########
__FILENAME__ = routing
#!/usr/bin/env python
#coding=utf-8
"""
    extensions.route

    Example:
    @route(r'/', name='index')
    class IndexHandler(tornado.web.RequestHandler):
        pass
    
    class Application(tornado.web.Application):
        def __init__(self):
            handlers = [
                # ...
            ] + Route.routes()
"""

from tornado.web import url

class Route(object):

    _routes = {}

    def __init__(self, pattern, kwargs={}, name=None, host='.*$'):
        self.pattern = pattern
        self.kwargs = {}
        self.name = name
        self.host = host

    def __call__(self, handler_class):
        spec = url(self.pattern, handler_class, self.kwargs, name=self.name)
        self._routes.setdefault(self.host, []).append(spec)
        return handler_class
    
    @classmethod
    def routes(cls, application=None):
        if application:
            for host, handlers in cls._routes.items():
                application.add_handlers(host, handlers)
        else:
            return reduce(lambda x,y:x+y, cls._routes.values()) if cls._routes else []

    @classmethod
    def url_for(cls, name, *args):
        named_handlers = dict([(spec.name, spec) for spec in cls.routes() if spec.name])
        if name in named_handlers:
            return named_handlers[name].reverse(*args)
        raise KeyError("%s not found in named urls" % name)


route = Route

########NEW FILE########
__FILENAME__ = sessions
#!/usr/bin/env python
#coding=utf-8
"""
    extensions.session
    ~~~~~~~~
    :origin version in https://gist.github.com/1735032
"""
try:
    import cPickle as pickle
except ImportError:
    import pickle
import time
import logging
from uuid import uuid4


class Session(object):
    def __init__(self, get_secure_cookie, set_secure_cookie, name='_session', expires_days=None):
        self.set_session = set_secure_cookie
        self.get_session = get_secure_cookie
        self.name = name
        self._expiry = expires_days
        self._dirty = False
        self.get_data()
    
    def get_data(self):
        value = self.get_session(self.name)
        self._data = pickle.loads(value) if value else {}

    def set_expires(self, days):
        self._expiry = days

    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
        self._dirty = True
    
    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]
            self._dirty = True
        
    def __contains__(self, key):
        return key in self._data
    
    def __len__(self):
        return len(self._data)
    
    def __iter__(self):
        for key in self._data:
            yield key
    
    def __del__(self):
        self.save()

    def save(self):
        if self._dirty:
            self.set_session(self.name, pickle.dumps(self._data), expires_days=self._expiry)
            self._dirty = False


class RedisSessionStore(object):
    def __init__(self, redis_connection, **options):
        self.options = {
            'key_prefix': 'session',
            'expire': 7200,
        }
        self.options.update(options)
        self.redis = redis_connection

    def prefixed(self, sid):
        return '%s:%s' % (self.options['key_prefix'], sid)

    def generate_sid(self):
        return uuid4().get_hex()

    def get_session(self, sid, name):
        data = self.redis.hget(self.prefixed(sid), name)
        session = pickle.loads(data) if data else dict()
        return session

    def set_session(self, sid, session_data, name, expiry=None):
        self.redis.hset(self.prefixed(sid), name, pickle.dumps(session_data))
        expiry = expiry or self.options['expire']
        if expiry:
            self.redis.expire(self.prefixed(sid), expiry)

    def delete_session(self, sid):
        self.redis.delete(self.prefixed(sid))


class RedisSession(object):
    def __init__(self, session_store, session_id=None, expires_days=None):
        self._store = session_store
        self._sid = session_id if session_id else self._store.generate_sid()
        self._dirty = False
        self.set_expires(expires_days)
        try:
            self._data = self._store.get_session(self._sid, 'data')
        except:
            logging.error('Can not connect Redis server.')
            self._data = {}

    def clear(self):
        self._store.delete_session(self._sid)

    @property
    def id(self):
        return self._sid
    
    def access(self, remote_ip):
        access_info = {'remote_ip':remote_ip, 'time':'%.6f' % time.time()}
        self._store.set_session(
                self._sid,
                'last_access',
                pickle.dumps(access_info))

    def last_access(self):
        access_info = self._store.get_session(self._sid, 'last_access')
        return pickle.loads(access_info)

    def set_expires(self, days):
        self._expiry = days * 86400 if days else None

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self._dirty = True

    def __delitem__(self, key):
        del self._data[key]
        self._dirty = True

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        for key in self._data:
            yield key

    def __repr__(self):
        return self._data.__repr__()

    def __del__(self):
        self.save()

    def save(self):
        if self._dirty:
            self._store.set_session(self._sid, self._data, 'data', self._expiry)
            self._dirty = False


########NEW FILE########
__FILENAME__ = filters
#!/usr/bin/env python
#coding=utf-8

import tornado.template


def field_errors(field):
    t = tornado.template.Template("""
        {% if field.errors %}
        <ul class="errors">
            {% for error in field.errors %}
            <li>{{ error }}</li>
            {% end %}
        </ul>
        {% end %}
        """)
    return t.generate(field=field)



########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
#coding=utf-8
import tornado.locale

from redisadmin.extensions.forms import Form, TextField, PasswordField, SubmitField, \
        HiddenField, required


def create_forms():
    
    _forms = {}
    
    for locale in tornado.locale.get_supported_locales(None):

        _ = tornado.locale.get(locale).translate
    
        class FormWrapper(object):

            class LoginForm(Form):
                username = TextField(_("Username"), validators=[
                                  required(message=\
                                           _("You must provide an username"))])

                password = PasswordField(_("Password"))

                next = HiddenField()

                submit = SubmitField(_("Login"))

            
        _forms[locale] = FormWrapper

    return _forms


########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/env python
#coding=utf-8
"""
    helpers.py
    ~~~~~~~~~~~~~
    :author: laoqiu.com@gmail.com
"""

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    >>> o = storage(a=1)
    >>> o.a
    1
    >>> o['a']
    1
    >>> o.a = 2
    >>> o['a']
    2
    >>> del o.a
    >>> o.a
    Traceback (most recent call last):
    ...
    AttributeError: 'a'
    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __setattr__(self, key, value):
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'


def setting_from_object(obj):
    settings = dict()
    for key in dir(obj):
        if key.isupper():
            settings[key.lower()] = getattr(obj, key)
    return settings


class Pagination(object):
    def __init__(self, query, page, per_page):
        self.query = query
        self.per_page = per_page
        self.page = page

    @property
    def total(self):
        return len(self.query)
    
    @property
    def items(self):
        return self.query[(self.page - 1) * self.per_page : self.page * self.per_page]

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num
        
    has_prev = property(lambda x: x.page > 1)
    prev_num = property(lambda x: x.page - 1)
    has_next = property(lambda x: x.page < x.pages)
    next_num = property(lambda x: x.page + 1)
    pages = property(lambda x: max(0, x.total - 1) // x.per_page + 1)


storage = Storage



########NEW FILE########
__FILENAME__ = permissions
#! /usr/bin/env python
#coding=utf-8
"""
    permissions.py
    ~~~~~~~~~~~
    set role need permissions
    :author: laoqiu.com@gmail.com
"""

from extensions.permission import RoleNeed, Permission

admin = Permission(RoleNeed('admin'))
moderator = Permission(RoleNeed('moderator'))
auth = Permission(RoleNeed('authenticated'))


########NEW FILE########
__FILENAME__ = settings
#!/usr/bin/env python
#coding=utf-8
import os

DEBUG = True
COOKIE_SECRET = 'simple'
LOGIN_URL = '/login'
XSRF_COOKIES = True

USERNAME = 'admin'
PASSWORD = '111'

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates')
STATIC_PATH = os.path.join(os.path.dirname(__file__), 'static')

DEFAULT_LOCALE = 'en_US' #'zh_CN'

REDIS_SERVER = True
REDIS_DB = 16

# If set to None or 0 the session will be deleted when the user closes the browser.
# If set number the session lives for value days.
PERMANENT_SESSION_LIFETIME = 1 # days

PER_PAGE = 100

try:
    from local_settings import *
except:
    pass



########NEW FILE########
__FILENAME__ = uimodules
#!/usr/bin/env python
#coding=utf-8

import tornado.web

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
#coding=utf-8
"""
    views: base.py
    ~~~~~~~~~~~
    :author: laoqiu.com@gmail.com
"""
import os

import logging
import tornado.web
import tornado.locale
import tornado.escape
import tornado.ioloop

from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import HtmlFormatter

from redisadmin.extensions.permission import Identity, AnonymousIdentity
from redisadmin.extensions.cache import cache
from redisadmin.extensions.sessions import RedisSession, Session


class FlashMessageMixIn(object):
    """
        Store a message between requests which the user needs to see.

        views
        -------

        self.flash("Welcome back, %s" % username, 'success')

        base.html
        ------------
        
        {% set messages = handler.get_flashed_messages() %}
        {% if messages %}
        <div id="flashed">
            {% for category, msg in messages %}
            <span class="flash-{{ category }}">{{ msg }}</span>
            {% end %}
        </div>
        {% end %}
    """
    def flash(self, message, category='message'):
        messages = self.messages()
        messages.append((category, message))
        self.set_secure_cookie('flash_messages', tornado.escape.json_encode(messages))
    
    def messages(self):
        messages = self.get_secure_cookie('flash_messages')
        messages = tornado.escape.json_decode(messages) if messages else []
        return messages
        
    def get_flashed_messages(self):
        messages = self.messages()
        self.clear_cookie('flash_messages')
        return messages
    

class PermissionMixIn(object):
    @property
    def identity(self):
        if not hasattr(self, "_identity"):
            self._identity = self.get_identity()
        return self._identity

    def get_identity(self):
        if self.current_user:
            identity = Identity(self.current_user.id)
            identity.provides.update(self.current_user.provides)
            return identity
        return AnonymousIdentity()


class CachedItemsMixIn(object):
    def get_cached_items(self, name):
        items = cache.get(name)
        if items is None:
            items = self.set_cached_items(name)
        return items

    def set_cached_items(self, name, limit=10):
        items = []
        if name == 'latest_comments':
            items = [comment.item for comment in Comment.query.order_by(Comment.created_date.desc()).limit(limit)]
        elif name == 'tags':
            items = Tag.query.cloud()
        elif name == 'links':
            items = [link.item for link in Link.query.filter(Link.passed==True).limit(limit)]
        cache.set(name, items)
        return items


class RequestHandler(tornado.web.RequestHandler, PermissionMixIn, FlashMessageMixIn, CachedItemsMixIn):
    def initialize(self):
        db = self.session['db'] if 'db' in self.session else 0
        self.redis = self.application.redis[db]
    
    def get_current_user(self):
        user = self.session['user'] if 'user' in self.session else None
        return user
    
    @property
    def session(self):
        if hasattr(self, '_session'):
            return self._session
        else:
            self.require_setting('permanent_session_lifetime', 'session')
            expires = self.settings['permanent_session_lifetime'] or None
            if 'redis_server' in self.settings and self.settings['redis_server']:
                sessionid = self.get_secure_cookie('sid')
                self._session = RedisSession(self.application.session_store, sessionid, expires_days=expires)
                if not sessionid: 
                    self.set_secure_cookie('sid', self._session.id, expires_days=expires)
            else:
                self._session = Session(self.get_secure_cookie, self.set_secure_cookie, expires_days=expires)
            return self._session
    
    def get_user_locale(self):
        code = self.get_cookie('lang', self.settings.get('default_locale', 'zh_CN'))
        return tornado.locale.get(code)
    
    def get_error_html(self, status_code, **kwargs):
        if self.settings.get('debug', False) is False:
            self.set_status(status_code)
            return self.render_string('errors/%s.html' % status_code)

        else:
            def get_snippet(fp, target_line, num_lines):
                if fp.endswith('.html'):
                    fp = os.path.join(self.get_template_path(), fp)

                half_lines = (num_lines/2)
                try:
                    with open(fp) as f:
                        all_lines = [line for line in f]
                        code = ''.join(all_lines[target_line-half_lines-1:target_line+half_lines])
                        formatter = HtmlFormatter(linenos=True, linenostart=target_line-half_lines, hl_lines=[half_lines+1])
                        lexer = get_lexer_for_filename(fp) 
                        return highlight(code, lexer, formatter)
                
                except Exception, ex:
                    logging.error(ex)
                    return ''

            css = HtmlFormatter().get_style_defs('.highlight')
            exception = kwargs.get('exception', None)
            return self.render_string('errors/exception.htm', 
                                      get_snippet=get_snippet,
                                      css=css,
                                      exception=exception,
                                      status_code=status_code, 
                                      kwargs=kwargs)
    
    def get_args(self, key, default=None, type=None):
        if type==list:
            if default is None: default = []
            return self.get_arguments(key, default)
        value = self.get_argument(key, default)
        if value and type:
            try:
                value = type(value)
            except ValueError:
                value = default
        return value
    
    @property
    def is_xhr(self):
        '''True if the request was triggered via a JavaScript XMLHttpRequest.
        This only works with libraries that support the `X-Requested-With`
        header and set it to "XMLHttpRequest".  Libraries that do that are
        prototype, jQuery and Mochikit and probably some more.'''
        return self.request.headers.get('X-Requested-With', '') \
                           .lower() == 'xmlhttprequest'
    
    @property
    def forms(self):
        return self.application.forms[self.locale.code]

    def _(self, message, plural_message=None, count=None):
        return self.locale.translate(message, plural_message, count)

 
class ErrorHandler(RequestHandler):
    """raise 404 error if url is not found.
    fixed tornado.web.RequestHandler HTTPError bug.
    """
    def prepare(self):
        self.set_status(404)
        raise tornado.web.HTTPError(404)



########NEW FILE########
__FILENAME__ = frontend
#!/usr/bin/env python
#coding=utf-8
"""
    views: frontend.py
    ~~~~~~~~~~~
    :author: laoqiu.com@gmail.com
"""
# import redis
import logging
import json
import tornado.web

from redisadmin.views import RequestHandler
from redisadmin.helpers import Pagination
from redisadmin.extensions.routing import route


@route("/", name='index')
class Index(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        self.render('index.html')
        return 


@route("/connection", name='connection')
class Connection(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        db  = self.get_args('db', 0, type=int)

        self.session['db'] = db
        self.session.save()

        self.write(dict(success=True))
        return


@route("/menu", name='menu')
class Menu(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        q = self.get_args('q','*')
        
        fullkeys = self.redis.keys(q)

        def get_item(key, root):
            id = '%s:%s' % (root, key) if root else key
            children = get_children(id)
            item = {"text": '%s(%s)' % (id, len(children)) if children else id,
                    "id": id,
                    "children": sorted(children)[:200]
                    }
            return item

        def get_children(root=None):
            if root:
                keys = set(sorted([key[len(root)+1:].split(':')[0] for key in fullkeys if key[:len(root)+1]=='%s:' % root]))
            else:
                keys = set(sorted([key.split(':')[0] for key in fullkeys]))

            return [get_item(key, root) for key in keys]
        

        children = get_children()
        while len(children)==1 and children[0]['children']:
            children = children[0]['children']

        menu = [{"text": '%s(%s)' % (q, len(children)), "id": q, "children": children}]
        
        self.write(json.dumps(menu))
        return 


@route("/new", name='new')
class New(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        key = self.get_args('key')
        _type = self.get_args('type')
        value = self.get_args('value')

        if key and value and _type in ['string', 'hash', 'list', 'set', 'zset']:

            if self.redis.exists(key):
                self.write(dict(success=False, error=u"Key is exists!"))
                return

            if _type=='string':
                self.redis.set(key, value)

            elif _type=='hash':
                try:
                    value = json.loads(value)
                except:
                    self.error()
                    return
                else:
                    if isinstance(value, dict):
                        for field,v in value.items():
                            self.redis.hset(key, field, str(v))
                    else:
                        self.error()
                        return

            elif _type=='list':
                try:
                    value = json.loads(value)
                except:
                    self.error()
                    return
                else:
                    if isinstance(value, list):
                        for v in value:
                            self.redis.rpush(str(v))
                    else:
                        self.error()
                        return

            elif _type=='set':
                try:
                    value = json.loads(value)
                except:
                    self.error()
                    return
                else:
                    if isinstance(value, list):
                        for v in value:
                            self.redis.sadd(str(v))
                    else:
                        self.error()
                        return

            elif _type=='zset':
                score = self.get_args('score')
                if score: 
                    self.redis.zadd(key, score, value)
                else:
                    self.error()
                    return

            self.write(dict(success=True))
            return

        self.error()
        return
        
    def error(self):
        self.write(dict(success=False, error="New key create failed, check form and value is valid."))
        return


@route("/value", name='value')
class Value(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        key = self.get_args('key','')
        if key:
            _type = self.redis.type(key)
            if _type=='string':
                value = self.get_strings(key)
            elif _type=='list':
                value = self.get_lists(key)
            elif _type=='hash':
                value = self.get_hashes(key)
            elif _type=='set':
                value = self.get_sets(key)
            elif _type=='zset':
                value = self.get_sortedsets(key)
            else:
                _type = value = None
            
            self.write(dict(type=_type,key=key,value=value))
            return

        self.write(dict(type=None,key=key,value=None))
        return
    
    def get_strings(self, key):
        return self.redis.get(key)
    
    def get_hashes(self, key):
        return self.redis.hgetall(key)

    def get_lists(self, key):
        return self.redis.lrange(key, 0, -1)
    
    def get_sets(self, key):
        return list(self.redis.smembers(key))
    
    def get_sortedsets(self, key):
        return list(self.redis.zrange(key, 0, -1))


@route("/list", name='list')
class List(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        root = self.get_args('root','')
        if root:
            
            while (root and root[-1] in [':','*']):
                root = root[:-1]

            page = self.get_args('page', 1, type=int)
            if page < 1: page = 1

            per_page = self.settings['per_page']

            fullkeys = sorted(self.redis.keys(root+':*'))

            data = [(key, self.redis.hgetall(key) if self.redis.type(key)=='hash' else {}) \
                        for key in fullkeys if key.split(root)[-1].count(':')==1]

            page_obj = Pagination(data, page, per_page=per_page)
            
            iter_pages = [p for p in page_obj.iter_pages()]
            
            self.write(dict(data=page_obj.items, root=root, page=page, iter_pages=iter_pages))
            return

        self.write(dict(data=[]))
        return


@route("/info", name="info")
class Info(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        info = self.redis.info()
        self.write(json.dumps(info.items()))
        return 


@route("/flush/db", name="flush_db")
class FlushDB(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        result = self.redis.flushdb()
        self.write(dict(success=result))
        return 


@route("/flush/all", name="flush_all")
class FlushDB(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        result = self.redis.flushall()
        self.write(dict(success=result))
        return 


@route("/expire", name="expire")
class Expire(RequestHandler):
    @tornado.web.authenticated
    def get(self):

        key = self.get_args('key', '')
        seconds = self.get_args('seconds', 0, type=int)

        if key:

            result = self.redis.expire(key, seconds)

            self.write(dict(success=result))
            return 

        self.write(dict(success=False))
        return 


@route("/move", name="move")
class Move(RequestHandler):
    @tornado.web.authenticated
    def get(self):

        key = self.get_args('key', '')
        db = self.get_args('db', -1, type=int)

        if key and db>=0:
            try:
                result = self.redis.move(key, db)
            except:
                result = False

            self.write(dict(success=result))
            return 

        self.write(dict(success=False))
        return 


@route("/edit", name="edit")
class Edit(RequestHandler):
    @tornado.web.authenticated
    def get(self):
    
        key = self.get_args('key', '')
        index = self.get_args('index', '')
        field = self.get_args('field', '')
        value = self.get_args('value', '')

        if key:
    
            if self.redis.exists(key):
                
                _type = self.redis.type(key)

                if _type == 'string':
                    result = self.edit_strings(key, value)
                elif _type == 'list':
                    result = self.edit_lists(key, index, value)
                elif _type == 'hash':
                    result = self.edit_hashs(key, index, value)
                elif _type == 'set':
                    result = self.edit_sets(key, field, value)
                elif _type == 'zset':
                    result = self.edit_sortedsets(key, field, value)
                else:
                    logging.error('Unexpected key type by %s' % key)
                    result = False

                self.write(dict(success=result))
                return

        self.write(dict(success=False))
        return
    
    def edit_strings(self, key, value):
        return self.redis.set(key, value)

    def edit_lists(self, key, index, value):
        index = int(index) if index.isdigit() else None
        return self.redis.lset(key, index, value) if index is not None else False

    def edit_hashs(self, key, field, value):
        return self.redis.hset(key, field, value)

    def edit_sets(self, key, field, value):
        if field == value:
            return True
        self.redis.srem(key, field)
        return self.redis.sadd(key, value)

    def edit_sortedsets(self, key, field, value):
        if field == value:
            return True
        score = self.redis.zscore(key, field)
        self.redis.zrem(key, field)
        return self.redis.zadd(key, score, value)


@route("/add", name="add")
class Add(RequestHandler):
    @tornado.web.authenticated
    def get(self):
    
        key = self.get_args('key', '')
        value = self.get_args('value', '')

        if key:
    
            if self.redis.exists(key):
                
                _type = self.redis.type(key)

                if _type == 'string':
                    result = self.add_strings(key, value)
                elif _type == 'list':
                    pos = self.get_args('pos','r')
                    result = self.add_lists(key, value, pos)
                elif _type == 'hash':
                    field = self.get_args('field', '')
                    result = self.add_hashs(key, field, value) if field else False
                elif _type == 'set':
                    result = self.add_sets(key, value)
                elif _type == 'zset':
                    score = self.get_args('score','')
                    result = self.add_sortedsets(key, score, value) if score else False
                else:
                    logging.error('Unexpected key type by %s' % key)
                    result = False

                self.write(dict(success=result))
                return

        self.write(dict(success=False))
        return
    
    def add_strings(self, key, value):
        """ return a length with key """
        return self.redis.append(key, value)
        
    def add_lists(self, key, value, pos):
        """ return a index with key """
        if pos=='r':
            return self.redis.rpush(key, value)
        else:
            return self.redis.lpush(key, value)
        
    def add_hashs(self, key, field, value):
        """ return a changed lines with key """
        return self.redis.hset(key, field, value)

    def add_sets(self, key, member):
        """ return a changed lines with key """
        return self.redis.sadd(key, member)
        
    def add_sortedsets(self, key, score, member):
        """ return a changed lines with key """
        return self.redis.zadd(key, score, member)


@route("/remove", name="remove")
class Remove(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        
        key = self.get_args('key', '')
        field = self.get_args('field', '')
        
        if key:
    
            if self.redis.exists(key):

                _type = self.redis.type(key)

                if _type == 'hash':
                    result = self.redis.hdel(key, field)
                elif _type == 'set':
                    result = self.redis.srem(key, field)
                elif _type == 'zset':
                    result = self.redis.zrem(key, field)
                else:
                    logging.error('Unexpected key type by %s' % key)
                    result = False

                self.write(dict(success=result))
                return

        self.write(dict(success=False))
        return


@route("/pop", name="pop")
class Pop(RequestHandler):
    @tornado.web.authenticated
    def get(self):
        
        key = self.get_args('key', '')
        pos = self.get_args('pos', 'l')
        
        if key:
    
            if self.redis.exists(key):

                _type = self.redis.type(key)

                if _type == 'list':
                    if pos=='r':
                        result = self.redis.rpop(key)
                    else:
                        result = self.redis.lpop(key)
                else:
                    logging.error('Can not pop by key %s' % key)
                    result = False

                self.write(dict(success=result))
                return

        self.write(dict(success=False))
        return


@route("/delete", name="delete")
class Delete(RequestHandler):
    @tornado.web.authenticated
    def get(self):

        key = self.get_args('key', '')
        if key:
            result = self.redis.delete(key)

            self.write(dict(success=result))
            return 
        
        self.write(dict(success=False))
        return 


@route("/login", name='login')
class Login(RequestHandler):
    def get(self):
        form = self.forms.LoginForm()
        self.render('login.html', form=form)
        return 
     
    def post(self):
        form = self.forms.LoginForm(self.request.arguments)
    
        if form.validate():
            if self.settings['username']==form.username.data and \
                    self.settings['password']==form.password.data:

                self.session['user'] = {'username': self.settings['username']}
                self.session.save()
                
                self.redirect(self.reverse_url('index'))
                return
            else:
                form.submit.errors.append(self._("The username or password you provided are incorrect."))

        self.render('login.html', form=form)
        return 


@route("/logout", name='logout')
class Logout(RequestHandler):
    def get(self):

        del self.session['user']
        self.session.save()

        self.redirect(self.reverse_url('index'))
        return



########NEW FILE########
