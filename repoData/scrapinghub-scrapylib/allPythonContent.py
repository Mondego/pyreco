__FILENAME__ = pipeline
from scrapy.exceptions import DropItem

class ConstraintsPipeline(object):

    def process_item(self, item, spider):
        try:
            for c in item.constraints:
                c(item)
        except AssertionError, e:
            raise DropItem(str(e))
        return item

########NEW FILE########
__FILENAME__ = crawlera
import warnings
from scrapy.exceptions import ScrapyDeprecationWarning
from collections import defaultdict
from w3lib.http import basic_auth_header
from scrapy import log, signals


class CrawleraMiddleware(object):

    url = 'http://proxy.crawlera.com:8010'
    maxbans = 20
    ban_code = 503
    download_timeout = 1800

    @classmethod
    def from_crawler(cls, crawler):
        o = cls()
        o.crawler = crawler
        o._bans = defaultdict(int)
        crawler.signals.connect(o.open_spider, signals.spider_opened)
        return o

    def open_spider(self, spider):
        self.enabled = self.is_enabled(spider)
        if not self.enabled:
            return

        for k in ('user', 'pass', 'url', 'maxbans', 'download_timeout'):
            v = self._get_setting_value(spider, k)
            if k == 'url' and '?noconnect' not in v:
                v += '?noconnect'
            setattr(self, k, v)

        self._proxyauth = self.get_proxyauth(spider)
        log.msg("Using crawlera at %s (user: %s)" % (self.url, self.user), spider=spider)

    def _get_setting_value(self, spider, k):
        if hasattr(spider, 'hubproxy_' + k):
            warnings.warn('hubproxy_%s attribute is deprecated, '
                          'use crawlera_%s instead.' % (k, k),
                          category=ScrapyDeprecationWarning, stacklevel=1)

        if self.crawler.settings.get('HUBPROXY_%s' % k.upper()) is not None:
            warnings.warn('HUBPROXY_%s setting is deprecated, '
                          'use CRAWLERA_%s instead.' % (k.upper(), k.upper()),
                          category=ScrapyDeprecationWarning, stacklevel=1)

        o = getattr(self, k, None)
        s = self.crawler.settings.get('CRAWLERA_' + k.upper(),
            self.crawler.settings.get('HUBPROXY_' + k.upper(), o))
        return getattr(spider, 'crawlera_' + k,
               getattr(spider, 'hubproxy_' + k, s))

    def is_enabled(self, spider):
        """Hook to enable middleware by custom rules"""
        if hasattr(spider, 'use_hubproxy'):
            warnings.warn('use_hubproxy attribute is deprecated, '
                          'use crawlera_enabled instead.',
                          category=ScrapyDeprecationWarning, stacklevel=1)

        if self.crawler.settings.get('HUBPROXY_ENABLED') is not None:
            warnings.warn('HUBPROXY_ENABLED setting is deprecated, '
                          'use CRAWLERA_ENABLED instead.',
                          category=ScrapyDeprecationWarning, stacklevel=1)

        return getattr(spider, 'crawlera_enabled', False) \
            or getattr(spider, 'use_hubproxy', False) \
            or self.crawler.settings.getbool("CRAWLERA_ENABLED") \
            or self.crawler.settings.getbool("HUBPROXY_ENABLED")

    def get_proxyauth(self, spider):
        """Hook to compute Proxy-Authorization header by custom rules"""
        return basic_auth_header(self.user, getattr(self, 'pass'))

    def process_request(self, request, spider):
        if self.enabled and 'dont_proxy' not in request.meta:
            request.meta['proxy'] = self.url
            request.meta['download_timeout'] = self.download_timeout
            request.headers['Proxy-Authorization'] = self._proxyauth

    def process_response(self, request, response, spider):
        if not self.enabled:
            return response

        if response.status == self.ban_code:
            key = request.meta.get('download_slot')
            self._bans[key] += 1
            if self._bans[key] > self.maxbans:
                self.crawler.engine.close_spider(spider, 'banned')
            else:
                after = response.headers.get('retry-after')
                if after:
                    key, slot = self._get_slot(request, spider)
                    if slot:
                        slot.delay = float(after)
        else:
            key, slot = self._get_slot(request, spider)
            if slot:
                slot.delay = 0
            self._bans[key] = 0

        return response

    def _get_slot(self, request, spider):
        key = request.meta.get('download_slot')
        return key, self.crawler.engine.downloader.slots.get(key)

########NEW FILE########
__FILENAME__ = deltafetch
import os, time

from scrapy.http import Request
from scrapy.item import BaseItem
from scrapy.utils.request import request_fingerprint
from scrapy.utils.project import data_path
from scrapy.exceptions import NotConfigured
from scrapy import log, signals

class DeltaFetch(object):
    """This is a spider middleware to ignore requests to pages containing items
    seen in previous crawls of the same spider, thus producing a "delta crawl"
    containing only new items.

    This also speeds up the crawl, by reducing the number of requests that need
    to be crawled, and processed (typically, item requests are the most cpu
    intensive).

    Supported settings:
    
    * DELTAFETCH_ENABLED - to enable (or disable) this extension
    * DELTAFETCH_DIR - directory where to store state
    * DELTAFETCH_DBM_MODULE - which DBM module to use for storage
    * DELTAFETCH_RESET - reset the state, clearing out all seen requests

    Supported spider arguments:

    * deltafetch_reset - same effect as DELTAFETCH_RESET setting

    Supported request meta keys:

    * deltafetch_key - used to define the lookup key for that request. by
      default it's the fingerprint, but it can be changed to contain an item
      id, for example. This requires support from the spider, but makes the
      extension more efficient for sites that many URLs for the same item.

    """

    def __init__(self, dir, dbmodule='anydbm', reset=False):
        self.dir = dir
        self.dbmodule = __import__(dbmodule)
        self.reset = reset

    @classmethod
    def from_crawler(cls, crawler):
        s = crawler.settings
        if not s.getbool('DELTAFETCH_ENABLED'):
            raise NotConfigured
        dir = data_path(s.get('DELTAFETCH_DIR', 'deltafetch'))
        dbmodule = s.get('DELTAFETCH_DBM_MODULE', 'anydbm')
        reset = s.getbool('DELTAFETCH_RESET')
        o = cls(dir, dbmodule, reset)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        dbpath = os.path.join(self.dir, '%s.db' % spider.name)
        reset = self.reset or getattr(spider, 'deltafetch_reset', False)
        flag = 'n' if reset else 'c'
        self.db = self.dbmodule.open(dbpath, flag)

    def spider_closed(self, spider):
        self.db.close()

    def process_spider_output(self, response, result, spider):
        for r in result:
            if isinstance(r, Request):
                key = self._get_key(r)
                if self.db.has_key(key):
                    spider.log("Ignoring already visited: %s" % r, level=log.INFO)
                    continue
            elif isinstance(r, BaseItem):
                key = self._get_key(response.request)
                self.db[key] = str(time.time())
            yield r

    def _get_key(self, request):
        return request.meta.get('deltafetch_key') or request_fingerprint(request)

########NEW FILE########
__FILENAME__ = guid
import hashlib

from scrapy import signals
from scrapy.exceptions import DropItem


def hash_values(*values):
    """Hash a series of non-None values.

    For example:
    >>> hash_values('some', 'values', 'to', 'hash')
    '1d7b7a17aeb0e5f9a6814289d12d3253'
    """
    hash = hashlib.md5()
    for value in values:
        if value is None:
            message = "hash_values was passed None at argument index %d" % list(values).index(None)
            raise ValueError(message)
        hash.update('%s' % value)
    return hash.hexdigest()


class GUIDPipeline(object):

    item_fields = {}

    def __init__(self):
        self.guids = {}

    @classmethod
    def from_crawler(cls, crawler):
        o = cls()
        crawler.signals.connect(o.spider_opened, signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signals.spider_closed)
        return o

    def spider_opened(self, spider):
        self.guids[spider] = set()

    def spider_closed(self, spider):
        del self.guids[spider]

    def process_item(self, item, spider):
        if type(item) in self.item_fields:
            item['guid'] = guid = self.generate_guid(item, spider)
            if guid is None:
                raise DropItem("Missing guid fields on: %s" % item)
            if guid in self.guids[spider]:
                raise DropItem("Duplicate item found: %s" % item)
            else:
                self.guids[spider].add(guid)
        return item

    def generate_guid(self, item, spider):
        values = []
        for field in  self.item_fields[type(item)]:
            value = item.get(field)
            if value is None:
                return
            values.append(value.encode('utf-8'))
        values.insert(0, spider.name)
        return hash_values(*values)

########NEW FILE########
__FILENAME__ = hcf
"""
HCF Middleware

This SpiderMiddleware uses the HCF backend from hubstorage to retrieve the new
urls to crawl and store back the links extracted.

To activate this middleware it needs to be added to the SPIDER_MIDDLEWARES
list, i.e:

SPIDER_MIDDLEWARES = {
    'scrapylib.hcf.HcfMiddleware': 543,
}

And the next settings need to be defined:

    HS_AUTH     - API key
    HS_PROJECTID - Project ID in the dash (not needed if the spider is ran on dash)
    HS_FRONTIER  - Frontier name.
    HS_CONSUME_FROM_SLOT - Slot from where the spider will read new URLs.

Note that HS_FRONTIER and HS_CONSUME_FROM_SLOT can be overriden from inside a spider using
the spider attributes: "hs_frontier" and "hs_consume_from_slot" respectively.

The next optional settings can be defined:

    HS_ENDPOINT - URL to the API endpoint, i.e: http://localhost:8003.
                  The default value is provided by the python-hubstorage
                  package.

    HS_MAX_LINKS - Number of links to be read from the HCF, the default is 1000.

    HS_START_JOB_ENABLED - Enable whether to start a new job when the spider
                           finishes. The default is False

    HS_START_JOB_ON_REASON - This is a list of closing reasons, if the spider ends
                             with any of these reasons a new job will be started
                             for the same slot. The default is ['finished']

    HS_NUMBER_OF_SLOTS - This is the number of slots that the middleware will
                         use to store the new links. The default is 8.

The next keys can be defined in a Request meta in order to control the behavior
of the HCF middleware:

    use_hcf - If set to True the request will be stored in the HCF.
    hcf_params - Dictionary of parameters to be stored in the HCF with the request
                 fingerprint

        qdata    data to be stored along with the fingerprint in the request queue
        fdata    data to be stored along with the fingerprint in the fingerprint set
        p    Priority - lower priority numbers are returned first. The default is 0

The value of 'qdata' parameter could be retrieved later using
``response.meta['hcf_params']['qdata']``.

The spider can override the default slot assignation function by setting the
spider slot_callback method to a function with the following signature:

   def slot_callback(request):
       ...
       return slot

"""
import os
import hashlib
import logging
from collections import defaultdict
from datetime import datetime
from scrapinghub import Connection
from scrapy import signals, log
from scrapy.exceptions import NotConfigured
from scrapy.http import Request
from hubstorage import HubstorageClient

DEFAULT_MAX_LINKS = 1000
DEFAULT_HS_NUMBER_OF_SLOTS = 8


class HcfMiddleware(object):

    def __init__(self, crawler):
        settings = crawler.settings
        self.hs_endpoint = settings.get("HS_ENDPOINT")
        self.hs_auth = self._get_config(settings, "HS_AUTH")
        self.hs_projectid = self._get_config(settings, "HS_PROJECTID", os.environ.get('SCRAPY_PROJECT_ID'))
        self.hs_frontier = self._get_config(settings, "HS_FRONTIER")
        self.hs_consume_from_slot = self._get_config(settings, "HS_CONSUME_FROM_SLOT")
        self.hs_number_of_slots = settings.getint("HS_NUMBER_OF_SLOTS", DEFAULT_HS_NUMBER_OF_SLOTS)
        self.hs_max_links = settings.getint("HS_MAX_LINKS", DEFAULT_MAX_LINKS)
        self.hs_start_job_enabled = settings.getbool("HS_START_JOB_ENABLED", False)
        self.hs_start_job_on_reason = settings.getlist("HS_START_JOB_ON_REASON", ['finished'])

        conn = Connection(self.hs_auth)
        self.panel_project = conn[self.hs_projectid]

        self.hsclient = HubstorageClient(auth=self.hs_auth, endpoint=self.hs_endpoint)
        self.project = self.hsclient.get_project(self.hs_projectid)
        self.fclient = self.project.frontier

        self.new_links = defaultdict(set)
        self.batch_ids = []

        crawler.signals.connect(self.close_spider, signals.spider_closed)

        # Make sure the logger for hubstorage.batchuploader is configured
        logging.basicConfig()

    def _get_config(self, settings, key, default=None):
        value = settings.get(key, default)
        if not value:
            raise NotConfigured('%s not found' % key)
        return value

    def _msg(self, msg, level=log.INFO):
        log.msg('(HCF) %s' % msg, level)

    def start_job(self, spider):
        self._msg("Starting new job for: %s" % spider.name)
        jobid = self.panel_project.schedule(
            spider.name,
            hs_consume_from_slot=self.hs_consume_from_slot,
            dummy=datetime.now()
        )
        self._msg("New job started: %s" % jobid)
        return jobid

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_start_requests(self, start_requests, spider):

        self.hs_frontier = getattr(spider, 'hs_frontier', self.hs_frontier)
        self._msg('Using HS_FRONTIER=%s' % self.hs_frontier)

        self.hs_consume_from_slot = getattr(spider, 'hs_consume_from_slot', self.hs_consume_from_slot)
        self._msg('Using HS_CONSUME_FROM_SLOT=%s' % self.hs_consume_from_slot)

        self.has_new_requests = False
        for req in self._get_new_requests():
            self.has_new_requests = True
            yield req

        # if there are no links in the hcf, use the start_requests
        # unless this is not the first job.
        if not self.has_new_requests and not getattr(spider, 'dummy', None):
            self._msg('Using start_requests')
            for r in start_requests:
                yield r

    def process_spider_output(self, response, result, spider):
        slot_callback = getattr(spider, 'slot_callback', self._get_slot)
        for item in result:
            if isinstance(item, Request):
                request = item
                if request.meta.get('use_hcf', False):
                    if request.method == 'GET':  # XXX: Only GET support for now.
                        slot = slot_callback(request)
                        if not request.url in self.new_links[slot]:
                            hcf_params = request.meta.get('hcf_params')
                            fp = {'fp': request.url}
                            if hcf_params:
                                fp.update(hcf_params)
                            # Save the new links as soon as possible using
                            # the batch uploader
                            self.fclient.add(self.hs_frontier, slot, [fp])
                            self.new_links[slot].add(request.url)
                    else:
                        self._msg("'use_hcf' meta key is not supported for non GET requests (%s)" % request.url,
                                  log.ERROR)
                        yield request
                else:
                    yield request
            else:
                yield item

    def close_spider(self, spider, reason):
        # Only store the results if the spider finished normally, if it
        # didn't finished properly there is not way to know whether all the url batches
        # were processed and it is better not to delete them from the frontier
        # (so they will be picked by another process).
        if reason == 'finished':
            self._save_new_links_count()
            self._delete_processed_ids()

        # Close the frontier client in order to make sure that all the new links
        # are stored.
        self.fclient.close()
        self.hsclient.close()

        # If the reason is defined in the hs_start_job_on_reason list then start
        # a new job right after this spider is finished.
        if self.hs_start_job_enabled and reason in self.hs_start_job_on_reason:

            # Start the new job if this job had requests from the HCF or it
            # was the first job.
            if self.has_new_requests or not getattr(spider, 'dummy', None):
                self.start_job(spider)

    def _get_new_requests(self):
        """ Get a new batch of links from the HCF."""
        num_batches = 0
        num_links = 0
        for num_batches, batch in enumerate(self.fclient.read(self.hs_frontier, self.hs_consume_from_slot), 1):
            for fingerprint, data in batch['requests']:
                num_links += 1
                yield Request(url=fingerprint, meta={'hcf_params': {'qdata': data}})
            self.batch_ids.append(batch['id'])
            if num_links >= self.hs_max_links:
                break
        self._msg('Read %d new batches from slot(%s)' % (num_batches, self.hs_consume_from_slot))
        self._msg('Read %d new links from slot(%s)' % (num_links, self.hs_consume_from_slot))

    def _save_new_links_count(self):
        """ Save the new extracted links into the HCF."""
        for slot, new_links in self.new_links.items():
            self._msg('Stored %d new links in slot(%s)' % (len(new_links), slot))
        self.new_links = defaultdict(set)

    def _delete_processed_ids(self):
        """ Delete in the HCF the ids of the processed batches."""
        self.fclient.delete(self.hs_frontier, self.hs_consume_from_slot, self.batch_ids)
        self._msg('Deleted %d processed batches in slot(%s)' % (len(self.batch_ids),
                                                                self.hs_consume_from_slot))
        self.batch_ids = []

    def _get_slot(self, request):
        """ Determine to which slot should be saved the request."""
        md5 = hashlib.md5()
        md5.update(request.url)
        digest = md5.hexdigest()
        return str(int(digest, 16) % self.hs_number_of_slots)

########NEW FILE########
__FILENAME__ = hubproxy
from .crawlera import CrawleraMiddleware


class HubProxyMiddleware(CrawleraMiddleware):

    def __init__(self, *args, **kwargs):
        import warnings
        from scrapy.exceptions import ScrapyDeprecationWarning
        warnings.warn('scrapylib.hubproxy.HubProxyMiddleware is deprecated, '
                      'use scrapylib.crawlera.CrawleraMiddleware instead.',
                      category=ScrapyDeprecationWarning, stacklevel=1)
        super(HubProxyMiddleware, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = links
from scrapy.http import Request

def follow_links(link_extractor, response, callback):
    """Returns a generator of requests with given `callback`
    of links extractor from `response`.

    Parameters:
        link_extractor -- LinkExtractor to use
        response -- Response to extract links from
        callback -- callback to apply to each new requests

    """
    for link in link_extractor.extract_links(response):
        yield Request(link.url, callback=callback)

########NEW FILE########
__FILENAME__ = magicfields
"""
Allow to add extra fields to items, based on the configuration setting MAGIC_FIELDS and MAGIC_FIELDS_OVERRIDE.
Both settings are a dict. The keys are the destination field names, their values, a string which admits magic variables,
identified by a starting '$', which will be substituted by a corresponding value. Some magic also accept arguments, and are specified
after the magic name, using a ':' as separator.

You can set project global magics with MAGIC_FIELDS, and tune them for a specific spider using MAGIC_FIELDS_OVERRIDE.

In case there is more than one argument, they must come separated by ','. So, the generic magic format is 

$<magic name>[:arg1,arg2,...]

Current magic variables are:
    - $time
            The UTC timestamp at which the item was scraped, in format '%Y-%m-%d %H:%M:%S'.
    - $unixtime
            The unixtime (number of seconds since the Epoch, i.e. time.time()) at which the item was scraped.
    - $isotime
            The UTC timestamp at which the item was scraped, with format '%Y-%m-%dT%H:%M:%S".
    - $spider
            Must be followed by an argument, which is the name of an attribute of the spider (like an argument passed to it).
    - $env
            The value of an environment variable. It admits as argument the name of the variable.
    - $jobid
            The job id (shortcut for $env:SCRAPY_JOB)
    - $jobtime
            The UTC timestamp at which the job started, in format '%Y-%m-%d %H:%M:%S'.
    - $response
            Access to some response properties.
                $response:url
                    The url from where the item was extracted from.
                $response:status
                    Response http status.
                $response:headers
                    Response http headers.
    - $setting
            Access the given Scrapy setting. It accepts one argument: the name of the setting.
    - $field
            Allows to copy the value of one field to another. Its argument is the source field. Effects are unpredicable if you use as source a field that is filled
            using magic fields.

Examples:

The following configuration will add two fields to each scraped item: 'timestamp', which will be filled with the string 'item scraped at <scraped timestamp>',
and 'spider', which will contain the spider name:

MAGIC_FIELDS = {"timestamp": "item scraped at $time", "spider": "$spider:name"}

The following configuration will copy the url to the field sku:

MAGIC_FIELDS = {"sku": "$field:url"}

Magics admits also regular expression argument which allow to extract and assign only part of the value generated by the magic. You have to specify
it using the r'' notation. Suppose that the urls of your items are like 'http://www.example.com/product.html?item_no=345' and you want to assign to the sku field
only the item number. The following example, similar to the previous one but with a second regular expression argument, will do the task:

MAGIC_FIELDS = {"sku": "$field:url,r'item_no=(\d+)'"}

"""

import re, time, datetime, os

from scrapy.exceptions import NotConfigured
from scrapy.item import BaseItem

def _time():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def _isotime():
    return datetime.datetime.utcnow().isoformat()

_REGEXES = {}
_REGEX_ERRORS = {}
def _extract_regex_group(regex, txt):
    compiled = _REGEXES.get(regex)
    errmessage = _REGEX_ERRORS.get(regex)
    if compiled is None and errmessage is None:
        try:
            compiled = re.compile(regex)
            _REGEXES[regex] = compiled
        except Exception, e:
            errmessage = e.message
            _REGEX_ERRORS[regex] = errmessage
    if errmessage:
        raise ValueError(errmessage)
    m = compiled.search(txt)
    if m:
        return "".join(m.groups()) or None

_ENTITY_FUNCTION_MAP = {
    '$time': _time,
    '$unixtime': time.time,
    '$isotime': _isotime,
}

_ENTITIES_RE = re.compile("(\$[a-z]+)(:\w+)?(?:,r\'(.+)\')?")
def _first_arg(args):
    if args:
        return args.pop(0)

def _format(fmt, spider, response, item, fixed_values):
    out = fmt
    for m in _ENTITIES_RE.finditer(fmt):
        val = None
        entity, args, regex = m.groups()
        args = filter(None, (args or ':')[1:].split(','))
        if entity == "$jobid":
            val = os.environ.get('SCRAPY_JOB', '')
        elif entity == "$spider":
            attr = _first_arg(args)
            if not attr or not hasattr(spider, attr):
                spider.log("Error at '%s': spider does not have attribute" % m.group())
            else:
                val = str(getattr(spider, attr))
        elif entity == "$response":
            attr = _first_arg(args)
            if not attr or not hasattr(response, attr):
                spider.log("Error at '%s': response does not have attribute" % m.group())
            else:
                val = str(getattr(response, attr))
        elif entity == "$field":
            attr = _first_arg(args)
            if attr in item:
                val = str(item[attr])
        elif entity in fixed_values:
            attr = _first_arg(args)
            val = fixed_values[entity]
            if entity == "$setting" and attr:
                val = str(val[attr])
        elif entity == "$env" and args:
            attr = _first_arg(args)
            if attr:
                val = os.environ.get(attr, '')
        else:
            function = _ENTITY_FUNCTION_MAP.get(entity)
            if function is not None:
                try:
                    val = str(function(*args))
                except:
                    spider.log("Error at '%s': invalid argument for function" % m.group())
        if val is not None:
            out = out.replace(m.group(), val, 1)
        if regex:
            try:
                out = _extract_regex_group(regex, out)
            except ValueError, e:
                spider.log("Error at '%s': %s" % (m.group(), e.message))

    return out

class MagicFieldsMiddleware(object):
    
    @classmethod
    def from_crawler(cls, crawler):
        mfields = crawler.settings.getdict("MAGIC_FIELDS").copy()
        mfields.update(crawler.settings.getdict("MAGIC_FIELDS_OVERRIDE"))
        if not mfields:
            raise NotConfigured
        return cls(mfields, crawler.settings)

    def __init__(self, mfields, settings):
        self.mfields = mfields
        self.fixed_values = {
            "$jobtime": _time(),
            "$setting": settings,
        }

    def process_spider_output(self, response, result, spider):
        for _res in result:
            if isinstance(_res, BaseItem):
                for field, fmt in self.mfields.items():
                    _res.setdefault(field, _format(fmt, spider, response, _res, self.fixed_values))
            yield _res 


########NEW FILE########
__FILENAME__ = pipelines

class SpiderFieldPipeline(object):
    def process_item(self, item, spider):
        item['spider'] = spider.name
        return item

########NEW FILE########
__FILENAME__ = date
from dateutil.parser import parse
from scrapy.contrib.loader.processor import Compose
from scrapy import log
from scrapylib.processors import default_output_processor

def parse_datetime(value):
    try:
        d = parse(value)
    except ValueError:
        log.msg('Unable to parse %s' % value, level=log.WARNING)
        return value
    else:
        return d.isoformat()

def parse_date(value):
    try:
        d = parse(value)
    except ValueError:
        log.msg('Unable to parse %s' % value, level=log.WARNING)
        return value
    else:
        return d.strftime("%Y-%m-%d")

default_out_parse_datetime = Compose(default_output_processor, parse_datetime)
default_out_parse_date = Compose(default_output_processor, parse_date)

########NEW FILE########
__FILENAME__ = proxy
import base64
from urllib import unquote
from urllib2 import _parse_proxy
from urlparse import urlunparse


class SelectiveProxyMiddleware(object):
    """A middleware to enable http proxy to selected spiders only.

    Settings:
        HTTP_PROXY -- proxy uri. e.g.: http://user:pass@proxy.host:port
        PROXY_SPIDERS -- all requests from these spiders will be routed
                         through the proxy
    """

    def __init__(self, settings):
        self.proxy = self.parse_proxy(settings.get('HTTP_PROXY'), 'http')
        self.proxy_spiders = set(settings.getlist('PROXY_SPIDERS', []))

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def parse_proxy(self, url, orig_type):
        proxy_type, user, password, hostport = _parse_proxy(url)
        proxy_url = urlunparse((proxy_type or orig_type, hostport, '', '', '', ''))

        if user and password:
            user_pass = '%s:%s' % (unquote(user), unquote(password))
            creds = base64.b64encode(user_pass).strip()
        else:
            creds = None

        return creds, proxy_url

    def process_request(self, request, spider):
        if spider.name in self.proxy_spiders:
            creds, proxy = self.proxy
            request.meta['proxy'] = proxy
            if creds:
                request.headers['Proxy-Authorization'] = 'Basic ' + creds

########NEW FILE########
__FILENAME__ = querycleaner
"""Get parameter cleaner for AS.

Add removed/kept pattern (regex) with

QUERYCLEANER_REMOVE
QUERYCLEANER_KEEP

Remove patterns has precedence.
"""
import re
from urllib import quote

from scrapy.utils.httpobj import urlparse_cached
from scrapy.http import Request
from scrapy.exceptions import NotConfigured

from w3lib.url import _safe_chars

def _parse_query_string(query):
    """Used for replacing cgi.parse_qsl.
    The cgi version returns the same pair for query 'key'
    and query 'key=', so reconstruction
    maps to the same string. But some sites does not handle both versions
    in the same way.
    This version returns (key, None) in the first case, and (key, '') in the
    second one, so correct reconstruction can be performed."""

    params = query.split("&")
    keyvals = []
    for param in params:
        kv = param.split("=") + [None]
        keyvals.append((kv[0], kv[1]))
    return keyvals

def _filter_query(query, remove_re=None, keep_re=None):
    """
    Filters query parameters in a query string according to key patterns
    >>> _filter_query('as=3&bs=8&cs=9')
    'as=3&bs=8&cs=9'
    >>> _filter_query('as=3&bs=8&cs=9', None, re.compile("as|bs"))
    'as=3&bs=8'
    >>> _filter_query('as=3&bs=8&cs=9', re.compile("as|bs"))
    'cs=9'
    >>> _filter_query('as=3&bs=8&cs=9', re.compile("as|bs"), re.compile("as|cs"))
    'cs=9'
    """
    keyvals = _parse_query_string(query)
    qargs = []
    for k, v in keyvals:
        if remove_re is not None and remove_re.search(k):
            continue
        if keep_re is None or keep_re.search(k):
            qarg = quote(k, _safe_chars)
            if isinstance(v, basestring):
                qarg = qarg + '=' + quote(v, _safe_chars)
            qargs.append(qarg.replace("%20", "+"))
    return '&'.join(qargs)

class QueryCleanerMiddleware(object):
    def __init__(self, settings):
        remove = settings.get("QUERYCLEANER_REMOVE")
        keep = settings.get("QUERYCLEANER_KEEP")
        if not (remove or keep):
            raise NotConfigured
        self.remove = re.compile(remove) if remove else None
        self.keep = re.compile(keep) if keep else None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_spider_output(self, response, result, spider):
        for res in result:
            if isinstance(res, Request):
                parsed = urlparse_cached(res)
                if parsed.query:
                    parsed = parsed._replace(query=_filter_query(parsed.query, self.remove, self.keep))
                    res = res.replace(url=parsed.geturl())
            yield res


########NEW FILE########
__FILENAME__ = redisqueue
try:
    import cPickle as pickle
except ImportError:
    import pickle

from scrapy.exceptions import NotConfigured
from scrapy import signals


class RedisQueue(object):

    def __init__(self, crawler):
        try:
            from redis import Redis
        except ImportError:
            raise NotConfigured

        settings = crawler.settings

        # get settings
        queue = settings.get('REDIS_QUEUE')
        if queue is None:
            raise NotConfigured

        host = settings.get('REDIS_HOST', 'localhost')
        port = settings.getint('REDIS_PORT', 6379)
        db = settings.getint('REDIS_DB', 0)
        password = settings.get('REDIS_PASSWORD')

        self.redis = Redis(host=host, port=port, db=db, password=password)
        self.queue = queue
        self.project = settings['BOT_NAME']

        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def spider_closed(self, spider, reason):
        msg = {'project': self.project, 'spider': spider.name, 'reason': reason}
        self.redis.rpush(self.queue, pickle.dumps(msg))

########NEW FILE########
__FILENAME__ = spidertrace
"""
Spider Trace 

This SpiderMiddleware logs a trace of requests and items extracted for a
spider
"""
import os
from os.path import basename
from tempfile import mkstemp
from gzip import GzipFile
import time
import boto
import json
from boto.s3.key import Key
from scrapy import signals, log
from scrapy.exceptions import NotConfigured
from scrapy.http import Request
from scrapy.utils.request import request_fingerprint


class SpiderTraceMiddleware(object):
    """Saves a trace of spider execution and uploads to S3

    The trace records:
        (timestamp, http response, results extracted from spider)
    """
    REQUEST_ATTRS = ('url', 'method', 'body', 'headers', 'cookies', 'meta')
    RESPONSE_ATTRS = ('url', 'status', 'headers', 'body', 'request', 'flags')

    def __init__(self, crawler):
        self.bucket = crawler.settings.get("SPIDERTRACE_BUCKET")
        if not self.bucket:
            raise NotConfigured
        crawler.signals.connect(self.open_spider, signals.spider_opened)
        crawler.signals.connect(self.close_spider, signals.spider_closed)
        self.outputs = {}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_spider_output(self, response, result, spider):
        f = self.outputs[spider]
        fp = request_fingerprint(response.request)
        tracetime = time.time()
        data = self._objtodict(self.RESPONSE_ATTRS, response)
        data['request'] = self._objtodict(self.REQUEST_ATTRS, response.request)
        self._write(f, fp, tracetime, 'response', data)

        for item in result:
            if isinstance(item, Request):
                data = self._objtodict(self.REQUEST_ATTRS, item)
                data['fp'] = request_fingerprint(item)
                self._write(f, fp, tracetime, 'request', data)
            else:
                self._write(f, fp, tracetime, 'item', dict(item))
            yield item

    @staticmethod
    def _write(f, fp, tracetime, otype, data):
        f.write('%s\t%s\t%s\t%s\n' % (tracetime, fp, otype, json.dumps(data)))

    @staticmethod
    def _objtodict(attrs, obj):
        data = [(a, getattr(obj, a)) for a in attrs]
        return dict(x for x in data if x[1])

    def open_spider(self, spider):
        _, fname = mkstemp(prefix=spider.name + '-', suffix='.trace.gz')
        self.outputs[spider] = GzipFile(fname, 'wb')

    def close_spider(self, spider):
        f = self.outputs.pop(spider)
        f.close()
        c = boto.connect_s3()
        fname = basename(f.name)
        key = Key(c.get_bucket(self.bucket), fname)
        log.msg("uploading trace to s3://%s/%s" % (key.bucket.name, fname))
        key.set_contents_from_filename(f.name)
        os.remove(f.name)

########NEW FILE########
__FILENAME__ = test_constraints
import unittest
from scrapylib.constraints import RequiredFields, IsType, IsNumber, IsPrice, MaxLen, MinLen


class RequiredFieldsTest(unittest.TestCase):

    def setUp(self):
        self.item = {'str': 'bar', 'list': ['one']}

    def test_basic(self):
        RequiredFields('str')(self.item)
        RequiredFields('str', 'list')(self.item)

    def test_fail(self):
        self.assertRaises(AssertionError, RequiredFields('list', 'xxx'), self.item)

class IsTypeTest(unittest.TestCase):

    def setUp(self):
        self.item = {'str': 'bar', 'list': ['one']}

    def test_ok(self):
        IsType(basestring, 'str')(self.item)
        IsType(list, 'list')(self.item)
        IsType(list, 'missing')(self.item)

    def test_fail(self):
        self.assertRaises(AssertionError, IsType(basestring, 'list'), self.item)
        self.assertRaises(AssertionError, IsType(list, 'str'), self.item)

class IsNumberTest(unittest.TestCase):

    def setUp(self):
        self.item = {'name': 'foo', 'age': '23'}

    def test_ok(self):
        IsNumber('age')(self.item)
        IsNumber('xxx')(self.item)

    def test_fail(self):
        self.assertRaises(AssertionError, IsNumber('name'), self.item)

class IsPriceTest(unittest.TestCase):

    def setUp(self):
        self.item = {'name': 'foo', 'price': '1,223.23 '}

    def test_basic(self):
        IsPrice('price')(self.item)
        IsPrice('xxx')(self.item)

    def test_fail(self):
        self.assertRaises(AssertionError, IsPrice('name'), self.item)

class MaxLenTest(unittest.TestCase):

    def setUp(self):
        self.item = {'name': 'foo', 'other': 'very long content'}

    def test_ok(self):
        MaxLen(8, 'name')(self.item)
        MaxLen(8, 'xxx')(self.item)

    def test_fail(self):
        self.assertRaises(AssertionError, MaxLen(8, 'other'), self.item)

class MinLenTest(MaxLenTest):

    def test_ok(self):
        MinLen(8, 'other')(self.item)
        MinLen(8, 'xxx')(self.item)

    def test_fail(self):
        self.assertRaises(AssertionError, MinLen(8, 'name'), self.item)

########NEW FILE########
__FILENAME__ = test_crawlera
from unittest import TestCase

from w3lib.http import basic_auth_header
from scrapy.http import Request, Response
from scrapy.spider import BaseSpider
from scrapy.utils.test import get_crawler
from scrapylib.crawlera import CrawleraMiddleware


class CrawleraMiddlewareTestCase(TestCase):

    mwcls = CrawleraMiddleware

    def setUp(self):
        self.spider = BaseSpider('foo')
        self.settings = {'CRAWLERA_USER': 'user', 'CRAWLERA_PASS': 'pass'}

    def _mock_crawler(self, settings=None):
        class MockedDownloader(object):
            slots = {}

        class MockedEngine(object):
            downloader = MockedDownloader()
            fake_spider_closed_result = None

            def close_spider(self, spider, reason):
                self.fake_spider_closed_result = (spider, reason)

        crawler = get_crawler(settings)
        crawler.engine = MockedEngine()
        return crawler

    def _assert_disabled(self, spider, settings=None):
        crawler = self._mock_crawler(settings)
        mw = self.mwcls.from_crawler(crawler)
        mw.open_spider(spider)
        req = Request('http://www.scrapytest.org')
        out = mw.process_request(req, spider)
        self.assertEqual(out, None)
        self.assertEqual(req.meta.get('proxy'), None)
        self.assertEqual(req.meta.get('download_timeout'), None)
        self.assertEqual(req.headers.get('Proxy-Authorization'), None)
        res = Response(req.url)
        assert mw.process_response(req, res, spider) is res
        res = Response(req.url, status=mw.ban_code)
        assert mw.process_response(req, res, spider) is res

    def _assert_enabled(self, spider,
                        settings=None,
                        proxyurl='http://proxy.crawlera.com:8010?noconnect',
                        proxyauth=basic_auth_header('user', 'pass'),
                        bancode=503,
                        maxbans=20,
                        download_timeout=1800):
        crawler = self._mock_crawler(settings)
        mw = self.mwcls.from_crawler(crawler)
        mw.open_spider(spider)
        req = Request('http://www.scrapytest.org')
        assert mw.process_request(req, spider) is None
        self.assertEqual(req.meta.get('proxy'), proxyurl)
        self.assertEqual(req.meta.get('download_timeout'), download_timeout)
        self.assertEqual(req.headers.get('Proxy-Authorization'), proxyauth)
        res = Response(req.url)
        assert mw.process_response(req, res, spider) is res

        # disabled if 'dont_proxy' is set
        req = Request('http://www.scrapytest.org')
        req.meta['dont_proxy'] = True
        assert mw.process_request(req, spider) is None
        self.assertEqual(req.meta.get('proxy'), None)
        self.assertEqual(req.meta.get('download_timeout'), None)
        self.assertEqual(req.headers.get('Proxy-Authorization'), None)
        res = Response(req.url)
        assert mw.process_response(req, res, spider) is res

        if maxbans > 0:
            # assert ban count is reseted after a succesful response
            res = Response('http://ban.me', status=bancode)
            assert mw.process_response(req, res, spider) is res
            self.assertEqual(crawler.engine.fake_spider_closed_result, None)
            res = Response('http://unban.me')
            assert mw.process_response(req, res, spider) is res
            self.assertEqual(crawler.engine.fake_spider_closed_result, None)
            self.assertEqual(mw._bans[None], 0)

        # check for not banning before maxbans for bancode
        for x in xrange(maxbans + 1):
            self.assertEqual(crawler.engine.fake_spider_closed_result, None)
            res = Response('http://ban.me/%d' % x, status=bancode)
            assert mw.process_response(req, res, spider) is res

        # max bans reached and close_spider called
        self.assertEqual(crawler.engine.fake_spider_closed_result, (spider, 'banned'))

    def test_disabled_by_lack_of_crawlera_settings(self):
        self._assert_disabled(self.spider, settings={})

    def test_spider_crawlera_enabled(self):
        self.assertFalse(hasattr(self.spider, 'crawlera_enabled'))
        self._assert_disabled(self.spider, self.settings)
        self.spider.crawlera_enabled = True
        self._assert_enabled(self.spider, self.settings)
        self.spider.crawlera_enabled = False
        self._assert_disabled(self.spider, self.settings)

    def test_enabled(self):
        self._assert_disabled(self.spider, self.settings)
        self.settings['CRAWLERA_ENABLED'] = True
        self._assert_enabled(self.spider, self.settings)

    def test_userpass(self):
        self.spider.crawlera_enabled = True
        self.settings['CRAWLERA_USER'] = user = 'other'
        self.settings['CRAWLERA_PASS'] = pass_ = 'secret'
        proxyauth = basic_auth_header(user, pass_)
        self._assert_enabled(self.spider, self.settings, proxyauth=proxyauth)

        self.spider.crawlera_user = user = 'notfromsettings'
        self.spider.crawlera_pass = pass_ = 'anothersecret'
        proxyauth = basic_auth_header(user, pass_)
        self._assert_enabled(self.spider, self.settings, proxyauth=proxyauth)

    def test_proxyurl(self):
        self.spider.crawlera_enabled = True
        self.settings['CRAWLERA_URL'] = 'http://localhost:8010'
        self._assert_enabled(self.spider, self.settings, proxyurl='http://localhost:8010?noconnect')

    def test_proxyurl_including_noconnect(self):
        self.spider.crawlera_enabled = True
        self.settings['CRAWLERA_URL'] = 'http://localhost:8010?noconnect'
        self._assert_enabled(self.spider, self.settings, proxyurl='http://localhost:8010?noconnect')

    def test_maxbans(self):
        self.spider.crawlera_enabled = True
        self.settings['CRAWLERA_MAXBANS'] = maxbans = 0
        self._assert_enabled(self.spider, self.settings, maxbans=maxbans)
        self.settings['CRAWLERA_MAXBANS'] = maxbans = 100
        self._assert_enabled(self.spider, self.settings, maxbans=maxbans)

    def test_download_timeout(self):
        self.spider.crawlera_enabled = True
        self.settings['CRAWLERA_DOWNLOAD_TIMEOUT'] = 60
        self._assert_enabled(self.spider, self.settings, download_timeout=60)
        self.spider.crawlera_download_timeout = 120
        self._assert_enabled(self.spider, self.settings, download_timeout=120)

    def test_hooks(self):
        class _ECLS(self.mwcls):
            def is_enabled(self, spider):
                wascalled.append('is_enabled')
                return enabled

            def get_proxyauth(self, spider):
                wascalled.append('get_proxyauth')
                return proxyauth

        wascalled = []
        self.mwcls = _ECLS

        # test is_enabled returns False
        enabled = False
        self.spider.crawlera_enabled = True
        self._assert_disabled(self.spider, self.settings)
        self.assertEqual(wascalled, ['is_enabled'])

        wascalled[:] = []  # reset
        enabled = True
        self.spider.crawlera_enabled = False
        proxyauth = 'Basic Foo'
        self._assert_enabled(self.spider, self.settings, proxyauth=proxyauth)
        self.assertEqual(wascalled, ['is_enabled', 'get_proxyauth'])

########NEW FILE########
__FILENAME__ = test_hcf
import os
import hashlib
import unittest

from scrapy.http import Request, Response
from scrapy.spider import BaseSpider
from scrapy.utils.test import get_crawler
from scrapylib.hcf import HcfMiddleware
from scrapy.exceptions import NotConfigured, DontCloseSpider
from hubstorage import HubstorageClient

HS_ENDPOINT = os.getenv('HS_ENDPOINT', 'http://localhost:8003')
HS_AUTH = os.getenv('HS_AUTH')

@unittest.skipUnless(HS_AUTH, 'No valid hubstorage credentials set')
class HcfTestCase(unittest.TestCase):

    hcf_cls = HcfMiddleware

    projectid = '2222222'
    spidername = 'hs-test-spider'
    frontier = 'test'
    slot = '0'
    number_of_slots = 1

    @classmethod
    def setUpClass(cls):
        cls.endpoint = HS_ENDPOINT
        cls.auth = HS_AUTH
        cls.hsclient = HubstorageClient(auth=cls.auth, endpoint=cls.endpoint)
        cls.project = cls.hsclient.get_project(cls.projectid)
        cls.fclient = cls.project.frontier

    @classmethod
    def tearDownClass(cls):
        cls.project.frontier.close()
        cls.hsclient.close()

    def setUp(self):
        class TestSpider(BaseSpider):
            name = self.spidername
            start_urls = [
                'http://www.example.com/'
            ]

        self.spider = TestSpider()
        self.hcf_settings = {'HS_ENDPOINT': self.endpoint,
                             'HS_AUTH': self.auth,
                             'HS_PROJECTID': self.projectid,
                             'HS_FRONTIER': self.frontier,
                             'HS_CONSUME_FROM_SLOT': self.slot,
                             'HS_NUMBER_OF_SLOTS': self.number_of_slots}
        self._delete_slot()

    def tearDown(self):
        self._delete_slot()

    def _delete_slot(self):
        self.fclient.delete_slot(self.frontier, self.slot)

    def _build_response(self, url, meta=None):
        return Response(url, request=Request(url="http://www.example.com/parent.html", meta=meta))

    def _get_crawler(self, settings=None):
        crawler = get_crawler(settings)
        # simulate crawler engine
        class Engine():
            def __init__(self):
                self.requests = []
            def schedule(self, request, spider):
                self.requests.append(request)
        crawler.engine = Engine()

        return crawler

    def test_not_loaded(self):
        crawler = self._get_crawler({})
        self.assertRaises(NotConfigured, self.hcf_cls.from_crawler, crawler)

    def test_start_requests(self):
        crawler = self._get_crawler(self.hcf_settings)
        hcf = self.hcf_cls.from_crawler(crawler)

        # first time should be empty
        start_urls = self.spider.start_urls
        new_urls = list(hcf.process_start_requests(start_urls, self.spider))
        self.assertEqual(new_urls, ['http://www.example.com/'])

        # now try to store some URLs in the hcf and retrieve them
        fps = [{'fp': 'http://www.example.com/index.html'},
               {'fp': 'http://www.example.com/index2.html'}]
        self.fclient.add(self.frontier, self.slot, fps)
        self.fclient.flush()
        new_urls = [r.url for r in hcf.process_start_requests(start_urls, self.spider)]
        expected_urls = [r['fp'] for r in fps]
        self.assertEqual(new_urls, expected_urls)
        self.assertEqual(len(hcf.batch_ids), 1)

    def test_spider_output(self):
        crawler = self._get_crawler(self.hcf_settings)
        hcf = self.hcf_cls.from_crawler(crawler)

        # process new GET request
        response = self._build_response("http://www.example.com/qxg1231")
        request = Request(url="http://www.example.com/product/?qxp=12&qxg=1231", meta={'use_hcf': True})
        outputs = list(hcf.process_spider_output(response, [request], self.spider))
        self.assertEqual(outputs, [])
        expected_links = {'0': set(['http://www.example.com/product/?qxp=12&qxg=1231'])}
        self.assertEqual(dict(hcf.new_links), expected_links)

        # process new POST request (don't add it to the hcf)
        response = self._build_response("http://www.example.com/qxg456")
        request = Request(url="http://www.example.com/product/?qxp=456", method='POST')
        outputs = list(hcf.process_spider_output(response, [request], self.spider))
        self.assertEqual(outputs, [request])
        expected_links = {'0': set(['http://www.example.com/product/?qxp=12&qxg=1231'])}
        self.assertEqual(dict(hcf.new_links), expected_links)

        # process new GET request (without the use_hcf meta key)
        response = self._build_response("http://www.example.com/qxg1231")
        request = Request(url="http://www.example.com/product/?qxp=789")
        outputs = list(hcf.process_spider_output(response, [request], self.spider))
        self.assertEqual(outputs, [request])
        expected_links = {'0': set(['http://www.example.com/product/?qxp=12&qxg=1231'])}
        self.assertEqual(dict(hcf.new_links), expected_links)

        # Simulate close spider
        hcf.close_spider(self.spider, 'finished')

    def test_close_spider(self):
        crawler = self._get_crawler(self.hcf_settings)
        hcf = self.hcf_cls.from_crawler(crawler)

        # Save 2 batches in the HCF
        fps = [{'fp': 'http://www.example.com/index_%s.html' % i} for i in range(0, 200)]
        self.fclient.add(self.frontier, self.slot, fps)
        self.fclient.flush()

        # Read the first batch
        start_urls = self.spider.start_urls
        new_urls = [r.url for r in hcf.process_start_requests(start_urls, self.spider)]
        expected_urls = [r['fp'] for r in fps]
        self.assertEqual(new_urls, expected_urls)

        # Simulate extracting some new urls
        response = self._build_response("http://www.example.com/parent.html")
        new_fps = ["http://www.example.com/child_%s.html" % i for i in range(0, 50)]
        for fp in new_fps:
            request = Request(url=fp, meta={'use_hcf': True})
            list(hcf.process_spider_output(response, [request], self.spider))
        self.assertEqual(len(hcf.new_links[self.slot]), 50)

        # Simulate emptying the scheduler
        crawler.engine.requests = []

        # Simulate close spider
        hcf.close_spider(self.spider, 'finished')
        self.assertEqual(len(hcf.new_links[self.slot]), 0)
        self.assertEqual(len(hcf.batch_ids), 0)

        # HCF must be have 1 new batch
        batches = [b for b in self.fclient.read(self.frontier, self.slot)]
        self.assertEqual(len(batches), 1)

    def test_hcf_params(self):
        crawler = self._get_crawler(self.hcf_settings)
        hcf = self.hcf_cls.from_crawler(crawler)

        # Simulate extracting some new urls and adding them to the HCF
        response = self._build_response("http://www.example.com/parent.html")
        new_fps = ["http://www.example.com/child_%s.html" % i for i in range(0, 5)]
        new_requests = []
        for fp in new_fps:
            hcf_params = {'qdata': {'a': '1', 'b': '2', 'c': '3'},
                          'fdata': {'x': '1', 'y': '2', 'z': '3'},
                          'p': 1}
            request = Request(url=fp, meta={'use_hcf': True, "hcf_params": hcf_params})
            new_requests.append(request)
            list(hcf.process_spider_output(response, [request], self.spider))
        expected = set(['http://www.example.com/child_4.html',
                        'http://www.example.com/child_1.html',
                        'http://www.example.com/child_0.html',
                        'http://www.example.com/child_3.html',
                        'http://www.example.com/child_2.html'])
        self.assertEqual(hcf.new_links[self.slot], expected)

        # Simulate close spider
        hcf.close_spider(self.spider, 'finished')

        # Similate running another spider
        start_urls = self.spider.start_urls
        stored_requests = list(hcf.process_start_requests(start_urls, self.spider))
        for a, b in zip(new_requests, stored_requests):
            self.assertEqual(a.url, b.url)
            self.assertEqual(a.meta.get('qdata'), b.meta.get('qdata'))

        # Simulate emptying the scheduler
        crawler.engine.requests = []

        # Simulate close spider
        hcf.close_spider(self.spider, 'finished')

    def test_spider_output_override_slot(self):
        crawler = self._get_crawler(self.hcf_settings)
        hcf = self.hcf_cls.from_crawler(crawler)

        def get_slot_callback(request):
            md5 = hashlib.md5()
            md5.update(request.url)
            digest = md5.hexdigest()
            return str(int(digest, 16) % 5)
        self.spider.slot_callback = get_slot_callback

        # process new GET request
        response = self._build_response("http://www.example.com/qxg1231")
        request = Request(url="http://www.example.com/product/?qxp=12&qxg=1231",
                          meta={'use_hcf': True})
        outputs = list(hcf.process_spider_output(response, [request], self.spider))
        self.assertEqual(outputs, [])
        expected_links = {'4': set(['http://www.example.com/product/?qxp=12&qxg=1231'])}
        self.assertEqual(dict(hcf.new_links), expected_links)

        # Simulate close spider
        hcf.close_spider(self.spider, 'finished')


########NEW FILE########
__FILENAME__ = test_hubproxy
from unittest import TestCase

from w3lib.http import basic_auth_header
from scrapy.http import Request, Response
from scrapy.spider import BaseSpider
from scrapy.utils.test import get_crawler
from scrapylib.hubproxy import HubProxyMiddleware


class HubProxyMiddlewareTestCase(TestCase):

    mwcls = HubProxyMiddleware

    def setUp(self):
        self.spider = BaseSpider('foo')
        self.settings = {'HUBPROXY_USER': 'user', 'HUBPROXY_PASS': 'pass'}

    def _mock_crawler(self, settings=None):
        class MockedDownloader(object):
            slots = {}

        class MockedEngine(object):
            downloader = MockedDownloader()
            fake_spider_closed_result = None
            def close_spider(self, spider, reason):
                self.fake_spider_closed_result = (spider, reason)

        crawler = get_crawler(settings)
        crawler.engine = MockedEngine()
        return crawler

    def _assert_disabled(self, spider, settings=None):
        crawler = self._mock_crawler(settings)
        mw = self.mwcls.from_crawler(crawler)
        mw.open_spider(spider)
        req = Request('http://www.scrapytest.org')
        out = mw.process_request(req, spider)
        self.assertEqual(out, None)
        self.assertEqual(req.meta.get('proxy'), None)
        self.assertEqual(req.meta.get('download_timeout'), None)
        self.assertEqual(req.headers.get('Proxy-Authorization'), None)
        res = Response(req.url)
        assert mw.process_response(req, res, spider) is res
        res = Response(req.url, status=mw.ban_code)
        assert mw.process_response(req, res, spider) is res

    def _assert_enabled(self, spider,
                        settings=None,
                        proxyurl='http://proxy.crawlera.com:8010?noconnect',
                        proxyauth=basic_auth_header('user', 'pass'),
                        bancode=503,
                        maxbans=20,
                        download_timeout=1800,
                       ):
        crawler = self._mock_crawler(settings)
        mw = self.mwcls.from_crawler(crawler)
        mw.open_spider(spider)
        req = Request('http://www.scrapytest.org')
        assert mw.process_request(req, spider) is None
        self.assertEqual(req.meta.get('proxy'), proxyurl)
        self.assertEqual(req.meta.get('download_timeout'), download_timeout)
        self.assertEqual(req.headers.get('Proxy-Authorization'), proxyauth)
        res = Response(req.url)
        assert mw.process_response(req, res, spider) is res

        # disabled if 'dont_proxy' is set
        req = Request('http://www.scrapytest.org')
        req.meta['dont_proxy'] = True
        assert mw.process_request(req, spider) is None
        self.assertEqual(req.meta.get('proxy'), None)
        self.assertEqual(req.meta.get('download_timeout'), None)
        self.assertEqual(req.headers.get('Proxy-Authorization'), None)
        res = Response(req.url)
        assert mw.process_response(req, res, spider) is res

        if maxbans > 0:
            # assert ban count is reseted after a succesful response
            res = Response('http://ban.me', status=bancode)
            assert mw.process_response(req, res, spider) is res
            self.assertEqual(crawler.engine.fake_spider_closed_result, None)
            res = Response('http://unban.me')
            assert mw.process_response(req, res, spider) is res
            self.assertEqual(crawler.engine.fake_spider_closed_result, None)
            self.assertEqual(mw._bans[None], 0)

        # check for not banning before maxbans for bancode
        for x in xrange(maxbans + 1):
            self.assertEqual(crawler.engine.fake_spider_closed_result, None)
            res = Response('http://ban.me/%d' % x, status=bancode)
            assert mw.process_response(req, res, spider) is res

        # max bans reached and close_spider called
        self.assertEqual(crawler.engine.fake_spider_closed_result, (spider, 'banned'))

    def test_disabled_by_lack_of_hubproxy_settings(self):
        self._assert_disabled(self.spider, settings={})

    def test_spider_use_hubproxy(self):
        self.assertFalse(hasattr(self.spider, 'use_hubproxy'))
        self._assert_disabled(self.spider, self.settings)
        self.spider.use_hubproxy = True
        self._assert_enabled(self.spider, self.settings)
        self.spider.use_hubproxy = False
        self._assert_disabled(self.spider, self.settings)

    def test_enabled(self):
        self._assert_disabled(self.spider, self.settings)
        self.settings['HUBPROXY_ENABLED'] = True
        self._assert_enabled(self.spider, self.settings)

    def test_userpass(self):
        self.spider.use_hubproxy = True
        self.settings['HUBPROXY_USER'] = user = 'other'
        self.settings['HUBPROXY_PASS'] = pass_ = 'secret'
        proxyauth = basic_auth_header(user, pass_)
        self._assert_enabled(self.spider, self.settings, proxyauth=proxyauth)

        self.spider.hubproxy_user = user = 'notfromsettings'
        self.spider.hubproxy_pass = pass_ = 'anothersecret'
        proxyauth = basic_auth_header(user, pass_)
        self._assert_enabled(self.spider, self.settings, proxyauth=proxyauth)

    def test_proxyurl(self):
        self.spider.use_hubproxy = True
        self.settings['HUBPROXY_URL'] = 'http://localhost:8010'
        self._assert_enabled(self.spider, self.settings, proxyurl='http://localhost:8010?noconnect')

    def test_maxbans(self):
        self.spider.use_hubproxy = True
        self.settings['HUBPROXY_MAXBANS'] = maxbans = 0
        self._assert_enabled(self.spider, self.settings, maxbans=maxbans)
        self.settings['HUBPROXY_MAXBANS'] = maxbans = 100
        self._assert_enabled(self.spider, self.settings, maxbans=maxbans)

    def test_download_timeout(self):
        self.spider.use_hubproxy = True
        self.settings['HUBPROXY_DOWNLOAD_TIMEOUT'] = 60
        self._assert_enabled(self.spider, self.settings, download_timeout=60)
        self.spider.hubproxy_download_timeout = 120
        self._assert_enabled(self.spider, self.settings, download_timeout=120)

    def test_hooks(self):
        class _ECLS(self.mwcls):
            def is_enabled(self, spider):
                wascalled.append('is_enabled')
                return enabled
            def get_proxyauth(self, spider):
                wascalled.append('get_proxyauth')
                return proxyauth

        wascalled = []
        self.mwcls = _ECLS

        # test is_enabled returns False
        enabled = False
        self.spider.use_hubproxy = True
        self._assert_disabled(self.spider, self.settings)
        self.assertEqual(wascalled, ['is_enabled'])

        wascalled[:] = [] # reset
        enabled = True
        self.spider.use_hubproxy = False
        proxyauth = 'Basic Foo'
        self._assert_enabled(self.spider, self.settings, proxyauth=proxyauth)
        self.assertEqual(wascalled, ['is_enabled', 'get_proxyauth'])

########NEW FILE########
__FILENAME__ = test_links
import unittest
from scrapylib.links import follow_links
from scrapy.http import Request

class LinkMock(object):
    def __init__(self, url):
        self.url = url

class LinkExtractorMock(object):
    def extract_links(self, response):
        return [LinkMock(url=x) for x in response.split('|')]

def some_callback():
    pass

class TestLinks(unittest.TestCase):

    def test_follow_links(self):
        r = list(follow_links(LinkExtractorMock(), 'http://link1|http://link2|http://link3', callback=some_callback))
        assert all(isinstance(x, Request) for x in r)
        assert all(x.callback is some_callback for x in r)
        self.assertEqual([x.url for x in r], ['http://link1', 'http://link2', 'http://link3'])

########NEW FILE########
__FILENAME__ = test_magicfields
import re, os
from unittest import TestCase

from scrapy.spider import BaseSpider
from scrapy.utils.test import get_crawler
from scrapy.item import DictItem, Field
from scrapy.http import HtmlResponse

from scrapylib.magicfields import _format, MagicFieldsMiddleware

class TestItem(DictItem):
    fields = {
        'url': Field(),
        'nom': Field(),
        'prix': Field(),
        'spider': Field(),
        'sku': Field(),
    }

class MagicFieldsTest(TestCase):
    
    def setUp(self):
        self.environ = os.environ.copy()
        self.spider = BaseSpider('myspider', arg1='val1', start_urls = ["http://example.com"])
        def _log(x):
            print x
        self.spider.log = _log
        self.response = HtmlResponse(body="<html></html>", url="http://www.example.com/product/8798732") 
        self.item = TestItem({'nom': 'myitem', 'prix': "56.70 euros", "url": "http://www.example.com/product.html?item_no=345"})

    def tearDown(self):
        os.environ = self.environ

    def assertRegexpMatches(self, text, regexp):
        """not present in python below 2.7"""
        return self.assertNotEqual(re.match(regexp, text), None)

    def test_hello(self):
        self.assertEqual(_format("hello world!", self.spider, self.response, self.item, {}), 'hello world!')

    def test_spidername_time(self):
        formatted = _format("Spider: $spider:name. Item scraped at $time", self.spider, self.response, self.item, {})
        self.assertRegexpMatches(formatted, 'Spider: myspider. Item scraped at \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$')

    def test_unixtime(self):
        formatted = _format("Item scraped at $unixtime", self.spider, self.response, self.item, {})
        self.assertRegexpMatches(formatted, 'Item scraped at \d+\.\d+$')

    def test_isotime(self):
        formatted = _format("$isotime", self.spider, self.response, self.item, {})
        self.assertRegexpMatches(formatted, '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}$')

    def test_jobid(self):
        os.environ["SCRAPY_JOB"] = 'aa788'
        formatted = _format("job id '$jobid' for spider $spider:name", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, "job id 'aa788' for spider myspider")

    def test_spiderarg(self):
        formatted = _format("Argument arg1: $spider:arg1", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, 'Argument arg1: val1')

    def test_spiderattr(self):
        formatted = _format("$spider:start_urls", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, "['http://example.com']")

    def test_settings(self):
        formatted = _format("$setting:MY_SETTING", self.spider, self.response, self.item, {"$setting": {"MY_SETTING": True}})
        self.assertEqual(formatted, 'True')

    def test_notexisting(self):
        """Not existing entities are not substituted"""
        formatted = _format("Item scraped at $myentity", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, 'Item scraped at $myentity')

    def test_noargs(self):
        """If entity does not accept arguments, don't substitute"""
        formatted = _format("Scraped on day $unixtime:arg", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, "Scraped on day $unixtime:arg")

    def test_noargs2(self):
        """If entity does not have enough arguments, don't substitute"""
        formatted = _format("$spider", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, "$spider")

    def test_invalidattr(self):
        formatted = _format("Argument arg2: $spider:arg2", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, "Argument arg2: $spider:arg2")

    def test_environment(self):
        os.environ["TEST_ENV"] = "testval"
        formatted = _format("$env:TEST_ENV", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, "testval")

    def test_response(self):
        formatted = _format("$response:url", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, self.response.url)

    def test_fields_copy(self):
        formatted = _format("$field:nom", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, 'myitem')

    def test_regex(self):
        formatted = _format("$field:url,r'item_no=(\d+)'", self.spider, self.response, self.item, {})
        self.assertEqual(formatted, '345')

    def test_mware(self):
        settings = {"MAGIC_FIELDS": {"spider": "$spider:name"}}
        crawler = get_crawler(settings)
        mware = MagicFieldsMiddleware.from_crawler(crawler)
        result = list(mware.process_spider_output(self.response, [self.item], self.spider))[0]
        expected = {
            'nom': 'myitem',
            'prix': '56.70 euros',
            'spider': 'myspider',
            'url': 'http://www.example.com/product.html?item_no=345'
        }
        self.assertEqual(result, expected)

    def test_mware_override(self):
        settings = {
            "MAGIC_FIELDS": {"spider": "$spider:name"},
            "MAGIC_FIELDS_OVERRIDE": {"sku": "$field:nom"}
        }
        crawler = get_crawler(settings)
        mware = MagicFieldsMiddleware.from_crawler(crawler)
        result = list(mware.process_spider_output(self.response, [self.item], self.spider))[0]
        expected = {
            'nom': 'myitem',
            'prix': '56.70 euros',
            'spider': 'myspider',
            'url': 'http://www.example.com/product.html?item_no=345',
            'sku': 'myitem',
        }
        self.assertEqual(result, expected)

########NEW FILE########
__FILENAME__ = test_processors
#!/usr/bin/env python
import datetime
import locale
import unittest

from scrapylib.processors import to_datetime, to_date


class TestProcessors(unittest.TestCase):

    def test_to_datetime(self):
        self.assertEquals(to_datetime('March 4, 2011 20:00', '%B %d, %Y %H:%S'),
                          datetime.datetime(2011, 3, 4, 20, 0))

        # test no year in parse format
        test_date = to_datetime('March 4, 20:00', '%B %d, %H:%S')
        self.assertEquals(test_date.year, datetime.datetime.utcnow().year)

        # test parse only date
        self.assertEquals(to_datetime('March 4, 2011', '%B %d, %Y'),
                          datetime.datetime(2011, 3, 4))

    def test_localized_to_datetime(self):
        current_locale = locale.getlocale(locale.LC_ALL)

        self.assertEquals(
            to_datetime('11 janvier 2011', '%d %B %Y', locale='fr_FR.UTF-8'),
            datetime.datetime(2011, 1, 11)
        )

        self.assertEquals(current_locale, locale.getlocale(locale.LC_ALL))

    def test_to_date(self):
        self.assertEquals(to_date('March 4, 2011', '%B %d, %Y'),
                          datetime.date(2011, 3, 4))

        # test no year in parse format
        test_date = to_date('March 4', '%B %d')
        self.assertEquals(test_date.year, datetime.datetime.utcnow().year)

    def test_localized_to_date(self):
        current_locale = locale.getlocale(locale.LC_ALL)

        self.assertEquals(
            to_date('11 janvier 2011', '%d %B %Y', locale='fr_FR.UTF-8'),
            datetime.date(2011, 1, 11)
        )

        self.assertEquals(current_locale, locale.getlocale(locale.LC_ALL))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_querycleaner
from unittest import TestCase

from scrapy.http import Request, Response
from scrapy.spider import BaseSpider
from scrapy.utils.test import get_crawler
from scrapylib.querycleaner import QueryCleanerMiddleware
from scrapy.exceptions import NotConfigured

class QueryCleanerTestCase(TestCase):

    mwcls = QueryCleanerMiddleware

    def setUp(self):
        self.spider = BaseSpider('foo')

    def test_not_loaded(self):
        crawler = get_crawler({})
        self.assertRaises(NotConfigured, self.mwcls.from_crawler, crawler)
        
    def test_filter_keep(self):
        crawler = get_crawler({"QUERYCLEANER_KEEP": "qxp"})
        mw = self.mwcls.from_crawler(crawler)
        response = Response(url="http://www.example.com/qxg1231")
        request = Request(url="http://www.example.com/product/?qxp=12&qxg=1231")
        new_request = list(mw.process_spider_output(response, [request], self.spider))[0]
        self.assertEqual(new_request.url, "http://www.example.com/product/?qxp=12")
        self.assertNotEqual(request, new_request)

    def test_filter_remove(self):
        crawler = get_crawler({"QUERYCLEANER_REMOVE": "qxg"})
        mw = self.mwcls.from_crawler(crawler)
        response = Response(url="http://www.example.com/qxg1231")
        request = Request(url="http://www.example.com/product/?qxp=12&qxg=1231")
        new_request = list(mw.process_spider_output(response, [request], self.spider))[0]
        self.assertEqual(new_request.url, "http://www.example.com/product/?qxp=12")
        self.assertNotEqual(request, new_request)

########NEW FILE########
