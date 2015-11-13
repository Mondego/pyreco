__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if len(sys.argv) > 2 and sys.argv[1] == '--version':
    VERSION = '==%s' % sys.argv[2]
    args = sys.argv[3:] + ['bootstrap']
else:
    VERSION = ''
    args = sys.argv[1:] + ['bootstrap']

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse('setuptools')).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse('setuptools')).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = cache
import hashlib
import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_str


class Cache(object):
    """
    A base cache class, providing some default behaviors that all other
    cache systems can inherit or override, as necessary.
    """

    def exists(self, name):
        """
        Returns True if a file referened by the given name already exists in the
        storage system, or False if the name is available for a new file.

        If the cache doesn't exist then return None.
        """
        raise NotImplementedError()

    def size(self, name):
        """
        Returns the total size, in bytes, of the file specified by name.

        If the cache doesn't exist then return None.
        """
        raise NotImplementedError()

    def modified_time(self, name):
        """
        Return the time of last modification of name. The return value is a
        number giving the number of seconds since the epoch.

        If the cache doesn't exist then return None.
        """
        raise NotImplementedError()

    def save(self, name, size, mtime):
        """
        Save the values to the cache.
        """
        raise NotImplementedError()

    def remove(self, name):
        """
        Remove the values from the cache.
        """
        raise NotImplementedError()


class FileSystemCache(Cache):
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = getattr(settings, 'CUDDLYBUDDLY_STORAGE_S3_FILE_CACHE_DIR', None)
            if cache_dir is None:
                raise ImproperlyConfigured(
                    '%s requires CUDDLYBUDDLY_STORAGE_S3_FILE_CACHE_DIR to be set to a directory.' % type(self)
                )
        self.cache_dir = cache_dir

    def _path(self, name):
        return os.path.join(self.cache_dir, hashlib.md5(smart_str(name)).hexdigest())

    def exists(self, name):
        return None

    def size(self, name):
        try:
            file = open(self._path(name))
            size = int(file.readlines()[1])
            file.close()
        except:
            size = None
        return size

    def modified_time(self, name):
        try:
            file = open(self._path(name))
            mtime = float(file.readlines()[2])
            file.close()
        except:
            mtime = None
        return mtime

    def save(self, name, size, mtime):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        file = open(self._path(name), 'w')
        file.write(smart_str(name)+'\n'+str(size)+'\n'+str(mtime))
        file.close()

    def remove(self, name):
        name = self._path(name)
        if os.path.exists(name):
            os.remove(name)

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings


def media(request):
    if request.is_secure() or \
       getattr(request.META, 'HTTP_X_FORWARDED_SSL', 'off') == 'on':
        if hasattr(settings.MEDIA_URL, 'https'):
            url = settings.MEDIA_URL.https()
        else:
            url = settings.MEDIA_URL.replace('http://', 'https://')
    else:
        url = settings.MEDIA_URL.replace('https://', 'http://')
    return {'MEDIA_URL': url}

########NEW FILE########
__FILENAME__ = exceptions
class S3Error(IOError):
    pass

########NEW FILE########
__FILENAME__ = lib
#!/usr/bin/env python

#  This software code is made available "AS IS" without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices.  Your use of this software
#  code is at your own risk and you waive any claim against Amazon
#  Digital Services, Inc. or its affiliates with respect to your use of
#  this software code. (c) 2006-2007 Amazon Digital Services, Inc. or its
#  affiliates.

#  Now uses Django's urlquote_plus to circumvent lack of unicode support in
#  urllib.
#
#  Fixed urlquote_plus escaping slashes in urls.
#
#  Stopped build_url_base from adding unnecessary ports (80 and 443).
#
#  Replaced sha with hashlib.
#
#  Date header locale fix.
#
#  Added S3Exception.
#
#  2011/03/07 - Changed all uses of urlquote_plus to urlquote.
#
#  (c) 2009-2011 Kyle MacFarlane

import base64
import hmac
import httplib
import hashlib
import time
import urlparse
import xml.sax
from django.utils.http import urlquote

DEFAULT_HOST = 's3.amazonaws.com'
PORTS_BY_SECURITY = { True: 443, False: 80 }
METADATA_PREFIX = 'x-amz-meta-'
AMAZON_HEADER_PREFIX = 'x-amz-'

class S3Exception(Exception):
    pass

# generates the aws canonical string for the given parameters
def canonical_string(method, bucket="", key="", query_args={}, headers={}, expires=None):
    interesting_headers = {}
    for header_key in headers:
        lk = header_key.lower()
        if lk in ['content-md5', 'content-type', 'date'] or lk.startswith(AMAZON_HEADER_PREFIX):
            interesting_headers[lk] = headers[header_key].strip()

    # these keys get empty strings if they don't exist
    if not 'content-type' in interesting_headers:
        interesting_headers['content-type'] = ''
    if not 'content-md5' in interesting_headers:
        interesting_headers['content-md5'] = ''

    # just in case someone used this.  it's not necessary in this lib.
    if 'x-amz-date' in interesting_headers:
        interesting_headers['date'] = ''

    # if you're using expires for query string auth, then it trumps date
    # (and x-amz-date)
    if expires:
        interesting_headers['date'] = str(expires)

    sorted_header_keys = interesting_headers.keys()
    sorted_header_keys.sort()

    buf = "%s\n" % method
    for header_key in sorted_header_keys:
        if header_key.startswith(AMAZON_HEADER_PREFIX):
            buf += "%s:%s\n" % (header_key, interesting_headers[header_key])
        else:
            buf += "%s\n" % interesting_headers[header_key]

    # append the bucket if it exists
    if bucket != "":
        buf += "/%s" % bucket

    # add the key.  even if it doesn't exist, add the slash
    buf += "/%s" % urlquote(key, '/')

    # handle special query string arguments

    if "acl" in query_args:
        buf += "?acl"
    elif "torrent" in query_args:
        buf += "?torrent"
    elif "logging" in query_args:
        buf += "?logging"
    elif "location" in query_args:
        buf += "?location"

    return buf

# computes the base64'ed hmac-sha hash of the canonical string and the secret
# access key, optionally urlencoding the result
def encode(aws_secret_access_key, str, urlencode=False):
    b64_hmac = base64.encodestring(hmac.new(aws_secret_access_key, str, hashlib.sha1).digest()).strip()
    if urlencode:
        return urlquote(b64_hmac)
    else:
        return b64_hmac

def merge_meta(headers, metadata):
    final_headers = headers.copy()
    for k in metadata.keys():
        final_headers[METADATA_PREFIX + k] = metadata[k]

    return final_headers

# builds the query arg string
def query_args_hash_to_string(query_args):
    query_string = ""
    pairs = []
    for k, v in query_args.items():
        piece = k
        if v != None:
            piece += "=%s" % urlquote(str(v))
        pairs.append(piece)

    return '&'.join(pairs)


class CallingFormat:
    PATH = 1
    SUBDOMAIN = 2
    VANITY = 3

    def build_url_base(protocol, server, port, bucket, calling_format):
        url_base = '%s://' % protocol

        if bucket == '':
            url_base += server
        elif calling_format == CallingFormat.SUBDOMAIN:
            url_base += "%s.%s" % (bucket, server)
        elif calling_format == CallingFormat.VANITY:
            url_base += bucket
        else:
            url_base += server

        if port not in (80, 443):
            url_base += ":%s" % port

        if (bucket != '') and (calling_format == CallingFormat.PATH):
            url_base += "/%s" % bucket

        return url_base

    build_url_base = staticmethod(build_url_base)



class Location:
    DEFAULT = None
    EU = 'EU'



class AWSAuthConnection:
    def __init__(self, aws_access_key_id, aws_secret_access_key, is_secure=True,
            server=DEFAULT_HOST, port=None, calling_format=CallingFormat.SUBDOMAIN):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.is_secure = is_secure
        self.server = server
        self.port = port
        self.calling_format = calling_format

    def create_bucket(self, bucket, headers={}):
        return Response(self._make_request('PUT', bucket, '', {}, headers))

    def create_located_bucket(self, bucket, location=Location.DEFAULT, headers={}):
        if location == Location.DEFAULT:
            body = ""
        else:
            body = "<CreateBucketConstraint><LocationConstraint>" + \
                   location + \
                   "</LocationConstraint></CreateBucketConstraint>"
        return Response(self._make_request('PUT', bucket, '', {}, headers, body))

    def check_bucket_exists(self, bucket):
        return self._make_request('HEAD', bucket, '', {}, {})

    def list_bucket(self, bucket, options={}, headers={}):
        return ListBucketResponse(self._make_request('GET', bucket, '', options, headers))

    def delete_bucket(self, bucket, headers={}):
        return Response(self._make_request('DELETE', bucket, '', {}, headers))

    def put(self, bucket, key, object, headers={}):
        if not isinstance(object, S3Object):
            object = S3Object(object)

        return Response(
                self._make_request(
                    'PUT',
                    bucket,
                    key,
                    {},
                    headers,
                    object.data,
                    object.metadata))

    def get(self, bucket, key, headers={}):
        return GetResponse(
                self._make_request('GET', bucket, key, {}, headers))

    def delete(self, bucket, key, headers={}):
        return Response(
                self._make_request('DELETE', bucket, key, {}, headers))

    def get_bucket_logging(self, bucket, headers={}):
        return GetResponse(self._make_request('GET', bucket, '', { 'logging': None }, headers))

    def put_bucket_logging(self, bucket, logging_xml_doc, headers={}):
        return Response(self._make_request('PUT', bucket, '', { 'logging': None }, headers, logging_xml_doc))

    def get_bucket_acl(self, bucket, headers={}):
        return self.get_acl(bucket, '', headers)

    def get_acl(self, bucket, key, headers={}):
        return GetResponse(
                self._make_request('GET', bucket, key, { 'acl': None }, headers))

    def put_bucket_acl(self, bucket, acl_xml_document, headers={}):
        return self.put_acl(bucket, '', acl_xml_document, headers)

    def put_acl(self, bucket, key, acl_xml_document, headers={}):
        return Response(
                self._make_request(
                    'PUT',
                    bucket,
                    key,
                    { 'acl': None },
                    headers,
                    acl_xml_document))

    def list_all_my_buckets(self, headers={}):
        return ListAllMyBucketsResponse(self._make_request('GET', '', '', {}, headers))

    def get_bucket_location(self, bucket):
        return LocationResponse(self._make_request('GET', bucket, '', {'location' : None}))

    # end public methods

    def _make_request(self, method, bucket='', key='', query_args={}, headers={}, data='', metadata={}):
        server = ''
        if bucket == '':
            server = self.server
        elif self.calling_format == CallingFormat.SUBDOMAIN:
            server = "%s.%s" % (bucket, self.server)
        elif self.calling_format == CallingFormat.VANITY:
            server = bucket
        else:
            server = self.server

        path = ''

        if (bucket != '') and (self.calling_format == CallingFormat.PATH):
            path += "/%s" % bucket

        # add the slash after the bucket regardless
        # the key will be appended if it is non-empty
        path += "/%s" % urlquote(key, '/')


        # build the path_argument string
        # add the ? in all cases since 
        # signature and credentials follow path args
        if len(query_args):
            path += "?" + query_args_hash_to_string(query_args)

        is_secure = self.is_secure
        host = "%s:%d" % (server, self.port)
        while True:
            if (is_secure):
                connection = httplib.HTTPSConnection(host)
            else:
                connection = httplib.HTTPConnection(host)

            final_headers = merge_meta(headers, metadata);
            # add auth header
            self._add_aws_auth_header(final_headers, method, bucket, key, query_args)

            connection.request(method, path, data, final_headers)
            resp = connection.getresponse()
            if resp.status < 300 or resp.status >= 400:
                return resp
            # handle redirect
            location = resp.getheader('location')
            if not location:
                return resp
            # (close connection)
            resp.read()
            scheme, host, path, params, query, fragment \
                    = urlparse.urlparse(location)
            if scheme == "http":    is_secure = True
            elif scheme == "https": is_secure = False
            else: raise S3Exception("Not http/https: " + location)
            if query: path += "?" + query
            # retry with redirect

    def _add_aws_auth_header(self, headers, method, bucket, key, query_args):
        if not 'Date' in headers:
            headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

        c_string = canonical_string(method, bucket, key, query_args, headers)
        headers['Authorization'] = \
            "AWS %s:%s" % (self.aws_access_key_id, encode(self.aws_secret_access_key, c_string))


class QueryStringAuthGenerator:
    # by default, expire in 1 minute
    DEFAULT_EXPIRES_IN = 60

    def __init__(self, aws_access_key_id, aws_secret_access_key, is_secure=True,
                 server=DEFAULT_HOST, port=None, calling_format=CallingFormat.SUBDOMAIN):

        if not port:
            port = PORTS_BY_SECURITY[is_secure]

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        if (is_secure):
            self.protocol = 'https'
        else:
            self.protocol = 'http'

        self.is_secure = is_secure
        self.server = server
        self.port = port
        self.calling_format = calling_format
        self.__expires_in = QueryStringAuthGenerator.DEFAULT_EXPIRES_IN
        self.__expires = None

        # for backwards compatibility with older versions
        self.server_name = "%s:%s" % (self.server, self.port)

    def set_expires_in(self, expires_in):
        self.__expires_in = expires_in
        self.__expires = None

    def set_expires(self, expires):
        self.__expires = expires
        self.__expires_in = None

    def create_bucket(self, bucket, headers={}):
        return self.generate_url('PUT', bucket, '', {}, headers)

    def list_bucket(self, bucket, options={}, headers={}):
        return self.generate_url('GET', bucket, '', options, headers)

    def delete_bucket(self, bucket, headers={}):
        return self.generate_url('DELETE', bucket, '', {}, headers)

    def put(self, bucket, key, object, headers={}):
        if not isinstance(object, S3Object):
            object = S3Object(object)

        return self.generate_url(
                'PUT',
                bucket,
                key,
                {},
                merge_meta(headers, object.metadata))

    def get(self, bucket, key, headers={}):
        return self.generate_url('GET', bucket, key, {}, headers)

    def delete(self, bucket, key, headers={}):
        return self.generate_url('DELETE', bucket, key, {}, headers)

    def get_bucket_logging(self, bucket, headers={}):
        return self.generate_url('GET', bucket, '', { 'logging': None }, headers)

    def put_bucket_logging(self, bucket, logging_xml_doc, headers={}):
        return self.generate_url('PUT', bucket, '', { 'logging': None }, headers)

    def get_bucket_acl(self, bucket, headers={}):
        return self.get_acl(bucket, '', headers)

    def get_acl(self, bucket, key='', headers={}):
        return self.generate_url('GET', bucket, key, { 'acl': None }, headers)

    def put_bucket_acl(self, bucket, acl_xml_document, headers={}):
        return self.put_acl(bucket, '', acl_xml_document, headers)

    # don't really care what the doc is here.
    def put_acl(self, bucket, key, acl_xml_document, headers={}):
        return self.generate_url('PUT', bucket, key, { 'acl': None }, headers)

    def list_all_my_buckets(self, headers={}):
        return self.generate_url('GET', '', '', {}, headers)

    def make_bare_url(self, bucket, key=''):
        full_url = self.generate_url(self, bucket, key)
        return full_url[:full_url.index('?')]

    def generate_url(self, method, bucket='', key='', query_args={}, headers={}):
        expires = 0
        if self.__expires_in != None:
            expires = int(time.time() + self.__expires_in)
        elif self.__expires != None:
            expires = int(self.__expires)
        else:
            raise S3Exception("Invalid expires state")

        canonical_str = canonical_string(method, bucket, key, query_args, headers, expires)
        encoded_canonical = encode(self.aws_secret_access_key, canonical_str)

        url = CallingFormat.build_url_base(self.protocol, self.server, self.port, bucket, self.calling_format)

        url += "/%s" % urlquote(key, '/')

        query_args['Signature'] = encoded_canonical
        query_args['Expires'] = expires
        query_args['AWSAccessKeyId'] = self.aws_access_key_id

        url += "?%s" % query_args_hash_to_string(query_args)

        return url


class S3Object:
    def __init__(self, data, metadata={}):
        self.data = data
        self.metadata = metadata

class Owner:
    def __init__(self, id='', display_name=''):
        self.id = id
        self.display_name = display_name

class ListEntry:
    def __init__(self, key='', last_modified=None, etag='', size=0, storage_class='', owner=None):
        self.key = key
        self.last_modified = last_modified
        self.etag = etag
        self.size = size
        self.storage_class = storage_class
        self.owner = owner

class CommonPrefixEntry:
    def __init(self, prefix=''):
        self.prefix = prefix

class Bucket:
    def __init__(self, name='', creation_date=''):
        self.name = name
        self.creation_date = creation_date

class Response:
    def __init__(self, http_response):
        self.http_response = http_response
        # you have to do this read, even if you don't expect a body.
        # otherwise, the next request fails.
        self.body = http_response.read()
        if http_response.status >= 300 and self.body:
            self.message = self.body
        else:
            self.message = "%03d %s" % (http_response.status, http_response.reason)



class ListBucketResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status < 300:
            handler = ListBucketHandler()
            xml.sax.parseString(self.body, handler)
            self.entries = handler.entries
            self.common_prefixes = handler.common_prefixes
            self.name = handler.name
            self.marker = handler.marker
            self.prefix = handler.prefix
            self.is_truncated = handler.is_truncated
            self.delimiter = handler.delimiter
            self.max_keys = handler.max_keys
            self.next_marker = handler.next_marker
        else:
            self.entries = []

class ListAllMyBucketsResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status < 300:
            handler = ListAllMyBucketsHandler()
            xml.sax.parseString(self.body, handler)
            self.entries = handler.entries
        else:
            self.entries = []

class GetResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        response_headers = http_response.msg   # older pythons don't have getheaders
        metadata = self.get_aws_metadata(response_headers)
        self.object = S3Object(self.body, metadata)

    def get_aws_metadata(self, headers):
        metadata = {}
        for hkey in headers.keys():
            if hkey.lower().startswith(METADATA_PREFIX):
                metadata[hkey[len(METADATA_PREFIX):]] = headers[hkey]
                del headers[hkey]

        return metadata

class LocationResponse(Response):
    def __init__(self, http_response):
        Response.__init__(self, http_response)
        if http_response.status < 300:
            handler = LocationHandler()
            xml.sax.parseString(self.body, handler)
            self.location = handler.location

class ListBucketHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.entries = []
        self.curr_entry = None
        self.curr_text = ''
        self.common_prefixes = []
        self.curr_common_prefix = None
        self.name = ''
        self.marker = ''
        self.prefix = ''
        self.is_truncated = False
        self.delimiter = ''
        self.max_keys = 0
        self.next_marker = ''
        self.is_echoed_prefix_set = False

    def startElement(self, name, attrs):
        if name == 'Contents':
            self.curr_entry = ListEntry()
        elif name == 'Owner':
            self.curr_entry.owner = Owner()
        elif name == 'CommonPrefixes':
            self.curr_common_prefix = CommonPrefixEntry()


    def endElement(self, name):
        if name == 'Contents':
            self.entries.append(self.curr_entry)
        elif name == 'CommonPrefixes':
            self.common_prefixes.append(self.curr_common_prefix)
        elif name == 'Key':
            self.curr_entry.key = self.curr_text
        elif name == 'LastModified':
            self.curr_entry.last_modified = self.curr_text
        elif name == 'ETag':
            self.curr_entry.etag = self.curr_text
        elif name == 'Size':
            self.curr_entry.size = int(self.curr_text)
        elif name == 'ID':
            self.curr_entry.owner.id = self.curr_text
        elif name == 'DisplayName':
            self.curr_entry.owner.display_name = self.curr_text
        elif name == 'StorageClass':
            self.curr_entry.storage_class = self.curr_text
        elif name == 'Name':
            self.name = self.curr_text
        elif name == 'Prefix' and self.is_echoed_prefix_set:
            self.curr_common_prefix.prefix = self.curr_text
        elif name == 'Prefix':
            self.prefix = self.curr_text
            self.is_echoed_prefix_set = True
        elif name == 'Marker':
            self.marker = self.curr_text
        elif name == 'IsTruncated':
            self.is_truncated = self.curr_text == 'true'
        elif name == 'Delimiter':
            self.delimiter = self.curr_text
        elif name == 'MaxKeys':
            self.max_keys = int(self.curr_text)
        elif name == 'NextMarker':
            self.next_marker = self.curr_text

        self.curr_text = ''

    def characters(self, content):
        self.curr_text += content


class ListAllMyBucketsHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.entries = []
        self.curr_entry = None
        self.curr_text = ''

    def startElement(self, name, attrs):
        if name == 'Bucket':
            self.curr_entry = Bucket()

    def endElement(self, name):
        if name == 'Name':
            self.curr_entry.name = self.curr_text
        elif name == 'CreationDate':
            self.curr_entry.creation_date = self.curr_text
        elif name == 'Bucket':
            self.entries.append(self.curr_entry)

    def characters(self, content):
        self.curr_text = content


class LocationHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.location = None
        self.state = 'init'

    def startElement(self, name, attrs):
        if self.state == 'init':
            if name == 'LocationConstraint':
                self.state = 'tag_location'
                self.location = ''
            else: self.state = 'bad'
        else: self.state = 'bad'

    def endElement(self, name):
        if self.state == 'tag_location' and name == 'LocationConstraint':
            self.state = 'done'
        else: self.state = 'bad'

    def characters(self, content):
        if self.state == 'tag_location':
            self.location += content

########NEW FILE########
__FILENAME__ = cb_s3_sync_media
from datetime import datetime
from optparse import make_option
import os
import re
import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from cuddlybuddly.storage.s3.exceptions import S3Error
from cuddlybuddly.storage.s3.storage import S3Storage


output_length = 0
def output(text, options, min_verbosity=1, rtrn=False, nl=False):
    if int(options['verbosity']) >= min_verbosity:
        global output_length
        if rtrn:
            if len(text) < output_length:
                text = text + ' ' * (output_length - len(text) - 1)
            text = '\r' + text
            output_length = 0
        output_length += len(text)
        if nl:
            output_length = 0
            text = text + '\n'
        sys.stdout.write(text)
        sys.stdout.flush()


def walk(dir, options):
    to_sync = []
    for root, dirs, files in os.walk(dir):
        for dir in dirs:
            for pattern in options['exclude']:
                if pattern.search(os.path.join(root, dir)):
                    dirs.remove(dir)
        for file in files:
            file = os.path.join(root, file)
            exclude = False
            for pattern in options['exclude']:
                if pattern.search(file):
                    exclude = True
                    break
            if exclude:
                continue
            # Because the followlinks parameter is only in >= 2.6 we have to
            # follow symlinks ourselves.
            if os.path.isdir(file) and os.path.islink(file):
                to_sync = to_sync + walk(file)
            else:
                to_sync.append(file)
    return to_sync


class Command(BaseCommand):
    help = 'Sync folder with your S3 bucket'
    option_list = BaseCommand.option_list + (
        make_option('-c', '--cache',
            action='store_true',
            dest='cache',
            default=False,
            help='Whether or not to check the cache for the modified times'),
        make_option('-d', '--dir',
            action='store',
            dest='dir',
            type='string',
            default=None,
            help='Directory to sync to S3'),
        make_option('-e', '--exclude',
            action='store',
            dest='exclude',
            type='string',
            default=None,
            help='A comma separated list of regular expressions of files and folders to skip'),
        make_option('-f', '--force',
            action='store_true',
            dest='force',
            default=False,
            help='Upload all files even if the version on S3 is up to date'),
        make_option('-p', '--prefix',
            action='store',
            dest='prefix',
            type='string',
            default='',
            help='Prefix to prepend to uploaded files'),
    )

    def handle(self, *args, **options):
        if options['dir'] is None:
            options['dir'] = settings.MEDIA_ROOT
        if options['exclude'] is None:
            options['exclude'] = getattr(
                settings,
                'CUDDLYBUDDLY_STORAGE_S3_SYNC_EXCLUDE',
                ['\.svn$', '\.git$', '\.hg$', 'Thumbs\.db$', '\.DS_Store$']
            )
        else:
            options['exclude'] = options['exclude'].split(',')
        exclude = []
        for pattern in options['exclude']:
            exclude.append(re.compile(pattern))
        options['exclude'] = exclude

        files = walk(options['dir'], options)
        skipped = uploaded = 0
        output(
            'Uploaded: %s, Skipped: %s, Total: %s/%s' % (0, 0, 0, len(files)),
            options,
            rtrn=True # Needed to correctly calculate padding
        )
        storage = S3Storage()
        for file in files:
            s3name = os.path.join(
                options['prefix'],
                os.path.relpath(file, options['dir'])
            )
            try:
                mtime = storage.modified_time(s3name, force_check=not options['cache'])
            except S3Error:
                mtime = None
            if options['force'] or mtime is None or \
               mtime < datetime.fromtimestamp(os.path.getmtime(file)):
                if mtime:
                    storage.delete(s3name)
                fh = open(file, 'rb')
                output(' Uploading %s...' % s3name, options)
                storage.save(s3name, fh)
                output('Uploaded %s' % s3name, options, rtrn=True, nl=True)
                fh.close()
                uploaded += 1
            else:
                output(
                    'Skipped %s because it hasn\'t been modified' % s3name,
                    options,
                    min_verbosity=2,
                    rtrn=True,
                    nl=True
                )
                skipped += 1
            output(
                'Uploaded: %s, Skipped: %s, Total: %s/%s'
                    % (uploaded, skipped, uploaded + skipped, len(files)),
                options,
                rtrn=True
            )
        output('', options, nl=True)

########NEW FILE########
__FILENAME__ = cb_s3_sync_static
from django.conf import settings
from cuddlybuddly.storage.s3.management.commands.cb_s3_sync_media import \
    Command as BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        if options['dir'] is None:
            options['dir'] = getattr(settings, 'STATIC_ROOT', None)
        return super(Command, self).handle(*args, **options)

########NEW FILE########
__FILENAME__ = middleware
try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local


_thread_locals = local()


def request_is_secure():
    return getattr(_thread_locals, 'cb_request_is_secure', None)


class ThreadLocals(object):
    def process_request(self, request):
        if request.is_secure() or \
           getattr(request.META, 'HTTP_X_FORWARDED_SSL', 'off') == 'on':
            secure = True
        else:
            secure = False
        _thread_locals.cb_request_is_secure = secure

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = storage
from calendar import timegm
from datetime import datetime
from email.utils import parsedate
from gzip import GzipFile
import mimetypes
import os
import re
from StringIO import StringIO # Don't use cStringIO as it's not unicode safe
import sys
from urlparse import urljoin
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.encoding import iri_to_uri
from django.utils.importlib import import_module
from cuddlybuddly.storage.s3 import CallingFormat
from cuddlybuddly.storage.s3.exceptions import S3Error
from cuddlybuddly.storage.s3.lib import AWSAuthConnection
from cuddlybuddly.storage.s3.middleware import request_is_secure


ACCESS_KEY_NAME = 'AWS_ACCESS_KEY_ID'
SECRET_KEY_NAME = 'AWS_SECRET_ACCESS_KEY'
HEADERS = 'AWS_HEADERS'


class S3Storage(Storage):
    """Amazon Simple Storage Service"""

    static = False

    def __init__(self, bucket=None, access_key=None, secret_key=None,
                 headers=None, calling_format=None, cache=None, base_url=None):
        if bucket is None:
            bucket = settings.AWS_STORAGE_BUCKET_NAME
        if calling_format is None:
           calling_format = getattr(settings, 'AWS_CALLING_FORMAT',
                                    CallingFormat.SUBDOMAIN)
        self.bucket = bucket

        if not access_key and not secret_key:
            access_key, secret_key = self._get_access_keys()

        self.connection = AWSAuthConnection(access_key, secret_key,
                            calling_format=calling_format)

        default_headers = getattr(settings, HEADERS, [])
        # Backwards compatibility for original format from django-storages
        if isinstance(default_headers, dict):
            default_headers = [('.*', default_headers)]
        if headers:
            # Headers passed to __init__ take precedence over headers from
            # settings file.
            default_headers = list(headers) + list(default_headers)
        self.headers = []
        for value in default_headers:
            self.headers.append((re.compile(value[0]), value[1]))

        if cache is not None:
            self.cache = cache
        else:
            cache = getattr(settings, 'CUDDLYBUDDLY_STORAGE_S3_CACHE', None)
            if cache is not None:
                self.cache = self._get_cache_class(cache)()
            else:
                self.cache = None

        if base_url is None:
            if not self.static:
                base_url = settings.MEDIA_URL
            else:
                base_url = settings.STATIC_URL
        self.base_url = base_url

    def _get_cache_class(self, import_path=None):
        try:
            dot = import_path.rindex('.')
        except ValueError:
            raise ImproperlyConfigured("%s isn't a cache module." % import_path)
        module, classname = import_path[:dot], import_path[dot+1:]
        try:
            mod = import_module(module)
        except ImportError, e:
            raise ImproperlyConfigured('Error importing cache module %s: "%s"' % (module, e))
        try:
            return getattr(mod, classname)
        except AttributeError:
            raise ImproperlyConfigured('Cache module "%s" does not define a "%s" class.' % (module, classname))

    def _store_in_cache(self, name, response):
        size = int(response.getheader('Content-Length'))
        date = response.getheader('Last-Modified')
        date = timegm(parsedate(date))
        self.cache.save(name, size=size, mtime=date)

    def _get_access_keys(self):
        access_key = getattr(settings, ACCESS_KEY_NAME, None)
        secret_key = getattr(settings, SECRET_KEY_NAME, None)
        if (access_key or secret_key) and (not access_key or not secret_key):
            access_key = os.environ.get(ACCESS_KEY_NAME)
            secret_key = os.environ.get(SECRET_KEY_NAME)

        if access_key and secret_key:
            # Both were provided, so use them
            return access_key, secret_key

        return None, None

    def _get_connection(self):
        return AWSAuthConnection(*self._get_access_keys())

    def _put_file(self, name, content):
        name = self._path(name)
        placeholder = False
        if self.cache:
            if not self.cache.exists(name):
                self.cache.save(name, 0, 0)
                placedholder = True
        content_type = mimetypes.guess_type(name)[0] or "application/x-octet-stream"
        headers = {}
        for pattern in self.headers:
            if pattern[0].match(name):
                headers = pattern[1].copy()
                break
        file_pos = content.tell()
        content.seek(0, 2)
        content_length = content.tell()
        content.seek(0)
        gz_cts = getattr(
            settings,
            'CUDDLYBUDDLY_STORAGE_S3_GZIP_CONTENT_TYPES',
            (
                'text/css',
                'application/javascript',
                'application/x-javascript'
            )
        )
        gz_content = None
        if content_length > 1024 and content_type in gz_cts:
            gz_content = StringIO()
            gzf = GzipFile(mode='wb', fileobj=gz_content)
            gzf.write(content.read())
            content.seek(0)
            gzf.close()
            gz_content.seek(0, 2)
            gz_content_length = gz_content.tell()
            gz_content.seek(0)
            if gz_content_length < content_length:
                content_length = gz_content_length
                headers.update({
                    'Content-Encoding': 'gzip'
                })
            else:
                gz_content = None
        headers.update({
            'Content-Type': content_type,
            'Content-Length': str(content_length)
        })
        # Httplib in < 2.6 doesn't accept file like objects. Meanwhile in
        # >= 2.7 it will try to join a content str object with the headers which
        # results in encoding problems.
        if sys.version_info[0] == 2 and sys.version_info[1] < 6:
            content_to_send = gz_content.read() if gz_content is not None else content.read()
        else:
            content_to_send = gz_content if gz_content is not None else content
        response = self.connection.put(self.bucket, name, content_to_send, headers)
        content.seek(file_pos)
        if response.http_response.status != 200:
            if placeholder:
                self.cache.remove(name)
            raise S3Error(response.message)
        if self.cache:
            date = response.http_response.getheader('Date')
            date = timegm(parsedate(date))
            self.cache.save(name, size=content_length, mtime=date)

    def _open(self, name, mode='rb'):
        remote_file = S3StorageFile(name, self, mode=mode)
        return remote_file

    def _read(self, name, start_range=None, end_range=None):
        name = self._path(name)
        headers, range_ = {}, None
        if start_range is not None and end_range is not None:
            range_ = '%s-%s' % (start_range, end_range)
        elif start_range is not None:
            range_ = '%s' % start_range
        if range_ is not None:
            headers = {'Range': 'bytes=%s' % range_}
        response = self.connection.get(self.bucket, name, headers)
        valid_responses = [200]
        if start_range is not None or end_range is not None:
            valid_responses.append(206)
        if response.http_response.status not in valid_responses:
            raise S3Error(response.message)
        headers = response.http_response.msg
        data = response.object.data

        if headers.get('Content-Encoding') == 'gzip':
            gzf = GzipFile(mode='rb', fileobj=StringIO(data))
            data = gzf.read()
            gzf.close()

        return data, headers.get('etag', None), headers.get('content-range', None)

    def _save(self, name, content):
        self._put_file(name, content)
        return name

    def delete(self, name):
        name = self._path(name)
        response = self.connection.delete(self.bucket, name)
        if response.http_response.status != 204:
            raise S3Error(response.message)
        if self.cache:
            self.cache.remove(name)

    def exists(self, name, force_check=False):
        if not name:
            return False
        name = self._path(name)
        if self.cache and not force_check:
            exists = self.cache.exists(name)
            if exists is not None:
                return exists
        response = self.connection._make_request('HEAD', self.bucket, name)
        exists = response.status == 200
        if self.cache and exists:
            self._store_in_cache(name, response)
        return exists

    def size(self, name, force_check=False):
        name = self._path(name)
        if self.cache and not force_check:
            size = self.cache.size(name)
            if size is not None:
                return size
        response = self.connection._make_request('HEAD', self.bucket, name)
        content_length = response.getheader('Content-Length')
        if self.cache:
            self._store_in_cache(name, response)
        return content_length and int(content_length) or 0

    def modified_time(self, name, force_check=False):
        name = self._path(name)
        if self.cache and not force_check:
            last_modified = self.cache.modified_time(name)
            if last_modified:
                return datetime.fromtimestamp(last_modified)
        response = self.connection._make_request('HEAD', self.bucket, name)
        if response.status == 404:
            raise S3Error("Cannot find the file specified: '%s'" % name)
        last_modified = timegm(parsedate(response.getheader('Last-Modified')))
        if self.cache:
            self._store_in_cache(name, response)
        return datetime.fromtimestamp(last_modified)

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        name = self._path(name)
        if request_is_secure():
            if hasattr(self.base_url, 'https'):
                url = self.base_url.https()
            else:
                if hasattr(self.base_url, 'match'):
                    url = self.base_url.match(name)
                else:
                    url = self.base_url
                url = url.replace('http://', 'https://')
        else:
            if hasattr(self.base_url, 'match'):
                url = self.base_url.match(name)
            else:
                url = self.base_url
            url = url.replace('https://', 'http://')
        return urljoin(url, iri_to_uri(name))

    def listdir(self, path):
        path = self._path(path)
        if not path.endswith('/'):
            path = path+'/'
        directories, files = [], []
        options = {'prefix': path, 'delimiter': '/'}
        response = self.connection.list_bucket(self.bucket, options=options)
        for prefix in response.common_prefixes:
            directories.append(prefix.prefix.replace(path, '').strip('/'))
        for entry in response.entries:
            files.append(entry.key.replace(path, ''))
        return directories, files

    def _path(self, name):
        name = name.replace('\\', '/')
        # Because the S3 lib just loves to add slashes
        if name.startswith('/'):
            name = name[1:]
        return name


class S3StorageFile(File):
    def __init__(self, name, storage, mode):
        self.name = name
        self._storage = storage
        self.mode = mode
        self._is_dirty = False
        self.file = StringIO()
        self.start_range = 0

    @property
    def size(self):
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self.name)
        return self._size

    def _empty_read(self):
        self.file = StringIO('')
        return self.file.getvalue()

    def read(self, num_bytes=None):
        # Reading past the file size results in a 416 (InvalidRange) error from
        # S3, but accessing the size when not using chunked reading causes an
        # unnecessary HEAD call.
        if self.start_range and self.start_range >= self.size:
            return self._empty_read()

        args = []

        if num_bytes:
            if self.start_range < 0:
                offset = self.size
            else:
                offset = 0
            args = [self.start_range + offset, self.start_range + num_bytes - 1 + offset]
        elif self.start_range:
            args = [self.start_range, '']

        try:
            data, etags, content_range = self._storage._read(self.name, *args)
        except S3Error, e:
            # Catch InvalidRange for 0 length reads. Perhaps we should be
            # catching all kinds of exceptions...
            if '<Code>InvalidRange</Code>' in unicode(e):
                return self._empty_read()
            raise
        if content_range is not None:
            current_range, size = content_range.split(' ', 1)[1].split('/', 1)
            start_range, end_range = current_range.split('-', 1)
            self._size, self.start_range = int(size), int(end_range) + 1

        self.file = StringIO(data)
        return self.file.getvalue()

    def write(self, content):
        if 'w' not in self.mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = StringIO(content)
        self._is_dirty = True

    def close(self):
        if self._is_dirty:
            self._storage._put_file(self.name, self.file)
            self._size = len(self.file.getvalue())
        self.file.close()

    def seek(self, pos, mode=0):
        self.file.seek(pos, mode)
        if mode == 0:
            self.start_range = pos
        elif mode == 1:
            self.start_range += pos
        elif mode == 2:
            # While S3 does support negative positions, using them makes tell()
            # unreliable. Getting size is a pretty fast HEAD anyway.
            self.start_range = self.size + pos

    def tell(self):
        return self.start_range


class S3StorageStatic(S3Storage):
    """
    For use with ``STATICFILES_STORAGE`` and ``STATIC_URL``.
    """
    static = True

########NEW FILE########
__FILENAME__ = s3_tags
from urlparse import urljoin
from django import template
from django.conf import settings
from django.utils.encoding import iri_to_uri
from cuddlybuddly.storage.s3.utils import CloudFrontURLs


register = template.Library()


class S3MediaURLNode(template.Node):
    def __init__(self, static, path, as_var=None):
        self.static = static
        self.path = template.Variable(path)
        self.as_var = as_var

    def render(self, context):
        path = self.path.resolve(context)
        if self.static:
            base_url = settings.STATIC_URL
        else:
            base_url = settings.MEDIA_URL
        if not isinstance(base_url, CloudFrontURLs):
            base_url = CloudFrontURLs(base_url)
        url = base_url.get_url(path)

        if self.as_var:
            context[self.as_var] = url
            return ''
        else:
            return url


def do_s3_media_url(parser, token, static=False):
    """
    This is for use with ``CloudFrontURLs`` and will return the appropriate url
    if a match is found.

    Usage::

        {% s3_media_url path %}


    For ``HTTPS``, the ``cuddlybuddly.storage.s3.middleware.ThreadLocals``
    middleware must also be used.
    """

    split_token = token.split_contents()
    vars = []
    as_var = False
    for k, v in enumerate(split_token[1:]):
        if v == 'as':
            try:
                while len(vars) < 1:
                    vars.append(None)
                vars.append(split_token[k+2])
                as_var = True
            except IndexError:
                raise template.TemplateSyntaxError, \
                      "%r tag requires a variable name to attach to" \
                      % split_token[0]
            break
        else:
            vars.append(v)

    if (not as_var and len(vars) not in (1,)) \
       or (as_var and len(vars) not in (2,)):
        raise template.TemplateSyntaxError, \
              "%r tag requires a path or url" \
              % token.contents.split()[0]

    return S3MediaURLNode(static, *vars)


do_s3_media_url = register.tag('s3_media_url', do_s3_media_url)


def do_s3_static_url(parser, token):
    """
    This is the same as ``s3_media_url`` but defaults to ``STATIC_URL`` instead.
    """
    return do_s3_media_url(parser, token, static=True)


do_s3_static_url = register.tag('s3_static_url', do_s3_static_url)

########NEW FILE########
__FILENAME__ = s3test
#!/usr/bin/env python

# This software code is made available "AS IS" without warranties of any
# kind.  You may copy, display, modify and redistribute the software
# code either by itself or as incorporated into your code; provided that
# you do not remove any proprietary notices.  Your use of this software
# code is at your own risk and you waive any claim against Amazon
# Digital Services, Inc. or its affiliates with respect to your use of
# this software code. (c) 2006-2007 Amazon Digital Services, Inc. or its
# affiliates.

# Incorporated Django settings.
#
# 409 error fix - you can't create and delete the same bucket on US and EU
# servers within a short time. Now appeds location to bucket name.
#
# (c) 2009 Kyle MacFarlane

import unittest
import httplib
from django.conf import settings
from cuddlybuddly.storage.s3 import lib as S3

AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY

# for subdomains (bucket.s3.amazonaws.com),
# the bucket name must be lowercase since DNS is case-insensitive
BUCKET_NAME = "%s-test-bucket" % AWS_ACCESS_KEY_ID.lower();


class TestAWSAuthConnection(unittest.TestCase):
    def setUp(self):
        self.conn = S3.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

    # test all operations for both regular and vanity domains
    # regular: http://s3.amazonaws.com/bucket/key
    # subdomain: http://bucket.s3.amazonaws.com/key
    # testing pure vanity domains (http://<vanity domain>/key) is not covered here
    # but is possible with some additional setup (set the server in @conn to your vanity domain)

    def test_subdomain_default(self):
        self.run_tests(S3.CallingFormat.SUBDOMAIN, S3.Location.DEFAULT)

    def test_subdomain_eu(self):
        self.run_tests(S3.CallingFormat.SUBDOMAIN, S3.Location.EU)

    def test_path_default(self):
        self.run_tests(S3.CallingFormat.PATH, S3.Location.DEFAULT)


    def run_tests(self, calling_format, location):
        bucket_name = BUCKET_NAME+str(location).lower()
        self.conn.calling_format = calling_format

        response = self.conn.create_located_bucket(bucket_name, location)
        self.assertEquals(response.http_response.status, 200, 'create bucket')

        response = self.conn.list_bucket(bucket_name)
        self.assertEquals(response.http_response.status, 200, 'list bucket')
        self.assertEquals(len(response.entries), 0, 'bucket is empty')

        text = 'this is a test'
        key = 'example.txt'

        response = self.conn.put(bucket_name, key, text)
        self.assertEquals(response.http_response.status, 200, 'put with a string argument')

        response = \
            self.conn.put(
                    bucket_name,
                    key,
                    S3.S3Object(text, {'title': 'title'}),
                    {'Content-Type': 'text/plain'})

        self.assertEquals(response.http_response.status, 200, 'put with complex argument and headers')

        response = self.conn.get(bucket_name, key)
        self.assertEquals(response.http_response.status, 200, 'get object')
        self.assertEquals(response.object.data, text, 'got right data')
        self.assertEquals(response.object.metadata, { 'title': 'title' }, 'metadata is correct')
        self.assertEquals(int(response.http_response.getheader('Content-Length')), len(text), 'got content-length header')

        title_with_spaces = " \t  title with leading and trailing spaces     "
        response = \
            self.conn.put(
                    bucket_name,
                    key,
                    S3.S3Object(text, {'title': title_with_spaces}),
                    {'Content-Type': 'text/plain'})

        self.assertEquals(response.http_response.status, 200, 'put with headers with spaces')

        response = self.conn.get(bucket_name, key)
        self.assertEquals(response.http_response.status, 200, 'get object')
        self.assertEquals(
                response.object.metadata,
                { 'title': title_with_spaces.strip() },
                'metadata with spaces is correct')

        # delimited list tests
        inner_key = 'test/inner.txt'
        last_key = 'z-last-key.txt'
        response = self.conn.put(bucket_name, inner_key, text)
        self.assertEquals(response.http_response.status, 200, 'put inner key')

        response = self.conn.put(bucket_name, last_key, text)
        self.assertEquals(response.http_response.status, 200, 'put last key')

        response = self.do_delimited_list(bucket_name, False, {'delimiter': '/'}, 2, 1, 'root list')

        response = self.do_delimited_list(bucket_name, True, {'max-keys': 1, 'delimiter': '/'}, 1, 0, 'root list with max keys of 1', 'example.txt')

        response = self.do_delimited_list(bucket_name, True, {'max-keys': 2, 'delimiter': '/'}, 1, 1, 'root list with max keys of 2, page 1', 'test/')

        marker = response.next_marker

        response = self.do_delimited_list(bucket_name, False, {'marker': marker, 'max-keys': 2, 'delimiter': '/'}, 1, 0, 'root list with max keys of 2, page 2')

        response = self.do_delimited_list(bucket_name, False, {'prefix': 'test/', 'delimiter': '/'}, 1, 0, 'test/ list')

        response = self.conn.delete(bucket_name, inner_key)
        self.assertEquals(response.http_response.status, 204, 'delete %s' % inner_key)

        response = self.conn.delete(bucket_name, last_key)
        self.assertEquals(response.http_response.status, 204, 'delete %s' % last_key)


        weird_key = '&=//%# ++++'

        response = self.conn.put(bucket_name, weird_key, text)
        self.assertEquals(response.http_response.status, 200, 'put weird key')

        response = self.conn.get(bucket_name, weird_key)
        self.assertEquals(response.http_response.status, 200, 'get weird key')

        response = self.conn.get_acl(bucket_name, key)
        self.assertEquals(response.http_response.status, 200, 'get acl')

        acl = response.object.data

        response = self.conn.put_acl(bucket_name, key, acl)
        self.assertEquals(response.http_response.status, 200, 'put acl')

        response = self.conn.get_bucket_acl(bucket_name)
        self.assertEquals(response.http_response.status, 200, 'get bucket acl')

        bucket_acl = response.object.data

        response = self.conn.put_bucket_acl(bucket_name, bucket_acl)
        self.assertEquals(response.http_response.status, 200, 'put bucket acl')

        response = self.conn.get_bucket_acl(bucket_name)
        self.assertEquals(response.http_response.status, 200, 'get bucket logging')

        bucket_logging = response.object.data

        response = self.conn.put_bucket_acl(bucket_name, bucket_logging)
        self.assertEquals(response.http_response.status, 200, 'put bucket logging')

        response = self.conn.list_bucket(bucket_name)
        self.assertEquals(response.http_response.status, 200, 'list bucket')
        entries = response.entries
        self.assertEquals(len(entries), 2, 'got back right number of keys')
        # depends on weird_key < key
        self.assertEquals(entries[0].key, weird_key, 'first key is right')
        self.assertEquals(entries[1].key, key, 'second key is right')

        response = self.conn.list_bucket(bucket_name, {'max-keys': 1})
        self.assertEquals(response.http_response.status, 200, 'list bucket with args')
        self.assertEquals(len(response.entries), 1, 'got back right number of keys')

        for entry in entries:
            response = self.conn.delete(bucket_name, entry.key)
            self.assertEquals(response.http_response.status, 204, 'delete %s' % entry.key)

        response = self.conn.list_all_my_buckets()
        self.assertEquals(response.http_response.status, 200, 'list all my buckets')
        buckets = response.entries

        response = self.conn.delete_bucket(bucket_name)
        self.assertEquals(response.http_response.status, 204, 'delete bucket')

        response = self.conn.list_all_my_buckets()
        self.assertEquals(response.http_response.status, 200, 'list all my buckets again')

        self.assertEquals(len(response.entries), len(buckets) - 1, 'bucket count is correct')

    def verify_list_bucket_response(self, response, bucket, is_truncated, parameters, next_marker=''):
        prefix = ''
        marker = ''

        if 'prefix' in parameters:
            prefix = parameters['prefix']
        if 'marker' in parameters:
            marker = parameters['marker']

        self.assertEquals(bucket, response.name, 'bucket name should match')
        self.assertEquals(prefix, response.prefix, 'prefix should match')
        self.assertEquals(marker, response.marker, 'marker should match')
        if 'max-keys' in parameters:
            self.assertEquals(parameters['max-keys'], response.max_keys, 'max-keys should match')
        self.assertEquals(parameters['delimiter'], response.delimiter, 'delimiter should match')
        self.assertEquals(is_truncated, response.is_truncated, 'is_truncated should match')
        self.assertEquals(next_marker, response.next_marker, 'next_marker should match')

    def do_delimited_list(self, bucket_name, is_truncated, parameters, regular_expected, common_expected, test_name, next_marker=''):
        response = self.conn.list_bucket(bucket_name, parameters)
        self.assertEquals(response.http_response.status, 200, test_name)
        self.assertEquals(regular_expected, len(response.entries), 'right number of regular entries')
        self.assertEquals(common_expected, len(response.common_prefixes), 'right number of common prefixes')

        self.verify_list_bucket_response(response, bucket_name, is_truncated, parameters, next_marker)

        return response

class TestQueryStringAuthGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = S3.QueryStringAuthGenerator(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        if (self.generator.is_secure == True):
            self.connection = httplib.HTTPSConnection(self.generator.server_name)
        else:
            self.connection = httplib.HTTPConnection(self.generator.server_name)

    def check_url(self, url, method, status, message, data=''):
        if (method == 'PUT'):
            headers = { 'Content-Length': str(len(data)) }
            self.connection.request(method, url, data, headers)
        else:
            self.connection.request(method, url)

        response = self.connection.getresponse()
        self.assertEquals(response.status, status, message)

        return response.read()

    # test all operations for both regular and vanity domains
    # regular: http://s3.amazonaws.com/bucket/key
    # subdomain: http://bucket.s3.amazonaws.com/key
    # testing pure vanity domains (http://<vanity domain>/key) is not covered here
    # but is possible with some additional setup (set the server in @conn to your vanity domain)

    def test_subdomain(self):
        self.run_tests(S3.CallingFormat.SUBDOMAIN)

    def test_path(self):
        self.run_tests(S3.CallingFormat.PATH)

    def run_tests(self, calling_format):
        self.generator.calling_format = calling_format

        key = 'test'

        self.check_url(self.generator.create_bucket(BUCKET_NAME), 'PUT', 200, 'create_bucket')
        self.check_url(self.generator.put(BUCKET_NAME, key, ''), 'PUT', 200, 'put object', 'test data')
        self.check_url(self.generator.get(BUCKET_NAME, key), 'GET', 200, 'get object')
        self.check_url(self.generator.list_bucket(BUCKET_NAME), 'GET', 200, 'list bucket')
        self.check_url(self.generator.list_all_my_buckets(), 'GET', 200, 'list all my buckets')
        acl = self.check_url(self.generator.get_acl(BUCKET_NAME, key), 'GET', 200, 'get acl')
        self.check_url(self.generator.put_acl(BUCKET_NAME, key, acl), 'PUT', 200, 'put acl', acl)
        bucket_acl = self.check_url(self.generator.get_bucket_acl(BUCKET_NAME), 'GET', 200, 'get bucket acl')
        self.check_url(self.generator.put_bucket_acl(BUCKET_NAME, bucket_acl), 'PUT', 200, 'put bucket acl', bucket_acl)
        bucket_logging = self.check_url(self.generator.get_bucket_logging(BUCKET_NAME), 'GET', 200, 'get bucket logging')
        self.check_url(self.generator.put_bucket_logging(BUCKET_NAME, bucket_logging), 'PUT', 200, 'put bucket logging', bucket_logging)
        self.check_url(self.generator.delete(BUCKET_NAME, key), 'DELETE', 204, 'delete object')
        self.check_url(self.generator.delete_bucket(BUCKET_NAME), 'DELETE', 204, 'delete bucket')


if __name__ == '__main__':
    unittest.main()



########NEW FILE########
__FILENAME__ = tests
from datetime import datetime, timedelta
import httplib
import os
from StringIO import StringIO
from time import sleep
import urlparse
from zipfile import ZipFile
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.forms.widgets import Media
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_unicode
from django.utils.http import urlquote
from cuddlybuddly.storage.s3 import lib
from cuddlybuddly.storage.s3.exceptions import S3Error
from cuddlybuddly.storage.s3.storage import S3Storage
from cuddlybuddly.storage.s3.utils import CloudFrontURLs, create_signed_url


default_storage = S3Storage()


MEDIA_URL = settings.MEDIA_URL
if not MEDIA_URL.endswith('/'):
    MEDIA_URL = MEDIA_URL+'/'

DUMMY_IMAGE = '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAIBAQEBAQIBAQECAgICAgQDAgICAgUEBAMEBgUGBgYF\nBgYGBwkIBgcJBwYGCAsICQoKCgoKBggLDAsKDAkKCgr/2wBDAQICAgICAgUDAwUKBwYHCgoKCgoK\nCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgr/wAARCAAKAA8DASIA\nAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA\nAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3\nODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm\np6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA\nAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx\nBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK\nU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3\nuLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3PxT8\nZP23oP8AggV47sNP/Z28PS+EF8K+J0HxAf4typqaW/8Aa97mcWH9mn515UR/aeQo+YZwPWP2tPCv\nxF/afv8A4g+AvAfhqWwl8I/tpxwXdz4XiuBNeWw+GVvL9ouzvcbvNvY4sqETbHANu/LN02saXph/\n4N6/GulnToPszeC/Ewa38lfLIOrXhI24xya5n9p+8vNA1v4jXGhXctlJd/tsJ9qe0kMZm/4tfa/f\nK43fcTr/AHF9BQB//9k=\n'.decode('base64')


class UnicodeContentFile(ContentFile):
    """
    A version of ContentFile that never uses cStringIO so that it is always
    unicode compatible.
    """
    def __init__(self, content):
        content = content or ''
        super(ContentFile, self).__init__(StringIO(content))
        self.size = len(content)


class S3StorageTests(TestCase):
    def run_test(self, filename, content='Lorem ipsum dolar sit amet'):
        content = UnicodeContentFile(content)
        filename = default_storage.save(filename, content)
        self.assert_(default_storage.exists(filename))

        self.assertEqual(default_storage.size(filename), content.size)
        now = datetime.now()
        delta = timedelta(minutes=5)
        mtime = default_storage.modified_time(filename)
        self.assert_(mtime > (now - delta))
        self.assert_(mtime < (now + delta))
        file = default_storage.open(filename)
        self.assertEqual(file.size, content.size)
        fileurl = force_unicode(file).replace('\\', '/')
        fileurl = urlquote(fileurl, '/')
        if fileurl.startswith('/'):
            fileurl = fileurl[1:]

        self.assertEqual(
            MEDIA_URL+fileurl,
            default_storage.url(filename)
        )
        file.close()

        default_storage.delete(filename)
        self.assert_(not default_storage.exists(filename))

    def test_absolute_path(self):
        self.run_test('/testsdir/file1.txt')

    def test_relative_path(self):
        self.run_test('testsdir/file2.txt')

    def test_unicode(self):
        self.run_test(u'testsdir/\u00E1\u00E9\u00ED\u00F3\u00FA.txt')

    def test_byte_contents(self):
        self.run_test('testsdir/filebytes.jpg', DUMMY_IMAGE)

    def test_filename_with_spaces(self):
        self.run_test('testsdir/filename with spaces.txt')

    def test_byte_contents_when_closing_file(self):
        filename = u'filebytes\u00A3.jpg'
        file = default_storage.open(filename, 'wb')
        file.write(DUMMY_IMAGE)
        file.close()
        self.assertEqual(default_storage.size(filename), file.size)
        default_storage.delete(filename)
        self.assert_(not default_storage.exists(filename))

    def test_ranged_read(self):
        filename = u'fileranged.jpg'
        file = default_storage.open(filename, 'wb')
        file.write(DUMMY_IMAGE)
        file.close()
        self.assertEqual(default_storage.size(filename), file.size)
        self.assertEqual(len(default_storage.open(filename).read(128)), 128)
        default_storage.delete(filename)
        self.assert_(not default_storage.exists(filename))

    def test_seek(self):
        filename = u'fileseek.jpg'
        file = default_storage.open(filename, 'wb')
        file.write(DUMMY_IMAGE)
        file.close()
        self.assertEqual(default_storage.size(filename), file.size)

        # Recreation of how PIL detects JPEGs.
        file = default_storage.open(filename)
        prefix = file.read(16)
        file.seek(0)
        self.assertEqual(ord(file.read(1)[0]), 255)
        file.close()

        default_storage.delete(filename)
        self.assert_(not default_storage.exists(filename))

    def test_write_to_file(self):
        filename = 'file6.txt'
        default_storage.save(filename, UnicodeContentFile('Lorem ipsum dolor sit amet'))
        self.assert_(default_storage.exists(filename))

        file = default_storage.open(filename, 'w')
        self.assertEqual(file.size, 26)

        file.write('Lorem ipsum')
        file.close()
        self.assertEqual(file.size, 11)

        default_storage.delete(filename)
        self.assert_(not default_storage.exists(filename))

    def run_listdir_test(self, folder):
        content = ('testsdir/file3.txt', 'testsdir/file4.txt',
                 'testsdir/sub/file5.txt')
        for file in content:
            default_storage.save(file, UnicodeContentFile('Lorem ipsum dolor sit amet'))
            self.assert_(default_storage.exists(file))

        dirs, files = default_storage.listdir(folder)
        self.assertEqual(dirs, ['sub'])
        self.assertEqual(files, ['file3.txt', 'file4.txt'])
        if not folder.endswith('/'):
            folder = folder+'/'
        dirs, files = default_storage.listdir(folder+dirs[0])
        self.assertEqual(dirs, [])
        self.assertEqual(files, ['file5.txt'])

        for file in content:
            default_storage.delete(file)
            self.assert_(not default_storage.exists(file))

    def test_listdir_absolute_path(self):
        self.run_listdir_test('/testsdir')

    def test_listdir_relative_path(self):
        self.run_listdir_test('testsdir')

    def test_listdir_ending_slash(self):
        self.run_listdir_test('testsdir/')

    def test_gzip(self):
        ct_backup = getattr(settings, 'CUDDLYBUDDLY_STORAGE_S3_GZIP_CONTENT_TYPES', None)
        settings.CUDDLYBUDDLY_STORAGE_S3_GZIP_CONTENT_TYPES = (
            'text/css',
            'application/javascript',
            'application/x-javascript'
        )

        filename = 'testsdir/filegzip.css'
        file = UnicodeContentFile('Lorem ipsum ' * 512)
        self.assertEqual(file.size, 6144)
        default_storage.save(filename, file)
        self.assertEqual(default_storage.size(filename), 62)

        file2 = default_storage.open(filename)
        self.assertEqual(file2.read(), 'Lorem ipsum ' * 512, 'Failed to read Gzipped content')
        file2.close()

        default_storage.delete(filename)

        if ct_backup is not None:
            settings.CUDDLYBUDDLY_STORAGE_S3_GZIP_CONTENT_TYPES = ct_backup

    def test_exists_on_empty_path(self):
        self.assert_(not default_storage.exists(''))
        self.assert_(not default_storage.exists(None))

    def test_modified_time_on_non_existent_file(self):
        self.assertRaises(
            S3Error,
            default_storage.modified_time,
            'this/file/better/not/exist'
        )

    # Turn off gzip to make file sizes more predictable
    @override_settings(CUDDLYBUDDLY_STORAGE_S3_GZIP_CONTENT_TYPES=())
    def test_chunked_read(self):
        filename = 'testsdir/filechunked.txt'
        file_ = UnicodeContentFile('Lorem ipsum ' * 200)
        self.assertEqual(file_.size, 2400)
        filename = default_storage.save(filename, file_)

        file_ = default_storage.open(filename)
        for i, data in enumerate(file_.chunks(1024)):
            if i == 3:
                length = 0
            elif i == 2:
                length = 352
            else:
                length = 1024
            self.assertEqual(len(unicode(data)), length)

        default_storage.delete(filename)

        # Now for a 0 length read
        filename = 'testsdir/filechunkedzerolength.txt'
        file_ = UnicodeContentFile('')
        self.assertEqual(file_.size, 0)
        filename = default_storage.save(filename, file_)

        file_ = default_storage.open(filename)
        for c in file_.chunks(1024):
            self.assertEqual(len(c), 0)

        default_storage.delete(filename)

    def test_chunked_zipfile_read(self):
        """
        A zip file's central directory is located at the end of the file and
        ZipFile.infolist will try to read chunks from the end before falling
        back to reading the whole file.
        """
        filename = 'testsdir/filechunked.zip'
        file_ = StringIO()
        zip_ = ZipFile(file_, 'a')
        zip_.writestr('test.txt', 'Lorem ipsum ' * 512)
        zip_.close()
        default_storage.save(filename, file_)

        file2 = default_storage.open(filename)
        zip_ = ZipFile(file2)
        self.assertEqual(
            [i.filename for i in zip_.infolist()],
            ['test.txt']
        )
        file2.close()

        default_storage.delete(filename)


class SignedURLTests(TestCase):
    def setUp(self):
        self.conn = lib.AWSAuthConnection(
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY
        )
        self.key = getattr(settings, 'CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR', None)
        settings.CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR = ('PK12345EXAMPLE',
"""-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDA7ki9gI/lRygIoOjV1yymgx6FYFlzJ+z1ATMaLo57nL57AavW
hb68HYY8EA0GJU9xQdMVaHBogF3eiCWYXSUZCWM/+M5+ZcdQraRRScucmn6g4EvY
2K4W2pxbqH8vmUikPxir41EeBPLjMOzKvbzzQy9e/zzIQVREKSp/7y1mywIDAQAB
AoGABc7mp7XYHynuPZxChjWNJZIq+A73gm0ASDv6At7F8Vi9r0xUlQe/v0AQS3yc
N8QlyR4XMbzMLYk3yjxFDXo4ZKQtOGzLGteCU2srANiLv26/imXA8FVidZftTAtL
viWQZBVPTeYIA69ATUYPEq0a5u5wjGyUOij9OWyuy01mbPkCQQDluYoNpPOekQ0Z
WrPgJ5rxc8f6zG37ZVoDBiexqtVShIF5W3xYuWhW5kYb0hliYfkq15cS7t9m95h3
1QJf/xI/AkEA1v9l/WN1a1N3rOK4VGoCokx7kR2SyTMSbZgF9IWJNOugR/WZw7HT
njipO3c9dy1Ms9pUKwUF46d7049ck8HwdQJARgrSKuLWXMyBH+/l1Dx/I4tXuAJI
rlPyo+VmiOc7b5NzHptkSHEPfR9s1OK0VqjknclqCJ3Ig86OMEtEFBzjZQJBAKYz
470hcPkaGk7tKYAgP48FvxRsnzeooptURW5E+M+PQ2W9iDPPOX9739+Xi02hGEWF
B0IGbQoTRFdE4VVcPK0CQQCeS84lODlC0Y2BZv2JxW3Osv/WkUQ4dslfAQl1T303
7uwwr7XTroMv8dIFQIPreoPhRKmd/SbJzbiKfS/4QDhU
-----END RSA PRIVATE KEY-----""")
        self.media_url = settings.MEDIA_URL
        default_storage.base_url = settings.MEDIA_URL = CloudFrontURLs(
            'http://%s.s3.amazonaws.com/' % settings.AWS_STORAGE_BUCKET_NAME,
            patterns={'^horizon.jpg': 'http://d604721fxaaqy9.cloudfront.net'}
        )

    def tearDown(self):
        if self.key is not None:
            settings.CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR = self.key
        default_storage.base_url = settings.MEDIA_URL = self.media_url

    def get_url(self, url):
        url = urlparse.urlparse(url)
        if url.scheme == 'https':
            conn = httplib.HTTPSConnection(url.netloc)
        else:
            conn = httplib.HTTPConnection(url.netloc)
        path = url.path
        if url.query:
            path = path+'?'+url.query
        conn.request('GET', path)
        return conn.getresponse()

    def run_test_signed_url(self, filename):
        response = self.conn.put(
            settings.AWS_STORAGE_BUCKET_NAME,
            filename,
            'Lorem ipsum dolor sit amet.',
            {'x-amz-acl': 'private'}
        )
        self.assertEquals(response.http_response.status, 200, 'put with a string argument')
        response = self.get_url(default_storage.url(filename))
        self.assertEqual(response.status, 403)

        signed_url = create_signed_url(filename, expires=5, secure=True)
        response = self.get_url(signed_url)
        self.assertEqual(
            response.status,
            200,
            'If this is failing, try resyncing your computer\'s clock.'
        )
        sleep(6)
        response = self.get_url(signed_url)
        self.assertEqual(
            response.status,
            403,
            'If this is failing, try resyncing your computer\'s clock.'
        )

        default_storage.delete(filename)
        return signed_url

    def test_signed_url(self):
        self.run_test_signed_url('testprivatefile.txt')

    def test_signed_url_with_spaces(self):
        filename = 'test private file with spaces.txt'
        signed_url = self.run_test_signed_url('test private file with spaces.txt')
        self.assert_(filename.replace(' ', '+') not in signed_url)
        self.assert_(filename.replace(' ', '%20') in signed_url)

    def test_signed_url_with_unicode(self):
        self.run_test_signed_url(u'testprivatefile\u00E1\u00E9\u00ED\u00F3\u00FA.txt')

    def test_signed_url_in_subdir(self):
        self.run_test_signed_url('testdirs/testprivatefile.txt')

    def test_signed_url_in_subdir_with_unicode(self):
        self.run_test_signed_url(u'testdirs/testprivatefile\u00E1\u00E9\u00ED\u00F3\u00FA.txt')

    def test_signed_url_missing_file(self):
        signed_url = create_signed_url('testprivatemissing.txt', expires=5, secure=True)
        response = self.get_url(signed_url)
        self.assertEqual(response.status, 404)

    def test_private_cloudfront(self):
        signed_url = create_signed_url('horizon.jpg?large=yes&license=yes', secure=False, private_cloudfront=True, expires_at=1258237200)
        self.assertEqual(
            signed_url,
            'http://d604721fxaaqy9.cloudfront.net/horizon.jpg?large=yes&license=yes&Expires=1258237200&Signature=Nql641NHEUkUaXQHZINK1FZ~SYeUSoBJMxjdgqrzIdzV2gyEXPDNv0pYdWJkflDKJ3xIu7lbwRpSkG98NBlgPi4ZJpRRnVX4kXAJK6tdNx6FucDB7OVqzcxkxHsGFd8VCG1BkC-Afh9~lOCMIYHIaiOB6~5jt9w2EOwi6sIIqrg_&Key-Pair-Id=PK12345EXAMPLE'
        )

    def test_encoding(self):
        signed_url = create_signed_url('it\'s/a/test.jpg', secure=False, private_cloudfront=True, expires_at=1258237200)
        self.assert_('/it\'s/a/test.jpg?' not in signed_url)
        self.assert_('/it%27s/a/test.jpg?' in signed_url)


class TemplateTagsTests(TestCase):
    def render_template(self, source, context=None):
        if not context:
            context = {}
        context = Context(context)
        source = '{% load s3_tags %}' + source
        return Template(source).render(context)

    def test_bad_values(self):
        tests = (
            '{% s3_media_url %}',
            '{% s3_media_url "a" as %}',
        )
        for test in tests:
            self.assertRaises(TemplateSyntaxError, self.render_template, test)

    def test_good_values(self):
        tests = {
            '{% s3_media_url "test/file.txt" %}':
                'test/file.txt',
            '{% s3_media_url "test/file2.txt" as var %}':
                '',
            '{% s3_media_url "test/file2.txt" as var %}{{ var }}':
                'test/file2.txt',
            '{% s3_media_url file %}':
                ('test/file3.txt', {'file': 'test/file3.txt'}),
            '{% s3_media_url file as var %}{{ var }}':
                ('test/file4.txt', {'file': 'test/file4.txt'}),
            '{% s3_media_url "test/file%20quote.txt" %}':
                'test/file%20quote.txt',
            '{% s3_media_url "test/file quote.txt" %}':
                'test/file%20quote.txt',
            u'{% s3_media_url "test/fil\u00E9.txt" %}':
                'test/fil%C3%A9.txt',
            '{% s3_media_url "test/fil%C3%A9.txt" %}':
                'test/fil%C3%A9.txt',
        }
        for name, val in tests.items():
            if type(val).__name__ == 'str':
                val = (val, None)
            self.assertEqual(self.render_template(name, val[1]),
                             urlparse.urljoin(settings.MEDIA_URL, val[0]) if val[0] else '')


class CommandTests(TestCase):
    def setUp(self):
        self.backup_exclude = getattr(
            settings,
            'CUDDLYBUDDLY_STORAGE_S3_SYNC_EXCLUDE',
            None
        )
        settings.CUDDLYBUDDLY_STORAGE_S3_SYNC_EXCLUDE = ['\.svn$', 'Thumbs\.db$']
        self.folder = 'cbs3testsync'
        self.basepath = os.path.join(settings.MEDIA_ROOT, self.folder)
        if not os.path.exists(self.basepath):
            os.makedirs(self.basepath)
        self.files = {
            'test1.txt': 'Lorem',
            'test2.txt': 'Ipsum',
            'test3.txt': 'Dolor'
        }
        self.exclude_files = {
            '.svn/test4.txt': 'Lorem',
            'Thumbs.db': 'Ipsum'
        }
        self.created_paths = []
        for files in (self.files, self.exclude_files):
            for filename, contents in files.items():
                path = os.path.join(self.basepath, os.path.split(filename)[0])
                if not os.path.exists(path):
                    self.created_paths.append(path)
                    os.makedirs(path)
                fh = open(os.path.join(self.basepath, filename), 'w')
                fh.write(contents)
                fh.close()
        self.created_paths.append(self.basepath)

    def tearDown(self):
        for files in (self.files, self.exclude_files):
            for file in files.keys():
                try:
                    os.remove(os.path.join(self.basepath, file))
                except:
                    pass
        for dir in self.created_paths:
            try:
                os.rmdir(dir)
            except:
                pass
        if self.backup_exclude is not None:
            settings.CUDDLYBUDDLY_STORAGE_S3_SYNC_EXCLUDE = self.backup_exclude

    def test_sync(self):
        for file in self.files.keys():
            self.assert_(not default_storage.exists(
                os.path.join(self.folder, file))
            )
        call_command(
            'cb_s3_sync_media',
            verbosity=0,
            dir=self.basepath,
            prefix=self.folder
        )
        for file in self.files.keys():
            self.assert_(default_storage.exists(
                os.path.join(self.folder, file))
            )
        for file in self.exclude_files.keys():
            self.assert_(not default_storage.exists(
                os.path.join(self.folder, file))
            )

        modified_times = {}
        for file in self.files.keys():
            modified_times[file] = default_storage.modified_time(
                os.path.join(self.folder, file)
            )

        call_command(
            'cb_s3_sync_media',
            verbosity=0,
            dir=self.basepath,
            prefix=self.folder
        )
        for file in self.files.keys():
            self.assertEqual(
                modified_times[file],
                default_storage.modified_time(os.path.join(self.folder, file)),
                'If this is failing, try resyncing your computer\'s clock.'
            )

        call_command(
            'cb_s3_sync_media',
            verbosity=0,
            dir=self.basepath,
            prefix=self.folder,
            force=True
        )
        for file in self.files.keys():
            self.assert_(
                modified_times[file] < \
                default_storage.modified_time(os.path.join(self.folder, file))
            )

        for file in self.files.keys():
            default_storage.delete(os.path.join(self.folder, file))


class MediaMonkeyPatchTest(TestCase):
    def test_media_monkey_patch(self):
        media = Media()
        media.add_js((
            '/admin/test1.js',
            'admin/test2.js',
            'http://example.com/admin/test3.js',
            '//example.com/admin/test3.js'
        ))
        media.add_css({
            'all': (
                '/admin/test1.css',
                'admin/test2.css',
                'http://example.com/admin/test2.css',
                '//example.com/admin/test2.css'
            )
        })

        no_monkey = """
<link href="/admin/test1.css" type="text/css" media="all" rel="stylesheet" />
<link href="/static/admin/test2.css" type="text/css" media="all" rel="stylesheet" />
<link href="http://example.com/admin/test2.css" type="text/css" media="all" rel="stylesheet" />
<link href="//example.com/admin/test2.css" type="text/css" media="all" rel="stylesheet" />
<script type="text/javascript" src="/admin/test1.js"></script>
<script type="text/javascript" src="/static/admin/test2.js"></script>
<script type="text/javascript" src="http://example.com/admin/test3.js"></script>
<script type="text/javascript" src="//example.com/admin/test3.js"></script>
        """.strip()
        monkey = """
<link href="/admin/test1.css" type="text/css" media="all" rel="stylesheet" />
<link href="http://this.com/static/admin/test2.css" type="text/css" media="all" rel="stylesheet" />
<link href="http://example.com/admin/test2.css" type="text/css" media="all" rel="stylesheet" />
<link href="//example.com/admin/test2.css" type="text/css" media="all" rel="stylesheet" />
<script type="text/javascript" src="/admin/test1.js"></script>
<script type="text/javascript" src="http://this.com/static/admin/test2.js"></script>
<script type="text/javascript" src="http://example.com/admin/test3.js"></script>
<script type="text/javascript" src="//example.com/admin/test3.js"></script>
        """.strip()

        with self.settings(STATIC_URL='/static/'):
            self.assertEqual(media.render(), no_monkey)

        with self.settings(
            STATIC_URL=CloudFrontURLs('http://notthis.com/', patterns={
                '^admin': 'http://this.com/static/'
            })
        ):
            self.assertEqual(media.render(), monkey)

########NEW FILE########
__FILENAME__ = testsettings
import os
import sys


DEBUG = True
if sys.platform[0:3] == 'win':
    TEMP = os.environ.get('TEMP', '')
else:
    TEMP = '/tmp'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memoery:'
    }
}
INSTALLED_APPS = [
    'cuddlybuddly.storage.s3'
]
STATIC_ROOT = MEDIA_ROOT = os.path.join(TEMP, 'cbs3test')
SECRET_KEY = 'placeholder'

DEFAULT_FILE_STORAGE = 'cuddlybuddly.storage.s3.S3Storage'
from cuddlybuddly.storage.s3 import CallingFormat
AWS_CALLING_FORMAT = CallingFormat.SUBDOMAIN

# Below should contain:
#
# MEDIA_URL = 'http://yourbucket.s3.amazonaws.com/'
# AWS_ACCESS_KEY_ID = ''
# AWS_SECRET_ACCESS_KEY = ''
# AWS_STORAGE_BUCKET_NAME = ''
from cuddlybuddly.storage.s3.tests3credentials import *

CUDDLYBUDDLY_STORAGE_S3_CACHE = 'cuddlybuddly.storage.s3.cache.FileSystemCache'
CUDDLYBUDDLY_STORAGE_S3_FILE_CACHE_DIR = TEMP+'/cbs3testcache'

########NEW FILE########
__FILENAME__ = utils
import base64
import json
import re
import rsa
import time
from urllib2 import unquote
from urlparse import urljoin, urlparse, urlunparse
from django.conf import settings
from django.utils.http import urlquote
from cuddlybuddly.storage.s3 import CallingFormat
from cuddlybuddly.storage.s3.lib import QueryStringAuthGenerator
from cuddlybuddly.storage.s3.middleware import request_is_secure


def create_signed_url(file, expires=60, secure=False, private_cloudfront=False, expires_at=None):
    if not private_cloudfront:
        generator = QueryStringAuthGenerator(
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY,
            calling_format=getattr(settings, 'AWS_CALLING_FORMAT',
                                CallingFormat.SUBDOMAIN),
            is_secure=secure)
        generator.set_expires_in(expires)
        return generator.generate_url(
            'GET',
            settings.AWS_STORAGE_BUCKET_NAME,
            file
        )

    url = settings.MEDIA_URL
    if not isinstance(settings.MEDIA_URL, CloudFrontURLs):
        url = CloudFrontURLs(settings.MEDIA_URL)
    url = url.get_url(file, force_https=True if secure else False)

    if expires_at is None:
        expires = int(time.time() + expires)
    else:
        expires = expires_at

    policy = {
        'Statement': [{
            'Resource': url,
            'Condition': {
                'DateLessThan': {
                    'AWS:EpochTime': expires
                }
            }
        }]
    }

    key = settings.CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR
    policy = json.dumps(policy, separators=(',',':'))
    sig = rsa.PrivateKey.load_pkcs1(key[1])
    sig = rsa.sign(policy, sig, 'SHA-1')
    sig = base64.b64encode(sig).replace('+', '-').replace('=', '_').replace('/', '~')

    return '%s%sExpires=%s&Signature=%s&Key-Pair-Id=%s' % (
        url,
        '&' if '?' in url else '?',
        expires,
        sig,
        key[0]
    )


class CloudFrontURLs(unicode):
    def __new__(cls, default, patterns={}, https=None):
        obj = super(CloudFrontURLs, cls).__new__(cls, default)
        obj._patterns = []
        for key, value in patterns.iteritems():
            obj._patterns.append((re.compile(key), unicode(value)))
        obj._https = https
        return obj

    def match(self, name):
        for pattern in self._patterns:
            if pattern[0].match(name):
                return pattern[1]
        return self

    def https(self):
        if self._https is not None:
            return unicode(self._https)
        return self.replace('http://', 'https://')

    def get_url(self, path, force_https=False):
        if force_https or request_is_secure():
            url = self.https()
        else:
            url = self.match(path).replace('https://', 'http://')
        url = list(urlparse(urljoin(url, path)))
        url[2] = urlquote(unquote(url[2].encode('utf-8')))
        return urlunparse(url)

########NEW FILE########
