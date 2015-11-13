__FILENAME__ = base
from django.utils.translation import ugettext_lazy as _


class HealthCheckStatusType(object):
    unavailable = 0
    working = 1
    unexpected_result = 2

HEALTH_CHECK_STATUS_TYPE_TRANSLATOR = {
    0: _("unavailable"),
    1: _("working"),
    2: _("unexpected result"),
}


class HealthCheckException(Exception):
    pass


class ServiceUnavailable(HealthCheckException):
    message = HEALTH_CHECK_STATUS_TYPE_TRANSLATOR[0]
    code = 0


class ServiceReturnedUnexpectedResult(HealthCheckException):
    message = HEALTH_CHECK_STATUS_TYPE_TRANSLATOR[2]
    code = 2


class BaseHealthCheckBackend(object):

    def check_status(self):
        return None

    @property
    def status(self):
        if not getattr(self, "_status", False):
            try:
                setattr(self, "_status", self.check_status())
            except (ServiceUnavailable, ServiceReturnedUnexpectedResult) as e:
                setattr(self, "_status", e.code)

        return self._status

    def pretty_status(self):
        return u"%s" % (HEALTH_CHECK_STATUS_TYPE_TRANSLATOR[self.status])

    @classmethod
    def identifier(cls):
        return cls.__name__


########NEW FILE########
__FILENAME__ = models
from django.db import models


class TestModel(models.Model):
    title = models.CharField(max_length=128)
########NEW FILE########
__FILENAME__ = plugins
# This is heavily inspired by the django admin sites.py

from health_check.backends.base import BaseHealthCheckBackend

class AlreadyRegistered(Exception):
    pass

class NotRegistered(Exception):
    pass

class HealthCheckPluginDirectory(object):
    """
    An AdminSite object encapsulates an instance of the Django admin application, ready
    to be hooked in to your URLconf. Models are registered with the AdminSite using the
    register() method, and the get_urls() method can then be used to access Django view
    functions that present a full admin interface for the collection of registered
    models.
    """

    def __init__(self):
        self._registry = {} # model_class class -> admin_class instance

    def register(self, plugin, admin_class=None, **options):
        """
        Registers the given model(s) with the given admin class.

        The model(s) should be Model classes, not instances.

        If an admin class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.

        If a model is already registered, this will raise AlreadyRegistered.

        If a model is abstract, this will raise ImproperlyConfigured.
        """
        if plugin in self._registry:
            raise AlreadyRegistered('The model %s is already registered' % plugin.__name__)
        # Instantiate the admin class to save in the registry
        self._registry[plugin] = plugin()

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, BaseHealthCheckBackend):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]


plugin_dir = HealthCheckPluginDirectory()
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

import health_check
health_check.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'health_check.views.home', name='health_check_home'),
)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from django.db.models.options import get_verbose_name
from health_check.backends.base import HealthCheckStatusType, BaseHealthCheckBackend
from health_check.plugins import plugin_dir


class BaseHealthCheck(BaseHealthCheckBackend):
    def check_status(self):
        self._wrapped()


def healthcheck(func_or_name):
    """
    Usage:

        @healthcheck("My Check")
        def my_check():
            if something_is_not_okay():
                raise ServiceReturnedUnexpectedResult()

        @healthcheck
        def other_check():
            if something_is_not_available():
                raise ServiceUnavailable()
    """
    def inner(func):
        cls = type(func.__name__, (BaseHealthCheck,), {'_wrapped': staticmethod(func)})
        cls.identifier = name
        plugin_dir.register(cls)
        return func
    if callable(func_or_name):
        name = get_verbose_name(func_or_name.__name__).replace('_', ' ')
        return inner(func_or_name)
    else:
        name = func_or_name
        return inner

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseServerError
from django.template import loader
from health_check.plugins import plugin_dir


def home(request):
    plugins = []
    working = True
    for plugin_class, plugin in plugin_dir._registry.items():
        plugin = plugin_class()
        if not plugin.status:  # Will return True or None
            working = False
        plugins.append(plugin)
    plugins.sort(key=lambda x: x.identifier())

    if working:
        return HttpResponse(loader.render_to_string("health_check/dashboard.html", {'plugins': plugins}))
    else:
        return HttpResponseServerError(loader.render_to_string("health_check/dashboard.html", {'plugins': plugins}))

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = plugin_health_check
from django.core.cache.backends.base import CacheKeyWarning
from health_check.backends.base import BaseHealthCheckBackend, ServiceUnavailable, ServiceReturnedUnexpectedResult
from health_check.plugins import plugin_dir
from django.core.cache import cache

class CacheBackend(BaseHealthCheckBackend):

    def check_status(self):
        try:
            cache.set('djangohealtcheck_test', 'itworks', 1)
            if cache.get("djangohealtcheck_test") == "itworks":
                return True
            else:
                raise ServiceUnavailable("Cache key does not match")
        except CacheKeyWarning:
            raise ServiceReturnedUnexpectedResult("Cache key warning")
        except ValueError:
            raise ServiceReturnedUnexpectedResult("ValueError")
        except Exception:
            raise ServiceUnavailable("Unknown exception")

plugin_dir.register(CacheBackend)
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = plugin_health_check
from health_check.plugins import plugin_dir
from health_check.backends.base import BaseHealthCheckBackend, ServiceUnavailable
from health_check_celery.tasks import add
from datetime import datetime, timedelta
from time import sleep


class CeleryHealthCheck(BaseHealthCheckBackend):

    def check_status(self):
        try:
            result = add.apply_async(args=[4, 4], expires=datetime.now() + timedelta(seconds=3), connect_timeout=3)
            now = datetime.now()
            while (now + timedelta(seconds=3)) > datetime.now():
                if result.result == 8:
                    return True
                sleep(0.5)
        except IOError:
            pass
        raise ServiceUnavailable("Unknown error")

plugin_dir.register(CeleryHealthCheck)

########NEW FILE########
__FILENAME__ = tasks
from celery.task import task

@task
def add(x, y):
    return x + y
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = plugin_health_check
from health_check.backends.base import BaseHealthCheckBackend, ServiceUnavailable, ServiceReturnedUnexpectedResult
from health_check.models import TestModel
from django.db import DatabaseError, IntegrityError
from health_check.plugins import plugin_dir

class DjangoDatabaseBackend(BaseHealthCheckBackend):

    def check_status(self):
        try:
            obj = TestModel.objects.create(title="test")
            obj.title = "newtest"
            obj.save()
            obj.delete()
            return True
        except IntegrityError:
            raise ServiceReturnedUnexpectedResult("Integrity Error")
        except DatabaseError:
            raise ServiceUnavailable("Database error")

plugin_dir.register(DjangoDatabaseBackend)
########NEW FILE########
__FILENAME__ = base
#-*- coding: utf-8 -*-
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from health_check.backends.base import BaseHealthCheckBackend, ServiceUnavailable
import random
import datetime


class StorageHealthCheck(BaseHealthCheckBackend):
    """
    Tests the status of a StorageBakcend. Can be extended to test any storage backend by subclassing:

        class MyStorageHealthCheck(StorageHealthCheck):
            storage = 'some.other.StorageBackend'
        plugin_dir.register(MyStorageHealthCheck)

    storage must be either a string pointing to a storage class (e.g 'django.core.files.storage.FileSystemStorage') or
    a Storage instance.
    """
    storage = None

    def get_storage(self):
        if isinstance(self.storage, basestring):
            return get_storage_class(self.storage)()
        else:
            return self.storage

    def get_file_name(self):
        return 'health_check_storage_test/test-%s-%s.txt' % (datetime.datetime.now(), random.randint(10000,99999))

    def get_file_content(self):
        return 'this is the healthtest file content'

    def check_status(self):
        try:
            # write the file to the storage backend
            storage = self.get_storage()
            file_name = self.get_file_name()
            file_content = self.get_file_content()

            # save the file
            file_name = storage.save(file_name, ContentFile(content=file_content))
            # read the file and compare
            f = storage.open(file_name)
            if not storage.exists(file_name):
                raise ServiceUnavailable("File does not exist")
            if not f.read() == file_content:
                return ServiceUnavailable("File content doesn't match")
            # delete the file and make sure it is gone
            storage.delete(file_name)
            if storage.exists(file_name):
                return ServiceUnavailable("File was not deleted")
            return True
        except Exception:
            return ServiceUnavailable("Unknown exception")
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = plugin_health_check
#-*- coding: utf-8 -*-
from health_check.plugins import plugin_dir
from health_check_storage.base import StorageHealthCheck
from django.conf import settings


class DefaultFileStorageHealthCheck(StorageHealthCheck):
    storage = settings.DEFAULT_FILE_STORAGE

plugin_dir.register(DefaultFileStorageHealthCheck)

########NEW FILE########
