__FILENAME__ = fixture_gen
def fixture_generator(*models, **kwargs):
    requires = kwargs.pop("requires", [])
    if kwargs:
        raise TypeError("fixture_generator got an unexpected keyword argument:"
            " %r", iter(kwargs).next())
    def inner(func):
        func.models = models
        func.requires = requires
        func.__fixture_gen__ = True
        return func
    return inner

########NEW FILE########
__FILENAME__ = generate_fixture
import os
from optparse import make_option

from django.core.management import BaseCommand, call_command, CommandError
from django.core.management.commands.dumpdata import Command as DumpDataCommand
from django.conf import settings
from django.db import router, connections
from django.utils.importlib import import_module
from django.utils.module_loading import module_has_submodule


FIXTURE_DATABASE = "__fixture_gen__"

class CircularDependencyError(Exception):
    """
    Raised when there is a circular dependency in fixture requirements.
    """
    pass

def linearize_requirements(available_fixtures, fixture, seen=None):
    if seen is None:
        seen = set([fixture])
    requirements = []
    models = []

    for requirement in fixture.requires:
        app_label, fixture_name = requirement.rsplit(".", 1)
        fixture_func = available_fixtures[(app_label, fixture_name)]
        if fixture_func in seen:
            raise CircularDependencyError
        r, m = linearize_requirements(
            available_fixtures,
            fixture_func,
            seen | set([fixture_func])
        )
        requirements.extend([req for req in r if req not in requirements])
        models.extend([model for model in m if model not in models])

    models.extend([model for model in fixture.models if model not in models])
    requirements.append(fixture)
    return requirements, models


class FixtureRouter(object):
    def __init__(self, models):
        self.models = models

    def db_for_read(self, model, instance=None, **hints):
        return FIXTURE_DATABASE

    def db_for_write(self, model, instance=None, **hints):
        return FIXTURE_DATABASE

    def allow_relation(self, *args, **kwargs):
        return True

    def allow_syncdb(self, db, model):
        return True


class Command(BaseCommand):
    option_list = tuple(
        opt for opt in DumpDataCommand.option_list
        if "--database" not in opt._long_opts and "--exclude" not in opt._long_opts
    )
    args = "app_label.fixture"

    def handle(self, fixture, **options):
        available_fixtures = {}
        for app in settings.INSTALLED_APPS:
            try:
                fixture_gen = import_module(".fixture_gen", app)
            except ImportError:
                if module_has_submodule(import_module(app), "fixture_gen"):
                   raise
                continue
            for obj in fixture_gen.__dict__.values():
                if getattr(obj, "__fixture_gen__", False):
                    available_fixtures[(app.rsplit(".", 1)[-1], obj.__name__)] = obj
        app_label, fixture_name = fixture.rsplit(".", 1)
        try:
            fixture = available_fixtures[(app_label, fixture_name)]
        except KeyError:
            available = ", ".join(
                "%s.%s" % (app_label, fixture_name)
                for app_label, fixture_name in available_fixtures
            )
            raise CommandError("Fixture generator '%s' not found, available "
                "choices: %s" % (fixture, available))

        requirements, models = linearize_requirements(available_fixtures, fixture)

        settings.DATABASES[FIXTURE_DATABASE] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
        old_routers = router.routers
        router.routers = [FixtureRouter(models)]
        try:
            # migrate_all=True is for south, Django just absorbs it
            call_command("syncdb", database=FIXTURE_DATABASE, verbosity=0,
                interactive=False, migrate_all=True)
            for fixture_func in requirements:
                fixture_func()
            call_command("dumpdata",
                *["%s.%s" % (m._meta.app_label, m._meta.object_name) for m in models],
                **dict(options, verbosity=0, database=FIXTURE_DATABASE)
            )
        finally:
            del settings.DATABASES[FIXTURE_DATABASE]
            if isinstance(connections._connections, dict):
                del connections._connections[FIXTURE_DATABASE]
            else:
                delattr(connections._connections, FIXTURE_DATABASE)
            router.routers = old_routers

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = fixture_gen
from django.contrib.auth.models import User

from fixture_generator import fixture_generator
from fixture_generator.tests.models import Author, Entry


@fixture_generator(Author)
def test_1():
    Author.objects.create(name="Tom Clancy")
    Author.objects.create(name="Daniel Pinkwater")

@fixture_generator(User)
def test_2():
    pass

@fixture_generator(Entry)
def test_3():
    Entry.objects.create(public=True)
    Entry.objects.create(public=False)
########NEW FILE########
__FILENAME__ = models
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)


class EntryManager(models.Manager):
    def get_query_set(self):
        return super(EntryManager, self).get_query_set().filter(public=True)

class Entry(models.Model):
    public = models.BooleanField()

    objects = EntryManager()
########NEW FILE########
__FILENAME__ = tests
import sys
from StringIO import StringIO

import django
from django.core.management import call_command
from django.test import TestCase

from fixture_generator import fixture_generator
from fixture_generator.management.commands.generate_fixture import (
    linearize_requirements, CircularDependencyError)


@fixture_generator()
def test_func_1():
    pass

@fixture_generator(requires=["tests.test_func_3", "tests.test_func_4"])
def test_func_2():
    pass

@fixture_generator(requires=["tests.test_func_5"])
def test_func_3():
    pass

@fixture_generator(requires=["tests.test_func_5"])
def test_func_4():
    pass

@fixture_generator()
def test_func_5():
    pass

@fixture_generator(requires=["tests.test_func_7"])
def test_func_6():
    pass

@fixture_generator(requires=["tests.test_func_6"])
def test_func_7():
    pass

class LinearizeRequirementsTests(TestCase):
    def setUp(self):
        self.available_fixtures = {}
        fixtures = [
            "test_func_1", "test_func_2", "test_func_3", "test_func_4",
            "test_func_5", "test_func_6", "test_func_7",
        ]
        for fixture in fixtures:
            self.available_fixtures[("tests", fixture)] = globals()[fixture]

    def linearize_requirements(self, test_func):
        return linearize_requirements(self.available_fixtures, test_func)

    def test_basic(self):
        requirements, models = self.linearize_requirements(test_func_1)
        self.assertEqual(requirements, [test_func_1])
        self.assertEqual(models, [])

    def test_diamond(self):
        requirements, models = self.linearize_requirements(test_func_2)
        self.assertEqual(
            requirements,
            [test_func_5, test_func_3, test_func_4, test_func_2]
        )

    def test_circular(self):
        self.assertRaises(CircularDependencyError,
            linearize_requirements, self.available_fixtures, test_func_6
        )


class ManagementCommandTests(TestCase):
    def generate_fixture(self, fixture, error=False, **kwargs):
        stdout = StringIO()
        stderr = StringIO()
        run = lambda: call_command("generate_fixture", fixture, stdout=stdout, stderr=stderr, **kwargs)

        if error:
            # CommandError gets turned into SystemExit
            self.assertRaises(SystemExit, run)
        else:
            run()
        return stdout.getvalue(), stderr.getvalue()

    def test_basic(self):
        output, _ = self.generate_fixture("tests.test_1")
        self.assertEqual(output, """[{"pk": 1, "model": "tests.author", "fields": {"name": "Tom Clancy"}}, {"pk": 2, "model": "tests.author", "fields": {"name": "Daniel Pinkwater"}}]""")

    def test_auth(self):
        # All that we're checking for is that it doesn't hang on this call,
        # which would happen if the auth post syncdb hook goes and prompts the
        # user to create an account.
        output, _ = self.generate_fixture("tests.test_2")
        self.assertEqual(output, "[]")

    def test_all(self):
        if django.VERSION < (1, 3):
            return
        output, _ = self.generate_fixture("tests.test_3", use_base_manager=True)
        self.assertEqual(output, """[{"pk": 1, "model": "tests.entry", "fields": {"public": true}}, {"pk": 2, "model": "tests.entry", "fields": {"public": false}}]""")

    def test_nonexistant(self):
        out, err = self.generate_fixture("tests.test_255", error=True)
        # Has a leading shell color thingy.
        self.assertTrue("Error: Fixture generator 'tests.test_255' not found" in err)
        self.assertFalse(out)

        out, err = self.generate_fixture("xxx.xxx", error=True)
        self.assertTrue("Error: Fixture generator 'xxx.xxx' not found" in err)
        self.assertFalse(out)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys

from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES = {
            "default": {
                 "ENGINE": "django.db.backends.sqlite3",
                 "NAME": ":memory:",
            },
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "fixture_generator",
            "fixture_generator.tests",
        ]
    )

from django.core.management import call_command


def runtests(*test_args):
    if not test_args:
        test_args = ["tests"]
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    call_command("test", *test_args)


if __name__ == '__main__':
    runtests(*sys.argv[1:])


########NEW FILE########
