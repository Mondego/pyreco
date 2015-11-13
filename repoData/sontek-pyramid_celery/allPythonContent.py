__FILENAME__ = models
from sqlalchemy import (
    Column,
    Integer,
    Text,
    )

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    )

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

class TaskItem(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    task = Column(Text, unique=True)

########NEW FILE########
__FILENAME__ = populate
import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from ..models import (
    DBSession,
    TaskItem,
    Base,
    )

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd)) 
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    with transaction.manager:
        model = TaskItem(task='create more tasks!')
        DBSession.add(model)

########NEW FILE########
__FILENAME__ = tasks
from celery.task import Task
from celery.task import task

import transaction

from .models import (
    DBSession,
    TaskItem,
)

import time
import random

class DeleteTask(Task):
    def run(self, task_pk):
        print 'deleting task! %s' % task_pk
        task = DBSession.query(TaskItem).filter(TaskItem.id==task_pk)[0]
        DBSession.delete(task)
        transaction.commit()

@task
def add_task(task):
    time.sleep(random.choice([2,4,6,8,10]))
    print 'creating task %s' % task
    task = TaskItem(task=task)
    DBSession.add(task)
    transaction.commit()

########NEW FILE########
__FILENAME__ = views
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from .models import (
    DBSession,
    TaskItem,
)

from .tasks import (
    DeleteTask,
    add_task
)

import time

@view_config(route_name='index', renderer='long_running_with_tm:templates/tasks.mako')
def index(request):
    tasks = DBSession.query(TaskItem).all()
    return {'tasks': tasks }

@view_config(route_name='add_task')
def create_task(request):
    task_val = request.POST['task']
    add_task.delay(task_val)
    time.sleep(1)

    return HTTPFound(request.route_url('index'))

@view_config(route_name='delete_task')
def delete_task(request):
    task_pk = request.matchdict['task_pk']
    DeleteTask().delay(task_pk)
    time.sleep(1)
    return HTTPFound(request.route_url('index'))

########NEW FILE########
__FILENAME__ = celery
from __future__ import absolute_import, print_function
import sys

from celery.bin.celery import CeleryCommand
from celery.app import default_app

from . import CommandMixin

class pworker(CommandMixin, CeleryCommand):
    pass


def main():
    # Fix for setuptools generated scripts, so that it will
    # work with multiprocessing fork emulation.
    # (see multiprocessing.forking.get_preparation_data())
    if __name__ != "__main__":
        sys.modules["__main__"] = sys.modules[__name__]

    pworker(app=default_app).execute_from_commandline()

########NEW FILE########
__FILENAME__ = celerybeat
from __future__ import absolute_import

from pyramid_celery.commands import CommandMixin
try:
    from celery.bin.celerybeat import BeatCommand as BaseBeatCommand
except ImportError:
    from celery.bin.celery import beat as BaseCeleryCtl

from celery.bin.base import Command


class BeatCommand(CommandMixin, BaseBeatCommand):
    preload_options = tuple(BaseBeatCommand.preload_options
            [len(Command.preload_options):])



def main():
    return BeatCommand().execute_from_commandline()

########NEW FILE########
__FILENAME__ = celeryctl
from __future__ import absolute_import

from pyramid_celery.commands import CommandMixin
try:
    from celery.bin.celery import CeleryCommand as BaseCeleryCtl
except ImportError:
    from celery.bin.celery import control as BaseCeleryCtl


class CeleryCtl(CommandMixin, BaseCeleryCtl):
    commands = BaseCeleryCtl.commands.copy()
    option_list = BaseCeleryCtl.option_list[len(BaseCeleryCtl.preload_options):]


def main():
    return CeleryCtl().execute_from_commandline()

########NEW FILE########
__FILENAME__ = celeryd
from __future__ import absolute_import

import sys
from pyramid_celery.commands import CommandMixin
try:
    from celery.bin.celeryd import WorkerCommand as BaseWorkerCommand
except ImportError:
    # Celery >=3.1
    from celery.bin.celery import worker as BaseWorkerCommand

try:
    from celery.concurrency.processes.forking import freeze_support
except ImportError:  # pragma: no cover
    freeze_support = lambda: True  # noqa


class WorkerCommand(CommandMixin, BaseWorkerCommand):
    preload_options = ()


def main():
    # Fix for setuptools generated scripts, so that it will
    # work with multiprocessing fork emulation.
    # (see multiprocessing.forking.get_preparation_data())
    if __name__ != "__main__":
        sys.modules["__main__"] = sys.modules[__name__]
    freeze_support()
    worker = WorkerCommand()
    worker.execute_from_commandline()

########NEW FILE########
__FILENAME__ = celeryev
from __future__ import absolute_import

from pyramid_celery.commands import CommandMixin
try:
    from celery.bin.celeryev import EvCommand as BaseEvCommand
except ImportError:
    from celery.bin.celery import events as BaseEvCommand

from celery.bin.base import Command

class EvCommand(CommandMixin, BaseEvCommand):
    preload_options = tuple(BaseEvCommand.preload_options
            [len(Command.preload_options):])



def main():
    return EvCommand().execute_from_commandline()

########NEW FILE########
__FILENAME__ = test_celery
import unittest
from mock import Mock
from mock import patch


class TestCelery(unittest.TestCase):

    def test_includeme_with_quoted_string(self):
        from pyramid_celery import includeme
        from celery.app import default_app

        config = Mock()
        config.registry = Mock()
        settings = {
            'CELERY_ALWAYS_EAGER': True,
            'BROKER_URL': '"foo"'
        }

        config.registry.settings = settings
        includeme(config)

        assert default_app.conf['BROKER_URL'] == 'foo'

    def test_detailed_includeme(self):
        from pyramid_celery import includeme
        from celery.app import default_app

        settings = {
                'CELERY_ALWAYS_EAGER': 'true',
                'CELERYD_CONCURRENCY': '1',
                'BROKER_URL': '"redis:://localhost:6379/0"',
                'BROKER_TRANSPORT_OPTIONS': '{"foo": "bar"}',
                'ADMINS': '(("Foo Bar", "foo@bar"), ("Baz Qux", "baz@qux"))',
                'CELERYD_TASK_TIME_LIMIT': '0.1',
                'CASSANDRA_SERVERS': '["foo", "bar"]',
                'CELERY_ANNOTATIONS': '[1, 2, 3]',   # any
                'CELERY_ROUTERS': 'some.string',  # also any
                'SOME_KEY': 'SOME VALUE',
                'CELERY_IMPORTS': '("myapp.tasks", )'
        }

        config = Mock()
        config.registry = Mock()

        config.registry.settings = settings

        includeme(config)

        new_settings = default_app.conf

        # Check conversions
        assert new_settings['CELERY_ALWAYS_EAGER'] == True
        assert new_settings['CELERYD_CONCURRENCY'] == 1
        assert new_settings['ADMINS'] == (
                ("Foo Bar", "foo@bar"),
                ("Baz Qux", "baz@qux")
        )
        assert new_settings['BROKER_TRANSPORT_OPTIONS'] == {"foo": "bar"}
        assert new_settings['CELERYD_TASK_TIME_LIMIT'] > 0.09
        assert new_settings['CELERYD_TASK_TIME_LIMIT'] < 0.11
        assert new_settings['CASSANDRA_SERVERS'] == ["foo", "bar"]
        assert new_settings['CELERY_ANNOTATIONS'] == [1, 2, 3]
        assert new_settings['CELERY_ROUTERS'] == 'some.string'
        assert new_settings['SOME_KEY'] == settings['SOME_KEY']
        assert new_settings['CELERY_IMPORTS'] == ("myapp.tasks", )

    def test_celery_quoted_values(self):
        from pyramid_celery import includeme
        from celery.app import default_app

        settings = {
                'BROKER_URL': '"redis://localhost:6379/0"',
                'BROKER_TRANSPORT_OPTIONS': '{"foo": "bar"}',
        }

        config = Mock()
        config.registry = Mock()

        config.registry.settings = settings

        includeme(config)

        new_settings = default_app.conf

        assert new_settings['BROKER_URL'] == 'redis://localhost:6379/0'

    @patch('pyramid_celery.commands.celeryd.WorkerCommand')
    def test_celeryd(self, workercommand):
        from pyramid_celery.commands.celeryd import main

        worker = Mock()
        run = Mock()

        worker.run = run
        workercommand.return_value = worker

        settings = {'CELERY_ALWAYS_EAGER': True}
        registry = Mock()
        registry.settings = settings

        main()

#        workercommand.assert_called_with(app=celery(env))
#        bootstrap.assert_called_with('config.ini')
#        run.assert_called_once_with()

    def test_result_backend(self):

        from pyramid_celery import includeme
        from celery.app import default_app
        from celery.backends.redis import RedisBackend
        from celery.backends.amqp import AMQPBackend

        config = Mock()
        config.registry = Mock()

        settings = {
            'CELERY_RESULT_BACKEND': '"amqp"'
        }
        config.registry.settings = settings

        includeme(config)
        self.assertIsInstance(default_app.backend, AMQPBackend)

        settings = {
            'CELERY_RESULT_BACKEND': '"redis"'
        }
        config.registry.settings = settings

        includeme(config)
        self.assertIsInstance(default_app.backend, RedisBackend)

########NEW FILE########
