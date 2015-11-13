__FILENAME__ = conf
# -*- coding: utf-8 -*-

import os
import sys

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'murl'
copyright = u'2013, Berker Peksag'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = version

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'nature'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Output file base name for HTML help builder.
htmlhelp_basename = 'murldoc'

########NEW FILE########
__FILENAME__ = murl
# coding: utf-8

from __future__ import unicode_literals

try:
    from urllib.parse import (urlencode, urlparse, urlunparse,
                              parse_qs, ParseResult)
except ImportError:
    from urllib import urlencode
    from urlparse import urlparse, urlunparse, parse_qs, ParseResult

__all__ = ['Url']

__version__ = '0.5'

#: Parts for RFC 3986 URI syntax
#: <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
URL_PARTS = ('scheme', 'netloc', 'path', 'params', 'query', 'fragment')


class Url(object):
    """Parse (absolute and relative) URLs for humans."""

    def __init__(self, url, **parts):
        """
        Constructor for Url object.

        :param url:
        :type url: string

        :param parts: scheme, netloc, path, params,
                      query, fragment
        :type parts: dict
        """
        self._url = url
        self.params = dict((URL_PARTS[k], v)
            for k, v in enumerate(urlparse(self._url)))

        for option, value in parts.items():
            if option in parts:
                self.params[option] = value

    @property
    def url(self):
        return urlunparse(ParseResult(**self.params))

    @property
    def scheme(self):
        return self.params.get('scheme')

    @scheme.setter
    def scheme(self, value):
        self.params['scheme'] = value

    @property
    def host(self):
        # Following the syntax specifications in RFC 1808,
        # urlparse recognizes a netloc only if it is properly
        # introduced by ‘//’. Otherwise the input is presumed
        # to be a relative URL and thus to start with a path component.
        if self.params.get('path').startswith('www.'):
            self.params['netloc'] = '//' + self.params.get('path')
            self.params['path'] = ''
        return self.params.get('netloc')

    @property
    def netloc(self):
        return self.host

    @host.setter
    def host(self, value):
        self.params['netloc'] = value

    @property
    def port(self):
        return urlparse(self._url).port

    @port.setter
    def port(self, value):
        if self.port:
            host = ":".join(self.params['netloc'].split(":")[:-1])
            self.params['netloc'] = "{host}:{port}".format(host=host, port=value)
        else:
            self.params['netloc'] += ":{port}".format(port=value)

        self._url = urlunparse(ParseResult(**self.params))

    @property
    def path(self):
        return self.params.get('path')

    @path.setter
    def path(self, value):
        self.params['path'] = value

    @property
    def querystring(self):
        if self.params.get('query'):
            return urlencode(parse_qs(self.params.get('query')), doseq=True)
        return ''

    @property
    def qs(self):
        return parse_qs(self.params.get('query'))

    @property
    def fragment(self):
        return self.params.get('fragment')

    @fragment.setter
    def fragment(self, value):
        self.params['fragment'] = value

    def __repr__(self):
        return '<Url: {}>'.format(self.url)

    def __str__(self):
        return self.url

    def __dir__(self):
        return ['url', 'scheme', 'netloc', 'host', 'port', 'path', 'querystring',
                'qs', 'fragment']

########NEW FILE########
__FILENAME__ = test_murl
from __future__ import unicode_literals

import unittest

from murl import Url


class TestMurl(unittest.TestCase):

    def test_parse_url(self):
        url = Url('http://www.mozilla.org/en-US/')
        self.assertEqual('http://www.mozilla.org/en-US/', str(url))
        self.assertEqual('http://www.mozilla.org/en-US/', url.url)
        self.assertEqual('http', url.scheme)
        self.assertEqual('www.mozilla.org', url.host)
        self.assertEqual('', url.querystring)

    def test_update_scheme(self):
        url = Url('http://githubbadge.appspot.com/badge/berkerpeksag?s=1')
        old_scheme = url.scheme
        self.assertEqual('http', url.scheme)
        url.scheme = 'https'
        self.assertEqual('https', url.scheme)
        self.assertNotEqual(old_scheme, url.scheme)

    def test_update_scheme_and_url(self):
        url_string = 'http://githubbadge.appspot.com/badge/berkerpeksag?s=1'
        url = Url(url_string)
        self.assertEqual(url_string, url.url)
        url.scheme = 'https'
        self.assertEqual(
            'https://githubbadge.appspot.com/badge/berkerpeksag?s=1', url.url)

    def test_update_host_and_url(self):
        url_string = 'http://githubbadge.appspot.com/badge/berkerpeksag?s=1'
        url = Url(url_string)
        old_host = url.host
        self.assertEqual('githubbadge.appspot.com', url.host)
        url.host = 'githubbadge.com'
        self.assertNotEqual(old_host, url.host)
        self.assertEqual(
            'http://githubbadge.com/badge/berkerpeksag?s=1', url.url)

    def test_update_path_and_url(self):
        url_string = 'http://githubbadge.appspot.com/badge/berkerpeksag?s=1'
        url = Url(url_string)
        old_path = url.path
        self.assertEqual('/badge/berkerpeksag', url.path)
        self.assertTrue(url.path.startswith('/'))
        url.path = 'badge/BYK'
        self.assertEqual('badge/BYK', url.path)
        self.assertNotEqual(old_path, url.path)
        self.assertEqual('http://githubbadge.appspot.com/badge/BYK?s=1',
                         url.url)

    def test_update_querystring_and_url(self):
        url = Url('http://githubbadge.appspot.com/badge/berkerpeksag?s=1&a=0')
        self.assertEqual({'a': ['0'], 's': ['1']}, url.qs)

    def test_url_with_port(self):
        url_string = 'http://test.python.org:5432/foo/#top'
        url = Url(url_string)
        self.assertEqual('test.python.org:5432', url.host)
        self.assertEqual('/foo/', url.path)

    def test_get_port(self):
        """When a URL contains a port test it is returned correctly"""
        url_string = 'http://test.python.org:8080/foo/#top'
        url = Url(url_string)
        self.assertEqual(8080, url.port)
        self.assertEqual('test.python.org:8080', url.host)
        self.assertEqual('test.python.org:8080', url.netloc)

    def test_url_no_port(self):
        """When a URL does not contain a port test that None is returned"""
        url_string = 'http://test.python.org/foo/#top'
        url = Url(url_string)
        self.assertEqual(None, url.port)
        self.assertEqual('test.python.org', url.host)
        self.assertEqual('test.python.org', url.netloc)

    def test_set_port(self):
        """When a URL does not contain a port test we can set one"""
        url_string = 'http://test.python.org/foo/#top'
        url = Url(url_string)
        url.port = 8080
        self.assertEqual(8080, url.port)
        self.assertEqual('http://test.python.org:8080/foo/#top', url.url)
        self.assertEqual('test.python.org:8080', url.netloc)

    def test_update_url_and_port(self):
        """When a URL contains a port test that we can update it"""
        url_string = 'http://test.python.org:8080/foo/#top'
        url = Url(url_string)
        url.port = 9000
        self.assertEqual(9000, url.port)
        self.assertEqual('http://test.python.org:9000/foo/#top', url.url)
        self.assertEqual('test.python.org:9000', url.netloc)

    def test_url_with_fragment(self):
        url_string = 'http://test.python.org:5432/foo/#top'
        url = Url(url_string)
        self.assertEqual('top', url.fragment)

    def test_change_scheme(self):
        url_str = '//www.python.org'
        url = Url(url_str, scheme='http')
        self.assertEqual('http', url.scheme)
        self.assertEqual('http://www.python.org', url.url)

    def test_rfc1808(self):
        url = Url('www.python.org')
        self.assertEqual('//www.python.org', url.host)

    def test_change_host(self):
        url_str = 'http://docs.python.org/library/urlparse.html'
        url = Url(url_str, netloc='dev.python.org')
        self.assertEqual('http', url.scheme)
        self.assertEqual('dev.python.org', url.host)
        self.assertEqual('http://dev.python.org/library/urlparse.html',
                         url.url)

    def test_alias_host_netloc(self):
        url_str = 'http://docs.python.org/library/urlparse.html'
        url = Url(url_str, netloc='dev.python.org')
        self.assertEqual('dev.python.org', url.host)
        self.assertEqual('dev.python.org', url.netloc)
        self.assertEqual(url.netloc, url.host)
        self.assertEqual('http://dev.python.org/library/urlparse.html',
                         url.url)

    def test_manipulate_querystring(self):
        url_string = 'http://example.com/berkerpeksag?s=1&a=0&b=berker'
        url = Url(url_string)
        self.assertEqual({'a': ['0'], 's': ['1'], 'b': ['berker']}, url.qs)
        self.assertEqual(['0'], url.qs.get('a'))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
