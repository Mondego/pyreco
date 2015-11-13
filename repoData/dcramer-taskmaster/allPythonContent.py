__FILENAME__ = master
"""
taskmaster.cli.master
~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from taskmaster.util import parse_options
from taskmaster.constants import DEFAULT_LOG_LEVEL, DEFAULT_ADDRESS, \
  DEFAULT_BUFFER_SIZE


def run(target, kwargs=None, reset=False, size=DEFAULT_BUFFER_SIZE, address=DEFAULT_ADDRESS, log_level=DEFAULT_LOG_LEVEL):
    from taskmaster.server import Server, Controller

    server = Server(address, size=size, log_level=log_level)

    controller = Controller(server, target, kwargs=kwargs, log_level=log_level)
    if reset:
        controller.reset()
    controller.start()


def main():
    import optparse
    import sys
    parser = optparse.OptionParser()
    parser.add_option("--address", dest="address", default=DEFAULT_ADDRESS)
    parser.add_option("--size", dest="size", default=DEFAULT_BUFFER_SIZE, type=int)
    parser.add_option("--reset", dest="reset", default=False, action='store_true')
    parser.add_option("--log-level", dest="log_level", default=DEFAULT_LOG_LEVEL)
    (options, args) = parser.parse_args()
    if len(args) < 1:
        print 'Usage: tm-master <callback> [key=value, key2=value2]'
        sys.exit(1)
    sys.exit(run(args[0], parse_options(args[1:]), **options.__dict__))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = run
"""
taskmaster.cli.run
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from multiprocessing import Process
from taskmaster.cli.spawn import run as run_spawn
from taskmaster.cli.master import run as run_master
from taskmaster.constants import DEFAULT_LOG_LEVEL, DEFAULT_ADDRESS, \
  DEFAULT_ITERATOR_TARGET, DEFAULT_CALLBACK_TARGET, DEFAULT_BUFFER_SIZE, \
  DEFAULT_RETRIES, DEFAULT_TIMEOUT
from taskmaster.util import parse_options


def run(get_jobs_target, handle_job_target, procs, kwargs=None, log_level=DEFAULT_LOG_LEVEL,
        address=DEFAULT_ADDRESS, reset=False, size=DEFAULT_BUFFER_SIZE,
        retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT):
    pool = [
        Process(target=run_master, args=[get_jobs_target], kwargs={
            'log_level': log_level,
            'address': address,
            'size': size,
            'reset': reset,
            'kwargs': kwargs,
        }),
        Process(target=run_spawn, args=[handle_job_target, procs], kwargs={
            'log_level': log_level,
            'address': address,
            'progressbar': False,
            'retries': retries,
            'timeout': timeout,
        }),
    ]

    for p in pool:
        p.start()

    for p in (p for p in pool if p.is_alive()):
        p.join(0)


def main():
    import optparse
    import sys
    parser = optparse.OptionParser()
    parser.add_option("--address", dest="address", default=DEFAULT_ADDRESS)
    parser.add_option("--size", dest="size", default='10000', type=int)
    parser.add_option("--retries", dest="retries", default=DEFAULT_RETRIES, type=int)
    parser.add_option("--timeout", dest="timeout", default=DEFAULT_TIMEOUT, type=int)
    parser.add_option("--reset", dest="reset", default=False, action='store_true')
    parser.add_option("--log-level", dest="log_level", default=DEFAULT_LOG_LEVEL)
    parser.add_option("--get-jobs-callback", dest="get_jobs_target", default=DEFAULT_ITERATOR_TARGET)
    parser.add_option("--handle-job-callback", dest="handle_job_target", default=DEFAULT_CALLBACK_TARGET)
    (options, args) = parser.parse_args()
    if len(args) < 2:
        print 'Usage: tm-run <script> <processes> [key=value, key2=value2]'
        sys.exit(1)

    kwargs = options.__dict__.copy()

    script_name = args[0]
    handle_job_target = script_name + ':' + kwargs.pop('handle_job_target')
    get_jobs_target = script_name + ':' + kwargs.pop('get_jobs_target')

    sys.exit(run(
        get_jobs_target=get_jobs_target,
        handle_job_target=handle_job_target,
        procs=int(args[1]),
        kwargs=parse_options(args[2:]),
        **kwargs
    ))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = slave
"""
taskmaster.cli.slave
~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from taskmaster.constants import (
    DEFAULT_ADDRESS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
)


def run(target, address=DEFAULT_ADDRESS, progressbar=True,
        log_level=DEFAULT_LOG_LEVEL, retries=DEFAULT_RETRIES, timeout=DEFAULT_TIMEOUT):
    from taskmaster.client import Consumer, Client

    client = Client(address, log_level=log_level, retries=retries,
            timeout=timeout)

    consumer = Consumer(client, target, progressbar=progressbar, log_level=log_level)
    consumer.start()


def main():
    import optparse
    import sys
    parser = optparse.OptionParser()
    parser.add_option("--address", dest="address", default=DEFAULT_ADDRESS)
    parser.add_option("--no-progress", dest="progressbar", action="store_false", default=True)
    parser.add_option("--log-level", dest="log_level", default=DEFAULT_LOG_LEVEL)
    parser.add_option("--retries", dest="retries", default=DEFAULT_RETRIES, type=int)
    parser.add_option("--timeout", dest="timeout", default=DEFAULT_TIMEOUT, type=int)
    (options, args) = parser.parse_args()
    if len(args) != 1:
        print 'Usage: tm-slave <callback>'
        sys.exit(1)
    sys.exit(run(args[0], **options.__dict__))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = spawn
"""
taskmaster.cli.spawn
~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from multiprocessing import Process
from taskmaster.cli.slave import run as run_slave
from taskmaster.constants import (
    DEFAULT_ADDRESS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
)


def run(target, procs, **kwargs):
    pool = []
    for n in xrange(procs):
        pool.append(Process(target=run_slave, args=[target], kwargs=kwargs))

    for p in pool:
        p.start()

    for p in (p for p in pool if p.is_alive()):
        p.join(0)


def main():
    import optparse
    import sys
    parser = optparse.OptionParser()
    parser.add_option("--address", dest="address", default=DEFAULT_ADDRESS)
    parser.add_option("--log-level", dest="log_level", default=DEFAULT_LOG_LEVEL)
    parser.add_option("--retries", dest="retries", default=DEFAULT_RETRIES, type=int)
    parser.add_option("--timeout", dest="timeout", default=DEFAULT_TIMEOUT, type=int)
    (options, args) = parser.parse_args()
    if len(args) != 2:
        print 'Usage: tm-spawn <callback> <processes>'
        sys.exit(1)
    sys.exit(run(args[0], procs=int(args[1]), progressbar=False, **options.__dict__))

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = client
"""
taskmaster.consumer
~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import cPickle as pickle
import gevent
from gevent_zeromq import zmq
from gevent.queue import Queue
from taskmaster.constants import DEFAULT_LOG_LEVEL, DEFAULT_CALLBACK_TARGET
from taskmaster.util import import_target, get_logger


class Worker(object):
    def __init__(self, consumer, target):
        self.consumer = consumer
        self.target = target

    def run(self):
        self.started = True

        while self.started:
            gevent.sleep(0)

            try:
                job_id, job = self.consumer.get_job()
                self.target(job)
            except KeyboardInterrupt:
                return
            finally:
                self.consumer.task_done()


class Client(object):
    def __init__(self, address, timeout=2500, retries=3, log_level=DEFAULT_LOG_LEVEL):
        self.address = address
        self.timeout = timeout
        self.retries = retries

        self.context = zmq.Context(1)
        self.poller = zmq.Poller()
        self.client = None
        self.logger = get_logger(self, log_level)

    def reconnect(self):
        if self.client:
            self.poller.unregister(self.client)
            self.client.close()
            self.logger.info('Reconnecting to server on %r', self.address)
        else:
            self.logger.info('Connecting to server on %r', self.address)

        self.client = self.context.socket(zmq.REQ)
        self.client.setsockopt(zmq.LINGER, 0)
        self.client.connect(self.address)
        self.poller.register(self.client, zmq.POLLIN)

    def send(self, cmd, data=''):
        request = [cmd, data]
        retries = self.retries
        reply = None

        while retries > 0:
            self.client.send_multipart(request)
            try:
                items = self.poller.poll(self.timeout)
            except KeyboardInterrupt:
                break  # interrupted

            if items:
                reply = self.recv()
                break
            else:
                if retries:
                    self.reconnect()
                else:
                    break
                retries -= 1

            # We only sleep if we need to retry
            gevent.sleep(0.01)

        return reply

    def recv(self):
        reply = self.client.recv_multipart()

        assert len(reply) == 2

        return reply

    def destroy(self):
        if self.client:
            self.poller.unregister(self.client)
            self.client.setsockopt(zmq.LINGER, 0)
            self.client.close()
        self.context.destroy()


class Consumer(object):
    def __init__(self, client, target, progressbar=True, log_level=DEFAULT_LOG_LEVEL):
        if isinstance(target, basestring):
            target = import_target(target, DEFAULT_CALLBACK_TARGET)

        self.client = client
        self.target = target
        self.queue = Queue(maxsize=1)
        if progressbar:
            self.pbar = self.get_progressbar()
        else:
            self.pbar = None

        self._wants_job = False
        self.logger = get_logger(self, log_level)

    def get_progressbar(self):
        from taskmaster.progressbar import Counter, Speed, Timer, ProgressBar, UnknownLength

        widgets = ['Tasks Completed: ', Counter(), ' | ', Speed(), ' | ', Timer()]

        pbar = ProgressBar(widgets=widgets, maxval=UnknownLength)

        return pbar

    def get_job(self):
        self._wants_job = True

        return self.queue.get()

    def task_done(self):
        if self.pbar:
            self.pbar.update(self.tasks_completed)
        self.tasks_completed += 1
        # self.client.send('DONE')

    def start(self):
        self.started = True
        self.tasks_completed = 0

        self.client.reconnect()

        worker = Worker(self, self.target)
        gevent.spawn(worker.run)

        if self.pbar:
            self.pbar.start()

        while self.started:
            gevent.sleep(0)

            # If the queue has items in it, we just loop
            if not self._wants_job:
                continue

            reply = self.client.send('GET')
            if not reply:
                self.logger.error('No response from server; shutting down.')
                break

            cmd, data = reply
            # Reply can be "WAIT", "OK", or "ERROR"
            if cmd == 'OK':
                self._wants_job = False
                job = pickle.loads(data)
                self.queue.put(job)
            elif cmd == 'QUIT':
                break

        self.logger.info('Shutting down')
        self.shutdown()

    def shutdown(self):
        if not self.started:
            return
        self.started = False
        if self.pbar:
            self.pbar.finish()
        self.client.destroy()

########NEW FILE########
__FILENAME__ = constants
"""
taskmaster.constants
~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

DEFAULT_ADDRESS = 'tcp://0.0.0.0:3050'
DEFAULT_LOG_LEVEL = 'ERROR'
DEFAULT_ITERATOR_TARGET = 'get_jobs'
DEFAULT_CALLBACK_TARGET = 'handle_job'
DEFAULT_BUFFER_SIZE = 10000
DEFAULT_TIMEOUT = 2500
DEFAULT_RETRIES = 3

########NEW FILE########
__FILENAME__ = example
"""
taskmaster.example
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""


def get_jobs(last=0, **kwargs):
    # last_job would be sent if state was resumed
    # from a previous run
    print 'Running with options: %r' % kwargs
    for i in xrange(last, 20000):
        yield i


def handle_job(i):
    pass
    # print "Got %r!" % i

########NEW FILE########
__FILENAME__ = progressbar
"""
taskmaster.progressbar
~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from __future__ import absolute_import

from progressbar import ProgressBar, UnknownLength, Counter, Timer
from progressbar.widgets import Widget


class Speed(Widget):
    'Widget for showing the rate.'

    format = 'Rate:  %6.2f/s'

    def __init__(self):
        self.startval = 0

    def update(self, pbar):
        'Updates the widget with the current SI prefixed speed.'

        if self.startval == 0:
            self.startval = pbar.currval
            return 'Rate:  --/s'

        speed = (pbar.currval - self.startval) / pbar.seconds_elapsed

        return self.format % speed


class Value(Widget):

    def __init__(self, label=None, callback=None):
        assert not (label and callback)
        self.label = label
        self.callback = callback

    def update(self, pbar):
        if self.callback:
            return self.callback(pbar)
        return self.label

########NEW FILE########
__FILENAME__ = server
"""
taskmaster.controller
~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import cPickle as pickle
import gevent
import hashlib
import sys
from gevent_zeromq import zmq
from gevent.queue import Queue, Empty
from os import path, unlink, rename
from taskmaster.constants import DEFAULT_LOG_LEVEL, DEFAULT_ITERATOR_TARGET
from taskmaster.util import import_target, get_logger


class Server(object):
    def __init__(self, address, size=None, log_level=DEFAULT_LOG_LEVEL):
        self.daemon = True
        self.started = False
        self.size = size
        self.queue = Queue(maxsize=size)
        self.address = address

        self.context = zmq.Context(1)
        self.server = None
        self.logger = get_logger(self, log_level)

        self._has_fetched_jobs = False

    def send(self, cmd, data=''):
        self.server.send_multipart([cmd, data])

    def recv(self):
        reply = self.server.recv_multipart()

        assert len(reply) == 2

        return reply

    def bind(self):
        if self.server:
            self.server.close()

        self.server = self.context.socket(zmq.REP)
        self.server.bind(self.address)

    def start(self):
        self.started = True

        self.logger.info("Taskmaster binding to %r", self.address)
        self.bind()

        while self.started:
            gevent.sleep(0)
            cmd, data = self.recv()
            if cmd == 'GET':
                if not self.has_work():
                    self.send('QUIT')
                    continue

                try:
                    job = self.queue.get_nowait()
                except Empty:
                    self.send('WAIT')
                    continue

                self.send('OK', pickle.dumps(job))

            elif cmd == 'DONE':
                self.queue.task_done()
                if self.has_work():
                    self.send('OK')
                else:
                    self.send('QUIT')

            else:
                self.send('ERROR', 'Unrecognized command')

        self.logger.info('Shutting down')
        self.shutdown()

    def mark_queue_filled(self):
        self._has_fetched_jobs = True

    def put_job(self, job):
        return self.queue.put(job)

    def first_job(self):
        return self.queue.queue[0]

    def get_current_size(self):
        return self.queue.qsize()

    def get_max_size(self):
        return self.size

    def has_work(self):
        if not self._has_fetched_jobs:
            return True
        return not self.queue.empty()

    def is_alive(self):
        return self.started

    def shutdown(self):
        if not self.started:
            return
        self.server.close()
        self.context.term()
        self.started = False


class Controller(object):
    def __init__(self, server, target, kwargs=None, state_file=None, progressbar=True, log_level=DEFAULT_LOG_LEVEL):
        if isinstance(target, basestring):
            target = import_target(target, DEFAULT_ITERATOR_TARGET)

        if not state_file:
            target_file = sys.modules[target.__module__].__file__.rsplit('.', 1)[0]
            state_file = path.join(path.dirname(target_file),
                '%s' % (path.basename(target_file),))
            if kwargs:
                checksum = hashlib.md5()
                for k, v in sorted(kwargs.items()):
                    checksum.update('%s=%s' % (k, v))
                state_file += '.%s' % checksum.hexdigest()
            state_file += '.state'
            print state_file

        self.server = server
        self.target = target
        self.target_kwargs = kwargs
        self.state_file = state_file
        if progressbar:
            self.pbar = self.get_progressbar()
        else:
            self.pbar = None
        self.logger = get_logger(self, log_level)

    def get_progressbar(self):
        from taskmaster.progressbar import Counter, Speed, Timer, ProgressBar, UnknownLength, Value

        sizelen = len(str(self.server.size))
        format = 'In-Queue: %%-%ds / %%-%ds' % (sizelen, sizelen)

        queue_size = Value(callback=lambda x: format % (self.server.get_current_size(), self.server.get_max_size()))

        widgets = ['Completed Tasks: ', Counter(), ' | ', queue_size, ' | ', Speed(), ' | ', Timer()]

        pbar = ProgressBar(widgets=widgets, maxval=UnknownLength)

        return pbar

    def read_state(self):
        if path.exists(self.state_file):
            self.logger.info("Reading previous state from %r", self.state_file)
            with open(self.state_file, 'r') as fp:
                try:
                    return pickle.load(fp)
                except EOFError:
                    pass
                except Exception, e:
                    self.logger.exception("There was an error reading from state file. Ignoring and continuing without.\n%s", e)
        return {}

    def update_state(self, job_id, job, fp=None):
        last_job_id = getattr(self, '_last_job_id', None)

        if self.pbar:
            self.pbar.update(job_id)

        if job_id == last_job_id:
            return

        if not job:
            return

        last_job_id = job_id

        data = {
            'job': job,
            'job_id': job_id,
        }

        with open(self.state_file + '.tmp', 'w') as fp:
            pickle.dump(data, fp)
        rename(self.state_file + '.tmp', self.state_file)

    def state_writer(self):
        while self.server.is_alive():
            # state is not guaranteed accurate, as we do not
            # update the file on every iteration
            gevent.sleep(0.01)

            try:
                job_id, job = self.server.first_job()
            except IndexError:
                self.update_state(None, None)
                continue

            self.update_state(job_id, job)

    def reset(self):
        if path.exists(self.state_file):
            unlink(self.state_file)

    def start(self):
        if self.target_kwargs:
            kwargs = self.target_kwargs.copy()
        else:
            kwargs = {}
        
        last_job = self.read_state()
        if last_job:
            kwargs['last'] = last_job['job']
            start_id = last_job['job_id']
        else:
            start_id = 0

        gevent.spawn(self.server.start)

        # context switch so the server can spawn
        gevent.sleep(0)

        if self.pbar:
            self.pbar.start()
            self.pbar.update(start_id)

        state_writer = gevent.spawn(self.state_writer)

        job_id, job = (None, None)
        for job_id, job in enumerate(self.target(**kwargs), start_id):
            self.server.put_job((job_id, job))
            gevent.sleep(0)
        self.server.mark_queue_filled()

        while self.server.has_work():
            gevent.sleep(0.01)

        # Give clients a few seconds to receive a DONE message
        gevent.sleep(3)

        self.server.shutdown()
        state_writer.join(1)

        self.update_state(job_id, job)

        if self.pbar:
            self.pbar.finish()

########NEW FILE########
__FILENAME__ = util
"""
taskmaster.util
~~~~~~~~~~~~~~~

:copyright: (c) 2010 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

import imp
import logging
import sys
from os.path import exists


def import_target(target, default=None):
    """
    >>> import_target('foo.bar:blah', 'get_jobs')
    <function foo.bar.blah>

    >>> import_target('foo.bar', 'get_jobs')
    <function foo.bar.get_jobs>

    >>> import_target('foo.bar:get_jobs')
    <function foo.bar.get_jobs>

    >>> import_target('foo/bar.py:get_jobs')
    <function get_jobs>
    """
    if ':' not in target:
        target += ':%s' % default

    path, func_name = target.split(':', 1)

    if exists(path):
        module_name = path.rsplit('/', 1)[-1].split('.', 1)[0]
        module = imp.new_module(module_name)
        module.__file__ = path
        try:
            execfile(path, module.__dict__)
        except IOError, e:
            e.strerror = 'Unable to load file (%s)' % e.strerror
            raise
        sys.modules[module_name] = module
    elif '/' in path:
        raise ValueError('File not found: %r' % path)
    else:
        module = __import__(path, {}, {}, [func_name], -1)

    callback = getattr(module, func_name)

    return callback


def get_logger(inst, log_level='INFO'):
    logger = logging.getLogger('%s.%s[%s]' % (inst.__module__, type(inst).__name__, id(inst)))
    logger.setLevel(getattr(logging, log_level))
    logger.addHandler(logging.StreamHandler())
    return logger


def parse_options(args):
    return dict(a.split('=', 1) for a in args)

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
