__FILENAME__ = awsauth
# -*- coding: utf-8 -*-
import base64
import hmac

from hashlib import sha1 as sha
py3k = False
try:
    from urlparse import urlparse
    from base64 import encodestring
 
except:
    py3k = True
    from urllib.parse import urlparse
    from base64 import encodebytes as encodestring

from email.utils import formatdate

from requests.auth import AuthBase


class S3Auth(AuthBase):

    """Attaches AWS Authentication to the given Request object."""

    service_base_url = 's3.amazonaws.com'
    # List of Query String Arguments of Interest
    special_params = [
        'acl', 'location', 'logging', 'partNumber', 'policy', 'requestPayment',
        'torrent', 'versioning', 'versionId', 'versions', 'website', 'uploads',
        'uploadId', 'response-content-type', 'response-content-language',
        'response-expires', 'response-cache-control', 'delete', 'lifecycle',
        'response-content-disposition', 'response-content-encoding'
    ]

    def __init__(self, access_key, secret_key, service_url=None):
        if service_url:
            self.service_base_url = service_url
        self.access_key = str(access_key)
        self.secret_key = str(secret_key)

    def __call__(self, r):
        # Create date header if it is not created yet.
        if not 'date' in r.headers and not 'x-amz-date' in r.headers:
            r.headers['date'] = formatdate(
                timeval=None,
                localtime=False,
                usegmt=True)
        signature = self.get_signature(r)
        if py3k:
            signature = signature.decode('utf-8')
        r.headers['Authorization'] = 'AWS %s:%s' % (self.access_key, signature)
        return r

    def get_signature(self, r):
        canonical_string = self.get_canonical_string(
            r.url, r.headers, r.method)
        if py3k:
            key = self.secret_key.encode('utf-8')
            msg = canonical_string.encode('utf-8')
        else:
            key = self.secret_key
            msg = canonical_string
        h = hmac.new(key, msg, digestmod=sha)
        return encodestring(h.digest()).strip()

    def get_canonical_string(self, url, headers, method):
        parsedurl = urlparse(url)
        objectkey = parsedurl.path[1:]
        query_args = sorted(parsedurl.query.split('&'))

        bucket = parsedurl.netloc[:-len(self.service_base_url)]
        if len(bucket) > 1:
            # remove last dot
            bucket = bucket[:-1]

        interesting_headers = {
            'content-md5': '',
            'content-type': '',
            'date': ''}
        for key in headers:
            lk = key.lower()
            try:
                lk = lk.decode('utf-8')
            except:
                pass
            if headers[key] and (lk in interesting_headers.keys() or lk.startswith('x-amz-')):
                interesting_headers[lk] = headers[key].strip()

        # If x-amz-date is used it supersedes the date header.
        if not py3k:
            if 'x-amz-date' in interesting_headers:
                interesting_headers['date'] = ''
        else:
            if 'x-amz-date' in interesting_headers:
                interesting_headers['date'] = ''

        buf = '%s\n' % method
        for key in sorted(interesting_headers.keys()):
            val = interesting_headers[key]
            if key.startswith('x-amz-'):
                buf += '%s:%s\n' % (key, val)
            else:
                buf += '%s\n' % val

        # append the bucket if it exists
        if bucket != '':
            buf += '/%s' % bucket

        # add the objectkey. even if it doesn't exist, add the slash
        buf += '/%s' % objectkey

        params_found = False

        # handle special query string arguments
        for q in query_args:
            k = q.split('=')[0]
            if k in self.special_params:
                if params_found:
                    buf += '&%s' % q
                else:
                    buf += '?%s' % q
                params_found = True
        return buf

########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python

from __future__ import print_function

import requests

from awsauth import S3Auth

import gzip

import urllib

ACCESS_KEY = "ACCESSKEYXXXXXXXXXXXX"
SECRET_KEY = "AWSSECRETKEYXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

acceptableAccessCodes = (200, 204) # # https://forums.aws.amazon.com/thread.jspa?threadID=28799: http://docs.amazonwebservices.com/AmazonS3/latest/API/RESTObjectDELETE.html

if __name__ == '__main__':

    confirmIt = u'Sam is sweet' # Data needs to be in unicode, or it will fail

    bucketName = 'mybucket'
    objectName = ['myfile.txt', 'my+file.txt']

    for o in objectName:
        # Creating a file
        r = requests.put(('http://%s.s3.amazonaws.com/%s' % (bucketName, o)), data=confirmIt, auth=S3Auth(ACCESS_KEY, SECRET_KEY))
        if r.status_code not in acceptableAccessCodes:
            r.raise_for_status()

        # Downloading a file
        r = requests.get(('http://%s.s3.amazonaws.com/%s' % (bucketName, o)), auth=S3Auth(ACCESS_KEY, SECRET_KEY))
        if r.status_code not in acceptableAccessCodes:
            r.raise_for_status()

        if r.content == confirmIt:
            print('Hala Madrid!')

        # Removing a file
        r = requests.delete(('http://%s.s3.amazonaws.com/%s' % (bucketName, o)), auth=S3Auth(ACCESS_KEY, SECRET_KEY))
        if r.status_code not in acceptableAccessCodes:
            r.raise_for_status()

########NEW FILE########
__FILENAME__ = test
import unittest
import os
import requests
from awsauth import S3Auth


TEST_BUCKET = 'testpolpol'
ACCESS_KEY = 'ACCESSKEYXXXXXXXXXXXX'
SECRET_KEY = 'AWSSECRETKEYXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
if 'AWS_ACCESS_KEY' in os.environ:
    ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
if 'AWS_SECRET_KEY' in os.environ:
    SECRET_KEY = os.environ['AWS_SECRET_KEY']

class TestAWS(unittest.TestCase):
    def setUp(self):
        self.auth=S3Auth(ACCESS_KEY, SECRET_KEY)
    
    def test_put_get_delete(self):
        testdata = 'Sam is sweet'
        r = requests.put('http://'+ TEST_BUCKET + '.s3.amazonaws.com/myfile.txt', data=testdata, auth=self.auth)
        self.assertEqual(r.status_code, 200)
        # Downloading a file
        r = requests.get('http://'+ TEST_BUCKET + '.s3.amazonaws.com/myfile.txt', auth=self.auth)
        self.assertEqual(r.status_code, 200) 
        self.assertEqual(r.text, 'Sam is sweet')
        # Removing a file
        r = requests.delete('http://'+ TEST_BUCKET + '.s3.amazonaws.com/myfile.txt', auth=self.auth)
        self.assertEqual(r.status_code, 204)        
        
    def test_put_get_delete_filnamehasplus(self):
        testdata = 'Sam is sweet'
        filename = 'my+file.txt'
        url = 'http://'+ TEST_BUCKET + '.s3.amazonaws.com/%s'%(filename)
        r = requests.put(url, data=testdata, auth=self.auth)
        self.assertEqual(r.status_code, 200)
        # Downloading a file
        r = requests.get(url, auth=self.auth)
        self.assertEqual(r.status_code, 200) 
        self.assertEqual(r.text, testdata)
        # Removing a file
        r = requests.delete(url, auth=self.auth)
        self.assertEqual(r.status_code, 204)

    def test_put_get_delete_filname_encoded(self):
        testdata = 'Sam is sweet'
        filename = 'my%20file.txt'
        url = 'http://'+ TEST_BUCKET + '.s3.amazonaws.com/%s'%(filename)
        r = requests.put(url, data=testdata, auth=self.auth)
        self.assertEqual(r.status_code, 200)
        # Downloading a file
        r = requests.get(url, auth=self.auth)
        self.assertEqual(r.status_code, 200) 
        self.assertEqual(r.text, testdata)
        # Removing a file
        r = requests.delete(url, auth=self.auth)
        self.assertEqual(r.status_code, 204)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
