__FILENAME__ = admin
from django.contrib import admin
from jogging.models import Log

class LogAdmin(admin.ModelAdmin):
    date_hierarchy = 'datetime' 
    model = Log
    list_display = ['datetime', 'host', 'level', 'source', 'abbrev_msg']
    search_fields = ['source', 'msg', 'host']
    list_filter = ['level', 'source', 'host']

admin.site.register(Log, LogAdmin)

########NEW FILE########
__FILENAME__ = handlers
import datetime, logging
import platform

HOST = platform.uname()[1]

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

class MockHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        self.msgs = []
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.msgs.append(record)

class DatabaseHandler(logging.Handler):
    def emit(self, record):
        from jogging.models import Log
        
        if hasattr(record, 'source'):
            source = record.source
        else:
            source = record.name
        
        try:
            Log.objects.create(source=source, level=record.levelname, msg=record.msg, host=HOST)
        except:
            # squelching exceptions sucks, but 500-ing because of a logging error sucks more
            pass

class EmailHandler(logging.Handler):
    def __init__(self, from_email=None, recipient_spec=None, fail_silently=False, auth_user=None, auth_password=None, *args, **kwargs):
        logging.Handler.__init__(self, *args, **kwargs)
        self.recipient_spec = recipient_spec or () 
        self.from_email = from_email
        self.auth_user = auth_user
        self.auth_password = auth_password
        self.fail_silently = fail_silently

    def emit(self, record):
        from django.conf import settings
        from django.core.mail import send_mail 

        if hasattr(record, 'source'):
            source = record.source
        else:
            source = record.name

        send_mail(
            subject="%s[%s] %s: %s" % (settings.EMAIL_SUBJECT_PREFIX, HOST, source, record.levelname.upper()),
            message=record.msg,
            from_email=self.from_email or settings.SERVER_EMAIL,
            recipient_list=[a[1] for a in (self.recipient_spec or settings.ADMINS)],
            fail_silently=self.fail_silently,
            auth_user=self.auth_user,
            auth_password=self.auth_password,
        )

########NEW FILE########
__FILENAME__ = middleware
class LoggingMiddleware(object):
    
    def process_exception(self, request, exception):
        from jogging import logging
        logging.exception(exception=exception, request=request)

########NEW FILE########
__FILENAME__ = models
import datetime

import logging as py_logging

from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


class Log(models.Model):
    "A log message, used by jogging's DatabaseHandler"
    datetime = models.DateTimeField(default=datetime.datetime.now)
    level = models.CharField(max_length=128)
    msg = models.TextField()
    source = models.CharField(max_length=128, blank=True)
    host = models.CharField(max_length=200, blank=True, null=True)

    def abbrev_msg(self, maxlen=500):
        if len(self.msg) > maxlen:
            return u'%s ...' % self.msg[:maxlen]
        return self.msg
    abbrev_msg.short_description = u'abbreviated msg'
    
    class Meta:
        get_latest_by = 'datetime'


## Set up logging handlers

def jogging_init():
    def add_handlers(logger, handlers):
        if not handlers:
            return

        for handler in handlers:
            if type(handler) is dict:
                if 'format' in handler:
                    handler['handler'].setFormatter(py_logging.Formatter(handler['format']))
                if 'level' in handler:
                    handler['handler'].setLevel(handler['level'])
                logger.addHandler(handler['handler'])
            else:
                logger.addHandler(handler)

    if hasattr(settings, 'LOGGING') and settings.LOGGING:
        for module, properties in settings.LOGGING.items():
            logger = py_logging.getLogger(module)

            if 'level' in properties:
                logger.setLevel(properties['level'])
            elif hasattr(settings, 'GLOBAL_LOG_LEVEL'):
                logger.setLevel(settings.GLOBAL_LOG_LEVEL)
            elif 'handlers' in properties:
                # set the effective log level of this logger to the lowest so
                # that logging decisions will always be passed to the handlers
                logger.setLevel(1)
                pass
            else:
                raise ImproperlyConfigured(
                    "A logger in settings.LOGGING doesn't have its log level set. " +
                    "Either set a level on that logger, or set GLOBAL_LOG_LEVEL.")

            handlers = [] 
            if 'handler' in properties:
                handlers = [properties['handler']]
            elif 'handlers' in properties:
                handlers = properties['handlers']
            elif hasattr(settings, 'GLOBAL_LOG_HANDLERS'):
                handlers = settings.GLOBAL_LOG_HANDLERS

            add_handlers(logger, handlers)

    if hasattr(settings, 'GLOBAL_LOG_LEVEL') and settings.GLOBAL_LOG_LEVEL and \
            hasattr(settings, 'GLOBAL_LOG_HANDLERS') and settings.GLOBAL_LOG_HANDLERS:
        logger = py_logging.getLogger('')
        logger.setLevel(settings.GLOBAL_LOG_LEVEL)
        handlers = settings.GLOBAL_LOG_HANDLERS

        add_handlers(logger, handlers)

jogging_init()

########NEW FILE########
__FILENAME__ = tests
#:coding=utf8:

import logging

from django.test import TestCase as DjangoTestCase
from django.conf import settings

from jogging.models import Log, jogging_init

class DatabaseHandlerTestCase(DjangoTestCase):
    
    def setUp(self):
        from jogging.handlers import DatabaseHandler, MockHandler
        import logging
        
        self.LOGGING = getattr(settings, 'LOGGING', None)
        
        settings.LOGGING = {
            'database_test': {
                'handler': DatabaseHandler(),
                'level': logging.DEBUG,
            },
            'multi_test': {
                'handlers': [
                    { 'handler': DatabaseHandler(), 'level': logging.DEBUG },
                    { 'handler': MockHandler(), 'level': logging.DEBUG },
                ],
            },
        }
        
        jogging_init()
    
    def tearDown(self):
        import logging

        # clear out all handlers on loggers
        loggers = [logging.getLogger(""), logging.getLogger("database_test"), logging.getLogger("multi_test")]
        for logger in loggers:
            logger.handlers = []
        
        # delete all log entries in the database
        for l in Log.objects.all():
            l.delete()
        
        if self.LOGGING:
            settings.LOGGING = self.LOGGING
        jogging_init()
    
    def test_basic(self):
        logger = logging.getLogger("database_test")
        logger.info("My Logging Test")
        log_obj = Log.objects.latest()
        self.assertEquals(log_obj.level, "INFO")
        self.assertEquals(log_obj.source, "database_test")
        self.assertEquals(log_obj.msg, "My Logging Test")
        self.assertTrue(log_obj.host)
    
    def test_multi(self):
        logger = logging.getLogger("multi_test")
        logger.info("My Logging Test")
        
        log_obj = Log.objects.latest()
        self.assertEquals(log_obj.level, "INFO")
        self.assertEquals(log_obj.source, "multi_test")
        self.assertEquals(log_obj.msg, "My Logging Test")
        self.assertTrue(log_obj.host)
        
        log_obj = settings.LOGGING["multi_test"]["handlers"][1]["handler"].msgs[0]
        self.assertEquals(log_obj.levelname, "INFO")
        self.assertEquals(log_obj.name, "multi_test")
        self.assertEquals(log_obj.msg, "My Logging Test")

class DictHandlerTestCase(DjangoTestCase):

    def setUp(self):
        from jogging.handlers import MockHandler
        import logging
        
        self.LOGGING = getattr(settings, 'LOGGING', None)

        settings.LOGGING = {
            'dict_handler_test': {
                'handlers': [
                    { 'handler': MockHandler(), 'level': logging.ERROR },
                    { 'handler': MockHandler(), 'level': logging.INFO },
                ],
            },
        }
        
        jogging_init()
    
    def tearDown(self):
        import logging

        # clear out all handlers on loggers
        loggers = [logging.getLogger(""), logging.getLogger("database_test"), logging.getLogger("multi_test")]
        for logger in loggers:
            logger.handlers = []
        
        # delete all log entries in the database
        for l in Log.objects.all():
            l.delete()
        
        if self.LOGGING:
            settings.LOGGING = self.LOGGING
        jogging_init()
    
    def test_basic(self):
        logger = logging.getLogger("dict_handler_test")
        error_handler = settings.LOGGING["dict_handler_test"]["handlers"][0]["handler"]
        info_handler = settings.LOGGING["dict_handler_test"]["handlers"][1]["handler"]


        logger.info("My Logging Test")
        # Make sure we didn't log to the error handler
        self.assertEquals(len(error_handler.msgs), 0)

        log_obj = info_handler.msgs[0]
        self.assertEquals(log_obj.levelname, "INFO")
        self.assertEquals(log_obj.name, "dict_handler_test")
        self.assertEquals(log_obj.msg, "My Logging Test")

class GlobalExceptionTestCase(DjangoTestCase):
    urls = 'jogging.tests.urls'
    
    def setUp(self):
        from jogging.handlers import DatabaseHandler, MockHandler
        import logging
        
        self.LOGGING = getattr(settings, 'LOGGING', None)
        self.GLOBAL_LOG_HANDLERS = getattr(settings, 'GLOBAL_LOG_HANDLERS', None)
        self.GLOBAL_LOG_LEVEL = getattr(settings, 'GLOBAL_LOG_LEVEL', None)
        
        loggers = [logging.getLogger("")]
        for logger in loggers:
            logger.handlers = []
        
        settings.LOGGING = {}
        settings.GLOBAL_LOG_HANDLERS = [MockHandler()]
        settings.GLOBAL_LOG_LEVEL = logging.DEBUG
        
        jogging_init()
    
    def tearDown(self):
        import logging

        # clear out all handlers on loggers
        loggers = [logging.getLogger("")]
        for logger in loggers:
            logger.handlers = []
        
        # delete all log entries in the database
        for l in Log.objects.all():
            l.delete()
        
        if self.LOGGING:
            settings.LOGGING = self.LOGGING
        if self.GLOBAL_LOG_HANDLERS:
            settings.GLOBAL_LOG_HANDLERS = self.GLOBAL_LOG_HANDLERS
        if self.GLOBAL_LOG_LEVEL:
            settings.GLOBAL_LOG_LEVEL = self.GLOBAL_LOG_LEVEL
        jogging_init()
 
    def test_exception(self):
        from views import TestException
        try:
            resp = self.client.get("/exception_view")
            self.fail("Expected Exception")
        except TestException:
            pass
        root_handler = logging.getLogger("").handlers[0]

        log_obj = root_handler.msgs[0]
        self.assertEquals(log_obj.levelname, "ERROR")
        self.assertEquals(log_obj.name, "root")
        self.assertTrue("Traceback" in log_obj.msg)

########NEW FILE########
__FILENAME__ = urls
#:coding=utf-8:
from django.conf.urls.defaults import *
from django.conf import settings

urlpatterns = patterns('',
    (r'exception_view', 'jogging.tests.views.exception_view'),
)

########NEW FILE########
__FILENAME__ = views
#:coding=utf8:

class TestException(Exception):
    pass

def exception_view(request):
    raise TestException("This is a test exception")

########NEW FILE########
__FILENAME__ = tests
import os
import sys
import unittest
import doctest
import django
import logging

APP_MODULE = 'jogging'

def main():
    """
    Standalone django model test with a 'memory-only-django-installation'.
    You can play with a django model without a complete django app installation.
    http://www.djangosnippets.org/snippets/1044/
    """
    os.environ["DJANGO_SETTINGS_MODULE"] = "django.conf.global_settings"
    from django.conf import global_settings

    global_settings.INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        APP_MODULE,
    )
    global_settings.DATABASE_ENGINE = "sqlite3"
    global_settings.DATABASE_NAME = ":memory:"
    global_settings.ROOT_URLCONF = 'jogging.tests.urls'

    global_settings.MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'jogging.middleware.LoggingMiddleware',
    )

    # jogging settings must be set up here.
    from jogging.handlers import DatabaseHandler, MockHandler
    global_settings.GLOBAL_LOG_HANDLERS = []
    global_settings.GLOBAL_LOG_LEVEL = logging.INFO
    global_settings.LOGGING = {}

    from django.test.utils import get_runner
    test_runner = get_runner(global_settings)

    if django.VERSION > (1,2):
        test_runner = test_runner()
        failures = test_runner.run_tests([APP_MODULE])
    else:
        failures = test_runner([APP_MODULE], verbosity=1)
    sys.exit(failures)

if __name__ == '__main__':
    main()

########NEW FILE########
