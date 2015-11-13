__FILENAME__ = common
import os
import warnings

from django import dispatch
from jinja2 import Environment, loaders
from jinja2 import defaults as jinja2_defaults
from coffin.template import Library as CoffinLibrary

__all__ = ('env',)

env = None

_JINJA_I18N_EXTENSION_NAME = 'jinja2.ext.i18n'

class CoffinEnvironment(Environment):
    def __init__(self, filters={}, globals={}, tests={}, loader=None, extensions=[], **kwargs):
        if not loader:
            loader = loaders.ChoiceLoader(self._get_loaders())
        all_ext = self._get_all_extensions()

        extensions.extend(all_ext['extensions'])
        super(CoffinEnvironment, self).__init__(
            extensions=extensions,
            loader=loader,
            **kwargs
        )
        # Note: all_ext already includes Jinja2's own builtins (with
        # the proper priority), so we want to assign to these attributes.
        self.filters = all_ext['filters'].copy()
        self.filters.update(filters)
        self.globals.update(all_ext['globals'])
        self.globals.update(globals)
        self.tests = all_ext['tests'].copy()
        self.tests.update(tests)
        for key, value in all_ext['attrs'].items():
            setattr(self, key, value)

        from coffin.template import Template as CoffinTemplate
        self.template_class = CoffinTemplate

    def _get_loaders(self):
        """Tries to translate each template loader given in the Django settings
        (:mod:`django.settings`) to a similarly-behaving Jinja loader.
        Warns if a similar loader cannot be found.
        Allows for Jinja2 loader instances to be placed in the template loader
        settings.
        """
        loaders = []

        from coffin.template.loaders import jinja_loader_from_django_loader
        from jinja2.loaders import BaseLoader as JinjaLoader

        from django.conf import settings
        _loaders = getattr(settings, 'JINJA2_TEMPLATE_LOADERS', settings.TEMPLATE_LOADERS)
        for loader in _loaders:
            if isinstance(loader, JinjaLoader):
                loaders.append(loader)
            else:
                loader_name = args = None
                if isinstance(loader, basestring):
                    loader_name = loader
                    args = []
                elif isinstance(loader, (tuple, list)):
                    loader_name = loader[0]
                    args = loader[1]

                if loader_name:
                    loader_obj = jinja_loader_from_django_loader(loader_name, args)
                    if loader_obj:
                        loaders.append(loader_obj)
                        continue

                warnings.warn('Cannot translate loader: %s' % loader)
        return loaders

    def _get_templatelibs(self):
        """Return an iterable of template ``Library`` instances.

        Since we cannot support the {% load %} tag in Jinja, we have to
        register all libraries globally.
        """
        from django.conf import settings
        from django.template import (
            get_library, import_library, InvalidTemplateLibrary)

        libs = []
        for app in settings.INSTALLED_APPS:
            ns = app + '.templatetags'
            try:
                path = __import__(ns, {}, {}, ['__file__']).__file__
                path = os.path.dirname(path)  # we now have the templatetags/ directory
            except ImportError:
                pass
            else:
                for filename in os.listdir(path):
                    if filename == '__init__.py' or filename.startswith('.'):
                        continue

                    if filename.endswith('.py'):
                        try:
                            module = "%s.%s" % (ns, os.path.splitext(filename)[0])
                            l = import_library(module)
                            libs.append(l)

                        except InvalidTemplateLibrary:
                            pass

        # In addition to loading application libraries, support a custom list
        for libname in getattr(settings, 'JINJA2_DJANGO_TEMPLATETAG_LIBRARIES', ()):
            libs.append(get_library(libname))

        return libs

    def _get_all_extensions(self):
        from django.conf import settings
        from django.template import builtins as django_builtins
        from coffin.template import builtins as coffin_builtins
        from django.core.urlresolvers import get_callable

        # Note that for extensions, the order in which we load the libraries
        # is not maintained (https://github.com/mitsuhiko/jinja2/issues#issue/3).
        # Extensions support priorities, which should be used instead.
        extensions, filters, globals, tests, attrs = [], {}, {}, {}, {}
        def _load_lib(lib):
            if not isinstance(lib, CoffinLibrary):
                # If this is only a standard Django library,
                # convert it. This will ensure that Django
                # filters in that library are converted and
                # made available in Jinja.
                lib = CoffinLibrary.from_django(lib)
            extensions.extend(getattr(lib, 'jinja2_extensions', []))
            filters.update(getattr(lib, 'jinja2_filters', {}))
            globals.update(getattr(lib, 'jinja2_globals', {}))
            tests.update(getattr(lib, 'jinja2_tests', {}))
            attrs.update(getattr(lib, 'jinja2_environment_attrs', {}))

        # Start with Django's builtins; this give's us all of Django's
        # filters courtasy of our interop layer.
        for lib in django_builtins:
            _load_lib(lib)

        # The stuff Jinja2 comes with by default should override Django.
        filters.update(jinja2_defaults.DEFAULT_FILTERS)
        tests.update(jinja2_defaults.DEFAULT_TESTS)
        globals.update(jinja2_defaults.DEFAULT_NAMESPACE)

        # Our own set of builtins are next, overwriting Jinja2's.
        for lib in coffin_builtins:
            _load_lib(lib)

        # Optionally, include the i18n extension.
        if settings.USE_I18N:
            extensions.append(_JINJA_I18N_EXTENSION_NAME)

        # Next, add the globally defined extensions
        extensions.extend(list(getattr(settings, 'JINJA2_EXTENSIONS', [])))
        def from_setting(setting, values_must_be_callable = False):
            retval = {}
            setting = getattr(settings, setting, {})
            if isinstance(setting, dict):
                for key, value in setting.iteritems():
                    if values_must_be_callable and not callable(value):
                        value = get_callable(value)
                    retval[key] = value
            else:
                for value in setting:
                    if values_must_be_callable and not callable(value):
                        value = get_callable(value)
                    retval[value.__name__] = value
            return retval

        tests.update(from_setting('JINJA2_TESTS', True))
        filters.update(from_setting('JINJA2_FILTERS', True))
        globals.update(from_setting('JINJA2_GLOBALS'))

        # Finally, add extensions defined in application's templatetag libraries
        for lib in self._get_templatelibs():
            _load_lib(lib)

        return dict(
            extensions=extensions,
            filters=filters,
            globals=globals,
            tests=tests,
            attrs=attrs,
        )

def get_env():
    """
    :return: A Jinja2 environment singleton.
    """
    from django.conf import settings

    kwargs = {
        'autoescape': True,
    }
    kwargs.update(getattr(settings, 'JINJA2_ENVIRONMENT_OPTIONS', {}))

    result = CoffinEnvironment(**kwargs)
    # Hook Jinja's i18n extension up to Django's translation backend
    # if i18n is enabled; note that we differ here from Django, in that
    # Django always has it's i18n functionality available (that is, if
    # enabled in a template via {% load %}), but uses a null backend if
    # the USE_I18N setting is disabled. Jinja2 provides something similar
    # (install_null_translations), but instead we are currently not
    # enabling the extension at all when USE_I18N=False.
    # While this is basically an incompatibility with Django, currently
    # the i18n tags work completely differently anyway, so for now, I
    # don't think it matters.
    if settings.USE_I18N:
        from django.utils import translation
        result.install_gettext_translations(translation)

    return result

env = get_env()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *

handler404 = 'coffin.views.defaults.page_not_found'
handler500 = 'coffin.views.defaults.server_error'

########NEW FILE########
__FILENAME__ = admin
from django.contrib.auth.admin import *
########NEW FILE########
__FILENAME__ = backends
from django.contrib.auth.backends import *
########NEW FILE########
__FILENAME__ = decorators
from django.contrib.auth.decorators import *
########NEW FILE########
__FILENAME__ = forms
from django.contrib.auth.forms import *
########NEW FILE########
__FILENAME__ = handlers
from django.contrib.auth.handlers import *
########NEW FILE########
__FILENAME__ = middleware
from django.contrib.auth.middleware import *
########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import *
########NEW FILE########
__FILENAME__ = tokens
from django.contrib.auth.tokens import *
########NEW FILE########
__FILENAME__ = urls
import inspect

from django.contrib.auth import urls

exec inspect.getsource(urlpatterns)\
        .replace('django.contrib.auth.views', 'coffin.contrib.auth.views')
########NEW FILE########
__FILENAME__ = views
import inspect

from django.contrib.auth.views import *

# XXX: maybe approach this as importing the entire model, and doing string replacements
# on the template and shortcut import lines?

from coffin.shortcuts import render_to_response
from coffin.template import RequestContext, loader

exec inspect.getsource(logout)
exec inspect.getsource(password_change_done)
exec inspect.getsource(password_reset)
exec inspect.getsource(password_reset_confirm)
exec inspect.getsource(password_reset_done)
exec inspect.getsource(password_reset_complete)

exec inspect.getsource(password_change.view_func)
password_change = login_required(password_change)

# XXX: this function uses a decorator, which calls functools.wraps, which compiles the code
# thus we cannot inspect the source
def login(request, template_name='registration/login.html', redirect_field_name=REDIRECT_FIELD_NAME):
    "Displays the login form and handles the login action."
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            # Light security check -- make sure redirect_to isn't garbage.
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            from django.contrib.auth import login
            login(request, form.get_user())
            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        form = AuthenticationForm(request)
    request.session.set_test_cookie()
    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)
    return render_to_response(template_name, {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }, context_instance=RequestContext(request))
login = never_cache(login)
########NEW FILE########
__FILENAME__ = admin
# coding=utf-8
from django.contrib.flatpages.admin import *

########NEW FILE########
__FILENAME__ = context
# coding=utf-8
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from coffin.common import env


def get_flatpages(starts_with=None, user=None, site_id=None):
    """
    Context-function similar to get_flatpages tag in Django templates.

    Usage:
        <ul>
            {% for page in get_flatpages(starts_with='/about/', user=user, site_id=site.pk) %}
                <li><a href="{{ page.url }}">{{ page.title }}</a></li>
            {% endfor %}
        </ul>

    """
    flatpages = FlatPage.objects.filter(sites__id=site_id or settings.SITE_ID)

    if starts_with:
        flatpages = flatpages.filter(url__startswith=starts_with)

    if not user or not user.is_authenticated():
        flatpages = flatpages.filter(registration_required=False)

    return flatpages

env.globals['get_flatpages'] = get_flatpages

########NEW FILE########
__FILENAME__ = middleware
import inspect

from django.contrib.flatpages.middleware import *
from coffin.contrib.flatpages.views import flatpage

exec inspect.getsource(FlatpageFallbackMiddleware)\

########NEW FILE########
__FILENAME__ = views
# coding=utf-8

from django.contrib.flatpages.models import FlatPage
from django.contrib.flatpages.views import DEFAULT_TEMPLATE
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_protect

from coffin.template import RequestContext, loader

# This view is called from FlatpageFallbackMiddleware.process_response
# when a 404 is raised, which often means CsrfViewMiddleware.process_view
# has not been called even if CsrfViewMiddleware is installed. So we need
# to use @csrf_protect, in case the template needs {% csrf_token %}.
@csrf_protect
def flatpage(request, url):
    """
    Flat page view.

    Models: `flatpages.flatpages`
    Templates: Uses the template defined by the ``template_name`` field,
        or `flatpages/default.html` if template_name is not defined.
    Context:
        flatpage
            `flatpages.flatpages` object
    """
    if not url.endswith('/') and settings.APPEND_SLASH:
        return HttpResponseRedirect("%s/" % request.path)
    if not url.startswith('/'):
        url = "/" + url
    f = get_object_or_404(FlatPage, url__exact=url, sites__id__exact=settings.SITE_ID)
    # If registration is required for accessing this page, and the user isn't
    # logged in, redirect to the login page.
    if f.registration_required and not request.user.is_authenticated():
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.path)
    if f.template_name:
        t = loader.select_template((f.template_name, DEFAULT_TEMPLATE))
    else:
        t = loader.get_template(DEFAULT_TEMPLATE)

    # To avoid having to always use the "|safe" filter in flatpage templates,
    # mark the title and content as already safe (since they are raw HTML
    # content in the first place).
    f.title = mark_safe(f.title)
    f.content = mark_safe(f.content)

    c = RequestContext(request, {
        'flatpage': f,
    })
    response = HttpResponse(t.render(c))
    return response

########NEW FILE########
__FILENAME__ = loader
# -*- coding: utf-8 -*-
"""
A Django template loader wrapper for Coffin that intercepts
requests for "*.jinja" templates, rendering them with Coffin
instead of Django templates.

Usage:

TEMPLATE_LOADERS = (
    'coffin.contrib.loader.AppLoader',
    'coffin.contrib.loader.FileSystemLoader',
)

"""

from os.path import splitext
from coffin.common import env
from django.conf import settings
from django.template.loaders import app_directories, filesystem


JINJA2_DEFAULT_TEMPLATE_EXTENSION = getattr(settings,
    'JINJA2_DEFAULT_TEMPLATE_EXTENSION', ('.jinja',))

if isinstance(JINJA2_DEFAULT_TEMPLATE_EXTENSION, basestring):
    JINJA2_DEFAULT_TEMPLATE_EXTENSION = (JINJA2_DEFAULT_TEMPLATE_EXTENSION,)


class LoaderMixin(object):
    is_usable = True

    def load_template(self, template_name, template_dirs=None):
        extension = splitext(template_name)[1]

        if not extension in JINJA2_DEFAULT_TEMPLATE_EXTENSION:
            return super(LoaderMixin, self).load_template(template_name,
                template_dirs)
        template = env.get_template(template_name)
        return template, template.filename


class FileSystemLoader(LoaderMixin, filesystem.Loader):
    pass


class AppLoader(LoaderMixin, app_directories.Loader):
    pass

########NEW FILE########
__FILENAME__ = static
from coffin import template
from django.contrib.staticfiles.storage import staticfiles_storage
from coffin.templatetags.static import StaticExtension


register = template.Library()


class StaticExtension(StaticExtension):
    """Implements the {% static %} tag as provided by the ``staticfiles``
    contrib module.

    Rreturns the URL to a file using staticfiles' storage backend.

    Usage::

        {% static path [as varname] %}

    Examples::

        {% static "myapp/css/base.css" %}
        {% static variable_with_path %}
        {% static "myapp/css/base.css" as admin_base_css %}
        {% static variable_with_path as varname %}

    """

    @classmethod
    def get_statc_url(cls, path):
        return super(StaticExtension, cls).get_statc_url(
            staticfiles_storage.url(path))


register.tag(StaticExtension)


def static(path):
    return StaticExtension.get_static_url(path)

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.feeds import *       # merge modules

import sys
from django.contrib.syndication.feeds import Feed as DjangoDeprecatedFeed
from django.contrib.syndication.views import Feed as DjangoNewFeed
from coffin.template import loader as coffin_loader
from django import VERSION as DJANGO_VERSION


class Feed(DjangoDeprecatedFeed):
    """Django changed the syndication framework in 1.2. This class
    represents the old way, ported to Coffin. If you are using 1.2,
    you should use the ``Feed`` class in
    ``coffin.contrib.syndication.views``.

    See also there for some notes on what we are doing here.
    """

    def get_feed(self, *args, **kwargs):
        if DJANGO_VERSION < (1,2):
            parent_module = sys.modules[DjangoDeprecatedFeed.__module__]
        else:
            # In Django 1.2, our parent DjangoDeprecatedFeed class really
            # inherits from DjangoNewFeed, so we need to patch the loader
            # in a different module.
            parent_module = sys.modules[DjangoNewFeed.__module__]

        old_loader = parent_module.loader
        parent_module.loader = coffin_loader
        try:
            return super(Feed, self).get_feed(*args, **kwargs)
        finally:
            parent_module.loader = old_loader
########NEW FILE########
__FILENAME__ = views
from django.contrib.syndication.views import *       # merge modules

import sys
from django.contrib.syndication.views import Feed as DjangoFeed
from coffin.template import loader as coffin_loader


class Feed(DjangoFeed):
    """A ``Feed`` implementation that renders it's title and
    description templates using Jinja2.

    Unfortunately, Django's base ``Feed`` class is not very extensible
    in this respect at all. For a real solution, we'd have to essentially
    have to duplicate the whole class. So for now, we use this terrible
    non-thread safe hack.

    Another, somewhat crazy option would be:
        * Render the templates ourselves through Jinja2 (possible
          introduce new attributes to avoid having to rewrite the
          existing ones).
        * Make the rendered result available to Django/the superclass by
          using a custom template loader using a prefix, say
          "feed:<myproject.app.views.MyFeed>". The loader would simply
          return the Jinja-rendered template (escaped), the Django template
          mechanism would find no nodes and just pass the output through.
    Possible even worse than this though.
    """

    def get_feed(self, *args, **kwargs):
        parent_module = sys.modules[DjangoFeed.__module__]
        old_loader = parent_module.loader
        parent_module.loader = coffin_loader
        try:
            return super(Feed, self).get_feed(*args, **kwargs)
        finally:
            parent_module.loader = old_loader
########NEW FILE########
__FILENAME__ = interop
"""Compatibility functions between Jinja2 and Django.

General notes:

  - The Django ``stringfilter`` decorator is supported, but should not be
    used when writing filters specifically for Jinja: It will lose the
    attributes attached to the filter function by Jinja's
    ``environmentfilter`` and ``contextfilter`` decorators, when used
    in the wrong order.

    Maybe coffin should provide a custom version of stringfilter.

  - While transparently converting filters between Django and Jinja works
    for the most part, there is an issue with Django's
    ``mark_for_escaping``, as Jinja does not support a similar mechanism.
    Instead, for Jinja, we escape such strings immediately (whereas Django
    defers it to the template engine).
"""

import inspect
from django.utils.safestring import SafeUnicode, SafeData, EscapeData
from jinja2 import Markup, environmentfilter, Undefined


__all__ = (
    'DJANGO', 'JINJA2',
    'django_filter_to_jinja2',
    'jinja2_filter_to_django',
    'guess_filter_type',)


DJANGO = 'django'
JINJA2 = 'jinja2'


def django_filter_to_jinja2(filter_func):
    """
    Note: Due to the way this function is used by
    ``coffin.template.Library``, it needs to be able to handle native
    Jinja2 filters and pass them through unmodified. This necessity
    stems from the fact that it is not always possible to determine
    the type of a filter.

    TODO: Django's "func.is_safe" is not yet handled
    """
    def _convert_out(v):
        if isinstance(v, SafeData):
            return Markup(v)
        if isinstance(v, EscapeData):
            return Markup.escape(v)       # not 100% equivalent, see mod docs
        return v
    def _convert_in(v):
        if isinstance(v, Undefined):
            # Essentially the TEMPLATE_STRING_IF_INVALID default
            # setting. If a non-default is set, Django wouldn't apply
            # filters. This is something that we neither can nor want to
            # simulate in Jinja.
            return ''
        return v
    def conversion_wrapper(value, *args, **kwargs):
        result = filter_func(_convert_in(value), *args, **kwargs)
        return _convert_out(result)
    # Jinja2 supports a similar machanism to Django's
    # ``needs_autoescape`` filters: environment filters. We can
    # thus support Django filters that use it in Jinja2 with just
    # a little bit of argument rewriting.
    if hasattr(filter_func, 'needs_autoescape'):
        @environmentfilter
        def autoescape_wrapper(environment, *args, **kwargs):
            kwargs['autoescape'] = environment.autoescape
            return conversion_wrapper(*args, **kwargs)
        return autoescape_wrapper
    else:
        return conversion_wrapper


def jinja2_filter_to_django(filter_func):
    """
    Note: Due to the way this function is used by
    ``coffin.template.Library``, it needs to be able to handle native
    Django filters and pass them through unmodified. This necessity
    stems from the fact that it is not always possible to determine
    the type of a filter.
    """
    if guess_filter_type(filter_func)[0] == DJANGO:
        return filter_func
    def _convert(v):
        # TODO: for now, this is not even necessary: Markup strings have
        # a custom replace() method that is immume to Django's escape()
        # attempts.
        #if isinstance(v, Markup):
        #    return SafeUnicode(v)         # jinja is always unicode
        # ... Jinja does not have a EscapeData equivalent
        return v
    def wrapped(value, *args, **kwargs):
        result = filter_func(value, *args, **kwargs)
        return _convert(result)
    return wrapped


def guess_filter_type(filter_func):
    """Returns a 2-tuple of (type, can_be_ported).

    ``type`` is one of DJANGO, JINJA2, or ``False`` if the type can
    not be determined.

    ``can_be_ported`` is ``True`` if we believe the filter could be
    ported to the other engine, respectively, or ``False`` if we know
    it can't.

    TODO: May not yet use all possible clues, e.g. decorators like
    ``stringfilter``.
    TOOD: Needs tests.
    """
    if hasattr(filter_func, 'contextfilter') or \
       hasattr(filter_func, 'environmentfilter'):
            return JINJA2, False

    args = inspect.getargspec(filter_func)
    if len(args[0]) - (len(args[3]) if args[3] else 0) > 2:
        return JINJA2, False

    if hasattr(filter_func, 'needs_autoescape'):
        return DJANGO, True

    # Looks like your run of the mill Python function, which are
    # easily convertible in either direction.
    return False, True
########NEW FILE########
__FILENAME__ = makemessages
"""Jinja2's i18n functionality is not exactly the same as Django's.
In particular, the tags names and their syntax are different:

  1. The Django ``trans`` tag is replaced by a _() global.
  2. The Django ``blocktrans`` tag is called ``trans``.

(1) isn't an issue, since the whole ``makemessages`` process is based on
converting the template tags to ``_()`` calls. However, (2) means that
those Jinja2 ``trans`` tags will not be picked up my Django's
``makemessage`` command.

There aren't any nice solutions here. While Jinja2's i18n extension does
come with extraction capabilities built in, the code behind ``makemessages``
unfortunately isn't extensible, so we can:

  * Duplicate the command + code behind it.
  * Offer a separate command for Jinja2 extraction.
  * Try to get Django to offer hooks into makemessages().
  * Monkey-patch.

We are currently doing that last thing. It turns out there we are lucky
for once: It's simply a matter of extending two regular expressions.
Credit for the approach goes to:
http://stackoverflow.com/questions/2090717/getting-translation-strings-for-jinja2-templates-integrated-with-django-1-x
"""

import re
from django.core.management.commands import makemessages
from django.utils.translation import trans_real
from django.template import BLOCK_TAG_START, BLOCK_TAG_END

strip_whitespace_right = re.compile(r"(%s-?\s*(trans|pluralize).*?-%s)\s+" % (BLOCK_TAG_START, BLOCK_TAG_END), re.U)
strip_whitespace_left = re.compile(r"\s+(%s-\s*(endtrans|pluralize).*?-?%s)" % (BLOCK_TAG_START, BLOCK_TAG_END), re.U)

def strip_whitespaces(src):
    src = strip_whitespace_left.sub(r'\1', src)
    src = strip_whitespace_right.sub(r'\1', src)
    return src

class Command(makemessages.Command):

    def handle(self, *args, **options):
        old_endblock_re = trans_real.endblock_re
        old_block_re = trans_real.block_re
        old_templatize = trans_real.templatize
        # Extend the regular expressions that are used to detect
        # translation blocks with an "OR jinja-syntax" clause.
        trans_real.endblock_re = re.compile(
            trans_real.endblock_re.pattern + '|' + r"""^-?\s*endtrans\s*-?$""")
        trans_real.block_re = re.compile(
            trans_real.block_re.pattern + '|' + r"""^-?\s*trans(?:\s+(?!'|")(?=.*?=.*?)|-?$)""")
        trans_real.plural_re = re.compile(
            trans_real.plural_re.pattern + '|' + r"""^-?\s*pluralize(?:\s+.+|-?$)""")

        def my_templatize(src, origin=None):
            new_src = strip_whitespaces(src)
            return old_templatize(new_src, origin)

        trans_real.templatize = my_templatize

        try:
            super(Command, self).handle(*args, **options)
        finally:
            trans_real.endblock_re = old_endblock_re
            trans_real.block_re = old_block_re
            trans_real.templatize = old_templatize

########NEW FILE########
__FILENAME__ = defaultfilters
﻿"""Coffin automatically makes Django's builtin filters available in Jinja2,
through an interop-layer.

However, Jinja 2 provides room to improve the syntax of some of the
filters. Those can be overridden here.

TODO: Most of the filters in here need to be updated for autoescaping.
"""

from coffin.template import Library
from jinja2.runtime import Undefined
# from jinja2 import Markup
from jinja2 import filters

register = Library()

def url(view_name, *args, **kwargs):
    """This is an alternative to the {% url %} tag. It comes from a time
    before Coffin had a port of the tag.
    """
    from coffin.template.defaulttags import url
    return url._reverse(view_name, args, kwargs)
register.jinja2_filter(url, jinja2_only=True)
register.object(url)

@register.jinja2_filter(jinja2_only=True)
def timesince(value, *arg):
    if value is None or isinstance(value, Undefined):
        return u''
    from django.utils.timesince import timesince
    return timesince(value, *arg)

@register.jinja2_filter(jinja2_only=True)
def timeuntil(value, *args):
    if value is None or isinstance(value, Undefined):
        return u''
    from django.utils.timesince import timeuntil
    return timeuntil(value, *args)

@register.jinja2_filter(jinja2_only=True)
def date(value, arg=None):
    """Formats a date according to the given format."""
    if value is None or isinstance(value, Undefined):
        return u''
    from django.conf import settings
    from django.utils import formats
    from django.utils.dateformat import format
    if arg is None:
        arg = settings.DATE_FORMAT
    try: 
        return formats.date_format(value, arg) 
    except AttributeError:
        try: 
            return format(value, arg) 
        except AttributeError:
            return ''

@register.jinja2_filter(jinja2_only=True)
def time(value, arg=None):
    """Formats a time according to the given format."""
    if value is None or isinstance(value, Undefined):
        return u''
    from django.conf import settings
    from django.utils import formats
    from django.utils.dateformat import time_format
    if arg is None:
        arg = settings.TIME_FORMAT
    try: 
        return formats.time_format(value, arg) 
    except AttributeError:
        try: 
            return time_format(value, arg) 
        except AttributeError:
            return ''

@register.jinja2_filter(jinja2_only=True)
def truncatewords(value, length):
    # Jinja2 has it's own ``truncate`` filter that supports word
    # boundaries and more stuff, but cannot deal with HTML.
    try:
        from django.utils.text import Truncator
    except ImportError:
        from django.utils.text import truncate_words # Django < 1.6
    else:
        truncate_words = lambda value, length: Truncator(value).words(length)
    return truncate_words(value, int(length))

@register.jinja2_filter(jinja2_only=True)
def truncatewords_html(value, length):
    try:
        from django.utils.text import Truncator
    except ImportError:
        from django.utils.text import truncate_html_words # Django < 1.6
    else:
        truncate_html_words = lambda value, length: Truncator(value).words(length, html=True)
    return truncate_html_words(value, int(length))

@register.jinja2_filter(jinja2_only=True)
def pluralize(value, s1='s', s2=None):
    """Like Django's pluralize-filter, but instead of using an optional
    comma to separate singular and plural suffixes, it uses two distinct
    parameters.

    It also is less forgiving if applied to values that do not allow
    making a decision between singular and plural.
    """
    if s2 is not None:
        singular_suffix, plural_suffix = s1, s2
    else:
        plural_suffix = s1
        singular_suffix = ''

    try:
        if int(value) != 1:
            return plural_suffix
    except TypeError: # not a string or a number; maybe it's a list?
        if len(value) != 1:
            return plural_suffix
    return singular_suffix

@register.jinja2_filter(jinja2_only=True)
def floatformat(value, arg=-1):
    """Builds on top of Django's own version, but adds strict error
    checking, staying with the philosophy.
    """
    from django.template.defaultfilters import floatformat
    from coffin.interop import django_filter_to_jinja2
    arg = int(arg)  # raise exception
    result = django_filter_to_jinja2(floatformat)(value, arg)
    if result == '':  # django couldn't handle the value
        raise ValueError(value)
    return result

@register.jinja2_filter(jinja2_only=True)
def default(value, default_value=u'', boolean=True):
    """Make the default filter, if used without arguments, behave like
    Django's own version.
    """
    return filters.do_default(value, default_value, boolean)


########NEW FILE########
__FILENAME__ = defaulttags
﻿from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.exceptions import TemplateSyntaxError
from jinja2 import Markup
from django.conf import settings
from coffin.template import Library


class LoadExtension(Extension):
    """The load-tag is a no-op in Coffin. Instead, all template libraries
    are always loaded.

    Note: Supporting a functioning load-tag in Jinja is tough, though
    theoretically possible. The trouble is activating new extensions while
    parsing is ongoing. The ``Parser.extensions`` dict of the current
    parser instance needs to be modified, but apparently the only way to
    get access would be by hacking the stack.
    """
    tags = set(['load'])

    def parse(self, parser):
        while not parser.stream.current.type == 'block_end':
            parser.stream.next()
        return []


"""class AutoescapeExtension(Extension):
    ""#"
    Template to output works in three phases in Jinja2: parsing,
    generation (compilation, AST-traversal), and rendering (execution).

    Unfortunatly, the environment ``autoescape`` option comes into effect
    during traversal, the part where we happen to have basically no control
    over as an extension. It determines whether output is wrapped in
    ``escape()`` calls.

    Solutions that could possibly work:

        * This extension could preprocess it's childnodes and wrap
          everything output related inside the appropriate
          ``Markup()`` or escape() call.

        * We could use the ``preprocess`` hook to insert the
          appropriate ``|safe`` and ``|escape`` filters on a
          string-basis. This is very unlikely to work well.

    There's also the issue of inheritance and just generally the nesting
    of autoescape-tags to consider.

    Other things of note:

        * We can access ``parser.environment``, but that would only
          affect the **parsing** of our child nodes.

        * In the commented-out code below we are trying to affect the
          autoescape setting during rendering. As noted, this could be
          necessary for rare border cases where custom extension use
          the autoescape attribute.

    Both the above things would break Environment thread-safety though!

    Overall, it's not looking to good for this extension.
    ""#"

    tags = ['autoescape']

    def parse(self, parser):
        lineno = parser.stream.next().lineno

        old_autoescape = parser.environment.autoescape
        parser.environment.autoescape = True
        try:
            body = parser.parse_statements(
                ['name:endautoescape'], drop_needle=True)
        finally:
            parser.environment.autoescape = old_autoescape

        # Not sure yet if the code below is necessary - it changes
        # environment.autoescape during template rendering. If for example
        # a CallBlock function accesses ``environment.autoescape``, it
        # presumably is.
        # This also should use try-finally though, which Jinja's API
        # doesn't support either. We could fake that as well by using
        # InternalNames that output the necessary indentation and keywords,
        # but at this point it starts to get really messy.
        #
        # TODO: Actually, there's ``nodes.EnvironmentAttribute``.
        #ae_setting = object.__new__(nodes.InternalName)
        #nodes.Node.__init__(ae_setting, 'environment.autoescape',
            lineno=lineno)
        #temp = parser.free_identifier()
        #body.insert(0, nodes.Assign(temp, ae_setting))
        #body.insert(1, nodes.Assign(ae_setting, nodes.Const(True)))
        #body.insert(len(body), nodes.Assign(ae_setting, temp))
        return body
"""


class URLExtension(Extension):
    """Returns an absolute URL matching given view with its parameters.

    This is a way to define links that aren't tied to a particular URL
    configuration::

        {% url path.to.some_view arg1,arg2,name1=value1 %}

    Known differences to Django's url-Tag:

        - In Django, the view name may contain any non-space character.
          Since Jinja's lexer does not identify whitespace to us, only
          characters that make up valid identifers, plus dots and hyphens
          are allowed. Note that identifers in Jinja 2 may not contain
          non-ascii characters.

          As an alternative, you may specifify the view as a string,
          which bypasses all these restrictions. It further allows you
          to apply filters:

            {% url "меткаda.some-view"|afilter %}
    """

    tags = set(['url'])

    def parse(self, parser):
        stream = parser.stream

        tag = stream.next()

        # get view name
        if stream.current.test('string'):
            # Need to work around Jinja2 syntax here. Jinja by default acts
            # like Python and concats subsequent strings. In this case
            # though, we want {% url "app.views.post" "1" %} to be treated
            # as view + argument, while still supporting
            # {% url "app.views.post"|filter %}. Essentially, what we do is
            # rather than let ``parser.parse_primary()`` deal with a "string"
            # token, we do so ourselves, and let parse_expression() handle all
            # other cases.
            if stream.look().test('string'):
                token = stream.next()
                viewname = nodes.Const(token.value, lineno=token.lineno)
            else:
                viewname = parser.parse_expression()
        else:
            # parse valid tokens and manually build a string from them
            bits = []
            name_allowed = True
            while True:
                if stream.current.test_any('dot', 'sub', 'colon'):
                    bits.append(stream.next())
                    name_allowed = True
                elif stream.current.test('name') and name_allowed:
                    bits.append(stream.next())
                    name_allowed = False
                else:
                    break
            viewname = nodes.Const("".join([b.value for b in bits]))
            if not bits:
                raise TemplateSyntaxError("'%s' requires path to view" %
                    tag.value, tag.lineno)

        # get arguments
        args = []
        kwargs = []
        while not stream.current.test_any('block_end', 'name:as'):
            if args or kwargs:
                stream.expect('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(stream.next().value)
                stream.skip()
                value = parser.parse_expression()
                kwargs.append(nodes.Pair(key, value, lineno=key.lineno))
            else:
                args.append(parser.parse_expression())

        def make_call_node(*kw):
            return self.call_method('_reverse', args=[
                viewname,
                nodes.List(args),
                nodes.Dict(kwargs),
                nodes.Name('_current_app', 'load'),
            ], kwargs=kw)

        # if an as-clause is specified, write the result to context...
        if stream.next_if('name:as'):
            var = nodes.Name(stream.expect('name').value, 'store')
            call_node = make_call_node(nodes.Keyword('fail',
                nodes.Const(False)))
            return nodes.Assign(var, call_node)
        # ...otherwise print it out.
        else:
            return nodes.Output([make_call_node()]).set_lineno(tag.lineno)

    @classmethod
    def _reverse(self, viewname, args, kwargs, current_app=None, fail=True):
        from django.core.urlresolvers import reverse, NoReverseMatch

        # Try to look up the URL twice: once given the view name,
        # and again relative to what we guess is the "main" app.
        url = ''
        urlconf=kwargs.pop('urlconf', None)
        try:
            url = reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs,
                current_app=current_app)
        except NoReverseMatch:
            projectname = settings.SETTINGS_MODULE.split('.')[0]
            try:
                url = reverse(projectname + '.' + viewname, urlconf=urlconf, 
                              args=args, kwargs=kwargs)
            except NoReverseMatch:
                if fail:
                    raise
                else:
                    return ''

        return url


class WithExtension(Extension):
    """Adds a value to the context (inside this block) for caching and
    easy access, just like the Django-version does.

    For example::

        {% with person.some_sql_method as total %}
            {{ total }} object{{ total|pluralize }}
        {% endwith %}

    TODO: The new Scope node introduced in Jinja2 6334c1eade73 (the 2.2
    dev version) would help here, but we don't want to rely on that yet.
    See also:
        http://dev.pocoo.org/projects/jinja/browser/tests/test_ext.py
        http://dev.pocoo.org/projects/jinja/ticket/331
        http://dev.pocoo.org/projects/jinja/ticket/329
    """

    tags = set(['with'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        value = parser.parse_expression()
        parser.stream.expect('name:as')
        name = parser.stream.expect('name')
        body = parser.parse_statements(['name:endwith'], drop_needle=True)
        # Use a local variable instead of a macro argument to alias
        # the expression.  This allows us to nest "with" statements.
        body.insert(0, nodes.Assign(nodes.Name(name.value, 'store'), value))
        return nodes.CallBlock(
                self.call_method('_render_block'), [], [], body).\
                    set_lineno(lineno)

    def _render_block(self, caller=None):
        return caller()


class CacheExtension(Extension):
    """Exactly like Django's own tag, but supports full Jinja2
    expressiveness for all arguments.

        {% cache gettimeout()*2 "foo"+options.cachename  %}
            ...
        {% endcache %}

    This actually means that there is a considerable incompatibility
    to Django: In Django, the second argument is simply a name, but
    interpreted as a literal string. This tag, with Jinja2 stronger
    emphasis on consistent syntax, requires you to actually specify the
    quotes around the name to make it a string. Otherwise, allowing
    Jinja2 expressions would be very hard to impossible (one could use
    a lookahead to see if the name is followed by an operator, and
    evaluate it as an expression if so, or read it as a string if not.
    TODO: This may not be the right choice. Supporting expressions
    here is probably not very important, so compatibility should maybe
    prevail. Unfortunately, it is actually pretty hard to be compatibly
    in all cases, simply because Django's per-character parser will
    just eat everything until the next whitespace and consider it part
    of the fragment name, while we have to work token-based: ``x*2``
    would actually be considered ``"x*2"`` in Django, while Jinja2
    would give us three tokens: ``x``, ``*``, ``2``.

    General Syntax:

        {% cache [expire_time] [fragment_name] [var1] [var2] .. %}
            .. some expensive processing ..
        {% endcache %}

    Available by default (does not need to be loaded).

    Partly based on the ``FragmentCacheExtension`` from the Jinja2 docs.

    TODO: Should there be scoping issues with the internal dummy macro
    limited access to certain outer variables in some cases, there is a
    different way to write this. Generated code would look like this:

        internal_name = environment.extensions['..']._get_cache_value():
        if internal_name is not None:
            yield internal_name
        else:
            internal_name = ""  # or maybe use [] and append() for performance
            internalname += "..."
            internalname += "..."
            internalname += "..."
            environment.extensions['..']._set_cache_value(internalname):
            yield internalname

    In other words, instead of using a CallBlock which uses a local
    function and calls into python, we have to separate calls into
    python, but put the if-else logic itself into the compiled template.
    """

    tags = set(['cache'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno

        expire_time = parser.parse_expression()
        fragment_name = parser.parse_expression()
        vary_on = []
        while not parser.stream.current.test('block_end'):
            vary_on.append(parser.parse_expression())

        body = parser.parse_statements(['name:endcache'], drop_needle=True)

        return nodes.CallBlock(
            self.call_method('_cache_support',
                             [expire_time, fragment_name,
                              nodes.List(vary_on), nodes.Const(lineno)]),
            [], [], body).set_lineno(lineno)

    def _cache_support(self, expire_time, fragm_name, vary_on, lineno, caller):
        from hashlib import md5
        from django.core.cache import cache   # delay depending in settings
        from django.utils.http import urlquote

        try:
            expire_time = int(expire_time)
        except (ValueError, TypeError):
            raise TemplateSyntaxError('"%s" tag got a non-integer timeout '
                'value: %r' % (list(self.tags)[0], expire_time), lineno)

        args_string = u':'.join([urlquote(v) for v in vary_on])
        args_md5 = md5(args_string)
        cache_key = 'template.cache.%s.%s' % (fragm_name, args_md5.hexdigest())
        value = cache.get(cache_key)
        if value is None:
            value = caller()
            cache.set(cache_key, value, expire_time)
        return value


class SpacelessExtension(Extension):
    """Removes whitespace between HTML tags, including tab and
    newline characters.

    Works exactly like Django's own tag.
    """

    tags = set(['spaceless'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        body = parser.parse_statements(['name:endspaceless'], drop_needle=True)
        return nodes.CallBlock(
            self.call_method('_strip_spaces', [], [], None, None),
            [], [], body,
        ).set_lineno(lineno)

    def _strip_spaces(self, caller=None):
        from django.utils.html import strip_spaces_between_tags
        return strip_spaces_between_tags(caller().strip())


class CsrfTokenExtension(Extension):
    """Jinja2-version of the ``csrf_token`` tag.

    Adapted from a snippet by Jason Green:
    http://www.djangosnippets.org/snippets/1847/

    This tag is a bit stricter than the Django tag in that it doesn't
    simply ignore any invalid arguments passed in.
    """

    tags = set(['csrf_token'])

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        return nodes.Output([
            self.call_method('_render', [nodes.Name('csrf_token', 'load')]),
        ]).set_lineno(lineno)

    def _render(self, csrf_token):
        from django.template.defaulttags import CsrfTokenNode
        return Markup(CsrfTokenNode().render({'csrf_token': csrf_token}))


# nicer import names
load = LoadExtension
url = URLExtension
with_ = WithExtension
cache = CacheExtension
spaceless = SpacelessExtension
csrf_token = CsrfTokenExtension

register = Library()
register.tag(load)
register.tag(url)
register.tag(with_)
register.tag(cache)
register.tag(spaceless)
register.tag(csrf_token)


########NEW FILE########
__FILENAME__ = library
﻿from django.template import Library as DjangoLibrary, InvalidTemplateLibrary
from jinja2.ext import Extension as Jinja2Extension
import types
from coffin.interop import (
    DJANGO, JINJA2,
    guess_filter_type, jinja2_filter_to_django, django_filter_to_jinja2)


__all__ = ['Library']


class Library(DjangoLibrary):
    """Version of the Django ``Library`` class that can handle both
    Django template engine tags and filters, as well as Jinja2
    extensions and filters.

    Tries to present a common registration interface to the extension
    author, but provides both template engines with only those
    components they can support.

    Since custom Django tags and Jinja2 extensions are two completely
    different beasts, they are handled completely separately. You can
    register custom Django tags as usual, for example:

        register.tag('current_time', do_current_time)

    Or register a Jinja2 extension like this:

        register.tag(CurrentTimeNode)

    Filters, on the other hand, work similarily in both engines, and
    for the most one can't tell whether a filter function was written
    for Django or Jinja2. A compatibility layer is used to make to
    make the filters you register usuable with both engines:

        register.filter('cut', cut)

    However, some of the more powerful filters just won't work in
    Django, for example if more than one argument is required, or if
    context- or environmentfilters are used. If ``cut`` in the above
    example where such an extended filter, it would only be registered
    with Jinja.

    See also the module documentation for ``coffin.interop`` for
    information on some of the limitations of this conversion.

    TODO: Jinja versions of the ``simple_tag`` and ``inclusion_tag``
    helpers would be nice, though since custom tags are not needed as
    often in Jinja, this is not urgent.
    """

    def __init__(self):
        super(Library, self).__init__()
        self.jinja2_filters = {}
        self.jinja2_extensions = []
        self.jinja2_environment_attrs = {}
        self.jinja2_globals = {}
        self.jinja2_tests = {}

    @classmethod
    def from_django(cls, django_library):
        """Create a Coffin library object from a Django library.

        Specifically, this ensures that filters already registered
        with the Django library are also made available to Jinja,
        where applicable.
        """
        from copy import copy
        result = cls()
        result.tags = copy(django_library.tags)
        for name, func in django_library.filters.iteritems():
            result._register_filter(name, func, type='django')
        return result

    def test(self, name=None, func=None):
        def inner(f):
            name = getattr(f, "_decorated_function", f).__name__
            self.jinja2_tests[name] = f
            return f
        if name == None and func == None:
            # @register.test()
            return inner
        elif func == None:
            if (callable(name)):
                # register.test()
                return inner(name)
            else:
                # @register.test('somename') or @register.test(name='somename')
                def dec(func):
                    return self.test(name, func)
                return dec
        elif name != None and func != None:
            # register.filter('somename', somefunc)
            self.jinja2_tests[name] = func
            return func
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to "
                "Library.test: (%r, %r)", (name, func))

    def object(self, name=None, func=None):
        def inner(f):
            name = getattr(f, "_decorated_function", f).__name__
            self.jinja2_globals[name] = f
            return f
        if name == None and func == None:
            # @register.object()
            return inner
        elif func == None:
            if (callable(name)):
                # register.object()
                return inner(name)
            else:
                # @register.object('somename') or @register.object(name='somename')
                def dec(func):
                    return self.object(name, func)
                return dec
        elif name != None and func != None:
            # register.object('somename', somefunc)
            self.jinja2_globals[name] = func
            return func
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to "
                "Library.object: (%r, %r)", (name, func))

    def tag(self, name_or_node=None, compile_function=None, environment={}):
        """Register a Django template tag (1) or Jinja 2 extension (2).

        For (1), supports the same invocation syntax as the original
        Django version, including use as a decorator.

        For (2), since Jinja 2 extensions are classes (which can't be
        decorated), and have the tag name effectively built in, only the
        following syntax is supported:

            register.tag(MyJinjaExtensionNode)

        If your extension needs to be configured by setting environment
        attributes, you can can pass key-value pairs via ``environment``.
        """
        if isinstance(name_or_node, type) and issubclass(name_or_node, Jinja2Extension):
            if compile_function:
                raise InvalidTemplateLibrary('"compile_function" argument not supported for Jinja2 extensions')
            self.jinja2_extensions.append(name_or_node)
            self.jinja2_environment_attrs.update(environment)
            return name_or_node
        else:
            if environment:
                raise InvalidTemplateLibrary('"environment" argument not supported for Django tags')
            return super(Library, self).tag(name_or_node, compile_function)

    def tag_function(self, func_or_node):
        if not isinstance(func_or_node, types.FunctionType) and \
                issubclass(func_or_node, Jinja2Extension):
            self.jinja2_extensions.append(func_or_node)
            return func_or_node
        else:
            return super(Library, self).tag_function(func_or_node)

    def filter(self, name=None, filter_func=None, type=None, jinja2_only=None):
        """Register a filter with both the Django and Jinja2 template
        engines, if possible - or only Jinja2, if ``jinja2_only`` is
        specified. ``jinja2_only`` does not affect conversion of the
        filter if neccessary.

        Implements a compatibility layer to handle the different
        auto-escaping approaches transparently. Extended Jinja2 filter
        features like environment- and contextfilters are however not
        supported in Django. Such filters will only be registered with
        Jinja.

        If you know which template language the filter was written for,
        you may want to specify type="django" or type="jinja2", to disable
        the interop layer which in some cases might not be able to operate
        entirely opaque. For example, Jinja 2 filters may not receive a
        "Undefined" value if the interop layer is applied.

        Supports the same invocation syntax as the original Django
        version, including use as a decorator.

        If the function is supposed to return the registered filter
        (by example of the superclass implementation), but has
        registered multiple filters, a tuple of all filters is
        returned.
        """
        def filter_function(f):
            return self._register_filter(
                getattr(f, "_decorated_function", f).__name__,
                f, type=type, jinja2_only=jinja2_only)
        if name == None and filter_func == None:
            # @register.filter()
            return filter_function
        elif filter_func == None:
            if (callable(name)):
                # @register.filter
                return filter_function(name)
            else:
                # @register.filter('somename') or @register.filter(name='somename')
                def dec(func):
                    return self.filter(name, func, type=type,
                                       jinja2_only=jinja2_only)
                return dec
        elif name != None and filter_func != None:
            # register.filter('somename', somefunc)
            return self._register_filter(name, filter_func, type=type,
                jinja2_only=jinja2_only)
        else:
            raise InvalidTemplateLibrary("Unsupported arguments to "
                "Library.filter: (%r, %r)", (name, filter_func))

    def jinja2_filter(self, *args, **kwargs):
        """Shortcut for filter(type='jinja2').
        """
        kw = {'type': JINJA2}
        kw.update(kwargs)
        return self.filter(*args, **kw)

    def _register_filter(self, name, func, type=None, jinja2_only=None):
        assert type in (None, JINJA2, DJANGO,)

        # The user might not specify the language the filter was written
        # for, but sometimes we can auto detect it.
        filter_type, can_be_ported = guess_filter_type(func)
        assert not (filter_type and type) or filter_type == type, \
               "guessed filter type (%s) not matching claimed type (%s)" % (
                   filter_type, type,
               )
        if not filter_type and type:
            filter_type = type

        if filter_type == JINJA2:
            self.jinja2_filters[name] = func
            if can_be_ported and not jinja2_only:
                self.filters[name] = jinja2_filter_to_django(func)
            return func
        elif filter_type == DJANGO:
            self.filters[name] = func
            if not can_be_ported and jinja2_only:
                raise ValueError('This filter cannot be ported to Jinja2.')
            if can_be_ported:
                self.jinja2_filters[name] = django_filter_to_jinja2(func)
            return func
        else:
            django_func = jinja2_filter_to_django(func)
            jinja2_func = django_filter_to_jinja2(func)
            if jinja2_only:
                self.jinja2_filters[name] = jinja2_func
                return jinja2_func
            else:
                # register the filter with both engines
                self.filters[name] = django_func
                self.jinja2_filters[name] = jinja2_func
                return (django_func, jinja2_func)

########NEW FILE########
__FILENAME__ = loader
"""Replacement for ``django.template.loader`` that uses Jinja 2.

The module provides a generic way to load templates from an arbitrary
backend storage (e.g. filesystem, database).
"""

from django.template import TemplateDoesNotExist
from jinja2 import TemplateNotFound


def find_template_source(name, dirs=None):
    # This is Django's most basic loading function through which
    # all template retrievals go. Not sure if Jinja 2 publishes
    # an equivalent, but no matter, it mostly for internal use
    # anyway - developers will want to start with
    # ``get_template()`` or ``get_template_from_string`` anyway.
    raise NotImplementedError()


def get_template(template_name):
    # Jinja will handle this for us, and env also initializes
    # the loader backends the first time it is called.
    from coffin.common import env
    try:
        return env.get_template(template_name)
    except TemplateNotFound:
        raise TemplateDoesNotExist(template_name)


def get_template_from_string(source):
    """
    Does not support then ``name`` and ``origin`` parameters from
    the Django version.
    """
    from coffin.common import env
    return env.from_string(source)


def render_to_string(template_name, dictionary=None, context_instance=None):
    """Loads the given ``template_name`` and renders it with the given
    dictionary as context. The ``template_name`` may be a string to load
    a single template using ``get_template``, or it may be a tuple to use
    ``select_template`` to find one of the templates in the list.

    ``dictionary`` may also be Django ``Context`` object.

    Returns a string.
    """
    dictionary = dictionary or {}
    if isinstance(template_name, (list, tuple)):
        template = select_template(template_name)
    else:
        template = get_template(template_name)
    if context_instance:
        context_instance.update(dictionary)
    else:
        context_instance = dictionary
    return template.render(context_instance)


def select_template(template_name_list):
    "Given a list of template names, returns the first that can be loaded."
    for template_name in template_name_list:
        try:
            return get_template(template_name)
        except TemplateDoesNotExist:
            continue
    # If we get here, none of the templates could be loaded
    raise TemplateDoesNotExist(', '.join(template_name_list))

########NEW FILE########
__FILENAME__ = loaders
import re
from jinja2 import loaders

match_loader = re.compile(r'^(django|coffin)\.')


def jinja_loader_from_django_loader(django_loader, args=None):
    """Attempts to make a conversion from the given Django loader to an
    similarly-behaving Jinja loader.

    :param django_loader: Django loader module string.
    :return: The similarly-behaving Jinja loader, or None if a similar loader
        could not be found.
    """
    if not match_loader.match(django_loader):
        return None
    for substr, func in _JINJA_LOADER_BY_DJANGO_SUBSTR.iteritems():
        if substr in django_loader:
            return func(*(args or []))
    return None


def _make_jinja_app_loader():
    """Makes an 'app loader' for Jinja which acts like
    :mod:`django.template.loaders.app_directories`.
    """
    from django.template.loaders.app_directories import app_template_dirs
    return loaders.FileSystemLoader(app_template_dirs)


def _make_jinja_filesystem_loader():
    """Makes a 'filesystem loader' for Jinja which acts like
    :mod:`django.template.loaders.filesystem`.
    """
    from django.conf import settings
    return loaders.FileSystemLoader(settings.TEMPLATE_DIRS)


def _make_jinja_cached_loader(*loaders):
    """Makes a loader for Jinja which acts like
    :mod:`django.template.loaders.cached`.
    """
    return JinjaCachedLoader(
        [jinja_loader_from_django_loader(l) for l in loaders])


# Determine loaders from Django's conf.
_JINJA_LOADER_BY_DJANGO_SUBSTR = { # {substr: callable, ...}
    'app_directories': _make_jinja_app_loader,
    'filesystem': _make_jinja_filesystem_loader,
    'cached': _make_jinja_cached_loader,
    'AppLoader': _make_jinja_app_loader,
    'FileSystemLoader': _make_jinja_filesystem_loader,
}


class JinjaCachedLoader(loaders.BaseLoader):
    """A "sort of" port of of Django's "cached" template loader
    to Jinja 2. It exists primarily to support Django's full
    TEMPLATE_LOADERS syntax.

    However, note that it does not behave exactly like Django's cached
    loader: Rather than caching the compiled template, it only caches
    the template source, and recompiles the template every time. This is
    due to the way the Jinja2/Coffin loader setup works: The ChoiceLoader,
    which Coffin uses at the root to select from any of the configured
    loaders, calls the ``get_source`` method of each loader directly,
    bypassing ``load``. Our loader can therefore only hook into the process
    BEFORE template compilation.
    Caching the compiled templates by implementing ``load`` would only
    work if this loader instance were the root loader. See also the comments
    in Jinja2's BaseLoader class.

    Note that Jinja2 has an environment-wide bytecode cache (i.e. it caches
    compiled templates), that can function alongside with this class.

    Note further that Jinja2 has an environment-wide template cache (via the
    ``auto_reload`` environment option), which duplicate the functionality
    of this class entirely, and should be preferred when possible.
    """

    def __init__(self, subloaders):
        self.loader = loaders.ChoiceLoader(subloaders)
        self.template_cache = {}

    def get_source(self, environment, template):
        key = (environment, template)
        if key not in self.template_cache:
            result = self.loader.get_source(environment, template)
            self.template_cache[key] = result
        return self.template_cache[key]

########NEW FILE########
__FILENAME__ = response
from coffin.template import loader
from django.template import response as django_response


class SimpleTemplateResponse(django_response.SimpleTemplateResponse):
    def resolve_template(self, template):
        if isinstance(template, (list, tuple)):
            return loader.select_template(template)
        elif isinstance(template, basestring):
            return loader.get_template(template)
        else:
            return template

class TemplateResponse(django_response.TemplateResponse,
        SimpleTemplateResponse):
    pass

########NEW FILE########
__FILENAME__ = static
try:
    from urllib.parse import urljoin
except ImportError:     # Python 2
    from urlparse import urljoin

from coffin.template import Library
from jinja2.ext import Extension
from jinja2 import nodes
from django.utils.encoding import iri_to_uri


register = Library()


class PrefixExtension(Extension):

    def parse(self, parser):
        stream = parser.stream
        lineno = stream.next().lineno

        call_node = self.call_method('render')

        if stream.next_if('name:as'):
            var = nodes.Name(stream.expect('name').value, 'store')
            return nodes.Assign(var, call_node).set_lineno(lineno)
        else:
            return nodes.Output([call_node]).set_lineno(lineno)

    def render(self, name):
        raise NotImplementedError()

    @classmethod
    def get_uri_setting(cls, name):
        try:
            from django.conf import settings
        except ImportError:
            prefix = ''
        else:
            prefix = iri_to_uri(getattr(settings, name, ''))
        return prefix


class GetStaticPrefixExtension(PrefixExtension):
    """
    Populates a template variable with the static prefix,
    ``settings.STATIC_URL``.

    Usage::

        {% get_static_prefix [as varname] %}

    Examples::

        {% get_static_prefix %}
        {% get_static_prefix as static_prefix %}

    """

    tags = set(['get_static_prefix'])

    def render(self):
        return self.get_uri_setting('STATIC_URL')


class GetMediaPrefixExtension(PrefixExtension):
    """
    Populates a template variable with the media prefix,
    ``settings.MEDIA_URL``.

    Usage::

        {% get_media_prefix [as varname] %}

    Examples::

        {% get_media_prefix %}
        {% get_media_prefix as media_prefix %}

    """

    tags = set(['get_media_prefix'])

    def render(self):
        return self.get_uri_setting('STATIC_URL')


class StaticExtension(PrefixExtension):
    """
    Joins the given path with the STATIC_URL setting.

    Usage::

        {% static path [as varname] %}

    Examples::

        {% static "myapp/css/base.css" %}
        {% static variable_with_path %}
        {% static "myapp/css/base.css" as admin_base_css %}
        {% static variable_with_path as varname %}

    """

    tags = set(['static'])

    def parse(self, parser):
        stream = parser.stream
        lineno = stream.next().lineno

        path = parser.parse_expression()
        call_node = self.call_method('get_statc_url', args=[path])

        if stream.next_if('name:as'):
            var = nodes.Name(stream.expect('name').value, 'store')
            return nodes.Assign(var, call_node).set_lineno(lineno)
        else:
            return nodes.Output([call_node]).set_lineno(lineno)

    @classmethod
    def get_statc_url(cls, path):
        return urljoin(PrefixExtension.get_uri_setting("STATIC_URL"), path)


register.tag(GetStaticPrefixExtension)
register.tag(GetMediaPrefixExtension)
register.tag(StaticExtension)


def static(path):
    return StaticExtension.get_static_url(path)

########NEW FILE########
__FILENAME__ = decorators
from coffin.template.response import TemplateResponse

def template_response(cls):
    """
    A decorator to enforce class_based generic views 
    to use coffin TemplateResponse
    """
    cls.response_class = TemplateResponse
    return cls

########NEW FILE########
__FILENAME__ = defaults
from django import http
from django.template import Context, RequestContext
from coffin.template.loader import render_to_string


__all__ = ('page_not_found', 'server_error', 'shortcut')


# no Jinja version for this needed
from django.views.defaults import shortcut


def page_not_found(request, template_name='404.html'):
    """
    Default 404 handler.

    Templates: `404.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/')
    """
    content = render_to_string(template_name,
        RequestContext(request, {'request_path': request.path}))
    return http.HttpResponseNotFound(content)


def server_error(request, template_name='500.html'):
    """
    500 error handler.

    Templates: `500.html`
    Context: None
    """
    content = render_to_string(template_name, Context({}))
    return http.HttpResponseServerError(content)

########NEW FILE########
__FILENAME__ = base
import django.views.generic.base as _generic_base
from coffin.template.response import TemplateResponse as JinjaTemplateResponse

class TemplateResponseMixin(_generic_base.TemplateResponseMixin):
    """
    A mixin that can be used to render a template using Jinja.
    """
    response_class = JinjaTemplateResponse

class TemplateView(TemplateResponseMixin, _generic_base.TemplateView):
    """
    A view that renders a template using Jinja.
    """
########NEW FILE########
__FILENAME__ = create_update
from coffin.template import loader
from django.views.generic import create_update as _create_update
import functools

create_object = functools.partial(_create_update.create_object, template_loader=loader)
update_object = functools.partial(_create_update.update_object, template_loader=loader)
delete_object = functools.partial(_create_update.delete_object, template_loader=loader)

########NEW FILE########
__FILENAME__ = dates
from coffin.views.generic.detail import SingleObjectTemplateResponseMixin
from coffin.views.generic.list import MultipleObjectTemplateResponseMixin
import django.views.generic.dates as _generic_dates

class ArchiveIndexView(MultipleObjectTemplateResponseMixin, _generic_dates.BaseArchiveIndexView):
    """
    Equivalent of django generic view ArchiveIndexView, but uses Jinja template renderer.
    """
    template_name_suffix = '_archive'


class YearArchiveView(MultipleObjectTemplateResponseMixin, _generic_dates.BaseYearArchiveView):
    """
    Equivalent of django generic view YearArchiveView, but uses Jinja template renderer.
    """
    template_name_suffix = '_archive_year'


class MonthArchiveView(MultipleObjectTemplateResponseMixin, _generic_dates.BaseMonthArchiveView):
    """
    Equivalent of django generic view MonthArchiveView, but uses Jinja template renderer.
    """
    template_name_suffix = '_archive_month'


class WeekArchiveView(MultipleObjectTemplateResponseMixin, _generic_dates.BaseWeekArchiveView):
    """
    Equivalent of django generic view WeekArchiveView, but uses Jinja template renderer.
    """
    template_name_suffix = '_archive_week'


class DayArchiveView(MultipleObjectTemplateResponseMixin, _generic_dates.BaseDayArchiveView):
    """
    Equivalent of django generic view DayArchiveView, but uses Jinja template renderer.
    """
    template_name_suffix = "_archive_day"

class TodayArchiveView(MultipleObjectTemplateResponseMixin, _generic_dates.BaseTodayArchiveView):
    """
    Equivalent of django generic view TodayArchiveView, but uses Jinja template renderer.
    """
    template_name_suffix = "_archive_day"


class DateDetailView(SingleObjectTemplateResponseMixin, _generic_dates.BaseDateDetailView):
    """
    Equivalent of django generic view DateDetailView, but uses Jinja template renderer.
    """
    template_name_suffix = '_detail'
########NEW FILE########
__FILENAME__ = date_based
from coffin.template import loader
from django.views.generic import date_based as _date_based
import functools


archive_index = functools.partial(_date_based.archive_index, template_loader=loader)
archive_year = functools.partial(_date_based.archive_year, template_loader=loader)
archive_month = functools.partial(_date_based.archive_month, template_loader=loader)
archive_week = functools.partial(_date_based.archive_week, template_loader=loader)
archive_daye = functools.partial(_date_based.archive_day, template_loader=loader)
archive_today = functools.partial(_date_based.archive_today, template_loader=loader)

object_detail = functools.partial(_date_based.object_detail, template_loader=loader)
########NEW FILE########
__FILENAME__ = detail
import django.views.generic.detail as _generic_detail
from coffin.views.generic.base import TemplateResponseMixin as JinjaTemplateResponseMixin

class SingleObjectTemplateResponseMixin(JinjaTemplateResponseMixin, _generic_detail.SingleObjectTemplateResponseMixin):
    """
    Equivalent of django mixin SingleObjectTemplateResponseMixin, but uses Jinja template renderer.
    """

class DetailView(SingleObjectTemplateResponseMixin, _generic_detail.BaseDetailView):
    """
    Equivalent of django generic view DetailView, but uses Jinja template renderer.
    """

########NEW FILE########
__FILENAME__ = edit
from coffin.views.generic.base import TemplateResponseMixin
from coffin.views.generic.detail import SingleObjectTemplateResponseMixin
import django.views.generic.edit as _generic_edit


class FormView(TemplateResponseMixin, _generic_edit.BaseFormView):
    """
    Equivalent of django generic view FormView, but uses Jinja template renderer.
    """


class CreateView(SingleObjectTemplateResponseMixin, _generic_edit.BaseCreateView):
    """
    Equivalent of django generic view CreateView, but uses Jinja template renderer.
    """
    template_name_suffix = '_form'


class UpdateView(SingleObjectTemplateResponseMixin, _generic_edit.BaseUpdateView):
    """
    Equivalent of django generic view UpdateView, but uses Jinja template renderer.
    """
    template_name_suffix = '_form'


class DeleteView(SingleObjectTemplateResponseMixin, _generic_edit.BaseDeleteView):
    """
    Equivalent of django generic view DeleteView, but uses Jinja template renderer.
    """
    template_name_suffix = '_confirm_delete'

########NEW FILE########
__FILENAME__ = list
import django.views.generic.list as _generic_list
from coffin.views.generic.base import TemplateResponseMixin as JinjaTemplateResponseMixin

class MultipleObjectTemplateResponseMixin(JinjaTemplateResponseMixin, _generic_list.MultipleObjectTemplateResponseMixin):
    """
    Equivalent of django mixin MultipleObjectTemplateResponseMixin, but uses Jinja template renderer.
    """

class ListView(MultipleObjectTemplateResponseMixin, _generic_list.BaseListView):
    """
    Equivalent of django generic view ListView, but uses Jinja template renderer.
    """

########NEW FILE########
__FILENAME__ = list_detail
from coffin.template import loader
from django.views.generic import list_detail as _list_detail
import functools

object_list = functools.partial(_list_detail.object_list, template_loader=loader)
object_detail = functools.partial(_list_detail.object_detail, template_loader=loader)

########NEW FILE########
__FILENAME__ = simple
import inspect

from django.views.generic.simple import *
from coffin.template import loader, RequestContext

exec inspect.getsource(direct_to_template)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Coffin documentation build configuration file, created by
# sphinx-quickstart on Tue Sep  8 15:22:15 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Coffin'
copyright = u'2009, Christopher D. Leary'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

import coffin
# The short X.Y version.
version = '.'.join(map(str, coffin.__version__))
# The full version, including alpha/beta/rc tags.
release = '.'.join(map(str, coffin.__version__))

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
html_static_path = ['_static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Coffindoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Coffin.tex', u'Coffin Documentation',
   u'Christopher D. Leary', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = django_lib
"""A Django library, but but auto-loaded via the templatetags/ directory.

Instead, to use it, it needs to be added to the builtins.
"""

def foo(value):
    return "{foo}"

from django.template import Library
register = Library()
register.filter('foo_django_builtin', foo)

########NEW FILE########
__FILENAME__ = feeds
from coffin.contrib.syndication.feeds import Feed as OldFeed


class TestOldFeed(OldFeed):
    title = 'Foo'
    link = '/'

    def items(self):
        return [1,2,3]

    def item_link(self, item):
        return '/item'

    title_template = 'feeds_app/feed_title.html'
    description_template = 'feeds_app/feed_description.html'


try:
    from coffin.contrib.syndication.views import Feed as NewFeed
except ImportError:
    pass
else:
    class TestNewFeed(NewFeed):
        title = 'Foo'
        link = '/'

        def items(self):
            return [1,2,3]

        def item_link(self, item):
            return '/item'

        title_template = 'feeds_app/feed_title.html'
        description_template = 'feeds_app/feed_description.html'
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
from os import path


DATABASES = {
    'default': {}
}

INSTALLED_APPS = (
    'templatelibs_app',
    'feeds_app',
    'urls_app',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.load_template_source',
    'django.template.loaders.filesystem.load_template_source',
)

TEMPLATE_DIRS = (path.join(path.dirname(__file__), 'templates'),)

ROOT_URLCONF = 'urls'
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = compat_filters
"""Register a number of portable filters (with a Coffin library object)
that require a compatibility layer to function correctly in both engines.
"""

from jinja2 import Markup
from django.utils.safestring import mark_safe, mark_for_escaping


def needing_autoescape(value, autoescape=None):
    return str(autoescape)
needing_autoescape.needs_autoescape = True


def jinja_safe_output(value):
    return Markup(value)

def django_safe_output(value):
    return mark_safe(value)

def unsafe_output(value):
    return unicode(value)


def django_raw_output(value):
    return value

def django_escape_output(value):
    # Make sure the value is converted to unicode first, because otherwise,
    # if it is already SafeData (for example, when coming from the template
    # code), then mark_for_escaping would do nothing. We want to guarantee
    # a EscapeData return value in this filter though.
    return mark_for_escaping(unicode(value))


from coffin.template import Library
register = Library()
register.filter('needing_autoescape', needing_autoescape)
register.filter('jinja_safe_output', jinja_safe_output)
register.filter('django_safe_output', django_safe_output)
register.filter('django_raw_output', django_raw_output)
register.filter('unsafe_output', unsafe_output)
register.filter('django_escape_output', django_escape_output)
########NEW FILE########
__FILENAME__ = django_library
"""Register a filter with a Django library object.
"""

def foo(value):
    return "{foo}"

from django.template import Library
register = Library()
register.filter('foo_django', foo)
########NEW FILE########
__FILENAME__ = django_tags
"""Register a Django tag with a Coffin library object.
"""

from django.template import Node

class FooNode(Node):
    def render(self, context):
        return u'{foo}'

def do_foo(parser, token):
    return FooNode()

from coffin.template import Library
register = Library()
register.tag('foo_coffin', do_foo)
########NEW FILE########
__FILENAME__ = jinja2_ext
"""Register a Jinja2 extension with a Coffin library object.
"""

from jinja2.ext import Extension
from jinja2 import nodes

class FooExtension(Extension):
    tags = set(['foo'])

    def parse(self, parser):
        parser.stream.next()
        return nodes.Const('{foo}')


class FooWithConfigExtension(Extension):
    tags = set(['foo_ex'])

    def __init__(self, environment):
        Extension.__init__(self, environment)
        environment.extend(
            foo_custom_output='foo',
        )

    def parse(self, parser):
        parser.stream.next()
        return nodes.Const('{%s}' % self.environment.foo_custom_output)


from coffin.template import Library
register = Library()
register.tag(FooExtension)
register.tag(FooWithConfigExtension, environment={'foo_custom_output': 'my_foo'})
########NEW FILE########
__FILENAME__ = jinja2_filters
"""Register a number of non-portable, Jinja2-only filters with a Coffin
library object.
"""

from jinja2 import environmentfilter, contextfilter

@environmentfilter
def environment(environment, value):
    return ""

@contextfilter
def context(context, value):
    return ""

def multiarg(value, arg1, arg2):
    return ""

def jinja_forced(value):
    return ""

def django_jinja_forced(value):
    # a django filter that returns a django-safestring. It will *only*
    # be added to jinja, and coffin will hopefully ensure the string
    # stays safe.
    from django.utils.safestring import mark_safe
    return mark_safe(value)


from coffin.template import Library
register = Library()
register.filter('environment', environment)
register.filter('context', context)
register.filter('multiarg', multiarg)
register.filter('jinja_forced', jinja_forced, jinja2_only=True)
register.filter('django_jinja_forced', django_jinja_forced, jinja2_only=True)
########NEW FILE########
__FILENAME__ = jinja2_objects
"""Register a Jinja2 global object with a Coffin library object.
"""

def hello_func(name):
    return u"Hello %s" % name

from coffin.template import Library
register = Library()
register.object('hello', hello_func)

########NEW FILE########
__FILENAME__ = portable_filters
"""Register a portable filter with a Coffin library object.
"""

def foo(value):
    return "{foo}"

from coffin.template import Library
register = Library()
register.filter('foo', foo)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^url_test/', include('urls_app.urls')),

    # These two are used to test that our url-tag implementation can
    # deal with application namespaces / the "current app".
    (r'^app/one/', include('urls_app.urls', app_name="testapp", namespace="testapp")),  # default instance
    (r'^app/two/', include('urls_app.urls', app_name="testapp", namespace="two")),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('apps.urls_app',
    # Test urls for testing reverse lookups
    url(r'^$', 'views.index', name='the-index-view'),
    (r'^sum/(?P<left>\d+),(?P<right>\d+)$', 'views.sum'),
)

########NEW FILE########
__FILENAME__ = views
def index(r):
    pass

def sum(r):
    pass
########NEW FILE########
__FILENAME__ = test_contrib
from nose.plugins.skip import SkipTest
import django


class TestSyndication:

    def test_old(self):
        from django.http import HttpRequest
        fake_request = HttpRequest()
        fake_request.META['SERVER_NAME'] = 'foo'
        fake_request.META['SERVER_PORT'] = 80

        from apps.feeds_app.feeds import TestOldFeed
        feedgen = TestOldFeed('', fake_request).get_feed(None)
        s = feedgen.writeString('utf-8')
        assert 'JINJA WAS HERE (TITLE)' in s
        assert 'JINJA WAS HERE (DESCRIPTION)' in s

    def test_new(self):
        if django.VERSION < (1,2):
            raise SkipTest()

        from django.http import HttpRequest
        fake_request = HttpRequest()
        fake_request.META['SERVER_NAME'] = 'foo'
        fake_request.META['SERVER_PORT'] = 80

        from apps.feeds_app.feeds import TestNewFeed
        response = TestNewFeed()(fake_request)
        assert 'JINJA WAS HERE (TITLE)' in response.content
        assert 'JINJA WAS HERE (DESCRIPTION)' in response.content
########NEW FILE########
__FILENAME__ = test_defaultags
﻿from jinja2 import Environment


def test_load():
    from coffin.template.defaulttags import LoadExtension
    env = Environment(extensions=[LoadExtension])

    # the load tag is a no-op
    assert env.from_string('a{% load %}b').render() == 'ab'
    assert env.from_string('a{% load news.photos %}b').render() == 'ab'
    assert env.from_string('a{% load "news.photos" %}b').render() == 'ab'

    # [bug] invalid code was generated under certain circumstances
    assert env.from_string('{% set x=1 %}{% load "news.photos" %}').render() == ''


def test_spaceless():
    from coffin.template.defaulttags import SpacelessExtension
    env = Environment(extensions=[SpacelessExtension])

    assert env.from_string("""{% spaceless %}
<p>
    <a href="foo/">Foo</a>
</p>
{% endspaceless %}""").render() == '<p><a href="foo/">Foo</a></p>'
    assert env.from_string("""{% spaceless %}
    <strong>
        Hello
    </strong>
{% endspaceless %}""").render() == '<strong>\n        Hello\n    </strong>'


def test_url():
    from coffin.template.defaulttags import URLExtension
    from jinja2.exceptions import TemplateSyntaxError
    from django.core.urlresolvers import NoReverseMatch
    env = Environment(extensions=[URLExtension])

    for template, context, expected_result in (
        # various ways to specify the view
        ('{% url urls_app.views.index %}', {}, '/url_test/'),
        ('{% url apps.urls_app.views.index %}', {}, '/url_test/'),  # project name is optional
        ('{% url "urls_app.views.index" %}', {}, '/url_test/'),
        ('{% url "urls_app.views.indexXX"[:-2] %}', {}, '/url_test/'),
        ('{% url the-index-view %}', {}, '/url_test/'),

        # various ways to specify the arguments
        ('{% url urls_app.views.sum 1,2 %}', {}, '/url_test/sum/1,2'),
        ('{% url urls_app.views.sum left=1,right=2 %}', {}, '/url_test/sum/1,2'),
        ('{% url urls_app.views.sum l,2 %}', {'l':1}, '/url_test/sum/1,2'),
        ('{% url urls_app.views.sum left=l,right=2 %}', {'l':1}, '/url_test/sum/1,2'),
        ('{% url urls_app.views.sum left=2*3,right=z()|length %}',
                {'z':lambda: 'u'}, '/url_test/sum/6,1'),   # full expressive syntax

	# regression: string view followed by a string argument works
	('{% url "urls_app.views.sum" "1","2" %}', {}, '/url_test/sum/1,2'),

        # failures
        ('{% url %}', {}, TemplateSyntaxError),
        ('{% url 1,2,3 %}', {}, TemplateSyntaxError),
        ('{% url inexistant-view %}', {}, NoReverseMatch),

        # ValueError, not TemplateSyntaxError:
        # We actually support parsing a mixture of positional and keyword
        # arguments, but reverse() doesn't handle them.
        ('{% url urls_app.views.sum left=1,2 %}', {'l':1}, ValueError),

        # as-syntax
        ('{% url urls_app.views.index as url %}', {}, ''),
        ('{% url urls_app.views.index as url %}{{url}}', {}, '/url_test/'),
        ('{% url inexistent as url %}{{ url }}', {}, ''),    # no exception
    ):
        print template, '==', expected_result
        try:
            actual_result = env.from_string(template).render(context)
        except Exception, e:
            print '==> %s: (%s)' % (type(e), e)
            assert type(e) == expected_result
        else:
            print '==> %s' % actual_result
            assert actual_result == expected_result


def test_url_current_app():
    """Test that the url can deal with the current_app context setting."""
    from coffin.template.loader import get_template_from_string
    from django.template import RequestContext
    from django.http import HttpRequest
    t = get_template_from_string('{% url testapp:the-index-view %}')
    assert t.render(RequestContext(HttpRequest())) == '/app/one/'
    assert t.render(RequestContext(HttpRequest(), current_app="two")) == '/app/two/'


def test_with():
    from coffin.template.defaulttags import WithExtension
    env = Environment(extensions=[WithExtension])

    assert env.from_string('{{ x }}{% with y as x %}{{ x }}{% endwith %}{{ x }}').render({'x': 'x', 'y': 'y'}) == 'xyx'


def test_cache():
    from coffin.template.defaulttags import CacheExtension
    env = Environment(extensions=[CacheExtension])

    x = 0
    assert env.from_string('{%cache 500 "ab"%}{{x}}{%endcache%}').render({'x': x}) == '0'
    # cache is used; Jinja2 expressions work
    x += 1
    assert env.from_string('{%cache 50*10 "a"+"b"%}{{x}}{%endcache%}').render({'x': x}) == '0'
    # vary-arguments can be used
    x += 1
    assert env.from_string('{%cache 50*10 "ab" x "foo"%}{{x}}{%endcache%}').render({'x': x}) == '2'
    x += 1
    assert env.from_string('{%cache 50*10 "ab" x "foo"%}{{x}}{%endcache%}').render({'x': x}) == '3'

########NEW FILE########
__FILENAME__ = test_defaultfilters
from datetime import datetime, date
from nose.tools import assert_raises


def r(s, context={}):
    from coffin.common import env
    return env.from_string(s).render(context)


def test_django_builtins_available():
    """Many filters have not been re-implemented specifically for
    Coffin, but instead the Django version is used through an
    interop-layer.

    Make sure that those are properly made available in Jinja2.
    """
    from coffin.template import defaultfilters
    assert not hasattr(defaultfilters, 'get_digit')  # has no port
    assert r('{{ "23475"|get_digit("2") }}') == '7'
    assert r('{{ unknown|get_digit("2") }}') == ''


def test_jinja2_builtins():
    """Ensure that the Jinja2 builtins are available, and take
    precedence over the Django builtins (which we automatically convert
    and install).
    """
    # Django's default filter only accepts one argument.
    assert r('{{ unknown|default("2", True) }}') == '2'


def test_url():
    # project name is optional
    assert r('{{ "urls_app.views.index"|url() }}') == '/url_test/'
    assert r('{{ "apps.urls_app.views.index"|url() }}') == '/url_test/'


def test_default():
    """We make the Jinja2 default filter behave like Django's without
    arguments, but still support Jinja2 extended syntax.
    """
    assert r('{{ foo|default("default") }}') == 'default'
    assert r('{{ foo|default("default") }}', {'foo': False}) == 'default'
    assert r('{{ foo|default("default", False) }}', {'foo': False}) == 'False'


def test_pluralize():
    assert r('vote{{ 0|pluralize }}') == 'votes'
    assert r('vote{{ 1|pluralize }}') == 'vote'
    assert r('class{{ 2|pluralize("es") }}') == 'classes'
    assert r('cand{{ 0|pluralize("y", "ies") }}') == 'candies'
    assert r('cand{{ 1|pluralize("y", "ies") }}') == 'candy'
    assert r('cand{{ 2|pluralize("y", "ies") }}') == 'candies'
    assert r('vote{{ [1,2,3]|pluralize }}') == 'votes'
    assert r('anonyme{{ 0|pluralize("r", "") }}') == 'anonyme'
    assert r('anonyme{{ 1|pluralize("r", "") }}') == 'anonymer'
    assert r('vote{{ 1|pluralize }}') == 'vote'
    assert_raises(TypeError, r, 'vote{{ x|pluralize }}', {'x': object()})
    assert_raises(ValueError, r, 'vote{{ x|pluralize }}', {'x': 'foo'})


def test_floatformat():
    assert r('{{ 1.3434|floatformat }}') == '1.3'
    assert r('{{ 1.3511|floatformat }}') == '1.4'
    assert r('{{ 1.3|floatformat(2) }}') == '1.30'
    assert r('{{ 1.30|floatformat(-3) }}') == '1.300'
    assert r('{{ 1.000|floatformat(3) }}') == '1.000'
    assert r('{{ 1.000|floatformat(-3) }}') == '1'
    assert_raises(ValueError, r, '{{ "foo"|floatformat(3) }}')
    assert_raises(ValueError, r, '{{ 4.33|floatformat("foo") }}')


def test_date_stuff():
    from coffin.common import env
    assert r('a{{ d|date("Y") }}b', {'d': date(2007, 01, 01)}) == 'a2007b'
    assert r('a{{ d|time("H") }}b', {'d': datetime(2007, 01, 01, 12, 01, 01)}) == 'a12b'
    # TODO: timesince, timeuntil

    # Make sure the date filters can handle unset values gracefully.
    # While generally we'd like to be explicit instead of hiding errors,
    # this is a particular case where it makes sense.
    for f in ('date', 'time', 'timesince', 'timeuntil'):
        assert r('a{{ d|%s }}b' % f) == 'ab'
        assert r('a{{ d|%s }}b' % f, {'d': None}) == 'ab'
########NEW FILE########
__FILENAME__ = test_env
"""Test construction of the implicitly provided JinjaEnvironment,
in the common.py module.
"""

from coffin.common import get_env
from django.test.utils import override_settings


def test_i18n():
    with override_settings(USE_I18N=True):
        assert get_env().from_string('{{ _("test") }}').render() == 'test'


class TestLoaders:

    def test_django_loader_replace(self):
        from coffin.template.loaders import jinja_loader_from_django_loader
        from jinja2 import loaders

        # Test replacement of filesystem loader
        l = jinja_loader_from_django_loader('django.template.loaders.filesystem.Loader')
        assert isinstance(l, loaders.FileSystemLoader)

        # Since we don't do exact matches for the loader string, make sure we
        # are not replacing loaders that are outside the Django namespace.
        l = jinja_loader_from_django_loader('djangoaddon.template.loaders.filesystem.Loader')
        assert not isinstance(l, loaders.FileSystemLoader)

    def test_cached_loader(self):
        from jinja2 import loaders

        with override_settings(TEMPLATE_LOADERS=[
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            )),]):
            env = get_env()
            assert len(env.loader.loaders) == 1
            cached_loader = get_env().loader.loaders[0]
            assert hasattr(cached_loader, 'template_cache')
            assert len(cached_loader.loader.loaders) == 2
            assert isinstance(cached_loader.loader.loaders[0], loaders.FileSystemLoader)

            # the cached loader can find a template too.
            assert env.loader.load(env, 'render-x.html').render({'x': 'foo'}) == 'foo'


########NEW FILE########
__FILENAME__ = test_library
"""Test the various features of our custom library object.
"""

from nose.tools import assert_raises

from jinja2 import TemplateAssertionError as Jinja2TemplateAssertionError
from django.template import Template, Context, \
    TemplateSyntaxError as DjangoTemplateSyntaxError


# TODO: It would be preferrable to split these tests into those checks
# which actually test the Library object, and those which test the assembly
# of the Environment instance. Testcode for the former could be written more
# cleanly by creating the library instances within the test code and
# registering them manually with the environment, rather than having to
# place them in fake Django apps in completely different files to have
# them loaded.
# The tests for the compatibility layer could also be factored out.


def test_nodes_and_extensions():
    """Test availability of registered nodes/extensions.
    """
    from coffin.common import env

    # Jinja2 extensions, loaded from a Coffin library
    assert env.from_string('a{% foo %}b').render() == 'a{foo}b'
    assert env.from_string('a{% foo_ex %}b').render() == 'a{my_foo}b'

    # Django tags, loaded from a Coffin library
    assert Template('{% load django_tags %}a{% foo_coffin %}b').render(Context()) == 'a{foo}b'


def test_objects():
    """For coffin, global objects can be registered.
    """
    from coffin.common import env

    # Jinja2 global objects, loaded from a Coffin library
    assert env.from_string('{{ hello("John") }}').render() == 'Hello John'


def test_filters():
    """Test availability of registered filters.
    """
    from coffin.common import env

    # Filter registered with a Coffin library is available in Django and Jinja2
    assert env.from_string('a{{ "b"|foo }}c').render() == 'a{foo}c'
    assert Template('{% load portable_filters %}a{{ "b"|foo }}c').render(Context()) == 'a{foo}c'

    # Filter registered with a Django library is also available in Jinja2
    Template('{% load django_library %}{{ "b"|foo_django }}').render(Context())
    assert env.from_string('a{{ "b"|foo }}c').render() == 'a{foo}c'

    # Some filters, while registered with a Coffin library, are only
    # available in Jinja2:
    # - when using @environmentfilter
    env.from_string('{{ "b"|environment }}')
    assert_raises(Exception, Template, '{% load jinja2_filters %}{{ "b"|environment }}')
    # - when using @contextfilter
    env.from_string('{{ "b"|context }}')
    assert_raises(Exception, Template, '{% load jinja2_filters %}{{ "b"|context }}')
    # - when requiring more than one argument
    env.from_string('{{ "b"|multiarg(1,2) }}')
    assert_raises(Exception, Template, '{% load jinja2_filters %}{{ "b"|multiarg }}')
    # - when Jinja2-exclusivity is explicitly requested
    env.from_string('{{ "b"|jinja_forced }}')
    assert_raises(Exception, Template, '{% load jinja2_filters %}{{ "b"|jinja_forced }}')
    # [bug] Jinja2-exclusivity caused the compatibility layer to be not
    # applied, causing for example safe strings to be escaped.
    assert env.from_string('{{ "><"|django_jinja_forced }}').render() == '><'


def test_env_builtins_django():
    """Test that when the environment is assembled, Django libraries which
    are included in the list of builtins are properly supported.
    """
    from coffin.common import get_env
    from coffin.template import add_to_builtins
    add_to_builtins('apps.django_lib')
    assert get_env().from_string('a{{ "b"|foo_django_builtin }}c').render() == 'a{foo}c'


def test_filter_compat_safestrings():
    """Test filter compatibility layer with respect to safe strings.
    """
    from coffin.common import env
    env.autoescape = True

    # Jinja-style safe output strings are considered "safe" by both engines
    assert env.from_string('{{ "<b>"|jinja_safe_output }}').render() == '<b>'
    # TODO: The below actually works regardless of our converting between
    # the same string types: Jinja's Markup() strings are actually immune
    # to Django's escape() attempt, since they have a custom version of
    # replace() that operates on an already escaped version.
    assert Template('{% load compat_filters %}{{ "<b>"|jinja_safe_output }}').render(Context()) == '<b>'

    # Unsafe, unmarked output strings are considered "unsafe" by both engines
    assert env.from_string('{{ "<b>"|unsafe_output }}').render() == '&lt;b&gt;'
    assert Template('{% load compat_filters %}{{ "<b>"|unsafe_output }}').render(Context()) == '&lt;b&gt;'

    # Django-style safe output strings are considered "safe" by both engines
    assert env.from_string('{{ "<b>"|django_safe_output }}').render() == '<b>'
    assert Template('{% load compat_filters %}{{ "<b>"|django_safe_output }}').render(Context()) == '<b>'


def test_filter_compat_escapetrings():
    """Test filter compatibility layer with respect to strings flagged as
    "wanted for escaping".
    """
    from coffin.common import env
    env.autoescape = False

    # Django-style "force escaping" works in both engines
    assert env.from_string('{{ "<b>"|django_escape_output }}').render() == '&lt;b&gt;'
    assert Template('{% load compat_filters %}{{ "<b>"|django_escape_output }}').render(Context()) == '&lt;b&gt;'


def test_filter_compat_other():
    """Test other features of the filter compatibility layer.
    """
    # A Django filter with @needs_autoescape works in Jinja2
    from coffin.common import env
    env.autoescape = True
    assert env.from_string('{{ "b"|needing_autoescape }}').render() == 'True'
    env.autoescape = False
    assert env.from_string('{{ "b"|needing_autoescape }}').render() == 'False'

    # [bug] @needs_autoescape also (still) works correctly in Django
    assert Template('{% load compat_filters %}{{ "b"|needing_autoescape }}').render(Context()) == 'True'

    # The Django filters can handle "Undefined" values
    assert env.from_string('{{ doesnotexist|django_raw_output }}').render() == ''

    # TODO: test @stringfilter

########NEW FILE########
__FILENAME__ = test_shortcuts
def test_render():
    """Test the render shortcut."""
    from coffin.shortcuts import render
    response = render(None, 'render-x.html', {'x': 'foo'})
    assert response.content == 'foo'

########NEW FILE########
__FILENAME__ = test_template
"""Tests for ``coffin.template``.

``coffin.template.library``, ``coffin.template.defaultfilters`` and
``coffin.template.defaulttags`` have their own test modules.
"""

def test_template_class():
    from coffin.template import Template
    from coffin.common import env

    # initializing a template directly uses Coffin's Jinja
    # environment - we know it does if our tags are available.
    t = Template('{% spaceless %}{{ ""|truncatewords }}{% endspaceless %}')
    assert t.environment == env

    # render can accept a Django context object
    from django.template import Context
    c = Context()
    c.update({'x': '1'})  # update does a push
    c.update({'y': '2'})
    assert Template('{{x}};{{y}}').render(c) == '1;2'

    # [bug] render can handle nested Context objects
    c1 = Context(); c2 = Context(); c3 = Context()
    c3['foo'] = 'bar'
    c2.update(c3)
    c1.update(c2)
    assert Template('{{foo}}').render(c1) == 'bar'

    # There is a "origin" attribute for Django compatibility
    assert Template('{{foo}}').origin.name == '<template>'


def test_render_to_string():
    # [bug] Test that the values given directly do overwrite does that
    # are already exist in the given context_instance. Due to a bug this
    # was previously not the case.
    from django.template import Context
    from coffin.template.loader import render_to_string
    assert render_to_string('render-x.html', {'x': 'new'},
        context_instance=Context({'x': 'old'})) == 'new'

    # [bug] Test that the values from context_instance actually make it
    # into the template.
    assert render_to_string('render-x.html',
        context_instance=Context({'x': 'foo'})) == 'foo'

    # [bug] Call without the optional ``context_instance`` argument works
    assert render_to_string('render-x.html', {'x': 'foo'}) == 'foo'

    # ``dictionary`` argument may be a Context instance
    assert render_to_string('render-x.html', Context({'x': 'foo'})) == 'foo'

    # [bug] Both ``dictionary`` and ``context_instance`` may be
    # Context objects
    assert render_to_string('render-x.html', Context({'x': 'foo'}), context_instance=Context()) == 'foo'
########NEW FILE########
__FILENAME__ = test_views
def test_import():
    # [bug] make sure the coffin.views module is importable.
    from coffin import views
########NEW FILE########
