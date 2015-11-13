__FILENAME__ = base
from __future__ import with_statement, unicode_literals
import os
import codecs

from django.core.files.base import ContentFile
from django.template import Context
from django.template.loader import render_to_string
from django.utils.importlib import import_module
from django.utils.safestring import mark_safe

try:
    from urllib.request import url2pathname
except ImportError:
    from urllib import url2pathname

from compressor.cache import get_hexdigest, get_mtime
from compressor.conf import settings
from compressor.exceptions import (CompressorError, UncompressableFileError,
        FilterDoesNotExist)
from compressor.filters import CompilerFilter
from compressor.storage import compressor_file_storage
from compressor.signals import post_compress
from compressor.utils import get_class, get_mod_func, staticfiles
from compressor.utils.decorators import cached_property

# Some constants for nicer handling.
SOURCE_HUNK, SOURCE_FILE = 'inline', 'file'
METHOD_INPUT, METHOD_OUTPUT = 'input', 'output'


class Compressor(object):
    """
    Base compressor object to be subclassed for content type
    depending implementations details.
    """
    type = None

    def __init__(self, content=None, output_prefix=None, context=None, *args, **kwargs):
        self.content = content or ""  # rendered contents of {% compress %} tag
        self.output_prefix = output_prefix or "compressed"
        self.output_dir = settings.COMPRESS_OUTPUT_DIR.strip('/')
        self.charset = settings.DEFAULT_CHARSET
        self.split_content = []
        self.context = context or {}
        self.extra_context = {}
        self.all_mimetypes = dict(settings.COMPRESS_PRECOMPILERS)
        self.finders = staticfiles.finders
        self._storage = None

    @cached_property
    def storage(self):
        from compressor.storage import default_storage
        return default_storage

    def split_contents(self):
        """
        To be implemented in a subclass, should return an
        iterable with four values: kind, value, basename, element
        """
        raise NotImplementedError

    def get_template_name(self, mode):
        """
        Returns the template path for the given mode.
        """
        try:
            template = getattr(self, "template_name_%s" % mode)
            if template:
                return template
        except AttributeError:
            pass
        return "compressor/%s_%s.html" % (self.type, mode)

    def get_basename(self, url):
        """
        Takes full path to a static file (eg. "/static/css/style.css") and
        returns path with storage's base url removed (eg. "css/style.css").
        """
        try:
            base_url = self.storage.base_url
        except AttributeError:
            base_url = settings.COMPRESS_URL
        if not url.startswith(base_url):
            raise UncompressableFileError("'%s' isn't accessible via "
                                          "COMPRESS_URL ('%s') and can't be "
                                          "compressed" % (url, base_url))
        basename = url.replace(base_url, "", 1)
        # drop the querystring, which is used for non-compressed cache-busting.
        return basename.split("?", 1)[0]

    def get_filepath(self, content, basename=None):
        """
        Returns file path for an output file based on contents.

        Returned path is relative to compressor storage's base url, for
        example "CACHE/css/e41ba2cc6982.css".

        When `basename` argument is provided then file name (without extension)
        will be used as a part of returned file name, for example:

        get_filepath(content, "my_file.css") -> 'CACHE/css/my_file.e41ba2cc6982.css'
        """
        parts = []
        if basename:
            filename = os.path.split(basename)[1]
            parts.append(os.path.splitext(filename)[0])
        parts.extend([get_hexdigest(content, 12), self.type])
        return os.path.join(self.output_dir, self.output_prefix, '.'.join(parts))

    def get_filename(self, basename):
        """
        Returns full path to a file, for example:

        get_filename('css/one.css') -> '/full/path/to/static/css/one.css'
        """
        filename = None
        # first try finding the file in the root
        try:
            # call path first so remote storages don't make it to exists,
            # which would cause network I/O
            filename = self.storage.path(basename)
            if not self.storage.exists(basename):
                filename = None
        except NotImplementedError:
            # remote storages don't implement path, access the file locally
            if compressor_file_storage.exists(basename):
                filename = compressor_file_storage.path(basename)
        # secondly try to find it with staticfiles (in debug mode)
        if not filename and self.finders:
            filename = self.finders.find(url2pathname(basename))
        if filename:
            return filename
        # or just raise an exception as the last resort
        raise UncompressableFileError(
            "'%s' could not be found in the COMPRESS_ROOT '%s'%s" %
            (basename, settings.COMPRESS_ROOT,
             self.finders and " or with staticfiles." or "."))

    def get_filecontent(self, filename, charset):
        """
        Reads file contents using given `charset` and returns it as text.
        """
        with codecs.open(filename, 'r', charset) as fd:
            try:
                return fd.read()
            except IOError as e:
                raise UncompressableFileError("IOError while processing "
                                              "'%s': %s" % (filename, e))
            except UnicodeDecodeError as e:
                raise UncompressableFileError("UnicodeDecodeError while "
                                              "processing '%s' with "
                                              "charset %s: %s" %
                                              (filename, charset, e))

    @cached_property
    def parser(self):
        return get_class(settings.COMPRESS_PARSER)(self.content)

    @cached_property
    def cached_filters(self):
        return [get_class(filter_cls) for filter_cls in self.filters]

    @cached_property
    def mtimes(self):
        return [str(get_mtime(value))
                for kind, value, basename, elem in self.split_contents()
                if kind == SOURCE_FILE]

    @cached_property
    def cachekey(self):
        return get_hexdigest(''.join(
            [self.content] + self.mtimes).encode(self.charset), 12)

    def hunks(self, forced=False):
        """
        The heart of content parsing, iterates over the
        list of split contents and looks at its kind
        to decide what to do with it. Should yield a
        bunch of precompiled and/or rendered hunks.
        """
        enabled = settings.COMPRESS_ENABLED or forced

        for kind, value, basename, elem in self.split_contents():
            precompiled = False
            attribs = self.parser.elem_attribs(elem)
            charset = attribs.get("charset", self.charset)
            options = {
                'method': METHOD_INPUT,
                'elem': elem,
                'kind': kind,
                'basename': basename,
                'charset': charset,
            }

            if kind == SOURCE_FILE:
                options = dict(options, filename=value)
                value = self.get_filecontent(value, charset)

            if self.all_mimetypes:
                precompiled, value = self.precompile(value, **options)

            if enabled:
                yield self.filter(value, **options)
            else:
                if precompiled:
                    yield self.handle_output(kind, value, forced=True,
                                             basename=basename)
                else:
                    yield self.parser.elem_str(elem)

    def filter_output(self, content):
        """
        Passes the concatenated content to the 'output' methods
        of the compressor filters.
        """
        return self.filter(content, method=METHOD_OUTPUT)

    def filter_input(self, forced=False):
        """
        Passes each hunk (file or code) to the 'input' methods
        of the compressor filters.
        """
        content = []
        for hunk in self.hunks(forced):
            content.append(hunk)
        return content

    def precompile(self, content, kind=None, elem=None, filename=None,
                   charset=None, **kwargs):
        """
        Processes file using a pre compiler.

        This is the place where files like coffee script are processed.
        """
        if not kind:
            return False, content
        attrs = self.parser.elem_attribs(elem)
        mimetype = attrs.get("type", None)
        if mimetype:
            filter_or_command = self.all_mimetypes.get(mimetype)
            if filter_or_command is None:
                if mimetype not in ("text/css", "text/javascript"):
                    raise CompressorError("Couldn't find any precompiler in "
                                          "COMPRESS_PRECOMPILERS setting for "
                                          "mimetype '%s'." % mimetype)
            else:
                mod_name, cls_name = get_mod_func(filter_or_command)
                try:
                    mod = import_module(mod_name)
                except ImportError:
                    filter = CompilerFilter(
                        content, filter_type=self.type, filename=filename,
                        charset=charset, command=filter_or_command)
                    return True, filter.input(**kwargs)
                try:
                    precompiler_class = getattr(mod, cls_name)
                except AttributeError:
                    raise FilterDoesNotExist('Could not find "%s".' %
                            filter_or_command)
                else:
                    filter = precompiler_class(
                        content, attrs, filter_type=self.type, charset=charset,
                        filename=filename)
                    return True, filter.input(**kwargs)

        return False, content

    def filter(self, content, method, **kwargs):
        for filter_cls in self.cached_filters:
            filter_func = getattr(
                filter_cls(content, filter_type=self.type), method)
            try:
                if callable(filter_func):
                    content = filter_func(**kwargs)
            except NotImplementedError:
                pass
        return content

    def output(self, mode='file', forced=False):
        """
        The general output method, override in subclass if you need to do
        any custom modification. Calls other mode specific methods or simply
        returns the content directly.
        """
        output = '\n'.join(self.filter_input(forced))

        if not output:
            return ''

        if settings.COMPRESS_ENABLED or forced:
            filtered_output = self.filter_output(output)
            return self.handle_output(mode, filtered_output, forced)

        return output

    def handle_output(self, mode, content, forced, basename=None):
        # Then check for the appropriate output method and call it
        output_func = getattr(self, "output_%s" % mode, None)
        if callable(output_func):
            return output_func(mode, content, forced, basename)
        # Total failure, raise a general exception
        raise CompressorError(
            "Couldn't find output method for mode '%s'" % mode)

    def output_file(self, mode, content, forced=False, basename=None):
        """
        The output method that saves the content to a file and renders
        the appropriate template with the file's URL.
        """
        new_filepath = self.get_filepath(content, basename=basename)
        if not self.storage.exists(new_filepath) or forced:
            self.storage.save(new_filepath, ContentFile(content.encode(self.charset)))
        url = mark_safe(self.storage.url(new_filepath))
        return self.render_output(mode, {"url": url})

    def output_inline(self, mode, content, forced=False, basename=None):
        """
        The output method that directly returns the content for inline
        display.
        """
        return self.render_output(mode, {"content": content})

    def render_output(self, mode, context=None):
        """
        Renders the compressor output with the appropriate template for
        the given mode and template context.
        """
        # Just in case someone renders the compressor outside
        # the usual template rendering cycle
        if 'compressed' not in self.context:
            self.context['compressed'] = {}

        self.context['compressed'].update(context or {})
        self.context['compressed'].update(self.extra_context)
        final_context = Context(self.context)
        post_compress.send(sender=self.__class__, type=self.type,
                           mode=mode, context=final_context)
        template_name = self.get_template_name(mode)
        return render_to_string(template_name, context_instance=final_context)

########NEW FILE########
__FILENAME__ = cache
import json
import hashlib
import os
import socket
import time

from django.core.cache import get_cache
from django.core.files.base import ContentFile
from django.utils.encoding import force_text, smart_bytes
from django.utils.functional import SimpleLazyObject
from django.utils.importlib import import_module

from compressor.conf import settings
from compressor.storage import default_storage
from compressor.utils import get_mod_func

_cachekey_func = None


def get_hexdigest(plaintext, length=None):
    digest = hashlib.md5(smart_bytes(plaintext)).hexdigest()
    if length:
        return digest[:length]
    return digest


def simple_cachekey(key):
    return 'django_compressor.%s' % force_text(key)


def socket_cachekey(key):
    return 'django_compressor.%s.%s' % (socket.gethostname(), force_text(key))


def get_cachekey(*args, **kwargs):
    global _cachekey_func
    if _cachekey_func is None:
        try:
            mod_name, func_name = get_mod_func(
                settings.COMPRESS_CACHE_KEY_FUNCTION)
            _cachekey_func = getattr(import_module(mod_name), func_name)
        except (AttributeError, ImportError) as e:
            raise ImportError("Couldn't import cache key function %s: %s" %
                              (settings.COMPRESS_CACHE_KEY_FUNCTION, e))
    return _cachekey_func(*args, **kwargs)


def get_mtime_cachekey(filename):
    return get_cachekey("mtime.%s" % get_hexdigest(filename))


def get_offline_hexdigest(render_template_string):
    return get_hexdigest(render_template_string)


def get_offline_cachekey(source):
    return get_cachekey("offline.%s" % get_offline_hexdigest(source))


def get_offline_manifest_filename():
    output_dir = settings.COMPRESS_OUTPUT_DIR.strip('/')
    return os.path.join(output_dir, settings.COMPRESS_OFFLINE_MANIFEST)


_offline_manifest = None


def get_offline_manifest():
    global _offline_manifest
    if _offline_manifest is None:
        filename = get_offline_manifest_filename()
        if default_storage.exists(filename):
            with default_storage.open(filename) as fp:
                _offline_manifest = json.loads(fp.read().decode('utf8'))
        else:
            _offline_manifest = {}
    return _offline_manifest


def flush_offline_manifest():
    global _offline_manifest
    _offline_manifest = None


def write_offline_manifest(manifest):
    filename = get_offline_manifest_filename()
    content = json.dumps(manifest, indent=2).encode('utf8')
    default_storage.save(filename, ContentFile(content))
    flush_offline_manifest()


def get_templatetag_cachekey(compressor, mode, kind):
    return get_cachekey(
        "templatetag.%s.%s.%s" % (compressor.cachekey, mode, kind))


def get_mtime(filename):
    if settings.COMPRESS_MTIME_DELAY:
        key = get_mtime_cachekey(filename)
        mtime = cache.get(key)
        if mtime is None:
            mtime = os.path.getmtime(filename)
            cache.set(key, mtime, settings.COMPRESS_MTIME_DELAY)
        return mtime
    return os.path.getmtime(filename)


def get_hashed_mtime(filename, length=12):
    try:
        filename = os.path.realpath(filename)
        mtime = str(int(get_mtime(filename)))
    except OSError:
        return None
    return get_hexdigest(mtime, length)


def get_hashed_content(filename, length=12):
    try:
        filename = os.path.realpath(filename)
    except OSError:
        return None

    # should we make sure that file is utf-8 encoded?
    with open(filename, 'rb') as file:
        return get_hexdigest(file.read(), length)


def cache_get(key):
    packed_val = cache.get(key)
    if packed_val is None:
        return None
    val, refresh_time, refreshed = packed_val
    if (time.time() > refresh_time) and not refreshed:
        # Store the stale value while the cache
        # revalidates for another MINT_DELAY seconds.
        cache_set(key, val, refreshed=True,
            timeout=settings.COMPRESS_MINT_DELAY)
        return None
    return val


def cache_set(key, val, refreshed=False, timeout=None):
    if timeout is None:
        timeout = settings.COMPRESS_REBUILD_TIMEOUT
    refresh_time = timeout + time.time()
    real_timeout = timeout + settings.COMPRESS_MINT_DELAY
    packed_val = (val, refresh_time, refreshed)
    return cache.set(key, packed_val, real_timeout)


cache = SimpleLazyObject(lambda: get_cache(settings.COMPRESS_CACHE_BACKEND))

########NEW FILE########
__FILENAME__ = conf
from __future__ import unicode_literals
import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from appconf import AppConf


class CompressorConf(AppConf):
    # Main switch
    ENABLED = not settings.DEBUG
    # Allows changing verbosity from the settings.
    VERBOSE = False
    # GET variable that disables compressor e.g. "nocompress"
    DEBUG_TOGGLE = None
    # the backend to use when parsing the JavaScript or Stylesheet files
    PARSER = 'compressor.parser.AutoSelectParser'
    OUTPUT_DIR = 'CACHE'
    STORAGE = 'compressor.storage.CompressorFileStorage'

    CSS_COMPRESSOR = 'compressor.css.CssCompressor'
    JS_COMPRESSOR = 'compressor.js.JsCompressor'

    URL = None
    ROOT = None

    CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter']
    CSS_HASHING_METHOD = 'mtime'

    JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
    PRECOMPILERS = (
        # ('text/coffeescript', 'coffee --compile --stdio'),
        # ('text/less', 'lessc {infile} {outfile}'),
        # ('text/x-sass', 'sass {infile} {outfile}'),
        # ('text/stylus', 'stylus < {infile} > {outfile}'),
        # ('text/x-scss', 'sass --scss {infile} {outfile}'),
    )
    CLOSURE_COMPILER_BINARY = 'java -jar compiler.jar'
    CLOSURE_COMPILER_ARGUMENTS = ''
    CSSTIDY_BINARY = 'csstidy'
    CSSTIDY_ARGUMENTS = '--template=highest'
    YUI_BINARY = 'java -jar yuicompressor.jar'
    YUI_CSS_ARGUMENTS = ''
    YUI_JS_ARGUMENTS = ''
    YUGLIFY_BINARY = 'yuglify'
    YUGLIFY_CSS_ARGUMENTS = '--terminal'
    YUGLIFY_JS_ARGUMENTS = '--terminal'
    DATA_URI_MAX_SIZE = 1024

    # the cache backend to use
    CACHE_BACKEND = None
    # the dotted path to the function that creates the cache key
    CACHE_KEY_FUNCTION = 'compressor.cache.simple_cachekey'
    # rebuilds the cache every 30 days if nothing has changed.
    REBUILD_TIMEOUT = 60 * 60 * 24 * 30  # 30 days
    # the upper bound on how long any compression should take to be generated
    # (used against dog piling, should be a lot smaller than REBUILD_TIMEOUT
    MINT_DELAY = 30  # seconds
    # check for file changes only after a delay
    MTIME_DELAY = 10  # seconds
    # enables the offline cache -- also filled by the compress command
    OFFLINE = False
    # invalidates the offline cache after one year
    OFFLINE_TIMEOUT = 60 * 60 * 24 * 365  # 1 year
    # The context to be used when compressing the files "offline"
    OFFLINE_CONTEXT = {}
    # The name of the manifest file (e.g. filename.ext)
    OFFLINE_MANIFEST = 'manifest.json'
    # The Context to be used when TemplateFilter is used
    TEMPLATE_FILTER_CONTEXT = {}
    # Function that returns the Jinja2 environment to use in offline compression.
    def JINJA2_GET_ENVIRONMENT():
        try:
            import jinja2
            return jinja2.Environment()
        except ImportError:
            return None

    class Meta:
        prefix = 'compress'

    def configure_root(self, value):
        # Uses Django's STATIC_ROOT by default
        if value is None:
            value = settings.STATIC_ROOT
        if value is None:
            raise ImproperlyConfigured('COMPRESS_ROOT defaults to ' +
                                       'STATIC_ROOT, please define either')
        return os.path.normcase(os.path.abspath(value))

    def configure_url(self, value):
        # Uses Django's STATIC_URL by default
        if value is None:
            value = settings.STATIC_URL
        if not value.endswith('/'):
            raise ImproperlyConfigured("URL settings (e.g. COMPRESS_URL) "
                                       "must have a trailing slash")
        return value

    def configure_cache_backend(self, value):
        if value is None:
            value = 'default'
        return value

    def configure_offline_context(self, value):
        if not value:
            value = {'STATIC_URL': settings.STATIC_URL}
        return value

    def configure_template_filter_context(self, value):
        if not value:
            value = {'STATIC_URL': settings.STATIC_URL}
        return value

    def configure_precompilers(self, value):
        if not isinstance(value, (list, tuple)):
            raise ImproperlyConfigured("The COMPRESS_PRECOMPILERS setting "
                                       "must be a list or tuple. Check for "
                                       "missing commas.")
        return value

########NEW FILE########
__FILENAME__ = jinja2ext
from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.exceptions import TemplateSyntaxError

from compressor.templatetags.compress import OUTPUT_FILE, CompressorMixin


class CompressorExtension(CompressorMixin, Extension):

    tags = set(['compress'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        kindarg = parser.parse_expression()
        # Allow kind to be defined as jinja2 name node
        if isinstance(kindarg, nodes.Name):
            kindarg = nodes.Const(kindarg.name)
        args = [kindarg]
        if args[0].value not in self.compressors:
            raise TemplateSyntaxError('compress kind may be one of: %s' %
                                      (', '.join(self.compressors.keys())),
                                      lineno)
        if parser.stream.skip_if('comma'):
            modearg = parser.parse_expression()
            # Allow mode to be defined as jinja2 name node
            if isinstance(modearg, nodes.Name):
                modearg = nodes.Const(modearg.name)
                args.append(modearg)
        else:
            args.append(nodes.Const('file'))

        body = parser.parse_statements(['name:endcompress'], drop_needle=True)

        # Skip the kind if used in the endblock, by using the kind in the
        # endblock the templates are slightly more readable.
        parser.stream.skip_if('name:' + kindarg.value)
        return nodes.CallBlock(self.call_method('_compress_normal', args), [], [],
            body).set_lineno(lineno)

    def _compress_forced(self, kind, mode, caller):
        return self._compress(kind, mode, caller, True)

    def _compress_normal(self, kind, mode, caller):
        return self._compress(kind, mode, caller, False)

    def _compress(self, kind, mode, caller, forced):
        mode = mode or OUTPUT_FILE
        original_content = caller()
        context = {
            'original_content': original_content
        }
        return self.render_compressed(context, kind, mode, forced=forced)

    def get_original_content(self, context):
        return context['original_content']

########NEW FILE########
__FILENAME__ = sekizai
"""
 source: https://gist.github.com/1311010
 Get django-sekizai, django-compessor (and django-cms) playing nicely together
 re: https://github.com/ojii/django-sekizai/issues/4
 using: https://github.com/django-compressor/django-compressor.git
 and: https://github.com/ojii/django-sekizai.git@0.6 or later
"""
from compressor.templatetags.compress import CompressorNode
from django.template.base import Template


def compress(context, data, name):
    """
    Data is the string from the template (the list of js files in this case)
    Name is either 'js' or 'css' (the sekizai namespace)
    Basically passes the string through the {% compress 'js' %} template tag
    """
    return CompressorNode(nodelist=Template(data).nodelist, kind=name, mode='file').render(context=context)

########NEW FILE########
__FILENAME__ = css
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE
from compressor.conf import settings


class CssCompressor(Compressor):

    def __init__(self, content=None, output_prefix="css", context=None):
        super(CssCompressor, self).__init__(content=content,
            output_prefix=output_prefix, context=context)
        self.filters = list(settings.COMPRESS_CSS_FILTERS)
        self.type = output_prefix

    def split_contents(self):
        if self.split_content:
            return self.split_content
        self.media_nodes = []
        for elem in self.parser.css_elems():
            data = None
            elem_name = self.parser.elem_name(elem)
            elem_attribs = self.parser.elem_attribs(elem)
            if elem_name == 'link' and elem_attribs['rel'].lower() == 'stylesheet':
                basename = self.get_basename(elem_attribs['href'])
                filename = self.get_filename(basename)
                data = (SOURCE_FILE, filename, basename, elem)
            elif elem_name == 'style':
                data = (SOURCE_HUNK, self.parser.elem_content(elem), None, elem)
            if data:
                self.split_content.append(data)
                media = elem_attribs.get('media', None)
                # Append to the previous node if it had the same media type
                append_to_previous = self.media_nodes and self.media_nodes[-1][0] == media
                # and we are not just precompiling, otherwise create a new node.
                if append_to_previous and settings.COMPRESS_ENABLED:
                    self.media_nodes[-1][1].split_content.append(data)
                else:
                    node = self.__class__(content=self.parser.elem_str(elem),
                                         context=self.context)
                    node.split_content.append(data)
                    self.media_nodes.append((media, node))
        return self.split_content

    def output(self, *args, **kwargs):
        if (settings.COMPRESS_ENABLED or settings.COMPRESS_PRECOMPILERS or
                kwargs.get('forced', False)):
            # Populate self.split_content
            self.split_contents()
            if hasattr(self, 'media_nodes'):
                ret = []
                for media, subnode in self.media_nodes:
                    subnode.extra_context.update({'media': media})
                    ret.append(subnode.output(*args, **kwargs))
                return ''.join(ret)
        return super(CssCompressor, self).output(*args, **kwargs)

########NEW FILE########
__FILENAME__ = exceptions
class CompressorError(Exception):
    """
    A general error of the compressor
    """
    pass


class UncompressableFileError(Exception):
    """
    This exception is raised when a file cannot be compressed
    """
    pass


class FilterError(Exception):
    """
    This exception is raised when a filter fails
    """
    pass


class ParserError(Exception):
    """
    This exception is raised when the parser fails
    """
    pass


class OfflineGenerationError(Exception):
    """
    Offline compression generation related exceptions
    """
    pass


class FilterDoesNotExist(Exception):
    """
    Raised when a filter class cannot be found.
    """
    pass


class TemplateDoesNotExist(Exception):
    """
    This exception is raised when a template does not exist.
    """
    pass


class TemplateSyntaxError(Exception):
    """
    This exception is raised when a template syntax error is encountered.
    """
    pass

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import, unicode_literals
import io
import logging
import subprocess

from django.core.exceptions import ImproperlyConfigured
from django.core.files.temp import NamedTemporaryFile
from django.utils.importlib import import_module
from django.utils.encoding import smart_text
from django.utils import six

from compressor.conf import settings
from compressor.exceptions import FilterError
from compressor.utils import get_mod_func


logger = logging.getLogger("compressor.filters")


class FilterBase(object):
    """
    A base class for filters that does nothing.

    Subclasses should implement `input` and/or `output` methods which must
    return a string (unicode under python 2) or raise a NotImplementedError.
    """
    def __init__(self, content, filter_type=None, filename=None, verbose=0,
                 charset=None):
        self.type = filter_type or getattr(self, 'type', None)
        self.content = content
        self.verbose = verbose or settings.COMPRESS_VERBOSE
        self.logger = logger
        self.filename = filename
        self.charset = charset

    def input(self, **kwargs):
        raise NotImplementedError

    def output(self, **kwargs):
        raise NotImplementedError


class CallbackOutputFilter(FilterBase):
    """
    A filter which takes function path in `callback` attribute, imports it
    and uses that function to filter output string::

        class MyFilter(CallbackOutputFilter):
            callback = 'path.to.my.callback'

    Callback should be a function which takes a string as first argument and
    returns a string (unicode under python 2).
    """
    callback = None
    args = []
    kwargs = {}
    dependencies = []

    def __init__(self, *args, **kwargs):
        super(CallbackOutputFilter, self).__init__(*args, **kwargs)
        if self.callback is None:
            raise ImproperlyConfigured(
                "The callback filter %s must define a 'callback' attribute." %
                self.__class__.__name__)
        try:
            mod_name, func_name = get_mod_func(self.callback)
            func = getattr(import_module(mod_name), func_name)
        except ImportError:
            if self.dependencies:
                if len(self.dependencies) == 1:
                    warning = "dependency (%s) is" % self.dependencies[0]
                else:
                    warning = ("dependencies (%s) are" %
                               ", ".join([dep for dep in self.dependencies]))
            else:
                warning = ""
            raise ImproperlyConfigured(
                "The callback %s couldn't be imported. Make sure the %s "
                "correctly installed." % (self.callback, warning))
        except AttributeError as e:
            raise ImproperlyConfigured("An error occurred while importing the "
                                       "callback filter %s: %s" % (self, e))
        else:
            self._callback_func = func

    def output(self, **kwargs):
        ret = self._callback_func(self.content, *self.args, **self.kwargs)
        assert isinstance(ret, six.text_type)
        return ret


class CompilerFilter(FilterBase):
    """
    A filter subclass that is able to filter content via
    external commands.
    """
    command = None
    options = ()
    default_encoding = settings.FILE_CHARSET

    def __init__(self, content, command=None, *args, **kwargs):
        super(CompilerFilter, self).__init__(content, *args, **kwargs)
        self.cwd = None

        if command:
            self.command = command
        if self.command is None:
            raise FilterError("Required attribute 'command' not given")

        if isinstance(self.options, dict):
            # turn dict into a tuple
            new_options = ()
            for item in kwargs.items():
                new_options += (item,)
            self.options = new_options

        # append kwargs to self.options
        for item in kwargs.items():
            self.options += (item,)

        self.stdout = self.stdin = self.stderr = subprocess.PIPE
        self.infile = self.outfile = None

    def input(self, **kwargs):
        encoding = self.default_encoding
        options = dict(self.options)

        if self.infile is None and "{infile}" in self.command:
            # create temporary input file if needed
            if self.filename is None:
                self.infile = NamedTemporaryFile(mode='wb')
                self.infile.write(self.content.encode(encoding))
                self.infile.flush()
                options["infile"] = self.infile.name
            else:
                # we use source file directly, which may be encoded using
                # something different than utf8. If that's the case file will
                # be included with charset="something" html attribute and
                # charset will be available as filter's charset attribute
                encoding = self.charset  # or self.default_encoding
                self.infile = open(self.filename)
                options["infile"] = self.filename

        if "{outfile}" in self.command and "outfile" not in options:
            # create temporary output file if needed
            ext = self.type and ".%s" % self.type or ""
            self.outfile = NamedTemporaryFile(mode='r+', suffix=ext)
            options["outfile"] = self.outfile.name

        try:
            command = self.command.format(**options)
            proc = subprocess.Popen(
                command, shell=True, cwd=self.cwd, stdout=self.stdout,
                stdin=self.stdin, stderr=self.stderr)
            if self.infile is None:
                # if infile is None then send content to process' stdin
                filtered, err = proc.communicate(
                    self.content.encode(encoding))
            else:
                filtered, err = proc.communicate()
            filtered, err = filtered.decode(encoding), err.decode(encoding)
        except (IOError, OSError) as e:
            raise FilterError('Unable to apply %s (%r): %s' %
                              (self.__class__.__name__, self.command, e))
        else:
            if proc.wait() != 0:
                # command failed, raise FilterError exception
                if not err:
                    err = ('Unable to apply %s (%s)' %
                           (self.__class__.__name__, self.command))
                    if filtered:
                        err += '\n%s' % filtered
                raise FilterError(err)

            if self.verbose:
                self.logger.debug(err)

            outfile_path = options.get('outfile')
            if outfile_path:
                with io.open(outfile_path, 'r', encoding=encoding) as file:
                    filtered = file.read()
        finally:
            if self.infile is not None:
                self.infile.close()
            if self.outfile is not None:
                self.outfile.close()

        return smart_text(filtered)

########NEW FILE########
__FILENAME__ = closure
from compressor.conf import settings
from compressor.filters import CompilerFilter


class ClosureCompilerFilter(CompilerFilter):
    command = "{binary} {args}"
    options = (
        ("binary", settings.COMPRESS_CLOSURE_COMPILER_BINARY),
        ("args", settings.COMPRESS_CLOSURE_COMPILER_ARGUMENTS),
    )

########NEW FILE########
__FILENAME__ = cssmin
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# `cssmin.py` - A Python port of the YUI CSS compressor.
#
# Copyright (c) 2010 Zachary Voase
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""`cssmin` - A Python port of the YUI CSS compressor."""

import re

__version__ = '0.1.4'


def remove_comments(css):
    """Remove all CSS comment blocks."""

    iemac = False
    preserve = False
    comment_start = css.find("/*")
    while comment_start >= 0:
        # Preserve comments that look like `/*!...*/`.
        # Slicing is used to make sure we don"t get an IndexError.
        preserve = css[comment_start + 2:comment_start + 3] == "!"

        comment_end = css.find("*/", comment_start + 2)
        if comment_end < 0:
            if not preserve:
                css = css[:comment_start]
                break
        elif comment_end >= (comment_start + 2):
            if css[comment_end - 1] == "\\":
                # This is an IE Mac-specific comment; leave this one and the
                # following one alone.
                comment_start = comment_end + 2
                iemac = True
            elif iemac:
                comment_start = comment_end + 2
                iemac = False
            elif not preserve:
                css = css[:comment_start] + css[comment_end + 2:]
            else:
                comment_start = comment_end + 2
        comment_start = css.find("/*", comment_start)

    return css


def remove_unnecessary_whitespace(css):
    """Remove unnecessary whitespace characters."""

    def pseudoclasscolon(css):

        """
        Prevents 'p :link' from becoming 'p:link'.

        Translates 'p :link' into 'p ___PSEUDOCLASSCOLON___link'; this is
        translated back again later.
        """

        regex = re.compile(r"(^|\})(([^\{\:])+\:)+([^\{]*\{)")
        match = regex.search(css)
        while match:
            css = ''.join([
                css[:match.start()],
                match.group().replace(":", "___PSEUDOCLASSCOLON___"),
                css[match.end():]])
            match = regex.search(css)
        return css

    css = pseudoclasscolon(css)
    # Remove spaces from before things.
    css = re.sub(r"\s+([!{};:>+\(\)\],])", r"\1", css)

    # If there is a `@charset`, then only allow one, and move to the beginning.
    css = re.sub(r"^(.*)(@charset \"[^\"]*\";)", r"\2\1", css)
    css = re.sub(r"^(\s*@charset [^;]+;\s*)+", r"\1", css)

    # Put the space back in for a few cases, such as `@media screen` and
    # `(-webkit-min-device-pixel-ratio:0)`.
    css = re.sub(r"\band\(", "and (", css)

    # Put the colons back.
    css = css.replace('___PSEUDOCLASSCOLON___', ':')

    # Remove spaces from after things.
    css = re.sub(r"([!{}:;>+\(\[,])\s+", r"\1", css)

    return css


def remove_unnecessary_semicolons(css):
    """Remove unnecessary semicolons."""

    return re.sub(r";+\}", "}", css)


def remove_empty_rules(css):
    """Remove empty rules."""

    return re.sub(r"[^\}\{]+\{\}", "", css)


def normalize_rgb_colors_to_hex(css):
    """Convert `rgb(51,102,153)` to `#336699`."""

    regex = re.compile(r"rgb\s*\(\s*([0-9,\s]+)\s*\)")
    match = regex.search(css)
    while match:
        colors = map(lambda s: s.strip(), match.group(1).split(","))
        hexcolor = '#%.2x%.2x%.2x' % tuple(map(int, colors))
        css = css.replace(match.group(), hexcolor)
        match = regex.search(css)
    return css


def condense_zero_units(css):
    """Replace `0(px, em, %, etc)` with `0`."""

    return re.sub(r"([\s:])(0)(px|em|%|in|cm|mm|pc|pt|ex)", r"\1\2", css)


def condense_multidimensional_zeros(css):
    """Replace `:0 0 0 0;`, `:0 0 0;` etc. with `:0;`."""

    css = css.replace(":0 0 0 0;", ":0;")
    css = css.replace(":0 0 0;", ":0;")
    css = css.replace(":0 0;", ":0;")

    # Revert `background-position:0;` to the valid `background-position:0 0;`.
    css = css.replace("background-position:0;", "background-position:0 0;")

    return css


def condense_floating_points(css):
    """Replace `0.6` with `.6` where possible."""

    return re.sub(r"(:|\s)0+\.(\d+)", r"\1.\2", css)


def condense_hex_colors(css):
    """Shorten colors from #AABBCC to #ABC where possible."""

    regex = re.compile(r"([^\"'=\s])(\s*)#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])")
    match = regex.search(css)
    while match:
        first = match.group(3) + match.group(5) + match.group(7)
        second = match.group(4) + match.group(6) + match.group(8)
        if first.lower() == second.lower():
            css = css.replace(match.group(), match.group(1) + match.group(2) + '#' + first)
            match = regex.search(css, match.end() - 3)
        else:
            match = regex.search(css, match.end())
    return css


def condense_whitespace(css):
    """Condense multiple adjacent whitespace characters into one."""

    return re.sub(r"\s+", " ", css)


def condense_semicolons(css):
    """Condense multiple adjacent semicolon characters into one."""

    return re.sub(r";;+", ";", css)


def wrap_css_lines(css, line_length):
    """Wrap the lines of the given CSS to an approximate length."""

    lines = []
    line_start = 0
    for i, char in enumerate(css):
        # It's safe to break after `}` characters.
        if char == '}' and (i - line_start >= line_length):
            lines.append(css[line_start:i + 1])
            line_start = i + 1

    if line_start < len(css):
        lines.append(css[line_start:])
    return '\n'.join(lines)


def cssmin(css, wrap=None):
    css = remove_comments(css)
    css = condense_whitespace(css)
    # A pseudo class for the Box Model Hack
    # (see http://tantek.com/CSS/Examples/boxmodelhack.html)
    css = css.replace('"\\"}\\""', "___PSEUDOCLASSBMH___")
    css = remove_unnecessary_whitespace(css)
    css = remove_unnecessary_semicolons(css)
    css = condense_zero_units(css)
    css = condense_multidimensional_zeros(css)
    css = condense_floating_points(css)
    css = normalize_rgb_colors_to_hex(css)
    css = condense_hex_colors(css)
    if wrap is not None:
        css = wrap_css_lines(css, wrap)
    css = css.replace("___PSEUDOCLASSBMH___", '"\\"}\\""')
    css = condense_semicolons(css)
    return css.strip()


def main():
    import optparse
    import sys

    p = optparse.OptionParser(
        prog="cssmin", version=__version__,
        usage="%prog [--wrap N]",
        description="""Reads raw CSS from stdin, and writes compressed CSS to stdout.""")

    p.add_option(
        '-w', '--wrap', type='int', default=None, metavar='N',
        help="Wrap output to approximately N chars per line.")

    options, args = p.parse_args()
    sys.stdout.write(cssmin(sys.stdin.read(), wrap=options.wrap))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = rcssmin
#!/usr/bin/env python
# -*- coding: ascii -*-
#
# Copyright 2011, 2012
# Andr\xe9 Malo or his licensors, as applicable
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""
==============
 CSS Minifier
==============

CSS Minifier.

The minifier is based on the semantics of the `YUI compressor`_\, which itself
is based on `the rule list by Isaac Schlueter`_\.

This module is a re-implementation aiming for speed instead of maximum
compression, so it can be used at runtime (rather than during a preprocessing
step). RCSSmin does syntactical compression only (removing spaces, comments
and possibly semicolons). It does not provide semantic compression (like
removing empty blocks, collapsing redundant properties etc). It does, however,
support various CSS hacks (by keeping them working as intended).

Here's a feature list:

- Strings are kept, except that escaped newlines are stripped
- Space/Comments before the very end or before various characters are
  stripped: ``:{});=>+],!`` (The colon (``:``) is a special case, a single
  space is kept if it's outside a ruleset.)
- Space/Comments at the very beginning or after various characters are
  stripped: ``{}(=:>+[,!``
- Optional space after unicode escapes is kept, resp. replaced by a simple
  space
- whitespaces inside ``url()`` definitions are stripped
- Comments starting with an exclamation mark (``!``) can be kept optionally.
- All other comments and/or whitespace characters are replaced by a single
  space.
- Multiple consecutive semicolons are reduced to one
- The last semicolon within a ruleset is stripped
- CSS Hacks supported:

  - IE7 hack (``>/**/``)
  - Mac-IE5 hack (``/*\*/.../**/``)
  - The boxmodelhack is supported naturally because it relies on valid CSS2
    strings
  - Between ``:first-line`` and the following comma or curly brace a space is
    inserted. (apparently it's needed for IE6)
  - Same for ``:first-letter``

rcssmin.c is a reimplementation of rcssmin.py in C and improves runtime up to
factor 50 or so (depending on the input).

Both python 2 (>= 2.4) and python 3 are supported.

.. _YUI compressor: https://github.com/yui/yuicompressor/

.. _the rule list by Isaac Schlueter: https://github.com/isaacs/cssmin/tree/
"""
__author__ = "Andr\xe9 Malo"
__author__ = getattr(__author__, 'decode', lambda x: __author__)('latin-1')
__docformat__ = "restructuredtext en"
__license__ = "Apache License, Version 2.0"
__version__ = '1.0.2'
__all__ = ['cssmin']

import re as _re


def _make_cssmin(python_only=False):
    """
    Generate CSS minifier.

    :Parameters:
      `python_only` : ``bool``
        Use only the python variant. If true, the c extension is not even
        tried to be loaded.

    :Return: Minifier
    :Rtype: ``callable``
    """
    # pylint: disable = W0612
    # ("unused" variables)

    # pylint: disable = R0911, R0912, R0914, R0915
    # (too many anything)

    if not python_only:
        try:
            import _rcssmin
        except ImportError:
            pass
        else:
            return _rcssmin.cssmin

    nl = r'(?:[\n\f]|\r\n?)' # pylint: disable = C0103
    spacechar = r'[\r\n\f\040\t]'

    unicoded = r'[0-9a-fA-F]{1,6}(?:[\040\n\t\f]|\r\n?)?'
    escaped = r'[^\n\r\f0-9a-fA-F]'
    escape = r'(?:\\(?:%(unicoded)s|%(escaped)s))' % locals()

    nmchar = r'[^\000-\054\056\057\072-\100\133-\136\140\173-\177]'
    # nmstart = r'[^\000-\100\133-\136\140\173-\177]'
    # ident = (r'(?:'
    #    r'-?(?:%(nmstart)s|%(escape)s)%(nmchar)s*(?:%(escape)s%(nmchar)s*)*'
    # r')') % locals()

    comment = r'(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)'

    # only for specific purposes. The bang is grouped:
    _bang_comment = r'(?:/\*(!?)[^*]*\*+(?:[^/*][^*]*\*+)*/)'

    string1 = \
        r'(?:\047[^\047\\\r\n\f]*(?:\\[^\r\n\f][^\047\\\r\n\f]*)*\047)'
    string2 = r'(?:"[^"\\\r\n\f]*(?:\\[^\r\n\f][^"\\\r\n\f]*)*")'
    strings = r'(?:%s|%s)' % (string1, string2)

    nl_string1 = \
        r'(?:\047[^\047\\\r\n\f]*(?:\\(?:[^\r]|\r\n?)[^\047\\\r\n\f]*)*\047)'
    nl_string2 = r'(?:"[^"\\\r\n\f]*(?:\\(?:[^\r]|\r\n?)[^"\\\r\n\f]*)*")'
    nl_strings = r'(?:%s|%s)' % (nl_string1, nl_string2)

    uri_nl_string1 = r'(?:\047[^\047\\]*(?:\\(?:[^\r]|\r\n?)[^\047\\]*)*\047)'
    uri_nl_string2 = r'(?:"[^"\\]*(?:\\(?:[^\r]|\r\n?)[^"\\]*)*")'
    uri_nl_strings = r'(?:%s|%s)' % (uri_nl_string1, uri_nl_string2)

    nl_escaped = r'(?:\\%(nl)s)' % locals()

    space = r'(?:%(spacechar)s|%(comment)s)' % locals()

    ie7hack = r'(?:>/\*\*/)'

    uri = (r'(?:'
        r'(?:[^\000-\040"\047()\\\177]*'
            r'(?:%(escape)s[^\000-\040"\047()\\\177]*)*)'
        r'(?:'
            r'(?:%(spacechar)s+|%(nl_escaped)s+)'
            r'(?:'
                r'(?:[^\000-\040"\047()\\\177]|%(escape)s|%(nl_escaped)s)'
                r'[^\000-\040"\047()\\\177]*'
                r'(?:%(escape)s[^\000-\040"\047()\\\177]*)*'
            r')+'
        r')*'
    r')') % locals()

    nl_unesc_sub = _re.compile(nl_escaped).sub

    uri_space_sub = _re.compile((
        r'(%(escape)s+)|%(spacechar)s+|%(nl_escaped)s+'
    ) % locals()).sub
    uri_space_subber = lambda m: m.groups()[0] or ''

    space_sub_simple = _re.compile((
        r'[\r\n\f\040\t;]+|(%(comment)s+)'
    ) % locals()).sub
    space_sub_banged = _re.compile((
        r'[\r\n\f\040\t;]+|(%(_bang_comment)s+)'
    ) % locals()).sub

    post_esc_sub = _re.compile(r'[\r\n\f\t]+').sub

    main_sub = _re.compile((
        r'([^\\"\047u>@\r\n\f\040\t/;:{}]+)'
        r'|(?<=[{}(=:>+[,!])(%(space)s+)'
        r'|^(%(space)s+)'
        r'|(%(space)s+)(?=(([:{});=>+\],!])|$)?)'
        r'|;(%(space)s*(?:;%(space)s*)*)(?=(\})?)'
        r'|(\{)'
        r'|(\})'
        r'|(%(strings)s)'
        r'|(?<!%(nmchar)s)url\(%(spacechar)s*('
                r'%(uri_nl_strings)s'
                r'|%(uri)s'
            r')%(spacechar)s*\)'
        r'|(@[mM][eE][dD][iI][aA])(?!%(nmchar)s)'
        r'|(%(ie7hack)s)(%(space)s*)'
        r'|(:[fF][iI][rR][sS][tT]-[lL]'
            r'(?:[iI][nN][eE]|[eE][tT][tT][eE][rR]))'
            r'(%(space)s*)(?=[{,])'
        r'|(%(nl_strings)s)'
        r'|(%(escape)s[^\\"\047u>@\r\n\f\040\t/;:{}]*)'
    ) % locals()).sub

    # print main_sub.__self__.pattern

    def main_subber(keep_bang_comments):
        """ Make main subber """
        in_macie5, in_rule, at_media = [0], [0], [0]

        if keep_bang_comments:
            space_sub = space_sub_banged
            def space_subber(match):
                """ Space|Comment subber """
                if match.lastindex:
                    group1, group2 = match.group(1, 2)
                    if group2:
                        if group1.endswith(r'\*/'):
                            in_macie5[0] = 1
                        else:
                            in_macie5[0] = 0
                        return group1
                    elif group1:
                        if group1.endswith(r'\*/'):
                            if in_macie5[0]:
                                return ''
                            in_macie5[0] = 1
                            return r'/*\*/'
                        elif in_macie5[0]:
                            in_macie5[0] = 0
                            return '/**/'
                return ''
        else:
            space_sub = space_sub_simple
            def space_subber(match):
                """ Space|Comment subber """
                if match.lastindex:
                    if match.group(1).endswith(r'\*/'):
                        if in_macie5[0]:
                            return ''
                        in_macie5[0] = 1
                        return r'/*\*/'
                    elif in_macie5[0]:
                        in_macie5[0] = 0
                        return '/**/'
                return ''

        def fn_space_post(group):
            """ space with token after """
            if group(5) is None or (
                    group(6) == ':' and not in_rule[0] and not at_media[0]):
                return ' ' + space_sub(space_subber, group(4))
            return space_sub(space_subber, group(4))

        def fn_semicolon(group):
            """ ; handler """
            return ';' + space_sub(space_subber, group(7))

        def fn_semicolon2(group):
            """ ; handler """
            if in_rule[0]:
                return space_sub(space_subber, group(7))
            return ';' + space_sub(space_subber, group(7))

        def fn_open(group):
            """ { handler """
            # pylint: disable = W0613
            if at_media[0]:
                at_media[0] -= 1
            else:
                in_rule[0] = 1
            return '{'

        def fn_close(group):
            """ } handler """
            # pylint: disable = W0613
            in_rule[0] = 0
            return '}'

        def fn_media(group):
            """ @media handler """
            at_media[0] += 1
            return group(13)

        def fn_ie7hack(group):
            """ IE7 Hack handler """
            if not in_rule[0] and not at_media[0]:
                in_macie5[0] = 0
                return group(14) + space_sub(space_subber, group(15))
            return '>' + space_sub(space_subber, group(15))

        table = (
            None,
            None,
            None,
            None,
            fn_space_post,                      # space with token after
            fn_space_post,                      # space with token after
            fn_space_post,                      # space with token after
            fn_semicolon,                       # semicolon
            fn_semicolon2,                      # semicolon
            fn_open,                            # {
            fn_close,                           # }
            lambda g: g(11),                    # string
            lambda g: 'url(%s)' % uri_space_sub(uri_space_subber, g(12)),
                                                # url(...)
            fn_media,                           # @media
            None,
            fn_ie7hack,                         # ie7hack
            None,
            lambda g: g(16) + ' ' + space_sub(space_subber, g(17)),
                                                # :first-line|letter followed
                                                # by [{,] (apparently space
                                                # needed for IE6)
            lambda g: nl_unesc_sub('', g(18)),  # nl_string
            lambda g: post_esc_sub(' ', g(19)), # escape
        )

        def func(match):
            """ Main subber """
            idx, group = match.lastindex, match.group
            if idx > 3:
                return table[idx](group)

            # shortcuts for frequent operations below:
            elif idx == 1:     # not interesting
                return group(1)
            # else: # space with token before or at the beginning
            return space_sub(space_subber, group(idx))

        return func

    def cssmin(style, keep_bang_comments=False): # pylint: disable = W0621
        """
        Minify CSS.

        :Parameters:
          `style` : ``str``
            CSS to minify

          `keep_bang_comments` : ``bool``
            Keep comments starting with an exclamation mark? (``/*!...*/``)

        :Return: Minified style
        :Rtype: ``str``
        """
        return main_sub(main_subber(keep_bang_comments), style)

    return cssmin

cssmin = _make_cssmin()


if __name__ == '__main__':
    def main():
        """ Main """
        import sys as _sys
        keep_bang_comments = (
            '-b' in _sys.argv[1:]
            or '-bp' in _sys.argv[1:]
            or '-pb' in _sys.argv[1:]
        )
        if '-p' in _sys.argv[1:] or '-bp' in _sys.argv[1:] \
                or '-pb' in _sys.argv[1:]:
            global cssmin # pylint: disable = W0603
            cssmin = _make_cssmin(python_only=True)
        _sys.stdout.write(cssmin(
            _sys.stdin.read(), keep_bang_comments=keep_bang_comments
        ))
    main()

########NEW FILE########
__FILENAME__ = csstidy
from compressor.conf import settings
from compressor.filters import CompilerFilter


class CSSTidyFilter(CompilerFilter):
    command = "{binary} {infile} {args} {outfile}"
    options = (
        ("binary", settings.COMPRESS_CSSTIDY_BINARY),
        ("args", settings.COMPRESS_CSSTIDY_ARGUMENTS),
    )

########NEW FILE########
__FILENAME__ = css_default
import os
import re
import posixpath

from compressor.cache import get_hashed_mtime, get_hashed_content
from compressor.conf import settings
from compressor.filters import FilterBase, FilterError
from compressor.utils import staticfiles

URL_PATTERN = re.compile(r'url\(([^\)]+)\)')
SRC_PATTERN = re.compile(r'src=([\'"])(.+?)\1')
SCHEMES = ('http://', 'https://', '/', 'data:')


class CssAbsoluteFilter(FilterBase):

    def __init__(self, *args, **kwargs):
        super(CssAbsoluteFilter, self).__init__(*args, **kwargs)
        self.root = settings.COMPRESS_ROOT
        self.url = settings.COMPRESS_URL.rstrip('/')
        self.url_path = self.url
        self.has_scheme = False

    def input(self, filename=None, basename=None, **kwargs):
        if filename is not None:
            filename = os.path.normcase(os.path.abspath(filename))
        if (not (filename and filename.startswith(self.root)) and
                not self.find(basename)):
            return self.content
        self.path = basename.replace(os.sep, '/')
        self.path = self.path.lstrip('/')
        if self.url.startswith(('http://', 'https://')):
            self.has_scheme = True
            parts = self.url.split('/')
            self.url = '/'.join(parts[2:])
            self.url_path = '/%s' % '/'.join(parts[3:])
            self.protocol = '%s/' % '/'.join(parts[:2])
            self.host = parts[2]
        self.directory_name = '/'.join((self.url, os.path.dirname(self.path)))
        return SRC_PATTERN.sub(self.src_converter,
            URL_PATTERN.sub(self.url_converter, self.content))

    def find(self, basename):
        if settings.DEBUG and basename and staticfiles.finders:
            return staticfiles.finders.find(basename)

    def guess_filename(self, url):
        local_path = url
        if self.has_scheme:
            # COMPRESS_URL had a protocol,
            # remove it and the hostname from our path.
            local_path = local_path.replace(self.protocol + self.host, "", 1)
        # remove url fragment, if any
        local_path = local_path.rsplit("#", 1)[0]
        # remove querystring, if any
        local_path = local_path.rsplit("?", 1)[0]
        # Now, we just need to check if we can find
        # the path from COMPRESS_URL in our url
        if local_path.startswith(self.url_path):
            local_path = local_path.replace(self.url_path, "", 1)
        # Re-build the local full path by adding root
        filename = os.path.join(self.root, local_path.lstrip('/'))
        return os.path.exists(filename) and filename

    def add_suffix(self, url):
        filename = self.guess_filename(url)
        suffix = None
        if filename:
            if settings.COMPRESS_CSS_HASHING_METHOD == "mtime":
                suffix = get_hashed_mtime(filename)
            elif settings.COMPRESS_CSS_HASHING_METHOD in ("hash", "content"):
                suffix = get_hashed_content(filename)
            elif settings.COMPRESS_CSS_HASHING_METHOD is None:
                suffix = None
            else:
                raise FilterError('COMPRESS_CSS_HASHING_METHOD is configured '
                                  'with an unknown method (%s).' %
                                  settings.COMPRESS_CSS_HASHING_METHOD)
        if suffix is None:
            return url
        if url.startswith(SCHEMES):
            fragment = None
            if "#" in url:
                url, fragment = url.rsplit("#", 1)
            if "?" in url:
                url = "%s&%s" % (url, suffix)
            else:
                url = "%s?%s" % (url, suffix)
            if fragment is not None:
                url = "%s#%s" % (url, fragment)
        return url

    def _converter(self, matchobj, group, template):
        url = matchobj.group(group)
        url = url.strip(' \'"')
        if url.startswith('#'):
            return "url('%s')" % url
        elif url.startswith(SCHEMES):
            return "url('%s')" % self.add_suffix(url)
        full_url = posixpath.normpath('/'.join([str(self.directory_name),
                                                url]))
        if self.has_scheme:
            full_url = "%s%s" % (self.protocol, full_url)
        return template % self.add_suffix(full_url)

    def url_converter(self, matchobj):
        return self._converter(matchobj, 1, "url('%s')")

    def src_converter(self, matchobj):
        return self._converter(matchobj, 2, "src='%s'")

########NEW FILE########
__FILENAME__ = datauri
from __future__ import unicode_literals
import os
import re
import mimetypes
from base64 import b64encode

from compressor.conf import settings
from compressor.filters import FilterBase


class DataUriFilter(FilterBase):
    """Filter for embedding media as data: URIs.

    Settings:
         COMPRESS_DATA_URI_MAX_SIZE: Only files that are smaller than this
                                     value will be embedded. Unit; bytes.


    Don't use this class directly. Use a subclass.
    """
    def input(self, filename=None, **kwargs):
        if not filename or not filename.startswith(settings.COMPRESS_ROOT):
            return self.content
        output = self.content
        for url_pattern in self.url_patterns:
            output = url_pattern.sub(self.data_uri_converter, output)
        return output

    def get_file_path(self, url):
        # strip query string of file paths
        if "?" in url:
            url = url.split("?")[0]
        if "#" in url:
            url = url.split("#")[0]
        return os.path.join(
            settings.COMPRESS_ROOT, url[len(settings.COMPRESS_URL):])

    def data_uri_converter(self, matchobj):
        url = matchobj.group(1).strip(' \'"')
        if not url.startswith('data:') and not url.startswith('//'):
            path = self.get_file_path(url)
            if os.stat(path).st_size <= settings.COMPRESS_DATA_URI_MAX_SIZE:
                with open(path, 'rb') as file:
                    data = b64encode(file.read()).decode('ascii')
                return 'url("data:%s;base64,%s")' % (
                    mimetypes.guess_type(path)[0], data)
        return 'url("%s")' % url


class CssDataUriFilter(DataUriFilter):
    """Filter for embedding media as data: URIs in CSS files.

    See DataUriFilter.
    """
    url_patterns = (
        re.compile(r'url\(([^\)]+)\)'),
    )

########NEW FILE########
__FILENAME__ = rjsmin
#!/usr/bin/env python
# -*- coding: ascii -*-
#
# Copyright 2011 - 2013
# Andr\xe9 Malo or his licensors, as applicable
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""
=====================
 Javascript Minifier
=====================

rJSmin is a javascript minifier written in python.

The minifier is based on the semantics of `jsmin.c by Douglas Crockford`_\.

The module is a re-implementation aiming for speed, so it can be used at
runtime (rather than during a preprocessing step). Usually it produces the
same results as the original ``jsmin.c``. It differs in the following ways:

- there is no error detection: unterminated string, regex and comment
  literals are treated as regular javascript code and minified as such.
- Control characters inside string and regex literals are left untouched; they
  are not converted to spaces (nor to \n)
- Newline characters are not allowed inside string and regex literals, except
  for line continuations in string literals (ECMA-5).
- "return /regex/" is recognized correctly.
- "+ +" and "- -" sequences are not collapsed to '++' or '--'
- Newlines before ! operators are removed more sensibly
- rJSmin does not handle streams, but only complete strings. (However, the
  module provides a "streamy" interface).

Since most parts of the logic are handled by the regex engine it's way
faster than the original python port of ``jsmin.c`` by Baruch Even. The speed
factor varies between about 6 and 55 depending on input and python version
(it gets faster the more compressed the input already is). Compared to the
speed-refactored python port by Dave St.Germain the performance gain is less
dramatic but still between 1.2 and 7. See the docs/BENCHMARKS file for
details.

rjsmin.c is a reimplementation of rjsmin.py in C and speeds it up even more.

Both python 2 and python 3 are supported.

.. _jsmin.c by Douglas Crockford:
   http://www.crockford.com/javascript/jsmin.c
"""
__author__ = "Andr\xe9 Malo"
__author__ = getattr(__author__, 'decode', lambda x: __author__)('latin-1')
__docformat__ = "restructuredtext en"
__license__ = "Apache License, Version 2.0"
__version__ = '1.0.7'
__all__ = ['jsmin']

import re as _re


def _make_jsmin(python_only=False):
    """
    Generate JS minifier based on `jsmin.c by Douglas Crockford`_

    .. _jsmin.c by Douglas Crockford:
       http://www.crockford.com/javascript/jsmin.c

    :Parameters:
      `python_only` : ``bool``
        Use only the python variant. If true, the c extension is not even
        tried to be loaded.

    :Return: Minifier
    :Rtype: ``callable``
    """
    # pylint: disable = R0912, R0914, W0612
    if not python_only:
        try:
            import _rjsmin
        except ImportError:
            pass
        else:
            return _rjsmin.jsmin
    try:
        xrange
    except NameError:
        xrange = range # pylint: disable = W0622

    space_chars = r'[\000-\011\013\014\016-\040]'

    line_comment = r'(?://[^\r\n]*)'
    space_comment = r'(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)'
    string1 = \
        r'(?:\047[^\047\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|\r)[^\047\\\r\n]*)*\047)'
    string2 = r'(?:"[^"\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|\r)[^"\\\r\n]*)*")'
    strings = r'(?:%s|%s)' % (string1, string2)

    charclass = r'(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]*)*\])'
    nospecial = r'[^/\\\[\r\n]'
    regex = r'(?:/(?![\r\n/*])%s*(?:(?:\\[^\r\n]|%s)%s*)*/)' % (
        nospecial, charclass, nospecial
    )
    space = r'(?:%s|%s)' % (space_chars, space_comment)
    newline = r'(?:%s?[\r\n])' % line_comment

    def fix_charclass(result):
        """ Fixup string of chars to fit into a regex char class """
        pos = result.find('-')
        if pos >= 0:
            result = r'%s%s-' % (result[:pos], result[pos + 1:])

        def sequentize(string):
            """
            Notate consecutive characters as sequence

            (1-4 instead of 1234)
            """
            first, last, result = None, None, []
            for char in map(ord, string):
                if last is None:
                    first = last = char
                elif last + 1 == char:
                    last = char
                else:
                    result.append((first, last))
                    first = last = char
            if last is not None:
                result.append((first, last))
            return ''.join(['%s%s%s' % (
                chr(first2),
                last2 > first2 + 1 and '-' or '',
                last2 != first2 and chr(last2) or ''
            ) for first2, last2 in result])

        return _re.sub(r'([\000-\040\047])', # for better portability
            lambda m: '\\%03o' % ord(m.group(1)), (sequentize(result)
                .replace('\\', '\\\\')
                .replace('[', '\\[')
                .replace(']', '\\]')
            )
        )

    def id_literal_(what):
        """ Make id_literal like char class """
        match = _re.compile(what).match
        result = ''.join([
            chr(c) for c in xrange(127) if not match(chr(c))
        ])
        return '[^%s]' % fix_charclass(result)

    def not_id_literal_(keep):
        """ Make negated id_literal like char class """
        match = _re.compile(id_literal_(keep)).match
        result = ''.join([
            chr(c) for c in xrange(127) if not match(chr(c))
        ])
        return r'[%s]' % fix_charclass(result)

    not_id_literal = not_id_literal_(r'[a-zA-Z0-9_$]')
    preregex1 = r'[(,=:\[!&|?{};\r\n]'
    preregex2 = r'%(not_id_literal)sreturn' % locals()

    id_literal = id_literal_(r'[a-zA-Z0-9_$]')
    id_literal_open = id_literal_(r'[a-zA-Z0-9_${\[(!+-]')
    id_literal_close = id_literal_(r'[a-zA-Z0-9_$}\])"\047+-]')

    dull = r'[^\047"/\000-\040]'

    space_sub = _re.compile((
        r'(%(dull)s+)'
        r'|(%(strings)s%(dull)s*)'
        r'|(?<=%(preregex1)s)'
            r'%(space)s*(?:%(newline)s%(space)s*)*'
            r'(%(regex)s%(dull)s*)'
        r'|(?<=%(preregex2)s)'
            r'%(space)s*(?:%(newline)s%(space)s)*'
            r'(%(regex)s%(dull)s*)'
        r'|(?<=%(id_literal_close)s)'
            r'%(space)s*(?:(%(newline)s)%(space)s*)+'
            r'(?=%(id_literal_open)s)'
        r'|(?<=%(id_literal)s)(%(space)s)+(?=%(id_literal)s)'
        r'|(?<=\+)(%(space)s)+(?=\+)'
        r'|(?<=-)(%(space)s)+(?=-)'
        r'|%(space)s+'
        r'|(?:%(newline)s%(space)s*)+'
    ) % locals()).sub
    # print space_sub.__self__.pattern

    def space_subber(match):
        """ Substitution callback """
        # pylint: disable = C0321, R0911
        groups = match.groups()
        if groups[0]: return groups[0]
        elif groups[1]: return groups[1]
        elif groups[2]: return groups[2]
        elif groups[3]: return groups[3]
        elif groups[4]: return '\n'
        elif groups[5] or groups[6] or groups[7]: return ' '
        else: return ''

    def jsmin(script): # pylint: disable = W0621
        r"""
        Minify javascript based on `jsmin.c by Douglas Crockford`_\.

        Instead of parsing the stream char by char, it uses a regular
        expression approach which minifies the whole script with one big
        substitution regex.

        .. _jsmin.c by Douglas Crockford:
           http://www.crockford.com/javascript/jsmin.c

        :Parameters:
          `script` : ``str``
            Script to minify

        :Return: Minified script
        :Rtype: ``str``
        """
        return space_sub(space_subber, '\n%s\n' % script).strip()

    return jsmin

jsmin = _make_jsmin()


def jsmin_for_posers(script):
    r"""
    Minify javascript based on `jsmin.c by Douglas Crockford`_\.

    Instead of parsing the stream char by char, it uses a regular
    expression approach which minifies the whole script with one big
    substitution regex.

    .. _jsmin.c by Douglas Crockford:
       http://www.crockford.com/javascript/jsmin.c

    :Warning: This function is the digest of a _make_jsmin() call. It just
              utilizes the resulting regex. It's just for fun here and may
              vanish any time. Use the `jsmin` function instead.

    :Parameters:
      `script` : ``str``
        Script to minify

    :Return: Minified script
    :Rtype: ``str``
    """
    def subber(match):
        """ Substitution callback """
        groups = match.groups()
        return (
            groups[0] or
            groups[1] or
            groups[2] or
            groups[3] or
            (groups[4] and '\n') or
            (groups[5] and ' ') or
            (groups[6] and ' ') or
            (groups[7] and ' ') or
            ''
        )

    return _re.sub(
        r'([^\047"/\000-\040]+)|((?:(?:\047[^\047\\\r\n]*(?:\\(?:[^\r\n]|\r?'
        r'\n|\r)[^\047\\\r\n]*)*\047)|(?:"[^"\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|'
        r'\r)[^"\\\r\n]*)*"))[^\047"/\000-\040]*)|(?<=[(,=:\[!&|?{};\r\n])(?'
        r':[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*'
        r'(?:(?:(?://[^\r\n]*)?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:/\*'
        r'[^*]*\*+(?:[^/*][^*]*\*+)*/))*)*((?:/(?![\r\n/*])[^/\\\[\r\n]*(?:('
        r'?:\\[^\r\n]|(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/\\\['
        r'\r\n]*)*/)[^\047"/\000-\040]*)|(?<=[\000-#%-,./:-@\[-^`{-~-]return'
        r')(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'
        r'))*(?:(?:(?://[^\r\n]*)?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:'
        r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))*((?:/(?![\r\n/*])[^/\\\[\r\n]*(?'
        r':(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/'
        r'\\\[\r\n]*)*/)[^\047"/\000-\040]*)|(?<=[^\000-!#%&(*,./:-@\[\\^`{|'
        r'~])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)'
        r'*/))*(?:((?:(?://[^\r\n]*)?[\r\n]))(?:[\000-\011\013\014\016-\040]'
        r'|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)+(?=[^\000-\040"#%-\047)*,./'
        r':-@\\-^`|-~])|(?<=[^\000-#%-,./:-@\[-^`{-~-])((?:[\000-\011\013\01'
        r'4\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=[^\000-#%-,./:'
        r'-@\[-^`{-~-])|(?<=\+)((?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*'
        r'\*+(?:[^/*][^*]*\*+)*/)))+(?=\+)|(?<=-)((?:[\000-\011\013\014\016-'
        r'\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=-)|(?:[\000-\011\013'
        r'\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))+|(?:(?:(?://[^'
        r'\r\n]*)?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^'
        r'/*][^*]*\*+)*/))*)+', subber, '\n%s\n' % script
    ).strip()


if __name__ == '__main__':
    import sys as _sys
    _sys.stdout.write(jsmin(_sys.stdin.read()))

########NEW FILE########
__FILENAME__ = slimit
from __future__ import absolute_import
from compressor.filters import CallbackOutputFilter


class SlimItFilter(CallbackOutputFilter):
    dependencies = ["slimit"]
    callback = "slimit.minify"
    kwargs = {
        "mangle": True,
    }

########NEW FILE########
__FILENAME__ = template
from django.template import Template, Context
from django.conf import settings

from compressor.filters import FilterBase


class TemplateFilter(FilterBase):

    def input(self, filename=None, basename=None, **kwargs):
        template = Template(self.content)
        context = Context(settings.COMPRESS_TEMPLATE_FILTER_CONTEXT)
        return template.render(context)

########NEW FILE########
__FILENAME__ = yuglify
from compressor.conf import settings
from compressor.filters import CompilerFilter


class YUglifyFilter(CompilerFilter):
    command = "{binary} {args}"

    def __init__(self, *args, **kwargs):
        super(YUglifyFilter, self).__init__(*args, **kwargs)
        self.command += ' --type=%s' % self.type


class YUglifyCSSFilter(YUglifyFilter):
    type = 'css'
    options = (
        ("binary", settings.COMPRESS_YUGLIFY_BINARY),
        ("args", settings.COMPRESS_YUGLIFY_CSS_ARGUMENTS),
    )


class YUglifyJSFilter(YUglifyFilter):
    type = 'js'
    options = (
        ("binary", settings.COMPRESS_YUGLIFY_BINARY),
        ("args", settings.COMPRESS_YUGLIFY_JS_ARGUMENTS),
    )

########NEW FILE########
__FILENAME__ = yui
from compressor.conf import settings
from compressor.filters import CompilerFilter


class YUICompressorFilter(CompilerFilter):
    command = "{binary} {args}"

    def __init__(self, *args, **kwargs):
        super(YUICompressorFilter, self).__init__(*args, **kwargs)
        self.command += ' --type=%s' % self.type
        if self.verbose:
            self.command += ' --verbose'


class YUICSSFilter(YUICompressorFilter):
    type = 'css'
    options = (
        ("binary", settings.COMPRESS_YUI_BINARY),
        ("args", settings.COMPRESS_YUI_CSS_ARGUMENTS),
    )


class YUIJSFilter(YUICompressorFilter):
    type = 'js'
    options = (
        ("binary", settings.COMPRESS_YUI_BINARY),
        ("args", settings.COMPRESS_YUI_JS_ARGUMENTS),
    )

########NEW FILE########
__FILENAME__ = finders
from compressor.utils import staticfiles
from compressor.storage import CompressorFileStorage


class CompressorFinder(staticfiles.finders.BaseStorageFinder):
    """
    A staticfiles finder that looks in COMPRESS_ROOT
    for compressed files, to be used during development
    with staticfiles development file server or during
    deployment.
    """
    storage = CompressorFileStorage

    def list(self, ignore_patterns):
        return []

########NEW FILE########
__FILENAME__ = js
from compressor.conf import settings
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE


class JsCompressor(Compressor):

    def __init__(self, content=None, output_prefix="js", context=None):
        super(JsCompressor, self).__init__(content, output_prefix, context)
        self.filters = list(settings.COMPRESS_JS_FILTERS)
        self.type = output_prefix

    def split_contents(self):
        if self.split_content:
            return self.split_content
        for elem in self.parser.js_elems():
            attribs = self.parser.elem_attribs(elem)
            if 'src' in attribs:
                basename = self.get_basename(attribs['src'])
                filename = self.get_filename(basename)
                content = (SOURCE_FILE, filename, basename, elem)
                self.split_content.append(content)
            else:
                content = self.parser.elem_content(elem)
                self.split_content.append((SOURCE_HUNK, content, None, elem))
        return self.split_content

########NEW FILE########
__FILENAME__ = compress
# flake8: noqa
import os
import sys

from fnmatch import fnmatch
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError
import django.template
from django.template import Context
from django.utils import six
from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module
from django.template.loader import get_template  # noqa Leave this in to preload template locations

from compressor.cache import get_offline_hexdigest, write_offline_manifest
from compressor.conf import settings
from compressor.exceptions import (OfflineGenerationError, TemplateSyntaxError,
                                   TemplateDoesNotExist)
from compressor.templatetags.compress import CompressorNode

if six.PY3:
    # there is an 'io' module in python 2.6+, but io.StringIO does not
    # accept regular strings, just unicode objects
    from io import StringIO
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


class Command(NoArgsCommand):
    help = "Compress content outside of the request/response cycle"
    option_list = NoArgsCommand.option_list + (
        make_option('--extension', '-e', action='append', dest='extensions',
            help='The file extension(s) to examine (default: ".html", '
                'separate multiple extensions with commas, or use -e '
                'multiple times)'),
        make_option('-f', '--force', default=False, action='store_true',
            help="Force the generation of compressed content even if the "
                "COMPRESS_ENABLED setting is not True.", dest='force'),
        make_option('--follow-links', default=False, action='store_true',
            help="Follow symlinks when traversing the COMPRESS_ROOT "
                "(which defaults to STATIC_ROOT). Be aware that using this "
                "can lead to infinite recursion if a link points to a parent "
                "directory of itself.", dest='follow_links'),
        make_option('--engine', default="django", action="store",
            help="Specifies the templating engine. jinja2 or django",
            dest="engine"),
    )

    requires_model_validation = False

    def get_loaders(self):
        from django.template.loader import template_source_loaders
        if template_source_loaders is None:
            try:
                from django.template.loader import (
                    find_template as finder_func)
            except ImportError:
                from django.template.loader import (
                    find_template_source as finder_func)  # noqa
            try:
                # Force django to calculate template_source_loaders from
                # TEMPLATE_LOADERS settings, by asking to find a dummy template
                source, name = finder_func('test')
            except django.template.TemplateDoesNotExist:
                pass
            # Reload template_source_loaders now that it has been calculated ;
            # it should contain the list of valid, instanciated template loaders
            # to use.
            from django.template.loader import template_source_loaders
        loaders = []
        # If template loader is CachedTemplateLoader, return the loaders
        # that it wraps around. So if we have
        # TEMPLATE_LOADERS = (
        #    ('django.template.loaders.cached.Loader', (
        #        'django.template.loaders.filesystem.Loader',
        #        'django.template.loaders.app_directories.Loader',
        #    )),
        # )
        # The loaders will return django.template.loaders.filesystem.Loader
        # and django.template.loaders.app_directories.Loader
        # The cached Loader and similar ones include a 'loaders' attribute
        # so we look for that.
        for loader in template_source_loaders:
            if hasattr(loader, 'loaders'):
                loaders.extend(loader.loaders)
            else:
                loaders.append(loader)
        return loaders

    def __get_parser(self, engine):
        if engine == "jinja2":
            from compressor.offline.jinja2 import Jinja2Parser
            env = settings.COMPRESS_JINJA2_GET_ENVIRONMENT()
            parser = Jinja2Parser(charset=settings.FILE_CHARSET, env=env)
        elif engine == "django":
            from compressor.offline.django import DjangoParser
            parser = DjangoParser(charset=settings.FILE_CHARSET)
        else:
            raise OfflineGenerationError("Invalid templating engine specified.")

        return parser

    def compress(self, log=None, **options):
        """
        Searches templates containing 'compress' nodes and compresses them
        "offline" -- outside of the request/response cycle.

        The result is cached with a cache-key derived from the content of the
        compress nodes (not the content of the possibly linked files!).
        """
        extensions = options.get('extensions')
        extensions = self.handle_extensions(extensions or ['html'])
        verbosity = int(options.get("verbosity", 0))
        if not log:
            log = StringIO()
        if not settings.TEMPLATE_LOADERS:
            raise OfflineGenerationError("No template loaders defined. You "
                                         "must set TEMPLATE_LOADERS in your "
                                         "settings.")
        paths = set()
        for loader in self.get_loaders():
            try:
                module = import_module(loader.__module__)
                get_template_sources = getattr(module,
                    'get_template_sources', None)
                if get_template_sources is None:
                    get_template_sources = loader.get_template_sources
                paths.update(list(get_template_sources('')))
            except (ImportError, AttributeError):
                # Yeah, this didn't work out so well, let's move on
                pass
        if not paths:
            raise OfflineGenerationError("No template paths found. None of "
                                         "the configured template loaders "
                                         "provided template paths. See "
                                         "http://django.me/template-loaders "
                                         "for more information on template "
                                         "loaders.")
        if verbosity > 1:
            log.write("Considering paths:\n\t" + "\n\t".join(paths) + "\n")
        templates = set()
        for path in paths:
            for root, dirs, files in os.walk(path,
                    followlinks=options.get('followlinks', False)):
                templates.update(os.path.join(root, name)
                    for name in files if not name.startswith('.') and
                        any(fnmatch(name, "*%s" % glob) for glob in extensions))
        if not templates:
            raise OfflineGenerationError("No templates found. Make sure your "
                                         "TEMPLATE_LOADERS and TEMPLATE_DIRS "
                                         "settings are correct.")
        if verbosity > 1:
            log.write("Found templates:\n\t" + "\n\t".join(templates) + "\n")

        engine = options.get("engine", "django")
        parser = self.__get_parser(engine)

        compressor_nodes = SortedDict()
        for template_name in templates:
            try:
                template = parser.parse(template_name)
            except IOError:  # unreadable file -> ignore
                if verbosity > 0:
                    log.write("Unreadable template at: %s\n" % template_name)
                continue
            except TemplateSyntaxError as e:  # broken template -> ignore
                if verbosity > 0:
                    log.write("Invalid template %s: %s\n" % (template_name, e))
                continue
            except TemplateDoesNotExist:  # non existent template -> ignore
                if verbosity > 0:
                    log.write("Non-existent template at: %s\n" % template_name)
                continue
            except UnicodeDecodeError:
                if verbosity > 0:
                    log.write("UnicodeDecodeError while trying to read "
                              "template %s\n" % template_name)
            try:
                nodes = list(parser.walk_nodes(template))
            except (TemplateDoesNotExist, TemplateSyntaxError) as e:
                # Could be an error in some base template
                if verbosity > 0:
                    log.write("Error parsing template %s: %s\n" % (template_name, e))
                continue
            if nodes:
                template.template_name = template_name
                compressor_nodes.setdefault(template, []).extend(nodes)

        if not compressor_nodes:
            raise OfflineGenerationError(
                "No 'compress' template tags found in templates."
                "Try running compress command with --follow-links and/or"
                "--extension=EXTENSIONS")

        if verbosity > 0:
            log.write("Found 'compress' tags in:\n\t" +
                      "\n\t".join((t.template_name
                                   for t in compressor_nodes.keys())) + "\n")

        log.write("Compressing... ")
        count = 0
        results = []
        offline_manifest = SortedDict()
        init_context = parser.get_init_context(settings.COMPRESS_OFFLINE_CONTEXT)

        for template, nodes in compressor_nodes.items():
            context = Context(init_context)
            template._log = log
            template._log_verbosity = verbosity

            if not parser.process_template(template, context):
                continue

            for node in nodes:
                context.push()
                parser.process_node(template, context, node)
                rendered = parser.render_nodelist(template, context, node)
                key = get_offline_hexdigest(rendered)

                if key in offline_manifest:
                    continue

                try:
                    result = parser.render_node(template, context, node)
                except Exception as e:
                    raise CommandError("An error occured during rendering %s: "
                                       "%s" % (template.template_name, e))
                offline_manifest[key] = result
                context.pop()
                results.append(result)
                count += 1

        write_offline_manifest(offline_manifest)

        log.write("done\nCompressed %d block(s) from %d template(s).\n" %
                  (count, len(compressor_nodes)))
        return count, results

    def handle_extensions(self, extensions=('html',)):
        """
        organizes multiple extensions that are separated with commas or
        passed by using --extension/-e multiple times.

        for example: running 'django-admin compress -e js,txt -e xhtml -a'
        would result in a extension list: ['.js', '.txt', '.xhtml']

        >>> handle_extensions(['.html', 'html,js,py,py,py,.py', 'py,.py'])
        ['.html', '.js']
        >>> handle_extensions(['.html, txt,.tpl'])
        ['.html', '.tpl', '.txt']
        """
        ext_list = []
        for ext in extensions:
            ext_list.extend(ext.replace(' ', '').split(','))
        for i, ext in enumerate(ext_list):
            if not ext.startswith('.'):
                ext_list[i] = '.%s' % ext_list[i]
        return set(ext_list)

    def handle_noargs(self, **options):
        if not settings.COMPRESS_ENABLED and not options.get("force"):
            raise CommandError(
                "Compressor is disabled. Set the COMPRESS_ENABLED "
                "setting or use --force to override.")
        if not settings.COMPRESS_OFFLINE:
            if not options.get("force"):
                raise CommandError(
                    "Offline compression is disabled. Set "
                    "COMPRESS_OFFLINE or use the --force to override.")
        self.compress(sys.stdout, **options)

########NEW FILE########
__FILENAME__ = mtime_cache
import fnmatch
import os
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError

from compressor.conf import settings
from compressor.cache import cache, get_mtime, get_mtime_cachekey


class Command(NoArgsCommand):
    help = "Add or remove all mtime values from the cache"
    option_list = NoArgsCommand.option_list + (
        make_option('-i', '--ignore', action='append', default=[],
            dest='ignore_patterns', metavar='PATTERN',
            help="Ignore files or directories matching this glob-style "
                "pattern. Use multiple times to ignore more."),
        make_option('--no-default-ignore', action='store_false',
            dest='use_default_ignore_patterns', default=True,
            help="Don't ignore the common private glob-style patterns 'CVS', "
                "'.*' and '*~'."),
        make_option('--follow-links', dest='follow_links', action='store_true',
            help="Follow symlinks when traversing the COMPRESS_ROOT "
                "(which defaults to STATIC_ROOT). Be aware that using this "
                "can lead to infinite recursion if a link points to a parent "
                "directory of itself."),
        make_option('-c', '--clean', dest='clean', action='store_true',
            help="Remove all items"),
        make_option('-a', '--add', dest='add', action='store_true',
            help="Add all items"),
    )

    def is_ignored(self, path):
        """
        Return True or False depending on whether the ``path`` should be
        ignored (if it matches any pattern in ``ignore_patterns``).
        """
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatchcase(path, pattern):
                return True
        return False

    def handle_noargs(self, **options):
        ignore_patterns = options['ignore_patterns']
        if options['use_default_ignore_patterns']:
            ignore_patterns += ['CVS', '.*', '*~']
            options['ignore_patterns'] = ignore_patterns
        self.ignore_patterns = ignore_patterns

        if (options['add'] and options['clean']) or (not options['add'] and not options['clean']):
            raise CommandError('Please specify either "--add" or "--clean"')

        if not settings.COMPRESS_MTIME_DELAY:
            raise CommandError('mtime caching is currently disabled. Please '
                'set the COMPRESS_MTIME_DELAY setting to a number of seconds.')

        files_to_add = set()
        keys_to_delete = set()

        for root, dirs, files in os.walk(settings.COMPRESS_ROOT, followlinks=options['follow_links']):
            for dir_ in dirs:
                if self.is_ignored(dir_):
                    dirs.remove(dir_)
            for filename in files:
                common = "".join(root.split(settings.COMPRESS_ROOT))
                if common.startswith(os.sep):
                    common = common[len(os.sep):]
                if self.is_ignored(os.path.join(common, filename)):
                    continue
                filename = os.path.join(root, filename)
                keys_to_delete.add(get_mtime_cachekey(filename))
                if options['add']:
                    files_to_add.add(filename)

        if keys_to_delete:
            cache.delete_many(list(keys_to_delete))
            print("Deleted mtimes of %d files from the cache." % len(keys_to_delete))

        if files_to_add:
            for filename in files_to_add:
                get_mtime(filename)
            print("Added mtimes of %d files to cache." % len(files_to_add))

########NEW FILE########
__FILENAME__ = models
from compressor.conf import CompressorConf  # noqa

########NEW FILE########
__FILENAME__ = django
from __future__ import absolute_import
from copy import copy

from django import template
from django.conf import settings
from django.template import Context
from django.template.base import Node, VariableNode, TextNode, NodeList
from django.template.defaulttags import IfNode
from django.template.loader import get_template
from django.template.loader_tags import ExtendsNode, BlockNode, BlockContext


from compressor.exceptions import TemplateSyntaxError, TemplateDoesNotExist
from compressor.templatetags.compress import CompressorNode


def handle_extendsnode(extendsnode, block_context=None):
    """Create a copy of Node tree of a derived template replacing
    all blocks tags with the nodes of appropriate blocks.
    Also handles {{ block.super }} tags.
    """
    if block_context is None:
        block_context = BlockContext()
    blocks = dict((n.name, n) for n in
                  extendsnode.nodelist.get_nodes_by_type(BlockNode))
    block_context.add_blocks(blocks)

    context = Context(settings.COMPRESS_OFFLINE_CONTEXT)
    compiled_parent = extendsnode.get_parent(context)
    parent_nodelist = compiled_parent.nodelist
    # If the parent template has an ExtendsNode it is not the root.
    for node in parent_nodelist:
        # The ExtendsNode has to be the first non-text node.
        if not isinstance(node, TextNode):
            if isinstance(node, ExtendsNode):
                return handle_extendsnode(node, block_context)
            break
    # Add blocks of the root template to block context.
    blocks = dict((n.name, n) for n in
                  parent_nodelist.get_nodes_by_type(BlockNode))
    block_context.add_blocks(blocks)

    block_stack = []
    new_nodelist = remove_block_nodes(parent_nodelist, block_stack, block_context)
    return new_nodelist


def remove_block_nodes(nodelist, block_stack, block_context):
    new_nodelist = NodeList()
    for node in nodelist:
        if isinstance(node, VariableNode):
            var_name = node.filter_expression.token.strip()
            if var_name == 'block.super':
                if not block_stack:
                    continue
                node = block_context.get_block(block_stack[-1].name)
        if isinstance(node, BlockNode):
            expanded_block = expand_blocknode(node, block_stack, block_context)
            new_nodelist.extend(expanded_block)
        else:
            # IfNode has nodelist as a @property so we can not modify it
            if isinstance(node, IfNode):
                node = copy(node)
                for i, (condition, sub_nodelist) in enumerate(node.conditions_nodelists):
                    sub_nodelist = remove_block_nodes(sub_nodelist, block_stack, block_context)
                    node.conditions_nodelists[i] = (condition, sub_nodelist)
            else:
                for attr in node.child_nodelists:
                    sub_nodelist = getattr(node, attr, None)
                    if sub_nodelist:
                        sub_nodelist = remove_block_nodes(sub_nodelist, block_stack, block_context)
                        node = copy(node)
                        setattr(node, attr, sub_nodelist)
            new_nodelist.append(node)
    return new_nodelist


def expand_blocknode(node, block_stack, block_context):
    popped_block = block = block_context.pop(node.name)
    if block is None:
        block = node
    block_stack.append(block)
    expanded_nodelist = remove_block_nodes(block.nodelist, block_stack, block_context)
    block_stack.pop()
    if popped_block is not None:
        block_context.push(node.name, popped_block)
    return expanded_nodelist


class DjangoParser(object):
    def __init__(self, charset):
        self.charset = charset

    def parse(self, template_name):
        try:
            return get_template(template_name)
        except template.TemplateSyntaxError as e:
            raise TemplateSyntaxError(str(e))
        except template.TemplateDoesNotExist as e:
            raise TemplateDoesNotExist(str(e))

    def process_template(self, template, context):
        return True

    def get_init_context(self, offline_context):
        return offline_context

    def process_node(self, template, context, node):
        pass

    def render_nodelist(self, template, context, node):
        return node.nodelist.render(context)

    def render_node(self, template, context, node):
        return node.render(context, forced=True)

    def get_nodelist(self, node):
        if isinstance(node, ExtendsNode):
            try:
                return handle_extendsnode(node)
            except template.TemplateSyntaxError as e:
                raise TemplateSyntaxError(str(e))
            except template.TemplateDoesNotExist as e:
                raise TemplateDoesNotExist(str(e))

        # Check if node is an ```if``` switch with true and false branches
        nodelist = []
        if isinstance(node, Node):
            for attr in node.child_nodelists:
                nodelist += getattr(node, attr, [])
        else:
            nodelist = getattr(node, 'nodelist', [])
        return nodelist

    def walk_nodes(self, node):
        for node in self.get_nodelist(node):
            if isinstance(node, CompressorNode) and node.is_offline_compression_enabled(forced=True):
                yield node
            else:
                for node in self.walk_nodes(node):
                    yield node

########NEW FILE########
__FILENAME__ = jinja2
from __future__ import absolute_import
import io

import jinja2
import jinja2.ext
from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.nodes import CallBlock, Call, ExtensionAttribute

from compressor.exceptions import TemplateSyntaxError, TemplateDoesNotExist


def flatten_context(context):
    if hasattr(context, 'dicts'):
        context_dict = {}

        for d in context.dicts:
            context_dict.update(d)

        return context_dict

    return context


class SpacelessExtension(Extension):
    """
    Functional "spaceless" extension equivalent to Django's.

    See: https://github.com/django/django/blob/master/django/template/defaulttags.py
    """

    tags = set(['spaceless'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        body = parser.parse_statements(['name:endspaceless'], drop_needle=True)

        return nodes.CallBlock(self.call_method('_spaceless', []),
                               [], [], body).set_lineno(lineno)

    def _spaceless(self, caller):
        from django.utils.html import strip_spaces_between_tags

        return strip_spaces_between_tags(caller().strip())


def url_for(mod, filename):
    """
    Incomplete emulation of Flask's url_for.
    """
    from django.contrib.staticfiles.templatetags import staticfiles

    if mod == "static":
        return staticfiles.static(filename)

    return ""


class Jinja2Parser(object):
    COMPRESSOR_ID = 'compressor.contrib.jinja2ext.CompressorExtension'

    def __init__(self, charset, env):
        self.charset = charset
        self.env = env

    def parse(self, template_name):
        with io.open(template_name, mode='rb') as file:
            try:
                template = self.env.parse(file.read().decode(self.charset))
            except jinja2.TemplateSyntaxError as e:
                raise TemplateSyntaxError(str(e))
            except jinja2.TemplateNotFound as e:
                raise TemplateDoesNotExist(str(e))

        return template

    def process_template(self, template, context):
        return True

    def get_init_context(self, offline_context):
        # Don't need to add filters and tests to the context, as Jinja2 will
        # automatically look for them in self.env.filters and self.env.tests.
        # This is tested by test_complex and test_templatetag.

        # Allow offline context to override the globals.
        context = self.env.globals.copy()
        context.update(offline_context)

        return context

    def process_node(self, template, context, node):
        pass

    def _render_nodes(self, template, context, nodes):
        compiled_node = self.env.compile(jinja2.nodes.Template(nodes))
        template = jinja2.Template.from_code(self.env, compiled_node, {})
        flat_context = flatten_context(context)

        return template.render(flat_context)

    def render_nodelist(self, template, context, node):
        return self._render_nodes(template, context, node.body)

    def render_node(self, template, context, node):
        return self._render_nodes(template, context, [node])

    def get_nodelist(self, node):
        body = getattr(node, "body", getattr(node, "nodes", []))

        if isinstance(node, jinja2.nodes.If):
            return body + node.else_

        return body

    def walk_nodes(self, node, block_name=None):
        for node in self.get_nodelist(node):
            if (isinstance(node, CallBlock) and
              isinstance(node.call, Call) and
              isinstance(node.call.node, ExtensionAttribute) and
              node.call.node.identifier == self.COMPRESSOR_ID):
                node.call.node.name = '_compress_forced'
                yield node
            else:
                for node in self.walk_nodes(node, block_name=block_name):
                    yield node

########NEW FILE########
__FILENAME__ = base
class ParserBase(object):
    """
    Base parser to be subclassed when creating an own parser.
    """
    def __init__(self, content):
        self.content = content

    def css_elems(self):
        """
        Return an iterable containing the css elements to handle
        """
        raise NotImplementedError

    def js_elems(self):
        """
        Return an iterable containing the js elements to handle
        """
        raise NotImplementedError

    def elem_attribs(self, elem):
        """
        Return the dictionary like attribute store of the given element
        """
        raise NotImplementedError

    def elem_content(self, elem):
        """
        Return the content of the given element
        """
        raise NotImplementedError

    def elem_name(self, elem):
        """
        Return the name of the given element
        """
        raise NotImplementedError

    def elem_str(self, elem):
        """
        Return the string representation of the given elem
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = beautifulsoup
from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.encoding import smart_text

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class BeautifulSoupParser(ParserBase):

    @cached_property
    def soup(self):
        try:
            if six.PY3:
                from bs4 import BeautifulSoup
            else:
                from BeautifulSoup import BeautifulSoup
            return BeautifulSoup(self.content)
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing BeautifulSoup: %s" % err)
        except Exception as err:
            raise ParserError("Error while initializing Parser: %s" % err)

    def css_elems(self):
        if six.PY3:
            return self.soup.find_all({'link': True, 'style': True})
        else:
            return self.soup.findAll({'link': True, 'style': True})

    def js_elems(self):
        if six.PY3:
            return self.soup.find_all('script')
        else:
            return self.soup.findAll('script')

    def elem_attribs(self, elem):
        return dict(elem.attrs)

    def elem_content(self, elem):
        return elem.string

    def elem_name(self, elem):
        return elem.name

    def elem_str(self, elem):
        return smart_text(elem)

########NEW FILE########
__FILENAME__ = default_htmlparser
from django.utils import six
from django.utils.encoding import smart_text

from compressor.exceptions import ParserError
from compressor.parser import ParserBase


class DefaultHtmlParser(ParserBase, six.moves.html_parser.HTMLParser):
    def __init__(self, content):
        six.moves.html_parser.HTMLParser.__init__(self)
        self.content = content
        self._css_elems = []
        self._js_elems = []
        self._current_tag = None
        try:
            self.feed(self.content)
            self.close()
        except Exception as err:
            lineno = err.lineno
            line = self.content.splitlines()[lineno]
            raise ParserError("Error while initializing HtmlParser: %s (line: %s)" % (err, repr(line)))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in ('style', 'script'):
            if tag == 'style':
                tags = self._css_elems
            elif tag == 'script':
                tags = self._js_elems
            tags.append({
                'tag': tag,
                'attrs': attrs,
                'attrs_dict': dict(attrs),
                'text': ''
            })
            self._current_tag = tag
        elif tag == 'link':
            self._css_elems.append({
                'tag': tag,
                'attrs': attrs,
                'attrs_dict': dict(attrs),
                'text': None
            })

    def handle_endtag(self, tag):
        if self._current_tag and self._current_tag == tag.lower():
            self._current_tag = None

    def handle_data(self, data):
        if self._current_tag == 'style':
            self._css_elems[-1]['text'] = data
        elif self._current_tag == 'script':
            self._js_elems[-1]['text'] = data

    def css_elems(self):
        return self._css_elems

    def js_elems(self):
        return self._js_elems

    def elem_name(self, elem):
        return elem['tag']

    def elem_attribs(self, elem):
        return elem['attrs_dict']

    def elem_content(self, elem):
        return smart_text(elem['text'])

    def elem_str(self, elem):
        tag = {}
        tag.update(elem)
        tag['attrs'] = ''
        if len(elem['attrs']):
            tag['attrs'] = ' %s' % ' '.join(['%s="%s"' % (name, value) for name, value in elem['attrs']])
        if elem['tag'] == 'link':
            return '<%(tag)s%(attrs)s />' % tag
        else:
            return '<%(tag)s%(attrs)s>%(text)s</%(tag)s>' % tag

########NEW FILE########
__FILENAME__ = html5lib
from __future__ import absolute_import
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_text

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class Html5LibParser(ParserBase):

    def __init__(self, content):
        super(Html5LibParser, self).__init__(content)
        import html5lib
        self.html5lib = html5lib

    def _serialize(self, elem):
        return self.html5lib.serialize(
            elem, tree="etree", quote_attr_values=True,
            omit_optional_tags=False, use_trailing_solidus=True,
        )

    def _find(self, *names):
        for elem in self.html:
            if elem.tag in names:
                yield elem

    @cached_property
    def html(self):
        try:
            return self.html5lib.parseFragment(self.content, treebuilder="etree")
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing html5lib: %s" % err)
        except Exception as err:
            raise ParserError("Error while initializing Parser: %s" % err)

    def css_elems(self):
        return self._find('{http://www.w3.org/1999/xhtml}link',
                          '{http://www.w3.org/1999/xhtml}style')

    def js_elems(self):
        return self._find('{http://www.w3.org/1999/xhtml}script')

    def elem_attribs(self, elem):
        return elem.attrib

    def elem_content(self, elem):
        return smart_text(elem.text)

    def elem_name(self, elem):
        if '}' in elem.tag:
            return elem.tag.split('}')[1]
        return elem.tag

    def elem_str(self, elem):
        # This method serializes HTML in a way that does not pass all tests.
        # However, this method is only called in tests anyway, so it doesn't
        # really matter.
        return smart_text(self._serialize(elem))

########NEW FILE########
__FILENAME__ = lxml
from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.encoding import smart_text

from compressor.exceptions import ParserError
from compressor.parser import ParserBase
from compressor.utils.decorators import cached_property


class LxmlParser(ParserBase):
    """
    LxmlParser will use `lxml.html` parser to parse rendered contents of
    {% compress %} tag. Under python 2 it will also try to use beautiful
    soup parser in case of any problems with encoding.
    """
    def __init__(self, content):
        try:
            from lxml.html import fromstring
            from lxml.etree import tostring
        except ImportError as err:
            raise ImproperlyConfigured("Error while importing lxml: %s" % err)
        except Exception as err:
            raise ParserError("Error while initializing parser: %s" % err)

        if not six.PY3:
            # soupparser uses Beautiful Soup 3 which does not run on python 3.x
            try:
                from lxml.html import soupparser
            except ImportError as err:
                soupparser = None
            except Exception as err:
                raise ParserError("Error while initializing parser: %s" % err)
        else:
            soupparser = None

        self.soupparser = soupparser
        self.fromstring = fromstring
        self.tostring = tostring
        super(LxmlParser, self).__init__(content)

    @cached_property
    def tree(self):
        """
        Document tree.
        """
        content = '<root>%s</root>' % self.content
        tree = self.fromstring(content)
        try:
            self.tostring(tree, encoding=six.text_type)
        except UnicodeDecodeError:
            if self.soupparser:  # use soup parser on python 2
                tree = self.soupparser.fromstring(content)
            else:  # raise an error on python 3
                raise
        return tree

    def css_elems(self):
        return self.tree.xpath('//link[re:test(@rel, "^stylesheet$", "i")]|style',
            namespaces={"re": "http://exslt.org/regular-expressions"})

    def js_elems(self):
        return self.tree.findall('script')

    def elem_attribs(self, elem):
        return elem.attrib

    def elem_content(self, elem):
        return smart_text(elem.text)

    def elem_name(self, elem):
        return elem.tag

    def elem_str(self, elem):
        elem_as_string = smart_text(
            self.tostring(elem, method='html', encoding=six.text_type))
        if elem.tag == 'link':
            # This makes testcases happy
            return elem_as_string.replace('>', ' />')
        return elem_as_string

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


post_compress = django.dispatch.Signal(providing_args=['type', 'mode', 'context'])

########NEW FILE########
__FILENAME__ = storage
from __future__ import unicode_literals
import errno
import gzip
import os
from datetime import datetime
import time

from django.core.files.storage import FileSystemStorage, get_storage_class
from django.utils.functional import LazyObject, SimpleLazyObject

from compressor.conf import settings


class CompressorFileStorage(FileSystemStorage):
    """
    Standard file system storage for files handled by django-compressor.

    The defaults for ``location`` and ``base_url`` are ``COMPRESS_ROOT`` and
    ``COMPRESS_URL``.

    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.COMPRESS_ROOT
        if base_url is None:
            base_url = settings.COMPRESS_URL
        super(CompressorFileStorage, self).__init__(location, base_url,
                                                    *args, **kwargs)

    def accessed_time(self, name):
        return datetime.fromtimestamp(os.path.getatime(self.path(name)))

    def created_time(self, name):
        return datetime.fromtimestamp(os.path.getctime(self.path(name)))

    def modified_time(self, name):
        return datetime.fromtimestamp(os.path.getmtime(self.path(name)))

    def get_available_name(self, name):
        """
        Deletes the given file if it exists.
        """
        if self.exists(name):
            self.delete(name)
        return name

    def delete(self, name):
        """
        Handle deletion race condition present in Django prior to 1.4
        https://code.djangoproject.com/ticket/16108
        """
        try:
            super(CompressorFileStorage, self).delete(name)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise


compressor_file_storage = SimpleLazyObject(
    lambda: get_storage_class('compressor.storage.CompressorFileStorage')())


class GzipCompressorFileStorage(CompressorFileStorage):
    """
    The standard compressor file system storage that gzips storage files
    additionally to the usual files.
    """
    def save(self, filename, content):
        filename = super(GzipCompressorFileStorage, self).save(filename, content)
        orig_path = self.path(filename)
        compressed_path = '%s.gz' % orig_path

        f_in = open(orig_path, 'rb')
        f_out = open(compressed_path, 'wb')
        try:
            f_out = gzip.GzipFile(fileobj=f_out)
            f_out.write(f_in.read())
        finally:
            f_out.close()
            f_in.close()
            # Ensure the file timestamps match.
            # os.stat() returns nanosecond resolution on Linux, but os.utime()
            # only sets microsecond resolution.  Set times on both files to
            # ensure they are equal.
            stamp = time.time()
            os.utime(orig_path, (stamp, stamp))
            os.utime(compressed_path, (stamp, stamp))

        return filename


class DefaultStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(settings.COMPRESS_STORAGE)()

default_storage = DefaultStorage()

########NEW FILE########
__FILENAME__ = compress
from django import template
from django.core.exceptions import ImproperlyConfigured
from django.utils import six

from compressor.cache import (cache_get, cache_set, get_offline_hexdigest,
                              get_offline_manifest, get_templatetag_cachekey)
from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.utils import get_class

register = template.Library()

OUTPUT_FILE = 'file'
OUTPUT_INLINE = 'inline'
OUTPUT_MODES = (OUTPUT_FILE, OUTPUT_INLINE)


class CompressorMixin(object):

    def get_original_content(self, context):
        raise NotImplementedError

    @property
    def compressors(self):
        return {
            'js': settings.COMPRESS_JS_COMPRESSOR,
            'css': settings.COMPRESS_CSS_COMPRESSOR,
        }

    def compressor_cls(self, kind, *args, **kwargs):
        if kind not in self.compressors.keys():
            raise template.TemplateSyntaxError(
                "The compress tag's argument must be 'js' or 'css'.")
        return get_class(self.compressors.get(kind),
                         exception=ImproperlyConfigured)(*args, **kwargs)

    def get_compressor(self, context, kind):
        return self.compressor_cls(kind,
            content=self.get_original_content(context), context=context)

    def debug_mode(self, context):
        if settings.COMPRESS_DEBUG_TOGGLE:
            # Only check for the debug parameter
            # if a RequestContext was used
            request = context.get('request', None)
            if request is not None:
                return settings.COMPRESS_DEBUG_TOGGLE in request.GET

    def is_offline_compression_enabled(self, forced):
        """
        Check if offline compression is enabled or forced

        Defaults to just checking the settings and forced argument,
        but can be overridden to completely disable compression for
        a subclass, for instance.
        """
        return (settings.COMPRESS_ENABLED and
                settings.COMPRESS_OFFLINE) or forced

    def render_offline(self, context, forced):
        """
        If enabled and in offline mode, and not forced check the offline cache
        and return the result if given
        """
        if self.is_offline_compression_enabled(forced) and not forced:
            key = get_offline_hexdigest(self.get_original_content(context))
            offline_manifest = get_offline_manifest()
            if key in offline_manifest:
                return offline_manifest[key]
            else:
                raise OfflineGenerationError('You have offline compression '
                    'enabled but key "%s" is missing from offline manifest. '
                    'You may need to run "python manage.py compress".' % key)

    def render_cached(self, compressor, kind, mode, forced=False):
        """
        If enabled checks the cache for the given compressor's cache key
        and return a tuple of cache key and output
        """
        if settings.COMPRESS_ENABLED and not forced:
            cache_key = get_templatetag_cachekey(compressor, mode, kind)
            cache_content = cache_get(cache_key)
            return cache_key, cache_content
        return None, None

    def render_compressed(self, context, kind, mode, forced=False):

        # See if it has been rendered offline
        cached_offline = self.render_offline(context, forced=forced)
        if cached_offline:
            return cached_offline

        # Take a shortcut if we really don't have anything to do
        if ((not settings.COMPRESS_ENABLED and
             not settings.COMPRESS_PRECOMPILERS) and not forced):
            return self.get_original_content(context)

        context['compressed'] = {'name': getattr(self, 'name', None)}
        compressor = self.get_compressor(context, kind)

        # Prepare the actual compressor and check cache
        cache_key, cache_content = self.render_cached(compressor, kind, mode, forced=forced)
        if cache_content is not None:
            return cache_content

        # call compressor output method and handle exceptions
        try:
            rendered_output = self.render_output(compressor, mode, forced=forced)
            if cache_key:
                cache_set(cache_key, rendered_output)
            assert isinstance(rendered_output, six.string_types)
            return rendered_output
        except Exception:
            if settings.DEBUG or forced:
                raise

        # Or don't do anything in production
        return self.get_original_content(context)

    def render_output(self, compressor, mode, forced=False):
        return compressor.output(mode, forced=forced)


class CompressorNode(CompressorMixin, template.Node):

    def __init__(self, nodelist, kind=None, mode=OUTPUT_FILE, name=None):
        self.nodelist = nodelist
        self.kind = kind
        self.mode = mode
        self.name = name

    def get_original_content(self, context):
        return self.nodelist.render(context)

    def debug_mode(self, context):
        if settings.COMPRESS_DEBUG_TOGGLE:
            # Only check for the debug parameter
            # if a RequestContext was used
            request = context.get('request', None)
            if request is not None:
                return settings.COMPRESS_DEBUG_TOGGLE in request.GET

    def render(self, context, forced=False):

        # Check if in debug mode
        if self.debug_mode(context):
            return self.get_original_content(context)

        return self.render_compressed(context, self.kind, self.mode, forced=forced)


@register.tag
def compress(parser, token):
    """
    Compresses linked and inline javascript or CSS into a single cached file.

    Syntax::

        {% compress <js/css> %}
        <html of inline or linked JS/CSS>
        {% endcompress %}

    Examples::

        {% compress css %}
        <link rel="stylesheet" href="/static/css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="/static/css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}

    Which would be rendered something like::

        <link rel="stylesheet" href="/static/CACHE/css/f7c661b7a124.css" type="text/css" media="all" charset="utf-8">

    or::

        {% compress js %}
        <script src="/static/js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}

    Which would be rendered something like::

        <script type="text/javascript" src="/static/CACHE/js/3f33b9146e12.js" charset="utf-8"></script>

    Linked files must be on your COMPRESS_URL (which defaults to STATIC_URL).
    If DEBUG is true off-site files will throw exceptions. If DEBUG is false
    they will be silently stripped.
    """

    nodelist = parser.parse(('endcompress',))
    parser.delete_first_token()

    args = token.split_contents()

    if not len(args) in (2, 3, 4):
        raise template.TemplateSyntaxError(
            "%r tag requires either one, two or three arguments." % args[0])

    kind = args[1]

    if len(args) >= 3:
        mode = args[2]
        if mode not in OUTPUT_MODES:
            raise template.TemplateSyntaxError(
                "%r's second argument must be '%s' or '%s'." %
                (args[0], OUTPUT_FILE, OUTPUT_INLINE))
    else:
        mode = OUTPUT_FILE
    if len(args) == 4:
        name = args[3]
    else:
        name = None
    return CompressorNode(nodelist, kind, mode, name)

########NEW FILE########
__FILENAME__ = precompiler
#!/usr/bin/env python
from __future__ import with_statement
import optparse
import sys


def main():
    p = optparse.OptionParser()
    p.add_option('-f', '--file', action="store",
                 type="string", dest="filename",
                 help="File to read from, defaults to stdin", default=None)
    p.add_option('-o', '--output', action="store",
                 type="string", dest="outfile",
                 help="File to write to, defaults to stdout", default=None)

    options, arguments = p.parse_args()

    if options.filename:
        f = open(options.filename)
        content = f.read()
        f.close()
    else:
        content = sys.stdin.read()

    content = content.replace('background:', 'color:')

    if options.outfile:
        with open(options.outfile, 'w') as f:
            f.write(content)
    else:
        print(content)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_base
from __future__ import with_statement, unicode_literals
import os
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup

from django.utils import six
from django.core.cache.backends import locmem
from django.test import SimpleTestCase
from django.test.utils import override_settings

from compressor.base import SOURCE_HUNK, SOURCE_FILE
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.js import JsCompressor
from compressor.exceptions import FilterDoesNotExist


def make_soup(markup):
    # we use html.parser instead of lxml because it doesn't work on python 3.3
    if six.PY3:
        return BeautifulSoup(markup, 'html.parser')
    else:
        return BeautifulSoup(markup)


def css_tag(href, **kwargs):
    rendered_attrs = ''.join(['%s="%s" ' % (k, v) for k, v in kwargs.items()])
    template = '<link rel="stylesheet" href="%s" type="text/css" %s/>'
    return template % (href, rendered_attrs)


class TestPrecompiler(object):
    """A filter whose output is always the string 'OUTPUT' """
    def __init__(self, content, attrs, filter_type=None, filename=None,
                 charset=None):
        pass

    def input(self, **kwargs):
        return 'OUTPUT'


test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))


class CompressorTestCase(SimpleTestCase):

    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = ()
        settings.COMPRESS_DEBUG_TOGGLE = 'nocompress'
        self.css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" />
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" />"""
        self.css_node = CssCompressor(self.css)

        self.js = """\
<script src="/static/js/one.js" type="text/javascript"></script>
<script type="text/javascript">obj.value = "value";</script>"""
        self.js_node = JsCompressor(self.js)

    def assertEqualCollapsed(self, a, b):
        """
        assertEqual with internal newlines collapsed to single, and
        trailing whitespace removed.
        """
        collapse = lambda x: re.sub(r'\n+', '\n', x).rstrip()
        self.assertEqual(collapse(a), collapse(b))

    def assertEqualSplits(self, a, b):
        """
        assertEqual for splits, particularly ignoring the presence of
        a trailing newline on the content.
        """
        mangle = lambda split: [(x[0], x[1], x[2], x[3].rstrip()) for x in split]
        self.assertEqual(mangle(a), mangle(b))

    def test_css_split(self):
        out = [
            (
                SOURCE_FILE,
                os.path.join(settings.COMPRESS_ROOT, 'css', 'one.css'),
                'css/one.css', '<link rel="stylesheet" href="/static/css/one.css" type="text/css" />',
            ),
            (
                SOURCE_HUNK,
                'p { border:5px solid green;}',
                None,
                '<style type="text/css">p { border:5px solid green;}</style>',
            ),
            (
                SOURCE_FILE,
                os.path.join(settings.COMPRESS_ROOT, 'css', 'two.css'),
                'css/two.css',
                '<link rel="stylesheet" href="/static/css/two.css" type="text/css" />',
            ),
        ]
        split = self.css_node.split_contents()
        split = [(x[0], x[1], x[2], self.css_node.parser.elem_str(x[3])) for x in split]
        self.assertEqualSplits(split, out)

    def test_css_hunks(self):
        out = ['body { background:#990; }', 'p { border:5px solid green;}', 'body { color:#fff; }']
        self.assertEqual(out, list(self.css_node.hunks()))

    def test_css_output(self):
        out = 'body { background:#990; }\np { border:5px solid green;}\nbody { color:#fff; }'
        hunks = '\n'.join([h for h in self.css_node.hunks()])
        self.assertEqual(out, hunks)

    def test_css_mtimes(self):
        is_date = re.compile(r'^\d{10}[\.\d]+$')
        for date in self.css_node.mtimes:
            self.assertTrue(is_date.match(str(float(date))),
                "mtimes is returning something that doesn't look like a date: %s" % date)

    def test_css_return_if_off(self):
        settings.COMPRESS_ENABLED = False
        self.assertEqualCollapsed(self.css, self.css_node.output())

    def test_cachekey(self):
        is_cachekey = re.compile(r'\w{12}')
        self.assertTrue(is_cachekey.match(self.css_node.cachekey),
            "cachekey is returning something that doesn't look like r'\w{12}'")

    def test_css_return_if_on(self):
        output = css_tag('/static/CACHE/css/e41ba2cc6982.css')
        self.assertEqual(output, self.css_node.output().strip())

    def test_js_split(self):
        out = [
            (
                SOURCE_FILE,
                os.path.join(settings.COMPRESS_ROOT, 'js', 'one.js'),
                'js/one.js',
                '<script src="/static/js/one.js" type="text/javascript"></script>',
            ),
            (
                SOURCE_HUNK,
                'obj.value = "value";',
                None,
                '<script type="text/javascript">obj.value = "value";</script>',
            ),
        ]
        split = self.js_node.split_contents()
        split = [(x[0], x[1], x[2], self.js_node.parser.elem_str(x[3])) for x in split]
        self.assertEqualSplits(split, out)

    def test_js_hunks(self):
        out = ['obj = {};', 'obj.value = "value";']
        self.assertEqual(out, list(self.js_node.hunks()))

    def test_js_output(self):
        out = '<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, self.js_node.output())

    def test_js_override_url(self):
        self.js_node.context.update({'url': 'This is not a url, just a text'})
        out = '<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, self.js_node.output())

    def test_css_override_url(self):
        self.css_node.context.update({'url': 'This is not a url, just a text'})
        output = css_tag('/static/CACHE/css/e41ba2cc6982.css')
        self.assertEqual(output, self.css_node.output().strip())

    @override_settings(COMPRESS_PRECOMPILERS=(), COMPRESS_ENABLED=False)
    def test_js_return_if_off(self):
        self.assertEqualCollapsed(self.js, self.js_node.output())

    def test_js_return_if_on(self):
        output = '<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(output, self.js_node.output())

    @override_settings(COMPRESS_OUTPUT_DIR='custom')
    def test_custom_output_dir1(self):
        output = '<script type="text/javascript" src="/static/custom/js/066cd253eada.js"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())

    @override_settings(COMPRESS_OUTPUT_DIR='')
    def test_custom_output_dir2(self):
        output = '<script type="text/javascript" src="/static/js/066cd253eada.js"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())

    @override_settings(COMPRESS_OUTPUT_DIR='/custom/nested/')
    def test_custom_output_dir3(self):
        output = '<script type="text/javascript" src="/static/custom/nested/js/066cd253eada.js"></script>'
        self.assertEqual(output, JsCompressor(self.js).output())

    @override_settings(COMPRESS_PRECOMPILERS=(
        ('text/foobar', 'compressor.tests.test_base.TestPrecompiler'),
    ), COMPRESS_ENABLED=True)
    def test_precompiler_class_used(self):
        css = '<style type="text/foobar">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        output = make_soup(css_node.output('inline'))
        self.assertEqual(output.text, 'OUTPUT')

    @override_settings(COMPRESS_PRECOMPILERS=(
        ('text/foobar', 'compressor.tests.test_base.NonexistentFilter'),
    ), COMPRESS_ENABLED=True)
    def test_nonexistent_precompiler_class_error(self):
        css = '<style type="text/foobar">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        self.assertRaises(FilterDoesNotExist, css_node.output, 'inline')


class CssMediaTestCase(SimpleTestCase):
    def setUp(self):
        self.css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" media="screen">
<style type="text/css" media="print">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" media="all">
<style type="text/css">h1 { border:5px solid green;}</style>"""

    def test_css_output(self):
        css_node = CssCompressor(self.css)
        if six.PY3:
            links = make_soup(css_node.output()).find_all('link')
        else:
            links = make_soup(css_node.output()).findAll('link')
        media = ['screen', 'print', 'all', None]
        self.assertEqual(len(links), 4)
        self.assertEqual(media, [l.get('media', None) for l in links])

    def test_avoid_reordering_css(self):
        css = self.css + '<style type="text/css" media="print">p { border:10px solid red;}</style>'
        css_node = CssCompressor(css)
        media = ['screen', 'print', 'all', None, 'print']
        if six.PY3:
            links = make_soup(css_node.output()).find_all('link')
        else:
            links = make_soup(css_node.output()).findAll('link')
        self.assertEqual(media, [l.get('media', None) for l in links])

    @override_settings(COMPRESS_PRECOMPILERS=(
        ('text/foobar', 'python %s {infile} {outfile}' % os.path.join(test_dir, 'precompiler.py')),
    ), COMPRESS_ENABLED=False)
    def test_passthough_when_compress_disabled(self):
        css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" media="screen">
<link rel="stylesheet" href="/static/css/two.css" type="text/css" media="screen">
<style type="text/foobar" media="screen">h1 { border:5px solid green;}</style>"""
        css_node = CssCompressor(css)
        if six.PY3:
            output = make_soup(css_node.output()).find_all(['link', 'style'])
        else:
            output = make_soup(css_node.output()).findAll(['link', 'style'])
        self.assertEqual(['/static/css/one.css', '/static/css/two.css', None],
                         [l.get('href', None) for l in output])
        self.assertEqual(['screen', 'screen', 'screen'],
                         [l.get('media', None) for l in output])


class VerboseTestCase(CompressorTestCase):

    def setUp(self):
        super(VerboseTestCase, self).setUp()
        settings.COMPRESS_VERBOSE = True


class CacheBackendTestCase(CompressorTestCase):

    def test_correct_backend(self):
        from compressor.cache import cache
        self.assertEqual(cache.__class__, locmem.LocMemCache)

########NEW FILE########
__FILENAME__ = test_filters
from __future__ import with_statement, unicode_literals
import io
import os
import sys
import textwrap

from django.utils import six
from django.test import TestCase
from django.utils import unittest
from django.test.utils import override_settings

from compressor.cache import get_hashed_mtime, get_hashed_content
from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.utils import find_command
from compressor.filters.base import CompilerFilter
from compressor.filters.cssmin import CSSMinFilter
from compressor.filters.css_default import CssAbsoluteFilter
from compressor.filters.template import TemplateFilter
from compressor.filters.closure import ClosureCompilerFilter
from compressor.filters.csstidy import CSSTidyFilter
from compressor.filters.yuglify import YUglifyCSSFilter, YUglifyJSFilter
from compressor.filters.yui import YUICSSFilter, YUIJSFilter
from compressor.tests.test_base import test_dir


@unittest.skipIf(find_command(settings.COMPRESS_CSSTIDY_BINARY) is None,
                 'CSStidy binary %r not found' % settings.COMPRESS_CSSTIDY_BINARY)
class CssTidyTestCase(TestCase):
    def test_tidy(self):
        content = textwrap.dedent("""\
        /* Some comment */
        font,th,td,p{
        color: black;
        }
        """)
        ret = CSSTidyFilter(content).input()
        self.assertIsInstance(ret, six.text_type)
        self.assertEqual(
            "font,th,td,p{color:#000;}", CSSTidyFilter(content).input())


class PrecompilerTestCase(TestCase):
    def setUp(self):
        self.filename = os.path.join(test_dir, 'static/css/one.css')
        with io.open(self.filename, encoding=settings.FILE_CHARSET) as file:
            self.content = file.read()
        self.test_precompiler = os.path.join(test_dir, 'precompiler.py')

    def test_precompiler_infile_outfile(self):
        command = '%s %s -f {infile} -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=self.filename,
            charset=settings.FILE_CHARSET, command=command)
        self.assertEqual("body { color:#990; }", compiler.input())

    def test_precompiler_infile_stdout(self):
        command = '%s %s -f {infile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=None, charset=None, command=command)
        self.assertEqual("body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_stdin_outfile(self):
        command = '%s %s -o {outfile}' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=None, charset=None, command=command)
        self.assertEqual("body { color:#990; }", compiler.input())

    def test_precompiler_stdin_stdout(self):
        command = '%s %s' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=None, charset=None, command=command)
        self.assertEqual("body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_stdin_stdout_filename(self):
        command = '%s %s' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(
            content=self.content, filename=self.filename,
            charset=settings.FILE_CHARSET, command=command)
        self.assertEqual("body { color:#990; }%s" % os.linesep, compiler.input())

    def test_precompiler_output_unicode(self):
        command = '%s %s' % (sys.executable, self.test_precompiler)
        compiler = CompilerFilter(content=self.content, filename=self.filename, command=command)
        self.assertEqual(type(compiler.input()), six.text_type)


class CssMinTestCase(TestCase):
    def test_cssmin_filter(self):
        content = """p {


        background: rgb(51,102,153) url('../../images/image.gif');


        }
        """
        output = "p{background:#369 url('../../images/image.gif')}"
        self.assertEqual(output, CSSMinFilter(content).output())


class CssAbsolutizingTestCase(TestCase):
    hashing_method = 'mtime'
    hashing_func = staticmethod(get_hashed_mtime)
    content = ("p { background: url('../../img/python.png') }"
               "p { filter: Alpha(src='../../img/python.png') }")

    def setUp(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        self.old_url = settings.COMPRESS_URL
        self.old_hashing_method = settings.COMPRESS_CSS_HASHING_METHOD
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_URL = '/static/'
        settings.COMPRESS_CSS_HASHING_METHOD = self.hashing_method
        self.css = """
        <link rel="stylesheet" href="/static/css/url/url1.css" type="text/css">
        <link rel="stylesheet" href="/static/css/url/2/url2.css" type="text/css">
        """
        self.css_node = CssCompressor(self.css)

    def tearDown(self):
        settings.COMPRESS_ENABLED = self.old_enabled
        settings.COMPRESS_URL = self.old_url
        settings.COMPRESS_CSS_HASHING_METHOD = self.old_hashing_method

    def test_css_no_hash(self):
        settings.COMPRESS_CSS_HASHING_METHOD = None
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        params = {
            'url': settings.COMPRESS_URL,
        }
        output = ("p { background: url('%(url)simg/python.png') }"
                  "p { filter: Alpha(src='%(url)simg/python.png') }") % params
        filter = CssAbsoluteFilter(self.content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        settings.COMPRESS_URL = params['url'] = 'http://static.example.com/'
        filter = CssAbsoluteFilter(self.content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = ("p { background: url('%(url)simg/python.png') }"
                  "p { filter: Alpha(src='%(url)simg/python.png') }") % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        filter = CssAbsoluteFilter(self.content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        settings.COMPRESS_URL = params['url'] = 'http://static.example.com/'
        filter = CssAbsoluteFilter(self.content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_url_fragment(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        content = "p { background: url('../../img/python.png#foo') }"

        output = "p { background: url('%(url)simg/python.png?%(hash)s#foo') }" % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        settings.COMPRESS_URL = params['url'] = 'http://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%(url)simg/python.png?%(hash)s#foo') }" % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_only_url_fragment(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        content = "p { background: url('#foo') }"
        filter = CssAbsoluteFilter(content)
        self.assertEqual(content, filter.input(filename=filename, basename='css/url/test.css'))

        settings.COMPRESS_URL = 'http://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        self.assertEqual(content, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_querystring(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        content = "p { background: url('../../img/python.png?foo') }"

        output = "p { background: url('%(url)simg/python.png?foo&%(hash)s') }" % params
        filter = CssAbsoluteFilter(content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        settings.COMPRESS_URL = params['url'] = 'http://media.example.com/'
        filter = CssAbsoluteFilter(content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = "p { background: url('%(url)simg/python.png?foo&%(hash)s') }" % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_https(self):
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        filter = CssAbsoluteFilter(self.content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        settings.COMPRESS_URL = params['url'] = 'https://static.example.com/'
        filter = CssAbsoluteFilter(self.content)
        filename = os.path.join(settings.COMPRESS_ROOT, 'css/url/test.css')
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_absolute_filter_relative_path(self):
        filename = os.path.join(settings.TEST_DIR, 'whatever', '..', 'static', 'whatever/../css/url/test.css')
        imagefilename = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
        params = {
            'url': settings.COMPRESS_URL,
            'hash': self.hashing_func(imagefilename),
        }
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        filter = CssAbsoluteFilter(self.content)
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

        settings.COMPRESS_URL = params['url'] = 'https://static.example.com/'
        filter = CssAbsoluteFilter(self.content)
        output = ("p { background: url('%(url)simg/python.png?%(hash)s') }"
                  "p { filter: Alpha(src='%(url)simg/python.png?%(hash)s') }") % params
        self.assertEqual(output, filter.input(filename=filename, basename='css/url/test.css'))

    def test_css_hunks(self):
        hash_dict = {
            'hash1': self.hashing_func(os.path.join(settings.COMPRESS_ROOT, 'img/python.png')),
            'hash2': self.hashing_func(os.path.join(settings.COMPRESS_ROOT, 'img/add.png')),
        }
        self.assertEqual(["""\
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { background: url('/static/img/python.png?%(hash1)s'); }
p { filter: progid:DXImageTransform.Microsoft.AlphaImageLoader(src='/static/img/python.png?%(hash1)s'); }
""" % hash_dict,
               """\
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { background: url('/static/img/add.png?%(hash2)s'); }
p { filter: progid:DXImageTransform.Microsoft.AlphaImageLoader(src='/static/img/add.png?%(hash2)s'); }
""" % hash_dict], list(self.css_node.hunks()))

    def test_guess_filename(self):
        for base_url in ('/static/', 'http://static.example.com/'):
            settings.COMPRESS_URL = base_url
            url = '%s/img/python.png' % settings.COMPRESS_URL.rstrip('/')
            path = os.path.join(settings.COMPRESS_ROOT, 'img/python.png')
            content = "p { background: url('%s') }" % url
            filter = CssAbsoluteFilter(content)
            self.assertEqual(path, filter.guess_filename(url))


class CssAbsolutizingTestCaseWithHash(CssAbsolutizingTestCase):
    hashing_method = 'content'
    hashing_func = staticmethod(get_hashed_content)


class CssDataUriTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_CSS_FILTERS = [
            'compressor.filters.css_default.CssAbsoluteFilter',
            'compressor.filters.datauri.CssDataUriFilter',
        ]
        settings.COMPRESS_URL = '/static/'
        settings.COMPRESS_CSS_HASHING_METHOD = 'mtime'
        self.css = """
        <link rel="stylesheet" href="/static/css/datauri.css" type="text/css">
        """
        self.css_node = CssCompressor(self.css)

    def test_data_uris(self):
        datauri_hash = get_hashed_mtime(os.path.join(settings.COMPRESS_ROOT, 'img/python.png'))
        out = ['''.add { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }
.add-with-hash { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAAK/INwWK6QAAABl0RVh0U29mdHdhcmUAQWRvYmUgSW1hZ2VSZWFkeXHJZTwAAAJvSURBVDjLpZPrS5NhGIf9W7YvBYOkhlkoqCklWChv2WyKik7blnNris72bi6dus0DLZ0TDxW1odtopDs4D8MDZuLU0kXq61CijSIIasOvv94VTUfLiB74fXngup7nvrnvJABJ/5PfLnTTdcwOj4RsdYmo5glBWP6iOtzwvIKSWstI0Wgx80SBblpKtE9KQs/We7EaWoT/8wbWP61gMmCH0lMDvokT4j25TiQU/ITFkek9Ow6+7WH2gwsmahCPdwyw75uw9HEO2gUZSkfyI9zBPCJOoJ2SMmg46N61YO/rNoa39Xi41oFuXysMfh36/Fp0b7bAfWAH6RGi0HglWNCbzYgJaFjRv6zGuy+b9It96N3SQvNKiV9HvSaDfFEIxXItnPs23BzJQd6DDEVM0OKsoVwBG/1VMzpXVWhbkUM2K4oJBDYuGmbKIJ0qxsAbHfRLzbjcnUbFBIpx/qH3vQv9b3U03IQ/HfFkERTzfFj8w8jSpR7GBE123uFEYAzaDRIqX/2JAtJbDat/COkd7CNBva2cMvq0MGxp0PRSCPF8BXjWG3FgNHc9XPT71Ojy3sMFdfJRCeKxEsVtKwFHwALZfCUk3tIfNR8XiJwc1LmL4dg141JPKtj3WUdNFJqLGFVPC4OkR4BxajTWsChY64wmCnMxsWPCHcutKBxMVp5mxA1S+aMComToaqTRUQknLTH62kHOVEE+VQnjahscNCy0cMBWsSI0TCQcZc5ALkEYckL5A5noWSBhfm2AecMAjbcRWV0pUTh0HE64TNf0mczcnnQyu/MilaFJCae1nw2fbz1DnVOxyGTlKeZft/Ff8x1BRssfACjTwQAAAABJRU5ErkJggg=="); }
.python { background-image: url("/static/img/python.png?%s"); }
.datauri { background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9YGARc5KB0XV+IAAAAddEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIFRoZSBHSU1Q72QlbgAAAF1JREFUGNO9zL0NglAAxPEfdLTs4BZM4DIO4C7OwQg2JoQ9LE1exdlYvBBeZ7jqch9//q1uH4TLzw4d6+ErXMMcXuHWxId3KOETnnXXV6MJpcq2MLaI97CER3N0 vr4MkhoXe0rZigAAAABJRU5ErkJggg=="); }
''' % datauri_hash]
        self.assertEqual(out, list(self.css_node.hunks()))


class TemplateTestCase(TestCase):
    @override_settings(COMPRESS_TEMPLATE_FILTER_CONTEXT={
        'stuff': 'thing',
        'gimmick': 'bold'
    })
    def test_template_filter(self):
        content = """
        #content {background-image: url("{{ STATIC_URL|default:stuff }}/images/bg.png");}
        #footer {font-weight: {{ gimmick }};}
        """
        input = """
        #content {background-image: url("thing/images/bg.png");}
        #footer {font-weight: bold;}
        """
        self.assertEqual(input, TemplateFilter(content).input())


class SpecializedFiltersTest(TestCase):
    """
    Test to check the Specializations of filters.
    """
    def test_closure_filter(self):
        filter = ClosureCompilerFilter('')
        self.assertEqual(filter.options, (('binary', six.text_type('java -jar compiler.jar')), ('args', six.text_type(''))))

    def test_csstidy_filter(self):
        filter = CSSTidyFilter('')
        self.assertEqual(filter.options, (('binary', six.text_type('csstidy')), ('args', six.text_type('--template=highest'))))

    def test_yuglify_filters(self):
        filter = YUglifyCSSFilter('')
        self.assertEqual(filter.command, '{binary} {args} --type=css')
        self.assertEqual(filter.options, (('binary', six.text_type('yuglify')), ('args', six.text_type('--terminal'))))

        filter = YUglifyJSFilter('')
        self.assertEqual(filter.command, '{binary} {args} --type=js')
        self.assertEqual(filter.options, (('binary', six.text_type('yuglify')), ('args', six.text_type('--terminal'))))

    def test_yui_filters(self):
        filter = YUICSSFilter('')
        self.assertEqual(filter.command, '{binary} {args} --type=css')
        self.assertEqual(filter.options, (('binary', six.text_type('java -jar yuicompressor.jar')), ('args', six.text_type(''))))

        filter = YUIJSFilter('', verbose=1)
        self.assertEqual(filter.command, '{binary} {args} --type=js --verbose')
        self.assertEqual(filter.options, (('binary', six.text_type('java -jar yuicompressor.jar')), ('args', six.text_type('')), ('verbose', 1)))

########NEW FILE########
__FILENAME__ = test_jinja2ext
# -*- coding: utf-8 -*-
from __future__ import with_statement, unicode_literals

import sys

from django.test import TestCase
from django.utils import unittest, six
from django.test.utils import override_settings

from compressor.conf import settings
from compressor.tests.test_base import css_tag


@unittest.skipUnless(not six.PY3 or sys.version_info[:2] >= (3, 3),
                     'Jinja can only run on Python < 3 and >= 3.3')
class TestJinja2CompressorExtension(TestCase):
    """
    Test case for jinja2 extension.

    .. note::
       At tests we need to make some extra care about whitespace. Please note
       that we use jinja2 specific controls (*minus* character at block's
       beginning or end). For more information see jinja2 documentation.
    """
    def assertStrippedEqual(self, result, expected):
        self.assertEqual(result.strip(), expected.strip(), "%r != %r" % (
            result.strip(), expected.strip()))

    def setUp(self):
        import jinja2
        self.jinja2 = jinja2
        from compressor.contrib.jinja2ext import CompressorExtension
        self.env = self.jinja2.Environment(extensions=[CompressorExtension])

    def test_error_raised_if_no_arguments_given(self):
        self.assertRaises(self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress %}Foobar{% endcompress %}')

    def test_error_raised_if_wrong_kind_given(self):
        self.assertRaises(self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress foo %}Foobar{% endcompress %}')

    def test_error_raised_if_wrong_closing_kind_given(self):
        self.assertRaises(self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress js %}Foobar{% endcompress css %}')

    def test_error_raised_if_wrong_mode_given(self):
        self.assertRaises(self.jinja2.exceptions.TemplateSyntaxError,
            self.env.from_string, '{% compress css foo %}Foobar{% endcompress %}')

    @override_settings(COMPRESS_ENABLED=False)
    def test_compress_is_disabled(self):
        tag_body = '\n'.join([
            '<link rel="stylesheet" href="css/one.css" type="text/css" charset="utf-8">',
            '<style type="text/css">p { border:5px solid green;}</style>',
            '<link rel="stylesheet" href="css/two.css" type="text/css" charset="utf-8">',
        ])
        template_string = '{% compress css %}' + tag_body + '{% endcompress %}'
        template = self.env.from_string(template_string)
        self.assertEqual(tag_body, template.render())

        # Test with explicit kind
        template_string = '{% compress css %}' + tag_body + '{% endcompress css %}'
        template = self.env.from_string(template_string)
        self.assertEqual(tag_body, template.render())

    def test_empty_tag(self):
        template = self.env.from_string("""{% compress js %}{% block js %}
        {% endblock %}{% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        self.assertEqual('', template.render(context))

    def test_empty_tag_with_kind(self):
        template = self.env.from_string("""{% compress js %}{% block js %}
        {% endblock %}{% endcompress js %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        self.assertEqual('', template.render(context))

    def test_css_tag(self):
        template = self.env.from_string("""{% compress css -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        <link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css" charset="utf-8">
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/e41ba2cc6982.css")
        self.assertEqual(out, template.render(context))

    def test_nonascii_css_tag(self):
        template = self.env.from_string("""{% compress css -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/nonasc.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/799f6defe43c.css")
        self.assertEqual(out, template.render(context))

    def test_js_tag(self):
        template = self.env.from_string("""{% compress js -%}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_js_tag(self):
        template = self.env.from_string("""{% compress js -%}
        <script src="{{ STATIC_URL }}js/nonasc.js" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">var test_value = "\u2014";</script>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript" src="/static/CACHE/js/e214fe629b28.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_latin1_js_tag(self):
        template = self.env.from_string("""{% compress js -%}
        <script src="{{ STATIC_URL }}js/nonasc-latin1.js" type="text/javascript" charset="latin-1"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript" src="/static/CACHE/js/be9e078b5ca7.js"></script>'
        self.assertEqual(out, template.render(context))

    def test_css_inline(self):
        template = self.env.from_string("""{% compress css, inline -%}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css" charset="utf-8">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '\n'.join([
            '<style type="text/css">body { background:#990; }',
            'p { border:5px solid green;}</style>',
        ])
        self.assertEqual(out, template.render(context))

    def test_js_inline(self):
        template = self.env.from_string("""{% compress js, inline -%}
        <script src="{{ STATIC_URL }}js/one.js" type="text/css" type="text/javascript" charset="utf-8"></script>
        <script type="text/javascript" charset="utf-8">obj.value = "value";</script>
        {% endcompress %}""")
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = '<script type="text/javascript">obj={};obj.value="value";</script>'
        self.assertEqual(out, template.render(context))

    def test_nonascii_inline_css(self):
        org_COMPRESS_ENABLED = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = False
        template = self.env.from_string('{% compress css %}'
                                        '<style type="text/css">'
                                        '/* русский текст */'
                                        '</style>{% endcompress %}')
        out = '<link rel="stylesheet" href="/static/CACHE/css/b2cec0f8cb24.css" type="text/css" />'
        settings.COMPRESS_ENABLED = org_COMPRESS_ENABLED
        context = {'STATIC_URL': settings.COMPRESS_URL}
        self.assertEqual(out, template.render(context))

########NEW FILE########
__FILENAME__ = test_offline
from __future__ import with_statement, unicode_literals
import io
import os
import sys

from django.core.management.base import CommandError
from django.template import Template, Context
from django.test import TestCase
from django.utils import six, unittest

from compressor.cache import flush_offline_manifest, get_offline_manifest
from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.management.commands.compress import Command as CompressCommand
from compressor.storage import default_storage

if six.PY3:
    # there is an 'io' module in python 2.6+, but io.StringIO does not
    # accept regular strings, just unicode objects
    from io import StringIO
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

# The Jinja2 tests fail on Python 3.2 due to the following:
# The line in compressor/management/commands/compress.py:
#     compressor_nodes.setdefault(template, []).extend(nodes)
# causes the error "unhashable type: 'Template'"
_TEST_JINJA2 = not(sys.version_info[0] == 3 and sys.version_info[1] == 2)


class OfflineTestCaseMixin(object):
    template_name = "test_compressor_offline.html"
    verbosity = 0
    # Change this for each test class
    templates_dir = ""
    expected_hash = ""
    # Engines to test
    if _TEST_JINJA2:
        engines = ("django", "jinja2")
    else:
        engines = ("django",)

    def setUp(self):
        self._old_compress = settings.COMPRESS_ENABLED
        self._old_compress_offline = settings.COMPRESS_OFFLINE
        self._old_template_dirs = settings.TEMPLATE_DIRS
        self._old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        self.log = StringIO()

        # Reset template dirs, because it enables us to force compress to
        # consider only a specific directory (helps us make true,
        # independant unit tests).
        # Specify both Jinja2 and Django template locations. When the wrong engine
        # is used to parse a template, the TemplateSyntaxError will cause the
        # template to be skipped over.
        django_template_dir = os.path.join(settings.TEST_DIR, 'test_templates', self.templates_dir)
        jinja2_template_dir = os.path.join(settings.TEST_DIR, 'test_templates_jinja2', self.templates_dir)
        settings.TEMPLATE_DIRS = (django_template_dir, jinja2_template_dir)

        # Enable offline compress
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_OFFLINE = True

        if "django" in self.engines:
            self.template_path = os.path.join(django_template_dir, self.template_name)

            with io.open(self.template_path, encoding=settings.FILE_CHARSET) as file:
                self.template = Template(file.read())

        self._old_jinja2_get_environment = settings.COMPRESS_JINJA2_GET_ENVIRONMENT

        if "jinja2" in self.engines:
            # Setup Jinja2 settings.
            settings.COMPRESS_JINJA2_GET_ENVIRONMENT = lambda: self._get_jinja2_env()
            jinja2_env = settings.COMPRESS_JINJA2_GET_ENVIRONMENT()
            self.template_path_jinja2 = os.path.join(jinja2_template_dir, self.template_name)

            with io.open(self.template_path_jinja2, encoding=settings.FILE_CHARSET) as file:
                self.template_jinja2 = jinja2_env.from_string(file.read())

    def tearDown(self):
        settings.COMPRESS_JINJA2_GET_ENVIRONMENT = self._old_jinja2_get_environment
        settings.COMPRESS_ENABLED = self._old_compress
        settings.COMPRESS_OFFLINE = self._old_compress_offline
        settings.TEMPLATE_DIRS = self._old_template_dirs
        manifest_path = os.path.join('CACHE', 'manifest.json')
        if default_storage.exists(manifest_path):
            default_storage.delete(manifest_path)

    def _render_template(self, engine):
        if engine == "django":
            return self.template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        elif engine == "jinja2":
            return self.template_jinja2.render(settings.COMPRESS_OFFLINE_CONTEXT) + "\n"
        else:
            return None

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(1, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/%s.js"></script>' % (self.expected_hash, ),
        ], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, "".join(result) + "\n")

    def test_offline(self):
        for engine in self.engines:
            self._test_offline(engine=engine)

    def _get_jinja2_env(self):
        import jinja2
        import jinja2.ext
        from compressor.offline.jinja2 import url_for, SpacelessExtension
        from compressor.contrib.jinja2ext import CompressorExtension

        # Extensions needed for the test cases only.
        extensions = [
            CompressorExtension,
            SpacelessExtension,
            jinja2.ext.with_,
            jinja2.ext.do,
        ]
        loader = self._get_jinja2_loader()
        env = jinja2.Environment(extensions=extensions, loader=loader)
        env.globals['url_for'] = url_for

        return env

    def _get_jinja2_loader(self):
        import jinja2

        loader = jinja2.FileSystemLoader(settings.TEMPLATE_DIRS, encoding=settings.FILE_CHARSET)
        return loader


class OfflineGenerationSkipDuplicatesTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_duplicate"

    # We don't need to test multiples engines here.
    engines = ("django",)

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        # Only one block compressed, the second identical one was skipped.
        self.assertEqual(1, count)
        # Only 1 <script> block in returned result as well.
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/f5e179b8eca4.js"></script>',
        ], result)
        rendered_template = self._render_template(engine)
        # But rendering the template returns both (identical) scripts.
        self.assertEqual(rendered_template, "".join(result * 2) + "\n")


class OfflineGenerationBlockSuperTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super"
    expected_hash = "7c02d201f69d"
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)


class OfflineGenerationBlockSuperMultipleTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super_multiple"
    expected_hash = "f8891c416981"
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)


class OfflineGenerationBlockSuperMultipleWithCachedLoaderTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super_multiple_cached"
    expected_hash = "2f6ef61c488e"
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)

    def setUp(self):
        self._old_template_loaders = settings.TEMPLATE_LOADERS
        settings.TEMPLATE_LOADERS = (
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            )),
        )
        super(OfflineGenerationBlockSuperMultipleWithCachedLoaderTestCase, self).setUp()

    def tearDown(self):
        super(OfflineGenerationBlockSuperMultipleWithCachedLoaderTestCase, self).tearDown()
        settings.TEMPLATE_LOADERS = self._old_template_loaders


class OfflineGenerationBlockSuperTestCaseWithExtraContent(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_block_super_extra"
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(2, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/ced14aec5856.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/7c02d201f69d.js"></script>'
        ], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, "".join(result) + "\n")


class OfflineGenerationConditionTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_condition"
    expected_hash = "4e3758d50224"

    def setUp(self):
        self.old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'condition': 'red',
        }
        super(OfflineGenerationConditionTestCase, self).setUp()

    def tearDown(self):
        self.COMPRESS_OFFLINE_CONTEXT = self.old_offline_context
        super(OfflineGenerationConditionTestCase, self).tearDown()


class OfflineGenerationTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_templatetag"
    expected_hash = "a27e1d3a619a"


class OfflineGenerationStaticTemplateTagTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_static_templatetag"
    expected_hash = "dfa2bb387fa8"


class OfflineGenerationTestCaseWithContext(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_with_context"
    expected_hash = "5838e2fd66af"

    def setUp(self):
        self.old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'content': 'OK!',
        }
        super(OfflineGenerationTestCaseWithContext, self).setUp()

    def tearDown(self):
        settings.COMPRESS_OFFLINE_CONTEXT = self.old_offline_context
        super(OfflineGenerationTestCaseWithContext, self).tearDown()


class OfflineGenerationTestCaseErrors(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_error_handling"

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)

        if engine == "django":
            self.assertEqual(2, count)
        else:
            # Because we use env.parse in Jinja2Parser, the engine does not
            # actually load the "extends" and "includes" templates, and so
            # it is unable to detect that they are missing. So all the "compress"
            # nodes are processed correctly.
            self.assertEqual(4, count)
            self.assertEqual(engine, "jinja2")
            self.assertIn('<link rel="stylesheet" href="/static/CACHE/css/78bd7a762e2d.css" type="text/css" />', result)
            self.assertIn('<link rel="stylesheet" href="/static/CACHE/css/e31030430724.css" type="text/css" />', result)

        self.assertIn('<script type="text/javascript" src="/static/CACHE/js/3872c9ae3f42.js"></script>', result)
        self.assertIn('<script type="text/javascript" src="/static/CACHE/js/cd8870829421.js"></script>', result)


class OfflineGenerationTestCaseWithError(OfflineTestCaseMixin, TestCase):
    templates_dir = 'test_error_handling'

    def setUp(self):
        self._old_compress_precompilers = settings.COMPRESS_PRECOMPILERS
        settings.COMPRESS_PRECOMPILERS = (('text/coffeescript', 'non-existing-binary'),)
        super(OfflineGenerationTestCaseWithError, self).setUp()

    def _test_offline(self, engine):
        """
        Test that a CommandError is raised with DEBUG being False as well as
        True, as otherwise errors in configuration will never show in
        production.
        """
        self._old_debug = settings.DEBUG

        try:
            settings.DEBUG = True
            self.assertRaises(CommandError, CompressCommand().compress, engine=engine)

            settings.DEBUG = False
            self.assertRaises(CommandError, CompressCommand().compress, engine=engine)

        finally:
            settings.DEBUG = self._old_debug

    def tearDown(self):
        settings.COMPRESS_PRECOMPILERS = self._old_compress_precompilers
        super(OfflineGenerationTestCaseWithError, self).tearDown()


class OfflineGenerationTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "basic"
    expected_hash = "f5e179b8eca4"

    def test_rendering_without_manifest_raises_exception(self):
        # flush cached manifest
        flush_offline_manifest()
        self.assertRaises(OfflineGenerationError,
                          self.template.render, Context({}))

    @unittest.skipIf(not _TEST_JINJA2, "No Jinja2 testing")
    def test_rendering_without_manifest_raises_exception_jinja2(self):
        # flush cached manifest
        flush_offline_manifest()
        self.assertRaises(OfflineGenerationError,
                          self.template_jinja2.render, {})

    def _test_deleting_manifest_does_not_affect_rendering(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        get_offline_manifest()
        manifest_path = os.path.join('CACHE', 'manifest.json')
        if default_storage.exists(manifest_path):
            default_storage.delete(manifest_path)
        self.assertEqual(1, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/%s.js"></script>' % (self.expected_hash, ),
        ], result)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, "".join(result) + "\n")

    def test_deleting_manifest_does_not_affect_rendering(self):
        for engine in self.engines:
            self._test_deleting_manifest_does_not_affect_rendering(engine)

    def test_requires_model_validation(self):
        self.assertFalse(CompressCommand.requires_model_validation)

    def test_get_loaders(self):
        old_loaders = settings.TEMPLATE_LOADERS
        settings.TEMPLATE_LOADERS = (
            ('django.template.loaders.cached.Loader', (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            )),
        )
        try:
            from django.template.loaders.filesystem import Loader as FileSystemLoader
            from django.template.loaders.app_directories import Loader as AppDirectoriesLoader
        except ImportError:
            pass
        else:
            loaders = CompressCommand().get_loaders()
            self.assertTrue(isinstance(loaders[0], FileSystemLoader))
            self.assertTrue(isinstance(loaders[1], AppDirectoriesLoader))
        finally:
            settings.TEMPLATE_LOADERS = old_loaders


class OfflineGenerationBlockSuperBaseCompressed(OfflineTestCaseMixin, TestCase):
    template_names = ["base.html", "base2.html", "test_compressor_offline.html"]
    templates_dir = 'test_block_super_base_compressed'
    expected_hash = ['028c3fc42232', '2e9d3f5545a6', 'f8891c416981']
    # Block.super not supported for Jinja2 yet.
    engines = ("django",)

    def setUp(self):
        super(OfflineGenerationBlockSuperBaseCompressed, self).setUp()

        self.template_paths = []
        self.templates = []
        for template_name in self.template_names:
            template_path = os.path.join(settings.TEMPLATE_DIRS[0], template_name)
            self.template_paths.append(template_path)
            with io.open(template_path, encoding=settings.FILE_CHARSET) as file:
                template = Template(file.read())
            self.templates.append(template)

    def _render_template(self, template, engine):
        if engine == "django":
            return template.render(Context(settings.COMPRESS_OFFLINE_CONTEXT))
        elif engine == "jinja2":
            return template.render(settings.COMPRESS_OFFLINE_CONTEXT) + "\n"
        else:
            return None

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(len(self.expected_hash), count)
        for expected_hash, template in zip(self.expected_hash, self.templates):
            expected_output = '<script type="text/javascript" src="/static/CACHE/js/%s.js"></script>' % (expected_hash, )
            self.assertIn(expected_output, result)
            rendered_template = self._render_template(template, engine)
            self.assertEqual(rendered_template, expected_output + '\n')


class OfflineGenerationInlineNonAsciiTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_inline_non_ascii"

    def setUp(self):
        self.old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'test_non_ascii_value': '\u2014',
        }
        super(OfflineGenerationInlineNonAsciiTestCase, self).setUp()

    def tearDown(self):
        self.COMPRESS_OFFLINE_CONTEXT = self.old_offline_context
        super(OfflineGenerationInlineNonAsciiTestCase, self).tearDown()

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        rendered_template = self._render_template(engine)
        self.assertEqual(rendered_template, "".join(result) + "\n")


class OfflineGenerationComplexTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_complex"

    def setUp(self):
        self.old_offline_context = settings.COMPRESS_OFFLINE_CONTEXT
        settings.COMPRESS_OFFLINE_CONTEXT = {
            'condition': 'OK!',
            # Django templating does not allow definition of tuples in the
            # templates. Make sure this is same as test_templates_jinja2/test_complex.
            'my_names': ("js/one.js", "js/nonasc.js"),
        }
        super(OfflineGenerationComplexTestCase, self).setUp()

    def tearDown(self):
        self.COMPRESS_OFFLINE_CONTEXT = self.old_offline_context
        super(OfflineGenerationComplexTestCase, self).tearDown()

    def _test_offline(self, engine):
        count, result = CompressCommand().compress(log=self.log, verbosity=self.verbosity, engine=engine)
        self.assertEqual(3, count)
        self.assertEqual([
            '<script type="text/javascript" src="/static/CACHE/js/0e8807bebcee.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/eed1d222933e.js"></script>',
            '<script type="text/javascript" src="/static/CACHE/js/00b4baffe335.js"></script>',
        ], result)
        rendered_template = self._render_template(engine)
        result = (result[0], result[2])
        self.assertEqual(rendered_template, "".join(result) + "\n")


# Coffin does not work on Python 3.2+ due to:
# The line at coffin/template/__init__.py:15
#     from library import *
# causing 'ImportError: No module named library'.
# It seems there is no evidence nor indicated support for Python 3+.
@unittest.skipIf(sys.version_info >= (3, 2),
    "Coffin does not support 3.2+")
class OfflineGenerationCoffinTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_coffin"
    expected_hash = "32c8281e3346"
    engines = ("jinja2",)

    def _get_jinja2_env(self):
        import jinja2
        from coffin.common import env
        from compressor.contrib.jinja2ext import CompressorExtension

        # Could have used the env.add_extension method, but it's only available
        # in Jinja2 v2.5
        new_env = jinja2.Environment(extensions=[CompressorExtension])
        env.extensions.update(new_env.extensions)

        return env


# Jingo does not work when using Python 3.2 due to the use of Unicode string
# prefix (and possibly other stuff), but it actually works when using Python 3.3
# since it tolerates the use of the Unicode string prefix. Python 3.3 support
# is also evident in its tox.ini file.
@unittest.skipIf(sys.version_info >= (3, 2) and sys.version_info < (3, 3),
    "Jingo does not support 3.2")
class OfflineGenerationJingoTestCase(OfflineTestCaseMixin, TestCase):
    templates_dir = "test_jingo"
    expected_hash = "61ec584468eb"
    engines = ("jinja2",)

    def _get_jinja2_env(self):
        import jinja2
        import jinja2.ext
        from jingo import env
        from compressor.contrib.jinja2ext import CompressorExtension
        from compressor.offline.jinja2 import SpacelessExtension, url_for

        # Could have used the env.add_extension method, but it's only available
        # in Jinja2 v2.5
        new_env = jinja2.Environment(extensions=[CompressorExtension, SpacelessExtension, jinja2.ext.with_])
        env.extensions.update(new_env.extensions)
        env.globals['url_for'] = url_for

        return env

########NEW FILE########
__FILENAME__ = test_parsers
from __future__ import with_statement
import os

try:
    import lxml
except ImportError:
    lxml = None

try:
    import html5lib
except ImportError:
    html5lib = None

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from django.utils import unittest
from django.test.utils import override_settings

from compressor.base import SOURCE_HUNK, SOURCE_FILE
from compressor.conf import settings
from compressor.tests.test_base import CompressorTestCase


class ParserTestCase(object):
    def setUp(self):
        self.old_parser = settings.COMPRESS_PARSER
        settings.COMPRESS_PARSER = self.parser_cls
        super(ParserTestCase, self).setUp()

    def tearDown(self):
        settings.COMPRESS_PARSER = self.old_parser


@unittest.skipIf(lxml is None, 'lxml not found')
class LxmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.LxmlParser'


@unittest.skipIf(html5lib is None, 'html5lib not found')
class Html5LibParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.Html5LibParser'
    # Special test variants required since xml.etree holds attributes
    # as a plain dictionary, e.g. key order is unpredictable.

    def test_css_split(self):
        split = self.css_node.split_contents()
        out0 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, 'css', 'one.css'),
            'css/one.css',
            '{http://www.w3.org/1999/xhtml}link',
            {'rel': 'stylesheet', 'href': '/static/css/one.css',
             'type': 'text/css'},
        )
        self.assertEqual(out0, split[0][:3] + (split[0][3].tag,
                                               split[0][3].attrib))
        out1 = (
            SOURCE_HUNK,
            'p { border:5px solid green;}',
            None,
            '<style type="text/css">p { border:5px solid green;}</style>',
        )
        self.assertEqual(out1, split[1][:3] +
                         (self.css_node.parser.elem_str(split[1][3]),))
        out2 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, 'css', 'two.css'),
            'css/two.css',
            '{http://www.w3.org/1999/xhtml}link',
            {'rel': 'stylesheet', 'href': '/static/css/two.css',
             'type': 'text/css'},
        )
        self.assertEqual(out2, split[2][:3] + (split[2][3].tag,
                                               split[2][3].attrib))

    def test_js_split(self):
        split = self.js_node.split_contents()
        out0 = (
            SOURCE_FILE,
            os.path.join(settings.COMPRESS_ROOT, 'js', 'one.js'),
            'js/one.js',
            '{http://www.w3.org/1999/xhtml}script',
            {'src': '/static/js/one.js', 'type': 'text/javascript'},
            None,
        )
        self.assertEqual(out0, split[0][:3] + (split[0][3].tag,
                                               split[0][3].attrib,
                                               split[0][3].text))
        out1 = (
            SOURCE_HUNK,
            'obj.value = "value";',
            None,
            '{http://www.w3.org/1999/xhtml}script',
            {'type': 'text/javascript'},
            'obj.value = "value";',
        )
        self.assertEqual(out1, split[1][:3] + (split[1][3].tag,
                                               split[1][3].attrib,
                                               split[1][3].text))

    def test_css_return_if_off(self):
        settings.COMPRESS_ENABLED = False
        # Yes, they are semantically equal but attributes might be
        # scrambled in unpredictable order. A more elaborate check
        # would require parsing both arguments with a different parser
        # and then evaluating the result, which no longer is
        # a meaningful unit test.
        self.assertEqual(len(self.css), len(self.css_node.output()))

    @override_settings(COMPRESS_PRECOMPILERS=(), COMPRESS_ENABLED=False)
    def test_js_return_if_off(self):
        # As above.
        self.assertEqual(len(self.js), len(self.js_node.output()))


@unittest.skipIf(BeautifulSoup is None, 'BeautifulSoup not found')
class BeautifulSoupParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.BeautifulSoupParser'


class HtmlParserTests(ParserTestCase, CompressorTestCase):
    parser_cls = 'compressor.parser.HtmlParser'

########NEW FILE########
__FILENAME__ = test_signals
from django.test import TestCase

from mock import Mock

from compressor.conf import settings
from compressor.css import CssCompressor
from compressor.js import JsCompressor
from compressor.signals import post_compress


class PostCompressSignalTestCase(TestCase):
    def setUp(self):
        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = ()
        settings.COMPRESS_DEBUG_TOGGLE = 'nocompress'
        self.css = """\
<link rel="stylesheet" href="/static/css/one.css" type="text/css" />
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" />"""
        self.css_node = CssCompressor(self.css)

        self.js = """\
<script src="/static/js/one.js" type="text/javascript"></script>
<script type="text/javascript">obj.value = "value";</script>"""
        self.js_node = JsCompressor(self.js)

    def tearDown(self):
        post_compress.disconnect()

    def test_js_signal_sent(self):
        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        self.js_node.output()
        args, kwargs = callback.call_args
        self.assertEqual(JsCompressor, kwargs['sender'])
        self.assertEqual('js', kwargs['type'])
        self.assertEqual('file', kwargs['mode'])
        context = kwargs['context']
        assert 'url' in context['compressed']

    def test_css_signal_sent(self):
        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        self.css_node.output()
        args, kwargs = callback.call_args
        self.assertEqual(CssCompressor, kwargs['sender'])
        self.assertEqual('css', kwargs['type'])
        self.assertEqual('file', kwargs['mode'])
        context = kwargs['context']
        assert 'url' in context['compressed']

    def test_css_signal_multiple_media_attributes(self):
        css = """\
<link rel="stylesheet" href="/static/css/one.css" media="handheld" type="text/css" />
<style type="text/css" media="print">p { border:5px solid green;}</style>
<link rel="stylesheet" href="/static/css/two.css" type="text/css" />"""
        css_node = CssCompressor(css)

        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        css_node.output()
        self.assertEqual(3, callback.call_count)

########NEW FILE########
__FILENAME__ = test_storages
from __future__ import with_statement, unicode_literals
import errno
import os

from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.test import TestCase
from django.utils.functional import LazyObject

from compressor import storage
from compressor.conf import settings
from compressor.tests.test_base import css_tag
from compressor.tests.test_templatetags import render


class GzipStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class('compressor.storage.GzipCompressorFileStorage')()


class StorageTestCase(TestCase):
    def setUp(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = True
        self.default_storage = storage.default_storage
        storage.default_storage = GzipStorage()

    def tearDown(self):
        storage.default_storage = self.default_storage
        settings.COMPRESS_ENABLED = self.old_enabled

    def test_gzip_storage(self):
        storage.default_storage.save('test.txt', ContentFile('yeah yeah'))
        self.assertTrue(os.path.exists(os.path.join(settings.COMPRESS_ROOT, 'test.txt')))
        self.assertTrue(os.path.exists(os.path.join(settings.COMPRESS_ROOT, 'test.txt.gz')))

    def test_css_tag_with_storage(self):
        template = """{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
        <style type="text/css">p { border:5px solid white;}</style>
        <link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
        {% endcompress %}
        """
        context = {'STATIC_URL': settings.COMPRESS_URL}
        out = css_tag("/static/CACHE/css/1d4424458f88.css")
        self.assertEqual(out, render(template, context))

    def test_race_condition_handling(self):
        # Hold on to original os.remove
        original_remove = os.remove

        def race_remove(path):
            "Patched os.remove to raise ENOENT (No such file or directory)"
            original_remove(path)
            raise OSError(errno.ENOENT, 'Fake ENOENT')

        try:
            os.remove = race_remove
            self.default_storage.save('race.file', ContentFile('Fake ENOENT'))
            self.default_storage.delete('race.file')
            self.assertFalse(self.default_storage.exists('race.file'))
        finally:
            # Restore os.remove
            os.remove = original_remove

########NEW FILE########
__FILENAME__ = test_templatetags
from __future__ import with_statement, unicode_literals

import os
import sys

from mock import Mock

from django.template import Template, Context, TemplateSyntaxError
from django.test import TestCase
from django.test.utils import override_settings

from compressor.conf import settings
from compressor.signals import post_compress
from compressor.tests.test_base import css_tag, test_dir


def render(template_string, context_dict=None):
    """
    A shortcut for testing template output.
    """
    if context_dict is None:
        context_dict = {}
    c = Context(context_dict)
    t = Template(template_string)
    return t.render(c).strip()


class TemplatetagTestCase(TestCase):
    def setUp(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        settings.COMPRESS_ENABLED = True
        self.context = {'STATIC_URL': settings.COMPRESS_URL}

    def tearDown(self):
        settings.COMPRESS_ENABLED = self.old_enabled

    def test_empty_tag(self):
        template = """{% load compress %}{% compress js %}{% block js %}
        {% endblock %}{% endcompress %}"""
        self.assertEqual('', render(template, self.context))

    def test_css_tag(self):
        template = """{% load compress %}{% compress css %}
<link rel="stylesheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="stylesheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
{% endcompress %}"""
        out = css_tag("/static/CACHE/css/e41ba2cc6982.css")
        self.assertEqual(out, render(template, self.context))

    def test_uppercase_rel(self):
        template = """{% load compress %}{% compress css %}
<link rel="StyleSheet" href="{{ STATIC_URL }}css/one.css" type="text/css">
<style type="text/css">p { border:5px solid green;}</style>
<link rel="StyleSheet" href="{{ STATIC_URL }}css/two.css" type="text/css">
{% endcompress %}"""
        out = css_tag("/static/CACHE/css/e41ba2cc6982.css")
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_css_tag(self):
        template = """{% load compress %}{% compress css %}
        <link rel="stylesheet" href="{{ STATIC_URL }}css/nonasc.css" type="text/css">
        <style type="text/css">p { border:5px solid green;}</style>
        {% endcompress %}
        """
        out = css_tag("/static/CACHE/css/799f6defe43c.css")
        self.assertEqual(out, render(template, self.context))

    def test_js_tag(self):
        template = """{% load compress %}{% compress js %}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}
        """
        out = '<script type="text/javascript" src="/static/CACHE/js/066cd253eada.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_js_tag(self):
        template = """{% load compress %}{% compress js %}
        <script src="{{ STATIC_URL }}js/nonasc.js" type="text/javascript"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        out = '<script type="text/javascript" src="/static/CACHE/js/e214fe629b28.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_nonascii_latin1_js_tag(self):
        template = """{% load compress %}{% compress js %}
        <script src="{{ STATIC_URL }}js/nonasc-latin1.js" type="text/javascript" charset="latin-1"></script>
        <script type="text/javascript">var test_value = "\u2014";</script>
        {% endcompress %}
        """
        out = '<script type="text/javascript" src="/static/CACHE/js/be9e078b5ca7.js"></script>'
        self.assertEqual(out, render(template, self.context))

    def test_compress_tag_with_illegal_arguments(self):
        template = """{% load compress %}{% compress pony %}
        <script type="pony/application">unicorn</script>
        {% endcompress %}"""
        self.assertRaises(TemplateSyntaxError, render, template, {})

    @override_settings(COMPRESS_DEBUG_TOGGLE='togglecompress')
    def test_debug_toggle(self):
        template = """{% load compress %}{% compress js %}
        <script src="{{ STATIC_URL }}js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}
        """

        class MockDebugRequest(object):
            GET = {settings.COMPRESS_DEBUG_TOGGLE: 'true'}

        context = dict(self.context, request=MockDebugRequest())
        out = """<script src="/static/js/one.js" type="text/javascript"></script>
        <script type="text/javascript">obj.value = "value";</script>"""
        self.assertEqual(out, render(template, context))

    def test_named_compress_tag(self):
        template = """{% load compress %}{% compress js inline foo %}
        <script type="text/javascript">obj.value = "value";</script>
        {% endcompress %}
        """

        def listener(sender, **kwargs):
            pass
        callback = Mock(wraps=listener)
        post_compress.connect(callback)
        render(template)
        args, kwargs = callback.call_args
        context = kwargs['context']
        self.assertEqual('foo', context['compressed']['name'])


class PrecompilerTemplatetagTestCase(TestCase):
    def setUp(self):
        self.old_enabled = settings.COMPRESS_ENABLED
        self.old_precompilers = settings.COMPRESS_PRECOMPILERS

        precompiler = os.path.join(test_dir, 'precompiler.py')
        python = sys.executable

        settings.COMPRESS_ENABLED = True
        settings.COMPRESS_PRECOMPILERS = (
            ('text/coffeescript', '%s %s' % (python, precompiler)),
            ('text/less', '%s %s' % (python, precompiler)),
        )
        self.context = {'STATIC_URL': settings.COMPRESS_URL}

    def tearDown(self):
        settings.COMPRESS_ENABLED = self.old_enabled
        settings.COMPRESS_PRECOMPILERS = self.old_precompilers

    def test_compress_coffeescript_tag(self):
        template = """{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            {% endcompress %}"""
        out = script(src="/static/CACHE/js/e920d58f166d.js")
        self.assertEqual(out, render(template, self.context))

    def test_compress_coffeescript_tag_and_javascript_tag(self):
        template = """{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            <script type="text/javascript"># this too is a comment.</script>
            {% endcompress %}"""
        out = script(src="/static/CACHE/js/ef6b32a54575.js")
        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_coffeescript_and_js_tag_with_compress_enabled_equals_false(self):
        template = """{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            <script type="text/javascript"># this too is a comment.</script>
            {% endcompress %}"""
        out = (script('# this is a comment.\n') + '\n' +
               script('# this too is a comment.'))
        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_compress_coffeescript_tag_compress_enabled_is_false(self):
        template = """{% load compress %}{% compress js %}
            <script type="text/coffeescript"># this is a comment.</script>
            {% endcompress %}"""
        out = script("# this is a comment.\n")
        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_compress_coffeescript_file_tag_compress_enabled_is_false(self):
        template = """
        {% load compress %}{% compress js %}
        <script type="text/coffeescript" src="{{ STATIC_URL }}js/one.coffee">
        </script>
        {% endcompress %}"""

        out = script(src="/static/CACHE/js/one.95cfb869eead.js")
        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_multiple_file_order_conserved(self):
        template = """
        {% load compress %}{% compress js %}
        <script type="text/coffeescript" src="{{ STATIC_URL }}js/one.coffee">
        </script>
        <script src="{{ STATIC_URL }}js/one.js"></script>
        <script type="text/coffeescript" src="{{ STATIC_URL }}js/one.js">
        </script>
        {% endcompress %}"""

        out = '\n'.join([script(src="/static/CACHE/js/one.95cfb869eead.js"),
                         script(scripttype="", src="/static/js/one.js"),
                         script(src="/static/CACHE/js/one.81a2cd965815.js")])

        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_css_multiple_files_disabled_compression(self):
        assert(settings.COMPRESS_PRECOMPILERS)
        template = """
        {% load compress %}{% compress css %}
        <link rel="stylesheet" type="text/css" href="{{ STATIC_URL }}css/one.css"></link>
        <link rel="stylesheet" type="text/css" href="{{ STATIC_URL }}css/two.css"></link>
        {% endcompress %}"""

        out = ''.join(['<link rel="stylesheet" type="text/css" href="/static/css/one.css" />',
                       '<link rel="stylesheet" type="text/css" href="/static/css/two.css" />'])

        self.assertEqual(out, render(template, self.context))

    @override_settings(COMPRESS_ENABLED=False)
    def test_css_multiple_files_mixed_precompile_disabled_compression(self):
        assert(settings.COMPRESS_PRECOMPILERS)
        template = """
        {% load compress %}{% compress css %}
        <link rel="stylesheet" type="text/css" href="{{ STATIC_URL }}css/one.css"/>
        <link rel="stylesheet" type="text/css" href="{{ STATIC_URL }}css/two.css"/>
        <link rel="stylesheet" type="text/less" href="{{ STATIC_URL }}css/url/test.css"/>
        {% endcompress %}"""

        out = ''.join(['<link rel="stylesheet" type="text/css" href="/static/css/one.css" />',
                       '<link rel="stylesheet" type="text/css" href="/static/css/two.css" />',
                       '<link rel="stylesheet" href="/static/CACHE/css/test.5dddc6c2fb5a.css" type="text/css" />'])
        self.assertEqual(out, render(template, self.context))


def script(content="", src="", scripttype="text/javascript"):
    """
    returns a unicode text html script element.

    >>> script('#this is a comment', scripttype="text/applescript")
    '<script type="text/applescript">#this is a comment</script>'
    """
    out_script = '<script '
    if scripttype:
        out_script += 'type="%s" ' % scripttype
    if src:
        out_script += 'src="%s" ' % src
    return out_script[:-1] + '>%s</script>' % content

########NEW FILE########
__FILENAME__ = test_settings
import os
import django

TEST_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tests')

COMPRESS_CACHE_BACKEND = 'django.core.cache.backends.locmem.LocMemCache'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'compressor',
    'coffin',
    'jingo',
]

STATIC_URL = '/static/'


STATIC_ROOT = os.path.join(TEST_DIR, 'static')

TEMPLATE_DIRS = (
    # Specifically choose a name that will not be considered
    # by app_directories loader, to make sure each test uses
    # a specific template without considering the others.
    os.path.join(TEST_DIR, 'test_templates'),
)

if django.VERSION[:2] < (1, 6):
    TEST_RUNNER = 'discover_runner.DiscoverRunner'

SECRET_KEY = "iufoj=mibkpdz*%bob952x(%49rqgv8gg45k36kjcg76&-y5=!"

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
)

########NEW FILE########
__FILENAME__ = decorators
class cached_property(object):
    """Property descriptor that caches the return value
    of the get function.

    *Examples*

    .. code-block:: python

         @cached_property
         def connection(self):
              return Connection()

         @connection.setter  # Prepares stored value
         def connection(self, value):
              if value is None:
                    raise TypeError("Connection must be a connection")
              return value

         @connection.deleter
         def connection(self, value):
              # Additional action to do at del(self.attr)
              if value is not None:
                    print("Connection %r deleted" % (value, ))
    """
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.__get = fget
        self.__set = fset
        self.__del = fdel
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.__name__]
        except KeyError:
            value = obj.__dict__[self.__name__] = self.__get(obj)
            return value

    def __set__(self, obj, value):
        if obj is None:
            return self
        if self.__set is not None:
            value = self.__set(obj, value)
        obj.__dict__[self.__name__] = value

    def __delete__(self, obj):
        if obj is None:
            return self
        try:
            value = obj.__dict__.pop(self.__name__)
        except KeyError:
            pass
        else:
            if self.__del is not None:
                self.__del(obj, value)

    def setter(self, fset):
        return self.__class__(self.__get, fset, self.__del)

    def deleter(self, fdel):
        return self.__class__(self.__get, self.__set, fdel)

########NEW FILE########
__FILENAME__ = staticfiles
from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ImproperlyConfigured

from compressor.conf import settings

INSTALLED = ("staticfiles" in settings.INSTALLED_APPS or
             "django.contrib.staticfiles" in settings.INSTALLED_APPS)

if INSTALLED:
    if "django.contrib.staticfiles" in settings.INSTALLED_APPS:
        from django.contrib.staticfiles import finders
    else:
        try:
            from staticfiles import finders  # noqa
        except ImportError:
            # Old (pre 1.0) and incompatible version of staticfiles
            INSTALLED = False

    if (INSTALLED and "compressor.finders.CompressorFinder"
            not in settings.STATICFILES_FINDERS):
        raise ImproperlyConfigured(
            "When using Django Compressor together with staticfiles, "
            "please add 'compressor.finders.CompressorFinder' to the "
            "STATICFILES_FINDERS setting.")
else:
    finders = None  # noqa

########NEW FILE########
__FILENAME__ = stringformat
# -*- coding: utf-8 -*-
"""Advanced string formatting for Python >= 2.4.

An implementation of the advanced string formatting (PEP 3101).

Author: Florent Xicluna
"""

from __future__ import unicode_literals

import re

from django.utils import six

_format_str_re = re.compile(
    r'((?<!{)(?:{{)+'                       # '{{'
    r'|(?:}})+(?!})'                        # '}}
    r'|{(?:[^{](?:[^{}]+|{[^{}]*})*)?})'    # replacement field
)
_format_sub_re = re.compile(r'({[^{}]*})')  # nested replacement field
_format_spec_re = re.compile(
    r'((?:[^{}]?[<>=^])?)'      # alignment
    r'([-+ ]?)'                 # sign
    r'(#?)' r'(\d*)' r'(,?)'    # base prefix, minimal width, thousands sep
    r'((?:\.\d+)?)'             # precision
    r'(.?)$'                    # type
)
_field_part_re = re.compile(
    r'(?:(\[)|\.|^)'            # start or '.' or '['
    r'((?(1)[^]]*|[^.[]*))'     # part
    r'(?(1)(?:\]|$)([^.[]+)?)'  # ']' and invalid tail
)

_format_str_sub = _format_str_re.sub


def _is_integer(value):
    return hasattr(value, '__index__')


def _strformat(value, format_spec=""):
    """Internal string formatter.

    It implements the Format Specification Mini-Language.
    """
    m = _format_spec_re.match(str(format_spec))
    if not m:
        raise ValueError('Invalid conversion specification')
    align, sign, prefix, width, comma, precision, conversion = m.groups()
    is_numeric = hasattr(value, '__float__')
    is_integer = is_numeric and _is_integer(value)
    if prefix and not is_integer:
        raise ValueError('Alternate form (#) not allowed in %s format '
                         'specifier' % (is_numeric and 'float' or 'string'))
    if is_numeric and conversion == 'n':
        # Default to 'd' for ints and 'g' for floats
        conversion = is_integer and 'd' or 'g'
    elif sign:
        if not is_numeric:
            raise ValueError("Sign not allowed in string format specifier")
        if conversion == 'c':
            raise ValueError("Sign not allowed with integer "
                             "format specifier 'c'")
    if comma:
        # TODO: thousand separator
        pass
    try:
        if ((is_numeric and conversion == 's') or (not is_integer and conversion in set('cdoxX'))):
            raise ValueError
        if conversion == 'c':
            conversion = 's'
            value = chr(value % 256)
        rv = ('%' + prefix + precision + (conversion or 's')) % (value,)
    except ValueError:
        raise ValueError("Unknown format code %r for object of type %r" %
                         (conversion, value.__class__.__name__))
    if sign not in '-' and value >= 0:
        # sign in (' ', '+')
        rv = sign + rv
    if width:
        zero = (width[0] == '0')
        width = int(width)
    else:
        zero = False
        width = 0
    # Fastpath when alignment is not required
    if width <= len(rv):
        if not is_numeric and (align == '=' or (zero and not align)):
            raise ValueError("'=' alignment not allowed in string format "
                             "specifier")
        return rv
    fill, align = align[:-1], align[-1:]
    if not fill:
        fill = zero and '0' or ' '
    if align == '^':
        padding = width - len(rv)
        # tweak the formatting if the padding is odd
        if padding % 2:
            rv += fill
        rv = rv.center(width, fill)
    elif align == '=' or (zero and not align):
        if not is_numeric:
            raise ValueError("'=' alignment not allowed in string format "
                             "specifier")
        if value < 0 or sign not in '-':
            rv = rv[0] + rv[1:].rjust(width - 1, fill)
        else:
            rv = rv.rjust(width, fill)
    elif align in ('>', '=') or (is_numeric and not align):
        # numeric value right aligned by default
        rv = rv.rjust(width, fill)
    else:
        rv = rv.ljust(width, fill)
    return rv


def _format_field(value, parts, conv, spec, want_bytes=False):
    """Format a replacement field."""
    for k, part, _ in parts:
        if k:
            if part.isdigit():
                value = value[int(part)]
            else:
                value = value[part]
        else:
            value = getattr(value, part)
    if conv:
        value = ((conv == 'r') and '%r' or '%s') % (value,)
    if hasattr(value, '__format__'):
        value = value.__format__(spec)
    elif hasattr(value, 'strftime') and spec:
        value = value.strftime(str(spec))
    else:
        value = _strformat(value, spec)
    if want_bytes and isinstance(value, six.text_type):
        return str(value)
    return value


class FormattableString(object):
    """Class which implements method format().

    The method format() behaves like str.format() in python 2.6+.

    >>> FormattableString('{a:5}').format(a=42)
    ... # Same as '{a:5}'.format(a=42)
    '   42'

    """

    __slots__ = '_index', '_kwords', '_nested', '_string', 'format_string'

    def __init__(self, format_string):
        self._index = 0
        self._kwords = {}
        self._nested = {}

        self.format_string = format_string
        self._string = _format_str_sub(self._prepare, format_string)

    def __eq__(self, other):
        if isinstance(other, FormattableString):
            return self.format_string == other.format_string
        # Compare equal with the original string.
        return self.format_string == other

    def _prepare(self, match):
        # Called for each replacement field.
        part = match.group(0)
        if part[0] == part[-1]:
            # '{{' or '}}'
            assert part == part[0] * len(part)
            return part[:len(part) // 2]
        repl = part[1:-1]
        field, _, format_spec = repl.partition(':')
        literal, sep, conversion = field.partition('!')
        if sep and not conversion:
            raise ValueError("end of format while looking for "
                             "conversion specifier")
        if len(conversion) > 1:
            raise ValueError("expected ':' after format specifier")
        if conversion not in 'rsa':
            raise ValueError("Unknown conversion specifier %s" %
                             str(conversion))
        name_parts = _field_part_re.findall(literal)
        if literal[:1] in '.[':
            # Auto-numbering
            if self._index is None:
                raise ValueError("cannot switch from manual field "
                                 "specification to automatic field numbering")
            name = str(self._index)
            self._index += 1
            if not literal:
                del name_parts[0]
        else:
            name = name_parts.pop(0)[1]
            if name.isdigit() and self._index is not None:
                # Manual specification
                if self._index:
                    raise ValueError("cannot switch from automatic field "
                                     "numbering to manual field specification")
                self._index = None
        empty_attribute = False
        for k, v, tail in name_parts:
            if not v:
                empty_attribute = True
            if tail:
                raise ValueError("Only '.' or '[' may follow ']' "
                                 "in format field specifier")
        if name_parts and k == '[' and not literal[-1] == ']':
            raise ValueError("Missing ']' in format string")
        if empty_attribute:
            raise ValueError("Empty attribute in format string")
        if '{' in format_spec:
            format_spec = _format_sub_re.sub(self._prepare, format_spec)
            rv = (name_parts, conversion, format_spec)
            self._nested.setdefault(name, []).append(rv)
        else:
            rv = (name_parts, conversion, format_spec)
            self._kwords.setdefault(name, []).append(rv)
        return r'%%(%s)s' % id(rv)

    def format(self, *args, **kwargs):
        """Same as str.format() and unicode.format() in Python 2.6+."""
        if args:
            kwargs.update(dict((str(i), value)
                               for (i, value) in enumerate(args)))
        # Encode arguments to ASCII, if format string is bytes
        want_bytes = isinstance(self._string, str)
        params = {}
        for name, items in self._kwords.items():
            value = kwargs[name]
            for item in items:
                parts, conv, spec = item
                params[str(id(item))] = _format_field(value, parts, conv, spec,
                                                      want_bytes)
        for name, items in self._nested.items():
            value = kwargs[name]
            for item in items:
                parts, conv, spec = item
                spec = spec % params
                params[str(id(item))] = _format_field(value, parts, conv, spec,
                                                      want_bytes)
        return self._string % params


def selftest():
    import datetime
    F = FormattableString

    assert F("{0:{width}.{precision}s}").format('hello world',
             width=8, precision=5) == 'hello   '

    d = datetime.date(2010, 9, 7)
    assert F("The year is {0.year}").format(d) == "The year is 2010"
    assert F("Tested on {0:%Y-%m-%d}").format(d) == "Tested on 2010-09-07"
    print('Test successful')

if __name__ == '__main__':
    selftest()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-compressor documentation build configuration file, created by
# sphinx-quickstart on Fri Jan 21 11:47:42 2011.
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

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
# extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Compressor'
copyright = u'2014, Django Compressor authors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
try:
    from compressor import __version__
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
pygments_style = 'murphy'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'default'
RTD_NEW_THEME = True

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = ['_theme']

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
# html_static_path = ['_static']

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
htmlhelp_basename = 'django-compressordoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'django-compressor.tex', u'Django Compressor Documentation',
    u'Django Compressor authors', 'manual'),
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
    ('index', 'django-compressor', u'Django Compressor Documentation',
     [u'Django Compressor authors'], 1)
]

########NEW FILE########
