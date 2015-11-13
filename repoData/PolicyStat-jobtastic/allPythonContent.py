__FILENAME__ = states
"""
Additional task states used by jobtastic.
"""

PROGRESS = 'PROGRESS'

########NEW FILE########
__FILENAME__ = task
"""
Celery base task aimed at longish-running jobs that return a result.

``JobtasticTask`` adds thundering herd avoidance, result caching, progress
reporting, error fallback and JSON encoding of results.
"""
from __future__ import division

import logging
import time
import os
import sys
import warnings
from contextlib import contextmanager
from hashlib import md5

import psutil

from celery.datastructures import ExceptionInfo
from celery.states import PENDING, SUCCESS
from celery.task import Task
from celery.utils import gen_unique_id

get_task_logger = None
try:
    from celery.utils.log import get_task_logger
except ImportError:
    pass  # get_task_logger is new in Celery 3.X

cache = None
try:
    # For now, let's just say that if Django exists, we should use it.
    # Otherwise, try Flask. This definitely needs an actual configuration
    # variable so folks can make an explicit decision.
    from django.core.cache import cache
    HAS_DJANGO = True
except ImportError:
    try:
        # We should really have an explicitly-defined way of doing this, but
        # for now, let's just use werkzeug Memcached if it exists
        from werkzeug.contrib.cache import MemcachedCache

        from celery import conf
        if conf.CELERY_RESULT_BACKEND == 'cache':
            uri_str = conf.CELERY_CACHE_BACKEND.strip('memcached://')
            uris = uri_str.split(';')
            cache = MemcachedCache(uris)
            HAS_WERKZEUG = True
    except ImportError:
        pass

if cache is None:
    raise Exception(
        "Jobtastic requires either Django or Flask + Memcached result backend")


from jobtastic.states import PROGRESS


@contextmanager
def acquire_lock(lock_name):
    """
    A contextmanager to wait until an exclusive lock is available,
    hold the lock and then release it when the code under context
    is complete.

    TODO: This code doesn't work like it should. It doesn't
    wait indefinitely for the lock and in fact cycles through
    very quickly.
    """
    for _ in range(10):
        try:
            value = cache.incr(lock_name)
        except ValueError:
            cache.set(lock_name, 0)
            value = cache.incr(lock_name)
        if value == 1:
            break
        else:
            cache.decr(lock_name)
    else:
        yield
        cache.set(lock_name, 0)
        return
    yield
    cache.decr(lock_name)


class JobtasticTask(Task):
    """
    A base ``Celery.Task`` class that provides some common niceties for running
    tasks that return some kind of result for which you need to wait.

    To create a task that uses these helpers, use ``JobtasticTask`` as a
    subclass and define a ``calculate_result`` method which returns a
    dictionary to be turned in to JSON. You will also need to define the
    following class variables:

    * ``significant_kwargs`` The kwarg values that will be converted to strings
      and hashed to determine if two versions of the same task are equivalent.
      This is a list of 2-tuples with the first item being the kwarg string and
      the second being a callable that converts the value to a hashable string.
      If no second item is given, it's assumed that calling ``str()`` on the
      value works just fine.
    * ``herd_avoidance_timeout`` Number of seconds to hold a lock on this task
      for other equivalent runs. Generally, this should be set to the longest
      estimated amount of time the task could consume.

    The following class members are optional:
    * ``cache_prefix`` A unique string representing this task. Eg.
      ``foo.bar.tasks.BazzTask``
    * ``cache_duration`` The number of seconds for which the result of this
      task should be cached, meaning subsequent equivalent runs will skip
      computation. The default is to do no result caching.
    * ``memleak_threshold`` When a single run of a Task increase the resident
      process memory usage by more than this number of MegaBytes, a warning is
      logged to the logger. This is useful for finding tasks that are behaving
      badly under certain conditions. By default, no logging is performed.
      Set this value to 0 to log all RAM changes and -1 to disable logging.

    Provided are helpers for:

    1. Handling failures to connect the task broker by either directly
      running the task (`delay_or_run`) or by returning a task that
      contains the connection error (`delay_or_fail`). This minimizes
      the user-facing impact of a dead task broker.
    2. Defeating any thundering herd issues by ensuring only one of a task with
      specific arguments can be running at a time by directing subsequent calls
      to latch on to the appropriate result.
    3. Caching the final result for a designated time period so that subsequent
      equivalent calls return quickly.
    4. Returning the results as JSON, so that they can be processed easily by
      client-side javascript.
    5. Returning time-based, continually updating progress estimates to
      front-end code so that users know what to expect.
    """
    abstract = True

    @classmethod
    def delay_or_eager(self, *args, **kwargs):
        """
        Attempt to call self.delay, or if that fails because of a problem with
        the broker, run the task eagerly and return an EagerResult.
        """
        possible_broker_errors = self._get_possible_broker_errors_tuple()
        try:
            return self.apply_async(args=args, kwargs=kwargs)
        except possible_broker_errors:
            return self.apply(args=args, kwargs=kwargs)

    @classmethod
    def delay_or_run(self, *args, **kwargs):
        """
        Attempt to call self.delay, or if that fails, call self.run.

        Returns a tuple, (result, required_fallback). ``result`` is the result
        of calling delay or run. ``required_fallback`` is True if the broker
        failed we had to resort to `self.run`.
        """
        warnings.warn(
            "delay_or_run is deprecated. Please use delay_or_eager",
            DeprecationWarning,
        )
        possible_broker_errors = self._get_possible_broker_errors_tuple()
        try:
            result = self.apply_async(args=args, kwargs=kwargs)
            required_fallback = False
        except possible_broker_errors:
            result = self().run(*args, **kwargs)
            required_fallback = True
        return result, required_fallback

    @classmethod
    def delay_or_fail(self, *args, **kwargs):
        """
        Attempt to call self.delay, but if that fails with an exception, we
        fake the task completion using the exception as the result. This allows
        us to seamlessly handle errors on task creation the same way we handle
        errors when a task runs, simplifying the user interface.
        """
        possible_broker_errors = self._get_possible_broker_errors_tuple()
        try:
            return self.apply_async(args=args, kwargs=kwargs)
        except possible_broker_errors as e:
            return self.simulate_async_error(e)

    @classmethod
    def _get_possible_broker_errors_tuple(self):
        if hasattr(self.app, 'connection'):
            dummy_conn = self.app.connection()
        else:
            # Celery 2.5 uses `broker_connection` instead
            dummy_conn = self.app.broker_connection()

        return dummy_conn.connection_errors + dummy_conn.channel_errors

    @classmethod
    def simulate_async_error(self, exception):
        """
        Take this exception and store it as an error in the result backend.
        This unifies the handling of broker-connection errors with any other
        type of error that might occur when running the task. So the same
        error-handling that might retry a task or display a useful message to
        the user can also handle this error.
        """
        task_id = gen_unique_id()
        async_result = self.AsyncResult(task_id)
        einfo = ExceptionInfo(sys.exc_info())

        async_result.backend.mark_as_failure(
            task_id,
            exception,
            traceback=einfo.traceback,
        )

        return async_result

    @classmethod
    def apply_async(self, args, kwargs, **options):
        """
        Put this task on the Celery queue as a singleton. Only one of this type
        of task with its distinguishing args/kwargs will be allowed on the
        queue at a time. Subsequent duplicate tasks called while this task is
        still running will just latch on to the results of the running task by
        synchronizing the task uuid. Additionally, identical task calls will
        return those results for the next ``cache_duration`` seconds.
        """
        self._validate_required_class_vars()

        cache_key = self._get_cache_key(**kwargs)

        # Check for an already-computed and cached result
        task_id = cache.get(cache_key)  # Check for the cached result
        if task_id:
            # We've already built this result, just latch on to the task that
            # did the work
            logging.info(
                'Found existing cached and completed task: %s', task_id)
            return self.AsyncResult(task_id)

        # Check for an in-progress equivalent task to avoid duplicating work
        task_id = cache.get('herd:%s' % cache_key)
        if task_id:
            logging.info('Found existing in-progress task: %s', task_id)
            return self.AsyncResult(task_id)

        # It's not cached and it's not already running. Use an atomic lock to
        # start the task, ensuring there isn't a race condition that could
        # result in multiple identical tasks being fired at once.
        with acquire_lock('lock:%s' % cache_key):
            task_meta = super(JobtasticTask, self).apply_async(
                args,
                kwargs,
                **options
            )
            logging.info('Current status: %s', task_meta.status)
            if task_meta.status in (PROGRESS, PENDING):
                cache.set(
                    'herd:%s' % cache_key,
                    task_meta.task_id,
                    timeout=self.herd_avoidance_timeout)
                logging.info(
                    'Setting herd-avoidance cache for task: %s', cache_key)
        return task_meta

    def calc_progress(self, completed_count, total_count):
        """
        Calculate the percentage progress and estimated remaining time based on
        the current number of items completed of the total.

        Returns a tuple of ``(percentage_complete, seconds_remaining)``.
        """
        self.logger.debug(
            "calc_progress(%s, %s)",
            completed_count,
            total_count,
        )
        current_time = time.time()

        time_spent = current_time - self.start_time
        self.logger.debug("Progress time spent: %s", time_spent)

        if total_count == 0:
            return 100, 1

        completion_fraction = completed_count / total_count
        if completion_fraction == 0:
            completion_fraction = 1

        total_time = 0
        total_time = time_spent / completion_fraction
        time_remaining = total_time - time_spent

        completion_display = completion_fraction * 100
        if completion_display == 100:
            return 100, 1  # 1 second to finish up

        return completion_display, time_remaining

    def update_progress(
        self,
        completed_count,
        total_count,
        update_frequency=1,
    ):
        """
        Update the task backend with both an estimated percentage complete and
        number of seconds remaining until completion.

        ``completed_count`` Number of task "units" that have been completed out
        of ``total_count`` total "units."
        ``update_frequency`` Only actually store the updated progress in the
        background at most every ``N`` ``completed_count``.
        """
        if completed_count - self._last_update_count < update_frequency:
            # We've updated the progress too recently. Don't stress out the
            # result backend
            return
        # Store progress for display
        progress_percent, time_remaining = self.calc_progress(
            completed_count, total_count)
        self.logger.debug(
            "Updating progress: %s percent, %s remaining",
            progress_percent,
            time_remaining)
        if self.request.id:
            self._last_update_count = completed_count
            self.update_state(None, PROGRESS, {
                "progress_percent": progress_percent,
                "time_remaining": time_remaining,
            })

    def run(self, *args, **kwargs):
        if get_task_logger:
            self.logger = get_task_logger(self.__class__.__name__)
        else:
            # Celery 2.X fallback
            self.logger = self.get_logger(**kwargs)
        self.logger.info("Starting %s", self.__class__.__name__)

        self.cache_key = self._get_cache_key(**kwargs)

        # Record start time to give estimated time remaining estimates
        self.start_time = time.time()

        # Keep track of progress updates for update_frequency tracking
        self._last_update_count = 0

        # Report to the backend that work has been started.
        if self.request.id:
            self.update_state(None, PROGRESS, {
                "progress_percent": 0,
                "time_remaining": -1,
            })

        memleak_threshold = int(getattr(self, 'memleak_threshold', -1))
        if memleak_threshold >= 0:
            begining_memory_usage = self._get_memory_usage()

        self.logger.info("Calculating result")
        try:
            task_result = self.calculate_result(*args, **kwargs)
        except Exception:
            # Don't want other tasks waiting for this task to finish, since it
            # won't
            self._break_thundering_herd_cache()
            raise  # We can use normal celery exception handling for this

        if hasattr(self, 'cache_duration'):
            cache_duration = self.cache_duration
        else:
            cache_duration = -1  # By default, don't cache
        if cache_duration >= 0:
            # If we're configured to cache this result, do so.
            cache.set(self.cache_key, self.request.id, cache_duration)

        # Now that the task is finished, we can stop all of the thundering herd
        # avoidance
        self._break_thundering_herd_cache()

        if memleak_threshold >= 0:
            self._warn_if_leaking_memory(
                begining_memory_usage,
                self._get_memory_usage(),
                memleak_threshold,
                task_kwargs=kwargs,
            )

        return task_result

    def calculate_result(self, *args, **kwargs):
        raise NotImplementedError((
            "Tasks using JobtasticTask must implement "
            "their own calculate_result"
        ))

    @classmethod
    def _validate_required_class_vars(self):
        """
        Ensure that this subclass has defined all of the required class
        variables.
        """
        required_members = (
            'significant_kwargs',
            'herd_avoidance_timeout',
        )
        for required_member in required_members:
            if not hasattr(self, required_member):
                raise Exception(
                    "JobtasticTask's must define a %s" % required_member)

    def on_success(self, retval, task_id, args, kwargs):
        """
        Store results in the backend even if we're always eager. This ensures
        the `delay_or_run` calls always at least have results.
        """
        if self.request.is_eager:
            # Store the result because celery wouldn't otherwise
            self.update_state(task_id, SUCCESS, retval)

    def _break_thundering_herd_cache(self):
        cache.delete('herd:%s' % self.cache_key)

    @classmethod
    def _get_cache_key(self, **kwargs):
        """
        Take this task's configured ``significant_kwargs`` and build a hash
        that all equivalent task calls will match.

        Takes in kwargs and returns a string.

        To change the way the cache key is generated or do more in-depth
        processing, override this method.
        """
        m = md5()
        for significant_kwarg in self.significant_kwargs:
            key, to_str = significant_kwarg
            m.update(to_str(kwargs[key]))

        if hasattr(self, 'cache_prefix'):
            cache_prefix = self.cache_prefix
        else:
            cache_prefix = '%s.%s' % (self.__module__, self.__name__)
        return '%s:%s' % (cache_prefix, m.hexdigest())

    def _get_memory_usage(self):
        current_process = psutil.Process(os.getpid())
        usage = current_process.get_memory_info()

        return usage.rss

    def _warn_if_leaking_memory(
        self, begining_usage, ending_usage, threshold, task_kwargs,
    ):
        growth = ending_usage - begining_usage

        threshold_in_bytes = threshold * 1000000

        if growth > threshold_in_bytes:
            self.warn_of_memory_leak(
                growth,
                begining_usage,
                ending_usage,
                task_kwargs,
            )

    def warn_of_memory_leak(
        self, growth, begining_usage, ending_usage, task_kwargs,
    ):
        self.logger.warning(
            "Jobtastic:memleak memleak_detected. memory_increase=%05d unit=MB",
            growth / 1000000,
        )
        self.logger.info(
            "Jobtastic:memleak memory_usage_start=%05d unit=MB",
            begining_usage / 1000000,
        )
        self.logger.info(
            "Jobtastic:memleak memory_usage_end=%05d unit=MB",
            ending_usage / 1000000,
        )
        self.logger.info(
            "Jobtastic:memleak task_kwargs=%s",
            repr(task_kwargs),
        )

########NEW FILE########
__FILENAME__ = test_broker_fallbacks
import os

import mock


from celery import states
try:
    from celery.tests.utils import AppCase
except ImportError:
    # AppCase was moved in Celery 3.1
    from celery.tests.case import AppCase
# eager_tasks was removed in celery 3.1
from jobtastic.tests.utils import eager_tasks

USING_CELERY_2_X = False
try:
    from kombu.transport.pyamqp import (
        Channel as AmqpChannel,
    )
    from kombu.exceptions import StdChannelError, StdConnectionError
except ImportError:
    USING_CELERY_2_X = True
    from kombu.transport.amqplib import (
        Channel as AmqpChannel,
    )
    from kombu.exceptions import StdChannelError
    # Kombu 2.1 doesn' thave a StdConnectionError, but the 2.1 amqp Transport
    # uses an IOError, so we'll just test with that
    StdConnectionError = IOError

from jobtastic import JobtasticTask


class ParrotTask(JobtasticTask):
    """
    Just return whatever is passed in as the result.
    """
    significant_kwargs = [
        ('result', str),
    ]
    herd_avoidance_timeout = 0

    def calculate_result(self, result, **kwargs):
        return result


error_if_calculate_result_patch = mock.patch.object(
    ParrotTask,
    'calculate_result',
    autospec=True,
    side_effect=AssertionError("Should have skipped calculate_result"),
)
basic_publish_connection_error_patch = mock.patch.object(
    AmqpChannel,
    'basic_publish',
    autospec=True,
    side_effect=StdConnectionError("Should be handled"),
)
basic_publish_channel_error_patch = mock.patch.object(
    AmqpChannel,
    'basic_publish',
    autospec=True,
    side_effect=StdChannelError("Should be handled"),
)


class BrokenBrokerTestCase(AppCase):
    def _set_broker_host(self, new_value):
        os.environ['CELERY_BROKER_URL'] = new_value
        self.app.conf.BROKER_URL = new_value
        self.app.conf.BROKER_HOST = new_value

    def setup(self):
        # lowercase on purpose. AppCase calls `self.setup`
        self.app._pool = None
        # Deleting the cache AMQP class so that it gets recreated with the new
        # BROKER_URL
        del self.app.amqp

        self.old_broker_host = self.app.conf.BROKER_HOST

        # Modifying the broken host name simulates the task broker being
        # 'unresponsive'
        # We need to make this modification in 3 places because of version
        # backwards compatibility
        self._set_broker_host('amqp://')
        self.app.conf['BROKER_CONNECTION_RETRY'] = False
        self.app.conf['BROKER_POOL_LIMIT'] = 1
        self.app.conf['CELERY_TASK_PUBLISH_RETRY'] = False

        self.task = ParrotTask

    def teardown(self):
        del self.app.amqp
        self.app._pool = None

        self._set_broker_host(self.old_broker_host)

    def test_sanity(self):
        self.assertRaises(IOError, self.task.delay, result=1)

    @error_if_calculate_result_patch
    def test_delay_or_fail_bad_connection(self, mock_calculate_result):
        # Loop through all of the possible connection errors and ensure they're
        # properly handled
        with basic_publish_connection_error_patch:
            async_task = self.task.delay_or_fail(result=1)
        self.assertEqual(async_task.status, states.FAILURE)

    @error_if_calculate_result_patch
    def test_delay_or_fail_bad_channel(self, mock_calculate_result):
        with basic_publish_channel_error_patch:
            async_task = self.task.delay_or_fail(result=1)
        self.assertEqual(async_task.status, states.FAILURE)

    def test_delay_or_run_bad_connection(self):
        with basic_publish_connection_error_patch:
            async_task, was_fallback = self.task.delay_or_run(result=27)
        self.assertTrue(was_fallback)
        self.assertEqual(async_task, 27)

    def test_delay_or_run_bad_channel(self):
        with basic_publish_channel_error_patch:
            async_task, was_fallback = self.task.delay_or_run(result=27)
        self.assertTrue(was_fallback)
        self.assertEqual(async_task, 27)

    def test_delay_or_eager_bad_connection(self):
        with basic_publish_connection_error_patch:
            async_task = self.task.delay_or_eager(result=27)
        self.assertEqual(async_task.status, states.SUCCESS)
        self.assertEqual(async_task.result, 27)

    def test_delay_or_eager_bad_channel(self):
        with basic_publish_channel_error_patch:
            async_task = self.task.delay_or_eager(result=27)
        self.assertEqual(async_task.status, states.SUCCESS)
        self.assertEqual(async_task.result, 27)


calculate_result_returns_one_patch = mock.patch.object(
    ParrotTask,
    'calculate_result',
    autospec=True,
    return_value=1,
)


class WorkingBrokerTestCase(AppCase):
    def setup(self):
        self.task = ParrotTask

    def test_sanity(self):
        # The task actually runs
        with eager_tasks(self.app):
            async_task = self.task.delay(result=1)
        self.assertEqual(async_task.status, states.SUCCESS)
        self.assertEqual(async_task.result, 1)

    @calculate_result_returns_one_patch
    def test_delay_or_fail_runs(self, mock_calculate_result):
        with eager_tasks(self.app):
            async_task = self.task.delay_or_fail(result=1)
        self.assertEqual(async_task.status, states.SUCCESS)
        self.assertEqual(async_task.result, 1)

        self.assertEqual(mock_calculate_result.call_count, 1)

    @calculate_result_returns_one_patch
    def test_delay_or_run_runs(self, mock_calculate_result):
        with eager_tasks(self.app):
            async_task, _ = self.task.delay_or_run(result=1)
        self.assertEqual(async_task.status, states.SUCCESS)
        self.assertEqual(async_task.result, 1)

        self.assertEqual(mock_calculate_result.call_count, 1)

    @calculate_result_returns_one_patch
    def test_delay_or_eager_runs(self, mock_calculate_result):
        with eager_tasks(self.app):
            async_task = self.task.delay_or_eager(result=1)
        self.assertEqual(async_task.status, states.SUCCESS)
        self.assertEqual(async_task.result, 1)

        self.assertEqual(mock_calculate_result.call_count, 1)

########NEW FILE########
__FILENAME__ = test_memleak_detection
import mock
from unittest2 import TestCase

from testproj.someapp import tasks as mem_tasks


class MemoryGrowthTest(TestCase):
    def setUp(self):
        self.task = mem_tasks.MemLeakyTask()

    def tearDown(self):
        # Reset the variable that leaks memory
        mem_tasks.leaky_global = []

    def test_sanity(self):
        # The task actually runs
        self.assertEqual(self.task.run(bloat_factor=0), 0)

    @mock.patch.object(
        mem_tasks.MemLeakyTask,
        'warn_of_memory_leak',
        autospec=True,
        side_effect=mem_tasks.MemLeakyTask.warn_of_memory_leak,
    )
    def test_below_threshold(self, mock_warn_of_memory_leak):
        # If there's less than the threshold in growth, we don't spit out any
        # warnings
        self.assertEqual(self.task.run(bloat_factor=1), 1)
        # We should have logged no warnings as a result of this
        self.assertEqual(mock_warn_of_memory_leak.call_count, 0)

    @mock.patch.object(
        mem_tasks.MemLeakyTask,
        'warn_of_memory_leak',
        autospec=True,
    )
    def test_above_threshold(self, mock_warn_of_memory_leak):
        self.assertEqual(self.task.run(bloat_factor=5), 5)
        self.assertEqual(mock_warn_of_memory_leak.call_count, 1)

    @mock.patch.object(
        mem_tasks.MemLeakyTask,
        'warn_of_memory_leak',
        autospec=True,
    )
    def test_triggered_repeatedly_on_increase(self, mock_warn_of_memory_leak):
        self.assertEqual(self.task.run(bloat_factor=5), 5)
        self.assertEqual(mock_warn_of_memory_leak.call_count, 1)

        self.assertEqual(self.task.run(bloat_factor=5), 5)
        self.assertEqual(mock_warn_of_memory_leak.call_count, 2)

    @mock.patch.object(
        mem_tasks.MemLeakyTask,
        'warn_of_memory_leak',
        autospec=True,
        side_effect=mem_tasks.MemLeakyTask.warn_of_memory_leak,
    )
    def test_only_triggered_on_change(self, mock_warn_of_memory_leak):
        self.assertEqual(self.task.run(bloat_factor=5), 5)
        self.assertEqual(mock_warn_of_memory_leak.call_count, 1)

        self.assertEqual(self.task.run(bloat_factor=0), 0)
        # There are no extra warnings
        self.assertEqual(mock_warn_of_memory_leak.call_count, 1)

    @mock.patch.object(
        mem_tasks.MemLeakyDefaultedTask,
        'warn_of_memory_leak',
        autospec=True,
        side_effect=mem_tasks.MemLeakyDefaultedTask.warn_of_memory_leak,
    )
    def test_defaults_disabled(self, mock_warn_of_memory_leak):
        self.assertEqual(
            mem_tasks.MemLeakyDefaultedTask().run(bloat_factor=5),
            5,
        )
        self.assertEqual(mock_warn_of_memory_leak.call_count, 0)

    @mock.patch.object(
        mem_tasks.MemLeakyDisabledWarningTask,
        'warn_of_memory_leak',
        autospec=True,
    )
    def test_disabled_with_negative_config(self, mock_warn_of_memory_leak):
        self.assertEqual(
            mem_tasks.MemLeakyDisabledWarningTask().run(bloat_factor=5),
            5,
        )
        self.assertEqual(mock_warn_of_memory_leak.call_count, 0)

########NEW FILE########
__FILENAME__ = test_progress

import mock

from celery.result import BaseAsyncResult
from celery.states import SUCCESS
try:
    from celery.tests.utils import AppCase
except ImportError:
    # AppCase was moved in Celery 3.1
    from celery.tests.case import AppCase
# eager_tasks was removed in celery 3.1
from jobtastic.tests.utils import eager_tasks

from jobtastic import JobtasticTask
from jobtastic.states import PROGRESS


class ProgressTask(JobtasticTask):
    """
    Just count up to the given number, with hooks for testing.
    """
    significant_kwargs = [
        ('count_to', str),
    ]
    herd_avoidance_timeout = 0

    def calculate_result(self, count_to, **kwargs):
        update_frequency = 2
        for counter in xrange(count_to):
            self.update_progress(
                counter,
                count_to,
                update_frequency=update_frequency,
            )

        return count_to


def task_status_is_progress(self, **kwargs):
    task_id = self.request.id
    meta = BaseAsyncResult(task_id)

    assert meta.status == PROGRESS


class ProgressTestCase(AppCase):
    def setup(self):
        self.task = ProgressTask

    def test_sanity(self):
        # The task actually runs
        with eager_tasks(self.app):
            async_task = self.task.delay(count_to=2)
        self.assertEqual(async_task.status, SUCCESS)
        self.assertEqual(async_task.result, 2)

    def test_starts_with_progress_state(self):
        # The state has already been set to PROGRESS before `calculate_result`
        # starts
        with eager_tasks(self.app):
            with mock.patch.object(
                self.task,
                'calculate_result',
                autospec=True,
                side_effect=task_status_is_progress,
            ):
                async_task = self.task.delay(count_to=2)
        # And the state should still be set to SUCCESS in the end
        self.assertEqual(async_task.status, SUCCESS)

########NEW FILE########
__FILENAME__ = utils
from __future__ import with_statement

from contextlib import contextmanager

from celery.app import app_or_default


# Ported from Celery 3.0, because this was removed in Celery 3.1
@contextmanager
def eager_tasks(app=None):
    if app is None:
        app = app_or_default()

    prev = app.conf.CELERY_ALWAYS_EAGER
    app.conf.CELERY_ALWAYS_EAGER = True
    try:
        yield True
    finally:
        app.conf.CELERY_ALWAYS_EAGER = prev

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproj.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
import os
import warnings

# Ignore deprecation warnings caused by running the same project with different
# versions of Django
warnings.filterwarnings(
    'ignore',
    category=DeprecationWarning,
    module=r'django\.core\.management',
)
warnings.filterwarnings(
    'ignore',
    category=DeprecationWarning,
    module=r'django_nose\.management\.commands\.test',
)

here = os.path.abspath(os.path.dirname(__file__))

ROOT_URLCONF = 'testproj.urls'

DEBUG = True
TEMPLATE_DEBUG = DEBUG
USE_TZ = True
TIME_ZONE = 'UTC'
SITE_ID = 1
SECRET_KEY = ')&a$!r0n!&c$$!-!%r)4kq4b5y9jncx(&2ulmb2*nvx^yi^bp5'
ADMINS = ()
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(here, 'jobtastic-test-db'),
        'USER': '',
        'PASSWORD': '',
        'PORT': '',
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'djcelery',
    'testproj.someapp',
    'jobtastic',
    'django_nose',
)


NOSE_ARGS = [
    os.path.join(here, os.pardir, os.pardir, os.pardir, 'jobtastic', 'tests'),
    os.environ.get("NOSE_VERBOSE") and "--verbose" or "",
]
TEST_RUNNER = 'django_nose.run_tests'

# Celery Configuration
BROKER_URL = 'memory://'
BROKER_CONNECTION_TIMEOUT = 1
BROKER_CONNECTION_RETRY = False
BROKER_CONNECTION_MAX_RETRIES = 1
# The default BROKER_POOL_LIMIT is 10, broker connections are not
# properly cleaned up on error, so the tests will run out of
# connections and result in one test hanging forever
# To prevent that, just disable it
BROKER_POOL_LIMIT = 0
CELERY_RESULT_BACKEND = 'cache'
CELERY_SEND_TASK_ERROR_EMAILS = False
from celery import VERSION
if VERSION[0] < 3:
    # Use Django's syntax instead of Celery's, which would be:
    CELERY_CACHE_BACKEND = 'locmem://'
    import djcelery
    djcelery.setup_loader()
elif VERSION[0] == 3 and VERSION[1] == 0:
    CELERY_CACHE_BACKEND = 'memory'
    import djcelery
    djcelery.setup_loader()
else:
    from celery import Celery
    CELERY_RESULT_BACKEND = 'cache+memory://'
    celery_app = Celery('testproj')
    celery_app.config_from_object('django.conf:settings')
    celery_app.autodiscover_tasks(lambda: INSTALLED_APPS)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tasks
import string
import random

from jobtastic import JobtasticTask

leaky_global = []


class BaseMemLeakyTask(JobtasticTask):
    """
    This task leaks memory like crazy, by adding things to `leaky_global`.
    """
    significant_kwargs = [
        ('bloat_factor', str),
    ]
    herd_avoidance_timeout = 0

    def calculate_result(self, bloat_factor, **kwargs):
        """
        Let's bloat our thing!
        """
        global leaky_global

        for _ in xrange(bloat_factor):
            # 1 million bytes for a MB
            new_str = u'X' * 1000000
            # Add something new to it so python can't just point to the same
            # memory location
            new_str += random.choice(string.letters)
            leaky_global.append(new_str)

        return bloat_factor


class MemLeakyTask(BaseMemLeakyTask):
    memleak_threshold = 10


class MemLeakyDisabledWarningTask(BaseMemLeakyTask):
    memleak_threshold = -1


class MemLeakyDefaultedTask(BaseMemLeakyTask):
    pass

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from djcelery.views import apply

urlpatterns = patterns('',
    url(r'^apply/(?P<task_name>.+?)/', apply, name='celery-apply'),
    url(r'^celery/', include('djcelery.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for testproj project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "testproj.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproj.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
