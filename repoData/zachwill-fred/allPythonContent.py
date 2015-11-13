__FILENAME__ = api
"""
Simplified functions for using the Fred API.
"""

import os
from .core import Fred


def key(api_key):
    os.environ['FRED_API_KEY'] = api_key
    return Fred()


#####################
# Category
#####################

def category(**kwargs):
    """Get a category."""
    if 'series' in kwargs:
        kwargs.pop('series')
        path = 'series'
    else:
        path = None
    return Fred().category(path, **kwargs)


def categories(identifier, **kwargs):
    """Just in case someone misspells the method."""
    kwargs['category_id'] = identifier
    return category(**kwargs)


def children(category_id=None, **kwargs):
    """Get child categories for a specified parent category."""
    kwargs['category_id'] = category_id
    return Fred().category('children', **kwargs)


def related(identifier, **kwargs):
    """Get related categories for a specified category."""
    kwargs['category_id'] = identifier
    return Fred().category('related', **kwargs)


def category_series(identifier, **kwargs):
    """Get the series in a category."""
    kwargs['category_id'] = identifier
    return Fred().category('series', **kwargs)


#####################
# Releases
#####################

def release(release_id, **kwargs):
    """Get the release of economic data."""
    kwargs['release_id'] = release_id
    return Fred().release(**kwargs)


def releases(release_id=None, **kwargs):
    """Get all releases of economic data."""
    if not 'id' in kwargs and release_id is not None:
        kwargs['release_id'] = release_id
        return Fred().release(**kwargs)
    return Fred().releases(**kwargs)


def dates(**kwargs):
    """Get release dates for economic data."""
    return Fred().releases('dates', **kwargs)


#####################
# Series
#####################

def series(identifier=None, **kwargs):
    """Get an economic data series."""
    if identifier:
        kwargs['series_id'] = identifier
    if 'release' in kwargs:
        kwargs.pop('release')
        path = 'release'
    elif 'releases' in kwargs:
        kwargs.pop('releases')
        path = 'release'
    else:
        path = None
    return Fred().series(path, **kwargs)


def observations(identifier, **kwargs):
    """Get an economic data series."""
    kwargs['series_id'] = identifier
    return Fred().series('observations', **kwargs)


def search(text, **kwargs):
    """Get economic data series that match keywords."""
    kwargs['search_text'] = text
    return Fred().series('search', **kwargs)


def updates(**kwargs):
    """Get economic data series sorted in descending order."""
    return Fred().series('updates', **kwargs)


def vintage(identifier, **kwargs):
    """
    Get the dates in history when a series' data values were revised or new
    data values were released.
    """
    kwargs['series_id'] = identifier
    return Fred().series('vintagedates', **kwargs)


#####################
# Sources
#####################

def source(source_id=None, **kwargs):
    """Get a source of economic data."""
    if source_id is not None:
        kwargs['source_id'] = source_id
    elif 'id' in kwargs:
        source_id = kwargs.pop('id')
        kwargs['source_id'] = source_id
    if 'releases' in kwargs:
        kwargs.pop('releases')
        path = 'releases'
    else:
        path = None
    return Fred().source(path, **kwargs)


def sources(source_id=None, **kwargs):
    """Get the sources of economic data."""
    if source_id or 'id' in kwargs:
        return source(source_id, **kwargs)
    return Fred().sources(**kwargs)

########NEW FILE########
__FILENAME__ = core
"""
FRED API documentation: http://api.stlouisfed.org/docs/fred/

Core functionality for interacting with the FRED API.
"""

import os
import requests

try:
    from itertools import ifilter as filter
except ImportError:
    pass

try:
    import simplejson as json
except ImportError:
    import json


class Fred(object):
    """An easy-to-use Python wrapper over the St. Louis FRED API."""

    def __init__(self, api_key='', xml_output=False):
        if 'FRED_API_KEY' in os.environ:
            self.api_key = os.environ['FRED_API_KEY']
        else:
            self.api_key = api_key
        self.xml = xml_output
        self.endpoint = 'http://api.stlouisfed.org/fred/'

    def _create_path(self, *args):
        """Create the URL path with the Fred endpoint and given arguments."""
        args = filter(None, args)
        path = self.endpoint + '/'.join(args)
        return path

    def get(self, *args, **kwargs):
        """Perform a GET request againt the Fred API endpoint."""
        location = args[0]
        params = self._get_keywords(location, kwargs)
        url = self._create_path(*args)
        request = requests.get(url, params=params)
        content = request.content
        self._request = request
        return self._output(content)

    def _get_keywords(self, location, keywords):
        """Format GET request's parameters from keywords."""
        if 'xml' in keywords:
            keywords.pop('xml')
            self.xml = True
        else:
            keywords['file_type'] = 'json'
        if 'id' in keywords:
            if location != 'series':
                location = location.rstrip('s')
            key = '%s_id' % location
            value = keywords.pop('id')
            keywords[key] = value
        if 'start' in keywords:
            time = keywords.pop('start')
            keywords['realtime_start'] = time
        if 'end' in keywords:
            time = keywords.pop('end')
            keywords['realtime_end'] = time
        if 'sort' in keywords:
            order = keywords.pop('sort')
            keywords['sort_order'] = order
        keywords['api_key'] = self.api_key
        return keywords

    def _output(self, content):
        """Return the output from a given GET request."""
        if self.xml:
            return content
        return json.loads(content)

    def category(self, path=None, **kwargs):
        """
        Get a specific category.

        >>> Fred().category(category_id=125)
        """
        return self.get('category', path, **kwargs)

    def release(self, path=None, **kwargs):
        """
        Get a release of economic data.

        >>> Fred().release('series', release_id=51)
        """
        return self.get('release', path, **kwargs)

    def releases(self, path=None, **kwargs):
        """
        Get all releases of economic data.

        >>> Fred().releases('dates', limit=10)
        """
        return self.get('releases', path, **kwargs)

    def series(self, path=None, **kwargs):
        """
        Get economic series of data.

        >>> Fred().series('search', search_text="money stock")
        """
        return self.get('series', path, **kwargs)

    def source(self, path=None, **kwargs):
        """
        Get a single source of economic data.

        >>> Fred().source(source_id=51)
        """
        return self.get('source', path, **kwargs)

    def sources(self, path=None, **kwargs):
        """
        Get all of FRED's sources of economic data.

        >>> Fred().sources()
        """
        return self.get('sources', path, **kwargs)


########NEW FILE########
__FILENAME__ = test
"""
Tests for V2 of Fred API wrapper.
"""

import os
import unittest

import fred
from mock import Mock


class Category(unittest.TestCase):

    def setUp(self):
        fred.core.requests = Mock()
        fred.core.json = Mock()
        self.get = fred.core.requests.get

    def test_fred_category(self):
        fred.category()
        expected = 'http://api.stlouisfed.org/fred/category'
        params = {'api_key': '', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_category_series(self):
        fred.key('123abc')
        fred.category(series=True)
        expected = 'http://api.stlouisfed.org/fred/category/series'
        params = {'api_key': '123abc', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_category_children(self):
        fred.key('abc123')
        fred.children()
        expected = 'http://api.stlouisfed.org/fred/category/children'
        params = {'api_key': 'abc123', 'category_id': None, 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_category_related(self):
        fred.related(32073)
        expected = 'http://api.stlouisfed.org/fred/category/related'
        params = {'api_key': '', 'category_id': 32073, 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_category_series_function(self):
        fred.key('my_fred_key')
        fred.category_series(123)
        expected = 'http://api.stlouisfed.org/fred/category/series'
        params = {'api_key': 'my_fred_key', 'category_id': 123, 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def tearDown(self):
        os.environ['FRED_API_KEY'] = ''


class Releases(unittest.TestCase):

    def setUp(self):
        fred.core.requests = Mock()
        fred.core.json = Mock()
        self.get = fred.core.requests.get

    def test_fred_releases(self):
        fred.key('123')
        fred.releases()
        expected = 'http://api.stlouisfed.org/fred/releases'
        params = {'api_key': '123', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_releases_with_id_calls_release(self):
        fred.key('abc')
        fred.releases('123')
        expected = 'http://api.stlouisfed.org/fred/release'
        params = {'api_key': 'abc', 'release_id': '123', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_specific_release(self):
        fred.key('my_key')
        fred.release('123')
        expected = 'http://api.stlouisfed.org/fred/release'
        params = {'api_key': 'my_key', 'release_id': '123', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_releases_dates(self):
        fred.key('123')
        fred.dates()
        expected = 'http://api.stlouisfed.org/fred/releases/dates'
        params = {'api_key': '123', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_releases_dates_with_start_and_end_keywords(self):
        fred.key('github')
        fred.dates(start='2012-01-01', end='2012-03-16')
        expected = 'http://api.stlouisfed.org/fred/releases/dates'
        params = {
            'api_key': 'github',
            'realtime_start': '2012-01-01',
            'realtime_end': '2012-03-16',
            'file_type': 'json'
        }
        self.get.assert_called_with(expected, params=params)

    def tearDown(self):
        os.environ['FRED_API_KEY'] = ''


class Series(unittest.TestCase):

    def setUp(self):
        fred.core.requests = Mock()
        fred.core.json = Mock()
        self.get = fred.core.requests.get

    def test_fred_series(self):
        fred.key('abc')
        fred.series()
        expected = 'http://api.stlouisfed.org/fred/series'
        params = {'api_key': 'abc', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_series_release(self):
        fred.key('abc')
        fred.series(releases=True)
        expected = 'http://api.stlouisfed.org/fred/series/release'
        params = {'api_key': 'abc', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_series_observations(self):
        fred.key('ohai')
        fred.observations("AAA")
        expected = 'http://api.stlouisfed.org/fred/series/observations'
        params = {'api_key': 'ohai', 'series_id': 'AAA', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_series_search(self):
        fred.key('123')
        fred.search('money stock')
        expected = 'http://api.stlouisfed.org/fred/series/search'
        params = {'api_key': '123', 'search_text': 'money stock', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_series_updates(self):
        fred.key('ALL THE FRED API!')
        fred.updates()
        expected = 'http://api.stlouisfed.org/fred/series/updates'
        params = {'api_key': 'ALL THE FRED API!', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_series_vintage_dates(self):
        fred.key('123abc')
        fred.vintage('AAA', sort='desc')
        expected = 'http://api.stlouisfed.org/fred/series/vintagedates'
        params = {
            'api_key': '123abc',
            'series_id': 'AAA',
            'sort_order': 'desc',
            'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def tearDown(self):
        os.environ['FRED_API_KEY'] = ''


class Sources(unittest.TestCase):

    def setUp(self):
        fred.core.requests = Mock()
        fred.core.json = Mock()
        self.get = fred.core.requests.get

    def test_fred_sources(self):
        fred.key('moar fred')
        fred.sources()
        expected = 'http://api.stlouisfed.org/fred/sources'
        params = {'api_key': 'moar fred', 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_sources_accidentally_passed_source_id(self):
        fred.key('123')
        fred.sources(123)
        expected = 'http://api.stlouisfed.org/fred/source'
        params = {'api_key': '123', 'source_id': 123, 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def test_fred_source(self):
        fred.key('123')
        fred.source(25)
        expected = 'http://api.stlouisfed.org/fred/source'
        params = {'api_key': '123', 'source_id': 25, 'file_type': 'json'}
        self.get.assert_called_with(expected, params=params)

    def tearDown(self):
        os.environ['FRED_API_KEY'] = ''

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
