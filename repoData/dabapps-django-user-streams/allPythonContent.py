__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'user_streams',
    'user_streams.backends.user_streams_single_table_backend',
    'user_streams.backends.user_streams_many_to_many_backend',
    'user_streams.backends.user_streams_redis_backend',
]

SECRET_KEY = 'foobar'

########NEW FILE########
__FILENAME__ = dummy

class DummyStreamItem(object):

    def __init__(self, content, created_at):
        self.content = content
        self.created_at = created_at


class MemoryStorage(object):

    def __init__(self):
        self.streams = {}

    def add_stream_item(self, users, content, created_at):
        stream_item = DummyStreamItem(content, created_at)
        for user in users:
            if user in self.streams:
                self.streams[user].insert(0, stream_item)
            else:
                self.streams[user] = [stream_item]

    def get_stream_items(self, user):
        return self.streams.get(user, [])

    def flush(self):
        self.streams = {}


storage = MemoryStorage()


class DummyBackend(object):

    """
    A dummy storage backend that stores user streams in memory.
    Only used for testing purposes.
    """

    def add_stream_item(self, users, content, created_at):
        storage.add_stream_item(users, content, created_at)

    def get_stream_items(self, user):
        return storage.get_stream_items(user)

    def flush(self):
        storage.flush()

########NEW FILE########
__FILENAME__ = models
from django.db import models


class StreamItem(models.Model):

    users = models.ManyToManyField('auth.User', related_name='+')
    content = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

########NEW FILE########
__FILENAME__ = tests
from user_streams import BACKEND_SETTING_NAME
from user_streams.tests import StreamStorageTestMixin
from user_streams.utils import TestCase, override_settings


BACKEND_SETTINGS = {BACKEND_SETTING_NAME: 'user_streams.backends.user_streams_many_to_many_backend.ManyToManyDatabaseBackend'}


@override_settings(**BACKEND_SETTINGS)
class ManyToManyDatabaseBackendTestCase(TestCase, StreamStorageTestMixin):
    pass

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from user_streams import BACKEND_SETTING_NAME
from user_streams.tests import StreamStorageTestMixin
from user_streams.utils import TestCase, override_settings

from . import Redis, KEY_PREFIX_SETTING_NAME


KEY_PREFIX = 'redis_backend_tests'
BACKEND_SETTINGS = {
    BACKEND_SETTING_NAME: 'user_streams.backends.user_streams_redis_backend.RedisBackend',
    KEY_PREFIX_SETTING_NAME: KEY_PREFIX,
}


@override_settings(**BACKEND_SETTINGS)
class RedisBackendTestCase(TestCase, StreamStorageTestMixin):

    def tearDown(self):
        client = Redis()
        keys = client.keys('%s*' % KEY_PREFIX)
        if keys:
            client.delete(*keys)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class StreamItem(models.Model):

    user = models.ForeignKey('auth.User', related_name='+')
    content = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

########NEW FILE########
__FILENAME__ = tests
from user_streams import BACKEND_SETTING_NAME
from user_streams.tests import StreamStorageTestMixin
from user_streams.utils import TestCase, override_settings


BACKEND_SETTINGS = {BACKEND_SETTING_NAME: 'user_streams.backends.user_streams_single_table_backend.SingleTableDatabaseBackend'}


@override_settings(**BACKEND_SETTINGS)
class SingleTableDatabaseBackendTestCase(TestCase, StreamStorageTestMixin):
    pass

########NEW FILE########
__FILENAME__ = compat
try:
    from django.utils.timezone import now as datetime_now
except ImportError:
    # Compat with previous 1.3 behavior
    from datetime import datetime
    from django.conf import settings
    if getattr(settings, 'USER_STREAMS_USE_UTC', False):
        datetime_now = datetime.utcnow
    else:
        datetime_now = datetime.now

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-


from datetime import timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator


from user_streams import BACKEND_SETTING_NAME, get_backend, add_stream_item, get_stream_items
from user_streams.backends.dummy import DummyBackend
from user_streams.compat import datetime_now
from user_streams.utils import TestCase, override_settings


DUMMY_BACKEND_SETTINGS = {BACKEND_SETTING_NAME: 'user_streams.backends.dummy.DummyBackend'}


class GetBackendTestCase(TestCase):

    def test_missing_setting(self):
        with self.assertRaises(ImproperlyConfigured):
            get_backend()

    def test_invalid_backend_path(self):
        settings = {BACKEND_SETTING_NAME: 'invalid'}
        with self.settings(**settings):
            with self.assertRaises(ImproperlyConfigured):
                get_backend()

    def test_incorrect_backend_path(self):
        settings = {BACKEND_SETTING_NAME: 'foo.bar.invalid.InvalidClass'}
        with self.settings(**settings):
            with self.assertRaises(ImproperlyConfigured):
                get_backend()

    def test_correct_backend_returned(self):
        with self.settings(**DUMMY_BACKEND_SETTINGS):
            backend = get_backend()
            self.assertTrue(isinstance(backend, DummyBackend))


class StreamStorageTestMixin(object):

    """
    A mixin providing a set of test cases that can be run to test
    any backend. Note that the backend MUST be emptied (all messages
    should be removed) between each test. If a database backend
    is being tested, this will happen automatically. Otherwise, you
    are responsible for deleting all the messages between tests.
    """

    def test_single_user(self):
        user = User.objects.create()
        content = 'Test message'

        add_stream_item(user, content)

        items = get_stream_items(user)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.content, content)

    def test_multiple_users(self):
        user_1 = User.objects.create(username='test1')
        user_2 = User.objects.create(username='test2')
        user_3 = User.objects.create(username='test3')
        content = 'Broadcast message'

        add_stream_item(User.objects.all(), content)

        for user in user_1, user_2, user_3:
            self.assertEqual(get_stream_items(user)[0].content, content)

    def test_message_ordering(self):
        user = User.objects.create()
        now = datetime_now()

        add_stream_item(user, 'Message 1', created_at=now)
        add_stream_item(user, 'Message 2', created_at=now + timedelta(minutes=1))
        add_stream_item(user, 'Message 3', created_at=now + timedelta(minutes=2))

        stream_items = get_stream_items(user)

        self.assertEqual(stream_items[0].content, 'Message 3')
        self.assertEqual(stream_items[1].content, 'Message 2')
        self.assertEqual(stream_items[2].content, 'Message 1')

    def test_slicing(self):
        user = User.objects.create()
        now = datetime_now()

        for count in range(10):
            created_at = now + timedelta(minutes=count)
            add_stream_item(user, 'Message %s' % count, created_at=created_at)

        stream_items = get_stream_items(user)

        first_five = stream_items[:5]
        self.assertEqual(len(first_five), 5)
        self.assertEqual(first_five[0].content, 'Message 9')
        self.assertEqual(first_five[4].content, 'Message 5')

        middle = stream_items[3:7]
        self.assertEqual(len(middle), 4)
        self.assertEqual(middle[0].content, 'Message 6')
        self.assertEqual(middle[3].content, 'Message 3')

        end = stream_items[6:]
        self.assertEqual(len(end), 4)
        self.assertEqual(end[0].content, 'Message 3')
        self.assertEqual(end[3].content, 'Message 0')

    def test_pagination(self):
        user = User.objects.create()
        now = datetime_now()

        for count in range(100):
            created_at = now + timedelta(minutes=count)
            add_stream_item(user, 'Message %s' % count, created_at=created_at)

        paginator = Paginator(get_stream_items(user), 10)
        self.assertEqual(paginator.num_pages, 10)

        page_1 = paginator.page(1)
        objects = page_1.object_list
        self.assertEqual(len(objects), 10)
        self.assertEqual(objects[0].content, 'Message 99')
        self.assertEqual(objects[9].content, 'Message 90')
        self.assertEqual(page_1.next_page_number(), 2)

        page_10 = paginator.page(10)
        objects = page_10.object_list
        self.assertEqual(len(objects), 10)
        self.assertEqual(objects[0].content, 'Message 9')
        self.assertEqual(objects[9].content, 'Message 0')
        self.assertFalse(page_10.has_next())

    def test_identical_messages(self):
        """Check that identical messages are handled properly. Mostly
        an issue for the Redis backend (which uses sets to store messages)"""
        user = User.objects.create()
        message = 'Test message'

        add_stream_item(user, message)
        add_stream_item(user, message)

        items = get_stream_items(user)
        self.assertEqual(len(items), 2)

    def test_unicode_handled_properly(self):
        user = User.objects.create()
        message = u'☃'

        add_stream_item(user, message)

        items = get_stream_items(user)
        self.assertEqual(items[0].content, message)



@override_settings(**DUMMY_BACKEND_SETTINGS)
class DummyBackendStreamTestCase(TestCase, StreamStorageTestMixin):

    def setUp(self):
        dummy_backend = get_backend()
        dummy_backend.flush()

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings, UserSettingsHolder
from django.test import TestCase as DjangoTestCase
from django.utils.functional import wraps


class OverrideSettingsHolder(UserSettingsHolder):
    """
    A custom setting holder that sends a signal upon change.
    """
    def __setattr__(self, name, value):
        UserSettingsHolder.__setattr__(self, name, value)


class override_settings(object):
    """
    Acts as either a decorator, or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement. In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """
    def __init__(self, **kwargs):
        self.options = kwargs
        self.wrapped = settings._wrapped

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from django.test import TransactionTestCase
        if isinstance(test_func, type) and issubclass(test_func, TransactionTestCase):
            original_pre_setup = test_func._pre_setup
            original_post_teardown = test_func._post_teardown
            def _pre_setup(innerself):
                self.enable()
                original_pre_setup(innerself)
            def _post_teardown(innerself):
                original_post_teardown(innerself)
                self.disable()
            test_func._pre_setup = _pre_setup
            test_func._post_teardown = _post_teardown
            return test_func
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
        return inner

    def enable(self):
        override = OverrideSettingsHolder(settings._wrapped)
        for key, new_value in self.options.items():
            setattr(override, key, new_value)
        settings._wrapped = override

    def disable(self):
        settings._wrapped = self.wrapped


class TestCase(DjangoTestCase):

    """TestCase base class with settings override functionality copied from Django 1.4"""

    def settings(self, **kwargs):
        """
        A context manager that temporarily sets a setting and reverts
        back to the original value when exiting the context.
        """
        return override_settings(**kwargs)

########NEW FILE########
