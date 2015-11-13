__FILENAME__ = conf
import sys, os

extensions = []
templates_path = []
source_suffix = '.rst'
master_doc = 'index'
project = u'eventlog'
copyright_holder = 'Eldarion'
copyright = u'2014, %s' % copyright_holder
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
htmlhelp_basename = '%sdoc' % project
latex_documents = [
  ('index', '%s.tex' % project, u'%s Documentation' % project,
   copyright_holder, 'manual'),
]
man_pages = [
    ('index', project, u'%s Documentation' % project,
     [copyright_holder], 1)
]

sys.path.insert(0, os.pardir)
m = __import__(project)

version = m.__version__
release = version

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from eventlog.models import Log


class LogAdmin(admin.ModelAdmin):

    raw_id_fields = ["user"]
    list_filter = ["action", "timestamp"]
    list_display = ["timestamp", "user", "action", "extra"]
    search_fields = ["user__username", "user__email", "extra"]


admin.site.register(Log, LogAdmin)

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

import jsonfield

from .signals import event_logged


class Log(models.Model):

    user = models.ForeignKey(
        getattr(settings, "AUTH_USER_MODEL", "auth.User"),
        null=True,
        on_delete=models.SET_NULL
    )
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    action = models.CharField(max_length=50, db_index=True)
    extra = jsonfield.JSONField()

    class Meta:
        ordering = ["-timestamp"]


def log(user, action, extra=None):
    if (user is not None and not user.is_authenticated()):
        user = None
    if extra is None:
        extra = {}
    event = Log.objects.create(user=user, action=action, extra=extra)
    event_logged.send(sender=Log, event=event)
    return event

########NEW FILE########
__FILENAME__ = signals
import django.dispatch


event_logged = django.dispatch.Signal(providing_args=["event"])

########NEW FILE########
__FILENAME__ = stats
from datetime import datetime, timedelta

from django.contrib.auth.models import User


def used_active(days):
    used = User.objects.filter(
        log__timestamp__gt=datetime.now() - timedelta(days=days)
    ).distinct().count()

    active = User.objects.filter(
        log__timestamp__gt=datetime.now() - timedelta(days=days)
    ).exclude(
        date_joined__gt=datetime.now() - timedelta(days=days)
    ).distinct().count()

    return used, active


def stats():
    used_seven, active_seven = used_active(7)
    used_thirty, active_thirty = used_active(30)

    return {
        "used_seven": used_seven,
        "used_thirty": used_thirty,
        "active_seven": active_seven,
        "active_thirty": active_thirty
    }

########NEW FILE########
