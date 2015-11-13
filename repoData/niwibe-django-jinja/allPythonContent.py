__FILENAME__ = apps
from django.apps import AppConfig
from django_jinja import base


class DjangoJinjaAppConfig(AppConfig):
    name = "django_jinja"
    verbose_name = "Django Jinja"

    def ready(self):
        base.initialize_environment()


########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

import os

from jinja2 import Environment
from jinja2 import Template
from jinja2 import FileSystemLoader

from django.conf import settings
from django.template import Origin
from django.template.context import BaseContext
from django.utils.importlib import import_module
from django.utils import six

from . import builtins, utils


JINJA2_ENVIRONMENT_OPTIONS = getattr(settings, "JINJA2_ENVIRONMENT_OPTIONS", {})
JINJA2_EXTENSIONS = getattr(settings, "JINJA2_EXTENSIONS", [])
JINJA2_FILTERS = getattr(settings, "JINJA2_FILTERS", {})
JINJA2_FILTERS_REPLACE_FROM_DJANGO = getattr(settings, "JINJA2_FILTERS_REPLACE_FROM_DJANGO", True)
JINJA2_TESTS = getattr(settings, "JINJA2_TESTS", {})
JINJA2_GLOBALS = getattr(settings, "JINJA2_GLOBALS", {})
JINJA2_AUTOESCAPE = getattr(settings, "JINJA2_AUTOESCAPE", True)
JINJA2_NEWSTYLE_GETTEXT = getattr(settings, "JINJA2_NEWSTYLE_GETTEXT", True)
JINJA2_CONSTANTS = getattr(settings, "JINJA2_CONSTANTS", {})

JINJA2_BYTECODE_CACHE_ENABLE = getattr(settings, "JINJA2_BYTECODE_CACHE_ENABLE", False)
JINJA2_BYTECODE_CACHE_NAME = getattr(settings, "JINJA2_BYTECODE_CACHE_NAME", "default")
JINJA2_BYTECODE_CACHE_BACKEND = getattr(settings, "JINJA2_BYTECODE_CACHE_BACKEND",
                                        "django_jinja.cache.BytecodeCache")


# Default jinja extension list
DEFAULT_EXTENSIONS = [
    "jinja2.ext.do",
    "jinja2.ext.loopcontrols",
    "jinja2.ext.with_",
    "jinja2.ext.i18n",
    "jinja2.ext.autoescape",
]


JINJA2_FILTERS.update({
    "static": "django_jinja.builtins.filters.static",
    "reverseurl": "django_jinja.builtins.filters.reverse",
    "addslashes": "django_jinja.builtins.filters.addslashes",
    "capfirst": "django_jinja.builtins.filters.capfirst",
    "escapejs": "django_jinja.builtins.filters.escapejs_filter",
    "fix_ampersands": "django_jinja.builtins.filters.fix_ampersands_filter",
    "floatformat": "django_jinja.builtins.filters.floatformat",
    "iriencode": "django_jinja.builtins.filters.iriencode",
    "linenumbers": "django_jinja.builtins.filters.linenumbers",
    "make_list": "django_jinja.builtins.filters.make_list",
    "slugify": "django_jinja.builtins.filters.slugify",
    "stringformat": "django_jinja.builtins.filters.stringformat",
    "truncatechars": "django_jinja.builtins.filters.truncatechars",
    "truncatewords": "django_jinja.builtins.filters.truncatewords",
    "truncatewords_html": "django_jinja.builtins.filters.truncatewords_html",
    "urlizetrunc": "django_jinja.builtins.filters.urlizetrunc",
    "ljust": "django_jinja.builtins.filters.ljust",
    "rjust": "django_jinja.builtins.filters.rjust",
    "cut": "django_jinja.builtins.filters.cut",
    "linebreaksbr": "django_jinja.builtins.filters.linebreaksbr",
    "linebreaks": "django_jinja.builtins.filters.linebreaks_filter",
    "removetags": "django_jinja.builtins.filters.removetags",
    "striptags": "django_jinja.builtins.filters.striptags",
    "add": "django_jinja.builtins.filters.add",
    "date": "django_jinja.builtins.filters.date",
    "time": "django_jinja.builtins.filters.time",
    "timesince": "django_jinja.builtins.filters.timesince_filter",
    "timeuntil": "django_jinja.builtins.filters.timeuntil_filter",
    "default_if_none": "django_jinja.builtins.filters.default_if_none",
    "divisibleby": "django_jinja.builtins.filters.divisibleby",
    "yesno": "django_jinja.builtins.filters.yesno",
    "pluralize": "django_jinja.builtins.filters.pluralize",
})

if JINJA2_FILTERS_REPLACE_FROM_DJANGO:
    JINJA2_FILTERS.update({
        "title": "django_jinja.builtins.filters.title",
        "upper": "django_jinja.builtins.filters.upper",
        "lower": "django_jinja.builtins.filters.lower",
        "urlencode": "django_jinja.builtins.filters.urlencode",
        "urlize": "django_jinja.builtins.filters.urlize",
        "wordcount": "django_jinja.builtins.filters.wordcount",
        "wordwrap": "django_jinja.builtins.filters.wordwrap",
        "center": "django_jinja.builtins.filters.center",
        "join": "django_jinja.builtins.filters.join",
        "length": "django_jinja.builtins.filters.length",
        "random": "django_jinja.builtins.filters.random",
        "default": "django_jinja.builtins.filters.default",
        "filesizeformat": "django_jinja.builtins.filters.filesizeformat",
        "pprint": "django_jinja.builtins.filters.pprint",
    })

JINJA2_GLOBALS.update({
    "url": "django_jinja.builtins.global_context.url",
    "static": "django_jinja.builtins.global_context.static",
})


def dict_from_context(context):
    """
    Converts context to native python dict.
    """

    if isinstance(context, BaseContext):
        new_dict = {}
        for i in reversed(list(context)):
            new_dict.update(dict_from_context(i))
        return new_dict

    return dict(context)


class Template(Template):
    """
    Customized template class.
    Add correct handling django context objects.
    """

    def render(self, context={}):
        new_context = dict_from_context(context)

        if settings.TEMPLATE_DEBUG:
            from django.test import signals
            self.origin = Origin(self.filename)
            signals.template_rendered.send(sender=self, template=self, context=context)

        return super(Template, self).render(new_context)

    def stream(self, context={}):
        new_context = dict_from_context(context)

        if settings.TEMPLATE_DEBUG:
            from django.test import signals
            self.origin = Origin(self.filename)
            signals.template_rendered.send(sender=self, template=self, context=context)

        return super(Template, self).stream(new_context)


class Environment(Environment):
    def initialize(self):
        self.initialize_i18n()
        self.initialize_bytecode_cache()
        self.initialize_template_loader()
        self.initialize_autoescape()

    def initialize_i18n(self):
        # install translations
        if settings.USE_I18N:
            from django.utils import translation
            self.install_gettext_translations(translation, newstyle=JINJA2_NEWSTYLE_GETTEXT)
        else:
            self.install_null_translations(newstyle=JINJA2_NEWSTYLE_GETTEXT)

    def initialize_bytecode_cache(self):
        # Install bytecode cache if is enabled
        if JINJA2_BYTECODE_CACHE_ENABLE:
            cls = utils.load_class(JINJA2_BYTECODE_CACHE_BACKEND)
            self.bytecode_cache = cls(JINJA2_BYTECODE_CACHE_NAME)

    def initialize_template_loader(self):
        self.template_class = Template

        loader = getattr(settings, "JINJA2_LOADER", None)
        if loader is None:
            from django.template.loaders import app_directories
            default_loader_dirs = (app_directories.app_template_dirs +
                                   tuple(settings.TEMPLATE_DIRS))

            self.loader = FileSystemLoader(default_loader_dirs)
        elif isinstance(loader, six.string_types):
            loader_params = getattr(settings, "JINJA2_LOADER_SETTINGS", {})
            cls = utils.load_class(loader)
            self.loader = cls(**loader_params)
        else:
            self.loader = loader

    def initialize_autoescape(self):
        if not self.autoescape:
            return

        from django.utils import safestring

        if hasattr(safestring, "SafeText"):
            if not hasattr(safestring.SafeText, "__html__"):
                safestring.SafeText.__html__ = lambda self: six.text_type(self)

        if hasattr(safestring, "SafeString"):
            if not hasattr(safestring.SafeString, "__html__"):
                safestring.SafeString.__html__ = lambda self: six.text_type(self)

        if hasattr(safestring, "SafeUnicode"):
            if not hasattr(safestring.SafeUnicode, "__html__"):
                safestring.SafeUnicode.__html__ = lambda self: six.text_type(self)

        if hasattr(safestring, "SafeBytes"):
            if not hasattr(safestring.SafeBytes, "__html__"):
                safestring.SafeBytes.__html__ = lambda self: six.text_type(self)


def get_templatetags_modules_list():
    """
    Get list of modules that contains templatetags
    submodule.
    """
    # Django 1.7 compatibility imports
    try:
        from django.apps import apps
        all_modules = [x.name for x in apps.get_app_configs()]
    except ImportError:
        all_modules = settings.INSTALLED_APPS

    mod_list = []
    for app_path in all_modules:
        try:
            mod = import_module(app_path + ".templatetags")
            mod_list.append((app_path, os.path.dirname(mod.__file__)))
        except ImportError:
            pass

    return mod_list


def load_builtins(env):
    for name, value in JINJA2_FILTERS.items():
        if isinstance(value, six.string_types):
            env.filters[name] = utils.load_class(value)
        else:
            env.filters[name] = value

    for name, value in JINJA2_TESTS.items():
        if isinstance(value, six.string_types):
            env.tests[name] = utils.load_class(value)
        else:
            env.tests[name] = value

    for name, value in JINJA2_GLOBALS.items():
        if isinstance(value, six.string_types):
            env.globals[name] = utils.load_class(value)
        else:
            env.globals[name] = value

    for name, value in JINJA2_CONSTANTS.items():
        env.globals[name] = value

    env.add_extension(builtins.extensions.CsrfExtension)
    env.add_extension(builtins.extensions.CacheExtension)


def load_django_templatetags():
    """
    Given a ready modules list, try import all modules
    related to templatetags for populate a library.
    """

    for app_path, mod_path in get_templatetags_modules_list():
        if not os.path.isdir(mod_path):
            continue

        for filename in filter(lambda x: x.endswith(".py") or x.endswith(".pyc"), os.listdir(mod_path)):
            # Exclude __init__.py files
            if filename == "__init__.py" or filename == "__init__.pyc":
                continue

            file_mod_path = "%s.templatetags.%s" % (app_path, filename.rsplit(".", 1)[0])
            try:
                import_module(file_mod_path)
            except ImportError:
                pass


initial_params = {
    "autoescape": JINJA2_AUTOESCAPE,
    "extensions": list(set(list(JINJA2_EXTENSIONS) + DEFAULT_EXTENSIONS)),
}

initial_params.update(JINJA2_ENVIRONMENT_OPTIONS)
env = Environment(**initial_params)


def initialize_environment():
    env.initialize()

    load_django_templatetags()
    load_builtins(env)


__all__ = ["env", "initialize_environment"]

########NEW FILE########
__FILENAME__ = extensions
from __future__ import unicode_literals

import traceback

from django.conf import settings
from django.core.cache import cache
import django

from jinja2.ext import Extension
from jinja2 import nodes
from jinja2 import Markup
from jinja2 import TemplateSyntaxError


try:
    from django.utils.encoding import force_text
    from django.utils.encoding import force_bytes
except ImportError:
    from django.utils.encoding import force_unicode as force_text
    from django.utils.encoding import smart_str as force_bytes

# Compatibility with django <= 1.5

if django.VERSION[:2] <= (1, 5):
    import hashlib
    from django.utils.http import urlquote

    def make_template_fragment_key(fragm_name, vary_on):
        args_map = map(urlquote, vary_on)
        args_map = map(lambda x: force_bytes(x), args_map)

        args_string = b':'.join(args_map)
        args_hash = hashlib.md5(args_string).hexdigest()

        return 'template.cache.{0}.{1}'.format(fragm_name, args_hash)
else:
    from django.core.cache.utils import make_template_fragment_key


class CsrfExtension(Extension):
    tags = set(['csrf_token'])

    def __init__(self, environment):
        self.environment = environment

    def parse(self, parser):
        try:
            token = next(parser.stream)
            call_res = self.call_method('_render', [nodes.Name('csrf_token', 'load')])
            return nodes.Output([call_res]).set_lineno(token.lineno)
        except Exception:
            traceback.print_exc()

    def _render(self, csrf_token):
        if csrf_token:
            if csrf_token == 'NOTPROVIDED':
                return Markup("")

            return Markup("<input type='hidden'"
                          " name='csrfmiddlewaretoken' value='%s' />" % (csrf_token))

        if settings.DEBUG:
            import warnings
            warnings.warn("A {% csrf_token %} was used in a template, but the context"
                          "did not provide the value.  This is usually caused by not "
                          "using RequestContext.")
        return ''


class CacheExtension(Extension):
    """
    Exactly like Django's own tag, but supports full Jinja2
    expressiveness for all arguments.

        {% cache gettimeout()*2 "foo"+options.cachename  %}
            ...
        {% endcache %}

    General Syntax:

        {% cache [expire_time] [fragment_name] [var1] [var2] .. %}
            .. some expensive processing ..
        {% endcache %}

    Available by default (does not need to be loaded).

    Partly based on the ``FragmentCacheExtension`` from the Jinja2 docs.
    """

    tags = set(['cache'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno

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
        try:
            expire_time = int(expire_time)
        except (ValueError, TypeError):
            raise TemplateSyntaxError('"%s" tag got a non-integer timeout '
                'value: %r' % (list(self.tags)[0], expire_time), lineno)

        cache_key = make_template_fragment_key(fragm_name, vary_on)

        value = cache.get(cache_key)
        if value is None:
            value = caller()
            cache.set(cache_key, force_text(value), expire_time)

        return value

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

from django.core.urlresolvers import reverse as django_reverse
from django.contrib.staticfiles.storage import staticfiles_storage
from jinja2 import Markup


def reverse(value, *args, **kwargs):
    """
    Shortcut filter for reverse url on templates. Is a alternative to
    django {% url %} tag, but more simple.

    Usage example:
        {{ 'web:timeline'|reverse(userid=2) }}

    This is a equivalent to django:
        {% url 'web:timeline' userid=2 %}

    """
    return django_reverse(value, args=args, kwargs=kwargs)

def static(path):
    return staticfiles_storage.url(path)


from django.template.defaultfilters import addslashes
from django.template.defaultfilters import capfirst
from django.utils.html import escapejs as escapejs_filter
from django.utils.html import fix_ampersands as fix_ampersands_filter
from django.template.defaultfilters import floatformat
from django.template.defaultfilters import iriencode
from django.template.defaultfilters import linenumbers
from django.template.defaultfilters import make_list
from django.template.defaultfilters import stringformat
from django.template.defaultfilters import title
from django.template.defaultfilters import truncatechars
from django.template.defaultfilters import truncatewords
from django.template.defaultfilters import truncatewords_html
from django.template.defaultfilters import upper
from django.template.defaultfilters import lower
from django.template.defaultfilters import urlencode
from django.template.defaultfilters import urlize
from django.template.defaultfilters import urlizetrunc
from django.template.defaultfilters import wordcount
from django.template.defaultfilters import wordwrap
from django.template.defaultfilters import ljust
from django.template.defaultfilters import rjust
from django.template.defaultfilters import center
from django.template.defaultfilters import cut
from django.template.defaultfilters import linebreaks_filter
from django.template.defaultfilters import linebreaksbr
from django.template.defaultfilters import removetags
from django.template.defaultfilters import striptags
from django.template.defaultfilters import join
from django.template.defaultfilters import length
from django.template.defaultfilters import random
from django.template.defaultfilters import add
from django.template.defaultfilters import date
from django.template.defaultfilters import time
from django.template.defaultfilters import timesince_filter
from django.template.defaultfilters import timeuntil_filter
from django.template.defaultfilters import default
from django.template.defaultfilters import default_if_none
from django.template.defaultfilters import divisibleby
from django.template.defaultfilters import yesno
from django.template.defaultfilters import filesizeformat
from django.template.defaultfilters import pprint
from django.template.defaultfilters import pluralize

try:
    from django.utils.text import slugify as djslugify
except ImportError:
    from django.template.defaultfilters import slugify as djslugify

def slugify(value):
    return djslugify(force_text(value))

########NEW FILE########
__FILENAME__ = global_context
# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.core.urlresolvers import reverse as django_reverse, NoReverseMatch
from django.contrib.staticfiles.storage import staticfiles_storage

JINJA2_MUTE_URLRESOLVE_EXCEPTIONS = getattr(settings, "JINJA2_MUTE_URLRESOLVE_EXCEPTIONS", False)
logger = logging.getLogger(__name__)


def url(name, *args, **kwargs):
    """
    Shortcut filter for reverse url on templates. Is a alternative to
    django {% url %} tag, but more simple.

    Usage example:
        {{ url('web:timeline', userid=2) }}

    This is a equivalent to django:
        {% url 'web:timeline' userid=2 %}

    """
    try:
        return django_reverse(name, args=args, kwargs=kwargs)
    except NoReverseMatch as exc:
        logger.error('Error: %s', exc)
        if not JINJA2_MUTE_URLRESOLVE_EXCEPTIONS:
            raise
        return ''


def static(path):
    return staticfiles_storage.url(path)

########NEW FILE########
__FILENAME__ = cache
# -*- coding: utf-8 -*-

from django.core.cache import get_cache
from django.utils.functional import cached_property
from jinja2 import BytecodeCache as _BytecodeCache


class BytecodeCache(_BytecodeCache):
    """
    A bytecode cache for Jinja2 that uses Django's caching framework.
    """

    def __init__(self, cache_name):
        self._cache_name = cache_name

    @cached_property
    def backend(self):
        return get_cache(self._cache_name)

    def load_bytecode(self, bucket):
        key = 'jinja2_%s' % str(bucket.key)
        bytecode = self.backend.get(key)
        if bytecode:
            bucket.bytecode_from_string(bytecode)

    def dump_bytecode(self, bucket):
        key = 'jinja2_%s' % str(bucket.key)
        self.backend.set(key, bucket.bytecode_to_string())

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-



########NEW FILE########
__FILENAME__ = thumbnails
# -*- coding: utf-8 -*-

from easy_thumbnails.templatetags import thumbnail as _thumbnail
from django_jinja import library


@library.filter
def thumbnail_url(source, alias):
    return _thumbnail.thumbnail_url(source, alias)


@library.global_function
def thumbnailer_passive(obj):
    return _thumbnail.thumbnailer_passive(obj)


@library.global_function
def thumbnailer(obj):
    return _thumbnail.thumbnailer(obj)


@library.global_function
def thumbnail(source, **kwargs):
    thumbnail =  _thumbnail.get_thumbnailer(source).get_thumbnail(kwargs)
    return thumbnail.url

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-



########NEW FILE########
__FILENAME__ = _humanize
# -*- coding: utf-8 -*-

from django.contrib.humanize.templatetags import humanize
from django_jinja import library


@library.filter
def ordinal(source):
    return humanize.ordinal(source)


@library.filter
def intcomma(source, use_l10n=True):
    return humanize.intcomma(source, use_l10n)


@library.filter
def intword(source):
    return humanize.intword(source)


@library.filter
def apnumber(source):
    return humanize.apnumber(source)


@library.filter
def naturalday(source, arg=None):
    return humanize.naturalday(source, arg)


@library.filter
def naturaltime(source):
    return humanize.naturaltime(source)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = _pipeline
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.contrib.staticfiles.storage import staticfiles_storage
from django.template.loader import render_to_string

from pipeline.conf import settings
from pipeline.utils import guess_type
from pipeline.packager import Packager, PackageNotFound

from django_jinja import library, utils


@library.global_function
@utils.safe
def compressed_css(name):
    package = settings.PIPELINE_CSS.get(name, {})
    if package:
        package = {name: package}

    packager = Packager(css_packages=package, js_packages={})

    try:
        package = packager.package_for('css', name)
    except PackageNotFound:
        return ""

    def _render_css(path):
        template_name = package.template_name or "pipeline/css.jinja"

        context = package.extra_context
        context.update({
            'type': guess_type(path, 'text/css'),
            'url': staticfiles_storage.url(path)
        })

        return render_to_string(template_name, context)

    if settings.PIPELINE_ENABLED:
        return _render_css(package.output_filename)

    paths = packager.compile(package.paths)
    tags = [_render_css(path) for path in paths]

    return '\n'.join(tags)


@library.global_function
@utils.safe
def compressed_js(name):
    package = settings.PIPELINE_JS.get(name, {})
    if package:
        package = {name: package}

    packager = Packager(css_packages={}, js_packages=package)
    try:
        package = packager.package_for('js', name)
    except PackageNotFound:
        return ""

    def _render_js(path):
        template_name = package.template_name or "pipeline/js.jinja"
        context = package.extra_context
        context.update({
            'type': guess_type(path, 'text/javascript'),
            'url': staticfiles_storage.url(path),
        })
        return render_to_string(template_name, context)

    def _render_inline_js(js):
        context = package.extra_context
        context.update({
            'source': js
        })
        return render_to_string("pipeline/inline_js.jinja", context)

    if settings.PIPELINE_ENABLED:
        return _render_js(package.output_filename)

    paths = packager.compile(package.paths)
    templates = packager.pack_templates(package)
    tags = [_render_js(js) for js in paths]

    if templates:
        tags.append(_render_inline_js(templates))

    return '\n'.join(tags)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = subdomainurls
# -*- coding: utf-8 -*-

from django_jinja import library
from jinja2 import contextfunction
from subdomains.templatetags.subdomainurls import url as subdomain_url


@library.global_function
@contextfunction
def url(context, *args, **kwargs):
    return subdomain_url(context, *args, **kwargs)

########NEW FILE########
__FILENAME__ = library
# -*- coding: utf-8 -*-

import warnings


def _get_env():
    from django_jinja.base import env
    return env


def _attach_function(attr, func, name=None):
    _env = _get_env()
    _attr = getattr(_env, attr)

    if name is None:
        name = func.__name__

    _attr[name] = func
    return func


def _register_function(attr, name=None, fn=None):
    if name is None and fn is None:
        def dec(func):
            return _attach_function(attr, func)
        return dec

    elif name is not None and fn is None:
        if callable(name):
            return _attach_function(attr, name)
        else:
            def dec(func):
                return _register_function(attr, name, func)
            return dec

    elif name is not None and fn is not None:
        return _attach_function(attr, fn, name)

    raise RuntimeError("Invalid parameters")



def global_function(*args, **kwargs):
    return _register_function("globals", *args, **kwargs)


def test(*args, **kwargs):
    return _register_function("tests", *args, **kwargs)


def filter(*args, **kwargs):
    return _register_function("filters", *args, **kwargs)


class Library(object):
    def __init__(self):
        warnings.warn("Use Library class is deprecated and will be removed "
                      "in future versions", DeprecationWarning, stacklevel=2)

    def global_function(self, *args, **kwargs):
        return _register_function("globals", *args, **kwargs)

    def test(self, *args, **kwargs):
        return _register_function("tests", *args, **kwargs)

    def filter(self, *args, **kwargs):
        return _register_function("filters", *args, **kwargs)

    def __setitem__(self, item, value):
        _env = _get_env()
        _env.globals[item] = value

    def __getitem__(self, item, value):
        _env = _get_env()
        return _env.globals[item]

########NEW FILE########
__FILENAME__ = loaders
# -*- coding: utf-8 -*-

import re

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loaders import app_directories
from django.template.loaders import filesystem
from django_jinja.base import env

import jinja2


if hasattr(settings, "DEFAULT_JINJA2_TEMPLATE_INTERCEPT_RE"):
    RE_INTERCEPT_ON = True
    DEFAULT_JINJA2_TEMPLATE_INTERCEPT_RE = \
        settings.DEFAULT_JINJA2_TEMPLATE_INTERCEPT_RE
    RE_INTERCEPT = re.compile(settings.DEFAULT_JINJA2_TEMPLATE_INTERCEPT_RE)
else:
    RE_INTERCEPT_ON = False
    DEFAULT_JINJA2_TEMPLATE_EXTENSION = getattr(settings,
        'DEFAULT_JINJA2_TEMPLATE_EXTENSION', '.jinja')


class LoaderMixin(object):
    is_usable = True

    def load_template(self, template_name, template_dirs=None):
        # If regex intercept is off (default), try
        # template intercept by extension.
        if (not RE_INTERCEPT_ON and
                not template_name.endswith(DEFAULT_JINJA2_TEMPLATE_EXTENSION)):
            return super(LoaderMixin, self).load_template(template_name, template_dirs)

        # If regex intercept is on, try regex match over
        # template name.
        elif RE_INTERCEPT_ON and not RE_INTERCEPT.match(template_name):
            return super(LoaderMixin, self).load_template(template_name, template_dirs)

        try:
            template = env.get_template(template_name)
            return template, template.filename
        except jinja2.TemplateNotFound:
            raise TemplateDoesNotExist(template_name)


class FileSystemLoader(LoaderMixin, filesystem.Loader):
    pass


class AppLoader(LoaderMixin, app_directories.Loader):
    pass

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
__FILENAME__ = models
import django

if django.get_version() < '1.7':
    from django_jinja import base
    base.initialize_environment()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import functools
from importlib import import_module

from django.utils.safestring import mark_safe
from django.core.exceptions import ImproperlyConfigured


def load_class(path):
    """
    Load class from path.
    """

    try:
        mod_name, klass_name = path.rsplit('.', 1)
        mod = import_module(mod_name)
    except AttributeError as e:
        raise ImproperlyConfigured('Error importing {0}: "{1}"'.format(mod_name, e))

    try:
        klass = getattr(mod, klass_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "{0}" does not define a "{1}" class'.format(mod_name, klass_name))

    return klass


def safe(function):
    @functools.wraps(function)
    def _decorator(*args, **kwargs):
        return mark_safe(function(*args, **kwargs))
    return _decorator


########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django.conf import settings
from django.views.generic import View
from django.template import loader, RequestContext
from django import http


class GenericView(View):
    response_cls = http.HttpResponse
    content_type = "text/html"
    tmpl_name = None

    def get_context_data(self):
        return {"view": self}

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        output = loader.render_to_string(self.tmpl_name, context,
                                         context_instance=RequestContext(request))
        return self.response_cls(output, content_type=self.content_type)


class ErrorView(GenericView):
    def head(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class PageNotFound(ErrorView):
    tmpl_name = "404" + getattr(settings, 'DEFAULT_JINJA2_TEMPLATE_EXTENSION', '.jinja')
    response_cls = http.HttpResponseNotFound


class PermissionDenied(ErrorView):
    tmpl_name = "403" + getattr(settings, 'DEFAULT_JINJA2_TEMPLATE_EXTENSION', '.jinja')
    response_cls = http.HttpResponseForbidden


class ServerError(ErrorView):
    tmpl_name = "500" + getattr(settings, 'DEFAULT_JINJA2_TEMPLATE_EXTENSION', '.jinja')
    response_cls = http.HttpResponseServerError

########NEW FILE########
__FILENAME__ = settings
# Django settings for example_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'testdb',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '5gj0k2i*kn(#t!gp=m*r($g6erhozfb$8l5r7!2xt_$9k=!1@7'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django_jinja.loaders.AppLoader',
    'django_jinja.loaders.FileSystemLoader',
    #'django.template.loaders.filesystem.Loader',
    #'django.template.loaders.app_directories.Loader',
    #'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example_project.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jinja',
    'example_project.web',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.views.generic.base import TemplateView

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

from example_project.web.views import Test1, Test2

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'example_project.views.home', name='home'),
    # url(r'^example_project/', include('example_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^test1/$', Test1.as_view(), name='test-1'),
    url(r'^test2/$', Test2.as_view(), name='test-2'),
    url(r'^test3/$', TemplateView.as_view(template_name='test3.jinja'), name='test-3')
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = testags
# -*- coding: utf-8 -*-

from django_jinja.base import Library
import jinja2

register = Library()

@register.filter
@jinja2.contextfilter
def datetimeformat(ctx, value, format='%H:%M / %d-%m-%Y'):
    return value.strftime(format)

@register.global_function
def hello(name):
    return "Hello" + name

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

from django.views.generic import View
from django.shortcuts import render_to_response
from django.template import RequestContext

lista = [{'id':x, 'pow': x*x} for x in xrange(20)]
import datetime

class Test1(View):
    def get(self, request):
        context = {
            'lista': lista,
            'pub_date': datetime.datetime.now(),
        }
        
        context['footext'] = "<div>Test</div>"

        return render_to_response("home.jinja", context,
            context_instance=RequestContext(request))


class Test2(View):
    def get(self, request):
        return render_to_response("home.html", {'lista':lista},
            context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example_project project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")
import sys
sys.path.insert(0, '/home/niwi/devel/django-jinja')

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

sys.path.insert(0, '..')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-



########NEW FILE########
__FILENAME__ = sample_addons
# -*- coding: utf-8 -*-

from django_jinja.library import Library
import jinja2

register = Library()

@register.test(name="one")
def is_one(n):
    return n == 1


@register.filter
@jinja2.contextfilter
def replace(context, value, x, y):
    return value.replace(x, y)


@register.global_function
def myecho(data):
    return data

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from django.http import HttpResponse
from django.test import signals, TestCase
from django.test.client import RequestFactory
from django.template.loader import render_to_string
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.urlresolvers import NoReverseMatch

from django_jinja.base import env, dict_from_context, Template

import datetime
import sys

class TemplateFunctionsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def tearDown(self):
        pass

    def test_template_filters(self):
        filters_data = [
            ("{{ 'test-static.css'|static }}", {}, '/static/test-static.css'),
            ("{{ 'test-1'|reverseurl }}", {}, '/test1/'),
            ("{{ 'test-1'|reverseurl(data=2) }}", {}, '/test1/2/'),
            ("{{ num|floatformat }}", {'num': 34.23234}, '34.2'),
            ("{{ num|floatformat(3) }}", {'num': 34.23234}, '34.232'),
            ("{{ 'hola'|capfirst }}", {}, "Hola"),
            ("{{ 'hola mundo'|truncatechars(5) }}", {}, "ho..."),
            ("{{ 'hola mundo'|truncatewords(1) }}", {}, "hola ..."),
            ("{{ 'hola mundo'|truncatewords_html(1) }}", {}, "hola ..."),
            ("{{ 'hola mundo'|wordwrap(1) }}", {}, "hola\nmundo"),
            ("{{ 'hola mundo'|title }}", {}, "Hola Mundo"),
            ("{{ 'hola mundo'|slugify }}", {}, "hola-mundo"),
            ("{{ 'hello'|ljust(10) }}", {}, "hello     "),
            ("{{ 'hello'|rjust(10) }}", {}, "     hello"),
            ("{{ 'hello\nworld'|linebreaksbr }}", {}, "hello<br />world"),
            ("{{ '<div>hello</div>'|removetags('div') }}", {}, "hello"),
            ("{{ '<div>hello</div>'|striptags }}", {}, "hello"),
            ("{{ list|join(',') }}", {'list':['a','b']}, 'a,b'),
            ("{{ 3|add(2) }}", {}, "5"),
            ("{{ now|date('n Y') }}", {"now": datetime.datetime(2012, 12, 20)}, "12 2012"),
            ("{{ url('test-1') }}", {}, '/test1/'),
            ("{{ foo }}", {}, "bar"),
        ]

        print()
        for template_str, kwargs, result in filters_data:
            print("- Testing: ", template_str, "with:", kwargs)
            template = env.from_string(template_str)
            _result = template.render(kwargs)
            self.assertEqual(_result, result)

    def test_urlresolve_exceptions(self):
        template = env.from_string("{{ url('adads') }}")
        template.render({})

    def test_custom_addons_01(self):
        template = env.from_string("{{ 'Hello'|replace('H','M') }}")
        result = template.render({})

        self.assertEqual(result, "Mello")

    def test_custom_addons_02(self):
        template = env.from_string("{% if m is one %}Foo{% endif %}")
        result = template.render({'m': 1})

        self.assertEqual(result, "Foo")

    def test_custom_addons_03(self):
        template = env.from_string("{{ myecho('foo') }}")
        result = template.render({})

        self.assertEqual(result, "foo")

    def test_autoescape_01(self):
        old_autoescape_value = env.autoescape
        env.autoescape = True

        template = env.from_string("{{ foo|safe }}")
        result = template.render({'foo': '<h1>Hellp</h1>'})
        self.assertEqual(result, "<h1>Hellp</h1>")

        env.autoescape = old_autoescape_value

    def test_autoescape_02(self):
        old_autoescape_value = env.autoescape
        env.autoescape = True

        template = env.from_string("{{ foo }}")
        result = template.render({'foo': '<h1>Hellp</h1>'})
        self.assertEqual(result, "&lt;h1&gt;Hellp&lt;/h1&gt;")

        env.autoescape = old_autoescape_value

    def test_csrf_01(self):
        template_content = "{% csrf_token %}"

        request = self.factory.get('/customer/details')
        if sys.version_info[0] < 3:
            request.META["CSRF_COOKIE"] = b'1234123123'
        else:
            request.META["CSRF_COOKIE"] = '1234123123'

        context = dict_from_context(RequestContext(request))

        template = env.from_string(template_content)
        result = template.render(context)
        self.assertEqual(result, "<input type='hidden' name='csrfmiddlewaretoken' value='1234123123' />")

    def test_cache_01(self):
        template_content = "{% cache 200 'fooo' %}fóäo bar{% endcache %}"

        request = self.factory.get('/customer/details')
        context = dict_from_context(RequestContext(request))

        template = env.from_string(template_content)
        result = template.render(context)

        self.assertEqual(result, "fóäo bar")

    def test_404_page(self):
        response = self.client.get(reverse("page-404"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b"404")
        response = self.client.post(reverse("page-404"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b"404")
        response = self.client.put(reverse("page-404"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b"404")
        response = self.client.delete(reverse("page-404"))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b"404")

    def test_403_page(self):
        response = self.client.get(reverse("page-403"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b"403")

    def test_500_page(self):
        response = self.client.get(reverse("page-500"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"500")


class DjangoPipelineTestTest(TestCase):
    def test_pipeline_js_safe(self):
        template = env.from_string("{{ compressed_js('test') }}")
        result = template.render({})
        self.assertEqual(result,
            '<script type="application/javascript" src="/static/script.2.js" charset="utf-8"></script>')

    def test_pipeline_css_safe(self):
        template = env.from_string("{{ compressed_css('test') }}")
        result = template.render({})
        self.assertEqual(result,
            '<link href="/static/style.2.css" rel="stylesheet" type="text/css" />')


class TemplateDebugSignalsTest(TestCase):
    def setUp(self):
        signals.template_rendered.connect(self._listener)

    def tearDown(self):
        signals.template_rendered.disconnect(self._listener)
        signals.template_rendered.disconnect(self._fail_listener)

    def _listener(self, sender=None, template=None, **kwargs):
        self.assertTrue(isinstance(sender, Template))
        self.assertTrue(isinstance(template, Template))

    def _fail_listener(self, *args, **kwargs):
        self.fail("I shouldn't be called")

    def test_render(self):
        with self.settings(TEMPLATE_DEBUG=True):
            tmpl = Template("OK")
            tmpl.render()

    def test_render_without_template_debug_setting(self):
        signals.template_rendered.connect(self._fail_listener)

        with self.settings(TEMPLATE_DEBUG=False):
            tmpl = Template("OK")
            tmpl.render()

    def test_stream(self):
        with self.settings(TEMPLATE_DEBUG=True):
            tmpl = Template("OK")
            tmpl.stream()

    def test_stream_without_template_debug_setting(self):
        signals.template_rendered.connect(self._fail_listener)

        with self.settings(TEMPLATE_DEBUG=False):
            tmpl = Template("OK")
            tmpl.stream()

    def test_template_used(self):
        """
        Test TestCase.assertTemplateUsed with django-jinja template
        """
        template_name = 'test.jinja'

        def view(request, template_name):
            tmpl = Template("{{ test }}")
            return HttpResponse(tmpl.stream({"test": "success"}))

        with self.settings(TEMPLATE_DEBUG=True):
            request = RequestFactory().get('/')
            response = view(request, template_name=template_name)
            self.assertTemplateUsed(response, template_name)
            self.assertEqual(response.content, b"success")

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url
from django_jinja import views

from .views import BasicTestView

urlpatterns = patterns('',
    url(r'^test1/$', BasicTestView.as_view(), name='test-1'),
    url(r'^test1/(?P<data>\d+)/$', BasicTestView.as_view(), name='test-1'),
    url(r'^test/404$', views.PageNotFound.as_view(), name="page-404"),
    url(r'^test/403$', views.PermissionDenied.as_view(), name="page-403"),
    url(r'^test/500$', views.ServerError.as_view(), name="page-500"),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-

from django.views.generic import View
from django.http import HttpResponse


class BasicTestView(View):
    def get(self, request, data=None):
        return HttpResponse("Hello World")



########NEW FILE########
__FILENAME__ = runtests
# -*- coding: utf-8 -*-

import sys, os
import django

from django.conf import settings
from django.core.management import call_command

TEST_TEMPLATE_DIR = 'templates'
RUNTESTS_DIR = os.path.dirname(__file__)
PREVIOUS_DIR = os.path.abspath(os.path.join(RUNTESTS_DIR, ".."))
sys.path.insert(0, PREVIOUS_DIR)


test_settings = {
    'DATABASES':{
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    'INSTALLED_APPS': [
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.staticfiles',
        'django.contrib.messages',
        'django_jinja',
        'django_jinja_test',
        'pipeline',
        'django_jinja.contrib._pipeline',
    ],
    'ROOT_URLCONF':'django_jinja_test.urls',
    'STATIC_URL':'/static/',
    'STATIC_ROOT': os.path.join(RUNTESTS_DIR, 'static'),
    'TEMPLATE_DIRS':(
        os.path.join(RUNTESTS_DIR, TEST_TEMPLATE_DIR),
    ),
    'USE_I18N': True,
    'USE_TZ': True,
    'LANGUAGE_CODE':'en',
    'MIDDLEWARE_CLASSES': (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ),
    'MANAGERS': ("niwi@niwi.be",),
    'TEMPLATE_LOADERS': [
        'django_jinja.loaders.AppLoader',
        'django_jinja.loaders.FileSystemLoader',
    ],
    'PIPELINE_CSS': {
        'test': {
            'source_filenames': ["style.css"],
            'output_filename': "style.2.css",
        }
    },
    'PIPELINE_JS': {
        'test': {
            'source_filenames': ['script.js'],
            'output_filename': 'script.2.js',
        }
    },
    'JINJA2_CONSTANTS': {"foo": "bar"},
    'JINJA2_MUTE_URLRESOLVE_EXCEPTIONS': True,
}

if django.VERSION[:2] >= (1, 6):
    test_settings["TEST_RUNNER"] = "django.test.runner.DiscoverRunner"


if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    if not settings.configured:
        settings.configure(**test_settings)

    args = sys.argv
    args.insert(1, "test")

    if django.VERSION[:2] < (1, 6):
        args.insert(2, "django_jinja_test")

    execute_from_command_line(args)

########NEW FILE########
