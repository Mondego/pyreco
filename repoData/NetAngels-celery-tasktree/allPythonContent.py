__FILENAME__ = celery_tasktree
# -*- coding: utf-8 -*-
from celery.task import task
from celery.task.sets import TaskSet
from functools import wraps


class TaskTree(object):

    def __init__(self):
        self.children = []
        self.last_node = self

    def add_task(self, func, args=None, kwargs=None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        node = TaskTreeNode(func, args, kwargs)
        self.children.append(node)
        node.parent = self
        return node

    def push(self, func, args=None, kwargs=None):
        self.last_node = self.last_node.add_task(func, args, kwargs)
        return self.last_node

    def pop(self):
        if self.last_node == self:
            raise IndexError('pop from empty stack')
        parent = self.last_node.parent
        parent.children.remove(self.last_node)
        self.last_node = parent

    def apply_async(self):
        tasks = []
        for node in self.children:
            func = node.func
            args = node.args
            kwargs = node.kwargs
            callback = kwargs.pop('callback', [])
            if not isinstance(callback, (list, tuple)):
                callback = [callback]
            subtasks = node._get_child_tasks()
            callback += subtasks
            kwargs = dict(callback=callback, **kwargs)
            _task = func.subtask(args=args, kwargs=kwargs)
            tasks.append(_task)
        taskset = TaskSet(tasks)
        result = taskset.apply_async()
        return result

    def apply_and_join(self):
        """ Execute tasks asynchronously and wait for the latest result.

        Method can be useful in conjunction with pop()/push() methods. In such
        a case method returns a list of results in the order which corresponds
        to the order of nodes being pushed.
        """
        return join_tree(self.apply_async())


def join_tree(async_result):
    """ Join to all async results in the tree """
    output = []
    results = async_result.join()
    if not results:
        return output
    first_result = results[0]
    while True:
        output.append(first_result)
        if not getattr(first_result, 'async_result', None):
            break
        first_result = first_result.async_result.join()[0]
    return output


class TaskTreeNode(object):

    def __init__(self, func, args=None, kwargs=None):
        self.parent = None
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.children = []

    def add_task(self, func, args=None, kwargs=None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        node = TaskTreeNode(func, args, kwargs)
        self.children.append(node)
        node.parent = self
        return node

    def _get_child_tasks(self):
        tasks = []
        for node in self.children:
            func = node.func
            args = node.args
            kwargs = node.kwargs
            callback = kwargs.pop('callback', [])
            if not isinstance(callback, (list, tuple)):
                callback = [callback]
            subtasks = node._get_child_tasks()
            callback += subtasks
            kwargs = dict(callback=callback, **kwargs)
            _task = func.subtask(args=args, kwargs=kwargs)
            tasks.append(_task)
        return tasks


def task_with_callbacks(func, **options):
    """ decorator "task with callbacks"

    Callback or list of callbacks which go to function in "callbacks" kwarg,
    will be executed after the function, regardless of the subtask's return
    status.

    If subtask (function) result is an object, then a property named
    "async_result" will be added to that object so that it will be possible to
    join() for that result.
    """
    return task(run_with_callbacks(func), **options)


def run_with_callbacks(func):
    """Decorator "run with callbacks"

    Function is useful as decorator for :meth:`run` method of tasks which are
    subclasses of generic :class:`celery.task.Task` and are expected to be used
    with callbacks.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        callback = kwargs.pop('callback', None)
        retval = func(*args, **kwargs)
        async_result = _exec_callbacks(callback)
        try:
            retval.async_result = async_result
        except AttributeError:
            pass
        return retval
    return wrapper


def _exec_callbacks(callback):
    """ Exec the callback or list of callbacks. Return asyncronous results as
    the TaskSetResult object.
    """
    async_result = None
    if callback:
        if not isinstance(callback, (list, tuple)): # not iterable
            callback = [callback,]
        taskset = TaskSet(tasks=callback)
        async_result = taskset.apply_async()
    return async_result

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
"""
How to run these tests.
------------------------

1. Install celery, then copy ``celeryconfig.py.example`` to ``celeryconfig.py``
and tune the configuration file. Follow celery "getting started" guide:
http://docs.celeryproject.org/en/latest/getting-started/index.html
2. Launch celeryd as ``celeryd --loglevel=INFO``.
Make sure that tasks "test_tasks.mkdir" and "test_tasks.MkdirTask" are found.
3. Run tests with ``nosetests`` command.

"""
import os
from celery_tasktree import *
from nose.tools import *
from test_tasks import mkdir, MkdirTask

def setup():
    for dir in 'd1/2/1 d1/2/2 d1/2 d1/3 d1 d0/1/2 d0/1 d0/2 d0'.split():
        if os.path.isdir(dir):
            os.rmdir(dir)

@with_setup(setup, setup)
def test_task_tree():
    """
    Check TaskTree execution order.

    Following tree of tasks is created::

        d 0
        d 1 - d 1.1
            ` d 1.2 - d 1.2.1
            ` d 1.3 ` d 1.2.2
    """
    tree = TaskTree()

    # this set of tasks created in the right order should create all these
    # files
    node0 = tree.add_task(mkdir, args=['d0'])
    node1 = tree.add_task(mkdir, args=['d1'])
    node12 = node1.add_task(mkdir, args=['d1/2'])
    node13 = node1.add_task(mkdir, args=['d1/3'])
    node121 = node12.add_task(mkdir, args=['d1/2/1'])
    node122 = node12.add_task(mkdir, args=['d1/2/2'])

    # check that tree is build correctly
    eq_(tree.children, [node0, node1])
    eq_(node1.children, [node12, node13])
    eq_(node12.children, [node121, node122])
    eq_(node13.children, [])

    # run tasks and wait for the f0 and f1 task result
    async_res = tree.apply_async()
    f0_res, f1_res = async_res.join()
    eq_(f0_res.created, True)
    eq_(f1_res.created, True)

    # wait for the 1.1, 1.2, 1.3 task result
    f11_res, f12_res = f1_res.async_result.join()
    eq_(f11_res.created, True)
    eq_(f12_res.created, True)

    # wait for 1.2.1 and 1.2.2 tasks
    f121_res, f122_res = f11_res.async_result.join()
    eq_(f121_res.created, True)
    eq_(f122_res.created, True)

    # check that all files were created
    ok_(os.path.isdir('d1/2/1'))
    ok_(os.path.isdir('d1/2/2'))
    ok_(os.path.isdir('d1/3'))


@with_setup(setup, setup)
def test_task_already_contains_callback():
    tree = TaskTree()
    task0 = mkdir.subtask(args=['d0/1'])
    node0 = tree.add_task(mkdir, args=['d0'], kwargs=dict(callback=task0))
    node01 = node0.add_task(mkdir, args=['d0/2'])
    async_res = tree.apply_async()
    (f0_res,) = async_res.join()
    eq_(f0_res.created, True)
    f01_res, f02_res = f0_res.async_result.join()
    eq_(f01_res.created, True)
    eq_(f02_res.created, True)

@with_setup(setup, setup)
def test_task_subclass():
    tree = TaskTree()
    node0 = tree.add_task(MkdirTask, args=['d0'])
    node01 = node0.add_task(MkdirTask, args=['d0/1'])
    tree.apply_and_join()
    ok_(os.path.isdir('d0'))
    ok_(os.path.isdir('d0/1'))

@with_setup(setup, setup)
def test_push_and_pop():
    tree = TaskTree()
    tree.push(mkdir, args=('d0',))
    tree.push(mkdir, args=('d0/abc/def',))
    tree.pop()
    tree.push(mkdir, args=('d0/1',))
    tree.push(mkdir, args=('d0/1/2',))
    [res0, res1, res2] = tree.apply_and_join()

def test_empty_task_tree():
    tree = TaskTree()
    results = tree.apply_and_join()
    eq_(results, [])

########NEW FILE########
__FILENAME__ = test_tasks
# -*- coding: utf-8 -*-
from celery.task import Task
from celery_tasktree import task_with_callbacks, run_with_callbacks
import os


@task_with_callbacks
def mkdir(directory):
    """ Create directory.

    We return CreateDirectoryResult object intentionally, so that
    task_with_callbacks decorator can add async_result attribute to this one.
    """
    os.mkdir(directory)
    return CreateDirectoryResult(True)


class MkdirTask(Task):

    @run_with_callbacks
    def run(self, directory):
        os.mkdir(directory)
        return CreateDirectoryResult(True)


class CreateDirectoryResult(object):
    def __init__(self, created):
        self.created = created
    def __bool__(self):
        return bool(self.created)
    def __str__(self):
        return '%s <%s>' % (id(self), self.created)

########NEW FILE########
