__FILENAME__ = adapter
import functools

from requests.adapters import HTTPAdapter

from .controller import CacheController
from .cache import DictCache
from .filewrapper import CallbackFileWrapper


class CacheControlAdapter(HTTPAdapter):
    invalidating_methods = set(['PUT', 'DELETE'])

    def __init__(self, cache=None, cache_etags=True, controller_class=None,
                 serializer=None, *args, **kw):
        super(CacheControlAdapter, self).__init__(*args, **kw)
        self.cache = cache or DictCache()

        controller_factory = controller_class or CacheController
        self.controller = controller_factory(
            self.cache,
            cache_etags=cache_etags,
            serializer=serializer,
        )

    def send(self, request, **kw):
        """
        Send a request. Use the request information to see if it
        exists in the cache and cache the response if we need to and can.
        """
        if request.method == 'GET':
            cached_response = self.controller.cached_request(request)
            if cached_response:
                return self.build_response(request, cached_response, from_cache=True)

            # check for etags and add headers if appropriate
            request.headers.update(self.controller.conditional_headers(request))

        resp = super(CacheControlAdapter, self).send(request, **kw)

        return resp

    def build_response(self, request, response, from_cache=False):
        """
        Build a response by making a request or using the cache.

        This will end up calling send and returning a potentially
        cached response
        """
        if not from_cache and request.method == 'GET':
            if response.status == 304:
                # We must have sent an ETag request. This could mean
                # that we've been expired already or that we simply
                # have an etag. In either case, we want to try and
                # update the cache if that is the case.
                cached_response = self.controller.update_cached_response(
                    request, response
                )

                if cached_response is not response:
                    from_cache = True

                response = cached_response
            else:
                # Wrap the response file with a wrapper that will cache the
                #   response when the stream has been consumed.
                response._fp = CallbackFileWrapper(
                    response._fp,
                    functools.partial(
                        self.controller.cache_response,
                        request,
                        response,
                    )
                )

        resp = super(CacheControlAdapter, self).build_response(
            request, response
        )

        # See if we should invalidate the cache.
        if request.method in self.invalidating_methods and resp.ok:
            cache_url = self.controller.cache_url(request.url)
            self.cache.delete(cache_url)

        # Give the request a from_cache attr to let people use it
        resp.from_cache = from_cache

        return resp

########NEW FILE########
__FILENAME__ = cache
"""
The cache object API for implementing caches. The default is just a
dictionary, which in turns means it is not threadsafe for writing.
"""
from threading import Lock


class BaseCache(object):

    def get(self, key):
        raise NotImplemented()

    def set(self, key, value):
        raise NotImplemented()

    def delete(self, key):
        raise NotImplemented()


class DictCache(BaseCache):

    def __init__(self, init_dict=None):
        self.lock = Lock()
        self.data = init_dict or {}

    def get(self, key):
        return self.data.get(key, None)

    def set(self, key, value):
        with self.lock:
            self.data.update({key: value})

    def delete(self, key):
        with self.lock:
            if key in self.data:
                self.data.pop(key)

########NEW FILE########
__FILENAME__ = file_cache
import hashlib
import os

from lockfile import FileLock


def _secure_open_write(filename, fmode):
    # We only want to write to this file, so open it in write only mode
    flags = os.O_WRONLY

    # os.O_CREAT | os.O_EXCL will fail if the file already exists, so we only
    #  will open *new* files.
    # We specify this because we want to ensure that the mode we pass is the
    # mode of the file.
    flags |= os.O_CREAT | os.O_EXCL

    # Do not follow symlinks to prevent someone from making a symlink that
    # we follow and insecurely open a cache file.
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    # On Windows we'll mark this file as binary
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    # Before we open our file, we want to delete any existing file that is
    # there
    try:
        os.remove(filename)
    except (IOError, OSError):
        # The file must not exist already, so we can just skip ahead to opening
        pass

    # Open our file, the use of os.O_CREAT | os.O_EXCL will ensure that if a
    # race condition happens between the os.remove and this line, that an
    # error will be raised. Because we utilize a lockfile this should only
    # happen if someone is attempting to attack us.
    fd = os.open(filename, flags, fmode)
    try:
        return os.fdopen(fd, "wb")
    except:
        # An error occurred wrapping our FD in a file object
        os.close(fd)
        raise


class FileCache(object):
    def __init__(self, directory, forever=False, filemode=0o0600,
                 dirmode=0o0700):
        self.directory = directory
        self.forever = forever
        self.filemode = filemode
        self.dirmode = dirmode

    @staticmethod
    def encode(x):
        return hashlib.sha224(x.encode()).hexdigest()

    def _fn(self, name):
        hashed = self.encode(name)
        parts = list(hashed[:5]) + [hashed]
        return os.path.join(self.directory, *parts)

    def get(self, key):
        name = self._fn(key)
        if not os.path.exists(name):
            return None

        with open(name, 'rb') as fh:
            return fh.read()

    def set(self, key, value):
        name = self._fn(key)

        # Make sure the directory exists
        try:
            os.makedirs(os.path.dirname(name), self.dirmode)
        except (IOError, OSError):
            pass

        with FileLock(name) as lock:
            # Write our actual file
            with _secure_open_write(lock.path, self.filemode) as fh:
                fh.write(value)

    def delete(self, key):
        name = self._fn(key)
        if not self.forever:
            os.remove(name)

########NEW FILE########
__FILENAME__ = redis_cache
from __future__ import division

from datetime import datetime


def total_seconds(td):
    """Python 2.6 compatability"""
    if hasattr(td, 'total_seconds'):
        return td.total_seconds()

    ms = td.microseconds
    secs = (td.seconds + td.days * 24 * 3600)
    return (ms + secs * 10**6) / 10**6


class RedisCache(object):

    def __init__(self, conn):
        self.conn = conn

    def get(self, key):
        return self.conn.get(key)

    def set(self, key, value, expires=None):
        if not expires:
            self.conn.set(key, value)
        else:
            expires = expires - datetime.now()
            self.conn.setex(key, total_seconds(expires), value)

    def delete(self, key):
        self.conn.delete(key)

    def clear(self):
        """Helper for clearing all the keys in a database. Use with
        caution!"""
        for key in self.conn.keys():
            self.conn.delete(key)

########NEW FILE########
__FILENAME__ = compat
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin


try:
    import email.utils
    parsedate_tz = email.utils.parsedate_tz
except ImportError:
    import email.Utils
    parsedate_tz = email.Utils.parsedate_tz


try:
    import cPickle as pickle
except ImportError:
    import pickle


# Handle the case where the requests has been patched to not have urllib3
# bundled as part of it's source.
try:
    from requests.packages.urllib3.response import HTTPResponse
except ImportError:
    from urllib3.response import HTTPResponse

try:
    from requests.packages.urllib3.util import is_fp_closed
except ImportError:
    from urllib3.util import is_fp_closed

########NEW FILE########
__FILENAME__ = controller
"""
The httplib2 algorithms ported for use with requests.
"""
import re
import calendar
import time

from requests.structures import CaseInsensitiveDict

from .cache import DictCache
from .compat import parsedate_tz
from .serialize import Serializer


URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")


def parse_uri(uri):
    """Parses a URI using the regex given in Appendix B of RFC 3986.

        (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    groups = URI.match(uri).groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])


class CacheController(object):
    """An interface to see if request should cached or not.
    """
    def __init__(self, cache=None, cache_etags=True, serializer=None):
        self.cache = cache or DictCache()
        self.cache_etags = cache_etags
        self.serializer = serializer or Serializer()

    def _urlnorm(self, uri):
        """Normalize the URL to create a safe key for the cache"""
        (scheme, authority, path, query, fragment) = parse_uri(uri)
        if not scheme or not authority:
            raise Exception("Only absolute URIs are allowed. uri = %s" % uri)
        authority = authority.lower()
        scheme = scheme.lower()
        if not path:
            path = "/"

        # Could do syntax based normalization of the URI before
        # computing the digest. See Section 6.2.2 of Std 66.
        request_uri = query and "?".join([path, query]) or path
        scheme = scheme.lower()
        defrag_uri = scheme + "://" + authority + request_uri

        return defrag_uri

    def cache_url(self, uri):
        return self._urlnorm(uri)

    def parse_cache_control(self, headers):
        """
        Parse the cache control headers returning a dictionary with values
        for the different directives.
        """
        retval = {}

        cc_header = 'cache-control'
        if 'Cache-Control' in headers:
            cc_header = 'Cache-Control'

        if cc_header in headers:
            parts = headers[cc_header].split(',')
            parts_with_args = [
                tuple([x.strip().lower() for x in part.split("=", 1)])
                for part in parts if -1 != part.find("=")]
            parts_wo_args = [(name.strip().lower(), 1)
                             for name in parts if -1 == name.find("=")]
            retval = dict(parts_with_args + parts_wo_args)
        return retval

    def cached_request(self, request):
        cache_url = self.cache_url(request.url)
        cc = self.parse_cache_control(request.headers)

        # non-caching states
        no_cache = True if 'no-cache' in cc else False
        if 'max-age' in cc and cc['max-age'] == 0:
            no_cache = True

        # Bail out if no-cache was set
        if no_cache:
            return False

        # It is in the cache, so lets see if it is going to be
        # fresh enough
        resp = self.serializer.loads(request, self.cache.get(cache_url))

        # Check to see if we have a cached object
        if not resp:
            return False

        headers = CaseInsensitiveDict(resp.headers)

        now = time.time()
        date = calendar.timegm(
            parsedate_tz(headers['date'])
        )
        current_age = max(0, now - date)

        # TODO: There is an assumption that the result will be a
        # urllib3 response object. This may not be best since we
        # could probably avoid instantiating or constructing the
        # response until we know we need it.
        resp_cc = self.parse_cache_control(headers)

        # determine freshness
        freshness_lifetime = 0
        if 'max-age' in resp_cc and resp_cc['max-age'].isdigit():
            freshness_lifetime = int(resp_cc['max-age'])
        elif 'expires' in headers:
            expires = parsedate_tz(headers['expires'])
            if expires is not None:
                expire_time = calendar.timegm(expires) - date
                freshness_lifetime = max(0, expire_time)

        # determine if we are setting freshness limit in the req
        if 'max-age' in cc:
            try:
                freshness_lifetime = int(cc['max-age'])
            except ValueError:
                freshness_lifetime = 0

        if 'min-fresh' in cc:
            try:
                min_fresh = int(cc['min-fresh'])
            except ValueError:
                min_fresh = 0
            # adjust our current age by our min fresh
            current_age += min_fresh

        # see how fresh we actually are
        fresh = (freshness_lifetime > current_age)

        if fresh:
            return resp

        # we're not fresh. If we don't have an Etag, clear it out
        if 'etag' not in headers:
            self.cache.delete(cache_url)

        # return the original handler
        return False

    def conditional_headers(self, request):
        cache_url = self.cache_url(request.url)
        resp = self.serializer.loads(request, self.cache.get(cache_url))
        new_headers = {}

        if resp:
            headers = CaseInsensitiveDict(resp.headers)

            if 'etag' in headers:
                new_headers['If-None-Match'] = headers['ETag']

            if 'last-modified' in headers:
                new_headers['If-Modified-Since'] = headers['Last-Modified']

        return new_headers

    def cache_response(self, request, response, body=None):
        """
        Algorithm for caching requests.

        This assumes a requests Response object.
        """
        # From httplib2: Don't cache 206's since we aren't going to
        # handle byte range requests
        if response.status not in [200, 203]:
            return

        response_headers = CaseInsensitiveDict(response.headers)

        cc_req = self.parse_cache_control(request.headers)
        cc = self.parse_cache_control(response_headers)

        cache_url = self.cache_url(request.url)

        # Delete it from the cache if we happen to have it stored there
        no_store = cc.get('no-store') or cc_req.get('no-store')
        if no_store and self.cache.get(cache_url):
            self.cache.delete(cache_url)

        # If we've been given an etag, then keep the response
        if self.cache_etags and 'etag' in response_headers:
            self.cache.set(
                cache_url,
                self.serializer.dumps(request, response, body=body),
            )

        # Add to the cache if the response headers demand it. If there
        # is no date header then we can't do anything about expiring
        # the cache.
        elif 'date' in response_headers:
            # cache when there is a max-age > 0
            if cc and cc.get('max-age'):
                if int(cc['max-age']) > 0:
                    self.cache.set(
                        cache_url,
                        self.serializer.dumps(request, response, body=body),
                    )

            # If the request can expire, it means we should cache it
            # in the meantime.
            elif 'expires' in response_headers:
                if response_headers['expires']:
                    self.cache.set(
                        cache_url,
                        self.serializer.dumps(request, response, body=body),
                    )

    def update_cached_response(self, request, response):
        """On a 304 we will get a new set of headers that we want to
        update our cached value with, assuming we have one.

        This should only ever be called when we've sent an ETag and
        gotten a 304 as the response.
        """
        cache_url = self.cache_url(request.url)

        cached_response = self.serializer.loads(request, self.cache.get(cache_url))

        if not cached_response:
            # we didn't have a cached response
            return response

        # Lets update our headers with the headers from the new request:
        # http://tools.ietf.org/html/draft-ietf-httpbis-p4-conditional-26#section-4.1
        #
        # The server isn't supposed to send headers that would make
        # the cached body invalid. But... just in case, we'll be sure
        # to strip out ones we know that might be problmatic due to
        # typical assumptions.
        excluded_headers = [
            "content-length",
        ]

        cached_response.headers.update(
            dict((k, v) for k, v in response.headers.items()
                 if k.lower() not in excluded_headers)
        )

        # we want a 200 b/c we have content via the cache
        cached_response.status = 200

        # update our cache
        self.cache.set(
            cache_url,
            self.serializer.dumps(request, cached_response),
        )

        return cached_response

########NEW FILE########
__FILENAME__ = filewrapper
from io import BytesIO

from .compat import is_fp_closed


class CallbackFileWrapper(object):
    """
    Small wrapper around a fp object which will tee everything read into a
    buffer, and when that file is closed it will execute a callback with the
    contents of that buffer.

    All attributes are proxied to the underlying file object.

    This class uses members with a double underscore (__) leading prefix so as
    not to accidentally shadow an attribute.
    """

    def __init__(self, fp, callback):
        self.__buf = BytesIO()
        self.__fp = fp
        self.__callback = callback

    def __getattr__(self, name):
        return getattr(self.__fp, name)

    def read(self, amt=None):
        data = self.__fp.read(amt)
        self.__buf.write(data)

        # Is this the best way to figure out if the file has been completely
        #   consumed?
        if is_fp_closed(self.__fp):
            self.__callback(self.__buf.getvalue())

        return data

########NEW FILE########
__FILENAME__ = serialize
import io

from requests.structures import CaseInsensitiveDict

from .compat import HTTPResponse, pickle


class Serializer(object):

    def dumps(self, request, response, body=None):
        response_headers = CaseInsensitiveDict(response.headers)

        if body is None:
            body = response.read(decode_content=False)
            response._fp = io.BytesIO(body)

        data = {
            "response": {
                "body": body,
                "headers": response.headers,
                "status": response.status,
                "version": response.version,
                "reason": response.reason,
                "strict": response.strict,
                "decode_content": response.decode_content,
            },
        }

        # Construct our vary headers
        data["vary"] = {}
        if "vary" in response_headers:
            varied_headers = response_headers['vary'].split(',')
            for header in varied_headers:
                header = header.strip()
                data["vary"][header] = request.headers.get(header, None)

        return b"cc=1," + pickle.dumps(data, pickle.HIGHEST_PROTOCOL)

    def loads(self, request, data):
        # Short circuit if we've been given an empty set of data
        if not data:
            return

        # Determine what version of the serializer the data was serialized
        # with
        try:
            ver, data = data.split(b",", 1)
        except ValueError:
            ver = b"cc=0"

        # Make sure that our "ver" is actually a version and isn't a false
        # positive from a , being in the data stream.
        if ver[:3] != b"cc=":
            data = ver + data
            ver = b"cc=0"

        # Get the version number out of the cc=N
        ver = ver.split(b"=", 1)[-1].decode("ascii")

        # Dispatch to the actual load method for the given version
        try:
            return getattr(self, "_loads_v{0}".format(ver))(request, data)
        except AttributeError:
            # This is a version we don't have a loads function for, so we'll
            # just treat it as a miss and return None
            return

    def _loads_v0(self, request, data):
        # The original legacy cache data. This doesn't contain enough
        # information to construct everything we need, so we'll treat this as
        # a miss.
        return

    def _loads_v1(self, request, data):
        try:
            cached = pickle.loads(data)
        except ValueError:
            return

        # Special case the '*' Vary value as it means we cannot actually
        # determine if the cached response is suitable for this request.
        if "*" in cached.get("vary", {}):
            return

        # Ensure that the Vary headers for the cached response match our
        # request
        for header, value in cached.get("vary", {}).items():
            if request.headers.get(header, None) != value:
                return

        body = io.BytesIO(cached["response"].pop("body"))
        return HTTPResponse(
            body=body,
            preload_content=False,
            **cached["response"]
        )

########NEW FILE########
__FILENAME__ = wrapper
from .adapter import CacheControlAdapter
from .cache import DictCache


def CacheControl(sess, cache=None, cache_etags=True, serializer=None):
    cache = cache or DictCache()
    adapter = CacheControlAdapter(
        cache,
        cache_etags=cache_etags,
        serializer=serializer,
    )
    sess.mount('http://', adapter)
    sess.mount('https://', adapter)

    return sess

########NEW FILE########
__FILENAME__ = conftest
from pprint import pformat

import pytest

from webtest.http import StopableWSGIServer


class SimpleApp(object):

    def __init__(self):
        self.etag_count = 0
        self.update_etag_string()

    def dispatch(self, env):
        path = env['PATH_INFO'][1:].split('/')
        segment = path.pop(0)
        if segment and hasattr(self, segment):
            return getattr(self, segment)
        return None

    def vary_accept(self, env, start_response):
        headers = [
            ('Cache-Control', 'max-age=5000'),
            ('Content-Type', 'text/plain'),
            ('Vary', 'Accept-Encoding, Accept'),
        ]
        start_response('200 OK', headers)
        return [pformat(env).encode("utf8")]

    def update_etag_string(self):
        self.etag_count += 1
        self.etag_string = '"ETAG-{0}"'.format(self.etag_count)

    def update_etag(self, env, start_response):
        self.update_etag_string()
        headers = [
            ('Cache-Control', 'max-age=5000'),
            ('Content-Type', 'text/plain'),
        ]
        start_response('200 OK', headers)
        return [pformat(env).encode("utf8")]

    def etag(self, env, start_response):
        headers = [
            ('Etag', self.etag_string),
        ]
        if env.get('HTTP_IF_NONE_MATCH') == self.etag_string:
            start_response('304 Not Modified', headers)
        else:
            start_response('200 OK', headers)
        return [pformat(env).encode("utf8")]

    def __call__(self, env, start_response):
        func = self.dispatch(env)

        if func:
            return func(env, start_response)

        headers = [
            ('Cache-Control', 'max-age=5000'),
            ('Content-Type', 'text/plain'),
        ]
        start_response('200 OK', headers)
        return [pformat(env).encode("utf8")]


@pytest.fixture(scope='session')
def server():
    return pytest.server


@pytest.fixture()
def url(server):
    return server.application_url


def pytest_namespace():
    return dict(server=StopableWSGIServer.create(SimpleApp()))


def pytest_unconfigure(config):
    pytest.server.shutdown()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# CacheControl documentation build configuration file, created by
# sphinx-quickstart on Mon Nov  4 15:01:23 2013.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'CacheControl'
copyright = u'2013, Eric Larson'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6'
# The full version, including alpha/beta/rc tags.
release = '0.6'

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
htmlhelp_basename = 'CacheControldoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'CacheControl.tex', u'CacheControl Documentation',
   u'Eric Larson', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'cachecontrol', u'CacheControl Documentation',
     [u'Eric Larson'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'CacheControl', u'CacheControl Documentation',
   u'Eric Larson', 'CacheControl', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = benchmark
import sys
import requests
import argparse

from multiprocessing import Process
from datetime import datetime
from wsgiref.simple_server import make_server
from cachecontrol import CacheControl

HOST = 'localhost'
PORT = 8050
URL = 'http://{0}:{1}/'.format(HOST, PORT)


class Server(object):

    def __call__(self, env, sr):
        body = 'Hello World!'
        status = '200 OK'
        headers = [
            ('Cache-Control', 'max-age=%i' % (60 * 10)),
            ('Content-Type', 'text/plain'),
        ]
        sr(status, headers)
        return body


def start_server():
    httpd = make_server(HOST, PORT, Server())
    httpd.serve_forever()


def run_benchmark(sess):
    proc = Process(target=start_server)
    proc.start()

    start = datetime.now()
    for i in xrange(0, 1000):
        sess.get(URL)
        sys.stdout.write('.')
    end = datetime.now()
    print()

    total = end - start
    print('Total time for 1000 requests: %s' % total)
    proc.terminate()


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--no-cache',
                        default=False,
                        action='store_true',
                        help='Do not use cachecontrol')
    args = parser.parse_args()

    sess = requests.Session()
    if not args.no_cache:
        sess = CacheControl(sess)

    run_benchmark(sess)


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = test_adapter
import pytest

from requests import Session
from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.wrapper import CacheControl


def use_wrapper():
    print('Using helper')
    sess = CacheControl(Session())
    return sess


def use_adapter():
    print('Using adapter')
    sess = Session()
    sess.mount('http://', CacheControlAdapter())
    return sess


@pytest.fixture(params=[use_adapter, use_wrapper])
def sess(url, request):
    sess = request.param()
    sess.get(url)
    return sess


class TestSessionActions(object):

    def test_get_caches(self, url, sess):
        r2 = sess.get(url)
        assert r2.from_cache is True

    def test_get_with_no_cache_does_not_cache(self, url, sess):
        r2 = sess.get(url, headers={'Cache-Control': 'no-cache'})
        assert not r2.from_cache

    def test_put_invalidates_cache(self, url, sess):
        r2 = sess.put(url, data={'foo': 'bar'})
        sess.get(url)
        assert not r2.from_cache

    def test_delete_invalidates_cache(self, url, sess):
        r2 = sess.delete(url)
        sess.get(url)
        assert not r2.from_cache

########NEW FILE########
__FILENAME__ = test_cache_control
"""
Unit tests that verify our caching methods work correctly.
"""
import pytest
from mock import ANY, Mock
import time

from cachecontrol import CacheController
from cachecontrol.cache import DictCache


TIME_FMT = "%a, %d %b %Y %H:%M:%S GMT"


class NullSerializer(object):

    def dumps(self, request, response):
        return response

    def loads(self, request, data):
        return data


class TestCacheControllerResponse(object):
    url = 'http://url.com/'

    def req(self, headers=None):
        headers = headers or {}
        return Mock(full_url=self.url,  # < 1.x support
                    url=self.url,
                    headers=headers)

    def resp(self, headers=None):
        headers = headers or {}
        return Mock(status=200,
                    headers=headers,
                    request=self.req(),
                    read=lambda **k: b"testing")

    @pytest.fixture()
    def cc(self):
        # Cache controller fixture
        return CacheController(Mock(), serializer=Mock())

    def test_no_cache_non_20x_response(self, cc):
        # No caching without some extra headers, so we add them
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = self.resp({'cache-control': 'max-age=3600',
                          'date': now})

        no_cache_codes = [201, 300, 400, 500]
        for code in no_cache_codes:
            resp.status = code
            cc.cache_response(Mock(), resp)
            assert not cc.cache.set.called

        # this should work b/c the resp is 20x
        resp.status = 203
        cc.cache_response(self.req(), resp)
        assert cc.serializer.dumps.called
        assert cc.cache.set.called

    def test_no_cache_with_no_date(self, cc):
        # No date header which makes our max-age pointless
        resp = self.resp({'cache-control': 'max-age=3600'})
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_no_cache_control(self, cc):
        resp = self.resp()
        cc.cache_response(self.req(), resp)

        assert not cc.cache.set.called

    def test_cache_response_cache_max_age(self, cc):
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = self.resp({'cache-control': 'max-age=3600',
                          'date': now})
        req = self.req()
        cc.cache_response(req, resp)
        cc.serializer.dumps.assert_called_with(req, resp, body=None)
        cc.cache.set.assert_called_with(self.url, ANY)

    def test_cache_repsonse_no_store(self):
        resp = Mock()
        cache = DictCache({self.url: resp})
        cc = CacheController(cache)

        cache_url = cc.cache_url(self.url)

        resp = self.resp({'cache-control': 'no-store'})
        assert cc.cache.get(cache_url)

        cc.cache_response(self.req(), resp)
        assert not cc.cache.get(cache_url)

    def test_update_cached_response_with_valid_headers(self):
        cached_resp = Mock(headers={'ETag': 'jfd9094r808', 'Content-Length': 100})

        # Set our content length to 200. That would be a mistake in
        # the server, but we'll handle it gracefully... for now.
        resp = Mock(headers={'ETag': '28371947465', 'Content-Length': 200})
        cache = DictCache({self.url: cached_resp})

        cc = CacheController(cache)

        # skip our in/out processing
        cc.serializer = Mock()
        cc.serializer.loads.return_value = cached_resp
        cc.cache_url = Mock(return_value='http://foo.com')

        result = cc.update_cached_response(Mock(), resp)

        assert result.headers['ETag'] == resp.headers['ETag']
        assert result.headers['Content-Length'] == 100


class TestCacheControlRequest(object):
    url = 'http://foo.com/bar'

    def setup(self):
        self.c = CacheController(
            DictCache(),
            serializer=NullSerializer(),
        )

    def req(self, headers):
        return self.c.cached_request(Mock(url=self.url, headers=headers))

    def test_cache_request_no_cache(self):
        resp = self.req({'cache-control': 'no-cache'})
        assert not resp

    def test_cache_request_pragma_no_cache(self):
        resp = self.req({'pragma': 'no-cache'})
        assert not resp

    def test_cache_request_no_store(self):
        resp = self.req({'cache-control': 'no-store'})
        assert not resp

    def test_cache_request_max_age_0(self):
        resp = self.req({'cache-control': 'max-age=0'})
        assert not resp

    def test_cache_request_not_in_cache(self):
        resp = self.req({})
        assert not resp

    def test_cache_request_fresh_max_age(self):
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'cache-control': 'max-age=3600',
                             'date': now})

        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_max_age(self):
        earlier = time.time() - 3700  # epoch - 1h01m40s
        now = time.strftime(TIME_FMT, time.gmtime(earlier))
        resp = Mock(headers={'cache-control': 'max-age=3600',
                             'date': now})
        self.c.cache = DictCache({self.url: resp})
        r = self.req({})
        assert not r

    def test_cache_request_fresh_expires(self):
        later = time.time() + 86400  # GMT + 1 day
        expires = time.strftime(TIME_FMT, time.gmtime(later))
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'expires': expires,
                             'date': now})
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert r == resp

    def test_cache_request_unfresh_expires(self):
        sooner = time.time() - 86400  # GMT - 1 day
        expires = time.strftime(TIME_FMT, time.gmtime(sooner))
        now = time.strftime(TIME_FMT, time.gmtime())
        resp = Mock(headers={'expires': expires,
                             'date': now})
        cache = DictCache({self.url: resp})
        self.c.cache = cache
        r = self.req({})
        assert not r

########NEW FILE########
__FILENAME__ = test_etag
import pytest
import requests

from cachecontrol import CacheControl
from cachecontrol.cache import DictCache
from cachecontrol.compat import urljoin


class NullSerializer(object):

    def dumps(self, request, response, body=None):
        return response

    def loads(self, request, data):
        return data


class TestETag(object):
    """Test our equal priority caching with ETags

    Equal Priority Caching is a term I've defined to describe when
    ETags are cached orthgonally from Time Based Caching.
    """

    @pytest.fixture()
    def sess(self, server):
        self.etag_url = urljoin(server.application_url, '/etag')
        self.update_etag_url = urljoin(server.application_url, '/update_etag')
        self.cache = DictCache()
        sess = CacheControl(
            requests.Session(),
            cache=self.cache,
            serializer=NullSerializer(),
        )
        return sess

    def test_etags_get_example(self, sess, server):
        """RFC 2616 14.26

        The If-None-Match request-header field is used with a method to make
        it conditional. A client that has one or more entities previously
        obtained from the resource can verify that none of those entities
        is current by including a list of their associated entity tags in
        the If-None-Match header field. The purpose of this feature is to
        allow efficient updates of cached information with a minimum amount
        of transaction overhead

        If any of the entity tags match the entity tag of the entity that
        would have been returned in the response to a similar GET request
        (without the If-None-Match header) on that resource, [...] then
        the server MUST NOT perform the requested method, [...]. Instead, if
        the request method was GET or HEAD, the server SHOULD respond with
        a 304 (Not Modified) response, including the cache-related header
        fields (particularly ETag) of one of the entities that matched.

        (Paraphrased) A server may provide an ETag header on a response. On
        subsequent queries, the client may reference the value of this Etag
        header in an If-None-Match header; on receiving such a header, the
        server can check whether the entity at that URL has changed from the
        clients last version, and if not, it can return a 304 to indicate
        the client can use it's current representation.
        """
        r = sess.get(self.etag_url)

        # make sure we cached it
        assert self.cache.get(self.etag_url) == r.raw

        # make the same request
        resp = sess.get(self.etag_url)
        assert resp.raw == r.raw
        assert resp.from_cache

        # tell the server to change the etags of the response
        sess.get(self.update_etag_url)

        resp = sess.get(self.etag_url)
        assert resp != r
        assert not resp.from_cache

        # Make sure we updated our cache with the new etag'd response.
        assert self.cache.get(self.etag_url) == resp.raw


class TestDisabledETags(object):
    """Test our use of ETags when the response is stale and the
    response has an ETag.
    """
    @pytest.fixture()
    def sess(self, server):
        self.etag_url = urljoin(server.application_url, '/etag')
        self.update_etag_url = urljoin(server.application_url, '/update_etag')
        self.cache = DictCache()
        sess = CacheControl(requests.Session(),
                            cache=self.cache,
                            cache_etags=False,
                            serializer=NullSerializer())
        return sess

    def test_expired_etags_if_none_match_response(self, sess):
        """Make sure an expired response that contains an ETag uses
        the If-None-Match header.
        """
        # get our response
        r = sess.get(self.etag_url)

        # expire our request by changing the date. Our test endpoint
        # doesn't provide time base caching headers, so we add them
        # here in order to expire the request.
        r.headers['Date'] = 'Tue, 26 Nov 2012 00:50:49 GMT'
        self.cache.set(self.etag_url, r)

        r = sess.get(self.etag_url)
        assert r.from_cache
        assert 'if-none-match' in r.request.headers
        assert r.status_code == 200

########NEW FILE########
__FILENAME__ = test_max_age
from __future__ import print_function
import pytest

from requests import Session
from cachecontrol.adapter import CacheControlAdapter
from cachecontrol.cache import DictCache


class NullSerializer(object):

    def dumps(self, request, response, body=None):
        return response

    def loads(self, request, data):
        return data


class TestMaxAge(object):

    @pytest.fixture()
    def sess(self, server):
        self.url = server.application_url
        self.cache = DictCache()
        sess = Session()
        sess.mount(
            'http://',
            CacheControlAdapter(self.cache, serializer=NullSerializer()),
        )
        return sess

    def test_client_max_age_0(self, sess):
        """
        Making sure when the client uses max-age=0 we don't get a
        cached copy even though we're still fresh.
        """
        print('first request')
        r = sess.get(self.url)
        assert self.cache.get(self.url) == r.raw

        print('second request')
        r = sess.get(self.url, headers={'Cache-Control': 'max-age=0'})

        # don't remove from the cache
        assert self.cache.get(self.url)
        assert not r.from_cache

    def test_client_max_age_3600(self, sess):
        """
        Verify we get a cached value when the client has a
        reasonable max-age value.
        """
        r = sess.get(self.url)
        assert self.cache.get(self.url) == r.raw

        # request that we don't want a new one unless
        r = sess.get(self.url, headers={'Cache-Control': 'max-age=3600'})
        assert r.from_cache is True

        # now lets grab one that forces a new request b/c the cache
        # has expired. To do that we'll inject a new time value.
        resp = self.cache.get(self.url)
        resp.headers['date'] = 'Tue, 15 Nov 1994 08:12:31 GMT'
        r = sess.get(self.url)
        assert not r.from_cache

########NEW FILE########
__FILENAME__ = test_storage_filecache
"""
Unit tests that verify FileCache storage works correctly.
"""
import os
import string

from random import randint, sample

import pytest
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache


def randomdata():
    """Plain random http data generator:"""
    key = ''.join(sample(string.ascii_lowercase, randint(2, 4)))
    val = ''.join(sample(string.ascii_lowercase + string.digits,
                         randint(2, 10)))
    return '&{0}={1}'.format(key, val)


class TestStorageFileCache(object):

    @pytest.fixture()
    def sess(self, server, tmpdir):
        self.url = server.application_url
        self.cache = FileCache(str(tmpdir))
        sess = CacheControl(requests.Session(), cache=self.cache)
        return sess

    def test_filecache_from_cache(self, sess):
        response = sess.get(self.url)
        assert not response.from_cache
        response = sess.get(self.url)
        assert response.from_cache

    def test_filecache_directory_not_exists(self, tmpdir, sess):
        url = self.url + ''.join(sample(string.ascii_lowercase, randint(2, 4)))

        # Make sure our cache dir doesn't exist
        tmp_cache = tmpdir.join('missing', 'folder', 'name').strpath
        assert not os.path.exists(tmp_cache)

        self.cache.directory = tmp_cache

        # trigger a cache save
        sess.get(url)

        # Now our cache dir does exist
        assert os.path.exists(tmp_cache)

    def test_filecache_directory_already_exists(self, tmpdir, sess):
        """
        Assert no errors are raised when using a cache directory
        that already exists on the filesystem.
        """
        url = self.url + ''.join(sample(string.ascii_lowercase, randint(2, 4)))

        # Make sure our cache dir DOES exist
        tmp_cache = tmpdir.join('missing', 'folder', 'name').strpath
        os.makedirs(tmp_cache, self.cache.dirmode)

        assert os.path.exists(tmp_cache)

        self.cache.directory = tmp_cache

        # trigger a cache save
        sess.get(url)

        assert True  # b/c no exceptions were raised

    def test_key_length(self, sess):
        """
        Hash table keys:
           Most file systems have a 255 characters path limitation.
              * Make sure hash method does not produce too long keys
              * Ideally hash method generate fixed length keys
        """
        url0 = url1 = 'http://example.org/res?a=1'
        while len(url0) < 255:
            url0 += randomdata()
            url1 += randomdata()
        assert len(self.cache.encode(url0)) < 200
        assert len(self.cache.encode(url0)) == len(self.cache.encode(url1))

########NEW FILE########
__FILENAME__ = test_storage_redis
from datetime import datetime

from mock import Mock
from cachecontrol.caches import RedisCache


class TestRedisCache(object):

    def setup(self):
        self.conn = Mock()
        self.cache = RedisCache(self.conn)

    def test_set_expiration(self):
        self.cache.set('foo', 'bar', expires=datetime(2014, 2, 2))
        assert self.conn.setex.called

########NEW FILE########
__FILENAME__ = test_vary
import pytest
import requests

from cachecontrol import CacheControl
from cachecontrol.cache import DictCache
from cachecontrol.compat import urljoin


class TestVary(object):

    @pytest.fixture()
    def sess(self, server):
        self.url = urljoin(server.application_url, '/vary_accept')
        self.cache = DictCache()
        sess = CacheControl(requests.Session(), cache=self.cache)
        return sess

    def cached_equal(self, cached, resp):
        checks = [
            cached._fp.getvalue() == resp.content,
            cached.headers == resp.raw.headers,
            cached.status == resp.raw.status,
            cached.version == resp.raw.version,
            cached.reason == resp.raw.reason,
            cached.strict == resp.raw.strict,
            cached.decode_content == resp.raw.decode_content,
        ]
        return all(checks)

    def test_vary_example(self, sess):
        """RFC 2616 13.6

        When the cache receives a subsequent request whose Request-URI
        specifies one or more cache entries including a Vary header field,
        the cache MUST NOT use such a cache entry to construct a response
        to the new request unless all of the selecting request-headers
        present in the new request match the corresponding stored
        request-headers in the original request.

        Or, in simpler terms, when you make a request and the server
        returns defines a Vary header, unless all the headers listed
        in the Vary header are the same, it won't use the cached
        value.
        """
        s = sess.adapters["http://"].controller.serializer
        r = sess.get(self.url)
        c = s.loads(r.request, self.cache.get(self.url))

        # make sure we cached it
        assert self.cached_equal(c, r)

        # make the same request
        resp = sess.get(self.url)
        assert self.cached_equal(c, resp)
        assert resp.from_cache

        # make a similar request, changing the accept header
        resp = sess.get(self.url, headers={'Accept': 'text/plain, text/html'})
        assert not self.cached_equal(c, resp)
        assert not resp.from_cache

        # Just confirming two things here:
        #
        #   1) The server used the vary header
        #   2) We have more than one header we vary on
        #
        # The reason for this is that when we don't specify the header
        # in the request, it is considered the same in terms of
        # whether or not to use the cached value.
        assert 'vary' in r.headers
        assert len(r.headers['vary'].replace(' ', '').split(',')) == 2

########NEW FILE########
