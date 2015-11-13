__FILENAME__ = scheduler
import logging
import signal
import time
import warnings

from datetime import datetime, timedelta
from itertools import repeat

from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.queue import Queue

from redis import WatchError

from .utils import from_unix, to_unix

logger = logging.getLogger(__name__)


class Scheduler(object):
    scheduler_key = 'rq:scheduler'
    scheduled_jobs_key = 'rq:scheduler:scheduled_jobs'

    def __init__(self, queue_name='default', interval=60, connection=None):
        from rq.connections import resolve_connection
        self.connection = resolve_connection(connection)
        self.queue_name = queue_name
        self._interval = interval
        self.log = logger

    def register_birth(self):
        if self.connection.exists(self.scheduler_key) and \
                not self.connection.hexists(self.scheduler_key, 'death'):
            raise ValueError("There's already an active RQ scheduler")
        key = self.scheduler_key
        now = time.time()
        with self.connection._pipeline() as p:
            p.delete(key)
            p.hset(key, 'birth', now)
            # Set scheduler key to expire a few seconds after polling interval
            # This way, the key will automatically expire if scheduler
            # quits unexpectedly
            p.expire(key, self._interval + 10)
            p.execute()

    def register_death(self):
        """Registers its own death."""
        with self.connection._pipeline() as p:
            p.hset(self.scheduler_key, 'death', time.time())
            p.expire(self.scheduler_key, 60)
            p.execute()

    def _install_signal_handlers(self):
        """
        Installs signal handlers for handling SIGINT and SIGTERM
        gracefully.
        """

        def stop(signum, frame):
            """
            Register scheduler's death and exit.
            """
            self.log.debug('Shutting down RQ scheduler...')
            self.register_death()
            raise SystemExit()

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)

    def _create_job(self, func, args=None, kwargs=None, commit=True,
                    result_ttl=None):
        """
        Creates an RQ job and saves it to Redis.
        """
        if func.__module__ == '__main__':
            raise ValueError(
                    'Functions from the __main__ module cannot be processed '
                    'by workers.')
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        job = Job.create(func, args=args, connection=self.connection,
                         kwargs=kwargs, result_ttl=result_ttl)
        job.origin = self.queue_name
        if commit:
            job.save()
        return job

    def enqueue_at(self, scheduled_time, func, *args, **kwargs):
        """
        Pushes a job to the scheduler queue. The scheduled queue is a Redis sorted
        set ordered by timestamp - which in this case is job's scheduled execution time.

        Usage:

        from datetime import datetime
        from redis import Redis
        from rq.scheduler import Scheduler

        from foo import func

        redis = Redis()
        scheduler = Scheduler(queue_name='default', connection=redis)
        scheduler.enqueue_at(datetime(2020, 1, 1), func, 'argument', keyword='argument')
        """
        job = self._create_job(func, args=args, kwargs=kwargs)
        self.connection._zadd(self.scheduled_jobs_key,
                              to_unix(scheduled_time),
                              job.id)
        return job

    def enqueue_in(self, time_delta, func, *args, **kwargs):
        """
        Similar to ``enqueue_at``, but accepts a timedelta instead of datetime object.
        The job's scheduled execution time will be calculated by adding the timedelta
        to datetime.utcnow().
        """
        job = self._create_job(func, args=args, kwargs=kwargs)
        self.connection._zadd(self.scheduled_jobs_key,
                              to_unix(datetime.utcnow() + time_delta),
                              job.id)
        return job

    def enqueue_periodic(self, scheduled_time, interval, repeat, func,
                         *args, **kwargs):
        """
        Schedule a job to be periodically executed, at a certain interval.
        """
        warnings.warn("'enqueue_periodic()' has been deprecated in favor of '.schedule()'"
                      "and will be removed in a future release.", DeprecationWarning)
        return self.schedule(scheduled_time, func, args=args, kwargs=kwargs,
                            interval=interval, repeat=repeat)

    def schedule(self, scheduled_time, func, args=None, kwargs=None,
                interval=None, repeat=None, result_ttl=None, timeout=None):
        """
        Schedule a job to be periodically executed, at a certain interval.
        """
        # Set result_ttl to -1 for periodic jobs, if result_ttl not specified
        if interval is not None and result_ttl is None:
            result_ttl = -1
        job = self._create_job(func, args=args, kwargs=kwargs, commit=False,
                               result_ttl=result_ttl)
        if interval is not None:
            job.meta['interval'] = int(interval)
        if repeat is not None:
            job.meta['repeat'] = int(repeat)
        if repeat and interval is None:
            raise ValueError("Can't repeat a job without interval argument")
        if timeout is not None:
            job.timeout = timeout
        job.save()
        self.connection._zadd(self.scheduled_jobs_key,
                              to_unix(scheduled_time),
                              job.id)
        return job

    def enqueue(self, scheduled_time, func, args=None, kwargs=None,
                interval=None, repeat=None, result_ttl=None):
        """
        This method is deprecated and only left in as a backwards compatibility
        alias for schedule().
        """
        warnings.warn("'enqueue()' has been deprecated in favor of '.schedule()'"
                      "and will be removed in a future release.", DeprecationWarning)
        return self.schedule(scheduled_time, func, args, kwargs, interval,
                             repeat, result_ttl)

    def cancel(self, job):
        """
        Pulls a job from the scheduler queue. This function accepts either a
        job_id or a job instance.
        """
        if isinstance(job, Job):
            self.connection.zrem(self.scheduled_jobs_key, job.id)
        else:
            self.connection.zrem(self.scheduled_jobs_key, job)

    def __contains__(self, item):
        """
        Returns a boolean indicating whether the given job instance or job id is
        scheduled for execution.
        """
        job_id = item
        if isinstance(item, Job):
            job_id = item.id
        return self.connection.zscore(self.scheduled_jobs_key, job_id) is not None

    def change_execution_time(self, job, date_time):
        """
        Change a job's execution time. Wrap this in a transaction to prevent race condition.
        """
        with self.connection._pipeline() as pipe:
            while 1:
                try:
                    pipe.watch(self.scheduled_jobs_key)
                    if pipe.zscore(self.scheduled_jobs_key, job.id) is None:
                        raise ValueError('Job not in scheduled jobs queue')
                    pipe.zadd(self.scheduled_jobs_key, to_unix(date_time), job.id)
                    break
                except WatchError:
                    # If job is still in the queue, retry otherwise job is already executed
                    # so we raise an error
                    if pipe.zscore(self.scheduled_jobs_key, job.id) is None:
                        raise ValueError('Job not in scheduled jobs queue')
                    continue

    def get_jobs(self, until=None, with_times=False):
        """
        Returns a list of job instances that will be queued until the given time.
        If no 'until' argument is given all jobs are returned. This function
        accepts datetime and timedelta instances as well as integers representing
        epoch values.
        If with_times is True a list of tuples consisting of the job instance and
        it's scheduled execution time is returned.
        """
        def epoch_to_datetime(epoch):
            return from_unix(float(epoch))
        
        if until is None:
            until = "+inf"
        elif isinstance(until, datetime):
            until = to_unix(until)
        elif isinstance(until, timedelta):
            until = to_unix((datetime.utcnow() + until))
        job_ids = self.connection.zrangebyscore(self.scheduled_jobs_key, 0,
                                                until, withscores=with_times,
                                                score_cast_func=epoch_to_datetime)
        if not with_times:
            job_ids = zip(job_ids, repeat(None))
        jobs = []
        for job_id, sched_time in job_ids:
            job_id = job_id.decode('utf-8')
            try:
                job = Job.fetch(job_id, connection=self.connection)
                if with_times:
                    jobs.append((job, sched_time))
                else:
                    jobs.append(job)
            except NoSuchJobError:
                # Delete jobs that aren't there from scheduler
                self.cancel(job_id)
        return jobs

    def get_jobs_to_queue(self, with_times=False):
        """
        Returns a list of job instances that should be queued
        (score lower than current timestamp).
        If with_times is True a list of tuples consisting of the job instance and
        it's scheduled execution time is returned.
        """
        return self.get_jobs(to_unix(datetime.utcnow()), with_times=with_times)

    def get_queue_for_job(self, job):
        """
        Returns a queue to put job into.
        """
        key = '{0}{1}'.format(Queue.redis_queue_namespace_prefix, job.origin)
        return Queue.from_queue_key(key, connection=self.connection)

    def enqueue_job(self, job):
        """
        Move a scheduled job to a queue. In addition, it also does puts the job
        back into the scheduler if needed.
        """
        self.log.debug('Pushing {0} to {1}'.format(job.id, job.origin))

        interval = job.meta.get('interval', None)
        repeat = job.meta.get('repeat', None)

        # If job is a repeated job, decrement counter
        if repeat:
            job.meta['repeat'] = int(repeat) - 1
        job.enqueued_at = datetime.utcnow()
        job.save()

        queue = self.get_queue_for_job(job)
        queue.push_job_id(job.id)
        self.connection.zrem(self.scheduled_jobs_key, job.id)

        if interval:
            # If this is a repeat job and counter has reached 0, don't repeat
            if repeat is not None:
                if job.meta['repeat'] == 0:
                    return
            self.connection._zadd(self.scheduled_jobs_key,
                                  to_unix(datetime.utcnow()) + int(interval),
                                  job.id)

    def enqueue_jobs(self):
        """
        Move scheduled jobs into queues.
        """
        jobs = self.get_jobs_to_queue()
        for job in jobs:
            self.enqueue_job(job)
        
        # Refresh scheduler key's expiry
        self.connection.expire(self.scheduler_key, self._interval + 10)
        return jobs

    def run(self):
        """
        Periodically check whether there's any job that should be put in the queue (score
        lower than current time).
        """
        self.log.debug('Running RQ scheduler...')
        self.register_birth()
        self._install_signal_handlers()
        try:
            while True:
                self.enqueue_jobs()
                time.sleep(self._interval)
        finally:
            self.register_death()

########NEW FILE########
__FILENAME__ = rqscheduler
#!/usr/bin/env python

import argparse
import sys
import os

from redis import Redis
from rq_scheduler.scheduler import Scheduler


def main():
    parser = argparse.ArgumentParser(description='Runs RQ scheduler')
    parser.add_argument('-H', '--host', default=os.environ.get('RQ_REDIS_HOST', 'localhost'), help="Redis host")
    parser.add_argument('-p', '--port', default=int(os.environ.get('RQ_REDIS_PORT', 6379)), type=int, help="Redis port number")
    parser.add_argument('-d', '--db', default=int(os.environ.get('RQ_REDIS_DB', 0)), type=int, help="Redis database")
    parser.add_argument('-P', '--password', default=os.environ.get('RQ_REDIS_PASSWORD'), help="Redis password")
    parser.add_argument('--url', '-u', default=os.environ.get('RQ_REDIS_URL')
        , help='URL describing Redis connection details. \
            Overrides other connection arguments if supplied.')
    parser.add_argument('-i', '--interval', default=60, type=int
        , help="How often the scheduler checks for new jobs to add to the \
            queue (in seconds).")
    parser.add_argument('--path', default='.', help='Specify the import path.')
    parser.add_argument('--pid', help='A filename to use for the PID file.', metavar='FILE')
    args = parser.parse_args()
    if args.path:
        sys.path = args.path.split(':') + sys.path
    if args.pid:
        pid = str(os.getpid())
        filename = args.pid
        with open(filename, 'w') as f:
            f.write(pid)
    if args.url is not None:
        connection = Redis.from_url(args.url)
    else:
        connection = Redis(args.host, args.port, args.db, args.password)
    scheduler = Scheduler(connection=connection, interval=args.interval)
    scheduler.run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = utils
import calendar
from datetime import datetime

# from_unix from times.from_unix()
def from_unix(string):
    """Convert a unix timestamp into a utc datetime"""
    return datetime.utcfromtimestamp(float(string))


# to_unix from times.to_unix()
def to_unix(dt):
    """Converts a datetime object to unixtime"""
    return calendar.timegm(dt.utctimetuple())

########NEW FILE########
__FILENAME__ = test_scheduler
import unittest
from datetime import datetime, timedelta
import os
import signal
import time
from threading import Thread

from rq import Queue
from rq.compat import as_text
from rq.job import Job
import warnings
from rq_scheduler import Scheduler
from rq_scheduler.utils import to_unix

from tests import RQTestCase


def say_hello(name=None):
    """A job with a single argument and a return value."""
    if name is None:
        name = 'Stranger'
    return 'Hi there, %s!' % (name,)

def tl(l):
    return [as_text(i) for i in l]

def simple_addition(x, y, z):
    return x + y + z


class TestScheduler(RQTestCase):

    def setUp(self):
        super(TestScheduler, self).setUp()
        self.scheduler = Scheduler(connection=self.testconn)
    
    def test_birth_and_death_registration(self):
        """
        When scheduler registers it's birth, besides creating a key, it should
        also set an expiry that's a few seconds longer than it's polling
        interval so it automatically expires if scheduler is unexpectedly 
        terminated.
        """
        key = Scheduler.scheduler_key
        self.assertNotIn(key, tl(self.testconn.keys('*')))
        scheduler = Scheduler(connection=self.testconn, interval=20)
        scheduler.register_birth()
        self.assertIn(key, tl(self.testconn.keys('*')))
        self.assertEqual(self.testconn.ttl(key), 30)
        self.assertFalse(self.testconn.hexists(key, 'death'))
        self.assertRaises(ValueError, scheduler.register_birth)
        scheduler.register_death()
        self.assertTrue(self.testconn.hexists(key, 'death'))

    def test_create_job(self):
        """
        Ensure that jobs are created properly.
        """
        job = self.scheduler._create_job(say_hello, args=(), kwargs={})
        job_from_queue = Job.fetch(job.id, connection=self.testconn)
        self.assertEqual(job, job_from_queue)
        self.assertEqual(job_from_queue.func, say_hello)

    def test_job_not_persisted_if_commit_false(self):
        """
        Ensure jobs are only saved to Redis if commit=True.
        """
        job = self.scheduler._create_job(say_hello, commit=False)
        self.assertEqual(self.testconn.hgetall(job.key), {})

    def test_create_scheduled_job(self):
        """
        Ensure that scheduled jobs are put in the scheduler queue with the right score
        """
        scheduled_time = datetime.utcnow()
        job = self.scheduler.enqueue_at(scheduled_time, say_hello)
        self.assertEqual(job, Job.fetch(job.id, connection=self.testconn))
        self.assertIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))
        self.assertEqual(self.testconn.zscore(self.scheduler.scheduled_jobs_key, job.id),
                         to_unix(scheduled_time))

    def test_enqueue_in(self):
        """
        Ensure that jobs have the right scheduled time.
        """
        right_now = datetime.utcnow()
        time_delta = timedelta(minutes=1)
        job = self.scheduler.enqueue_in(time_delta, say_hello)
        self.assertIn(job.id,
                      tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))
        self.assertEqual(self.testconn.zscore(self.scheduler.scheduled_jobs_key, job.id),
                         to_unix(right_now + time_delta))
        time_delta = timedelta(hours=1)
        job = self.scheduler.enqueue_in(time_delta, say_hello)
        self.assertEqual(self.testconn.zscore(self.scheduler.scheduled_jobs_key, job.id),
                         to_unix(right_now + time_delta))

    def test_get_jobs(self):
        """
        Ensure get_jobs() returns all jobs until the specified time.
        """
        now = datetime.utcnow()
        job = self.scheduler.enqueue_at(now, say_hello)
        self.assertIn(job, self.scheduler.get_jobs(now))
        future_time = now + timedelta(hours=1)
        job = self.scheduler.enqueue_at(future_time, say_hello)
        self.assertIn(job, self.scheduler.get_jobs(timedelta(hours=1, seconds=1)))
        self.assertIn(job, [j[0] for j in self.scheduler.get_jobs(with_times=True)])
        self.assertIsInstance(self.scheduler.get_jobs(with_times=True)[0][1], datetime)
        self.assertNotIn(job, self.scheduler.get_jobs(timedelta(minutes=59, seconds=59)))
    
    def test_get_jobs_to_queue(self):
        """
        Ensure that jobs scheduled the future are not queued.
        """
        now = datetime.utcnow()
        job = self.scheduler.enqueue_at(now, say_hello)
        self.assertIn(job, self.scheduler.get_jobs_to_queue())
        future_time = now + timedelta(hours=1)
        job = self.scheduler.enqueue_at(future_time, say_hello)
        self.assertNotIn(job, self.scheduler.get_jobs_to_queue())

    def test_enqueue_job(self):
        """
        When scheduled job is enqueued, make sure:
        - Job is removed from the sorted set of scheduled jobs
        - "enqueued_at" attribute is properly set
        - Job appears in the right queue
        """
        now = datetime.utcnow()
        queue_name = 'foo'
        scheduler = Scheduler(connection=self.testconn, queue_name=queue_name)

        job = scheduler.enqueue_at(now, say_hello)
        self.scheduler.enqueue_job(job)
        self.assertNotIn(job, tl(self.testconn.zrange(scheduler.scheduled_jobs_key, 0, 10)))
        job = Job.fetch(job.id, connection=self.testconn)
        self.assertTrue(job.enqueued_at is not None)
        queue = scheduler.get_queue_for_job(job)
        self.assertIn(job, queue.jobs)
        queue = Queue.from_queue_key('rq:queue:{0}'.format(queue_name))
        self.assertIn(job, queue.jobs)

    def test_job_membership(self):
        now = datetime.utcnow()
        job = self.scheduler.enqueue_at(now, say_hello)
        self.assertIn(job, self.scheduler)
        self.assertIn(job.id, self.scheduler)
        self.assertNotIn("non-existing-job-id", self.scheduler)

    def test_cancel_scheduled_job(self):
        """
        When scheduled job is canceled, make sure:
        - Job is removed from the sorted set of scheduled jobs
        """
        # schedule a job to be enqueued one minute from now
        time_delta = timedelta(minutes=1)
        job = self.scheduler.enqueue_in(time_delta, say_hello)
        # cancel the scheduled job and check that it's gone from the set
        self.scheduler.cancel(job)
        self.assertNotIn(job.id, tl(self.testconn.zrange(
            self.scheduler.scheduled_jobs_key, 0, 1)))

    def test_change_execution_time(self):
        """
        Ensure ``change_execution_time`` is called, ensure that job's score is updated
        """
        job = self.scheduler.enqueue_at(datetime.utcnow(), say_hello)
        new_date = datetime(2010, 1, 1)
        self.scheduler.change_execution_time(job, new_date)
        self.assertEqual(to_unix(new_date),
            self.testconn.zscore(self.scheduler.scheduled_jobs_key, job.id))
        self.scheduler.cancel(job)
        self.assertRaises(ValueError, self.scheduler.change_execution_time, job, new_date)

    def test_args_kwargs_are_passed_correctly(self):
        """
        Ensure that arguments and keyword arguments are properly saved to jobs.
        """
        job = self.scheduler.enqueue_at(datetime.utcnow(), simple_addition, 1, 1, 1)
        self.assertEqual(job.args, (1, 1, 1))
        job = self.scheduler.enqueue_at(datetime.utcnow(), simple_addition, z=1, y=1, x=1)
        self.assertEqual(job.kwargs, {'x': 1, 'y': 1, 'z': 1})
        job = self.scheduler.enqueue_at(datetime.utcnow(), simple_addition, 1, z=1, y=1)
        self.assertEqual(job.kwargs, {'y': 1, 'z': 1})
        self.assertEqual(job.args, (1,))

        time_delta = timedelta(minutes=1)
        job = self.scheduler.enqueue_in(time_delta, simple_addition, 1, 1, 1)
        self.assertEqual(job.args, (1, 1, 1))
        job = self.scheduler.enqueue_in(time_delta, simple_addition, z=1, y=1, x=1)
        self.assertEqual(job.kwargs, {'x': 1, 'y': 1, 'z': 1})
        job = self.scheduler.enqueue_in(time_delta, simple_addition, 1, z=1, y=1)
        self.assertEqual(job.kwargs, {'y': 1, 'z': 1})
        self.assertEqual(job.args, (1,))

    def test_enqueue_is_deprecated(self):
        """
        Ensure .enqueue() throws a DeprecationWarning
        """
        with warnings.catch_warnings(record=True) as w:
            # Enable all warnings
            warnings.simplefilter("always")
            job = self.scheduler.enqueue(datetime.utcnow(), say_hello)
            self.assertEqual(1, len(w))
            self.assertEqual(w[0].category, DeprecationWarning)

    def test_enqueue_periodic(self):
        """
        Ensure .enqueue_periodic() throws a DeprecationWarning
        """
        with warnings.catch_warnings(record=True) as w:
            # Enable all warnings
            warnings.simplefilter("always")
            job = self.scheduler.enqueue_periodic(datetime.utcnow(), 1, None, say_hello)
            self.assertEqual(1, len(w))
            self.assertEqual(w[0].category, DeprecationWarning)

    def test_interval_and_repeat_persisted_correctly(self):
        """
        Ensure that interval and repeat attributes get correctly saved in Redis.
        """
        job = self.scheduler.schedule(datetime.utcnow(), say_hello, interval=10, repeat=11)
        job_from_queue = Job.fetch(job.id, connection=self.testconn)
        self.assertEqual(job_from_queue.meta['interval'], 10)
        self.assertEqual(job_from_queue.meta['repeat'], 11)

    def test_repeat_without_interval_raises_error(self):
        # Ensure that an error is raised if repeat is specified without interval
        def create_job():
            self.scheduler.schedule(datetime.utcnow(), say_hello, repeat=11)
        self.assertRaises(ValueError, create_job)

    def test_job_with_intervals_get_rescheduled(self):
        """
        Ensure jobs with interval attribute are put back in the scheduler
        """
        time_now = datetime.utcnow()
        interval = 10
        job = self.scheduler.schedule(time_now, say_hello, interval=interval)
        self.scheduler.enqueue_job(job)
        self.assertIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))
        self.assertEqual(self.testconn.zscore(self.scheduler.scheduled_jobs_key, job.id),
                         to_unix(time_now) + interval)

        # Now the same thing using enqueue_periodic
        job = self.scheduler.enqueue_periodic(time_now, interval, None, say_hello)
        self.scheduler.enqueue_job(job)
        self.assertIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))
        self.assertEqual(self.testconn.zscore(self.scheduler.scheduled_jobs_key, job.id),
                         to_unix(time_now) + interval)

    def test_job_with_repeat(self):
        """
        Ensure jobs with repeat attribute are put back in the scheduler
        X (repeat) number of times
        """
        time_now = datetime.utcnow()
        interval = 10
        # If job is repeated once, the job shouldn't be put back in the queue
        job = self.scheduler.schedule(time_now, say_hello, interval=interval, repeat=1)
        self.scheduler.enqueue_job(job)
        self.assertNotIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))

        # If job is repeated twice, it should only be put back in the queue once
        job = self.scheduler.schedule(time_now, say_hello, interval=interval, repeat=2)
        self.scheduler.enqueue_job(job)
        self.assertIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))
        self.scheduler.enqueue_job(job)
        self.assertNotIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))

        time_now = datetime.utcnow()
        # Now the same thing using enqueue_periodic
        job = self.scheduler.enqueue_periodic(time_now, interval, 1, say_hello)
        self.scheduler.enqueue_job(job)
        self.assertNotIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))

        # If job is repeated twice, it should only be put back in the queue once
        job = self.scheduler.enqueue_periodic(time_now, interval, 2, say_hello)
        self.scheduler.enqueue_job(job)
        self.assertIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))
        self.scheduler.enqueue_job(job)
        self.assertNotIn(job.id,
            tl(self.testconn.zrange(self.scheduler.scheduled_jobs_key, 0, 1)))

    def test_missing_jobs_removed_from_scheduler(self):
        """
        Ensure jobs that don't exist when queued are removed from the scheduler.
        """
        job = self.scheduler.schedule(datetime.utcnow(), say_hello)
        job.cancel()
        self.scheduler.get_jobs_to_queue()
        self.assertNotIn(job.id, tl(self.testconn.zrange(
            self.scheduler.scheduled_jobs_key, 0, 1)))

    def test_periodic_jobs_sets_ttl(self):
        """
        Ensure periodic jobs set result_ttl to infinite.
        """
        job = self.scheduler.schedule(datetime.utcnow(), say_hello, interval=5)
        job_from_queue = Job.fetch(job.id, connection=self.testconn)
        self.assertEqual(job.result_ttl, -1)

    def test_run(self):
        """
        Check correct signal handling in Scheduler.run().
        """
        def send_stop_signal():
            """
            Sleep for 1 second, then send a INT signal to ourself, so the
            signal handler installed by scheduler.run() is called.
            """
            time.sleep(1)
            os.kill(os.getpid(), signal.SIGINT)
        thread = Thread(target=send_stop_signal)
        thread.start()
        self.assertRaises(SystemExit, self.scheduler.run)
        thread.join()

    def test_scheduler_w_o_explicit_connection(self):
        """
        Ensure instantiating Scheduler w/o explicit connection works.
        """
        s = Scheduler()
        self.assertEqual(s.connection, self.testconn)

    def test_no_functions_from__main__module(self):
        """
        Ensure functions from the __main__ module are not accepted for scheduling.
        """
        def dummy():
            return 1
        # Fake __main__ module function
        dummy.__module__ = "__main__"
        self.assertRaises(ValueError, self.scheduler._create_job, dummy)

########NEW FILE########
