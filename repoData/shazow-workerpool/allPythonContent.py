__FILENAME__ = check
#!/usr/bin/env python
import os
import sys
import glob

import pep8
from pyflakes.scripts import pyflakes


def findpy(path):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            for py in findpy(cfile):
                yield py
        if cfile.endswith('.py'):
            yield cfile


def check_pyflakes(srcdir):
    print(">>> Running pyflakes...")
    clean = True
    for pyfile in findpy(srcdir):
        if pyflakes.checkPath(pyfile) != 0:
            clean = False
    return clean


def check_pep8(srcdir):
    print(">>> Running pep8...")
    clean = True
    pep8.process_options([''])
    for pyfile in findpy(srcdir):
        if pep8.Checker(pyfile).check_all() != 0:
            clean = False
    return clean


def main():
    src = os.path.dirname(sys.argv[0])
    if not check_pep8(src):
        print
        err = "ERROR: pep8 failed on some source files\n"
        err += "ERROR: please fix the errors and re-run this script"
        print(err)
    elif not check_pyflakes(src):
        print
        err = "ERROR: pyflakes failed on some source files\n"
        err += "ERROR: please fix the errors and re-run this script"
        print(err)
    else:
        print(">>> Clean!")

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = clean
#!/usr/bin/env python
import os
import sys
import glob


def find_cruft(path, extensions=['.pyc', '.pyo']):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            for cruft in find_cruft(cfile):
                yield cruft
        fname, ext = os.path.splitext(cfile)
        if ext in extensions:
            yield cfile


def main():
    sc_src = os.path.dirname(sys.argv[0])
    for i in find_cruft(sc_src):
        os.unlink(i)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = blockingworker
from workerpool import WorkerPool

"""
WARNING: This sample class is obsolete since version 0.9.2. It will be removed
or replaced soon.
"""


class BlockingWorkerPool(WorkerPool):
    """
    Similar to WorkerPool but a result queue is passed in along with each job
    and the method will block until the queue is filled with one entry per job.

    Bulk job lists can be performed using the `contract` method.
    """
    def put(self, job, result):
        "Perform a job by a member in the pool and return the result."
        self.job.put(job)
        r = result.get()
        return r

    def contract(self, jobs, result):
        """
        Perform a contract on a number of jobs and block until a result is
        retrieved for each job.
        """
        for j in jobs:
            WorkerPool.put(self, j)

        r = []
        for i in xrange(len(jobs)):
            r.append(result.get())

        return r

########NEW FILE########
__FILENAME__ = sdb
"""
Collection of Amazon Web Services related jobs. Due to the distributed nature
of AWS, executing calls in parallel is super useful.
"""

import time
from Queue import Queue

from workerpool import WorkerPool, SimpleJob, EquippedWorker

try:
    import boto
except ImportError:
    print """
    This module requires `boto` to communicate with Amazon's web services.
    Install it using easy_install:
        easy_install boto
    """
    raise


class SDBToolBox(object):
    "Create a connection to SimpleDB and hold on to it."
    def __init__(self, domain):
        self.conn = boto.connect_sdb()
        self.domain = self.conn.get_domain(domain)


class SdbJob(SimpleJob):
    def run(self, toolbox):
        msg = "Method pointer must come from the Domain class"
        assert isinstance(toolbox.domain, self.method.im_class), msg
        r = self.method(toolbox.domain, *self.args)
        self.result.put(r)


def main():
    DOMAIN = "benchmark"
    conn = boto.connect_sdb()
    domain = conn.get_domain(DOMAIN)

    # Prepare item list
    items = []
    now = time.time()
    for i in domain:
        items.append(i)
    elapsed = time.time() - now

    if not items:
        print "No items found."
        return

    msg = "Fetched manifest of %d items in %f seconds, proceeding."
    print msg % (len(items), elapsed)

    # THE REAL MEAT:

    # Prepare the pool
    print "Initializing pool."

    def toolbox_factory():
        return SDBToolBox(DOMAIN)

    def worker_factory(job_queue):
        return EquippedWorker(job_queue, toolbox_factory)

    pool = WorkerPool(size=20, worker_factory=worker_factory)

    print "Starting to fetch items..."
    now = time.time()

    # Insert jobs
    results_queue = Queue()
    for i in items:
        j = SdbJob(results_queue, boto.sdb.domain.Domain.get_item, [i])
        pool.put(j)

    # Fetch results
    r = [results_queue.get() for i in items]
    elapsed = time.time() - now

    print "Fetched %d items paralleled in %f seconds." % (len(r), elapsed)

    pool.shutdown()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_equipped
import unittest

from Queue import Queue
import sys
sys.path.append('../')

import workerpool


class Counter(object):
    "Counter resource used for testing EquippedWorker."
    def __init__(self):
        self.count = 0


class CountJob(workerpool.Job):
    "Job that just increments the count in its resource and append it to the"
    "results queue."
    def __init__(self, results):
        self.results = results

    def run(self, toolbox):
        "Append the current count to results and increment."
        self.results.put(toolbox.count)
        toolbox.count += 1


class TestEquippedWorkers(unittest.TestCase):
    def test_equipped(self):
        """
        Created equipped worker that will use an internal Counter resource to
        keep track of the job count.
        """
        results = Queue()

        def toolbox_factory():
            return Counter()

        def worker_factory(job_queue):
            return workerpool.EquippedWorker(job_queue, toolbox_factory)

        pool = workerpool.WorkerPool(1, worker_factory=worker_factory)

        # Run 10 jobs
        for i in xrange(10):
            j = CountJob(results)
            pool.put(j)

        # Get 10 results
        for i in xrange(10):
            r = results.get()
            # Each result should be an incremented value
            self.assertEquals(r, i)

        pool.shutdown()

########NEW FILE########
__FILENAME__ = test_workerpool
import unittest

from Queue import Queue, Empty
import sys
sys.path.append('../')

import workerpool


class TestWorkerPool(unittest.TestCase):
    def double(self, i):
        return i * 2

    def add(self, *args):
        return sum(args)

    def test_map(self):
        "Map a list to a method to a pool of two workers."
        pool = workerpool.WorkerPool(2)

        r = pool.map(self.double, [1, 2, 3, 4, 5])
        self.assertEquals(set(r), {2, 4, 6, 8, 10})
        pool.shutdown()

    def test_map_multiparam(self):
        "Test map with multiple parameters."
        pool = workerpool.WorkerPool(2)
        r = pool.map(self.add, [1, 2, 3], [4, 5, 6])
        self.assertEquals(set(r), {5, 7, 9})
        pool.shutdown()

    def test_wait(self):
        "Make sure each task gets marked as done so pool.wait() works."
        pool = workerpool.WorkerPool(5)
        q = Queue()
        for i in xrange(100):
            pool.put(workerpool.SimpleJob(q, sum, [range(5)]))
        pool.wait()
        pool.shutdown()

    def test_init_size(self):
        pool = workerpool.WorkerPool(1)
        self.assertEquals(pool.size(), 1)
        pool.shutdown()

    def test_shrink(self):
        pool = workerpool.WorkerPool(1)
        pool.shrink()
        self.assertEquals(pool.size(), 0)
        pool.shutdown()

    def test_grow(self):
        pool = workerpool.WorkerPool(1)
        pool.grow()
        self.assertEquals(pool.size(), 2)
        pool.shutdown()

    def test_changesize(self):
        "Change sizes and make sure pool doesn't work with no workers."
        pool = workerpool.WorkerPool(5)
        for i in xrange(5):
            pool.grow()
        self.assertEquals(pool.size(), 10)
        for i in xrange(10):
            pool.shrink()
        pool.wait()
        self.assertEquals(pool.size(), 0)

        # Make sure nothing is reading jobs anymore
        q = Queue()
        for i in xrange(5):
            pool.put(workerpool.SimpleJob(q, sum, [range(5)]))
        try:
            q.get(block=False)
        except Empty:
            pass  # Success
        else:
            assert False, "Something returned a result, even though we are"
            "expecting no workers."
        pool.shutdown()

########NEW FILE########
__FILENAME__ = exceptions
# exceptions.py - Exceptions used in the operation of a worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php


class TerminationNotice(Exception):
    "This exception is raised inside a thread when it's time for it to die."
    pass

########NEW FILE########
__FILENAME__ = jobs
# jobs.py - Generic jobs used with the worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

from exceptions import TerminationNotice

__all__ = ['Job', 'SuicideJob', 'SimpleJob']


class Job(object):
    "Interface for a Job object."
    def __init__(self):
        pass

    def run(self):
        "The actual task for the job should be implemented here."
        pass


class SuicideJob(Job):
    "A worker receiving this job will commit suicide."
    def run(self, **kw):
        raise TerminationNotice()


class SimpleJob(Job):
    """
    Given a `result` queue, a `method` pointer, and an `args` dictionary or
    list, the method will execute r = method(*args) or r = method(**args),
    depending on args' type, and perform result.put(r).
    """
    def __init__(self, result, method, args=[]):
        self.result = result
        self.method = method
        self.args = args

    def run(self):
        if isinstance(self.args, list) or isinstance(self.args, tuple):
            r = self.method(*self.args)
        elif isinstance(self.args, dict):
            r = self.method(**self.args)
        self._return(r)

    def _return(self, r):
        "Handle return value by appending to the ``self.result`` queue."
        self.result.put(r)

########NEW FILE########
__FILENAME__ = pools
# workerpool.py - Module for distributing jobs to a pool of worker threads.
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php


from Queue import Queue
if not hasattr(Queue, 'task_done'):
    # Graft Python 2.5's Queue functionality onto Python 2.4's implementation
    # TODO: The extra methods do nothing for now. Make them do something.
    from QueueWrapper import Queue

from workers import Worker
from jobs import SimpleJob, SuicideJob


__all__ = ['WorkerPool', 'default_worker_factory']


def default_worker_factory(job_queue):
    return Worker(job_queue)


class WorkerPool(Queue):
    """
    WorkerPool servers two functions: It is a Queue and a master of Worker
    threads. The Queue accepts Job objects and passes it on to Workers, who are
    initialized during the construction of the pool and by using grow().

    Jobs are inserted into the WorkerPool with the `put` method.
    Hint: Have the Job append its result into a shared queue that the caller
    holds and then the caller reads an expected number of results from it.

    The shutdown() method must be explicitly called to terminate the Worker
    threads when the pool is no longer needed.

    Construction parameters:

    size = 1
        Number of active worker threads the pool should contain.

    maxjobs = 0
        Maximum number of jobs to allow in the queue at a time. Will block on
        `put` if full.

    default_worker = default_worker_factory
        The default worker factory is called with one argument, which is the
        jobs Queue object that it will read from to acquire jobs. The factory
        will produce a Worker object which will be added to the pool.
    """
    def __init__(self, size=1, maxjobs=0,
                 worker_factory=default_worker_factory):
        if not callable(worker_factory):
            raise TypeError("worker_factory must be callable")

        self.worker_factory = worker_factory  # Used to build new workers
        self._size = 0  # Number of active workers we have

        # Initialize the Queue
        # The queue contains job that are read by workers
        Queue.__init__(self, maxjobs)
        # Pointer to the queue for backward-compatibility with version <=0.9.1
        self._jobs = self

        # Hire some workers!
        for i in xrange(size):
            self.grow()

    def grow(self):
        "Add another worker to the pool."
        t = self.worker_factory(self)
        t.start()
        self._size += 1

    def shrink(self):
        "Get rid of one worker from the pool. Raises IndexError if empty."
        if self._size <= 0:
            raise IndexError("pool is already empty")
        self._size -= 1
        self.put(SuicideJob())

    def shutdown(self):
        "Retire the workers."
        for i in xrange(self.size()):
            self.put(SuicideJob())

    def size(self):
        "Approximate number of active workers"
        "(could be more if a shrinking is in progress)."
        return self._size

    def map(self, fn, *seq):
        "Perform a map operation distributed among the workers. Will "
        "block until done."
        results = Queue()
        args = zip(*seq)
        for seq in args:
            j = SimpleJob(results, fn, seq)
            self.put(j)

        # Aggregate results
        r = []
        for i in xrange(len(args)):
            r.append(results.get())

        return r

    def wait(self):
        "DEPRECATED: Use join() instead."
        self.join()

########NEW FILE########
__FILENAME__ = QueueWrapper
# QueueWrapper.py - Implements Python 2.5 Queue functionality for Python 2.4
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

# TODO: The extra methods provided here do nothing for now. Add real
# functionality to them someday.

from Queue import Queue as OldQueue

__all__ = ['Queue']


class Queue(OldQueue):
    def task_done(self):
        "Does nothing in Python 2.4"
        pass

    def join(self):
        "Does nothing in Python 2.4"
        pass

########NEW FILE########
__FILENAME__ = workers
# workers.py - Worker objects who become members of a worker pool
# Copyright (c) 2008 Andrey Petrov
#
# This module is part of workerpool and is released under
# the MIT license: http://www.opensource.org/licenses/mit-license.php

from threading import Thread
from exceptions import TerminationNotice

__all__ = ['Worker', 'EquippedWorker']


class Worker(Thread):
    """
    A loyal worker who will pull jobs from the `jobs` queue and perform them.

    The run method will get jobs from the `jobs` queue passed into the
    constructor, and execute them. After each job, task_done() must be executed
    on the `jobs` queue in order for the pool to know when no more jobs are
    being processed.
    """

    def __init__(self, jobs):
        self.jobs = jobs
        Thread.__init__(self)

    def run(self):
        "Get jobs from the queue and perform them as they arrive."
        while 1:
            # Sleep until there is a job to perform.
            job = self.jobs.get()

            # Yawn. Time to get some work done.
            try:
                job.run()
                self.jobs.task_done()
            except TerminationNotice:
                self.jobs.task_done()
                break


class EquippedWorker(Worker):
    """
    Each worker will create an instance of ``toolbox`` and hang on to it during
    its lifetime. This can be used to pass in a resource such as a persistent
    connections to services that the worker will be using.

    The toolbox factory is called without arguments to produce an instance of
    an object which contains resources necessary for this Worker to perform.
    """
    # TODO: Should a variation of this become the default Worker someday?

    def __init__(self, jobs, toolbox_factory):
        self.toolbox = toolbox_factory()
        Worker.__init__(self, jobs)

    def run(self):
        "Get jobs from the queue and perform them as they arrive."
        while 1:
            job = self.jobs.get()
            try:
                job.run(toolbox=self.toolbox)
                self.jobs.task_done()
            except TerminationNotice:
                self.jobs.task_done()
                break

########NEW FILE########
