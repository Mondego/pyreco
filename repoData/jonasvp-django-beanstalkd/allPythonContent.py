__FILENAME__ = beanstalk_jobs
"""
Example Beanstalk Job File.
Needs to be called beanstalk_jobs.py and reside inside a registered Django app.
"""
import os
import time

from django_beanstalkd import beanstalk_job


@beanstalk_job
def background_counting(arg):
    """
    Do some incredibly useful counting to the value of arg
    """
    value = int(arg)
    pid = os.getpid()
    print "[%s] Counting from 1 to %d." % (pid, value)
    for i in range(1, value+1):
        print '[%s] %d' % (pid, i)
        time.sleep(1)

########NEW FILE########
__FILENAME__ = beanstalk_example_client
from django.core.management.base import NoArgsCommand
from django_beanstalkd import BeanstalkClient


class Command(NoArgsCommand):
    help = "Execute an example command with the django_beanstalk_jobs interface"
    __doc__ = help

    def handle_noargs(self, **options):
        client = BeanstalkClient()

        print "Asynchronous Beanstalk Call"
        print "-------------------------"
        print "Notice how this app exits, while the workers still work on the tasks."
        for i in range(4):
            client.call(
                'beanstalk_example.background_counting', '5'
            )

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-
import sys

class beanstalk_job(object):
    """
    Decorator marking a function inside some_app/beanstalk_jobs.py as a
    beanstalk job
    """

    def __init__(self, f):
        modname = f.__module__
        self.f = f
        self.__name__ = f.__name__
        self.__module__ = modname

        # determine app name
        parts = f.__module__.split('.')
        if len(parts) > 1:
            self.app = parts[-2]
        else:
            self.app = ''

        # store function in per-app job list (to be picked up by a worker)
        __import__(modname)
        bs_module = sys.modules[modname]
        try:
            if self not in bs_module.beanstalk_job_list:
                bs_module.beanstalk_job_list.append(self)
        except AttributeError:
            bs_module.beanstalk_job_list = [self]

    def __call__(self, arg):
        # call function with argument passed by the client only
        return self.f(arg)

########NEW FILE########
__FILENAME__ = beanstalk_worker
import logging
from optparse import make_option
import os
import sys
import traceback

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django_beanstalkd import connect_beanstalkd


logger = logging.getLogger('django_beanstalkd')
logger.addHandler(logging.StreamHandler())

class Command(NoArgsCommand):
    help = "Start a Beanstalk worker serving all registered Beanstalk jobs"
    __doc__ = help
    option_list = NoArgsCommand.option_list + (
        make_option('-w', '--workers', action='store', dest='worker_count',
                    default='1', help='Number of workers to spawn.'),
        make_option('-l', '--log-level', action='store', dest='log_level',
                    default='info', help='Log level of worker process (one of '
                    '"debug", "info", "warning", "error")'),
    )
    children = [] # list of worker processes
    jobs = {}

    def handle_noargs(self, **options):
        # set log level
        logger.setLevel(getattr(logging, options['log_level'].upper()))

        # find beanstalk job modules
        bs_modules = []
        for app in settings.INSTALLED_APPS:
            try:
                modname = "%s.beanstalk_jobs" % app
                __import__(modname)
                bs_modules.append(sys.modules[modname])
            except ImportError:
                pass
        if not bs_modules:
            logger.error("No beanstalk_jobs modules found!")
            return

        # find all jobs
        jobs = []
        for bs_module in bs_modules:
            try:
                jobs += bs_module.beanstalk_job_list
            except AttributeError:
                pass
        if not jobs:
            logger.error("No beanstalk jobs found!")
            return
        logger.info("Available jobs:")
        for job in jobs:
            # determine right name to register function with
            app = job.app
            jobname = job.__name__
            try:
                func = settings.BEANSTALK_JOB_NAME % {
                    'app': app,
                    'job': jobname,
                }
            except AttributeError:
                func = '%s.%s' % (app, jobname)
            self.jobs[func] = job
            logger.info("* %s" % func)

        # spawn all workers and register all jobs
        try:
            worker_count = int(options['worker_count'])
            assert(worker_count > 0)
        except (ValueError, AssertionError):
            worker_count = 1
        self.spawn_workers(worker_count)

        # start working
        logger.info("Starting to work... (press ^C to exit)")
        try:
            for child in self.children:
                os.waitpid(child, 0)
        except KeyboardInterrupt:
            sys.exit(0)

    def spawn_workers(self, worker_count):
        """
        Spawn as many workers as desired (at least 1).
        Accepts:
        - worker_count, positive int
        """
        # no need for forking if there's only one worker
        if worker_count == 1:
            return self.work()

        logger.info("Spawning %s worker(s)" % worker_count)
        # spawn children and make them work (hello, 19th century!)
        for i in range(worker_count):
            child = os.fork()
            if child:
                self.children.append(child)
                continue
            else:
                self.work()
                break

    def work(self):
        """children only: watch tubes for all jobs, start working"""
        beanstalk = connect_beanstalkd()
        for job in self.jobs.keys():
            beanstalk.watch(job)
        beanstalk.ignore('default')

        try:
            while True:
                job = beanstalk.reserve()
                job_name = job.stats()['tube']
                if job_name in self.jobs:
                    logger.debug("Calling %s with arg: %s" % (job_name, job.body))
                    try:
                        self.jobs[job_name](job.body)
                    except Exception, e:
                        tp, value, tb = sys.exc_info()
                        logger.error('Error while calling "%s" with arg "%s": '
                            '%s' % (
                                job_name,
                                job.body,
                                e,
                            )
                        )
                        logger.debug("%s:%s" % (tp.__name__, value))
                        logger.debug("\n".join(traceback.format_tb(tb)))
                        job.bury()
                    else:
                        job.delete()
                else:
                    job.release()

        except KeyboardInterrupt:
            sys.exit(0)

########NEW FILE########
