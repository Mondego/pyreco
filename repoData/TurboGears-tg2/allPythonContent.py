__FILENAME__ = test_controller
# -*- coding: utf-8 -*-
from paste.fixture import TestApp

import os.path
config = 'config:'+(os.path.abspath(os.path.basename(__name__)+'/../../development.ini#main'))

app = TestApp(config)

class TestTGController:
    def test_index(self):
        resp = app.get('/')
        assert 'TurboGears 2 is a open source front-to-back web development' in resp.body, resp.body

########NEW FILE########
__FILENAME__ = test_controller
# -*- coding: utf-8 -*-
from paste.fixture import TestApp

import os.path
config = 'config:'+(os.path.abspath(os.path.basename(__name__)+'/../../development.ini#main'))

app = TestApp(config)

class TestTGController:
    def test_index(self):
        resp = app.get('/')
        assert 'TurboGears 2 is a open source front-to-back web development' in resp.body, resp.body

########NEW FILE########
__FILENAME__ = testapp
#!/usr/bin/python
from wsgiref.simple_server import make_server
import sys
import tg
from tg.configuration import AppConfig
from tg import TGController, expose

class RootController(TGController):
    @expose()
    def index(self, *args, **kw):
        return 'HELLO FROM %s' % tg.request.path

    @expose()
    def somewhere(self):
        return 'WELCOME SOMEWHERE'

    @expose('testapp.mak')
    def test(self):
        return dict(ip=tg.request.remote_addr)

app_config = AppConfig(minimal=True)
app_config['tg.root_controller'] = RootController()

#Setup support for MAKO.
app_config.renderers = ['mako']
app_config.default_renderer = 'mako'
app_config.use_dotted_templatenames = False

app = app_config.make_wsgi_app()
make_server('', 8080, app).serve_forever()


########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

import os, shutil
from unittest import TestCase

try:
    from xmlrpclib import loads, dumps
except ImportError:
    from xmlrpc.client import loads, dumps
import warnings

import beaker

from tg.support.registry import Registry, RegistryManager

from webtest import TestApp

import tg
from tg import tmpl_context, request_local
from tg.configuration import milestones

from tg.wsgiapp import ContextObj, TGApp, RequestLocals
from tg.controllers import TGController

from .test_stack.baseutils import ControllerWrap, FakeRoutes, default_config

from beaker.middleware import CacheMiddleware

data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'session')

def setup_session_dir():
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

def teardown_session_dir():
    shutil.rmtree(session_dir, ignore_errors=True)

def make_app(controller_klass=None, environ=None):
    """Creates a `TestApp` instance."""
    if controller_klass is None:
        controller_klass = TGController

    tg.config['renderers'] = default_config['renderers']
    tg.config['rendering_engines_options'] = default_config['rendering_engines_options']

    app = TGApp(config=default_config)
    app.controller_classes['root'] = ControllerWrap(controller_klass)

    app = FakeRoutes(app)

    app = RegistryManager(app)
    app = beaker.middleware.SessionMiddleware(app, {}, data_dir=session_dir)
    app = CacheMiddleware(app, {}, data_dir=os.path.join(data_dir, 'cache'))
    return TestApp(app)

def create_request(path, environ=None):
    """Helper used in test cases to quickly setup a request obj.

    ``path``
        The path will become PATH_INFO
    ``environ``
        Additional environment

    Returns an instance of the `webob.Request` object.
    """
    # setup the environ
    if environ is None:
        environ = {}

    # create a "blank" WebOb Request object
    # using TG Request which is a webob Request plus
    # some compatibility methods
    req = request_local.Request.blank(path, environ)

    # setup a Registry
    reg = environ.setdefault('paste.registry', Registry())
    reg.prepare()

    # Setup turbogears context with request, url and tmpl_context
    tgl = RequestLocals()
    tgl.tmpl_context = ContextObj()
    tgl.request = req

    request_local.context._push_object(tgl)

    return req

class TestWSGIController(TestCase):
    def setUp(self):
        tmpl_options = {}
        tmpl_options['genshi.search_path'] = ['tests']

        self._tgl = RequestLocals()
        self._tgl.tmpl_context = ContextObj()
        request_local.context._push_object(self._tgl)

        # Mark configuration milestones as passed as
        # test sets up a fake configuration
        milestones._reach_all()

        warnings.simplefilter("ignore")
        tg.config.push_process_config(default_config)
        warnings.resetwarnings()
        setup_session_dir()

    def tearDown(self):
        request_local.context._pop_object(self._tgl)
        tg.config.pop_process_config()
        teardown_session_dir()

        # Reset milestones
        milestones._reset_all()

    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['tg.routes_dict'].update(kargs)

        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')

        return self.app.post(url, extra_environ=self.environ, params=kargs)


########NEW FILE########
__FILENAME__ = model
"""A fake application's model objects"""

from datetime import datetime

from zope.sqlalchemy import ZopeTransactionExtension
from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.orm import scoped_session, sessionmaker, relation, backref, \
                           synonym
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import String, Unicode, UnicodeText, Integer, DateTime, \
                             Boolean, Float


# Global session manager.  DBSession() returns the session object
# appropriate for the current web request.
maker = sessionmaker(autoflush=True, autocommit=False,
                     extension=ZopeTransactionExtension())
DBSession = scoped_session(maker)

# By default, the data model is defined with SQLAlchemy's declarative
# extension, but if you need more control, you can switch to the traditional
# method.
DeclarativeBase = declarative_base()

# Global metadata.
# The default metadata is the one from the declarative base.
metadata = DeclarativeBase.metadata

def init_model(engine):
    """Call me before using any of the tables or classes in the model."""
    DBSession.configure(bind=engine)


class Group(DeclarativeBase):
    """An ultra-simple group definition.
    """
    __tablename__ = 'tg_group'
    
    group_id = Column(Integer, autoincrement=True, primary_key=True)
    
    group_name = Column(Unicode(16), unique=True)
    
    display_name = Column(Unicode(255))
    
    created = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return '<Group: name=%s>' % self.group_name

########NEW FILE########
__FILENAME__ = test_balanced_session
from tg.configuration.sqla.balanced_session import BalancedSession, UsingEngineContext, force_request_engine
from tg.util import Bunch
from tg.wsgiapp import RequestLocals
from tg import request_local
import tg

class TestBalancedSession(object):
    def setup(self):
        locals = RequestLocals()
        locals.request = Bunch()
        locals.app_globals = Bunch()
        locals.config = Bunch({'tg.app_globals':locals.app_globals,
                               'balanced_engines': {'all':{'master':'master',
                                                            'slave1':'slave1',
                                                            'slave2':'slave2'},
                                                    'master':'master',
                                                    'slaves':{'slave1':'slave1',
                                                              'slave2':'slave2'}}})

        #Register Global objects
        request_local.config._push_object(locals.config)
        request_local.context._push_object(locals)

        self.locals = locals
        self.session = BalancedSession()
        locals.config['DBSession'] = self.session

    def teardown(self):
        request_local.config._pop_object()
        request_local.context._pop_object()

    def test_disabled_balancing(self):
        tg.config['balanced_engines'] = None
        tg.app_globals['sa_engine'] = 'DEFAULT_ENGINE'
        assert self.session.get_bind() == 'DEFAULT_ENGINE'

    def test_disabled_balancing_out_of_request(self):
        request_local.context._pop_object()
        tg.config['balanced_engines'] = None
        tg.config['tg.app_globals']['sa_engine'] = 'DEFAULT_ENGINE'
        assert self.session.get_bind() == 'DEFAULT_ENGINE'
        request_local.context._push_object(self.locals)

    def test_master_on_flush(self):
        self.session._flushing = True
        assert self.session.get_bind() == 'master'

    def test_master_out_of_request(self):
        request_local.context._pop_object()
        assert self.session.get_bind() == 'master'
        request_local.context._push_object(self.locals)

    def test_pick_slave(self):
        assert self.session.get_bind().startswith('slave')

    def test_with_context(self):
        with self.session.using_engine('master'):
            assert self.session.get_bind() == 'master'
        assert self.session.get_bind().startswith('slave')

    def test_forced_engine(self):
        force_request_engine('slave2')
        assert self.session.get_bind() == 'slave2'

    def test_with_explicit_context(self):
        class FakeThreadedSession:
            def __init__(self, real_session):
                self.sess = real_session
            def __call__(self):
                return self.sess

        self.locals.config['DBSession'] = FakeThreadedSession(self.session)
        with UsingEngineContext('master'):
            assert self.session.get_bind() == 'master'
        assert self.session.get_bind().startswith('slave')

########NEW FILE########
__FILENAME__ = test_caching
# -*- coding: utf-8 -*-

""" Test cases for TG caching.  See:

http://turbogears.org/2.1/docs/main/Caching.html

For more details.
"""


import tg
from tg.controllers import TGController
from tg.decorators import expose, cached
from tg.caching import create_cache_key, cached_property, beaker_cache
from tg.controllers.util import etag_cache
from tg import cache
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir

def setup():
    setup_session_dir()
    
def teardown():
    teardown_session_dir()

# a variable used to represent state held outside the controllers
mockdb = {}

class MockTime:
    
    """ A very simple class to mock the time module. This lets us slide time
    around to fake expiry in beaker.container. """
    
    mock_time = 0
    
    def time(self):
        return self.mock_time
    
    def set_time(self, v):
        self.mock_time = v

mocktime = MockTime()
import beaker.container
beaker.container.time = mocktime

class TestCachedProperty(object):
    def setup(self):
        class FakeObject(object):
            def __init__(self):
                self.v = 0

            @cached_property
            def value(self):
                self.v += 1
                return self.v

        self.FakeObjectClass = FakeObject

    def test_cached_property(self):
        o = self.FakeObjectClass()
        for i in range(10):
            assert o.value == 1

    def test_cached_property_on_class(self):
        assert isinstance(self.FakeObjectClass.value, cached_property)

class SimpleCachingController(TGController):
    
    """ Pylons supports a mechanism for arbitrary caches that can be allocated
    within controllers. Each cache value has a creation function associated
    with it that is called to retrieve it's results. """
    
    @expose()
    def simple(self, a):
        c = cache.get_cache("BasicTGController.index")
        x = c.get_value(key=a, 
                        createfunc=lambda: "cached %s" % a,
                        type="memory",
                        expiretime=3600)
        return x
    
    def createfunc(self):
        return "cached %s" % mockdb['expiry']
    
    @expose()
    def expiry(self, a):
        mockdb['expiry'] = a # inject a value into the context
        c = cache.get_cache("BasicTGController.index")
        x = c.get_value(key='test', 
                        createfunc=self.createfunc,
                        type="memory",
                        expiretime=100)
        return x

class TestSimpleCaching(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        self.app = make_app(SimpleCachingController, self.baseenviron)

    def test_simple_cache(self):
        """ test that caches get different results for different cache keys. """
        resp = self.app.get('/simple/', params={'a':'foo'})
        assert resp.body.decode('ascii') == 'cached foo'
        resp = self.app.get('/simple/', params={'a':'bar'})
        assert resp.body.decode('ascii') == 'cached bar'
        resp = self.app.get('/simple/', params={'a':'baz'})
        assert resp.body.decode('ascii') == 'cached baz'

    def test_expiry(self):
        """ test that values expire from a single cache key. """
        mocktime.set_time(0)
        resp = self.app.get('/expiry/', params={'a':'foo1'})
        assert resp.body.decode('ascii') == 'cached foo1'
        mocktime.set_time(1)
        resp = self.app.get('/expiry/', params={'a':'foo2'})
        assert resp.body.decode('ascii') == 'cached foo1'
        mocktime.set_time(200) # wind clock past expiry
        resp = self.app.get('/expiry/', params={'a':'foo2'})
        assert resp.body.decode('ascii') == 'cached foo2'

class DecoratorController(TGController):
    
    @cached(expire=100, type='memory')
    @expose()
    def simple(self):
        return "cached %s" % mockdb['DecoratorController.simple']
    
class TestDecoratorCaching(TestWSGIController):
    
    """ Test that the decorators function. """
    
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        self.app = make_app(DecoratorController, self.baseenviron)
    
    def test_simple(self):
        """ Test expiry of cached results for decorated functions. """
        mocktime.set_time(0)
        mockdb['DecoratorController.simple'] = 'foo1'
        resp = self.app.get('/simple/')
        assert resp.body.decode('ascii') == 'cached foo1'
        mocktime.set_time(1)
        mockdb['DecoratorController.simple'] = 'foo2'
        resp = self.app.get('/simple/')
        assert resp.body.decode('ascii') == 'cached foo1'
        mocktime.set_time(200)
        mockdb['DecoratorController.simple'] = 'foo2'
        resp = self.app.get('/simple/')
        assert resp.body.decode('ascii') == 'cached foo2'

class EtagController(TGController):

    @expose()
    def etagged(self, etag):
        etag_cache(etag)
        return "bar"
    
class TestEtagCaching(TestWSGIController):
    
    """ A simple mechanism is provided to set the etag header for returned results. """
    
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(EtagController)

    def test_etags(self):
        """ Test that the etag in the response headers is the one we expect. """
        resp = self.app.get('/etagged/', params={'etag':'foo'})
        assert resp.etag == 'foo', resp.etag
        resp = self.app.get('/etagged/', params={'etag':'bar'})
        assert resp.etag == 'bar', resp.etag    
        
    def test_304(self):
        resp = self.app.get('/etagged/', params={'etag':'foo'}, headers={'if-none-match': '"foo"'})
        assert "304" in resp.status, resp

class SessionTouchController(TGController):
    @expose()
    def session_get(self):
        if tg.session.accessed():
            return 'ACCESSED'
        else:
            return 'NOTOUCH'

class TestSessionTouch(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(SessionTouchController)

    def test_prova(self):
        tg.config['beaker.session.tg_avoid_touch'] = False
        assert 'ACCESSED' in self.app.get('/session_get')

    def test_avoid_touch(self):
        tg.config['beaker.session.tg_avoid_touch'] = True
        assert 'NOTOUCH' in self.app.get('/session_get')


def disable_cache(wrapped):
    def wrapper(*args, **kws):
        tg.config['cache_enabled'] = False
        x = wrapped(*args, **kws)
        tg.config['cache_enabled'] = True
        return x
    return wrapper


class CachedController(TGController):
    CALL_COUNT = 0

    @expose()
    @cached(key=None)
    def none_key(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached()
    def no_options(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached(key='arg')
    def specified_cache_key(self, arg):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached(key=['arg1', 'arg2'])
    def specified_cache_key_args(self, arg1, arg2):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached(query_args=True)
    def cache_with_args(self, arg):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @disable_cache
    @cached()
    def disabled_cache(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    def invalidate_on_startup(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached(invalidate_on_startup=True)
    def invalidate_on_startup(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT


class BeakerCacheController(TGController):  # For backward compatibility
    CALL_COUNT = 0

    @expose()
    @beaker_cache(key=None)
    def none_key(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache()
    def no_options(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache(key='arg')
    def specified_cache_key(self, arg):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache(key=['arg1', 'arg2'])
    def specified_cache_key_args(self, arg1, arg2):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache(query_args=True)
    def cache_with_args(self, arg):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @disable_cache
    @beaker_cache()
    def disabled_cache(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    def invalidate_on_startup(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache(invalidate_on_startup=True)
    def invalidate_on_startup(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT


class TestCacheTouch(TestWSGIController):
    CACHED_CONTROLLER = CachedController

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(self.CACHED_CONTROLLER)

    def test_none_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/none_key')
        assert 'Counter=1' in r
        r = self.app.get('/none_key')
        assert 'Counter=1' in r

    def test_invalidate_on_startup(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/invalidate_on_startup')
        assert 'Counter=1' in r
        r = self.app.get('/invalidate_on_startup')
        assert 'Counter=2' in r

    def test_no_options(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/no_options')
        assert 'Counter=1' in r
        r = self.app.get('/no_options')
        assert 'Counter=1' in r

    def test_specified_cache_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r

    def test_specified_cache_key_args(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=y')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=y')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=z')
        assert 'Counter=2' in r

    def test_cache_with_args(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/cache_with_args?arg=x')
        assert 'Counter=1' in r, r
        r = self.app.get('/cache_with_args?arg=x')
        assert 'Counter=1' in r, r

    def test_different_cache_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key?arg=y')
        assert 'Counter=2' in r

    def test_cache_key_instance_method(self):
        class Something(object):
            def method(self, arg):
                return arg

        o = Something()
        namespace, key = create_cache_key(o.method)

        assert namespace == 'tests.test_caching.Something'
        assert key == 'method'

    def test_cache_key_function(self):
        def method(self, arg):
            return arg

        namespace, key = create_cache_key(method)

        assert namespace == 'tests.test_caching'
        assert key == 'method'

    def test_disable_cache(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/disabled_cache')
        assert 'Counter=1' in r
        r = self.app.get('/disabled_cache')
        assert 'Counter=2' in r


class TestBeakerCacheTouch(TestWSGIController):
    CACHED_CONTROLLER = BeakerCacheController

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(self.CACHED_CONTROLLER)

    def test_none_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/none_key')
        assert 'Counter=1' in r
        r = self.app.get('/none_key')
        assert 'Counter=1' in r

    def test_invalidate_on_startup(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/invalidate_on_startup')
        assert 'Counter=1' in r
        r = self.app.get('/invalidate_on_startup')
        assert 'Counter=2' in r

    def test_no_options(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/no_options')
        assert 'Counter=1' in r
        r = self.app.get('/no_options')
        assert 'Counter=1' in r

    def test_specified_cache_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r

    def test_specified_cache_key_args(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=y')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=y')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=z')
        assert 'Counter=2' in r

    def test_cache_with_args(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/cache_with_args?arg=x')
        assert 'Counter=1' in r, r
        r = self.app.get('/cache_with_args?arg=x')
        assert 'Counter=1' in r, r

    def test_different_cache_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key?arg=y')
        assert 'Counter=2' in r

    def test_cache_key_instance_method(self):
        class Something(object):
            def method(self, arg):
                return arg

        o = Something()
        namespace, key = create_cache_key(o.method)

        assert namespace == 'tests.test_caching.Something'
        assert key == 'method'

    def test_cache_key_function(self):
        def method(self, arg):
            return arg

        namespace, key = create_cache_key(method)

        assert namespace == 'tests.test_caching'
        assert key == 'method'

    def test_disable_cache(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/disabled_cache')
        assert 'Counter=1' in r
        r = self.app.get('/disabled_cache')
        assert 'Counter=2' in r

########NEW FILE########
__FILENAME__ = test_configuration
"""
Testing for TG2 Configuration
"""
from nose import SkipTest
from nose.tools import eq_, raises
import atexit, sys, os

from tg.util import Bunch
from tg.configuration import AppConfig, config
from tg.configuration.app_config import TGConfigError
from tg.configuration.auth import _AuthenticationForgerPlugin
from tg.configuration.auth.metadata import _AuthMetadataAuthenticator
from tg.configuration.utils import coerce_config
from tg.configuration import milestones
from paste.deploy.converters import asint

import tg.i18n
from tg import TGController, expose, response, request, abort
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request
from webtest import TestApp
from tg.renderers.base import RendererFactory

from tg.wsgiapp import TGApp
from tg._compat import PY3

def setup():
    milestones._reset_all()
    setup_session_dir()
def teardown():
    milestones._reset_all()
    teardown_session_dir()

class PackageWithModel:
    __name__ = 'tests'
    __file__ = __file__

    def __init__(self):
        self.model = self.ModelClass()
        self.model.DBSession = self.model.FakeDBSession()

    class ModelClass:
        class FakeDBSession:
            def remove(self):
                self.DBSESSION_REMOVED=True

        @classmethod
        def init_model(package, engine):
            pass

    class lib:
        class app_globals:
            class Globals:
                pass
PackageWithModel.__name__ = 'tests'

class UncopiableList(list):
    """
    This is to test configuration methods that make a copy
    of a list to modify it, using this we can check how it has
    been modified
    """
    def __copy__(self):
        return self

class FakeTransaction:
    def get(self):
        return self

    def begin(self):
        self.aborted = False
        self.doomed = False

    def abort(self):
        self.aborted = True

    def commit(self):
        self.aborted = False

    def _retryable(self, *args):
        return True
    note = _retryable

    def isDoomed(self):
        return self.doomed

    def doom(self):
        self.doomed = True

from tg.configuration.auth import TGAuthMetadata
class ApplicationAuthMetadata(TGAuthMetadata):
    def get_user(self, identity, userid):
        return {'name':'None'}

class ApplicationAuthMetadataWithAuthentication(TGAuthMetadata):
    def authenticate(self, environ, identity):
        return 1
    def get_user(self, identity, userid):
        return {'name':'None'}

class AtExitTestException(Exception):
    pass

class TestPylonsConfigWrapper:

    def setup(self):
        self.config = config

    def test_create(self):
        pass

    def test_getitem(self):
        expected_keys = ['global_conf', 'use_sqlalchemy', 'package', 'tg.app_globals', 'call_on_shutdown']
        for key in expected_keys:
            self.config[key]

    @raises(KeyError)
    def test_getitem_bad(self):
        self.config['no_such_key']

    def test_setitem(self):
        self.config['no_such_key'] = 'something'

    def test_delattr(self):
        del self.config.use_sqlalchemy
        eq_(hasattr(self.config, 'use_sqlalchemy'), False)
        self.config.use_sqlalchemy = True

    @raises(AttributeError)
    def test_delattr_bad(self):
        del self.config.i_dont_exist

    def test_keys(self):
        k = self.config.keys()
        assert 'tg.app_globals' in k

def test_coerce_config():
    conf = coerce_config({'ming.connection.max_pool_size':'5'}, 'ming.connection.', {'max_pool_size':asint})
    assert conf['max_pool_size'] == 5

class TestAppConfig:
    def __init__(self):
        self.fake_package = PackageWithModel

    def setup(self):
        milestones._reset_all()

        self.config = AppConfig()
        # set up some required paths and config settings
        # FIXME: these seem to be needed so that
        # other tests don't suffer - but that's a nasty
        # side-effect. setup for those tests actually needs
        # fixing.
        self.config.package = self.fake_package
        self.config['paths']['root'] = 'test'
        self.config['paths']['controllers'] = 'test.controllers'
        self.config._init_config({'cache_dir':'/tmp'}, {})

        config['paths']['static_files'] = "test"
        config["tg.app_globals"] = Bunch()
        config["use_sqlalchemy"] = False
        config["global_conf"] = Bunch()
        config["package"] = "test"
        config["render_functions"] = Bunch()
        config['beaker.session.secret'] = 'some_secret'

    def teardown(self):
        #This is here to avoid that other tests keep using the forced controller
        config.pop('tg.root_controller', None)
        milestones._reset_all()

    def test_get_root(self):
        current_root_module = self.config['paths']['root']
        assert self.config.get_root_module() == 'tests.controllers.root', self.config.get_root_module()
        self.config['paths']['root'] = None
        assert self.config.get_root_module() == None, self.config.get_root_module()
        self.config['paths']['root'] = current_root_module

    def test_lang_can_be_changed_by_ini(self):
        conf = AppConfig(minimal=True)
        conf._init_config({'lang':'ru'}, {})
        assert config['lang'] == 'ru'

    def test_create_minimal_app(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

        #This is here to avoid that other tests keep using the forced controller
        config.pop('tg.root_controller')

    def test_enable_routes(self):
        if PY3: raise SkipTest()

        conf = AppConfig(minimal=True)
        conf.enable_routes = True
        app = conf.make_wsgi_app()

        a = TGApp()
        assert a.enable_routes == True

        config.pop('routes.map')
        config.pop('enable_routes')

    def test_create(self):
        pass

    def test_setup_startup_and_shutdown_startup_callable(self):
        def func():
            a = 7
        self.config.call_on_startup = [func]
        self.config._setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_callable_startup_with_exception(self):
        def func():
            raise Exception
        self.config.call_on_startup = [func]
        self.config._setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_startup_not_callable(self):
        self.config.call_on_startup = ['not callable']
        self.config._setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_shutdown_not_callable(self):
        self.config.call_on_shutdown = ['not callable']
        self.config._setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_shutdown_callable(self):
        def func():
            raise AtExitTestException()

        _registered_exit_funcs = []
        def _fake_atexit_register(what):
            _registered_exit_funcs.append(what)

        _real_register = atexit.register
        atexit.register = _fake_atexit_register

        try:
            self.config.call_on_shutdown = [func]
            self.config._setup_startup_and_shutdown()
        finally:
            atexit.register = _real_register

        assert func in _registered_exit_funcs, _registered_exit_funcs

    def test_setup_helpers_and_globals(self):
        self.config.setup_helpers_and_globals()

    def test_setup_sa_auth_backend(self):
        class ConfigWithSetupAuthBackend(self.config.__class__):
            called = []

            def setup_sa_auth_backend(self):
                self.called.append(True)

        conf = ConfigWithSetupAuthBackend()
        conf.setup_auth()

        assert len(ConfigWithSetupAuthBackend.called) >= 1

    def test_setup_jinja_without_package(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.renderers = ['jinja']
        app = conf.make_wsgi_app()

    def test_setup_sqlalchemy(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf['sqlalchemy.url'] = 'sqlite://'
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert package.model.DBSession.DBSESSION_REMOVED

    def test_custom_transaction_manager(self):
        class CustomAppConfig(AppConfig):
            def add_tm_middleware(self, app):
                self.did_perform_custom_tm = True
                return app

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        package = PackageWithModel()
        conf = CustomAppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite://'

        app = conf.make_wsgi_app()

        assert conf.did_perform_custom_tm == True
        assert conf.application_wrappers == []

    def test_sqlalchemy_commit_veto(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

            @expose()
            def crash(self):
                raise Exception('crash')

            @expose()
            def forbidden(self):
                response.status = 403
                return 'FORBIDDEN'

            @expose()
            def notfound(self):
                response.status = 404
                return 'NOTFOUND'

        def custom_commit_veto(environ, status, headers):
            if status.startswith('404'):
                return True
            return False

        fake_transaction = FakeTransaction()
        import transaction
        prev_transaction_manager = transaction.manager
        transaction.manager = fake_transaction

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite://'
        conf.commit_veto = custom_commit_veto

        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test')
        assert fake_transaction.aborted == False

        try:
            app.get('/crash')
        except:
            pass
        assert fake_transaction.aborted == True

        app.get('/forbidden', status=403)
        assert fake_transaction.aborted == False

        app.get('/notfound', status=404)
        assert fake_transaction.aborted == True

        transaction.manager = prev_transaction_manager

    def test_sqlalchemy_doom(self):
        fake_transaction = FakeTransaction()
        import transaction
        prev_transaction_manager = transaction.manager
        transaction.manager = fake_transaction

        class RootController(TGController):
            @expose()
            def test(self):
                fake_transaction.doom()
                return 'HI!'

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite://'

        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test')
        assert fake_transaction.aborted == True

        transaction.manager = prev_transaction_manager

    def test_sqlalchemy_retry(self):
        fake_transaction = FakeTransaction()
        import transaction
        prev_transaction_manager = transaction.manager
        transaction.manager = fake_transaction

        from transaction.interfaces import TransientError

        class RootController(TGController):
            attempts = []

            @expose()
            def test(self):
                self.attempts.append(True)
                if len(self.attempts) == 3:
                    return 'HI!'
                raise TransientError()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite://'
        conf['tm.attempts'] = 3

        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        assert 'HI' in resp

        transaction.manager = prev_transaction_manager

    def test_setup_sqla_persistance(self):
        config['sqlalchemy.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        self.config.setup_persistence()

        self.config.use_sqlalchemy = False

    def test_setup_sqla_balanced(self):
        config['sqlalchemy.master.url'] = 'sqlite://'
        config['sqlalchemy.slaves.slave1.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        self.config.setup_persistence()

        self.config.use_sqlalchemy = False
        config.pop('sqlalchemy.master.url')
        config.pop('sqlalchemy.slaves.slave1.url')

    @raises(TGConfigError)
    def test_setup_sqla_balanced_prevent_slave_named_master(self):
        config['sqlalchemy.master.url'] = 'sqlite://'
        config['sqlalchemy.slaves.master.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        try:
            self.config.setup_persistence()
        except:
            raise
        finally:
            self.config.use_sqlalchemy = False
            config.pop('sqlalchemy.master.url')
            config.pop('sqlalchemy.slaves.master.url')

    @raises(TGConfigError)
    def test_setup_sqla_balanced_no_slaves(self):
        config['sqlalchemy.master.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        try:
            self.config.setup_persistence()
        except:
            raise
        finally:
            self.config.use_sqlalchemy = False
            config.pop('sqlalchemy.master.url')

    def test_setup_ming_persistance(self):
        if PY3: raise SkipTest()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://'
        conf['ming.db'] = 'inmemdb'

        app = conf.make_wsgi_app()
        assert app is not None

    def test_setup_ming_persistance_with_url_alone(self):
        if PY3: raise SkipTest()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://inmemdb'

        app = conf.make_wsgi_app()
        assert app is not None

    def test_setup_ming_persistance_advanced_options(self):
        if PY3: raise SkipTest()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://inmemdb'
        conf['ming.connection.read_preference'] = 'PRIMARY'

        app = conf.make_wsgi_app()
        assert app is not None

    def test_add_auth_middleware(self):
        class Dummy:pass

        self.config.sa_auth.dbsession = Dummy()
        self.config.sa_auth.user_class = Dummy
        self.config.sa_auth.group_class = Dummy
        self.config.sa_auth.permission_class = Dummy
        self.config.sa_auth.cookie_secret = 'dummy'
        self.config.sa_auth.password_encryption_method = 'sha'

        self.config.setup_auth()
        self.config.add_auth_middleware(None, None)

    def test_add_static_file_middleware(self):
        self.config.add_static_file_middleware(None)

    def test_setup_sqla_auth(self):
        if PY3: raise SkipTest()

        class RootController(TGController):
            @expose()
            def test(self):
                return str(request.environ)

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.auth_backend = 'sqlalchemy'
        conf.use_sqlalchemy = True
        conf['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                           'dbsession': None,
                           'user_class': None,
                           'cookie_secret':'12345'}
        conf['sqlalchemy.url'] = 'sqlite://'
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'repoze.who.plugins' in app.get('/test')

        self.config.auth_backend = None

    def test_setup_ming_auth(self):
        self.config.auth_backend = 'ming'

        self.config.setup_auth()
        assert 'sa_auth' in config

        self.config.auth_backend = None

    def test_register_hooks(self):
        def dummy(*args):
            pass

        milestones.config_ready._reset()
        milestones.environment_loaded._reset()
 
        self.config.register_hook('startup', dummy)
        self.config.register_hook('shutdown', dummy)
        self.config.register_hook('controller_wrapper', dummy)
        for hook_name in self.config.hooks.keys():
            self.config.register_hook(hook_name, dummy)

        milestones.config_ready.reach()
        milestones.environment_loaded.reach()

        for hooks in self.config.hooks.values():
            assert hooks

        assert self.config.call_on_startup
        assert self.config.call_on_shutdown
        assert self.config.controller_wrappers

    @raises(TGConfigError)
    def test_missing_secret(self):
        self.config.auth_backend = 'sqlalchemy'
        config.pop('beaker.session.secret', None)
        self.config.setup_auth()

    def test_controler_wrapper_setup(self):
        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = []
        self.config._setup_controller_wrappers()
        assert config['controller_caller'] == orig_caller

        def controller_wrapper(caller):
            def call(*args, **kw):
                return caller(*args, **kw)
            return call

        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = [controller_wrapper]
        self.config._setup_controller_wrappers()
        assert config['controller_caller'].__name__ == controller_wrapper(orig_caller).__name__

    def test_backward_compatible_controler_wrapper_setup(self):
        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = []
        self.config._setup_controller_wrappers()
        assert config['controller_caller'] == orig_caller

        def controller_wrapper(app_config, caller):
            def call(*args, **kw):
                return caller(*args, **kw)
            return call

        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = [controller_wrapper]
        self.config._setup_controller_wrappers()

        deprecated_wrapper = config['controller_caller'].wrapper
        assert deprecated_wrapper.__name__ == controller_wrapper(self.config, orig_caller).__name__

    def test_global_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_hook('controller_wrapper', controller_wrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True

    def test_backward_compatible_global_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(app_config, caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        def controller_wrapper2(app_config, caller):
            def call(controller, remainder, params):
                wrapper_has_been_visited.append(True)
                return caller(controller, remainder, params)
            return call

        def controller_wrapper3(caller):
            def call(config, controller, remainder, params):
                wrapper_has_been_visited.append(True)
                return caller(config, controller, remainder, params)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_hook('controller_wrapper', controller_wrapper2)
        conf.register_hook('controller_wrapper', controller_wrapper3)
        conf.register_hook('controller_wrapper', controller_wrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert len(wrapper_has_been_visited) == 3

    def test_dedicated_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        tg.hooks.wrap_controller(controller_wrapper, controller=RootController.test)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True

    def test_mixed_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        app_wrapper_has_been_visited = []
        def app_controller_wrapper(caller):
            def call(*args, **kw):
                app_wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        wrapper_has_been_visited = []
        def controller_wrapper(caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        tg.hooks.wrap_controller(app_controller_wrapper)
        tg.hooks.wrap_controller(controller_wrapper, controller=RootController.test)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True
        assert app_wrapper_has_been_visited[0] is True

    def test_application_wrapper_setup(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        class AppWrapper(object):
            def __init__(self, dispatcher):
                self.dispatcher = dispatcher
            def __call__(self, *args, **kw):
                wrapper_has_been_visited.append(True)
                return self.dispatcher(*args, **kw)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_wrapper(AppWrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] == True

    def test_application_wrapper_ordering_after(self):
        class AppWrapper1:
            pass
        class AppWrapper2:
            pass
        class AppWrapper3:
            pass
        class AppWrapper4:
            pass
        class AppWrapper5:
            pass

        conf = AppConfig(minimal=True)
        conf.register_wrapper(AppWrapper2)
        conf.register_wrapper(AppWrapper4, after=AppWrapper3)
        conf.register_wrapper(AppWrapper3)
        conf.register_wrapper(AppWrapper1, after=False)
        conf.register_wrapper(AppWrapper5, after=AppWrapper3)
        milestones.environment_loaded.reach()

        assert conf.application_wrappers[0] == AppWrapper1
        assert conf.application_wrappers[1] == AppWrapper2
        assert conf.application_wrappers[2] == AppWrapper3
        assert conf.application_wrappers[3] == AppWrapper4
        assert conf.application_wrappers[4] == AppWrapper5

    @raises(TGConfigError)
    def test_application_wrapper_blocked_after_milestone(self):
        class AppWrapper1:
            pass
        class AppWrapper2:
            pass

        conf = AppConfig(minimal=True)
        conf.register_wrapper(AppWrapper1)
        milestones.environment_loaded.reach()
        conf.register_wrapper(AppWrapper2)

    def test_wrap_app(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        middleware_has_been_visited = []
        class AppWrapper(object):
            def __init__(self, app):
                self.app = app
            def __call__(self, environ, start_response):
                middleware_has_been_visited.append(True)
                return self.app(environ, start_response)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app(wrap_app=AppWrapper)
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert middleware_has_been_visited[0] == True

    def test_unsupported_renderer(self):
        renderers = self.config.renderers
        self.config.renderers = ['unknwon']
        try:
            self.config._setup_renderers()
        except TGConfigError:
            self.config.renderers = renderers
        else:
            assert False

    @raises(TGConfigError)
    def test_cookie_secret_required(self):
        self.config.sa_auth = {}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, False)

    def test_sqla_auth_middleware(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'sqlauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_using_translations(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'translations': {'user_name':'SomethingElse'},
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'sqlauth' in authenticators

        auth = None
        for authname, authobj in self.config['sa_auth']['authenticators']:
            if authname == 'sqlauth':
                auth = authobj
                break

        assert auth is not None, self.config['sa_auth']['authenticators']
        assert auth.translations['user_name'] == 'SomethingElse', auth.translations

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_default_after(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'cookie_secret':'12345',
                                  'dbsession': None,
                                  'user_class': None,
                                  'authenticators':UncopiableList([('superfirst', None),
                                                                   ('default', None)])}

        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert authenticators[1] == 'superfirst'
        assert 'cookie' in authenticators
        assert 'sqlauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_no_authenticators(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'dbsession': None,
                                  'user_class': None,
                                  'cookie_secret':'12345'}

        #In this case we can just test it doesn't crash
        #as the sa_auth dict doesn't have an authenticators key to check for
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_only_mine(self):
        past_config_sa_auth = config.sa_auth
        config.sa_auth = {}

        class RootController(TGController):
            @expose()
            def test(self):
                return str(request.environ)

            @expose()
            def forbidden(self):
                response.status = "401"

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.auth_backend = 'sqlalchemy'
        conf.use_sqlalchemy = True
        conf['sqlalchemy.url'] = 'sqlite://'

        alwaysadmin = _AuthenticationForgerPlugin(fake_user_key='FAKE_USER')
        conf['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                           'cookie_secret':'12345',
                           'form_plugin':alwaysadmin,
                           'authenticators':UncopiableList([('alwaysadmin', alwaysadmin)]),
                           'identifiers':[('alwaysadmin', alwaysadmin)],
                           'challengers':[]}

        app = conf.make_wsgi_app()

        authenticators = [x[0] for x in conf['sa_auth']['authenticators']]
        assert authenticators[0] == 'alwaysadmin'
        assert 'sqlauth' not in authenticators

        challengers = [x[1] for x in conf['sa_auth']['challengers']]
        assert alwaysadmin in challengers

        app = TestApp(app)
        assert 'repoze.who.identity' in app.get('/test', extra_environ={'FAKE_USER':'admin'})
        assert app.get('/forbidden', status=401)

        self.config['sa_auth'] = {}
        self.config.auth_backend = None
        config.sa_auth = past_config_sa_auth

    def test_sqla_auth_logging_stderr(self):
        past_config_sa_auth = config.sa_auth
        config.sa_auth = {}

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.auth_backend = 'sqlalchemy'
        conf.use_sqlalchemy = True
        conf['sqlalchemy.url'] = 'sqlite://'

        alwaysadmin = _AuthenticationForgerPlugin(fake_user_key='FAKE_USER')
        conf['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                           'cookie_secret':'12345',
                           'form_plugin':alwaysadmin,
                           'log_level':'DEBUG',
                           'authenticators':UncopiableList([('alwaysadmin', alwaysadmin)]),
                           'identifiers':[('alwaysadmin', alwaysadmin)],
                           'challengers':[]}

        conf['sa_auth']['log_file'] = 'stderr'
        app = conf.make_wsgi_app()
        conf['sa_auth']['log_file'] = 'stdout'
        app = conf.make_wsgi_app()

        import tempfile
        f = tempfile.NamedTemporaryFile()
        conf['sa_auth']['log_file'] = f.name
        app = conf.make_wsgi_app()

        self.config['sa_auth'] = {}
        self.config.auth_backend = None
        config.sa_auth = past_config_sa_auth

    def test_ming_auth_middleware(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'ming'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'mingauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    @raises(KeyError)
    def test_sqla_auth_middleware_no_backend(self):
        #This is expected to raise error as no authenticators are specified for a custom backend
        past_config_sa_auth = config.sa_auth
        config.sa_auth = {}

        self.config.auth_backend = None
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'cookie_secret':'12345'}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert len(authenticators) == 1

        self.config['sa_auth'] = {}
        self.config.auth_backend = None
        config.sa_auth = past_config_sa_auth

    def test_tgauthmetadata_auth_middleware(self):
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'tgappauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_auth_middleware_doesnt_touch_authenticators(self):
        # Checks that the auth middleware process doesn't touch original authenticators
        # list, to prevent regressions on this.
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':[('default', None)]}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert len(authenticators) == 1

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_tgauthmetadata_loginpwd(self):
        who_authenticator = _AuthMetadataAuthenticator(ApplicationAuthMetadataWithAuthentication(), using_password=True)
        assert who_authenticator.authenticate({}, {}) == None

    def test_tgauthmetadata_nologinpwd(self):
        who_authenticator = _AuthMetadataAuthenticator(ApplicationAuthMetadataWithAuthentication(), using_password=False)
        assert who_authenticator.authenticate({}, {}) == 1

    def test_toscawidgets_recource_variant(self):
        if PY3: raise SkipTest()

        resultingconfig = {}

        def fake_make_middleware(app, twconfig):
            resultingconfig.update(twconfig)
            return app

        import tw.api
        prev_tw_make_middleware = tw.api.make_middleware

        tw.api.make_middleware = fake_make_middleware
        config['toscawidgets.framework.resource_variant'] = 'min'
        self.config.add_tosca_middleware(None)
        config.pop('toscawidgets.framework.resource_variant', None)
        tw.api.make_middleware = prev_tw_make_middleware

        assert resultingconfig['toscawidgets.framework.default_view'] == self.config.default_renderer
        assert resultingconfig['toscawidgets.framework.translator'] == tg.i18n.ugettext
        assert resultingconfig['toscawidgets.middleware.inject_resources'] == True
        assert tw.api.resources.registry.ACTIVE_VARIANT == 'min'

    def test_config_hooks(self):
        # Reset milestone so that registered hooks
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        visited_hooks = []
        def before_config_hook(app):
            visited_hooks.append('before_config')
            return app
        def after_config_hook(app):
            visited_hooks.append('after_config')
            return app

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_hook('before_config', before_config_hook)
        conf.register_hook('after_config', after_config_hook)
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert 'before_config' in visited_hooks
        assert 'after_config' in visited_hooks

    def test_controller_hooks_with_value(self):
        # Reset milestone so that registered hooks
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return tg.hooks.notify_with_value('test_hook', 'BO',
                                                  controller=RootController.test)

        def value_hook(value):
            return value*2

        tg.hooks.register('test_hook', value_hook, controller=RootController.test)

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        assert 'BOBO' in resp, resp

    @raises(TGConfigError)
    def test_config_hooks_startup_on_controller(self):
        def f():
            pass

        tg.hooks.register('startup', None, controller=f)

    @raises(TGConfigError)
    def test_config_hooks_shutdown_on_controller(self):
        def f():
            pass

        tg.hooks.register('shutdown', None, controller=f)

    @raises(TGConfigError)
    def test_controller_wrapper_using_register(self):
        milestones.config_ready.reach()
        tg.hooks.register('controller_wrapper', None)

    @raises(TGConfigError)
    def test_global_controller_wrapper_after_milestone_reached(self):
        milestones.environment_loaded.reach()
        tg.hooks.wrap_controller(None)

    @raises(TGConfigError)
    def test_dedicated_controller_wrapper_after_milestone_reached(self):
        milestones.environment_loaded.reach()

        def f():
            pass

        tg.hooks.wrap_controller(None, controller=f)

    def test_error_middleware_disabled_with_optimize(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()

        os.environ['PYTHONOPTIMIZE'] = '2'
        app = conf.make_wsgi_app()
        os.environ.pop('PYTHONOPTIMIZE')

        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    def test_serve_statics(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        conf.serve_static = True
        app = conf.make_wsgi_app()
        assert app.__class__.__name__.startswith('Statics')

        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    def test_mount_point_with_minimal(self):
        class SubController(TGController):
            @expose()
            def test(self):
                return self.mount_point

        class RootController(TGController):
            sub = SubController()

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()

        app = TestApp(app)
        assert '/sub' in app.get('/sub/test')

    def test_application_test_vars(self):
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app(global_conf={'debug':True})
        app = TestApp(app)

        assert 'DONE' in app.get('/_test_vars')
        assert request.path == '/_test_vars'

    def test_application_empty_controller(self):
        class RootController(object):
            def __call__(self, environ, start_response):
                return None

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app(global_conf={'debug':True})
        app = TestApp(app)

        r = app.get('/something', status=500)
        assert 'No content returned by controller' in r

    def test_application_test_mode_detection(self):
        class FakeRegistry(object):
            def register(self, *args, **kw):
                pass

        a = TGApp()
        testmode, __ = a.setup_app_env({'paste.registry':FakeRegistry()})
        assert testmode is False

        testmode, __ = a.setup_app_env({'paste.registry':FakeRegistry(),
                                        'paste.testing_variables':{}})
        assert testmode is True

    def test_application_no_controller_hijacking(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        class AppWrapper(object):
            def __init__(self, dispatcher):
                self.dispatcher = dispatcher
            def __call__(self, controller, environ, start_response):
                return self.dispatcher(None, environ, start_response)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.application_wrappers.append(AppWrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test', status=404)

    def test_package_no_app_globals(self):
        class RootController(TGController):
            pass

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = sys.modules[__name__]

        app = conf.make_wsgi_app()

    def test_custom_error_document(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                abort(403)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.handle_error_page = True
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' in resp, resp

    def test_custom_error_document_with_streamed_response(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                response.status_code = 403
                def _output():
                    yield 'Hi'
                    yield 'World'
                return _output()

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.handle_error_page = True
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' in resp, resp

    def test_errorware_configuration(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HI'

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app(global_conf={'trace_errors.error_email': 'test@domain.com'},
                                 full_stack=True)
        app = TestApp(app)

        resp = app.get('/test')
        assert 'HI' in resp, resp

        assert config['tg.errorware']['error_email'] == 'test@domain.com'
        assert config['tg.errorware']['error_subject_prefix'] == 'WebApp Error: '
        assert config['tg.errorware']['error_message'] == 'An internal server error occurred'

    def test_tw2_unsupported_renderer(self):
        import tw2.core

        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                rl = tw2.core.core.request_local()
                tw2conf = rl['middleware'].config
                return ','.join(tw2conf.preferred_rendering_engines)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.prefer_toscawidgets2 = True
        conf.renderers = ['kajiki', 'genshi']
        conf.default_renderer = 'kajiki'

        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test')
        assert 'genshi' in resp, resp

    def test_tw2_renderers_preference(self):
        import tw2.core

        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                rl = tw2.core.core.request_local()
                tw2conf = rl['middleware'].config
                return ','.join(tw2conf.preferred_rendering_engines)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.prefer_toscawidgets2 = True
        conf.renderers = ['genshi']
        conf.default_renderer = 'genshi'

        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test')
        assert 'genshi' in resp, resp

    def test_tw2_unsupported(self):
        import tw2.core

        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                rl = tw2.core.core.request_local()
                tw2conf = rl['middleware'].config
                return ','.join(tw2conf.preferred_rendering_engines)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.prefer_toscawidgets2 = True
        conf.renderers = ['kajiki']
        conf.default_renderer = 'kajiki'

        try:
            app = conf.make_wsgi_app(full_stack=True)
            assert False
        except TGConfigError as e:
            assert 'None of the configured rendering engines is supported' in str(e)

    def test_backward_compatible_engine_failed_setup(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HELLO'

        def setup_broken_renderer():
            return False

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.setup_broken_renderer = setup_broken_renderer
        conf.renderers = ['json', 'broken']

        app = conf.make_wsgi_app(full_stack=True)
        assert conf.renderers == ['json']

    def test_backward_compatible_engine_success_setup(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HELLO'

        conf = AppConfig(minimal=True, root_controller=RootController())

        def setup_broken_renderer():
            conf.render_functions.broken = 'BROKEN'
            return True

        conf.setup_broken_renderer = setup_broken_renderer
        conf.renderers = ['json', 'broken']

        app = conf.make_wsgi_app(full_stack=True)
        assert conf.renderers == ['json', 'broken']
        assert conf.render_functions.broken == 'BROKEN'

    def test_render_factory_success(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HELLO'

        class FailedFactory(RendererFactory):
            engines = {'broken': {'content_type': 'text/plain'}}

            @classmethod
            def create(cls, config, app_globals):
                return {'broken': 'BROKEN'}

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_rendering_engine(FailedFactory)
        conf.renderers = ['json', 'broken']

        app = conf.make_wsgi_app(full_stack=True)
        assert conf.renderers == ['json', 'broken']
        assert conf.render_functions.broken == 'BROKEN'

    def test_render_factory_failure(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HELLO'

        class FailedFactory(RendererFactory):
            engines = {'broken': {'content_type': 'text/plain'}}

            @classmethod
            def create(cls, config, app_globals):
                return None

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_rendering_engine(FailedFactory)
        conf.renderers = ['json', 'broken']

        app = conf.make_wsgi_app(full_stack=True)
        assert conf.renderers == ['json']


########NEW FILE########
__FILENAME__ = test_config_milestones
from tg.configuration.milestones import _ConfigMilestoneTracker


class Action:
    called = 0
    def __call__(self):
        self.called += 1


class TestMilestones(object):
    def setup(self):
        self.milestone = _ConfigMilestoneTracker('test_milestone')

    def test_multiple_registration(self):
        a = Action()
        self.milestone.register(a)
        self.milestone.register(a)
        self.milestone.register(a)

        self.milestone.reach()
        assert a.called == 1

    def test_register_after_reach(self):
        a = Action()

        self.milestone.reach()
        self.milestone.register(a)
        assert a.called == 1

    def test_call_all(self):
        a = Action()
        a2 = Action()
        a3 = Action()

        self.milestone.register(a)
        self.milestone.register(a2)
        self.milestone.register(a3)

        self.milestone.reach()
        assert a.called == a2.called == a3.called == 1

    def test_register_func_unique(self):
        called = []
        def f():
            called.append(True)

        self.milestone.register(f)
        self.milestone.register(f)

        self.milestone.reach()
        assert len(called) == 1




########NEW FILE########
__FILENAME__ = test_controllers
# -*- coding: utf-8 -*-
import tg
from tg.controllers import *
from tg.exceptions import HTTPFound
from nose.tools import eq_
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request
from tg.util import no_warn
from tg._compat import u_, string_type

def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

def test_create_request():
    environ = { 'SCRIPT_NAME' : '/xxx' }
    request = create_request('/', environ)
    eq_('http://localhost/xxx/hello', tg.request.relative_url('hello'))
    eq_('http://localhost/xxx', tg.request.application_url)

def test_approots():
    create_request('/subthing/',{ 'SCRIPT_NAME' : '/subthing' })
    eq_("foo", url("foo"))
    eq_("/subthing/foo", url("/foo"))

def test_lowerapproots():
    create_request(
                '/subthing/subsubthing/',
                { 'SCRIPT_NAME' : '/subthing/subsubthing' }
                )
    eq_("/subthing/subsubthing/foo", url("/foo"))

@no_warn
def test_multi_values():
    create_request('/')
    r = url("/foo", params=dict(bar=("asdf", "qwer")))
    assert r in \
            ["/foo?bar=qwer&bar=asdf", "/foo?bar=asdf&bar=qwer"], r
    r = url("/foo", params=dict(bar=[1,2]))
    assert  r in \
            ["/foo?bar=1&bar=2", "/foo?bar=2&bar=1"], r

@no_warn
def test_unicode():
    """url() can handle unicode parameters"""
    create_request("/")
    unicodestring =  u_('àèìòù')
    eq_(url('/', params=dict(x=unicodestring)),
        '/?x=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'
        )
@no_warn
def test_list():
    """url() can handle list parameters, with unicode too"""
    create_request("/")
    value = url('/', params=dict(foo=['bar', u_('à')])),
    assert '/?foo=bar&foo=%C3%A0' in value, value

@no_warn
def test_url_positional_params():
    params = {'spamm': 'eggs'}
    result = url('/foo', params)
    assert 'spamm=eggs' in result

def test_url_with_params_key():
    params = {'spamm': 'eggs'}
    result = url('/foo', params=params)
    assert 'spamm=eggs' in result

@no_warn
def test_url_strip_None():
    params = {'spamm':'eggs', 'hamm':None }
    result = url('/foo', params=params)
    assert 'hamm' not in result, result

def test_lurl():
    params = {'spamm':'eggs', 'hamm':None }
    assert url('/foo', params=params) == str(lurl('/foo', params=params))

@no_warn
def test_url_qualified():
    """url() can handle list parameters, with unicode too"""
    create_request("/")
    value = url('/', qualified=True)
    assert value.startswith('http')

@no_warn
def test_lurl():
    """url() can handle list parameters, with unicode too"""
    create_request("/")
    value = lurl('/lurl')
    assert not isinstance(value, string_type)
    assert value.startswith('/lurl')
    assert str(value) == repr(value) == value.id == value.encode('utf-8').decode('utf-8') == value.__html__()

def test_lurl_as_HTTPFound_location():
    create_request('/')
    exc = HTTPFound(location=lurl('/lurl'))

    def _fake_start_response(*args, **kw):
        pass

    resp = exc({'PATH_INFO':'/',
                'wsgi.url_scheme': 'HTTP',
                'REQUEST_METHOD': 'GET',
                'SERVER_NAME': 'localhost',
                'SERVER_PORT': '80'}, _fake_start_response)
    assert b'resource was found at http://localhost:80/lurl' in resp[0]

def test_HTTPFound_without_location():
    exc = HTTPFound(add_slash=True)
 
    def _fake_start_response(*args, **kw):
        pass

    resp = exc({'PATH_INFO':'/here',
                'wsgi.url_scheme': 'HTTP',
                'REQUEST_METHOD': 'GET',
                'SERVER_NAME': 'localhost',
                'SERVER_PORT': '80'}, _fake_start_response)
    assert b'resource was found at http://localhost:80/here/' in resp[0]

@no_warn
def test_lurl_format():
    """url() can handle list parameters, with unicode too"""
    create_request("/")
    value = lurl('/lurl/{0}')
    value = value.format('suburl')
    assert value == '/lurl/suburl', value

@no_warn
def test_lurl_add():
    """url() can handle list parameters, with unicode too"""
    create_request("/")
    value = lurl('/lurl')
    value = value + '/suburl'
    assert value == '/lurl/suburl', value

@no_warn
def test_lurl_radd():
    """url() can handle list parameters, with unicode too"""
    create_request("/")
    value = lurl('/lurl')
    value = '/suburl' + value
    assert value == '/suburl/lurl', value

########NEW FILE########
__FILENAME__ = test_converters
from nose.tools import raises
from tg.support.converters import asbool, asint, aslist

class TestAsBool(object):
    def test_asbool_truthy(self):
        assert asbool('true')
        assert asbool('yes')
        assert asbool('on')
        assert asbool('y')
        assert asbool('t')
        assert asbool('1')

    def test_asbool_falsy(self):
        assert not asbool('false')
        assert not asbool('no')
        assert not asbool('off')
        assert not asbool('n')
        assert not asbool('f')
        assert not asbool('0')

    @raises(ValueError)
    def test_asbool_broken(self):
        asbool('Test')

    @raises(ValueError)
    def test_nonstring(self):
        asint([True])


class TestAsInt(object):
    def test_fine(self):
        assert asint('55') == 55

    @raises(ValueError)
    def test_nan(self):
        asint('hello')

    @raises(ValueError)
    def test_nonstring(self):
        asint(['55'])


class TestAsList(object):
    def test_fine(self):
        assert aslist('first,   second, third', ',') == ['first', 'second', 'third']
        assert aslist('first second     third') == ['first', 'second', 'third']
        assert aslist('first,   second, third', ',', False) == ['first', '   second', ' third']

    def test_nonstring(self):
        assert aslist(55) == [55]

    def test_already_list(self):
        assert aslist([55]) == [55]

    def test_None(self):
        assert aslist(None) == []
########NEW FILE########
__FILENAME__ = test_errorware
from tg.error import ErrorReporter


def simple_app(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    return ['HELLO']


class TestErrorReporterConfig(object):
    def test_disable_all(self):
        app = ErrorReporter(simple_app, {})
        reporters = [r.__class__.__name__ for r in app.reporters]
        assert 'EmailReporter' not in reporters
        assert 'SentryReporter' not in reporters

    def test_enable_email(self):
        app = ErrorReporter(simple_app, {}, error_email='user@somedomain.com')
        reporters = [r.__class__.__name__ for r in app.reporters]
        assert 'EmailReporter' in reporters

    def test_enable_sentry(self):
        app = ErrorReporter(simple_app, {}, sentry_dsn='http://public:secret@example.com/1')
        reporters = [r.__class__.__name__ for r in app.reporters]
        assert 'SentryReporter' in reporters

########NEW FILE########
__FILENAME__ = test_fastform
from webob.exc import HTTPFound, HTTPUnauthorized
from tg.configuration.auth.fastform import FastFormPlugin

class FakeCookieAuth(object):
    def remember(self, *args, **kw):
        return 'REMEMBER'

    def forget(self, *args, **kw):
        return 'FORGET'

def build_env(path_info, qs='', SCRIPT_NAME=''):
    environ = {
        'PATH_INFO': path_info,
        'SCRIPT_NAME': SCRIPT_NAME,
        'QUERY_STRING': qs,
        'SERVER_NAME': 'example.org',
        'SERVER_PORT': '80',
        'wsgi.input': '',
        'wsgi.url_scheme': 'http',
        'CONTENT_TYPE': "application/x-www-form-urlencoded",
        }

    environ['repoze.who.plugins'] = {'cookie': FakeCookieAuth()}

    return environ


class TestFastFormPlugin(object):
    def setup(self):
        self.fform = FastFormPlugin('/login', '/login_handler', '/post_login', '/logout_handler',
                                    '/post_logout', 'cookie')

    def test_login(self):
        env = build_env('/login_handler', 'login=user&password=pwd&came_from=/goback')
        cred = self.fform.identify(env)

        assert isinstance(env['repoze.who.application'], HTTPFound)
        assert cred['login'] == 'user'
        assert cred['password'] == 'pwd'
        assert env['repoze.who.application'].location == '/post_login?came_from=%2Fgoback'

    def test_login_nocred(self):
        env = build_env('/login_handler', 'login=user&came_from=/goback')
        cred = self.fform.identify(env)
        assert cred is None

    def test_login_counter(self):
        env = build_env('/login_handler', 'login=user&password=pwd&__logins=1')
        cred = self.fform.identify(env)

        assert isinstance(env['repoze.who.application'], HTTPFound)
        assert cred['login'] == 'user'
        assert cred['password'] == 'pwd'
        assert env['repoze.who.application'].location == '/post_login?__logins=1'

    def test_login_counter_keep(self):
        env = build_env('/login', '__logins=1')
        self.fform.identify(env)

        assert 'logins' not in env['QUERY_STRING']
        assert env['repoze.who.logins'] == 1

    def test_logout_handler(self):
        env = build_env('/logout_handler', 'came_from=%2Fgoback')
        self.fform.identify(env)

        assert isinstance(env['repoze.who.application'], HTTPUnauthorized)
        assert env['came_from'] == '/goback'

    def test_logout_handler_no_came_from(self):
        env = build_env('/logout_handler')
        self.fform.identify(env)

        assert isinstance(env['repoze.who.application'], HTTPUnauthorized)
        assert env['came_from'] == '/'

    def test_logout_handler_challenge(self):
        env = build_env('/logout_handler', 'came_from=%2Fgoback')
        self.fform.identify(env)
        ans = self.fform.challenge(env, '401 Unauthorized', [('app', '1')], [('forget', '1')])

        assert isinstance(ans, HTTPFound)
        assert ans.location == '/post_logout?came_from=%2Fgoback'

    def test_challenge_redirect_to_form(self):
        env = build_env('/private', SCRIPT_NAME='/SOMEWHERE')
        ans = self.fform.challenge(env, '401 Unauthorized', [('app', '1')], [('forget', '1')])

        assert isinstance(ans, HTTPFound)
        assert ans.location == '/SOMEWHERE/login?came_from=%2FSOMEWHERE%2Fprivate'

    def test_challenge_redirect_to_form_with_args(self):
        env = build_env('/private', qs='A=1&B=2', SCRIPT_NAME='/SOMEWHERE')
        ans = self.fform.challenge(env, '401 Unauthorized', [('app', '1')], [('forget', '1')])

        assert isinstance(ans, HTTPFound)

        # Cope with different dictionary ordering on Py2 and Py3
        assert ans.location in ('/SOMEWHERE/login?came_from=%2FSOMEWHERE%2Fprivate%3FA%3D1%26B%3D2',
                                '/SOMEWHERE/login?came_from=%2FSOMEWHERE%2Fprivate%3FB%3D2%26A%3D1'), ans.location

    def test_remember_forget(self):
        env = build_env('/private', SCRIPT_NAME='/SOMEWHERE')
        assert self.fform.remember(env, {}) == 'REMEMBER'
        assert self.fform.forget(env, {}) == 'FORGET'

    def test_repr(self):
        assert repr(self.fform).startswith('<FastFormPlugin:/login_handler')

########NEW FILE########
__FILENAME__ = test_generic_json
from tg.jsonify import jsonify, encode
from datetime import date

from json import loads

class Person(object):
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name
    
    @property
    def name(self):
        return '%s %s' % (self.first_name, self.last_name)
    
    def __json__(self):
        return dict(first_name=self.first_name, last_name=self.last_name)

def test_simple_rule():    
    # skip this test if simplegeneric is not installed
    try:
        import simplegeneric
    except ImportError:
        return
    
    # create a Person instance
    p = Person('Jonathan', 'LaCour')
    
    # encode the object using the existing "default" rules
    result = loads(encode(p))
    assert result['first_name'] == 'Jonathan'
    assert result['last_name'] == 'LaCour'
    assert len(result) == 2
    
    # register a generic JSON rule
    @jsonify.when_type(Person)
    def jsonify_person(obj):
        return dict(
            name=obj.name
        )
    
    # encode the object using our new rule
    result = loads(encode(p))
    assert result['name'] == 'Jonathan LaCour'
    assert len(result) == 1

def test_builtin_override():
    # skip this test if simplegeneric is not installed
    try:
        import simplegeneric
    except ImportError:
        return
    
    # create a few date objects
    d1 = date(1979, 10, 12)
    d2 = date(2000, 1, 1)
    d3 = date(2012, 1, 1)
    
    # jsonify using the built in rules
    result1 = encode(dict(date=d1))
    assert '"1979-10-12"' in result1
    result2 = encode(dict(date=d2))
    assert '"2000-01-01"' in result2
    result3 = encode(dict(date=d3))
    assert '"2012-01-01"' in result3
    
    # create a custom rule
    @jsonify.when_type(date)
    def jsonify_date(obj):
        if obj.year == 1979 and obj.month == 10 and obj.day == 12:
            return "Jon's Birthday!"
        elif obj.year == 2000 and obj.month == 1 and obj.day == 1:
            return "Its Y2K! Panic!"
        return '%d/%d/%d' % (obj.month, obj.day, obj.year)
    
    # jsonify using the built in rules
    result1 = encode(dict(date=d1))
    assert '"Jon\'s Birthday!"' in result1
    result2 = encode(dict(date=d2))
    assert '"Its Y2K! Panic!"' in result2
    result3 = encode(dict(date=d3))
    assert  '"1/1/2012"' in result3

########NEW FILE########
__FILENAME__ = test_i18n
# -*- coding: utf-8 -*-
from nose.tools import raises
from webtest import TestApp
import gettext as _gettext

import tg
from tg import i18n, expose, TGController, config
from tg.configuration import AppConfig

from tg._compat import unicode_text, u_

class _FakePackage:
    __name__ = 'tests'
    __file__ = __file__

    class lib:
        class app_globals:
            class Globals:
                pass
_FakePackage.__name__ = 'tests'

class TestSanitizeLanguage():
    def test_sanitize_language_code(self):
        """Check that slightly malformed language codes can be corrected."""
        for lang in 'pt', 'PT':
            assert i18n.sanitize_language_code(lang) == 'pt'
        for lang in 'pt-br', 'pt_br', 'pt_BR':
            assert i18n.sanitize_language_code(lang) == 'pt_BR'
        for lang in 'foo', 'bar', 'foo-bar':
            assert i18n.sanitize_language_code(lang) == lang

    def test_sanitize_language_code_charset(self):
        assert i18n.sanitize_language_code('en_US.UTF-8') == 'en_US'

    def test_sanitize_language_code_modifier(self):
        assert i18n.sanitize_language_code('it_IT@euro') == 'it_IT'

    def test_sanitize_language_code_charset_and_modifier(self):
        assert i18n.sanitize_language_code('de_DE.iso885915@euro') == 'de_DE'

    def test_sanitize_language_code_territory_script_variant(self):
        assert i18n.sanitize_language_code('zh_Hans_CN') == 'zh_CN'

    def test_sanitize_language_code_numeric(self):
        assert i18n.sanitize_language_code('es-419') == 'es_419'

    def test_sanitize_language_code_numeric_variant(self):
        assert i18n.sanitize_language_code('de-CH-1996') == 'de_CH'

def test_formencode_gettext_nulltranslation():
    prev_gettext = i18n.ugettext
    def nop_gettext(v):
        return v

    i18n.ugettext = nop_gettext
    assert i18n._formencode_gettext('something') == 'something'
    i18n.ugettext = prev_gettext
    return 'OK'

@raises(i18n.LanguageError)
def test_get_unaccessible_translator():
    def _fake_find(*args, **kwargs):
        return '/fake_file'

    real_find = _gettext.find
    _gettext.find = _fake_find
    try:
        i18n._get_translator(['de'], tg_config={'localedir': '',
                                                'package': _FakePackage()})
    finally:
        _gettext.find = real_find

class i18nRootController(TGController):
    def _before(self, *args, **kw):
        if not tg.request.GET.get('skip_lang'):
            forced_lang = tg.request.GET.get('force_lang', 'de')
            forced_lang = forced_lang.split(',')
            i18n.set_temporary_lang(forced_lang)

        if tg.request.GET.get('fallback'):
            i18n.add_fallback(tg.request.GET.get('fallback'),
                              fallback=tg.request.GET.get('fallback-fallback', False))

    @expose('json')
    def lazy_hello(self, **kw):
        return dict(text=unicode_text(i18n.lazy_ugettext('Your application is now running')))

    @expose('json')
    def get_lang(self, **kw):
        return dict(lang=i18n.get_lang())

    @expose('json')
    def get_supported_lang(self, **kw):
        return dict(lang=i18n.get_lang(all=False))

    @expose('json')
    def hello(self, **kw):
        return dict(text=unicode_text(i18n.ugettext('Your application is now running')))

    @expose()
    def fallback(self, **kw):
        return i18n.ugettext('This is a fallback')

    @expose('json')
    def hello_plural(self):
        return dict(text=i18n.ungettext('Your application is now running',
                                        'Your applications are now running',
                                        2))

    @expose()
    def force_german(self, **kw):
        i18n.set_lang('de')
        return 'OK'


class TestI18NStack(object):
    def setup(self):
        conf = AppConfig(minimal=True, root_controller=i18nRootController())
        conf['paths']['root'] = 'tests'
        conf['i18n_enabled'] = True
        conf['use_sessions'] = True
        conf['beaker.session.key'] = 'tg_test_session'
        conf['beaker.session.secret'] = 'this-is-some-secret'
        conf.renderers = ['json']
        conf.default_renderer = 'json'
        conf.package = _FakePackage()
        app = conf.make_wsgi_app()
        self.app = TestApp(app)

    def teardown(self):
        config.pop('tg.root_controller')

    def test_lazy_gettext(self):
        r = self.app.get('/lazy_hello')
        assert 'Ihre Anwendung' in r

    def test_plural_gettext(self):
        r = self.app.get('/hello_plural')
        assert 'Your applications' in r, r

    def test_get_lang(self):
        r = self.app.get('/get_lang?skip_lang=1')
        assert '[]' in r, r.body

    def test_gettext_default_lang(self):
        r = self.app.get('/hello?skip_lang=1')
        assert 'Your application' in r, r

    def test_gettext_nop(self):
        k = 'HELLO'
        assert i18n.gettext_noop(k) is k

    def test_null_translator(self):
        assert i18n._get_translator(None).gettext('Hello') == 'Hello'

    def test_get_lang_nonexisting_lang(self):
        r = self.app.get('/get_lang?force_lang=fa')
        assert 'fa' in r, r

    def test_get_lang_existing(self):
        r = self.app.get('/get_lang?force_lang=de')
        assert 'de' in r, r

    def test_fallback(self):
        r = self.app.get('/fallback?force_lang=it&fallback=de')
        assert 'Dies ist' in r, r

    @raises(i18n.LanguageError)
    def test_fallback_non_existing(self):
        r = self.app.get('/fallback?force_lang=it&fallback=ko')

    def test_fallback_fallback(self):
        r = self.app.get('/fallback?force_lang=it&fallback=ko&fallback-fallback=true')
        assert 'This is a fallback' in r, r

    def test_get_lang_supported(self):
        r = self.app.get('/get_supported_lang?force_lang=it,ru,fa,de')
        langs = r.json['lang']
        assert langs == ['ru', 'de'], langs

    def test_get_lang_supported_without_lang(self):
        r = self.app.get('/get_supported_lang?skip_lang=1')
        langs = r.json['lang']
        assert langs == [], langs

    def test_force_lang(self):
        r = self.app.get('/get_lang?skip_lang=1')
        assert '[]' in r, r.body

        r = self.app.get('/force_german?skip_lang=1')
        assert 'tg_test_session' in r.headers.get('Set-cookie')

        cookie_value = r.headers.get('Set-cookie')
        r = self.app.get('/get_lang?skip_lang=1', headers={'Cookie':cookie_value})
        assert 'de' in r

    def test_get_lang_no_session(self):
        r = self.app.get('/get_lang?skip_lang=1', extra_environ={})
        assert '[]' in r, r.body

########NEW FILE########
__FILENAME__ = test_jsonify
from tg import jsonify, lurl
from datetime import datetime
from decimal import Decimal
from nose.tools import raises
from nose import SkipTest
from webob.multidict import MultiDict
import json

class Foo(object):
    def __init__(self, bar):
        self.bar = bar

class Bar(object):
    def __init__(self, bar):
        self.bar = bar
    def __json__(self):
        return 'bar-%s' % self.bar

class Baz(object):
    pass

def test_string():
    d = "string"
    encoded = jsonify.encode(d)
    assert encoded == '"string"'

@raises(jsonify.JsonEncodeError)
def test_list():
    d = ['a', 1, 'b', 2]
    encoded = jsonify.encode(d)
    assert encoded == '["a", 1, "b", 2]'

@raises(jsonify.JsonEncodeError)
def test_list_iter():
    d = list(range(3))
    encoded = jsonify.encode_iter(d)
    assert ''.join(jsonify.encode_iter(d)) == jsonify.encode(d)

def test_dictionary():
    d = {'a': 1, 'b': 2}
    encoded = jsonify.encode(d)
    expected = json.dumps(json.loads('{"a": 1, "b": 2}'))
    assert encoded == expected

@raises(jsonify.JsonEncodeError)
def test_nospecificjson():
    b = Baz()
    try:
        encoded = jsonify.encode(b)
    except TypeError as e:
        pass
    assert  "is not JSON serializable" in e.message 

def test_exlicitjson():
    b = Bar("bq")
    encoded = jsonify.encode(b)
    assert encoded == '"bar-bq"'

@raises(jsonify.JsonEncodeError)
def test_exlicitjson_in_list():
    b = Bar("bq")
    d = [b]
    encoded = jsonify.encode(d)
    assert encoded == '["bar-bq"]'

def test_exlicitjson_in_dict():
    b = Bar("bq")
    d = {"b": b}
    encoded = jsonify.encode(d)
    assert encoded == '{"b": "bar-bq"}'

def test_datetime():
    d = datetime.utcnow()
    encoded = jsonify.encode({'date':d})
    assert str(d.year) in encoded, (str(d), encoded)

def test_decimal():
    d = Decimal('3.14')
    encoded = jsonify.encode({'dec':d})
    assert '3.14' in encoded

def test_objectid():
    try:
        from bson import ObjectId
    except:
        raise SkipTest()

    d = ObjectId('507f1f77bcf86cd799439011')
    encoded = jsonify.encode({'oid':d})
    assert encoded == '{"oid": "%s"}' % d, encoded

def test_multidict():
    d = MultiDict({'v':1})
    encoded = jsonify.encode({'md':d})
    assert encoded == '{"md": {"v": 1}}', encoded

def test_json_encode_lazy_url():
    url = lurl('/test')
    encoded = jsonify.encode({'url': url})
    assert encoded == '{"url": "/test"}', encoded

def test_json_encode_generators():
    encoded = jsonify.encode({'values': (v for v in [1, 2, 3])})
    assert encoded == '{"values": [1, 2, 3]}', encoded
########NEW FILE########
__FILENAME__ = test_jsonify_sqlalchemy
from nose.tools import raises
from tg import jsonify
import json

try:
    try:
        import sqlite3
    except:
        import pysqlite2
    from sqlalchemy import (MetaData, Table, Column, ForeignKey,
        Integer, String)
    from sqlalchemy.orm import create_session, mapper, relation

    metadata = MetaData('sqlite:///:memory:')

    test1 = Table('test1', metadata,
        Column('id', Integer, primary_key=True),
        Column('val', String(8)))

    test2 = Table('test2', metadata,
        Column('id', Integer, primary_key=True),
        Column('test1id', Integer, ForeignKey('test1.id')),
        Column('val', String(8)))

    test3 = Table('test3', metadata,
        Column('id', Integer, primary_key=True),
        Column('val', String(8)))

    test4 = Table('test4', metadata,
        Column('id', Integer, primary_key=True),
        Column('val', String(8)))

    metadata.create_all()

    class Test2(object):
        pass
    mapper(Test2, test2)

    class Test1(object):
        pass
    mapper(Test1, test1, properties={'test2s': relation(Test2)})

    class Test3(object):
        def __json__(self):
            return {'id': self.id, 'val': self.val, 'customized': True}

    mapper(Test3, test3)

    class Test4(object):
        pass
    mapper(Test4, test4)

    test1.insert().execute({'id': 1, 'val': 'bob'})
    test2.insert().execute({'id': 1, 'test1id': 1, 'val': 'fred'})
    test2.insert().execute({'id': 2, 'test1id': 1, 'val': 'alice'})
    test3.insert().execute({'id': 1, 'val': 'bob'})
    test4.insert().execute({'id': 1, 'val': 'alberto'})

except ImportError:
    from warnings import warn
    warn('SQLAlchemy or PySqlite not installed - cannot run these tests.')

else:

    def test_saobj():
        s = create_session()
        t = s.query(Test1).get(1)
        encoded = jsonify.encode(t)
        expected = json.loads('{"id": 1, "val": "bob"}')
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_salist():
        s = create_session()
        t = s.query(Test1).get(1)
        encoded = jsonify.encode(dict(results=t.test2s))
        expected = json.loads('''{"results": [{"test1id": 1, "id": 1, "val": "fred"}, {"test1id": 1, "id": 2, "val": "alice"}]}''')
        result = json.loads(encoded)
        assert result == expected, encoded
        
    def test_select_row():
        s = create_session()
        t = test1.select().execute()
        encoded = jsonify.encode(dict(results=t))
        expected = json.loads("""{"results": {"count": -1, "rows": [{"count": 1, "rows": {"id": 1, "val": "bob"}}]}}""")
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_select_rows():
        s = create_session()
        t = test2.select().execute()
        encoded = jsonify.encode(dict(results=t))
        expected = json.loads("""{"results": {"count": -1, "rows": [{"count": 1, "rows": {"test1id": 1, "id": 1, "val": "fred"}}, {"count": 1, "rows": {"test1id": 1, "id": 2, "val": "alice"}}]}}""")
        result = json.loads(encoded)
        assert result == expected, encoded

    def test_explicit_saobj():
        s = create_session()
        t = s.query(Test3).get(1)
        encoded = jsonify.encode(t)
        expected = json.loads('{"id": 1, "val": "bob", "customized": true}')
        result = json.loads(encoded)
        assert result == expected, encoded


########NEW FILE########
__FILENAME__ = test_middlewares
from webtest import TestApp
from tg.support.middlewares import StatusCodeRedirect
from tg.support.middlewares import DBSessionRemoverMiddleware


def FakeApp(environ, start_response):
    if environ['PATH_INFO'].startswith('/error'):
        start_response('403 Forbidden', [])
    else:
        start_response('200 Success', [])

    if environ['PATH_INFO'] == '/error/document':
        yield b'ERROR!!!'
    else:
        yield b'HI'
        yield b'MORE'


class TestStatusCodeRedirectMiddleware(object):
    def setup(self):
        self.app = TestApp(StatusCodeRedirect(FakeApp, [403]))

    def test_error_redirection(self):
        r = self.app.get('/error_test', status=403)
        assert 'ERROR!!!' in r, r

    def test_success_passthrough(self):
        r = self.app.get('/success_test')
        assert 'HI' in r, r


class FakeDBSession(object):
    removed = False

    def remove(self):
        self.removed = True


class FakeAppWithClose(object):
    closed = False
    step = 0

    def __call__(self, environ, start_response):
        start_response('200 Success', [])
        return self

    def __iter__(self):
        return self

    def next(self):
        self.step += 1

        if self.step > 3:
            raise StopIteration()

        return str(self.step)

    def close(self):
        self.closed = True

    def __repr__(self):
        return '%s - %s' % (self.step, self.closed)


class TestDBSessionRemoverMiddleware(object):
    def setup(self):
        self.app_with_close = FakeAppWithClose()
        self.session = FakeDBSession()
        self.app = TestApp(DBSessionRemoverMiddleware(self.session, self.app_with_close))

    def test_close_is_called(self):
        r = self.app.get('/nonerror')
        assert self.app_with_close.closed == True, self.app_with_close

    def test_session_is_removed(self):
        r = self.app.get('/nonerror')
        assert self.session.removed == True, self.app_with_close

########NEW FILE########
__FILENAME__ = test_predicates
# -*- coding: utf-8 -*-
"""Tests for Predicates, mostly took from repoze.what test suite"""

##############################################################################
#
# Copyright (c) 2007, Agendaless Consulting and Contributors.
# Copyright (c) 2008, Florent Aide <florent.aide@gmail.com>.
# Copyright (c) 2008-2009, Gustavo Narea <me@gustavonarea.net>.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from nose.tools import raises
from webtest import TestApp
from tg._compat import u_, unicode_text

from tg import predicates, TGController, expose, config
from tg.configuration import AppConfig

class BasePredicateTester(object):
    """Base test case for predicates."""

    def assertEqual(self, val1, val2):
        assert val1 == val2, (val1, val2)

    def eval_met_predicate(self, p, environ):
        """Evaluate a predicate that should be met"""
        self.assertEqual(p.check_authorization(environ), None)
        self.assertEqual(p.is_met(environ), True)

    def eval_unmet_predicate(self, p, environ, expected_error):
        """Evaluate a predicate that should not be met"""
        credentials = environ.get('repoze.what.credentials')
        # Testing check_authorization
        try:
            p.evaluate(environ, credentials)
            self.fail('Predicate must not be met; expected error: %s' %
                      expected_error)
        except predicates.NotAuthorizedError as error:
            self.assertEqual(unicode_text(error), expected_error)
            # Testing is_met:
        self.assertEqual(p.is_met(environ), False)


#{ The test suite itself


class TestPredicate(BasePredicateTester):

    @raises(NotImplementedError)
    def test_evaluate_isnt_implemented(self):
        p = MockPredicate()
        p.evaluate(None, None)

    def test_message_is_changeable(self):
        previous_msg = EqualsTwo.message
        new_msg = 'It does not equal two!'
        p = EqualsTwo(msg=new_msg)
        self.assertEqual(new_msg, p.message)

    def test_message_isnt_changed_unless_required(self):
        previous_msg = EqualsTwo.message
        p = EqualsTwo()
        self.assertEqual(previous_msg, p.message)

    def test_unicode_messages(self):
        unicode_msg = u_('请登陆')
        p = EqualsTwo(msg=unicode_msg)
        environ = {'test_number': 3}
        self.eval_unmet_predicate(p, environ, unicode_msg)

    def test_authorized(self):
        environ = {'test_number': 4}
        p = EqualsFour()
        p.check_authorization(environ)

    def test_unauthorized(self):
        environ = {'test_number': 3}
        p = EqualsFour(msg="Go away!")
        try:
            p.check_authorization(environ)
            self.fail('Authorization must have been rejected')
        except predicates.NotAuthorizedError as e:
            self.assertEqual(str(e), "Go away!")

    def test_unauthorized_with_unicode_message(self):
        # This test is broken on Python 2.4 and 2.5 because the unicode()
        # function doesn't work when converting an exception into an unicode
        # string (this is, to extract its message).
        unicode_msg = u_('请登陆')
        environ = {'test_number': 3}
        p = EqualsFour(msg=unicode_msg)
        try:
            p.check_authorization(environ)
            self.fail('Authorization must have been rejected')
        except predicates.NotAuthorizedError as e:
            self.assertEqual(unicode_text(e), unicode_msg)

    def test_custom_failure_message(self):
        message = u_('This is a custom message whose id is: %(id_number)s')
        id_number = 23
        p = EqualsFour(msg=message)
        try:
            p.unmet(message, id_number=id_number)
            self.fail('An exception must have been raised')
        except predicates.NotAuthorizedError as e:
            self.assertEqual(unicode_text(e), message % dict(id_number=id_number))

    def test_credentials_dict_when_anonymous(self):
        """The credentials must be a dict even if the user is anonymous"""
        class CredentialsPredicate(predicates.Predicate):
            message = "Some text"
            def evaluate(self, environ, credentials):
                if 'something' in credentials:
                    self.unmet()
            # --- Setting the environ up
        environ = {}
        # --- Testing it:
        p = CredentialsPredicate()
        self.eval_met_predicate(p, environ)
        self.assertEqual(True, p.is_met(environ))

class TestContextRelatedBoolPredicate(BasePredicateTester):
    def setup(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return str(bool(EqualsTwo()))

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app()
        self.app = TestApp(app)

    def teardown(self):
        config.pop('tg.root_controller', None)

    def test_success(self):
        ans = self.app.get('/test', extra_environ={'test_number':'2'})
        assert 'True' in ans, ans

    def test_faillure(self):
        ans = self.app.get('/test', extra_environ={'test_number':'4'})
        assert 'False' in ans, ans

class TestCompoundPredicate(BasePredicateTester):

    def test_one_predicate_works(self):
        p = EqualsTwo()
        cp = predicates.CompoundPredicate(p)
        self.assertEqual(cp.predicates, (p,))

    def test_two_predicates_work(self):
        p1 = EqualsTwo()
        p2 = MockPredicate()
        cp = predicates.CompoundPredicate(p1, p2)
        self.assertEqual(cp.predicates, (p1, p2))


class TestNotPredicate(BasePredicateTester):

    def test_failure(self):
        environ = {'test_number': 4}
        # It must NOT equal 4
        p = predicates.Not(EqualsFour())
        # It equals 4!
        self.eval_unmet_predicate(p, environ, 'The condition must not be met')

    def test_failure_with_custom_message(self):
        environ = {'test_number': 4}
        # It must not equal 4
        p = predicates.Not(EqualsFour(), msg='It must not equal four')
        # It equals 4!
        self.eval_unmet_predicate(p, environ, 'It must not equal four')

    def test_success(self):
        environ = {'test_number': 5}
        # It must not equal 4
        p = predicates.Not(EqualsFour())
        # It doesn't equal 4!
        self.eval_met_predicate(p, environ)


class TestAllPredicate(BasePredicateTester):

    def test_one_true(self):
        environ = {'test_number': 2}
        p = predicates.All(EqualsTwo())
        self.eval_met_predicate(p, environ)

    def test_one_false(self):
        environ = {'test_number': 3}
        p = predicates.All(EqualsTwo())
        self.eval_unmet_predicate(p, environ, "Number 3 doesn't equal 2")

    def test_two_true(self):
        environ = {'test_number': 4}
        p = predicates.All(EqualsFour(), GreaterThan(3))
        self.eval_met_predicate(p, environ)

    def test_two_false(self):
        environ = {'test_number': 1}
        p = predicates.All(EqualsFour(), GreaterThan(3))
        self.eval_unmet_predicate(p, environ, "Number 1 doesn't equal 4")

    def test_two_mixed(self):
        environ = {'test_number': 5}
        p = predicates.All(EqualsFour(), GreaterThan(3))
        self.eval_unmet_predicate(p, environ, "Number 5 doesn't equal 4")


class TestAnyPredicate(BasePredicateTester):

    def test_one_true(self):
        environ = {'test_number': 2}
        p = predicates.Any(EqualsTwo())
        self.eval_met_predicate(p, environ)

    def test_one_false(self):
        environ = {'test_number': 3}
        p = predicates.Any(EqualsTwo())
        self.eval_unmet_predicate(p, environ,
            "At least one of the following predicates must be "
            "met: Number 3 doesn't equal 2")

    def test_two_true(self):
        environ = {'test_number': 4}
        p = predicates.Any(EqualsFour(), GreaterThan(3))
        self.eval_met_predicate(p, environ)

    def test_two_false(self):
        environ = {'test_number': 1}
        p = predicates.Any(EqualsFour(), GreaterThan(3))
        self.eval_unmet_predicate(p, environ,
            "At least one of the following predicates must be "
            "met: Number 1 doesn't equal 4, 1 is not greater "
            "than 3")

    def test_two_mixed(self):
        environ = {'test_number': 5}
        p = predicates.Any(EqualsFour(), GreaterThan(3))
        self.eval_met_predicate(p, environ)


class TestIsUserPredicate(BasePredicateTester):

    def test_user_without_credentials(self):
        environ = {}
        p = predicates.is_user('gustavo')
        self.eval_unmet_predicate(p, environ,
            'The current user must be "gustavo"')

    def test_user_without_userid(self):
        environ = {'repoze.what.credentials': {}}
        p = predicates.is_user('gustavo')
        self.eval_unmet_predicate(p, environ,
            'The current user must be "gustavo"')

    def test_right_user(self):
        environ = make_environ('gustavo')
        p = predicates.is_user('gustavo')
        self.eval_met_predicate(p, environ)

    def test_wrong_user(self):
        environ = make_environ('andreina')
        p = predicates.is_user('gustavo')
        self.eval_unmet_predicate(p, environ,
            'The current user must be "gustavo"')


class TestInGroupPredicate(BasePredicateTester):

    def test_user_belongs_to_group(self):
        environ = make_environ('gustavo', ['developers'])
        p = predicates.in_group('developers')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_belong_to_group(self):
        environ = make_environ('gustavo', ['developers', 'admins'])
        p = predicates.in_group('designers')
        self.eval_unmet_predicate(p, environ,
            'The current user must belong to the group "designers"')


class TestInAllGroupsPredicate(BasePredicateTester):

    def test_user_belongs_to_groups(self):
        environ = make_environ('gustavo', ['developers', 'admins'])
        p = predicates.in_all_groups('developers', 'admins')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_belong_to_groups(self):
        environ = make_environ('gustavo', ['users', 'admins'])
        p = predicates.in_all_groups('developers', 'designers')
        self.eval_unmet_predicate(p, environ,
            'The current user must belong to the group "developers"')

    def test_user_doesnt_belong_to_one_group(self):
        environ = make_environ('gustavo', ['developers'])
        p = predicates.in_all_groups('developers', 'designers')
        self.eval_unmet_predicate(p, environ,
            'The current user must belong to the group "designers"')


class TestInAnyGroupsPredicate(BasePredicateTester):

    def test_user_belongs_to_groups(self):
        environ = make_environ('gustavo', ['developers',' admins'])
        p = predicates.in_any_group('developers', 'admins')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_belong_to_groups(self):
        environ = make_environ('gustavo', ['users', 'admins'])
        p = predicates.in_any_group('developers', 'designers')
        self.eval_unmet_predicate(p, environ,
            'The member must belong to at least one of the '
            'following groups: developers, designers')

    def test_user_doesnt_belong_to_one_group(self):
        environ = make_environ('gustavo', ['designers'])
        p = predicates.in_any_group('developers', 'designers')
        self.eval_met_predicate(p, environ)


class TestIsAnonymousPredicate(BasePredicateTester):

    def test_authenticated_user(self):
        environ = make_environ('gustavo')
        p = predicates.is_anonymous()
        self.eval_unmet_predicate(p, environ,
            'The current user must be anonymous')

    def test_anonymous_user(self):
        environ = {}
        p = predicates.is_anonymous()
        self.eval_met_predicate(p, environ)


class TestNotAnonymousPredicate(BasePredicateTester):

    def test_authenticated_user(self):
        environ = make_environ('gustavo')
        p = predicates.not_anonymous()
        self.eval_met_predicate(p, environ)

    def test_anonymous_user(self):
        environ = {}
        p = predicates.not_anonymous()
        self.eval_unmet_predicate(p, environ,
            'The current user must have been authenticated')


class TestHasPermissionPredicate(BasePredicateTester):

    def test_user_has_permission(self):
        environ = make_environ('gustavo', permissions=['watch-tv'])
        p = predicates.has_permission('watch-tv')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_have_permission(self):
        environ = make_environ('gustavo', permissions=['watch-tv'])
        p = predicates.has_permission('eat')
        self.eval_unmet_predicate(p, environ,
            'The user must have the "eat" permission')


class TestHasAllPermissionsPredicate(BasePredicateTester):

    def test_user_has_all_permissions(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_all_permissions('watch-tv', 'eat')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_have_permissions(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_all_permissions('jump', 'scream')
        self.eval_unmet_predicate(p, environ,
            'The user must have the "jump" permission')

    def test_user_has_one_permission(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_all_permissions('party', 'scream')
        self.eval_unmet_predicate(p, environ,
            'The user must have the "scream" permission')


class TestUserHasAnyPermissionsPredicate(BasePredicateTester):

    def test_user_has_all_permissions(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_any_permission('watch-tv', 'eat')
        self.eval_met_predicate(p, environ)

    def test_user_doesnt_have_all_permissions(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_any_permission('jump', 'scream')
        self.eval_unmet_predicate(p, environ,
            'The user must have at least one of the following '
            'permissions: jump, scream')

    def test_user_has_one_permission(self):
        environ = make_environ('gustavo', permissions=['watch-tv', 'party',
                                                       'eat'])
        p = predicates.has_any_permission('party', 'scream')
        self.eval_met_predicate(p, environ)


#{ Test utilities


def make_environ(user, groups=None, permissions=None):
    """Make a WSGI enviroment with the credentials dict"""
    credentials = {'repoze.what.userid': user}
    credentials['groups'] = groups or []
    credentials['permissions'] = permissions or []
    environ = {'repoze.what.credentials': credentials}
    return environ


#{ Mock definitions


class MockPredicate(predicates.Predicate):
    message = "I'm a fake predicate"

class EqualsTwo(predicates.Predicate):
    message = "Number %(number)s doesn't equal 2"

    def evaluate(self, environ, credentials):
        number = environ.get('test_number')
        if not number or int(number) != 2:
            self.unmet(number=number)


class EqualsFour(predicates.Predicate):
    message = "Number %(number)s doesn't equal 4"

    def evaluate(self, environ, credentials):
        number = environ.get('test_number')
        if number == 4:
            return
        self.unmet(number=number)


class GreaterThan(predicates.Predicate):
    message = "%(number)s is not greater than %(compared_number)s"

    def __init__(self, compared_number, **kwargs):
        super(GreaterThan, self).__init__(**kwargs)
        self.compared_number = compared_number

    def evaluate(self, environ, credentials):
        number = environ.get('test_number')
        if not number > self.compared_number:
            self.unmet(number=number, compared_number=self.compared_number)


class LessThan(predicates.Predicate):
    message = "%(number)s must be less than %(compared_number)s"

    def __init__(self, compared_number, **kwargs):
        super(LessThan, self).__init__(**kwargs)
        self.compared_number = compared_number

    def evaluate(self, environ, credentials):
        number = environ.get('test_number')
        if not number < self.compared_number:
            self.unmet(number=number, compared_number=self.compared_number)


########NEW FILE########
__FILENAME__ = test_render
"""
Testing for TG2 Configuration
"""
from nose.tools import raises
from nose import SkipTest

import tg
from tg.render import MissingRendererError
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request

from tg.configuration import AppConfig
from mako.exceptions import TemplateLookupException

def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

class FakePackage:
    __name__ = 'tests'
    __file__ = __file__

    class lib:
        class app_globals:
            class Globals:
                pass

@raises(MissingRendererError)
def test_render_missing_renderer():
    conf = AppConfig(minimal=True)
    app = conf.make_wsgi_app()

    tg.render_template({}, 'gensh')

def test_jinja_lookup_nonexisting_template():
    conf = AppConfig(minimal=True)
    conf.use_dotted_templatenames = True
    conf.renderers.append('jinja')
    conf.package = FakePackage()
    app = conf.make_wsgi_app()

    from jinja2 import TemplateNotFound
    try:
        render_jinja = conf.render_functions['jinja']
        render_jinja('tg.this_template_does_not_exists',
                     {'app_globals':tg.config['tg.app_globals']})
        assert False
    except TemplateNotFound:
        pass

class TestMakoLookup(object):
    def setup(self):
        conf = AppConfig(minimal=True)
        conf.use_dotted_templatenames = True
        conf.renderers.append('mako')
        conf.package = FakePackage()
        self.conf = conf
        self.app = conf.make_wsgi_app()

    def test_adjust_uri(self):
        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader

        assert mlookup.adjust_uri('this_template_should_pass_unaltered', None) == 'this_template_should_pass_unaltered'

        dotted_test = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        assert dotted_test.endswith('tests/test_stack/rendering/templates/mako_inherits_local.mak')

        dotted_test = mlookup.adjust_uri('local:test_stack.rendering.templates.mako_inherits_local', None)
        assert dotted_test.endswith('tests/test_stack/rendering/templates/mako_inherits_local.mak')

    def test_local_lookup(self):
        render_mako = self.conf.render_functions['mako']
        res = render_mako('tests.test_stack.rendering.templates.mako_inherits_local',
                          {'app_globals':tg.config['tg.app_globals']})
        assert 'inherited mako page' in res

    def test_passthrough_text_literal__check(self):
        from mako.template import Template
        t = Template('Hi')

        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader
        mlookup.template_cache['hi_template'] = t
        assert mlookup.get_template('hi_template') is t

    @raises(TemplateLookupException)
    def test__check_not_existing_anymore(self):
        from mako.template import Template
        t = Template('Hi', filename='deleted_template.mak')

        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader
        mlookup.template_cache['deleted_template'] = t
        mlookup.get_template('deleted_template')

    @raises(IOError)
    def test_never_existed(self):
        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader

        mlookup.get_template('deleted_template')

    def test__check_should_reload_on_cache_expire(self):
        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader

        template_path = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        t = mlookup.get_template(template_path) #cache the template
        t.output_encoding = 'FAKE_ENCODING'

        t = mlookup.get_template(template_path)
        assert t.output_encoding == 'FAKE_ENCODING'

        import os, stat
        def fake_os_stat(o):
            return {stat.ST_MTIME:t.module._modified_time+1}

        old_stat = os.stat
        os.stat = fake_os_stat
        try:
            t = mlookup.get_template(template_path)
            #if the template got reloaded should not have our fake encoding anymore
            assert t.output_encoding != 'FAKE_ENCODING'
        finally:
            os.stat = old_stat

    def test__check_should_not_reload_when_disabled(self):
        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader
        mlookup.auto_reload = False

        template_path = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        t = mlookup.get_template(template_path) #cache the template
        t.output_encoding = 'FAKE_ENCODING'

        t = mlookup.get_template(template_path)
        assert t.output_encoding == 'FAKE_ENCODING'

        import os, stat
        def fake_os_stat(o):
            return {stat.ST_MTIME:t.module._modified_time+1}

        old_stat = os.stat
        os.stat = fake_os_stat
        try:
            t = mlookup.get_template(template_path)
            assert t.output_encoding == 'FAKE_ENCODING'
        finally:
            os.stat = old_stat


########NEW FILE########
__FILENAME__ = test_rest_controller_dispatch
# -*- coding: utf-8 -*-

from webob import Response, Request

from tg.controllers import TGController, RestController
from tg.decorators import expose
from tg.util import no_warn

from tests.base import (
    TestWSGIController, make_app, setup_session_dir, teardown_session_dir)


def setup():
    setup_session_dir()

def teardown():
    teardown_session_dir()


def wsgi_app(environ, start_response):
    req = Request(environ)
    if req.method == 'POST':
        resp = Response(req.POST['data'])
    else:
        resp = Response("Hello from %s/%s"%(req.script_name, req.path_info))
    return resp(environ, start_response)


class LookupHelper:
    def __init__(self, var):
        self.var = var

    @expose()
    def index(self):
        return self.var


class LookupController(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupHelper(a), args


class DeprecatedLookupController(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupHelper(a), args


class LookupAlwaysHelper:
    """for testing _dispatch"""

    def __init__(self, var):
        self.var = var

    def _setup_wsgiorg_routing_args(self, url_path, remainder, params):
        pass

    @expose()
    def always(self, *args, **kwargs):
        return 'always go here'

    def _dispatch(self, state, remainder):
        state.add_method(self.always, remainder)
        return state


class LookupAlwaysController(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupAlwaysHelper(a), args


class CustomDispatchingSubController(TGController):

    @expose()
    def always(self, *args, **kwargs):
        return 'always go here'

    def _dispatch(self, state, remainder):
        state.add_method(self.always, remainder)
        return state


class OptionalArgumentRestController(RestController):

    @expose()
    def get_one(self, optional=None):
        return "SUBREST GET ONE"

    @expose()
    def put(self, optional=None):
        return "subrest put"

    @expose()
    def post(self, optional=None):
        return "subrest post"

    @expose()
    def edit(self, optional=None):
        return "subrest edit"

    @expose()
    def new(self, optional=None):
        return "subrest new"

    @expose()
    def get_delete(self, optional=None):
        return "subrest get delete"

    @expose()
    def post_delete(self, optional=None):
        return "subrest post delete"


class RequiredArgumentRestController(RestController):

    @expose()
    def get_one(self, something):
        return "subrest get one"

    @expose()
    def put(self, something):
        return "subrest put"

    @expose()
    def post(self, something):
        return "subrest post"

    @expose()
    def edit(self, something):
        return "subrest edit"

    @expose()
    def new(self):
        return "subrest new"

    @expose()
    def get_delete(self, something):
        return "subrest get delete"

    @expose()
    def post_delete(self, something):
        return "subrest post delete"


class VariableSubRestController(RestController):

    @expose()
    def get_one(self, *args):
        return "subrest get one"

    @expose()
    def put(self, *args):
        return "subrest put"

    @expose()
    def edit(self, *args):
        return "subrest edit"

    @expose()
    def new(self, *args):
        return "subrest new"

    @expose()
    def get_delete(self, *args):
        return "subrest get delete"

    @expose()
    def post_delete(self, *args):
        return "subrest post delete"


class SubRestController(RestController):

    @expose()
    def get_all(self):
        return "subrest get all"

    @expose()
    def get_one(self, nr):
        return "subrest get one %s" % nr

    @expose()
    def new(self):
        return "subrest new"

    @expose()
    def edit(self, nr):
        return "subrest edit %s" % nr

    @expose()
    def post(self):
        return "subrest post"

    @expose()
    def put(self, nr):
        return "subrest put %s" % nr

    @expose()
    def fxn(self):
        return "subrest fxn"

    @expose()
    def get_delete(self, nr):
        return "subrest get delete %s" % nr

    @expose()
    def post_delete(self, nr):
        return "subrest post delete %s" % nr


class VariableRestController(RestController):

    subrest = SubRestController()
    vsubrest = VariableSubRestController()

    @expose()
    def get_all(self):
        return "rest get all"

    @expose()
    def get_one(self, *args):
        return "rest get onE"

    @expose()
    def get_delete(self, *args):
        return "rest get delete"

    @expose()
    def post_delete(self, *args):
        return "rest post delete"


class ExtraRestController(RestController):

    @expose()
    def get_all(self):
        return "rest get all"

    @expose()
    def get_one(self, nr):
        return "rest get one %s" % nr

    @expose()
    def get_delete(self, nr):
        return "rest get delete %s" % nr

    @expose()
    def post_delete(self, nr):
        return "rest post delete %s" % nr

    class SubClass(TGController):
        @expose()
        def index(self):
            return "rest sub index"

    sub = SubClass()
    subrest = SubRestController()
    optsubrest = OptionalArgumentRestController()
    reqsubrest = RequiredArgumentRestController()

    @expose()
    def post_archive(self):
        return 'got to post archive'

    @expose()
    def get_archive(self):
        return 'got to get archive'


class BasicRestController(RestController):

    @expose()
    def get(self):
        return "rest get"

    @expose()
    def post(self):
        return "rest post"

    @expose()
    def put(self):
        return "rest put"

    @expose()
    def delete(self):
        return "rest delete"

    @expose()
    def new(self):
        return "rest new"
    @expose()
    def edit(self, *args, **kw):
        return "rest edit"

    @expose()
    def other(self):
        return "rest other"

    @expose()
    def archive(self):
        return 'got to archive'


class EmptyRestController(RestController):
    pass


class SubController(TGController):

    rest = BasicRestController()

    @expose()
    def sub_method(self, arg):
        return 'sub %s'%arg


class BasicTGController(TGController):

    sub = SubController()
    custom_dispatch = CustomDispatchingSubController()
    lookup = LookupController()
    deprecated_lookup = LookupController()
    lookup_dispatch = LookupAlwaysController()
    rest  = BasicRestController()
    rest2 = ExtraRestController()
    rest3 = VariableRestController()
    empty = EmptyRestController()

    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def _default(self, *remainder):
        return "Main default page called for url /%s" % [str(r) for r in remainder]

    @expose()
    def hello(self, name, silly=None):
        return "Hello %s" % name


class BasicTGControllerNoDefault(TGController):

    @expose()
    def index(self, **kwargs):
        return 'hello world'


class TestTGControllerRoot(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGControllerNoDefault)

    def test_root_default_dispatch(self):
        self.app.get('/i/am/not/a/sub/controller', status=404)


class TestTGController(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_lookup(self):
        r = self.app.get('/lookup/eye')
        msg = 'eye'
        assert msg in r, r

    def test_deprecated_lookup(self):
        r = self.app.get('/deprecated_lookup/eye')
        msg = 'eye'
        assert msg in r, r

    def test_lookup_with_dispatch(self):
        r = self.app.get('/lookup_dispatch/eye')
        msg = 'always'
        assert msg in r, r

    def test_root_method_dispatch(self):
        resp = self.app.get('/hello/Bob')
        assert "Hello Bob" in resp, resp

    def test_root_index_dispatch(self):
        resp = self.app.get('/')
        assert "hello world" in resp, resp

    def test_no_sub_index_dispatch(self):
        resp = self.app.get('/sub/')
        assert "['sub']" in resp, resp

    def test_root_default_dispatch(self):
        resp = self.app.get('/i/am/not/a/sub/controller')
        assert "['i', 'am', 'not', 'a', 'sub', 'controller']" in resp, resp

    def test_default_dispatch_not_found_in_sub_controller(self):
        resp = self.app.get('/sub/no/default/found')
        assert "['sub', 'no', 'default', 'found']" in resp, resp

    def test_root_method_dispatch_with_trailing_slash(self):
        resp = self.app.get('/hello/Bob/')
        assert "Hello Bob" in resp, resp

    def test_sub_method_dispatch(self):
        resp = self.app.get('/sub/sub_method/army of darkness')
        assert "sub army" in resp, resp

    def test_custom_dispatch(self):
        resp = self.app.get('/custom_dispatch/army of darkness')
        assert "always" in resp, resp

class TestRestController(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_post(self):
        r = self.app.post('/rest/')
        assert 'rest post' in r, r

    def _test_non_resty(self):
        r = self.app.post('/rest/non_resty_thing')
        assert 'non_resty' in r, r

    def test_custom_action_simple_get(self):
        r = self.app.get('/rest/archive')
        assert 'got to archive' in r, r

    def test_custom_action_simple_post(self):
        r = self.app.post('/rest/archive')
        assert 'got to archive' in r, r

    def test_custom_action_simple_post_args(self):
        r = self.app.post('/rest?_method=archive')
        assert 'got to archive' in r, r

    def test_custom_action_get(self):
        r = self.app.get('/rest2/archive')
        assert 'got to get archive' in r, r

    def test_custom_action_post(self):
        r = self.app.post('/rest2?_method=archive')
        assert 'got to post archive' in r, r

    def test_get(self):
        r = self.app.get('/rest/')
        assert 'rest get' in r, r

    def test_put(self):
        r = self.app.put('/rest/')
        assert 'rest put' in r, r

    def test_put_post(self):
        r = self.app.post('/rest?_method=PUT')
        assert 'rest put' in r, r

    def test_put_post_params(self):
        r = self.app.post('/rest', params={'_method':'PUT'})
        assert 'rest put' in r, r

    def test_put_get(self):
        self.app.get('/rest?_method=PUT', status=405)

    def test_get_delete_bad(self):
        self.app.get('/rest?_method=DELETE', status=405)

    def test_delete(self):
        r = self.app.delete('/rest/')
        assert 'rest delete' in r, r

    def test_post_delete(self):
        r = self.app.post('/rest/', params={'_method':'DELETE'})
        assert 'rest delete' in r, r

    def test_get_all(self):
        r = self.app.get('/rest2/')
        assert 'rest get all' in r, r

    def test_get_one(self):
        r = self.app.get('/rest2/1')
        assert 'rest get one 1' in r, r

    def test_get_delete(self):
        r = self.app.get('/rest2/1/delete')
        assert 'rest get delete' in r, r

    def test_post_delete_params(self):
        r = self.app.post('/rest2/1', params={'_method':'DELETE'})
        assert 'rest post delete' in r, r

    def test_post_delete_var(self):
        r = self.app.post('/rest3/a/b/c', params={'_method':'DELETE'})
        assert 'rest post delete' in r, r

    def test_get_delete_var(self):
        r = self.app.get('/rest3/a/b/c/delete')
        assert 'rest get delete' in r, r

    def test_get_method(self):
        r = self.app.get('/rest/other')
        assert 'rest other' in r, r

    @no_warn
    def test_get_sub_controller(self):
        r = self.app.get('/rest2/sub')
        assert 'rest sub index' in r, r

    @no_warn
    def test_put_sub_controller(self):
        r = self.app.put('/rest2/sub')
        assert 'rest sub index' in r, r

    def test_post_sub_controller(self):
        r = self.app.post('/rest2/sub')
        assert 'rest sub index' in r, r

    def test_post_miss(self):
        r = self.app.post('/rest2/something')
        assert "/['rest2', 'something']" in r, r

    def test_get_empty(self):
        r = self.app.get('/empty/')
        assert "/['empty']" in r, r

    def test_post_empty(self):
        r = self.app.post('/empty/')
        assert "/['empty']" in r, r

    def test_put_empty(self):
        r = self.app.put('/empty/')
        assert "/['empty']" in r, r

    @no_warn
    def test_delete_empty(self):
        r = self.app.delete('/empty/')
        assert "/['empty']" in r, r

    def test_put_miss(self):
        r = self.app.put('/rest/something')
        assert "/['rest', 'something']" in r, r

    def test_delete_miss(self):
        r = self.app.delete('/rest/something')
        assert "/['rest', 'something']" in r, r

    def test_get_miss(self):
        r = self.app.get('/rest2/something/else')
        assert "/['rest2', 'something', 'else']" in r, r

    def test_post_method(self):
        r = self.app.post('/rest/other')
        assert 'rest other' in r, r

    def test_new_method(self):
        r = self.app.post('/rest/new')
        assert 'rest new' in r, r

    def test_edit_method(self):
        r = self.app.get('/rest/1/edit')
        assert 'rest edit' in r, r

    def test_delete_method(self):
        self.app.delete('/rest/other', status=405)

    def test_sub_with_rest_delete(self):
        r = self.app.delete('/sub/rest/')
        assert 'rest delete' in r, r

    def test_put_method(self):
        r = self.app.put('/rest/other')
        assert 'rest other' in r, r

    def test_sub_get_all_method(self):
        r = self.app.get('/rest2/1/subrest')
        assert 'subrest get all' in r, r

    def test_var_sub_get_all_method(self):
        r = self.app.get('/rest3/1/3/3/subrest')
        assert 'subrest get all' in r, r
        r = self.app.get('/rest3/1/3/subrest')
        assert 'subrest get all' in r, r
        r = self.app.get('/rest3/subrest')
        assert 'subrest get all' in r, r

    def test_var_sub_get_one_method(self):
        r = self.app.get('/rest3/1/3/3/subrest/1')
        assert 'subrest get one' in r, r
        r = self.app.get('/rest3/1/3/subrest/1')
        assert 'subrest get one' in r, r
        r = self.app.get('/rest3/subrest/1')
        assert 'subrest get one' in r, r

    def test_var_sub_edit_method(self):
        r = self.app.get('/rest3/1/3/3/subrest/1/edit')
        assert 'subrest edit' in r, r
        r = self.app.get('/rest3/1/3/subrest/1/edit')
        assert 'subrest edit' in r, r
        r = self.app.get('/rest3/subrest/1/edit')
        assert 'subrest edit' in r, r

    def test_var_sub_edit_var_method(self):
        r = self.app.get('/rest3/1/3/3/vsubrest/1/edit')
        assert 'subrest edit' in r, r
        r = self.app.get('/rest3/1/3/vsubrest/1/a/edit')
        assert 'subrest edit' in r, r
        r = self.app.get('/rest3/vsubrest/edit')
        assert 'subrest edit' in r, r

    def test_var_sub_delete_method(self):
        r = self.app.get('/rest3/1/3/3/subrest/1/delete')
        assert 'subrest get delete' in r, r
        r = self.app.get('/rest3/1/3/subrest/1/delete')
        assert 'subrest get delete' in r, r
        r = self.app.get('/rest3/subrest/1/delete')
        assert 'subrest get delete' in r, r

    def test_var_sub_new_method(self):
        r = self.app.get('/rest3/1/3/3/subrest/new')
        assert 'subrest new' in r, r
        r = self.app.get('/rest3/1/3/subrest/new')
        assert 'subrest new' in r, r
        r = self.app.get('/rest3/subrest/new')
        assert 'subrest new' in r, r

    def test_var_sub_var_get_one_method(self):
        r = self.app.get('/rest3/1/3/3/vsubrest/1')
        assert 'subrest get one' in r, r
        r = self.app.get('/rest3/1/3/vsubrest/1/a')
        assert 'subrest get one' in r, r
        r = self.app.get('/rest3/vsubrest/')
        assert 'subrest get one' in r, r

    def test_var_sub_var_put_method(self):
        r = self.app.put('/rest3/1/3/3/vsubrest/1')
        assert 'subrest put' in r, r
        r = self.app.put('/rest3/1/3/vsubrest/1/asdf')
        assert 'subrest put' in r, r
        r = self.app.put('/rest3/vsubrest/')
        assert 'subrest put' in r, r

    def test_var_sub_post_method(self):
        r = self.app.post('/rest3/1/3/3/subrest/')
        assert 'subrest post' in r, r
        r = self.app.post('/rest3/1/3/subrest/')
        assert 'subrest post' in r, r
        r = self.app.post('/rest3/subrest/')
        assert 'subrest post' in r, r

    def test_var_sub_post_delete_method(self):
        r = self.app.delete('/rest3/1/3/3/subrest/1')
        assert 'subrest post delete' in r, r
        r = self.app.delete('/rest3/1/3/subrest/1')
        assert 'subrest post delete' in r, r

    def test_var_sub_put_method(self):
        r = self.app.put('/rest3/1/3/3/subrest/1')
        assert 'subrest put' in r, r
        r = self.app.put('/rest3/1/3/subrest/1')
        assert 'subrest put' in r, r
        r = self.app.put('/rest3/subrest/1')
        assert 'subrest put' in r, r

    def test_var_sub_put_hack_method(self):
        r = self.app.post('/rest3/1/3/3/subrest/1?_method=PUT')
        assert 'subrest put' in r, r
        r = self.app.post('/rest3/1/3/subrest/1?_method=put')
        assert 'subrest put' in r, r
        r = self.app.post('/rest3/subrest/1?_method=put')
        assert 'subrest put' in r, r

    def test_var_sub_var_delete_method(self):
        r = self.app.delete('/rest3/1/3/3/vsubrest/1')
        assert 'subrest post delete' in r, r
        r = self.app.delete('/rest3/1/3/vsubrest/1')
        assert 'subrest post delete' in r, r
        r = self.app.delete('/rest3/vsubrest/')
        assert 'subrest post delete' in r, r

    def test_var_sub_delete_var_hack_method(self):
        r = self.app.post('/rest3/1/3/3/vsubrest/1?_method=DELETE')
        assert 'subrest post delete' in r, r
        r = self.app.post('/rest3/1/3/vsubrest/1?_method=delete')
        assert 'subrest post delete' in r, r
        r = self.app.post('/rest3/vsubrest?_method=delete')
        assert 'subrest post delete' in r, r

    def test_var_sub_var_put_hack_method(self):
        r = self.app.post('/rest3/1/3/3/vsubrest/1?_method=PUT')
        assert 'subrest put' in r, r
        r = self.app.post('/rest3/1/3/vsubrest/1/a?_method=put')
        assert 'subrest put' in r, r
        r = self.app.post('/rest3/vsubrest/?_method=put')
        assert 'subrest put' in r, r

    def test_var_sub_delete_hack_method(self):
        r = self.app.post('/rest3/1/3/3/subrest/1?_method=DELETE')
        assert 'subrest post delete' in r, r
        r = self.app.post('/rest3/1/3/subrest/1?_method=delete')
        assert 'subrest post delete' in r, r
        r = self.app.post('/rest3/subrest/1?_method=delete')
        assert 'subrest post delete' in r, r

    def test_sub_new(self):
        r = self.app.get('/rest2/1/subrest/new')
        assert 'subrest new' in r, r

    def test_sub_edit(self):
        r = self.app.get('/rest2/1/subrest/1/edit')
        assert 'subrest edit' in r, r

    def test_sub_post(self):
        r = self.app.post('/rest2/1/subrest/')
        assert 'subrest post' in r, r

    def test_sub_put(self):
        r = self.app.put('/rest2/1/subrest/2')
        assert 'subrest put' in r, r

    def test_sub_post_opt(self):
        r = self.app.post('/rest2/1/optsubrest/1')
        assert 'subrest post' in r, r

    def test_sub_put_opt(self):
        r = self.app.put('/rest2/1/optsubrest/1')
        assert 'subrest put' in r, r

    def test_sub_put_opt_hack(self):
        r = self.app.post('/rest2/1/optsubrest/1?_method=PUT')
        assert 'subrest put' in r, r

    def test_sub_delete_opt_hack(self):
        r = self.app.post('/rest2/1/optsubrest/1?_method=DELETE')
        assert 'subrest ' in r, r

    def test_put_post_req(self):
        r = self.app.post('/rest2/reqsubrest', params={'something':'required'})
        assert 'subrest post' in r, r

    def test_sub_put_req(self):
        r = self.app.post('/rest2/reqsubrest', params={'_method':'PUT', 'something':'required'})
        assert 'subrest put' in r, r

    def test_sub_post_req_bad(self):
        r = self.app.post('/rest2/reqsubrest',)
        assert "['rest2', 'reqsubrest']" in r, r

    def test_sub_delete_hack(self):
        r = self.app.post('/rest2/1/subrest/2?_method=DELETE')
        assert 'subrest post delete' in r, r

    def test_sub_get_delete(self):
        r = self.app.get('/rest2/1/subrest/2/delete')
        assert 'subrest get delete' in r, r

    def test_sub_post_delete(self):
        r = self.app.delete('/rest2/1/subrest/2')
        assert 'subrest post delete' in r, r

    def test_sub_get_fxn(self):
        r = self.app.get('/rest2/1/subrest/fxn')
        assert 'subrest fxn' in r, r

    def test_sub_post_fxn(self):
        r = self.app.post('/rest2/1/subrest/fxn')
        assert 'subrest fxn' in r, r

########NEW FILE########
__FILENAME__ = baseutils
import tg

class FakePackage(object):
    pass

default_config = {
        'debug': False,
        'package': FakePackage,
        'package_name' : 'FakePackage',
        'paths': {'root': None,
                         'controllers': None,
                         'templates': [],
                         'static_files': None},
        'db_engines': {},
        'tg.strict_tmpl_context':False,
        'use_dotted_templatenames':True,
        'buffet.template_engines': [],
        'buffet.template_options': {},
        'default_renderer':'json',
        'renderers': ['json'],
        'render_functions': {'json': tg.renderers.json.JSONRenderer.render_json},
        'rendering_engines_options': {'json': {'content_type': 'application/json'}},
        'rendering_engines_without_vars': set(('json',)),
        'use_legacy_renderers':False,
        'use_sqlalchemy': False,
        'lang': None
}

class FakeRoutes(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        environ['wsgiorg.routing_args'] = [None, {'controller':'root'}]
        environ['routes.url'] = None
        return self.app(environ, start_response)


class ControllerWrap(object):
    def __init__(self, controller):
        self.controller = controller

    def __call__(self, environ, start_response):
        app = self.controller()
        return app(environ, start_response)
########NEW FILE########
__FILENAME__ = root
"""Main Controller"""

from tg import expose, redirect, config
from tg.controllers import TGController

class RootController(TGController):
    @expose()
    def index(self):
        return "my foo"

    @expose()
    def config_test(self):
        return str(config)
    
    @expose()
    def config_attr_lookup(self):
        return str(config.render_functions)
    
    @expose()
    def config_dotted_values(self):
        return str(config.paths)
    
    @expose()
    def config_attr_set(self, foo):
        config.test_value = foo
        return str(config.test_value)
        
    @expose()
    def config_set_method(self):
        return str(config.get('pylons'))

    @expose()
    def config_dict_set(self, foo):
        config['test_value'] = foo
        return str(config.test_value)
        


########NEW FILE########
__FILENAME__ = test_config
from tests.test_stack import TestConfig, app_from_config

def setup_noDB():
    base_config = TestConfig(folder = 'config',
                             values = {'use_sqlalchemy': False,
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2':False}
                             )
    return app_from_config(base_config)

def test_basic_stack():
    app = setup_noDB()
    resp = app.get('/')
    assert resp.body.decode('ascii') == "my foo"

def test_config_reading():
    """Ensure that the config object can be read via dict and attr access"""
    app = setup_noDB()
    resp = app.get('/config_test')
    resp_body = resp.body.decode('ascii')

    assert "default_renderer" in resp_body
    resp = app.get('/config_attr_lookup')
    assert "genshi" in resp_body
    resp = app.get('/config_dotted_values')
    assert "root" in resp_body

def test_config_writing():
    """Ensure that new values can be added to the config object"""
    app = setup_noDB()
    value = "gooberblue"
    resp = app.get('/config_attr_set/'+value)
    resp_body = resp.body.decode('ascii')

    assert value in resp_body
    resp = app.get('/config_dict_set/'+value)
    assert value in resp_body


########NEW FILE########
__FILENAME__ = root
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import tg
from tg.controllers import TGController
from tg.decorators import expose, validate, https, variable_decode, with_trailing_slash, \
    without_trailing_slash, with_engine
from tg import expose, redirect, config
from tg.controllers import TGController
from tg import dispatched_controller
from nose.tools import eq_
from tests.test_validation import validators
from tg._compat import unicode_text

from paste.deploy.converters import asbool

class NestedSubController(TGController):
    @expose()
    def index(self):
        return '-'.join((self.mount_point, dispatched_controller().mount_point))

    @expose()
    def hitme(self):
        return '*'.join((self.mount_point, dispatched_controller().mount_point))

    @expose()
    def _lookup(self, *args):
        lookup = LookupController()
        return lookup, args

class SubController(TGController):
    nested = NestedSubController()
    
    @expose()
    def foo(self,):
        return 'sub_foo'

    @expose()
    def index(self):
        return 'sub index'

    @expose()
    def _default(self, *args):
        return ("recieved the following args (from the url): %s" %list(args))

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, **kw)

    @expose()
    def redirect_sub(self):
        tg.redirect('index')

    @expose()
    def redirect_list(self):
        tg.redirect(["/sub2", "list"])

    @expose()
    def hello(self, name):
        return "Why HELLO! " + name

    @expose()
    def hitme(self):
        return '@'.join((self.mount_point, dispatched_controller().mount_point))

class LookupController(TGController):
    nested = NestedSubController()
    
    @expose()
    def findme(self, *args, **kw):
        return 'got to lookup'

    @expose()
    def hiddenhitme(self, *args, **kw):
        return ' '.join((self.mount_point, dispatched_controller().mount_point))

class SubController2(object):
    @expose()
    def index(self):
        tg.redirect('list')

    @expose()
    def list(self, **kw):
        return "hello list"

    @expose()
    def _lookup(self, *args):
        lookup = LookupController()
        return lookup, args

class RootController(TGController):
    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def _default(self, remainder):
        return "Main Default Page called for url /%s"%remainder

    @expose()
    def feed(self, feed=None):
        return feed

    sub = SubController()
    sub2 = SubController2()

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, kw)

    @expose()
    def hello(self, name, silly=None):
        return "Hello " + name

    @expose()
    def redirect_cookie(self, name):
        tg.response.set_cookie('name', name)
        tg.redirect('/hello_cookie')

    @expose()
    def hello_cookie(self):
        return "Hello " + tg.request.cookies['name']

    @expose()
    def flash_redirect(self):
        tg.flash("Wow, flash!")
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_render(self, using_js=False, with_message=True):
        if asbool(with_message):
            tg.flash('JS Flash')

        return tg.flash.render('flash', asbool(using_js))

    @expose()
    def bigflash_redirect(self):
        tg.flash('x' * 5000)
        tg.redirect('/flash_after_redirect')

    @expose()
    def flash_unicode(self):
        tg.flash("Привет, мир!")
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_after_redirect(self):
        return tg.get_flash()

    @expose()
    def flash_status(self):
        return tg.get_status()

    @expose()
    def flash_no_redirect(self):
        tg.flash("Wow, flash!")
        return tg.get_flash()

    @expose('json')
    @validate(validators={"some_int": validators.Int()})
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json')
    @validate(validators={"a":validators.Int()})
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
        return dict(int=a,str=b)

    @expose()
    @expose('json')
    def stacked_expose(self, tg_format=None):
        return dict(got_json=True)

    @expose('json')
    def json_return_list(self):
        return [1,2,3]

    @expose(content_type='image/png')
    def custom_content_type(self):
        return b'PNG'

    @expose()
    def custom_content_type2(self):
        tg.response.content_type = 'image/png'
        return b'PNG2'

    @expose(content_type='text/plain')
    def custom_content_text_plain_type(self):
        return 'a<br/>bx'

    @expose()
    def check_params(self, *args, **kwargs):
        if not args and not kwargs:
            return "None recieved"
        else:
            return "Controler recieved: %s, %s" %(args, kwargs)

    @expose()
    def test_url_sop(self):
        from tg import url
        eq_('/foo', url('/foo'))


        u = url("/foo", params=dict(bar=1, baz=2))
        assert u in \
                ["/foo?bar=1&baz=2", "/foo?baz=2&bar=1"], u

    @https
    @expose()
    def test_https(self, **kw):
        return ''

    @expose('json')
    @variable_decode
    def test_vardec(self, **kw):
        return kw

    @expose('mako:echo.mak')
    def echo(self):
        return dict()

    @expose()
    @with_trailing_slash
    def with_tslash(self):
        return 'HI'

    @expose()
    @without_trailing_slash
    def without_tslash(self):
        return 'HI'

    @expose()
    @with_engine('mainslave', master_params=['first'])
    def onmaster_withlist(self, **kw):
        return '%s-%s' % (tg.request._tg_force_sqla_engine, kw)

    @expose()
    @with_engine('mainslave', master_params={'first':True, 'second':False})
    def onmaster(self, **kw):
        return '%s-%s' % (tg.request._tg_force_sqla_engine, kw)
########NEW FILE########
__FILENAME__ = test_config
import os
from tests.test_stack import TestConfig
from webtest import TestApp

def setup_noDB():
    global_config = {'debug': 'true', 
                     'error_email_from': 'paste@localhost', 
                     'smtp_server': 'localhost'}
    
    base_config = TestConfig(folder = 'config', 
                             values = {'use_sqlalchemy': False,
                                       'use_toscawidgets':False,
                                       'use_toscawidgets2':False}
                             )
                             
    env_loader = base_config.make_load_environment()
    app_maker = base_config.setup_tg_wsgi_app(env_loader)
    app = TestApp(app_maker(global_config, full_stack=True))
    return app 

def test_basic_stack():
    app = setup_noDB()
    resp = app.get('/')
    assert resp.body.decode('ascii') == "my foo"

def test_config_reading():
    """Ensure that the config object can be read via dict and attr access"""
    app = setup_noDB()
    resp = app.get('/config_test')
    assert "default_renderer" in str(resp.body)
    resp = app.get('/config_attr_lookup')
    assert "genshi" in str(resp.body)
    resp = app.get('/config_dotted_values')
    assert "root" in str(resp.body)

def test_config_writing():
    """Ensure that new values can be added to the config object"""
    app = setup_noDB()
    value = "gooberblue"
    resp = app.get('/config_attr_set/'+value)
    assert value in str(resp.body)
    resp = app.get('/config_dict_set/'+value)
    assert value in str(resp.body)


########NEW FILE########
__FILENAME__ = test_decorated_controller
# -*- coding: utf-8 -*-
from nose.tools import raises
import os, tg
from tests.test_stack import TestConfig, app_from_config
from tg.decorators import Decoration
from tg.configuration import milestones

from nose.tools import eq_
from nose import SkipTest
from tg._compat import PY3, u_
from tg.util import Bunch


class TestHooks(object):
    def setUp(self):
        milestones._reset_all()

    def test_hooks_syswide(self):
        base_config = TestConfig(folder = 'dispatch',
                                 values = {'use_sqlalchemy': False,
                                           'use_toscawidgets': False,
                                           'use_toscawidgets2': False,
                                           'ignore_parameters': ["ignore", "ignore_me"]
                                 })

        def hook(*args, **kw):
            tg.tmpl_context.echo = 'WORKED'

        base_config.register_hook('before_call', hook)
        app = app_from_config(base_config, reset_milestones=False)

        ans = app.get('/echo')
        assert 'WORKED' in ans

    def test_decoration_run_hooks_backward_compatibility(self):
        # TODO: Remove test when Decoration.run_hooks gets removed

        def func(*args, **kw):
            pass

        def hook(*args, **kw):
            hook.did_run = True
        hook.did_run = False

        milestones.renderers_ready.reach()
        tg.hooks.register('before_call', hook, controller=func)

        deco = Decoration.get_decoration(func)
        deco.run_hooks(Bunch(config=None), 'before_call')

        assert hook.did_run is True

class TestExpose(object):
    def setUp(self):
        milestones.renderers_ready._reset()

    def tearDown(self):
        milestones.renderers_ready._reset()

    def test_unregisterd_renderers_detection(self):
        #If no renderers are available we should just issue a warning
        #and avoid crashing. Simply bypass rendering availability check.
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        app = app_from_config(base_config)

        old_renderers = tg.config['renderers']
        tg.config['renderers'] = []

        @tg.expose('mako:nonexisting')
        def func(*args, **kw):
            pass

        tg.config['renderers'] = old_renderers

    def test_use_default_renderer(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        app = app_from_config(base_config)

        exposition = tg.expose('nonexisting')
        exposition._resolve_options()

        assert exposition.engine == tg.config['default_renderer']
        assert exposition.template == 'nonexisting'

    def test_expose_without_function_does_nothing(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        app = app_from_config(base_config)

        exposition = tg.expose('nonexisting')
        exposition._apply()

        assert exposition._func is None
        assert exposition.engine is None

    def test_expose_idempotent(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        app = app_from_config(base_config)

        exposition = tg.expose('nonexisting')

        @exposition
        @exposition
        def func(*args, **kw):
            pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(func)
        assert len(deco.engines) == 1, deco.engines

class TestDecorators(object):
    def setup(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        self.app = app_from_config(base_config)

    def test_variabledecode_fail(self):
        resp = self.app.get('/test_vardec', params={'test-1': '1',
                                                    'test-2': 2,
                                                    'test--repetitions': 'hi'})
        assert resp.json['test-1'] == '1', resp.json
        assert resp.json['test--repetitions'] == 'hi', resp.json
        assert 'test' not in resp.json, resp.json

    def test_variabledecode_partial_fail(self):
        resp = self.app.get('/test_vardec', params={'test-1': '1',
                                                    'test-2': 2,
                                                    'test-': 4})
        assert resp.json['test-1'] == '1'
        assert resp.json['test-'] == '4'
        assert len(resp.json['test']) == 2

    def test_variable_decode(self):
        from formencode.variabledecode import variable_encode
        obj = dict(a=['1','2','3'], b=dict(c=[dict(d='1')]))
        params = variable_encode(dict(obj=obj), add_repetitions=False)
        resp = self.app.get('/test_vardec', params=params)
        assert resp.json['obj'] == obj, (resp.json['obj'], obj)

    def test_without_trailing_slash(self):
        resp = self.app.get('/without_tslash/', status=301)
        assert resp.headers['Location'].endswith('/without_tslash')

    def test_with_trailing_slash(self):
        resp = self.app.get('/with_tslash', status=301)
        assert resp.headers['Location'].endswith('/with_tslash/')

    def test_with_engine(self):
        resp = self.app.get('/onmaster')
        assert 'mainslave' in resp

    def test_with_engine_nopop(self):
        resp = self.app.get('/onmaster?second=1')
        assert 'master' in resp
        assert 'second' in resp

    def test_with_engine_pop(self):
        resp = self.app.get('/onmaster?first=1')
        assert 'master' in resp
        assert 'first' not in resp

    def test_with_engine_using_list(self):
        resp = self.app.get('/onmaster_withlist?first=1')
        assert 'master' in resp
        assert 'first' not in resp

########NEW FILE########
__FILENAME__ = test_url_dispatch
# -*- coding: utf-8 -*-
from nose.tools import raises
import os
from tests.test_stack import TestConfig, app_from_config
from webtest import TestApp
from tg.jsonify import JsonEncodeError
from tg.util import no_warn

from nose.tools import eq_
from nose import SkipTest
from tg._compat import PY3, u_
import json

def setup_noDB():
    base_config = TestConfig(folder = 'dispatch',
                             values = {'use_sqlalchemy': False,
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False,
                                       'ignore_parameters': ["ignore", "ignore_me"]
                             })
    return app_from_config(base_config)


app = None
def setup():
    global app
    app = setup_noDB()

@no_warn #should be _default now
def test_tg_style_default():
    resp = app.get('/sdfaswdfsdfa') #random string should be caught by the default route
    assert 'Default' in resp.body.decode('utf-8')

def test_url_encoded_param_passing():
    resp = app.get('/feed?feed=http%3A%2F%2Fdeanlandolt.com%2Ffeed%2Fatom%2F')
    assert "http://deanlandolt.com/feed/atom/" in resp.body.decode('utf-8')

def test_tg_style_index():
    resp = app.get('/index/')
    assert 'hello' in resp.body.decode('utf-8'), resp

def test_tg_style_subcontroller_index():
    resp = app.get('/sub/index')
    assert "sub index" in resp.body.decode('utf-8')

def test_tg_style_subcontroller_default():
    resp=app.get('/sub/bob/tim/joe')
    assert 'bob' in resp.body.decode('utf-8'), resp
    assert 'tim' in resp.body.decode('utf-8'), resp
    assert 'joe' in resp.body.decode('utf-8'), resp

def test_redirect_absolute():
    resp = app.get('/redirect_me?target=/')
    assert resp.status == "302 Found", resp.status
    assert 'http://localhost/' in resp.headers['location']
    resp = resp.follow()
    assert 'hello world' in resp, resp

@no_warn
def test_redirect_relative():
    resp = app.get('/redirect_me?target=hello&name=abc')
    resp = resp.follow()
    assert 'Hello abc' in resp, resp
    resp = app.get('/sub/redirect_me?target=hello&name=def')
    resp = resp.follow()
    assert 'Why HELLO! def' in resp, resp
    resp = app.get('/sub/redirect_me?target=../hello&name=ghi')
    resp = resp.follow()
    assert 'Hello ghi' in resp, resp

def test_redirect_external():
    resp = app.get('/redirect_me?target=http://example.com')
    assert resp.status == "302 Found" and resp.headers['location'] == 'http://example.com', resp

def test_redirect_param():
    resp = app.get('/redirect_me?target=/hello&name=paj')
    resp = resp.follow()
    assert 'Hello paj' in resp, resp
    resp = app.get('/redirect_me?target=/hello&name=pbj')
    resp = resp.follow()
    assert 'Hello pbj' in resp, resp
    resp = app.get('/redirect_me?target=/hello&silly=billy&name=pcj')
    resp = resp.follow()
    assert 'Hello pcj' in resp, resp

def test_redirect_cookie():
    resp = app.get('/redirect_cookie?name=stefanha').follow()
    assert 'Hello stefanha' in resp

def test_subcontroller_redirect_subindex():
    resp=app.get('/sub/redirect_sub').follow()
    assert 'sub index' in resp

def test_subcontroller_redirect_sub2index():
    resp=app.get('/sub2/').follow()
    assert 'hello list' in resp

#this test does not run because of some bug in nose
def _test_subcontroller_lookup():
    resp=app.get('/sub2/findme').follow()
    assert 'lookup' in resp, resp

def test_subcontroller_redirect_no_slash_sub2index():
    resp=app.get('/sub2/').follow()
    assert 'hello list' in resp, resp

def test_redirect_to_list_of_strings():
    resp = app.get('/sub/redirect_list').follow()
    assert 'hello list' in resp, resp

def test_flash_redirect():
    resp = app.get('/flash_redirect').follow()
    assert 'Wow, flash!' in resp, resp

def test_bigflash_redirect():
    try:
        resp = app.get('/bigflash_redirect')
        assert False
    except Exception as e:
        assert 'Flash value is too long (cookie would be >4k)' in str(e)

def test_flash_no_redirect():
    resp = app.get('/flash_no_redirect')
    assert 'Wow, flash!' in resp, resp

def test_flash_unicode():
    resp = app.get('/flash_unicode').follow()
    content = resp.body.decode('utf8')
    assert u_('Привет, мир!') in content, content

def test_flash_status():
    resp = app.get('/flash_status')
    assert 'ok' in resp, resp

def test_flash_javascript():
    resp = app.get('/flash_render?using_js=True')
    webflash_js_parameters = json.dumps({"id": "flash", "name": "webflash"})
    expected = 'webflash(%s).render()' % webflash_js_parameters
    assert expected in resp

def test_flash_render_plain():
    resp = app.get('/flash_render')
    assert 'JS Flash' in resp

def test_flash_render_no_message():
    resp = app.get('/flash_render?with_message=False')
    assert 'flash' not in resp

def test_custom_content_type():
    resp = app.get('/custom_content_type')
    assert 'image/png' == dict(resp.headers)['Content-Type'], resp
    assert resp.body.decode('utf-8') == 'PNG', resp

def test_custom_text_plain_content_type():
    resp = app.get('/custom_content_text_plain_type')
    assert 'text/plain; charset=utf-8' == dict(resp.headers)['Content-Type'], resp
    assert resp.body.decode('utf-8') == """a<br/>bx""", resp

@no_warn
def test_custom_content_type2():
    resp = app.get('/custom_content_type2')
    assert 'image/png' == dict(resp.headers)['Content-Type'], resp
    assert resp.body.decode('utf-8') == 'PNG2', resp

@no_warn
def test_basicurls():
    resp = app.get("/test_url_sop")

def test_ignore_parameters():
    resp = app.get("/check_params?ignore='bar'&ignore_me='foo'")
    assert "None Received"

def test_json_return_list():
    try:
        resp = app.get("/json_return_list")
        assert False
    except Exception as e:
        assert 'You may not expose with JSON a list' in str(e)

def test_https_redirect():
    resp = app.get("/test_https?foo=bar&baz=bat")
    assert 'https://' in resp, resp
    assert resp.location.endswith("/test_https?foo=bar&baz=bat")
    resp = app.post("/test_https?foo=bar&baz=bat", status=405)

class TestVisits(object):
    def test_visit_path_sub1(self):
        resp = app.get("/sub/hitme")
        assert str(resp).endswith('/sub@/sub')

    def test_visit_path_nested(self):
        resp = app.get("/sub/nested/hitme")
        assert str(resp).endswith('/sub/nested*/sub/nested')

    def test_visit_path_nested_index(self):
        resp = app.get("/sub/nested")
        assert str(resp).endswith('/sub/nested-/sub/nested')

    def test_runtime_visit_path_subcontroller(self):
        resp = app.get("/sub/nested/nested/hitme")
        assert str(resp).endswith('*/sub/nested')

    def test_runtime_visit_path(self):
        resp = app.get("/sub/nested/hiddenhitme")
        assert str(resp).endswith(' /sub/nested')

########NEW FILE########
__FILENAME__ = base
"""Pylons requires that packages have a lib.base and lib.helpers 


So we've added on here so we can run tests in the context of the tg 
package itself, pylons will likely remove this restriction before 1.0 
and this module can then be removed. 

"""
########NEW FILE########
__FILENAME__ = helpers
"""Pylons requires that packages have a lib.base and lib.helpers 


So we've added on here so we can run tests in the context of the tg 
package itself, pylons will likely remove this restriction before 1.0 
and this module can then be removed. 

"""
########NEW FILE########
__FILENAME__ = jinja_filters
try:
    from hashlib import sha1
except ImportError:
    from sha1 import sha1

# avoid polluting module namespace
__all__ = ['codify']

def codify(value):
    string_hash = sha1(value.encode('ascii'))
    return string_hash.hexdigest()

def polluting_function(value):
    return "Template filter namespace has been POLLUTED"

########NEW FILE########
__FILENAME__ = root
"""Main Controller"""
import tg
from tg import expose, redirect, config, validate, override_template, response, render_template, tmpl_context
from tg import cache, i18n, request
from tg.decorators import paginate, use_custom_format, with_trailing_slash, Decoration, before_render
from tg.controllers import TGController
from tg.validation import TGValidationError
from tg._compat import PY3
from tg.render import _get_tg_vars, cached_template

if not PY3:
    from tw.forms import TableForm, TextField, CalendarDatePicker, SingleSelectField, TextArea
    from tw.api import WidgetsList

    class MovieForm(TableForm):
        # This WidgetsList is just a container
        class fields(WidgetsList):
            title = TextField()
            year = TextField(size=4, default=1984)
            description = TextArea()

    #then, we create an instance of this form
    base_movie_form = MovieForm("movie_form", action='create')


    import tw2.forms as tw2f
    import tw2.core as tw2c
    class TW2MovieForm(tw2f.TableForm):
        title = tw2f.TextField(validator=tw2c.Required)
        year = tw2f.TextField(size=4, validator=tw2c.IntValidator)

    tw2_movie_form = TW2MovieForm()

else:
    base_movie_form = None

class IntValidator(object):
    def to_python(self, value):
        try:
            return int(value)
        except:
            raise TGValidationError('Not a number')


class GoodJsonObject(object):

    def __json__(self):
        return {'Json':'Rocks'}

class BadJsonObject(object):
    pass


class JsonController(TGController):

    @expose('json')
    def json(self):
        return dict(a='hello world', b=True)

    @expose('json', exclude_names=["b"])
    def excluded_b(self):
        return dict(a="visible", b="invisible")

    @expose('json')
    @expose('genshi:test', content_type='application/xml')
    def xml_or_json(self):
        return dict(name="John Carter", title='officer', status='missing')

    @expose('json')
    def json_with_object(self):
        return dict(obj=GoodJsonObject())

    @expose('json')
    def json_with_bad_object(self):
        return dict(obj=BadJsonObject())


class SubClassableController(TGController):
    @expose('genshi:index.html')
    def index(self):
        return {}

    @expose('genshi:index.html')
    def index_override(self):
        return {}

    def before_render_data(remainder, params, output):
        output['parent_value'] = 'PARENT'

    @expose('json')
    @before_render(before_render_data)
    def data(self):
        return {'v':5}

class SubClassingController(SubClassableController):
    @expose(inherit=True)
    def index(self, *args, **kw):
        return super(SubClassingController, self).index(*args, **kw)

    @expose('genshi:genshi_doctype.html', inherit=True)
    def index_override(self, *args, **kw):
        return super(SubClassingController, self).index_override(*args, **kw)

    def before_render_data(remainder, params, output):
        output['child_value'] = 'CHILD'

    @expose(inherit=True)
    @before_render(before_render_data)
    def data(self, *args, **kw):
        return super(SubClassingController, self).data(*args, **kw)

class RootController(TGController):

    j = JsonController()
    sub1 = SubClassableController()
    sub2 = SubClassingController()

    @expose('genshi:index.html')
    def index(self):
        return {}

    @expose('genshi:genshi_doctype.html')
    def auto_doctype(self):
        return {}

    @expose('genshi:genshi_doctype.html', content_type='text/html')
    def auto_doctype_html(self):
        return {}

    @expose('genshi:genshi_doctype.html', content_type='application/xhtml+xml')
    def auto_doctype_xhtml(self):
        return {}

    @expose('genshi:genshi_doctype.html', render_params=dict(doctype=None))
    def explicit_no_doctype(self):
        return {}

    @expose('genshi:genshi_doctype.html', render_params=dict(doctype='html'))
    def explicit_doctype_html(self):
        return {}

    @expose('genshi:genshi_doctype.html', render_params=dict(doctype='xhtml'))
    def explicit_doctype_xhtml(self):
        return {}

    @expose('genshi:genshi_form.html')
    def form(self):
        return dict(form=base_movie_form)

    @expose('genshi:genshi_form.html')
    def tw2form(self):
        return dict(form=tw2_movie_form)

    @expose('genshi:genshi_foreign.html')
    def foreign(self):
        return {}

    @expose('json')
    @validate(form=base_movie_form)
    def process_form_errors(self, **kwargs):
        #add error messages to the kwargs dictionary and return it
        kwargs['errors'] = request.validation['errors']
        return dict(kwargs)

    @expose()
    @paginate('testdata')
    def paginated_text(self):
        return '''Some Text'''

    @expose('genshi:genshi_paginated.html')
    @expose('json')
    @paginate('testdata', max_items_per_page=20)
    def paginated(self, n):
        return dict(testdata=range(int(n)))

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    def paginate_with_params(self, n):
        url_params = dict(param1='hi', param2='man')
        return dict(testdata=range(int(n)), url_params=url_params)

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    @validate(dict(n=IntValidator()))
    def paginated_validated(self, n):
        return dict(testdata=range(n))

    @expose('genshi:genshi_paginated.html')
    @validate(dict(n=IntValidator()))
    @paginate('testdata')
    def validated_paginated(self, n):
        return dict(testdata=range(n))

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata', use_prefix=True)
    @paginate('testdata2', use_prefix=True)
    def multiple_paginators(self, n):
        n = int(n)
        return dict(testdata=range(n), testdata2=range(n+100, n+100+n))

    @expose('genshi:genshi_inherits.html')
    def genshi_inherits(self):
        return {}

    @expose('genshi:genshi_inherits_sub.html')
    def genshi_inherits_sub(self):
        return {}

    @expose('genshi:sub/frombottom.html')
    def genshi_inherits_sub_from_bottom(self):
        return {}

    @expose('jinja:jinja_noop.jinja')
    def jinja_index(self):
        return {}

    @expose('jinja:jinja_autoload.jinja')
    def jinja_autoload(self):
        return {}

    @expose('jinja:jinja_inherits.jinja')
    def jinja_inherits(self):
        return {}

    @expose('jinja:tests.test_stack.rendering.templates.jinja_noop')
    def jinja_dotted(self):
        return {}

    @expose('jinja:tests.test_stack.rendering.templates.jinja_inherits_dotted')
    def jinja_inherits_dotted(self):
        return {}

    @expose('jinja:tests.test_stack.rendering.templates.jinja_inherits')
    def jinja_inherits_mixed(self):
        return {}

    @expose('jinja:jinja_extensions.jinja')
    def jinja_extensions(self):
        test_autoescape_on = "<b>Test Autoescape On</b>"
        test_autoescape_off = "<b>Autoescape Off</b>"
        return dict(test_autoescape_off=test_autoescape_off,
                test_autoescape_on=test_autoescape_on)

    @expose('jinja:jinja_filters.jinja')
    def jinja_filters(self):
        return {}

    @expose('jinja:jinja_buildins.jinja')
    def jinja_buildins(self):
        return {}

    @expose('jinja:jinja_i18n.jinja')
    def jinja_i18n(self):
        return {}

    @expose('jinja:jinja_i18n.jinja')
    def jinja_i18n_en(self):
        i18n.set_temporary_lang("en")
        return {}

    @expose('jinja:jinja_i18n.jinja')
    def jinja_i18n_de(self):
        i18n.set_temporary_lang("de")
        return {}

    @expose('chameleon_genshi:index.html')
    def chameleon_genshi_index(self):
        return {}

    @expose('chameleon_genshi:genshi_inherits.html')
    def chameleon_genshi_inherits(self):
        return {}

    @expose('mako:mako_noop.mak')
    def mako_index(self):
        return {}

    @expose('mako:mako_inherits.mak')
    def mako_inherits(self):
        return {}

    @expose('chameleon_genshi:tests.test_stack.rendering.templates.index')
    def chameleon_index_dotted(self):
        return {}

    @expose('kajiki:tests.test_stack.rendering.templates.index')
    def kajiki_index_dotted(self):
        return {}

    @expose('genshi:tests.test_stack.rendering.templates.index')
    def index_dotted(self):
        return {}

    @expose('genshi:tests.test_stack.rendering.templates.genshi_inherits')
    def genshi_inherits_dotted(self):
        return {}

    @expose('genshi:tests.test_stack.rendering.templates.genshi_inherits_sub_dotted')
    def genshi_inherits_sub_dotted(self):
        return {}

    @expose('genshi:tests.test_stack.rendering.templates.sub.frombottom_dotted')
    def genshi_inherits_sub_dotted_from_bottom(self):
        return {}

    @expose('mako:tests.test_stack.rendering.templates.mako_noop')
    def mako_index_dotted(self):
        return {}

    @expose('mako:tests.test_stack.rendering.templates.mako_inherits_dotted')
    def mako_inherits_dotted(self):
        return {}

    @expose('json')
    @expose('genshi:index.html')
    def html_and_json(self):
        return {}

    @expose('json', custom_format='json')
    @expose('mako:mako_custom_format.mak', content_type='text/xml', custom_format='xml')
    @expose('genshi:genshi_custom_format.html', content_type='text/html', custom_format='html')
    def custom_format(self, format='default'):
        if format != 'default':
            use_custom_format(self.custom_format, format)
            return dict(format=format, status="ok")
        else:
            return 'OK'

    @expose("genshi:tests.non_overridden")
    def template_override(self, override=False):
        if override:
            override_template(self.template_override, "genshi:tests.overridden")
        return dict()

    @with_trailing_slash
    @expose("genshi:tests.non_overridden")
    def template_override_wts(self, override=False):
        if override:
            override_template(self.template_override_wts, "genshi:tests.overridden")
        return dict()

    @expose(content_type='text/javascript')
    def template_override_content_type(self, override=False):
        if override:
            override_template(self.template_override_content_type, "mako:tests.overridden_js")
            return dict()
        else:
            return "alert('Not overridden')"

    @expose('mako:mako_custom_format.mak', content_type='text/xml')
    @expose('genshi:genshi_custom_format.html', content_type='text/html')
    def template_override_multiple_content_type(self, override=False):
        if override:
            override_template(self.template_override_multiple_content_type, "mako:mako_noop.mak")
        return dict(format='something', status="ok")

    @expose()
    def jinja2_manual_rendering(self, frompylons=False):
        try:
            import pylons
        except ImportError:
            frompylons = False

        if frompylons:
            from pylons.templating import render_jinja2
            return render_jinja2('jinja_inherits.jinja')
        else:
            return render_template({}, 'jinja', 'jinja_inherits.jinja')

    @expose()
    def no_template_generator(self):
        def output():
            num = 0
            while num < 5:
                num += 1
                yield str(num).encode('ascii')
        return output()
    
    @expose()
    def genshi_manual_rendering_with_doctype(self, doctype=None):
        response.content_type = 'text/html'
        response.charset = 'utf-8'
        return render_template({}, 'genshi', 'genshi_doctype.html', doctype=doctype)

    @expose('mako:mako_custom_format.mak')
    @expose('genshi:genshi_custom_format.html')
    def multiple_engines(self):
        deco = Decoration.get_decoration(self.multiple_engines)
        used_engine = deco.engines.get('text/html')[0]
        return dict(format=used_engine, status='ok')

    @expose('json')
    def get_tg_vars(self):
        return dict(tg_vars=list(_get_tg_vars().keys()))

    @expose('genshi:index.html')
    def template_caching(self):
        from datetime import datetime
        tmpl_context.now = datetime.utcnow
        return dict(tg_cache={'key':'TEMPLATE_CACHE_TEST',
                              'type':'memory',
                              'expire':'never'})

    @expose('genshi:index.html')
    def template_caching_default_type(self):
        from datetime import datetime
        tmpl_context.now = datetime.utcnow
        return dict(tg_cache={'key':'TEMPLATE_CACHE_TEST2',
                              'expire':'never'})

    @expose('json')
    def template_caching_options(self, **kwargs):
        _cache_options = {}
        class FakeCache(object):
            def get_cache(self, *args, **kwargs):
                _cache_options['args'] = args
                _cache_options['kwargs'] = kwargs
                try:
                    c = cache.get_cache(*args, **kwargs)
                    _cache_options['cls'] = c.namespace.__class__.__name__
                except TypeError:
                    _cache_options['cls'] = 'NoImplementation'
                    c = cache.get_cache(*args, type='memory', **kwargs)
                return c

        tg.cache.kwargs['type'] = 'NoImplementation'
        old_cache = tg.cache
        tg.cache = FakeCache()

        try:
            def render_func(*args, **kw):
                return 'OK'
            cached_template('index.html', render_func, **kwargs)
            return _cache_options
        finally:
            tg.cache = old_cache

    @expose('jsonp', render_params={'callback_param': 'call'})
    def get_jsonp(self, **kwargs):
        return {'value': 5}
########NEW FILE########
__FILENAME__ = test_decorators
from tests.test_stack import TestConfig, app_from_config
from tg.util import no_warn
from tg.configuration import config
from tg.configuration import milestones
from tg.decorators import Decoration
import tg
import json

def make_app():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    return app_from_config(base_config)

class TestTGController(object):

    def setup(self):
        self.app = make_app()

    def test_simple_jsonification(self):
        resp = self.app.get('/j/json')
        expected = {"a": "hello world", "b": True}
        assert json.dumps(expected) in str(resp.body)

    def test_multi_dispatch_json(self):
        resp = self.app.get('/j/xml_or_json', headers={'accept':'application/json'})
        assert '''"status": "missing"''' in resp
        assert '''"name": "John Carter"''' in resp
        assert '''"title": "officer"''' in resp

    def test_json_with_object(self):
        resp = self.app.get('/j/json_with_object')
        assert '''"Json": "Rocks"''' in str(resp.body)

    @no_warn
    def test_json_with_bad_object(self):
        try:
            resp = self.app.get('/j/json_with_bad_object')
            assert False
        except Exception as e:
            assert "is not JSON serializable" in str(e), str(e)

    def test_multiple_engines(self):
        default_renderer = config['default_renderer']
        resp = self.app.get('/multiple_engines')
        assert default_renderer in resp, resp

class TestExposeInheritance(object):
    def setup(self):
        self.app = make_app()

    def test_inherited_expose_template(self):
        resp1 = self.app.get('/sub1/index')
        resp2 = self.app.get('/sub2/index')
        assert resp1.body == resp2.body

    def test_inherited_expose_override(self):
        resp1 = self.app.get('/sub1/index_override')
        resp2 = self.app.get('/sub2/index_override')
        assert resp1.body != resp2.body

    def test_inherited_expose_hooks(self):
        resp1 = self.app.get('/sub1/data')
        assert ('"v"' in resp1 and '"parent_value"' in resp1)
        resp2 = self.app.get('/sub2/data')
        assert ('"v"' in resp2 and '"parent_value"' in resp2 and '"child_value"' in resp2)


class TestExposeLazyInheritance(object):
    def test_lazy_inheritance(self):
        milestones.renderers_ready._reset()

        class BaseController(tg.TGController):
            @tg.expose('template.html')
            def func(self):
                pass

        class SubController(BaseController):
            @tg.expose(inherit=True)
            def func(self):
                pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(SubController.func)
        assert len(deco.engines) == 1, deco.engines
        assert deco.engines['text/html'][1] == 'template.html', deco.engines

    def test_lazy_inheritance_with_template(self):
        milestones.renderers_ready._reset()

        class BaseController(tg.TGController):
            @tg.expose('template.html')
            def func(self):
                pass

        class SubController(BaseController):
            @tg.expose('new_template.html', inherit=True)
            def func(self):
                pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(SubController.func)
        assert len(deco.engines) == 1, deco.engines
        assert deco.engines['text/html'][1] == 'new_template.html', deco.engines

    def test_lazy_inheritance_with_nested_template(self):
        milestones.renderers_ready._reset()

        class BaseController(tg.TGController):
            @tg.expose('template.html')
            @tg.expose('template.html', content_type='text/plain')
            def func(self):
                pass

        class SubController(BaseController):
            @tg.expose('new_template.html', inherit=True)
            @tg.expose('new_template.html', content_type='text/plain')
            def func(self):
                pass

        class SubSubController(SubController):
            @tg.expose('new2_template.html', inherit=True)
            def func(self):
                pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(SubSubController.func)
        assert len(deco.engines) == 2, deco.engines
        assert deco.engines['text/html'][1] == 'new2_template.html', deco.engines
        assert deco.engines['text/plain'][1] == 'new_template.html', deco.engines

    def test_lazy_inheritance_with_3nested_template(self):
        milestones.renderers_ready._reset()

        class BaseController(tg.TGController):
            @tg.expose('template.html')
            @tg.expose('template.html', content_type='text/plain')
            @tg.expose('template.html', content_type='text/javascript')
            def func(self):
                pass

        class SubController(BaseController):
            @tg.expose('new_template.html', inherit=True)
            @tg.expose('new_template.html', content_type='text/plain')
            @tg.expose('new_template.html', content_type='text/javascript')
            def func(self):
                pass

        class SubSubController(SubController):
            @tg.expose('new2_template.html', inherit=True)
            @tg.expose('new2_template.html', content_type='text/javascript')
            def func(self):
                pass

        class SubSubSubController(SubSubController):
            @tg.expose('new3_template.html', inherit=True)
            def func(self):
                pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(SubSubSubController.func)
        assert len(deco.engines) == 3, deco.engines
        assert deco.engines['text/html'][1] == 'new3_template.html', deco.engines
        assert deco.engines['text/plain'][1] == 'new_template.html', deco.engines
        assert deco.engines['text/javascript'][1] == 'new2_template.html', deco.engines

########NEW FILE########
__FILENAME__ = test_dotted_rendering
# -*- coding: utf-8 -*-

import sys
from nose import SkipTest
from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch, no_warn
from webtest import TestApp
from tg._compat import PY3, u_, im_func
from tg.configuration import milestones
from tg import expose
from tg.decorators import Decoration

try:
    from tgext.chameleon_genshi import ChameleonGenshiRenderer
except ImportError:
    ChameleonGenshiRenderer = None

def setup_noDB(extra_init=None):
    base_config = TestConfig(folder = 'rendering',
                     values = {'use_sqlalchemy': False,
                               # we want to test the new renderer functions
                               'use_legacy_renderer': False,
                               # in this test we want dotted names support
                               'use_dotted_templatenames': True,
                               'use_toscawidgets': False,
                               'use_toscawidgets2': False
                               }
                             )

    if extra_init is not None:
        extra_init(base_config)

    return app_from_config(base_config)

def test_default_chameleon_genshi_renderer():
    if ChameleonGenshiRenderer is None:
        raise SkipTest()

    def add_chameleon_renderer(app_config):
        app_config.register_rendering_engine(ChameleonGenshiRenderer)
        app_config.renderers.append('chameleon_genshi')

    app = setup_noDB(add_chameleon_renderer)

    # Manually add the exposition again as it was already discarded
    # due to chameleon_genshi not being in the available renderes.
    milestones.renderers_ready._reset()
    from .controllers.root import RootController
    controller = im_func(RootController.chameleon_index_dotted)
    expose('chameleon_genshi:tests.test_stack.rendering.templates.index')(controller)
    milestones.renderers_ready.reach()

    resp = app.get('/chameleon_index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_default_kajiki_renderer():
    if PY3: raise SkipTest()
    if '__pypy__' in sys.builtin_module_names: raise SkipTest()

    app = setup_noDB()
    resp = app.get('/kajiki_index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_jinja_dotted():
    app = setup_noDB()
    resp = app.get('/jinja_dotted')
    assert "move along, nothing to see here" in resp, resp

def test_jinja_inherits_dotted():
    app = setup_noDB()
    resp = app.get('/jinja_inherits_dotted')
    assert "Welcome on my awsome homepage" in resp, resp

def test_jinja_inherits_mixed():
    # Mixed notation, dotted and regular
    app = setup_noDB()
    resp = app.get('/jinja_inherits_mixed')
    assert "Welcome on my awsome homepage" in resp, resp

def test_jinja_i18n():
    app = setup_noDB()
    resp = app.get('/jinja_i18n', status=200)

def test_jinja_i18n_en():
    app = setup_noDB()
    resp = app.get('/jinja_i18n_en')
    assert "Your application is now running" in resp

def test_jinja_i18n_de():
    app = setup_noDB()
    resp = app.get('/jinja_i18n_de')
    assert u_("Ihre Anwendung läuft jetzt einwandfrei") in resp

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_dotted')
    assert "Inheritance template" in resp, resp
    assert "Master template" in resp, resp
 
def test_genshi_sub_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_dotted')
    assert "Inheritance template" in resp, resp
    assert "Master template" in resp, resp
    assert "from sub-template: sub.tobeincluded" in resp, resp

def test_genshi_sub_inheritance_frombottom():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_dotted_from_bottom')
    assert "Master template" in resp, resp
    assert "from sub-template: sub.frombottom_dotted" in resp, resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index_dotted')
    assert "<p>This is the mako index page</p>" in resp, resp

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits_dotted')
    assert "inherited mako page" in resp, resp
    assert "Inside parent template" in resp, resp


########NEW FILE########
__FILENAME__ = test_pagination
import json
from nose import SkipTest
from tests.test_stack import TestConfig, app_from_config
from tg.support.paginate import Page
from tg.controllers.util import _urlencode
from tg import json_encode

def setup_noDB():
    base_config = TestConfig(folder='rendering',
            values={
                'use_sqlalchemy': False,
                'use_toscawidgets': False,
                'use_toscawidgets2': False
            })
    return app_from_config(base_config)


_pager = ('<div id="pager"><span class="pager_curpage">1</span>'
    ' <a href="%(url)s?page=2">2</a>'
    ' <a href="%(url)s?page=3">3</a>'
    ' <span class="pager_dotdot">..</span>'
    ' <a href="%(url)s?page=5">5</a></div>')

_data = '<ul id="data">%s</ul>' % ''.join(
        '<li>%d</li>' % i for i in range(10))


class TestPagination:
    def setup(self):
        self.app = setup_noDB()

    def test_basic_pagination(self):
        url = '/paginated/42'
        page = self.app.get(url)
        assert _pager % locals() in page, page
        assert _data in page, page
        url = '/paginated/42?page=2'
        page = self.app.get(url)
        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page

    def test_pagination_negative(self):
        url = '/paginated/42?page=-1'
        page = self.app.get(url)
        assert '<li>0</li>' in page

    def test_pagination_items_per_page(self):
        url = '/paginated/42?items_per_page=20'
        page = self.app.get(url)
        assert '<li>0</li>' in page
        assert '<li>19</li>' in page

    def test_pagination_items_per_page_negative(self):
        url = '/paginated/42?items_per_page=-1'
        page = self.app.get(url)
        assert '<li>0</li>' in page
        assert '<li>10</li>' not in page

    def test_pagination_non_paginable(self):
        url = '/paginated_text'
        page = self.app.get(url)
        assert 'Some Text' in page

    def test_pagination_with_validation(self):
        url = '/paginated_validated/42'
        page = self.app.get(url)
        assert _pager % locals() in page, page
        assert _data in page, page
        url = '/paginated_validated/42?page=2'
        page = self.app.get(url)
        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page

    def test_validation_with_pagination(self):
        url = '/validated_paginated/42'
        page = self.app.get(url)
        assert _pager % locals() in page, page
        assert _data in page, page
        url = '/validated_paginated/42?page=2'
        page = self.app.get(url)
        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page

    def test_pagination_with_link_args(self):
        url = '/paginate_with_params/42'
        page = self.app.get(url)
        assert 'param1=hi' in page
        assert 'param2=man' in page
        assert 'partial' not in page
        assert '/fake_url' in page
        url = '/paginate_with_params/42?page=2'
        page = self.app.get(url)
        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page

    def test_multiple_paginators(self):
        url = '/multiple_paginators/42'
        goto_page2_params = _urlencode({'testdata2_page':2,
                                        'testdata_page':2})
        goto_page2_link = url + '?' + goto_page2_params

        page = self.app.get(url)
        assert '/multiple_paginators/42?testdata2_page=2' in page, str(page)
        assert '/multiple_paginators/42?testdata_page=2' in page, str(page)

        url = '/multiple_paginators/42?testdata_page=2'
        page = self.app.get(url)

        assert goto_page2_link in page, str(page)
        assert '/multiple_paginators/42?testdata_page=4' in page, str(page)

        assert '<li>0</li>' not in page
        assert '<li>10</li>' in page
        assert '<li>142</li>' in page
        assert '<li>151</li>' in page

        url = '/multiple_paginators/42?testdata2_page=2'
        page = self.app.get(url)

        assert goto_page2_link in page, str(page)
        assert '/multiple_paginators/42?testdata2_page=4' in page, str(page)

        assert '<li>0</li>' in page
        assert '<li>9</li>' in page
        assert '<li>151</li>' not in page
        assert '<li>161</li>' in page

    def test_json_pagination(self):
        url = '/paginated/42.json'
        page = self.app.get(url)
        assert '[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]' in page

        url = '/paginated/42.json?page=2'
        page = self.app.get(url)
        assert '[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]' in page


class TestPage(object):
    def test_not_a_number_page(self):
        p = Page(range(100), items_per_page=10, page='A')
        sec = list(p)
        assert sec[-1] == 9, sec

    def test_empty_list(self):
        p = Page([], items_per_page=10, page=1)
        assert list(p) == []

    def test_page_out_of_bound(self):
        p = Page(range(100), items_per_page=10, page=10000)
        sec = list(p)
        assert sec[-1] == 99, sec

    def test_page_out_of_lower_bound(self):
        p = Page(range(100), items_per_page=10, page=-5)
        sec = list(p)
        assert sec[-1] == 9, sec

    def test_navigator_one_page(self):
        p = Page(range(10), items_per_page=10, page=10)
        assert p.pager() == ''

    def test_navigator_middle_page(self):
        p = Page(range(100), items_per_page=10, page=5)
        pager = p.pager()

        assert '?page=1' in pager
        assert '?page=4' in pager
        assert '?page=6' in pager
        assert '?page=10' in pager

    def test_navigator_ajax(self):
        p = Page(range(100), items_per_page=10, page=5)
        pager = p.pager(onclick='goto($page)')

        assert 'goto(1)' in pager
        assert 'goto(4)' in pager
        assert 'goto(6)' in pager
        assert 'goto(10)' in pager


try:
    import sqlite3
except:
    import pysqlite2
from sqlalchemy import (MetaData, Table, Column, ForeignKey, Integer, String)
from sqlalchemy.orm import create_session, mapper, relation

metadata = MetaData('sqlite:///:memory:')

test1 = Table('test1', metadata,
    Column('id', Integer, primary_key=True),
    Column('val', String(8)))

test2 = Table('test2', metadata,
    Column('id', Integer, primary_key=True),
    Column('test1id', Integer, ForeignKey('test1.id')),
    Column('val', String(8)))

test3 = Table('test3', metadata,
    Column('id', Integer, primary_key=True),
    Column('val', String(8)))

test4 = Table('test4', metadata,
    Column('id', Integer, primary_key=True),
    Column('val', String(8)))

metadata.create_all()

class Test2(object):
    pass
mapper(Test2, test2)

class Test1(object):
    pass
mapper(Test1, test1, properties={'test2s': relation(Test2)})

class Test3(object):
    pass
mapper(Test3, test3)

class Test4(object):
    pass
mapper(Test4, test4)

test1.insert().execute({'id': 1, 'val': 'bob'})
test2.insert().execute({'id': 1, 'test1id': 1, 'val': 'fred'})
test2.insert().execute({'id': 2, 'test1id': 1, 'val': 'alice'})
test3.insert().execute({'id': 1, 'val': 'bob'})
test4.insert().execute({'id': 1, 'val': 'alberto'})

class TestPageSQLA(object):
    def setup(self):
        self.s = create_session()

    def test_relationship(self):
        t = self.s.query(Test1).get(1)
        p = Page(t.test2s, items_per_page=1, page=1)
        assert len(list(p)) == 1
        assert list(p)[0].val == 'fred', list(p)

    def test_query(self):
        q = self.s.query(Test2)
        p = Page(q, items_per_page=1, page=1)
        assert len(list(p)) == 1
        assert list(p)[0].val == 'fred', list(p)

    def test_json_query(self):
        q = self.s.query(Test2)
        p = Page(q, items_per_page=1, page=1)
        res = json.loads(json_encode(p))
        assert len(res['entries']) == 1
        assert res['total'] == 2
        assert res['entries'][0]['val'] == 'fred'


try:
    import ming
    from ming import create_datastore, Session, schema, ASCENDING
    from ming.odm import ODMSession, FieldProperty, ForeignIdProperty, RelationProperty, Mapper
    from ming.odm.declarative import MappedClass
except ImportError:
    ming = None


class TestPageMing(object):
    @classmethod
    def setupClass(cls):
        if ming is None:
            raise SkipTest('Ming not available...')

        cls.basic_session = Session(create_datastore('mim:///'))
        cls.s = ODMSession(cls.basic_session)

        class Author(MappedClass):
            class __mongometa__:
                session = cls.s
                name = 'wiki_author'

            _id = FieldProperty(schema.ObjectId)
            name = FieldProperty(str)
            pages = RelationProperty('WikiPage')

        class WikiPage(MappedClass):
            class __mongometa__:
                session = cls.s
                name = 'wiki_page'

            _id = FieldProperty(schema.ObjectId)
            title = FieldProperty(str)
            text = FieldProperty(str)
            order = FieldProperty(int)
            author_id = ForeignIdProperty(Author)
            author = RelationProperty(Author)

        cls.Author = Author
        cls.WikiPage = WikiPage
        Mapper.compile_all()

        cls.author = Author(name='author1')
        author2 = Author(name='author2')

        WikiPage(title='Hello', text='Text', order=1, author=cls.author)
        WikiPage(title='Another', text='Text', order=2, author=cls.author)
        WikiPage(title='ThirdOne', text='Text', order=3, author=author2)
        cls.s.flush()
        cls.s.clear()

    def teardown(self):
        self.s.clear()

    def test_query(self):
        q = self.WikiPage.query.find().sort([('order', ASCENDING)])
        p = Page(q, items_per_page=1, page=1)
        assert len(list(p)) == 1
        assert list(p)[0].title == 'Hello', list(p)

    def test_json_query(self):
        q = self.WikiPage.query.find().sort([('order', ASCENDING)])
        p = Page(q, items_per_page=1, page=1)
        res = json.loads(json_encode(p))
        assert len(res['entries']) == 1
        assert res['total'] == 3
        assert res['entries'][0]['title'] == 'Hello', res['entries']
        assert res['entries'][0]['author_id'] == str(self.author._id), res['entries']

    def test_relation(self):
        a = self.Author.query.find({'name': 'author1'}).first()
        p = Page(a.pages, items_per_page=1, page=1)
        assert len(list(p)) == 1
        assert list(p)[0].title in ('Hello', 'Another'), list(p)
########NEW FILE########
__FILENAME__ = test_rendering
# -*- coding: utf-8 -*-
from nose import SkipTest
import shutil, os
import json
import tg
from tg.configuration import milestones
#tg.configuration.reqlocal_config.push_process_config({})

from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from tg._compat import PY3, im_func
from tg.renderers.genshi import GenshiRenderer
from tg import expose
from tg import TGController, AppConfig
from webtest import TestApp

try:
    from tgext.chameleon_genshi import ChameleonGenshiRenderer
except ImportError:
    ChameleonGenshiRenderer = None

def setup_noDB(genshi_doctype=None, genshi_method=None, genshi_encoding=None, extra={},
               extra_init=None):
    base_config = TestConfig(folder='rendering', values={
        'use_sqlalchemy': False,
       'use_legacy_renderer': False,
       # this is specific to mako  to make sure inheritance works
       'use_dotted_templatenames': False,
       'use_toscawidgets': False,
       'use_toscawidgets2': False
    })

    deployment_config = {}
    # remove previous option value to avoid using the old one
    tg.config.pop('templating.genshi.doctype', None)
    if genshi_doctype:
        deployment_config['templating.genshi.doctype'] = genshi_doctype
    tg.config.pop('templating.genshi.method', None)
    if genshi_method:
        deployment_config['templating.genshi.method'] = genshi_method
    tg.config.pop('templating.genshi.encoding', None)
    if genshi_encoding:
        deployment_config['templating.genshi.encoding'] = genshi_encoding

    deployment_config.update(extra)

    if extra_init is not None:
        extra_init(base_config)

    return app_from_config(base_config, deployment_config)

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert "Welcome" in resp
    assert "TurboGears" in resp

def test_genshi_doctype_html5():
    app = setup_noDB(genshi_doctype='html5')
    resp = app.get('/')
    assert '<!DOCTYPE html>' in resp
    assert "Welcome" in resp
    assert "TurboGears" in resp

def test_genshi_auto_doctype():
    app = setup_noDB()
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_html():
    app = setup_noDB(genshi_method='html')
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"'
        ' "http://www.w3.org/TR/html4/loose.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xhtml():
    app = setup_noDB(genshi_method='xhtml')
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_html():
    app = setup_noDB(genshi_doctype='html')
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_html5():
    app = setup_noDB(genshi_doctype='html5')
    resp = app.get('/auto_doctype')
    assert '<!DOCTYPE html>' in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_xhtml_strict():
    app = setup_noDB(genshi_doctype='xhtml-strict')
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_html_maps_to_xhtml():
    app = setup_noDB(genshi_doctype={'text/html': ('xhtml', 'html')})
    resp = app.get('/auto_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_html_maps_to_xhtml():
    app = setup_noDB(genshi_method={'text/html': ('xhtml', 'html')})
    resp = app.get('/auto_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xml_overridden_by_content_type_html():
    app = setup_noDB(genshi_method='xml')
    resp = app.get('/auto_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xhtml_is_ok_with_content_type_html():
    app = setup_noDB(genshi_method='xhtml')
    resp = app.get('/auto_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_xhtml_maps_to_html():
    app = setup_noDB(
        genshi_doctype={'application/xhtml+xml': ('html', 'xhtml')})
    resp = app.get('/auto_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="application/xhtml+xml; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xhtml_maps_to_html():
    app = setup_noDB(
        genshi_doctype={'application/xhtml+xml': ('html', 'xhtml')},
        genshi_method={'application/xhtml+xml': ('html', 'xhtml')})
    resp = app.get('/auto_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="application/xhtml+xml; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xml_overridden_by_content_type_xhtml():
    app = setup_noDB(genshi_method='xml')
    resp = app.get('/auto_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="application/xhtml+xml; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_html_overridden_by_content_type_xhtml():
    app = setup_noDB(genshi_method='html')
    resp = app.get('/auto_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="application/xhtml+xml; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_explicit_no_doctype():
    app = setup_noDB()
    resp = app.get('/explicit_no_doctype')
    assert 'DOCTYPE' not in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_explicit_doctype_html():
    app = setup_noDB(genshi_doctype='xhtml')
    resp = app.get('/explicit_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_explicit_doctype_xhtml():
    app = setup_noDB(genshi_doctype='html')
    resp = app.get('/explicit_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_html_priority_for_ie():
    app = setup_noDB()
    resp = app.get('/html_and_json', headers={'Accept':
        'application/x-ms-application, image/jpeg, application/xaml+xml,'
        ' image/gif, image/pjpeg, application/x-ms-xbap, */*'})
    assert 'text/html' in str(resp), resp

def test_genshi_foreign_characters():
    app = setup_noDB()
    resp = app.get('/foreign')
    assert "Foreign Cuisine" in resp
    assert "Crème brûlée with Käsebrötchen" in resp

def test_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits')
    assert "Inheritance template" in resp
    assert "Master template" in resp

def test_genshi_sub_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub')
    assert "Inheritance template" in resp
    assert "Master template" in resp
    assert "from sub-template: sub.tobeincluded" in resp

def test_genshi_sub_inheritance_from_bottom():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_from_bottom')
    assert "from sub-template: sub.frombottom" in resp
    assert "Master template" in resp

def test_chameleon_genshi_base():
    if ChameleonGenshiRenderer is None:
        raise SkipTest()

    def add_chameleon_renderer(app_config):
        app_config.register_rendering_engine(ChameleonGenshiRenderer)
        app_config.renderers.append('chameleon_genshi')

    app = setup_noDB(extra_init=add_chameleon_renderer)

    # Manually add the exposition again as it was already discarded
    # due to chameleon_genshi not being in the available renderes.
    milestones.renderers_ready._reset()
    from .controllers.root import RootController
    controller = im_func(RootController.chameleon_genshi_index)
    expose('chameleon_genshi:index.html')(controller)
    milestones.renderers_ready.reach()

    resp = app.get('/chameleon_genshi_index')
    assert ("<p>TurboGears 2 is rapid web application development toolkit"
        " designed to make your life easier.</p>") in resp

def test_chameleon_genshi_inheritance():
    if ChameleonGenshiRenderer is None:
        raise SkipTest()

    def add_chameleon_renderer(app_config):
        app_config.register_rendering_engine(ChameleonGenshiRenderer)
        app_config.renderers.append('chameleon_genshi')

    try:
        import lxml
    except ImportError:
        # match templates need lxml, but since they don're really work anyway
        # (at least not fully compatible with Genshi), we just skip this test
        return

    app = setup_noDB(extra_init=add_chameleon_renderer)

    milestones.renderers_ready._reset()
    from .controllers.root import RootController
    controller = im_func(RootController.chameleon_genshi_inherits)
    expose('chameleon_genshi:genshi_inherits.html')(controller)
    milestones.renderers_ready.reach()

    try:
        resp = app.get('/chameleon_genshi_inherits')
    except NameError as e:
        # known issue with chameleon.genshi 1.0
        if 'match_templates' not in str(e):
            raise
    except AttributeError as e:
        # known issue with chameleon.genshi 1.3
        if 'XPathResult' not in str(e):
            raise
    else:
        assert "Inheritance template" in resp
        assert "Master template" in resp

def test_jinja_autoload():
    app = setup_noDB()

    try:
        resp = app.get('/jinja_autoload')
        assert False
    except Exception as e:
        assert "no filter named 'polluting_function'" in str(e)

def _test_jinja_inherits():
    app = setup_noDB()
    resp = app.get('/jinja_inherits')
    assert "Welcome on my awsome homepage" in resp, resp

def test_jinja_extensions():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'renderers':['jinja'],
                                       'jinja_extensions': ['jinja2.ext.do', 'jinja2.ext.i18n',
                                                            'jinja2.ext.with_', 'jinja2.ext.autoescape'],
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)
    resp = app.get('/jinja_extensions')
    assert "<b>Autoescape Off</b>" in resp, resp
    assert "&lt;b&gt;Test Autoescape On&lt;/b&gt;" in resp, resp

def test_jinja_buildin_filters():
    app = setup_noDB()
    resp = app.get('/jinja_buildins')
    assert 'HELLO JINJA!' in resp, resp

def test_jinja_custom_filters():
    # Simple test filter to get a md5 hash of a string
    def codify(value):
        try:
            from hashlib import md5
        except ImportError:
            from md5 import md5
        string_hash = md5(value.encode('ascii'))
        return string_hash.hexdigest()

    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'renderers':['jinja'],
                                       'jinja_filters': {'codify': codify},
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)

    try:
        resp = app.get('/jinja_filters')
    finally:
        # Remove filters so we don't mess with other test units
        tg.config.pop('jinja_filters')

    assert '8bb23e0b574ecb147536efacc864891b' in resp, resp

def test_jinja_autoload_filters():
    app = setup_noDB()
    resp = app.get('/jinja_filters')
    assert '29464d5ffe8f8dba1782fffcd6ed9fca6ceb4742' in resp, resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index')
    assert "<p>This is the mako index page</p>" in resp, resp

def test_mako_renderer_compiled():
    tg.config['templating.mako.compiled_templates_dir'] = '_tg_tests_mako_compiled/dest'
    app = setup_noDB()
    resp = app.get('/mako_index')
    tg.config.pop('templating.mako.compiled_templates_dir')
    assert "<p>This is the mako index page</p>" in resp, resp

    assert os.path.exists('_tg_tests_mako_compiled')
    shutil.rmtree('_tg_tests_mako_compiled', True)

def test_mako_renderer_compiled_existing():
    os.makedirs('_tg_tests_mako_compiled/dest')
    test_mako_renderer_compiled()

def test_mako_renderer_compiled_no_access():
    os.makedirs('_tg_tests_mako_compiled')
    os.makedirs('_tg_tests_mako_compiled/dest', mode=0o400)
    test_mako_renderer_compiled()

def test_mako_renderer_compiled_no_access_parent():
    os.makedirs('_tg_tests_mako_compiled', mode=0o400)
    test_mako_renderer_compiled()

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits')
    assert "inherited mako page" in resp, resp
    assert "Inside parent template" in resp, resp

def test_template_override():
#    app = setup_noDB()
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'renderers':['genshi'],
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)
    r =app.get('/template_override')
    assert "Not overridden" in r, r
    r = app.get('/template_override', params=dict(override=True))
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override')
    assert "Not overridden" in r, r

def test_template_override_wts():
#    app = setup_noDB()
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'renderers':['genshi'],
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)
    r = app.get('/template_override_wts', status=301) # ensure with_trailing_slash
    r =app.get('/template_override_wts/')
    assert "Not overridden" in r, r
    r = app.get('/template_override_wts/', params=dict(override=True))
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override_wts/')
    assert "Not overridden" in r, r

def test_template_override_content_type():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'renderers':['mako', 'genshi'],
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)
    r =app.get('/template_override_content_type')
    assert r.content_type == 'text/javascript'
    assert "Not overridden" in r, r
    r = app.get('/template_override_content_type', params=dict(override=True))
    assert r.content_type == 'text/javascript'
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override_content_type')
    assert "Not overridden" in r, r

def test_template_custom_format_default():
    app = setup_noDB()
    resp = app.get('/custom_format')
    assert 'OK' in resp
    assert resp.content_type == 'text/html'

def test_template_custom_format_xml():
    app = setup_noDB()
    resp = app.get('/custom_format?format=xml')
    assert 'xml' in resp
    assert resp.content_type == 'text/xml'

def test_template_custom_format_json():
    app = setup_noDB()
    resp = app.get('/custom_format?format=json')
    assert 'json' in resp
    assert resp.content_type == 'application/json'

def test_template_custom_format_html():
    app = setup_noDB()
    resp = app.get('/custom_format?format=html')
    assert 'html' in resp
    assert resp.content_type == 'text/html'

def test_template_custom_format_nonexisting():
    app = setup_noDB()

    try:
        resp = app.get('/custom_format?format=csv')
        assert False
    except Exception as e:
        assert 'not a valid custom_format' in str(e)

def test_template_override_multiple_content_type():
    app = setup_noDB()
    resp = app.get('/template_override_multiple_content_type')
    assert 'something' in resp

    resp = app.get(
        '/template_override_multiple_content_type',
        params=dict(override=True))
    assert 'This is the mako index page' in resp

def test_override_template_on_noncontroller():
    tg.override_template(None, 'this.is.not.a.template')

def test_jinja2_manual_rendering():
    app = setup_noDB()
    tgresp = app.get('/jinja2_manual_rendering')
    pyresp = app.get('/jinja2_manual_rendering?frompylons=1')
    assert str(tgresp) == str(pyresp), str(tgresp) + '\n------\n' + str(pyresp)

def test_no_template():
    app = setup_noDB()
    resp = app.get('/no_template_generator')
    assert '1234' in resp, resp

def test_genshi_manual_render_no_doctype():
    app = setup_noDB()
    resp = app.get('/genshi_manual_rendering_with_doctype')
    assert 'DOCTYPE' not in resp, resp
    assert "<hr />" in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_manual_render_auto_doctype():
    app = setup_noDB()
    resp = app.get('/genshi_manual_rendering_with_doctype?doctype=auto')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_manual_render_html_doctype():
    app = setup_noDB()
    resp = app.get('/genshi_manual_rendering_with_doctype?doctype=html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_manual_render_svg_doctype():
    app = setup_noDB()
    resp = app.get('/genshi_manual_rendering_with_doctype?doctype=svg')
    assert '<!DOCTYPE svg' in resp

def test_genshi_methods_for_doctype():
    assert GenshiRenderer.method_for_doctype('application/xml') == 'xhtml'

def test_variable_provider():
    app = setup_noDB(extra={'variable_provider': lambda: {'inject_this_var':5}})
    resp = app.get('/get_tg_vars')
    assert 'inject_this_var' in resp

def test_render_hooks():
    calls = []
    def render_call_hook(*args, **kw):
        calls.append(1)

    base_config = TestConfig(folder='rendering', values={
        'use_sqlalchemy': False,
        'use_legacy_renderer': False,
        # this is specific to mako  to make sure inheritance works
        'use_dotted_templatenames': False,
        'use_toscawidgets': False,
        'use_toscawidgets2': False
    })

    milestones._reset_all()
    base_config.register_hook('before_render_call', render_call_hook)
    base_config.register_hook('after_render_call', render_call_hook)
    app = app_from_config(base_config, reset_milestones=False)
    app.get('/')

    assert len(calls) == 2

class TestTemplateCaching(object):
    def setUp(self):
        base_config = TestConfig(folder='rendering', values={
            'use_sqlalchemy': False,
            'use_legacy_renderer': False,
            # this is specific to mako  to make sure inheritance works
            'use_dotted_templatenames': False,
            'use_toscawidgets': False,
            'use_toscawidgets2': False,
            'cache_dir': '.'
        })
        self.app = app_from_config(base_config)

    def test_basic(self):
        resp = self.app.get('/template_caching')
        current_date = resp.text.split('NOW:')[1].split('\n')[0].strip()

        resp = self.app.get('/template_caching')
        assert current_date in resp, (current_date, resp.body)

    def test_default_type(self):
        resp = self.app.get('/template_caching_default_type')
        current_date = resp.text.split('NOW:')[1].split('\n')[0].strip()

        resp = self.app.get('/template_caching_default_type')
        assert current_date in resp, (current_date, resp.body)

    def test_template_caching_options(self):
        resp = self.app.get('/template_caching_options', params={'cache_type':'memory'})
        resp = json.loads(resp.text)
        assert resp['cls'] == 'MemoryNamespaceManager', resp

        resp = self.app.get('/template_caching_options', params={'cache_expire':1})
        resp = json.loads(resp.text)
        assert resp['cls'] == 'NoImplementation', resp

        resp = self.app.get('/template_caching_options', params={'cache_key':'TEST'})
        resp = json.loads(resp.text)
        assert resp['cls'] == 'NoImplementation', resp

    def test_jsonp(self):
        resp = self.app.get('/get_jsonp', params={'call': 'callme'})
        assert 'callme({"value": 5});' in resp.text, resp

    def test_jsonp_missing_callback(self):
        resp = self.app.get('/get_jsonp', status=400)
        assert 'JSONP requires a "call" parameter with callback name' in resp.text, resp
########NEW FILE########
__FILENAME__ = test_toscawidgets
from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp

from nose import SkipTest
from tg._compat import PY3


def setup_noDB(prefer_tw2=False):

    base_config = TestConfig(folder = 'rendering',
                     values = {'use_sqlalchemy': False,
                               # we want to test the new renderer functions
                               'use_legacy_renderer': False,
                               # in this test we want dotted names support
                               'use_dotted_templatenames': False,
                               'templating.genshi.method':'xhtml',
                               'prefer_toscawidgets2':prefer_tw2
                               }
                             )
    return app_from_config(base_config)


expected_fields = ['name="year"', 'name="title"']

def test_basic_form_rendering():
    if PY3: raise SkipTest()

    app = setup_noDB()
    resp = app.get('/form')
    assert "form" in resp

    for expected_field in expected_fields:
        assert expected_field in resp, resp

def test_tw2_form_rendering():
    if PY3: raise SkipTest()

    app = setup_noDB(prefer_tw2=True)
    resp = app.get('/tw2form')
    assert "form" in resp

    for expected_field in expected_fields:
        assert expected_field in resp, resp

########NEW FILE########
__FILENAME__ = test_authz
# -*- coding: utf-8 -*-
"""
repoze.who **integration** tests.

Note that it is not necessary to have integration tests for the other auth*
software in this package. They must be in tg.devtools, specifically in the test
suite of the quickstarted applications (and there's where they are, as of
this writing).

"""

from unittest import TestCase
from shutil import rmtree
import os

from tg._compat import url_unquote

from tg.support.registry import RegistryManager
from webob import Response, Request
from webtest import TestApp

from tg import request, response, expose, require
from tg.controllers import TGController, WSGIAppController, RestController
from tg.controllers.util import abort
from tg.wsgiapp import ContextObj, TGApp
from tg.support.middlewares import CacheMiddleware, SessionMiddleware, StatusCodeRedirect
from tg.decorators import Decoration

from .baseutils import ControllerWrap, FakeRoutes, default_config

from tg.configuration.auth import setup_auth, TGAuthMetadata
from tg.predicates import is_user, not_anonymous, in_group, has_permission

from tg.error import ErrorHandler

#{ AUT's setup
NOT_AUTHENTICATED = "The current user must have been authenticated"

data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'session')

# Just in case...
rmtree(session_dir, ignore_errors=True)


class TestAuthMetadata(TGAuthMetadata):
    """
    Provides a way to lookup for user, groups and permissions
    given the current identity. This has to be specialized
    for each storage backend.

    By default it returns empty lists for groups and permissions
    and None for the user.
    """
    def get_user(self, identity, userid):
        if ':' in userid:
            return userid.split(':')[0]

        return super(TestAuthMetadata, self).get_user(identity, userid)

    def get_groups(self, identity, userid):
        if userid:
            parts = userid.split(':')
            return parts[1:2]

        return super(TestAuthMetadata, self).get_groups(identity, userid)

    def get_permissions(self, identity, userid):
        if userid:
            parts = userid.split(':')
            return parts[2:]

        return super(TestAuthMetadata, self).get_permissions(identity, userid)


def make_app(controller_klass, environ={}, with_errors=False):
    """Creates a ``TestApp`` instance."""
    # The basic middleware:
    app = TGApp(config=default_config)
    app.controller_classes['root'] = ControllerWrap(controller_klass)

    app = FakeRoutes(app)
    
    if with_errors:
        app = ErrorHandler(app, {}, debug=False)
        app = StatusCodeRedirect(app, [403, 404, 500])
    app = RegistryManager(app)
    app = SessionMiddleware(app, {}, data_dir=session_dir)
    app = CacheMiddleware(app, {}, data_dir=os.path.join(data_dir, 'cache'))

    # Setting repoze.who up:
    from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
    cookie = AuthTktCookiePlugin('secret', 'authtkt')
    identifiers = [('cookie', cookie)]

    app = setup_auth(app, TestAuthMetadata(),
                     identifiers=identifiers, skip_authentication=True,
                     authenticators=[], challengers=[])

    return TestApp(app)


#{ Mock objects


def wsgi_app(environ, start_response):
    """Mock WSGI application"""
    req = Request(environ)
    resp = Response("Hello from %s" % req.script_name + req.path_info)
    return resp(environ, start_response)


class DaRestController(RestController):
    """Mock REST controller"""

    allow_only = is_user('gustavo')

    @expose()
    def new(self):
        return "new here"


class HRManagementController(TGController):
    """Mock TG2 protected controller using the .allow_only attribute"""

    allow_only = is_user('hiring-manager')

    @expose()
    def index(self):
        return 'you can manage Human Resources'

    @expose()
    def hire(self, person_name):
        return "%s was just hired" % person_name


class ControlPanel(TGController):
    """Mock TG2 protected controller using @allow_only directly."""

    hr = HRManagementController()
    allow_only = not_anonymous()

    @expose()
    def index(self):
        return 'you are in the panel'

    @expose()
    @require(is_user('admin'))
    def add_user(self, user_name):
        return "%s was just registered" % user_name

class CustomAllowOnly(TGController):
    class something(object):
        def check_authorization(self, env):
            from tg.controllers.decoratedcontroller import NotAuthorizedError
            raise NotAuthorizedError()

    @expose()
    def index(self):
        return 'HI'

    allow_only = something()

class SmartDenialAllowOnly(TGController):
    allow_only = require(is_user('developer'), smart_denial=True)

    @expose('json')
    def data(self):
        return {'key': 'value'}

class RootController(TGController):
    custom_allow = CustomAllowOnly()
    smart_allow = SmartDenialAllowOnly()
    cp = ControlPanel()

    rest = DaRestController()

    mounted_app = WSGIAppController(wsgi_app, allow_only=is_user('gustavo'))

    @expose()
    def index(self):
        return "you're in the main page"

    @expose()
    @require(is_user('developer'))
    def commit(self):
        return 'you can commit'

    @expose('json:')
    @require(is_user('developer'), smart_denial=True)
    def smartabort(self):
        return {'key': 'value'}

    @expose()
    @require(in_group('managers'))
    @require(has_permission('commit'))
    def force_commit(self):
        return 'you can commit'


class ControllerWithAllowOnlyAttributeAndAuthzDenialHandler(TGController):
    """Mock TG2 protected controller using the .allow_only attribute"""

    allow_only = is_user('foobar')

    @expose()
    def index(self):
        return 'Welcome back, foobar!'

    @classmethod
    def _failed_authorization(self, reason):
        # Pay first!
        abort(402)


#{ The tests themselves


class BaseIntegrationTests(TestCase):
    """Base test case for the integration tests"""

    controller = RootController

    def setUp(self):
        # Creating the session dir:
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)

        # Setting TG2 up:
        self.app = make_app(self.controller, {})

    def tearDown(self):
        # Removing the session dir:
        rmtree(session_dir, ignore_errors=True)

    def _check_flash(self, response, *expected_messages):
        """
        Check that ``expected_messages`` are defined in the WebFlash cookie.

        """
        assert 'webflash' in response.cookies_set, "Such no WebFlash cookie"
        flash = url_unquote(response.cookies_set['webflash'])
        for msg in expected_messages:
            msg = '"%s"' % msg
            assert msg in flash, 'Message %s not in flash: %s' % (msg, flash)


class TestRequire(BaseIntegrationTests):
    """Test case for the @require decorator"""

    def test_authz_custom_allow_only(self):
        #environ = {'REMOTE_USER': 'developer'}
        resp = self.app.get('/custom_allow', extra_environ={}, status=401)

    def test_authz_granted_in_root_controller(self):
        environ = {'REMOTE_USER': 'developer'}
        resp = self.app.get('/commit', extra_environ=environ, status=200)
        self.assertEqual("you can commit", resp.body.decode('utf-8'))

    def test_multiple_requirements_passed(self):
        environ = {'REMOTE_USER': 'developer:managers:commit'}
        resp = self.app.get('/force_commit', extra_environ=environ, status=200)
        self.assertEqual("you can commit", resp.text)

    def test_multiple_requirements_blocked_1(self):
        environ = {'REMOTE_USER': 'tester:testing:commit'}
        resp = self.app.get('/force_commit', extra_environ=environ, status=403)
        assert 'The current user must belong to the group "managers"' in resp.text, resp.text

    def test_multiple_requirements_blocked_2(self):
        environ = {'REMOTE_USER': 'manager:managers:viewonly'}
        resp = self.app.get('/force_commit', extra_environ=environ, status=403)
        assert 'The user must have the "commit" permission' in resp.text, resp.text

    def test_multiple_requirements_all_registered(self):
        deco = Decoration.get_decoration(RootController.force_commit)
        assert len(deco.requirements) == 2, deco.requirements

    def test_multiple_requirements_backward_compatibility(self):
        deco = Decoration.get_decoration(RootController.force_commit)
        predicate = deco.requirement.predicate
        assert isinstance(predicate, has_permission), predicate

    def test_authz_denied_in_root_controller(self):
        # As an anonymous user:
        resp = self.app.get('/commit', status=401)
        assert "you can commit" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"developer\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/commit', extra_environ=environ, status=403)
        assert "you can commit" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"developer\"')

    def test_authz_granted_in_sub_controller(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body.decode('utf-8'))

    def test_authz_denied_in_sub_controller(self):
        # As an anonymous user:
        resp = self.app.get('/cp/add_user/foo', status=401)
        assert "was just registered" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)
        # As an authenticated user:
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=403)
        assert "was just registered" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"admin\"')

    def test_smart_auth_json(self):
        nouser = {'accept': 'application/json'}
        baduser = {'accept': 'application/json',
                'REMOTE_USER': 'foobar'}
        gooduser = {'accept': 'application/json',
                'REMOTE_USER': 'developer'}

        resp = self.app.get('/smartabort.json', extra_environ=nouser, status=401)
        assert resp.status == '401 Unauthorized', 'Expected 401, got %s' % (resp.status)
        assert 'The current user must be "developer"' in resp.json['detail']

        resp = self.app.get('/smartabort.json', extra_environ=baduser, status=403)
        assert resp.status == '403 Forbidden', 'Expected 403, got %s' % (resp.status)
        assert 'The current user must be "developer"' in resp.json['detail']

        resp = self.app.get('/smartabort.json', extra_environ=gooduser, status=200)
        assert resp.status == '200 OK', 'Expected 200, got %s' % (resp.body)
        assert {'key': 'value'} == resp.json, resp.json

    def test_smart_auth_json_allow_only(self):
        nouser = {'accept': 'application/json'}
        baduser = {'accept': 'application/json',
                'REMOTE_USER': 'foobar'}
        gooduser = {'accept': 'application/json',
                'REMOTE_USER': 'developer'}

        resp = self.app.get('/smart_allow/data.json', extra_environ=nouser, status=401)
        assert resp.status == '401 Unauthorized', 'Expected 401, got %s' % (resp.status)
        assert 'The current user must be "developer"' in resp.json['detail']

        resp = self.app.get('/smart_allow/data.json', extra_environ=baduser, status=403)
        assert resp.status == '403 Forbidden', 'Expected 403, got %s' % (resp.status)
        assert 'The current user must be "developer"' in resp.json['detail']

        resp = self.app.get('/smart_allow/data.json', extra_environ=gooduser, status=200)
        assert resp.status == '200 OK', 'Expected 200, got %s' % (resp.body)
        assert {'key': 'value'} == resp.json, resp.json


class TestAllowOnlyDecoratorInSubController(BaseIntegrationTests):
    """Test case for the @allow_only decorator in a sub-controller"""

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/cp/', extra_environ=environ, status=200)
        self.assertEqual("you are in the panel", resp.body.decode('utf-8'))

    def test_authz_denied_without_require(self):
        resp = self.app.get('/cp/', status=401)
        assert "you are in the panel" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body.decode('utf-8'))

    def test_authz_denied_with_require(self):
        resp = self.app.get('/cp/add_user/foo', status=401)
        assert "was just registered" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)

class TestAllowOnlyAttributeInSubController(BaseIntegrationTests):
    """Test case for the .allow_only attribute in a sub-controller"""

    controller = ControlPanel

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hr/', extra_environ=environ, status=200)
        self.assertEqual("you can manage Human Resources", resp.body.decode('utf-8'))

    def test_authz_denied_without_require(self):
        # As an anonymous user:
        resp = self.app.get('/hr/', status=401)
        assert "you can manage Human Resources" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must have been authenticated')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hr/', extra_environ = environ, status=403)
        assert "you can manage Human Resources" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hr/hire/gustavo', extra_environ=environ,
                            status=200)
        self.assertEqual("gustavo was just hired", resp.body.decode('utf-8'))

    def test_authz_denied_with_require(self):
        # As an anonymous user:
        resp = self.app.get('/hr/hire/gustavo', status=401)
        assert "was just hired" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must have been authenticated')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hr/hire/gustavo', extra_environ = environ, status=403)
        assert "was just hired" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')

class TestAllowOnlyAttributeAndDefaultAuthzDenialHandler(BaseIntegrationTests):
    """
    Test case for the .allow_only attribute in a controller using
    _failed_authorization() as its denial handler.

    """

    controller = ControllerWithAllowOnlyAttributeAndAuthzDenialHandler

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("Welcome back, foobar!", resp.body.decode('utf-8'))

    def test_authz_denied(self):
        resp = self.app.get('/', status=402)
        assert "Welcome back" not in resp.body.decode('utf-8')

class TestAppWideAuthzWithAllowOnlyDecorator(BaseIntegrationTests):
    """Test case for application-wide authz with the @allow_only decorator"""

    controller = ControlPanel

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("you are in the panel", resp.body.decode('utf-8'))

    def test_authz_denied_without_require(self):
        resp = self.app.get('/', status=401)
        assert "you are in the panel" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body.decode('utf-8'))

    def test_authz_denied_with_require(self):
        resp = self.app.get('/add_user/foo', status=401)
        assert "was just registered" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)


class TestAppWideAuthzWithAllowOnlyAttribute(BaseIntegrationTests):
    """Test case for application-wide authz with the .allow_only attribute"""

    controller = HRManagementController

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("you can manage Human Resources", resp.body.decode('utf-8'))

    def test_authz_denied_without_require(self):
        # As an anonymous user:
        resp = self.app.get('/', status=401)
        assert "you can manage Human Resources" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/', extra_environ = environ, status=403)
        assert "you can manage Human Resources" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hire/gustavo', extra_environ=environ,
                            status=200)
        self.assertEqual("gustavo was just hired", resp.body.decode('utf-8'))

    def test_authz_denied_with_require(self):
        # As an anonymous user:
        resp = self.app.get('/hire/gustavo', status=401)
        assert "was just hired" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hire/gustavo', extra_environ = environ, status=403)
        assert "was just hired" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')


class TestProtectedRESTContoller(BaseIntegrationTests):
    """Test case for protected REST controllers"""

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'gustavo'}
        resp = self.app.get('/rest/new', extra_environ=environ,
                            status=200)
        self.assertEqual("new here", resp.body.decode('utf-8'))

    def test_authz_denied(self):
        # As an anonymous user:
        resp = self.app.get('/rest/new', status=401)
        assert "new here" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"gustavo\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'non-gustavo'}
        resp = self.app.get('/rest/new', extra_environ=environ, status=403)
        assert "new here" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"gustavo\"')


class TestProtectedWSGIApplication(BaseIntegrationTests):
    """Test case for protected WSGI applications mounted on the controller"""

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'gustavo'}
        resp = self.app.get('/mounted_app/da-path', extra_environ=environ,
                            status=200)
        self.assertEqual("Hello from /mounted_app/da-path", resp.body.decode('utf-8'))

    def test_authz_denied(self):
        # As an anonymous user:
        resp = self.app.get('/mounted_app/da-path', status=401)
        assert "Hello from /mounted_app/" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"gustavo\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'non-gustavo'}
        resp = self.app.get('/mounted_app/da-path', extra_environ=environ,
                            status=403)
        assert "Hello from /mounted_app/" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"gustavo\"')

class ErrorController(object):
    @expose()
    def document(self, *args, **kwargs):
        return request.environ.get('repoze.who.identity')['repoze.who.userid']

class DefaultLessTGController(TGController):
    error = ErrorController()

    @expose()
    def index(self):
        return request.environ.get('repoze.who.identity')['repoze.who.userid']

class TestLoggedErrorTGController(BaseIntegrationTests):
    def setUp(self):
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)

        # Setting TG2 up:
        self.app = make_app(DefaultLessTGController, {}, with_errors=True)

    def test_logged_index(self):
        resp = self.app.get('/index', extra_environ={'REMOTE_USER': 'gustavo'}, expect_errors=True)
        assert 'gustavo' in resp

    def test_logged_error(self):
        resp = self.app.get('/missing_page_for_sure', extra_environ={'REMOTE_USER': 'gustavo'}, expect_errors=True)
        assert 'gustavo' in resp 
        
#}

########NEW FILE########
__FILENAME__ = test_registry
# (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
from nose.tools import raises

from webtest import TestApp
from tg.support.registry import RegistryManager, StackedObjectProxy, DispatchingConfig
from tg.util import Bunch

regobj = StackedObjectProxy()
secondobj = StackedObjectProxy(default=dict(hi='people'))

def simpleapp(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    return ['Hello world!\n'.encode('utf-8')]

def simpleapp_withregistry(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    return [('Hello world!Value is %s\n' % regobj.keys()).encode('utf-8')]

def simpleapp_withregistry_default(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    return [('Hello world!Value is %s\n' % secondobj).encode('utf-8')]

class RegistryUsingApp(object):
    def __init__(self, var, value, raise_exc=False):
        self.var = var
        self.value = value
        self.raise_exc = raise_exc

    def __call__(self, environ, start_response):
        if 'paste.registry' in environ:
            environ['paste.registry'].register(self.var, self.value)
        if self.raise_exc:
            raise self.raise_exc
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return [('Hello world!\nThe variable is %s' % str(regobj)).encode('utf-8')]

class RegistryUsingIteratorApp(object):
    def __init__(self, var, value):
        self.var = var
        self.value = value

    def __call__(self, environ, start_response):
        if 'paste.registry' in environ:
            environ['paste.registry'].register(self.var, self.value)
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return iter([('Hello world!\nThe variable is %s' % str(regobj)).encode('utf-8')])

class RegistryMiddleMan(object):
    def __init__(self, app, var, value, depth):
        self.app = app
        self.var = var
        self.value = value
        self.depth = depth

    def __call__(self, environ, start_response):
        if 'paste.registry' in environ:
            environ['paste.registry'].register(self.var, self.value)
        app_response = [('\nInserted by middleware!\nInsertValue at depth \
            %s is %s' % (self.depth, str(regobj))).encode('utf-8')]
        app_iter = None
        app_iter = self.app(environ, start_response)
        if type(app_iter) in (list, tuple):
            app_response.extend(app_iter)
        else:
            response = []
            for line in app_iter:
                response.append(line)
            if hasattr(app_iter, 'close'):
                app_iter.close()
            app_response.extend(response)
        app_response.extend([('\nAppended by middleware!\nAppendValue at \
            depth %s is %s' % (self.depth, str(regobj))).encode('utf-8')])
        return app_response

def test_stacked_object_dir():
    regobj._push_object({'hi':'people'})
    try:
        values = dir(regobj)
        assert 'hi' in repr(regobj)
    finally:
        regobj._pop_object()

    assert '_current_obj' in values
    assert 'pop' in values
    assert 'items' in values

def test_stacked_object_dir_fail():
    values = dir(regobj)
    assert '_current_obj' in values

    assert repr(regobj).startswith('<tg.support.registry.StackedObjectProxy')

def test_stacked_object_callable():
    class Callable(object):
        def __call__(self, w):
            return w

    regobj._push_object(Callable())
    try:
        assert regobj('HI') == 'HI'
    finally:
        regobj._pop_object()

def test_stacked_object_common_actions():
    regobj._push_object(Bunch({'hi':'people'}))
    try:
        regobj['hi'] = 'val'
        assert regobj['hi'] == 'val'

        keys = []
        for k in regobj:
            keys.append(k)
        assert keys == ['hi'], keys

        assert len(regobj) == 1

        assert 'hi' in regobj

        assert bool(regobj) == True

        del regobj['hi']
        assert regobj.get('hi') is None

        regobj.someattr = 'val'
        assert regobj.someattr == 'val'

        del regobj.someattr
        assert getattr(regobj, 'someattr', None) is None
    finally:
        regobj._pop_object()

@raises(AssertionError)
def test_stacked_object_pop_something_else():
    o = Bunch({'hi':'people'})
    regobj._push_object(o)
    regobj._pop_object({'another':'object'})

@raises(AssertionError)
def test_stacked_object_pop_never_registered():
    regobj._pop_object()

def test_stacked_object_stack():
    so = StackedObjectProxy()

    assert(len(so._object_stack()) == 0)
    so._push_object({'hi':'people'})
    assert(len(so._object_stack()) == 1)
    so._pop_object()
    assert(len(so._object_stack()) == 0)

def test_stacked_object_preserve_empty():
    so = StackedObjectProxy()
    so._preserve_object()

    so._push_object({'hi':'people'})
    so._pop_object()
    so._preserve_object()

def test_stacked_object_preserved():
    so = StackedObjectProxy()
    assert not so._is_preserved

    so._push_object({'hi':'people'})
    assert not so._is_preserved

    so._pop_object()
    assert not so._is_preserved

    so._push_object({'hi':'people'})
    so._preserve_object()
    assert so._is_preserved
    so._pop_object()

def test_simple():
    app = TestApp(simpleapp)
    response = app.get('/')
    assert 'Hello world' in response

def test_solo_registry():
    obj = {'hi':'people'}
    wsgiapp = RegistryUsingApp(regobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res

@raises(TypeError)
def test_registry_no_object_error():
    app = TestApp(simpleapp_withregistry)
    app.get('/')

def test_with_default_object():
    app = TestApp(simpleapp_withregistry_default)
    res = app.get('/')
    assert 'Hello world' in res
    assert "Value is {'hi': 'people'}" in res

def test_double_registry():
    obj = {'hi':'people'}
    secondobj = {'bye':'friends'}
    wsgiapp = RegistryUsingApp(regobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    wsgiapp = RegistryMiddleMan(wsgiapp, regobj, secondobj, 0)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    assert "InsertValue at depth 0 is {'bye': 'friends'}" in res
    assert "AppendValue at depth 0 is {'bye': 'friends'}" in res

def test_really_deep_registry():
    keylist = ['fred', 'wilma', 'barney', 'homer', 'marge', 'bart', 'lisa',
               'maggie']
    valuelist = range(0, len(keylist))
    obj = {'hi':'people'}
    wsgiapp = RegistryUsingApp(regobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    for depth in valuelist:
        newobj = {keylist[depth]: depth}
        wsgiapp = RegistryMiddleMan(wsgiapp, regobj, newobj, depth)
        wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    for depth in valuelist:
        assert "InsertValue at depth %s is {'%s': %s}" %\
               (depth, keylist[depth], depth) in res
    for depth in valuelist:
        assert "AppendValue at depth %s is {'%s': %s}" %\
               (depth, keylist[depth], depth) in res

def test_iterating_response():
    obj = {'hi':'people'}
    secondobj = {'bye':'friends'}
    wsgiapp = RegistryUsingIteratorApp(regobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    wsgiapp = RegistryMiddleMan(wsgiapp, regobj, secondobj, 0)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    assert "InsertValue at depth 0 is {'bye': 'friends'}" in res
    assert "AppendValue at depth 0 is {'bye': 'friends'}" in res

def test_registry_streaming():
    def app(environ, start_response):
        environ['paste.registry'].register(regobj, {'hi':'people'})
        for i in range(10):
            yield str(i)
    rm = RegistryManager(app, streaming=True)

    environ = {}

    res = []
    for x in rm(environ, None):
        res.append(int(x))
        assert len(regobj._object_stack())

    assert len(res) == 10
    assert not(regobj._object_stack())

@raises(SystemError)
def test_registry_streaming_exception():
    def app(environ, start_response):
        environ['paste.registry'].register(regobj, {'hi':'people'})
        for i in range(10):
            if i == 5:
                raise SystemError('Woah!')
            else:
                yield str(i)
    rm = RegistryManager(app, streaming=True, preserve_exceptions=True)
    environ = {}
    try:
        for x in rm(environ, None):
            assert len(regobj._object_stack())
    except:
        #check the object got preserved due to exception
        assert regobj._object_stack()
        regobj._pop_object()
        raise

def test_dispatch_config():
    conf = DispatchingConfig()
    conf.push_process_config({'key':'default'})
    conf.push_thread_config({'key':'value'})
    assert conf.current()['key'] == 'value'
    conf.pop_thread_config()
    assert conf.current()['key'] == 'default'

    try:
        conf.pop_process_config({'another':'one'})
        pop_failed = False
    except AssertionError:
        pop_failed = True
    assert pop_failed, 'It should have failed due to different config popped'

    try:
        conf.current()
        assert False, 'It should fail due to empty objects stack'
    except AttributeError:
        pass
########NEW FILE########
__FILENAME__ = test_request_local
from tg.request_local import Request, Response

class TestRequest(object):
    def test_language(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, da'})
        bmatch = r.languages_best_match()
        assert ['da', 'en-gb'] == bmatch

    def test_language_fallback(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, da'})
        bmatch = r.languages_best_match(fallback='it')
        assert ['da', 'en-gb', 'it'] == bmatch

    def test_language_fallback_already_there(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, it, da'})
        bmatch = r.languages_best_match(fallback='it')
        assert ['it'] == bmatch, bmatch

    def test_languages(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, it;q=0.9, da'})
        r.language = 'it'
        assert r.language == 'it'
        bmatch = r.languages
        assert ['da', 'it'] == bmatch, bmatch

    def test_match_accept(self):
        r = Request({}, headers={'Accept': 'text/html;q=0.5, foo/bar'})
        first_match = r.match_accept(['foo/bar'])
        assert first_match == 'foo/bar', first_match

    def test_signed_cookie(self):
        resp = Response()
        resp.signed_cookie('key_name', 'VALUE', secret='123')
        cookie = resp.headers['Set-Cookie']

        r = Request({}, headers={'Cookie':cookie})
        value = r.signed_cookie('key_name', '123')
        assert value == 'VALUE', value

        r = Request({}, headers={'Cookie':cookie})
        value = r.signed_cookie('non_existing', '123')
        assert not value

class TestResponse(object):
    def test_wsgi_response(self):
        r = Response()
        status, headers, body = r.wsgi_response()
        assert '200 OK' == status
########NEW FILE########
__FILENAME__ = test_statics
from webtest import TestApp
from nose.tools import raises
from webob import Request
from tg.support.statics import StaticsMiddleware, FileServeApp
from webob.exc import HTTPBadRequest, HTTPForbidden
from datetime import datetime

def FakeApp(environ, start_response):
    return ['APP']

class TestStatics(object):
    def setup(self):
        self.app = TestApp(StaticsMiddleware(FakeApp, './tests'))

    def test_plain_request(self):
        r = self.app.get('/test.html')
        assert 'Welcome to TurboGears 2.0' in r

    def test_unknown_content_type(self):
        r = self.app.get('/empty_file.unknown')
        assert r.content_type == 'application/octet-stream'
        assert 'EMPTY' in r

    def test_if_modified_since(self):
        r = self.app.get('/empty_file.unknown', headers={'If-Modified-Since':'Sat, 29 Oct 1994 19:43:31 GMT'})
        assert 'EMPTY' in r

    @raises(HTTPBadRequest)
    def test_if_modified_since_invalid_date(self):
        r = self.app.get('/empty_file.unknown', headers={'If-Modified-Since':'This is not a date'})

    def test_if_modified_since_future(self):
        next_year = datetime.utcnow()
        next_year.replace(year=next_year.year+1)

        r = self.app.get('/empty_file.unknown',
                         headers={'If-Modified-Since':FileServeApp.make_date(next_year)},
                         status=304)

    def test_if_none_match(self):
        r = self.app.get('/empty_file.unknown')
        etag = r.headers['ETag']

        r = self.app.get('/empty_file.unknown', headers={'If-None-Match':etag}, status=304)

    def test_if_none_match_different(self):
        r = self.app.get('/empty_file.unknown', headers={'If-None-Match':'Probably-Not-The-Etag'})
        assert 'EMPTY' in r

    def test_make_date(self):
        res = FileServeApp.make_date(datetime(2000, 1, 1, 0, 0, 0, 0))
        assert res == 'Sat, 01 Jan 2000 00:00:00 GMT'

    def test_304_on_post(self):
        r = self.app.post('/empty_file.unknown', status=304)

    def test_forbidden_path(self):
        r = self.app.get('/missing/../test.html', status=404)
        assert 'Out of bounds' in r

    def test_FileApp_non_existing_file(self):
        fa = TestApp(FileServeApp('this_does_not_exists.unknown', 0))
        r = fa.get('/', status=403)
        assert '403' in r

    def test_wsgi_file_wrapper(self):
        class DummyWrapper(object):
            def __init__(self, file, block_size):
                self.file = file
                self.block_size = block_size

        environ = {
            'wsgi.url_scheme': 'http',
            'wsgi.version':(1,0),
            'wsgi.file_wrapper': DummyWrapper,
            'SERVER_NAME': 'somedomain.com',
            'SERVER_PORT': '8080',
            'PATH_INFO': '/index.html',
            'SCRIPT_NAME': '',
            'REQUEST_METHOD': 'GET',
            }

        app = FileServeApp('./tests/test.html', 3600)
        app_iter = Request(environ).send(app).app_iter
        assert isinstance(app_iter, DummyWrapper)
        assert b'Welcome to TurboGears 2.0' in app_iter.file.read()
        app_iter.file.close()

########NEW FILE########
__FILENAME__ = test_tg_controller_dispatch
# -*- coding: utf-8 -*-
from wsgiref.simple_server import demo_app
from wsgiref.validate import validator

from tests.test_validation import validators

from webob import Response, Request
from tg._compat import unicode_text, u_

try:
    from pylons.controllers.xmlrpc import XMLRPCController
except ImportError:
    try:
        from xmlrpclib import dumps
    except ImportError:
        from xmlrpc.client import dumps

    class XMLRPCController(object):
        def __call__(self, environ, start_response):
            raw_response = self.textvalue()
            response = dumps((raw_response,), methodresponse=True, allow_none=False).encode('utf-8')

            headers = []
            headers.append(('Content-Length', str(len(response))))
            headers.append(('Content-Type', 'text/xml'))
            start_response("200 OK", headers)
            return [response]


import tg
from tg import config, tmpl_context
from tg.controllers import (TGController, WSGIAppController)
from tg.decorators import expose, validate
from tg.util import no_warn

from tests.base import (
    TestWSGIController, make_app, setup_session_dir, teardown_session_dir)


config['renderers'] = ['genshi', 'mako', 'json']


def setup():
    setup_session_dir()


def teardown():
    teardown_session_dir()


def wsgi_app(environ, start_response):
    req = Request(environ)
    if req.method == 'POST':
        resp = Response(req.POST['data'])
    else:
        resp = Response("Hello from %s/%s"%(req.script_name, req.path_info))
    return resp(environ, start_response)


class XMLRpcTestController(XMLRPCController):

    def textvalue(self):
        return 'hi from xmlrpc'

    textvalue.signature = [ ['string'] ]


class BeforeController(TGController):

    def _before(self, *args, **kw):
        tmpl_context.var = '__my_before__'

    def _after(self, *args, **kw):
        global_craziness = '__my_after__'

    @expose()
    def index(self):
        assert tmpl_context.var
        return tmpl_context.var


class NewBeforeController(TGController):

    def _before(self, *args, **kw):
        tmpl_context.var = '__my_before__'
        tmpl_context.args = args
        tmpl_context.params = dict(environ=tg.request.environ, **kw)

    def _after(self, *args, **kw):
        global_craziness = '__my_after__'

    def _visit(self, *remainder, **params):
        tmpl_context.visit = 'visited'

    @expose()
    def index(self):
        assert tmpl_context.var
        return tmpl_context.var

    @expose()
    def with_args(self, *args, **kw):
        assert tmpl_context.args
        assert tmpl_context.params
        return tmpl_context.var + tmpl_context.params['environ']['webob._parsed_query_vars'][0]['x']

    @expose()
    def visited(self):
        return tmpl_context.visit

class SubController(object):

    mounted_app = WSGIAppController(wsgi_app)

    before = BeforeController()
    newbefore = NewBeforeController()

    @expose('genshi')
    def unknown_template(self):
        return "sub unknown template"

    @expose()
    def foo(self,):
        return 'sub_foo'

    @expose()
    def index(self):
        return 'sub index'

    @expose()
    def _default(self, *args):
        return "received the following args (from the url): %s" % ', '.join(args)

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, **kw)

    @expose()
    def redirect_sub(self):
        tg.redirect('index')

    @expose()
    def hello(self, name):
        return "Why hello, %s!" % name

    @expose()
    def get_controller_state(self):
        return '/'.join([p[0] for p in tg.request.controller_state.controller_path])

class SubController3(object):
    @expose()
    def get_all(self):
        return 'Sub 3'

    @expose()
    def controller_url(self, using_tmpl_context='false', *args):
        if using_tmpl_context == 'true':
            return tmpl_context.controller_url
        else:
            return tg.request.controller_url

class SubController2(object):

    @expose()
    def index(self):
        tg.redirect('list')

    @expose()
    def list(self, **kw):
        return "hello list"


class LookupHelper:

    def __init__(self, var):
        self.var = var

    @expose()
    def index(self):
        return self.var


class LookupHelperWithArgs:

    @expose()
    def get_here(self, *args):
        return "%s"%args

    @expose()
    def post_with_mixed_args(self, arg1, arg2, **kw):
        return "%s%s" % (arg1, arg2)


class LookupControllerWithArgs(TGController):

    @expose()
    def _lookup(self, *args):
        helper = LookupHelperWithArgs()
        return helper, args


class LookupController(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupHelper(a), args


class LookupWithEmbeddedLookupController(TGController):

    @expose()
    def _lookup(self, *args):
        return LookupControllerWithArgs(), args


class LookupHelperWithIndex:

    @expose()
    def index(self):
        return "helper index"

    @expose()
    def method(self):
        return "helper method"


class LookupControllerWithIndexHelper(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupHelperWithIndex(), args

    @expose()
    def index(self):
        return "second controller with index"


class LookupWithEmbeddedLookupWithHelperWithIndex(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupControllerWithIndexHelper(), args

    @expose()
    def index(self):
        return "first controller with index"


class LookupControllerWithSubcontroller(TGController):

    class SubController(object): pass

    @expose()
    def _lookup(self, a, *args):
        return self.SubController(), args


class RemoteErrorHandler(TGController):
    @expose()
    def errors_here(self, *args, **kw):
        return "remote error handler"


class NotFoundController(TGController):
    pass

class NotFoundWithIndexController(TGController):
    @expose()
    def index(self, *args, **kw):
        return 'INDEX'

class DefaultWithArgsController(TGController):

    @expose()
    def _default(self, a, b=None, **kw):
        return "default with args %s %s" % (a, b)


class DeprecatedDefaultWithArgsController(TGController):

    @expose()
    def _default(self, a, b=None, **kw):
        return "deprecated default with args %s %s" % (a, b)


class DefaultWithArgsAndValidatorsController(TGController):

    @expose()
    def failure(self, *args, **kw):
        return "failure"

    @expose()
    @validate(dict(a=validators.Int(), b=validators.StringBool()),
        error_handler=failure)
    def _default(self, a, b=None, **kw):
        return "default with args and validators %s %s"%(a, b)


class SubController4:

    default_with_args = DefaultWithArgsController()
    deprecated_default_with_args = DeprecatedDefaultWithArgsController()


class SubController5:

    default_with_args = DefaultWithArgsAndValidatorsController()


class HelperWithSpecificArgs(TGController):

    @expose()
    def index(self, **kw):
        return str(kw)

    @expose()
    def method(self, arg1, arg2, **kw):
        return str((str(arg1), str(arg2), kw))


class SelfCallingLookupController(TGController):

    @expose()
    def _lookup(self, a, *args):
        if a in ['a', 'b', 'c']:
            return SelfCallingLookupController(), args
        a = [a]
        a.extend(args)
        return HelperWithSpecificArgs(), a

    @expose()
    def index(self, *args, **kw):
        return str((args, kw))

class BasicTGController(TGController):
    mounted_app = WSGIAppController(wsgi_app)
    xml_rpc = WSGIAppController(XMLRpcTestController())

    error_controller = RemoteErrorHandler()

    lookup = LookupController()
    lookup_with_args = LookupControllerWithArgs()
    lookup_with_sub = LookupControllerWithSubcontroller()
    self_calling = SelfCallingLookupController()

    @expose()
    def use_wsgi_app(self):
        return tg.use_wsgi_app(wsgi_app)

    @expose(content_type='application/rss+xml')
    def ticket2351(self, **kw):
        return 'test'

    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose(content_type='application/rss+xml')
    def index_unicode(self):
        tg.response.charset = None
        return u_('Hello World')

    @expose()
    def _default(self, *remainder):
        return "Main default page called for url /%s" % [str(r) for r in remainder]

    @expose()
    def feed(self, feed=None):
        return feed

    sub = SubController()
    sub2 = SubController2()
    sub3 = SubController3()
    sub4 = SubController4()
    sub5 = SubController5()

    embedded_lookup = LookupWithEmbeddedLookupController()
    embedded_lookup_with_index = LookupWithEmbeddedLookupWithHelperWithIndex()

    @expose()
    def test_args(self, name, one=None, two=2, three=3):
        return "name=%s, one=%s, two=%s, three=%s" % (name, one, two, three)

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, kw)

    @expose()
    def hello(self, name, silly=None):
        return "Hello " + name

    @expose()
    def optional_and_req_args(self, name, one=None, two=2, three=3):
        return "name=%s, one=%s, two=%s, three=%s" % (name, one, two, three)

    @expose()
    def ticket2412(self, arg1):
        return arg1

    @expose()
    def redirect_cookie(self, name):
        tg.response.set_cookie('name', name)
        tg.redirect('/hello_cookie')

    @expose()
    def hello_cookie(self):
        return "Hello " + tg.request.cookies['name']

    @expose()
    def flash_redirect(self):
        tg.flash("Wow, flash!")
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_unicode(self):
        tg.flash(u_("Привет, мир!"))
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_after_redirect(self):
        return tg.get_flash()

    @expose()
    def flash_status(self):
        return tg.get_status()

    @expose()
    def flash_no_redirect(self):
        tg.flash("Wow, flash!")
        return tg.get_flash()

    @expose('json')
    @validate(validators=dict(some_int=validators.Int()))
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json')
    @validate(validators=dict(a=validators.Int()))
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
        return dict(int=a,str=b)

    @expose()
    def error_handler(self, **kw):
        return 'validation error handler'

    @expose('json')
    @validate(validators=dict(a=validators.Int()),
        error_handler=error_handler)
    def validated_with_error_handler(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
        return dict(int=a,str=b)

    @expose('json')
    @validate(validators=dict(a=validators.Int()),
        error_handler=error_controller.errors_here)
    def validated_with_remote_error_handler(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
        return dict(int=a,str=b)

    @expose()
    @expose('json')
    def stacked_expose(self):
        return dict(got_json=True)

    @expose('json')
    def bad_json(self):
        return [(1, 'a'), 'b']

    @expose()
    def custom_content_type_in_controller(self):
        tg.response.headers['content-type'] = 'image/png'
        return b'PNG'

    @expose('json', content_type='application/json')
    def custom_content_type_in_controller_charset(self):
        tg.response.headers['content-type'] = 'application/json; charset=utf-8'
        return dict(result='TXT')

    @expose(content_type='image/png')
    def custom_content_type_in_decorator(self):
        return b'PNG'

    @expose()
    def test_204(self, *args, **kw):
        from webob.exc import HTTPNoContent
        raise HTTPNoContent()

    @expose()
    def custom_content_type_replace_header(self):
        replace_header(tg.response.headerlist, 'Content-Type', 'text/xml')
        return "<?xml version='1.0'?>"

    @expose()
    def multi_value_kws(sekf, *args, **kw):
        assert kw['foo'] == ['1', '2'], kw

    @expose()
    def with_routing_args(self, **kw):
        return str(tg.request._controller_state.routing_args)

    @expose('json')
    @expose('genshi')
    @expose()
    def get_response_type(self):
        return dict(ctype=tg.request.response_type)

    @expose()
    def hello_ext(self, *args):
        return str(tg.request.response_ext)

class TestNotFoundController(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(NotFoundController)

    def test_not_found(self):
        r = self.app.get('/something', status=404)
        assert '404 Not Found' in r, r

    def test_not_found_blank(self):
        r = self.app.get('/', status=404)
        assert '404 Not Found' in r, r

    def test_not_found_unicode(self):
        r = self.app.get('/%D0%BF%D1%80%D0%B0%D0%B2%D0%B0', status=404)
        assert '404 Not Found' in r, r

class TestNotFoundWithIndexController(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(NotFoundWithIndexController)

    def test_not_found(self):
        r = self.app.get('/something', status=404)
        assert '404 Not Found' in r, r


class TestWSGIAppController(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        class TestedWSGIAppController(WSGIAppController):
            def __init__(self):
                def test_app(environ, start_response):
                    if environ.get('CONTENT_LENGTH', None) in (-1, '-1'):
                        del environ['CONTENT_LENGTH']
                    return validator(demo_app)(environ, start_response)
                super(TestedWSGIAppController, self).__init__(test_app)
        self.app = make_app(TestedWSGIAppController)

    def test_valid_wsgi(self):
        try:
            r = self.app.get('/some_url')
        except Exception as e:
            raise AssertionError(str(e))
        assert 'some_url' in r

class TestWSGIAppControllerNotHTML(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        class TestedWSGIAppController(WSGIAppController):
            def __init__(self):
                def test_app(environ, start_response):
                    start_response('200 OK', [('Content-type','text/plain'),
                                              ('Content-Length', '5')])
                    return [b'HELLO']
                super(TestedWSGIAppController, self).__init__(test_app)
        self.app = make_app(TestedWSGIAppController)

    def test_right_wsgi_headers(self):
        r = self.app.get('/some_url')
        assert 'HELLO' in r
        assert r.content_length == 5
        assert r.content_type == 'text/plain'

class TestTGController(TestWSGIController):
    def setUp(self, *args, **kargs):
        TestWSGIController.setUp(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_enable_routing_args(self):
        config.enable_routing_args = True
        r =self.app.get('/with_routing_args?a=1&b=2&c=3')
        assert 'a' in str(r)
        assert 'b' in str(r)
        assert 'c' in str(r)
        config.enable_routing_args = False

    def test_response_without_charset(self):
        r = self.app.get('/index_unicode')
        assert 'Hello World' in r, r
        assert 'charset=utf-8' in str(r), r

    def test_lookup(self):
        r = self.app.get('/lookup/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_lookup_with_sub(self):
        r = self.app.get('/lookup_with_sub/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_lookup_with_args(self):
        r = self.app.get('/lookup_with_args/get_here/got_here')
        msg = 'got_here'
        assert r.body.decode('utf-8')==msg, r

    def test_post_with_mixed_args(self):
        r = self.app.post('/lookup_with_args/post_with_mixed_args/test', params={'arg2': 'time'})
        msg = 'testtime'
        assert r.body.decode('utf-8')==msg, r

    def test_validated_int(self):
        r = self.app.get('/validated_int/1')
        assert '{"response": 1}' in r, r

    def test_validated_with_error_handler(self):
        r = self.app.get('/validated_with_error_handler?a=asdf&b=123')
        msg = 'validation error handler'
        assert msg in r, r

    def test_validated_with_remote_error_handler(self):
        r = self.app.get('/validated_with_remote_error_handler?a=asdf&b=123')
        msg = 'remote error handler'
        assert msg in r, r

    def test_unknown_template(self):
        r = self.app.get('/sub/unknown_template/')
        msg = 'sub unknown template'
        assert msg in r, r

    def test_mounted_wsgi_app_at_root(self):
        r = self.app.get('/mounted_app/')
        assert 'Hello from /mounted_app' in r, r

    def test_mounted_wsgi_app_at_subcontroller(self):
        r = self.app.get('/sub/mounted_app/')
        assert 'Hello from /sub/mounted_app/' in r, r

    def test_request_for_wsgi_app_with_extension(self):
        r = self.app.get('/sub/mounted_app/some_document.pdf')
        assert 'Hello from /sub/mounted_app//some_document.pdf' in r, r

    def test_posting_to_mounted_app(self):
        r = self.app.post('/mounted_app/', params={'data':'Foooo'})
        assert 'Foooo' in r, r

    def test_use_wsgi_app(self):
        r = self.app.get('/use_wsgi_app')
        assert '/use_wsgi_app' in r, r

    def test_custom_content_type_replace_header(self):
        s = '''<?xml version="1.0"?>
<methodCall>
<methodName>textvalue</methodName>
</methodCall>
'''
        r = self.app.post('/xml_rpc/', s, [('Content-Type', 'text/xml')])
        assert len(r.headers.getall('Content-Type')) == 1, r.headers.getall('Content-Type')
        assert r.headers['Content-Type'] == 'text/xml'

    def test_response_type(self):
        r = self.app.post('/stacked_expose.json')
        assert 'got_json' in r.body.decode('utf-8'), r

    def test_multi_value_kw(self):
        r = self.app.get('/multi_value_kws?foo=1&foo=2')

    def test_before_controller(self):
        r = self.app.get('/sub/before')
        assert '__my_before__' in r, r

    def test_new_before_controller(self):
        r = self.app.get('/sub/newbefore')
        assert '__my_before__' in r, r

    def test_visit_entry_point(self):
        r = self.app.get('/sub/newbefore/visited')
        assert 'visited' in r, r

    def test_before_with_args(self):
        r = self.app.get('/sub/newbefore/with_args/1/2?x=5')
        assert '__my_before__5' in r, r

    def test_before_controller_mounted_in_subpath(self):
        r = self.app.get('/subpath/sub/before', extra_environ={'SCRIPT_NAME':'/subpath'})
        assert '__my_before__' in r, r

    def test_empty_path_after_script_name_removal(self):
        r = self.app.get('/')
        check_again_response = r.text

        r = self.app.get('/subpath', extra_environ={'SCRIPT_NAME':'/subpath'})
        assert r.text == check_again_response, r

    def test_before_controller_without_script_name(self):
        req = self.app.RequestClass.blank('/sub/before', {})
        req.environ.pop('SCRIPT_NAME')
        r = self.app.do_request(req, status=None, expect_errors=False)
        assert '__my_before__' in r, r

    @no_warn
    def test_unicode_default_dispatch(self):
        r =self.app.get('/sub/%C3%A4%C3%B6')
        assert u_("äö") in r.body.decode('utf-8'), r

    def test_default_with_empty_second_arg(self):
        r =self.app.get('/sub4/default_with_args/a')
        assert "default with args a None" in r.body.decode('utf-8'), r
        assert "deprecated" not in r.body.decode('utf-8')
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args/a')
        warnings.resetwarnings()
        assert "deprecated default with args a None" in r.body.decode('utf-8'), r

    def test_default_with_args_a_b(self):
        r =self.app.get('/sub4/default_with_args/a/b')
        assert "default with args a b" in r.body.decode('utf-8'), r
        assert "deprecated" not in r.body.decode('utf-8')
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args/a/b')
        warnings.resetwarnings()
        assert "deprecated default with args a b" in r.body.decode('utf-8'), r

    def test_default_with_query_arg(self):
        r =self.app.get('/sub4/default_with_args?a=a')
        assert "default with args a None" in  r.body.decode('utf-8'), r
        assert "deprecated" not in  r.body.decode('utf-8')
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args?a=a')
        warnings.resetwarnings()
        assert "deprecated default with args a None" in  r.body.decode('utf-8'), r

    def test_default_with_validator_fail(self):
        r =self.app.get('/sub5/default_with_args?a=True')
        assert "failure" in  r.body.decode('utf-8'), r

    def test_default_with_validator_pass(self):
        r =self.app.get('/sub5/default_with_args?a=66')
        assert "default with args and validators 66 None" in  r.body.decode('utf-8'), r

    def test_default_with_validator_pass2(self):
        r =self.app.get('/sub5/default_with_args/66')
        assert "default with args and validators 66 None" in  r.body.decode('utf-8'), r

    def test_default_with_validator_fail2(self):
        r =self.app.get('/sub5/default_with_args/True/more')
        assert "failure" in  r.body.decode('utf-8'), r

    def test_custom_content_type_in_controller(self):
        resp = self.app.get('/custom_content_type_in_controller')
        assert 'PNG' in resp, resp
        assert resp.headers['Content-Type'] == 'image/png', resp

    def test_custom_content_type_in_controller_charset(self):
        resp = self.app.get('/custom_content_type_in_controller_charset')
        assert 'TXT' in resp, resp
        assert resp.headers['Content-Type'] == 'application/json; charset=utf-8', resp

    def test_custom_content_type_in_decorator(self):
        resp = self.app.get('/custom_content_type_in_decorator')
        assert 'PNG' in resp, resp
        assert resp.headers['Content-Type'] == 'image/png', resp

    def test_removed_spurious_content_type(self):
        r = self.app.get('/test_204')
        assert r.headers.get('Content-Type', 'MISSING') == 'MISSING'

    def test_optional_and_req_args(self):
        resp = self.app.get('/optional_and_req_args/test/one')
        assert "name=test, one=one, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_optional_and_req_args_at_root(self):
        resp = self.app.get('/test_args/test/one')
        assert "name=test, one=one, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_no_args(self):
        resp = self.app.get('/test_args/test/')
        assert "name=test, one=None, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_one_extra_arg(self):
        resp = self.app.get('/test_args/test/1')
        assert "name=test, one=1, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_two_extra_args(self):
        resp = self.app.get('/test_args/test/1/2')
        assert "name=test, one=1, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_three_extra_args(self):
        resp = self.app.get('/test_args/test/1/2/3')
        assert "name=test, one=1, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_extra_args_forces_default_lookup(self):
        resp = self.app.get('/test_args/test/1/2/3/4')
        assert resp.body.decode('utf-8') == """Main default page called for url /['test_args', 'test', '1', '2', '3', '4']""", resp

    def test_not_enough_args(self):
        resp = self.app.get('/test_args/test/1')
        assert "name=test, one=1, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_ticket_2412_with_ordered_arg(self):
        resp = self.app.get('/ticket2412/Abip%C3%B3n')
        assert u_("""Abipón""") in resp.body.decode('utf-8'), resp

    def test_ticket_2412_with_named_arg(self):
        resp = self.app.get('/ticket2412?arg1=Abip%C3%B3n')
        assert u_("""Abipón""") in resp.body.decode('utf-8'), resp

    def test_ticket_2351_bad_content_type(self):
        resp = self.app.get('/ticket2351', headers={'Accept':'text/html'})
        assert 'test' in resp.body.decode('utf-8'), resp

    def test_embedded_lookup_with_index_first(self):
        resp = self.app.get('/embedded_lookup_with_index/')
        assert 'first controller with index' in resp.body.decode('utf-8'), resp

    def test_embedded_lookup_with_index_second(self):
        resp = self.app.get('/embedded_lookup_with_index/a')
        assert 'second controller with index' in resp.body.decode('utf-8'), resp

    def test_embedded_lookup_with_index_helper(self):
        resp = self.app.get('/embedded_lookup_with_index/a/b')
        assert 'helper index' in resp.body.decode('utf-8'), resp

    def test_embedded_lookup_with_index_method(self):
        resp = self.app.get('/embedded_lookup_with_index/a/b/method')
        assert 'helper method' in resp.body.decode('utf-8'), resp

    def test_self_calling_lookup_simple_index(self):
        resp = self.app.get('/self_calling')
        assert '((), {})' in resp.body.decode('utf-8'), resp

    def test_self_calling_lookup_method(self):
        resp = self.app.get('/self_calling/a/method/a/b')
        assert "('a', 'b', {})" in resp.body.decode('utf-8'), resp

    def test_self_calling_lookup_multiple_calls_method(self):
        resp = self.app.get('/self_calling/a/b/c/method/a/b')
        assert "('a', 'b', {})" in resp.body.decode('utf-8'), resp

    def test_controller_state(self):
        resp = self.app.get('/sub/get_controller_state')
        assert '/sub' in resp

    def test_response_type(self):
        resp = self.app.get('/get_response_type.json')
        assert 'json' in resp

    def test_response_type_html(self):
        resp = self.app.get('/get_response_type.html')
        assert 'html' in resp

    def test_extensions_single(self):
        resp = self.app.get('/hello_ext.html')
        assert resp.body.decode('ascii') == '.html', resp.body

    def test_extensions_missing(self):
        resp = self.app.get('/hello_ext')
        assert resp.body.decode('ascii') == 'None', resp.body

    def test_extensions_two(self):
        resp = self.app.get('/hello_ext.json.html')
        assert 'Main default page' in resp, resp
        assert 'hello_ext.json' in resp, resp

    def test_extensions_three(self):
        resp = self.app.get('/hello_ext.jpg.json.html')
        assert 'Main default page' in resp, resp
        assert 'hello_ext.jpg.json' in resp, resp

    def test_controller_url(self):
        resp = self.app.get('/sub3/controller_url/false/a/b/c')
        assert resp.text == 'sub3/controller_url', resp.text

    def test_controller_url_backward_compatibility(self):
        resp = self.app.get('/sub3/controller_url/true/a/b/c')
        assert resp.text == 'sub3/controller_url', resp.text


########NEW FILE########
__FILENAME__ = test_util
# -*- coding: utf-8 -*-

import tg
from tg.util import *
from nose.tools import eq_, raises
import os
from tg.controllers.util import *
from tg.util import ContextObj, AttribSafeContextObj

import tg._compat
from tg._compat import u_

path = None
def setup():
    global path
    path = os.curdir
    os.chdir(os.path.abspath(os.path.dirname(os.path.dirname(tg.__file__))))

def teardown():
    global path
    os.chdir(path)

def test_get_partial_dict():
    eq_(get_partial_dict('prefix', {'prefix.xyz':1, 'prefix.zyx':2, 'xy':3}),
        {'xyz':1,'zyx':2})

def test_compat_im_class():
    class FakeClass(object):
        def method(self):
            pass

    def func():
        pass

    o = FakeClass()
    assert tg._compat.im_class(o.method) == FakeClass
    assert tg._compat.im_class(func) == None

def test_url_unicode():
    res = url('.', {'p1':u_('v1')})
    assert res == '.?p1=v1'

def test_url_unicode_nonascii():
    res = url('.', {'p1':u_('àèìòù')})
    assert res == '.?p1=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'

def test_url_nonstring():
    res = url('.', {'p1':1})
    assert res == '.?p1=1'

def test_url_object():
    class Object(object):
        def __str__(self):
            return 'aeiou'

    res = url('.', {'p1':Object()})
    assert res == '.?p1=aeiou'

def test_url_object_unicodeerror():
    class Object(object):
        def __str__(self):
            return u_('àèìòù')

    res = url('.', {'p1':Object()})
    assert res == '.?p1=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'

def test_url_object_exception():
    class SubException(Exception):
        def __str__(self):
            return u_('àèìòù')

    res = url('.', {'p1':SubException('a', 'b', 'c')})
    assert res == '.?p1=a+b+c', res

class TestBunch(object):
    def test_add_entry(self):
        d = Bunch()
        d['test.value'] = 5
        assert d.test.value == 5

    def test_del_entry(self):
        d = Bunch()
        d['test_value'] = 5
        del d.test_value
        assert not list(d.keys())

    @raises(AttributeError)
    def test_del_entry_fail(self):
        d = Bunch()
        del d.not_existing

class TestDottedNameFinder(object):
    @raises(DottedFileLocatorError)
    def test_non_python_package(self):
        DottedFileNameFinder().get_dotted_filename('this.is.not.a.python.package')

    def test_local_file(self):
        assert DottedFileNameFinder().get_dotted_filename('this_should_be_my_template') == 'this_should_be_my_template'

class TestLazyString(object):
    def test_lazy_string_to_str(self):
        l = LazyString(lambda: 'HI')
        assert str(l) == 'HI'

    def test_lazy_string_to_mod(self):
        l = LazyString(lambda: '%s')
        assert (l % 'HI') == 'HI'

    def test_lazy_string_format(self):
        l = LazyString(lambda: '{0}')
        lf = l.format('HI')
        assert lf == 'HI', lf

class TestAttribSafeContextObj(object):
    def setup(self):
        self.c = AttribSafeContextObj()

    def test_attribute_default_value(self):
        assert self.c.something == ''

        self.c.something = 'HELLO'
        assert self.c.something == 'HELLO'

        assert self.c.more == ''

def test_tmpl_context_long_entry():
    c = ContextObj()
    c.something = '3'*300
    assert len(str(c)) < 300
########NEW FILE########
__FILENAME__ = test_validation
# -*- coding: utf-8 -*-
from functools import partial
from nose.tools import raises
from nose import SkipTest
from crank.util import get_params_with_argspec

import tg
import tests
from json import loads, dumps

from tg.controllers import TGController, DecoratedController
from tg.decorators import expose, validate, before_render, before_call, Decoration
from tests.base import (TestWSGIController, data_dir,
    make_app, setup_session_dir, teardown_session_dir)

from tg._compat import PY3, unicode_text, u_, default_im_func
from tg.validation import TGValidationError, validation_errors

from formencode import validators, Schema

import tw2.core as tw2c
import tw2.forms as tw2f

class MovieForm(tw2f.TableForm):
    title = tw2f.TextField(validator=tw2c.Required)
    year = tw2f.TextField(size=4, validator=tw2c.IntValidator)
movie_form = MovieForm(action='save_movie')

class Pwd(Schema):
    pwd1 = validators.String(not_empty=True)
    pwd2 = validators.String(not_empty=True)
    chained_validators = [validators.FieldsMatch('pwd1', 'pwd2')]

class FormWithFieldSet(tw2f.TableForm):
    class fields1(tw2f.ListFieldSet):
        f1 = tw2f.TextField(validator=tw2c.Required)

    class fields2(tw2f.ListFieldSet):
        f2 = tw2f.TextField(validator=tw2c.IntValidator)

if not PY3:
    from tw.forms import TableForm, TextField
    from tw.api import WidgetsList

    class MyForm(TableForm):
        class fields(WidgetsList):
            """This WidgetsList is just a container."""
            title=TextField(validator = validators.NotEmpty())
            year = TextField(size=4, validator=validators.Int())
    myform = MyForm("my_form", action='create')
else:
    myform = None


def setup():
    setup_session_dir()

def teardown():
    teardown_session_dir()

class controller_based_validate(validate):

    def __init__(self, error_handler=None, *args, **kw):
        self.error_handler = error_handler
        self.needs_controller = True

        class Validators(object):
            def validate(self, controller, params, state):
                return params

        self.validators = Validators()

class ColonValidator(validators.FancyValidator):
    def validate_python(self, value, state):
        raise validators.Invalid('ERROR: Description', value, state)

class ColonLessGenericValidator(object):
    def validate(self, value, state=None):
        raise validators.Invalid('Unknown Error', value, {'_the_form':'Unknown Error'})

def error_handler_function(controller_instance, uid, num):
    return 'UID: %s' % uid


def ControllerWrapperForErrorHandler(caller):
    def call(*args, **kw):
        value = caller(*args, **kw)
        return value + 'X'
    return call


class ErrorHandlerCallable(object):
    def __call__(self, controller_instance, uid, num):
        return 'UID: %s' % uid

class BasicTGController(TGController):
    @expose()
    @validate(ColonLessGenericValidator())
    def validator_without_columns(self, **kw):
        return tg.request.validation['errors']['_the_form']

    @expose('json:')
    @validate(validators={"some_int": validators.Int()})
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json:')
    @validate(validators={"a": validators.Int()})
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
        return dict(int=a, str=b)

    @expose()
    @controller_based_validate()
    def validate_controller_based_validator(self, *args, **kw):
        return 'ok'

    @expose('json:')
    @validate(validators={"a": validators.Int(), "someemail": validators.Email()})
    def two_validators(self, a=None, someemail=None, *args):
        errors = tg.request.validation['errors']
        values = tg.request.validation['values']
        return dict(a=a, someemail=someemail,
                errors=str(errors), values=str(values))

    @expose('json:')
    @validate(validators={"a": validators.Int()})
    def with_default_shadow(self, a, b=None ):
        """A default value should not cause the validated value to disappear"""
        assert isinstance( a, int ), type(a)
        return {
            'int': a,
        }

    @expose('json:')
    @validate(validators={"e": ColonValidator()})
    def error_with_colon(self, e):
        errors = tg.request.validation['errors']
        return dict(errors=str(errors))

    @expose('json:')
    @validate(validators={
        "a": validators.Int(),"b":validators.Int(),"c":validators.Int(),"d":validators.Int()
    })
    def with_default_shadow_long(self, a, b=None,c=None,d=None ):
        """A default value should not cause the validated value to disappear"""
        assert isinstance( a, int ), type(a)
        assert isinstance( b, int ), type(b)
        assert isinstance( c, int ), type(c)
        assert isinstance( d, int ), type(d)
        return {
            'int': [a,b,c,d],
        }

    @expose()
    def display_form(self, **kwargs):
        return str(myform.render(values=kwargs))

    @expose('json:')
    @validate(form=myform)
    def process_form(self, **kwargs):
        kwargs['errors'] = tg.request.validation['errors']
        return dict(kwargs)

    @expose('json:')
    @validate(form=myform, error_handler=process_form)
    def send_to_error_handler(self, **kwargs):
        kwargs['errors'] = tg.request.validation['errors']
        return dict(kwargs)

    @expose()
    def tw2form_error_handler(self, **kwargs):
        return dumps(dict(errors=tg.request.validation['errors']))

    @expose('json:')
    @validate(form=movie_form, error_handler=tw2form_error_handler)
    def send_tw2_to_error_handler(self, **kwargs):
        return 'passed validation'

    @expose()
    @validate({'param':tw2c.IntValidator()})
    def tw2_dict_validation(self, **kwargs):
        return str(tg.request.validation['errors'])

    @expose('text/plain')
    @validate(form=FormWithFieldSet, error_handler=tw2form_error_handler)
    def tw2_fieldset_submit(self, **kwargs):
        return 'passed validation'

    @expose()
    def set_lang(self, lang=None):
        tg.session['tg_lang'] = lang
        tg.session.save()
        return 'ok'

    @expose()
    @validate(validators=Pwd())
    def password(self, pwd1, pwd2):
        if tg.request.validation['errors']:
            return "There was an error"
        else:
            return "Password ok!"

    @expose('json:')
    @before_render(lambda rem,params,output:output.update({'GOT_ERROR':'HOOKED'}))
    def hooked_error_handler(self, *args, **kw):
        return dict(GOT_ERROR='MISSED HOOK')

    @expose()
    @validate({'v':validators.Int()}, error_handler=hooked_error_handler)
    def with_hooked_error_handler(self, *args, **kw):
        return dict(GOT_ERROR='NO ERROR')

    @expose('json')
    @validate({'v': validators.Int()})
    def check_tmpl_context_compatibility(self, *args, **kw):
        return dict(tmpl_errors=str(tg.tmpl_context.form_errors),
                    errors=str(tg.request.validation['errors']))

    @expose()
    def error_handler(self, *args, **kw):
        return 'ERROR HANDLER!'

    @expose('json:')
    @validate(validators={"some_int": validators.Int()},
              error_handler=error_handler)
    def validate_other_error_handler(self, some_int):
        return dict(response=some_int)

    def unexposed_error_handler(self, uid, **kw):
        return 'UID: %s' % uid

    @expose()
    @validate({'uid': validators.Int(),
               'num': validators.Int()},
              error_handler=unexposed_error_handler)
    def validate_unexposed(self, uid, num):
        return 'HUH'

    @expose()
    @validate({'num': validators.Int()},
              error_handler=partial(unexposed_error_handler,
                                    uid=5))
    def validate_partial(self, num):
        return 'HUH'

    @expose()
    @validate({'uid': tw2c.IntValidator(),
               'num': tw2c.IntValidator()},
              error_handler=error_handler_function)
    def validate_function(self, uid, num):
        return 'HUH'

    @expose()
    @validate({'uid': validators.Int(),
               'num': validators.Int()},
              error_handler=ErrorHandlerCallable())
    def validate_callable(self, uid, num):
        return 'HUH'

    @expose()
    @before_call(lambda remainder, params: params.setdefault('num', 5))
    def hooked_error_handler(self, uid, num):
        return 'UID: %s, NUM: %s' % (uid, num)

    @expose()
    @validate({'uid': validators.Int()},
              error_handler=hooked_error_handler)
    def validate_hooked(self, uid):
        return 'HUH'

    # Decorate validate_hooked with a controller wrapper
    Decoration.get_decoration(hooked_error_handler)\
        ._register_controller_wrapper(ControllerWrapperForErrorHandler)

    @expose()
    def manually_handle_validation(self):
        # This is done to check that we don't break compatibility
        # with external modules that perform custom validation like tgext.socketio

        controller = self.__class__.validate_function
        args = (2, 'NaN')
        try:
            output = ''
            validate_params = get_params_with_argspec(controller, {}, args)
            params = DecoratedController._perform_validate(controller,
                                                           validate_params)
        except validation_errors as inv:
            handler, output = DecoratedController._handle_validation_errors(controller,
                                                                            args, {},
                                                                            inv, None)

        return output


class TestTGController(TestWSGIController):
    def setUp(self):
        TestWSGIController.setUp(self)
        tg.config.update({
            'paths': {'root': data_dir},
            'package': tests,
        })

        self.app = make_app(BasicTGController)

    def test_basic_validation_and_jsonification(self):
        """Ensure you can pass in a dictionary of validators"""
        form_values = {"some_int": 22}
        resp = self.app.post('/validated_int', form_values)
        assert '{"response": 22}'in resp, resp

    def test_validation_other_error_handler(self):
        form_values = {"some_int": 'TEXT'}
        resp = self.app.post('/validate_other_error_handler', form_values)
        assert 'ERROR HANDLER!'in resp, resp

    def test_validator_without_columns(self):
        form_values = {"some_int": 22}
        resp = self.app.post('/validator_without_columns', form_values)
        assert 'Unknown Error' in resp, resp

    def test_for_other_params_after_validation(self):
        """Ensure that both validated and unvalidated data make it through"""
        form_values = {'a': 1, 'b': "string"}
        resp = self.app.post('/validated_and_unvalidated', form_values)
        assert '"int": 1' in resp
        assert '"str": "string"' in resp, resp

    def test_validation_shadowed_by_defaults( self ):
        """Catch regression on positional argument validation with defaults"""
        resp = self.app.post('/with_default_shadow/1?b=string')
        assert '"int": 1' in resp, resp

    def test_optional_shadowed_by_defaults( self ):
        """Catch regression on optional arguments being reverted to un-validated"""
        resp = self.app.post('/with_default_shadow_long/1?b=2&c=3&d=4')
        assert '"int": [1, 2, 3, 4]' in resp, resp

    @raises(AssertionError)
    def test_validation_fails_with_no_error_handler(self):
        form_values = {'a':'asdf', 'b':"string"}
        resp = self.app.post('/validated_and_unvalidated', form_values)

    def test_two_validators_errors(self):
        """Ensure that multiple validators are applied correctly"""
        form_values = {'a': '1', 'someemail': "guido@google.com"}
        resp = self.app.post('/two_validators', form_values)
        content = loads(resp.body.decode('utf-8'))
        assert content['a'] == 1

    def test_validation_errors(self):
        """Ensure that dict validation produces a full set of errors"""
        form_values = {'a': '1', 'someemail': "guido~google.com"}
        resp = self.app.post('/two_validators', form_values)
        content = loads(resp.body.decode('utf-8'))
        errors = content.get('errors', None)
        assert errors, 'There should have been at least one error'
        assert 'someemail' in errors, \
            'The email was invalid and should have been reported in the errors'

    def test_form_validation(self):
        """Check @validate's handing of ToscaWidget forms instances"""
        if PY3: raise SkipTest()

        form_values = {'title': 'Razer', 'year': "2007"}
        resp = self.app.post('/process_form', form_values)
        values = loads(resp.body.decode('utf-8'))
        assert values['year'] == 2007

    def test_error_with_colon(self):
        resp = self.app.post('/error_with_colon', {'e':"fakeparam"})
        assert 'Description' in str(resp.body), resp.body

    def test_form_render(self):
        """Test that myform renders properly"""
        if PY3: raise SkipTest()

        resp = self.app.post('/display_form')
        assert 'id="my_form_title.label"' in resp, resp
        assert 'class="fieldlabel required"' in resp, resp
        assert "Title" in resp, resp

    def test_form_validation_error(self):
        """Test form validation with error message"""
        if PY3: raise SkipTest()

        form_values = {'title': 'Razer', 'year': "t007"}
        resp = self.app.post('/process_form', form_values)
        values = loads(resp.body.decode('utf-8'))
        assert "Please enter an integer value" in values['errors']['year'], \
            'Error message not found: %r' % values['errors']

    def test_form_validation_redirect(self):
        """Test form validation error message with redirect"""
        if PY3: raise SkipTest()

        form_values = {'title': 'Razer', 'year': "t007"}
        resp = self.app.post('/send_to_error_handler', form_values)
        values = loads(resp.body.decode('utf-8'))
        assert "Please enter an integer value" in values['errors']['year'], \
            'Error message not found: %r' % values['errors']

    def test_tw2form_validation(self):
        form_values = {'title': 'Razer', 'year': "t007"}
        resp = self.app.post('/send_tw2_to_error_handler', form_values)
        values = loads(resp.body.decode('utf-8'))
        assert "Must be an integer" in values['errors']['year'],\
        'Error message not found: %r' % values['errors']

    def test_tw2dict_validation(self):
        resp = self.app.post('/tw2_dict_validation', {'param': "7"})
        assert '{}' in str(resp.body)

        resp = self.app.post('/tw2_dict_validation', {'param': "hello"})
        assert 'Must be an integer' in str(resp.body)

    def test_form_validation_translation(self):
        if PY3: raise SkipTest()

        """Test translation of form validation error messages"""
        form_values = {'title': 'Razer', 'year': "t007"}
        # check with language set in request header
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'de,ru,it'})
        values = loads(resp.body.decode('utf-8'))
        assert "Bitte eine ganze Zahl eingeben" in values['errors']['year'], \
            'No German error message: %r' % values['errors']
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'ru,de,it'})
        values = loads(resp.body.decode('utf-8'))
        assert u_("Введите числовое значение") in values['errors']['year'], \
            'No Russian error message: %r' % values['errors']
        # check with language set in session
        self.app.post('/set_lang/de')
        resp = self.app.post('/process_form', form_values,
            headers={'Accept-Language': 'ru,it'})
        values = loads(resp.body.decode('utf-8'))
        assert "Bitte eine ganze Zahl eingeben" in values['errors']['year'], \
            'No German error message: %r' % values['errors']

    def test_form_validation_error(self):
        """Test schema validation"""
        form_values = {'pwd1': 'me', 'pwd2': 'you'}
        resp = self.app.post('/password', form_values)
        assert "There was an error" in resp, resp
        form_values = {'pwd1': 'you', 'pwd2': 'you'}
        resp = self.app.post('/password', form_values)
        assert "Password ok!" in resp, resp

    def test_controller_based_validator(self):
        """Test controller based validation"""
        resp = self.app.post('/validate_controller_based_validator')
        assert 'ok' in resp, resp

    def test_hook_after_validation_error(self):
        resp = self.app.post('/with_hooked_error_handler?v=a')
        assert 'HOOKED' in resp, resp

    def test_check_tmpl_context_compatibility(self):
        resp = self.app.post('/check_tmpl_context_compatibility?v=a')
        resp = resp.json
        assert resp['errors'] == resp['tmpl_errors'], resp

    def test_validation_error_has_message(self):
        e = TGValidationError('This is a validation error')
        assert str(e) == 'This is a validation error'

    def test_tw2_fieldset(self):
        form_values = {'fields1:f1': 'Razer', 'fields2:f2': "t007"}
        resp = self.app.post('/tw2_fieldset_submit', form_values)
        values = loads(resp.body.decode('utf-8'))

        assert "Must be an integer" in values['errors'].get('fields2:f2', ''),\
        'Error message not found: %r' % values['errors']

    def test_validate_partial(self):
        resp = self.app.post('/validate_partial', {'num': 'NaN'})
        assert resp.text == 'UID: 5', resp

    def test_validate_unexposed(self):
        resp = self.app.post('/validate_unexposed', {'uid': 2,
                                                     'num': 'NaN'})
        assert resp.text == 'UID: 2', resp

    def test_validate_function(self):
        resp = self.app.post('/validate_function', {'uid': 2,
                                                    'num': 'NaN'})
        assert resp.text == 'UID: 2', resp

    def test_validate_callable(self):
        resp = self.app.post('/validate_callable', {'uid': 2,
                                                    'num': 'NaN'})
        assert resp.text == 'UID: 2', resp

    def test_validate_hooked(self):
        resp = self.app.post('/validate_hooked', {'uid': 'NaN'})
        assert resp.text == 'UID: NaN, NUM: 5X', resp

    def test_manually_handle_validation(self):
        # This is done to check that we don't break compatibility
        # with external modules that perform custom validation like tgext.socketio
        resp = self.app.post('/manually_handle_validation')
        assert resp.text == 'UID: 2', resp
########NEW FILE########
__FILENAME__ = caching
"""Caching decorator, took as is from pylons"""
import tg, inspect, time
from tg.support.converters import asbool
from tg.support import NoDefault, EmptyContext
from tg._compat import im_func, im_class
from functools import wraps

class cached_property(object):
    """
    Works like python @property but the decorated function only gets
    executed once, successive accesses to the property will just
    return the value previously stored into the object.

    The ``@cached_property`` decorator can be executed within a
    provided context, for example to make the cached property
    thread safe a Lock can be provided::

        from threading import Lock
        from tg.caching import cached_property

        class MyClass(object):
            @cached_property
            def my_property(self):
                return 'Value!'
            my_property.context = Lock()

    """
    def __init__(self, func):
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self.func = func
        self.context = EmptyContext()

    def _get_value(self, obj):
        value = obj.__dict__.get(self.__name__, NoDefault)
        if value is NoDefault:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        with self.context:
            return self._get_value(obj)


def _cached_call(func, args, kwargs, key_func, key_dict,
                 expire="never", type=None, starttime=None,
                 cache_headers=('content-type', 'content-length'),
                 cache_response=True, cache_extra_args=None):
    """
    Optional arguments:

    ``key_func``
        Function used to genereate the cache key, the function name
        and class will be used as the base for the cache key. If None
        the ``func`` itself will be used. It's usually handy when
        creating caches for decorated functions, for which we want the
        cache key to be generated on the decorated function and not on
        the decorator.
    ``key_dict``
        Arguments used to generate the cache key, only the arguments
        listed into this dictionary will be used to generate the
        cache key together with the key_func.
    ``expire``
        Time in seconds before cache expires, or the string "never".
        Defaults to "never"
    ``type``
        Type of cache to use: dbm, memory, file, memcached, or None for
        Beaker's default
    ``cache_headers``
        A tuple of header names indicating response headers that
        will also be cached.
    ``invalidate_on_startup``
        If True, the cache will be invalidated each time the application
        starts or is restarted.
    ``cache_response``
        Determines whether the response at the time beaker_cache is used
        should be cached or not, defaults to True.

        .. note::
            When cache_response is set to False, the cache_headers
            argument is ignored as none of the response is cached.

    If cache_enabled is set to False in the .ini file, then cache is
    disabled globally.
    """

    tg_locals = tg.request.environ['tg.locals']
    enabled = tg_locals.config.get("cache_enabled", "True")

    if not asbool(enabled):
        return func(*args, **kwargs)

    cache_extra_args = cache_extra_args or {}

    self = None
    if args:
        self = args[0]
    namespace, cache_key = create_cache_key(key_func, key_dict, self)

    if type:
        cache_extra_args['type'] = type

    cache_obj = getattr(tg_locals, 'cache', None)
    if not cache_obj:  # pragma: no cover
        raise Exception('TurboGears Cache object not found')

    my_cache = cache_obj.get_cache(namespace, **cache_extra_args)

    if expire == "never":
        cache_expire = None
    else:
        cache_expire = expire

    def create_func():
        result = func(*args, **kwargs)
        glob_response = tg_locals.response
        headers = glob_response.headerlist
        status = glob_response.status
        full_response = dict(headers=headers, status=status,
                             cookies=None, content=result)
        return full_response

    response = my_cache.get_value(cache_key,
                                  createfunc=create_func,
                                  expiretime=cache_expire,
                                  starttime=starttime)
    if cache_response:
        glob_response = tg_locals.response
        glob_response.headerlist = [header for header in response['headers']
                                    if header[0].lower() in cache_headers]
        glob_response.status = response['status']

    return response['content']


def beaker_cache(key="cache_default", expire="never", type=None,
                 query_args=False,
                 cache_headers=('content-type', 'content-length'),
                 invalidate_on_startup=False,
                 cache_response=True, **b_kwargs):
    """Cache decorator utilizing Beaker. Caches a
    function that returns a pickle-able object as a result.

    Optional arguments:

    ``key``
        None - No variable key, uses function name as key
        "cache_default" - Uses all function arguments as the key
        string - Use kwargs[key] as key
        list - Use [kwargs[k] for k in list] as key
    ``expire``
        Time in seconds before cache expires, or the string "never".
        Defaults to "never"
    ``type``
        Type of cache to use: dbm, memory, file, memcached, or None for
        Beaker's default
    ``query_args``
        Uses the query arguments as the key, defaults to False
    ``cache_headers``
        A tuple of header names indicating response headers that
        will also be cached.
    ``invalidate_on_startup``
        If True, the cache will be invalidated each time the application
        starts or is restarted.
    ``cache_response``
        Determines whether the response at the time beaker_cache is used
        should be cached or not, defaults to True.

        .. note::
            When cache_response is set to False, the cache_headers
            argument is ignored as none of the response is cached.

    If cache_enabled is set to False in the .ini file, then cache is
    disabled globally.

    """
    if invalidate_on_startup:
        starttime = time.time()
    else:
        starttime = None
    cache_headers = set(cache_headers)

    def beaker_cache_decorate(func):
        @wraps(func)
        def beaker_cached_call(*args, **kwargs):
            if key:
                key_dict = kwargs.copy()
                key_dict.update(_make_dict_from_args(func, args, kwargs))
                if query_args:
                    key_dict.update(tg.request.GET.mixed())

                if key != 'cache_default':
                    if isinstance(key, list):
                        key_dict = dict((k, key_dict[k]) for k in key)
                    else:
                        key_dict = {key: key_dict[key]}
            else:
                key_dict = None

            return _cached_call(func, args, kwargs, func, key_dict,
                                expire, type, starttime,
                                cache_headers, cache_response,
                                b_kwargs)

        return beaker_cached_call

    return beaker_cache_decorate


def create_cache_key(func, key_dict=None, self=None):
    """Get a cache namespace and key used by the beaker_cache decorator.

    Example::
        from tg import cache
        from tg.caching import create_cache_key
        namespace, key = create_cache_key(MyController.some_method)
        cache.get_cache(namespace).remove(key)

    """
    kls = None
    imfunc = im_func(func)
    if imfunc:
        kls = im_class(func)
        func = imfunc
        cache_key = func.__name__
    else:
        cache_key = func.__name__
    if key_dict:
        cache_key += " " + " ".join("%s=%s" % (k, v)
                                    for k, v in key_dict.items())

    if not kls and self:
        kls = getattr(self, '__class__', None)

    if kls:
        return '%s.%s' % (kls.__module__, kls.__name__), cache_key
    else:
        return func.__module__, cache_key


def _make_dict_from_args(func, args, kwargs):
    """Inspects function for name of args"""
    args_keys = {}
    for i, arg in enumerate(inspect.getargspec(func)[0]):
        if arg != "self":
            try:
                args_keys[arg] = args[i]
            except IndexError:
                args_keys[arg] = kwargs[arg]
    return args_keys

########NEW FILE########
__FILENAME__ = app_config
"""Configuration Helpers for TurboGears 2"""

import atexit
import os
import logging
import warnings
from copy import copy, deepcopy
import mimetypes
from collections import MutableMapping as DictMixin, deque

from tg.i18n import ugettext, get_lang

from tg.support.middlewares import SessionMiddleware, CacheMiddleware
from tg.support.middlewares import StaticsMiddleware, SeekableRequestBodyMiddleware, \
    DBSessionRemoverMiddleware
from tg.support.registry import RegistryManager
from tg.support.converters import asbool, asint, aslist
from tg.request_local import config as reqlocal_config

import tg
from tg.configuration.utils import coerce_config
from tg.util import Bunch, get_partial_dict, DottedFileNameFinder
from tg.configuration import milestones
from tg.configuration.utils import TGConfigError

from tg.renderers.genshi import GenshiRenderer
from tg.renderers.json import JSONRenderer
from tg.renderers.jinja import JinjaRenderer
from tg.renderers.mako import MakoRenderer
from tg.renderers.kajiki import KajikiRenderer

log = logging.getLogger(__name__)


class DispatchingConfigWrapper(DictMixin):
    """Wrapper for the Dispatching configuration.

    Simple wrapper for the DispatchingConfig object that provides attribute
    style access to the config dictionary.

    This class works by proxying all attribute and dictionary access to
    the underlying DispatchingConfig config object, which is an application local
    proxy that allows for multiple TG2 applications to live
    in the same process simultaneously, but to always get the right
    config data for the application that's requesting them.

    """

    def __init__(self, dict_to_wrap):
        """Initialize the object by passing in config to be wrapped"""
        self.__dict__['config_proxy'] = dict_to_wrap

    def __getitem__(self, key):
        return  self.config_proxy.current_conf()[key]

    def __setitem__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __getattr__(self, key):
        """Our custom attribute getter.

        Tries to get the attribute off the wrapped object first,
        if that does not work, tries dictionary lookup, and finally
        tries to grab all keys that start with the attribute and
        return sub-dictionaries that can be looked up.

        """
        try:
            return self.config_proxy.__getattribute__(key)
        except AttributeError:
            try:
                return self.config_proxy.current_conf()[key]
            except KeyError:
                return get_partial_dict(key, self.config_proxy.current_conf())

    def __setattr__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __delattr__(self, name):
        try:
            del self.config_proxy.current_conf()[name]
        except KeyError:
            raise AttributeError(name)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __len__(self):
        return len(self.config_proxy.current_conf())

    def __iter__(self):
        return iter(self.config_proxy.current_conf())

    def __repr__(self):
        return repr(self.config_proxy.current_conf())

    def keys(self):
        return self.config_proxy.keys()


defaults = {
    'debug': False,
    'package': None,
    'paths': {'root': None,
              'controllers': None,
              'templates': ['.'],
              'static_files': None},
    'tg.app_globals': None,
    'tg.strict_tmpl_context': True,
    'tg.pylons_compatible': True,
    'lang': None
}

# Push an empty config so all accesses to config at import time have something
# to look at and modify. This config will be merged with the app's when it's
# built in the paste.app_factory entry point.
reqlocal_config.push_process_config(deepcopy(defaults))

#Create a config object that has attribute style lookup built in.
config = DispatchingConfigWrapper(reqlocal_config)


def call_controller(tg_config, controller, remainder, params):
    return controller(*remainder, **params)


class _DeprecatedControllerWrapper(object):
    def __init__(self, controller_wrapper, config, next_wrapper):
        # Backward compatible old-way of configuring controller wrappers
        warnings.warn("Controller wrapper will now accept the configuration"
                      "as parameter when called instead of receiving it as"
                      "a constructor parameter, please refer to the documentation"
                      "to update your controller wrappers",
                      DeprecationWarning, stacklevel=2)

        def _adapted_next_wrapper(controller, remainder, params):
            return next_wrapper(tg.config._current_obj(),
                                controller, remainder, params)

        self.wrapper = controller_wrapper(config, _adapted_next_wrapper)

    def __call__(self, config, controller, remainder, params):
        return self.wrapper(controller, remainder, params)


class AppConfig(Bunch):
    """Class to store application configuration.

    This class should have configuration/setup information
    that is *necessary* for proper application function.
    Deployment specific configuration information should go in
    the config files (e.g. development.ini or deployment.ini).

    AppConfig instances have a number of methods that are meant to be
    overridden by users who wish to have finer grained control over
    the setup of the WSGI environment in which their application is run.

    This is the place to configure custom routes, transaction handling,
    error handling, etc.

    """

    def __init__(self, minimal=False, root_controller=None):
        """Creates some configuration defaults"""

        # Create a few bunches we know we'll use
        self.paths = Bunch()

        # Provide a default app_globals for single file applications
        self['tg.app_globals'] = Bunch({'dotted_filename_finder':DottedFileNameFinder()})

        # And also very often...
        self.sa_auth = Bunch()

        #Set individual defaults
        self.auto_reload_templates = True
        self.auth_backend = None
        self.stand_alone = True

        self.renderers = []
        self.default_renderer = 'genshi'
        self.render_functions = Bunch()
        self.rendering_engines = {}
        self.rendering_engines_without_vars = set()
        self.rendering_engines_options = {}

        self.enable_routes = False
        self.enable_routing_args = False
        self.disable_request_extensions = minimal

        self.use_ming = False
        self.use_sqlalchemy = False
        self.use_transaction_manager = not minimal
        self.commit_veto = None
        self.use_toscawidgets = not minimal
        self.use_toscawidgets2 = False
        self.prefer_toscawidgets2 = False
        self.use_dotted_templatenames = not minimal
        self.handle_error_page = not minimal
        self.registry_streaming = True

        self.use_sessions = not minimal
        self.i18n_enabled = not minimal
        self.serve_static = not minimal

        # Registry for functions to be called on startup/teardown
        self.call_on_startup = []
        self.call_on_shutdown = []
        self.controller_caller = call_controller
        self.controller_wrappers = []
        self.application_wrappers = []
        self.application_wrappers_dependencies = {False: [],
                                                  None: []}
        self.hooks = dict(before_validate=[],
                          before_call=[],
                          before_render=[],
                          after_render=[],
                          before_render_call=[],
                          after_render_call=[],
                          before_config=[],
                          after_config=[])

        # The codes TG should display an error page for. All other HTTP errors are
        # sent to the client or left for some middleware above us to handle
        self.handle_status_codes = [403, 404]

        #override this variable to customize how the tw2 middleware is set up
        self.custom_tw2_config = {}

        #This is for minimal mode to set root controller manually
        if root_controller is not None:
            self['tg.root_controller'] = root_controller

        self.register_rendering_engine(JSONRenderer)
        self.register_rendering_engine(GenshiRenderer)
        self.register_rendering_engine(MakoRenderer)
        self.register_rendering_engine(JinjaRenderer)
        self.register_rendering_engine(KajikiRenderer)

    def get_root_module(self):
        root_module_path = self.paths['root']
        if not root_module_path:
            return None

        base_controller_path = self.paths['controllers']
        controller_path = base_controller_path[len(root_module_path)+1:]
        root_controller_module = '.'.join([self.package_name] + controller_path.split(os.sep) + ['root'])
        return root_controller_module

    def register_hook(self, hook_name, func):
        warnings.warn("AppConfig.register_hook is deprecated, "
                      "please use tg.hooks.register and "
                      "tg.hooks.wrap_controller instead", DeprecationWarning)

        if hook_name == 'controller_wrapper':
            tg.hooks.wrap_controller(func)
        else:
            tg.hooks.register(hook_name, func)

    def register_wrapper(self, wrapper, after=None):
        """Registers a TurboGears application wrapper.

        Application wrappers are like WSGI middlewares but
        are executed in the context of TurboGears and work
        with abstractions like Request and Respone objects.

        Application wrappers are callables built by passing
        the next handler in chain and the current TurboGears
        configuration.

        Every wrapper, when called, is expected to accept
        the WSGI environment and a TurboGears context as parameters
        and are expected to return a :class:`tg.request_local.Response`
        instance::

            class AppWrapper(object):
                def __init__(self, handler, config):
                    self.handler = handler

                def __call__(self, environ, context):
                    print 'Going to run %s' % context.request.path
                    return self.handler(environ, context)
        """
        if milestones.environment_loaded.reached:
            # We must block registering wrappers if milestone passed, this is because
            # wrappers are consumed by TGApp constructor, and all the hooks available
            # after the milestone and that could register new wrappers are actually
            # called after TGApp constructors and so the wrappers wouldn't be applied.
            raise TGConfigError('Cannot register application wrappers after application '
                                'environment has already been loaded')

        self.application_wrappers_dependencies.setdefault(after, []).append(wrapper)
        milestones.environment_loaded.register(self._configure_application_wrappers)

    def register_rendering_engine(self, factory):
        """Registers a rendering engine ``factory``.

        Rendering engine factories are :class:`tg.renderers.base.RendererFactory`
        subclasses in charge of creating a rendering engine.

        """
        for engine, options in factory.engines.items():
            self.rendering_engines[engine] = factory
            self.rendering_engines_options[engine] = options
            if factory.with_tg_vars is False:
                self.rendering_engines_without_vars.add(engine)

    def _setup_startup_and_shutdown(self):
        for cmd in self.call_on_startup:
            if callable(cmd):
                try:
                    cmd()
                except Exception as error:
                    log.exception("Error registering %s at startup: %s" % (cmd, error ))
            else:
                log.warn("Unable to register %s for startup" % cmd )

        for cmd in self.call_on_shutdown:
            if callable(cmd):
                atexit.register(cmd)
            else:
                log.warn("Unable to register %s for shutdown" % cmd )

    def _configure_application_wrappers(self):
        visit_queue = deque([False, None])
        while visit_queue:
            current = visit_queue.popleft()
            if current not in (False, None):
                self.application_wrappers.append(current)

            dependant_wrappers = self.application_wrappers_dependencies.pop(current, [])
            visit_queue.extendleft(reversed(dependant_wrappers))

    def _configure_package_paths(self):
        root = os.path.dirname(os.path.abspath(self.package.__file__))
        # The default paths:
        paths = Bunch(root=root,
                     controllers=os.path.join(root, 'controllers'),
                     static_files=os.path.join(root, 'public'),
                     templates=[os.path.join(root, 'templates')])
        # If the user defined custom paths, then use them instead of the
        # default ones:
        paths.update(self.paths)
        self.paths = paths

    def _init_config(self, global_conf, app_conf):
        """Initialize the config object.

        Besides basic initialization, this method copies all the values
        in base_config into the ``tg.config`` objects.

        """
        # Load the mimetypes with its default types
        self.mimetypes = mimetypes.MimeTypes()

        try:
            self.package_name = self.package.__name__
        except AttributeError:
            self.package_name = None

        log.debug("Initializing configuration, package: '%s'", self.package_name)
        conf = global_conf.copy()
        conf.update(app_conf)
        conf.update(dict(app_conf=app_conf, global_conf=global_conf))
        conf.update(self.pop('environment_load', {}))
        conf['paths'] = self.paths
        conf['package_name'] = self.package_name
        conf['debug'] = asbool(conf.get('debug'))

        # Ensure all the keys from defaults are present, load them if not
        for key, val in deepcopy(defaults).items():
            conf.setdefault(key, val)

        # Ensure all paths are set, load default ones otherwise
        for key, val in defaults['paths'].items():
            conf['paths'].setdefault(key, val)

        # Load the errorware configuration from the Paste configuration file
        # These all have defaults, and emails are only sent if configured and
        # if this application is running in production mode
        errorware = {}
        errorware['debug'] = conf['debug']
        if not errorware['debug']:
            errorware['debug'] = False

            trace_errors_config = coerce_config(conf, 'trace_errors.', {'smtp_use_tls': asbool,
                                                                        'dump_request_size': asint,
                                                                        'dump_request': asbool,
                                                                        'dump_local_frames': asbool,
                                                                        'dump_local_frames_count': asint})
            if not trace_errors_config:
                # backward compatibility
                warnings.warn("direct usage of error tracing options has been deprecated, "
                              "please specify them as trace_errors.option_name instad of directly "
                              "setting option_name. EXAMPLE: trace_errors.error_email", DeprecationWarning)

                trace_errors_config['error_email'] = conf.get('email_to')
                trace_errors_config['error_log'] = conf.get('error_log', None)
                trace_errors_config['smtp_server'] = conf.get('smtp_server', 'localhost')
                trace_errors_config['smtp_use_tls'] = asbool(conf.get('smtp_use_tls', False))
                trace_errors_config['smtp_username'] = conf.get('smtp_username')
                trace_errors_config['smtp_password'] = conf.get('smtp_password')
                trace_errors_config['error_subject_prefix'] = conf.get('error_subject_prefix', 'WebApp Error: ')
                trace_errors_config['from_address'] = conf.get('from_address', conf.get('error_email_from', 'turbogears@yourapp.com'))
                trace_errors_config['error_message'] = conf.get('error_message', 'An internal server error occurred')
            else:
                # Provide Defaults
                trace_errors_config.setdefault('error_subject_prefix',
                                               'WebApp Error: ')
                trace_errors_config.setdefault('error_message',
                                               'An internal server error occurred')

            errorware.update(trace_errors_config)

        conf['tg.errorware'] = errorware

        slowreqsware = coerce_config(conf, 'trace_slowreqs.', {'smtp_use_tls': asbool,
                                                               'dump_request_size': asint,
                                                               'dump_request': asbool,
                                                               'dump_local_frames': asbool,
                                                               'dump_local_frames_count': asint,
                                                               'enable': asbool,
                                                               'interval': asint,
                                                               'exclude': aslist})
        slowreqsware.setdefault('error_subject_prefix', 'Slow Request: ')
        slowreqsware.setdefault('error_message', 'A request is taking too much time')
        for erroropt in errorware: slowreqsware.setdefault(erroropt, errorware[erroropt])
        conf['tg.slowreqs'] = slowreqsware

        # Copy in some defaults
        if 'cache_dir' in conf:
            conf.setdefault('beaker.session.data_dir', os.path.join(conf['cache_dir'], 'sessions'))
            conf.setdefault('beaker.cache.data_dir', os.path.join(conf['cache_dir'], 'cache'))
        conf['tg.cache_dir'] = conf.pop('cache_dir', conf['app_conf'].get('cache_dir'))

        if self.prefer_toscawidgets2:
            self.use_toscawidgets = False
            self.use_toscawidgets2 = True

        if not self.use_sqlalchemy:
            #Transaction manager is useless with Ming
            self.use_transaction_manager = False

        # Load conf dict into the global config object
        config.update(conf)

        if 'auto_reload_templates' in config:
            self.auto_reload_templates = asbool(config['auto_reload_templates'])

        config['application_root_module'] = self.get_root_module()
        if conf['paths']['root']:
            self.localedir = os.path.join(conf['paths']['root'], 'i18n')
        else:
            self.i18n_enabled = False

        if not conf['paths']['static_files']:
            self.serve_static = False

        self._configure_renderers()

        config.update(self)

        #see http://trac.turbogears.org/ticket/2247
        if asbool(config['debug']):
            config['tg.strict_tmpl_context'] = True
        else:
            config['tg.strict_tmpl_context'] = False

        self.after_init_config()
        self._configure_mimetypes()

        milestones.config_ready.reach()

    def _configure_renderers(self):
        """Provides default configurations for renderers"""
        if not 'json' in self.renderers:
            self.renderers.append('json')

        if self.default_renderer not in self.renderers:
            first_renderer = self.renderers[0]
            log.warn('Default renderer not in renders, automatically switching to %s' % first_renderer)
            self.default_renderer = first_renderer

    def _configure_mimetypes(self):
        lookup = {'.json': 'application/json',
                  '.js': 'application/javascript'}
        lookup.update(config.get('mimetype_lookup', {}))

        for key, value in lookup.items():
            self.mimetypes.add_type(value, key)

    def after_init_config(self):
        """
        Override this method to set up configuration variables at the application
        level.  This method will be called after your configuration object has
        been initialized on startup.  Here is how you would use it to override
        the default setting of tg.strict_tmpl_context ::

            from tg.configuration import AppConfig
            from tg import config

            class MyAppConfig(AppConfig):
                def after_init_config(self):
                    config['tg.strict_tmpl_context'] = False

            base_config = MyAppConfig()

        """

    def setup_routes(self):
        """Setup the default TG2 routes

        Override this and setup your own routes maps if you want to use
        custom routes.

        It is recommended that you keep the existing application routing in
        tact, and just add new connections to the mapper above the routes_placeholder
        connection.  Lets say you want to add a tg controller SamplesController,
        inside the controllers/samples.py file of your application.  You would
        augment the app_cfg.py in the following way::

            from routes import Mapper
            from tg.configuration import AppConfig

            class MyAppConfig(AppConfig):
                def setup_routes(self):
                    map = Mapper(directory=config['paths']['controllers'],
                                always_scan=config['debug'])

                    # Add a Samples route
                    map.connect('/samples/', controller='samples', action=index)

                    # Setup a default route for the root of object dispatch
                    map.connect('*url', controller='root', action='routes_placeholder')

                    config['routes.map'] = map


            base_config = MyAppConfig()

        """
        if not self.enable_routes:
            return None

        from routes import Mapper

        map = Mapper(directory=config['paths']['controllers'],
                     always_scan=config['debug'])

        # Setup a default route for the root of object dispatch
        map.connect('*url', controller='root', action='routes_placeholder')

        config['routes.map'] = map
        return map

    def setup_helpers_and_globals(self):
        """Add helpers and globals objects to the config.

        Override this method to customize the way that ``app_globals``
        and ``helpers`` are setup.

        """

        try:
            g = self.package.lib.app_globals.Globals()
        except AttributeError:
            log.warn('Application has a package but no lib.app_globals.Globals class is available.')
            return

        g.dotted_filename_finder = DottedFileNameFinder()
        config['tg.app_globals'] = g

        if config.get('tg.pylons_compatible', True):
            config['pylons.app_globals'] = g

    def setup_persistence(self):
        """Override this method to define how your application configures it's persistence model.
           the default is to setup sqlalchemy from the cofiguration file, but you might choose
           to set up a persistence system other than sqlalchemy, or add an additional persistence
           layer.  Here is how you would go about setting up a ming (mongo) persistence layer::

            class MingAppConfig(AppConfig):
                def setup_persistence(self):
                    self.ming_ds = DataStore(config['mongo.url'])
                    session = Session.by_name('main')
                    session.bind = self.ming_ds
        """
        if self.use_sqlalchemy:
            self.setup_sqlalchemy()
        elif self.use_ming:
            self.setup_ming()

    def setup_ming(self):
        """Setup MongoDB database engine using Ming"""
        try:
            from ming import create_datastore
            def create_ming_datastore(url, database, **kw):
                if database and url[-1] != '/':
                    url += '/'
                ming_url = url + database
                return create_datastore(ming_url, **kw)
        except ImportError: #pragma: no cover
            from ming.datastore import DataStore
            def create_ming_datastore(url, database, **kw):
                return DataStore(url, database=database, **kw)

        def mongo_read_pref(value):
            from pymongo.read_preferences import ReadPreference
            return getattr(ReadPreference, value)

        datastore_options = coerce_config(config, 'ming.connection.', {'max_pool_size':asint,
                                                                       'network_timeout':asint,
                                                                       'tz_aware':asbool,
                                                                       'safe':asbool,
                                                                       'journal':asbool,
                                                                       'wtimeout':asint,
                                                                       'fsync':asbool,
                                                                       'ssl':asbool,
                                                                       'read_preference':mongo_read_pref})
        datastore_options.pop('host', None)
        datastore_options.pop('port', None)

        datastore = create_ming_datastore(config['ming.url'], config.get('ming.db', ''), **datastore_options)
        config['tg.app_globals'].ming_datastore = datastore
        self.package.model.init_model(datastore)

    def setup_sqlalchemy(self):
        """Setup SQLAlchemy database engine.

        The most common reason for modifying this method is to add
        multiple database support.  To do this you might modify your
        app_cfg.py file in the following manner::

            from tg.configuration import AppConfig, config
            from myapp.model import init_model

            # add this before base_config =
            class MultiDBAppConfig(AppConfig):
                def setup_sqlalchemy(self):
                    '''Setup SQLAlchemy database engine(s)'''
                    from sqlalchemy import engine_from_config
                    engine1 = engine_from_config(config, 'sqlalchemy.first.')
                    engine2 = engine_from_config(config, 'sqlalchemy.second.')
                    # engine1 should be assigned to sa_engine as well as your first engine's name
                    config['tg.app_globals'].sa_engine = engine1
                    config['tg.app_globals'].sa_engine_first = engine1
                    config['tg.app_globals'].sa_engine_second = engine2
                    # Pass the engines to init_model, to be able to introspect tables
                    init_model(engine1, engine2)

            #base_config = AppConfig()
            base_config = MultiDBAppConfig()

        This will pull the config settings from your .ini files to create the necessary
        engines for use within your application.  Make sure you have a look at :ref:`multidatabase`
        for more information.

        """
        from sqlalchemy import engine_from_config

        balanced_master = config.get('sqlalchemy.master.url')
        if not balanced_master:
            engine = engine_from_config(config, 'sqlalchemy.')
        else:
            engine = engine_from_config(config, 'sqlalchemy.master.')
            config['balanced_engines'] = {'master':engine,
                                          'slaves':{},
                                          'all':{'master':engine}}

            all_engines = config['balanced_engines']['all']
            slaves = config['balanced_engines']['slaves']
            for entry in config.keys():
                if entry.startswith('sqlalchemy.slaves.'):
                    slave_path = entry.split('.')
                    slave_name = slave_path[2]
                    if slave_name == 'master':
                        raise TGConfigError('A slave node cannot be named master')
                    slave_config = '.'.join(slave_path[:3])
                    all_engines[slave_name] = slaves[slave_name] = engine_from_config(config, slave_config+'.')

            if not config['balanced_engines']['slaves']:
                raise TGConfigError('When running in balanced mode your must specify at least a slave node')

        # Pass the engine to initmodel, to be able to introspect tables
        config['tg.app_globals'].sa_engine = engine
        self.package.model.init_model(engine)

        if not hasattr(self, 'DBSession'):
            # If the user hasn't specified a scoped_session, assume
            # he/she uses the default DBSession in model
            model = getattr(self, 'model', self.package.model)
            self.DBSession = model.DBSession

    def setup_auth(self):
        """
        Override this method to define how you would like the authentication options
        to be setup for your application.
        """
        if hasattr(self, 'setup_sa_auth_backend'):
            warnings.warn("setup_sa_auth_backend is deprecated, please override"
                          "AppConfig.setup_auth instead", DeprecationWarning)
            self.setup_sa_auth_backend()
        elif self.auth_backend in ("ming", "sqlalchemy"):
            if 'beaker.session.secret' not in config:
                raise TGConfigError("You must provide a value for 'beaker.session.secret' "
                                    "If this is a project quickstarted with TG 2.0.2 or earlier "
                                    "double check that you have base_config['beaker.session.secret'] "
                                    "= 'mysecretsecret' in your app_cfg.py file.")

            # The developer must have defined a 'sa_auth' section, because
            # values such as the User, Group or Permission classes must be
            # explicitly defined.
            self.sa_auth.setdefault('form_plugin', None)
            self.sa_auth.setdefault('cookie_secret', config['beaker.session.secret'])

    def _setup_controller_wrappers(self):
        base_controller_caller = config.get('controller_caller')

        controller_caller = base_controller_caller
        for wrapper in self.get('controller_wrappers', []):
            try:
                controller_caller = wrapper(controller_caller)
            except TypeError:
                controller_caller = _DeprecatedControllerWrapper(wrapper, self, controller_caller)
        config['controller_caller'] = controller_caller

    def _setup_renderers(self):
        for renderer in self.renderers[:]:
            setup = getattr(self, 'setup_%s_renderer'%renderer, None)
            if setup is not None:
                # Backward compatible old-way of configuring rendering engines
                warnings.warn("Using setup_NAME_renderer to configure rendering engines"
                              "is now deprecated, please use register_rendering_engine "
                              "with a tg.renderers.base.RendererFactory subclass instead",
                              DeprecationWarning, stacklevel=2)

                success = setup()
                if success is False:
                    log.error('Failed to initialize %s template engine, removing it...' % renderer)
                    self.renderers.remove(renderer)
            elif renderer in self.rendering_engines:
                rendering_engine = self.rendering_engines[renderer]
                engines = rendering_engine.create(config, config['tg.app_globals'])
                if engines is None:
                    log.error('Failed to initialize %s template engine, removing it...' % renderer)
                    self.renderers.remove(renderer)
                else:
                    self.render_functions.update(engines)
            else:
                raise TGConfigError('This configuration object does not support the %s renderer' % renderer)

        milestones.renderers_ready.reach()

    def make_load_environment(self):
        """Return a load_environment function.

        The returned load_environment function can be called to configure
        the TurboGears runtime environment for this particular application.
        You can do this dynamically with multiple nested TG applications
        if necessary.

        """

        def load_environment(global_conf, app_conf):
            """Configure the TurboGears environment via ``tg.configuration.config``."""
            global_conf = Bunch(global_conf)
            app_conf = Bunch(app_conf)

            try:
                app_package = self.package
            except AttributeError:
                #if we don't have a specified package, don't try
                #to detect paths and helpers from the package.
                #Expect the user to specify them.
                app_package = None

            if app_package:
                self._configure_package_paths()

            self._init_config(global_conf, app_conf)

            #Registers functions to be called at startup and shutdown
            #from self.call_on_startup and shutdown respectively.
            self._setup_startup_and_shutdown()

            self.setup_routes()

            if app_package:
                self.setup_helpers_and_globals()

            self.setup_auth()
            self._setup_renderers()
            self.setup_persistence()

            # Trigger milestone here so that it gets triggered even when
            # websetup (setup-app command) is performed.
            milestones.environment_loaded.reach()

        return load_environment

    def add_error_middleware(self, global_conf, app):
        """Add middleware which handles errors and exceptions."""
        from tg.error import ErrorReporter
        app = ErrorReporter(app, global_conf, **config['tg.errorware'])

        if self.handle_error_page:
            from tg.support.middlewares import StatusCodeRedirect

            # Display error documents for self.handle_status_codes status codes (and
            # 500 when debug is disabled)
            if asbool(config['debug']):
                app = StatusCodeRedirect(app, self.handle_status_codes)
            else:
                app = StatusCodeRedirect(app, self.handle_status_codes + [500])

        return app

    def add_slowreqs_middleware(self, global_conf, app):
        from tg.error import SlowReqsReporter
        return SlowReqsReporter(app, global_conf, **config['tg.slowreqs'])

    def add_debugger_middleware(self, global_conf, app):
        from tg.error import ErrorHandler
        return ErrorHandler(app, global_conf)

    def add_auth_middleware(self, app, skip_authentication):
        """
        Configure authentication and authorization.

        :param app: The TG2 application.
        :param skip_authentication: Should authentication be skipped if
            explicitly requested? (used by repoze.who-testutil)
        :type skip_authentication: bool

        """
        # Start with the current configured authentication options.
        # Depending on the auth backend a new auth_args dictionary
        # can replace this one later on.
        auth_args = copy(self.sa_auth)

        # Configuring auth logging:
        if 'log_stream' not in self.sa_auth:
            auth_args['log_stream'] = logging.getLogger('auth')

        # Removing keywords not used by repoze.who:
        auth_args.pop('password_encryption_method', None)

        if not skip_authentication and 'cookie_secret' not in auth_args:
            raise TGConfigError("base_config.sa_auth.cookie_secret is required "
                                "you must define it in app_cfg.py or set "
                                "sa_auth.cookie_secret in development.ini")

        if 'authmetadata' not in auth_args: #pragma: no cover
            # authmetadata not provided, fallback to old authentication setup
            if self.auth_backend == "sqlalchemy":
                from repoze.what.plugins.quickstart import setup_sql_auth
                app = setup_sql_auth(app, skip_authentication=skip_authentication, **auth_args)
            elif self.auth_backend == "ming":
                from tgming import setup_ming_auth
                app = setup_ming_auth(app, skip_authentication=skip_authentication, **auth_args)
        else:
            try:
                pos = auth_args['authenticators'].index(('default', None))
            except KeyError:
                # Didn't specify authenticators, setup default one
                pos = None
            except ValueError:
                # Specified authenticators and default is not in there
                # so we want to skip default TG auth configuration.
                pos = -1

            if pos is None or pos >= 0:
                if getattr(auth_args['authmetadata'], 'authenticate', None) is not None:
                    from tg.configuration.auth import create_default_authenticator
                    auth_args, tgauth = create_default_authenticator(**auth_args)
                    authenticator = ('tgappauth', tgauth)
                elif self.auth_backend == "sqlalchemy":
                    from tg.configuration.sqla.auth import create_default_authenticator
                    auth_args, sqlauth = create_default_authenticator(**auth_args)
                    authenticator = ('sqlauth', sqlauth)
                elif self.auth_backend == "ming":
                    from tg.configuration.mongo.auth import create_default_authenticator
                    auth_args, mingauth = create_default_authenticator(**auth_args)
                    authenticator = ('mingauth', mingauth)
                else:
                    authenticator = None

                if authenticator is not None:
                    if pos is None:
                        auth_args['authenticators'] = [authenticator]
                    else:
                        # We make a copy so that we don't modify the original one.
                        auth_args['authenticators'] = copy(auth_args['authenticators'])
                        auth_args['authenticators'][pos] = authenticator

            from tg.configuration.auth import setup_auth
            app = setup_auth(app, skip_authentication=skip_authentication, **auth_args)

        return app

    def add_core_middleware(self, app):
        """Add support for routes dispatch, sessions, and caching.
        This is where you would want to override if you wanted to provide your
        own routing, session, or caching middleware.  Your app_cfg.py might look something
        like this::

            from tg.configuration import AppConfig
            from routes.middleware import RoutesMiddleware
            from beaker.middleware import CacheMiddleware
            from mysessionier.middleware import SessionMiddleware

            class MyAppConfig(AppConfig):
                def add_core_middleware(self, app):
                    app = RoutesMiddleware(app, config['routes.map'])
                    app = SessionMiddleware(app, config)
                    app = CacheMiddleware(app, config)
                    return app
            base_config = MyAppConfig()
        """
        if self.enable_routes:
            warnings.warn("Internal routes support will be deprecated soon, please "
                          "consider using tgext.routes instead", DeprecationWarning)
            from routes.middleware import RoutesMiddleware
            app = RoutesMiddleware(app, config['routes.map'])

        if self.use_sessions:
            app = SessionMiddleware(app, config)
        
        app = CacheMiddleware(app, config)

        return app

    def add_tosca_middleware(self, app):
        """Configure the ToscaWidgets middleware.

        If you would like to override the way the TW middleware works, you might do something like::

            from tg.configuration import AppConfig
            from tw.api import make_middleware as tw_middleware

            class MyAppConfig(AppConfig):

                def add_tosca2_middleware(self, app):

                    app = tw_middleware(app, {
                        'toscawidgets.framework.default_view': self.default_renderer,
                        'toscawidgets.framework.translator': ugettext,
                        'toscawidgets.middleware.inject_resources': False,
                        })
                    return app

            base_config = MyAppConfig()



        The above example would disable resource injection.

        There is more information about the settings you can change
        in the ToscaWidgets `middleware. <http://toscawidgets.org/documentation/ToscaWidgets/modules/middleware.html>`


        """

        import tw
        from tw.api import make_middleware as tw_middleware

        twconfig = {'toscawidgets.framework.default_view': self.default_renderer,
                    'toscawidgets.framework.translator': ugettext,
                    'toscawidgets.middleware.inject_resources': True,
                    }
        for k,v in config.items():
            if k.startswith('toscawidgets.framework.') or k.startswith('toscawidgets.middleware.'):
                twconfig[k] = v

        if 'toscawidgets.framework.resource_variant' in config:
            import tw.api
            tw.api.resources.registry.ACTIVE_VARIANT = config['toscawidgets.framework.resource_variant']
            #remove it from the middleware madness
            del twconfig['toscawidgets.framework.resource_variant']

        app = tw_middleware(app, twconfig)

        if self.default_renderer in ('genshi','mako'):
            tw.framework.default_view = self.default_renderer

        return app

    def add_tosca2_middleware(self, app):
        """Configure the ToscaWidgets2 middleware.

        If you would like to override the way the TW2 middleware works,
        you might do change your app_cfg.py to add something like::

            from tg.configuration import AppConfig
            from tw2.core.middleware import TwMiddleware

            class MyAppConfig(AppConfig):

                def add_tosca2_middleware(self, app):

                    app = TwMiddleware(app,
                        default_engine=self.default_renderer,
                        translator=ugettext,
                        auto_reload_templates = False
                        )

                    return app
            base_config = MyAppConfig()



        The above example would always set the template auto reloading off. (This is normally an
        option that is set within your application's ini file.)
        """
        from tw2.core.middleware import Config, TwMiddleware

        shared_engines = list(set(self.renderers) & set(Config.preferred_rendering_engines))
        if not shared_engines:
            raise TGConfigError('None of the configured rendering engines is supported'
                                'by ToscaWidgets2, unable to configure ToscaWidgets.')

        if self.default_renderer in shared_engines:
            tw2_engines = [self.default_renderer] + shared_engines
            tw2_default_engine = self.default_renderer
        else:
            # If preferred rendering engine is not available in TW2, fallback to another one
            # This happens for Kajiki which is not supported by recent TW2 versions.
            tw2_engines = shared_engines
            tw2_default_engine = shared_engines[0]

        default_tw2_config = dict( default_engine=tw2_default_engine,
                                   preferred_rendering_engines=tw2_engines,
                                   translator=ugettext,
                                   get_lang=lambda: get_lang(all=False),
                                   auto_reload_templates=self.auto_reload_templates,
                                   controller_prefix='/tw2/controllers/',
                                   res_prefix='/tw2/resources/',
                                   debug=config['debug'],
                                   rendering_extension_lookup={
                                        'mako': ['mak', 'mako'],
                                        'genshi': ['genshi', 'html'],
                                        'jinja':['jinja', 'jinja2'],
                                        'kajiki':['kajiki', 'xml']
                                   })
        default_tw2_config.update(self.custom_tw2_config)
        app = TwMiddleware(app, **default_tw2_config)
        return app

    def add_static_file_middleware(self, app):
        app = StaticsMiddleware(app, config['paths']['static_files'])
        return app

    def add_tm_middleware(self, app):
        """Set up the transaction management middleware.

        To abort a transaction inside a TG2 app::

          import transaction
          transaction.doom()

        By default http error responses also roll back transactions, but this
        behavior can be overridden by overriding base_config.commit_veto.

        """
        from tg.support.transaction_manager import TGTransactionManager

        #TODO: remove self.commit_veto option in future release
        #backward compatibility with "commit_veto" option
        config['tm.commit_veto'] = self.commit_veto

        return TGTransactionManager(app, config)

    def add_ming_middleware(self, app):
        """Set up the ming middleware for the unit of work"""
        import ming.odm.middleware
        return ming.odm.middleware.MingMiddleware(app)

    def add_sqlalchemy_middleware(self, app):
        """Set up middleware that cleans up the sqlalchemy session.

        The default behavior of TG 2 is to clean up the session on every
        request.  Only override this method if you know what you are doing!

        """
        return DBSessionRemoverMiddleware(self.DBSession, app)

    def setup_tg_wsgi_app(self, load_environment=None):
        """Create a base TG app, with all the standard middleware.

        ``load_environment``
            A required callable, which sets up the basic evironment
            needed for the application.
        ``setup_vars``
            A dictionary with all special values necessary for setting up
            the base wsgi app.

        """

        def make_base_app(global_conf=None, wrap_app=None, full_stack=False, **app_conf):
            """Create a tg WSGI application and return it.

            ``wrap_app``
                a WSGI middleware component which takes the core turbogears
                application and wraps it -- inside all the WSGI-components
                provided by TG and Pylons. This allows you to work with the
                full environment that your TG application would get before
                anything happens in the application itself.

            ``global_conf``
                The inherited configuration for this application. Normally
                from the [DEFAULT] section of the Paste ini file.

            ``full_stack``
                Whether or not this application provides a full WSGI stack (by
                default, meaning it handles its own exceptions and errors).
                Disable full_stack when this application is "managed" by
                another WSGI middleware.

            ``app_conf``
                The application's local configuration. Normally specified in
                the [app:<name>] section of the Paste ini file (where <name>
                defaults to main).

            """
            from tg import TGApp

            if global_conf is None:
                global_conf = {}

            # Configure the Application environment
            if load_environment:
                load_environment(global_conf, app_conf)

            # trigger the environment_loaded milestone again, so that
            # when load_environment is not provided the attached actions gets performed anyway.
            milestones.environment_loaded.reach()

            # Apply controller wrappers to controller caller
            self._setup_controller_wrappers()

            # TODO: This should be moved in configuration phase.
            # It is here as it requires both the .ini file and AppConfig to be ready
            avoid_sess_touch = config.get('beaker.session.tg_avoid_touch', 'false')
            config['beaker.session.tg_avoid_touch'] = asbool(avoid_sess_touch)

            app = TGApp()
            if wrap_app:
                app = wrap_app(app)

            app = tg.hooks.notify_with_value('before_config', app, context_config=config)

            app = self.add_core_middleware(app)

            if self.auth_backend:
                # Skipping authentication if explicitly requested. Used by
                # repoze.who-testutil:
                skip_authentication = app_conf.get('skip_authentication', False)
                app = self.add_auth_middleware(app, skip_authentication)

            if self.use_transaction_manager:
                app = self.add_tm_middleware(app)

            # TODO: Middlewares before this point should be converted to App Wrappers.
            # They provide some basic TG features like AUTH, Caching and transactions
            # which should be app wrappers to make possible to add wrappers in the
            # stack before or after them.

            if self.use_toscawidgets:
                app = self.add_tosca_middleware(app)

            if self.use_toscawidgets2:
                app = self.add_tosca2_middleware(app)

            # from here on the response is a generator
            # so any middleware that relies on the response to be
            # a string needs to be applied before this point.

            if self.use_sqlalchemy:
                app = self.add_sqlalchemy_middleware(app)

            if self.use_ming:
                app = self.add_ming_middleware(app)

            if config.get('make_body_seekable'):
                app = SeekableRequestBodyMiddleware(app)

            if 'PYTHONOPTIMIZE' in os.environ:
                warnings.warn("Forcing full_stack=False due to PYTHONOPTIMIZE enabled. "+\
                              "Error Middleware will be disabled", RuntimeWarning, stacklevel=2)
                full_stack = False

            if asbool(full_stack):
                # This should never be true for internal nested apps
                if (self.auth_backend is None
                        and 401 not in self.handle_status_codes):
                    # If there's no auth backend configured which traps 401
                    # responses we redirect those responses to a nicely
                    # formatted error page
                    self.handle_status_codes.append(401)
                app = self.add_slowreqs_middleware(global_conf, app)
                app = self.add_error_middleware(global_conf, app)

            # Establish the registry for this application
            app = RegistryManager(app, streaming=config.get('registry_streaming', True),
                                  preserve_exceptions=asbool(global_conf.get('debug')))

            # Place the debuggers after the registry so that we
            # can preserve context in case of exceptions
            app = self.add_debugger_middleware(global_conf, app)

            # Static files (if running in production, and Apache or another
            # web server is serving static files)

            #if the user has set the value in app_config, don't pull it from the ini
            forced_serve_static = config.get('serve_static')
            if forced_serve_static is not None:
                self.serve_static = asbool(forced_serve_static)

            if self.serve_static:
                app = self.add_static_file_middleware(app)

            app = tg.hooks.notify_with_value('after_config', app, context_config=config)

            return app

        return make_base_app

    def make_wsgi_app(self, **app_conf):
        loadenv = self.make_load_environment()
        return self.setup_tg_wsgi_app(loadenv)(**app_conf)

########NEW FILE########
__FILENAME__ = fastform
from tg.controllers.util import _build_url

try:
    from urlparse import urlparse, urlunparse, parse_qs
except ImportError: #pragma: no cover
    from urllib.parse import urlparse, urlunparse, parse_qs

try:
    from urllib import urlencode
except ImportError: #pragma: no cover
    from urllib.parse import urlencode

from webob import Request
from webob.exc import HTTPFound, HTTPUnauthorized
from zope.interface import implementer

from repoze.who.interfaces import IChallenger, IIdentifier

@implementer(IChallenger, IIdentifier)
class FastFormPlugin(object):
    """
    Simplified and faster version of the repoze.who.friendlyforms
    FriendlyForm plugin. The FastForm version works only with UTF-8
    content which is the default for new WebOb versions.
    """
    classifications = {
        IIdentifier: ["browser"],
        IChallenger: ["browser"],
        }

    def __init__(self, login_form_url, login_handler_path, post_login_url,
                 logout_handler_path, post_logout_url, rememberer_name,
                 login_counter_name=None):
        """
        :param login_form_url: The URL/path where the login form is located.
        :type login_form_url: str
        :param login_handler_path: The URL/path where the login form is
            submitted to (where it is processed by this plugin).
        :type login_handler_path: str
        :param post_login_url: The URL/path where the user should be redirected
            to after login (even if wrong credentials were provided).
        :type post_login_url: str
        :param logout_handler_path: The URL/path where the user is logged out.
        :type logout_handler_path: str
        :param post_logout_url: The URL/path where the user should be
            redirected to after logout.
        :type post_logout_url: str
        :param rememberer_name: The name of the repoze.who identifier which
            acts as rememberer.
        :type rememberer_name: str
        """
        self.login_form_url = login_form_url
        self.login_handler_path = login_handler_path
        self.post_login_url = post_login_url
        self.logout_handler_path = logout_handler_path
        self.post_logout_url = post_logout_url
        self.rememberer_name = rememberer_name

        if not login_counter_name:
            login_counter_name = '__logins'
        self.login_counter_name = login_counter_name

    # IIdentifier
    def identify(self, environ):
        path_info = environ['PATH_INFO']

        if path_info == self.login_handler_path:
            query = self._get_form_data(environ)

            try:
                credentials = {'login': query['login'],
                               'password': query['password'],
                               'max_age':query.get('remember')}
            except KeyError:
                credentials = None

            params = {}
            if 'came_from' in query:
                params['came_from'] = query['came_from']
            if self.login_counter_name is not None and self.login_counter_name in query:
                params[self.login_counter_name] = query[self.login_counter_name]

            destination = _build_url(environ, self.post_login_url, params=params)
            environ['repoze.who.application'] = HTTPFound(location=destination)
            return credentials

        elif path_info == self.logout_handler_path:
            query = self._get_form_data(environ)
            came_from = query.get('came_from')
            if came_from is None:
                came_from = _build_url(environ, '/')

            # set in environ for self.challenge() to find later
            environ['came_from'] = came_from
            environ['repoze.who.application'] = HTTPUnauthorized()

        elif path_info in (self.login_form_url, self.post_login_url):
            query = self._get_form_data(environ)
            environ['repoze.who.logins'] = 0

            if self.login_counter_name is not None and self.login_counter_name in query:
                environ['repoze.who.logins'] = int(query[self.login_counter_name])
                del query[self.login_counter_name]
                environ['QUERY_STRING'] = urlencode(query, doseq=True)

        return None

    # IChallenger
    def challenge(self, environ, status, app_headers, forget_headers):
        path_info = environ['PATH_INFO']

        # Configuring the headers to be set:
        cookies = [(h,v) for (h,v) in app_headers if h.lower() == 'set-cookie']
        headers = forget_headers + cookies

        if path_info == self.logout_handler_path:
            params = {}
            if 'came_from' in environ:
                params.update({'came_from':environ['came_from']})
            destination = _build_url(environ, self.post_logout_url, params=params)

        else:
            came_from_params = parse_qs(environ.get('QUERY_STRING', ''))
            params = {'came_from': _build_url(environ, path_info, came_from_params)}
            destination = _build_url(environ, self.login_form_url, params=params)

        return HTTPFound(location=destination, headers=headers)

    # IIdentifier
    def remember(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.remember(environ, identity)

    # IIdentifier
    def forget(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.forget(environ, identity)

    def _get_rememberer(self, environ):
        rememberer = environ['repoze.who.plugins'][self.rememberer_name]
        return rememberer

    def _get_form_data(self, environ):
        request = Request(environ)
        query = dict(request.GET)
        query.update(request.POST)
        return query

    def __repr__(self):
        return '<%s:%s %s>' % (self.__class__.__name__, self.login_handler_path, id(self))

########NEW FILE########
__FILENAME__ = metadata
from zope.interface import implementer
from repoze.who.interfaces import IMetadataProvider, IAuthenticator


class TGAuthMetadata(object):
    """
    Provides a way to lookup for user, groups and permissions
    given the current identity. This has to be specialized
    for each storage backend.

    By default it returns empty lists for groups and permissions
    and None for the user.
    """
    def get_user(self, identity, userid):
        return None

    def get_groups(self, identity, userid):
        return []

    def get_permissions(self, identity, userid):
        return []


@implementer(IMetadataProvider)
class _AuthMetadataProvider(object):
    """
    repoze.who metadata provider to load groups and permissions data for
    the current user. This uses a :class:`TGAuthMetadata` to fetch
    the groups and permissions.
    """

    def __init__(self, tgmdprovider):
        self.tgmdprovider = tgmdprovider

    # IMetadataProvider
    def add_metadata(self, environ, identity):
        # Get the userid retrieved by repoze.who Authenticator
        userid = identity['repoze.who.userid']

        # Finding the user, groups and permissions:
        identity['user'] = self.tgmdprovider.get_user(identity, userid)
        if identity['user']:
            identity['groups'] = self.tgmdprovider.get_groups(identity, userid)
            identity['permissions'] = self.tgmdprovider.get_permissions(identity, userid)
        else:
            identity['groups'] = identity['permissions'] = []

        # Adding the groups and permissions to the repoze.what
        # credentials for repoze.what compatibility:
        if 'repoze.what.credentials' not in environ:
            environ['repoze.what.credentials'] = {}
        environ['repoze.what.credentials'].update(identity)
        environ['repoze.what.credentials']['repoze.what.userid'] = userid


@implementer(IAuthenticator)
class _AuthMetadataAuthenticator(object):
    def __init__(self, tgmdprovider, using_password):
        self.tgmdprovider = tgmdprovider
        self.using_password = using_password

    # IAuthenticator
    def authenticate(self, environ, identity):
        if self.using_password and not ('login' in identity and 'password' in identity):
            return None
        return self.tgmdprovider.authenticate(environ, identity)


def create_default_authenticator(using_password=True, translations=None,
                                 user_class=None, dbsession=None,
                                 **kept_params):
    auth = _AuthMetadataAuthenticator(kept_params['authmetadata'], using_password)
    return kept_params, auth

########NEW FILE########
__FILENAME__ = hooks
# -*- coding: utf-8 -*-
"""
Utilities for TurboGears hooks management.

Provides a consistent API to register and execute hooks.

"""
from tg.configuration.utils import TGConfigError
from tg.configuration.milestones import config_ready, renderers_ready, environment_loaded
from tg.decorators import Decoration
from tg._compat import default_im_func
import tg

from logging import getLogger
log = getLogger(__name__)


class _TGHooks(object):
    """Manages hooks registrations and notifications"""

    def register(self, hook_name, func, controller=None):
        """Registers a TurboGears hook.

        Given an hook name and a function it registers the provided
        function for that role. For a complete list of hooks
        provided by default have a look at :ref:`hooks_and_events`.

        It permits to register hooks both application wide
        or for specific controllers::

            tg.hooks.register('before_render', hook_func, controller=RootController.index)
            tg.hooks.register('startup', startup_function)

        """
        if hook_name in ('startup', 'shutdown') and controller is not None:
            raise TGConfigError('Startup and Shutdown hooks cannot be registered on controllers')

        if hook_name == 'controller_wrapper':
            raise TGConfigError('tg.hooks.wrap_controller must be used to register wrappers')

        if controller is None:
            config_ready.register(_ApplicationHookRegistration(hook_name, func))
        else:
            controller = default_im_func(controller)
            renderers_ready.register(_ControllerHookRegistration(controller, hook_name, func))

    def wrap_controller(self, func, controller=None):
        """Registers a TurboGears controller wrapper.

        Controller Wrappers are much like a **decorator** applied to
        every controller.
        They receive :class:`tg.configuration.AppConfig` instance
        as an argument and the next handler in chain and are expected
        to return a new handler that performs whatever it requires
        and then calls the next handler.

        A simple example for a controller wrapper is a simple logging wrapper::

            def controller_wrapper(app_config, caller):
                def call(*args, **kw):
                    try:
                        print 'Before handler!'
                        return caller(*args, **kw)
                    finally:
                        print 'After Handler!'
                return call

            tg.hooks.wrap_controller(controller_wrapper)

        It is also possible to register wrappers for a specific controller::

            tg.hooks.wrap_controller(controller_wrapper, controller=RootController.index)

        """
        if environment_loaded.reached:
            raise TGConfigError('Controller wrappers can be registered only at '
                                'configuration time.')

        if controller is None:
            environment_loaded.register(_ApplicationHookRegistration('controller_wrapper', func))
        else:
            controller = default_im_func(controller)
            registration = _ControllerHookRegistration(controller, 'controller_wrapper', func)
            renderers_ready.register(registration)

    def notify(self, hook_name, args=None, kwargs=None, controller=None, context_config=None):
        """Notifies a TurboGears hook.

        Each function registered for the given hook will be executed,
        ``args`` and ``kwargs`` will be passed to the registered functions
        as arguments.

        It permits to notify both application hooks::

            tg.hooks.notify('custom_global_hook')

        Or controller hooks::

            tg.hooks.notify('before_render', args=(remainder, params, output),
                            controller=RootController.index)

        """
        if context_config is None: #pragma: no cover
            context_config = tg.config._current_obj()

        args = args or []
        kwargs = kwargs or {}

        try:
            syswide_hooks = context_config['hooks'][hook_name]
            for func in syswide_hooks:
                func(*args, **kwargs)
        except KeyError: #pragma: no cover
            pass

        if controller is not None:
            controller = default_im_func(controller)
            deco = Decoration.get_decoration(controller)
            for func in deco.hooks.get(hook_name, []):
                func(*args, **kwargs)

    def notify_with_value(self, hook_name, value, controller=None, context_config=None):
        """Notifies a TurboGears hook which is expected to return a value.

        hooks with values are expected to accept an input value an return
        a replacement for it. Each registered function will receive as input
        the value returned by the previous function in chain.

        The resulting value will be returned by the ``notify_with_value``
        call itself::

            app = tg.hooks.notify_with_value('before_config', app)

        """
        if context_config is None: #pragma: no cover
            context_config = tg.config._current_obj()

        try:
            syswide_hooks = context_config['hooks'][hook_name]
            for func in syswide_hooks:
                value = func(value)
        except KeyError: #pragma: no cover
            pass

        if controller is not None:
            controller = default_im_func(controller)
            deco = Decoration.get_decoration(controller)
            for func in deco.hooks[hook_name]:
                value = func(value)

        return value


class _ApplicationHookRegistration(object):
    def __init__(self, hook_name, func):
        self.hook_name = hook_name
        self.func = func

    def __call__(self):
        log.debug("Registering %s for application wide hook %s",
                  self.func, self.hook_name)

        config = tg.config._current_obj()
        if self.hook_name == 'startup':
            config['call_on_startup'].append(self.func)
        elif self.hook_name == 'shutdown':
            config['call_on_shutdown'].append(self.func)
        elif self.hook_name == 'controller_wrapper':
            config['controller_wrappers'].append(self.func)
        else:
            config['hooks'].setdefault(self.hook_name, []).append(self.func)


class _ControllerHookRegistration(object):
    def __init__(self, controller, hook_name, func):
        self.controller = controller
        self.hook_name = hook_name
        self.func = func

    def __call__(self):
        log.debug("Registering %s for hook %s on controller %s",
                  self.func, self.hook_name, self.controller)

        if self.hook_name == 'controller_wrapper':
            deco = Decoration.get_decoration(self.controller)
            deco._register_controller_wrapper(self.func)
        else:
            deco = Decoration.get_decoration(self.controller)
            deco._register_hook(self.hook_name, self.func)


hooks = _TGHooks()

########NEW FILE########
__FILENAME__ = milestones
# -*- coding: utf-8 -*-
"""
Utilities for lazy resolution of configurations.

Provides a bunch of tools to perform actions that need
the configuration to be in place when performed

"""

from logging import getLogger
log = getLogger(__name__)


class _ConfigMilestoneTracker(object):
    """Tracks actions that need to be performed
    when a specific configuration point is reached
    and required options are correctly initialized

    """
    def __init__(self, name):
        self.name = name
        self._actions = dict()
        self._reached = False

    @property
    def reached(self):
        return self._reached

    def register(self, action):
        """Registers an action to be called on milestone completion.

        If milestone is already passed action is immediately called

        """
        if self._reached:
            log.debug('%s milestone passed, calling %s directly', self.name, action)
            action()
        else:
            log.debug('Register %s to be called when %s reached', action, self.name)
            self._actions[id(action)] = action

    def reach(self):
        """Marks the milestone as reached.

        Runs the registered actions. Calling this
        method multiple times should lead to nothing.

        """
        self._reached = True

        log.debug('%s milestone reached', self.name)
        while True:
            try:
                __, action = self._actions.popitem()
                action()
            except KeyError:
                break

    def _reset(self):
        """This is just for testing purposes"""
        self._reached = False
        self._actions = dict()


config_ready = _ConfigMilestoneTracker('config_ready')
renderers_ready = _ConfigMilestoneTracker('renderers_ready')
environment_loaded = _ConfigMilestoneTracker('environment_loaded')


def _reset_all():
    """Utility method for the test suite to reset milestones"""
    config_ready._reset()
    renderers_ready._reset()
    environment_loaded._reset()


def _reach_all():
    """Utility method for the test suite to reach all milestones"""
    config_ready.reach()
    renderers_ready.reach()
    environment_loaded.reach()

########NEW FILE########
__FILENAME__ = auth
# -*- coding: utf-8 -*-
from tgming.auth import MingAuthenticatorPlugin

def create_default_authenticator(user_class, translations=None, **unused):
    mingauth = MingAuthenticatorPlugin(user_class)
    return unused, mingauth

########NEW FILE########
__FILENAME__ = auth
# -*- coding: utf-8 -*-
from repoze.who.plugins.sa import SQLAlchemyAuthenticatorPlugin

def create_default_authenticator(user_class, dbsession, translations=None, **unused):
    sqlauth = SQLAlchemyAuthenticatorPlugin(user_class, dbsession)
    if translations is not None:
        sqlauth.translations.update(translations)
    return unused, sqlauth

########NEW FILE########
__FILENAME__ = balanced_session
import tg
import random, logging

try:
    from sqlalchemy.orm import Session
except ImportError: #pragma: no cover
    class Session(object):
        """SQLAlchemy Session"""

log = logging.getLogger(__name__)

class BalancedSession(Session):
    _force_engine = None

    def get_bind(self, mapper=None, clause=None):
        config = tg.config._current_obj()

        engines = config.get('balanced_engines')
        if not engines:
            log.debug('Balancing disabled, using master')
            return config['tg.app_globals'].sa_engine

        forced_engine = self._force_engine
        if not forced_engine:
            try:
                forced_engine = tg.request._tg_force_sqla_engine
            except TypeError:
                forced_engine = 'master'
            except AttributeError:
                pass

        if forced_engine:
            log.debug('Forced engine: %s', forced_engine)
            return engines['all'][forced_engine]
        elif self._flushing:
            log.debug('Choose engine: master')
            return engines['master']
        else:
            choosen_slave = random.choice(list(engines['slaves'].keys()))
            log.debug('Choose engine: %s', choosen_slave)
            return engines['slaves'][choosen_slave]

    def using_engine(self, engine_name):
        return UsingEngineContext(engine_name, self)

class UsingEngineContext(object):
    def __init__(self, engine_name, DBSession=None):
        self.engine_name = engine_name
        if not DBSession:
            DBSession = tg.config['DBSession']()
        self.session = DBSession
        self.past_engine = self.session._force_engine

    def __enter__(self):
        self.session._force_engine = self.engine_name
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        self.session._force_engine = self.past_engine

def force_request_engine(engine_name):
    tg.request._tg_force_sqla_engine = engine_name

########NEW FILE########
__FILENAME__ = utils
class TGConfigError(Exception):pass


def coerce_config(configuration, prefix, converters):
    """Convert configuration values to expected types."""

    options = dict((key[len(prefix):], configuration[key])
                    for key in configuration if key.startswith(prefix))

    for option, converter in converters.items():
        if option in options:
            options[option] = converter(options[option])

    return options

########NEW FILE########
__FILENAME__ = decoratedcontroller
# -*- coding: utf-8 -*-
"""
This module defines the class for decorating controller methods so that on
call the methods can be expressed using expose, validate, and other
decorators to effect a rendered page.
"""

import inspect, operator
import tg
from tg.controllers.util import abort
from tg.predicates import NotAuthorizedError, not_anonymous

from crank.util import (get_params_with_argspec,
                        remove_argspec_params_from_params)

from tg.flash import flash
from tg.jsonify import JsonEncodeError
from tg.render import render as tg_render
from tg.util import Bunch
from tg.validation import (_navigate_tw2form_children, _FormEncodeSchema,
                           _Tw2ValidationError, validation_errors,
                           _FormEncodeValidator, TGValidationError)

from tg._compat import unicode_text, with_metaclass, im_self, url2pathname, default_im_func
from tg.configuration.hooks import hooks
from functools import partial

strip_string = operator.methodcaller('strip')


class _DecoratedControllerMeta(type):
    def __init__(cls, name, bases, attrs):
        super(_DecoratedControllerMeta, cls).__init__(name, bases, attrs)
        for name, value in attrs.items():
            #Inherit decorations for methods exposed with inherit=True
            if hasattr(value, 'decoration') and value.decoration.inherit:
                for pcls in reversed(bases):
                    parent_method = getattr(pcls, name, None)
                    if parent_method and hasattr(parent_method, 'decoration'):
                        value.decoration.merge(parent_method.decoration)


class DecoratedController(with_metaclass(_DecoratedControllerMeta, object)):
    """Decorated controller object.

    Creates an interface to hang decoration attributes on
    controller methods for the purpose of rendering web content.

    """
    def _is_exposed(self, controller, name):
        method = getattr(controller, name, None)
        if method and inspect.ismethod(method) and hasattr(method, 'decoration'):
            return method.decoration.exposed

    def _call(self, controller, params, remainder=None, context=None):
        """Run the controller with the given parameters.

        _call is called by _perform_call in CoreDispatcher.

        Any of the before_validate hook, the validation, the before_call hook,
        and the controller method can return a FormEncode Invalid exception,
        which will give the validation error handler the opportunity to provide
        a replacement decorated controller method and output that will
        subsequently be rendered.

        This allows for validation to display the original page or an
        abbreviated form with validation errors shown on validation failure.

        The before_render hook provides a place for functions that are called
        before the template is rendered. For example, you could use it to
        add and remove from the dictionary returned by the controller method,
        before it is passed to rendering.

        The after_render hook can act upon and modify the response out of
        rendering.

        """
        if context is None: #pragma: no cover
            #compatibility with old code that didn't pass request locals explicitly
            context = tg.request.environ['tg.locals']

        context_config = tg.config._current_obj()
        self._initialize_validation_context(context)

        #This is necessary to prevent spurious Content Type header which would
        #cause problems to paste.response.replace_header calls and cause
        #responses wihout content type to get out with a wrong content type
        resp_headers = context.response.headers
        if not resp_headers.get('Content-Type'):
            resp_headers.pop('Content-Type', None)

        if remainder:
            remainder = tuple(map(url2pathname, remainder or []))
        else:
            remainder = tuple()

        hooks.notify('before_validate', args=(remainder, params),
                     controller=controller, context_config=context_config)

        try:
            validate_params = get_params_with_argspec(controller, params, remainder)

            # Validate user input
            params = self._perform_validate(controller, validate_params)
            context.request.validation['values'] = params

            params, remainder = remove_argspec_params_from_params(controller, params, remainder)
            bound_controller_callable = controller
        except validation_errors as inv:
            instance, controller = self._process_validation_errors(controller,
                                                                   remainder, params,
                                                                   inv, context=context)
            bound_controller_callable = partial(controller, instance)

        hooks.notify('before_call', args=(remainder, params),
                     controller=controller, context_config=context_config)

        # call controller method with applied wrappers
        controller_caller = controller.decoration.controller_caller
        output = controller_caller(context_config, bound_controller_callable, remainder, params)

        # Render template
        hooks.notify('before_render', args=(remainder, params, output),
                     controller=controller, context_config=context_config)

        response = self._render_response(context, controller, output)

        hooks.notify('after_render', args=(response,),
                     controller=controller, context_config=context_config)

        return response['response']

    @classmethod
    def _perform_validate(cls, controller, params):
        """Run validation for the controller with the given parameters.

        Validation is stored on the "validation" attribute of the controller's
        decoration.

        If can be in three forms:

        1) A dictionary, with key being the request parameter name, and value a
           FormEncode validator.

        2) A FormEncode Schema object

        3) Any object with a "validate" method that takes a dictionary of the
           request variables.

        Validation can "clean" or otherwise modify the parameters that were
        passed in, not just raise an exception.  Validation exceptions should
        be FormEncode Invalid objects.

        """

        validation = getattr(controller.decoration, 'validation', None)

        if validation is None:
            return params

        # An object used by FormEncode to get translator function
        formencode_state = type('state', (), {'_': staticmethod(tg.i18n._formencode_gettext)})

        #Initialize new_params -- if it never gets updated just return params
        new_params = {}

        # The validator may be a dictionary, a FormEncode Schema object, or any
        # object with a "validate" method.
        if isinstance(validation.validators, dict):
            # TG developers can pass in a dict of param names and FormEncode
            # validators.  They are applied one by one and builds up a new set
            # of validated params.

            errors = {}
            for field, validator in validation.validators.items():
                try:
                    if isinstance(validator, _FormEncodeValidator):
                        new_params[field] = validator.to_python(params.get(field),
                                                                formencode_state)
                    else:
                        new_params[field] = validator.to_python(params.get(field))
                # catch individual validation errors into the errors dictionary
                except validation_errors as inv:
                    errors[field] = inv

            # Parameters that don't have validators are returned verbatim
            for param, param_value in params.items():
                if not param in new_params:
                    new_params[param] = param_value

            # If there are errors, create a compound validation error based on
            # the errors dictionary, and raise it as an exception
            if errors:
                raise TGValidationError(TGValidationError.make_compound_message(errors),
                                        value=params,
                                        error_dict=errors)

        elif isinstance(validation.validators, _FormEncodeSchema):
            # A FormEncode Schema object - to_python converts the incoming
            # parameters to sanitized Python values
            new_params = validation.validators.to_python(params, formencode_state)

        elif (hasattr(validation.validators, 'validate')
              and getattr(validation, 'needs_controller', False)):
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(
                controller, params, formencode_state)

        elif hasattr(validation.validators, 'validate'):
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(params, formencode_state)

        # Theoretically this should not happen...
        # if new_params is None:
        #     return params

        return new_params

    def _render_response(self, tgl, controller, response):
        """
        Render response takes the dictionary returned by the
        controller calls the appropriate template engine. It uses
        information off of the decoration object to decide which engine
        and template to use, and removes anything in the exclude_names
        list from the returned dictionary.

        The exclude_names functionality allows you to pass variables to
        some template rendering engines, but not others. This behavior
        is particularly useful for rendering engines like JSON or other
        "web service" style engines which don't use and explicit
        template, or use a totally generic template.

        All of these values are populated into the context object by the
        expose decorator.
        """

        req = tgl.request
        resp = tgl.response

        (content_type, engine_name, template_name, exclude_names, render_params
            ) = controller.decoration.lookup_template_engine(tgl)

        result = dict(response=response, content_type=content_type,
                      engine_name=engine_name, template_name=template_name)

        if content_type is not None:
            resp.headers['Content-Type'] = content_type

        # if it's a string return that string and skip all the stuff
        if not isinstance(response, dict):
            if engine_name == 'json' and isinstance(response, list):
                raise JsonEncodeError(
                    'You may not expose with JSON a list return value because'
                    ' it leaves your application open to CSRF attacks.')
            return result

        # Save these objects as locals from the SOP to avoid expensive lookups
        tmpl_context = tgl.tmpl_context

        # If there is an identity, push it to the Pylons template context
        tmpl_context.identity = req.environ.get('repoze.who.identity')

        # Setup the template namespace, removing anything that the user
        # has marked to be excluded.
        namespace = response
        for name in exclude_names:
            namespace.pop(name, None)

        # If we are in a test request put the namespace where it can be
        # accessed directly
        if 'paste.testing' in req.environ:
            testing_variables = req.environ['paste.testing_variables']
            testing_variables['namespace'] = namespace
            testing_variables['template_name'] = template_name
            testing_variables['exclude_names'] = exclude_names
            testing_variables['render_params'] = render_params
            testing_variables['controller_output'] = response

        # Render the result.
        rendered = tg_render(template_vars=namespace, template_engine=engine_name,
                             template_name=template_name, **render_params)

        result['response'] = rendered
        return result

    @classmethod
    def _process_validation_errors(cls, controller, remainder, params, exception, context):
        """Process validation errors.

        Sets up validation status and error tracking
        to assist generating a form with given values
        and the validation failure messages.

        The error handler in decoration.validation.error_handler resolved
        and returned to be called as a controller.
        If an error_handler isn't given, the original controller is returned instead.

        """
        req = context.request

        validation_status = req.validation
        validation_status['exception'] = exception

        if isinstance(exception, _Tw2ValidationError):
            #Fetch all the children and grandchildren of a widget
            widget = exception.widget
            widget_children = _navigate_tw2form_children(widget.child)

            errors = dict((child.compound_key, child.error_msg) for child in widget_children)
            validation_status['errors'] = errors
            validation_status['values'] = widget.child.value
        elif isinstance(exception, TGValidationError):
            validation_status['errors'] = exception.error_dict
            validation_status['values'] = exception.value
        else:
            # Most Invalid objects come back with a list of errors in the format:
            #"fieldname1: error\nfieldname2: error"
            error_list = exception.__str__().split('\n')
            for error in error_list:
                field_value = list(map(strip_string, error.split(':', 1)))

                #if the error has no field associated with it,
                #return the error as a global form error
                if len(field_value) == 1:
                    validation_status['errors']['_the_form'] = field_value[0]
                    continue

                validation_status['errors'][field_value[0]] = field_value[1]

            validation_status['values'] = getattr(exception, 'value', {})

        deco = controller.decoration

        error_handler = deco.validation.error_handler
        if error_handler is None:
            error_handler = default_im_func(controller)

        validation_status['error_handler'] = error_handler
        return im_self(controller), error_handler

    @classmethod
    def _handle_validation_errors(cls, controller, remainder, params, exception, tgl=None):
        """Handle validation errors.

        Processes validation errors and call the error_handler,
        this is not used by TurboGears itself and is mostly provided
        for backward compatibility.
        """
        if tgl is None: #pragma: no cover
            #compatibility with old code that didn't pass request locals explicitly
            tgl = tg.request.environ['tg.locals']

        obj, error_handler = cls._process_validation_errors(controller, remainder, params,
                                                            exception, tgl)
        return error_handler, error_handler(obj, *remainder, **dict(params))

    def _initialize_validation_context(self, context):
        context.request.validation = Bunch(errors={},
                                           values={},
                                           exception=None,
                                           error_handler=None)

    def _check_security(self):
        requirement = getattr(self, 'allow_only', None)
        if requirement is None:
            return True

        if hasattr(requirement, 'predicate'):
            # It is a full requirement, let it build the response
            requirement._check_authorization()
            return True

        # It is directly a predicate, build the response ourselves
        predicate = requirement
        try:
            predicate.check_authorization(tg.request.environ)
        except NotAuthorizedError as e:
            reason = unicode_text(e)
            if hasattr(self, '_failed_authorization'):
                # Should shortcircuit the rest, but if not we will still
                # deny authorization
                self._failed_authorization(reason)
            if not_anonymous().is_met(tg.request.environ):
                # The user is authenticated but not allowed.
                code = 403
                status = 'error'
            else:
                # The user has not been not authenticated.
                code = 401
                status = 'warning'
            tg.response.status = code
            flash(reason, status=status)
            abort(code, comment=reason)

__all__ = ['DecoratedController']

########NEW FILE########
__FILENAME__ = dispatcher
"""
This is the main dispatcher module.

Dispatch works as follows:
Start at the RootController, the root controller must
have a _dispatch function, which defines how we move
from object to object in the system.
Continue following the dispatch mechanism for a given
controller until you reach another controller with a
_dispatch method defined.  Use the new _dispatch
method until anther controller with _dispatch defined
or until the url has been traversed to entirety.

This module also contains the standard ObjectDispatch
class which provides the ordinary TurboGears mechanism.

"""
import tg, sys
from webob.exc import HTTPException
from tg._compat import unicode_text
from tg.i18n import setup_i18n
from tg.decorators import cached_property
from crank.dispatchstate import DispatchState
from tg.request_local import WebObResponse
import mimetypes as default_mimetypes
import weakref


def dispatched_controller():
    state = tg.request._controller_state
    for location, cont in reversed(state.controller_path):
        if cont.mount_point:
            return cont


class CoreDispatcher(object):
    """Extend this class to define your own mechanism for dispatch."""
    _use_lax_params = True
    _use_index_fallback = False

    def _get_dispatchable(self, thread_locals, url_path):
        """
        Returns a tuple (controller, remainder, params)

        :Parameters:
          url
            url as string
        """
        req = thread_locals.request
        conf = thread_locals.config
        
        enable_request_extensions = not conf.get('disable_request_extensions', False)
        dispatch_path_translator = conf.get('dispatch_path_translator', True)

        params = req.args_params
        state = DispatchState(weakref.proxy(req), self, params, url_path.split('/'),
                              conf.get('ignore_parameters', []),
                              strip_extension=enable_request_extensions,
                              path_translator=dispatch_path_translator)
        url_path = state.path  # Get back url_path as crank performs some cleaning

        if enable_request_extensions:
            try:
                mimetypes = conf['mimetypes']
            except KeyError:
                mimetypes = default_mimetypes

            ext = state.extension
            if ext is not None:
                ext = '.' + ext
                mime_type, encoding = mimetypes.guess_type('file'+ext)
                req._fast_setattr('_response_type', mime_type)
            req._fast_setattr('_response_ext', ext)

        state = state.controller._dispatch(state, url_path)

        #save the controller state for possible use within the controller methods
        req._fast_setattr('_controller_state', state)

        if conf.get('enable_routing_args', False):
            state.routing_args.update(params)
            if hasattr(state.dispatcher, '_setup_wsgiorg_routing_args'):
                state.dispatcher._setup_wsgiorg_routing_args(url_path, state.remainder,
                                                             state.routing_args)

        return state, params

    def _enter_controller(self, state, remainder):
        if hasattr(state.controller, '_visit'):
            state.controller._visit(*remainder, **state.params)

        return super(CoreDispatcher, self)._enter_controller(state, remainder)

    def _perform_call(self, context):
        """
        This function is called by __call__ to actually perform the controller
        execution.
        """
        py_request = context.request
        py_config = context.config

        if py_config.get('i18n_enabled', True):
            setup_i18n(context)

        state, params = self._get_dispatchable(context, py_request.quoted_path_info)
        func, controller, remainder = state.method, state.controller, state.remainder

        if hasattr(controller, '_before'):
            controller._before(*remainder, **params)

        self._setup_wsgi_script_name(state.path, remainder, params)

        r = self._call(func, params, remainder=remainder, context=context)

        if hasattr(controller, '_after'):
            controller._after(*remainder, **params)

        return r

    def routes_placeholder(self, url='/', start_response=None, **kwargs): #pragma: no cover
        """Routes placeholder.

        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.
        """
        pass

    def __call__(self, environ, context):
        py_response = context.response

        try:
            response = self._perform_call(context)
        except HTTPException as httpe:
            response = httpe

        if isinstance(response, bytes):
            py_response.body = response
        elif isinstance(response, unicode_text):
            if not py_response.charset:
                py_response.charset = 'utf-8'
            py_response.text = response
        elif isinstance(response, WebObResponse):
            py_response.content_length = response.content_length
            for name, value in py_response.headers.items():
                header_name = name.lower()
                if header_name == 'set-cookie':
                    response.headers.add(name, value)
                else:
                    response.headers.setdefault(name, value)
            py_response = context.response = response
        elif response is None:
            pass
        else:
            py_response.app_iter = response

        return py_response

    @cached_property
    def mount_point(self):
        if not self.mount_steps:
            return ''
        return '/' + '/'.join((x[0] for x in self.mount_steps[1:]))

    @cached_property
    def mount_steps(self):
        def find_url(root, item, parents):
            for i in dir(root):
                if i.startswith('_') or i in ('mount_steps', 'mount_point'):
                    continue

                controller = getattr(root, i)
                if controller is item:
                    return parents + [(i, item)]
                if hasattr(controller, '_dispatch'):
                    v = find_url(controller.__class__,
                        item, parents + [(i, controller)])
                    if v:
                        return v
            return []

        if 'tg.root_controller' in tg.config:
            root_controller = tg.config['tg.root_controller']
        else:
            root_controller = sys.modules[tg.config['application_root_module']].RootController
        return find_url(root_controller, self, [('/', root_controller)])

########NEW FILE########
__FILENAME__ = restcontroller
"""This module contains the RestController implementation.

Rest controller provides a RESTful dispatch mechanism, and
combines controller decoration for TG-Controller behavior.
"""

from crank.restdispatcher import RestDispatcher

from tg.controllers.dispatcher import CoreDispatcher
from tg.controllers.decoratedcontroller import DecoratedController

class RestController(DecoratedController, CoreDispatcher, RestDispatcher):
    """A Decorated Controller that dispatches in a RESTful Manner.

    This controller was designed to follow Representational State Transfer protocol, also known as REST.
    The goal of this controller method is to provide the developer a way to map
    RESTful URLS to controller methods directly, while still allowing Normal Object Dispatch to occur.

    Here is a brief rundown of the methods which are called on dispatch along with an example URL.

    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | Method          | Description                                                  | Example Method(s) / URL(s)                 |
    +=================+==============================================================+============================================+
    | get_one         | Display one record.                                          | GET /movies/1                              |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | get_all         | Display all records in a resource.                           | GET /movies/                               |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | get             | A combo of get_one and get_all.                              | GET /movies/                               |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | GET /movies/1                              |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | new             | Display a page to prompt the User for resource creation.     | GET /movies/new                            |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | edit            | Display a page to prompt the User for resource modification. |  GET /movies/1/edit                        |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | post            | Create a new record.                                         | POST /movies/                              |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | put             | Update an existing record.                                   | POST /movies/1?_method=PUT                 |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | PUT /movies/1                              |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | post_delete     | Delete an existing record.                                   | POST /movies/1?_method=DELETE              |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | DELETE /movies/1                           |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | get_delete      | Display a delete Confirmation page.                          | GET /movies/1/delete                       |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | delete          | A combination of post_delete and get_delete.                 | GET /movies/delete                         |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | DELETE /movies/1                           |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | DELETE /movies/                            |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | POST /movies/1/delete                      |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | POST /movies/delete                        |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+

    You may note the ?_method on some of the URLs.  This is basically a hack because exiting browsers
    do not support the PUT and DELETE methods.  Just note that if you decide to use a this resource with a web browser,
    you will likely have to add a _method as a hidden field in your forms for these items.  Also note that RestController differs
    from TGController in that it offers no index, _default, or _lookup.  It is intended primarily for  resource management.

    :References:

      `Controller <../main/Controllers.html>`_  A basic overview on how to write controller methods.

      `CrudRestController <../main/Extensions/Crud/index.html>`_  A way to integrate ToscaWdiget Functionality with RESTful Dispatch.

    """

__all__ = ['RestController']

########NEW FILE########
__FILENAME__ = tgcontroller
"""This module contains the main TurboGears controller implementation."""

from crank.objectdispatcher import ObjectDispatcher

from tg.controllers.dispatcher import CoreDispatcher
from tg.controllers.decoratedcontroller import DecoratedController


class TGController(DecoratedController, CoreDispatcher, ObjectDispatcher):
    """
    TGController is a specialized form of ObjectDispatchController that forms the
    basis of standard TurboGears controllers.  The "Root" controller of a standard
    tg project must be a TGController.

    This controller can be used as a baseclass for anything in the
    object dispatch tree, but it MUST be used in the Root controller
    and any controller which you intend to do object dispatch from
    using Routes.

    This controller has a few reserved method names which provide special functionality.

    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | Method          | Description                                                  | Example URL(s)                             |
    +=================+==============================================================+============================================+
    | index           | The root of the controller.                                  | /                                          |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | _default        | A method to call when all other methods have failed.         | /movies                                    |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | _lookup         | Allows the developer to return a                             | /location/23.35/2343.34/elevation          |
    |                 | Controller instance for further dispatch.                    |                                            |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+


    :References:

      `Controller <../main/Controllers.html>`_  A basic overview on how to write controller methods.

    """

__all__ = ['TGController']


########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
"""Helper functions for controller operation.

URL definition and browser redirection are defined here.

"""
import re
from webob.exc import status_map

import tg

from tg._compat import string_type, url_encode, unicode_text, bytes_
from tg.exceptions import HTTPFound


def _smart_str(s):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.

    This function was borrowed from Django.

    """
    if not isinstance(s, string_type):
        try:
            return bytes_(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([_smart_str(arg).decode('utf-8') for arg in s.args]).encode('utf-8', 'strict')
            return unicode_text(s).encode('utf-8', 'strict')
    elif isinstance(s, unicode_text):
        return s.encode('utf-8', 'strict')
    else:
        return s


def _generate_smart_str(params):
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                yield _smart_str(key), _smart_str(item)
        else:
            yield _smart_str(key), _smart_str(value)


def _urlencode(params):
    """
    A version of Python's urllib.urlencode() function that can operate on
    unicode strings. The parameters are first case to UTF-8 encoded strings and
    then encoded as per normal.
    """
    return url_encode([i for i in _generate_smart_str(params)])


def _build_url(environ, base_url='/', params=None):
    if base_url.startswith('/'):
        base_url = environ['SCRIPT_NAME'] + base_url

    if params:
        return '?'.join((base_url, _urlencode(params)))

    return base_url


def url(base_url='/', params=None, qualified=False):
    """Generate an absolute URL that's specific to this application.

    The URL function takes a string (base_url) and, appends the
    SCRIPT_NAME and adds parameters for all of the
    parameters passed into the params dict.

    """
    if not isinstance(base_url, string_type) and hasattr(base_url, '__iter__'):
        base_url = '/'.join(base_url)

    req = tg.request._current_obj()
    base_url = _build_url(req.environ, base_url, params)
    if qualified:
        base_url = req.host_url + base_url

    return base_url


class LazyUrl(object):
    """
    Wraps tg.url in an object that enforces evaluation of the url
    only when you try to display it as a string.
    """

    def __init__(self, base_url, params=None):
        self.base_url = base_url
        self.params = params
        self._decoded = None

    @property
    def _id(self):
        if self._decoded == None:
            self._decoded = url(self.base_url, params=self.params)
        return self._decoded

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return self._id

    def __html__(self):
        return str(self)

    def __str__(self):
        return str(self._id)

    def encode(self, *args, **kw):
        return self._id.encode(*args, **kw)

    def __add__(self, other):
        return self._id + other

    def __radd__(self, other):
        return other + self._id

    def startswith(self, *args, **kw):
        return self._id.startswith(*args, **kw)

    def format(self, other):
        return self._id.format(other)

    def __json__(self):
        return str(self)


def lurl(base_url=None, params=None):
    """
    Like tg.url but is lazily evaluated.

    This is useful when creating global variables as no
    request is in place.

    As without a request it wouldn't be possible
    to correctly calculate the url using the SCRIPT_NAME
    this demands the url resolution to when it is
    displayed for the first time.
    """
    return LazyUrl(base_url, params)


def redirect(base_url='/', params={}, redirect_with=HTTPFound, **kwargs):
    """Generate an HTTP redirect.

    The function raises an exception internally,
    which is handled by the framework. The URL may be either absolute (e.g.
    http://example.com or /myfile.html) or relative. Relative URLs are
    automatically converted to absolute URLs. Parameters may be specified,
    which are appended to the URL. This causes an external redirect via the
    browser; if the request is POST, the browser will issue GET for the
    second request.
    """

    if kwargs:
        params = params.copy()
        params.update(kwargs)

    new_url = url(base_url, params=params)
    raise redirect_with(location=new_url)


IF_NONE_MATCH = re.compile('(?:W/)?(?:"([^"]*)",?\s*)')
def etag_cache(key=None):
    """Use the HTTP Entity Tag cache for Browser side caching

    If a "If-None-Match" header is found, and equivilant to ``key``,
    then a ``304`` HTTP message will be returned with the ETag to tell
    the browser that it should use its current cache of the page.

    Otherwise, the ETag header will be added to the response headers.
    """
    if_none_matches = IF_NONE_MATCH.findall(tg.request.environ.get('HTTP_IF_NONE_MATCH', ''))
    response = tg.response._current_obj()
    response.headers['ETag'] = '"%s"' % key
    if str(key) in if_none_matches:
        response.headers.pop('Content-Type', None)
        response.headers.pop('Cache-Control', None)
        response.headers.pop('Pragma', None)
        raise status_map[304]()


def abort(status_code=None, detail="", headers=None, comment=None,
          passthrough=False):
    """Aborts the request immediately by returning an HTTP exception

    In the event that the status_code is a 300 series error, the detail
    attribute will be used as the Location header should one not be
    specified in the headers attribute.

    **passthrough**
        When ``True`` instead of displaying the custom error
        document for errors or the authentication page for
        failed authorizations the response will just pass
        through as is.

        Set to ``"json"`` to send out the response body in
        JSON format.

    """
    exc = status_map[status_code](detail=detail, headers=headers,
                                  comment=comment)

    if passthrough == 'json':
        exc.content_type = 'application/json'
        exc.charset = 'utf-8'
        exc.body = tg.json_encode(dict(status=status_code,
                                       detail=str(exc))).encode('utf-8')

    if passthrough:
        tg.request.environ['tg.status_code_redirect'] = False
        tg.request.environ['tg.skip_auth_challenge'] = False

    raise exc


def use_wsgi_app(wsgi_app):
    return tg.request.get_response(wsgi_app)


__all__ = ['url', 'lurl', 'redirect', 'etag_cache', 'abort']

########NEW FILE########
__FILENAME__ = wsgiappcontroller
# -*- coding: utf-8 -*-
"""This module contains the main WSGI controller implementation."""
import tg

from tg.decorators import expose

from tg.controllers.tgcontroller import TGController
from tg.controllers.util import redirect


class WSGIAppController(TGController):
    """
    A controller you can use to mount a WSGI app.
    """
    def __init__(self, app, allow_only=None):
        self.app = app
        self.allow_only = allow_only
        # Signal tg.configuration.maybe_make_body_seekable which is wrapping
        # The stack to make the body seekable so default() can rewind it.
        tg.config['make_body_seekable'] = True
        # Calling the parent's contructor, to enable controller-wide auth:
        super(WSGIAppController, self).__init__()

    @expose()
    def _default(self, *args, **kw):
        """The default controller method.

        This method is called whenever a request reaches this controller.
        It prepares the WSGI environment and delegates the request to the
        WSGI app.

        """
        # Push into SCRIPT_NAME the path components that have been consumed,
        request = tg.request._current_obj()
        new_req = request.copy()
        to_pop = len(new_req.path_info.strip('/').split('/')) - len(args)
        for i in range(to_pop):
            new_req.path_info_pop()

        if not new_req.path_info: #pragma: no cover
            # This should not happen
            redirect(request.path_info + '/')

        new_req.body_file.seek(0)
        return self.delegate(new_req)

    def delegate(self, request):
        """Delegate the request to the WSGI app.

        Override me if you need to update the environ, mangle response, etc...

        """
        return request.get_response(self.app)


__all__ = ['WSGIAppController']

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
"""
Decorators use by the TurboGears controllers.

Not all of these decorators are traditional wrappers. They are much simplified
from the TurboGears 1 decorators, because all they do is register attributes on
the functions they wrap, and then the DecoratedController provides the hooks
needed to support these decorators.

"""
import copy
import warnings
import time
from webob.exc import HTTPUnauthorized, HTTPMethodNotAllowed, HTTPMovedPermanently
from tg.support import NoDefault
from tg.support.paginate import Page
from tg.configuration import config
from tg.configuration.app_config import _DeprecatedControllerWrapper, call_controller
from tg.controllers.util import abort, redirect
from tg import tmpl_context, request, response
from tg.util import partial, Bunch
from tg.configuration.sqla.balanced_session import force_request_engine
from tg.flash import flash
from tg.caching import beaker_cache, cached_property, _cached_call
from tg.predicates import NotAuthorizedError
from tg._compat import default_im_func, unicode_text
from webob.acceptparse import Accept
from tg.configuration import milestones
import tg

import logging
log = logging.getLogger(__name__)


def _decorated_controller_caller(tg_config, controller, remainder, params):
    try:
        application_controller_caller = tg_config['controller_caller']
    except KeyError:
        application_controller_caller = call_controller

    return application_controller_caller(tg_config, controller, remainder, params)


class Decoration(object):
    """ Simple class to support 'simple registration' type decorators
    """
    def __init__(self, controller):
        self.controller = controller
        self.controller_caller = _decorated_controller_caller
        self._expositions = []
        self.engines = {}
        self.engines_keys = []
        self.default_engine = None
        self.custom_engines = {}
        self.render_custom_format = None
        self.validation = None
        self.inherit = False
        self.requirements = []
        self.hooks = dict(before_validate=[],
                          before_call=[],
                          before_render=[],
                          after_render=[])

    def __repr__(self): # pragma: no cover
        return '<Decoration %s for %r>' % (id(self), self.controller)

    @classmethod
    def get_decoration(cls, func):
        try:
            dec = func.decoration
        except:
            dec = func.decoration = cls(func)
        return dec

    def _register_exposition(self, exposition, inherit=False, before=False):
        """Register an exposition for later application"""

        # We need to store a reference to the exposition
        # so that we can merge them when inheritance is performed
        if before:
            self._expositions.insert(0, exposition)
        else:
            self._expositions.append(exposition)

        if inherit:
            # if at least one exposition is in inherit mode
            # all of them must inherit
            self.inherit = True

        milestones.renderers_ready.register(self._resolve_expositions)

    def _resolve_expositions(self):
        """Applies all the registered expositions"""
        while True:
            try:
                exposition = self._expositions.pop(0)
                exposition._apply()
            except IndexError:
                break

    @property
    def requirement(self):  # pragma: no cover
        warnings.warn("Decoration.requirement is deprecated, "
                      "please use 'requirements' instead", DeprecationWarning)
        return self.requirements[0]

    @property
    def exposed(self):
        return bool(self.engines) or bool(self.custom_engines)

    def merge(self, deco):
        # This merges already registered template engines
        self.engines = dict(tuple(deco.engines.items()) + tuple(self.engines.items()))
        self.engines_keys = sorted(self.engines, reverse=True)
        self.custom_engines = dict(tuple(deco.custom_engines.items()) + tuple(self.custom_engines.items()))

        # This merges yet to register template engines
        for exposition in reversed(deco._expositions):
            self._register_exposition(exposition._clone(self.controller), before=True)

        # inherit all the parent hooks
        # parent hooks before current hooks so that they get called before
        for hook_name, hooks in deco.hooks.items():
            self.hooks[hook_name] = hooks + self.hooks[hook_name]

        if not self.validation:
            self.validation = deco.validation

    def run_hooks(self, tgl, hook, *l, **kw):
        warnings.warn("Decoration.run_hooks is deprecated, "
                      "please use tg.hooks.notify instead", DeprecationWarning)
        tg.hooks.notify(hook, args=l, kwargs=kw,
                        controller=self.controller, context_config=tgl.config)

    def register_hook(self, hook_name, func): #pragma: no cover
        warnings.warn("Decoration.register_hook is deprecated, "
                      "please use tg.hooks.register instead", DeprecationWarning)
        tg.hooks.register(hook_name, func, controller=self.controller)

    def register_template_engine(self,
            content_type, engine, template, exclude_names, render_params):
        """Registers an engine on the controller.

        Multiple engines can be registered, but only one engine per
        content_type.  If no content type is specified the engine is
        registered at */* which is the default, and will be used
        whenever no content type is specified.

        exclude_names keeps track of a list of keys which will be
        removed from the controller's dictionary before it is loaded
        into the template.  This allows you to exclude some information
        from JSONification, and other 'automatic' engines which don't
        require a template.

        render_params registers extra parameters which will be sent
        to the rendering method.  This allows you to influence things
        like the rendering method or the injected doctype.

        """
        default_renderer = config.get('default_renderer')
        available_renderers = config.get('renderers', [])

        if engine and not available_renderers:
            log.warn('Renderers not registered yet while exposing template %s for engine %s, '
                     'skipping engine availability check', template, engine)

        if engine and available_renderers and engine not in available_renderers:
            log.debug('Registering template %s for engine %s not available. Skipping it', template, engine)
            return

        content_type = content_type or '*/*'
        if content_type in self.engines and engine != default_renderer:
            #Avoid overwriting the default renderer when there is already a template registered
            return

        self.engines[content_type] = (engine, template, exclude_names, render_params or {})

        #Avoid engine lookup if we have only one engine registered
        if len(self.engines) == 1:
            self.default_engine = content_type
        else:
            self.default_engine = None

        # this is a work-around to make text/html prominent in respect
        # to other common choices when they have the same weight for
        # paste.util.mimeparse.best_match.
        self.engines_keys = sorted(self.engines, reverse=True)

    def register_custom_template_engine(self, custom_format,
            content_type, engine, template, exclude_names, render_params):
        """Registers a custom engine on the controller.

        Multiple engines can be registered, but only one engine per
        custom_format.

        The engine is registered when @expose is used with the
        custom_format parameter and controllers render using this
        engine when the use_custom_format() function is called
        with the corresponding custom_format.

        exclude_names keeps track of a list of keys which will be
        removed from the controller's dictionary before it is loaded
        into the template.  This allows you to exclude some information
        from JSONification, and other 'automatic' engines which don't
        require a template.

        render_params registers extra parameters which will be sent
        to the rendering method.  This allows you to influence things
        like the rendering method or the injected doctype.

        """

        self.custom_engines[custom_format or '"*/*"'] = (
            content_type, engine, template, exclude_names, render_params or {})

    def lookup_template_engine(self, tgl):
        """Return the template engine data.

        Provides a convenience method to get the proper engine,
        content_type, template, and exclude_names for a particular
        tg_format (which is pulled off of the request headers).

        """
        request = tgl.request
        response = tgl.response

        try:
            render_custom_format = request._render_custom_format[self.controller]
        except:
            render_custom_format = self.render_custom_format

        if render_custom_format:
            (content_type, engine, template, exclude_names, render_params
                ) = self.custom_engines[render_custom_format]
        else:
            if self.default_engine:
                content_type = self.default_engine
            elif self.engines:
                if request._response_type and request._response_type in self.engines:
                    accept_types = request._response_type
                else:
                    accept_types = request.headers.get('accept', '*/*')
                content_type = Accept(accept_types).best_match(self.engines_keys, self.engines_keys[0])
            else:
                content_type = 'text/html'

            # check for overridden content type from the controller call
            try:
                controller_content_type = response.headers['Content-Type']
                # make sure we handle content_types like 'text/html; charset=utf-8'
                content_type = controller_content_type.split(';')[0]
            except KeyError:
                pass

            # check for overridden templates
            try:
                cnt_override_mapping = request._override_mapping[self.controller]
                engine, template, exclude_names, render_params = cnt_override_mapping[content_type.split(";")[0]]
            except (AttributeError, KeyError):
                (engine, template, exclude_names, render_params
                    ) = self.engines.get(content_type, (None,) * 4)

        if 'charset' not in content_type and (content_type.startswith('text')
                or  content_type in ('application/xhtml+xml',
                        'application/xml', 'application/json')):
            content_type += '; charset=utf-8'

        return content_type, engine, template, exclude_names, render_params

    def _register_hook(self, hook_name, func):
        """Registers the specified function as a hook.

        This is internal API which is used by tg.hooks, instead of
        calling this tg.hooks.register should be used.

        We now have four core hooks that can be applied by adding
        decorators: before_validate, before_call, before_render, and
        after_render. register_hook attaches the function to the hook
        which get's called at the appropriate time in the request life
        cycle.)
        """
        self.hooks.setdefault(hook_name, []).append(func)

    def _register_requirement(self, requirement):
        self._register_hook('before_call', requirement._check_authorization)
        self.requirements.append(requirement)

    def _register_controller_wrapper(self, wrapper):
        try:
            self.controller_caller = wrapper(self.controller_caller)
        except TypeError:
            self.controller_caller = _DeprecatedControllerWrapper(wrapper, tg.config,
                                                                  self.controller_caller)


class _hook_decorator(object):
    """Superclass for all the specific TG2 hook validators.

    Its `hook_name` must be overridden by a specific hook.

    """

    hook_name = None

    def __init__(self, hook_func):
        if hasattr(hook_func, '__name__'):
            self.__name__ = hook_func.__name__
        if hasattr(hook_func, '__doc__'):
            self.__doc__ = hook_func.__doc__
        self.hook_func = hook_func

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco._register_hook(self.hook_name, self.hook_func)
        return func


class before_validate(_hook_decorator):
    """A list of callables to be run before validation is performed."""

    hook_name = 'before_validate'


class before_call(_hook_decorator):
    """A list of callables to be run before the controller method is called."""

    hook_name = 'before_call'


class before_render(_hook_decorator):
    """A list of callables to be run before the template is rendered."""

    hook_name = 'before_render'


class after_render(_hook_decorator):
    """A list of callables to be run after the template is rendered.

    Will be run before it is returned returned up the WSGI stack.

    """

    hook_name = 'after_render'


class expose(object):
    """Register attributes on the decorated function.

    :Parameters:
      template
        Assign a template, you could use the syntax 'genshi:template'
        to use different templates.
        The default template engine is genshi.
      content_type
        Assign content type.
        The default content type is 'text/html'.
      exclude_names
        Assign exclude names
      custom_format
        Registers as a custom format which can later be activated calling
        use_custom_format
      render_params
        Assign parameters that shall be passed to the rendering method.
      inherit
        Inherit all the decorations from the same method in the parent
        class. This will let the exposed method expose the same template
        as the overridden method template and keep the same hooks and
        validation that the parent method had.

    The expose decorator registers a number of attributes on the
    decorated function, but does not actually wrap the function the way
    TurboGears 1.0 style expose decorators did.

    This means that we don't have to play any kind of special tricks to
    maintain the signature of the exposed function.

    The exclude_names parameter is new, and it takes a list of keys that
    ought to be scrubbed from the dictionary before passing it on to the
    rendering engine.  This is particularly useful for JSON.

    The render_parameters is also new.  It takes a dictionary of arguments
    that ought to be sent to the rendering engine, like this::

        render_params={'method': 'xml', 'doctype': None}

    Expose decorator can be stacked like this::

        @expose('json', exclude_names='d')
        @expose('kid:blogtutorial.templates.test_form',
                content_type='text/html')
        @expose('kid:blogtutorial.templates.test_form_xml',
                content_type='text/xml', custom_format='special_xml')
        def my_exposed_method(self):
            return dict(a=1, b=2, d="username")

    The expose('json') syntax is a special case.  json is a
    rendering engine, but unlike others it does not require a template,
    and expose assumes that it matches content_type='application/json'

    If you want to declare a desired content_type in a url, you
    can use the mime-type style dotted notation::

        "/mypage.json" ==> for json
        "/mypage.html" ==> for text/html
        "/mypage.xml" ==> for xml.

    If you're doing an http post, you can also declare the desired
    content type in the accept headers, with standard content type
    strings.

    By default expose assumes that the template is for html.  All other
    content_types must be explicitly matched to a template and engine.

    The last expose decorator example uses the custom_format parameter
    which takes an arbitrary value (in this case 'special_xml').
    You can then use the`use_custom_format` function within the method
    to decide which of the 'custom_format' registered expose decorators
    to use to render the template.

    """

    def __init__(self, template='', content_type=None, exclude_names=None,
                 custom_format=None, render_params=None, inherit=False):

        self.engine = None
        self.template = template
        self.content_type = content_type
        self.exclude_names = exclude_names
        self.custom_format = custom_format
        self.render_params = render_params

        self.inherit = inherit
        self._func = None

    def __call__(self, func):
        self._func = func
        deco = Decoration.get_decoration(func)
        deco._register_exposition(self, self.inherit)
        return func

    def _resolve_options(self):
        """This resolves exposition options that depend on
        configuration steps that might not have already happened.
        It's automatically called by _apply when required

        """
        if self.engine is not None:
            return

        exclude_names = self.exclude_names
        template = self.template
        content_type = self.content_type

        if exclude_names is None:
            exclude_names = []

        if template in config.get('renderers', []):
            engine, template = template, ''
        elif ':' in template:
            engine, template = template.split(':', 1)
        elif template:
            # Use the default templating engine from the config
            engine = config.get('default_renderer')
        else:
            engine, template = None, None

        if content_type is None:
            all_engines_options = config.get('rendering_engines_options', {})
            engine_options = all_engines_options.get(engine, {})
            content_type = engine_options.get('content_type', 'text/html')

        engines_without_vars = config.get('rendering_engines_without_vars', [])
        if engine in engines_without_vars and 'tmpl_context' not in exclude_names:
            exclude_names.append('tmpl_context')

        self.engine = engine
        self.template = template
        self.content_type = content_type
        self.exclude_names = exclude_names

    def _clone(self, func):
        clone = copy.copy(self)
        clone._func = func
        return clone

    def _apply(self):
        """Applies an exposition for real"""
        if self._func is None:
            log.error('Applying an exposition with no decorated function!')
            return

        self._resolve_options()

        deco = Decoration.get_decoration(self._func)
        if deco.inherit and not self.template and not self.engine:
            # If we are just inheriting without adding additional
            # engines or templates we can just skip this part.
            return

        if self.custom_format:
            deco.register_custom_template_engine(
                self.custom_format, self.content_type, self.engine,
                self.template, self.exclude_names, self.render_params)
        else:
            deco.register_template_engine(
                self.content_type, self.engine,
                self.template, self.exclude_names, self.render_params)


def use_custom_format(controller, custom_format):
    """Use use_custom_format in a controller in order to change
    the active @expose decorator when available."""
    deco = Decoration.get_decoration(controller)

    # Check the custom_format passed is available for use
    if custom_format not in deco.custom_engines:
        raise ValueError("'%s' is not a valid custom_format" % custom_format)

    try:
        render_custom_format = request._render_custom_format
    except AttributeError:
        render_custom_format = request._render_custom_format = {}
    render_custom_format[default_im_func(controller)] = custom_format


def override_template(controller, template):
    """Override the template to be used.

    Use override_template in a controller in order to change the template
    that will be used to render the response dictionary dynamically.

    The template string passed in requires that
    you include the template engine name, even if you're using the default.

    So you have to pass in a template id string like::

       "genshi:myproject.templates.index2"

    future versions may make the `genshi:` optional if you want to use
    the default engine.

    """
    try:
        engines = controller.decoration.engines
    except:
        return

    for content_type, content_engine in engines.items():
        tmpl = template.split(':', 1)
        tmpl.extend(content_engine[2:])
        try:
            override_mapping = request._override_mapping
        except AttributeError:
            override_mapping = request._override_mapping = {}
        override_mapping.setdefault(default_im_func(controller), {}).update({content_type: tmpl})


class validate(object):
    """Registers which validators ought to be applied.

    If you want to validate the contents of your form,
    you can use the ``@validate()`` decorator to register
    the validators that ought to be called.

    :Parameters:
      validators
        Pass in a dictionary of FormEncode validators.
        The keys should match the form field names.
      error_handler
        Pass in the controller method which shoudl be used
        to handle any form errors
      form
        Pass in a ToscaWidget based form with validators

    The first positional parameter can either be a dictonary of validators,
    a FormEncode schema validator, or a callable which acts like a FormEncode
    validator.

    """
    def __init__(self, validators=None, error_handler=None, form=None):
        self.validators = None
        if form:
            self.validators = form
        if validators:
            self.validators = validators
        self.error_handler = error_handler

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco.validation = self
        return func


class paginate(object):
    """Paginate a given collection.

    This decorator is mainly exposing the functionality
    of :func:`webhelpers.paginate`.

    :Usage:

    You use this decorator as follows::

     class MyController(object):

         @expose()
         @paginate("collection")
         def sample(self, *args):
             collection = get_a_collection()
             return dict(collection=collection)

    To render the actual pager, use::

      ${tmpl_context.paginators.<name>.pager()}

    It is possible to have several :func:`paginate`-decorators for
    one controller action to paginate several collections independently
    from each other. If this is desired, don't forget to set the :attr:`use_prefix`-parameter
    to :const:`True`.

    :Parameters:
      name
        the collection to be paginated.
      items_per_page
        the number of items to be rendered. Defaults to 10
      max_items_per_page
        the maximum number of items allowed to be set via parameter.
        Defaults to 0 (does not allow to change that value).
      use_prefix
        if True, the parameters the paginate
        decorator renders and reacts to are prefixed with
        "<name>_". This allows for multi-pagination.

    """

    def __init__(self, name, use_prefix=False,
        items_per_page=10, max_items_per_page=0):
        self.name = name
        prefix = use_prefix and name + '_' or ''
        self.page_param = prefix + 'page'
        self.items_per_page_param = prefix + 'items_per_page'
        self.items_per_page = items_per_page
        self.max_items_per_page = max_items_per_page

    def __call__(self, func):
        decoration = Decoration.get_decoration(func)
        decoration._register_hook('before_validate', self.before_validate)
        decoration._register_hook('before_render', self.before_render)
        return func

    def before_validate(self, remainder, params):
        page_param = params.pop(self.page_param, None)
        if page_param:
            try:
                page = int(page_param)
                if page < 1:
                    raise ValueError
            except ValueError:
                page = 1
        else:
            page = 1

        try:
            paginators_data = request.paginators
        except:
            paginators_data = request.paginators = {'_tg_paginators_params':{}}

        paginators_data['_tg_paginators_params'][self.page_param] = page_param
        paginators_data[self.name] = paginator = Bunch()

        paginator.paginate_page = page or 1
        items_per_page = params.pop(self.items_per_page_param, None)
        if items_per_page:
            try:
                items_per_page = min(
                    int(items_per_page), self.max_items_per_page)
                if items_per_page < 1:
                    raise ValueError
            except ValueError:
                items_per_page = self.items_per_page
        else:
            items_per_page = self.items_per_page
        paginator.paginate_items_per_page = items_per_page
        paginator.paginate_params = params.copy()
        paginator.paginate_params.update(paginators_data['_tg_paginators_params'])
        if items_per_page != self.items_per_page:
            paginator.paginate_params[self.items_per_page_param] = items_per_page

    def before_render(self, remainder, params, output):
        if not isinstance(output, dict) or not self.name in output:
            return

        paginator = request.paginators[self.name]
        collection = output[self.name]
        page = Page(collection, paginator.paginate_page, paginator.paginate_items_per_page)
        page.kwargs = paginator.paginate_params
        if self.page_param != 'name':
            page.pager = partial(page.pager, page_param=self.page_param)
        if not getattr(tmpl_context, 'paginators', None):
            tmpl_context.paginators = Bunch()
        tmpl_context.paginators[self.name] = output[self.name] = page

@before_validate
def https(remainder, params):
    """Ensure that the decorated method is always called with https."""
    if request.scheme.lower() == 'https': return
    if request.method.upper() == 'GET':
        redirect('https' + request.url[len(request.scheme):])
    raise HTTPMethodNotAllowed(headers=dict(Allow='GET'))


_variabledecode = None
@before_validate
def variable_decode(remainder, params):
    """Best-effort formencode.variabledecode on the params before validation.

    If any exceptions are raised due to invalid parameter names, they are
    silently ignored, hopefully to be caught by the actual validator.
    Note that this decorator will *add* parameters to the method, not remove.
    So for instance a method will move from {'foo-1':'1', 'foo-2':'2'}
    to {'foo-1':'1', 'foo-2':'2', 'foo':['1', '2']}.

    """
    global _variabledecode
    if _variabledecode is None:
        from formencode import variabledecode as _variabledecode

    try:
        new_params = _variabledecode.variable_decode(params)
        params.update(new_params)
    except:
        pass


@before_validate
def without_trailing_slash(remainder, params):
    """This decorator allows you to ensure that the URL does not end in "/".

    The decorator accomplish this by redirecting to the correct URL.

    :Usage:

    You use this decorator as follows::

     class MyController(object):

         @without_trailing_slash
         @expose()
         def sample(self, *args):
             return "found sample"

    In the above example http://localhost:8080/sample/ redirects to http://localhost:8080/sample
    In addition, the URL http://localhost:8080/sample/1/ redirects to http://localhost:8080/sample/1

    """
    req = request._current_obj()
    if req.method == 'GET' and req.path.endswith('/') and not(req._response_type) and len(req.params)==0:
        redirect(request.url[:-1], redirect_with=HTTPMovedPermanently)


@before_validate
def with_trailing_slash(remainder, params):
    """This decorator allows you to ensure that the URL ends in "/".

    The decorator accomplish this by redirecting to the correct URL.

    :Usage:

    You use this decorator as follows::

     class MyController(object):

         @with_trailing_slash
         @expose()
         def sample(self, *args):
             return "found sample"

    In the above example http://localhost:8080/sample redirects to http://localhost:8080/sample/
    In addition, the URL http://localhost:8080/sample/1 redirects to http://localhost:8080/sample/1/

    """
    req = request._current_obj()
    if (req.method == 'GET' and not(req.path.endswith('/')) and not(req._response_type) and len(req.params)==0):
        redirect(request.url+'/', redirect_with=HTTPMovedPermanently)


class require(object):
    """
    Decorator that checks if the specified predicate it met, if it isn't
    it calls the denial_handler to prevent access to the decorated method.

    The default authorization denial handler of this protector will flash
    the message of the unmet predicate with ``warning`` or ``error`` as the
    flash status if the HTTP status code is 401 or 403, respectively.

    :param predicate: An object with a check_authorization(environ) method which
        must raise a tg.predicates.NotAuthorizedError if not met.
    :param denial_handler: The callable to be run if authorization is
        denied (overrides :attr:`default_denial_handler` if defined).
    :param smart_denial: A list of response types for which to trigger
        the smart denial, which will act as an API providing a pass-through
        :func:`tg.controllers.util.abort`.
        If ``True``, ``('application/json', 'text/xml')`` will be used.

    If called, ``denial_handler`` will be passed a positional argument
    which represents a message on why authorization was denied.

    Use ``allow_only`` property of ``TGController`` for controller-wide authorization.

    """
    def __init__(self, predicate, denial_handler=None, smart_denial=False):
        self.predicate = predicate
        self.denial_handler = denial_handler or self.default_denial_handler

        if smart_denial is True:
            smart_denial = ('application/json', 'text/xml')
        self.smart_denial = smart_denial

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco._register_requirement(self)
        return func

    def _check_authorization(self, *args, **kwargs):
        req = request._current_obj()

        try:
            self.predicate.check_authorization(req.environ)
        except NotAuthorizedError as e:
            reason = unicode_text(e)
            if req.environ.get('repoze.who.identity'):
                # The user is authenticated.
                code = 403
            else:
                # The user is not authenticated.
                code = 401
            response.status = code
            return self.denial_handler(reason)

    def default_denial_handler(self, reason):
        """Authorization denial handler for protectors."""
        passthrough_abort = False

        if self.smart_denial:
            response_type = response.content_type or request.response_type
            if response_type in self.smart_denial:
                # It's an API response, use a pass-through abort
                passthrough_abort = True
                if response_type == 'application/json':
                    passthrough_abort = 'json'

        if passthrough_abort is False:
            # Plain HTML page
            status = 'warning' if response.status_int == 401 else 'error'
            flash(reason, status=status)

        abort(response.status_int, reason, passthrough=passthrough_abort)


class with_engine(object):
    """
    Decorator to force usage of a specific database engine
    in TurboGears SQLAlchemy BalancedSession.
    
    :param engine_name: 'master' or the name of one of the slaves, if is ``None``
             it will not force any specific engine.
    :param master_params: A dictionary or GET parameters that when present will force
             usage of the master node. The keys of the dictionary will be the
             name of the parameters to look for, while the values must be whenever
             to pop the paramter from the parameters passed to the controller (True/False).
             If `master_params` is a list then it is converted to a dictionary where
             the keys are the entries of the list and the value is always True.
    """

    def __init__(self, engine_name=None, master_params={}):
        self.engine_name = engine_name

        if not hasattr(master_params, 'keys'):
            self.master_params = dict((p, True) for p in master_params)
        else:
            self.master_params = master_params

    def before_validate(self, remainder, params):
        force_request_engine(self.engine_name)
        for p, pop in self.master_params.items():
            if p in params:
                if pop:
                    v = params.pop(p, None)
                else:
                    v = params.get(p)

                if v:
                    force_request_engine('master')
                    break

    def __call__(self, func):
        decoration = Decoration.get_decoration(func)
        decoration._register_hook('before_validate', self.before_validate)
        return func


class cached(object):
    """
    Decorator to cache the controller, if you also want to cache
    template remember to return ``tg_cache`` option from the controller.

    The following parameters are accepted:

    ``key`` - Specifies the controller parameters used to generate the cache key.
        NoDefault - Uses function name and all request parameters as the key (default)
        
        None - No variable key, uses only function name as key
        
        string - Use function name and only "key" parameter
        
        list - Use function name and all parameters listed
    ``expire``
        Time in seconds before cache expires, or the string "never".
        Defaults to "never"
    ``type``
        Type of cache to use: dbm, memory, file, memcached, or None for
        Beaker's default
    ``cache_headers``
        A tuple of header names indicating response headers that
        will also be cached.
    ``invalidate_on_startup``
        If True, the cache will be invalidated each time the application
        starts or is restarted.
    ``cache_response``
        Determines whether the response at the time the cache is used
        should be cached or not, defaults to True.

        .. note::
            When cache_response is set to False, the cache_headers
            argument is ignored as none of the response is cached.
    """
    def __init__(self, key=NoDefault, expire="never", type=None,
                 query_args=None,  # Backward compatibility, actually ignored
                 cache_headers=('content-type', 'content-length'),
                 invalidate_on_startup=False, cache_response=True,
                 **b_kwargs):
        self.key = key
        self.expire = expire
        self.type = type
        self.cache_headers = cache_headers
        self.invalidate_on_startup = invalidate_on_startup
        self.cache_response = cache_response
        self.beaker_options = b_kwargs

    def __call__(self, func):
        decoration = Decoration.get_decoration(func)

        def controller_wrapper(__, next_caller):
            if self.invalidate_on_startup:
                starttime = time.time()
            else:
                starttime = None

            def cached_call_controller(controller, remainder, params):
                if self.key:
                    key_dict = tg.request.args_params
                    if self.key != NoDefault:
                        if isinstance(self.key, (list, tuple)):
                            key_dict = dict((k, key_dict[k]) for k in key_dict)
                        else:
                            key_dict = {self.key: key_dict[self.key]}
                else:
                    key_dict = {}

                return _cached_call(next_caller, (controller, remainder, params), {},
                                    key_func=func, key_dict=key_dict,
                                    expire=self.expire, type=self.type,
                                    starttime=starttime, cache_headers=self.cache_headers,
                                    cache_response=self.cache_response,
                                    cache_extra_args=self.beaker_options)

            return cached_call_controller

        decoration._register_controller_wrapper(controller_wrapper)
        return func

########NEW FILE########
__FILENAME__ = error
import logging
from tg.support.converters import asbool

log = logging.getLogger(__name__)


def _turbogears_backlash_context(environ):
    tgl = environ.get('tg.locals')
    return {'request':getattr(tgl, 'request', None)}


def ErrorHandler(app, global_conf, **errorware):
    """ErrorHandler Toggle
    
    If debug is enabled, this function will return the app wrapped in
    the WebError ``EvalException`` middleware which displays
    interactive debugging sessions when a traceback occurs.
    
    Otherwise, the app will be wrapped in the WebError
    ``ErrorMiddleware``, and the ``errorware`` dict will be passed into
    it. The ``ErrorMiddleware`` handles sending an email to the address
    listed in the .ini file, under ``email_to``.
    
    """
    try:
        import backlash
    except ImportError: #pragma: no cover
        log.warning('backlash not installed, debug mode won\'t be available')
        return app

    if asbool(global_conf.get('debug')):
        app = backlash.DebuggedApplication(app, context_injectors=[_turbogears_backlash_context])

    return app


def ErrorReporter(app, global_conf, **errorware):
    try:
        import backlash
    except ImportError: #pragma: no cover
        log.warning('backlash not installed, email tracebacks won\'t be available')
        return app


    reporters = []
    if errorware.get('error_email'):
        from backlash.trace_errors import EmailReporter
        reporters.append(EmailReporter(**errorware))

    if errorware.get('sentry_dsn'):
        from backlash.trace_errors.sentry import SentryReporter
        reporters.append(SentryReporter(**errorware))

    if not asbool(global_conf.get('debug')):
        app = backlash.TraceErrorsMiddleware(app, reporters,
                                             context_injectors=[_turbogears_backlash_context])

    return app


def SlowReqsReporter(app, global_conf, **errorware):
    try:
        import backlash
    except ImportError: #pragma: no cover
        log.warning('backlash not installed, slow requests reporting won\'t be available')
        return app

    reporters = []
    if errorware.get('error_email'):
        from backlash.tracing.reporters.mail import EmailReporter
        reporters.append(EmailReporter(**errorware))

    if errorware.get('sentry_dsn'):
        from backlash.tracing.reporters.sentry import SentryReporter
        reporters.append(SentryReporter(**errorware))

    if not asbool(global_conf.get('debug')):
        app = backlash.TraceSlowRequestsMiddleware(app, reporters, interval=errorware.get('interval', 25),
                                                   exclude_paths=errorware.get('exclude', None),
                                                   context_injectors=[_turbogears_backlash_context])

    return app



########NEW FILE########
__FILENAME__ = exceptions
"""http exceptions for TurboGears

TurboGears http exceptions are inherited from WebOb http exceptions
"""
import webob
from webob.exc import *


class _HTTPMoveLazyLocation(object):
    """
    
    """
    def __init__(self, *args, **kw):
        try:
            kw['location'] = str(kw['location'])
        except KeyError:
            pass
        super(_HTTPMoveLazyLocation, self).__init__(*args, **kw)


class HTTPMovedPermanently(_HTTPMoveLazyLocation, webob.exc.HTTPMovedPermanently):
    """
    subclass of :class:`webob.exc.HTTPMovedPermanently` with
    support for lazy strings as location.

    This indicates that the requested resource has been assigned a new
    permanent URI and any future references to this resource SHOULD use
    one of the returned URIs.

    code: 301, title: Moved Permanently
    """


class HTTPFound(_HTTPMoveLazyLocation, webob.exc.HTTPFound):
    """
    subclass of :class:`webob.exc.HTTPFound` with
    support for lazy strings as location.

    This indicates that the requested resource resides temporarily under
    a different URI.

    code: 302, title: Found
    """


class HTTPTemporaryRedirect(_HTTPMoveLazyLocation, webob.exc.HTTPTemporaryRedirect):
    """
    subclass of :class:`webob.exc.HTTPTemporaryRedirect` with
    support for lazy strings as location.

    This indicates that if the client has performed a conditional GET
    request and access is allowed, but the document has not been
    modified, the server SHOULD respond with this status code.

    code: 304, title: Not Modified
    """

########NEW FILE########
__FILENAME__ = flash
"""
Flash messaging system for sending info to the user in a non-obtrusive way
"""

import json
from tg import response, request
from logging import getLogger

log = getLogger(__name__)

from tg._compat import unicode_text, url_quote, url_unquote

from markupsafe import escape_silent as escape


class TGFlash(object):
    """
    Flash Message Creator
    """
    template = '<div id="%(container_id)s">'\
               '<script type="text/javascript">'\
               '//<![CDATA[\n'\
               '%(js_code)s'\
               '%(js_call)s'\
               '\n//]]>'\
               '</script>'\
               '</div>'

    static_template = '<div id="%(container_id)s">'\
                      '<div class="%(status)s">%(message)s</div>'\
                      '</div>'

    js_code = '''if(!window.webflash){webflash=(function(){var j=document;var k=j.cookie;var f=null;var e=false;\
var g=null;var c=/msie|MSIE/.test(navigator.userAgent);var a=function(m){return j.createTextNode(m.message)};\
var l=function(n,m){};var b=function(o,m){var n=m;if(typeof(o)=="string"){n=window[o]}\
else{if(o){n=o}}return n};var h=function(){var p=k.indexOf(f+"=");if(p<0){return null}\
var o=p+f.length+1;var m=k.indexOf(";",o);if(m==-1){m=k.length}var n=k.substring(o,m);\
j.cookie=f+"=; expires=Fri, 02-Jan-1970 00:00:00 GMT; path=/";return webflash.lj(unescape(n))};\
var i=function(){if(e){return}e=true;var p=h();if(p!==null){var m=j.getElementById(g);\
var n=j.createElement("div");if(p.status){n.setAttribute(c?"className":"class",p.status)}\
var o=a(p);n.appendChild(o);m.style.display="block";if(p.delay){setTimeout(function(){m.style.display="none"},p.delay)}\
m.appendChild(n);l(p,m)}};var d=function(){if(!c){var m="DOMContentLoaded";\
j.addEventListener(m,function(){j.removeEventListener(m,arguments.callee,false);i()},false);\
window.addEventListener("load",i,false)}else{if(c){var m="onreadystatechange";\
j.attachEvent(m,function(){j.detachEvent(m,arguments.callee);i()});\
if(j.documentElement.doScroll&&!frameElement){(function(){if(e){return}try{j.documentElement.doScroll("left")}\
catch(n){setTimeout(arguments.callee,0);return}i()})()}window.attachEvent("load",i)}}};\
return function(m){f=m.name||"webflash";g=m.id||"webflash";l=b(m.on_display,l);a=b(m.create_node,a);\
return{payload:h,render:d}}})();webflash.lj=function(s){var r;eval("r="+s);return r}};'''

    def __init__(self, cookie_name="webflash", default_status="ok"):
        self.default_status = default_status
        self.cookie_name = cookie_name

    def __call__(self, message, status=None, **extra_payload):
        # Force the message to be unicode so lazystrings, etc... are coerced
        message = unicode_text(message)

        payload = self.prepare_payload(message = message,
                                       status = status or self.default_status,
                                       **extra_payload)

        if request is not None:
            # Save the payload in environ too in case JavaScript is not being
            # used and the message is being displayed in the same request.
            request.environ['webflash.payload'] = payload

        resp = response._current_obj()
        resp.set_cookie(self.cookie_name, payload)
        if len(resp.headers['Set-Cookie']) > 4096:
            raise ValueError('Flash value is too long (cookie would be >4k)')

    def prepare_payload(self, **data):
        return url_quote(json.dumps(data))

    def js_call(self, container_id):
        return 'webflash(%(options)s).render();' % {'options': json.dumps({'id': container_id,
                                                                           'name': self.cookie_name})}

    def render(self, container_id, use_js=True):
        if use_js:
            return self._render_js_version(container_id)
        else:
            return self._render_static_version(container_id)

    def _render_static_version(self, container_id):
        payload = self.pop_payload()
        if not payload:
            return ''
        payload['message'] = escape(payload.get('message',''))
        payload['container_id'] = container_id
        return self.static_template % payload

    def _render_js_version(self, container_id):
        return self.template % {'container_id': container_id,
                                'js_code': self.js_code,
                                'js_call': self.js_call(container_id)}

    def pop_payload(self):
        # First try fetching it from the request
        req = request._current_obj()
        payload = req.environ.get('webflash.payload', {})
        if not payload:
            payload = req.cookies.get(self.cookie_name, {})

        if payload:
            payload = json.loads(url_unquote(payload))
            if 'webflash.deleted_cookie' not in req.environ:
                response.delete_cookie(self.cookie_name)
                req.environ['webflash.delete_cookie'] = True
        return payload or {}

    @property
    def message(self):
        return self.pop_payload().get('message')

    @property
    def status(self):
        return self.pop_payload().get('status') or self.default_status


flash = TGFlash()

#TODO: Deprecate these?

def get_flash():
    """Get the message previously set by calling flash().

    Additionally removes the old flash message.

    """
    return flash.message


def get_status():
    """Get the status of the last flash message.

    Additionally removes the old flash message status.

    """
    return flash.status

########NEW FILE########
__FILENAME__ = i18n
import copy
import logging, os
import gettext as _gettext
from gettext import NullTranslations, GNUTranslations
import tg
from tg.util import lazify
from tg._compat import PY3, string_type

log = logging.getLogger(__name__)


class LanguageError(Exception):
    """Exception raised when a problem occurs with changing languages"""
    pass


def _parse_locale(identifier, sep='_'):
    """
    Took from Babel,
    Parse a locale identifier into a tuple of the form::

      ``(language, territory, script, variant)``

    >>> parse_locale('zh_CN')
    ('zh', 'CN', None, None)
    >>> parse_locale('zh_Hans_CN')
    ('zh', 'CN', 'Hans', None)

    The default component separator is "_", but a different separator can be
    specified using the `sep` parameter:

    :see: `IETF RFC 4646 <http://www.ietf.org/rfc/rfc4646.txt>`_
    """
    if '.' in identifier:
        # this is probably the charset/encoding, which we don't care about
        identifier = identifier.split('.', 1)[0]
    if '@' in identifier:
        # this is a locale modifier such as @euro, which we don't care about
        # either
        identifier = identifier.split('@', 1)[0]

    parts = identifier.split(sep)
    lang = parts.pop(0).lower()
    if not lang.isalpha():
        raise ValueError('expected only letters, got %r' % lang)

    script = territory = variant = None
    if parts:
        if len(parts[0]) == 4 and parts[0].isalpha():
            script = parts.pop(0).title()

    if parts:
        if len(parts[0]) == 2 and parts[0].isalpha():
            territory = parts.pop(0).upper()
        elif len(parts[0]) == 3 and parts[0].isdigit():
            territory = parts.pop(0)

    if parts:
        if len(parts[0]) == 4 and parts[0][0].isdigit() or\
           len(parts[0]) >= 5 and parts[0][0].isalpha():
            variant = parts.pop()

    if parts:
        raise ValueError('%r is not a valid locale identifier' % identifier)

    return lang, territory, script, variant


def gettext_noop(value):
    """Mark a string for translation without translating it. Returns
    value.
    """
    return value


def ugettext(value):
    """Mark a string for translation. Returns the localized unicode
    string of value.

    Mark a string to be localized as follows::

        _('This should be in lots of languages')

    """
    if PY3: #pragma: no cover
        return tg.translator.gettext(value)
    else:
        return tg.translator.ugettext(value)
lazy_ugettext = lazify(ugettext)


def ungettext(singular, plural, n):
    """Mark a string for translation. Returns the localized unicode
    string of the pluralized value.

    This does a plural-forms lookup of a message id. ``singular`` is
    used as the message id for purposes of lookup in the catalog, while
    ``n`` is used to determine which plural form to use. The returned
    message is a Unicode string.

    Mark a string to be localized as follows::

        ungettext('There is %(num)d file here', 'There are %(num)d files here',
                  n) % {'num': n}

    """
    if PY3: #pragma: no cover
        return tg.translator.ngettext(singular, plural, n)
    else:
        return tg.translator.ungettext(singular, plural, n)
lazy_ungettext = lazify(ungettext)


_TRANSLATORS_CACHE = {}
def _translator_from_mofiles(domain, mofiles, class_=None, fallback=False):
    """
    Adapted from python translation function in gettext module
    to work with a provided list of mo files
    """
    if class_ is None:
        class_ = GNUTranslations

    if not mofiles:
        if fallback:
            return NullTranslations()
        raise LanguageError('No translation file found for domain %s' % domain)

    result = None
    for mofile in mofiles:
        key = (class_, os.path.abspath(mofile))
        t = _TRANSLATORS_CACHE.get(key)
        if t is None:
            with open(mofile, 'rb') as fp:
                # Cache Translator to avoid reading it again
                t = _TRANSLATORS_CACHE.setdefault(key, class_(fp))

        t = copy.copy(t)
        if result is None:
            # Copy the translation object to be able to append fallbacks
            # without affecting the cached object.
            result = t
        else:
            result.add_fallback(t)

    return result


def _get_translator(lang, tgl=None, tg_config=None, **kwargs):
    """Utility method to get a valid translator object from a language name"""
    if tg_config:
        conf = tg_config
    else:
        if tgl:
            conf = tgl.config
        else:  # pragma: no cover
            #backward compatibility with explicit calls without
            #specifying local context or config.
            conf = tg.config.current_conf()

    if not lang:
        return NullTranslations()

    try:
        localedir = conf['localedir']
    except KeyError:  # pragma: no cover
        localedir = os.path.join(conf['paths']['root'], 'i18n')
    app_domain = conf['package'].__name__

    if not isinstance(lang, list):
        lang = [lang]

    mofiles = []
    supported_languages = []
    for l in lang:
        mo = _gettext.find(app_domain, localedir=localedir, languages=[l], all=False)
        if mo is not None:
            mofiles.append(mo)
            supported_languages.append(l)

    try:
        translator = _translator_from_mofiles(app_domain, mofiles, **kwargs)
    except IOError as ioe:
        raise LanguageError('IOError: %s' % ioe)

    translator.tg_lang = lang
    translator.tg_supported_lang = supported_languages

    return translator


def get_lang(all=True):
    """
    Return the current i18n languages used

    returns ``None`` if no supported language is available (no translations
    are in place) or a list of languages.

    In case ``all`` parameter is ``False`` only the languages for which
    the application is providing a translation are returned. Otherwise
    all the languages preferred by the user are returned.
    """
    if all is False:
        return getattr(tg.translator, 'tg_supported_lang', [])
    return getattr(tg.translator, 'tg_lang', [])


def add_fallback(lang, **kwargs):
    """Add a fallback language from which words not matched in other
    languages will be translated to.

    This fallback will be associated with the currently selected
    language -- that is, resetting the language via set_lang() resets
    the current fallbacks.

    This function can be called multiple times to add multiple
    fallbacks.
    """
    tgl = tg.request_local.context._current_obj()
    return tg.translator.add_fallback(_get_translator(lang, tgl=tgl, **kwargs))


sanitized_language_cache = {}
def sanitize_language_code(lang):
    """Sanitize the language code if the spelling is slightly wrong.

    For instance, 'pt-br' and 'pt_br' should be interpreted as 'pt_BR'.

    """
    try:
        lang = sanitized_language_cache[lang]
    except:
        orig_lang = lang

        try:
            lang = '_'.join(filter(None, _parse_locale(lang)[:2]))
        except ValueError:
            if '-' in lang:
                try:
                    lang = '_'.join(filter(None, _parse_locale(lang, sep='-')[:2]))
                except ValueError:
                    pass

        sanitized_language_cache[orig_lang] = lang

    return lang


def setup_i18n(tgl=None):
    """Set languages from the request header and the session.

    The session language(s) take priority over the request languages.

    Automatically called by tg controllers to setup i18n.
    Should only be manually called if you override controllers function.

    """
    if not tgl: #pragma: no cover
        tgl = tg.request_local.context._current_obj()

    session_ = tgl.session
    if session_:
        session_existed = session_.accessed()
        # If session is available, we try to see if there are languages set
        languages = session_.get(tgl.config.get('lang_session_key', 'tg_lang'))
        if not session_existed and tgl.config.get('beaker.session.tg_avoid_touch'):
            session_.__dict__['_sess'] = None

        if languages:
            if isinstance(languages, string_type):
                languages = [languages]
        else:
            languages = []
    else: #pragma: no cover
        languages = []

    languages.extend(map(sanitize_language_code, tgl.request.plain_languages))
    set_temporary_lang(languages, tgl=tgl)


def set_temporary_lang(languages, tgl=None):
    """Set the current language(s) used for translations without touching
    the session language.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    # the logging to the screen was removed because
    # the printing to the screen for every problem causes serious slow down.
    if not tgl:
        tgl = tg.request_local.context._current_obj()

    # Should only raise exceptions in case of IO errors,
    # so we let them propagate to the developer.
    tgl.translator = _get_translator(languages, tgl=tgl, fallback=True)

    # If the application has a set of supported translation
    # limit the formencode translations to those so that
    # we don't get the application in a language and
    # the errors in another one
    supported_languages = get_lang(all=False)
    if supported_languages:
        languages = supported_languages

    try:
        set_formencode_translation(languages, tgl=tgl)
    except LanguageError:
        pass


def set_lang(languages, **kwargs):
    """Set the current language(s) used for translations
    in current call and session.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    tgl = tg.request_local.context._current_obj()

    set_temporary_lang(languages, tgl)

    if tgl.session:
        tgl.session[tgl.config.get('lang_session_key', 'tg_lang')] = languages
        tgl.session.save()

FormEncodeMissing = '_MISSING_FORMENCODE'
formencode = None
_localdir = None

def set_formencode_translation(languages, tgl=None):
    """Set request specific translation of FormEncode."""
    global formencode, _localdir
    if formencode is FormEncodeMissing:  # pragma: no cover
        return

    if formencode is None:
        try:
            import formencode
            _localdir = formencode.api.get_localedir()
        except ImportError:  # pragma: no cover
            formencode = FormEncodeMissing
            return

    if not tgl:  # pragma: no cover
        tgl = tg.request_local.context._current_obj()

    try:
        formencode_translation = _gettext.translation('FormEncode',
                                                      languages=languages,
                                                      localedir=_localdir)
    except IOError as error:
        raise LanguageError('IOError: %s' % error)
    tgl.translator._formencode_translation = formencode_translation


# Idea stolen from Pylons
def _formencode_gettext(value):
    trans = ugettext(value)
    # Translation failed, try formencode
    if trans == value:
        try:
            fetrans = tg.translator._formencode_translation
        except (AttributeError, TypeError):
            # the translator was not set in the TG context
            # we are certainly in the test framework
            # let's make sure won't return something that is ok with the caller
            fetrans = None

        if not fetrans:
            fetrans = NullTranslations()

        translator_gettext = getattr(fetrans, 'ugettext', fetrans.gettext)
        trans = translator_gettext(value)

    return trans


__all__ = [
    "setup_i18n", "set_lang", "get_lang", "add_fallback", "set_temporary_lang",
    "ugettext", "lazy_ugettext", "ungettext", "lazy_ungettext"
]


########NEW FILE########
__FILENAME__ = jsonify
"""JSON encoding functions."""

import datetime
import decimal
import types

from json import JSONEncoder

from webob.multidict import MultiDict
from tg._compat import string_type

class NotExistingImport:
    pass

try:
    import sqlalchemy
    from sqlalchemy.engine import ResultProxy, RowProxy
except ImportError: #pragma: no cover
    ResultProxy=NotExistingImport
    RowProxy=NotExistingImport

try:
    from bson import ObjectId
except ImportError: #pragma: no cover
    ObjectId=NotExistingImport

try:
    import ming
    import ming.odm
except ImportError: #pragma: no cover
    ming=NotExistingImport

def is_saobject(obj):
    return hasattr(obj, '_sa_class_manager')

def is_mingobject(obj):
    return hasattr(obj, '__ming__')


class JsonEncodeError(Exception):
    """JSON Encode error"""


class GenericJSON(JSONEncoder):
    """JSON Encoder class"""

    def default(self, obj):
        if hasattr(obj, '__json__') and callable(obj.__json__):
            return obj.__json__()
        elif isinstance(obj, (datetime.date, datetime.datetime)):
            return str(obj)
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif is_saobject(obj):
            props = {}
            for key in obj.__dict__:
                if not key.startswith('_sa_'):
                    props[key] = getattr(obj, key)
            return props
        elif is_mingobject(obj) and ming is not NotExistingImport:
            prop_names = [prop.name for prop in ming.odm.mapper(obj).properties
                          if isinstance(prop, ming.odm.property.FieldProperty)]

            props = {}
            for key in prop_names:
                props[key] = getattr(obj, key)
            return props
        elif isinstance(obj, ResultProxy):
            return dict(rows=list(obj), count=obj.rowcount)
        elif isinstance(obj, RowProxy):
            return dict(rows=dict(obj), count=1)
        elif isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, MultiDict):
            return obj.mixed()
        elif isinstance(obj, types.GeneratorType):
            return list(obj)
        else:
            return JSONEncoder.default(self, obj)

try: #pragma: no cover
    from simplegeneric import generic

    _default = GenericJSON()

    @generic
    def jsonify(obj):
        return _default.default(obj)

    class GenericFunctionJSON(GenericJSON):
        """Generic Function JSON Encoder class."""

        def default(self, obj):
            return jsonify(obj)

    _instance = GenericFunctionJSON()
except ImportError:

    def jsonify(obj): #pragma: no cover
        raise ImportError('simplegeneric is not installed')

    _instance = GenericJSON()


# General encoding functions

def encode(obj):
    """Return a JSON string representation of a Python object."""
    if isinstance(obj, string_type):
        return _instance.encode(obj)

    try:
        value = obj['test']
    except TypeError:
        if not hasattr(obj, '__json__') and not is_saobject(obj):
            raise JsonEncodeError('Your Encoded object must be dict-like.')
    except:
        pass

    return _instance.encode(obj)


def encode_iter(obj):
    """Encode object, yielding each string representation as available."""
    return _instance.iterencode(obj)

########NEW FILE########
__FILENAME__ = predicates
# -*- coding: utf-8 -*-
"""
Built-in predicate checkers.

This is mostly took from repoze.what.precidates

This is module provides the predicate checkers that were present in the
original "identity" framework of TurboGears 1, plus others.

"""

from __future__ import unicode_literals
from tg import request
from tg._compat import unicode_text

__all__ = ['Predicate', 'CompoundPredicate', 'All', 'Any',
           'has_all_permissions', 'has_any_permission', 'has_permission',
           'in_all_groups', 'in_any_group', 'in_group', 'is_user',
           'is_anonymous', 'not_anonymous', 'NotAuthorizedError']

try: #pragma: no cover
    # If repoze.what is available use repoze.what Predicate and
    # NotAuthorizedError adding booleanization support to the
    # predicates
    from repoze.what.predicates import NotAuthorizedError, Predicate
    Predicate.__nonzero__ = lambda self: self.is_met(request.environ)
except ImportError:
    class NotAuthorizedError(Exception):
        pass

    class Predicate(object):
        def __init__(self, msg=None):
            if msg:
                self.message = msg

        def evaluate(self, environ, credentials):
            raise NotImplementedError

        def unmet(self, msg=None, **placeholders):
            """
            Raise an exception because this predicate is not met.

            :param msg: The error message to be used; overrides the predicate's
                default one.
            :type msg: str
            :raises NotAuthorizedError: If the predicate is not met.

            ``placeholders`` represent the placeholders for the predicate message.
            The predicate's attributes will also be taken into account while
            creating the message with its placeholders.
            """
            if msg:
                message = msg
            else:
                message = self.message

            # This enforces lazy strings resolution (lazy translation for example)
            message = unicode_text(message)

            # Include the predicate attributes in the placeholders:
            all_placeholders = self.__dict__.copy()
            all_placeholders.update(placeholders)

            raise NotAuthorizedError(message % all_placeholders)

        def check_authorization(self, environ):
            """
            Evaluate the predicate and raise an exception if it's not met.

            :param environ: The WSGI environment.
            :raise NotAuthorizedError: If it the predicate is not met.
            """
            credentials = environ.get('repoze.what.credentials', {})
            try:
                self.evaluate(environ, credentials)
            except NotAuthorizedError:
                raise

        def is_met(self, environ):
            """
            Find whether the predicate is met or not.

            :param environ: The WSGI environment.
            :return: Whether the predicate is met or not.
            :rtype: bool
            """
            credentials = environ.get('repoze.what.credentials', {})
            try:
                self.evaluate(environ, credentials)
                return True
            except NotAuthorizedError:
                return False

        def __nonzero__(self):
            return self.is_met(request.environ)
        __bool__ = __nonzero__

class CompoundPredicate(Predicate):
    """A predicate composed of other predicates."""

    def __init__(self, *predicates, **kwargs):
        super(CompoundPredicate, self).__init__(**kwargs)
        self.predicates = predicates


class Not(Predicate):
    """
    Negate the specified predicate.

    :param predicate: The predicate to be negated.

    Example::

        # The user *must* be anonymous:
        p = Not(not_anonymous())

    """
    message = "The condition must not be met"

    def __init__(self, predicate, **kwargs):
        super(Not, self).__init__(**kwargs)
        self.predicate = predicate

    def evaluate(self, environ, credentials):
        try:
            self.predicate.evaluate(environ, credentials)
        except NotAuthorizedError:
            return
        self.unmet()


class All(CompoundPredicate):
    """
    Check that all of the specified predicates are met.

    :param predicates: All of the predicates that must be met.

    Example::

        # Grant access if the current month is July and the user belongs to
        # the human resources group.
        p = All(is_month(7), in_group('hr'))

    """

    def evaluate(self, environ, credentials):
        """
        Evaluate all the predicates it contains.

        :param environ: The WSGI environment.
        :param credentials: The :mod:`repoze.what` ``credentials``.
        :raises NotAuthorizedError: If one of the predicates is not met.

        """
        for p in self.predicates:
            p.evaluate(environ, credentials)


class Any(CompoundPredicate):
    """
    Check that at least one of the specified predicates is met.

    :param predicates: Any of the predicates that must be met.

    Example::

        # Grant access if the currest user is Richard Stallman or Linus
        # Torvalds.
        p = Any(is_user('rms'), is_user('linus'))

    """
    message = "At least one of the following predicates must be met: %(failed_predicates)s"

    def evaluate(self, environ, credentials):
        """
        Evaluate all the predicates it contains.

        :param environ: The WSGI environment.
        :param credentials: The :mod:`repoze.what` ``credentials``.
        :raises NotAuthorizedError: If none of the predicates is met.

        """
        errors = []
        for p in self.predicates:
            try:
                p.evaluate(environ, credentials)
                return
            except NotAuthorizedError as exc:
                errors.append(unicode_text(exc))
        failed_predicates = ', '.join(errors)
        self.unmet(failed_predicates=failed_predicates)


class is_user(Predicate):
    """
    Check that the authenticated user's username is the specified one.

    :param user_name: The required user name.
    :type user_name: str

    Example::

        p = is_user('linus')

    """

    message = 'The current user must be "%(user_name)s"'

    def __init__(self, user_name, **kwargs):
        super(is_user, self).__init__(**kwargs)
        self.user_name = user_name

    def evaluate(self, environ, credentials):
        if credentials and\
           self.user_name == credentials.get('repoze.what.userid'):
            return
        self.unmet()


class in_group(Predicate):
    """
    Check that the user belongs to the specified group.

    :param group_name: The name of the group to which the user must belong.
    :type group_name: str

    Example::

        p = in_group('customers')

    """

    message = 'The current user must belong to the group "%(group_name)s"'

    def __init__(self, group_name, **kwargs):
        super(in_group, self).__init__(**kwargs)
        self.group_name = group_name

    def evaluate(self, environ, credentials):
        if credentials and self.group_name in credentials.get('groups'):
            return
        self.unmet()


class in_all_groups(All):
    """
    Check that the user belongs to all of the specified groups.

    :param groups: The name of all the groups the user must belong to.

    Example::

        p = in_all_groups('developers', 'designers')

    """


    def __init__(self, *groups, **kwargs):
        group_predicates = [in_group(g) for g in groups]
        super(in_all_groups,self).__init__(*group_predicates, **kwargs)


class in_any_group(Any):
    """
    Check that the user belongs to at least one of the specified groups.

    :param groups: The name of any of the groups the user may belong to.

    Example::

        p = in_any_group('directors', 'hr')

    """

    message = "The member must belong to at least one of the following groups: %(group_list)s"

    def __init__(self, *groups, **kwargs):
        self.group_list = ", ".join(groups)
        group_predicates = [in_group(g) for g in groups]
        super(in_any_group,self).__init__(*group_predicates, **kwargs)


class is_anonymous(Predicate):
    """
    Check that the current user is anonymous.

    Example::

        # The user must be anonymous!
        p = is_anonymous()

    .. versionadded:: 1.0.7

    """

    message = "The current user must be anonymous"

    def evaluate(self, environ, credentials):
        if credentials:
            self.unmet()


class not_anonymous(Predicate):
    """
    Check that the current user has been authenticated.

    Example::

        # The user must have been authenticated!
        p = not_anonymous()

    """

    message = "The current user must have been authenticated"

    def evaluate(self, environ, credentials):
        if not credentials:
            self.unmet()


class has_permission(Predicate):
    """
    Check that the current user has the specified permission.

    :param permission_name: The name of the permission that must be granted to
        the user.

    Example::

        p = has_permission('hire')

    """
    message = 'The user must have the "%(permission_name)s" permission'

    def __init__(self, permission_name, **kwargs):
        super(has_permission, self).__init__(**kwargs)
        self.permission_name = permission_name

    def evaluate(self, environ, credentials):
        if credentials and\
           self.permission_name in credentials.get('permissions'):
            return
        self.unmet()


class has_all_permissions(All):
    """
    Check that the current user has been granted all of the specified
    permissions.

    :param permissions: The names of all the permissions that must be
        granted to the user.

    Example::

        p = has_all_permissions('view-users', 'edit-users')

    """

    def __init__(self, *permissions, **kwargs):
        permission_predicates = [has_permission(p) for p in permissions]
        super(has_all_permissions, self).__init__(*permission_predicates,
            **kwargs)


class has_any_permission(Any):
    """
    Check that the user has at least one of the specified permissions.

    :param permissions: The names of any of the permissions that have to be
        granted to the user.

    Example::

        p = has_any_permission('manage-users', 'edit-users')

    """

    message = "The user must have at least one of the following permissions: %(permission_list)s"

    def __init__(self, *permissions, **kwargs):
        self.permission_list = ", ".join(permissions)
        permission_predicates = [has_permission(p) for p in permissions]
        super(has_any_permission,self).__init__(*permission_predicates,
            **kwargs)
########NEW FILE########
__FILENAME__ = release
"""TurboGears project related information"""
version = "2.3.2"
description = "Next generation TurboGears"
long_description="""
TurboGears brings together a best of breed python tools
to create a flexible, full featured, and easy to use web
framework.

TurboGears 2 provides an integrated and well tested set of tools for
everything you need to build dynamic, database driven applications.
It provides a full range of tools for front end javascript
develeopment, back database development and everything in between:

 * dynamic javascript powered widgets (ToscaWidgets2)
 * automatic JSON generation from your controllers
 * powerful, designer friendly XHTML based templating (Genshi)
 * object or route based URL dispatching
 * powerful Object Relational Mappers (SQLAlchemy)

The latest development version is available in the
`TurboGears Git repositories`_.

.. _TurboGears Git repositories:
    https://github.com/TurboGears
"""
url="http://www.turbogears.org/"
author= "Mark Ramm, Christopher Perkins, Jonathan LaCour, Rick Copland, Alberto Valverde, Michael Pedersen, Alessandro Molina, and the TurboGears community"
email = "mark.ramm@gmail.com, alberto@toscat.net, m.pedersen@icelus.org, amol@turbogears.org"
copyright = """Copyright 2005-2014 Kevin Dangoor,
Alberto Valverde, Mark Ramm, Christopher Perkins and contributors"""
license = "MIT"

########NEW FILE########
__FILENAME__ = render
try:
    from urllib import quote_plus
except ImportError: #pragma: no cover
    from urllib.parse import quote_plus

from tg.support.converters import asbool
from markupsafe import Markup

import tg
from tg import predicates
from tg.util import Bunch


class MissingRendererError(Exception):
    def __init__(self, template_engine):
        Exception.__init__(self,
            ("The renderer for '%(template_engine)s' templates is missing. "
            "Try adding the following line in you app_cfg.py:\n"
            "\"base_config.renderers.append('%(template_engine)s')\"") % dict(
            template_engine=template_engine))
        self.template_engine = template_engine


def _get_tg_vars():
    """Create a Bunch of variables that should be available in all templates.

    These variables are:

    WARNING: This function should not be called from outside of the render()
    code.  Please consider this function as private.

    quote_plus
        the urllib quote_plus function
    url
        the turbogears.url function for creating flexible URLs
    identity
        the current visitor's identity information
    session
        the current beaker.session if the session_filter.on it set
        in the app.cfg configuration file. If it is not set then session
        will be None.
    locale
        the default locale
    inputs
        input values from a form
    errors
        validation errors
    request
        the WebOb Request Object
    config
        the app's config object
    auth_stack_enabled
        A boolean that determines if the auth stack is present in the environment
    predicates
        The :mod:`tg.predicates` module.

    """

    tgl = tg.request_local.context._current_obj()
    req = tgl.request
    conf = tgl.config
    tmpl_context = tgl.tmpl_context
    app_globals = tgl.app_globals
    translator = tgl.translator
    response = tgl.response
    session = tgl.session

    try:
        h = conf['package'].lib.helpers
    except (AttributeError, ImportError):
        h = Bunch()

    # TODO: Implement user_agent and other missing features.
    tg_vars = Bunch(
        config=tg.config,
        flash_obj=tg.flash,
        quote_plus=quote_plus,
        url=tg.url,
        # this will be None if no identity
        identity = req.environ.get('repoze.who.identity'),
        session = session,
        locale = req.plain_languages,
        errors = req.validation['errors'],
        inputs = req.validation['values'],
        request = req,
        auth_stack_enabled = 'repoze.who.plugins' in req.environ,
        predicates = predicates)

    root_vars = Bunch(
        c=tmpl_context,
        tmpl_context=tmpl_context,
        response=response,
        request=req,
        config=conf,
        app_globals=app_globals,
        g=app_globals,
        session=session,
        url=tg.url,
        helpers=h,
        h=h,
        tg=tg_vars,
        translator=translator,
        ungettext=tg.i18n.ungettext,
        _=tg.i18n.ugettext,
        N_=tg.i18n.gettext_noop)

    # Allow users to provide a callable that defines extra vars to be
    # added to the template namespace
    variable_provider = conf.get('variable_provider', None)
    if variable_provider:
        root_vars.update(variable_provider())
    return root_vars

#Monkey patch pylons_globals for cases when pylons.templating is used
#instead of tg.render to programmatically render templates.
try: #pragma: no cover
    import pylons
    import pylons.templating
    pylons.templating.pylons_globals = _get_tg_vars
except ImportError:
    pass
# end monkeying around


def render(template_vars, template_engine=None, template_name=None, **kwargs):
    config = tg.config._current_obj()

    render_function = None
    if template_engine is not None:
        # the engine was defined in the @expose()
        render_function = config['render_functions'].get(template_engine)

        if render_function is None:
            # engine was forced in @expose() but is not present in the
            # engine list, warn developer
            raise MissingRendererError(template_engine)

    if not render_function:
        # getting the default renderer, if no engine was defined in @expose()
        template_engine = config['default_renderer']
        render_function = config['render_functions'][template_engine]

    if not template_vars:
        template_vars = {}

    caching_options = template_vars.get('tg_cache', {})
    kwargs['cache_key'] = caching_options.get('key')
    kwargs['cache_expire'] = caching_options.get('expire')
    kwargs['cache_type'] = caching_options.get('type')

    for func in config.get('hooks', {}).get('before_render_call', []):
        func(template_engine, template_name, template_vars, kwargs)

    tg_vars = template_vars

    engines_without_vars = config['rendering_engines_without_vars']
    if template_engine not in engines_without_vars:
        # Get the extra vars, and merge in the vars from the controller
        tg_vars = _get_tg_vars()
        tg_vars.update(template_vars)

    kwargs['result'] = render_function(template_name, tg_vars, **kwargs)

    for func in config.get('hooks', {}).get('after_render_call', []):
        func(template_engine, template_name, template_vars, kwargs)

    return kwargs['result']


def cached_template(template_name, render_func, ns_options=(),
                    cache_key=None, cache_type=None, cache_expire=None,
                    **kwargs):
    """Cache and render a template, took from Pylons

    Cache a template to the namespace ``template_name``, along with a
    specific key if provided.

    Basic Options

    ``template_name``
        Name of the template, which is used as the template namespace.
    ``render_func``
        Function used to generate the template should it no longer be
        valid or doesn't exist in the cache.
    ``ns_options``
        Tuple of strings, that should correspond to keys likely to be
        in the ``kwargs`` that should be used to construct the
        namespace used for the cache. For example, if the template
        language supports the 'fragment' option, the namespace should
        include it so that the cached copy for a template is not the
        same as the fragment version of it.

    Caching options (uses Beaker caching middleware)

    ``cache_key``
        Key to cache this copy of the template under.
    ``cache_type``
        Valid options are ``dbm``, ``file``, ``memory``, ``database``,
        or ``memcached``.
    ``cache_expire``
        Time in seconds to cache this template with this ``cache_key``
        for. Or use 'never' to designate that the cache should never
        expire.

    The minimum key required to trigger caching is
    ``cache_expire='never'`` which will cache the template forever
    seconds with no key.

    """
    # If one of them is not None then the user did set something
    if cache_key is not None or cache_type is not None or cache_expire is not None:
        get_cache_kw = {}
        if cache_type is not None:
            get_cache_kw['type'] = cache_type

        if not cache_key:
            cache_key = 'default'
        if cache_expire == 'never':
            cache_expire = None

        namespace = template_name
        for name in ns_options:
            namespace += str(kwargs.get(name))

        cache = tg.cache.get_cache(namespace, **get_cache_kw)
        content = cache.get_value(cache_key, createfunc=render_func,
            expiretime=cache_expire)
        return content
    else:
        return render_func()


########NEW FILE########
__FILENAME__ = base

class RendererFactory(object):
    """
    Factory that creates one or multiple rendering engines
    for TurboGears. Subclasses have to be registered with
    :func:`tg.configuration.AppConfig.register_rendering_engine`
    and must implement the ``create`` method accordingly.

    """

    #: Here specify the list of engines for which this factory
    #: will create a rendering engine and their options.
    #: They must be specified like::
    #:
    #:   engines = {'json': {'content_type': 'application/json'}}
    #:
    #: Currently only supported option is ``content_type``.
    options = {}

    #: Here specify if turbogears variables have to be injected
    #: in the template context before using any of the declared engines.
    #: Usually ``True`` unless engines are protocols (ie JSON).
    with_tg_vars = True

    @classmethod
    def create(cls, config, app_globals):  # pragma: no cover
        """
        Given the TurboGears configuration and application globals
        it must create a rendering engine for each one specified
        into the ``engines`` list.

        It must return a dictionary in the form::

            {'engine_name': rendering_engine_callable,
             'other_engine': other_rendering_callable}

        Rendering engine callables are callables in the form::

            func(template_name, template_vars,
                 cache_key=None, cache_type=None, cache_expire=None,
                 **render_params)

        ``render_params`` parameter will contain all the values
        provide through ``@expose(render_params={})``.

        """
        raise NotImplementedError()
########NEW FILE########
__FILENAME__ = genshi
from __future__ import absolute_import

from markupsafe import Markup
from tg.support.converters import asint, asbool
from tg.i18n import ugettext
from tg.render import cached_template
from .base import RendererFactory
import tg

try:
    import genshi
except ImportError:  # pragma: no cover
    genshi = None

if genshi is not None:
    from genshi.template import TemplateLoader as GenshiTemplateLoader
    from genshi.filters import Translator
    from genshi import HTML, XML
else:  # pragma: no cover
    class GenshiTemplateLoader(object): pass


__all__ = ['GenshiRenderer']


class GenshiRenderer(RendererFactory):
    """Singleton that can be called as the Genshi render function."""
    engines = {'genshi': {'content_type': 'text/html'}}

    doctypes_for_methods = {
        'html': 'html-transitional',
        'xhtml': 'xhtml-transitional'}

    doctypes_for_content_type = {
        'text/html': ('html', 'html-transitional',
            'html-frameset', 'html5',
            'xhtml', 'xhtml-strict',
            'xhtml-transitional', 'xhtml-frameset'),
        'application/xhtml+xml': ('xhtml', 'xhtml-strict',
            'xhtml-transitional',
            'xhtml-frameset', 'xhtml11'),
        'image/svg+xml': ('svg', 'svg-full', 'svg-basic', 'svg-tiny')}

    methods_for_content_type = {
        'text/plain': ('text',),
        'text/css': ('text',),
        'text/html': ('html', 'xhtml'),
        'text/xml': ('xml', 'xhtml'),
        'application/xml': ('xml', 'xhtml'),
        'application/xhtml+xml': ('xhtml',),
        'application/atom+xml': ('xml',),
        'application/rss+xml': ('xml',),
        'application/soap+xml': ('xml',),
        'image/svg+xml': ('xml',)}

    @classmethod
    def create(cls, config, app_globals):
        """Setup a renderer and loader for Genshi templates.

        Override this to customize the way that the internationalization
        filter, template loader

        """
        if genshi is None:  # pragma: no cover
            # Genshi not available
            return None

        if config.get('use_dotted_templatenames', True):
            TemplateLoader = DottedTemplateLoader
            template_loader_args = {'dotted_finder': app_globals.dotted_filename_finder}
        else:
            TemplateLoader = GenshiTemplateLoader
            template_loader_args = {}

        loader = TemplateLoader(search_path=config.paths.templates,
                                max_cache_size=asint(config.get('genshi.max_cache_size', 30)),
                                auto_reload=config.auto_reload_templates,
                                callback=cls.on_template_loaded,
                                **template_loader_args)

        return {'genshi': cls(loader, config)}

    def __init__(self, loader, config):
        self.tg_config = config
        self.genshi_functions = dict(HTML=HTML, XML=XML)
        self.load_template = loader.load

        self.default_doctype = None
        doctype = self.tg_config.get('templating.genshi.doctype')
        if doctype:
            if isinstance(doctype, str):
                self.default_doctype = doctype
            elif isinstance(doctype, dict):
                doctypes = self.doctypes_for_content_type.copy()
                doctypes.update(doctype)
                self.doctypes_for_content_type = doctypes

        self.default_method = None
        method = self.tg_config.get('templating.genshi.method')
        if method:
            if isinstance(method, str):
                self.default_method = method
            elif isinstance(method, dict):
                methods = self.methods_for_content_type.copy()
                methods.update(method)
                self.methods_for_content_type = methods

    @classmethod
    def on_template_loaded(cls, template):
        """
        Plug-in our i18n function to Genshi, once the template is loaded.

        This function will be called by the Genshi TemplateLoader after
        loading the template.

        """
        translator = Translator(ugettext)
        template.filters.insert(0, translator)

        if hasattr(template, 'add_directives'):
            template.add_directives(Translator.NAMESPACE, translator)

    @staticmethod
    def method_for_doctype(doctype):
        method = 'xhtml'
        if doctype:
            if doctype.startswith('html'):
                method = 'html'
            elif doctype.startswith('xhtml'):
                method = 'xhtml'
            elif doctype.startswith('svg'):
                method = 'xml'
            else:
                method = 'xhtml'
        return method

    def __call__(self, template_name, template_vars, **kwargs):
        """Render the template_vars with the Genshi template.

        If you don't pass a doctype or pass 'auto' as the doctype,
        then the doctype will be automatically determined.
        If you pass a doctype of None, then no doctype will be injected.
        If you don't pass a method or pass 'auto' as the method,
        then the method will be automatically determined.

        """
        response = tg.response._current_obj()

        template_vars.update(self.genshi_functions)

        # Gets document type from content type or from config options
        doctype = kwargs.get('doctype', 'auto')
        if doctype == 'auto':
            doctype = self.default_doctype
            if not doctype:
                method = kwargs.get('method') or self.default_method or 'xhtml'
                doctype = self.doctypes_for_methods.get(method)
            doctypes = self.doctypes_for_content_type.get(response.content_type)
            if doctypes and (not doctype or doctype not in doctypes):
                doctype = doctypes[0]
            kwargs['doctype'] = doctype

        # Gets rendering method from content type or from config options
        method = kwargs.get('method')
        if not method or method == 'auto':
            method = self.default_method
            if not method:
                method = self.method_for_doctype(doctype)
            methods = self.methods_for_content_type.get(response.content_type)
            if methods and (not method or method not in methods):
                method = methods[0]
            kwargs['method'] = method

        def render_template():
            template = self.load_template(template_name)
            return Markup(template.generate(**template_vars).render(
                    doctype=doctype, method=method, encoding=None))

        return cached_template(template_name, render_template,
                               ns_options=('doctype', 'method'), **kwargs)


class DottedTemplateLoader(GenshiTemplateLoader):
    """
    Genshi template loader supporting dotted filenames.
    Supports zipped applications and dotted filenames as well as path names.

    """
    def __init__(self, *args, **kwargs):
        self.template_extension = kwargs.pop('template_extension', '.html')
        self.dotted_finder = kwargs.pop('dotted_finder')

        super(DottedTemplateLoader, self).__init__(*args, **kwargs)

    def get_dotted_filename(self, filename):
        if not filename.endswith(self.template_extension):
            finder = self.dotted_finder
            filename = finder.get_dotted_filename(template_name=filename,
                                                  template_extension=self.template_extension)
        return filename

    def load(self, filename, relative_to=None, cls=None, encoding=None):
        """Actual loader function."""
        return super(DottedTemplateLoader, self).load(self.get_dotted_filename(filename),
                                                      relative_to=relative_to, cls=cls,
                                                      encoding=encoding)

########NEW FILE########
__FILENAME__ = jinja
from __future__ import absolute_import

from os.path import exists, getmtime
from tg.i18n import ugettext, ungettext
from tg.render import cached_template
from markupsafe import Markup
from .base import RendererFactory

try:
    import jinja2
except ImportError:  # pragma: no cover
    jinja2 = None

if jinja2 is not None:
    from jinja2.loaders import FileSystemLoader
    from jinja2 import ChoiceLoader, Environment
    from jinja2.filters import FILTERS
    from jinja2.exceptions import TemplateNotFound
else:  # pragma: no cover
    class FileSystemLoader(object): pass

__all__ = ['JinjaRenderer']


class JinjaRenderer(RendererFactory):
    engines = {'jinja': {'content_type': 'text/html'}}

    @classmethod
    def create(cls, config, app_globals):
        """Setup a renderer and loader for Jinja2 templates."""
        if jinja2 is None:  # pragma: no cover
            return None

        if config.get('use_dotted_templatenames', True):
            TemplateLoader = DottedTemplateLoader
            template_loader_args = {'dotted_finder': app_globals.dotted_filename_finder}
        else:
            TemplateLoader = FileSystemLoader
            template_loader_args = {}

        if not 'jinja_extensions' in config:
            config.jinja_extensions = []

        # Add i18n extension by default
        if not "jinja2.ext.i18n" in config.jinja_extensions:
            config.jinja_extensions.append("jinja2.ext.i18n")

        if not 'jinja_filters' in config:
            config.jinja_filters = {}

        loader = ChoiceLoader(
            [TemplateLoader(path, **template_loader_args) for path in config.paths['templates']])

        jinja2_env = Environment(loader=loader, autoescape=True,
                                 auto_reload=config.auto_reload_templates,
                                 extensions=config.jinja_extensions)

        # Try to load custom filters module under app_package.lib.templatetools
        try:
            if not config.package_name:
                raise AttributeError()

            filter_package = config.package_name + ".lib.templatetools"
            autoload_lib = __import__(filter_package, {}, {}, ['jinja_filters'])
            try:
                autoload_filters = dict(
                    map(lambda x: (x, autoload_lib.jinja_filters.__dict__[x]),
                                  autoload_lib.jinja_filters.__all__)
                )
            except AttributeError: #pragma: no cover
                autoload_filters = dict(
                    filter(lambda x: callable(x[1]),
                        autoload_lib.jinja_filters.__dict__.iteritems())
                )
        except (ImportError, AttributeError):
            autoload_filters = {}

        # Add jinja filters
        filters = dict(FILTERS, **autoload_filters)
        filters.update(config.jinja_filters)
        jinja2_env.filters = filters

        # Jinja's unable to request c's attributes without strict_c
        config['tg.strict_tmpl_context'] = True

        # Add gettext functions to the jinja environment
        jinja2_env.install_gettext_callables(ugettext, ungettext)

        return {'jinja': cls(jinja2_env)}

    def __init__(self, jinja2_env):
        self.jinja2_env = jinja2_env

    def __call__(self, template_name, template_vars, cache_key=None,
                 cache_type=None, cache_expire=None):
        """Render a template with Jinja2

        Accepts the cache options ``cache_key``, ``cache_type``, and
        ``cache_expire``.

        """
        # Create a render callable for the cache function
        def render_template():
            # Grab a template reference
            template = self.jinja2_env.get_template(template_name)
            return Markup(template.render(**template_vars))

        return cached_template(template_name, render_template,
                               cache_key=cache_key,
                               cache_type=cache_type,
                               cache_expire=cache_expire)


class DottedTemplateLoader(FileSystemLoader):
    """Jinja template loader supporting dotted filenames. Based on Genshi Loader

    """
    def __init__(self, *args, **kwargs):
        self.template_extension = kwargs.pop('template_extension', '.jinja')
        self.dotted_finder = kwargs.pop('dotted_finder')

        super(DottedTemplateLoader, self).__init__(*args, **kwargs)

    def get_source(self, environment, template):
        # Check if dottedname
        if not template.endswith(self.template_extension):
            # Get the actual filename from dotted finder
            finder = self.dotted_finder
            template = finder.get_dotted_filename(template_name=template,
                                                  template_extension=self.template_extension)
        else:
            return FileSystemLoader.get_source(self, environment, template)

        # Check if the template exists
        if not exists(template):
            raise TemplateNotFound(template)

        # Get modification time
        mtime = getmtime(template)

        # Read the source
        fd = open(template, 'rb')
        try:
            source = fd.read().decode('utf-8')
        finally:
            fd.close()

        return source, template, lambda: mtime == getmtime(template)

########NEW FILE########
__FILENAME__ = json
import tg
from tg.jsonify import encode
from .base import RendererFactory
from tg.exceptions import HTTPBadRequest

__all__ = ['JSONRenderer']


class JSONRenderer(RendererFactory):
    engines = {'json': {'content_type': 'application/json'},
               'jsonp': {'content_type': 'application/javascript'}}
    with_tg_vars = False

    @classmethod
    def create(cls, config, app_globals):
        return {'json': cls.render_json,
                'jsonp': cls.render_jsonp}

    @staticmethod
    def render_json(template_name, template_vars, **kwargs):
        return encode(template_vars)

    @staticmethod
    def render_jsonp(template_name, template_vars, **kwargs):
        pname = kwargs.get('callback_param', 'callback')
        callback = tg.request.GET.get(pname)
        if callback is None:
            raise HTTPBadRequest('JSONP requires a "%s" parameter with callback name' % pname)

        values = encode(template_vars)
        return '%s(%s);' % (callback, values)
########NEW FILE########
__FILENAME__ = kajiki
from __future__ import absolute_import

from tg.render import cached_template
from markupsafe import Markup
from .base import RendererFactory

try:
    import kajiki
except ImportError:  # pragma: no cover
    kajiki = None

if kajiki is not None:
    from kajiki.loader import FileLoader
else:  # pragma: no cover
    class FileLoader(object): pass

__all__ = ['KajikiRenderer']


class KajikiRenderer(RendererFactory):
    engines = {'kajiki': {'content_type': 'text/html'}}

    @classmethod
    def create(cls, config, app_globals):
        """Setup a renderer and loader for the Kajiki engine."""
        if kajiki is None:  # pragma: no cover
            return None

        loader = KajikiTemplateLoader(config.paths.templates[0],
                                      dotted_finder=app_globals.dotted_filename_finder,
                                      force_mode='xml',
                                      reload=config.auto_reload_templates,
                                      template_extension='.xml')
        return {'kajiki': cls(loader)}

    def __init__(self, loader):
        self.loader = loader

    def __call__(self, template_name, template_vars, cache_key=None,
                 cache_type=None, cache_expire=None, method='xhtml'):
        """Render a template with Kajiki

        Accepts the cache options ``cache_key``, ``cache_type``, and
        ``cache_expire`` in addition to method which are passed to Kajiki's
        render function.

        """
        # Create a render callable for the cache function
        def render_template():
            # Grab a template reference
            template = self.loader.load(template_name)
            return Markup(template(template_vars).render())

        return cached_template(template_name, render_template,
                               cache_key=cache_key, cache_type=cache_type,
                               cache_expire=cache_expire,
                               ns_options=('method'), method=method)


class KajikiTemplateLoader(FileLoader):
    """Kaijik template loader supporting dotted filenames.
    Solves also the issue of not supporting relative paths when using
    py:extends in Kaijiki
    """
    def __init__(self, base, dotted_finder, reload=True, force_mode=None, **kwargs):
        self.dotted_finder = dotted_finder
        self.template_extension = kwargs.pop('template_extension', '.xml')

        super(KajikiTemplateLoader, self).__init__(base, reload, force_mode, **kwargs)

    def _filename(self, filename):
        if not filename.endswith(self.template_extension):
            finder = self.dotted_finder
            filename = finder.get_dotted_filename(template_name=filename,
                                                  template_extension=self.template_extension)
        return super(KajikiTemplateLoader, self)._filename(filename)

########NEW FILE########
__FILENAME__ = mako
from __future__ import absolute_import

import os
import logging
import stat

try:
    import threading
except ImportError: #pragma: no cover
    import dummy_threading as threading

from tg.support.converters import asbool
from markupsafe import Markup
from tg.render import cached_template
from .base import RendererFactory

try:
    import mako
except ImportError:  # pragma: no cover
    mako = None

if mako is not None:
    from mako.template import Template
    from mako import exceptions
    from mako.lookup import TemplateLookup

__all__ = ['MakoRenderer']

log = logging.getLogger(__name__)


class MakoRenderer(RendererFactory):
    engines = {'mako': {'content_type': 'text/html'}}

    @classmethod
    def create(cls, config, app_globals):
        """
        Setup a renderer and loader for mako templates.
        """
        if mako is None:  # pragma: no cover
            return None

        use_dotted_templatenames = config.get('use_dotted_templatenames', True)

        # If no dotted names support was required we will just setup
        # a file system based template lookup mechanism.
        compiled_dir = config.get('templating.mako.compiled_templates_dir', None)

        if not compiled_dir or compiled_dir.lower() in ('none', 'false'):
            # Cache compiled templates in-memory
            compiled_dir = None
        else:
            bad_path = None
            if os.path.exists(compiled_dir):
                if not os.access(compiled_dir, os.W_OK):
                    bad_path = compiled_dir
                    compiled_dir = None
            else:
                try:
                    os.makedirs(compiled_dir)
                except:
                    bad_path = compiled_dir
                    compiled_dir = None
            if bad_path:
                log.warn("Unable to write cached templates to %r; falling back "
                         "to an in-memory cache. Please set the `templating.mak"
                         "o.compiled_templates_dir` configuration option to a "
                         "writable directory." % bad_path)

        dotted_finder = app_globals.dotted_filename_finder
        if use_dotted_templatenames:
            # Support dotted names by injecting a slightly different template
            # lookup system that will return templates from dotted template notation.
            mako_lookup = DottedTemplateLookup(
                input_encoding='utf-8', output_encoding='utf-8',
                imports=['from markupsafe import escape_silent as escape'],
                package_name=config.package_name,
                dotted_finder=dotted_finder,
                module_directory=compiled_dir,
                default_filters=['escape'],
                auto_reload_templates=config.auto_reload_templates)

        else:
            mako_lookup = TemplateLookup(
                directories=config.paths['templates'],
                module_directory=compiled_dir,
                input_encoding='utf-8', output_encoding='utf-8',
                imports=['from markupsafe import escape_silent as escape'],
                default_filters=['escape'],
                filesystem_checks=config.auto_reload_templates)

        return {'mako': cls(dotted_finder, mako_lookup, use_dotted_templatenames)}

    def __init__(self, dotted_finder, mako_lookup, use_dotted_templatenames):
        self.dotted_finder = dotted_finder
        self.loader = mako_lookup
        self.use_dotted_templatenames = use_dotted_templatenames

    def __call__(self, template_name, template_vars,
                 cache_key=None, cache_type=None, cache_expire=None):

        if self.use_dotted_templatenames:
            template_name = self.dotted_finder.get_dotted_filename(template_name,
                                                                   template_extension='.mak')

        # Create a render callable for the cache function
        def render_template():
            # Grab a template reference
            template = self.loader.get_template(template_name)
            return Markup(template.render_unicode(**template_vars))

        return cached_template(template_name, render_template, cache_key=cache_key,
                               cache_type=cache_type, cache_expire=cache_expire)


class DottedTemplateLookup(object):
    """Mako template lookup emulation that supports
    zipped applications and dotted filenames.

    This is an emulation of the Mako template lookup that will handle
    get_template and support dotted names in Python path notation
    to support zipped eggs.

    This is necessary because Mako asserts that your project will always
    be installed in a zip-unsafe manner with all files somewhere on the
    hard drive.

    This is not the case when you want your application to be deployed
    in a single zip file (zip-safe). If you want to deploy in a zip
    file _and_ use the dotted template name notation then this class
    is necessary because it emulates files on the filesystem for the
    underlying Mako engine while they are in fact in your zip file.

    """

    def __init__(self, input_encoding, output_encoding,
                 imports, default_filters, package_name,
                 dotted_finder, module_directory=None,
                 auto_reload_templates=False):

        self.package_name = package_name
        self.dotted_finder = dotted_finder

        self.input_encoding = input_encoding
        self.output_encoding = output_encoding
        self.imports = imports
        self.default_filters = default_filters
        # implement a cache for the loaded templates
        self.template_cache = dict()
        # implement a cache for the filename lookups
        self.template_filenames_cache = dict()
        self.module_directory = module_directory
        self.auto_reload = auto_reload_templates

        # a mutex to ensure thread safeness during template loading
        self._mutex = threading.Lock()

    def adjust_uri(self, uri, relativeto):
        """Adjust the given uri relative to a filename.

        This method is used by mako for filesystem based reasons.
        In dotted lookup land we don't adjust uri so we just return
        the value we are given without any change.

        """
        if uri.startswith('local:'):
            uri = self.package_name + '.' + uri[6:]

        if '.' in uri:
            # We are in the DottedTemplateLookup system so dots in
            # names should be treated as a Python path. Since this
            # method is called by template inheritance we must
            # support dotted names also in the inheritance.
            result = self.dotted_finder.get_dotted_filename(template_name=uri,
                                                            template_extension='.mak')

            if not uri in self.template_filenames_cache:
                # feed our filename cache if needed.
                self.template_filenames_cache[uri] = result

        else:
            # no dot detected, just return plain name
            result = uri

        return result

    def __check(self, template):
        """private method used to verify if a template has changed
        since the last time it has been put in cache...

        This method being based on the mtime of a real file this should
        never be called on a zipped deployed application.

        This method is a ~copy/paste of the original caching system from
        the Mako lookup loader.

        """
        if template.filename is None:
            return template


        if not os.path.exists(template.filename):
            # remove from cache.
            self.template_cache.pop(template.filename, None)
            raise exceptions.TemplateLookupException(
                    "Cant locate template '%s'" % template.filename)

        elif template.module._modified_time < os.stat(
                template.filename)[stat.ST_MTIME]:

            # cache is too old, remove old template
            # from cache and reload.
            self.template_cache.pop(template.filename, None)
            return self.__load(template.filename)

        else:
            # cache is correct, use it.
            return template

    def __load(self, filename):
        """real loader function. copy paste from the mako template
        loader.

        """
        # make sure the template loading from filesystem is only done
        # one thread at a time to avoid bad clashes...
        self._mutex.acquire()
        try:
            try:
                # try returning from cache one more time in case
                # concurrent thread already loaded
                return self.template_cache[filename]

            except KeyError:
                # not in cache yet... we can continue normally
                pass

            try:
                self.template_cache[filename] = Template(
                    filename=filename,
                    module_directory=self.module_directory,
                    input_encoding=self.input_encoding,
                    output_encoding=self.output_encoding,
                    default_filters=self.default_filters,
                    imports=self.imports,
                    lookup=self)

                return self.template_cache[filename]

            except:
                self.template_cache.pop(filename, None)
                raise

        finally:
            # _always_ release the lock once done to avoid
            # "thread lock" effect
            self._mutex.release()

    def get_template(self, template_name):
        """this is the emulated method that must return a template
        instance based on a given template name
        """

        if template_name not in self.template_cache:
            # the template string is not yet loaded into the cache.
            # Do so now
            self.__load(template_name)

        if self.auto_reload:
            # AUTO RELOADING will be activated only if user has
            # explicitly asked for it in the configuration
            # return the template, but first make sure it's not outdated
            # and if outdated, refresh the cache.
            return self.__check(self.template_cache[template_name])

        else:
            return self.template_cache[template_name]


########NEW FILE########
__FILENAME__ = request_local
import hmac, base64, binascii, re
from tg.support.objectproxy import TurboGearsObjectProxy
from tg.support.registry import StackedObjectProxy, DispatchingConfig
from tg.caching import cached_property

try:
    import cPickle as pickle
except ImportError: #pragma: no cover
    import pickle

try:
    from hashlib import sha1
except ImportError: #pragma: no cover
    import sha as sha1

from webob import Request as WebObRequest
from webob import Response as WebObResponse
from webob.request import PATH_SAFE
from webob.compat import url_quote as webob_url_quote, bytes_ as webob_bytes_

class Request(WebObRequest):
    """WebOb Request subclass

    The WebOb :class:`webob.Request` has no charset, or other defaults. This subclass
    adds defaults, along with several methods for backwards
    compatibility with paste.wsgiwrappers.WSGIRequest.

    """
    def languages_best_match(self, fallback=None):
        al = self.accept_language
        try:
            items = [i for i, q in sorted(al._parsed, key=lambda iq: -iq[1])]
        except AttributeError:
            #NilAccept has no _parsed, here for test units
            items = []

        if fallback:
            for index, item in enumerate(items):
                if al._match(item, fallback):
                    items[index:] = [fallback]
                    break
            else:
                items.append(fallback)

        return items

    @cached_property
    def controller_state(self):
        return self._controller_state

    @cached_property
    def controller_url(self):
        state = self._controller_state
        return '/'.join(state.path[:-len(state.remainder)])

    @cached_property
    def plain_languages(self):
        return self.languages_best_match()

    @property
    def languages(self):
        return self.languages_best_match(self._language)

    @property
    def language(self):
        return self._language

    @language.setter
    def language(self, value):
        self._language = value

    @property
    def response_type(self):
        return self._response_type

    @property
    def response_ext(self):
        return self._response_ext

    def match_accept(self, mimetypes):
        return self.accept.best_match(mimetypes)

    def signed_cookie(self, name, secret):
        """Extract a signed cookie of ``name`` from the request

        The cookie is expected to have been created with
        ``Response.signed_cookie``, and the ``secret`` should be the
        same as the one used to sign it.

        Any failure in the signature of the data will result in None
        being returned.

        """
        cookie = self.cookies.get(name)
        if not cookie:
            return

        secret = secret.encode('ascii')
        try:
            sig, pickled = cookie[:40], base64.decodestring(cookie[40:].encode('ascii'))
        except binascii.Error: #pragma: no cover
            # Badly formed data can make base64 die
            return

        if hmac.new(secret, pickled, sha1).hexdigest() == sig:
            return pickle.loads(pickled)

    @cached_property
    def args_params(self):
        # This was: dict(((str(n), v) for n,v in self.params.mixed().items()))
        # so that keys were all strings making possible to use them as arguments.
        # Now it seems that all keys are always strings, did WebOb change behavior?
        return self.params.mixed()

    @cached_property
    def quoted_path_info(self):
        bpath = webob_bytes_(self.path_info, self.url_encoding)
        return webob_url_quote(bpath, PATH_SAFE)

    def _fast_setattr(self, name, value):
        object.__setattr__(self, name, value)

class Response(WebObResponse):
    """WebOb Response subclass"""
    content = WebObResponse.body

    def wsgi_response(self):
        return self.status, self.headers, self.body

    def signed_cookie(self, name, data, secret, **kwargs):
        """Save a signed cookie with ``secret`` signature

        Saves a signed cookie of the pickled data. All other keyword
        arguments that ``WebOb.set_cookie`` accepts are usable and
        passed to the WebOb set_cookie method after creating the signed
        cookie value.

        """
        secret = secret.encode('ascii')

        pickled = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
        sig = hmac.new(secret, pickled, sha1).hexdigest().encode('ascii')
        cookie_value = sig + base64.encodestring(pickled)
        self.set_cookie(name, cookie_value, **kwargs)

config = DispatchingConfig()
context = StackedObjectProxy(name="context")

class TurboGearsContextMember(TurboGearsObjectProxy):
    """Member of the TurboGears request context.

    Provides access to turbogears context members
    like request, response, template context and so on

    """

    def __init__(self, name):
        self.__dict__['name'] = name

    def _current_obj(self):
        return getattr(context, self.name)


request = TurboGearsContextMember(name="request")
app_globals = TurboGearsContextMember(name="app_globals")
cache = TurboGearsContextMember(name="cache")
response = TurboGearsContextMember(name="response")
session = TurboGearsContextMember(name="session")
tmpl_context = TurboGearsContextMember(name="tmpl_context")
url = TurboGearsContextMember(name="url")
translator = TurboGearsContextMember(name="translator")

__all__ = ['app_globals', 'request', 'response', 'tmpl_context', 'session', 'cache', 'translator', 'url', 'config']
########NEW FILE########
__FILENAME__ = converters
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
from tg._compat import string_type


def asbool(obj):
    if isinstance(obj, string_type):
        obj = obj.strip().lower()
        if obj in ['true', 'yes', 'on', 'y', 't', '1']:
            return True
        elif obj in ['false', 'no', 'off', 'n', 'f', '0']:
            return False
        else:
            raise ValueError("String is not true/false: %r" % obj)
    return bool(obj)


def asint(obj):
    try:
        return int(obj)
    except (TypeError, ValueError):
        raise ValueError("Bad integer value: %r" % obj)


def aslist(obj, sep=None, strip=True):
    if isinstance(obj, string_type):
        lst = obj.split(sep)
        if strip:
            lst = [v.strip() for v in lst]
        return lst
    elif isinstance(obj, (list, tuple)):
        return obj
    elif obj is None:
        return []
    else:
        return [obj]

########NEW FILE########
__FILENAME__ = middlewares
from tg.request_local import Request, Response

import logging
log = logging.getLogger(__name__)


def _call_wsgi_application(application, environ):
    """
    Call the given WSGI application, returning ``(status_string,
    headerlist, app_iter)``

    Be sure to call ``app_iter.close()`` if it's there.
    """
    captured = []
    output = []
    def _start_response(status, headers, exc_info=None):
        captured[:] = [status, headers, exc_info]
        return output.append

    app_iter = application(environ, _start_response)
    if not captured or output:
        try:
            output.extend(app_iter)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        app_iter = output
    return (captured[0], captured[1], app_iter, captured[2])


class StatusCodeRedirect(object):
    """Internally redirects a request based on status code

    StatusCodeRedirect watches the response of the app it wraps. If the
    response is an error code in the errors sequence passed the request
    will be re-run with the path URL set to the path passed in.

    This operation is non-recursive and the output of the second
    request will be used no matter what it is.

    Should an application wish to bypass the error response (ie, to
    purposely return a 401), set
    ``environ['tg.status_code_redirect'] = False`` in the application.

    """
    def __init__(self, app, errors=(400, 401, 403, 404),
                 path='/error/document'):
        """Initialize the ErrorRedirect

        ``errors``
            A sequence (list, tuple) of error code integers that should
            be caught.
        ``path``
            The path to set for the next request down to the
            application.

        """
        self.app = app
        self.error_path = path

        # Transform errors to str for comparison
        self.errors = tuple([str(x) for x in errors])

    def __call__(self, environ, start_response):
        status, headers, app_iter, exc_info = _call_wsgi_application(self.app, environ)
        if status[:3] in self.errors and \
            'tg.status_code_redirect' not in environ and self.error_path:
            # Create a response object
            environ['tg.original_response'] = Response(status=status, headerlist=headers, app_iter=app_iter)
            environ['tg.original_request'] = Request(environ)

            environ['pylons.original_response'] = environ['tg.original_response']
            environ['pylons.original_request'] = environ['tg.original_request']
            
            # Create a new environ to avoid touching the original request data
            new_environ = environ.copy()
            new_environ['PATH_INFO'] = self.error_path

            newstatus, headers, app_iter, exc_info = _call_wsgi_application(self.app, new_environ)
        start_response(status, headers, exc_info)
        return app_iter

from beaker.middleware import CacheMiddleware as BeakerCacheMiddleware
from beaker.middleware import SessionMiddleware as BeakerSessionMiddleware


class SessionMiddleware(BeakerSessionMiddleware):
    session = None


class CacheMiddleware(BeakerCacheMiddleware):
    cache = None


class SeekableRequestBodyMiddleware(object):
    def __init__(self, app):
        self.app = app

    def _stream_response(self, data):
        try:
            for chunk in data:
                yield chunk
        finally:
            if hasattr(data, 'close'):
                data.close()

    def __call__(self, environ, start_response):
        log.debug("Making request body seekable")
        Request(environ).make_body_seekable()
        return self._stream_response(self.app(environ, start_response))


class DBSessionRemoverMiddleware(object):
    def __init__(self, DBSession, app):
        self.app = app
        self.DBSession = DBSession

    def _stream_response(self, data):
        try:
            for chunk in data:
                yield chunk
        finally:
            log.debug("Removing DBSession from current thread")
            if hasattr(data, 'close'):
                data.close()
            self.DBSession.remove()

    def __call__(self, environ, start_response):
        try:
            return self._stream_response(self.app(environ, start_response))
        except:
            log.debug("Removing DBSession from current thread")
            self.DBSession.remove()
            raise


from .statics import StaticsMiddleware

__all__ = ['StatusCodeRedirect', 'CacheMiddleware', 'SessionMiddleware', 'StaticsMiddleware',
           'SeekableRequestBodyMiddleware', 'DBSessionRemoverMiddleware']

########NEW FILE########
__FILENAME__ = objectproxy

class TurboGearsObjectProxy(object):
    """
    Foundation for the TurboGears request locals
    and StackedObjectProxy.

    Mostly inspired by paste.registry.StackedObjectProxy
    """
    def __dir__(self):
        dir_list = dir(self.__class__) + list(self.__dict__.keys())
        try:
            dir_list.extend(dir(self._current_obj()))
        except TypeError:
            pass
        dir_list.sort()
        return dir_list

    def __getattr__(self, attr):
        return getattr(self._current_obj(), attr)

    def __setattr__(self, attr, value):
        setattr(self._current_obj(), attr, value)

    def __delattr__(self, name):
        delattr(self._current_obj(), name)

    def __getitem__(self, key):
        return self._current_obj()[key]

    def __setitem__(self, key, value):
        self._current_obj()[key] = value

    def __delitem__(self, key):
        del self._current_obj()[key]

    def __call__(self, *args, **kw):
        return self._current_obj()(*args, **kw)

    def __repr__(self):
        try:
            return repr(self._current_obj())
        except (TypeError, AttributeError):
            return '<%s.%s object at 0x%x>' % (self.__class__.__module__,
                                               self.__class__.__name__,
                                               id(self))

    def __iter__(self):
        return iter(self._current_obj())

    def __len__(self):
        return len(self._current_obj())

    def __contains__(self, key):
        return key in self._current_obj()

    def __nonzero__(self):
        return bool(self._current_obj())
########NEW FILE########
__FILENAME__ = paginate
import re, string
from tg import request
from tg.controllers.util import url

from markupsafe import Markup
from markupsafe import escape_silent as escape

try:
    import sqlalchemy
    import sqlalchemy.orm
    from sqlalchemy.orm.query import Query as SQLAQuery
except ImportError:  # pragma: no cover
    class SQLAQuery(object):
        pass

try:
    from ming.odm.odmsession import ODMCursor as MingCursor
except ImportError:  # pragma: no cover
    class MingCursor(object):
        pass

def _format_attrs(**attrs):
    strings = [' %s="%s"' % (attr, escape(value)) for attr, value in attrs.items() if value is not None]
    return Markup("".join(strings))

def _make_tag(template, text, **attrs):
    return Markup(template % (_format_attrs(**attrs), escape(text))) 

class _SQLAlchemyQueryWrapper(object):
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, range):
        return self.obj[range]

    def __len__(self):
        return self.obj.count()

class _MingQueryWrapper(object):
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, range):
        return self.obj.skip(range.start).limit(range.stop-range.start)

    def __len__(self):
        return self.obj.count()

def _wrap_collection(col):
    if isinstance(col, SQLAQuery):
        return _SQLAlchemyQueryWrapper(col)
    elif isinstance(col, MingCursor):
        return _MingQueryWrapper(col)
    return col

class Page(object):
    """
    TurboGears Pagination support for @paginate decorator.
    It is based on a striped down version of the WebHelpers pagination class
    This represents a page inside a collection of items
    """
    def __init__(self, collection, page=1, items_per_page=20):
        """
        Create a "Page" instance.

        Parameters:

        collection
            Sequence, can be a a list of items or an SQLAlchemy query.

        page
            The requested page number - starts with 1. Default: 1.

        items_per_page
            The maximal number of items to be displayed per page.
            Default: 20.
        """
        self.kwargs = {}
        self.collection = _wrap_collection(collection)

        # The self.page is the number of the current page.
        try:
            self.page = int(page)
        except (ValueError, TypeError):
            self.page = 1

        self.items_per_page = items_per_page
        self.item_count = len(self.collection)

        if not self.item_count:
            #Empty collection, just set everything at empty
            self.first_page = None
            self.page_count = 0
            self.last_page = None
            self.first_item = None
            self.last_item = None
            self.previous_page = None
            self.next_page = None
            self.items = []
        else:
            #Otherwise compute the actual pagination values
            self.first_page = 1
            self.page_count = ((self.item_count - 1) // self.items_per_page) + 1
            self.last_page = self.first_page + self.page_count - 1

            # Make sure that the requested page number is the range of valid pages
            if self.page > self.last_page:
                self.page = self.last_page
            elif self.page < self.first_page:
                self.page = self.first_page

            # Note: the number of items on this page can be less than
            #       items_per_page if the last page is not full
            self.first_item = (self.page - 1) * items_per_page + 1
            self.last_item = min(self.first_item + items_per_page - 1, self.item_count)

            try:
                first = self.first_item - 1
                last = self.last_item
                self.items = list(self.collection[first:last])
            except TypeError: #pragma: no cover
                raise

            # Links to previous and next page
            if self.page > self.first_page:
                self.previous_page = self.page-1
            else:
                self.previous_page = None

            if self.page < self.last_page:
                self.next_page = self.page+1
            else:
                self.next_page = None

    def pager(self, format='~2~', page_param='page', partial_param='partial',
              show_if_single_page=False, separator=' ', onclick=None,
              symbol_first='<<', symbol_last='>>',
              symbol_previous='<', symbol_next='>',
              link_attr={'class':'pager_link'},
              curpage_attr={'class':'pager_curpage'},
              dotdot_attr={'class':'pager_dotdot'},
              page_link_template='<a%s>%s</a>',
              page_plain_template='<span%s>%s</span>',
              **kwargs):
        """
        Return string with links to other pages (e.g. "1 2 [3] 4 5 6 7").

        format:
            Format string that defines how the pager is rendered. The string
            can contain the following $-tokens that are substituted by the
            string.Template module:

            - $first_page: number of first reachable page
            - $last_page: number of last reachable page
            - $page: number of currently selected page
            - $page_count: number of reachable pages
            - $items_per_page: maximal number of items per page
            - $first_item: index of first item on the current page
            - $last_item: index of last item on the current page
            - $item_count: total number of items
            - $link_first: link to first page (unless this is first page)
            - $link_last: link to last page (unless this is last page)
            - $link_previous: link to previous page (unless this is first page)
            - $link_next: link to next page (unless this is last page)

            To render a range of pages the token '~3~' can be used. The
            number sets the radius of pages around the current page.
            Example for a range with radius 3:

            '1 .. 5 6 7 [8] 9 10 11 .. 500'

            Default: '~2~'

        symbol_first
            String to be displayed as the text for the %(link_first)s
            link above.

            Default: '<<'

        symbol_last
            String to be displayed as the text for the %(link_last)s
            link above.

            Default: '>>'

        symbol_previous
            String to be displayed as the text for the %(link_previous)s
            link above.

            Default: '<'

        symbol_next
            String to be displayed as the text for the %(link_next)s
            link above.

            Default: '>'

        separator:
            String that is used to separate page links/numbers in the
            above range of pages.

            Default: ' '

        page_param:
            The name of the parameter that will carry the number of the
            page the user just clicked on.

        partial_param:
            When using AJAX/AJAH to do partial updates of the page area the
            application has to know whether a partial update (only the
            area to be replaced) or a full update (reloading the whole
            page) is required. So this parameter is the name of the URL
            parameter that gets set to 1 if the 'onclick' parameter is
            used. So if the user requests a new page through a Javascript
            action (onclick) then this parameter gets set and the application
            is supposed to return a partial content. And without
            Javascript this parameter is not set. The application thus has
            to check for the existence of this parameter to determine
            whether only a partial or a full page needs to be returned.
            See also the examples in this modules docstring.

            Default: 'partial'

            Note: If you set this argument and are using a URL generator
            callback, the callback must accept this name as an argument instead
            of 'partial'.

        show_if_single_page:
            if True the navigator will be shown even if there is only
            one page

            Default: False

        link_attr (optional)
            A dictionary of attributes that get added to A-HREF links
            pointing to other pages. Can be used to define a CSS style
            or class to customize the look of links.

            Example: { 'style':'border: 1px solid green' }

            Default: { 'class':'pager_link' }

        curpage_attr (optional)
            A dictionary of attributes that get added to the current
            page number in the pager (which is obviously not a link).
            If this dictionary is not empty then the elements
            will be wrapped in a SPAN tag with the given attributes.

            Example: { 'style':'border: 3px solid blue' }

            Default: { 'class':'pager_curpage' }

        dotdot_attr (optional)
            A dictionary of attributes that get added to the '..' string
            in the pager (which is obviously not a link). If this
            dictionary is not empty then the elements will be wrapped in
            a SPAN tag with the given attributes.

            Example: { 'style':'color: #808080' }

            Default: { 'class':'pager_dotdot' }

        page_link_template (optional)
            A string with the template used to render page links

            Default: '<a%s>%s</a>'

        page_plain_template (optional)
            A string with the template used to render current page,
            and dots in pagination.

            Default: '<span%s>%s</span>'

        onclick (optional)
            This paramter is a string containing optional Javascript code
            that will be used as the 'onclick' action of each pager link.
            It can be used to enhance your pager with AJAX actions loading another
            page into a DOM object.

            In this string the variable '$partial_url' will be replaced by
            the URL linking to the desired page with an added 'partial=1'
            parameter (or whatever you set 'partial_param' to).
            In addition the '$page' variable gets replaced by the
            respective page number.

            Note that the URL to the destination page contains a 'partial_param'
            parameter so that you can distinguish between AJAX requests (just
            refreshing the paginated area of your page) and full requests (loading
            the whole new page).

            [Backward compatibility: you can use '%s' instead of '$partial_url']

            jQuery example:
                "$('#my-page-area').load('$partial_url'); return false;"

            Yahoo UI example:
                "YAHOO.util.Connect.asyncRequest('GET','$partial_url',{
                    success:function(o){YAHOO.util.Dom.get('#my-page-area').innerHTML=o.responseText;}
                    },null); return false;"

            scriptaculous example:
                "new Ajax.Updater('#my-page-area', '$partial_url',
                    {asynchronous:true, evalScripts:true}); return false;"

            ExtJS example:
                "Ext.get('#my-page-area').load({url:'$partial_url'}); return false;"

            Custom example:
                "my_load_page($page)"

        Additional keyword arguments are used as arguments in the links.
        """
        self.curpage_attr = curpage_attr
        self.separator = separator
        self.pager_kwargs = kwargs
        self.page_param = page_param
        self.partial_param = partial_param
        self.onclick = onclick
        self.link_attr = link_attr
        self.dotdot_attr = dotdot_attr
        self.page_link_template = page_link_template
        self.page_plain_template = page_plain_template

        # Don't show navigator if there is no more than one page
        if self.page_count == 0 or (self.page_count == 1 and not show_if_single_page):
            return ''

        # Replace ~...~ in token format by range of pages
        result = re.sub(r'~(\d+)~', self._range, format)

        # Interpolate '%' variables
        result = string.Template(result).safe_substitute({
            'first_page': self.first_page,
            'last_page': self.last_page,
            'page': self.page,
            'page_count': self.page_count,
            'items_per_page': self.items_per_page,
            'first_item': self.first_item,
            'last_item': self.last_item,
            'item_count': self.item_count,
            'link_first': self.page>self.first_page and\
                          self._pagerlink(self.first_page, symbol_first) or '',
            'link_last': self.page<self.last_page and\
                         self._pagerlink(self.last_page, symbol_last) or '',
            'link_previous': self.previous_page and\
                             self._pagerlink(self.previous_page, symbol_previous) or '',
            'link_next': self.next_page and\
                         self._pagerlink(self.next_page, symbol_next) or ''
        })

        return Markup(result)

    #### Private methods ####
    def _range(self, regexp_match):
        """
        Return range of linked pages (e.g. '1 2 [3] 4 5 6 7 8').

        Arguments:

        regexp_match
            A "re" (regular expressions) match object containing the
            radius of linked pages around the current page in
            regexp_match.group(1) as a string

        This function is supposed to be called as a callable in
        re.sub.

        """
        radius = int(regexp_match.group(1))

        # Compute the first and last page number within the radius
        # e.g. '1 .. 5 6 [7] 8 9 .. 12'
        # -> leftmost_page  = 5
        # -> rightmost_page = 9
        leftmost_page = max(self.first_page, (self.page-radius))
        rightmost_page = min(self.last_page, (self.page+radius))

        nav_items = []

        # Create a link to the first page (unless we are on the first page
        # or there would be no need to insert '..' spacers)
        if self.page != self.first_page and self.first_page < leftmost_page:
            nav_items.append( self._pagerlink(self.first_page, self.first_page) )

        # Insert dots if there are pages between the first page
        # and the currently displayed page range
        if leftmost_page - self.first_page > 1:
            # Wrap in a SPAN tag if nolink_attr is set
            text = '..'
            if self.dotdot_attr:
                text = _make_tag(self.page_plain_template, text, **self.dotdot_attr)
            nav_items.append(text)

        for thispage in range(leftmost_page, rightmost_page+1):
            # Hilight the current page number and do not use a link
            if thispage == self.page:
                text = '%s' % (thispage,)
                # Wrap in a SPAN tag if nolink_attr is set
                if self.curpage_attr:
                    text = _make_tag(self.page_plain_template, text, **self.curpage_attr)
                nav_items.append(text)
            # Otherwise create just a link to that page
            else:
                text = '%s' % (thispage,)
                nav_items.append( self._pagerlink(thispage, text) )

        # Insert dots if there are pages between the displayed
        # page numbers and the end of the page range
        if self.last_page - rightmost_page > 1:
            text = '..'
            # Wrap in a SPAN tag if nolink_attr is set
            if self.dotdot_attr:
                text = _make_tag(self.page_plain_template, text, **self.dotdot_attr)
            nav_items.append(text)

        # Create a link to the very last page (unless we are on the last
        # page or there would be no need to insert '..' spacers)
        if self.page != self.last_page and rightmost_page < self.last_page:
            nav_items.append( self._pagerlink(self.last_page, self.last_page) )

        return self.separator.join(nav_items)

    def _pagerlink(self, pagenr, text):
        """
        Create a URL that links to another page.

        Parameters:

        pagenr
            Number of the page that the link points to

        text
            Text to be printed in the A-HREF tag
        """
        link_params = {}
        # Use the instance kwargs as URL parameters
        link_params.update(self.kwargs)
        # Add keyword arguments from pager() to the link as parameters
        link_params.update(self.pager_kwargs)
        link_params[self.page_param] = pagenr

        # Create the URL to load the page area part of a certain page (AJAX updates)
        partial_url = link_params.pop('partial', '')

        # Create the URL to load a certain page
        link_url = link_params.pop('link', request.path_info)
        link_url = Markup(url(link_url, params=link_params))

        if self.onclick: # create link with onclick action for AJAX
            try: # if '%s' is used in the 'onclick' parameter (backwards compatibility)
                onclick_action = self.onclick % (partial_url,)
            except TypeError:
                onclick_action = string.Template(self.onclick).safe_substitute({
                  "partial_url": partial_url,
                  "page": pagenr
                })
            return _make_tag(self.page_link_template, text, href=link_url, onclick=onclick_action, **self.link_attr)
        else: # return static link
            return _make_tag(self.page_link_template, text, href=link_url, **self.link_attr)

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def __json__(self):
        return {'total':self.item_count, 
                'page':self.page, 
                'items_per_page':self.items_per_page, 
                'entries':self.items}

########NEW FILE########
__FILENAME__ = registry
"""
This is a striped down version of the Python Paste Registry Module
it is not meant to be used by itself, it's only purpose is to provide
global objects for TurboGears2.

# Original Module (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""

from tg.support.objectproxy import TurboGearsObjectProxy
from tg.support import NoDefault
import itertools, time
import threading as threadinglocal

__all__ = ['StackedObjectProxy', 'RegistryManager']

def _getboolattr(obj, attrname):
    try:
        return object.__getattribute__(obj, attrname)
    except AttributeError:
        return None


class StackedObjectProxy(TurboGearsObjectProxy):
    """Track an object instance internally using a stack

    The StackedObjectProxy proxies access to an object internally using a
    stacked thread-local. This makes it safe for complex WSGI environments
    where access to the object may be desired in multiple places without
    having to pass the actual object around.

    New objects are added to the top of the stack with _push_object while
    objects can be removed with _pop_object.

    """
    def __init__(self, default=NoDefault, name="Default"):
        """Create a new StackedObjectProxy

        If a default is given, its used in every thread if no other object
        has been pushed on.

        """
        self.__dict__['____name__'] = name
        self.__dict__['____local__'] = threadinglocal.local()
        if default is not NoDefault:
            self.__dict__['____default_object__'] = default

    def _current_obj(self):
        """Returns the current active object being proxied to

        In the event that no object was pushed, the default object if
        provided will be used. Otherwise, a TypeError will be raised.

        """
        try:
            objects = self.____local__.objects
        except AttributeError:
            objects = None
        if objects:
            return objects[-1][0]
        else:
            obj = self.__dict__.get('____default_object__', NoDefault)
            if obj is not NoDefault:
                return obj
            else:
                raise TypeError(
                    'No object (name: %s) has been registered for this '
                    'thread' % self.____name__)

    def _push_object(self, obj):
        """Make ``obj`` the active object for this thread-local.

        This should be used like:

        .. code-block:: python

            obj = yourobject()
            module.glob = StackedObjectProxy()
            module.glob._push_object(obj)
            try:
                ... do stuff ...
            finally:
                module.glob._pop_object(conf)

        """
        try:
            self.____local__.objects.append((obj, False))
        except AttributeError:
            self.____local__.objects = []
            self.____local__.objects.append((obj, False))

    def _pop_object(self, obj=None):
        """Remove a thread-local object.

        If ``obj`` is given, it is checked against the popped object and an
        error is emitted if they don't match.

        """
        try:
            popped = self.____local__.objects.pop()
            popped_obj = popped[0]
            if obj and popped_obj is not obj:
                raise AssertionError(
                    'The object popped (%s) is not the same as the object '
                    'expected (%s)' % (popped_obj, obj))
        except (AttributeError, IndexError):
            raise AssertionError('No object has been registered for this thread')

    def _object_stack(self):
        """Returns all of the objects stacked in this container

        (Might return [] if there are none)
        """
        try:
            try:
                objs = self.____local__.objects
            except AttributeError:
                return []
            return objs[:]
        except AssertionError: #pragma: no cover
            return []

    def _preserve_object(self):
        try:
            object, preserved = self.____local__.objects[-1]
        except (AttributeError, IndexError):
            return

        self.____local__.objects[-1] = (object, True)

    @property
    def _is_preserved(self):
        try:
            objects = self.____local__.objects
        except AttributeError:
            return False

        if not objects:
            return False

        object, preserved = objects[-1]
        return preserved

class Registry(object):
    """Track objects and stacked object proxies for removal

    The Registry object is instantiated a single time for the request no
    matter how many times the RegistryManager is used in a WSGI stack. Each
    RegistryManager must call ``prepare`` before continuing the call to
    start a new context for object registering.

    Each context is tracked with a dict inside a list. The last list
    element is the currently executing context. Each context dict is keyed
    by the id of the StackedObjectProxy instance being proxied, the value
    is a tuple of the StackedObjectProxy instance and the object being
    tracked.

    """
    def __init__(self, enable_preservation=False):
        """Create a new Registry object

        ``prepare`` must still be called before this Registry object can be
        used to register objects.

        """
        self.reglist = []

        #preservation makes possible to keep around the objects
        #this is especially useful when debugging to avoid
        #discarding the objects after request completion.
        self.enable_preservation = enable_preservation

    def prepare(self):
        """Used to create a new registry context

        Anytime a new RegistryManager is called, ``prepare`` needs to be
        called on the existing Registry object. This sets up a new context
        for registering objects.

        """
        self.reglist.append({})

    def register(self, stacked, obj):
        """Register an object with a StackedObjectProxy"""

        if stacked is None:
            #makes possible to disable registering for some
            #stacked objects by setting them to None.
            return

        myreglist = self.reglist[-1]
        stacked_id = id(stacked)
        if stacked_id in myreglist:
            stacked._pop_object(myreglist[stacked_id][1])
            del myreglist[stacked_id]

        #Avoid leaking memory on successive request when preserving objects
        if self.enable_preservation and _getboolattr(stacked, '_is_preserved'):
            stacked._pop_object()

        stacked._push_object(obj)
        myreglist[stacked_id] = (stacked, obj)

    def cleanup(self):
        """Remove all objects from all StackedObjectProxy instances that
        were tracked at this Registry context"""
        for stacked, obj in self.reglist[-1].values():
            if not _getboolattr(stacked, '_is_preserved'):
                stacked._pop_object(obj)
        self.reglist.pop()

    def preserve(self):
        if not self.enable_preservation:
            return

        for stacked, obj in self.reglist[-1].values():
            if hasattr(stacked, '_preserve_object'):
                stacked._preserve_object()

class RegistryManager(object):
    """Creates and maintains a Registry context

    RegistryManager creates a new registry context for the registration of
    StackedObjectProxy instances. Multiple RegistryManager's can be in a
    WSGI stack and will manage the context so that the StackedObjectProxies
    always proxy to the proper object.

    The object being registered can be any object sub-class, list, or dict.

    Registering objects is done inside a WSGI application under the
    RegistryManager instance, using the ``environ['paste.registry']``
    object which is a Registry instance.

    """
    def __init__(self, application, streaming=False, preserve_exceptions=False):
        self.application = application
        self.streaming = streaming
        self.preserve_exceptions = preserve_exceptions

    def __call__(self, environ, start_response):
        app_iter = None
        reg = environ.setdefault('paste.registry', Registry(self.preserve_exceptions))
        reg.prepare()

        try:
            app_iter = self.application(environ, start_response)
        except:
            reg.preserve()
            reg.cleanup()
            raise
        else:
            # If we are streaming streaming_iter will cleanup things for us
            if not self.streaming:
                reg.cleanup()

        if self.streaming:
            return self.streaming_iter(reg, app_iter)

        return app_iter

    def streaming_iter(self, reg, data):
        try:
            for chunk in data:
                yield chunk
        except:
            reg.preserve()
            raise
        finally:
            if hasattr(data, 'close'):
                data.close()
            reg.cleanup()

class DispatchingConfig(StackedObjectProxy):
    """
    This is a configuration object that can be used globally,
    imported, have references held onto.  The configuration may differ
    by thread (or may not).

    Specific configurations are registered (and deregistered) either
    for the process or for threads.
    """
    # @@: What should happen when someone tries to add this
    # configuration to itself?  Probably the conf should become
    # resolved, and get rid of this delegation wrapper

    def __init__(self, name='DispatchingConfig'):
        super(DispatchingConfig, self).__init__(name=name)
        self.__dict__['_process_configs'] = []

    def push_thread_config(self, conf):
        """
        Make ``conf`` the active configuration for this thread.
        Thread-local configuration always overrides process-wide
        configuration.

        This should be used like::

            conf = make_conf()
            dispatching_config.push_thread_config(conf)
            try:
                ... do stuff ...
            finally:
                dispatching_config.pop_thread_config(conf)
        """
        self._push_object(conf)

    def pop_thread_config(self, conf=None):
        """
        Remove a thread-local configuration.  If ``conf`` is given,
        it is checked against the popped configuration and an error
        is emitted if they don't match.
        """
        self._pop_object(conf)

    def push_process_config(self, conf):
        """
        Like push_thread_config, but applies the configuration to
        the entire process.
        """
        self._process_configs.append(conf)

    def pop_process_config(self, conf=None):
        self._pop_from(self._process_configs, conf)

    def _pop_from(self, lst, conf):
        popped = lst.pop()
        if conf is not None and popped is not conf:
            raise AssertionError(
                "The config popped (%s) is not the same as the config "
                "expected (%s)"
                % (popped, conf))

    def _current_obj(self):
        try:
            return super(DispatchingConfig, self)._current_obj()
        except TypeError:
            if self._process_configs:
                return self._process_configs[-1]
            raise AttributeError(
                "No configuration has been registered for this process "
                "or thread")
    current = current_conf = _current_obj

########NEW FILE########
__FILENAME__ = statics
from datetime import datetime
from email.utils import parsedate_tz, mktime_tz
import mimetypes
from time import gmtime, time
from os.path import normcase, normpath, join, isfile, getmtime, getsize
from webob.exc import HTTPNotFound, HTTPForbidden, HTTPBadRequest
from repoze.lru import LRUCache

_BLOCK_SIZE = 4096 * 64 # 256K

mimetypes.init()

class _FileIter(object):
    def __init__(self, file, block_size):
        self.file = file
        self.block_size = block_size

    def __iter__(self):
        return self

    def next(self):
        val = self.file.read(self.block_size)
        if not val:
            raise StopIteration
        return val

    __next__ = next # py3

    def close(self):
        self.file.close()

class FileServeApp(object):
    """
    Serves a static filelike object.
    """
    def __init__(self, path, cache_max_age):
        self.path = path

        try:
            self.last_modified = getmtime(path)
            self.content_length = getsize(path)
        except (IOError, OSError):
            self.path = None

        if self.path is not None:
            content_type, content_encoding = mimetypes.guess_type(path, strict=False)
            if content_type is None:
                content_type = 'application/octet-stream'

            self.content_type = content_type
            self.content_encoding = content_encoding

        if cache_max_age is not None:
            self.cache_expires = cache_max_age

    def generate_etag(self):
        return '"%s-%s"' % (self.last_modified, self.content_length)

    def parse_date(self, value):
        try:
            return mktime_tz(parsedate_tz(value))
        except (TypeError, OverflowError):
            raise HTTPBadRequest(("Received an ill-formed timestamp for %s: %s\r\n") % (self.path, value))

    @classmethod
    def make_date(cls, d):
        if isinstance(d, datetime):
            d = d.utctimetuple()
        else:
            d = gmtime(d)

        return '%s, %02d%s%s%s%s %02d:%02d:%02d GMT' % (
            ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[d.tm_wday],
            d.tm_mday, ' ',
            ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
             'Oct', 'Nov', 'Dec')[d.tm_mon - 1],
            ' ', str(d.tm_year), d.tm_hour, d.tm_min, d.tm_sec)


    def has_been_modified(self, environ, etag, last_modified):
        if environ['REQUEST_METHOD'] not in ('GET', 'HEAD'):
            return False

        unmodified = False

        modified_since = environ.get('HTTP_IF_MODIFIED_SINCE')
        if modified_since:
            modified_since = self.parse_date(modified_since)
            if last_modified and last_modified <= modified_since:
                unmodified = True

        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match and etag == if_none_match:
            unmodified = True

        return not unmodified

    def __call__(self, environ, start_response):
        try:
            file = open(self.path, 'rb')
        except (IOError, OSError, TypeError) as e:
            return HTTPForbidden('You are not permitted to view this file (%s)' % e)(environ, start_response)

        headers = []
        timeout = self.cache_expires
        etag = self.generate_etag()
        headers += [('Etag', '%s' % etag),
            ('Cache-Control', 'max-age=%d, public' % timeout)]

        if not self.has_been_modified(environ, etag, self.last_modified):
            file.close()
            start_response('304 Not Modified', headers)
            return []

        headers.extend((
            ('Expires', self.make_date(time() + timeout)),
            ('Content-Type', self.content_type),
            ('Content-Length', str(self.content_length)),
            ('Last-Modified', self.make_date(self.last_modified))
            ))
        start_response('200 OK', headers)
        return environ.get('wsgi.file_wrapper', _FileIter)(file, _BLOCK_SIZE)

INVALID_PATH_PARTS = set(['..', '.']).intersection

class StaticsMiddleware(object):
    def _adapt_path(self, path):
        return normcase(normpath(path))

    def __init__(self, app, root_dir, cache_max_age=3600):
        self.app = app
        self.cache_max_age = cache_max_age
        self.doc_root = self._adapt_path(root_dir)
        self.paths_cache = LRUCache(1024)

    def __call__(self, environ, start_response):
        full_path = environ['PATH_INFO']
        filepath = self.paths_cache.get(full_path)

        if filepath is None:
            path = full_path.split('/')
            if INVALID_PATH_PARTS(path):
                return HTTPNotFound('Out of bounds: %s' % environ['PATH_INFO'])(environ, start_response)
            filepath = self._adapt_path(join(self.doc_root, *path))
            self.paths_cache.put(full_path, filepath)

        if isfile(filepath):
            return FileServeApp(filepath, self.cache_max_age)(environ, start_response)

        return self.app(environ, start_response)


########NEW FILE########
__FILENAME__ = transaction_manager
from tg._compat import reraise
from tg.request_local import Request
import sys
import transaction

import logging
log = logging.getLogger('tg.transaction_manager')


class AbortTransaction(Exception):
    def __init__(self, response_data):
        self.response_data = response_data


class TGTransactionManager(object):
    def __init__(self, app, config):
        self.app = app
        self.config = config

        self.attempts = config.get('tm.attempts', 1)
        self.commit_veto = config.get('tm.commit_veto', None)

    def __call__(self, environ, start_response):
        if 'repoze.tm.active' in environ: #pragma: no cover
            #Skip transaction manager if repoze.tm2 is enabled
            return self.app(environ, start_response)

        transaction_manager = transaction.manager
        total_attempts = self.attempts
        commit_veto = self.commit_veto
        started_response = {}

        def _start_response(status, headers, exc_info=None):
            started_response.update(status=status, headers=headers)
            return start_response(status, headers, exc_info)

        attempts_left = total_attempts
        while attempts_left:
            attempts_left -= 1

            try:
                log.debug('Attempts Left %d (%d total)', attempts_left, total_attempts)
                transaction_manager.begin()

                if total_attempts > 1:
                    Request(environ).make_body_seekable()

                t = transaction_manager.get()
                t.note(environ.get('PATH_INFO', ''))

                response_data = self.app(environ, _start_response)
                if transaction_manager.isDoomed():
                    log.debug('Transaction doomed')
                    raise AbortTransaction(response_data)

                if commit_veto is not None:
                    veto = commit_veto(environ, started_response['status'], started_response['headers'])
                    if veto:
                        log.debug('Transaction vetoed')
                        raise AbortTransaction(response_data)

                transaction_manager.commit()
                log.debug('Transaction committed!')
                return response_data
            except AbortTransaction as e:
                transaction_manager.abort()
                return e.response_data
            except:
                exc_info = sys.exc_info()
                log.debug('Error while running request, aborting transaction')
                try:
                    can_retry = transaction_manager._retryable(*exc_info[:-1])
                    transaction_manager.abort()
                    if (attempts_left <= 0) or (not can_retry):
                        reraise(*exc_info)
                finally:
                    del exc_info

########NEW FILE########
__FILENAME__ = util
"""Utilities"""
from pkg_resources import resource_filename
import warnings
from tg.request_local import request
from functools import partial, update_wrapper


class DottedFileLocatorError(Exception):pass


def get_partial_dict(prefix, dictionary):
    """Given a dictionary and a prefix, return a Bunch, with just items
    that start with prefix

    The returned dictionary will have 'prefix.' stripped so:

    get_partial_dict('prefix', {'prefix.xyz':1, 'prefix.zyx':2, 'xy':3})

    would return:

    {'xyz':1,'zyx':2}
    """

    match = prefix + "."
    n = len(match)

    new_dict = Bunch([(key[n:], dictionary[key])
                       for key in dictionary.keys()
                       if key.startswith(match)])
    if new_dict:
        return new_dict
    else:
        raise AttributeError


class Bunch(dict):
    """A dictionary that provides attribute-style access."""

    def __getitem__(self, key):
        return  dict.__getitem__(self, key)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return get_partial_dict(name, self)

    __setattr__ = dict.__setitem__

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


class DottedFileNameFinder(object):
    """this class implements a cache system above the
    get_dotted_filename function and is designed to be stuffed
    inside the app_globals.

    It exposes a method named get_dotted_filename with the exact
    same signature as the function of the same name in this module.

    The reason is that is uses this function itself and just adds
    caching mechanism on top.
    """
    def __init__(self):
        self.__cache = dict()

    def get_dotted_filename(self, template_name, template_extension='.html'):
        """this helper function is designed to search a template or any other
        file by python module name.

        Given a string containing the file/template name passed to the @expose
        decorator we will return a resource useable as a filename even
        if the file is in fact inside a zipped egg.

        The actual implementation is a revamp of the Genshi buffet support
        plugin, but could be used with any kind a file inside a python package.

        @param template_name: the string representation of the template name
        as it has been given by the user on his @expose decorator.
        Basically this will be a string in the form of:
        "genshi:myapp.templates.somename"
        @type template_name: string

        @param template_extension: the extension we excpect the template to have,
        this MUST be the full extension as returned by the os.path.splitext
        function. This means it should contain the dot. ie: '.html'

        This argument is optional and the default value if nothing is provided will
        be '.html'
        @type template_extension: string
        """
        try:
            return self.__cache[template_name]
        except KeyError:
            # the template name was not found in our cache
            divider = template_name.rfind('.')
            if divider >= 0:
                package = template_name[:divider]
                basename = template_name[divider + 1:] + template_extension
                try:
                    result = resource_filename(package, basename)
                except ImportError as e:
                    raise DottedFileLocatorError(str(e) +". Perhaps you have forgotten an __init__.py in that folder.")
            else:
                result = template_name

            self.__cache[template_name] = result

            return result


def no_warn(f, *args, **kwargs):
    def _f(*args, **kwargs):
        warnings.simplefilter("ignore")
        f(*args, **kwargs)
        warnings.resetwarnings()
    return update_wrapper(_f, f)


class LazyString(object):
    """Has a number of lazily evaluated functions replicating a
    string. Just override the eval() method to produce the actual value.
    """
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def eval(self):
        return self.func(*self.args, **self.kwargs)

    def __unicode__(self):
        return unicode(self.eval())

    def __str__(self):
        return str(self.eval())

    def __mod__(self, other):
        return self.eval() % other

    def format(self, other):
        return self.eval().format(other)


def lazify(func):
    """Decorator to return a lazy-evaluated version of the original"""
    def newfunc(*args, **kwargs):
        return LazyString(func, *args, **kwargs)
    newfunc.__name__ = 'lazy_%s' % func.__name__
    newfunc.__doc__ = 'Lazy-evaluated version of the %s function\n\n%s' % \
        (func.__name__, func.__doc__)
    return newfunc


class ContextObj(object):
    def __repr__(self):
        attrs = sorted((name, value)
                       for name, value in self.__dict__.items()
                       if not name.startswith('_'))
        parts = []
        for name, value in attrs:
            value_repr = repr(value)
            if len(value_repr) > 70:
                value_repr = value_repr[:60] + '...' + value_repr[-5:]
            parts.append(' %s=%s' % (name, value_repr))
        return '<%s.%s at %s%s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self)),
            ','.join(parts))

    def __getattr__(self, item):
        if item in ('form_values', 'form_errors'):
            warnings.warn('tmpl_context.form_values and tmpl_context.form_errors got deprecated '
                          'use request.validation instead', DeprecationWarning)
            return request.validation[item[5:]]
        elif item == 'controller_url':
            warnings.warn('tmpl_context.controller_url got deprecated, '
                          'use request.controller_url instead', DeprecationWarning)
            return request.controller_url

        raise AttributeError()


class AttribSafeContextObj(ContextObj):
    """The :term:`tmpl_context` object, with lax attribute access (
    returns '' when the attribute does not exist)"""
    def __getattr__(self, name):
        try:
            return ContextObj.__getattr__(self, name)
        except AttributeError:
            return ''

########NEW FILE########
__FILENAME__ = validation
try:
    from tw2.core import ValidationError as _Tw2ValidationError
except ImportError: #pragma: no cover
    class _Tw2ValidationError(Exception):
        """ToscaWidgets2 Validation Error"""

try:
    from formencode.api import Invalid as _FormEncodeValidationError
    from formencode.api import Validator as _FormEncodeValidator
    from formencode import Schema as _FormEncodeSchema
except ImportError: #pragma: no cover
    class _FormEncodeValidationError(Exception):
        """FormEncode Invalid"""
    class _FormEncodeValidator(object):
        """FormEncode Validator"""
    class _FormEncodeSchema(object):
        """FormEncode Schema"""

def _navigate_tw2form_children(w):
    if getattr(w, 'compound_key', None):
        # If we have a compound_key it's a leaf widget with form values
        yield w
    else:
        child = getattr(w, 'child', None)
        if child:
            # Widgets with "child" don't have children, but their child has
            w = child

        for c in getattr(w, 'children', []):
            for cc in _navigate_tw2form_children(c):
                yield cc

class TGValidationError(Exception):
    """Invalid data was encountered during validation.

    The constructor can be passed a short message with
    the reason of the failed validation.
    """
    def __init__(self, msg, value=None, error_dict=None):
        super(TGValidationError, self).__init__(msg)
        self.msg = msg
        self.value = value
        self.error_dict = error_dict

    @classmethod
    def make_compound_message(cls, error_dict):
        return '\n'.join("%s: %s" % errorinfo for errorinfo in error_dict.items())

    def __str__(self):
        return self.msg

validation_errors = (_Tw2ValidationError, _FormEncodeValidationError, TGValidationError)

########NEW FILE########
__FILENAME__ = wsgiapp
import os, sys, logging
from webob.exc import HTTPNotFound

log = logging.getLogger(__name__)

import tg
from tg import request_local
from tg.i18n import _get_translator
from tg.request_local import Request, Response
from tg.util import ContextObj, AttribSafeContextObj

try: #pragma: no cover
    import pylons
    has_pylons = True
except:
    has_pylons = False


class RequestLocals(object):
    __slots__ = ('response', 'request', 'app_globals',
                 'config', 'tmpl_context', 'translator',
                 'session', 'cache', 'url')


class TGApp(object):
    def __init__(self, config=None, **kwargs):
        """Initialize a base WSGI application

        Given an application configuration creates the WSGI
        application for it, if no configuration is provided
        then tg.config is used.

        TGApp constructor is also in charge of actually
        initializing application wrappers.
        """
        self.config = config = config or tg.config._current_obj()
        self.globals = config.get('tg.app_globals')
        self.package_name = config['package_name']

        self.controller_classes = {}
        self.controller_instances = {}

        # Cache some options for use during requests
        self.strict_tmpl_context = self.config['tg.strict_tmpl_context']
        self.pylons_compatible = self.config.get('tg.pylons_compatible', True)
        self.enable_routes = self.config.get('enable_routes', False)

        self.resp_options = config.get('tg.response_options',
                                       dict(content_type='text/html',
                                            charset='utf-8',
                                            headers={'Cache-Control': 'no-cache',
                                                     'Pragma': 'no-cache',
                                                     'Content-Type': None,
                                                     'Content-Length': '0'}))

        self.wrapped_dispatch = self.dispatch
        for wrapper in self.config.get('application_wrappers', []):
            try:
                self.wrapped_dispatch = wrapper(self.wrapped_dispatch, self.config)
            except TypeError:
                #backward compatibility with wrappers that didn't receive the config
                self.wrapped_dispatch = wrapper(self.wrapped_dispatch)

        if 'tg.root_controller' in self.config:
            self.controller_instances['root'] = self.config['tg.root_controller']

    def setup_pylons_compatibility(self, environ, controller): #pragma: no cover
        """Updates environ to be backward compatible with Pylons"""
        try:
            environ['pylons.controller'] = controller
            environ['pylons.pylons'] = environ['tg.locals']

            self.config['pylons.app_globals'] = self.globals

            pylons.request = request_local.request
            pylons.cache = request_local.cache
            pylons.config = request_local.config
            pylons.app_globals = request_local.app_globals
            pylons.session = request_local.session
            pylons.translator = request_local.translator
            pylons.response = request_local.response
            pylons.tmpl_context = request_local.tmpl_context

            if self.enable_routes:
                environ['pylons.routes_dict'] = environ['tg.routes_dict']
                pylons.url = request_local.url
        except ImportError:
            pass

    def __call__(self, environ, start_response):
        # Hide outer middlewares when crash inside application itself
        __traceback_hide__ = 'before'

        testmode, context = self.setup_app_env(environ)

        #Expose a path that simply registers the globals and preserves them
        # without doing much else
        if testmode is True and environ['PATH_INFO'] == '/_test_vars':
            registry = environ['paste.registry']
            registry.preserve()
            start_response('200 OK', [('Content-type', 'text/plain')])
            return ['DONE'.encode('utf-8')]

        controller = self.resolve(environ, context)
        response = self.wrapped_dispatch(controller, environ, context)

        if testmode is True:
            environ['paste.testing_variables']['response'] = response

        try:
            if response is not None:
                return response(environ, start_response)

            raise Exception("No content returned by controller (Did you "
                            "remember to 'return' it?) in: %r" %
                            controller)
        finally:
            # Help Python collect ram a bit faster by removing the reference
            # cycle that the thread local objects cause
            del environ['tg.locals']
            if has_pylons and 'pylons.pylons' in environ: #pragma: no cover
                del environ['pylons.pylons']

    def setup_app_env(self, environ):
        """Setup Request, Response and TurboGears context objects.

        Is also in charge of pushing TurboGears context into the
        paste registry and detect test mode. Returns whenever
        the testmode is enabled or not and the TurboGears context.
        """
        conf = self.config

        # Setup the basic global objects
        req = Request(environ)
        req._fast_setattr('_language', conf['lang'])
        req._fast_setattr('_response_type', None)

        resp_options = self.resp_options
        response = Response(
            content_type=resp_options['content_type'],
            charset=resp_options['charset'],
            headers=resp_options['headers'])

        # Setup the translator object
        lang = conf['lang']
        translator = _get_translator(lang, tg_config=conf)

        if self.strict_tmpl_context:
            tmpl_context = ContextObj()
        else:
            tmpl_context = AttribSafeContextObj()

        app_globals = self.globals
        session = environ.get('beaker.session')
        cache = environ.get('beaker.cache')

        locals = RequestLocals()
        locals.response = response
        locals.request = req
        locals.app_globals = app_globals
        locals.config = conf
        locals.tmpl_context = tmpl_context
        locals.translator = translator
        locals.session = session
        locals.cache = cache

        if self.enable_routes: #pragma: no cover
            url = environ.get('routes.url')
            locals.url = url

        environ['tg.locals'] = locals

        #Register Global objects
        registry = environ['paste.registry']
        registry.register(request_local.config, conf)
        registry.register(request_local.context, locals)

        if 'paste.testing_variables' in environ:
            testenv = environ['paste.testing_variables']
            testenv['req'] = req
            testenv['response'] = response
            testenv['tmpl_context'] = tmpl_context
            testenv['app_globals'] = self.globals
            testenv['config'] = conf
            testenv['session'] = locals.session
            testenv['cache'] = locals.cache
            return True, locals

        return False, locals

    def resolve(self, environ, context):
        """Uses dispatching information found in
        ``environ['wsgiorg.routing_args']`` to retrieve a controller
        name and return the controller instance from the appropriate
        controller module.

        Override this to change how the controller name is found and
        returned.

        """
        if self.enable_routes: #pragma: no cover
            match = environ['wsgiorg.routing_args'][1]
            environ['tg.routes_dict'] = match
            controller = match.get('controller')
            if not controller:
                return None
        else:
            controller = 'root'

        return self.get_controller_instance(controller)

    def class_name_from_module_name(self, module_name):
        words = module_name.replace('-', '_').split('_')
        return ''.join(w.title() for w in words)

    def find_controller(self, controller):
        """Locates a controller by attempting to import it then grab
        the SomeController instance from the imported module.

        Override this to change how the controller object is found once
        the URL has been resolved.

        """
        # Check to see if we've cached the class instance for this name
        if controller in self.controller_classes:
            return self.controller_classes[controller]

        root_module_path = self.config['paths']['root']
        base_controller_path = self.config['paths']['controllers']

        #remove the part of the path we expect to be the root part (plus one '/')
        assert base_controller_path.startswith(root_module_path)
        controller_path = base_controller_path[len(root_module_path)+1:]

        #attach the package
        full_module_name = '.'.join([self.package_name] +
            controller_path.split(os.sep) + controller.split('/'))

        # Hide the traceback here if the import fails (bad syntax and such)
        __traceback_hide__ = 'before_and_this'

        __import__(full_module_name)
        module_name = controller.split('/')[-1]
        class_name = self.class_name_from_module_name(module_name) + 'Controller'
        mycontroller = getattr(sys.modules[full_module_name], class_name)

        self.controller_classes[controller] = mycontroller
        return mycontroller

    def get_controller_instance(self, controller):
        # Check to see if we've cached the instance for this name
        try:
            return self.controller_instances[controller]
        except KeyError:
            mycontroller = self.find_controller(controller)

            # If it's a class, instantiate it
            if hasattr(mycontroller, '__bases__'):
                mycontroller = mycontroller()

            self.controller_instances[controller] = mycontroller
            return mycontroller

    def dispatch(self, controller, environ, context):
        """Dispatches to a controller, the controller itself is expected
        to implement the routing system.

        Override this to change how requests are dispatched to controllers.
        """
        if not controller:
            return HTTPNotFound()

        #Setup pylons compatibility before calling controller
        if has_pylons and self.pylons_compatible: #pragma: no cover
            self.setup_pylons_compatibility(environ, controller)

        # Controller is assumed to handle a WSGI call
        return controller(environ, context)

########NEW FILE########
__FILENAME__ = _compat
import platform, sys

if platform.system() == 'Windows': # pragma: no cover
    WIN = True
else: # pragma: no cover
    WIN = False

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_type = str
    unicode_text = str
    byte_string = bytes
    from urllib.parse import urlencode as url_encode
    from urllib.parse import quote as url_quote
    from urllib.parse import unquote as url_unquote
    from urllib.request import url2pathname

    def u_(s):
        return str(s)

    def bytes_(s):
        return str(s).encode('ascii', 'strict')
else:
    string_type = basestring
    unicode_text = unicode
    byte_string = str
    from urllib import urlencode as url_encode
    from urllib import quote as url_quote
    from urllib import unquote as url_unquote
    from urllib import url2pathname

    def u_(s):
        return unicode(s, 'utf-8')

    def bytes_(s):
        return str(s)

def im_func(f):
    if PY3: # pragma: no cover
        return getattr(f, '__func__', None)
    else:
        return getattr(f, 'im_func', None)

def default_im_func(f):
    if PY3: # pragma: no cover
        return getattr(f, '__func__', f)
    else:
        return getattr(f, 'im_func', f)

def im_self(f):
    if PY3: # pragma: no cover
        return getattr(f, '__self__', None)
    else:
        return getattr(f, 'im_self', None)

def im_class(f):
    if PY3: # pragma: no cover
        self = im_self(f)
        if self is not None:
            return self.__class__
        else:
            return None
    else:
        return getattr(f, 'im_class', None)

def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})

if PY3: # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else: # pragma: no cover
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

########NEW FILE########
