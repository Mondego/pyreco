__FILENAME__ = helloworld_basic
#!/usr/bin/env python
#
# Copyright 2009 Facebook
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
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado
from basic import require_basic_auth

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

def validate(uname, passwd):
    print("VALIDATE: Called with creds %s:%s" % (uname, passwd))
    creds = {'auth_username': 'jonesy', 'auth_password': 'foobar'}
    if uname == creds['auth_username'] and passwd == creds['auth_password']:
        print("VALIDATE: Credentials appear to be valid")
        return True
    else:
        print("VALIDATE: Bad creds")
        return False

@require_basic_auth('Authrealm', validate)
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world - Tornado %s" % tornado.version)


def main():
    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/", MainHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = helloworld_basic_ldap
#!/usr/bin/env python
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado
from basic import require_basic_auth
import ldapauth
from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

@require_basic_auth('Authrealm', ldapauth.auth_user_ldap)
class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world - Tornado %s" % tornado.version)


def main():
    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/", MainHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = helloworld_digest
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import digest
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)


class MainHandler(digest.DigestAuthMixin, tornado.web.RequestHandler):
    def getcreds(uname):
        creds = {'auth_username': 'jonesy', 'auth_password': 'foobar'}
        if uname == creds['auth_username']:
            return creds

    @digest.digest_auth('Authusers', getcreds)
    def get(self):
        self.write("Hello, world - Tornado %s" % tornado.version)


def main():
    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/", MainHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = application_test
import mock
import sys
from tornado import web
try:
    import unittest2 as unittest
except ImportError:
    import unittest
sys.path.insert(0, '..')

from tinman import application


class ApplicationTests(unittest.TestCase):

    def setUp(self):
        self._mock_obj = mock.Mock(spec=application.TinmanApplication)

    def test_load_translations(self):
        with mock.patch('tornado.locale.load_translations') as mock_load:
            path = '/foo'
            application.TinmanApplication._load_translations(self._mock_obj,
                                                             path)
            mock_load.assert_called_once_with(path)


class AttributeTests(unittest.TestCase):

    def test_add_attribute_exists(self):
        obj = application.TinmanAttributes()
        obj.add('test_attr', 'test')
        self.assertTrue('test_attr' in obj)

    def test_add_attribute_matches(self):
        obj = application.TinmanAttributes()
        value = 'Test Value'
        obj.add('test_attr', value)
        self.assertEqual(obj.test_attr, value)

    def test_add_attribute_raises(self):
        obj = application.TinmanAttributes()
        value = 'Test Value'
        obj.add('test_attr', value)
        self.assertRaises(AttributeError, obj.add, 'test_attr', value)

    def test_set_attribute_matches(self):
        obj = application.TinmanAttributes()
        value = 'Test Value'
        obj.test_attr = value
        self.assertEqual(obj.test_attr, value)

    def test_set_overwrite_attribute(self):
        obj = application.TinmanAttributes()
        obj.test_attr = 'First Value'
        value = 'Test Value'
        obj.test_attr = value
        self.assertEqual(obj.test_attr, value)

    def test_attribute_in_obj(self):
        obj = application.TinmanAttributes()
        obj.test_attr = 'First Value'
        self.assertTrue('test_attr' in obj)

    def test_attribute_not_in_obj(self):
        obj = application.TinmanAttributes()
        self.assertFalse('test_attr' in obj)

    def test_attribute_delete(self):
        obj = application.TinmanAttributes()
        obj.test_attr = 'Foo'
        del obj.test_attr
        self.assertFalse('test_attr' in obj)

    def test_attribute_remove(self):
        obj = application.TinmanAttributes()
        obj.test_attr = 'Foo'
        obj.remove('test_attr')
        self.assertFalse('test_attr' in obj)

    def test_attribute_remove_raises(self):
        obj = application.TinmanAttributes()
        self.assertRaises(AttributeError, obj.remove, 'test_attr')

########NEW FILE########
__FILENAME__ = whitelist_test
import mock
import sys
from tornado import web
try:
    import unittest2 as unittest
except ImportError:
    import unittest
sys.path.insert(0, '..')


from tinman import whitelist


# Mock up the values
class RequestMock(object):

    def __init__(self, remote_ip):

        # Mock the application object
        self.application = mock.Mock()
        self.application.settings = dict()

        # Mock up the request object
        self.request = mock.Mock()
        self.request.remote_ip = remote_ip

    @whitelist.whitelisted
    def whitelisted_method(self):
        return True

    @whitelist.whitelisted("11.12.13.0/24")
    def whitelisted_specific(self):
        return True


class WhitelistTests(unittest.TestCase):

    def setUp(self):
        self.request = self._get_request()

    def tearDown(self):
        del self.request

    def _get_request(self, ip_address='1.2.3.4'):
        request = RequestMock(ip_address)
        request.application.settings['whitelist'] = ['1.2.3.0/24']
        return request

    def test_empty_whitelist(self):
        request = RequestMock('1.2.3.4')
        self.assertRaises(ValueError,
                          request.whitelisted_method,
                          'ValueError not raised for empty whitelist')

    def test_whitelisted_ip(self):
        self.assertTrue(self.request.whitelisted_method(),
                        'Whitelisted IP address did not pass')

    def test_non_whitelisted_ip(self):
        request = self._get_request('2.2.3.4')
        self.assertRaises(web.HTTPError,
                          request.whitelisted_method,
                          'whitelist did not raise whitelist.HTTPError')

    def test_specific_whitelisted_ip(self):
        request = self._get_request('11.12.13.14')
        self.assertTrue(request.whitelisted_specific(),
                        'Whitelisted IP address did not pass')

    def test_specific_non_whitelisted_ip(self):
        self.assertRaises(web.HTTPError,
                          self.request.whitelisted_specific,
                          'whitelist did not raise whitelist.HTTPError')


    def test_invalid_whitelisted_ip(self):
        try:
            @whitelist.whitelisted(1234)
            def whitelisted_invalid(self):
                return True
        except ValueError:
            return
        assert False, 'invalid specified whitelist did not raise ValueError'

########NEW FILE########
__FILENAME__ = application
"""
Main Tinman Application Class

"""
import logging
import sys

from tornado import web

from tinman import config
from tinman import exceptions
from tinman import utils
from tinman import __version__

LOGGER = logging.getLogger(__name__)

STATIC_PATH = 'static_path'
TEMPLATE_PATH = 'template_path'


class Application(web.Application):
    """Application extends web.Application and handles all sorts of things
    for you that you'd have to handle yourself.

    """
    def __init__(self, settings, routes, port):
        """Create a new Application instance with the specified Routes and
        settings.

        :param dict settings: Application settings
        :param list routes: A list of route tuples
        :param int port: The port number for the HTTP server

        """
        self.attributes = Attributes()
        self.host = utils.gethostname()
        self.port = port
        self._config = settings or dict()
        self._insert_base_path()
        self._prepare_paths()
        self._prepare_routes(routes)
        self._prepare_static_path()
        self._prepare_template_path()
        self._prepare_transforms()
        self._prepare_translations()
        self._prepare_uimodules()
        self._prepare_version()
        if not routes:
            LOGGER.critical('Did not add any routes, will exit')
            raise exceptions.NoRoutesException()

        # Get the routes and initialize the tornado.web.Application instance
        super(Application, self).__init__(routes, **self._config)

    def log_request(self, handler):
        """Writes a completed HTTP request to the logs.

        By default writes to the tinman.application LOGGER.  To change
        this behavior either subclass Application and override this method,
        or pass a function in the application settings dictionary as
        'log_function'.

        :param tornado.web.RequestHandler handler: The request handler

        """
        if config.LOG_FUNCTION in self.settings:
            self.settings[config.LOG_FUNCTION](handler)
            return
        if handler.get_status() < 400:
            log_method = LOGGER.info
        elif handler.get_status() < 500:
            log_method = LOGGER.warning
        else:
            log_method = LOGGER.exception
        request_time = 1000.0 * handler.request.request_time()
        log_method("%d %s %.2fms", handler.get_status(),
                   handler._request_summary(), request_time)

    @property
    def paths(self):
        """Return the path configuration

        :rtype: dict

        """
        return self._config.get(config.PATHS, dict())

    def _import_class(self, class_path):
        """Try and import the specified namespaced class.

        :param str class_path: The full path to the class (foo.bar.Baz)
        :rtype: class

        """
        LOGGER.debug('Importing %s', class_path)
        try:
            return utils.import_namespaced_class(class_path)
        except ImportError as error:
            LOGGER.critical('Could not import %s: %s', class_path, error)
            return None

    def _import_module(self, module_path):
        """Dynamically import a module returning a handle to it.

        :param str module_path: The module path
        :rtype: module

        """
        LOGGER.debug('Importing %s', module_path)
        try:
            return __import__(module_path)
        except ImportError as error:
            LOGGER.critical('Could not import %s: %s', module_path, error)
            return None

    def _insert_base_path(self):
        """If the "base" path is set in the paths section of the config, insert
        it into the python path.

        """
        if config.BASE in self.paths:
            sys.path.insert(0, self.paths[config.BASE])

    def _prepare_paths(self):
        """Set the value of {{base}} in paths if the base path is set in the
        configuration.

        :raises: ValueError

        """
        if config.BASE in self.paths:
            for path in [path for path in self.paths if path != config.BASE]:
                if config.BASE_VARIABLE in self.paths[path]:
                    self.paths[path] = \
                        self.paths[path].replace(config.BASE_VARIABLE,
                                                 self.paths[config.BASE])
        LOGGER.debug('Prepared paths: %r', self.paths)

    def _prepare_route(self, attrs):
        """Take a given inbound list for a route and parse it creating the
        route and importing the class it belongs to.

        :param list attrs: Route attributes
        :rtype: list

        """
        if type(attrs) not in (list, tuple):
            LOGGER.error('Invalid route, must be a list or tuple: %r', attrs)
            return

        # By default there are not any extra kwargs
        kwargs = None

        # If there is a regex based route, set it up with a raw string
        if attrs[0] == 're':
            route = r'%s' % attrs[1]
            classpath = attrs[2]
            if len(attrs) == 4:
                kwargs = attrs[3]
        else:
            route = r'%s' % attrs[0]
            classpath = attrs[1]
            if len(attrs) == 3:
                kwargs = attrs[2]

        LOGGER.debug('Initializing route: %s with %s', route, classpath)
        try:
            handler = self._import_class(classpath)
        except ImportError as error:
            LOGGER.error('Class import error for %s: %r', classpath, error)
            return None

        # Setup the prepared route, adding kwargs if there are any
        prepared_route = [route, handler]
        if kwargs:
            prepared_route.append(kwargs)

        # Return the prepared route as a tuple
        return tuple(prepared_route)

    def _prepare_routes(self, routes):
        """Prepare the routes by iterating through the list of tuples & calling
        prepare route on them.

        :param routes: Routes to prepare
        :type routes: list
        :rtype: list
        :raises: ValueError

        """
        if not isinstance(routes, list):
            raise ValueError('Routes parameter must be a list of tuples')
        prepared_routes = list()
        for parts in routes:
            route = self._prepare_route(parts)
            if route:
                LOGGER.info('Appending handler: %r', route)
                prepared_routes.append(route)
        return prepared_routes

    def _prepare_static_path(self):
        LOGGER.info('%s in %r: %s', config.STATIC, self.paths,
                    config.STATIC in self.paths)
        if config.STATIC in self.paths:
            LOGGER.info('Setting static path to %s', self.paths[config.STATIC])
            self._config[STATIC_PATH] = self.paths[config.STATIC]

    def _prepare_template_path(self):
        LOGGER.info('%s in %r: %s', config.TEMPLATES, self.paths,
                    config.TEMPLATES in self.paths)
        if config.TEMPLATES in self.paths:
            LOGGER.info('Setting template path to %s',
                        self.paths[config.TEMPLATES])
            self._config[TEMPLATE_PATH] = self.paths[config.TEMPLATES]

    def _prepare_transforms(self):
        """Prepare the list of transforming objects"""
        for offset, value in enumerate(self._config.get(config.TRANSFORMS, [])):
            self._config[config.TRANSFORMS][offset] = self._import_class(value)

    def _prepare_translations(self):
        """Load in translations if they are set, and add the default locale as
        well.

        """
        if config.TRANSLATIONS in self.paths:
            LOGGER.info('Loading translations from %s',
                        self.paths[config.TRANSLATIONS])
            from tornado import locale
            locale.load_translations(self.paths[config.TRANSLATIONS])
            if config.DEFAULT_LOCALE in self._config:
                LOGGER.info('Setting default locale to %s',
                            self._config[config.DEFAULT_LOCALE])
                locale.set_default_locale(self._config[config.DEFAULT_LOCALE])

    def _prepare_uimodules(self):
        """Prepare the UI Modules from a list of namespaced paths."""
        for key, value in self._config.get(config.UI_MODULES, {}).iteritems():
            self._config[config.UI_MODULES][key] = self._import_class(value)
        self._config[config.UI_MODULES] = dict(self._config[config.UI_MODULES] or {})

    def _prepare_version(self):
        """Setup the application version"""
        if config.VERSION not in self._config:
            self._config[config.VERSION] = __version__


class Attributes(object):
    """A base object to hang attributes off of for application level scope that
    can be used across connections.

    """
    ATTRIBUTES = '_attributes'

    def __init__(self):
        """Create a new instance of the Attributes class"""
        self._attributes = dict()

    def __contains__(self, item):
        """Check to see if an attribute is set on the object.

        :param str item: The attribute name
        :rtype: bool

        """
        return item in self.__dict__[self.ATTRIBUTES].keys()

    def __delattr__(self, item):
        """Delete an attribute from the object.

        :param str item: The attribute name
        :raises: AttributeError

        """
        if item == self.ATTRIBUTES:
            raise AttributeError('Can not delete %s', item)
        if item not in self.__dict__[self.ATTRIBUTES]:
            raise AttributeError('%s is not set' % item)
        del self.__dict__[self.ATTRIBUTES][item]

    def __getattr__(self, item):
        """Get an attribute from the class.

        :param str item: The attribute name
        :rtype: any

        """
        if item == self.ATTRIBUTES:
            return self.__dict__[item]
        return self.__dict__[self.ATTRIBUTES].get(item)

    def __iter__(self):
        """Iterate through the keys in the data dictionary.

        :rtype: list

        """
        return iter(self.__dict__[self.ATTRIBUTES])

    def __len__(self):
        """Return the length of the data dictionary.

        :rtype: int

        """
        return len(self.__dict__[self.ATTRIBUTES])

    def __repr__(self):
        """Return the representation of the class as a string.

        :rtype: str

        """
        return '<%s(%r)>' % (self.__class__.__name__,
                             self.__dict__[self.ATTRIBUTES])

    def __setattr__(self, item, value):
        """Set an attribute on the object.

        :param str item: The attribute name
        :param any value: The attribute value

        """
        if item == self.ATTRIBUTES:
            self.__dict__[item] = value
        else:
            self.__dict__[self.ATTRIBUTES][item] = value

    def add(self, item, value):
        """Add an attribute value to our object instance.

        :param str item: Application attribute name
        :param any value: Value to associate with the attribute
        :raises: AttributeError

        """
        if item in self.__dict__[self.ATTRIBUTES].keys():
            raise AttributeError('%s already exists' % item)
        setattr(self, item, value)

    def remove(self, item):
        """Remove an attribute value to our object instance.

        :param str item: Application attribute name
        :raises: AttributeError

        """
        if item not in self.__dict__[self.ATTRIBUTES].keys():
            raise AttributeError('%s does not exist' % item)
        delattr(self, item)

    def set(self, item, value):
        """Set an attribute value to our object instance.

        :param str item: Application attribute name
        :param any value: Value to associate with the attribute
        :raises: AttributeError

        """
        setattr(self, item, value)

########NEW FILE########
__FILENAME__ = basic
"""
A tornado.web.RequestHandler decorator that provides HTTP Basic Authentication. 

The decorator takes two arguments: 

    1. realm: the realm that's typically presented to the user during a
    challenge request for authentication.

    2. validate_callback: A callable that's used to validate the credentials.
    The callable will receive the username and password provided by the end
    user in a challenge.

Example usage (also see helloworld_basic.py in the examples): 

    # define the validation callback.
    def validate(uname, passwd):
        creds = {'auth_username': 'jonesy', 'auth_password': 'foobar'}
        if uname == creds['auth_username'] and passwd == creds['auth_password']:
            return True
        else:
            return False

    # now define the RequestHandler, using the decorator.
    @require_basic_auth('AuthRealm', validate)
    class MainHandler(tornado.web.RequestHandler):
        def get(self):
            self.write("Hello, world - Tornado %s" % tornado.version)

""" 

import base64

def require_basic_auth(realm, validate_callback, do_wrap=True):
    def require_basic_auth_decorator(handler_class):
        def wrap_execute(handler_execute):
            def require_basic_auth(handler, kwargs):
                def create_auth_header():
                    print("Creating auth header")
                    handler.set_status(401)
                    handler.set_header('WWW-Authenticate', 'Basic realm=%s' % realm)
                    handler._transforms = []
                    handler.finish()

                auth_header = handler.request.headers.get('Authorization')
                if auth_header is None or not auth_header.startswith('Basic '):
                    create_auth_header()
                else:
                    auth_decoded = base64.decodestring(auth_header[6:])
                    basicauth_user, basicauth_pass = auth_decoded.split(':', 2)
                    if validate_callback(basicauth_user, basicauth_pass):
                        return True
                    else:
                        create_auth_header()
            def _execute(self, transforms, *args, **kwargs):
                if not require_basic_auth(self, kwargs):
                    return False
                return handler_execute(self, transforms, *args, **kwargs)
            return _execute

        if do_wrap:
            handler_class._execute = wrap_execute(handler_class._execute)
        return handler_class
    return require_basic_auth_decorator

########NEW FILE########
__FILENAME__ = digest
"""
Unlike Tinman's basic authentication decorator, this one is 
applied to the individual methods inside the RequestHandler. 

See helloworld_digest.py in the examples.

"""
from tornado.web import *
from hashlib import md5

class DigestAuthMixin(object):
    def apply_checksum(self, data):
        return md5(data).hexdigest()

    def apply_digest(self, secret, data):
        return self.apply_checksum(secret + ":" + data)

    def A1(self, algorithm, auth_pass):
        """
         If 'algorithm' is "MD5" or unset, A1 is:
         A1 = unq(username-value) ":" unq(realm-value) ":" passwd

         if 'algorithm' is 'MD5-Sess', A1 is:
         A1 = H( unq(username-value) ":" unq(realm-value) ":" passwd )
          ":" unq(nonce-value) ":" unq(cnonce-value)

        """

        username = self.params["username"]
        if algorithm == 'MD5' or not algorithm:
            return "%s:%s:%s" % (username, self.realm, auth_pass)
        elif algorithm == 'MD5-Sess':
            return self.apply_checksum('%s:%s:%s:%s:%s' % \
                                       (username,
                                       self.realm,
                                       auth_pass,
                                       self.params['nonce'],
                                       self.params['cnonce']))


    def A2(self):
        """
        If the "qop" directive's value is "auth" or is unspecified, then A2 is:
            A2 = Method ":" digest-uri-value
        Else,
            A2 = Method ":" digest-uri-value ":" H(entity-body)

        """
        if self.params['qop'] == 'auth' or not self.params['qop']:
            return self.request.method + ":" + self.request.uri
        elif self.params['qop'] == 'auth-int':
            #print "UNSUPPORTED 'qop' METHOD\n"
            return ":".join([self.request.method,
                             self.request.uri,
                             self.apply_checksum(self.request.body)])
        else:
            print "A2 GOT BAD VALUE FOR 'qop': %s\n" % self.params['qop']

    def response(self, auth_pass):
        if 'qop' in self.params:
            auth_comps = [self.params['nonce'],
                               self.params['nc'],
                               self.params['cnonce'],
                               self.params['qop'],
                               self.apply_checksum(self.A2())]
            return self.apply_digest(self.apply_checksum( \
                                    self.A1(self.params.get('algorithm'),
                                            auth_pass)),
                                     ':'.join(auth_comps))
        else:
            return self.apply_digest(self.apply_checksum( \
                                    self.A1(self.params.get('algorithm'),
                                            auth_pass)),
                                    ':'.join([self.params["nonce"],
                                              self.apply_checksum(self.A2())]))

    def _parse_header(self, authheader):
        try:
            n = len("Digest ")
            authheader = authheader[n:].strip()
            items = authheader.split(", ")
            keyvalues = [i.split("=", 1) for i in items]
            keyvalues = ([(k.strip(), v.strip().replace('"', '')) for
                                                            k, v in keyvalues])
            self.params = dict(keyvalues)
        except:
            self.params = []

    def _create_nonce(self):
        return md5("%d:%s" % (time.time(), self.realm)).hexdigest()

    def createAuthHeader(self):
        self.set_status(401)
        nonce = self._create_nonce()
        self.set_header("WWW-Authenticate",
                        "Digest algorithm=MD5 realm=%s qop=auth nonce=%s" %
                        (self.realm, nonce))
        self.finish()

        return False

    def get_authenticated_user(self, get_creds_callback, realm):
        creds = None
        expected_response = None
        actual_response = None
        auth = None
        if not hasattr(self,'realm'):
            self.realm = realm

        try:
            auth = self.request.headers.get('Authorization')
            if not auth or not auth.startswith('Digest '):
                return self.createAuthHeader()
            else:
                self._parse_header(auth)
                required_params = ['username', 'realm', 'nonce', 'uri',
                                   'response', 'qop', 'nc', 'cnonce']
                for k in required_params:
                    if k not in self.params:
                        print "REQUIRED PARAM %s MISSING\n" % k
                        return self.createAuthHeader()
                    elif not self.params[k]:
                        print "REQUIRED PARAM %s IS NONE OR EMPTY\n" % k
                        return self.createAuthHeader()
                    else:
                        continue

            creds = get_creds_callback(self.params['username'])
            if not creds:
                # the username passed to get_creds_callback didn't
                # match any valid users.
                self.createAuthHeader()
            else:
                expected_response = self.response(creds['auth_password'])
                actual_response = self.params['response']
                print "Expected: %s" % expected_response
                print "Actual: %s" % actual_response

            if expected_response and actual_response:
                if expected_response == actual_response:
                    self._current_user = self.params['username']
                    print ("Digest Auth user '%s' successful for realm '%s'. "
                            "URI: '%s', IP: '%s'" % (self.params['username'],
                                                     self.realm,
                                                     self.request.uri,
                                                     self.request.remote_ip))
                    return True
                else:
                    self.createAuthHeader()

        except Exception as out:
            print "FELL THROUGH: %s\n" % out
            print "AUTH HEADERS: %s" % auth
            print "SELF.PARAMS: ",self.params,"\n"
            print "CREDS: ", creds
            print "EXPECTED RESPONSE: %s" % expected_response
            print "ACTUAL RESPONSE: %s" % actual_response
            return self.createAuthHeader()


def digest_auth(realm, auth_func):
    """A decorator used to protect methods with HTTP Digest authentication.

    """
    def digest_auth_decorator(func):
        def func_replacement(self, *args, **kwargs):
            # 'self' here is the RequestHandler object, which is inheriting
            # from DigestAuthMixin to get 'get_authenticated_user'
            if self.get_authenticated_user(auth_func, realm):
                return func(self, *args, **kwargs)
        return func_replacement
    return digest_auth_decorator

########NEW FILE########
__FILENAME__ = ldapauth
"""
See an example that uses basic auth with an LDAP 
backend in examples/helloworld_basic_ldap.py

"""
import ldap
import logging

# where to start the search for users
LDAP_SEARCH_BASE = 'ou=People,dc=yourdomain,dc=com'

# the server to auth against
LDAP_URL = 'ldap://ldap.yourdomain.com'

# The attribute we try to match the username against.
LDAP_UNAME_ATTR = 'uid'

# The attribute we need to retrieve in order to perform a bind.
LDAP_BIND_ATTR = 'dn'

# Whether to use LDAPv3. Highly recommended.
LDAP_VERSION_3 = True

def auth_user_ldap(uname, pwd):
    """
    Attempts to bind using the uname/pwd combo passed in.
    If that works, returns true. Otherwise returns false.

    """
    if not uname or not pwd:
        logging.error("Username or password not supplied")
        return False

    ld = ldap.initialize(LDAP_URL)
    if LDAP_VERSION_3:
        ld.set_option(ldap.VERSION3, 1)
    ld.start_tls_s()
    udn = ld.search_s(LDAP_SEARCH_BASE, ldap.SCOPE_ONELEVEL,
                           '(%s=%s)' % (LDAP_UNAME_ATTR,uname), [LDAP_BIND_ATTR])
    if udn:
        try:
            bindres = ld.simple_bind_s(udn[0][0], pwd)
        except ldap.INVALID_CREDENTIALS, ldap.UNWILLING_TO_PERFORM:
            logging.error("Invalid or incomplete credentials for %s", uname)
            return False
        except Exception as out:
            logging.error("Auth attempt for %s had an unexpected error: %s",
                         uname, out)
            return False
        else:
            return True
    else:
        logging.error("No user by that name")
        return False



########NEW FILE########
__FILENAME__ = mixins
"""
GitHub Authentication and API Mixins

"""
import hashlib
import logging
from tornado import auth
from tornado import concurrent
from tornado import escape
from tornado import httpclient
from tinman import __version__ as tinman_version
from tornado import version as tornado_version

LOGGER = logging.getLogger(__name__)


class OAuth2Mixin(auth.OAuth2Mixin):
    """Base OAuth2 Mixin with a few more handy functions"""
    _ACCEPT = 'application/json'
    _USER_AGENT = 'Tinman %s/Tornado %s' % (tinman_version, tornado_version)

    _API_NAME = None

    _CLIENT_ID_SETTING = None
    _CLIENT_SECRET_SETTING = None
    _BASE_SCOPE = []

    # The state value to prevent hijacking
    state = None

    def oauth2_redirect_uri(self, callback_uri=''):
        return auth.urlparse.urljoin(self.request.full_url(), callback_uri)


    @concurrent.return_future
    def authenticate_redirect(self, callback_uri=None, cancel_uri=None,
                              extended_permissions=None, callback=None):
        """Perform the authentication redirect to GitHub


        """
        self.require_setting(self._CLIENT_ID_SETTING, self._API_NAME)

        scope = self._BASE_SCOPE
        if extended_permissions:
            scope += extended_permissions

        args = {'client_id': self.settings[self._CLIENT_ID_SETTING],
                'redirect_uri': self.oauth2_redirect_uri(callback_uri),
                'scope': ','.join(scope)}

        # If cookie_secret is set, use it for GitHub's state value
        if not self.state and 'cookie_secret' in self.settings:
            sha1 = hashlib.sha1(self.settings['cookie_secret'])
            self.state = str(sha1.hexdigest())

        # If state is set, add it to args
        if self.state:
            args['state'] = self.state

        LOGGER.info('Redirect args: %r', args)

        # Redirect the user to the proper URL
        self.redirect(self._OAUTH_AUTHORIZE_URL +
                      auth.urllib_parse.urlencode(args))
        callback()

    @auth._auth_return_future
    def get_authenticated_user(self, callback):
        """ Fetches the authenticated user

        :param method callback: The callback method to invoke

        """
        self.require_setting(self._CLIENT_ID_SETTING, self._API_NAME)
        self.require_setting(self._CLIENT_SECRET_SETTING, self._API_NAME)

        if self.state:
            if (not self.get_argument('state', None) or
                self.state != self.get_argument('state')):
                LOGGER.error('State did not match: %s != %s',
                             self.state, self.get_argument('state'))
                raise auth.AuthError('Problematic Reply from %s' %
                                     self._API_NAME)

        args = {'client_id': self.settings[self._CLIENT_ID_SETTING],
                'client_secret': self.settings[self._CLIENT_SECRET_SETTING],
                'code': self.get_argument('code'),
                'redirect_uri': self.oauth2_redirect_uri()}

        http_client = self._get_auth_http_client()
        callback = self.async_callback(self._on_access_token, callback)
        http_client.fetch(self._OAUTH_ACCESS_TOKEN_URL,
                          method='POST',
                          headers={'Accept': self._ACCEPT},
                          user_agent=self._USER_AGENT,
                          body=auth.urllib_parse.urlencode(args),
                          callback=callback)

    @staticmethod
    def _get_auth_http_client():
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()

    def _on_access_token(self, future, response):
        """This should be extended in the child mixins"""
        raise NotImplementedError


class GithubMixin(OAuth2Mixin):
    """GitHub OAuth2 Authentication

    To authenticate with GitHub, first register your application at
    https://github.com/settings/applications/new to get the client ID and
    secret.

    """
    _API_URL = 'https://api.github.com/'
    _OAUTH_ACCESS_TOKEN_URL = 'https://github.com/login/oauth/access_token'
    _OAUTH_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize?'

    _API_NAME = 'GitHub API'
    _CLIENT_ID_SETTING = 'github_client_id'
    _CLIENT_SECRET_SETTING = 'github_client_secret'
    _BASE_SCOPE = ['user:email']

    def _on_access_token(self, future, response):
        """Invoked as a callback when GitHub has returned a response to the
        access token request.

        :param method future: The callback method to pass along
        :param tornado.httpclient.HTTPResponse response: The HTTP response

        """
        content = escape.json_decode(response.body)
        if 'error' in content:
            LOGGER.error('Error fetching access token: %s', content['error'])
            future.set_exception(auth.AuthError('Github auth error: %s' %
                                                str(content['error'])))
            return
        callback = self.async_callback(self._on_github_user, future,
                                       content['access_token'])
        self.github_request('user', callback, content['access_token'])

    def _on_github_user(self, future, access_token, response):
        """Invoked as a callback when self.github_request returns the response
        to the request for user data.

        :param method future: The callback method to pass along
        :param str access_token: The access token for the user's use
        :param dict response: The HTTP response already decoded

        """
        response['access_token'] = access_token
        future.set_result(response)

    @auth._auth_return_future
    def github_request(self, path, callback, access_token=None,
                       post_args=None, **kwargs):
        """Make a request to the GitHub API, passing in the path, a callback,
        the access token, optional post arguments and keyword arguments to be
        added as values in the request body or URI

        """
        url = self._API_URL + path
        all_args = {}
        if access_token:
            all_args["access_token"] = access_token
            all_args.update(kwargs)
        if all_args:
            url += "?" + auth.urllib_parse.urlencode(all_args)
        callback = self.async_callback(self._on_github_request, callback)
        http = self._get_auth_http_client()
        if post_args is not None:
            http.fetch(url, method="POST",
                       user_agent='Tinman/Tornado',
                       body=auth.urllib_parse.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, user_agent='Tinman/Tornado', callback=callback)

    def _on_github_request(self, future, response):
        """Invoked as a response to the GitHub API request. Will decode the
        response and set the result for the future to return the callback or
        raise an exception

        """
        try:
            content = escape.json_decode(response.body)
        except ValueError as error:
            future.set_exception(Exception('Github error: %s' %
                                           response.body))
            return

        if 'error' in content:
            future.set_exception(Exception('Github error: %s' %
                                           str(content['error'])))
            return
        future.set_result(content)





class StackExchangeMixin(OAuth2Mixin):
    """StackExchange OAuth2 Authentication

    To authenticate with StackExchange, first register your application at
    http://stackapps.com/apps/oauth/register to get the client ID and
    secret.

    """
    _API_URL = 'https://api.stackexchange.com/2.1'
    _API_NAME = 'StackExchange API'
    _CLIENT_ID_SETTING = 'stackexchange_client_id'
    _CLIENT_SECRET_SETTING = 'stackexchange_client_secret'
    _OAUTH_ACCESS_TOKEN_URL = 'https://stackexchange.com/oauth/access_token'
    _OAUTH_AUTHORIZE_URL = 'https://stackexchange.com/oauth?'

    def _on_access_token(self, future, response):
        """Invoked as a callback when StackExchange has returned a response to
        the access token request.

        :param method future: The callback method to pass along
        :param tornado.httpclient.HTTPResponse response: The HTTP response

        """
        LOGGER.info(response.body)
        content = escape.json_decode(response.body)
        if 'error' in content:
            LOGGER.error('Error fetching access token: %s', content['error'])
            future.set_exception(auth.AuthError('StackExchange auth error: %s' %
                                                str(content['error'])))
            return
        callback = self.async_callback(self._on_stackexchange_user, future,
                                       content['access_token'])
        self.stackexchange_request('me', callback, content['access_token'])

    def _on_stackexchange_user(self, future, access_token, response):
        """Invoked as a callback when self.stackexchange_request returns the
        response to the request for user data.

        :param method future: The callback method to pass along
        :param str access_token: The access token for the user's use
        :param dict response: The HTTP response already decoded

        """
        response['access_token'] = access_token
        future.set_result(response)

    @auth._auth_return_future
    def stackexchange_request(self, path, callback, access_token=None,
                       post_args=None, **kwargs):
        """Make a request to the StackExchange API, passing in the path, a
        callback, the access token, optional post arguments and keyword
        arguments to be added as values in the request body or URI

        """
        url = self._API_URL + path
        all_args = {}
        if access_token:
            all_args["access_token"] = access_token
            all_args.update(kwargs)
        if all_args:
            url += "?" + auth.urllib_parse.urlencode(all_args)
        callback = self.async_callback(self._on_stackexchange_request, callback)
        http = self._get_auth_http_client()
        if post_args is not None:
            http.fetch(url, method="POST",
                       body=auth.urllib_parse.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback)

    def _on_stackexchange_request(self, future, response):
        """Invoked as a response to the StackExchange API request. Will decode
        the response and set the result for the future to return the callback or
        raise an exception

        """
        content = escape.json_decode(response.body)
        if 'error' in content:
            future.set_exception(Exception('StackExchange error: %s' %
                                           str(content['error'])))
            return
        future.set_result(content)

########NEW FILE########
__FILENAME__ = config
"""
Configuration Constants

"""
APPLICATION = 'Application'
DAEMON = 'Daemon'
HTTP_SERVER = 'HTTPServer'
LOGGING = 'Logging'
ROUTES = 'Routes'

ADAPTER = 'adapter'
AUTOMATIC = 'automatic'
BASE = 'base'
BASE_VARIABLE = '{{base}}'
CERT_REQS = 'cert_reqs'
DEBUG = 'debug'
DEFAULT_LOCALE = 'default_locale'
DB = 'db'
DIRECTORY = 'directory'
DURATION = 'duration'
FILE = 'file'
HOST = 'host'
LOG_FUNCTION = 'log_function'
NAME = 'name'
NEWRELIC = 'newrelic_ini'
NO_KEEP_ALIVE = 'no_keep_alive'
NONE = 'none'
OPTIONAL = 'optional'
PROCESSES = 'processes'
PATHS = 'paths'
PORT = 'port'
PORTS = 'ports'
RABBITMQ = 'rabbitmq'
REDIS = 'redis'
REQUIRED = 'required'
SSL_OPTIONS = 'ssl_options'
STATIC = 'static'
TEMPLATES = 'templates'
TRANSFORMS = 'transforms'
TRANSLATIONS = 'translations'
UI_MODULES = 'ui_modules'
VERSION = 'version'
XHEADERS = 'xheaders'

########NEW FILE########
__FILENAME__ = controller
"""The Tinman Controller class, uses clihelper for most of the main
functionality with regard to configuration, logging and daemoniaztion. Spawns a
tornado.HTTPServer and Application per port using multiprocessing.

"""
import helper
import logging
from helper import parser
import multiprocessing
import os
import signal
import sys
import time
from tornado import version as tornado_version

# Tinman Imports
from tinman import __desc__
from tinman import __version__
from tinman import config
from tinman import process

LOGGER = logging.getLogger(__name__)


class Controller(helper.Controller):
    """Tinman controller is the core application coordinator, responsible for
    spawning and managing children.

    """
    APPNAME = 'Tinman'
    DEFAULT_PORTS = [8900]
    MAX_SHUTDOWN_WAIT = 4
    VERSION = __version__

    def enable_debug(self):
        """If the cli arg for foreground is set, set the configuration option
        for debug.

        """
        if self.args.foreground:
            self.config.application[config.DEBUG] = True

    def insert_paths(self):
        """Inserts a base path into the sys.path list if one is specified in
        the configuration.

        """
        if self.args.path:
            sys.path.insert(0, self.args.path)

        if hasattr(self.config.application, config.PATHS):
            if hasattr(self.config.application.paths, config.BASE):
                sys.path.insert(0, self.config.application.paths.base)

    @property
    def living_children(self):
        """Returns a list of all child processes that are still alive.

        :rtype: list

        """
        return [child for child in self.children if child.is_alive()]

    def configuration_reloaded(self):
        """Send a SIGHUP to child processes"""
        LOGGER.info('Notifying children of new configuration updates')
        self.signal_children(signal.SIGHUP)

    def process(self):
        """Check up on child processes and make sure everything is running as
        it should be.

        """
        children = len(self.living_children)
        LOGGER.debug('%i active child%s',
                     children, '' if children == 1 else 'ren')

    @property
    def ports_to_spawn(self):
        """Return the list of ports to spawn

        :rtype: list

        """
        return (self.config.get(config.HTTP_SERVER, dict()).get(config.PORTS)
                or self.DEFAULT_PORTS)

    def set_base_path(self, value):
        """Munge in the base path into the configuration values

        :param str value: The path value

        """
        if config.PATHS not in self.config.application:
            self.config.application[config.PATHS] = dict()

        if config.BASE not in self.config.application[config.PATHS]:
            self.config.application[config.PATHS][config.BASE] = value

    def setup(self):
        """Additional setup steps."""
        LOGGER.info('Tinman v%s starting up with Tornado v%s',
                    __version__, tornado_version)
        # Setup debugging and paths
        self.enable_debug()
        self.set_base_path(os.getcwd())
        self.insert_paths()

        # Setup child processes
        self.children = list()
        self.manager = multiprocessing.Manager()
        self.namespace = self.manager.Namespace()
        self.namespace.args = self.args
        self.namespace.config = dict(self.config.application)
        self.namespace.logging = self.config.logging
        self.namespace.debug = self.debug
        self.namespace.routes = self.config.get(config.ROUTES)
        self.namespace.server = self.config.get(config.HTTP_SERVER)
        self.spawn_processes()

    def shutdown(self):
        """Send SIGABRT to child processes to instruct them to stop"""
        self.signal_children(signal.SIGABRT)

        # Wait a few iterations when trying to stop children before terminating
        waiting = 0
        while self.living_children:
            time.sleep(0.5)
            waiting += 1
            if waiting == self.MAX_SHUTDOWN_WAIT:
                self.signal_children(signal.SIGKILL)
                break

    def signal_children(self, signum):
        """Send a signal to all children

        :param int signum: The signal to send

        """
        LOGGER.info('Sending signal %i to children', signum)
        for child in self.living_children:
            if child.pid != os.getpid():
                os.kill(child.pid, signum)

    def spawn_process(self, port):
        """Create an Application and HTTPServer for the given port.

        :param int port: The port to listen on
        :rtype: multiprocessing.Process

        """
        return process.Process(name="ServerProcess.%i" % port,
                               kwargs={'namespace': self.namespace,
                                       'port': port})

    def spawn_processes(self):
        """Spawn of the appropriate number of application processes"""
        for port in self.ports_to_spawn:
            process = self.spawn_process(port)
            process.start()
            self.children.append(process)


def main():
    """Invoked by the script installed by setuptools."""
    parser.name('tinman')
    parser.description(__desc__)

    p = parser.get()
    p.add_argument('-p', '--path',
                   action='store',
                   dest='path',
                   help='Path to prepend to the Python system path')

    helper.start(Controller)

########NEW FILE########
__FILENAME__ = couchdb
"""
The CouchDB template loader allows for Tornado templates to be stored in CouchDB
and retrieved on demand and supports all of the syntax of including and
extending templates that you'd expect in any other template loader.

"""
import json
import logging
from tornado import escape
from tornado import httpclient
from tornado import template

LOGGER = logging.getLogger(__name__)


class CouchDBLoader(template.BaseLoader):
    """Extends the tornado.template.Loader allowing for templates to be loaded
    out of CouchDB.

    Templates in CouchDB should have have an _id matching the value of the name
    that is passed into load. _id's may have /'s in them. The template itself
    should be in the template node of the JSON document in CouchDB.

    """
    def __init__(self, base_url, **kwargs):
        """Creates a template loader.

        :param str base_url: The base URL for the CouchDB server

        """
        super(CouchDBLoader, self).__init__('/', **kwargs)
        self._base_url = base_url.rstrip('/')
        LOGGER.info('Initialized with base URL of %s', self._base_url)
        self._http_client = httpclient.HTTPClient()

    def load(self, name, parent_path=None):
        """Loads a template.

        :param str name: The template name
        :param str parent_path: The optional path for a parent document
        :rtype: tornado.template.Template

        """
        if name not in self.templates:
            self.templates[name] = self._create_template(name)
        return self.templates[name]

    def _create_template(self, name):
        """Create an instance of a tornado.template.Template object for the
        given template name.

        :param str name: The name/path to the template
        :rtype: tornado.template.Template

        """
        url = '%s/%s' % (self._base_url, escape.url_escape(name))
        LOGGER.debug('Making HTTP GET request to %s', url)
        response = self._http_client.fetch(url)
        data = json.loads(response.body, ensure_ascii=False)
        return template.Template(data['template'], name=name, loader=self)

########NEW FILE########
__FILENAME__ = authentication

########NEW FILE########
__FILENAME__ = memoize
"""
Tinman Cache Module

"""
from functools import wraps
from logging import debug

# Module wide dictionary to hold the cached values in
local_cache = dict()


def memoize_write(*args):

    # Append the value if the key exists, otherwise just set it
    if args[0].tinman_memoize_key in local_cache:
        debug('memoize append: %s' % args[0].tinman_memoize_key)
        local_cache[args[0].tinman_memoize_key] += args[1]
    else:
        debug('memoize set: %s' % args[0].tinman_memoize_key)
        local_cache[args[0].tinman_memoize_key] = args[1]

    # Call the monkey patched RequestHandler.write
    args[0]._write(args[1])


def memoize_finish(*args):

    # If they passed in a last chunk, run the write
    if len(args) > 1:
        memoize_write(args)

    # Un-Monkey-patch
    args[0].write = args[0]._write
    args[0].finish = args[0]._finish

    # Remove the monkey patched attributes
    del args[0]._write
    del args[0]._finish

    # Call the RequestHandler.finish
    args[0].finish()


# Cache Decorator
def memoize(method):

    @wraps(method)
    def wrapper(*args, **kwargs):

        # Our module wide local_cache
        global local_cache

        if not hasattr(args[0], 'write'):
            raise AttributeError("Could not find the ")

        # Get the class name for the key
        key = repr(args[0])

        # Add the arguments to the key
        for value in args[1:]:
            key += ':%s' % str(value)

        debug('memoize: %s' % key)

        # See if the key is in cache and if so, send it
        if key in local_cache:
            debug('memoize hit: %s' % key)
            return self.finish(local_cache[key])

        # Assign our key
        args[0].tinman_memoize_key = key

        # Monkey-patch the write and finish functions
        args[0]._write = args[0].write
        args[0]._finish = args[0].finish
        args[0].write = memoize_write
        args[0].finish = memoize_finish

        # Return the value
        return method(*args, **kwargs)

    return wrapper


def flush():
    """
    Flush all of the attributes in the cache
    """
    global local_cache
    local_cache = dict()

########NEW FILE########
__FILENAME__ = whitelist
"""
Tinman Whitelist Module

"""
import ipaddr
from tornado import web
import types


def whitelisted(argument=None):
    """Decorates a method requiring that the requesting IP address is
    whitelisted. Requires a whitelist value as a list in the
    Application.settings dictionary. IP addresses can be an individual IP
    address or a subnet.

    Examples:
        ['10.0.0.0/8','192.168.1.0/24', '1.2.3.4/32']

    :param list argument: List of whitelisted ip addresses or blocks
    :raises: web.HTTPError
    :raises: ValueError
    :rtype: any

    """
    def is_whitelisted(remote_ip, whitelist):
        """Check to see if an IP address is whitelisted.

        :param str ip_address: The IP address to check
        :param list whitelist: The whitelist to check against
        :rtype: bool

        """
        # Convert the ip into a long int version of the ip address
        user_ip = ipaddr.IPv4Address(remote_ip)

        # Loop through the ranges in the whitelist and check
        if any([user_ip in ipaddr.IPv4Network(entry) for entry in whitelist]):
            return True

        return False

    # If the argument is a function then there were no parameters
    if type(argument) is types.FunctionType:

        def wrapper(self, *args, **kwargs):
            """Check the whitelist against our application.settings dictionary
            whitelist key.

            :rtype: any
            :raises: web.HTTPError

            """
            # Validate we have a configured whitelist
            if 'whitelist' not in self.application.settings:
                raise ValueError('whitelist not found in Application.settings')

            # If the IP address is whitelisted, call the wrapped function
            if is_whitelisted(self.request.remote_ip,
                              self.application.settings['whitelist']):

                # Call the original function, IP is whitelisted
                return argument(self, *args, **kwargs)

            # The ip address was not in the whitelist
            raise web.HTTPError(403)

        # Return the wrapper method
        return wrapper

    # They passed in string or list?
    else:

        # Convert a single ip address to a list
        if isinstance(argument, str):
            argument = [argument]

        # Make sure it's a list
        elif not isinstance(argument, list):
            raise ValueError('whitelisted requires no parameters or '
                             'a string or list')

        def argument_wrapper(method):
            """Wrapper for a method passing in the IP addresses that constitute
            the whitelist.

            :param method method: The method being wrapped
            :rtype: any
            :raises: web.HTTPError

            """
            def validate(self, *args, **kwargs):
                """
                Validate the ip address agross the list of ip addresses
                passed in as a list
                """
                if is_whitelisted(self.request.remote_ip, argument):

                    # Call the original function, IP is whitelisted
                    return method(self, *args, **kwargs)

                # The ip address was not in the whitelist
                raise web.HTTPError(403)

            # Return the validate method
            return validate

        # Return the wrapper method
        return argument_wrapper

########NEW FILE########
__FILENAME__ = example
"""
Tinman Test Application

"""
from datetime import date
import logging
from tornado import web

from tinman.handlers import SessionRequestHandler
from tinman import __version__

LOGGER = logging.getLogger(__name__)


CONFIG = {'Application': {'debug': True,
                          'xsrf_cookies': False},
          'HTTPServer': {'no_keep_alive': False,
                         'ports': [8000],
                         'xheaders': False},
          'Logging': {'loggers': {'tinman': {'propagate': True,
                                            'level': 'DEBUG'}},
                      'formatters': {'verbose': ('%(levelname) -10s %(asctime)s'
                                                 ' %(name) -30s %(funcName) '
                                                 '-25s: %(message)s')},
                      'filters': {'tinman': 'tinman'},
                      'handlers': {'console': {'formatter': 'verbose',
                                               'filters': ['tinman'],
                                               'debug_only': True,
                                               'class': 'logging.StreamHandler',
                                               'level': 'DEBUG'},
                                   'file': {'delay': False,
                                            'mode': 'a',
                                            'encoding': 'UTF-8',
                                            'formatter': 'verbose',
                                            'filters': ['tinman'],
                                            'class': 'logging.FileHandler',
                                            'filename': '/tmp/tinman.log'}}},
          'Routes': [("/", "tinman.test.DefaultHandler")]}


class Handler(SessionRequestHandler):

    @web.asynchronous
    def get(self, *args, **kwargs):
        """Example HTTP Get response method.

        :param args: positional args
        :param kwargs: keyword args

        """
        self.session.username = 'gmr'

        session = self.session.as_dict()
        if session['last_request_at']:
            session['last_request_at'] = str(date.fromtimestamp(
                                             session['last_request_at']))

        # Send a JSON string for our test
        self.write({'message': 'Hello World',
                    'request': {'method': self.request.method,
                                'protocol': self.request.protocol,
                                'path': self.request.path,
                                'query': self.request.query,
                                'remote_ip': self.request.remote_ip,
                                'version': self.request.version},
                    'session': session,
                    'tinman': {'version':  __version__}})
        self.finish()

########NEW FILE########
__FILENAME__ = exceptions
"""
Tinman Exceptions

"""

class ConfigurationException(Exception):
    def __repr__(self):
        return 'Configuration for %s is missing or invalid' % self.args[0]


class NoRoutesException(Exception):
    def __repr__(self):
        return 'No routes could be configured'
########NEW FILE########
__FILENAME__ = base
"""
Base Tinman RequestHandlers

"""
import datetime
from tornado import gen
import json
import logging
from tornado import escape
from tornado import web

from tinman import config
from tinman import session

LOGGER = logging.getLogger(__name__)

HEAD = 'HEAD'
GET = 'GET'
POST = 'POST'
DELETE = 'DELETE'
PATCH = 'PATCH'
PUT = 'PUT'
OPTIONS = 'OPTIONS'


class RequestHandler(web.RequestHandler):
    """A base RequestHandler that adds the following functionality:

    - If sending a dict, checks the user-agent string for curl and sends an
      indented, sorted human-readable JSON snippet
    - Toggles the ensure_ascii flag in json.dumps
    - Overrides the default behavior for unimplemented methods to instead set
    the status and look to the allow object attribute for methods that can be
    allowed. This is useful for when using NewRelic since the newrelic agent
    will catch the normal exceptions thrown as errors and trigger false alerts.

    To use, do something like::

        from tinman import handlers

        class Handler(handlers.RequestHandler):

            ALLOW = [handlers.GET, handlers.POST]

            def get(self, *args, **kwargs):
                self.write({'foo': 'bar'})

            def post(self, *args, **kwargs):
                self.write({'message': 'Saved'})

    """
    ALLOW = []
    JSON = 'application/json'

    def __init__(self, application, request, **kwargs):
        super(RequestHandler, self).__init__(application, request, **kwargs)

    def _method_not_allowed(self):
        self.set_header('Allow', ', '.join(self.ALLOW))
        self.set_status(405, 'Method Not Allowed')
        self.finish()

    @web.asynchronous
    def head(self, *args, **kwargs):
        """Implement the HTTP HEAD method

        :param list args: Positional arguments
        :param dict kwargs: Keyword arguments

        """
        self._method_not_allowed()

    @web.asynchronous
    def get(self, *args, **kwargs):
        """Implement the HTTP GET method

        :param list args: Positional arguments
        :param dict kwargs: Keyword arguments

        """
        self._method_not_allowed()

    @web.asynchronous
    def post(self, *args, **kwargs):
        """Implement the HTTP POST method

        :param list args: Positional arguments
        :param dict kwargs: Keyword arguments

        """
        self._method_not_allowed()

    @web.asynchronous
    def delete(self, *args, **kwargs):
        """Implement the HTTP DELETE method

        :param list args: Positional arguments
        :param dict kwargs: Keyword arguments

        """
        self._method_not_allowed()

    @web.asynchronous
    def patch(self, *args, **kwargs):
        """Implement the HTTP PATCH method

        :param list args: Positional arguments
        :param dict kwargs: Keyword arguments

        """
        self._method_not_allowed()

    @web.asynchronous
    def put(self, *args, **kwargs):
        """Implement the HTTP PUT method

        :param list args: Positional arguments
        :param dict kwargs: Keyword arguments

        """
        self._method_not_allowed()

    @web.asynchronous
    def options(self, *args, **kwargs):
        """Implement the HTTP OPTIONS method

        :param list args: Positional arguments
        :param dict kwargs: Keyword arguments

        """
        self.set_header('Allow', ', '.join(self.ALLOW))
        self.set_status(204)
        self.finish()

    def prepare(self):
        """Prepare the incoming request, checking to see the request is sending
        JSON content in the request body. If so, the content is decoded and
        assigned to the json_arguments attribute.

        """
        super(RequestHandler, self).prepare()
        if self.request.headers.get('content-type', '').startswith(self.JSON):
            self.request.body = escape.json_decode(self.request.body)

    def write(self, chunk):
        """Writes the given chunk to the output buffer. Checks for curl in the
        user-agent and if set, provides indented output if returning JSON.

        To write the output to the network, use the flush() method below.

        If the given chunk is a dictionary, we write it as JSON and set
        the Content-Type of the response to be ``application/json``.
        (if you want to send JSON as a different ``Content-Type``, call
        set_header *after* calling write()).

        :param mixed chunk: The string or dict to write to the client

        """
        if self._finished:
            raise RuntimeError("Cannot write() after finish().  May be caused "
                               "by using async operations without the "
                               "@asynchronous decorator.")
        if isinstance(chunk, dict):
            options = {'ensure_ascii': False}
            if 'curl' in self.request.headers.get('user-agent'):
                options['indent'] = 2
                options['sort_keys'] = True
            chunk = json.dumps(chunk, **options).replace("</", "<\\/") + '\n'
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        self._write_buffer.append(web.utf8(chunk))



class SessionRequestHandler(RequestHandler):
    """A RequestHandler that adds session support. For configuration details
    see the tinman.session module.

    """
    SESSION_COOKIE_NAME = 'session'
    SESSION_DURATION = 3600

    @gen.coroutine
    def on_finish(self):
        """Called by Tornado when the request is done. Update the session data
        and remove the session object.

        """
        super(SessionRequestHandler, self).on_finish()
        LOGGER.debug('Entering SessionRequestHandler.on_finish: %s',
                     self.session.id)
        self.session.last_request_at = self.current_epoch()
        self.session.last_request_uri = self.request.uri
        if self.session.dirty:
            result = yield self.session.save()
            LOGGER.debug('on_finish yield save: %r', result)
        self.session = None
        LOGGER.debug('Exiting SessionRequestHandler.on_finish: %r',
                     self.session)

    def current_epoch(self):
        return int(datetime.datetime.now().strftime('%s'))

    @gen.coroutine
    def start_session(self):
        """Start the session. Invoke in your @gen.coroutine wrapped prepare
        method like::

            result = yield gen.Task(self.start_session)

        :rtype: bool

        """
        self.session = self._session_start()
        result = yield gen.Task(self.session.fetch)
        self._set_session_cookie()
        if not self.session.get('ip_address'):
            self.session.ip_address = self.request.remote_ip
        self._last_values()
        raise gen.Return(result)

    @gen.coroutine
    def prepare(self):
        """Prepare the session, setting up the session object and loading in
        the values, assigning the IP address to the session if it's an new one.

        """
        super(SessionRequestHandler, self).prepare()
        result = yield gen.Task(self.start_session)
        LOGGER.debug('Exiting SessionRequestHandler.prepare: %r', result)

    @property
    def _cookie_expiration(self):
        """Return the expiration timestamp for the session cookie.

        :rtype: datetime

        """
        value = (datetime.datetime.utcnow() +
                 datetime.timedelta(seconds=self._session_duration))
        LOGGER.debug('Cookie expires: %s', value.isoformat())
        return value

    @property
    def _cookie_settings(self):
        return self.settings['session'].get('cookie', dict())

    def _last_values(self):
        """Always carry last_request_uri and last_request_at even if the last_*
        values are null.

        """
        if not self.session.get('last_request_uri'):
            self.session.last_request_uri = None
        self.session.last_request_at = self.session.get('last_request_at', 0)

    @property
    def _session_class(self):
        if self._session_settings.get('name') == config.FILE:
            return session.FileSession
        elif self._session_settings.get('name') == config.REDIS:
            return session.RedisSession
        else:
            raise ValueError('Unknown adapter type')

    @property
    def _session_cookie_name(self):
        """Return the session cookie name, defaulting to the class default

        :rtype: str

        """
        return self._cookie_settings.get(config.NAME, self.SESSION_COOKIE_NAME)

    @property
    def _session_duration(self):
        """Return the session duration from config or the default value

        :rtype: int

        """
        return self._cookie_settings.get(config.DURATION, self.SESSION_DURATION)

    @property
    def _session_id(self):
        """Returns the session id from the session cookie.

        :rtype: str

        """
        return self.get_secure_cookie(self._session_cookie_name, None)

    @property
    def _session_settings(self):
        return self.settings['session'].get('adapter', dict())

    def _session_start(self):
        """Return an instance of the proper session object.

        :rtype: Session

        """
        return self._session_class(self._session_id,
                                   self._session_duration,
                                   self._session_settings)
    def _set_session_cookie(self):
        """Set the session data cookie."""
        LOGGER.debug('Setting session cookie for %s', self.session.id)
        self.set_secure_cookie(name=self._session_cookie_name,
                               value=self.session.id,
                               expires=self._cookie_expiration)

########NEW FILE########
__FILENAME__ = heapy
"""The heapy handler gives information about the process's memory stack. It is
slow and will block any asynchronous activity and should be used for debugging
purposes only.

For best results, connect directly to the port of the process you would like to
check.

"""
import guppy
import logging
import re
from tornado import web

LOGGER = logging.getLogger(__name__)
MAX_REFERRER_DEPTH = 4
MAX_ROW_COUNT_PER_LEVEL = 5

REPORT_TOTAL = re.compile('^Partition of a set of ([\d]+) objects\.'
                          ' Total size = ([\d]+) bytes\.')
REPORT_HEADER = re.compile('^ Index  Count   %     Size   % Cumulative  % (.*)',
                           re.MULTILINE)
REPORT_ITEMS = re.compile('^\s+([\d]+)\s+([\d]+)\s+([\d]+)\s+([\d]+)\s+'
                          '([\d]+)\s+([\d]+)\s+([\d]+)\s+(.*)', re.MULTILINE)


def get_report_data(heapy_obj, depth=1):
    LOGGER.debug('Getting report data at depth %i', depth)
    report = {'total_objects': 0, 'total_bytes': 0, 'rows': []}
    totals = REPORT_TOTAL.findall(str(heapy_obj))
    if totals:
        report['total_objects'], report['total_bytes'] = (int(totals[0][0]),
                                                          int(totals[0][1]))
    items = REPORT_ITEMS.findall(str(heapy_obj))
    for index, row in enumerate(items):
        report['rows'].append({'item': row[-1],
                               'count': {'value': int(row[1]),
                                         'percent': int(row[2])},
                               'size': {'value': int(row[3]),
                                        'percent': int(row[4])},
                               'cumulative': {'value': int(row[5]),
                                              'percent': int(row[6])}})
        if depth < MAX_REFERRER_DEPTH:
            try:
                rows = len(heapy_obj.byrcs[index])
            except IndexError:
                LOGGER.warning('Could not process item at index %i', index)
                report['rows'][index]['error'] = 'Could not get referrers'
                continue
            if rows > MAX_ROW_COUNT_PER_LEVEL:
                rows = MAX_ROW_COUNT_PER_LEVEL
            for referrer_index in range(0, rows):
                report['rows'][index]['referrers'] =\
                    get_report_data(heapy_obj.byrcs[index].referrers.byrcs,
                                    depth + 1)

    header = REPORT_HEADER.findall(str(heapy_obj))
    if header:
        report['title'] = header[0]
    return report


class HeapyRequestHandler(web.RequestHandler):
    """Dumps the heap to a text/plain output."""

    def initialize(self):
        self._heapy = guppy.hpy()

    def get(self):
        heap = self._heapy.heap()
        report = get_report_data(heap.byrcs)
        self.write(report)
        self.finish()

########NEW FILE########
__FILENAME__ = mixins
"""
Mixin handlers adding various different types of functionality

"""
import socket
from tornado import escape
from tornado import gen
import logging
from tornado import web

from tinman.handlers import base
from tinman import config

LOGGER = logging.getLogger(__name__)


class StatsdMixin(base.RequestHandler):
    """Increments a counter and adds timing data to statsd for each request.

    Example key format:

        tornado.web.RequestHandler.GET.200

    Additionally adds methods for talking to statsd via the request handler.

    By default, it will talk to statsd on localhost. To configure the statsd
    server address, add a statsd staza to the application configuration:

    Application:
      statsd:
        host: 192.168.1.2
        port: 8125
    
    """
    STATSD_HOST = '127.0.0.1'
    STATSD_PORT = 8125

    def __init__(self, application, request, **kwargs):
        super(StatsdMixin, self).__init__(application, request, **kwargs)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @property
    def _statsd_address(self):
        """Return a tuple of host and port for the statsd server to send
        stats to.

        :return: tuple(host, port)

        """
        return (self.application.settings.get('statsd',
                                              {}).get('host',
                                                      self.STATSD_HOST),
                self.application.settings.get('statsd',
                                              {}).get('port',
                                                      self.STATSD_PORT))

    def _statsd_send(self, value):
        """Send the specified value to the statsd daemon via UDP without a
        direct socket connection.

        :param str value: The properly formatted statsd counter value

        """
        self.socket.sendto(value, self._statsd_address)

    def on_finish(self):
        """Invoked once the request has been finished. Increment a counter
        created in the format:

            package[.module].Class.METHOD.STATUS
            tornado.web.RequestHandler.GET.200

        """
        super(StatsdMixin, self).on_finish()
        key = '%s.%s.%s.%s' % (self.__module__,
                               self.__class__.__name__,
                               self.request.method, self._status_code)
        LOGGER.info('Processing %s', key)
        self.statsd_incr(key)
        self.statsd_add_timing(key, self.request.request_time() * 1000)

    def statsd_incr(self, name, value=1):
        """Increment a statsd counter by the specified value.

        :param str name: The counter name to increment
        :param int|float value: The value to increment by

        """
        self._statsd_send('%s:%s|c' % (name, value))

    def statsd_set_gauge(self, name, value):
        """Set a gauge in statsd for the specified name and value.

        :param str name: The gauge name to increment
        :param int|float value: The gauge value

        """
        self._statsd_send('%s:%s|g' % (name, value))

    def statsd_add_timing(self, name, value):
        """Add a time value in statsd for the specified name

        :param str name: The timing name to add a sample to
        :param int|float value: The time value

        """
        self._statsd_send('%s:%s|ms' % (name, value))


class RedisMixin(base.RequestHandler):
    """This request web will connect to Redis on initialize if the
    connection is not previously set. Uses the asynchronous tornadoredis
    library.

    Example use:

        @web.asynchronous
        @gen.engine
        def get(self, *args, **kwargs):
            value = self.redis.get('foo')

    """
    _redis_client = None
    _REDIS_HOST = 'localhost'
    _REDIS_PORT = 6379
    _REDIS_DB = 0

    @gen.coroutine
    def prepare(self):
        """Prepare RequestHandler requests, ensuring that there is a
        connected tornadoredis.Client object.

        """
        self._ensure_redis_client()
        super(RedisMixin, self).prepare()

    @property
    def redis(self):
        """Return a handle to the active redis client.

        :rtype: tornadoredis.Client

        """
        self._ensure_redis_client()
        return RedisMixin._redis_client

    def _ensure_redis_client(self):
        """Ensure the redis client has been created."""
        if not RedisMixin._redis_client:
            RedisMixin._redis_client = self._new_redis_client()

    def _new_redis_client(self):
        """Create a new redis client and assign it the class _redis_client
        attribute for reuse across requests.

        :rtype: tornadoredis.Client()

        """
        if 'tornadoredis' not in globals():
            import tornadoredis
        kwargs = self._redis_connection_settings()
        LOGGER.info('Connecting to %(host)s:%(port)s DB %(selected_db)s',
                    kwargs)
        return tornadoredis.Client(**kwargs)

    def _redis_connection_settings(self):
        """Return a dictionary of redis connection settings.

        """
        return {config.HOST: self.settings.get(config.HOST, self._REDIS_HOST),
                config.PORT: self.settings.get(config.PORT, self._REDIS_PORT),
                'selected_db': self.settings.get(config.DB, self._REDIS_DB)}


class ModelAPIMixin(base.RequestHandler):
    """The Model API Request Handler provides a simple RESTful API interface
    for access to Tinman data models.

    Set the MODEL attribute to the Model class for the web for basic,
    unauthenticated GET, DELETE, PUT, and POST behavior where PUT is

    """
    ACCEPT = [base.GET, base.HEAD, base.DELETE, base.PUT, base.POST]
    MODEL = None

    # Data attributes to replace in the model
    REPLACE_ATTRIBUTES = {'password': bool}

    # Data attributes to strip from the model
    STRIP_ATTRIBUTES = []

    # Core Tornado Methods

    def initialize(self):
        super(ModelAPIMixin, self).initialize()
        self.model = None

    @web.asynchronous
    @gen.engine
    def delete(self, *args, **kwargs):
        """Handle delete of an item

        :param args:
        :param kwargs:

        """
        # Create the model and fetch its data
        self.model = self.get_model(kwargs.get('id'))
        result = yield self.model.fetch()

        # If model is not found, return 404
        if not result:
            self.not_found()
            return

        # Stub to check for delete permissions
        if not self.has_delete_permission():
            self.permission_denied()
            return

        # Delete the model from its storage backend
        self.model.delete()

        # Set the status to request processed, no content returned
        self.set_status(204)
        self.finish()

    @web.asynchronous
    @gen.engine
    def head(self, *args, **kwargs):
        """Handle HEAD requests for the item

        :param args:
        :param kwargs:

        """
        # Create the model and fetch its data
        self.model = self.get_model(kwargs.get('id'))
        result = yield self.model.fetch()

        # If model is not found, return 404
        if not result:
            self.not_found()
            return

        # Stub to check for read permissions
        if not self.has_read_permission():
            self.permission_denied()
            return

        # Add the headers (etag, content-length), set the status
        self.add_headers()
        self.set_status(200)
        self.finish()

    @web.asynchronous
    @gen.engine
    def get(self, *args, **kwargs):
        """Handle reading of the model

        :param args:
        :param kwargs:

        """
        # Create the model and fetch its data
        self.model = self.get_model(kwargs.get('id'))
        result = yield self.model.fetch()

        # If model is not found, return 404
        if not result:
            LOGGER.debug('Not found')
            self.not_found()
            return

        # Stub to check for read permissions
        if not self.has_read_permission():
            LOGGER.debug('Permission denied')
            self.permission_denied()
            return

        # Add the headers and return the content as JSON
        self.add_headers()
        self.finish(self.model_json())

    @web.asynchronous
    @gen.engine
    def post(self, *args, **kwargs):
        """Handle creation of an item.

        :param args:
        :param kwargs:

        """
        self.initialize_post()

        # Don't allow the post if the poster does not have permission
        if not self.has_create_permission():
            LOGGER.debug('Does not have write_permission')
            self.set_status(403, self.status_message('Creation Forbidden'))
            self.finish()
            return

        result = yield self.model.save()
        if result:
            self.set_status(201, self.status_message('Created'))
            self.add_headers()
            self.finish(self.model.as_dict())
        else:
            self.set_status(507, self.status_message('Creation Failed'))
            self.finish()

    @web.asynchronous
    @gen.engine
    def put(self, *args, **kwargs):
        """Handle updates of an item.

        :param args:
        :param kwargs:

        """
        self.initialize_put(kwargs.get('id'))

        if not self.has_update_permission():
            self.set_status(403, self.status_message('Creation Forbidden'))
            self.finish()
            return

        for key, value in self.model.items():
            if self.json_arguments.get(key) != value:
                self.model.set(key, self.json_arguments.get(key))

        if not self.model.dirty:
            self.set_status(431, self.status_message('No changes made'))
            self.finish(self.model.as_dict())
            return

        result = yield self.model.save()
        if result:
            self.set_status(200, self.status_message('Updated'))
        else:
            self.set_status(507, self.status_message('Update Failed'))
        self.add_headers()
        self.finish(self.model.as_dict())

    # Methods to Extend

    def has_create_permission(self):
        """Extend this method to implement custom permission checking
        for your data APIs.

        :rtype: bool

        """
        return True

    def has_delete_permission(self):
        """Extend this method to implement custom permission checking
        for your data APIs.

        :rtype: bool

        """
        return True

    def has_read_permission(self):
        """Extend this method to implement custom permission checking
        for your data APIs.

        :rtype: bool

        """
        return True

    def has_update_permission(self):
        """Extend this method to implement custom permission checking
        for your data APIs.

        :rtype: bool

        """
        return True

    def initialize_post(self):
        """Invoked by the ModelAPIRequestHandler.post method prior to taking
        any action.

        """
        self.model = self.get_model()
        for key in self.model.keys():
            self.model.set(key, self.json_arguments.get(key))

    def initialize_put(self, item_id):
        """Invoked by the ModelAPIRequestHandler.put method prior to taking
        any action.

        """
        self.model = self.get_model(item_id)

    # Model API Methods

    def add_etag(self):
        self.set_header('Etag', '"%s"' % self.model.sha1())

    def add_content_length(self):
        self.set_header('Content-Length', len(self.model_json()))

    def add_headers(self):
        self.add_etag()
        self.add_content_length()

    def get_model(self, *args, **kwargs):
        return self.MODEL(*args, **kwargs)

    def model_json(self):
        output = self.model.as_dict()
        for key in self.REPLACE_ATTRIBUTES:
            output[key] = self.REPLACE_ATTRIBUTES[key](output[key])
        for key in self.STRIP_ATTRIBUTES:
            del output[key]
        return web.utf8(escape.json_encode(output))

    def not_found(self):
        self.set_status(404, self.status_message('Not Found'))
        self.finish()

    def permission_denied(self, message=None):
        self.set_status(403, self.status_message(message or
                                                 'Permission Denied'))
        self.finish()

    def status_message(self, message):
        return self.model.__class__.__name__ + ' ' + message


class RedisModelAPIMixin(ModelAPIMixin, RedisMixin):
    """Use for Model API support with Redis"""
    def get_model(self, *args, **kwargs):
        kwargs['redis_client'] = RedisMixin._redis_client
        return self.MODEL(*args, **kwargs)

########NEW FILE########
__FILENAME__ = rabbitmq
"""The RabbitMQRequestHandler wraps RabbitMQ use into a request handler, with
methods to speed the development of publishing RabbitMQ messages.

Example configuration:

    Application:
      rabbitmq:
        host: rabbitmq1
        virtual_host: my_web_app
        username: tinman
        password: tornado

"""
from tornado import gen
import logging
import pika
from pika.adapters import tornado_connection
from tornado import web

LOGGER = logging.getLogger(__name__)

from tinman import exceptions

message_stack = list()
pending_rabbitmq_connection = None
rabbitmq_connection = None


class RabbitMQRequestHandler(web.RequestHandler):
    """The request handler will connect to RabbitMQ on the first request,
    buffering any messages that need to be published until the Channel to
    RabbitMQ is opened, sending the stack of previously buffered messages at
    that time. If RabbitMQ closes it's connection to the app at any point, a
    connection attempt will be made on the next request.

    Expects configuration in the YAML file under a "rabbitmq" node. All of the
    configuration values are optional but username and password:

        host: Hostname, defaults to localhost if omitted
        port: RabbitMQ port, defaults to 5672 if omitted
        virtual_host: The virtual host, defaults to / if omitted
        username: The username to connect with
        password: The password to connect with
        channel_max: Maximum number of channels to allow, defaults to 0
        frame_max: The maximum byte size for an AMQP frame, defaults to 131072
        heartbeat_interval: Heartbeat interval, defaults to 0 (Off)
        ssl: Enable SSL, defaults to False
        ssl_options: Arguments passed to ssl.wrap_socket as described at
                     http://docs.python.org/dev/library/ssl.html
        connection_attempts: Maximum number of retry attempts, defaults to 1
        retry_delay: Time to wait in seconds between attempts, defaults to 2
        socket_timeout: Use for high latency networks, defaults to 0.25
        locale: Set the connection locale value, defaults to en_US

    """
    CHANNEL = 'rabbitmq_channel'
    CONNECTION = 'rabbitmq_connection'

    def _add_to_publish_stack(self, exchange, routing_key, message, properties):
        """Temporarily add the message to the stack to publish to RabbitMQ

        :param str exchange: The exchange to publish to
        :param str routing_key: The routing key to publish with
        :param str message: The message body
        :param pika.BasicProperties: The message properties

        """
        global message_stack
        message_stack.append((exchange, routing_key, message, properties))

    def _connect_to_rabbitmq(self):
        """Connect to RabbitMQ and assign a local attribute"""
        global pending_rabbitmq_connection, rabbitmq_connection
        if not rabbitmq_connection:
            LOGGER.info('Creating a new RabbitMQ connection')
            pending_rabbitmq_connection = self._new_rabbitmq_connection()

    def _new_message_properties(self, content_type=None, content_encoding=None,
                                headers=None, delivery_mode=None, priority=None,
                                correlation_id=None, reply_to=None,
                                expiration=None, message_id=None,
                                timestamp=None, message_type=None, user_id=None,
                                app_id=None):
        """Create a BasicProperties object, with the properties specified

        :param str content_type: MIME content type
        :param str content_encoding: MIME content encoding
        :param dict headers: Message header field table
        :param int delivery_mode: Non-persistent (1) or persistent (2)
        :param int priority: Message priority, 0 to 9
        :param str correlation_id: Application correlation identifier
        :param str reply_to: Address to reply to
        :param str expiration: Message expiration specification
        :param str message_id: Application message identifier
        :param int timestamp: Message timestamp
        :param str message_type: Message type name
        :param str user_id: Creating user id
        :param str app_id: Creating application id
        :rtype: pika.BasicProperties

        """
        return pika.BasicProperties(content_type, content_encoding, headers,
                                    delivery_mode, priority, correlation_id,
                                    reply_to, expiration, message_id, timestamp,
                                    message_type, user_id, app_id)

    def _new_rabbitmq_connection(self):
        """Return a connection to RabbitMQ via the pika.Connection object.
        When RabbitMQ is connected, on_rabbitmq_open will be called.

        :rtype: pika.adapters.tornado_connection.TornadoConnection

        """
        return tornado_connection.TornadoConnection(self._rabbitmq_parameters,
                                                    self.on_rabbitmq_conn_open)

    def _publish_deferred_messages(self):
        """Called when pika is connected and has a channel open to publish
        any requests buffered.

        """
        global message_stack
        if not self._rabbitmq_is_closed and message_stack:
            LOGGER.info('Publishing %i deferred message(s)', len(message_stack))
            while message_stack:
                self._publish_message(*message_stack.pop())

    def _publish_message(self, exchange, routing_key, message, properties):
        """Publish the message to RabbitMQ

        :param str exchange: The exchange to publish to
        :param str routing_key: The routing key to publish with
        :param str message: The message body
        :param pika.BasicProperties: The message properties

        """
        if self._rabbitmq_is_closed or not self._rabbitmq_channel:
            LOGGER.warning('Temporarily buffering message to publish')
            self._add_to_publish_stack(exchange, routing_key,
                                       message, properties)
            return
        self._rabbitmq_channel.basic_publish(exchange, routing_key,
                                             message, properties)

    @property
    def _rabbitmq_config(self):
        """Return the RabbitMQ configuration dictionary.

        :rtype: dict

        """
        config = self.application.settings.get('rabbitmq')
        if not config:
            raise exceptions.ConfigurationException('rabbitmq')
        return config

    @property
    def _rabbitmq_channel(self):
        """Return the Pika channel from the tinman object assignment.

        :rtype: pika.channel.Channel

        """
        return getattr(self.application.attributes, self.CHANNEL, None)

    @property
    def _rabbitmq_is_closed(self):
        """Returns True if the pika connection to RabbitMQ is closed.

        :rtype: bool

        """
        global rabbitmq_connection
        return not rabbitmq_connection and not pending_rabbitmq_connection

    @property
    def _rabbitmq_parameters(self):
        """Return a pika ConnectionParameters object using the configuration
        from the configuration service. The configuration dictionary should
        match the parameters for pika.connection.ConnectionParameters and
        include an extra username and password variable.

        :rtype: pika.ConnectionParameters

        """
        kwargs = dict(self._rabbitmq_config)
        kwargs['credentials'] =  pika.PlainCredentials(kwargs['username'],
                                                       kwargs['password'])
        for key in ['username', 'password']:
            del kwargs[key]
        return pika.ConnectionParameters(**kwargs)

    def _set_rabbitmq_channel(self, channel):
        """Assign the channel object to the tinman global object.

        :param pika.channel.Channel channel: The pika channel

        """
        setattr(self.application.attributes, self.CHANNEL, channel)

    def on_rabbitmq_close(self, reply_code, reply_text):
        """Called when RabbitMQ has been connected to.

        :param int reply_code: The code for the disconnect
        :param str reply_text: The disconnect reason

        """
        global rabbitmq_connection
        LOGGER.warning('RabbitMQ has disconnected (%s): %s',
                       reply_code, reply_text)
        rabbitmq_connection = None
        self._set_rabbitmq_channel(None)
        self._connect_to_rabbitmq()

    def on_rabbitmq_conn_open(self, connection):
        """Called when RabbitMQ has been connected to.

        :param pika.connection.Connection connection: The pika connection

        """
        global pending_rabbitmq_connection, rabbitmq_connection
        LOGGER.info('RabbitMQ has connected')
        rabbitmq_connection = connection
        rabbitmq_connection.add_on_close_callback(self.on_rabbitmq_close)
        rabbitmq_connection.channel(self.on_rabbitmq_channel_open)
        pending_rabbitmq_connection = None

    def on_rabbitmq_channel_open(self, channel):
        """Called when the RabbitMQ accepts the channel open request.

        :param pika.channel.Channel channel: The channel opened with RabbitMQ

        """
        LOGGER.info('Channel %i is opened for communication with RabbitMQ',
                    channel.channel_number)
        self._set_rabbitmq_channel(channel)
        self._publish_deferred_messages()

    @gen.coroutine
    def prepare(self):
        """Prepare the handler, ensuring RabbitMQ is connected or start a new
        connection attempt.

        """
        super(RabbitMQRequestHandler, self).prepare()
        if self._rabbitmq_is_closed:
            self._connect_to_rabbitmq()

########NEW FILE########
__FILENAME__ = redis_handlers
"""
Deprecated and moved into tornado.handlers.mixins

"""
import warnings
warnings.warn('tinman.handlers.redis_handlers moved to tinman.handlers.mixins',
              DeprecationWarning, stacklevel=2)

from tinman.handlers.mixins import RedisMixin as RedisRequestHandler
from tinman.handlers.mixins import RedisMixin as AsynchronousRedisRequestHandler

########NEW FILE########
__FILENAME__ = session
"""
Deprecated and moved into tornado.handlers.base

"""
import warnings
warnings.warn('tinman.handlers.session moved to tinman.handlers.base',
              DeprecationWarning, stacklevel=2)

from tinman.handlers.base import SessionRequestHandler

########NEW FILE########
__FILENAME__ = couchdb
"""This module is deprecated"""
import warnings

warnings.warn('tinman.loaders.couchdb moved to tinman.couchdb',
              DeprecationWarning, stacklevel=2)

from tinman import couchdb

########NEW FILE########
__FILENAME__ = mapping
"""
A generic mapping object that allows access to attributes and via getters and
setters.

"""
import collections
import inspect
import json


class Mapping(collections.Mapping):
    """A generic data object that provides access to attributes via getters
    and setters, built in serialization via JSON, iterator methods
    and other Mapping methods.

    """
    # Flag indicating the mapping has changed attributes
    _dirty = False

    def __init__(self, **kwargs):
        """Assign all kwargs passed in as attributes of the object."""
        self.from_dict(kwargs)

    def __contains__(self, item):
        """Check to see if the attribute name passed in exists.

        :param str item: The attribute name

        """
        return item in self.keys()

    def __eq__(self, other):
        """Test another mapping for equality against this one

        :param mapping other: The mapping to test against this one
        :rtype: bool

        """
        if not isinstance(other, self.__class__):
            return False
        return all([getattr(self, k) == getattr(other, k)
                    for k in self.keys()])

    def __delitem__(self, key):
        """Delete the attribute from the mapping.

        :param str key: The attribute name
        :raises: KeyError

        """
        if key not in self.keys():
            raise KeyError(key)
        delattr(self, key)

    def __getitem__(self, item):
        """Get an item from the mapping.

        :param str item: The attribute name
        :rtype: mixed
        :raises: KeyError

        """
        if item not in self.keys():
            raise KeyError(item)
        return getattr(self, item)

    def __hash__(self):
        """Return the hash value of the items

        :rtype: int

        """
        return hash(self.items())

    def __iter__(self):
        """Iterate through the keys in the mapping object.

        :rtype: listiterator

        """
        return self.iterkeys()

    def __len__(self):
        """Return the number of attributes in this mapping object.

        :rtype: int

        """
        return len(self.keys())

    def __ne__(self, other):
        """Test two mappings for inequality.

        :param mapping other: The mapping to test against this one
        :rtype: bool

        """
        return not self.__eq__(other)

    def __repr__(self):
        """Mapping object representation

        :rtype: str

        """
        return '<%s.%s keys="%s">' % (__name__, self.__class__.__name__,
                                      ','.join(self.keys()))

    def __setattr__(self, key, value):
        """Set an attribute on the object flipping the indicator

        :param str key: The attribute name
        :param mixed value: The value to set

        """
        if key[0] != '_' and not self._dirty:
            self._dirty = True
        super(Mapping, self).__setattr__(key, value)

    def __setitem__(self, key, value):
        """Set an item in the mapping

        :param str key: The attribute name
        :param mixed value: The value to set

        """
        setattr(self, key, value)

    def as_dict(self):
        """Return this object as a dict value.

        :rtype: dict

        """
        return dict(self.items())

    def from_dict(self, values):
        """Assign the values from the dict passed in. All items in the dict
        are assigned as attributes of the object.

        :param dict values: The dictionary of values to assign to this mapping

        """
        for k in values.keys():
            setattr(self, k, values[k])

    def clear(self):
        """Clear all set attributes in the mapping.

        """
        for key in self.keys():
            delattr(self, key)

    @property
    def dirty(self):
        """Indicate if the mapping has changes from it's initial state

        :rtype: bool

        """
        return self._dirty

    def dumps(self):
        """Return a JSON serialized version of the mapping.

        :rtype: str|unicode

        """
        return json.dumps(self.as_dict(), encoding='utf-8', ensure_ascii=False)

    def loads(self, value):
        """Load in a serialized value, overwriting any previous values.

        :param str|unicode value: The serialized value

        """
        self.from_dict(json.loads(value, encoding='utf-8'))

    def keys(self):
        """Return a list of attribute names for the mapping.

        :rtype: list

        """
        return sorted([k for k in dir(self) if
                       k[0:1] != '_' and k != 'keys' and not k.isupper() and
                       not inspect.ismethod(getattr(self, k)) and
                       not (hasattr(self.__class__, k) and
                            isinstance(getattr(self.__class__, k),
                                       property)) and
                       not isinstance(getattr(self, k), property)])

    def get(self, key, default=None):
        """Get the value of key, passing in a default value if it is not set.

        :param str key: The attribute to get
        :param mixed default: The default value
        :rtype: mixed

        """
        return getattr(self, key, default)

    def iterkeys(self):
        """Iterate through the attribute names for this mapping.

        :rtype: listiterator

        """
        return iter(self.keys())

    def iteritems(self):
        """Iterate through a list of the attribute names and their values.

        :rtype: listiterator

        """
        return iter(self.items())

    def itervalues(self):
        """Iterate through a list of the attribute values for this mapping.

        :rtype: listiterator

        """
        return iter(self.values())

    def items(self):
        """Return a list of attribute name and value tuples for this mapping.

        :rtype: list

        """
        return [(k, getattr(self, k)) for k in self.keys()]

    def set(self, key, value):
        """Set the value of key.

        :param str key: The attribute to set
        :param mixed value: The value to set
        :raises: KeyError

        """
        return setattr(self, key, value)

    def values(self):
        """Return a list of values for this mapping in attribute name order.

        :rtype list

        """
        return [getattr(self, k) for k in self.keys()]

########NEW FILE########
__FILENAME__ = model
"""
Base tinman data models. The Model class is the base model that all other base
model classes extend. StorageModel defines the interfaces for models with built
in storage functionality.

Specific model storage base classes exist in the tornado.model package.

Example use::

    from tornado import gen
    from tornado import web
    from tinman.handlers import redis_handlers
    from tinman.model.redis import AsyncRedisModel


    class ExampleModel(AsyncRedisModel):
        name = None
        age = None
        location = None


    class Test(redis_handlers.AsynchronousRedisRequestHandler):

        @web.asynchronous
        @gen.engine
        def get(self, *args, **kwargs):
            model = ExampleModel(self.get_argument('id'),
                                 redis_client=self.redis)
            yield model.fetch()
            self.finish(model.as_dict())

        @web.asynchronous
        @gen.engine
        def post(self, *args, **kwargs):
            model = ExampleModel(self.get_argument('id', None),
                                 redis_client=self.redis)

            # Assign the posted values, requiring at least a name
            model.name = self.get_argument('name')
            model.age = self.get_argument('age', None)
            model.location = self.get_argument('location', None)

            # Save the model
            result = yield model.save()
            if result:
                self.set_status(201)
                self.finish(model.as_dict())
            else:
                raise web.HTTPError(500, 'Could not save model')

"""
import base64
from tornado import gen
import hashlib
import logging
import time
import uuid

from tinman import mapping

LOGGER = logging.getLogger(__name__)


class Model(mapping.Mapping):
    """A data object that provides attribute level assignment and retrieval of
    values, serialization and deserialization, the ability to load values from
    a dict and dump them to a dict, and Mapping and iterator behaviors.

    Base attributes are provided for keeping track of when the model was created
    and when it was last updated.

    If model attributes are passed into the constructor, they will be assigned
    to the model upon creation.

    :param str item_id: An id for the model, defaulting to a random UUID
    :param dict kwargs: Additional kwargs passed in

    """
    id = None
    created_at = None
    last_updated_at = None

    def __init__(self, item_id=None, **kwargs):
        """Create a new instance of the model, passing in a id value."""
        self.id = item_id or str(uuid.uuid4())
        self.created_at = int(time.time())
        self.last_updated_at = None

        # If values are in the kwargs that match the model keys, assign them
        for k in [k for k in kwargs.keys() if k in self.keys()]:
            setattr(self, k, kwargs[k])

    def from_dict(self, value):
        """Set the values of the model based upon the content of the passed in
        dictionary.

        :param dict value: The dictionary of values to assign to this model

        """
        for key in self.keys():
            setattr(self, key, value.get(key, None))

    def sha1(self):
        """Return a sha1 hash of the model items.

        :rtype: str

        """
        sha1 = hashlib.sha1(''.join(['%s:%s' % (k,v) for k,v in self.items()]))
        return str(sha1.hexdigest())


class StorageModel(Model):
    """A base model that defines the behavior for models with storage backends.

    :param str item_id: An id for the model, defaulting to a random UUID
    :param dict kwargs: Additional kwargs passed in

    """
    _new = True

    def __init__(self, item_id=None, **kwargs):
        super(StorageModel, self).__init__(item_id, **kwargs)
        if self.id:
            # It's no longer a new model, since it's a load
            self._new = False

            # Fetch the model values from storage
            self.fetch()

            # Toggle the changed back to false since it's an initial load
            self._dirty = False

    def delete(self):
        """Delete the data for the model from storage and assign the values.

        :raises: NotImplementedError

        """
        raise NotImplementedError("Must extend this method")

    def fetch(self):
        """Fetch the data for the model from storage and assign the values.

        :raises: NotImplementedError

        """
        raise NotImplementedError("Must extend this method")

    def save(self):
        """Store the model.

        :raises: NotImplementedError

        """
        raise NotImplementedError("Must extend this method")

    @property
    def is_new(self):
        """Return a bool indicating if it's a new item or not

        :rtype: bool

        """
        return self._new


class AsyncRedisModel(StorageModel):
    """A model base class that uses Redis for the storage backend. Uses the
    asynchronous tornadoredis client. If you assign a value to the _ttl
    attribute, that _ttl value will be used to set the expiraiton of the
    data in redis.

    Data is serialized with msgpack to cut down on the byte size, but due to
    the binary data, it is then base64 encoded. This is a win on large objects
    but a slight amount of overhead on smaller ones.

    :param str item_id: The id for the data item
    :param tornadoredis.Client: The already created tornadoredis client

    """
    _redis_client = None
    _saved = False
    _ttl = None

    def __init__(self, item_id=None, *args, **kwargs):
        if 'msgpack' not in globals():
            import msgpack
        self._serializer = msgpack
        if 'redis_client' not in kwargs:
            raise ValueError('redis_client must be passed in')
        self._redis_client = kwargs['redis_client']

        # The parent will attempt to fetch the value if item_id is set
        super(AsyncRedisModel, self).__init__(item_id, **kwargs)

    @property
    def _key(self):
        """Return a storage key for Redis that consists of the class name of
        the model and its id joined by :.

        :rtype: str

        """
        return '%s:%s' % (self.__class__.__name__, self.id)

    @gen.coroutine
    def delete(self):
        """Delete the item from storage

        :rtype: bool

        """
        result = gen.Task(self._redis_client.delete, self._key)
        raise gen.Return(bool(result))

    @gen.coroutine
    def fetch(self):
        """Fetch the data for the model from Redis and assign the values.

        :rtype: bool

        """
        raw = yield gen.Task(self._redis_client.get, self._key)
        if raw:
            self.loads(base64.b64decode(raw))
            raise gen.Return(True)
        raise gen.Return(False)

    @gen.coroutine
    def save(self):
        """Store the model in Redis.

        :rtype: bool

        """
        pipeline = self._redis_client.pipeline()
        pipeline.set(self._key, base64.b64encode(self.dumps()))
        if self._ttl:
            pipeline.expire(self._key, self._ttl)
        result = yield gen.Task(pipeline.execute)
        self._dirty, self._saved = not all(result), all(result)
        raise gen.Return(all(result))

########NEW FILE########
__FILENAME__ = process
"""
process.py

"""
from helper import config as helper_config
from tornado import httpserver
from tornado import ioloop
import logging
import multiprocessing
import signal
import socket
import ssl
from tornado import version as tornado_version

from tinman import application
from tinman import config
from tinman import exceptions

LOGGER = logging.getLogger(__name__)


class Process(multiprocessing.Process):
    """The process holding the HTTPServer and Application"""
    CERT_REQUIREMENTS = {config.NONE: ssl.CERT_NONE,
                         config.OPTIONAL: ssl.CERT_OPTIONAL,
                         config.REQUIRED: ssl.CERT_REQUIRED}
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        """Create a new instance of Process

        """
        super(Process, self).__init__(group, target, name, args, kwargs)

        # Passed in values
        self.namespace = kwargs['namespace']
        self.port = kwargs['port']

        # Internal attributes holding instance information
        self.app = None
        self.http_server = None
        self.request_counters = dict()

        # Re-setup logging in the new process
        self.logging_config = None

        # If newrelic is passed, use it
        if self.newrelic_ini_path:
            self.setup_newrelic()

    def create_application(self):
        """Create and return a new instance of tinman.application.Application"""
        return application.Application(self.settings,
                                       self.namespace.routes,
                                       self.port)

    def create_http_server(self):
        """Setup the HTTPServer

        :rtype: tornado.httpserver.HTTPServer

        """
        return self.start_http_server(self.port, self.http_config)

    @property
    def http_config(self):
        """Return a dictionary of HTTPServer arguments using the default values
        as specified in the HTTPServer class docstrings if no values are
        specified.

        :param dict config: The HTTPServer specific section of the config
        :rtype: dict

        """
        return {config.NO_KEEP_ALIVE:
                    self.namespace.server.get(config.NO_KEEP_ALIVE, False),
                config.SSL_OPTIONS: self.ssl_options,
                config.XHEADERS: self.namespace.server.get(config.XHEADERS,
                                                           False)}

    def on_sigabrt(self, signal_unused, frame_unused):
        """Stop the HTTP Server and IO Loop, shutting down the process

        :param int signal_unused: Unused signal number
        :param frame frame_unused: Unused frame the signal was caught in

        """
        LOGGER.info('Stopping HTTP Server and IOLoop')
        self.http_server.stop()
        self.ioloop.stop()

    def on_sighup(self, signal_unused, frame_unused):
        """Reload the configuration

        :param int signal_unused: Unused signal number
        :param frame frame_unused: Unused frame the signal was caught in

        """
        # Update HTTP configuration
        for setting in self.http_config:
            if getattr(self.http_server, setting) != self.http_config[setting]:
                LOGGER.debug('Changing HTTPServer %s setting', setting)
                setattr(self.http_server, setting, self.http_config[setting])

        # Update Application Settings
        for setting in self.settings:
            if self.app.settings[setting] != self.settings[setting]:
                LOGGER.debug('Changing Application %s setting', setting)
                self.app.settings[setting] = self.settings[setting]

        # Update the routes
        self.app.handlers = []
        self.app.named_handlers = {}
        routes = self.namespace.config.get(config.ROUTES)
        self.app.add_handlers(".*$", self.app.prepare_routes(routes))

        LOGGER.info('Configuration reloaded')

    def run(self):
        """Called when the process has started

        :param int port: The HTTP Server port

        """
        LOGGER.debug('Initializing process')

        # Setup logging
        self.logging_config = self.setup_logging()

        # Register the signal handlers
        self.setup_signal_handlers()

        # Create the application instance
        try:
            self.app = self.create_application()
        except exceptions.NoRoutesException:
            return

        # Create the HTTPServer
        self.http_server = self.create_http_server()

        # Hold on to the IOLoop in case it's needed for responding to signals
        self.ioloop = ioloop.IOLoop.instance()

        # Start the IOLoop, blocking until it is stopped
        try:
            self.ioloop.start()
        except KeyboardInterrupt:
            pass

    @property
    def settings(self):
        """Return the Application configuration

        :rtype: dict

        """
        return dict(self.namespace.config)

    def setup_logging(self):
        return helper_config.LoggingConfig(self.namespace.logging)

    @property
    def newrelic_ini_path(self):
        return self.namespace.config.get(config.NEWRELIC)

    def setup_newrelic(self):
        """Setup the NewRelic python agent"""
        import newrelic.agent
        newrelic.agent.initialize(self.newrelic_ini_path)

    def setup_signal_handlers(self):
        """Called when a child process is spawned to register the signal
        handlers

        """
        LOGGER.debug('Registering signal handlers')
        signal.signal(signal.SIGABRT, self.on_sigabrt)

    @property
    def ssl_options(self):
        """Check the config to see if SSL configuration options have been passed
        and replace none, option, and required with the correct values in
        the certreqs attribute if it is specified.

        :rtype: dict

        """
        opts = self.namespace.server.get(config.SSL_OPTIONS) or dict()
        if config.CERT_REQS in opts:
            opts[config.CERT_REQS] = \
                self.CERT_REQUIREMENTS[opts[config.CERT_REQS]]
        return opts or None

    def start_http_server(self, port, args):
        """Start the HTTPServer

        :param int port: The port to run the HTTPServer on
        :param dict args: Dictionary of arguments for HTTPServer
        :rtype: tornado.httpserver.HTTPServer

        """
        # Start the HTTP Server
        LOGGER.info("Starting Tornado v%s HTTPServer on port %i Args: %r",
                    tornado_version, port, args)
        http_server = httpserver.HTTPServer(self.app, **args)
        http_server.bind(port, family=socket.AF_INET)
        http_server.start(1)
        return http_server

########NEW FILE########
__FILENAME__ = serializers
"""
Tinman data serializers for use with sessions and other data objects.

"""
import datetime
import json
try:
    import msgpack
except ImportError:
    msgpack = None
import pickle


class Serializer(object):
    """Base data serialization object used by session adapters and other
    classes. To use different data serialization formats, extend this class and
    implement the serialize and deserialize methods.

    """
    def deserialize(self, data):
        """Return the deserialized data.

        :param str data: The data to deserialize
        :rtype: dict
        :raises: NotImplementedError

        """
        raise NotImplementedError

    def serialize(self, data):
        """Return self._data as a serialized string.

        :param str data: The data to serialize
        :rtype: str

        """
        raise NotImplementedError

    def _deserialize_datetime(self, data):
        """Take any values coming in as a datetime and deserialize them

        """
        for key in data:
            if isinstance(data[key], dict):
                if data[key].get('type') == 'datetime':
                    data[key] = \
                        datetime.datetime.fromtimestamp(data[key]['value'])
        return data

    def _serialize_datetime(self, data):
        for key in data.keys():
            if isinstance(data[key], datetime.datetime):
                data[key] = {'type': 'datetime',
                             'value': data[key].strftime('%s')}
        return data


class Pickle(Serializer):
    """Serializes the data in Pickle format"""
    def deserialize(self, data):
        """Return the deserialized data.

        :param str data: The data to deserialize
        :rtype: dict

        """
        if not data:
            return dict()
        return self._deserialize_datetime(pickle.loads(data))

    def serialize(self, data):
        """Return self._data as a serialized string.

        :param str data: The data to serialize
        :rtype: str

        """
        return pickle.dumps(self._serialize_datetime(data))


class JSON(Serializer):
    """Serializes the data in JSON format"""
    def deserialize(self, data):
        """Return the deserialized data.

        :param str data: The data to deserialize
        :rtype: dict

        """
        return self._deserialize_datetime(json.loads(data, encoding='utf-8'))

    def serialize(self, data):
        """Return the data as serialized string.

        :param dict data: The data to serialize
        :rtype: str

        """
        return json.dumps(self._serialize_datetime(data), ensure_ascii=False)


class MsgPack(Serializer):
    """Serializes the data in msgpack format"""

    def deserialize(self, data):
        """Return the deserialized data.

        :param str data: The data to deserialize
        :rtype: dict

        """
        return self._deserialize_datetime(msgpack.loads(data))

    def serialize(self, data):
        """Return the data as serialized string.

        :param dict data: The data to serialize
        :rtype: str

        """
        return msgpack.dumps(self._serialize_datetime(data))

########NEW FILE########
__FILENAME__ = session
"""
Tinman session classes for the management of session data

"""
from tornado import gen
import logging
import os
from os import path
import tempfile
import time
import uuid

from tinman import config
from tinman import exceptions
from tinman import mapping

LOGGER = logging.getLogger(__name__)


class Session(mapping.Mapping):
    """Session provides a base interface for session management and should be
    extended by storage objects that are used by the SessionHandlerMixin.

    """
    id = None
    ip_address = None
    last_request_at = None
    last_request_uri = None

    def __init__(self, session_id=None, duration=3600, settings=None):
        """Create a new session instance. If no id is passed in, a new ID is
        created. If an id is passed in, load the session data from storage.

        :param str session_id: The session ID
        :param dict settings: Session object configuration

        """
        super(Session, self).__init__()
        self._duration = duration
        self._settings = settings or dict()
        self.id = session_id or str(uuid.uuid4())

    def fetch(self):
        """Fetch the contents of the session from storage.

        :raises: NotImplementedError

        """
        raise NotImplementedError

    def delete(self):
        """Extend to the delete the session from storage

        :raises: NotImplementedError

        """
        raise NotImplementedError

    def save(self):
        """Save the session for later retrieval

        :raises: NotImplementedError

        """
        raise NotImplementedError


class FileSession(Session):
    """Session data is stored on disk using the FileSession object.

    Configuration in the application settings is as follows::

        Application:
          session:
            adapter:
              name: file
              cleanup: false
              directory: /tmp/sessions
            cookie:
              name: session
              duration: 3600

    """
    DEFAULT_SUBDIR = 'tinman'

    def __init__(self, session_id=None, duration=None, settings=None):
        """Create a new session instance. If no id is passed in, a new ID is
        created. If an id is passed in, load the session data from storage.

        :param str session_id: The session ID
        :param dict settings: Session object configuration

        """
        super(FileSession, self).__init__(session_id, duration, settings)
        self._storage_dir = self._setup_storage_dir()
        if settings.get('cleanup', True):
            self._cleanup()

    def fetch(self):
        """Fetch the contents of the session from storage.

        :raises: NotImplementedError

        """
        raise NotImplementedError

    def delete(self):
        """Extend to the delete the session from storage

        """
        self.clear()
        if os.path.isfile(self._filename):
            os.unlink(self._filename)
        else:
            LOGGER.debug('Session file did not exist: %s', self._filename)

    def save(self):
        """Save the session for later retrieval

        :raises: IOError

        """
        try:
            with open(self._filename, 'wb') as session_file:
                session_file.write(self.dumps())
        except IOError as error:
            LOGGER.error('Session file error: %s', error)
            raise error

    def _cleanup(self):
        """Remove any stale files from the session storage directory"""
        for filename in os.listdir(self._storage_dir):
            file_path = path.join(self._storage_dir, filename)
            file_stat = os.stat(file_path)
            evaluate = max(file_stat.st_ctime, file_stat.st_mtime)
            if evaluate + self._duration < time.time():
                LOGGER.debug('Removing stale file: %s', file_path)
                os.unlink(file_path)

    @property
    def _default_path(self):
        """Return the default path for session data

        :rtype: str

        """
        return path.join(tempfile.gettempdir(), self.DEFAULT_SUBDIR)

    @property
    def _filename(self):
        """Returns the filename for the session file.

        :rtype: str

        """
        return path.join(self._storage_dir, self.id)

    @staticmethod
    def _make_path(dir_path):
        """Create the full path specified.

        :param str dir_path: The path to make

        """
        os.makedirs(dir_path, 0x755)

    def _setup_storage_dir(self):
        """Setup the storage directory path value and ensure the path exists.

        :rtype: str
        :raises: tinman.exceptions.ConfigurationException

        """
        dir_path = self._settings.get(config.DIRECTORY)
        if dir_path is None:
            dir_path = self._default_path
            if not os.path.exists(dir_path):
                self._make_path(dir_path)
        else:
            dir_path = path.abspath(dir_path)
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                raise exceptions.ConfigurationException(self.__class__.__name__,
                                                        config.DIRECTORY)
        return dir_path.rstrip('/')


class RedisSession(Session):
    """Using the RedisSession object, session data is stored in a Redis database
    using the tornadoredis client library.

    Example configuration in the application settings is as follows::

        Application:
          session:
            adapter:
              name: redis
              host: localhost
              port: 6379
              db: 2
            cookie:
              name: session
              duration: 3600

    """
    _redis_client = None
    REDIS_DB = 2
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379

    def __init__(self, session_id, duration=None, settings=None):
        """Create a new redis session instance. If no id is passed in, a
        new ID is created. If an id is passed in, load the session data from
        storage.

        :param str session_id: The session ID
        :param dict config: Session object configuration

        """
        if not RedisSession._redis_client:
            RedisSession._redis_connect(settings)
        super(RedisSession, self).__init__(session_id, duration, settings)

    @property
    def _key(self):
        return 's:%s' % self.id

    @classmethod
    def _redis_connect(cls, settings):
        """Connect to redis and assign the client to the RedisSession class
        so that it is globally available in this process.

        :param dict settings: The redis session configuration

        """
        if 'tornadoredis' not in globals():
            import tornadoredis
        kwargs = {'host': settings.get('host', cls.REDIS_HOST),
                  'port': settings.get('port', cls.REDIS_PORT),
                  'selected_db': settings.get('db', cls.REDIS_DB)}
        LOGGER.info('Connecting to %(host)s:%(port)s DB %(selected_db)s',
                    kwargs)
        cls._redis_client = tornadoredis.Client(**kwargs)
        cls._redis_client.connect()

    @gen.coroutine
    def delete(self):
        """Delete the item from storage

        :param method callback: The callback method to invoke when done

        """
        result = yield gen.Task(RedisSession._redis_client.delete, self._key)
        LOGGER.debug('Deleted session %s (%r)', self.id, result)
        self.clear()
        raise gen.Return(result)

    @gen.coroutine
    def fetch(self):
        """Fetch the data for the model from Redis and assign the values.

        :param method callback: The callback method to invoke when done

        """
        LOGGER.debug('Fetching session data: %s', self.id)
        result = yield gen.Task(RedisSession._redis_client.get, self._key)
        if result:
            self.loads(result)
            raise gen.Return(True)
        else:
            raise gen.Return(False)

    @gen.coroutine
    def save(self):
        """Store the session data in redis

        :param method callback: The callback method to invoke when done

        """
        result = yield gen.Task(RedisSession._redis_client.set,
                                self._key, self.dumps())
        LOGGER.debug('Saved session %s (%r)', self.id, result)
        raise gen.Return(result)

########NEW FILE########
__FILENAME__ = transforms
"""
Tornado Output Transforming Classes

"""
from tornado import web


class StripBlankLines(web.OutputTransform):

    def transform_first_chunk(self, status_code, headers, chunk, finishing):
        content_type = headers.get("Content-Type", "").split(";")[0]
        if content_type.split('/')[0] == 'text':
            chunk = self.transform_chunk(chunk, finishing)
            if "Content-Length" in headers:
                headers["Content-Length"] = str(len(chunk))
        return status_code, headers, chunk

    def transform_chunk(self, chunk, finishing):
        return '\n'.join([line for line in chunk.split('\n') if line])

########NEW FILE########
__FILENAME__ = heapy_report
#!/usr/bin/env python
"""Will generate a plaintext report from the JSON document created
by the HeapyRequestHandler.

Usage: tinman-heap-report file.json

"""
import json
import os
import sys


def print_row(row, depth):
    prefix = ''.join([' ' for offset in range(0, depth * 4)])
    item = '%s - %s' % (prefix, row['item'])
    parts = [item.ljust(80),
             ('%(value)s' % (row['count'])).rjust(10),
             (' %(percent)s%%' % (row['count'])).rjust(7),
             ('%(value)s' % (row['size'])).rjust(10),
             (' %(percent)s%%' % (row['size'])).rjust(7)]
    print ''.join(parts)


def main():
    if len(sys.argv) == 1 or not (os.path.exists(sys.argv[1]) and
                                  os.path.isfile(sys.argv[1])):
        print 'Usage: tinman-heap-report heap-file.json\n'
        sys.exit(-1)
    with open(sys.argv[1], "r") as handle:
        report = json.load(handle)
    print ''.join(['Item'.ljust(80), 'Count'.rjust(17), 'Size'.rjust(17)])
    print ''.join(['-' for position in xrange(0, 114)])
    for row in report['rows']:
        print
        print_row(row, 0)
        for child in row['referrers']['rows']:
            print
            print_row(child, 1)
            for grandchild in child['referrers']['rows']:
                print_row(grandchild, 2)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = initialize
"""Create a new tinman/tornado project including setting up the setup.py file,
initial directory structure and virtual environment, if desired.

"""
import argparse
import logging
import os

DESCRIPTION = ('A tool to create a new tinman project, including the directory '
               'structure, setup.py file and skeleton configuration')
LOGGER = logging.getLogger(__name__)

from tinman import __version__


class Project(object):

    DEFAULT_MODE = 0755
    DIRECTORIES = ['etc',
                   'source', 'source/less', 'source/js',
                   'static', 'static/css', 'static/img', 'static/js',
                   'templates',
                   'tests']

    def __init__(self):
        self._parser = self._create_argument_parser()

    def _add_base_arguments(self, parser):
        """Add the base arguments to the argument parser.

        :param argparse.ArgumentParser parser: The parser to add arguments to

        """
        parser.add_argument('--version',
                            help='show the version number and exit',
                            action='version',
                            version='%(prog)s ' + __version__)

    def _add_required_arguments(self, parser):
        """Add the required arguments to the argument parser.

        :param argparse.ArgumentParser parser: The parser to add arguments to

        """
        parser.add_argument('project',
                            metavar='PROJECT',
                            help='The project to create')

    def _create_argument_parser(self):
        """Create and return the argument parser with all of the arguments
        and configuration ready to go.

        :rtype: argparse.ArgumentParser

        """
        parser = self._new_argument_parser()
        self._add_base_arguments(parser)
        self._add_required_arguments(parser)
        return parser

    def _create_base_directory(self):
        os.mkdir(self._arguments.project, self.DEFAULT_MODE)

    def _create_directories(self):
        self._create_base_directory()
        self._create_subdirectory(self._arguments.project)
        for directory in self.DIRECTORIES:
            self._create_subdirectory(directory)

    def _create_package_init(self):
        with open('%s/%s/__init__.py' %
                  (self._arguments.project,
                   self._arguments.project), 'w') as init:
            init.write('')

    def _create_package_setup(self):

        template = """from setuptools import setup
import os
from platform import python_version_tuple

requirements = ['tinman']
test_requirements = ['mock', 'nose']
if float('!s.!s' ! python_version_tuple()[0:2]) < 2.7:
    requirements.append('argparse')
    test_requirements.append('unittest2')

# Build the path to install the templates, example config and static files
base_path = '/usr/share/%(project)s'
data_files = dict()
data_paths = ['static', 'templates', 'etc']
for data_path in data_paths:
    for dir_path, dir_names, file_names in os.walk(data_path):
        install_path = '!s/!s' ! (base_path, dir_path)
        if install_path not in data_files:
            data_files[install_path] = list()
        for file_name in file_names:
            data_files[install_path].append('!s/!s' ! (dir_path, file_name))
with open('MANIFEST.in', 'w') as handle:
    for path in data_files:
        for filename in data_files[path]:
            handle.write('include !s\\n' ! filename)


setup(name='%(project)s',
      version='1.0.0',
      packages=['%(project)s'],
      install_requires=requirements,
      test_suite='nose.collector',
      tests_require=test_requirements,
      data_files=[(key, data_files[key]) for key in data_files.keys()],
      zip_safe=True)

"""
        setup_py = template % {'project': self._arguments.project}
        print setup_py
        with open('%s/setup.py' % self._arguments.project, 'w') as init:
            init.write(setup_py.replace('!', '%'))

    def _create_subdirectory(self, subdir):
        os.mkdir('%s/%s' % (self._arguments.project, subdir), self.DEFAULT_MODE)

    def _new_argument_parser(self):
        """Return a new argument parser.

        :rtype: argparse.ArgumentParser

        """
        return argparse.ArgumentParser(prog='tinman-init',
                                       conflict_handler='resolve',
                                       description=DESCRIPTION)


    def run(self):
        self._arguments = self._parser.parse_args()
        self._create_directories()
        self._create_package_init()
        self._create_package_setup()


def main():
    initializer = Project()
    initializer.run()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = utils
"""
@TODO see if we can move these functions to a more appropriate spot

"""
import importlib
import os
import sys
from socket import gethostname


def application_name():
    """Returns the currently running application name

    :rtype: str

    """
    return os.path.split(sys.argv[0])[1]


def hostname():
    """Returns the hostname for the machine we're running on

    :rtype: str

    """
    return gethostname().split(".")[0]


def import_namespaced_class(path):
    """Pass in a string in the format of foo.Bar, foo.bar.Baz, foo.bar.baz.Qux
    and it will return a handle to the class

    :param str path: The object path
    :rtype: class

    """
    parts = path.split('.')
    return getattr(importlib.import_module('.'.join(parts[0:-1])), parts[-1])

########NEW FILE########
