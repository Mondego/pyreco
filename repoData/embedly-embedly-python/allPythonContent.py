__FILENAME__ = client
"""
Client
======

The embedly object that interacts with the service
"""
from __future__ import absolute_import, unicode_literals
import re
import httplib2
import json
from urllib import quote, urlencode

from .models import Url


def get_user_agent():
    from . import __version__
    return 'Mozilla/5.0 (compatible; embedly-python/%s;)' % __version__


class Embedly(object):
    """
    Client

    """
    def __init__(self, key=None, user_agent=None, timeout=60):
        """
        Initialize the Embedly client

        :param key: Embedly Pro key
        :type key: str
        :param user_agent: User Agent passed to Embedly
        :type user_agent: str
        :param timeout: timeout for HTTP connection attempts
        :type timeout: int

        :returns: None
        """
        self.key = key
        self.user_agent = user_agent or get_user_agent()
        self.timeout = timeout

        self.services = []
        self._regex = None

    def get_services(self):
        """
        get_services makes call to services end point of api.embed.ly to fetch
        the list of supported providers and their regexes
        """

        if self.services:
            return self.services

        url = 'http://api.embed.ly/1/services/python'

        http = httplib2.Http(timeout=self.timeout)
        headers = {'User-Agent': self.user_agent,
                   'Connection': 'close'}
        resp, content = http.request(url, headers=headers)

        if resp['status'] == '200':
            resp_data = json.loads(content.decode('utf-8'))
            self.services = resp_data

            # build the regex that we can use later
            _regex = []
            for each in self.services:
                _regex.append('|'.join(each.get('regex', [])))

            self._regex = re.compile('|'.join(_regex))

        return self.services

    def is_supported(self, url):
        """
        ``is_supported`` is a shortcut for client.regex.match(url)
        """
        return self.regex.match(url) is not None

    @property
    def regex(self):
        """
        ``regex`` property just so we can call get_services if the _regex is
        not yet filled.
        """
        if not self._regex:
            self.get_services()

        return self._regex

    def _get(self, version, method, url_or_urls, **kwargs):
        """
        _get makes the actual call to api.embed.ly
        """
        if not url_or_urls:
            raise ValueError('%s requires a url or a list of urls given: %s' %
                             (method.title(), url_or_urls))

        # a flag we can use instead of calling isinstance() all the time
        multi = isinstance(url_or_urls, list)

        # throw an error early for too many URLs
        if multi and len(url_or_urls) > 20:
            raise ValueError('Embedly accepts only 20 urls at a time. Url '
                             'Count:%s' % len(url_or_urls))

        query = ''

        key = kwargs.get('key', self.key)

        # make sure that a key was set on the client or passed in
        if not key:
            raise ValueError('Requires a key. None given: %s' % key)

        kwargs['key'] = key

        query += urlencode(kwargs)

        if multi:
            query += '&urls=%s&' % ','.join([quote(url) for url in url_or_urls])
        else:
            query += '&url=%s' % quote(url_or_urls)

        url = 'http://api.embed.ly/%s/%s?%s' % (version, method, query)

        http = httplib2.Http(timeout=self.timeout)

        headers = {'User-Agent': self.user_agent,
                   'Connection': 'close'}

        resp, content = http.request(url, headers=headers)

        if resp['status'] == '200':
            data = json.loads(content.decode('utf-8'))

            if kwargs.get('raw', False):
                data['raw'] = content
        else:
            data = {'type': 'error',
                    'error': True,
                    'error_code': int(resp['status'])}

        if multi:
            return map(lambda url, data: Url(data, method, url),
                       url_or_urls, data)

        return Url(data, method, url_or_urls)

    def oembed(self, url_or_urls, **kwargs):
        """
        oembed
        """
        return self._get(1, 'oembed', url_or_urls, **kwargs)

    def preview(self, url_or_urls, **kwargs):
        """
        oembed
        """
        return self._get(1, 'preview', url_or_urls, **kwargs)

    def objectify(self, url_or_urls, **kwargs):
        """
        oembed
        """
        return self._get(2, 'objectify', url_or_urls, **kwargs)

    def extract(self, url_or_urls, **kwargs):
        """
        oembed
        """
        return self._get(1, 'extract', url_or_urls, **kwargs)

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import, unicode_literals
from .py3_utils import python_2_unicode_compatible, IterableUserDict


@python_2_unicode_compatible
class Url(IterableUserDict, object):
    """
    A dictionary with two additional attributes for the method and url.
    UserDict provides a dictionary interface along with the regular
    dictionary accsesible via the `data` attribute.

    """
    def __init__(self, data=None, method=None, original_url=None, **kwargs):
        super(Url, self).__init__(data, **kwargs)
        self.method = method or 'url'
        self.original_url = original_url

    def __str__(self):
        return '<%s %s>' % (self.method.title(), self.original_url or "")

########NEW FILE########
__FILENAME__ = py3_utils
import sys

# 2to3 doesn't handle the UserDict relocation
# put the import logic here for cleaner usage
try:
    from collections import UserDict as IterableUserDict
except ImportError:  # Python 2
    from UserDict import IterableUserDict


def python_2_unicode_compatible(klass):
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    From django.utils.encoding.py in 1.4.2+, minus the dependency on Six.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.
    """
    if sys.version_info[0] == 2:
        if '__str__' not in klass.__dict__:
            raise ValueError("@python_2_unicode_compatible cannot be applied "
                             "to %s because it doesn't define __str__()." %
                             klass.__name__)
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
    return klass

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals
import re
import sys
import json

try:  # pragma: no cover
    import unittest2 as unittest  # Python 2.6   # pragma: no cover
except ImportError:  # pragma: no cover
    import unittest  # pragma: no cover

try:  # pragma: no cover
    from unittest import mock  # pragma: no cover
except ImportError:  # Python < 3.3  # pragma: no cover
    import mock  # pragma: no cover

from embedly.client import Embedly
from embedly.models import Url


class UrlTestCase(unittest.TestCase):
    def test_model(self):
        data = {
            'provider_url': 'http://www.google.com/',
            'safe': True,
            'description': 'Google',
            'url': 'http://www.google.com/',
            'type': 'html',
            'object': {},
            'provider_display': 'www.google.com',
            'author_name': None,
            'favicon_url': 'http://www.google.com/favicon.ico',
            'place': {},
            'author_url': None,
            'images': [
                {'url': 'http://www.google.com/intl/en_ALL/images/srpr/logo1w.png',
                 'width': 275,
                 'height': 95}],
            'title': 'Google',
            'provider_name': 'Google',
            'cache_age': 86400,
            'embeds': []
        }
        obj = Url(data, 'preview', 'http://original.url.com/')

        self.assertEqual(len(obj), 16)
        self.assertEqual(len(obj.values()), 16)
        self.assertEqual(len(obj.keys()), 16)
        self.assertEqual(len(obj.items()), 16)

        # check for expected data
        self.assertTrue('type' in obj.keys())
        self.assertTrue('html' in obj.values())
        self.assertEqual(obj['type'], 'html')
        self.assertEqual(obj.get('type'), 'html')
        self.assertEqual(obj.data['type'], 'html')
        self.assertEqual(obj.data.get('type'), 'html')

        # our special attrs shouldn't be in the data dict
        self.assertFalse('method' in obj.keys())
        with self.assertRaises(KeyError):
            obj['method']

        # attrs and data dict values should be separate
        self.assertEqual(obj.original_url, 'http://original.url.com/')

        obj.new_attr = 'attr value'
        obj['new_key'] = 'dict value'
        self.assertEqual(obj.new_attr, 'attr value')
        self.assertEqual(obj['new_key'], 'dict value')

    def test_model_data_can_serialize(self):
        obj = Url({'hash': {'key': 'value'},
                   'none': None,
                   'empty': '',
                   'float': 1.234,
                   'int': 1,
                   'string': 'string',
                   'array': [0, -1]})
        unserialzed = json.loads(json.dumps(obj.data))
        self.assertDictEqual(obj.data, unserialzed)

    def test_str_representation(self):
        unistr = 'I\xf1t\xebrn\xe2ti\xf4n\xe0liz\xe6tion'
        url = "http://test.com"
        obj = Url(method=unistr, original_url=url)

        if sys.version_info[0] == 2:
            self.assertTrue(unistr.encode('utf-8') in str(obj))
            self.assertTrue(url.encode('utf-8') in str(obj))
        else:
            self.assertTrue(unistr in str(obj))
            self.assertTrue(url in str(obj))


class EmbedlyTestCase(unittest.TestCase):
    def setUp(self):
        self.key = 'internal'

    def test_requires_api_key(self):
        with self.assertRaises(ValueError):
            Embedly()._get(1, "test", "http://fake")

    def test_requires_url(self):
        with self.assertRaises(ValueError):
            Embedly(self.key)._get(1, "test", None)

    def test_exception_on_too_many_urls(self):
        urls = ['http://embed.ly'] * 21
        with self.assertRaises(ValueError):
            Embedly(self.key)._get(1, "test", urls)

    def test_provider(self):
        http = Embedly(self.key)

        obj = http.oembed('http://www.scribd.com/doc/13994900/Easter')

        self.assertEqual(obj['provider_url'], 'http://www.scribd.com/')

        obj = http.oembed('http://www.scribd.com/doc/28452730/Easter-Cards')
        self.assertEqual(obj['provider_url'], 'http://www.scribd.com/')

        obj = http.oembed('http://www.youtube.com/watch?v=Zk7dDekYej0')
        self.assertEqual(obj['provider_url'], 'http://www.youtube.com/')

        obj = http.oembed('http://yfrog.com/h22eu4j')
        self.assertEqual(obj['provider_url'], 'http://yfrog.com')

    def test_providers(self):
        http = Embedly(self.key)

        objs = list(http.oembed(['http://www.scribd.com/doc/13994900/Easter',
                                 'http://www.scribd.com/doc/28452730/Easter-Cards']))

        self.assertEqual(objs[0]['provider_url'], 'http://www.scribd.com/')
        self.assertEqual(objs[1]['provider_url'], 'http://www.scribd.com/')

        objs = list(http.oembed(['http://www.youtube.com/watch?v=Zk7dDekYej0',
                                 'http://yfrog.com/h22eu4']))
        self.assertEqual(objs[0]['provider_url'], 'http://www.youtube.com/')
        self.assertEqual(objs[1]['provider_url'], 'http://yfrog.com')

    def test_error(self):
        http = Embedly(self.key)

        obj = http.oembed('http://www.embedly.com/this/is/a/bad/url')
        self.assertTrue(obj['error'])
        obj = http.oembed('http://blog.embed.ly/lsbsdlfldsf/asdfkljlas/klajsdlfkasdf')
        self.assertTrue(obj['error'])
        obj = http.oembed('http://twitpic/nothing/to/see/here')
        self.assertTrue(obj['error'])

    def test_multi_errors(self):
        http = Embedly(self.key)

        objs = list(http.oembed(['http://www.embedly.com/this/is/a/bad/url',
                                 'http://blog.embed.ly/alsd/slsdlf/asdlfj']))

        self.assertEqual(objs[0]['type'], 'error')
        self.assertEqual(objs[1]['type'], 'error')

        objs = list(http.oembed(['http://blog.embed.ly/lsbsdlfldsf/asdf/kl',
                                 'http://twitpic.com/nothing/to/see/here']))
        self.assertEqual(objs[0]['type'], 'error')
        self.assertEqual(objs[1]['type'], 'error')

        objs = list(http.oembed(['http://blog.embed.ly/lsbsdlfldsf/asdf/kl',
                                 'http://yfrog.com/h22eu4j']))
        self.assertEqual(objs[0]['type'], 'error')
        self.assertEqual(objs[1]['type'], 'photo')

        objs = list(http.oembed(['http://yfrog.com/h22eu4j',
                                 'http://www.scribd.com/asdf/asdf/asdfasdf']))
        self.assertEqual(objs[0]['type'], 'photo')
        self.assertEqual(objs[1]['type'], 'error')

    def test_raw_content_in_request(self):
        client = Embedly(self.key)
        response = client.oembed(
            'http://www.scribd.com/doc/13994900/Easter',
            raw=True)

        self.assertEqual(response['raw'], response.data['raw'])

        parsed = json.loads(response['raw'].decode('utf-8'))
        self.assertEqual(response['type'], parsed['type'])

    def test_regex_url_matches(self):
        regex = [
            'http://.*youtube\\.com/watch.*',
            'http://www\\.vimeo\\.com/.*']
        client = Embedly(self.key)
        client._regex = re.compile('|'.join(regex))

        self.assertTrue(
            client.is_supported('http://www.youtube.com/watch?v=Zk7dDekYej0'))
        self.assertTrue(
            client.is_supported('http://www.vimeo.com/18150336'))
        self.assertFalse(
            client.is_supported('http://vimeo.com/18150336'))
        self.assertFalse(
            client.is_supported('http://yfrog.com/h22eu4j'))

    @mock.patch.object(Embedly, 'get_services')
    def test_regex_access_triggers_get_services(self, mock_services):
        client = Embedly(self.key)
        client.regex

        self.assertTrue(mock_services.called)
        self.assertIsNone(client._regex)

    def test_services_can_be_manually_configured(self):
        client = Embedly(self.key)
        client.services = ['nothing', 'like', 'real', 'response', 'data']

        self.assertTrue('nothing' in client.get_services())
        self.assertEqual(len(client.get_services()), 5)

    @mock.patch('httplib2.Http', autospec=True)
    def test_services_remains_empty_on_failed_http(self, MockHttp):
        MockHttp.return_value.request.return_value = ({'status': 500}, "")

        client = Embedly(self.key)
        client.get_services()

        self.assertFalse(client.services)
        self.assertTrue(MockHttp.return_value.request.called)

    def test_get_services_retrieves_data_and_builds_regex(self):
        client = Embedly(self.key)
        client.get_services()

        self.assertGreater(len(client.services), 0)
        self.assertTrue(client.regex.match('http://yfrog.com/h22eu4j'))

    def test_extract(self):
        client = Embedly(self.key)
        response = client.extract('http://vimeo.com/18150336')

        self.assertEqual(response.method, 'extract')
        self.assertEqual(response['provider_name'], 'Vimeo')

    def test_preview(self):
        client = Embedly(self.key)
        response = client.preview('http://vimeo.com/18150336')

        self.assertEqual(response.method, 'preview')
        self.assertEqual(response['provider_name'], 'Vimeo')

    def test_objectify(self):
        client = Embedly(self.key)
        response = client.objectify('http://vimeo.com/18150336')

        self.assertEqual(response.method, 'objectify')
        self.assertEqual(response['provider_name'], 'Vimeo')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()  # pragma: no cover

########NEW FILE########
