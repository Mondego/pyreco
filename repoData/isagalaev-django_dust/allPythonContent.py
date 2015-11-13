__FILENAME__ = base

class BaseRetryStorage(object):
    """Plugable interface for retry queue storage"""
    fields = ['operation', 'target_host', 'source_host', 'filename']
    
    def count(self):
        """Returs total retry count"""
        raise NotImplementedError

    def all(self):
        """Returns all retries in queue"""
        raise NotImplementedError

    def create(self, **kwargs):
        """Creates new retry object in queue"""
        raise NotImplementedError

    def delete(self, retry):
        """Deletes given retry object from queue"""
        raise NotImplementedError

    def filter_by_filename(self, filename):
        """Returns retry objects for given file name"""
        raise NotImplementedError
########NEW FILE########
__FILENAME__ = db
from itertools import imap

from django_dust.backends.base import BaseRetryStorage

from django_dust.models import Retry

class RetryStorage(BaseRetryStorage):
    fields = BaseRetryStorage.fields + ['id']
    
    def count(self):
        return Retry.objects.count()

    def all(self):
        return imap(self._to_dict, Retry.objects.all())

    def create(self, **kwargs):
        for key in kwargs.iterkeys():
            if key not in self.field:
                raise ValueError('Illegal retry object field: %s', key)

        Retry.objects.create(**kwargs)

    def delete(self, retry):
        if 'id' not in retry:
            raise ValueError('Retry object must have id value')
        return Retry.objects.filter(pk=retry['id']).delete()

    def filter_by_filename(self, filename):
        return imap(self._to_dict, Retry.objects.filter(filename=filename))

    def _to_dict(self, instance):
        return dict([(field, getattr(instance, field)) for field in self.fields])

########NEW FILE########
__FILENAME__ = http
# -*- coding:utf-8 -*-
import httplib2
from urlparse import urlsplit

from django_dust.settings import getsetting


class HTTPError(Exception):
    pass


class HTTPTransport(object):
    '''
    Transport for doing actual saving and deleting files on remote machines.
    Uses httplib2 and expects that target HTTP host support PUT and DELETE
    methods (apart from the all usual).
    '''
    timeout = getsetting('DUST_TIMEOUT')

    def __init__(self, base_url):
        scheme, host, path, query, fragment = urlsplit(base_url)
        self.scheme = scheme or 'http'
        self.url_path = path or '/'

    def _get_url(self, host, name):
        '''
        Constructs a full URL for a given host and file name.
        '''
        return '%s://%s%s%s' % (self.scheme, host, self.url_path, name)

    def _headers(self, host, name):
        '''
        Gets headers of an HTTP response for a given file name using HEAD
        request. Used in `exists` and `size`.
        '''
        http = httplib2.Http(timeout=self.timeout)
        url = self._get_url(host, name)
        response, response_body = http.request(url, 'HEAD')
        if response.status >= 400 and response.status != 404:
            raise HTTPError('HEAD', url, response.status)
        return response

    # Public interface of a transport. Transport should support following
    # methods:
    #
    # - put     uploading a file
    # - delete  deleting a file
    # - get     getting a file's contents
    # - exists  test if a file exists
    # - size    get a file size
    #
    # All methods are free to raise appropriate exceptions if some functionality
    # is not supported.

    def put(self, host, name, body):
        http = httplib2.Http(timeout=self.timeout)
        url = self._get_url(host, name)
        response, response_body = http.request(url, 'PUT',
            body=body,
            headers={'Content-type': 'application/octet-stream'}
        )
        if response.status >= 400:
            raise HTTPError('PUT', url, response.status)

    def delete(self, host, name):
        http = httplib2.Http(timeout=self.timeout)
        url = self._get_url(host, name)
        response, response_body = http.request(url, 'DELETE')
        if response.status >= 400 and response.status != 404:
            raise HTTPError('DELETE', url, response.status)

    def get(self, host, name):
        http = httplib2.Http(timeout=self.timeout)
        url = self._get_url(host, name)
        response, response_body = http.request(url, 'GET')
        if response.status >= 400:
            raise HTTPError('GET', url, response.status)
        return response_body

    def exists(self, host, name):
        response = self._headers(host, name)
        return response.status == 200

    def size(self, host, name):
        response = self._headers(host, name)
        try:
            return int(response['content-length'])
        except (KeyError, ValueError):
            raise Exception('Invalid or missing content length for %s: "%s"' % (
                name,
                response.get('content-length'),
            ))

########NEW FILE########
__FILENAME__ = process_failed_media
# -*- coding:utf-8 -*-
'''
Command for processing a queue of failed media distribution operations
(puts and deletes). It's expected to be called periodically by a scheduler.

Reports are sent to a logger named 'django_dust'.
'''
import socket
import logging

from django.core.management.base import NoArgsCommand

from django_dust import retry_storage
from django_dust.storage import DistributedStorage
from django_dust.http import HTTPError

logger = logging.getLogger('django_dust')

def _to_unicode(retry):
    return u'%(operation)s %(target_host)s %(filename)s' % retry

class Command(NoArgsCommand):
    help = "Retries failed attempts to distribute media files among media servers"

    def handle_noargs(self, **options):
        logger.info('Initializing storage')
        storage = DistributedStorage()
        retries = retry_storage.all()
        logger.info('Retries to process: %s' % len(retries))
        for retry in retries:
            logger.info('Retry: %s' % _to_unicode(retry))
            try:
                if retry['operation'] == 'put':
                    body = storage.transport.get(retry['source_host'], retry['filename'])
                    storage.transport.put(retry['target_host'], retry['filename'], body)
                if retry['operation'] == 'delete':
                    storage.transport.delete(retry['target_host'], retry['filename'])
                retry_storage.delete(retry)
            except (socket.error, HTTPError), e:
                logger.warning('Retry <%s> not processed: %s' % (_to_unicode(retry), e))
                pass
        logger.info('Done processing retries. Remaning: %s' % retry_storage.count())

########NEW FILE########
__FILENAME__ = models
# -*- coding:utf-8 -*-
from datetime import datetime

from django.db import models

FILE_OPERATIONS = (
    ('put', 'put'),
    ('delete', 'delete'),
)


class Retry(models.Model):
    '''
    Failed attempts of file operations on remote hosts that need to
    be retried periodically.
    '''
    created = models.DateTimeField(default=datetime.now)
    operation = models.CharField(max_length=20, choices=FILE_OPERATIONS, blank=True)
    target_host = models.CharField(max_length=50)
    filename = models.CharField(max_length=100)
    source_host = models.CharField(max_length=50)

    def __unicode__(self):
        return u'%s %s %s' % (self.get_operation_display(), self.target_host, self.filename)

########NEW FILE########
__FILENAME__ = settings
'''
Default values for settings.
If you want to change these settings define them in your project's settings
file.
'''

def getsetting(name, defaults=locals()):
    '''
    Tries to get a setting from Django's default settings object. If not
    available returns a local default.
    '''
    from django.conf import settings
    return getattr(settings, name, defaults.get(name))

# Retry storage backend setting -- import path for storage module
# Default is DB backend
DUST_RETRY_STORAGE_BACKEND = 'django_dust.backends.db'

# Timeout in seconds for accessing hosts over network. Defaults to 2.
DUST_TIMEOUT = 2

# List of file storage hosts
DUST_HOSTS = ['127.0.0.1']

# Whether to use a local file system. If files are stored on those same
# servers that handle web requests then setting this flag to True
# allows django_dust to access files locally saving time and bandwidth
# on existence checking operations. Defaults to False.
DUST_USE_LOCAL_FS = False

########NEW FILE########
__FILENAME__ = storage
# -*- coding:utf-8 -*-
from threading import Thread
import socket
import random
import urlparse

from django.core.files import base
from django.core.files.storage import Storage, FileSystemStorage
from django.conf import settings

from django_dust import http
from django_dust.settings import getsetting


class DistributionError(IOError):
    pass


class DistributedStorage(Storage):
    '''
    DistributedStorage saves files by copying them on several servers listed
    in settings.DUST_HOSTS.
    '''
    def __init__(self, hosts=None, use_local=None, base_url=settings.MEDIA_URL, **kwargs):
        super(DistributedStorage, self).__init__(**kwargs)
        if hosts is None:
            hosts = getsetting('DUST_HOSTS')
        self.hosts = hosts
        if use_local is None:
            use_local = getsetting('DUST_USE_LOCAL_FS')
        self.local_storage = use_local and FileSystemStorage(base_url=base_url, **kwargs)
        self.base_url = base_url
        self.transport = http.HTTPTransport(base_url=base_url)

    def _execute(self, func, name, args):
        '''
        Runs an operation (put or delete) over several hosts at once in multiple
        threads.
        '''
        def run(index, host):
            try:
                results[index] = func(host, name, *args)
            except Exception, e:
                results[index] = (e)

        # Run distribution threads keeping result of each operation in `results`.
        results = [None] * len(self.hosts)
        threads = [Thread(target=run, args=(index, h)) for index, h in enumerate(self.hosts)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        exceptions = []
        for host, result in zip(self.hosts, results):
            if result is None: # no errors, remember successful_host to use in retries
                successful_host = host
                break
        else:
            successful_host = None

        # All `socket.error` exceptions are not fatal meaning that a host might
        # be temporarily unavailable. Those operations are kept in a queue in
        # database to be retried later.
        # All other errors mean in most casess misconfigurations and are fatal
        # for the whole distributed operation.
        for host, result in zip(self.hosts, results):
            if isinstance(result, socket.error):
                if successful_host is not None:
                    from django_dust import retry_storage # this causes errors when imported at module level
                    retry_storage.create(
                        operation=func.__name__,
                        target_host=host,
                        source_host=successful_host,
                        filename=name,
                    )
                else:
                    exceptions.append(result)
            elif isinstance(result, Exception):
                exceptions.append(result)
        if exceptions:
            raise DistributionError(*exceptions)

    def _open(self, name, mode='rb'):
        if mode != 'rb':
            # In future when allowed to operate locally (self.local_storage)
            # all modes can be allowed. However this will require executing
            # distribution upon closing file opened for updates. This worth
            # evaluating.
            raise IOError('Illegal mode "%s". Only "rb" is supported.')
        if self.local_storage:
            return self.local_storage.open(name, mode)
        host = random.choice(self.hosts)
        return base.ContentFile(self.transport.get(host, name))

    def _save(self, name, content):
        content.seek(0)
        body = content.read()
        self._execute(self.transport.put, name, [body])
        return name

    def get_available_name(self, name):
        from django_dust import retry_storage # this causes errors when imported at module level
        while self.exists(name) or retry_storage.filter_by_filename(name):
            try:
                dot_index = name.rindex('.')
            except ValueError: # filename has no dot
                name += '_'
            else:
                name = name[:dot_index] + '_' + name[dot_index:]
        return name

    def path(self, name):
        if self.local_storage:
            return self.local_storage.path(name)
        return super(DistributedStorage, self).path(name)

    def delete(self, name):
        self._execute(self.transport.delete, name, [])

    def exists(self, name):
        if self.local_storage:
            return self.local_storage.exists(name)
        return self.transport.exists(random.choice(self.hosts), name)

    def listdir(self, path):
        if self.local_storage:
            return self.local_storage.listdir(path)
        raise NotImplementedError()

    def size(self, name):
        if self.local_storage:
            return self.local_storage.size(name)
        return self.transport.size(random.choice(self.hosts), name)

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self.base_url, name).replace('\\', '/')

########NEW FILE########
