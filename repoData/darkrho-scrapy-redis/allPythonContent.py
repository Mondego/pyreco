__FILENAME__ = items
# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, TakeFirst, Join

class ExampleItem(Item):
    name = Field()
    description = Field()
    link = Field()
    crawled = Field()
    spider = Field()
    url = Field()


class ExampleLoader(XPathItemLoader):
    default_item_class = ExampleItem
    default_input_processor = MapCompose(lambda s: s.strip())
    default_output_processor = TakeFirst()
    description_out = Join()

########NEW FILE########
__FILENAME__ = pipelines
# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/topics/item-pipeline.html
from datetime import datetime

class ExamplePipeline(object):
    def process_item(self, item, spider):
        item["crawled"] = datetime.utcnow()
        item["spider"] = spider.name
        return item

########NEW FILE########
__FILENAME__ = settings
# Scrapy settings for example project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#
SPIDER_MODULES = ['example.spiders']
NEWSPIDER_MODULE = 'example.spiders'

SCHEDULER = "scrapy_redis.scheduler.Scheduler"
SCHEDULER_PERSIST = True
#SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderPriorityQueue"
#SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderQueue"
#SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderStack"

ITEM_PIPELINES = [
    'example.pipelines.ExamplePipeline',
    'scrapy_redis.pipelines.RedisPipeline',
]

########NEW FILE########
__FILENAME__ = dmoz
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.contrib.spiders import CrawlSpider, Rule
from example.items import ExampleLoader

class DmozSpider(CrawlSpider):
    name = 'dmoz'
    allowed_domains = ['dmoz.org']
    start_urls = ['http://www.dmoz.org/']

    rules = (
        Rule(SgmlLinkExtractor(restrict_xpaths='//div[@id="catalogs"]')),
        Rule(SgmlLinkExtractor(restrict_xpaths='//ul[@class="directory dir-col"]'),
             callback='parse_directory', follow=True)
    )

    def parse_directory(self, response):
        hxs = HtmlXPathSelector(response)
        for li in hxs.select('//ul[@class="directory-url"]/li'):
            el = ExampleLoader(selector=li)
            el.add_xpath('name', 'a/text()')
            el.add_xpath('description', 'text()')
            el.add_xpath('link', 'a/@href')
            el.add_value('url', response.url)
            yield el.load_item()

########NEW FILE########
__FILENAME__ = mycrawler_redis
from scrapy_redis.spiders import RedisMixin

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor

from example.items import ExampleLoader


class MyCrawler(RedisMixin, CrawlSpider):
    """Spider that reads urls from redis queue (myspider:start_urls)."""
    name = 'mycrawler_redis'
    redis_key = 'mycrawler:start_urls'

    rules = (
        # follow all links
        Rule(SgmlLinkExtractor(), callback='parse_page', follow=True),
    )

    def set_crawler(self, crawler):
        CrawlSpider.set_crawler(self, crawler)
        RedisMixin.setup_redis(self)

    def parse_page(self, response):
        el = ExampleLoader(response=response)
        el.add_xpath('name', '//title[1]/text()')
        el.add_value('url', response.url)
        return el.load_item()

########NEW FILE########
__FILENAME__ = myspider_redis
from scrapy_redis.spiders import RedisSpider
from example.items import ExampleLoader


class MySpider(RedisSpider):
    """Spider that reads urls from redis queue (myspider:start_urls)."""
    name = 'myspider_redis'
    redis_key = 'myspider:start_urls'

    def parse(self, response):
        el = ExampleLoader(response=response)
        el.add_xpath('name', '//title[1]/text()')
        el.add_value('url', response.url)
        return el.load_item()

########NEW FILE########
__FILENAME__ = process_items
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import redis


def main():
    r = redis.Redis()
    while True:
        # process queue as FIFO, change `blpop` to `brpop` to process as LIFO
        source, data = r.blpop(["dmoz:items"])
        item = json.loads(data)
        try:
            print u"Processing: %(name)s <%(link)s>" % item
        except KeyError:
            print u"Error procesing: %r" % item


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = connection
import redis


# Default values.
REDIS_URL = None
REDIS_HOST = 'localhost'
REDIS_PORT = 6379


def from_settings(settings):
    url = settings.get('REDIS_URL',  REDIS_URL)
    host = settings.get('REDIS_HOST', REDIS_HOST)
    port = settings.get('REDIS_PORT', REDIS_PORT)

    # REDIS_URL takes precedence over host/port specification.
    if url:
        return redis.from_url(url)
    else:
        return redis.Redis(host=host, port=port)

########NEW FILE########
__FILENAME__ = dupefilter
import time
import connection

from scrapy.dupefilter import BaseDupeFilter
from scrapy.utils.request import request_fingerprint


class RFPDupeFilter(BaseDupeFilter):
    """Redis-based request duplication filter"""

    def __init__(self, server, key):
        """Initialize duplication filter

        Parameters
        ----------
        server : Redis instance
        key : str
            Where to store fingerprints
        """
        self.server = server
        self.key = key

    @classmethod
    def from_settings(cls, settings):
        server = connection.from_settings(settings)
        # create one-time key. needed to support to use this
        # class as standalone dupefilter with scrapy's default scheduler
        # if scrapy passes spider on open() method this wouldn't be needed
        key = "dupefilter:%s" % int(time.time())
        return cls(server, key)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings)

    def request_seen(self, request):
        fp = request_fingerprint(request)
        added = self.server.sadd(self.key, fp)
        return not added

    def close(self, reason):
        """Delete data on close. Called by scrapy's scheduler"""
        self.clear()

    def clear(self):
        """Clears fingerprints data"""
        self.server.delete(self.key)

########NEW FILE########
__FILENAME__ = pipelines
import redis
import connection

from twisted.internet.threads import deferToThread
from scrapy.utils.serialize import ScrapyJSONEncoder


class RedisPipeline(object):
    """Pushes serialized item into a redis list/queue"""

    def __init__(self, server):
        self.server = server
        self.encoder = ScrapyJSONEncoder()

    @classmethod
    def from_settings(cls, settings):
        server = connection.from_settings(settings)
        return cls(server)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings)

    def process_item(self, item, spider):
        return deferToThread(self._process_item, item, spider)

    def _process_item(self, item, spider):
        key = self.item_key(item, spider)
        data = self.encoder.encode(item)
        self.server.rpush(key, data)
        return item

    def item_key(self, item, spider):
        """Returns redis key based on given spider"""
        return "%s:items" % spider.name

########NEW FILE########
__FILENAME__ = queue
from scrapy.utils.reqser import request_to_dict, request_from_dict

try:
    import cPickle as pickle
except ImportError:
    import pickle


class Base(object):
    """Per-spider queue/stack base class"""

    def __init__(self, server, spider, key):
        """Initialize per-spider redis queue.

        Parameters:
            server -- redis connection
            spider -- spider instance
            key -- key for this queue (e.g. "%(spider)s:queue")
        """
        self.server = server
        self.spider = spider
        self.key = key % {'spider': spider.name}

    def _encode_request(self, request):
        """Encode a request object"""
        return pickle.dumps(request_to_dict(request, self.spider), protocol=-1)

    def _decode_request(self, encoded_request):
        """Decode an request previously encoded"""
        return request_from_dict(pickle.loads(encoded_request), self.spider)

    def __len__(self):
        """Return the length of the queue"""
        raise NotImplementedError

    def push(self, request):
        """Push a request"""
        raise NotImplementedError

    def pop(self, timeout=0):
        """Pop a request"""
        raise NotImplementedError

    def clear(self):
        """Clear queue/stack"""
        self.server.delete(self.key)


class SpiderQueue(Base):
    """Per-spider FIFO queue"""

    def __len__(self):
        """Return the length of the queue"""
        return self.server.llen(self.key)

    def push(self, request):
        """Push a request"""
        self.server.lpush(self.key, self._encode_request(request))

    def pop(self, timeout=0):
        """Pop a request"""
        if timeout > 0:
            data = self.server.brpop(self.key, timeout)
            if isinstance(data, tuple):
                data = data[1]
        else:
            data = self.server.rpop(self.key)
        if data:
            return self._decode_request(data)


class SpiderPriorityQueue(Base):
    """Per-spider priority queue abstraction using redis' sorted set"""

    def __len__(self):
        """Return the length of the queue"""
        return self.server.zcard(self.key)

    def push(self, request):
        """Push a request"""
        data = self._encode_request(request)
        pairs = {data: -request.priority}
        self.server.zadd(self.key, **pairs)

    def pop(self, timeout=0):
        """
        Pop a request
        timeout not support in this queue class
        """
        # use atomic range/remove using multi/exec
        pipe = self.server.pipeline()
        pipe.multi()
        pipe.zrange(self.key, 0, 0).zremrangebyrank(self.key, 0, 0)
        results, count = pipe.execute()
        if results:
            return self._decode_request(results[0])


class SpiderStack(Base):
    """Per-spider stack"""

    def __len__(self):
        """Return the length of the stack"""
        return self.server.llen(self.key)

    def push(self, request):
        """Push a request"""
        self.server.lpush(self.key, self._encode_request(request))

    def pop(self, timeout=0):
        """Pop a request"""
        if timeout > 0:
            data = self.server.blpop(self.key, timeout)
            if isinstance(data, tuple):
                data = data[1]
        else:
            data = self.server.lpop(self.key)

        if data:
            return self._decode_request(data)


__all__ = ['SpiderQueue', 'SpiderPriorityQueue', 'SpiderStack']

########NEW FILE########
__FILENAME__ = scheduler
import connection

from scrapy.utils.misc import load_object
from scrapy_redis.dupefilter import RFPDupeFilter


# default values
SCHEDULER_PERSIST = False
QUEUE_KEY = '%(spider)s:requests'
QUEUE_CLASS = 'scrapy_redis.queue.SpiderPriorityQueue'
DUPEFILTER_KEY = '%(spider)s:dupefilter'
IDLE_BEFORE_CLOSE = 0


class Scheduler(object):
    """Redis-based scheduler"""

    def __init__(self, server, persist, queue_key, queue_cls, dupefilter_key, idle_before_close):
        """Initialize scheduler.

        Parameters
        ----------
        server : Redis instance
        persist : bool
        queue_key : str
        queue_cls : queue class
        dupefilter_key : str
        idle_before_close : int
        """
        self.server = server
        self.persist = persist
        self.queue_key = queue_key
        self.queue_cls = queue_cls
        self.dupefilter_key = dupefilter_key
        self.idle_before_close = idle_before_close
        self.stats = None

    def __len__(self):
        return len(self.queue)

    @classmethod
    def from_settings(cls, settings):
        persist = settings.get('SCHEDULER_PERSIST', SCHEDULER_PERSIST)
        queue_key = settings.get('SCHEDULER_QUEUE_KEY', QUEUE_KEY)
        queue_cls = load_object(settings.get('SCHEDULER_QUEUE_CLASS', QUEUE_CLASS))
        dupefilter_key = settings.get('DUPEFILTER_KEY', DUPEFILTER_KEY)
        idle_before_close = settings.get('SCHEDULER_IDLE_BEFORE_CLOSE', IDLE_BEFORE_CLOSE)
        server = connection.from_settings(settings)
        return cls(server, persist, queue_key, queue_cls, dupefilter_key, idle_before_close)

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls.from_settings(crawler.settings)
        # FIXME: for now, stats are only supported from this constructor
        instance.stats = crawler.stats
        return instance

    def open(self, spider):
        self.spider = spider
        self.queue = self.queue_cls(self.server, spider, self.queue_key)
        self.df = RFPDupeFilter(self.server, self.dupefilter_key % {'spider': spider.name})
        if self.idle_before_close < 0:
            self.idle_before_close = 0
        # notice if there are requests already in the queue to resume the crawl
        if len(self.queue):
            spider.log("Resuming crawl (%d requests scheduled)" % len(self.queue))

    def close(self, reason):
        if not self.persist:
            self.df.clear()
            self.queue.clear()

    def enqueue_request(self, request):
        if not request.dont_filter and self.df.request_seen(request):
            return
        if self.stats:
            self.stats.inc_value('scheduler/enqueued/redis', spider=self.spider)
        self.queue.push(request)

    def next_request(self):
        block_pop_timeout = self.idle_before_close
        request = self.queue.pop(block_pop_timeout)
        if request and self.stats:
            self.stats.inc_value('scheduler/dequeued/redis', spider=self.spider)
        return request

    def has_pending_requests(self):
        return len(self) > 0

########NEW FILE########
__FILENAME__ = spiders
import connection

from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from scrapy.spider import BaseSpider


class RedisMixin(object):
    """Mixin class to implement reading urls from a redis queue."""
    redis_key = None  # use default '<spider>:start_urls'

    def setup_redis(self):
        """Setup redis connection and idle signal.

        This should be called after the spider has set its crawler object.
        """
        if not self.redis_key:
            self.redis_key = '%s:start_urls' % self.name

        self.server = connection.from_settings(self.crawler.settings)
        # idle signal is called when the spider has no requests left,
        # that's when we will schedule new requests from redis queue
        self.crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)
        self.crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        self.log("Reading URLs from redis list '%s'" % self.redis_key)

    def next_request(self):
        """Returns a request to be scheduled or none."""
        url = self.server.lpop(self.redis_key)
        if url:
            return self.make_requests_from_url(url)

    def schedule_next_request(self):
        """Schedules a request if available"""
        req = self.next_request()
        if req:
            self.crawler.engine.crawl(req, spider=self)

    def spider_idle(self):
        """Schedules a request if available, otherwise waits."""
        self.schedule_next_request()
        raise DontCloseSpider

    def item_scraped(self, *args, **kwargs):
        """Avoids waiting for the spider to  idle before scheduling the next request"""
        self.schedule_next_request()


class RedisSpider(RedisMixin, BaseSpider):
    """Spider that reads urls from redis queue when idle."""

    def set_crawler(self, crawler):
        super(RedisSpider, self).set_crawler(crawler)
        self.setup_redis()

########NEW FILE########
__FILENAME__ = tests
import os
import redis
import connection

from scrapy.http import Request
from scrapy.spider import BaseSpider
from unittest import TestCase

from .dupefilter import RFPDupeFilter
from .queue import SpiderQueue, SpiderPriorityQueue, SpiderStack
from .scheduler import Scheduler


# allow test settings from environment
REDIS_HOST = os.environ.get('REDIST_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))


class DupeFilterTest(TestCase):

    def setUp(self):
        self.server = redis.Redis(REDIS_HOST, REDIS_PORT)
        self.key = 'scrapy_redis:tests:dupefilter:'
        self.df = RFPDupeFilter(self.server, self.key)

    def tearDown(self):
        self.server.delete(self.key)

    def test_dupe_filter(self):
        req = Request('http://example.com')

        self.assertFalse(self.df.request_seen(req))
        self.assertTrue(self.df.request_seen(req))

        self.df.close('nothing')


class QueueTestMixin(object):

    queue_cls = None

    def setUp(self):
        self.spider = BaseSpider('myspider')
        self.key = 'scrapy_redis:tests:%s:queue' % self.spider.name
        self.server = redis.Redis(REDIS_HOST, REDIS_PORT)
        self.q = self.queue_cls(self.server, BaseSpider('myspider'), self.key)

    def tearDown(self):
        self.server.delete(self.key)

    def test_clear(self):
        self.assertEqual(len(self.q), 0)

        for i in range(10):
            # XXX: can't use same url for all requests as SpiderPriorityQueue
            # uses redis' set implemention and we will end with only one
            # request in the set and thus failing the test. It should be noted
            # that when using SpiderPriorityQueue it acts as a request
            # duplication filter whenever the serielized requests are the same.
            # This might be unwanted on repetitive requests to the same page
            # even with dont_filter=True flag.
            req = Request('http://example.com/?page=%s' % i)
            self.q.push(req)
        self.assertEqual(len(self.q), 10)

        self.q.clear()
        self.assertEqual(len(self.q), 0)


class SpiderQueueTest(QueueTestMixin, TestCase):

    queue_cls = SpiderQueue

    def test_queue(self):
        req1 = Request('http://example.com/page1')
        req2 = Request('http://example.com/page2')

        self.q.push(req1)
        self.q.push(req2)

        out1 = self.q.pop()
        out2 = self.q.pop()

        self.assertEqual(out1.url, req1.url)
        self.assertEqual(out2.url, req2.url)


class SpiderPriorityQueueTest(QueueTestMixin, TestCase):

    queue_cls = SpiderPriorityQueue

    def test_queue(self):
        req1 = Request('http://example.com/page1', priority=100)
        req2 = Request('http://example.com/page2', priority=50)
        req3 = Request('http://example.com/page2', priority=200)

        self.q.push(req1)
        self.q.push(req2)
        self.q.push(req3)

        out1 = self.q.pop()
        out2 = self.q.pop()
        out3 = self.q.pop()

        self.assertEqual(out1.url, req3.url)
        self.assertEqual(out2.url, req1.url)
        self.assertEqual(out3.url, req2.url)


class SpiderStackTest(QueueTestMixin, TestCase):

    queue_cls = SpiderStack

    def test_queue(self):
        req1 = Request('http://example.com/page1')
        req2 = Request('http://example.com/page2')

        self.q.push(req1)
        self.q.push(req2)

        out1 = self.q.pop()
        out2 = self.q.pop()

        self.assertEqual(out1.url, req2.url)
        self.assertEqual(out2.url, req1.url)


class SchedulerTest(TestCase):

    def setUp(self):
        self.server = redis.Redis(REDIS_HOST, REDIS_PORT)
        self.key_prefix = 'scrapy_redis:tests:'
        self.queue_key = self.key_prefix + '%(spider)s:requests'
        self.dupefilter_key = self.key_prefix + '%(spider)s:dupefilter'
        self.idle_before_close = 0
        self.scheduler = Scheduler(self.server, False, self.queue_key,
                                   SpiderQueue, self.dupefilter_key,
                                   self.idle_before_close)

    def tearDown(self):
        for key in self.server.keys(self.key_prefix):
            self.server.delete(key)

    def test_scheduler(self):
        # default no persist
        self.assertFalse(self.scheduler.persist)

        spider = BaseSpider('myspider')
        self.scheduler.open(spider)
        self.assertEqual(len(self.scheduler), 0)

        req = Request('http://example.com')
        self.scheduler.enqueue_request(req)
        self.assertTrue(self.scheduler.has_pending_requests())
        self.assertEqual(len(self.scheduler), 1)

        # dupefilter in action
        self.scheduler.enqueue_request(req)
        self.assertEqual(len(self.scheduler), 1)

        out = self.scheduler.next_request()
        self.assertEqual(out.url, req.url)

        self.assertFalse(self.scheduler.has_pending_requests())
        self.assertEqual(len(self.scheduler), 0)

        self.scheduler.close('finish')

    def test_scheduler_persistent(self):
        messages = []
        spider = BaseSpider('myspider')
        spider.log = lambda *args, **kwargs: messages.append([args, kwargs])

        self.scheduler.persist = True
        self.scheduler.open(spider)

        self.assertEqual(messages, [])

        self.scheduler.enqueue_request(Request('http://example.com/page1'))
        self.scheduler.enqueue_request(Request('http://example.com/page2'))

        self.assertTrue(self.scheduler.has_pending_requests())
        self.scheduler.close('finish')

        self.scheduler.open(spider)
        self.assertEqual(messages, [
            [('Resuming crawl (2 requests scheduled)',), {}],
        ])
        self.assertEqual(len(self.scheduler), 2)

        self.scheduler.persist = False
        self.scheduler.close('finish')

        self.assertEqual(len(self.scheduler), 0)


class ConnectionTest(TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # We can get a connection from just REDIS_URL.
    def test_redis_url(self):
        settings = dict(
            REDIS_URL = 'redis://foo:bar@localhost:9001/42'
        )

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'localhost')
        self.assertEqual(connect_args['port'], 9001)
        self.assertEqual(connect_args['password'], 'bar')
        self.assertEqual(connect_args['db'], 42)

    # We can get a connection from REDIS_HOST/REDIS_PORT.
    def test_redis_host_port(self):
        settings = dict(
            REDIS_HOST = 'localhost',
            REDIS_PORT = 9001
        )

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'localhost')
        self.assertEqual(connect_args['port'], 9001)

    # REDIS_URL takes precedence over REDIS_HOST/REDIS_PORT.
    def test_redis_url_precedence(self):
        settings = dict(
            REDIS_HOST = 'baz',
            REDIS_PORT = 1337,
            REDIS_URL = 'redis://foo:bar@localhost:9001/42'
        )

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'localhost')
        self.assertEqual(connect_args['port'], 9001)
        self.assertEqual(connect_args['password'], 'bar')
        self.assertEqual(connect_args['db'], 42)

    # We fallback to REDIS_HOST/REDIS_PORT if REDIS_URL is None.
    def test_redis_host_port_fallback(self):
        settings = dict(
            REDIS_HOST = 'baz',
            REDIS_PORT = 1337,
            REDIS_URL = None
        )

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'baz')
        self.assertEqual(connect_args['port'], 1337)

    # We use default values for REDIS_HOST/REDIS_PORT.
    def test_redis_default(self):
        settings = dict()

        server = connection.from_settings(settings)
        connect_args = server.connection_pool.connection_kwargs

        self.assertEqual(connect_args['host'], 'localhost')
        self.assertEqual(connect_args['port'], 6379)

########NEW FILE########
