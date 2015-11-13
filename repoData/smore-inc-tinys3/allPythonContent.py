__FILENAME__ = auth
# -*- coding: utf-8 -*-
import requests

from requests.auth import AuthBase
from requests.structures import CaseInsensitiveDict
from datetime import datetime
import hashlib
import hmac
import base64
import re

# Python 2/3 support
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

# A regexp used for detecting aws bucket names
BUCKET_VHOST_MATCH = re.compile(r'^([a-z0-9\-]+\.)?s3([a-z0-9\-]+)?\.amazonaws\.com$', flags=re.IGNORECASE)

# A list of query params used by aws
AWS_QUERY_PARAMS = ['versioning', 'location', 'acl', 'torrent', 'lifecycle', 'versionid',
                    'response-content-type', 'response-content-language', 'response-expires', 'response-cache-control',
                    'response-content-disposition', 'response-content-encoding', 'delete']


class S3Auth(AuthBase):
    """
    S3 Custom Authenticator class for requests

    This authenticator will sign your requests based on the RESTAuthentication specs by Amazon
    http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html

    You can read more about custom authenticators here:
    http://docs.python-requests.org/en/latest/user/advanced.html#custom-authentication

    Usage:

    >>> from tinys3.auth import S3Auth
    >>> requests.put('<S3Url>', data='<S3Data'>, auth=S3Auth('<access_key>','<secret_key>'))
    """

    def __init__(self, access_key, secret_key):
        """
        Initiate the authenticator, using S3 Credentials

        Params:
            - access_key    Your S3 access key
            - secret_key    You S3 secret key

        """
        self.secret_key = secret_key
        self.access_key = access_key

    def sign(self, string_to_sign):
        """
        Generates a signature for the given string

        Params:
            - string_to_sign    The string we want to sign

        Returns:
            Signature in bytes
        """
        digest = hmac.new(self.secret_key.encode('utf8'),
                          msg=string_to_sign.encode('utf8'),
                          digestmod=hashlib.sha1).digest()

        return base64.b64encode(digest).strip().decode('ascii')

    def string_to_sign(self, request):
        """
        Generates the string we need to sign on.

        Params:
            - request   The request object

        Returns
            String ready to be signed on

        """

        # We'll use case insensitive dict to store the headers
        h = CaseInsensitiveDict()
        # Add the hearders
        h.update(request.headers)

        # If we have an 'x-amz-date' header, we'll try to use it instead of the date
        if b'x-amz-date' in h or 'x-amz-date' in h:
            date = ''
        else:
            # No x-amz-header, we'll generate a date
            date = h.get('Date') or self._get_date()

        # Set the date header
        request.headers['Date'] = date

        # A fix for the content type header extraction in python 3
        # This have to be done because requests will try to set application/www-url-encoded herader
        # if we pass bytes as the content, and the content-type is set with a key that is b'Content-Type' and not
        # 'Content-Type'
        content_type = ''
        if b'Content-Type' in request.headers:
            # Fix content type
            content_type = h.get(b'Content-Type')
            del request.headers[b'Content-Type']
            request.headers['Content-Type'] = content_type

        # The string we're about to generate
        # There's more information about it here:
        # http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html#ConstructingTheAuthenticationHeader
        msg = [
            # HTTP Method
            request.method,
            # MD5 If provided
            h.get(b'Content-MD5', '') or h.get('Content-MD5', ''),
            # Content type if provided
            content_type or h.get('Content-Type', ''),
            # Date
            date,
            # Canonicalized special amazon headers and resource uri
            self._get_canonicalized_amz_headers(h) + self._get_canonicalized_resource(request)
        ]

        # join with a newline and return
        return '\n'.join(msg)

    def _get_canonicalized_amz_headers(self, headers):
        """
        Collect the special Amazon headers, prepare them for signing

        Params:
            - headers   CaseInsensitiveDict with the header requests

        Returns:
            - String with the canonicalized headers

        More information about this process here:
        http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html#RESTAuthenticationConstructingCanonicalizedAmzHeaders
        """

        # New dict for the amazon headers
        amz_dict = {}

        # Go over the existing headers
        for k, v in headers.items():
            # Decode the keys if they are encoded
            if isinstance(k, bytes):
                k = k.decode('ascii')

            # to lower case
            k = k.lower()

            # If it starts with 'x-amz' add it to our dict
            if k.startswith('x-amz'):
                amz_dict[k] = v

        result = ""
        # Sort the keys and iterate through them
        for k in sorted(amz_dict.keys()):
            # add stripped key and value to the result string
            result += "%s:%s\n" % (k.strip(), amz_dict[k].strip().replace('\n', ' '))

        # Return the result string
        return result

    def _get_canonicalized_resource(self, request):
        """
        Generates the canonicalized resource string form a request

        You can read more about the process here:
        http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html#ConstructingTheCanonicalizedResourceElement

        Params:
            - request   The request object

        Returns:
            String the canoncicalized resource string.
        """

        r = ""

        # parse our url
        parts = urlparse(request.url)

        # get the host, remove any port identifiers
        host = parts.netloc.split(':')[0]

        if host:
            # try to match our host to <hostname>.s3.amazonaws.com/s3.amazonaws.com
            m = BUCKET_VHOST_MATCH.match(host)
            if m:
                bucket = (m.groups()[0] or '').rstrip('.')

                if bucket:
                    r += ('/' + bucket)
            else:
                # It's a virtual host, add it to the result
                r += ('/' + host)

        # Add the path string
        r += parts.path or '/'

        # add the special query strings
        r += self._get_subresource(parts.query)

        return r

    def _get_subresource(self, qs):
        """
        Handle subresources in the query string

        More information about subresources:
        http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html#ConstructingTheCanonicalizedResourceElement
        """
        r = []

        # Split the querystring
        keys = qs.split('&')
        # for each item
        for i in keys:
            # get the key
            item = i.split('=')
            k = item[0].lower()

            # If it's one the special params
            if k in AWS_QUERY_PARAMS:
                # add it to our result list
                r.append(i)

        # If we have result, convert them to query string
        if r:
            return '?' + '&'.join(r)

        return ''

    def _get_date(self):
        """
        Returns a string for the current date
        """
        return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

    def _fix_content_length(self, request):
        """
        Amazon requires to have content-length header when using the put request,
        However, requests won't add this header, so we need to add it ourselves.

        Params:
            - request   The request object
        """

        if request.method == 'PUT' and not 'Content-Length' in request.headers:
            request.headers['Content-Length'] = '0'

    def __call__(self, r):
        """
        The entry point of the custom authenticator.

        When used as an auth class, requests will call this method just before sending
        the request.

        Params:
            - r     The request object

        Returns:
            The request object, after we've updated some headers
        """

        # Generate the string to sign
        msg = self.string_to_sign(r)
        # Sign the string and add the authorization header
        r.headers['Authorization'] = "AWS %s:%s" % (self.access_key, self.sign(msg))

        # Fix an issue with 0 length requests
        self._fix_content_length(r)

        # return the request
        return r

########NEW FILE########
__FILENAME__ = connection
# -*- coding: utf-8 -*-

from .auth import S3Auth
from .request_factory import UploadRequest, UpdateMetadataRequest, CopyRequest, DeleteRequest, GetRequest


class Base(object):
    """
    The "Base" connection object, Handles the common S3 tasks (upload, copy, delete,etc)

    This is an "abstract" class, both Connection and Pool implement it.
    """

    def __init__(self, access_key, secret_key, default_bucket=None, tls=False, endpoint="s3.amazonaws.com"):
        """
        Creates a new S3 connection

        Params:
            - access_key        AWS access key
            - secret_key        AWS secret key
            - default_bucket    (Optional) Sets the default bucket, so requests inside this pool won't have to specify
                                the bucket every time.
            - tls               (Optional) Make the requests using secure connection (Defaults to False)
            - endpoint          (Optional) Sets the s3 endpoint.

        """
        self.default_bucket = default_bucket
        self.auth = S3Auth(access_key, secret_key)
        self.tls = tls
        self.endpoint = endpoint

    def bucket(self, bucket):
        """
        Verifies that we have a bucket for a request

        Params:
            - bucket    The name of the bucket we're trying to use, None if we want to use the default bucket

        Returns:
            The bucket to use for the request

        Raises:
            ValueError if no bucket was provided AND no default bucket was defined.
        """
        b = bucket or self.default_bucket

        # If we don't have a bucket, raise an exception
        if not b:
            raise ValueError("You must specify a bucket in your request or set the default_bucket for the connection")

        return b

    def get(self, key, bucket=None):
        """
        Get a key from a bucket

        Params:
            - key           The key to get

            - bucket        (Optional) The name of the bucket to use (can be skipped if setting the default_bucket)
                            option for the connection

        Returns:
            - A response object from the requests lib or a future that wraps that response object if used with a pool.

        Usage:

        >>> conn.get('my_awesome_key.zip','sample_bucket')

        """
        r = GetRequest(self, key, self.bucket(bucket))

        return self.run(r)

    def upload(self, key, local_file,
               bucket=None, expires=None, content_type=None,
               public=True, headers=None, rewind=True, close=False):
        """
        Upload a file and store it under a key

        Params:
            - key           The key to store the file under.

            - local_file    A file-like object which would be uploaded

            - bucket        (Optional) The name of the bucket to use (can be skipped if setting the default_bucket)
                            option for the connection

            - expires       (Optional) Sets the the Cache-Control headers. The value can be a number (used as seconds),
                            A Timedelta or the 'max' string, which will automatically set the file to be cached for a
                            year. Defaults to no caching

            - content_type  (Optional) Explicitly sets the Content-Type header. if not specified, tinys3 will try to
                            guess the right content type for the file (using the mimetypes lib)

            - public        (Optional) If set to true, tinys3 will set the file to be publicly available using the acl
                            headers. Defaults to True.

            - headers       (Optional) Allows you to specify extra headers for the request using a dict.

            - rewind        (Optional) If true, tinys3 will seek the file like object to the beginning before uploading.
                            Defaults to True.

            - Close         (Optional) If true, tinys3 will close the file like object after the upload was complete

        Returns:
            - A response object from the requests lib or a future that wraps that response object if used with a pool.

        Usage:

        >>> with open('my_local_file.zip', 'rb') as f:
        >>>     conn.upload('my_awesome_key.zip',f,
        >>>                 expires='max',
        >>>                 bucket='sample_bucket',
        >>>                 headers={
        >>>                     'x-amz-storage-class': 'REDUCED_REDUNDANCY'
        >>>                 })

        There are more usage examples in the readme file.

        """
        r = UploadRequest(self, key, local_file, self.bucket(bucket), expires=expires, content_type=content_type,
                          public=public, extra_headers=headers, rewind=rewind, close=close)

        return self.run(r)

    def copy(self, from_key, from_bucket, to_key, to_bucket=None, metadata=None, public=True):
        """
        Copy a key contents to another key/bucket with an option to update metadata/public state

        Params:
            - from_key      The source key
            - from_bucket   The source bucket
            - to_key        The target key
            - to_bucket     (Optional) The target bucket, if not specified, tinys3 will use the `from_bucket`
            - metadata      (Optional) Allows an override of the new key's metadata. if not defined, tinys3 will copy
                            The source key's metadata.
            - public        (Optional) Same as upload, should the new key be publicly accessible? Default to True.

        Returns:
            - A response object from the requests lib or a future that wraps that response object if used with a pool.

        Usage:
            >>> conn.copy('source_key.jpg','source_bucket','target_key.jpg','target_bucket',
            >>>         metadata={ 'x-amz-storage-class': 'REDUCED_REDUNDANCY'})

        There are more usage examples in the readme file.
        """
        to_bucket = self.bucket(to_bucket or from_bucket)

        r = CopyRequest(self, from_key, from_bucket, to_key, to_bucket, metadata=metadata, public=public)

        return self.run(r)

    def update_metadata(self, key, metadata=None, bucket=None, public=True):
        """
        Updates the metadata information for a file

        Params:
            - key           The key to update
            - metadata      (Optional) The metadata dict to set for the key
            - public        (Optional) Same as upload, should the key be publicly accessible? Default to True.

        Returns:
            - A response object from the requests lib or a future that wraps that response object if used with a pool.

        Usage:
            >>> conn.update_metadata('key.jpg',{ 'x-amz-storage-class': 'REDUCED_REDUNDANCY'},'my_bucket')

        There are more usage examples in the readme file.
        """
        r = UpdateMetadataRequest(self, key, self.bucket(bucket), metadata, public)

        return self.run(r)

    def delete(self, key, bucket=None):
        """
        Delete a key from a bucket

        Params:
            - key           The key to delete

            - bucket        (Optional) The name of the bucket to use (can be skipped if setting the default_bucket)
                            option for the connection

        Returns:
            - A response object from the requests lib or a future that wraps that response object if used with a pool.

        Usage:

        >>> conn.delete('my_awesome_key.zip','sample_bucket')

        """
        r = DeleteRequest(self, key, self.bucket(bucket))

        return self.run(r)

    def run(self, request):
        """
        Executes an S3Request and returns the result

        Params:
            - request An instance of S3Request

        """
        return self._handle_request(request)

    def _handle_request(self, request):
        """
        An abstract method, to be implemented by inheriting classes
        """
        raise NotImplementedError


class Connection(Base):
    """
    The basic implementation of an S3 connection.
    """

    def _handle_request(self, request):
        """
        Implements S3Request execution.

        Params:
            - request       S3Request object to run

        """
        return request.run()

########NEW FILE########
__FILENAME__ = pool
# -*- coding: utf-8 -*
from .connection import Base

from concurrent.futures import ThreadPoolExecutor, Future, as_completed, wait, TimeoutError


class Pool(Base):
    def __init__(self, access_key, secret_key, default_bucket=None, tls=False, endpoint="s3.amazonaws.com", size=5):
        """
        Create a new pool.

        Params:
            - access_key        AWS access key
            - secret_key        AWS secret key
            - default_bucket    (Optional) Sets the default bucket, so requests inside this pool won't have to specify
                                the bucket every time.
            - tls               (Optional) Make the requests using secure connection (Defaults to False)
            - endpoint          (Optional) Sets the s3 endpoint.
            - size              (Optional) The maximum number of worker threads to use (Defaults to 5)

        Notes:
            - The pool uses the concurrent.futures library to implement the worker threads.
            - You can use the pool as a context manager, and it will close itself (and it's workers) upon exit.

        """

        # Call to the base constructor
        super(Pool, self).__init__(access_key, secret_key, tls=tls, default_bucket=default_bucket, endpoint=endpoint)

        # Setup the executor
        self.executor = ThreadPoolExecutor(max_workers=size)

    def _handle_request(self, request):
        """
        Handle S3 request and return the result.

        Params:
            - request   An instance of the S3Request object.

        Notes
            - This implementation will execute the request in a different thread and return a Future object.
        """
        future = self.executor.submit(request.run)
        return future

    def close(self, wait=True):
        """
        Close the pool.

        Params:
            - Wait      (Optional) Should the close action block until all the work is completed? (Defaults to True)
        """
        self.executor.shutdown(wait)

    def as_completed(self, futures, timeout=None):
        """
        Returns an iterator that yields the response for every request when it's completed.

        A thin wrapper around concurrent.futures.as_completed.

        Params:
            - futures   A list of Future objects
            - timeout   (Optional) The number of seconds to wait until a TimeoutError is raised

        Notes:
            - The order of the results may not be preserved
            - For more information:
                http://docs.python.org/dev/library/concurrent.futures.html#concurrent.futures.as_completed
        """
        for r in as_completed(futures, timeout):
            yield r.result()

    def all_completed(self, futures, timeout=None):
        """
        Blocks until all the futures are completed, returns a list of responses

        A thin wrapper around concurrent.futures.wait.

        Params:
            - futures   A list of Future objects
            - timeout   (Optional) The number of seconds to wait until a TimeoutError is raised

        Notes:
            - For more information:
                http://docs.python.org/dev/library/concurrent.futures.html#concurrent.futures.wait
        """

        results = wait(futures, timeout)[0]  # Return the 'done' set

        return [i.result() for i in results]

    def __enter__(self):
        """
        Context manager implementation
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the pool
        """
        self.close()
########NEW FILE########
__FILENAME__ = request_factory
# -*- coding: utf-8 -*-

"""

tinys3.request_factory
~~~~~~~~~~~~~~~~~~~~~~

Generates Request objects for various S3 requests

"""

from datetime import timedelta
import mimetypes
import os
import requests

from .util import LenWrapperStream


# A fix for windows pc issues with mimetypes
# http://grokbase.com/t/python/python-list/129tb1ygws/mimetypes-guess-type-broken-in-windows-on-py2-7-and-python-3-x
mimetypes.init([])


class S3Request(object):
    def __init__(self, conn):
        self.auth = conn.auth
        self.tls = conn.tls
        self.endpoint = conn.endpoint

    def bucket_url(self, key, bucket):
        protocol = 'https' if self.tls else 'http'

        return "%s://%s/%s/%s" % (protocol, self.endpoint, bucket, key.lstrip('/'))

    def run(self):
        raise NotImplementedError()

    def adapter(self):
        """
        Returns the adapter to use when issuing a request.
        useful for testing
        """
        return requests


class GetRequest(S3Request):
    def __init__(self, conn, key, bucket):
        super(GetRequest, self).__init__(conn)
        self.key = key
        self.bucket = bucket

    def run(self):
        url = self.bucket_url(self.key, self.bucket)
        r = self.adapter().get(url, auth=self.auth)

        r.raise_for_status()

        return r


class UploadRequest(S3Request):
    def __init__(self, conn, key, local_file, bucket, expires=None, content_type=None, public=True, extra_headers=None,
                 close=False, rewind=True):
        """



        :param conn:
        :param key:
        :param local_file:
        :param bucket:
        :param expires:
        :param content_type:
        :param public:
        :param extra_headers:
        :param close:
        :param rewind:
        """
        super(UploadRequest, self).__init__(conn)

        self.key = key
        self.fp = local_file
        self.bucket = bucket
        self.expires = expires
        self.content_type = content_type
        self.public = public
        self.extra_headers = extra_headers
        self.close = close
        self.rewind = rewind

    def run(self):

        headers = {}

        # calc the expires headers
        if self.expires:
            headers['Cache-Control'] = self._calc_cache_control()

        # calc the content type
        headers['Content-Type'] = self.content_type or mimetypes.guess_type(self.key)[0] or 'application/octet-stream'

        # if public - set public headers
        if self.public:
            headers['x-amz-acl'] = 'public-read'

        # if rewind - rewind the fp like object
        if self.rewind and hasattr(self.fp, 'seek'):
            self.fp.seek(0, os.SEEK_SET)

        # update headers with extra headers
        if self.extra_headers:
            headers.update(self.extra_headers)

        try:
            # Wrap our file pointer with a LenWrapperStream.
            # We do it because requests will try to fallback to chuncked transfer if
            # it can't extract the len attribute of the object it gets, and S3 doesn't
            # support chuncked transfer.
            # In some cases, like cStreamIO, it may cause some issues, so we wrap the stream
            # with a class of our own, that will proxy the stream and provide a proper
            # len attribute
            #
            # TODO - add some tests for that
            # shlomiatar @ 08/04/13
            data = LenWrapperStream(self.fp)

            # call requests with all the params
            r = self.adapter().put(self.bucket_url(self.key, self.bucket),
                                   data=data,
                                   headers=headers,
                                   auth=self.auth)

            r.raise_for_status()

        finally:
            # if close is set, try to close the fp like object (also, use finally to ensure the close)
            if self.close and hasattr(self.fp, 'close'):
                self.fp.close()

        return r

    def _calc_cache_control(self):

        expires = self.expires
        # Handle content expiration
        if expires == 'max':
            expires = timedelta(seconds=31536000)
        elif isinstance(expires, int):
            expires = timedelta(seconds=expires)
        else:
            expires = expires

        return "max-age=%d" % self._get_total_seconds(expires) + ', public' if self.public else ''

    def _get_total_seconds(self, timedelta):
        """
        Support for getting the total seconds from a time delta (Required for python 2.6 support)
        """
        return timedelta.days * 24 * 60 * 60 + timedelta.seconds


class DeleteRequest(S3Request):
    def __init__(self, conn, key, bucket):
        super(DeleteRequest, self).__init__(conn)
        self.key = key
        self.bucket = bucket

    def run(self):
        url = self.bucket_url(self.key, self.bucket)
        r = self.adapter().delete(url, auth=self.auth)

        r.raise_for_status()

        return r


class CopyRequest(S3Request):
    def __init__(self, conn, from_key, from_bucket, to_key, to_bucket, metadata=None, public=True):
        super(CopyRequest, self).__init__(conn)
        self.from_key = from_key.lstrip('/')
        self.from_bucket = from_bucket
        self.to_key = to_key.lstrip('/')
        self.to_bucket = to_bucket
        self.metadata = metadata
        self.public = public

    def run(self):

        headers = {
            'x-amz-copy-source': "/%s/%s" % (self.from_bucket, self.from_key),
            'x-amz-metadata-directive': 'COPY' if not self.metadata else 'REPLACE'
        }

        if self.public:
            headers['x-amz-acl'] = 'public-read'

        if self.metadata:
            headers.update(self.metadata)

        r = self.adapter().put(self.bucket_url(self.to_key, self.to_bucket), auth=self.auth, headers=headers)
        r.raise_for_status()

        return r


class UpdateMetadataRequest(CopyRequest):
    def __init__(self, conn, key, bucket, metadata=None, public=True):
        super(UpdateMetadataRequest, self).__init__(conn, key, bucket, key, bucket, metadata=metadata, public=public)

########NEW FILE########
__FILENAME__ = test_auth
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals

import unittest
from flexmock import flexmock
from tinys3.auth import S3Auth

from requests import Request

# Test access and secret keys, from the s3 manual on REST authentication
# http://docs.aws.amazon.com/AmazonS3/latest/dev/RESTAuthentication.html
TEST_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'
TEST_SECRET_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'


class TestS3Auth(unittest.TestCase):
    def setUp(self):
        # Create a new auth object for every test
        self.auth = S3Auth(TEST_ACCESS_KEY, TEST_SECRET_KEY)

    def test_object_get(self):
        mock_request = Request(method='GET',
                               url="http://johnsmith.s3.amazonaws.com/photos/puppy.jpg",
                               headers={'Date': 'Tue, 27 Mar 2007 19:36:42 +0000'})

        # Call auth
        self.auth(mock_request)

        # test authorization code
        self.assertEquals(mock_request.headers['Authorization'],
                          'AWS AKIAIOSFODNN7EXAMPLE:bWq2s1WEIj+Ydj0vQ697zp+IXMU=')

    def test_object_put(self):
        mock_request = Request(method='PUT',
                               url="http://johnsmith.s3.amazonaws.com/photos/puppy.jpg",
                               headers={'Date': 'Tue, 27 Mar 2007 21:15:45 +0000',
                                        'Content-Type': 'image/jpeg',
                                        'Content-Length': 94328})

        # Call auth
        self.auth(mock_request)

        # test authorization code
        self.assertEquals(mock_request.headers['Authorization'],
                          'AWS AKIAIOSFODNN7EXAMPLE:MyyxeRY7whkBe+bq8fHCL/2kKUg=')

    def test_list_reqeust(self):
        mock_request = Request(method='GET',
                               url="http://johnsmith.s3.amazonaws.com/?prefix=photos&max-keys=50&marker=puppy",
                               headers={'Date': 'Tue, 27 Mar 2007 19:42:41 +0000'})

        # Call auth
        self.auth(mock_request)

        # test authorization code
        self.assertEquals(mock_request.headers['Authorization'],
                          'AWS AKIAIOSFODNN7EXAMPLE:htDYFYduRNen8P9ZfE/s9SuKy0U=')

    def test_fetch(self):
        mock_request = Request(method='GET',
                               url="http://johnsmith.s3.amazonaws.com/?acl",
                               headers={'Date': 'Tue, 27 Mar 2007 19:44:46 +0000'})

        # Call auth
        self.auth(mock_request)

        # test authorization code
        self.assertEquals(mock_request.headers['Authorization'],
                          'AWS AKIAIOSFODNN7EXAMPLE:c2WLPFtWHVgbEmeEG93a4cG37dM=')

    def test_x_amz_date(self):
        mock_request = Request(method='DELETE',
                               url="http://s3.amazonaws.com/johnsmith/photos/puppy.jpg",
                               headers={'Date': 'Tue, 27 Mar 2007 21:20:27 +0000',
                                        'x-amz-date': 'Tue, 27 Mar 2007 21:20:26 +0000'})

        target = """
DELETE



x-amz-date:Tue, 27 Mar 2007 21:20:26 +0000
/johnsmith/photos/puppy.jpg
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)


    def test_delete(self):
        mock_request = Request(method='DELETE',
                               url="http://s3.amazonaws.com/johnsmith/photos/puppy.jpg",
                               headers={'Date': 'Tue, 27 Mar 2007 21:20:26 +0000'})

        target = """
DELETE


Tue, 27 Mar 2007 21:20:26 +0000
/johnsmith/photos/puppy.jpg
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

        # Call auth
        self.auth(mock_request)

        # test authorization code
        self.assertEquals(mock_request.headers['Authorization'],
                          'AWS AKIAIOSFODNN7EXAMPLE:lx3byBScXR6KzyMaifNkardMwNk=')

    def test_upload(self):
        mock_request = Request(method='PUT',
                               url="http://static.johnsmith.net:8080/db-backup.dat.gz",
                               headers={'Date': 'Tue, 27 Mar 2007 21:06:08 +0000',
                                        'x-amz-acl': 'public-read',
                                        'content-type': 'application/x-download',
                                        'Content-MD5': '4gJE4saaMU4BqNR0kLY+lw==',
                                        'X-Amz-Meta-ReviewedBy': 'joe@johnsmith.net,jane@johnsmith.net',
                                        'X-Amz-Meta-FileChecksum': '0x02661779',
                                        'X-Amz-Meta-ChecksumAlgorithm': 'crc32',
                                        'Content-Disposition': 'attachment; filename=database.dat',
                                        'Content-Encoding': 'gzip',
                                        'Content-Length': '5913339'})

        target = """
PUT
4gJE4saaMU4BqNR0kLY+lw==
application/x-download
Tue, 27 Mar 2007 21:06:08 +0000
x-amz-acl:public-read
x-amz-meta-checksumalgorithm:crc32
x-amz-meta-filechecksum:0x02661779
x-amz-meta-reviewedby:joe@johnsmith.net,jane@johnsmith.net
/static.johnsmith.net/db-backup.dat.gz
        """.strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

        # Call auth
        self.auth(mock_request)

        # test authorization code
        self.assertEquals(mock_request.headers['Authorization'],
                          'AWS AKIAIOSFODNN7EXAMPLE:ilyl83RwaSoYIEdixDQcA4OnAnc=')

    def test_upload_0_length_file(self):
        """
        Make sure the auth adds content-length: 0 if we don't have any content length defined (for put requests)
        """

        mock_request = Request(method='PUT',
                               url="http://static.johnsmith.net:8080/db-backup.dat.gz",
                               headers={'Date': 'Tue, 27 Mar 2007 21:06:08 +0000',
                                        'x-amz-acl': 'public-read',
                                        'Content-type': 'application/x-download'})
        # Call auth
        self.auth(mock_request)

        # test Content-Length
        self.assertEquals(mock_request.headers['Content-Length'], '0')

    def test_list_all_buckets(self):
        mock_request = Request(method='GET',
                               url="http://s3.amazonaws.com",
                               headers={'Date': 'Wed, 28 Mar 2007 01:29:59 +0000'})

        # Call auth
        self.auth(mock_request)

        # test authorization code
        self.assertEquals(mock_request.headers['Authorization'],
                          'AWS AKIAIOSFODNN7EXAMPLE:qGdzdERIC03wnaRNKh6OqZehG9s=')

    def test_unicode_keys(self):
        mock_request = Request(method='GET',
                               url="http://s3.amazonaws.com/dictionary/fran%C3%A7ais/pr%c3%a9f%c3%a8re",
                               headers={'Date': 'Wed, 28 Mar 2007 01:49:49 +0000'})

        # Call auth
        self.auth(mock_request)

        # test authorization code
        self.assertEquals(mock_request.headers['Authorization'],
                          'AWS AKIAIOSFODNN7EXAMPLE:DNEZGsoieTZ92F3bUfSPQcbGmlM=')

    def test_simple_signature(self):
        self.auth = S3Auth('AKID', 'secret')
        mock_request = Request(method='POST', url='/', headers={'Date': 'DATE-STRING'})

        flexmock(self.auth).should_receive('string_to_sign').and_return('string-to-sign')

        self.auth(mock_request)

        self.assertEquals(mock_request.headers['Authorization'], 'AWS AKID:Gg5WLabTOvH0WMd15wv7lWe4zK0=')


    def test_string_to_sign(self):
        mock_request = Request(method='POST', url='/', headers={'Date': 'DATE-STRING'})

        target = """
POST


DATE-STRING
/
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_includes_content_md5_and_content_type(self):
        mock_request = Request(method='POST', url='/',
                               headers={'Date': 'DATE-STRING',
                                        'Content-Type': 'CONTENT-TYPE',
                                        'Content-MD5': 'CONTENT-MD5'})

        target = """
POST
CONTENT-MD5
CONTENT-TYPE
DATE-STRING
/
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_includes_the_http_method(self):
        mock_request = Request(method='VERB', url='/',
                               headers={'Date': 'DATE-STRING'})

        target = """
VERB


DATE-STRING
/
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)


    def test_sts_includes_any_x_amz_headers_but_not_others(self):
        mock_request = Request(method='POST', url='/',
                               headers={'Date': 'DATE-STRING',
                                        'X-Amz-Abc': 'abc',
                                        'X-Amz-Xyz': 'xyz',
                                        'random-header': 'random'})

        target = """
POST


DATE-STRING
x-amz-abc:abc
x-amz-xyz:xyz
/
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_includes_x_amz_headers_that_are_lower_cased(self):
        mock_request = Request(method='POST', url='/',
                               headers={'Date': 'DATE-STRING',
                                        'x-amz-Abc': 'abc',
                                        'x-amz-Xyz': 'xyz',
                                        'random-header': 'random'})

        target = """
POST


DATE-STRING
x-amz-abc:abc
x-amz-xyz:xyz
/
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_sorts_headers_by_their_name(self):
        mock_request = Request(method='POST', url='/',
                               headers={'Date': 'DATE-STRING',
                                        'x-amz-Abc': 'abc',
                                        'x-amz-Xyz': 'xyz',
                                        'x-amz-mno': 'mno',
                                        'random-header': 'random'})

        target = """
POST


DATE-STRING
x-amz-abc:abc
x-amz-mno:mno
x-amz-xyz:xyz
/
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_builds_a_canonical_resource_from_the_path(self):
        mock_request = Request(method='POST', url='/bucket_name/key',
                               headers={'Date': 'DATE-STRING'})

        target = """
POST


DATE-STRING
/bucket_name/key
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_appends_the_bucket_to_the_path_when_it_is_part_of_the_hostname(self):
        mock_request = Request(method='POST', url='http://bucket-name.s3.amazonaws.com/',
                               headers={'Date': 'DATE-STRING'})

        target = """
POST


DATE-STRING
/bucket-name/
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_appends_the_subresource_portion_of_the_path_querystring(self):
        mock_request = Request(method='POST', url='http://bucket-name.s3.amazonaws.com/?acl',
                               headers={'Date': 'DATE-STRING'})

        target = """
POST


DATE-STRING
/bucket-name/?acl
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_includes_sub_resource_value_when_present(self):
        mock_request = Request(method='POST', url='/bucket_name/key?versionId=123',
                               headers={'Date': 'DATE-STRING'})

        target = """
POST


DATE-STRING
/bucket_name/key?versionId=123
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_omits_non_sub_resource_querystring_params_from_the_resource_string(self):
        mock_request = Request(method='POST', url='/?versionId=abc&next-marker=xyz',
                               headers={'Date': 'DATE-STRING'})

        target = """
POST


DATE-STRING
/?versionId=abc
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

    #
    #     def test_sts_sorts_sub_resources_by_name(self):
    #         mock_request = Request(method='POST', url='/?logging&acl&website&torrent=123',
    #                                headers={'Date': 'DATE-STRING'})
    #
    #         target = """
    # POST
    #
    #
    # DATE-STRING
    # /?acl&logging&torrent=123&website
    # """.strip()
    #
    #         self.assertEquals(self.auth.string_to_sign(mock_request), target)

    def test_sts_includes_the_un_decoded_query_string_param_for_sub_resources(self):
        mock_request = Request(method='POST', url='/?versionId=a%2Bb',
                               headers={'Date': 'DATE-STRING'})

        target = """
POST


DATE-STRING
/?versionId=a%2Bb
""".strip()

        self.assertEquals(self.auth.string_to_sign(mock_request), target)

        #

#     def test_sts_includes_the_non_encoded_query_string_get_header_overrides(self):
#         mock_request = Request(method='POST', url='/?response-content-type=a%2Bb',
#                                headers={'Date': 'DATE-STRING'})
#
#         target = """
# POST
#
#
# DATE-STRING
# /?response-content-type=a+b
# """.strip()
#
#         self.assertEquals(self.auth.string_to_sign(mock_request), target)

########NEW FILE########
__FILENAME__ = test_bucket_iterator
__author__ = 'shlomiatar'

########NEW FILE########
__FILENAME__ = test_conn
# -*- coding: utf-8 -*-

import unittest
from tinys3 import Connection
from tinys3.auth import S3Auth
from flexmock import flexmock

TEST_SECRET_KEY = 'TEST_SECRET_KEY'
TEST_ACCESS_KEY = 'TEST_ACCESS_KEY'
TEST_BUCKET = 'bucket'
TEST_DATA = 'test test test' * 2


class TestConn(unittest.TestCase):
    def setUp(self):
        self.conn = Connection(TEST_ACCESS_KEY,TEST_SECRET_KEY, default_bucket=TEST_BUCKET, tls=True)

    def test_creation(self):
        """
        Test the creation of a connection
        """

        self.assertTrue(isinstance(self.conn.auth, S3Auth))
        self.assertEquals(self.conn.default_bucket, TEST_BUCKET)
        self.assertEquals(self.conn.tls, True)
        self.assertEquals(self.conn.endpoint, "s3.amazonaws.com")

########NEW FILE########
__FILENAME__ = test_non_upload_requests
# -*- coding: utf-8 -*-
from datetime import timedelta
import mimetypes
import unittest
from flexmock import flexmock
from tinys3.request_factory import CopyRequest, S3Request, UpdateMetadataRequest, DeleteRequest, GetRequest
from tinys3 import Connection

TEST_AUTH = ("TEST_ACCESS_KEY", "TEST_SECRET_KEY")


class TestNonUploadRequests(unittest.TestCase):
    def setUp(self):
        """
        Create a default connection
        """
        self.conn = Connection("TEST_ACCESS_KEY", "TEST_SECRET_KEY", tls=True)

    def test_url_generation(self):
        """
        Check that the url generation function works properly
        """

        r = S3Request(self.conn)

        # Simple with tls
        url = r.bucket_url('test_key', 'test_bucket')
        self.assertEqual(url, 'https://s3.amazonaws.com/test_bucket/test_key', 'Simple url with SSL')

        # change connection to non-http
        self.conn.tls = False

        r = S3Request(self.conn)

        # Test the simplest url
        url = r.bucket_url('test_key', 'test_bucket')
        self.assertEqual(url, 'http://s3.amazonaws.com/test_bucket/test_key', 'Simple url')

        # Key with / prefix
        url = r.bucket_url('/test_key', 'test_bucket')
        self.assertEqual(url, 'http://s3.amazonaws.com/test_bucket/test_key', 'Key with / prefix')

        # Nested key
        url = r.bucket_url('folder/for/key/test_key', 'test_bucket')
        self.assertEqual(url, 'http://s3.amazonaws.com/test_bucket/folder/for/key/test_key', 'Nested key')

    def _mock_adapter(self, request):
        """
        Creates a mock object and replace the result of the adapter method with is
        """
        mock_obj = flexmock()
        flexmock(request).should_receive('adapter').and_return(mock_obj)

        return mock_obj

    def test_delete_request(self):
        """
        Test the generation of a delete request
        """

        r = DeleteRequest(self.conn, 'key_to_delete', 'bucket')

        mock = self._mock_adapter(r)

        mock.should_receive('delete').with_args('https://s3.amazonaws.com/bucket/key_to_delete',
                                                auth=self.conn.auth).and_return(self._mock_response())

        r.run()

    def test_get_request(self):
        """
        Test the generation of a get request
        """

        r = GetRequest(self.conn, 'key_to_get', 'bucket')

        mock = self._mock_adapter(r)

        mock.should_receive('get').with_args('https://s3.amazonaws.com/bucket/key_to_get',
                                             auth=self.conn.auth).and_return(self._mock_response())

        r.run()

    def test_update_metadata(self):
        """
        Test the generation of an update metadata request
        """

        r = UpdateMetadataRequest(self.conn, 'key_to_update', 'bucket', {'example-meta-key': 'example-meta-value'},
                                  True)

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-copy-source': '/bucket/key_to_update',
            'x-amz-metadata-directive': 'REPLACE',
            'x-amz-acl': 'public-read',
            'example-meta-key': 'example-meta-value'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/key_to_update',
            headers=expected_headers,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

    def test_copy(self):
        """
        Test the generation of a copy request
        """

        r = CopyRequest(self.conn, 'from_key', 'from_bucket', 'to_key', 'to_bucket', None, False)

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-copy-source': '/from_bucket/from_key',
            'x-amz-metadata-directive': 'COPY',
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/to_bucket/to_key',
            headers=expected_headers,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

    def _mock_response(self):
        """
        Create a mock response with 'raise_for_status' method
        """

        return flexmock(raise_for_status=lambda: None)

########NEW FILE########
__FILENAME__ = test_pool
# -*- coding: utf-8 -*-

import threading
import unittest
from flexmock import flexmock
from nose.tools import raises
import time
from tinys3.auth import S3Auth
from tinys3.pool import Pool
from .test_conn import TEST_SECRET_KEY, TEST_ACCESS_KEY
from concurrent.futures import ThreadPoolExecutor, Future
import concurrent.futures

DUMMY_OBJECT = 'DUMMY'


class TestPool(unittest.TestCase):
    def test_pool_creation(self):
        """
        Test creating a pool
        """

        # Test new pool with auth
        pool = Pool(TEST_ACCESS_KEY, TEST_SECRET_KEY, default_bucket='bucket', tls=True)

        self.assertEquals(pool.tls, True)
        self.assertEquals(pool.default_bucket, 'bucket')
        self.assertTrue(isinstance(pool.auth, S3Auth))
        self.assertTrue(isinstance(pool.executor, ThreadPoolExecutor))

        # Test new pool with different size
        pool = Pool(TEST_ACCESS_KEY, TEST_SECRET_KEY, size=25)
        self.assertEquals(pool.executor._max_workers, 25)


    def test_as_completed(self):
        """
        Test the as_completed method
        """

        # Create mock futures
        futures = [Future(), Future(), Future()]

        # Create a default pool
        pool = Pool(TEST_ACCESS_KEY, TEST_SECRET_KEY)

        # Resolve futures with a simple object
        for i in futures:
            i.set_result(DUMMY_OBJECT)

        # Make sure all the results are dummy objects
        for i in pool.as_completed(futures):
            self.assertEquals(i, DUMMY_OBJECT)

    def test_all_completed(self):
        """
        Test the all completed
        """
        # Create mock futures
        futures = [Future(), Future(), Future()]

        # Create a default pool
        pool = Pool(TEST_ACCESS_KEY, TEST_SECRET_KEY)

        # Resolve futures with a simple object
        for i in futures:
            i.set_result(DUMMY_OBJECT)

        # Make sure all the results are dummy objects
        for i in pool.all_completed(futures):
            self.assertEquals(i, DUMMY_OBJECT)

    def test_pool_as_context_manager(self):
        """
        Test the pool's context_management ability
        """

        pool = Pool(TEST_ACCESS_KEY, TEST_SECRET_KEY)

        flexmock(pool).should_receive('close')

        with pool as p:
            # do nothing
            pass
########NEW FILE########
__FILENAME__ = test_upload_request
from datetime import timedelta
import unittest
from flexmock import flexmock
from tinys3 import Connection
from tinys3.request_factory import UploadRequest


# Support for python 2/3
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class TestUploadRequest(unittest.TestCase):
    def setUp(self):
        """
        Create a default connection
        """
        self.conn = Connection("TEST_ACCESS_KEY", "TEST_SECRET_KEY", tls=True)

        self.dummy_data = StringIO('DUMMY_DATA')

    def _mock_adapter(self, request):
        """
        Creates a mock object and replace the result of the adapter method with is
        """
        mock_obj = flexmock()
        flexmock(request).should_receive('adapter').and_return(mock_obj)

        return mock_obj

    def test_simple_upload(self):
        """
        Test the simplest case of upload
        """

        r = UploadRequest(self.conn, 'upload_key', self.dummy_data, 'bucket')

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'application/octet-stream'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/upload_key',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

    def _mock_response(self):
        """
        Create a mock response with 'raise_for_status' method
        """

        return flexmock(raise_for_status=lambda: None)

    def test_upload_content_type(self):
        """
        Test automatic/explicit content type setting
        """

        # No need to test fallback case ('application/octet-stream'), because
        # it was tested on the 'test_simple_upload' test

        # Test auto content type guessing
        r = UploadRequest(self.conn, 'test_zip_key.zip', self.dummy_data, 'bucket')

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'application/zip'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/test_zip_key.zip',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

        # Test explicit content setting
        r = UploadRequest(self.conn, 'test_zip_key.zip', self.dummy_data, 'bucket', content_type='candy/smore')

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'candy/smore'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/test_zip_key.zip',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

    def test_upload_expires(self):
        """
        Test setting of expires headers
        """

        # Test max expiry headers

        r = UploadRequest(self.conn, 'test_zip_key.zip', self.dummy_data, 'bucket', expires='max')

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'application/zip',
            'Cache-Control': 'max-age=31536000, public'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/test_zip_key.zip',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

        # Test number expiry
        r = UploadRequest(self.conn, 'test_zip_key.zip', self.dummy_data, 'bucket', expires=1337)

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'application/zip',
            'Cache-Control': 'max-age=1337, public'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/test_zip_key.zip',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

        # Test timedelta expiry

        r = UploadRequest(self.conn, 'test_zip_key.zip', self.dummy_data, 'bucket', expires=timedelta(weeks=2))

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'application/zip',
            'Cache-Control': 'max-age=1209600, public'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/test_zip_key.zip',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

    def test_upload_extra_headers(self):
        """
        Test providing extra headers to the upload request
        """

        r = UploadRequest(self.conn, 'test_zip_key.zip', self.dummy_data, 'bucket',
                          extra_headers={'example-meta-key': 'example-meta-value'})

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'application/zip',
            'example-meta-key': 'example-meta-value'
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/test_zip_key.zip',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

    def test_auto_close(self):
        """
        Test auto closing of the stream automatically
        """

        r = UploadRequest(self.conn, 'test_zip_key.zip', self.dummy_data, 'bucket',
                          close=True)

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'application/zip',
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/test_zip_key.zip',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

        self.assertTrue(self.dummy_data.closed)

    def test_auto_rewind(self):
        """
        Test auto rewinding of the input stream
        """

        # seek the data
        self.dummy_data.seek(5)

        r = UploadRequest(self.conn, 'test_zip_key.zip', self.dummy_data, 'bucket',
                          rewind=True)

        mock = self._mock_adapter(r)

        expected_headers = {
            'x-amz-acl': 'public-read',
            'Content-Type': 'application/zip',
        }

        mock.should_receive('put').with_args(
            'https://s3.amazonaws.com/bucket/test_zip_key.zip',
            headers=expected_headers,
            data=self.dummy_data,
            auth=self.conn.auth
        ).and_return(self._mock_response())

        r.run()

        self.assertEqual(self.dummy_data.tell(), 0)

########NEW FILE########
__FILENAME__ = util
import os


class LenWrapperStream(object):
    """
    A simple class to wrap a stream and provide length capability
    for streams like cStringIO

     We do it because requests will try to fallback to chuncked transfer if
     it can't extract the len attribute of the object it gets, and S3 doesn't
     support chuncked transfer.
     In some cases, like cStringIO, it may cause some issues, so we wrap the stream
     with a class of our own, that will proxy the stream and provide a proper
     len attribute
    """

    def __init__(self, stream):
        """
        Creates a new wrapper from the given stream

        Params:
            - stream    The baseline stream

        """
        self.stream = stream

    def read(self, n=-1):
        """
        Proxy for reading the stream
        """
        return self.stream.read(n)

    def __iter__(self):
        """
        Proxy for iterating the stream
        """
        return self.stream

    def seek(self, pos, mode=0):
        """
        Proxy for the `seek` method of the underlying stream
        """
        return self.stream.seek(pos, mode)

    def tell(self):
        """
        Proxy for the `tell` method of the underlying stream
        """
        return self.stream.tell()

    def __len__(self):
        """
        Calculate the stream length in a fail-safe way
        """
        o = self.stream

        # If we have a '__len__' method
        if hasattr(o, '__len__'):
            return len(o)

        # If we have a len property
        if hasattr(o, 'len'):
            return o.len

        # If we have a fileno property
        if hasattr(o, 'fileno'):
            try:
                return os.fstat(o.fileno()).st_size
            except IOError:
                pass  # fallback to the manual way, this is useful when using something like BytesIO


        # calculate based on bytes to end of content
        # get our start position
        start_pos = o.tell()
        # move to the end
        o.seek(0, os.SEEK_END)
        # Our len is end - start position
        size = o.tell() - start_pos
        # Seek the stream back to the start position
        o.seek(start_pos)
        # Return the size
        return size

    def __eq__(self, other):
        """
        Make sure equal method works as expected (comparing the underlying stream and not the wrapper)
        """
        if self.stream == other:
            return True

        if isinstance(other, LenWrapperStream) and other.stream == self.stream:
            return True

    @property
    def closed(self):
        """
        Proxy for the underlying stream closed property
        """
        return self.stream.closed

    def __repr__(self):
        """
        Proxy for the repr of the stream
        """
        return repr(self.stream)
########NEW FILE########
