__FILENAME__ = messages
from django.contrib.messages import constants
from . import message_user

"""
Mimic the django.contrib.messages API
"""


def debug(user, message):
    """
    Adds a message with the ``DEBUG`` level.

    :param user: User instance
    :param message: Message to show
    """
    message_user(user, message, constants.DEBUG)


def info(user, message):
    """
    Adds a message with the ``INFO`` level.

    :param user: User instance
    :param message: Message to show
    """
    message_user(user, message, constants.INFO)


def success(user, message):
    """
    Adds a message with the ``SUCCESS`` level.

    :param user: User instance
    :param message: Message to show
    """
    message_user(user, message, constants.SUCCESS)


def warning(user, message):
    """
    Adds a message with the ``WARNING`` level.

    :param user: User instance
    :param message: Message to show
    """
    message_user(user, message, constants.WARNING)


def error(user, message):
    """
    Adds a message with the ``ERROR`` level.

    :param user: User instance
    :param message: Message to show
    """
    message_user(user, message, constants.ERROR)

########NEW FILE########
__FILENAME__ = middleware
from django.contrib import messages

from async_messages import get_messages


class AsyncMiddleware(object):

    def process_response(self, request, response):
        """
        Check for messages for this user and, if it exists,
        call the messages API with it
        """
        if hasattr(request, "session") and hasattr(request, "user") and request.user.is_authenticated():
            msgs = get_messages(request.user)
            if msgs:
                for msg, level in msgs:
                    messages.add_message(request, level, msg)
        return response

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
import os

from django.conf import settings, global_settings

if not settings.configured:
    settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    }
                },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.admin',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.sites',
                'async_messages',
                'tests',
                ],
            MIDDLEWARE_CLASSES=global_settings.MIDDLEWARE_CLASSES + (
                'async_messages.middleware.AsyncMiddleware',
                ),
            ROOT_URLCONF='tests.urls',
            DEBUG=False,
            SITE_ID=1,
        )

from django.test.simple import DjangoTestSuiteRunner


def run_tests():
    # Modify path
    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    # Run tests
    test_runner = DjangoTestSuiteRunner(verbosity=2)
    failures = test_runner.run_tests(['tests'])
    sys.exit(failures)

if __name__ == '__main__':
    run_tests()

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.messages import constants, set_level

from async_messages import message_user, message_users, messages


class MiddlewareTests(TestCase):

    def setUp(self):
        username, password = 'david', 'password'
        self.user = User.objects.create_user(username, "django-async@test.com", password)
        self.client = Client()
        self.client.login(username=username, password=password)

    def test_message_appears_for_user(self):
        message_user(self.user, "Hello")
        response = self.client.get('/')
        msgs = list(response.context['messages'])
        self.assertEqual(1, len((msgs)))
        self.assertEqual('Hello', str((msgs)[0]))

    def test_message_appears_all_users(self):
        message_users(User.objects.all(), "Hello")
        response = self.client.get('/')
        msgs = list(response.context['messages'])
        self.assertEqual(1, len((msgs)))
        self.assertEqual('Hello', str((msgs)[0]))

    def test_message_queue(self):
        message_user(self.user, "First Message")
        message_user(self.user, "Second Message")
        response = self.client.get('/')
        msgs = list(response.context['messages'])
        self.assertEqual(2, len((msgs)))
        self.assertEqual('Second Message', str((msgs)[1]))


class AnonynousUserTests(TestCase):
    def test_anonymous(self):
        client = Client()
        response = client.get('/')
        msgs = list(response.context['messages'])
        self.assertEqual(0, len((msgs)))


class TestMessagesApi(TestCase):
    def setUp(self):
        username, password = 'david', 'password'
        self.user = User.objects.create_user(username, "django-async@test.com", password)
        self.client = Client()
        self.client.login(username=username, password=password)

    def assertMessageOk(self, level):
        response = self.client.get('/')
        msgs = list(response.context['messages'])
        self.assertEqual(1, len((msgs)))
        self.assertEqual('Hello', str((msgs)[0]))

    def test_info(self):
        messages.info(self.user, "Hello")
        self.assertMessageOk(constants.INFO)

    def test_success(self):
        messages.success(self.user, "Hello")
        self.assertMessageOk(constants.SUCCESS)

    def test_warning(self):
        messages.warning(self.user, "Hello")
        self.assertMessageOk(constants.WARNING)

    def test_error(self):
        messages.error(self.user, "Hello")
        self.assertMessageOk(constants.ERROR)

    def test_debug(self):
        messages.debug(self.user, "Hello")
        # 0 messages because by default django.contrib.messages ignore DEBUG
        # messages (this can be changed using set_level)
        response = self.client.get('/')
        msgs = list(response.context['messages'])
        self.assertEqual(0, len((msgs)))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'tests.views.index'),
)

########NEW FILE########
__FILENAME__ = views
from django.template.response import TemplateResponse
from django.template import Template


def index(request):
    t = Template("")
    return TemplateResponse(request, t, {'a': 1000})

########NEW FILE########
