__FILENAME__ = norc_control
#!/usr/bin/env python

"""A command-line tool to control various functions of Norc.

Presently, this means sending requests to Schedulers and Executors.

"""

import sys
import time
from optparse import OptionParser

from norc.core import controls
from norc.core.constants import Status, Request
from norc.core.models import Executor, Scheduler
from norc.norc_utils.django_extras import update_obj, MultiQuerySet

EXECUTOR_KEYWORDS = ["e", "executor"]
SCHEDULER_KEYWORDS = ["s", "scheduler"]
HOST_KEYWORDS = ["h", "host"]

REQ_TO_STAT = {
    Request.STOP: Status.ENDED,
    Request.KILL: Status.KILLED,
    Request.PAUSE: Status.PAUSED,
    Request.RESUME: Status.RUNNING,
}

def _wait(ds, req):
    print "Waiting for request(s) to take effect..."
    status = REQ_TO_STAT.get(req)
    if status:
        fin = lambda: all(map(lambda d: update_obj(d).status == status, ds))
    else:
        fin = lambda: all(map(lambda d: update_obj(d).request == None, ds))
    while not fin():
        time.sleep(0.5)

def main():
    usage = "norc_control [executor | scheduler | host] <id | host> " + \
        "--[stop | kill | pause | resume | reload | handle] [--wait]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-s", "--stop", action="store_true", default=False,
        help="Send a stop request.")
    parser.add_option("-k", "--kill", action="store_true", default=False,
        help="Send a kill request.")
    parser.add_option("-p", "--pause", action="store_true", default=False,
        help="Send a pause request.")
    parser.add_option("-u", "--resume", action="store_true", default=False,
        help="Send an resume request.")
    parser.add_option("-r", "--reload", action="store_true", default=False,
        help="Send an reload request to a Scheduler.")
    parser.add_option("--handle", action="store_true", default=False,
        help="Change the object's status to HANDLED.")
    parser.add_option("-f", "--force", action="store_true", default=False,
        help="Force the request to be made..")
    parser.add_option("-w", "--wait", action="store_true", default=False,
        help="Wait until the request has been responded to.")
    
    options, args = parser.parse_args()
    
    if len(args) != 2:
        bad_args("Invalid number of arguments.")
    
    
    requests = filter(lambda a: getattr(options, a.lower()),
        Request.NAMES.values())
    if  len(requests) + (1 if options.handle else 0) != 1:
        bad_args("Must request exactly one action.")
    if not options.handle:
        request = requests[0]
        req = getattr(Request, request)
    
    cls = None
    if args[0] in EXECUTOR_KEYWORDS:
        cls = Executor
    elif args[0] in SCHEDULER_KEYWORDS:
        cls = Scheduler
    elif args[0] in HOST_KEYWORDS:
        if options.handle:
            bad_args("Can't perform handle operation on multiple daemons.")
        daemons = MultiQuerySet(Executor, Scheduler).objects.all()
        daemons = daemons.filter(host=args[1]).status_in("active")
        if not options.force:
            daemons = daemons.filter(request=None)
        for d in daemons:
            if req in d.VALID_REQUESTS:
                d.make_request(req)
                print "%s was sent a %s request." % (d, request)
        if options.wait:
            _wait(daemons, req)
    else:
        bad_args("Invalid keyword '%s'." % args[0])
    
    if cls:
        name = cls.__name__
        try:
            obj_id = int(args[1])
        except ValueError:
            bad_args("Invalid id '%s'; must be an integer." % args[1])
        try:
            d = cls.objects.get(id=obj_id)
        except cls.DoesNotExist:
            print "Could not find a(n) %s with id=%s" % (name, obj_id)
        else:
            if options.handle:
                if controls.handle(d):
                    print "The error state of %s was marked as handled." % d
                else:
                    print "%s isn't in an error state." % d
            elif Status.is_final(d.status) and not options.force:
                print "%s is already in a final state." % d
            elif d.request == None or options.force:
                d.make_request(req)
                print "%s was sent a %s request." % (d, request)
                if options.wait:
                    _wait([d], req)
            else:
                print "%s already has request %s." % \
                    (d, Request.name(d.request))
    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = norc_executor
#!/usr/bin/env python

"""A command-line script to run a Norc executor."""

import sys
from optparse import OptionParser

from norc.core.models import Executor, Queue, DBQueue
from norc.norc_utils.log import make_log

def main():
    usage = "norc_executor <queue_name> -c <n> [-e] [-d]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-c", "--concurrent", type='int',
        help="How many instances can be run concurrently.")
    parser.add_option("-q", "--create_queue", action="store_true",
        default=False, help="Force creation of a DBQueue with this name.")
    parser.add_option("-e", "--echo", action="store_true", default=False,
        help="Echo log messages to stdout.")
    parser.add_option("-d", "--debug", action="store_true", default=False,
        help="Enable debug messages.")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        bad_args("A single queue name is required.")
    
    if options.concurrent is None:
        bad_args("You must give a maximum number of concurrent subprocesses.")
    
    queue = Queue.get(args[0])
    if not queue:
        if options.create_queue:
            queue = DBQueue.objects.create(name=args[0])
        else:
            bad_args("Invalid queue name '%s'." % args[0])
    
    executor = Executor.objects.create(queue=queue, concurrent=options.concurrent)
    executor.log = make_log(executor.log_path,
        echo=options.echo, debug=options.debug)
    executor.start()
    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = norc_log_viewer
#!/usr/bin/env python

"""A command-line script to retrieve a Norc log file."""

import sys, os
from optparse import OptionParser

from django.contrib.contenttypes.models import ContentType

from norc import settings
from norc.core.models import Executor, Queue
from norc.norc_utils.log import make_log

if settings.BACKUP_SYSTEM == "AmazonS3":
    from norc.norc_utils.aws import get_s3_key

def main():
    usage = "norc_log_viewer <class_name> <id> [-r]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-r", "--remote", action="store_true", default=False,
        help="Forces log retrieval from the remote source.")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        bad_args("A class name and id are required.")
    
    model_name = args[0].lower()  
    try:
        if args[1].startswith("#"):
            args[1] = args[1][1:]
        obj_id = int(args[1])
    except ValueError:
        bad_args("Invalid id '%s', must be an integer." % args[1])
    
    ctypes = ContentType.objects.filter(model=model_name)
    ct_count = ctypes.count()
    
    if ct_count == 0:
        print "No model found matching '%s'." % model_name
        return
    
    i = 0
    if ct_count > 1:
        i = -1
        while i < 0 or i >= ct_count:
            print 
            for i, ct in enumerate(ctypes):
                print "%s: %s.%s" % \
                    (i, ct.app_label, ct.model_class().__name__)
            try:
                i = int(raw_input(
                    "Please enter the number of the correct model: "))
            except ValueError:
                pass
    
    Model = ctypes[i].model_class()
    try:
        obj = Model.objects.get(id=obj_id)
    except Model.DoesNotExist:
        print "No %s found with id=%s." % (Model.__name__, obj_id)
        return
    
    if hasattr(obj, "log_path"):
        local_path = os.path.join(settings.NORC_LOG_DIR, obj.log_path)
        log = None
        if os.path.isfile(local_path) and not options.remote:
            f = open(local_path, 'r')
            log = ''.join(f.readlines())
            f.close()
        elif settings.BACKUP_SYSTEM == "AmazonS3":
            print "Retreiving log from S3..."
            try:
                key = 'norc_logs/' + obj.log_path
                log = get_s3_key(key)
            except:
                log = 'Could not retrieve log file from local machine or S3.'
        print log,
    else:
        print "Object does not support a log file."
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = norc_reporter
#!/usr/bin/env python

"""A command-line script to run a Norc scheduler."""

import sys, time
from optparse import OptionParser

from norc.core import reports
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.formatting import untitle, pprint_table

def main():
    usage = "norc_reporter [--executors] [--schedulers] [--queues]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-e", "--executors", action="store_true",
        help="Report on executors.")
    parser.add_option("-s", "--schedulers", action="store_true",
        help="Report on schedulers.")
    parser.add_option("-q", "--queues", action="store_true",
        help="Report on queues.")
    parser.add_option("-t", "--timeframe",
        help="Filter to only things in this timeframe (e.g. '10m').")
    parser.add_option("-n", "--number", default=20, type="int",
        help="The number of items to display.")
    
    (options, args) = parser.parse_args()
    since = parse_since(options.timeframe)
    
    if not any([options.executors, options.schedulers, options.queues]):
        options.executors = True
    
    print time.strftime('[%Y/%m/%d %H:%M:%S]'),
    if since:
        print 'from the last %s.' % options.timeframe,
    print ''
    
    def print_report(report):
        data_objects = report.get_all()
        data_objects = report.since_filter(data_objects, since)
        data_objects = report.order_by(data_objects, None)
        data_list = reports.generate(data_objects, report, dict(since=since))
        if options.number > 0:
            data_list = data_list[:options.number]
        if len(data_list) > 0:
            table = [report.headers] + [[str(o[untitle(h)])
                for h in report.headers] for o in data_list]
            pprint_table(sys.stdout, table)
        else:
            print 'None found.'

    if options.executors:
        print '\n## Executors ##'
        print_report(reports.executors)
    if options.schedulers:
        print '\n## Schedulers ##'
        print_report(reports.schedulers)
    if options.queues:
        print '\n## Queues ##'
        print_report(reports.queues)
        
        
        

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = norc_scheduler
#!/usr/bin/env python

"""A command-line script to run a Norc scheduler."""

import sys
from optparse import OptionParser

from norc.core.models import Scheduler
from norc.norc_utils.log import make_log

def main():
    usage = "norc_scheduler [-e] [-d]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-e", "--echo", action="store_true", default=False,
        help="Echo log messages to stdout.")
    parser.add_option("-d", "--debug", action="store_true", default=False,
        help="Enable debug messages.")
    
    (options, args) = parser.parse_args()
    
    if Scheduler.objects.alive().count() > 0:
        print "Cannot run more than one scheduler at a time."
        return
    
    scheduler = Scheduler.objects.create()
    scheduler.log = make_log(scheduler.log_path,
        echo=options.echo, debug=options.debug)
    scheduler.start()
    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sqsctl
#!/usr/bin/env python

import sys, datetime, pickle, time
from optparse import OptionParser

from boto.sqs.connection import SQSConnection
from boto.exception import SQSError

from norc import settings
from norc.norc_utils import formatting
from norc.norc_utils import log
log = log.Log(settings.LOGGING_DEBUG)


def get_name(q):
    name = q.url.split('/')[-1]
    return name

def delete_queue(c, queue_name):
    q = c.get_queue(queue_name)
    if q == None:
        raise Exception("No queue exists by name '%s'" % (queue_name))
    log.info("Deleting q '%s' (had %s messages)" % (queue_name, q.count()))
    q.delete()

def clear_queue(c, queue_name, use_api):
    q = c.get_queue(queue_name)
    if q == None:
        raise Exception("No queue exists by name '%s'" % (queue_name))
    if use_api:
        log.info("Clearing q '%s' using method recommended in API (had %s messages)" % (queue_name, q.count()))
        q.clear()
    else:
        # clearing is slow & unreliable for some reason.  Just delete it and recreate it.
        log.info("Clearing q using deletion '%s' (had %s messages)" % (queue_name, q.count()))
        visibility_timeout = q.get_timeout()
        delete_queue(c, queue_name)
        wait = 65
        log.info("Waiting %s seconds before recreating queue" % (wait))
        time.sleep(wait)# amazon forces us to wait 1 minute before creating a queue by the same name
        create_queue(c, queue_name, visibility_timeout=visibility_timeout)

def create_queue(c, queue_name, visibility_timeout=None):
    q = c.get_queue(queue_name)
    if not q == None:
        raise Exception("Queue by name '%s' already exists!" % (queue_name))
    log.info("Creating queue '%s' with visibility timeout %s" % (queue_name, visibility_timeout))
    c.create_queue(queue_name, visibility_timeout)

def rpt_queues(c):
    all_queues = c.get_all_queues()
    print "%s AWS SQS Queue(s) as of %s" % (len(all_queues), datetime.datetime.now())
    sys.stdout.write('\n')
    
    table_data = [['Name', '~ #', 'Timeout'], ['','','']]
    for q in all_queues:
        try:
            row = [get_name(q), q.count(), q.get_timeout()]
            table_data.append(row)
        except SQSError, sqse:
            log.error("Internal SQS error (maybe ignorable):" + str(sqse))
    
    if len(table_data) > 2:
        formatting.pprint_table(sys.stdout, table_data)
    sys.stdout.write('\n')

#
#
#

def main():
    parser = OptionParser("%prog [--create_queue <name> [--visibility_timeout <seconds>]] \
[--clear_queue <name> [--use_api]] [--delete_queue <name>] [--debug]")
    parser.add_option("--create_queue", action="store")
    parser.add_option("--visibility_timeout", action="store", type="int")
    parser.add_option("--delete_queue", action="store")
    parser.add_option("--clear_queue", action="store")
    parser.add_option("--use_api", action="store_true")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    c = SQSConnection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    
    if options.create_queue:
        create_queue(c, options.create_queue, options.visibility_timeout)
    if options.clear_queue:
        clear_queue(c, options.clear_queue, options.use_api)
    if options.delete_queue:
        delete_queue(c, options.delete_queue)
    
    rpt_queues(c)
    
    #for q in c.get_all_queues():
    #    test_read(q)
    

if __name__ == '__main__':
    main()

#

########NEW FILE########
__FILENAME__ = admin

from django.contrib import admin

from norc.core import models

class ExecutorAdmin(admin.ModelAdmin):
    list_display = ['id', 'host', 'pid', 'status', 'request', 
        'heartbeat', 'started', 'ended', 'queue', 'concurrent']

admin.site.register(models.Executor, ExecutorAdmin)

class DBQueueAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'count_']
    
    def count_(self, dbq):
        return dbq.count()
    count_.short_description = "# Enqueued"

admin.site.register(models.DBQueue, DBQueueAdmin)

class DBQueueItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'dbqueue', 'item', 'enqueued']

admin.site.register(models.DBQueueItem, DBQueueItemAdmin)

class QueueGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'count_']
    
    def count_(self, qg):
        return qg.count()
    count_.short_description = "# Enqueued"

admin.site.register(models.QueueGroup, QueueGroupAdmin)

class QueueGroupItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'group', 'queue', 'priority']

admin.site.register(models.QueueGroupItem, QueueGroupItemAdmin)

class JobAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 
        'timeout', 'date_added']

    def timeout_(self, j):
        return j.timeout
    timeout_.short_description = "Timeout (secs)"

admin.site.register(models.Job, JobAdmin)

class CommandTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 
        'command', 'nice',
        'timeout', 'date_added']
    
    def timeout_(self, j):
        return j.timeout
    timeout_.short_description = "Timeout (secs)"

admin.site.register(models.CommandTask, CommandTaskAdmin)

class SchedulerAdmin(admin.ModelAdmin):
    list_display = ['id', 'host', 'heartbeat', 'is_alive']

admin.site.register(models.Scheduler, SchedulerAdmin)

class CronScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'queue', 'repetitions', 
        'remaining', 'scheduler', 'make_up', 'base', 'encoding']

admin.site.register(models.CronSchedule, CronScheduleAdmin)

class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'queue', 'repetitions', 
        'remaining', 'scheduler', 'make_up', 'next', 'period']

admin.site.register(models.Schedule, ScheduleAdmin)


########NEW FILE########
__FILENAME__ = constants

""" Norc-specific constants.

Any constants required for the core execution of Norc
should be defined here if possible.

"""

# The maximum number of tasks an Executor is allowed to run at once.
CONCURRENCY_LIMIT = 4

# How often a scheduler can poll the database for new schedules.
SCHEDULER_PERIOD = 5

# How many new schedules the scheduler can pull from the database at once.
SCHEDULER_LIMIT = 10000

EXECUTOR_PERIOD = 0.5

# A list of all Task implementations.
TASK_MODELS = [] # NOTE: This is dynamically generated by MetaTask.

# A list of all AbstractInstance implementations.
INSTANCE_MODELS = [] # NOTE: This is dynamically generated by MetaInstance.

# How often hearts should beat, in seconds.
HEARTBEAT_PERIOD = 3

# How long a heart can go without beating before being considered failed.
# This has serious implications for how long before an error in the system
# is caught.  If the number is too small, though, a slow database could
# cause failsafes to activate erroneously.
HEARTBEAT_FAILED = HEARTBEAT_PERIOD + 20

# Controls how long an instance's finally method has to run.
FINALLY_TIMEOUT = 30

class MetaConstant(type):
    """Generates the NAMES attribute of the Status class."""
    
    def __new__(cls, name, bases, dct):
        """Magical function to dynamically create NAMES and ALL."""
        NAMES = {}
        ALL = []
        for k, v in dct.iteritems():
            if type(v) == int:
                assert not v in NAMES, "Can't have duplicate values."
                NAMES[v] = k
                ALL.append(v)
        dct['NAMES'] = NAMES
        dct['ALL'] = ALL
        return type.__new__(cls, name, bases, dct)
    
    def name(cls, item):
        return cls.NAMES.get(item)

class Status(object):
    """Class to hold all status constants.
    
    The MetaStatus class automatically generates a NAMES attribute which
    contains the reverse dict for retrieving a status name from its value.
    
    The numbers should probably be moved further apart, but SUCCESS being
    7 and FAILURE being 13 just seems so fitting...
    
    """
    __metaclass__ = MetaConstant
    
    # Transitive states.
    CREATED = 1         # Created but nothing else.
    RUNNING = 2         # Is currently running.
    PAUSED = 3          # Currently paused.
    STOPPING = 4        # In the process of stopping; should become ENDED.
    SUSPENDED = 5       # Errors need addressing before a restart.
    
    # Final states.
    SUCCESS = 7         # Succeeded.
    ENDED = 8           # Ended gracefully.
    KILLED = 9          # Forcefully killed.
    HANDLED = 12        # Was ERROR, but the problem's been handled.
    
    # Failure states.
    FAILURE = 13        # User defined failure (Task returned False).
    ERROR = 14          # There was an error during execution.
    TIMEDOUT = 15       # The execution timed out.
    INTERRUPTED = 16    # Execution was interrupted before completion.
    
    @staticmethod
    def is_final(status):
        """Whether the given status counts as final."""
        return status >= 7
    
    @staticmethod
    def is_failure(status):
        """Whether the given status counts as a failure."""
        return status >= 13
    
    @staticmethod
    def GROUPS(name):
        """Used for accessing groups of Statuses by a string name."""
        return {
            "active": filter(lambda s: s < 7, Status.ALL),
            "running": [Status.RUNNING],
            "succeeded": filter(lambda s: s >= 7 and s < 13, Status.ALL),
            "failed": filter(lambda s: s >= 13, Status.ALL),
            "final": filter(lambda s: s >= 7, Status.ALL),
            "error": filter(lambda s: s >= 13, Status.ALL) +
                [Status.SUSPENDED],
        }.get(name.lower())
    

class Request(object):
    """"""
    
    __metaclass__ = MetaConstant
    
    # Requests to change to a final state.
    STOP = 1
    KILL = 2
    
    # Other features.
    PAUSE = 7
    RESUME = 8
    RELOAD = 9
    
    

########NEW FILE########
__FILENAME__ = controls

"""File to contain functions for controlling parts of Norc."""

from datetime import datetime

from norc.core.constants import Status

def handle(obj):
    if not obj.is_alive():
        obj.status = Status.HANDLED
        if hasattr(obj, "ended") and obj.ended == None:
            obj.ended = datetime.utcnow()
        obj.save()
        return True
    else:
        return False

########NEW FILE########
__FILENAME__ = daemon

import os
import signal
import time
from datetime import datetime, timedelta
from threading import Thread, Event

from django.db.models.query import QuerySet
from django.db.models import Model, CharField, DateTimeField, IntegerField

from norc import settings
from norc.core.constants import (Status, Request,
    HEARTBEAT_PERIOD, HEARTBEAT_FAILED)
from norc.norc_utils.log import make_log
from norc.norc_utils.backup import backup_log
from norc.norc_utils.parsing import parse_since

class AbstractDaemon(Model):
    
    class Meta:
        app_label = "core"
        abstract = True
    
    class QuerySet(QuerySet):
        
        def alive(self):
            """Running executors with a recent heartbeat."""
            cutoff = datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
            return self.status_in("active").filter(
                heartbeat__isnull=False).filter(heartbeat__gt=cutoff)
        
        def since(self, since):
            """Date ended since a certain time, or not ended."""
            if type(since) == str:
                since = parse_since(since)
            return self.exclude(ended__lt=since) if since else self
        
        def status_in(self, statuses):
            """Filter by status group. Takes a string or iterable."""
            if isinstance(statuses, basestring):
                statuses = Status.GROUPS(statuses)
            return self.filter(status__in=statuses) if statuses else self
    
    # The host this daemon ran on.
    host = CharField(default=lambda: os.uname()[1], max_length=128)
    
    # The process ID of the main daemon process.
    pid = IntegerField(default=os.getpid)
    
    # The datetime of the daemon's last heartbeat.  Used in conjunction
    # with the active flag to determine whether a Scheduler is still alive.
    heartbeat = DateTimeField(null=True)
    
    # When this daemon started.
    started = DateTimeField(null=True)
    
    # When this daemon ended.
    ended = DateTimeField(null=True, blank=True)
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        self.flag = Event()
        self.heart = Thread(target=self.heart_run)
        self.heart.daemon = True
        self.heart.flag = Event()
    
    def heart_run(self):
        """Method to be run by the heart thread."""
        while not Status.is_final(self.status):
            start = time.time()
            
            self.heartbeat = datetime.utcnow()
            self.save(safe=True)
            
            # In case the database is slow and saving takes longer
            # than HEARTBEAT_PERIOD to complete.
            wait = HEARTBEAT_PERIOD - (time.time() - start)
            if wait > 0:
                self.heart.flag.wait(wait)
                self.heart.flag.clear()
    
    def start(self):
        """Starts the daemon.  Does initialization then calls run()."""
        
        if self.status != Status.CREATED:
            print "Can't start a %s that's already been run." \
                % type(self).__name__
            return
        
        if not hasattr(self, 'id'):
            self.save()
        if not hasattr(self, 'log'):
            self.log = make_log(self.log_path)
        
        if settings.DEBUG:
            self.log.info("WARNING, DEBUG is True, which means Django " +
                "will gobble memory as it stores all database queries.")
        
        # This try block is needed because the unit tests run daemons
        # in threads, which breaks signals.
        try:
            for signum in (signal.SIGINT, signal.SIGTERM):
                signal.signal(signum, self.signal_handler)
        except ValueError:
            pass
        
        self.log.start_redirect()
        self.log.info("%s initialized; starting..." % self)
        
        self.status = Status.RUNNING
        self.heartbeat = self.started = datetime.utcnow()
        self.save()
        self.heart.start()
        
        try:
            self.run()
        except Exception:
            self.set_status(Status.ERROR)
            self.log.error("An internal error occured!", trace=True)
        else:
            if not Status.is_final(self.status):
                self.set_status(Status.ENDED)
        finally:    
            self.log.info("Shutting down...")
            try:
                self.clean_up()
            except:
                self.log.error("Clean up function failed.", trace=True)
            if not Status.is_final(self.status):
                self.set_status(Status.ERROR)
            self.heart.flag.set()
            self.heart.join()
            self.ended = datetime.utcnow()
            self.save()
            if settings.BACKUP_SYSTEM:
                self.log.info('Backing up log file...')
                try:
                    if backup_log(self.log_path):
                        self.log.info('Completed log backup.')
                    else:
                        self.log.error('Failed to backup log.')
                except:
                    self.log.error('Failed to backup log.', trace=True)
            self.log.info('%s has been shut down successfully.' % self)
            self.log.stop_redirect()
            self.log.close()
    
    def run(self):
        raise NotImplementedError
    
    def clean_up(self):
        pass
    
    def signal_handler(self, signum, frame=None):
        """Handles signal interruption."""
        sig_name = None
        # A reverse lookup to find the signal name.
        for attr in dir(signal):
            if attr.startswith('SIG') and getattr(signal, attr) == signum:
                sig_name = attr
                break
        self.log.info("Signal '%s' received!" % (sig_name or signum))
        if signum == signal.SIGINT:
            self.make_request(Request.STOP)
        elif signum == signal.SIGTERM:
            self.make_request(Request.KILL)
    
    def wait(self, t=1):
        """Waits on the flag.
        
        For whatever reason, when this is done signals are no longer
        handled properly, so we must catch the exceptions explicitly.
        
        """
        self.flag.clear()
        self.flag.wait(t)
    
    def is_alive(self):
        """Whether the Daemon is still alive.
        
        A Daemon is defined as alive if its status is not final and its
        last heartbeat was within the last HEARTBEAT_FAILED seconds.
        
        """
        return not Status.is_final(self.status) \
            and self.heartbeat and self.heartbeat > \
            datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
    
    def set_status(self, status):
        """Sets the status with a log message.  Does not save."""
        self.log.info("Changing state from %s to %s." %
            (Status.name(self.status), Status.name(status)))
        self.status = status
    
    def make_request(self, request):
        """This method is how the request field should always be set."""
        if not request in self.VALID_REQUESTS:
            return False
        if not Status.is_final(self.status):
            self.request = request
            self.save()
            self.flag.set()
            return True
        else:
            return False
    
    def save(self, *args, **kwargs):
        """Overwrites Model.save().
        
        We have to be very careful to never overwrite a request, so
        often the request must be read from the database prior to saving.
        The safe parameter being set to True enables this behavior.
        
        """
        if kwargs.pop('safe', False):
            self.request = type(self).objects.get(id=self.id).request
        return Model.save(self, *args, **kwargs)
    
    def __unicode__(self):
        return u"[%s #%s on %s]" % (type(self).__name__, self.id, self.host)
    
    __repr__ = __unicode__
    

########NEW FILE########
__FILENAME__ = executor

"""The Norc Executor is defined here."""

import os
import signal
import time
from datetime import datetime, timedelta
from threading import Thread
# from multiprocessing import Process
# Alas, 2.5 doesn't have multiprocessing...
from subprocess import Popen, STDOUT
import resource

from django.db.models import (
    IntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericForeignKey)

from norc.core.models.daemon import AbstractDaemon
from norc.core.constants import (Status, Request,
    EXECUTOR_PERIOD, HEARTBEAT_FAILED, INSTANCE_MODELS)
from norc.norc_utils.django_extras import QuerySetManager, MultiQuerySet
from norc.norc_utils.log import make_log
from norc.norc_utils.parallel import ThreadPool
from norc.norc_utils.backup import backup_log
from norc import settings

class Executor(AbstractDaemon):
    """Executors are responsible for the running of instances.
    
    Executors have a single queue that they pull instances from.  There
    can (and in many cases should) be more than one Executor running for
    a single queue.
    
    """
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_executor'
    
    objects = QuerySetManager()
    
    class QuerySet(AbstractDaemon.QuerySet):
        
        def for_queue(self, q):
            """Executors pulling from the given queue."""
            return self.filter(queue_id=q.id,
                queue_type=ContentType.objects.get_for_model(q).id)
    
    @property
    def instances(self):
        """A custom implementation of the Django related manager pattern."""
        return MultiQuerySet(*[i.objects.filter(executor=self.pk)
            for i in INSTANCE_MODELS])
    
    # All the statuses executors can have.  See constants.py.
    VALID_STATUSES = [
        Status.CREATED,
        Status.RUNNING,
        Status.PAUSED,
        Status.STOPPING,
        Status.ENDED,
        Status.ERROR,
        Status.KILLED,
        Status.SUSPENDED,
    ]
    
    VALID_REQUESTS = [
        Request.STOP,
        Request.KILL,
        Request.PAUSE,
        Request.RESUME,
    ]
    
    # The status of this executor.
    status = PositiveSmallIntegerField(default=Status.CREATED,
        choices=[(s, Status.name(s)) for s in VALID_STATUSES])
    
    # A state-change request.
    request = PositiveSmallIntegerField(null=True,
        choices=[(r, Request.name(r)) for r in VALID_REQUESTS])
    
    # The queue this executor draws task instances from.
    queue_type = ForeignKey(ContentType)
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey('queue_type', 'queue_id')
    
    # The number of things that can be run concurrently.
    concurrent = IntegerField()
    
    @property
    def alive(self):
        return self.status == Status.RUNNING and self.heartbeat > \
            datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
    
    def __init__(self, *args, **kwargs):
        AbstractDaemon.__init__(self, *args, **kwargs)
        self.processes = {}
    
    def run(self):
        """Core executor function."""
        if settings.BACKUP_SYSTEM:
            self.pool = ThreadPool(self.concurrent + 1)
        self.log.info("%s is now running on host %s." % (self, self.host))
        
        if self.log.debug_on:
            self.resource_reporter = Thread(target=self.report_resources)
            self.resource_reporter.daemon = True
            self.resource_reporter.start()
        
        # Main loop.
        while not Status.is_final(self.status):
            if self.request:
                self.handle_request()
            
            if self.status == Status.RUNNING:
                while len(self.processes) < self.concurrent:
                    # self.log.debug("Popping instance...")
                    instance = self.queue.pop()
                    if instance:
                        # self.log.debug("Popped %s" % instance)
                        self.start_instance(instance)
                    else:
                        # self.log.debug("No instance in queue.")
                        break
            
            elif self.status == Status.STOPPING and len(self.processes) == 0:
                self.set_status(Status.ENDED)
                self.save(safe=True)
            
            # Clean up completed tasks before iterating.
            for pid, p in self.processes.items()[:]:
                p.poll()
                self.log.debug(
                    "Checking pid %s: return code %s." % (pid, p.returncode))
                if not p.returncode == None:
                    i = type(p.instance).objects.get(pk=p.instance.pk)
                    if i.status == Status.CREATED:
                        self.log.info(("%s fail to initialize properly; " +
                            "entering suspension to avoid more errors.") % i)
                        self.set_status(Status.SUSPENDED)
                        self.save()
                    if not Status.is_final(i.status):
                        self.log.info(("%s ended with invalid " +
                            "status %s, changing to ERROR.") %
                            (i, Status.name(i.status)))
                        i.status = Status.ERROR
                        i.save()
                    self.log.info("%s ended with status %s." %
                        (i, Status.name(i.status)))
                    del self.processes[pid]
                    if settings.BACKUP_SYSTEM:
                        self.pool.queueTask(self.backup_instance_log, [i])
            
            if not Status.is_final(self.status):
                self.wait(EXECUTOR_PERIOD)
                self.request = Executor.objects.get(pk=self.pk).request
    
    def clean_up(self):
        if settings.BACKUP_SYSTEM:
            self.pool.joinAll()
    
    def report_resources(self):
        while not Status.is_final(self.status):
            time.sleep(10)
            rself = resource.getrusage(resource.RUSAGE_SELF)
            self.log.debug(rself)
            rchildren = resource.getrusage(resource.RUSAGE_CHILDREN)
            self.log.debug(rchildren)
    
    def start_instance(self, instance):
        """Starts a given instance in a new process."""
        instance.executor = self
        instance.save()
        self.log.info("Starting %s..." % instance)
        # p = Process(target=self.execute, args=[instance.start])
        # p.start()
        ct = ContentType.objects.get_for_model(instance)
        f = make_log(instance.log_path).file
        p = Popen('norc_taskrunner --ct_pk %s --target_pk %s' %
            (ct.pk, instance.pk), stdout=f, stderr=STDOUT, shell=True)
        p.instance = instance
        self.processes[p.pid] = p
    
    # This should be used in 2.6, but with subprocess it's not possible.
    # def execute(self, func):
    #     """Calls a function, then sets the flag after its execution."""
    #     try:
    #         func()
    #     finally:
    #         self.flag.set()
    
    def handle_request(self):
        """Called when a request is found."""
        
        # Clear request immediately.
        request = self.request
        self.request = None
        self.save()
        
        self.log.info("Request received: %s" % Request.name(request))
        
        if request == Request.PAUSE:
            self.set_status(Status.PAUSED)
        
        elif request == Request.RESUME:
            if self.status not in (Status.PAUSED, Status.SUSPENDED):
                self.log.info("Must be paused or suspended to resume; " + 
                    "clearing request.")
            else:
                self.set_status(Status.RUNNING)
        
        elif request == Request.STOP:
            self.set_status(Status.STOPPING)
        
        elif request == Request.KILL:
            # for p in self.processes.values():
            #     p.terminate()
            for pid, p in self.processes.iteritems():
                self.log.info("Killing process for %s." % p.instance)
                os.kill(pid, signal.SIGTERM)
            self.set_status(Status.KILLED)
    
    def backup_instance_log(self, instance):
        self.log.info("Attempting upload of log for %s..." % instance)
        if backup_log(instance.log_path):
            self.log.info("Completed upload of log for %s." % instance)
        else:
            self.log.info("Failed to upload log for %s." % instance)
    
    @property
    def log_path(self):
        return 'executors/executor-%s' % self.id
    

########NEW FILE########
__FILENAME__ = extras

from django.db.models import Model, CharField

class Revision(Model):
    """Represents a code revision."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_revision'
    
    info = CharField(max_length=64, unique=True)
    
    @staticmethod
    def create(info):
        return Revision.objects.create(info=info)
    
    def __str__(self):
        return "[Revision %s]" % self.info
    

########NEW FILE########
__FILENAME__ = job

import os
import time

from django.db.models import (Model, query,
    BooleanField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status
from norc.core.models.task import Task, AbstractInstance, Instance
from norc.norc_utils.django_extras import queryset_exists, QuerySetManager

class Job(Task):
    """A Task composed of running several other Tasks."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_job'
    
    def start(self, instance):
        """Modified to give run() the instance object."""
        return self.run(instance)
    
    def run(self, instance):
        """Enqueue instances for all nodes that don't have dependencies."""
        for node in self.nodes.all():
            node_instance = JobNodeInstance.objects.create(
                node=node,
                job_instance=instance)
            if node_instance.can_run():
                instance.schedule.queue.push(node_instance)
        while True:
            complete = True
            for ni in instance.nodis.all():
                if not Status.is_final(ni.status):
                    complete = False
                elif Status.is_failure(ni.status):
                    return False
            if complete and instance.nodis.count() == self.nodes.count():
                return True
            time.sleep(1)
    

class JobNode(Model):
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_jobnode'
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    job = ForeignKey(Job, related_name='nodes')
    
    def __unicode__(self):
        return u"[JobNode #%s in %s for %s]" % (self.id, self.job, self.task)
    
    __repr__ = __unicode__
    

class JobNodeInstance(AbstractInstance):
    """An instance of a node executed within a job."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_jobnodeinstance'
    
    objects = QuerySetManager()
    
    QuerySet = Instance.QuerySet
    
    # The node that spawned this instance.
    node = ForeignKey(JobNode, related_name='nis') # nis -> NodeInstances
    
    # The JobInstance that this NodeInstance belongs to.
    job_instance = ForeignKey(Instance, related_name='nodis')
    
    def start(self):
        try:
            AbstractInstance.start(self)
        finally:
            ji = self.job_instance
            if not Status.is_failure(self.status):
                for sub_dep in self.node.sub_deps.all():
                    sub_node = sub_dep.child
                    ni = sub_node.nis.get(job_instance=ji)
                    if ni.can_run():
                        self.job_instance.schedule.queue.push(ni)
    
    def run(self):
        self.node.task.run()
    
    @property
    def timeout(self):
        return self.node.task.timeout
    
    @property
    def source(self):
        return self.node.job
    
    @property
    def log_path(self):
        return os.path.join(self.job_instance.log_path + '-nodes',
            'node-%s' % self.id)
    
    @property
    def task(self):
        return self.node.task
    
    def can_run(self):
        """Whether dependencies are met for this instance to run."""
        for dep in self.node.super_deps.all():
            ni = dep.parent.nis.get(job_instance=self.job_instance)
            if ni.status != Status.SUCCESS:
                return False
        return True
    
    def __unicode__(self):
        return u'[NodeInstance #%s of %s]' % \
            (self.id, str(self.node.task)[1:-1])
    
    __repr__ = __unicode__
    

class Dependency(Model):
    """One task Node's dependency on another.
    
    Represents an edge in the job's dependency digraph.
    
    """
    class Meta:
        app_label = 'core'
        db_table = 'norc_dependency'
    
    parent = ForeignKey(JobNode, related_name='sub_deps')
    child = ForeignKey(JobNode, related_name='super_deps')
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        assert self.parent.job == self.child.job
    
    def __unicode__(self):
        return u"[Dependency %s -> %s]" % (self.parent, self.child)
    
    __repr__ = __unicode__
    

########NEW FILE########
__FILENAME__ = queue

"""All queueing related models."""

import datetime, time

from django.db.models.base import ModelBase
from django.db.models import (Model, Manager,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.models.task import AbstractInstance

class MetaQueue(ModelBase):
    """This metaclass is used to create a list of Queue implementations."""
    
    IMPLEMENTATIONS = []
    
    def __init__(self, name, bases, attrs):
        ModelBase.__init__(self, name, bases, attrs)
        if not self._meta.abstract:
            MetaQueue.IMPLEMENTATIONS.append(self)
    

class Queue(Model):
    """Abstract concept of a queue."""
    
    __metaclass__ = MetaQueue
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(unique=True, max_length=64)
    
    @staticmethod
    def get(name):
        for QueueClass in MetaQueue.IMPLEMENTATIONS:
            try:
                return QueueClass.objects.get(name=name)
            except QueueClass.DoesNotExist:
                pass
    
    @staticmethod
    def all_queues():
        return reduce(lambda a, b: a + b,
            [[q for q in QueueClass.objects.all()]
                for QueueClass in MetaQueue.IMPLEMENTATIONS])
    
    @staticmethod
    def validate(item):
        assert isinstance(item, AbstractInstance), "Invalid queue item."
    
    def save(self, *args, **kwargs):
        """Performs a name uniqueness check before saving a new queue."""
        if not self.pk and Queue.get(self.name) != None:
            raise ValueError(
                "A queue with name %s already exists." % self.name)
        return super(Queue, self).save(*args, **kwargs)
    
    # TODO: Unique names for queues should be enforced somehow around here.
    # def __init__(self, *args, **kwargs):
    #     print type(self)
    #     if type(self) == Queue:
    #         raise NotImplementedError("Can't instantiate Queue directly!")
    #     Model.__init__(self, *args, **kwargs)
    
    def peek(self):
        raise NotImplementedError
    
    def pop(self, timeout=None):
        raise NotImplementedError
    
    def push(self, item):
        raise NotImplementedError
    
    def count(self):
        raise NotImplementedError
    
    def __unicode__(self):
        return u"[%s %s]" % (type(self).__name__, self.name)
    
    __repr__ = __unicode__


class DBQueue(Queue):
    """A distributed queue implementation that uses the Norc database.
    
    In order to reduce database load, it is recommended to use an
    indepedent distributed queueing system, like Amazon's SQS.
    
    """
    class Meta:
        app_label = 'core'
        db_table = 'norc_dbqueue'
    
    def peek(self):
        """Retrieves the next item but does not remove it from the queue.
        
        Returns None if the queue is empty.
        
        """
        try:
            return self.items.all()[0].item
        except IndexError:
            return None
    
    def pop(self):
        """Retrieves the next item and removes it from the queue."""
        try:
            next = self.items.all()[0]
        except IndexError:
            return None
        next.delete()
        return next.item
    
    def push(self, item):
        """Adds an item to the queue."""
        Queue.validate(item)
        DBQueueItem.objects.create(dbqueue=self, item=item)
    
    def count(self):
        return self.items.count()


class DBQueueItem(Model):
    """An item in a DBQueue."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_dbqueueitem'
        ordering = ['id']
    
    # The queue this item is a part of.
    dbqueue = ForeignKey(DBQueue, related_name='items')
    
    # The item being enqueued.
    item_type = ForeignKey(ContentType)
    item_id = PositiveIntegerField()
    item = GenericForeignKey('item_type', 'item_id')
    
    # The datetime at which this item was enqueued.
    enqueued = DateTimeField(default=datetime.datetime.utcnow, db_index=True)
    
    def __unicode__(self):
        return u'[DBQueueItem #%s, %s]' % (self.id, self.enqueued)
        

########NEW FILE########
__FILENAME__ = queuegroup

from django.db.models import Model, ForeignKey, PositiveIntegerField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import \
    GenericRelation, GenericForeignKey

from norc.core.models.queue import Queue

class QueueGroup(Queue):
    """A group of Norc queues."""
    
    class Meta:
        app_label = "core"
        db_table = "norc_queuegroup"
    
    @property
    def queues(self):
        return [i.queue for i in self.items.all()]
    
    def peek(self):
        """Retrieves the next item but does not remove it from the queue.
        
        Returns None if the queue is empty.
        
        """
        for q in self.queues:
            try:
                i = q.peek()
                if i != None:
                    return i
            except:
                pass
        return None
    
    def pop(self):
        """Retrieves the next item and removes it from the queue."""
        for q in self.queues:
            try:
                i = q.pop()
                if i != None:
                    return i
            except:
                pass
        return None
    
    def push(self, item):
        raise NotImplementedError("Cannot push to a queue group.")
    
    def count(self):
        return sum([q.count() for q in self.queues])
    

class QueueGroupItem(Model):
    """Maps queues to QueueGroups."""
    
    class Meta:
        app_label = "core"
        db_table = "norc_queuegroupitem"
        ordering = ["priority"]
        unique_together = ("group", "queue_type", "queue_id")
    
    group = ForeignKey(QueueGroup, related_name="items")
    
    queue_type = ForeignKey(ContentType)
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey("queue_type", "queue_id")
    
    priority = PositiveIntegerField()
    
    def __unicode__(self):
        return u'[QueueGroupItem G:%s Q:%s P:%s]' % (self.group, self.queue, self.priority)
    
    __repr__ = __unicode__
    

########NEW FILE########
__FILENAME__ = scheduler

"""The Norc Scheduler is defined here.

Norc requires that at least one of these is running at all times.

"""

import os
import re
import signal
import random
import time
from datetime import datetime, timedelta
from threading import Thread, Event
import itertools

# from django.db.models.query import QuerySet
from django.db.models import (Model, Manager,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveSmallIntegerField)

from norc import settings
from norc.core.models.task import Instance
from norc.core.models.schedules import Schedule, CronSchedule
from norc.core.models.daemon import AbstractDaemon
from norc.core.constants import (Status, Request,
    SCHEDULER_PERIOD, SCHEDULER_LIMIT, HEARTBEAT_PERIOD, HEARTBEAT_FAILED)
from norc.norc_utils import search
from norc.norc_utils.parallel import MultiTimer
from norc.norc_utils.log import make_log
from norc.norc_utils.django_extras import queryset_exists, get_object
from norc.norc_utils.django_extras import QuerySetManager, MultiQuerySet
from norc.norc_utils.backup import backup_log

class Scheduler(AbstractDaemon):
    """Scheduling process for handling Schedules.
    
    Takes unclaimed Schedules from the database and adds their next
    instance to a timer.  At the appropriate time, the instance is
    added to its queue and the Schedule is updated.
    
    Idea: Split this up into two threads, one which continuously handles
    already claimed schedules, the other which periodically polls the DB
    for new schedules.
    
    """
    class Meta:
        app_label = 'core'
        db_table = 'norc_scheduler'
    
    objects = QuerySetManager()
    
    class QuerySet(AbstractDaemon.QuerySet):
        """Custom manager/query set for Scheduler."""
        
        def undead(self):
            """Schedulers that are active but the heart isn't beating."""
            cutoff = datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
            return self.status_in("active").filter(heartbeat__lt=cutoff)
    
    # All the statuses Schedulers can have.  See constants.py.
    VALID_STATUSES = [
        Status.CREATED,
        Status.RUNNING,
        Status.PAUSED,
        Status.ENDED,
        Status.ERROR,
    ]
    
    VALID_REQUESTS = [
        Request.STOP,
        Request.KILL,
        Request.PAUSE,
        Request.RESUME,
        Request.RELOAD,
    ]
    
    # The status of this scheduler.
    status = PositiveSmallIntegerField(default=Status.CREATED,
        choices=[(s, Status.name(s)) for s in VALID_STATUSES])
    
    # A state-change request.
    request = PositiveSmallIntegerField(null=True,
        choices=[(r, Request.name(r)) for r in VALID_REQUESTS])
    
    def __init__(self, *args, **kwargs):
        AbstractDaemon.__init__(self, *args, **kwargs)
        self.timer = MultiTimer()
        self.set = set()
    
    def start(self):
        """Starts the Scheduler."""
        # Temporary check until multiple schedulers is supported fully.
        if Scheduler.objects.alive().count() > 0:
            print "Cannot run more than one scheduler at a time."
            return
        AbstractDaemon.start(self)
    
    def run(self):
        """Main run loop of the Scheduler."""
        self.timer.start()
        
        while not Status.is_final(self.status):
            if self.request:
                self.handle_request()
            
            if self.status == Status.RUNNING:
                # Clean up orphaned schedules and undead schedulers.
                # Schedule.objects.orphaned().update(scheduler=None)
                # CronSchedule.objects.orphaned().update(scheduler=None)
                
                cron = CronSchedule.objects.unclaimed()[:SCHEDULER_LIMIT]
                simple = Schedule.objects.unclaimed()[:SCHEDULER_LIMIT]
                for schedule in itertools.chain(cron, simple):
                    self.log.info('Claiming %s.' % schedule)
                    schedule.scheduler = self
                    schedule.save()
                    self.add(schedule)
            if not Status.is_final(self.status):
                self.wait()
                self.request = Scheduler.objects.get(pk=self.pk).request
    
    def wait(self):
        """Waits on the flag."""
        AbstractDaemon.wait(self, SCHEDULER_PERIOD)
    
    def clean_up(self):
        self.timer.cancel()
        self.timer.join()
        cron = self.cronschedules.all()
        simple = self.schedules.all()
        claimed_count = cron.count() + simple.count()
        if claimed_count > 0:
            self.log.info("Cleaning up %s schedules." % claimed_count)
            cron.update(scheduler=None)
            simple.update(scheduler=None)
    
    def handle_request(self):
        """Called when a request is found."""
        
        # Clear request immediately.
        request = self.request
        self.request = None
        self.save()
        
        self.log.info("Request received: %s" % Request.name(request))
        
        if request == Request.PAUSE:
            self.set_status(Status.PAUSED)
        
        elif request == Request.RESUME:
            if self.status != Status.PAUSED:
                self.log.info("Must be paused to resume; clearing request.")
            else:
                self.set_status(Status.RUNNING)
        
        elif request == Request.STOP:
            self.set_status(Status.ENDED)
        
        elif request == Request.KILL:
            self.set_status(Status.KILLED)
        
        elif request == Request.RELOAD:
            changed = MultiQuerySet(Schedule, CronSchedule)
            changed = changed.objects.unfinished.filter(
                changed=True, scheduler=self)
            for item in self.timer.tasks:
                s = item[2][0]
                if s in changed:
                    self.log.info("Removing outdated: %s" % s)
                    self.timer.tasks.remove(item)
                    self.set.remove(s)
                s = type(s).objects.get(pk=s.pk)
            for s in changed:
                self.log.info("Adding updated: %s" % s)
                self.add(s)
            changed.update(changed=False)
    
    def add(self, schedule):
        """Adds the schedule to the timer."""
        try:
            if schedule in self.set:
                self.log.error("%s has already been added to this Scheduler." %
                    schedule)
                return
            self.log.debug('Adding %s to timer for %s.' %
                (schedule, schedule.next))
            self.timer.add_task(schedule.next, self._enqueue, [schedule])
            self.set.add(schedule)
        except:
            self.log.error(
                "Invalid schedule %s found, deleting." % schedule)
            schedule.soft_delete()
    
    def _enqueue(self, schedule):
        """Called by the timer to add an instance to the queue."""
        updated_schedule = get_object(type(schedule), pk=schedule.pk)
        self.set.remove(schedule)
        if updated_schedule == None or updated_schedule.deleted:
            self.log.info('%s was removed.' % schedule)
            if updated_schedule != None:
                updated_schedule.scheduler = None
                updated_schedule.save()
            return
        schedule = updated_schedule
        
        if not schedule.scheduler == self:
            self.log.info("%s is no longer tied to this Scheduler." %
                schedule)
            # self.set.remove(schedule)
            return
        instance = Instance.objects.create(
            task=schedule.task, schedule=schedule)
        self.log.info('Enqueuing %s.' % instance)
        schedule.queue.push(instance)
        schedule.enqueued()
        if not schedule.finished():
            self.add(schedule)
        else:
            schedule.scheduler = None
            schedule.save()
    
    @property
    def log_path(self):
        return 'schedulers/scheduler-%s' % self.id
    

########NEW FILE########
__FILENAME__ = schedules

import re
import random
import time
from datetime import datetime, timedelta

from django.db.models import (Model, Manager, Q,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveIntegerField,
    ForeignKey)
from django.db.models.query import QuerySet
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from norc.core.constants import HEARTBEAT_FAILED, Request
from norc.core.models.task import Instance
from norc.norc_utils import search
from norc.norc_utils.django_extras import QuerySetManager
from norc.norc_utils.parallel import MultiTimer
from norc.norc_utils.log import make_log


class AbstractSchedule(Model):
    """A schedule of executions for a specific task."""
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    class QuerySet(QuerySet):
    
        @property
        def unfinished(self):
            return self.filter(deleted=False).filter(
                Q(remaining__gt=0) | Q(repetitions=0))
        
        def unclaimed(self):
            return self.unfinished.filter(scheduler__isnull=True)
        
        def orphaned(self):
            cutoff = datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
            return self.unfinished.exclude(scheduler__heartbeat__gt=cutoff)
    
    # The Task this is a schedule for.
    task_type = ForeignKey(ContentType, related_name='%(class)ss')
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    
    # The Queue to execute the Task through.
    queue_type = ForeignKey(ContentType, related_name='%(class)s_set')
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey('queue_type', 'queue_id')
    
    # The total number of repetitions of the Task.  0 for infinite.
    repetitions = PositiveIntegerField()
    
    # The number of repetitions remaining.
    remaining = PositiveIntegerField()
    
    # The Scheduler that has scheduled the next execution.
    scheduler = ForeignKey('core.Scheduler', null=True, blank=True, 
        related_name='%(class)ss')
    
    # Whether or not to make up missed executions.
    make_up = BooleanField(default=False)
    
    # When this schedule was added.
    added = DateTimeField(default=datetime.utcnow)
    
    # Whether this schedule has been changed and needs to be reloaded.
    changed = BooleanField(default=False)
    
    # Marks a schedule as deleted and to be ignored.
    deleted = BooleanField(default=False)
    
    @property
    def instances(self):
        """Custom implemented to avoid cascade-deleting instances."""
        schedule_type = ContentType.objects.get_for_model(self)
        return Instance.objects.filter(
            schedule_type__pk=schedule_type.pk, schedule_id=self.id)
    
    def enqueued(self):
        """Called when the next instance has been enqueued."""
        raise NotImplementedError
    
    def finished(self):
        """Checks whether all runs of the Schedule have been completed."""
        return self.remaining == 0 and self.repetitions > 0
    
    def soft_delete(self):
        """Marks the schedule as deleted in the DB without erasing data."""
        self.deleted = True
        self.save()
    
    def __eq__(self, other):
        return type(self) == type(other) and self.pk == other.pk

class Schedule(AbstractSchedule):
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_schedule'
    
    objects = QuerySetManager()
    
    class QuerySet(AbstractSchedule.QuerySet):
        pass
    
    # Next execution.
    next = DateTimeField(null=True)
    
    # The delay in between executions.
    period = PositiveIntegerField()
    
    @staticmethod
    def create(task, queue, period=0, reps=1, start=0, make_up=False):
        if type(start) == int:
            start = timedelta(seconds=start)
        if type(start) == timedelta:
            start = datetime.utcnow() + start
        return Schedule.objects.create(task=task, queue=queue, next=start,
            repetitions=reps, remaining=reps, period=period, make_up=make_up)
    
    def enqueued(self):
        """Called when the next instance has been enqueued."""
        now = datetime.utcnow()
        # Sanity check: this method should never be called before self.next.
        assert self.next < now, "Enqueued too early!"
        if self.repetitions > 0:
            self.remaining -= 1
        self.period = Schedule.objects.get(pk=self.pk).period
        if not self.finished() and self.period > 0:
            period = timedelta(seconds=self.period)
            self.next += period
            while not self.make_up and self.next < now:
                self.next += period
        elif self.finished():
            self.next = None
        self.save()
    
    def __unicode__(self):
        return u'[Schedule #%s, %s:%ss]' % \
            (self.id, self.task, self.period)
    
    __repr__ = __unicode__

ri = random.randint

def _make_halfhourly():
    m = ri(0, 29)
    return 'o*d*w*h*m%s,%ss%s' % (m, m + 30, ri(0, 59))

def _make_hourly():
    return 'o*d*w*h*m%ss%s' % (ri(0, 59), ri(0, 59))

def _make_daily():
    return 'o*d*w*h%sm%ss%s' % (ri(0, 23), ri(0, 59), ri(0, 59))

def _make_weekly():
    return 'o*d*w%sh%sm%ss%s' % (ri(0, 6), ri(0, 23), ri(0, 59), ri(0, 59))

def _make_monthly():
    return 'o*d%sw*h%sm%ss%s' % (ri(1, 28), ri(0, 23), ri(0, 59), ri(0, 59))

class CronSchedule(AbstractSchedule):
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_cronschedule'
    
    objects = QuerySetManager()
    
    class QuerySet(AbstractSchedule.QuerySet):
        pass
    
    # The datetime that the next execution time is based off of.
    base = DateTimeField(default=datetime.utcnow)
    
    # The string encoding of the schedule.
    encoding = CharField(max_length=864)
    
    MONTHS = range(1,13)
    DAYS = range(1,32)
    DAYSOFWEEK = range(7)
    HOURS = range(24)
    MINUTES = range(60)
    SECONDS = range(60)
    
    SYNONYMS = {
        'o': (('o', 'months'), MONTHS),
        'd': (('d', 'day', 'days'), DAYS),
        'w': (('w', 'weekday', 'weekdays', 'daysofweek'), DAYSOFWEEK),
        'h': (('h', 'hour', 'hours'), HOURS),
        'm': (('m', 'minute', 'minutes'), MINUTES),
        's': (('s', 'second', 'seconds', 'sec', 'secs'), SECONDS),
    }
    
    FIELDS = ['months', 'days', 'daysofweek', 'hours', 'minutes', 'seconds']
    
    MAKE_PREDEFINED = {
        'HALFHOURLY': _make_halfhourly,
        'HOURLY': _make_hourly,
        'DAILY': _make_daily,
        'WEEKLY': _make_weekly,
        'MONTHLY': _make_monthly,
    }
    
    @staticmethod
    def create(task, queue, encoding, reps=0, make_up=False):
        if encoding.upper() in CronSchedule.MAKE_PREDEFINED:
            encoding = CronSchedule.MAKE_PREDEFINED[encoding.upper()]()
        encoding = CronSchedule.validate(encoding)[0]
        return CronSchedule.objects.create(task=task, encoding=encoding,
            queue=queue, repetitions=reps, remaining=reps, make_up=make_up)
    
    @staticmethod
    def decode(encoding):
        regex = r'([a-zA-Z])+(\*|\d+(?:,\d+)*)'
        encoding = ''.join(encoding.split()) # Strip whitespace.
        results = {}
        assert re.sub(regex, '', encoding) == '', \
            "Invalid formatting found in encoding '%s'." % encoding
        for k, ls in re.findall(regex, encoding):
            choices = map(int, ls.split(',')) if ls != '*' else '*'
            found = False
            for names, valid_range in CronSchedule.SYNONYMS.values():
                if k in names:
                    if choices == '*':
                        choices = valid_range
                    assert all([e in valid_range for e in choices]), \
                        "Invalid number found for key '%s'." % k
                    choices.sort()
                    results[names[0]] = choices
                    found = True
                    break
            assert found, "Invalid key: '%s'" % k
        return results
    
    @staticmethod
    def validate(encoding):
        """Attempts to create a valid version of an encoding.
        
        This function will throw assertion errors if it finds invalid
        content in the encoding.  It returns a validated version of the
        encoding as well as a dictionary with the parsed schedule lists.
        
        """
        SYNS = CronSchedule.SYNONYMS
        results = CronSchedule.decode(encoding)
        # Get everything possible from encoding and make sure it's valid.
        for k, choices in results.iteritems():
            assert all([c in SYNS[k][1] for c in choices]), \
                "Invalid number found in range for key '%s'." % k
        # Fill in any missing ranges.
        for k, valid_r in [(k, v[1]) for k, v in SYNS.items()]:
            if not k in results:
                if k != 's':
                    results[k] = valid_r
                else:
                    results[k] = [random.choice(valid_r)]
        assert set(results.keys()) == set(SYNS.keys())
        new_encoding = 'o%sd%sw%sh%sm%ss%s' % tuple(['*' if results[k] ==
            SYNS[k][1] else ','.join(map(str, results[k])) for k in 'odwhms'])
        return new_encoding, results
    
    def __init__(self, *args, **kwargs):
        AbstractSchedule.__init__(self, *args, **kwargs)
        self._next = None
    
    def set_lists(self, d=None):
        if not d:
            d = CronSchedule.validate(self.encoding)[1]
        self.months = d['o']
        self.days = d['d']
        self.daysofweek = d['w']
        self.hours = d['h']
        self.minutes = d['m']
        self.seconds = d['s']
    
    def reschedule(self, encoding):
        e, d = CronSchedule.validate(encoding)
        self = CronSchedule.objects.get(pk=self.pk)
        self.encoding = e
        self.set_lists(d)
        self.changed = True
        self.save()
        if self.scheduler != None:
            self.scheduler.make_request(Request.RELOAD)
        return self
    
    def enqueued(self):
        """Called when the next instance has been enqueued."""
        now = datetime.utcnow()
        # Sanity check: this method should never be called before self.next.
        assert self.next < now, "Enqueued too early!"
        if self.repetitions > 0:
            self.remaining -= 1
        if not self.finished():
            if self.make_up:
                self.base = self.next
            else:
                self.base = now
        self._next = None # Don't calculate now, but clear the old value.
        self.encoding = CronSchedule.objects.get(pk=self.pk).encoding
        self.save()
    
    @property
    def next(self):
        """Essentially a wrapper for calculate_next() with a cache.
        
        The cache is _next, and it is manually cleared by enqueued().
        
        """
        if not self._next:
            self._next = self.calculate_next()
        return self._next
    
    def calculate_next(self, dt=None):
        if not hasattr(self, "months"):
            self.set_lists()
        if not dt:
            dt = self.base
        dt = dt.replace(microsecond=0)
        dt += timedelta(seconds=1)
        second = self.find_gte(dt.second, self.seconds)
        if second == None:
            second = self.seconds[0]
            dt += timedelta(minutes=1)
        dt = dt.replace(second=second)
        minute = self.find_gte(dt.minute, self.minutes)
        if minute == None:
            minute = self.minutes[0]
            dt += timedelta(hours=1)
        dt = dt.replace(minute=minute)
        hour = self.find_gte(dt.hour, self.hours)
        if hour == None:
            hour = self.hours[0]
            dt += timedelta(days=1)
        dt = dt.replace(hour=hour)
        cond = lambda d: d.day in self.days and d.weekday() in self.daysofweek
        one_day = timedelta(days=1)
        while not cond(dt):
            dt += one_day
        return dt
    
    def find_gte(self, p, ls):
        """Return the first element of ls that is >= p."""
        # TODO: Binary search.
        for e in ls:
            if e >= p:
                return e
    
    def pretty_name(self):
        """Returns the pretty (predefined) name for this schedule."""
        searchs = {
            r'o\*d\*w\*h\*m(\d+),(\d+)s\d+': 'HALFHOURLY',
            r'o\*d\*w\*h\*m\d+s\d+': 'HOURLY',
            r'o\*d\*w\*h\d+m\d+s\d+': 'DAILY',
            r'o\*d\*w\d+h\d+m\d+s\d+': 'WEEKLY',
            r'o\*d\d+w\*h\d+m\d+s\d+': 'MONTHLY',
        }
        for regex, name in searchs.items():
            m = re.match(regex, self.encoding)
            if m:
                # A check just for HALFHOURLY.
                mins = map(int, m.groups())
                if m.groups() and abs(mins[0] - mins[1]) != 30:
                    continue
                return name
        # If no pretty name, just return the encoding.
        return self.encoding
    
    def __unicode__(self):
        return u'[CronSchedule #%s, %s:%s]' % \
            (self.id, self.task, self.encoding)
    
    __repr__ = __unicode__
    

########NEW FILE########
__FILENAME__ = task

"""All basic task related models."""

import os, sys
from datetime import datetime
import re
import subprocess
import signal

from django.db.models import (Model, query, base,
    BooleanField,
    CharField,
    DateTimeField,
    IntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc import settings
from norc.core.constants import (Status,
    TASK_MODELS, INSTANCE_MODELS, FINALLY_TIMEOUT)
from norc.norc_utils.log import make_log
from norc.norc_utils.django_extras import QuerySetManager
from norc.norc_utils.parsing import parse_since

class MetaTask(base.ModelBase):
    def __init__(self, name, bases, dct):
        base.ModelBase.__init__(self, name, bases, dct)
        if not self._meta.abstract:
            TASK_MODELS.append(self)
    

class Task(Model):
    """An abstract class that represents something to be executed."""
    
    __metaclass__ = MetaTask
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(max_length=128, unique=True, null=True)
    description = CharField(max_length=512, blank=True, default='')
    date_added = DateTimeField(default=datetime.utcnow)
    timeout = PositiveIntegerField(default=0)
    instances = GenericRelation('Instance',
        content_type_field='task_type', object_id_field='task_id')
    
    schedules = GenericRelation('Schedule',
        content_type_field='task_type', object_id_field='task_id')
    cronschedules = GenericRelation('CronSchedule',
        content_type_field='task_type', object_id_field='task_id')
    
    def start(self, instance):
        """ A hook function for easily changing the parameters to run().
        
        This is useful because some types of task (such as Job) need access
        to the instance object that is currently running, but we don't want
        to make run have any parameters by default.
        
        """
        return self.run()
    
    def run(self):
        """The actual work of the Task should be done in this function."""
        raise NotImplementedError
    
    def get_name(self):
        return self.name or ("#%s" % self.id if self.id
            else False) or "(nameless)"
    
    def get_revision(self):
        """ Hook to provide revision tracking functionality for instances.
        
        The value returned by this function will be retrieved and set for
        each instance of the task that is run.
        
        """
        return None
    
    def __unicode__(self):
        return u"[%s %s]" % (type(self).__name__, self.get_name())
    
    __repr__ = __unicode__
    

class MetaInstance(base.ModelBase):
    
    def __init__(self, name, bases, dct):
        base.ModelBase.__init__(self, name, bases, dct)
        if not self._meta.abstract:
            INSTANCE_MODELS.append(self)
    

class AbstractInstance(Model):
    """One instance (run) of a Task."""
    
    __metaclass__ = MetaInstance
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    class QuerySet(query.QuerySet):
        
        def since(self, since):
            if type(since) == str:
                since = parse_since(since)
            return self.exclude(ended__lt=since) if since else self
        
        def status_in(self, statuses):
            if isinstance(statuses, basestring):
                statuses = Status.GROUPS(statuses)
            return self.filter(status__in=statuses) if statuses else self
        
        def from_queue(self, q):
            return self.filter(executor__queue_id=q.id,
                executor__queue_type=ContentType.objects.get_for_model(q).id)
        
    
    VALID_STATUSES = [
        Status.CREATED,
        Status.RUNNING,
        Status.SUCCESS,
        Status.FAILURE,
        Status.HANDLED,
        Status.ERROR,
        Status.TIMEDOUT,
        Status.INTERRUPTED,
    ]
    
    # The status of the execution.
    status = PositiveSmallIntegerField(default=Status.CREATED,
        choices=[(s, Status.name(s)) for s in VALID_STATUSES])
    
    # When the instance was added to a queue.
    enqueued = DateTimeField(default=datetime.utcnow)
    
    # When the instance started.
    started = DateTimeField(null=True)
    
    # When the instance ended.
    ended = DateTimeField(null=True)
    
    # The executor of this instance.
    executor = ForeignKey('core.Executor', null=True,
        related_name='_%(class)ss')
    
    revision = ForeignKey('core.Revision', null=True,
        related_name='_%(class)ss')
    
    def start(self):
        """Performs initialization before calling run()."""
        
        if not hasattr(self, 'log'):
            self.log = make_log(self.log_path)
        if self.status != Status.CREATED:
            self.log.error("Can't start an instance more than once.")
            return
        try:
            for signum in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(signum, self.kill_handler)
        except ValueError:
            pass
        if self.timeout > 0:
            signal.signal(signal.SIGALRM, self.timeout_handler)
            signal.alarm(self.timeout)
        self.log.info('Starting %s.' % self)
        self.log.start_redirect()
        self.status = Status.RUNNING
        self.revision = self.get_revision()
        self.started = datetime.utcnow()
        self.save()
        try:
            success = self.run()
        except Exception:
            self.log.error("Task failed with an exception!", trace=True)
            self.status = Status.FAILURE
        else:
            if success or success == None:
                self.status = Status.SUCCESS
            else:
                self.status = Status.FAILURE
        finally:
            self.run_finally()
            self.cleanup()
            sys.exit(0 if self.status == Status.SUCCESS else 1)
    
    def run_finally(self):
        signal.alarm(0)
        if hasattr(self, "finally_") and callable(self.finally_):
            signal.signal(signal.SIGALRM, self.finally_timeout_handler)
            signal.alarm(FINALLY_TIMEOUT)
            self.log.info("Executing final block...")
            self.finally_()
            signal.alarm(0)
    
    def cleanup(self):
        """Cleanup code that should be executed last."""
        self.ended = datetime.utcnow()
        self.save()
        self.log.info("Task ended with status %s." %
            Status.name(self.status))
        self.log.stop_redirect()
    
    def run(self):
        """Runs the instance."""
        raise NotImplementedError
    
    def kill_handler(self, *args, **kwargs):
        self.log.info("Interrupt signal received!")
        self.status = Status.INTERRUPTED
        self.run_finally()
        self.cleanup()
        self._nuke()
    
    def timeout_handler(self, *args, **kwargs):
        self.log.error("Task timed out!")
        self.status = Status.TIMEDOUT
        self.run_finally()
        self.cleanup()
        self._nuke()
    
    def finally_timeout_handler(self, *args, **kwargs):
        self.log.error("Final block timed out!")
        self.status = Status.TIMEDOUT
        self.cleanup()
        self._nuke()
    
    def _nuke(self, *args, **kwargs):
        self.log.info("Ceasing execution.")
        os._exit(1)
    
    def get_revision(self):
        """ Hook to provide revision tracking functionality for instances.
        
        Defaults to None because other instances implementations might not
        have task attributes.
        
        """
        return None
    
    @property
    def timeout(self):
        return 0
    
    @property
    def source(self):
        return None
    
    @property
    def queue(self):
        try:
            return self.executor.queue
        except AttributeError:
            return None
    
    @property
    def log_path(self):
        return "instances/%s/%s" % (type(self).__name__, self.id)
    
    @property
    def log_url(self):
        return ('/logs/instances/%s_%s/' %
            (ContentType.objects.get_for_model(self).id, self.id))
    
    def __unicode__(self):
        return u"[%s #%s]" % (type(self).__name__, self.id)
    
    __repr__ = __unicode__
    

class Instance(AbstractInstance):
    """Normal Instance implementation for Tasks."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_instance'
    
    objects = QuerySetManager()
    
    # The object that spawned this instance.
    task_type = ForeignKey(ContentType, related_name='instances')
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    
    # The schedule from whence this instance spawned.
    schedule_type = ForeignKey(ContentType, null=True)
    schedule_id = PositiveIntegerField(null=True)
    schedule = GenericForeignKey('schedule_type', 'schedule_id')
    
    def run(self):
        return self.task.start(self)
    
    @property
    def timeout(self):
        return self.task.timeout
    
    @property
    def source(self):
        return self.task.get_name()
    
    @property
    def log_path(self):
        return 'tasks/%s/%s/%s-%s' % (self.task.__class__.__name__,
            self.task.get_name(), self.task.get_name(), self.id)
    
    def get_revision(self):
        """ Hook to provide revision tracking functionality.
        
        Redirects to Task.get_revision() for ease with normal task/instance
        setups.  Other instances implementations might need to customize.
        
        """
        return self.task.get_revision()
    
    def __unicode__(self):
        return u'[Instance #%s of %s]' % (self.id, str(self.task)[1:-1])
    
    __repr__ = __unicode__
    

class CommandTask(Task):
    """Task which runs an arbitrary shell command."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_commandtask'
    
    command = CharField(max_length=1024)
    nice = IntegerField(default=0)
    
    INTERPRETED_SETTINGS = ['NORC_TMP_DIR', 'DATABASE_NAME', 'DATABASE_USER',
        'DATABASE_PASSWORD', 'DATABASE_HOST', 'DATABASE_PORT']
    
    @staticmethod
    def interpret(cmd):
        for s in CommandTask.INTERPRETED_SETTINGS:
            cmd = cmd.replace('$' + s, getattr(settings, s))
        def unpack_match(f):
            return lambda m: f(*m.groups())
        def datetime_parser(dt):
            def parser(s):
                decoder = dict(YYYY='%Y', MM='%m', DD='%d',
                    hh='%H', mm='%m', ss='%S')
                for k, v in decoder.items():
                    s = s.replace(k, dt.strftime(v))
                return s
            return unpack_match(parser)
        local = datetime.now()
        utc = datetime.utcnow()
        cmd = re.sub(r'\$LOCAL\{(.*?)\}', datetime_parser(local), cmd)
        cmd = re.sub(r'\$UTC\{(.*?)\}', datetime_parser(utc), cmd)
        return cmd
    
    def run(self):
        command = CommandTask.interpret(self.command)
        if self.nice:
            command = "nice -n %s %s" % (self.nice, command)
        print "Executing command...\n$ %s" % command
        sys.stdout.flush()
        exit_status = subprocess.call(command, shell=True,
            stdout=sys.stdout, stderr=sys.stderr)
        if exit_status in [126, 127]:
            raise ValueError("Invalid command: %s" % command)
        return exit_status == 0
    

########NEW FILE########
__FILENAME__ = norc_taskrunner
#!/usr/bin/env python

"""Script to run a Norc instance for 2.5 compatibility."""

import sys
from optparse import OptionParser

from django.contrib.contenttypes.models import ContentType

def main():
    usage = "norc_taskrunner --ct_pk <pk> --content_pk <pk>" # [-e] [-d]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("--ct_pk",
        help="The ContentType primary key for the object to start().")
    parser.add_option("--target_pk",
        help="The primary key of the object to start().")
    # parser.add_option("-e", "--echo", action="store_true", default=False,
    #     help="Echo log messages to stdout.")
    # parser.add_option("-d", "--debug", action="store_true", default=False,
    #     help="Enable debug messages.")
    
    (options, args) = parser.parse_args()
    
    if not hasattr(options, 'ct_pk') or not hasattr(options, 'target_pk'):
        bad_args("You must give the ContentType and target primary keys.")
    
    try:
        ct = ContentType.objects.get(pk=options.ct_pk)
    except ContentType.DoesNotExist:
        bad_args("Invalid ContentType primary key '%s'." % options.ct_pk)
    
    try:
        target = ct.get_object_for_this_type(pk=options.target_pk)
    except ct.model_class().DoesNotExist:
        bad_args("Target object not found for pk='%s'" % options.target_pk)
    
    target.start()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = reports

"""External modules should access Norc data using these functions.

The main benefit currently is to prevent the occurence of a try block
everywhere data is needed, and to reduce the amount of code needed for
retrievals using consistent attributes.  Additionally, it prevents
external modules from having to query core classes directly.

"""

from django.contrib.contenttypes.models import ContentType

from norc.core.models import *
from norc.core.constants import Status, TASK_MODELS, INSTANCE_MODELS
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.formatting import untitle
from norc.norc_utils.django_extras import get_object

from norc import settings    

for path in settings.EXTERNAL_CLASSES:
    split = path.split(".")
    try:
        __import__(".".join(split[:-1]), fromlist=[split[-1]])
    except ImportError:
        print "Failed to import %s." % path

all = {}

def make_status_color(status, alive):
    if status in map(Status.name, Status.GROUPS("error")):
        return "status_error"
    elif status in map(Status.name, Status.GROUPS("succeeded")):
        return "status_good"
    elif status == "RUNNING":
        if not alive or (alive and alive == "True"):
            return "status_good"
        else:
            return "status_error"
    elif status in map(Status.name, Status.GROUPS("active")):
        return "status_good"
    else:
        return "status_error"

def generate(data_set, report, params):
    ret_list = []
    for obj in data_set:
        obj_data = {}
        for key, func in report.data.iteritems():
            obj_data[key] = func(obj, **params)
        if "status" in obj_data:
            obj_data["status_color"] = make_status_color(
                obj_data["status"], obj_data.get("alive"))
        ret_list.append(obj_data)
    return ret_list

class Report(type):
    """A definition for the data of a status table on the frontend.
    
    Contains all the information needed for retrieving and organizing the
    data for displaying in a table on the status page.
    
    Required parameters:
    
    key         String which identifies this data.
    data        A dictionary whose keys represent columns in the table and
                whose values are functions which take an object and the GET
                dict from the AJAX request and return the desired data.
    
    Optional parameters:
    
    retrieve        Function which returns the basic set of data.  Needed
                    if the data is to have its own table.
    detail_key      String which identifies the type of data that expanding
                    a row in this table will reveal.
    details         Function which takes the ID of an object and the GET
                    params and returns the detail objects for that ID.
    since_filter    Function which takes data and a since date and filters
                    the data using that date.
    order_by        Function which takes data and an optional order string
                    and returns ordered data.
    
    """
    def __new__(cls, name, bases, dct):
        function = type(lambda: None)
        attr_getter = lambda a: lambda obj, **kws: getattr(obj, a)
        for k, v in dct.iteritems():
            if type(v) == function:
                dct[k] = staticmethod(v)
        for h in dct['headers']:
            k = untitle(h)
            if not k in dct['data']:
                dct['data'][k] = attr_getter(k)
        return type.__new__(cls, name, bases, dct)
    
    def __init__(self, name, bases, dct):
        type.__init__(self, name, bases, dct)
        if name != 'BaseReport':
            all[name] = self
        # if base:
        #     self = copy(REPORT[base])
        # for k, v in kwargs.iteritems():
        #     setattr(self, k, v)
        # DATA_DEFS[self.key] = self
    
    def __call__(self, id=None):
        return self.get(id) if id != None else self.get_all()
    
    # def __getattr__(self, *args, **kwargs):
    #     try:
    #         return super(Report, self).__getattr__(self, *args, **kwargs)
    #     except AttributeError:
    #         return None
    

def date_ended_since(query, since):
    if type(since) == str:
        since = parse_since(since)
    return query.exclude(ended__lt=since) if since else query

date_ended_order = lambda data, o: data.order_by(o if o else '-ended')
date_ended_getter = lambda obj, **kws: obj.ended if obj.ended else '-'

def _parse_content_ids(id_str):
    ct_id, obj_id = map(int, id_str.split('_'))
    ct = ContentType.objects.get(id=ct_id)
    return ct.get_object_for_this_type(id=obj_id)

class BaseReport(object):
    """Ideally, this would be replaced with a class decorator in 2.6."""
    __metaclass__ = Report
    get = lambda id: None
    get_all = lambda: None
    since_filter = lambda data, since: data
    order_by = lambda data, order: data
    details = {}
    headers = []
    data = {}

def _executor_instance_counter(executor, since, group):
    return executor.instances.since(since).status_in(group).count()

class executors(BaseReport):
    
    get = lambda id: get_object(Executor, id=id)
    get_all = lambda: Executor.objects.all()
    
    since_filter = date_ended_since
    order_by = date_ended_order
    
    details = {
        'instances': lambda id, since=None, status=None, **kws:
            executors.get(id).instances.since(since).status_in(status),
    }
    headers = ['ID', 'Queue', 'Queue Type', 'Host', 'PID', 'Running',
        'Succeeded', 'Failed', 'Started', 'Ended', 'Status']
    data = {
        'queue': lambda obj, **kws: obj.queue.name,
        'queue_type': lambda obj, **kws: obj.queue.__class__.__name__,
        'running': lambda obj, since, **kws:
            obj.instances.since(since).status_in('running').count(),
        'succeeded': lambda obj, since, **kws:
            obj.instances.since(since).status_in('succeeded').count(),
        'failed': lambda obj, since, **kws:
            obj.instances.since(since).status_in('failed').count(),
        'status': lambda obj, **kws: Status.name(obj.status),
        'ended': date_ended_getter,
        'heartbeat': lambda obj, **kws: obj.heartbeat,
        'alive': lambda obj, **kws: str(obj.is_alive()),
    }
    

class schedulers(BaseReport):
    
    get = lambda id: get_object(Scheduler, id=id)
    get_all = lambda: Scheduler.objects.all()
    
    since_filter = date_ended_since
    order_by = lambda data, o: data.order_by(o if o else '-started')
    
    details = {
        'schedules': lambda id, **kws:
            Schedule.objects.filter(scheduler__id=id)
    }
    headers = ['ID', 'Host', "PID", "Claimed", 'Started', 'Ended', "Status"]
    data = {
        "claimed": lambda obj, **kws:
            obj.schedules.count() + obj.cronschedules.count(),
        'ended': date_ended_getter,    
        'alive': lambda obj, **kws: str(obj.is_alive()),
        'status': lambda obj, **kws: Status.name(obj.status),
    }

# def _queue_failure_rate(obj, **kws):
#     instances = MultiQuerySet(*[i.objects.all() for i in INSTANCE_MODELS])
#     instances = instances.from_queue(obj)
#     failed = instances.status_in('failed').count()
#     total = instances.count()
#     return '%.2f%%' % (100.0 * failed / total) if total > 0 else 'n/a'

class queues(BaseReport):
    
    get = Queue.get
    get_all = Queue.all_queues
    order_by = lambda data, o: sorted(data, key=lambda v: v.name)
    
    headers = ['Name', 'Type', 'Items', 'Executors']
    data = {
        'type': lambda obj, **kws: type(obj).__name__,
        'items': lambda obj, **kws: obj.count(),
        'executors': lambda obj, **kws:
            Executor.objects.for_queue(obj).alive().count(),
        # 'failure_rate': _queue_failure_rate,
    }

class tasks(BaseReport):
    
    get_all = lambda: reduce(lambda a, b: a + b,
        [[t for t in TaskClass.objects.all()] for TaskClass in TASK_MODELS])
    
    details = {
        'instances': lambda id, **kws: _parse_content_ids(id).instances.all(),
    }
    headers = ['Name', 'Type', 'Description', 'Added', 'Timeout', 'Instances']
    data = {
        'id': lambda obj, **kws: '%s_%s' %
            (ContentType.objects.get_for_model(obj).id, obj.id),
        'name': lambda obj, **kws: obj.get_name(),
        'type': lambda obj, **kws: type(obj).__name__,
        'added': lambda obj, **kws: obj.date_added,
        'instances': lambda obj, **kws: obj.instances.count(),
    }

class instances(BaseReport):
    
    get = _parse_content_ids
    get_all = lambda: MultiQuerySet(*[i.objects.all()
        for i in INSTANCE_MODELS])
    since_filter = date_ended_since
    order_by = date_ended_order
    
    headers = ['ID#', 'Type', 'Source', 'Started', 'Ended', 'Status']
    data = {
        'id': lambda obj, **kws: '%s_%s' %
            (ContentType.objects.get_for_model(obj).id, obj.id),
        'id#': lambda obj, **kws: obj.id,
        'type': lambda obj, **kws: type(obj).__name__,
        'source': lambda i, **kws: i.source or 'n/a',
            # i.source if hasattr(i, 'source') else 'n/a',
        'status': lambda obj, **kws: Status.name(obj.status),
    }

class task_classes(BaseReport):
    
    get = lambda name: filter(lambda t: t.__name__ == name, TASK_MODELS)[0]
    get_all = lambda: TASK_MODELS
    
    headers = ['Task', 'Objects']
    data = {
        'task': lambda task, **kws: task.__name__,
        'objects': lambda task, **kws: task.objects.count(),
    }

########NEW FILE########
__FILENAME__ = executor_test

"""Module for testing anything related to executors."""

import os
from threading import Thread

from django.test import TestCase

from norc.core.models import Executor, DBQueue, CommandTask, Instance
from norc.core.constants import Status, Request
from norc.norc_utils import wait_until, log

class ExecutorTest(TestCase):
    """Tests for a Norc executor."""
    
    @property
    def executor(self):
        return Executor.objects.get(pk=self._executor.pk)
    
    def setUp(self):
        """Create the executor and thread objects."""
        self.queue = DBQueue.objects.create(name='test')
        self._executor = Executor.objects.create(queue=self.queue, concurrent=4)
        self._executor.log = log.Log(os.devnull)
        self.thread = Thread(target=self._executor.start)
    
    def test_start_stop(self):    
        self.assertEqual(self.executor.status, Status.CREATED)
        self.thread.start()
        wait_until(lambda: self.executor.status == Status.RUNNING, 3)
        self.assertEqual(self.executor.status, Status.RUNNING)
        self.executor.make_request(Request.STOP)
        wait_until(lambda: Status.is_final(self.executor.status), 5)
        self.assertEqual(self.executor.status, Status.ENDED)
        
    def test_kill(self):
        self.thread.start()
        wait_until(lambda: self.executor.status == Status.RUNNING, 3)
        self.assertEqual(self.executor.status, Status.RUNNING)
        self.executor.make_request(Request.KILL)
        wait_until(lambda: Status.is_final(self.executor.status), 5)
        self.assertEqual(self.executor.status, Status.KILLED)
    
    def test_pause_resume(self):
        self.thread.start()
        wait_until(lambda: self.executor.status == Status.RUNNING, 3)
        self.assertEqual(self.executor.status, Status.RUNNING)
        self.executor.make_request(Request.PAUSE)
        wait_until(lambda: self.executor.status == Status.PAUSED, 5)
        self.assertEqual(self.executor.status, Status.PAUSED)
        self.executor.make_request(Request.RESUME)
        wait_until(lambda: self.executor.status == Status.RUNNING, 5)
        self.assertEqual(self.executor.status, Status.RUNNING)
    
    # This test does not work because of an issue with subprocesses using
    # the Django test database.
    
    # def test_run_instance(self):
    #     self.thread.start()
    #     ct = CommandTask.objects.create(name='test', command='echo "blah"')
    #     _instance = Instance.objects.create(task=ct, executor=self._executor)
    #     instance = lambda: Instance.objects.get(pk=_instance.pk)
    #     wait_until(lambda: self.executor.status == Status.RUNNING, 3)
    #     self.queue.push(_instance)
    #     wait_until(lambda: Status.is_final(instance().status), 5)
    #     self.assertEqual(instance().status, Status.SUCCESS)
    
    def tearDown(self):
        if not Status.is_final(self._executor.status):
            print self._executor.make_request(Request.KILL)
        self.thread.join(7)
        self._executor.heart.join(7)
        assert not self.thread.isAlive()
        assert not self._executor.heart.isAlive()

########NEW FILE########
__FILENAME__ = job_test

""""""

import os
import unittest
import re
from threading import Thread

from django.test import TestCase

from norc.core.models import Job, JobNode, Dependency, Instance, Schedule
from norc.norc_utils import wait_until, log, testing

class JobTest(TestCase):
    
    def queue_items(self):
        items = []
        while self.queue.count() > 0:
            items.append(self.queue.pop())
        return items
    
    def _start_instance(self, instance):
        try:
            instance.start()
        except SystemExit:
            pass
    
    def setUp(self):
        self.queue = testing.make_queue()
        self.tasks = [testing.make_task('JobTask%s' % i) for i in range(6)]
        self.job = Job.objects.create(name='TestJob')
        self.nodes = [JobNode.objects.create(task=self.tasks[i], job=self.job)
            for i in range(6)]
        n = self.nodes
        Dependency.objects.create(parent=n[0], child=n[2])
        Dependency.objects.create(parent=n[0], child=n[3])
        Dependency.objects.create(parent=n[1], child=n[4])
        Dependency.objects.create(parent=n[2], child=n[3])
        Dependency.objects.create(parent=n[2], child=n[5])
        Dependency.objects.create(parent=n[3], child=n[5])
        Dependency.objects.create(parent=n[4], child=n[5])
    
    def test_job(self):
        schedule = Schedule.create(self.job, self.queue, 1)
        instance = Instance.objects.create(task=self.job, schedule=schedule)
        # instance.log = log.Log(os.devnull)
        self.thread = Thread(target=instance.start)
        self.thread.start()
        wait_until(lambda: self.queue.count() == 2, 2)
        self.assertEqual(set([i.item.node for i in self.queue.items.all()]),
            set([self.nodes[0], self.nodes[1]]))
        for i in self.queue_items():
            self._start_instance(i)
        self.assertEqual(set([i.item.node for i in self.queue.items.all()]),
            set([self.nodes[2], self.nodes[4]]))
        for i in self.queue_items():
            self._start_instance(i)
        self.assertEqual(set([i.item.node for i in self.queue.items.all()]),
            set([self.nodes[3]]))
        for i in self.queue_items():
            self._start_instance(i)
        self.assertEqual(set([i.item.node for i in self.queue.items.all()]),
            set([self.nodes[5]]))
        for i in self.queue_items():
            self._start_instance(i)
        self.thread.join(2)
        self.assertFalse(self.thread.isAlive())
    

########NEW FILE########
__FILENAME__ = queue_test

from django.test import TestCase

from norc.core.models import DBQueue, QueueGroup, QueueGroupItem, Instance
from norc.norc_utils import wait_until
from norc.norc_utils.testing import *

class DBQueueTest(TestCase):
    """Super simple test that pushes and pops something from the queue."""
    
    def setUp(self):
        self.queue = DBQueue.objects.create(name='test')
        self.item = make_instance()
    
    def test_push_peek_pop(self):
        self.queue.push(self.item)
        self.assertEqual(self.queue.peek(), self.item)
        self.assertEqual(self.queue.pop(), self.item)
    
    def test_invalid(self):
        self.assertRaises(AssertionError, lambda: self.queue.push(self.queue))
    
    def tearDown(self):
        pass
    

class QueueGroupTest(TestCase):
    """Tests and demonstrates the usage of QueueGroups."""
    
    def setUp(self):
        self.group = g = QueueGroup.objects.create(name='TestGroup')
        self.q1 = DBQueue.objects.create(name="Q1")
        self.q2 = DBQueue.objects.create(name="Q2")
        self.q3 = DBQueue.objects.create(name="Q3")
        QueueGroupItem.objects.create(group=g, queue=self.q1, priority=1)
        QueueGroupItem.objects.create(group=g, queue=self.q2, priority=2)
        QueueGroupItem.objects.create(group=g, queue=self.q3, priority=3)
        self.task = make_task()
    
    def new_instance(self):
        return Instance.objects.create(task=self.task)
    
    def test_push_peek_pop(self):
        """Test that all three queues work."""
        item = self.new_instance()
        self.q1.push(item)
        self.assertEqual(self.group.peek(), item)
        self.assertEqual(self.group.pop(), item)
        self.q2.push(item)
        self.assertEqual(self.group.peek(), item)
        self.assertEqual(self.group.pop(), item)
        self.q3.push(item)
        self.assertEqual(self.group.peek(), item)
        self.assertEqual(self.group.pop(), item)
    
    def test_priority(self):
        """Test that things get popped in priority order."""
        p1 = [self.new_instance() for _ in range(10)]
        p2 = [self.new_instance() for _ in range(10)]
        p3 = [self.new_instance() for _ in range(10)]
        for i in p3: self.q3.push(i)
        for i in p2: self.q2.push(i)
        for i in p1: self.q1.push(i)
        popped = [self.group.pop() for _ in range(30)]
        self.assertEqual(popped, p1 + p2 + p3)
    
    def test_no_push(self):
        """Test that pushing to a QueueGroup fails."""
        self.assertRaises(NotImplementedError, lambda: self.group.push(None))
    
    def tearDown(self):
        pass
    

########NEW FILE########
__FILENAME__ = s3_test

"""Module for testing anything related to executors."""

import os
from threading import Thread

from django.test import TestCase

from norc.core.models import Executor, DBQueue, CommandTask, Instance
from norc.core.constants import Status
from norc.norc_utils import wait_until, log

class ExecutorTest(TestCase):
    """Tests for a Norc executor."""
    
    def setUp(self):
        """Create the executor and thread objects."""
        self.queue = DBQueue.objects.create(name='test')
        self._executor = Executor.objects.create(queue=self.queue, concurrent=4)
        self._executor.log = log.Log(os.devnull)
        self.thread = Thread(target=self._executor.start)
    
    def test_start_stop(self):    
        pass
    
    def tearDown(self):
        pass
    

########NEW FILE########
__FILENAME__ = scheduler_test

"""Test schedule handling cases in the SchedulableTask class."""

import os, sys
from threading import Thread
from datetime import timedelta, datetime

from django.test import TestCase

from norc.core.models import Scheduler, Schedule, CronSchedule
from norc.core.constants import Status, Request
from norc.norc_utils import wait_until, log
from norc.norc_utils.testing import make_queue, make_task

class SchedulerTest(TestCase):
    
    @property
    def scheduler(self):
        return Scheduler.objects.get(pk=self._scheduler.pk)
    
    def setUp(self):
        self._scheduler = Scheduler.objects.create()
        self._scheduler.log = log.Log(os.devnull)
        self.thread = Thread(target=self._scheduler.start)
        self.thread.start()
        wait_until(lambda: self.scheduler.is_alive(), 3)
    
    def test_stop(self):
        self.scheduler.make_request(Request.STOP)
        self._scheduler.flag.set()
        wait_until(lambda: not self.scheduler.is_alive(), 3)
    
    def test_schedule(self):
        task = make_task()
        queue = make_queue()
        s = Schedule.create(task, queue, 0, 5)
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 5, 5)
    
    def test_cron(self):
        task = make_task()
        queue = make_queue()
        s = CronSchedule.create(task, queue, 'o*d*w*h*m*s*', 3)
        self._scheduler.flag.set()
        wait_until(lambda: queue.count() == 3, 8)
        enqueued = map(lambda i: i.enqueued, s.instances)
        def fold(acc, e):
            self.assertEqual(e - acc, timedelta(seconds=1))
            return e
        reduce(fold, enqueued)
    
    def test_update_schedule(self):
        task = make_task()
        queue = make_queue()
        s = CronSchedule.create(task, queue, 'o*d*w*h*m*s*', 10)
        self._scheduler.flag.set()
        wait_until(lambda: queue.count() == 2, 5)
        s.encoding = 'o*d*w*h*m*s4'
        s.save()
        self.assertRaises(Exception,
            lambda: wait_until(lambda: s.instances.count() > 3, 3))
    
    def test_make_up(self):
        task = make_task()
        queue = make_queue()
        s = Schedule.create(task, queue, 1, 10, -10, True)
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 10, 5)
        s = Schedule.create(task, queue, 60, 10, -10, False)
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 1, 5)
    
    def test_cron_make_up(self):
        task = make_task()
        queue = make_queue()
        now = datetime.utcnow()
        s = CronSchedule(encoding='o*d*w*h*m*s%s' % ((now.second - 1) % 60),
            task=task, queue=queue, repetitions=0, remaining=0, make_up=False)
        s.base = now - timedelta(seconds=2)
        s.save()
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 1, 3)
        
        now = datetime.utcnow()
        s = CronSchedule(encoding='o*d*w*h*m*s*',
            task=task, queue=queue, repetitions=0, remaining=0, make_up=True)
        s.base = now - timedelta(seconds=5)
        s.save()
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 6, 1)
    
    def test_reload(self):
        task = make_task()
        queue = make_queue()
        now = datetime.utcnow()
        s = CronSchedule.create(task, queue, 'o*d*w*h*m*s%s' %
            ((now.second - 1) % 60), 1)
        self._scheduler.flag.set()
        wait_until(lambda: self.scheduler.cronschedules.count() == 1, 5)
        CronSchedule.objects.get(pk=s.pk).reschedule('o*d*w*h*m*s*')
        self.scheduler.make_request(Request.RELOAD)
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 1, 10)
    
    def test_duplicate(self):
        task = make_task()
        queue = make_queue()
        s = Schedule.create(task, queue, 1, 2, start=2)
        self._scheduler.flag.set()
        wait_until(lambda: self.scheduler.schedules.count() == 1, 2)
        s = Schedule.objects.get(pk=s.pk)
        s.scheduler = None
        s.save()
        self._scheduler.flag.set()
        wait_until(lambda: s.instances.count() == 2, 5)
    
    def test_bad_schedule(self):
        task = make_task()
        queue = make_queue()
        s = CronSchedule.create(task, queue, "o*d*w*h*m*s*")
        s.encoding = "gibberish"
        s.save()
        self._scheduler.flag.set()
        wait_until(lambda: CronSchedule.objects.get(pk=s.pk).deleted, 2)
    
    #def test_stress(self):
    #    task = make_task()
    #    queue = make_queue()
    #    for i in range(5000):
    #        CronSchedule.create(task, queue, 'HALFHOURLY')
    #    self._scheduler.flag.set()
    #    wait_until(lambda: self._scheduler.cronschedules.count() == 5000, 60)
    
    def tearDown(self):
        if not Status.is_final(self._scheduler.status):
            self._scheduler.make_request(Request.KILL)
        self.thread.join(15)
        assert not self.thread.isAlive()
        assert not self._scheduler.timer.isAlive()
    

########NEW FILE########
__FILENAME__ = schedule_test

"""Test schedule handling cases in the SchedulableTask class."""

import unittest
import re

from django.test import TestCase

from norc.core.models import CommandTask, DBQueue, Schedule, CronSchedule
from norc.norc_utils import wait_until, log

# class ScheduleTest(TestCase):
#     
#     def setUp(self):
#         pass
#     
#     def test_run_schedule(self):
#         pass
    

class CronScheduleTest(TestCase):
    
    def setUp(self):
        self.t = CommandTask.objects.create(
            name='TestTask', command='echo "Testing, 1, 2, 3."')
        self.q = DBQueue.objects.create(name='Test')
        # self.cron = CronSchedule.create(self.t, self.q, 'WEEKLY')
    
    def test_validate(self):
        v = lambda s: CronSchedule.validate(s)[0]
        self.assertEqual(v('o1d1w1h1m1s1'), 'o1d1w1h1m1s1')
        self.assertTrue(re.match(r'^o\*d\*w\*h\*m\*s\d+$', v('')))
        self.assertEqual(v('d1w1h1m1s1'), 'o*d1w1h1m1s1')
        self.assertEqual(v(' d 1 , 2 s 1 '), 'o*d1,2w*h*m*s1')
        
        self.assertRaises(AssertionError, lambda: v('adf'))
        self.assertRaises(AssertionError, lambda: v('o1,13'))
    
    def test_pretty_name(self):
        make = lambda p: CronSchedule.create(self.t, self.q, p)
        self.assertEqual(make('HALFHOURLY').pretty_name(), 'HALFHOURLY')
        self.assertEqual(make('HOURLY').pretty_name(), 'HOURLY')
        self.assertEqual(make('DAILY').pretty_name(), 'DAILY')
        self.assertEqual(make('WEEKLY').pretty_name(), 'WEEKLY')
        self.assertEqual(make('MONTHLY').pretty_name(), 'MONTHLY')
    

########NEW FILE########
__FILENAME__ = task_test

"""Module for testing CommandTasks."""

import os, sys
import time

from django.test import TestCase

from norc.core.models import CommandTask, Instance, Revision
from norc.core.constants import Status
from norc.norc_utils import log

class TestTask(TestCase):
    """Tests for Norc tasks."""
    
    def run_task(self, task):
        if type(task) == str:
            task = CommandTask.objects.create(name=task, command=task)
        return self.run_instance(Instance.objects.create(task=task)).status
    
    def run_instance(self, instance):
        instance.log = log.Log(os.devnull, echo=True)
        try:
            instance.start()
        except SystemExit:
            pass
        return Instance.objects.get(pk=instance.pk)
    
    def disarm(self, instance):
        """Have to soften _nuke sometimes or the test process will die."""
        def _nuke():
            sys.exit(1)
        instance._nuke = _nuke
    
    def test_success(self):
        """Tests that a task can end with status SUCCESS."""
        self.assertEqual(Status.SUCCESS, self.run_task('echo "Success!"'))
    
    def test_failure(self):
        """Tests that a task can end with status FAILURE."""
        self.assertEqual(Status.FAILURE, self.run_task('exit 1'))
        self.assertEqual(Status.FAILURE, self.run_task('asd78sad7ftaoq'))
    
    def test_timeout(self):
        "Tests that a task can end with status TIMEDOUT."
        task = CommandTask.objects.create(
            name='Timeout', command='sleep 5', timeout=1)
        instance = Instance.objects.create(task=task)
        self.disarm(instance)
        self.assertEqual(Status.TIMEDOUT, self.run_instance(instance).status)
    
    def test_finally(self):
        task = CommandTask.objects.create(name='Nothing', command='sleep 0')
        instance = Instance.objects.create(task=task)
        self.disarm(instance)
        def finally_():
            instance.status = Status.ERROR
        instance.finally_ = finally_
        self.assertEqual(Status.ERROR, self.run_instance(instance).status)
    
    def test_finally_timeout(self):
        t = CommandTask.objects.create(name='Nothing', command='sleep 0')
        instance = Instance.objects.create(task=t)
        self.disarm(instance)
        from norc.core.models import task
        task.FINALLY_TIMEOUT = 1
        def finally_():
            import time
            time.sleep(2)
        instance.finally_ = finally_
        self.assertEqual(Status.TIMEDOUT, self.run_instance(instance).status)
    
    def test_double_timeout(self):
        """Tests a task timing out and then its final block timing out.
        
        NOTE: because the "nuking" of the process can't occur in a test
        environment, this test actually results in the final clause being
        run twice.  This won't happen in a real setting because _nuke()
        is aptly named.
        
        """
        t = CommandTask.objects.create(
            name='Nothing', command='sleep 2', timeout=1)
        instance = Instance.objects.create(task=t)
        self.disarm(instance)
        from norc.core.models import task
        task.FINALLY_TIMEOUT = 1
        def finally_():
            import time
            time.sleep(2)
        instance.finally_ = finally_
        self.assertEqual(Status.TIMEDOUT, self.run_instance(instance).status)
    
    def test_nameless(self):
        "Tests that a task can be nameless."
        t = CommandTask.objects.create(command="echo 'Nameless!'")
        self.assertEqual(Status.SUCCESS, self.run_task(t))

    def test_revisions(self):
        r = Revision.objects.create(info="rev")
        t = CommandTask.objects.create(command="ls")
        i = Instance.objects.create(task=t)
        i.get_revision = lambda: r
        self.assertEqual(r, self.run_instance(i).revision)

########NEW FILE########
__FILENAME__ = defaults

import os

# Norc's directory (assumed to be the parent folder of this file).
NORC_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
# The path to Norc on GitHub.
NORC_CODE_ROOT = 'git://github.com/darrellsilver/norc.git'

class Envs(type):
    """Meta class that collects a list of all implementations of BaseEnv."""
    
    ALL = {}
    
    def __init__(cls, name, bases, dct):
        super(Envs, cls).__init__(name, bases, dct)
        Envs.ALL[name] = cls
    
    def __getitem__(self, attr):
        """Allows dictionary-style lookup of attributes."""
        return getattr(self, attr)

class BaseEnv(object):
    """Basic Norc setting defaults.
    
    This serves as a base class from which specific environments
    classes can inherit default settings.  Not meant to be instantiated.
    
    """
    __metaclass__ = Envs
    
    # Norc settings.
    NORC_LOG_DIR = os.path.join(NORC_DIRECTORY, 'log/')
    NORC_TMP_DIR = os.path.join(NORC_DIRECTORY, 'tmp/')
    BACKUP_SYSTEM = None
    # See core/reports.py for options.
    STATUS_TABLES = ['executors', 'queues', 'schedulers', 'tasks']
    EXTERNAL_CLASSES = [];
    
    # Important Django settings.
    ADMINS = ()
    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'norc.core',
        'norc.web',
    )
    MIDDLEWARE_CLASSES = (
        'django.middleware.gzip.GZipMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'norc.middleware.ErrorHandlingMiddleware',
    )
    
    # Database configuration.
    DATABASE_ENGINE = 'mysql'
    # Name and user MUST be overwritten by a local environment!
    DATABASE_NAME = ''
    DATABASE_USER = ''
    DATABASE_HOST = 'localhost'
    DATABASE_PORT = '3306'
    
    # Email configuration; commented out for future use.
    # EMAIL_HOST = 'smtp.gmail.com'
    # EMAIL_HOST_USER = ''
    # EMAIL_PORT = '587'
    # EMAIL_USE_TLS = 'True'
    
    # Debugging switches.
    DEBUG = False
    LOGGING_DEBUG = False
    TEMPLATE_DEBUG = False
    
    # Miscellaneous Django settings.
    INTERNAL_IPS = ('127.0.0.1',)
    MEDIA_ROOT = os.path.join(NORC_DIRECTORY, 'static/')
    ROOT_URLCONF = 'norc.urls'
    SITE_ID = 1
    TEMPLATE_DIRS = ()
    TIME_ZONE = 'America/New-York'

########NEW FILE########
__FILENAME__ = schedule_conversion

"""Simple function for converting schedules.

The old Norc had SchedulableTask objects, which were tasks with a schedule.
This function takes that, a new-style task and a queue and creates a
CronSchedule out of them.

"""

import random
from norc.core.models import CronSchedule

def convert_schedule(st, task, queue):
    o = st.month if st.__month_r__ != CronSchedule.MONTHS else '*'
    d = st.day_of_month if st.__day_of_month_r__ != CronSchedule.DAYS else '*'
    w = st.day_of_week if st.__day_of_week_r__ != CronSchedule.DAYSOFWEEK else '*'
    h = st.hour if st.__hour_r__ != CronSchedule.HOURS else '*'
    m = st.minute if st.__minute_r__ != CronSchedule.MINUTES else '*'
    s = random.choice(CronSchedule.SECONDS)
    encoding = 'o%sd%sw%sh%sm%ss%s' % (o, d, w, h, m, s)
    return CronSchedule.create(task, queue, encoding)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from django.core.management import execute_manager

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write(
"""Error: Can't find the file 'settings.py' in the directory containing %r. \
It appears you've customized things.You'll have to run django-admin.py, \
passing it your settings module.(If the file settings.py does indeed exist, \
it's causing an ImportError somehow.)\n""" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = middleware
import traceback
from django.http import HttpResponseServerError
from django.template.loader import render_to_string
from django.shortcuts import render_to_response

class StaffOnlyMiddleware(object):
    def process_request(self, request):
        if not request.path.startswith('/admin'):
            if not request.user.is_staff:
                return render_to_response('404.html')

class ErrorHandlingMiddleware(object):
    def process_exception(self, request, exception):
        if request.is_ajax():
            return HttpResponseServerError(traceback.format_exc(),
                content_type='text/plain')
        # else:
        #     return HttpResponseServerError(render_to_string('500.html',
        #         dict(message=traceback.format_exc())))

########NEW FILE########
__FILENAME__ = aws

import zlib

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from norc.settings import (NORC_LOG_DIR, BACKUP_SYSTEM,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME)

def get_s3_connection():
    return S3Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

def get_s3_bucket(name=AWS_BUCKET_NAME):
    c = get_s3_connection()
    b = c.get_bucket(name)
    if not b:
        b = c.create_bucket(AWS_BUCKET_NAME)
    return b

def set_s3_key(key, contents):
    k = Key(get_s3_bucket())
    k.key = key
    if not isinstance(contents, basestring):
        contents = contents.read()
    k.set_contents_from_string(zlib.compress(contents, 9))

def get_s3_key(key, target=None):
    k = Key(get_s3_bucket())
    k.key = key
    contents = k.get_contents_as_string()
    try:
        contents = zlib.decompress(contents)
    except zlib.error:
        pass
    if target:
        target.write(contents)
    else:
        return contents


########NEW FILE########
__FILENAME__ = backup

import os

from norc.settings import NORC_LOG_DIR, BACKUP_SYSTEM

if BACKUP_SYSTEM == 'AmazonS3':
    from norc.norc_utils.aws import set_s3_key
    from norc.settings import (AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME)


def s3_backup(fp, target):
    NUM_TRIES = 3
    for i in range(NUM_TRIES):
        try:
            set_s3_key(target, fp)
            return True
        except:
            if i == NUM_TRIES - 1:
                raise
    return False

BACKUP_SYSTEMS = {
    'AmazonS3': s3_backup,
}

def backup_log(rel_log_path):
    log_path = os.path.join(NORC_LOG_DIR, rel_log_path)
    log_file = open(log_path, 'rb')
    target = os.path.join('norc_logs/', rel_log_path)
    try:
        return _backup_file(log_file, target)
    finally:
        log_file.close()

def _backup_file(fp, target):
    if BACKUP_SYSTEM:
        return BACKUP_SYSTEMS[BACKUP_SYSTEM](fp, target)
    else:
        return False

########NEW FILE########
__FILENAME__ = django_extras

"""Utilities that extend Django functionality."""

import itertools

from django.db.models import Manager

# Replaced in Django 1.2 by QuerySet.exists()
def queryset_exists(q):
    """Efficiently tests whether a queryset is empty or not."""
    try:
        q[0]
        return True
    except IndexError:
        return False

def get_object(model, **kwargs):
    """Retrieves a database object of the given class and attributes.
    
    model is the class of the object to find.
    kwargs are the parameters used to find the object.
    If no object is found, returns None.
    
    """
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None

def update_obj(obj):
    return type(obj).objects.get(pk=obj.pk)

class QuerySetManager(Manager):
    """
    
    This Manager uses a QuerySet class defined within its model and
    will forward attribute requests to it so you only have to
    define custom attributes in one place.
    
    """
    use_for_related_fields = True
    
    def get_query_set(self):
        """Use the model.QuerySet class."""
        return self.model.QuerySet(self.model)
    
    def __getattr__(self, attr, *args):
        """Forward attribute lookup to the QuerySet."""
        return getattr(self.get_query_set(), attr, *args)
    

class MultiQuerySet(object):
    
    def __init__(self, *args):
        self.querysets = args
    
    def count(self):
        return sum(qs.count() for qs in self.querysets)
    
    def __len__(self):
        return self.count()
    
    def __getitem__(self, item):
        indices = (offset, stop, step) = item.indices(self.count())
        items = []
        total_len = stop - offset
        for qs in self.querysets:
            if len(qs) < offset:
                offset -= len(qs)
            else:
                items += list(qs[offset:stop])
                if len(items) >= total_len:
                    return items
                else:
                    offset = 0
                    stop = total_len - len(items)
                    continue
    
    def __iter__(self):
        return itertools.chain(*self.querysets)
    
    def __call__(self, *args, **kwargs):
        """Call each queryset."""
        return MultiQuerySet(*[qs(*args, **kwargs) for qs in self.querysets])
    
    def __getattr__(self, attr, *args):
        """Get the attribute for each queryset."""
        return MultiQuerySet(*[getattr(qs, attr, *args)
            for qs in self.querysets])
    
    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.querysets)
########NEW FILE########
__FILENAME__ = formatting

import locale
locale.setlocale(locale.LC_NUMERIC, "")

def format_num(num):
    """Format a number according to given places.
    Adds commas, etc. Will truncate floats into ints!"""

    try:
        inum = int(num)
        return locale.format("%.*f", (0, inum), True)

    except (ValueError, TypeError):
        return str(num)

def get_max_width(table, index):
    """Get the maximum width of the given column index"""

    return max([len(format_num(row[index])) for row in table])

def pprint_table(out, table):
    """Prints out a table of data, padded for alignment
    @param out: Output stream (file-like object)
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns. """

    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # left col
        print >> out, row[0].ljust(col_paddings[0] + 1),
        # rest of the cols
        for i in range(1, len(row)):
            col = format_num(row[i]).rjust(col_paddings[i] + 2)
            print >> out, col,
        print >> out

def to_title(s):
    return ' '.join(map(lambda w: w.capitalize(), s.split('_')))

def untitle(s):
    return '_'.join([t.lower() for t in s.split(' ')])

if __name__ == "__main__":
    table = [["", "taste", "land speed", "life"],
        ["spam", 300101, 4, 1003],
        ["eggs", 105, 13, 42],
        ["lumberjacks", 13, 105, 10]]

    import sys
    out = sys.stdout
    pprint_table(out, table)

########NEW FILE########
__FILENAME__ = log

"""General logging utilities."""

import os
import sys
import datetime
import traceback

from norc.settings import (LOGGING_DEBUG, NORC_LOG_DIR)

def timestamp():
    """Returns a string timestamp of the current time."""
    now = datetime.datetime.utcnow()
    return now.strftime('%Y/%m/%d %H:%M:%S') + '.%06d' % now.microsecond

class LogHook(object):
    """A pseudo file class meant to be set as stdout to intercept writes."""
    
    def __init__(self, log):
        self.log = log
    
    def write(self, string):
        self.log.write(string, False)
    
    def writelines(seq):
        for s in seq:
            self.write(s)
    
    def flush(self):
        pass
    
    def fileno(self):
        return self.log.file.fileno()
    

class AbstractLog(object):
    """Abstract class for creating a text log."""
    
    INFO = 'INFO'
    ERROR = 'ERROR'
    DEBUG = 'DEBUG'
    
    @staticmethod
    def format(msg, prefix):
        """The format of all log messages."""
        return '[%s] %s: %s\n' % (timestamp(), prefix, msg)
    
    def __init__(self, debug):
        """Initialize a Log object.
        
        If debug is not given, it defaults to the
        LOGGING_DEBUG setting of Norc.
        
        """
        self.debug_on = debug if debug != None else LOGGING_DEBUG
    
    def info(self, msg):
        """Log some informational message."""
        raise NotImplementedError
    
    def error(self, msg, trace):
        """Log about an error that occurred, with optional stack trace."""
        raise NotImplementedError
    
    def debug(self, msg):
        """Message for debugging purposes; only log if debug is true."""
        raise NotImplementedError
    

class Log(AbstractLog):
    """Implementation of Log that sends logs to a file."""
    
    def __init__(self, log_file, debug=None, echo=False):
        """ Parameters:
        
        path    Path to the file that all output should go in.
        debug   Boolean; whether debug output should be logged.
        echo    Echoes all logging to stdout if True.
        
        """
        AbstractLog.__init__(self, debug)
        if not isinstance(log_file, file):
            if not os.path.isdir(os.path.dirname(log_file)):
                os.makedirs(os.path.dirname(log_file))
            log_file = open(log_file, 'a')
        self.file = log_file
        self.echo = echo
    
    def write(self, msg, format_prefix):
        if format_prefix:
            msg = Log.format(msg, format_prefix)
        self.file.write(msg)
        self.file.flush()
        if self.echo:
            print >>sys.__stdout__, msg,
    
    def info(self, msg, format=True):
        self.write(msg, Log.INFO if format else False)
    
    def error(self, msg, trace=False, format=True):
        self.write(msg, Log.ERROR if format else False)
        if trace:
            self.write(traceback.format_exc(), False)
    
    def debug(self, msg, format=True):
        if self.debug_on:
            self.write(msg, Log.DEBUG if format else False)
    
    def start_redirect(self):
        """Redirect all stdout and stderr to this log's files."""
        sys.stdout = sys.stderr = LogHook(self)
    
    def stop_redirect(self):
        """Restore stdout and stderr to their original values."""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
    
    def close(self):
        self.file.close()
    

def make_log(norc_path, *args, **kwargs):
    """Make a log object with a subpath of the norc log directory."""
    return Log(os.path.join(NORC_LOG_DIR, norc_path), *args, **kwargs)
    # log_class = BACKUP_LOGS.get(BACKUP_SYSTEM, NorcLog)
    # return log_class(norc_path, *args, **kwargs)
    

########NEW FILE########
__FILENAME__ = parallel

from __future__ import division

import time
from datetime import datetime, timedelta
from threading import Thread, Event, RLock
from heapq import heappop, heappush
import traceback

def total_secs(td):
    assert type(td) == timedelta
    return (td.microseconds +
        (td.seconds + td.days * 24 * 3600) * 10**6) / float(10**6)

class MultiTimer(Thread):
    """A timer implementation that can handle multiple tasks at once."""
    
    def __init__(self):
        Thread.__init__(self)
        self.tasks = [] # SortedList(reverse=True)
        self.cancelled = False
        self.interrupt = Event()
    
    def run(self):
        while not self.cancelled:
            if len(self.tasks) == 0:
                self.interrupt.wait()
                self.interrupt.clear()
            else:
                self.interrupt.wait(self.tasks[0][0] - time.time())
                if not self.interrupt.isSet():
                    func, args, kwargs = heappop(self.tasks)[1:]
                    # self.tasks.pop()
                    # assert item == self.tasks.pop()
                    try:
                        func(*args, **kwargs)
                    except Exception:
                        traceback.print_exc()
                else:
                    self.interrupt.clear()
    
    def cancel(self):
        self.cancelled = True
        self.interrupt.set()
    
    def add_task(self, delay, func, args=[], kwargs={}):
        if type(delay) == datetime:
            now = datetime.utcnow()
            delay = delay - now if now < delay else 0
        if type(delay) == timedelta:
            delay = total_secs(delay)
        delay += time.time()
        item = (delay, func, args, kwargs)
        heappush(self.tasks, item)
        # self.tasks.add(item)
        if item == self.tasks[0]: # .peek():
            self.interrupt.set()
    

## {{{ http://code.activestate.com/recipes/203871/ (r3)
import threading
from time import sleep

class ThreadPool:

    """Flexible thread pool class.  Creates a pool of threads, then
    accepts tasks that will be dispatched to the next available
    thread."""
    
    def __init__(self, numThreads):

        """Initialize the thread pool with numThreads workers."""
        
        self.__threads = []
        self.__resizeLock = threading.Condition(threading.Lock())
        self.__taskLock = threading.Condition(threading.Lock())
        self.__tasks = []
        self.__isJoining = False
        self.setThreadCount(numThreads)

    def setThreadCount(self, newNumThreads):

        """ External method to set the current pool size.  Acquires
        the resizing lock, then calls the internal version to do real
        work."""
        
        # Can't change the thread count if we're shutting down the pool!
        if self.__isJoining:
            return False
        
        self.__resizeLock.acquire()
        try:
            self.__setThreadCountNolock(newNumThreads)
        finally:
            self.__resizeLock.release()
        return True

    def __setThreadCountNolock(self, newNumThreads):
        
        """Set the current pool size, spawning or terminating threads
        if necessary.  Internal use only; assumes the resizing lock is
        held."""
        
        # If we need to grow the pool, do so
        while newNumThreads > len(self.__threads):
            newThread = ThreadPoolThread(self)
            self.__threads.append(newThread)
            newThread.start()
        # If we need to shrink the pool, do so
        while newNumThreads < len(self.__threads):
            self.__threads[0].goAway()
            del self.__threads[0]

    def getThreadCount(self):

        """Return the number of threads in the pool."""
        
        self.__resizeLock.acquire()
        try:
            return len(self.__threads)
        finally:
            self.__resizeLock.release()

    def queueTask(self, task, args=None, taskCallback=None):

        """Insert a task into the queue.  task must be callable;
        args and taskCallback can be None."""
        
        if self.__isJoining == True:
            return False
        if not callable(task):
            return False
        
        self.__taskLock.acquire()
        try:
            self.__tasks.append((task, args, taskCallback))
            return True
        finally:
            self.__taskLock.release()

    def getNextTask(self):

        """ Retrieve the next task from the task queue.  For use
        only by ThreadPoolThread objects contained in the pool."""
        
        self.__taskLock.acquire()
        try:
            if self.__tasks == []:
                return (None, None, None)
            else:
                return self.__tasks.pop(0)
        finally:
            self.__taskLock.release()
    
    def joinAll(self, waitForTasks = True, waitForThreads = True):

        """ Clear the task queue and terminate all pooled threads,
        optionally allowing the tasks and threads to finish."""
        
        # Mark the pool as joining to prevent any more task queueing
        self.__isJoining = True

        # Wait for tasks to finish
        if waitForTasks:
            while self.__tasks != []:
                sleep(.1)

        # Tell all the threads to quit
        self.__resizeLock.acquire()
        try:
            self.__setThreadCountNolock(0)
            self.__isJoining = True

            # Wait until all threads have exited
            if waitForThreads:
                for t in self.__threads:
                    t.join()
                    del t

            # Reset the pool for potential reuse
            self.__isJoining = False
        finally:
            self.__resizeLock.release()


        
class ThreadPoolThread(threading.Thread):

    """ Pooled thread class. """
    
    threadSleepTime = 0.1

    def __init__(self, pool):

        """ Initialize the thread and remember the pool. """
        
        threading.Thread.__init__(self)
        self.__pool = pool
        self.__isDying = False
        
    def run(self):

        """ Until told to quit, retrieve the next task and execute
        it, calling the callback if any.  """
        
        while self.__isDying == False:
            cmd, args, callback = self.__pool.getNextTask()
            # If there's nothing to do, just sleep a bit
            if cmd is None:
                sleep(ThreadPoolThread.threadSleepTime)
            elif callback is None:
                cmd(*args)
            else:
                callback(cmd(*args))
    
    def goAway(self):

        """ Exit the run loop next time through."""
        
        self.__isDying = True

# Usage example
if __name__ == "__main__":

    from random import randrange

    # Sample task 1: given a start and end value, shuffle integers,
    # then sort them
    
    def sortTask(data):
        print "SortTask starting for ", data
        numbers = range(data[0], data[1])
        for a in numbers:
            rnd = randrange(0, len(numbers) - 1)
            a, numbers[rnd] = numbers[rnd], a
        print "SortTask sorting for ", data
        numbers.sort()
        print "SortTask done for ", data
        return "Sorter ", data

    # Sample task 2: just sleep for a number of seconds.

    def waitTask(data):
        print "WaitTask starting for ", data
        print "WaitTask sleeping for %d seconds" % data
        sleep(data)
        return "Waiter", data

    # Both tasks use the same callback

    def taskCallback(data):
        print "Callback called for", data

    # Create a pool with three worker threads

    pool = ThreadPool(3)

    # Insert tasks into the queue and let them run
    pool.queueTask(sortTask, (1000, 100000), taskCallback)
    pool.queueTask(waitTask, 5, taskCallback)
    pool.queueTask(sortTask, (200, 200000), taskCallback)
    pool.queueTask(waitTask, 2, taskCallback)
    pool.queueTask(sortTask, (3, 30000), taskCallback)
    pool.queueTask(waitTask, 7, taskCallback)

    # When all tasks are finished, allow the threads to terminate
    pool.joinAll()
## end of http://code.activestate.com/recipes/203871/ }}}

########NEW FILE########
__FILENAME__ = parsing

import re, datetime

def parse_since(since_str):
    """A utility function to help parse a since string."""
    if since_str == 'all':
        since_date = None
    else:
        try:
            since_date = parse_date_relative(since_str)
        except TypeError:
            since_date = None
    return since_date

def parse_date_relative(back, date=None):
    if date == None:
        date = datetime.datetime.utcnow()
    parser = re.compile("([0-9]*)(d|h|m)")
    parsed = parser.findall(back)
    if not len(parsed) == 1:
        raise TypeError("Could not parse '%s'" % (back))
    num, units = parsed[0]
    num = -1 * int(num)
    if units == 'd':
        td = datetime.timedelta(days=num)
    elif units == 'h':
        td = datetime.timedelta(hours=num)
    elif units == 'm':
        td = datetime.timedelta(minutes=num)
    
    return date + td
    

def parse_class(class_path):
    """Attempts to import a class at the given path and return it."""
    parts = class_path.split('.')
    module = '.'.join(parts[:-1])
    class_name = parts[-1]
    if len(parts) < 2:
        raise Exception(
            'Invalid path "%s".  Must be of the form "x.Y".' % class_path)
    try:
        #exec("from %s import %s" % (module, class_name))
        #return locals()[class_name]
        imported = __import__(module, globals(), locals(), [class_name])
        return getattr(imported, class_name)
    except ImportError:
        return None

# DEPR
# def _class_for_name(name, *args, **kw):
#     try:
#         ns = kw.get('namespace',globals())
#         return ns[name]
#     except KeyError, ke:
#         #raise Exception("Could not find class by name '%s'" % (name))
#         raise ImportError("Could not find class by name '%s'" % (name))
# 
# def _lib_by_name(library_name):
#     try:
#         lib_parts = library_name.split('.')
#         import_base = '.'.join(lib_parts[:-1])
#         to_import = lib_parts[-1]
#         import_str = "from %s import %s" % (import_base, to_import)
#         exec(import_str)
#         return locals()[to_import]
#     except ImportError:
#         return None
# 
# def _get_task_class(path):
#     # get the class for this library
#     task_lib_parts = task_library.split('.')
#     if len(task_lib_parts) < 2:
#         raise Exception("--task_library must be of the form path.to.lib.ClassName")
#     try:
#         task_class_baselib = '.'.join(task_lib_parts[:-1])
#         task_class_name = task_lib_parts[-1]
#         library = _lib_by_name(task_class_baselib)
#         task_class = _class_for_name(task_class_name, namespace=library.__dict__)
#         return task_class
#     except ImportError, ie:
#         raise Exception("Could not find class '%s'" % (task_library))

########NEW FILE########
__FILENAME__ = populate_db
#!/usr/bin/python

import sys
import random, string
import datetime
from norc.core.models import *

def random_string(a, b=None):
    CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_'
    length = random.randint(a, b) if b else a
    return "".join([random.choice(CHARS) for _ in range(length)])
    
HOSTS = ['.'.join([random_string(3) for _ in range(3)]) for _ in range(20)]

def choice_from_queryset(q):
    return q[random.randint(0, len(q) - 1)]

def print_period():
    sys.stdout.write('.')
    sys.stdout.flush()

def add_region():
    ResourceRegion(name=random_string(10,20)).save()

def add_daemon():
    region = choice_from_queryset(ResourceRegion.objects.all())
    global HOSTS
    host = random.choice(HOSTS)
    pid = random.randint(15000, 25000)
    r = random.random()
    if r < 0.85:
        status = NorcDaemonStatus.STATUS_ENDEDGRACEFULLY
    elif r < 0.9:
        status = NorcDaemonStatus.STATUS_ERROR
    elif r < 0.95:
        status = NorcDaemonStatus.STATUS_RUNNING
    else:
        status = random.choice(NorcDaemonStatus.ALL_STATUSES)
    started = datetime.datetime.now() - datetime.timedelta(
        seconds=random.randrange(1209600))
    if status in [NorcDaemonStatus.STATUS_ERROR,
                  NorcDaemonStatus.STATUS_PAUSED,
                  NorcDaemonStatus.STATUS_ENDEDGRACEFULLY,
                  NorcDaemonStatus.STATUS_KILLED,
                  NorcDaemonStatus.STATUS_DELETED]:
        ended = started + datetime.timedelta(
            seconds=random.uniform(120, 60*60*24))
    else:
        ended = None
    NorcDaemonStatus(region=region, host=host, pid=pid, status=status,
        date_started=started, date_ended=ended).save()

def add_job():
    job = Job(name=random_string(5,15), description=random_string(20, 30))
    job.save()
    for _ in range(random.randint(1, 10)):
        add_iteration(job)
    print_period()
    for _ in range(random.randint(0, 20)):
        add_task(job)

def add_iteration(job):
    status = random.choice(Iteration.ALL_STATUSES)
    type_ = random.choice(Iteration.ALL_ITER_TYPES)
    started = datetime.datetime.now() - datetime.timedelta(
        seconds=random.randrange(1209600))
    if type_ == Iteration.ITER_TYPE_EPHEMERAL:
        ended = started + datetime.timedelta(
            seconds=random.uniform(30, 60*60))
    else:
        ended = None
    Iteration(job=job, iteration_type=type_, status=status,
        date_started=started, date_ended=ended).save()

def add_task(job):
    r = random.random()
    if r < 0.9:
        status = Task.STATUS_ACTIVE
    else:
        status = random.choice(Task.ALL_STATUSES)
    rc = RunCommand(job=job, status=status, cmd='', timeout=300)
    rc.save()
    iterations = list(job.iteration_set.all())
    daemons = list(NorcDaemonStatus.objects.all())
    for _ in xrange(random.randint(0, 500)):
        iteration = random.choice(iterations)
        daemon = random.choice(daemons)
        add_trs(rc, iteration, daemon)
    print_period()

def add_trs(task, iteration, daemon):
    r = random.random()
    if r < 0.8:
        status = TaskRunStatus.STATUS_SUCCESS
    elif r < 0.9:
        status = TaskRunStatus.STATUS_ERROR
    else:
        status = random.choice(TaskRunStatus.ALL_STATUSES)
    started = iteration.date_started + datetime.timedelta(
        seconds=random.uniform(30, 60*60))
    if status != TaskRunStatus.STATUS_RUNNING:
        ended = started + datetime.timedelta(seconds=random.uniform(0.1, 5))
    else:
        ended = None
    trs = TaskRunStatus(task=task, iteration=iteration, status=status,
        date_started=started, date_ended=ended, controlling_daemon=daemon)
    trs.save()

def populate():
    for _ in range(10):
        add_region()
    print_period()
    for _ in range(random.randint(500, 1000)):
        add_daemon()
    print_period()
    for _ in range(10):
        add_job()
    print ''

if __name__ == '__main__':
    populate()

########NEW FILE########
__FILENAME__ = reporting

#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#



#############################################
#
# Some utilities used in generating reports
#
#
#Darrell
#05/20/2009
#############################################

import datetime

from utils import log
log = log.Log()


def round_datetime(dt, round_to):
    if round_to == 'DAY':
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if round_to == 'HOUR':
        return dt.replace(minute=0, second=0, microsecond=0)
    if round_to == 'HALFHOUR':
        if dt.minute < 30:
            return dt.replace(minute=0, second=0, microsecond=0)
        else:
            return dt.replace(minute=30, second=0, microsecond=0)
    if round_to == '10MIN':
        return dt.replace(minute=int((dt.minute/10)*10), second=0, microsecond=0)
    raise Exception("Unknown round to unit '%s'" % (round_to))

def round_2_delta(round_to):
    if round_to == 'DAY':
        return datetime.timedelta(days=1)
    if round_to == 'HOUR':
        return datetime.timedelta(hours=1)
    if round_to == 'HALFHOUR':
        return datetime.timedelta(minutes=30)
    if round_to == '10MIN':
        return datetime.timedelta(minutes=10)
    raise Exception("Unknown round to unit '%s'" % (round_to))

def calc_avg(date_deltas):
    total = 0
    for d in date_deltas:
        total += d.seconds
    return float(total) / float(len(date_deltas))

def ensure_hash_depth(h, *keys):
    for key in keys:
        if not h.has_key(key):
            h[key] = {}
        h = h[key]

def ensure_list(h, key, to_append):
    if h.has_key(key):
        h[key].append(to_append)
    else:
        h[key] = [to_append]

def mod_timedelta(td, mod):
    s = td.seconds % mod.seconds
    return datetime.timedelta(seconds=s)

def save_csv(csv, fn):
    log.info("Savin' CSV to '%s'" % (fn))
    fh = open(fn, 'w')
    for line in csv:
        fh.write(','.join(map(str, line)))
        fh.write('\n')
    fh.close()

#

########NEW FILE########
__FILENAME__ = testing

from norc.core.models import *

def make_task(name='TestTask'):
    return CommandTask.objects.create(
        name=name, command="echo 'Running: %s'" % name)

def make_instance():
    return Instance.objects.create(task=make_task())

def make_queue():
    return DBQueue.objects.create(name='Test_Queue')
    

########NEW FILE########
__FILENAME__ = web
import datetime
from django.utils import simplejson
from django.core.paginator import Paginator, InvalidPage

class JSONObjectEncoder(simplejson.JSONEncoder):
    """Handle encoding of complex objects.
    
    The simplejson module doesn't handle the encoding of complex
    objects such as datetime, so we handle it here.
    
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%m/%d/%Y %H:%M:%S")
        try:
            return simplejson.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

def paginate(request, data_set):
    try:
        per_page = int(request.GET.get('per_page', 20))
    except ValueError:
        per_page = 20
    paginator = Paginator(data_set, per_page)
    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    if page_num < 1 or page_num > paginator.num_pages:    
        page_num = 1
    page = paginator.page(page_num)
    page_data = {
        'nextPage': page.next_page_number() if page.has_next() else 0,
        'prevPage': page.previous_page_number() if page.has_previous() else 0,
        'start': page.start_index(),
        'end': page.end_index(),
        'current': page_num,
        'total': paginator.num_pages,
    }
    return page, page_data

########NEW FILE########
__FILENAME__ = settings

"""Settings for Norc, including all Django configuration.

Defaults are stored in defaults.py, and local environments are stored in
settings_local.py to avoid version control.  This file merely pulls in
settings from those other files.

"""

import os
import sys

try:
    import norc
except ImportError, e:
    print 'ImportError:', e
    sys.exit(1)

from norc.settings_local import *
from norc.defaults import Envs

# Find the user's environment.
env_str = os.environ.get('NORC_ENVIRONMENT')
if not env_str:
    raise Exception('You must set the NORC_ENVIRONMENT shell variable.')
try:
    cur_env = Envs.ALL[env_str]
except KeyError, ke:
    raise Exception("Unknown NORC_ENVIRONMENT '%s'." % env_str)

# Use the settings from that environment.
for s in dir(cur_env):
    # If the setting name is a valid constant, add it to globals.
    VALID_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'
    if not s.startswith('_') and all(map(lambda c: c in VALID_CHARS, s)):
        globals()[s] = cur_env[s]

########NEW FILE########
__FILENAME__ = models

import pickle

from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from django.contrib.contenttypes.models import ContentType

from norc.core.models import Queue
from norc.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

class SQSQueue(Queue):
    
    class Meta:
        app_label = 'sqs'
        db_table = 'norc_sqsqueue'
    
    def __init__(self, *args, **kwargs):
        Queue.__init__(self, *args, **kwargs)
        c = SQSConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        self.queue = c.lookup(self.name)
        if not self.queue:
            self.queue = c.create_queue(self.name, 1)
        self.connection = c
    
    @staticmethod
    def get_item(content_type_pk, content_pk):
        ct = ContentType.objects.get(pk=content_type_pk)
        return ct.get_object_for_this_type(pk=content_pk)
    
    # This has weird effects because SQS is crap.
    # def peek(self):
    #     message = self.queue.read(0)
    #     if message:
    #         return SQSQueue.get_item(*pickle.loads(message.get_body()))
    
    def pop(self):
        message = self.queue.read()
        if message:
            self.queue.delete_message(message)
            return SQSQueue.get_item(*pickle.loads(message.get_body()))
    
    def push(self, item):
        Queue.validate(item)
        content_type = ContentType.objects.get_for_model(item)
        body = (content_type.pk, item.pk)
        message = self.queue.new_message(pickle.dumps(body))
        self.queue.write(message)
    
    def count(self):
        return self.queue.count()
    

########NEW FILE########
__FILENAME__ = tests

"""Unit tests for the norc.sqs module."""

from django.test import TestCase

from norc.sqs.models import SQSQueue
from norc.norc_utils import wait_until
from norc.norc_utils.testing import make_instance

class SQSQueueTest(TestCase):
    """Tests the ability to push and pop from an SQSQueue."""
    
    def setUp(self):
        self.queue = SQSQueue.objects.create(name='test')
        self.queue.queue.clear()
        self.item = make_instance()
        # wait_until(lambda: self.queue.queue.count() == 0)
    
    def test_push_pop(self):
        self.queue.push(self.item)
        self.i = None
        def get_item():
            self.i = self.queue.pop()
            return self.i != None
        wait_until(get_item)
        self.assertEqual(self.item, self.i)
    
    def test_invalid(self):
        self.assertRaises(AssertionError, lambda: self.queue.push(self.queue))
    
    def tearDown(self):
        pass
    

########NEW FILE########
__FILENAME__ = urls

import os

from django.conf.urls.defaults import *
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from norc.settings import MEDIA_ROOT

urlpatterns = patterns('',
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/(.*)$', admin.site.root),
    (r'^$', 'norc.web.views.index'),
    (r'^data/counts/$', 'norc.web.views.get_counts'),
    (r'^data/(\w+)/$', 'norc.web.views.get_data'),
    (r'^data/(\w+)/(\w+)/$', 'norc.web.views.get_data'),
    (r'^data/(\w+)/(\w+)/(\w+)/$', 'norc.web.views.get_data'),
    (r'^control/(\w+)/(\w+)/$', 'norc.web.views.control'),
    (r'^logs/(\w+)/(\w+)/$', 'norc.web.views.get_log'),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': MEDIA_ROOT}),
)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = norc_extras

from django import template

register = template.Library()

@register.filter
def totitle(value):
    return value.replace('_', ' ').title()


########NEW FILE########
__FILENAME__ = tests
""" Unit tests for the web module.

So far, tests the data retrieval functionality.

"""

from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson as json

# class DataRetrievalTest(TestCase):
#     
#     def setUp(self):
#         init_test_db()
#         self.c = Client()
#         # self.c.login(username='max', password='norc')
#     
#     def test_executors(self):
#         data = self.c.get('/data/executors/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "status": "ENDED",
#             "success": 1,
#             "started": "06/07/2010 00:00:00",
#             "region": "TEST_REGION",
#             "pid": 9001,
#             "host": "test.norc.com",
#             "ended": "08/27/2010 00:00:00",
#             "running": 0,
#             "errored": 0,
#             "type": "NORC",
#             "id": 1
#         }])
#     
#     def test_executor_details(self):
#         data = self.c.get('/data/executors/1/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "status": "SUCCESS",
#             "task": "RunCommand.1",
#             "started": "07/29/2010 09:30:42",
#             "iteration": 1,
#             "ended": "07/29/2010 16:46:42",
#             "job": "TEST",
#             "id": 1
#         }])
#     
#     def test_jobs(self):
#         data = self.c.get('/data/jobs/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "added": "07/11/2010 12:34:56",
#             "description": "test",
#             "name": "TEST",
#             "id": 1
#         }])
#     
#     def test_jobs_details(self):
#         data = self.c.get('/data/jobs/1/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "status": "",
#             "started": "07/11/2010 13:13:13",
#             "type": "PERSISTENT",
#             "id": 1,
#             "ended": "-"
#         }])
#     
#     def test_iteration_details(self):
#         data = self.c.get('/data/iterations/1/')
#         self.assertEqual(json.loads(data.content)['data'], [{
#             "status": "SUCCESS",
#             "task": "RunCommand.1",
#             "started": "07/29/2010 09:30:42",
#             "iteration": 1,
#             "ended": "07/29/2010 16:46:42",
#             "job": "TEST",
#             "id": 1
#         }])

########NEW FILE########
__FILENAME__ = views

import os
import datetime

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.db.models.query import QuerySet

from norc import settings
from norc.core import reports, controls
from norc.core.constants import Status, Request
from norc.core.models import Scheduler, Executor
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.web import JSONObjectEncoder, paginate
from norc.norc_utils.formatting import untitle

if settings.BACKUP_SYSTEM == "AmazonS3":
    from norc.norc_utils.aws import get_s3_key

def no_cache(view_func):
    def no_cache_wrapper(*args, **kwargs):
        response = view_func(*args, **kwargs)
        response['Cache-Control'] = 'no-cache'
        return response
    return no_cache_wrapper

@no_cache
def index(request):
    """Returns the index.html template."""
    return render_to_response('norc/index.html', {
        'sqs': 'norc.sqs' in settings.INSTALLED_APPS,
        'is_superuser': request.user.is_superuser,
        'reports': reports.all,
        'sections': settings.STATUS_TABLES,
        "requests": {
            "executors": map(Request.name, Executor.VALID_REQUESTS) + ["handle"],
            "schedulers": map(Request.name, Scheduler.VALID_REQUESTS) + ["handle"],
        },
    })

def get_counts(request):
    s_count = Scheduler.objects.alive().count()
    json = simplejson.dumps(s_count, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")

@no_cache
def get_data(request, content_type, content_id=None, detail_type=None):
    """Retrieves and structures data, then returns it as a JSON object.
    
    Returns a JSON object containing data on given content type.
    If content_id is provided, data on the details of the content_type
    object associated with that id will be returned.  The data is
    filtered by GET parameters in the request.
    
    """
    if not content_type in reports.all:
        raise ValueError("Invalid content type '%s'." % content_type)
    report = reports.all[content_type]
    params = {}
    for k, v in request.GET.iteritems():
        params[str(k)] = v
    params['since'] = parse_since(params.get('since'))
    if detail_type:
        if not detail_type in report.details:
            raise ValueError("Invalid detail type '%s'." % detail_type)
        data_key = detail_type
        data_set = report.details[data_key](content_id, **params)
    else:
        data_key = content_type
        data_set = report(content_id)
    report = reports.all[data_key]
    if isinstance(data_set, QuerySet):
        print data_key
        data_set = report.since_filter(data_set, params['since'])
        data_set = report.order_by(data_set, params.get('order'))
    page, page_data = paginate(request, data_set)
    json_data = {
        'data': reports.generate(page.object_list, report, params),
        'page': page_data,
    }
    json = simplejson.dumps(json_data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")

def control(request, content_type, content_id):
    success = False
    if request.user.is_superuser:
        obj = reports.all[content_type].get(content_id)
        req = request.POST.get('request')
        if req == "handle":
            success = controls.handle(obj)
        else:
            success = obj.make_request(getattr(Request, req.upper()))
    return http.HttpResponse(simplejson.dumps(success), mimetype="json")

def get_log(request, content_type, content_id):    
    if not content_type in reports.all:
        raise ValueError("Invalid content type '%s'." % content_type)
    report = reports.all[content_type]
    obj = report.get(content_id)
    header_data = \
        [report.data[untitle(s)](obj, since='all') for s in report.headers]
    local_path = os.path.join(settings.NORC_LOG_DIR, obj.log_path)
    if os.path.isfile(local_path):
        f = open(local_path, 'r')
        log = ''.join(f.readlines())
        f.close()
    elif settings.BACKUP_SYSTEM == "AmazonS3":
        try:
            log = get_s3_key("norc_logs/" + obj.log_path)
        except:
            log = "Error retrieving log from S3."
    else:
        log = "Could not retrieve log file from local machine."
    return render_to_response('norc/log.html', {
        'key': content_type,
        'log': log,
        'headers': report.headers,
        'data': header_data,
    })

########NEW FILE########
