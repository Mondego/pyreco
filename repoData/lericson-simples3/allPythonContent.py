__FILENAME__ = bucket
"""Bucket manipulation"""

from __future__ import absolute_import

import time
import hmac
import hashlib
import httplib
import urllib2
import datetime
import warnings
from xml.etree import cElementTree as ElementTree
from contextlib import contextmanager
from urllib import quote_plus
from base64 import b64encode
from cgi import escape

from .utils import (_amz_canonicalize, metadata_headers, rfc822_fmtdate, _iso8601_dt,
                    aws_md5, aws_urlquote, guess_mimetype, info_dict, expire2datetime)

amazon_s3_domain = "s3.amazonaws.com"
amazon_s3_ns_url = "http://%s/doc/2006-03-01/" % amazon_s3_domain

class S3Error(Exception):
    fp = None

    def __init__(self, message, **kwds):
        self.args = message, kwds.copy()
        self.msg, self.extra = self.args

    def __str__(self):
        rv = self.msg
        if self.extra:
            rv += " ("
            rv += ", ".join("%s=%r" % i for i in self.extra.iteritems())
            rv += ")"
        return rv

    @classmethod
    def from_urllib(cls, e, **extra):
        """Try to read the real error from AWS."""
        self = cls("HTTP error", **extra)
        for attr in ("reason", "code", "filename"):
            if attr not in extra and hasattr(e, attr):
                self.extra[attr] = getattr(e, attr)
        self.fp = getattr(e, "fp", None)
        if self.fp:
            # The except clause is to avoid a bug in urllib2 which has it read
            # as in chunked mode, but S3 gives an empty reply.
            try:
                self.data = data = self.fp.read()
            except (httplib.HTTPException, urllib2.URLError), e:
                self.extra["read_error"] = e
            else:
                data = data.decode("utf-8")
                begin, end = data.find("<Message>"), data.find("</Message>")
                if min(begin, end) >= 0:
                    self.msg = data[begin + 9:end]
        return self

    @property
    def code(self): return self.extra.get("code")

class KeyNotFound(S3Error, KeyError):
    @property
    def key(self): return self.extra.get("key")

class StreamHTTPHandler(urllib2.HTTPHandler):
    pass

class StreamHTTPSHandler(urllib2.HTTPSHandler):
    pass

class AnyMethodRequest(urllib2.Request):
    def __init__(self, method, *args, **kwds):
        self.method = method
        urllib2.Request.__init__(self, *args, **kwds)

    def get_method(self):
        return self.method

class S3Request(object):
    urllib_request_cls = AnyMethodRequest

    def __init__(self, bucket=None, key=None, method="GET", headers={},
                 args=None, data=None, subresource=None):
        headers = headers.copy()
        if data and "Content-MD5" not in headers:
            headers["Content-MD5"] = aws_md5(data)
        if "Date" not in headers:
            headers["Date"] = rfc822_fmtdate()
        if hasattr(bucket, "name"):
            bucket = bucket.name
        self.bucket = bucket
        self.key = key
        self.method = method
        self.headers = headers
        self.args = args
        self.data = data
        self.subresource = subresource

    def __str__(self):
        return "<S3 %s request bucket %r key %r>" % (self.method, self.bucket, self.key)

    def descriptor(self):
        # The signature descriptor is detalied in the developer's PDF on p. 65.
        lines = (self.method,
                 self.headers.get("Content-MD5", ""),
                 self.headers.get("Content-Type", ""),
                 self.headers.get("Date", ""))
        preamb = "\n".join(str(line) for line in lines) + "\n"
        headers = _amz_canonicalize(self.headers)
        res = self.canonical_resource
        return "".join((preamb, headers, res))

    @property
    def canonical_resource(self):
        res = "/"
        if self.bucket:
            res += aws_urlquote(self.bucket)
        if self.key is not None:
            res += "/%s" % aws_urlquote(self.key)
        if self.subresource:
            res += "?%s" % aws_urlquote(self.subresource)
        return res

    def sign(self, cred):
        "Sign the request with credentials *cred*."
        desc = self.descriptor()
        key = cred.secret_key.encode("utf-8")
        hasher = hmac.new(key, desc.encode("utf-8"), hashlib.sha1)
        sign = b64encode(hasher.digest())
        self.headers["Authorization"] = "AWS %s:%s" % (cred.access_key, sign)
        return sign

    def urllib(self, bucket):
        return self.urllib_request_cls(self.method, self.url(bucket.base_url),
                                       data=self.data, headers=self.headers)

    def url(self, base_url, arg_sep="&"):
        url = base_url + "/"
        if self.key:
            url += aws_urlquote(self.key)
        if self.subresource or self.args:
            ps = []
            if self.subresource:
                ps.append(self.subresource)
            if self.args:
                args = self.args
                if hasattr(args, "iteritems"):
                    args = args.iteritems()
                args = ((quote_plus(k), quote_plus(v)) for (k, v) in args)
                args = arg_sep.join("%s=%s" % i for i in args)
                ps.append(args)
            url += "?" + "&".join(ps)
        return url

class S3File(str):
    def __new__(cls, value, **kwds):
        return super(S3File, cls).__new__(cls, value)

    def __init__(self, value, **kwds):
        kwds["data"] = value
        self.kwds = kwds

    def put_into(self, bucket, key):
        return bucket.put(key, **self.kwds)

class S3Listing(object):
    """Representation of a single pageful of S3 bucket listing data."""

    truncated = None

    def __init__(self, etree):
        # TODO Use SAX - processes XML before downloading entire response
        root = etree.getroot()
        expect_tag = self._mktag("ListBucketResult")
        if root.tag != expect_tag:
            raise ValueError("root tag mismatch, wanted %r but got %r"
                             % (expect_tag, root.tag))
        self.etree = etree
        trunc_text = root.findtext(self._mktag("IsTruncated"))
        self.truncated = {"true": True, "false": False}[trunc_text]

    def __iter__(self):
        root = self.etree.getroot()
        for entry in root.findall(self._mktag("Contents")):
            item = self._el2item(entry)
            yield item
            self.next_marker = item[0]

    @classmethod
    def parse(cls, resp):
        return cls(ElementTree.parse(resp))

    def _mktag(self, name):
        return "{%s}%s" % (amazon_s3_ns_url, name)

    def _el2item(self, el):
        get = lambda tag: el.findtext(self._mktag(tag))
        key = get("Key")
        modify = _iso8601_dt(get("LastModified"))
        etag = get("ETag")
        size = int(get("Size"))
        return (key, modify, etag, size)

class S3Bucket(object):
    default_encoding = "utf-8"
    n_retries = 10

    def __init__(self, name=None, access_key=None, secret_key=None,
                 base_url=None, timeout=None, secure=False):
        scheme = ("http", "https")[int(bool(secure))]
        if not base_url:
            base_url = "%s://%s" % (scheme, amazon_s3_domain)
            if name:
                base_url += "/%s" % aws_urlquote(name)
        elif secure is not None:
            if not base_url.startswith(scheme + "://"):
                raise ValueError("secure=%r, url must use %s"
                                 % (secure, scheme))
        self.opener = self.build_opener()
        self.name = name
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.timeout = timeout

    def __str__(self):
        return "<%s %s at %r>" % (self.__class__.__name__, self.name, self.base_url)

    def __repr__(self):
        return self.__class__.__name__ + "(%r, access_key=%r, base_url=%r)" % (
            self.name, self.access_key, self.base_url)

    def __getitem__(self, name): return self.get(name)
    def __delitem__(self, name): return self.delete(name)
    def __setitem__(self, name, value):
        if hasattr(value, "put_into"):
            return value.put_into(self, name)
        else:
            return self.put(name, value)
    def __contains__(self, name):
        try:
            self.info(name)
        except KeyError:
            return False
        else:
            return True

    @contextmanager
    def timeout_disabled(self):
        (prev_timeout, self.timeout) = (self.timeout, None)
        try:
            yield
        finally:
            self.timeout = prev_timeout

    @classmethod
    def build_opener(cls):
        return urllib2.build_opener(StreamHTTPHandler, StreamHTTPSHandler)

    def request(self, *a, **k):
        k.setdefault("bucket", self.name)
        return S3Request(*a, **k)

    def send(self, s3req):
        s3req.sign(self)
        for retry_no in xrange(self.n_retries):
            req = s3req.urllib(self)
            try:
                if self.timeout:
                    return self.opener.open(req, timeout=self.timeout)
                else:
                    return self.opener.open(req)
            except (urllib2.HTTPError, urllib2.URLError), e:
                # If S3 gives HTTP 500, we should try again.
                ecode = getattr(e, "code", None)
                if ecode == 500:
                    continue
                elif ecode == 404:
                    exc_cls = KeyNotFound
                else:
                    exc_cls = S3Error
                raise exc_cls.from_urllib(e, key=s3req.key)
        else:
            raise RuntimeError("ran out of retries")  # Shouldn't happen.

    def make_request(self, *a, **k):
        warnings.warn(DeprecationWarning("make_request() is deprecated, "
                                         "use request() and send()"))
        return self.send(self.request(*a, **k))

    def get(self, key):
        response = self.send(self.request(key=key))
        response.s3_info = info_dict(dict(response.info()))
        return response

    def info(self, key):
        response = self.send(self.request(method="HEAD", key=key))
        rv = info_dict(dict(response.info()))
        response.close()
        return rv

    def put(self, key, data=None, acl=None, metadata={}, mimetype=None,
            transformer=None, headers={}):
        if isinstance(data, unicode):
            data = data.encode(self.default_encoding)
        headers = headers.copy()
        if mimetype:
            headers["Content-Type"] = str(mimetype)
        elif "Content-Type" not in headers:
            headers["Content-Type"] = guess_mimetype(key)
        headers.update(metadata_headers(metadata))
        if acl: headers["X-AMZ-ACL"] = acl
        if transformer: data = transformer(headers, data)
        if "Content-Length" not in headers:
            headers["Content-Length"] = str(len(data))
        if "Content-MD5" not in headers:
            headers["Content-MD5"] = aws_md5(data)
        s3req = self.request(method="PUT", key=key, data=data, headers=headers)
        self.send(s3req).close()

    def delete(self, *keys):
        n_keys = len(keys)
        if not keys:
            raise TypeError("required one key at least")

        if n_keys == 1:
            # In <=py25, urllib2 raises an exception for HTTP 204, and later
            # does not, so treat errors and non-errors as equals.
            try:
                resp = self.send(self.request(method="DELETE", key=keys[0]))
            except KeyNotFound, e:
                e.fp.close()
                return False
            else:
                return 200 <= resp.code < 300
        else:
            if n_keys > 1000:
                raise ValueError("cannot delete more than 1000 keys at a time")
            fmt = "<Object><Key>%s</Key></Object>"
            body = "".join(fmt % escape(k) for k in keys)
            data = ('<?xml version="1.0" encoding="UTF-8"?><Delete>'
                    "<Quiet>true</Quiet>%s</Delete>") % body
            headers = {"Content-Type": "multipart/form-data"}
            resp = self.send(self.request(method="POST", data=data,
                                          headers=headers, subresource="delete"))
            return 200 <= resp.code < 300

    # TODO Expose the conditional headers, x-amz-copy-source-if-*
    # TODO Add module-level documentation and doctests.
    def copy(self, source, key, acl=None, metadata=None,
             mimetype=None, headers={}):
        """Copy S3 file *source* on format '<bucket>/<key>' to *key*.

        If metadata is not None, replaces the metadata with given metadata,
        otherwise copies the previous metadata.

        Note that *acl* is not copied, but set to *private* by S3 if not given.
        """
        headers = headers.copy()
        headers.update({"Content-Type": mimetype or guess_mimetype(key)})
        headers["X-AMZ-Copy-Source"] = source
        if acl: headers["X-AMZ-ACL"] = acl
        if metadata is not None:
            headers["X-AMZ-Metadata-Directive"] = "REPLACE"
            headers.update(metadata_headers(metadata))
        else:
            headers["X-AMZ-Metadata-Directive"] = "COPY"
        self.send(self.request(method="PUT", key=key, headers=headers)).close()

    def _get_listing(self, args):
        return S3Listing.parse(self.send(self.request(key='', args=args)))

    def listdir(self, prefix=None, marker=None, limit=None, delimiter=None):
        """List bucket contents.

        Yields tuples of (key, modified, etag, size).

        *prefix*, if given, predicates `key.startswith(prefix)`.
        *marker*, if given, predicates `key > marker`, lexicographically.
        *limit*, if given, predicates `len(keys) <= limit`.

        *key* will include the *prefix* if any is given.

        .. note:: This method can make several requests to S3 if the listing is
                  very long.
        """
        m = (("prefix", prefix),
             ("marker", marker),
             ("max-keys", limit),
             ("delimiter", delimiter))
        args = dict((str(k), str(v)) for (k, v) in m if v is not None)

        listing = self._get_listing(args)
        while listing:
            for item in listing:
                yield item

            if listing.truncated:
                args["marker"] = listing.next_marker
                listing = self._get_listing(args)
            else:
                break

    def make_url(self, key, args=None, arg_sep=";"):
        s3req = self.request(key=key, args=args)
        return s3req.url(self.base_url, arg_sep=arg_sep)

    def make_url_authed(self, key, expire=datetime.timedelta(minutes=5)):
        """Produce an authenticated URL for S3 object *key*.

        *expire* is a delta or a datetime on which the authenticated URL
        expires. It defaults to five minutes, and accepts a timedelta, an
        integer delta in seconds, or a datetime.

        To generate an unauthenticated URL for a key, see `B.make_url`.
        """
        # NOTE There is a usecase for having a headers argument to this
        # function - Amazon S3 will validate the X-AMZ-* headers of the GET
        # request, and so for the browser to send such a header, it would have
        # to be listed in the signature description.
        expire = expire2datetime(expire)
        expire = time.mktime(expire.timetuple()[:9])
        expire = str(int(expire))
        s3req = self.request(key=key, headers={"Date": expire})
        sign = s3req.sign(self)
        s3req.args = (("AWSAccessKeyId", self.access_key),
                      ("Expires", expire),
                      ("Signature", sign))
        return s3req.url(self.base_url, arg_sep="&")

    def url_for(self, key, authenticated=False,
                expire=datetime.timedelta(minutes=5)):
        msg = "use %s instead of url_for(authenticated=%r)"
        dep_cls = DeprecationWarning
        if authenticated:
            warnings.warn(dep_cls(msg % ("make_url_authed", True)))
            return self.make_url_authed(key, expire=expire)
        else:
            warnings.warn(dep_cls(msg % ("make_url", False)))
            return self.make_url(key)

    def put_bucket(self, config_xml=None, acl=None):
        if config_xml:
            if isinstance(config_xml, unicode):
                config_xml = config_xml.encode("utf-8")
            headers = {"Content-Length": len(config_xml),
                       "Content-Type": "text/xml"}
        else:
            headers = {"Content-Length": "0"}
        if acl:
            headers["X-AMZ-ACL"] = acl
        resp = self.send(self.request(method="PUT", key=None,
                                      data=config_xml, headers=headers))
        resp.close()
        return resp.code == 200

    def delete_bucket(self):
        return self.delete(None)

class ReadOnlyS3Bucket(S3Bucket):
    """Read-only S3 bucket.

    Mostly useful for situations where urllib2 isn't available (e.g. Google App
    Engine), but you still want the utility functions (like generating
    authenticated URLs, and making upload HTML forms.)
    """

    def build_opener(self):
        return None

########NEW FILE########
__FILENAME__ = gae
"""Compatibility layer for Google App Engine

Use as you would normally do with :mod:`simples3`, only instead of
:class:`simples3.S3Bucket`, use :class:`simples3.gae.AppEngineS3Bucket`.
"""

import urllib2
from StringIO import StringIO
from urllib import addinfourl
from google.appengine.api import urlfetch
from simples3.bucket import S3Bucket

class _FakeDict(list):
    def iteritems(self):
        return self

def _http_open(req):
    resp = urlfetch.fetch(req.get_full_url(),
                          payload=req.get_data(),
                          method=req.get_method(),
                          headers=_FakeDict(req.header_items()))
    fp = StringIO(resp.content)
    rv = addinfourl(fp, resp.headers, req.get_full_url())
    rv.code = resp.status_code
    rv.msg = "?"
    return rv

class UrlFetchHTTPHandler(urllib2.HTTPHandler):
    def http_open(self, req):
        return _http_open(req)

class UrlFetchHTTPSHandler(urllib2.HTTPSHandler):
    def https_open(self, req):
        return _http_open(req)

class AppEngineS3Bucket(S3Bucket):
    @classmethod
    def build_opener(cls):
        # urllib likes to import ctypes. Why? Because on OS X, it uses it to
        # find proxy configurations. While that is nice and all (and a huge
        # f---ing kludge), it makes the GAE development server bork because the
        # platform makes urllib import ctypes, and that's not permissible on
        # App Engine (can't load dynamic libraries at all.)
        #
        # Giving urllib2 a ProxyHandler without any proxies avoids this look-up
        # trickery, and so is beneficial to our ends and goals in this pickle
        # of a situation.
        return urllib2.build_opener(UrlFetchHTTPHandler, UrlFetchHTTPSHandler,
                                    urllib2.ProxyHandler(proxies={}))

########NEW FILE########
__FILENAME__ = streaming
"""Streaming with :mod:`simples3` via :mod:`poster.streaminghttp`

Usage::

    >>> bucket = StreamingS3Bucket("foo.com")
    >>> bucket.put_file("huge_cd.iso", "foo/huge_cd.iso", acl="public-read")
    >>> with open("foo/huge_cd.iso", "rb") as fp:
    ...     bucket.put_file("memdump.bin", fp)
"""

import os
import urllib2
from simples3.bucket import S3Bucket

class ProgressCallingFile(object):
    __slots__ = ("fp", "pos", "size", "progress")

    def __init__(self, fp, size, progress):
        self.fp = fp
        self.pos = fp.tell()
        self.size = size
        self.progress = progress

    def __getattr__(self, attnam):
        return getattr(self.fp, attnam)

    def read(self, *a, **k):
        chunk = self.fp.read(*a, **k)
        self.pos += len(chunk)
        self.progress(self.pos, self.size, len(chunk))
        return chunk

class StreamingMixin(object):
    def put_file(self, key, fp, acl=None, metadata={}, progress=None,
                 size=None, mimetype=None, transformer=None, headers={}):
        """Put file-like object or filename *fp* on S3 as *key*.

        *fp* must have a read method that takes a buffer size, and must behave
        correctly with regards to seeking and telling.

        *size* can be specified as a size hint. Otherwise the size is figured
        out via ``os.fstat``, and requires that *fp* have a functioning
        ``fileno()`` method.

        *progress* is a callback that might look like ``p(current, total,
        last_read)``. ``current`` is the current position, ``total`` is the
        size, and ``last_read`` is how much was last read. ``last_read`` is
        zero on EOF.
        """
        headers = headers.copy()
        do_close = False
        if not hasattr(fp, "read"):
            fp = open(fp, "rb")
            do_close = True

        if size is None and hasattr(fp, "fileno"):
            size = os.fstat(fp.fileno()).st_size
        if "Content-Length" not in headers:
            if size is None:
                raise TypeError("no size given and fp does not have a fileno")
            headers["Content-Length"] = str(size)

        if progress:
            fp = ProgressCallingFile(fp, int(size), progress)

        try:
            self.put(key, data=fp, acl=acl, metadata=metadata,
                     mimetype=mimetype, transformer=transformer,
                     headers=headers)
        finally:
            if do_close:
                fp.close()

class UnimplementedStreamingMixin(StreamingMixin):
    exc_text = """it appears you forgot to install a streaming http library\n
for example, you could run ``sudo easy_install poster``
"""

    @classmethod
    def build_opener(cls):
        raise NotImplementedError(cls.exc_text)

default_stream_mixin = UnimplementedStreamingMixin

try:
    from poster.streaminghttp import StreamingHTTPHandler
except ImportError:
    pass
else:
    class PosterStreamingMixin(StreamingMixin):
        @classmethod
        def build_opener(cls):
            return urllib2.build_opener(StreamingHTTPHandler)

    default_stream_mixin = PosterStreamingMixin

class StreamingS3Bucket(default_stream_mixin, S3Bucket): pass

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = utils
"""Misc. S3-related utilities."""

import time
import hashlib
import datetime
import mimetypes
from base64 import b64encode
from urllib import quote
from calendar import timegm

def _amz_canonicalize(headers):
    r"""Canonicalize AMZ headers in that certain AWS way.

    >>> _amz_canonicalize({"x-amz-test": "test"})
    'x-amz-test:test\n'
    >>> _amz_canonicalize({"x-amz-first": "test",
    ...                    "x-amz-second": "hello"})
    'x-amz-first:test\nx-amz-second:hello\n'
    >>> _amz_canonicalize({})
    ''
    """
    rv = {}
    for header, value in headers.iteritems():
        header = header.lower()
        if header.startswith("x-amz-"):
            rv.setdefault(header, []).append(value)
    parts = []
    for key in sorted(rv):
        parts.append("%s:%s\n" % (key, ",".join(rv[key])))
    return "".join(parts)

def metadata_headers(metadata):
    return dict(("X-AMZ-Meta-" + h, v) for h, v in metadata.iteritems())

def headers_metadata(headers):
    return dict((h[11:], v) for h, v in headers.iteritems()
                            if h.lower().startswith("x-amz-meta-"))

iso8601_fmt = '%Y-%m-%dT%H:%M:%S.000Z'

def _iso8601_dt(v): return datetime.datetime.strptime(v, iso8601_fmt)
def rfc822_fmtdate(t=None):
    from email.utils import formatdate
    if t is None:
        t = datetime.datetime.utcnow()
    return formatdate(timegm(t.timetuple()), usegmt=True)
def rfc822_parsedate(v):
    from email.utils import parsedate
    return datetime.datetime.fromtimestamp(time.mktime(parsedate(v)))

def expire2datetime(expire, base=None):
    """Force *expire* into a datetime relative to *base*.

    If expire is a relatively small integer, it is assumed to be a delta in
    seconds. This is possible for deltas up to 10 years.

    If expire is a delta, it is added to *base* to yield the expire date.

    If base isn't given, the current time is assumed.

    >>> base = datetime.datetime(1990, 1, 31, 1, 2, 3)
    >>> expire2datetime(base) == base
    True
    >>> expire2datetime(3600 * 24, base=base) - base
    datetime.timedelta(1)
    >>> import time
    >>> expire2datetime(time.mktime(base.timetuple())) == base
    True
    """
    if hasattr(expire, "timetuple"):
        return expire
    if base is None:
        base = datetime.datetime.now()
    # *expire* is not a datetime object; try interpreting it
    # as a timedelta, a UNIX timestamp or offsets in seconds.
    try:
        return base + expire
    except TypeError:
        # Since the operands could not be added, reinterpret
        # *expire* as a UNIX timestamp or a delta in seconds.
        # This is rather arbitrary: 10 years are allowed.
        unix_eighties = 315529200
        if expire < unix_eighties:
            return base + datetime.timedelta(seconds=expire)
        else:
            return datetime.datetime.fromtimestamp(expire)

def aws_md5(data):
    """Make an AWS-style MD5 hash (digest in base64)."""
    hasher = hashlib.new("md5")
    if hasattr(data, "read"):
        data.seek(0)
        while True:
            chunk = data.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
        data.seek(0)
    else:
        hasher.update(data)
    return b64encode(hasher.digest()).decode("ascii")

def aws_urlquote(value):
    r"""AWS-style quote a URL part.

    >>> aws_urlquote("/bucket/a key")
    '/bucket/a%20key'
    """
    if isinstance(value, unicode):
        value = value.encode("utf-8")
    return quote(value, "/")

def guess_mimetype(fn, default="application/octet-stream"):
    """Guess a mimetype from filename *fn*.

    >>> guess_mimetype("foo.txt")
    'text/plain'
    >>> guess_mimetype("foo")
    'application/octet-stream'
    """
    if "." not in fn:
        return default
    bfn, ext = fn.lower().rsplit(".", 1)
    if ext == "jpg": ext = "jpeg"
    return mimetypes.guess_type(bfn + "." + ext)[0] or default

def info_dict(headers):
    rv = {"headers": headers, "metadata": headers_metadata(headers)}
    if "content-length" in headers:
        rv["size"] = int(headers["content-length"])
    if "content-type" in headers:
        rv["mimetype"] = headers["content-type"]
    if "date" in headers:
        rv["date"] = rfc822_parsedate(headers["date"])
    if "last-modified" in headers:
        rv["modify"] = rfc822_parsedate(headers["last-modified"])
    return rv

def name(o):
    """Find the name of *o*.

    Functions:
    >>> name(name)
    'simples3.utils.name'
    >>> def my_fun(): pass
    >>> name(my_fun)
    'simples3.utils.my_fun'

    Classes:
    >>> class MyKlass(object): pass
    >>> name(MyKlass)
    'simples3.utils.MyKlass'

    Instances:
    >>> name(MyKlass())
    'simples3.utils.MyKlass'

    Types:
    >>> name(str), name(object), name(int)
    ('str', 'object', 'int')

    Type instances:
    >>> name("Hello"), name(True), name(None), name(Ellipsis)
    ('str', 'bool', 'NoneType', 'ellipsis')
    """
    if hasattr(o, "__name__"):
        rv = o.__name__
        modname = getattr(o, "__module__", None)
        # This work-around because Python does it itself,
        # see typeobject.c, type_repr.
        # Note that Python only checks for __builtin__.
        if modname not in (None, "", "__builtin__", "builtins"):
            rv = o.__module__ + "." + rv
    else:
        for o in getattr(o, "__mro__", o.__class__.__mro__):
            rv = name(o)
            # If there is no name for the this baseclass, this ensures we check
            # the next rather than say the object has no name (i.e., return
            # None)
            if rv is not None:
                break
    return rv

########NEW FILE########
__FILENAME__ = test_bucket
from __future__ import with_statement

import StringIO
import urllib2
import unittest
import datetime
from nose.tools import eq_

import simples3
from simples3.utils import aws_md5, aws_urlquote
from simples3.utils import rfc822_fmtdate, rfc822_parsedate
from tests import MockHTTPResponse, BytesIO, g

from tests import setup_package, teardown_package
setup_package, teardown_package

def test_rfc822():
    s = rfc822_fmtdate()
    dt = rfc822_parsedate(s)
    eq_(s, rfc822_fmtdate(dt))
    eq_(dt, rfc822_parsedate(s))

class S3BucketTestCase(unittest.TestCase):
    def setUp(self):
        g.bucket.mock_reset()

    def tearDown(self):
        if g.bucket.mock_responses:
            raise RuntimeError("test run without exhausting mock_responses")

class MiscTests(S3BucketTestCase):
    def test_str(self):
        eq_(str(g.bucket), "<MockBucket johnsmith at "
                           "'http://johnsmith.s3.amazonaws.com'>")

    def test_repr(self):
        eq_(repr(g.bucket),
            "MockBucket('johnsmith', "
            "access_key='0PN5J17HBGZHT7JJ3X82', "
            "base_url='http://johnsmith.s3.amazonaws.com')")

    def test_timeout_disabled(self):
        g.bucket.timeout = 10.0
        with g.bucket.timeout_disabled():
            eq_(g.bucket.timeout, None)
        eq_(g.bucket.timeout, 10.0)
        g.bucket.timeout = None

    def test_error_in_error(self):
        # a hairy situation: an error arising during the parsing of an error.
        def read(bs=4096):
            raise urllib2.URLError("something something dark side")
        FP = type("ErringFP", (object,),
                  {"read": read, "readline": read, "readlines": read})
        url = g.bucket.base_url + "/foo.txt"
        resp = MockHTTPResponse(FP(), {}, url, code=401)
        g.bucket.add_resp_obj(resp, status="401 Something something")
        try:
            g.bucket.get("foo.txt")
        except simples3.S3Error, e:
            assert "read_error" in e.extra

    def test_aws_md5_lit(self):
        val = "Hello!".encode("ascii")
        eq_(aws_md5(val), 'lS0sVtBIWVgzZ0e83ZhZDQ==')

    def test_aws_md5_fp(self):
        val = "Hello world!".encode("ascii")
        eq_(aws_md5(BytesIO(val)), 'hvsmnRkNLIX24EaM7KQqIA==')

    def test_aws_urlquote_funky(self):
        if hasattr(str, "decode"):
            val = "/bucket/\xc3\xa5der".decode("utf-8")
        else:
            val = "/bucket/\xe5der"
        eq_(aws_urlquote(val), "/bucket/%C3%A5der")

    def test_amazon_s3_ns_url(self):
      # The Amazon S3 XML namespace needs to be *exactly* as advertised
      eq_("http://s3.amazonaws.com/doc/2006-03-01/", simples3.bucket.amazon_s3_ns_url)

class GetTests(S3BucketTestCase):
    def test_get(self):
        dt = datetime.datetime(1990, 1, 31, 12, 34, 56)
        headers = g.H("text/plain",
            ("date", rfc822_fmtdate(dt)),
            ("x-amz-meta-foo", "bar"))
        g.bucket.add_resp("/foo.txt", headers, "ohi")
        fp = g.bucket["foo.txt"]
        eq_(fp.s3_info["mimetype"], "text/plain")
        eq_(fp.s3_info["metadata"], {"foo": "bar"})
        eq_(fp.s3_info["date"], dt)
        eq_(fp.read().decode("ascii"), "ohi")

    def test_get_not_found(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<Error><Code>NoSuchKey</Code>'
               '<Message>The specified key does not exist.</Message>'
               '<Key>foo.txt</Key>'
               '<RequestId>abcdef</RequestId>'
               '<HostId>abcdef</HostId>'
               '</Error>')
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), xml,
                          status="404 Not Found")
        try:
            g.bucket.get("foo.txt")
        except simples3.KeyNotFound, e:
            eq_(e.key, "foo.txt")
            eq_(str(e), "The specified key does not exist. (code=404, "
                        "key='foo.txt', filename='http://johnsmith.s3."
                        "amazonaws.com/foo.txt')")

class InfoTests(S3BucketTestCase):
    headers = g.H("text/plain",
                  ("x-amz-meta-foo", "bar"),
                  ("last-modified", "Mon, 06 Sep 2010 19:34:18 GMT"),
                  ("content-length", "1234"))

    def test_info(self):
        g.bucket.add_resp("/foo.txt", self.headers, "")
        info = g.bucket.info("foo.txt")
        eq_(info["mimetype"], "text/plain")
        eq_(info["metadata"], {"foo": "bar"})

    def test_mapping(self):
        g.bucket.add_resp("/foo.txt", self.headers, "")
        assert "foo.txt" in g.bucket

    def test_mapping_not(self):
        g.bucket.add_resp("/foobar.txt", self.headers, "", status="404 Blah")
        assert "foobar.txt" not in g.bucket

class PutTests(S3BucketTestCase):
    def _verify_headers(self, contents, headers):
        assert "Content-length" in headers
        assert str(len(contents)) == headers['Content-length']
        assert "Content-type" in headers
        assert "Content-md5" in headers
        content_md5 = aws_md5(contents.encode("ascii"))
        assert content_md5 == headers['Content-md5']
        assert "Authorization" in headers

    def _put_contents(self, key, contents):
        g.bucket.add_resp("/%s" % key, g.H("application/xml"), "OK!")
        g.bucket[key] = contents
        self._verify_headers(contents, g.bucket.mock_requests[-1].headers)

    def test_put(self):
        self._put_contents("foo.txt", "hello")

    def test_put_multiple(self):
        self._put_contents("bar.txt", "hi mom, how are you")
        self._put_contents("foo.txt", "hello")

    def test_put_s3file(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), "OK!")
        g.bucket["foo.txt"] = simples3.S3File("hello")
        data = g.bucket.mock_requests[-1].get_data()
        eq_(data.decode("ascii"), "hello")

    def test_put_retry(self):
        eq_(g.bucket.mock_responses, [])
        xml = "<?xml etc... ?>"
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), xml,
                          status="500 Internal Server Error")
        g.bucket.add_resp("/foo.txt", g.H("text/plain"), "OK!")
        g.bucket.put("foo.txt", "hello")
        eq_(len(g.bucket.mock_requests), 2)
        for req in g.bucket.mock_requests:
            eq_(req.get_method(), "PUT")
            eq_(req.get_selector(), "/foo.txt")
        eq_(g.bucket.mock_responses, [])

class DeleteTests(S3BucketTestCase):
    def test_delete(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"), "<ok />")
        assert g.bucket.delete("foo.txt")
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "DELETE")

    def test_delete_multi_object(self):
        expected = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<DeleteResult xmlns="http://s3.amazonaws.com/doc/2006-'
                    '03-01/"></DeleteResult>')
        g.bucket.add_resp("/?delete", g.H("application/xml"), expected)
        assert g.bucket.delete("foo.txt", "bar.txt", "baz.txt")

    def test_delete_not_found(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"),
                          "<notfound />", status="404 Not Found")
        assert not g.bucket.delete("foo.txt")

    def test_delete_other_error(self):
        g.bucket.add_resp("/foo.txt", g.H("application/xml"),
                          "<wat />", status="403 What's Up?")
        try:
            g.bucket.delete("foo.txt")
        except simples3.S3Error, e:
            eq_(e.extra.get("key"), "foo.txt")
            eq_(e.code, 403)
        else:
            assert False, "did not raise exception"

class CopyTests(S3BucketTestCase):
    def test_copy_metadata(self):
        g.bucket.add_resp("/bar", g.H("application/xml"), "<ok />")
        g.bucket.copy("foo/bar", "bar", acl="public")
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "PUT")
        eq_(req.headers["X-amz-copy-source"], "foo/bar")
        eq_(req.headers["X-amz-metadata-directive"], "COPY")

    def test_copy_replace_metadata(self):
        g.bucket.add_resp("/bar", g.H("application/xml"), "<ok />")
        g.bucket.copy("foo/bar", "bar", metadata={}, acl="public")
        req = g.bucket.mock_requests[-1]
        eq_(req.headers["X-amz-metadata-directive"], "REPLACE")

class ListDirTests(S3BucketTestCase):
    def test_listdir(self):
        xml = """
<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Name>bucket</Name>
    <Prefix></Prefix>
    <Marker></Marker>
    <MaxKeys>1000</MaxKeys>
    <IsTruncated>false</IsTruncated>
    <Contents>
        <Key>my-image.jpg</Key>
        <LastModified>2009-10-12T17:50:30.000Z</LastModified>
        <ETag>&quot;fba9dede5f27731c9771645a39863328&quot;</ETag>
        <Size>434234</Size>
        <StorageClass>STANDARD</StorageClass>
        <Owner>
            <ID>0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef</ID>
            <DisplayName>johndoe</DisplayName>
        </Owner>
    </Contents>
    <Contents>
        <Key>my-third-image.jpg</Key>
        <LastModified>2009-10-12T17:50:30.000Z</LastModified>
        <ETag>&quot;1b2cf535f27731c974343645a3985328&quot;</ETag>
        <Size>64994</Size>
        <StorageClass>STANDARD</StorageClass>
        <Owner>
            <ID>0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef</ID>
            <DisplayName>johndoe</DisplayName>
        </Owner>
    </Contents>
</ListBucketResult>
""".lstrip()
        g.bucket.add_resp("/", g.H("application/xml"), xml)
        reftups = (
            ('my-image.jpg', datetime.datetime(2009, 10, 12, 17, 50, 30),
             '"fba9dede5f27731c9771645a39863328"', 434234),
            ('my-third-image.jpg', datetime.datetime(2009, 10, 12, 17, 50, 30),
             '"1b2cf535f27731c974343645a3985328"', 64994))
        next_reftup = iter(reftups).next
        for tup in g.bucket.listdir():
            eq_(len(tup), 4)
            eq_(tup, next_reftup())
            key, mtype, etag, size = tup

    def test_empty_listing(self):
        xml = """
<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Name>bucket</Name>
    <Prefix></Prefix>
    <Marker></Marker>
    <MaxKeys>1000</MaxKeys>
    <IsTruncated>false</IsTruncated>
</ListBucketResult>
""".lstrip()
        g.bucket.add_resp("/", g.H("application/xml"), xml)
        eq_([], list(g.bucket.listdir()))

class ModifyBucketTests(S3BucketTestCase):
    def test_bucket_put(self):
        g.bucket.add_resp("/", g.H("application/xml"), "<ok />")
        g.bucket.put_bucket(acl="private")
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "PUT")
        eq_(req.headers["X-amz-acl"], "private")

    def test_bucket_put_conf(self):
        g.bucket.add_resp("/", g.H("application/xml"), "<ok />")
        g.bucket.put_bucket("<etc>etc</etc>", acl="public")
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "PUT")
        eq_(req.headers["X-amz-acl"], "public")

    def test_bucket_delete(self):
        g.bucket.add_resp("/", g.H("application/xml"), "<ok />")
        g.bucket.delete_bucket()
        req = g.bucket.mock_requests[-1]
        eq_(req.get_method(), "DELETE")

########NEW FILE########
__FILENAME__ = test_streaming
from __future__ import with_statement

import StringIO

from nose.tools import eq_

from simples3 import streaming
from simples3.utils import aws_md5
from tests import MockBucketMixin, H

class StreamingMockBucket(MockBucketMixin, streaming.StreamingS3Bucket):
    pass

def _verify_headers(headers, contents):
    assert "Content-length" in headers
    assert str(len(contents)) == headers['Content-length']
    assert "Content-type" in headers
    assert "Content-md5" in headers
    content_md5 = aws_md5(contents.encode("ascii"))
    assert content_md5 == headers['Content-md5']
    assert "Authorization" in headers

def _put_contents(bucket, key, contents):
    bucket.add_resp("/%s" % key, H("application/xml"), "OK!")
    bucket[key] = contents
    _verify_headers(bucket.mock_requests[-1].headers, contents)

def _put_file_contents(bucket, key, contents):
    bucket.add_resp("/%s" % key, H("application/xml"), "OK!")

    fp = StringIO.StringIO(contents)
    try:
        bucket.put_file(key, fp, size=len(contents))
    finally:
        fp.close()

    _verify_headers(bucket.mock_requests[-1].headers, contents)

def _test_put(bucket):
    L = []
    bucket.add_resp("/test.py", H("application/xml"), "OK!")
    with open(__file__, 'rb') as fp:
        bucket.put_file("test.py", fp, progress=lambda *a: L.append(a))
    for total, curr, read in L:
        if read == 0:
            eq_(total, curr)
        else:
            assert curr >= read
    assert L[-1][2] == 0, 'Last progress() has read=0'

def _test_put_multiple(bucket):
    _put_contents(bucket, "bar.txt", "hi mom, how are you")
    _put_contents(bucket, "foo.txt", "hello")

def _test_put_file(bucket):
    _put_file_contents(bucket, "foo.txt", "hello")

def _test_put_file_multiple(bucket):
    _put_file_contents(bucket, "bar.txt", "hi mom, how are you")
    _put_file_contents(bucket, "foo.txt", "hello")

def _streaming_test_iter(bucket):
    # yield lambda: _test_put(bucket)
    yield lambda: _test_put_multiple(bucket)
    yield lambda: _test_put_file(bucket)
    yield lambda: _test_put_file_multiple(bucket)

def test_streaming():
    bucket = StreamingMockBucket("johnsmith",
        access_key="0PN5J17HBGZHT7JJ3X82",
        secret_key="uV3F3YluFJax1cknvbcGwgjvx4QpvB+leU8dUj2o",
        base_url="http://johnsmith.s3.amazonaws.com")
    for f in _streaming_test_iter(bucket):
        bucket.mock_reset()
        yield f
        if bucket.mock_responses:
            raise RuntimeError("test run without exhausting mock_responses")

########NEW FILE########
__FILENAME__ = test_urls
import unittest
from tests import g
from nose.tools import eq_

class URLGenerationTests(unittest.TestCase):
    def test_make_url(self):
        eq_('http://johnsmith.s3.amazonaws.com/file.txt',
            g.bucket.make_url('file.txt'))
        eq_('http://johnsmith.s3.amazonaws.com/my%20key',
            g.bucket.make_url('my key'))

    def test_make_url_authed(self):
        # The expected query string is from S3 Developer Guide
        # "Example Query String Request Authentication" section.
        ou = ("http://johnsmith.s3.amazonaws.com/photos/puppy.jpg"
              "?AWSAccessKeyId=0PN5J17HBGZHT7JJ3X82&Expires=1175139620&"
              "Signature=rucSbH0yNEcP9oM2XNlouVI3BH4%3D")
        eq_(ou, g.bucket.make_url_authed("photos/puppy.jpg", expire=1175139620))

    def test_deprecated_url_for(self):
        eq_(g.bucket.make_url_authed("photos/puppy.jpg", expire=1175139620),
            g.bucket.url_for("photos/puppy.jpg", authenticated=True,
                             expire=1175139620))
        eq_(g.bucket.make_url("photos/puppy.jpg"),
            g.bucket.url_for("photos/puppy.jpg"))

########NEW FILE########
