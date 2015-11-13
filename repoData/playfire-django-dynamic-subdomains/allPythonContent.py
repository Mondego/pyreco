__FILENAME__ = decorators
import functools

from .middleware import _thread_local

def disable_subdomain_middleware(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        prev = getattr(_thread_local, 'enabled', True)

        try:
            _thread_local.enabled = False
            return fn(*args, **kwargs)
        finally:
            _thread_local.enabled = prev

    return wrapped

########NEW FILE########
__FILENAME__ = defaults
from django.core.exceptions import ImproperlyConfigured
from django.utils.datastructures import SortedDict

def patterns(*args):
    subdomains = SortedDict()

    for x in args:
        name = x['name']

        if name in subdomains:
            raise ImproperlyConfigured("Duplicate subdomain name: %s" % name)

        subdomains[name] = x

    return subdomains

class subdomain(dict):
    def __init__(self, regex, urlconf, name, callback=None):
        self.update({
            'regex': regex,
            'urlconf': urlconf,
            'name': name,
        })

        if callback:
            self['callback'] = callback

########NEW FILE########
__FILENAME__ = forms
from django import forms

class RedirectForm(forms.Form):
    domain = forms.CharField()
    path = forms.CharField()

########NEW FILE########
__FILENAME__ = middleware
import re
import threading

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed, ImproperlyConfigured
from django.core.urlresolvers import set_urlconf

from .utils import from_dotted_path

_thread_local = threading.local()

class SubdomainMiddleware(object):
    """
    Adjust incoming request's urlconf based on `settings.SUBDOMAINS`.

    Overview
    ========

    This middleware routes requests to specific subdomains to different URL
    schemes ("urlconf").

    For example, if you own ``example.com`` but want to serve specific content
    at ``api.example.com` and ``beta.example.com``, add the following to your
    ``settings.py``:

        from dynamic_subdomains.defaults import patterns, subdomain

        SUBDOMAINS = patterns(
            subdomain('api', 'path.to.api.urls', name='api'),
            subdomain('beta', 'path.to.beta.urls', name='beta'),
        )

    This causes requests to ``{api,beta}.example.com`` to be routed to their
    corresponding urlconf. You can use your ``urls.py`` as a template for these
    urlconfs.

    Patterns are evaluated in order. If no pattern matches, the request is
    processed in the usual way, ie. using ``settings.ROOT_URLCONF``.

    Pattern format
    ==============

    The patterns on the left-hand side are regular expressions. For example,
    the following ``settings.SUBDOMAINS`` will route ``foo.example.com`` and
    ``bar.example.com`` to the same urlconf.

        SUBDOMAINS = patterns(
            subdomain(r'(foo|bar)', 'path.to.urls', name='foo-or-bar'),
        )

    .. note:

      * Patterns are matched against the extreme left of the requested host

      * It is implied that all patterns end either with a literal full stop
        (ie. ".") or an end of line metacharacter.

      * As with all regular expressions, various metacharacters need quoting.

    Dynamic subdomains using regular expressions
    ============================================

    Patterns being regular expressions allows setups to feature dynamic (or
    "wildcard") subdomain schemes:

        SUBDOMAINS = patterns(
            subdomain('www', ROOT_URLCONF, name='static'),
            subdomain('\w+', 'path.to.custom_urls', name='wildcard'),
        )

    Here, requests to ``www.example.com`` will be routed as normal but a
    request to ``lamby.example.com`` is routed to ``path.to.custom_urls``.

    As patterns are matched in order, we placed ``www`` first as it otherwise
    would have matched against ``\w+`` and thus routed to the wrong
    destination.

    Alternatively, we could have used negative lookahead:

        SUBDOMAINS = patterns(
            subdomain('(?!www)\w+', 'path.to.custom_urls', name='wildcard'),
        )

    Callback methods to simplify dynamic subdomains
    ===============================================

    The previous section outlined using regular expressions to implement
    dynamic subdomains.

    However, inside every view referenced by the target urlconf we would have
    to parse the subdomain from ``request.get_host()`` and lookup its
    corresponding object instance, violating DRY. If these dynamic subdomains
    had a lot of views this would become particularly unwieldy.

    To remedy this, you can optionally specify a callback method to be called
    if your subdomain matches:

        SUBDOMAINS = patterns(
            subdomain('www', ROOT_URLCONF, name='static'),
            subdomain('(?P<username>\w+)', 'path.to.custom_urls',
                callback='path.to.custom_fn', name='with-callback'),
        )

        [..]

        from django.shortcuts import get_object_or_404
        from django.contrib.auth.models import User

        def custom_fn(request, username):
            request.viewing_user = get_object_or_404(User, username=username)

    This example avoids the duplicated work in every view by attaching a
    ``viewing_user`` instance to the request object. Views referenced by the
    "dynamic" urlconf can now assume that this object exists.

    The custom method is called with the ``request`` object and any named
    captured arguments, similar to regular Django url processing.

    Callbacks may return either ``None`` or an ``HttpResponse`` object. If it
    returns ``None``, the request continues to be processed and the appropriate
    view is eventually called. If a callback returns an ``HttpResponse``
    object, that ``HttpResponse`` is returned to the client without any further
    processing.

    .. note:

        Callbacks are executed with the urlconf set to the second argument in
        the ``SUBDOMAINS`` list. For example, in the example above, the
        callback will be executed with the urlconf as ``path.to.custom_urls``
        and not the default urlconf.

        This can cause problems when reversing URLs within your callback as
        they may not be "visible" to ``django.core.urlresolvers.reverse`` as
        they are specified in (eg.) the default urlconf.

        To remedy this, specify the ``urlconf`` parameter when calling
        ``reverse``.

    Notes
    =====

      * When using dynamic subdomains based on user input, ensure users cannot
        specify names that conflict with static subdomains such as "www" or
        their subdomain will not be accessible.

      * Don't forget to add ``handler404`` and ``handler500`` entries for your
        custom urlconfs.
    """

    def __init__(self):
        try:
            settings.SUBDOMAINS
        except AttributeError:
            raise ImproperlyConfigured("Missing settings.SUBDOMAINS setting")

        try:
            self.default = settings.SUBDOMAINS[settings.SUBDOMAIN_DEFAULT]
        except AttributeError:
            raise ImproperlyConfigured(
                "Missing settings.SUBDOMAIN_DEFAULT setting"
            )
        except KeyError:
            raise ImproperlyConfigured(
                "settings.SUBDOMAIN_DEFAULT does not point to a valid domain"
            )

        if not settings.SUBDOMAINS:
            raise MiddlewareNotUsed()

        # Compile subdomains. We add a literal fullstop to the end of every
        # pattern to avoid rather unwieldy escaping in every definition.
        for subdomain in settings.SUBDOMAINS.values():
            callback = subdomain.get('callback', lambda *args, **kwargs: None)
            if isinstance(callback, (basestring,)):
                callback = from_dotted_path(callback)

            subdomain['_regex'] = re.compile(r'%s(\.|$)' % subdomain['regex'])
            subdomain['_callback'] = callback

    def process_request(self, request):
        if not getattr(_thread_local, 'enabled', True):
            return

        host = request.get_host()

        # Find best match, falling back to settings.SUBDOMAIN_DEFAULT
        for subdomain in settings.SUBDOMAINS.values():
            match = subdomain['_regex'].match(host)
            if match:
                kwargs = match.groupdict()
                break
        else:
            kwargs = {}
            subdomain = self.default

        urlconf = subdomain['urlconf']
        callback = subdomain['_callback']

        request.urlconf = urlconf
        try:
            set_urlconf(urlconf)
            return callback(request, **kwargs)
        finally:
            set_urlconf(None)

########NEW FILE########
__FILENAME__ = models
import debug_toolbar.urls

from django.conf import settings
from django.conf.urls import patterns, include

from .urls import urlpatterns

debug_toolbar.urls.urlpatterns += patterns('',
    ('', include(urlpatterns)),
)

########NEW FILE########
__FILENAME__ = panels
from debug_toolbar.panels import DebugPanel

from django.http.utils import fix_location_header
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.core.handlers.base import BaseHandler

class SubdomainPanel(DebugPanel):
    """
    Panel that allows you to alter the subdomain you are viewing the site
    without /etc/hosts hacks.
    """

    name = 'Subdomain'
    has_content = True

    def nav_title(self):
        return _("Subdomain")

    def nav_subtitle(self):
        return self.domain

    def url(self):
        return ''

    def title(self):
        return _("Subdomain navigation")

    def content(self):
        context = self.context.copy()
        context['domain'] = self.domain
        return render_to_string('subdomains/panel.html', context)

    def process_request(self, request):
        self.domain = request.COOKIES.get('_domain')

        request.META.pop('HTTP_HOST', '')
        if self.domain:
            request.META['HTTP_HOST'] = self.domain

            # django.http.utils.fix_location_header rewrites any relative
            # Location header to an absolute one. For example:
            #
            #    Location: /foo   ==>   Location: http://sub.example.com/foo
            #
            # This causes problems when testing subdomains locally so we remove
            # it here.

            try:
                BaseHandler.response_fixes.remove(fix_location_header)
            except ValueError:
                pass

########NEW FILE########
__FILENAME__ = reverse
import re
import urllib

from django.conf import settings
from django.utils.encoding import force_unicode
from django.core.urlresolvers import NoReverseMatch, reverse
from django.utils.regex_helper import normalize

def urlconf_from_subdomain(name):
    try:
        return settings.SUBDOMAINS[name]['urlconf']
    except KeyError:
        raise NoReverseMatch("No %r subdomain exists" % name)

def reverse_subdomain(name, args=(), kwargs=None):
    if args and kwargs:
        raise ValueError("Don't mix *args and **kwargs in call to reverse()!")

    if kwargs is None:
        kwargs = {}

    try:
        subdomain = settings.SUBDOMAINS[name]
    except KeyError:
        raise NoReverseMatch("No subdomain called %s exists" % name)

    unicode_args = [force_unicode(x) for x in args]
    unicode_kwargs = dict([(k, force_unicode(v)) for (k, v) in kwargs.items()])

    for result, params in normalize(subdomain['regex']):
        if args:
            if len(args) != len(params):
                continue
            candidate = result % dict(zip(params, unicode_args))
        else:
            if set(kwargs.keys()) != set(params):
                continue
            candidate = result % unicode_kwargs

        if re.match(subdomain['regex'], candidate, re.UNICODE):
            return candidate

    raise NoReverseMatch(
        "Reverse subdomain for '%s' with arguments '%s' and keyword arguments "
        "'%s' not found." % (name, args, kwargs)
    )

def reverse_crossdomain_part(subdomain, path, subdomain_args=(), subdomain_kwargs=None, mangle=True):
    if subdomain_kwargs is None:
        subdomain_kwargs = {}


    domain_part = reverse_subdomain(
        subdomain,
        args=subdomain_args,
        kwargs=subdomain_kwargs,
    )

    if mangle and getattr(settings, 'EMULATE_SUBDOMAINS', settings.DEBUG):
        return '%s?%s' % (
            reverse('debug-subdomain-redirect'),
            urllib.urlencode((
                ('domain', domain_part),
                ('path', path),
            ))
        )

    return u'//%s%s' % (domain_part, path)

def reverse_path(subdomain, view, args=(), kwargs=None):
    if kwargs is None:
        kwargs = {}

    try:
        urlconf = settings.SUBDOMAINS[subdomain]['urlconf']
    except KeyError:
        raise NoReverseMatch("No subdomain called %s exists" % subdomain)

    return reverse(view, args=args, kwargs=kwargs, urlconf=urlconf)

def reverse_crossdomain(subdomain, view, subdomain_args=(), subdomain_kwargs=None, view_args=(), view_kwargs=None, mangle=True):

    path = reverse_path(subdomain, view, view_args, view_kwargs)

    return reverse_crossdomain_part(
        subdomain,
        path,
        subdomain_args,
        subdomain_kwargs,
        mangle=mangle,
    )

########NEW FILE########
__FILENAME__ = dynamic_subdomains
from django import template
from django.conf import settings
from django.template import TemplateSyntaxError
from django.utils.encoding import smart_str
from django.template.defaulttags import kwarg_re

from ..reverse import reverse_crossdomain

register = template.Library()

@register.tag
def domain_url(parser, token, mangle=True):
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least 1 argument" % bits[0])

    view = parser.compile_filter(bits[1])
    bits = bits[1:] # Strip off view

    try:
        pivot = bits.index('on')

        try:
            domain = bits[pivot + 1]
        except IndexError:
            raise TemplateSyntaxError(
                "'%s' arguments must include a domain after 'on'" % bits[0]
            )

        view_args, view_kwargs = parse_args_kwargs(parser, bits[1:pivot])
        domain_args, domain_kwargs = parse_args_kwargs(parser, bits[pivot+2:])

    except ValueError:
        # No "on <subdomain>" was specified so use the default domain
        domain = settings.SUBDOMAIN_DEFAULT
        view_args, view_kwargs = parse_args_kwargs(parser, bits[1:])
        domain_args, domain_kwargs = (), {}

    return DomainURLNode(
        domain, view, domain_args, domain_kwargs, view_args, view_kwargs, mangle
    )

@register.tag
def domain_url_no_mangle(parser, token):
    return domain_url(parser, token, mangle=False)

class DomainURLNode(template.Node):
    def __init__(self, subdomain, view, subdomain_args, subdomain_kwargs, view_args, view_kwargs, mangle):
        self.subdomain = subdomain
        self.view = view

        self.subdomain_args = subdomain_args
        self.subdomain_kwargs = subdomain_kwargs

        self.view_args = view_args
        self.view_kwargs = view_kwargs

        self.mangle = mangle

    def render(self, context):
        subdomain_args = [x.resolve(context) for x in self.subdomain_args]
        subdomain_kwargs = dict((smart_str(k, 'ascii'), v.resolve(context))
            for k, v in self.subdomain_kwargs.items())

        view_args = [x.resolve(context) for x in self.view_args]
        view_kwargs = dict((smart_str(k, 'ascii'), v.resolve(context))
            for k, v in self.view_kwargs.items())

        return reverse_crossdomain(
            self.subdomain,
            self.view.resolve(context),
            subdomain_args,
            subdomain_kwargs,
            view_args,
            view_kwargs,
            self.mangle,
        )

def parse_args_kwargs(parser, bits):
    args = []
    kwargs = {}

    for bit in bits:
        match = kwarg_re.match(bit)
        if not match:
            raise TemplateSyntaxError("Malformed arguments to domain_url tag")

        name, value = match.groups()
        if name:
            kwargs[name] = parser.compile_filter(value)
        else:
            args.append(parser.compile_filter(value))

    return args, kwargs

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from debug_toolbar.urls import _PREFIX

urlpatterns = patterns('dynamic_subdomains.views',
    url(r'^%s/subdomain/redirect/$' % _PREFIX, 'redirect',
        name='debug-subdomain-redirect'),
)

########NEW FILE########
__FILENAME__ = utils
def from_dotted_path(fullpath):
    """
    Returns the specified attribute of a module, specified by a string.

    ``from_dotted_path('a.b.c.d')`` is roughly equivalent to::

        from a.b.c import d

    except that ``d`` is returned and not entered into the current namespace.
    """

    module, attr = fullpath.rsplit('.', 1)

    return getattr(
        __import__(module, {}, {}, (attr,)),
        attr,
    )

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect, HttpResponseBadRequest

from .forms import RedirectForm

def redirect(request):
    form = RedirectForm(request.GET)

    if not form.is_valid():
        return HttpResponseBadRequest(repr(form.errors))

    response = HttpResponseRedirect(form.cleaned_data['path'])
    response.set_cookie('_domain', form.cleaned_data['domain'])
    response.status_code = 307 # Re-submit POST requests

    return response

########NEW FILE########
