__FILENAME__ = decorators
def gearman_job(queue='default', name=None):
    """
    Decorator turning a function inside some_app/gearman_jobs.py into a
    Gearman job.
    """

    class gearman_job_cls(object):

        def __init__(self, f):
            self.f = f
            # set the custom task name
            self.__name__ = name
            # if it's null, set the import name as the task name
            # this also saves one line (no else clause) :)
            if not name:
                self.__name__ = '.'.join(
                    (f.__module__.replace('.gearman_jobs', ''), f.__name__)
                )
                                    
            self.queue = queue

            # Store function in per-app job list (to be picked up by a
            # worker).
            gm_module = __import__(f.__module__)
            try:
                gm_module.gearman_job_list[queue].append(self)
            except KeyError:
                gm_module.gearman_job_list[queue] = [self]
            except AttributeError:
                gm_module.gearman_job_list = {self.queue: [self]}

        def __call__(self, worker, job, *args, **kwargs):
            # Call function with argument passed by the client only.
            job_args = job.data
            return self.f(*job_args["args"], **job_args["kwargs"])

    return gearman_job_cls

########NEW FILE########
__FILENAME__ = gearman_list_tasks
from django.core.management.base import NoArgsCommand
from gearman_worker import Command as Worker

class Command(NoArgsCommand):
    help = "List all available gearman jobs with queues they belong to"
    __doc__ = help

    def handle_noargs(self, **options):
        gm_modules = Worker.get_gearman_enabled_modules()
        if not gm_modules:
            self.stderr.write("No gearman modules found!\n")
            return

        for gm_module in gm_modules:
            try:
                gm_module.gearman_job_list
            except AttributeError:
                continue
            for queue, jobs in gm_module.gearman_job_list.items():
                self.stdout.write("Queue: %s\n" % queue)
                for job in jobs:
                    self.stdout.write("* %s\n" % job.__name__)

########NEW FILE########
__FILENAME__ = gearman_worker
from optparse import make_option
import os
import sys

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django_gearman import GearmanWorker


class Command(NoArgsCommand):
    ALL_QUEUES = '*'
    help = "Start a Gearman worker serving all registered Gearman jobs"
    __doc__ = help
    option_list = NoArgsCommand.option_list + (
        make_option('-w', '--workers', action='store', dest='worker_count',
                    default='1', help='Number of workers to spawn.'),
        make_option('-q', '--queue', action='store', dest='queue',
                    default=ALL_QUEUES, help='Queue to register tasks from'),
    )

    children = [] # List of worker processes

    @staticmethod
    def get_gearman_enabled_modules():
        gm_modules = []
        for app in settings.INSTALLED_APPS:
            try:
                gm_modules.append(__import__("%s.gearman_jobs" % app))
            except ImportError:
                pass
        if not gm_modules:
            return None
        return gm_modules


    def handle_noargs(self, **options):
        queue = options["queue"]
        # find gearman modules
        gm_modules = Command.get_gearman_enabled_modules()
        if not gm_modules:
            self.stderr.write("No gearman modules found!\n")
            return
        # find all jobs
        jobs = []
        for gm_module in gm_modules:
            try:
                gm_module.gearman_job_list
            except AttributeError:
                continue
            if queue == Command.ALL_QUEUES:
                for _jobs in gm_module.gearman_job_list.itervalues():
                    jobs += _jobs
            else:
                jobs += gm_module.gearman_job_list.get(queue, [])
        if not jobs:
            self.stderr.write("No gearman jobs found!\n")
            return
        self.stdout.write("Available jobs:\n")
        for job in jobs:
            # determine right name to register function with
            self.stdout.write("* %s\n" % job.__name__)

        # spawn all workers and register all jobs
        try:
            worker_count = int(options['worker_count'])
            assert(worker_count > 0)
        except (ValueError, AssertionError):
            worker_count = 1
        self.spawn_workers(worker_count, jobs)

        # start working
        self.stdout.write("Starting to work... (press ^C to exit)\n")
        try:
            for child in self.children:
                os.waitpid(child, 0)
        except KeyboardInterrupt:
            sys.exit(0)

    def spawn_workers(self, worker_count, jobs):
        """
        Spawn as many workers as desired (at least 1).

        Accepts:
        - worker_count, positive int
        - jobs: list of gearman jobs
        """
        # no need for forking if there's only one worker
        if worker_count == 1:
            return self.work(jobs)

        self.stdout.write("Spawning %s worker(s)\n" % worker_count)
        # spawn children and make them work (hello, 19th century!)
        for i in range(worker_count):
            child = os.fork()
            if child:
                self.children.append(child)
                continue
            else:
                self.work(jobs)
                break

    def work(self, jobs):
        """Children only: register all jobs, start working."""
        worker = GearmanWorker()
        for job in jobs:
            worker.register_task(job.__name__, job)
        try:
            worker.work()
        except KeyboardInterrupt:
            sys.exit(0)


########NEW FILE########
__FILENAME__ = models
import pickle
from os import getcwd
from zlib import adler32

import gearman

from django.conf import settings


def default_taskname_decorator(task_name):
    return "%s.%s" % (str(adler32(getcwd()) & 0xffffffff), task_name)

task_name_decorator = getattr(settings, 'GEARMAN_JOB_NAME',
                              default_taskname_decorator)


class PickleDataEncoder(gearman.DataEncoder):
    @classmethod
    def encode(cls, encodable_object):
        return pickle.dumps(encodable_object)

    @classmethod
    def decode(cls, decodable_string):
        return pickle.loads(decodable_string)


class DjangoGearmanClient(gearman.GearmanClient):
    """Gearman client, automatically connecting to server."""

    data_encoder = PickleDataEncoder

    def __call__(self, func, arg, uniq=None, **kwargs):
        raise NotImplementedError('Use do_task() or dispatch_background'
                                  '_task() instead')

    def __init__(self, **kwargs):
        """instantiate Gearman client with servers from settings file"""
        return super(DjangoGearmanClient, self).__init__(
                settings.GEARMAN_SERVERS, **kwargs)

    def parse_data(self, arg, args=None, kwargs=None, *arguments, **karguments):
        data = {
            "args": [],
            "kwargs": {}
        }

        # The order is significant:
        # - First, use pythonic *args and/or **kwargs.
        # - If someone provided explicit declaration of args/kwargs, use those
        #   instead.
        if arg:
            data["args"] = [arg]
        elif arguments:
            data["args"] = arguments
        elif args:
            data["args"] = args

        data["kwargs"].update(karguments)
        # We must ensure if kwargs actually exist,
        # Otherwise 'NoneType' is not iterable is thrown
        if kwargs:
            data["kwargs"].update(kwargs)

        return data

    def submit_job(
        self, task, orig_data = None, unique=None, priority=None,
        background=False, wait_until_complete=True, max_retries=0,
        poll_timeout=None, args=None, kwargs=None, *arguments, **karguments):
        """
        Handle *args and **kwargs before passing it on to GearmanClient's
        submit_job function.
        """
        if callable(task_name_decorator):
            task = task_name_decorator(task)

        data = self.parse_data(orig_data, args, kwargs, *arguments, **karguments)

        return super(DjangoGearmanClient, self).submit_job(
            task, data, unique, priority, background, wait_until_complete,
            max_retries, poll_timeout)

    def dispatch_background_task(
        self, func, arg = None, uniq=None, high_priority=False, args=None,
        kwargs=None, *arguments, **karguments):
        """Submit a background task and return its handle."""

        priority = None
        if high_priority:
            priority = gearman.PRIORITY_HIGH

        request = self.submit_job(func, arg, unique=uniq,
            wait_until_complete=False, priority=priority, args=args,
            kwargs=kwargs, *arguments, **karguments)

        return request


class DjangoGearmanWorker(gearman.GearmanWorker):
    """
    Gearman worker, automatically connecting to server and discovering
    available jobs.
    """
    data_encoder = PickleDataEncoder

    def __init__(self, **kwargs):
        """Instantiate Gearman worker with servers from settings file."""
        return super(DjangoGearmanWorker, self).__init__(
                settings.GEARMAN_SERVERS, **kwargs)

    def register_task(self, task_name, task):
        if callable(task_name_decorator):
            task_name = task_name_decorator(task_name)
        return super(DjangoGearmanWorker, self).register_task(task_name, task)

########NEW FILE########
__FILENAME__ = gearman_jobs
"""
Example Gearman Job File.
Needs to be called gearman_jobs.py and reside inside a registered Django app.
"""
import os
import time

from django_gearman.decorators import gearman_job


@gearman_job
def reverse(input):
    """Reverse a string"""
    print "[%s] Reversing string: %s" % (os.getpid(), input)
    return input[::-1]

@gearman_job
def background_counting(arg=None):
    """
    Do some incredibly useful counting to 5
    Takes no arguments, returns nothing to the caller.
    """
    print "[%s] Counting from 1 to 5." % os.getpid()
    for i in range(1,6):
        print i
        time.sleep(1)


########NEW FILE########
__FILENAME__ = gearman_example_client
from django.core.management.base import NoArgsCommand
from django_gearman import GearmanClient, Task


class Command(NoArgsCommand):
    help = "Execute an example command with the django_gearman interface"
    __doc__ = help

    def handle_noargs(self, **options):
        client = GearmanClient()

        print "Synchronous Gearman Call"
        print "------------------------"
        sentence = "The quick brown fox jumps over the lazy dog."
        print "Reversing example sentence: '%s'" % sentence
        # call "reverse" job defined in gearman_example app (i.e., this app)
        res = client.do_task(Task("gearman_example.reverse", sentence))
        print "Result: '%s'" % res
        print

        print "Asynchronous Gearman Call"
        print "-------------------------"
        print "Notice how this app exits, while the workers still work on the tasks."
        for i in range(4):
            client.dispatch_background_task(
                'gearman_example.background_counting', None
            )


########NEW FILE########
