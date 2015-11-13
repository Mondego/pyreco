__FILENAME__ = cases
import unittest
import sys

from testscenarios import TestWithScenarios


if sys.version_info >= (3, 0):
    from urllib.request import urlopen
    from urllib.error import URLError
    from tests.server import tpb
else:
    from urllib2 import urlopen, URLError
    from server import tpb


class RemoteTestCase(TestWithScenarios):
    _do_local = True
    _do_remote = False

    @classmethod
    def setUpClass(cls):
        """
        Start local server and setup local and remote urls defaulting to local
        one.
        """
        cls.server = tpb
        cls.server.start()
        cls.remote = 'http://thepiratebay.org'
        cls.local = cls.server.url
        cls.scenarios = []
        if cls._do_local:
            cls.scenarios.append(('local', {'url': cls.local}))
        if cls._do_remote and cls._is_remote_available:
            cls.scenarios.append(('remote', {'url': cls.remote}))

    @classmethod
    def tearDownClass(cls):
        """
        Stop local server.
        """
        cls.server.stop()

    @property
    @classmethod
    def _is_remote_available(cls):
        """
        Check connectivity to remote.
        """
        try:
            urlopen(cls.remote)
        except URLError:
            return False
        else:
            return True

    def _assertCountEqual(self, first, second):
        """
        Compatibility function to test if the first sequence contains the
        same elements as the second one.

        This was done in order to have backwards compatibility between python
        2.x and 3.x
        """
        if sys.version_info >= (3, 0):
            self.assertCountEqual(first, second)
        else:
            self.assertItemsEqual(first, second)

########NEW FILE########
__FILENAME__ = server
from time import sleep
from os import path
from multiprocessing import Process

from bottle import Bottle, route, run, template


PRESETS_DIR = path.join(path.dirname(__file__), 'presets')


def template_response(func):
    def wrapper(*args, **kwargs):
        filename = func(*args, **kwargs)
        with open(path.join(PRESETS_DIR, filename)) as f:
            content = f.read()
        return template(content)
    return wrapper


class TPBApp(Bottle):

    def __init__(self, host='localhost', port=8000):
        super(TPBApp, self).__init__()
        self.host = host
        self.port = port
        self.process = None

    def run(self):
        run(self, host=self.host, port=self.port, debug=False, quiet=True)

    def start(self):
        self.process = Process(target=self.run)
        self.process.start()
        sleep(1)

    def stop(self):
        self.process.terminate()
        self.process = None

    @property
    def url(self):
        return 'http://{}:{}'.format(self.host, self.port)

tpb = TPBApp()


@tpb.route('/search/<query>/<page>/<ordering>/<category>')
@template_response
def search(**kwargs):
    return 'search.html'


@tpb.route('/recent/<page>')
@template_response
def recent(**kwargs):
    return 'recent.html'


@tpb.route('/top/<category>')
@template_response
def top(**kwargs):
    return 'top.html'


@tpb.route('/torrent/<id>/<name>')
@template_response
def torrent(**kwargs):
    return 'torrent.html'


@tpb.route('/ajax_details_filelist.php')
@template_response
def files(**kwargs):
    return 'files.html'

if __name__ == '__main__':
    tpb.run()

########NEW FILE########
__FILENAME__ = tests
from datetime import datetime, timedelta
import itertools
import sys
import os
import time
import unittest

from lxml import html

from tpb.tpb import TPB, Search, Recent, Top, List, Paginated
from tpb.constants import ConstantType, Constants, ORDERS, CATEGORIES
from tpb.utils import URL

if sys.version_info >= (3, 0):
    from urllib.request import urlopen
    from tests.cases import RemoteTestCase
    unicode = str
else:
    from urllib2 import urlopen
    from cases import RemoteTestCase


class ConstantsTestCase(RemoteTestCase):

    def test_extension(self):
        checks = [ORDERS, CATEGORIES]
        while checks:
            current = checks.pop()
            for name, attr in current.__dict__.items():
                if isinstance(attr, type):
                    self.assertTrue(attr.__class__, ConstantType)
                    checks.append(attr)

    def test_repr(self):
        class Alphanum(Constants):
            greek = True

            class Alpha:
                alpha = 'a'
                beta = 'b'
                gamma = 'c'

            class Num:
                alpha = 1
                beta = 2
                gamma = 3
        output = """\
Alphanum:
    Alpha:
        alpha: 'a'
        beta: 'b'
        gamma: 'c'
    Num:
        alpha: 1
        beta: 2
        gamma: 3
    greek: True
"""
        self.assertEqual(repr(Alphanum), output)
        self.assertEqual(str(Alphanum), output)


class PathSegmentsTestCase(RemoteTestCase):

    def setUp(self):
        self.segments = ['alpha', 'beta', 'gamma']
        self.defaults = ['0', '1', '2']
        self.url = URL('', '/', self.segments, self.defaults)

    def test_attributes(self):
        other_segments = ['one', 'two', 'three']
        other_url = URL('', '/', other_segments, self.defaults)
        for segment, other_segment in zip(self.segments, other_segments):
            self.assertTrue(hasattr(self.url, segment))
            self.assertFalse(hasattr(other_url, segment))
            self.assertTrue(hasattr(other_url, other_segment))
            self.assertFalse(hasattr(self.url, other_segment))

    def test_properties(self):
        self.assertEqual(str(self.url), '/0/1/2')
        self.url.alpha = '9'
        self.url.beta = '8'
        self.url.gamma = '7'
        self.assertEqual(str(self.url), '/9/8/7')


class ParsingTestCase(RemoteTestCase):

    def setUp(self):
        self.torrents = Search(self.url, 'tpb afk')

    def test_items(self):
        self.assertEqual(len(list(self.torrents.items())), 30)
        self.assertEqual(len(list(iter(self.torrents))), 30)

    def test_creation_dates(self):
        """
        Make sure torrents aren't lazily created.
        """
        alpha = time.time()
        # Create torrents
        torrents = self.torrents.items()
        time.sleep(1)
        # If they were lazily evaluated, they would be created now
        diff = next(torrents)._created[1] - alpha
        self.assertTrue(diff > 1)

    def test_torrent_rows(self):
        request = urlopen(str(self.torrents.url))
        document = html.parse(request)
        rows = self.torrents._get_torrent_rows(document.getroot())
        self.assertEqual(len(rows), 30)

    def test_torrent_build(self):
        for torrent in self.torrents.items():
            if torrent.title == 'TPB.AFK.2013.720p.h264-SimonKlose' and\
               torrent.user == 'SimonKlose':
                self.assertEqual(torrent.user_status, 'VIP')
                self.assertTrue(torrent.comments >= 313)
                self.assertEqual(torrent.has_cover, 'Yes')
                break


class TorrentTestCase(RemoteTestCase):

    def setUp(self):
        self.torrents = Search(self.url, 'tpb afk')

    def assertEqualDatetimes(self, *datetimes):
        datetimes = [d.replace(microsecond=0) for d in datetimes]
        return self.assertEqual(*datetimes)

    def test_created_timestamp_parse(self):
        for torrent in self.torrents.items():
            torrent.created
        torrent._created = ('1 sec ago', time.time())
        self.assertEqualDatetimes(
            torrent.created, datetime.now() - timedelta(seconds=1))
        torrent._created = ('1 min ago', time.time())
        self.assertEqualDatetimes(
            torrent.created, datetime.now() - timedelta(minutes=1))
        torrent._created = ('1 hour ago', time.time())
        self.assertEqualDatetimes(
            torrent.created, datetime.now() - timedelta(hours=1))
        torrent._created = ('Today', time.time())
        self.assertEqual(torrent.created.date(), datetime.now().date())
        torrent._created = ('Y-day', time.time())
        self.assertEqual(torrent.created.date(),
                         (datetime.now() - timedelta(days=1)).date())
        torrent._created = ('1 sec ago', time.time() - 60 * 60 * 24)
        self.assertEqualDatetimes(torrent.created, datetime.now() -
                                  timedelta(days=1, seconds=1))

    def test_info(self):
        for torrent in self.torrents.items():
            self.assertNotEqual('', torrent.info.strip())

    def test_files(self):
        for torrent in self.torrents.items():
            self.assertTrue(len(torrent.files) > 0)


class PaginationTestCase(RemoteTestCase):

    def setUp(self):
        self.torrents = Search(self.url, 'tpb afk')

    def test_page_items(self):
        self.assertEqual(len(list(self.torrents.items())), 30)

    def test_multipage_items(self):
        self.torrents.multipage()
        items = list(itertools.islice(self.torrents.items(), 50))
        self.assertEqual(len(items), 50)
        self.assertEqual(self.torrents.page(), 1)

    def test_last_page(self):
        class DummyList(List):
            pages_left = 5

            def items(self):
                if self.pages_left == 0:
                    raise StopIteration()
                for i in range(10):
                    yield i
                self.pages_left -= 1

        class DummySearch(Search, Paginated, DummyList):
            pass
        self.torrents = DummySearch(self.url, 'tpb afk').multipage()
        self.assertEqual(len(list(iter(self.torrents))), 50)


class SearchTestCase(RemoteTestCase):

    def setUp(self):
        self.torrents = Search(self.url, 'tpb afk')

    def test_url(self):
        self.assertEqual(str(self.torrents.url),
                         self.url + '/search/tpb%20afk/0/7/0')
        self.torrents.query('something').page(1).next().previous()
        self.torrents.order(9).category(100)
        self.assertEqual(self.torrents.query(), 'something')
        self.assertEqual(self.torrents.page(), 1)
        self.assertEqual(self.torrents.order(), 9)
        self.assertEqual(self.torrents.category(), 100)
        self.assertEqual(str(self.torrents.url),
                         self.url + '/search/something/1/9/100')

    def test_torrents(self):
        for item in self.torrents:
            self.assertEqual(unicode, type(item.title))
            self.assertEqual(unicode, type(item.user))
            self.assertTrue(hasattr(item, 'url'))
            # ensure the URL points to the /torrent/ html page
            self.assertTrue(item.url.path().startswith('/torrent/'))


class RecentTestCase(RemoteTestCase):

    def setUp(self):
        self.torrents = Recent(self.url)

    def test_url(self):
        self.assertEqual(str(self.torrents.url),
                         self.url + '/recent/0')
        self.torrents.page(1).next().previous()
        self.assertEqual(str(self.torrents.url),
                         self.url + '/recent/1')


class TopTestCase(RemoteTestCase):

    def setUp(self):
        self.torrents = Top(self.url)

    def test_url(self):
        self.assertEqual(str(self.torrents.url),
                         self.url + '/top/0')
        self.torrents.category(100)
        self.assertEqual(str(self.torrents.url),
                         self.url + '/top/100')

    def test_results(self):
        self.assertEqual(len(list(self.torrents.items())), 100)


class TPBTestCase(RemoteTestCase):

    def setUp(self):
        self.tpb = TPB(self.url)

    def test_search(self):
        kwargs = {'query': 'tpb afk', 'page': 5, 'order': 9, 'category': 100}
        a_search = self.tpb.search(**kwargs)
        b_search = Search(self.url, **kwargs)
        self.assertTrue(isinstance(a_search, Search))
        self.assertTrue(isinstance(b_search, Search))
        self.assertEqual(str(a_search.url), str(b_search.url))

    def test_recent(self):
        kwargs = {'page': 5}
        a_recent = self.tpb.recent(**kwargs)
        b_recent = Recent(self.url, **kwargs)
        self.assertTrue(isinstance(a_recent, Recent))
        self.assertTrue(isinstance(b_recent, Recent))
        self.assertEqual(str(a_recent.url), str(b_recent.url))

    def test_top(self):
        kwargs = {'category': 100}
        a_top = self.tpb.top(**kwargs)
        b_top = Top(self.url, **kwargs)
        self.assertTrue(isinstance(a_top, Top))
        self.assertTrue(isinstance(b_top, Top))
        self.assertEqual(str(a_top.url), str(b_top.url))


def load_tests(loader, tests, discovery):
    for attr, envvar in [('_do_local', 'LOCAL'), ('_do_remote', 'REMOTE')]:
        envvar = os.environ.get(envvar)
        if envvar is not None:
            setattr(RemoteTestCase, attr, envvar.lower() in ['true', '1'])
    return unittest.TestSuite(tests)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = constants
import sys

if sys.version_info >= (3, 0):
    class_type = type
else:
    from new import classobj
    class_type = classobj


class ConstantType(type):

    """
    Tree representation metaclass for class attributes. Metaclass is extended
    to all child classes too.
    """
    def __new__(cls, clsname, bases, dct):
        """
        Extend metaclass to all class attributes too.
        """
        attrs = {}
        for name, attr in dct.items():
            if isinstance(attr, class_type):
                # substitute attr with a new class with Constants as
                # metaclass making it possible to spread this same method
                # to all child classes
                attr = ConstantType(
                    attr.__name__, attr.__bases__, attr.__dict__)
            attrs[name] = attr
        return super(ConstantType, cls).__new__(cls, clsname, bases, attrs)

    def __repr__(cls):
        """
        Tree representation of class attributes. Child classes are also
        represented.
        """
        # dump current class name
        tree = cls.__name__ + ':\n'
        for name in dir(cls):
            if not name.startswith('_'):
                attr = getattr(cls, name)
                output = repr(attr)
                if not isinstance(attr, ConstantType):
                    output = '{}: {}'.format(name, output)
                # indent all child attrs
                tree += '\n'.join([' ' * 4 + line
                                  for line in output.splitlines()]) + '\n'
        return tree

    def __str__(cls):
        return repr(cls)


Constants = ConstantType('Constants', (object,), {})


class ORDERS(Constants):

    class NAME:
        DES = 1
        ASC = 2

    class UPLOADED:
        DES = 3
        ASC = 4

    class SIZE:
        DES = 5
        ASC = 6

    class SEEDERS:
        DES = 7
        ASC = 8

    class LEECHERS:
        DES = 9
        ASC = 10

    class UPLOADER:
        DES = 11
        ASC = 12

    class TYPE:
        DES = 13
        ASC = 14


class CATEGORIES(Constants):
    ALL = 0

    class AUDIO:
        ALL = 100
        MUSIC = 101
        AUDIO_BOOKS = 102
        SOUND_CLIPS = 103
        FLAC = 104
        OTHER = 199

    class VIDEO:
        ALL = 200
        MOVIES = 201
        MOVIES_DVDR = 202
        MUSIC_VIDEOS = 203
        MOVIE_CLIPS = 204
        TV_SHOWS = 205
        HANDHELD = 206
        HD_MOVIES = 207
        HD_TV_SHOWS = 208
        THREE_DIMENSIONS = 209
        OTHER = 299

    class APPLICATIONS:
        ALL = 300
        WINDOWS = 301
        MAC = 302
        UNIX = 303
        HANDHELD = 304
        IOS = 305
        ANDROID = 306
        OTHER = 399

    class GAMES:
        ALL = 400
        PC = 401
        MAC = 402
        PSX = 403
        XBOX360 = 404
        WII = 405
        HANDHELD = 406
        IOS = 407
        ANDROID = 408
        OTHER = 499

    class PORN:
        ALL = 500
        MOVIES = 501
        MOVIES_DVDR = 502
        PICTURES = 503
        GAMES = 504
        HD_MOVIES = 505
        MOVIE_CLIPS = 506
        OTHER = 599

    class OTHER:
        EBOOKS = 601
        COMICS = 602
        PICTURES = 603
        COVERS = 604
        PHYSIBLES = 605
        OTHER = 699

########NEW FILE########
__FILENAME__ = tpb
#!/usr/bin/env python

"""
Unofficial Python API for ThePirateBay.

@author Karan Goel
@email karan@goel.im
"""

from __future__ import unicode_literals

import datetime
import dateutil.parser
from functools import wraps
from lxml import html
import os
import re
import sys
import time

from .utils import URL

if sys.version_info >= (3, 0):
    from urllib.request import urlopen
    unicode = str
else:
    from urllib2 import urlopen


def self_if_parameters(func):
    """
    If any parameter is given, the method's binded object is returned after
    executing the function. Else the function's result is returned.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if args or kwargs:
            return self
        else:
            return result
    return wrapper


class List(object):

    """
    Abstract class for parsing a torrent list at some url and generate torrent
    objects to iterate over. Includes a resource path parser.
    """

    _meta = re.compile('Uploaded (.*), Size (.*), ULed by (.*)')
    base_path = ''

    def items(self):
        """
        Request URL and parse response. Yield a ``Torrent`` for every torrent
        on page.
        """
        request = urlopen(str(self.url))
        document = html.parse(request)
        root = document.getroot()
        items = [self._build_torrent(row) for row in
                 self._get_torrent_rows(root)]
        for item in items:
            yield item

    def __iter__(self):
        return self.items()

    def _get_torrent_rows(self, page):
        """
        Returns all 'tr' tag rows as a list of tuples. Each tuple is for
        a single torrent.
        """
        table = page.find('.//table')  # the table with all torrent listing
        if table is None:  # no table means no results:
            return []
        else:
            return table.findall('.//tr')[1:]  # get all rows but header

    def _build_torrent(self, row):
        """
        Builds and returns a Torrent object for the given parsed row.
        """
        # Scrape, strip and build!!!
        cols = row.findall('.//td')  # split the row into it's columns

        # this column contains the categories
        [category, sub_category] = [c.text for c in cols[0].findall('.//a')]

        # this column with all important info
        links = cols[1].findall('.//a')  # get 4 a tags from this columns
        title = unicode(links[0].text)
        url = self.url.build().path(links[0].get('href'))
        magnet_link = links[1].get('href')  # the magnet download link
        try:
            torrent_link = links[2].get('href')  # the torrent download link
            if not torrent_link.endswith('.torrent'):
                torrent_link = None
        except IndexError:
            torrent_link = None
        comments = 0
        has_cover = 'No'
        images = cols[1].findall('.//img')
        for image in images:
            image_title = image.get('title')
            if image_title is None:
                continue
            if "comments" in image_title:
                comments = int(image_title.split(" ")[3])
            if "cover" in image_title:
                has_cover = 'Yes'
        user_status = "MEMBER"
        if links[-2].get('href').startswith("/user/"):
            user_status = links[-2].find('.//img').get('title')
        meta_col = cols[1].find('.//font').text_content()  # don't need user
        match = self._meta.match(meta_col)
        created = match.groups()[0].replace('\xa0', ' ')
        size = match.groups()[1].replace('\xa0', ' ')
        user = match.groups()[2]  # uploaded by user

        # last 2 columns for seeders and leechers
        seeders = int(cols[2].text)
        leechers = int(cols[3].text)
        t = Torrent(title, url, category, sub_category, magnet_link,
                    torrent_link, comments, has_cover, user_status, created,
                    size, user, seeders, leechers)
        return t


class Paginated(List):

    """
    Abstract class on top of ``List`` for parsing a torrent list with
    pagination capabilities.
    """

    def __init__(self, *args, **kwargs):
        super(Paginated, self).__init__(*args, **kwargs)
        self._multipage = False

    def items(self):
        """
        Request URL and parse response. Yield a ``Torrent`` for every torrent
        on page. If in multipage mode, Torrents from next pages are
        automatically chained.
        """
        if self._multipage:
            while True:
                # Pool for more torrents
                items = super(Paginated, self).items()
                # Stop if no more torrents
                first = next(items, None)
                if first is None:
                    raise StopIteration()
                # Yield them if not
                else:
                    yield first
                    for item in items:
                        yield item
                # Go to the next page
                self.next()
        else:
            for item in super(Paginated, self).items():
                yield item

    def multipage(self):
        """
        Enable multipage iteration.
        """
        self._multipage = True
        return self

    @self_if_parameters
    def page(self, number=None):
        """
        If page is given, modify the URL correspondingly, return the current
        page otherwise.
        """
        if number is None:
            return int(self.url.page)
        self.url.page = str(number)

    def next(self):
        """
        Jump to the next page.
        """
        self.page(self.page() + 1)
        return self

    def previous(self):
        """
        Jump to the previous page.
        """
        self.page(self.page() - 1)
        return self


class Search(Paginated):

    """
    Paginated search featuring query, category and order management.
    """
    base_path = '/search'

    def __init__(self, base_url, query, page='0', order='7', category='0'):
        super(Search, self).__init__()
        self.url = URL(base_url, self.base_path,
                       segments=['query', 'page', 'order', 'category'],
                       defaults=[query, str(page), str(order), str(category)],
                       )

    @self_if_parameters
    def query(self, query=None):
        """
        If query is given, modify the URL correspondingly, return the current
        query otherwise.
        """
        if query is None:
            return self.url.query
        self.url.query = query

    @self_if_parameters
    def order(self, order=None):
        """
        If order is given, modify the URL correspondingly, return the current
        order otherwise.
        """
        if order is None:
            return int(self.url.order)
        self.url.order = str(order)

    @self_if_parameters
    def category(self, category=None):
        """
        If category is given, modify the URL correspondingly, return the
        current category otherwise.
        """
        if category is None:
            return int(self.url.category)
        self.url.category = str(category)


class Recent(Paginated):

    """
    Paginated most recent torrents.
    """
    base_path = '/recent'

    def __init__(self, base_url, page='0'):
        super(Recent, self).__init__()
        self.url = URL(base_url, self.base_path,
                       segments=['page'],
                       defaults=[str(page)],
                       )


class Top(List):

    """
    Top torrents featuring category management.
    """
    base_path = '/top'

    def __init__(self, base_url, category='0'):
        self.url = URL(base_url, self.base_path,
                       segments=['category'],
                       defaults=[str(category)],
                       )

    @self_if_parameters
    def category(self, category=None):
        """
        If category is given, modify the URL correspondingly, return the
        current category otherwise.
        """
        if category is None:
            return int(self.url.category)
        self.url.category = str(category)


class TPB(object):

    """
    TPB API with searching, most recent torrents and top torrents support.
    Passes on base_url to the instantiated Search, Recent and Top classes.
    """

    def __init__(self, base_url):
        self.base_url = base_url

    def search(self, query, page=0, order=7, category=0, multipage=False):
        """
        Searches TPB for query and returns a list of paginated Torrents capable
        of changing query, categories and orders.
        """
        search = Search(self.base_url, query, page, order, category)
        if multipage:
            search.multipage()
        return search

    def recent(self, page=0):
        """
        Lists most recent Torrents added to TPB.
        """
        return Recent(self.base_url, page)

    def top(self, category=0):
        """
        Lists top Torrents on TPB optionally filtering by category.
        """
        return Top(self.base_url, category)


class Torrent(object):

    """
    Holder of a single TPB torrent.
    """

    def __init__(self, title, url, category, sub_category, magnet_link,
                 torrent_link, comments, has_cover, user_status, created,
                 size, user, seeders, leechers):
        self.title = title  # the title of the torrent
        self.url = url  # TPB url for the torrent
        self.id = self.url.path_segments()[1]
        self.category = category  # the main category
        self.sub_category = sub_category  # the sub category
        self.magnet_link = magnet_link  # magnet download link
        self.torrent_link = torrent_link  # .torrent download link
        self.comments = comments
        self.has_cover = has_cover
        self.user_status = user_status
        self._created = (created, time.time())  # uploaded date, current time
        self.size = size  # size of torrent
        self.user = user  # username of uploader
        self.seeders = seeders  # number of seeders
        self.leechers = leechers  # number of leechers
        self._info = None
        self._files = {}

    @property
    def info(self):
        if self._info is None:
            request = urlopen(str(self.url))
            document = html.parse(request)
            root = document.getroot()
            info = root.cssselect('#details > .nfo > pre')[0].text_content()
            self._info = info
        return self._info

    @property
    def files(self):
        if not self._files:
            path = '/ajax_details_filelist.php?id={id}'.format(id=self.id)
            url = self.url.path(path)
            request = urlopen(str(url))
            document = html.parse(request)
            root = document.getroot()
            rows = root.findall('.//tr')
            for row in rows:
                name, size = [unicode(v.text_content())
                              for v in row.findall('.//td')]
                self._files[name] = size.replace('\xa0', ' ')
        return self._files

    @property
    def created(self):
        """
        Attempt to parse the human readable torrent creation datetime.
        """
        timestamp, current = self._created
        if timestamp.endswith('ago'):
            quantity, kind, ago = timestamp.split()
            quantity = int(quantity)
            if 'sec' in kind:
                current -= quantity
            elif 'min' in kind:
                current -= quantity * 60
            elif 'hour' in kind:
                current -= quantity * 60 * 60
            return datetime.datetime.fromtimestamp(current)
        current = datetime.datetime.fromtimestamp(current)
        timestamp = timestamp.replace(
            'Y-day', str(current.date() - datetime.timedelta(days=1)))
        timestamp = timestamp.replace('Today', current.date().isoformat())
        try:
            return dateutil.parser.parse(timestamp)
        except:
            return current

    def print_torrent(self):
        """
        Print the details of a torrent
        """
        print('Title: %s' % self.title)
        print('URL: %s' % self.url)
        print('Category: %s' % self.category)
        print('Sub-Category: %s' % self.sub_category)
        print('Magnet Link: %s' % self.magnet_link)
        print('Torrent Link: %s' % self.torrent_link)
        print('Uploaded: %s' % self.created)
        print('Comments: %d' % self.comments)
        print('Has Cover Image: %s' % self.has_cover)
        print('User Status: %s' % self.user_status)
        print('Size: %s' % self.size)
        print('User: %s' % self.user)
        print('Seeders: %d' % self.seeders)
        print('Leechers: %d' % self.leechers)

    def __repr__(self):
        return '{0} by {1}'.format(self.title, self.user)

########NEW FILE########
__FILENAME__ = utils
from collections import OrderedDict

from purl import URL as PURL


def URL(base, path, segments=None, defaults=None):
    """
    URL segment handler capable of getting and setting segments by name. The
    URL is constructed by joining base, path and segments.

    For each segment a property capable of getting and setting that segment is
    created dynamically.
    """
    # Make a copy of the Segments class
    url_class = type(Segments.__name__, Segments.__bases__,
                     dict(Segments.__dict__))
    segments = [] if segments is None else segments
    defaults = [] if defaults is None else defaults
    # For each segment attach a property capable of getting and setting it
    for segment in segments:
        setattr(url_class, segment, url_class._segment(segment))
    # Instantiate the class with the actual parameters
    return url_class(base, path, segments, defaults)


class Segments(object):

    """
    URL segment handler, not intended for direct use. The URL is constructed by
    joining base, path and segments.
    """

    def __init__(self, base, path, segments, defaults):
        # Preserve the base URL
        self.base = PURL(base, path=path)
        # Map the segments and defaults lists to an ordered dict
        self.segments = OrderedDict(zip(segments, defaults))

    def build(self):
        # Join base segments and segments
        segments = self.base.path_segments() + tuple(self.segments.values())
        # Create a new URL with the segments replaced
        url = self.base.path_segments(segments)
        return url

    def __str__(self):
        return self.build().as_string()

    def _get_segment(self, segment):
        return self.segments[segment]

    def _set_segment(self, segment, value):
        self.segments[segment] = value

    @classmethod
    def _segment(cls, segment):
        """
        Returns a property capable of setting and getting a segment.
        """
        return property(
            fget=lambda x: cls._get_segment(x, segment),
            fset=lambda x, v: cls._set_segment(x, segment, v),
        )

########NEW FILE########
