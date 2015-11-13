__FILENAME__ = models
from django.db import models

from django.contrib.sessions.models import Session


class Task(models.Model):
    
    session = models.ForeignKey(Session)
    label = models.CharField(max_length=100)
    done = models.BooleanField(default=False)

########NEW FILE########
__FILENAME__ = settings
import os
import urlparse


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PACKAGE_ROOT = os.path.abspath(os.path.dirname(__file__))
DEBUG = bool(int(os.environ.get("DEBUG", 1)))
TEMPLATE_DEBUG = DEBUG
ADMINS = [
    ("Patrick Altman", "paltman@eldarion.com"),
]
MANAGERS = ADMINS

if "GONDOR_DATABASE_URL" in os.environ:
    urlparse.uses_netloc.append("postgres")
    url = urlparse.urlparse(os.environ["GONDOR_DATABASE_URL"])
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
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "demo",
            "HOST": "127.0.0.1",
        }
    }

TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
SITE_ID = os.environ.get("SITE_ID", 1)
USE_I18N = False
USE_L10N = False
USE_TZ = True
MEDIA_ROOT = os.path.join(
    os.environ.get("GONDOR_DATA_DIR", PACKAGE_ROOT),
    "site_media",
    "media"
)
STATIC_ROOT = os.path.join(
    os.environ.get("GONDOR_DATA_DIR", PACKAGE_ROOT),
    "site_media",
    "static"
)
MEDIA_URL = "/site_media/media/"
STATIC_URL = "/site_media/static/"
STATICFILES_DIRS = [
    os.path.join(PACKAGE_ROOT, "static"),
]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
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
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "pinax_theme_bootstrap.context_processors.theme",
    "account.context_processors.account",
]
MIDDLEWARE_CLASSES = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "demo.urls"
WSGI_APPLICATION = "demo.wsgi.application"
TEMPLATE_DIRS = [
    os.path.join(PACKAGE_ROOT, "templates"),
]
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # theme
    "pinax_theme_bootstrap",
    "django_forms_bootstrap",
    
    # external
    "account",
    "metron",
    
    # project
    "demo"
]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse"
        }
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler"
        }
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
    }
}
FIXTURE_DIRS = [
    os.path.join(PROJECT_ROOT, "fixtures"),
]
METRON_SETTINGS = {
    "google": {
        "2": os.environ.get("GOOGLE_ANALYTICS_ID", ""),
    }
}
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.sendgrid.net")
EMAIL_PORT = os.environ.get("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
ACCOUNT_OPEN_SIGNUP = False
ACCOUNT_USE_OPENID = False
ACCOUNT_REQUIRED_EMAIL = False
ACCOUNT_EMAIL_VERIFICATION = False
ACCOUNT_EMAIL_AUTHENTICATION = False
ACCOUNT_LOGIN_REDIRECT_URL = "home"
ACCOUNT_LOGOUT_REDIRECT_URL = "home"
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 2

ALLOWED_HOSTS = [
    "uk013.gondor.co",
]

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns(
    "",
    url(r"^$", "demo.views.home", name="home"),
    url(r"^tasks/(?P<pk>\d+)/done/$", "demo.views.mark_done", name="task_mark_done"),
    url(r"^tasks/(?P<pk>\d+)/undone/$", "demo.views.mark_undone", name="task_mark_undone"),
    url(r"^tasks/completed/$", "demo.views.complete_count_fragment", name="task_complete_count_fragment"),
    url(r"^tasks/add/$", "demo.views.add", name="task_add"),
    url(r"^tasks/(?P<pk>\d+)/delete/$", "demo.views.delete", name="task_delete"),
    url(r"^status/$", "demo.views.status", name="status"),
    url(r"^total-count/$", "demo.views.total_count", name="total_count"),
    url(r"^admin/", include(admin.site.urls)),
    url(r"^account/", include("account.urls")),
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = views
import json

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from django.contrib.sessions.models import Session

from demo.models import Task


def status(request):
    data = {
        "fragments": {
            ".alert": render_to_string(
                "_status.html",
                RequestContext(request, {
                    "count": Task.objects.filter(
                        session__session_key=request.session.session_key
                    ).count()
                })
            )
        }
    }
    return HttpResponse(json.dumps(data), content_type="application/json")


def total_count(request):
    return HttpResponse(json.dumps({
        "html": Task.objects.count()
    }), content_type="application/json")


def home(request):
    if not request.session.exists(request.session.session_key):
        request.session.create()
    
    return render(request, "homepage.html", {
        "tasks": Task.objects.filter(
            session__session_key=request.session.session_key
        ),
        "total_count": Task.objects.count(),
        "done_count": Task.objects.filter(
            session__session_key=request.session.session_key,
            done=True
        ).count()
    })


def complete_count_fragment(request):
    data = {
        "html": render_to_string(
            "_complete_count.html",
            RequestContext(request, {
                "done_count": Task.objects.filter(
                    done=True,
                    session__session_key=request.session.session_key
                ).count()
            })
        )
    }
    return HttpResponse(json.dumps(data), content_type="application/json")


def _task_data(request, task):
    data = {
        "html": render_to_string(
            "_task.html",
            RequestContext(request, {
                "task": task
            })
        )
    }
    return data


@require_POST
def mark_done(request, pk):
    task = get_object_or_404(
        Task,
        session__session_key=request.session.session_key,
        pk=pk
    )
    task.done = True
    task.save()
    data = _task_data(request, task)
    return HttpResponse(json.dumps(data), content_type="application/json")


@require_POST
def mark_undone(request, pk):
    task = get_object_or_404(
        Task,
        session__session_key=request.session.session_key,
        pk=pk
    )
    task.done = False
    task.save()
    data = _task_data(request, task)
    return HttpResponse(json.dumps(data), content_type="application/json")


@require_POST
def add(request):
    session = Session.objects.get(session_key=request.session.session_key)
    task = Task.objects.create(
        session=session,
        label=request.POST.get("label")
    )
    data = _task_data(request, task)
    return HttpResponse(json.dumps(data), content_type="application/json")


@require_POST
def delete(request, pk):
    task = get_object_or_404(
        Task,
        session__session_key=request.session.session_key,
        pk=pk
    )
    task.delete()
    data = {
        "html": "<div class=\"alert alert-info\">Task #{} deleted!</div>".format(pk)
    }
    return HttpResponse(json.dumps(data), content_type="application/json")

########NEW FILE########
__FILENAME__ = wsgi
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

########NEW FILE########
