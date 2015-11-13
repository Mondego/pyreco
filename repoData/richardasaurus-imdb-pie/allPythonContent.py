__FILENAME__ = imdbpie
import json
import time
import requests
import hashlib
import re

# handle python 2 and python 3 imports
try:
    from urllib.parse import urlencode
    import html.parser as htmlparser
except ImportError:
    from urllib import urlencode
    import HTMLParser as htmlparser

base_uri = 'app.imdb.com'
api_key = '2wex6aeu6a8q9e49k7sfvufd6rhh0n'
sha1_key = hashlib.sha1(api_key.encode('utf-8')).hexdigest()


class Imdb(object):

    def __init__(self, options=None):
        self.locale = 'en_US'
        self.base_uri = base_uri

        if options is None:
            options = {}

        self.options = options
        if options.get('anonymize') is True:
            self.base_uri = 'youtubeproxy.org/default.aspx?prx=https://{0}'.format(self.base_uri)

        if options.get('exclude_episodes') is True:
            self.exclude_episodes = True
        else:
            self.exclude_episodes = False

        if options.get('locale'):
            self.locale = options.get('locale')

    def build_url(self, path, params):
        default_params = {"api": "v1",
                          "appid": "iphone1_1",
                          "apiPolicy": "app1_1",
                          "apiKey": sha1_key,
                          "locale": self.locale,
                          "timestamp": int(time.time())}

        query_params = dict(list(default_params.items()) + list(params.items()))
        query_params = urlencode(query_params)
        return 'https://{0}{1}?{2}'.format(self.base_uri, path, query_params)

    def find_movie_by_id(self, imdb_id, json=False):
        imdb_id = self.validate_id(imdb_id)
        url = self.build_url('/title/maindetails', {'tconst': imdb_id})
        result = self.get(url)
        if 'error' in result:
            return False
        # if the result is a re-dir, see imdb id tt0000021 for e.g...
        if result["data"].get('tconst') != result["data"].get('news').get('channel'):
            return False

        #get the full cast information, add key if not present
        result["data"][str("credits")] = self.get_credits(imdb_id)

        if self.exclude_episodes is True and result["data"].get('type') == 'tv_episode':
            return False
        elif json is True:
            return result["data"]
        else:
            title = Title(**result["data"])
            return title

    def get_credits(self, imdb_id):
        imdb_id = self.validate_id(imdb_id)
        url = self.build_url('/title/fullcredits', {'tconst': imdb_id})
        result = self.get(url)
        return result.get('data').get('credits')

    def filter_out(self, string):
        return string not in ('id', 'title')

    def movie_exists(self, imdb_id):
        """
        Check with imdb, does a movie exist
        """
        imdb_id = self.validate_id(imdb_id)
        if imdb_id:
            results = self.find_movie_by_id(imdb_id)
            if results:
                return True
            else:
                return False
        else:
            return False

    def validate_id(self, imdb_id):
        """
        Check imdb id is a 7 digit number
        """
        match = re.findall(r'tt(\d+)', imdb_id, re.IGNORECASE)
        if match:
            id_num = match[0]
            if len(id_num) is not 7:
                #pad id to 7 digits
                id_num = id_num.zfill(7)
            return 'tt' + id_num
        else:
            return False

    def find_by_title(self, title):
        default_find_by_title_params = {'json': '1',
                                        'nr': 1,
                                        'tt': 'on',
                                        'q': title}
        query_params = urlencode(default_find_by_title_params)
        results = self.get(('http://www.imdb.com/'
                            'xml/find?{0}').format(query_params))

        keys = ['title_popular',
                'title_exact',
                'title_approx',
                'title_substring']
        title_results = []

        html_unescape = htmlparser.HTMLParser().unescape

        # Loop through all results and build a list with popular matches first
        for key in keys:
            if key in results:
                for r in results[key]:
                    year = None
                    year_match = re.search(r'(\d{4})', r['title_description'])
                    if year_match:
                        year = year_match.group(0)

                    title_match = {
                        'title': html_unescape(r['title']),
                        'year': year,
                        'imdb_id': r['id']
                    }
                    title_results.append(title_match)

        return title_results

    def top_250(self):
        url = self.build_url('/chart/top', {})
        result = self.get(url)
        return result["data"]["list"]["list"]

    def popular_shows(self):
        url = self.build_url('/chart/tv', {})
        result = self.get(url)
        return result["data"]["list"]

    def get_images(self, result):
        if 'error' in result:
            return False

        results = []
        if 'photos' in result.get('data'):
            for image in result.get('data').get('photos'):
                results.append(Image(**image))
        return results

    def title_images(self, imdb_id):
        url = self.build_url('/title/photos', {'tconst': imdb_id})
        result = self.get(url)
        return self.get_images(result)

    def person_images(self, imdb_id):
        url = self.build_url('/name/photos', {'nconst': imdb_id})
        result = self.get(url)
        return self.get_images(result)

    def get(self, url):
        r = requests.get(url, headers={'User-Agent': '''Mozilla/5.0
        (iPhone; U; CPU iPhone OS 4_1 like Mac OS X; en-us)
        AppleWebKit/532.9 (KHTML, like Gecko) Version/4.0.5 Mobile/8B5097d Safari/6531.22.7'''})
        return json.loads(r.content.decode('utf-8'))


class Person(object):
    def __init__(self, **person):
        p = person.get('name')
        # token and label are the persons categorisation
        # e.g token: writers label: Series writing credits
        self.token = person.get('token')
        self.label = person.get('label')

        # attr is a note about this persons work
        # e.g. (1990 - 1992 20 episodes)
        self.attr = person.get('attr')

        # other primary information about their part
        self.name = p.get('name')
        self.imdb_id = p.get('nconst')
        self.role = person.get('char').split('/') if person.get('char') else None
        self.job = person.get('job')

    def __repr__(self):
        return '<Person: {0} ({1})>'.format(self.name.encode('utf-8'), self.imdb_id)


class Title(object):
    def __init__(self, **kwargs):
        self.data = kwargs

        self.imdb_id = self.data.get('tconst')
        self.title = self.data.get('title')
        self.type = self.data.get('type')
        self.year = int(self.data.get('year'))
        self.tagline = self.data.get('tagline')
        self.plot = self.data.get('plot')
        self.runtime = self.data.get('runtime')
        self.rating = self.data.get('rating')
        self.genres = self.data.get('genres')
        self.votes = self.data.get('num_votes')

        self.plot_outline = None
        if 'plot' in self.data and 'outline' in self.data['plot']:
            self.plot_outline = self.data['plot']['outline']

        self.runtime = None
        if 'runtime' in self.data:
            #mins
            self.runtime = str(int((self.data['runtime']['time'] / 60)))

        self.poster_url = None
        if 'image' in self.data and 'url' in self.data['image']:
            self.poster_url = self.data['image']['url']

        self.cover_url = None
        if 'image' in self.data and 'url' in self.data['image']:
            self.cover_url = '{}_SX214_.jpg'.format(self.data['image']['url'].replace('.jpg', ''))

        self.release_date = None
        if 'release_date' in self.data and 'normal' in self.data['release_date']:
            self.release_date = self.data['release_date']['normal']

        self.certification = None
        if 'certificate' in self.data and 'certificate' in self.data['certificate']:
            self.certification = self.data['certificate']['certificate']

        self.trailer_img_url = None
        if ('trailer' in self.data and 'slates' in self.data['trailer'] and
                self.data['trailer']['slates']):
            self.trailer_img_url = self.data['trailer']['slates'][0]['url']

        # Directors summary
        self.directors_summary = []
        if self.data.get('directors_summary'):
            for director in self.data['directors_summary']:
                self.directors_summary.append(Person(**director))

        # Creators
        self.creators = []
        if self.data.get('creators'):
            for creator in self.data['creators']:
                self.creators.append(Person(**creator))

        # Cast summary
        self.cast_summary = []
        if self.data.get('cast_summary'):
            for cast in self.data['cast_summary']:
                self.cast_summary.append(Person(**cast))

        # Writers summary
        self.writers_summary = []
        if self.data.get('writers_summary'):
            for writer in self.data['writers_summary']:
                self.writers_summary.append(Person(**writer))

        # Credits
        self.credits = []
        if self.data.get('credits'):
            for credit in self.data['credits']:
                """
                Possible tokens: directors, cast, writers, producers and others
                """
                for person in credit['list']:
                    person_extra = {'token': credit.get('token'),
                                    'label': credit.get('label'),
                                    'job': person.get('job'),
                                    'attr': person.get('attr')}
                    person = dict(list(person_extra.items()) + list(person.items()))
                    if 'name' in person:
                        # some 'special' credits such as script rewrites have different formatting
                        # check for 'name' is a temporary fix for this, we lose a minimal amount of data from this
                        self.credits.append(Person(**person))

        # Trailers
        self.trailers = {}
        if 'trailer' in self.data and 'encodings' in self.data['trailer']:
            for k, v in list(self.data['trailer']['encodings'].items()):
                self.trailers[v['format']] = v['url']


class Image(object):
    def __init__(self, **image):
        self.caption = image.get('caption')
        self.url = image.get('image').get('url')
        self.width = image.get('image').get('width')
        self.height = image.get('image').get('height')

    def __repr__(self):
        return '<Image: {0}>'.format(self.caption.encode('utf-8'))
########NEW FILE########
__FILENAME__ = all_tests_runner
import unittest


def load_tests(loader, tests, pattern):
    """
    Find and load all tests in dir
    """
    suite = unittest.TestSuite()
    for all_tests in unittest.defaultTestLoader.discover('./', pattern='*_test.py'):
        for test in all_tests:
            suite.addTests(test)
    return suite


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = image_test
from imdbpie import Imdb
import unittest

imdb = Imdb({'anonymize': False})
images = imdb.title_images("tt0468569")


class TestImage(unittest.TestCase):

    def test_results(self):
        self.assertGreaterEqual(len(images), 107)

    def test_caption(self):
        self.assertEqual(images[0].caption, 'Still of Gary Oldman in The Dark Knight')

    def test_url(self):
        self.assertEqual(
            images[0].url,
            'http://ia.media-imdb.com/images/M/MV5BOTAxNzI0ND'
            'E1NF5BMl5BanBnXkFtZTcwNjczMTk2Mw@@._V1_.jpg')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = movie_test
from imdbpie import Imdb
import unittest
import re

imdb = Imdb({'anonymize': False})
movie = imdb.find_movie_by_id("tt0382932")


class TestTitle(unittest.TestCase):

    @staticmethod
    def valid_poster(poster_url):
        match = re.findall(r'http://ia.media-imdb.com/images/.*/', poster_url)[0]
        if match:
            return True
        else:
            return False

    def test_title(self):
        self.assertEqual(movie.title, 'Ratatouille')

    def test_imdb_id(self):
        self.assertEqual(movie.imdb_id, 'tt0382932')

    def test_tagline(self):
        self.assertEqual(movie.tagline, 'Dinner is served... Summer 2007')

    def test_plot(self):
        self.assertIsNotNone(movie.plot)

    def test_runtime(self):
        self.assertIsNotNone(movie.runtime)

    def test_rating(self):
        self.assertTrue(str(movie.rating).isdigit())

    def test_poster_url(self):
        self.assertTrue(self.valid_poster(movie.poster_url))

    def test_release_date(self):
        self.assertIsNotNone(movie.release_date)

    def test_certification(self):
        self.assertIsNotNone(movie.certification)

    def test_trailers(self):
        self.assertIsNotNone(movie.trailers)

    def test_genres(self):
        self.assertIsNotNone(movie.genres)

    def test_directors(self):
        self.assertIsNotNone(movie.directors_summary)

    def test_writers(self):
        self.assertIsNotNone(movie.writers_summary)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = overall_test
from imdbpie import Imdb

imdb = Imdb({'anonymize': False,
             'locale': 'en_US',
             'exclude_episodes': False})


def run_tests():
    """
    Overall tests not using unittests
    for a simple visual results overview
    """
    print((movie.title))
    print(('year', movie.year))
    print(('type', movie.type))
    print(('tagline', movie.tagline))
    print(('rating', movie.rating))
    print(('certification', movie.certification))
    print(('genres', movie.genres))
    print(('plot', movie.plot))
    print(('runtime', movie.runtime))
    print(('writers summary', movie.writers_summary))
    print(('directors summary', movie.directors_summary))
    print(('creators', movie.creators))
    print(('cast summary', movie.cast_summary))
    print(('full credits', movie.credits))

if __name__ == '__main__':
    movie = imdb.find_movie_by_id('tt0705926')
    run_tests()

########NEW FILE########
__FILENAME__ = person_test
from imdbpie import Imdb
import unittest

imdb = Imdb({'anonymize': False})
movie = imdb.find_movie_by_id("tt0382932")


class TestPerson(unittest.TestCase):

    def test_name(self):
        self.assertIsNotNone(movie.credits)

    def test_director(self):
        self.assertEqual(movie.directors_summary[0].name, 'Brad Bird')

    def test_director_role(self):
        self.assertFalse(movie.directors_summary[0].role)

    def test_writers(self):
        self.assertEqual(movie.writers_summary[0].name, 'Brad Bird')

    def test_writers_role(self):
        self.assertFalse(movie.writers_summary[0].role)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = search_test
from imdbpie import Imdb
import unittest

imdb = Imdb({'anonymize': False})


class TestSearch(unittest.TestCase):

    def test_batman(self):
        self.results = imdb.find_by_title("batman")
        self.assertGreater(len(self.results), 15)

    def test_truman(self):
        self.results = imdb.find_by_title("the truman show")
        self.assertGreater(len(self.results), 1)

    def test_bad_search(self):
        self.results = imdb.find_by_title("fdlfj494llsidjg49hkdg")
        self.assertEquals(len(self.results), 0)

    def test_top_250(self):
        self.movies = imdb.top_250()
        self.assertTrue(isinstance(self.movies[0], dict))

    def test_popular_shows(self):
        self.shows = imdb.popular_shows()
        self.assertTrue(isinstance(self.shows[0], dict))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = trailer_test
from imdbpie import Imdb
import unittest

imdb = Imdb({'anonymize': False})
movie = imdb.find_movie_by_id("tt0382932")


class TestTrailer(unittest.TestCase):

    def test_trailer_url(self):
        self.assertIsNotNone(movie.trailers)


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
