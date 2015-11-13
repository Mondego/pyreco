__FILENAME__ = config
CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_HOST = "localhost"
CELERY_REDIS_PORT = 6379
CELERY_REDIS_DB = 0

BROKER_URL = 'redis://localhost:6379/0'


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from __future__ import absolute_import
from flask.ext.script import Manager
from flask.ext.celery import install_commands as install_celery_commands

from myapp import create_app

app = create_app()
manager = Manager(app)
install_celery_commands(manager)

if __name__ == "__main__":
    manager.run()

########NEW FILE########
__FILENAME__ = myapp
from flask import Flask, request
from flask.ext.celery import Celery


def create_app():
    return Flask("myapp")

app = create_app()
app.config.from_pyfile('config.py')
celery = Celery(app)


@celery.task(name="myapp.add")
def add(x, y):
    return x + y


@app.route("/")
def hello_world(x=16, y=16):
    x = int(request.args.get("x", x))
    y = int(request.args.get("y", y))
    res = add.apply_async((x, y))
    context = {"id": res.task_id, "x": x, "y": y}
    return """Hello world: \
                add(%(x)s, %(y)s) = \
                <a href="/result/%(id)s">%(id)s</a>""" % context


@app.route("/result/<task_id>")
def show_result(task_id):
    retval = add.AsyncResult(task_id).get(timeout=1.0)
    return repr(retval)


if __name__ == "__main__":
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = flask_celery
# -*- coding: utf-8 -*-
"""
    flask.ext.celery
    ~~~~~~~~~~~~~~~~

    Celery integration for Flask.

    :copyright: (c) 2010-2011 Ask Solem <ask@celeryproject.org>
    :license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import

import argparse

from celery.app import App, AppPickler, current_app as current_celery
from celery.loaders import default as _default
from celery.utils import get_full_cls_name

from werkzeug import cached_property

from flask.ext import script


class FlaskLoader(_default.Loader):

    def read_configuration(self):
        config = self.app.flask_app.config
        settings = self.setup_settings(config)
        self.configured = True
        return settings


class FlaskAppPickler(AppPickler):

    def build_kwargs(self, flask_app, *args):
        kwargs = self.build_standard_kwargs(*args)
        kwargs["flask_app"] = flask_app
        return kwargs


class Celery(App):
    Pickler = FlaskAppPickler
    flask_app = None
    loader_cls = get_full_cls_name(FlaskLoader)

    def __init__(self, flask_app=None, *args, **kwargs):
        self.flask_app = flask_app
        super(Celery, self).__init__(*args, **kwargs)

    def __reduce_args__(self):
        return (self.flask_app, ) + super(Celery, self).__reduce_args__()



def to_Option(option, typemap={"int": int, "float": float, "string": str}):
    kwargs = vars(option)

    # convert type strings to real types.
    type_ = kwargs["type"]
    kwargs["type"] = typemap.get(type_) or type_

    # callback not supported by argparse, must use type|action instead.
    cb = kwargs.pop("callback", None)
    cb_args = kwargs.pop("callback_args", None) or ()
    cb_kwargs = kwargs.pop("callback_kwargs", None) or {}

    # action specific conversions
    action = kwargs["action"]
    if action == "store_true":
        map(kwargs.pop, ("const", "type", "nargs", "metavar", "choices"))
    elif action == "store":
        kwargs.pop("nargs")

    if kwargs["default"] == ("NO", "DEFAULT"):
        kwargs["default"] = None

    if action == "callback":

        class _action_cls(argparse.Action):

            def __call__(self, parser, namespace, values, option_string=None):
                return cb(*cb_args, **cb_kwargs)

        kwargs["action"] = _action_cls
        kwargs.setdefault("nargs", 0)

    args = kwargs.pop("_short_opts") + kwargs.pop("_long_opts")
    return script.Option(*args, **kwargs)


class Command(script.Command):

    def __init__(self, app):
        self.app = app
        super(Command, self).__init__()


class celeryd(Command):
    """Runs a Celery worker node."""

    def get_options(self):
        return filter(None, map(to_Option, self.worker.get_options()))

    def run(self, **kwargs):
        for arg_name, arg_value in kwargs.items():
            if isinstance(arg_value, list) and arg_value:
                kwargs[arg_name] = arg_value[0]
        self.worker.run(**kwargs)

    @cached_property
    def worker(self):
        from celery.bin.celeryd import WorkerCommand
        return WorkerCommand(app=current_celery())


class celerybeat(Command):
    """Runs the Celery periodic task scheduler."""

    def get_options(self):
        return filter(None, map(to_Option, self.beat.get_options()))

    def run(self, **kwargs):
        self.beat.run(**kwargs)

    @cached_property
    def beat(self):
        from celery.bin.celerybeat import BeatCommand
        return BeatCommand(app=current_celery())


class celeryev(Command):
    """Runs the Celery curses event monitor."""
    command = None

    def get_options(self):
        return filter(None, map(to_Option, self.ev.get_options()))

    def run(self, **kwargs):
        self.ev.run(**kwargs)

    @cached_property
    def ev(self):
        from celery.bin.celeryev import EvCommand
        return EvCommand(app=current_celery())


class celeryctl(Command):

    def get_options(self):
        return ()

    def handle(self, app, prog, name, remaining_args):
        if not remaining_args:
            remaining_args = ["help"]
        from celery.bin.celeryctl import celeryctl as ctl
        ctl(current_celery()).execute_from_commandline(
                ["%s celeryctl" % prog] + remaining_args)


class camqadm(Command):
    """Runs the Celery AMQP admin shell/utility."""

    def get_options(self):
        return ()

    def handle(self, app, prog, name, remaining_args):
        from celery.bin.camqadm import AMQPAdminCommand
        return AMQPAdminCommand(app=current_celery()).run(*remaining_args)


commands = {"celeryd": celeryd,
            "celerybeat": celerybeat,
            "celeryev": celeryev,
            "celeryctl": celeryctl,
            "camqadm": camqadm}


def install_commands(manager):
    for name, command in commands.items():
        manager.add_command(name, command(manager.app))

########NEW FILE########
__FILENAME__ = test_basic
import flask

import flask_celery as celery
from celery.tests.utils import unittest


class test_Celery(unittest.TestCase):

    def get_app(self, **kwargs):
        app = flask.Flask(__name__)
        default_config = dict(
            BROKER_TRANSPORT="memory",
        )
        app.config.update(default_config, **kwargs)
        return app

    def test_loader_is_configured(self):
        app = self.get_app()
        c = celery.Celery(app)
        self.assertEqual(c.conf.BROKER_TRANSPORT, "memory")
        self.assertIsInstance(c.loader, celery.FlaskLoader)
        self.assertTrue(c.loader.configured)

    def test_task_honors_app_settings(self):
        app = self.get_app(
            CELERY_IGNORE_RESULT=True,
            CELERY_TASK_SERIALIZER="msgpack",
        )
        c = celery.Celery(app)

        @c.task(foo=1)
        def add_task_args(x, y):
            return x + y

        @c.task
        def add_task_noargs(x, y):
            return x + y

        for task in add_task_args, add_task_noargs:
            #print(task.__class__.mro())
            #self.assertTrue(any("BaseFlaskTask" in repr(cls)
            #                    for cls in task.__class__.mro()))
            self.assertEqual(task(2, 2), 4)
            self.assertEqual(task.serializer, "msgpack")
            self.assertTrue(task.ignore_result)

    def test_establish_connection(self):
        app = self.get_app()
        c = celery.Celery(app)
        Task = c.create_task_cls()
        conn = Task.establish_connection()
        self.assertIn("kombu.transport.memory", repr(conn.create_backend()))
        conn.connect()

    def test_apply(self):
        app = self.get_app()
        c = celery.Celery(app)

        @c.task
        def add(x, y):
            return x + y

        res = add.apply_async((16, 16))
        self.assertTrue(res.task_id)

        consumer = add.get_consumer()
        while True:
            m = consumer.fetch()
            if m:
                break
        self.assertEqual(m.payload["task"], add.name)

    def test_Worker(self):
        app = self.get_app()
        c = celery.Celery(app)
        worker = c.Worker()
        self.assertTrue(worker)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
