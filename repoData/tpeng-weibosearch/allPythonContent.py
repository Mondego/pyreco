__FILENAME__ = feeds
#-*- coding: utf-8 -*-
# A weibo parser.
#
# tpeng <pengtaoo@gmail.com>
# 2012/9/21
#
from pyquery import PyQuery as pq
from datetime import datetime
import re

class SearchPage():
  def __init__(self, values):
    if values is None or len(values) == 0:
      self.values = []
    else:
      self.values = values

  def __len__(self):
    return len(self.values)

  def __getitem__(self, key):
    return self.values[key]

  def __iter__(self):
    return iter(self.values)

  @staticmethod
  def wrap(html):
    jQuery = pq(html)
    hrefs = jQuery('li a')
    values = []
    if len(hrefs) > 1:
      size = int(hrefs[-2].text)
      href = hrefs[-2]
      link = href.get('href')
      if link.startswith('/'):
        link = '%s%s' % ('http://s.weibo.com', link)
      for i in xrange(1, size + 1):
        values.append(re.sub(r'page=\d+', 'page=%s' % i, link))
    return SearchPage(values)

# represent a single feed return by the weibo search
class Author():
  def __init__(self, id, name, img_url):
    self.id = id
    self.name = name
    self.img_url = img_url

  @staticmethod
  def wrap(html):
    jQuery = pq(html)
    name = unicode(jQuery('a').attr('title'))
    img = jQuery('a img').attr('src')
    #    id = unicode(jQuery('a').attr('suda-data').split(':')[-1])
    id = re.search('id=(\d+)&', jQuery('a img').attr('usercard'), re.I).group(1)
    return Author(id, name, img)

  def __str__(self):
    return 'Author(id=%s, name=%s)' % (self.id, self.name)


class Feed():
  def __init__(self, mid, author, content, retweets, replies, timestamp):
    self.mid = mid
    self.author = author
    self.content = content
    self.retweets = retweets
    self.replies = replies
    self.timestamp = timestamp

  @staticmethod
  def wrap(html):
    replies = retweets = 0
    jQuery = pq(html)
    dl = jQuery("dl.feed_list")
    author = Author.wrap(dl('dt.face').html())
    em = jQuery('dd.content em').eq(0)
    imgs = em.find('img')
    # replace the images with image's alt text
    for img in imgs:
      if pq(img).attr('alt'):
        pq(img).replaceWith(pq(img).attr('alt'))
    spans = em.find('span')
    # replace the span (added by weibo search for highlight the words) with text
    for span in spans:
      pq(span).replaceWith(pq(span).text())
    content = em.text()
    info = jQuery('dd.content p.info').text()
    retweets_match = re.search(ur'\u8f6c\u53d1\((\d+)\)', info, re.M | re.I | re.U)
    if retweets_match:
      retweets = int(retweets_match.group(1))
    replies_match = re.search(ur'\u8bc4\u8bba\((\d+)\)', info, re.M | re.I | re.U)
    if replies_match:
      replies = int(replies_match.group(1))

    time = jQuery('dd.content p.info a.date').attr('date')
    timestamp = datetime.fromtimestamp(long(time) / 1000)
    return Feed(dl.attr('mid'), author, content, retweets, replies, timestamp)

  def __str__(self):
    return 'Feed(mid=%s author=%s)' % (self.mid, self.author)

########NEW FILE########
__FILENAME__ = items
# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class ScrapyWeiboItem(Item):
  html = Field()

########NEW FILE########
__FILENAME__ = pipelines
# See: http://doc.scrapy.org/en/0.14/topics/item-pipeline.html
# tpeng <pengtaoo@gmail.com>
#
from scrapy.exceptions import DropItem
from twisted.enterprise import adbapi
from weibosearch.feeds import Feed
from scrapy import log
import MySQLdb.cursors

class ScrapyWeiboPipeline(object):
  def __init__(self):
    self.dbpool = adbapi.ConnectionPool('MySQLdb',
      db='weibosearch2',
      user='root',
      passwd='pw',
      cursorclass=MySQLdb.cursors.DictCursor,
      charset='utf8',
      use_unicode=True
    )

  def process_item(self, item, spider):
    # run db query in thread pool
    if spider.savedb == 'True':
        query = self.dbpool.runInteraction(self._conditional_insert, item)
        query.addErrback(self.handle_error)
    return item

  def _conditional_insert(self, tx, item):
    # create record if doesn't exist.
    # all this block run on it's own thread
    try:
      feed = Feed.wrap(item['html'])
    except Exception as e:
      print e
      raise DropItem('Feed.wrap error: %s' % item['html'])

    # insert author
    tx.execute("select * from author where id = %s" % feed.author.id)
    result = tx.fetchone()
    if result:
      log.msg("Author already stored in db: %s" % feed.author.id, level=log.INFO)
    else:
      tx.execute("insert into author (id, name, url)"
                 "values (%s, %s, %s)",
        (feed.author.id, feed.author.name, feed.author.img_url))
      log.msg("Author stored in db: %s" % feed.author.id, level=log.INFO)

    # insert feed
    tx.execute("select * from feed where id = %s" % feed.mid)
    result = tx.fetchone()
    if result:
      log.msg("Feed already stored in db: (%s,%s)" % (feed.author.id, feed.mid), level=log.INFO)
    else:
      tx.execute("insert into feed (id, author_id, content, retweets, replies, timestamp)"
                 "values (%s, %s, %s, %s, %s, %s)",
        (feed.mid, feed.author.id, feed.content, feed.retweets, feed.replies,
         feed.timestamp.strftime('%Y-%m-%d %H:%M:%S')))

      log.msg("Feed stored in db: %s" % feed.mid, level=log.INFO)

  def handle_error(self, e):
    log.err(e)
########NEW FILE########
__FILENAME__ = query
class QueryFactory:
  @staticmethod
  def create_query(query):
    return 'http://s.weibo.com/weibo/%s&Refer=STopic_box&scope=ori' % query

  @staticmethod
  def create_paging_query(query, page):
    return 'http://s.weibo.com/weibo/%s&page=%d' % (query, page)

  @staticmethod
  def create_timerange_query(query, start, end):
    s = start.strftime('%Y-%m-%d-%H')
    e = end.strftime('%Y-%m-%d-%H')
    return 'http://s.weibo.com/weibo/%s&Refer=STopic_box&timescope=custom:%s:%s&scope=ori' % (query, s, e)


########NEW FILE########
__FILENAME__ = dupefilter
import redis
import time
from scrapy.dupefilter import BaseDupeFilter
from scrapy.utils.request import request_fingerprint

class RFPDupeFilter(BaseDupeFilter):
  """Redis-based request duplication filter"""

  def __init__(self, server, key):
    """Initialize duplication filter

    Parameters:
        server -- Redis connection
        key -- redis key to store fingerprints

    """
    self.server = server
    self.key = key

  @classmethod
  def from_settings(cls, settings):
    host = settings.get('REDIS_HOST', 'localhost')
    port = settings.get('REDIS_PORT', 6379)
    server = redis.Redis(host, port)
    # create one-time key. needed to support to use this
    # class as standalone dupefilter with scrapy's default scheduler
    # if scrapy passes spider on open() method this wouldn't be needed
    key = "dupefilter:%s" % int(time.time())
    return cls(server, key)

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

from twisted.internet.threads import deferToThread
from scrapy.utils.serialize import ScrapyJSONEncoder


class RedisPipeline(object):
  """Pushes serialized item into a redis list/queue"""

  def __init__(self, host, port):
    self.server = redis.Redis(host, port)
    self.encoder = ScrapyJSONEncoder()

  @classmethod
  def from_settings(cls, settings):
    host = settings.get('REDIS_HOST', 'localhost')
    port = settings.get('REDIS_PORT', 6379)
    return cls(host, port)

  def process_item(self, item, spider):
    return deferToThread(self._process_item, item, spider)

  def _process_item(self, item, spider):
    key = self.item_key(item, spider)
    data = self.encoder.encode(dict(item))
    self.server.rpush(key, data)
    return item

  def item_key(self, item, spider):
    """Returns redis key based on given spider"""
    return "%s:items" % spider.name


########NEW FILE########
__FILENAME__ = queue
import marshal
from scrapy.utils.reqser import request_to_dict, request_from_dict

class SpiderQueue(object):
  """Per-spider queue abstraction on top of redis using sorted set"""

  def __init__(self, server, spider, key):
    """Initialize per-spider redis queue

    Parameters:
        redis -- redis connection
        spider -- spider instance
        key -- key for this queue (e.g. "%(spider)s:queue")

    """
    self.redis = server
    self.spider = spider
    self.key = key % {'spider': spider.name}

  def __len__(self):
    return self.redis.zcard(self.key)

  def push(self, request):
    data = marshal.dumps(request_to_dict(request, self.spider))
    pairs = {data: -request.priority}
    self.redis.zadd(self.key, **pairs)

  def pop(self):
    # use atomic range/remove using multi/exec
    pipe = self.redis.pipeline()
    pipe.multi()
    pipe.zrange(self.key, 0, 0).zremrangebyrank(self.key, 0, 0)
    results, count = pipe.execute()
    if results:
      return request_from_dict(marshal.loads(results[0]), self.spider)

  def clear(self):
    self.redis.delete(self.key)

########NEW FILE########
__FILENAME__ = scheduler
import redis
from weibosearch.redis.queue import SpiderQueue
from weibosearch.redis.dupefilter import RFPDupeFilter

# default values
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
SCHEDULER_PERSIST = True
QUEUE_KEY = '%(spider)s:requests'
DUPEFILTER_KEY = '%(spider)s:dupefilter'

class Scheduler(object):
  """Redis-based scheduler"""

  def __init__(self, redis, persist, queue_key):
    self.server = redis
    self.persist = persist
    self.queue_key = queue_key
    # in-memory queue
    self.own_queue = []

  def __len__(self):
    return len(self.queue)

  @classmethod
  def from_settings(cls, settings):
    host = settings.get('REDIS_HOST', REDIS_HOST)
    port = settings.get('REDIS_PORT', REDIS_PORT)
    persist = settings.get('SCHEDULER_PERSIST', SCHEDULER_PERSIST)
    queue_key = settings.get('SCHEDULER_QUEUE_KEY', QUEUE_KEY)
    server = redis.Redis(host, port)
    return cls(server, persist, queue_key)

  @classmethod
  def from_crawler(cls, crawler):
    settings = crawler.settings
    return cls.from_settings(settings)

  def open(self, spider):
    self.spider = spider
    self.queue = SpiderQueue(self.server, spider, self.queue_key)
    self.df = RFPDupeFilter(self.server, DUPEFILTER_KEY % {'spider': spider.name})
    # notice if there are requests already in the queue
    if not self.persist:
      self.df.clear()
      self.queue.clear()

    if len(self.queue):
      spider.log("Resuming crawl (%d requests scheduled)" % len(self.queue))

  def close(self, reason):
    pass

  def enqueue_request(self, request):
    if not request.dont_filter and self.df.request_seen(request):
      return
    if self.spider.logined:
      self.queue.push(request)
    else:
      self.own_queue.append(request)

  def next_request(self):
    if self.spider.logined:
      return self.queue.pop()
    if len(self.own_queue) > 0:
      return self.own_queue.pop()

  def has_pending_requests(self):
    if self.spider.logined:
      return len(self) > 0
    return len(self.own_queue)


########NEW FILE########
__FILENAME__ = settings
# Scrapy settings for scrapy_weibo project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'weibosearch'

SPIDER_MODULES = ['weibosearch.spiders']
NEWSPIDER_MODULE = 'weibosearch.spiders'

# redis config
REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# scheduler config
SCHEDULER_PERSIST = True
QUEUE_KEY = '%(spider)s:requests'
DUPEFILTER_KEY = '%(spider)s:dupefilter'
SCHEDULER = "weibosearch.redis.scheduler.Scheduler"

# pipelines config
ITEM_PIPELINES = ['weibosearch.pipelines.ScrapyWeiboPipeline']

DOWNLOAD_DELAY = 10

TIME_DELTA = 30

# bootstrap from file (item.txt) or from db
BOOTSTRAP = 'file'

# how many feeds can fetch from a item
FEED_LIMIT = 300000
########NEW FILE########
__FILENAME__ = weibo
#coding=utf8
# original from http://www.douban.com/note/201767245/
# also see http://www.cnblogs.com/mouse-coder/archive/2013/03/03/2941265.html for recent change in weibo login
# modified by tpeng <pengtaoo@gmail.com>
# 2012/9/20

import urllib
import urllib2
import cookielib
import base64
import re, sys, json
import binascii
import rsa

postdata = {
  'entry': 'weibo',
  'gateway': '1',
  'from': '',
  'savestate': '7',
  'userticket': '1',
  'ssosimplelogin': '1',
  'vsnf': '1',
  'vsnval': '',
  'su': '',
  'service': 'miniblog',
  'servertime': '',
  'nonce': '',
  'pwencode': 'rsa2',
  'sp': '',
  'encoding': 'UTF-8',
  'url': 'http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack',
  'returntype': 'META'
}

class Weibo():
  def __init__(self):
    # 获取一个保存cookie的对象
    self.cj = cookielib.LWPCookieJar()

    # 将一个保存cookie对象，和一个HTTP的cookie的处理器绑定
    cookie_support = urllib2.HTTPCookieProcessor(self.cj)

    # 创建一个opener，将保存了cookie的http处理器，还有设置一个handler用于处理http的URL的打开
    opener = urllib2.build_opener(cookie_support, urllib2.HTTPHandler)

    # 将包含了cookie、http处理器、http的handler的资源和urllib2对象板顶在一起
    urllib2.install_opener(opener)

  def _get_servertime(self, username):
    url = 'http://login.sina.com.cn/sso/prelogin.php?entry=sso&callback=sinaSSOController.preloginCallBack&su=%s&rsakt=mod&client=ssologin.js(v1.4.4)' %username
    data = urllib2.urlopen(url).read()
    p = re.compile('\((.*)\)')
    json_data = p.search(data).group(1)
    data = json.loads(json_data)
    servertime = str(data['servertime'])
    nonce = data['nonce']
    pubkey = data['pubkey']
    rsakv = data['rsakv']
    return servertime, nonce, pubkey, rsakv

  def _get_pwd(self, pwd, servertime, nonce, pubkey):
    rsaPublickey = int(pubkey, 16)
    key = rsa.PublicKey(rsaPublickey, 65537)
    message = str(servertime) + '\t' + str(nonce) + '\n' + str(pwd)
    pwd = rsa.encrypt(message, key)
    return binascii.b2a_hex(pwd)

  def _get_user(self, username):
    username_ = urllib.quote(username)
    username = base64.encodestring(username_)[:-1]
    return username

  def login(self, username, pwd):
    url = 'http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.4)'
    try:
      servertime, nonce, pubkey, rsakv = self._get_servertime(username)
    except:
      print >> sys.stderr, 'Get severtime error!'
      return None
    global postdata
    postdata['servertime'] = servertime
    postdata['nonce'] = nonce
    postdata['su'] = self._get_user(username)
    postdata['sp'] = self._get_pwd(pwd, servertime, nonce, pubkey)
    postdata['rsakv'] = rsakv
    postdata = urllib.urlencode(postdata)
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:8.0) Gecko/20100101 Firefox/8.0'}

    req = urllib2.Request(
      url=url,
      data=postdata,
      headers=headers
    )

    result = urllib2.urlopen(req)
    text = result.read()
    p = re.compile('location\.replace\([\'|"](.*?)[\'|"]\)')
    try:
      return p.search(text).group(1)
    except:
      return None

if __name__ == '__main__':
  weibo = Weibo()
  # weibo.login('your weibo account', 'your password')

########NEW FILE########
__FILENAME__ = WeiboSearchSpider
#coding=utf-8
# weibosearch spider
# tpeng <pengtaoo@gmail.com>
#
import codecs
from datetime import datetime, timedelta
import urllib
import MySQLdb
from scrapy import log
from scrapy.conf import settings
from scrapy.exceptions import CloseSpider
from scrapy.http import Request
from scrapy.spider import BaseSpider
from weibosearch.feeds import SearchPage
from weibosearch.items import ScrapyWeiboItem
import re, json
from pyquery import PyQuery as pq
from lxml.html import tostring
from weibosearch.query import QueryFactory
from weibosearch.sina.weibo import Weibo
from weibosearch.sina import _epoch
from weibosearch.timerange import daterange

# default values
REDIS_HOST = 'localhost'
REDIS_PORT = 6379

class WeiboSearchSpider(BaseSpider):
  name = 'weibosearch'
  allowed_domains = ['weibo.com']
  weibo = Weibo()
  # allow save to db
  savedb = 'True'
  username = 'YOUR_WEIBO_ACCOUNT'
  password = 'YOUR_WEIBO_PASSWORD'

  def __init__(self, name=None, **kwargs):
    super(WeiboSearchSpider, self).__init__(name, **kwargs)
    if not self.savedb:
        self.db = MySQLdb.connect(host="localhost", port=3306, user="root", passwd="pw", db="weibosearch2",
          charset='utf8', use_unicode=True)
        self.cursor = self.db.cursor()
    self.logined = False

    self.log('login with %s' % self.username)
    login_url = self.weibo.login(self.username, self.password)
    if login_url:
      self.start_urls.append(login_url)

  # only parse the login page
  def parse(self, response):
    if response.body.find('feedBackUrlCallBack') != -1:
      data = json.loads(re.search(r'feedBackUrlCallBack\((.*?)\)', response.body, re.I).group(1))
      userinfo = data.get('userinfo', '')
      if len(userinfo):
        log.msg('user id %s' % userinfo['userid'], level=log.INFO)
        assert userinfo['userid'] == self.username
        self.logined = True

        bootstrap = settings.get('BOOTSTRAP')
        log.msg('bootstrap from %s' % bootstrap, level=log.INFO)
        # FIXME: use last scheduled time instead of today, otherwise queue filter will not work
        today = datetime.now()
        if bootstrap == 'file':
          lines = tuple(codecs.open('items.txt', 'r', 'utf-8'))
          for line in lines:
            if line.startswith("#"):
              continue
            start = _epoch()
            url = QueryFactory.create_timerange_query(urllib.quote(line.encode('utf8')), start, today)
            request = Request(url=url, callback=self.parse_weibo, meta={
              'query': line,
              'start': start.strftime("%Y-%m-%d %H:%M:%S"),
              'end': today.strftime("%Y-%m-%d %H:%M:%S"),
              'last_fetched': today.strftime("%Y-%m-%d %H:%M:%S")})
            yield request
      else:
        self.log('login failed: errno=%s, reason=%s' % (data.get('errno', ''), data.get('reason', '')))

      # TODO: can also bootstrap from db

  def parse_weibo(self, response):
    query = response.request.meta['query']
    start = datetime.strptime(response.request.meta['start'], "%Y-%m-%d %H:%M:%S")
    end = datetime.strptime(response.request.meta['end'], "%Y-%m-%d %H:%M:%S")
    range = daterange(start, end).delta()
    last_fetched = datetime.strptime(response.request.meta['last_fetched'], "%Y-%m-%d %H:%M:%S")

    jQuery = pq(response.body)
    scripts = jQuery('script')

    text = "".join(filter(lambda x: x is not None, [x.text for x in scripts]))
    # check if we exceed the sina limit
    sassfilter_match = re.search(r'{(\"pid\":\"pl_common_sassfilter\".*?)}', text, re.M | re.I)
    if sassfilter_match:
      raise CloseSpider('weibo search exceeded')

    # check the num of search results
    totalshow_match = re.search(r'{(\"pid\":\"pl_common_totalshow\".*?)}', text, re.M | re.I)
    if totalshow_match:
      html = json.loads(totalshow_match.group())['html']
      if len(html) == 0:
        raise CloseSpider('not login? %s' % html)
      totalshow = pq(html)
      if totalshow('div.topcon_l').html() is None:
        log.msg('%s 0 feeds' % query, level=log.INFO)
        return
      topcon_num = int(re.search('\s(\d+)\s', totalshow('div.topcon_l').text().replace(',', ''), re.I).group(1))
      log.msg('%s %d feeds' % (query, topcon_num), level=log.INFO)
      max_feeds = settings.getint('FEED_LIMIT', 200000)
      if topcon_num > max_feeds:
        log.msg('too much (%d) result for %s.' % (topcon_num, query), logLevel=log.WARNING)
      elif 1000 < topcon_num < max_feeds:
        # weibo search only allow 20 feeds on 1 page and at most 50 pages.
        days = range.days / float(2)
        middle = start + timedelta(days)

        # first part
        url = QueryFactory.create_timerange_query(urllib.quote(query.encode('utf8')), start, middle)
        request = Request(url=url, callback=self.parse_weibo)
        request.meta['query'] = query
        request.meta['start'] = start.strftime("%Y-%m-%d %H:%M:%S")
        request.meta['end'] = middle.strftime("%Y-%m-%d %H:%M:%S")
        request.meta['priority'] = days / 2
        request.meta['last_fetched'] = last_fetched.strftime("%Y-%m-%d %H:%M:%S")
        yield request

        # second part
        url2 = QueryFactory.create_timerange_query(urllib.quote(query.encode('utf8')), middle, end)
        request2 = Request(url=url2, callback=self.parse_weibo)
        request2.meta['query'] = query
        request2.meta['start'] = middle.strftime("%Y-%m-%d %H:%M:%S")
        request2.meta['end'] = end.strftime("%Y-%m-%d %H:%M:%S")
        request2.meta['priority'] = days / 2
        request2.meta['last_fetched'] = last_fetched.strftime("%Y-%m-%d %H:%M:%S")
        yield request2
      else:
        # check the feeds update
        feedlist_match = re.search(r'{(\"pid\":\"pl_weibo_feedlist\".*?)}', text, re.M | re.I)
        if feedlist_match:
          search_results = pq(json.loads(feedlist_match.group())['html'])
          feeds = search_results('dl.feed_list')
          search_pages = search_results('ul.search_page_M')
          pages = SearchPage.wrap(search_pages)

          # send the items to pipeline
          for feed in feeds:
            item = ScrapyWeiboItem()
            item['html'] = tostring(feed)
            yield item
            # skip first page and request other pages
          for i in xrange(2, len(pages)):
            query = pages[i]
            log.msg('%s' % query)
            request = Request(url=query, callback=self.parse_page)
            request.meta['query'] = query
            yield request

  # parse single weibo page
  def parse_page(self, response):
    jQuery = pq(response.body)
    scripts = jQuery('script')
    for script in scripts:
      match = re.search(r'{(\"pid\":\"pl_weibo_feedlist\".*)}', unicode(script.text), re.M | re.I)
      if match:
        search_results = pq(json.loads(match.group())['html'])
        feeds = search_results('dl.feed_list')
        for feed in feeds:
          item = ScrapyWeiboItem()
          item['html'] = tostring(feed)
          yield item




########NEW FILE########
