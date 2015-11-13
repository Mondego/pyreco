__FILENAME__ = admin
from django.contrib import admin
from django.conf import settings
from django.db.models import F
from .job import FailedJob, QueuedJob, DequeuedJob, ScheduledJob
from .queue import FailedQueue
from .flow import FlowStore
from .worker import Worker

CONN = getattr(settings, 'PQ_ADMIN_CONNECTION', 'default')

def requeue_failed_jobs(modeladmin, request, queryset):
    """Requeue selected failed jobs onto the origin queue"""
    fq = FailedQueue.create(CONN)
    for job in queryset:
        fq.requeue(job.id)
requeue_failed_jobs.short_description = "Requeue selected jobs"

class FailedJobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'origin', 'exc_info', 'ended_at')
    list_filter = ('origin',)
    ordering = ('-id',)
    actions = [requeue_failed_jobs]

    def __init__(self, *args, **kwargs):
        super(FailedJobAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def queryset(self, request):
        return self.model.objects.using(
            CONN).filter(queue__name='failed')

    def has_add_permission(self, request):
        return False


class QueuedJobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'queue', 'timeout', 'enqueued_at',
                    'scheduled_for', 'get_schedule_options',)
    list_filter = ('origin',)
    ordering = ('id', 'scheduled_for')

    def __init__(self, *args, **kwargs):
        super(QueuedJobAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )


    def queryset(self, request):
        return self.model.objects.using(
            CONN).all().exclude(queue__name='failed').exclude(queue=None)

    def has_add_permission(self, request):
        return False


class ScheduledJobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'queue', 'timeout', 'enqueued_at',
                    'scheduled_for', 'get_schedule_options',)
    list_filter = ('origin',)
    ordering = ('scheduled_for', )

    def __init__(self, *args, **kwargs):
        super(ScheduledJobAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def queryset(self, request):
        return self.model.objects.using(
            CONN).filter(status=0).exclude(queue__name='failed').exclude(queue=None)

    def has_add_permission(self, request):
        return False

def requeue_jobs(modeladmin, request, queryset):
    """Requeue selected jobs onto the origin queue"""
    fq = FailedQueue.create(CONN)
    for job in queryset:
        fq.requeue(job.id)
requeue_jobs.short_description = "Requeue selected jobs"


class DequeuedJobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'origin', 'status', 'enqueued_at', 'ended_at')
    list_filter = ('origin', 'status')
    ordering = ('-enqueued_at',)
    actions = [requeue_jobs]

    def __init__(self, *args, **kwargs):
        super(DequeuedJobAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def queryset(self, request):
        return self.model.objects.using(CONN).filter(queue=None)

    def has_add_permission(self, request):
        return False


class FlowAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'queue', 'enqueued_at', 'ended_at', 'status' )
    list_filter = ('name', 'queue',)
    ordering = ('id',)

    def __init__(self, *args, **kwargs):
        super(FlowAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def has_add_permission(self, request):
        return False


class WorkerAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth', 'expire', 'heartbeat', 'queue_names', 'stop')
    list_editable = ('stop', )
    ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super(WorkerAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def has_add_permission(self, request):
        return False



admin.site.register(FailedJob, FailedJobAdmin)
admin.site.register(QueuedJob, QueuedJobAdmin)
admin.site.register(ScheduledJob, ScheduledJobAdmin)
admin.site.register(DequeuedJob, DequeuedJobAdmin)
admin.site.register(FlowStore, FlowAdmin)
admin.site.register(Worker, WorkerAdmin)


########NEW FILE########
__FILENAME__ = sentry
def register_sentry(client, worker):
    """Given a Raven client and an RQ worker, registers exception handlers
    with the worker so exceptions are logged to Sentry.
    """
    def send_to_sentry(job, *exc_info):
        client.captureException(
                exc_info=exc_info,
                extra={
                    'job_id': job.id,
                    'func': job.func,
                    'args': job.args,
                    'kwargs': job.kwargs,
                    'description': job.description,
                    })

    worker.push_exc_handler(send_to_sentry)
########NEW FILE########
__FILENAME__ = decorators
from functools import wraps

from six import string_types

from .queue import Queue
from .worker import PQ_DEFAULT_RESULT_TTL

class job(object):

    def __init__(self, queue, connection='default', timeout=None,
            result_ttl=PQ_DEFAULT_RESULT_TTL):
        """A decorator that adds a ``delay`` method to the decorated function,
        which in turn creates a RQ job when called. Accepts a required
        ``queue`` argument that can be either a ``Queue`` instance or a string
        denoting the queue name.  For example:

            @job(queue='default')
            def simple_add(x, y):
                return x + y

            simple_add.delay(1, 2) # Puts simple_add function into queue
        """
        self.queue = queue
        self.connection = connection
        self.timeout = timeout
        self.result_ttl = result_ttl

    def __call__(self, f):
        @wraps(f)
        def delay(*args, **kwargs):
            if isinstance(self.queue, string_types):
                queue = Queue.create(name=self.queue, connection=self.connection)
            else:
                queue = self.queue
            return queue.enqueue_call(f, args=args, kwargs=kwargs,
                    timeout=self.timeout, result_ttl=self.result_ttl)
        f.delay = delay
        return f
########NEW FILE########
__FILENAME__ = exceptions
class NoSuchJobError(Exception):
    pass


class InvalidJobOperationError(Exception):
    pass


class NoQueueError(Exception):
    pass


class InvalidQueueName(Exception):
    pass


class MulipleQueueConnectionsError(Exception):
    pass


class UnpickleError(Exception):
    def __init__(self, message, raw_data, inner_exception=None):
        super(UnpickleError, self).__init__(message, inner_exception)
        self.raw_data = raw_data


class DequeueTimeout(Exception):
    pass


class StopRequested(Exception):
    pass


class InvalidBetween(Exception):
    pass


class InvalidInterval(Exception):
    pass

class InvalidWeekdays(Exception):
    pass


########NEW FILE########
__FILENAME__ = flow
from collections import OrderedDict
import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils.timezone import now
from picklefield.fields import PickledObjectField
from six import integer_types

from .queue import Queue
from .job import Job

PQ_DEFAULT_JOB_TIMEOUT = getattr(settings, 'PQ_DEFAULT_JOB_TIMEOUT', 180)

class FlowQueue(Queue):
    class Meta:
        proxy = True

    def enqueue_job(self, job, timeout=None, set_meta_data=True, async=True):
        """Enqueues a job for delayed execution.

        When the `timeout` argument is sent, it will overrides the default
        timeout value of 180 seconds.  `timeout` may either be a string or
        integer.

        If the `set_meta_data` argument is `True` (default), it will update
        the properties `origin` and `enqueued_at`.

        If Queue is instantiated with async=False, job is executed immediately.
        """
        if set_meta_data:
            job.origin = self.name

        if timeout:
            job.timeout = timeout
        else:
            job.timeout = PQ_DEFAULT_JOB_TIMEOUT  # default

        # set the simple sequential case on success
        job.uuid = uuid.uuid4()
        if self.jobs:
            try:
                prior_job = self.jobs.values()[-1]
            except TypeError:  # py33
                prior_job = self.jobs.popitem()[1]
            prior_job.if_result = job.uuid
            self.jobs[prior_job.uuid] = prior_job
        else:  # first job
            job.queue_id = self.name

        self.jobs[job.uuid] = job

        return job


class FlowStore(models.Model):
    """Flow storage """

    QUEUED = 1
    FINISHED = 2
    FAILED = 3

    STATUS_CHOICES = (
        (QUEUED, 'queued'),
        (FINISHED, 'finished'),
        (FAILED, 'failed'),
    )

    name = models.CharField(max_length=100, default='')
    queue = models.ForeignKey('Queue', blank=True, null=True)
    enqueued_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField('expires', null=True, blank=True)
    status = models.PositiveIntegerField(null=True,
            blank=True, choices=STATUS_CHOICES)
    jobs = PickledObjectField(blank=True)

    class Meta:
        verbose_name ='flow'
        verbose_name_plural = 'flows'


    def __unicode__(self):
        if self.id and self.name:
            return '%i - %s' % (self.id, self.name)
        elif self.id:
            return str(self.id)
        else:
            return self.name

    def enqueue(self, func, *args, **kwargs):
        return self.queue.enqueue(func, *args, **kwargs)

    def enqueue_call(self, func, *args, **kwargs):
        return self.queue.enqueue_call(func, *args, **kwargs)

    def schedule(self, *args, **kwargs):
        return self.queue.schedule(*args, **kwargs)

    def schedule_call(self, *args, **kwargs):
        return self.queue.schedule_call(*args, **kwargs)


    @classmethod
    def delete_expired_ttl(cls, connection):
        """Delete jobs from the queue which have expired"""
        with transaction.commit_on_success(using=connection):
            FlowStore.objects.using(connection).filter(
               status=FlowStore.FINISHED, expired_at__lte=now()).delete()

    def save(self, *args, **kwargs):
        self.queue.save_queue()
        super(FlowStore, self).save(*args, **kwargs)

class Flow(object):

    def __init__(self, queue, name=''):
        queue = FlowQueue.create(name=queue.name)
        self.flowstore = FlowStore(name=name)
        self.flowstore.jobs = []
        self.flowstore.queue = queue
        self.flowstore.save()
        queue.jobs = OrderedDict()
        self.queue = queue
        self.name = name
        self.async = queue._async

    def __enter__(self):
        return self.flowstore

    def __exit__(self, type, value, traceback):
        for i, job in enumerate(self.queue.jobs.values()):
            job.flow = self.flowstore
            if not job.queue_id:
                job.status = Job.FLOW
            else:
                job.status = Job.QUEUED
            if self.async:
                job.save()
                if i == 0:
                    self.flowstore.enqueued_at = job.enqueued_at
                self.flowstore.jobs.append(job.id)
                if job.queue_id:
                    self.queue.notify(job.id)
            else:
                job.perform()
                job.save()

        if self.async and self.queue.jobs:
            self.flowstore.status = FlowStore.QUEUED
            self.flowstore.save()

    @classmethod
    def get(cls, id_or_name):
        if isinstance(id_or_name, integer_types):
            return FlowStore.objects.get(pk=id_or_name)
        else:
            return FlowStore.objects.filter(name=id_or_name)



    @classmethod
    def handle_result(cls, job, queue):
        """Get the next job in the flow sequence"""
        if job.if_result:
            next_job = Job.objects.get(uuid=job.if_result)
            next_job.queue_id = queue.name
            next_job.enqueued_at = now()
            next_job.status = Job.QUEUED
            next_job.save()
            queue.notify(next_job.id)
        else:  # maybe last job
            fs = FlowStore.objects.get(pk=job.flow_id)
            if fs.jobs[-1] == job.id and job.expired_at < now():
                fs.delete()
            elif fs.jobs[-1] == job.id:
                fs.ended_at = job.ended_at
                fs.expired_at = job.expired_at
                fs.status = FlowStore.FINISHED
                fs.save()

    @classmethod
    def handle_failed(cls, job, queue):
        """Handle a failed job"""
        if job.if_failed:
            next_job = Job.objects.get(uuid=job.if_failed)
            next_job.queue_id = queue.name
            next_job.enqueued_at = now()
            next_job.status = Job.QUEUED
            next_job.save()
            queue.notify(next_job.id)
        fs = FlowStore.objects.get(pk=job.flow_id)
        fs.status = FlowStore.FAILED
        fs.save()

########NEW FILE########
__FILENAME__ = job
import importlib
import inspect
from datetime import timedelta, datetime

from dateutil.relativedelta import relativedelta, weekday
from dateutil.relativedelta import weekdays as wdays
from picklefield.fields import PickledObjectField
from django.db import models
from django.db import transaction
from django.utils.timezone import now
from six import get_method_self, integer_types

from .exceptions import InvalidInterval


class Job(models.Model):

    SCHEDULED = 0
    QUEUED = 1
    FINISHED = 2
    FAILED = 3
    STARTED = 4
    FLOW = 5

    STATUS_CHOICES = (
        (SCHEDULED, 'scheduled'),
        (QUEUED, 'queued'),
        (FINISHED, 'finished'),
        (FAILED, 'failed'),
        (STARTED, 'started'),
        (FLOW, 'flow'),
    )
    uuid = models.CharField(max_length=64, null=True, blank=True)
    connection = None
    created_at = models.DateTimeField()
    origin = models.CharField(max_length=254, null=True, blank=True)
    queue = models.ForeignKey('Queue', null=True, blank=True)
    instance = PickledObjectField(null=True, blank=True)
    func_name = models.CharField(max_length=254)
    args = PickledObjectField(blank=True)
    kwargs = PickledObjectField(blank=True)
    description = models.CharField(max_length=254)
    result_ttl = models.IntegerField(null=True, blank=True)
    status = models.PositiveIntegerField(null=True,
            blank=True, choices=STATUS_CHOICES)
    enqueued_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField()
    repeat = PickledObjectField(null=True, blank=True,
            help_text="Number of times to repeat. -1 for forever.")
    interval = PickledObjectField(null=True, blank=True,
            help_text="Timedelta till next job")
    between = models.CharField(max_length=5, null=True, blank=True)
    weekdays = PickledObjectField(blank=True, null=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField('expires', null=True, blank=True)
    result = PickledObjectField(null=True, blank=True)
    exc_info = models.TextField(null=True, blank=True)
    timeout = models.PositiveIntegerField(null=True, blank=True)
    meta = PickledObjectField(blank=True)
    flow = models.ForeignKey('FlowStore', null=True, blank=True)
    if_failed = models.CharField(max_length=64, null=True, blank=True)
    if_result = models.CharField(max_length=64, null=True, blank=True)

    def __unicode__(self):
        return self.get_call_string()

    @classmethod
    def create(cls, func, args=None,
               kwargs=None, connection=None,
               result_ttl=None, status=None,
               scheduled_for=None, interval=0,
               repeat=0, between=None, weekdays=None):
        """Creates a new Job instance for the given function, arguments, and
        keyword arguments.
        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        assert isinstance(args, tuple), \
            '%r is not a valid args list.' % (args,)
        assert isinstance(kwargs, dict), \
            '%r is not a valid kwargs dict.' % (kwargs,)
        job = cls()
        job.connection = connection
        job.created_at = now()
        if inspect.ismethod(func):
            job.instance = get_method_self(func)
            job.func_name = func.__name__
        elif inspect.isfunction(func) or inspect.isbuiltin(func):
            job.func_name = '%s.%s' % (func.__module__, func.__name__)
        else:  # we expect a string
            job.func_name = func
        job.args = args
        job.kwargs = kwargs
        job.description = job.get_call_string()[:254]
        job.result_ttl = result_ttl
        job.status = status
        job.scheduled_for = scheduled_for
        job.interval = interval
        job.between = between
        job.repeat = repeat
        job.weekdays = weekdays
        job.clean()
        return job

    def clean(self):
        if isinstance(self.interval, int) and self.interval >= 0:
                self.interval = relativedelta(seconds=self.interval)
        elif self.scheduled_for and not (
                isinstance(self.interval, timedelta) or
                isinstance(self.interval, relativedelta)):
            raise InvalidInterval(
                "Interval must be a positive integer,"
                " timedelta, or relativedelta instance")

    @classmethod
    def _get_job_or_promise(cls, conn, queue, timeout):
        """
        Helper function that pops the job from the queue
        or returns a queue_name (the promise) and a revised timeout.

        The job is considered started at this point.

        The promised queue name is a queue to be polled
        at the timeout.
        """
        promise = None
        with transaction.commit_on_success(using=conn):
            try:
                qs = cls.objects.using(conn).select_for_update().filter(
                    queue_id=queue.name)
                if queue.scheduled:
                    near_future = now()
                    if timeout:
                        near_future += timedelta(seconds=timeout)
                    job = qs.filter(scheduled_for__lte=near_future).order_by(
                        'scheduled_for')[0]
                    if job.scheduled_for > now():
                        # ensure the next listen times-out
                        # when scheduled job is due
                        timed = near_future - now()
                        if timed.seconds > 1:
                            timeout = timed.seconds
                            promise = job.queue_id
                            job = None
                else:
                    job = qs.order_by('id')[0]

                if job:
                    job.queue = None
                    job.status = Job.STARTED
                    job.save()
                    return job, None, timeout
            except IndexError:
                pass
        return None, promise, timeout

    @property
    def func(self):
        func_name = self.func_name
        if func_name is None:
            return None

        if self.instance:
            return getattr(self.instance, func_name)

        module_name, func_name = func_name.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, func_name)


    def get_schedule_options(self):
        """Humanized schedule options"""
        s = []
        if isinstance(self.repeat, integer_types) and self.repeat < 0:
            s.append('repeat forever')
        elif isinstance(self.repeat, integer_types) and self.repeat > 0:
            s.append('repeat %i times' % self.repeat)
        elif isinstance(self.repeat, datetime):
            s.append('repeat until %s,' % self.repeat.isoformat()[:16])

        if self.interval and \
            (isinstance(self.interval, relativedelta) or \
            isinstance(self.interval, timedelta)) \
            and self.interval.seconds > 0:
            s.append('every %s' % str(self.interval))

        if self.between:
            s.append('between %s' % self.between)
        if self.weekdays:
            s.append('on any')
            for day in self.weekdays:
                if isinstance(day, weekday):
                    s.append('%s,' % str(day))
                else:
                    s.append('%s,' % str(wdays[day]))
        if s:
            s = ' '.join(s)
            if s[-1] == ',':
                s = s[:-1]
            first_letter = s[0].capitalize()
            s = first_letter + s[1:]
            return s
    get_schedule_options.short_description = 'schedule options'


    def get_ttl(self, default_ttl=None):
        """Returns ttl for a job that determines how long a job and its result
        will be persisted. In the future, this method will also be responsible
        for determining ttl for repeated jobs.
        """
        return default_ttl if self.result_ttl is None else self.result_ttl

    # Representation
    def get_call_string(self):  # noqa
        """Returns a string representation of the call, formatted as a regular
        Python function invocation statement.
        """
        if self.func_name is None:
            return 'None'

        arg_list = [repr(arg) for arg in self.args]
        arg_list += ['%s=%r' % (k, v) for k, v in self.kwargs.items()]
        args = ', '.join(arg_list)
        return '%s(%s)' % (self.func_name, args)

    # Job execution
    def perform(self):  # noqa
        """Invokes the job function with the job arguments."""
        self.result = self.func(*self.args, **self.kwargs)
        return self.result

    def save(self, *args, **kwargs):
        kwargs.setdefault('using', self.connection)
        if not self.enqueued_at:
            self.enqueued_at = now()
        if not self.scheduled_for:
            self.scheduled_for = self.enqueued_at
        super(Job, self).save(*args, **kwargs)


class FailedJob(Job):
    class Meta:
        proxy = True


class QueuedJob(Job):
    class Meta:
        proxy = True


class ScheduledJob(Job):
    class Meta:
        proxy = True


class DequeuedJob(Job):
    class Meta:
        proxy = True

########NEW FILE########
__FILENAME__ = pqbenchmark

import time
from django.core.management.base import BaseCommand
from optparse import make_option

def do_nothing(sleep=0):
    """The best job in the world."""
    if sleep:
        time.sleep(sleep/1000.0)

def worker(worker_num, backend):
    import subprocess
    print('Worker %i started' % worker_num)
    if backend == 'pq':
        subprocess.call('django-admin.py pqworker benchmark -b', 
            shell=True)
    elif backend == 'rq':
        from rq.worker import Worker
        from redis import Redis
        from rq import Queue
        q = Queue('benchmark', connection=Redis())
        w = Worker(q, connection=Redis())
        w.work(burst=False)
    print('Worker %i fin' % worker_num)
    return


def feeder(num_jobs, backend, sleep):
    if backend == 'pq':
        from pq import Queue
        q = Queue('benchmark')
    elif backend == 'rq':
        from redis import Redis
        from rq import Queue
        connection=Redis()
        q = Queue('benchmark', connection=Redis())
    print('enqueuing %i jobs'% num_jobs)
    for i in range(num_jobs):
        q.enqueue(do_nothing, sleep)
    print('feeder fin')    


class Command(BaseCommand):
    help = "Benchmarks PQ and RQ"
    args = "<number of jobs>"

    option_list = BaseCommand.option_list + (
        make_option('--workers', '-w', default=1, dest='workers',
            help='Number of workers [1]'),
        make_option('--backend', '-b', default='pq', dest='backend',
            help='Backend to use [pq] or rq'),
        make_option('--sleep', default=0, dest='sleep',
            help='Add sleep milliseconds to job [0]')
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        import multiprocessing
        import time
        backend = options.get('backend')
        if backend.lower() == 'pq':
            from pq import Queue
            from pq.job import Job
            q = Queue('benchmark')
            Job.objects.filter(queue_id='benchmark').delete()
        elif backend.lower() == 'rq':
            from redis import Redis
            from rq import Queue
            connection=Redis()
            q = Queue('benchmark', connection=Redis())
        q.empty()
        print('Init queue count: %i' % q.count)
        num_workers = int(options.get('workers'))
        sleep = int(options.get('sleep'))
        try:
            num_jobs = int(args[0])
        except IndexError:
            num_jobs = 100000 
        eq = multiprocessing.Process(target=feeder, args=(num_jobs, backend, sleep), name=str('Feeder'))
        eq.start()
        workers = []
        
        start = time.time()
        for i in range(num_workers):
            p = multiprocessing.Process(target=worker, args=(i, backend), name=str('Worker %i' % i))
            workers.append(p)
            p.start()
        eq.join()
        count = q.count
        stop = time.time()
        q.empty()

        for i, j in enumerate(workers):
            print('Terminating worker %s' % i)
            j.terminate()

        print('Fin queue count %i'% count)
        num_jobs = num_jobs - count
        total_time = stop - start
        print('Total time %s seconds' % str(total_time))
        print('Jobs completed: %i' % num_jobs)
        
        jobs_per_sec = round(num_jobs/total_time, 1)
        print('%s jobs/s' % str(jobs_per_sec))

########NEW FILE########
__FILENAME__ = pqcreate
from django.core.management.base import BaseCommand
from optparse import make_option

from django.conf import settings

from pq.queue import PQ_DEFAULT_JOB_TIMEOUT


class Command(BaseCommand):
    help = "Create a queue"
    args = "<queue queue ...>"


    option_list = BaseCommand.option_list + (
        make_option('--queue', '-q', dest='queue', default='',
            help='Specify the queue [default]'),
        make_option('--conn', '-c', dest='conn', default='default',
            help='Specify a connection [default]'),
        make_option('--scheduled', action="store_true", default=False, 
            dest="scheduled", help="Schedule jobs in the future"),
        make_option('--timeout', '-t', type="int", dest='timeout',
            help="Default timeout in seconds"),
        make_option('--serial', action="store_true", default=False, dest='serial',
            help="A timeout in seconds"),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        from pq.queue import Queue, SerialQueue
        verbosity = int(options.get('verbosity', 1))
        timeout = options.get('timeout')
        for queue in args:
            if options['serial']:
                q = SerialQueue.create(queue)
            else:
                q = Queue.create(queue)
            q.connection = options.get('conn')
            q.scheduled = options.get('scheduled')
            if timeout:
                q.default_timeout = timeout
            q.save()


########NEW FILE########
__FILENAME__ = pqenqueue
from django.core.management.base import BaseCommand
from optparse import make_option

from django.conf import settings

from pq.queue import PQ_DEFAULT_JOB_TIMEOUT


class Command(BaseCommand):
    help = "Enqueue a function"
    args = "<function arg arg ...>"


    option_list = BaseCommand.option_list + (
        make_option('--queue', '-q', dest='queue', default='',
            help='Specify the queue [default]'),
        make_option('--conn', '-c', dest='conn', default='default',
            help='Specify a connection [default]'),
        make_option('--timeout', '-t', type="int", dest='timeout',
            help="A timeout in seconds"),
        make_option('--serial', action="store_true", default=False, dest='serial',
            help="A timeout in seconds"),
        make_option('--sync', action="store_true", default=False, dest='sync',
            help="Perform the task now")
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        from pq.queue import Queue, SerialQueue
        verbosity = int(options.get('verbosity', 1))
        func = args[0]
        args = args[1:]
        async = not options.get('sync')
        timeout = options.get('timeout')
        queue = options.get('queue')
        conn = options.get('conn')
        if options['serial']:
            queue = queue or 'serial'
            q = SerialQueue.create(queue, connection=conn)
        else:
            queue = queue or 'default'
            q = Queue.create(queue, connection=conn)
        if timeout:
            job = q.enqueue_call(func, args=args, timeout=timeout, async=async)
        else:
            job = q.enqueue_call(func, args=args, async=async)
        if verbosity and job.id:
            print('Job %i created' % job.id)
        elif verbosity:
            print('Job complete')
########NEW FILE########
__FILENAME__ = pqschedule
from django.core.management.base import BaseCommand
from optparse import make_option

from six import integer_types
from dateutil import parser
from django.conf import settings
from django.utils.timezone import now, get_default_timezone

from pq.queue import PQ_DEFAULT_JOB_TIMEOUT


class Command(BaseCommand):
    help = "Schedule a function 'now' or at a future date."
    args = "<function now|ISO8601 arg arg ...>"


    option_list = BaseCommand.option_list + (
        make_option('--queue', '-q', dest='queue', default='',
            help='Specify the queue [default]'),
        make_option('--conn', '-c', dest='conn', default='default',
            help='Specify a connection [default]'),
        make_option('--timeout', '-t', type="int", dest='timeout',
            help="A timeout in seconds"),
        make_option('--serial', action="store_true", default=False, dest='serial',
            help="Serial queue"),
        make_option('--repeat', '-r', type="int", dest='repeat', default=0,
            help="Repeat number of times or -1 for indefinitely"),
        make_option('--interval', '-i', type="int", dest='interval', default=0,
            help="Interval seconds between repeats"),
        make_option('--between', '-b', dest='between', default='',
            help="Restricted time"),
        make_option('--mo', action="store_const", const=0, dest='mo', 
            help="Monday"),
        make_option('--tu', action="store_const", const=1, dest='tu', 
            help="Tuesday"),
        make_option('--we', action="store_const", const=2, dest='we', 
            help="Wednesday"),
        make_option('--th', action="store_const", const=3, dest='th', 
            help="Thursday"),
        make_option('--fr', action="store_const", const=4, dest='fr', 
            help="Friday"),
        make_option('--sa', action="store_const", const=5, dest='sa', 
            help="Saturday"),
        make_option('--su', action="store_const", const=6, dest='su', 
            help="Sunday"),
        make_option('--mtwtf', action="store_true", dest='mtwtf', 
            help="Monday to Friday"),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.
        """
        from pq.queue import Queue, SerialQueue
        verbosity = int(options.get('verbosity', 1))
        func = args[1]
        if args[0].lower() == 'now':
            at = now()
        else:
            at = parser.parse(args[0])
        if not at.tzinfo:
            at = at.replace(tzinfo=get_default_timezone())

        args = args[2:]
        if options.get('mtwtf'):
            weekdays = (0,1,2,3,4)
        else:
            weekdays = (
                options.get('mo'),
                options.get('tu'),
                options.get('we'),
                options.get('th'),
                options.get('fr'),
                options.get('sa'),
                options.get('su'),
                )

            weekdays = [w for w in weekdays if isinstance(w, integer_types)]
        timeout = options.get('timeout')
        queue = options.get('queue')
        conn = options.get('conn')
        if options['serial']:
            queue = queue or 'serial'
            q = SerialQueue.create(queue, connection=conn, scheduled=True)
        else:
            queue = queue or 'default'
            q = Queue.create(queue, connection=conn, scheduled=True)
        job = q.schedule_call(at, func, args=args, 
            timeout=timeout,
            repeat=options['repeat'],
            interval=options['interval'],
            between=options['between'],
            weekdays=weekdays
            )
        if verbosity:
            print('Job %i created' % job.id)


########NEW FILE########
__FILENAME__ = pqworker
import logging
import time
import sys
from django.core.management.base import BaseCommand
from optparse import make_option

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Starts a pq worker on all available queues or just specified queues in order"
    args = "[queue queue ...]"


    option_list = BaseCommand.option_list + (
        make_option('--burst', '-b', action='store_true', dest='burst',
            default=False, help='Run in burst mode (quit after all work is done)'),
        make_option('--name', '-n', default=None, dest='name',
            help='Specify a different name'),
        make_option('--connection', '-c', action='store', default='default',
                    help='Report exceptions to this Sentry DSN'),
        make_option('--sentry-dsn', action='store', default=None, metavar='URL',
                    help='Report exceptions to this Sentry DSN'),
        make_option('--terminate', action='store_true', dest='terminate',
                    help='Terminate worker'),
    )

    def handle(self, *args, **options):
        """
        The actual logic of the command. Subclasses must implement
        this method.

        """
        from django.conf import settings
        from pq.queue import Queue, SerialQueue
        from pq.worker import Worker

        sentry_dsn = options.get('sentry_dsn')
        if not sentry_dsn:
            sentry_dsn = settings.SENTRY_DSN if hasattr(settings, 'SENTRY_DSN') else None

        verbosity = int(options.get('verbosity'))
        queues = []
        if options.get('terminate'):
            workern = [w.name for w in Worker.objects.all()]

            for worker in Worker.objects.all()[:]:
                worker.stop = True
                worker.save()

            print('Terminating %s ...' % ' '.join(workern))  
            while Worker.objects.all():
                time.sleep(5)
            
            return
        if not args:
            args = [q[0] for q in Queue.objects.values_list('name').exclude(name='failed')]
            args.sort()
        if not args:
            print('There are no queues to work on')
            sys.exit(1)
        for queue in args:
            try:
                q = Queue.objects.get(name=queue)
            except Queue.DoesNotExist:
                print("The '%s' queue does not exist. Use the pqcreate command to create it." % queue)
                continue
            if q.serial:
                q = SerialQueue.objects.get(name=queue)
            else:
                q = Queue.objects.get(name=queue)
            q.connection = options['connection']
            q._saved = True
            queues.append(q)
        if queues:
            w = Worker.create(queues, name=options.get('name'), connection=options['connection'])

            # Should we configure Sentry?
            if sentry_dsn:
                from raven import Client
                from pq.contrib.sentry import register_sentry
                client = Client(sentry_dsn)
                register_sentry(client, w)

            w.work(burst=options['burst'])


########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Job'
        db.create_table(u'pq_job', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('origin', self.gf('django.db.models.fields.CharField')(max_length=254, null=True, blank=True)),
            ('queue', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['pq.Queue'], null=True, blank=True)),
            ('instance', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('func_name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('args', self.gf('picklefield.fields.PickledObjectField')(blank=True)),
            ('kwargs', self.gf('picklefield.fields.PickledObjectField')(blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('result_ttl', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('enqueued_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('scheduled_for', self.gf('django.db.models.fields.DateTimeField')()),
            ('repeat', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('interval', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('between', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('weekdays', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('ended_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('expired_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('result', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('exc_info', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('timeout', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('meta', self.gf('picklefield.fields.PickledObjectField')(blank=True)),
            ('flow', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['pq.FlowStore'], null=True, blank=True)),
            ('if_failed', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('if_result', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal(u'pq', ['Job'])

        # Adding model 'Queue'
        db.create_table(u'pq_queue', (
            ('name', self.gf('django.db.models.fields.CharField')(default='default', max_length=100, primary_key=True)),
            ('default_timeout', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('cleaned', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('scheduled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('lock_expires', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 4, 10, 0, 0))),
            ('serial', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'pq', ['Queue'])

        # Adding model 'FlowStore'
        db.create_table(u'pq_flowstore', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('queue', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['pq.Queue'], null=True, blank=True)),
            ('enqueued_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('ended_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('expired_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('jobs', self.gf('picklefield.fields.PickledObjectField')(blank=True)),
        ))
        db.send_create_signal(u'pq', ['FlowStore'])

        # Adding model 'Worker'
        db.create_table(u'pq_worker', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254, primary_key=True)),
            ('birth', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('expire', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('queue_names', self.gf('django.db.models.fields.CharField')(max_length=254, null=True, blank=True)),
        ))
        db.send_create_signal(u'pq', ['Worker'])


    def backwards(self, orm):
        # Deleting model 'Job'
        db.delete_table(u'pq_job')

        # Deleting model 'Queue'
        db.delete_table(u'pq_queue')

        # Deleting model 'FlowStore'
        db.delete_table(u'pq_flowstore')

        # Deleting model 'Worker'
        db.delete_table(u'pq_worker')


    models = {
        u'pq.flowstore': {
            'Meta': {'object_name': 'FlowStore'},
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'enqueued_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expired_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jobs': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.Queue']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'pq.job': {
            'Meta': {'object_name': 'Job'},
            'args': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'between': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'enqueued_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'exc_info': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'expired_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'flow': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.FlowStore']", 'null': 'True', 'blank': 'True'}),
            'func_name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'if_failed': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'if_result': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'instance': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'interval': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'kwargs': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'meta': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'origin': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.Queue']", 'null': 'True', 'blank': 'True'}),
            'repeat': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'result': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'result_ttl': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_for': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timeout': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'weekdays': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'})
        },
        u'pq.queue': {
            'Meta': {'object_name': 'Queue'},
            'cleaned': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_timeout': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'lock_expires': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 4, 10, 0, 0)'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '100', 'primary_key': 'True'}),
            'scheduled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'serial': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'pq.worker': {
            'Meta': {'object_name': 'Worker'},
            'birth': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expire': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254', 'primary_key': 'True'}),
            'queue_names': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['pq']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_queue_connection__add_field_queue_idempotent__add_fiel
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Queue.idempotent'
        db.add_column(u'pq_queue', 'idempotent',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Worker.stop'
        db.add_column(u'pq_worker', 'stop',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Queue.idempotent'
        db.delete_column(u'pq_queue', 'idempotent')

        # Deleting field 'Worker.stop'
        db.delete_column(u'pq_worker', 'stop')


    models = {
        u'pq.flowstore': {
            'Meta': {'object_name': 'FlowStore'},
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'enqueued_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expired_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jobs': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.Queue']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'pq.job': {
            'Meta': {'object_name': 'Job'},
            'args': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'between': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'enqueued_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'exc_info': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'expired_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'flow': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.FlowStore']", 'null': 'True', 'blank': 'True'}),
            'func_name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'if_failed': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'if_result': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'instance': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'interval': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'kwargs': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'meta': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'origin': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.Queue']", 'null': 'True', 'blank': 'True'}),
            'repeat': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'result': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'result_ttl': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_for': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timeout': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'weekdays': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'})
        },
        u'pq.queue': {
            'Meta': {'object_name': 'Queue'},
            'cleaned': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_timeout': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'idempotent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lock_expires': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 5, 12, 0, 0)'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '100', 'primary_key': 'True'}),
            'scheduled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'serial': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'pq.worker': {
            'Meta': {'object_name': 'Worker'},
            'birth': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expire': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254', 'primary_key': 'True'}),
            'queue_names': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'stop': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['pq']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_worker_heartbeat
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Worker.heartbeat'
        db.add_column(u'pq_worker', 'heartbeat',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Worker.heartbeat'
        db.delete_column(u'pq_worker', 'heartbeat')


    models = {
        u'pq.flowstore': {
            'Meta': {'object_name': 'FlowStore'},
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'enqueued_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expired_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jobs': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.Queue']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'pq.job': {
            'Meta': {'object_name': 'Job'},
            'args': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'between': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'enqueued_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'exc_info': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'expired_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'flow': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.FlowStore']", 'null': 'True', 'blank': 'True'}),
            'func_name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'if_failed': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'if_result': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'instance': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'interval': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'kwargs': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'meta': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'origin': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.Queue']", 'null': 'True', 'blank': 'True'}),
            'repeat': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'result': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'result_ttl': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_for': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timeout': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'weekdays': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'})
        },
        u'pq.queue': {
            'Meta': {'object_name': 'Queue'},
            'cleaned': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_timeout': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'idempotent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lock_expires': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 5, 24, 0, 0)'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '100', 'primary_key': 'True'}),
            'scheduled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'serial': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'pq.worker': {
            'Meta': {'object_name': 'Worker'},
            'birth': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expire': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'heartbeat': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254', 'primary_key': 'True'}),
            'queue_names': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'stop': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['pq']
########NEW FILE########
__FILENAME__ = models
from .queue import Queue
from .job import Job
from .worker import Worker
from .flow import FlowStore


########NEW FILE########
__FILENAME__ = queue
import logging
import select
from datetime import timedelta, datetime

from dateutil.relativedelta import relativedelta
from django.db import connections, DatabaseError
from django.db import transaction
from django.db import models
from django.conf import settings
from django.utils.timezone import now
from six import string_types

from .job import Job
from .utils import get_restricted_datetime
from .exceptions import (DequeueTimeout, InvalidBetween,
                         InvalidInterval, InvalidQueueName)

_PQ_QUEUES = {}
PQ_DEFAULT_JOB_TIMEOUT = getattr(settings, 'PQ_DEFAULT_JOB_TIMEOUT', 600)
PQ_QUEUE_CACHE = getattr(settings, 'PQ_QUEUE_CACHE', True)

logger = logging.getLogger(__name__)

def get_failed_queue(connection='default'):
    """Returns a handle to the special failed queue."""
    return FailedQueue.create(connection=connection)


class _EnqueueArgs(object):
    """Simple argument and keyword argument wrapper
        for enqueue and schedule queue methods
    """
    def __init__(self, *args, **kwargs):
        self.timeout = None
        self.result_ttl = None
        self.async = True
        self.args = args
        self.kwargs = kwargs
        # Detect explicit invocations, i.e. of the form:
        #  q.enqueue(foo, args=(1, 2), kwargs={'a': 1}, timeout=30)
        if 'args' in kwargs or 'kwargs' in kwargs:
            assert args == (), 'Extra positional arguments cannot be used when using explicit args and kwargs.'  # noqa
            self.result_ttl = kwargs.pop('result_ttl', None)
            self.timeout = kwargs.pop('timeout', None)
            self.async = kwargs.pop('async', True)
            self.args = kwargs.pop('args', None)
            self.kwargs = kwargs.pop('kwargs', None)


class Queue(models.Model):

    connection = None
    name = models.CharField(max_length=100, primary_key=True, default='default')
    default_timeout = models.PositiveIntegerField(null=True, blank=True)
    cleaned = models.DateTimeField(null=True, blank=True)
    scheduled = models.BooleanField(default=False,
        help_text="Optimisation: scheduled tasks are slower.")
    lock_expires = models.DateTimeField(default=now())
    serial = models.BooleanField(default=False)
    idempotent = models.BooleanField(default=False)
    _async = True
    _saved = False

    def __unicode__(self):
        return self.name

    @classmethod
    def create(cls,
               name='default', default_timeout=None,
               connection='default', scheduled=False, async=True, idempotent=False):
        """Returns a Queue ready for accepting jobs"""
        queue = cls(name=cls.validated_name(name))
        queue.default_timeout = default_timeout or PQ_DEFAULT_JOB_TIMEOUT
        queue.connection = connection
        queue.scheduled = scheduled
        queue.idempotent = idempotent
        queue._async = async
        return queue

    @classmethod
    def validated_name(cls, name):
        """Ensure there is no closing parenthesis"""
        if not name or not isinstance(name, string_types):
            raise InvalidQueueName('%s is not a valid queue name' % str(name))
        name = name.strip()
        if name.lower() == 'failed':
            raise InvalidQueueName("'failed' is a reserved queue name")
        return name

    @classmethod
    def validated_queue(cls, name):
        q = _PQ_QUEUES.get(name) if PQ_QUEUE_CACHE else None
        created = False
        if not q:
            q, created = cls.objects.get_or_create(name=name)
            _PQ_QUEUES[name] = q
        if not created and q.serial:
            raise InvalidQueueName("%s is a serial queue" % name)
        return q

    def save_queue(self):
        q = self.validated_queue(self.name)
        fields = ['default_timeout', 'scheduled', 'idempotent']
        dirty = [f for f in fields if q.__dict__[f] != self.__dict__[f]]
        if dirty:
            q.default_timeout = self.default_timeout
            q.serial = self.serial
            q.idempotent = self.idempotent
            # a queue remains a scheduled queue if prior scheduled jobs have been
            # submitted to it
            q.scheduled = True if self.scheduled else q.scheduled
            q.save()
            _PQ_QUEUES[self.name] = q

    @classmethod
    def all(cls, connection='default'):
        allqs = []
        queues = cls.objects.using(connection).all()[:]
        for q in queues:
            if q.name == 'failed':
                allqs.append(get_failed_queue(connection))
            else:
                allqs.append(q)

        return allqs


    @property
    def count(self):
        return Job.objects.using(self.connection).filter(queue_id=self.name).count()


    def delete_expired_ttl(self):
        """Delete jobs from the queue which have expired"""
        with transaction.commit_on_success(using=self.connection):
            Job.objects.using(self.connection).filter(
                origin=self.name, status=Job.FINISHED, expired_at__lte=now()).delete()

    def empty(self):
        """Delete all jobs from a queue"""
        Job.objects.using(self.connection).filter(queue_id=self.name).delete()

    def enqueue_next(self, job):
        """Enqueue the next scheduled job relative to this one"""
        if not job.repeat:
            return

        if isinstance(job.repeat, datetime):
            if job.repeat <= now():
                return
            else:
                repeat = job.repeat
        else:
            repeat = job.repeat - 1 if job.repeat > 0 else -1
        timeout = job.timeout
        scheduled_for = job.scheduled_for + job.interval
        scheduled_for = get_restricted_datetime(scheduled_for, job.between, job.weekdays)
        status = Job.SCHEDULED if scheduled_for > job.scheduled_for else Job.QUEUED
        self.save_queue()
        job = Job.create(job.func, job.args, job.kwargs, connection=job.connection,
                         result_ttl=job.result_ttl,
                         scheduled_for=scheduled_for,
                         repeat=repeat,
                         interval=job.interval,
                         between=job.between,
                         weekdays=job.weekdays,
                         status=status)
        return self.enqueue_job(job, timeout=timeout)


    def enqueue_call(self, func, args=None, kwargs=None,
        timeout=None, result_ttl=None, async=True, at=None,
        repeat=None, interval=0, between='', weekdays=None): #noqa
        """Creates a job to represent the delayed function call and enqueues
        it.

        It is much like `.enqueue()`, except that it takes the function's args
        and kwargs as explicit arguments.  Any kwargs passed to this function
        contain options for PQ itself.
        """
        at = get_restricted_datetime(at, between, weekdays)
        # Scheduled tasks require a slower query
        status = Job.SCHEDULED if at else Job.QUEUED
        self.save_queue()
        timeout = timeout or self.default_timeout

        job = Job.create(func, args, kwargs, connection=self.connection,
                         result_ttl=result_ttl,
                         scheduled_for=at,
                         repeat=repeat,
                         interval=interval,
                         between=between,
                         weekdays=weekdays,
                         status=status)
        return self.enqueue_job(job, timeout=timeout, async=async)

    def enqueue(self, f, *args, **kwargs):
        """Creates a job to represent the delayed function call and enqueues
        it.

        Expects the function to call, along with the arguments and keyword
        arguments.

        The function argument `f` may be any of the following:

        * A reference to a function
        * A reference to an object's instance method
        * A string, representing the location of a function (must be
          meaningful to the import context of the workers)
        """
        if not isinstance(f, string_types) and f.__module__ == '__main__':
            raise ValueError(
                    'Functions from the __main__ module cannot be processed '
                    'by workers.')
        enq = _EnqueueArgs(*args, **kwargs)

        return self.enqueue_call(func=f, args=enq.args, kwargs=enq.kwargs,
                                 timeout=enq.timeout, 
                                 result_ttl=enq.result_ttl,
                                 async=enq.async)

    def enqueue_job(self, job, timeout=None, set_meta_data=True, async=True):
        """Enqueues a job for delayed execution.

        When the `timeout` argument is sent, it will overrides the default
        timeout value of 180 seconds.  `timeout` may either be a string or
        integer.

        If the `set_meta_data` argument is `True` (default), it will update
        the properties `origin` and `enqueued_at`.

        If Queue is instantiated with async=False, job is executed immediately.
        """
        if set_meta_data:
            job.origin = self.name

        if timeout:
            job.timeout = timeout
        else:
            job.timeout = PQ_DEFAULT_JOB_TIMEOUT  # default

        if self._async and async:
            job.queue_id = self.name
            job.save()
            self.notify(job.id)

        else:
            job.perform()
            job.status = Job.FINISHED
        return job

    def schedule(self, at, f, *args, **kwargs):
        """As per enqueue but schedule ``at`` datetime"""

        if not isinstance(f, string_types) and f.__module__ == '__main__':
            raise ValueError(
                    'Functions from the __main__ module cannot be processed '
                    'by workers.')
        enq = _EnqueueArgs(*args, **kwargs)

        return self.enqueue_call(func=f, args=enq.args, kwargs=enq.kwargs,
                                 timeout=enq.timeout, result_ttl=enq.result_ttl,
                                 async=enq.async,
                                 at=at)


    def schedule_call(self, at, f, args=None, kwargs=None,
        timeout=None, result_ttl=None, repeat=0, interval=0,
        between='', weekdays=None):
        """
        As per enqueue_call but with a datetime argument ``at`` first.

        ``repeat`` a number of times or infinitely -1 at
        ``interval`` seconds. Interval also accepts a timedelta or
        dateutil relativedelta instance

        ``between`` is a time window that the scheduled
        function will be called for example:
        '0:0/6:00' or '0-6' or '0.0-6.0'

        ``weekdays`` is a tuple or list of relativedelta weekday
        instances or the same of integers ranging from 0 (MO) to 6 (SU)

        """

        return self.enqueue_call(func=f, args=args, kwargs=kwargs,
                                 timeout=timeout, result_ttl=result_ttl,
                                 at=at, repeat=repeat, interval=interval,
                                 between=between, weekdays=weekdays)

    def dequeue(self):
        """Dequeues the front-most job from this queue.

        Returns a Job instance, which can be executed or inspected.
        Does not respect serial queue locks
        """
        with transaction.commit_on_success(using=self.connection):
            try:
                job = Job.objects.using(self.connection).select_for_update().filter(
                queue=self, status=Job.QUEUED,
                scheduled_for__lte=now()).order_by('scheduled_for')[0]
                job.queue = None
                job.save()
            except IndexError:
                job = None
        if job and job.repeat:
            self.enqueue_next(job)

        return job


    @classmethod
    def _listen_for_jobs(cls, queue_names, connection_name, timeout):
        """Get notification from postgresql channels
        corresponding to queue names.
        """
        conn = cls.listen(connection_name, queue_names)

        while True:
            for notify in conn.notifies:
                if not notify.channel in queue_names:
                    continue
                elif notify.payload == 'stop':
                    raise DequeueTimeout(0)
                conn.notifies.remove(notify)
                logger.debug('Got job notification %s on queue %s'% (
                    notify.payload, notify.channel))
                return notify.channel
            else:
                r, w, e = select.select([conn], [], [], timeout)
                if not (r or w or e):
                    raise DequeueTimeout(timeout)
                logger.debug('Got data on %s' % (str(r[0])))
                conn.poll()

    @classmethod
    def dequeue_any(cls, queues, timeout):
        """Helper method, that polls the database queues for new jobs.
        The timeout parameter is interpreted as follows:
            None - non-blocking (return immediately)
             > 0 - maximum number of seconds to block

        Returns a job instance and a queue
        """
        burst = True if not timeout else False
        job = None
        # queues must share the same connection - enforced at worker startup
        conn = queues[0].connection
        queue_names = [q.name for q in queues]
        q_lookup = dict(zip(queue_names, queues))
        default_timeout = timeout or 0
        queue_stack = queues[:]
        while True:
            while queue_stack:
                q = queue_stack.pop(0)
                if q.serial and not q.acquire_lock(timeout):
                    # promise to check the queue at timeout
                    job = None
                    promise = q.name
                else:
                    job, promise, timeout = Job._get_job_or_promise(
                        conn, q, timeout)
                if job and job.repeat:
                    self.enqueue_next(job)
                if job:
                    return job, q
            if burst:
                return
            if promise:
                queue_stack.append(promise)
            q = cls._listen_for_jobs(queue_names, conn, timeout)
            timeout = default_timeout
            queue_stack.append(q_lookup[q])

    @classmethod
    def listen(cls, connection_name, queue_names):
        conn = connections[connection_name]
        cursor = conn.cursor()
        for q_name in queue_names:
            sql = "LISTEN \"%s\"" % q_name
            cursor.execute(sql)
        cursor.close()
        # Need to return django's wrapped open connection so that
        # the calling method can use the same session to actually
        # receive pg notify messages
        return conn.connection


    def notify(self, job_id):
        """Notify postgresql channel when a job is enqueued"""
        cursor = connections[self.connection].cursor()
        cursor.execute("SELECT pg_notify(%s, %s);", (self.name, str(job_id)))
        cursor.close()


class SerialQueue(Queue):
    """A queue with a lock"""

    class Meta:
        proxy = True

    @classmethod
    def create(cls,
               name='serial', default_timeout=None,
               connection='default', scheduled=False, async=True):
        """Returns a Queue ready for accepting jobs"""
        queue = super(SerialQueue, cls).create(name, 
            default_timeout, connection, scheduled, async)
        if not queue.serial:
            queue.serial=True
            queue.save()
        return queue

    @classmethod
    def validated_queue(cls, name):
        q, created = cls.objects.get_or_create(name=name)
        if not created and not q.serial:
            raise InvalidQueueName("%s is not a serial queue" % name)
        return q

    def acquire_lock(self, timeout=0, no_wait=True):
        try:
            with transaction.commit_on_success(using=self.connection):
                SerialQueue.objects.using(
                    self.connection).select_for_update(
                    no_wait=no_wait).get(
                    name=self.name, lock_expires__lte=now())
                if timeout:
                    self.lock_expires = now() + timedelta(seconds=timeout)
                    self.save()
        except DatabaseError:
            logger.debug('%s SerialQueue currently locked on update' % self.name)
            return False
        except SerialQueue.DoesNotExist:
            logger.debug('%s SerialQueue currently locked' % self.name)
            return False
        return True

    def release_lock(self):
        self.lock_expires = now()
        self.save()


class FailedQueue(Queue):
    class Meta:
        proxy = True

    @classmethod
    def validated_name(self, name):
        return name

    @classmethod
    def create(cls, connection='default'):
        fq = super(FailedQueue, cls).create('failed', connection=connection)
        fq.save()
        return fq

    def quarantine(self, job, exc_info):
        """Puts the given Job in quarantine (i.e. put it on the failed
        queue).

        This is different from normal job enqueueing, since certain meta data
        must not be overridden (e.g. `origin` or `enqueued_at`) and other meta
        data must be inserted (`ended_at` and `exc_info`).
        """
        job.ended_at = now()
        job.exc_info = exc_info
        return self.enqueue_job(job, timeout=job.timeout, set_meta_data=False)


    def requeue(self, job_id):
        """Requeues the job with the given job ID."""
        with transaction.commit_on_success(self.connection):
            job = Job.objects.using(self.connection).select_for_update().get(id=job_id)
            # Delete it from the failed queue (raise an error if that failed)
            job.queue = None
            job.status = Job.QUEUED
            job.exc_info = None
            job.scheduled_for = now()
            job.save()
            q = Queue.create(job.origin, connection=self.connection)
            q.enqueue_job(job, timeout=job.timeout)


########NEW FILE########
__FILENAME__ = timeouts
import signal


class JobTimeoutException(Exception):
    """Raised when a job takes longer to complete than the allowed maximum
    timeout value.
    """
    pass


class death_penalty_after(object):
    def __init__(self, timeout):
        self._timeout = timeout

    def __enter__(self):
        self.setup_death_penalty()

    def __exit__(self, type, value, traceback):
        # Always cancel immediately, since we're done
        try:
            self.cancel_death_penalty()
        except JobTimeoutException:
            # Weird case: we're done with the with body, but now the alarm is
            # fired.  We may safely ignore this situation and consider the
            # body done.
            pass

        # __exit__ may return True to supress further exception handling.  We
        # don't want to suppress any exceptions here, since all errors should
        # just pass through, JobTimeoutException being handled normally to the
        # invoking context.
        return False

    def handle_death_penalty(self, signum, frame):
        raise JobTimeoutException('Job exceeded maximum timeout '
                'value (%d seconds).' % self._timeout)

    def setup_death_penalty(self):
        """Sets up an alarm signal and a signal handler that raises
        a JobTimeoutException after the timeout amount (expressed in
        seconds).
        """
        signal.signal(signal.SIGALRM, self.handle_death_penalty)
        signal.alarm(self._timeout)

    def cancel_death_penalty(self):
        """Removes the death penalty alarm and puts back the system into
        default signal handling.
        """
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""
Miscellaneous helper functions.

The formatter for ANSI colored console output is heavily based on Pygments
terminal colorizing code, originally by Georg Brandl.
"""
import os
import re
import sys
import logging
from datetime import timedelta, datetime, time
from dateutil import relativedelta
from six import integer_types

from .compat import is_python_version
from .exceptions import InvalidBetween, InvalidWeekdays


def gettermsize():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct  # noqa
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return None
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])

def get_restricted_datetime(at, between='', weekdays=None):
    """
    Returns a new datetime that always falls in
    the timerange ``between`` an iso 8601 string or variant,
    and days where days is a list or tuple of relativedelta weekday
    objects.

    If the time part of the datetime falls before the
    timerange the datetime will be moved forward to the
    start of the range. In the event the time is after the
    range the datetime will be moved forward to the next
    day.

    >>> dt = datetime(2013,1,1,6,30)
    >>> get_restricted_datetime(dt, '7-12')
    datetime(2013,1,1,7)
    >>> get_restricted_datetime(dt, '1:00/6:00')
    datetime(2013,1,2,1)
    >>> get_restricted_datetime(dt, '1:00-6:00')
    datetime(2013,1,2,1)
    >>> get_restricted_datetime(dt, '1:00:10/6:00:59')
    datetime(2013,1,2,1)
    """
    if between:
        pattern = re.compile(
            r"(\d{1,2})[:.]?(\d{0,2})[:.]?\d{0,2}\s*[/-]+" +
            r"\s*(\d{1,2})[:.]?(\d{0,2})[:.]?\d{0,2}"
            )
        r = pattern.search(between)
        if not r:
            raise InvalidBetween("Invalid between range %s" % between)

        shour, smin, ehour, emin = r.groups()
        shour = int(shour)
        smin = int(smin) if smin else 0
        ehour = int(ehour)
        emin = int(emin) if emin else 0
        if ehour < shour:
            raise InvalidBetween("Between end cannot be before start")
        elif ehour == 24:
            ehour = 23
            emin = 59
        st = time(shour, smin, tzinfo=at.tzinfo)
        et = time(ehour, emin, tzinfo=at.tzinfo)
        date = at.date()
        compare_st = datetime.combine(date, st)
        compare_et = datetime.combine(date, et)
        if at < compare_st:
            at = compare_st
        elif at > compare_et:
            at = compare_st + timedelta(days=1)
    if weekdays:
        weekdays = list(weekdays)
        for i, value in enumerate(weekdays):
            if isinstance(value, relativedelta.weekday):
                weekdays[i] = value.weekday
            elif isinstance(value, integer_types) and value >=0 and value <=6:
                continue
            else:
                msg = "Invalid weekday %s. Weekdays must be a" % str(value)
                msg = ' '.join([msg, "list or tuple of relativedelta.weekday",
                               "instances or integers between 0 and 6"])
                raise InvalidWeekdays(msg)
        weekdays = sorted(weekdays)
        nextdays = relativedelta.weekdays[at.weekday():]
        priordays = relativedelta.weekdays[:at.weekday()]
        for i, day in enumerate(nextdays + priordays):
            if day.weekday in weekdays:
                at += timedelta(days=i)
                break
    return at


class _Colorizer(object):
    def __init__(self):
        esc = "\x1b["

        self.codes = {}
        self.codes[""] = ""
        self.codes["reset"] = esc + "39;49;00m"

        self.codes["bold"] = esc + "01m"
        self.codes["faint"] = esc + "02m"
        self.codes["standout"] = esc + "03m"
        self.codes["underline"] = esc + "04m"
        self.codes["blink"] = esc + "05m"
        self.codes["overline"] = esc + "06m"

        dark_colors = ["black", "darkred", "darkgreen", "brown", "darkblue",
                        "purple", "teal", "lightgray"]
        light_colors = ["darkgray", "red", "green", "yellow", "blue",
                        "fuchsia", "turquoise", "white"]

        x = 30
        for d, l in zip(dark_colors, light_colors):
            self.codes[d] = esc + "%im" % x
            self.codes[l] = esc + "%i;01m" % x
            x += 1

        del d, l, x

        self.codes["darkteal"] = self.codes["turquoise"]
        self.codes["darkyellow"] = self.codes["brown"]
        self.codes["fuscia"] = self.codes["fuchsia"]
        self.codes["white"] = self.codes["bold"]
        self.notty = not sys.stdout.isatty()


    def reset_color(self):
        return self.codes["reset"]

    def colorize(self, color_key, text):
        if not sys.stdout.isatty():
            return text
        else:
            return self.codes[color_key] + text + self.codes["reset"]

    def ansiformat(self, attr, text):
        """
        Format ``text`` with a color and/or some attributes::

            color       normal color
            *color*     bold color
            _color_     underlined color
            +color+     blinking color
        """
        result = []
        if attr[:1] == attr[-1:] == '+':
            result.append(self.codes['blink'])
            attr = attr[1:-1]
        if attr[:1] == attr[-1:] == '*':
            result.append(self.codes['bold'])
            attr = attr[1:-1]
        if attr[:1] == attr[-1:] == '_':
            result.append(self.codes['underline'])
            attr = attr[1:-1]
        result.append(self.codes[attr])
        result.append(text)
        result.append(self.codes['reset'])
        return ''.join(result)


colorizer = _Colorizer()


def make_colorizer(color):
    """Creates a function that colorizes text with the given color.

    For example:

        green = make_colorizer('darkgreen')
        red = make_colorizer('red')

    Then, you can use:

        print "It's either " + green('OK') + ' or ' + red('Oops')
    """
    def inner(text):
        return colorizer.colorize(color, text)
    return inner


class ColorizingStreamHandler(logging.StreamHandler):

    levels = {
        logging.WARNING: make_colorizer('darkyellow'),
        logging.ERROR: make_colorizer('darkred'),
        logging.CRITICAL: make_colorizer('darkred'),
    }

    def __init__(self, exclude=None, *args, **kwargs):
        self.exclude = exclude
        if is_python_version((2,6)):
            logging.StreamHandler.__init__(self, *args, **kwargs)
        else:
            super(ColorizingStreamHandler, self).__init__(*args, **kwargs)

    @property
    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)
        return isatty and isatty()

    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        if self.is_tty:
            colorize = self.levels.get(record.levelno, lambda x: x)

            # Don't colorize any traceback
            parts = message.split('\n', 1)
            parts[0] = " ".join([parts[0].split(" ", 1)[0], colorize(parts[0].split(" ", 1)[1])])

            message = '\n'.join(parts)

        return message

def test_job():
    """ A simple do nothing test job """
    print('Hello world')
########NEW FILE########
__FILENAME__ = worker
import sys
import os
import errno
import random
import time
from datetime import timedelta

try:
    from procname import setprocname
except ImportError:
    def setprocname(*args, **kwargs):  # noqa
        pass
import socket
import signal
import traceback
import logging
from datetime import timedelta

from picklefield.fields import PickledObjectField
from django.db import connections, models, transaction
from django.conf import settings
from django.utils.timezone import now
from six import u

from .queue import Queue as PQ
from .queue import PQ_DEFAULT_JOB_TIMEOUT, get_failed_queue
from .flow import Flow, FlowStore
from .job import Job
from .utils import make_colorizer
from .exceptions import (NoQueueError, UnpickleError,
                         DequeueTimeout, StopRequested,
                         MulipleQueueConnectionsError)
from .timeouts import death_penalty_after

from . import __version__ as VERSION


green = make_colorizer('darkgreen')
yellow = make_colorizer('darkyellow')
blue = make_colorizer('darkblue')

PQ_DEFAULT_WORKER_TTL = getattr(settings, 'PQ_DEFAULT_WORKER_TTL', 420)
PQ_DEFAULT_RESULT_TTL = getattr(settings, 'PQ_DEFAULT_RESULT_TTL', 500)


logger = logging.getLogger(__name__)


def iterable(x):
    return hasattr(x, '__iter__')

_signames = dict((getattr(signal, signame), signame) \
                    for signame in dir(signal) \
                    if signame.startswith('SIG') and '_' not in signame)

def signal_name(signum):
    # Hackety-hack-hack: is there really no better way to reverse lookup the
    # signal name?  If you read this and know a way: please provide a patch :)
    try:
        return _signames[signum]
    except KeyError:
        return 'SIG_UNKNOWN'

def close_connection():
    # Hackety-hack-hack for django_postgrespool
    for conn in connections.all():
        if hasattr(conn, '_dispose'):
            conn._dispose()
        else:
            conn.close()


class Worker(models.Model):

    name = models.CharField(max_length=254, primary_key=True)
    birth = models.DateTimeField(null=True, blank=True)
    expire = models.PositiveIntegerField('Polling TTL', null=True, blank=True)
    queue_names = models.CharField(max_length=254, null=True, blank=True)
    stop = models.BooleanField(default=False, help_text="Send a stop signal to the worker")
    heartbeat = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    @classmethod
    def all(cls, connection='default'):
        """Returns an iterable of all Workers.
        """
        return Worker.objects.using(connection).all()

    @classmethod
    def create(cls, queues, name=None,
            default_result_ttl=PQ_DEFAULT_RESULT_TTL, connection='default',
            exc_handler=None, default_worker_ttl=PQ_DEFAULT_WORKER_TTL,
            expires_after=None):  # noqa
        """Create a Worker instance without saving to the backend.
        Workers are not persistent but can register themselves.
        """
        w = cls()
        w.connection = connection
        if isinstance(queues, PQ):
            w.queues = [queues]
        else:
            w.queues = queues
        w.name = name
        w.validate_queues()
        w._exc_handlers = []
        w.default_result_ttl = default_result_ttl
        w.default_worker_ttl = default_worker_ttl
        # To save overhead we don't persist state - but we may change this behaviour.
        w.state = 'starting'
        w._is_horse = False
        w._horse_pid = 0
        w._stopped = False
        w.log = logger
        w.failed_queue = get_failed_queue(connection)
        w._clear_expired = None
        # Worker expires after x loops ( for internal testing use)
        w._expires_after = expires_after

        # By default, push the "move-to-failed-queue" exception handler onto
        # the stack
        w.push_exc_handler(w.move_to_failed_queue)
        if exc_handler is not None:
            w.push_exc_handler(exc_handler)
        return w


    def validate_queues(self):  # noqa
        """Sanity check for the given queues."""
        if not iterable(self.queues):
            raise ValueError('Argument queues not iterable.')
        elif not len(self.queues):
            raise NoQueueError('Give each worker at least one Queue.')
        connection = None
        for queue in self.queues:
            if not isinstance(queue, PQ):
                raise NoQueueError('%s is not a valid Queue.' % str(queue))
            elif connection and queue.connection != connection:
                raise MulipleQueueConnectionsError("A worker's queues must use the same connection")
            connection = queue.connection


    def get_queue_names(self):
        """Returns the queue names of this worker's queues."""
        return map(lambda q: q.name, self.queues)


    def set_queues(self, addqueues):
        self._queues = addqueues
        self.queue_names = self.get_queue_names()

    def get_queues(self):
        return self._queues
    queues = property(get_queues, set_queues)

    @property  # noqa
    def calculated_name(self):
        """Returns the name of the worker, under which it is registered to the
        monitoring system.

        By default, the name of the worker is constructed from the current
        (short) host name and the current PID.
        """
        #if self._name is None:
        hostname = socket.gethostname()
        shortname, _, _ = hostname.partition('.')
        name = '%s.%s' % (shortname, self.pid)
        return name


    @property
    def pid(self):
        """The current process ID."""
        return os.getpid()

    @property
    def horse_pid(self):
        """The horse's process ID.  Only available in the worker.  Will return
        0 in the horse part of the fork.
        """
        return self._horse_pid

    @property
    def is_horse(self):
        """Returns whether or not this is the worker or the work horse."""
        return self._is_horse

    def procline(self, message):
        """Changes the current procname for the process.

        This can be used to make `ps -ef` output more readable.
        """
        setprocname('pq: %s' % (message,))


    def register_birth(self):  # noqa
        """Registers its own birth, saving to Postgres"""
        self.log.debug('Registering birth of worker %s' % (self.calculated_name,))
        with transaction.commit_on_success(using=self.connection):
            if Worker.objects.using(self.connection).filter(name=self.calculated_name)[:]:
                raise ValueError(
                        'There exists an active worker named \'%s\' '
                        'already.' % (self.calculated_name,))
            self.name = self.calculated_name
            self.birth = now()
            self.queue_names = ','.join(self.get_queue_names())
            self.expire = self.default_worker_ttl
            self._clear_expired = now()
            self.save()
        # clear out any expired workers
        Worker.objects.filter(
            heartbeat__lte=now())\
            .delete()

    def register_heartbeat(self, timeout):
        """Register a heartbeat"""
        if self.heartbeat < now():
            self.save(timeout=timeout)

    def register_death(self):
        """Registers its own death deleting the instance"""
        self.log.debug('Clearing expired jobs from queues.')
        for q in self.queues:
            q.delete_expired_ttl()
        FlowStore.delete_expired_ttl(q.connection)
        self.log.debug('Registering death')
        self.delete()

    @property
    def stopped(self):
        if not self._stopped and Worker.objects.filter(name=self.name, stop=True):
            self._stopped = True
        return self._stopped

    def _install_signal_handlers(self):
        """Installs signal handlers for handling SIGINT and SIGTERM
        gracefully.
        """

        def request_force_stop(signum, frame):
            """Terminates the application (cold shutdown).
            """
            self.log.warning('Cold shut down.')

            # Take down the horse with the worker
            if self.horse_pid:
                msg = 'Taking down horse %d with me.' % self.horse_pid
                self.log.warning(msg)
                try:
                    os.kill(self.horse_pid, signal.SIGKILL)
                except OSError as e:
                    # ESRCH ("No such process") is fine with us
                    if e.errno != errno.ESRCH:
                        self.log.debug('Horse already down.')
                        raise
            raise SystemExit()

        def request_stop(signum, frame):
            """Stops the current worker loop but waits for child processes to
            end gracefully (warm shutdown).
            """
            self.log.debug('Got signal %s.' % signal_name(signum))

            signal.signal(signal.SIGINT, request_force_stop)
            signal.signal(signal.SIGTERM, request_force_stop)

            msg = 'Warm shut down requested.'
            self.log.warning(msg)
            # If shutdown is requested in the middle of a job, wait until
            # finish before shutting down
            if self.state == 'busy':
                self._stopped = True
                self.log.debug('Stopping after current horse is finished. '
                               'Press Ctrl+C again for a cold shutdown.')
            else:
                raise StopRequested()

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)


    def work(self, burst=False):  # noqa
        """Starts the work loop.

        Pops and performs all jobs on the current list of queues.  When all
        queues are empty, block and wait for new jobs to arrive on any of the
        queues, unless `burst` mode is enabled.

        The return value indicates whether any jobs were processed.
        """
        # delayed saving of queues
        for q in self.queues:
            q.save_queue()
        self._install_signal_handlers()
        did_perform_work = False
        self.register_birth()
        self.log.info('PQ worker started, version %s' % VERSION)
        self.state = 'starting'
        try:
            while True:
                if self.stopped:
                    self.log.info('Stopping on request.')
                    break
                self.state = 'idle'
                qnames = self.get_queue_names()
                self.procline('Listening on %s' % ','.join(qnames))
                self.log.info('')
                self.log.info('*** Listening on %s...' % \
                        green(', '.join(qnames)))
                timeout = None if burst else max(1, self.default_worker_ttl)
                try:
                    result = self.dequeue_job_and_maintain_ttl(timeout)
                    if result is None:
                        break
                except StopRequested:
                    self.log.info('Stopping on request.')
                    break

                self.state = 'busy'

                job, queue = result
                self.register_heartbeat(job.timeout or PQ_DEFAULT_JOB_TIMEOUT)
                self.log.info('%s: %s (%s)' % (green(queue.name),
                    blue(job.description), job.id))
                close_connection()
                self.fork_and_perform_job(job)
                did_perform_work = True
        finally:
            if not self.is_horse:
                self.register_death()
        return did_perform_work

    @property
    def _dequeue_loop(self):
        """Helper function to control the loop in tests"""
        if Worker.objects.filter(name=self.name, stop=True):
            raise StopRequested
        elif self._expires_after == None:
            return True
        elif self._expires_after < 0:
            raise StopRequested
        elif self._expires_after >= 0:
            self._expires_after -= 1
            return True
        else:
            return True

    def dequeue_job_and_maintain_ttl(self, timeout):
        while self._dequeue_loop:
            try:
                return PQ.dequeue_any(self.queues, timeout)
            except DequeueTimeout:
                delete_expired = self._clear_expired + timedelta(
                    seconds=self.default_result_ttl)
                if delete_expired < now():
                    self.log.debug('Clearing expired jobs from queues.')
                    for q in self.queues:
                        q.delete_expired_ttl()
                    FlowStore.delete_expired_ttl(q.connection)
                    self._clear_expired = now()


    def fork_and_perform_job(self, job):
        """Spawns a work horse to perform the actual work and passes it a job.
        The worker will wait for the work horse and make sure it executes
        within the given timeout bounds, or will end the work horse with
        SIGALRM.
        """
        child_pid = os.fork()
        if child_pid == 0:
            self.main_work_horse(job)
        else:
            self._horse_pid = child_pid
            self.procline('Forked %d at %d' % (child_pid, time.time()))
            while True:
                try:
                    os.waitpid(child_pid, 0)
                    break
                except OSError as e:
                    # In case we encountered an OSError due to EINTR (which is
                    # caused by a SIGINT or SIGTERM signal during
                    # os.waitpid()), we simply ignore it and enter the next
                    # iteration of the loop, waiting for the child to end.  In
                    # any other case, this is some other unexpected OS error,
                    # which we don't want to catch, so we re-raise those ones.
                    if e.errno != errno.EINTR:
                        raise

    def main_work_horse(self, job):
        """This is the entry point of the newly spawned work horse."""
        # After fork()'ing, always assure we are generating random sequences
        # that are different from the worker.
        random.seed()

        # Always ignore Ctrl+C in the work horse, as it might abort the
        # currently running job.
        # The main worker catches the Ctrl+C and requests graceful shutdown
        # after the current work is done.  When cold shutdown is requested, it
        # kills the current job anyway.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        self._is_horse = True
        self.log = logger

        success = self.perform_job(job)

        # os._exit() is the way to exit from childs after a fork(), in
        # constrast to the regular sys.exit()
        os._exit(int(not success))

    def perform_job(self, job):
        """Performs the actual work of a job.  Will/should only be called
        inside the work horse's process.
        """
        self.procline('Processing %s from %s since %s' % (
            job.func_name,
            job.origin, time.time()))

               # do it this way to avoid the extra sql call through job
        for q in self.queues:
            if q.name == job.queue_id:
                break
        try:
            with death_penalty_after(job.timeout or PQ_DEFAULT_JOB_TIMEOUT):
                rv = job.perform()

            # Pickle the result in the same try-except block since we need to
            # use the same exc handling when pickling fails
            job.result = rv
            job.status = Job.FINISHED
            job.ended_at = now()
            job.result_ttl = job.get_ttl(self.default_result_ttl)
            if job.result_ttl > 0:
                ttl = timedelta(seconds=job.result_ttl)
                job.expired_at = job.ended_at + ttl
            if job.result_ttl != 0:
                job.save()
            else:
                job.delete()

        except:
            job.status = Job.FAILED
            job.save()
            if job.flow_id:
                Flow.handle_failed(job, q)
            self.handle_exception(job, *sys.exc_info())
            return False

        if q.serial:
            q.release_lock()

        if rv is None:
            self.log.info('Job OK')
        else:
            # the six u doesnt seem compatible
            # with converting an integer
            try:
                msg = unicode(rv)
            except NameError:
                msg = str(rv)
            self.log.info('Job OK, result = %s' % (yellow(msg),))
        if job.flow_id:
            Flow.handle_result(job, q)
        if job.result_ttl == 0:
            self.log.info('Result discarded immediately.')
        elif job.result_ttl > 0:
            self.log.info('Result is kept for %d seconds.' % job.result_ttl)
        else:
            self.log.warning('Result will never expire, clean up result key manually.')

        return True


    def handle_exception(self, job, *exc_info):
        """Walks the exception handler stack to delegate exception handling."""
        exc_string = ''.join(
                traceback.format_exception_only(*exc_info[:2]) +
                traceback.format_exception(*exc_info))
        self.log.error(exc_string)

        for handler in reversed(self._exc_handlers):
            self.log.debug('Invoking exception handler %s' % (handler,))
            fallthrough = handler(job, *exc_info)

            # Only handlers with explicit return values should disable further
            # exc handling, so interpret a None return value as True.
            if fallthrough is None:
                fallthrough = True

            if not fallthrough:
                break

    def move_to_failed_queue(self, job, *exc_info):
        """Default exception handler: move the job to the failed queue."""
        exc_string = ''.join(traceback.format_exception(*exc_info))
        self.log.warning('Moving job to %s queue.' % self.failed_queue.name)
        self.failed_queue.quarantine(job, exc_info=exc_string)

    def push_exc_handler(self, handler_func):
        """Pushes an exception handler onto the exc handler stack."""
        self._exc_handlers.append(handler_func)

    def pop_exc_handler(self):
        """Pops the latest exception handler off of the exc handler stack."""
        return self._exc_handlers.pop()

    def save(self, *args, **kwargs):
        timeout = kwargs.pop('timeout', PQ_DEFAULT_JOB_TIMEOUT)
        self.heartbeat = now() + timedelta(seconds=timeout+PQ_DEFAULT_WORKER_TTL)
        if self.stop:
            for q in self.queue_names.split(','):
                PQ.objects.get(name=q).notify('stop')
        super(Worker, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = fixtures
"""
This file contains all jobs that are used in tests.  Each of these test
fixtures has a slighty different characteristics.
"""
import time
from pq.decorators import job


def say_hello(name=None):
    """A job with a single argument and a return value."""
    if name is None:
        name = 'Stranger'
    return 'Hi there, %s!' % (name,)


def do_nothing():
    """The best job in the world."""
    pass


def div_by_zero(x):
    """Prepare for a division-by-zero exception."""
    return x / 0


def some_calculation(x, y, z=1):
    """Some arbitrary calculation with three numbers.  Choose z smartly if you
    want a division by zero exception.
    """
    return x * y / z


def create_file(path):
    """Creates a file at the given path.  Actually, leaves evidence that the
    job ran."""
    with open(path, 'w') as f:
        f.write('Just a sentinel.')


def create_file_after_timeout(path, timeout):
    time.sleep(timeout)
    create_file(path)


#def access_self():
#    job = get_current_job()
#    return job.id


class Calculator(object):
    """Test instance methods."""
    def __init__(self, denominator):
        self.denominator = denominator

    def calculate(self, x, y):
        return x * y / self.denominator


@job(queue='default')
def decorated_job(x, y):
    return x + y


def long_running_job():
    time.sleep(10)


########NEW FILE########
__FILENAME__ = settings
import os
try:
    from psycopg2cffi import compat
    compat.register()
except ImportError:
    pass

DEBUG=True
TEMPLATE=DEBUG
USE_TZ = True
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
SOUTH_TESTS_MIGRATE = False
PQ_QUEUE_CACHE = False # switch off for tests

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'django-pq',
        'USER': 'django-pq',
        'PASSWORD': 'django-pq',
        'HOST': '127.0.0.1',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': 5432,
        'OPTIONS': {'autocommit': True}
    },

}
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'pq',
)
if os.getenv('SOUTH'):
    INSTALLED_APPS += ('south', )

ROOT_URLCONF='test_pq.urls'
SECRET_KEY = '1234'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '[%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console':{
            'level':'DEBUG',
            'class':"logging.StreamHandler",
            'formatter': 'standard'
        },
    },
    'loggers': {
        'pq': {
            'handlers': ['console'],
            'level': os.getenv('LOGGING_LEVEL', 'CRITICAL'),
            'propagate': True
        },
    }
}

########NEW FILE########
__FILENAME__ = test_admin
from datetime import datetime
from django.test import TestCase, TransactionTestCase
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.contrib.auth.models import User
from nose2.tools import params

from pq.job import (Job, FailedJob, DequeuedJob,
                     QueuedJob, ScheduledJob)
from pq.worker import Worker
from pq import Queue
from pq.queue import FailedQueue
from pq.admin import requeue_failed_jobs

from .fixtures import say_hello, div_by_zero

class TestJobAdmin(TransactionTestCase):
    def setUp(self):
        password = 'test'
        user = User.objects.create_superuser('test', 'test@test.com', password)
        self.client.login(username = user.username, password = password)
        self.q = Queue()
        self.q.enqueue_call(say_hello, args=('you',))
        self.q.enqueue_call(div_by_zero, args=(1,))
        self.q.schedule(datetime(2099,1,1), say_hello, 'later')
        w = Worker.create(self.q)
        w.work(burst=True)
        self.q.enqueue_call(say_hello, args=('me',))
        

    @params(
        ("failedjob", FailedJob),
        ("queuedjob", QueuedJob),
        ("dequeuedjob", DequeuedJob),
        ("scheduledjob", ScheduledJob))
    def test_changelist(self, modelname, Model):
        url = reverse("admin:pq_%s_changelist" % modelname)
        response = self.client.get(url, follow = True)
        self.failUnlessEqual(response.status_code, 200,
                     "%s != %s -> %s, url: %s" % (response.status_code, 200, repr(Model), url))

class TestRequeueAdminAction(TransactionTestCase):
    def setUp(self):
        self.q = Queue()
        self.q.enqueue_call(div_by_zero, args=(1,))
        w = Worker.create(self.q)
        w.work(burst=True)

    def test_requeue_admin_action(self):
        self.assertEqual(0, len(Job.objects.filter(queue_id='default')))
        requeue_failed_jobs(None, None, Job.objects.filter(queue_id='failed'))
        self.assertEqual(0, len(Job.objects.filter(queue_id='failed')))

        self.assertEqual('test_pq.fixtures.div_by_zero', Job.objects.get(queue_id='default').func_name)

########NEW FILE########
__FILENAME__ = test_commands
from dateutil.relativedelta import relativedelta
from django.test import TransactionTestCase
from django.core.management import call_command

from pq import Queue, SerialQueue
from pq.worker import Worker
from pq.queue import Queue as PQ
from pq.job import Job


class TestPQWorker(TransactionTestCase):
    reset_sequences = True
    def setUp(self):
        self.q = Queue()
        self.q.save_queue()

    def test_pq_worker(self):
        call_command('pqworker', 'default', burst=True)

    def test_pq_worker_all_queues(self):
        call_command('pqworker', burst=True)


class TestPQWorkerSerial(TransactionTestCase):
    reset_sequences = True
    def setUp(self):
        self.q = Queue()
        self.q.save_queue()
        self.sq = SerialQueue()
        self.sq.save_queue()

    def test_pq_worker_serial(self):
        call_command('pqworker', 'serial', 'default', burst=True)


class TestPQSchedule(TransactionTestCase):
    reset_sequences = True

    def test_pqschedule(self):
        call_command('pqschedule', '2099-01-01', 'test_pq.fixtures.do_nothing', 
            mo=0, tu=1, we=2, th=3, fr=4, sa=5, su=6,
            serial=True, queue='blah', repeat=-1, interval=60, 
            between='2-4', timeout=300)

        j = Job.objects.all()[0]
        self.assertEqual(j.origin, 'blah')
        q = PQ.objects.get(name=j.origin)
        self.assertTrue(q.serial)
        self.assertTrue(q.scheduled)
        self.assertEqual(j.weekdays, [0,1,2,3,4,5,6])
        self.assertEqual(j.repeat, -1)
        self.assertEqual(j.interval, relativedelta(minutes=1))
        self.assertEqual(j.between, '2-4')
        self.assertEqual(j.timeout, 300)


class TestPQEnqueue(TransactionTestCase):
    reset_sequences = True

    def test_pqenqueue_sync(self):
        call_command('pqenqueue', 'test_pq.fixtures.do_nothing', 
            serial=True, queue='blah', timeout=300, sync=True)
        self.assertFalse(Job.objects.all())

    def test_pqenqueue(self):
        call_command('pqenqueue', 'test_pq.fixtures.do_nothing', 
            serial=True, queue='blah', timeout=300)
        j = Job.objects.all()[0]
        self.assertEqual(j.origin, 'blah')
        q = PQ.objects.get(name=j.origin)
        self.assertTrue(q.serial)
        self.assertFalse(q.scheduled)
        self.assertEqual(j.timeout, 300)
        self.assertEqual(j.status, Job.QUEUED)






########NEW FILE########
__FILENAME__ = test_decorators
from django.test import TransactionTestCase


from pq.decorators import job
from pq.job import Job
from pq.worker import PQ_DEFAULT_RESULT_TTL

from .fixtures import decorated_job

class TestDecorator(TransactionTestCase):

    def setUp(self):
        pass

    def test_decorator_preserves_functionality(self):
        """Ensure that a decorated function's functionality is still preserved.
        """
        self.assertEqual(decorated_job(1, 2), 3)

    def test_decorator_adds_delay_attr(self):
        """Ensure that decorator adds a delay attribute to function that returns
        a Job instance when called.
        """
        self.assertTrue(hasattr(decorated_job, 'delay'))
        result = decorated_job.delay(1, 2)
        self.assertTrue(isinstance(result, Job))
        # Ensure that job returns the right result when performed
        self.assertEqual(result.perform(), 3)

    def test_decorator_accepts_queue_name_as_argument(self):
        """Ensure that passing in queue name to the decorator puts the job in
        the right queue.
        """
        @job(queue='queue_name')
        def hello():
            return 'Hi'
        result = hello.delay()
        self.assertEqual(result.origin, 'queue_name')

    def test_decorator_accepts_result_ttl_as_argument(self):
        """Ensure that passing in result_ttl to the decorator sets the
        result_ttl on the job
        """
        #Ensure default
        result = decorated_job.delay(1, 2)
        self.assertEqual(result.result_ttl, PQ_DEFAULT_RESULT_TTL)

        @job('default', result_ttl=10)
        def hello():
            return 'Why hello'
        result = hello.delay()
        self.assertEqual(result.result_ttl, 10)
########NEW FILE########
__FILENAME__ = test_flow
import time
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.timezone import now

from pq.flow import Flow, FlowStore
from pq import Queue, Worker
from pq.queue import FailedQueue
from pq.job import Job
from .fixtures import say_hello, do_nothing, some_calculation

class TestFlowCreate(TestCase):

    def setUp(self):
        self.q = Queue()

    def test_simple_flow(self):
        with Flow(self.q) as f:
            job = f.enqueue(say_hello, 'Bob')
            n_job = f.enqueue(do_nothing)

        # jobs must be performed in sequence
        self.assertLess(job.id, n_job.id)

        # jobs must have uuids
        self.assertIsNotNone(job.uuid)
        self.assertIsNotNone(n_job.uuid)

        # Job 1 must be queued
        self.assertEqual(job.status, job.QUEUED)
        self.assertEqual('default', job.queue_id)

        # Job 2 must not be queued
        self.assertEqual(n_job.status, job.FLOW)
        self.assertIsNone(n_job.queue_id)


class TestFlowPerform(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q)
        with Flow(self.q) as f:
            self.job = f.enqueue(say_hello, 'Bob')
            self.n_job = f.enqueue(do_nothing)

    def test_flow_perform(self):
        self.w.work(burst=True)
        j1 = Job.objects.get(pk=self.job.id)
        j2 = Job.objects.get(pk=self.n_job.id)
        self.assertEqual(Job.FINISHED, j1.status)
        self.assertEqual(Job.FINISHED, j2.status)
        self.assertEqual(self.q.count, 0)


class TestFlowStore(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q)
        with Flow(self.q, name='test') as f:
            self.job = f.enqueue(say_hello, 'Bob')
            self.n_job = f.enqueue(do_nothing)

    def test_flowstore(self):

        fs = FlowStore.objects.get(name='test')
        j1 = Job.objects.get(pk=self.job.id)
        self.assertEqual(len(fs.jobs), 2)

        self.assertEqual(fs.status, FlowStore.QUEUED)
        self.assertEqual(fs.enqueued_at, j1.enqueued_at)
        self.assertIsNone(fs.ended_at)
        self.assertIsNone(fs.expired_at)

        self.w.work(burst=True)

        fs = FlowStore.objects.get(name='test')
        self.assertEqual(fs.status, FlowStore.FINISHED)
        self.assertIsNotNone(fs.ended_at)
        self.assertIsNotNone(fs.expired_at)


class TestFlowStoreExpiredTTL(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q, default_result_ttl=1)
        with Flow(self.q, name='test') as f:
            self.n_job = f.enqueue(do_nothing)

    def test_delete_expired_ttl(self):
        self.w.work(burst=True)
        self.assertIsNotNone(FlowStore.objects.get(name='test'))
        time.sleep(1)
        self.w.work(burst=True)
        with self.assertRaises(FlowStore.DoesNotExist):
            fs = FlowStore.objects.get(name='test')


class TestFlowStoreExpiredTTLOnDequeue(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q, default_result_ttl=1, default_worker_ttl=2.1, expires_after=1)
        with Flow(self.q, name='test') as f:
            self.n_job = f.enqueue(do_nothing)

    def test_delete_expired_ttl_on_dequeue(self):
        self.w.work()
        with self.assertRaises(FlowStore.DoesNotExist):
            fs = FlowStore.objects.get(name='test')


class TestFlowStoreFailed(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker(self.q)
        with Flow(self.q, name='test') as f:
            # enqueue a job to fail
            self.job = f.enqueue(some_calculation, 2, 3, 0)
            self.n_job = f.enqueue(do_nothing)

    def test_flowstore_failed(self):

        fs = FlowStore.objects.get(name='test')
        self.w.work(burst=True)

        fs = FlowStore.objects.get(name='test')
        self.assertEqual(fs.status, FlowStore.FAILED)
        self.assertIsNone(fs.ended_at)
        self.assertIsNone(fs.expired_at)
        n_job = Job.objects.get(pk=self.n_job.id)
        self.assertIsNone(n_job.queue_id)
        self.assertEqual(n_job.status, Job.FLOW)
        job = Job.objects.get(pk=self.job.id)
        # alter the args so it passes
        job.args = (2, 3, 2)
        job.save()
        fq = FailedQueue.create()
        fq.requeue(job.id)

        # do work
        self.w.work(burst=True)

        # should now be finished
        fs = FlowStore.objects.get(name='test')
        self.assertEqual(fs.status, FlowStore.FINISHED)
        job = Job.objects.get(pk=self.job.id)
        n_job = Job.objects.get(pk=self.n_job.id)
        self.assertEqual(job.status, Job.FINISHED)
        self.assertEqual(n_job.status, Job.FINISHED)

########NEW FILE########
__FILENAME__ = test_job
import time
from datetime import timedelta, datetime
from django.test import TestCase, TransactionTestCase
from django.utils.timezone import utc, now
from dateutil.relativedelta import relativedelta
from nose2.tools import params

from pq.job import Job
from pq import Queue
from .fixtures import some_calculation, say_hello, Calculator, do_nothing

class TestJobCreation(TestCase):

    def test_job_create(self):
        job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))

        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.description)
        self.assertIsNone(job.instance)

        # Job data is set...
        self.assertEquals(job.func, some_calculation)
        self.assertEquals(job.args, (3, 4))
        self.assertEquals(job.kwargs, {'z': 2})

        # ...but metadata is not
        self.assertIsNone(job.origin)
        self.assertIsNone(job.enqueued_at)

    def test_create_instance_method_job(self):
        """Creation of jobs for instance methods."""
        c = Calculator(2)
        job = Job.create(func=c.calculate, args=(3, 4))

        # Job data is set
        self.assertEquals(job.func, c.calculate)
        self.assertEquals(job.instance, c)
        self.assertEquals(job.args, (3, 4))

    def test_create_job_from_string_function(self):
        """Creation of jobs using string specifier."""
        job = Job.create(func='test_pq.fixtures.say_hello', args=('World',))

        # Job data is set
        self.assertEquals(job.func, say_hello)
        self.assertIsNone(job.instance)
        self.assertEquals(job.args, ('World',))


class TestScheduledJobCreation(TestCase):

    def test_scheduled_job_create(self):
        """ Test extra kwargs """
        dt = datetime(2013,1,1, tzinfo=utc)
        rd = relativedelta(months=1, days=-1)
        job = Job.create(func=some_calculation,
            args=(3, 4), kwargs=dict(z=2),
            scheduled_for = dt,
            repeat = -1,
            interval = rd,
            between = '0-24'
            )
        job.save()
        job = Job.objects.get(pk=job.id)
        self.assertEqual(rd, job.interval)
        self.assertEqual(dt, job.scheduled_for)



class TestJobSave(TransactionTestCase):

    def setUp(self):
        self.job = Job.create(func=some_calculation, args=(3, 4), kwargs=dict(z=2))

    def test_job_save(self):  # noqa
        """Storing jobs."""
        self.job.save()
        self.assertIsNotNone(self.job.id)


class Test_get_job_or_promise(TransactionTestCase):
    """Test the Job._get_job_or_promise classmethod"""

    def setUp(self):
        self.q = Queue(scheduled=True)
        # simulate the default worker timeout
        self.timeout = 60
        future = now() + timedelta(seconds=self.timeout/2)
        # enqueue a job for 30 seconds time in the future
        self.job = self.q.schedule_call(future, do_nothing)


    def test_get_job_or_promise(self):
        """Test get a promise of a job in the future"""

        job, promise, timeout = Job._get_job_or_promise(
            self.q.connection, self.q, self.timeout)
        self.assertLessEqual(timeout, self.timeout)
        self.assertIsNone(job)
        self.assertEqual(promise, self.q.name)

    def test_get_no_job_no_promise(self):
        """Test get no job and no promise"""

        # job is in the future beyond the current
        # worker timeout
        job, promise, timeout = Job._get_job_or_promise(
            self.q.connection, self.q, 1)
        self.assertEqual(timeout, 1)
        self.assertIsNone(job)
        self.assertIsNone(promise)

    def test_get_earlier_job_no_promise(self):
        """Test get earlier job and no promise"""
        # Job enqueue after the first scheduled job
        # but to be exec ahead of the scheduled job
        now_job = self.q.enqueue(do_nothing)
        job, promise, timeout = Job._get_job_or_promise(
            self.q.connection, self.q, 60)
        # timeout should remain the same
        self.assertEqual(timeout, 60)
        self.assertEqual(now_job.id, job.id)
        self.assertIsNone(promise)


class Test_get_job_no_promise(TransactionTestCase):

    def setUp(self):
        # setup a job in the very near future which
        # should execute
        self.q = Queue(scheduled=True)
        # simulate the default worker timeout
        self.timeout = 60
        future = now() + timedelta(seconds=1)
        # enqueue a job for 1 second time in the future
        self.job = self.q.schedule_call(future, do_nothing)
        time.sleep(1)

    def test_get_job_no_promise(self):
        """Test get job and no promise"""

        job, promise, timeout = Job._get_job_or_promise(
            self.q.connection, self.q, self.timeout)
        self.assertEqual(timeout, self.timeout)
        self.assertEquals(job.id, self.job.id)
        self.assertIsNone(promise)


class TestJobSchedule(TestCase):

    def test_job_get_schedule_options(self):
        """Test the job schedule property"""
        j = Job.create(
            do_nothing,
            interval=600,
            between='2-4',
            repeat=10,
            weekdays=(0,1,2)
            )
        self.assertIsNotNone(j.get_schedule_options())


########NEW FILE########
__FILENAME__ = test_queue
import time
import multiprocessing
from datetime import datetime, timedelta
from django.utils.timezone import utc, now
from django.test import TestCase, TransactionTestCase
from nose2.tools import params

from pq import Queue
from pq.queue import Queue as PQ
from pq.queue import FailedQueue, get_failed_queue
from pq.job import Job
from pq.worker import Worker
from pq.exceptions import DequeueTimeout, InvalidQueueName


from .fixtures import (say_hello, Calculator,
    div_by_zero, some_calculation, do_nothing)



class TestQueueCreation(TestCase):

    def test_default_queue_create(self):
        queue = Queue()
        self.assertEqual(queue.name, 'default')


class TestQueueNameValidation(TestCase):

    def test_validated_name(self):
        with self.assertRaises(InvalidQueueName):
            PQ.validated_name('failed')


class TestQueueInstanceMethods(TransactionTestCase):

    def setUp(self):
        self.q = Queue()

    def test_enqueue(self):  # noqa
        """Enqueueing job onto queues."""

        # say_hello spec holds which queue this is sent to
        job = self.q.enqueue(say_hello, 'Nick', foo='bar')
        self.assertEqual(job.queue, self.q)


class TestEnqueue(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.q.save()
        self.job = Job.create(func=say_hello, args=('Nick',), kwargs=dict(foo='bar'))


    def test_enqueue_sets_metadata(self):
        """Enqueueing job onto queues modifies meta data."""

        # Preconditions
        self.assertIsNone(self.job.origin)
        self.assertIsNone(self.job.enqueued_at)

        # Action
        self.q.enqueue_job(self.job)

        # Postconditions
        self.assertEquals(self.job.origin, self.q.name)
        self.assertIsNotNone(self.job.enqueued_at)


class TestDequeueOnEmpty(TransactionTestCase):

    def setUp(self):
        self.q = Queue()

    def test_pop_job_on_empty(self):
        job = self.q.dequeue()
        self.assertIsNone(job)


class TestDequeue(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.result = self.q.enqueue(say_hello, 'Rick', foo='bar')
        #self.result2 = q.enqueue(c.calculate, 3, 4)
        #self.c = Calculator(2)

    def test_dequeue(self):
        """Dequeueing jobs from queues."""

        # Dequeue a job (not a job ID) off the queue
        self.assertEquals(self.q.count, 1)
        job = self.q.dequeue()
        self.assertEquals(job.id, self.result.id)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, self.q.name)
        self.assertEquals(job.args[0], 'Rick')
        self.assertEquals(job.kwargs['foo'], 'bar')

        # ...and assert the queue count when down
        self.assertEquals(self.q.count, 0)


class TestDequeueInstanceMethods(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.c = Calculator(2)
        self.result = self.q.enqueue(self.c.calculate, 3, 4)


    def test_dequeue_instance_method(self):
        """Dequeueing instance method jobs from queues."""

        job = self.q.dequeue()

        self.assertEquals(job.func.__name__, 'calculate')
        self.assertEquals(job.args, (3, 4))


class TestDequeueAnyEmpty(TransactionTestCase):

    def setUp(self):
        self.fooq = Queue('foo')
        self.barq = Queue('bar')

    def test_dequeue_any_empty(self):
        """Fetching work from any given queue."""

        self.assertEquals(PQ.dequeue_any([self.fooq, self.barq], None), None)


class TestDequeueAnySingle(TransactionTestCase):

    def setUp(self):
        self.fooq = Queue('foo')
        self.barq = Queue('bar')
        # Enqueue a single item
        self.barq.enqueue(say_hello)

    def test_dequeue_any_single(self):

        job, queue = PQ.dequeue_any([self.fooq, self.barq], None)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(queue, self.barq)


class TestDequeueAnyMultiple(TransactionTestCase):

    def setUp(self):
        self.fooq = Queue('foo')
        self.barq = Queue('bar')
        # Enqueue items on both queues
        self.barq.enqueue(say_hello, 'for Bar')
        self.fooq.enqueue(say_hello, 'for Foo')

    def test_dequeue_any_multiple(self):

        job, queue = PQ.dequeue_any([self.fooq, self.barq], None)
        self.assertEquals(queue, self.fooq)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, self.fooq.name)
        self.assertEquals(job.args[0], 'for Foo',
                'Foo should be dequeued first.')

        job, queue = PQ.dequeue_any([self.fooq, self.barq], None)
        self.assertEquals(queue, self.barq)
        self.assertEquals(job.func, say_hello)
        self.assertEquals(job.origin, self.barq.name)
        self.assertEquals(job.args[0], 'for Bar',
                'Bar should be dequeued second.')


class TestGetFailedQueue(TransactionTestCase):
    def test_get_failed_queue(self):
        fq = get_failed_queue()
        self.assertIsInstance(fq, FailedQueue)


class TestFQueueQuarantine(TransactionTestCase):

    def setUp(self):
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.save()
        self.job = job

    def test_quarantine_job(self):
        """Requeueing existing jobs."""

        get_failed_queue().quarantine(self.job, Exception('Some fake error'))  # noqa
        self.assertEqual(sorted(PQ.all()), sorted([get_failed_queue()]))  # noqa
        self.assertEquals(get_failed_queue().count, 1)


class TestFQueueQuarantineTimeout(TransactionTestCase):

    def setUp(self):
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.timeout = 200
        job.save()
        self.job = job
        self.fq = get_failed_queue()

    def test_quarantine_preserves_timeout(self):
        """Quarantine preserves job timeout."""

        self.fq.quarantine(self.job, Exception('Some fake error'))
        self.assertEquals(self.job.timeout, 200)


class TestRequeue(TransactionTestCase):

    def setUp(self):
        Queue('fake').save()
        job = Job.create(func=div_by_zero, args=(1, 2, 3))
        job.origin = 'fake'
        job.save()
        self.job = job
        self.fq = get_failed_queue()

    def test_requeue(self):
        self.fq.requeue(self.job.id)
        self.assertEquals(self.fq.count, 0)
        self.assertEquals(Queue('fake').count, 1)


class TestAsyncFalse(TransactionTestCase):
    def test_async_false(self):
     """Executes a job immediately if async=False."""
     q = Queue(async=False)
     job = q.enqueue(some_calculation, args=(2, 3))
     self.assertEqual(job.result, 6)


class TestEnqueueAsyncFalse(TestCase):
    def setUp(self):
        self.q = Queue()

    def test_enqueue_async_false(self):
        job = self.q.enqueue(some_calculation, args=(2, 3), async=False)
        self.assertEqual(job.result, 6)

    def test_enqueue_call_async_false(self):
        job = self.q.enqueue_call(some_calculation, args=(2, 3), async=False)
        self.assertEqual(job.result, 6)

    def test_schedule_call_async_false(self):
        job = self.q.enqueue_call(some_calculation, args=(2, 3), async=False)
        self.assertEqual(job.result, 6)



class TestDeleteExpiredTTL(TransactionTestCase):
    def setUp(self):
        q = Queue()
        q.enqueue(say_hello, kwargs={'name':'bob'}, result_ttl=1)  # expires
        q.enqueue(say_hello, kwargs={'name':'polly'})  # won't expire in this test lifecycle
        q.enqueue(say_hello, kwargs={'name':'frank'}, result_ttl=-1) # never expires
        w = Worker.create([q])
        w.work(burst=True)
        q.enqueue(say_hello, kwargs={'name':'david'}) # hasn't run yet
        self.q = q

    def test_delete_expired_ttl(self):
        time.sleep(1)
        self.q.delete_expired_ttl()
        jobs = Job.objects.all()[:]
        self.assertEqual(len(jobs), 3)


class TestDequeueTimeout(TransactionTestCase):
    def setUp(self):
        q = Queue()
        self.q = q

    def test_dequeue_timeout(self):
        with self.assertRaises(DequeueTimeout):
            PQ.dequeue_any([self.q], timeout=1)


class TestListen(TransactionTestCase):

    def test_listen(self):
        """Postgresql LISTEN on channel with default connection"""

        conn = PQ.listen('default', ['default'])
        self.assertIsNotNone(conn)

class TestNotify(TransactionTestCase):
    def setUp(self):
        self.q = Queue()

    def test_notify(self):
        """Postgresql NOTIFY on channel with default connection"""
        self.q.notify(1)


class TestListenForJobs(TransactionTestCase):
    def setUp(self):
        self.q = Queue()
        # pre-call this so we don't need to use multi-process
        # otherwise this is called within the classmethod
        PQ.listen('default', ['default'])
        # Fire off a notification of a fake job enqueued
        self.q.notify(1)

    def test_listen_for_jobs(self):
        """Test the first part of the _listen_for_jobs method which polls
        for notifications"""
        queue_name = PQ._listen_for_jobs(['default'], 'default', 1)
        self.assertEqual('default', queue_name)


class TestListenForJobsSelect(TransactionTestCase):

    def setUp(self):
        # We'll have to simulate the notify method since there are issues with
        # sharing database connections with the additional process
        def fake_job():
            import psycopg2
            import psycopg2.extensions
            time.sleep(1)
            conn = psycopg2.connect("dbname=test_django-pq host=localhost user=django-pq")
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

            curs = conn.cursor()
            # fake notifying a job_id 2 has been enqueued on the farq
            curs.execute("SELECT pg_notify(%s, %s);", ('farq', str(2)))

        p = multiprocessing.Process(target=fake_job)
        p.start()


    def test_listen_for_jobs_select(self):
        """Test the 2nd part of the _listen_for_jobs method which
        blocks and waits for postgresql to notify it"""
        queue_name = PQ._listen_for_jobs(['default', 'farq'], 'default', 5)
        self.assertEqual('farq', queue_name)


class TestScheduleJobs(TransactionTestCase):

    def setUp(self):
        self.q = Queue(scheduled=True)
        self.w = Worker.create([self.q])

    def test_shedule_call(self):
        """Schedule to fire now"""
        job = self.q.schedule_call(now(), do_nothing)
        self.w.work(burst=True)
        with self.assertRaises(Job.DoesNotExist) as exc:
            Job.objects.get(queue_id='default', pk=job.id)

    def test_schedule_future_call(self):
        """Schedule to fire in the distant future"""
        job = self.q.schedule_call(datetime(2999,12,1, tzinfo=utc), do_nothing)
        self.w.work(burst=True)
        # check it is still in the queue
        self.assertIsNotNone(Job.objects.get(queue_id='default', pk=job.id))

class TestEnqueueNext(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.job = Job.create(func=some_calculation,
            args=(3, 4),
            kwargs=dict(z=2),
            repeat=1,
            interval=60)
        self.job.save()

    def test_enqueue_next(self):
        """Schedule the next job"""
        job = self.q.enqueue_next(self.job)
        self.assertIsNotNone(job.id)
        self.assertNotEqual(job.id, self.job.id)
        self.assertEqual(job.scheduled_for,
            self.job.scheduled_for + self.job.interval)

    def test_schedule_repeat_infinity(self):
        """Schedule repeats for infinity"""
        self.job.repeat = -1
        job = self.q.enqueue_next(self.job)
        self.assertIsNotNone(job.id)
        self.assertNotEqual(job.id, self.job.id)
        self.assertEqual(job.repeat, self.job.repeat)

    def test_schedule_repeat_until(self):
        """Schedule repeat until datetime"""
        self.job.repeat = datetime(2999,1,1, tzinfo=utc)
        job = self.q.enqueue_next(self.job)
        self.assertIsNotNone(job.id)
        self.assertNotEqual(job.id, self.job.id)
        self.assertEqual(job.repeat, self.job.repeat)

########NEW FILE########
__FILENAME__ = test_queue_serial

import time
from datetime import datetime, timedelta
from django.utils.timezone import utc, now
from django.test import TestCase, TransactionTestCase

from pq import Worker
from pq.queue import SerialQueue, Queue
from pq.exceptions import DequeueTimeout

from .fixtures import do_nothing



class TestSerialQueueCreate(TestCase):

    def test_serial_queue_create(self):
        sq = SerialQueue.create()
        self.assertTrue(sq.serial)


class TestQueueCreationTwoQueueTypes(TestCase):

    def test_default_queue_create_multiple(self):
        queue = Queue.create()
        self.assertEqual(queue.name, 'default')
        queue = SerialQueue.create()
        self.assertEqual(queue.name, 'serial')


class TestSerialQueueMethods(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.sq.save()

    def test_acquire_lock(self):
        """Acquire a lock for an arbitrary time"""
        self.assertTrue(self.sq.acquire_lock(60))


class TestSerialQueueLock(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.sq.save()
        self.sq.acquire_lock(1)

    def test_acquire_already_locked(self):
        self.assertFalse(self.sq.acquire_lock())

    def test_lock_expires(self):
        time.sleep(1)
        self.assertTrue(self.sq.acquire_lock())



class TestDequeueAnySerialJobs(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.job = self.sq.enqueue(do_nothing)

    def test_dequeue_any_serial(self):
        job, queue = Queue.dequeue_any([self.sq], timeout=10)
        self.assertEquals(job.func, do_nothing)


class TestDequeueAnyLockedSerialJobs(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.job = self.sq.enqueue(do_nothing)
        self.sq.acquire_lock(10)

    def test_dequeue_any_serial_lock(self):
        """Test that it raises a DequeueTimeout timeout"""
        with self.assertRaises(DequeueTimeout):
            Queue.dequeue_any([self.sq], timeout=1)


class TestDequeueLockExpiresSerialJobs(TestCase):

    def setUp(self):
        self.sq = SerialQueue.create()
        self.job = self.sq.enqueue(do_nothing)
        self.sq.acquire_lock(1)

    def test_dequeue_any_serial_lock_expired(self):
        """Test that it raises a DequeueTimeout timeout"""
        time.sleep(1)
        job, queue = Queue.dequeue_any([self.sq], timeout=1)
        self.assertEquals(self.job.id, job.id)


class TestQueueCreationConflictIssue2(TransactionTestCase):
    "https://github.com/bretth/django-pq/issues/2"

    def setUp(self):
        self.q = SerialQueue.create()
        self.assertTrue(self.q.serial)

    def test_queue_creation_conflict_issue2(self):
        """Ordinary queue shouldn't ever become a serial queue"""
        q = Queue.create()
        self.assertFalse(q.serial)
        q.enqueue(do_nothing)
        self.q.enqueue(do_nothing)
        w = Worker([q, self.q])
        w.work(burst=True)


########NEW FILE########
__FILENAME__ = test_utils
import unittest
from datetime import datetime

from django.utils.timezone import utc
from nose2.tools import params
from dateutil.relativedelta import weekdays

from pq.utils import get_restricted_datetime
from pq.exceptions import InvalidWeekdays

class TestGetRestrictedDatetime(unittest.TestCase):
    def setUp(self):
        self.dt = datetime(2013, 1, 1, 6, tzinfo=utc)

    @params(
        ('0-24', datetime(2013,1,1,6, tzinfo=utc)),
        ('1.30 - 5.30', datetime(2013,1,2,1,30, tzinfo=utc)),
        ('7:00-8:00', datetime(2013,1,1,7,0, tzinfo=utc)),
        ('7:00/8:00', datetime(2013,1,1,7,0, tzinfo=utc)),
        ('7:00:01-8:00:59', datetime(2013,1,1,7,0, tzinfo=utc)),


    )
    def test_get_restricted_datetime(self, between, result):
        dt = get_restricted_datetime(self.dt, between)
        self.assertEqual(dt, result)

    def test_get_naive_datetime(self):
        dt = datetime(2013,1,1,6)
        rdt = get_restricted_datetime(dt, '0-24')
        self.assertEqual(dt, rdt)


class TestGetRestrictedDatetimeWeekdays(unittest.TestCase):
    def setUp(self):
        self.dt = datetime(2013, 1, 1)

    @params(
        ((1,), datetime(2013,1,1)),
        ((0,), datetime(2013,1,7)),
        ((weekdays[6],weekdays[5]), datetime(2013,1,5)),
    )
    def test_get_restricted_weekdays(self, weekdays, result):
        dt = get_restricted_datetime(self.dt, weekdays=weekdays)
        self.assertEqual(dt, result)

    def test_invalid_weekdays(self):
        with self.assertRaises(InvalidWeekdays):
            dt = get_restricted_datetime(self.dt, weekdays=(7,))



########NEW FILE########
__FILENAME__ = test_worker
import os
import time
import times
from datetime import datetime
from django.test import TransactionTestCase, TestCase
from django.utils.timezone import utc
from nose2.tools import params

from pq import Queue
from pq.queue import get_failed_queue
from pq.worker import Worker
from pq.job import Job

from .fixtures import say_hello, div_by_zero, create_file_after_timeout


class TestWorker(TransactionTestCase):
    def setUp(self):
        self.fooq, self.barq = Queue('foo'), Queue('bar')

    def test_create_worker(self):
        """Worker creation."""

        w = Worker.create([self.fooq, self.barq])
        self.assertEquals(w.queues, [self.fooq, self.barq])


class TestWorkNoJobs(TransactionTestCase):
    def setUp(self):
        self.fooq, self.barq = Queue('foo'), Queue('bar')
        self.w = Worker.create([self.fooq, self.barq])

    def test_work_no_jobs(self):
        self.assertEquals(self.w.work(burst=True), False,
                'Did not expect any work on the queue.')


class TestWorkerWithJobs(TransactionTestCase):
    def setUp(self):
        self.fooq, self.barq = Queue('foo'), Queue('bar')
        self.w = Worker.create([self.fooq, self.barq])
        self.fooq.enqueue(say_hello, name='Frank')

    def test_worker_with_jobs(self):

        self.assertEquals(self.w.work(burst=True), True,
                'Expected at least some work done.')


class TestWorkViaStringArg(TransactionTestCase):
    def setUp(self):
        self.q = Queue('foo')
        self.w = Worker.create([self.q])
        self.job = self.q.enqueue('test_pq.fixtures.say_hello', name='Frank')

    def test_work_via_string_argument(self):
        """Worker processes work fed via string arguments."""

        self.assertEquals(self.w.work(burst=True), True,
                'Expected at least some work done.')
        job = Job.objects.get(id=self.job.id)
        self.assertEquals(job.result, 'Hi there, Frank!')

class TestWorkIsUnreadable(TransactionTestCase):
    def setUp(self):
        self.q = Queue()
        self.q.save()
        self.fq = get_failed_queue()
        self.w = Worker.create([self.q])


    def test_work_is_unreadable(self):
        """Unreadable jobs are put on the failed queue."""

        self.assertEquals(self.fq.count, 0)
        self.assertEquals(self.q.count, 0)

        # NOTE: We have to fake this enqueueing for this test case.
        # What we're simulating here is a call to a function that is not
        # importable from the worker process.
        job = Job.create(func=div_by_zero, args=(3,))
        job.save()
        job.instance = 'nonexisting_job'
        job.queue = self.q
        job.save()


        self.assertEquals(self.q.count, 1)

        # All set, we're going to process it

        self.w.work(burst=True)   # should silently pass
        self.assertEquals(self.q.count, 0)
        self.assertEquals(self.fq.count, 1)


class TestWorkFails(TransactionTestCase):
    def setUp(self):
        self.q = Queue()
        self.fq = get_failed_queue()
        self.w = Worker.create([self.q])
        self.job = self.q.enqueue(div_by_zero)
        self.enqueued_at = self.job.enqueued_at

    def test_work_fails(self):
        """Failing jobs are put on the failed queue."""


        self.w.work(burst=True)  # should silently pass

        # Postconditions
        self.assertEquals(self.q.count, 0)
        self.assertEquals(self.fq.count, 1)

        # Check the job
        job = Job.objects.get(id=self.job.id)
        self.assertEquals(job.origin, self.q.name)

        # Should be the original enqueued_at date, not the date of enqueueing
        # to the failed queue
        self.assertEquals(job.enqueued_at, self.enqueued_at)
        self.assertIsNotNone(job.exc_info)  # should contain exc_info


class TestWorkerCustomExcHandling(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.fq = get_failed_queue()
        def black_hole(job, *exc_info):
            # Don't fall through to default behaviour of moving to failed queue
            return False
        self.black_hole = black_hole
        self.job = self.q.enqueue(div_by_zero)



    def test_custom_exc_handling(self):
        """Custom exception handling."""


        w = Worker.create([self.q], exc_handler=self.black_hole)
        w.work(burst=True)  # should silently pass

        # Postconditions
        self.assertEquals(self.q.count, 0)
        self.assertEquals(self.fq.count, 0)

        # Check the job
        job = Job.objects.get(id=self.job.id)
        self.assertEquals(job.status, Job.FAILED)


class TestWorkerTimeouts(TransactionTestCase):

    def setUp(self):
        self.sentinel_file = '/tmp/.rq_sentinel'
        self.q = Queue()
        self.fq = get_failed_queue()
        self.w = Worker.create([self.q])

    def test_timeouts(self):
        """Worker kills jobs after timeout."""

        # Put it on the queue with a timeout value
        jobr = self.q.enqueue(
                create_file_after_timeout,
                args=(self.sentinel_file, 4),
                timeout=1)

        self.assertEquals(os.path.exists(self.sentinel_file), False)
        self.w.work(burst=True)
        self.assertEquals(os.path.exists(self.sentinel_file), False)

        job = Job.objects.get(id=jobr.id)
        self.assertIn('JobTimeoutException', job.exc_info)

    def tearDown(self):
        try:
            os.unlink(self.sentinel_file)
        except OSError as e:
            if e.errno == 2:
                pass


class TestWorkerSetsResultTTL(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker.create([self.q])

    @params((10,10), (-1,-1), (0, None))
    def test_worker_sets_result_ttl(self, ttl, outcome):
        """Ensure that Worker properly sets result_ttl for individual jobs or deletes them."""
        job = self.q.enqueue(say_hello, args=('Frank',), result_ttl=ttl)
        self.w.work(burst=True)
        try:
            rjob = Job.objects.get(id=job.id)
            result_ttl = rjob.result_ttl
        except Job.DoesNotExist:
            result_ttl = None

        self.assertEqual(result_ttl, outcome)


class TestWorkerDeletesExpiredTTL(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker.create([self.q])
        self.job = self.q.enqueue(say_hello, args=('Bob',), result_ttl=1)
        self.w.work(burst=True)

    def test_worker_deletes_expired_ttl(self):
        """Ensure that Worker deletes expired jobs"""
        time.sleep(1)
        self.w.work(burst=True)
        with self.assertRaises(Job.DoesNotExist) as exc:
            rjob = Job.objects.get(id=self.job.id)


class TestWorkerDequeueTimeout(TransactionTestCase):
    """Simple test to ensure the worker finishes"""

    def setUp(self):
        self.q = Queue()
        self.w = Worker.create([self.q],
            expires_after=1,
            default_worker_ttl=1)

    def test_worker_dequeue_timeout(self):
        self.w.work()
        self.assertEqual(self.w._expires_after, -1)


class TestRegisterHeartbeat(TransactionTestCase):

    def setUp(self):
        self.q = Queue()
        self.w = Worker.create([self.q], name='Test')
        self.w.heartbeat = datetime(2010,1,1, tzinfo=utc)

    def test_worker_register_heartbeat(self):
        self.w.register_heartbeat(timeout=0)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', '{{ project_name }}.views.home', name='home'),
    # url(r'^{{ project_name }}/', include('{{ project_name }}.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
########NEW FILE########
