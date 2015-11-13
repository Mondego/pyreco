__FILENAME__ = handlers
# coding: utf-8
from tornado.web import asynchronous
from torneira import __version__
from torneira.handler import TorneiraHandler
from torneira.template import MakoMixin


class MainHandler(TorneiraHandler, MakoMixin):
    def index(self):
        return self.render_to_template('index.html')

    def simple(self):
        return "You can use self.write or just returns the contents"

    def as_json(self):
        return {'json_response': [1, 2, 3]}

    @asynchronous
    def async(self):
        context = {'version': __version__}
        content = self.render_to_template('async.html', **context)
        self.write(content)
        self.finish()

########NEW FILE########
__FILENAME__ = settings
import os
from functools import partial


ROOT_URLS = 'more_complex_app.urls'
DEBUG = True

join = partial(os.path.join, os.path.dirname(__file__))

TEMPLATE_DIRS = (
    join('templates'),
)

########NEW FILE########
__FILENAME__ = urls
# coding: utf-8
from tornado.web import url

from more_complex_app.handlers import MainHandler


urls = (
    url(r'/', MainHandler, {'action': 'index'}),
    url(r'/simple', MainHandler, {'action': 'simple'}),
    url(r'/json', MainHandler, {'action': 'as_json'}),
    url(r'/async', MainHandler, {'action': 'async'}),
)

########NEW FILE########
__FILENAME__ = handlers
# coding: utf-8
from torneira import __version__
from torneira.handler import TorneiraHandler


class MainHandler(TorneiraHandler):
    def index(self):
        return "You are running Torneira v%s" % __version__

########NEW FILE########
__FILENAME__ = settings
ROOT_URLS = 'simple_app.urls'
DEBUG = True

########NEW FILE########
__FILENAME__ = urls
# coding: utf-8
from tornado.web import url

from simple_app.handlers import MainHandler


urls = (
    url(r'/', MainHandler, {'action': 'index'}),
)

########NEW FILE########
__FILENAME__ = test_util
# coding: utf-8
from torneira.cache.util import cache_key

from tests.util import unittest


class MySimpleObject(object):
    def do_something(self, a, b):
        return a + b


class MyModel(object):
    id = None

    def __init__(self, id_):
        self.id = id_

    def do_something(self, a, b):
        return a + b


class ObjectWithSpecialMethod(object):
    # just to ensure that cache_key will not use this value
    id = 'should-not-be-used'
    _my_value = None

    def __init__(self, value):
        self._my_value = value

    def get_cache_key(self):
        return self._my_value

    def do_something(a, b):
        return a + b


class GenerateCacheKeyTestCase(unittest.TestCase):
    def test_generate_cache_key_for_simple_object(self):
        my_instance = MySimpleObject()

        fn_kwargs = {'a': 1, 'b': 2}
        _, generated_key = cache_key(my_instance, 'do_something', **fn_kwargs)
        expected_key = 'tests.cache.test_util.MySimpleObject().do_something(a=1,b=2)'

        self.assertEqual(generated_key, expected_key)

    def test_generate_cache_key_for_model_object(self):
        my_instance = MyModel("unique-id-1")

        fn_kwargs = {'a': 1, 'b': 2}
        _, generated_key = cache_key(my_instance, 'do_something', **fn_kwargs)
        expected_key = 'tests.cache.test_util.MyModel(unique-id-1).do_something(a=1,b=2)'

        self.assertEqual(generated_key, expected_key)

    def test_generate_cache_key_for_object_with_special_method(self):
        my_instance = ObjectWithSpecialMethod('unique-value')

        fn_kwargs = {'a': 1, 'b': 2}
        _, generated_key = cache_key(my_instance, 'do_something', **fn_kwargs)
        expected_key = 'tests.cache.test_util.ObjectWithSpecialMethod(unique-value).do_something(a=1,b=2)'

        self.assertEqual(generated_key, expected_key)

########NEW FILE########
__FILENAME__ = test_base
# -*- coding: utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import with_statement
import urllib

import fudge
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, url

from torneira.controller import BaseController, render_to_extension
from tests.util import unittest

try:
    # Python >= 2.6
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

# simplexml module is optional
try:
    import simplexml
except ImportError:
    simplexml = None

try:
    import json
except ImportError:
    import simplejson as json


class SimpleController(BaseController):
    def index(self, *args, **kwargs):
        if 'request_handler' in kwargs:
            response = 'request_handler received'
        else:
            response = 'request_handler not received'
        return response

    def post_data(self, request_handler, *args, **kwargs):
        response = []
        for key, value in kwargs.iteritems():
            if type(value) == list:
                for v in value:
                    response.append((key, v))
            else:
                response.append((key, value))
        return urllib.urlencode(response)

    def render_json(self, request_handler, *args, **kwargs):
        response = [
            {'a': 1},
            {'b': 2},
        ]
        return self.render_to_json(response, request_handler)

    def render_xml(self, request_handler, *args, **kwargs):
        response = {
            'root': {
                'a': 1,
                'b': 2,
            }
        }
        return self.render_to_xml(response, request_handler)

    def render_response_error(self, request_handler, *args, **kwargs):
        message = 'error!'
        return self.render_error(message)

    def render_response_success(self, request_handler, *args, **kwargs):
        message = 'success!'
        return self.render_success(message)

    @render_to_extension
    def render_to_extension_with_decorator(self, request_handler, *args, **kwargs):
        return {'root': {'key': 'value'}}


urls = (
    url(r'/controller/simple/', SimpleController, {'action': 'index'}),
    url(r'/controller/post-data/', SimpleController, {'action': 'post_data'}),
    url(r'/controller/render-json/', SimpleController, {'action': 'render_json'}),
    url(r'/controller/render-xml/', SimpleController, {'action': 'render_xml'}),
    url(r'/controller/render-error/', SimpleController, {'action': 'render_response_error'}),
    url(r'/controller/render-success/', SimpleController, {'action': 'render_response_success'}),
    url(r'/controller/render-to-extension\.(?P<extension>[a-z]*)', SimpleController, {'action': 'render_to_extension_with_decorator'}),
)
app = Application(urls, cookie_secret='secret')


class BaseControllerTestCase(AsyncHTTPTestCase, unittest.TestCase):
    def get_app(self):
        return app

    def test_controller_method_must_receive_request_handler_as_kwarg(self):
        response = self.fetch('/controller/simple/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'request_handler received')

    def test_post_data_should_be_received_in_kwargs(self):
        post_data = (
            ('a_list', 1),
            ('a_list', 2),
            ('a_list', 3),
            ('single_value', 'value'),
            ('another_single_value', 'value 2'),
        )
        post_body = urllib.urlencode(post_data)
        response = self.fetch('/controller/post-data/', method='POST', body=post_body)
        self.assertEqual(response.code, 200)
        self.assertEqual(parse_qs(response.body), parse_qs(post_body))

    def test_render_to_json_should_return_json_response(self):
        response = self.fetch('/controller/render-json/')
        self.assertTrue('Content-Type' in response.headers)
        self.assertEqual(response.headers['Content-Type'], 'application/json; charset=UTF-8')
        self.assertEqual(response.code, 200)

        expected = [
            {'a': 1},
            {'b': 2},
        ]
        parsed_response = json.loads(response.body)
        self.assertEqual(parsed_response, expected)

    @unittest.skipUnless(simplexml, "simplexml module not installed")
    def test_render_to_xml_should_return_xml_response(self):
        response = self.fetch('/controller/render-xml/')
        self.assertTrue('Content-Type' in response.headers)
        self.assertEqual(response.headers['Content-Type'], 'text/xml; charset=UTF-8')
        self.assertEqual(response.code, 200)

        expected = {
            'root': {
                'a': '1',
                'b': '2',
            }
        }
        parsed_response = simplexml.loads(response.body)
        self.assertEqual(parsed_response, expected)

    def test_render_response_error_should_return_preformatted_json(self):
        response = self.fetch('/controller/render-error/')
        self.assertTrue('Content-Type' in response.headers)
        self.assertEqual(response.headers['Content-Type'], 'application/json; charset=UTF-8')
        self.assertEqual(response.code, 200)

        expected = {
            'errors': {
                'error': {
                    'message': 'error!'
                }
            }
        }
        parsed_response = json.loads(response.body)
        self.assertEqual(parsed_response, expected)

    def test_render_response_success_should_return_preformatted_json(self):
        response = self.fetch('/controller/render-success/')
        self.assertTrue('Content-Type' in response.headers)
        self.assertEqual(response.headers['Content-Type'], 'application/json; charset=UTF-8')
        self.assertEqual(response.code, 200)

        expected = {
            'errors': '',
            'message': 'success!'
        }
        parsed_response = json.loads(response.body)
        self.assertEqual(parsed_response, expected)

    @fudge.patch('torneira.controller.base.locale',
                 'torneira.controller.base.settings')
    def test_if_can_setup_tornado_locale_module(self, locale, settings):
        LOCALE = {
            'code': 'pt_BR',
            'path': 'locales/',
            'domain': 'appname',
        }
        settings.has_attr(LOCALE=LOCALE)

        (locale
            .is_a_stub()
            .expects('set_default_locale')
            .with_args('pt_BR')
            .expects('load_gettext_translations')
            .with_args('locales/', 'appname'))

        response = self.fetch('/controller/simple/')
        self.assertEqual(response.code, 200)

    @fudge.patch('torneira.controller.base.settings')
    def test_raise_assertexception_if_settings_locale_was_not_configured(self, settings):
        settings.has_attr(LOCALE={})

        with self.assertRaises(AssertionError):
            self.fetch('/controller/simple/')


class RenderToExtensionDecoratorTestCase(AsyncHTTPTestCase):
    EXPECTED_RESPONSE = {'root': {'key': 'value'}}

    def get_app(self):
        return app

    def test_render_response_without_specifying_extension_should_return_json(self):
        response = self.fetch('/controller/render-to-extension.')
        self.assertTrue('Content-Type' in response.headers)
        self.assertEqual(response.headers['Content-Type'], 'application/json; charset=UTF-8')
        self.assertEqual(response.code, 200)
        parsed_response = json.loads(response.body)
        self.assertEqual(parsed_response, self.EXPECTED_RESPONSE)

    def test_render_response_as_json(self):
        response = self.fetch('/controller/render-to-extension.json')
        self.assertTrue('Content-Type' in response.headers)
        self.assertEqual(response.headers['Content-Type'], 'application/json; charset=UTF-8')
        self.assertEqual(response.code, 200)
        parsed_response = json.loads(response.body)
        self.assertEqual(parsed_response, self.EXPECTED_RESPONSE)

    def test_render_response_as_jsonp(self):
        response = self.fetch('/controller/render-to-extension.jsonp?callback=cb')
        self.assertTrue('Content-Type' in response.headers)
        self.assertEqual(response.headers['Content-Type'], 'application/javascript; charset=UTF-8')
        self.assertEqual(response.code, 200)
        expected_response = "cb(%s);" % json.dumps(self.EXPECTED_RESPONSE)
        self.assertEqual(response.body, expected_response)

    @unittest.skipUnless(simplexml, "simplexml module not installed")
    def test_render_response_as_xml(self):
        response = self.fetch('/controller/render-to-extension.xml')
        self.assertTrue('Content-Type' in response.headers)
        self.assertEqual(response.headers['Content-Type'], 'text/xml; charset=UTF-8')
        self.assertEqual(response.code, 200)
        parsed_response = simplexml.loads(response.body)
        self.assertEqual(parsed_response, self.EXPECTED_RESPONSE)

########NEW FILE########
__FILENAME__ = test_dispatcher
# -*- coding: utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase
from torneira.controller import BaseController
from torneira.core.dispatcher import url


class SimpleController(BaseController):
    def index(self, *args, **kwargs):
        return 'index ok'

    def with_parameter(self, param, request_handler):
        return "action_with_parameter " + param

    def preserve_url_name(self, request_handler):
        return request_handler.reverse_url('name-of-url')


urls = (
    url('/controller/simple/', SimpleController, action='index', name='index'),
    url('/controller/parameter/{param}', SimpleController, action='with_parameter', name='with_parameter'),
    url('/controller/preserve-name/', SimpleController, action='preserve_url_name', name='name-of-url'),
)
app = Application(urls, cookie_secret='secret')


class DispatcherTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return app

    def test_use_routes_for_map_a_simple_url(self):
        response = self.fetch('/controller/simple/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'index ok')

    def test_use_routes_for_map_a_url_with_parameter(self):
        response = self.fetch('/controller/parameter/shouldBeParam')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'action_with_parameter shouldBeParam')

    def test_use_routes_for_mapping_urls_should_preserve_the_name_of_url(self):
        response = self.fetch('/controller/preserve-name/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, r'/controller/preserve-name/')

########NEW FILE########
__FILENAME__ = test_meta
# -*- coding: utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest, fudge

from torneira import settings
from torneira.core import meta

class TimerProxyTestCase(unittest.TestCase):
            
    def test_timer_proxy_debug_true(self):
        
        settings.DEBUG = True

        fudge.clear_expectations()
        fudge.clear_calls()
        
        execute_fake = fudge.Fake(callable=True).with_args("shouldBeCursor", "shouldBeStatement", "shouldBeParameters", "shouldBeContext")        
        
        timerProxy = meta.TimerProxy()
        timerProxy.cursor_execute(execute_fake, "shouldBeCursor", "shouldBeStatement", "shouldBeParameters", "shouldBeContext", "shouldBeExecutemany")
        
        fudge.verify()

    @fudge.test
    def test_timer_proxy_debug_false(self):

        settings.DEBUG = False

        execute_fake = fudge.Fake(callable=True).with_args("shouldBeCursor", "shouldBeStatement", "shouldBeParameters", "shouldBeContext")        

        timerProxy = meta.TimerProxy()
        timerProxy.cursor_execute(execute_fake, "shouldBeCursor", "shouldBeStatement", "shouldBeParameters", "shouldBeContext", "shouldBeExecutemany")

class SessionTestCase(unittest.TestCase):
    @fudge.test
    def test_can_be_get_session(self):
        settings.DATABASE_ENGINE = "shouldBeDataBase"
        settings.DATABASE_POOL_SIZE = "shouldBePoolSize"
        
        FakeTimerProxy = fudge.Fake("TimerProxy").expects("__init__")
        timer_proxy_instance = FakeTimerProxy.returns_fake()

        create_engine_fake = fudge.Fake(callable=True).with_args("shouldBeDataBase", 
            pool_size="shouldBePoolSize", 
            pool_recycle=300, 
            proxy=timer_proxy_instance
        ).returns("shouldBeEngine")
        
        sessionmaker_fake = fudge.Fake(callable=True).with_args(autocommit=True, 
            autoflush=False, 
            expire_on_commit=False, 
            bind="shouldBeEngine"
        ).returns("shouldBeScopedSession")

        scoped_session_fake = fudge.Fake(callable=True).with_args("shouldBeScopedSession").returns("shouldBeSession")

        patches = [
            fudge.patch_object(meta, "TimerProxy", FakeTimerProxy),
            fudge.patch_object(meta, "create_engine", create_engine_fake),
            fudge.patch_object(meta, "sessionmaker", sessionmaker_fake),
            fudge.patch_object(meta, "scoped_session", scoped_session_fake)
        ]

        try:
            session = meta.TorneiraSession()
            self.assertEqual(session, "shouldBeSession")
        finally:
            
            for p in patches:
                p.restore()

########NEW FILE########
__FILENAME__ = test_server
# coding: utf-8
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from fudge import patch
from fudge.inspector import arg
from tornado.testing import AsyncTestCase

from torneira.core import server

urls = ()


class RunServerTestCase(AsyncTestCase):
    @patch('torneira.core.server.settings',
           'torneira.core.server.IOLoop',
           'torneira.core.server.Application')
    def test_run_server_should_pass_xheaders_to_correct_method(self, settings, IOLoop, Application):
        settings.has_attr(ROOT_URLS='tests.core.test_server')
        PORT = 1234
        XHEADERS = True

        # Just to prevent the test from hanging
        IOLoop.is_a_stub()

        (Application
            .is_callable()
            .with_args(arg.any(), cookie_secret=None, debug=False)
            .returns_fake()
            .expects('listen')
            .with_args(PORT, xheaders=XHEADERS))

        torneira_server = server.TorneiraServer(PORT, '/my_media/', XHEADERS)
        torneira_server.run()

########NEW FILE########
__FILENAME__ = test_handler
# coding: utf-8
import os

import fudge
from tornado.web import Application, url
from tornado.testing import AsyncHTTPTestCase

from torneira.handler import TorneiraHandler
from torneira.template.mako_engine import MakoMixin


class SimpleHandler(TorneiraHandler):
    def index(self):
        self.write("output from simple handler")

    def another_action(self):
        self.write("output from another action")

    def action_returns_something(self):
        return 'returned output'

    def put(self):
        self.write("output from put method")


class MakoTemplateHandler(TorneiraHandler, MakoMixin):
    def index(self):
        context = {
            'variable_name': 'variable value',
        }
        return self.render_to_template('template.html', **context)

    def unknown_template(self):
        self.render_to_template('unknown-template.html')


urls = (
    url(r'/simple/', SimpleHandler, {'action': 'index'}),
    url(r'/without-action/', SimpleHandler),
    url(r'/another-action/', SimpleHandler, {'action': 'another_action'}),
    url(r'/should-return-something/', SimpleHandler, {'action': 'action_returns_something'}),
    url(r'/mako-mixin/', MakoTemplateHandler, {'action': 'index'}),
    url(r'/mako-mixin/unknown-template/', MakoTemplateHandler, {'action': 'unknown_template'}),
)
app = Application(urls, cookie_secret='secret')
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')


class TorneiraHandlerTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return app

    def test_make_get_request_should_call_correct_action(self):
        response = self.fetch('/simple/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'output from simple handler')

    def test_make_get_request_without_action_and_custom_get_should_return_500(self):
        response = self.fetch('/without-action/')
        self.assertEqual(response.code, 500)

    def test_make_get_request_to_another_url_should_call_correct_action(self):
        response = self.fetch('/another-action/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'output from another action')

    def test_make_request_to_action_should_write_returned_content_to_server_output(self):
        response = self.fetch('/should-return-something/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'returned output')

    def test_make_post_request_should_call_correct_action(self):
        response = self.fetch('/simple/', method='POST', body='key=value')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'output from simple handler')

    def test_make_put_request_should_call_default_put_method_from_tornado(self):
        response = self.fetch('/without-action/', method='PUT', body='key=value')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'output from put method')


class MakoTemplateHandlerTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return app

    def test_make_request_without_template_dirs_settings_should_return_500(self):
        response = self.fetch('/mako-mixin/')
        self.assertEqual(response.code, 500)

    @fudge.patch('torneira.template.mako_engine.settings')
    def test_make_request_for_unknown_template_should_return_500(self, settings):
        settings.has_attr(TEMPLATE_DIRS=(ASSETS_DIR,))
        response = self.fetch('/mako-mixin/unknown-template/')
        self.assertEqual(response.code, 500)

    @fudge.patch('torneira.template.mako_engine.settings')
    def test_make_request_should_render_template_with_params(self, settings):
        settings.has_attr(TEMPLATE_DIRS=(ASSETS_DIR,))
        response = self.fetch('/mako-mixin/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, u'template text em português (variable value)\n'.encode('utf-8'))


class ProfilerHandlerTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return app

    @fudge.patch('torneira.handler.settings',
                 'torneira.handler.Profile')
    def test_enable_profile_request_should_call_profile_class(self, settings, Profile):
        settings.has_attr(PROFILING=True, PROFILE_FILE='profile_filename.out')

        (Profile
            .is_callable()
            .returns_fake()
            .expects('runcall')
            .calls(lambda method, *a, **kw: method(*a, **kw))
            .expects('dump_stats')
            .with_args('profile_filename.out'))

        response = self.fetch('/simple/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'output from simple handler')

########NEW FILE########
__FILENAME__ = util
## copied from tornado source code:

import sys

# Encapsulate the choice of unittest or unittest2 here.
# To be used as 'from tests.util import unittest'.
if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

########NEW FILE########
__FILENAME__ = backend
# -*- coding: utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
import pickle

from torneira.helper.encoding import smart_unicode, smart_str

import memcache


class MemcachedClass():

    def __init__(self, server, timeout):
        self.server = server
        self.default_timeout = int(timeout)
        self._cache = memcache.Client(self.server)
        logging.debug("Memcached start client %s" % server)

    def add(self, key, value, timeout=0):
        if isinstance(value, unicode):
            value = value.encode('utf-8')

        try:
            return self._cache.add(smart_str(key), value, timeout or self.default_timeout)
        except:
            logging.exception("memcache server desligado!")

    def get(self, key, default=None):
        try:
            val = self._cache.get(smart_str(key))
            if val is None:
                return default
            else:
                if isinstance(val, basestring):
                    return smart_unicode(val)
                else:
                    return val
        except:
            logging.exception("memcache server desligado!")
            return None

    def set(self, key, value, timeout=0):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        self._cache.set(smart_str(key), value, timeout or self.default_timeout)

    def delete(self, key):
        self._cache.delete(smart_str(key))

    def get_many(self, keys):
        return self._cache.get_multi(map(smart_str, keys))

    def close(self, **kwargs):
        self._cache.disconnect_all()

    def stats(self):
        try:
            return self._cache.get_stats()
        except Exception:
            logging.exception("memcache server desligado!")

    def flush_all(self):
        try:
            self._cache.flush_all()
        except Exception:
            logging.exception("memcache server desligado!")


class RedisClass():
    def __init__(self, master, slave, timeout):
        import redis

        host_master, port_master = master.split(':')
        self._cache_master = redis.Redis(host=host_master, port=int(port_master), db=0)
        host_slave, port_slave = slave.split(':')
        self._cache_slave = redis.Redis(host=host_slave, port=int(port_slave), db=0)
        self.default_timeout = int(timeout)

        logging.debug("Redis master start client %s" % master)
        logging.debug("Redis slave start client %s" % slave)

    def add(self, key, value, timeout=0):
        try:
            val = self._cache_master.getset(smart_str(key), pickle.dumps(value))
            self._cache_master.expire(smart_str(key), timeout or self.default_timeout)
            return val
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)

    def get(self, key, default=None):
        try:
            val = self._cache_slave.get(smart_str(key))
            if val is None:
                return default
            else:
                return pickle.loads(val)
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)

    def set(self, key, value, timeout=0):
        try:
            self._cache_master.set(smart_str(key), pickle.dumps(value))
            self._cache_master.expire(smart_str(key), timeout or self.default_timeout)
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)

    def delete(self, key):
        try:
            self._cache_master.delete(smart_str(key))
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)

    def get_many(self, keys):
        try:
            return self._cache_slave.get_multi(map(smart_str, keys))
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)

    def close(self, **kwargs):
        try:
            self._cache_master.disconnect_all()
            self._cache_slave.disconnect_all()
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)

    def stats(self, server='slave'):
        try:
            if server == 'master':
                return self._cache_master.info()
            else:
                return self._cache_slave.info()
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)

    def flush_all(self):
        self._cache.flushdb()

    def stats_master(self):
        try:
            return self._cache_master.info()
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)

    def stats_slave(self):
        try:
            return self._cache_slave.info()
        except redis.ConnectionError, e:
            logging.exception("ConnectionError %s" % e)


class DummyClass():
    def add(self, key, value, timeout=0):
        pass

    def get(self, key, default=None):
        return None

    def set(self, key, value, timeout=0):
        pass

    def delete(self, key):
        pass

    def get_many(self, keys):
        pass

    def close(self, **kwargs):
        pass

    def flush_all(self):
        pass

########NEW FILE########
__FILENAME__ = extension
# -*- coding: utf-8 -*-
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import re
import logging
import hashlib

from sqlalchemy.orm.query import Query
from sqlalchemy.orm import attributes, MapperExtension, EXT_CONTINUE, EXT_STOP
from sqlalchemy.orm.session import Session

from torneira import settings
from torneira.cache.util import get_cache, cache_key


class CachedQuery(Query):
    @staticmethod
    def generate_key(obj, id):
        if type(id) == list:
            id = id[0]

        key_cache = "%s.%s(%s)" % (obj.__module__, obj.__name__, id)
        logging.debug("CachedQuery -> generate key %s" % key_cache)
        return hashlib.md5(key_cache).hexdigest(), key_cache

    def get(self, ident, **kw):
        mapper = self._mapper_zero()
        session = self.session
        cache = get_cache()

        try:
            ident = long(ident)
        except TypeError:
            if type(ident) in (tuple, list):
                ident = long(ident[0])

        key = mapper.identity_key_from_primary_key([ident])

        cacheobj = session.identity_map.get(key)
        if cacheobj and hasattr(cacheobj, "__no_session__") and cacheobj.__no_session__:
            session.expunge(cacheobj)
            cacheobj = None

        cache_key, keystr = CachedQuery.generate_key(key[0], ident)

        if not cacheobj:
            if not (hasattr(key[0], "__no_cache__") and key[0].__no_cache__):
                cacheobj = cache.get(cache_key)

            if cacheobj is not None:
                logging.debug("CachedQuery [CACHE] -> recuperando do cache e setando na sessao")
                cacheobj.__dict__["_sa_instance_state"] = attributes.instance_state(cacheobj)
                session.add(cacheobj)
            else:
                logging.debug("CachedQuery [BANCO] -> nao existe no cache, pega do banco %s" % keystr)
                cacheobj = super(CachedQuery, self).get(ident)
                if cacheobj is None:
                    return None
                logging.debug("CachedQuery [CACHE] -> setando no cache %s" % cacheobj)
                cache.set(cache_key, cacheobj)
        else:
            logging.debug("CachedQuery [SESSION] -> recuperando da sessao ")

        return cacheobj


class CachedExtension(MapperExtension):
    def get_key_from_mapper(self, mapper, instance):
        mapperkey = mapper.identity_key_from_instance(instance)
        key = "%s.%s(%s)" % (mapperkey[0].__module__, mapperkey[0].__name__, int(mapperkey[1][0]))
        md5key = hashlib.md5(key).hexdigest()
        return md5key, key

    def prepare_parameters(self, instance, params):
        result = {}

        if params != '':
            for param in params.split(","):
                arg = param.split("=")
                value = instance
                for attr in arg[1].split("."):
                    value = getattr(value, attr)
                result[arg[0].strip()] = value
        return result

    def load_model(self, module, classe):
        mod = __import__("%s.%s" % (settings.CACHED_QUERY_MODELS, module), fromlist=[classe])
        return getattr(mod, classe)()

    def get_key_from_expires(self, instance, expire):
        match = re.search("(?P<module>\w+)\.(?P<method>[^\(]+)\((?P<params>[^\)]*)\)", expire)
        if match:
            result = match.groupdict()
            expire_instance = self.load_model(result['module'].lower(), result['module'])
            kwarguments = self.prepare_parameters(instance, result['params'])
            return cache_key(expire_instance, result['method'], **kwarguments)
        return None

    def get_expires(self, instance, action):
        if hasattr(instance, "__expires__"):
            expires = instance.__expires__.get(action)
            if expires:
                return expires
        return []

    def after_insert(self, mapper, connection, instance):
        cache = get_cache()
        expires = self.get_expires(instance, "create")
        for expire in expires:
            md5key, key = self.get_key_from_expires(instance, expire)
            logging.debug("Invalidando chave[%s] no cache on insert [%s]" % (key, instance))
            cache.delete(md5key)
        return EXT_CONTINUE

    def after_update(self, mapper, connection, instance):
        if not Session.object_session(instance).is_modified(instance, include_collections=False, passive=True):
            return EXT_STOP

        cache = get_cache()
        expires = self.get_expires(instance, "update")
        for expire in expires:
            md5key, key = self.get_key_from_expires(instance, expire)
            logging.debug("Invalidando chave[%s] no cache on update [%s]" % (key, instance))
            cache.delete(md5key)

        # espira a instancia
        md5key, key = self.get_key_from_mapper(mapper, instance)
        logging.debug("Invalidando chave[%s] no cache on update [%s]" % (key, instance))
        cache.delete(md5key)

        return EXT_CONTINUE

    def after_delete(self, mapper, connection, instance):
        cache = get_cache()
        expires = self.get_expires(instance, "delete")
        for expire in expires:
            md5key, key = self.get_key_from_expires(instance, expire)
            logging.debug("Invalidando chave[%s] no cache on delete [%s]" % (key, instance))
            cache.delete(md5key)

        # espira a instancia
        md5key, key = self.get_key_from_mapper(mapper, instance)
        logging.debug("Invalidando chave[%s] no cache on delete [%s]" % (key, instance))
        cache.delete(md5key)

        return EXT_CONTINUE

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import functools
import inspect
import logging
import hashlib

from tornado import gen

from torneira.cache.backend import MemcachedClass, DummyClass, RedisClass
from torneira import settings

__cache__ = None


def get_cache():
    global __cache__
    if not __cache__:
        if settings.CACHE_BACKEND == "memcached":
            servers = settings.CACHE_BACKEND_OPTS[settings.CACHE_BACKEND]
            __cache__ = MemcachedClass(servers, settings.CACHE_TIMEOUT)
        elif settings.CACHE_BACKEND == "redis":
            master = settings.CACHE_BACKEND_OPTS[settings.CACHE_BACKEND]["master"]
            slave = settings.CACHE_BACKEND_OPTS[settings.CACHE_BACKEND]["slave"]
            __cache__ = RedisClass(master, slave, settings.CACHE_TIMEOUT)
        else:
            __cache__ = DummyClass()
    return __cache__


def cache_key(instance, method, **kwarguments):
    cachekey = "{module}.{classe}({instanceid}).{method}({params})"

    cachekey = cachekey.replace("{module}", instance.__module__)
    cachekey = cachekey.replace("{classe}", instance.__class__.__name__)
    cachekey = cachekey.replace("{method}", method)

    if hasattr(instance, "get_cache_key"):
        cachekey = cachekey.replace("{instanceid}", str(instance.get_cache_key()))
    elif hasattr(instance, "id") and instance.id:
        cachekey = cachekey.replace("{instanceid}", "%s" % instance.id)
    else:
        cachekey = cachekey.replace("{instanceid}", "")

    params = {}

    argspected = inspect.getargspec(getattr(instance, method))
    for arg in argspected[0]:
        if arg != 'self':
            params[arg] = ""

    for name, value in kwarguments.iteritems():
        if value:
            params[name] = value.replace(' ', '') if isinstance(value, str) else value

    keys = params.keys()
    keys.sort()

    cachekey = cachekey.replace("{params}", ",".join(["%s=%s" % (key, params[key]) for key in keys]))
    md5key = hashlib.md5(cachekey).hexdigest()

    return md5key, cachekey


def cached_method(fn, *arguments, **kwarguments):
    if len(arguments) == 0:
        raise ValueError("Somente metodods de instancia podem ser cacheados")

    md5key, key = cache_key(arguments[0], fn.__name__, **kwarguments)

    logging.debug("verificando chave %s no cache no formato md5 %s  " % (key, md5key))
    cache = get_cache()
    result = cache.get(md5key)

    if result is None:
        result = fn(*arguments, **kwarguments)
        if hasattr(fn, 'timeout'):
            cache.set(md5key, result, fn.timeout)
        else:
            cache.set(md5key, result)

        logging.debug("SET IN CACHE %s" % result)
    else:
        logging.debug("GET FROM CACHE")
    return result


def cached(fn):
    @functools.wraps(fn)
    def cached_static_fn(*args, **kw):
        return cached_method(fn, *args, **kw)
    return cached_static_fn


def cached_timeout(timeout):
    def cached(fn):
        @functools.wraps(fn)
        def cached_static_fn(*arguments, **kwarguments):
            fn.timeout = timeout
            return cached_method(fn, *arguments, **kwarguments)
        return cached_static_fn
    return cached


def async_cached(timeout=None):
    def async_inner(fn):
        @functools.wraps(fn)
        @gen.engine
        def wrapper(self, *args, **kwargs):
            assert 'callback' in kwargs, "Functions decorated with async_cached must have an callback argument"
            callback = kwargs['callback']
            del kwargs['callback']

            md5key, key = cache_key(self, fn.__name__, **kwargs)
            logging.debug("verificando chave %s no cache no formato md5 %s  " % (key, md5key))

            cache = get_cache()
            result = cache.get(md5key)

            if result is not None:
                logging.debug("GET FROM CACHE")
            else:
                result = yield gen.Task(fn, self, *args, **kwargs)
                cache.set(md5key, result, timeout)
                logging.debug("SET IN CACHE %s" % result)

            callback(result)
        return wrapper
    return async_inner


def expire_key(method, **kw):
    '''
    expire decorated method from cache
    '''
    if method.__name__ not in ('cached_static_fn', 'async_cached_wrapper', 'cached'):
        raise ValueError("Somente metodos decorados com cached, podes ser expirados")

    md5key, key = cache_key(method.im_self or method.im_class(), method.fn.__name__, **kw)

    cache = get_cache()
    logging.debug("[CACHE][expire] - %s {%s}" % (md5key, key))

    cache.delete(md5key)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools

from tornado import locale
from torneira import settings
from torneira.handler import TorneiraHandler
from torneira.template import MakoMixin

try:
    import json
except ImportError:
    import simplejson as json

# simplexml is optional
try:
    import simplexml
except ImportError:
    simplexml = None

class BaseController(TorneiraHandler, MakoMixin):
    def initialize(self, *args, **kwargs):
        super(BaseController, self).initialize(*args, **kwargs)
        self.setup_locale()

    def _process_request(self, *args, **kwargs):
        kwargs['request_handler'] = self
        super(BaseController, self)._process_request(*args, **kwargs)

    def _prepare_arguments_for_kwargs(self):
        # There is a bug in this design: if only one argument is received, we
        # don't know if this needs to be a list or a single value. This
        # implementation assumes that you will want a single value, for
        # compatibility.
        arguments = {}
        for key in self.request.arguments.iterkeys():
            values = self.get_arguments(key)
            arguments[key] = values[0] if len(values) == 1 else values

        return arguments

    def get(self, *args, **kwargs):
        kwargs.update(self._prepare_arguments_for_kwargs())
        super(BaseController, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs.update(self._prepare_arguments_for_kwargs())
        super(BaseController, self).post(*args, **kwargs)

    def render_to_json(self, data, request_handler=None, **kwargs):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        return json.dumps(data)

    def render_to_xml(self, data, request_handler=None, **kw):
        assert simplexml, "Module simplexml needs to be installed to use this method"
        self.set_header("Content-Type", "text/xml; charset=UTF-8")
        return simplexml.dumps(data)

    def render_error(self, message="Ops! Ocorreu um erro!", **kw):
        return self.render_to_json({"errors": {"error": {"message": message}}}, **kw)

    def render_success(self, message="Operação realizada com sucesso!", **kw):
        return self.render_to_json({"errors": "", "message": message}, **kw)

    def define_current_locale(self, locale_code):
        self._current_locale = locale.get(locale_code)

    def setup_locale(self):
        if not hasattr(settings, 'LOCALE'):
            return

        assert 'code' in settings.LOCALE
        assert 'path' in settings.LOCALE
        assert 'domain' in settings.LOCALE

        locale_code = settings.LOCALE['code']
        locale.set_default_locale(locale_code)
        locale.load_gettext_translations(settings.LOCALE['path'],
                                         settings.LOCALE['domain'])
        self.define_current_locale(locale_code)

    def get_translate(self):
        if not self._current_locale:
            return lambda s: s
        else:
            return self._current_locale.translate


def render_to_extension(fn):
    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        response = fn(self, *args, **kwargs)

        extension = kwargs.get('extension')
        if not extension:
            return response

        if extension == 'json':
            return self.render_to_json(response, request_handler=self)
        elif extension == 'jsonp':
            self.set_header("Content-Type", "application/javascript; charset=UTF-8")
            callback = kwargs.get('callback') if kwargs.get('callback') else fn.__name__
            return "%s(%s);" % (callback, json.dumps(response))
        elif extension == 'xml':
            return self.render_to_xml(response, request_handler=self)

    return wrapped

########NEW FILE########
__FILENAME__ = dispatcher
# coding: utf-8
import re

from tornado.web import URLSpec
from routes.route import Route


def url(route=None, controller=None, action=None, name=None):

    route = Route(name, route)
    route.makeregexp('')

    regexp = re.sub(r'(?<!\\)\\', '', route.regexp)

    return URLSpec(regexp, controller, dict(action=action), name=name)

########NEW FILE########
__FILENAME__ = meta
# -*- coding: utf-8 -*-
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import time

from sqlalchemy import create_engine
from sqlalchemy.interfaces import ConnectionProxy
from sqlalchemy.orm import scoped_session, sessionmaker

from torneira import settings


class TimerProxy(ConnectionProxy):
    def cursor_execute(self, execute, cursor, statement, parameters, context, executemany):
        if not settings.DEBUG:
            return execute(cursor, statement, parameters, context)

        now = time.time()
        try:
            return execute(cursor, statement, parameters, context)
        finally:
            total = time.time() - now
            logging.debug("Query: %s" % statement)
            logging.debug("Total Time: %f" % total)


class TorneiraSession(object):
    _session = None

    def __new__(cls, *args, **kwarg):
        if not cls._session:
            engine = create_engine(settings.DATABASE_ENGINE, pool_size=settings.DATABASE_POOL_SIZE, pool_recycle=300, proxy=TimerProxy())

            if hasattr(settings, 'CACHED_QUERY') and settings.CACHED_QUERY:
                from torneira.cache import CachedQuery
                cls._session = scoped_session(sessionmaker(autocommit=True, autoflush=False, expire_on_commit=False, query_cls=CachedQuery, bind=engine))
            else:
                cls._session = scoped_session(sessionmaker(autocommit=True, autoflush=False, expire_on_commit=False, bind=engine))

        return cls._session

########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging

from tornado.web import Application, StaticFileHandler, URLSpec
from tornado.ioloop import IOLoop

from torneira import settings


class TorneiraServer(object):

    def __init__(self, port, media_dir, xheaders=False):
        self.port = port
        self.media_dir = media_dir
        self.xheaders = xheaders
        self.urls = self._get_urls()

    def _get_urls(self):
        _imported = __import__(settings.ROOT_URLS, globals(), locals(), ['urls'], -1)
        return _imported.urls

    def run(self):
        conf = {
            'debug': getattr(settings, 'DEBUG', False),
            'cookie_secret': getattr(settings, 'COOKIE_SECRET', None),
        }

        if hasattr(settings, 'LOG_FUNCTION'):
            conf['log_function'] = settings.LOG_FUNCTION

        static_url = URLSpec(r"/media/(.*)", StaticFileHandler, {"path": self.media_dir}),
        urls = static_url + self.urls
        application = Application(urls, **conf)

        application.listen(self.port, xheaders=self.xheaders)

        logging.info("Starting Torneira Server on port %s" % self.port)

        IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = handler
# coding: utf-8
from cProfile import Profile

from tornado.web import RequestHandler

from torneira import settings


class TorneiraHandler(RequestHandler):
    _action = None

    def initialize(self, *args, **kwargs):
        self._action = kwargs.get('action')

    def get(self, *args, **kwargs):
        self._process_request(*args, **kwargs)

    def post(self, *args, **kwargs):
        self._process_request(*args, **kwargs)

    def _process_request(self, *args, **kwargs):
        assert self._action, 'You need to specify action data for URL or override get/post/etc methods.'

        method_callable = getattr(self, self._action)
        if hasattr(settings, 'PROFILING') and settings.PROFILING is True:
            response = self._profile_request(method_callable, *args, **kwargs)
        else:
            response = method_callable(*args, **kwargs)
        if response is not None:
            self.write(response)

    def _profile_request(self, method, *args, **kwargs):
        assert hasattr(settings, 'PROFILE_FILE'), "Missing PROFILE_FILE config"
        profiler = Profile()
        output = profiler.runcall(method, *args, **kwargs)
        profiler.dump_stats(settings.PROFILE_FILE)
        return output

    def write_error(self, status_code, **kwargs):
        if hasattr(self, 'output_errors'):
            self.output_errors(status_code, **kwargs)

########NEW FILE########
__FILENAME__ = encoding
# -*- coding: utf-8 -*-
#
# Copyright Marcel Nicolay <marcel.nicolay@gmail.com>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import datetime
import types


class TorneiraUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj,
                type(self.obj))


class StrAndUnicode(object):
    """
    A class whose __str__ returns its __unicode__ as a UTF-8 bytestring.

    Useful as a mix-in.
    """
    def __str__(self):
        return self.__unicode__().encode('utf-8')


def smart_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a unicode object representing 's'. Treats bytestrings using the
    'encoding' codec.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    return force_unicode(s, encoding, strings_only, errors)


def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int, long, datetime.datetime, datetime.date, datetime.time, float)):
        return s
    try:
        if not isinstance(s, basestring,):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                try:
                    s = unicode(str(s), encoding, errors)
                except UnicodeEncodeError:
                    if not isinstance(s, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    s = ' '.join([force_unicode(arg, encoding, strings_only,
                            errors) for arg in s])
        elif not isinstance(s, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError, e:
        raise TorneiraUnicodeDecodeError(s, *e.args)
    return s


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import datetime

from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base

from torneira.core.meta import TorneiraSession

metadata = MetaData()


class MetaBaseModel(DeclarativeMeta):
    def __init__(cls, classname, bases, dict_):
        return DeclarativeMeta.__init__(cls, classname, bases, dict_)

Model = declarative_base(metadata=metadata, metaclass=MetaBaseModel)


class Repository(object):
    def as_dict(self):
        items = {}
        for attrname in dir(self):
            if attrname.startswith("_"):
                continue

            attr = getattr(self, attrname)
            if isinstance(attr, (basestring, int, float, long)):
                items[attrname] = attr
            if isinstance(attr, (datetime.datetime, datetime.time)):
                items[attrname] = attr.isoformat()
            if isinstance(attr, list):
                items[attrname] = [x.as_dict() for x in attr]

        return items

    @classmethod
    def get(cls, id):
        session = TorneiraSession()
        return session.query(cls).get(id)

    @classmethod
    def fetch_by(cls, **kw):
        session = TorneiraSession()
        return session.query(cls).filter_by(**kw)

    @classmethod
    def all(cls, limit=None):
        session = TorneiraSession()
        if limit:
            return session.query(cls).all()[limit[0]:limit[1]]
        return session.query(cls).all()

    @classmethod
    def create(cls, **kwargs):
        instance = cls()
        for k, v in kwargs.items():
            setattr(instance, k, v)

        instance.save()
        return instance

    def delete(self):
        session = TorneiraSession()
        session.delete(self)
        session.flush()

    def save(self):
        session = TorneiraSession()
        if not self.id:
            session.add(self)
        session.flush()

########NEW FILE########
__FILENAME__ = cli
import sys
from optparse import OptionParser


class CLI(object):

    color = {
        "PINK": "",
        "BLUE": "",
        "CYAN": "",
        "GREEN": "",
        "YELLOW": "",
        "RED": "",
        "END": "",
    }

    def enable_colors(self):
        CLI.color = {
            "PINK": "\033[35m",
            "BLUE": "\033[34m",
            "CYAN": "\033[36m",
            "GREEN": "\033[32m",
            "YELLOW": "\033[33m",
            "RED": "\033[31m",
            "END": "\033[0m",
        }

    def __init__(self):
        self.__config_parser()

    def __config_parser(self):
        self.__parser = OptionParser(usage="usage: %prog [options]")

        self.__parser.add_option("-s", "--settings",
                dest="settings_file",
                default="settings.py",
                help="Use a specific settings file. If not provided, will search for 'settings.py' in the current directory.")

        self.__parser.add_option("-d", "--daemon",
                dest="daemon",
                default=False,
                action="store_true",
                help="Run torneira server as an daemon. (default is false)")

        self.__parser.add_option("-m", "--media", "--media_dir",
                dest="media_dir",
                default="media",
                help="User a specific media dir. If not provided, will search for media dir in the current directory")

        self.__parser.add_option("-x", "--xheaders",
                dest="xheaders",
                default=False,
                action="store_true",
                help="Turn extra headers parse on in tornado server. (default is false)")

        self.__parser.add_option("-p", "--port",
                dest="port",
                default=8888,
                type=int,
                help="Use a specific port number (default is 8888).")

        self.__parser.add_option("--pidfile",
                dest="pidfile",
                default="/tmp/torneira.pid",
                help="Use a specific pidfile. If not provide, will create /tmp/torneira.pid")

        self.__parser.add_option("-v", "--version",
                action="store_true",
                dest="print_version",
                default=False,
                help="Displays tornado and torneira version and exit.")

        self.__parser.add_option("--colors",
                action="store_true",
                dest="enable_colors",
                default=False,
                help="Output with beautiful colors.")

    def parse(self):
        return self.__parser.parse_args()

    def print_error(self, msg):
        self.print_msg(msg, "RED", out=sys.stderr)
        sys.exit(1)

    def print_info(self, msg):
        self.print_msg(msg, "BLUE")
        sys.exit(0)

    def print_msg(self, msg, color='END', out=None):
        if not out:
            out = sys.stdout
        out.write("%s%s%s\n" % (self.color[color], msg, self.color["END"]))

########NEW FILE########
__FILENAME__ = main
# coding: utf-8
from __future__ import with_statement

import daemon
import os
import sys
import traceback
from cli import CLI

import lockfile
import tornado
import torneira


class Main(object):
    def __init__(self, cli, options, args):
        self.options = options
        self.args = args
        self.cli = cli

    def start(self):
        options = self.options
        # set path
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(options.settings_file)), ".."))
        sys.path.insert(0, os.path.dirname(os.path.abspath(options.settings_file)))

        # set setting
        exec("import %s as settings" % os.path.splitext(os.path.basename(options.settings_file))[0])
        torneira.settings = settings  

        from torneira.core.server import TorneiraServer
        server = TorneiraServer(
            port=options.port,
            media_dir=os.path.abspath(options.media_dir),
            xheaders=options.xheaders
        )

        if options.daemon:
            pidfile = '%s.%s' % (options.pidfile, options.port)
            lock = lockfile.FileLock(pidfile)
            if lock.is_locked():
                sys.stderr.write("torneira already running on port %s\n" % options.port)
                return

            context = daemon.DaemonContext(pidfile=lock)
            with context:
                server.run()
        else:
            server.run()

    def print_version(self):
        msg = 'torneira v%s' % torneira.__version__
        self.cli.print_msg(msg)

########NEW FILE########
__FILENAME__ = mako_engine
# coding: utf-8
from mako.exceptions import TopLevelLookupException, html_error_template
from mako.lookup import TemplateLookup
from tornado.web import HTTPError

from torneira import settings


class MakoMixin(object):

    def render_to_template(self, template_name, **context):
        assert hasattr(settings, 'TEMPLATE_DIRS'), "Missing TEMPLATE_DIRS config"

        lookup = TemplateLookup(directories=settings.TEMPLATE_DIRS,
            input_encoding='utf-8', output_encoding='utf-8',
            default_filters=['decode.utf8'])

        try:
            template = lookup.get_template(template_name)
        except TopLevelLookupException:
            raise HTTPError(500, "Template %s not found" % template_name)

        context.update({
            'settings': settings,
            'url_for': self.reverse_url
        })

        return template.render(**context)

    def output_errors(self, status_code, **kwargs):
        self.write(html_error_template().render())

########NEW FILE########
__FILENAME__ = client
import urllib

from tornado.httpserver import HTTPRequest
from tornado.escape import parse_qs_bytes, native_str
from tornado.web import Application, HTTPError

from torneira.core.server import TorneiraHandler
from torneira import settings


class TestingClient(object):

    def create_request(self, uri, method="GET", headers={}, body=None, remote_ip=None):
        request = HTTPRequest(uri=uri, method=method, headers=headers, body=body, remote_ip=remote_ip)

        if body:
            arguments = parse_qs_bytes(native_str(body))
            for name, values in arguments.iteritems():
                values = [v for v in values if v]
                if values:
                    request.arguments.setdefault(name, []).extend(values)

        return request

    def make_request(self, request, callback=None):
        cookie_secret = settings.COOKIE_SECRET if hasattr(settings, 'COOKIE_SECRET') else None
        application = Application([], cookie_secret=cookie_secret)
        handler = TestingHandler(application, request, callback=callback)

        try:
            handler.process_request(method=request.method)
            if not callback:
                handler.finish()
        except HTTPError, e:
            handler.response.set_code(e.status_code)

        return handler.response

    def get(self, request, callback=None, **kwargs):
        if isinstance(request, str):
            request = self.create_request(uri=request, method='GET', **kwargs)

        return self.make_request(request, callback=callback)

    def post(self, request, data={}, callback=None, **kwargs):
        if isinstance(request, str):
            request = self.create_request(uri=request, method='POST', body=TestingClient.parse_post_data(data), **kwargs)

        return self.make_request(request, callback=callback)

    def put(self, request, data={}, callback=None, **kwargs):
        if isinstance(request, str):
            request = self.create_request(uri=request, method='PUT', body=TestingClient.parse_post_data(data), **kwargs)

        return self.make_request(request, callback=callback)

    def delete(self, request, data={}, callback=None, **kwargs):
        if isinstance(request, str):
            request = self.create_request(uri=request, method='DELETE', body=TestingClient.parse_post_data(data), **kwargs)

        return self.make_request(request, callback=callback)

    @staticmethod
    def parse_post_data(data):
        if isinstance(data, dict):
            data = TestingClient._convert_dict_to_tuple(data)
        return urllib.urlencode(data)

    @staticmethod
    def _convert_dict_to_tuple(data):
        """Converts params dict to tuple

        This allows lists on each value.
        """
        tuples = []
        for key, value in data.iteritems():
            if isinstance(value, list):
                for each_value in value:
                    tuples.append((key, each_value))
            else:
                tuples.append((key, value))
        return tuples


class TestingResponse(object):
    def __init__(self, request_handler):
        self.body = None
        self.code = None
        self._request_handler = request_handler

    def write(self, body):
        self.body = body

    def set_code(self, code):
        self.code = code

    @property
    def headers(self):
        return self._request_handler._headers


class TestingHandler(TorneiraHandler):
    def __init__(self, application, request, callback=None, **kargs):
        self.response = TestingResponse(self)
        self.callback = callback

        del(request.connection)

        super(TestingHandler, self).__init__(application, request)

    def write(self, body):
        self.response.write(body)

    def finish(self):
        self.response.set_code(self.get_status())
        if self.callback:
            self.callback(self.response)

########NEW FILE########
__FILENAME__ = testcase
# coding: utf-8
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application
from torneira import settings


class TestCase(AsyncHTTPTestCase):
    def get_app(self):
        _imported = __import__(settings.ROOT_URLS, globals(), locals(), ['urls'], -1)
        return Application(_imported.urls, cookie_secret='123456')

########NEW FILE########
