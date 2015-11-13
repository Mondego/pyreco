__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys


if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings.{}".format(sys.argv[1]))
    execute_from_command_line([sys.argv[0]] + sys.argv[2:])


########NEW FILE########
__FILENAME__ = base
import os


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

SECRET_KEY = "{{ secret_key }}"


MANAGERS = ADMINS = []

SITE_ID = 1

USE_I18N = True
USE_L10N = True

TIME_ZONE = "America/Chicago"
LANGUAGE_CODE = "en-us"

# These are for user-uploaded content.
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "site_media")
MEDIA_URL = "/media/"

# These are for site static media (e.g. CSS and JS)
# This one is where static content is collected to.
STATIC_ROOT = os.path.join(PROJECT_ROOT, "static_root")
STATIC_URL = "/static/"
ADMIN_MEDIA_PREFIX = "/static/admin/"
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, "static"),
]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Template stuff   
TEMPLATE_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",    
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
]

TEMPLATE_DIRS = [
    os.path.join(PROJECT_ROOT, "templates"),
]


ROOT_URLCONF = "{{ project_name }}.urls"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

INSTALLED_APPS = [
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

########NEW FILE########
__FILENAME__ = development
import os

from {{ project_name }}.settings.base import *


DEBUG = TEMPLATE_DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(PROJECT_ROOT, "dev.db"),
    },
}

########NEW FILE########
__FILENAME__ = production
from {{ project_name }}.settings.base import *


DEBUG = TEMPLATE_DEBUG = False

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


urlpatterns = patterns("",
) + staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for {{ project_name }} project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# Because we have multiple settings files, this is commented out by default,
# you should pass this in the enviroment.
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
