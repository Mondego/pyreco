__FILENAME__ = callbacks
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.functional import LazyObject

from django_hosts.reverse import reverse_host

HOST_SITE_TIMEOUT = getattr(settings, "HOST_SITE_TIMEOUT", 3600)


class LazySite(LazyObject):

    def __init__(self, request, *args, **kwargs):
        super(LazySite, self).__init__()
        self.__dict__.update({
            'name': request.host.name,
            'args': args,
            'kwargs': kwargs,
        })

    def _setup(self):
        host = reverse_host(self.name, args=self.args, kwargs=self.kwargs)
        from django.contrib.sites.models import Site
        site = get_object_or_404(Site, domain__iexact=host)
        self._wrapped = site


class CachedLazySite(LazySite):

    def _setup(self):
        host = reverse_host(self.name, args=self.args, kwargs=self.kwargs)
        cache_key = "hosts:%s" % host
        from django.core.cache import cache
        site = cache.get(cache_key, None)
        if site is not None:
            self._wrapped = site
            return
        from django.contrib.sites.models import Site
        site = get_object_or_404(Site, domain__iexact=host)
        cache.set(cache_key, site, HOST_SITE_TIMEOUT)
        self._wrapped = site


def host_site(request, *args, **kwargs):
    """
    A callback function which uses the :mod:`django.contrib.sites` contrib
    app included in Django to match a host to a
    :class:`~django.contrib.sites.models.Site` instance, setting a
    ``request.site`` attribute on success.

    :param request: the request object passed from the middleware
    :param \*args: the parameters as matched by the host patterns
    :param \*\*kwargs: the keyed parameters as matched by the host patterns

    It's important to note that this uses
    :func:`~django_hosts.reverse.reverse_host` behind the scenes to
    reverse the host with the given arguments and keyed arguments to
    enable a flexible configuration of what will be used to retrieve
    the :class:`~django.contrib.sites.models.Site` instance -- in the end
    the callback will use a ``domain__iexact`` lookup to get it.

    For example, imagine a host conf with a username parameter::

        from django.conf import settings
        from django_hosts import patterns, host

        settings.PARENT_HOST = 'example.com'

        host_patterns = patterns('',
            host(r'www', settings.ROOT_URLCONF, name='www'),
            host(r'(?P<username>\w+)', 'path.to.custom_urls',
                 callback='django_hosts.callbacks.host_site',
                 name='user-sites'),
        )

    When requesting this website with the host ``jezdez.example.com``,
    the callback will act as if you'd do::

        request.site = Site.objects.get(domain__iexact='jezdez.example.com')

    ..since the result of calling :func:`~django_hosts.reverse.reverse_host`
    with the username ``'jezdez'`` is ``'jezdez.example.com'``.

    Later, in your views, you can nicely refer to the current site
    as ``request.site`` for further site-specific functionality.
    """
    request.site = LazySite(request, *args, **kwargs)


def cached_host_site(request, *args, **kwargs):
    """
    A callback function similar to :func:`~django_hosts.callbacks.host_site`
    which caches the resulting :class:`~django.contrib.sites.models.Site`
    instance in the default cache backend for the time specfified as
    :attr:`~django.conf.settings.HOST_SITE_TIMEOUT`.

    :param request: the request object passed from the middleware
    :param \*args: the parameters as matched by the host patterns
    :param \*\*kwargs: the keyed parameters as matched by the host patterns
    """
    request.site = CachedLazySite(request, *args, **kwargs)

########NEW FILE########
__FILENAME__ = defaults
import imp
import os
import re
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_mod_func
from django.utils.encoding import smart_str
from django.utils.functional import memoize
from django.utils.importlib import import_module

_callable_cache = {}  # Maps view and url pattern names to their view functions.


HOST_SCHEME = getattr(settings, 'HOST_SCHEME', '//')
if HOST_SCHEME.endswith(':'):
    HOST_SCHEME = '%s//' % HOST_SCHEME
if '//' not in HOST_SCHEME:
    HOST_SCHEME = '%s://' % HOST_SCHEME


def module_has_submodule(package, module_name):
    """See if 'module' is in 'package'."""
    name = ".".join([package.__name__, module_name])
    try:
        # None indicates a cached miss; see mark_miss() in Python/import.c.
        return sys.modules[name] is not None
    except KeyError:
        pass
    try:
        package_path = package.__path__   # No __path__, then not a package.
    except AttributeError:
        # Since the remainder of this function assumes that we're dealing with
        # a package (module with a __path__), so if it's not, then bail here.
        return False
    for finder in sys.meta_path:
        if finder.find_module(name, package_path):
            return True
    for entry in package_path:
        try:
            # Try the cached finder.
            finder = sys.path_importer_cache[entry]
            if finder is None:
                # Implicit import machinery should be used.
                try:
                    file_, _, _ = imp.find_module(module_name, [entry])
                    if file_:
                        file_.close()
                    return True
                except ImportError:
                    continue
            # Else see if the finder knows of a loader.
            elif finder.find_module(name):
                return True
            else:
                continue
        except KeyError:
            # No cached finder, so try and make one.
            for hook in sys.path_hooks:
                try:
                    finder = hook(entry)
                    # XXX Could cache in sys.path_importer_cache
                    if finder.find_module(name):
                        return True
                    else:
                        # Once a finder is found, stop the search.
                        break
                except ImportError:
                    # Continue the search for a finder.
                    continue
            else:
                # No finder found.
                # Try the implicit import machinery if searching a directory.
                if os.path.isdir(entry):
                    try:
                        file_, _, _ = imp.find_module(module_name, [entry])
                        if file_:
                            file_.close()
                        return True
                    except ImportError:
                        pass
                # XXX Could insert None or NullImporter
    else:
        # Exhausted the search, so the module cannot be found.
        return False


def get_callable(lookup_view, can_fail=False):
    """
    Convert a string version of a function name to the callable object.

    If the lookup_view is not an import path, it is assumed to be a URL pattern
    label and the original string is returned.

    If can_fail is True, lookup_view might be a URL pattern label, so errors
    during the import fail and the string is returned.
    """
    if not callable(lookup_view):
        mod_name, func_name = get_mod_func(lookup_view)
        try:
            if func_name != '':
                lookup_view = getattr(import_module(mod_name), func_name)
                if not callable(lookup_view):
                    raise ImproperlyConfigured("Could not import %s.%s." %
                                               (mod_name, func_name))
        except AttributeError:
            if not can_fail:
                raise ImproperlyConfigured("Could not import %s. Callable "
                                           "does not exist in module %s." %
                                           (lookup_view, mod_name))
        except ImportError:
            parentmod, submod = get_mod_func(mod_name)
            if (not can_fail and submod != '' and
                    not module_has_submodule(import_module(parentmod), submod)):
                raise ImproperlyConfigured("Could not import %s. Parent "
                                           "module %s does not exist." %
                                           (lookup_view, mod_name))
            if not can_fail:
                raise
    return lookup_view
get_callable = memoize(get_callable, _callable_cache, 1)


def patterns(prefix, *args):
    """
    The function to define the list of hosts (aka host confs), e.g.::

        from django_hosts import patterns

        host_patterns = patterns('path.to',
            (r'www', 'urls.default', 'default'),
            (r'api', 'urls.api', 'api'),
        )

    :param prefix: the URLconf prefix to pass to the host object
    :type prefix: str
    :param \*args: a list of :class:`~django_hosts.defaults.hosts` instances
                   or an iterable thereof
    """
    hosts = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            arg = host(prefix=prefix, *arg)
        else:
            arg.add_prefix(prefix)
        name = arg.name
        if name in [h.name for h in hosts]:
            raise ImproperlyConfigured("Duplicate host name: %s" % name)
        hosts.append(arg)
    return hosts


class host(object):
    """
    The host object used in host conf together with the
    :func:`django_hosts.defaults.patterns` function, e.g.::

        from django_hosts import patterns, host

        host_patterns = patterns('path.to',
            host(r'www', 'urls.default', name='default'),
            host(r'api', 'urls.api', name='api'),
            host(r'admin', 'urls.admin', name='admin', scheme='https://'),
        )

    :param regex: a regular expression to be used to match the request's
                  host.
    :type regex: str
    :param urlconf: the dotted path of a URLconf module of the host
    :type urlconf: str
    :param callback: a callable or the dotted path of a callable to be used
                     when matching has happened
    :type callback: callable or str
    :param prefix: the prefix to apply to the ``urlconf`` parameter
    :type prefix: str
    :param scheme: the scheme to prepend host names with during reversing,
                   e.g.  when using the host_url() template tag. Defaults to
                   :attr:`~django.conf.settings.HOST_SCHEME`.
    :type scheme: str
    """
    def __init__(self, regex, urlconf, name, callback=None, prefix='',
                 scheme=HOST_SCHEME):
        """
        Compile hosts. We add a literal fullstop to the end of every
        pattern to avoid rather unwieldy escaping in every definition.
        """
        self.regex = regex
        self.compiled_regex = re.compile(r'%s(\.|$)' % regex)
        self.urlconf = urlconf
        self.name = name
        self.scheme = scheme
        if callable(callback):
            self._callback = callback
        else:
            self._callback, self._callback_str = None, callback
        self.add_prefix(prefix)

    def __repr__(self):
        return smart_str('<%s %s: %s (%r)>' %
                         (self.__class__.__name__, self.name,
                          self.urlconf, self.regex))

    @property
    def callback(self):
        if self._callback is not None:
            return self._callback
        elif self._callback_str is None:
            return lambda *args, **kwargs: None
        try:
            self._callback = get_callable(self._callback_str)
        except ImportError as e:
            mod_name, _ = get_mod_func(self._callback_str)
            raise ImproperlyConfigured("Could not import '%s'. "
                                       "Error was: %s" %
                                       (mod_name, str(e)))
        except AttributeError as e:
            mod_name, func_name = get_mod_func(self._callback_str)
            raise ImproperlyConfigured("Tried '%s' in module '%s'. "
                                       "Error was: %s" %
                                       (func_name, mod_name, str(e)))
        return self._callback

    def add_prefix(self, prefix=''):
        """
        Adds the prefix string to a string-based urlconf.
        """
        if prefix:
            self.urlconf = prefix.rstrip('.') + '.' + self.urlconf

########NEW FILE########
__FILENAME__ = managers
from django.conf import settings
from django.db import models
from django.db.models.fields import FieldDoesNotExist


class HostSiteManager(models.Manager):
    """
    A model manager to limit objects to those associated with a site.

    :param field_name: the name of the related field pointing at the
                       :class:`~django.contrib.sites.models.Site` model,
                       or a series of relations using the
                       ``field1__field2__field3`` notation. Falls back
                       to looking for 'site' and 'sites' fields.
    :param select_related: a boolean specifying whether to use
                           :meth:`~django.db.models.QuerySet.select_related`
                           when querying the database

    Define a manager instance in your model class with one
    of the following notations::

        on_site = HostSiteManager()  # automatically looks for site and sites
        on_site = HostSiteManager("author__site")
        on_site = HostSiteManager("author__blog__site")
        on_site = HostSiteManager("author__blog__site",
                                  select_related=False)

    Then query against it with one of the manager methods::

        def home_page(request):
            posts = BlogPost.on_site.by_request(request).all()
            return render(request, 'home_page.html', {'posts': posts})

    """
    def __init__(self, field_name=None, select_related=True):
        super(HostSiteManager, self).__init__()
        self._field_name = field_name
        self._select_related = select_related
        self._depth = 1
        self._is_validated = False

    def _validate_field_name(self):
        field_names = self.model._meta.get_all_field_names()

        # If a custom name is provided, make sure the field exists on the model
        if self._field_name is not None:
            name_parts = self._field_name.split("__", 1)
            rel_depth = len(name_parts)
            if rel_depth > self._depth:
                self._depth = rel_depth
            field_name = name_parts[0]
            if field_name not in field_names:
                raise ValueError("%s couldn't find a field named %s in %s." %
                                 (self.__class__.__name__, field_name,
                                  self.model._meta.object_name))

        # Otherwise, see if there is a field called either 'site' or 'sites'
        else:
            for potential_name in ['site', 'sites']:
                if potential_name in field_names:
                    self._field_name = field_name = potential_name
                    self._is_validated = True
                    break
                else:
                    field_name = None

        # Now do a type check on the field (FK or M2M only)
        try:
            field = self.model._meta.get_field(field_name)
            if not isinstance(field, (models.ForeignKey,
                                      models.ManyToManyField)):
                raise TypeError("%s must be a ForeignKey or "
                                "ManyToManyField." % field_name)
        except FieldDoesNotExist:
            raise ValueError("%s couldn't find a field named %s in %s." %
                             (self.__class__.__name__, field_name,
                              self.model._meta.object_name))
        self._is_validated = True

    def get_query_set(self, site_id=None):
        if site_id is None:
            site_id = settings.SITE_ID
        if not self._is_validated:
            self._validate_field_name()
        qs = super(HostSiteManager, self).get_query_set()
        if self._select_related:
            qs = qs.select_related(depth=self._depth)
        return qs.filter(**{'%s__id__exact' % self._field_name: site_id})

    def by_id(self, site_id=None):
        """
        Returns a queryset matching the given site id. If not given
        this falls back to the ``SITE_ID`` setting.

        :param site_id: the ID of the site
        :rtype: :class:`~django.db.models.query.QuerySet`
        """
        return self.get_query_set(site_id)

    def by_request(self, request):
        """
        Returns a queryset matching the given request's site
        attribute.

        :param request: the current request
        :type request: :class:`~django.http.HttpRequest`
        :rtype: :class:`~django.db.models.query.QuerySet`
        """
        if not hasattr(request, "site") or request.site is None:
            return self.none()
        return self.by_site(request.site)

    def by_site(self, site):
        """
        Returns a queryset matching the given site.

        :param site: a site instance
        :type site: :class:`~django.contrib.sites.models.Site`
        :rtype: :class:`~django.db.models.query.QuerySet`
        """
        return self.by_id(site.id)

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import NoReverseMatch, set_urlconf, get_urlconf

from django_hosts.reverse import get_host_patterns, get_host

hosts_middleware = "django_hosts.middleware.HostsMiddleware"
toolbar_middleware = "debug_toolbar.middleware.DebugToolbarMiddleware"


class HostsMiddleware(object):
    """
    Adjust incoming request's urlconf based on hosts defined in
    settings.ROOT_HOSTCONF module.
    """
    def __init__(self):
        self.host_patterns = get_host_patterns()
        try:
            self.default_host = get_host(settings.DEFAULT_HOST)
        except AttributeError:
            raise ImproperlyConfigured("Missing DEFAULT_HOST setting")
        except NoReverseMatch as e:
            raise ImproperlyConfigured("Invalid DEFAULT_HOST setting: %s" % e)

        middlewares = list(settings.MIDDLEWARE_CLASSES)
        try:
            if (middlewares.index(hosts_middleware) >
                    middlewares.index(toolbar_middleware)):
                raise ImproperlyConfigured(
                    "The django_hosts and debug_toolbar middlewares "
                    "are in the wrong order. Make sure %r comes before "
                    "%r in the MIDDLEWARE_CLASSES setting." %
                    (hosts_middleware, toolbar_middleware))
        except ValueError:
            # django-debug-toolbar middleware doesn't seem to be installed
            pass

    def get_host(self, request_host):
        for host in self.host_patterns:
            match = host.compiled_regex.match(request_host)
            if match:
                return host, match.groupdict()
        return self.default_host, {}

    def process_request(self, request):
        # Find best match, falling back to settings.DEFAULT_HOST
        host, kwargs = self.get_host(request.get_host())
        # This is the main part of this middleware
        request.urlconf = host.urlconf
        request.host = host
        # But we have to temporarily override the URLconf
        # already to allow correctly reversing host URLs in
        # the host callback, if needed.
        current_urlconf = get_urlconf()
        try:
            set_urlconf(host.urlconf)
            return host.callback(request, **kwargs)
        finally:
            # Reset URLconf for this thread on the way out for complete
            # isolation of request.urlconf
            set_urlconf(current_urlconf)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = reverse
import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import NoReverseMatch, reverse
from django.utils import six
from django.utils.encoding import iri_to_uri, force_text
from django.utils.functional import memoize, lazy
from django.utils.importlib import import_module
from django.utils.regex_helper import normalize

from django_hosts.defaults import host as host_cls

_hostconf_cache = {}
_hostconf_module_cache = {}
_host_patterns_cache = {}
_host_cache = {}


def get_hostconf():
    try:
        return settings.ROOT_HOSTCONF
    except AttributeError:
        raise ImproperlyConfigured("Missing ROOT_HOSTCONF setting")
get_hostconf = memoize(get_hostconf, _hostconf_cache, 0)


def get_hostconf_module(hostconf=None):
    if hostconf is None:
        hostconf = get_hostconf()
    return import_module(hostconf)
get_hostconf_module = memoize(get_hostconf_module, _hostconf_module_cache, 1)


def get_host(name):
    for host in get_host_patterns():
        if host.name == name:
            return host
    raise NoReverseMatch("No host called '%s' exists" % name)
get_host = memoize(get_host, _host_cache, 1)


def get_host_patterns():
    hostconf = get_hostconf()
    module = get_hostconf_module(hostconf)
    try:
        return module.host_patterns
    except AttributeError:
        raise ImproperlyConfigured("Missing host_patterns in '%s'" %
                                   hostconf)
get_host_patterns = memoize(get_host_patterns, _host_patterns_cache, 0)


def clear_host_caches():
    global _hostconf_cache, _hostconf_module_cache, _host_patterns_cache, _host_cache
    _hostconf_cache.clear()
    _hostconf_module_cache.clear()
    _host_patterns_cache.clear()
    _host_cache.clear()


def reverse_host(host, args=None, kwargs=None):
    """
    Given the host name and the appropriate parameters,
    reverses the host, e.g.::

        >>> from django.conf import settings
        >>> settings.ROOT_HOSTCONF = 'mysite.hosts'
        >>> settings.PARENT_HOST = 'example.com'
        >>> from django_hosts.reverse import reverse_host
        >>> reverse_host('with_username', 'jezdez')
        'jezdez.example.com'

    :param name: the name of the host as specified in the hostconf
    :args: the host arguments to use to find a matching entry in the hostconf
    :kwargs: similar to args but key value arguments
    :raises django.core.urlresolvers.NoReverseMatch: if no host matches
    :rtype: reversed hostname
    """
    if args and kwargs:
        raise ValueError("Don't mix *args and **kwargs in call to reverse()!")

    args = args or ()
    kwargs = kwargs or {}

    if not isinstance(host, host_cls):
        host = get_host(host)

    unicode_args = [force_text(x) for x in args]
    unicode_kwargs = dict(((k, force_text(v))
                          for (k, v) in six.iteritems(kwargs)))

    for result, params in normalize(host.regex):
        if args:
            if len(args) != len(params):
                continue
            candidate = result % dict(zip(params, unicode_args))
        else:
            if set(kwargs.keys()) != set(params):
                continue
            candidate = result % unicode_kwargs

        if re.match(host.regex, candidate, re.UNICODE):  # pragma: no cover
            parent_host = getattr(settings, 'PARENT_HOST', '').lstrip('.')
            if parent_host:
                # only add the parent host when needed (aka www-less domain)
                if candidate and candidate != parent_host:
                    candidate = '%s.%s' % (candidate, parent_host)
                else:
                    candidate = parent_host
            return candidate

    raise NoReverseMatch("Reverse host for '%s' with arguments '%s' "
                         "and keyword arguments '%s' not found." %
                         (host.name, args, kwargs))


def reverse_full(host, view,
                 host_args=None, host_kwargs=None,
                 view_args=None, view_kwargs=None):
    """
    Given the host and view name and the appropriate parameters,
    reverses the fully qualified URL, e.g.::

        >>> from django.conf import settings
        >>> settings.ROOT_HOSTCONF = 'mysite.hosts'
        >>> settings.PARENT_HOST = 'example.com'
        >>> from django_hosts.reverse import reverse_full
        >>> reverse_full('www', 'about')
        '//www.example.com/about/'

    You can set the used scheme in the host object.

    :param host: the name of the host
    :param view: the name of the view
    :host_args: the host arguments
    :host_kwargs: the host keyed arguments
    :view_args: the arguments of the view
    :view_kwargs: the keyed arguments of the view
    :rtype: fully qualified URL with path
    """
    host = get_host(host)
    host_part = reverse_host(host,
                             args=host_args,
                             kwargs=host_kwargs)
    path_part = reverse(view,
                        args=view_args or (),
                        kwargs=view_kwargs or {},
                        urlconf=host.urlconf)
    return iri_to_uri('%s%s%s' % (host.scheme, host_part, path_part))

reverse_full_lazy = lazy(reverse_full, str)

########NEW FILE########
__FILENAME__ = hosts
import re
from django import template
from django.conf import settings
from django.template import TemplateSyntaxError
from django.utils import six
from django.utils.encoding import smart_str

from django_hosts.reverse import reverse_full

register = template.Library()

kwarg_re = re.compile(r"(?:(\w+)=)?(.+)")


class HostURLNode(template.Node):

    @classmethod
    def parse_params(cls, parser, bits):
        args, kwargs = [], {}
        for bit in bits:
            name, value = kwarg_re.match(bit).groups()
            if name:
                kwargs[name] = parser.compile_filter(value)
            else:
                args.append(parser.compile_filter(value))
        return args, kwargs

    @classmethod
    def handle_token(cls, parser, token):
        bits = token.split_contents()
        name = bits[0]
        if len(bits) < 2:
            raise TemplateSyntaxError("'%s' takes at least 1 argument" % name)
        view = bits[1]
        bits = bits[1:]  # Strip off view
        asvar = None
        if 'as' in bits:
            pivot = bits.index('as')
            try:
                asvar = bits[pivot + 1]
            except IndexError:
                raise TemplateSyntaxError("'%s' arguments must include "
                                          "a variable name after 'as'" % name)
            del bits[pivot:pivot + 2]
        try:
            pivot = bits.index('on')
            try:
                host = bits[pivot + 1]
            except IndexError:
                raise TemplateSyntaxError("'%s' arguments must include "
                                          "a host after 'on'" % name)
            view_args, view_kwargs = cls.parse_params(parser, bits[1:pivot])
            host_args, host_kwargs = cls.parse_params(parser, bits[pivot + 2:])
        except ValueError:
            # No host was given so use the default host
            host = settings.DEFAULT_HOST
            view_args, view_kwargs = cls.parse_params(parser, bits[1:])
            host_args, host_kwargs = (), {}
        return cls(host, view, host_args, host_kwargs, view_args, view_kwargs, asvar)

    def __init__(self, host, view,
                 host_args, host_kwargs, view_args, view_kwargs, asvar):
        self.host = host
        self.view = view
        self.host_args = host_args
        self.host_kwargs = host_kwargs
        self.view_args = view_args
        self.view_kwargs = view_kwargs
        self.asvar = asvar

    def render(self, context):
        host_args = [x.resolve(context) for x in self.host_args]
        host_kwargs = dict((smart_str(k, 'ascii'), v.resolve(context))
                           for k, v in six.iteritems(self.host_kwargs))
        view_args = [x.resolve(context) for x in self.view_args]
        view_kwargs = dict((smart_str(k, 'ascii'), v.resolve(context))
                           for k, v in six.iteritems(self.view_kwargs))
        url = reverse_full(self.host, self.view,
                           host_args, host_kwargs, view_args, view_kwargs)
        if self.asvar:
            context[self.asvar] = url
            return ''
        else:
            return url


@register.tag
def host_url(parser, token):
    """
    Simple tag to reverse the URL inclusing a host.

    {% host_url url-name on host-name  %}
    {% host_url url-name on host-name as url_on_host_variable %}
    {% host_url url-name on host-name 'spam' %}
    {% host_url url-name varg1=vvalue1 on host-name 'spam' 'hvalue1' %}
    {% host_url url-name vvalue2 on host-name 'spam' harg2=hvalue2 %}

    """
    return HostURLNode.handle_token(parser, token)

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import, with_statement

from django.conf import settings, UserSettingsHolder
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.base import BaseHandler
from django.test import TestCase, Client
from django.utils.functional import wraps

from ..reverse import clear_host_caches


class override_settings(object):
    """
    Acts as either a decorator, or a context manager.  If it's a decorator it
    takes a function and returns a wrapped function.  If it's a contextmanager
    it's used with the ``with`` statement.  In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """
    def __init__(self, **kwargs):
        self.options = kwargs
        self.wrapped = settings._wrapped

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return inner

    def enable(self):
        override = UserSettingsHolder(settings._wrapped)
        for key, new_value in self.options.items():
            setattr(override, key, new_value)
        settings._wrapped = override

    def disable(self):
        settings._wrapped = self.wrapped


# Adapted from Simon Willison's snippet:
# http://djangosnippets.org/snippets/963/.
try:
    from django.test import RequestFactory
except ImportError:

    class RequestFactory(Client):  # noqa
        """
        Class that lets you create mock Request objects for use in testing.

        Usage:

        rf = RequestFactory()
        get_request = rf.get('/hello/')
        post_request = rf.post('/submit/', {'foo': 'bar'})

        This class re-uses the django.test.client.Client interface, docs here:
        http://www.djangoproject.com/documentation/testing/#the-test-client

        Once you have a request object you can pass it to any view function,
        just as if that view had been hooked up using a URLconf.

        """
        def request(self, **request):
            """
            Similar to parent class, but returns the request object as soon as it
            has created it.
            """
            environ = {
                'HTTP_COOKIE': self.cookies,
                'PATH_INFO': '/',
                'QUERY_STRING': '',
                'REQUEST_METHOD': 'GET',
                'SCRIPT_NAME': '',
                'SERVER_NAME': 'testserver',
                'SERVER_PORT': 80,
                'SERVER_PROTOCOL': 'HTTP/1.1',
            }
            environ.update(self.defaults)
            environ.update(request)
            request = WSGIRequest(environ)

            handler = BaseHandler()
            handler.load_middleware()
            for middleware_method in handler._request_middleware:
                if middleware_method(request):
                    raise Exception("Couldn't create request object - "
                                    "request middleware returned a response")
            return request


class HostsTestCase(TestCase):

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.old_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = tuple(settings.INSTALLED_APPS) + ('django_hosts.tests',)

    def tearDown(self):
        clear_host_caches()
        settings.INSTALLED_APPS = self.old_apps

    def assertRaisesWithMessage(self, error,
                                message, callable, *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error as e:
            self.assertEqual(message, str(e))

    def assertRaisesWithMessageIn(self, error,
                                  message, callable, *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error as e:
            self.assertIn(message, str(e))

    def assertNumQueries(self, num, callable, *args, **kwargs):
        from django.db import connection
        if hasattr(connection, 'use_debug_cursor'):
            old_use_debug_cursor = connection.use_debug_cursor
            connection.use_debug_cursor = True
            old_debug = None
        else:
            old_use_debug_cursor = None
            old_debug = settings.DEBUG
            settings.DEBUG = True
        starting_queries = len(connection.queries)
        try:
            callable(*args, **kwargs)
        finally:
            final_queries = len(connection.queries)
            if old_use_debug_cursor is not None:
                connection.use_debug_cursor = old_use_debug_cursor
            elif old_debug is not None:
                settings.DEBUG = old_debug
            executed = final_queries - starting_queries
            self.assertEqual(executed, num,
                             "%s queries executed, %s expected" %
                             (executed, num))

    def settings(self, **kwargs):
        """
        A context manager that temporarily sets a setting and reverts
        back to the original value when exiting the context.
        """
        return override_settings(**kwargs)

########NEW FILE########
__FILENAME__ = appended
from django_hosts import patterns, host
from django_hosts.tests.hosts.simple import host_patterns

host_patterns += patterns('',
    host(r'special', 'django_hosts.tests.urls.simple', name='special'),
)

########NEW FILE########
__FILENAME__ = blank
from django_hosts import patterns, host

host_patterns = patterns('',
    host(r'', 'django_hosts.tests.urls.simple', name='blank'),
)

########NEW FILE########
__FILENAME__ = simple
from django_hosts import patterns, host

host_patterns = patterns('',
    host(r'example\.com', 'django_hosts.tests.urls.simple',
         name='without_www'),
    host(r'www\.example\.com', 'django_hosts.tests.urls.simple', name='www'),
    host(r'static', 'django_hosts.tests.urls.simple', name='static'),
    host(r'^s(?P<subdomain>\w+)', 'django_hosts.tests.urls.complex',
         name='with_view_kwargs'),
    host(r'wiki\.(?P<domain>\w+)', 'django_hosts.tests.urls.simple',
         callback='django_hosts.callbacks.host_site', name='with_callback'),
    host(r'admin\.(?P<domain>\w+)', 'django_hosts.tests.urls.simple',
         callback='django_hosts.callbacks.cached_host_site',
         name='with_cached_callback'),
    host(r'(?P<username>\w+)', 'django_hosts.tests.urls.simple',
         name='with_kwargs'),
    host(r'(\w+)', 'django_hosts.tests.urls.simple', name='with_args'),
    host(r'scheme', 'django_hosts.tests.urls.simple', name='scheme',
         scheme='https://'),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.sites.models import Site

from django_hosts.managers import HostSiteManager


class Author(models.Model):
    name = models.TextField()
    site = models.ForeignKey(Site)


class BlogPost(models.Model):
    content = models.TextField()
    author = models.ForeignKey(Author)

    objects = models.Manager()
    dead_end = HostSiteManager()
    on_site = HostSiteManager('author__site')
    no_select_related = HostSiteManager('author__site',
                                        select_related=False)
    non_existing = HostSiteManager('blabla')
    non_rel = HostSiteManager('content')

    def __unicode__(self):
        return str(self.id)


class WikiPage(models.Model):
    content = models.TextField()
    site = models.ForeignKey(Site)

    objects = models.Manager()
    on_site = HostSiteManager()

    def __unicode__(self):
        return str(self.id)

########NEW FILE########
__FILENAME__ = test_defaults
from django.core.exceptions import ImproperlyConfigured

from django_hosts.defaults import patterns, host
from django_hosts.reverse import get_host_patterns
from django_hosts.tests.base import HostsTestCase


class PatternsTests(HostsTestCase):

    def test_pattern(self):
        host_patterns = patterns('',
            host(r'api', 'api.urls', name='api'),
        )
        self.assertEqual(len(host_patterns), 1)
        self.assertTrue(isinstance(host_patterns[0], host))
        self.assertEqual(repr(host_patterns[0]),
                         "<host api: api.urls ('api')>")

    def test_pattern_as_tuple(self):
        host_patterns = patterns('',
            (r'api', 'api.urls', 'api'),
        )
        self.assertEqual(len(host_patterns), 1)
        self.assertTrue(isinstance(host_patterns[0], host))

    def test_pattern_with_duplicate(self):
        api_host = host(r'api', 'api.urls', name='api')
        self.assertRaises(ImproperlyConfigured,
                          patterns, '', api_host, api_host)

    def test_pattern_with_prefix(self):
        host_patterns = patterns('mysite',
            host(r'api', 'api.urls', name='api'),
        )
        self.assertEqual(len(host_patterns), 1)
        self.assertTrue(isinstance(host_patterns[0], host))
        self.assertEqual(host_patterns[0].urlconf, 'mysite.api.urls')


class HostTests(HostsTestCase):

    def test_host(self):
        api_host = host(r'api', 'api.urls', name='api')
        self.assertTrue(isinstance(api_host, host))

    def test_host_prefix(self):
        api_host = host(r'api', 'api.urls', name='api', prefix='spam.eggs')
        self.assertEqual(api_host.urlconf, 'spam.eggs.api.urls')

    def test_host_string_callback(self):
        api_host = host(r'api', 'api.urls', name='api',
            callback='django_hosts.reverse.get_host_patterns')
        self.assertEqual(api_host.callback, get_host_patterns)

    def test_host_callable_callback(self):
        api_host = host(r'api', 'api.urls', name='api',
                        callback=get_host_patterns)
        self.assertEqual(api_host.callback, get_host_patterns)

    def test_host_nonexistent_callback(self):
        api_host = host(r'api', 'api.urls', name='api',
                        callback='whatever.non_existent')
        self.assertRaisesWithMessageIn(ImproperlyConfigured,
            "Could not import 'whatever'. Error was: No module named",
            lambda: api_host.callback)

        api_host = host(r'api', 'api.urls', name='api',
                        callback='django_hosts.non_existent')
        self.assertRaisesWithMessageIn(ImproperlyConfigured,
            "Could not import django_hosts.non_existent. "
            "Callable does not exist in module",
            lambda: api_host.callback)

########NEW FILE########
__FILENAME__ = test_middleware
# -*- encoding: utf-8 -*-
from __future__ import absolute_import

from django.core.exceptions import ImproperlyConfigured

from django_hosts.middleware import HostsMiddleware
from django_hosts.tests.base import (override_settings, HostsTestCase,
                                     RequestFactory)


class MiddlewareTests(HostsTestCase):

    def test_missing_hostconf_setting(self):
        self.assertRaisesWithMessage(ImproperlyConfigured,
            'Missing ROOT_HOSTCONF setting', HostsMiddleware)

    @override_settings(ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_missing_default_hosts(self):
        self.assertRaisesWithMessage(ImproperlyConfigured,
            'Missing DEFAULT_HOST setting', HostsMiddleware)

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        DEFAULT_HOST='boo')
    def test_wrong_default_hosts(self):
        self.assertRaisesWithMessage(ImproperlyConfigured,
            "Invalid DEFAULT_HOST setting: No host called 'boo' exists",
            HostsMiddleware)

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        DEFAULT_HOST='www')
    def test_request_urlconf_module(self):
        rf = RequestFactory(HTTP_HOST='other.example.com')
        request = rf.get('/simple/')
        middleware = HostsMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'django_hosts.tests.urls.simple')

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        DEFAULT_HOST='with_view_kwargs')
    def test_fallback_to_defaulthost(self):
        rf = RequestFactory(HTTP_HOST='ss.example.com')
        request = rf.get('/template/test/')
        middleware = HostsMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'django_hosts.tests.urls.complex')

    # @override_settings(
    #     ROOT_HOSTCONF='django_hosts.tests.hosts.multiple',
    #     DEFAULT_HOST='www')
    # def test_multiple_subdomains(self):
    #     rf = RequestFactory(HTTP_HOST='bb.aa.tt.localhost.tld')
    #     request = rf.get('/multiple/')
    #     middleware = HostsMiddleware()
    #     middleware.process_request(request)
    #     self.assertEqual(request.urlconf, 'django_hosts.tests.urls.multiple')

########NEW FILE########
__FILENAME__ = test_reverse
from __future__ import absolute_import, with_statement

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import NoReverseMatch

from django_hosts.tests.base import override_settings, HostsTestCase
from django_hosts.reverse import (get_hostconf_module, get_host_patterns,
    get_host, reverse_host, reverse_full)


class ReverseTest(HostsTestCase):

    @override_settings(ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_reverse_host(self):
        self.assertRaises(ValueError,
            reverse_host, 'with_kwargs', ['spam'], dict(eggs='spam'))
        self.assertRaises(NoReverseMatch,
            reverse_host, 'with_kwargs', ['spam', 'eggs'])
        self.assertRaises(NoReverseMatch,
            reverse_host, 'with_kwargs', [], dict(eggs='spam', spam='eggs'))
        self.assertEqual('johndoe',
            reverse_host('with_kwargs', None, dict(username='johndoe')))
        self.assertEqual(reverse_host('with_args', ['johndoe']), 'johndoe')
        with self.settings(PARENT_HOST='spam.eggs'):
            self.assertEqual(reverse_host('with_args', ['johndoe']),
                             'johndoe.spam.eggs')

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        PARENT_HOST='spam.eggs')
    def test_reverse_full(self):
        self.assertEqual(reverse_full('static', 'simple-direct'),
                         '//static.spam.eggs/simple/')

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        PARENT_HOST='example.com')
    def test_reverse_full_without_www(self):
        self.assertEqual(reverse_full('without_www', 'simple-direct'),
                         '//example.com/simple/')

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        PARENT_HOST='spam.eggs')
    def test_reverse_custom_scheme(self):
        self.assertEqual(reverse_full('scheme', 'simple-direct'),
                         'https://scheme.spam.eggs/simple/')


class UtilityTests(HostsTestCase):

    @override_settings(ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_get_hostconf_module(self):
        from django_hosts.tests.hosts import simple
        self.assertEqual(get_hostconf_module(), simple)

    def test_get_hostconf_module_no_default(self):
        from django_hosts.tests.hosts import simple
        self.assertEqual(
            get_hostconf_module('django_hosts.tests.hosts.simple'), simple)

    def test_missing_host_patterns(self):
        self.assertRaisesWithMessage(ImproperlyConfigured,
            'Missing ROOT_HOSTCONF setting', get_host_patterns)

    @override_settings(ROOT_HOSTCONF='django_hosts.tests.hosts')
    def test_missing_host_patterns_in_module(self):
        self.assertRaisesWithMessage(ImproperlyConfigured,
            "Missing host_patterns in 'django_hosts.tests.hosts'",
            get_host_patterns)

    @override_settings(ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_get_working_host_patterns(self):
        from django_hosts.tests.hosts import simple
        self.assertEqual(get_host_patterns(), simple.host_patterns)

    @override_settings(ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_get_host(self):
        self.assertEqual(get_host('static').name, 'static')
        self.assertRaisesWithMessage(NoReverseMatch,
            "No host called 'non-existent' exists", get_host, 'non-existent')

    @override_settings(ROOT_HOSTCONF='django_hosts.tests.hosts.appended')
    def test_appended_patterns(self):
        self.assertEqual(get_host('special').name, 'special')

########NEW FILE########
__FILENAME__ = test_sites
from __future__ import with_statement

from django.contrib.sites.models import Site

from django_hosts.middleware import HostsMiddleware
from django_hosts.tests.base import (override_settings, HostsTestCase,
                                     RequestFactory)
from django_hosts.tests.models import Author, BlogPost, WikiPage


try:  # pragma: no cover
    from django.utils.functional import empty
except ImportError:  # pragma: no cover
    empty = None  # noqa


class SitesTests(HostsTestCase):

    def setUp(self):
        super(SitesTests, self).setUp()
        self.site1 = Site.objects.create(domain='wiki.site1', name='site1')
        self.site2 = Site.objects.create(domain='wiki.site2', name='site2')
        self.site3 = Site.objects.create(domain='wiki.site3', name='site3')
        self.site4 = Site.objects.create(domain='admin.site4', name='site4')
        self.page1 = WikiPage.objects.create(content='page1', site=self.site1)
        self.page2 = WikiPage.objects.create(content='page2', site=self.site1)
        self.page3 = WikiPage.objects.create(content='page3', site=self.site2)
        self.page4 = WikiPage.objects.create(content='page4', site=self.site3)

        self.author1 = Author.objects.create(name='john', site=self.site1)
        self.author2 = Author.objects.create(name='terry', site=self.site2)
        self.post1 = BlogPost.objects.create(content='post1',
                                             author=self.author1)
        self.post2 = BlogPost.objects.create(content='post2',
                                             author=self.author2)

    def tearDown(self):
        for model in [WikiPage, BlogPost, Author, Site]:
            model.objects.all().delete()

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        DEFAULT_HOST='www')
    def test_sites_callback(self):
        rf = RequestFactory(HTTP_HOST='wiki.site1')
        request = rf.get('/simple/')
        middleware = HostsMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'django_hosts.tests.urls.simple')
        self.assertEqual(request.site.pk, self.site1.pk)

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        DEFAULT_HOST='www')
    def test_sites_cached_callback(self):
        rf = RequestFactory(HTTP_HOST='admin.site4')
        request = rf.get('/simple/')
        middleware = HostsMiddleware()
        middleware.process_request(request)

        get_site = lambda: request.site.domain

        # first checking if there is a db query
        self.assertEqual(request.site._wrapped, empty)
        self.assertNumQueries(1, get_site)
        self.assertEqual(request.site._wrapped, self.site4)

        # resetting the wrapped site instance to check the cache value
        request.site._wrapped = empty
        self.assertNumQueries(0, get_site)
        self.assertEqual(request.site.pk, self.site4.pk)

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        DEFAULT_HOST='www')
    def test_sites_callback_with_parent_host(self):
        rf = RequestFactory(HTTP_HOST='wiki.site2')
        request = rf.get('/simple/')
        middleware = HostsMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'django_hosts.tests.urls.simple')
        self.assertEqual(request.site.pk, self.site2.pk)

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        DEFAULT_HOST='www')
    def test_manager_simple(self):
        rf = RequestFactory(HTTP_HOST='wiki.site2')
        request = rf.get('/simple/')
        middleware = HostsMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'django_hosts.tests.urls.simple')
        self.assertEqual(request.site.pk, self.site2.pk)
        self.assertEqual(list(WikiPage.on_site.by_request(request)),
                         [self.page3])

    @override_settings(
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        DEFAULT_HOST='www')
    def test_manager_missing_site(self):
        rf = RequestFactory(HTTP_HOST='static')
        request = rf.get('/simple/')
        middleware = HostsMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'django_hosts.tests.urls.simple')
        self.assertRaises(AttributeError, lambda: request.site)
        self.assertEqual(list(WikiPage.on_site.by_request(request)), [])

    def test_manager_default_site(self):
        with self.settings(SITE_ID=self.site1.id):
            self.assertEqual(list(WikiPage.on_site.all()),
                             [self.page1, self.page2])

    def test_manager_related_site(self):
        with self.settings(SITE_ID=self.site1.id):
            self.assertEqual(list(BlogPost.on_site.all()), [self.post1])
        with self.settings(SITE_ID=self.site2.id):
            self.assertEqual(list(BlogPost.on_site.all()), [self.post2])

    def test_no_select_related(self):
        with self.settings(SITE_ID=self.site1.id):
            self.assertEqual(list(BlogPost.no_select_related.all()),
                             [self.post1])

    def test_non_existing_field(self):
        with self.settings(SITE_ID=self.site1.id):
            self.assertRaises(ValueError, BlogPost.non_existing.all)

    def test_dead_end_field(self):
        with self.settings(SITE_ID=self.site1.id):
            self.assertRaises(ValueError, BlogPost.dead_end.all)

    def test_non_rel_field(self):
        with self.settings(SITE_ID=self.site1.id):
            self.assertRaises(TypeError, BlogPost.non_rel.all)

########NEW FILE########
__FILENAME__ = test_templatetags
from __future__ import absolute_import, with_statement

from django.template import Template, Context, TemplateSyntaxError, Parser

from django_hosts.templatetags.hosts import HostURLNode
from django_hosts.tests.base import override_settings, HostsTestCase


class TemplateTagsTest(HostsTestCase):

    def render(self, template, context=None):
        if context is None:
            context = Context({})
        return Template(template).render(context).strip()

    @override_settings(
        DEFAULT_HOST='www',
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_host_url_tag_simple(self):
        rendered = self.render(
            "{% load hosts %}{% host_url simple-direct on www %}")
        self.assertEqual(rendered, '//www.example.com/simple/')
        rendered = self.render(
            "{% load hosts %}{% host_url simple-direct on www as "
            "simple_direct_url %}{{ simple_direct_url }} ")
        self.assertEqual(rendered, '//www.example.com/simple/')

    @override_settings(
        DEFAULT_HOST='www',
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_host_url_tag_without_on(self):
        rendered = self.render(
            "{% load hosts %}{% host_url simple-direct %}")
        self.assertEqual(rendered, '//www.example.com/simple/')

    @override_settings(
        DEFAULT_HOST='www',
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_host_url_tag_with_args(self):
        rendered = self.render("{% load hosts %}"
            "{% host_url simple-direct on with_args 'www.eggs.spam' %}")
        self.assertEqual(rendered, '//www.eggs.spam/simple/')
        rendered = self.render("{% load hosts %}"
            "{% host_url simple-direct as yeah on with_args "
            "'www.eggs.spam' %}{{ yeah }}")
        self.assertEqual(rendered, '//www.eggs.spam/simple/')

    @override_settings(
        DEFAULT_HOST='www',
        PARENT_HOST='eggs.spam',
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_host_url_tag_with_kwargs(self):
        rendered = self.render("{% load hosts %}"
            "{% host_url simple-direct on with_kwargs username='johndoe' %}")
        self.assertEqual(rendered, '//johndoe.eggs.spam/simple/')

    @override_settings(
        DEFAULT_HOST='www',
        PARENT_HOST='eggs.spam',
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_host_url_tag_with_view_kwargs(self):
        rendered = self.render("{% load hosts %}"
            "{% host_url complex-direct template='test' on with_view_kwargs "
            "subdomain='test2000' %}")
        self.assertEqual(rendered, '//stest2000.eggs.spam/template/test/')

    @override_settings(
        DEFAULT_HOST='www',
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        PARENT_HOST='eggs.spam')
    def test_host_url_tag_parent_host(self):
        rendered = self.render(
            "{% load hosts %}{% host_url simple-direct on static %}")
        self.assertEqual(rendered, '//static.eggs.spam/simple/')

    @override_settings(
        DEFAULT_HOST='without_www',
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple',
        PARENT_HOST='example.com')
    def test_host_url_no_www(self):
        rendered = self.render(
            "{% load hosts %}{% host_url simple-direct on without_www %}")
        self.assertEqual(rendered, '//example.com/simple/')

    @override_settings(
        DEFAULT_HOST='www',
        ROOT_HOSTCONF='django_hosts.tests.hosts.simple')
    def test_raises_template_syntaxerror(self):
        self.assertRaises(TemplateSyntaxError,
                          self.render, "{% load hosts %}{% host_url %}")
        self.assertRaises(TemplateSyntaxError,
                          self.render,
                          "{% load hosts %}{% host_url simple-direct on %}")
        self.assertRaises(TemplateSyntaxError,
                          self.render,
                          "{% load hosts %}{% host_url simple-direct as %}")
        self.assertRaises(TemplateSyntaxError, HostURLNode.parse_params,
                          Parser(['']), "username=='johndoe'")

########NEW FILE########
__FILENAME__ = complex
from django.conf.urls import patterns, url

urlpatterns = patterns('django_hosts.tests.views',
    url(r'^template/(?P<template>\w+)/$', 'test_view', name='complex-direct'),
)

########NEW FILE########
__FILENAME__ = root
from django.conf.urls import patterns

urlpatterns = patterns('',
)

########NEW FILE########
__FILENAME__ = simple
from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^simple/$', 'django.shortcuts.render', name='simple-direct'),
)

########NEW FILE########
__FILENAME__ = views
def test_view(request, template=None):
    return template

########NEW FILE########
__FILENAME__ = test_settings
DATABASE_ENGINE = 'sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django_hosts',
    'django_hosts.tests',
]

ROOT_URLCONF = 'django_hosts.tests.urls.root'

SITE_ID = 1

SECRET_KEY = 'something-something'

import django

if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-hosts documentation build configuration file, created by
# sphinx-quickstart on Mon Sep 26 16:39:46 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'django_hosts.test_settings'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-hosts'
copyright = u'2011-2012, Jannis Leidel and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
try:
    from django_hosts import __version__
    # The short X.Y version.
    version = '.'.join(__version__.split('.')[:2])
    # The full version, including alpha/beta/rc tags.
    release = __version__
except ImportError:
    version = release = 'dev'

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
#html_static_path = ['_static']

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
htmlhelp_basename = 'django-hostsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-hosts.tex', u'django-hosts Documentation',
   u'Jannis Leidel and contributors', 'manual'),
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
    ('index', 'django-hosts', u'django-hosts Documentation',
     [u'Jannis Leidel and contributors'], 1)
]

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://python.readthedocs.org/en/v2.7.2/', None),
    'django': (
        'https://docs.djangoproject.com/en/dev/',
        'https://docs.djangoproject.com/en/dev/_objects/',
    ),
}

########NEW FILE########
