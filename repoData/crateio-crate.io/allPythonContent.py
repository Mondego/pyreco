__FILENAME__ = fix_missing_files
from django.core.management.base import BaseCommand

from crate.web.packages.models import ReleaseFile
from crate.pypi.processor import PyPIPackage


class Command(BaseCommand):

    def handle(self, *args, **options):
        i = 0
        for rf in ReleaseFile.objects.filter(digest="").distinct("release"):
            print rf.release.package.name, rf.release.version
            p = PyPIPackage(rf.release.package.name, version=rf.release.version)
            p.process(skip_modified=False)
            i += 1
        print "Fixed %d releases" % i

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
import os.path
import posixpath

import djcelery

djcelery.setup_loader()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))

DEBUG = False
TEMPLATE_DEBUG = True

SERVE_MEDIA = DEBUG

INTERNAL_IPS = [
    "127.0.0.1",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "crate",
    }
}

TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"

USE_I18N = True
USE_L10N = True
USE_TZ = True

LOCALE_PATHS = [
    os.path.join(PROJECT_ROOT, os.pardir, "locale"),
]

LANGUAGES = (
    ("en", "English"),

    ("de", "German"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("pt-br", "Portuguese (Brazil)"),
    ("ru", "Russian"),
)

MEDIA_ROOT = os.path.join(PROJECT_ROOT, "site_media", "media")
MEDIA_URL = "/site_media/media/"


STATIC_ROOT = os.path.join(PROJECT_ROOT, "site_media", "static")
STATIC_URL = "/site_media/static/"

ADMIN_MEDIA_PREFIX = posixpath.join(STATIC_URL, "admin/")

# STATICFILES_DIRS = [
#     os.path.join(PROJECT_ROOT, "static"),
# ]

STATICFILES_FINDERS = [
    "staticfiles.finders.FileSystemFinder",
    "staticfiles.finders.AppDirectoriesFinder",
    "staticfiles.finders.LegacyAppDirectoriesFinder",
]

TEMPLATE_LOADERS = [
    "jingo.Loader",
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

JINGO_EXCLUDE_APPS = [
    "debug_toolbar",
    "admin",
    "admin_tools",
]

JINJA_CONFIG = {
    "extensions": [
        "jinja2.ext.i18n",
        "jinja2.ext.autoescape",
    ],
}

MIDDLEWARE_CLASSES = [
    "django_hosts.middleware.HostsMiddleware",
    "djangosecure.middleware.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "account.middleware.LocaleMiddleware",
]

ROOT_URLCONF = "crateweb.urls"
ROOT_HOSTCONF = "crateweb.hosts"

DEFAULT_HOST = "default"

WSGI_APPLICATION = "crateweb.wsgi.application"

TEMPLATE_DIRS = [
    os.path.join(PROJECT_ROOT, "templates"),
    os.path.join(PROJECT_ROOT, "templates", "_dtl"),
]

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "staticfiles.context_processors.static",
    "pinax_utils.context_processors.settings",
    "account.context_processors.account",
    "social_auth.context_processors.social_auth_by_type_backends",
]

INSTALLED_APPS = [
    # Admin Dashboard
    "admin_tools",
    "admin_tools.theming",
    "admin_tools.menu",
    "admin_tools.dashboard",

    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.markup",

    # Authentication / Accounts
    "account",
    "social_auth",

    # Static Files
    "staticfiles",

    # Backend Tasks
    "djcelery",

    # Search
    "haystack",
    "celery_haystack",
    "saved_searches",

    # Database
    "south",

    # API
    "tastypie",

    # Utility
    "django_hosts",
    "storages",
    "djangosecure",

    # Templating
    "jingo",

    "jutils.jhumanize",
    "jutils.jmetron",
    "jutils.jintercom",

    # project
    "crate.web.theme",
    "crate.web.packages",
    "crate.web.search",
    "crate.web.history",
    "crate.web.lists",
    "crate.web.utils",
    "crate.pypi",

    "cmds",
]

FIXTURE_DIRS = [
    os.path.join(PROJECT_ROOT, "fixtures"),
]

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

ACCOUNT_OPEN_SIGNUP = True
ACCOUNT_EMAIL_UNIQUE = True
ACCOUNT_EMAIL_CONFIRMATION_REQUIRED = True
ACCOUNT_EMAIL_CONFIRMATION_EMAIL = True
ACCOUNT_CONTACT_EMAIL = "support@crate.io"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "crate.web.social_auth.backends.OpenIDBackend",
    "social_auth.backends.contrib.github.GithubBackend",
    "social_auth.backends.contrib.bitbucket.BitbucketBackend",
]

SOCIAL_AUTH_PIPELINE = [
    "social_auth.backends.pipeline.social.social_auth_user",
    "crate.web.social_auth.pipeline.associate.associate_by_email",
    "social_auth.backends.pipeline.user.get_username",
    "crate.web.social_auth.pipeline.user.create_user",
    "social_auth.backends.pipeline.social.associate_user",
    "social_auth.backends.pipeline.social.load_extra_data",
    "social_auth.backends.pipeline.user.update_user_details",
]

PASSWORD_HASHERS = (
    "django.contrib.auth.hashers.BCryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.SHA1PasswordHasher",
    "django.contrib.auth.hashers.MD5PasswordHasher",
    "django.contrib.auth.hashers.CryptPasswordHasher",
)

GITHUB_EXTRA_DATA = [
    ("login", "display"),
]

SOCIAL_AUTH_ASSOCIATE_BY_MAIL = False

LOGIN_URL = "/account/login/"
LOGIN_REDIRECT_URL = "/"
LOGIN_ERROR_URL = "/"
LOGIN_REDIRECT_URLNAME = "search"
LOGOUT_REDIRECT_URLNAME = "search"

EMAIL_CONFIRMATION_DAYS = 2
EMAIL_DEBUG = DEBUG

DEBUG_TOOLBAR_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
}

CELERY_SEND_TASK_ERROR_EMAILS = True
CELERY_DISABLE_RATE_LIMITS = True
CELERY_TASK_PUBLISH_RETRY = True

CELERYD_MAX_TASKS_PER_CHILD = 10000

CELERY_IGNORE_RESULT = True

CELERY_TASK_RESULT_EXPIRES = 7 * 24 * 60 * 60  # 7 Days

CELERYD_HIJACK_ROOT_LOGGER = False

CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"

HAYSTACK_SEARCH_RESULTS_PER_PAGE = 15

AWS_QUERYSTRING_AUTH = False
AWS_S3_SECURE_URLS = False

AWS_HEADERS = {
    "Cache-Control": "max-age=31556926",
}


METRON_SETTINGS = {
    "google": {3: "UA-28759418-1"},
    "gauges": {3: "4f1e4cd0613f5d7003000002"}
}

ADMIN_TOOLS_INDEX_DASHBOARD = "crate.web.dashboard.CrateIndexDashboard"

########NEW FILE########
__FILENAME__ = base
from ..base import *

DEBUG = True
TEMPLATE_DEBUG = True

SERVE_MEDIA = DEBUG

SITE_ID = 1

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

REDIS = {
    "default": {
        "HOST": 'localhost',
        "PORT": 6379,
        "PASSWORD": '',
    }
}

PYPI_DATASTORE = "default"

LOCK_DATASTORE = "default"

MIDDLEWARE_CLASSES += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INSTALLED_APPS += [
    "debug_toolbar",
    "devserver",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEVSERVER_ARGS = [
    "--dozer",
]

DEVSERVER_IGNORED_PREFIXES = [
    "/site_media/",
]

DEVSERVER_MODULES = [
    # "devserver.modules.sql.SQLRealTimeModule",
    "devserver.modules.sql.SQLSummaryModule",
    "devserver.modules.profile.ProfileSummaryModule",

    # Modules not enabled by default
    "devserver.modules.ajax.AjaxDumpModule",
    "devserver.modules.cache.CacheSummaryModule",
    "devserver.modules.profile.LineProfilerModule",
]

# Configure Celery
BROKER_TRANSPORT = "redis"
BROKER_HOST = "localhost"
BROKER_PORT = 6379
BROKER_VHOST = "0"
BROKER_PASSWORD = None
BROKER_POOL_LIMIT = 10

CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_HOST = "localhost"
CELERY_REDIS_PORT = 6379
CELERY_REDIS_PASSWORD = None

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine",
        "URL": "http://127.0.0.1:9200/",
        "INDEX_NAME": "crate-dev",
    },
}

SIMPLE_API_URL = "https://simple.crate.io/"

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    #'haystack.panels.HaystackDebugPanel',
)

AWS_STATS_LOG_REGEX = "^cloudfront/dev/packages/"

########NEW FILE########
__FILENAME__ = base
import os
import urlparse

from ..base import *

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple"
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "sentry": {
            "level": "ERROR",
            "class": "raven.contrib.django.handlers.SentryHandler",
        },
    },
    "root": {
        "handlers": ["console", "sentry"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "sentry.errors": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
    }
}

if "DATABASE_URL" in os.environ:
    urlparse.uses_netloc.append("postgres")
    url = urlparse.urlparse(os.environ["DATABASE_URL"])
    DATABASES = {
        "default": {
            "ENGINE": {
                "postgres": "django.db.backends.postgresql_psycopg2"
            }[url.scheme],
            "NAME": url.path[1:],
            "USER": url.username,
            "PASSWORD": url.password,
            "HOST": url.hostname,
            "PORT": url.port
        }
    }

if "REDIS_URL" in os.environ:
    urlparse.uses_netloc.append("redis")
    url = urlparse.urlparse(os.environ["REDIS_URL"])

    REDIS = {
        "default": {
            "HOST": url.hostname,
            "PORT": url.port,
            "PASSWORD": url.password,
        }
    }

    CACHES = {
       "default": {
            "BACKEND": "redis_cache.RedisCache",
            "LOCATION": "%(HOST)s:%(PORT)s" % REDIS["default"],
            "KEY_PREFIX": "cache",
            "OPTIONS": {
                "DB": 0,
                "PASSWORD": REDIS["default"]["PASSWORD"],
            }
        }
    }

    PYPI_DATASTORE = "default"

    LOCK_DATASTORE = "default"

    # Celery Broker
    BROKER_TRANSPORT = "redis"

    BROKER_HOST = REDIS["default"]["HOST"]
    BROKER_PORT = REDIS["default"]["PORT"]
    BROKER_PASSWORD = REDIS["default"]["PASSWORD"]
    BROKER_VHOST = "0"

    BROKER_POOL_LIMIT = 10

    # Celery Results
    CELERY_RESULT_BACKEND = "redis"

    CELERY_REDIS_HOST = REDIS["default"]["HOST"]
    CELERY_REDIS_PORT = REDIS["default"]["PORT"]
    CELERY_REDIS_PASSWORD = REDIS["default"]["PORT"]

if "ELASTICSEARCH_URL" in os.environ:
    url = urlparse.urlparse(os.environ["ELASTICSEARCH_URL"])
    index = url.path

    if index.startswith("/"):
        index = index[1:]

    if index.endswith("/"):
        index = index[:-1]

    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine",
            "URL": urlparse.urlunparse([url.scheme, url.netloc, "/", "", "", ""]),
            "INDEX_NAME": index,
        },
    }

SITE_ID = 3

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

SERVER_EMAIL = "server@crate.io"
DEFAULT_FROM_EMAIL = "support@crate.io"

PACKAGE_FILE_STORAGE = "storages.backends.s3boto.S3BotoStorage"
PACKAGE_FILE_STORAGE_OPTIONS = {
    "bucket": os.environ["PACKAGE_BUCKET"],
    "custom_domain": os.environ["PACKAGE_DOMAIN"],
}

DEFAULT_FILE_STORAGE = "storages.backends.s3boto.S3BotoStorage"
STATICFILES_STORAGE = "crateweb.storage.CachedStaticS3BotoStorage"

STATICFILES_S3_OPTIONS = {
    "bucket": "crate-static-production",
    "custom_domain": "dtl9zya2lik3.cloudfront.net",
    "secure_urls": True,
}

STATIC_URL = "https://dtl9zya2lik3.cloudfront.net/"

ADMIN_MEDIA_PREFIX = STATIC_URL + "admin/"

AWS_STORAGE_BUCKET_NAME = "crate-media-production"
AWS_S3_CUSTOM_DOMAIN = "media.crate-cdn.com"

AWS_STATS_BUCKET_NAME = "crate-logs"
AWS_STATS_LOG_REGEX = "^(cloudfront\.production/|cloudfront/production/packages/)"

INTERCOM_APP_ID = "79qt2qu3"

SIMPLE_API_URL = "https://simple.crate.io/"

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31556926
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

SECRET_KEY = os.environ["SECRET_KEY"]

EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ["EMAIL_PORT"])
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
EMAIL_USE_TLS = True

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]

INTERCOM_USER_HASH_KEY = os.environ["INTERCOM_USER_HASH_KEY"]

GITHUB_APP_ID = os.environ["GITHUB_APP_ID"]
GITHUB_API_SECRET = os.environ["GITHUB_API_SECRET"]

BITBUCKET_CONSUMER_KEY = os.environ["BITBUCKET_CONSUMER_KEY"]
BITBUCKET_CONSUMER_SECRET = os.environ["BITBUCKET_CONSUMER_SECRET"]

########NEW FILE########
__FILENAME__ = gondor
import os

if "GONDOR_DATABASE_URL" in os.environ:
    os.environ.setdefault("DATABASE_URL", os.environ["GONDOR_DATABASE_URL"])

if "GONDOR_REDIS_URL" in os.environ:
    os.environ.setdefault("REDIS_URL", os.environ["GONDOR_REDIS_URL"])

from .base import *

MEDIA_ROOT = os.path.join(os.environ["GONDOR_DATA_DIR"], "site_media", "media")
STATIC_ROOT = os.path.join(os.environ["GONDOR_DATA_DIR"], "site_media", "static")

MEDIA_URL = "/site_media/media/"
STATIC_URL = "/site_media/static/"

FILE_UPLOAD_PERMISSIONS = 0640

########NEW FILE########
__FILENAME__ = heroku
from .base import *


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

########NEW FILE########
__FILENAME__ = hosts
from django.conf import settings

from django_hosts import patterns, host

host_patterns = patterns("",
    host(r"www", settings.ROOT_URLCONF, name="default"),
    host(r"simple", "crate.web.packages.simple.urls", name="simple"),
    host(r"pypi", "crate.pypi.simple.urls", name="pypi"),
    host(r"restricted", "crate.web.packages.simple.restricted_urls", name="restricted"),
)

########NEW FILE########
__FILENAME__ = storage
from django.conf import settings
from staticfiles.storage import CachedFilesMixin
from storages.backends.s3boto import S3BotoStorage


class CachedStaticS3BotoStorage(CachedFilesMixin, S3BotoStorage):
    def __init__(self, *args, **kwargs):
        kwargs.update(getattr(settings, "STATICFILES_S3_OPTIONS", {}))
        super(CachedStaticS3BotoStorage, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

import jutils.ji18n.translate
jutils.ji18n.translate.patch()

from crate.web.search.views import Search


handler500 = "pinax.views.server_error"


urlpatterns = patterns("",
    url(r"^security/$", direct_to_template, {"template": "security.html"}),
    url(r"^security.asc$", direct_to_template, {"template": "security.asc", "mimetype": "text/plain"}),
    url(r"^$", Search.as_view(), name="home"),
    url(r"^admin/", include(admin.site.urls)),
    #url(r"^about/", include("about.urls")),
    url(r"^account/", include("account.urls")),
    url(r"^account/", include("crate.web.social_auth.urls")),
    url(r"^admin_tools/", include("admin_tools.urls")),
    url(
        r"^social-auth/disconnect/(?P<backend>[^/]+)/(?P<association_id>[^/]+)/$",
        "crate.web.social_auth.views.disconnect",
    ),
    url(r"^social-auth/", include("social_auth.urls")),

    url(r"^users/", include("crate.web.lists.urls")),

    url(r"^packages/", include("crate.web.packages.urls")),

    url(r"^stats/", include("crate.web.packages.stats.urls")),
    #url(r"^help/", include("helpdocs.urls")),
    #url(r"^api/", include("crateweb.api_urls")),

    url(r"^externally-hosted/$", "crate.web.packages.views.fuck_the_status_quo"),

    url(r"^", include("crate.web.search.urls")),
)


if settings.SERVE_MEDIA:
    urlpatterns += patterns("",
        url(r"", include("staticfiles.urls")),
    )

########NEW FILE########
__FILENAME__ = wsgi
import os

if "USE_NEWRELIC" in os.environ:
    import newrelic.agent
    newrelic.agent.initialize()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if "USE_NEWRELIC" in os.environ and "celeryd" in sys.argv:
    import newrelic.agent

    newrelic.agent.initialize()

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
