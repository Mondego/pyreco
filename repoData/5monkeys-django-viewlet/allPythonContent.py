__FILENAME__ = run_tests
#!/usr/bin/env python
# coding=utf-8
import sys
import django
from django.conf import settings


def main():
    conf = {'DEBUG': True,
            'TEMPLATE_DEBUG': True,
            'INSTALLED_APPS': ['viewlet', 'viewlet.tests'],
            'MEDIA_ROOT': '/tmp/viewlet/media',
            'STATIC_ROOT': '/tmp/viewlet/static',
            'MEDIA_URL': '/media/',
            'STATIC_URL': '/static/',
            'ROOT_URLCONF': 'viewlet.tests.urls',
            'SECRET_KEY': "iufoj=mibkpdz*%bob952x(%49rqgv8gg45k36kjcg76&-y5=!",
            'JINJA2_ENVIRONMENT_OPTIONS': {
                'optimized': False  # Coffin config
            },
            'JINJA_CONFIG': {
                'autoescape': True  # Jingo config
            }
    }

    if django.VERSION[:2] >= (1, 3):
        conf.update(DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        })

        conf.update(CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
            }
        })
    else:
        conf.update(DATABASE_ENGINE='sqlite3')
        conf.update(CACHE_BACKEND='locmem://')

    settings.configure(**conf)

    from django.test.utils import get_runner
    test_runner = get_runner(settings)(verbosity=2, interactive=True)
    failures = test_runner.run_tests(['viewlet'])

    sys.exit(failures)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = api
from viewlet.library import library

__all__ = ['viewlet', 'get', 'call', 'refresh']


# The decorator
viewlet = library._decorator


def get(viewlet_name):
    return library.get(viewlet_name)


def call(viewlet_name, context, *args, **kwargs):
    return get(viewlet_name).call(context or {}, *args, **kwargs)


def refresh(name, *args, **kwargs):
    return get(name).refresh(*args, **kwargs)

########NEW FILE########
__FILENAME__ = cache
from django.core.cache import InvalidCacheBackendError


def get_cache():
    try:
        from django.core.cache import get_cache
        cache = get_cache('viewlet')
    except (InvalidCacheBackendError, ValueError):
        from django.core.cache import cache
    return cache

########NEW FILE########
__FILENAME__ = conf
from django.conf import settings as django_settings


class ViewletSettings(dict):

    def __init__(self, **conf):
        super(ViewletSettings, self).__init__(conf)

        # Override defaults with django settings
        for key, value in conf.iteritems():
            setattr(self, key, getattr(django_settings, key, value))

    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


settings = ViewletSettings(**{
    'VIEWLET_TEMPLATE_ENGINE': 'django',
    'VIEWLET_INFINITE_CACHE_TIMEOUT': 31104000,  # 60*60*24*30*12, about a year
    'VIEWLET_JINJA2_ENVIRONMENT': 'viewlet.loaders.jinja2_loader.create_env'
})

########NEW FILE########
__FILENAME__ = exceptions
from django.template import TemplateSyntaxError


class ViewletException(Exception):
    pass


class UnknownViewlet(TemplateSyntaxError):
    pass

########NEW FILE########
__FILENAME__ = library
# coding=utf-8
import types


class Singleton(type):
    """
    Singleton type
    """

    instance = None

    def __call__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instance


class Library(dict):
    """
    The Library stores references to registered viewlets
    """

    __metaclass__ = Singleton

    def autodiscover(self):
        """
        Autodiscover decorated viewlets.
        Imports all views.py and viewlets.py to trigger the decorators.
        """
        from django.conf import settings
        from django.utils.importlib import import_module
        for app in settings.INSTALLED_APPS:
            try:
                import_module('%s.views' % app)
                import_module('%s.viewlets' % app)
            except ImportError:
                continue

    def get(self, name):
        """
        Getter for a registered viewlet.
        If not found then scan for decorated viewlets.
        """
        if not name in self.keys():
            self.autodiscover()

        try:
            return self[name]
        except KeyError:
            from viewlet.exceptions import UnknownViewlet
            raise UnknownViewlet(u'Unknown viewlet "%s"' % name)

    def add(self, viewlet):
        """
        Adds a registered viewlet to the Library dict
        """
        if not viewlet.name in self.keys():
            self[viewlet.name] = viewlet

    def _decorator(self, name=None, template=None, key=None, timeout=60, cached=True):
        """
        Handles both decorator pointer and caller (with or without arguments).
        Creates a Viewlet instance to wrap the decorated function with.
        """
        from viewlet.models import Viewlet

        if isinstance(name, types.FunctionType):
            def declare(func):
                viewlet = Viewlet(self)
                return viewlet.register(func)
            return declare(name)
        else:
            viewlet = Viewlet(self, name, template, key, timeout, cached)
            return viewlet.register


library = Library()

########NEW FILE########
__FILENAME__ = django_loader
# coding=utf-8
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

########NEW FILE########
__FILENAME__ = jinja2_loader
# coding=utf-8
from django.conf import settings as django_settings
from django.utils.importlib import import_module
from jinja2 import FileSystemLoader, PackageLoader, ChoiceLoader, nodes
from jinja2.environment import Environment
from jinja2.ext import Extension
from jinja2.filters import do_mark_safe
import viewlet
from viewlet.conf import settings


class ViewletExtension(Extension):
    tags = set(['viewlet'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno

        viewlet_args = []
        name = None
        first = True
        while parser.stream.current.type != 'block_end':
            if not first:
                parser.stream.expect('comma')
                viewlet_args.append(parser.parse_expression())
            else:
                name = parser.parse_expression()
            first = False
        context = nodes.ContextReference()
        return nodes.CallBlock(self.call_method('_call_viewlet', args=[name, context, nodes.List(viewlet_args)]),
                               [], [], []).set_lineno(lineno)

    def _call_viewlet(self, name, context, viewlet_args, caller=None):
        context = context.get_all()
        return mark_safe(viewlet.call(name, context, *viewlet_args))


def create_env():
    x = ((FileSystemLoader, django_settings.TEMPLATE_DIRS),
         (PackageLoader, django_settings.INSTALLED_APPS))
    loaders = [loader(p) for loader, places in x for p in places]
    env = Environment(loader=ChoiceLoader(loaders), extensions=[ViewletExtension])
    return env


_env = None


def get_env():
    global _env
    if _env:
        return _env

    jinja2_env_module = settings.VIEWLET_JINJA2_ENVIRONMENT
    module, environment = jinja2_env_module.rsplit('.', 1)
    imported_module = import_module(module)
    jinja2_env = getattr(imported_module, environment)
    if callable(jinja2_env):
        jinja2_env = jinja2_env()
    _env = jinja2_env
    return jinja2_env


def render_to_string(template_name, context):
    return get_template(template_name).render(context)


def get_template(template_name):
    return get_env().get_template(template_name)


def mark_safe(value):
    return do_mark_safe(value)

########NEW FILE########
__FILENAME__ = models
import warnings
from inspect import getargspec
from django.template.context import BaseContext
from django.utils.encoding import smart_str, smart_unicode
from viewlet.cache import get_cache
from viewlet.conf import settings
from viewlet.loaders import render

cache = get_cache()
DEFAULT_CACHE_TIMEOUT = cache.default_timeout


class Viewlet(object):
    """
    Representation of a viewlet
    """

    def __init__(self, library, name=None, template=None, key=None, timeout=DEFAULT_CACHE_TIMEOUT, cached=True):
        self.library = library
        self.name = name
        self.template = template
        self.key = key
        self.key_mod = False
        if timeout is None:
            # Handle infinite caching, due to Django's cache backend not respecting 0
            self.timeout = settings.VIEWLET_INFINITE_CACHE_TIMEOUT
        else:
            self.timeout = timeout
        if not cached:
            self.timeout = 0
            warnings.warn('Keyword argument "cache" is deprecated, use timeout=0 to disable cache', DeprecationWarning)

    def register(self, func):
        """
        Initial decorator wrapper that configures the viewlet instance,
        adds it to the library and then returns a pointer to the call
        function as the actual wrapper
        """
        self.viewlet_func = func
        self.viewlet_func_args = getargspec(func).args

        if not self.name:
            self.name = func.func_name

        func_argcount = len(self.viewlet_func_args) - 1
        if self.timeout:
            #TODO: HASH KEY
            self.key = u'viewlet:%s(%s)' % (self.name, ','.join(['%s' for _ in range(0, func_argcount)]))
            self.key_mod = func_argcount > 0
        self.library.add(self)

        return self.call

    def _build_args(self, *args, **kwargs):
        viewlet_func_kwargs = dict((self.viewlet_func_args[i], args[i]) for i in range(0, len(args)))
        viewlet_func_kwargs.update(dict((k, v) for k, v in kwargs.iteritems() if k in self.viewlet_func_args))
        return [viewlet_func_kwargs.get(arg) for arg in self.viewlet_func_args]

    def _build_cache_key(self, *args):
        """
        Build cache key based on viewlet argument except initial context argument.
        """
        return self.key if not self.key_mod else self.key % tuple(args)

    def _cache_get(self, key):
        return cache.get(key)

    def _cache_set(self, key, value):
        timeout = self.timeout

        # Avoid pickling string like objects
        if isinstance(value, basestring):
            value = smart_str(value)
        cache.set(key, value, timeout)

    def call(self, *args, **kwargs):
        """
        The actual wrapper around the decorated viewlet function.
        """
        refresh = kwargs.pop('refresh', False)
        merged_args = self._build_args(*args, **kwargs)
        output = self._call(merged_args, refresh)

        # Render template for context viewlets
        if self.template:
            context = merged_args[0]
            if isinstance(context, BaseContext):
                context.push()
            else:
                context = dict(context)
            context.update(output)

            output = self.render(context)

            if isinstance(context, BaseContext):
                context.pop()

        return smart_unicode(output)

    def _call(self, merged_args, refresh=False):
        """
        Executes the actual call to the viewlet function and handles all the cache logic
        """

        cache_key = self._build_cache_key(*merged_args[1:])

        if refresh or not self.is_using_cache():
            output = None
        else:
            output = self._cache_get(cache_key)

        # First viewlet execution, forced refresh or cache timeout
        if output is None:
            output = self.viewlet_func(*merged_args)
            if self.is_using_cache():
                self._cache_set(cache_key, output)

        return output

    def is_using_cache(self):
        return self.timeout != 0

    def render(self, context):
        """
        Renders the viewlet template.
        The render import is based on settings.VIEWLET_TEMPLATE_ENGINE (default django).
        """
        return render(self.template, context)

    def refresh(self, *args):
        """
        Shortcut to _call() with the refresh arg set to True to force a cache update.
        """
        merged_args = self._build_args({}, *args)
        return self._call(merged_args, refresh=True)

    def expire(self, *args):
        """
        Clears cached viewlet based on args
        """
        merged_args = self._build_args({}, *args)
        dyna_key = self._build_cache_key(*merged_args[1:])
        cache.delete(dyna_key)

########NEW FILE########
__FILENAME__ = viewlets
import logging
import re
from django import template
from django.template import TemplateSyntaxError
import viewlet
from viewlet.exceptions import UnknownViewlet
from viewlet.loaders import mark_safe

logger = logging.getLogger(__name__)
register = template.Library()
kwarg_re = re.compile(r'(?:(\w+)=)?(.+)')


class ViewletNode(template.Node):

    def __init__(self, viewlet_name, args, kwargs):
        self.viewlet_name = viewlet_name
        self.viewlet_args = args
        self.viewlet_kwargs = kwargs

    def render(self, context):
        try:
            args = [arg.resolve(context) for arg in self.viewlet_args]
            kwargs = dict((key, value.resolve(context)) for key, value in self.viewlet_kwargs.iteritems())
            template = viewlet.call(self.viewlet_name, context, *args, **kwargs)
            return mark_safe(template)
        except UnknownViewlet as e:
            logger.exception(e)
            raise


@register.tag(name='viewlet')
def viewlet_tag(parser, token):
    bits = token.split_contents()[1:]
    viewlet_name = bits.pop(0)
    args = []
    kwargs = {}

    for bit in bits:
        match = kwarg_re.match(bit)
        if not match:
            raise TemplateSyntaxError('Malformed arguments to viewlet tag')
        name, value = match.groups()
        if name:
            kwargs[name] = parser.compile_filter(value)
        else:
            args.append(parser.compile_filter(value))

    return ViewletNode(viewlet_name, args, kwargs)

########NEW FILE########
__FILENAME__ = test_viewlet
# coding=utf-8
from time import time, sleep
from django.core.urlresolvers import reverse
from django.template import Context
from django.template import TemplateSyntaxError
from django.template.loader import get_template_from_string
from django.test import TestCase, Client
from django import VERSION as django_version
import viewlet
from ..exceptions import UnknownViewlet
from ..cache import get_cache
from ..conf import settings
from ..loaders import jinja2_loader
from ..loaders.jinja2_loader import get_env

cache = get_cache()
__all__ = ['ViewletTest']


class ViewletTest(TestCase):

    def setUp(self):
        cache.clear()
        settings.VIEWLET_TEMPLATE_ENGINE = 'django'

        @viewlet.viewlet
        def hello_world(context):
            return u'Hello wörld!'

        @viewlet.viewlet
        def hello_name(context, name=u"wurld"):
            return u'Hello %s' % name

        @viewlet.viewlet(template='hello_world.html', cached=False)
        def hello_nocache(context, name="wurld"):
            return {'name': name}

        @viewlet.viewlet(template='hello_world.html', timeout=10)
        def hello_cache(context, name):
            return {
                'name': name,
                'timestamp': time(),
            }

        @viewlet.viewlet(name='hello_new_name', template='hello_world.html', timeout=10)
        def hello_named_world(context, name):
            return {
                'name': name,
            }

        @viewlet.viewlet(template='hello_timestamp.html', timeout=10)
        def hello_cached_timestamp(context, name):
            return {
                'name': name,
                'timestamp': time(),
            }

        @viewlet.viewlet(template='hello_timestamp.html', timeout=None)
        def hello_infinite_cache(context, name):
            return {
                'name': name,
                'timestamp': time(),
            }

        @viewlet.viewlet(template='hello_timestamp.html', cached=False)
        def hello_non_cached_timestamp(context, name):
            return {
                'name': name,
                'timestamp': time(),
            }

        @viewlet.viewlet(template='hello_strong_world.html', timeout=10)
        def hello_strong(context, name):
            return {
                'name': name
            }

        @viewlet.viewlet(template='hello_request.html', timeout=0)
        def hello_request(context, greeting):
            return {
                'greeting': greeting
            }

    def tearDown(self):
        jinja2_loader._env = None
        settings.VIEWLET_JINJA2_ENVIRONMENT = 'viewlet.loaders.jinja2_loader.create_env'

    def get_django_template(self, source):
        return '\n'.join(('{% load viewlets %}',
                          source))

    def get_jinja_template(self, source):
        settings.VIEWLET_TEMPLATE_ENGINE = 'jinja2'
        return get_env().from_string(source)

    def render(self, source, context=None):
        return get_template_from_string(source).render(Context(context or {})).strip()

    def test_version(self):
        self.assertEqual(viewlet.get_version((1, 2, 3, 'alpha', 1)), '1.2.3a1')
        self.assertEqual(viewlet.get_version((1, 2, 3, 'beta', 2)), '1.2.3b2')
        self.assertEqual(viewlet.get_version((1, 2, 3, 'rc', 3)), '1.2.3c3')
        self.assertEqual(viewlet.get_version((1, 2, 3, 'final', 4)), '1.2.3')

    def test_get_existing_viewlet(self):
        viewlet.get('hello_cache')

    def test_get_non_existing_viewlet(self):
        self.assertRaises(UnknownViewlet, viewlet.get, 'i_do_not_exist')

    def test_empty_decorator(self):
        template = self.get_django_template("<h1>{% viewlet hello_world %}</h1>")
        html1 = self.render(template)
        self.assertEqual(html1, u'<h1>Hello wörld!</h1>')
        html2 = self.render(template)
        sleep(0.01)
        self.assertEqual(html1, html2)

    def test_render_tag(self):
        template = self.get_django_template("<h1>{% viewlet hello_nocache name=viewlet_arg %}</h1>")
        html = self.render(template, {'viewlet_arg': u'wörld'})
        self.assertEqual(html.strip(), u'<h1>Hello wörld!\n</h1>')
        template = self.get_django_template("<h1>{% viewlet unknown_viewlet %}</h1>")
        self.assertRaises(UnknownViewlet, self.render, template)
        template = self.get_django_template("<h1>{% viewlet hello_world name= %}</h1>")
        self.assertRaises(TemplateSyntaxError, self.render, template)

    def test_cached_tag(self):
        template = self.get_django_template("<h1>{% viewlet hello_cached_timestamp 'world' %}</h1>")
        html1 = self.render(template)
        sleep(0.01)
        html2 = self.render(template)
        self.assertEqual(html1, html2)

    def test_non_cached_tag(self):
        template = self.get_django_template("<h1>{% viewlet hello_non_cached_timestamp 'world' %}</h1>")
        html1 = self.render(template)
        sleep(0.01)
        html2 = self.render(template)
        self.assertNotEqual(html1, html2)

    def test_cache(self):
        html1 = viewlet.call('hello_cache', None, 'world')
        sleep(0.01)
        html2 = viewlet.call('hello_cache', None, 'world')
        self.assertEquals(html1, html2)

    def test_unicode_cache(self):
        html1 = viewlet.call('hello_cache', None, u'wörld')
        sleep(0.01)
        html2 = viewlet.call('hello_cache', None, u'wörld')
        self.assertEquals(html1, html2)

    def test_refresh(self):
        template = self.get_django_template("<h1>{% viewlet hello_cached_timestamp 'world' %}</h1>")
        html1 = self.render(template)
        sleep(0.01)
        viewlet.refresh('hello_cached_timestamp', 'world')
        html2 = self.render(template)
        self.assertNotEqual(html1, html2)

    def test_view(self):
        client = Client()
        url = reverse('viewlet', args=['hello_cache'])
        response = client.get(url, {'name': u'wörld'})
        self.assertEqual(response.status_code, 200)
        html = viewlet.call('hello_cache', None, u'wörld')
        self.assertEqual(response.content.decode('utf-8'), html)

    def test_jinja_tag(self):
        template = self.get_jinja_template(u"<h1>{% viewlet 'hello_nocache', viewlet_arg %}</h1>")
        html = template.render({'extra': u'Räksmörgås', 'viewlet_arg': u'wörld'})
        self.assertEqual(html.strip(), u'<h1>RäksmörgåsHello wörld!</h1>')

    def test_custom_jinja2_environment(self):
        env = get_env()
        self.assertEqual(env.optimized, True)
        self.assertEqual(env.autoescape, False)
        settings.VIEWLET_JINJA2_ENVIRONMENT = 'coffin.common.env'
        jinja2_loader._env = None
        env = get_env()
        self.assertEqual(env.optimized, False)
        # Jingo does not support django <= 1.2
        if django_version[:2] > (1, 2):
            settings.VIEWLET_JINJA2_ENVIRONMENT = 'jingo.get_env'
            env = get_env()
            self.assertEqual(env.autoescape, True)

    def test_context_tag(self):
        template = self.get_django_template("<h1>{% viewlet hello_cached_timestamp 'world' %}</h1>")
        self.render(template)
        v = viewlet.get('hello_cached_timestamp')
        cache_key = v._build_cache_key('world')
        viewlet_data = cache.get(cache_key)
        self.assertTrue('name' in viewlet_data)
        self.assertEqual(viewlet_data['name'], 'world')
        self.assertTrue(isinstance(viewlet_data, dict))

    def test_infinite_cache(self):
        template = self.get_django_template("<h1>{% viewlet hello_infinite_cache 'world' %}</h1>")
        self.render(template)
        v = viewlet.get('hello_infinite_cache')
        self.assertEqual(v.timeout, settings.VIEWLET_INFINITE_CACHE_TIMEOUT)

    def test_expire_cache(self):
        v = viewlet.get('hello_cache')
        v.call({}, 'world')
        cache_key = v._build_cache_key('world')
        sleep(0.01)
        self.assertTrue(cache.get(cache_key) is not None)
        v.expire('world')
        self.assertTrue(cache.get(cache_key) is None)

    def test_mark_safe(self):
        # Test django
        template = self.get_django_template("<h1>{% viewlet hello_strong 'wörld' %}</h1>")
        html = self.render(template.strip())
        self.assertEqual(html, u'<h1>Hello <strong>wörld!</strong>\n</h1>')
        # Test jinja2
        template = self.get_jinja_template(u"<h1>{% viewlet 'hello_strong', 'wörld' %}</h1>")
        html = template.render()
        self.assertEqual(html, u'<h1>Hello <strong>wörld!</strong></h1>')

    def test_cached_string(self):
        template = self.get_django_template("<h1>{% viewlet hello_name name='wörld' %}</h1>")
        html = self.render(template)
        self.assertTrue(isinstance(html, unicode))
        v = viewlet.get('hello_name')
        cache_key = v._build_cache_key(u'wörld')
        cached_value = cache.get(cache_key)
        self.assertTrue(isinstance(cached_value, str))

    def test_named(self):
        template = self.get_django_template("<h1>{% viewlet hello_new_name 'wörld' %}</h1>")
        self.render(template)
        self.assertTrue(viewlet.get('hello_new_name') is not None)

    def test_refreshing_context_viewlet_expecting_request_while_rendering_using_jinja2(self):
        template = self.get_jinja_template("{% viewlet 'hello_request', 'nice to see you' %}")
        html = template.render({'request': {'user': 'nicolas cage'}})
        viewlet.refresh('hello_request', 'nice to see you')
        self.assertNotEqual(template.render({'request': {'user': 'castor troy'}}), html)

########NEW FILE########
__FILENAME__ = urls
# coding=utf-8
try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include

urlpatterns = patterns('',
    (r'^viewlet/', include('viewlet.urls')),
)

########NEW FILE########
__FILENAME__ = urls
# coding=utf-8
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('viewlet.views', url(r'^(?P<name>.+)/$', 'viewlet_view', name='viewlet'))

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.template.context import RequestContext
import viewlet
from viewlet.loaders import querydict_to_kwargs


def viewlet_view(request, name):
    context = RequestContext(request)
    kwargs = querydict_to_kwargs(request.GET)
    output = viewlet.call(name, context, **kwargs)
    return HttpResponse(output)

########NEW FILE########
