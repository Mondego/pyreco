__FILENAME__ = env
from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from dpxdt.server import models
target_metadata = models.Run.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix='sqlalchemy.',
                poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
                connection=connection,
                target_metadata=target_metadata
                )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


########NEW FILE########
__FILENAME__ = alembic
#!/usr/bin/env python

# I always have trouble with virtualenv, pip, pkg_resources, etc, so this is
# a boostrapping script to workaround how flaky these tools are.

import sys
sys.path.insert(0, './dependencies/lib/')

import alembic.config

alembic.config.main()

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration for local development."""

import os
from secrets import *

SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/test.db'

SERVER_NAME = os.environ.get('SERVER_NAME', None)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# Google OAuth2 login config for local development.
GOOGLE_OAUTH2_EMAIL_ADDRESS = (
    '918724168220-nqq27o7so1p7stukds23oo2vof5gkfmh@'
    'developer.gserviceaccount.com')
GOOGLE_OAUTH2_REDIRECT_PATH = '/oauth2callback'
GOOGLE_OAUTH2_REDIRECT_URI = (
    'http://localhost:5000' + GOOGLE_OAUTH2_REDIRECT_PATH)
GOOGLE_OAUTH2_CLIENT_ID = (
    '918724168220-nqq27o7so1p7stukds23oo2vof5gkfmh.apps.googleusercontent.com')
GOOGLE_OAUTH2_CLIENT_SECRET = 'EhiCP-PuQYN0OsWGAELTUHyl'

CACHE_TYPE = 'simple'
CACHE_DEFAULT_TIMEOUT = 600

SESSION_COOKIE_DOMAIN = None

MAIL_DEFAULT_SENDER = 'Depicted <nobody@localhost>'
MAIL_SUPPRESS_SEND = True
MAIL_USE_APPENGINE = False

########NEW FILE########
__FILENAME__ = blobstore
# Copyright 2013 Google Inc. All Rights Reserved.


"""A sample app that operates on GCS files with blobstore API."""

from __future__ import with_statement

import cloudstorage as gcs
import main
import webapp2

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers


def CreateFile(filename):
  """Create a GCS file with GCS client lib.

  Args:
    filename: GCS filename.

  Returns:
    The corresponding string blobkey for this GCS file.
  """
  with gcs.open(filename, 'w') as f:
    f.write('abcde\n')

  blobstore_filename = '/gs' + filename
  return blobstore.create_gs_key(blobstore_filename)


class GCSHandler(webapp2.RequestHandler):

  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    gcs_filename = main.BUCKET + '/blobstore_demo'
    blob_key = CreateFile(gcs_filename)

    self.response.write('Fetched data %s\n' %
                        blobstore.fetch_data(blob_key, 0, 2))

    blobstore.delete(blob_key)


class GCSServingHandler(blobstore_handlers.BlobstoreDownloadHandler):

  def get(self):
    blob_key = CreateFile(main.BUCKET + '/blobstore_serving_demo')
    self.send_blob(blob_key)


app = webapp2.WSGIApplication([('/blobstore/ops', GCSHandler),
                               ('/blobstore/serve', GCSServingHandler)],
                              debug=True)

########NEW FILE########
__FILENAME__ = api_utils
# Copyright 2013 Google Inc. All Rights Reserved.

"""Util functions and classes for cloudstorage_api."""



__all__ = ['set_default_retry_params',
           'RetryParams',
          ]

import copy
import httplib
import logging
import math
import os
import threading
import time


try:
  from google.appengine.api import urlfetch
  from google.appengine.datastore import datastore_rpc
  from google.appengine import runtime
  from google.appengine.runtime import apiproxy_errors
except ImportError:
  from google.appengine.api import urlfetch
  from google.appengine.datastore import datastore_rpc
  from google.appengine import runtime
  from google.appengine.runtime import apiproxy_errors


_RETRIABLE_EXCEPTIONS = (urlfetch.DownloadError,
                         apiproxy_errors.Error)

_thread_local_settings = threading.local()
_thread_local_settings.default_retry_params = None


def set_default_retry_params(retry_params):
  """Set a default RetryParams for current thread current request."""
  _thread_local_settings.default_retry_params = copy.copy(retry_params)


def _get_default_retry_params():
  """Get default RetryParams for current request and current thread.

  Returns:
    A new instance of the default RetryParams.
  """
  default = getattr(_thread_local_settings, 'default_retry_params', None)
  if default is None or not default.belong_to_current_request():
    return RetryParams()
  else:
    return copy.copy(default)


def _should_retry(resp):
  """Given a urlfetch response, decide whether to retry that request."""
  return (resp.status_code == httplib.REQUEST_TIMEOUT or
          (resp.status_code >= 500 and
           resp.status_code < 600))


class RetryParams(object):
  """Retry configuration parameters."""

  @datastore_rpc._positional(1)
  def __init__(self,
               backoff_factor=2.0,
               initial_delay=0.1,
               max_delay=10.0,
               min_retries=2,
               max_retries=5,
               max_retry_period=30.0,
               urlfetch_timeout=None):
    """Init.

    This object is unique per request per thread.

    Library will retry according to this setting when App Engine Server
    can't call urlfetch, urlfetch timed out, or urlfetch got a 408 or
    500-600 response.

    Args:
      backoff_factor: exponential backoff multiplier.
      initial_delay: seconds to delay for the first retry.
      max_delay: max seconds to delay for every retry.
      min_retries: min number of times to retry. This value is automatically
        capped by max_retries.
      max_retries: max number of times to retry. Set this to 0 for no retry.
      max_retry_period: max total seconds spent on retry. Retry stops when
       this period passed AND min_retries has been attempted.
      urlfetch_timeout: timeout for urlfetch in seconds. Could be None.
    """
    self.backoff_factor = self._check('backoff_factor', backoff_factor)
    self.initial_delay = self._check('initial_delay', initial_delay)
    self.max_delay = self._check('max_delay', max_delay)
    self.max_retry_period = self._check('max_retry_period', max_retry_period)
    self.max_retries = self._check('max_retries', max_retries, True, int)
    self.min_retries = self._check('min_retries', min_retries, True, int)
    if self.min_retries > self.max_retries:
      self.min_retries = self.max_retries

    self.urlfetch_timeout = None
    if urlfetch_timeout is not None:
      self.urlfetch_timeout = self._check('urlfetch_timeout', urlfetch_timeout)

    self._request_id = os.getenv('REQUEST_LOG_ID')

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not self.__eq__(other)

  @classmethod
  def _check(cls, name, val, can_be_zero=False, val_type=float):
    """Check init arguments.

    Args:
      name: name of the argument. For logging purpose.
      val: value. Value has to be non negative number.
      can_be_zero: whether value can be zero.
      val_type: Python type of the value.

    Returns:
      The value.

    Raises:
      ValueError: when invalid value is passed in.
      TypeError: when invalid value type is passed in.
    """
    valid_types = [val_type]
    if val_type is float:
      valid_types.append(int)

    if type(val) not in valid_types:
      raise TypeError(
          'Expect type %s for parameter %s' % (val_type.__name__, name))
    if val < 0:
      raise ValueError(
          'Value for parameter %s has to be greater than 0' % name)
    if not can_be_zero and val == 0:
      raise ValueError(
          'Value for parameter %s can not be 0' % name)
    return val

  def belong_to_current_request(self):
    return os.getenv('REQUEST_LOG_ID') == self._request_id

  def delay(self, n, start_time):
    """Calculate delay before the next retry.

    Args:
      n: the number of current attempt. The first attempt should be 1.
      start_time: the time when retry started in unix time.

    Returns:
      Number of seconds to wait before next retry. -1 if retry should give up.
    """
    if (n > self.max_retries or
        (n > self.min_retries and
         time.time() - start_time > self.max_retry_period)):
      return -1
    return min(
        math.pow(self.backoff_factor, n-1) * self.initial_delay,
        self.max_delay)


def _retry_fetch(url, retry_params, **kwds):
  """A blocking fetch function similar to urlfetch.fetch.

  This function should be used when a urlfetch has timed out or the response
  shows http request timeout. This function will put current thread to
  sleep between retry backoffs.

  Args:
    url: url to fetch.
    retry_params: an instance of RetryParams.
    **kwds: keyword arguments for urlfetch. If deadline is specified in kwds,
      it precedes the one in RetryParams. If none is specified, it's up to
      urlfetch to use its own default.

  Returns:
    A urlfetch response from the last retry. None if no retry was attempted.

  Raises:
    Whatever exception encountered during the last retry.
  """
  n = 1
  start_time = time.time()
  delay = retry_params.delay(n, start_time)
  if delay <= 0:
    return

  deadline = kwds.get('deadline', None)
  if deadline is None:
    kwds['deadline'] = retry_params.urlfetch_timeout

  while delay > 0:
    resp = None
    try:
      time.sleep(delay)
      resp = urlfetch.fetch(url, **kwds)
    except runtime.DeadlineExceededError:
      logging.info(
          'Urlfetch retry %s will exceed request deadline '
          'after %s seconds total', n, time.time() - start_time)
      raise
    except _RETRIABLE_EXCEPTIONS, e:
      pass

    n += 1
    delay = retry_params.delay(n, start_time)
    if resp and not _should_retry(resp):
      break
    elif resp:
      logging.info(
          'Got status %s from GCS. Will retry in %s seconds.',
          resp.status_code, delay)
    else:
      logging.info(
          'Got exception while contacting GCS. Will retry in %s seconds.',
          delay)
      logging.info(e)
    logging.debug('Tried to reach url %s', url)

  if resp:
    return resp

  logging.info('Urlfetch retry %s failed after %s seconds total',
               n - 1, time.time() - start_time)
  raise


########NEW FILE########
__FILENAME__ = cloudstorage_api
# Copyright 2012 Google Inc. All Rights Reserved.

"""File Interface for Google Cloud Storage."""



from __future__ import with_statement



__all__ = ['delete',
           'listbucket',
           'open',
           'stat',
          ]

import urllib
import xml.etree.ElementTree as ET
from . import common
from . import errors
from . import storage_api


def open(filename,
         mode='r',
         content_type=None,
         options=None,
         read_buffer_size=storage_api.ReadBuffer.DEFAULT_BUFFER_SIZE,
         retry_params=None,
         _account_id=None):
  """Opens a Google Cloud Storage file and returns it as a File-like object.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    mode: 'r' for reading mode. 'w' for writing mode.
      In reading mode, the file must exist. In writing mode, a file will
      be created or be overrode.
    content_type: The MIME type of the file. str. Only valid in writing mode.
    options: A str->basestring dict to specify additional headers to pass to
      GCS e.g. {'x-goog-acl': 'private', 'x-goog-meta-foo': 'foo'}.
      Supported options are x-goog-acl, x-goog-meta-, cache-control,
      content-disposition, and content-encoding.
      Only valid in writing mode.
      See https://developers.google.com/storage/docs/reference-headers
      for details.
    read_buffer_size: The buffer size for read. If buffer is empty, the read
      stream will asynchronously prefetch a new buffer before the next read().
      To minimize blocking for large files, always read in buffer size.
      To minimize number of requests for small files, set a larger
      buffer size.
    retry_params: An instance of api_utils.RetryParams for subsequent calls
      to GCS from this file handle. If None, the default one is used.
    _account_id: Internal-use only.

  Returns:
    A reading or writing buffer that supports File-like interface. Buffer
    must be closed after operations are done.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
    ValueError: invalid open mode or if content_type or options are specified
      in reading mode.
  """
  common.validate_file_path(filename)
  api = _get_storage_api(retry_params=retry_params, account_id=_account_id)

  if mode == 'w':
    common.validate_options(options)
    return storage_api.StreamingBuffer(api, filename, content_type, options)
  elif mode == 'r':
    if content_type or options:
      raise ValueError('Options and content_type can only be specified '
                       'for writing mode.')
    return storage_api.ReadBuffer(api,
                                  filename,
                                  max_buffer_size=read_buffer_size)
  else:
    raise ValueError('Invalid mode %s.' % mode)


def delete(filename, retry_params=None, _account_id=None):
  """Delete a Google Cloud Storage file.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Raises:
    errors.NotFoundError: if the file doesn't exist prior to deletion.
  """
  api = _get_storage_api(retry_params=retry_params, account_id=_account_id)
  common.validate_file_path(filename)
  status, _, _ = api.delete_object(filename)
  errors.check_status(status, [204])


def stat(filename, retry_params=None, _account_id=None):
  """Get GCSFileStat of a Google Cloud storage file.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Returns:
    a GCSFileStat object containing info about this file.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
  """
  common.validate_file_path(filename)
  api = _get_storage_api(retry_params=retry_params, account_id=_account_id)
  status, headers, _ = api.head_object(filename)
  errors.check_status(status, [200])
  file_stat = common.GCSFileStat(
      filename=filename,
      st_size=headers.get('content-length'),
      st_ctime=common.http_time_to_posix(headers.get('last-modified')),
      etag=headers.get('etag'),
      content_type=headers.get('content-type'),
      metadata=common.get_metadata(headers))

  return file_stat


def _copy2(src, dst, retry_params=None):
  """Copy the file content and metadata from src to dst.

  Internal use only!

  Args:
    src: /bucket/filename
    dst: /bucket/filename
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
  """
  common.validate_file_path(src)
  common.validate_file_path(dst)
  if src == dst:
    return

  api = _get_storage_api(retry_params=retry_params)
  status, headers, _ = api.put_object(
      dst,
      headers={'x-goog-copy-source': src,
               'Content-Length': '0'})
  errors.check_status(status, [200], headers)


def listbucket(bucket, marker=None, prefix=None, max_keys=None,
               retry_params=None, _account_id=None):
  """Return an GCSFileStat iterator over files in the given bucket.

  Optional arguments are to limit the result to a subset of files under bucket.

  This function is asynchronous. It does not block unless iterator is called
  before the iterator gets result.

  Args:
    bucket: A Google Cloud Storage bucket of form "/bucket".
    marker: A string after which (exclusive) to start listing.
    prefix: Limits the returned filenames to those with this prefix. no regex.
    max_keys: The maximum number of filenames to match. int.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Example:
    For files "/bucket/foo1", "/bucket/foo2", "/bucket/foo3", "/bucket/www",
    listbucket("/bucket", prefix="foo", marker="foo1")
    will match "/bucket/foo2" and "/bucket/foo3".

    See Google Cloud Storage documentation for more details and examples.
    https://developers.google.com/storage/docs/reference-methods#getbucket

  Returns:
    An GSFileStat iterator over matched files, sorted by filename.
    Only filename, etag, and st_size are set in these GSFileStat objects.
  """
  common.validate_bucket_path(bucket)
  api = _get_storage_api(retry_params=retry_params, account_id=_account_id)
  options = {}
  if marker:
    options['marker'] = marker
  if max_keys:
    options['max-keys'] = max_keys
  if prefix:
    options['prefix'] = prefix

  return _Bucket(api, bucket, options)


class _Bucket(object):
  """A wrapper for a GCS bucket as the return value of listbucket."""

  def __init__(self, api, path, options):
    """Initialize.

    Args:
      api: storage_api instance.
      path: bucket path of form '/bucket'.
      options: a dict of listbucket options. Please see listbucket doc.
    """
    self._api = api
    self._path = path
    self._options = options.copy()
    self._get_bucket_fut = self._api.get_bucket_async(
        self._path + '?' + urllib.urlencode(self._options))

  def _add_ns(self, tagname):
    return '{%(ns)s}%(tag)s' % {'ns': common.CS_XML_NS,
                                'tag': tagname}

  def __iter__(self):
    """Iter over the bucket.

    Yields:
      GCSFileStat: a GCSFileStat for an object in the bucket.
        They are ordered by GCSFileStat.filename.
    """
    total = 0
    while self._get_bucket_fut:
      status, _, content = self._get_bucket_fut.get_result()
      errors.check_status(status, [200])
      root = ET.fromstring(content)
      for contents in root.getiterator(self._add_ns('Contents')):
        last_modified = contents.find(self._add_ns('LastModified')).text
        st_ctime = common.dt_str_to_posix(last_modified)
        yield common.GCSFileStat(
            self._path + '/' + contents.find(self._add_ns('Key')).text,
            contents.find(self._add_ns('Size')).text,
            contents.find(self._add_ns('ETag')).text,
            st_ctime)
        total += 1

      max_keys = root.find(self._add_ns('MaxKeys'))
      next_marker = root.find(self._add_ns('NextMarker'))
      if (max_keys is None or total < int(max_keys.text)) and (
          next_marker is not None):
        self._options['marker'] = next_marker.text
        self._get_bucket_fut = self._api.get_bucket_async(
            self._path + '?' + urllib.urlencode(self._options))
      else:
        self._get_bucket_fut = None


def _get_storage_api(retry_params, account_id=None):
  """Returns storage_api instance for API methods.

  Args:
    retry_params: An instance of api_utils.RetryParams.
    account_id: Internal-use only.

  Returns:
    A storage_api instance to handle urlfetch work to GCS.
    On dev appserver, this instance by default will talk to a local stub
    unless common.ACCESS_TOKEN is set. That token will be used to talk
    to the real GCS.
  """


  api = storage_api._StorageApi(storage_api._StorageApi.full_control_scope,
                                service_account_id=account_id,
                                retry_params=retry_params)
  if common.local_run() and not common.get_access_token():
    api.api_url = 'http://' + common.LOCAL_API_HOST
  if common.get_access_token():
    api.token = common.get_access_token()
  return api

########NEW FILE########
__FILENAME__ = common
# Copyright 2012 Google Inc. All Rights Reserved.

"""Helpers shared by cloudstorage_stub and cloudstorage_api."""





__all__ = ['CS_XML_NS',
           'CSFileStat',
           'dt_str_to_posix',
           'LOCAL_API_HOST',
           'local_run',
           'get_access_token',
           'get_metadata',
           'GCSFileStat',
           'http_time_to_posix',
           'memory_usage',
           'posix_time_to_http',
           'posix_to_dt_str',
           'set_access_token',
           'validate_options',
           'validate_bucket_name',
           'validate_bucket_path',
           'validate_file_path',
          ]


import calendar
import datetime
from email import utils as email_utils
import logging
import os
import re

try:
  from google.appengine.api import runtime
except ImportError:
  from google.appengine.api import runtime


_GCS_BUCKET_REGEX_BASE = r'[a-z0-9\.\-_]{3,63}'
_GCS_BUCKET_REGEX = re.compile(_GCS_BUCKET_REGEX_BASE + r'$')
_GCS_BUCKET_PATH_REGEX = re.compile(r'/' + _GCS_BUCKET_REGEX_BASE + r'$')
_GCS_FULLPATH_REGEX = re.compile(r'/' + _GCS_BUCKET_REGEX_BASE + r'/.*')
_GCS_METADATA = ['x-goog-meta-',
                 'content-disposition',
                 'cache-control',
                 'content-encoding']
_GCS_OPTIONS = _GCS_METADATA + ['x-goog-acl']
CS_XML_NS = 'http://doc.s3.amazonaws.com/2006-03-01'
LOCAL_API_HOST = 'gcs-magicstring.appspot.com'
_access_token = ''


def set_access_token(access_token):
  """Set the shared access token to authenticate with Google Cloud Storage.

  When set, the library will always attempt to communicate with the
  real Google Cloud Storage with this token even when running on dev appserver.
  Note the token could expire so it's up to you to renew it.

  When absent, the library will automatically request and refresh a token
  on appserver, or when on dev appserver, talk to a Google Cloud Storage
  stub.

  Args:
    access_token: you can get one by run 'gsutil -d ls' and copy the
      str after 'Bearer'.
  """
  global _access_token
  _access_token = access_token


def get_access_token():
  """Returns the shared access token."""
  return _access_token


class GCSFileStat(object):
  """Container for GCS file stat."""

  def __init__(self,
               filename,
               st_size,
               etag,
               st_ctime,
               content_type=None,
               metadata=None):
    """Initialize.

    Args:
      filename: a Google Cloud Storage filename of form '/bucket/filename'.
      st_size: file size in bytes. long compatible.
      etag: hex digest of the md5 hash of the file's content. str.
      st_ctime: posix file creation time. float compatible.
      content_type: content type. str.
      metadata: a str->str dict of user specified options when creating
        the file. Possible keys are x-goog-meta-, content-disposition,
        content-encoding, and cache-control.
    """
    self.filename = filename
    self.st_size = long(st_size)
    self.st_ctime = float(st_ctime)
    if etag[0] == '"' and etag[-1] == '"':
      etag = etag[1:-1]
    self.etag = etag
    self.content_type = content_type
    self.metadata = metadata

  def __repr__(self):
    return (
        '(filename: %(filename)s, st_size: %(st_size)s, '
        'st_ctime: %(st_ctime)s, etag: %(etag)s, '
        'content_type: %(content_type)s, '
        'metadata: %(metadata)s)' %
        dict(filename=self.filename,
             st_size=self.st_size,
             st_ctime=self.st_ctime,
             etag=self.etag,
             content_type=self.content_type,
             metadata=self.metadata))


CSFileStat = GCSFileStat


def get_metadata(headers):
  """Get user defined options from HTTP response headers."""
  return dict((k, v) for k, v in headers.iteritems()
              if any(k.lower().startswith(valid) for valid in _GCS_METADATA))


def validate_bucket_name(name):
  """Validate a Google Storage bucket name.

  Args:
    name: a Google Storage bucket name with no prefix or suffix.

  Raises:
    ValueError: if name is invalid.
  """
  _validate_path(name)
  if not _GCS_BUCKET_REGEX.match(name):
    raise ValueError('Bucket should be 3-63 characters long using only a-z,'
                     '0-9, underscore, dash or dot but got %s' % name)


def validate_bucket_path(path):
  """Validate a Google Cloud Storage bucket path.

  Args:
    path: a Google Storage bucket path. It should have form '/bucket'.

  Raises:
    ValueError: if path is invalid.
  """
  _validate_path(path)
  if not _GCS_BUCKET_PATH_REGEX.match(path):
    raise ValueError('Bucket should have format /bucket '
                     'but got %s' % path)


def validate_file_path(path):
  """Validate a Google Cloud Storage file path.

  Args:
    path: a Google Storage file path. It should have form '/bucket/filename'.

  Raises:
    ValueError: if path is invalid.
  """
  _validate_path(path)
  if not _GCS_FULLPATH_REGEX.match(path):
    raise ValueError('Path should have format /bucket/filename '
                     'but got %s' % path)


def _validate_path(path):
  """Basic validation of Google Storage paths.

  Args:
    path: a Google Storage path. It should have form '/bucket/filename'
      or '/bucket'.

  Raises:
    ValueError: if path is invalid.
    TypeError: if path is not of type basestring.
  """
  if not path:
    raise ValueError('Path is empty')
  if not isinstance(path, basestring):
    raise TypeError('Path should be a string but is %s (%s).' %
                    (path.__class__, path))


def validate_options(options):
  """Validate Google Cloud Storage options.

  Args:
    options: a str->basestring dict of options to pass to Google Cloud Storage.

  Raises:
    ValueError: if option is not supported.
    TypeError: if option is not of type str or value of an option
      is not of type basestring.
  """
  if not options:
    return

  for k, v in options.iteritems():
    if not isinstance(k, str):
      raise TypeError('option %r should be a str.' % k)
    if not any(k.lower().startswith(valid) for valid in _GCS_OPTIONS):
      raise ValueError('option %s is not supported.' % k)
    if not isinstance(v, basestring):
      raise TypeError('value %r for option %s should be of type basestring.' %
                      v, k)


def http_time_to_posix(http_time):
  """Convert HTTP time format to posix time.

  See http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1
  for http time format.

  Args:
    http_time: time in RFC 2616 format. e.g.
      "Mon, 20 Nov 1995 19:12:08 GMT".

  Returns:
    A float of secs from unix epoch.
  """
  if http_time is not None:
    return email_utils.mktime_tz(email_utils.parsedate_tz(http_time))


def posix_time_to_http(posix_time):
  """Convert posix time to HTML header time format.

  Args:
    posix_time: unix time.

  Returns:
    A datatime str in RFC 2616 format.
  """
  if posix_time:
    return email_utils.formatdate(posix_time, usegmt=True)


_DT_FORMAT = '%Y-%m-%dT%H:%M:%S'


def dt_str_to_posix(dt_str):
  """format str to posix.

  datetime str is of format %Y-%m-%dT%H:%M:%S.%fZ,
  e.g. 2013-04-12T00:22:27.978Z. According to ISO 8601, T is a separator
  between date and time when they are on the same line.
  Z indicates UTC (zero meridian).

  A pointer: http://www.cl.cam.ac.uk/~mgk25/iso-time.html

  This is used to parse LastModified node from GCS's GET bucket XML response.

  Args:
    dt_str: A datetime str.

  Returns:
    A float of secs from unix epoch. By posix definition, epoch is midnight
    1970/1/1 UTC.
  """
  parsable, _ = dt_str.split('.')
  dt = datetime.datetime.strptime(parsable, _DT_FORMAT)
  return calendar.timegm(dt.utctimetuple())


def posix_to_dt_str(posix):
  """Reverse of str_to_datetime.

  This is used by GCS stub to generate GET bucket XML response.

  Args:
    posix: A float of secs from unix epoch.

  Returns:
    A datetime str.
  """
  dt = datetime.datetime.utcfromtimestamp(posix)
  dt_str = dt.strftime(_DT_FORMAT)
  return dt_str + '.000Z'


def local_run():
  """Whether running in dev appserver."""
  return ('SERVER_SOFTWARE' not in os.environ or
          os.environ['SERVER_SOFTWARE'].startswith('Development'))


def memory_usage(method):
  """Log memory usage before and after a method."""
  def wrapper(*args, **kwargs):
    logging.info('Memory before method %s is %s.',
                 method.__name__, runtime.memory_usage().current())
    result = method(*args, **kwargs)
    logging.info('Memory after method %s is %s',
                 method.__name__, runtime.memory_usage().current())
    return result
  return wrapper

########NEW FILE########
__FILENAME__ = errors
# Copyright 2012 Google Inc. All Rights Reserved.

"""Google Cloud Storage specific Files API calls."""





__all__ = ['AuthorizationError',
           'check_status',
           'Error',
           'FatalError',
           'ForbiddenError',
           'NotFoundError',
           'ServerError',
           'TimeoutError',
           'TransientError',
          ]

import httplib


class Error(Exception):
  """Base error for all gcs operations.

  Error can happen on GAE side or GCS server side.
  For details on a particular GCS HTTP response code, see
  https://developers.google.com/storage/docs/reference-status#standardcodes
  """


class TransientError(Error):
  """TransientError could be retried."""


class TimeoutError(TransientError):
  """HTTP 408 timeout."""


class FatalError(Error):
  """FatalError shouldn't be retried."""


class NotFoundError(FatalError):
  """HTTP 404 resource not found."""


class ForbiddenError(FatalError):
  """HTTP 403 Forbidden.

  While GCS replies with a 403 error for many reasons, the most common one
  is due to bucket permission not correctly setup for your app to access.
  """


class AuthorizationError(FatalError):
  """HTTP 401 authentication required.

  Unauthorized request has been received by GCS.

  This error is mostly handled by GCS client. GCS client will request
  a new access token and retry the request.
  """


class InvalidRange(FatalError):
  """HTTP 416 RequestRangeNotSatifiable."""


class ServerError(TransientError):
  """HTTP >= 500 server side error."""


def check_status(status, expected, headers=None):
  """Check HTTP response status is expected.

  Args:
    status: HTTP response status. int.
    expected: a list of expected statuses. A list of ints.
    headers: HTTP response headers.

  Raises:
    AuthorizationError: if authorization failed.
    NotFoundError: if an object that's expected to exist doesn't.
    TimeoutError: if HTTP request timed out.
    ServerError: if server experienced some errors.
    FatalError: if any other unexpected errors occurred.
  """
  if status in expected:
    return

  msg = ('Expect status %r from Google Storage. But got status %d. Response '
         'headers: %r' %
         (expected, status, headers))

  if status == httplib.UNAUTHORIZED:
    raise AuthorizationError(msg)
  elif status == httplib.FORBIDDEN:
    raise ForbiddenError(msg)
  elif status == httplib.NOT_FOUND:
    raise NotFoundError(msg)
  elif status == httplib.REQUEST_TIMEOUT:
    raise TimeoutError(msg)
  elif status == httplib.REQUESTED_RANGE_NOT_SATISFIABLE:
    raise InvalidRange(msg)
  elif status >= 500:
    raise ServerError(msg)
  else:
    raise FatalError(msg)

########NEW FILE########
__FILENAME__ = rest_api
# Copyright 2012 Google Inc. All Rights Reserved.

"""Base and helper classes for Google RESTful APIs."""





__all__ = ['add_sync_methods']

import httplib
import time

from . import api_utils

try:
  from google.appengine.api import app_identity
  from google.appengine.ext import ndb
except ImportError:
  from google.appengine.api import app_identity
  from google.appengine.ext import ndb


def _make_sync_method(name):
  """Helper to synthesize a synchronous method from an async method name.

  Used by the @add_sync_methods class decorator below.

  Args:
    name: The name of the synchronous method.

  Returns:
    A method (with first argument 'self') that retrieves and calls
    self.<name>, passing its own arguments, expects it to return a
    Future, and then waits for and returns that Future's result.
  """

  def sync_wrapper(self, *args, **kwds):
    method = getattr(self, name)
    future = method(*args, **kwds)
    return future.get_result()

  return sync_wrapper


def add_sync_methods(cls):
  """Class decorator to add synchronous methods corresponding to async methods.

  This modifies the class in place, adding additional methods to it.
  If a synchronous method of a given name already exists it is not
  replaced.

  Args:
    cls: A class.

  Returns:
    The same class, modified in place.
  """
  for name in cls.__dict__.keys():
    if name.endswith('_async'):
      sync_name = name[:-6]
      if not hasattr(cls, sync_name):
        setattr(cls, sync_name, _make_sync_method(name))
  return cls


class _AE_TokenStorage_(ndb.Model):
  """Entity to store app_identity tokens in memcache."""

  token = ndb.StringProperty()


@ndb.tasklet
def _make_token_async(scopes, service_account_id):
  """Get a fresh authentication token.

  Args:
    scopes: A list of scopes.
    service_account_id: Internal-use only.

  Returns:
    An tuple (token, expiration_time) where expiration_time is
    seconds since the epoch.
  """
  rpc = app_identity.create_rpc()
  app_identity.make_get_access_token_call(rpc, scopes, service_account_id)
  token, expires_at = yield rpc
  raise ndb.Return((token, expires_at))


class _RestApi(object):
  """Base class for REST-based API wrapper classes.

  This class manages authentication tokens and request retries.  All
  APIs are available as synchronous and async methods; synchronous
  methods are synthesized from async ones by the add_sync_methods()
  function in this module.

  WARNING: Do NOT directly use this api. It's an implementation detail
  and is subject to change at any release.
  """

  def __init__(self, scopes, service_account_id=None, token_maker=None,
               retry_params=None):
    """Constructor.

    Args:
      scopes: A scope or a list of scopes.
      token_maker: An asynchronous function of the form
        (scopes, service_account_id) -> (token, expires).
      retry_params: An instance of api_utils.RetryParams. If None, the
        default for current thread will be used.
      service_account_id: Internal use only.
    """

    if isinstance(scopes, basestring):
      scopes = [scopes]
    self.scopes = scopes
    self.service_account_id = service_account_id
    self.make_token_async = token_maker or _make_token_async
    self.token = None
    if not retry_params:
      retry_params = api_utils._get_default_retry_params()
    self.retry_params = retry_params

  def __getstate__(self):
    """Store state as part of serialization/pickling."""
    return {'token': self.token,
            'scopes': self.scopes,
            'id': self.service_account_id,
            'a_maker': None if self.make_token_async == _make_token_async
            else self.make_token_async,
            'retry_params': self.retry_params}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling."""
    self.__init__(state['scopes'],
                  service_account_id=state['id'],
                  token_maker=state['a_maker'],
                  retry_params=state['retry_params'])
    self.token = state['token']

  @ndb.tasklet
  def do_request_async(self, url, method='GET', headers=None, payload=None,
                       deadline=None, callback=None):
    """Issue one HTTP request.

    This is an async wrapper around urlfetch(). It adds an authentication
    header and retries on a 401 status code. Upon other retriable errors,
    it performs blocking retries.
    """
    headers = {} if headers is None else dict(headers)
    token = yield self.get_token_async()
    headers['authorization'] = 'OAuth ' + token

    retry = False
    resp = None
    try:
      resp = yield self.urlfetch_async(url, payload=payload, method=method,
                                       headers=headers, follow_redirects=False,
                                       deadline=deadline, callback=callback)
      if resp.status_code == httplib.UNAUTHORIZED:
        token = yield self.get_token_async(refresh=True)
        headers['authorization'] = 'OAuth ' + token
        resp = yield self.urlfetch_async(
            url, payload=payload, method=method, headers=headers,
            follow_redirects=False, deadline=deadline, callback=callback)
    except api_utils._RETRIABLE_EXCEPTIONS:
      retry = True
    else:
      retry = api_utils._should_retry(resp)

    if retry:
      retry_resp = api_utils._retry_fetch(
          url, retry_params=self.retry_params, payload=payload, method=method,
          headers=headers, follow_redirects=False, deadline=deadline)
      if retry_resp:
        resp = retry_resp
      elif not resp:
        raise

    raise ndb.Return((resp.status_code, resp.headers, resp.content))

  @ndb.tasklet
  def get_token_async(self, refresh=False):
    """Get an authentication token.

    The token is cached in memcache, keyed by the scopes argument.

    Args:
      refresh: If True, ignore a cached token; default False.

    Returns:
      An authentication token.
    """
    if self.token is not None and not refresh:
      raise ndb.Return(self.token)
    key = '%s,%s' % (self.service_account_id, ','.join(self.scopes))
    ts = None
    if not refresh:
      ts = yield _AE_TokenStorage_.get_by_id_async(key, use_datastore=False)
    if ts is None:
      token, expires_at = yield self.make_token_async(
          self.scopes, self.service_account_id)
      timeout = int(expires_at - time.time())
      ts = _AE_TokenStorage_(id=key, token=token)
      if timeout > 0:
        yield ts.put_async(memcache_timeout=timeout, use_datastore=False)
    self.token = ts.token
    raise ndb.Return(self.token)

  def urlfetch_async(self, url, **kwds):
    """Make an async urlfetch() call.

    This just passes the url and keyword arguments to NDB's async
    urlfetch() wrapper in the current context.

    This returns a Future despite not being decorated with @ndb.tasklet!
    """
    ctx = ndb.get_context()
    return ctx.urlfetch(url, **kwds)


_RestApi = add_sync_methods(_RestApi)

########NEW FILE########
__FILENAME__ = storage_api
# Copyright 2012 Google Inc. All Rights Reserved.

"""Python wrappers for the Google Storage RESTful API."""





__all__ = ['ReadBuffer',
           'StreamingBuffer',
          ]

import collections
import os
import urlparse

from . import errors
from . import rest_api

try:
  from google.appengine.api import urlfetch
  from google.appengine.ext import ndb
except ImportError:
  from google.appengine.api import urlfetch
  from google.appengine.ext import ndb


class _StorageApi(rest_api._RestApi):
  """A simple wrapper for the Google Storage RESTful API.

  WARNING: Do NOT directly use this api. It's an implementation detail
  and is subject to change at any release.

  All async methods have similar args and returns.

  Args:
    path: The path to the Google Storage object or bucket, e.g.
      '/mybucket/myfile' or '/mybucket'.
    **kwd: Options for urlfetch. e.g.
      headers={'content-type': 'text/plain'}, payload='blah'.

  Returns:
    A ndb Future. When fulfilled, future.get_result() should return
    a tuple of (status, headers, content) that represents a HTTP response
    of Google Cloud Storage XML API.
  """

  api_url = 'https://storage.googleapis.com'
  read_only_scope = 'https://www.googleapis.com/auth/devstorage.read_only'
  read_write_scope = 'https://www.googleapis.com/auth/devstorage.read_write'
  full_control_scope = 'https://www.googleapis.com/auth/devstorage.full_control'

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    Returns:
      A tuple (of dictionaries) with the state of this object
    """
    return (super(_StorageApi, self).__getstate__(), {'api_url': self.api_url})

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the tuple from a __getstate__ call
    """
    superstate, localstate = state
    super(_StorageApi, self).__setstate__(superstate)
    self.api_url = localstate['api_url']

  @ndb.tasklet
  def do_request_async(self, url, method='GET', headers=None, payload=None,
                       deadline=None, callback=None):
    """Inherit docs.

    This method translates urlfetch exceptions to more service specific ones.
    """
    if headers is None:
      headers = {}
    if 'x-goog-api-version' not in headers:
      headers['x-goog-api-version'] = '2'
    headers['accept-encoding'] = 'gzip, *'
    try:
      resp_tuple = yield super(_StorageApi, self).do_request_async(
          url, method=method, headers=headers, payload=payload,
          deadline=deadline, callback=callback)
    except urlfetch.DownloadError, e:
      raise errors.TimeoutError(
          'Request to Google Cloud Storage timed out.', e)

    raise ndb.Return(resp_tuple)


  def post_object_async(self, path, **kwds):
    """POST to an object."""
    return self.do_request_async(self.api_url + path, 'POST', **kwds)

  def put_object_async(self, path, **kwds):
    """PUT an object."""
    return self.do_request_async(self.api_url + path, 'PUT', **kwds)

  def get_object_async(self, path, **kwds):
    """GET an object.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'GET', **kwds)

  def delete_object_async(self, path, **kwds):
    """DELETE an object.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'DELETE', **kwds)

  def head_object_async(self, path, **kwds):
    """HEAD an object.

    Depending on request headers, HEAD returns various object properties,
    e.g. Content-Length, Last-Modified, and ETag.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'HEAD', **kwds)

  def get_bucket_async(self, path, **kwds):
    """GET a bucket."""
    return self.do_request_async(self.api_url + path, 'GET', **kwds)


_StorageApi = rest_api.add_sync_methods(_StorageApi)


class ReadBuffer(object):
  """A class for reading Google storage files.

  To achieve max prefetching benefit, always read by your buffer size.
  """

  DEFAULT_BUFFER_SIZE = 1024 * 1024
  MAX_REQUEST_SIZE = 30 * DEFAULT_BUFFER_SIZE

  def __init__(self,
               api,
               path,
               max_buffer_size=DEFAULT_BUFFER_SIZE,
               max_request_size=MAX_REQUEST_SIZE):
    """Constructor.

    Args:
      api: A StorageApi instance.
      path: Path to the object, e.g. '/mybucket/myfile'.
      max_buffer_size: Max bytes to buffer.
      max_request_size: Max bytes to request in one urlfetch.
    """
    self._api = api
    self._path = path
    self._max_buffer_size = max_buffer_size
    self._max_request_size = max_request_size
    self._offset = 0
    self._reset_buffer()
    self._closed = False
    self._etag = None

    self._buffer_future = self._get_segment(0, self._max_buffer_size)

    status, headers, _ = self._api.head_object(path)
    errors.check_status(status, [200])
    self._file_size = long(headers['content-length'])
    self._check_etag(headers.get('etag'))
    if self._file_size == 0:
      self._buffer_future = None

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    The contents of the read buffer are not stored, only the current offset for
    data read by the client. A new read buffer is established at unpickling.
    The head information for the object (file size and etag) are stored to
    reduce startup and ensure the file has not changed.

    Returns:
      A dictionary with the state of this object
    """
    return {'api': self._api,
            'path': self._path,
            'buffer_size': self._max_buffer_size,
            'request_size': self._max_request_size,
            'etag': self._etag,
            'size': self._file_size,
            'offset': self._offset,
            'closed': self._closed}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the dictionary from a __getstate__ call

    Along with restoring the state, pre-fetch the next read buffer.
    """
    self._api = state['api']
    self._path = state['path']
    self._max_buffer_size = state['buffer_size']
    self._max_request_size = state['request_size']
    self._etag = state['etag']
    self._file_size = state['size']
    self._offset = state['offset']
    self._reset_buffer()
    self._closed = state['closed']
    if self._offset < self._file_size and not self._closed:
      self._buffer_future = self._get_segment(self._offset,
                                              self._max_buffer_size)
    else:
      self._buffer_future = None

  def readline(self, size=-1):
    """Read one line delimited by '\n' from the file.

    A trailing newline character is kept in the string. It may be absent when a
    file ends with an incomplete line. If the size argument is non-negative,
    it specifies the maximum string size (counting the newline) to return.
    A negative size is the same as unspecified. Empty string is returned
    only when EOF is encountered immediately.

    Args:
      size: Maximum number of bytes to read. If not specified, readline stops
        only on '\n' or EOF.

    Returns:
      The data read as a string.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    self._buffer_future = None

    data_list = []

    if size == 0:
      return ''

    while True:
      if size >= 0:
        end_offset = self._buffer_offset + size
      else:
        end_offset = len(self._buffer)
      newline_offset = self._buffer.find('\n', self._buffer_offset, end_offset)

      if newline_offset >= 0:
        data_list.append(
            self._read_buffer(newline_offset + 1 - self._buffer_offset))
        return ''.join(data_list)
      else:
        result = self._read_buffer(size)
        data_list.append(result)
        size -= len(result)
        if size == 0 or self._file_size == self._offset:
          return ''.join(data_list)
        self._fill_buffer()

  def read(self, size=-1):
    """Read data from RAW file.

    Args:
      size: Number of bytes to read as integer. Actual number of bytes
        read is always equal to size unless EOF is reached. If size is
        negative or unspecified, read the entire file.

    Returns:
      data read as str.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    if self._file_size == 0:
      return ''

    if size >= 0 and size <= len(self._buffer) - self._buffer_offset:
      result = self._read_buffer(size)
    else:
      size -= len(self._buffer) - self._buffer_offset
      data_list = [self._read_buffer()]

      if self._buffer_future:
        self._reset_buffer(self._buffer_future.get_result())
        self._buffer_future = None

      if size >= 0 and size <= len(self._buffer) - self._buffer_offset:
        data_list.append(self._read_buffer(size))
      else:
        size -= len(self._buffer)
        data_list.append(self._read_buffer())
        if self._offset == self._file_size:
          return ''.join(data_list)

        if size < 0 or size >= self._file_size - self._offset:
          needs = self._file_size - self._offset
        else:
          needs = size
        data_list.extend(self._get_segments(self._offset, needs))
        self._offset += needs
      result = ''.join(data_list)
      data_list = None

    assert self._buffer_future is None
    if self._offset != self._file_size and not self._buffer:
      self._buffer_future = self._get_segment(self._offset,
                                              self._max_buffer_size)
    return result

  def _read_buffer(self, size=-1):
    """Returns bytes from self._buffer and update related offsets.

    Args:
      size: number of bytes to read. Read the entire buffer if negative.

    Returns:
      Requested bytes from buffer.
    """
    if size < 0:
      size = len(self._buffer) - self._buffer_offset
    result = self._buffer[self._buffer_offset : self._buffer_offset+size]
    self._offset += len(result)
    self._buffer_offset += len(result)
    if self._buffer_offset == len(self._buffer):
      self._reset_buffer()
    return result

  def _fill_buffer(self):
    """Fill self._buffer."""
    segments = self._get_segments(self._offset,
                                  min(self._max_buffer_size,
                                      self._max_request_size,
                                      self._file_size-self._offset))

    self._reset_buffer(''.join(segments))

  def _get_segments(self, start, request_size):
    """Get segments of the file from Google Storage as a list.

    A large request is broken into segments to avoid hitting urlfetch
    response size limit. Each segment is returned from a separate urlfetch.

    Args:
      start: start offset to request. Inclusive. Have to be within the
        range of the file.
      request_size: number of bytes to request. Can not exceed the logical
        range of the file.

    Returns:
      A list of file segments in order
    """
    end = start + request_size
    futures = []

    while request_size > self._max_request_size:
      futures.append(self._get_segment(start, self._max_request_size))
      request_size -= self._max_request_size
      start += self._max_request_size
    if start < end:
      futures.append(self._get_segment(start, end-start))
    return [fut.get_result() for fut in futures]

  @ndb.tasklet
  def _get_segment(self, start, request_size):
    """Get a segment of the file from Google Storage.

    Args:
      start: start offset of the segment. Inclusive. Have to be within the
        range of the file.
      request_size: number of bytes to request. Have to be within the range
        of the file.

    Yields:
      a segment [start, start + request_size) of the file.

    Raises:
      ValueError: if the file has changed while reading.
    """
    end = start + request_size - 1
    content_range = '%d-%d' % (start, end)
    headers = {'Range': 'bytes=' + content_range}
    status, headers, content = yield self._api.get_object_async(self._path,
                                                                headers=headers)
    errors.check_status(status, [200, 206], headers)
    self._check_etag(headers.get('etag'))
    raise ndb.Return(content)

  def _check_etag(self, etag):
    """Check if etag is the same across requests to GCS.

    If self._etag is None, set it. If etag is set, check that the new
    etag equals the old one.

    In the __init__ method, we fire one HEAD and one GET request using
    ndb tasklet. One of them would return first and set the first value.

    Args:
      etag: etag from a GCS HTTP response. None if etag is not part of the
        response header. It could be None for example in the case of GCS
        composite file.

    Raises:
      ValueError: if two etags are not equal.
    """
    if etag is None:
      return
    elif self._etag is None:
      self._etag = etag
    elif self._etag != etag:
      raise ValueError('File on GCS has changed while reading.')

  def close(self):
    self._closed = True
    self._reset_buffer()
    self._buffer_future = None

  def __enter__(self):
    return self

  def __exit__(self, atype, value, traceback):
    self.close()
    return False

  def seek(self, offset, whence=os.SEEK_SET):
    """Set the file's current offset.

    Note if the new offset is out of bound, it is adjusted to either 0 or EOF.

    Args:
      offset: seek offset as number.
      whence: seek mode. Supported modes are os.SEEK_SET (absolute seek),
        os.SEEK_CUR (seek relative to the current position), and os.SEEK_END
        (seek relative to the end, offset should be negative).

    Raises:
      IOError: When this buffer is closed.
      ValueError: When whence is invalid.
    """
    self._check_open()

    self._reset_buffer()
    self._buffer_future = None

    if whence == os.SEEK_SET:
      self._offset = offset
    elif whence == os.SEEK_CUR:
      self._offset += offset
    elif whence == os.SEEK_END:
      self._offset = self._file_size + offset
    else:
      raise ValueError('Whence mode %s is invalid.' % str(whence))

    self._offset = min(self._offset, self._file_size)
    self._offset = max(self._offset, 0)
    if self._offset != self._file_size:
      self._buffer_future = self._get_segment(self._offset,
                                              self._max_buffer_size)

  def tell(self):
    """Tell the file's current offset.

    Returns:
      current offset in reading this file.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    return self._offset

  def _check_open(self):
    if self._closed:
      raise IOError('Buffer is closed.')

  def _reset_buffer(self, new_buffer='', buffer_offset=0):
    self._buffer = new_buffer
    self._buffer_offset = buffer_offset


class StreamingBuffer(object):
  """A class for creating large objects using the 'resumable' API.

  The API is a subset of the Python writable stream API sufficient to
  support writing zip files using the zipfile module.

  The exact sequence of calls and use of headers is documented at
  https://developers.google.com/storage/docs/developer-guide#unknownresumables
  """

  _blocksize = 256 * 1024

  _maxrequestsize = 16 * _blocksize

  def __init__(self,
               api,
               path,
               content_type=None,
               gcs_headers=None):
    """Constructor.

    Args:
      api: A StorageApi instance.
      path: Path to the object, e.g. '/mybucket/myfile'.
      content_type: Optional content-type; Default value is
        delegate to Google Cloud Storage.
      gcs_headers: additional gs headers as a str->str dict, e.g
        {'x-goog-acl': 'private', 'x-goog-meta-foo': 'foo'}.
    """
    assert self._maxrequestsize > self._blocksize
    assert self._maxrequestsize % self._blocksize == 0

    self._api = api
    self._path = path

    self._buffer = collections.deque()
    self._buffered = 0
    self._written = 0
    self._offset = 0

    self._closed = False

    headers = {'x-goog-resumable': 'start'}
    if content_type:
      headers['content-type'] = content_type
    if gcs_headers:
      headers.update(gcs_headers)
    status, headers, _ = self._api.post_object(path, headers=headers)
    errors.check_status(status, [201], headers)
    loc = headers.get('location')
    if not loc:
      raise IOError('No location header found in 201 response')
    parsed = urlparse.urlparse(loc)
    self._path_with_token = '%s?%s' % (self._path, parsed.query)

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    The contents of the write buffer are stored. Writes to the underlying
    storage are required to be on block boundaries (_blocksize) except for the
    last write. In the worst case the pickled version of this object may be
    slightly larger than the blocksize.

    Returns:
      A dictionary with the state of this object

    """
    return {'api': self._api,
            'path_token': self._path_with_token,
            'buffer': self._buffer,
            'buffered': self._buffered,
            'written': self._written,
            'offset': self._offset,
            'closed': self._closed}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the dictionary from a __getstate__ call
    """
    self._api = state['api']
    self._path_with_token = state['path_token']
    self._buffer = state['buffer']
    self._buffered = state['buffered']
    self._written = state['written']
    self._offset = state['offset']
    self._closed = state['closed']

  def write(self, data):
    """Write some bytes."""
    self._check_open()
    assert isinstance(data, str)
    if not data:
      return
    self._buffer.append(data)
    self._buffered += len(data)
    self._offset += len(data)
    if self._buffered >= self._blocksize:
      self._flush()

  def flush(self):
    """Dummy API.

    This API is provided because the zipfile module uses it.  It is a
    no-op because Google Storage *requires* that all writes except for
    the final one are multiples on 256K bytes aligned on 256K-byte
    boundaries.
    """
    self._check_open()

  def tell(self):
    """Return the total number of bytes passed to write() so far.

    (There is no seek() method.)
    """
    self._check_open()
    return self._offset

  def close(self):
    """Flush the buffer and finalize the file.

    When this returns the new file is available for reading.
    """
    if not self._closed:
      self._closed = True
      self._flush(finish=True)
      self._buffer = None

  def __enter__(self):
    return self

  def __exit__(self, atype, value, traceback):
    self.close()
    return False

  def _flush(self, finish=False):
    """Internal API to flush.

    This is called only when the total amount of buffered data is at
    least self._blocksize, or to flush the final (incomplete) block of
    the file with finish=True.
    """
    flush_len = 0 if finish else self._blocksize
    last = False

    while self._buffered >= flush_len:
      buffer = []
      buffered = 0

      while self._buffer:
        buf = self._buffer.popleft()
        size = len(buf)
        self._buffered -= size
        buffer.append(buf)
        buffered += size
        if buffered >= self._maxrequestsize:
          break

      if buffered > self._maxrequestsize:
        excess = buffered - self._maxrequestsize
      elif finish:
        excess = 0
      else:
        excess = buffered % self._blocksize

      if excess:
        over = buffer.pop()
        size = len(over)
        assert size >= excess
        buffered -= size
        head, tail = over[:-excess], over[-excess:]
        self._buffer.appendleft(tail)
        self._buffered += len(tail)
        if head:
          buffer.append(head)
          buffered += len(head)

      if finish:
        last = not self._buffered
      self._send_data(''.join(buffer), last)
      if last:
        break

  def _send_data(self, data, last):
    """Send the block to the storage service and update self._written."""
    headers = {}
    length = self._written + len(data)

    if data:
      headers['content-range'] = ('bytes %d-%d/%s' %
                                  (self._written, length-1,
                                   length if last else '*'))
    else:
      headers['content-range'] = ('bytes */%s' %
                                  length if last else '*')
    status, _, _ = self._api.put_object(
        self._path_with_token, payload=data, headers=headers)
    if last:
      expected = 200
    else:
      expected = 308
    errors.check_status(status, [expected], headers)
    self._written += len(data)

  def _check_open(self):
    if self._closed:
      raise IOError('Buffer is closed.')

########NEW FILE########
__FILENAME__ = test_utils
# Copyright 2013 Google Inc. All Rights Reserved.

"""Utils for testing."""


class MockUrlFetchResult(object):

  def __init__(self, status, headers, body):
    self.status_code = status
    self.headers = headers
    self.content = body
    self.content_was_truncated = False
    self.final_url = None

########NEW FILE########
__FILENAME__ = main
# Copyright 2012 Google Inc. All Rights Reserved.


"""A sample app that uses GCS client to operate on bucket and file."""

import os
import cloudstorage as gcs
import webapp2

my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)
gcs.set_default_retry_params(my_default_retry_params)

BUCKET = '/yey-cloud-storage-trial'


class MainPage(webapp2.RequestHandler):

  def get(self):
    filename = BUCKET + '/demo-testfile'

    self.response.headers['Content-Type'] = 'text/plain'
    self.tmp_filenames_to_clean_up = []

    self.create_file(filename)
    self.response.write('\n\n')

    self.read_file(filename)
    self.response.write('\n\n')

    self.stat_file(filename)
    self.response.write('\n\n')

    self.list_bucket(BUCKET)
    self.response.write('\n\n')

    self.delete_files()

  def create_file(self, filename):
    """Create a file.

    The retry_params specified in the open call will override the default
    retry params for this particular file handle.

    Args:
      filename: filename.
    """
    self.response.write('Creating file %s\n' % filename)

    write_retry_params = gcs.RetryParams(backoff_factor=1.1)
    gcs_file = gcs.open(filename,
                        'w',
                        content_type='text/plain',
                        options={'x-goog-meta-foo': 'foo',
                                 'x-goog-meta-bar': 'bar'},
                        retry_params=write_retry_params)
    gcs_file.write('abcde\n')
    gcs_file.write('f'*1024*1024 + '\n')
    gcs_file.close()
    self.tmp_filenames_to_clean_up.append(filename)

  def read_file(self, filename):
    self.response.write('Truncated file content:\n')

    gcs_file = gcs.open(filename)
    self.response.write(gcs_file.readline())
    gcs_file.seek(-1024, os.SEEK_END)
    self.response.write(gcs_file.read())
    gcs_file.close()

  def stat_file(self, filename):
    self.response.write('File stat:\n')

    stat = gcs.stat(filename)
    self.response.write(repr(stat))

  def list_bucket(self, bucket):
    """Create several files and paginate through them.

    Production apps should set page_size to a practical value.

    Args:
      bucket: bucket.
    """
    self.response.write('Creating more files for listbucket...\n')
    self.create_file(bucket + '/foo1')
    self.create_file(bucket + '/foo2')
    self.response.write('\nListbucket result:\n')

    page_size = 1
    stats = gcs.listbucket(bucket, max_keys=page_size)
    while True:
      count = 0
      for stat in stats:
        count += 1
        self.response.write(repr(stat))
        self.response.write('\n')

      if count != page_size or count == 0:
        break
      last_filename = stat.filename[len(bucket)+1:]
      stats = gcs.listbucket(bucket, max_keys=page_size, marker=last_filename)

  def delete_files(self):
    self.response.write('Deleting files...\n')
    for filename in self.tmp_filenames_to_clean_up:
      try:
        gcs.delete(filename)
      except gcs.NotFoundError:
        pass


app = webapp2.WSGIApplication([('/', MainPage)],
                              debug=True)

########NEW FILE########
__FILENAME__ = api_utils
# Copyright 2013 Google Inc. All Rights Reserved.

"""Util functions and classes for cloudstorage_api."""



__all__ = ['set_default_retry_params',
           'RetryParams',
          ]

import copy
import httplib
import logging
import math
import os
import threading
import time


try:
  from google.appengine.api import urlfetch
  from google.appengine.datastore import datastore_rpc
  from google.appengine import runtime
  from google.appengine.runtime import apiproxy_errors
except ImportError:
  from google.appengine.api import urlfetch
  from google.appengine.datastore import datastore_rpc
  from google.appengine import runtime
  from google.appengine.runtime import apiproxy_errors


_RETRIABLE_EXCEPTIONS = (urlfetch.DownloadError,
                         apiproxy_errors.Error)

_thread_local_settings = threading.local()
_thread_local_settings.default_retry_params = None


def set_default_retry_params(retry_params):
  """Set a default RetryParams for current thread current request."""
  _thread_local_settings.default_retry_params = copy.copy(retry_params)


def _get_default_retry_params():
  """Get default RetryParams for current request and current thread.

  Returns:
    A new instance of the default RetryParams.
  """
  default = getattr(_thread_local_settings, 'default_retry_params', None)
  if default is None or not default.belong_to_current_request():
    return RetryParams()
  else:
    return copy.copy(default)


def _should_retry(resp):
  """Given a urlfetch response, decide whether to retry that request."""
  return (resp.status_code == httplib.REQUEST_TIMEOUT or
          (resp.status_code >= 500 and
           resp.status_code < 600))


class RetryParams(object):
  """Retry configuration parameters."""

  @datastore_rpc._positional(1)
  def __init__(self,
               backoff_factor=2.0,
               initial_delay=0.1,
               max_delay=10.0,
               min_retries=2,
               max_retries=5,
               max_retry_period=30.0,
               urlfetch_timeout=None):
    """Init.

    This object is unique per request per thread.

    Library will retry according to this setting when App Engine Server
    can't call urlfetch, urlfetch timed out, or urlfetch got a 408 or
    500-600 response.

    Args:
      backoff_factor: exponential backoff multiplier.
      initial_delay: seconds to delay for the first retry.
      max_delay: max seconds to delay for every retry.
      min_retries: min number of times to retry. This value is automatically
        capped by max_retries.
      max_retries: max number of times to retry. Set this to 0 for no retry.
      max_retry_period: max total seconds spent on retry. Retry stops when
       this period passed AND min_retries has been attempted.
      urlfetch_timeout: timeout for urlfetch in seconds. Could be None.
    """
    self.backoff_factor = self._check('backoff_factor', backoff_factor)
    self.initial_delay = self._check('initial_delay', initial_delay)
    self.max_delay = self._check('max_delay', max_delay)
    self.max_retry_period = self._check('max_retry_period', max_retry_period)
    self.max_retries = self._check('max_retries', max_retries, True, int)
    self.min_retries = self._check('min_retries', min_retries, True, int)
    if self.min_retries > self.max_retries:
      self.min_retries = self.max_retries

    self.urlfetch_timeout = None
    if urlfetch_timeout is not None:
      self.urlfetch_timeout = self._check('urlfetch_timeout', urlfetch_timeout)

    self._request_id = os.getenv('REQUEST_LOG_ID')

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return False
    return self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not self.__eq__(other)

  @classmethod
  def _check(cls, name, val, can_be_zero=False, val_type=float):
    """Check init arguments.

    Args:
      name: name of the argument. For logging purpose.
      val: value. Value has to be non negative number.
      can_be_zero: whether value can be zero.
      val_type: Python type of the value.

    Returns:
      The value.

    Raises:
      ValueError: when invalid value is passed in.
      TypeError: when invalid value type is passed in.
    """
    valid_types = [val_type]
    if val_type is float:
      valid_types.append(int)

    if type(val) not in valid_types:
      raise TypeError(
          'Expect type %s for parameter %s' % (val_type.__name__, name))
    if val < 0:
      raise ValueError(
          'Value for parameter %s has to be greater than 0' % name)
    if not can_be_zero and val == 0:
      raise ValueError(
          'Value for parameter %s can not be 0' % name)
    return val

  def belong_to_current_request(self):
    return os.getenv('REQUEST_LOG_ID') == self._request_id

  def delay(self, n, start_time):
    """Calculate delay before the next retry.

    Args:
      n: the number of current attempt. The first attempt should be 1.
      start_time: the time when retry started in unix time.

    Returns:
      Number of seconds to wait before next retry. -1 if retry should give up.
    """
    if (n > self.max_retries or
        (n > self.min_retries and
         time.time() - start_time > self.max_retry_period)):
      return -1
    return min(
        math.pow(self.backoff_factor, n-1) * self.initial_delay,
        self.max_delay)


def _retry_fetch(url, retry_params, **kwds):
  """A blocking fetch function similar to urlfetch.fetch.

  This function should be used when a urlfetch has timed out or the response
  shows http request timeout. This function will put current thread to
  sleep between retry backoffs.

  Args:
    url: url to fetch.
    retry_params: an instance of RetryParams.
    **kwds: keyword arguments for urlfetch. If deadline is specified in kwds,
      it precedes the one in RetryParams. If none is specified, it's up to
      urlfetch to use its own default.

  Returns:
    A urlfetch response from the last retry. None if no retry was attempted.

  Raises:
    Whatever exception encountered during the last retry.
  """
  n = 1
  start_time = time.time()
  delay = retry_params.delay(n, start_time)
  if delay <= 0:
    return

  deadline = kwds.get('deadline', None)
  if deadline is None:
    kwds['deadline'] = retry_params.urlfetch_timeout

  while delay > 0:
    resp = None
    try:
      time.sleep(delay)
      resp = urlfetch.fetch(url, **kwds)
    except runtime.DeadlineExceededError:
      logging.info(
          'Urlfetch retry %s will exceed request deadline '
          'after %s seconds total', n, time.time() - start_time)
      raise
    except _RETRIABLE_EXCEPTIONS, e:
      pass

    n += 1
    delay = retry_params.delay(n, start_time)
    if resp and not _should_retry(resp):
      break
    elif resp:
      logging.info(
          'Got status %s from GCS. Will retry in %s seconds.',
          resp.status_code, delay)
    else:
      logging.info(
          'Got exception while contacting GCS. Will retry in %s seconds.',
          delay)
      logging.info(e)
    logging.debug('Tried to reach url %s', url)

  if resp:
    return resp

  logging.info('Urlfetch retry %s failed after %s seconds total',
               n - 1, time.time() - start_time)
  raise


########NEW FILE########
__FILENAME__ = cloudstorage_api
# Copyright 2012 Google Inc. All Rights Reserved.

"""File Interface for Google Cloud Storage."""



from __future__ import with_statement



__all__ = ['delete',
           'listbucket',
           'open',
           'stat',
          ]

import urllib
import xml.etree.ElementTree as ET
from . import common
from . import errors
from . import storage_api


def open(filename,
         mode='r',
         content_type=None,
         options=None,
         read_buffer_size=storage_api.ReadBuffer.DEFAULT_BUFFER_SIZE,
         retry_params=None,
         _account_id=None):
  """Opens a Google Cloud Storage file and returns it as a File-like object.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    mode: 'r' for reading mode. 'w' for writing mode.
      In reading mode, the file must exist. In writing mode, a file will
      be created or be overrode.
    content_type: The MIME type of the file. str. Only valid in writing mode.
    options: A str->basestring dict to specify additional headers to pass to
      GCS e.g. {'x-goog-acl': 'private', 'x-goog-meta-foo': 'foo'}.
      Supported options are x-goog-acl, x-goog-meta-, cache-control,
      content-disposition, and content-encoding.
      Only valid in writing mode.
      See https://developers.google.com/storage/docs/reference-headers
      for details.
    read_buffer_size: The buffer size for read. If buffer is empty, the read
      stream will asynchronously prefetch a new buffer before the next read().
      To minimize blocking for large files, always read in buffer size.
      To minimize number of requests for small files, set a larger
      buffer size.
    retry_params: An instance of api_utils.RetryParams for subsequent calls
      to GCS from this file handle. If None, the default one is used.
    _account_id: Internal-use only.

  Returns:
    A reading or writing buffer that supports File-like interface. Buffer
    must be closed after operations are done.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
    ValueError: invalid open mode or if content_type or options are specified
      in reading mode.
  """
  common.validate_file_path(filename)
  api = _get_storage_api(retry_params=retry_params, account_id=_account_id)

  if mode == 'w':
    common.validate_options(options)
    return storage_api.StreamingBuffer(api, filename, content_type, options)
  elif mode == 'r':
    if content_type or options:
      raise ValueError('Options and content_type can only be specified '
                       'for writing mode.')
    return storage_api.ReadBuffer(api,
                                  filename,
                                  max_buffer_size=read_buffer_size)
  else:
    raise ValueError('Invalid mode %s.' % mode)


def delete(filename, retry_params=None, _account_id=None):
  """Delete a Google Cloud Storage file.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Raises:
    errors.NotFoundError: if the file doesn't exist prior to deletion.
  """
  api = _get_storage_api(retry_params=retry_params, account_id=_account_id)
  common.validate_file_path(filename)
  status, _, _ = api.delete_object(filename)
  errors.check_status(status, [204])


def stat(filename, retry_params=None, _account_id=None):
  """Get GCSFileStat of a Google Cloud storage file.

  Args:
    filename: A Google Cloud Storage filename of form '/bucket/filename'.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Returns:
    a GCSFileStat object containing info about this file.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
  """
  common.validate_file_path(filename)
  api = _get_storage_api(retry_params=retry_params, account_id=_account_id)
  status, headers, _ = api.head_object(filename)
  errors.check_status(status, [200])
  file_stat = common.GCSFileStat(
      filename=filename,
      st_size=headers.get('content-length'),
      st_ctime=common.http_time_to_posix(headers.get('last-modified')),
      etag=headers.get('etag'),
      content_type=headers.get('content-type'),
      metadata=common.get_metadata(headers))

  return file_stat


def _copy2(src, dst, retry_params=None):
  """Copy the file content and metadata from src to dst.

  Internal use only!

  Args:
    src: /bucket/filename
    dst: /bucket/filename
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.

  Raises:
    errors.AuthorizationError: if authorization failed.
    errors.NotFoundError: if an object that's expected to exist doesn't.
  """
  common.validate_file_path(src)
  common.validate_file_path(dst)
  if src == dst:
    return

  api = _get_storage_api(retry_params=retry_params)
  status, headers, _ = api.put_object(
      dst,
      headers={'x-goog-copy-source': src,
               'Content-Length': '0'})
  errors.check_status(status, [200], headers)


def listbucket(bucket, marker=None, prefix=None, max_keys=None,
               retry_params=None, _account_id=None):
  """Return an GCSFileStat iterator over files in the given bucket.

  Optional arguments are to limit the result to a subset of files under bucket.

  This function is asynchronous. It does not block unless iterator is called
  before the iterator gets result.

  Args:
    bucket: A Google Cloud Storage bucket of form "/bucket".
    marker: A string after which (exclusive) to start listing.
    prefix: Limits the returned filenames to those with this prefix. no regex.
    max_keys: The maximum number of filenames to match. int.
    retry_params: An api_utils.RetryParams for this call to GCS. If None,
      the default one is used.
    _account_id: Internal-use only.

  Example:
    For files "/bucket/foo1", "/bucket/foo2", "/bucket/foo3", "/bucket/www",
    listbucket("/bucket", prefix="foo", marker="foo1")
    will match "/bucket/foo2" and "/bucket/foo3".

    See Google Cloud Storage documentation for more details and examples.
    https://developers.google.com/storage/docs/reference-methods#getbucket

  Returns:
    An GSFileStat iterator over matched files, sorted by filename.
    Only filename, etag, and st_size are set in these GSFileStat objects.
  """
  common.validate_bucket_path(bucket)
  api = _get_storage_api(retry_params=retry_params, account_id=_account_id)
  options = {}
  if marker:
    options['marker'] = marker
  if max_keys:
    options['max-keys'] = max_keys
  if prefix:
    options['prefix'] = prefix

  return _Bucket(api, bucket, options)


class _Bucket(object):
  """A wrapper for a GCS bucket as the return value of listbucket."""

  def __init__(self, api, path, options):
    """Initialize.

    Args:
      api: storage_api instance.
      path: bucket path of form '/bucket'.
      options: a dict of listbucket options. Please see listbucket doc.
    """
    self._api = api
    self._path = path
    self._options = options.copy()
    self._get_bucket_fut = self._api.get_bucket_async(
        self._path + '?' + urllib.urlencode(self._options))

  def _add_ns(self, tagname):
    return '{%(ns)s}%(tag)s' % {'ns': common.CS_XML_NS,
                                'tag': tagname}

  def __iter__(self):
    """Iter over the bucket.

    Yields:
      GCSFileStat: a GCSFileStat for an object in the bucket.
        They are ordered by GCSFileStat.filename.
    """
    total = 0
    while self._get_bucket_fut:
      status, _, content = self._get_bucket_fut.get_result()
      errors.check_status(status, [200])
      root = ET.fromstring(content)
      for contents in root.getiterator(self._add_ns('Contents')):
        last_modified = contents.find(self._add_ns('LastModified')).text
        st_ctime = common.dt_str_to_posix(last_modified)
        yield common.GCSFileStat(
            self._path + '/' + contents.find(self._add_ns('Key')).text,
            contents.find(self._add_ns('Size')).text,
            contents.find(self._add_ns('ETag')).text,
            st_ctime)
        total += 1

      max_keys = root.find(self._add_ns('MaxKeys'))
      next_marker = root.find(self._add_ns('NextMarker'))
      if (max_keys is None or total < int(max_keys.text)) and (
          next_marker is not None):
        self._options['marker'] = next_marker.text
        self._get_bucket_fut = self._api.get_bucket_async(
            self._path + '?' + urllib.urlencode(self._options))
      else:
        self._get_bucket_fut = None


def _get_storage_api(retry_params, account_id=None):
  """Returns storage_api instance for API methods.

  Args:
    retry_params: An instance of api_utils.RetryParams.
    account_id: Internal-use only.

  Returns:
    A storage_api instance to handle urlfetch work to GCS.
    On dev appserver, this instance by default will talk to a local stub
    unless common.ACCESS_TOKEN is set. That token will be used to talk
    to the real GCS.
  """


  api = storage_api._StorageApi(storage_api._StorageApi.full_control_scope,
                                service_account_id=account_id,
                                retry_params=retry_params)
  if common.local_run() and not common.get_access_token():
    api.api_url = 'http://' + common.LOCAL_API_HOST
  if common.get_access_token():
    api.token = common.get_access_token()
  return api

########NEW FILE########
__FILENAME__ = common
# Copyright 2012 Google Inc. All Rights Reserved.

"""Helpers shared by cloudstorage_stub and cloudstorage_api."""





__all__ = ['CS_XML_NS',
           'CSFileStat',
           'dt_str_to_posix',
           'LOCAL_API_HOST',
           'local_run',
           'get_access_token',
           'get_metadata',
           'GCSFileStat',
           'http_time_to_posix',
           'memory_usage',
           'posix_time_to_http',
           'posix_to_dt_str',
           'set_access_token',
           'validate_options',
           'validate_bucket_name',
           'validate_bucket_path',
           'validate_file_path',
          ]


import calendar
import datetime
from email import utils as email_utils
import logging
import os
import re

try:
  from google.appengine.api import runtime
except ImportError:
  from google.appengine.api import runtime


_GCS_BUCKET_REGEX_BASE = r'[a-z0-9\.\-_]{3,63}'
_GCS_BUCKET_REGEX = re.compile(_GCS_BUCKET_REGEX_BASE + r'$')
_GCS_BUCKET_PATH_REGEX = re.compile(r'/' + _GCS_BUCKET_REGEX_BASE + r'$')
_GCS_FULLPATH_REGEX = re.compile(r'/' + _GCS_BUCKET_REGEX_BASE + r'/.*')
_GCS_METADATA = ['x-goog-meta-',
                 'content-disposition',
                 'cache-control',
                 'content-encoding']
_GCS_OPTIONS = _GCS_METADATA + ['x-goog-acl']
CS_XML_NS = 'http://doc.s3.amazonaws.com/2006-03-01'
LOCAL_API_HOST = 'gcs-magicstring.appspot.com'
_access_token = ''


def set_access_token(access_token):
  """Set the shared access token to authenticate with Google Cloud Storage.

  When set, the library will always attempt to communicate with the
  real Google Cloud Storage with this token even when running on dev appserver.
  Note the token could expire so it's up to you to renew it.

  When absent, the library will automatically request and refresh a token
  on appserver, or when on dev appserver, talk to a Google Cloud Storage
  stub.

  Args:
    access_token: you can get one by run 'gsutil -d ls' and copy the
      str after 'Bearer'.
  """
  global _access_token
  _access_token = access_token


def get_access_token():
  """Returns the shared access token."""
  return _access_token


class GCSFileStat(object):
  """Container for GCS file stat."""

  def __init__(self,
               filename,
               st_size,
               etag,
               st_ctime,
               content_type=None,
               metadata=None):
    """Initialize.

    Args:
      filename: a Google Cloud Storage filename of form '/bucket/filename'.
      st_size: file size in bytes. long compatible.
      etag: hex digest of the md5 hash of the file's content. str.
      st_ctime: posix file creation time. float compatible.
      content_type: content type. str.
      metadata: a str->str dict of user specified options when creating
        the file. Possible keys are x-goog-meta-, content-disposition,
        content-encoding, and cache-control.
    """
    self.filename = filename
    self.st_size = long(st_size)
    self.st_ctime = float(st_ctime)
    if etag[0] == '"' and etag[-1] == '"':
      etag = etag[1:-1]
    self.etag = etag
    self.content_type = content_type
    self.metadata = metadata

  def __repr__(self):
    return (
        '(filename: %(filename)s, st_size: %(st_size)s, '
        'st_ctime: %(st_ctime)s, etag: %(etag)s, '
        'content_type: %(content_type)s, '
        'metadata: %(metadata)s)' %
        dict(filename=self.filename,
             st_size=self.st_size,
             st_ctime=self.st_ctime,
             etag=self.etag,
             content_type=self.content_type,
             metadata=self.metadata))


CSFileStat = GCSFileStat


def get_metadata(headers):
  """Get user defined options from HTTP response headers."""
  return dict((k, v) for k, v in headers.iteritems()
              if any(k.lower().startswith(valid) for valid in _GCS_METADATA))


def validate_bucket_name(name):
  """Validate a Google Storage bucket name.

  Args:
    name: a Google Storage bucket name with no prefix or suffix.

  Raises:
    ValueError: if name is invalid.
  """
  _validate_path(name)
  if not _GCS_BUCKET_REGEX.match(name):
    raise ValueError('Bucket should be 3-63 characters long using only a-z,'
                     '0-9, underscore, dash or dot but got %s' % name)


def validate_bucket_path(path):
  """Validate a Google Cloud Storage bucket path.

  Args:
    path: a Google Storage bucket path. It should have form '/bucket'.

  Raises:
    ValueError: if path is invalid.
  """
  _validate_path(path)
  if not _GCS_BUCKET_PATH_REGEX.match(path):
    raise ValueError('Bucket should have format /bucket '
                     'but got %s' % path)


def validate_file_path(path):
  """Validate a Google Cloud Storage file path.

  Args:
    path: a Google Storage file path. It should have form '/bucket/filename'.

  Raises:
    ValueError: if path is invalid.
  """
  _validate_path(path)
  if not _GCS_FULLPATH_REGEX.match(path):
    raise ValueError('Path should have format /bucket/filename '
                     'but got %s' % path)


def _validate_path(path):
  """Basic validation of Google Storage paths.

  Args:
    path: a Google Storage path. It should have form '/bucket/filename'
      or '/bucket'.

  Raises:
    ValueError: if path is invalid.
    TypeError: if path is not of type basestring.
  """
  if not path:
    raise ValueError('Path is empty')
  if not isinstance(path, basestring):
    raise TypeError('Path should be a string but is %s (%s).' %
                    (path.__class__, path))


def validate_options(options):
  """Validate Google Cloud Storage options.

  Args:
    options: a str->basestring dict of options to pass to Google Cloud Storage.

  Raises:
    ValueError: if option is not supported.
    TypeError: if option is not of type str or value of an option
      is not of type basestring.
  """
  if not options:
    return

  for k, v in options.iteritems():
    if not isinstance(k, str):
      raise TypeError('option %r should be a str.' % k)
    if not any(k.lower().startswith(valid) for valid in _GCS_OPTIONS):
      raise ValueError('option %s is not supported.' % k)
    if not isinstance(v, basestring):
      raise TypeError('value %r for option %s should be of type basestring.' %
                      v, k)


def http_time_to_posix(http_time):
  """Convert HTTP time format to posix time.

  See http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.3.1
  for http time format.

  Args:
    http_time: time in RFC 2616 format. e.g.
      "Mon, 20 Nov 1995 19:12:08 GMT".

  Returns:
    A float of secs from unix epoch.
  """
  if http_time is not None:
    return email_utils.mktime_tz(email_utils.parsedate_tz(http_time))


def posix_time_to_http(posix_time):
  """Convert posix time to HTML header time format.

  Args:
    posix_time: unix time.

  Returns:
    A datatime str in RFC 2616 format.
  """
  if posix_time:
    return email_utils.formatdate(posix_time, usegmt=True)


_DT_FORMAT = '%Y-%m-%dT%H:%M:%S'


def dt_str_to_posix(dt_str):
  """format str to posix.

  datetime str is of format %Y-%m-%dT%H:%M:%S.%fZ,
  e.g. 2013-04-12T00:22:27.978Z. According to ISO 8601, T is a separator
  between date and time when they are on the same line.
  Z indicates UTC (zero meridian).

  A pointer: http://www.cl.cam.ac.uk/~mgk25/iso-time.html

  This is used to parse LastModified node from GCS's GET bucket XML response.

  Args:
    dt_str: A datetime str.

  Returns:
    A float of secs from unix epoch. By posix definition, epoch is midnight
    1970/1/1 UTC.
  """
  parsable, _ = dt_str.split('.')
  dt = datetime.datetime.strptime(parsable, _DT_FORMAT)
  return calendar.timegm(dt.utctimetuple())


def posix_to_dt_str(posix):
  """Reverse of str_to_datetime.

  This is used by GCS stub to generate GET bucket XML response.

  Args:
    posix: A float of secs from unix epoch.

  Returns:
    A datetime str.
  """
  dt = datetime.datetime.utcfromtimestamp(posix)
  dt_str = dt.strftime(_DT_FORMAT)
  return dt_str + '.000Z'


def local_run():
  """Whether running in dev appserver."""
  return ('SERVER_SOFTWARE' not in os.environ or
          os.environ['SERVER_SOFTWARE'].startswith('Development'))


def memory_usage(method):
  """Log memory usage before and after a method."""
  def wrapper(*args, **kwargs):
    logging.info('Memory before method %s is %s.',
                 method.__name__, runtime.memory_usage().current())
    result = method(*args, **kwargs)
    logging.info('Memory after method %s is %s',
                 method.__name__, runtime.memory_usage().current())
    return result
  return wrapper

########NEW FILE########
__FILENAME__ = errors
# Copyright 2012 Google Inc. All Rights Reserved.

"""Google Cloud Storage specific Files API calls."""





__all__ = ['AuthorizationError',
           'check_status',
           'Error',
           'FatalError',
           'ForbiddenError',
           'NotFoundError',
           'ServerError',
           'TimeoutError',
           'TransientError',
          ]

import httplib


class Error(Exception):
  """Base error for all gcs operations.

  Error can happen on GAE side or GCS server side.
  For details on a particular GCS HTTP response code, see
  https://developers.google.com/storage/docs/reference-status#standardcodes
  """


class TransientError(Error):
  """TransientError could be retried."""


class TimeoutError(TransientError):
  """HTTP 408 timeout."""


class FatalError(Error):
  """FatalError shouldn't be retried."""


class NotFoundError(FatalError):
  """HTTP 404 resource not found."""


class ForbiddenError(FatalError):
  """HTTP 403 Forbidden.

  While GCS replies with a 403 error for many reasons, the most common one
  is due to bucket permission not correctly setup for your app to access.
  """


class AuthorizationError(FatalError):
  """HTTP 401 authentication required.

  Unauthorized request has been received by GCS.

  This error is mostly handled by GCS client. GCS client will request
  a new access token and retry the request.
  """


class InvalidRange(FatalError):
  """HTTP 416 RequestRangeNotSatifiable."""


class ServerError(TransientError):
  """HTTP >= 500 server side error."""


def check_status(status, expected, headers=None):
  """Check HTTP response status is expected.

  Args:
    status: HTTP response status. int.
    expected: a list of expected statuses. A list of ints.
    headers: HTTP response headers.

  Raises:
    AuthorizationError: if authorization failed.
    NotFoundError: if an object that's expected to exist doesn't.
    TimeoutError: if HTTP request timed out.
    ServerError: if server experienced some errors.
    FatalError: if any other unexpected errors occurred.
  """
  if status in expected:
    return

  msg = ('Expect status %r from Google Storage. But got status %d. Response '
         'headers: %r' %
         (expected, status, headers))

  if status == httplib.UNAUTHORIZED:
    raise AuthorizationError(msg)
  elif status == httplib.FORBIDDEN:
    raise ForbiddenError(msg)
  elif status == httplib.NOT_FOUND:
    raise NotFoundError(msg)
  elif status == httplib.REQUEST_TIMEOUT:
    raise TimeoutError(msg)
  elif status == httplib.REQUESTED_RANGE_NOT_SATISFIABLE:
    raise InvalidRange(msg)
  elif status >= 500:
    raise ServerError(msg)
  else:
    raise FatalError(msg)

########NEW FILE########
__FILENAME__ = rest_api
# Copyright 2012 Google Inc. All Rights Reserved.

"""Base and helper classes for Google RESTful APIs."""





__all__ = ['add_sync_methods']

import httplib
import time

from . import api_utils

try:
  from google.appengine.api import app_identity
  from google.appengine.ext import ndb
except ImportError:
  from google.appengine.api import app_identity
  from google.appengine.ext import ndb


def _make_sync_method(name):
  """Helper to synthesize a synchronous method from an async method name.

  Used by the @add_sync_methods class decorator below.

  Args:
    name: The name of the synchronous method.

  Returns:
    A method (with first argument 'self') that retrieves and calls
    self.<name>, passing its own arguments, expects it to return a
    Future, and then waits for and returns that Future's result.
  """

  def sync_wrapper(self, *args, **kwds):
    method = getattr(self, name)
    future = method(*args, **kwds)
    return future.get_result()

  return sync_wrapper


def add_sync_methods(cls):
  """Class decorator to add synchronous methods corresponding to async methods.

  This modifies the class in place, adding additional methods to it.
  If a synchronous method of a given name already exists it is not
  replaced.

  Args:
    cls: A class.

  Returns:
    The same class, modified in place.
  """
  for name in cls.__dict__.keys():
    if name.endswith('_async'):
      sync_name = name[:-6]
      if not hasattr(cls, sync_name):
        setattr(cls, sync_name, _make_sync_method(name))
  return cls


class _AE_TokenStorage_(ndb.Model):
  """Entity to store app_identity tokens in memcache."""

  token = ndb.StringProperty()


@ndb.tasklet
def _make_token_async(scopes, service_account_id):
  """Get a fresh authentication token.

  Args:
    scopes: A list of scopes.
    service_account_id: Internal-use only.

  Returns:
    An tuple (token, expiration_time) where expiration_time is
    seconds since the epoch.
  """
  rpc = app_identity.create_rpc()
  app_identity.make_get_access_token_call(rpc, scopes, service_account_id)
  token, expires_at = yield rpc
  raise ndb.Return((token, expires_at))


class _RestApi(object):
  """Base class for REST-based API wrapper classes.

  This class manages authentication tokens and request retries.  All
  APIs are available as synchronous and async methods; synchronous
  methods are synthesized from async ones by the add_sync_methods()
  function in this module.

  WARNING: Do NOT directly use this api. It's an implementation detail
  and is subject to change at any release.
  """

  def __init__(self, scopes, service_account_id=None, token_maker=None,
               retry_params=None):
    """Constructor.

    Args:
      scopes: A scope or a list of scopes.
      token_maker: An asynchronous function of the form
        (scopes, service_account_id) -> (token, expires).
      retry_params: An instance of api_utils.RetryParams. If None, the
        default for current thread will be used.
      service_account_id: Internal use only.
    """

    if isinstance(scopes, basestring):
      scopes = [scopes]
    self.scopes = scopes
    self.service_account_id = service_account_id
    self.make_token_async = token_maker or _make_token_async
    self.token = None
    if not retry_params:
      retry_params = api_utils._get_default_retry_params()
    self.retry_params = retry_params

  def __getstate__(self):
    """Store state as part of serialization/pickling."""
    return {'token': self.token,
            'scopes': self.scopes,
            'id': self.service_account_id,
            'a_maker': None if self.make_token_async == _make_token_async
            else self.make_token_async,
            'retry_params': self.retry_params}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling."""
    self.__init__(state['scopes'],
                  service_account_id=state['id'],
                  token_maker=state['a_maker'],
                  retry_params=state['retry_params'])
    self.token = state['token']

  @ndb.tasklet
  def do_request_async(self, url, method='GET', headers=None, payload=None,
                       deadline=None, callback=None):
    """Issue one HTTP request.

    This is an async wrapper around urlfetch(). It adds an authentication
    header and retries on a 401 status code. Upon other retriable errors,
    it performs blocking retries.
    """
    headers = {} if headers is None else dict(headers)
    token = yield self.get_token_async()
    headers['authorization'] = 'OAuth ' + token

    retry = False
    resp = None
    try:
      resp = yield self.urlfetch_async(url, payload=payload, method=method,
                                       headers=headers, follow_redirects=False,
                                       deadline=deadline, callback=callback)
      if resp.status_code == httplib.UNAUTHORIZED:
        token = yield self.get_token_async(refresh=True)
        headers['authorization'] = 'OAuth ' + token
        resp = yield self.urlfetch_async(
            url, payload=payload, method=method, headers=headers,
            follow_redirects=False, deadline=deadline, callback=callback)
    except api_utils._RETRIABLE_EXCEPTIONS:
      retry = True
    else:
      retry = api_utils._should_retry(resp)

    if retry:
      retry_resp = api_utils._retry_fetch(
          url, retry_params=self.retry_params, payload=payload, method=method,
          headers=headers, follow_redirects=False, deadline=deadline)
      if retry_resp:
        resp = retry_resp
      elif not resp:
        raise

    raise ndb.Return((resp.status_code, resp.headers, resp.content))

  @ndb.tasklet
  def get_token_async(self, refresh=False):
    """Get an authentication token.

    The token is cached in memcache, keyed by the scopes argument.

    Args:
      refresh: If True, ignore a cached token; default False.

    Returns:
      An authentication token.
    """
    if self.token is not None and not refresh:
      raise ndb.Return(self.token)
    key = '%s,%s' % (self.service_account_id, ','.join(self.scopes))
    ts = None
    if not refresh:
      ts = yield _AE_TokenStorage_.get_by_id_async(key, use_datastore=False)
    if ts is None:
      token, expires_at = yield self.make_token_async(
          self.scopes, self.service_account_id)
      timeout = int(expires_at - time.time())
      ts = _AE_TokenStorage_(id=key, token=token)
      if timeout > 0:
        yield ts.put_async(memcache_timeout=timeout, use_datastore=False)
    self.token = ts.token
    raise ndb.Return(self.token)

  def urlfetch_async(self, url, **kwds):
    """Make an async urlfetch() call.

    This just passes the url and keyword arguments to NDB's async
    urlfetch() wrapper in the current context.

    This returns a Future despite not being decorated with @ndb.tasklet!
    """
    ctx = ndb.get_context()
    return ctx.urlfetch(url, **kwds)


_RestApi = add_sync_methods(_RestApi)

########NEW FILE########
__FILENAME__ = storage_api
# Copyright 2012 Google Inc. All Rights Reserved.

"""Python wrappers for the Google Storage RESTful API."""





__all__ = ['ReadBuffer',
           'StreamingBuffer',
          ]

import collections
import os
import urlparse

from . import errors
from . import rest_api

try:
  from google.appengine.api import urlfetch
  from google.appengine.ext import ndb
except ImportError:
  from google.appengine.api import urlfetch
  from google.appengine.ext import ndb


class _StorageApi(rest_api._RestApi):
  """A simple wrapper for the Google Storage RESTful API.

  WARNING: Do NOT directly use this api. It's an implementation detail
  and is subject to change at any release.

  All async methods have similar args and returns.

  Args:
    path: The path to the Google Storage object or bucket, e.g.
      '/mybucket/myfile' or '/mybucket'.
    **kwd: Options for urlfetch. e.g.
      headers={'content-type': 'text/plain'}, payload='blah'.

  Returns:
    A ndb Future. When fulfilled, future.get_result() should return
    a tuple of (status, headers, content) that represents a HTTP response
    of Google Cloud Storage XML API.
  """

  api_url = 'https://storage.googleapis.com'
  read_only_scope = 'https://www.googleapis.com/auth/devstorage.read_only'
  read_write_scope = 'https://www.googleapis.com/auth/devstorage.read_write'
  full_control_scope = 'https://www.googleapis.com/auth/devstorage.full_control'

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    Returns:
      A tuple (of dictionaries) with the state of this object
    """
    return (super(_StorageApi, self).__getstate__(), {'api_url': self.api_url})

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the tuple from a __getstate__ call
    """
    superstate, localstate = state
    super(_StorageApi, self).__setstate__(superstate)
    self.api_url = localstate['api_url']

  @ndb.tasklet
  def do_request_async(self, url, method='GET', headers=None, payload=None,
                       deadline=None, callback=None):
    """Inherit docs.

    This method translates urlfetch exceptions to more service specific ones.
    """
    if headers is None:
      headers = {}
    if 'x-goog-api-version' not in headers:
      headers['x-goog-api-version'] = '2'
    headers['accept-encoding'] = 'gzip, *'
    try:
      resp_tuple = yield super(_StorageApi, self).do_request_async(
          url, method=method, headers=headers, payload=payload,
          deadline=deadline, callback=callback)
    except urlfetch.DownloadError, e:
      raise errors.TimeoutError(
          'Request to Google Cloud Storage timed out.', e)

    raise ndb.Return(resp_tuple)


  def post_object_async(self, path, **kwds):
    """POST to an object."""
    return self.do_request_async(self.api_url + path, 'POST', **kwds)

  def put_object_async(self, path, **kwds):
    """PUT an object."""
    return self.do_request_async(self.api_url + path, 'PUT', **kwds)

  def get_object_async(self, path, **kwds):
    """GET an object.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'GET', **kwds)

  def delete_object_async(self, path, **kwds):
    """DELETE an object.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'DELETE', **kwds)

  def head_object_async(self, path, **kwds):
    """HEAD an object.

    Depending on request headers, HEAD returns various object properties,
    e.g. Content-Length, Last-Modified, and ETag.

    Note: No payload argument is supported.
    """
    return self.do_request_async(self.api_url + path, 'HEAD', **kwds)

  def get_bucket_async(self, path, **kwds):
    """GET a bucket."""
    return self.do_request_async(self.api_url + path, 'GET', **kwds)


_StorageApi = rest_api.add_sync_methods(_StorageApi)


class ReadBuffer(object):
  """A class for reading Google storage files.

  To achieve max prefetching benefit, always read by your buffer size.
  """

  DEFAULT_BUFFER_SIZE = 1024 * 1024
  MAX_REQUEST_SIZE = 30 * DEFAULT_BUFFER_SIZE

  def __init__(self,
               api,
               path,
               max_buffer_size=DEFAULT_BUFFER_SIZE,
               max_request_size=MAX_REQUEST_SIZE):
    """Constructor.

    Args:
      api: A StorageApi instance.
      path: Path to the object, e.g. '/mybucket/myfile'.
      max_buffer_size: Max bytes to buffer.
      max_request_size: Max bytes to request in one urlfetch.
    """
    self._api = api
    self._path = path
    self._max_buffer_size = max_buffer_size
    self._max_request_size = max_request_size
    self._offset = 0
    self._reset_buffer()
    self._closed = False
    self._etag = None

    self._buffer_future = self._get_segment(0, self._max_buffer_size)

    status, headers, _ = self._api.head_object(path)
    errors.check_status(status, [200])
    self._file_size = long(headers['content-length'])
    self._check_etag(headers.get('etag'))
    if self._file_size == 0:
      self._buffer_future = None

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    The contents of the read buffer are not stored, only the current offset for
    data read by the client. A new read buffer is established at unpickling.
    The head information for the object (file size and etag) are stored to
    reduce startup and ensure the file has not changed.

    Returns:
      A dictionary with the state of this object
    """
    return {'api': self._api,
            'path': self._path,
            'buffer_size': self._max_buffer_size,
            'request_size': self._max_request_size,
            'etag': self._etag,
            'size': self._file_size,
            'offset': self._offset,
            'closed': self._closed}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the dictionary from a __getstate__ call

    Along with restoring the state, pre-fetch the next read buffer.
    """
    self._api = state['api']
    self._path = state['path']
    self._max_buffer_size = state['buffer_size']
    self._max_request_size = state['request_size']
    self._etag = state['etag']
    self._file_size = state['size']
    self._offset = state['offset']
    self._reset_buffer()
    self._closed = state['closed']
    if self._offset < self._file_size and not self._closed:
      self._buffer_future = self._get_segment(self._offset,
                                              self._max_buffer_size)
    else:
      self._buffer_future = None

  def readline(self, size=-1):
    """Read one line delimited by '\n' from the file.

    A trailing newline character is kept in the string. It may be absent when a
    file ends with an incomplete line. If the size argument is non-negative,
    it specifies the maximum string size (counting the newline) to return.
    A negative size is the same as unspecified. Empty string is returned
    only when EOF is encountered immediately.

    Args:
      size: Maximum number of bytes to read. If not specified, readline stops
        only on '\n' or EOF.

    Returns:
      The data read as a string.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    self._buffer_future = None

    data_list = []

    if size == 0:
      return ''

    while True:
      if size >= 0:
        end_offset = self._buffer_offset + size
      else:
        end_offset = len(self._buffer)
      newline_offset = self._buffer.find('\n', self._buffer_offset, end_offset)

      if newline_offset >= 0:
        data_list.append(
            self._read_buffer(newline_offset + 1 - self._buffer_offset))
        return ''.join(data_list)
      else:
        result = self._read_buffer(size)
        data_list.append(result)
        size -= len(result)
        if size == 0 or self._file_size == self._offset:
          return ''.join(data_list)
        self._fill_buffer()

  def read(self, size=-1):
    """Read data from RAW file.

    Args:
      size: Number of bytes to read as integer. Actual number of bytes
        read is always equal to size unless EOF is reached. If size is
        negative or unspecified, read the entire file.

    Returns:
      data read as str.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    if self._file_size == 0:
      return ''

    if size >= 0 and size <= len(self._buffer) - self._buffer_offset:
      result = self._read_buffer(size)
    else:
      size -= len(self._buffer) - self._buffer_offset
      data_list = [self._read_buffer()]

      if self._buffer_future:
        self._reset_buffer(self._buffer_future.get_result())
        self._buffer_future = None

      if size >= 0 and size <= len(self._buffer) - self._buffer_offset:
        data_list.append(self._read_buffer(size))
      else:
        size -= len(self._buffer)
        data_list.append(self._read_buffer())
        if self._offset == self._file_size:
          return ''.join(data_list)

        if size < 0 or size >= self._file_size - self._offset:
          needs = self._file_size - self._offset
        else:
          needs = size
        data_list.extend(self._get_segments(self._offset, needs))
        self._offset += needs
      result = ''.join(data_list)
      data_list = None

    assert self._buffer_future is None
    if self._offset != self._file_size and not self._buffer:
      self._buffer_future = self._get_segment(self._offset,
                                              self._max_buffer_size)
    return result

  def _read_buffer(self, size=-1):
    """Returns bytes from self._buffer and update related offsets.

    Args:
      size: number of bytes to read. Read the entire buffer if negative.

    Returns:
      Requested bytes from buffer.
    """
    if size < 0:
      size = len(self._buffer) - self._buffer_offset
    result = self._buffer[self._buffer_offset : self._buffer_offset+size]
    self._offset += len(result)
    self._buffer_offset += len(result)
    if self._buffer_offset == len(self._buffer):
      self._reset_buffer()
    return result

  def _fill_buffer(self):
    """Fill self._buffer."""
    segments = self._get_segments(self._offset,
                                  min(self._max_buffer_size,
                                      self._max_request_size,
                                      self._file_size-self._offset))

    self._reset_buffer(''.join(segments))

  def _get_segments(self, start, request_size):
    """Get segments of the file from Google Storage as a list.

    A large request is broken into segments to avoid hitting urlfetch
    response size limit. Each segment is returned from a separate urlfetch.

    Args:
      start: start offset to request. Inclusive. Have to be within the
        range of the file.
      request_size: number of bytes to request. Can not exceed the logical
        range of the file.

    Returns:
      A list of file segments in order
    """
    end = start + request_size
    futures = []

    while request_size > self._max_request_size:
      futures.append(self._get_segment(start, self._max_request_size))
      request_size -= self._max_request_size
      start += self._max_request_size
    if start < end:
      futures.append(self._get_segment(start, end-start))
    return [fut.get_result() for fut in futures]

  @ndb.tasklet
  def _get_segment(self, start, request_size):
    """Get a segment of the file from Google Storage.

    Args:
      start: start offset of the segment. Inclusive. Have to be within the
        range of the file.
      request_size: number of bytes to request. Have to be within the range
        of the file.

    Yields:
      a segment [start, start + request_size) of the file.

    Raises:
      ValueError: if the file has changed while reading.
    """
    end = start + request_size - 1
    content_range = '%d-%d' % (start, end)
    headers = {'Range': 'bytes=' + content_range}
    status, headers, content = yield self._api.get_object_async(self._path,
                                                                headers=headers)
    errors.check_status(status, [200, 206], headers)
    self._check_etag(headers.get('etag'))
    raise ndb.Return(content)

  def _check_etag(self, etag):
    """Check if etag is the same across requests to GCS.

    If self._etag is None, set it. If etag is set, check that the new
    etag equals the old one.

    In the __init__ method, we fire one HEAD and one GET request using
    ndb tasklet. One of them would return first and set the first value.

    Args:
      etag: etag from a GCS HTTP response. None if etag is not part of the
        response header. It could be None for example in the case of GCS
        composite file.

    Raises:
      ValueError: if two etags are not equal.
    """
    if etag is None:
      return
    elif self._etag is None:
      self._etag = etag
    elif self._etag != etag:
      raise ValueError('File on GCS has changed while reading.')

  def close(self):
    self._closed = True
    self._reset_buffer()
    self._buffer_future = None

  def __enter__(self):
    return self

  def __exit__(self, atype, value, traceback):
    self.close()
    return False

  def seek(self, offset, whence=os.SEEK_SET):
    """Set the file's current offset.

    Note if the new offset is out of bound, it is adjusted to either 0 or EOF.

    Args:
      offset: seek offset as number.
      whence: seek mode. Supported modes are os.SEEK_SET (absolute seek),
        os.SEEK_CUR (seek relative to the current position), and os.SEEK_END
        (seek relative to the end, offset should be negative).

    Raises:
      IOError: When this buffer is closed.
      ValueError: When whence is invalid.
    """
    self._check_open()

    self._reset_buffer()
    self._buffer_future = None

    if whence == os.SEEK_SET:
      self._offset = offset
    elif whence == os.SEEK_CUR:
      self._offset += offset
    elif whence == os.SEEK_END:
      self._offset = self._file_size + offset
    else:
      raise ValueError('Whence mode %s is invalid.' % str(whence))

    self._offset = min(self._offset, self._file_size)
    self._offset = max(self._offset, 0)
    if self._offset != self._file_size:
      self._buffer_future = self._get_segment(self._offset,
                                              self._max_buffer_size)

  def tell(self):
    """Tell the file's current offset.

    Returns:
      current offset in reading this file.

    Raises:
      IOError: When this buffer is closed.
    """
    self._check_open()
    return self._offset

  def _check_open(self):
    if self._closed:
      raise IOError('Buffer is closed.')

  def _reset_buffer(self, new_buffer='', buffer_offset=0):
    self._buffer = new_buffer
    self._buffer_offset = buffer_offset


class StreamingBuffer(object):
  """A class for creating large objects using the 'resumable' API.

  The API is a subset of the Python writable stream API sufficient to
  support writing zip files using the zipfile module.

  The exact sequence of calls and use of headers is documented at
  https://developers.google.com/storage/docs/developer-guide#unknownresumables
  """

  _blocksize = 256 * 1024

  _maxrequestsize = 16 * _blocksize

  def __init__(self,
               api,
               path,
               content_type=None,
               gcs_headers=None):
    """Constructor.

    Args:
      api: A StorageApi instance.
      path: Path to the object, e.g. '/mybucket/myfile'.
      content_type: Optional content-type; Default value is
        delegate to Google Cloud Storage.
      gcs_headers: additional gs headers as a str->str dict, e.g
        {'x-goog-acl': 'private', 'x-goog-meta-foo': 'foo'}.
    """
    assert self._maxrequestsize > self._blocksize
    assert self._maxrequestsize % self._blocksize == 0

    self._api = api
    self._path = path

    self._buffer = collections.deque()
    self._buffered = 0
    self._written = 0
    self._offset = 0

    self._closed = False

    headers = {'x-goog-resumable': 'start'}
    if content_type:
      headers['content-type'] = content_type
    if gcs_headers:
      headers.update(gcs_headers)
    status, headers, _ = self._api.post_object(path, headers=headers)
    errors.check_status(status, [201], headers)
    loc = headers.get('location')
    if not loc:
      raise IOError('No location header found in 201 response')
    parsed = urlparse.urlparse(loc)
    self._path_with_token = '%s?%s' % (self._path, parsed.query)

  def __getstate__(self):
    """Store state as part of serialization/pickling.

    The contents of the write buffer are stored. Writes to the underlying
    storage are required to be on block boundaries (_blocksize) except for the
    last write. In the worst case the pickled version of this object may be
    slightly larger than the blocksize.

    Returns:
      A dictionary with the state of this object

    """
    return {'api': self._api,
            'path_token': self._path_with_token,
            'buffer': self._buffer,
            'buffered': self._buffered,
            'written': self._written,
            'offset': self._offset,
            'closed': self._closed}

  def __setstate__(self, state):
    """Restore state as part of deserialization/unpickling.

    Args:
      state: the dictionary from a __getstate__ call
    """
    self._api = state['api']
    self._path_with_token = state['path_token']
    self._buffer = state['buffer']
    self._buffered = state['buffered']
    self._written = state['written']
    self._offset = state['offset']
    self._closed = state['closed']

  def write(self, data):
    """Write some bytes."""
    self._check_open()
    assert isinstance(data, str)
    if not data:
      return
    self._buffer.append(data)
    self._buffered += len(data)
    self._offset += len(data)
    if self._buffered >= self._blocksize:
      self._flush()

  def flush(self):
    """Dummy API.

    This API is provided because the zipfile module uses it.  It is a
    no-op because Google Storage *requires* that all writes except for
    the final one are multiples on 256K bytes aligned on 256K-byte
    boundaries.
    """
    self._check_open()

  def tell(self):
    """Return the total number of bytes passed to write() so far.

    (There is no seek() method.)
    """
    self._check_open()
    return self._offset

  def close(self):
    """Flush the buffer and finalize the file.

    When this returns the new file is available for reading.
    """
    if not self._closed:
      self._closed = True
      self._flush(finish=True)
      self._buffer = None

  def __enter__(self):
    return self

  def __exit__(self, atype, value, traceback):
    self.close()
    return False

  def _flush(self, finish=False):
    """Internal API to flush.

    This is called only when the total amount of buffered data is at
    least self._blocksize, or to flush the final (incomplete) block of
    the file with finish=True.
    """
    flush_len = 0 if finish else self._blocksize
    last = False

    while self._buffered >= flush_len:
      buffer = []
      buffered = 0

      while self._buffer:
        buf = self._buffer.popleft()
        size = len(buf)
        self._buffered -= size
        buffer.append(buf)
        buffered += size
        if buffered >= self._maxrequestsize:
          break

      if buffered > self._maxrequestsize:
        excess = buffered - self._maxrequestsize
      elif finish:
        excess = 0
      else:
        excess = buffered % self._blocksize

      if excess:
        over = buffer.pop()
        size = len(over)
        assert size >= excess
        buffered -= size
        head, tail = over[:-excess], over[-excess:]
        self._buffer.appendleft(tail)
        self._buffered += len(tail)
        if head:
          buffer.append(head)
          buffered += len(head)

      if finish:
        last = not self._buffered
      self._send_data(''.join(buffer), last)
      if last:
        break

  def _send_data(self, data, last):
    """Send the block to the storage service and update self._written."""
    headers = {}
    length = self._written + len(data)

    if data:
      headers['content-range'] = ('bytes %d-%d/%s' %
                                  (self._written, length-1,
                                   length if last else '*'))
    else:
      headers['content-range'] = ('bytes */%s' %
                                  length if last else '*')
    status, _, _ = self._api.put_object(
        self._path_with_token, payload=data, headers=headers)
    if last:
      expected = 200
    else:
      expected = 308
    errors.check_status(status, [expected], headers)
    self._written += len(data)

  def _check_open(self):
    if self._closed:
      raise IOError('Buffer is closed.')

########NEW FILE########
__FILENAME__ = test_utils
# Copyright 2013 Google Inc. All Rights Reserved.

"""Utils for testing."""


class MockUrlFetchResult(object):

  def __init__(self, status, headers, body):
    self.status_code = status
    self.headers = headers
    self.content = body
    self.content_was_truncated = False
    self.final_url = None

########NEW FILE########
__FILENAME__ = api_utils_test
# Copyright 2013 Google Inc. All Rights Reserved.

"""Tests for api_utils.py."""

import httplib
import os
import threading
import time
import unittest

import mock

from google.appengine.api import urlfetch
from google.appengine.runtime import apiproxy_errors


try:
  from cloudstorage import api_utils
  from cloudstorage import test_utils
except ImportError:
  from google.appengine.ext.cloudstorage import api_utils
  from google.appengine.ext.cloudstorage import test_utils


class RetryParamsTest(unittest.TestCase):
  """Tests for RetryParams."""

  def testValidation(self):
    self.assertRaises(TypeError, api_utils.RetryParams, 2)
    self.assertRaises(TypeError, api_utils.RetryParams, urlfetch_timeout='foo')
    self.assertRaises(TypeError, api_utils.RetryParams, max_retries=1.1)
    self.assertRaises(ValueError, api_utils.RetryParams, initial_delay=0)
    api_utils.RetryParams(backoff_factor=1)

  def testNoDelay(self):
    start_time = time.time()
    retry_params = api_utils.RetryParams(max_retries=0, min_retries=5)
    self.assertEqual(-1, retry_params.delay(1, start_time))
    retry_params = api_utils.RetryParams(max_retry_period=1, max_retries=1)
    self.assertEqual(-1, retry_params.delay(2, start_time - 2))

  def testMinRetries(self):
    start_time = time.time()
    retry_params = api_utils.RetryParams(min_retries=3,
                                         max_retry_period=10,
                                         initial_delay=1)
    with mock.patch('time.time') as t:
      t.return_value = start_time + 11
      self.assertEqual(1, retry_params.delay(1, start_time))

  def testPerThreadSetting(self):
    set_count = [0]
    cv = threading.Condition()

    retry_params1 = api_utils.RetryParams(max_retries=1000)
    retry_params2 = api_utils.RetryParams(max_retries=2000)
    retry_params3 = api_utils.RetryParams(max_retries=3000)

    def Target(retry_params):
      api_utils.set_default_retry_params(retry_params)
      with cv:
        set_count[0] += 1
        if set_count[0] != 3:
          cv.wait()
        cv.notify()
      self.assertEqual(retry_params, api_utils._get_default_retry_params())

    threading.Thread(target=Target, args=(retry_params1,)).start()
    threading.Thread(target=Target, args=(retry_params2,)).start()
    threading.Thread(target=Target, args=(retry_params3,)).start()

  def testPerRequestSetting(self):
    os.environ['REQUEST_LOG_ID'] = '1'
    retry_params = api_utils.RetryParams(max_retries=1000)
    api_utils.set_default_retry_params(retry_params)
    self.assertEqual(retry_params, api_utils._get_default_retry_params())

    os.environ['REQUEST_LOG_ID'] = '2'
    self.assertEqual(api_utils.RetryParams(),
                     api_utils._get_default_retry_params())

  def testDelay(self):
    start_time = time.time()
    retry_params = api_utils.RetryParams(backoff_factor=3,
                                         initial_delay=1,
                                         max_delay=28,
                                         max_retries=10,
                                         max_retry_period=100)
    with mock.patch('time.time') as t:
      t.return_value = start_time + 1
      self.assertEqual(1, retry_params.delay(1, start_time))
      self.assertEqual(3, retry_params.delay(2, start_time))
      self.assertEqual(9, retry_params.delay(3, start_time))
      self.assertEqual(27, retry_params.delay(4, start_time))
      self.assertEqual(28, retry_params.delay(5, start_time))
      self.assertEqual(28, retry_params.delay(6, start_time))
      t.return_value = start_time + 101
      self.assertEqual(-1, retry_params.delay(7, start_time))


class RetryFetchTest(unittest.TestCase):
  """Tests for _retry_fetch."""

  def setUp(self):
    super(RetryFetchTest, self).setUp()
    self.results = []
    self.max_retries = 10
    self.retry_params = api_utils.RetryParams(backoff_factor=1,
                                              max_retries=self.max_retries)

  def _SideEffect(self, *args, **kwds):
    if self.results:
      result = self.results.pop(0)
      if isinstance(result, Exception):
        raise result
      return result

  def testRetriableStatus(self):
    self.assertTrue(api_utils._should_retry(
        test_utils.MockUrlFetchResult(httplib.REQUEST_TIMEOUT, None, None)))
    self.assertTrue(api_utils._should_retry(
        test_utils.MockUrlFetchResult(555, None, None)))

  def testNoRetry(self):
    retry_params = api_utils.RetryParams(max_retries=0)
    self.assertEqual(None, api_utils._retry_fetch('foo', retry_params))

  def testRetrySuccess(self):
    self.results.append(test_utils.MockUrlFetchResult(httplib.REQUEST_TIMEOUT,
                                                      None, None))
    self.results.append(test_utils.MockUrlFetchResult(
        httplib.SERVICE_UNAVAILABLE, None, None))
    self.results.append(urlfetch.DownloadError())
    self.results.append(apiproxy_errors.Error())
    self.results.append(test_utils.MockUrlFetchResult(httplib.ACCEPTED,
                                                      None, None))
    with mock.patch.object(api_utils.urlfetch, 'fetch') as f:
      f.side_effect = self._SideEffect
      self.assertEqual(httplib.ACCEPTED,
                       api_utils._retry_fetch('foo', self.retry_params,
                                              deadline=1000).status_code)
      self.assertEqual(1000, f.call_args[1]['deadline'])

  def testRetryFailWithUrlfetchTimeOut(self):
    with mock.patch.object(api_utils.urlfetch, 'fetch') as f:
      f.side_effect = urlfetch.DownloadError
      try:
        api_utils._retry_fetch('foo', self.retry_params)
        self.fail('Should have raised error.')
      except urlfetch.DownloadError:
        self.assertEqual(self.max_retries, f.call_count)

  def testRetryFailWithResponseTimeOut(self):
    self.results.extend([urlfetch.DownloadError()] * (self.max_retries - 1))
    self.results.append(test_utils.MockUrlFetchResult(httplib.REQUEST_TIMEOUT,
                                                      None, None))
    with mock.patch.object(api_utils.urlfetch, 'fetch') as f:
      f.side_effect = self._SideEffect
      self.assertEqual(
          httplib.REQUEST_TIMEOUT,
          api_utils._retry_fetch('foo', self.retry_params).status_code)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = cloudstorage_test
# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for cloudstorage_api.py."""

from __future__ import with_statement



import gzip
import hashlib
import math
import os
import time
import unittest

from google.appengine.ext import testbed

from google.appengine.ext.cloudstorage import stub_dispatcher

try:
  import cloudstorage
  from cloudstorage import cloudstorage_api
  from cloudstorage import errors
except ImportError:
  from google.appengine.ext import cloudstorage
  from google.appengine.ext.cloudstorage import cloudstorage_api
  from google.appengine.ext.cloudstorage import errors

BUCKET = '/bucket'
TESTFILE = BUCKET + '/testfile'
DEFAULT_CONTENT = ['a'*1024*257,
                   'b'*1024*257,
                   'c'*1024*257]


class CloudStorageTest(unittest.TestCase):
  """Test for cloudstorage."""

  def setUp(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_app_identity_stub()
    self.testbed.init_blobstore_stub()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_urlfetch_stub()
    self._old_max_keys = stub_dispatcher._MAX_GET_BUCKET_RESULT
    stub_dispatcher._MAX_GET_BUCKET_RESULT = 2
    self.start_time = time.time()
    cloudstorage.set_default_retry_params(None)

  def tearDown(self):
    stub_dispatcher._MAX_GET_BUCKET_RESULT = self._old_max_keys
    self.testbed.deactivate()

  def CreateFile(self, filename):
    f = cloudstorage.open(filename,
                          'w',
                          'text/plain',
                          {'x-goog-meta-foo': 'foo',
                           'x-goog-meta-bar': 'bar',
                           'x-goog-acl': 'public-read',
                           'cache-control': 'public, max-age=6000',
                           'content-disposition': 'attachment; filename=f.txt'})
    for content in DEFAULT_CONTENT:
      f.write(content)
    f.close()

  def testGzip(self):
    with cloudstorage.open(TESTFILE, 'w', 'text/plain',
                           {'content-encoding': 'gzip'}) as f:
      gz = gzip.GzipFile('', 'wb', 9, f)
      gz.write('a'*1024)
      gz.write('b'*1024)
      gz.close()

    stat = cloudstorage.stat(TESTFILE)
    self.assertEqual('text/plain', stat.content_type)
    self.assertEqual('gzip', stat.metadata['content-encoding'])
    self.assertTrue(stat.st_size < 1024*2)

    with cloudstorage.open(TESTFILE) as f:
      gz = gzip.GzipFile('', 'rb', 9, f)
      result = gz.read(10)
      self.assertEqual('a'*10, result)
      self.assertEqual('a'*1014 + 'b'*1024, gz.read())

  def testCopy2(self):
    with cloudstorage.open(TESTFILE, 'w',
                           'text/foo', {'x-goog-meta-foo': 'foo'}) as f:
      f.write('abcde')

    dst = TESTFILE + 'copy'
    self.assertRaises(cloudstorage.NotFoundError, cloudstorage.stat, dst)
    cloudstorage_api._copy2(TESTFILE, dst)

    src_stat = cloudstorage.stat(TESTFILE)
    dst_stat = cloudstorage.stat(dst)
    self.assertEqual(src_stat.st_size, dst_stat.st_size)
    self.assertEqual(src_stat.etag, dst_stat.etag)
    self.assertEqual(src_stat.content_type, dst_stat.content_type)
    self.assertEqual(src_stat.metadata, dst_stat.metadata)

    with cloudstorage.open(dst) as f:
      self.assertEqual('abcde', f.read())

    cloudstorage.delete(dst)
    cloudstorage.delete(TESTFILE)

  def testDelete(self):
    self.assertRaises(errors.NotFoundError, cloudstorage.delete, TESTFILE)
    self.CreateFile(TESTFILE)
    cloudstorage.delete(TESTFILE)
    self.assertRaises(errors.NotFoundError, cloudstorage.delete, TESTFILE)
    self.assertRaises(errors.NotFoundError, cloudstorage.stat, TESTFILE)

  def testReadEntireFile(self):
    f = cloudstorage.open(TESTFILE, 'w')
    f.write('abcde')
    f.close()

    f = cloudstorage.open(TESTFILE, read_buffer_size=1)
    self.assertEqual('abcde', f.read())
    f.close()

    f = cloudstorage.open(TESTFILE)
    self.assertEqual('abcde', f.read(8))
    f.close()

  def testReadNonexistFile(self):
    self.assertRaises(errors.NotFoundError, cloudstorage.open, TESTFILE)

  def testRetryParams(self):
    retry_params = cloudstorage.RetryParams(max_retries=0)
    cloudstorage.set_default_retry_params(retry_params)

    retry_params.max_retries = 1000
    with cloudstorage.open(TESTFILE, 'w') as f:
      self.assertEqual(0, f._api.retry_params.max_retries)

    with cloudstorage.open(TESTFILE, 'w') as f:
      cloudstorage.set_default_retry_params(retry_params)
      self.assertEqual(0, f._api.retry_params.max_retries)

    per_call_retry_params = cloudstorage.RetryParams()
    with cloudstorage.open(TESTFILE, 'w',
                           retry_params=per_call_retry_params) as f:
      self.assertEqual(per_call_retry_params, f._api.retry_params)

  def testReadEmptyFile(self):
    f = cloudstorage.open(TESTFILE, 'w')
    f.write('')
    f.close()

    f = cloudstorage.open(TESTFILE)
    self.assertEqual('', f.read())
    self.assertEqual('', f.read())
    f.close()

  def testReadSmall(self):
    f = cloudstorage.open(TESTFILE, 'w')
    f.write('abcdefghij')
    f.close()

    f = cloudstorage.open(TESTFILE, read_buffer_size=3)
    self.assertEqual('ab', f.read(2))
    self.assertEqual('c', f.read(1))
    self.assertEqual('de', f.read(2))
    self.assertEqual('fghij', f.read())
    f.close()

  def testWriteRead(self):
    f = cloudstorage.open(TESTFILE, 'w')
    f.write('a')
    f.write('b'*1024)
    f.write('c'*1024 + '\n')
    f.write('d'*1024*1024)
    f.write('e'*1024*1024*10)
    self.assertRaises(errors.NotFoundError, cloudstorage.stat, TESTFILE)
    f.close()

    f = cloudstorage.open(TESTFILE)
    self.assertEqual('a' + 'b'*1024, f.read(1025))
    self.assertEqual('c'*1024 + '\n', f.readline())
    self.assertEqual('d'*1024*1024, f.read(1024*1024))
    self.assertEqual('e'*1024*1024*10, f.read())
    self.assertEqual('', f.read())
    self.assertEqual('', f.readline())

  def WriteInBlockSizeTest(self):
    f = cloudstorage.open(TESTFILE, 'w')
    f.write('a'*256*1024)
    f.write('b'*256*1024)
    f.close()

    f = cloudstorage.open(TESTFILE)
    self.assertEqual('a'*256*1024 + 'b'*256*1024, f.read())
    self.assertEqual('', f.read())
    self.assertEqual('', f.readline())
    f.close()

  def testWriteReadWithContextManager(self):
    with cloudstorage.open(TESTFILE, 'w') as f:
      f.write('a')
      f.write('b'*1024)
      f.write('c'*1024 + '\n')
      f.write('d'*1024*1024)
      f.write('e'*1024*1024*10)
    self.assertTrue(f._closed)

    with cloudstorage.open(TESTFILE) as f:
      self.assertEqual('a' + 'b'*1024, f.read(1025))
      self.assertEqual('c'*1024 + '\n', f.readline())
      self.assertEqual('d'*1024*1024, f.read(1024*1024))
      self.assertEqual('e'*1024*1024*10, f.read())
      self.assertEqual('', f.read())
      self.assertEqual('', f.readline())
    self.assertTrue(f._closed)

  def testSeekAndTell(self):
    f = cloudstorage.open(TESTFILE, 'w')
    f.write('abcdefghij')
    f.close()

    f = cloudstorage.open(TESTFILE)
    f.seek(5)
    self.assertEqual(5, f.tell())
    self.assertEqual('f', f.read(1))
    self.assertEqual(6, f.tell())
    f.seek(-1, os.SEEK_CUR)
    self.assertEqual('f', f.read(1))
    f.seek(-1, os.SEEK_END)
    self.assertEqual('j', f.read(1))

  def testStat(self):
    self.CreateFile(TESTFILE)
    filestat = cloudstorage.stat(TESTFILE)
    content = ''.join(DEFAULT_CONTENT)
    self.assertEqual(len(content), filestat.st_size)
    self.assertEqual('text/plain', filestat.content_type)
    self.assertEqual('foo', filestat.metadata['x-goog-meta-foo'])
    self.assertEqual('bar', filestat.metadata['x-goog-meta-bar'])
    self.assertEqual('public, max-age=6000', filestat.metadata['cache-control'])
    self.assertEqual(
        'attachment; filename=f.txt',
        filestat.metadata['content-disposition'])
    self.assertEqual(TESTFILE, filestat.filename)
    self.assertEqual(hashlib.md5(content).hexdigest(), filestat.etag)
    self.assertTrue(math.floor(self.start_time) <= filestat.st_ctime)
    self.assertTrue(filestat.st_ctime <= time.time())

  def testListBucket(self):
    bars = [BUCKET + '/test/bar' + str(i) for i in range(3)]
    foos = [BUCKET + '/test/foo' + str(i) for i in range(3)]
    filenames = bars + foos
    for filename in filenames:
      self.CreateFile(filename)

    bucket = cloudstorage.listbucket(BUCKET, prefix='test/')
    self.assertEqual(filenames, [stat.filename for stat in bucket])

    bucket = cloudstorage.listbucket(BUCKET, prefix='test/', max_keys=1)
    stats = list(bucket)
    self.assertEqual(1, len(stats))
    stat = stats[0]
    content = ''.join(DEFAULT_CONTENT)
    self.assertEqual(filenames[0], stat.filename)
    self.assertEqual(len(content), stat.st_size)
    self.assertEqual(hashlib.md5(content).hexdigest(), stat.etag)

    bucket = cloudstorage.listbucket(BUCKET,
                                     prefix='test/',
                                     marker='test/foo0',
                                     max_keys=1)
    stats = [stat for stat in bucket]
    self.assertEqual(1, len(stats))
    stat = stats[0]
    self.assertEqual(foos[1], stat.filename)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = rest_api_test
# Copyright 2012 Google Inc. All Rights Reserved.




import httplib
import pickle
import unittest
import mock

from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from google.appengine.ext import testbed

try:
  from cloudstorage import api_utils
  from cloudstorage import rest_api
  from cloudstorage import test_utils
except ImportError:
  from google.appengine.ext.cloudstorage import api_utils
  from google.appengine.ext.cloudstorage import rest_api
  from google.appengine.ext.cloudstorage import test_utils


class RestApiTest(unittest.TestCase):

  def setUp(self):
    super(RestApiTest, self).setUp()
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_app_identity_stub()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()
    self.testbed.init_urlfetch_stub()
    api_utils._thread_local_settings.retry_params = None

  def tearDown(self):
    self.testbed.deactivate()
    super(RestApiTest, self).tearDown()

  def testBasicCall(self):
    api = rest_api._RestApi('scope')
    self.assertEqual(api.scopes, ['scope'])

    fut_get_token = ndb.Future()
    fut_get_token.set_result('blah')
    api.get_token_async = mock.create_autospec(api.get_token_async,
                                               return_value=fut_get_token)

    fut_urlfetch = ndb.Future()
    fut_urlfetch.set_result(
        test_utils.MockUrlFetchResult(200, {'foo': 'bar'}, 'yoohoo'))
    api.urlfetch_async = mock.create_autospec(api.urlfetch_async,
                                              return_value=fut_urlfetch)

    res = api.do_request('http://example.com')

    self.assertEqual(res, (200, {'foo': 'bar'}, 'yoohoo'))
    api.urlfetch_async.assert_called_once_with(
        'http://example.com',
        headers={'authorization': 'OAuth blah'},
        follow_redirects=False,
        payload=None,
        method='GET',
        deadline=None,
        callback=None)

  def testAsyncCall(self):
    api = rest_api._RestApi('scope')

    fut_urlfetch = ndb.Future()
    fut_urlfetch.set_result(
        test_utils.MockUrlFetchResult(200, {'foo': 'bar'}, 'yoohoo'))
    api.urlfetch_async = mock.create_autospec(api.urlfetch_async,
                                              return_value=fut_urlfetch)

    fut = api.do_request_async('http://example.com')
    res = fut.get_result()

    self.assertEqual(res, (200, {'foo': 'bar'}, 'yoohoo'))
    api.urlfetch_async.assert_called_once_with(
        'http://example.com',
        headers=mock.ANY,
        follow_redirects=False,
        payload=None,
        method='GET',
        deadline=None,
        callback=None)

  def testMultipleScopes(self):
    api = rest_api._RestApi(['scope1', 'scope2'])
    self.assertEqual(api.scopes, ['scope1', 'scope2'])

  def testNegativeTimeout(self):
    api = rest_api._RestApi('scope')
    fut1 = ndb.Future()
    fut1.set_result(('token1', 0))
    fut2 = ndb.Future()
    fut2.set_result(('token2', 0))
    api.make_token_async = mock.create_autospec(
        api.make_token_async, side_effect=[fut1, fut2])
    token1 = api.get_token()
    api.token = None
    token2 = api.get_token()
    self.assertNotEqual(token1, token2)

  def testTokenMemoized(self):
    api = rest_api._RestApi('scope')
    self.assertEqual(api.token, None)
    t1 = api.get_token()
    self.assertEqual(api.token, t1)
    t2 = api.get_token()
    self.assertEqual(t2, t1)

    t3 = api.get_token(refresh=True)
    self.assertNotEqual(t2, t3)
    self.assertEqual(api.token, t3)

  def testDifferentServiceAccounts(self):
    api1 = rest_api._RestApi('scope', 123)
    api2 = rest_api._RestApi('scope', 456)

    t1 = api1.get_token()
    t2 = api2.get_token()
    self.assertNotEqual(t1, t2)

  def testSameServiceAccount(self):
    api1 = rest_api._RestApi('scope', 123)
    api2 = rest_api._RestApi('scope', 123)

    t1 = api1.get_token()
    t2 = api2.get_token()
    self.assertEqual(t1, t2)

  def testRefreshToken(self):
    api = rest_api._RestApi('scope')

    fut_get_token1 = ndb.Future()
    fut_get_token1.set_result('blah')
    fut_get_token2 = ndb.Future()
    fut_get_token2.set_result('bleh')

    api.get_token_async = mock.create_autospec(
        api.get_token_async,
        side_effect=[fut_get_token1, fut_get_token2])

    fut_urlfetch1 = ndb.Future()
    fut_urlfetch1.set_result(test_utils.MockUrlFetchResult(401, {}, ''))
    fut_urlfetch2 = ndb.Future()
    fut_urlfetch2.set_result(
        test_utils.MockUrlFetchResult(200, {'foo': 'bar'}, 'yoohoo'))

    api.urlfetch_async = mock.create_autospec(
        api.urlfetch_async,
        side_effect=[fut_urlfetch1, fut_urlfetch2])

    res = api.do_request('http://example.com')

    self.assertEqual(res, (200, {'foo': 'bar'}, 'yoohoo'))

    self.assertEqual(api.urlfetch_async.call_args_list,
                     [mock.call('http://example.com',
                                headers={'authorization': 'OAuth bleh'},
                                follow_redirects=False,
                                payload=None,
                                method='GET',
                                deadline=None,
                                callback=None),
                      mock.call('http://example.com',
                                headers={'authorization': 'OAuth bleh'},
                                follow_redirects=False,
                                payload=None,
                                method='GET',
                                deadline=None,
                                callback=None)])

  def testCallUrlFetch(self):
    api = rest_api._RestApi('scope')

    fut = ndb.Future()
    fut.set_result(test_utils.MockUrlFetchResult(200, {}, 'response'))
    ndb.Context.urlfetch = mock.create_autospec(
        ndb.Context.urlfetch,
        return_value=fut)

    res = api.urlfetch('http://example.com', method='PUT', headers={'a': 'b'})

    self.assertEqual(res.status_code, 200)
    self.assertEqual(res.content, 'response')

  def testPickling(self):
    retry_params = api_utils.RetryParams(max_retries=1000)
    api = rest_api._RestApi('scope', service_account_id=1,
                            retry_params=retry_params)
    self.assertNotEqual(None, api.get_token())

    pickled_api = pickle.loads(pickle.dumps(api))
    self.assertEqual(0, len(set(api.__dict__.keys()) ^
                            set(pickled_api.__dict__.keys())))
    for k, v in api.__dict__.iteritems():
      if not hasattr(v, '__call__'):
        self.assertEqual(v, pickled_api.__dict__[k])

    pickled_api.token = None

    fut_urlfetch = ndb.Future()
    fut_urlfetch.set_result(
        test_utils.MockUrlFetchResult(200, {'foo': 'bar'}, 'yoohoo'))
    pickled_api.urlfetch_async = mock.create_autospec(
        pickled_api.urlfetch_async, return_value=fut_urlfetch)

    res = pickled_api.do_request('http://example.com')
    self.assertEqual(res, (200, {'foo': 'bar'}, 'yoohoo'))

  def testRetryAfterDoRequestUrlFetchTimeout(self):
    api = rest_api._RestApi('scope')

    fut = ndb.Future()
    fut.set_exception(urlfetch.DownloadError())
    ndb.Context.urlfetch = mock.create_autospec(
        ndb.Context.urlfetch,
        return_value=fut)

    with mock.patch('google.appengine.api.urlfetch'
                    '.fetch') as f:
      f.return_value = test_utils.MockUrlFetchResult(httplib.ACCEPTED,
                                                     None, None)
      self.assertEqual(httplib.ACCEPTED, api.do_request('foo')[0])

  def testRetryAfterNoRequsetResponseTimeout(self):
    api = rest_api._RestApi('scope')

    fut = ndb.Future()
    fut.set_result(test_utils.MockUrlFetchResult(httplib.REQUEST_TIMEOUT,
                                                 None, None))
    ndb.Context.urlfetch = mock.create_autospec(
        ndb.Context.urlfetch,
        return_value=fut)

    with mock.patch('google.appengine.api.urlfetch'
                    '.fetch') as f:
      f.return_value = test_utils.MockUrlFetchResult(httplib.ACCEPTED,
                                                     None, None)
      self.assertEqual(httplib.ACCEPTED, api.do_request('foo')[0])

  def testNoRetryAfterDoRequestUrlFetchTimeout(self):
    retry_params = api_utils.RetryParams(max_retries=0)
    api = rest_api._RestApi('scope', retry_params=retry_params)

    fut = ndb.Future()
    fut.set_exception(urlfetch.DownloadError())
    ndb.Context.urlfetch = mock.create_autospec(
        ndb.Context.urlfetch,
        return_value=fut)
    self.assertRaises(urlfetch.DownloadError, api.do_request, 'foo')

  def testNoRetryAfterDoRequestResponseTimeout(self):
    retry_params = api_utils.RetryParams(max_retries=0)
    api = rest_api._RestApi('scope', retry_params=retry_params)

    fut = ndb.Future()
    fut.set_result(test_utils.MockUrlFetchResult(httplib.REQUEST_TIMEOUT,
                                                 None, None))
    ndb.Context.urlfetch = mock.create_autospec(
        ndb.Context.urlfetch,
        return_value=fut)
    self.assertEqual(httplib.REQUEST_TIMEOUT, api.do_request('foo')[0])


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_runner
# Copyright 2012 Google Inc. All Rights Reserved.

"""Test runner for oss tests."""



import optparse
import sys
import unittest

USAGE = """%prog SDK_PATH LIB_PATH TEST_PATH
Run unit tests for Cloud Storage client library.

SDK_PATH Path to the SDK installation
LIB_PATH Path to Cloud Storage client library (e.g. ../src/)
TEST_PATH Path to package containing test modules (e.g. .)
"""


def main(sdk_path, lib_path, test_path):
  sys.path.insert(0, sdk_path)
  sys.path.insert(0, lib_path)
  import dev_appserver
  dev_appserver.fix_sys_path()
  suite = unittest.TestLoader().discover(test_path, pattern='*_test.py')
  unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
  parser = optparse.OptionParser(USAGE)
  options, args = parser.parse_args()
  if len(args) != 3:
    print 'Error: Exactly 3 arguments required.'
    parser.print_help()
    sys.exit(1)
  SDK_PATH = args[0]
  LIB_PATH = args[1]
  TEST_PATH = args[2]
  main(SDK_PATH, LIB_PATH, TEST_PATH)

########NEW FILE########
__FILENAME__ = flask_login
../flask-login/flask_login.py
########NEW FILE########
__FILENAME__ = flask_mail
../flask-mail/flask_mail.py
########NEW FILE########
__FILENAME__ = gflags
../python-gflags/gflags.py
########NEW FILE########
__FILENAME__ = gflags_validators
../python-gflags/gflags_validators.py
########NEW FILE########
__FILENAME__ = itsdangerous
../itsdangerous/itsdangerous.py
########NEW FILE########
__FILENAME__ = encode
"""multipart/form-data encoding module

This module provides functions that faciliate encoding name/value pairs
as multipart/form-data suitable for a HTTP POST or PUT request.

multipart/form-data is the standard way to upload files over HTTP"""

__all__ = ['gen_boundary', 'encode_and_quote', 'MultipartParam',
        'encode_string', 'encode_file_header', 'get_body_size', 'get_headers',
        'multipart_encode']

try:
    import uuid
    def gen_boundary():
        """Returns a random string to use as the boundary for a message"""
        return uuid.uuid4().hex
except ImportError:
    import random, sha
    def gen_boundary():
        """Returns a random string to use as the boundary for a message"""
        bits = random.getrandbits(160)
        return sha.new(str(bits)).hexdigest()

import urllib, re, os, mimetypes
try:
    from email.header import Header
except ImportError:
    # Python 2.4
    from email.Header import Header

def encode_and_quote(data):
    """If ``data`` is unicode, return urllib.quote_plus(data.encode("utf-8"))
    otherwise return urllib.quote_plus(data)"""
    if data is None:
        return None

    if isinstance(data, unicode):
        data = data.encode("utf-8")
    return urllib.quote_plus(data)

def _strify(s):
    """If s is a unicode string, encode it to UTF-8 and return the results,
    otherwise return str(s), or None if s is None"""
    if s is None:
        return None
    if isinstance(s, unicode):
        return s.encode("utf-8")
    return str(s)

class MultipartParam(object):
    """Represents a single parameter in a multipart/form-data request

    ``name`` is the name of this parameter.

    If ``value`` is set, it must be a string or unicode object to use as the
    data for this parameter.

    If ``filename`` is set, it is what to say that this parameter's filename
    is.  Note that this does not have to be the actual filename any local file.

    If ``filetype`` is set, it is used as the Content-Type for this parameter.
    If unset it defaults to "text/plain; charset=utf8"

    If ``filesize`` is set, it specifies the length of the file ``fileobj``

    If ``fileobj`` is set, it must be a file-like object that supports
    .read().

    Both ``value`` and ``fileobj`` must not be set, doing so will
    raise a ValueError assertion.

    If ``fileobj`` is set, and ``filesize`` is not specified, then
    the file's size will be determined first by stat'ing ``fileobj``'s
    file descriptor, and if that fails, by seeking to the end of the file,
    recording the current position as the size, and then by seeking back to the
    beginning of the file.

    ``cb`` is a callable which will be called from iter_encode with (self,
    current, total), representing the current parameter, current amount
    transferred, and the total size.
    """
    def __init__(self, name, value=None, filename=None, filetype=None,
                        filesize=None, fileobj=None, cb=None):
        self.name = Header(name).encode()
        self.value = _strify(value)
        if filename is None:
            self.filename = None
        else:
            if isinstance(filename, unicode):
                # Encode with XML entities
                self.filename = filename.encode("ascii", "xmlcharrefreplace")
            else:
                self.filename = str(filename)
            self.filename = self.filename.encode("string_escape").\
                    replace('"', '\\"')
        self.filetype = _strify(filetype)

        self.filesize = filesize
        self.fileobj = fileobj
        self.cb = cb

        if self.value is not None and self.fileobj is not None:
            raise ValueError("Only one of value or fileobj may be specified")

        if fileobj is not None and filesize is None:
            # Try and determine the file size
            try:
                self.filesize = os.fstat(fileobj.fileno()).st_size
            except (OSError, AttributeError):
                try:
                    fileobj.seek(0, 2)
                    self.filesize = fileobj.tell()
                    fileobj.seek(0)
                except:
                    raise ValueError("Could not determine filesize")

    def __cmp__(self, other):
        attrs = ['name', 'value', 'filename', 'filetype', 'filesize', 'fileobj']
        myattrs = [getattr(self, a) for a in attrs]
        oattrs = [getattr(other, a) for a in attrs]
        return cmp(myattrs, oattrs)

    def reset(self):
        if self.fileobj is not None:
            self.fileobj.seek(0)
        elif self.value is None:
            raise ValueError("Don't know how to reset this parameter")

    @classmethod
    def from_file(cls, paramname, filename):
        """Returns a new MultipartParam object constructed from the local
        file at ``filename``.

        ``filesize`` is determined by os.path.getsize(``filename``)

        ``filetype`` is determined by mimetypes.guess_type(``filename``)[0]

        ``filename`` is set to os.path.basename(``filename``)
        """

        return cls(paramname, filename=os.path.basename(filename),
                filetype=mimetypes.guess_type(filename)[0],
                filesize=os.path.getsize(filename),
                fileobj=open(filename, "rb"))

    @classmethod
    def from_params(cls, params):
        """Returns a list of MultipartParam objects from a sequence of
        name, value pairs, MultipartParam instances,
        or from a mapping of names to values

        The values may be strings or file objects, or MultipartParam objects.
        MultipartParam object names must match the given names in the
        name,value pairs or mapping, if applicable."""
        if hasattr(params, 'items'):
            params = params.items()

        retval = []
        for item in params:
            if isinstance(item, cls):
                retval.append(item)
                continue
            name, value = item
            if isinstance(value, cls):
                assert value.name == name
                retval.append(value)
                continue
            if hasattr(value, 'read'):
                # Looks like a file object
                filename = getattr(value, 'name', None)
                if filename is not None:
                    filetype = mimetypes.guess_type(filename)[0]
                else:
                    filetype = None

                retval.append(cls(name=name, filename=filename,
                    filetype=filetype, fileobj=value))
            else:
                retval.append(cls(name, value))
        return retval

    def encode_hdr(self, boundary):
        """Returns the header of the encoding of this parameter"""
        boundary = encode_and_quote(boundary)

        headers = ["--%s" % boundary]

        if self.filename:
            disposition = 'form-data; name="%s"; filename="%s"' % (self.name,
                    self.filename)
        else:
            disposition = 'form-data; name="%s"' % self.name

        headers.append("Content-Disposition: %s" % disposition)

        if self.filetype:
            filetype = self.filetype
        else:
            filetype = "text/plain; charset=utf-8"

        headers.append("Content-Type: %s" % filetype)

        headers.append("")
        headers.append("")

        return "\r\n".join(headers)

    def encode(self, boundary):
        """Returns the string encoding of this parameter"""
        if self.value is None:
            value = self.fileobj.read()
        else:
            value = self.value

        if re.search("^--%s$" % re.escape(boundary), value, re.M):
            raise ValueError("boundary found in encoded string")

        return "%s%s\r\n" % (self.encode_hdr(boundary), value)

    def iter_encode(self, boundary, blocksize=4096):
        """Yields the encoding of this parameter
        If self.fileobj is set, then blocks of ``blocksize`` bytes are read and
        yielded."""
        total = self.get_size(boundary)
        current = 0
        if self.value is not None:
            block = self.encode(boundary)
            current += len(block)
            yield block
            if self.cb:
                self.cb(self, current, total)
        else:
            block = self.encode_hdr(boundary)
            current += len(block)
            yield block
            if self.cb:
                self.cb(self, current, total)
            last_block = ""
            encoded_boundary = "--%s" % encode_and_quote(boundary)
            boundary_exp = re.compile("^%s$" % re.escape(encoded_boundary),
                    re.M)
            while True:
                block = self.fileobj.read(blocksize)
                if not block:
                    current += 2
                    yield "\r\n"
                    if self.cb:
                        self.cb(self, current, total)
                    break
                last_block += block
                if boundary_exp.search(last_block):
                    raise ValueError("boundary found in file data")
                last_block = last_block[-len(encoded_boundary)-2:]
                current += len(block)
                yield block
                if self.cb:
                    self.cb(self, current, total)

    def get_size(self, boundary):
        """Returns the size in bytes that this param will be when encoded
        with the given boundary."""
        if self.filesize is not None:
            valuesize = self.filesize
        else:
            valuesize = len(self.value)

        return len(self.encode_hdr(boundary)) + 2 + valuesize

def encode_string(boundary, name, value):
    """Returns ``name`` and ``value`` encoded as a multipart/form-data
    variable.  ``boundary`` is the boundary string used throughout
    a single request to separate variables."""

    return MultipartParam(name, value).encode(boundary)

def encode_file_header(boundary, paramname, filesize, filename=None,
        filetype=None):
    """Returns the leading data for a multipart/form-data field that contains
    file data.

    ``boundary`` is the boundary string used throughout a single request to
    separate variables.

    ``paramname`` is the name of the variable in this request.

    ``filesize`` is the size of the file data.

    ``filename`` if specified is the filename to give to this field.  This
    field is only useful to the server for determining the original filename.

    ``filetype`` if specified is the MIME type of this file.

    The actual file data should be sent after this header has been sent.
    """

    return MultipartParam(paramname, filesize=filesize, filename=filename,
            filetype=filetype).encode_hdr(boundary)

def get_body_size(params, boundary):
    """Returns the number of bytes that the multipart/form-data encoding
    of ``params`` will be."""
    size = sum(p.get_size(boundary) for p in MultipartParam.from_params(params))
    return size + len(boundary) + 6

def get_headers(params, boundary):
    """Returns a dictionary with Content-Type and Content-Length headers
    for the multipart/form-data encoding of ``params``."""
    headers = {}
    boundary = urllib.quote_plus(boundary)
    headers['Content-Type'] = "multipart/form-data; boundary=%s" % boundary
    headers['Content-Length'] = str(get_body_size(params, boundary))
    return headers

class multipart_yielder:
    def __init__(self, params, boundary, cb):
        self.params = params
        self.boundary = boundary
        self.cb = cb

        self.i = 0
        self.p = None
        self.param_iter = None
        self.current = 0
        self.total = get_body_size(params, boundary)

    def __iter__(self):
        return self

    def next(self):
        """generator function to yield multipart/form-data representation
        of parameters"""
        if self.param_iter is not None:
            try:
                block = self.param_iter.next()
                self.current += len(block)
                if self.cb:
                    self.cb(self.p, self.current, self.total)
                return block
            except StopIteration:
                self.p = None
                self.param_iter = None

        if self.i is None:
            raise StopIteration
        elif self.i >= len(self.params):
            self.param_iter = None
            self.p = None
            self.i = None
            block = "--%s--\r\n" % self.boundary
            self.current += len(block)
            if self.cb:
                self.cb(self.p, self.current, self.total)
            return block

        self.p = self.params[self.i]
        self.param_iter = self.p.iter_encode(self.boundary)
        self.i += 1
        return self.next()

    def reset(self):
        self.i = 0
        self.current = 0
        for param in self.params:
            param.reset()

def multipart_encode(params, boundary=None, cb=None):
    """Encode ``params`` as multipart/form-data.

    ``params`` should be a sequence of (name, value) pairs or MultipartParam
    objects, or a mapping of names to values.
    Values are either strings parameter values, or file-like objects to use as
    the parameter value.  The file-like objects must support .read() and either
    .fileno() or both .seek() and .tell().

    If ``boundary`` is set, then it as used as the MIME boundary.  Otherwise
    a randomly generated boundary will be used.  In either case, if the
    boundary string appears in the parameter values a ValueError will be
    raised.

    If ``cb`` is set, it should be a callback which will get called as blocks
    of data are encoded.  It will be called with (param, current, total),
    indicating the current parameter being encoded, the current amount encoded,
    and the total amount to encode.

    Returns a tuple of `datagen`, `headers`, where `datagen` is a
    generator that will yield blocks of data that make up the encoded
    parameters, and `headers` is a dictionary with the assoicated
    Content-Type and Content-Length headers.

    Examples:

    >>> datagen, headers = multipart_encode( [("key", "value1"), ("key", "value2")] )
    >>> s = "".join(datagen)
    >>> assert "value2" in s and "value1" in s

    >>> p = MultipartParam("key", "value2")
    >>> datagen, headers = multipart_encode( [("key", "value1"), p] )
    >>> s = "".join(datagen)
    >>> assert "value2" in s and "value1" in s

    >>> datagen, headers = multipart_encode( {"key": "value1"} )
    >>> s = "".join(datagen)
    >>> assert "value2" not in s and "value1" in s

    """
    if boundary is None:
        boundary = gen_boundary()
    else:
        boundary = urllib.quote_plus(boundary)

    headers = get_headers(params, boundary)
    params = MultipartParam.from_params(params)

    return multipart_yielder(params, boundary, cb), headers

########NEW FILE########
__FILENAME__ = streaminghttp
"""Streaming HTTP uploads module.

This module extends the standard httplib and urllib2 objects so that
iterable objects can be used in the body of HTTP requests.

In most cases all one should have to do is call :func:`register_openers()`
to register the new streaming http handlers which will take priority over
the default handlers, and then you can use iterable objects in the body
of HTTP requests.

**N.B.** You must specify a Content-Length header if using an iterable object
since there is no way to determine in advance the total size that will be
yielded, and there is no way to reset an interator.

Example usage:

>>> from StringIO import StringIO
>>> import urllib2, poster.streaminghttp

>>> opener = poster.streaminghttp.register_openers()

>>> s = "Test file data"
>>> f = StringIO(s)

>>> req = urllib2.Request("http://localhost:5000", f,
...                       {'Content-Length': str(len(s))})
"""

import httplib, urllib2, socket
from httplib import NotConnected

__all__ = ['StreamingHTTPConnection', 'StreamingHTTPRedirectHandler',
        'StreamingHTTPHandler', 'register_openers']

if hasattr(httplib, 'HTTPS'):
    __all__.extend(['StreamingHTTPSHandler', 'StreamingHTTPSConnection'])

class _StreamingHTTPMixin:
    """Mixin class for HTTP and HTTPS connections that implements a streaming
    send method."""
    def send(self, value):
        """Send ``value`` to the server.

        ``value`` can be a string object, a file-like object that supports
        a .read() method, or an iterable object that supports a .next()
        method.
        """
        # Based on python 2.6's httplib.HTTPConnection.send()
        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise NotConnected()

        # send the data to the server. if we get a broken pipe, then close
        # the socket. we want to reconnect when somebody tries to send again.
        #
        # NOTE: we DO propagate the error, though, because we cannot simply
        #       ignore the error... the caller will know if they can retry.
        if self.debuglevel > 0:
            print "send:", repr(value)
        try:
            blocksize = 8192
            if hasattr(value, 'read') :
                if hasattr(value, 'seek'):
                    value.seek(0)
                if self.debuglevel > 0:
                    print "sendIng a read()able"
                data = value.read(blocksize)
                while data:
                    self.sock.sendall(data)
                    data = value.read(blocksize)
            elif hasattr(value, 'next'):
                if hasattr(value, 'reset'):
                    value.reset()
                if self.debuglevel > 0:
                    print "sendIng an iterable"
                for data in value:
                    self.sock.sendall(data)
            else:
                self.sock.sendall(value)
        except socket.error, v:
            if v[0] == 32:      # Broken pipe
                self.close()
            raise

class StreamingHTTPConnection(_StreamingHTTPMixin, httplib.HTTPConnection):
    """Subclass of `httplib.HTTPConnection` that overrides the `send()` method
    to support iterable body objects"""

class StreamingHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    """Subclass of `urllib2.HTTPRedirectHandler` that overrides the
    `redirect_request` method to properly handle redirected POST requests

    This class is required because python 2.5's HTTPRedirectHandler does
    not remove the Content-Type or Content-Length headers when requesting
    the new resource, but the body of the original request is not preserved.
    """

    handler_order = urllib2.HTTPRedirectHandler.handler_order - 1

    # From python2.6 urllib2's HTTPRedirectHandler
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Return a Request or None in response to a redirect.

        This is called by the http_error_30x methods when a
        redirection response is received.  If a redirection should
        take place, return a new Request to allow http_error_30x to
        perform the redirect.  Otherwise, raise HTTPError if no-one
        else should try to handle this url.  Return None if you can't
        but another Handler might.
        """
        m = req.get_method()
        if (code in (301, 302, 303, 307) and m in ("GET", "HEAD")
            or code in (301, 302, 303) and m == "POST"):
            # Strictly (according to RFC 2616), 301 or 302 in response
            # to a POST MUST NOT cause a redirection without confirmation
            # from the user (of urllib2, in this case).  In practice,
            # essentially all clients do redirect in this case, so we
            # do the same.
            # be conciliant with URIs containing a space
            newurl = newurl.replace(' ', '%20')
            newheaders = dict((k, v) for k, v in req.headers.items()
                              if k.lower() not in (
                                  "content-length", "content-type")
                             )
            return urllib2.Request(newurl,
                           headers=newheaders,
                           origin_req_host=req.get_origin_req_host(),
                           unverifiable=True)
        else:
            raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)

class StreamingHTTPHandler(urllib2.HTTPHandler):
    """Subclass of `urllib2.HTTPHandler` that uses
    StreamingHTTPConnection as its http connection class."""

    handler_order = urllib2.HTTPHandler.handler_order - 1

    def http_open(self, req):
        """Open a StreamingHTTPConnection for the given request"""
        return self.do_open(StreamingHTTPConnection, req)

    def http_request(self, req):
        """Handle a HTTP request.  Make sure that Content-Length is specified
        if we're using an interable value"""
        # Make sure that if we're using an iterable object as the request
        # body, that we've also specified Content-Length
        if req.has_data():
            data = req.get_data()
            if hasattr(data, 'read') or hasattr(data, 'next'):
                if not req.has_header('Content-length'):
                    raise ValueError(
                            "No Content-Length specified for iterable body")
        return urllib2.HTTPHandler.do_request_(self, req)

if hasattr(httplib, 'HTTPS'):
    class StreamingHTTPSConnection(_StreamingHTTPMixin,
            httplib.HTTPSConnection):
        """Subclass of `httplib.HTTSConnection` that overrides the `send()`
        method to support iterable body objects"""

    class StreamingHTTPSHandler(urllib2.HTTPSHandler):
        """Subclass of `urllib2.HTTPSHandler` that uses
        StreamingHTTPSConnection as its http connection class."""

        handler_order = urllib2.HTTPSHandler.handler_order - 1

        def https_open(self, req):
            return self.do_open(StreamingHTTPSConnection, req)

        def https_request(self, req):
            # Make sure that if we're using an iterable object as the request
            # body, that we've also specified Content-Length
            if req.has_data():
                data = req.get_data()
                if hasattr(data, 'read') or hasattr(data, 'next'):
                    if not req.has_header('Content-length'):
                        raise ValueError(
                                "No Content-Length specified for iterable body")
            return urllib2.HTTPSHandler.do_request_(self, req)


def get_handlers():
    handlers = [StreamingHTTPHandler, StreamingHTTPRedirectHandler]
    if hasattr(httplib, "HTTPS"):
        handlers.append(StreamingHTTPSHandler)
    return handlers
    
def register_openers():
    """Register the streaming http handlers in the global urllib2 default
    opener object.

    Returns the created OpenerDirector object."""
    opener = urllib2.build_opener(*get_handlers())

    urllib2.install_opener(opener)

    return opener

########NEW FILE########
__FILENAME__ = gflags
#!/usr/bin/env python
#
# Copyright (c) 2002, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ---
# Author: Chad Lester
# Design and style contributions by:
#   Amit Patel, Bogdan Cocosel, Daniel Dulitz, Eric Tiedemann,
#   Eric Veach, Laurence Gonsalves, Matthew Springer
# Code reorganized a bit by Craig Silverstein

"""This module is used to define and parse command line flags.

This module defines a *distributed* flag-definition policy: rather than
an application having to define all flags in or near main(), each python
module defines flags that are useful to it.  When one python module
imports another, it gains access to the other's flags.  (This is
implemented by having all modules share a common, global registry object
containing all the flag information.)

Flags are defined through the use of one of the DEFINE_xxx functions.
The specific function used determines how the flag is parsed, checked,
and optionally type-converted, when it's seen on the command line.


IMPLEMENTATION: DEFINE_* creates a 'Flag' object and registers it with a
'FlagValues' object (typically the global FlagValues FLAGS, defined
here).  The 'FlagValues' object can scan the command line arguments and
pass flag arguments to the corresponding 'Flag' objects for
value-checking and type conversion.  The converted flag values are
available as attributes of the 'FlagValues' object.

Code can access the flag through a FlagValues object, for instance
gflags.FLAGS.myflag.  Typically, the __main__ module passes the command
line arguments to gflags.FLAGS for parsing.

At bottom, this module calls getopt(), so getopt functionality is
supported, including short- and long-style flags, and the use of -- to
terminate flags.

Methods defined by the flag module will throw 'FlagsError' exceptions.
The exception argument will be a human-readable string.


FLAG TYPES: This is a list of the DEFINE_*'s that you can do.  All flags
take a name, default value, help-string, and optional 'short' name
(one-letter name).  Some flags have other arguments, which are described
with the flag.

DEFINE_string: takes any input, and interprets it as a string.

DEFINE_bool or
DEFINE_boolean: typically does not take an argument: say --myflag to
                set FLAGS.myflag to true, or --nomyflag to set
                FLAGS.myflag to false.  Alternately, you can say
                   --myflag=true  or --myflag=t or --myflag=1  or
                   --myflag=false or --myflag=f or --myflag=0

DEFINE_float: takes an input and interprets it as a floating point
              number.  Takes optional args lower_bound and upper_bound;
              if the number specified on the command line is out of
              range, it will raise a FlagError.

DEFINE_integer: takes an input and interprets it as an integer.  Takes
                optional args lower_bound and upper_bound as for floats.

DEFINE_enum: takes a list of strings which represents legal values.  If
             the command-line value is not in this list, raise a flag
             error.  Otherwise, assign to FLAGS.flag as a string.

DEFINE_list: Takes a comma-separated list of strings on the commandline.
             Stores them in a python list object.

DEFINE_spaceseplist: Takes a space-separated list of strings on the
                     commandline.  Stores them in a python list object.
                     Example: --myspacesepflag "foo bar baz"

DEFINE_multistring: The same as DEFINE_string, except the flag can be
                    specified more than once on the commandline.  The
                    result is a python list object (list of strings),
                    even if the flag is only on the command line once.

DEFINE_multi_int: The same as DEFINE_integer, except the flag can be
                  specified more than once on the commandline.  The
                  result is a python list object (list of ints), even if
                  the flag is only on the command line once.


SPECIAL FLAGS: There are a few flags that have special meaning:
   --help          prints a list of all the flags in a human-readable fashion
   --helpshort     prints a list of all key flags (see below).
   --helpxml       prints a list of all flags, in XML format.  DO NOT parse
                   the output of --help and --helpshort.  Instead, parse
                   the output of --helpxml.  For more info, see
                   "OUTPUT FOR --helpxml" below.
   --flagfile=foo  read flags from file foo.
   --undefok=f1,f2 ignore unrecognized option errors for f1,f2.
                   For boolean flags, you should use --undefok=boolflag, and
                   --boolflag and --noboolflag will be accepted.  Do not use
                   --undefok=noboolflag.
   --              as in getopt(), terminates flag-processing


FLAGS VALIDATORS: If your program:
  - requires flag X to be specified
  - needs flag Y to match a regular expression
  - or requires any more general constraint to be satisfied
then validators are for you!

Each validator represents a constraint over one flag, which is enforced
starting from the initial parsing of the flags and until the program
terminates.

Also, lower_bound and upper_bound for numerical flags are enforced using flag
validators.

Howto:
If you want to enforce a constraint over one flag, use

gflags.RegisterValidator(flag_name,
                        checker,
                        message='Flag validation failed',
                        flag_values=FLAGS)

After flag values are initially parsed, and after any change to the specified
flag, method checker(flag_value) will be executed. If constraint is not
satisfied, an IllegalFlagValue exception will be raised. See
RegisterValidator's docstring for a detailed explanation on how to construct
your own checker.


EXAMPLE USAGE:

FLAGS = gflags.FLAGS

gflags.DEFINE_integer('my_version', 0, 'Version number.')
gflags.DEFINE_string('filename', None, 'Input file name', short_name='f')

gflags.RegisterValidator('my_version',
                        lambda value: value % 2 == 0,
                        message='--my_version must be divisible by 2')
gflags.MarkFlagAsRequired('filename')


NOTE ON --flagfile:

Flags may be loaded from text files in addition to being specified on
the commandline.

Any flags you don't feel like typing, throw them in a file, one flag per
line, for instance:
   --myflag=myvalue
   --nomyboolean_flag
You then specify your file with the special flag '--flagfile=somefile'.
You CAN recursively nest flagfile= tokens OR use multiple files on the
command line.  Lines beginning with a single hash '#' or a double slash
'//' are comments in your flagfile.

Any flagfile=<file> will be interpreted as having a relative path from
the current working directory rather than from the place the file was
included from:
   myPythonScript.py --flagfile=config/somefile.cfg

If somefile.cfg includes further --flagfile= directives, these will be
referenced relative to the original CWD, not from the directory the
including flagfile was found in!

The caveat applies to people who are including a series of nested files
in a different dir than they are executing out of.  Relative path names
are always from CWD, not from the directory of the parent include
flagfile. We do now support '~' expanded directory names.

Absolute path names ALWAYS work!


EXAMPLE USAGE:


  FLAGS = gflags.FLAGS

  # Flag names are globally defined!  So in general, we need to be
  # careful to pick names that are unlikely to be used by other libraries.
  # If there is a conflict, we'll get an error at import time.
  gflags.DEFINE_string('name', 'Mr. President', 'your name')
  gflags.DEFINE_integer('age', None, 'your age in years', lower_bound=0)
  gflags.DEFINE_boolean('debug', False, 'produces debugging output')
  gflags.DEFINE_enum('gender', 'male', ['male', 'female'], 'your gender')

  def main(argv):
    try:
      argv = FLAGS(argv)  # parse flags
    except gflags.FlagsError, e:
      print '%s\\nUsage: %s ARGS\\n%s' % (e, sys.argv[0], FLAGS)
      sys.exit(1)
    if FLAGS.debug: print 'non-flag arguments:', argv
    print 'Happy Birthday', FLAGS.name
    if FLAGS.age is not None:
      print 'You are a %d year old %s' % (FLAGS.age, FLAGS.gender)

  if __name__ == '__main__':
    main(sys.argv)


KEY FLAGS:

As we already explained, each module gains access to all flags defined
by all the other modules it transitively imports.  In the case of
non-trivial scripts, this means a lot of flags ...  For documentation
purposes, it is good to identify the flags that are key (i.e., really
important) to a module.  Clearly, the concept of "key flag" is a
subjective one.  When trying to determine whether a flag is key to a
module or not, assume that you are trying to explain your module to a
potential user: which flags would you really like to mention first?

We'll describe shortly how to declare which flags are key to a module.
For the moment, assume we know the set of key flags for each module.
Then, if you use the app.py module, you can use the --helpshort flag to
print only the help for the flags that are key to the main module, in a
human-readable format.

NOTE: If you need to parse the flag help, do NOT use the output of
--help / --helpshort.  That output is meant for human consumption, and
may be changed in the future.  Instead, use --helpxml; flags that are
key for the main module are marked there with a <key>yes</key> element.

The set of key flags for a module M is composed of:

1. Flags defined by module M by calling a DEFINE_* function.

2. Flags that module M explictly declares as key by using the function

     DECLARE_key_flag(<flag_name>)

3. Key flags of other modules that M specifies by using the function

     ADOPT_module_key_flags(<other_module>)

   This is a "bulk" declaration of key flags: each flag that is key for
   <other_module> becomes key for the current module too.

Notice that if you do not use the functions described at points 2 and 3
above, then --helpshort prints information only about the flags defined
by the main module of our script.  In many cases, this behavior is good
enough.  But if you move part of the main module code (together with the
related flags) into a different module, then it is nice to use
DECLARE_key_flag / ADOPT_module_key_flags and make sure --helpshort
lists all relevant flags (otherwise, your code refactoring may confuse
your users).

Note: each of DECLARE_key_flag / ADOPT_module_key_flags has its own
pluses and minuses: DECLARE_key_flag is more targeted and may lead a
more focused --helpshort documentation.  ADOPT_module_key_flags is good
for cases when an entire module is considered key to the current script.
Also, it does not require updates to client scripts when a new flag is
added to the module.


EXAMPLE USAGE 2 (WITH KEY FLAGS):

Consider an application that contains the following three files (two
auxiliary modules and a main module)

File libfoo.py:

  import gflags

  gflags.DEFINE_integer('num_replicas', 3, 'Number of replicas to start')
  gflags.DEFINE_boolean('rpc2', True, 'Turn on the usage of RPC2.')

  ... some code ...

File libbar.py:

  import gflags

  gflags.DEFINE_string('bar_gfs_path', '/gfs/path',
                      'Path to the GFS files for libbar.')
  gflags.DEFINE_string('email_for_bar_errors', 'bar-team@google.com',
                      'Email address for bug reports about module libbar.')
  gflags.DEFINE_boolean('bar_risky_hack', False,
                       'Turn on an experimental and buggy optimization.')

  ... some code ...

File myscript.py:

  import gflags
  import libfoo
  import libbar

  gflags.DEFINE_integer('num_iterations', 0, 'Number of iterations.')

  # Declare that all flags that are key for libfoo are
  # key for this module too.
  gflags.ADOPT_module_key_flags(libfoo)

  # Declare that the flag --bar_gfs_path (defined in libbar) is key
  # for this module.
  gflags.DECLARE_key_flag('bar_gfs_path')

  ... some code ...

When myscript is invoked with the flag --helpshort, the resulted help
message lists information about all the key flags for myscript:
--num_iterations, --num_replicas, --rpc2, and --bar_gfs_path.

Of course, myscript uses all the flags declared by it (in this case,
just --num_replicas) or by any of the modules it transitively imports
(e.g., the modules libfoo, libbar).  E.g., it can access the value of
FLAGS.bar_risky_hack, even if --bar_risky_hack is not declared as a key
flag for myscript.


OUTPUT FOR --helpxml:

The --helpxml flag generates output with the following structure:

<?xml version="1.0"?>
<AllFlags>
  <program>PROGRAM_BASENAME</program>
  <usage>MAIN_MODULE_DOCSTRING</usage>
  (<flag>
    [<key>yes</key>]
    <file>DECLARING_MODULE</file>
    <name>FLAG_NAME</name>
    <meaning>FLAG_HELP_MESSAGE</meaning>
    <default>DEFAULT_FLAG_VALUE</default>
    <current>CURRENT_FLAG_VALUE</current>
    <type>FLAG_TYPE</type>
    [OPTIONAL_ELEMENTS]
  </flag>)*
</AllFlags>

Notes:

1. The output is intentionally similar to the output generated by the
C++ command-line flag library.  The few differences are due to the
Python flags that do not have a C++ equivalent (at least not yet),
e.g., DEFINE_list.

2. New XML elements may be added in the future.

3. DEFAULT_FLAG_VALUE is in serialized form, i.e., the string you can
pass for this flag on the command-line.  E.g., for a flag defined
using DEFINE_list, this field may be foo,bar, not ['foo', 'bar'].

4. CURRENT_FLAG_VALUE is produced using str().  This means that the
string 'false' will be represented in the same way as the boolean
False.  Using repr() would have removed this ambiguity and simplified
parsing, but would have broken the compatibility with the C++
command-line flags.

5. OPTIONAL_ELEMENTS describe elements relevant for certain kinds of
flags: lower_bound, upper_bound (for flags that specify bounds),
enum_value (for enum flags), list_separator (for flags that consist of
a list of values, separated by a special token).

6. We do not provide any example here: please use --helpxml instead.

This module requires at least python 2.2.1 to run.
"""

import cgi
import getopt
import os
import re
import string
import struct
import sys
# pylint: disable-msg=C6204
try:
  import fcntl
except ImportError:
  fcntl = None
try:
  # Importing termios will fail on non-unix platforms.
  import termios
except ImportError:
  termios = None

import gflags_validators
# pylint: enable-msg=C6204


# Are we running under pychecker?
_RUNNING_PYCHECKER = 'pychecker.python' in sys.modules


def _GetCallingModuleObjectAndName():
  """Returns the module that's calling into this module.

  We generally use this function to get the name of the module calling a
  DEFINE_foo... function.
  """
  # Walk down the stack to find the first globals dict that's not ours.
  for depth in range(1, sys.getrecursionlimit()):
    if not sys._getframe(depth).f_globals is globals():
      globals_for_frame = sys._getframe(depth).f_globals
      module, module_name = _GetModuleObjectAndName(globals_for_frame)
      if module_name is not None:
        return module, module_name
  raise AssertionError("No module was found")


def _GetCallingModule():
  """Returns the name of the module that's calling into this module."""
  return _GetCallingModuleObjectAndName()[1]


def _GetThisModuleObjectAndName():
  """Returns: (module object, module name) for this module."""
  return _GetModuleObjectAndName(globals())


# module exceptions:
class FlagsError(Exception):
  """The base class for all flags errors."""
  pass


class DuplicateFlag(FlagsError):
  """Raised if there is a flag naming conflict."""
  pass

class CantOpenFlagFileError(FlagsError):
  """Raised if flagfile fails to open: doesn't exist, wrong permissions, etc."""
  pass


class DuplicateFlagCannotPropagateNoneToSwig(DuplicateFlag):
  """Special case of DuplicateFlag -- SWIG flag value can't be set to None.

  This can be raised when a duplicate flag is created. Even if allow_override is
  True, we still abort if the new value is None, because it's currently
  impossible to pass None default value back to SWIG. See FlagValues.SetDefault
  for details.
  """
  pass


class DuplicateFlagError(DuplicateFlag):
  """A DuplicateFlag whose message cites the conflicting definitions.

  A DuplicateFlagError conveys more information than a DuplicateFlag,
  namely the modules where the conflicting definitions occur. This
  class was created to avoid breaking external modules which depend on
  the existing DuplicateFlags interface.
  """

  def __init__(self, flagname, flag_values, other_flag_values=None):
    """Create a DuplicateFlagError.

    Args:
      flagname: Name of the flag being redefined.
      flag_values: FlagValues object containing the first definition of
          flagname.
      other_flag_values: If this argument is not None, it should be the
          FlagValues object where the second definition of flagname occurs.
          If it is None, we assume that we're being called when attempting
          to create the flag a second time, and we use the module calling
          this one as the source of the second definition.
    """
    self.flagname = flagname
    first_module = flag_values.FindModuleDefiningFlag(
        flagname, default='<unknown>')
    if other_flag_values is None:
      second_module = _GetCallingModule()
    else:
      second_module = other_flag_values.FindModuleDefiningFlag(
          flagname, default='<unknown>')
    msg = "The flag '%s' is defined twice. First from %s, Second from %s" % (
        self.flagname, first_module, second_module)
    DuplicateFlag.__init__(self, msg)


class IllegalFlagValue(FlagsError):
  """The flag command line argument is illegal."""
  pass


class UnrecognizedFlag(FlagsError):
  """Raised if a flag is unrecognized."""
  pass


# An UnrecognizedFlagError conveys more information than an UnrecognizedFlag.
# Since there are external modules that create DuplicateFlags, the interface to
# DuplicateFlag shouldn't change.  The flagvalue will be assigned the full value
# of the flag and its argument, if any, allowing handling of unrecognized flags
# in an exception handler.
# If flagvalue is the empty string, then this exception is an due to a
# reference to a flag that was not already defined.
class UnrecognizedFlagError(UnrecognizedFlag):
  def __init__(self, flagname, flagvalue=''):
    self.flagname = flagname
    self.flagvalue = flagvalue
    UnrecognizedFlag.__init__(
        self, "Unknown command line flag '%s'" % flagname)

# Global variable used by expvar
_exported_flags = {}
_help_width = 80  # width of help output


def GetHelpWidth():
  """Returns: an integer, the width of help lines that is used in TextWrap."""
  if (not sys.stdout.isatty()) or (termios is None) or (fcntl is None):
    return _help_width
  try:
    data = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, '1234')
    columns = struct.unpack('hh', data)[1]
    # Emacs mode returns 0.
    # Here we assume that any value below 40 is unreasonable
    if columns >= 40:
      return columns
    # Returning an int as default is fine, int(int) just return the int.
    return int(os.getenv('COLUMNS', _help_width))

  except (TypeError, IOError, struct.error):
    return _help_width


def CutCommonSpacePrefix(text):
  """Removes a common space prefix from the lines of a multiline text.

  If the first line does not start with a space, it is left as it is and
  only in the remaining lines a common space prefix is being searched
  for. That means the first line will stay untouched. This is especially
  useful to turn doc strings into help texts. This is because some
  people prefer to have the doc comment start already after the
  apostrophe and then align the following lines while others have the
  apostrophes on a separate line.

  The function also drops trailing empty lines and ignores empty lines
  following the initial content line while calculating the initial
  common whitespace.

  Args:
    text: text to work on

  Returns:
    the resulting text
  """
  text_lines = text.splitlines()
  # Drop trailing empty lines
  while text_lines and not text_lines[-1]:
    text_lines = text_lines[:-1]
  if text_lines:
    # We got some content, is the first line starting with a space?
    if text_lines[0] and text_lines[0][0].isspace():
      text_first_line = []
    else:
      text_first_line = [text_lines.pop(0)]
    # Calculate length of common leading whitespace (only over content lines)
    common_prefix = os.path.commonprefix([line for line in text_lines if line])
    space_prefix_len = len(common_prefix) - len(common_prefix.lstrip())
    # If we have a common space prefix, drop it from all lines
    if space_prefix_len:
      for index in xrange(len(text_lines)):
        if text_lines[index]:
          text_lines[index] = text_lines[index][space_prefix_len:]
    return '\n'.join(text_first_line + text_lines)
  return ''


def TextWrap(text, length=None, indent='', firstline_indent=None, tabs='    '):
  """Wraps a given text to a maximum line length and returns it.

  We turn lines that only contain whitespace into empty lines.  We keep
  new lines and tabs (e.g., we do not treat tabs as spaces).

  Args:
    text:             text to wrap
    length:           maximum length of a line, includes indentation
                      if this is None then use GetHelpWidth()
    indent:           indent for all but first line
    firstline_indent: indent for first line; if None, fall back to indent
    tabs:             replacement for tabs

  Returns:
    wrapped text

  Raises:
    FlagsError: if indent not shorter than length
    FlagsError: if firstline_indent not shorter than length
  """
  # Get defaults where callee used None
  if length is None:
    length = GetHelpWidth()
  if indent is None:
    indent = ''
  if len(indent) >= length:
    raise FlagsError('Indent must be shorter than length')
  # In line we will be holding the current line which is to be started
  # with indent (or firstline_indent if available) and then appended
  # with words.
  if firstline_indent is None:
    firstline_indent = ''
    line = indent
  else:
    line = firstline_indent
    if len(firstline_indent) >= length:
      raise FlagsError('First line indent must be shorter than length')

  # If the callee does not care about tabs we simply convert them to
  # spaces If callee wanted tabs to be single space then we do that
  # already here.
  if not tabs or tabs == ' ':
    text = text.replace('\t', ' ')
  else:
    tabs_are_whitespace = not tabs.strip()

  line_regex = re.compile('([ ]*)(\t*)([^ \t]+)', re.MULTILINE)

  # Split the text into lines and the lines with the regex above. The
  # resulting lines are collected in result[]. For each split we get the
  # spaces, the tabs and the next non white space (e.g. next word).
  result = []
  for text_line in text.splitlines():
    # Store result length so we can find out whether processing the next
    # line gave any new content
    old_result_len = len(result)
    # Process next line with line_regex. For optimization we do an rstrip().
    # - process tabs (changes either line or word, see below)
    # - process word (first try to squeeze on line, then wrap or force wrap)
    # Spaces found on the line are ignored, they get added while wrapping as
    # needed.
    for spaces, current_tabs, word in line_regex.findall(text_line.rstrip()):
      # If tabs weren't converted to spaces, handle them now
      if current_tabs:
        # If the last thing we added was a space anyway then drop
        # it. But let's not get rid of the indentation.
        if (((result and line != indent) or
             (not result and line != firstline_indent)) and line[-1] == ' '):
          line = line[:-1]
        # Add the tabs, if that means adding whitespace, just add it at
        # the line, the rstrip() code while shorten the line down if
        # necessary
        if tabs_are_whitespace:
          line += tabs * len(current_tabs)
        else:
          # if not all tab replacement is whitespace we prepend it to the word
          word = tabs * len(current_tabs) + word
      # Handle the case where word cannot be squeezed onto current last line
      if len(line) + len(word) > length and len(indent) + len(word) <= length:
        result.append(line.rstrip())
        line = indent + word
        word = ''
        # No space left on line or can we append a space?
        if len(line) + 1 >= length:
          result.append(line.rstrip())
          line = indent
        else:
          line += ' '
      # Add word and shorten it up to allowed line length. Restart next
      # line with indent and repeat, or add a space if we're done (word
      # finished) This deals with words that cannot fit on one line
      # (e.g. indent + word longer than allowed line length).
      while len(line) + len(word) >= length:
        line += word
        result.append(line[:length])
        word = line[length:]
        line = indent
      # Default case, simply append the word and a space
      if word:
        line += word + ' '
    # End of input line. If we have content we finish the line. If the
    # current line is just the indent but we had content in during this
    # original line then we need to add an empty line.
    if (result and line != indent) or (not result and line != firstline_indent):
      result.append(line.rstrip())
    elif len(result) == old_result_len:
      result.append('')
    line = indent

  return '\n'.join(result)


def DocToHelp(doc):
  """Takes a __doc__ string and reformats it as help."""

  # Get rid of starting and ending white space. Using lstrip() or even
  # strip() could drop more than maximum of first line and right space
  # of last line.
  doc = doc.strip()

  # Get rid of all empty lines
  whitespace_only_line = re.compile('^[ \t]+$', re.M)
  doc = whitespace_only_line.sub('', doc)

  # Cut out common space at line beginnings
  doc = CutCommonSpacePrefix(doc)

  # Just like this module's comment, comments tend to be aligned somehow.
  # In other words they all start with the same amount of white space
  # 1) keep double new lines
  # 2) keep ws after new lines if not empty line
  # 3) all other new lines shall be changed to a space
  # Solution: Match new lines between non white space and replace with space.
  doc = re.sub('(?<=\S)\n(?=\S)', ' ', doc, re.M)

  return doc


def _GetModuleObjectAndName(globals_dict):
  """Returns the module that defines a global environment, and its name.

  Args:
    globals_dict: A dictionary that should correspond to an environment
      providing the values of the globals.

  Returns:
    A pair consisting of (1) module object and (2) module name (a
    string).  Returns (None, None) if the module could not be
    identified.
  """
  # The use of .items() (instead of .iteritems()) is NOT a mistake: if
  # a parallel thread imports a module while we iterate over
  # .iteritems() (not nice, but possible), we get a RuntimeError ...
  # Hence, we use the slightly slower but safer .items().
  for name, module in sys.modules.items():
    if getattr(module, '__dict__', None) is globals_dict:
      if name == '__main__':
        # Pick a more informative name for the main module.
        name = sys.argv[0]
      return (module, name)
  return (None, None)


def _GetMainModule():
  """Returns: string, name of the module from which execution started."""
  # First, try to use the same logic used by _GetCallingModuleObjectAndName(),
  # i.e., call _GetModuleObjectAndName().  For that we first need to
  # find the dictionary that the main module uses to store the
  # globals.
  #
  # That's (normally) the same dictionary object that the deepest
  # (oldest) stack frame is using for globals.
  deepest_frame = sys._getframe(0)
  while deepest_frame.f_back is not None:
    deepest_frame = deepest_frame.f_back
  globals_for_main_module = deepest_frame.f_globals
  main_module_name = _GetModuleObjectAndName(globals_for_main_module)[1]
  # The above strategy fails in some cases (e.g., tools that compute
  # code coverage by redefining, among other things, the main module).
  # If so, just use sys.argv[0].  We can probably always do this, but
  # it's safest to try to use the same logic as _GetCallingModuleObjectAndName()
  if main_module_name is None:
    main_module_name = sys.argv[0]
  return main_module_name


class FlagValues:
  """Registry of 'Flag' objects.

  A 'FlagValues' can then scan command line arguments, passing flag
  arguments through to the 'Flag' objects that it owns.  It also
  provides easy access to the flag values.  Typically only one
  'FlagValues' object is needed by an application: gflags.FLAGS

  This class is heavily overloaded:

  'Flag' objects are registered via __setitem__:
       FLAGS['longname'] = x   # register a new flag

  The .value attribute of the registered 'Flag' objects can be accessed
  as attributes of this 'FlagValues' object, through __getattr__.  Both
  the long and short name of the original 'Flag' objects can be used to
  access its value:
       FLAGS.longname          # parsed flag value
       FLAGS.x                 # parsed flag value (short name)

  Command line arguments are scanned and passed to the registered 'Flag'
  objects through the __call__ method.  Unparsed arguments, including
  argv[0] (e.g. the program name) are returned.
       argv = FLAGS(sys.argv)  # scan command line arguments

  The original registered Flag objects can be retrieved through the use
  of the dictionary-like operator, __getitem__:
       x = FLAGS['longname']   # access the registered Flag object

  The str() operator of a 'FlagValues' object provides help for all of
  the registered 'Flag' objects.
  """

  def __init__(self):
    # Since everything in this class is so heavily overloaded, the only
    # way of defining and using fields is to access __dict__ directly.

    # Dictionary: flag name (string) -> Flag object.
    self.__dict__['__flags'] = {}
    # Dictionary: module name (string) -> list of Flag objects that are defined
    # by that module.
    self.__dict__['__flags_by_module'] = {}
    # Dictionary: module id (int) -> list of Flag objects that are defined by
    # that module.
    self.__dict__['__flags_by_module_id'] = {}
    # Dictionary: module name (string) -> list of Flag objects that are
    # key for that module.
    self.__dict__['__key_flags_by_module'] = {}

    # Set if we should use new style gnu_getopt rather than getopt when parsing
    # the args.  Only possible with Python 2.3+
    self.UseGnuGetOpt(False)

  def UseGnuGetOpt(self, use_gnu_getopt=True):
    """Use GNU-style scanning. Allows mixing of flag and non-flag arguments.

    See http://docs.python.org/library/getopt.html#getopt.gnu_getopt

    Args:
      use_gnu_getopt: wether or not to use GNU style scanning.
    """
    self.__dict__['__use_gnu_getopt'] = use_gnu_getopt

  def IsGnuGetOpt(self):
    return self.__dict__['__use_gnu_getopt']

  def FlagDict(self):
    return self.__dict__['__flags']

  def FlagsByModuleDict(self):
    """Returns the dictionary of module_name -> list of defined flags.

    Returns:
      A dictionary.  Its keys are module names (strings).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__flags_by_module']

  def FlagsByModuleIdDict(self):
    """Returns the dictionary of module_id -> list of defined flags.

    Returns:
      A dictionary.  Its keys are module IDs (ints).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__flags_by_module_id']

  def KeyFlagsByModuleDict(self):
    """Returns the dictionary of module_name -> list of key flags.

    Returns:
      A dictionary.  Its keys are module names (strings).  Its values
      are lists of Flag objects.
    """
    return self.__dict__['__key_flags_by_module']

  def _RegisterFlagByModule(self, module_name, flag):
    """Records the module that defines a specific flag.

    We keep track of which flag is defined by which module so that we
    can later sort the flags by module.

    Args:
      module_name: A string, the name of a Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    flags_by_module = self.FlagsByModuleDict()
    flags_by_module.setdefault(module_name, []).append(flag)

  def _RegisterFlagByModuleId(self, module_id, flag):
    """Records the module that defines a specific flag.

    Args:
      module_id: An int, the ID of the Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    flags_by_module_id = self.FlagsByModuleIdDict()
    flags_by_module_id.setdefault(module_id, []).append(flag)

  def _RegisterKeyFlagForModule(self, module_name, flag):
    """Specifies that a flag is a key flag for a module.

    Args:
      module_name: A string, the name of a Python module.
      flag: A Flag object, a flag that is key to the module.
    """
    key_flags_by_module = self.KeyFlagsByModuleDict()
    # The list of key flags for the module named module_name.
    key_flags = key_flags_by_module.setdefault(module_name, [])
    # Add flag, but avoid duplicates.
    if flag not in key_flags:
      key_flags.append(flag)

  def _GetFlagsDefinedByModule(self, module):
    """Returns the list of flags defined by a module.

    Args:
      module: A module object or a module name (a string).

    Returns:
      A new list of Flag objects.  Caller may update this list as he
      wishes: none of those changes will affect the internals of this
      FlagValue object.
    """
    if not isinstance(module, str):
      module = module.__name__

    return list(self.FlagsByModuleDict().get(module, []))

  def _GetKeyFlagsForModule(self, module):
    """Returns the list of key flags for a module.

    Args:
      module: A module object or a module name (a string)

    Returns:
      A new list of Flag objects.  Caller may update this list as he
      wishes: none of those changes will affect the internals of this
      FlagValue object.
    """
    if not isinstance(module, str):
      module = module.__name__

    # Any flag is a key flag for the module that defined it.  NOTE:
    # key_flags is a fresh list: we can update it without affecting the
    # internals of this FlagValues object.
    key_flags = self._GetFlagsDefinedByModule(module)

    # Take into account flags explicitly declared as key for a module.
    for flag in self.KeyFlagsByModuleDict().get(module, []):
      if flag not in key_flags:
        key_flags.append(flag)
    return key_flags

  def FindModuleDefiningFlag(self, flagname, default=None):
    """Return the name of the module defining this flag, or default.

    Args:
      flagname: Name of the flag to lookup.
      default: Value to return if flagname is not defined. Defaults
          to None.

    Returns:
      The name of the module which registered the flag with this name.
      If no such module exists (i.e. no flag with this name exists),
      we return default.
    """
    for module, flags in self.FlagsByModuleDict().iteritems():
      for flag in flags:
        if flag.name == flagname or flag.short_name == flagname:
          return module
    return default

  def FindModuleIdDefiningFlag(self, flagname, default=None):
    """Return the ID of the module defining this flag, or default.

    Args:
      flagname: Name of the flag to lookup.
      default: Value to return if flagname is not defined. Defaults
          to None.

    Returns:
      The ID of the module which registered the flag with this name.
      If no such module exists (i.e. no flag with this name exists),
      we return default.
    """
    for module_id, flags in self.FlagsByModuleIdDict().iteritems():
      for flag in flags:
        if flag.name == flagname or flag.short_name == flagname:
          return module_id
    return default

  def AppendFlagValues(self, flag_values):
    """Appends flags registered in another FlagValues instance.

    Args:
      flag_values: registry to copy from
    """
    for flag_name, flag in flag_values.FlagDict().iteritems():
      # Each flags with shortname appears here twice (once under its
      # normal name, and again with its short name).  To prevent
      # problems (DuplicateFlagError) with double flag registration, we
      # perform a check to make sure that the entry we're looking at is
      # for its normal name.
      if flag_name == flag.name:
        try:
          self[flag_name] = flag
        except DuplicateFlagError:
          raise DuplicateFlagError(flag_name, self,
                                   other_flag_values=flag_values)

  def RemoveFlagValues(self, flag_values):
    """Remove flags that were previously appended from another FlagValues.

    Args:
      flag_values: registry containing flags to remove.
    """
    for flag_name in flag_values.FlagDict():
      self.__delattr__(flag_name)

  def __setitem__(self, name, flag):
    """Registers a new flag variable."""
    fl = self.FlagDict()
    if not isinstance(flag, Flag):
      raise IllegalFlagValue(flag)
    if not isinstance(name, type("")):
      raise FlagsError("Flag name must be a string")
    if len(name) == 0:
      raise FlagsError("Flag name cannot be empty")
    # If running under pychecker, duplicate keys are likely to be
    # defined.  Disable check for duplicate keys when pycheck'ing.
    if (name in fl and not flag.allow_override and
        not fl[name].allow_override and not _RUNNING_PYCHECKER):
      module, module_name = _GetCallingModuleObjectAndName()
      if (self.FindModuleDefiningFlag(name) == module_name and
          id(module) != self.FindModuleIdDefiningFlag(name)):
        # If the flag has already been defined by a module with the same name,
        # but a different ID, we can stop here because it indicates that the
        # module is simply being imported a subsequent time.
        return
      raise DuplicateFlagError(name, self)
    short_name = flag.short_name
    if short_name is not None:
      if (short_name in fl and not flag.allow_override and
          not fl[short_name].allow_override and not _RUNNING_PYCHECKER):
        raise DuplicateFlagError(short_name, self)
      fl[short_name] = flag
    fl[name] = flag
    global _exported_flags
    _exported_flags[name] = flag

  def __getitem__(self, name):
    """Retrieves the Flag object for the flag --name."""
    return self.FlagDict()[name]

  def __getattr__(self, name):
    """Retrieves the 'value' attribute of the flag --name."""
    fl = self.FlagDict()
    if name not in fl:
      raise AttributeError(name)
    return fl[name].value

  def __setattr__(self, name, value):
    """Sets the 'value' attribute of the flag --name."""
    fl = self.FlagDict()
    fl[name].value = value
    self._AssertValidators(fl[name].validators)
    return value

  def _AssertAllValidators(self):
    all_validators = set()
    for flag in self.FlagDict().itervalues():
      for validator in flag.validators:
        all_validators.add(validator)
    self._AssertValidators(all_validators)

  def _AssertValidators(self, validators):
    """Assert if all validators in the list are satisfied.

    Asserts validators in the order they were created.
    Args:
      validators: Iterable(gflags_validators.Validator), validators to be
        verified
    Raises:
      AttributeError: if validators work with a non-existing flag.
      IllegalFlagValue: if validation fails for at least one validator
    """
    for validator in sorted(
        validators, key=lambda validator: validator.insertion_index):
      try:
        validator.Verify(self)
      except gflags_validators.Error, e:
        message = validator.PrintFlagsWithValues(self)
        raise IllegalFlagValue('%s: %s' % (message, str(e)))

  def _FlagIsRegistered(self, flag_obj):
    """Checks whether a Flag object is registered under some name.

    Note: this is non trivial: in addition to its normal name, a flag
    may have a short name too.  In self.FlagDict(), both the normal and
    the short name are mapped to the same flag object.  E.g., calling
    only "del FLAGS.short_name" is not unregistering the corresponding
    Flag object (it is still registered under the longer name).

    Args:
      flag_obj: A Flag object.

    Returns:
      A boolean: True iff flag_obj is registered under some name.
    """
    flag_dict = self.FlagDict()
    # Check whether flag_obj is registered under its long name.
    name = flag_obj.name
    if flag_dict.get(name, None) == flag_obj:
      return True
    # Check whether flag_obj is registered under its short name.
    short_name = flag_obj.short_name
    if (short_name is not None and
        flag_dict.get(short_name, None) == flag_obj):
      return True
    # The flag cannot be registered under any other name, so we do not
    # need to do a full search through the values of self.FlagDict().
    return False

  def __delattr__(self, flag_name):
    """Deletes a previously-defined flag from a flag object.

    This method makes sure we can delete a flag by using

      del flag_values_object.<flag_name>

    E.g.,

      gflags.DEFINE_integer('foo', 1, 'Integer flag.')
      del gflags.FLAGS.foo

    Args:
      flag_name: A string, the name of the flag to be deleted.

    Raises:
      AttributeError: When there is no registered flag named flag_name.
    """
    fl = self.FlagDict()
    if flag_name not in fl:
      raise AttributeError(flag_name)

    flag_obj = fl[flag_name]
    del fl[flag_name]

    if not self._FlagIsRegistered(flag_obj):
      # If the Flag object indicated by flag_name is no longer
      # registered (please see the docstring of _FlagIsRegistered), then
      # we delete the occurrences of the flag object in all our internal
      # dictionaries.
      self.__RemoveFlagFromDictByModule(self.FlagsByModuleDict(), flag_obj)
      self.__RemoveFlagFromDictByModule(self.FlagsByModuleIdDict(), flag_obj)
      self.__RemoveFlagFromDictByModule(self.KeyFlagsByModuleDict(), flag_obj)

  def __RemoveFlagFromDictByModule(self, flags_by_module_dict, flag_obj):
    """Removes a flag object from a module -> list of flags dictionary.

    Args:
      flags_by_module_dict: A dictionary that maps module names to lists of
        flags.
      flag_obj: A flag object.
    """
    for unused_module, flags_in_module in flags_by_module_dict.iteritems():
      # while (as opposed to if) takes care of multiple occurrences of a
      # flag in the list for the same module.
      while flag_obj in flags_in_module:
        flags_in_module.remove(flag_obj)

  def SetDefault(self, name, value):
    """Changes the default value of the named flag object."""
    fl = self.FlagDict()
    if name not in fl:
      raise AttributeError(name)
    fl[name].SetDefault(value)
    self._AssertValidators(fl[name].validators)

  def __contains__(self, name):
    """Returns True if name is a value (flag) in the dict."""
    return name in self.FlagDict()

  has_key = __contains__  # a synonym for __contains__()

  def __iter__(self):
    return iter(self.FlagDict())

  def __call__(self, argv):
    """Parses flags from argv; stores parsed flags into this FlagValues object.

    All unparsed arguments are returned.  Flags are parsed using the GNU
    Program Argument Syntax Conventions, using getopt:

    http://www.gnu.org/software/libc/manual/html_mono/libc.html#Getopt

    Args:
       argv: argument list. Can be of any type that may be converted to a list.

    Returns:
       The list of arguments not parsed as options, including argv[0]

    Raises:
       FlagsError: on any parsing error
    """
    # Support any sequence type that can be converted to a list
    argv = list(argv)

    shortopts = ""
    longopts = []

    fl = self.FlagDict()

    # This pre parses the argv list for --flagfile=<> options.
    argv = argv[:1] + self.ReadFlagsFromFiles(argv[1:], force_gnu=False)

    # Correct the argv to support the google style of passing boolean
    # parameters.  Boolean parameters may be passed by using --mybool,
    # --nomybool, --mybool=(true|false|1|0).  getopt does not support
    # having options that may or may not have a parameter.  We replace
    # instances of the short form --mybool and --nomybool with their
    # full forms: --mybool=(true|false).
    original_argv = list(argv)  # list() makes a copy
    shortest_matches = None
    for name, flag in fl.items():
      if not flag.boolean:
        continue
      if shortest_matches is None:
        # Determine the smallest allowable prefix for all flag names
        shortest_matches = self.ShortestUniquePrefixes(fl)
      no_name = 'no' + name
      prefix = shortest_matches[name]
      no_prefix = shortest_matches[no_name]

      # Replace all occurrences of this boolean with extended forms
      for arg_idx in range(1, len(argv)):
        arg = argv[arg_idx]
        if arg.find('=') >= 0: continue
        if arg.startswith('--'+prefix) and ('--'+name).startswith(arg):
          argv[arg_idx] = ('--%s=true' % name)
        elif arg.startswith('--'+no_prefix) and ('--'+no_name).startswith(arg):
          argv[arg_idx] = ('--%s=false' % name)

    # Loop over all of the flags, building up the lists of short options
    # and long options that will be passed to getopt.  Short options are
    # specified as a string of letters, each letter followed by a colon
    # if it takes an argument.  Long options are stored in an array of
    # strings.  Each string ends with an '=' if it takes an argument.
    for name, flag in fl.items():
      longopts.append(name + "=")
      if len(name) == 1:  # one-letter option: allow short flag type also
        shortopts += name
        if not flag.boolean:
          shortopts += ":"

    longopts.append('undefok=')
    undefok_flags = []

    # In case --undefok is specified, loop to pick up unrecognized
    # options one by one.
    unrecognized_opts = []
    args = argv[1:]
    while True:
      try:
        if self.__dict__['__use_gnu_getopt']:
          optlist, unparsed_args = getopt.gnu_getopt(args, shortopts, longopts)
        else:
          optlist, unparsed_args = getopt.getopt(args, shortopts, longopts)
        break
      except getopt.GetoptError, e:
        if not e.opt or e.opt in fl:
          # Not an unrecognized option, re-raise the exception as a FlagsError
          raise FlagsError(e)
        # Remove offender from args and try again
        for arg_index in range(len(args)):
          if ((args[arg_index] == '--' + e.opt) or
              (args[arg_index] == '-' + e.opt) or
              (args[arg_index].startswith('--' + e.opt + '='))):
            unrecognized_opts.append((e.opt, args[arg_index]))
            args = args[0:arg_index] + args[arg_index+1:]
            break
        else:
          # We should have found the option, so we don't expect to get
          # here.  We could assert, but raising the original exception
          # might work better.
          raise FlagsError(e)

    for name, arg in optlist:
      if name == '--undefok':
        flag_names = arg.split(',')
        undefok_flags.extend(flag_names)
        # For boolean flags, if --undefok=boolflag is specified, then we should
        # also accept --noboolflag, in addition to --boolflag.
        # Since we don't know the type of the undefok'd flag, this will affect
        # non-boolean flags as well.
        # NOTE: You shouldn't use --undefok=noboolflag, because then we will
        # accept --nonoboolflag here.  We are choosing not to do the conversion
        # from noboolflag -> boolflag because of the ambiguity that flag names
        # can start with 'no'.
        undefok_flags.extend('no' + name for name in flag_names)
        continue
      if name.startswith('--'):
        # long option
        name = name[2:]
        short_option = 0
      else:
        # short option
        name = name[1:]
        short_option = 1
      if name in fl:
        flag = fl[name]
        if flag.boolean and short_option: arg = 1
        flag.Parse(arg)

    # If there were unrecognized options, raise an exception unless
    # the options were named via --undefok.
    for opt, value in unrecognized_opts:
      if opt not in undefok_flags:
        raise UnrecognizedFlagError(opt, value)

    if unparsed_args:
      if self.__dict__['__use_gnu_getopt']:
        # if using gnu_getopt just return the program name + remainder of argv.
        ret_val = argv[:1] + unparsed_args
      else:
        # unparsed_args becomes the first non-flag detected by getopt to
        # the end of argv.  Because argv may have been modified above,
        # return original_argv for this region.
        ret_val = argv[:1] + original_argv[-len(unparsed_args):]
    else:
      ret_val = argv[:1]

    self._AssertAllValidators()
    return ret_val

  def Reset(self):
    """Resets the values to the point before FLAGS(argv) was called."""
    for f in self.FlagDict().values():
      f.Unparse()

  def RegisteredFlags(self):
    """Returns: a list of the names and short names of all registered flags."""
    return list(self.FlagDict())

  def FlagValuesDict(self):
    """Returns: a dictionary that maps flag names to flag values."""
    flag_values = {}

    for flag_name in self.RegisteredFlags():
      flag = self.FlagDict()[flag_name]
      flag_values[flag_name] = flag.value

    return flag_values

  def __str__(self):
    """Generates a help string for all known flags."""
    return self.GetHelp()

  def GetHelp(self, prefix=''):
    """Generates a help string for all known flags."""
    helplist = []

    flags_by_module = self.FlagsByModuleDict()
    if flags_by_module:

      modules = sorted(flags_by_module)

      # Print the help for the main module first, if possible.
      main_module = _GetMainModule()
      if main_module in modules:
        modules.remove(main_module)
        modules = [main_module] + modules

      for module in modules:
        self.__RenderOurModuleFlags(module, helplist)

      self.__RenderModuleFlags('gflags',
                               _SPECIAL_FLAGS.FlagDict().values(),
                               helplist)

    else:
      # Just print one long list of flags.
      self.__RenderFlagList(
          self.FlagDict().values() + _SPECIAL_FLAGS.FlagDict().values(),
          helplist, prefix)

    return '\n'.join(helplist)

  def __RenderModuleFlags(self, module, flags, output_lines, prefix=""):
    """Generates a help string for a given module."""
    if not isinstance(module, str):
      module = module.__name__
    output_lines.append('\n%s%s:' % (prefix, module))
    self.__RenderFlagList(flags, output_lines, prefix + "  ")

  def __RenderOurModuleFlags(self, module, output_lines, prefix=""):
    """Generates a help string for a given module."""
    flags = self._GetFlagsDefinedByModule(module)
    if flags:
      self.__RenderModuleFlags(module, flags, output_lines, prefix)

  def __RenderOurModuleKeyFlags(self, module, output_lines, prefix=""):
    """Generates a help string for the key flags of a given module.

    Args:
      module: A module object or a module name (a string).
      output_lines: A list of strings.  The generated help message
        lines will be appended to this list.
      prefix: A string that is prepended to each generated help line.
    """
    key_flags = self._GetKeyFlagsForModule(module)
    if key_flags:
      self.__RenderModuleFlags(module, key_flags, output_lines, prefix)

  def ModuleHelp(self, module):
    """Describe the key flags of a module.

    Args:
      module: A module object or a module name (a string).

    Returns:
      string describing the key flags of a module.
    """
    helplist = []
    self.__RenderOurModuleKeyFlags(module, helplist)
    return '\n'.join(helplist)

  def MainModuleHelp(self):
    """Describe the key flags of the main module.

    Returns:
      string describing the key flags of a module.
    """
    return self.ModuleHelp(_GetMainModule())

  def __RenderFlagList(self, flaglist, output_lines, prefix="  "):
    fl = self.FlagDict()
    special_fl = _SPECIAL_FLAGS.FlagDict()
    flaglist = [(flag.name, flag) for flag in flaglist]
    flaglist.sort()
    flagset = {}
    for (name, flag) in flaglist:
      # It's possible this flag got deleted or overridden since being
      # registered in the per-module flaglist.  Check now against the
      # canonical source of current flag information, the FlagDict.
      if fl.get(name, None) != flag and special_fl.get(name, None) != flag:
        # a different flag is using this name now
        continue
      # only print help once
      if flag in flagset: continue
      flagset[flag] = 1
      flaghelp = ""
      if flag.short_name: flaghelp += "-%s," % flag.short_name
      if flag.boolean:
        flaghelp += "--[no]%s" % flag.name + ":"
      else:
        flaghelp += "--%s" % flag.name + ":"
      flaghelp += "  "
      if flag.help:
        flaghelp += flag.help
      flaghelp = TextWrap(flaghelp, indent=prefix+"  ",
                          firstline_indent=prefix)
      if flag.default_as_str:
        flaghelp += "\n"
        flaghelp += TextWrap("(default: %s)" % flag.default_as_str,
                             indent=prefix+"  ")
      if flag.parser.syntactic_help:
        flaghelp += "\n"
        flaghelp += TextWrap("(%s)" % flag.parser.syntactic_help,
                             indent=prefix+"  ")
      output_lines.append(flaghelp)

  def get(self, name, default):
    """Returns the value of a flag (if not None) or a default value.

    Args:
      name: A string, the name of a flag.
      default: Default value to use if the flag value is None.
    """

    value = self.__getattr__(name)
    if value is not None:  # Can't do if not value, b/c value might be '0' or ""
      return value
    else:
      return default

  def ShortestUniquePrefixes(self, fl):
    """Returns: dictionary; maps flag names to their shortest unique prefix."""
    # Sort the list of flag names
    sorted_flags = []
    for name, flag in fl.items():
      sorted_flags.append(name)
      if flag.boolean:
        sorted_flags.append('no%s' % name)
    sorted_flags.sort()

    # For each name in the sorted list, determine the shortest unique
    # prefix by comparing itself to the next name and to the previous
    # name (the latter check uses cached info from the previous loop).
    shortest_matches = {}
    prev_idx = 0
    for flag_idx in range(len(sorted_flags)):
      curr = sorted_flags[flag_idx]
      if flag_idx == (len(sorted_flags) - 1):
        next = None
      else:
        next = sorted_flags[flag_idx+1]
        next_len = len(next)
      for curr_idx in range(len(curr)):
        if (next is None
            or curr_idx >= next_len
            or curr[curr_idx] != next[curr_idx]):
          # curr longer than next or no more chars in common
          shortest_matches[curr] = curr[:max(prev_idx, curr_idx) + 1]
          prev_idx = curr_idx
          break
      else:
        # curr shorter than (or equal to) next
        shortest_matches[curr] = curr
        prev_idx = curr_idx + 1  # next will need at least one more char
    return shortest_matches

  def __IsFlagFileDirective(self, flag_string):
    """Checks whether flag_string contain a --flagfile=<foo> directive."""
    if isinstance(flag_string, type("")):
      if flag_string.startswith('--flagfile='):
        return 1
      elif flag_string == '--flagfile':
        return 1
      elif flag_string.startswith('-flagfile='):
        return 1
      elif flag_string == '-flagfile':
        return 1
      else:
        return 0
    return 0

  def ExtractFilename(self, flagfile_str):
    """Returns filename from a flagfile_str of form -[-]flagfile=filename.

    The cases of --flagfile foo and -flagfile foo shouldn't be hitting
    this function, as they are dealt with in the level above this
    function.
    """
    if flagfile_str.startswith('--flagfile='):
      return os.path.expanduser((flagfile_str[(len('--flagfile=')):]).strip())
    elif flagfile_str.startswith('-flagfile='):
      return os.path.expanduser((flagfile_str[(len('-flagfile=')):]).strip())
    else:
      raise FlagsError('Hit illegal --flagfile type: %s' % flagfile_str)

  def __GetFlagFileLines(self, filename, parsed_file_list):
    """Returns the useful (!=comments, etc) lines from a file with flags.

    Args:
      filename: A string, the name of the flag file.
      parsed_file_list: A list of the names of the files we have
        already read.  MUTATED BY THIS FUNCTION.

    Returns:
      List of strings. See the note below.

    NOTE(springer): This function checks for a nested --flagfile=<foo>
    tag and handles the lower file recursively. It returns a list of
    all the lines that _could_ contain command flags. This is
    EVERYTHING except whitespace lines and comments (lines starting
    with '#' or '//').
    """
    line_list = []  # All line from flagfile.
    flag_line_list = []  # Subset of lines w/o comments, blanks, flagfile= tags.
    try:
      file_obj = open(filename, 'r')
    except IOError, e_msg:
      raise CantOpenFlagFileError('ERROR:: Unable to open flagfile: %s' % e_msg)

    line_list = file_obj.readlines()
    file_obj.close()
    parsed_file_list.append(filename)

    # This is where we check each line in the file we just read.
    for line in line_list:
      if line.isspace():
        pass
      # Checks for comment (a line that starts with '#').
      elif line.startswith('#') or line.startswith('//'):
        pass
      # Checks for a nested "--flagfile=<bar>" flag in the current file.
      # If we find one, recursively parse down into that file.
      elif self.__IsFlagFileDirective(line):
        sub_filename = self.ExtractFilename(line)
        # We do a little safety check for reparsing a file we've already done.
        if not sub_filename in parsed_file_list:
          included_flags = self.__GetFlagFileLines(sub_filename,
                                                   parsed_file_list)
          flag_line_list.extend(included_flags)
        else:  # Case of hitting a circularly included file.
          sys.stderr.write('Warning: Hit circular flagfile dependency: %s\n' %
                           (sub_filename,))
      else:
        # Any line that's not a comment or a nested flagfile should get
        # copied into 2nd position.  This leaves earlier arguments
        # further back in the list, thus giving them higher priority.
        flag_line_list.append(line.strip())
    return flag_line_list

  def ReadFlagsFromFiles(self, argv, force_gnu=True):
    """Processes command line args, but also allow args to be read from file.

    Args:
      argv: A list of strings, usually sys.argv[1:], which may contain one or
        more flagfile directives of the form --flagfile="./filename".
        Note that the name of the program (sys.argv[0]) should be omitted.
      force_gnu: If False, --flagfile parsing obeys normal flag semantics.
        If True, --flagfile parsing instead follows gnu_getopt semantics.
        *** WARNING *** force_gnu=False may become the future default!

    Returns:

      A new list which has the original list combined with what we read
      from any flagfile(s).

    References: Global gflags.FLAG class instance.

    This function should be called before the normal FLAGS(argv) call.
    This function scans the input list for a flag that looks like:
    --flagfile=<somefile>. Then it opens <somefile>, reads all valid key
    and value pairs and inserts them into the input list between the
    first item of the list and any subsequent items in the list.

    Note that your application's flags are still defined the usual way
    using gflags DEFINE_flag() type functions.

    Notes (assuming we're getting a commandline of some sort as our input):
    --> Flags from the command line argv _should_ always take precedence!
    --> A further "--flagfile=<otherfile.cfg>" CAN be nested in a flagfile.
        It will be processed after the parent flag file is done.
    --> For duplicate flags, first one we hit should "win".
    --> In a flagfile, a line beginning with # or // is a comment.
    --> Entirely blank lines _should_ be ignored.
    """
    parsed_file_list = []
    rest_of_args = argv
    new_argv = []
    while rest_of_args:
      current_arg = rest_of_args[0]
      rest_of_args = rest_of_args[1:]
      if self.__IsFlagFileDirective(current_arg):
        # This handles the case of -(-)flagfile foo.  In this case the
        # next arg really is part of this one.
        if current_arg == '--flagfile' or current_arg == '-flagfile':
          if not rest_of_args:
            raise IllegalFlagValue('--flagfile with no argument')
          flag_filename = os.path.expanduser(rest_of_args[0])
          rest_of_args = rest_of_args[1:]
        else:
          # This handles the case of (-)-flagfile=foo.
          flag_filename = self.ExtractFilename(current_arg)
        new_argv.extend(
            self.__GetFlagFileLines(flag_filename, parsed_file_list))
      else:
        new_argv.append(current_arg)
        # Stop parsing after '--', like getopt and gnu_getopt.
        if current_arg == '--':
          break
        # Stop parsing after a non-flag, like getopt.
        if not current_arg.startswith('-'):
          if not force_gnu and not self.__dict__['__use_gnu_getopt']:
            break

    if rest_of_args:
      new_argv.extend(rest_of_args)

    return new_argv

  def FlagsIntoString(self):
    """Returns a string with the flags assignments from this FlagValues object.

    This function ignores flags whose value is None.  Each flag
    assignment is separated by a newline.

    NOTE: MUST mirror the behavior of the C++ CommandlineFlagsIntoString
    from http://code.google.com/p/google-gflags
    """
    s = ''
    for flag in self.FlagDict().values():
      if flag.value is not None:
        s += flag.Serialize() + '\n'
    return s

  def AppendFlagsIntoFile(self, filename):
    """Appends all flags assignments from this FlagInfo object to a file.

    Output will be in the format of a flagfile.

    NOTE: MUST mirror the behavior of the C++ AppendFlagsIntoFile
    from http://code.google.com/p/google-gflags
    """
    out_file = open(filename, 'a')
    out_file.write(self.FlagsIntoString())
    out_file.close()

  def WriteHelpInXMLFormat(self, outfile=None):
    """Outputs flag documentation in XML format.

    NOTE: We use element names that are consistent with those used by
    the C++ command-line flag library, from
    http://code.google.com/p/google-gflags
    We also use a few new elements (e.g., <key>), but we do not
    interfere / overlap with existing XML elements used by the C++
    library.  Please maintain this consistency.

    Args:
      outfile: File object we write to.  Default None means sys.stdout.
    """
    outfile = outfile or sys.stdout

    outfile.write('<?xml version=\"1.0\"?>\n')
    outfile.write('<AllFlags>\n')
    indent = '  '
    _WriteSimpleXMLElement(outfile, 'program', os.path.basename(sys.argv[0]),
                           indent)

    usage_doc = sys.modules['__main__'].__doc__
    if not usage_doc:
      usage_doc = '\nUSAGE: %s [flags]\n' % sys.argv[0]
    else:
      usage_doc = usage_doc.replace('%s', sys.argv[0])
    _WriteSimpleXMLElement(outfile, 'usage', usage_doc, indent)

    # Get list of key flags for the main module.
    key_flags = self._GetKeyFlagsForModule(_GetMainModule())

    # Sort flags by declaring module name and next by flag name.
    flags_by_module = self.FlagsByModuleDict()
    all_module_names = list(flags_by_module.keys())
    all_module_names.sort()
    for module_name in all_module_names:
      flag_list = [(f.name, f) for f in flags_by_module[module_name]]
      flag_list.sort()
      for unused_flag_name, flag in flag_list:
        is_key = flag in key_flags
        flag.WriteInfoInXMLFormat(outfile, module_name,
                                  is_key=is_key, indent=indent)

    outfile.write('</AllFlags>\n')
    outfile.flush()

  def AddValidator(self, validator):
    """Register new flags validator to be checked.

    Args:
      validator: gflags_validators.Validator
    Raises:
      AttributeError: if validators work with a non-existing flag.
    """
    for flag_name in validator.GetFlagsNames():
      flag = self.FlagDict()[flag_name]
      flag.validators.append(validator)

# end of FlagValues definition


# The global FlagValues instance
FLAGS = FlagValues()


def _StrOrUnicode(value):
  """Converts value to a python string or, if necessary, unicode-string."""
  try:
    return str(value)
  except UnicodeEncodeError:
    return unicode(value)


def _MakeXMLSafe(s):
  """Escapes <, >, and & from s, and removes XML 1.0-illegal chars."""
  s = cgi.escape(s)  # Escape <, >, and &
  # Remove characters that cannot appear in an XML 1.0 document
  # (http://www.w3.org/TR/REC-xml/#charsets).
  #
  # NOTE: if there are problems with current solution, one may move to
  # XML 1.1, which allows such chars, if they're entity-escaped (&#xHH;).
  s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
  # Convert non-ascii characters to entities.  Note: requires python >=2.3
  s = s.encode('ascii', 'xmlcharrefreplace')   # u'\xce\x88' -> 'u&#904;'
  return s


def _WriteSimpleXMLElement(outfile, name, value, indent):
  """Writes a simple XML element.

  Args:
    outfile: File object we write the XML element to.
    name: A string, the name of XML element.
    value: A Python object, whose string representation will be used
      as the value of the XML element.
    indent: A string, prepended to each line of generated output.
  """
  value_str = _StrOrUnicode(value)
  if isinstance(value, bool):
    # Display boolean values as the C++ flag library does: no caps.
    value_str = value_str.lower()
  safe_value_str = _MakeXMLSafe(value_str)
  outfile.write('%s<%s>%s</%s>\n' % (indent, name, safe_value_str, name))


class Flag:
  """Information about a command-line flag.

  'Flag' objects define the following fields:
    .name  - the name for this flag
    .default - the default value for this flag
    .default_as_str - default value as repr'd string, e.g., "'true'" (or None)
    .value  - the most recent parsed value of this flag; set by Parse()
    .help  - a help string or None if no help is available
    .short_name  - the single letter alias for this flag (or None)
    .boolean  - if 'true', this flag does not accept arguments
    .present  - true if this flag was parsed from command line flags.
    .parser  - an ArgumentParser object
    .serializer - an ArgumentSerializer object
    .allow_override - the flag may be redefined without raising an error

  The only public method of a 'Flag' object is Parse(), but it is
  typically only called by a 'FlagValues' object.  The Parse() method is
  a thin wrapper around the 'ArgumentParser' Parse() method.  The parsed
  value is saved in .value, and the .present attribute is updated.  If
  this flag was already present, a FlagsError is raised.

  Parse() is also called during __init__ to parse the default value and
  initialize the .value attribute.  This enables other python modules to
  safely use flags even if the __main__ module neglects to parse the
  command line arguments.  The .present attribute is cleared after
  __init__ parsing.  If the default value is set to None, then the
  __init__ parsing step is skipped and the .value attribute is
  initialized to None.

  Note: The default value is also presented to the user in the help
  string, so it is important that it be a legal value for this flag.
  """

  def __init__(self, parser, serializer, name, default, help_string,
               short_name=None, boolean=0, allow_override=0):
    self.name = name

    if not help_string:
      help_string = '(no help available)'

    self.help = help_string
    self.short_name = short_name
    self.boolean = boolean
    self.present = 0
    self.parser = parser
    self.serializer = serializer
    self.allow_override = allow_override
    self.value = None
    self.validators = []

    self.SetDefault(default)

  def __hash__(self):
    return hash(id(self))

  def __eq__(self, other):
    return self is other

  def __lt__(self, other):
    if isinstance(other, Flag):
      return id(self) < id(other)
    return NotImplemented

  def __GetParsedValueAsString(self, value):
    if value is None:
      return None
    if self.serializer:
      return repr(self.serializer.Serialize(value))
    if self.boolean:
      if value:
        return repr('true')
      else:
        return repr('false')
    return repr(_StrOrUnicode(value))

  def Parse(self, argument):
    try:
      self.value = self.parser.Parse(argument)
    except ValueError, e:  # recast ValueError as IllegalFlagValue
      raise IllegalFlagValue("flag --%s=%s: %s" % (self.name, argument, e))
    self.present += 1

  def Unparse(self):
    if self.default is None:
      self.value = None
    else:
      self.Parse(self.default)
    self.present = 0

  def Serialize(self):
    if self.value is None:
      return ''
    if self.boolean:
      if self.value:
        return "--%s" % self.name
      else:
        return "--no%s" % self.name
    else:
      if not self.serializer:
        raise FlagsError("Serializer not present for flag %s" % self.name)
      return "--%s=%s" % (self.name, self.serializer.Serialize(self.value))

  def SetDefault(self, value):
    """Changes the default value (and current value too) for this Flag."""
    # We can't allow a None override because it may end up not being
    # passed to C++ code when we're overriding C++ flags.  So we
    # cowardly bail out until someone fixes the semantics of trying to
    # pass None to a C++ flag.  See swig_flags.Init() for details on
    # this behavior.
    # TODO(olexiy): Users can directly call this method, bypassing all flags
    # validators (we don't have FlagValues here, so we can not check
    # validators).
    # The simplest solution I see is to make this method private.
    # Another approach would be to store reference to the corresponding
    # FlagValues with each flag, but this seems to be an overkill.
    if value is None and self.allow_override:
      raise DuplicateFlagCannotPropagateNoneToSwig(self.name)

    self.default = value
    self.Unparse()
    self.default_as_str = self.__GetParsedValueAsString(self.value)

  def Type(self):
    """Returns: a string that describes the type of this Flag."""
    # NOTE: we use strings, and not the types.*Type constants because
    # our flags can have more exotic types, e.g., 'comma separated list
    # of strings', 'whitespace separated list of strings', etc.
    return self.parser.Type()

  def WriteInfoInXMLFormat(self, outfile, module_name, is_key=False, indent=''):
    """Writes common info about this flag, in XML format.

    This is information that is relevant to all flags (e.g., name,
    meaning, etc.).  If you defined a flag that has some other pieces of
    info, then please override _WriteCustomInfoInXMLFormat.

    Please do NOT override this method.

    Args:
      outfile: File object we write to.
      module_name: A string, the name of the module that defines this flag.
      is_key: A boolean, True iff this flag is key for main module.
      indent: A string that is prepended to each generated line.
    """
    outfile.write(indent + '<flag>\n')
    inner_indent = indent + '  '
    if is_key:
      _WriteSimpleXMLElement(outfile, 'key', 'yes', inner_indent)
    _WriteSimpleXMLElement(outfile, 'file', module_name, inner_indent)
    # Print flag features that are relevant for all flags.
    _WriteSimpleXMLElement(outfile, 'name', self.name, inner_indent)
    if self.short_name:
      _WriteSimpleXMLElement(outfile, 'short_name', self.short_name,
                             inner_indent)
    if self.help:
      _WriteSimpleXMLElement(outfile, 'meaning', self.help, inner_indent)
    # The default flag value can either be represented as a string like on the
    # command line, or as a Python object.  We serialize this value in the
    # latter case in order to remain consistent.
    if self.serializer and not isinstance(self.default, str):
      default_serialized = self.serializer.Serialize(self.default)
    else:
      default_serialized = self.default
    _WriteSimpleXMLElement(outfile, 'default', default_serialized, inner_indent)
    _WriteSimpleXMLElement(outfile, 'current', self.value, inner_indent)
    _WriteSimpleXMLElement(outfile, 'type', self.Type(), inner_indent)
    # Print extra flag features this flag may have.
    self._WriteCustomInfoInXMLFormat(outfile, inner_indent)
    outfile.write(indent + '</flag>\n')

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    """Writes extra info about this flag, in XML format.

    "Extra" means "not already printed by WriteInfoInXMLFormat above."

    Args:
      outfile: File object we write to.
      indent: A string that is prepended to each generated line.
    """
    # Usually, the parser knows the extra details about the flag, so
    # we just forward the call to it.
    self.parser.WriteCustomInfoInXMLFormat(outfile, indent)
# End of Flag definition


class _ArgumentParserCache(type):
  """Metaclass used to cache and share argument parsers among flags."""

  _instances = {}

  def __call__(mcs, *args, **kwargs):
    """Returns an instance of the argument parser cls.

    This method overrides behavior of the __new__ methods in
    all subclasses of ArgumentParser (inclusive). If an instance
    for mcs with the same set of arguments exists, this instance is
    returned, otherwise a new instance is created.

    If any keyword arguments are defined, or the values in args
    are not hashable, this method always returns a new instance of
    cls.

    Args:
      args: Positional initializer arguments.
      kwargs: Initializer keyword arguments.

    Returns:
      An instance of cls, shared or new.
    """
    if kwargs:
      return type.__call__(mcs, *args, **kwargs)
    else:
      instances = mcs._instances
      key = (mcs,) + tuple(args)
      try:
        return instances[key]
      except KeyError:
        # No cache entry for key exists, create a new one.
        return instances.setdefault(key, type.__call__(mcs, *args))
      except TypeError:
        # An object in args cannot be hashed, always return
        # a new instance.
        return type.__call__(mcs, *args)


class ArgumentParser(object):
  """Base class used to parse and convert arguments.

  The Parse() method checks to make sure that the string argument is a
  legal value and convert it to a native type.  If the value cannot be
  converted, it should throw a 'ValueError' exception with a human
  readable explanation of why the value is illegal.

  Subclasses should also define a syntactic_help string which may be
  presented to the user to describe the form of the legal values.

  Argument parser classes must be stateless, since instances are cached
  and shared between flags. Initializer arguments are allowed, but all
  member variables must be derived from initializer arguments only.
  """
  __metaclass__ = _ArgumentParserCache

  syntactic_help = ""

  def Parse(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument

  def Type(self):
    return 'string'

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    pass


class ArgumentSerializer:
  """Base class for generating string representations of a flag value."""

  def Serialize(self, value):
    return _StrOrUnicode(value)


class ListSerializer(ArgumentSerializer):

  def __init__(self, list_sep):
    self.list_sep = list_sep

  def Serialize(self, value):
    return self.list_sep.join([_StrOrUnicode(x) for x in value])


# Flags validators


def RegisterValidator(flag_name,
                      checker,
                      message='Flag validation failed',
                      flag_values=FLAGS):
  """Adds a constraint, which will be enforced during program execution.

  The constraint is validated when flags are initially parsed, and after each
  change of the corresponding flag's value.
  Args:
    flag_name: string, name of the flag to be checked.
    checker: method to validate the flag.
      input  - value of the corresponding flag (string, boolean, etc.
        This value will be passed to checker by the library). See file's
        docstring for examples.
      output - Boolean.
        Must return True if validator constraint is satisfied.
        If constraint is not satisfied, it should either return False or
          raise gflags_validators.Error(desired_error_message).
    message: error text to be shown to the user if checker returns False.
      If checker raises gflags_validators.Error, message from the raised
        Error will be shown.
    flag_values: FlagValues
  Raises:
    AttributeError: if flag_name is not registered as a valid flag name.
  """
  flag_values.AddValidator(gflags_validators.SimpleValidator(flag_name,
                                                            checker,
                                                            message))


def MarkFlagAsRequired(flag_name, flag_values=FLAGS):
  """Ensure that flag is not None during program execution.

  Registers a flag validator, which will follow usual validator
  rules.
  Args:
    flag_name: string, name of the flag
    flag_values: FlagValues
  Raises:
    AttributeError: if flag_name is not registered as a valid flag name.
  """
  RegisterValidator(flag_name,
                    lambda value: value is not None,
                    message='Flag --%s must be specified.' % flag_name,
                    flag_values=flag_values)


def _RegisterBoundsValidatorIfNeeded(parser, name, flag_values):
  """Enforce lower and upper bounds for numeric flags.

  Args:
    parser: NumericParser (either FloatParser or IntegerParser). Provides lower
      and upper bounds, and help text to display.
    name: string, name of the flag
    flag_values: FlagValues
  """
  if parser.lower_bound is not None or parser.upper_bound is not None:

    def Checker(value):
      if value is not None and parser.IsOutsideBounds(value):
        message = '%s is not %s' % (value, parser.syntactic_help)
        raise gflags_validators.Error(message)
      return True

    RegisterValidator(name,
                      Checker,
                      flag_values=flag_values)


# The DEFINE functions are explained in mode details in the module doc string.


def DEFINE(parser, name, default, help, flag_values=FLAGS, serializer=None,
           **args):
  """Registers a generic Flag object.

  NOTE: in the docstrings of all DEFINE* functions, "registers" is short
  for "creates a new flag and registers it".

  Auxiliary function: clients should use the specialized DEFINE_<type>
  function instead.

  Args:
    parser: ArgumentParser that is used to parse the flag arguments.
    name: A string, the flag name.
    default: The default value of the flag.
    help: A help string.
    flag_values: FlagValues object the flag will be registered with.
    serializer: ArgumentSerializer that serializes the flag value.
    args: Dictionary with extra keyword args that are passes to the
      Flag __init__.
  """
  DEFINE_flag(Flag(parser, serializer, name, default, help, **args),
              flag_values)


def DEFINE_flag(flag, flag_values=FLAGS):
  """Registers a 'Flag' object with a 'FlagValues' object.

  By default, the global FLAGS 'FlagValue' object is used.

  Typical users will use one of the more specialized DEFINE_xxx
  functions, such as DEFINE_string or DEFINE_integer.  But developers
  who need to create Flag objects themselves should use this function
  to register their flags.
  """
  # copying the reference to flag_values prevents pychecker warnings
  fv = flag_values
  fv[flag.name] = flag
  # Tell flag_values who's defining the flag.
  if isinstance(flag_values, FlagValues):
    # Regarding the above isinstance test: some users pass funny
    # values of flag_values (e.g., {}) in order to avoid the flag
    # registration (in the past, there used to be a flag_values ==
    # FLAGS test here) and redefine flags with the same name (e.g.,
    # debug).  To avoid breaking their code, we perform the
    # registration only if flag_values is a real FlagValues object.
    module, module_name = _GetCallingModuleObjectAndName()
    flag_values._RegisterFlagByModule(module_name, flag)
    flag_values._RegisterFlagByModuleId(id(module), flag)


def _InternalDeclareKeyFlags(flag_names,
                             flag_values=FLAGS, key_flag_values=None):
  """Declares a flag as key for the calling module.

  Internal function.  User code should call DECLARE_key_flag or
  ADOPT_module_key_flags instead.

  Args:
    flag_names: A list of strings that are names of already-registered
      Flag objects.
    flag_values: A FlagValues object that the flags listed in
      flag_names have registered with (the value of the flag_values
      argument from the DEFINE_* calls that defined those flags).
      This should almost never need to be overridden.
    key_flag_values: A FlagValues object that (among possibly many
      other things) keeps track of the key flags for each module.
      Default None means "same as flag_values".  This should almost
      never need to be overridden.

  Raises:
    UnrecognizedFlagError: when we refer to a flag that was not
      defined yet.
  """
  key_flag_values = key_flag_values or flag_values

  module = _GetCallingModule()

  for flag_name in flag_names:
    if flag_name not in flag_values:
      raise UnrecognizedFlagError(flag_name)
    flag = flag_values.FlagDict()[flag_name]
    key_flag_values._RegisterKeyFlagForModule(module, flag)


def DECLARE_key_flag(flag_name, flag_values=FLAGS):
  """Declares one flag as key to the current module.

  Key flags are flags that are deemed really important for a module.
  They are important when listing help messages; e.g., if the
  --helpshort command-line flag is used, then only the key flags of the
  main module are listed (instead of all flags, as in the case of
  --help).

  Sample usage:

    gflags.DECLARED_key_flag('flag_1')

  Args:
    flag_name: A string, the name of an already declared flag.
      (Redeclaring flags as key, including flags implicitly key
      because they were declared in this module, is a no-op.)
    flag_values: A FlagValues object.  This should almost never
      need to be overridden.
  """
  if flag_name in _SPECIAL_FLAGS:
    # Take care of the special flags, e.g., --flagfile, --undefok.
    # These flags are defined in _SPECIAL_FLAGS, and are treated
    # specially during flag parsing, taking precedence over the
    # user-defined flags.
    _InternalDeclareKeyFlags([flag_name],
                             flag_values=_SPECIAL_FLAGS,
                             key_flag_values=flag_values)
    return
  _InternalDeclareKeyFlags([flag_name], flag_values=flag_values)


def ADOPT_module_key_flags(module, flag_values=FLAGS):
  """Declares that all flags key to a module are key to the current module.

  Args:
    module: A module object.
    flag_values: A FlagValues object.  This should almost never need
      to be overridden.

  Raises:
    FlagsError: When given an argument that is a module name (a
    string), instead of a module object.
  """
  # NOTE(salcianu): an even better test would be if not
  # isinstance(module, types.ModuleType) but I didn't want to import
  # types for such a tiny use.
  if isinstance(module, str):
    raise FlagsError('Received module name %s; expected a module object.'
                     % module)
  _InternalDeclareKeyFlags(
      [f.name for f in flag_values._GetKeyFlagsForModule(module.__name__)],
      flag_values=flag_values)
  # If module is this flag module, take _SPECIAL_FLAGS into account.
  if module == _GetThisModuleObjectAndName()[0]:
    _InternalDeclareKeyFlags(
        # As we associate flags with _GetCallingModuleObjectAndName(), the
        # special flags defined in this module are incorrectly registered with
        # a different module.  So, we can't use _GetKeyFlagsForModule.
        # Instead, we take all flags from _SPECIAL_FLAGS (a private
        # FlagValues, where no other module should register flags).
        [f.name for f in _SPECIAL_FLAGS.FlagDict().values()],
        flag_values=_SPECIAL_FLAGS,
        key_flag_values=flag_values)


#
# STRING FLAGS
#


def DEFINE_string(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value can be any string."""
  parser = ArgumentParser()
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# BOOLEAN FLAGS
#


class BooleanParser(ArgumentParser):
  """Parser of boolean values."""

  def Convert(self, argument):
    """Converts the argument to a boolean; raise ValueError on errors."""
    if type(argument) == str:
      if argument.lower() in ['true', 't', '1']:
        return True
      elif argument.lower() in ['false', 'f', '0']:
        return False

    bool_argument = bool(argument)
    if argument == bool_argument:
      # The argument is a valid boolean (True, False, 0, or 1), and not just
      # something that always converts to bool (list, string, int, etc.).
      return bool_argument

    raise ValueError('Non-boolean argument to boolean flag', argument)

  def Parse(self, argument):
    val = self.Convert(argument)
    return val

  def Type(self):
    return 'bool'


class BooleanFlag(Flag):
  """Basic boolean flag.

  Boolean flags do not take any arguments, and their value is either
  True (1) or False (0).  The false value is specified on the command
  line by prepending the word 'no' to either the long or the short flag
  name.

  For example, if a Boolean flag was created whose long name was
  'update' and whose short name was 'x', then this flag could be
  explicitly unset through either --noupdate or --nox.
  """

  def __init__(self, name, default, help, short_name=None, **args):
    p = BooleanParser()
    Flag.__init__(self, p, None, name, default, help, short_name, 1, **args)
    if not self.help: self.help = "a boolean value"


def DEFINE_boolean(name, default, help, flag_values=FLAGS, **args):
  """Registers a boolean flag.

  Such a boolean flag does not take an argument.  If a user wants to
  specify a false value explicitly, the long option beginning with 'no'
  must be used: i.e. --noflag

  This flag will have a value of None, True or False.  None is possible
  if default=None and the user does not specify the flag on the command
  line.
  """
  DEFINE_flag(BooleanFlag(name, default, help, **args), flag_values)


# Match C++ API to unconfuse C++ people.
DEFINE_bool = DEFINE_boolean


class HelpFlag(BooleanFlag):
  """
  HelpFlag is a special boolean flag that prints usage information and
  raises a SystemExit exception if it is ever found in the command
  line arguments.  Note this is called with allow_override=1, so other
  apps can define their own --help flag, replacing this one, if they want.
  """
  def __init__(self):
    BooleanFlag.__init__(self, "help", 0, "show this help",
                         short_name="?", allow_override=1)
  def Parse(self, arg):
    if arg:
      doc = sys.modules["__main__"].__doc__
      flags = str(FLAGS)
      print doc or ("\nUSAGE: %s [flags]\n" % sys.argv[0])
      if flags:
        print "flags:"
        print flags
      sys.exit(1)
class HelpXMLFlag(BooleanFlag):
  """Similar to HelpFlag, but generates output in XML format."""
  def __init__(self):
    BooleanFlag.__init__(self, 'helpxml', False,
                         'like --help, but generates XML output',
                         allow_override=1)
  def Parse(self, arg):
    if arg:
      FLAGS.WriteHelpInXMLFormat(sys.stdout)
      sys.exit(1)
class HelpshortFlag(BooleanFlag):
  """
  HelpshortFlag is a special boolean flag that prints usage
  information for the "main" module, and rasies a SystemExit exception
  if it is ever found in the command line arguments.  Note this is
  called with allow_override=1, so other apps can define their own
  --helpshort flag, replacing this one, if they want.
  """
  def __init__(self):
    BooleanFlag.__init__(self, "helpshort", 0,
                         "show usage only for this module", allow_override=1)
  def Parse(self, arg):
    if arg:
      doc = sys.modules["__main__"].__doc__
      flags = FLAGS.MainModuleHelp()
      print doc or ("\nUSAGE: %s [flags]\n" % sys.argv[0])
      if flags:
        print "flags:"
        print flags
      sys.exit(1)

#
# Numeric parser - base class for Integer and Float parsers
#


class NumericParser(ArgumentParser):
  """Parser of numeric values.

  Parsed value may be bounded to a given upper and lower bound.
  """

  def IsOutsideBounds(self, val):
    return ((self.lower_bound is not None and val < self.lower_bound) or
            (self.upper_bound is not None and val > self.upper_bound))

  def Parse(self, argument):
    val = self.Convert(argument)
    if self.IsOutsideBounds(val):
      raise ValueError("%s is not %s" % (val, self.syntactic_help))
    return val

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    if self.lower_bound is not None:
      _WriteSimpleXMLElement(outfile, 'lower_bound', self.lower_bound, indent)
    if self.upper_bound is not None:
      _WriteSimpleXMLElement(outfile, 'upper_bound', self.upper_bound, indent)

  def Convert(self, argument):
    """Default implementation: always returns its argument unmodified."""
    return argument

# End of Numeric Parser

#
# FLOAT FLAGS
#


class FloatParser(NumericParser):
  """Parser of floating point values.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = "a"
  number_name = "number"
  syntactic_help = " ".join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    super(FloatParser, self).__init__()
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound is not None and upper_bound is not None:
      sh = ("%s in the range [%s, %s]" % (sh, lower_bound, upper_bound))
    elif lower_bound == 0:
      sh = "a non-negative %s" % self.number_name
    elif upper_bound == 0:
      sh = "a non-positive %s" % self.number_name
    elif upper_bound is not None:
      sh = "%s <= %s" % (self.number_name, upper_bound)
    elif lower_bound is not None:
      sh = "%s >= %s" % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    """Converts argument to a float; raises ValueError on errors."""
    return float(argument)

  def Type(self):
    return 'float'
# End of FloatParser


def DEFINE_float(name, default, help, lower_bound=None, upper_bound=None,
                 flag_values=FLAGS, **args):
  """Registers a flag whose value must be a float.

  If lower_bound or upper_bound are set, then this flag must be
  within the given range.
  """
  parser = FloatParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)
  _RegisterBoundsValidatorIfNeeded(parser, name, flag_values=flag_values)

#
# INTEGER FLAGS
#


class IntegerParser(NumericParser):
  """Parser of an integer value.

  Parsed value may be bounded to a given upper and lower bound.
  """
  number_article = "an"
  number_name = "integer"
  syntactic_help = " ".join((number_article, number_name))

  def __init__(self, lower_bound=None, upper_bound=None):
    super(IntegerParser, self).__init__()
    self.lower_bound = lower_bound
    self.upper_bound = upper_bound
    sh = self.syntactic_help
    if lower_bound is not None and upper_bound is not None:
      sh = ("%s in the range [%s, %s]" % (sh, lower_bound, upper_bound))
    elif lower_bound == 1:
      sh = "a positive %s" % self.number_name
    elif upper_bound == -1:
      sh = "a negative %s" % self.number_name
    elif lower_bound == 0:
      sh = "a non-negative %s" % self.number_name
    elif upper_bound == 0:
      sh = "a non-positive %s" % self.number_name
    elif upper_bound is not None:
      sh = "%s <= %s" % (self.number_name, upper_bound)
    elif lower_bound is not None:
      sh = "%s >= %s" % (self.number_name, lower_bound)
    self.syntactic_help = sh

  def Convert(self, argument):
    __pychecker__ = 'no-returnvalues'
    if type(argument) == str:
      base = 10
      if len(argument) > 2 and argument[0] == "0" and argument[1] == "x":
        base = 16
      return int(argument, base)
    else:
      return int(argument)

  def Type(self):
    return 'int'


def DEFINE_integer(name, default, help, lower_bound=None, upper_bound=None,
                   flag_values=FLAGS, **args):
  """Registers a flag whose value must be an integer.

  If lower_bound, or upper_bound are set, then this flag must be
  within the given range.
  """
  parser = IntegerParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE(parser, name, default, help, flag_values, serializer, **args)
  _RegisterBoundsValidatorIfNeeded(parser, name, flag_values=flag_values)


#
# ENUM FLAGS
#


class EnumParser(ArgumentParser):
  """Parser of a string enum value (a string value from a given set).

  If enum_values (see below) is not specified, any string is allowed.
  """

  def __init__(self, enum_values=None):
    super(EnumParser, self).__init__()
    self.enum_values = enum_values

  def Parse(self, argument):
    if self.enum_values and argument not in self.enum_values:
      raise ValueError("value should be one of <%s>" %
                       "|".join(self.enum_values))
    return argument

  def Type(self):
    return 'string enum'


class EnumFlag(Flag):
  """Basic enum flag; its value can be any string from list of enum_values."""

  def __init__(self, name, default, help, enum_values=None,
               short_name=None, **args):
    enum_values = enum_values or []
    p = EnumParser(enum_values)
    g = ArgumentSerializer()
    Flag.__init__(self, p, g, name, default, help, short_name, **args)
    if not self.help: self.help = "an enum string"
    self.help = "<%s>: %s" % ("|".join(enum_values), self.help)

  def _WriteCustomInfoInXMLFormat(self, outfile, indent):
    for enum_value in self.parser.enum_values:
      _WriteSimpleXMLElement(outfile, 'enum_value', enum_value, indent)


def DEFINE_enum(name, default, enum_values, help, flag_values=FLAGS,
                **args):
  """Registers a flag whose value can be any string from enum_values."""
  DEFINE_flag(EnumFlag(name, default, help, enum_values, ** args),
              flag_values)


#
# LIST FLAGS
#


class BaseListParser(ArgumentParser):
  """Base class for a parser of lists of strings.

  To extend, inherit from this class; from the subclass __init__, call

    BaseListParser.__init__(self, token, name)

  where token is a character used to tokenize, and name is a description
  of the separator.
  """

  def __init__(self, token=None, name=None):
    assert name
    super(BaseListParser, self).__init__()
    self._token = token
    self._name = name
    self.syntactic_help = "a %s separated list" % self._name

  def Parse(self, argument):
    if isinstance(argument, list):
      return argument
    elif argument == '':
      return []
    else:
      return [s.strip() for s in argument.split(self._token)]

  def Type(self):
    return '%s separated list of strings' % self._name


class ListParser(BaseListParser):
  """Parser for a comma-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, ',', 'comma')

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    _WriteSimpleXMLElement(outfile, 'list_separator', repr(','), indent)


class WhitespaceSeparatedListParser(BaseListParser):
  """Parser for a whitespace-separated list of strings."""

  def __init__(self):
    BaseListParser.__init__(self, None, 'whitespace')

  def WriteCustomInfoInXMLFormat(self, outfile, indent):
    BaseListParser.WriteCustomInfoInXMLFormat(self, outfile, indent)
    separators = list(string.whitespace)
    separators.sort()
    for ws_char in string.whitespace:
      _WriteSimpleXMLElement(outfile, 'list_separator', repr(ws_char), indent)


def DEFINE_list(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value is a comma-separated list of strings."""
  parser = ListParser()
  serializer = ListSerializer(',')
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


def DEFINE_spaceseplist(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value is a whitespace-separated list of strings.

  Any whitespace can be used as a separator.
  """
  parser = WhitespaceSeparatedListParser()
  serializer = ListSerializer(' ')
  DEFINE(parser, name, default, help, flag_values, serializer, **args)


#
# MULTI FLAGS
#


class MultiFlag(Flag):
  """A flag that can appear multiple time on the command-line.

  The value of such a flag is a list that contains the individual values
  from all the appearances of that flag on the command-line.

  See the __doc__ for Flag for most behavior of this class.  Only
  differences in behavior are described here:

    * The default value may be either a single value or a list of values.
      A single value is interpreted as the [value] singleton list.

    * The value of the flag is always a list, even if the option was
      only supplied once, and even if the default value is a single
      value
  """

  def __init__(self, *args, **kwargs):
    Flag.__init__(self, *args, **kwargs)
    self.help += ';\n    repeat this option to specify a list of values'

  def Parse(self, arguments):
    """Parses one or more arguments with the installed parser.

    Args:
      arguments: a single argument or a list of arguments (typically a
        list of default values); a single argument is converted
        internally into a list containing one item.
    """
    if not isinstance(arguments, list):
      # Default value may be a list of values.  Most other arguments
      # will not be, so convert them into a single-item list to make
      # processing simpler below.
      arguments = [arguments]

    if self.present:
      # keep a backup reference to list of previously supplied option values
      values = self.value
    else:
      # "erase" the defaults with an empty list
      values = []

    for item in arguments:
      # have Flag superclass parse argument, overwriting self.value reference
      Flag.Parse(self, item)  # also increments self.present
      values.append(self.value)

    # put list of option values back in the 'value' attribute
    self.value = values

  def Serialize(self):
    if not self.serializer:
      raise FlagsError("Serializer not present for flag %s" % self.name)
    if self.value is None:
      return ''

    s = ''

    multi_value = self.value

    for self.value in multi_value:
      if s: s += ' '
      s += Flag.Serialize(self)

    self.value = multi_value

    return s

  def Type(self):
    return 'multi ' + self.parser.Type()


def DEFINE_multi(parser, serializer, name, default, help, flag_values=FLAGS,
                 **args):
  """Registers a generic MultiFlag that parses its args with a given parser.

  Auxiliary function.  Normal users should NOT use it directly.

  Developers who need to create their own 'Parser' classes for options
  which can appear multiple times can call this module function to
  register their flags.
  """
  DEFINE_flag(MultiFlag(parser, serializer, name, default, help, **args),
              flag_values)


def DEFINE_multistring(name, default, help, flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of any strings.

  Use the flag on the command line multiple times to place multiple
  string values into the list.  The 'default' may be a single string
  (which will be converted into a single-element list) or a list of
  strings.
  """
  parser = ArgumentParser()
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


def DEFINE_multi_int(name, default, help, lower_bound=None, upper_bound=None,
                     flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of arbitrary integers.

  Use the flag on the command line multiple times to place multiple
  integer values into the list.  The 'default' may be a single integer
  (which will be converted into a single-element list) or a list of
  integers.
  """
  parser = IntegerParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


def DEFINE_multi_float(name, default, help, lower_bound=None, upper_bound=None,
                       flag_values=FLAGS, **args):
  """Registers a flag whose value can be a list of arbitrary floats.

  Use the flag on the command line multiple times to place multiple
  float values into the list.  The 'default' may be a single float
  (which will be converted into a single-element list) or a list of
  floats.
  """
  parser = FloatParser(lower_bound, upper_bound)
  serializer = ArgumentSerializer()
  DEFINE_multi(parser, serializer, name, default, help, flag_values, **args)


# Now register the flags that we want to exist in all applications.
# These are all defined with allow_override=1, so user-apps can use
# these flagnames for their own purposes, if they want.
DEFINE_flag(HelpFlag())
DEFINE_flag(HelpshortFlag())
DEFINE_flag(HelpXMLFlag())

# Define special flags here so that help may be generated for them.
# NOTE: Please do NOT use _SPECIAL_FLAGS from outside this module.
_SPECIAL_FLAGS = FlagValues()


DEFINE_string(
    'flagfile', "",
    "Insert flag definitions from the given file into the command line.",
    _SPECIAL_FLAGS)

DEFINE_string(
    'undefok', "",
    "comma-separated list of flag names that it is okay to specify "
    "on the command line even if the program does not define a flag "
    "with that name.  IMPORTANT: flags in this list that have "
    "arguments MUST use the --flag=value format.", _SPECIAL_FLAGS)

########NEW FILE########
__FILENAME__ = gflags2man
#!/usr/bin/env python

# Copyright (c) 2006, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""gflags2man runs a Google flags base program and generates a man page.

Run the program, parse the output, and then format that into a man
page.

Usage:
  gflags2man <program> [program] ...
"""

# TODO(csilvers): work with windows paths (\) as well as unix (/)

# This may seem a bit of an end run, but it:  doesn't bloat flags, can
# support python/java/C++, supports older executables, and can be
# extended to other document formats.
# Inspired by help2man.



import os
import re
import sys
import stat
import time

import gflags

_VERSION = '0.1'


def _GetDefaultDestDir():
  home = os.environ.get('HOME', '')
  homeman = os.path.join(home, 'man', 'man1')
  if home and os.path.exists(homeman):
    return homeman
  else:
    return os.environ.get('TMPDIR', '/tmp')

FLAGS = gflags.FLAGS
gflags.DEFINE_string('dest_dir', _GetDefaultDestDir(),
                    'Directory to write resulting manpage to.'
                    ' Specify \'-\' for stdout')
gflags.DEFINE_string('help_flag', '--help',
                    'Option to pass to target program in to get help')
gflags.DEFINE_integer('v', 0, 'verbosity level to use for output')


_MIN_VALID_USAGE_MSG = 9         # if fewer lines than this, help is suspect


class Logging:
  """A super-simple logging class"""
  def error(self, msg): print >>sys.stderr, "ERROR: ", msg
  def warn(self, msg): print >>sys.stderr, "WARNING: ", msg
  def info(self, msg): print msg
  def debug(self, msg): self.vlog(1, msg)
  def vlog(self, level, msg):
    if FLAGS.v >= level: print msg
logging = Logging()
class App:
  def usage(self, shorthelp=0):
    print >>sys.stderr, __doc__
    print >>sys.stderr, "flags:"
    print >>sys.stderr, str(FLAGS)
  def run(self):
    main(sys.argv)
app = App()


def GetRealPath(filename):
  """Given an executable filename, find in the PATH or find absolute path.
  Args:
    filename  An executable filename (string)
  Returns:
    Absolute version of filename.
    None if filename could not be found locally, absolutely, or in PATH
  """
  if os.path.isabs(filename):                # already absolute
    return filename

  if filename.startswith('./') or  filename.startswith('../'): # relative
    return os.path.abspath(filename)

  path = os.getenv('PATH', '')
  for directory in path.split(':'):
    tryname = os.path.join(directory, filename)
    if os.path.exists(tryname):
      if not os.path.isabs(directory):  # relative directory
        return os.path.abspath(tryname)
      return tryname
  if os.path.exists(filename):
    return os.path.abspath(filename)
  return None                         # could not determine

class Flag(object):
  """The information about a single flag."""

  def __init__(self, flag_desc, help):
    """Create the flag object.
    Args:
      flag_desc  The command line forms this could take. (string)
      help       The help text (string)
    """
    self.desc = flag_desc               # the command line forms
    self.help = help                    # the help text
    self.default = ''                   # default value
    self.tips = ''                      # parsing/syntax tips


class ProgramInfo(object):
  """All the information gleaned from running a program with --help."""

  # Match a module block start, for python scripts --help
  # "goopy.logging:"
  module_py_re = re.compile(r'(\S.+):$')
  # match the start of a flag listing
  # " -v,--verbosity:  Logging verbosity"
  flag_py_re         = re.compile(r'\s+(-\S+):\s+(.*)$')
  # "   (default: '0')"
  flag_default_py_re = re.compile(r'\s+\(default:\s+\'(.*)\'\)$')
  # "   (an integer)"
  flag_tips_py_re    = re.compile(r'\s+\((.*)\)$')

  # Match a module block start, for c++ programs --help
  # "google/base/commandlineflags":
  module_c_re = re.compile(r'\s+Flags from (\S.+):$')
  # match the start of a flag listing
  # " -v,--verbosity:  Logging verbosity"
  flag_c_re         = re.compile(r'\s+(-\S+)\s+(.*)$')

  # Match a module block start, for java programs --help
  # "com.google.common.flags"
  module_java_re = re.compile(r'\s+Flags for (\S.+):$')
  # match the start of a flag listing
  # " -v,--verbosity:  Logging verbosity"
  flag_java_re         = re.compile(r'\s+(-\S+)\s+(.*)$')

  def __init__(self, executable):
    """Create object with executable.
    Args:
      executable  Program to execute (string)
    """
    self.long_name = executable
    self.name = os.path.basename(executable)  # name
    # Get name without extension (PAR files)
    (self.short_name, self.ext) = os.path.splitext(self.name)
    self.executable = GetRealPath(executable)  # name of the program
    self.output = []          # output from the program.  List of lines.
    self.desc = []            # top level description.  List of lines
    self.modules = {}         # { section_name(string), [ flags ] }
    self.module_list = []     # list of module names in their original order
    self.date = time.localtime(time.time())   # default date info

  def Run(self):
    """Run it and collect output.

    Returns:
      1 (true)   If everything went well.
      0 (false)  If there were problems.
    """
    if not self.executable:
      logging.error('Could not locate "%s"' % self.long_name)
      return 0

    finfo = os.stat(self.executable)
    self.date = time.localtime(finfo[stat.ST_MTIME])

    logging.info('Running: %s %s </dev/null 2>&1'
                 % (self.executable, FLAGS.help_flag))
    # --help output is often routed to stderr, so we combine with stdout.
    # Re-direct stdin to /dev/null to encourage programs that
    # don't understand --help to exit.
    (child_stdin, child_stdout_and_stderr) = os.popen4(
      [self.executable, FLAGS.help_flag])
    child_stdin.close()       # '</dev/null'
    self.output = child_stdout_and_stderr.readlines()
    child_stdout_and_stderr.close()
    if len(self.output) < _MIN_VALID_USAGE_MSG:
      logging.error('Error: "%s %s" returned only %d lines: %s'
                    % (self.name, FLAGS.help_flag,
                       len(self.output), self.output))
      return 0
    return 1

  def Parse(self):
    """Parse program output."""
    (start_line, lang) = self.ParseDesc()
    if start_line < 0:
      return
    if 'python' == lang:
      self.ParsePythonFlags(start_line)
    elif 'c' == lang:
      self.ParseCFlags(start_line)
    elif 'java' == lang:
      self.ParseJavaFlags(start_line)

  def ParseDesc(self, start_line=0):
    """Parse the initial description.

    This could be Python or C++.

    Returns:
      (start_line, lang_type)
        start_line  Line to start parsing flags on (int)
        lang_type   Either 'python' or 'c'
       (-1, '')  if the flags start could not be found
    """
    exec_mod_start = self.executable + ':'

    after_blank = 0
    start_line = 0             # ignore the passed-in arg for now (?)
    for start_line in range(start_line, len(self.output)): # collect top description
      line = self.output[start_line].rstrip()
      # Python flags start with 'flags:\n'
      if ('flags:' == line
          and len(self.output) > start_line+1
          and '' == self.output[start_line+1].rstrip()):
        start_line += 2
        logging.debug('Flags start (python): %s' % line)
        return (start_line, 'python')
      # SWIG flags just have the module name followed by colon.
      if exec_mod_start == line:
        logging.debug('Flags start (swig): %s' % line)
        return (start_line, 'python')
      # C++ flags begin after a blank line and with a constant string
      if after_blank and line.startswith('  Flags from '):
        logging.debug('Flags start (c): %s' % line)
        return (start_line, 'c')
      # java flags begin with a constant string
      if line == 'where flags are':
        logging.debug('Flags start (java): %s' % line)
        start_line += 2                        # skip "Standard flags:"
        return (start_line, 'java')

      logging.debug('Desc: %s' % line)
      self.desc.append(line)
      after_blank = (line == '')
    else:
      logging.warn('Never found the start of the flags section for "%s"!'
                   % self.long_name)
      return (-1, '')

  def ParsePythonFlags(self, start_line=0):
    """Parse python/swig style flags."""
    modname = None                      # name of current module
    modlist = []
    flag = None
    for line_num in range(start_line, len(self.output)): # collect flags
      line = self.output[line_num].rstrip()
      if not line:                      # blank
        continue

      mobj = self.module_py_re.match(line)
      if mobj:                          # start of a new module
        modname = mobj.group(1)
        logging.debug('Module: %s' % line)
        if flag:
          modlist.append(flag)
        self.module_list.append(modname)
        self.modules.setdefault(modname, [])
        modlist = self.modules[modname]
        flag = None
        continue

      mobj = self.flag_py_re.match(line)
      if mobj:                          # start of a new flag
        if flag:
          modlist.append(flag)
        logging.debug('Flag: %s' % line)
        flag = Flag(mobj.group(1),  mobj.group(2))
        continue

      if not flag:                    # continuation of a flag
        logging.error('Flag info, but no current flag "%s"' % line)
      mobj = self.flag_default_py_re.match(line)
      if mobj:                          # (default: '...')
        flag.default = mobj.group(1)
        logging.debug('Fdef: %s' % line)
        continue
      mobj = self.flag_tips_py_re.match(line)
      if mobj:                          # (tips)
        flag.tips = mobj.group(1)
        logging.debug('Ftip: %s' % line)
        continue
      if flag and flag.help:
        flag.help += line              # multiflags tack on an extra line
      else:
        logging.info('Extra: %s' % line)
    if flag:
      modlist.append(flag)

  def ParseCFlags(self, start_line=0):
    """Parse C style flags."""
    modname = None                      # name of current module
    modlist = []
    flag = None
    for line_num in range(start_line, len(self.output)):  # collect flags
      line = self.output[line_num].rstrip()
      if not line:                      # blank lines terminate flags
        if flag:                        # save last flag
          modlist.append(flag)
          flag = None
        continue

      mobj = self.module_c_re.match(line)
      if mobj:                          # start of a new module
        modname = mobj.group(1)
        logging.debug('Module: %s' % line)
        if flag:
          modlist.append(flag)
        self.module_list.append(modname)
        self.modules.setdefault(modname, [])
        modlist = self.modules[modname]
        flag = None
        continue

      mobj = self.flag_c_re.match(line)
      if mobj:                          # start of a new flag
        if flag:                        # save last flag
          modlist.append(flag)
        logging.debug('Flag: %s' % line)
        flag = Flag(mobj.group(1),  mobj.group(2))
        continue

      # append to flag help.  type and default are part of the main text
      if flag:
        flag.help += ' ' + line.strip()
      else:
        logging.info('Extra: %s' % line)
    if flag:
      modlist.append(flag)

  def ParseJavaFlags(self, start_line=0):
    """Parse Java style flags (com.google.common.flags)."""
    # The java flags prints starts with a "Standard flags" "module"
    # that doesn't follow the standard module syntax.
    modname = 'Standard flags'          # name of current module
    self.module_list.append(modname)
    self.modules.setdefault(modname, [])
    modlist = self.modules[modname]
    flag = None

    for line_num in range(start_line, len(self.output)): # collect flags
      line = self.output[line_num].rstrip()
      logging.vlog(2, 'Line: "%s"' % line)
      if not line:                      # blank lines terminate module
        if flag:                        # save last flag
          modlist.append(flag)
          flag = None
        continue

      mobj = self.module_java_re.match(line)
      if mobj:                          # start of a new module
        modname = mobj.group(1)
        logging.debug('Module: %s' % line)
        if flag:
          modlist.append(flag)
        self.module_list.append(modname)
        self.modules.setdefault(modname, [])
        modlist = self.modules[modname]
        flag = None
        continue

      mobj = self.flag_java_re.match(line)
      if mobj:                          # start of a new flag
        if flag:                        # save last flag
          modlist.append(flag)
        logging.debug('Flag: %s' % line)
        flag = Flag(mobj.group(1),  mobj.group(2))
        continue

      # append to flag help.  type and default are part of the main text
      if flag:
        flag.help += ' ' + line.strip()
      else:
        logging.info('Extra: %s' % line)
    if flag:
      modlist.append(flag)

  def Filter(self):
    """Filter parsed data to create derived fields."""
    if not self.desc:
      self.short_desc = ''
      return

    for i in range(len(self.desc)):   # replace full path with name
      if self.desc[i].find(self.executable) >= 0:
        self.desc[i] = self.desc[i].replace(self.executable, self.name)

    self.short_desc = self.desc[0]
    word_list = self.short_desc.split(' ')
    all_names = [ self.name, self.short_name, ]
    # Since the short_desc is always listed right after the name,
    #  trim it from the short_desc
    while word_list and (word_list[0] in all_names
                         or word_list[0].lower() in all_names):
      del word_list[0]
      self.short_desc = ''              # signal need to reconstruct
    if not self.short_desc and word_list:
      self.short_desc = ' '.join(word_list)


class GenerateDoc(object):
  """Base class to output flags information."""

  def __init__(self, proginfo, directory='.'):
    """Create base object.
    Args:
      proginfo   A ProgramInfo object
      directory  Directory to write output into
    """
    self.info = proginfo
    self.dirname = directory

  def Output(self):
    """Output all sections of the page."""
    self.Open()
    self.Header()
    self.Body()
    self.Footer()

  def Open(self): raise NotImplementedError    # define in subclass
  def Header(self): raise NotImplementedError  # define in subclass
  def Body(self): raise NotImplementedError    # define in subclass
  def Footer(self): raise NotImplementedError  # define in subclass


class GenerateMan(GenerateDoc):
  """Output a man page."""

  def __init__(self, proginfo, directory='.'):
    """Create base object.
    Args:
      proginfo   A ProgramInfo object
      directory  Directory to write output into
    """
    GenerateDoc.__init__(self, proginfo, directory)

  def Open(self):
    if self.dirname == '-':
      logging.info('Writing to stdout')
      self.fp = sys.stdout
    else:
      self.file_path = '%s.1' % os.path.join(self.dirname, self.info.name)
      logging.info('Writing: %s' % self.file_path)
      self.fp = open(self.file_path, 'w')

  def Header(self):
    self.fp.write(
      '.\\" DO NOT MODIFY THIS FILE!  It was generated by gflags2man %s\n'
      % _VERSION)
    self.fp.write(
      '.TH %s "1" "%s" "%s" "User Commands"\n'
      % (self.info.name, time.strftime('%x', self.info.date), self.info.name))
    self.fp.write(
      '.SH NAME\n%s \\- %s\n' % (self.info.name, self.info.short_desc))
    self.fp.write(
      '.SH SYNOPSIS\n.B %s\n[\\fIFLAGS\\fR]...\n' % self.info.name)

  def Body(self):
    self.fp.write(
      '.SH DESCRIPTION\n.\\" Add any additional description here\n.PP\n')
    for ln in self.info.desc:
      self.fp.write('%s\n' % ln)
    self.fp.write(
      '.SH OPTIONS\n')
    # This shows flags in the original order
    for modname in self.info.module_list:
      if modname.find(self.info.executable) >= 0:
        mod = modname.replace(self.info.executable, self.info.name)
      else:
        mod = modname
      self.fp.write('\n.P\n.I %s\n' % mod)
      for flag in self.info.modules[modname]:
        help_string = flag.help
        if flag.default or flag.tips:
          help_string += '\n.br\n'
        if flag.default:
          help_string += '  (default: \'%s\')' % flag.default
        if flag.tips:
          help_string += '  (%s)' % flag.tips
        self.fp.write(
          '.TP\n%s\n%s\n' % (flag.desc, help_string))

  def Footer(self):
    self.fp.write(
      '.SH COPYRIGHT\nCopyright \(co %s Google.\n'
      % time.strftime('%Y', self.info.date))
    self.fp.write('Gflags2man created this page from "%s %s" output.\n'
                  % (self.info.name, FLAGS.help_flag))
    self.fp.write('\nGflags2man was written by Dan Christian. '
                  ' Note that the date on this'
                  ' page is the modification date of %s.\n' % self.info.name)


def main(argv):
  argv = FLAGS(argv)           # handles help as well
  if len(argv) <= 1:
    app.usage(shorthelp=1)
    return 1

  for arg in argv[1:]:
    prog = ProgramInfo(arg)
    if not prog.Run():
      continue
    prog.Parse()
    prog.Filter()
    doc = GenerateMan(prog, FLAGS.dest_dir)
    doc.Output()
  return 0

if __name__ == '__main__':
  app.run()

########NEW FILE########
__FILENAME__ = gflags_validators
#!/usr/bin/env python

# Copyright (c) 2010, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Module to enforce different constraints on flags.

A validator represents an invariant, enforced over a one or more flags.
See 'FLAGS VALIDATORS' in gflags.py's docstring for a usage manual.
"""

__author__ = 'olexiy@google.com (Olexiy Oryeshko)'


class Error(Exception):
  """Thrown If validator constraint is not satisfied."""


class Validator(object):
  """Base class for flags validators.

  Users should NOT overload these classes, and use gflags.Register...
  methods instead.
  """

  # Used to assign each validator an unique insertion_index
  validators_count = 0

  def __init__(self, checker, message):
    """Constructor to create all validators.

    Args:
      checker: function to verify the constraint.
        Input of this method varies, see SimpleValidator and
          DictionaryValidator for a detailed description.
      message: string, error message to be shown to the user
    """
    self.checker = checker
    self.message = message
    Validator.validators_count += 1
    # Used to assert validators in the order they were registered (CL/18694236)
    self.insertion_index = Validator.validators_count

  def Verify(self, flag_values):
    """Verify that constraint is satisfied.

    flags library calls this method to verify Validator's constraint.
    Args:
      flag_values: gflags.FlagValues, containing all flags
    Raises:
      Error: if constraint is not satisfied.
    """
    param = self._GetInputToCheckerFunction(flag_values)
    if not self.checker(param):
      raise Error(self.message)

  def GetFlagsNames(self):
    """Return the names of the flags checked by this validator.

    Returns:
      [string], names of the flags
    """
    raise NotImplementedError('This method should be overloaded')

  def PrintFlagsWithValues(self, flag_values):
    raise NotImplementedError('This method should be overloaded')

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues, containing all flags.
    Returns:
      Return type depends on the specific validator.
    """
    raise NotImplementedError('This method should be overloaded')


class SimpleValidator(Validator):
  """Validator behind RegisterValidator() method.

  Validates that a single flag passes its checker function. The checker function
  takes the flag value and returns True (if value looks fine) or, if flag value
  is not valid, either returns False or raises an Exception."""
  def __init__(self, flag_name, checker, message):
    """Constructor.

    Args:
      flag_name: string, name of the flag.
      checker: function to verify the validator.
        input  - value of the corresponding flag (string, boolean, etc).
        output - Boolean. Must return True if validator constraint is satisfied.
          If constraint is not satisfied, it should either return False or
          raise Error.
      message: string, error message to be shown to the user if validator's
        condition is not satisfied
    """
    super(SimpleValidator, self).__init__(checker, message)
    self.flag_name = flag_name

  def GetFlagsNames(self):
    return [self.flag_name]

  def PrintFlagsWithValues(self, flag_values):
    return 'flag --%s=%s' % (self.flag_name, flag_values[self.flag_name].value)

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues
    Returns:
      value of the corresponding flag.
    """
    return flag_values[self.flag_name].value


class DictionaryValidator(Validator):
  """Validator behind RegisterDictionaryValidator method.

  Validates that flag values pass their common checker function. The checker
  function takes flag values and returns True (if values look fine) or,
  if values are not valid, either returns False or raises an Exception.
  """
  def __init__(self, flag_names, checker, message):
    """Constructor.

    Args:
      flag_names: [string], containing names of the flags used by checker.
      checker: function to verify the validator.
        input  - dictionary, with keys() being flag_names, and value for each
          key being the value of the corresponding flag (string, boolean, etc).
        output - Boolean. Must return True if validator constraint is satisfied.
          If constraint is not satisfied, it should either return False or
          raise Error.
      message: string, error message to be shown to the user if validator's
        condition is not satisfied
    """
    super(DictionaryValidator, self).__init__(checker, message)
    self.flag_names = flag_names

  def _GetInputToCheckerFunction(self, flag_values):
    """Given flag values, construct the input to be given to checker.

    Args:
      flag_values: gflags.FlagValues
    Returns:
      dictionary, with keys() being self.lag_names, and value for each key
        being the value of the corresponding flag (string, boolean, etc).
    """
    return dict([key, flag_values[key].value] for key in self.flag_names)

  def PrintFlagsWithValues(self, flag_values):
    prefix = 'flags '
    flags_with_values = []
    for key in self.flag_names:
      flags_with_values.append('%s=%s' % (key, flag_values[key].value))
    return prefix + ', '.join(flags_with_values)

  def GetFlagsNames(self):
    return self.flag_names

########NEW FILE########
__FILENAME__ = module_bar
#!/usr/bin/env python

# Copyright (c) 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


"""Auxiliary module for testing gflags.py.

The purpose of this module is to define a few flags.  We want to make
sure the unit tests for gflags.py involve more than one module.
"""

__author__ = 'salcianu@google.com (Alex Salcianu)'

__pychecker__ = 'no-local'  # for unittest

import gflags

FLAGS = gflags.FLAGS


def DefineFlags(flag_values=FLAGS):
  """Defines some flags.

  Args:
    flag_values: The FlagValues object we want to register the flags
      with.
  """
  # The 'tmod_bar_' prefix (short for 'test_module_bar') ensures there
  # is no name clash with the existing flags.
  gflags.DEFINE_boolean('tmod_bar_x', True, 'Boolean flag.',
                       flag_values=flag_values)
  gflags.DEFINE_string('tmod_bar_y', 'default', 'String flag.',
                      flag_values=flag_values)
  gflags.DEFINE_boolean('tmod_bar_z', False,
                       'Another boolean flag from module bar.',
                       flag_values=flag_values)
  gflags.DEFINE_integer('tmod_bar_t', 4, 'Sample int flag.',
                       flag_values=flag_values)
  gflags.DEFINE_integer('tmod_bar_u', 5, 'Sample int flag.',
                       flag_values=flag_values)
  gflags.DEFINE_integer('tmod_bar_v', 6, 'Sample int flag.',
                       flag_values=flag_values)


def RemoveOneFlag(flag_name, flag_values=FLAGS):
  """Removes the definition of one flag from gflags.FLAGS.

  Note: if the flag is not defined in gflags.FLAGS, this function does
  not do anything (in particular, it does not raise any exception).

  Motivation: We use this function for cleanup *after* a test: if
  there was a failure during a test and not all flags were declared,
  we do not want the cleanup code to crash.

  Args:
    flag_name: A string, the name of the flag to delete.
    flag_values: The FlagValues object we remove the flag from.
  """
  if flag_name in flag_values.FlagDict():
    flag_values.__delattr__(flag_name)


def NamesOfDefinedFlags():
  """Returns: List of names of the flags declared in this module."""
  return ['tmod_bar_x',
          'tmod_bar_y',
          'tmod_bar_z',
          'tmod_bar_t',
          'tmod_bar_u',
          'tmod_bar_v']


def RemoveFlags(flag_values=FLAGS):
  """Deletes the flag definitions done by the above DefineFlags().

  Args:
    flag_values: The FlagValues object we remove the flags from.
  """
  for flag_name in NamesOfDefinedFlags():
    RemoveOneFlag(flag_name, flag_values=flag_values)


def GetModuleName():
  """Uses gflags._GetCallingModule() to return the name of this module.

  For checking that _GetCallingModule works as expected.

  Returns:
    A string, the name of this module.
  """
  # Calling the protected _GetCallingModule generates a lint warning,
  # but we do not have any other alternative to test that function.
  return gflags._GetCallingModule()


def ExecuteCode(code, global_dict):
  """Executes some code in a given global environment.

  For testing of _GetCallingModule.

  Args:
    code: A string, the code to be executed.
    global_dict: A dictionary, the global environment that code should
      be executed in.
  """
  # Indeed, using exec generates a lint warning.  But some user code
  # actually uses exec, and we have to test for it ...
  exec code in global_dict

########NEW FILE########
__FILENAME__ = module_baz
#!/usr/bin/env python

# Copyright (c) 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Auxiliary module for testing gflags.py.

The purpose of this module is to test the behavior of flags that are defined
before main() executes.
"""




import gflags

FLAGS = gflags.FLAGS

gflags.DEFINE_boolean('tmod_baz_x', True, 'Boolean flag.')

########NEW FILE########
__FILENAME__ = module_foo
#!/usr/bin/env python
#
# Copyright (c) 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Auxiliary module for testing gflags.py.

The purpose of this module is to define a few flags, and declare some
other flags as being important.  We want to make sure the unit tests
for gflags.py involve more than one module.
"""

__author__ = 'salcianu@google.com (Alex Salcianu)'

__pychecker__ = 'no-local'  # for unittest

import gflags
from flags_modules_for_testing import module_bar

FLAGS = gflags.FLAGS


DECLARED_KEY_FLAGS = ['tmod_bar_x', 'tmod_bar_z', 'tmod_bar_t',
                      # Special (not user-defined) flag:
                      'flagfile']


def DefineFlags(flag_values=FLAGS):
  """Defines a few flags."""
  module_bar.DefineFlags(flag_values=flag_values)
  # The 'tmod_foo_' prefix (short for 'test_module_foo') ensures that we
  # have no name clash with existing flags.
  gflags.DEFINE_boolean('tmod_foo_bool', True, 'Boolean flag from module foo.',
                       flag_values=flag_values)
  gflags.DEFINE_string('tmod_foo_str', 'default', 'String flag.',
                      flag_values=flag_values)
  gflags.DEFINE_integer('tmod_foo_int', 3, 'Sample int flag.',
                       flag_values=flag_values)


def DeclareKeyFlags(flag_values=FLAGS):
  """Declares a few key flags."""
  for flag_name in DECLARED_KEY_FLAGS:
    gflags.DECLARE_key_flag(flag_name, flag_values=flag_values)


def DeclareExtraKeyFlags(flag_values=FLAGS):
  """Declares some extra key flags."""
  gflags.ADOPT_module_key_flags(module_bar, flag_values=flag_values)


def NamesOfDefinedFlags():
  """Returns: list of names of flags defined by this module."""
  return ['tmod_foo_bool', 'tmod_foo_str', 'tmod_foo_int']


def NamesOfDeclaredKeyFlags():
  """Returns: list of names of key flags for this module."""
  return NamesOfDefinedFlags() + DECLARED_KEY_FLAGS


def NamesOfDeclaredExtraKeyFlags():
  """Returns the list of names of additional key flags for this module.

  These are the flags that became key for this module only as a result
  of a call to DeclareExtraKeyFlags() above.  I.e., the flags declared
  by module_bar, that were not already declared as key for this
  module.

  Returns:
    The list of names of additional key flags for this module.
  """
  names_of_extra_key_flags = list(module_bar.NamesOfDefinedFlags())
  for flag_name in NamesOfDeclaredKeyFlags():
    while flag_name in names_of_extra_key_flags:
      names_of_extra_key_flags.remove(flag_name)
  return names_of_extra_key_flags


def RemoveFlags(flag_values=FLAGS):
  """Deletes the flag definitions done by the above DefineFlags()."""
  for flag_name in NamesOfDefinedFlags():
    module_bar.RemoveOneFlag(flag_name, flag_values=flag_values)
  module_bar.RemoveFlags(flag_values=flag_values)


def GetModuleName():
  """Uses gflags._GetCallingModule() to return the name of this module.

  For checking that _GetCallingModule works as expected.

  Returns:
    A string, the name of this module.
  """
  # Calling the protected _GetCallingModule generates a lint warning,
  # but we do not have any other alternative to test that function.
  return gflags._GetCallingModule()


def DuplicateFlags(flagnames=None):
  """Returns a new FlagValues object with the requested flagnames.

  Used to test DuplicateFlagError detection.

  Args:
    flagnames: str, A list of flag names to create.

  Returns:
    A FlagValues object with one boolean flag for each name in flagnames.
  """
  flag_values = gflags.FlagValues()
  for name in flagnames:
    gflags.DEFINE_boolean(name, False, 'Flag named %s' % (name,),
                         flag_values=flag_values)
  return flag_values

########NEW FILE########
__FILENAME__ = gflags_googletest
#!/usr/bin/env python

# Copyright (c) 2011, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Some simple additions to the unittest framework useful for gflags testing."""



import re
import unittest


def Sorted(lst):
  """Equivalent of sorted(), but not dependent on python version."""
  sorted_list = lst[:]
  sorted_list.sort()
  return sorted_list


def MultiLineEqual(expected, actual):
  """Returns True if expected == actual, or returns False and logs."""
  if actual == expected:
    return True

  print "Error: FLAGS.MainModuleHelp() didn't return the expected result."
  print "Got:"
  print actual
  print "[End of got]"

  actual_lines = actual.split("\n")
  expected_lines = expected.split("\n")

  num_actual_lines = len(actual_lines)
  num_expected_lines = len(expected_lines)

  if num_actual_lines != num_expected_lines:
    print "Number of actual lines = %d, expected %d" % (
        num_actual_lines, num_expected_lines)

  num_to_match = min(num_actual_lines, num_expected_lines)

  for i in range(num_to_match):
    if actual_lines[i] != expected_lines[i]:
      print "One discrepancy: Got:"
      print actual_lines[i]
      print "Expected:"
      print expected_lines[i]
      break
  else:
    # If we got here, found no discrepancy, print first new line.
    if num_actual_lines > num_expected_lines:
      print "New help line:"
      print actual_lines[num_expected_lines]
    elif num_expected_lines > num_actual_lines:
      print "Missing expected help line:"
      print expected_lines[num_actual_lines]
    else:
      print "Bug in this test -- discrepancy detected but not found."

  return False


class TestCase(unittest.TestCase):
  def assertListEqual(self, list1, list2, msg=None):
    """Asserts that, when sorted, list1 and list2 are identical."""
    # This exists in python 2.7, but not previous versions.  Use the
    # built-in version if possible.
    if hasattr(unittest.TestCase, "assertListEqual"):
      unittest.TestCase.assertListEqual(self, Sorted(list1), Sorted(list2), msg)
    else:
      self.assertEqual(Sorted(list1), Sorted(list2), msg)

  def assertMultiLineEqual(self, expected, actual, msg=None):
    # This exists in python 2.7, but not previous versions.  Use the
    # built-in version if possible.
    if hasattr(unittest.TestCase, "assertMultiLineEqual"):
      unittest.TestCase.assertMultiLineEqual(self, expected, actual, msg)
    else:
      self.assertTrue(MultiLineEqual(expected, actual), msg)

  def assertRaisesWithRegexpMatch(self, exception, regexp, fn, *args, **kwargs):
    try:
      fn(*args, **kwargs)
    except exception, why:
      self.assertTrue(re.search(regexp, str(why)),
                      "'%s' does not match '%s'" % (regexp, why))
      return
    self.fail(exception.__name__ + " not raised")


def main():
  unittest.main()

########NEW FILE########
__FILENAME__ = gflags_helpxml_test
#!/usr/bin/env python

# Copyright (c) 2009, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Unit tests for the XML-format help generated by the gflags.py module."""

__author__ = 'salcianu@google.com (Alex Salcianu)'


import string
import StringIO
import sys
import xml.dom.minidom
import xml.sax.saxutils
import gflags_googletest as googletest
import gflags
from flags_modules_for_testing import module_bar


class _MakeXMLSafeTest(googletest.TestCase):

  def _Check(self, s, expected_output):
    self.assertEqual(gflags._MakeXMLSafe(s), expected_output)

  def testMakeXMLSafe(self):
    self._Check('plain text', 'plain text')
    self._Check('(x < y) && (a >= b)',
                '(x &lt; y) &amp;&amp; (a &gt;= b)')
    # Some characters with ASCII code < 32 are illegal in XML 1.0 and
    # are removed by us.  However, '\n', '\t', and '\r' are legal.
    self._Check('\x09\x0btext \x02 with\x0dsome \x08 good & bad chars',
                '\ttext  with\rsome  good &amp; bad chars')


def _ListSeparatorsInXMLFormat(separators, indent=''):
  """Generates XML encoding of a list of list separators.

  Args:
    separators: A list of list separators.  Usually, this should be a
      string whose characters are the valid list separators, e.g., ','
      means that both comma (',') and space (' ') are valid list
      separators.
    indent: A string that is added at the beginning of each generated
      XML element.

  Returns:
    A string.
  """
  result = ''
  separators = list(separators)
  separators.sort()
  for sep_char in separators:
    result += ('%s<list_separator>%s</list_separator>\n' %
               (indent, repr(sep_char)))
  return result


class WriteFlagHelpInXMLFormatTest(googletest.TestCase):
  """Test the XML-format help for a single flag at a time.

  There is one test* method for each kind of DEFINE_* declaration.
  """

  def setUp(self):
    # self.fv is a FlagValues object, just like gflags.FLAGS.  Each
    # test registers one flag with this FlagValues.
    self.fv = gflags.FlagValues()

  def _CheckFlagHelpInXML(self, flag_name, module_name,
                          expected_output, is_key=False):
    # StringIO.StringIO is a file object that writes into a memory string.
    sio = StringIO.StringIO()
    flag_obj = self.fv[flag_name]
    flag_obj.WriteInfoInXMLFormat(sio, module_name, is_key=is_key, indent=' ')
    self.assertMultiLineEqual(sio.getvalue(), expected_output)
    sio.close()

  def testFlagHelpInXML_Int(self):
    gflags.DEFINE_integer('index', 17, 'An integer flag', flag_values=self.fv)
    expected_output_pattern = (
        ' <flag>\n'
        '   <file>module.name</file>\n'
        '   <name>index</name>\n'
        '   <meaning>An integer flag</meaning>\n'
        '   <default>17</default>\n'
        '   <current>%d</current>\n'
        '   <type>int</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('index', 'module.name',
                             expected_output_pattern % 17)
    # Check that the output is correct even when the current value of
    # a flag is different from the default one.
    self.fv['index'].value = 20
    self._CheckFlagHelpInXML('index', 'module.name',
                             expected_output_pattern % 20)

  def testFlagHelpInXML_IntWithBounds(self):
    gflags.DEFINE_integer('nb_iters', 17, 'An integer flag',
                         lower_bound=5, upper_bound=27,
                         flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <key>yes</key>\n'
        '   <file>module.name</file>\n'
        '   <name>nb_iters</name>\n'
        '   <meaning>An integer flag</meaning>\n'
        '   <default>17</default>\n'
        '   <current>17</current>\n'
        '   <type>int</type>\n'
        '   <lower_bound>5</lower_bound>\n'
        '   <upper_bound>27</upper_bound>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('nb_iters', 'module.name',
                             expected_output, is_key=True)

  def testFlagHelpInXML_String(self):
    gflags.DEFINE_string('file_path', '/path/to/my/dir', 'A test string flag.',
                        flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>simple_module</file>\n'
        '   <name>file_path</name>\n'
        '   <meaning>A test string flag.</meaning>\n'
        '   <default>/path/to/my/dir</default>\n'
        '   <current>/path/to/my/dir</current>\n'
        '   <type>string</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('file_path', 'simple_module',
                             expected_output)

  def testFlagHelpInXML_StringWithXMLIllegalChars(self):
    gflags.DEFINE_string('file_path', '/path/to/\x08my/dir',
                        'A test string flag.', flag_values=self.fv)
    # '\x08' is not a legal character in XML 1.0 documents.  Our
    # current code purges such characters from the generated XML.
    expected_output = (
        ' <flag>\n'
        '   <file>simple_module</file>\n'
        '   <name>file_path</name>\n'
        '   <meaning>A test string flag.</meaning>\n'
        '   <default>/path/to/my/dir</default>\n'
        '   <current>/path/to/my/dir</current>\n'
        '   <type>string</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('file_path', 'simple_module',
                             expected_output)

  def testFlagHelpInXML_Boolean(self):
    gflags.DEFINE_boolean('use_hack', False, 'Use performance hack',
                         flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <key>yes</key>\n'
        '   <file>a_module</file>\n'
        '   <name>use_hack</name>\n'
        '   <meaning>Use performance hack</meaning>\n'
        '   <default>false</default>\n'
        '   <current>false</current>\n'
        '   <type>bool</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('use_hack', 'a_module',
                             expected_output, is_key=True)

  def testFlagHelpInXML_Enum(self):
    gflags.DEFINE_enum('cc_version', 'stable', ['stable', 'experimental'],
                      'Compiler version to use.', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>cc_version</name>\n'
        '   <meaning>&lt;stable|experimental&gt;: '
        'Compiler version to use.</meaning>\n'
        '   <default>stable</default>\n'
        '   <current>stable</current>\n'
        '   <type>string enum</type>\n'
        '   <enum_value>stable</enum_value>\n'
        '   <enum_value>experimental</enum_value>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('cc_version', 'tool', expected_output)

  def testFlagHelpInXML_CommaSeparatedList(self):
    gflags.DEFINE_list('files', 'a.cc,a.h,archive/old.zip',
                      'Files to process.', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>files</name>\n'
        '   <meaning>Files to process.</meaning>\n'
        '   <default>a.cc,a.h,archive/old.zip</default>\n'
        '   <current>[\'a.cc\', \'a.h\', \'archive/old.zip\']</current>\n'
        '   <type>comma separated list of strings</type>\n'
        '   <list_separator>\',\'</list_separator>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('files', 'tool', expected_output)

  def testListAsDefaultArgument_CommaSeparatedList(self):
    gflags.DEFINE_list('allow_users', ['alice', 'bob'],
                      'Users with access.', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>allow_users</name>\n'
        '   <meaning>Users with access.</meaning>\n'
        '   <default>alice,bob</default>\n'
        '   <current>[\'alice\', \'bob\']</current>\n'
        '   <type>comma separated list of strings</type>\n'
        '   <list_separator>\',\'</list_separator>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('allow_users', 'tool', expected_output)

  def testFlagHelpInXML_SpaceSeparatedList(self):
    gflags.DEFINE_spaceseplist('dirs', 'src libs bin',
                              'Directories to search.', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>dirs</name>\n'
        '   <meaning>Directories to search.</meaning>\n'
        '   <default>src libs bin</default>\n'
        '   <current>[\'src\', \'libs\', \'bin\']</current>\n'
        '   <type>whitespace separated list of strings</type>\n'
        'LIST_SEPARATORS'
        ' </flag>\n').replace('LIST_SEPARATORS',
                              _ListSeparatorsInXMLFormat(string.whitespace,
                                                         indent='   '))
    self._CheckFlagHelpInXML('dirs', 'tool', expected_output)

  def testFlagHelpInXML_MultiString(self):
    gflags.DEFINE_multistring('to_delete', ['a.cc', 'b.h'],
                             'Files to delete', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>to_delete</name>\n'
        '   <meaning>Files to delete;\n    '
        'repeat this option to specify a list of values</meaning>\n'
        '   <default>[\'a.cc\', \'b.h\']</default>\n'
        '   <current>[\'a.cc\', \'b.h\']</current>\n'
        '   <type>multi string</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('to_delete', 'tool', expected_output)

  def testFlagHelpInXML_MultiInt(self):
    gflags.DEFINE_multi_int('cols', [5, 7, 23],
                           'Columns to select', flag_values=self.fv)
    expected_output = (
        ' <flag>\n'
        '   <file>tool</file>\n'
        '   <name>cols</name>\n'
        '   <meaning>Columns to select;\n    '
        'repeat this option to specify a list of values</meaning>\n'
        '   <default>[5, 7, 23]</default>\n'
        '   <current>[5, 7, 23]</current>\n'
        '   <type>multi int</type>\n'
        ' </flag>\n')
    self._CheckFlagHelpInXML('cols', 'tool', expected_output)


# The next EXPECTED_HELP_XML_* constants are parts of a template for
# the expected XML output from WriteHelpInXMLFormatTest below.  When
# we assemble these parts into a single big string, we'll take into
# account the ordering between the name of the main module and the
# name of module_bar.  Next, we'll fill in the docstring for this
# module (%(usage_doc)s), the name of the main module
# (%(main_module_name)s) and the name of the module module_bar
# (%(module_bar_name)s).  See WriteHelpInXMLFormatTest below.
#
# NOTE: given the current implementation of _GetMainModule(), we
# already know the ordering between the main module and module_bar.
# However, there is no guarantee that _GetMainModule will never be
# changed in the future (especially since it's far from perfect).
EXPECTED_HELP_XML_START = """\
<?xml version="1.0"?>
<AllFlags>
  <program>gflags_helpxml_test.py</program>
  <usage>%(usage_doc)s</usage>
"""

EXPECTED_HELP_XML_FOR_FLAGS_FROM_MAIN_MODULE = """\
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>allow_users</name>
    <meaning>Users with access.</meaning>
    <default>alice,bob</default>
    <current>['alice', 'bob']</current>
    <type>comma separated list of strings</type>
    <list_separator>','</list_separator>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>cc_version</name>
    <meaning>&lt;stable|experimental&gt;: Compiler version to use.</meaning>
    <default>stable</default>
    <current>stable</current>
    <type>string enum</type>
    <enum_value>stable</enum_value>
    <enum_value>experimental</enum_value>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>cols</name>
    <meaning>Columns to select;
    repeat this option to specify a list of values</meaning>
    <default>[5, 7, 23]</default>
    <current>[5, 7, 23]</current>
    <type>multi int</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>dirs</name>
    <meaning>Directories to create.</meaning>
    <default>src libs bins</default>
    <current>['src', 'libs', 'bins']</current>
    <type>whitespace separated list of strings</type>
%(whitespace_separators)s  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>file_path</name>
    <meaning>A test string flag.</meaning>
    <default>/path/to/my/dir</default>
    <current>/path/to/my/dir</current>
    <type>string</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>files</name>
    <meaning>Files to process.</meaning>
    <default>a.cc,a.h,archive/old.zip</default>
    <current>['a.cc', 'a.h', 'archive/old.zip']</current>
    <type>comma separated list of strings</type>
    <list_separator>\',\'</list_separator>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>index</name>
    <meaning>An integer flag</meaning>
    <default>17</default>
    <current>17</current>
    <type>int</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>nb_iters</name>
    <meaning>An integer flag</meaning>
    <default>17</default>
    <current>17</current>
    <type>int</type>
    <lower_bound>5</lower_bound>
    <upper_bound>27</upper_bound>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>to_delete</name>
    <meaning>Files to delete;
    repeat this option to specify a list of values</meaning>
    <default>['a.cc', 'b.h']</default>
    <current>['a.cc', 'b.h']</current>
    <type>multi string</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(main_module_name)s</file>
    <name>use_hack</name>
    <meaning>Use performance hack</meaning>
    <default>false</default>
    <current>false</current>
    <type>bool</type>
  </flag>
"""

EXPECTED_HELP_XML_FOR_FLAGS_FROM_MODULE_BAR = """\
  <flag>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_t</name>
    <meaning>Sample int flag.</meaning>
    <default>4</default>
    <current>4</current>
    <type>int</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_u</name>
    <meaning>Sample int flag.</meaning>
    <default>5</default>
    <current>5</current>
    <type>int</type>
  </flag>
  <flag>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_v</name>
    <meaning>Sample int flag.</meaning>
    <default>6</default>
    <current>6</current>
    <type>int</type>
  </flag>
  <flag>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_x</name>
    <meaning>Boolean flag.</meaning>
    <default>true</default>
    <current>true</current>
    <type>bool</type>
  </flag>
  <flag>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_y</name>
    <meaning>String flag.</meaning>
    <default>default</default>
    <current>default</current>
    <type>string</type>
  </flag>
  <flag>
    <key>yes</key>
    <file>%(module_bar_name)s</file>
    <name>tmod_bar_z</name>
    <meaning>Another boolean flag from module bar.</meaning>
    <default>false</default>
    <current>false</current>
    <type>bool</type>
  </flag>
"""

EXPECTED_HELP_XML_END = """\
</AllFlags>
"""


class WriteHelpInXMLFormatTest(googletest.TestCase):
  """Big test of FlagValues.WriteHelpInXMLFormat, with several flags."""

  def testWriteHelpInXMLFormat(self):
    fv = gflags.FlagValues()
    # Since these flags are defined by the top module, they are all key.
    gflags.DEFINE_integer('index', 17, 'An integer flag', flag_values=fv)
    gflags.DEFINE_integer('nb_iters', 17, 'An integer flag',
                         lower_bound=5, upper_bound=27, flag_values=fv)
    gflags.DEFINE_string('file_path', '/path/to/my/dir', 'A test string flag.',
                        flag_values=fv)
    gflags.DEFINE_boolean('use_hack', False, 'Use performance hack',
                         flag_values=fv)
    gflags.DEFINE_enum('cc_version', 'stable', ['stable', 'experimental'],
                      'Compiler version to use.', flag_values=fv)
    gflags.DEFINE_list('files', 'a.cc,a.h,archive/old.zip',
                      'Files to process.', flag_values=fv)
    gflags.DEFINE_list('allow_users', ['alice', 'bob'],
                      'Users with access.', flag_values=fv)
    gflags.DEFINE_spaceseplist('dirs', 'src libs bins',
                              'Directories to create.', flag_values=fv)
    gflags.DEFINE_multistring('to_delete', ['a.cc', 'b.h'],
                             'Files to delete', flag_values=fv)
    gflags.DEFINE_multi_int('cols', [5, 7, 23],
                           'Columns to select', flag_values=fv)
    # Define a few flags in a different module.
    module_bar.DefineFlags(flag_values=fv)
    # And declare only a few of them to be key.  This way, we have
    # different kinds of flags, defined in different modules, and not
    # all of them are key flags.
    gflags.DECLARE_key_flag('tmod_bar_z', flag_values=fv)
    gflags.DECLARE_key_flag('tmod_bar_u', flag_values=fv)

    # Generate flag help in XML format in the StringIO sio.
    sio = StringIO.StringIO()
    fv.WriteHelpInXMLFormat(sio)

    # Check that we got the expected result.
    expected_output_template = EXPECTED_HELP_XML_START
    main_module_name = gflags._GetMainModule()
    module_bar_name = module_bar.__name__

    if main_module_name < module_bar_name:
      expected_output_template += EXPECTED_HELP_XML_FOR_FLAGS_FROM_MAIN_MODULE
      expected_output_template += EXPECTED_HELP_XML_FOR_FLAGS_FROM_MODULE_BAR
    else:
      expected_output_template += EXPECTED_HELP_XML_FOR_FLAGS_FROM_MODULE_BAR
      expected_output_template += EXPECTED_HELP_XML_FOR_FLAGS_FROM_MAIN_MODULE

    expected_output_template += EXPECTED_HELP_XML_END

    # XML representation of the whitespace list separators.
    whitespace_separators = _ListSeparatorsInXMLFormat(string.whitespace,
                                                       indent='    ')
    expected_output = (
        expected_output_template %
        {'usage_doc': sys.modules['__main__'].__doc__,
         'main_module_name': main_module_name,
         'module_bar_name': module_bar_name,
         'whitespace_separators': whitespace_separators})

    actual_output = sio.getvalue()
    self.assertMultiLineEqual(actual_output, expected_output)

    # Also check that our result is valid XML.  minidom.parseString
    # throws an xml.parsers.expat.ExpatError in case of an error.
    xml.dom.minidom.parseString(actual_output)


if __name__ == '__main__':
  googletest.main()

########NEW FILE########
__FILENAME__ = gflags_unittest
#!/usr/bin/env python

# Copyright (c) 2007, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"Unittest for gflags.py module"

__pychecker__ = "no-local" # for unittest


import cStringIO
import sys
import os
import shutil

import gflags
from flags_modules_for_testing import module_foo
from flags_modules_for_testing import module_bar
from flags_modules_for_testing import module_baz

FLAGS=gflags.FLAGS

import gflags_googletest as googletest

# TODO(csilvers): add a wrapper function around FLAGS(argv) that
# verifies the input is a list or tuple.  This avoids bugs where we
# make argv a string instead of a list, by mistake.

class FlagsUnitTest(googletest.TestCase):
  "Flags Unit Test"

  def setUp(self):
    # make sure we are using the old, stupid way of parsing flags.
    FLAGS.UseGnuGetOpt(False)

  def test_flags(self):

    ##############################################
    # Test normal usage with no (expected) errors.

    # Define flags
    number_test_framework_flags = len(FLAGS.RegisteredFlags())
    repeatHelp = "how many times to repeat (0-5)"
    gflags.DEFINE_integer("repeat", 4, repeatHelp,
                         lower_bound=0, short_name='r')
    gflags.DEFINE_string("name", "Bob", "namehelp")
    gflags.DEFINE_boolean("debug", 0, "debughelp")
    gflags.DEFINE_boolean("q", 1, "quiet mode")
    gflags.DEFINE_boolean("quack", 0, "superstring of 'q'")
    gflags.DEFINE_boolean("noexec", 1, "boolean flag with no as prefix")
    gflags.DEFINE_integer("x", 3, "how eXtreme to be")
    gflags.DEFINE_integer("l", 0x7fffffff00000000, "how long to be")
    gflags.DEFINE_list('letters', 'a,b,c', "a list of letters")
    gflags.DEFINE_list('numbers', [1, 2, 3], "a list of numbers")
    gflags.DEFINE_enum("kwery", None, ['who', 'what', 'why', 'where', 'when'],
                      "?")

    # Specify number of flags defined above.  The short_name defined
    # for 'repeat' counts as an extra flag.
    number_defined_flags = 11 + 1
    self.assertEqual(len(FLAGS.RegisteredFlags()),
                         number_defined_flags + number_test_framework_flags)

    assert FLAGS.repeat == 4, "integer default values not set:" + FLAGS.repeat
    assert FLAGS.name == 'Bob', "default values not set:" + FLAGS.name
    assert FLAGS.debug == 0, "boolean default values not set:" + FLAGS.debug
    assert FLAGS.q == 1, "boolean default values not set:" + FLAGS.q
    assert FLAGS.x == 3, "integer default values not set:" + FLAGS.x
    assert FLAGS.l == 0x7fffffff00000000, ("integer default values not set:"
                                           + FLAGS.l)
    assert FLAGS.letters == ['a', 'b', 'c'], ("list default values not set:"
                                              + FLAGS.letters)
    assert FLAGS.numbers == [1, 2, 3], ("list default values not set:"
                                        + FLAGS.numbers)
    assert FLAGS.kwery is None, ("enum default None value not set:"
                                  + FLAGS.kwery)

    flag_values = FLAGS.FlagValuesDict()
    assert flag_values['repeat'] == 4
    assert flag_values['name'] == 'Bob'
    assert flag_values['debug'] == 0
    assert flag_values['r'] == 4       # short for repeat
    assert flag_values['q'] == 1
    assert flag_values['quack'] == 0
    assert flag_values['x'] == 3
    assert flag_values['l'] == 0x7fffffff00000000
    assert flag_values['letters'] == ['a', 'b', 'c']
    assert flag_values['numbers'] == [1, 2, 3]
    assert flag_values['kwery'] is None

    # Verify string form of defaults
    assert FLAGS['repeat'].default_as_str == "'4'"
    assert FLAGS['name'].default_as_str == "'Bob'"
    assert FLAGS['debug'].default_as_str == "'false'"
    assert FLAGS['q'].default_as_str == "'true'"
    assert FLAGS['quack'].default_as_str == "'false'"
    assert FLAGS['noexec'].default_as_str == "'true'"
    assert FLAGS['x'].default_as_str == "'3'"
    assert FLAGS['l'].default_as_str == "'9223372032559808512'"
    assert FLAGS['letters'].default_as_str == "'a,b,c'"
    assert FLAGS['numbers'].default_as_str == "'1,2,3'"

    # Verify that the iterator for flags yields all the keys
    keys = list(FLAGS)
    keys.sort()
    reg_flags = FLAGS.RegisteredFlags()
    reg_flags.sort()
    self.assertEqual(keys, reg_flags)

    # Parse flags
    # .. empty command line
    argv = ('./program',)
    argv = FLAGS(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"

    # .. non-empty command line
    argv = ('./program', '--debug', '--name=Bob', '-q', '--x=8')
    argv = FLAGS(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert FLAGS['debug'].present == 1
    FLAGS['debug'].present = 0 # Reset
    assert FLAGS['name'].present == 1
    FLAGS['name'].present = 0 # Reset
    assert FLAGS['q'].present == 1
    FLAGS['q'].present = 0 # Reset
    assert FLAGS['x'].present == 1
    FLAGS['x'].present = 0 # Reset

    # Flags list
    self.assertEqual(len(FLAGS.RegisteredFlags()),
                     number_defined_flags + number_test_framework_flags)
    assert 'name' in FLAGS.RegisteredFlags()
    assert 'debug' in FLAGS.RegisteredFlags()
    assert 'repeat' in FLAGS.RegisteredFlags()
    assert 'r' in FLAGS.RegisteredFlags()
    assert 'q' in FLAGS.RegisteredFlags()
    assert 'quack' in FLAGS.RegisteredFlags()
    assert 'x' in FLAGS.RegisteredFlags()
    assert 'l' in FLAGS.RegisteredFlags()
    assert 'letters' in FLAGS.RegisteredFlags()
    assert 'numbers' in FLAGS.RegisteredFlags()

    # has_key
    assert FLAGS.has_key('name')
    assert not FLAGS.has_key('name2')
    assert 'name' in FLAGS
    assert 'name2' not in FLAGS

    # try deleting a flag
    del FLAGS.r
    self.assertEqual(len(FLAGS.RegisteredFlags()),
                     number_defined_flags - 1 + number_test_framework_flags)
    assert not 'r' in FLAGS.RegisteredFlags()

    # .. command line with extra stuff
    argv = ('./program', '--debug', '--name=Bob', 'extra')
    argv = FLAGS(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"
    assert FLAGS['debug'].present == 1
    FLAGS['debug'].present = 0 # Reset
    assert FLAGS['name'].present == 1
    FLAGS['name'].present = 0 # Reset

    # Test reset
    argv = ('./program', '--debug')
    argv = FLAGS(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0] == './program', "program name not preserved"
    assert FLAGS['debug'].present == 1
    assert FLAGS['debug'].value
    FLAGS.Reset()
    assert FLAGS['debug'].present == 0
    assert not FLAGS['debug'].value

    # Test that reset restores default value when default value is None.
    argv = ('./program', '--kwery=who')
    argv = FLAGS(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0] == './program', "program name not preserved"
    assert FLAGS['kwery'].present == 1
    assert FLAGS['kwery'].value == 'who'
    FLAGS.Reset()
    assert FLAGS['kwery'].present == 0
    assert FLAGS['kwery'].value == None

    # Test integer argument passing
    argv = ('./program', '--x', '0x12345')
    argv = FLAGS(argv)
    self.assertEquals(FLAGS.x, 0x12345)
    self.assertEquals(type(FLAGS.x), int)

    argv = ('./program', '--x', '0x1234567890ABCDEF1234567890ABCDEF')
    argv = FLAGS(argv)
    self.assertEquals(FLAGS.x, 0x1234567890ABCDEF1234567890ABCDEF)
    self.assertEquals(type(FLAGS.x), long)

    # Treat 0-prefixed parameters as base-10, not base-8
    argv = ('./program', '--x', '012345')
    argv = FLAGS(argv)
    self.assertEquals(FLAGS.x, 12345)
    self.assertEquals(type(FLAGS.x), int)

    argv = ('./program', '--x', '0123459')
    argv = FLAGS(argv)
    self.assertEquals(FLAGS.x, 123459)
    self.assertEquals(type(FLAGS.x), int)

    argv = ('./program', '--x', '0x123efg')
    try:
      argv = FLAGS(argv)
      raise AssertionError("failed to detect invalid hex argument")
    except gflags.IllegalFlagValue:
      pass

    # Test boolean argument parsing
    gflags.DEFINE_boolean("test0", None, "test boolean parsing")
    argv = ('./program', '--notest0')
    argv = FLAGS(argv)
    assert FLAGS.test0 == 0

    gflags.DEFINE_boolean("test1", None, "test boolean parsing")
    argv = ('./program', '--test1')
    argv = FLAGS(argv)
    assert FLAGS.test1 == 1

    FLAGS.test0 = None
    argv = ('./program', '--test0=false')
    argv = FLAGS(argv)
    assert FLAGS.test0 == 0

    FLAGS.test1 = None
    argv = ('./program', '--test1=true')
    argv = FLAGS(argv)
    assert FLAGS.test1 == 1

    FLAGS.test0 = None
    argv = ('./program', '--test0=0')
    argv = FLAGS(argv)
    assert FLAGS.test0 == 0

    FLAGS.test1 = None
    argv = ('./program', '--test1=1')
    argv = FLAGS(argv)
    assert FLAGS.test1 == 1

    # Test booleans that already have 'no' as a prefix
    FLAGS.noexec = None
    argv = ('./program', '--nonoexec', '--name', 'Bob')
    argv = FLAGS(argv)
    assert FLAGS.noexec == 0

    FLAGS.noexec = None
    argv = ('./program', '--name', 'Bob', '--noexec')
    argv = FLAGS(argv)
    assert FLAGS.noexec == 1

    # Test unassigned booleans
    gflags.DEFINE_boolean("testnone", None, "test boolean parsing")
    argv = ('./program',)
    argv = FLAGS(argv)
    assert FLAGS.testnone == None

    # Test get with default
    gflags.DEFINE_boolean("testget1", None, "test parsing with defaults")
    gflags.DEFINE_boolean("testget2", None, "test parsing with defaults")
    gflags.DEFINE_boolean("testget3", None, "test parsing with defaults")
    gflags.DEFINE_integer("testget4", None, "test parsing with defaults")
    argv = ('./program','--testget1','--notestget2')
    argv = FLAGS(argv)
    assert FLAGS.get('testget1', 'foo') == 1
    assert FLAGS.get('testget2', 'foo') == 0
    assert FLAGS.get('testget3', 'foo') == 'foo'
    assert FLAGS.get('testget4', 'foo') == 'foo'

    # test list code
    lists = [['hello','moo','boo','1'],
             [],]

    gflags.DEFINE_list('testlist', '', 'test lists parsing')
    gflags.DEFINE_spaceseplist('testspacelist', '', 'tests space lists parsing')

    for name, sep in (('testlist', ','), ('testspacelist', ' '),
                      ('testspacelist', '\n')):
      for lst in lists:
        argv = ('./program', '--%s=%s' % (name, sep.join(lst)))
        argv = FLAGS(argv)
        self.assertEquals(getattr(FLAGS, name), lst)

    # Test help text
    flagsHelp = str(FLAGS)
    assert flagsHelp.find("repeat") != -1, "cannot find flag in help"
    assert flagsHelp.find(repeatHelp) != -1, "cannot find help string in help"

    # Test flag specified twice
    argv = ('./program', '--repeat=4', '--repeat=2', '--debug', '--nodebug')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('repeat', None), 2)
    self.assertEqual(FLAGS.get('debug', None), 0)

    # Test MultiFlag with single default value
    gflags.DEFINE_multistring('s_str', 'sing1',
                             'string option that can occur multiple times',
                             short_name='s')
    self.assertEqual(FLAGS.get('s_str', None), [ 'sing1', ])

    # Test MultiFlag with list of default values
    multi_string_defs = [ 'def1', 'def2', ]
    gflags.DEFINE_multistring('m_str', multi_string_defs,
                             'string option that can occur multiple times',
                             short_name='m')
    self.assertEqual(FLAGS.get('m_str', None), multi_string_defs)

    # Test flag specified multiple times with a MultiFlag
    argv = ('./program', '--m_str=str1', '-m', 'str2')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('m_str', None), [ 'str1', 'str2', ])

    # Test single-letter flags; should support both single and double dash
    argv = ('./program', '-q', '-x8')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('q', None), 1)
    self.assertEqual(FLAGS.get('x', None), 8)

    argv = ('./program', '--q', '--x', '9', '--noqu')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('q', None), 1)
    self.assertEqual(FLAGS.get('x', None), 9)
    # --noqu should match '--noquack since it's a unique prefix
    self.assertEqual(FLAGS.get('quack', None), 0)

    argv = ('./program', '--noq', '--x=10', '--qu')
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.get('q', None), 0)
    self.assertEqual(FLAGS.get('x', None), 10)
    self.assertEqual(FLAGS.get('quack', None), 1)

    ####################################
    # Test flag serialization code:

    oldtestlist = FLAGS.testlist
    oldtestspacelist = FLAGS.testspacelist

    argv = ('./program',
            FLAGS['test0'].Serialize(),
            FLAGS['test1'].Serialize(),
            FLAGS['testnone'].Serialize(),
            FLAGS['s_str'].Serialize())
    argv = FLAGS(argv)
    self.assertEqual(FLAGS['test0'].Serialize(), '--notest0')
    self.assertEqual(FLAGS['test1'].Serialize(), '--test1')
    self.assertEqual(FLAGS['testnone'].Serialize(), '')
    self.assertEqual(FLAGS['s_str'].Serialize(), '--s_str=sing1')

    testlist1 = ['aa', 'bb']
    testspacelist1 = ['aa', 'bb', 'cc']
    FLAGS.testlist = list(testlist1)
    FLAGS.testspacelist = list(testspacelist1)
    argv = ('./program',
            FLAGS['testlist'].Serialize(),
            FLAGS['testspacelist'].Serialize())
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.testlist, testlist1)
    self.assertEqual(FLAGS.testspacelist, testspacelist1)

    testlist1 = ['aa some spaces', 'bb']
    testspacelist1 = ['aa', 'bb,some,commas,', 'cc']
    FLAGS.testlist = list(testlist1)
    FLAGS.testspacelist = list(testspacelist1)
    argv = ('./program',
            FLAGS['testlist'].Serialize(),
            FLAGS['testspacelist'].Serialize())
    argv = FLAGS(argv)
    self.assertEqual(FLAGS.testlist, testlist1)
    self.assertEqual(FLAGS.testspacelist, testspacelist1)

    FLAGS.testlist = oldtestlist
    FLAGS.testspacelist = oldtestspacelist

    ####################################
    # Test flag-update:

    def ArgsString():
      flagnames = FLAGS.RegisteredFlags()

      flagnames.sort()
      nonbool_flags = ['--%s %s' % (name, FLAGS.get(name, None))
                       for name in flagnames
                       if not isinstance(FLAGS[name], gflags.BooleanFlag)]

      truebool_flags = ['--%s' % (name)
                        for name in flagnames
                        if isinstance(FLAGS[name], gflags.BooleanFlag) and
                          FLAGS.get(name, None)]
      falsebool_flags = ['--no%s' % (name)
                         for name in flagnames
                         if isinstance(FLAGS[name], gflags.BooleanFlag) and
                           not FLAGS.get(name, None)]
      return ' '.join(nonbool_flags + truebool_flags + falsebool_flags)

    argv = ('./program', '--repeat=3', '--name=giants', '--nodebug')

    FLAGS(argv)
    self.assertEqual(FLAGS.get('repeat', None), 3)
    self.assertEqual(FLAGS.get('name', None), 'giants')
    self.assertEqual(FLAGS.get('debug', None), 0)
    self.assertEqual(ArgsString(),
      "--kwery None "
      "--l 9223372032559808512 "
      "--letters ['a', 'b', 'c'] "
      "--m ['str1', 'str2'] --m_str ['str1', 'str2'] "
      "--name giants "
      "--numbers [1, 2, 3] "
      "--repeat 3 "
      "--s ['sing1'] --s_str ['sing1'] "
      ""
      ""
      "--testget4 None --testlist [] "
      "--testspacelist [] --x 10 "
      "--noexec --quack "
      "--test1 "
      "--testget1 --tmod_baz_x "
      "--no? --nodebug --nohelp --nohelpshort --nohelpxml --noq "
      ""
      "--notest0 --notestget2 --notestget3 --notestnone")

    argv = ('./program', '--debug', '--m_str=upd1', '-s', 'upd2')
    FLAGS(argv)
    self.assertEqual(FLAGS.get('repeat', None), 3)
    self.assertEqual(FLAGS.get('name', None), 'giants')
    self.assertEqual(FLAGS.get('debug', None), 1)

    # items appended to existing non-default value lists for --m/--m_str
    # new value overwrites default value (not appended to it) for --s/--s_str
    self.assertEqual(ArgsString(),
      "--kwery None "
      "--l 9223372032559808512 "
      "--letters ['a', 'b', 'c'] "
      "--m ['str1', 'str2', 'upd1'] "
      "--m_str ['str1', 'str2', 'upd1'] "
      "--name giants "
      "--numbers [1, 2, 3] "
      "--repeat 3 "
      "--s ['upd2'] --s_str ['upd2'] "
      ""
      ""
      "--testget4 None --testlist [] "
      "--testspacelist [] --x 10 "
      "--debug --noexec --quack "
      "--test1 "
      "--testget1 --tmod_baz_x "
      "--no? --nohelp --nohelpshort --nohelpxml --noq "
      ""
      "--notest0 --notestget2 --notestget3 --notestnone")

    ####################################
    # Test all kind of error conditions.

    # Duplicate flag detection
    try:
      gflags.DEFINE_boolean("run", 0, "runhelp", short_name='q')
      raise AssertionError("duplicate flag detection failed")
    except gflags.DuplicateFlag:
      pass

    # Duplicate short flag detection
    try:
      gflags.DEFINE_boolean("zoom1", 0, "runhelp z1", short_name='z')
      gflags.DEFINE_boolean("zoom2", 0, "runhelp z2", short_name='z')
      raise AssertionError("duplicate short flag detection failed")
    except gflags.DuplicateFlag, e:
      self.assertTrue("The flag 'z' is defined twice. " in e.args[0])
      self.assertTrue("First from" in e.args[0])
      self.assertTrue(", Second from" in e.args[0])

    # Duplicate mixed flag detection
    try:
      gflags.DEFINE_boolean("short1", 0, "runhelp s1", short_name='s')
      gflags.DEFINE_boolean("s", 0, "runhelp s2")
      raise AssertionError("duplicate mixed flag detection failed")
    except gflags.DuplicateFlag, e:
      self.assertTrue("The flag 's' is defined twice. " in e.args[0])
      self.assertTrue("First from" in e.args[0])
      self.assertTrue(", Second from" in e.args[0])

    # Check that duplicate flag detection detects definition sites
    # correctly.
    flagnames = ["repeated"]
    original_flags = gflags.FlagValues()
    gflags.DEFINE_boolean(flagnames[0], False, "Flag about to be repeated.",
                         flag_values=original_flags)
    duplicate_flags = module_foo.DuplicateFlags(flagnames)
    try:
      original_flags.AppendFlagValues(duplicate_flags)
    except gflags.DuplicateFlagError, e:
      self.assertTrue("flags_unittest" in str(e))
      self.assertTrue("module_foo" in str(e))

    # Make sure allow_override works
    try:
      gflags.DEFINE_boolean("dup1", 0, "runhelp d11", short_name='u',
                           allow_override=0)
      flag = FLAGS.FlagDict()['dup1']
      self.assertEqual(flag.default, 0)

      gflags.DEFINE_boolean("dup1", 1, "runhelp d12", short_name='u',
                           allow_override=1)
      flag = FLAGS.FlagDict()['dup1']
      self.assertEqual(flag.default, 1)
    except gflags.DuplicateFlag:
      raise AssertionError("allow_override did not permit a flag duplication")

    # Make sure allow_override works
    try:
      gflags.DEFINE_boolean("dup2", 0, "runhelp d21", short_name='u',
                           allow_override=1)
      flag = FLAGS.FlagDict()['dup2']
      self.assertEqual(flag.default, 0)

      gflags.DEFINE_boolean("dup2", 1, "runhelp d22", short_name='u',
                           allow_override=0)
      flag = FLAGS.FlagDict()['dup2']
      self.assertEqual(flag.default, 1)
    except gflags.DuplicateFlag:
      raise AssertionError("allow_override did not permit a flag duplication")

    # Make sure allow_override doesn't work with None default
    try:
      gflags.DEFINE_boolean("dup3", 0, "runhelp d31", short_name='u3',
                           allow_override=0)
      flag = FLAGS.FlagDict()['dup3']
      self.assertEqual(flag.default, 0)

      gflags.DEFINE_boolean("dup3", None, "runhelp d32", short_name='u3',
                           allow_override=1)
      raise AssertionError('Cannot override a flag with a default of None')
    except gflags.DuplicateFlagCannotPropagateNoneToSwig:
      pass

    # Make sure that re-importing a module does not cause a DuplicateFlagError
    # to be raised.
    try:
      sys.modules.pop(
          "flags_modules_for_testing.module_baz")
      import flags_modules_for_testing.module_baz
    except gflags.DuplicateFlagError:
      raise AssertionError("Module reimport caused flag duplication error")

    # Make sure that when we override, the help string gets updated correctly
    gflags.DEFINE_boolean("dup3", 0, "runhelp d31", short_name='u',
                         allow_override=1)
    gflags.DEFINE_boolean("dup3", 1, "runhelp d32", short_name='u',
                         allow_override=1)
    self.assert_(str(FLAGS).find('runhelp d31') == -1)
    self.assert_(str(FLAGS).find('runhelp d32') != -1)

    # Make sure AppendFlagValues works
    new_flags = gflags.FlagValues()
    gflags.DEFINE_boolean("new1", 0, "runhelp n1", flag_values=new_flags)
    gflags.DEFINE_boolean("new2", 0, "runhelp n2", flag_values=new_flags)
    self.assertEqual(len(new_flags.FlagDict()), 2)
    old_len = len(FLAGS.FlagDict())
    FLAGS.AppendFlagValues(new_flags)
    self.assertEqual(len(FLAGS.FlagDict())-old_len, 2)
    self.assertEqual("new1" in FLAGS.FlagDict(), True)
    self.assertEqual("new2" in FLAGS.FlagDict(), True)

    # Then test that removing those flags works
    FLAGS.RemoveFlagValues(new_flags)
    self.assertEqual(len(FLAGS.FlagDict()), old_len)
    self.assertFalse("new1" in FLAGS.FlagDict())
    self.assertFalse("new2" in FLAGS.FlagDict())

    # Make sure AppendFlagValues works with flags with shortnames.
    new_flags = gflags.FlagValues()
    gflags.DEFINE_boolean("new3", 0, "runhelp n3", flag_values=new_flags)
    gflags.DEFINE_boolean("new4", 0, "runhelp n4", flag_values=new_flags,
                         short_name="n4")
    self.assertEqual(len(new_flags.FlagDict()), 3)
    old_len = len(FLAGS.FlagDict())
    FLAGS.AppendFlagValues(new_flags)
    self.assertEqual(len(FLAGS.FlagDict())-old_len, 3)
    self.assertTrue("new3" in FLAGS.FlagDict())
    self.assertTrue("new4" in FLAGS.FlagDict())
    self.assertTrue("n4" in FLAGS.FlagDict())
    self.assertEqual(FLAGS.FlagDict()['n4'], FLAGS.FlagDict()['new4'])

    # Then test removing them
    FLAGS.RemoveFlagValues(new_flags)
    self.assertEqual(len(FLAGS.FlagDict()), old_len)
    self.assertFalse("new3" in FLAGS.FlagDict())
    self.assertFalse("new4" in FLAGS.FlagDict())
    self.assertFalse("n4" in FLAGS.FlagDict())

    # Make sure AppendFlagValues fails on duplicates
    gflags.DEFINE_boolean("dup4", 0, "runhelp d41")
    new_flags = gflags.FlagValues()
    gflags.DEFINE_boolean("dup4", 0, "runhelp d42", flag_values=new_flags)
    try:
      FLAGS.AppendFlagValues(new_flags)
      raise AssertionError("ignore_copy was not set but caused no exception")
    except gflags.DuplicateFlag:
      pass

    # Integer out of bounds
    try:
      argv = ('./program', '--repeat=-4')
      FLAGS(argv)
      raise AssertionError('integer bounds exception not raised:'
                           + str(FLAGS.repeat))
    except gflags.IllegalFlagValue:
      pass

    # Non-integer
    try:
      argv = ('./program', '--repeat=2.5')
      FLAGS(argv)
      raise AssertionError("malformed integer value exception not raised")
    except gflags.IllegalFlagValue:
      pass

    # Missing required arugment
    try:
      argv = ('./program', '--name')
      FLAGS(argv)
      raise AssertionError("Flag argument required exception not raised")
    except gflags.FlagsError:
      pass

    # Non-boolean arguments for boolean
    try:
      argv = ('./program', '--debug=goofup')
      FLAGS(argv)
      raise AssertionError("Illegal flag value exception not raised")
    except gflags.IllegalFlagValue:
      pass

    try:
      argv = ('./program', '--debug=42')
      FLAGS(argv)
      raise AssertionError("Illegal flag value exception not raised")
    except gflags.IllegalFlagValue:
      pass


    # Non-numeric argument for integer flag --repeat
    try:
      argv = ('./program', '--repeat', 'Bob', 'extra')
      FLAGS(argv)
      raise AssertionError("Illegal flag value exception not raised")
    except gflags.IllegalFlagValue:
      pass

    # Test ModuleHelp().
    helpstr = FLAGS.ModuleHelp(module_baz)

    expected_help = "\n" + module_baz.__name__ + ":" + """
  --[no]tmod_baz_x: Boolean flag.
    (default: 'true')"""

    self.assertMultiLineEqual(expected_help, helpstr)

    # Test MainModuleHelp().  This must be part of test_flags because
    # it dpeends on dup1/2/3/etc being introduced first.
    helpstr = FLAGS.MainModuleHelp()

    expected_help = "\n" + sys.argv[0] + ':' + """
  --[no]debug: debughelp
    (default: 'false')
  -u,--[no]dup1: runhelp d12
    (default: 'true')
  -u,--[no]dup2: runhelp d22
    (default: 'true')
  -u,--[no]dup3: runhelp d32
    (default: 'true')
  --[no]dup4: runhelp d41
    (default: 'false')
  --kwery: <who|what|why|where|when>: ?
  --l: how long to be
    (default: '9223372032559808512')
    (an integer)
  --letters: a list of letters
    (default: 'a,b,c')
    (a comma separated list)
  -m,--m_str: string option that can occur multiple times;
    repeat this option to specify a list of values
    (default: "['def1', 'def2']")
  --name: namehelp
    (default: 'Bob')
  --[no]noexec: boolean flag with no as prefix
    (default: 'true')
  --numbers: a list of numbers
    (default: '1,2,3')
    (a comma separated list)
  --[no]q: quiet mode
    (default: 'true')
  --[no]quack: superstring of 'q'
    (default: 'false')
  -r,--repeat: how many times to repeat (0-5)
    (default: '4')
    (a non-negative integer)
  -s,--s_str: string option that can occur multiple times;
    repeat this option to specify a list of values
    (default: "['sing1']")
  --[no]test0: test boolean parsing
  --[no]test1: test boolean parsing
  --[no]testget1: test parsing with defaults
  --[no]testget2: test parsing with defaults
  --[no]testget3: test parsing with defaults
  --testget4: test parsing with defaults
    (an integer)
  --testlist: test lists parsing
    (default: '')
    (a comma separated list)
  --[no]testnone: test boolean parsing
  --testspacelist: tests space lists parsing
    (default: '')
    (a whitespace separated list)
  --x: how eXtreme to be
    (default: '3')
    (an integer)
  -z,--[no]zoom1: runhelp z1
    (default: 'false')"""

    # Insert the --help flags in their proper place.
    help_help = """\
  -?,--[no]help: show this help
  --[no]helpshort: show usage only for this module
  --[no]helpxml: like --help, but generates XML output
"""
    expected_help = expected_help.replace('  --kwery',
                                          help_help + '  --kwery')

    self.assertMultiLineEqual(expected_help, helpstr)


class MultiNumericalFlagsTest(googletest.TestCase):

  def testMultiNumericalFlags(self):
    """Test multi_int and multi_float flags."""

    int_defaults = [77, 88,]
    gflags.DEFINE_multi_int('m_int', int_defaults,
                           'integer option that can occur multiple times',
                           short_name='mi')
    self.assertListEqual(FLAGS.get('m_int', None), int_defaults)
    argv = ('./program', '--m_int=-99', '--mi=101')
    FLAGS(argv)
    self.assertListEqual(FLAGS.get('m_int', None), [-99, 101,])

    float_defaults = [2.2, 3]
    gflags.DEFINE_multi_float('m_float', float_defaults,
                             'float option that can occur multiple times',
                             short_name='mf')
    for (expected, actual) in zip(float_defaults, FLAGS.get('m_float', None)):
      self.assertAlmostEquals(expected, actual)
    argv = ('./program', '--m_float=-17', '--mf=2.78e9')
    FLAGS(argv)
    expected_floats = [-17.0, 2.78e9]
    for (expected, actual) in zip(expected_floats, FLAGS.get('m_float', None)):
      self.assertAlmostEquals(expected, actual)

  def testSingleValueDefault(self):
    """Test multi_int and multi_float flags with a single default value."""
    int_default = 77
    gflags.DEFINE_multi_int('m_int1', int_default,
                           'integer option that can occur multiple times')
    self.assertListEqual(FLAGS.get('m_int1', None), [int_default])

    float_default = 2.2
    gflags.DEFINE_multi_float('m_float1', float_default,
                             'float option that can occur multiple times')
    actual = FLAGS.get('m_float1', None)
    self.assertEquals(1, len(actual))
    self.assertAlmostEquals(actual[0], float_default)

  def testBadMultiNumericalFlags(self):
    """Test multi_int and multi_float flags with non-parseable values."""

    # Test non-parseable defaults.
    self.assertRaisesWithRegexpMatch(
        gflags.IllegalFlagValue,
        'flag --m_int2=abc: invalid literal for int\(\) with base 10: \'abc\'',
        gflags.DEFINE_multi_int, 'm_int2', ['abc'], 'desc')

    self.assertRaisesWithRegexpMatch(
        gflags.IllegalFlagValue,
        'flag --m_float2=abc: (invalid literal for float\(\)||could not convert string to float): abc',
        gflags.DEFINE_multi_float, 'm_float2', ['abc'], 'desc')

    # Test non-parseable command line values.
    gflags.DEFINE_multi_int('m_int2', '77',
                           'integer option that can occur multiple times')
    argv = ('./program', '--m_int2=def')
    self.assertRaisesWithRegexpMatch(
        gflags.IllegalFlagValue,
        'flag --m_int2=def: invalid literal for int\(\) with base 10: \'def\'',
        FLAGS, argv)

    gflags.DEFINE_multi_float('m_float2', 2.2,
                             'float option that can occur multiple times')
    argv = ('./program', '--m_float2=def')
    self.assertRaisesWithRegexpMatch(
        gflags.IllegalFlagValue,
        'flag --m_float2=def: (invalid literal for float\(\)||could not convert string to float): def',
        FLAGS, argv)


class UnicodeFlagsTest(googletest.TestCase):
  """Testing proper unicode support for flags."""

  def testUnicodeDefaultAndHelpstring(self):
    gflags.DEFINE_string("unicode_str", "\xC3\x80\xC3\xBD".decode("utf-8"),
                        "help:\xC3\xAA".decode("utf-8"))
    argv = ("./program",)
    FLAGS(argv)   # should not raise any exceptions

    argv = ("./program", "--unicode_str=foo")
    FLAGS(argv)   # should not raise any exceptions

  def testUnicodeInList(self):
    gflags.DEFINE_list("unicode_list", ["abc", "\xC3\x80".decode("utf-8"),
                                       "\xC3\xBD".decode("utf-8")],
                      "help:\xC3\xAB".decode("utf-8"))
    argv = ("./program",)
    FLAGS(argv)   # should not raise any exceptions

    argv = ("./program", "--unicode_list=hello,there")
    FLAGS(argv)   # should not raise any exceptions

  def testXMLOutput(self):
    gflags.DEFINE_string("unicode1", "\xC3\x80\xC3\xBD".decode("utf-8"),
                        "help:\xC3\xAC".decode("utf-8"))
    gflags.DEFINE_list("unicode2", ["abc", "\xC3\x80".decode("utf-8"),
                                   "\xC3\xBD".decode("utf-8")],
                      "help:\xC3\xAD".decode("utf-8"))
    gflags.DEFINE_list("non_unicode", ["abc", "def", "ghi"],
                      "help:\xC3\xAD".decode("utf-8"))

    outfile = cStringIO.StringIO()
    FLAGS.WriteHelpInXMLFormat(outfile)
    actual_output = outfile.getvalue()

    # The xml output is large, so we just check parts of it.
    self.assertTrue("<name>unicode1</name>\n"
                    "    <meaning>help:&#236;</meaning>\n"
                    "    <default>&#192;&#253;</default>\n"
                    "    <current>&#192;&#253;</current>"
                    in actual_output)
    self.assertTrue("<name>unicode2</name>\n"
                    "    <meaning>help:&#237;</meaning>\n"
                    "    <default>abc,&#192;,&#253;</default>\n"
                    "    <current>[\'abc\', u\'\\xc0\', u\'\\xfd\']</current>"
                    in actual_output)
    self.assertTrue("<name>non_unicode</name>\n"
                    "    <meaning>help:&#237;</meaning>\n"
                    "    <default>abc,def,ghi</default>\n"
                    "    <current>[\'abc\', \'def\', \'ghi\']</current>"
                    in actual_output)


class LoadFromFlagFileTest(googletest.TestCase):
  """Testing loading flags from a file and parsing them."""

  def setUp(self):
    self.flag_values = gflags.FlagValues()
    # make sure we are using the old, stupid way of parsing flags.
    self.flag_values.UseGnuGetOpt(False)
    gflags.DEFINE_string('UnitTestMessage1', 'Foo!', 'You Add Here.',
                        flag_values=self.flag_values)
    gflags.DEFINE_string('UnitTestMessage2', 'Bar!', 'Hello, Sailor!',
                        flag_values=self.flag_values)
    gflags.DEFINE_boolean('UnitTestBoolFlag', 0, 'Some Boolean thing',
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('UnitTestNumber', 12345, 'Some integer',
                         lower_bound=0, flag_values=self.flag_values)
    gflags.DEFINE_list('UnitTestList', "1,2,3", 'Some list',
                      flag_values=self.flag_values)
    self.files_to_delete = []

  def tearDown(self):
    self._RemoveTestFiles()

  def _SetupTestFiles(self):
    """ Creates and sets up some dummy flagfile files with bogus flags"""

    # Figure out where to create temporary files
    tmp_path = '/tmp/flags_unittest'
    if os.path.exists(tmp_path):
      shutil.rmtree(tmp_path)
    os.makedirs(tmp_path)

    try:
      tmp_flag_file_1 = open(tmp_path + '/UnitTestFile1.tst', 'w')
      tmp_flag_file_2 = open(tmp_path + '/UnitTestFile2.tst', 'w')
      tmp_flag_file_3 = open(tmp_path + '/UnitTestFile3.tst', 'w')
      tmp_flag_file_4 = open(tmp_path + '/UnitTestFile4.tst', 'w')
    except IOError, e_msg:
      print e_msg
      print 'FAIL\n File Creation problem in Unit Test'
      sys.exit(1)

    # put some dummy flags in our test files
    tmp_flag_file_1.write('#A Fake Comment\n')
    tmp_flag_file_1.write('--UnitTestMessage1=tempFile1!\n')
    tmp_flag_file_1.write('\n')
    tmp_flag_file_1.write('--UnitTestNumber=54321\n')
    tmp_flag_file_1.write('--noUnitTestBoolFlag\n')
    file_list = [tmp_flag_file_1.name]
    # this one includes test file 1
    tmp_flag_file_2.write('//A Different Fake Comment\n')
    tmp_flag_file_2.write('--flagfile=%s\n' % tmp_flag_file_1.name)
    tmp_flag_file_2.write('--UnitTestMessage2=setFromTempFile2\n')
    tmp_flag_file_2.write('\t\t\n')
    tmp_flag_file_2.write('--UnitTestNumber=6789a\n')
    file_list.append(tmp_flag_file_2.name)
    # this file points to itself
    tmp_flag_file_3.write('--flagfile=%s\n' % tmp_flag_file_3.name)
    tmp_flag_file_3.write('--UnitTestMessage1=setFromTempFile3\n')
    tmp_flag_file_3.write('#YAFC\n')
    tmp_flag_file_3.write('--UnitTestBoolFlag\n')
    file_list.append(tmp_flag_file_3.name)
    # this file is unreadable
    tmp_flag_file_4.write('--flagfile=%s\n' % tmp_flag_file_3.name)
    tmp_flag_file_4.write('--UnitTestMessage1=setFromTempFile3\n')
    tmp_flag_file_4.write('--UnitTestMessage1=setFromTempFile3\n')
    os.chmod(tmp_path + '/UnitTestFile4.tst', 0)
    file_list.append(tmp_flag_file_4.name)

    tmp_flag_file_1.close()
    tmp_flag_file_2.close()
    tmp_flag_file_3.close()
    tmp_flag_file_4.close()

    self.files_to_delete = file_list

    return file_list # these are just the file names
  # end SetupFiles def

  def _RemoveTestFiles(self):
    """Closes the files we just created.  tempfile deletes them for us """
    for file_name in self.files_to_delete:
      try:
        os.remove(file_name)
      except OSError, e_msg:
        print '%s\n, Problem deleting test file' % e_msg
  #end RemoveTestFiles def

  def _ReadFlagsFromFiles(self, argv, force_gnu):
    return argv[:1] + self.flag_values.ReadFlagsFromFiles(argv[1:],
                                                          force_gnu=force_gnu)

  #### Flagfile Unit Tests ####
  def testMethod_flagfiles_1(self):
    """ Test trivial case with no flagfile based options. """
    fake_cmd_line = 'fooScript --UnitTestBoolFlag'
    fake_argv = fake_cmd_line.split(' ')
    self.flag_values(fake_argv)
    self.assertEqual( self.flag_values.UnitTestBoolFlag, 1)
    self.assertEqual( fake_argv, self._ReadFlagsFromFiles(fake_argv, False))

  # end testMethodOne

  def testMethod_flagfiles_2(self):
    """Tests parsing one file + arguments off simulated argv"""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = 'fooScript --q --flagfile=%s' % tmp_files[0]
    fake_argv = fake_cmd_line.split(' ')

    # We should see the original cmd line with the file's contents spliced in.
    # Flags from the file will appear in the order order they are sepcified
    # in the file, in the same position as the flagfile argument.
    expected_results = ['fooScript',
                          '--q',
                          '--UnitTestMessage1=tempFile1!',
                          '--UnitTestNumber=54321',
                          '--noUnitTestBoolFlag']
    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)
  # end testTwo def

  def testMethod_flagfiles_3(self):
    """Tests parsing nested files + arguments of simulated argv"""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --UnitTestNumber=77 --flagfile=%s'
                     % tmp_files[1])
    fake_argv = fake_cmd_line.split(' ')

    expected_results = ['fooScript',
                          '--UnitTestNumber=77',
                          '--UnitTestMessage1=tempFile1!',
                          '--UnitTestNumber=54321',
                          '--noUnitTestBoolFlag',
                          '--UnitTestMessage2=setFromTempFile2',
                          '--UnitTestNumber=6789a']
    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)
  # end testThree def

  def testMethod_flagfiles_4(self):
    """Tests parsing self-referential files + arguments of simulated argv.
      This test should print a warning to stderr of some sort.
    """
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --flagfile=%s --noUnitTestBoolFlag'
                     % tmp_files[2])
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                          '--UnitTestMessage1=setFromTempFile3',
                          '--UnitTestBoolFlag',
                          '--noUnitTestBoolFlag' ]

    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_5(self):
    """Test that --flagfile parsing respects the '--' end-of-options marker."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = 'fooScript --SomeFlag -- --flagfile=%s' % tmp_files[0]
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                        '--SomeFlag',
                        '--',
                        '--flagfile=%s' % tmp_files[0]]

    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_6(self):
    """Test that --flagfile parsing stops at non-options (non-GNU behavior)."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%s'
                     % tmp_files[0])
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                        '--SomeFlag',
                        'some_arg',
                        '--flagfile=%s' % tmp_files[0]]

    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_7(self):
    """Test that --flagfile parsing skips over a non-option (GNU behavior)."""
    self.flag_values.UseGnuGetOpt()
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%s'
                     % tmp_files[0])
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                        '--SomeFlag',
                        'some_arg',
                        '--UnitTestMessage1=tempFile1!',
                        '--UnitTestNumber=54321',
                        '--noUnitTestBoolFlag']

    test_results = self._ReadFlagsFromFiles(fake_argv, False)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_8(self):
    """Test that --flagfile parsing respects force_gnu=True."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%s'
                     % tmp_files[0])
    fake_argv = fake_cmd_line.split(' ')
    expected_results = ['fooScript',
                        '--SomeFlag',
                        'some_arg',
                        '--UnitTestMessage1=tempFile1!',
                        '--UnitTestNumber=54321',
                        '--noUnitTestBoolFlag']

    test_results = self._ReadFlagsFromFiles(fake_argv, True)
    self.assertEqual(expected_results, test_results)

  def testMethod_flagfiles_NoPermissions(self):
    """Test that --flagfile raises except on file that is unreadable."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%s'
                     % tmp_files[3])
    fake_argv = fake_cmd_line.split(' ')
    self.assertRaises(gflags.CantOpenFlagFileError,
                      self._ReadFlagsFromFiles, fake_argv, True)

  def testMethod_flagfiles_NotFound(self):
    """Test that --flagfile raises except on file that does not exist."""
    tmp_files = self._SetupTestFiles()
    # specify our temp file on the fake cmd line
    fake_cmd_line = ('fooScript --SomeFlag some_arg --flagfile=%sNOTEXIST'
                     % tmp_files[3])
    fake_argv = fake_cmd_line.split(' ')
    self.assertRaises(gflags.CantOpenFlagFileError,
                      self._ReadFlagsFromFiles, fake_argv, True)

  def test_flagfiles_user_path_expansion(self):
    """Test that user directory referenced paths (ie. ~/foo) are correctly
      expanded.  This test depends on whatever account's running the unit test
      to have read/write access to their own home directory, otherwise it'll
      FAIL.
    """
    fake_flagfile_item_style_1 = '--flagfile=~/foo.file'
    fake_flagfile_item_style_2 = '-flagfile=~/foo.file'

    expected_results = os.path.expanduser('~/foo.file')

    test_results = self.flag_values.ExtractFilename(fake_flagfile_item_style_1)
    self.assertEqual(expected_results, test_results)

    test_results = self.flag_values.ExtractFilename(fake_flagfile_item_style_2)
    self.assertEqual(expected_results, test_results)

  # end testFour def

  def test_no_touchy_non_flags(self):
    """
    Test that the flags parser does not mutilate arguments which are
    not supposed to be flags
    """
    fake_argv = ['fooScript', '--UnitTestBoolFlag',
                 'command', '--command_arg1', '--UnitTestBoom', '--UnitTestB']
    argv = self.flag_values(fake_argv)
    self.assertEqual(argv, fake_argv[:1] + fake_argv[2:])

  def test_parse_flags_after_args_if_using_gnu_getopt(self):
    """
    Test that flags given after arguments are parsed if using gnu_getopt.
    """
    self.flag_values.UseGnuGetOpt()
    fake_argv = ['fooScript', '--UnitTestBoolFlag',
                 'command', '--UnitTestB']
    argv = self.flag_values(fake_argv)
    self.assertEqual(argv, ['fooScript', 'command'])

  def test_SetDefault(self):
    """
    Test changing flag defaults.
    """
    # Test that SetDefault changes both the default and the value,
    # and that the value is changed when one is given as an option.
    self.flag_values['UnitTestMessage1'].SetDefault('New value')
    self.assertEqual(self.flag_values.UnitTestMessage1, 'New value')
    self.assertEqual(self.flag_values['UnitTestMessage1'].default_as_str,
                     "'New value'")
    self.flag_values([ 'dummyscript', '--UnitTestMessage1=Newer value' ])
    self.assertEqual(self.flag_values.UnitTestMessage1, 'Newer value')

    # Test that setting the default to None works correctly.
    self.flag_values['UnitTestNumber'].SetDefault(None)
    self.assertEqual(self.flag_values.UnitTestNumber, None)
    self.assertEqual(self.flag_values['UnitTestNumber'].default_as_str, None)
    self.flag_values([ 'dummyscript', '--UnitTestNumber=56' ])
    self.assertEqual(self.flag_values.UnitTestNumber, 56)

    # Test that setting the default to zero works correctly.
    self.flag_values['UnitTestNumber'].SetDefault(0)
    self.assertEqual(self.flag_values.UnitTestNumber, 0)
    self.assertEqual(self.flag_values['UnitTestNumber'].default_as_str, "'0'")
    self.flag_values([ 'dummyscript', '--UnitTestNumber=56' ])
    self.assertEqual(self.flag_values.UnitTestNumber, 56)

    # Test that setting the default to "" works correctly.
    self.flag_values['UnitTestMessage1'].SetDefault("")
    self.assertEqual(self.flag_values.UnitTestMessage1, "")
    self.assertEqual(self.flag_values['UnitTestMessage1'].default_as_str, "''")
    self.flag_values([ 'dummyscript', '--UnitTestMessage1=fifty-six' ])
    self.assertEqual(self.flag_values.UnitTestMessage1, "fifty-six")

    # Test that setting the default to false works correctly.
    self.flag_values['UnitTestBoolFlag'].SetDefault(False)
    self.assertEqual(self.flag_values.UnitTestBoolFlag, False)
    self.assertEqual(self.flag_values['UnitTestBoolFlag'].default_as_str,
                     "'false'")
    self.flag_values([ 'dummyscript', '--UnitTestBoolFlag=true' ])
    self.assertEqual(self.flag_values.UnitTestBoolFlag, True)

    # Test that setting a list default works correctly.
    self.flag_values['UnitTestList'].SetDefault('4,5,6')
    self.assertEqual(self.flag_values.UnitTestList, ['4', '5', '6'])
    self.assertEqual(self.flag_values['UnitTestList'].default_as_str, "'4,5,6'")
    self.flag_values([ 'dummyscript', '--UnitTestList=7,8,9' ])
    self.assertEqual(self.flag_values.UnitTestList, ['7', '8', '9'])

    # Test that setting invalid defaults raises exceptions
    self.assertRaises(gflags.IllegalFlagValue,
                      self.flag_values['UnitTestNumber'].SetDefault, 'oops')
    self.assertRaises(gflags.IllegalFlagValue,
                      self.flag_values.SetDefault, 'UnitTestNumber', -1)


class FlagsParsingTest(googletest.TestCase):
  """Testing different aspects of parsing: '-f' vs '--flag', etc."""

  def setUp(self):
    self.flag_values = gflags.FlagValues()

  def testMethod_ShortestUniquePrefixes(self):
    """Test FlagValues.ShortestUniquePrefixes"""

    gflags.DEFINE_string('a', '', '', flag_values=self.flag_values)
    gflags.DEFINE_string('abc', '', '', flag_values=self.flag_values)
    gflags.DEFINE_string('common_a_string', '', '', flag_values=self.flag_values)
    gflags.DEFINE_boolean('common_b_boolean', 0, '',
                         flag_values=self.flag_values)
    gflags.DEFINE_boolean('common_c_boolean', 0, '',
                         flag_values=self.flag_values)
    gflags.DEFINE_boolean('common', 0, '', flag_values=self.flag_values)
    gflags.DEFINE_integer('commonly', 0, '', flag_values=self.flag_values)
    gflags.DEFINE_boolean('zz', 0, '', flag_values=self.flag_values)
    gflags.DEFINE_integer('nozz', 0, '', flag_values=self.flag_values)

    shorter_flags = self.flag_values.ShortestUniquePrefixes(
        self.flag_values.FlagDict())

    expected_results = {'nocommon_b_boolean': 'nocommon_b',
                        'common_c_boolean': 'common_c',
                        'common_b_boolean': 'common_b',
                        'a': 'a',
                        'abc': 'ab',
                        'zz': 'z',
                        'nozz': 'nozz',
                        'common_a_string': 'common_a',
                        'commonly': 'commonl',
                        'nocommon_c_boolean': 'nocommon_c',
                        'nocommon': 'nocommon',
                        'common': 'common'}

    for name, shorter in expected_results.iteritems():
      self.assertEquals(shorter_flags[name], shorter)

    self.flag_values.__delattr__('a')
    self.flag_values.__delattr__('abc')
    self.flag_values.__delattr__('common_a_string')
    self.flag_values.__delattr__('common_b_boolean')
    self.flag_values.__delattr__('common_c_boolean')
    self.flag_values.__delattr__('common')
    self.flag_values.__delattr__('commonly')
    self.flag_values.__delattr__('zz')
    self.flag_values.__delattr__('nozz')

  def test_twodasharg_first(self):
    gflags.DEFINE_string("twodash_name", "Bob", "namehelp",
                        flag_values=self.flag_values)
    gflags.DEFINE_string("twodash_blame", "Rob", "blamehelp",
                        flag_values=self.flag_values)
    argv = ('./program',
            '--',
            '--twodash_name=Harry')
    argv = self.flag_values(argv)
    self.assertEqual('Bob', self.flag_values.twodash_name)
    self.assertEqual(argv[1], '--twodash_name=Harry')

  def test_twodasharg_middle(self):
    gflags.DEFINE_string("twodash2_name", "Bob", "namehelp",
                        flag_values=self.flag_values)
    gflags.DEFINE_string("twodash2_blame", "Rob", "blamehelp",
                        flag_values=self.flag_values)
    argv = ('./program',
            '--twodash2_blame=Larry',
            '--',
            '--twodash2_name=Harry')
    argv = self.flag_values(argv)
    self.assertEqual('Bob', self.flag_values.twodash2_name)
    self.assertEqual('Larry', self.flag_values.twodash2_blame)
    self.assertEqual(argv[1], '--twodash2_name=Harry')

  def test_onedasharg_first(self):
    gflags.DEFINE_string("onedash_name", "Bob", "namehelp",
                        flag_values=self.flag_values)
    gflags.DEFINE_string("onedash_blame", "Rob", "blamehelp",
                        flag_values=self.flag_values)
    argv = ('./program',
            '-',
            '--onedash_name=Harry')
    argv = self.flag_values(argv)
    self.assertEqual(argv[1], '-')
    # TODO(csilvers): we should still parse --onedash_name=Harry as a
    # flag, but currently we don't (we stop flag processing as soon as
    # we see the first non-flag).
    # - This requires gnu_getopt from Python 2.3+ see FLAGS.UseGnuGetOpt()

  def test_unrecognized_flags(self):
    gflags.DEFINE_string("name", "Bob", "namehelp", flag_values=self.flag_values)
    # Unknown flag --nosuchflag
    try:
      argv = ('./program', '--nosuchflag', '--name=Bob', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'
      assert e.flagvalue == '--nosuchflag'

    # Unknown flag -w (short option)
    try:
      argv = ('./program', '-w', '--name=Bob', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'w'
      assert e.flagvalue == '-w'

    # Unknown flag --nosuchflagwithparam=foo
    try:
      argv = ('./program', '--nosuchflagwithparam=foo', '--name=Bob', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflagwithparam'
      assert e.flagvalue == '--nosuchflagwithparam=foo'

    # Allow unknown flag --nosuchflag if specified with undefok
    argv = ('./program', '--nosuchflag', '--name=Bob',
            '--undefok=nosuchflag', 'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # Allow unknown flag --noboolflag if undefok=boolflag is specified
    argv = ('./program', '--noboolflag', '--name=Bob',
            '--undefok=boolflag', 'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # But not if the flagname is misspelled:
    try:
      argv = ('./program', '--nosuchflag', '--name=Bob',
              '--undefok=nosuchfla', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'

    try:
      argv = ('./program', '--nosuchflag', '--name=Bob',
              '--undefok=nosuchflagg', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'

    # Allow unknown short flag -w if specified with undefok
    argv = ('./program', '-w', '--name=Bob', '--undefok=w', 'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # Allow unknown flag --nosuchflagwithparam=foo if specified
    # with undefok
    argv = ('./program', '--nosuchflagwithparam=foo', '--name=Bob',
            '--undefok=nosuchflagwithparam', 'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # Even if undefok specifies multiple flags
    argv = ('./program', '--nosuchflag', '-w', '--nosuchflagwithparam=foo',
            '--name=Bob',
            '--undefok=nosuchflag,w,nosuchflagwithparam',
            'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"

    # However, not if undefok doesn't specify the flag
    try:
      argv = ('./program', '--nosuchflag', '--name=Bob',
              '--undefok=another_such', 'extra')
      self.flag_values(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'

    # Make sure --undefok doesn't mask other option errors.
    try:
      # Provide an option requiring a parameter but not giving it one.
      argv = ('./program', '--undefok=name', '--name')
      self.flag_values(argv)
      raise AssertionError("Missing option parameter exception not raised")
    except gflags.UnrecognizedFlag:
      raise AssertionError("Wrong kind of error exception raised")
    except gflags.FlagsError:
      pass

    # Test --undefok <list>
    argv = ('./program', '--nosuchflag', '-w', '--nosuchflagwithparam=foo',
            '--name=Bob',
            '--undefok',
            'nosuchflag,w,nosuchflagwithparam',
            'extra')
    argv = self.flag_values(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"


class NonGlobalFlagsTest(googletest.TestCase):

  def test_nonglobal_flags(self):
    """Test use of non-global FlagValues"""
    nonglobal_flags = gflags.FlagValues()
    gflags.DEFINE_string("nonglobal_flag", "Bob", "flaghelp", nonglobal_flags)
    argv = ('./program',
            '--nonglobal_flag=Mary',
            'extra')
    argv = nonglobal_flags(argv)
    assert len(argv) == 2, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"
    assert argv[1]=='extra', "extra argument not preserved"
    assert nonglobal_flags['nonglobal_flag'].value == 'Mary'

  def test_unrecognized_nonglobal_flags(self):
    """Test unrecognized non-global flags"""
    nonglobal_flags = gflags.FlagValues()
    argv = ('./program',
            '--nosuchflag')
    try:
      argv = nonglobal_flags(argv)
      raise AssertionError("Unknown flag exception not raised")
    except gflags.UnrecognizedFlag, e:
      assert e.flagname == 'nosuchflag'
      pass

    argv = ('./program',
            '--nosuchflag',
            '--undefok=nosuchflag')

    argv = nonglobal_flags(argv)
    assert len(argv) == 1, "wrong number of arguments pulled"
    assert argv[0]=='./program', "program name not preserved"

  def test_create_flag_errors(self):
    # Since the exception classes are exposed, nothing stops users
    # from creating their own instances. This test makes sure that
    # people modifying the flags module understand that the external
    # mechanisms for creating the exceptions should continue to work.
    e = gflags.FlagsError()
    e = gflags.FlagsError("message")
    e = gflags.DuplicateFlag()
    e = gflags.DuplicateFlag("message")
    e = gflags.IllegalFlagValue()
    e = gflags.IllegalFlagValue("message")
    e = gflags.UnrecognizedFlag()
    e = gflags.UnrecognizedFlag("message")

  def testFlagValuesDelAttr(self):
    """Checks that del self.flag_values.flag_id works."""
    default_value = 'default value for testFlagValuesDelAttr'
    # 1. Declare and delete a flag with no short name.
    flag_values = gflags.FlagValues()
    gflags.DEFINE_string('delattr_foo', default_value, 'A simple flag.',
                        flag_values=flag_values)
    self.assertEquals(flag_values.delattr_foo, default_value)
    flag_obj = flag_values['delattr_foo']
    # We also check that _FlagIsRegistered works as expected :)
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.delattr_foo
    self.assertFalse('delattr_foo' in flag_values.FlagDict())
    self.assertFalse(flag_values._FlagIsRegistered(flag_obj))
    # If the previous del FLAGS.delattr_foo did not work properly, the
    # next definition will trigger a redefinition error.
    gflags.DEFINE_integer('delattr_foo', 3, 'A simple flag.',
                         flag_values=flag_values)
    del flag_values.delattr_foo

    self.assertFalse('delattr_foo' in flag_values.RegisteredFlags())

    # 2. Declare and delete a flag with a short name.
    gflags.DEFINE_string('delattr_bar', default_value, 'flag with short name',
                        short_name='x5', flag_values=flag_values)
    flag_obj = flag_values['delattr_bar']
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.x5
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.delattr_bar
    self.assertFalse(flag_values._FlagIsRegistered(flag_obj))

    # 3. Just like 2, but del flag_values.name last
    gflags.DEFINE_string('delattr_bar', default_value, 'flag with short name',
                        short_name='x5', flag_values=flag_values)
    flag_obj = flag_values['delattr_bar']
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.delattr_bar
    self.assertTrue(flag_values._FlagIsRegistered(flag_obj))
    del flag_values.x5
    self.assertFalse(flag_values._FlagIsRegistered(flag_obj))

    self.assertFalse('delattr_bar' in flag_values.RegisteredFlags())
    self.assertFalse('x5' in flag_values.RegisteredFlags())


class KeyFlagsTest(googletest.TestCase):

  def setUp(self):
    self.flag_values = gflags.FlagValues()

  def _GetNamesOfDefinedFlags(self, module, flag_values):
    """Returns the list of names of flags defined by a module.

    Auxiliary for the testKeyFlags* methods.

    Args:
      module: A module object or a string module name.
      flag_values: A FlagValues object.

    Returns:
      A list of strings.
    """
    return [f.name for f in flag_values._GetFlagsDefinedByModule(module)]

  def _GetNamesOfKeyFlags(self, module, flag_values):
    """Returns the list of names of key flags for a module.

    Auxiliary for the testKeyFlags* methods.

    Args:
      module: A module object or a string module name.
      flag_values: A FlagValues object.

    Returns:
      A list of strings.
    """
    return [f.name for f in flag_values._GetKeyFlagsForModule(module)]

  def _AssertListsHaveSameElements(self, list_1, list_2):
    # Checks that two lists have the same elements with the same
    # multiplicity, in possibly different order.
    list_1 = list(list_1)
    list_1.sort()
    list_2 = list(list_2)
    list_2.sort()
    self.assertListEqual(list_1, list_2)

  def testKeyFlags(self):
    # Before starting any testing, make sure no flags are already
    # defined for module_foo and module_bar.
    self.assertListEqual(self._GetNamesOfKeyFlags(module_foo, self.flag_values),
                         [])
    self.assertListEqual(self._GetNamesOfKeyFlags(module_bar, self.flag_values),
                         [])
    self.assertListEqual(self._GetNamesOfDefinedFlags(module_foo,
                                                      self.flag_values),
                         [])
    self.assertListEqual(self._GetNamesOfDefinedFlags(module_bar,
                                                      self.flag_values),
                         [])

    # Defines a few flags in module_foo and module_bar.
    module_foo.DefineFlags(flag_values=self.flag_values)

    try:
      # Part 1. Check that all flags defined by module_foo are key for
      # that module, and similarly for module_bar.
      for module in [module_foo, module_bar]:
        self._AssertListsHaveSameElements(
            self.flag_values._GetFlagsDefinedByModule(module),
            self.flag_values._GetKeyFlagsForModule(module))
        # Also check that each module defined the expected flags.
        self._AssertListsHaveSameElements(
            self._GetNamesOfDefinedFlags(module, self.flag_values),
            module.NamesOfDefinedFlags())

      # Part 2. Check that gflags.DECLARE_key_flag works fine.
      # Declare that some flags from module_bar are key for
      # module_foo.
      module_foo.DeclareKeyFlags(flag_values=self.flag_values)

      # Check that module_foo has the expected list of defined flags.
      self._AssertListsHaveSameElements(
          self._GetNamesOfDefinedFlags(module_foo, self.flag_values),
          module_foo.NamesOfDefinedFlags())

      # Check that module_foo has the expected list of key flags.
      self._AssertListsHaveSameElements(
          self._GetNamesOfKeyFlags(module_foo, self.flag_values),
          module_foo.NamesOfDeclaredKeyFlags())

      # Part 3. Check that gflags.ADOPT_module_key_flags works fine.
      # Trigger a call to gflags.ADOPT_module_key_flags(module_bar)
      # inside module_foo.  This should declare a few more key
      # flags in module_foo.
      module_foo.DeclareExtraKeyFlags(flag_values=self.flag_values)

      # Check that module_foo has the expected list of key flags.
      self._AssertListsHaveSameElements(
          self._GetNamesOfKeyFlags(module_foo, self.flag_values),
          module_foo.NamesOfDeclaredKeyFlags() +
          module_foo.NamesOfDeclaredExtraKeyFlags())
    finally:
      module_foo.RemoveFlags(flag_values=self.flag_values)

  def testKeyFlagsWithNonDefaultFlagValuesObject(self):
    # Check that key flags work even when we use a FlagValues object
    # that is not the default gflags.self.flag_values object.  Otherwise, this
    # test is similar to testKeyFlags, but it uses only module_bar.
    # The other test module (module_foo) uses only the default values
    # for the flag_values keyword arguments.  This way, testKeyFlags
    # and this method test both the default FlagValues, the explicitly
    # specified one, and a mixed usage of the two.

    # A brand-new FlagValues object, to use instead of gflags.self.flag_values.
    fv = gflags.FlagValues()

    # Before starting any testing, make sure no flags are already
    # defined for module_foo and module_bar.
    self.assertListEqual(
        self._GetNamesOfKeyFlags(module_bar, fv),
        [])
    self.assertListEqual(
        self._GetNamesOfDefinedFlags(module_bar, fv),
        [])

    module_bar.DefineFlags(flag_values=fv)

    # Check that all flags defined by module_bar are key for that
    # module, and that module_bar defined the expected flags.
    self._AssertListsHaveSameElements(
        fv._GetFlagsDefinedByModule(module_bar),
        fv._GetKeyFlagsForModule(module_bar))
    self._AssertListsHaveSameElements(
        self._GetNamesOfDefinedFlags(module_bar, fv),
        module_bar.NamesOfDefinedFlags())

    # Pick two flags from module_bar, declare them as key for the
    # current (i.e., main) module (via gflags.DECLARE_key_flag), and
    # check that we get the expected effect.  The important thing is
    # that we always use flags_values=fv (instead of the default
    # self.flag_values).
    main_module = gflags._GetMainModule()
    names_of_flags_defined_by_bar = module_bar.NamesOfDefinedFlags()
    flag_name_0 = names_of_flags_defined_by_bar[0]
    flag_name_2 = names_of_flags_defined_by_bar[2]

    gflags.DECLARE_key_flag(flag_name_0, flag_values=fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        [flag_name_0])

    gflags.DECLARE_key_flag(flag_name_2, flag_values=fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        [flag_name_0, flag_name_2])

    # Try with a special (not user-defined) flag too:
    gflags.DECLARE_key_flag('undefok', flag_values=fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        [flag_name_0, flag_name_2, 'undefok'])

    gflags.ADOPT_module_key_flags(module_bar, fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        names_of_flags_defined_by_bar + ['undefok'])

    # Adopt key flags from the flags module itself.
    gflags.ADOPT_module_key_flags(gflags, flag_values=fv)
    self._AssertListsHaveSameElements(
        self._GetNamesOfKeyFlags(main_module, fv),
        names_of_flags_defined_by_bar + ['flagfile', 'undefok'])

  def testMainModuleHelpWithKeyFlags(self):
    # Similar to test_main_module_help, but this time we make sure to
    # declare some key flags.

    # Safety check that the main module does not declare any flags
    # at the beginning of this test.
    expected_help = ''
    self.assertMultiLineEqual(expected_help, self.flag_values.MainModuleHelp())

    # Define one flag in this main module and some flags in modules
    # a and b.  Also declare one flag from module a and one flag
    # from module b as key flags for the main module.
    gflags.DEFINE_integer('main_module_int_fg', 1,
                         'Integer flag in the main module.',
                         flag_values=self.flag_values)

    try:
      main_module_int_fg_help = (
          "  --main_module_int_fg: Integer flag in the main module.\n"
          "    (default: '1')\n"
          "    (an integer)")

      expected_help += "\n%s:\n%s" % (sys.argv[0], main_module_int_fg_help)
      self.assertMultiLineEqual(expected_help,
                                self.flag_values.MainModuleHelp())

      # The following call should be a no-op: any flag declared by a
      # module is automatically key for that module.
      gflags.DECLARE_key_flag('main_module_int_fg', flag_values=self.flag_values)
      self.assertMultiLineEqual(expected_help,
                                self.flag_values.MainModuleHelp())

      # The definition of a few flags in an imported module should not
      # change the main module help.
      module_foo.DefineFlags(flag_values=self.flag_values)
      self.assertMultiLineEqual(expected_help,
                                self.flag_values.MainModuleHelp())

      gflags.DECLARE_key_flag('tmod_foo_bool', flag_values=self.flag_values)
      tmod_foo_bool_help = (
          "  --[no]tmod_foo_bool: Boolean flag from module foo.\n"
          "    (default: 'true')")
      expected_help += "\n" + tmod_foo_bool_help
      self.assertMultiLineEqual(expected_help,
                                self.flag_values.MainModuleHelp())

      gflags.DECLARE_key_flag('tmod_bar_z', flag_values=self.flag_values)
      tmod_bar_z_help = (
          "  --[no]tmod_bar_z: Another boolean flag from module bar.\n"
          "    (default: 'false')")
      # Unfortunately, there is some flag sorting inside
      # MainModuleHelp, so we can't keep incrementally extending
      # the expected_help string ...
      expected_help = ("\n%s:\n%s\n%s\n%s" %
                       (sys.argv[0],
                        main_module_int_fg_help,
                        tmod_bar_z_help,
                        tmod_foo_bool_help))
      self.assertMultiLineEqual(self.flag_values.MainModuleHelp(),
                                expected_help)

    finally:
      # At the end, delete all the flag information we created.
      self.flag_values.__delattr__('main_module_int_fg')
      module_foo.RemoveFlags(flag_values=self.flag_values)

  def test_ADOPT_module_key_flags(self):
    # Check that ADOPT_module_key_flags raises an exception when
    # called with a module name (as opposed to a module object).
    self.assertRaises(gflags.FlagsError,
                      gflags.ADOPT_module_key_flags,
                      'pyglib.app')


class GetCallingModuleTest(googletest.TestCase):
  """Test whether we correctly determine the module which defines the flag."""

  def test_GetCallingModule(self):
    self.assertEqual(gflags._GetCallingModule(), sys.argv[0])
    self.assertEqual(
        module_foo.GetModuleName(),
        'flags_modules_for_testing.module_foo')
    self.assertEqual(
        module_bar.GetModuleName(),
        'flags_modules_for_testing.module_bar')

    # We execute the following exec statements for their side-effect
    # (i.e., not raising an error).  They emphasize the case that not
    # all code resides in one of the imported modules: Python is a
    # really dynamic language, where we can dynamically construct some
    # code and execute it.
    code = ("import gflags\n"
            "module_name = gflags._GetCallingModule()")
    exec(code)

    # Next two exec statements executes code with a global environment
    # that is different from the global environment of any imported
    # module.
    exec(code, {})
    # vars(self) returns a dictionary corresponding to the symbol
    # table of the self object.  dict(...) makes a distinct copy of
    # this dictionary, such that any new symbol definition by the
    # exec-ed code (e.g., import flags, module_name = ...) does not
    # affect the symbol table of self.
    exec(code, dict(vars(self)))

    # Next test is actually more involved: it checks not only that
    # _GetCallingModule does not crash inside exec code, it also checks
    # that it returns the expected value: the code executed via exec
    # code is treated as being executed by the current module.  We
    # check it twice: first time by executing exec from the main
    # module, second time by executing it from module_bar.
    global_dict = {}
    exec(code, global_dict)
    self.assertEqual(global_dict['module_name'],
                     sys.argv[0])

    global_dict = {}
    module_bar.ExecuteCode(code, global_dict)
    self.assertEqual(
        global_dict['module_name'],
        'flags_modules_for_testing.module_bar')

  def test_GetCallingModuleWithIteritemsError(self):
    # This test checks that _GetCallingModule is using
    # sys.modules.items(), instead of .iteritems().
    orig_sys_modules = sys.modules

    # Mock sys.modules: simulates error produced by importing a module
    # in paralel with our iteration over sys.modules.iteritems().
    class SysModulesMock(dict):
      def __init__(self, original_content):
        dict.__init__(self, original_content)

      def iteritems(self):
        # Any dictionary method is fine, but not .iteritems().
        raise RuntimeError('dictionary changed size during iteration')

    sys.modules = SysModulesMock(orig_sys_modules)
    try:
      # _GetCallingModule should still work as expected:
      self.assertEqual(gflags._GetCallingModule(), sys.argv[0])
      self.assertEqual(
          module_foo.GetModuleName(),
          'flags_modules_for_testing.module_foo')
    finally:
      sys.modules = orig_sys_modules


class FindModuleTest(googletest.TestCase):
  """Testing methods that find a module that defines a given flag."""

  def testFindModuleDefiningFlag(self):
    self.assertEqual('default', FLAGS.FindModuleDefiningFlag(
        '__NON_EXISTENT_FLAG__', 'default'))
    self.assertEqual(
        module_baz.__name__, FLAGS.FindModuleDefiningFlag('tmod_baz_x'))

  def testFindModuleIdDefiningFlag(self):
    self.assertEqual('default', FLAGS.FindModuleIdDefiningFlag(
        '__NON_EXISTENT_FLAG__', 'default'))
    self.assertEqual(
        id(module_baz), FLAGS.FindModuleIdDefiningFlag('tmod_baz_x'))


class FlagsErrorMessagesTest(googletest.TestCase):
  """Testing special cases for integer and float flags error messages."""

  def setUp(self):
    # make sure we are using the old, stupid way of parsing flags.
    self.flag_values = gflags.FlagValues()
    self.flag_values.UseGnuGetOpt(False)

  def testIntegerErrorText(self):
    # Make sure we get proper error text
    gflags.DEFINE_integer('positive', 4, 'non-negative flag', lower_bound=1,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('non_negative', 4, 'positive flag', lower_bound=0,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('negative', -4, 'negative flag', upper_bound=-1,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('non_positive', -4, 'non-positive flag', upper_bound=0,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('greater', 19, 'greater-than flag', lower_bound=4,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('smaller', -19, 'smaller-than flag', upper_bound=4,
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('usual', 4, 'usual flag', lower_bound=0,
                         upper_bound=10000, flag_values=self.flag_values)
    gflags.DEFINE_integer('another_usual', 0, 'usual flag', lower_bound=-1,
                         upper_bound=1, flag_values=self.flag_values)

    self._CheckErrorMessage('positive', -4, 'a positive integer')
    self._CheckErrorMessage('non_negative', -4, 'a non-negative integer')
    self._CheckErrorMessage('negative', 0, 'a negative integer')
    self._CheckErrorMessage('non_positive', 4, 'a non-positive integer')
    self._CheckErrorMessage('usual', -4, 'an integer in the range [0, 10000]')
    self._CheckErrorMessage('another_usual', 4,
                            'an integer in the range [-1, 1]')
    self._CheckErrorMessage('greater', -5, 'integer >= 4')
    self._CheckErrorMessage('smaller', 5, 'integer <= 4')

  def testFloatErrorText(self):
    gflags.DEFINE_float('positive', 4, 'non-negative flag', lower_bound=1,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('non_negative', 4, 'positive flag', lower_bound=0,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('negative', -4, 'negative flag', upper_bound=-1,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('non_positive', -4, 'non-positive flag', upper_bound=0,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('greater', 19, 'greater-than flag', lower_bound=4,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('smaller', -19, 'smaller-than flag', upper_bound=4,
                       flag_values=self.flag_values)
    gflags.DEFINE_float('usual', 4, 'usual flag', lower_bound=0,
                       upper_bound=10000, flag_values=self.flag_values)
    gflags.DEFINE_float('another_usual', 0, 'usual flag', lower_bound=-1,
                       upper_bound=1, flag_values=self.flag_values)

    self._CheckErrorMessage('positive', 0.5, 'number >= 1')
    self._CheckErrorMessage('non_negative', -4.0, 'a non-negative number')
    self._CheckErrorMessage('negative', 0.5, 'number <= -1')
    self._CheckErrorMessage('non_positive', 4.0, 'a non-positive number')
    self._CheckErrorMessage('usual', -4.0, 'a number in the range [0, 10000]')
    self._CheckErrorMessage('another_usual', 4.0,
                            'a number in the range [-1, 1]')
    self._CheckErrorMessage('smaller', 5.0, 'number <= 4')

  def _CheckErrorMessage(self, flag_name, flag_value, expected_message_suffix):
    """Set a flag to a given value and make sure we get expected message."""

    try:
      self.flag_values.__setattr__(flag_name, flag_value)
      raise AssertionError('Bounds exception not raised!')
    except gflags.IllegalFlagValue, e:
      expected = ('flag --%(name)s=%(value)s: %(value)s is not %(suffix)s' %
                  {'name': flag_name, 'value': flag_value,
                   'suffix': expected_message_suffix})
      self.assertEquals(str(e), expected)


def main():
  googletest.main()


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = gflags_validators_test
#!/usr/bin/env python

# Copyright (c) 2010, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Testing that flags validators framework does work.

This file tests that each flag validator called when it should be, and that
failed validator will throw an exception, etc.
"""

__author__ = 'olexiy@google.com (Olexiy Oryeshko)'

import gflags_googletest as googletest
import gflags
import gflags_validators


class SimpleValidatorTest(googletest.TestCase):
  """Testing gflags.RegisterValidator() method."""

  def setUp(self):
    super(SimpleValidatorTest, self).setUp()
    self.flag_values = gflags.FlagValues()
    self.call_args = []

  def testSuccess(self):
    def Checker(x):
      self.call_args.append(x)
      return True
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program')
    self.flag_values(argv)
    self.assertEquals(None, self.flag_values.test_flag)
    self.flag_values.test_flag = 2
    self.assertEquals(2, self.flag_values.test_flag)
    self.assertEquals([None, 2], self.call_args)

  def testDefaultValueNotUsedSuccess(self):
    def Checker(x):
      self.call_args.append(x)
      return True
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    self.flag_values(argv)
    self.assertEquals(1, self.flag_values.test_flag)
    self.assertEquals([1], self.call_args)

  def testValidatorNotCalledWhenOtherFlagIsChanged(self):
    def Checker(x):
      self.call_args.append(x)
      return True
    gflags.DEFINE_integer('test_flag', 1, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.DEFINE_integer('other_flag', 2, 'Other integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program')
    self.flag_values(argv)
    self.assertEquals(1, self.flag_values.test_flag)
    self.flag_values.other_flag = 3
    self.assertEquals([1], self.call_args)

  def testExceptionRaisedIfCheckerFails(self):
    def Checker(x):
      self.call_args.append(x)
      return x == 1
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    self.flag_values(argv)
    try:
      self.flag_values.test_flag = 2
      raise AssertionError('gflags.IllegalFlagValue expected')
    except gflags.IllegalFlagValue, e:
      self.assertEquals('flag --test_flag=2: Errors happen', str(e))
    self.assertEquals([1, 2], self.call_args)

  def testExceptionRaisedIfCheckerRaisesException(self):
    def Checker(x):
      self.call_args.append(x)
      if x == 1:
        return True
      raise gflags_validators.Error('Specific message')
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    self.flag_values(argv)
    try:
      self.flag_values.test_flag = 2
      raise AssertionError('gflags.IllegalFlagValue expected')
    except gflags.IllegalFlagValue, e:
      self.assertEquals('flag --test_flag=2: Specific message', str(e))
    self.assertEquals([1, 2], self.call_args)

  def testErrorMessageWhenCheckerReturnsFalseOnStart(self):
    def Checker(x):
      self.call_args.append(x)
      return False
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    try:
      self.flag_values(argv)
      raise AssertionError('gflags.IllegalFlagValue expected')
    except gflags.IllegalFlagValue, e:
      self.assertEquals('flag --test_flag=1: Errors happen', str(e))
    self.assertEquals([1], self.call_args)

  def testErrorMessageWhenCheckerRaisesExceptionOnStart(self):
    def Checker(x):
      self.call_args.append(x)
      raise gflags_validators.Error('Specific message')
    gflags.DEFINE_integer('test_flag', None, 'Usual integer flag',
                         flag_values=self.flag_values)
    gflags.RegisterValidator('test_flag',
                            Checker,
                            message='Errors happen',
                            flag_values=self.flag_values)

    argv = ('./program', '--test_flag=1')
    try:
      self.flag_values(argv)
      raise AssertionError('IllegalFlagValue expected')
    except gflags.IllegalFlagValue, e:
      self.assertEquals('flag --test_flag=1: Specific message', str(e))
    self.assertEquals([1], self.call_args)

  def testValidatorsCheckedInOrder(self):

    def Required(x):
      self.calls.append('Required')
      return x is not None

    def Even(x):
      self.calls.append('Even')
      return x % 2 == 0

    self.calls = []
    self._DefineFlagAndValidators(Required, Even)
    self.assertEquals(['Required', 'Even'], self.calls)

    self.calls = []
    self._DefineFlagAndValidators(Even, Required)
    self.assertEquals(['Even', 'Required'], self.calls)

  def _DefineFlagAndValidators(self, first_validator, second_validator):
    local_flags = gflags.FlagValues()
    gflags.DEFINE_integer('test_flag', 2, 'test flag', flag_values=local_flags)
    gflags.RegisterValidator('test_flag',
                            first_validator,
                            message='',
                            flag_values=local_flags)
    gflags.RegisterValidator('test_flag',
                            second_validator,
                            message='',
                            flag_values=local_flags)
    argv = ('./program')
    local_flags(argv)


if __name__ == '__main__':
  googletest.main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# WTForms documentation build configuration file, created by
# sphinx-quickstart on Fri Aug 01 15:29:36 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

def _fix_import_path():
    """
    Don't want to pollute the config globals, so do path munging 
    here in this function
    """
    import sys, os

    try:
        import wtforms
    except ImportError:
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
        build_lib = os.path.join(parent_dir, 'build', 'lib')
        if os.path.isdir(build_lib):
            sys.path.insert(0, build_lib)
        else:
            sys.path.insert(0, parent_dir)

_fix_import_path()

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'WTForms'
copyright = '2010 by Thomas Johansson, James Crasta'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.0.3'
# The full version, including alpha/beta/rc tags.
release = '1.0.3'


# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

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
pygments_style = 'friendly'


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
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
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'WTFormsdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'WTForms.tex', 'WTForms Documentation',
   'Thomas Johansson, James Crasta', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
"""
Unittests for wtforms.ext.appengine

To run the tests, use NoseGAE:

easy_install nose
easy_install nosegae

nosetests --with-gae --without-sandbox
"""
from __future__ import unicode_literals

import sys, os
WTFORMS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, WTFORMS_DIR)

from unittest import TestCase

from google.appengine.ext import db

from wtforms import Form, fields as f, validators
from wtforms.ext.appengine.db import model_form
from wtforms.ext.appengine.fields import GeoPtPropertyField


class DummyPostData(dict):
    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v


class Author(db.Model):
    name = db.StringProperty(required=True)
    city = db.StringProperty()
    age = db.IntegerProperty(required=True)
    is_admin = db.BooleanProperty(default=False)


class Book(db.Model):
    author = db.ReferenceProperty(Author)


class AllPropertiesModel(db.Model):
    """Property names are ugly, yes."""
    prop_string = db.StringProperty()
    prop_byte_string = db.ByteStringProperty()
    prop_boolean = db.BooleanProperty()
    prop_integer = db.IntegerProperty()
    prop_float = db.FloatProperty()
    prop_date_time = db.DateTimeProperty()
    prop_date = db.DateProperty()
    prop_time = db.TimeProperty()
    prop_list = db.ListProperty(int)
    prop_string_list = db.StringListProperty()
    prop_reference = db.ReferenceProperty()
    prop_self_refeference = db.SelfReferenceProperty()
    prop_user = db.UserProperty()
    prop_blob = db.BlobProperty()
    prop_text = db.TextProperty()
    prop_category = db.CategoryProperty()
    prop_link = db.LinkProperty()
    prop_email = db.EmailProperty()
    prop_geo_pt = db.GeoPtProperty()
    prop_im = db.IMProperty()
    prop_phone_number = db.PhoneNumberProperty()
    prop_postal_address = db.PostalAddressProperty()
    prop_rating = db.RatingProperty()


class DateTimeModel(db.Model):
    prop_date_time_1 = db.DateTimeProperty()
    prop_date_time_2 = db.DateTimeProperty(auto_now=True)
    prop_date_time_3 = db.DateTimeProperty(auto_now_add=True)

    prop_date_1 = db.DateProperty()
    prop_date_2 = db.DateProperty(auto_now=True)
    prop_date_3 = db.DateProperty(auto_now_add=True)

    prop_time_1 = db.TimeProperty()
    prop_time_2 = db.TimeProperty(auto_now=True)
    prop_time_3 = db.TimeProperty(auto_now_add=True)


class TestModelForm(TestCase):
    def tearDown(self):
        for entity in Author.all():
            db.delete(entity)

        for entity in Book.all():
            db.delete(entity)

    def test_model_form_basic(self):
        form_class = model_form(Author)

        self.assertEqual(hasattr(form_class, 'name'), True)
        self.assertEqual(hasattr(form_class, 'age'), True)
        self.assertEqual(hasattr(form_class, 'city'), True)
        self.assertEqual(hasattr(form_class, 'is_admin'), True)

        form = form_class()
        self.assertEqual(isinstance(form.name, f.TextField), True)
        self.assertEqual(isinstance(form.city, f.TextField), True)
        self.assertEqual(isinstance(form.age, f.IntegerField), True)
        self.assertEqual(isinstance(form.is_admin, f.BooleanField), True)

    def test_required_field(self):
        form_class = model_form(Author)

        form = form_class()
        self.assertEqual(form.name.flags.required, True)
        self.assertEqual(form.city.flags.required, False)
        self.assertEqual(form.age.flags.required, True)
        self.assertEqual(form.is_admin.flags.required, False)

    def test_default_value(self):
        form_class = model_form(Author)

        form = form_class()
        self.assertEqual(form.name.default, None)
        self.assertEqual(form.city.default, None)
        self.assertEqual(form.age.default, None)
        self.assertEqual(form.is_admin.default, False)

    def test_model_form_only(self):
        form_class = model_form(Author, only=['name', 'age'])

        self.assertEqual(hasattr(form_class, 'name'), True)
        self.assertEqual(hasattr(form_class, 'city'), False)
        self.assertEqual(hasattr(form_class, 'age'), True)
        self.assertEqual(hasattr(form_class, 'is_admin'), False)

        form = form_class()
        self.assertEqual(isinstance(form.name, f.TextField), True)
        self.assertEqual(isinstance(form.age, f.IntegerField), True)

    def test_model_form_exclude(self):
        form_class = model_form(Author, exclude=['is_admin'])

        self.assertEqual(hasattr(form_class, 'name'), True)
        self.assertEqual(hasattr(form_class, 'city'), True)
        self.assertEqual(hasattr(form_class, 'age'), True)
        self.assertEqual(hasattr(form_class, 'is_admin'), False)

        form = form_class()
        self.assertEqual(isinstance(form.name, f.TextField), True)
        self.assertEqual(isinstance(form.city, f.TextField), True)
        self.assertEqual(isinstance(form.age, f.IntegerField), True)

    def test_datetime_model(self):
        """Fields marked as auto_add / auto_add_now should not be included."""
        form_class = model_form(DateTimeModel)

        self.assertEqual(hasattr(form_class, 'prop_date_time_1'), True)
        self.assertEqual(hasattr(form_class, 'prop_date_time_2'), False)
        self.assertEqual(hasattr(form_class, 'prop_date_time_3'), False)

        self.assertEqual(hasattr(form_class, 'prop_date_1'), True)
        self.assertEqual(hasattr(form_class, 'prop_date_2'), False)
        self.assertEqual(hasattr(form_class, 'prop_date_3'), False)

        self.assertEqual(hasattr(form_class, 'prop_time_1'), True)
        self.assertEqual(hasattr(form_class, 'prop_time_2'), False)
        self.assertEqual(hasattr(form_class, 'prop_time_3'), False)

    def test_not_implemented_properties(self):
        # This should not raise NotImplementedError.
        form_class = model_form(AllPropertiesModel)

        # These should be set.
        self.assertEqual(hasattr(form_class, 'prop_string'), True)
        self.assertEqual(hasattr(form_class, 'prop_byte_string'), True)
        self.assertEqual(hasattr(form_class, 'prop_boolean'), True)
        self.assertEqual(hasattr(form_class, 'prop_integer'), True)
        self.assertEqual(hasattr(form_class, 'prop_float'), True)
        self.assertEqual(hasattr(form_class, 'prop_date_time'), True)
        self.assertEqual(hasattr(form_class, 'prop_date'), True)
        self.assertEqual(hasattr(form_class, 'prop_time'), True)
        self.assertEqual(hasattr(form_class, 'prop_string_list'), True)
        self.assertEqual(hasattr(form_class, 'prop_reference'), True)
        self.assertEqual(hasattr(form_class, 'prop_self_refeference'), True)
        self.assertEqual(hasattr(form_class, 'prop_blob'), True)
        self.assertEqual(hasattr(form_class, 'prop_text'), True)
        self.assertEqual(hasattr(form_class, 'prop_category'), True)
        self.assertEqual(hasattr(form_class, 'prop_link'), True)
        self.assertEqual(hasattr(form_class, 'prop_email'), True)
        self.assertEqual(hasattr(form_class, 'prop_geo_pt'), True)
        self.assertEqual(hasattr(form_class, 'prop_phone_number'), True)
        self.assertEqual(hasattr(form_class, 'prop_postal_address'), True)
        self.assertEqual(hasattr(form_class, 'prop_rating'), True)

        # These should NOT be set.
        self.assertEqual(hasattr(form_class, 'prop_list'), False)
        self.assertEqual(hasattr(form_class, 'prop_user'), False)
        self.assertEqual(hasattr(form_class, 'prop_im'), False)

    def test_populate_form(self):
        entity = Author(key_name='test', name='John', city='Yukon', age=25, is_admin=True)
        entity.put()

        obj = Author.get_by_key_name('test')
        form_class = model_form(Author)

        form = form_class(obj=obj)
        self.assertEqual(form.name.data, 'John')
        self.assertEqual(form.city.data, 'Yukon')
        self.assertEqual(form.age.data, 25)
        self.assertEqual(form.is_admin.data, True)

    def test_field_attributes(self):
        form_class = model_form(Author, field_args={
            'name': {
                'label': 'Full name',
                'description': 'Your name',
            },
            'age': {
                'label': 'Age',
                'validators': [validators.NumberRange(min=14, max=99)],
            },
            'city': {
                'label': 'City',
                'description': 'The city in which you live, not the one in which you were born.',
            },
            'is_admin': {
                'label': 'Administrative rights',
            },
        })
        form = form_class()

        self.assertEqual(form.name.label.text, 'Full name')
        self.assertEqual(form.name.description, 'Your name')

        self.assertEqual(form.age.label.text, 'Age')

        self.assertEqual(form.city.label.text, 'City')
        self.assertEqual(form.city.description, 'The city in which you live, not the one in which you were born.')

        self.assertEqual(form.is_admin.label.text, 'Administrative rights')

    def test_reference_property(self):
        keys = ['__None']
        for name in ['foo', 'bar', 'baz']:
            author = Author(name=name, age=26)
            author.put()
            keys.append(str(author.key()))

        form_class = model_form(Book)
        form = form_class()

        choices = []
        i = 0
        for key, name, value in form.author.iter_choices():
            self.assertEqual(key, keys[i])
            i += 1


class TestFields(TestCase):
    class GeoTestForm(Form):
        geo = GeoPtPropertyField()

    def test_geopt_property(self):
        form = self.GeoTestForm(DummyPostData(geo='5.0, -7.0'))
        self.assertTrue(form.validate())
        self.assertEqual(form.geo.data, '5.0,-7.0')
        form = self.GeoTestForm(DummyPostData(geo='5.0,-f'))
        self.assertFalse(form.validate())

########NEW FILE########
__FILENAME__ = ext_csrf
from __future__ import unicode_literals

from unittest import TestCase

from wtforms.fields import TextField
from wtforms.ext.csrf import SecureForm
from wtforms.ext.csrf.session import SessionSecureForm

import datetime
import hashlib
import hmac

class DummyPostData(dict):
    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v

class InsecureForm(SecureForm):
    def generate_csrf_token(self, csrf_context):
        return csrf_context

    a = TextField()

class FakeSessionRequest(object):
    def __init__(self, session):
        self.session = session

class StupidObject(object):
    a = None
    csrf_token = None


class SecureFormTest(TestCase):
    def test_base_class(self):
        self.assertRaises(NotImplementedError, SecureForm)

    def test_basic_impl(self):
        form = InsecureForm(csrf_context=42)
        self.assertEqual(form.csrf_token.current_token, 42)
        self.assertFalse(form.validate())
        self.assertEqual(len(form.csrf_token.errors), 1)
        self.assertEqual(form.csrf_token._value(), 42)
        # Make sure csrf_token is taken out from .data
        self.assertEqual(form.data, {'a': None})

    def test_with_data(self):
        post_data = DummyPostData(csrf_token='test', a='hi')
        form = InsecureForm(post_data, csrf_context='test')
        self.assertTrue(form.validate())
        self.assertEqual(form.data, {'a': 'hi'})

        form = InsecureForm(post_data, csrf_context='something')
        self.assertFalse(form.validate())

        # Make sure that value is still the current token despite
        # the posting of a different value
        self.assertEqual(form.csrf_token._value(), 'something')

        # Make sure populate_obj doesn't overwrite the token
        obj = StupidObject()
        form.populate_obj(obj)
        self.assertEqual(obj.a, 'hi')
        self.assertEqual(obj.csrf_token, None)

    def test_with_missing_token(self):
        post_data = DummyPostData(a='hi')
        form = InsecureForm(post_data, csrf_context='test')
        self.assertFalse(form.validate())

        self.assertEqual(form.csrf_token.data, '')
        self.assertEqual(form.csrf_token._value(), 'test')



class SessionSecureFormTest(TestCase):
    class SSF(SessionSecureForm):
        SECRET_KEY = 'abcdefghijklmnop'.encode('ascii')

    class BadTimeSSF(SessionSecureForm):
        SECRET_KEY = 'abcdefghijklmnop'.encode('ascii')
        TIME_LIMIT = datetime.timedelta(-1, 86300)

    class NoTimeSSF(SessionSecureForm):
        SECRET_KEY = 'abcdefghijklmnop'.encode('ascii')
        TIME_LIMIT = None

    def test_basic(self):
        self.assertRaises(Exception, SessionSecureForm)
        self.assertRaises(TypeError, self.SSF)
        session = {}
        form = self.SSF(csrf_context=FakeSessionRequest(session))
        assert 'csrf' in session

    def test_timestamped(self):
        session = {}
        postdata = DummyPostData(csrf_token='fake##fake')
        form = self.SSF(postdata, csrf_context=session)
        assert 'csrf' in session
        assert form.csrf_token._value()
        assert form.csrf_token._value() != session['csrf']
        assert not form.validate()
        self.assertEqual(form.csrf_token.errors[0], 'CSRF failed')
        good_token = form.csrf_token._value()

        # Now test a valid CSRF with invalid timestamp
        evil_form = self.BadTimeSSF(csrf_context=session)
        bad_token = evil_form.csrf_token._value()
        
        postdata = DummyPostData(csrf_token=bad_token)
        form = self.SSF(postdata, csrf_context=session)
        assert not form.validate()
        self.assertEqual(form.csrf_token.errors[0], 'CSRF token expired')


    def test_notime(self):
        session = {}
        form = self.NoTimeSSF(csrf_context=session)
        hmacced = hmac.new(form.SECRET_KEY, session['csrf'].encode('utf8'), digestmod=hashlib.sha1)
        self.assertEqual(form.csrf_token._value(), '##%s' % hmacced.hexdigest())
        assert not form.validate()
        self.assertEqual(form.csrf_token.errors[0], 'CSRF token missing')

        # Test with pre-made values
        session = {'csrf': '00e9fa5fe507251ac5f32b1608e9282f75156a05'}
        postdata = DummyPostData(csrf_token='##d21f54b7dd2041fab5f8d644d4d3690c77beeb14')

        form = self.NoTimeSSF(postdata, csrf_context=session)
        assert form.validate()

########NEW FILE########
__FILENAME__ = ext_dateutil
#!/usr/bin/env python
from __future__ import unicode_literals

from datetime import datetime, date
from unittest import TestCase

from wtforms.form import Form
from wtforms.ext.dateutil.fields import DateTimeField, DateField


class DummyPostData(dict):
    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v

class DateutilTest(TestCase):
    class F(Form):
        a = DateTimeField()
        b = DateField(default=lambda: date(2004, 9, 12))
        c = DateField(parse_kwargs=dict(yearfirst=True, dayfirst=False))

    def test_form_input(self):
        f = self.F(DummyPostData(a='2008/09/12 4:17 PM', b='04/05/06', c='04/05/06'))
        self.assertEqual(f.a.data, datetime(2008, 9, 12, 16, 17))
        self.assertEqual(f.a._value(), '2008/09/12 4:17 PM')
        self.assertEqual(f.b.data, date(2006, 4, 5))
        self.assertEqual(f.c.data, date(2004, 5, 6))
        self.assertTrue(f.validate())
        f = self.F(DummyPostData(a='Grok Grarg Rawr'))
        self.assertFalse(f.validate())

    def test_blank_input(self):
        f = self.F(DummyPostData(a='', b=''))
        self.assertEqual(f.a.data, None)
        self.assertEqual(f.b.data, None)
        self.assertFalse(f.validate())

    def test_defaults_display(self):
        f = self.F(a=datetime(2001, 11, 15))
        self.assertEqual(f.a.data, datetime(2001, 11, 15))
        self.assertEqual(f.a._value(), '2001-11-15 00:00')
        self.assertEqual(f.b.data, date(2004, 9, 12))
        self.assertEqual(f.b._value(), '2004-09-12')
        self.assertEqual(f.c.data, None)
        self.assertTrue(f.validate())

    def test_render(self):
        f = self.F()
        self.assertEqual(f.b(), r'<input id="b" name="b" type="text" value="2004-09-12">')


if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db import models
from django.contrib.localflavor.us.models import USStateField

class Group(models.Model):
    name  = models.CharField(max_length=20)

    def __unicode__(self):
        return '%s(%d)' % (self.name, self.pk)

    __str__ = __unicode__

class User(models.Model):
    username = models.CharField(max_length=40)
    group    = models.ForeignKey(Group)
    birthday = models.DateField(help_text="Teh Birthday")
    email    = models.EmailField(blank=True)
    posts    = models.PositiveSmallIntegerField()
    state    = USStateField()
    reg_ip   = models.IPAddressField("IP Addy")
    url      = models.URLField()
    file     = models.FilePathField()
    file2    = models.FileField(upload_to='.')
    bool     = models.BooleanField()
    time1    = models.TimeField()
    slug     = models.SlugField()


########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python

from __future__ import unicode_literals

import sys, os
TESTS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, TESTS_DIR)

##########################################################################
# -- Django Initialization
#
# Unfortunately, we cannot do this in the setUp for a test case, as the
# settings.configure method cannot be called more than once, and we cannot
# control the order in which tests are run, so making a throwaway test won't
# work either.

from django.conf import settings
settings.configure(
    INSTALLED_APPS = ['ext_django', 'wtforms.ext.django'],
    # Django 1.0 to 1.3
    DATABASE_ENGINE = 'sqlite3',
    TEST_DATABASE_NAME = ':memory:',

    # Django 1.4
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:'
        }
    }
)

from django.db import connection
connection.creation.create_test_db(verbosity=0)

# -- End hacky Django initialization

from django.template import Context, Template
from django.test import TestCase as DjangoTestCase
from ext_django import models as test_models
from unittest import TestCase
from wtforms import Form, fields, validators
from wtforms.compat import text_type
from wtforms.ext.django.orm import model_form
from wtforms.ext.django.fields import QuerySetSelectField, ModelSelectField

def contains_validator(field, v_type):
    for v in field.validators:
        if isinstance(v, v_type):
            return True
    return False

def lazy_select(field, **kwargs):
    output = []
    for val, label, selected in field.iter_choices():
        s = selected and 'Y' or 'N'
        output.append('%s:%s:%s' % (s, text_type(val), text_type(label)))
    return tuple(output)

class DummyPostData(dict):
    def getlist(self, key):
        return self[key]

class TemplateTagsTest(TestCase):
    load_tag = '{% load wtforms %}'

    class F(Form):
        a = fields.TextField('I r label')
        b = fields.SelectField(choices=[('a', 'hi'), ('b', 'bai')])

    def _render(self, source):
        t = Template(self.load_tag + source)
        return t.render(Context({'form': self.F(), 'a': self.F().a,  'someclass': "CLASSVAL>!"}))

    def test_simple_print(self):
        self.assertEqual(self._render('{% autoescape off %}{{ form.a }}{% endautoescape %}'), '<input id="a" name="a" type="text" value="">')
        self.assertEqual(self._render('{% autoescape off %}{{ form.a.label }}{% endautoescape %}'), '<label for="a">I r label</label>')
        self.assertEqual(self._render('{% autoescape off %}{{ form.a.name }}{% endautoescape %}'), 'a')

    def test_form_field(self):
        self.assertEqual(self._render('{% form_field form.a %}'), '<input id="a" name="a" type="text" value="">')
        self.assertEqual(self._render('{% form_field a class=someclass onclick="alert()" %}'),
                         '<input class="CLASSVAL&gt;!" id="a" name="a" onclick="alert()" type="text" value="">')

class ModelFormTest(TestCase):
    F = model_form(test_models.User, exclude=['id'], field_args = {
        'posts': {
            'validators': [validators.NumberRange(min=4, max=7)],
            'description': 'Test'
        }
    })
    form = F()
    form_with_pk = model_form(test_models.User)()

    def test_form_sanity(self):
        self.assertEqual(self.F.__name__, 'UserForm')
        self.assertEqual(len([x for x in self.form]), 13)
        self.assertEqual(len([x for x in self.form_with_pk]), 14)

    def test_label(self):
        self.assertEqual(self.form.reg_ip.label.text, 'IP Addy')
        self.assertEqual(self.form.posts.label.text, 'posts')

    def test_description(self):
        self.assertEqual(self.form.birthday.description, 'Teh Birthday')

    def test_max_length(self):
        self.assertTrue(contains_validator(self.form.username, validators.Length))
        self.assertFalse(contains_validator(self.form.posts, validators.Length))

    def test_optional(self):
        self.assertTrue(contains_validator(self.form.email, validators.Optional))

    def test_simple_fields(self):
        self.assertEqual(type(self.form.file), fields.FileField)
        self.assertEqual(type(self.form.file2), fields.FileField)
        self.assertEqual(type(self.form_with_pk.id), fields.IntegerField)
        self.assertEqual(type(self.form.slug), fields.TextField)
        self.assertEqual(type(self.form.birthday), fields.DateField)

    def test_custom_converters(self):
        self.assertEqual(type(self.form.email), fields.TextField)
        self.assertTrue(contains_validator(self.form.email, validators.Email))
        self.assertEqual(type(self.form.reg_ip), fields.TextField)
        self.assertTrue(contains_validator(self.form.reg_ip, validators.IPAddress))
        self.assertEqual(type(self.form.group_id), ModelSelectField)

    def test_us_states(self):
        self.assertTrue(len(self.form.state.choices) >= 50)

    def test_field_args(self):
        self.assertTrue(contains_validator(self.form.posts, validators.NumberRange))
        self.assertEqual(self.form.posts.description, 'Test')

class QuerySetSelectFieldTest(DjangoTestCase):
    fixtures = ['ext_django.json']

    def setUp(self):
        from django.core.management import call_command
        self.queryset = test_models.Group.objects.all()
        class F(Form):
            a = QuerySetSelectField(allow_blank=True, get_label='name', widget=lazy_select)
            b = QuerySetSelectField(queryset=self.queryset, widget=lazy_select)

        self.F = F

    def test_queryset_freshness(self):
        form = self.F()
        self.assertTrue(form.b.queryset is not self.queryset)

    def test_with_data(self):
        form = self.F()
        form.a.queryset = self.queryset[1:]
        self.assertEqual(form.a(), ('Y:__None:', 'N:2:Admins'))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.validate(form), True)
        self.assertEqual(form.b.validate(form), False)
        form.b.data = test_models.Group.objects.get(pk=1)
        self.assertEqual(form.b.validate(form), True)
        self.assertEqual(form.b(), ('Y:1:Users(1)', 'N:2:Admins(2)'))

    def test_formdata(self):
        form = self.F(DummyPostData(a=['1'], b=['3']))
        form.a.queryset = self.queryset[1:]
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.validate(form), True)
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b.validate(form), False)
        form = self.F(DummyPostData(b=[2]))
        self.assertEqual(form.b.data.pk, 2)
        self.assertEqual(form.b.validate(form), True)


class ModelSelectFieldTest(DjangoTestCase):
    fixtures = ['ext_django.json']

    class F(Form):
        a = ModelSelectField(model=test_models.Group, widget=lazy_select)

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), ('N:1:Users(1)', 'N:2:Admins(2)'))


if __name__ == '__main__':
    import unittest
    unittest.main()

########NEW FILE########
__FILENAME__ = ext_i18n
from __future__ import unicode_literals

from unittest import TestCase
from wtforms.ext.i18n.utils import get_translations

class I18NTest(TestCase):
    def test_failure(self):
        self.assertRaises(IOError, get_translations, [])

    def test_us_translation(self):
        translations = get_translations(['en_US'])
        self.assertEqual(translations.gettext('Invalid Mac address.'), 'Invalid MAC address.')


if __name__ == '__main__':
    from unittest import main
    main()


########NEW FILE########
__FILENAME__ = ext_sqlalchemy
#!/usr/bin/env python
from __future__ import unicode_literals

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.schema import MetaData, Table, Column, ColumnDefault
from sqlalchemy.types import String, Integer, Date
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from unittest import TestCase

from wtforms.compat import text_type, iteritems
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.form import Form
from wtforms.fields import TextField
from wtforms.ext.sqlalchemy.orm import model_form
from wtforms.validators import Optional, Required, Length
from wtforms.ext.sqlalchemy.validators import Unique


class LazySelect(object):
    def __call__(self, field, **kwargs):
        return list((val, text_type(label), selected) for val, label, selected in field.iter_choices())

class DummyPostData(dict):
    def getlist(self, key):
        return self[key]

class Base(object):
    def __init__(self, **kwargs):
        for k, v in iteritems(kwargs):
            setattr(self, k, v)

class TestBase(TestCase):
    def _do_tables(self, mapper, engine):
        metadata = MetaData()

        test_table = Table('test', metadata,
            Column('id', Integer, primary_key=True, nullable=False),
            Column('name', String, nullable=False),
        )

        pk_test_table = Table('pk_test', metadata,
            Column('foobar', String, primary_key=True, nullable=False),
            Column('baz', String, nullable=False),
        )

        Test = type(str('Test'), (Base, ), {})
        PKTest = type(str('PKTest'), (Base, ), {
            '__unicode__': lambda x: x.baz,
            '__str__': lambda x: x.baz,
        })

        mapper(Test, test_table, order_by=[test_table.c.name])
        mapper(PKTest, pk_test_table, order_by=[pk_test_table.c.baz])
        self.Test = Test
        self.PKTest = PKTest

        metadata.create_all(bind=engine)

    def _fill(self, sess):
        for i, n in [(1, 'apple'),(2, 'banana')]:
            s = self.Test(id=i, name=n)
            p = self.PKTest(foobar='hello%s' % (i, ), baz=n)
            sess.add(s)
            sess.add(p)
        sess.flush()
        sess.commit()


class QuerySelectFieldTest(TestBase):
    def setUp(self):
        engine = create_engine('sqlite:///:memory:', echo=False)
        self.Session = sessionmaker(bind=engine)
        from sqlalchemy.orm import mapper
        self._do_tables(mapper, engine)

    def test_without_factory(self):
        sess = self.Session()
        self._fill(sess)
        class F(Form):
            a = QuerySelectField(get_label='name', widget=LazySelect(), get_pk=lambda x: x.id)
        form = F(DummyPostData(a=['1']))
        form.a.query = sess.query(self.Test)
        self.assertTrue(form.a.data is not None)
        self.assertEqual(form.a.data.id, 1)
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False)])
        self.assertTrue(form.validate())

    def test_with_query_factory(self):
        sess = self.Session()
        self._fill(sess)

        class F(Form):
            a = QuerySelectField(get_label=(lambda model: model.name), query_factory=lambda:sess.query(self.Test), widget=LazySelect())
            b = QuerySelectField(allow_blank=True, query_factory=lambda:sess.query(self.PKTest), widget=LazySelect())

        form = F()
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a(), [('1', 'apple', False), ('2', 'banana', False)])
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b(), [('__None', '', True), ('hello1', 'apple', False), ('hello2', 'banana', False)])
        self.assertFalse(form.validate())

        form = F(DummyPostData(a=['1'], b=['hello2']))
        self.assertEqual(form.a.data.id, 1)
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False)])
        self.assertEqual(form.b.data.baz, 'banana')
        self.assertEqual(form.b(), [('__None', '', False), ('hello1', 'apple', False), ('hello2', 'banana', True)])
        self.assertTrue(form.validate())

        # Make sure the query is cached
        sess.add(self.Test(id=3, name='meh'))
        sess.flush()
        sess.commit()
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False)])
        form.a._object_list = None
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False), ('3', 'meh', False)])

        # Test bad data
        form = F(DummyPostData(b=['bogus'], a=['fail']))
        assert not form.validate()
        self.assertEqual(form.b.errors, ['Not a valid choice'])


class QuerySelectMultipleFieldTest(TestBase):
    def setUp(self):
        from sqlalchemy.orm import mapper
        engine = create_engine('sqlite:///:memory:', echo=False)
        Session = sessionmaker(bind=engine)
        self._do_tables(mapper, engine)
        self.sess = Session()
        self._fill(self.sess)

    class F(Form):
        a = QuerySelectMultipleField(get_label='name', widget=LazySelect())

    def test_unpopulated_default(self):
        form = self.F()
        self.assertEqual([], form.a.data)

    def test_single_value_without_factory(self):
        form = self.F(DummyPostData(a=['1']))
        form.a.query = self.sess.query(self.Test)
        self.assertEqual([1], [v.id for v in form.a.data])
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', False)])
        self.assertTrue(form.validate())

    def test_multiple_values_without_query_factory(self):
        form = self.F(DummyPostData(a=['1', '2']))
        form.a.query = self.sess.query(self.Test)
        self.assertEqual([1, 2], [v.id for v in form.a.data])
        self.assertEqual(form.a(), [('1', 'apple', True), ('2', 'banana', True)])
        self.assertTrue(form.validate())

        form = self.F(DummyPostData(a=['1', '3']))
        form.a.query = self.sess.query(self.Test)
        self.assertEqual([x.id for x in form.a.data], [1])
        self.assertFalse(form.validate())

    def test_single_default_value(self):
        first_test = self.sess.query(self.Test).get(2)
        class F(Form):
            a = QuerySelectMultipleField(get_label='name', default=[first_test],
                widget=LazySelect(), query_factory=lambda: self.sess.query(self.Test))
        form = F()
        self.assertEqual([v.id for v in form.a.data], [2])
        self.assertEqual(form.a(), [('1', 'apple', False), ('2', 'banana', True)])
        self.assertTrue(form.validate())


class ModelFormTest(TestCase):
    def setUp(self):
        Model = declarative_base()

        student_course = Table(
            'student_course', Model.metadata,
            Column('student_id', Integer, ForeignKey('student.id')),
            Column('course_id', Integer, ForeignKey('course.id'))
        )

        class Course(Model):
            __tablename__ = "course"
            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)

        class School(Model):
            __tablename__ = "school"
            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)

        class Student(Model):
            __tablename__ = "student"
            id = Column(Integer, primary_key=True)
            full_name = Column(String(255), nullable=False, unique=True)
            dob = Column(Date(), nullable=True)
            current_school_id = Column(Integer, ForeignKey(School.id),
                nullable=False)

            current_school = relationship(School, backref=backref('students'))
            courses = relationship("Course", secondary=student_course,
                backref=backref("students", lazy='dynamic'))

        self.School = School
        self.Student = Student

        engine = create_engine('sqlite:///:memory:', echo=False)
        Session = sessionmaker(bind=engine)
        self.metadata = Model.metadata
        self.metadata.create_all(bind=engine)
        self.sess = Session()

    def test_nullable_field(self):
        student_form = model_form(self.Student, self.sess)()
        self.assertTrue(issubclass(Optional,
            student_form._fields['dob'].validators[0].__class__))

    def test_required_field(self):
        student_form = model_form(self.Student, self.sess)()
        self.assertTrue(issubclass(Required,
            student_form._fields['full_name'].validators[0].__class__))

    def test_unique_field(self):
        student_form = model_form(self.Student, self.sess)()
        self.assertTrue(issubclass(Unique,
            student_form._fields['full_name'].validators[1].__class__))

    def test_include_pk(self):
        form_class = model_form(self.Student, self.sess, exclude_pk=False)
        student_form = form_class()
        self.assertIn('id', student_form._fields)

    def test_exclude_pk(self):
        form_class = model_form(self.Student, self.sess, exclude_pk=True)
        student_form = form_class()
        self.assertNotIn('id', student_form._fields)

    def test_exclude_fk(self):
        student_form = model_form(self.Student, self.sess)()
        self.assertNotIn('current_school_id', student_form._fields)

    def test_include_fk(self):
        student_form = model_form(self.Student, self.sess, exclude_fk=False)()
        self.assertIn('current_school_id', student_form._fields)

    def test_convert_many_to_one(self):
        student_form = model_form(self.Student, self.sess)()
        self.assertTrue(issubclass(QuerySelectField,
            student_form._fields['current_school'].__class__))

    def test_convert_one_to_many(self):
        school_form = model_form(self.School, self.sess)()
        self.assertTrue(issubclass(QuerySelectMultipleField,
            school_form._fields['students'].__class__))

    def test_convert_many_to_many(self):
        student_form = model_form(self.Student, self.sess)()
        self.assertTrue(issubclass(QuerySelectMultipleField,
            student_form._fields['courses'].__class__))


class ModelFormColumnDefaultTest(TestCase):

    def setUp(self):
        Model = declarative_base()

        def default_score():
            return 5

        class StudentDefaultScoreCallable(Model):
            __tablename__ = "course"
            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)
            score = Column(Integer, default=default_score, nullable=False)

        class StudentDefaultScoreScalar(Model):
            __tablename__ = "school"
            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)
            # Default scalar value
            score = Column(Integer, default=10, nullable=False)

        self.StudentDefaultScoreCallable = StudentDefaultScoreCallable
        self.StudentDefaultScoreScalar = StudentDefaultScoreScalar

        engine = create_engine('sqlite:///:memory:', echo=False)
        Session = sessionmaker(bind=engine)
        self.metadata = Model.metadata
        self.metadata.create_all(bind=engine)
        self.sess = Session()

    def test_column_default_callable(self):
        student_form = model_form(self.StudentDefaultScoreCallable, self.sess)()
        self.assertEqual(student_form._fields['score'].default, 5)

    def test_column_default_scalar(self):
        student_form = model_form(self.StudentDefaultScoreScalar, self.sess)()
        self.assertNotIsInstance(student_form._fields['score'].default, ColumnDefault)
        self.assertEqual(student_form._fields['score'].default, 10)


class UniqueValidatorTest(TestCase):
    def setUp(self):
        Model = declarative_base()

        class User(Model):
            __tablename__ = "user"
            id = Column(Integer, primary_key=True)
            username = Column(String(255), nullable=False, unique=True)

        engine = create_engine('sqlite:///:memory:', echo=False)
        Session = sessionmaker(bind=engine)
        self.metadata = Model.metadata
        self.metadata.create_all(bind=engine)
        self.sess = Session()

        self.sess.add(User(username='batman'))
        self.sess.commit()

        class UserForm(Form):
            username = TextField('Username', [
                Length(min=4, max=25),
                Unique(lambda: self.sess, User, User.username)
            ])

        self.UserForm = UserForm

    def test_validate(self):
        user_form = self.UserForm(DummyPostData(username=['spiderman']))
        self.assertTrue(user_form.validate())

    def test_wrong(self):
        user_form = self.UserForm(DummyPostData(username=['batman']))
        self.assertFalse(user_form.validate())


if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = fields
#!/usr/bin/env python
from __future__ import unicode_literals

import sys

from datetime import date, datetime
from decimal import Decimal, ROUND_UP, ROUND_DOWN
from unittest import TestCase

from wtforms import validators, widgets
from wtforms.fields import *
from wtforms.fields import Label, Field
from wtforms.form import Form
from wtforms.compat import text_type


PYTHON_VERSION = sys.version_info

class DummyPostData(dict):
    def getlist(self, key):
        v = self[key]
        if not isinstance(v, (list, tuple)):
            v = [v]
        return v

class AttrDict(object):
    def __init__(self, *args, **kw):
        self.__dict__.update(*args, **kw)

def make_form(_name='F', **fields):
    return type(str(_name), (Form, ), fields)


class DefaultsTest(TestCase):
    def test(self):
        expected = 42

        def default_callable():
            return expected

        test_value = TextField(default=expected).bind(Form(), 'a')
        test_value.process(None)
        self.assertEqual(test_value.data, expected)

        test_callable = TextField(default=default_callable).bind(Form(), 'a')
        test_callable.process(None)
        self.assertEqual(test_callable.data, expected)


class LabelTest(TestCase):
    def test(self):
        expected = """<label for="test">Caption</label>"""
        label = Label('test', 'Caption')
        self.assertEqual(label(), expected)
        self.assertEqual(str(label), expected)
        self.assertEqual(text_type(label), expected)
        self.assertEqual(label.__html__(), expected)
        self.assertEqual(label().__html__(), expected)
        self.assertEqual(label('hello'), """<label for="test">hello</label>""")
        self.assertEqual(TextField('hi').bind(Form(), 'a').label.text, 'hi')
        if PYTHON_VERSION < (3,):
            self.assertEqual(repr(label), "Label(u'test', u'Caption')")
        else:
            self.assertEqual(repr(label), "Label('test', 'Caption')")

    def test_auto_label(self):
        t1 = TextField().bind(Form(), 'foo_bar')
        self.assertEqual(t1.label.text, 'Foo Bar')

        t2 = TextField('').bind(Form(), 'foo_bar')
        self.assertEqual(t2.label.text, '')


class FlagsTest(TestCase):
    def setUp(self):
        t = TextField(validators=[validators.Required()]).bind(Form(), 'a')
        self.flags = t.flags

    def test_existing_values(self):
        self.assertEqual(self.flags.required, True)
        self.assertTrue('required' in self.flags)
        self.assertEqual(self.flags.optional, False)
        self.assertTrue('optional' not in self.flags)

    def test_assignment(self):
        self.assertTrue('optional' not in self.flags)
        self.flags.optional = True
        self.assertEqual(self.flags.optional, True)
        self.assertTrue('optional' in self.flags)

    def test_unset(self):
        self.flags.required = False
        self.assertEqual(self.flags.required, False)
        self.assertTrue('required' not in self.flags)

    def test_repr(self):
        self.assertEqual(repr(self.flags), '<wtforms.fields.Flags: {required}>')


class FiltersTest(TestCase):
    class F(Form):
        a = TextField(default=' hello', filters=[lambda x: x.strip()])
        b = TextField(default='42', filters=[lambda x: int(x)])

    def test_working(self):
        form = self.F()
        self.assertEqual(form.a.data, 'hello')
        self.assertEqual(form.b.data, 42)
        assert form.validate()

    def test_failure(self):
        form = self.F(DummyPostData(a=['  foo bar  '], b=['hi']))
        self.assertEqual(form.a.data, 'foo bar')
        self.assertEqual(form.b.data, 'hi')
        self.assertEqual(len(form.b.process_errors), 1)
        assert not form.validate()


class FieldTest(TestCase):
    class F(Form):
        a = TextField(default='hello')

    def setUp(self):
        self.field = self.F().a

    def test_unbound_field(self):
        unbound = self.F.a
        assert unbound.creation_counter != 0
        assert unbound.field_class is TextField
        self.assertEqual(unbound.args, ())
        self.assertEqual(unbound.kwargs, {'default': 'hello'})
        assert repr(unbound).startswith('<UnboundField(TextField')

    def test_htmlstring(self):
        self.assertTrue(isinstance(self.field.__html__(), widgets.HTMLString))

    def test_str_coerce(self):
        self.assertTrue(isinstance(str(self.field), str))
        self.assertEqual(str(self.field), str(self.field()))

    def test_unicode_coerce(self):
        self.assertEqual(text_type(self.field), self.field())

    def test_process_formdata(self):
        Field.process_formdata(self.field, [42])
        self.assertEqual(self.field.data, 42)


class PrePostTestField(TextField):
    def pre_validate(self, form):
        if self.data == "stoponly":
            raise validators.StopValidation()
        elif self.data.startswith("stop"):
            raise validators.StopValidation("stop with message")

    def post_validate(self, form, stopped):
        if self.data == "p":
            raise ValueError("Post")
        elif stopped and self.data == "stop-post":
            raise ValueError("Post-stopped")


class PrePostValidationTest(TestCase):
    class F(Form):
        a = PrePostTestField(validators=[validators.Length(max=1, message="too long")])

    def _init_field(self, value):
        form = self.F(a=value)
        form.validate()
        return form.a

    def test_pre_stop(self):
        a = self._init_field("long")
        self.assertEqual(a.errors, ["too long"])

        stoponly = self._init_field("stoponly")
        self.assertEqual(stoponly.errors, [])

        stopmessage = self._init_field("stopmessage")
        self.assertEqual(stopmessage.errors, ["stop with message"])

    def test_post(self):
        a = self._init_field("p")
        self.assertEqual(a.errors, ["Post"])
        stopped = self._init_field("stop-post")
        self.assertEqual(stopped.errors, ["stop with message", "Post-stopped"])


class SelectFieldTest(TestCase):
    class F(Form):
        a = SelectField(choices=[('a', 'hello'), ('btest','bye')], default='a')
        b = SelectField(choices=[(1, 'Item 1'), (2, 'Item 2')], coerce=int, option_widget=widgets.TextInput())

    def test_defaults(self):
        form = self.F()
        self.assertEqual(form.a.data, 'a')
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.validate(), False)
        self.assertEqual(form.a(), """<select id="a" name="a"><option selected value="a">hello</option><option value="btest">bye</option></select>""")
        self.assertEqual(form.b(), """<select id="b" name="b"><option value="1">Item 1</option><option value="2">Item 2</option></select>""")

    def test_with_data(self):
        form = self.F(DummyPostData(a=['btest']))
        self.assertEqual(form.a.data, 'btest')
        self.assertEqual(form.a(), """<select id="a" name="a"><option value="a">hello</option><option selected value="btest">bye</option></select>""")

    def test_value_coercion(self):
        form = self.F(DummyPostData(b=['2']))
        self.assertEqual(form.b.data, 2)
        self.assertTrue(form.b.validate(form))
        form = self.F(DummyPostData(b=['b']))
        self.assertEqual(form.b.data, None)
        self.assertFalse(form.b.validate(form))

    def test_iterable_options(self):
        form = self.F()
        first_option = list(form.a)[0]
        self.assertTrue(isinstance(first_option, form.a._Option))
        self.assertEqual(list(text_type(x) for x in form.a), ['<option selected value="a">hello</option>',
                                                            '<option value="btest">bye</option>'])
        self.assertTrue(isinstance(first_option.widget, widgets.Option))
        self.assertTrue(isinstance(list(form.b)[0].widget, widgets.TextInput))
        self.assertEqual(first_option(disabled=True), '<option disabled selected value="a">hello</option>')

    def test_default_coerce(self):
        F = make_form(a=SelectField(choices=[('a', 'Foo')]))
        form = F(DummyPostData(a=[]))
        assert not form.validate()
        self.assertEqual(form.a.data, 'None')
        self.assertEqual(len(form.a.errors), 1)
        self.assertEqual(form.a.errors[0], 'Not a valid choice')


class SelectMultipleFieldTest(TestCase):
    class F(Form):
        a = SelectMultipleField(choices=[('a', 'hello'), ('b','bye'), ('c', 'something')], default=('a', ))
        b = SelectMultipleField(coerce=int, choices=[(1, 'A'), (2, 'B'), (3, 'C')], default=("1", "3"))

    def test_defaults(self):
        form = self.F()
        self.assertEqual(form.a.data, ['a'])
        self.assertEqual(form.b.data, [1, 3])
        # Test for possible regression with null data
        form.a.data = None
        self.assertTrue(form.validate())
        self.assertEqual(list(form.a.iter_choices()), [(v, l, False) for v, l in form.a.choices])

    def test_with_data(self):
        form = self.F(DummyPostData(a=['a', 'c']))
        self.assertEqual(form.a.data, ['a', 'c'])
        self.assertEqual(list(form.a.iter_choices()), [('a', 'hello', True), ('b', 'bye', False), ('c', 'something', True)])
        self.assertEqual(form.b.data, [])
        form = self.F(DummyPostData(b=['1', '2']))
        self.assertEqual(form.b.data, [1, 2])
        self.assertTrue(form.validate())
        form = self.F(DummyPostData(b=['1', '2', '4']))
        self.assertEqual(form.b.data, [1, 2, 4])
        self.assertFalse(form.validate())


class RadioFieldTest(TestCase):
    class F(Form):
        a = RadioField(choices=[('a', 'hello'), ('b','bye')], default='a')
        b = RadioField(choices=[(1, 'Item 1'), (2, 'Item 2')], coerce=int)

    def test(self):
        form = self.F()
        self.assertEqual(form.a.data, 'a')
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.validate(), False)
        self.assertEqual(form.a(), """<ul id="a"><li><input checked id="a-0" name="a" type="radio" value="a"> <label for="a-0">hello</label></li><li><input id="a-1" name="a" type="radio" value="b"> <label for="a-1">bye</label></li></ul>""")
        self.assertEqual(form.b(), """<ul id="b"><li><input id="b-0" name="b" type="radio" value="1"> <label for="b-0">Item 1</label></li><li><input id="b-1" name="b" type="radio" value="2"> <label for="b-1">Item 2</label></li></ul>""")
        self.assertEqual([text_type(x) for x in form.a], ['<input checked id="a-0" name="a" type="radio" value="a">', '<input id="a-1" name="a" type="radio" value="b">'])

    def test_text_coercion(self):
        # Regression test for text coercsion scenarios where the value is a boolean.
        coerce_func = lambda x: False if x == 'False' else bool(x)
        F = make_form(a=RadioField(choices=[(True, 'yes'), (False, 'no')], coerce=coerce_func))
        form = F()
        self.assertEqual(form.a(), '<ul id="a"><li><input id="a-0" name="a" type="radio" value="True"> <label for="a-0">yes</label></li><li><input checked id="a-1" name="a" type="radio" value="False"> <label for="a-1">no</label></li></ul>')

class TextFieldTest(TestCase):
    class F(Form):
        a = TextField()

    def test(self):
        form = self.F()
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="">""")
        form = self.F(DummyPostData(a=['hello']))
        self.assertEqual(form.a.data, 'hello')
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="hello">""")
        form = self.F(DummyPostData(b=['hello']))
        self.assertEqual(form.a.data, '')

class HiddenFieldTest(TestCase):
    class F(Form):
        a = HiddenField(default="LE DEFAULT")

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), """<input id="a" name="a" type="hidden" value="LE DEFAULT">""")


class TextAreaFieldTest(TestCase):
    class F(Form):
        a = TextAreaField(default="LE DEFAULT")

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), """<textarea id="a" name="a">LE DEFAULT</textarea>""")


class PasswordFieldTest(TestCase):
    class F(Form):
        a = PasswordField(widget=widgets.PasswordInput(hide_value=False), default="LE DEFAULT")
        b = PasswordField(default="Hai")

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), """<input id="a" name="a" type="password" value="LE DEFAULT">""")
        self.assertEqual(form.b(), """<input id="b" name="b" type="password" value="">""")


class FileFieldTest(TestCase):
    class F(Form):
        a = FileField(default="LE DEFAULT")

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), """<input id="a" name="a" type="file" value="LE DEFAULT">""")


class IntegerFieldTest(TestCase):
    class F(Form):
        a = IntegerField()
        b = IntegerField(default=48)

    def test(self):
        form = self.F(DummyPostData(a=['v'], b=['-15']))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.raw_data, ['v'])
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="v">""")
        self.assertEqual(form.b.data, -15)
        self.assertEqual(form.b(), """<input id="b" name="b" type="text" value="-15">""")
        self.assertTrue(not form.a.validate(form))
        self.assertTrue(form.b.validate(form))
        form = self.F(DummyPostData(a=[], b=['']))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.raw_data, [])
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b.raw_data, [''])
        self.assertTrue(not form.validate())
        self.assertEqual(len(form.b.process_errors), 1)
        self.assertEqual(len(form.b.errors), 1)
        form = self.F(b=9)
        self.assertEqual(form.b.data, 9)
        self.assertEqual(form.a._value(), '')
        self.assertEqual(form.b._value(), '9')


class DecimalFieldTest(TestCase):
    def test(self):
        F = make_form(a=DecimalField())
        form = F(DummyPostData(a='2.1'))
        self.assertEqual(form.a.data, Decimal('2.1'))
        self.assertEqual(form.a._value(), '2.1')
        form.a.raw_data = None
        self.assertEqual(form.a._value(), '2.10')
        self.assertTrue(form.validate())
        form = F(DummyPostData(a='2,1'), a=Decimal(5))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.raw_data, ['2,1'])
        self.assertFalse(form.validate())


    def test_quantize(self):
        F = make_form(a=DecimalField(places=3, rounding=ROUND_UP), b=DecimalField(places=None))
        form = F(a=Decimal('3.1415926535'))
        self.assertEqual(form.a._value(), '3.142')
        form.a.rounding = ROUND_DOWN
        self.assertEqual(form.a._value(), '3.141')
        self.assertEqual(form.b._value(), '')
        form = F(a=3.14159265, b=72)
        self.assertEqual(form.a._value(), '3.142')
        self.assertTrue(isinstance(form.a.data, float))
        self.assertEqual(form.b._value(), '72')


class FloatFieldTest(TestCase):
    class F(Form):
        a = FloatField()
        b = FloatField(default=48.0)

    def test(self):
        form = self.F(DummyPostData(a=['v'], b=['-15.0']))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.raw_data, ['v'])
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="v">""")
        self.assertEqual(form.b.data, -15.0)
        self.assertEqual(form.b(), """<input id="b" name="b" type="text" value="-15.0">""")
        self.assertFalse(form.a.validate(form))
        self.assertTrue(form.b.validate(form))
        form = self.F(DummyPostData(a=[], b=['']))
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b.raw_data, [''])
        self.assertFalse(form.validate())
        self.assertEqual(len(form.b.process_errors), 1)
        self.assertEqual(len(form.b.errors), 1)
        form = self.F(b=9.0)
        self.assertEqual(form.b.data, 9.0)
        self.assertEqual(form.b._value(), "9.0")


class BooleanFieldTest(TestCase):
    class BoringForm(Form):
        bool1 = BooleanField()
        bool2 = BooleanField(default=True)

    obj = AttrDict(bool1=None, bool2=True)

    def test_defaults(self):
        # Test with no post data to make sure defaults work
        form = self.BoringForm()
        self.assertEqual(form.bool1.raw_data, None)
        self.assertEqual(form.bool1.data, False)
        self.assertEqual(form.bool2.data, True)

    def test_rendering(self):
        form = self.BoringForm(DummyPostData(bool2="x"))
        self.assertEqual(form.bool1(), '<input id="bool1" name="bool1" type="checkbox" value="y">')
        self.assertEqual(form.bool2(), '<input checked id="bool2" name="bool2" type="checkbox" value="x">')
        self.assertEqual(form.bool2.raw_data, ['x'])

    def test_with_postdata(self):
        form = self.BoringForm(DummyPostData(bool1=['a']))
        self.assertEqual(form.bool1.raw_data, ['a'])
        self.assertEqual(form.bool1.data, True)

    def test_with_model_data(self):
        form = self.BoringForm(obj=self.obj)
        self.assertEqual(form.bool1.data, False)
        self.assertEqual(form.bool1.raw_data, None)
        self.assertEqual(form.bool2.data, True)

    def test_with_postdata_and_model(self):
        form = self.BoringForm(DummyPostData(bool1=['y']), obj=self.obj)
        self.assertEqual(form.bool1.data, True)
        self.assertEqual(form.bool2.data, False)


class DateFieldTest(TestCase):
    class F(Form):
        a = DateField()
        b = DateField(format='%m/%d %Y')

    def test_basic(self):
        d = date(2008, 5, 7)
        form = self.F(DummyPostData(a=['2008-05-07'], b=['05/07', '2008']))
        self.assertEqual(form.a.data, d)
        self.assertEqual(form.a._value(), '2008-05-07')
        self.assertEqual(form.b.data, d)
        self.assertEqual(form.b._value(), '05/07 2008')

    def test_failure(self):
        form = self.F(DummyPostData(a=['2008-bb-cc'], b=['hi']))
        assert not form.validate()
        self.assertEqual(len(form.a.process_errors), 1)
        self.assertEqual(len(form.a.errors), 1)
        self.assertEqual(len(form.b.errors), 1)
        self.assertEqual(form.a.process_errors[0], 'Not a valid date value')


class DateTimeFieldTest(TestCase):
    class F(Form):
        a = DateTimeField()
        b = DateTimeField(format='%Y-%m-%d %H:%M')

    def test_basic(self):
        d = datetime(2008, 5, 5, 4, 30, 0, 0)
        form = self.F(DummyPostData(a=['2008-05-05', '04:30:00'], b=['2008-05-05 04:30']))
        self.assertEqual(form.a.data, d)
        self.assertEqual(form.a(), """<input id="a" name="a" type="text" value="2008-05-05 04:30:00">""")
        self.assertEqual(form.b.data, d)
        self.assertEqual(form.b(), """<input id="b" name="b" type="text" value="2008-05-05 04:30">""")
        self.assertTrue(form.validate())
        form = self.F(DummyPostData(a=['2008-05-05']))
        self.assertFalse(form.validate())
        self.assertEqual(form.a.errors[0], 'Not a valid datetime value')

    def test_microseconds(self):
        if PYTHON_VERSION < (2, 6):
            return # Microsecond formatting support was only added in 2.6

        d = datetime(2011, 5, 7, 3, 23, 14, 424200)
        F = make_form(a=DateTimeField(format='%Y-%m-%d %H:%M:%S.%f'))
        form = F(DummyPostData(a=['2011-05-07 03:23:14.4242']))
        self.assertEqual(d, form.a.data)


class SubmitFieldTest(TestCase):
    class F(Form):
        a = SubmitField('Label')

    def test(self):
        self.assertEqual(self.F().a(), """<input id="a" name="a" type="submit" value="Label">""")


class FormFieldTest(TestCase):
    def setUp(self):
        F = make_form(
            a = TextField(validators=[validators.required()]),
            b = TextField(),
        )
        self.F1 = make_form('F1', a = FormField(F))
        self.F2 = make_form('F2', a = FormField(F, separator='::'))

    def test_formdata(self):
        form = self.F1(DummyPostData({'a-a':['moo']}))
        self.assertEqual(form.a.form.a.name, 'a-a')
        self.assertEqual(form.a.form.a.data, 'moo')
        self.assertEqual(form.a.form.b.data, '')
        self.assertTrue(form.validate())

    def test_iteration(self):
        self.assertEqual([x.name for x in self.F1().a], ['a-a', 'a-b'])

    def test_with_obj(self):
        obj = AttrDict(a=AttrDict(a='mmm'))
        form = self.F1(obj=obj)
        self.assertEqual(form.a.form.a.data, 'mmm')
        self.assertEqual(form.a.form.b.data, None)
        obj_inner = AttrDict(a=None, b='rawr')
        obj2 = AttrDict(a=obj_inner)
        form.populate_obj(obj2)
        self.assertTrue(obj2.a is obj_inner)
        self.assertEqual(obj_inner.a, 'mmm')
        self.assertEqual(obj_inner.b, None)

    def test_widget(self):
        self.assertEqual(self.F1().a(), '''<table id="a"><tr><th><label for="a-a">A</label></th><td><input id="a-a" name="a-a" type="text" value=""></td></tr><tr><th><label for="a-b">B</label></th><td><input id="a-b" name="a-b" type="text" value=""></td></tr></table>''')

    def test_separator(self):
        form = self.F2(DummyPostData({'a-a': 'fake', 'a::a': 'real'}))
        self.assertEqual(form.a.a.name, 'a::a')
        self.assertEqual(form.a.a.data, 'real')
        self.assertTrue(form.validate())

    def test_no_validators_or_filters(self):
        class A(Form):
            a = FormField(self.F1, validators=[validators.required()])
        self.assertRaises(TypeError, A)
        class B(Form):
            a = FormField(self.F1, filters=[lambda x: x])
        self.assertRaises(TypeError, B)

        class C(Form):
            a = FormField(self.F1)
            def validate_a(form, field):
                pass
        form = C()
        self.assertRaises(TypeError, form.validate)


class FieldListTest(TestCase):
    t = TextField(validators=[validators.Required()])

    def test_form(self):
        F = make_form(a = FieldList(self.t))
        data = ['foo', 'hi', 'rawr']
        a = F(a=data).a
        self.assertEqual(a.entries[1].data, 'hi')
        self.assertEqual(a.entries[1].name, 'a-1')
        self.assertEqual(a.data, data)
        self.assertEqual(len(a.entries), 3)

        pdata = DummyPostData({'a-0': ['bleh'], 'a-3': ['yarg'], 'a-4': [''], 'a-7': ['mmm']})
        form = F(pdata)
        self.assertEqual(len(form.a.entries), 4)
        self.assertEqual(form.a.data, ['bleh', 'yarg', '', 'mmm'])
        self.assertFalse(form.validate())

        form = F(pdata, a=data)
        self.assertEqual(form.a.data, ['bleh', 'yarg', '', 'mmm'])
        self.assertFalse(form.validate())

        # Test for formdata precedence
        pdata = DummyPostData({'a-0': ['a'], 'a-1': ['b']})
        form = F(pdata, a=data)
        self.assertEqual(len(form.a.entries), 2)
        self.assertEqual(form.a.data, ['a', 'b'])

    def test_enclosed_subform(self):
        make_inner = lambda: AttrDict(a=None)
        F = make_form(
            a = FieldList(FormField(make_form('FChild', a=self.t), default=make_inner))
        )
        data = [{'a': 'hello'}]
        form = F(a=data)
        self.assertEqual(form.a.data, data)
        self.assertTrue(form.validate())
        form.a.append_entry()
        self.assertEqual(form.a.data, data + [{'a': None}])
        self.assertFalse(form.validate())

        pdata = DummyPostData({'a-0': ['fake'], 'a-0-a': ['foo'], 'a-1-a': ['bar']})
        form = F(pdata, a=data)
        self.assertEqual(form.a.data, [{'a': 'foo'}, {'a': 'bar'}])

        inner_obj = make_inner()
        inner_list = [inner_obj]
        obj = AttrDict(a=inner_list)
        form.populate_obj(obj)
        self.assertTrue(obj.a is not inner_list)
        self.assertEqual(len(obj.a), 2)
        self.assertTrue(obj.a[0] is inner_obj)
        self.assertEqual(obj.a[0].a, 'foo')
        self.assertEqual(obj.a[1].a, 'bar')

    def test_entry_management(self):
        F = make_form(a = FieldList(self.t))
        a = F(a=['hello', 'bye']).a
        self.assertEqual(a.pop_entry().name, 'a-1')
        self.assertEqual(a.data, ['hello'])
        a.append_entry('orange')
        self.assertEqual(a.data, ['hello', 'orange'])
        self.assertEqual(a[-1].name, 'a-1')
        self.assertEqual(a.pop_entry().data, 'orange')
        self.assertEqual(a.pop_entry().name, 'a-0')
        self.assertRaises(IndexError, a.pop_entry)

    def test_min_max_entries(self):
        F = make_form(a = FieldList(self.t, min_entries=1, max_entries=3))
        a = F().a
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0].data, None)
        big_input = ['foo',  'flaf', 'bar', 'baz']
        self.assertRaises(AssertionError, F, a=big_input)
        pdata = DummyPostData(('a-%d' % i, v) for i, v in enumerate(big_input))
        a = F(pdata).a
        self.assertEqual(a.data, ['foo', 'flaf', 'bar'])
        self.assertRaises(AssertionError, a.append_entry)

    def test_validators(self):
        def validator(form, field):
            if field.data and field.data[0] == 'fail':
                raise ValueError('fail')
            elif len(field.data) > 2:
                raise ValueError('too many')

        F = make_form(a = FieldList(self.t, validators=[validator]))

        # Case 1: length checking validators work as expected.
        fdata = DummyPostData({'a-0': ['hello'], 'a-1': ['bye'], 'a-2': ['test3']})
        form = F(fdata)
        assert not form.validate()
        self.assertEqual(form.a.errors, ['too many'])

        # Case 2: checking a value within.
        fdata['a-0'] = ['fail']
        form = F(fdata)
        assert not form.validate()
        self.assertEqual(form.a.errors, ['fail'])

        # Case 3: normal field validator still works
        form = F(DummyPostData({'a-0': ['']}))
        assert not form.validate()
        self.assertEqual(form.a.errors, [['This field is required.']])


if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = form
#!/usr/bin/env python
from __future__ import unicode_literals

from unittest import TestCase

from wtforms.form import BaseForm, Form
from wtforms.fields import TextField, IntegerField
from wtforms.validators import ValidationError


class DummyPostData(dict):
    def getlist(self, key):
        return self[key]

class BaseFormTest(TestCase):
    def get_form(self, **kwargs):
        def validate_test(form, field):
            if field.data != 'foobar':
                raise ValidationError('error')

        return BaseForm({'test': TextField(validators=[validate_test])}, **kwargs)

    def test_data_proxy(self):
        form = self.get_form()
        form.process(test='foo')
        self.assertEqual(form.data, {'test': 'foo'})

    def test_errors_proxy(self):
        form = self.get_form()
        form.process(test='foobar')
        form.validate()
        self.assertEqual(form.errors, {})

        form = self.get_form()
        form.process()
        form.validate()
        self.assertEqual(form.errors, {'test': ['error']})

    def test_contains(self):
        form = self.get_form()
        self.assertTrue('test' in form)
        self.assertTrue('abcd' not in form)

    def test_field_removal(self):
        form = self.get_form()
        del form['test']
        self.assertRaises(AttributeError, getattr, form, 'test')
        self.assertTrue('test' not in form)

    def test_field_adding(self):
        form = self.get_form()
        self.assertEqual(len(list(form)), 1)
        form['foo'] = TextField()
        self.assertEqual(len(list(form)), 2)
        form.process(DummyPostData(foo=['hello']))
        self.assertEqual(form['foo'].data, 'hello')
        form['test'] = IntegerField()
        self.assertTrue(isinstance(form['test'], IntegerField))
        self.assertEqual(len(list(form)), 2)
        self.assertRaises(AttributeError, getattr, form['test'], 'data')
        form.process(DummyPostData(test=['1']))
        self.assertEqual(form['test'].data, 1)
        self.assertEqual(form['foo'].data, '')

    def test_populate_obj(self):
        m = type(str('Model'), (object, ), {})
        form = self.get_form()
        form.process(test='foobar')
        form.populate_obj(m)
        self.assertEqual(m.test, 'foobar')
        self.assertEqual([k for k in dir(m) if not k.startswith('_')], ['test'])

    def test_prefixes(self):
        form = self.get_form(prefix='foo')
        self.assertEqual(form['test'].name, 'foo-test')
        self.assertEqual(form['test'].short_name, 'test')
        self.assertEqual(form['test'].id, 'foo-test')
        form = self.get_form(prefix='foo.')
        form.process(DummyPostData({'foo.test': ['hello'], 'test': ['bye']}))
        self.assertEqual(form['test'].data, 'hello')
        self.assertEqual(self.get_form(prefix='foo[')['test'].name, 'foo[-test')

    def test_formdata_wrapper_error(self):
        form = self.get_form()
        self.assertRaises(TypeError, form.process, [])


class FormMetaTest(TestCase):
    def test_monkeypatch(self):
        class F(Form):
            a = TextField()

        self.assertEqual(F._unbound_fields, None)
        F()
        self.assertEqual(F._unbound_fields, [('a', F.a)])
        F.b = TextField()
        self.assertEqual(F._unbound_fields, None)
        F()
        self.assertEqual(F._unbound_fields, [('a', F.a), ('b', F.b)])
        del F.a
        self.assertRaises(AttributeError, lambda: F.a)
        F()
        self.assertEqual(F._unbound_fields, [('b', F.b)])
        F._m = TextField()
        self.assertEqual(F._unbound_fields, [('b', F.b)])

    def test_subclassing(self):
        class A(Form):
            a = TextField()
            c = TextField()
        class B(A):
            b = TextField()
            c = TextField()
        A(); B()
        self.assertTrue(A.a is B.a)
        self.assertTrue(A.c is not B.c)
        self.assertEqual(A._unbound_fields, [('a', A.a), ('c', A.c)])
        self.assertEqual(B._unbound_fields, [('a', B.a), ('b', B.b), ('c', B.c)])

class FormTest(TestCase):
    class F(Form):
        test = TextField()
        def validate_test(form, field):
            if field.data != 'foobar':
                raise ValidationError('error')

    def test_validate(self):
        form = self.F(test='foobar')
        self.assertEqual(form.validate(), True)

        form = self.F()
        self.assertEqual(form.validate(), False)

    def test_field_adding_disabled(self):
        form = self.F()
        self.assertRaises(TypeError, form.__setitem__, 'foo', TextField())

    def test_field_removal(self):
        form = self.F()
        del form.test
        self.assertTrue('test' not in form)
        self.assertEqual(form.test, None)
        self.assertEqual(len(list(form)), 0)
        # Try deleting a nonexistent field
        self.assertRaises(AttributeError, form.__delattr__, 'fake')

    def test_ordered_fields(self):
        class MyForm(Form):
            strawberry = TextField()
            banana     = TextField()
            kiwi       = TextField()

        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'banana', 'kiwi'])
        MyForm.apple = TextField()
        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'banana', 'kiwi', 'apple'])
        del MyForm.banana
        self.assertEqual([x.name for x in MyForm()], ['strawberry', 'kiwi', 'apple'])
        MyForm.strawberry = TextField()
        self.assertEqual([x.name for x in MyForm()], ['kiwi', 'apple', 'strawberry'])
        # Ensure sort is stable: two fields with the same creation counter 
        # should be subsequently sorted by name.
        MyForm.cherry = MyForm.kiwi
        self.assertEqual([x.name for x in MyForm()], ['cherry', 'kiwi', 'apple', 'strawberry'])


if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys
from unittest import defaultTestLoader, TextTestRunner, TestSuite

TESTS = ('form', 'fields', 'validators', 'widgets', 'webob_wrapper', 'translations', 'ext_csrf', 'ext_i18n')

OPTIONAL_TESTS = ('ext_django.tests', 'ext_sqlalchemy', 'ext_dateutil')

def make_suite(prefix='', extra=()):
    tests = TESTS + extra
    test_names = list(prefix + x for x in tests)
    suite = TestSuite()
    suite.addTest(defaultTestLoader.loadTestsFromNames(test_names))
    for name in OPTIONAL_TESTS:
        test_name = prefix + name
        try:
            suite.addTest(defaultTestLoader.loadTestsFromName(test_name))
        except (ImportError, AttributeError):
            sys.stderr.write("### Disabled test '%s', dependency not found\n" % name)
    return suite

def additional_tests():
    """
    This is called automatically by setup.py test
    """
    return make_suite('tests.')

def main():
    my_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(my_dir, '..')))

    extra_tests = tuple(x for x in sys.argv[1:] if '-' not in x)
    suite = make_suite('', extra_tests)

    runner = TextTestRunner(verbosity=(sys.argv.count('-v') - sys.argv.count('-q') + 1))
    result = runner.run(suite)
    sys.exit(not result.wasSuccessful())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = translations
from __future__ import unicode_literals

from unittest import TestCase

from wtforms import Form, TextField
from wtforms import validators as v


class Lower_Translator(object):
    """A fake translator that just converts everything to lowercase."""

    def gettext(self, s):
        return s.lower()

    def ngettext(self, singular, plural, n):
        if n == 1:
            return singular.lower()
        else:
            return plural.lower()


class MyFormBase(Form):
    def _get_translations(self):
        return Lower_Translator()


class DummyTranslationsTest(TestCase):
    class F(Form):
        a = TextField(validators=[v.Length(max=5)])

    def setUp(self):
        self.a = self.F().a

    def test_gettext(self):
        x = "foo"
        self.assertTrue(self.a.gettext(x) is x)

    def test_ngettext(self):
        getit = lambda n: self.a.ngettext("antelope", "antelopes", n)
        self.assertEqual(getit(0), "antelopes")
        self.assertEqual(getit(1), "antelope")
        self.assertEqual(getit(2), "antelopes")



class TranslationsTest(TestCase):
    class F(MyFormBase):
        a = TextField('', [v.Length(max=5)])

    def test_validator_translation(self):
        form = self.F(a='hellobye')
        self.assertFalse(form.validate())
        self.assertEqual(form.a.errors[0], 'field cannot be longer than 5 characters.')

########NEW FILE########
__FILENAME__ = validators
#!/usr/bin/env python
from unittest import TestCase
from wtforms.compat import text_type
from wtforms.validators import (
    StopValidation, ValidationError, email, equal_to,
    ip_address, length, required, optional, regexp,
    url, NumberRange, AnyOf, NoneOf, mac_address, UUID
)
from functools import partial

class DummyTranslations(object):
    def gettext(self, string):
        return string

    def ngettext(self, singular, plural, n):
        if n == 1:
            return singular

        return plural

class DummyForm(dict):
    pass

class DummyField(object):
    _translations = DummyTranslations()
    def __init__(self, data, errors=(), raw_data=None):
        self.data = data
        self.errors = list(errors)
        self.raw_data = raw_data

    def gettext(self, string):
        return self._translations.gettext(string)

    def ngettext(self, singular, plural, n):
        return self._translations.ngettext(singular, plural, n)

def grab_error_message(callable, form, field):
    try:
        callable(form, field)
    except ValidationError as e:
        return e.args[0]

class ValidatorsTest(TestCase):
    def setUp(self):
        self.form = DummyForm()

    def test_email(self):
        self.assertEqual(email()(self.form, DummyField('foo@bar.dk')), None)
        self.assertEqual(email()(self.form, DummyField('123@bar.dk')), None)
        self.assertEqual(email()(self.form, DummyField('foo@456.dk')), None)
        self.assertEqual(email()(self.form, DummyField('foo@bar456.info')), None)
        self.assertRaises(ValidationError, email(), self.form, DummyField(None))
        self.assertRaises(ValidationError, email(), self.form, DummyField(''))
        self.assertRaises(ValidationError, email(), self.form, DummyField('  '))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('bar.dk'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo@'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('@bar.dk'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo@bar'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo@bar.ab12'))
        self.assertRaises(ValidationError, email(), self.form, DummyField('foo@.bar.ab'))

    def test_equal_to(self):
        self.form['foo'] = DummyField('test')
        self.assertEqual(equal_to('foo')(self.form, self.form['foo']), None)
        self.assertRaises(ValidationError, equal_to('invalid_field_name'), self.form, DummyField('test'))
        self.assertRaises(ValidationError, equal_to('foo'), self.form, DummyField('different_value'))

    def test_ip_address(self):
        self.assertEqual(ip_address()(self.form, DummyField('127.0.0.1')), None)
        self.assertRaises(ValidationError, ip_address(), self.form, DummyField('abc.0.0.1'))
        self.assertRaises(ValidationError, ip_address(), self.form, DummyField('1278.0.0.1'))
        self.assertRaises(ValidationError, ip_address(), self.form, DummyField('127.0.0.abc'))
        self.assertRaises(ValidationError, ip_address(), self.form, DummyField('900.200.100.75'))
        self.assertRaises(ValidationError, ip_address(ipv6=True), self.form, DummyField('abc.0.0.1'))
        self.assertRaises(ValidationError, ip_address(ipv6=True), self.form, DummyField('abcd:1234::123::1'))
        for good_address in ('::1', 'dead:beef:0:0:0:0:42:1', 'abcd:ef::42:1'):
            self.assertEqual(ip_address(ipv6=True)(self.form, DummyField(good_address)), None)

    def test_mac_address(self):
        self.assertEqual(mac_address()(self.form, 
                                       DummyField('01:23:45:67:ab:CD')), None)

        check_fail = partial(
            self.assertRaises, ValidationError, 
            mac_address(), self.form
        )

        check_fail(DummyField('00:00:00:00:00'))
        check_fail(DummyField('01:23:45:67:89:'))
        check_fail(DummyField('01:23:45:67:89:gh'))
        check_fail(DummyField('123:23:45:67:89:00'))


    def test_uuid(self):
        self.assertEqual(UUID()(self.form, DummyField(
                    '2bc1c94f-0deb-43e9-92a1-4775189ec9f8')), None)
        self.assertRaises(ValidationError, UUID(), self.form, 
                          DummyField('2bc1c94f-deb-43e9-92a1-4775189ec9f8'))
        self.assertRaises(ValidationError, UUID(), self.form, 
                          DummyField('2bc1c94f-0deb-43e9-92a1-4775189ec9f'))
        self.assertRaises(ValidationError, UUID(), self.form, 
                          DummyField('gbc1c94f-0deb-43e9-92a1-4775189ec9f8'))
        self.assertRaises(ValidationError, UUID(), self.form, 
                          DummyField('2bc1c94f 0deb-43e9-92a1-4775189ec9f8'))

    def test_length(self):
        field = DummyField('foobar')
        self.assertEqual(length(min=2, max=6)(self.form, field), None)
        self.assertRaises(ValidationError, length(min=7), self.form, field)
        self.assertEqual(length(min=6)(self.form, field), None)
        self.assertRaises(ValidationError, length(max=5), self.form, field)
        self.assertEqual(length(max=6)(self.form, field), None)

        self.assertRaises(AssertionError, length)
        self.assertRaises(AssertionError, length, min=5, max=2)

        # Test new formatting features
        grab = lambda **k : grab_error_message(length(**k), self.form, field)
        self.assertEqual(grab(min=2, max=5, message='%(min)d and %(max)d'), '2 and 5')
        self.assertTrue('at least 8' in grab(min=8))
        self.assertTrue('longer than 5' in grab(max=5))
        self.assertTrue('between 2 and 5' in grab(min=2, max=5))

    def test_required(self):
        self.assertEqual(required()(self.form, DummyField('foobar')), None)
        self.assertRaises(StopValidation, required(), self.form, DummyField(''))
        self.assertRaises(StopValidation, required(), self.form, DummyField(' '))
        self.assertEqual(required().field_flags, ('required', ))
        f = DummyField('', ['Invalid Integer Value'])
        self.assertEqual(len(f.errors), 1)
        self.assertRaises(StopValidation, required(), self.form, f)
        self.assertEqual(len(f.errors), 0)

    def test_optional(self):
        self.assertEqual(optional()(self.form, DummyField('foobar', raw_data=['foobar'])), None)
        self.assertRaises(StopValidation, optional(), self.form, DummyField('', raw_data=['']))
        self.assertEqual(optional().field_flags, ('optional', ))
        f = DummyField('', ['Invalid Integer Value'], raw_data=[''])
        self.assertEqual(len(f.errors), 1)
        self.assertRaises(StopValidation, optional(), self.form, f)
        self.assertEqual(len(f.errors), 0)

        # Test for whitespace behavior.
        whitespace_field = DummyField(' ', raw_data=[' '])
        self.assertRaises(StopValidation, optional(), self.form, whitespace_field)
        self.assertEqual(optional(strip_whitespace=False)(self.form, whitespace_field), None)

    def test_regexp(self):
        import re
        # String regexp
        self.assertEqual(regexp('^a')(self.form, DummyField('abcd')), None)
        self.assertEqual(regexp('^a', re.I)(self.form, DummyField('ABcd')), None)
        self.assertRaises(ValidationError, regexp('^a'), self.form, DummyField('foo'))
        self.assertRaises(ValidationError, regexp('^a'), self.form, DummyField(None))
        # Compiled regexp
        self.assertEqual(regexp(re.compile('^a'))(self.form, DummyField('abcd')), None)
        self.assertEqual(regexp(re.compile('^a', re.I))(self.form, DummyField('ABcd')), None)
        self.assertRaises(ValidationError, regexp(re.compile('^a')), self.form, DummyField('foo'))
        self.assertRaises(ValidationError, regexp(re.compile('^a')), self.form, DummyField(None))

    def test_url(self):
        self.assertEqual(url()(self.form, DummyField('http://foobar.dk')), None)
        self.assertEqual(url()(self.form, DummyField('http://foobar.dk/')), None)
        self.assertEqual(url()(self.form, DummyField('http://foobar.museum/foobar')), None)
        self.assertEqual(url()(self.form, DummyField('http://127.0.0.1/foobar')), None)
        self.assertEqual(url()(self.form, DummyField('http://127.0.0.1:9000/fake')), None)
        self.assertEqual(url(require_tld=False)(self.form, DummyField('http://localhost/foobar')), None)
        self.assertEqual(url(require_tld=False)(self.form, DummyField('http://foobar')), None)
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://foobar'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('foobar.dk'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://127.0.0/asdf'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://foobar.d'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://foobar.12'))
        self.assertRaises(ValidationError, url(), self.form, DummyField('http://localhost:abc/a'))

    def test_number_range(self):
        v = NumberRange(min=5, max=10)
        self.assertEqual(v(self.form, DummyField(7)), None)
        self.assertRaises(ValidationError, v, self.form, DummyField(None))
        self.assertRaises(ValidationError, v, self.form, DummyField(0))
        self.assertRaises(ValidationError, v, self.form, DummyField(12))
        self.assertRaises(ValidationError, v, self.form, DummyField(-5))

        onlymin = NumberRange(min=5)
        self.assertEqual(onlymin(self.form, DummyField(500)), None)
        self.assertRaises(ValidationError, onlymin, self.form, DummyField(4))

        onlymax = NumberRange(max=50)
        self.assertEqual(onlymax(self.form, DummyField(30)), None)
        self.assertRaises(ValidationError, onlymax, self.form, DummyField(75))

    def test_lazy_proxy(self):
        """Tests that the validators support lazy translation strings for messages."""

        class ReallyLazyProxy(object):
            def __unicode__(self):
                raise Exception('Translator function called during form declaration: it should be called at response time.')
            __str__ = __unicode__

        message = ReallyLazyProxy()
        self.assertRaises(Exception, str, message)
        self.assertRaises(Exception, text_type, message)
        self.assertTrue(equal_to('fieldname', message=message))
        self.assertTrue(length(min=1, message=message))
        self.assertTrue(NumberRange(1,5, message=message))
        self.assertTrue(required(message=message))
        self.assertTrue(regexp('.+', message=message))
        self.assertTrue(email(message=message))
        self.assertTrue(ip_address(message=message))
        self.assertTrue(url(message=message))

    def test_any_of(self):
        self.assertEqual(AnyOf(['a', 'b', 'c'])(self.form, DummyField('b')), None)
        self.assertRaises(ValueError, AnyOf(['a', 'b', 'c']), self.form, DummyField(None))

        # Anyof in 1.0.1 failed on numbers for formatting the error with a TypeError
        check_num = AnyOf([1,2,3])
        self.assertEqual(check_num(self.form, DummyField(2)), None)
        self.assertRaises(ValueError, check_num, self.form, DummyField(4))

        # Test values_formatter
        formatter = lambda values: '::'.join(text_type(x) for x in reversed(values))
        checker = AnyOf([7,8,9], message='test %(values)s', values_formatter=formatter)
        self.assertEqual(grab_error_message(checker, self.form, DummyField(4)), 'test 9::8::7')

    def test_none_of(self):
        self.assertEqual(NoneOf(['a', 'b', 'c'])(self.form, DummyField('d')), None)
        self.assertRaises(ValueError, NoneOf(['a', 'b', 'c']), self.form, DummyField('a'))

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = webob_wrapper
#!/usr/bin/env python
from unittest import TestCase
from wtforms.form import BaseForm, WebobInputWrapper
from wtforms.fields import Field, _unset_value 

try:
    from webob.multidict import MultiDict
    has_webob = True
except ImportError:
    has_webob = False


class MockMultiDict(object):
    def __init__(self, tuples):
        self.tuples = tuples

    def __len__(self):
        return len(self.tuples)

    def __iter__(self):
        for k, _ in self.tuples:
            yield k

    def __contains__(self, key):
        for k, _ in self.tuples:
            if k == key:
                return True
        return False

    def getall(self, key):
        result = []
        for k, v in self.tuples:
            if key == k:
                result.append(v)
        return result


class SneakyField(Field):
    def __init__(self, sneaky_callable, *args, **kwargs):
        super(SneakyField, self).__init__(*args, **kwargs)
        self.sneaky_callable = sneaky_callable

    def process(self, formdata, data=_unset_value): 
        self.sneaky_callable(formdata)


class WebobWrapperTest(TestCase):
    def setUp(self):
        w_cls = has_webob and MultiDict or MockMultiDict

        self.test_values = [('a', 'Apple'), ('b', 'Banana'), ('a', 'Cherry')]
        self.empty_mdict = w_cls([])
        self.filled_mdict = w_cls(self.test_values)

    def test_automatic_wrapping(self):
        def _check(formdata):
            self.assertTrue(isinstance(formdata, WebobInputWrapper))

        form = BaseForm({'a': SneakyField(_check)})
        form.process(self.filled_mdict)

    def test_empty(self):
        formdata = WebobInputWrapper(self.empty_mdict)
        self.assertFalse(formdata)
        self.assertEqual(len(formdata), 0)
        self.assertEqual(list(formdata), [])
        self.assertEqual(formdata.getlist('fake'), [])

    def test_filled(self):
        formdata = WebobInputWrapper(self.filled_mdict)
        self.assertTrue(formdata)
        self.assertEqual(len(formdata), 3)
        self.assertEqual(list(formdata), ['a','b','a'])
        self.assertTrue('b' in formdata)
        self.assertTrue('fake' not in formdata)
        self.assertEqual(formdata.getlist('a'), ['Apple', 'Cherry'])
        self.assertEqual(formdata.getlist('b'), ['Banana'])
        self.assertEqual(formdata.getlist('fake'), [])


if __name__ == '__main__':
    from unittest import main
    main()


########NEW FILE########
__FILENAME__ = widgets
#!/usr/bin/env python
from __future__ import unicode_literals

from unittest import TestCase
from wtforms.widgets import html_params, Input
from wtforms.widgets import *


class DummyField(object):
    def __init__(self, data, name='f', label='', id='', type='TextField'):
        self.data = data
        self.name = name
        self.label = label
        self.id = id
        self.type = type

    _value       = lambda x: x.data
    __unicode__  = lambda x: x.data
    __str__      = lambda x: x.data
    __call__     = lambda x, **k: x.data
    __iter__     = lambda x: iter(x.data)
    iter_choices = lambda x: iter(x.data)


class HTMLParamsTest(TestCase):
    def test(self):
        self.assertEqual(html_params(foo=9, k='wuuu'), 'foo="9" k="wuuu"')
        self.assertEqual(html_params(class_='foo'), 'class="foo"')
        self.assertEqual(html_params(class__='foo'), 'class_="foo"')
        self.assertEqual(html_params(for_='foo'), 'for="foo"')


class ListWidgetTest(TestCase):
    def test(self):
        # ListWidget just expects an iterable of field-like objects as its
        # 'field' so that is what we will give it
        field = DummyField([DummyField(x, label='l' + x) for x in ['foo', 'bar']], id='hai')

        self.assertEqual(ListWidget()(field), '<ul id="hai"><li>lfoo: foo</li><li>lbar: bar</li></ul>')

        w = ListWidget(html_tag='ol', prefix_label=False)
        self.assertEqual(w(field), '<ol id="hai"><li>foo lfoo</li><li>bar lbar</li></ol>')


class TableWidgetTest(TestCase):
    def test(self):
        inner_fields = [
            DummyField('hidden1', type='HiddenField'),
            DummyField('foo', label='lfoo'),
            DummyField('bar', label='lbar'),
            DummyField('hidden2', type='HiddenField'),
        ]
        field = DummyField(inner_fields, id='hai')
        self.assertEqual(TableWidget()(field), '<table id="hai"><tr><th>lfoo</th><td>hidden1foo</td></tr><tr><th>lbar</th><td>bar</td></tr></table>hidden2')


class BasicWidgetsTest(TestCase):
    """Test most of the basic input widget types"""

    field = DummyField('foo', name='bar', label='label', id='id') 

    def test_input_type(self):
        a = Input()
        self.assertRaises(AttributeError, getattr, a, 'input_type')
        b = Input(input_type='test')
        self.assertEqual(b.input_type, 'test')

    def test_html_marking(self):
        html = TextInput()(self.field)
        self.assertTrue(hasattr(html, '__html__'))
        self.assertTrue(html.__html__() is html)

    def test_text_input(self):
        self.assertEqual(TextInput()(self.field), '<input id="id" name="bar" type="text" value="foo">')

    def test_password_input(self):
        self.assertTrue('type="password"' in PasswordInput()(self.field))
        self.assertTrue('value=""' in PasswordInput()(self.field))
        self.assertTrue('value="foo"' in PasswordInput(hide_value=False)(self.field))

    def test_hidden_input(self):
        self.assertTrue('type="hidden"' in HiddenInput()(self.field))

    def test_checkbox_input(self):
        self.assertEqual(CheckboxInput()(self.field, value='v'), '<input checked id="id" name="bar" type="checkbox" value="v">')
        field2 = DummyField(False)
        self.assertTrue('checked' not in CheckboxInput()(field2))

    def test_radio_input(self):
        pass # TODO

    def test_textarea(self):
        # Make sure textareas escape properly and render properly
        f = DummyField('hi<>bye')
        self.assertEqual(TextArea()(f), '<textarea id="" name="f">hi&lt;&gt;bye</textarea>')


class SelectTest(TestCase):
    field = DummyField([('foo', 'lfoo', True), ('bar', 'lbar', False)])

    def test(self):
        self.assertEqual(Select()(self.field), 
            '<select id="" name="f"><option selected value="foo">lfoo</option><option value="bar">lbar</option></select>')
        self.assertEqual(Select(multiple=True)(self.field), 
            '<select id="" multiple name="f"><option selected value="foo">lfoo</option><option value="bar">lbar</option></select>')

if __name__ == '__main__':
    from unittest import main
    main()

########NEW FILE########
__FILENAME__ = compat
import sys

if sys.version_info[0] >= 3:
    text_type = str
    string_types = str,
    iteritems = lambda o: o.items()
    itervalues = lambda o: o.values()
    izip = zip

else:
    text_type = unicode
    string_types = basestring,
    iteritems = lambda o: o.iteritems()
    itervalues = lambda o: o.itervalues()
    from itertools import izip

def with_metaclass(meta, base=object):
    return meta("NewBase", (base,), {})


########NEW FILE########
__FILENAME__ = db
"""
Form generation utilities for App Engine's ``db.Model`` class.

The goal of ``model_form()`` is to provide a clean, explicit and predictable
way to create forms based on ``db.Model`` classes. No malabarism or black
magic should be necessary to generate a form for models, and to add custom
non-model related fields: ``model_form()`` simply generates a form class
that can be used as it is, or that can be extended directly or even be used
to create other forms using ``model_form()``.

Example usage:

.. code-block:: python

   from google.appengine.ext import db
   from tipfy.ext.model.form import model_form

   # Define an example model and add a record.
   class Contact(db.Model):
       name = db.StringProperty(required=True)
       city = db.StringProperty()
       age = db.IntegerProperty(required=True)
       is_admin = db.BooleanProperty(default=False)

   new_entity = Contact(key_name='test', name='Test Name', age=17)
   new_entity.put()

   # Generate a form based on the model.
   ContactForm = model_form(Contact)

   # Get a form populated with entity data.
   entity = Contact.get_by_key_name('test')
   form = ContactForm(obj=entity)

Properties from the model can be excluded from the generated form, or it can
include just a set of properties. For example:

.. code-block:: python

   # Generate a form based on the model, excluding 'city' and 'is_admin'.
   ContactForm = model_form(Contact, exclude=('city', 'is_admin'))

   # or...

   # Generate a form based on the model, only including 'name' and 'age'.
   ContactForm = model_form(Contact, only=('name', 'age'))

The form can be generated setting field arguments:

.. code-block:: python

   ContactForm = model_form(Contact, only=('name', 'age'), field_args={
       'name': {
           'label': 'Full name',
           'description': 'Your name',
       },
       'age': {
           'label': 'Age',
           'validators': [validators.NumberRange(min=14, max=99)],
       }
   })

The class returned by ``model_form()`` can be used as a base class for forms
mixing non-model fields and/or other model forms. For example:

.. code-block:: python

   # Generate a form based on the model.
   BaseContactForm = model_form(Contact)

   # Generate a form based on other model.
   ExtraContactForm = model_form(MyOtherModel)

   class ContactForm(BaseContactForm):
       # Add an extra, non-model related field.
       subscribe_to_news = f.BooleanField()

       # Add the other model form as a subform.
       extra = f.FormField(ExtraContactForm)

The class returned by ``model_form()`` can also extend an existing form
class:

.. code-block:: python

   class BaseContactForm(Form):
       # Add an extra, non-model related field.
       subscribe_to_news = f.BooleanField()

   # Generate a form based on the model.
   ContactForm = model_form(Contact, base_class=BaseContactForm)

"""
from wtforms import Form, validators, widgets, fields as f
from wtforms.compat import iteritems
from wtforms.ext.appengine.fields import GeoPtPropertyField, ReferencePropertyField, StringListPropertyField


def get_TextField(kwargs):
    """
    Returns a ``TextField``, applying the ``db.StringProperty`` length limit
    of 500 bytes.
    """
    kwargs['validators'].append(validators.length(max=500))
    return f.TextField(**kwargs)


def get_IntegerField(kwargs):
    """
    Returns an ``IntegerField``, applying the ``db.IntegerProperty`` range
    limits.
    """
    v = validators.NumberRange(min=-0x8000000000000000, max=0x7fffffffffffffff)
    kwargs['validators'].append(v)
    return f.IntegerField(**kwargs)


def convert_StringProperty(model, prop, kwargs):
    """Returns a form field for a ``db.StringProperty``."""
    if prop.multiline:
        kwargs['validators'].append(validators.length(max=500))
        return f.TextAreaField(**kwargs)
    else:
        return get_TextField(kwargs)


def convert_ByteStringProperty(model, prop, kwargs):
    """Returns a form field for a ``db.ByteStringProperty``."""
    return get_TextField(kwargs)


def convert_BooleanProperty(model, prop, kwargs):
    """Returns a form field for a ``db.BooleanProperty``."""
    return f.BooleanField(**kwargs)


def convert_IntegerProperty(model, prop, kwargs):
    """Returns a form field for a ``db.IntegerProperty``."""
    return get_IntegerField(kwargs)


def convert_FloatProperty(model, prop, kwargs):
    """Returns a form field for a ``db.FloatProperty``."""
    return f.FloatField(**kwargs)


def convert_DateTimeProperty(model, prop, kwargs):
    """Returns a form field for a ``db.DateTimeProperty``."""
    if prop.auto_now or prop.auto_now_add:
        return None

    return f.DateTimeField(format='%Y-%m-%d %H:%M:%S', **kwargs)


def convert_DateProperty(model, prop, kwargs):
    """Returns a form field for a ``db.DateProperty``."""
    if prop.auto_now or prop.auto_now_add:
        return None

    return f.DateField(format='%Y-%m-%d', **kwargs)


def convert_TimeProperty(model, prop, kwargs):
    """Returns a form field for a ``db.TimeProperty``."""
    if prop.auto_now or prop.auto_now_add:
        return None

    return f.DateTimeField(format='%H:%M:%S', **kwargs)


def convert_ListProperty(model, prop, kwargs):
    """Returns a form field for a ``db.ListProperty``."""
    return None


def convert_StringListProperty(model, prop, kwargs):
    """Returns a form field for a ``db.StringListProperty``."""
    return StringListPropertyField(**kwargs)


def convert_ReferenceProperty(model, prop, kwargs):
    """Returns a form field for a ``db.ReferenceProperty``."""
    kwargs['reference_class'] = prop.reference_class
    kwargs.setdefault('allow_blank', not prop.required)
    return ReferencePropertyField(**kwargs)


def convert_SelfReferenceProperty(model, prop, kwargs):
    """Returns a form field for a ``db.SelfReferenceProperty``."""
    return None


def convert_UserProperty(model, prop, kwargs):
    """Returns a form field for a ``db.UserProperty``."""
    return None


def convert_BlobProperty(model, prop, kwargs):
    """Returns a form field for a ``db.BlobProperty``."""
    return f.FileField(**kwargs)


def convert_TextProperty(model, prop, kwargs):
    """Returns a form field for a ``db.TextProperty``."""
    return f.TextAreaField(**kwargs)


def convert_CategoryProperty(model, prop, kwargs):
    """Returns a form field for a ``db.CategoryProperty``."""
    return get_TextField(kwargs)


def convert_LinkProperty(model, prop, kwargs):
    """Returns a form field for a ``db.LinkProperty``."""
    kwargs['validators'].append(validators.url())
    return get_TextField(kwargs)


def convert_EmailProperty(model, prop, kwargs):
    """Returns a form field for a ``db.EmailProperty``."""
    kwargs['validators'].append(validators.email())
    return get_TextField(kwargs)


def convert_GeoPtProperty(model, prop, kwargs):
    """Returns a form field for a ``db.GeoPtProperty``."""
    return GeoPtPropertyField(**kwargs)


def convert_IMProperty(model, prop, kwargs):
    """Returns a form field for a ``db.IMProperty``."""
    return None


def convert_PhoneNumberProperty(model, prop, kwargs):
    """Returns a form field for a ``db.PhoneNumberProperty``."""
    return get_TextField(kwargs)


def convert_PostalAddressProperty(model, prop, kwargs):
    """Returns a form field for a ``db.PostalAddressProperty``."""
    return get_TextField(kwargs)


def convert_RatingProperty(model, prop, kwargs):
    """Returns a form field for a ``db.RatingProperty``."""
    kwargs['validators'].append(validators.NumberRange(min=0, max=100))
    return f.IntegerField(**kwargs)


class ModelConverter(object):
    """
    Converts properties from a ``db.Model`` class to form fields.

    Default conversions between properties and fields:

    +====================+===================+==============+==================+
    | Property subclass  | Field subclass    | datatype     | notes            |
    +====================+===================+==============+==================+
    | StringProperty     | TextField         | unicode      | TextArea         |
    |                    |                   |              | if multiline     |
    +--------------------+-------------------+--------------+------------------+
    | ByteStringProperty | TextField         | str          |                  |
    +--------------------+-------------------+--------------+------------------+
    | BooleanProperty    | BooleanField      | bool         |                  |
    +--------------------+-------------------+--------------+------------------+
    | IntegerProperty    | IntegerField      | int or long  |                  |
    +--------------------+-------------------+--------------+------------------+
    | FloatProperty      | TextField         | float        |                  |
    +--------------------+-------------------+--------------+------------------+
    | DateTimeProperty   | DateTimeField     | datetime     | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | DateProperty       | DateField         | date         | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | TimeProperty       | DateTimeField     | time         | skipped if       |
    |                    |                   |              | auto_now[_add]   |
    +--------------------+-------------------+--------------+------------------+
    | ListProperty       | None              | list         | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | StringListProperty | TextAreaField     | list of str  |                  |
    +--------------------+-------------------+--------------+------------------+
    | ReferenceProperty  | ReferencePropertyF| db.Model     |                  |
    +--------------------+-------------------+--------------+------------------+
    | SelfReferenceP.    | ReferencePropertyF| db.Model     |                  |
    +--------------------+-------------------+--------------+------------------+
    | UserProperty       | None              | users.User   | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | BlobProperty       | FileField         | str          |                  |
    +--------------------+-------------------+--------------+------------------+
    | TextProperty       | TextAreaField     | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | CategoryProperty   | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | LinkProperty       | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | EmailProperty      | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | GeoPtProperty      | TextField         | db.GeoPt     |                  |
    +--------------------+-------------------+--------------+------------------+
    | IMProperty         | None              | db.IM        | always skipped   |
    +--------------------+-------------------+--------------+------------------+
    | PhoneNumberProperty| TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | PostalAddressP.    | TextField         | unicode      |                  |
    +--------------------+-------------------+--------------+------------------+
    | RatingProperty     | IntegerField      | int or long  |                  |
    +--------------------+-------------------+--------------+------------------+
    | _ReverseReferenceP.| None              | <iterable>   | always skipped   |
    +====================+===================+==============+==================+
    """
    default_converters = {
        'StringProperty':        convert_StringProperty,
        'ByteStringProperty':    convert_ByteStringProperty,
        'BooleanProperty':       convert_BooleanProperty,
        'IntegerProperty':       convert_IntegerProperty,
        'FloatProperty':         convert_FloatProperty,
        'DateTimeProperty':      convert_DateTimeProperty,
        'DateProperty':          convert_DateProperty,
        'TimeProperty':          convert_TimeProperty,
        'ListProperty':          convert_ListProperty,
        'StringListProperty':    convert_StringListProperty,
        'ReferenceProperty':     convert_ReferenceProperty,
        'SelfReferenceProperty': convert_SelfReferenceProperty,
        'UserProperty':          convert_UserProperty,
        'BlobProperty':          convert_BlobProperty,
        'TextProperty':          convert_TextProperty,
        'CategoryProperty':      convert_CategoryProperty,
        'LinkProperty':          convert_LinkProperty,
        'EmailProperty':         convert_EmailProperty,
        'GeoPtProperty':         convert_GeoPtProperty,
        'IMProperty':            convert_IMProperty,
        'PhoneNumberProperty':   convert_PhoneNumberProperty,
        'PostalAddressProperty': convert_PostalAddressProperty,
        'RatingProperty':        convert_RatingProperty,
    }

    # Don't automatically add a required validator for these properties
    NO_AUTO_REQUIRED = frozenset(['ListProperty', 'StringListProperty', 'BooleanProperty'])

    def __init__(self, converters=None):
        """
        Constructs the converter, setting the converter callables.

        :param converters:
            A dictionary of converter callables for each property type. The
            callable must accept the arguments (model, prop, kwargs).
        """
        self.converters = converters or self.default_converters

    def convert(self, model, prop, field_args):
        """
        Returns a form field for a single model property.

        :param model:
            The ``db.Model`` class that contains the property.
        :param prop:
            The model property: a ``db.Property`` instance.
        :param field_args:
            Optional keyword arguments to construct the field.
        """
        prop_type_name = type(prop).__name__
        kwargs = {
            'label': prop.name.replace('_', ' ').title(),
            'default': prop.default_value(),
            'validators': [],
        }
        if field_args:
            kwargs.update(field_args)

        if prop.required and prop_type_name not in self.NO_AUTO_REQUIRED:
            kwargs['validators'].append(validators.required())

        if prop.choices:
            # Use choices in a select field.
            kwargs['choices'] = [(v, v) for v in prop.choices]
            return f.SelectField(**kwargs)
        else:
            converter = self.converters.get(prop_type_name, None)
            if converter is not None:
                return converter(model, prop, kwargs)


def model_fields(model, only=None, exclude=None, field_args=None,
                 converter=None):
    """
    Extracts and returns a dictionary of form fields for a given
    ``db.Model`` class.

    :param model:
        The ``db.Model`` class to extract fields from.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to a keyword arguments
        used to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    converter = converter or ModelConverter()
    field_args = field_args or {}

    # Get the field names we want to include or exclude, starting with the
    # full list of model properties.
    props = model.properties()
    sorted_props = sorted(iteritems(props), key=lambda prop: prop[1].creation_counter)
    field_names = list(x[0] for x in sorted_props)

    if only:
        field_names = list(f for f in only if f in field_names)
    elif exclude:
        field_names = list(f for f in field_names if f not in exclude)

    # Create all fields.
    field_dict = {}
    for name in field_names:
        field = converter.convert(model, props[name], field_args.get(name))
        if field is not None:
            field_dict[name] = field

    return field_dict


def model_form(model, base_class=Form, only=None, exclude=None, field_args=None,
               converter=None):
    """
    Creates and returns a dynamic ``wtforms.Form`` class for a given
    ``db.Model`` class. The form class can be used as it is or serve as a base
    for extended form classes, which can then mix non-model related fields,
    subforms with other model forms, among other possibilities.

    :param model:
        The ``db.Model`` class to generate a form for.
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments
        used to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    # Extract the fields from the model.
    field_dict = model_fields(model, only, exclude, field_args, converter)

    # Return a dynamically created form class, extending from base_class and
    # including the created fields as properties.
    return type(model.kind() + 'Form', (base_class,), field_dict)

########NEW FILE########
__FILENAME__ = fields
from __future__ import unicode_literals

import decimal
import operator
import warnings

from wtforms import fields, widgets
from wtforms.compat import text_type, string_types

class ReferencePropertyField(fields.SelectFieldBase):
    """
    A field for ``db.ReferenceProperty``. The list items are rendered in a
    select.

    :param reference_class:
        A db.Model class which will be used to generate the default query
        to make the list of items. If this is not specified, The `query`
        property must be overridden before validation.
    :param get_label:
        If a string, use this attribute on the model class as the label
        associated with each option. If a one-argument callable, this callable
        will be passed model instance and expected to return the label text.
        Otherwise, the model object's `__str__` or `__unicode__` will be used.
    :param allow_blank:
        If set to true, a blank choice will be added to the top of the list
        to allow `None` to be chosen.
    :param blank_text:
        Use this to override the default blank option's label.
    """
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, reference_class=None,
                 label_attr=None, get_label=None, allow_blank=False,
                 blank_text='', **kwargs):
        super(ReferencePropertyField, self).__init__(label, validators,
                                                     **kwargs)
        if label_attr is not None:
            warnings.warn('label_attr= will be removed in WTForms 1.1, use get_label= instead.', DeprecationWarning)
            self.get_label = operator.attrgetter(label_attr)
        elif get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, string_types):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self._set_data(None)
        if reference_class is not None:
            self.query = reference_class.all()

    def _get_data(self):
        if self._formdata is not None:
            for obj in self.query:
                if str(obj.key()) == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for obj in self.query:
            key = str(obj.key())
            label = self.get_label(obj)
            yield (key, label, self.data and ( self.data.key( ) == obj.key() ) )

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form):
        if not self.allow_blank or self.data is not None:
            for obj in self.query:
                if str(self.data.key()) == str(obj.key()):
                    break
            else:
                raise ValueError(self.gettext('Not a valid choice'))


class StringListPropertyField(fields.TextAreaField):
    """
    A field for ``db.StringListProperty``. The list items are rendered in a
    textarea.
    """
    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        else:
            return self.data and text_type("\n".join(self.data)) or ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = valuelist[0].splitlines()
            except ValueError:
                raise ValueError(self.gettext('Not a valid list'))


class GeoPtPropertyField(fields.TextField):

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                lat, lon = valuelist[0].split(',')
                self.data = '%s,%s' % (decimal.Decimal(lat.strip()), decimal.Decimal(lon.strip()),)
            except (decimal.InvalidOperation, ValueError):
                raise ValueError('Not a valid coordinate location')

########NEW FILE########
__FILENAME__ = fields
from wtforms.fields import HiddenField


class CSRFTokenField(HiddenField):
    current_token = None

    def _value(self):
        """
        We want to always return the current token on render, regardless of
        whether a good or bad token was passed.
        """
        return self.current_token

    def populate_obj(self, *args):
        """
        Don't populate objects with the CSRF token
        """
        pass

########NEW FILE########
__FILENAME__ = form
from __future__ import unicode_literals

from wtforms.form import Form
from wtforms.validators import ValidationError

from .fields import CSRFTokenField


class SecureForm(Form):
    """
    Form that enables CSRF processing via subclassing hooks.
    """
    csrf_token = CSRFTokenField()

    def __init__(self, formdata=None, obj=None, prefix='', csrf_context=None, **kwargs):
        """
        :param csrf_context: 
            Optional extra data which is passed transparently to your 
            CSRF implementation.
        """
        super(SecureForm, self).__init__(formdata, obj, prefix, **kwargs)
        self.csrf_token.current_token = self.generate_csrf_token(csrf_context)

    def generate_csrf_token(self, csrf_context):
        """
        Implementations must override this to provide a method with which one
        can get a CSRF token for this form.

        A CSRF token should be a string which can be generated
        deterministically so that on the form POST, the generated string is
        (usually) the same assuming the user is using the site normally.

        :param csrf_context: 
            A transparent object which can be used as contextual info for
            generating the token.
        """
        raise NotImplementedError()

    def validate_csrf_token(self, field):
        """
        Override this method to provide custom CSRF validation logic.

        The default CSRF validation logic simply checks if the recently
        generated token equals the one we received as formdata.
        """
        if field.current_token != field.data:
            raise ValidationError(field.gettext('Invalid CSRF Token'))

    @property
    def data(self):
        d = super(SecureForm, self).data
        d.pop('csrf_token')
        return d

########NEW FILE########
__FILENAME__ = session
"""
A provided CSRF implementation which puts CSRF data in a session.

This can be used fairly comfortably with many `request.session` type
objects, including the Werkzeug/Flask session store, Django sessions, and
potentially other similar objects which use a dict-like API for storing
session keys.

The basic concept is a randomly generated value is stored in the user's
session, and an hmac-sha1 of it (along with an optional expiration time,
for extra security) is used as the value of the csrf_token. If this token
validates with the hmac of the random value + expiration time, and the
expiration time is not passed, the CSRF validation will pass.
"""
from __future__ import unicode_literals

import hmac
import os

from hashlib import sha1
from datetime import datetime, timedelta

from ...validators import ValidationError
from .form import SecureForm

__all__ = ('SessionSecureForm', )

class SessionSecureForm(SecureForm):
    TIME_FORMAT = '%Y%m%d%H%M%S'
    TIME_LIMIT = timedelta(minutes=30)
    SECRET_KEY = None

    def generate_csrf_token(self, csrf_context):
        if self.SECRET_KEY is None:
            raise Exception('must set SECRET_KEY in a subclass of this form for it to work')
        if csrf_context is None:
            raise TypeError('Must provide a session-like object as csrf context')

        session = getattr(csrf_context, 'session', csrf_context)

        if 'csrf' not in session:
            session['csrf'] = sha1(os.urandom(64)).hexdigest()

        self.csrf_token.csrf_key = session['csrf']
        if self.TIME_LIMIT:
            expires = (datetime.now() + self.TIME_LIMIT).strftime(self.TIME_FORMAT)
            csrf_build = '%s%s' % (session['csrf'], expires)
        else:
            expires = ''
            csrf_build = session['csrf']

        hmac_csrf = hmac.new(self.SECRET_KEY, csrf_build.encode('utf8'), digestmod=sha1) 
        return '%s##%s' % (expires, hmac_csrf.hexdigest())

    def validate_csrf_token(self, field):
        if not field.data or '##' not in field.data:
            raise ValidationError(field.gettext('CSRF token missing'))

        expires, hmac_csrf = field.data.split('##')

        check_val = (field.csrf_key + expires).encode('utf8')

        hmac_compare = hmac.new(self.SECRET_KEY, check_val, digestmod=sha1)
        if hmac_compare.hexdigest() != hmac_csrf:
            raise ValidationError(field.gettext('CSRF failed'))

        if self.TIME_LIMIT:
            now_formatted = datetime.now().strftime(self.TIME_FORMAT)
            if now_formatted > expires:
                raise ValidationError(field.gettext('CSRF token expired'))

########NEW FILE########
__FILENAME__ = fields
"""
A DateTimeField and DateField that use the `dateutil` package for parsing.
"""
from __future__ import unicode_literals

from dateutil import parser

from wtforms.fields import Field
from wtforms.validators import ValidationError
from wtforms.widgets import TextInput


__all__ = (
    'DateTimeField', 'DateField',
)


class DateTimeField(Field):
    """
    DateTimeField represented by a text input, accepts all input text formats
    that `dateutil.parser.parse` will.

    :param parse_kwargs:
        A dictionary of keyword args to pass to the dateutil parse() function.
        See dateutil docs for available keywords.
    :param display_format:
        A format string to pass to strftime() to format dates for display.
    """
    widget = TextInput()

    def __init__(self, label=None, validators=None, parse_kwargs=None,
                 display_format='%Y-%m-%d %H:%M', **kwargs):
        super(DateTimeField, self).__init__(label, validators, **kwargs)
        if parse_kwargs is None:
            parse_kwargs = {}
        self.parse_kwargs = parse_kwargs
        self.display_format = display_format

    def _value(self):
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            return self.data and self.data.strftime(self.display_format) or ''

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            if not date_str:
                self.data = None
                raise ValidationError(self.gettext('Please input a date/time value'))

            parse_kwargs = self.parse_kwargs.copy()
            if 'default' not in parse_kwargs:
                try:
                    parse_kwargs['default'] = self.default()
                except TypeError:
                    parse_kwargs['default'] = self.default
            try:
                self.data = parser.parse(date_str, **parse_kwargs)
            except ValueError:
                self.data = None
                raise ValidationError(self.gettext('Invalid date/time input'))


class DateField(DateTimeField):
    """
    Same as the DateTimeField, but stores only the date portion.
    """
    def __init__(self, label=None, validators=None, parse_kwargs=None,
                 display_format='%Y-%m-%d', **kwargs):
        super(DateField, self).__init__(label, validators, parse_kwargs=parse_kwargs, display_format=display_format, **kwargs)

    def process_formdata(self, valuelist):
        super(DateField, self).process_formdata(valuelist)
        if self.data is not None and hasattr(self.data, 'date'):
            self.data = self.data.date()

########NEW FILE########
__FILENAME__ = fields
"""
Useful form fields for use with the Django ORM.
"""
from __future__ import unicode_literals

import operator

from wtforms import widgets
from wtforms.compat import string_types
from wtforms.fields import SelectFieldBase
from wtforms.validators import ValidationError


__all__ = (
    'ModelSelectField', 'QuerySetSelectField',
)


class QuerySetSelectField(SelectFieldBase):
    """
    Given a QuerySet either at initialization or inside a view, will display a
    select drop-down field of choices. The `data` property actually will
    store/keep an ORM model instance, not the ID. Submitting a choice which is
    not in the queryset will result in a validation error.

    Specify `get_label` to customize the label associated with each option. If
    a string, this is the name of an attribute on the model object to use as
    the label text. If a one-argument callable, this callable will be passed
    model instance and expected to return the label text. Otherwise, the model
    object's `__str__` or `__unicode__` will be used.

    If `allow_blank` is set to `True`, then a blank choice will be added to the
    top of the list. Selecting this choice will result in the `data` property
    being `None`.  The label for the blank choice can be set by specifying the
    `blank_text` parameter.
    """
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, queryset=None, get_label=None, allow_blank=False, blank_text='', **kwargs):
        super(QuerySetSelectField, self).__init__(label, validators, **kwargs)
        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self._set_data(None)
        if queryset is not None:
            self.queryset = queryset.all() # Make sure the queryset is fresh

        if get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, string_types):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

    def _get_data(self):
        if self._formdata is not None:
            for obj in self.queryset:
                if obj.pk == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for obj in self.queryset:
            yield (obj.pk, self.get_label(obj), obj == self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = int(valuelist[0])

    def pre_validate(self, form):
        if not self.allow_blank or self.data is not None:
            for obj in self.queryset:
                if self.data == obj:
                    break
            else:
                raise ValidationError(self.gettext('Not a valid choice'))


class ModelSelectField(QuerySetSelectField):
    """
    Like a QuerySetSelectField, except takes a model class instead of a
    queryset and lists everything in it.
    """
    def __init__(self, label=None, validators=None, model=None, **kwargs):
        super(ModelSelectField, self).__init__(label, validators, queryset=model._default_manager.all(), **kwargs)

########NEW FILE########
__FILENAME__ = i18n
from django.utils.translation import ugettext, ungettext
from wtforms import form

class DjangoTranslations(object):
    """
    A translations object for WTForms that gets its messages from django's
    translations providers.
    """
    def gettext(self, string):
        return ugettext(string)

    def ngettext(self, singular, plural, n):
        return ungettext(singular, plural, n)


class Form(form.Form):
    """
    A Form derivative which uses the translations engine from django.
    """
    _django_translations = DjangoTranslations()

    def _get_translations(self):
        return self._django_translations

########NEW FILE########
__FILENAME__ = orm
"""
Tools for generating forms based on Django models.
"""
from wtforms import fields as f
from wtforms import Form
from wtforms import validators
from wtforms.compat import iteritems
from wtforms.ext.django.fields import ModelSelectField


__all__ = (
    'model_fields', 'model_form',
)


class ModelConverterBase(object):
    def __init__(self, converters):
        self.converters = converters

    def convert(self, model, field, field_args):
        kwargs = {
            'label': field.verbose_name,
            'description': field.help_text,
            'validators': [],
            'filters': [],
            'default': field.default,
        }
        if field_args:
            kwargs.update(field_args)

        if field.blank:
            kwargs['validators'].append(validators.Optional())
        if field.max_length is not None and field.max_length > 0:
            kwargs['validators'].append(validators.Length(max=field.max_length))

        ftype = type(field).__name__
        if field.choices:
            kwargs['choices'] = field.choices
            return f.SelectField(**kwargs)
        elif ftype in self.converters:
            return self.converters[ftype](model, field, kwargs)
        else:
            converter = getattr(self, 'conv_%s' % ftype, None)
            if converter is not None:
                return converter(model, field, kwargs)


class ModelConverter(ModelConverterBase):
    DEFAULT_SIMPLE_CONVERSIONS = {
        f.IntegerField: ['AutoField', 'IntegerField', 'SmallIntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField'],
        f.DecimalField: ['DecimalField', 'FloatField'],
        f.FileField: ['FileField', 'FilePathField', 'ImageField'],
        f.DateTimeField: ['DateTimeField'],
        f.DateField : ['DateField'],
        f.BooleanField: ['BooleanField'],
        f.TextField: ['CharField', 'PhoneNumberField', 'SlugField'],
        f.TextAreaField: ['TextField', 'XMLField'],
    }

    def __init__(self, extra_converters=None, simple_conversions=None):
        converters = {}
        if simple_conversions is None:
            simple_conversions = self.DEFAULT_SIMPLE_CONVERSIONS
        for field_type, django_fields in iteritems(simple_conversions):
            converter = self.make_simple_converter(field_type)
            for name in django_fields:
                converters[name] = converter

        if extra_converters:
            converters.update(extra_converters)
        super(ModelConverter, self).__init__(converters)

    def make_simple_converter(self, field_type):
        def _converter(model, field, kwargs):
            return field_type(**kwargs)
        return _converter

    def conv_ForeignKey(self, model, field, kwargs):
        return ModelSelectField(model=field.rel.to, **kwargs)

    def conv_TimeField(self, model, field, kwargs):
        def time_only(obj):
            try:
                return obj.time()
            except AttributeError:
                return obj
        kwargs['filters'].append(time_only)
        return f.DateTimeField(format='%H:%M:%S', **kwargs)

    def conv_EmailField(self, model, field, kwargs):
        kwargs['validators'].append(validators.email())
        return f.TextField(**kwargs)

    def conv_IPAddressField(self, model, field, kwargs):
        kwargs['validators'].append(validators.ip_address())
        return f.TextField(**kwargs)

    def conv_URLField(self, model, field, kwargs):
        kwargs['validators'].append(validators.url())
        return f.TextField(**kwargs)

    def conv_USStateField(self, model, field, kwargs):
        try:
            from django.contrib.localflavor.us.us_states import STATE_CHOICES
        except ImportError:
            STATE_CHOICES = []

        return f.SelectField(choices=STATE_CHOICES, **kwargs)

    def conv_NullBooleanField(self, model, field, kwargs):
        def coerce_nullbool(value):
            d = {'None': None, None: None, 'True': True, 'False': False}
            if value in d:
                return d[value]
            else:
                return bool(int(value))

        choices = ((None, 'Unknown'), (True, 'Yes'), (False, 'No'))
        return f.SelectField(choices=choices, coerce=coerce_nullbool, **kwargs)


def model_fields(model, only=None, exclude=None, field_args=None, converter=None):
    """
    Generate a dictionary of fields for a given Django model.

    See `model_form` docstring for description of parameters.
    """
    converter = converter or ModelConverter()
    field_args = field_args or {}

    model_fields = ((f.attname, f) for f in model._meta.fields)
    if only:
        model_fields = (x for x in model_fields if x[0] in only)
    elif exclude:
        model_fields = (x for x in model_fields if x[0] not in exclude)

    field_dict = {}
    for name, model_field in model_fields:
        field = converter.convert(model, model_field, field_args.get(name))
        if field is not None:
            field_dict[name] = field

    return field_dict


def model_form(model, base_class=Form, only=None, exclude=None, field_args=None, converter=None):
    """
    Create a wtforms Form for a given Django model class::

        from wtforms.ext.django.orm import model_form
        from myproject.myapp.models import User
        UserForm = model_form(User)

    :param model:
        A Django ORM model class
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments used
        to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    field_dict = model_fields(model, only, exclude, field_args, converter)
    return type(model._meta.object_name + 'Form', (base_class, ), field_dict)

########NEW FILE########
__FILENAME__ = wtforms
"""
Template tags for easy WTForms access in Django templates.
"""
from __future__ import unicode_literals

import re

from django import template
from django.conf import settings
from django.template import Variable

from ....compat import iteritems

register = template.Library()


class FormFieldNode(template.Node):
    def __init__(self, field_var, html_attrs):
        self.field_var = field_var
        self.html_attrs = html_attrs

    def render(self, context):
        try:
            if '.' in self.field_var:
                base, field_name = self.field_var.rsplit('.', 1)
                field = getattr(Variable(base).resolve(context), field_name)
            else:
                field = context[self.field_var]
        except (template.VariableDoesNotExist, KeyError, AttributeError):
            return settings.TEMPLATE_STRING_IF_INVALID

        h_attrs = {}
        for k, v in iteritems(self.html_attrs):
            try:
                h_attrs[k] = v.resolve(context)
            except template.VariableDoesNotExist:
                h_attrs[k] = settings.TEMPLATE_STRING_IF_INVALID

        return field(**h_attrs)


@register.tag(name='form_field')
def do_form_field(parser, token):
    """
    Render a WTForms form field allowing optional HTML attributes.
    Invocation looks like this:
      {% form_field form.username class="big_text" onclick="alert('hello')" %}
    where form.username is the path to the field value we want.  Any number 
    of key="value" arguments are supported. Unquoted values are resolved as
    template variables.
    """
    parts = token.contents.split(' ', 2)
    if len(parts) < 2:
        raise template.TemplateSyntaxError('%r tag must have the form field name as the first value, followed by optional key="value" attributes.' % parts[0])

    html_attrs = {}
    if len(parts) == 3:
        raw_args = list(args_split(parts[2]))
        if (len(raw_args) % 2) != 0:
            raise template.TemplateSyntaxError('%r tag received the incorrect number of key=value arguments.' % parts[0])
        for x in range(0, len(raw_args), 2):
            html_attrs[str(raw_args[x])] = Variable(raw_args[x+1])

    return FormFieldNode(parts[1], html_attrs)


args_split_re = re.compile(r'''("(?:[^"\\]*(?:\\.[^"\\]*)*)"|'(?:[^'\\]*(?:\\.[^'\\]*)*)'|[^\s=]+)''')

def args_split(text):
    """ Split space-separated key=value arguments.  Keeps quoted strings intact. """ 
    for bit in args_split_re.finditer(text):
        bit = bit.group(0)
        if bit[0] == '"' and bit[-1] == '"':
            yield '"' + bit[1:-1].replace('\\"', '"').replace('\\\\', '\\') + '"'
        elif bit[0] == "'" and bit[-1] == "'":
            yield "'" + bit[1:-1].replace("\\'", "'").replace("\\\\", "\\") + "'"
        else:
            yield bit

########NEW FILE########
__FILENAME__ = form
from wtforms import form
from wtforms.ext.i18n.utils import get_translations

translations_cache = {}

class Form(form.Form):
    """
    Base form for a simple localized WTForms form.

    This will use the stdlib gettext library to retrieve an appropriate
    translations object for the language, by default using the locale
    information from the environment.

    If the LANGUAGES class variable is overridden and set to a sequence of
    strings, this will be a list of languages by priority to use instead, e.g::

        LANGUAGES = ['en_GB', 'en']

    Translations objects are cached to prevent having to get a new one for the
    same languages every instantiation. 
    """
    LANGUAGES = None

    def _get_translations(self):
        languages = tuple(self.LANGUAGES) if self.LANGUAGES else None
        if languages not in translations_cache:
            translations_cache[languages] = get_translations(languages)
        return translations_cache[languages]

########NEW FILE########
__FILENAME__ = utils
import os

def messages_path():
    """
    Determine the path to the 'messages' directory as best possible.
    """
    module_path = os.path.abspath(__file__)
    return os.path.join(os.path.dirname(module_path), 'messages')


def get_builtin_gnu_translations(languages=None):
    """
    Get a gettext.GNUTranslations object pointing at the
    included translation files.

    :param languages:
        A list of languages to try, in order. If omitted or None, then
        gettext will try to use locale information from the environment.
    """
    import gettext
    return gettext.translation('wtforms', messages_path(), languages)


def get_translations(languages=None):
    """
    Get a WTForms translation object which wraps the builtin GNUTranslations object.
    """
    translations = get_builtin_gnu_translations(languages)

    if hasattr(translations, 'ugettext'):
        return DefaultTranslations(translations)
    else:
        # Python 3 has no ugettext/ungettext, so just return the translations object.
        return translations


class DefaultTranslations(object):
    """
    A WTForms translations object to wrap translations objects which use
    ugettext/ungettext.
    """
    def __init__(self, translations):
        self.translations = translations

    def gettext(self, string):
        return self.translations.ugettext(string)

    def ngettext(self, singular, plural, n):
        return self.translations.ungettext(singular, plural, n)

########NEW FILE########
__FILENAME__ = fields
"""
Useful form fields for use with SQLAlchemy ORM.
"""
from __future__ import unicode_literals

import operator

from wtforms import widgets
from wtforms.compat import text_type, string_types
from wtforms.fields import SelectFieldBase
from wtforms.validators import ValidationError

try:
    from sqlalchemy.orm.util import identity_key
    has_identity_key = True
except ImportError:
    has_identity_key = False



__all__ = (
    'QuerySelectField', 'QuerySelectMultipleField',
)


class QuerySelectField(SelectFieldBase):
    """
    Will display a select drop-down field to choose between ORM results in a
    sqlalchemy `Query`.  The `data` property actually will store/keep an ORM
    model instance, not the ID. Submitting a choice which is not in the query
    will result in a validation error.

    This field only works for queries on models whose primary key column(s)
    have a consistent string representation. This means it mostly only works
    for those composed of string, unicode, and integer types. For the most
    part, the primary keys will be auto-detected from the model, alternately
    pass a one-argument callable to `get_pk` which can return a unique
    comparable key.

    The `query` property on the field can be set from within a view to assign
    a query per-instance to the field. If the property is not set, the
    `query_factory` callable passed to the field constructor will be called to
    obtain a query.

    Specify `get_label` to customize the label associated with each option. If
    a string, this is the name of an attribute on the model object to use as
    the label text. If a one-argument callable, this callable will be passed
    model instance and expected to return the label text. Otherwise, the model
    object's `__str__` or `__unicode__` will be used.

    If `allow_blank` is set to `True`, then a blank choice will be added to the
    top of the list. Selecting this choice will result in the `data` property
    being `None`. The label for this blank choice can be set by specifying the
    `blank_text` parameter.
    """
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, query_factory=None,
                 get_pk=None, get_label=None, allow_blank=False,
                 blank_text='', **kwargs):
        super(QuerySelectField, self).__init__(label, validators, **kwargs)
        self.query_factory = query_factory

        if get_pk is None:
            if not has_identity_key:
                raise Exception('The sqlalchemy identity_key function could not be imported.')
            self.get_pk = get_pk_from_identity
        else:
            self.get_pk = get_pk

        if get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, string_types):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self.query = None
        self._object_list = None

    def _get_data(self):
        if self._formdata is not None:
            for pk, obj in self._get_object_list():
                if pk == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def _get_object_list(self):
        if self._object_list is None:
            query = self.query or self.query_factory()
            get_pk = self.get_pk
            self._object_list = list((text_type(get_pk(obj)), obj) for obj in query)
        return self._object_list

    def iter_choices(self):
        if self.allow_blank:
            yield ('__None', self.blank_text, self.data is None)

        for pk, obj in self._get_object_list():
            yield (pk, self.get_label(obj), obj == self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            if self.allow_blank and valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form):
        data = self.data
        if data is not None:
            for pk, obj in self._get_object_list():
                if data == obj:
                    break
            else:
                raise ValidationError(self.gettext('Not a valid choice'))
        elif self._formdata or not self.allow_blank:
            raise ValidationError(self.gettext('Not a valid choice'))


class QuerySelectMultipleField(QuerySelectField):
    """
    Very similar to QuerySelectField with the difference that this will
    display a multiple select. The data property will hold a list with ORM
    model instances and will be an empty list when no value is selected.

    If any of the items in the data list or submitted form data cannot be
    found in the query, this will result in a validation error.
    """
    widget = widgets.Select(multiple=True)

    def __init__(self, label=None, validators=None, default=None, **kwargs):
        if default is None:
            default = []
        super(QuerySelectMultipleField, self).__init__(label, validators, default=default, **kwargs)
        self._invalid_formdata = False

    def _get_data(self):
        formdata = self._formdata
        if formdata is not None:
            data = []
            for pk, obj in self._get_object_list():
                if not formdata:
                    break
                elif pk in formdata:
                    formdata.remove(pk)
                    data.append(obj)
            if formdata:
                self._invalid_formdata = True
            self._set_data(data)
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        for pk, obj in self._get_object_list():
            yield (pk, self.get_label(obj), obj in self.data)

    def process_formdata(self, valuelist):
        self._formdata = set(valuelist)

    def pre_validate(self, form):
        if self._invalid_formdata:
            raise ValidationError(self.gettext('Not a valid choice'))
        elif self.data:
            obj_list = list(x[1] for x in self._get_object_list())
            for v in self.data:
                if v not in obj_list:
                    raise ValidationError(self.gettext('Not a valid choice'))


def get_pk_from_identity(obj):
    cls, key = identity_key(instance=obj)
    return ':'.join(text_type(x) for x in key)

########NEW FILE########
__FILENAME__ = orm
"""
Tools for generating forms based on SQLAlchemy models.
"""
from __future__ import unicode_literals

import inspect

from wtforms import fields as f
from wtforms import validators
from wtforms.form import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from wtforms.ext.sqlalchemy.validators import Unique

__all__ = (
    'model_fields', 'model_form',
)

def converts(*args):
    def _inner(func):
        func._converter_for = frozenset(args)
        return func
    return _inner


class ModelConverterBase(object):
    def __init__(self, converters, use_mro=True):
        self.use_mro = use_mro

        if not converters:
            converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, '_converter_for'):
                for classname in obj._converter_for:
                    converters[classname] = obj

        self.converters = converters

    def convert(self, model, mapper, prop, field_args, db_session=None):
        if not hasattr(prop, 'columns') and not hasattr(prop, 'direction'):
            return
        elif not hasattr(prop, 'direction') and len(prop.columns) != 1:
            raise TypeError('Do not know how to convert multiple-column '
                + 'properties currently')

        kwargs = {
            'validators': [],
            'filters': [],
            'default': None,
        }

        converter = None
        column = None

        if not hasattr(prop, 'direction'):
            column = prop.columns[0]
            # Support sqlalchemy.schema.ColumnDefault, so users can benefit
            # from  setting defaults for fields, e.g.:
            #   field = Column(DateTimeField, default=datetime.utcnow)

            default = getattr(column, 'default', None)

            if default is not None:
                # Only actually change default if it has an attribute named
                # 'arg' that's callable.
                callable_default = getattr(default, 'arg', None)

                if callable_default is not None:
                    # ColumnDefault(val).arg can be also a plain value
                    default = callable_default(None) if callable(callable_default) else callable_default

            kwargs['default'] = default

            if column.nullable:
                kwargs['validators'].append(validators.Optional())
            else:
                kwargs['validators'].append(validators.Required())

            if db_session and column.unique:
                kwargs['validators'].append(Unique(lambda: db_session, model,
                    column))

            if self.use_mro:
                types = inspect.getmro(type(column.type))
            else:
                types = [type(column.type)]

            for col_type in types:
                type_string = '%s.%s' % (col_type.__module__,
                    col_type.__name__)
                if type_string.startswith('sqlalchemy'):
                    type_string = type_string[11:]

                if type_string in self.converters:
                    converter = self.converters[type_string]
                    break
            else:
                for col_type in types:
                    if col_type.__name__ in self.converters:
                        converter = self.converters[col_type.__name__]
                        break
                else:
                    return

        if db_session and hasattr(prop, 'direction'):
            foreign_model = prop.mapper.class_

            nullable = True
            for pair in prop.local_remote_pairs:
                if not pair[0].nullable:
                    nullable = False

            kwargs.update({
                'allow_blank': nullable,
                'query_factory': lambda: db_session.query(foreign_model).all()
            })

            converter = self.converters[prop.direction.name]

        if field_args:
            kwargs.update(field_args)

        return converter(model=model, mapper=mapper, prop=prop, column=column,
            field_args=kwargs)


class ModelConverter(ModelConverterBase):
    def __init__(self, extra_converters=None):
        super(ModelConverter, self).__init__(extra_converters)

    @classmethod
    def _string_common(cls, column, field_args, **extra):
        if column.type.length:
            field_args['validators'].append(validators.Length(max=column.type.length))

    @converts('String', 'Unicode')
    def conv_String(self, field_args, **extra):
        self._string_common(field_args=field_args, **extra)
        return f.TextField(**field_args)

    @converts('Text', 'UnicodeText', 'types.LargeBinary', 'types.Binary')
    def conv_Text(self, field_args, **extra):
        self._string_common(field_args=field_args, **extra)
        return f.TextAreaField(**field_args)

    @converts('Boolean')
    def conv_Boolean(self, field_args, **extra):
        return f.BooleanField(**field_args)

    @converts('Date')
    def conv_Date(self, field_args, **extra):
        return f.DateField(**field_args)

    @converts('DateTime')
    def conv_DateTime(self, field_args, **extra):
        return f.DateTimeField(**field_args)

    @converts('Enum')
    def conv_Enum(self, column, field_args, **extra):
        field_args['choices'] = [(e, e) for e in column.type.enums]
        return f.SelectField(**field_args)

    @converts('Integer', 'SmallInteger')
    def handle_integer_types(self, column, field_args, **extra):
        unsigned = getattr(column.type, 'unsigned', False)
        if unsigned:
            field_args['validators'].append(validators.NumberRange(min=0))
        return f.IntegerField(**field_args)

    @converts('Numeric', 'Float')
    def handle_decimal_types(self, column, field_args, **extra):
        places = getattr(column.type, 'scale', 2)
        if places is not None:
            field_args['places'] = places
        return f.DecimalField(**field_args)

    @converts('databases.mysql.MSYear')
    def conv_MSYear(self, field_args, **extra):
        field_args['validators'].append(validators.NumberRange(min=1901, max=2155))
        return f.TextField(**field_args)

    @converts('databases.postgres.PGInet', 'dialects.postgresql.base.INET')
    def conv_PGInet(self, field_args, **extra):
        field_args.setdefault('label', 'IP Address')
        field_args['validators'].append(validators.IPAddress())
        return f.TextField(**field_args)

    @converts('dialects.postgresql.base.MACADDR')
    def conv_PGMacaddr(self, field_args, **extra):
        field_args.setdefault('label', 'MAC Address')
        field_args['validators'].append(validators.MacAddress())
        return f.TextField(**field_args)

    @converts('dialects.postgresql.base.UUID')
    def conv_PGUuid(self, field_args, **extra):
        field_args.setdefault('label', 'UUID')
        field_args['validators'].append(validators.UUID())
        return f.TextField(**field_args)

    @converts('MANYTOONE')
    def conv_ManyToOne(self, field_args, **extra):
        return QuerySelectField(**field_args)

    @converts('MANYTOMANY', 'ONETOMANY')
    def conv_ManyToMany(self, field_args, **extra):
        return QuerySelectMultipleField(**field_args)


def model_fields(model, db_session=None, only=None, exclude=None,
    field_args=None, converter=None):
    """
    Generate a dictionary of fields for a given SQLAlchemy model.

    See `model_form` docstring for description of parameters.
    """
    if not hasattr(model, '_sa_class_manager'):
        raise TypeError('model must be a sqlalchemy mapped model')

    mapper = model._sa_class_manager.mapper
    converter = converter or ModelConverter()
    field_args = field_args or {}

    properties = ((p.key, p) for p in mapper.iterate_properties)
    if only:
        properties = (x for x in properties if x[0] in only)
    elif exclude:
        properties = (x for x in properties if x[0] not in exclude)

    field_dict = {}
    for name, prop in properties:
        field = converter.convert(model, mapper, prop,
            field_args.get(name), db_session)
        if field is not None:
            field_dict[name] = field

    return field_dict


def model_form(model, db_session=None, base_class=Form, only=None,
    exclude=None, field_args=None, converter=None, exclude_pk=True,
    exclude_fk=True, type_name=None):
    """
    Create a wtforms Form for a given SQLAlchemy model class::

        from wtalchemy.orm import model_form
        from myapp.models import User
        UserForm = model_form(User)

    :param model:
        A SQLAlchemy mapped model class.
    :param db_session:
        An optional SQLAlchemy Session.
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments used
        to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    :param exclude_pk:
        An optional boolean to force primary key exclusion.
    :param exclude_fk:
        An optional boolean to force foreign keys exclusion.
    :param type_name:
        An optional string to set returned type name.
    """
    class ModelForm(base_class):
        """Sets object as form attribute."""
        def __init__(self, *args, **kwargs):
            if 'obj' in kwargs:
                self._obj = kwargs['obj']
            super(ModelForm, self).__init__(*args, **kwargs)

    if not exclude:
        exclude = []
    model_mapper = model.__mapper__
    for prop in model_mapper.iterate_properties:
        if not hasattr(prop, 'direction') and prop.columns[0].primary_key:
            if exclude_pk:
                exclude.append(prop.key)
        if hasattr(prop, 'direction') and  exclude_fk and \
                prop.direction.name != 'MANYTOMANY':
            for pair in prop.local_remote_pairs:
                exclude.append(pair[0].key)
    type_name = type_name or str(model.__name__ + 'Form')
    field_dict = model_fields(model, db_session, only, exclude, field_args,
        converter)
    return type(type_name, (ModelForm, ), field_dict)

########NEW FILE########
__FILENAME__ = validators
from __future__ import unicode_literals

from wtforms import ValidationError
from sqlalchemy.orm.exc import NoResultFound


class Unique(object):
    """Checks field value unicity against specified table field.

    :param get_session:
        A function that return a SQAlchemy Session.
    :param model:
        The model to check unicity against.
    :param column:
        The unique column.
    :param message:
        The error message.
    """
    field_flags = ('unique', )

    def __init__(self, get_session, model, column, message=None):
        self.get_session = get_session
        self.model = model
        self.column = column
        self.message = message

    def __call__(self, form, field):
        try:
            obj = self.get_session().query(self.model)\
                .filter(self.column == field.data).one()
            if not hasattr(form, '_obj') or not form._obj == obj:
                if self.message is None:
                    self.message = field.gettext('Already exists.')
                raise ValidationError(self.message)
        except NoResultFound:
            pass

########NEW FILE########
__FILENAME__ = core
from __future__ import unicode_literals

import datetime
import decimal
import itertools
import time

from wtforms import widgets
from wtforms.compat import text_type, izip
from wtforms.validators import StopValidation


__all__ = (
    'BooleanField', 'DecimalField', 'DateField', 'DateTimeField', 'FieldList',
    'FloatField', 'FormField', 'IntegerField', 'RadioField', 'SelectField',
    'SelectMultipleField', 'StringField',
)


_unset_value = object()


class DummyTranslations(object):
    def gettext(self, string):
        return string

    def ngettext(self, singular, plural, n):
        if n == 1:
            return singular

        return plural


class Field(object):
    """
    Field base class
    """
    errors = tuple()
    process_errors = tuple()
    raw_data = None
    validators = tuple()
    widget = None
    _formfield = True
    _translations = DummyTranslations()
    do_not_call_in_templates = True # Allow Django 1.4 traversal

    def __new__(cls, *args, **kwargs):
        if '_form' in kwargs and '_name' in kwargs:
            return super(Field, cls).__new__(cls)
        else:
            return UnboundField(cls, *args, **kwargs)

    def __init__(self, label=None, validators=None, filters=tuple(),
                 description='', id=None, default=None, widget=None,
                 _form=None, _name=None, _prefix='', _translations=None):
        """
        Construct a new field.

        :param label:
            The label of the field.
        :param validators:
            A sequence of validators to call when `validate` is called.
        :param filters:
            A sequence of filters which are run on input data by `process`.
        :param description:
            A description for the field, typically used for help text.
        :param id:
            An id to use for the field. A reasonable default is set by the form,
            and you shouldn't need to set this manually.
        :param default:
            The default value to assign to the field, if no form or object
            input is provided. May be a callable.
        :param widget:
            If provided, overrides the widget used to render the field.
        :param _form:
            The form holding this field. It is passed by the form itself during
            construction. You should never pass this value yourself.
        :param _name:
            The name of this field, passed by the enclosing form during its
            construction. You should never pass this value yourself.
        :param _prefix:
            The prefix to prepend to the form name of this field, passed by
            the enclosing form during construction.

        If `_form` and `_name` isn't provided, an :class:`UnboundField` will be
        returned instead. Call its :func:`bind` method with a form instance and
        a name to construct the field.
        """
        if _translations is not None:
            self._translations = _translations

        self.default = default
        self.description = description
        self.filters = filters
        self.flags = Flags()
        self.name = _prefix + _name
        self.short_name = _name
        self.type = type(self).__name__
        self.validators = validators or list(self.validators)

        self.id = id or self.name
        self.label = Label(self.id, label if label is not None else self.gettext(_name.replace('_', ' ').title()))

        if widget is not None:
            self.widget = widget

        for v in self.validators:
            flags = getattr(v, 'field_flags', ())
            for f in flags:
                setattr(self.flags, f, True)

    def __unicode__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the `__call__` method.
        """
        return self()

    def __str__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the `__call__` method.
        """
        return self()

    def __html__(self):
        """
        Returns a HTML representation of the field. For more powerful rendering,
        see the `__call__` method.
        """
        return self()

    def __call__(self, **kwargs):
        """
        Render this field as HTML, using keyword args as additional attributes.

        Any HTML attribute passed to the method will be added to the tag
        and entity-escaped properly.
        """
        return self.widget(self, **kwargs)

    def gettext(self, string):
        return self._translations.gettext(string)

    def ngettext(self, singular, plural, n):
        return self._translations.ngettext(singular, plural, n)

    def validate(self, form, extra_validators=tuple()):
        """
        Validates the field and returns True or False. `self.errors` will
        contain any errors raised during validation. This is usually only
        called by `Form.validate`.

        Subfields shouldn't override this, but rather override either
        `pre_validate`, `post_validate` or both, depending on needs.

        :param form: The form the field belongs to.
        :param extra_validators: A sequence of extra validators to run.
        """
        self.errors = list(self.process_errors)
        stop_validation = False

        # Call pre_validate
        try:
            self.pre_validate(form)
        except StopValidation as e:
            if e.args and e.args[0]:
                self.errors.append(e.args[0])
            stop_validation = True
        except ValueError as e:
            self.errors.append(e.args[0])

        # Run validators
        if not stop_validation:
            chain = itertools.chain(self.validators, extra_validators)
            stop_validation = self._run_validation_chain(form, chain)

        # Call post_validate
        try:
            self.post_validate(form, stop_validation)
        except ValueError as e:
            self.errors.append(e.args[0])

        return len(self.errors) == 0

    def _run_validation_chain(self, form, validators):
        """
        Run a validation chain, stopping if any validator raises StopValidation.

        :param form: The Form instance this field beongs to.
        :param validators: a sequence or iterable of validator callables.
        :return: True if validation was stopped, False otherwise.
        """
        for validator in validators:
            try:
                validator(form, self)
            except StopValidation as e:
                if e.args and e.args[0]:
                    self.errors.append(e.args[0])
                return True
            except ValueError as e:
                self.errors.append(e.args[0])

        return False

    def pre_validate(self, form):
        """
        Override if you need field-level validation. Runs before any other
        validators.

        :param form: The form the field belongs to.
        """
        pass

    def post_validate(self, form, validation_stopped):
        """
        Override if you need to run any field-level validation tasks after
        normal validation. This shouldn't be needed in most cases.

        :param form: The form the field belongs to.
        :param validation_stopped:
            `True` if any validator raised StopValidation.
        """
        pass

    def process(self, formdata, data=_unset_value):
        """
        Process incoming data, calling process_data, process_formdata as needed,
        and run filters.

        If `data` is not provided, process_data will be called on the field's
        default.

        Field subclasses usually won't override this, instead overriding the
        process_formdata and process_data methods. Only override this for
        special advanced processing, such as when a field encapsulates many
        inputs.
        """
        self.process_errors = []
        if data is _unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        try:
            self.process_data(data)
        except ValueError as e:
            self.process_errors.append(e.args[0])

        if formdata:
            try:
                if self.name in formdata:
                    self.raw_data = formdata.getlist(self.name)
                else:
                    self.raw_data = []
                self.process_formdata(self.raw_data)
            except ValueError as e:
                self.process_errors.append(e.args[0])

        for filter in self.filters:
            try:
                self.data = filter(self.data)
            except ValueError as e:
                self.process_errors.append(e.args[0])

    def process_data(self, value):
        """
        Process the Python data applied to this field and store the result.

        This will be called during form construction by the form's `kwargs` or
        `obj` argument.

        :param value: The python object containing the value to process.
        """
        self.data = value

    def process_formdata(self, valuelist):
        """
        Process data received over the wire from a form.

        This will be called during form construction with data supplied
        through the `formdata` argument.

        :param valuelist: A list of strings to process.
        """
        if valuelist:
            self.data = valuelist[0]

    def populate_obj(self, obj, name):
        """
        Populates `obj.<name>` with the field's data.

        :note: This is a destructive operation. If `obj.<name>` already exists,
               it will be overridden. Use with caution.
        """
        setattr(obj, name, self.data)


class UnboundField(object):
    _formfield = True
    creation_counter = 0

    def __init__(self, field_class, *args, **kwargs):
        UnboundField.creation_counter += 1
        self.field_class = field_class
        self.args = args
        self.kwargs = kwargs
        self.creation_counter = UnboundField.creation_counter

    def bind(self, form, name, prefix='', translations=None, **kwargs):
        return self.field_class(_form=form, _prefix=prefix, _name=name, _translations=translations, *self.args, **dict(self.kwargs, **kwargs))

    def __repr__(self):
        return '<UnboundField(%s, %r, %r)>' % (self.field_class.__name__, self.args, self.kwargs)


class Flags(object):
    """
    Holds a set of boolean flags as attributes.

    Accessing a non-existing attribute returns False for its value.
    """
    def __getattr__(self, name):
        if name.startswith('_'):
            return super(Flags, self).__getattr__(name)
        return False

    def __contains__(self, name):
        return getattr(self, name)

    def __repr__(self):
        flags = (name for name in dir(self) if not name.startswith('_'))
        return '<wtforms.fields.Flags: {%s}>' % ', '.join(flags)


class Label(object):
    """
    An HTML form label.
    """
    def __init__(self, field_id, text):
        self.field_id = field_id
        self.text = text

    def __str__(self):
        return self()

    def __unicode__(self):
        return self()

    def __html__(self):
        return self()

    def __call__(self, text=None, **kwargs):
        kwargs['for'] = self.field_id
        attributes = widgets.html_params(**kwargs)
        return widgets.HTMLString('<label %s>%s</label>' % (attributes, text or self.text))

    def __repr__(self):
        return 'Label(%r, %r)' % (self.field_id, self.text)


class SelectFieldBase(Field):
    option_widget = widgets.Option()

    """
    Base class for fields which can be iterated to produce options.

    This isn't a field, but an abstract base class for fields which want to
    provide this functionality.
    """
    def __init__(self, label=None, validators=None, option_widget=None, **kwargs):
        super(SelectFieldBase, self).__init__(label, validators, **kwargs)

        if option_widget is not None:
            self.option_widget = option_widget

    def iter_choices(self):
        """
        Provides data for choice widget rendering. Must return a sequence or
        iterable of (value, label, selected) tuples.
        """
        raise NotImplementedError()

    def __iter__(self):
        opts = dict(widget=self.option_widget, _name=self.name, _form=None)
        for i, (value, label, checked) in enumerate(self.iter_choices()):
            opt = self._Option(label=label, id='%s-%d' % (self.id, i), **opts)
            opt.process(None, value)
            opt.checked = checked
            yield opt

    class _Option(Field):
        checked = False

        def _value(self):
            return text_type(self.data)


class SelectField(SelectFieldBase):
    widget = widgets.Select()

    def __init__(self, label=None, validators=None, coerce=text_type, choices=None, **kwargs):
        super(SelectField, self).__init__(label, validators, **kwargs)
        self.coerce = coerce
        self.choices = choices

    def iter_choices(self):
        for value, label in self.choices:
            yield (value, label, self.coerce(value) == self.data)

    def process_data(self, value):
        try:
            self.data = self.coerce(value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = self.coerce(valuelist[0])
            except ValueError:
                raise ValueError(self.gettext('Invalid Choice: could not coerce'))

    def pre_validate(self, form):
        for v, _ in self.choices:
            if self.data == v:
                break
        else:
            raise ValueError(self.gettext('Not a valid choice'))


class SelectMultipleField(SelectField):
    """
    No different from a normal select field, except this one can take (and
    validate) multiple choices.  You'll need to specify the HTML `rows`
    attribute to the select field when rendering.
    """
    widget = widgets.Select(multiple=True)

    def iter_choices(self):
        for value, label in self.choices:
            selected = self.data is not None and self.coerce(value) in self.data
            yield (value, label, selected)

    def process_data(self, value):
        try:
            self.data = list(self.coerce(v) for v in value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        try:
            self.data = list(self.coerce(x) for x in valuelist)
        except ValueError:
            raise ValueError(self.gettext('Invalid choice(s): one or more data inputs could not be coerced'))

    def pre_validate(self, form):
        if self.data:
            values = list(c[0] for c in self.choices)
            for d in self.data:
                if d not in values:
                    raise ValueError(self.gettext("'%(value)s' is not a valid choice for this field") % dict(value=d))


class RadioField(SelectField):
    """
    Like a SelectField, except displays a list of radio buttons.

    Iterating the field will produce subfields (each containing a label as
    well) in order to allow custom rendering of the individual radio fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()


class StringField(Field):
    """
    This field is the base for most of the more complicated fields, and
    represents an ``<input type="text">``.
    """
    widget = widgets.TextInput()

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = valuelist[0]
        else:
            self.data = ''

    def _value(self):
        return text_type(self.data) if self.data is not None else ''


class IntegerField(Field):
    """
    A text field, except all input is coerced to an integer.  Erroneous input
    is ignored and will not be accepted as a value.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, **kwargs):
        super(IntegerField, self).__init__(label, validators, **kwargs)

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return text_type(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = int(valuelist[0])
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid integer value'))


class DecimalField(Field):
    """
    A text field which displays and coerces data of the `decimal.Decimal` type.

    :param places:
        How many decimal places to quantize the value to for display on form.
        If None, does not quantize value.
    :param rounding:
        How to round the value during quantize, for example
        `decimal.ROUND_UP`. If unset, uses the rounding value from the
        current thread's context.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, places=2, rounding=None, **kwargs):
        super(DecimalField, self).__init__(label, validators, **kwargs)
        self.places = places
        self.rounding = rounding

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            if self.places is not None:
                if hasattr(self.data, 'quantize'):
                    exp = decimal.Decimal('.1') ** self.places
                    if self.rounding is None:
                        quantized = self.data.quantize(exp)
                    else:
                        quantized = self.data.quantize(exp, rounding=self.rounding)
                    return text_type(quantized)
                else:
                    # If for some reason, data is a float or int, then format
                    # as we would for floats using string formatting.
                    format = '%%0.%df' % self.places
                    return format % self.data
            else:
                return text_type(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = decimal.Decimal(valuelist[0])
            except (decimal.InvalidOperation, ValueError):
                self.data = None
                raise ValueError(self.gettext('Not a valid decimal value'))


class FloatField(Field):
    """
    A text field, except all input is coerced to an float.  Erroneous input
    is ignored and will not be accepted as a value.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, **kwargs):
        super(FloatField, self).__init__(label, validators, **kwargs)

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return text_type(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = float(valuelist[0])
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid float value'))


class BooleanField(Field):
    """
    Represents an ``<input type="checkbox">``.
    """
    widget = widgets.CheckboxInput()

    def __init__(self, label=None, validators=None, **kwargs):
        super(BooleanField, self).__init__(label, validators, **kwargs)

    def process_data(self, value):
        self.data = bool(value)

    def process_formdata(self, valuelist):
        # Checkboxes and submit buttons simply do not send a value when
        # unchecked/not pressed. So the actual value="" doesn't matter for
        # purpose of determining .data, only whether one exists or not.
        self.data = bool(valuelist)

    def _value(self):
        if self.raw_data:
            return text_type(self.raw_data[0])
        else:
            return 'y'


class DateTimeField(Field):
    """
    A text field which stores a `datetime.datetime` matching a format.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, format='%Y-%m-%d %H:%M:%S', **kwargs):
        super(DateTimeField, self).__init__(label, validators, **kwargs)
        self.format = format

    def _value(self):
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            return self.data and self.data.strftime(self.format) or ''

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            try:
                self.data = datetime.datetime.strptime(date_str, self.format)
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid datetime value'))


class DateField(DateTimeField):
    """
    Same as DateTimeField, except stores a `datetime.date`.
    """
    def __init__(self, label=None, validators=None, format='%Y-%m-%d', **kwargs):
        super(DateField, self).__init__(label, validators, format, **kwargs)

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            try:
                self.data = datetime.datetime.strptime(date_str, self.format).date()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid date value'))


class FormField(Field):
    """
    Encapsulate a form as a field in another form.

    :param form_class:
        A subclass of Form that will be encapsulated.
    :param separator:
        A string which will be suffixed to this field's name to create the
        prefix to enclosed fields. The default is fine for most uses.
    """
    widget = widgets.TableWidget()

    def __init__(self, form_class, label=None, validators=None, separator='-', **kwargs):
        super(FormField, self).__init__(label, validators, **kwargs)
        self.form_class = form_class
        self.separator = separator
        self._obj = None
        if self.filters:
            raise TypeError('FormField cannot take filters, as the encapsulated data is not mutable.')
        if validators:
            raise TypeError('FormField does not accept any validators. Instead, define them on the enclosed form.')

    def process(self, formdata, data=_unset_value):
        if data is _unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default
            self._obj = data

        self.object_data = data

        prefix = self.name + self.separator
        if isinstance(data, dict):
            self.form = self.form_class(formdata=formdata, prefix=prefix, **data)
        else:
            self.form = self.form_class(formdata=formdata, obj=data, prefix=prefix)

    def validate(self, form, extra_validators=tuple()):
        if extra_validators:
            raise TypeError('FormField does not accept in-line validators, as it gets errors from the enclosed form.')
        return self.form.validate()

    def populate_obj(self, obj, name):
        candidate = getattr(obj, name, None)
        if candidate is None:
            if self._obj is None:
                raise TypeError('populate_obj: cannot find a value to populate from the provided obj or input data/defaults')
            candidate = self._obj
            setattr(obj, name, candidate)

        self.form.populate_obj(candidate)

    def __iter__(self):
        return iter(self.form)

    def __getitem__(self, name):
        return self.form[name]

    def __getattr__(self, name):
        return getattr(self.form, name)

    @property
    def data(self):
        return self.form.data

    @property
    def errors(self):
        return self.form.errors


class FieldList(Field):
    """
    Encapsulate an ordered list of multiple instances of the same field type,
    keeping data as a list.

    >>> authors = FieldList(TextField('Name', [validators.required()]))

    :param unbound_field:
        A partially-instantiated field definition, just like that would be
        defined on a form directly.
    :param min_entries:
        if provided, always have at least this many entries on the field,
        creating blank ones if the provided input does not specify a sufficient
        amount.
    :param max_entries:
        accept no more than this many entries as input, even if more exist in
        formdata.
    """
    widget=widgets.ListWidget()

    def __init__(self, unbound_field, label=None, validators=None, min_entries=0,
                 max_entries=None, default=tuple(), **kwargs):
        super(FieldList, self).__init__(label, validators, default=default, **kwargs)
        if self.filters:
            raise TypeError('FieldList does not accept any filters. Instead, define them on the enclosed field.')
        assert isinstance(unbound_field, UnboundField), 'Field must be unbound, not a field class'
        self.unbound_field = unbound_field
        self.min_entries = min_entries
        self.max_entries = max_entries
        self.last_index = -1
        self._prefix = kwargs.get('_prefix', '')

    def process(self, formdata, data=_unset_value):
        self.entries = []
        if data is _unset_value or not data:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        if formdata:
            indices = sorted(set(self._extract_indices(self.name, formdata)))
            if self.max_entries:
                indices = indices[:self.max_entries]

            idata = iter(data)
            for index in indices:
                try:
                    obj_data = next(idata)
                except StopIteration:
                    obj_data = _unset_value
                self._add_entry(formdata, obj_data, index=index)
        else:
            for obj_data in data:
                self._add_entry(formdata, obj_data)

        while len(self.entries) < self.min_entries:
            self._add_entry(formdata)

    def _extract_indices(self, prefix, formdata):
        """
        Yield indices of any keys with given prefix.

        formdata must be an object which will produce keys when iterated.  For
        example, if field 'foo' contains keys 'foo-0-bar', 'foo-1-baz', then
        the numbers 0 and 1 will be yielded, but not neccesarily in order.
        """
        offset = len(prefix) + 1
        for k in formdata:
            if k.startswith(prefix):
                k = k[offset:].split('-', 1)[0]
                if k.isdigit():
                    yield int(k)

    def validate(self, form, extra_validators=tuple()):
        """
        Validate this FieldList.

        Note that FieldList validation differs from normal field validation in
        that FieldList validates all its enclosed fields first before running any
        of its own validators.
        """
        self.errors = []

        # Run validators on all entries within
        for subfield in self.entries:
            if not subfield.validate(form):
                self.errors.append(subfield.errors)

        chain = itertools.chain(self.validators, extra_validators)
        stop_validation = self._run_validation_chain(form, chain)

        return len(self.errors) == 0

    def populate_obj(self, obj, name):
        values = getattr(obj, name, None)
        try:
            ivalues = iter(values)
        except TypeError:
            ivalues = iter([])

        candidates = itertools.chain(ivalues, itertools.repeat(None))
        _fake = type(str('_fake'), (object, ), {})
        output = []
        for field, data in izip(self.entries, candidates):
            fake_obj = _fake()
            fake_obj.data = data
            field.populate_obj(fake_obj, 'data')
            output.append(fake_obj.data)

        setattr(obj, name, output)

    def _add_entry(self, formdata=None, data=_unset_value, index=None):
        assert not self.max_entries or len(self.entries) < self.max_entries, \
            'You cannot have more than max_entries entries in this FieldList'
        new_index = self.last_index = index or (self.last_index + 1)
        name = '%s-%d' % (self.short_name, new_index)
        id   = '%s-%d' % (self.id, new_index)
        field = self.unbound_field.bind(form=None, name=name, prefix=self._prefix, id=id)
        field.process(formdata, data)
        self.entries.append(field)
        return field

    def append_entry(self, data=_unset_value):
        """
        Create a new entry with optional default data.

        Entries added in this way will *not* receive formdata however, and can
        only receive object data.
        """
        return self._add_entry(data=data)

    def pop_entry(self):
        """ Removes the last entry from the list and returns it. """
        entry = self.entries.pop()
        self.last_index -= 1
        return entry

    def __iter__(self):
        return iter(self.entries)

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        return self.entries[index]

    @property
    def data(self):
        return [f.data for f in self.entries]

########NEW FILE########
__FILENAME__ = simple
from .. import widgets
from .core import StringField, BooleanField


__all__ = (
    'BooleanField', 'TextAreaField', 'PasswordField', 'FileField',
    'HiddenField', 'SubmitField', 'TextField'
)


class TextField(StringField):
    """
    Legacy alias for StringField
    """

class TextAreaField(TextField):
    """
    This field represents an HTML ``<textarea>`` and can be used to take
    multi-line input.
    """
    widget = widgets.TextArea()


class PasswordField(TextField):
    """
    Represents an ``<input type="password">``.
    """
    widget = widgets.PasswordInput()


class FileField(TextField):
    """
    Can render a file-upload field.  Will take any passed filename value, if
    any is sent by the browser in the post params.  This field will NOT
    actually handle the file upload portion, as wtforms does not deal with
    individual frameworks' file handling capabilities.
    """
    widget = widgets.FileInput()


class HiddenField(TextField):
    """
    Represents an ``<input type="hidden">``.
    """
    widget = widgets.HiddenInput()


class SubmitField(BooleanField):
    """
    Represents an ``<input type="submit">``.  This allows checking if a given
    submit button has been pressed.
    """
    widget = widgets.SubmitInput()


########NEW FILE########
__FILENAME__ = form
import sys

__all__ = (
    'BaseForm',
    'Form',
)

from wtforms.compat import with_metaclass, iteritems, itervalues

class BaseForm(object):
    """
    Base Form Class.  Provides core behaviour like field construction,
    validation, and data and error proxying.
    """

    def __init__(self, fields, prefix=''):
        """
        :param fields:
            A dict or sequence of 2-tuples of partially-constructed fields.
        :param prefix:
            If provided, all fields will have their name prefixed with the
            value.
        """
        if prefix and prefix[-1] not in '-_;:/.':
            prefix += '-'

        self._prefix = prefix
        self._errors = None
        self._fields = {}

        if hasattr(fields, 'iteritems'):
            fields = fields.iteritems()
        elif hasattr(fields, 'items'):
            fields = fields.items()

        translations = self._get_translations()

        for name, unbound_field in fields:
            field = unbound_field.bind(form=self, name=name, prefix=prefix, translations=translations)
            self._fields[name] = field

    def __iter__(self):
        """ Iterate form fields in arbitrary order """
        return iter(itervalues(self._fields))

    def __contains__(self, name):
        """ Returns `True` if the named field is a member of this form. """
        return (name in self._fields)

    def __getitem__(self, name):
        """ Dict-style access to this form's fields."""
        return self._fields[name]

    def __setitem__(self, name, value):
        """ Bind a field to this form. """
        self._fields[name] = value.bind(form=self, name=name, prefix=self._prefix)

    def __delitem__(self, name):
        """ Remove a field from this form. """
        del self._fields[name]

    def _get_translations(self):
        """
        Override in subclasses to provide alternate translations factory.

        Must return an object that provides gettext() and ngettext() methods.
        """
        return None

    def populate_obj(self, obj):
        """
        Populates the attributes of the passed `obj` with data from the form's
        fields.

        :note: This is a destructive operation; Any attribute with the same name
               as a field will be overridden. Use with caution.
        """
        for name, field in iteritems(self._fields):
            field.populate_obj(obj, name)

    def process(self, formdata=None, obj=None, **kwargs):
        """
        Take form, object data, and keyword arg input and have the fields
        process them.

        :param formdata:
            Used to pass data coming from the enduser, usually `request.POST` or
            equivalent.
        :param obj:
            If `formdata` is empty or not provided, this object is checked for
            attributes matching form field names, which will be used for field
            values.
        :param `**kwargs`:
            If `formdata` is empty or not provided and `obj` does not contain
            an attribute named the same as a field, form will assign the value
            of a matching keyword argument to the field, if one exists.
        """
        if formdata is not None and not hasattr(formdata, 'getlist'):
            if hasattr(formdata, 'getall'):
                formdata = WebobInputWrapper(formdata)
            else:
                raise TypeError("formdata should be a multidict-type wrapper that supports the 'getlist' method")

        for name, field, in iteritems(self._fields):
            if obj is not None and hasattr(obj, name):
                field.process(formdata, getattr(obj, name))
            elif name in kwargs:
                field.process(formdata, kwargs[name])
            else:
                field.process(formdata)

    def validate(self, extra_validators=None):
        """
        Validates the form by calling `validate` on each field.

        :param extra_validators:
            If provided, is a dict mapping field names to a sequence of
            callables which will be passed as extra validators to the field's
            `validate` method.

        Returns `True` if no errors occur.
        """
        self._errors = None
        success = True
        for name, field in iteritems(self._fields):
            if extra_validators is not None and name in extra_validators:
                extra = extra_validators[name]
            else:
                extra = tuple()
            if not field.validate(self, extra):
                success = False
        return success

    @property
    def data(self):
        return dict((name, f.data) for name, f in iteritems(self._fields))

    @property
    def errors(self):
        if self._errors is None:
            self._errors = dict((name, f.errors) for name, f in iteritems(self._fields) if f.errors)
        return self._errors


class FormMeta(type):
    """
    The metaclass for `Form` and any subclasses of `Form`.

    `FormMeta`'s responsibility is to create the `_unbound_fields` list, which
    is a list of `UnboundField` instances sorted by their order of
    instantiation.  The list is created at the first instantiation of the form.
    If any fields are added/removed from the form, the list is cleared to be
    re-generated on the next instantiaton.

    Any properties which begin with an underscore or are not `UnboundField`
    instances are ignored by the metaclass.
    """
    def __init__(cls, name, bases, attrs):
        type.__init__(cls, name, bases, attrs)
        cls._unbound_fields = None

    def __call__(cls, *args, **kwargs):
        """
        Construct a new `Form` instance, creating `_unbound_fields` on the
        class if it is empty.
        """
        if cls._unbound_fields is None:
            fields = []
            for name in dir(cls):
                if not name.startswith('_'):
                    unbound_field = getattr(cls, name)
                    if hasattr(unbound_field, '_formfield'):
                        fields.append((name, unbound_field))
            # We keep the name as the second element of the sort
            # to ensure a stable sort.
            fields.sort(key=lambda x: (x[1].creation_counter, x[0]))
            cls._unbound_fields = fields
        return type.__call__(cls, *args, **kwargs)

    def __setattr__(cls, name, value):
        """
        Add an attribute to the class, clearing `_unbound_fields` if needed.
        """
        if not name.startswith('_') and hasattr(value, '_formfield'):
            cls._unbound_fields = None
        type.__setattr__(cls, name, value)

    def __delattr__(cls, name):
        """
        Remove an attribute from the class, clearing `_unbound_fields` if
        needed.
        """
        if not name.startswith('_'):
            cls._unbound_fields = None
        type.__delattr__(cls, name)


class Form(with_metaclass(FormMeta, BaseForm)):
    """
    Declarative Form base class. Extends BaseForm's core behaviour allowing
    fields to be defined on Form subclasses as class attributes.

    In addition, form and instance input data are taken at construction time
    and passed to `process()`.
    """

    def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
        """
        :param formdata:
            Used to pass data coming from the enduser, usually `request.POST` or
            equivalent.
        :param obj:
            If `formdata` is empty or not provided, this object is checked for
            attributes matching form field names, which will be used for field
            values.
        :param prefix:
            If provided, all fields will have their name prefixed with the
            value.
        :param `**kwargs`:
            If `formdata` is empty or not provided and `obj` does not contain
            an attribute named the same as a field, form will assign the value
            of a matching keyword argument to the field, if one exists.
        """
        super(Form, self).__init__(self._unbound_fields, prefix=prefix)

        for name, field in iteritems(self._fields):
            # Set all the fields to attributes so that they obscure the class
            # attributes with the same names.
            setattr(self, name, field)

        self.process(formdata, obj, **kwargs)

    def __iter__(self):
        """ Iterate form fields in their order of definition on the form. """
        for name, _ in self._unbound_fields:
            if name in self._fields:
                yield self._fields[name]

    def __setitem__(self, name, value):
        raise TypeError('Fields may not be added to Form instances, only classes.')

    def __delitem__(self, name):
        del self._fields[name]
        setattr(self, name, None)

    def __delattr__(self, name):
        try:
            self.__delitem__(name)
        except KeyError:
            super(Form, self).__delattr__(name)

    def validate(self):
        """
        Validates the form by calling `validate` on each field, passing any
        extra `Form.validate_<fieldname>` validators to the field validator.
        """
        extra = {}
        for name in self._fields:
            inline = getattr(self.__class__, 'validate_%s' % name, None)
            if inline is not None:
                extra[name] = [inline]

        return super(Form, self).validate(extra)


class WebobInputWrapper(object):
    """
    Wrap a webob MultiDict for use as passing as `formdata` to Field.

    Since for consistency, we have decided in WTForms to support as input a
    small subset of the API provided in common between cgi.FieldStorage,
    Django's QueryDict, and Werkzeug's MultiDict, we need to wrap Webob, the
    only supported framework whose multidict does not fit this API, but is
    nevertheless used by a lot of frameworks.

    While we could write a full wrapper to support all the methods, this will
    undoubtedly result in bugs due to some subtle differences between the
    various wrappers. So we will keep it simple.
    """

    def __init__(self, multidict):
        self._wrapped = multidict

    def __iter__(self):
        return iter(self._wrapped)

    def __len__(self):
        return len(self._wrapped)

    def __contains__(self, name):
        return (name in self._wrapped)

    def getlist(self, name):
        return self._wrapped.getall(name)


########NEW FILE########
__FILENAME__ = validators
from __future__ import unicode_literals

import re

from wtforms.compat import string_types, text_type

__all__ = (
    'DataRequired', 'data_required', 'Email', 'email', 'EqualTo', 'equal_to',
    'IPAddress', 'ip_address', 'InputRequired', 'input_required', 'Length',
    'length', 'NumberRange', 'number_range', 'Optional', 'optional',
    'Required', 'required', 'Regexp', 'regexp', 'URL', 'url', 'AnyOf',
    'any_of', 'NoneOf', 'none_of', 'MacAddress', 'mac_address', 'UUID'
)


class ValidationError(ValueError):
    """
    Raised when a validator fails to validate its input.
    """
    def __init__(self, message='', *args, **kwargs):
        ValueError.__init__(self, message, *args, **kwargs)


class StopValidation(Exception):
    """
    Causes the validation chain to stop.

    If StopValidation is raised, no more validators in the validation chain are
    called. If raised with a message, the message will be added to the errors
    list.
    """
    def __init__(self, message='', *args, **kwargs):
        Exception.__init__(self, message, *args, **kwargs)


class EqualTo(object):
    """
    Compares the values of two fields.

    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    """
    def __init__(self, fieldname, message=None):
        self.fieldname = fieldname
        self.message = message

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise ValidationError(field.gettext("Invalid field name '%s'.") % self.fieldname)
        if field.data != other.data:
            d = {
                'other_label': hasattr(other, 'label') and other.label.text or self.fieldname,
                'other_name': self.fieldname
            }
            if self.message is None:
                self.message = field.gettext('Field must be equal to %(other_name)s.')

            raise ValidationError(self.message % d)


class Length(object):
    """
    Validates the length of a string.

    :param min:
        The minimum required length of the string. If not provided, minimum
        length will not be checked.
    :param max:
        The maximum length of the string. If not provided, maximum length
        will not be checked.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated using `%(min)d` and `%(max)d` if desired. Useful defaults
        are provided depending on the existence of min and max.
    """
    def __init__(self, min=-1, max=-1, message=None):
        assert min != -1 or max!=-1, 'At least one of `min` or `max` must be specified.'
        assert max == -1 or min <= max, '`min` cannot be more than `max`.'
        self.min = min
        self.max = max
        self.message = message

    def __call__(self, form, field):
        l = field.data and len(field.data) or 0
        if l < self.min or self.max != -1 and l > self.max:
            if self.message is None:
                if self.max == -1:
                    self.message = field.ngettext('Field must be at least %(min)d character long.',
                                                  'Field must be at least %(min)d characters long.', self.min)
                elif self.min == -1:
                    self.message = field.ngettext('Field cannot be longer than %(max)d character.',
                                                  'Field cannot be longer than %(max)d characters.', self.max)
                else:
                    self.message = field.gettext('Field must be between %(min)d and %(max)d characters long.')

            raise ValidationError(self.message % dict(min=self.min, max=self.max))


class NumberRange(object):
    """
    Validates that a number is of a minimum and/or maximum value, inclusive.
    This will work with any comparable number type, such as floats and
    decimals, not just integers.

    :param min:
        The minimum required value of the number. If not provided, minimum
        value will not be checked.
    :param max:
        The maximum value of the number. If not provided, maximum value
        will not be checked.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated using `%(min)s` and `%(max)s` if desired. Useful defaults
        are provided depending on the existence of min and max.
    """
    def __init__(self, min=None, max=None, message=None):
        self.min = min
        self.max = max
        self.message = message

    def __call__(self, form, field):
        data = field.data
        if data is None or (self.min is not None and data < self.min) or \
            (self.max is not None and data > self.max):
            if self.message is None:
                # we use %(min)s interpolation to support floats, None, and
                # Decimals without throwing a formatting exception.
                if self.max is None:
                    self.message = field.gettext('Number must be at least %(min)s.')
                elif self.min is None:
                    self.message = field.gettext('Number must be at most %(max)s.')
                else:
                    self.message = field.gettext('Number must be between %(min)s and %(max)s.')

            raise ValidationError(self.message % dict(min=self.min, max=self.max))


class Optional(object):
    """
    Allows empty input and stops the validation chain from continuing.

    If input is empty, also removes prior errors (such as processing errors)
    from the field.

    :param strip_whitespace:
        If True (the default) also stop the validation chain on input which
        consists of only whitespace.
    """
    field_flags = ('optional', )

    def __init__(self, strip_whitespace=True):
        if strip_whitespace:
            self.string_check = lambda s: s.strip()
        else:
            self.string_check = lambda s: s

    def __call__(self, form, field):
        if not field.raw_data or isinstance(field.raw_data[0], string_types) and not self.string_check(field.raw_data[0]):
            field.errors[:] = []
            raise StopValidation()


class DataRequired(object):
    """
    Validates that the field contains data. This validator will stop the
    validation chain on error.

    If the data is empty, also removes prior errors (such as processing errors)
    from the field.

    :param message:
        Error message to raise in case of a validation error.
    """
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not field.data or isinstance(field.data, string_types) and not field.data.strip():
            if self.message is None:
                self.message = field.gettext('This field is required.')

            field.errors[:] = []
            raise StopValidation(self.message)


class Required(DataRequired):
    """
    Legacy alias for DataRequired.

    This is needed over simple aliasing for those who require that the
    class-name of required be 'Required.'

    This class will start throwing deprecation warnings in WTForms 1.1 and be removed by 1.2.
    """


class InputRequired(object):
    """
    Validates that input was provided for this field.

    Note there is a distinction between this and DataRequired in that
    InputRequired looks that form-input data was provided, and DataRequired
    looks at the post-coercion data.
    """
    field_flags = ('required', )

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if not field.raw_data or not field.raw_data[0]:
            if self.message is None:
                self.message = field.gettext('This field is required.')

            field.errors[:] = []
            raise StopValidation(self.message)


class Regexp(object):
    """
    Validates the field against a user provided regexp.

    :param regex:
        The regular expression string to use. Can also be a compiled regular
        expression pattern.
    :param flags:
        The regexp flags to use, for example re.IGNORECASE. Ignored if
        `regex` is not a string.
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, regex, flags=0, message=None):
        if isinstance(regex, string_types):
            regex = re.compile(regex, flags)
        self.regex = regex
        self.message = message

    def __call__(self, form, field):
        if not self.regex.match(field.data or ''):
            if self.message is None:
                self.message = field.gettext('Invalid input.')

            raise ValidationError(self.message)


class Email(Regexp):
    """
    Validates an email address. Note that this uses a very primitive regular
    expression and should only be used in instances where you later verify by
    other means, such as email activation or lookups.

    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, message=None):
        super(Email, self).__init__(r'^.+@[^.].*\.[a-z]{2,10}$', re.IGNORECASE, message)

    def __call__(self, form, field):
        if self.message is None:
            self.message = field.gettext('Invalid email address.')

        super(Email, self).__call__(form, field)


class IPAddress(object):
    """
    Validates an IPv4 (IPv6 too with ipv6=True) address.

    :param ipv6:
        If True, accept IPv6 as valid also.
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, ipv6=False, message=None):
        self.ipv6 = ipv6
        self.message = message

    def __call__(self, form, field):
        value = field.data
        valid = False
        if value:
            valid = self.check_ipv4(value)

            if not valid and self.ipv6:
                valid = self.check_ipv6(value)

        if not valid:
            if self.message is None:
                self.message = field.gettext('Invalid IP address.')
            raise ValidationError(self.message)

    def check_ipv4(self, value):
        parts = value.split('.')
        if len(parts) == 4 and all(x.isdigit() for x in parts):
            numbers = list(int(x) for x in parts)
            return all(num >= 0 and num < 256 for num in numbers)
        return False

    def check_ipv6(self, value):
        parts = value.split(':')
        if len(parts) > 8:
            return False

        num_blank = 0
        for part in parts:
            if not part:
                num_blank += 1
            else:
                try:
                    value = int(part, 16)
                except ValueError:
                    return False
                else:
                    if value < 0 or value >= 65536:
                        return False

        if num_blank < 2:
            return True
        elif num_blank == 2 and not parts[0] and not parts[1]:
            return True
        return False


class MacAddress(Regexp):
    """
    Validates a MAC address.

    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, message=None):
        pattern = r'^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$'
        super(MacAddress, self).__init__(pattern, message=message)

    def __call__(self, form, field):
        if self.message is None:
            self.message = field.gettext('Invalid Mac address.')

        super(MacAddress, self).__call__(form, field)


class URL(Regexp):
    """
    Simple regexp based url validation. Much like the email validator, you
    probably want to validate the url later by other means if the url must
    resolve.

    :param require_tld:
        If true, then the domain-name portion of the URL must contain a .tld
        suffix.  Set this to false if you want to allow domains like
        `localhost`.
    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, require_tld=True, message=None):
        tld_part = (require_tld and r'\.[a-z]{2,10}' or '')
        regex = r'^[a-z]+://([^/:]+%s|([0-9]{1,3}\.){3}[0-9]{1,3})(:[0-9]+)?(\/.*)?$' % tld_part
        super(URL, self).__init__(regex, re.IGNORECASE, message)

    def __call__(self, form, field):
        if self.message is None:
            self.message = field.gettext('Invalid URL.')

        super(URL, self).__call__(form, field)


class UUID(Regexp):
    """
    Validates a UUID.

    :param message:
        Error message to raise in case of a validation error.
    """
    def __init__(self, message=None):
        pattern = r'^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$'
        super(UUID, self).__init__(pattern, message=message)

    def __call__(self, form, field):
        if self.message is None:
            self.message = field.gettext('Invalid UUID.')

        super(UUID, self).__call__(form, field)


class AnyOf(object):
    """
    Compares the incoming data to a sequence of valid inputs.

    :param values:
        A sequence of valid inputs.
    :param message:
        Error message to raise in case of a validation error. `%(values)s`
        contains the list of values.
    :param values_formatter:
        Function used to format the list of values in the error message.
    """
    def __init__(self, values, message=None, values_formatter=None):
        self.values = values
        self.message = message
        if values_formatter is None:
            values_formatter = lambda v: ', '.join(text_type(x) for x in v)
        self.values_formatter = values_formatter

    def __call__(self, form, field):
        if field.data not in self.values:
            if self.message is None:
                self.message = field.gettext('Invalid value, must be one of: %(values)s.')

            raise ValidationError(self.message % dict(values=self.values_formatter(self.values)))


class NoneOf(object):
    """
    Compares the incoming data to a sequence of invalid inputs.

    :param values:
        A sequence of invalid inputs.
    :param message:
        Error message to raise in case of a validation error. `%(values)s`
        contains the list of values.
    :param values_formatter:
        Function used to format the list of values in the error message.
    """
    def __init__(self, values, message=None, values_formatter=None):
        self.values = values
        self.message = message
        if values_formatter is None:
            values_formatter = lambda v: ', '.join(text_type(x) for x in v)
        self.values_formatter = values_formatter

    def __call__(self, form, field):
        if field.data in self.values:
            if self.message is None:
                self.message = field.gettext('Invalid value, can\'t be any of: %(values)s.')

            raise ValidationError(self.message % dict(values=self.values_formatter(self.values)))


email = Email
equal_to = EqualTo
ip_address = IPAddress
mac_address = MacAddress
length = Length
number_range = NumberRange
optional = Optional
required = Required
input_required = InputRequired
data_required = DataRequired
regexp = Regexp
url = URL
any_of = AnyOf
none_of = NoneOf

########NEW FILE########
__FILENAME__ = core
from __future__ import unicode_literals

from cgi import escape

from wtforms.compat import text_type, string_types, iteritems

__all__ = (
    'CheckboxInput', 'FileInput', 'HiddenInput', 'ListWidget', 'PasswordInput',
    'RadioInput', 'Select', 'SubmitInput', 'TableWidget', 'TextArea',
    'TextInput', 'Option'
)


def html_params(**kwargs):
    """
    Generate HTML parameters from inputted keyword arguments.

    The output value is sorted by the passed keys, to provide consistent output
    each time this function is called with the same parameters.  Because of the
    frequent use of the normally reserved keywords `class` and `for`, suffixing
    these with an underscore will allow them to be used.

    >>> html_params(name='text1', id='f', class_='text') == 'class="text" id="f" name="text1"'
    True
    """
    params = []
    for k,v in sorted(iteritems(kwargs)):
        if k in ('class_', 'class__', 'for_'):
            k = k[:-1]
        if v is True:
            params.append(k)
        else:
            params.append('%s="%s"' % (text_type(k), escape(text_type(v), quote=True)))
    return ' '.join(params)


class HTMLString(text_type):
    def __html__(self):
        return self


class ListWidget(object):
    """
    Renders a list of fields as a `ul` or `ol` list.

    This is used for fields which encapsulate many inner fields as subfields.
    The widget will try to iterate the field to get access to the subfields and
    call them to render them.

    If `prefix_label` is set, the subfield's label is printed before the field,
    otherwise afterwards. The latter is useful for iterating radios or
    checkboxes.
    """
    def __init__(self, html_tag='ul', prefix_label=True):
        assert html_tag in ('ol', 'ul')
        self.html_tag = html_tag
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = ['<%s %s>' % (self.html_tag, html_params(**kwargs))]
        for subfield in field:
            if self.prefix_label:
                html.append('<li>%s: %s</li>' % (subfield.label, subfield()))
            else:
                html.append('<li>%s %s</li>' % (subfield(), subfield.label))
        html.append('</%s>' % self.html_tag)
        return HTMLString(''.join(html))


class TableWidget(object):
    """
    Renders a list of fields as a set of table rows with th/td pairs.

    If `with_table_tag` is True, then an enclosing <table> is placed around the
    rows.

    Hidden fields will not be displayed with a row, instead the field will be 
    pushed into a subsequent table row to ensure XHTML validity. Hidden fields
    at the end of the field list will appear outside the table.
    """
    def __init__(self, with_table_tag=True):
        self.with_table_tag = with_table_tag

    def __call__(self, field, **kwargs):
        html = []
        if self.with_table_tag:
            kwargs.setdefault('id', field.id)
            html.append('<table %s>' % html_params(**kwargs))
        hidden = ''
        for subfield in field:
            if subfield.type == 'HiddenField':
                hidden += text_type(subfield)
            else:
                html.append('<tr><th>%s</th><td>%s%s</td></tr>' % (text_type(subfield.label), hidden, text_type(subfield)))
                hidden = ''
        if self.with_table_tag:
            html.append('</table>')
        if hidden:
            html.append(hidden)
        return HTMLString(''.join(html))


class Input(object):
    """
    Render a basic ``<input>`` field.

    This is used as the basis for most of the other input fields.

    By default, the `_value()` method will be called upon the associated field
    to provide the ``value=`` HTML attribute.
    """
    html_params = staticmethod(html_params)

    def __init__(self, input_type=None):
        if input_type is not None:
            self.input_type = input_type

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('type', self.input_type)
        if 'value' not in kwargs:
            kwargs['value'] = field._value()
        return HTMLString('<input %s>' % self.html_params(name=field.name, **kwargs))


class TextInput(Input):
    """
    Render a single-line text input.
    """
    input_type = 'text'


class PasswordInput(Input):
    """
    Render a password input.

    For security purposes, this field will not reproduce the value on a form
    submit by default. To have the value filled in, set `hide_value` to
    `False`.
    """
    input_type = 'password'

    def __init__(self, hide_value=True):
        self.hide_value = hide_value

    def __call__(self, field, **kwargs): 
        if self.hide_value:
            kwargs['value'] = ''
        return super(PasswordInput, self).__call__(field, **kwargs)


class HiddenInput(Input):
    """
    Render a hidden input.
    """
    input_type = 'hidden'


class CheckboxInput(Input):
    """
    Render a checkbox.

    The ``checked`` HTML attribute is set if the field's data is a non-false value.
    """
    input_type = 'checkbox'

    def __call__(self, field, **kwargs):
        if getattr(field, 'checked', field.data):
            kwargs['checked'] = True
        return super(CheckboxInput, self).__call__(field, **kwargs)


class RadioInput(Input):
    """
    Render a single radio button.

    This widget is most commonly used in conjunction with ListWidget or some
    other listing, as singular radio buttons are not very useful.
    """
    input_type = 'radio'

    def __call__(self, field, **kwargs):
        if field.checked:
            kwargs['checked'] = True 
        return super(RadioInput, self).__call__(field, **kwargs)


class FileInput(object):
    """
    Renders a file input chooser field.
    """

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        value = field._value()
        if value:
            kwargs.setdefault('value', value)
        return HTMLString('<input %s>' % html_params(name=field.name, type='file', **kwargs))


class SubmitInput(Input):
    """
    Renders a submit button.

    The field's label is used as the text of the submit button instead of the
    data on the field.
    """
    input_type = 'submit'

    def __call__(self, field, **kwargs): 
        kwargs.setdefault('value', field.label.text)
        return super(SubmitInput, self).__call__(field, **kwargs)


class TextArea(object):
    """
    Renders a multi-line text area.

    `rows` and `cols` ought to be passed as keyword args when rendering.
    """
    def __call__(self, field, **kwargs): 
        kwargs.setdefault('id', field.id)
        return HTMLString('<textarea %s>%s</textarea>' % (html_params(name=field.name, **kwargs), escape(text_type(field._value()))))


class Select(object):
    """
    Renders a select field.

    If `multiple` is True, then the `size` property should be specified on
    rendering to make the field useful.

    The field must provide an `iter_choices()` method which the widget will
    call on rendering; this method must yield tuples of
    `(value, label, selected)`.
    """
    def __init__(self, multiple=False):
        self.multiple = multiple

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        if self.multiple:
            kwargs['multiple'] = True
        html = ['<select %s>' % html_params(name=field.name, **kwargs)]
        for val, label, selected in field.iter_choices():
            html.append(self.render_option(val, label, selected))
        html.append('</select>')
        return HTMLString(''.join(html))

    @classmethod
    def render_option(cls, value, label, selected, **kwargs):
        options = dict(kwargs, value=value)
        if selected:
            options['selected'] = True
        return HTMLString('<option %s>%s</option>' % (html_params(**options), escape(text_type(label))))


class Option(object):
    """
    Renders the individual option from a select field.

    This is just a convenience for various custom rendering situations, and an
    option by itself does not constitute an entire field.
    """
    def __call__(self, field, **kwargs):
        return Select.render_option(field._value(), field.label.text, field.checked, **kwargs)


########NEW FILE########
__FILENAME__ = appengine_config
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""App Engine configuration file.

See:
    https://developers.google.com/appengine/docs/python/tools/appengineconfig
"""

import os
import sys

# Load up our app and all its dependencies. Make the environment sane.
sys.path.insert(0, './lib/')
from dpxdt.server import app


# For debugging SQL queries.
# import logging
# logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)


# When in production use precompiled templates. Sometimes templates break
# in production. To debug templates there, comment this out entirely.
if os.environ.get('SERVER_SOFTWARE', '').startswith('Google App Engine'):
    import jinja2
    app.jinja_env.auto_reload = False
    app.jinja_env.loader = jinja2.ModuleLoader('templates_compiled.zip')


# Install dpxdt.server override hooks.
from dpxdt.server import api
import hooks

api._artifact_created = hooks._artifact_created
api._get_artifact_response = hooks._get_artifact_response


# Don't log when appstats is active.
appstats_DUMP_LEVEL = -1

# SQLAlchemy stacks are really deep.
appstats_MAX_STACK = 20

# Use very shallow local variable reprs to reduce noise.
appstats_MAX_DEPTH = 2


def gae_mini_profiler_should_profile_production():
    from google.appengine.api import users
    return users.is_current_user_admin()


def gae_mini_profiler_should_profile_development():
    return True


# Fix the appstats module's formatting helper function.
import appstats_monkey_patch

########NEW FILE########
__FILENAME__ = appstats_monkey_patch
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Modified version of appstats variable formatting code.

Does not call __nonzero__ or __bool__ in user code, which breaks with
SQLAlchemy's ColumnElement class.

Original code:
  https://code.google.com/p/googleappengine/source/browse/trunk/python/google/appengine/ext/appstats/formatting.py
"""

from google.appengine.ext.appstats.formatting import *


def _format_value(val, limit, level, len=len, repr=repr):
    if level <= 0:
        return '...'

    typ = type(val)

    if typ in EASY_TYPES:
        if typ is float:
            rep = str(val)
        elif typ is long:
            if val >= 10L ** 99:
                return '...L'
            elif val <= -10L ** 98:
                return '-...L'
            else:
                rep = repr(val)
        else:
            rep = repr(val)
        if typ is long and len(rep) > limit:
            n1 = (limit - 3) // 2
            n2 = limit - 3 - n1
            rep = rep[:n1] + '...' + rep[-n2:]
        return rep

    if typ in META_TYPES:
        return val.__name__

    if typ in STRING_TYPES:
        n1 = (limit - 3) // 2
        if n1 < 1:
            n1 = 1
        n2 = limit - 3 - n1
        if n2 < 1:
            n2 = 1
        if len(val) > limit:
            rep = repr(val[:n1] + val[-n2:])
        else:
            rep = repr(val)
            if len(rep) <= limit:
                return rep
        return rep[:n1] + '...' + rep[-n2:]

    if typ is types.MethodType:
        if val.im_self is None:
            fmt = '<unbound method %s of %s>'
        else:
            fmt = '<method %s of %s<>>'
        if val.im_class is not None:
            return fmt % (val.__name__, val.im_class.__name__)
        else:
            return fmt % (val.__name__, '?')

    if typ is types.FunctionType:
        nam = val.__name__
        if nam == '<lambda>':
            return nam
        else:
            return '<function %s>' % val.__name__

    if typ is types.BuiltinFunctionType:
        if val.__self__ is not None:
            return '<built-in method %s of %s<>>' % (val.__name__,
                    type(val.__self__).__name__)
        else:
            return '<built-in function %s>' % val.__name__

    if typ is types.ModuleType:
        if hasattr(val, '__file__'):
            return '<module %s>' % val.__name__
        else:
            return '<built-in module %s>' % val.__name__

    if typ is types.CodeType:
        return '<code object %s>' % val.co_name

    if isinstance(val, ProtocolBuffer.ProtocolMessage):
        buf = [val.__class__.__name__, '<']
        limit -= len(buf[0]) + 2
        append = buf.append
        first = True

        dct = getattr(val, '__dict__', None)
        if dct:
            for (k, v) in sorted(dct.items()):
                if k.startswith('has_') or not k.endswith('_'):
                    continue
                name = k[:-1]

                has_method = getattr(val, 'has_' + name, None)
                if has_method is not None:

                    if type(has_method) is not types.MethodType \
                        or not has_method():
                        continue

                size_method = getattr(val, name + '_size', None)
                if size_method is not None:

                    if type(size_method) is not types.MethodType \
                        or not size_method():
                        continue

                if has_method is None and size_method is None:
                    continue

                if first:
                    first = False
                else:
                    append(', ')
                limit -= len(name) + 2
                if limit <= 0:
                    append('...')
                    break
                append(name)
                append('=')
                rep = _format_value(v, limit, level - 1)
                limit -= len(rep)
                append(rep)
        append('>')
        return ''.join(buf)

    dct = getattr(val, '__dict__', None)
    if type(dct) is dict:
        if typ is INSTANCE_TYPE:
            typ = val.__class__
        typnam = typ.__name__
        priv = '_' + typnam + '__'
        buffer = [typnam, '<']
        limit -= len(buffer[0]) + 2
        if len(dct) <= limit // 4:
            names = sorted(dct)
        else:
            names = list(dct)
        append = buffer.append
        first = True

        if issubclass(typ, BUILTIN_TYPES):

            for builtin_typ in BUILTIN_TYPES:
                if issubclass(typ, builtin_typ):
                    try:
                        val = builtin_typ(val)
                        assert type(val) is builtin_typ
                    except Exception:
                        break
                    else:
                        append(_format_value(val, limit, level - 1))
                        first = False
                        break

        for nam in names:
            if not isinstance(nam, basestring):
                continue
            if first:
                first = False
            else:
                append(', ')
            pnam = nam
            if pnam.startswith(priv):
                pnam = pnam[len(priv) - 2:]
            limit -= len(pnam) + 2
            if limit <= 0:
                append('...')
                break
            append(pnam)
            append('=')
            rep = _format_value(dct[nam], limit, level - 1)
            limit -= len(rep)
            append(rep)
        append('>')
        return ''.join(buffer)

    how = CONTAINER_TYPES.get(typ)
    if how:
        (head, tail) = how
        buffer = [head]
        append = buffer.append
        limit -= 2
        series = val
        isdict = typ is dict
        # This explodes with SQLAlchemy's ColumnElement class.
        # if isdict and len(val) <= limit // 4:
        #     series = sorted(val)
        try:
            for elem in series:
                if limit <= 0:
                    append('...')
                    break
                rep = _format_value(elem, limit, level - 1)
                limit -= len(rep) + 2
                append(rep)
                if isdict:
                    rep = _format_value(val[elem], limit, level - 1)
                    limit -= len(rep)
                    append(':')
                    append(rep)
                append(', ')
            if buffer[-1] == ', ':
                if tail == ')' and len(val) == 1:
                    buffer[-1] = ',)'
                else:
                    buffer[-1] = tail
            else:
                append(tail)
            return ''.join(buffer)
        except (RuntimeError, KeyError):

            return head + tail \
                + ' (Container modified during iteration)'

    if issubclass(typ, BUILTIN_TYPES):

        for builtin_typ in BUILTIN_TYPES:
            if issubclass(typ, builtin_typ):
                try:
                    val = builtin_typ(val)
                    assert type(val) is builtin_typ
                except Exception:
                    break
                else:
                    typnam = typ.__name__
                    limit -= len(typnam) + 2
                    return '%s<%s>' % (typnam, _format_value(val,
                            limit, level - 1))

    if message is not None and isinstance(val, message.Message):
        buffer = [typ.__name__, '<']
        limit -= len(buffer[0]) + 2
        append = buffer.append
        first = True
        fields = val.ListFields()

        for (f, v) in fields:
            if first:
                first = False
            else:
                append(', ')
            name = f.name
            limit -= len(name) + 2
            if limit <= 0:
                append('...')
                break
            append(name)
            append('=')
            if f.label == f.LABEL_REPEATED:
                limit -= 2
                append('[')
                first_sub = True
                for item in v:
                    if first_sub:
                        first_sub = False
                    else:
                        limit -= 2
                        append(', ')
                    if limit <= 0:
                        append('...')
                        break
                    rep = _format_value(item, limit, level - 1)
                    limit -= len(rep)
                    append(rep)
                append(']')
            else:
                rep = _format_value(v, limit, level - 1)
                limit -= len(rep)
                append(rep)
        append('>')
        return ''.join(buffer)

    return typ.__name__ + '<>'


import google.appengine.ext.appstats.formatting
google.appengine.ext.appstats.formatting._format_value = _format_value

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration for local development."""

from secrets import *

SQLALCHEMY_DATABASE_URI = (
    'mysql+gaerdbms:///test?instance=foo:bar')

GOOGLE_OAUTH2_EMAIL_ADDRESS = '918724168220-nqq27o7so1p7stukds23oo2vof5gkfmh@developer.gserviceaccount.com'
GOOGLE_OAUTH2_REDIRECT_PATH = '/oauth2callback'
GOOGLE_OAUTH2_REDIRECT_URI = 'http://localhost:5000' + GOOGLE_OAUTH2_REDIRECT_PATH
GOOGLE_OAUTH2_CLIENT_ID = '918724168220-nqq27o7so1p7stukds23oo2vof5gkfmh.apps.googleusercontent.com'
GOOGLE_OAUTH2_CLIENT_SECRET = 'EhiCP-PuQYN0OsWGAELTUHyl'

GOOGLE_CLOUD_STORAGE_BUCKET = 'fake-bucket-name-here/artifacts'

CACHE_TYPE = 'memcached'
CACHE_DEFAULT_TIMEOUT = 600

SESSION_COOKIE_DOMAIN = None

MAIL_DEFAULT_SENDER = 'Depicted <nobody@localhost>'
MAIL_SUPPRESS_SEND = False
MAIL_USE_APPENGINE = True

########NEW FILE########
__FILENAME__ = hooks
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Hook overrides for the App Engine environment."""

import datetime
import logging

from google.appengine.api import files
from google.appengine.ext import blobstore

# Local libraries
import flask

# Local modules
from dpxdt.server import app
from dpxdt.server import models
import config


def _artifact_created(artifact):
    """Override for saving an artifact to google storage."""
    filename = '/gs/%s/sha1-%s' % (
        config.GOOGLE_CLOUD_STORAGE_BUCKET, artifact.id)

    # TODO: Move to the new cloudstorage module once it works with
    # dev_appserver and the BLOB_KEY_HEADER.
    writable_filename = files.gs.create(
        filename, mime_type=artifact.content_type)

    with files.open(writable_filename, 'a') as handle:
        handle.write(artifact.data)

    files.finalize(writable_filename)

    artifact.data = None
    artifact.alternate = filename
    logging.debug('Saved file=%r', artifact.alternate)


def _get_artifact_response(artifact):
    """Override for serving an artifact from Google Cloud Storage."""
    if artifact.alternate:
        blob_key = blobstore.create_gs_key(artifact.alternate)
        logging.debug('Serving file=%r, key=%r', artifact.alternate, blob_key)
        response = flask.Response(
            headers={blobstore.BLOB_KEY_HEADER: str(blob_key)},
            mimetype=artifact.content_type)
    else:
        response = flask.Response(
            artifact.data,
            mimetype=artifact.content_type)

    response.cache_control.public = True
    response.cache_control.max_age = 8640000
    response.set_etag(artifact.id)
    return response

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Entry point for the App Engine environment."""

# Local Libraries
import gae_mini_profiler.profiler
import gae_mini_profiler.templatetags

# Local modules
from dpxdt.server import app


@app.route('/_ah/warmup')
def appengine_warmup():
    return 'OK'


@app.context_processor
def gae_mini_profiler_context():
    return dict(
        profiler_includes=gae_mini_profiler.templatetags.profiler_includes)


application = gae_mini_profiler.profiler.ProfilerWSGIMiddleware(app)

########NEW FILE########
__FILENAME__ = capture_worker
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Background worker that screenshots URLs, possibly from a queue."""

import Queue
import json
import os
import shutil
import subprocess
import sys
import threading
import tempfile
import time
import urllib2

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt import constants
from dpxdt.client import process_worker
from dpxdt.client import queue_worker
from dpxdt.client import release_worker
from dpxdt.client import workers


gflags.DEFINE_integer(
    'capture_threads', 5, 'Number of website screenshot threads to run')

gflags.DEFINE_integer(
    'capture_task_max_attempts', 3,
    'Maximum number of attempts for processing a capture task.')

gflags.DEFINE_integer(
    'capture_wait_seconds', 3,
    'Wait this many seconds between repeated invocations of capture '
    'subprocesses. Can be used to spread out load on the server.')

gflags.DEFINE_string(
    'phantomjs_binary', None, 'Path to the phantomjs binary')

gflags.DEFINE_string(
    'phantomjs_script', None,
    'Path to the script that drives the phantomjs process')

gflags.DEFINE_integer(
    'phantomjs_timeout', 120,
    'Seconds until giving up on a phantomjs sub-process and trying again.')



class CaptureFailedError(queue_worker.GiveUpAfterAttemptsError):
    """Capturing a webpage screenshot failed for some reason."""


class CaptureWorkflow(process_worker.ProcessWorkflow):
    """Workflow for capturing a website screenshot using PhantomJs."""

    def __init__(self, log_path, config_path, output_path):
        """Initializer.

        Args:
            log_path: Where to write the verbose logging output.
            config_path: Path to the screenshot config file to pass
                to PhantomJs.
            output_path: Where the output screenshot should be written.
        """
        process_worker.ProcessWorkflow.__init__(
            self, log_path, timeout_seconds=FLAGS.phantomjs_timeout)
        self.config_path = config_path
        self.output_path = output_path

    def get_args(self):
        return [
            FLAGS.phantomjs_binary,
            '--disk-cache=false',
            '--debug=true',
            '--ignore-ssl-errors=true',
            FLAGS.phantomjs_script,
            self.config_path,
            self.output_path,
        ]


class DoCaptureQueueWorkflow(workers.WorkflowItem):
    """Runs a webpage screenshot process from queue parameters.

    Args:
        build_id: ID of the build.
        release_name: Name of the release.
        release_number: Number of the release candidate.
        run_name: Run to run perceptual diff for.
        url: URL of the content to screenshot.
        config_sha1sum: Content hash of the config for the new screenshot.
        baseline: Optional. When specified and True, this capture is for
            the reference baseline of the specified run, not the new capture.
        heartbeat: Function to call with progress status.

    Raises:
        CaptureFailedError if the screenshot process failed.
    """

    def run(self, build_id=None, release_name=None, release_number=None,
            run_name=None, url=None, config_sha1sum=None, baseline=None,
            heartbeat=None):
        output_path = tempfile.mkdtemp()
        try:
            image_path = os.path.join(output_path, 'capture.png')
            log_path = os.path.join(output_path, 'log.txt')
            config_path = os.path.join(output_path, 'config.json')
            capture_failed = True
            failure_reason = None

            yield heartbeat('Fetching webpage capture config')
            yield release_worker.DownloadArtifactWorkflow(
                build_id, config_sha1sum, result_path=config_path)

            yield heartbeat('Running webpage capture process')
            try:
                returncode = yield CaptureWorkflow(
                    log_path, config_path, image_path)
            except (process_worker.TimeoutError, OSError), e:
                failure_reason = str(e)
            else:
                capture_failed = returncode != 0
                failure_reason = 'returncode=%s' % returncode

            # Don't upload bad captures, but always upload the error log.
            if capture_failed:
                image_path = None

            yield heartbeat('Reporting capture status to server')
            yield release_worker.ReportRunWorkflow(
                build_id, release_name, release_number, run_name,
                image_path=image_path, log_path=log_path, baseline=baseline,
                run_failed=capture_failed)

            if capture_failed:
                raise CaptureFailedError(
                    FLAGS.capture_task_max_attempts,
                    failure_reason)
        finally:
            shutil.rmtree(output_path, True)


def register(coordinator):
    """Registers this module as a worker with the given coordinator."""
    assert FLAGS.phantomjs_binary
    assert FLAGS.phantomjs_script
    assert FLAGS.capture_threads > 0
    assert FLAGS.queue_server_prefix

    item = queue_worker.RemoteQueueWorkflow(
        constants.CAPTURE_QUEUE_NAME,
        DoCaptureQueueWorkflow,
        max_tasks=FLAGS.capture_threads,
        wait_seconds=FLAGS.capture_wait_seconds)
    item.root = True
    coordinator.input_queue.put(item)

########NEW FILE########
__FILENAME__ = fetch_worker
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workers for driving screen captures, perceptual diffs, and related work."""

import Queue
import base64
import json
import logging
import shutil
import socket
import ssl
import time
import urllib
import urllib2

# Local Libraries
import gflags
FLAGS = gflags.FLAGS
import poster.encode
import poster.streaminghttp
poster.streaminghttp.register_openers()

# Local modules
from dpxdt.client import workers


gflags.DEFINE_float(
    'fetch_frequency', 1.0,
    'Maximum number of fetches to make per second per thread.')

gflags.DEFINE_integer(
    'fetch_threads', 1, 'Number of fetch threads to run')


class FetchItem(workers.WorkItem):
    """Work item that is handled by fetching a URL."""

    def __init__(self, url, post=None, timeout_seconds=30, result_path=None,
                 username=None, password=None):
        """Initializer.

        Args:
            url: URL to fetch.
            post: Optional. Dictionary of post parameters to include in the
                request, with keys and values coerced to strings. If any
                values are open file handles, the post data will be formatted
                as multipart/form-data.
            timeout_seconds: Optional. How long until the fetch should timeout.
            result_path: When supplied, the output of the fetch should be
                streamed to a file on disk with the given path. Use this
                to prevent many fetches from causing memory problems.
            username: Optional. Username to use for the request, for
                HTTP basic authentication.
            password: Optional. Password to use for the request, for
                HTTP basic authentication.
        """
        workers.WorkItem.__init__(self)
        self.url = url
        self.post = post
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.result_path = result_path
        self.status_code = None
        self.data = None
        self.headers = None
        self._data_json = None

    def _get_dict_for_repr(self):
        result = self.__dict__.copy()
        if result.get('password'):
            result['password'] = 'ELIDED'
        return result

    @property
    def json(self):
        """Returns de-JSONed data or None if it's a different content type."""
        if self._data_json:
            return self._data_json

        if not self.data or self.headers.gettype() != 'application/json':
            return None

        self._data_json = json.loads(self.data)
        return self._data_json


class FetchThread(workers.WorkerThread):
    """Worker thread for fetching URLs."""

    def handle_item(self, item):
        start_time = time.time()

        if item.post is not None:
            adjusted_data = {}
            use_form_data = False

            for key, value in item.post.iteritems():
                if value is None:
                    continue
                if isinstance(value, file):
                    use_form_data = True
                adjusted_data[key] = value

            if use_form_data:
                datagen, headers = poster.encode.multipart_encode(
                    adjusted_data)
                request = urllib2.Request(item.url, datagen, headers)
            else:
                request = urllib2.Request(
                    item.url, urllib.urlencode(adjusted_data))
        else:
            request = urllib2.Request(item.url)

        if item.username:
            credentials = base64.b64encode(
                '%s:%s' % (item.username, item.password))
            request.add_header('Authorization', 'Basic %s' % credentials)

        try:
            try:
                conn = urllib2.urlopen(request, timeout=item.timeout_seconds)
            except urllib2.HTTPError, e:
                conn = e
            except (urllib2.URLError, ssl.SSLError), e:
                # TODO: Make this status more clear
                item.status_code = 400
                return item

            try:
                item.status_code = conn.getcode()
                item.headers = conn.info()
                if item.result_path:
                    with open(item.result_path, 'wb') as result_file:
                        shutil.copyfileobj(conn, result_file)
                else:
                    item.data = conn.read()
            except socket.timeout, e:
                # TODO: Make this status more clear
                item.status_code = 400
                return item
            finally:
                conn.close()

            return item
        finally:
            end_time = time.time()
            wait_duration = (1.0 / FLAGS.fetch_frequency) - (
                end_time - start_time)
            if wait_duration > 0:
                logging.debug('Rate limiting URL fetch for %f seconds',
                              wait_duration)
                time.sleep(wait_duration)


def register(coordinator):
    """Registers this module as a worker with the given coordinator."""
    fetch_queue = Queue.Queue()
    coordinator.register(FetchItem, fetch_queue)
    for i in xrange(FLAGS.fetch_threads):
        coordinator.worker_threads.append(
            FetchThread(fetch_queue, coordinator.input_queue))

########NEW FILE########
__FILENAME__ = pdiff_worker
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Background worker that does perceptual diffs, possibly from a queue."""

import Queue
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib2
import re

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt import constants
from dpxdt.client import process_worker
from dpxdt.client import queue_worker
from dpxdt.client import release_worker
from dpxdt.client import workers


gflags.DEFINE_integer(
    'pdiff_task_max_attempts', 3,
    'Maximum number of attempts for processing a pdiff task.')

gflags.DEFINE_integer(
    'pdiff_wait_seconds', 3,
    'Wait this many seconds between repeated invocations of pdiff '
    'subprocesses. Can be used to spread out load on the server.')

gflags.DEFINE_string(
    'pdiff_compare_binary', 'compare',
    'Path to the compare binary used for generating perceptual diffs.')

gflags.DEFINE_string(
    'pdiff_composite_binary', 'composite',
    'Path to the composite binary used for resizing images.')

gflags.DEFINE_integer(
    'pdiff_threads', 1, 'Number of perceptual diff threads to run')

gflags.DEFINE_integer(
    'pdiff_timeout', 60,
    'Seconds until we should give up on a pdiff sub-process and try again.')

DIFF_REGEX = re.compile(".*all:.*\(([0-9e\-\.]*)\).*")


class PdiffFailedError(queue_worker.GiveUpAfterAttemptsError):
    """Running a perceptual diff failed for some reason."""


class ResizeWorkflow(process_worker.ProcessWorkflow):
    """Workflow for making images to be diffed the same size."""

    def __init__(self, log_path, ref_path, run_path, resized_ref_path):
        """Initializer.

        Args:
            log_path: Where to write the verbose logging output.
            ref_path: Path to reference screenshot to diff.
            run_path: Path to the most recent run screenshot to diff.
            resized_ref_path: Where the resized ref image should be written.
        """
        process_worker.ProcessWorkflow.__init__(
            self, log_path, timeout_seconds=FLAGS.pdiff_timeout)
        self.ref_path = ref_path
        self.run_path = run_path
        self.resized_ref_path = resized_ref_path

    def get_args(self):
        return [
            FLAGS.pdiff_composite_binary,
            '-compose',
            'src',
            '-gravity',
            'NorthWest',
            self.ref_path,
            self.run_path,
            self.resized_ref_path,
        ]


class PdiffWorkflow(process_worker.ProcessWorkflow):
    """Workflow for doing perceptual diffs using pdiff."""

    def __init__(self, log_path, ref_path, run_path, output_path):
        """Initializer.

        Args:
            log_path: Where to write the verbose logging output.
            ref_path: Path to reference screenshot to diff.
            run_path: Path to the most recent run screenshot to diff.
            output_path: Where the diff image should be written, if any.
        """
        process_worker.ProcessWorkflow.__init__(
            self, log_path, timeout_seconds=FLAGS.pdiff_timeout)
        self.ref_path = ref_path
        self.run_path = run_path
        self.output_path = output_path

    def get_args(self):
        # Method from http://www.imagemagick.org/Usage/compare/
        return [
            FLAGS.pdiff_compare_binary,
            '-verbose',
            '-metric',
            'RMSE',
            '-highlight-color',
            'Red',
            '-compose',
            'Src',
            self.ref_path,
            self.run_path,
            self.output_path,
        ]


class DoPdiffQueueWorkflow(workers.WorkflowItem):
    """Runs the perceptual diff from queue parameters.

    Args:
        build_id: ID of the build.
        release_name: Name of the release.
        release_number: Number of the release candidate.
        run_name: Run to run perceptual diff for.
        reference_sha1sum: Content hash of the previously good image.
        run_sha1sum: Content hash of the new image.
        heartbeat: Function to call with progress status.

    Raises:
        PdiffFailedError if the perceptual diff process failed.
    """

    def run(self, build_id=None, release_name=None, release_number=None,
            run_name=None, reference_sha1sum=None, run_sha1sum=None,
            heartbeat=None):
        output_path = tempfile.mkdtemp()
        try:
            ref_path = os.path.join(output_path, 'ref')
            ref_resized_path = os.path.join(output_path, 'ref_resized')
            run_path = os.path.join(output_path, 'run')
            diff_path = os.path.join(output_path, 'diff.png')
            log_path = os.path.join(output_path, 'log.txt')

            yield heartbeat('Fetching reference and run images')
            yield [
                release_worker.DownloadArtifactWorkflow(
                    build_id, reference_sha1sum, result_path=ref_path),
                release_worker.DownloadArtifactWorkflow(
                    build_id, run_sha1sum, result_path=run_path)
            ]

            max_attempts = FLAGS.pdiff_task_max_attempts

            yield heartbeat('Resizing reference image')
            returncode = yield ResizeWorkflow(
                log_path, ref_path, run_path, ref_resized_path)
            if returncode != 0:
                raise PdiffFailedError(
                    max_attempts,
                    'Could not resize reference image to size of new image')

            yield heartbeat('Running perceptual diff process')
            returncode = yield PdiffWorkflow(
                log_path, ref_resized_path, run_path, diff_path)

            # ImageMagick returns 1 if the images are different and 0 if
            # they are the same, so the return code is a bad judge of
            # successfully running the diff command. Instead we need to check
            # the output text.
            diff_failed = True

            # Check for a successful run or a known failure.
            distortion = None
            if os.path.isfile(log_path):
                log_data = open(log_path).read()
                if 'all: 0 (0)' in log_data:
                    diff_path = None
                    diff_failed = False
                elif 'image widths or heights differ' in log_data:
                    # Give up immediately
                    max_attempts = 1
                else:
                    # Try to find the image magic normalized root square
                    # mean and grab the first one.
                    r = DIFF_REGEX.findall(log_data)
                    if len(r) > 0:
                        diff_failed = False
                        distortion = r[0]

            yield heartbeat('Reporting diff result to server')
            yield release_worker.ReportPdiffWorkflow(
                build_id, release_name, release_number, run_name,
                diff_path, log_path, diff_failed, distortion)

            if diff_failed:
                raise PdiffFailedError(
                    max_attempts,
                    'Comparison failed. returncode=%r' % returncode)
        finally:
            shutil.rmtree(output_path, True)


def register(coordinator):
    """Registers this module as a worker with the given coordinator."""
    assert FLAGS.pdiff_threads > 0
    assert FLAGS.queue_server_prefix

    item = queue_worker.RemoteQueueWorkflow(
        constants.PDIFF_QUEUE_NAME,
        DoPdiffQueueWorkflow,
        max_tasks=FLAGS.pdiff_threads,
        wait_seconds=FLAGS.pdiff_wait_seconds)
    item.root = True
    coordinator.input_queue.put(item)

########NEW FILE########
__FILENAME__ = process_worker
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workers for driving screen captures, perceptual diffs, and related work."""

import Queue
import logging
import subprocess
import time

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import timer_worker
from dpxdt.client import workers


class Error(Exception):
    """Base class for exceptions in this module."""

class TimeoutError(Exception):
    """Subprocess has taken too long to complete and was terminated."""


class ProcessWorkflow(workers.WorkflowItem):
    """Workflow that runs a subprocess.

    Args:
        log_path: Path to where output from this subprocess should be written.
        timeout_seconds: How long before the process should be force killed.

    Returns:
        The return code of the subprocess.
    """

    def get_args(self):
        """Return the arguments for running the subprocess."""
        raise NotImplemented

    def run(self, log_path, timeout_seconds=30):
        start_time = time.time()
        with open(log_path, 'a') as output_file:
            args = self.get_args()
            logging.info('item=%r Running subprocess: %r', self, args)
            try:
                process = subprocess.Popen(
                    args,
                    stderr=subprocess.STDOUT,
                    stdout=output_file,
                    close_fds=True)
            except:
                logging.error('item=%r Failed to run subprocess: %r',
                              self, args)
                raise

            while True:
                logging.info('item=%r Polling pid=%r', self, process.pid)
                # NOTE: Use undocumented polling method to work around a
                # bug in subprocess for handling defunct zombie processes:
                # http://bugs.python.org/issue2475
                process._internal_poll(_deadstate=127)
                if process.returncode is not None:
                    logging.info(
                        'item=%r Subprocess finished pid=%r, returncode=%r',
                        self, process.pid, process.returncode)
                    raise workers.Return(process.returncode)

                now = time.time()
                run_time = now - start_time
                if run_time > timeout_seconds:
                    logging.info('item=%r Subprocess timed out pid=%r',
                                 self, process.pid)
                    process.kill()
                    raise TimeoutError(
                        'Sent SIGKILL to item=%r, pid=%s, run_time=%s' %
                        (self, process.pid, run_time))

                yield timer_worker.TimerItem(FLAGS.polltime)

########NEW FILE########
__FILENAME__ = queue_worker
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workers that consumer a release server's work queue."""

import logging

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import fetch_worker
from dpxdt.client import timer_worker
from dpxdt.client import workers


gflags.DEFINE_string(
    'queue_server_prefix', None,
    'URL prefix of where the work queue server is located, such as '
    '"https://www.example.com/api/work_queue". This should use HTTPS if '
    'possible, since API requests send credentials using HTTP basic auth.')

gflags.DEFINE_integer(
    'queue_idle_poll_seconds', 60,
    'How often to poll the work queue for new tasks when the worker is '
    'currently not processing any tasks.')

gflags.DEFINE_integer(
    'queue_busy_poll_seconds', 1,
    'How often to poll tasks running locally to see if they have completed '
    'and then go back to the server to look for more work.')


class Error(Exception):
    """Base-class for exceptions in this module."""


class GiveUpAfterAttemptsError(Error):
    """Exception indicates the task should give up after N attempts."""

    def __init__(self, max_attempts, *args, **kwargs):
        """Initializer.

        Args:
            max_attempts: Maximum number of attempts to make for this task,
                inclusive. So 2 means try two times and then retire the task.
            *args, **kwargs: Optional Exception arguments.
        """
        Exception.__init__(self, *args, **kwargs)
        self.max_attempts = max_attempts


class HeartbeatError(Error):
    """Reporting the status of a task in progress failed for some reason."""


class HeartbeatWorkflow(workers.WorkflowItem):
    """Reports the status of a RemoteQueueWorkflow to the API server.

    Args:
        queue_url: Base URL of the work queue.
        task_id: ID of the task to update the heartbeat status message for.
        message: Heartbeat status message to report.
        index: Index for the heartbeat message. Should be at least one
            higher than the last heartbeat message.
    """

    def run(self, queue_url, task_id, message, index):
        call = yield fetch_worker.FetchItem(
            queue_url + '/heartbeat',
            post={
                'task_id': task_id,
                'message': message,
                'index': index,
            },
            username=FLAGS.release_client_id,
            password=FLAGS.release_client_secret)

        if call.json and call.json.get('error'):
            raise HeartbeatError(call.json.get('error'))

        if not call.json or not call.json.get('success'):
            raise HeartbeatError('Bad response: %r' % call)


class DoTaskWorkflow(workers.WorkflowItem):
    """Runs a local workflow for a task and marks it done in the remote queue.

    Args:
        queue_url: Base URL of the work queue.
        local_queue_workflow: WorkflowItem sub-class to create using parameters
            from the remote work payload that will execute the task.
        task: JSON payload of the task.
        wait_seconds: Wait this many seconds before starting work.
            Defaults to zero.
    """

    fire_and_forget = True

    def run(self, queue_url, local_queue_workflow, task, wait_seconds=0):
        logging.info('Starting work item from queue_url=%r, '
                     'task=%r, workflow=%r, wait_seconds=%r',
                     queue_url, task, local_queue_workflow, wait_seconds)

        if wait_seconds > 0:
            yield timer_worker.TimerItem(wait_seconds)

        # Define a heartbeat closure that will return a workflow for
        # reporting status. This will auto-increment the index on each
        # call, so only the latest update will be saved.
        index = [0]
        task_id = task['task_id']
        def heartbeat(message):
            next_index = index[0]
            index[0] = next_index + 1
            return HeartbeatWorkflow(
                queue_url, task_id, message, next_index)

        payload = task['payload']
        payload.update(heartbeat=heartbeat)

        error = False

        try:
            yield local_queue_workflow(**payload)
        except Exception, e:
            logging.exception('Exception while processing work from '
                              'queue_url=%r, task=%r', queue_url, task)
            yield heartbeat('%s: %s' % (e.__class__.__name__, str(e)))

            if (isinstance(e, GiveUpAfterAttemptsError) and
                    task['lease_attempts'] >= e.max_attempts):
                logging.warning(
                    'Hit max attempts on task=%r, marking task as error',
                    task)
                error = True
            else:
                # The task has legimiately failed. Do not mark the task as
                # finished. Let it retry in the queue again.
                return

        finish_params = {'task_id': task_id}
        if error:
            finish_params['error'] = '1'

        try:
            finish_item = yield fetch_worker.FetchItem(
                queue_url + '/finish',
                post=finish_params,
                username=FLAGS.release_client_id,
                password=FLAGS.release_client_secret)
        except Exception, e:
            logging.error('Could not finish work with '
                          'queue_url=%r, task=%r. %s: %s',
                          queue_url, task, e.__class__.__name__, e)
        else:
            if finish_item.json and finish_item.json.get('error'):
                logging.error('Could not finish work with '
                              'queue_url=%r, task=%r. %s',
                              queue_url, finish_item.json['error'], task)
            else:
                logging.info('Finished work item with queue_url=%r, '
                             'task_id=%r', queue_url, task_id)


class RemoteQueueWorkflow(workers.WorkflowItem):
    """Fetches tasks from a remote queue periodically, runs them locally.

    Args:
        queue_name: Name of the queue to fetch from.
        local_queue_workflow: WorkflowItem sub-class to create using parameters
            from the remote work payload that will execute the task.
        max_tasks: Maximum number of tasks to have in flight at any time.
            Defaults to 1.
        wait_seconds: How many seconds should be between tasks starting to
            process locally. Defaults to 0. Can be used to spread out
            the load a new set of tasks has on the server.
    """

    def run(self, queue_name, local_queue_workflow,
            max_tasks=1, wait_seconds=0):
        queue_url = '%s/%s' % (FLAGS.queue_server_prefix, queue_name)
        outstanding = []

        while True:
            next_count = max_tasks - len(outstanding)
            next_tasks = []

            if next_count > 0:
                logging.info(
                    'Fetching %d tasks from queue_url=%r for workflow=%r',
                    next_count, queue_url, local_queue_workflow)
                try:
                    next_item = yield fetch_worker.FetchItem(
                        queue_url + '/lease',
                        post={'count': next_count},
                        username=FLAGS.release_client_id,
                        password=FLAGS.release_client_secret)
                except Exception, e:
                    logging.error(
                        'Could not fetch work from queue_url=%r. %s: %s',
                        queue_url, e.__class__.__name__, e)
                else:
                    if next_item.json:
                        if next_item.json.get('error'):
                            logging.error(
                                'Could not fetch work from queue_url=%r. %s',
                                queue_url, next_item.json['error'])
                        elif next_item.json['tasks']:
                            next_tasks = next_item.json['tasks']

            for index, task in enumerate(next_tasks):
                item = yield DoTaskWorkflow(
                    queue_url, local_queue_workflow, task,
                    wait_seconds=index * wait_seconds)
                outstanding.append(item)

            # Poll for new tasks frequently when we're currently handling
            # task load. Poll infrequently when there hasn't been anything
            # to do recently.
            poll_time = FLAGS.queue_idle_poll_seconds
            if outstanding:
                poll_time = FLAGS.queue_busy_poll_seconds

            yield timer_worker.TimerItem(poll_time)

            outstanding[:] = [x for x in outstanding if not x.done]
            logging.debug('%d items for %r still outstanding: %r',
                          len(outstanding), local_queue_workflow, outstanding)

########NEW FILE########
__FILENAME__ = release_worker
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Background worker that uploads new release candidates."""

import hashlib
import os

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import fetch_worker
from dpxdt.client import workers


gflags.DEFINE_string(
    'release_server_prefix', None,
    'URL prefix of where the release server is located, such as '
    '"https://www.example.com/here/is/my/api". This should use HTTPS if '
    'possible, since API requests send credentials using HTTP basic auth.')

gflags.DEFINE_string(
    'release_client_id', None,
    'Client ID of the API key to use for requests to the release server.')

gflags.DEFINE_string(
    'release_client_secret', None,
    'Client secret of the API key to use for requests to the release server.')


class Error(Exception):
    """Base-class for exceptions in this module."""

class CreateReleaseError(Error):
    """Creating a new release failed for some reason."""

class UploadFileError(Error):
    """Uploading a file failed for some reason."""

class FindRunError(Error):
    """Finding a run failed for some reason."""

class RequestRunError(Error):
    """Requesting a run failed for some reason."""

class ReportRunError(Error):
    """Reporting a run failed for some reason."""

class ReportPdiffError(Error):
    """Reporting a pdiff failed for some reason."""

class RunsDoneError(Error):
    """Marking that all runs are done failed for some reason."""

class DownloadArtifactError(Error):
    """Downloading an artifact failed for some reason."""


class StreamingSha1File(file):
    """File sub-class that sha1 hashes the data as it's read."""

    def __init__(self, *args, **kwargs):
        """Replacement for open()."""
        file.__init__(self, *args, **kwargs)
        self.sha1 = hashlib.sha1()

    def read(self, *args):
        data = file.read(self, *args)
        self.sha1.update(data)
        return data

    def close(self):
        file.close(self)

    def hexdigest(self):
        return self.sha1.hexdigest()


class CreateReleaseWorkflow(workers.WorkflowItem):
    """Creates a new release candidate.

    Args:
        build_id: ID of the build.
        release_name: Name of the release candidate.
        url: Landing URL of the new release.

    Returns:
        The newly created release_number.

    Raises:
        CreateReleaseError if the release could not be created.
    """

    def run(self, build_id, release_name, url):
        call = yield fetch_worker.FetchItem(
            FLAGS.release_server_prefix + '/create_release',
            post={
                'build_id': build_id,
                'release_name': release_name,
                'url': url,
            },
            username=FLAGS.release_client_id,
            password=FLAGS.release_client_secret)

        if call.json and call.json.get('error'):
            raise CreateReleaseError(call.json.get('error'))

        if not call.json or not call.json.get('release_number'):
            raise CreateReleaseError('Bad response: %r' % call)

        raise workers.Return(call.json['release_number'])


class UploadFileWorkflow(workers.WorkflowItem):
    """Uploads a file for a build.

    Args:
        build_id: ID of the build to upload a file for.
        file_path: Path to the file to upload.

    Returns:
        sha1 sum of the file's contents or None if the file could not
        be found.

    Raises:
        UploadFileError if the file could not be uploaded.
    """

    def run(self, build_id, file_path):
        try:
            handle = StreamingSha1File(file_path, 'rb')
            upload = yield fetch_worker.FetchItem(
                FLAGS.release_server_prefix + '/upload',
                post={'build_id': build_id, 'file': handle},
                timeout_seconds=120,
                username=FLAGS.release_client_id,
                password=FLAGS.release_client_secret)

            if upload.json and upload.json.get('error'):
                raise UploadFileError(upload.json.get('error'))

            sha1sum = handle.hexdigest()
            if not upload.json or upload.json.get('sha1sum') != sha1sum:
                raise UploadFileError('Bad response: %r' % upload)

            raise workers.Return(sha1sum)

        except IOError:
            raise workers.Return(None)


class FindRunWorkflow(workers.WorkflowItem):
    """Finds the last good run for a release.

    Args:
        build_id: ID of the build.
        run_name: Name of the run being uploaded.

    Returns:
        JSON dictionary representing the run that was found, with the keys:
        build_id, release_name, release_number, run_name, url, image, log,
        config.

    Raises:
        FindRunError if a run could not be found.
    """

    def run(self, build_id, run_name):
        call = yield fetch_worker.FetchItem(
            FLAGS.release_server_prefix + '/find_run',
            post={
                'build_id': build_id,
                'run_name': run_name,
            },
            username=FLAGS.release_client_id,
            password=FLAGS.release_client_secret)

        if call.json and call.json.get('error'):
            raise FindRunError(call.json.get('error'))

        if not call.json:
            raise FindRunError('Bad response: %r' % call)

        raise workers.Return(call.json)


class RequestRunWorkflow(workers.WorkflowItem):
    """Requests the API server to do a test run and capture the results.

    Args:
        build_id: ID of the build.
        release_name: Name of the release.
        release_number: Number of the release candidate.
        run_name: Name of the run being requested.
        url: URL to fetch for the run.
        config_data: The JSON data that is the config for this run.
        ref_url: Optional. URL of the baseline to fetch for the run.
        ref_config_data: Optional. The JSON data that is the config for the
            baseline of this run.

    Raises:
        RequestRunError if the run could not be requested.
    """

    def run(self, build_id, release_name, release_number, run_name,
            url=None, config_data=None, ref_url=None, ref_config_data=None):
        post = {
            'build_id': build_id,
            'release_name': release_name,
            'release_number': release_number,
            'run_name': run_name,
            'url': url,
            'config': config_data,
        }
        if ref_url and ref_config_data:
            post.update(
                ref_url=ref_url,
                ref_config=ref_config_data)

        call = yield fetch_worker.FetchItem(
            FLAGS.release_server_prefix + '/request_run',
            post=post,
            username=FLAGS.release_client_id,
            password=FLAGS.release_client_secret)

        if call.json and call.json.get('error'):
            raise RequestRunError(call.json.get('error'))

        if not call.json or not call.json.get('success'):
            raise RequestRunError('Bad response: %r' % call)


class ReportRunWorkflow(workers.WorkflowItem):
    """Reports a run as finished.

    Args:
        build_id: ID of the build.
        release_name: Name of the release.
        release_number: Number of the release candidate.
        run_name: Name of the run being uploaded.
        log_path: Optional. Path to the screenshot log to upload.
        image_path: Optional. Path to the screenshot to upload.
        url: Optional. URL that was fetched for the run.
        config_path: Optional. Path to the config to upload.
        ref_url: Optional. Previously fetched URL this is being compared to.
        ref_image: Optional. Asset ID of the image to compare to.
        ref_log: Optional. Asset ID of the reference image's log.
        ref_config: Optional. Asset ID of the reference image's config.
        baseline: Optional. When specified and True, the log_path, url,
            and image_path are for the reference baseline of the specified
            run, not the new capture. If this is True, the ref_* parameters
            must not be provided.
        run_failed: Optional. When specified and True it means that this run
            has failed for some reason. The run may be tried again in the
            future but this will cause this run to immediately show up as
            failing. When not specified or False the run will be assumed to
            have been successful.

    Raises:
        ReportRunError if the run could not be reported.
    """

    def run(self, build_id, release_name, release_number, run_name,
            image_path=None, log_path=None, url=None, config_path=None,
            ref_url=None, ref_image=None, ref_log=None, ref_config=None,
            baseline=None, run_failed=False):
        if baseline and (ref_url or ref_image or ref_log or ref_config):
            raise ReportRunError(
                'Cannot specify "baseline" along with any "ref_*" arguments.')

        upload_jobs = [
            UploadFileWorkflow(build_id, log_path),
        ]
        if image_path:
            image_index = len(upload_jobs)
            upload_jobs.append(UploadFileWorkflow(build_id, image_path))

        if config_path:
            config_index = len(upload_jobs)
            upload_jobs.append(UploadFileWorkflow(build_id, config_path))

        results = yield upload_jobs
        log_id = results[0]
        image_id = None
        config_id = None
        if image_path:
            image_id = results[image_index]
        if config_path:
            config_id = results[config_index]

        post = {
            'build_id': build_id,
            'release_name': release_name,
            'release_number': release_number,
            'run_name': run_name,
        }

        if baseline:
            ref_url = url
            ref_log = log_id
            ref_image = image_id
            ref_config = config_id
            url = None
            log_id = None
            image_id = None
            config_id = None

        if url:
            post.update(url=url)
        if image_id:
            post.update(image=image_id)
        if log_id:
            post.update(log=log_id)
        if config_id:
            post.update(config=config_id)

        if run_failed:
            post.update(run_failed='yes')

        if ref_url:
            post.update(ref_url=ref_url)
        if ref_image:
            post.update(ref_image=ref_image)
        if ref_log:
            post.update(ref_log=ref_log)
        if ref_config:
            post.update(ref_config=ref_config)

        call = yield fetch_worker.FetchItem(
            FLAGS.release_server_prefix + '/report_run',
            post=post,
            username=FLAGS.release_client_id,
            password=FLAGS.release_client_secret)

        if call.json and call.json.get('error'):
            raise ReportRunError(call.json.get('error'))

        if not call.json or not call.json.get('success'):
            raise ReportRunError('Bad response: %r' % call)


class ReportPdiffWorkflow(workers.WorkflowItem):
    """Reports a pdiff's result status.

    Args:
        build_id: ID of the build.
        release_name: Name of the release.
        release_number: Number of the release candidate.
        run_name: Name of the pdiff being uploaded.
        diff_path: Path to the diff to upload.
        log_path: Path to the diff log to upload.
        diff_failed: True when there was a problem computing the diff. False
            when the diff was computed successfully. Defaults to False.

    Raises:
        ReportPdiffError if the pdiff status could not be reported.
    """

    def run(self, build_id, release_name, release_number, run_name,
            diff_path=None, log_path=None, diff_failed=False, distortion=None):
        diff_id = None
        log_id = None
        if (isinstance(diff_path, basestring) and
                os.path.isfile(diff_path) and
                isinstance(log_path, basestring) and
                os.path.isfile(log_path)):
            diff_id, log_id = yield [
                UploadFileWorkflow(build_id, diff_path),
                UploadFileWorkflow(build_id, log_path),
            ]
        elif isinstance(log_path, basestring) and os.path.isfile(log_path):
            log_id = yield UploadFileWorkflow(build_id, log_path)

        post = {
            'build_id': build_id,
            'release_name': release_name,
            'release_number': release_number,
            'run_name': run_name,
        }
        if diff_id:
            post.update(diff_image=diff_id)
        if log_id:
            post.update(diff_log=log_id)
        if diff_failed:
            post.update(diff_failed='yes')
        if distortion:
            post.update(distortion=distortion)

        call = yield fetch_worker.FetchItem(
            FLAGS.release_server_prefix + '/report_run',
            post=post,
            username=FLAGS.release_client_id,
            password=FLAGS.release_client_secret)

        if call.json and call.json.get('error'):
            raise ReportPdiffError(call.json.get('error'))

        if not call.json or not call.json.get('success'):
            raise ReportPdiffError('Bad response: %r' % call)


class RunsDoneWorkflow(workers.WorkflowItem):
    """Reports all runs are done for a release candidate.

    Args:
        build_id: ID of the build.
        release_name: Name of the release.
        release_number: Number of the release candidate.

    Returns:
        URL of where the results for this release candidate can be viewed.

    Raises:
        RunsDoneError if the release candidate could not have its runs
        marked done.
    """

    def run(self, build_id, release_name, release_number):
        call = yield fetch_worker.FetchItem(
            FLAGS.release_server_prefix + '/runs_done',
            post={
                'build_id': build_id,
                'release_name': release_name,
                'release_number': release_number,
            },
            username=FLAGS.release_client_id,
            password=FLAGS.release_client_secret)

        if call.json and call.json.get('error'):
            raise RunsDoneError(call.json.get('error'))

        if not call.json or not call.json.get('success'):
            raise RunsDoneError('Bad response: %r' % call)

        raise workers.Return(call.json['results_url'])


class DownloadArtifactWorkflow(workers.WorkflowItem):
    """Downloads an artifact to a given path.

    Args:
        build_id: ID of the build.
        sha1sum: Content hash of the artifact to fetch.
        result_path: Path where the artifact should be saved on disk.

    Raises:
        DownloadArtifactError if the artifact could not be found or
        fetched for some reason.
    """

    def run(self, build_id, sha1sum, result_path):
        download_url = '%s/download?sha1sum=%s&build_id=%s' % (
            FLAGS.release_server_prefix, sha1sum, build_id)
        call = yield fetch_worker.FetchItem(
            download_url,
            result_path=result_path,
            username=FLAGS.release_client_id,
            password=FLAGS.release_client_secret)
        if call.status_code != 200:
            raise DownloadArtifactError('Bad response: %r' % call)

########NEW FILE########
__FILENAME__ = timer_worker
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workers for driving screen captures, perceptual diffs, and related work."""

import Queue
import heapq
import logging
import time

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import workers


class TimerItem(workers.WorkItem):
    """Work item for waiting some period of time before returning."""

    def __init__(self, delay_seconds):
        workers.WorkItem.__init__(self)
        self.delay_seconds = delay_seconds
        self.ready_time = time.time() + delay_seconds


class TimerThread(workers.WorkerThread):
    """"Worker thread that tracks many timers."""

    def __init__(self, *args):
        """Initializer."""
        workers.WorkerThread.__init__(self, *args)
        self.timers = []

    def handle_nothing(self):
        now = time.time()
        while self.timers:
            ready_time, _ = self.timers[0]
            wait_time = ready_time - now
            if wait_time <= 0:
                _, item = heapq.heappop(self.timers)
                self.output_queue.put(item)
            else:
                # Wait for new work up to the point that the earliest
                # timer is ready to fire.
                self.polltime = wait_time
                return

        # Nothing to do, use the default poll time.
        self.polltime = FLAGS.polltime

    def handle_item(self, item):
        heapq.heappush(self.timers, (item.ready_time, item))
        self.handle_nothing()


def register(coordinator):
    """Registers this module as a worker with the given coordinator."""
    timer_queue = Queue.Queue()
    coordinator.register(TimerItem, timer_queue)
    coordinator.worker_threads.append(
        TimerThread(timer_queue, coordinator.input_queue))

########NEW FILE########
__FILENAME__ = workers
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workers for driving screen captures, perceptual diffs, and related work."""

import Queue
import logging
import sys
import threading

# Local Libraries
import gflags
FLAGS = gflags.FLAGS


gflags.DEFINE_float(
    'polltime', 1.0,
    'How long to sleep between polling for work from an input queue, '
    'a subprocess, or a waiting timer.')


class WorkItem(object):
    """Base work item that can be handled by a worker thread."""

    # Instance variables. May be overridden by a sub-class @property.
    error = None
    done = False
    parent = None

    # Set this to True for WorkItems that should never wait for their
    # return values.
    fire_and_forget = False

    def __init__(self):
        pass

    @staticmethod
    def _print_tree(obj):
        if isinstance(obj, dict):
            result = []
            for key, value in obj.iteritems():
                result.append('%s: %s' % (key, WorkItem._print_tree(value)))
            return '{%s}' % ', '.join(result)
        else:
            value_str = repr(obj)
            if len(value_str) > 100:
                return '%s...%s' % (value_str[:100], value_str[-1])
            else:
                return value_str

    def _get_dict_for_repr(self):
        return self.__dict__

    def __repr__(self):
        return '%s.%s(%s)#%d' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self._print_tree(self._get_dict_for_repr()),
            id(self))

    def check_result(self):
        # TODO: For WorkflowItems, remove generator.throw(*item.error) from
        # the stack trace since it's noise. General approach outlined here:
        # https://github.com/mitsuhiko/jinja2/blob/master/jinja2/debug.py
        if self.error:
            raise self.error[0], self.error[1], self.error[2]


class WorkerThread(threading.Thread):
    """Base worker thread that handles items one at a time."""

    def __init__(self, input_queue, output_queue):
        """Initializer.

        Args:
            input_queue: Queue this worker consumes work from.
            output_queue: Queue where this worker puts new work items, if any.
        """
        threading.Thread.__init__(self)
        self.daemon = True
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.interrupted = False
        self.polltime = FLAGS.polltime

    def stop(self):
        """Stops the thread but does not join it."""
        if self.interrupted:
            return
        self.interrupted = True

    def run(self):
        while not self.interrupted:
            try:
                item = self.input_queue.get(True, self.polltime)
            except Queue.Empty:
                self.handle_nothing()
                continue

            try:
                next_item = self.handle_item(item)
            except Exception, e:
                item.error = sys.exc_info()
                logging.exception('%s error item=%r', self.worker_name, item)
                self.output_queue.put(item)
            else:
                logging.debug('%s processed item=%r', self.worker_name, item)
                if not isinstance(item, WorkflowItem):
                    item.done = True
                if next_item:
                    self.output_queue.put(next_item)
            finally:
                self.input_queue.task_done()

    @property
    def worker_name(self):
        return '%s:%s' % (self.__class__.__name__, self.ident)

    def handle_nothing(self):
        """Runs whenever there are no items in the queue."""
        pass

    def handle_item(self, item):
        """Handles a single item.

        Args:
            item: WorkItem to process.

        Returns:
            A WorkItem that should go on the output queue. If None, then
            the provided work item is considered finished and no
            additional work is needed.
        """
        raise NotImplemented


class WorkflowItem(WorkItem):
    """Work item for coordinating other work items.

    To use: Sub-class and override run(). Yield WorkItems you want processed
    as part of this workflow. Exceptions in child workflows will be reinjected
    into the run() generator at the yield point. Results will be available on
    the WorkItems returned by yield statements. Yield a list of WorkItems
    to do them in parallel. The first error encountered for the whole list
    will be raised if there's an exception.
    """

    # Allow these value to be assigned or overridden by a sub-class @property.
    result = None
    root = False

    def __init__(self, *args, **kwargs):
        WorkItem.__init__(self)
        self.args = args
        self.kwargs = kwargs

    def run(self, *args, **kwargs):
        raise NotImplemented


class WaitAny(object):
    """Return control to a workflow after any one of these items finishes.

    As soon as a single work item completes, the combined barrier will be
    fulfilled and control will return to the WorkflowItem. The return values
    will be WorkItem instances, the same ones passed into WaitAny. For
    WorkflowItems the return values will be WorkflowItems if the work is not
    finished yet, and the final return value once work is finished.
    """

    def __init__(self, items):
        """Initializer.

        Args:
            items: List of WorkItems to wait for.
        """
        self.items = items


class Barrier(list):
    """Barrier for running multiple WorkItems in parallel."""

    def __init__(self, workflow, generator, work):
        """Initializer.

        Args:
            workflow: WorkflowItem instance this is for.
            generator: Current state of the WorkflowItem's generator.
            work: Next set of work to do. May be a single WorkItem object or
                a list or tuple that contains a set of WorkItems to run in
                parallel.
        """
        list.__init__(self)
        self.workflow = workflow
        self.generator = generator

        if isinstance(work, (list, tuple)):
            self[:] = list(work)
            self.was_list = True
            self.wait_any = False
        elif isinstance(work, WaitAny):
            self[:] = list(work.items)
            self.was_list = True
            self.wait_any = True
        else:
            self[:] = [work]
            self.was_list = False
            self.wait_any = False

        for item in self:
            assert isinstance(item, WorkItem)
            item.parent = workflow

    @property
    def outstanding(self):
        """Returns whether or not this barrier has pending work."""
        # Allow the same WorkItem to be yielded multiple times but not
        # count towards blocking the barrier.
        done_count = 0
        for item in self:
            if not self.wait_any and item.fire_and_forget:
                # Only count fire_and_forget items as done if this is
                # *not* a WaitAny barrier. We only want to return control
                # to the caller when at least one of the blocking items
                # has completed.
                done_count += 1
            elif item.done:
                done_count += 1

        if self.wait_any and done_count > 0:
            return False

        if done_count == len(self):
            return False

        return True

    @property
    def error(self):
        """Returns the error for this barrier and all work items, if any."""
        # Copy the error from any failed item to be the error for the whole
        # barrier. The first error seen "wins". Also handles the case where
        # the WorkItems passed into the barrier have already completed and
        # been marked with errors.
        for item in self:
            if isinstance(item, WorkItem) and item.error:
                return item.error
        return None

    def get_item(self):
        """Returns the item to send back into the workflow generator."""
        if self.was_list:
            blocking_items = self[:]
            self[:] = []
            for item in blocking_items:
                if (isinstance(item, WorkflowItem) and
                        item.done and
                        not item.error):
                    self.append(item.result)
                else:
                    self.append(item)
            return self
        else:
            return self[0]


class Return(Exception):
    """Raised in WorkflowItem.run to return a result to the caller."""

    def __init__(self, result=None):
        """Initializer.

        Args:
            result: Result of a WorkflowItem, if any.
        """
        self.result = result


class WorkflowThread(WorkerThread):
    """Worker thread for running workflows."""

    def __init__(self, input_queue, output_queue):
        """Initializer.

        Args:
            input_queue: Queue this worker consumes work from. These should be
                WorkflowItems to process, or any WorkItems registered with this
                class using the register() method.
            output_queue: Queue where this worker puts finished work items,
                if any.
        """
        WorkerThread.__init__(self, input_queue, output_queue)
        self.pending = {}
        self.work_map = {}
        self.worker_threads = []
        self.register(WorkflowItem, input_queue)

    # TODO: Implement drain, to let all existing work finish but no new work
    # allowed at the top of the funnel.

    def start(self):
        """Starts the coordinator thread and all related worker threads."""
        assert not self.interrupted
        for thread in self.worker_threads:
            thread.start()
        WorkerThread.start(self)

    def stop(self):
        """Stops the coordinator thread and all related threads."""
        if self.interrupted:
            return
        for thread in self.worker_threads:
            thread.interrupted = True
        self.interrupted = True

    def join(self):
        """Joins the coordinator thread and all worker threads."""
        for thread in self.worker_threads:
            thread.join()
        WorkerThread.join(self)

    def wait_one(self):
        """Waits until this worker has finished one work item or died."""
        while True:
            try:
                item = self.output_queue.get(True, 1)
            except Queue.Empty:
                continue
            except KeyboardInterrupt:
                logging.debug('Exiting')
                return
            else:
                item.check_result()
                return

    def register(self, work_type, queue):
        """Registers where work for a specific type can be executed.

        Args:
            work_type: Sub-class of WorkItem to register.
            queue: Queue instance where WorkItems of the work_type should be
                enqueued when they are yielded by WorkflowItems being run by
                this worker.
        """
        self.work_map[work_type] = queue

    def enqueue_barrier(self, barrier):
        for item in barrier:
            if item.done:
                # Don't reenqueue items that are already done.
                continue

            # Try to find a queue by the work item's class, then by its
            # super class, and so on.
            next_types = [type(item)]
            while next_types:
                try_types = next_types[:]
                next_types[:] = []
                for current_type in try_types:
                    target_queue = self.work_map.get(current_type)
                    if target_queue:
                        next_types = []
                        break
                    next_types.extend(current_type.__bases__)

            assert target_queue, 'Could not find queue to handle %r' % item

            if not item.fire_and_forget:
                self.pending[item] = barrier
            target_queue.put(item)

    def dequeue_barrier(self, item):
        # This is a WorkItem from a worker thread that has finished and
        # needs to be reinjected into a WorkflowItem generator.
        barrier = self.pending.pop(item, None)
        if not barrier:
            # Item was already finished in another barrier, or was
            # fire-and-forget and never part of a barrier; ignore it.
            return None

        if barrier.outstanding and not barrier.error:
            # More work to do and no error seen. Keep waiting.
            return None

        for work in barrier:
            # The barrier has been fulfilled one way or another. Clear out any
            # other pending parts of the barrier so they don't trigger again.
            self.pending.pop(work, None)

        return barrier

    def handle_item(self, item):
        if isinstance(item, WorkflowItem) and not item.done:
            workflow = item
            try:
                generator = item.run(*item.args, **item.kwargs)
            except TypeError, e:
                raise TypeError('Bad workflow function item=%r error=%s' % (
                                item, str(e)))
            item = None
        else:
            barrier = self.dequeue_barrier(item)
            if not barrier:
                logging.debug('Could not find barrier for finished item=%r',
                              item)
                return
            item = barrier.get_item()
            workflow = barrier.workflow
            generator = barrier.generator

        while True:
            try:
                try:
                    error = item is not None and item.error
                    if error:
                        logging.debug('Throwing workflow=%r error=%r',
                                      workflow, error)
                        next_item = generator.throw(*error)
                    elif isinstance(item, WorkflowItem) and item.done:
                        logging.debug(
                            'Sending workflow=%r finished item=%r',
                            workflow, item)
                        next_item = generator.send(item.result)
                    else:
                        logging.debug(
                            'Sending workflow=%r finished item=%r',
                            workflow, item)
                        next_item = generator.send(item)
                except StopIteration:
                    logging.debug('Exhausted workflow=%r', workflow)
                    workflow.done = True
                except Return, e:
                    logging.debug('Return from workflow=%r result=%r',
                                  workflow, e.result)
                    workflow.done = True
                    workflow.result = e.result
                except Exception, e:
                    logging.exception(
                        'Error in workflow=%r from item=%r, error=%r',
                        workflow, item, error)
                    workflow.done = True
                    workflow.error = sys.exc_info()
            finally:
                if workflow.done:
                    if workflow.root:
                        # Root workflow finished. This goes to the output
                        # queue so it can be received by the main thread.
                        return workflow
                    else:
                        # Sub-workflow finished. Reinject it into the
                        # workflow so a pending parent can catch it.
                        self.input_queue.put(workflow)
                        return

            barrier = Barrier(workflow, generator, next_item)
            self.enqueue_barrier(barrier)
            if barrier.outstanding:
                break

            # If a returned barrier has no oustanding parts, immediately
            # progress the workflow.
            item = barrier.get_item()


class PrintWorkflow(WorkflowItem):
    """Prints a message to stdout."""

    def run(self, message):
        yield []  # Make this into a generator
        print message


def get_coordinator():
    """Creates a coordinator and returns it."""
    workflow_queue = Queue.Queue()
    complete_queue = Queue.Queue()
    coordinator = WorkflowThread(workflow_queue, complete_queue)
    coordinator.register(WorkflowItem, workflow_queue)
    return coordinator

########NEW FILE########
__FILENAME__ = constants
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Constants used by all sub-modules of dpxdt.

* Do not import anything into this file!
* Do not put configuration in this file!
* Do not put secret keys in this file!
"""


CAPTURE_QUEUE_NAME = 'capture'

PDIFF_QUEUE_NAME = 'run-pdiff'

SITE_DIFF_QUEUE_NAME = 'site-diff'

########NEW FILE########
__FILENAME__ = runserver
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Runs the dpxdt API server, optionally with local queue workers."""

import logging
import os
import sys
import threading

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt import runworker
from dpxdt import server


gflags.DEFINE_bool(
    'local_queue_workers', False,
    'When true, run queue worker threads locally in the same process '
    'as the server.')

gflags.DEFINE_bool(
    'reload_code', False,
    'Reload code on every request. Should only be used in local development.')

gflags.DEFINE_bool(
    'ignore_auth', False,
    'Ignore any need for authentication for API and frontend accesses. You '
    'should only do this for local development!')

gflags.DEFINE_integer('port', 5000, 'Port to run the HTTP server on.')

gflags.DEFINE_string('host', '0.0.0.0', 'Host argument for the server.')


def main(argv):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig(
        format='%(levelname)s %(filename)s:%(lineno)s] %(message)s')
    if FLAGS.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    if FLAGS.verbose_queries:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

    if FLAGS.local_queue_workers:
        coordinator = runworker.run_workers()

        # If the babysitter thread dies, the whole process goes down.
        def worker_babysitter():
            try:
                coordinator.wait_one()
            finally:
                os._exit(1)

        babysitter_thread = threading.Thread(target=worker_babysitter)
        babysitter_thread.setDaemon(True)
        babysitter_thread.start()

    if FLAGS.ignore_auth:
        server.app.config['IGNORE_AUTH'] = True

    server.app.run(debug=FLAGS.reload_code, host=FLAGS.host, port=FLAGS.port)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = runworker
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Runs a dpxdt queue worker."""

import Queue
import logging
import sys
import threading

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import capture_worker
from dpxdt.client import fetch_worker
from dpxdt.client import pdiff_worker
from dpxdt.client import timer_worker
from dpxdt.client import workers


def run_workers():
    coordinator = workers.get_coordinator()
    capture_worker.register(coordinator)
    fetch_worker.register(coordinator)
    pdiff_worker.register(coordinator)
    timer_worker.register(coordinator)
    coordinator.start()
    return coordinator
    logging.info('Workers started')


def main(argv):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    logging.basicConfig(
        format='%(levelname)s %(filename)s:%(lineno)s] %(message)s')

    if FLAGS.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if FLAGS.verbose_queries:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)

    coordinator = run_workers()
    coordinator.wait_one()


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = api
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Web-based API for managing screenshots and incremental perceptual diffs.

Lifecycle of a release:

1. User creates a new build, which represents a single product or site that
   will be screenshotted repeatedly over time. This may happen very
   infrequenty through a web UI.

2. User creates a new release candidate for the build with a specific release
   name. The candidate is an attempt at finishing a specific release name. It
   may take many attempts, many candidates, before the release with that name
   is complete and can be marked as good.

3. User creates many runs for the candidate created in #2. Each run is
   identified by a unique name that describes what it does. For example, the
   run name could be the URL path for a page being screenshotted. The user
   associates each run with a new screenshot artifact. Runs are automatically
   associated with a corresponding run from the last good release. This makes
   it easy to compare new and old screenshots for runs with the same name.

4. User uploads a series of screenshot artifacts identified by content hash.
   Perceptual diffs between these new screenshots and the last good release
   may also be uploaded as an optimization. This may happen in parallel
   with #3.

5. The user marks the release candidate as having all of its expected runs
   present, meaning it will no longer receive new runs. This should only
   happen after all screenshot artifacts have finished uploading.

6. If a run indicates a previous screenshot, but no perceptual diff has
   been made to compare the new and old versions, a worker will do a perceptual
   diff, upload it, and associate it with the run.

7. Once all perceptual diffs for a release candidate's runs are complete,
   the results of the candidate are emailed out to the build's owner.

8. The build owner can go into a web UI, inspect the new/old perceptual diffs,
   and mark certain runs as okay even though the perceptual diff showed a
   difference. For example, a new feature will cause a perceptual diff, but
   should not be treated as a failure.

9. The user decides the release candidate looks correct and marks it as good,
   or the user thinks the candidate looks bad and goes back to #2 and begins
   creating a new candidate for that release all over again.


Notes:

- At any time, a user can manually mark any candidate or release as bad. This
  is useful to deal with bugs in the screenshotter, mistakes in approving a
  release candidate, rolling back to an earlier version, etc.

- As soon as a new release name is cut for a build, the last candidate of
  the last release is marked as good if there is no other good candidate. This
  lets the API establish a "baseline" release easily for first-time users.

- Only one release candidate may be receiving runs for a build at a time.

- Failure status can be indicated for a run at the capture phase or the
  diff phase. The API assumes that the same user that indicated the failure
  will also provide a log for the failing process so it can be inspected
  manually for a root cause. Uploading image artifacts for failed runs is
  not supported.
"""

import datetime
import hashlib
import functools
import json
import logging
import mimetypes
import time

# Local libraries
import flask
from flask import Flask, abort, g, request, url_for
from flask.exceptions import HTTPException

# Local modules
from . import app
from . import db
from dpxdt import constants
from dpxdt.server import auth
from dpxdt.server import emails
from dpxdt.server import models
from dpxdt.server import signals
from dpxdt.server import work_queue
from dpxdt.server import utils


@app.route('/api/create_release', methods=['POST'])
@auth.build_api_access_required
@utils.retryable_transaction()
def create_release():
    """Creates a new release candidate for a build."""
    build = g.build
    release_name = request.form.get('release_name')
    utils.jsonify_assert(release_name, 'release_name required')
    url = request.form.get('url')
    utils.jsonify_assert(release_name, 'url required')

    release = models.Release(
        name=release_name,
        url=url,
        number=1,
        build_id=build.id)

    last_candidate = (
        models.Release.query
        .filter_by(build_id=build.id, name=release_name)
        .order_by(models.Release.number.desc())
        .first())
    if last_candidate:
        release.number += last_candidate.number
        if last_candidate.status == models.Release.PROCESSING:
            canceled_task_count = work_queue.cancel(
                release_id=last_candidate.id)
            logging.info('Canceling %d tasks for previous attempt '
                         'build_id=%r, release_name=%r, release_number=%d',
                         canceled_task_count, build.id, last_candidate.name,
                         last_candidate.number)
            last_candidate.status = models.Release.BAD
            db.session.add(last_candidate)

    db.session.add(release)
    db.session.commit()

    signals.release_updated_via_api.send(app, build=build, release=release)

    logging.info('Created release: build_id=%r, release_name=%r, url=%r, '
                 'release_number=%d', build.id, release.name,
                 url, release.number)

    return flask.jsonify(
        success=True,
        build_id=build.id,
        release_name=release.name,
        release_number=release.number,
        url=url)


def _check_release_done_processing(release):
    """Moves a release candidate to reviewing if all runs are done."""
    if release.status != models.Release.PROCESSING:
        # NOTE: This statement also guards for situations where the user has
        # prematurely specified that the release is good or bad. Once the user
        # has done that, the system will not automatically move the release
        # back into the 'reviewing' state or send the email notification below.
        logging.info('Release not in processing state yet: build_id=%r, '
                     'name=%r, number=%d', release.build_id, release.name,
                     release.number)
        return False

    query = models.Run.query.filter_by(release_id=release.id)
    for run in query:
        if run.status == models.Run.NEEDS_DIFF:
            # Still waiting for the diff to finish.
            return False
        if run.ref_config and not run.ref_image:
            # Still waiting for the ref capture to process.
            return False
        if run.config and not run.image:
            # Still waiting for the run capture to process.
            return False

    logging.info('Release done processing, now reviewing: build_id=%r, '
                 'name=%r, number=%d', release.build_id, release.name,
                 release.number)

    # Send the email at the end of this request so we know it's only
    # sent a single time (guarded by the release.status check above).
    build_id = release.build_id
    release_name = release.name
    release_number = release.number

    @utils.after_this_request
    def send_notification_email(response):
        emails.send_ready_for_review(build_id, release_name, release_number)

    release.status = models.Release.REVIEWING
    db.session.add(release)
    return True


def _get_release_params():
    """Gets the release params from the current request."""
    release_name = request.form.get('release_name')
    utils.jsonify_assert(release_name, 'release_name required')
    release_number = request.form.get('release_number', type=int)
    utils.jsonify_assert(release_number is not None, 'release_number required')
    return release_name, release_number


def _find_last_good_run(build):
    """Finds the last good release and run for a build."""
    run_name = request.form.get('run_name', type=str)
    utils.jsonify_assert(run_name, 'run_name required')

    last_good_release = (
        models.Release.query
        .filter_by(
            build_id=build.id,
            status=models.Release.GOOD)
        .order_by(models.Release.created.desc())
        .first())

    last_good_run = None

    if last_good_release:
        logging.debug('Found last good release for: build_id=%r, '
                      'release_name=%r, release_number=%d',
                      build.id, last_good_release.name,
                      last_good_release.number)
        last_good_run = (
            models.Run.query
            .filter_by(release_id=last_good_release.id, name=run_name)
            .first())
        if last_good_run:
            logging.debug('Found last good run for: build_id=%r, '
                          'release_name=%r, release_number=%d, '
                          'run_name=%r',
                          build.id, last_good_release.name,
                          last_good_release.number, last_good_run.name)

    return last_good_release, last_good_run


@app.route('/api/find_run', methods=['POST'])
@auth.build_api_access_required
def find_run():
    """Finds the last good run of the given name for a release."""
    build = g.build
    last_good_release, last_good_run = _find_last_good_run(build)

    if last_good_run:
        return flask.jsonify(
            success=True,
            build_id=build.id,
            release_name=last_good_release.name,
            release_number=last_good_release.number,
            run_name=last_good_run.name,
            url=last_good_run.url,
            image=last_good_run.image,
            log=last_good_run.log,
            config=last_good_run.config)

    return utils.jsonify_error('Run not found')


def _get_or_create_run(build):
    """Gets a run for a build or creates it if it does not exist."""
    release_name, release_number = _get_release_params()
    run_name = request.form.get('run_name', type=str)
    utils.jsonify_assert(run_name, 'run_name required')

    release = (
        models.Release.query
        .filter_by(build_id=build.id, name=release_name, number=release_number)
        .first())
    utils.jsonify_assert(release, 'release does not exist')

    run = (
        models.Run.query
        .filter_by(release_id=release.id, name=run_name)
        .first())
    if not run:
        # Ignore re-reports of the same run name for this release.
        logging.info('Created run: build_id=%r, release_name=%r, '
                     'release_number=%d, run_name=%r',
                     build.id, release.name, release.number, run_name)
        run = models.Run(
            release_id=release.id,
            name=run_name,
            status=models.Run.DATA_PENDING)
        db.session.add(run)
        db.session.flush()

    return release, run


def _enqueue_capture(build, release, run, url, config_data, baseline=False):
    """Enqueues a task to run a capture process."""
    # Validate the JSON config parses.
    try:
        config_dict = json.loads(config_data)
    except Exception, e:
        abort(utils.jsonify_error(e))

    # Rewrite the config JSON to include the URL specified in this request.
    # Blindly overwrite anything that was there.
    config_dict['targetUrl'] = url
    config_data = json.dumps(config_dict)

    config_artifact = _save_artifact(build, config_data, 'application/json')
    db.session.add(config_artifact)
    db.session.flush()

    suffix = ''
    if baseline:
        suffix = ':baseline'

    task_id = '%s:%s%s' % (run.id, hashlib.sha1(url).hexdigest(), suffix)
    logging.info('Enqueueing capture task=%r, baseline=%r', task_id, baseline)

    work_queue.add(
        constants.CAPTURE_QUEUE_NAME,
        payload=dict(
            build_id=build.id,
            release_name=release.name,
            release_number=release.number,
            run_name=run.name,
            url=url,
            config_sha1sum=config_artifact.id,
            baseline=baseline,
        ),
        build_id=build.id,
        release_id=release.id,
        run_id=run.id,
        source='request_run',
        task_id=task_id)

    # Set the URL and config early to indicate to report_run that there is
    # still data pending even if 'image' and 'ref_image' are unset.
    if baseline:
        run.ref_url = url
        run.ref_config = config_artifact.id
    else:
        run.url = url
        run.config = config_artifact.id


@app.route('/api/request_run', methods=['POST'])
@auth.build_api_access_required
@utils.retryable_transaction()
def request_run():
    """Requests a new run for a release candidate."""
    build = g.build
    current_release, current_run = _get_or_create_run(build)

    current_url = request.form.get('url', type=str)
    config_data = request.form.get('config', default='{}', type=str)
    utils.jsonify_assert(current_url, 'url to capture required')
    utils.jsonify_assert(config_data, 'config document required')

    config_artifact = _enqueue_capture(
        build, current_release, current_run, current_url, config_data)

    ref_url = request.form.get('ref_url', type=str)
    ref_config_data = request.form.get('ref_config', type=str)
    utils.jsonify_assert(
        bool(ref_url) == bool(ref_config_data),
        'ref_url and ref_config must both be specified or not specified')

    if ref_url and ref_config_data:
        ref_config_artifact = _enqueue_capture(
            build, current_release, current_run, ref_url, ref_config_data,
            baseline=True)
    else:
        _, last_good_run = _find_last_good_run(build)
        if last_good_run:
            current_run.ref_url = last_good_run.url
            current_run.ref_image = last_good_run.image
            current_run.ref_log = last_good_run.log
            current_run.ref_config = last_good_run.config

    db.session.add(current_run)
    db.session.commit()

    signals.run_updated_via_api.send(
        app, build=build, release=current_release, run=current_run)

    return flask.jsonify(
        success=True,
        build_id=build.id,
        release_name=current_release.name,
        release_number=current_release.number,
        run_name=current_run.name,
        url=current_run.url,
        config=current_run.config,
        ref_url=current_run.ref_url,
        ref_config=current_run.ref_config)


@app.route('/api/report_run', methods=['POST'])
@auth.build_api_access_required
@utils.retryable_transaction()
def report_run():
    """Reports data for a run for a release candidate."""
    build = g.build
    release, run = _get_or_create_run(build)

    db.session.refresh(run, lockmode='update')

    current_url = request.form.get('url', type=str)
    current_image = request.form.get('image', type=str)
    current_log = request.form.get('log', type=str)
    current_config = request.form.get('config', type=str)

    ref_url = request.form.get('ref_url', type=str)
    ref_image = request.form.get('ref_image', type=str)
    ref_log = request.form.get('ref_log', type=str)
    ref_config = request.form.get('ref_config', type=str)

    diff_failed = request.form.get('diff_failed', type=str)
    diff_image = request.form.get('diff_image', type=str)
    diff_log = request.form.get('diff_log', type=str)

    distortion = request.form.get('distortion', default=None, type=float)
    run_failed = request.form.get('run_failed', type=str)

    if current_url:
        run.url = current_url
    if current_image:
        run.image = current_image
    if current_log:
        run.log = current_log
    if current_config:
        run.config = current_config
    if current_image or current_log or current_config:
        logging.info('Saving run data: build_id=%r, release_name=%r, '
                     'release_number=%d, run_name=%r, url=%r, '
                     'image=%r, log=%r, config=%r, run_failed=%r',
                     build.id, release.name, release.number, run.name,
                     run.url, run.image, run.log, run.config, run_failed)

    if ref_url:
        run.ref_url = ref_url
    if ref_image:
        run.ref_image = ref_image
    if ref_log:
        run.ref_log = ref_log
    if ref_config:
        run.ref_config = ref_config
    if ref_image or ref_log or ref_config:
        logging.info('Saved reference data: build_id=%r, release_name=%r, '
                     'release_number=%d, run_name=%r, ref_url=%r, '
                     'ref_image=%r, ref_log=%r, ref_config=%r',
                     build.id, release.name, release.number, run.name,
                     run.ref_url, run.ref_image, run.ref_log, run.ref_config)

    if diff_image:
        run.diff_image = diff_image
    if diff_log:
        run.diff_log = diff_log
    if distortion:
        run.distortion = distortion

    if diff_image or diff_log:
        logging.info('Saved pdiff: build_id=%r, release_name=%r, '
                     'release_number=%d, run_name=%r, diff_image=%r, '
                     'diff_log=%r, diff_failed=%r, distortion=%r',
                     build.id, release.name, release.number, run.name,
                     run.diff_image, run.diff_log, diff_failed, distortion)

    if run.image and run.diff_image:
        run.status = models.Run.DIFF_FOUND
    elif run.image and run.ref_image and not run.diff_log:
        run.status = models.Run.NEEDS_DIFF
    elif run.image and run.ref_image and not diff_failed:
        run.status = models.Run.DIFF_NOT_FOUND
    elif run.image and not run.ref_config:
        run.status = models.Run.NO_DIFF_NEEDED
    elif run_failed or diff_failed:
        run.status = models.Run.FAILED
    else:
        # NOTE: Intentionally do not transition state here in the default case.
        # We allow multiple background workers to be writing to the same Run in
        # parallel updating its various properties.
        pass

    # TODO: Verify the build has access to both the current_image and
    # the reference_sha1sum so they can't make a diff from a black image
    # and still see private data in the diff image.

    if run.status == models.Run.NEEDS_DIFF:
        task_id = '%s:%s:%s' % (run.id, run.image, run.ref_image)
        logging.info('Enqueuing pdiff task=%r', task_id)

        work_queue.add(
            constants.PDIFF_QUEUE_NAME,
            payload=dict(
                build_id=build.id,
                release_name=release.name,
                release_number=release.number,
                run_name=run.name,
                run_sha1sum=run.image,
                reference_sha1sum=run.ref_image,
            ),
            build_id=build.id,
            release_id=release.id,
            run_id=run.id,
            source='report_run',
            task_id=task_id)

    # Flush the run so querying for Runs in _check_release_done_processing
    # will be find the new run too and we won't deadlock.
    db.session.add(run)
    db.session.flush()

    _check_release_done_processing(release)
    db.session.commit()

    signals.run_updated_via_api.send(
        app, build=build, release=release, run=run)

    logging.info('Updated run: build_id=%r, release_name=%r, '
                 'release_number=%d, run_name=%r, status=%r',
                 build.id, release.name, release.number, run.name, run.status)

    return flask.jsonify(success=True)


@app.route('/api/runs_done', methods=['POST'])
@auth.build_api_access_required
@utils.retryable_transaction()
def runs_done():
    """Marks a release candidate as having all runs reported."""
    build = g.build
    release_name, release_number = _get_release_params()

    release = (
        models.Release.query
        .filter_by(build_id=build.id, name=release_name, number=release_number)
        .with_lockmode('update')
        .first())
    utils.jsonify_assert(release, 'Release does not exist')

    release.status = models.Release.PROCESSING
    db.session.add(release)
    _check_release_done_processing(release)
    db.session.commit()

    signals.release_updated_via_api.send(app, build=build, release=release)

    logging.info('Runs done for release: build_id=%r, release_name=%r, '
                 'release_number=%d', build.id, release.name, release.number)

    results_url = url_for(
        'view_release',
        id=build.id,
        name=release.name,
        number=release.number,
        _external=True)

    return flask.jsonify(
        success=True,
        results_url=results_url)


def _artifact_created(artifact):
    """Called whenever an Artifact is created.

    This method may be overridden in environments that have a different way of
    storing artifact files, such as on-disk or S3. Use the artifact.alternate
    field to hold the environment-specific data you need.
    """
    pass


def _save_artifact(build, data, content_type):
    """Saves an artifact to the DB and returns it."""
    sha1sum = hashlib.sha1(data).hexdigest()
    artifact = models.Artifact.query.filter_by(id=sha1sum).first()

    if artifact:
      logging.debug('Upload already exists: artifact_id=%r', sha1sum)
    else:
      logging.info('Upload received: artifact_id=%r, content_type=%r',
                   sha1sum, content_type)
      artifact = models.Artifact(
          id=sha1sum,
          content_type=content_type,
          data=data)
      _artifact_created(artifact)

    artifact.owners.append(build)
    return artifact


@app.route('/api/upload', methods=['POST'])
@auth.build_api_access_required
@utils.retryable_transaction()
def upload():
    """Uploads an artifact referenced by a run."""
    build = g.build
    utils.jsonify_assert(len(request.files) == 1,
                         'Need exactly one uploaded file')

    file_storage = request.files.values()[0]
    data = file_storage.read()
    content_type, _ = mimetypes.guess_type(file_storage.filename)

    artifact = _save_artifact(build, data, content_type)

    db.session.add(artifact)
    db.session.commit()

    return flask.jsonify(
        success=True,
        build_id=build.id,
        sha1sum=artifact.id,
        content_type=content_type)


def _get_artifact_response(artifact):
    """Gets the response object for the given artifact.

    This method may be overridden in environments that have a different way of
    storing artifact files, such as on-disk or S3.
    """
    response = flask.Response(
        artifact.data,
        mimetype=artifact.content_type)
    response.cache_control.public = True
    response.cache_control.max_age = 8640000
    response.set_etag(artifact.id)
    return response


@app.route('/api/download')
def download():
    """Downloads an artifact by it's content hash."""
    # Allow users with access to the build to download the file. Falls back
    # to API keys with access to the build. Prefer user first for speed.
    try:
        build = auth.can_user_access_build('build_id')
    except HTTPException:
        logging.debug('User access to artifact failed. Trying API key.')
        _, build = auth.can_api_key_access_build('build_id')

    sha1sum = request.args.get('sha1sum', type=str)
    if not sha1sum:
        logging.debug('Artifact sha1sum=%r not supplied', sha1sum)
        abort(404)

    artifact = models.Artifact.query.get(sha1sum)
    if not artifact:
        logging.debug('Artifact sha1sum=%r does not exist', sha1sum)
        abort(404)

    build_id = request.args.get('build_id', type=int)
    if not build_id:
        logging.debug('build_id missing for artifact sha1sum=%r', sha1sum)
        abort(404)

    is_owned = artifact.owners.filter_by(id=build_id).first()
    if not is_owned:
        logging.debug('build_id=%r not owner of artifact sha1sum=%r',
                      build_id, sha1sum)
        abort(403)

    # Make sure there are no Set-Cookie headers on the response so this
    # request is cachable by all HTTP frontends.
    @utils.after_this_request
    def no_session(response):
        if 'Set-Cookie' in response.headers:
            del response.headers['Set-Cookie']

    if not utils.is_production():
        # Insert a sleep to emulate how the page loading looks in production.
        time.sleep(1.5)

    if request.if_none_match and request.if_none_match.contains(sha1sum):
        response = flask.Response(status=304)
        return response

    return _get_artifact_response(artifact)

########NEW FILE########
__FILENAME__ = auth
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implements authentication for the API server and frontend."""

import datetime
import functools
import json
import logging
import time
import urllib
import urllib2

# Local libraries
import flask
from flask import abort, g, redirect, render_template, request, url_for
from flask.ext.login import (
    confirm_login, current_user, fresh_login_required, login_fresh,
    login_required, login_user, logout_user)

# Local modules
from . import app
from . import db
from . import login
import config
from dpxdt.server import forms
from dpxdt.server import models
from dpxdt.server import operations
from dpxdt.server import utils

GOOGLE_OAUTH2_AUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_OAUTH2_TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_OAUTH2_USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo'
GOOGLE_OAUTH2_SCOPES ='https://www.googleapis.com/auth/userinfo.email'
FETCH_TIMEOUT_SECONDS = 60


@login.user_loader
def load_user(user_id):
    user = operations.UserOps(user_id).load()
    if user and user.is_authenticated():
        logging.debug('Authenticated as user=%r', user.get_id())
    return user


@app.context_processor
def auth_context():
    """Adds extra default context for rendered templates."""
    return dict(current_user=current_user)


@app.route('/login')
def login_view():
    next_url = request.args.get('next', default='/', type=str)

    if app.config.get('IGNORE_AUTH'):
        fake_id = 'anonymous_superuser'
        anonymous_superuser = models.User.query.get(fake_id)
        if not anonymous_superuser:
            anonymous_superuser = models.User(
                id=fake_id,
                email_address='superuser@example.com',
                superuser=1)
            db.session.add(anonymous_superuser)
            db.session.commit()
        login_user(anonymous_superuser)
        confirm_login()
        return redirect(next_url)

    # Inspired by:
    #   http://stackoverflow.com/questions/9499286
    #   /using-google-oauth2-with-flask
    params = dict(
        response_type='code',
        client_id=config.GOOGLE_OAUTH2_CLIENT_ID,
        redirect_uri=config.GOOGLE_OAUTH2_REDIRECT_URI,
        scope=GOOGLE_OAUTH2_SCOPES,
        state=urllib.quote(next_url),
    )
    target_url = '%s?%s' % (
        GOOGLE_OAUTH2_AUTH_URL, urllib.urlencode(params))
    logging.debug('Redirecting user to login at url=%r', target_url)
    return redirect(target_url)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('homepage'))


@app.route(config.GOOGLE_OAUTH2_REDIRECT_PATH)
def login_auth():
    # TODO: Handle when the 'error' parameter is present
    params = dict(
        code=request.args.get('code'),
        client_id=config.GOOGLE_OAUTH2_CLIENT_ID,
        client_secret=config.GOOGLE_OAUTH2_CLIENT_SECRET,
        redirect_uri=config.GOOGLE_OAUTH2_REDIRECT_URI,
        grant_type='authorization_code'
    )
    payload = urllib.urlencode(params)
    logging.debug('Posting for token to url=%r, payload=%r',
                  GOOGLE_OAUTH2_TOKEN_URL, payload)
    fetch_request = urllib2.Request(GOOGLE_OAUTH2_TOKEN_URL, payload)
    conn = urllib2.urlopen(fetch_request, timeout=FETCH_TIMEOUT_SECONDS)
    data = conn.read()
    result_dict = json.loads(data)

    params = dict(
        access_token=result_dict['access_token']
    )
    payload = urllib.urlencode(params)
    target_url = '%s?%s' % (GOOGLE_OAUTH2_USERINFO_URL, payload)
    logging.debug('Fetching user info from url=%r', target_url)
    fetch_request = urllib2.Request(target_url)
    conn = urllib2.urlopen(fetch_request, timeout=FETCH_TIMEOUT_SECONDS)
    data = conn.read()
    result_dict = json.loads(data)
    logging.debug('Result user info dict: %r', result_dict)
    email_address = result_dict['email']

    if not result_dict['verified_email']:
        abort(flask.Response('Your email address must be verified', 403))

    user_id = '%s:%s' % (models.User.GOOGLE_OAUTH2, result_dict['id'])
    user = models.User.query.get(user_id)
    if not user:
        user = models.User(id=user_id)

    # Email address on the account may change, user ID will stay the same.
    # Do not allow the user to claim existing build invitations with their
    # old email address.
    if user.email_address != email_address:
        user.email_address = email_address

    user.last_seen = datetime.datetime.utcnow()

    db.session.add(user)
    db.session.commit()

    login_user(user)
    confirm_login()

    # Clear all flashed messages from the session on login.
    flask.get_flashed_messages()

    final_url = urllib.unquote(request.args.get('state'))
    logging.debug('User is logged in. Redirecting to url=%r', final_url)
    return redirect(final_url)


@app.route('/whoami')
@login_required
def debug_login():
    return render_template(
        'whoami.html', user=current_user)


def superuser_required(f):
    """Requires the requestor to be a super user."""
    @functools.wraps(f)
    @login_required
    def wrapped(*args, **kwargs):
        if not (current_user.is_authenticated() and current_user.superuser):
            abort(403)
        return f(*args, **kwargs)
    return wrapped


def can_user_access_build(param_name):
    """Determines if the current user can access the build ID in the request.

    Args:
        param_name: Parameter name to use for getting the build ID from the
            request. Will fetch from GET or POST requests.

    Returns:
        The build the user has access to.
    """
    build_id = (
        request.args.get(param_name, type=int) or
        request.form.get(param_name, type=int))
    if not build_id:
        logging.debug('Build ID in param_name=%r was missing', param_name)
        abort(400)

    ops = operations.UserOps(current_user.get_id())
    build, user_is_owner = ops.owns_build(build_id)
    if not build:
        logging.debug('Could not find build_id=%r', build_id)
        abort(404)

    if current_user.is_authenticated() and not user_is_owner:
        # Assume the user should be able to access the build but can't because
        # the cache is out of date. This forces the cache to repopulate, any
        # outstanding user invitations to be completed, hopefully resulting in
        # the user having access to the build.
        ops.evict()
        claim_invitations(current_user)
        build, user_is_owner = ops.owns_build(build_id)

    if not user_is_owner:
        if current_user.is_authenticated() and current_user.superuser:
            pass
        elif request.method != 'GET':
            logging.debug('No way to log in user via modifying request')
            abort(403)
        elif build.public:
            pass
        elif current_user.is_authenticated():
            logging.debug('User does not have access to this build')
            abort(flask.Response('You cannot access this build', 403))
        else:
            logging.debug('Redirecting user to login to get build access')
            abort(login.unauthorized())
    elif not login_fresh():
        logging.debug('User login is old; forcing refresh')
        abort(login.needs_refresh())

    return build


def build_access_required(function_or_param_name):
    """Decorator ensures user has access to the build ID in the request.

    May be used in two ways:

        @build_access_required
        def my_func(build):
            ...

        @build_access_required('custom_build_id_param')
        def my_func(build):
            ...

    Always calls the given function with the models.Build entity as the
    first positional argument.
    """
    def get_wrapper(param_name, f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            g.build = can_user_access_build(param_name)
            if not utils.is_production():
                # Insert a sleep to emulate page loading in production.
                time.sleep(0.5)
            return f(*args, **kwargs)
        return wrapped

    if isinstance(function_or_param_name, basestring):
        return lambda f: get_wrapper(function_or_param_name, f)
    else:
        return get_wrapper('id', function_or_param_name)


def _get_api_key_ops():
    """Gets the operations.ApiKeyOps instance for the current request."""
    auth_header = request.authorization
    if not auth_header:
        logging.debug('API request lacks authorization header')
        abort(flask.Response(
            'API key required', 401,
            {'WWW-Authenticate': 'Basic realm="API key required"'}))

    return operations.ApiKeyOps(auth_header.username, auth_header.password)


def current_api_key():
    """Determines the API key for the current request.

    Returns:
        The ApiKey instance.
    """
    if app.config.get('IGNORE_AUTH'):
        return models.ApiKey(
            id='anonymous_superuser',
            secret='',
            superuser=True)

    ops = _get_api_key_ops()
    api_key = ops.get()
    logging.debug('Authenticated as API key=%r', api_key.id)

    return api_key


def can_api_key_access_build(param_name):
    """Determines if the current API key can access the build in the request.

    Args:
        param_name: Parameter name to use for getting the build ID from the
            request. Will fetch from GET or POST requests.

    Returns:
        (api_key, build) The API Key and the Build it has access to.
    """
    build_id = (
        request.args.get(param_name, type=int) or
        request.form.get(param_name, type=int))
    utils.jsonify_assert(build_id, 'build_id required')

    if app.config.get('IGNORE_AUTH'):
        api_key = models.ApiKey(
            id='anonymous_superuser',
            secret='',
            superuser=True)
        build = models.Build.query.get(build_id)
        utils.jsonify_assert(build is not None, 'build must exist', 404)
    else:
        ops = _get_api_key_ops()
        api_key, build = ops.can_access_build(build_id)

    return api_key, build


def build_api_access_required(f):
    """Decorator ensures API key has access to the build ID in the request.

    Always calls the given function with the models.Build entity as the
    first positional argument.
    """
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        g.api_key, g.build = can_api_key_access_build('build_id')
        return f(*args, **kwargs)
    return wrapped


def superuser_api_key_required(f):
    """Decorator ensures only superuser API keys can request this function."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        api_key = current_api_key()
        g.api_key = api_key

        utils.jsonify_assert(
            api_key.superuser,
            'API key=%r must be a super user' % api_key.id,
            403)

        return f(*args, **kwargs)

    return wrapped


@app.route('/api_keys', methods=['GET', 'POST'])
@fresh_login_required
@build_access_required('build_id')
def manage_api_keys():
    """Page for viewing and creating API keys."""
    build = g.build
    create_form = forms.CreateApiKeyForm()
    if create_form.validate_on_submit():
        api_key = models.ApiKey()
        create_form.populate_obj(api_key)
        api_key.id = utils.human_uuid()
        api_key.secret = utils.password_uuid()

        save_admin_log(build, created_api_key=True, message=api_key.id)

        db.session.add(api_key)
        db.session.commit()

        logging.info('Created API key=%r for build_id=%r',
                     api_key.id, build.id)
        return redirect(url_for('manage_api_keys', build_id=build.id))

    create_form.build_id.data = build.id

    api_key_query = (
        models.ApiKey.query
        .filter_by(build_id=build.id)
        .order_by(models.ApiKey.created.desc())
        .limit(1000))

    revoke_form_list = []
    for api_key in api_key_query:
        form = forms.RevokeApiKeyForm()
        form.id.data = api_key.id
        form.build_id.data = build.id
        form.revoke.data = True
        revoke_form_list.append((api_key, form))

    return render_template(
        'view_api_keys.html',
        build=build,
        create_form=create_form,
        revoke_form_list=revoke_form_list)


@app.route('/api_keys.revoke', methods=['POST'])
@fresh_login_required
@build_access_required('build_id')
def revoke_api_key():
    """Form submission handler for revoking API keys."""
    build = g.build
    form = forms.RevokeApiKeyForm()
    if form.validate_on_submit():
        api_key = models.ApiKey.query.get(form.id.data)
        if api_key.build_id != build.id:
            logging.debug('User does not have access to API key=%r',
                          api_key.id)
            abort(403)

        api_key.active = False
        save_admin_log(build, revoked_api_key=True, message=api_key.id)

        db.session.add(api_key)
        db.session.commit()

        ops = operations.ApiKeyOps(api_key.id, api_key.secret)
        ops.evict()

    return redirect(url_for('manage_api_keys', build_id=build.id))


def claim_invitations(user):
    """Claims any pending invitations for the given user's email address."""
    # See if there are any build invitations present for the user with this
    # email address. If so, replace all those invitations with the real user.
    invitation_user_id = '%s:%s' % (
        models.User.EMAIL_INVITATION, user.email_address)
    invitation_user = models.User.query.get(invitation_user_id)
    if invitation_user:
        invited_build_list = list(invitation_user.builds)
        if not invited_build_list:
            return

        db.session.add(user)
        logging.debug('Found %d build admin invitations for id=%r, user=%r',
                      len(invited_build_list), invitation_user_id, user)

        for build in invited_build_list:
            build.owners.remove(invitation_user)
            if not build.is_owned_by(user.id):
                build.owners.append(user)
                logging.debug('Claiming invitation for build_id=%r', build.id)
                save_admin_log(build, invite_accepted=True)
            else:
                logging.debug('User already owner of build. '
                              'id=%r, build_id=%r', user.id, build.id)
            db.session.add(build)

        db.session.delete(invitation_user)
        db.session.commit()
        # Re-add the user to the current session so we can query with it.
        db.session.add(current_user)


@app.route('/admins', methods=['GET', 'POST'])
@fresh_login_required
@build_access_required('build_id')
def manage_admins():
    """Page for viewing and managing build admins."""
    build = g.build

    # Do not show cached data
    db.session.add(build)
    db.session.refresh(build)

    add_form = forms.AddAdminForm()
    if add_form.validate_on_submit():

        invitation_user_id = '%s:%s' % (
            models.User.EMAIL_INVITATION, add_form.email_address.data)

        invitation_user = models.User.query.get(invitation_user_id)
        if not invitation_user:
            invitation_user = models.User(
                id=invitation_user_id,
                email_address=add_form.email_address.data)
            db.session.add(invitation_user)

        db.session.add(build)
        db.session.add(invitation_user)
        db.session.refresh(build, lockmode='update')

        build.owners.append(invitation_user)
        save_admin_log(build, invited_new_admin=True,
                       message=invitation_user.email_address)

        db.session.commit()

        logging.info('Added user=%r as owner to build_id=%r',
                     invitation_user.id, build.id)
        return redirect(url_for('manage_admins', build_id=build.id))

    add_form.build_id.data = build.id

    revoke_form_list = []
    for user in build.owners:
        form = forms.RemoveAdminForm()
        form.user_id.data = user.id
        form.build_id.data = build.id
        form.revoke.data = True
        revoke_form_list.append((user, form))

    return render_template(
        'view_admins.html',
        build=build,
        add_form=add_form,
        revoke_form_list=revoke_form_list)


@app.route('/admins.revoke', methods=['POST'])
@fresh_login_required
@build_access_required('build_id')
def revoke_admin():
    """Form submission handler for revoking admin access to a build."""
    build = g.build
    form = forms.RemoveAdminForm()
    if form.validate_on_submit():
        user = models.User.query.get(form.user_id.data)
        if not user:
            logging.debug('User being revoked admin access does not exist.'
                          'id=%r, build_id=%r', form.user_id.data, build.id)
            abort(400)

        if user == current_user:
            logging.debug('User trying to remove themself as admin. '
                          'id=%r, build_id=%r', user.id, build.id)
            abort(400)

        db.session.add(build)
        db.session.add(user)
        db.session.refresh(build, lockmode='update')
        db.session.refresh(user, lockmode='update')

        user_is_owner = build.owners.filter_by(id=user.id)
        if not user_is_owner:
            logging.debug('User being revoked admin access is not owner. '
                          'id=%r, build_id=%r.', user.id, build.id)
            abort(400)

        build.owners.remove(user)
        save_admin_log(build, revoked_admin=True, message=user.email_address)

        db.session.commit()

        operations.UserOps(user.get_id()).evict()

    return redirect(url_for('manage_admins', build_id=build.id))


def save_admin_log(build, **kwargs):
    """Saves an action to the admin log."""
    message = kwargs.pop('message', None)
    release = kwargs.pop('release', None)
    run = kwargs.pop('run', None)

    if not len(kwargs) == 1:
        raise TypeError('Must specify a LOG_TYPE argument')

    log_enum = kwargs.keys()[0]
    log_type = getattr(models.AdminLog, log_enum.upper(), None)
    if not log_type:
        raise TypeError('Bad log_type argument: %s' % log_enum)

    if current_user.is_anonymous():
        user_id = None
    else:
        user_id = current_user.get_id()

    log = models.AdminLog(
        build_id=build.id,
        log_type=log_type,
        message=message,
        user_id=user_id)

    if release:
        log.release_id = release.id

    if run:
        log.run_id = run.id
        log.release_id = run.release_id

    db.session.add(log)


@app.route('/activity')
@fresh_login_required
@build_access_required('build_id')
def view_admin_log():
    """Page for viewing the log of admin activity."""
    build = g.build

    # TODO: Add paging

    log_list = (
        models.AdminLog.query
        .filter_by(build_id=build.id)
        .order_by(models.AdminLog.created.desc())
        .all())

    return render_template(
        'view_admin_log.html',
        build=build,
        log_list=log_list)

########NEW FILE########
__FILENAME__ = emails
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implements email sending for the API server and frontend."""

import logging

# Local libraries
from flask import render_template, request
from flask.ext.mail import Message
from flask.ext.login import current_user

# Local modules
from . import app
from . import mail
from dpxdt.server import models
from dpxdt.server import operations
from dpxdt.server import utils


def render_or_send(func, message):
    """Renders an email message for debugging or actually sends it."""
    if request.endpoint != func.func_name:
        mail.send(message)

    if (current_user.is_authenticated() and current_user.superuser):
        return render_template('debug_email.html', message=message)


@utils.ignore_exceptions
@app.route('/email/ready_for_review/<int:build_id>/'
           '<string:release_name>/<int:release_number>')
def send_ready_for_review(build_id, release_name, release_number):
    """Sends an email indicating that the release is ready for review."""
    build = models.Build.query.get(build_id)

    if not build.send_email:
        logging.debug(
            'Not sending ready for review email because build does not have '
            'email enabled. build_id=%r', build.id)
        return

    ops = operations.BuildOps(build_id)
    release, run_list, stats_dict, _ = ops.get_release(
        release_name, release_number)

    if not run_list:
        logging.debug(
            'Not sending ready for review email because there are '
            ' no runs. build_id=%r, release_name=%r, release_number=%d',
            build.id, release.name, release.number)
        return

    title = '%s: %s - Ready for review' % (build.name, release.name)

    email_body = render_template(
        'email_ready_for_review.html',
        build=build,
        release=release,
        run_list=run_list,
        stats_dict=stats_dict)

    recipients = []
    if build.email_alias:
        recipients.append(build.email_alias)
    else:
        for user in build.owners:
            recipients.append(user.email_address)

    if not recipients:
        logging.debug(
            'Not sending ready for review email because there are no '
            'recipients. build_id=%r, release_name=%r, release_number=%d',
            build.id, release.name, release.number)
        return

    message = Message(title, recipients=recipients)
    message.html = email_body

    logging.info('Sending ready for review email for build_id=%r, '
                 'release_name=%r, release_number=%d to %r',
                 build.id, release.name, release.number, recipients)

    return render_or_send(send_ready_for_review, message)

########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Forms for parsing and validating frontend requests."""

import datetime

# Local libraries
from flask.ext.wtf import (
    BooleanField, DataRequired, Email, Form, HiddenField, IntegerField,
    Length, NumberRange, Optional, Required, SubmitField, TextField)

# Local modules
from . import app


class BuildForm(Form):
    """Form for creating or editing a build."""

    name = TextField(validators=[Length(min=1, max=200)])


class ReleaseForm(Form):
    """Form for viewing or approving a release."""

    id = HiddenField(validators=[NumberRange(min=1)])
    name = HiddenField(validators=[Length(min=1, max=200)])
    number = HiddenField(validators=[NumberRange(min=1)])

    good = HiddenField()
    bad = HiddenField()
    reviewing = HiddenField()


class RunForm(Form):
    """Form for viewing or approving a run."""

    id = HiddenField(validators=[NumberRange(min=1)])
    name = HiddenField(validators=[Length(min=1, max=200)])
    number = HiddenField(validators=[NumberRange(min=1)])
    test = HiddenField(validators=[Length(min=1, max=200)])
    type = HiddenField(validators=[Length(min=1, max=200)])
    approve = HiddenField()
    disapprove = HiddenField()


class CreateApiKeyForm(Form):
    """Form for creating an API key."""

    build_id = HiddenField(validators=[NumberRange(min=1)])
    purpose = TextField('Purpose', validators=[Length(min=1, max=200)])
    create = SubmitField('Create')


class RevokeApiKeyForm(Form):
    """Form for revoking an API key."""

    id = HiddenField()
    build_id = HiddenField(validators=[NumberRange(min=1)])
    revoke = SubmitField('Revoke')


class AddAdminForm(Form):
    """Form for adding a build admin."""

    email_address = TextField('Email address',
                              validators=[Length(min=1, max=200)])
    build_id = HiddenField(validators=[NumberRange(min=1)])
    add = SubmitField('Add')


class RemoveAdminForm(Form):
    """Form for removing a build admin."""

    user_id = HiddenField(validators=[Length(min=1, max=200)])
    build_id = HiddenField(validators=[NumberRange(min=1)])
    revoke = SubmitField('Revoke')


class ModifyWorkQueueTaskForm(Form):
    """Form for modifying a work queue task."""

    task_id = HiddenField()
    action = HiddenField()
    delete = SubmitField('Delete')
    retry = SubmitField('Retry')


class SettingsForm(Form):
    """Form for modifying build settings."""

    name = TextField(validators=[Length(min=1, max=200)])
    send_email = BooleanField('Send notification emails')
    email_alias = TextField('Mailing list for notifications',
                            validators=[Optional(), Email()])
    build_id = HiddenField(validators=[NumberRange(min=1)])
    save = SubmitField('Save')

########NEW FILE########
__FILENAME__ = frontend
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Frontend for the API server."""

import base64
import datetime
import hashlib
import logging

# Local libraries
import flask
from flask import Flask, abort, g, redirect, render_template, request, url_for
from flask.ext.login import (
    current_user, fresh_login_required, login_fresh, login_required)
from flask.ext.wtf import Form

# Local modules
from . import app
from . import db
from . import login
from dpxdt.server import auth
from dpxdt.server import forms
from dpxdt.server import models
from dpxdt.server import operations
from dpxdt.server import signals
from dpxdt.server import utils


@app.context_processor
def frontend_context():
    """Adds extra default context for rendered templates."""
    return dict(cache_buster=utils.get_deployment_timestamp())


@app.route('/')
def homepage():
    """Renders the homepage."""
    if current_user.is_authenticated():
        if not login_fresh():
            logging.debug('User needs a fresh token')
            abort(login.needs_refresh())

        auth.claim_invitations(current_user)

    build_list = operations.UserOps(current_user.get_id()).get_builds()

    return render_template(
        'home.html',
        build_list=build_list)


@app.route('/new', methods=['GET', 'POST'])
@fresh_login_required
def new_build():
    """Page for crediting or editing a build."""
    form = forms.BuildForm()
    if form.validate_on_submit():
        build = models.Build()
        form.populate_obj(build)
        build.owners.append(current_user)

        db.session.add(build)
        db.session.flush()

        auth.save_admin_log(build, created_build=True, message=build.name)

        db.session.commit()

        operations.UserOps(current_user.get_id()).evict()

        logging.info('Created build via UI: build_id=%r, name=%r',
                     build.id, build.name)
        return redirect(url_for('view_build', id=build.id))

    return render_template(
        'new_build.html',
        build_form=form)


@app.route('/build')
@auth.build_access_required
def view_build():
    """Page for viewing all releases in a build."""
    build = g.build
    page_size = 20
    offset = request.args.get('offset', 0, type=int)

    ops = operations.BuildOps(build.id)
    has_next_page, candidate_list, stats_counts = ops.get_candidates(
        page_size, offset)

    # Collate by release name, order releases by latest creation. Init stats.
    release_dict = {}
    created_dict = {}
    run_stats_dict = {}
    for candidate in candidate_list:
        release_list = release_dict.setdefault(candidate.name, [])
        release_list.append(candidate)
        max_created = created_dict.get(candidate.name, candidate.created)
        created_dict[candidate.name] = max(candidate.created, max_created)
        run_stats_dict[candidate.id] = dict(
            runs_total=0,
            runs_complete=0,
            runs_successful=0,
            runs_failed=0,
            runs_baseline=0,
            runs_pending=0)

    # Sort each release by candidate number descending
    for release_list in release_dict.itervalues():
        release_list.sort(key=lambda x: x.number, reverse=True)

    # Sort all releases by created time descending
    release_age_list = [
        (value, key) for key, value in created_dict.iteritems()]
    release_age_list.sort(reverse=True)
    release_name_list = [key for _, key in release_age_list]

    # Count totals for each run state within that release.
    for candidate_id, status, count in stats_counts:
        stats_dict = run_stats_dict[candidate_id]
        for key in ops.get_stats_keys(status):
            stats_dict[key] += count

    return render_template(
        'view_build.html',
        build=build,
        release_name_list=release_name_list,
        release_dict=release_dict,
        run_stats_dict=run_stats_dict,
        has_next_page=has_next_page,
        current_offset=offset,
        next_offset=offset + page_size,
        last_offset=max(0, offset -  page_size))


@app.route('/release', methods=['GET', 'POST'])
@auth.build_access_required
def view_release():
    """Page for viewing all tests runs in a release."""
    build = g.build
    if request.method == 'POST':
        form = forms.ReleaseForm(request.form)
    else:
        form = forms.ReleaseForm(request.args)

    form.validate()

    ops = operations.BuildOps(build.id)
    release, run_list, stats_dict, approval_log = ops.get_release(
        form.name.data, form.number.data)

    if not release:
        abort(404)

    if request.method == 'POST':
        decision_states = (
            models.Release.REVIEWING,
            models.Release.RECEIVING,
            models.Release.PROCESSING)

        if form.good.data and release.status in decision_states:
            release.status = models.Release.GOOD
            auth.save_admin_log(build, release_good=True, release=release)
        elif form.bad.data and release.status in decision_states:
            release.status = models.Release.BAD
            auth.save_admin_log(build, release_bad=True, release=release)
        elif form.reviewing.data and release.status in (
                models.Release.GOOD, models.Release.BAD):
            release.status = models.Release.REVIEWING
            auth.save_admin_log(build, release_reviewing=True, release=release)
        else:
            logging.warning(
                'Bad state transition for name=%r, number=%r, form=%r',
                release.name, release.number, form.data)
            abort(400)

        db.session.add(release)
        db.session.commit()

        ops.evict()

        return redirect(url_for(
            'view_release',
            id=build.id,
            name=release.name,
            number=release.number))

    # Update form values for rendering
    form.good.data = True
    form.bad.data = True
    form.reviewing.data = True

    return render_template(
        'view_release.html',
        build=build,
        release=release,
        run_list=run_list,
        release_form=form,
        approval_log=approval_log,
        stats_dict=stats_dict)


def _get_artifact_context(run, file_type):
    """Gets the artifact details for the given run and file_type."""
    sha1sum = None
    image_file = False
    log_file = False
    config_file = False

    if request.path == '/image':
        image_file = True
        if file_type == 'before':
            sha1sum = run.ref_image
        elif file_type == 'diff':
            sha1sum = run.diff_image
        elif file_type == 'after':
            sha1sum = run.image
        else:
            abort(400)
    elif request.path == '/log':
        log_file = True
        if file_type == 'before':
            sha1sum = run.ref_log
        elif file_type == 'diff':
            sha1sum = run.diff_log
        elif file_type == 'after':
            sha1sum = run.log
        else:
            abort(400)
    elif request.path == '/config':
        config_file = True
        if file_type == 'before':
            sha1sum = run.ref_config
        elif file_type == 'after':
            sha1sum = run.config
        else:
            abort(400)

    return image_file, log_file, config_file, sha1sum


@app.route('/run', methods=['GET', 'POST'])
@app.route('/image', endpoint='view_image', methods=['GET', 'POST'])
@app.route('/log', endpoint='view_log', methods=['GET', 'POST'])
@app.route('/config', endpoint='view_config', methods=['GET', 'POST'])
@auth.build_access_required
def view_run():
    """Page for viewing before/after for a specific test run."""
    build = g.build
    if request.method == 'POST':
        form = forms.RunForm(request.form)
    else:
        form = forms.RunForm(request.args)

    form.validate()

    ops = operations.BuildOps(build.id)
    run, next_run, previous_run, approval_log = ops.get_run(
        form.name.data, form.number.data, form.test.data)

    if not run:
        abort(404)

    file_type = form.type.data
    image_file, log_file, config_file, sha1sum = (
        _get_artifact_context(run, file_type))

    if request.method == 'POST':
        if form.approve.data and run.status == models.Run.DIFF_FOUND:
            run.status = models.Run.DIFF_APPROVED
            auth.save_admin_log(build, run_approved=True, run=run)
        elif form.disapprove.data and run.status == models.Run.DIFF_APPROVED:
            run.status = models.Run.DIFF_FOUND
            auth.save_admin_log(build, run_rejected=True, run=run)
        else:
            abort(400)

        db.session.add(run)
        db.session.commit()

        ops.evict()

        return redirect(url_for(
            request.endpoint,
            id=build.id,
            name=run.release.name,
            number=run.release.number,
            test=run.name,
            type=file_type))

    # Update form values for rendering
    form.approve.data = True
    form.disapprove.data = True

    context = dict(
        build=build,
        release=run.release,
        run=run,
        run_form=form,
        previous_run=previous_run,
        next_run=next_run,
        file_type=file_type,
        image_file=image_file,
        log_file=log_file,
        config_file=config_file,
        sha1sum=sha1sum,
        approval_log=approval_log)

    if file_type:
        template_name = 'view_artifact.html'
    else:
        template_name = 'view_run.html'

    response = flask.Response(render_template(template_name, **context))

    return response


@app.route('/settings', methods=['GET', 'POST'])
@auth.build_access_required('build_id')
def build_settings():
    build = g.build

    settings_form = forms.SettingsForm()

    if settings_form.validate_on_submit():
        settings_form.populate_obj(build)

        message = ('name=%s, send_email=%s, email_alias=%s' % (
            build.name, build.send_email, build.email_alias))
        auth.save_admin_log(build, changed_settings=True, message=message)

        db.session.add(build)
        db.session.commit()

        signals.build_updated.send(app, build=build, user=current_user)

        return redirect(url_for(
            request.endpoint,
            build_id=build.id))

    # Update form values for rendering
    settings_form.name.data = build.name
    settings_form.build_id.data = build.id
    settings_form.email_alias.data = build.email_alias
    settings_form.send_email.data = build.send_email

    return render_template(
        'view_settings.html',
        build=build,
        settings_form=settings_form)

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Models for managing screenshots and incremental perceptual diffs."""

import datetime

# Local modules
from . import app
from . import db


class User(db.Model):
    """Represents a user who is authenticated in the system.

    Primary key is prefixed with a valid AUTH_TYPES like:

        'google_oauth2:1234567890'
    """

    EMAIL_INVITATION = 'email_invitation'
    GOOGLE_OAUTH2 = 'google_oauth2'
    AUTH_TYPES = frozenset([EMAIL_INVITATION, GOOGLE_OAUTH2])

    id = db.Column(db.String(255), primary_key=True)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    email_address = db.Column(db.String(255))
    superuser = db.Column(db.Boolean, default=False)

    def get_auth_type(self):
        return self.id.split(':', 1)[0]

    # For flask-cache memoize key.
    def __repr__(self):
        return 'User(id=%r)' % self.get_id()

    # Methods required by flask-login.
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __eq__(self, other):
        return other.id == self.id

    def __ne__(self, other):
        return other.id != self.id


class ApiKey(db.Model):
    """API access for an automated system."""

    id = db.Column(db.String(255), primary_key=True)
    secret = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True)
    purpose = db.Column(db.String(255))
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                         onupdate=datetime.datetime.utcnow)
    revoked = db.Column(db.DateTime)
    superuser = db.Column(db.Boolean, default=False)
    build_id = db.Column(db.Integer, db.ForeignKey('build.id'))


ownership_table = db.Table(
    'build_ownership',
    db.Column('build_id', db.Integer, db.ForeignKey('build.id')),
    db.Column('user_id', db.String(255), db.ForeignKey('user.id')))


class Build(db.Model):
    """A single repository of artifacts and diffs owned by someone."""

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                         onupdate=datetime.datetime.utcnow)
    name = db.Column(db.String(255))
    public = db.Column(db.Boolean, default=False)
    owners = db.relationship('User', secondary=ownership_table,
                             backref=db.backref('builds', lazy='dynamic'),
                             lazy='dynamic')
    send_email = db.Column(db.Boolean, default=True)
    email_alias = db.Column(db.String(255))

    def is_owned_by(self, user_id):
        return self.owners.filter_by(id=user_id).first() is not None

    # For flask-cache memoize key.
    def __repr__(self):
        return 'Build(id=%r)' % self.id


class Release(db.Model):
    """A set of runs in a build, grouped by user-supplied name."""

    RECEIVING = 'receiving'
    PROCESSING = 'processing'
    REVIEWING = 'reviewing'
    BAD = 'bad'
    GOOD = 'good'
    STATES = frozenset([RECEIVING, PROCESSING, REVIEWING, BAD, GOOD])

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                         onupdate=datetime.datetime.utcnow)
    status = db.Column(db.Enum(*STATES), default=RECEIVING, nullable=False)
    build_id = db.Column(db.Integer, db.ForeignKey('build.id'), nullable=False)
    url = db.Column(db.String(2048))

    # For flask-cache memoize key.
    def __repr__(self):
        return 'Release(id=%r)' % self.id


artifact_ownership_table = db.Table(
    'artifact_ownership',
    db.Column('artifact', db.String(100), db.ForeignKey('artifact.id')),
    db.Column('build_id', db.Integer, db.ForeignKey('build.id')))


class Artifact(db.Model):
    """Contains a single file uploaded by a diff worker."""

    id = db.Column(db.String(100), primary_key=True)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    data = db.Column(db.LargeBinary(length=2**31))
    alternate = db.Column(db.Text)
    content_type = db.Column(db.String(255))
    owners = db.relationship('Build', secondary=artifact_ownership_table,
                             backref=db.backref('artifacts', lazy='dynamic'),
                             lazy='dynamic')


class Run(db.Model):
    """Contains a set of screenshot records uploaded by a diff worker."""

    DATA_PENDING = 'data_pending'
    DIFF_APPROVED = 'diff_approved'
    DIFF_FOUND = 'diff_found'
    DIFF_NOT_FOUND = 'diff_not_found'
    FAILED = 'failed'
    NEEDS_DIFF = 'needs_diff'
    NO_DIFF_NEEDED = 'no_diff_needed'

    STATES = frozenset([
        DATA_PENDING, DIFF_APPROVED, DIFF_FOUND, DIFF_NOT_FOUND,
        FAILED, NEEDS_DIFF, NO_DIFF_NEEDED])

    DIFF_NEEDED_STATES = frozenset([DIFF_FOUND, DIFF_APPROVED])

    id = db.Column(db.Integer, primary_key=True)
    release_id = db.Column(db.Integer, db.ForeignKey('release.id'))
    release = db.relationship('Release',
                              backref=db.backref('runs', lazy='select'),
                              lazy='joined',
                              join_depth=1)

    name = db.Column(db.String(255), nullable=False)
    # TODO: Put rigid DB constraint on uniqueness of (release_id, name)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                         onupdate=datetime.datetime.utcnow)
    status = db.Column(db.Enum(*STATES), nullable=False)

    image = db.Column(db.String(100), db.ForeignKey('artifact.id'))
    log = db.Column(db.String(100), db.ForeignKey('artifact.id'))
    config = db.Column(db.String(100), db.ForeignKey('artifact.id'))
    url = db.Column(db.String(2048))

    ref_image = db.Column(db.String(100), db.ForeignKey('artifact.id'))
    ref_log = db.Column(db.String(100), db.ForeignKey('artifact.id'))
    ref_config = db.Column(db.String(100), db.ForeignKey('artifact.id'))
    ref_url = db.Column(db.String(2048))

    diff_image = db.Column(db.String(100), db.ForeignKey('artifact.id'))
    diff_log = db.Column(db.String(100), db.ForeignKey('artifact.id'))
    distortion = db.Column(db.Float())

    tasks = db.relationship('WorkQueue',
                            backref=db.backref('runs', lazy='select'),
                            lazy='joined',
                            join_depth=1,
                            order_by='WorkQueue.created')

    # For flask-cache memoize key.
    def __repr__(self):
        return 'Run(id=%r)' % self.id


class AdminLog(db.Model):
    """Log of admin user actions for a build."""

    CHANGED_SETTINGS = 'changed_settings'
    CREATED_API_KEY = 'created_api_key'
    CREATED_BUILD = 'created_build'
    INVITE_ACCEPTED = 'invite_accepted'
    INVITED_NEW_ADMIN = 'invited_new_admin'
    REVOKED_ADMIN = 'revoked_admin'
    REVOKED_API_KEY = 'revoked_api_key'
    RUN_APPROVED = 'run_approved'
    RUN_REJECTED = 'run_rejected'
    RELEASE_BAD = 'release_bad'
    RELEASE_GOOD = 'release_good'
    RELEASE_REVIEWING = 'release_reviewing'

    LOG_TYPES = frozenset([
        CHANGED_SETTINGS, CREATED_API_KEY, CREATED_BUILD, INVITE_ACCEPTED,
        INVITED_NEW_ADMIN, REVOKED_ADMIN, REVOKED_API_KEY, RUN_APPROVED,
        RUN_REJECTED, RELEASE_BAD, RELEASE_GOOD, RELEASE_REVIEWING])

    id = db.Column(db.Integer, primary_key=True)
    build_id = db.Column(db.Integer, db.ForeignKey('build.id'), nullable=False)

    release_id = db.Column(db.Integer, db.ForeignKey('release.id'))
    release = db.relationship('Release', lazy='joined', join_depth=2)

    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    run = db.relationship('Run', lazy='joined', join_depth=1)

    user_id = db.Column(db.String(255), db.ForeignKey('user.id'))
    user = db.relationship('User', lazy='joined', join_depth=1)

    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    log_type = db.Column(db.Enum(*LOG_TYPES), nullable=False)
    message = db.Column(db.Text)

    # For flask-cache memoize key.
    def __repr__(self):
        return 'AdminLog(id=%r)' % self.id

########NEW FILE########
__FILENAME__ = operations
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Cacheable operations and eviction for models in the frontend."""

import functools
import logging

# Local libraries
import sqlalchemy

# Local modules
from . import app
from . import cache
from . import db
from dpxdt.server import models
from dpxdt.server import signals
from dpxdt.server import utils
from dpxdt.server import work_queue


class UserOps(object):
    """Cacheable operations for user-specific information."""

    def __init__(self, user_id):
        self.user_id = user_id

    # For Flask-Cache keys
    def __repr__(self):
        return 'caching.UserOps(user_id=%r)' % self.user_id

    @cache.memoize(per_instance=True)
    def load(self):
        if not self.user_id:
            return None
        user = models.User.query.get(self.user_id)
        if user:
            db.session.expunge(user)
        return user

    @cache.memoize(per_instance=True)
    def get_builds(self):
        if self.user_id:
            user = models.User.query.get(self.user_id)
            build_list = (
                user.builds
                .order_by(models.Build.created.desc())
                .limit(1000)
                .all())
        else:
            # Anonymous users see only public builds
            build_list = (
                models.Build.query
                .filter_by(public=True)
                .order_by(models.Build.created.desc())
                .limit(1000)
                .all())

        for build in build_list:
            db.session.expunge(build)

        return build_list

    @cache.memoize(per_instance=True)
    def owns_build(self, build_id):
        build = models.Build.query.get(build_id)
        user_is_owner = False
        if build:
            user_is_owner = build.is_owned_by(self.user_id)
            db.session.expunge(build)

        return build, user_is_owner

    def evict(self):
        """Evict all caches related to this user."""
        logging.debug('Evicting cache for %r', self)
        cache.delete_memoized(self.load)
        cache.delete_memoized(self.get_builds)
        cache.delete_memoized(self.owns_build)


class ApiKeyOps(object):
    """Cacheable operations for API key-specific information."""

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    # For Flask-Cache keys
    def __repr__(self):
        return 'caching.ApiKeyOps(client_id=%r)' % self.client_id

    @cache.memoize(per_instance=True)
    def get(self):
        api_key = models.ApiKey.query.get(self.client_id)
        utils.jsonify_assert(api_key, 'API key must exist', 403)
        utils.jsonify_assert(api_key.active, 'API key must be active', 403)
        utils.jsonify_assert(api_key.secret == self.client_secret,
                             'Must have good credentials', 403)
        return api_key

    @cache.memoize(per_instance=True)
    def can_access_build(self, build_id):
        api_key = self.get()

        build = models.Build.query.get(build_id)
        utils.jsonify_assert(build is not None, 'build must exist', 404)

        if not api_key.superuser:
            utils.jsonify_assert(api_key.build_id == build_id,
                                 'API key must have access', 404)

        return api_key, build

    def evict(self):
        """Evict all caches related to this API key."""
        logging.debug('Evicting cache for %r', self)
        cache.delete_memoized(self.get)
        cache.delete_memoized(self.can_access_build)


class BuildOps(object):
    """Cacheable operations for build-specific operations."""

    def __init__(self, build_id):
        self.build_id = build_id

    # For Flask-Cache keys
    def __repr__(self):
        return 'caching.BuildOps(build_id=%r)' % self.build_id

    @staticmethod
    def sort_run(run):
        """Sort function for runs within a release."""
        # Sort errors first, then by name. Also show errors that were manually
        # approved, so the paging sort order stays the same even after users
        # approve a diff on the run page.
        if run.status in models.Run.DIFF_NEEDED_STATES:
            return (0, run.name)
        return (1, run.name)

    @staticmethod
    def get_stats_keys(status):
        if status in (models.Run.DIFF_APPROVED,
                      models.Run.DIFF_NOT_FOUND):
            return ('runs_successful', 'runs_complete', 'runs_total')
        elif status in models.Run.DIFF_FOUND:
            return ('runs_failed', 'runs_complete', 'runs_total')
        elif status == models.Run.NO_DIFF_NEEDED:
            return ('runs_baseline',)
        elif status == models.Run.NEEDS_DIFF:
            return ('runs_total', 'runs_pending')
        elif status == models.Run.FAILED:
            return ('runs_failed',)
        return ('runs_pending',)

    @cache.memoize(per_instance=True)
    def get_candidates(self, page_size, offset):
        candidate_list = (
            models.Release.query
            .filter_by(build_id=self.build_id)
            .order_by(models.Release.created.desc())
            .offset(offset)
            .limit(page_size + 1)
            .all())

        stats_counts = []

        has_next_page = len(candidate_list) > page_size
        if has_next_page:
            candidate_list = candidate_list[:-1]

        if candidate_list:
            candidate_keys = [c.id for c in candidate_list]
            stats_counts = (
                db.session.query(
                    models.Run.release_id,
                    models.Run.status,
                    sqlalchemy.func.count(models.Run.id))
                .join(models.Release)
                .filter(models.Release.id.in_(candidate_keys))
                .group_by(models.Run.status, models.Run.release_id)
                .all())

        for candidate in candidate_list:
            db.session.expunge(candidate)

        return has_next_page, candidate_list, stats_counts

    @cache.memoize(per_instance=True)
    def get_release(self, release_name, release_number):
        release = (
            models.Release.query
            .filter_by(
                build_id=self.build_id,
                name=release_name,
                number=release_number)
            .first())

        if not release:
            return None, None, None, None

        run_list = list(release.runs)
        run_list.sort(key=BuildOps.sort_run)

        stats_dict = dict(
            runs_total=0,
            runs_complete=0,
            runs_successful=0,
            runs_failed=0,
            runs_baseline=0,
            runs_pending=0)
        for run in run_list:
            for key in self.get_stats_keys(run.status):
                stats_dict[key] += 1

        approval_log = None
        if release.status in (models.Release.GOOD, models.Release.BAD):
            approval_log = (
                models.AdminLog.query
                .filter_by(release_id=release.id)
                .filter(models.AdminLog.log_type.in_(
                    (models.AdminLog.RELEASE_BAD,
                     models.AdminLog.RELEASE_GOOD)))
                .order_by(models.AdminLog.created.desc())
                .first())

        for run in run_list:
            db.session.expunge(run)

        if approval_log:
            db.session.expunge(approval_log)

        return release, run_list, stats_dict, approval_log

    def _get_next_previous_runs(self, run):
        next_run = None
        previous_run = None

        # We sort the runs in the release by diffs first, then by name.
        # Simulate that behavior here with multiple queries.
        if run.status in models.Run.DIFF_NEEDED_STATES:
            previous_run = (
                models.Run.query
                .filter_by(release_id=run.release_id)
                .filter(models.Run.status.in_(models.Run.DIFF_NEEDED_STATES))
                .filter(models.Run.name < run.name)
                .order_by(models.Run.name.desc())
                .first())
            next_run = (
                models.Run.query
                .filter_by(release_id=run.release_id)
                .filter(models.Run.status.in_(models.Run.DIFF_NEEDED_STATES))
                .filter(models.Run.name > run.name)
                .order_by(models.Run.name)
                .first())

            if not next_run:
                next_run = (
                    models.Run.query
                    .filter_by(release_id=run.release_id)
                    .filter(
                        ~models.Run.status.in_(models.Run.DIFF_NEEDED_STATES))
                    .order_by(models.Run.name)
                    .first())
        else:
            previous_run = (
                models.Run.query
                .filter_by(release_id=run.release_id)
                .filter(~models.Run.status.in_(models.Run.DIFF_NEEDED_STATES))
                .filter(models.Run.name < run.name)
                .order_by(models.Run.name.desc())
                .first())
            next_run = (
                models.Run.query
                .filter_by(release_id=run.release_id)
                .filter(~models.Run.status.in_(models.Run.DIFF_NEEDED_STATES))
                .filter(models.Run.name > run.name)
                .order_by(models.Run.name)
                .first())

            if not previous_run:
                previous_run = (
                    models.Run.query
                    .filter_by(release_id=run.release_id)
                    .filter(
                        models.Run.status.in_(models.Run.DIFF_NEEDED_STATES))
                    .order_by(models.Run.name.desc())
                    .first())

        return next_run, previous_run

    @cache.memoize(per_instance=True)
    def get_run(self, release_name, release_number, test_name):
        run = (
            models.Run.query
            .join(models.Release)
            .filter(models.Release.name == release_name)
            .filter(models.Release.number == release_number)
            .filter(models.Run.name == test_name)
            .first())
        if not run:
            return None, None, None, None

        next_run, previous_run = self._get_next_previous_runs(run)

        approval_log = None
        if run.status == models.Run.DIFF_APPROVED:
            approval_log = (
                models.AdminLog.query
                .filter_by(run_id=run.id,
                           log_type=models.AdminLog.RUN_APPROVED)
                .order_by(models.AdminLog.created.desc())
                .first())

        if run:
            db.session.expunge(run)
        if next_run:
            db.session.expunge(next_run)
        if previous_run:
            db.session.expunge(previous_run)
        if approval_log:
            db.session.expunge(approval_log)

        return run, next_run, previous_run, approval_log

    def evict(self):
        """Evict all caches relating to this build."""
        logging.debug('Evicting cache for %r', self)
        cache.delete_memoized(self.get_candidates)
        cache.delete_memoized(self.get_release)
        cache.delete_memoized(self.get_run)



# Connect Frontend and API events to cache eviction.


def _evict_user_cache(sender, user=None, build=None):
    UserOps(user.get_id()).evict()


def _evict_build_cache(sender, build=None, release=None, run=None):
    BuildOps(build.id).evict()


def _evict_task_cache(sender, task=None):
    if not task.run_id:
        return
    run = models.Run.query.get(task.run_id)
    # Update the modification time on the run, since the task status changed.
    db.session.add(run)
    BuildOps(run.release.build_id).evict()


signals.build_updated.connect(_evict_user_cache, app)
signals.release_updated_via_api.connect(_evict_build_cache, app)
signals.run_updated_via_api.connect(_evict_build_cache, app)
signals.task_updated.connect(_evict_task_cache, app)

########NEW FILE########
__FILENAME__ = signals
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Signals for frontend and API server requests."""


# Local modules
from blinker import Namespace


_signals = Namespace()


# The build settings have been modified. Sender is the app. Arguments
# are (models.Build, models.User). Signal is sent immediately *after* the
# Build is committed to the DB.
build_updated = _signals.signal('build-updated')


# A release has been created or updated via the API. Sender is the app.
# Arguments are (models.Build, models.Release). Signal is sent immediately
# *after* the Release is committed to the DB.
release_updated_via_api = _signals.signal('release-update')


# A run has been created or updated via the API. Sender is the app. Arguments
# are (models.Build, models.Release, models.Run). Signal is sent immediately
# *after* the Run is committed to the DB.
run_updated_via_api = _signals.signal('run-updated')

# A WorkQueue task's status has been updated via the API. Sender is the app.
# Argument is (work_queue.WorkQueue). Signal is sent immediately after the
# task is updated but before it is committed to the DB.
task_updated = _signals.signal('task-updated')

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common utility functions."""

import base64
import datetime
import hashlib
import functools
import logging
import os
import traceback
import uuid

# Local libraries
import flask
from flask import abort, g, jsonify
from sqlalchemy.exc import OperationalError

# Local modules
from . import app
from . import db


def retryable_transaction(attempts=3, exceptions=(OperationalError,)):
    """Decorator retries a function when expected exceptions are raised."""
    assert len(exceptions) > 0
    assert attempts > 0

    def wrapper(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            for i in xrange(attempts):
                try:
                    return f(*args, **kwargs)
                except exceptions, e:
                    if i == (attempts - 1):
                        raise
                    logging.warning(
                        'Retryable error in transaction on attempt %d. %s: %s',
                        i + 1, e.__class__.__name__, e)
                    db.session.rollback()

        return wrapped

    return wrapper


def jsonify_assert(asserted, message, status_code=400):
    """Asserts something is true, aborts the request if not."""
    if asserted:
        return
    try:
        raise AssertionError(message)
    except AssertionError, e:
        stack = traceback.extract_stack()
        stack.pop()
        logging.error('Assertion failed: %s\n%s',
                      str(e), ''.join(traceback.format_list(stack)))
        abort(jsonify_error(e, status_code=status_code))


def jsonify_error(message_or_exception, status_code=400):
    """Returns a JSON payload that indicates the request had an error."""
    if isinstance(message_or_exception, Exception):
        message = '%s: %s' % (
            message_or_exception.__class__.__name__, message_or_exception)
    else:
        message = message_or_exception

    logging.debug('Returning status=%d, error message: %s',
                  status_code, message)
    response = jsonify(error=message)
    response.status_code = status_code
    return response


def ignore_exceptions(f):
    """Decorator catches and ignores any exceptions raised by this function."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            logging.exception("Ignoring exception in %r", f)
    return wrapped


# Based on http://flask.pocoo.org/snippets/33/
@app.template_filter()
def timesince(when):
    """Returns string representing "time since" or "time until".

    Examples:
        3 days ago, 5 hours ago, 3 minutes from now, 5 hours from now, now.
    """
    if not when:
        return ''

    now = datetime.datetime.utcnow()
    if now > when:
        diff = now - when
        suffix = 'ago'
    else:
        diff = when - now
        suffix = 'from now'

    periods = (
        (diff.days / 365, 'year', 'years'),
        (diff.days / 30, 'month', 'months'),
        (diff.days / 7, 'week', 'weeks'),
        (diff.days, 'day', 'days'),
        (diff.seconds / 3600, 'hour', 'hours'),
        (diff.seconds / 60, 'minute', 'minutes'),
        (diff.seconds, 'second', 'seconds'),
    )

    for period, singular, plural in periods:
        if period:
            return '%d %s %s' % (
                period,
                singular if period == 1 else plural,
                suffix)

    return 'now'


def human_uuid():
    """Returns a good UUID for using as a human readable string."""
    return base64.b32encode(
        hashlib.sha1(uuid.uuid4().bytes).digest()).lower().strip('=')


def password_uuid():
    """Returns a good UUID for using as a password."""
    return base64.b64encode(
        hashlib.sha1(uuid.uuid4().bytes).digest()).strip('=')


def is_production():
    """Returns True if this is the production environment."""
    # TODO: Support other deployment situations.
    return (
        os.environ.get('SERVER_SOFTWARE', '').startswith('Google App Engine'))


def get_deployment_timestamp():
    """Returns a unique string represeting the current deployment.

    Used for busting caches.
    """
    # TODO: Support other deployment situations.
    if os.environ.get('SERVER_SOFTWARE', '').startswith('Google App Engine'):
        version_id = os.environ.get('CURRENT_VERSION_ID')
        major_version, timestamp = version_id.split('.', 1)
        return timestamp
    return 'test'


# From http://flask.pocoo.org/snippets/53/
def after_this_request(func):
    if not hasattr(g, 'call_after_request'):
        g.call_after_request = []
    g.call_after_request.append(func)
    return func


def per_request_callbacks(sender, response):
    for func in getattr(g, 'call_after_request', ()):
        response = func(response)
    return response


# Do this with signals instead of @app.after_request because the session
# cookie is added to the response *after* "after_request" callbacks run.
flask.request_finished.connect(per_request_callbacks, app)

########NEW FILE########
__FILENAME__ = work_queue
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pull-queue API."""

import datetime
import json
import logging
import time
import uuid

# Local modules
from . import app
from . import db
from dpxdt.server import signals


class Error(Exception):
    """Base class for exceptions in this module."""

class TaskDoesNotExistError(Error):
    """Task with the given ID does not exist and cannot be finished."""

class LeaseExpiredError(Error):
    """Owner's lease on the task has expired, not completing task."""

class NotOwnerError(Error):
    """Requestor is no longer the owner of the task."""


class WorkQueue(db.Model):
    """Represents a single item of work to do in a specific queue.

    Queries:
    - By task_id for finishing a task or extending a lease.
    - By Index(queue_name, status, eta) for finding the oldest task for a queue
        that is still pending.
    - By Index(status, create) for finding old tasks that should be deleted
        from the table periodically to free up space.
    """

    CANCELED = 'canceled'
    DONE = 'done'
    ERROR = 'error'
    LIVE = 'live'
    STATES = frozenset([CANCELED, DONE, ERROR, LIVE])

    task_id = db.Column(db.String(100), primary_key=True, nullable=False)
    queue_name = db.Column(db.String(100), primary_key=True, nullable=False)
    status = db.Column(db.Enum(*STATES), default=LIVE, nullable=False)
    eta = db.Column(db.DateTime, default=datetime.datetime.utcnow,
                    nullable=False)

    build_id = db.Column(db.Integer, db.ForeignKey('build.id'))
    release_id = db.Column(db.Integer, db.ForeignKey('release.id'))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))

    source = db.Column(db.String(500))
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    finished = db.Column(db.DateTime)

    lease_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_lease = db.Column(db.DateTime)
    last_owner = db.Column(db.String(500))

    heartbeat = db.Column(db.Text)
    heartbeat_number = db.Column(db.Integer)

    payload = db.Column(db.LargeBinary)
    content_type = db.Column(db.String(100))

    __table_args__ = (
        db.Index('created_index', 'queue_name', 'status', 'created'),
        db.Index('lease_index', 'queue_name', 'status', 'eta'),
        db.Index('reap_index', 'status', 'created'),
    )

    @property
    def lease_outstanding(self):
        if not self.status == WorkQueue.LIVE:
            return False
        if not self.last_owner:
            return False
        now = datetime.datetime.utcnow()
        return now < self.eta


def add(queue_name, payload=None, content_type=None, source=None, task_id=None,
        build_id=None, release_id=None, run_id=None):
    """Adds a work item to a queue.

    Args:
        queue_name: Name of the queue to add the work item to.
        payload: Optional. Payload that describes the work to do as a string.
            If not a string and content_type is not provided, then this
            function assumes the payload is a JSON-able Python object.
        content_type: Optional. Content type of the payload.
        source: Optional. Who or what originally created the task.
        task_id: Optional. When supplied, only enqueue this task if a task
            with this ID does not already exist. If a task with this ID already
            exists, then this function will do nothing.
        build_id: Build ID to associate with this task. May be None.
        release_id: Release ID to associate with this task. May be None.
        run_id: Run ID to associate with this task. May be None.

    Returns:
        ID of the task that was added.
    """
    if task_id:
        task = WorkQueue.query.filter_by(task_id=task_id).first()
        if task:
            return task.task_id
    else:
        task_id = uuid.uuid4().hex

    if payload and not content_type and not isinstance(payload, basestring):
        payload = json.dumps(payload)
        content_type = 'application/json'

    now = datetime.datetime.utcnow()
    task = WorkQueue(
        task_id=task_id,
        queue_name=queue_name,
        eta=now,
        source=source,
        build_id=build_id,
        release_id=release_id,
        run_id=run_id,
        payload=payload,
        content_type=content_type)
    db.session.add(task)

    return task.task_id


def _datetime_to_epoch_seconds(dt):
    """Converts a datetime.datetime to seconds since the epoch."""
    if dt is None:
        return None
    return int(time.mktime(dt.utctimetuple()))


def _task_to_dict(task):
    """Converts a WorkQueue to a JSON-able dictionary."""
    payload = task.payload
    if payload and task.content_type == 'application/json':
        payload = json.loads(payload)

    return dict(
        task_id=task.task_id,
        queue_name=task.queue_name,
        eta=_datetime_to_epoch_seconds(task.eta),
        source=task.source,
        created=_datetime_to_epoch_seconds(task.created),
        lease_attempts=task.lease_attempts,
        last_lease=_datetime_to_epoch_seconds(task.last_lease),
        payload=payload,
        content_type=task.content_type)


# TODO: Allow requesting key to lease a task if the source matches. This
# would let users run their own workers for server-side capture queues.


def lease(queue_name, owner, count=1, timeout_seconds=60):
    """Leases a work item from a queue, usually the oldest task available.

    Args:
        queue_name: Name of the queue to lease work from.
        owner: Who or what is leasing the task.
        count: Lease up to this many tasks. Return value will never have more
            than this many items present.
        timeout_seconds: Number of seconds to lock the task for before
            allowing another owner to lease it.

    Returns:
        List of dictionaries representing the task that was leased, or
        an empty list if no tasks are available to be leased.
    """
    now = datetime.datetime.utcnow()
    query = (
        WorkQueue.query
        .filter_by(queue_name=queue_name, status=WorkQueue.LIVE)
        .filter(WorkQueue.eta <= now)
        .order_by(WorkQueue.eta)
        .with_lockmode('update')
        .limit(count))

    task_list = query.all()
    if not task_list:
        return None

    next_eta = now + datetime.timedelta(seconds=timeout_seconds)

    for task in task_list:
        task.eta = next_eta
        task.lease_attempts += 1
        task.last_owner = owner
        task.last_lease = now
        task.heartbeat = None
        task.heartbeat_number = 0
        db.session.add(task)

    return [_task_to_dict(task) for task in task_list]


def _get_task_with_policy(queue_name, task_id, owner):
    """Fetches the specified task and enforces ownership policy.

    Args:
        queue_name: Name of the queue the work item is on.
        task_id: ID of the task that is finished.
        owner: Who or what has the current lease on the task.

    Returns:
        The valid WorkQueue task that is currently owned.

    Raises:
        TaskDoesNotExistError if the task does not exist.
        LeaseExpiredError if the lease is no longer active.
        NotOwnerError if the specified owner no longer owns the task.
    """
    now = datetime.datetime.utcnow()
    task = (
        WorkQueue.query
        .filter_by(queue_name=queue_name, task_id=task_id)
        .with_lockmode('update')
        .first())
    if not task:
        raise TaskDoesNotExistError('task_id=%r' % task_id)

    # Lease delta should be positive, meaning it has not yet expired!
    lease_delta = now - task.eta
    if lease_delta > datetime.timedelta(0):
        db.session.rollback()
        raise LeaseExpiredError('queue=%r, task_id=%r expired %s' % (
                                task.queue_name, task_id, lease_delta))

    if task.last_owner != owner:
        db.session.rollback()
        raise NotOwnerError('queue=%r, task_id=%r, owner=%r' % (
                            task.queue_name, task_id, task.last_owner))

    return task


def heartbeat(queue_name, task_id, owner, message, index):
    """Sets the heartbeat status of the task and extends its lease.

    The task's lease is extended by the same amount as its last lease to
    ensure that any operations following the heartbeat will still hold the
    lock for the original lock period.

    Args:
        queue_name: Name of the queue the work item is on.
        task_id: ID of the task that is finished.
        owner: Who or what has the current lease on the task.
        message: Message to report as the task's current status.
        index: Number of this message in the sequence of messages from the
            current task owner, starting at zero. This lets the API receive
            heartbeats out of order, yet ensure that the most recent message
            is actually saved to the database. This requires the owner issuing
            heartbeat messages to issue heartbeat indexes sequentially.

    Returns:
        True if the heartbeat message was set, False if it is lower than the
        current heartbeat index.

    Raises:
        TaskDoesNotExistError if the task does not exist.
        LeaseExpiredError if the lease is no longer active.
        NotOwnerError if the specified owner no longer owns the task.
    """
    task = _get_task_with_policy(queue_name, task_id, owner)
    if task.heartbeat_number > index:
        return False

    task.heartbeat = message
    task.heartbeat_number = index

    # Extend the lease by the time of the last lease.
    now = datetime.datetime.utcnow()
    timeout_delta = task.eta - task.last_lease
    task.eta = now + timeout_delta
    task.last_lease = now

    db.session.add(task)

    signals.task_updated.send(app, task=task)

    return True


def finish(queue_name, task_id, owner, error=False):
    """Marks a work item on a queue as finished.

    Args:
        queue_name: Name of the queue the work item is on.
        task_id: ID of the task that is finished.
        owner: Who or what has the current lease on the task.
        error: Defaults to false. True if this task's final state is an error.

    Returns:
        True if the task has been finished for the first time; False if the
        task was already finished.

    Raises:
        TaskDoesNotExistError if the task does not exist.
        LeaseExpiredError if the lease is no longer active.
        NotOwnerError if the specified owner no longer owns the task.
    """
    task = _get_task_with_policy(queue_name, task_id, owner)

    if not task.status == WorkQueue.LIVE:
        logging.warning('Finishing already dead task. queue=%r, task_id=%r, '
                        'owner=%r, status=%r',
                        task.queue_name, task_id, owner, task.status)
        return False

    if not error:
        task.status = WorkQueue.DONE
    else:
        task.status = WorkQueue.ERROR

    task.finished = datetime.datetime.utcnow()
    db.session.add(task)

    signals.task_updated.send(app, task=task)

    return True


def _query(queue_name=None, build_id=None, release_id=None, run_id=None,
           count=None):
    """Queries for work items based on their criteria.

    Args:
        queue_name: Optional queue name to restrict to.
        build_id: Optional build ID to restrict to.
        release_id: Optional release ID to restrict to.
        run_id: Optional run ID to restrict to.
        count: How many tasks to fetch. Defaults to None, which means all
            tasks are fetch that match the query.

    Returns:
        List of WorkQueue items.
    """
    assert queue_name or build_id or release_id or run_id

    q = WorkQueue.query
    if queue_name:
        q = q.filter_by(queue_name=queue_name)
    if build_id:
        q = q.filter_by(build_id=build_id)
    if release_id:
        q = q.filter_by(release_id=release_id)
    if run_id:
        q = q.filter_by(run_id=run_id)

    q = q.order_by(WorkQueue.created.desc())

    if count is not None:
        q = q.limit(count)

    return q.all()


def query(**kwargs):
    """Queries for work items based on their criteria.

    Args:
        queue_name: Optional queue name to restrict to.
        build_id: Optional build ID to restrict to.
        release_id: Optional release ID to restrict to.
        run_id: Optional run ID to restrict to.
        count: How many tasks to fetch. Defaults to None, which means all
            tasks are fetch that match the query.

    Returns:
        Dictionaries of the most recent tasks that match the criteria, in
        order of most recently created. When count is 1 the return value will
        be the most recent task or None. When count is not 1 the return value
        will be a  list of tasks.
    """
    count = kwargs.get('count', None)
    task_list = _query(**kwargs)
    task_dict_list = [_task_to_dict(task) for task in task_list]

    if count == 1:
        if not task_dict_list:
            return None
        else:
            return task_dict_list[0]

    return task_dict_list


def cancel(**kwargs):
    """Cancels work items based on their criteria.

    Args:
        **kwargs: Same parameters as the query() method.

    Returns:
        The number of tasks that were canceled.
    """
    task_list = _query(**kwargs)
    for task in task_list:
        task.status = WorkQueue.CANCELED
        task.finished = datetime.datetime.utcnow()
        db.session.add(task)
    return len(task_list)

########NEW FILE########
__FILENAME__ = work_queue_handlers
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pull-queue web handlers."""

import logging

# Local libraries
import flask
from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy import func

# Local modules
from . import app
from . import db
from dpxdt.server import auth
from dpxdt.server import forms
from dpxdt.server import utils
from dpxdt.server import work_queue


@app.route('/api/work_queue/<string:queue_name>/add', methods=['POST'])
@auth.superuser_api_key_required
@utils.retryable_transaction()
def handle_add(queue_name):
    """Adds a task to a queue."""
    source = request.form.get('source', request.remote_addr, type=str)
    try:
        task_id = work_queue.add(
            queue_name,
            payload=request.form.get('payload', type=str),
            content_type=request.form.get('content_type', type=str),
            source=source,
            task_id=request.form.get('task_id', type=str))
    except work_queue.Error, e:
        return utils.jsonify_error(e)

    db.session.commit()
    logging.info('Task added: queue=%r, task_id=%r, source=%r',
                 queue_name, task_id, source)
    return flask.jsonify(task_id=task_id)


@app.route('/api/work_queue/<string:queue_name>/lease', methods=['POST'])
@auth.superuser_api_key_required
@utils.retryable_transaction()
def handle_lease(queue_name):
    """Leases a task from a queue."""
    owner = request.form.get('owner', request.remote_addr, type=str)
    try:
        task_list = work_queue.lease(
            queue_name,
            owner,
            request.form.get('count', 1, type=int),
            request.form.get('timeout', 60, type=int))
    except work_queue.Error, e:
        return utils.jsonify_error(e)

    if not task_list:
        return flask.jsonify(tasks=[])

    db.session.commit()
    task_ids = [t['task_id'] for t in task_list]
    logging.debug('Task leased: queue=%r, task_ids=%r, owner=%r',
                  queue_name, task_ids, owner)
    return flask.jsonify(tasks=task_list)


@app.route('/api/work_queue/<string:queue_name>/heartbeat', methods=['POST'])
@auth.superuser_api_key_required
@utils.retryable_transaction()
def handle_heartbeat(queue_name):
    """Updates the heartbeat message for a task."""
    task_id = request.form.get('task_id', type=str)
    message = request.form.get('message', type=str)
    index = request.form.get('index', type=int)
    try:
        work_queue.heartbeat(
            queue_name,
            task_id,
            request.form.get('owner', request.remote_addr, type=str),
            message,
            index)
    except work_queue.Error, e:
        return utils.jsonify_error(e)

    db.session.commit()
    logging.debug('Task heartbeat: queue=%r, task_id=%r, message=%r, index=%d',
                  queue_name, task_id, message, index)
    return flask.jsonify(success=True)


@app.route('/api/work_queue/<string:queue_name>/finish', methods=['POST'])
@auth.superuser_api_key_required
@utils.retryable_transaction()
def handle_finish(queue_name):
    """Marks a task on a queue as finished."""
    task_id = request.form.get('task_id', type=str)
    owner = request.form.get('owner', request.remote_addr, type=str)
    error = request.form.get('error', type=str) is not None
    try:
        work_queue.finish(queue_name, task_id, owner, error=error)
    except work_queue.Error, e:
        return utils.jsonify_error(e)

    db.session.commit()
    logging.debug('Task finished: queue=%r, task_id=%r, owner=%r, error=%r',
                  queue_name, task_id, owner, error)
    return flask.jsonify(success=True)


@app.route('/api/work_queue')
@auth.superuser_required
def view_all_work_queues():
    """Page for viewing the index of all active work queues."""
    count_list = list(
        db.session.query(
            work_queue.WorkQueue.queue_name,
            work_queue.WorkQueue.status,
            func.count(work_queue.WorkQueue.task_id))
        .group_by(work_queue.WorkQueue.queue_name,
                  work_queue.WorkQueue.status))

    queue_dict = {}
    for name, status, count in count_list:
        queue_dict[(name, status)] = dict(
            name=name, status=status, count=count)

    max_created_list = list(
        db.session.query(
            work_queue.WorkQueue.queue_name,
            work_queue.WorkQueue.status,
            func.max(work_queue.WorkQueue.created))
        .group_by(work_queue.WorkQueue.queue_name,
                  work_queue.WorkQueue.status))

    for name, status, newest_created in max_created_list:
        queue_dict[(name, status)]['newest_created'] = newest_created

    min_eta_list = list(
        db.session.query(
            work_queue.WorkQueue.queue_name,
            work_queue.WorkQueue.status,
            func.min(work_queue.WorkQueue.eta))
        .group_by(work_queue.WorkQueue.queue_name,
                  work_queue.WorkQueue.status))

    for name, status, oldest_eta in min_eta_list:
        queue_dict[(name, status)]['oldest_eta'] = oldest_eta

    queue_list = list(queue_dict.values())
    queue_list.sort(key=lambda x: (x['name'], x['status']))

    context = dict(
        queue_list=queue_list,
    )
    return render_template('view_work_queue_index.html', **context)


@app.route('/api/work_queue/<string:queue_name>', methods=['GET', 'POST'])
@auth.superuser_required
def manage_work_queue(queue_name):
    """Page for viewing the contents of a work queue."""
    modify_form = forms.ModifyWorkQueueTaskForm()
    if modify_form.validate_on_submit():
        primary_key = (modify_form.task_id.data, queue_name)
        task = work_queue.WorkQueue.query.get(primary_key)
        if task:
            logging.info('Action: %s task_id=%r',
                         modify_form.action.data, modify_form.task_id.data)
            if modify_form.action.data == 'retry':
                task.status = work_queue.WorkQueue.LIVE
                task.lease_attempts = 0
                task.heartbeat = 'Retrying ...'
                db.session.add(task)
            else:
                db.session.delete(task)
            db.session.commit()
        else:
            logging.warning('Could not find task_id=%r to delete',
                            modify_form.task_id.data)
        return redirect(url_for('manage_work_queue', queue_name=queue_name))

    query = (
        work_queue.WorkQueue.query
        .filter_by(queue_name=queue_name)
        .order_by(work_queue.WorkQueue.created.desc()))

    status = request.args.get('status', '', type=str).lower()
    if status in work_queue.WorkQueue.STATES:
        query = query.filter_by(status=status)
    else:
        status = None

    item_list = list(query.limit(100))
    work_list = []
    for item in item_list:
        form = forms.ModifyWorkQueueTaskForm()
        form.task_id.data = item.task_id
        form.delete.data = True
        work_list.append((item, form))

    context = dict(
        queue_name=queue_name,
        status=status,
        work_list=work_list,
    )
    return render_template('view_work_queue.html', **context)

########NEW FILE########
__FILENAME__ = diff_my_images
#!/usr/bin/env python
# Copyright 2014 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility for uploading and diffing images that were generated locally.

Plugs screenshots generated in a tool like Selenium into Depicted. Uses the
last known good screenshots for tests with the same name as the baseline for
comparison. Depicted will generate diffs for you and manage the workflow.

Example usage:

./dpxdt/tools/diff_my_images.py \
    --upload_build_id=1234 \
    --release_server_prefix=https://my-dpxdt-apiserver.example.com/api \
    --release_client_id=<your api key> \
    --release_client_secret=<your api secret> \
    --upload_release_name="My release name" \
    --release_cut_url=http://example.com/path/to/my/release/tool/for/this/cut
    --tests_json_path=my_tests.json

Example input file "my_tests.json". One entry per test:

[
    {
        "name": "My homepage",
        "run_failed": false,
        "image_path": "/tmp/path/to/my/new_screenshot.png",
        "log_path": "/tmp/path/to/my/new_output_log.txt",
        "url": "http://example.com/new/build/url/here"
    },
    ...
]

Use the "run_failed" parameter when your screenshotting tool failed for
some reason and you want to upload your log but still mark the test as
having failed. This makes it easy to debug all of your Depicted tests in
one place for a single release.
"""

import datetime
import json
import logging
import sys

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import fetch_worker
from dpxdt.client import release_worker
from dpxdt.client import workers
import flags


class Test(object):
    """Represents the JSON of a single test."""

    def __init__(self, name=None, run_failed=False, image_path=None,
                 log_path=None, url=None):
        self.name = name
        self.run_failed = run_failed
        self.image_path = image_path
        self.log_path = log_path
        self.url = url


def load_tests(data):
    """Loads JSON data and returns a list of Test objects it contains."""
    test_list = json.loads(data)
    results = []
    for test_json in test_list:
        results.append(Test(**test_json))
    return results


class RunTest(workers.WorkflowItem):
    """Workflow to run a single test.

    Searches for the last good run for the same test name to use as a
    baseline for comparison. If no last good run is found, the supplied
    images will be treated as a new basline.

    Args:
        build_id: ID of the build being tested.
        release_name: Name of the release being tested.
        release_number: Number of the release being tested.
        test: Test object to handle.
        heartbeat: Function to call with progress status.
    """

    def run(self, build_id, release_name, release_number, test, heartbeat=None):
        ref_image, ref_log, ref_url = None, None, None
        try:
            last_good = yield release_worker.FindRunWorkflow(
                build_id, test.name)
        except release_worker.FindRunError, e:
            yield heartbeat('Could not find last good run for %s' % test.name)
        else:
            ref_image = last_good['image'] or None
            ref_log = last_good['log'] or None
            ref_url = last_good['url'] or None

        yield heartbeat('Uploading data for %s' % test.name)
        yield release_worker.ReportRunWorkflow(
            build_id,
            release_name,
            release_number,
            test.name,
            image_path=test.image_path,
            log_path=test.log_path,
            url=test.url,
            ref_image=ref_image,
            ref_log=ref_log,
            ref_url=ref_url,
            run_failed=test.run_failed)


class DiffMyImages(workers.WorkflowItem):
    """Workflow for diffing set of images generated outside of Depicted.

    Args:
        release_url: URL of the newest and best version of the page.
        tests: List of Test objects to test.
        upload_build_id: Optional. Build ID of the site being compared. When
            supplied a new release will be cut for this build comparing it
            to the last good release.
        upload_release_name: Optional. Release name to use for the build. When
            not supplied, a new release based on the current time will be
            created.
        heartbeat: Function to call with progress status.
    """

    def run(self,
            release_url,
            tests,
            upload_build_id,
            upload_release_name,
            heartbeat=None):
        if not upload_release_name:
            upload_release_name = str(datetime.datetime.utcnow())

        yield heartbeat('Creating release %s' % upload_release_name)
        release_number = yield release_worker.CreateReleaseWorkflow(
            upload_build_id, upload_release_name, release_url)

        pending_uploads = []
        for test in tests:
            item = RunTest(upload_build_id, upload_release_name,
                           release_number, test, heartbeat=heartbeat)
            pending_uploads.append(item)

        yield heartbeat('Uploading %d runs' % len(pending_uploads))
        yield pending_uploads

        yield heartbeat('Marking runs as complete')
        release_url = yield release_worker.RunsDoneWorkflow(
            upload_build_id, upload_release_name, release_number)

        yield heartbeat('Results viewable at: %s' % release_url)


def real_main(release_url=None,
              tests_json_path=None,
              upload_build_id=None,
              upload_release_name=None):
    """Runs diff_my_images."""
    coordinator = workers.get_coordinator()
    fetch_worker.register(coordinator)
    coordinator.start()

    data = open(FLAGS.tests_json_path).read()
    tests = load_tests(data)

    item = DiffMyImages(
        release_url,
        tests,
        upload_build_id,
        upload_release_name,
        heartbeat=workers.PrintWorkflow)
    item.root = True

    coordinator.input_queue.put(item)
    coordinator.wait_one()


def main(argv):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    assert FLAGS.release_cut_url
    assert FLAGS.release_server_prefix
    assert FLAGS.tests_json_path
    assert FLAGS.upload_build_id

    if FLAGS.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    real_main(
        release_url=FLAGS.release_cut_url,
        tests_json_path=FLAGS.tests_json_path,
        upload_build_id=FLAGS.upload_build_id,
        upload_release_name=FLAGS.upload_release_name)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = diff_my_urls
#!/usr/bin/env python
# Copyright 2014 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility for diffing a set of URL pairs defined in a config file.

Example usage:

./dpxdt/tools/diff_my_urls.py \
    --upload_build_id=1234 \
    --release_server_prefix=https://my-dpxdt-apiserver.example.com/api \
    --release_client_id=<your api key> \
    --release_client_secret=<your api secret> \
    --upload_release_name="My release name" \
    --release_cut_url=http://example.com/path/to/my/release/tool/for/this/cut
    --tests_json_path=my_url_tests.json

Example input file "my_url_tests.json". One entry per test:

[
    {
        "name": "My homepage",
        "run_url": "http://localhost:5000/static/dummy/dummy_page1.html",
        "run_config": {
            "viewportSize": {
                "width": 1024,
                "height": 768
            },
            "injectCss": "#foobar { background-color: lime",
            "injectJs": "document.getElementById('foobar').innerText = 'bar';",
        },
        "ref_url": "http://localhost:5000/static/dummy/dummy_page1.html",
        "ref_config": {
            "viewportSize": {
                "width": 1024,
                "height": 768
            },
            "injectCss": "#foobar { background-color: goldenrod; }",
            "injectJs": "document.getElementById('foobar').innerText = 'foo';",
        }
    },
    ...
]

See README.md for documentation of config parameters.
"""

import datetime
import json
import logging
import sys

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import fetch_worker
from dpxdt.client import release_worker
from dpxdt.client import workers
import flags


class Test(object):
    """Represents the JSON of a single test."""

    def __init__(self, name=None, run_url=None, run_config=None,
                 ref_url=None, ref_config=None):
        self.name = name
        self.run_url = run_url
        self.run_config_data = json.dumps(run_config)
        self.ref_url = ref_url
        self.ref_config_data = json.dumps(ref_config)


def load_tests(data):
    """Loads JSON data and returns a list of Test objects it contains."""
    test_list = json.loads(data)
    results = []
    for test_json in test_list:
        results.append(Test(**test_json))
    return results


class DiffMyUrls(workers.WorkflowItem):
    """Workflow for diffing a set of URL pairs defined in a config file.

    Args:
        release_url: URL of the newest and best version of the page.
        tests: List of Test objects to test.
        upload_build_id: Optional. Build ID of the site being compared. When
            supplied a new release will be cut for this build comparing it
            to the last good release.
        upload_release_name: Optional. Release name to use for the build. When
            not supplied, a new release based on the current time will be
            created.
        heartbeat: Function to call with progress status.
    """

    def run(self,
            release_url,
            tests,
            upload_build_id,
            upload_release_name,
            heartbeat=None):
        if not upload_release_name:
            upload_release_name = str(datetime.datetime.utcnow())

        yield heartbeat('Creating release %s' % upload_release_name)
        release_number = yield release_worker.CreateReleaseWorkflow(
            upload_build_id, upload_release_name, release_url)

        pending_uploads = []
        for test in tests:
            item = release_worker.RequestRunWorkflow(
                upload_build_id, upload_release_name, release_number,
                test.name, url=test.run_url, config_data=test.run_config_data,
                ref_url=test.ref_url, ref_config_data=test.ref_config_data)
            pending_uploads.append(item)

        yield heartbeat('Requesting %d runs' % len(pending_uploads))
        yield pending_uploads

        yield heartbeat('Marking runs as complete')
        release_url = yield release_worker.RunsDoneWorkflow(
            upload_build_id, upload_release_name, release_number)

        yield heartbeat('Results viewable at: %s' % release_url)


def real_main(release_url=None,
              tests_json_path=None,
              upload_build_id=None,
              upload_release_name=None):
    """Runs diff_my_urls."""
    coordinator = workers.get_coordinator()
    fetch_worker.register(coordinator)
    coordinator.start()

    data = open(FLAGS.tests_json_path).read()
    tests = load_tests(data)

    item = DiffMyUrls(
        release_url,
        tests,
        upload_build_id,
        upload_release_name,
        heartbeat=workers.PrintWorkflow)
    item.root = True

    coordinator.input_queue.put(item)
    coordinator.wait_one()


def main(argv):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    assert FLAGS.release_cut_url
    assert FLAGS.release_server_prefix
    assert FLAGS.tests_json_path
    assert FLAGS.upload_build_id

    if FLAGS.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    real_main(
        release_url=FLAGS.release_cut_url,
        tests_json_path=FLAGS.tests_json_path,
        upload_build_id=FLAGS.upload_build_id,
        upload_release_name=FLAGS.upload_release_name)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = flags
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common flags for utility scripts."""

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

gflags.DEFINE_string(
    'upload_build_id', None,
    'ID of the build to upload this screenshot set to as a new release.')

gflags.DEFINE_string(
    'upload_release_name', None,
    'Along with upload_build_id, the name of the release to upload to. If '
    'not supplied, a new release will be created.')

gflags.DEFINE_string(
    'inject_css', None,
    'CSS to inject into all captured pages after they have loaded but '
    'before screenshotting.')

gflags.DEFINE_string(
    'inject_js', None,
    'JavaScript to inject into all captured pages after they have loaded '
    'but before screenshotting.')

gflags.DEFINE_string(
    'cookies', None,
    'Filename containing a JSON array of cookies to set.')

gflags.DEFINE_string(
    'release_cut_url', None,
    'URL that describes the release that you are testing. Usually a link to '
    'the commit or branch that was built.')

gflags.DEFINE_string(
    'tests_json_path', None,
    'Path to the JSON file containing the list of tests to diff.')

########NEW FILE########
__FILENAME__ = site_diff
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility for doing incremental diffs for a live website.

Example usage:

./dpxdt/tools/site_diff.py \
    --upload_build_id=1234 \
    --release_server_prefix=https://my-dpxdt-apiserver.example.com/api \
    --release_client_id=<your api key> \
    --release_client_secret=<your api secret> \
    --crawl_depth=1 \
    http://www.example.com/my/website/here
"""

import HTMLParser
import Queue
import datetime
import json
import logging
import os
import re
import sys
import urlparse

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import release_worker
from dpxdt.client import fetch_worker
from dpxdt.client import workers
import flags


gflags.DEFINE_integer(
    'crawl_depth', -1,
    'How deep to crawl. Depth of 0 means only the given page. 1 means pages '
    'that are one click away, 2 means two clicks, and so on. Set to -1 to '
    'scan every URL with the supplied prefix.')

gflags.DEFINE_spaceseplist(
    'ignore_prefixes', [],
    'URL prefixes that should not be crawled.')


# URL regex rewriting code originally from mirrorrr
# http://code.google.com/p/mirrorrr/source/browse/trunk/transform_content.py

# URLs that have absolute addresses
ABSOLUTE_URL_REGEX = r"(?P<url>(http(s?):)?//[^\"'> \t]+)"
# URLs that are relative to the base of the current hostname.
BASE_RELATIVE_URL_REGEX = (
    r"/(?!(/)|(http(s?)://)|(url\())(?P<url>[^\"'> \t]*)")
# URLs that have '../' or './' to start off their paths.
TRAVERSAL_URL_REGEX = (
    r"(?P<relative>\.(\.)?)/(?!(/)|"
    r"(http(s?)://)|(url\())(?P<url>[^\"'> \t]*)")
# URLs that are in the same directory as the requested URL.
SAME_DIR_URL_REGEX = r"(?!(/)|(http(s?)://)|(#)|(url\())(?P<url>[^\"'> \t]+)"
# URL matches the root directory.
ROOT_DIR_URL_REGEX = r"(?!//(?!>))/(?P<url>)(?=[ \t\n]*[\"'> /])"
# Start of a tag using 'src' or 'href'
TAG_START = (
    r"(?i)(?P<tag>\ssrc|href|action|url|background)"
    r"(?P<equals>[\t ]*=[\t ]*)(?P<quote>[\"']?)")
# Potential HTML document URL with no fragments.
MAYBE_HTML_URL_REGEX = (
    TAG_START + r"(?P<absurl>(http(s?):)?//[^\"'> \t]+)")

REPLACEMENT_REGEXES = [
    (TAG_START + SAME_DIR_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>%(accessed_dir)s\g<url>"),
    (TAG_START + TRAVERSAL_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>%(accessed_dir)s/\g<relative>/\g<url>"),
    (TAG_START + BASE_RELATIVE_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>%(base)s/\g<url>"),
    (TAG_START + ROOT_DIR_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>%(base)s/"),
    (TAG_START + ABSOLUTE_URL_REGEX,
     "\g<tag>\g<equals>\g<quote>\g<url>"),
]


def clean_url(url, force_scheme=None):
    """Cleans the given URL."""
    # URL should be ASCII according to RFC 3986
    url = str(url)
    # Collapse ../../ and related
    url_parts = urlparse.urlparse(url)
    path_parts = []
    for part in url_parts.path.split('/'):
        if part == '.':
            continue
        elif part == '..':
            if path_parts:
                path_parts.pop()
        else:
            path_parts.append(part)

    url_parts = list(url_parts)
    if force_scheme:
        url_parts[0] = force_scheme
    url_parts[2] = '/'.join(path_parts)
    url_parts[4] = ''    # No query string
    url_parts[5] = ''    # No path

    # Always have a trailing slash
    if not url_parts[2]:
        url_parts[2] = '/'

    return urlparse.urlunparse(url_parts)


def extract_urls(url, data, unescape=HTMLParser.HTMLParser().unescape):
    """Extracts the URLs from an HTML document."""
    parts = urlparse.urlparse(url)
    prefix = '%s://%s' % (parts.scheme, parts.netloc)

    accessed_dir = os.path.dirname(parts.path)
    if not accessed_dir.endswith('/'):
        accessed_dir += '/'

    for pattern, replacement in REPLACEMENT_REGEXES:
        fixed = replacement % {
            'base': prefix,
            'accessed_dir': accessed_dir,
        }
        data = re.sub(pattern, fixed, data)

    result = set()
    for match in re.finditer(MAYBE_HTML_URL_REGEX, data):
        found_url = unescape(match.groupdict()['absurl'])
        found_url = clean_url(
            found_url,
            force_scheme=parts[0])  # Use the main page's scheme
        result.add(found_url)

    return result


IGNORE_SUFFIXES = frozenset([
    'jpg', 'jpeg', 'png', 'css', 'js', 'xml', 'json', 'gif', 'ico', 'doc'])


def prune_urls(url_set, start_url, allowed_list, ignored_list):
    """Prunes URLs that should be ignored."""
    result = set()

    for url in url_set:
        allowed = False
        for allow_url in allowed_list:
            if url.startswith(allow_url):
                allowed = True
                break

        if not allowed:
            continue

        ignored = False
        for ignore_url in ignored_list:
            if url.startswith(ignore_url):
                ignored = True
                break

        if ignored:
            continue

        prefix, suffix = (url.rsplit('.', 1) + [''])[:2]
        if suffix.lower() in IGNORE_SUFFIXES:
            continue

        result.add(url)

    return result


class SiteDiff(workers.WorkflowItem):
    """Workflow for coordinating the site diff.

    Args:
        start_url: URL to begin the site diff scan.
        ignore_prefixes: Optional. List of URL prefixes to ignore during
            the crawl; start_url should be a common prefix with all of these.
        upload_build_id: Build ID of the site being compared.
        upload_release_name: Optional. Release name to use for the build. When
            not supplied, a new release based on the current time will be
            created.
        heartbeat: Function to call with progress status.
    """

    def run(self,
            start_url,
            ignore_prefixes,
            upload_build_id,
            upload_release_name=None,
            heartbeat=None):
        if not ignore_prefixes:
            ignore_prefixes = []

        pending_urls = set([clean_url(start_url)])
        seen_urls = set()
        good_urls = set()

        yield heartbeat('Scanning for content')

        limit_depth = FLAGS.crawl_depth >= 0
        depth = 0
        while (not limit_depth or depth <= FLAGS.crawl_depth) and pending_urls:
            # TODO: Enforce a job-wide timeout on the whole process of
            # URL discovery, to make sure infinitely deep sites do not
            # cause this job to never stop.
            seen_urls.update(pending_urls)
            yield heartbeat(
                'Scanning %d pages for good urls' % len(pending_urls))
            output = yield [fetch_worker.FetchItem(u) for u in pending_urls]
            pending_urls.clear()

            for item in output:
                if not item.data:
                    logging.debug('No data from url=%r', item.url)
                    continue

                if item.headers.gettype() != 'text/html':
                    logging.debug('Skipping non-HTML document url=%r',
                                  item.url)
                    continue

                good_urls.add(item.url)
                found = extract_urls(item.url, item.data)
                pruned = prune_urls(
                    found, start_url, [start_url], ignore_prefixes)
                new = pruned - seen_urls
                pending_urls.update(new)
                yield heartbeat('Found %d new URLs from %s' % (
                                len(new), item.url))

            yield heartbeat('Finished crawl at depth %d' % depth)
            depth += 1

        yield heartbeat(
            'Found %d total URLs, %d good HTML pages; starting '
            'screenshots' % (len(seen_urls), len(good_urls)))

        # TODO: Make the default release name prettier.
        if not upload_release_name:
            upload_release_name = str(datetime.datetime.utcnow())

        release_number = yield release_worker.CreateReleaseWorkflow(
            upload_build_id, upload_release_name, start_url)

        run_requests = []
        for url in good_urls:
            yield heartbeat('Requesting run for %s' % url)
            parts = urlparse.urlparse(url)
            run_name = parts.path

            config_dict = {
                'viewportSize': {
                    'width': 1280,
                    'height': 1024,
                }
            }
            if FLAGS.inject_css:
                config_dict['injectCss'] = FLAGS.inject_css
            if FLAGS.inject_js:
                config_dict['injectJs'] = FLAGS.inject_js
            if FLAGS.cookies:
                config_dict['cookies'] = json.loads(
                    open(FLAGS.cookies).read())
            config_data = json.dumps(config_dict)

            run_requests.append(release_worker.RequestRunWorkflow(
                upload_build_id, upload_release_name, release_number,
                run_name, url, config_data))

        yield run_requests

        yield heartbeat('Marking runs as complete')
        release_url = yield release_worker.RunsDoneWorkflow(
            upload_build_id, upload_release_name, release_number)

        yield heartbeat('Results viewable at: %s' % release_url)


def real_main(start_url=None,
              ignore_prefixes=None,
              upload_build_id=None,
              upload_release_name=None):
    """Runs the site_diff."""
    coordinator = workers.get_coordinator()
    fetch_worker.register(coordinator)
    coordinator.start()

    item = SiteDiff(
        start_url=start_url,
        ignore_prefixes=ignore_prefixes,
        upload_build_id=upload_build_id,
        upload_release_name=upload_release_name,
        heartbeat=workers.PrintWorkflow)
    item.root = True

    coordinator.input_queue.put(item)
    coordinator.wait_one()


def main(argv):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    if len(argv) != 2:
        print 'Must supply a website URL as the first argument.'
        sys.exit(1)

    assert FLAGS.upload_build_id
    assert FLAGS.release_server_prefix

    if FLAGS.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    real_main(
        start_url=argv[1],
        ignore_prefixes=FLAGS.ignore_prefixes,
        upload_build_id=FLAGS.upload_build_id,
        upload_release_name=FLAGS.upload_release_name)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = url_pair_diff
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility for doing a diff between a pair of URLs.

Example usage:

./dpxdt/tools/url_pair_diff.py \
    --upload_build_id=1234 \
    --release_server_prefix=https://my-dpxdt-apiserver.example.com/api \
    --release_client_id=<your api key> \
    --release_client_secret=<your api secret> \
    http://www.example.com/my/before/page \
    http://www.example.com/my/after/page
"""

import HTMLParser
import Queue
import datetime
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import urlparse

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import fetch_worker
from dpxdt.client import release_worker
from dpxdt.client import workers
import flags


class UrlPairDiff(workers.WorkflowItem):
    """Workflow for diffing a pair of URLs.

    Args:
        new_url: URL of the newest and best version of the page.
        baseline_url: URL of the baseline to compare to.
        upload_build_id: Optional. Build ID of the site being compared. When
            supplied a new release will be cut for this build comparing it
            to the last good release.
        upload_release_name: Optional. Release name to use for the build. When
            not supplied, a new release based on the current time will be
            created.
        heartbeat: Function to call with progress status.
    """

    def run(self,
            new_url,
            baseline_url,
            upload_build_id,
            upload_release_name=None,
            heartbeat=None):
        # TODO: Make the default release name prettier.
        if not upload_release_name:
            upload_release_name = str(datetime.datetime.utcnow())

        yield heartbeat('Creating release %s' % upload_release_name)
        release_number = yield release_worker.CreateReleaseWorkflow(
            upload_build_id, upload_release_name, new_url)

        config_dict = {
            'viewportSize': {
                'width': 1280,
                'height': 1024,
            }
        }
        if FLAGS.inject_css:
            config_dict['injectCss'] = FLAGS.inject_css
        if FLAGS.inject_js:
            config_dict['injectJs'] = FLAGS.inject_js
        config_data = json.dumps(config_dict)

        url_parts = urlparse.urlparse(new_url)

        yield heartbeat('Requesting captures')
        yield release_worker.RequestRunWorkflow(
                upload_build_id,
                upload_release_name,
                release_number,
                url_parts.path or '/',
                new_url,
                config_data,
                ref_url=baseline_url,
                ref_config_data=config_data)

        yield heartbeat('Marking runs as complete')
        release_url = yield release_worker.RunsDoneWorkflow(
            upload_build_id, upload_release_name, release_number)

        yield heartbeat('Results viewable at: %s' % release_url)


def real_main(new_url=None,
              baseline_url=None,
              upload_build_id=None,
              upload_release_name=None):
    """Runs the ur_pair_diff."""
    coordinator = workers.get_coordinator()
    fetch_worker.register(coordinator)
    coordinator.start()

    item = UrlPairDiff(
        new_url,
        baseline_url,
        upload_build_id,
        upload_release_name=upload_release_name,
        heartbeat=workers.PrintWorkflow)
    item.root = True

    coordinator.input_queue.put(item)
    coordinator.wait_one()


def main(argv):
    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    if len(argv) != 3:
        print 'Must supply two URLs as arguments.'
        sys.exit(1)

    assert FLAGS.upload_build_id
    assert FLAGS.release_server_prefix

    if FLAGS.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    real_main(
        new_url=argv[1],
        baseline_url=argv[2],
        upload_build_id=FLAGS.upload_build_id,
        upload_release_name=FLAGS.upload_release_name)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = site_diff_test
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the site_diff utility."""

import BaseHTTPServer
import logging
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
import uuid

# Local libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt import runworker
from dpxdt import server
from dpxdt.client import capture_worker
from dpxdt.client import workers
from dpxdt.server import db
from dpxdt.server import models
from dpxdt.tools import site_diff


def get_free_port():
    sock = socket.socket()
    sock.bind(('', 0))
    return sock.getsockname()[1]


# Will be set by one-time setUp
server_thread = None


def setUpModule():
    """Sets up the environment for testing."""
    global server_thread

    server_port = get_free_port()

    FLAGS.fetch_frequency = 100
    FLAGS.fetch_threads = 1
    FLAGS.phantomjs_timeout = 60
    FLAGS.polltime = 1
    FLAGS.queue_idle_poll_seconds = 1
    FLAGS.queue_busy_poll_seconds = 1
    FLAGS.queue_server_prefix = (
        'http://localhost:%d/api/work_queue' % server_port)
    FLAGS.release_server_prefix = 'http://localhost:%d/api' % server_port

    db_path = tempfile.mktemp(suffix='.db')
    logging.info('sqlite path used in tests: %s', db_path)
    server.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    db.drop_all()
    db.create_all()

    server.app.config['CSRF_ENABLED'] = False
    server.app.config['IGNORE_AUTH'] = True
    server.app.config['TESTING'] = True
    run = lambda: server.app.run(debug=False, host='0.0.0.0', port=server_port)

    server_thread = threading.Thread(target=run)
    server_thread.setDaemon(True)
    server_thread.start()

    runworker.run_workers()


def create_build():
    """Creates a new build and returns its ID."""
    build = models.Build(name='My build')
    db.session.add(build)
    db.session.commit()
    return build.id


def wait_for_release(build_id, release_name, timeout_seconds=60):
    """Waits for a release to enter a terminal state."""
    start = time.time()
    while True:
        release = (models.Release.query
            .filter_by(build_id=build_id, name=release_name)
            .order_by(models.Release.number.desc())
            .first())
        db.session.refresh(release)
        if release.status == models.Release.REVIEWING:
            return release
        else:
            print 'Release status: %s' % release.status

        assert time.time() - start < timeout_seconds, (
            'Timing out waiting for release to enter terminal state')
        time.sleep(1)


def webserver(func):
    """Runs the given function as a webserver.

    Function should take one argument, the path of the request. Should
    return tuple (status, content_type, content) or Nothing if there is no
    response.
    """
    class HandlerClass(BaseHTTPServer.BaseHTTPRequestHandler):
        def do_GET(self):
            output = func(self.path)
            if output:
                code, content_type, result = output
            else:
                code, content_type, result = 404, 'text/plain', 'Not found!'

            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.end_headers()
            if result:
                self.wfile.write(result)

    server = BaseHTTPServer.HTTPServer(('', 0), HandlerClass)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    server.server_prefix = 'http://localhost:%d' % server.server_address[1]
    print 'Test server started on %s' % server.server_prefix
    return server


class SiteDiffTest(unittest.TestCase):
    """Tests for the SiteDiff workflow."""

    def setUp(self):
        """Sets up the test harness."""
        self.coordinator = workers.get_coordinator()
        self.build_id = create_build()
        self.release_name = uuid.uuid4().hex
        self.client = server.app.test_client()

    def testEndToEnd(self):
        """Tests doing a site diff from end to end."""
        # Create the first release.
        @webserver
        def test1(path):
            if path == '/':
                return 200, 'text/html', '<h1>Hello world!</h1>'

        site_diff.real_main(
            start_url=test1.server_prefix + '/',
            upload_build_id=self.build_id,
            upload_release_name=self.release_name)

        release = wait_for_release(self.build_id, self.release_name)

        # Verify the first screenshot worked and its status can load.
        resp = self.client.get(
            '/release?id=%d&name=%s&number=%d' % (
                self.build_id, release.name, release.number),
            follow_redirects=True)
        self.assertEquals('200 OK', resp.status)
        self.assertIn('Nothing to test', resp.data)
        self.assertIn('Diff not required', resp.data)

        # Mark the release as good.
        resp = self.client.post(
            '/release',
            data=dict(
                id=self.build_id,
                name=release.name,
                number=release.number,
                good=True),
            follow_redirects=True)
        self.assertEquals('200 OK', resp.status)

        # Create the second release.
        @webserver
        def test2(path):
            if path == '/':
                return 200, 'text/html', '<h1>Hello again!</h1>'

        site_diff.real_main(
            start_url=test2.server_prefix + '/',
            upload_build_id=self.build_id,
            upload_release_name=self.release_name)

        release = wait_for_release(self.build_id, self.release_name)

        # Verify a diff was computed and found.
        resp = self.client.get(
            '/release?id=%d&name=%s&number=%d' % (
                self.build_id, release.name, release.number),
            follow_redirects=True)
        self.assertEquals('200 OK', resp.status)
        self.assertIn('1 tested', resp.data)
        self.assertIn('1 failure', resp.data)
        self.assertIn('Diff found', resp.data)

        # Create the second release.
        site_diff.real_main(
            start_url=test1.server_prefix + '/',
            upload_build_id=self.build_id,
            upload_release_name=self.release_name)

        release = wait_for_release(self.build_id, self.release_name)
        test1.shutdown()
        test2.shutdown()

        # No diff found.
        resp = self.client.get(
            '/release?id=%d&name=%s&number=%d' % (
                self.build_id, release.name, release.number),
            follow_redirects=True)
        self.assertEquals('200 OK', resp.status)
        self.assertIn('1 tested', resp.data)
        self.assertIn('All passing', resp.data)

    def testCrawler(self):
        """Tests that the crawler behaves well.

        Specifically:
            - Finds new links in HTML data
            - Avoids non-HTML pages
            - Respects ignore patterns specified on flags
            - Properly handles 404s
        """
        @webserver
        def test(path):
            if path == '/':
                return 200, 'text/html', (
                    'Hello world! <a href="/stuff">x</a> '
                    '<a href="/ignore">y</a> and also '
                    '<a href="/missing">z</a>')
            elif path == '/stuff':
                return 200, 'text/html', 'Stuff page <a href="/avoid">x</a>'
            elif path == '/missing':
                return 404, 'text/plain', 'Nope'
            elif path == '/avoid':
                return 200, 'text/plain', 'Ignore me!'

        site_diff.real_main(
            start_url=test.server_prefix + '/',
            upload_build_id=self.build_id,
            upload_release_name=self.release_name,
            ignore_prefixes=['/ignore'])

        release = wait_for_release(self.build_id, self.release_name)
        run_list = models.Run.query.all()
        found = set(run.name for run in run_list)

        expected = set(['/', '/stuff'])
        self.assertEquals(expected, found)

        test.shutdown()


class HtmlRewritingTest(unittest.TestCase):
    """Tests the HTML rewriting functions."""

    def testAll(self):
        """Tests all the variations."""
        base_url = 'http://www.example.com/my-url/here'
        def test(test_url):
            data = '<a href="%s">my link here</a>' % test_url
            result = site_diff.extract_urls(base_url, data)
            if not result:
                return None
            return list(result)[0]

        self.assertEquals('http://www.example.com/my-url/dummy_page2.html',
                          test('dummy_page2.html'))

        self.assertEquals('http://www.example.com/',
                          test('/'))

        self.assertEquals('http://www.example.com/mypath-here',
                          test('/mypath-here'))

        self.assertEquals(None, test('#fragment-only'))

        self.assertEquals('http://www.example.com/my/path/over/here.html',
                          test('/my/path/01/13/../../over/here.html'))

        self.assertEquals('http://www.example.com/my/path/01/over/here.html',
                          test('/my/path/01/13/./../over/here.html'))

        self.assertEquals('http://www.example.com/my-url/same-directory.html',
                          test('same-directory.html'))

        self.assertEquals('http://www.example.com/relative-but-no/child',
                          test('../../relative-but-no/child'))

        self.assertEquals('http://www.example.com/too/many/relative/paths',
                          test('../../../../too/many/relative/paths'))

        self.assertEquals(
            'http://www.example.com/this/is/scheme-relative.html',
            test('//www.example.com/this/is/scheme-relative.html'))

        self.assertEquals(
            'http://www.example.com/okay-then',    # Scheme changed
            test('https://www.example.com/okay-then#blah'))

        self.assertEquals('http://www.example.com/another-one',
                          test('http://www.example.com/another-one'))

        self.assertEquals('http://www.example.com/this-has/a',
                          test('/this-has/a?query=string'))

        self.assertEquals(
            'http://www.example.com/this-also-has/a/',
            test('/this-also-has/a/?query=string&but=more-complex'))

        self.assertEquals(
            'http://www.example.com/relative-with/some-(parenthesis%20here)',
            test('/relative-with/some-(parenthesis%20here)'))

        self.assertEquals(
            'http://www.example.com/relative-with/some-(parenthesis%20here)',
            test('//www.example.com/relative-with/some-(parenthesis%20here)'))

        self.assertEquals(
            'http://www.example.com/relative-with/some-(parenthesis%20here)',
            test('http://www.example.com/relative-with/some-'
                 '(parenthesis%20here)'))


def main(argv):
    gflags.MarkFlagAsRequired('phantomjs_binary')
    gflags.MarkFlagAsRequired('phantomjs_script')

    try:
        argv = FLAGS(argv)
    except gflags.FlagsError, e:
        print '%s\nUsage: %s ARGS\n%s' % (e, sys.argv[0], FLAGS)
        sys.exit(1)

    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main(argv=argv)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = workers_test
#!/usr/bin/env python
# Copyright 2013 Brett Slatkin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the workers module."""

import Queue
import logging
import sys
import time
import unittest

# Local Libraries
import gflags
FLAGS = gflags.FLAGS

# Local modules
from dpxdt.client import fetch_worker
from dpxdt.client import workers
from dpxdt.client import timer_worker


class EchoThread(workers.WorkerThread):
    def handle_item(self, item):
        if item.should_die:
            raise Exception('Dying on %d' % item.input_number)
        item.output_number = item.input_number
        return item


class EchoItem(workers.WorkItem):
    def __init__(self, number, should_die=False):
        workers.WorkItem.__init__(self)
        self.input_number = number
        self.output_number = None
        self.should_die = should_die


class EchoChild(workers.WorkflowItem):
    def run(self, number, should_die=False, wait_seconds=0):
        if wait_seconds > 0:
            yield timer_worker.TimerItem(wait_seconds)
        item = yield EchoItem(number, should_die=should_die)
        raise workers.Return(item.output_number)


class EchoChildWorkflow(workers.WorkflowItem):
    def run(self, number, should_die=False, wait_seconds=0):
        if wait_seconds > 0:
            yield timer_worker.TimerItem(wait_seconds)
        if should_die:
            try:
                yield EchoChild(number, should_die=should_die)
            except Exception, e:
                raise e
        raise workers.Return(number)


class RootWorkflow(workers.WorkflowItem):
    def run(self, child_count, die_on=-1):
        total = 0
        for i in xrange(child_count):
            number = yield EchoChild(i, should_die=(die_on == i))
            assert number is i
            total += number
        self.result = total  # Don't raise to test StopIteration


class GeneratorExceptionChild(workers.WorkflowItem):
    def run(self):
        number = yield EchoChild(4, should_die=False)
        raise Exception('My exception here %d' % number)


class GeneratorExceptionReraiseParent(workers.WorkflowItem):
    def run(self):
        try:
            yield GeneratorExceptionChild()
        except Exception, e:
            assert str(e) == 'My exception here 4', str(e)
            raise Exception('Another exception')


class RootGeneratorExceptionWorkflow(workers.WorkflowItem):
    def run(self):
        try:
            print 'up here'
            yield GeneratorExceptionReraiseParent()
        except Exception, e:
            assert str(e) == 'Another exception', str(e)
            raise workers.Return('good')
        else:
            raise workers.Return('bad')


class RootWaitAllWorkflow(workers.WorkflowItem):
    def run(self, child_count):
        wait_all = [EchoItem(i) for i in xrange(child_count)]
        output = yield wait_all
        raise workers.Return(sum(x.output_number for x in output))


class RootWaitAnyWorkflow(workers.WorkflowItem):
    def run(self):
        output = yield workers.WaitAny([
            EchoItem(10),
            EchoChild(42),
            EchoItem(2),
            EchoItem(25),
        ])
        # At least one EchoItem will be done. We don't know exactly because
        # the jobs WorkflowItems in WaitAny are inserted into a dictionary
        # so their completion ordering is non-deterministic.
        assert len([x for x in output if x.done]) >= 1
        # The EchoChild will not be ready yet.
        assert not output[1].done

        yield timer_worker.TimerItem(2)

        results = yield output
        # Now everything will be done.
        assert len([x for x in output if x.done]) >= 1
        assert results[0].done and results[0].output_number == 10
        assert results[1] == 42
        assert results[2].done and results[2].output_number == 2
        assert results[3].done and results[3].output_number == 25

        raise workers.Return('Donezo')


class RootWaitAnyExceptionWorkflow(workers.WorkflowItem):
    def run(self):
        output = yield workers.WaitAny([
            EchoChild(42, should_die=True),
            EchoItem(10),
            EchoItem(33),
        ])
        assert len([x for x in output if x.done]) == 2
        assert not output[0].done
        assert output[1].done and output[1].output_number == 10
        assert output[2].done and output[2].output_number == 33

        yield timer_worker.TimerItem(2)

        try:
            yield output
        except Exception, e:
            raise workers.Return(str(e))
        else:
            assert False, 'Should have raised'


class FireAndForgetEchoItem(EchoItem):
    fire_and_forget = True


class RootFireAndForgetWorkflow(workers.WorkflowItem):
    def run(self):
        job1 = FireAndForgetEchoItem(10)
        result = yield job1
        print result
        assert result is job1
        assert not result.done

        result = yield EchoItem(25)
        assert result.done
        assert result.output_number == 25

        job2 = EchoItem(30)
        job2.fire_and_forget = True
        result = yield job2
        assert result is job2
        assert not result.done

        job3 = FireAndForgetEchoItem(66)
        job3.fire_and_forget = False
        result = yield job3
        assert result is job3
        assert result.done
        assert result.output_number == 66

        job4 = EchoChild(22)
        job4.fire_and_forget = True
        result = yield job4
        assert result is job4
        assert not result.done

        yield timer_worker.TimerItem(2)
        assert job1.done
        assert job1.output_number == 10
        assert job2.done
        assert job2.output_number == 30
        assert job4.done
        assert job4.result == 22

        raise workers.Return('Okay')


class RootFireAndForgetExceptionWorkflow(workers.WorkflowItem):
    def run(self):
        job = EchoChild(99, should_die=True)
        job.fire_and_forget = True
        result = yield job
        assert result is job
        assert not result.done
        assert not result.error

        result = yield EchoItem(25)
        assert result.done
        assert result.output_number == 25

        yield timer_worker.TimerItem(2)
        assert job.done
        assert str(job.error[1]) == 'Dying on 99'

        raise workers.Return('No fire and forget error')


class RootFireAndForgetMultipleExceptionWorkflow(workers.WorkflowItem):
    def run(self):
        jobs = []
        for i in xrange(3):
            job = EchoChildWorkflow(99, should_die=True, wait_seconds=i*0.5)
            job.fire_and_forget = True
            result = yield job
            assert result is job
            assert not result.done
            assert not result.error
            jobs.append(job)

        yield timer_worker.TimerItem(0.5)

        assert jobs[0].done
        assert jobs[1].done is False
        assert jobs[2].done is False

        # for i, job in enumerate(jobs):
        #     print '%d is done %r' % (i, job.done)
        #     # assert str(job.error[1]) == 'Dying on 99'

        yield timer_worker.TimerItem(1.5)

        assert jobs[0].done
        assert jobs[1].done
        assert jobs[2].done

        raise workers.Return('All errors seen')


class RootWaitAnyFireAndForget(workers.WorkflowItem):
    def run(self):
        output = yield workers.WaitAny([
            FireAndForgetEchoItem(22),
            EchoItem(14),
            EchoChild(98),
        ])
        assert output[0].done
        assert output[1].done
        assert not output[2].done

        # Yielding here will let the next pending WorkflowItem to run,
        # causing output #3 to finish.
        result = yield output
        assert result[2] == 98

        raise workers.Return('All done')


class RootWaitAllFireAndForget(workers.WorkflowItem):
    def run(self):
        output = yield [
            FireAndForgetEchoItem(22),
            EchoItem(14),
            EchoChild(98),
        ]
        assert output[0].done
        assert output[1].done
        assert output[2] == 98

        raise workers.Return('Waited for all of them')


class WorkflowThreadTest(unittest.TestCase):
    """Tests for the WorkflowThread worker."""

    def setUp(self):
        """Sets up the test harness."""
        FLAGS.fetch_frequency = 100
        FLAGS.polltime = 0.01
        self.coordinator = workers.get_coordinator()

        self.echo_queue = Queue.Queue()
        self.coordinator.register(EchoItem, self.echo_queue)
        self.coordinator.register(FireAndForgetEchoItem, self.echo_queue)
        self.coordinator.worker_threads.append(
            EchoThread(self.echo_queue, self.coordinator.input_queue))

        self.timer_queue = Queue.Queue()
        self.coordinator.register(timer_worker.TimerItem, self.timer_queue)
        self.coordinator.worker_threads.append(
            timer_worker.TimerThread(
                self.timer_queue, self.coordinator.input_queue))

        self.coordinator.start()

    def tearDown(self):
        """Cleans up the test harness."""
        self.coordinator.stop()
        self.coordinator.join()
        # Nothing should be pending in the coordinator
        self.assertEquals(0, len(self.coordinator.pending))

    def testMultiLevelWorkflow(self):
        """Tests a multi-level workflow."""
        work = RootWorkflow(5)
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()

        self.assertTrue(work is finished)
        finished.check_result()    # Did not raise
        self.assertEquals(4 + 3 + 2 + 1 + 0, work.result)

    def testMultiLevelWorkflowException(self):
        """Tests when a child of a child raises an exception."""
        work = RootWorkflow(5, die_on=3)
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()

        self.assertTrue(work is finished)
        try:
            finished.check_result()
        except Exception, e:
            self.assertEquals('Dying on 3', str(e))

    def testWorkflowExceptionPropagation(self):
        """Tests when workflow items in a hierarchy re-raise exceptions."""
        work = RootGeneratorExceptionWorkflow()
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()

        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals('good', work.result)

    def testWaitAll(self):
        """Tests waiting on all items in a list of work."""
        work = RootWaitAllWorkflow(4)
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()
        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals(6, work.result)

    def testWaitAny(self):
        """Tests using the WaitAny class."""
        work = RootWaitAnyWorkflow()
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()
        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals('Donezo', work.result)

    def testWaitAnyException(self):
        """Tests using the WaitAny class when an exception is raised."""
        work = RootWaitAnyExceptionWorkflow()
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()
        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals('Dying on 42', work.result)

    def testFireAndForget(self):
        """Tests running fire-and-forget WorkItems."""
        work = RootFireAndForgetWorkflow()
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()
        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals('Okay', work.result)

    def testFireAndForgetException(self):
        """Tests that exceptions from fire-and-forget WorkItems are ignored."""
        work = RootFireAndForgetExceptionWorkflow()
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()
        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals('No fire and forget error', work.result)

    def testFireAndForgetException_MultiLevel(self):
        """Tests exceptions in multi-level fire-and-forget work items."""
        work = RootFireAndForgetMultipleExceptionWorkflow()
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()
        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals('All errors seen', work.result)

    def testWaitAnyFireAndForget(self):
        """Tests wait any with a mix of blocking and non-blocking items."""
        work = RootWaitAnyFireAndForget()
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()
        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals('All done', work.result)

    def testWaitAllFireAndForget(self):
        """Tests wait all with a mix of blocking and non-blocking items."""
        work = RootWaitAllFireAndForget()
        work.root = True
        self.coordinator.input_queue.put(work)
        finished = self.coordinator.output_queue.get()
        self.assertTrue(work is finished)
        finished.check_result()
        self.assertEquals('Waited for all of them', work.result)


class TimerThreadTest(unittest.TestCase):
    """Tests for the TimerThread."""

    def setUp(self):
        """Tests setting up the test harness."""
        self.timer_queue = Queue.Queue()
        self.output_queue = Queue.Queue()
        self.worker = timer_worker.TimerThread(
            self.timer_queue, self.output_queue)

    def testSimple(self):
        """Tests simple waiting."""
        self.worker.start()
        one = timer_worker.TimerItem(0.8)
        two = timer_worker.TimerItem(0.5)
        three = timer_worker.TimerItem(0.1)

        # T = 0, one = 0
        begin = time.time()
        self.timer_queue.put(one)
        time.sleep(0.2)
        # T = 0.2, one = 0.2, two = 0
        self.timer_queue.put(two)
        time.sleep(0.2)
        # T = 0.4, one = 0.4, two = 0.2
        self.timer_queue.put(three)
        time.sleep(0.2)
        # T = 0.6, one = 0.6, two = 0.4, three = 0.1 ready!
        output_three = self.output_queue.get()
        time.sleep(0.1)
        # T = 0.7, one = 0.7, two = 0.5 ready!
        output_two = self.output_queue.get()
        # T = 0.8, one = 0.8 ready!
        output_one = self.output_queue.get()
        end = time.time()

        self.assertEquals(one.delay_seconds, output_one.delay_seconds)
        self.assertEquals(two.delay_seconds, output_two.delay_seconds)
        self.assertEquals(three.delay_seconds, output_three.delay_seconds)

        elapsed = end - begin
        self.assertTrue(1.0 > elapsed > 0.7)


def main(argv):
    logging.getLogger().setLevel(logging.DEBUG)
    argv = FLAGS(argv)
    unittest.main(argv=argv)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
