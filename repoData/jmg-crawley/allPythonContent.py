__FILENAME__ = config
""" Crawley configuration file """

# Paths

CRAWLEY_ROOT_DIR = "crawley"
GREEN_POOL_MAX_SIZE = 1000

# Requests

REQUEST_TIMEOUT = None    #in seconds
REQUEST_DELAY = 0.5       #in secconds
REQUEST_DEVIATION = 0.25   #in secconds

MOZILLA_USER_AGENT = "Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/10.10 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30"

# Crawlers

MAX_THREAD_POOL_SIZE = 25
MAX_GREEN_POOL_SIZE = 1000

# Scrapers

SIMILARITY_RATIO = 0.45


########NEW FILE########
__FILENAME__ = base
from eventlet import GreenPool
from crawley.multiprogramming.pool import ThreadPool

from crawley import config
from crawley.http.managers import RequestManager
from crawley.http.urls import UrlFinder
from crawley.extractors import XPathExtractor
from crawley.exceptions import AuthenticationError
from crawley.utils import url_matcher

user_crawlers = []

class CrawlerMeta(type):
    """
        This metaclass adds the user's crawlers to a list
        used by the CLI commands.
        Abstract base crawlers won't be added.
    """

    def __init__(cls, name, bases, dct):

        if not hasattr(cls, '__module__' ) or not cls.__module__.startswith(config.CRAWLEY_ROOT_DIR):
            user_crawlers.append(cls)
        super(CrawlerMeta, cls).__init__(name, bases, dct)


Pools = {'greenlets' : {'pool' : GreenPool, 'max_concurrency' : config.MAX_GREEN_POOL_SIZE },
         'threads' : {'pool' : ThreadPool, 'max_concurrency' : config.MAX_THREAD_POOL_SIZE }, }

class BaseCrawler(object):
    """
        User's Crawlers must inherit from this class, may
        override some methods and define the start_urls list,
        the scrapers and the max crawling depth.
    """

    __metaclass__ = CrawlerMeta

    start_urls = []
    """ A list containing the start urls for the crawler """

    allowed_urls = []
    """ A list of urls allowed for crawl """

    black_list = []
    """ A list of blocked urls which never be crawled """

    scrapers = []
    """ A list of scrapers classes """

    max_depth = -1
    """ The maximun crawling recursive level """

    max_concurrency_level = None
    """ The maximun coroutines concurrecy level """

    headers = {}
    """ The default request headers """

    requests_delay = config.REQUEST_DELAY
    """ The average delay time between requests """

    requests_deviation = config.REQUEST_DEVIATION
    """ The requests deviation time """

    extractor = None
    """ The extractor class. Default is XPathExtractor """

    post_urls = []
    """
        The Post data for the urls. A List of tuples containing (url, data_dict)
        Example: ("http://www.mypage.com/post_url", {'page' : '1', 'color' : 'blue'})
    """

    login = None
    """
        The login data. A tuple of (url, login_dict).
        Example: ("http://www.mypage.com/login", {'user' : 'myuser', 'pass', 'mypassword'})
    """

    search_all_urls = True
    """
        If user doesn't define the get_urls method in scrapers then the crawler will search for urls
        in the current page itself depending on the [search_all_urls] attribute.
    """

    search_hidden_urls = False
    """
        Search for hidden urls in the whole html
    """

    def __init__(self, sessions=None, settings=None):
        """
            Initializes the crawler

            params:

                sessions: Database or Documents persistant sessions

                debug: indicates if the crawler logs to stdout debug info
        """

        if sessions is None:
            sessions = []

        self.sessions = sessions
        self.debug = getattr(settings, 'SHOW_DEBUG_INFO', True)
        self.settings = settings

        if self.extractor is None:
            self.extractor = XPathExtractor

        self.extractor = self.extractor()

        pool_type = getattr(settings, 'POOL', 'greenlets')
        pool = Pools[pool_type]

        if self.max_concurrency_level is None:
            self.max_concurrency_level = pool['max_concurrency']

        self.pool = pool['pool'](self.max_concurrency_level)
        self.request_manager = RequestManager(settings=settings, headers=self.headers, delay=self.requests_delay, deviation=self.requests_deviation)

        self._initialize_scrapers()

    def _initialize_scrapers(self):
        """
            Instanciates all the scraper classes
        """

        self.scrapers = [scraper_class(settings=self.settings) for scraper_class in self.scrapers]

    def _make_request(self, url, data=None):
        """
            Returns the response object from a request

            params:
                data: if this param is present it makes a POST.
        """
        return self.request_manager.make_request(url, data, self.extractor)

    def _get_response(self, url, data=None):
        """
            Returns the response data from a request

            params:
                data: if this param is present it makes a POST.
        """

        for pattern, post_data in self.post_urls:
            if url_matcher(url, pattern):
                data = post_data

        return self._make_request(url, data)

    def request(self, url, data=None):

        return self._get_response(url, data=data)

    def _manage_scrapers(self, response):
        """
            Checks if some scraper is suited for data extraction on the current url.
            If so, gets the extractor object and delegate the scraping task
            to the scraper Object
        """
        scraped_urls = []

        for scraper in self.scrapers:

            urls = scraper.try_scrape(response)

            if urls is not None:

                self._commit()
                scraped_urls.extend(urls)

        return scraped_urls

    def _commit(self):
        """
            Makes a Commit in all sessions
        """

        for session in self.sessions:
            session.commit()

    def _search_in_urls_list(self, urls_list, url, default=True):
        """
            Searches an url in a list of urls
        """

        if not urls_list:
            return default

        for pattern in urls_list:
            if url_matcher(url, pattern):
                return True

        return False

    def _validate_url(self, url):
        """
            Validates if the url is in the crawler's [allowed_urls] list and not in [black_list].
        """

        return self._search_in_urls_list(self.allowed_urls, url) and not self._search_in_urls_list(self.black_list, url, default=False)

    def _fetch(self, url, depth_level=0):
        """
            Recursive url fetching.

            Params:
                depth_level: The maximun recursion level
                url: The url to start crawling
        """

        if not self._validate_url(url):
            return

        if self.debug:
            print "-" * 80
            print "crawling -> %s" % url

        try:
            response = self._get_response(url)
        except Exception, ex:
            self.on_request_error(url, ex)
            return

        if self.debug:
            print "-" * 80

        urls = self._manage_scrapers(response)

        if not urls:

            if self.search_all_urls:
                urls = self.get_urls(response)
            else:
                return

        for new_url in urls:

            if depth_level >= self.max_depth and self.max_depth != -1:
                return

            self.pool.spawn_n(self._fetch, new_url, depth_level + 1)

    def _login(self):
        """
            If target pages are hidden behind a login then
            pass through it first.

            self.login can be None or a tuple containing
            (login_url, params_dict)
        """
        if self.login is None:
            return

        url, data = self.login
        if self._get_response(url, data) is None:
            raise AuthenticationError("Can't login")

    def start(self):
        """
            Crawler's run method
        """
        self.on_start()
        self._login()

        for url in self.start_urls:
            self.pool.spawn_n(self._fetch, url, depth_level=0)

        self.pool.waitall()
        self.on_finish()

    def get_urls(self, response):
        """
            Returns a list of urls found in the current html page
        """
        urls = set()

        finder = UrlFinder(response, self.search_hidden_urls)
        return finder.get_urls()

    #Events section

    def on_start(self):
        """
            Override this method to do some work when the crawler starts.
        """

        pass

    def on_finish(self):
        """
            Override this method to do some work when the crawler finishes.
        """

        pass

    def on_request_error(self, url, ex):
        """
            Override this method to customize the request error handler.
        """

        if self.debug:
            print "Request to %s returned error: %s" % (url, ex)

########NEW FILE########
__FILENAME__ = fast
from base import BaseCrawler
from crawley.http.managers import FastRequestManager

class FastCrawler(BaseCrawler):

    def __init__(self, *args, **kwargs):

        BaseCrawler.__init__(self, *args, **kwargs)
        self.request_manager = FastRequestManager()

########NEW FILE########
__FILENAME__ = offline
from base import BaseCrawler
from lxml import etree
from crawley.extractors import XPathExtractor
from crawley.http.urls import UrlFinder
from StringIO import StringIO

class OffLineCrawler(BaseCrawler):

    def __init__(self, *args, **kwargs):

        BaseCrawler.__init__(self, *args, **kwargs)

    def _get_response(self, url, data=None):

        response = BaseCrawler._get_response(self, url, data)

        fixer = HTMLFixer(UrlFinder._url_regex, url, response.raw_html)
        html = fixer.get_fixed_html()

        return html


class HTMLFixer(object):

    def __init__(self, url_regex, url, html):

        self._url_regex = url_regex
        self.url = url
        self.html_tree = XPathExtractor().get_object(html)

    def get_fixed_html(self):

        self._fix_tags("link", "href")
        self._fix_tags("img", "src")

        return etree.tostring(self.html_tree.getroot(), pretty_print=True, method="html")

    def _fix_tags(self, tag, attrib):

        tags = self.html_tree.xpath("//%s" % tag)

        for tag in tags:
            if not self._url_regex.match(tag.attrib[attrib]):
                tag.attrib[attrib] = "%s/%s" % (self.url, tag.attrib[attrib])

########NEW FILE########
__FILENAME__ = exceptions
"""
    Crawley exceptions
"""

class AuthenticationError(Exception):
    """
        Raised when a login error occurs
    """

    def __init__(self, *args, **kwargs):

        Exception.__init__(self, *args, **kwargs)


class TemplateSyntaxError(Exception):
    """
        DSL Template sintax error
    """

    def __init__(self, line=0, *args, **kwargs):

        self.line = line
        Exception.__init__(self, *args, **kwargs)


class ScraperCantParseError(Exception):
    """
        Raised when a scraper can't parse an html page
    """

    def __init__(self, *args, **kwargs):

        Exception.__init__(self, *args, **kwargs)


class InvalidProjectError(Exception):
    """
        Raised when the user opens a invalid directory with the browser
    """

    def __init__(self, *args, **kwargs):

        Exception.__init__(self, *args, **kwargs)

########NEW FILE########
__FILENAME__ = extractors
"""
    Data Extractors classes
"""

from pyquery import PyQuery

from lxml import etree
from StringIO import StringIO


class PyQueryExtractor(object):
    """
        Extractor using PyQuery (A JQuery-like library for Python)
    """

    def get_object(self, data):

        html = PyQuery(data)
        return html


class XPathExtractor(object):
    """
        Extractor using Xpath
    """

    def get_object(self, data):

        parser = etree.HTMLParser()
        html = etree.parse(StringIO(data), parser)
        return html


class RawExtractor(object):
    """
        Returns the raw html data
        Use your favourite python tool to scrape it.
    """

    def get_object(self, data):

        return data

########NEW FILE########
__FILENAME__ = cookies
import os.path
import urllib2
import cookielib
import tempfile

class CookieHandler(urllib2.HTTPCookieProcessor):
    """
        Cookie jar wrapper for save and load cookie from a file
    """

    COOKIES_FILE = "crawley_cookies"

    def _make_temp_file(self):

        tmp = tempfile.gettempdir()
        self.cookie_file = os.path.join(tmp, self.COOKIES_FILE)

    def __init__(self, *args, **kwargs):

        self._make_temp_file()

        self._jar = cookielib.LWPCookieJar(self.cookie_file)
        urllib2.HTTPCookieProcessor.__init__(self, self._jar, *args, **kwargs)

    def load_cookies(self):
        """
            Load cookies from the file
        """

        if os.path.isfile(self.cookie_file):
            self._jar.load()

    def save_cookies(self):
        """
            Save cookies if the jar is not empty
        """

        if self._jar is not None:
            self._jar.save()

########NEW FILE########
__FILENAME__ = managers
import urllib

from eventlet.green import urllib2
from request import DelayedRequest, Request
from crawley.http.cookies import CookieHandler
from crawley.http.response import Response
from crawley.utils import has_valid_attr
from crawley import config


class HostCounterDict(dict):
    """
        A counter dictionary for requested hosts
    """

    def increase(self, key):

        if key in self:
            self[key] += 1
        else:
            self[key] = 1

    def count(self, key):

        if not key in self:
            self[key] = 0

        return self[key]


class RequestManager(object):
    """
        Manages the http requests
    """

    MAX_TRIES = 3

    def __init__(self, settings=None, headers=None, delay=None, deviation=None):

        self.host_counter = HostCounterDict()
        self.cookie_handler = CookieHandler()
        self.headers = headers
        self.delay = delay
        self.deviation = deviation
        self.settings = settings

        self._install_opener()

    def _install_opener(self):

        if has_valid_attr(self.settings,'PROXY_HOST') and has_valid_attr(self.settings,'PROXY_PORT'):

            proxy_info = {        #proxy information
                'user' : getattr(self.settings, 'PROXY_USER', ''),
                'pass' : getattr(self.settings, 'PROXY_PASS', ''),
                'host' : getattr(self.settings, 'PROXY_HOST', ''), #localhost
                'port' : getattr(self.settings, 'PROXY_PORT', 80)
            }

            # build a new opener that uses a proxy requiring authorization
            proxy = urllib2.ProxyHandler({"http" :"http://%(user)s:%(pass)s@%(host)s:%(port)d" % proxy_info})
            self.opener = urllib2.build_opener(proxy, self.cookie_handler)

        else:
            self.opener = urllib2.build_opener(self.cookie_handler)

    def _get_request(self, url):

        host = urllib2.urlparse.urlparse(url).netloc
        count = self.host_counter.count(host)

        return DelayedRequest(url=url, cookie_handler=self.cookie_handler, headers=self.headers, opener=self.opener, delay=self.delay, deviation=self.deviation)

    def make_request(self, url, data=None, extractor=None):
        """
            Acumulates a counter with the requests per host and
            then make a Delayed Request
        """
        request = self._get_request(url)

        if data is not None:
            data = urllib.urlencode(data)

        response = self.get_response(request, data)
        raw_html = self._get_data(response)

        extracted_html = None

        if extractor is not None:
            extracted_html = extractor.get_object(raw_html)

        return Response(raw_html=raw_html, extracted_html=extracted_html, url=url, response=response)

    def get_response(self, request, data):
        """
            Tries [MAX_TRIES] times to get the response and
            return the response data
        """

        response = None
        tries = 0

        while response is None:

            try:
                response = request.get_response(data, delay_factor=tries)
            except Exception, ex:
                if tries >= self.MAX_TRIES:
                    raise ex

            tries += 1

        return response

    def _get_data(self, response):

        return response.read()


class FastRequestManager(RequestManager):

    def _get_request(self, url):

        return Request(url=url, cookie_handler=self.cookie_handler, headers=self.headers, opener=self.opener)

########NEW FILE########
__FILENAME__ = request
import time
import random

from eventlet.green import urllib2
from cookies import CookieHandler

from crawley import config


class Request(object):
    """
        Custom request object
    """

    def __init__(self, url=None, cookie_handler=None, headers=None, opener=None):

        if cookie_handler is None:
           cookie_handler = CookieHandler()

        self.url = url
        self.headers = headers if headers is not None else {}
        self.headers["User-Agent"] = headers.get("User-Agent", config.MOZILLA_USER_AGENT)
        self.headers["Accept-Charset"] = headers.get("Accept-Charset", "ISO-8859-1,utf-8;q=0.7,*;q=0.3")
        self.headers["Accept-Language"] = headers.get("Accept-Language", "es-419,es;q=0.8")

        self.cookie_handler = cookie_handler
        self.cookie_handler.load_cookies()
        self.opener = opener

    def get_response(self, data=None, delay_factor=1):
        """
            Returns the response object from a request.
            Cookies are supported via a CookieHandler object
        """

        """The proxy settings is used as the following dictionary"""

        self._normalize_url()

        request = urllib2.Request(self.url, data, self.headers)

        args = {}
        if config.REQUEST_TIMEOUT is not None:
            args["timeout"] = config.REQUEST_TIMEOUT

        response = self.opener.open(request, **args)
        self.cookie_handler.save_cookies()

        return response

    def _normalize_url(self):
        """
            Normalize the request url
        """

        self.url = urllib2.quote(self.url.encode('utf-8'), safe="%/:=&?~#+!$,;'@()*[]")


class DelayedRequest(Request):
    """
        A delayed custom Request
    """

    def __init__(self, delay=0, deviation=0, **kwargs):

        FACTOR = 1000.0

        deviation = deviation * FACTOR
        randomize = random.randint(-deviation, deviation) / FACTOR

        self.delay = delay + randomize
        Request.__init__(self, **kwargs)

    def get_response(self, data=None, delay_factor=1):
        """
            Waits [delay] miliseconds and then make the request
        """

        delay = self.delay * delay_factor
        time.sleep(delay)
        return Request.get_response(self, data)

########NEW FILE########
__FILENAME__ = response
"""
    HTTP crawley's response object
"""

class Response(object):
    """
        Class that encapsulates an HTTP response
    """

    def __init__(self, raw_html=None, extracted_html=None, url=None, response=None):

        self.raw_html = raw_html
        self.html = extracted_html
        self.url = url

        if response is not None:
            self.headers = response.headers
            self.code = response.getcode()

########NEW FILE########
__FILENAME__ = urls
from re import compile as re_compile
from urllib2 import urlparse

from crawley.extractors import XPathExtractor

class UrlFinder(object):
    """
        This class will find for urls in htmls
    """

    _url_regex = re_compile(r'(http://|https://)([a-zA-Z0-9]+\.[a-zA-Z0-9\-]+|[a-zA-Z0-9\-]+)\.[a-zA-Z\.]{2,6}(/[a-zA-Z0-9\.\?=/#%&\+-]+|/|)')

    def __init__(self, response, search_hidden_urls):

        self.response = response
        self.search_hidden_urls = search_hidden_urls

    def get_urls(self):
        """
            Returns a list of urls found in the current html page
        """

        urls = self.search_regulars()

        if self.search_hidden_urls:

            urls = self.search_hiddens(urls)

        return urls

    def search_regulars(self):
        """
            Search urls inside the <A> tags
        """

        urls = set()

        tree = XPathExtractor().get_object(self.response.raw_html)

        for link_tag in tree.xpath("//a"):

            if not 'href' in link_tag.attrib:
                continue

            url = link_tag.attrib["href"]

            if not urlparse.urlparse(url).netloc:

                url = self._fix_url(url)

            url = self._normalize_url(url)

            urls.add(url)

        return urls

    def _fix_url(self, url):
        """
            Fix relative urls
        """

        parsed_url = urlparse.urlparse(self.response.url)

        if not url.startswith("/"):
             url = "/%s" % url

        url = "%s://%s%s" % (parsed_url.scheme, parsed_url.netloc, url)

        return url

    def _normalize_url(self, url):
        """
            Try to normalize some weird urls
        """

        SLASHES = "//"

        if url.startswith(SLASHES):

            return url.replace(SLASHES, "http://")

        return url

    def search_hiddens(self, urls):
        """
            Search in the entire html via a regex
        """

        for url_match in self._url_regex.finditer(response.raw_html):

            urls.add(url_match.group(0))

        return urls

########NEW FILE########
__FILENAME__ = browser
import sys
from command import BaseCommand
from crawley.utils import exit_with_error

try:
    #install pyqt4
    from PyQt4 import QtGui
    from crawley.web_browser.browser import Browser
except ImportError:
    pass


class BrowserCommand(BaseCommand):
    """
        Runs a browser
    """

    name = "browser"

    def validations(self):

        return [(len(self.args) >= 1, "No given url")]

    def execute(self):

        app = QtGui.QApplication(sys.argv)
        main = Browser(self.args[0])
        main.show()
        sys.exit(app.exec_())


########NEW FILE########
__FILENAME__ = command
import sys
import os
from optparse import OptionParser

from crawley.utils import exit_with_error, import_user_module, check_for_file, fix_file_extension, has_valid_attr, add_to_path
from crawley.manager.projects import project_types


class BaseCommand(object):
    """
        Base Crawley's Command
    """

    name = "BaseCommand"

    def __init__(self, args):

        self.args = args

    def check_validations(self):
        """
            Checks for validations
        """

        for validation, message in self.validations():
            if not validation:
                exit_with_error(message)

    def validations(self):
        """
            Returns a list of tuples containing:
                [(validate_condition, error_message)]
        """

        return []

    def execute(self):
        """
            Executes the command
        """

        raise NotImplementedError()

    def checked_execute(self):
        """
            Checks before Execute
        """

        self.check_validations()
        self.execute()


class ProjectCommand(BaseCommand):
    """
        A command that requires a settings.py file to run
    """

    def __init__(self, args=None, settings=None, **kwargs):

        self.kwargs = kwargs
        self.settings = settings

        BaseCommand.__init__(self, args)

    def checked_execute(self):
        """
            Checks for settings before run
        """
        if self.settings is None:
            self._add_options()
            self.settings = self._check_for_settings()
        else:
            add_to_path(self.settings.PROJECT_ROOT, 1)

        self._check_settings_errors()
        self._check_project_type()
        BaseCommand.checked_execute(self)

    def _add_options(self):
        """
            Add options that can be procesed by OptionParser
        """

        self.parser = OptionParser()
        self.parser.add_option("-s", "--settings", help="Indicates the settings.py file")

    def _check_for_settings(self):
        """
            tries to import the user's settings file
        """

        (options, args) = self.parser.parse_args(self.args)

        if options.settings is not None:

            settings_dir, file_name = os.path.split(options.settings)

            add_to_path(settings_dir)
            settings_file = os.path.splitext(file_name)[0]

        else:
            add_to_path(os.getcwd())
            settings_file = "settings"

        settings = import_user_module(settings_file)

        add_to_path(settings.PROJECT_ROOT, 1)
        return settings

    def _check_settings_errors(self):
        """
            Fix errors in settings.py
        """

        if hasattr(self.settings, 'DATABASE_ENGINE'):
            if self.settings.DATABASE_ENGINE == 'sqlite':
                self.settings.DATABASE_NAME = fix_file_extension(self.settings.DATABASE_NAME, 'sqlite')

        if hasattr(self.settings, 'JSON_DOCUMENT'):
            self.settings.JSON_DOCUMENT = fix_file_extension(self.settings.JSON_DOCUMENT, 'json')

        if hasattr(self.settings, 'XML_DOCUMENT'):
            self.settings.XML_DOCUMENT = fix_file_extension(self.settings.XML_DOCUMENT, 'xml')

    def _check_project_type(self):
        """
            Check for the project's type
        """

        if has_valid_attr(self.settings, "PROJECT_TYPE"):
            project_type = self.settings.PROJECT_TYPE
        else:
            meta_data = import_user_module("__init__")
            project_type = meta_data.project_type

        self.project_type = project_types[project_type]()

########NEW FILE########
__FILENAME__ = migratedb
from command import ProjectCommand
from crawley.utils import import_user_module
from crawley.persistance.relational.connectors import connectors
from syncdb import SyncDbCommand
import elixir

class MigrateDbCommand(ProjectCommand):
    """
        Migrate up the DataBase.

        Reads the models.py user's file and generate a database from it.
    """

    name = "migratedb"

    def execute(self):
        self.syncdb = SyncDbCommand(args=self.args, settings=self.settings, **self.kwargs)

        connector = connectors[self.settings.DATABASE_ENGINE](self.settings)
        elixir.metadata.bind = connector.get_connection_string()
        elixir.metadata.bind.echo = self.settings.SHOW_DEBUG_INFO
        elixir.cleanup_all(True)

        self.syncdb.checked_execute()

########NEW FILE########
__FILENAME__ = run
from command import ProjectCommand
from syncdb import SyncDbCommand


class RunCommand(ProjectCommand):
    """
        Run the user's crawler

        Reads the crawlers.py file to obtain the user's crawler classes
        and then run these crawlers.
    """

    name = "run"

    def execute(self):

        self.syncdb = SyncDbCommand(args=self.args, settings=self.settings, **self.kwargs)
        self.syncdb.checked_execute()

        self.project_type.run(self)

########NEW FILE########
__FILENAME__ = shell
from crawley.crawlers import BaseCrawler
from crawley.extractors import XPathExtractor

from command import BaseCommand
from crawley.utils import exit_with_error


class ShellCommand(BaseCommand):
    """
        Shows an url data in a console like the XPathExtractor see it.
        So users can interactive scrape the data.
    """

    name = "shell"

    def validations(self):

        return [(len(self.args) >= 1, "No given url")]

    def execute(self):

        try:
            import IPython
        except ImportError:
            exit_with_error("Please install the ipython console")

        url = self.args[0]
        crawler = BaseCrawler()

        response = crawler._get_response(url)
        html = XPathExtractor().get_object(response)

        shell = IPython.Shell.IPShellEmbed(argv=[], user_ns={ 'response' : response })
        shell()

########NEW FILE########
__FILENAME__ = startproject
from optparse import OptionParser

from command import BaseCommand
from crawley.manager.projects import project_types, CodeProject


class StartProjectCommand(BaseCommand):
    """
        Starts a new crawley project.

        Copies the files inside conf/project_template in order
        to generate a new project
    """

    name = "startproject"

    def __init__(self, args=None, project_type=None, project_name=None, base_dir=None):

        if args is None:
            args = []

        self.project_type = project_type
        self.base_dir = base_dir

        if project_type is not None:
            args.extend(["--type", project_type])

        if project_name is not None:
            args.append(project_name)

        BaseCommand.__init__(self, args)

    def validations(self):

        return [(len(self.args) >= 1, "No given project name")]

    def execute(self):

        self.parser = OptionParser()
        self.parser.add_option("-t", "--type", help="Type can be 'code' or 'template'")

        (options, args) = self.parser.parse_args(self.args)

        if options.type is None:

            options.type = CodeProject.name
            self.project_name = self.args[0]

        else:
            self.project_name = self.args[2]

        self.project_type = options.type

        project = project_types[self.project_type]()
        project.set_up(self.project_name, base_dir=self.base_dir)

########NEW FILE########
__FILENAME__ = syncdb
from crawley.utils import import_user_module
from command import ProjectCommand

class SyncDbCommand(ProjectCommand):
    """
        Build up the DataBase.

        Reads the models.py user's file and generate a database from it.
    """

    name = "syncdb"

    def execute(self):

        self.project_type.syncdb(self)


########NEW FILE########
__FILENAME__ = base
import os.path
import shutil

import elixir
import crawley

from multiprocessing import Process
from eventlet.green.threading import Thread as GreenThread
from crawley.multiprogramming.threads import KThread
from crawley.multiprogramming.collections import WorkersList

from crawley.utils import generate_template, get_full_template_path, has_valid_attr
from crawley.persistance import Entity, UrlEntity, setup
from crawley.persistance.relational.databases import session as database_session

from crawley.persistance.documents import json_session, JSONDocument
from crawley.persistance.documents import documents_entities, xml_session, XMLDocument
from crawley.persistance.documents import csv_session, CSVDocument

from crawley.persistance.nosql.mongo import mongo_session, MongoEntity
from crawley.persistance.nosql.couch import couch_session, CouchEntity
from crawley.persistance.relational.connectors import connectors
from crawley.manager.utils import import_user_module


worker_type = { 'greenlets' : GreenThread, 'threads' : KThread }

class BaseProject(object):
    """
        Base of all crawley's projects
    """

    def set_up(self, project_name, base_dir=None):
        """
            Setups a crawley project
        """

        main_module = project_name

        if base_dir is not None:
            main_module = os.path.join(base_dir, project_name)

        self._create_module(main_module)
        self._write_meta_data(main_module)

        generate_template("settings", project_name, main_module)

        self.project_dir = os.path.join(main_module, project_name)

        self._create_module(self.project_dir)

    def _write_meta_data(self, directory_module):

        with open(get_full_template_path("metadata")) as f:
            data = f.read()

        data = data % { 'version' : crawley.__version__, 'type' : self.name }

        with open(os.path.join(directory_module, "__init__.py"), "w") as f:
            f.write(data)

    def _create_module(self, name):
        """
            Generates a python module with the given name
        """

        if not os.path.exists(name):

            shutil.os.mkdir(name)
            f = open(os.path.join(name, "__init__.py"), "w")
            f.close()

    def syncdb(self, syncb_command):
        """
            Checks for storages configuration in the settings.py file
        """

        self.connector = None
        syncb_command.sessions = []

        documents_sessions = { 'JSON_DOCUMENT' : json_session,
                               'XML_DOCUMENT' : xml_session,
                               'CSV_DOCUMENT' : csv_session,
                               'MONGO_DB_HOST' : mongo_session,
                               'COUCH_DB_HOST' : couch_session,
                             }

        for storage_name, session in documents_sessions.iteritems():

            if has_valid_attr(syncb_command.settings, storage_name):

                session.set_up(syncb_command.settings, storage_name)
                syncb_command.sessions.append(session)

        if has_valid_attr(syncb_command.settings, "DATABASE_ENGINE"):

            import_user_module("models", exit=False)
            syncb_command.sessions.append(database_session)
            self.connector = connectors[syncb_command.settings.DATABASE_ENGINE](syncb_command.settings)

    def _setup_entities(self, entities, settings):

        elixir.metadata.bind = self.connector.get_connection_string()
        elixir.metadata.bind.echo = settings.SHOW_DEBUG_INFO

        setup(elixir.entities)

    def run(self, run_command, crawlers):

        workers = WorkersList()

        for crawler_class in crawlers:

            crawler = crawler_class(sessions=run_command.syncdb.sessions, settings=run_command.settings)

            pool_type = getattr(run_command.settings, 'POOL', 'greenlets')
            worker_class = worker_type[pool_type]

            worker = worker_class(target=crawler.start)
            workers.append(worker)

        workers.start()
        workers.waitall()

        for session in run_command.syncdb.sessions:
            session.close()

########NEW FILE########
__FILENAME__ = code
import os
import elixir
from multiprocessing import Process

from crawley.persistance import Entity, UrlEntity, setup
from crawley.persistance.relational.connectors import connectors

from crawley.persistance import UrlEntity

from crawley.utils import import_user_module, search_class, generate_template
from crawley.crawlers import user_crawlers

from base import BaseProject


class CodeProject(BaseProject):
    """
        This class represents a code project.
        It can be started with:

            ~$ crawley startproject -t code [name]
    """

    name = "code"

    def set_up(self, project_name, **kwargs):
        """
            Setups a code project.
            Generates the crawlers and models files based on a template.
        """

        BaseProject.set_up(self, project_name, **kwargs)

        generate_template("models", project_name, self.project_dir)
        generate_template("crawlers", project_name, self.project_dir)

    def syncdb(self, syncb_command):
        """
            Builds the database and find the documents storages.
            Foreach storage it adds a session to commit the results.
        """

        BaseProject.syncdb(self, syncb_command)

        if self.connector is not None:
            self._setup_entities(elixir.entities, syncb_command.settings)

    def run(self, run_command):
        """
            Run the crawler of a code project
        """

        import_user_module("crawlers")
        BaseProject.run(self, run_command, user_crawlers)


########NEW FILE########
__FILENAME__ = database
import os.path

from crawley.utils import generate_template
from crawley.simple_parser import Generator
from crawley.simple_parser.compilers import CrawlerCompiler

from template import TemplateProject
from crawley.utils import generate_template, import_user_module
from crawley.simple_parser.config_parser import ConfigApp


class DataBaseProject(TemplateProject):
    """
        This class represents a database project.
        It can be started with:

            ~$ crawley startproject -t database [name]
    """

    name = "database"

    def set_up(self, project_name, base_dir=None):
        """
            Setups a crawley database project
        """

        main_module = project_name

        if base_dir is not None:
            main_module = os.path.join(base_dir, project_name)

        self._create_module(main_module)
        self._write_meta_data(main_module)

    def _get_template(self, syncb_command):

        return syncb_command.kwargs["template"]

    def _get_config(self, run_command):

        return run_command.kwargs["config"]


########NEW FILE########
__FILENAME__ = template
import os.path

from crawley.utils import generate_template
from crawley.simple_parser import Generator
from crawley.simple_parser.compilers import CrawlerCompiler

from base import BaseProject
from crawley.utils import generate_template, import_user_module
from crawley.simple_parser.config_parser import ConfigApp


class TemplateProject(BaseProject):
    """
        This class represents a template project.
        It can be started with:

            ~$ crawley startproject -t template [name]
    """

    name = "template"

    def set_up(self, project_name, **kwargs):
        """
            Setups a crawley's template project
        """

        BaseProject.set_up(self, project_name, **kwargs)

        self._generate_templates(project_name)

    def _generate_templates(self, project_name):

        generate_template("template", project_name, self.project_dir, new_extension=".crw")
        generate_template("config", project_name, self.project_dir, new_extension=".ini")

    def syncdb(self, syncb_command):
        """
            Builds the database
        """

        BaseProject.syncdb(self, syncb_command)

        if self.connector is None:
            return

        template = self._get_template(syncb_command)

        syncb_command.generator = Generator(template, syncb_command.settings)
        entities = syncb_command.generator.gen_entities()

        self._setup_entities(entities, syncb_command.settings)

    def _get_template(self, syncb_command):

        with open(os.path.join(syncb_command.settings.PROJECT_ROOT, "template.crw"), "r") as f:
            return f.read()

    def run(self, run_command):
        """
            Runs the crawley.

            For this kind of project it needs to generate the crawlers and scrapers
            classes at runtime first.
        """

        scraper_classes = run_command.syncdb.generator.gen_scrapers()

        config = self._get_config(run_command)

        compiler = CrawlerCompiler(scraper_classes, config)
        crawler_class = compiler.compile()

        BaseProject.run(self, run_command, [crawler_class])

    def _get_config(self, run_command):

        return ConfigApp(run_command.settings.PROJECT_ROOT)

########NEW FILE########
__FILENAME__ = utils
import sys
import os

PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PATH, "..", "conf", "templates")

class CustomDict(dict):

    def __init__(self, error="[%s] Not valid argument", *args, **kwargs):

        self.error = error
        dict.__init__(self, *args, **kwargs)

    def __getitem__(self, key):

        if key in self:
            return dict.__getitem__(self, key)
        else:
            exit_with_error(self.error % key)


def exit_with_error(error="Non Specified Error"):
    """
        Terminates crawley with an error
    """
    print error
    sys.exit(1)


def import_user_module(module, exit=True):
    """
        Imports a user module
    """

    try:
        return __import__(module, locals(), globals(), [])

    except ImportError:

        if exit:
            exit_with_error("%s.py file not found!" % module)


def search_class(base_klass, entities_list, return_class=False):

    for klass in entities_list:
        if issubclass(klass, base_klass) and not klass is base_klass:
            return klass


def generate_template(tm_name, project_name, output_dir, new_extension=None):
    """
        Generates a project's file from a template
    """

    tm_name, ext = os.path.splitext(tm_name)
    if not ext:
        ext = ".tm"

    if new_extension is None:
        new_extension = '.py'

    with open(os.path.join(TEMPLATES_DIR, "%s%s" % (tm_name, ext)), 'r') as f:
        template = f.read()

    data = template % { 'project_name' : project_name }

    with open(os.path.join(output_dir, "%s%s" % (tm_name, new_extension)), 'w') as f:
        f.write(data)


def get_full_template_path(tm_name, extension=None):
    """
        Returns the full template path
    """

    if extension is None:
        extension = "tm"
    return os.path.join(TEMPLATES_DIR, "%s.%s" % (tm_name, extension))


def check_for_file(settings, file_name):
    """
        Checks if a project file exists
    """

    return os.path.exists(os.path.join(settings.PROJECT_ROOT, file_name))


def fix_file_extension(file_name, extension):
    """
        Fixes the file extensions
    """

    if not file_name.endswith(".%s" % extension):
        file_name = "%s.%s" % (file_name, extension)
    return file_name


def has_valid_attr(settings, attr_name):
    """
        Checks if settings has the attribute [attr_name] and it's not an empty string.
    """

    attr = getattr(settings, attr_name, None)
    return attr is not None and attr


def get_settings_attribute(settings, default=None):

    attr = getattr(settings, attr_name, None)
    return attr is not None and attr

########NEW FILE########
__FILENAME__ = collections
class WorkersList(list):
    """
        A list of workers
    """

    def start(self):

        for worker in self:
            worker.start()

    def waitall(self):

        for worker in self:
            worker.join()

########NEW FILE########
__FILENAME__ = pool
from Queue import Queue
from threads import WorkerThread, KThread

class ThreadPool(object):
    """
        Pool of threads consuming tasks from a queue
    """

    def __init__(self, num_threads):

        if num_threads < 1:
            raise ValueError("ThreadPool must have 1 thread or greenlet at least")

        elif num_threads == 1:
            self.__class__ = SingleThreadedPool
            return

        self.tasks = Queue(num_threads)

        for x in range(num_threads):
            WorkerThread(self.tasks)

    def spawn_n(self, func, *args, **kargs):
        """
            Add a task to the queue and asign a thread to do the work
        """

        self.tasks.put((func, args, kargs))

    def waitall(self):
        """
            Wait for completion of all the tasks in the queue
        """

        self.tasks.join()


class SingleThreadedPool(object):
    """
        One thread "pool" abstraction
    """

    def spawn_n(self, func, *args, **kargs):
        """
            Just executes the function in the same thread
        """

        func(*args, **kargs)

    def waitall(self):
        """
            SingleThreaded pool don't need to wait for anything
        """
        pass

########NEW FILE########
__FILENAME__ = threads
from threading import Thread

class KThread(Thread):

    def __init__(self, *args, **kwargs):

        Thread.__init__(self, *args, **kwargs)
        self.killed = False

    def run(self):

        while not self.killed:
            Thread.run(self)


class WorkerThread(KThread):
    """
        Thread executing tasks from a given tasks queue
    """

    def __init__(self, tasks, *args, **kwargs):

        KThread.__init__(self, *args, **kwargs)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        """
            Runs the thread functionality
        """

        while not self.killed:

            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception, e:
                print e
            self.tasks.task_done()

########NEW FILE########
__FILENAME__ = csv_doc
import csv

from meta import DocumentMeta, BaseDocumentSession

csv_objects = []

class CSVDocument(object):
    """
        CSV Document base class
    """

    __metaclass__ = DocumentMeta

    def __init__(self, **kwargs):

        csv_objects.append(kwargs)


class Session(BaseDocumentSession):
    """
        A class featuring a database session
    """

    file_name = None

    def commit(self):
        """
            Dumps the scraped data to the filesystem
        """

        with open(self.file_name, 'wb') as f:

            writer = csv.writer(f)

            if csv_objects:

                titles = self._encode(csv_objects[0].keys())
                writer.writerow(titles)

                for csv_object in csv_objects:

                    values = self._encode(csv_object.values())
                    writer.writerow(values)

    def _encode(self, list_values):

        return [v.encode('utf-8') for v in list_values if v is not None]

    def close(self):
        pass


csv_session = Session()

########NEW FILE########
__FILENAME__ = json_doc
try:
    import simplejson
except ImportError:
    import json as simplejson

from meta import DocumentMeta, BaseDocumentSession

json_objects = []

class JSONDocument(object):
    """
        JSON Document base class
    """

    __metaclass__ = DocumentMeta

    def __init__(self, **kwargs):

        json_objects.append(kwargs)


class Session(BaseDocumentSession):
    """
        A class featuring a database session
    """

    def commit(self):
        """
            Dumps the scraped data to the filesystem
        """
        with open(self.file_name, 'w') as f:
            simplejson.dump(json_objects, f)

    def close(self):
        pass


json_session = Session()

########NEW FILE########
__FILENAME__ = meta
from crawley.config import CRAWLEY_ROOT_DIR

documents_entities = []

class DocumentMeta(type):
    """
        This metaclass adds the user's documents storages to a list
        used by the CLI commands.
        Abstract base documents storages won't be added.
    """

    def __init__(cls, name, bases, dct):

        if not hasattr(cls, '__module__' ) or not cls.__module__.startswith(CRAWLEY_ROOT_DIR):
            documents_entities.append(cls)
        super(DocumentMeta, cls).__init__(name, bases, dct)


class BaseDocumentSession(object):

    def set_up(self, settings, storage_name):

        self.settings = settings
        self.file_name = getattr(settings, storage_name)

########NEW FILE########
__FILENAME__ = xml
from lxml import etree
from meta import DocumentMeta, BaseDocumentSession

root = etree.Element('root')

class XMLDocument(object):
    """
        XML Document base class
    """

    __metaclass__ = DocumentMeta

    def __init__(self, **kwargs):

        row = etree.Element(self.__class__.__name__)
        root.append(row)

        for key, value in kwargs.iteritems():

            element = etree.Element(key)
            element.text = value
            row.append(element)


class Session(BaseDocumentSession):
    """
        A class featuring a database session
    """

    def commit(self):
        """
            Dumps the scraped data to the filesystem
        """

        with open(self.file_name, "w") as f:
            f.writelines(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8'))

    def close(self):
        pass


xml_session = Session()

########NEW FILE########
__FILENAME__ = base

class NosqlEntity(object):
    """
        Base of NosqlEntities like MongoEntity or CouchEntity

        Collection is a list of nosql objects and it must be overrrided
        in the base classes.
    """
    def __init__(self, **kwargs):

        self.collection.append((self.__class__.__name__, kwargs))


class BaseNosqlSession(object):

    def set_up(self, settings, storage_name):

        self.settings = settings
        self.db_host = getattr(settings, storage_name)

########NEW FILE########
__FILENAME__ = couch
import couchdb
from base import BaseNosqlSession, NosqlEntity

couch_objects = []

class CouchEntity(NosqlEntity):

    collection = couch_objects


class Session(BaseNosqlSession):

    def set_up(self, settings, storage_name):

        BaseNosqlSession.set_up(self, settings, storage_name)
        server = couchdb.Server(self.db_host)

        try:
            self.db = server[settings.COUCH_DB_NAME]
        except:
            self.db = server.create(settings.COUCH_DB_NAME)

    def commit(self):

        for entity, obj in couch_objects:

            if self.settings.SHOW_DEBUG_INFO:
                print obj

            self.db.save(obj)

    def close(self):
        pass


couch_session = Session()



########NEW FILE########
__FILENAME__ = mongo
from pymongo.connection import Connection
from base import BaseNosqlSession, NosqlEntity

mongo_objects = []

class MongoEntity(NosqlEntity):

    collection = mongo_objects


class Session(BaseNosqlSession):

    def set_up(self, settings, storage_name):

        BaseNosqlSession.set_up(self, settings, storage_name)

        self.connection = Connection(self.db_host)
        self.db = getattr(self.connection, self.settings.MONGO_DB_NAME)

    def commit(self):

        for entity, obj in mongo_objects:

            if self.settings.SHOW_DEBUG_INFO:
                print obj

            doc = getattr(self.db, entity)
            doc.save(obj)

    def close(self):
        pass


mongo_session = Session()

########NEW FILE########
__FILENAME__ = connectors
"""
    Database connectors for elixir
"""
import os.path
from crawley.utils import exit_with_error

class Connector(object):
    """
        A Connector represents an object that can provide the
        database connection to the elixir framework.
    """

    def __init__(self, settings):

        self.settings = settings

    def get_connection_string(self):
        """
            Returns the connection string to the corresponding database
        """
        pass


class SimpleConnector(Connector):
    """
        A simple connector for a database without host and user. I.E: sqlite
    """

    def get_connection_string(self):

        return "%s:///%s" % (self.settings.DATABASE_ENGINE, os.path.join(self.settings.PATH, self.settings.DATABASE_NAME))


class HostConnector(Connector):
    """
        A connector for a database that requires host, user and password. I.E: postgres
    """

    def get_connection_string(self):

        user_pass = "%s:%s" % (self.settings.DATABASE_USER, self.settings.DATABASE_PASSWORD)
        host_port = "%s:%s" % (self.settings.DATABASE_HOST, self.settings.DATABASE_PORT)
        return "%s://%s@%s/%s" % (self.settings.DATABASE_ENGINE, user_pass, host_port, self.settings.DATABASE_NAME)



class SqliteConnector(SimpleConnector):
    """
        Sqlite3 Engine connector
    """

    name = "sqlite"


class MySqlConnector(HostConnector):
    """
        Mysql Engine connector
    """

    name = "mysql"


class OracleConnector(HostConnector):
    """
        Oracle Engine connector
    """

    name = "oracle"


class PostgreConnector(HostConnector):
    """
        Postgre Engine connector
    """

    name = "postgres"


class ConnectorsDict(dict):

    def __getitem__(self, key):

        if key in self:
            return dict.__getitem__(self, key)
        else:
            exit_with_error("No recognized database Engine")


connectors = ConnectorsDict()
connectors.update({ PostgreConnector.name : PostgreConnector,
                    OracleConnector.name : OracleConnector,
                    MySqlConnector.name : MySqlConnector,
                    SqliteConnector.name : SqliteConnector})

########NEW FILE########
__FILENAME__ = databases
import elixir
from elixir import Field, Unicode, UnicodeText

session = elixir.session


class Entity(elixir.EntityBase):
    """
        Base Entity.

        Every Crawley's Entity must Inherit from this class
    """

    __metaclass__ = elixir.EntityMeta


class UrlEntity(elixir.EntityBase):
    """
        Entity intended to save urls
    """

    href = Field(Unicode(255))
    parent = Field(Unicode(255))

    __metaclass__ = elixir.EntityMeta


def setup(entities):
    """
        Setup the database based on a list of user's entities
    """

    elixir.setup_entities(entities)
    elixir.create_all()

########NEW FILE########
__FILENAME__ = base
"""
    User's Scrapers Base
"""
from crawley.exceptions import ScraperCantParseError
from crawley.utils import url_matcher

class BaseScraper(object):
    """
       User's Scrappers must Inherit from this class,
       implement the scrape method and define
       the urls that may be procesed by it.
    """

    matching_urls = []

    def __init__(self, settings=None):

        self.settings = settings
        self.debug = getattr(settings, 'SHOW_DEBUG_INFO', True)

    def try_scrape(self, response):
        """
            Tries to parse the html page
        """

        try:
            self._validate(response)
            self.scrape(response)
            return self.get_urls(response)

        except ScraperCantParseError, ex:
            pass

        except Exception, ex:
            self.on_scrape_error(response, ex)

    def _validate(self, response):
        """
            Override this method in order to provide more validations before the data extraction with the given scraper class
        """

        for pattern in self.matching_urls:

            if url_matcher(response.url, pattern):

                if self.debug:
                    print "%s matches the url %s" % (self.__class__.__name__, response.url)
                return

        self.on_cannot_scrape(response)

    #Overridables

    def scrape(self, response):
        """
            Define the data you want to extract here
        """

        pass

    def get_urls(self, response):
        """
            Return a list of urls in the current html
        """

        return []

    #Events section

    def on_scrape_error(self, response, ex):
        """
            Override this method to customize the scrape error handler.
        """

        if self.debug:
            print "%s failed to extract data from %s: %s" % (self.__class__.__name__, response.url, ex)

    def on_cannot_scrape(self, response):
        """
            Override this method to customize the can't scrape handler.
        """

        raise ScraperCantParseError("The Scraper %s can't parse the html from %s" % (self.__class__.__name__, response.url))

########NEW FILE########
__FILENAME__ = smart
import difflib

from HTMLParser import HTMLParser

from base import BaseScraper
from crawley.http.managers import FastRequestManager
from crawley.exceptions import ScraperCantParseError
from crawley.config import SIMILARITY_RATIO


class SmartScraper(BaseScraper):
    """
        This class is used to find similar htmls
    """

    template_url = None
    ratio = SIMILARITY_RATIO

    def __init__(self, *args, **kwargs):

        BaseScraper.__init__(self, *args, **kwargs)

        if self.template_url is None:
            raise ValueError("%s must have a template_url attribute" % self.__class__.__name__)

        self.request_manager = FastRequestManager()
        response = self.request_manager.make_request(self.template_url)
        self.template_html_schema = self._get_html_schema(response.raw_html)

    def _validate(self, response):

        return BaseScraper._validate(self, response) and self._compare_with_template(response)

    def _compare_with_template(self, response):

        if self.debug :
            print "Evaluating similar html structure of %s" % response.url

        html_schema = self._get_html_schema(response.raw_html)

        evaluated_ratio = difflib.SequenceMatcher(None, html_schema, self.template_html_schema).ratio()

        if evaluated_ratio <= self.ratio:
            self.on_cannot_scrape(response)

    def _get_html_schema(self, html):

        html_schema = HtmlSchema()
        html_schema.feed(html)
        return html_schema.get_schema()


class HtmlSchema(HTMLParser):
    """
        This class represents an html page structure, used to compare with another pages
    """

    def __init__(self):
        self.tags = []
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def get_schema(self):
        return "/".join(self.tags)

########NEW FILE########
__FILENAME__ = compilers
from crawley.scrapers import SmartScraper
from crawley.crawlers import BaseCrawler
from crawley.persistance.relational.databases import Entity, Field, Unicode, setup, session, elixir
from crawley.persistance.relational.connectors import connectors

class DSLInterpreter(object):
    """
        This class "compiles" the DSL into scraper classes for
        the crawley framework
    """

    def __init__(self, code_blocks, settings):

        self.code_blocks = code_blocks
        self.settings = settings
        self.entities = {}

    def gen_scrapers(self):
        """
            Returns a runtime generated scraper class
        """

        scrapers = []

        for block in self.code_blocks:

            header = block[0]
            matching_url = "%"
            template_url = header.xpath

            attrs_dict = self._gen_scrape_method(block[1:])
            attrs_dict["matching_urls"] = [matching_url, ]
            attrs_dict["template_url"] = template_url

            scraper = self._gen_class("GeneratedScraper", (SmartScraper, ), attrs_dict)
            scrapers.append(scraper)

        return scrapers

    def _gen_class(self, name, bases, attrs_dict):
        """
            Generates a class at runtime
        """

        return type(name, bases, attrs_dict)

    def gen_entities(self):
        """
            Generates the entities classes
        """

        descriptors = {}
        fields = [line.field for lines in self.code_blocks for line in lines if not line.is_header]

        for field in fields:

            table = field["table"]
            column = field["column"]

            if table not in descriptors:
                descriptors[table] = [column, ]
            else:
                if column not in descriptors[table]:
                    descriptors[table].append(column)

        for entity_name, fields in descriptors.iteritems():

            attrs_dict = dict([(field, Field(Unicode(255))) for field in fields])
            attrs_dict["options_defaults"] = {"shortnames" : True }

            entity = self._gen_class(entity_name, (Entity, ), attrs_dict)
            self.entities[entity_name] = entity

        return self.entities.values()

    def _gen_scrape_method(self, sentences):
        """
            Generates scrapers methods.
            Returns a dictionary containing methods and attributes for the
            scraper class.
        """

        entities = self.entities

        def scrape(self, response):
            """
                Generated scrape method
            """

            fields = {}

            for sentence in sentences:

                nodes = response.html.xpath(sentence.xpath)

                column = sentence.field["column"]
                table = sentence.field["table"]

                if nodes:

                    value = _get_text_recursive(nodes[0])

                    if table not in fields:
                        fields[table] = {column : value}
                    else:
                        fields[table][column] = value

            for table, attrs_dict in fields.iteritems():

                entities[table](**attrs_dict)
                session.commit()


        def _get_text_recursive(node):
            """
                Extract the text from html nodes recursively.
            """
            if node.text is not None and node.text.strip():
                return node.text

            childs = node.getchildren()

            for child in childs:
                return _get_text_recursive(child)

        return { "scrape" : scrape }


class CrawlerCompiler(object):

    def __init__(self, scrapers, config):

        self.scrapers = scrapers
        self.config = config

    def compile(self):

        attrs_dict = {}
        attrs_dict["scrapers"] = self.scrapers
        attrs_dict["start_urls"] = self.config[('crawler','start_urls')].split(',')
        attrs_dict["max_depth"] = int(self.config[('crawler','max_depth')])

        return type("GeneratedCrawler", (BaseCrawler, ), attrs_dict)

########NEW FILE########
__FILENAME__ = config_parser
import os.path
from ConfigParser import ConfigParser

class ConfigObj(object):
    """
        Implements a dictionary object of (section, item)
        with the config.ini file
    """

    def __init__(self):

        self._config_parser = ConfigParser()
        self.config = {}

    def _update_dictionary(self):

        for sect in self._config_parser.sections():
            for item_name, value in self._config_parser.items(sect):
                self.config[(sect, item_name)] = value

    def __getitem__(self, key):

        return self.config.get(key, None)

    def __setitem__(self, key, value):

        if value is None:
            value = ''
        self.config[key] = value
        (section, item) = key
        if not self._config_parser.has_section(section):
            self._config_parser.add_section(section)
        self._config_parser.set(section, item, value)

    def __str__(self):

        return str(self.config)

    def save(self, filename):

        self._config_parser.write(open(filename,'wb'))


class ConfigApp(ConfigObj):
    """
        Open the CONFIG_FILE and update the dictionary
        It can be accesed with a tuple of (section, item). I.E.:

        config = ConfigApp()
        value = config[('section', 'item')]
    """

    CONFIG_FILE = 'config.ini'

    def __init__(self, ini_dir):

        ConfigObj.__init__(self)

        self.ini_dir = ini_dir
        config = open(self._get_path(), 'rb')

        self._config_parser.readfp(config)
        self._update_dictionary()

    def _get_path(self):

        return os.path.join(self.ini_dir, self.CONFIG_FILE)

    def save(self):

        ConfigObj.save(self, self._get_path())

########NEW FILE########
__FILENAME__ = parsers
from crawley.exceptions import TemplateSyntaxError

class DSLAnalizer(object):
    """
        Analizes the DSL written by users
    """

    def __init__(self, dsl):

        self.dsl = dsl

    def is_header(self, line):

        return DSLHeaderLine.SEPARATOR in line

    def parse(self):

        blocks = []
        lines = []

        for n, line in enumerate(self.dsl.split("\n")):

            line = line.strip()

            if not line:
                continue

            if self.is_header(line):

                if lines:
                    blocks.append(lines)

                lines = []
                lines.append(DSLHeaderLine(line, n))

            else:
                lines.append(DSLLine(line, n))

        blocks.append(lines)
        return blocks


class DSLLine(object):
    """
        A DSL line abstraction
    """

    SEPARATOR = "->"
    is_header = False

    def __init__(self, content, number):

        self.number = number
        self.content = content
        self._parse()

    def _parse(self):

        parts = self.content.split(self.SEPARATOR)

        if len(parts) > 2:
            raise TemplateSyntaxError(self.number, "More than one '%s' token found in the same line" % self.SEPARATOR)
        elif len(parts) < 2:
            raise TemplateSyntaxError(self.number, "Missed separator token '%s'" % self.SEPARATOR)

        self.field = self._parse_attribs(parts[0])
        self.xpath = parts[1].strip()

    def _parse_attribs(self, parmas):

        table, column = parmas.split(".")
        return {"table" : table.strip(), "column" : column.strip()}


class DSLHeaderLine(DSLLine):

    SEPARATOR = "=>"
    is_header = True

    def _parse_attribs(self, field):

        return field

########NEW FILE########
__FILENAME__ = sender
def patch_smtp():

    #FIXME: This code have some bug caused by the nonblocking I/O.
    # At this moment this patcher isn't used by the crawler. It just
    # import the regular smtplib module
    from eventlet import patcher
    from eventlet.green import socket
    from eventlet.green import ssl
    from eventlet.green import time

    smtplib = patcher.inject('smtplib',
        globals(),
        ('socket', socket),
        ('ssl', ssl),
        ('time', time))

    del patcher

#The Code begins here
import smtplib

class MailSender(object):
    """
        Smtp server wrapper
    """

    def __init__(self, host, port=25, user=None, password=None, enable_ssl=True):

        self.host = host
        self.port = port
        self.user = user
        self.password = password

        self.server = smtplib.SMTP(host, port)

        if enable_ssl:
            self.start_ssl()

    def start_ssl(self):
        """
            Starts the ssl session over the stmp protocol
        """

        self.server.ehlo()
        self.server.starttls()
        self.server.ehlo()
        self.server.login(self.user, self.password)

    def send(self, to_addresses, body, from_address=None, subject='Crawley Mailer'):
        """
            Sends an email to a list of to_addresses
        """

        if from_address is None and self.user is not None:
            from_address = self.user
        else:
            from_address = self.host

        msg = "\r\n".join(["From: %s" % from_address, "To: %s" % ",".join(to_addresses), "Subject: %s" % subject, "", body])

        self.server.sendmail(from_address, to_addresses, msg)

    def __del__(self):
        """
            Ends the server
        """

        self.server.quit()

########NEW FILE########
__FILENAME__ = toolbox
from crawlers import BaseCrawler

default_crawler = BaseCrawler()

def request(url, data=None):

    return default_crawler.request(url, data=data)
########NEW FILE########
__FILENAME__ = custom_dict
from crawley.utils.common import exit_with_error

class CustomDict(dict):

    def __init__(self, error="[%s] Not valid argument", *args, **kwargs):

        self.error = error
        dict.__init__(self, *args, **kwargs)

    def __getitem__(self, key):

        if key in self:
            return dict.__getitem__(self, key)
        else:
            exit_with_error(self.error % key)

########NEW FILE########
__FILENAME__ = ordered_dict
# Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
# Passes Python2.7's test suite and incorporates all the latest updates.

try:
    from thread import get_ident as _get_ident
except ImportError:
    from dummy_thread import get_ident as _get_ident

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass


class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        return iter(self)

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        for k in self:
            yield self[k]

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) items in od'
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        '''
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)

########NEW FILE########
__FILENAME__ = common
import sys
import os

def exit_with_error(error="Non Specified Error"):
    """
        Terminates crawley with an error
    """
    print error
    sys.exit(1)


def search_class(base_klass, entities_list, return_class=False):

    for klass in entities_list:
        if issubclass(klass, base_klass) and not klass is base_klass:
            return klass


def check_for_file(settings, file_name):
    """
        Checks if a project file exists
    """

    return os.path.exists(os.path.join(settings.PROJECT_ROOT, file_name))


def fix_file_extension(file_name, extension):
    """
        Fixes the file extensions
    """

    if not file_name.endswith(".%s" % extension):
        file_name = "%s.%s" % (file_name, extension)
    return file_name


def has_valid_attr(settings, attr_name):
    """
        Checks if settings has the attribute [attr_name] and it's not an empty string.
    """

    attr = getattr(settings, attr_name, None)
    return attr is not None and attr


def get_settings_attribute(settings, default=None):

    attr = getattr(settings, attr_name, None)
    return attr is not None and attr


def add_to_path(path, index=0):
    """
        Adds the [path] variable to python path
    """
    if not path in sys.path:
        sys.path.insert(index, path)

########NEW FILE########
__FILENAME__ = files
import os

def check_for_file(settings, file_name):
    """
        Checks if a project file exists
    """

    return os.path.exists(os.path.join(settings.PROJECT_ROOT, file_name))


def fix_file_extension(file_name, extension):
    """
        Fixes the file extensions
    """

    if not file_name.endswith(".%s" % extension):
        file_name = "%s.%s" % (file_name, extension)
    return file_name


def has_valid_attr(settings, attr_name):
    """
        Checks if settings has the attribute [attr_name] and it's not an empty string.
    """

    attr = getattr(settings, attr_name, None)
    return attr is not None and attr


def get_settings_attribute(settings, default=None):

    attr = getattr(settings, attr_name, None)
    return attr is not None and attr

########NEW FILE########
__FILENAME__ = matchers
import re

def url_matcher(url, pattern):
    """
        Returns True if the url matches the given pattern
    """

    WILDCARD = "%"

    if pattern.startswith(WILDCARD) and pattern.endswith(WILDCARD):
        return matcher(pattern[1:-1], url, strict=False)
    elif pattern.endswith(WILDCARD):
        return matcher(pattern[:-1], url[:len(pattern)-1])
    elif pattern.startswith(WILDCARD):
        return matcher(pattern[1:], url[-len(pattern)+1:])
    else:
        return matcher(pattern, url)


def matcher(pattern, url, strict=True):
    """
        Checks if the pattern matches the url
    """

    if strict:
        return pattern == url
    return pattern in url


def complex_matcher(pattern, url, strict=True):

    #FIXME
    match = re.search(pattern, url)

    if match is None:

        return url in pattern
    group = match.group(0)

    if strict:
        return group == url

    return group in url

########NEW FILE########
__FILENAME__ = projects
import sys
import os
from common import exit_with_error

PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(PATH, "..", "conf", "templates")


def import_user_module(module, exit=True):
    """
        Imports a user module
    """

    try:
        return __import__(module, locals(), globals(), [])

    except ImportError, e:

        if exit:
            exit_with_error("%s.py file not found!: %s" % (module, e))


def import_from_path(path, name, exit=True):
    """
        Import a module from a specific path
    """

    module = "%s.%s" % (path.replace(os.sep, "."), name)
    return import_user_module(module, exit=exit)


def generate_template(tm_name, project_name, output_dir, new_extension=None):
    """
        Generates a project's file from a template
    """

    tm_name, ext = os.path.splitext(tm_name)
    if not ext:
        ext = ".tm"

    if new_extension is None:
        new_extension = '.py'

    with open(os.path.join(TEMPLATES_DIR, "%s%s" % (tm_name, ext)), 'r') as f:
        template = f.read()

    data = template % { 'project_name' : project_name }

    with open(os.path.join(output_dir, "%s%s" % (tm_name, new_extension)), 'w') as f:
        f.write(data)


def get_full_template_path(tm_name, extension=None):
    """
        Returns the full template path
    """

    if extension is None:
        extension = "tm"
    return os.path.join(TEMPLATES_DIR, "%s.%s" % (tm_name, extension))

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'base.ui'
#
# Created: Mon Oct 10 14:34:16 2011
#      by: PyQt4 UI code generator 4.7.4
#
# WARNING! All changes made in this file will be lost!


########NEW FILE########
__FILENAME__ = baseBrowser
from PyQt4 import QtCore, QtWebKit, QtGui
from GUI import BrowserGUI, BrowserTabGUI, FrmConfigGUI, FrmSettingsGUI

actions = {"Alt+Left" : QtWebKit.QWebPage.Back, "Alt+Right" : QtWebKit.QWebPage.Forward, "F5" : QtWebKit.QWebPage.Reload }

class BaseBrowser(BrowserGUI):
    """
        This class is the base for a simple web browser

        Inherit from this class and override all the virtual methods
        to make a full functional browser
    """

    def __init__(self):

        BrowserGUI.__init__(self)

        self.connect(self.ui.tb_url, QtCore.SIGNAL("returnPressed()"), self.browse)
        self.connect(self.ui.tab_pages, QtCore.SIGNAL("tabCloseRequested(int)"), self.tab_closed)
        self.connect(self.ui.tab_pages, QtCore.SIGNAL("currentChanged(int)"), self.tab_changed)

    # overridable methods section

    def browse():
        pass

    def tab_closed(index):
        pass

    def tab_changed(index):
        pass

    def add_tab():
        pass


class BaseBrowserTab(BrowserTabGUI):
    """
        This class is the base for a browser tab

        Inherit from this class and override all the virtual methods
        to make a browser tab
    """

    def __init__(self, parent):

        BrowserTabGUI.__init__(self, parent)

        self.connect(self.parent.bt_back, QtCore.SIGNAL("clicked()"), self.back)
        self.connect(self.parent.bt_ahead, QtCore.SIGNAL("clicked()"), self.ahead)
        self.connect(self.parent.bt_reload, QtCore.SIGNAL("clicked()"), self.reload)
        self.connect(self.parent.bt_save, QtCore.SIGNAL("clicked()"), self.save)
        self.connect(self.parent.bt_run, QtCore.SIGNAL("clicked()"), self.run)
        self.connect(self.parent.bt_start, QtCore.SIGNAL("clicked()"), self.start)
        self.connect(self.parent.bt_open, QtCore.SIGNAL("clicked()"), self.open)
        self.connect(self.parent.bt_configure, QtCore.SIGNAL("clicked()"), self.configure)
        self.connect(self.parent.bt_settings, QtCore.SIGNAL("clicked()"), self.settings)

        self.connect(self.html, QtCore.SIGNAL("loadStarted()"), self.load_start)
        self.connect(self.html, QtCore.SIGNAL("loadFinished(bool)"), self.loaded_bar)
        self.connect(self.html, QtCore.SIGNAL("loadProgress(int)"), self.load_bar)
        self.connect(self.html, QtCore.SIGNAL("urlChanged(const QUrl)"), self.url_changed)

        self._disable_enable_project_buttons(False)


    # overridable methods section

    def load_start(self):
        pass

    def load_bar(self):
        pass

    def loaded_bar(self):
        pass

    def url_changed(self):
        pass

    def back(self):
        pass

    def ahead(self):
        pass

    def reload():
        pass


class FrmBaseConfig(FrmConfigGUI):

    def __init__(self, parent):

        FrmConfigGUI.__init__(self, parent)
        self.connect(self.config_ui.bt_ok, QtCore.SIGNAL("clicked()"), self.ok)
        self.connect(self.config_ui.bt_cancel, QtCore.SIGNAL("clicked()"), self.cancel)


class FrmBaseSettings(FrmSettingsGUI):

    def __init__(self, parent):

        FrmSettingsGUI.__init__(self, parent)
        self.connect(self.settings_ui.bt_ok, QtCore.SIGNAL("clicked()"), self.ok)
        self.connect(self.settings_ui.bt_cancel, QtCore.SIGNAL("clicked()"), self.cancel)

########NEW FILE########
__FILENAME__ = browser
import multiprocessing

from lxml import etree
from PyQt4 import QtCore, QtWebKit, QtGui
from baseBrowser import BaseBrowser, BaseBrowserTab, FrmBaseConfig, FrmBaseSettings
from config import DEFAULTS, SELECTED_CLASS

from crawley.crawlers.offline import OffLineCrawler
from crawley.manager.utils import get_full_template_path
from crawley.exceptions import InvalidProjectError
from crawley.extractors import XPathExtractor
from crawley.persistance.relational.connectors import connectors
from gui_project import GUIProject


class Browser(BaseBrowser):
    """
        A Browser representation

        This class overrides all the methods of the
        base class.
    """

    def __init__(self, default_url=None):

        if default_url is None:
            default_url = DEFAULTS['url']

        self.default_url = default_url
        BaseBrowser.__init__(self)
        self.add_tab()

    def current_tab(self):
        """
            Return the current tab
        """

        return self.ui.tab_pages.currentWidget()

    def browse(self):
        """
            Make a browse and call the url loader method
        """

        url = self.ui.tb_url.text() if self.ui.tb_url.text() else self.default_url
        if not DEFAULTS['protocol'] in url:
            url = "%s://%s" % (DEFAULTS['protocol'], url)
        tab = self.current_tab()
        self.ui.tb_url.setText(url)
        tab.load_url(url)

    def add_tab(self):
        """
            Add a new tab to the browser
        """

        index = self.ui.tab_pages.addTab(BrowserTab(self.ui), "New Tab")
        self.ui.tab_pages.setCurrentIndex(index)
        self.ui.tb_url.setFocus()
        self.browse()

    def tab_closed(self, index):
        """
            Triggered when the user close a tab
        """

        self.ui.tab_pages.widget(index).deleteLater()
        if self.ui.tab_pages.count() <= 1:
            self.close()

    def tab_changed(self, index):
        """
            Triggered when the current tab changes
        """

        tab = self.current_tab()
        if tab is not None and tab.url is not None:
            self.ui.tb_url.setText(tab.url)

    def show(self):
        """
            Show the main windows
        """

        BaseBrowser.show(self)


class BrowserTab(BaseBrowserTab):
    """
        A Browser Tab representation

        This class overrides all the methods of the
        base class.
    """

    def __init__(self, parent):

        BaseBrowserTab.__init__(self, parent)
        self.url = None
        self.crawler = OffLineCrawler()

    def load_bar(self, value):
        """
            Load the progress bar
        """

        self.pg_load.setValue(value)

    def loaded_bar(self, state):
        """
            Triggered when the bar finish the loading
        """

        self.pg_load.hide()
        index = self.parent.tab_pages.indexOf(self)
        self.parent.tab_pages.setTabText(index, self.html.title())
        self.parent.tab_pages.setTabIcon(index, QtWebKit.QWebSettings.iconForUrl(QtCore.QUrl(self.url)))

    def load_start(self):
        """
            Show the progress bar
        """

        self.pg_load.show()

    def load_url(self, url, selected_nodes=None):
        """
            Load the requested url in the webwiew
        """

        self.url = str(url)
        html = self.crawler._get_response(self.url)

        with open(get_full_template_path("html_template"), "r") as f:
            template = f.read()
            html = template % {'content': html, 'css_class': SELECTED_CLASS }

        if selected_nodes is not None:
            html = self._highlight_nodes(html, selected_nodes)

        self.html.setHtml(html)
        self.html.show()

    def _highlight_nodes(self, html, nodes):
        """
            Highlights the nodes selected by the user in the current page
        """

        html_tree = XPathExtractor().get_object(html)

        for xpath in nodes:

            tags = html_tree.xpath(xpath)

            if tags:

                tag = tags[0]

                classes = tag.attrib.get("class", "")
                classes = "%s %s" % (classes, SELECTED_CLASS)
                tag.attrib["class"] = classes.strip()
                tag.attrib["id"] = xpath

        return etree.tostring(html_tree.getroot(), pretty_print=True, method="html")

    def url_changed(self, url):
        """
            Update the url text box
        """

        if self.is_current():
            self.parent.tb_url.setText(self.url)
        self.url = url.toString()

    def back(self):
        """
            Back to previous page
        """

        if self.is_current():
            self.html.back()

    def ahead(self):
        """
            Go to next page
        """

        if self.is_current():
            self.html.forward()

    def reload(self):
        """
            Reload page
        """

        if self.is_current():
            self.html.reload()

    def start(self):
        """
            Starts a new project
        """

        self._start(is_new=True)

    def open(self):
        """
            Opens an existing project
        """

        self._start()

    def _start(self, is_new=False):
        """
            starts or opens a project depending on
            [is_new] parameter
        """

        if not is_new:
            dir_name = str(QtGui.QFileDialog.getExistingDirectory(self, 'Open Project'))
        else:
            dir_name = str(QtGui.QFileDialog.getSaveFileName(self, 'Start Project'))

        if not dir_name:
            return

        try:
            self.current_project = GUIProject(dir_name)
            self.current_project.set_up(self, is_new)

            self._disable_enable_project_buttons(True)

            if is_new:
                self.configure()

        except InvalidProjectError, e:

            print "%s" % e

            self._disable_enable_project_buttons(False)

    def configure(self):
        """
            Configure a project accesing the config.ini file
        """

        frm_config = FrmConfig(self, self.current_project)
        frm_config.show()

    def settings(self):
        """
            Shows the settings dialog
        """

        frm_settings = FrmSettings(self, self.current_project.settings)
        frm_settings.show()

    def save(self):
        """
            Saves a crawley project
        """

        self.generate()

    def generate(self):
        """
            Generates a DSL template
        """

        if self.is_current():

            url = self.parent.tb_url.text()

            main_frame = self.html.page().mainFrame()
            content = unicode(main_frame.toHtml())
            self.current_project.generate_template(url, content)

    def _run(self):
        """
            Run the crawler in other process
        """
        self.generate()

        self.current_project.run()
        self._disable_enable_buttons(True)

    def run(self):
        """
            Runs the current project
        """

        self._disable_enable_buttons(False, also_run=False)
        self._change_run_handler(self.run, self.stop, "Stop Crawler")

        self.process = multiprocessing.Process(target=self._run)
        self.process.start()

    def _change_run_handler(self, curr_handler, new_handler, label):
        """
            Connects the run signal to another handler
        """

        self.disconnect(self.parent.bt_run, QtCore.SIGNAL("clicked()"), curr_handler)
        self.connect(self.parent.bt_run, QtCore.SIGNAL("clicked()"), new_handler)

        self.parent.bt_run.setText(label)

    def stop(self):
        """
            Kills the running crawler process
        """

        self.process.terminate()
        self._change_run_handler(self.stop, self.run, "Run Crawler")
        self._disable_enable_buttons(True)

    def is_current(self):
        """"
            Return true if this is the current active tab
        """

        return self is self.parent.tab_pages.currentWidget()

    def _disable_enable_buttons(self, enable, also_run=True):
        """
            Disables crawley related buttons
            enable: boolean
        """

        self.parent.bt_configure.setEnabled(enable)
        self.parent.bt_start.setEnabled(enable)
        self.parent.bt_open.setEnabled(enable)
        self.parent.bt_save.setEnabled(enable)
        self.parent.bt_settings.setEnabled(enable)

        if also_run:
            self.parent.bt_run.setEnabled(enable)

    def _disable_enable_project_buttons(self, enable):
        """
            Disables crawley project related buttons
            enable: boolean
        """

        self.parent.bt_configure.setEnabled(enable)
        self.parent.bt_run.setEnabled(enable)
        self.parent.bt_settings.setEnabled(enable)
        self.parent.bt_save.setEnabled(enable)


class FrmConfig(FrmBaseConfig):
    """
        A GUI on the top of the config.ini files of crawley projects.
    """

    INFINITE = "Infinite"
    MAX_DEPTH_OPTIONS = 100

    def __init__(self, parent, current_project):
        """
            Setups the frm config window
        """

        FrmBaseConfig.__init__(self, parent)
        self.current_project = current_project

        self.config = current_project.get_configuration()
        self.config_ui.tb_start_url.setText(self.config[("crawler", "start_urls")])

        items = ["%s" % i for i in range(self.MAX_DEPTH_OPTIONS)]
        items.append(self.INFINITE)

        self.config_ui.cb_max_depth.addItems(items)

        max_depth = int(self.config[("crawler", "max_depth")])
        max_depth = self._check_infinite(max_depth, infinite_value=-1, get_index=True)

        self.config_ui.cb_max_depth.setCurrentIndex(max_depth)

    def _check_infinite(self, max_depth, infinite_value=INFINITE, get_index=False):
        """
            Check if max_depth is infinite or not
        """

        if max_depth == infinite_value:
            if get_index:
                return self.MAX_DEPTH_OPTIONS
            return -1
        return max_depth

    def ok(self):
        """
            Gets the new config file
        """

        max_depth = self.config_ui.cb_max_depth.currentText()
        max_depth = self._check_infinite(max_depth)
        self.config[("crawler", "max_depth")] = max_depth

        start_url = self.config_ui.tb_start_url.text()
        self.config[("crawler", "start_urls")] = start_url

        self.config.save()
        self.close()

    def cancel(self):
        """
            Closes the dialog
        """
        self.close()


class FrmSettings(FrmBaseSettings):
    """
        A GUI on the top of the settings.py files of crawley projects.
    """

    attrs_controls = { 'tb_name' : "DATABASE_NAME",
                       'tb_user' : "DATABASE_USER",
                       'tb_password' : "DATABASE_PASSWORD",
                       'tb_host' : "DATABASE_HOST",
                       'tb_port' : "DATABASE_PORT",
                       'tb_json' : "JSON_DOCUMENT",
                       'tb_xml' : "XML_DOCUMENT",
                       'ck_show_debug' : "SHOW_DEBUG_INFO",
                     }

    def __init__(self, parent, settings):
        """
            Setups the frm settings window
        """

        FrmBaseSettings.__init__(self, parent)
        self.settings = settings

        for control_name, attribute_name in self.attrs_controls.iteritems():

            control = getattr(self.settings_ui, control_name)

            if control_name.startswith("tb_"):
                control.setText(self._check_for_attribute(attribute_name))

            elif control_name.startswith("ck_"):
                control.setChecked(self._check_for_attribute(attribute_name))


        engine = self._check_for_attribute("DATABASE_ENGINE")

        connectors_names = []

        for i, connector in enumerate(connectors.keys()):

            connectors_names.append(connector)

            if connector == engine:
                index = i

        self.settings_ui.cb_engine.addItems(connectors_names)
        self.settings_ui.cb_engine.setCurrentIndex(index)

    def _check_for_attribute(self, attr_name):

        return getattr(self.settings, attr_name, '')

    def ok(self):
        """
            Saves the settings.py file
        """

        settings_dict = {}

        for control_name, attribute_name in self.attrs_controls.iteritems():

            control = getattr(self.settings_ui, control_name)

            if control_name.startswith("tb_"):
                settings_dict[attribute_name] = str(control.text())

            if control_name.startswith("ck_"):
                settings_dict[attribute_name] = control.isChecked()

        settings_dict["DATABASE_ENGINE"] = str(self.settings_ui.cb_engine.currentText())

        self.settings.__dict__.update(settings_dict)
        self._dump_file(settings_dict)
        self.close()

    def _dump_file(self, settings_dict):
        """
            Writes the settings_dict to a settings.py file
        """
        SEPARATOR = " = "

        with open(self.settings.__file__, 'r') as f:

            lines = [line.split(SEPARATOR) for line in f.readlines()]

        new_lines = []

        for line in lines:

            try:
                key, value = [val.strip() for val in line]
                new_value = settings_dict.get(key, None)

                if isinstance(new_value, basestring) and new_value.count("'") != 2 and new_value.count('"') != 2:
                    new_value = "'%s'" % new_value

                if new_value is None:
                    new_value = value

                new_line = "%s%s%s" % (key, SEPARATOR, new_value)
                new_lines.append(new_line)

            except ValueError:
                new_lines.append(line[0])

        stream = ""

        for line in new_lines:
            if not "\n" in line:
                line = "%s \n" % line
            stream += line

        with open(self.settings.__file__, 'w') as f:
            f.write(stream)

    def cancel(self):
        """
            Closes the dialog
        """
        self.close()

########NEW FILE########
__FILENAME__ = config
""" Default configuration file """

DEFAULTS = {'url' : 'http://www.crawley-project.com.ar' , 'protocol' : 'http'}
SELECTED_CLASS = "crawley-framework-selected"

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'base.ui'
#
# Created: Mon Oct 24 23:46:32 2011
#      by: PyQt4 UI code generator 4.7.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1132, 671)
        self.centralwidget = QtGui.QWidget(MainWindow)
        font = QtGui.QFont()
        font.setFamily("Ubuntu")
        font.setWeight(50)
        font.setItalic(False)
        font.setBold(False)
        self.centralwidget.setFont(font)
        self.centralwidget.setAutoFillBackground(True)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.centralwidget)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setMargin(1)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.frame = QtGui.QFrame(self.centralwidget)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.gridLayout = QtGui.QGridLayout(self.frame)
        self.gridLayout.setMargin(0)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.bt_back = QtGui.QPushButton(self.frame)
        self.bt_back.setText("")
        self.bt_back.setObjectName("bt_back")
        self.horizontalLayout_5.addWidget(self.bt_back)
        self.bt_ahead = QtGui.QPushButton(self.frame)
        self.bt_ahead.setText("")
        self.bt_ahead.setObjectName("bt_ahead")
        self.horizontalLayout_5.addWidget(self.bt_ahead)
        self.bt_reload = QtGui.QPushButton(self.frame)
        self.bt_reload.setText("")
        self.bt_reload.setObjectName("bt_reload")
        self.horizontalLayout_5.addWidget(self.bt_reload)
        self.bt_start = QtGui.QPushButton(self.frame)
        self.bt_start.setObjectName("bt_start")
        self.horizontalLayout_5.addWidget(self.bt_start)
        self.bt_open = QtGui.QPushButton(self.frame)
        self.bt_open.setObjectName("bt_open")
        self.horizontalLayout_5.addWidget(self.bt_open)
        self.bt_save = QtGui.QPushButton(self.frame)
        self.bt_save.setObjectName("bt_save")
        self.horizontalLayout_5.addWidget(self.bt_save)
        self.bt_configure = QtGui.QPushButton(self.frame)
        self.bt_configure.setObjectName("bt_configure")
        self.horizontalLayout_5.addWidget(self.bt_configure)
        self.bt_settings = QtGui.QPushButton(self.frame)
        self.bt_settings.setObjectName("bt_settings")
        self.horizontalLayout_5.addWidget(self.bt_settings)
        self.bt_run = QtGui.QPushButton(self.frame)
        self.bt_run.setObjectName("bt_run")
        self.horizontalLayout_5.addWidget(self.bt_run)
        self.tb_url = QtGui.QLineEdit(self.frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tb_url.sizePolicy().hasHeightForWidth())
        self.tb_url.setSizePolicy(sizePolicy)
        self.tb_url.setSizeIncrement(QtCore.QSize(0, 0))
        self.tb_url.setObjectName("tb_url")
        self.horizontalLayout_5.addWidget(self.tb_url)
        self.gridLayout.addLayout(self.horizontalLayout_5, 1, 0, 1, 1)
        self.tab_pages = QtGui.QTabWidget(self.frame)
        self.tab_pages.setTabsClosable(True)
        self.tab_pages.setMovable(True)
        self.tab_pages.setObjectName("tab_pages")
        self.gridLayout.addWidget(self.tab_pages, 5, 0, 1, 1)
        self.horizontalLayout_3.addWidget(self.frame)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.tab_pages.setCurrentIndex(-1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Crawley Browser", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_start.setText(QtGui.QApplication.translate("MainWindow", "Start Project", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_open.setText(QtGui.QApplication.translate("MainWindow", "Open Project", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_save.setText(QtGui.QApplication.translate("MainWindow", "Save", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_configure.setText(QtGui.QApplication.translate("MainWindow", "Configure", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_settings.setText(QtGui.QApplication.translate("MainWindow", "Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_run.setText(QtGui.QApplication.translate("MainWindow", "Run Crawler", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'config.ui'
#
# Created: Sun Oct 23 23:18:00 2011
#      by: PyQt4 UI code generator 4.7.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_FrmConfig(object):
    def setupUi(self, FrmConfig):
        FrmConfig.setObjectName("FrmConfig")
        FrmConfig.resize(400, 131)
        self.bt_ok = QtGui.QPushButton(FrmConfig)
        self.bt_ok.setGeometry(QtCore.QRect(310, 100, 81, 27))
        self.bt_ok.setObjectName("bt_ok")
        self.bt_cancel = QtGui.QPushButton(FrmConfig)
        self.bt_cancel.setGeometry(QtCore.QRect(220, 100, 81, 27))
        self.bt_cancel.setObjectName("bt_cancel")
        self.formLayoutWidget = QtGui.QWidget(FrmConfig)
        self.formLayoutWidget.setGeometry(QtCore.QRect(10, 10, 381, 81))
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.formLayout = QtGui.QFormLayout(self.formLayoutWidget)
        self.formLayout.setObjectName("formLayout")
        self.label = QtGui.QLabel(self.formLayoutWidget)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.tb_start_url = QtGui.QLineEdit(self.formLayoutWidget)
        self.tb_start_url.setObjectName("tb_start_url")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.tb_start_url)
        self.label_2 = QtGui.QLabel(self.formLayoutWidget)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.cb_max_depth = QtGui.QComboBox(self.formLayoutWidget)
        self.cb_max_depth.setObjectName("cb_max_depth")
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.cb_max_depth)

        self.retranslateUi(FrmConfig)
        QtCore.QMetaObject.connectSlotsByName(FrmConfig)

    def retranslateUi(self, FrmConfig):
        FrmConfig.setWindowTitle(QtGui.QApplication.translate("FrmConfig", "Project Configuration ", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_ok.setText(QtGui.QApplication.translate("FrmConfig", "Ok", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_cancel.setText(QtGui.QApplication.translate("FrmConfig", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("FrmConfig", "Start Url", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("FrmConfig", "Max Depth", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'settings.ui'
#
# Created: Mon Oct 24 23:38:01 2011
#      by: PyQt4 UI code generator 4.7.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Settings(object):
    def setupUi(self, Settings):
        Settings.setObjectName("Settings")
        Settings.resize(340, 476)
        self.groupBox = QtGui.QGroupBox(Settings)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 541, 241))
        self.groupBox.setObjectName("groupBox")
        self.formLayoutWidget = QtGui.QWidget(self.groupBox)
        self.formLayoutWidget.setGeometry(QtCore.QRect(0, 30, 311, 202))
        self.formLayoutWidget.setObjectName("formLayoutWidget")
        self.formLayout = QtGui.QFormLayout(self.formLayoutWidget)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setContentsMargins(-1, 0, -1, -1)
        self.formLayout.setObjectName("formLayout")
        self.label = QtGui.QLabel(self.formLayoutWidget)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.cb_engine = QtGui.QComboBox(self.formLayoutWidget)
        self.cb_engine.setObjectName("cb_engine")
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.cb_engine)
        self.label_2 = QtGui.QLabel(self.formLayoutWidget)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.tb_name = QtGui.QLineEdit(self.formLayoutWidget)
        self.tb_name.setObjectName("tb_name")
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.tb_name)
        self.label_3 = QtGui.QLabel(self.formLayoutWidget)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.tb_user = QtGui.QLineEdit(self.formLayoutWidget)
        self.tb_user.setObjectName("tb_user")
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.tb_user)
        self.label_4 = QtGui.QLabel(self.formLayoutWidget)
        self.label_4.setObjectName("label_4")
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_4)
        self.tb_password = QtGui.QLineEdit(self.formLayoutWidget)
        self.tb_password.setObjectName("tb_password")
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.tb_password)
        self.label_5 = QtGui.QLabel(self.formLayoutWidget)
        self.label_5.setObjectName("label_5")
        self.formLayout.setWidget(4, QtGui.QFormLayout.LabelRole, self.label_5)
        self.tb_host = QtGui.QLineEdit(self.formLayoutWidget)
        self.tb_host.setObjectName("tb_host")
        self.formLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.tb_host)
        self.label_6 = QtGui.QLabel(self.formLayoutWidget)
        self.label_6.setObjectName("label_6")
        self.formLayout.setWidget(5, QtGui.QFormLayout.LabelRole, self.label_6)
        self.tb_port = QtGui.QLineEdit(self.formLayoutWidget)
        self.tb_port.setObjectName("tb_port")
        self.formLayout.setWidget(5, QtGui.QFormLayout.FieldRole, self.tb_port)
        self.groupBox_2 = QtGui.QGroupBox(Settings)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 250, 491, 111))
        self.groupBox_2.setObjectName("groupBox_2")
        self.formLayoutWidget_2 = QtGui.QWidget(self.groupBox_2)
        self.formLayoutWidget_2.setGeometry(QtCore.QRect(0, 30, 311, 71))
        self.formLayoutWidget_2.setObjectName("formLayoutWidget_2")
        self.formLayout_2 = QtGui.QFormLayout(self.formLayoutWidget_2)
        self.formLayout_2.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout_2.setObjectName("formLayout_2")
        self.label_8 = QtGui.QLabel(self.formLayoutWidget_2)
        self.label_8.setObjectName("label_8")
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_8)
        self.tb_xml = QtGui.QLineEdit(self.formLayoutWidget_2)
        self.tb_xml.setObjectName("tb_xml")
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.FieldRole, self.tb_xml)
        self.label_9 = QtGui.QLabel(self.formLayoutWidget_2)
        self.label_9.setObjectName("label_9")
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_9)
        self.tb_json = QtGui.QLineEdit(self.formLayoutWidget_2)
        self.tb_json.setObjectName("tb_json")
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.FieldRole, self.tb_json)
        self.groupBox_3 = QtGui.QGroupBox(Settings)
        self.groupBox_3.setGeometry(QtCore.QRect(10, 360, 301, 80))
        self.groupBox_3.setObjectName("groupBox_3")
        self.formLayoutWidget_3 = QtGui.QWidget(self.groupBox_3)
        self.formLayoutWidget_3.setGeometry(QtCore.QRect(0, 30, 301, 41))
        self.formLayoutWidget_3.setObjectName("formLayoutWidget_3")
        self.formLayout_3 = QtGui.QFormLayout(self.formLayoutWidget_3)
        self.formLayout_3.setObjectName("formLayout_3")
        self.ck_show_debug = QtGui.QCheckBox(self.formLayoutWidget_3)
        self.ck_show_debug.setObjectName("ck_show_debug")
        self.formLayout_3.setWidget(0, QtGui.QFormLayout.FieldRole, self.ck_show_debug)
        self.bt_ok = QtGui.QPushButton(Settings)
        self.bt_ok.setGeometry(QtCore.QRect(227, 440, 91, 27))
        self.bt_ok.setObjectName("bt_ok")
        self.bt_cancel = QtGui.QPushButton(Settings)
        self.bt_cancel.setGeometry(QtCore.QRect(130, 440, 91, 27))
        self.bt_cancel.setObjectName("bt_cancel")

        self.retranslateUi(Settings)
        QtCore.QMetaObject.connectSlotsByName(Settings)

    def retranslateUi(self, Settings):
        Settings.setWindowTitle(QtGui.QApplication.translate("Settings", "Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox.setTitle(QtGui.QApplication.translate("Settings", "DataBase Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Settings", "Engine", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Settings", "Name", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Settings", "User", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("Settings", "Password", None, QtGui.QApplication.UnicodeUTF8))
        self.label_5.setText(QtGui.QApplication.translate("Settings", "Host", None, QtGui.QApplication.UnicodeUTF8))
        self.label_6.setText(QtGui.QApplication.translate("Settings", "Port", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox_2.setTitle(QtGui.QApplication.translate("Settings", "Documents Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.label_8.setText(QtGui.QApplication.translate("Settings", "XML Doc.", None, QtGui.QApplication.UnicodeUTF8))
        self.label_9.setText(QtGui.QApplication.translate("Settings", "Json Doc.", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox_3.setTitle(QtGui.QApplication.translate("Settings", "General", None, QtGui.QApplication.UnicodeUTF8))
        self.ck_show_debug.setText(QtGui.QApplication.translate("Settings", "Show Debug Info", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_ok.setText(QtGui.QApplication.translate("Settings", "Ok", None, QtGui.QApplication.UnicodeUTF8))
        self.bt_cancel.setText(QtGui.QApplication.translate("Settings", "Cancel", None, QtGui.QApplication.UnicodeUTF8))


########NEW FILE########
__FILENAME__ = gui_project
import os

from crawley.extractors import PyQueryExtractor

from crawley.manager.commands.startproject import StartProjectCommand
from crawley.manager.commands.run import RunCommand
from crawley.manager.projects.template import TemplateProject
from crawley.exceptions import InvalidProjectError
from crawley.manager.utils import import_user_module
from crawley.simple_parser.config_parser import ConfigApp
from crawley.simple_parser.parsers import DSLAnalizer
from config import SELECTED_CLASS


class GUIProject(object):
    """
        A class that represents a crawley GUI project on the browser.
    """

    HEADER_LINE = "PAGE => %s \r\n"
    SENTENCE_LINE = "%s.%s -> %s \r\n"

    def __init__(self, dir_name):

        self.dir_name, self.project_name = os.path.split(dir_name)

    def set_up(self, browser_tab, is_new=False):
        """
            Starts or opens a crawley's project depending on
            the [is_new] parameter
        """

        os.chdir(self.dir_name)
        os.sys.path[0] = self.project_name

        if is_new:
            cmd = StartProjectCommand(project_type=TemplateProject.name, project_name=self.project_name)
            cmd.execute()

        else:
            self._validate_project()
            self._load_data(browser_tab)

        self.settings = import_user_module("settings")

    def _validate_project(self):
        """
            Checks if the given directory is a valid crawley project
        """

        try:
            with open(os.path.join(self.dir_name, self.project_name, "__init__.py"), "r") as f:
                content = f.read()

            if not 'crawley_version' in content:
                raise IOError
            if not 'template' in content:
                raise InvalidProjectError("The selected directory isn't a correct crawley project type")

        except IOError:
            raise InvalidProjectError("The selected directory isn't a crawley project")

    def _load_data(self, browser_tab):
        """
            Loads the project data into the browser
        """

        with open(os.path.join(self._get_project_path(), "template.crw"), "r") as f:
            template_data = f.read()

        analizer = DSLAnalizer(template_data)
        blocks = analizer.parse()

        for block in blocks:

            header = block[0]
            selected_nodes = [sentence.xpath for sentence in block[1:]]

            browser_tab.parent.tb_url.setText(header.xpath)
            browser_tab.load_url(header.xpath, selected_nodes=selected_nodes)

    def _get_project_path(self):
        """
            Returns the config.ini path
        """

        return os.path.join(self.dir_name, self.project_name, self.project_name)

    def get_configuration(self):
        """
            Returns the content of the config.ini
        """

        return ConfigApp(self._get_project_path())

    def generate_template(self, url, html):
        """
            Generates a template based on what users selects
            on the browser.
        """

        obj = PyQueryExtractor().get_object(html)
        elements = obj(".%s" % SELECTED_CLASS)

        elements_xpath = [e.get("id") for e in elements]

        stream = self.HEADER_LINE % url
        for i, e in enumerate(elements_xpath):
            stream += self.SENTENCE_LINE % ("my_table", "my_field_%s" % i, e)

        with open(os.path.join(os.getcwd(), self.project_name, self.project_name, "template.crw"), "w") as f:
            f.write(stream)

    def run(self):
        """
            Runs the crawler of the generated project
        """

        project_dir = os.path.join(self.dir_name, self.project_name)
        
        os.chdir(project_dir)
        os.sys.path.insert(0, project_dir)

        cmd = RunCommand(settings=self.settings)
        cmd.checked_execute()

########NEW FILE########
__FILENAME__ = run
"""
    ****************** SimpleWebBrowser v1.0 *********************

    A Simple Fully Functional Web Browser implemented over Qt
    and QtWebKit.

    This browser have the basic functions of a clasic web browser
    and it's thought to be easily extended and maintainable.

    It separates the GUI from the logic from the implementation in
    many classes. The inheritance hierarchy looks like this:

        BrowserGUI -> BrowserBase -> Browser
        BrowserTabGUI -> BrowserTabBase -> BrowserTab

        [GUI -> Logic Definition -> Logic Implementation]

    If you have any commentary, query or bug report you can contact
    me to my mail.

    To run this program just type:

        ~$ python run.py

    Inside the main directory.

    author: Juan Manuel Garcia <jmg.utn@gmail.com>
"""

import sys
from PyQt4 import QtGui
from browser import Browser

if __name__ == "__main__":
    """ Run the browser """

    app = QtGui.QApplication(sys.argv)
    main = Browser()
    main.show()
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# crawley documentation build configuration file, created by
# sphinx-quickstart on Wed Sep 14 10:05:07 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
sys.path.append("..")

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.pngmath', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'crawley'
copyright = u'2011, crawley developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
import crawley
version = crawley.__version__
# The full version, including alpha/beta/rc tags.
release = crawley.__version__

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
exclude_patterns = []

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
htmlhelp_basename = 'crawleydoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'crawley.tex', u'crawley Documentation',
   u'crawley developers', 'manual'),
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
    ('index', 'crawley', u'crawley Documentation',
     [u'crawley developers'], 1)
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'crawley'
epub_author = u'crawley developers'
epub_publisher = u'crawley developers'
epub_copyright = u'2011, crawley developers'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = crawlers
from crawley.crawlers import BaseCrawler
from crawley.extractors import XPathExtractor
from models import *
from crawley.scrapers.smart import SmartScraper

class EbayScraper(SmartScraper):

    #specify the urls that can be scraped by this class
    #example: ["%python.org%"] #(where % is a wildcard)
    matching_urls = ["http://www.ebay.com/itm/%"]
    template_url = "http://www.ebay.com/itm/Notebook-Journal-72-pages-hand-made-Lokta-paper-/120814141537?pt=LH_DefaultDomain_0&hash=item1c21158061#ht_2348wt_1398"

    def scrape(self, response):

        #parse the html and populate your model's tables here.
        #example:
        data = response.html.xpath("/html/body/div/table/tr/td/div/table/tr/td[2]/form/table/tr/td/div/b/h1")
        EbayProducts(title=data[0].text)


class EbayCrawler(BaseCrawler):

    #add your starting urls here
    #example: ["http://packages.python.org/crawley/"]
    start_urls = ["http://www.ebay.com/sch/Blank-Diaries-Journals-/45112/i.html?_catref=1&_trksid=p3910.c0.m449"]
    allowed_urls= ["http://www.ebay.com/%"]

    #add your scraper classes here
    #example: [ebayScraper]
    scrapers = [EbayScraper]

    #specify you maximum crawling depth level
    max_depth = 1

    #select your favourite HTML parsing tool
    extractor = XPathExtractor

########NEW FILE########
__FILENAME__ = models
from crawley.persistance import Entity, UrlEntity, Field, Unicode

class EbayProducts(Entity):

    #add your table fields here
    title = Field(Unicode(2000))

########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project directory
PROJECT_NAME = "ebay"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

#Configure you database here. If you don't want to use any leave the fields empty o remove them.
DATABASE_ENGINE = 'sqlite'
DATABASE_NAME = 'ebay'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

#If you want generate a XML o JSON document enter the name of the file here.
XML_DOCUMENT = ''
JSON_DOCUMENT = ''

#Show general debug information
SHOW_DEBUG_INFO = True


########NEW FILE########
__FILENAME__ = crawlers
from crawley.scrapers import BaseScraper
from crawley.extractors import XPathExtractor
from models import *
from crawley.crawlers.base import BaseCrawler

class PackagesAuthorsScraper(BaseScraper):

    #The pages that have the precious data
    matching_urls = ["%pypi.python.org/pypi/%"]

    def scrape(self, response):

        project = response.html.xpath("/html/body/div[5]/div/div/div[3]/h1")[0].text
        author = response.html.xpath("/html/body/div[5]/div/div/div[3]/ul/li/span")[0].text

        PackagesAuthors(project=project, author=author)


class PackagesAuthorsCrawler(BaseCrawler):

    #add your starting urls here
    start_urls = ["http://pypi.python.org/pypi"]

    #add your scraper classes here
    scrapers = [PackagesAuthorsScraper]

    #specify you maximum crawling depth level
    max_depth = 1

    #select your favourite HTML parsing tool
    extractor = XPathExtractor

########NEW FILE########
__FILENAME__ = models
from crawley.persistance import Entity, UrlEntity, Field, Unicode

class PackagesUrls(UrlEntity):

    #this entity is intended for save urls
    pass

class PackagesAuthors(Entity):

    #add your table fields here
    project = Field(Unicode(255))
    author = Field(Unicode(255))


########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "pypi_crawler"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = 'sqlite'
DATABASE_NAME = 'pypi_crawler'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

SHOW_DEBUG_INFO = True

POOL = 'greenlets'

########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "pypi_crawler_dsl"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = 'sqlite'
DATABASE_NAME = 'pypi_crawler_dsl'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

SHOW_DEBUG_INFO = True

########NEW FILE########
__FILENAME__ = crawlers
from crawley.crawlers import BaseCrawler
from crawley.scrapers.smart import SmartScraper
from crawley.extractors import XPathExtractor
from models import *

class PackagesAuthorsScraper(SmartScraper):

    #The pages that have the precious data
    matching_urls = ["%pypi.python.org/pypi/%"]

    #an example of a page that you want to scrap
    template_url = "http://pypi.python.org/pypi/Shake/0.5.10"

    def scrape(self, response):

        project = response.html.xpath("/html/body/div[5]/div/div/div[3]/h1")[0].text
        author = response.html.xpath("/html/body/div[5]/div/div/div[3]/ul/li/span")[0].text

        PackagesAuthors(project=project, author=author)


class PackagesAuthorsCrawler(BaseCrawler):

    #add your starting urls here
    start_urls = ["http://pypi.python.org/pypi"]

    #add your scraper classes here
    scrapers = [PackagesAuthorsScraper]

    #specify you maximum crawling depth level
    max_depth = 1

    #select your favourite HTML parsing tool
    extractor = XPathExtractor

########NEW FILE########
__FILENAME__ = models
from crawley.persistance import Entity, UrlEntity, Field, Unicode

class PackagesUrls(UrlEntity):

    #this entity is intended for save urls
    pass

class PackagesAuthors(Entity):

    #add your table fields here
    project = Field(Unicode(255))
    author = Field(Unicode(255))


########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "pypi_crawler"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = 'sqlite'
DATABASE_NAME = 'pypi_crawler'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

SHOW_DEBUG_INFO = True

########NEW FILE########
__FILENAME__ = crawlers
from crawley.crawlers import BaseCrawler
from crawley.scrapers import BaseScraper
from crawley.extractors import XPathExtractor
from models import *

class pypiScraper(BaseScraper):

    #specify the urls that can be scraped by this class
    matching_urls = ["%"]

    def scrape(self, response):

        #getting the html table
        table = response.html.xpath("/html/body/div[5]/div/div/div[3]/table")[0]

        #for rows 1 to n-1
        for tr in table[1:-1]:

            #obtaining the searched html inside the rows
            td_updated = tr[0]
            td_package = tr[1]
            package_link = td_package[0]
            td_description = tr[2]

            data = {"updated" : td_updated.text, "package" : package_link.text, "description" : td_description.text }

            #storing data in the xml document
            XMLPackage(**data)
            #storing data in the json document
            JSONPackage(**data)
            #storing data in the csv document
            CSVPackage(**data)


class pypiCrawler(BaseCrawler):

    #add your starting urls here
    start_urls = ["http://pypi.python.org/pypi"]

    #add your scraper classes here
    scrapers = [pypiScraper]

    #specify you maximum crawling depth level
    max_depth = 0

    #select your favourite HTML parsing tool
    extractor = XPathExtractor

########NEW FILE########
__FILENAME__ = models
from crawley.persistance.documents import XMLDocument, JSONDocument, CSVDocument

class XMLPackage(XMLDocument):
    """
        Class wich represents a xml document
    """
    pass


class JSONPackage(JSONDocument):
    """
        Class wich represents a json document
    """
    pass

class CSVPackage(CSVDocument):
    """
        Class wich represents a csv document
    """
    pass


########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "documents_storage"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = ''
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

XML_DOCUMENT = 'data.xml'
JSON_DOCUMENT = 'data.json'
CSV_DOCUMENT = 'data.csv'

SHOW_DEBUG_INFO = True

########NEW FILE########
__FILENAME__ = get_all
from pymongo.connection import Connection
import couchdb

connection = Connection("localhost")

db = connection.mongo_db_name

print "-" * 80
print "Mongo Entities"
print "-" * 80
print ""

for obj in db.Package.find():
    print obj

print "-" * 80
print ""
print "Total entities: %s" % db.Package.count()


print "-" * 80
print "CouchDb Entities"
print "-" * 80
print ""

couch = couchdb.Server("http://localhost:5984")
couch_db = "couch_db_name"

try:
    db = couch[couch_db]
except:
    db = couch.create(couch_db)

for entity in db:
    print db.get(entity)

print "-" * 80
print ""

print "Total entities: %s" % len(db)

########NEW FILE########
__FILENAME__ = crawlers
from crawley.crawlers import BaseCrawler
from crawley.scrapers import BaseScraper
from crawley.extractors import XPathExtractor
from models import *

class pypiScraper(BaseScraper):

    #specify the urls that can be scraped by this class
    matching_urls = ["%"]

    def scrape(self, response):

        #getting the html table
        table = response.html.xpath("/html/body/div[5]/div/div/div[3]/table")[0]

        #for rows 1 to n-1
        for tr in table[1:-1]:

            #obtaining the searched html inside the rows
            td_updated = tr[0]
            td_package = tr[1]
            package_link = td_package[0]
            td_description = tr[2]

            #storing data in Packages table

            data =  {'updated' : td_updated.text, 'package' : package_link.text, 'description' : td_description.text }

            PackageMongo(**data)
            PackageCouch(**data)


class pypiCrawler(BaseCrawler):

    #add your starting urls here
    start_urls = ["http://pypi.python.org/pypi"]

    #add your scraper classes here
    scrapers = [pypiScraper]

    #specify you maximum crawling depth level
    max_depth = 0

    #select your favourite HTML parsing tool
    extractor = XPathExtractor

########NEW FILE########
__FILENAME__ = models
from crawley.persistance import MongoEntity, CouchEntity, Field, Unicode

class PackageMongo(MongoEntity):

    pass


class PackageCouch(CouchEntity):

    pass

########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project directory
PROJECT_NAME = "pypi"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

#Configure you database here. If you don't want to use any leave the fields empty o remove them.
DATABASE_ENGINE = ''
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

#If you want generate a XML o JSON document enter the name of the file here.
XML_DOCUMENT = ''
JSON_DOCUMENT = ''

MONGO_DB_HOST = 'localhost'
MONGO_DB_NAME = 'mongo_db_name'

COUCH_DB_HOST = 'http://localhost:5984'
COUCH_DB_NAME = 'couch_db_name'

#Show general debug information
SHOW_DEBUG_INFO = True


########NEW FILE########
__FILENAME__ = crawlers
from crawley.crawlers import BaseCrawler
from crawley.scrapers import BaseScraper
from crawley.extractors import XPathExtractor
from models import *

class pypiScraper(BaseScraper):

    #specify the urls that can be scraped by this class
    matching_urls = ["%"]

    def scrape(self, response):

        #getting the html table
        table = response.html.xpath("/html/body/div[5]/div/div/div[3]/table")[0]

        #for rows 1 to n-1
        for tr in table[1:-1]:

            #obtaining the searched html inside the rows
            td_updated = tr[0]
            td_package = tr[1]
            package_link = td_package[0]
            td_description = tr[2]

            #storing data in Packages table
            Package(updated=td_updated.text, package=package_link.text, description=td_description.text)


class pypiCrawler(BaseCrawler):

    #add your starting urls here
    start_urls = ["http://pypi.python.org/pypi"]

    #add your scraper classes here
    scrapers = [pypiScraper]

    #specify you maximum crawling depth level
    max_depth = 0

    #select your favourite HTML parsing tool
    extractor = XPathExtractor

########NEW FILE########
__FILENAME__ = models
from crawley.persistance import Entity, Field, Unicode

class Package(Entity):

    #add your table fields here
    updated = Field(Unicode(255))
    package = Field(Unicode(255))
    description = Field(Unicode(255))

########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "pypi"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = 'sqlite'
DATABASE_NAME = 'pypi'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

SHOW_DEBUG_INFO = True



########NEW FILE########
__FILENAME__ = config
""" Crawlers configuration file """

start_urls = ["http://pypi.python.org/pypi/crawley"]

max_depth = 0

########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "pypi_packages_template"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = 'sqlite'
DATABASE_NAME = 'pypi_packages_template'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

SHOW_DEBUG_INFO = True

########NEW FILE########
__FILENAME__ = run_tests
"""
    Tests runner
"""

import unittest
import sys
from optparse import OptionParser

from tests.crawler_test import CrawlerTest
from tests.utils_test import UtilsTest
from tests.commands_test import CommandsTest
from tests.simple_parser_test import ParserTest
from tests.persistance_test import PersistanceTest
from tests.http_test import HTTPTest


def load_tests(tests):

    suite = unittest.TestSuite()
    for test_class in tests:
        tests = unittest.defaultTestLoader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    return suite

def suite(options):
    unit = [UtilsTest, ParserTest, PersistanceTest, HTTPTest]
    integration = [CommandsTest, CrawlerTest]

    if options.all is not None:
        return load_tests(unit + integration)
    elif options.unittests is not None:
        return load_tests(unit)
    elif options.integration is not None:
        return load_tests(integration)
    else:
        return None

if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("-i", "--integration", help="run integration tests", nargs=0)
    parser.add_option("-u", "--unittests", help="run unit tests", nargs=0)
    parser.add_option("-a", "--all", help="run all tests", nargs=0)
    (options, args) = parser.parse_args()
    test_suite = suite(options)
    if len(sys.argv) <= 1 or len(sys.argv) >= 3 or test_suite is None:
        print parser.print_help()
    else:
        unittest.TextTestRunner(verbosity=2).run(test_suite)


########NEW FILE########
__FILENAME__ = commands_test
import unittest
from crawley.manager.commands.run import RunCommand
from crawley.manager.commands.syncdb import SyncDbCommand
from crawley.manager.commands.startproject import StartProjectCommand
from crawley.manager.commands.shell import ShellCommand
import os
import shutil

class CommandsTest(unittest.TestCase):

    def setUp(self):

        self.settings_dir = os.path.join(os.getcwd(), "tests", "test_project")
        self.settings_args = ["-s", os.path.join(self.settings_dir, "settings.py")]

        self.test_name_args = ["test"]

    def test_startproject(self):

        cmd = StartProjectCommand(self.test_name_args)
        cmd.checked_execute()
        self.assertTrue(os.path.exists("test"))
        self.assertTrue(os.path.exists(os.path.join("test", "settings.py")))
        self.assertTrue(os.path.exists(os.path.join("test", "test", "models.py")))
        self.assertTrue(os.path.exists(os.path.join("test", "test", "crawlers.py")))
        shutil.rmtree("test")

    def test_syncbd(self):

        cmd = SyncDbCommand(self.settings_args)
        cmd.checked_execute()
        self.assertTrue(os.path.exists(os.path.join(self.settings_dir, "test_project.sqlite")))
        os.remove(os.path.join(self.settings_dir, "test_project.sqlite"))

    def test_run(self):

        cmd = RunCommand(self.settings_args)
        cmd.checked_execute()

    def _test_shell(self):
        """
            Skiped because it blocks the console
        """

        cmd = ShellCommand(self.test_name_args)
        cmd.checked_execute()

    #database project tests

    def test_params_run(self):

        cmd = RunCommand(template="sarasa", config="config_file")
        self.assertTrue("template" in cmd.kwargs)
        self.assertTrue(cmd.kwargs["template"] == "sarasa")
        self.assertTrue("config" in cmd.kwargs)
        self.assertTrue(cmd.kwargs["config"] == "config_file")
########NEW FILE########
__FILENAME__ = crawler_test
import unittest
from crawley.crawlers import BaseCrawler

import urllib


class PostCrawler(BaseCrawler):

    start_urls = ["https://github.com/jmg"]
    post_urls = [("https://github.com/jmg", {'user' : 'jm'})]
    max_depth = 0


class CrawlerTest(unittest.TestCase):

    def setUp(self):
        self.crawler = BaseCrawler()

    def _test_requests(self):
        """
            Very basic and foolish test
        """
        response = self.crawler._get_response("https://github.com/jmg")
        self.assertTrue(response)

    def test_cookies(self):
        """
            This test asserts if the login was successful and the second request retrieves
            a facebook's page that requires to be logged in.
        """
        data = {'email' : 'user', 'pass': 'pass'}

        response = self.crawler._get_response("https://www.facebook.com/login.php?login_attempt=1", data)
        response = self.crawler._get_response("http://www.facebook.com/profile.php?id=1271577281")
        with open("url.html", 'w') as f:
            f.write(response.raw_html)

    def _test_post(self):

        crawler = PostCrawler()
        crawler.start()

########NEW FILE########
__FILENAME__ = config
""" Crawlers configuration file """

start_urls = ["http://www.python.org/"]

max_depth = 0

########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "dsl_project"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = 'sqlite'
DATABASE_NAME = 'dsl_project'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

SHOW_DEBUG_INFO = True

########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "documents_storage"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = 'sqlite'
DATABASE_NAME = 'base.sqlite'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

SHOW_DEBUG_INFO = True

########NEW FILE########
__FILENAME__ = http_test
import unittest
import os
from crawley.http.cookies import CookieHandler


class HTTPTest(unittest.TestCase):

    def test_cookies(self):
        """
            Test cookies dir
        """

        handler = CookieHandler()
        self.assertTrue(isinstance(handler.cookie_file, basestring))


########NEW FILE########
__FILENAME__ = persistance_test
import unittest
import os
from crawley.persistance.documents import XMLDocument, JSONDocument, CSVDocument, json_session, xml_session, csv_session

class TestXMLDoc(XMLDocument):
    pass

class TestJSONDoc(JSONDocument):
    pass

class TestCSVDoc(CSVDocument):
    pass

class PersistanceTest(unittest.TestCase):

    def setUp(self):

        pass

    def test_XMLDocument(self):

        doc = TestXMLDoc(attribute="test_value")
        doc = TestXMLDoc(attribute="test_value2")
        xml_session.file_name = "data.xml"
        xml_session.commit()

        self.assertTrue(os.path.exists("data.xml"))
        os.remove("data.xml")

    def test_JSONDocument(self):

        doc = TestJSONDoc(attribute="test_value")
        doc = TestJSONDoc(attribute="test_value2")
        json_session.file_name = "data.json"
        json_session.commit()

        self.assertTrue(os.path.exists("data.json"))
        os.remove("data.json")

    def test_CVSDocument(self):

        doc = TestCSVDoc(attribute="test_value")
        doc = TestCSVDoc(attribute="test_value2")
        csv_session.file_name = "data.csv"
        csv_session.commit()

        self.assertTrue(os.path.exists("data.csv"))
        os.remove("data.csv")

########NEW FILE########
__FILENAME__ = simple_parser_test
import unittest
from crawley.crawlers import BaseCrawler
from crawley.simple_parser import Generator
from crawley.exceptions import TemplateSyntaxError
from crawley.extractors import XPathExtractor
from crawley.http.response import Response
from dsl_tests import settings

class ParserTest(unittest.TestCase):

    def setUp(self):

        pass

    def test_interprete(self):

        test_dsl = """PAGE => http://www.python.org/
                      table1.model1 -> /html/body/div[5]/div/div/h1
                      table1.model2 -> /html/body/div
                      table2.model1 -> /html/body/div/span"""

        fail_dsl = """my_model -> /html/body -> other_stuff"""
        self.assertRaises(TemplateSyntaxError, Generator, fail_dsl, settings)

        fail_dsl = """my_model = /html/body"""
        self.assertRaises(TemplateSyntaxError, Generator, fail_dsl, settings)

    def test_generated_scrapers(self):

        test_dsl = """PAGE => http://www.python.org/
                      table3.model1 -> /html/body/div[5]/div/div/h1
                      table3.model2 -> /html/body/div
                      table4.model1 -> /html/body/div/span"""

        generator = Generator(test_dsl, settings)
        generator.gen_entities()

        scrapers_classes = generator.gen_scrapers()

        crawler = BaseCrawler()
        response = crawler._get_response("http://www.python.org/")

        for scraper_class in scrapers_classes:
            scraper_class().scrape(response)

########NEW FILE########
__FILENAME__ = settings
import os
PATH = os.path.dirname(os.path.abspath(__file__))

#Don't change this if you don't have renamed the project
PROJECT_NAME = "test_project"
PROJECT_ROOT = os.path.join(PATH, PROJECT_NAME)

DATABASE_ENGINE = 'sqlite'     #TODO: test elixir with several DB engines
DATABASE_NAME = 'test_project'
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''
DATABASE_PORT = ''

SHOW_DEBUG_INFO = True

########NEW FILE########
__FILENAME__ = crawlers
from crawley.crawlers import BaseCrawler
from crawley.scrapers.smart import SmartScraper
from crawley.extractors import XPathExtractor
from models import *

class PackagesAuthorsScraper(SmartScraper):

    #The pages that have the precious data
    matching_urls = ["%pypi.python.org/pypi/%"]

    #an example of a page that you want to scrap
    template_url = "http://pypi.python.org/pypi/crawley/0.2.4"

    def scrape(self, response):

        project = response.html.xpath("/html/body/div[5]/div/div/div[3]/h1")[0].text
        author = response.html.xpath("/html/body/div[5]/div/div/div[3]/ul/li/span")[0].text

        PackagesAuthors(project=project, author=author)


class PackagesAuthorsCrawler(BaseCrawler):

    #add your starting urls here
    start_urls = ["http://pypi.python.org/pypi"]

    #add your scraper classes here
    scrapers = [PackagesAuthorsScraper]

    #specify you maximum crawling depth level
    max_depth = 1

    #select your favourite HTML parsing tool
    extractor = XPathExtractor

########NEW FILE########
__FILENAME__ = models
from crawley.persistance import Entity, UrlEntity, Field, Unicode

class PackagesUrls(UrlEntity):

    #this entity is intended for save urls
    pass

class PackagesAuthors(Entity):

    #add your table fields here
    project = Field(Unicode(255))
    author = Field(Unicode(255))


########NEW FILE########
__FILENAME__ = utils_test
import unittest

from crawley.utils import matcher, url_matcher, OrderedDict

class UtilsTest(unittest.TestCase):

	def test_url_matcher(self):

		self.assertTrue(url_matcher("http://www.google.com.ar", "%www.google.com%"))
		self.assertTrue(url_matcher("http://www.google.com.ar", "http://www.google.com%"))
		self.assertTrue(url_matcher("http://www.google.com.ar", "%www.google.com.ar"))
		self.assertTrue(url_matcher("http://www.google.com.ar", "http://www.google.com.ar"))

		self.assertFalse(url_matcher("http://www.google.com.ar", "%www.google.com"))
		self.assertFalse(url_matcher("http://www.google.com.ar", "www.google.com%"))
		self.assertFalse(url_matcher("http://www.google.com.ar", "%www.goo.com%"))
		self.assertFalse(url_matcher("http://www.google.com.ar", "http://www.goo.com.ar"))

	def test_strict_matcher(self):

		self.assertTrue(matcher("http://www.a.com", "http://www.a.com"))
		self.assertTrue(matcher("www.a.com", "http://www.a.com", False))

		self.assertFalse(matcher("patron_fruta", "http://www.a.com"))
		self.assertFalse(matcher("patron_fruta", "http://www.a.com"))

	def test_ordered_dict(self):

		od = OrderedDict()
		od['a'] = 1
		od['b'] = 2

		i = 1
		for k,v in od.iteritems():
			if i == 1:
				self.assertEquals('a', k)
				self.assertEquals(1, v)
			elif i == 2:
				self.assertEquals('b', k)
				self.assertEquals(2, v)

			i += 1

	def _test_url_matcher_with_regex(self):

		self.assertTrue(url_matcher("http://www.google.com.ar", "http://([a-z.]+)"))
		self.assertTrue(url_matcher("http://www.google.com.ar", "http://(([a-z]+.){4})"))
		self.assertTrue(url_matcher("http://www.google.com.ar", "[a-z/:.]+"))

		self.assertFalse(url_matcher("http://www.google.com.ar", "http://([a-z]+)"))
		self.assertFalse(url_matcher("http://www.google.com.ar", "http://(([a-z]+.){1})"))
		self.assertFalse(url_matcher("http://www.google.com.ar", "[a-z:.]+"))

########NEW FILE########
