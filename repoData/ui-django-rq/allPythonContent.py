__FILENAME__ = admin
from django.contrib import admin
from django_rq import settings


if settings.SHOW_ADMIN_LINK:
    admin.site.index_template = 'django_rq/index.html'
########NEW FILE########
__FILENAME__ = decorators
from rq.decorators import job as _rq_job

from .queues import get_queue


def job(func_or_queue, connection=None, *args, **kwargs):
    """
    The same as RQ's job decorator, but it works automatically works out
    the ``connection`` argument from RQ_QUEUES.

    And also, it allows simplified ``@job`` syntax to put job into
    default queue.
    """
    if callable(func_or_queue):
        func = func_or_queue
        queue = 'default'
    else:
        func = None
        queue = func_or_queue

    try:
        from django.utils import six
        string_type = six.string_types
    except ImportError:
        # for django lt v1.5 and python 2
        string_type = basestring

    if isinstance(queue, string_type):
        try:
            queue = get_queue(queue)
            if connection is None:
                connection = queue.connection
        except KeyError:
            pass

    decorator = _rq_job(queue, connection=connection, *args, **kwargs)
    if func:
        return decorator(func)
    return decorator


########NEW FILE########
__FILENAME__ = rqscheduler
from django.core.management.base import BaseCommand
from optparse import make_option
from django_rq import get_scheduler


class Command(BaseCommand):
    """
    Runs RQ scheduler
    """
    help = __doc__
    args = '<queue>'

    option_list = BaseCommand.option_list + (
        make_option(
            '--interval',
            type=int,
            dest='interval',
            default=60,
            help="How often the scheduler checks for new jobs to add to the "
                 "queue (in seconds).",
        ),
    )

    def handle(self, queue='default', *args, **options):
        scheduler = get_scheduler(name=queue, interval=options.get('interval'))
        scheduler.run()

########NEW FILE########
__FILENAME__ = rqworker
import logging
from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils.log import dictConfig

from redis.exceptions import ConnectionError

from django_rq.queues import get_queues

from rq import use_connection
import importlib

# Setup logging for RQWorker if not already configured
logger = logging.getLogger('rq.worker')
if not logger.handlers:
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "rq_console": {
                "format": "%(asctime)s %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },

        "handlers": {
            "rq_console": {
                "level": "DEBUG",
                #"class": "logging.StreamHandler",
                "class": "rq.utils.ColorizingStreamHandler",
                "formatter": "rq_console",
                "exclude": ["%(asctime)s"],
            },
        },

        "worker": {
            "handlers": ["rq_console"],
            "level": "DEBUG"
        }
    })

    
# Copied from rq.utils
def import_attribute(name):
    """Return an attribute from a dotted path name (e.g. "path.to.func")."""
    module_name, attribute = name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


class Command(BaseCommand):
    """
    Runs RQ workers on specified queues. Note that all queues passed into a
    single rqworker command must share the same connection.

    Example usage:
    python manage.py rqworker high medium low
    """
    option_list = BaseCommand.option_list + (
        make_option(
            '--burst',
            action='store_true',
            dest='burst',
            default=False,
            help='Run worker in burst mode'
        ),
        make_option(
            '--worker-class',
            action='store',
            dest='worker_class',
            default='rq.Worker',
            help='RQ Worker class to use'
        ),
        make_option(
            '--name',
            action='store',
            dest='name',
            default=None,
            help='Name of the worker'
        ),
    )
    args = '<queue queue ...>'

    def handle(self, *args, **options):
        try:
            # Instantiate a worker
            worker_class = import_attribute(options.get('worker_class', 'rq.Worker'))
            queues = get_queues(*args)
            w = worker_class(queues, connection=queues[0].connection, name=options['name'])

            # Call use_connection to push the redis connection into LocalStack
            # without this, jobs using RQ's get_current_job() will fail
            use_connection(w.connection)
            w.work(burst=options.get('burst', False))
        except ConnectionError as e:
            print(e)

########NEW FILE########
__FILENAME__ = models
from django.core.signals import got_request_exception, request_finished

from django_rq import thread_queue
from .queues import get_commit_mode


# If we're not in AUTOCOMMIT mode, wire up request finished/exception signal
if not get_commit_mode():
    request_finished.connect(thread_queue.commit)
    got_request_exception.connect(thread_queue.clear)

########NEW FILE########
__FILENAME__ = queues
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

import redis
from rq.queue import FailedQueue, Queue

from django_rq import thread_queue


def get_commit_mode():
    """
    Disabling AUTOCOMMIT causes enqueued jobs to be stored in a temporary queue.
    Jobs in this queue are only enqueued after the request is completed and are
    discarded if the request causes an exception (similar to db transactions).

    To disable autocommit, put this in settings.py:
    RQ = {
        'AUTOCOMMIT': False,
    }
    """
    RQ = getattr(settings, 'RQ', {})
    return RQ.get('AUTOCOMMIT', True)


class DjangoRQ(Queue):
    """
    A subclass of RQ's QUEUE that allows jobs to be stored temporarily to be
    enqueued later at the end of Django's request/response cycle.
    """

    def __init__(self, *args, **kwargs):
        autocommit = kwargs.pop('autocommit', None)
        self._autocommit = get_commit_mode() if autocommit is None else autocommit
        return super(DjangoRQ, self).__init__(*args, **kwargs)

    def original_enqueue_call(self, *args, **kwargs):
        return super(DjangoRQ, self).enqueue_call(*args, **kwargs)

    def enqueue_call(self, *args, **kwargs):
        # print args, kwargs
        if self._autocommit:
            return self.original_enqueue_call(*args, **kwargs)
        else:
            thread_queue.add(self, args, kwargs)


def get_redis_connection(config):
    """
    Returns a redis connection from a connection config
    """
    if 'URL' in config:
        return redis.from_url(config['URL'], db=config['DB'])
    if 'USE_REDIS_CACHE' in config.keys():

        from django.core.cache import get_cache
        cache = get_cache(config['USE_REDIS_CACHE'])

        if hasattr(cache, 'client'):
            # We're using django-redis. The cache's `client` attribute
            # is a pluggable backend that return its Redis connection as
            # its `client`
            try:
                # To get Redis connection on django-redis >= 3.4.0
                # we need to use cache.client.get_client() instead of
                # cache.client.client used in older versions
                try:
                    return cache.client.get_client()
                except AttributeError:
                    return cache.client.client
            except NotImplementedError:
                pass
        else:
            # We're using django-redis-cache
            return cache._client

    return redis.Redis(host=config['HOST'],
                       port=config['PORT'], db=config['DB'],
                       password=config.get('PASSWORD', None))


def get_connection(name='default'):
    """
    Returns a Redis connection to use based on parameters in settings.RQ_QUEUES
    """
    from .settings import QUEUES
    return get_redis_connection(QUEUES[name])


def get_connection_by_index(index):
    """
    Returns a Redis connection to use based on parameters in settings.RQ_QUEUES
    """
    from .settings import QUEUES_LIST
    return get_redis_connection(QUEUES_LIST[index]['connection_config'])


def get_queue(name='default', default_timeout=None, async=None,
              autocommit=None):
    """
    Returns an rq Queue using parameters defined in ``RQ_QUEUES``
    """
    from .settings import QUEUES

    # If async is provided, use it, otherwise, get it from the configuration
    if async is None:
        async = QUEUES[name].get('ASYNC', True)

    return DjangoRQ(name, default_timeout=default_timeout,
                    connection=get_connection(name), async=async,
                    autocommit=autocommit)


def get_queue_by_index(index):
    """
    Returns an rq Queue using parameters defined in ``QUEUES_LIST``
    """
    from .settings import QUEUES_LIST
    config = QUEUES_LIST[int(index)]
    if config['name'] == 'failed':
        return FailedQueue(connection=get_redis_connection(config['connection_config']))
    return DjangoRQ(
        config['name'],
        connection=get_redis_connection(config['connection_config']),
        async=config.get('ASYNC', True))


def get_failed_queue(name='default'):
    """
    Returns the rq failed Queue using parameters defined in ``RQ_QUEUES``
    """
    return FailedQueue(connection=get_connection(name))


def get_queues(*queue_names, **kwargs):
    """
    Return queue instances from specified queue names.
    All instances must use the same Redis connection.
    """
    from .settings import QUEUES
    autocommit = kwargs.get('autocommit', None)
    if len(queue_names) == 0:
        # Return "default" queue if no queue name is specified
        return [get_queue(autocommit=autocommit)]
    if len(queue_names) > 1:
        connection_params = QUEUES[queue_names[0]]
        for name in queue_names:
            if QUEUES[name] != connection_params:
                raise ValueError(
                    'Queues must have the same redis connection.'
                    '"{0}" and "{1}" have '
                    'different connections'.format(name, queue_names[0]))
    return [get_queue(name, autocommit=autocommit) for name in queue_names]


def enqueue(func, *args, **kwargs):
    """
    A convenience function to put a job in the default queue. Usage::

    from django_rq import enqueue
    enqueue(func, *args, **kwargs)
    """
    return get_queue().enqueue(func, *args, **kwargs)


def get_unique_connection_configs(config=None):
    """
    Returns a list of unique Redis connections from config
    """
    if config is None:
        from .settings import QUEUES
        config = QUEUES

    connection_configs = []
    for key, value in config.items():
        if value not in connection_configs:
            connection_configs.append(value)
    return connection_configs


"""
If rq_scheduler is installed, provide a ``get_scheduler`` function that
behaves like ``get_connection``, except that it returns a ``Scheduler``
instance instead of a ``Queue`` instance.
"""
try:
    from rq_scheduler import Scheduler

    def get_scheduler(name='default', interval=60):
        """
        Returns an RQ Scheduler instance using parameters defined in
        ``RQ_QUEUES``
        """
        return Scheduler(name, interval=interval,
                         connection=get_connection(name))
except ImportError:
    def get_scheduler(*args, **kwargs):
        raise ImproperlyConfigured('rq_scheduler not installed')

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .queues import get_unique_connection_configs

SHOW_ADMIN_LINK = getattr(settings, 'RQ_SHOW_ADMIN_LINK', False)

QUEUES = getattr(settings, 'RQ_QUEUES', None)
if QUEUES is None:
    raise ImproperlyConfigured("You have to define RQ_QUEUES in settings.py")
NAME = getattr(settings, 'RQ_NAME', 'default')
BURST = getattr(settings, 'RQ_BURST', False)

# All queues in list format so we can get them by index, includes failed queues
QUEUES_LIST = []
for key, value in QUEUES.items():
    QUEUES_LIST.append({'name': key, 'connection_config': value})
for config in get_unique_connection_configs():
    QUEUES_LIST.append({'name': 'failed', 'connection_config': config})

########NEW FILE########
__FILENAME__ = tests
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.unittest import skipIf
from django.test.client import Client
from django.test.utils import override_settings
from django.conf import settings

from rq import get_current_job, Queue
from rq.job import Job

from django_rq.decorators import job
from django_rq.queues import (
    get_connection, get_queue, get_queue_by_index, get_queues,
    get_unique_connection_configs
)
from django_rq import thread_queue
from django_rq.workers import get_worker


try:
    from rq_scheduler import Scheduler
    from ..queues import get_scheduler
    RQ_SCHEDULER_INSTALLED = True
except ImportError:
    RQ_SCHEDULER_INSTALLED = False

QUEUES = settings.RQ_QUEUES


def access_self():
    job = get_current_job()
    return job.id


def divide(a, b):
    return a / b


def get_failed_queue_index(name='default'):
    """
    Returns the position of FailedQueue for the named queue in QUEUES_LIST
    """
    # Get the index of FailedQueue for 'default' Queue in QUEUES_LIST
    queue_index = None
    connection = get_connection(name)
    connection_kwargs = connection.connection_pool.connection_kwargs
    for i in range(0, 100):
        q = get_queue_by_index(i)
        if q.name == 'failed' and q.connection.connection_pool.connection_kwargs == connection_kwargs:
            queue_index = i
            break

    return queue_index


def get_queue_index(name='default'):
    """
    Returns the position of Queue for the named queue in QUEUES_LIST
    """
    queue_index = None
    connection = get_connection(name)
    connection_kwargs = connection.connection_pool.connection_kwargs
    for i in range(0, 100):
        q = get_queue_by_index(i)
        if q.name == name and q.connection.connection_pool.connection_kwargs == connection_kwargs:
            queue_index = i
            break
    return queue_index


@override_settings(RQ={'AUTOCOMMIT': True})
class QueuesTest(TestCase):

    def test_get_connection_default(self):
        """
        Test that get_connection returns the right connection based for
        `defaut` queue.
        """
        config = QUEUES['default']
        connection = get_connection()
        connection_kwargs = connection.connection_pool.connection_kwargs
        self.assertEqual(connection_kwargs['host'], config['HOST'])
        self.assertEqual(connection_kwargs['port'], config['PORT'])
        self.assertEqual(connection_kwargs['db'], config['DB'])

    def test_get_connection_test(self):
        """
        Test that get_connection returns the right connection based for
        `test` queue.
        """
        config = QUEUES['test']
        connection = get_connection('test')
        connection_kwargs = connection.connection_pool.connection_kwargs
        self.assertEqual(connection_kwargs['host'], config['HOST'])
        self.assertEqual(connection_kwargs['port'], config['PORT'])
        self.assertEqual(connection_kwargs['db'], config['DB'])

    def test_get_queue_default(self):
        """
        Test that get_queue use the right parameters for `default`
        connection.
        """
        config = QUEUES['default']
        queue = get_queue('default')
        connection_kwargs = queue.connection.connection_pool.connection_kwargs
        self.assertEqual(queue.name, 'default')
        self.assertEqual(connection_kwargs['host'], config['HOST'])
        self.assertEqual(connection_kwargs['port'], config['PORT'])
        self.assertEqual(connection_kwargs['db'], config['DB'])

    def test_get_queue_url(self):
        """
        Test that get_queue use the right parameters for queues using URL for
        connection.
        """
        config = QUEUES['url']
        queue = get_queue('url')
        connection_kwargs = queue.connection.connection_pool.connection_kwargs
        self.assertEqual(queue.name, 'url')
        self.assertEqual(connection_kwargs['host'], 'host')
        self.assertEqual(connection_kwargs['port'], 1234)
        self.assertEqual(connection_kwargs['db'], 4)
        self.assertEqual(connection_kwargs['password'], 'password')

    def test_get_queue_test(self):
        """
        Test that get_queue use the right parameters for `test`
        connection.
        """
        config = QUEUES['test']
        queue = get_queue('test')
        connection_kwargs = queue.connection.connection_pool.connection_kwargs
        self.assertEqual(queue.name, 'test')
        self.assertEqual(connection_kwargs['host'], config['HOST'])
        self.assertEqual(connection_kwargs['port'], config['PORT'])
        self.assertEqual(connection_kwargs['db'], config['DB'])

    def test_get_queues_same_connection(self):
        """
        Checks that getting queues with the same redis connection is ok.
        """
        self.assertEqual(get_queues('test', 'test2'), [get_queue('test'), get_queue('test2')])

    def test_get_queues_different_connections(self):
        """
        Checks that getting queues with different redis connections raise
        an exception.
        """
        self.assertRaises(ValueError, get_queues, 'default', 'test')


    def test_get_unique_connection_configs(self):
        connection_params_1 = {
            'HOST': 'localhost',
            'PORT': 6379,
            'DB': 0,
        }
        connection_params_2 = {
            'HOST': 'localhost',
            'PORT': 6379,
            'DB': 1,
        }
        config = {
            'default': connection_params_1,
            'test': connection_params_2
        }
        self.assertEqual(get_unique_connection_configs(config),
                         [connection_params_1, connection_params_2])
        config = {
            'default': connection_params_1,
            'test': connection_params_1
        }
        # Should return one connection config since it filters out duplicates
        self.assertEqual(get_unique_connection_configs(config),
                         [connection_params_1])

    def test_async(self):
        """
        Checks whether asynchronous settings work
        """
        # Make sure async is not set by default
        defaultQueue = get_queue('default')
        self.assertTrue(defaultQueue._async)

        # Make sure async override works
        defaultQueueAsync = get_queue('default', async=False)
        self.assertFalse(defaultQueueAsync._async)

        # Make sure async setting works
        asyncQueue = get_queue('async')
        self.assertFalse(asyncQueue._async)

    @override_settings(RQ={'AUTOCOMMIT': False})
    def test_autocommit(self):
        """
        Checks whether autocommit is set properly.
        """
        queue = get_queue(autocommit=True)
        self.assertTrue(queue._autocommit)
        queue = get_queue(autocommit=False)
        self.assertFalse(queue._autocommit)
        # Falls back to default AUTOCOMMIT mode
        queue = get_queue()
        self.assertFalse(queue._autocommit)

        queues = get_queues(autocommit=True)
        self.assertTrue(queues[0]._autocommit)
        queues = get_queues(autocommit=False)
        self.assertFalse(queues[0]._autocommit)
        queues = get_queues()
        self.assertFalse(queues[0]._autocommit)


@override_settings(RQ={'AUTOCOMMIT': True})
class DecoratorTest(TestCase):
    def test_job_decorator(self):
        # Ensure that decorator passes in the right queue from settings.py
        queue_name = 'test3'
        config = QUEUES[queue_name]
        @job(queue_name)
        def test():
            pass
        result = test.delay()
        queue = get_queue(queue_name)
        self.assertEqual(result.origin, queue_name)
        result.delete()

    def test_job_decorator_default(self):
        # Ensure that decorator passes in the right queue from settings.py
        @job
        def test():
            pass
        result = test.delay()
        self.assertEqual(result.origin, 'default')
        result.delete()


class ConfigTest(TestCase):
    @override_settings(RQ_QUEUES=None)
    def test_empty_queue_setting_raises_exception(self):
        # Raise an exception if RQ_QUEUES is not defined
        self.assertRaises(ImproperlyConfigured, get_connection)


@override_settings(RQ={'AUTOCOMMIT': True})
class WorkersTest(TestCase):
    def test_get_worker_default(self):
        """
        By default, ``get_worker`` should return worker for ``default`` queue.
        """
        worker = get_worker()
        queue = worker.queues[0]
        self.assertEqual(queue.name, 'default')

    def test_get_worker_specified(self):
        """
        Checks if a worker with specified queues is created when queue
        names are given.
        """
        w = get_worker('test')
        self.assertEqual(len(w.queues), 1)
        queue = w.queues[0]
        self.assertEqual(queue.name, 'test')

    def test_get_current_job(self):
        """
        Ensure that functions using RQ's ``get_current_job`` doesn't fail
        when run from rqworker (the job id is not in the failed queue).
        """
        queue = get_queue()
        job = queue.enqueue(access_self)
        call_command('rqworker', burst=True)
        failed_queue = Queue(name='failed', connection=queue.connection)
        self.assertFalse(job.id in failed_queue.job_ids)
        job.delete()


@override_settings(RQ={'AUTOCOMMIT': True})
class ViewTest(TestCase):

    def setUp(self):
        user = User.objects.create_user('foo', password='pass')
        user.is_staff = True
        user.is_active = True
        user.save()
        self.client = Client()
        self.client.login(username=user.username, password='pass')

    def test_requeue_job(self):
        """
        Ensure that a failed job gets requeued when rq_requeue_job is called
        """
        def failing_job():
            raise ValueError

        queue = get_queue('default')
        queue_index = get_failed_queue_index('default')
        job = queue.enqueue(failing_job)
        worker = get_worker('default')
        worker.work(burst=True)
        job.refresh()
        self.assertTrue(job.is_failed)
        self.client.post(reverse('rq_requeue_job', args=[queue_index, job.id]),
                         {'requeue': 'Requeue'})
        self.assertIn(job, queue.jobs)
        job.delete()

    def test_delete_job(self):
        """
        In addition to deleting job from Redis, the job id also needs to be
        deleted from Queue.
        """
        queue = get_queue('django_rq_test')
        queue_index = get_queue_index('django_rq_test')
        job = queue.enqueue(access_self)
        self.client.post(reverse('rq_delete_job', args=[queue_index, job.id]),
                         {'post': 'yes'})
        self.assertFalse(Job.exists(job.id, connection=queue.connection))
        self.assertNotIn(job.id, queue.job_ids)

    def test_clear_queue(self):
        """Test that the queue clear actually clears the queue."""
        queue = get_queue('django_rq_test')
        queue_index = get_queue_index('django_rq_test')
        job = queue.enqueue(access_self)
        self.client.post(reverse('rq_clear', args=[queue_index]),
                         {'post': 'yes'})
        self.assertFalse(Job.exists(job.id, connection=queue.connection))
        self.assertNotIn(job.id, queue.job_ids)


class ThreadQueueTest(TestCase):

    @override_settings(RQ={'AUTOCOMMIT': True})
    def test_enqueue_autocommit_on(self):
        """
        Running ``enqueue`` when AUTOCOMMIT is on should
        immediately persist job into Redis.
        """
        queue = get_queue()
        job = queue.enqueue(divide, 1, 1)
        self.assertTrue(job.id in queue.job_ids)
        job.delete()

    @override_settings(RQ={'AUTOCOMMIT': False})
    def test_enqueue_autocommit_off(self):
        """
        Running ``enqueue`` when AUTOCOMMIT is off should
        put the job in the delayed queue instead of enqueueing it right away.
        """
        queue = get_queue()
        job = queue.enqueue(divide, 1, b=1)
        self.assertTrue(job is None)
        delayed_queue = thread_queue.get_queue()
        self.assertEqual(delayed_queue[0][0], queue)
        self.assertEqual(delayed_queue[0][1], ())
        kwargs = delayed_queue[0][2]
        self.assertEqual(kwargs['args'], (1,))
        self.assertEqual(kwargs['result_ttl'], None)
        self.assertEqual(kwargs['kwargs'], {'b': 1})
        self.assertEqual(kwargs['func'], divide)
        self.assertEqual(kwargs['timeout'], None)

    def test_commit(self):
        """
        Ensure that commit_delayed_jobs properly enqueue jobs and clears
        delayed_queue.
        """
        queue = get_queue()
        delayed_queue = thread_queue.get_queue()
        queue.empty()
        self.assertEqual(queue.count, 0)
        queue.enqueue_call(divide, args=(1,), kwargs={'b': 1})
        thread_queue.commit()
        self.assertEqual(queue.count, 1)
        self.assertEqual(len(delayed_queue), 0)

    def test_clear(self):
        queue = get_queue()
        delayed_queue = thread_queue.get_queue()
        delayed_queue.append((queue, divide, (1,), {'b': 1}))
        thread_queue.clear()
        delayed_queue = thread_queue.get_queue()
        self.assertEqual(delayed_queue, [])

    @override_settings(RQ={'AUTOCOMMIT': False})
    def test_success(self):
        queue = get_queue()
        queue.empty()
        thread_queue.clear()
        self.assertEqual(queue.count, 0)
        self.client.get(reverse('success'))
        self.assertEqual(queue.count, 1)

    @override_settings(RQ={'AUTOCOMMIT': False})
    def test_error(self):
        queue = get_queue()
        queue.empty()
        self.assertEqual(queue.count, 0)
        url = reverse('error')
        self.assertRaises(ValueError, self.client.get, url)
        self.assertEqual(queue.count, 0)


class SchedulerTest(TestCase):

    @skipIf(RQ_SCHEDULER_INSTALLED is False, 'RQ Scheduler not installed')
    def test_get_scheduler(self):
        """
        Ensure get_scheduler creates a scheduler instance with the right
        connection params for `test` queue.
        """
        config = QUEUES['test']
        scheduler = get_scheduler('test')
        connection_kwargs = scheduler.connection.connection_pool.connection_kwargs
        self.assertEqual(scheduler.queue_name, 'test')
        self.assertEqual(connection_kwargs['host'], config['HOST'])
        self.assertEqual(connection_kwargs['port'], config['PORT'])
        self.assertEqual(connection_kwargs['db'], config['DB'])


class RedisCacheTest(TestCase):

    @skipIf(settings.REDIS_CACHE_TYPE != 'django-redis',
            'django-redis not installed')
    def test_get_queue_django_redis(self):
        """
        Test that the USE_REDIS_CACHE option for configuration works.
        """
        queueName = 'django-redis'
        queue = get_queue(queueName)
        connection_kwargs = queue.connection.connection_pool.connection_kwargs
        self.assertEqual(queue.name, queueName)

        cacheHost = settings.CACHES[queueName]['LOCATION'].split(':')[0]
        cachePort = settings.CACHES[queueName]['LOCATION'].split(':')[1]
        cacheDBNum = settings.CACHES[queueName]['LOCATION'].split(':')[2]

        self.assertEqual(connection_kwargs['host'], cacheHost)
        self.assertEqual(connection_kwargs['port'], int(cachePort))
        self.assertEqual(connection_kwargs['db'], int(cacheDBNum))
        self.assertEqual(connection_kwargs['password'], None)

    @skipIf(settings.REDIS_CACHE_TYPE != 'django-redis-cache',
            'django-redis-cache not installed')
    def test_get_queue_django_redis_cache(self):
        """
        Test that the USE_REDIS_CACHE option for configuration works.
        """
        queueName = 'django-redis-cache'
        queue = get_queue(queueName )
        connection_kwargs = queue.connection.connection_pool.connection_kwargs
        self.assertEqual(queue.name, queueName)

        cacheHost = settings.CACHES[queueName]['LOCATION'].split(':')[0]
        cachePort = settings.CACHES[queueName]['LOCATION'].split(':')[1]
        cacheDBNum = settings.CACHES[queueName]['OPTIONS']['DB']

        self.assertEqual(connection_kwargs['host'], cacheHost)
        self.assertEqual(connection_kwargs['port'], int(cachePort))
        self.assertEqual(connection_kwargs['db'], int(cacheDBNum))
        self.assertEqual(connection_kwargs['password'], None)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    (r'^django-rq/', include('django_rq.urls')),
    url(r'^success/$', 'django_rq.tests.views.success', name='success'),
    url(r'^error/$', 'django_rq.tests.views.error', name='error'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

from django_rq import get_queue


def say_hello():
    return 'Hello'


def success(request):
    queue = get_queue()
    queue.enqueue(say_hello)
    return render(request, 'django_rq/test.html', {})


def error(request):
    queue = get_queue()
    queue.enqueue(say_hello)
    raise ValueError

########NEW FILE########
__FILENAME__ = test_settings
# -*- coding: utf-8 -*-

SECRET_KEY = 'a'

# Detect whether either django-redis or django-redis-cache is installed. This
# is only really used to conditionally configure options for the unit tests.
# In actually usage, no such check is necessary.
try:
    import redis_cache
    if hasattr(redis_cache, 'get_redis_connection'):
        REDIS_CACHE_TYPE = 'django-redis'
    else:
        REDIS_CACHE_TYPE = 'django-redis-cache'
except ImportError:
    REDIS_CACHE_TYPE = 'none'

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django_rq',
]


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

if REDIS_CACHE_TYPE == 'django-redis':
    CACHES = {
        'django-redis': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': 'localhost:6379:2',
            'KEY_PREFIX': 'django-rq-tests',
            'OPTIONS': {
                'CLIENT_CLASS': 'redis_cache.client.DefaultClient',
                'MAX_ENTRIES': 5000,
            },
        },
    }
elif REDIS_CACHE_TYPE == 'django-redis-cache':
    CACHES = {
        'django-redis-cache': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': 'localhost:6379',
            'KEY_PREFIX': 'django-rq-tests',
            'OPTIONS': {
                'DB': 2,
                'MAX_ENTRIES': 5000,
            },
        },
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "rq_console": {
            "format": "%(asctime)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "rq_console": {
            "level": "DEBUG",
            #"class": "logging.StreamHandler",
            "class": "rq.utils.ColorizingStreamHandler",
            "formatter": "rq_console",
            "exclude": ["%(asctime)s"],
        },
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
    },
    'loggers': {
        "rq.worker": {
            "handlers": ['null'],
            "level": "ERROR"
        },
    }
}

RQ_QUEUES = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
    },
    'test': {
        'HOST': 'localhost',
        'PORT': 1,
        'DB': 1,
    },
    'test2': {
        'HOST': 'localhost',
        'PORT': 1,
        'DB': 1,
    },
    'test3': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 1,
    },
    'async': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 1,
        'ASYNC': False,
    },
    'url': {
        'URL': 'redis://username:password@host:1234/',
        'DB': 4,
    },
    'django_rq_test': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
    },
}

RQ = {
    'AUTOCOMMIT': False,
}

if REDIS_CACHE_TYPE == 'django-redis':
    RQ_QUEUES['django-redis'] = {'USE_REDIS_CACHE': 'django-redis'}
elif REDIS_CACHE_TYPE == 'django-redis-cache':
    RQ_QUEUES['django-redis-cache'] = {'USE_REDIS_CACHE': 'django-redis-cache'}

ROOT_URLCONF = 'django_rq.tests.urls'

TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.request",
)

########NEW FILE########
__FILENAME__ = thread_queue
import threading


_thread_data = threading.local()


def get_queue():
    """
    Returns a temporary queue to store jobs before they're committed
    later in the request/responsce cycle. Each job is stored as a tuple
    containing the queue, args and kwargs.

    For example, if we call ``queue.enqueue_call(foo, kwargs={'bar': 'baz'})`` during the
    request/response cycle, job_queue will look like:

    job_queue = [(default_queue, foo, {'kwargs': {'bar': 'baz'}})]

    This implementation is heavily inspired by
    https://github.com/chrisdoble/django-celery-transactions
    """
    return _thread_data.__dict__.setdefault("job_queue", [])


def add(queue, args, kwargs):
    get_queue().append((queue, args, kwargs))


def commit(*args, **kwargs):
    """
    Processes all jobs in the delayed queue.
    """
    delayed_queue = get_queue()
    try:
        while delayed_queue:
            queue, args, kwargs = delayed_queue.pop(0)
            queue.original_enqueue_call(*args, **kwargs)
    finally:
        clear()


def clear(*args, **kwargs):
    try:
        del(_thread_data.job_queue)
    except AttributeError:
        pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns('django_rq.views',
    url(r'^$', 'stats', name='rq_home'),
    url(r'^queues/(?P<queue_index>[\d]+)/$', 'jobs', name='rq_jobs'),
    url(r'^queues/(?P<queue_index>[\d]+)/empty/$', 'clear_queue', name='rq_clear'),
    url(r'^queues/(?P<queue_index>[\d]+)/(?P<job_id>[-\w]+)/$', 'job_detail',
        name='rq_job_detail'),
    url(r'^queues/(?P<queue_index>[\d]+)/(?P<job_id>[-\w]+)/delete/$',
        'delete_job', name='rq_delete_job'),
    url(r'^queues/(?P<queue_index>[\d]+)/(?P<job_id>[-\w]+)/requeue/$',
        'requeue_job_view', name='rq_requeue_job'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import redirect, render

from rq import requeue_job, Worker
from rq.exceptions import NoSuchJobError
from rq.job import Job

from .queues import get_connection, get_queue_by_index
from .settings import QUEUES_LIST


@staff_member_required
def stats(request):
    queues = []
    for index, config in enumerate(QUEUES_LIST):
        queue = get_queue_by_index(index)
        queue_data = {
            'name': queue.name,
            'jobs': queue.count,
            'index': index,
        }
        if queue.name == 'failed':
            queue_data['workers'] = '-'
        else:
            connection = get_connection(queue.name)
            all_workers = Worker.all(connection=connection)
            queue_workers = [worker for worker in all_workers if queue in worker.queues]
            queue_data['workers'] = len(queue_workers)
        queues.append(queue_data)

    context_data = {'queues': queues}
    return render(request, 'django_rq/stats.html', context_data)


@staff_member_required
def jobs(request, queue_index):
    queue_index = int(queue_index)
    queue = get_queue_by_index(queue_index)
    context_data = {
        'queue': queue,
        'queue_index': queue_index,
        'jobs': queue.jobs,
    }

    return render(request, 'django_rq/jobs.html', context_data)


@staff_member_required
def job_detail(request, queue_index, job_id):
    queue_index = int(queue_index)
    queue = get_queue_by_index(queue_index)
    try:
        job = Job.fetch(job_id, connection=queue.connection)
    except NoSuchJobError:
        raise Http404("Couldn't find job with this ID: %s" % job_id)
    
    context_data = {
        'queue_index': queue_index,
        'job': job,
        'queue': queue,
    }
    return render(request, 'django_rq/job_detail.html', context_data)


@staff_member_required
def delete_job(request, queue_index, job_id):
    queue_index = int(queue_index)
    queue = get_queue_by_index(queue_index)
    job = Job.fetch(job_id, connection=queue.connection)

    if request.POST:
        # Remove job id from queue and delete the actual job
        queue.connection._lrem(queue.key, 0, job.id)
        job.delete()
        messages.info(request, 'You have successfully deleted %s' % job.id)
        return redirect('rq_jobs', queue_index)

    context_data = {
        'queue_index': queue_index,
        'job': job,
        'queue': queue,
    }
    return render(request, 'django_rq/delete_job.html', context_data)


@staff_member_required
def requeue_job_view(request, queue_index, job_id):
    queue_index = int(queue_index)
    queue = get_queue_by_index(queue_index)
    job = Job.fetch(job_id, connection=queue.connection)
    if request.POST:
        requeue_job(job_id, connection=queue.connection)
        messages.info(request, 'You have successfully requeued %s' % job.id)
        return redirect('rq_job_detail', queue_index, job_id)

    context_data = {
        'queue_index': queue_index,
        'job': job,
        'queue': queue,
    }
    return render(request, 'django_rq/delete_job.html', context_data)


@staff_member_required
def clear_queue(request, queue_index):
    queue_index = int(queue_index)
    queue = get_queue_by_index(queue_index)
    if request.POST:
        queue.empty()
        messages.info(request, 'You have successfully cleared the queue %s' % queue.name)
        return redirect('rq_jobs', queue_index)
    context_data = {
        'queue_index': queue_index,
        'queue': queue,
    }
    return render(request, 'django_rq/clear_queue.html', context_data)

########NEW FILE########
__FILENAME__ = workers
from rq import Worker

from .queues import get_queues


def get_worker(*queue_names):
    """
    Returns a RQ worker for all queues or specified ones.
    """
    queues = get_queues(*queue_names)
    return Worker(queues, connection=queues[0].connection)

########NEW FILE########
