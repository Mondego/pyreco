__FILENAME__ = patu
#!/usr/bin/env python

import httplib2
import sys
from lxml.html import fromstring
from optparse import OptionParser
from multiprocessing import Process, Queue
from urlparse import urlsplit, urljoin, urlunsplit


class Spinner(object):
    def __init__(self):
        self.status = 0
        self.locations = ['|', '/', '-', '\\']

    def spin(self):
        sys.stderr.write("%s\r" % self.locations[self.status])
        sys.stderr.flush()
        self.status = (self.status + 1) % 4

class Response(object):
    def __init__(self, url, status_code=-1, content=None, links=[]):
        self.url = url
        self.status_code = status_code
        self.content = content
        self.links = links

class Patu(object):

    def __init__(self, urls=[], spiders=1, spinner=True, verbose=False, depth=-1, input_file=None, generate=False):
        # Set up the multiprocessing bits
        self.processes = []
        self.task_queue = Queue()
        self.done_queue = Queue()
        self.next_urls = {}
        self.queued_urls = {}
        self.seen_urls = set()
        self.spinner = Spinner()

        # Generate the initial URLs, either from command-line, stdin, or file
        if input_file:
            if input_file == '-':
                f = sys.stdin
            else:
                f = open(input_file)
            for line in f:
                bits = line.strip().split("\t")
                if bits == ['']:
                    continue
                elif len(bits) == 1:
                    self.next_urls[bits[0]] = None
                else:
                    self.next_urls[bits[0]] = bits[1]
            f.close()
        else:
            self.urls = []
            h = httplib2.Http(timeout = 60)
            for url in urls:
                if not url.startswith("http://"):
                    url = "http://" + url
                # Follow initial redirects here to set self.constraints
                try:
                    resp, content = h.request(url)
                    url = resp['content-location']
                except:
                    # This URL is no good. Keep it in the queue to show the
                    # error later
                    pass
                self.urls.append(url)
                self.next_urls[url] = None
            self.constraints = [''] + [urlsplit(url).netloc for url in self.urls]
        self.spiders = spiders
        self.show_spinner = spinner
        self.verbose = verbose
        self.depth = depth
        self.input_file = input_file
        self.generate = generate

    def worker(self):
        """
        Function run by worker processes
        """
        try:
            h = httplib2.Http(timeout = 60)
            for url in iter(self.task_queue.get, 'STOP'):
                result = self.get_urls(h, url)
                self.done_queue.put(result)
        except KeyboardInterrupt:
            self.done_queue.put(Response(url, -1))

    def get_urls(self, h, url):
        """
        Function used to calculate result
        """
        links = []
        try:
            resp, content = h.request(url)
            if self.input_file:
                # Short-circuit if we got our list of links from a file
                return Response(url, resp.status)
            elif resp.status != 200:
                return Response(url, resp.status)
            elif urlsplit(resp['content-location']).netloc not in self.constraints:
                # httplib2 follows redirects automatically
                # Check to make sure we've not been redirected off-site
                return Response(url, resp.status)
            else:
                html = fromstring(content)
        except Exception, e:
            print "%s %s" % (type(e), str(e))
            return Response(url)

        # Add relevant links
        for link in html.cssselect('a'):
            if not link.attrib.has_key('href'):
                # Skip links w/o an href attrib
                continue
            href = link.attrib['href']
            absolute_url = urljoin(resp['content-location'], href.strip())
            parts = urlsplit(absolute_url)
            if parts.netloc in self.constraints and parts.scheme == 'http':
                # Ignore the #foo at the end of the url
                no_fragment = parts[:4] + ('',)
                links.append(urlunsplit(no_fragment))
        return Response(url, resp.status, content, links)

    def process_next_url(self):
        response = self.done_queue.get()
        referer = self.queued_urls[response.url]
        result = '[%s] %s (from %s)' % (response.status_code, response.url, referer)
        if response.status_code == 200:
            if self.verbose:
                print result
                sys.stdout.flush()
            elif self.generate:
                print "%s\t%s" % (response.url, referer)
            elif self.show_spinner:
                self.spinner.spin()
        else:
            print result
            sys.stdout.flush()
        self.seen_urls.add(response.url)
        del(self.queued_urls[response.url])
        for link in response.links:
            if link not in self.seen_urls and link not in self.queued_urls:
                # remember what url referenced this link
                self.next_urls[link] = response.url

    def crawl(self):
        # For the next level
        current_depth = 0
        try:
            # Start worker processes
            for i in range(self.spiders):
                p = Process(target=self.worker)
                p.start()
                self.processes.append(p)

            while len(self.next_urls) > 0 and (current_depth <= self.depth or self.depth == -1):
                if self.verbose:
                    print "Starting link depth %s" % current_depth
                    sys.stdout.flush()

                # place next urls into the task queue, possibly
                # short-circuiting if we're generating them
                for url, referer in self.next_urls.iteritems():
                    self.queued_urls[url] = referer
                    if self.generate and current_depth == self.depth:
                        self.done_queue.put(Response(url, 200))
                    else:
                        self.task_queue.put(url)
                self.next_urls = {}

                while len(self.queued_urls) > 0:
                    self.process_next_url()
                current_depth += 1

        except KeyboardInterrupt:
            pass
        finally:
            # Give the spiders a chance to exit cleanly
            for i in range(self.spiders):
                self.task_queue.put('STOP')
            for p in self.processes:
                # Forcefully close the spiders
                p.terminate()
                p.join()

def main():
    parser = OptionParser()
    options_a = [
        ["-s", "--spiders", dict(dest="spiders", type="int", default=1, help="sends more than one spider")],
        ["-S", "--nospinner", dict(dest="spinner", action="store_false", default=True, help="turns off the spinner")],
        ["-v", "--verbose", dict(dest="verbose", action="store_true", default=False, help="outputs every request (implies --nospiner)")],
        ["-d", "--depth", dict(dest="depth", type="int", default=-1, help="does a breadth-first crawl, stopping after DEPTH levels")],
        ['-g', '--generate', dict(dest='generate', action='store_true', default=False, help='generate a list of crawled URLs on stdout')],
        ['-i', '--input', dict(dest='input_file', type='str', default='', help='file of URLs to crawl')],
    ]
    for s, l, k in options_a:
        parser.add_option(s, l, **k)
    (options, args) = parser.parse_args()
     # Submit first url
    urls = [unicode(url) for url in args]
    kwargs = {
        'urls': urls,
        'spiders': options.spiders,
        'spinner': options.spinner,
        'verbose': options.verbose,
        'depth': options.depth,
        'generate': options.generate,
        'input_file': options.input_file
    }
    spider = Patu(**kwargs)
    spider.crawl()
    print

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = test
import httplib2
from nose.tools import eq_, with_setup
from os import path, remove
import sys

try:
    __file__
except NameError:
    __file__ = 'test/test.py'
sys.path.append(path.join(path.dirname(__file__), '..'))

from patu import Patu, Spinner, main

TEST_URL = 'http://www.djangoproject.com'
SEEN_URLS = set(['http://www.djangoproject.com',
                 'http://www.djangoproject.com/',
                 'http://www.djangoproject.com/community/',
                 'http://www.djangoproject.com/download/',
                 'http://www.djangoproject.com/foundation/',
                 'http://www.djangoproject.com/weblog/',
                 'http://www.djangoproject.com/weblog/2010/apr/14/django-1_2-release-schedule-update-5/',
                 'http://www.djangoproject.com/weblog/2010/apr/22/django-1_2-release-schedule-update-6/',
                 'http://www.djangoproject.com/weblog/2010/apr/28/django-1_2-release-schedule-update-7/',
                 'http://www.djangoproject.com/weblog/2010/may/05/12-rc-1/'])
TEST_HTML = path.join(path.dirname(__file__), 'test.html')
TEST_INPUT = path.join(path.dirname(__file__), 'test_input.txt')
LINKS = ['http://www.djangoproject.com/',
         'http://www.djangoproject.com/',
         'http://www.djangoproject.com/download/',
         'http://www.djangoproject.com/weblog/',
         'http://www.djangoproject.com/community/',
         'http://www.djangoproject.com/download/',
         'http://www.djangoproject.com/weblog/2010/may/05/12-rc-1/',
         'http://www.djangoproject.com/weblog/2010/may/05/12-rc-1/',
         'http://www.djangoproject.com/weblog/2010/apr/28/django-1_2-release-schedule-update-7/',
         'http://www.djangoproject.com/weblog/2010/apr/28/django-1_2-release-schedule-update-7/',
         'http://www.djangoproject.com/weblog/2010/apr/22/django-1_2-release-schedule-update-6/',
         'http://www.djangoproject.com/weblog/2010/apr/22/django-1_2-release-schedule-update-6/',
         'http://www.djangoproject.com/weblog/2010/apr/14/django-1_2-release-schedule-update-5/',
         'http://www.djangoproject.com/weblog/2010/apr/14/django-1_2-release-schedule-update-5/',
         'http://www.djangoproject.com/foundation/']

class MockHttpResponse(dict):
    def __init__(self, url, status = 200, **kwargs):
        for key, value in kwargs:
            setattr(self, key, value)
        self.status = status
        self['content-location'] = url

class MockHttp(httplib2.Http):
    h = httplib2.Http
    def request(self, url):
        if url == 'http://redirect.me':
            resp = MockHttpResponse(url = 'http://www.djangoproject.com')
            content = open(TEST_HTML).read()
        elif url == 'http://djangoproject.com':
            resp = MockHttpResponse(url = 'http://www.djangoproject.com')
            content = open(TEST_HTML).read()
        elif url == 'http://error.me':
            resp = MockHttpResponse(url, status=500)
            content = ''
        elif url == 'http://keyboard.me':
            raise KeyboardInterrupt
        elif url == 'http://io.me':
            raise IOError
        elif url == 'http://www.djangoproject.com/offsite_redirect':
            resp = MockHttpResponse(url = 'http://www.other-site.com')
            content = open(TEST_HTML).read()
        else:
            resp = MockHttpResponse(url)
            content = open(TEST_HTML).read()
        return resp, content

def mock():
    httplib2.Http = MockHttp

def unmock():
    httplib2.Http = MockHttp.h

def test_parse_html():
    p = Patu(urls=[TEST_URL])
    r = p.get_urls(MockHttp(), TEST_URL)
    eq_(r.links, LINKS)

def test_spinner():
    s = Spinner()
    for x in xrange(0,6):
        s.spin()
    eq_(s.status, 2)

@with_setup(mock, unmock)
def test_crawl():
    p = Patu(urls=[TEST_URL], depth=1)
    p.crawl()
    eq_(p.seen_urls, SEEN_URLS)

@with_setup(mock, unmock)
def test_generate():

    with open('.test_generated.txt', 'w') as f:
        s = sys.stdout
        sys.stdout = f

        p = Patu(urls=[TEST_URL], depth=1, generate=True)
        p.crawl()

        sys.stdout = s
    with open('.test_generated.txt', 'r') as f:
        generated_urls = f.read().strip()
    remove('.test_generated.txt')
    correct_urls = """
http://www.djangoproject.com	None
http://www.djangoproject.com/weblog/	http://www.djangoproject.com
http://www.djangoproject.com/weblog/2010/apr/22/django-1_2-release-schedule-update-6/	http://www.djangoproject.com
http://www.djangoproject.com/	http://www.djangoproject.com
http://www.djangoproject.com/weblog/2010/apr/28/django-1_2-release-schedule-update-7/	http://www.djangoproject.com
http://www.djangoproject.com/weblog/2010/may/05/12-rc-1/	http://www.djangoproject.com
http://www.djangoproject.com/weblog/2010/apr/14/django-1_2-release-schedule-update-5/	http://www.djangoproject.com
http://www.djangoproject.com/foundation/	http://www.djangoproject.com
http://www.djangoproject.com/community/	http://www.djangoproject.com
http://www.djangoproject.com/download/	http://www.djangoproject.com
"""
    correct_urls = correct_urls.strip()
    eq_(generated_urls, correct_urls)

@with_setup(mock, unmock)
def test_stdin():
    with open(TEST_INPUT) as f:
        s = sys.stdin
        sys.stdin = f

        p = Patu(depth=1, input_file='-', verbose=True)
        p.crawl()

        sys.stdin = s
    eq_(p.seen_urls, SEEN_URLS)

@with_setup(mock, unmock)
def test_file_input():
    p = Patu(depth=1, input_file=TEST_INPUT)
    p.crawl()
    eq_(p.seen_urls, SEEN_URLS)

@with_setup(mock, unmock)
def test_no_http():
    p = Patu(urls=['www.djangoproject.com'], depth=1)
    p.crawl()
    eq_(p.seen_urls, SEEN_URLS)

@with_setup(mock, unmock)
def test_worker():
    p = Patu(urls=['www.djangoproject.com'], depth=1)
    for url, referer in p.next_urls.iteritems():
        p.task_queue.put(url)
    p.task_queue.put('STOP')
    p.worker()
    content = p.done_queue.get().content

    with open(TEST_HTML) as f:
        eq_(f.read(), content)

@with_setup(mock, unmock)
def test_worker_statuses():
    """
    This is kind of wanking - just trying to get test coverage in the worker
    processes
    """
    url_statuses = [
        ('www.djangoproject.com/offsite_redirect', 200),
        ('error.me', 500),
        ('io.me', -1),
        ('keyboard.me', -1)
        ]

    for address, error_code in url_statuses:
        p = Patu(urls=[address], depth=1)
        for url, referer in p.next_urls.iteritems():
            p.task_queue.put(url)
        p.task_queue.put('STOP')
        p.worker()
        u = p.done_queue.get()
        eq_(u.status_code, error_code)

@with_setup(mock, unmock)
def test_worker_input_file():
    p = Patu(urls=['www.djangoproject.com'], depth=1, input_file=TEST_INPUT)
    for url, referer in p.next_urls.iteritems():
        p.task_queue.put(url)
    p.task_queue.put('STOP')
    p.worker()
    p.done_queue.put('STOP')
    for u in iter(p.done_queue.get, 'STOP'):
        try:
            url = u.url
        except AttributeError:
            url = False
        assert url in SEEN_URLS or not url

@with_setup(mock, unmock)
def test_error():
    with open('.test_generated.txt', 'w') as f:
        s = sys.stdout
        sys.stdout = f

        p = Patu(urls=['error.me'], depth=1)
        p.crawl()

        sys.stdout = s
    with open('.test_generated.txt', 'r') as f:
        eq_(f.read().strip(), '[500] http://error.me (from None)')

@with_setup(mock, unmock)
def test_main_process_keyboard():
    p = Patu(urls=['www.djangoproject.com'], depth=1)
    def ctrl_c():
        raise KeyboardInterrupt
    p.process_next_url = ctrl_c
    p.crawl()
    eq_(p.seen_urls, set([]))

@with_setup(mock, unmock)
def test_redirect():
    p = Patu(urls=['www.djangoproject.com'])
    r = p.get_urls(MockHttp(), 'http://www.djangoproject.com/offsite_redirect')
    eq_(r.url, 'http://www.djangoproject.com/offsite_redirect')
    eq_(r.links, [])
    eq_(r.status_code, 200)

@with_setup(mock, unmock)
def test_initial_redirect():
    p = Patu(urls=['redirect.me'], depth=2)
    p.crawl()
    eq_(p.seen_urls, SEEN_URLS)
    p = Patu(urls=['djangoproject.com'], depth=2)
    p.crawl()
    eq_(p.seen_urls, SEEN_URLS)

@with_setup(mock, unmock)
def test_options():
    with open('.test_generated.txt', 'w') as f:
        s = sys.stdout
        sys.stdout = f

        sys.argv = ['patu.py', 'error.me']

        main()

        sys.stdout = s
    with open('.test_generated.txt', 'r') as f:
        eq_(f.read().strip(), '[500] http://error.me (from None)')

########NEW FILE########
