__FILENAME__ = api_urls
from django.conf.urls import patterns, include, url

from tastypie.api import Api

from packages.api import PackageResource, ReleaseResource

v1_api = Api(api_name="v1")

v1_api.register(PackageResource())
v1_api.register(ReleaseResource())


urlpatterns = patterns("",
    url("", include(include(v1_api.urls))),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template


urlpatterns = patterns("",
    url(r"^$", direct_to_template, {"template": "about/about.html"}, name="about"),
    url(r"^terms/$", direct_to_template, {"template": "about/terms.html"}, name="terms"),
    url(r"^privacy/$", direct_to_template, {"template": "about/privacy.html"}, name="privacy"),
    url(r"^dmca/$", direct_to_template, {"template": "about/dmca.html"}, name="dmca"),
)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from aws_stats.models import Log


class LogAdmin(admin.ModelAdmin):
    list_display = ["when", "method", "status", "host", "uri_stem", "uri_query", "ip", "edge_location"]
    list_filter = ["when", "method", "status", "edge_location"]
    search_fields = ["host", "uri_stem", "uri_query", "ip", "referer", "user_agent"]


admin.site.register(Log, LogAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Log'
        db.create_table('aws_stats_log', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('when', self.gf('django.db.models.fields.DateTimeField')()),
            ('edge_location', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('method', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('bytes', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('host', self.gf('django.db.models.fields.TextField')()),
            ('uri_stem', self.gf('django.db.models.fields.TextField')()),
            ('uri_query', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('ip', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39)),
            ('referer', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('user_agent', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('aws_stats', ['Log'])

    def backwards(self, orm):
        # Deleting model 'Log'
        db.delete_table('aws_stats_log')

    models = {
        'aws_stats.log': {
            'Meta': {'object_name': 'Log'},
            'bytes': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'edge_location': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'host': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'referer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'uri_query': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'uri_stem': ('django.db.models.fields.TextField', [], {}),
            'user_agent': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'when': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['aws_stats']
########NEW FILE########
__FILENAME__ = 0002_auto__add_logprocessed
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LogProcessed'
        db.create_table('aws_stats_logprocessed', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')(unique=True)),
        ))
        db.send_create_signal('aws_stats', ['LogProcessed'])

    def backwards(self, orm):
        # Deleting model 'LogProcessed'
        db.delete_table('aws_stats_logprocessed')

    models = {
        'aws_stats.log': {
            'Meta': {'object_name': 'Log'},
            'bytes': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'edge_location': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'host': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'referer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'uri_query': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'uri_stem': ('django.db.models.fields.TextField', [], {}),
            'user_agent': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'when': ('django.db.models.fields.DateTimeField', [], {})
        },
        'aws_stats.logprocessed': {
            'Meta': {'object_name': 'LogProcessed'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['aws_stats']
########NEW FILE########
__FILENAME__ = models
from django.db import models


class Log(models.Model):

    when = models.DateTimeField()
    edge_location = models.CharField(max_length=25)

    method = models.CharField(max_length=25)
    status = models.CharField(max_length=3)
    bytes = models.PositiveIntegerField()

    host = models.TextField()
    uri_stem = models.TextField()
    uri_query = models.TextField(blank=True)

    ip = models.GenericIPAddressField(unpack_ipv4=True)
    referer = models.TextField(blank=True)
    user_agent = models.TextField(blank=True)

    def __unicode__(self):
        return "%(method)s %(uri_stem)s" % self.__dict__


class LogProcessed(models.Model):

    name = models.TextField(unique=True)

########NEW FILE########
__FILENAME__ = tasks
import datetime
import gzip
import itertools
import logging
import re
import StringIO
import urllib

from django.conf import settings
from django.db import transaction

from boto.s3.connection import S3Connection
from celery.task import task
from pytz import utc

from aws_stats.models import Log, LogProcessed

logger = logging.getLogger(__name__)


_log_filename = re.compile(settings.AWS_STATS_LOG_REGEX)


@task
def process_aws_log(key):
    if LogProcessed.objects.filter(name=key).exists():
        return

    conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    bucket = conn.lookup(settings.AWS_STATS_BUCKET_NAME)

    k = bucket.get_key(key)

    logs = []

    with gzip.GzipFile(fileobj=StringIO.StringIO(k.get_contents_as_string())) as f:
        fields = None
        for line in f:
            if line.startswith("#"):
                directive, value = line[1:].split(":", 1)

                directive = directive.strip()
                value = value.strip()

                if directive == "Version":
                    assert value == "1.0"

                if directive == "Fields":
                    fields = value.split()
            else:
                assert fields is not None

                logs.append(dict(itertools.izip(fields, [urllib.unquote(x) if x is not "-" else "" for x in line.split()])))

    with transaction.commit_on_success():
        for l in logs:
            when = datetime.datetime.strptime("T".join([l["date"], l["time"]]), "%Y-%m-%dT%H:%M:%S")
            when = when.replace(tzinfo=utc)

            Log.objects.create(
                    when=when,
                    edge_location=l["x-edge-location"],
                    method=l["cs-method"],
                    status=l["sc-status"],
                    bytes=int(l["sc-bytes"]),
                    host=l["cs(Host)"],
                    uri_stem=l["cs-uri-stem"],
                    uri_query=l["cs-uri-query"],
                    ip=l["c-ip"],
                    referer=l["cs(Referer)"],
                    user_agent=l["cs(User-Agent)"]
                )

        LogProcessed.objects.get_or_create(name=key)

    k.delete()


@task
def process_aws_logs():
    conn = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    bucket = conn.lookup(settings.AWS_STATS_BUCKET_NAME)

    for k in bucket:
        if _log_filename.search(k.name) is not None:
            process_aws_log.delay(k.name)
        else:
            logger.warning("%s doesn't match the aws log regex" % k.name)

########NEW FILE########
__FILENAME__ = helpers
import os

from urllib import urlencode
from urlparse import urlparse, parse_qs, urlunparse

from django.conf import settings
from django.utils import formats

import jinja2

from jingo import register
from account.utils import user_display as pinax_user_display
from staticfiles.storage import staticfiles_storage


@register.function
def ifelse(first, test, nelse):
    return first if test else nelse


@register.function
def pagination_numbers(numbers, current, max_num=13):
    step = (max_num - 1) / 2
    start = numbers.index(current) - step

    if start < 0:
        end = numbers.index(current) + step + abs(start)
        start = 0
    else:
        end = numbers.index(current) + step
    return numbers[start:end + 1]


@register.filter
def reqarg(url, name, value=None):
    parsed = urlparse(url)
    data = parse_qs(parsed.query)
    if value is not None:
        data.update({
            name: [value],
        })
    else:
        if name in data:
            del data[name]

    _data = []
    for key, value in data.iteritems():
        for item in value:
            _data.append((key, item))

    return jinja2.Markup(urlunparse([parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(_data), parsed.fragment]))


@register.filter
def filename(name):
    return os.path.basename(name)


@register.function
def char_split(value, names=None, char="$"):
    value_list = value.split(char)

    if names is not None:
        return dict(zip(names, value_list))

    return value_list


@register.filter
def date(value, arg=None):
    """Formats a date according to the given format."""
    if not value:
        return u''
    if arg is None:
        arg = settings.DATE_FORMAT
    try:
        return formats.date_format(value, arg)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''


@register.function
def static(path):
    """
    A template tag that returns the URL to a file
    using staticfiles' storage backend
    """
    return staticfiles_storage.url(path)


@register.filter
def is_checkbox(field):
    return field.field.widget.__class__.__name__.lower() == "checkboxinput"


@register.filter
def css_class(field):
    return field.field.widget.__class__.__name__.lower()


@register.function
def user_display(user):
    return pinax_user_display(user)


@register.function
def null_get(d, key, fallback=None):
    if d is None:
        return fallback
    return d.get(key, fallback)

########NEW FILE########
__FILENAME__ = dummy_passwords
from django.conf import settings
from django.core.management.base import BaseCommand

from django.contrib.auth.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):
        if not settings.DEBUG:
            print "Dummy Passwords Only Available when DEBUG = True"
            return

        first_user = User.objects.all()[:1].get()
        first_user.set_password("letmein")
        first_user.save()

        User.objects.all().update(password=first_user.password)


########NEW FILE########
__FILENAME__ = migrate_django_openid_social_auth
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from django.contrib.auth.models import User

from account.models import EmailAddress
from social_auth.models import UserSocialAuth


class Command(BaseCommand):

    def handle(self, *args, **options):
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, openid FROM django_openid_useropenidassociation;")

        for openid in cursor.fetchall():
            user = User.objects.get(pk=openid[0])
            print user.username, openid[1]
            UserSocialAuth.objects.get_or_create(provider="openid", uid=openid[1], defaults={"user": user})

########NEW FILE########
__FILENAME__ = migrate_emails_pinax_dua
from django.conf import settings
from django.core.management.base import BaseCommand

from django.contrib.auth.models import User

from account.models import EmailAddress


class Command(BaseCommand):

    def handle(self, *args, **options):
        for u in User.objects.all():
            EmailAddress.objects.create(user=u, email=u.email, verified=True, primary=True)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = associate
from django.core.exceptions import MultipleObjectsReturned

from account.models import EmailAddress

from social_auth.utils import setting
from social_auth.backends.pipeline import warn_setting
from social_auth.backends.exceptions import AuthException


def associate_by_email(details, *args, **kwargs):
    """Return user entry with same email address as one returned on details."""
    email = details.get('email')

    warn_setting('SOCIAL_AUTH_ASSOCIATE_BY_MAIL', 'associate_by_email')

    if email and setting('SOCIAL_AUTH_ASSOCIATE_BY_MAIL', True):
        # try to associate accounts registered with the same email address,
        # only if it's a single object. AuthException is raised if multiple
        # objects are returned
        try:
            address = EmailAddress.objects.filter(email=email, verified=True).select_related("user").get()
            return {"user": address.user}
        except MultipleObjectsReturned:
            raise AuthException(kwargs['backend'], 'Not unique email address.')
        except EmailAddress.DoesNotExist:
            pass

########NEW FILE########
__FILENAME__ = user
from account.models import Account, EmailAddress

from social_auth.models import User
from social_auth.backends.pipeline import warn_setting
from social_auth.utils import setting
from social_auth.signals import socialauth_not_registered


def create_user(backend, details, response, uid, username, user=None, *args, **kwargs):
    """Create user. Depends on get_username pipeline."""
    if user:
        return {'user': user}
    if not username:
        return None

    warn_setting('SOCIAL_AUTH_CREATE_USERS', 'create_user')

    if not setting('SOCIAL_AUTH_CREATE_USERS', True):
        # Send signal for cases where tracking failed registering is useful.
        socialauth_not_registered.send(sender=backend.__class__, uid=uid, response=response, details=details)
        return None

    email = details.get('email')
    request = kwargs["request"]

    user = User.objects.create_user(username=username, email=email)

    Account.create(request=request, user=user)
    EmailAddress.objects.add_email(user, user.email, primary=True)

    return {
        'user': user,
        'is_new': True
    }

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from core.social_auth.views import SocialAuths

urlpatterns = patterns("",
    url(r"^social/$", SocialAuths.as_view(), name="social_auth_accounts"),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.views.generic.list import ListView
from django.utils.translation import ugettext as _

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required

from account.mixins import LoginRequiredMixin
from social_auth.decorators import dsa_view
from social_auth.models import UserSocialAuth
from social_auth.utils import backend_setting
from social_auth.views import DEFAULT_REDIRECT


class SocialAuths(LoginRequiredMixin, ListView):

    model = UserSocialAuth

    def get_queryset(self):
        qs = super(SocialAuths, self).get_queryset()
        qs = qs.filter(user=self.request.user)
        return qs


@login_required
@dsa_view()
def disconnect(request, backend, association_id=None):
    associated = request.user.social_auth.count()
    url = request.REQUEST.get(REDIRECT_FIELD_NAME, '') or backend_setting(backend, 'SOCIAL_AUTH_DISCONNECT_REDIRECT_URL') or DEFAULT_REDIRECT

    if not request.user.has_usable_password() and associated <= 1:
        messages.error(request, _("Cannot remove the only Social Account without first setting a Password or adding another Social Account."))
        return HttpResponseRedirect(url)

    usa = request.user.social_auth.get(pk=association_id)

    backend.disconnect(request.user, association_id)
    messages.success(request, _("Removed the %(provider)s account '%(uid)s'.") % {
        "provider": usa.provider,
        "uid": usa.extra_data.get("display", usa.uid) if usa.extra_data is not None else usa.uid,
    })

    return HttpResponseRedirect(url)

########NEW FILE########
__FILENAME__ = index
from django.core.urlresolvers import reverse

from admin_tools.dashboard import modules, Dashboard
from admin_tools.utils import get_admin_site_name

from crate.dashboard.modules import StatusModule, RedisStatusModule


class CrateIndexDashboard(Dashboard):

    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        # append a link list module for "quick links"
        self.children.append(modules.LinkList(
            "Quick links",
            layout="inline",
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                ["Return to site", "/"],
                ["Change password",
                 reverse("%s:password_change" % site_name)],
                ["Log out", reverse("%s:logout" % site_name)],
            ]
        ))

        # append an app list module for "Administration"
        self.children.append(modules.AppList(
            "Administration",
            models=('django.contrib.*',),
        ))

        # append an app list module for "Applications"
        self.children.append(modules.AppList(
            "Applications",
            exclude=[
                "django.contrib.*",
                "pinax.apps.*",
                "djcelery.*",
                "emailconfirmation.*",
                "profiles.*",
            ],
        ))

        self.children.append(StatusModule("Status"))

        self.children.append(RedisStatusModule(
            "Redis Status",

        ))

        # append a recent actions module
        self.children.append(modules.RecentActions("Recent Actions", 5))

########NEW FILE########
__FILENAME__ = modules
import collections
import datetime

import redis

from django.conf import settings
from django.utils.timezone import utc

from admin_tools.dashboard.modules import DashboardModule


class StatusModule(DashboardModule):

    title = "Status"
    template = "admin_tools/dashboard/modules/status.html"

    def init_with_context(self, context):
        if hasattr(settings, "PYPI_DATASTORE"):
            datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))

            if datastore.get("crate:pypi:since") is not None:
                self.last_sync = datetime.datetime.fromtimestamp(float(datastore.get("crate:pypi:since")))
                self.last_sync.replace(tzinfo=utc)
            else:
                self.last_sync = None

            self.celery_queue_length = datastore.llen("celery")

    def is_empty(self):
        return False


class RedisStatusModule(DashboardModule):

    title = "Redis Status"
    template = "admin_tools/dashboard/modules/redis.html"

    def init_with_context(self, context):
        if hasattr(settings, "PYPI_DATASTORE"):
            datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))
            self.redis_info = collections.OrderedDict(sorted([(k, v) for k, v in datastore.info().iteritems()], key=lambda x: x[0]))

    def is_empty(self):
        return False

########NEW FILE########
__FILENAME__ = json
from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import simplejson as json

from south.modelsinspector import add_introspection_rules


class JSONWidget(forms.Textarea):

    def render(self, name, value, attrs=None):
        if not isinstance(value, basestring):
            value = json.dumps(value, indent=4)
        return super(JSONWidget, self).render(name, value, attrs)


class JSONFormField(forms.CharField):

    def __init__(self, *args, **kwargs):
        kwargs["widget"] = JSONWidget
        super(JSONFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        if not value:
            return
        try:
            return json.loads(value)
        except ValueError, e:
            raise forms.ValidationError(u"JSON decode error: %s" % unicode(e))


class JSONField(models.TextField):

    __metaclass__ = models.SubfieldBase

    def _loads(self, value):
        return json.loads(value)

    def _dumps(self, value):
        return json.dumps(value, cls=DjangoJSONEncoder)

    def to_python(self, value):
        # if value is basestring this likely means this method is being called
        # while a QuerySet is being iterated or otherwise is coming in raw
        # and this is the only case when we should deserialize.
        if isinstance(value, basestring):
            return self._loads(value)

        return value

    def get_db_prep_save(self, value, **kwargs):
        return self._dumps(value)

    def formfield(self, **kwargs):
        return super(JSONField, self).formfield(form_class=JSONFormField, **kwargs)


add_introspection_rules([], ["^crate\.fields\.json\.JSONField"])

########NEW FILE########
__FILENAME__ = celery_status
import redis

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        r = redis.StrictRedis(
            host=settings.REDIS['default']['HOST'],
            port=settings.REDIS['default']['PORT'],
            password=settings.REDIS['default']['PASSWORD'])
        print "There are", r.llen("celery"), "items in the celery queue."

########NEW FILE########
__FILENAME__ = clear_celery
import redis

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        r = redis.StrictRedis(
            host=settings.REDIS['default']['HOST'],
            port=settings.REDIS['default']['PORT'],
            password=settings.REDIS['default']['PASSWORD'])
        r.delete("celery")

########NEW FILE########
__FILENAME__ = clear_celery_meta
import redis

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        r = redis.StrictRedis(
            host=settings.REDIS['default']['HOST'],
            port=settings.REDIS['default']['PORT'],
            password=settings.REDIS['default']['PASSWORD'])
        i = 0
        for key in r.keys("celery-*"):
            r.delete(key)
            i += 1
        print "%d keys cleared" % i

########NEW FILE########
__FILENAME__ = fix_missing_files
from django.core.management.base import BaseCommand

from packages.models import ReleaseFile
from pypi.processor import PyPIPackage


class Command(BaseCommand):

    def handle(self, *args, **options):
        i = 0
        for rf in ReleaseFile.objects.filter(digest="").distinct("release")[:10]:
            print rf.release.package.name, rf.release.version
            p = PyPIPackage(rf.release.package.name, version=rf.release.version)
            p.process(skip_modified=False)
            i += 1
        print "Fixed %d releases" % i

########NEW FILE########
__FILENAME__ = force_key_rollover
from django.core.management.base import BaseCommand
from pypi.tasks import pypi_key_rollover


class Command(BaseCommand):

    def handle(self, *args, **options):
        pypi_key_rollover.delay()

########NEW FILE########
__FILENAME__ = get_last_sync
import redis

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        r = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))
        print r.get("crate:pypi:since")

########NEW FILE########
__FILENAME__ = get_pypi_serverkey
import redis

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        r = redis.StrictRedis(
            host=settings.REDIS['default']['HOST'],
            port=settings.REDIS['default']['PORT'],
            password=settings.REDIS['default']['PASSWORD'])
        print r.get("crate:pypi:serverkey")
        print r.hgetall("crate:pypi:serverkey:headers")

########NEW FILE########
__FILENAME__ = migrate_releases
from django.core.management.base import BaseCommand
from pypi.tasks import migrate_all_releases


class Command(BaseCommand):

    def handle(self, *args, **options):
        print "Migrating All Releases"
        migrate_all_releases.delay()

########NEW FILE########
__FILENAME__ = reset_hidden
from django.core.management.base import BaseCommand

from packages.models import Release, ReleaseFile


class Command(BaseCommand):

    def handle(self, *args, **options):
        Release.objects.filter(hidden=True).update(hidden=False)
        ReleaseFile.objects.filter(hidden=True).update(hidden=False)

########NEW FILE########
__FILENAME__ = set_last_sync
import redis

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        r = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))
        if args:
            r.set("crate:pypi:since", args[0])

########NEW FILE########
__FILENAME__ = sync_mirror
from optparse import make_option

from django.core.management.base import BaseCommand

from pypi.tasks import synchronize_mirror


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("--since",
            dest="since",
            default=-1),
        )

    def handle(self, *args, **options):
        if options.get("since", -1) == -1:
            since = None
        else:
            since = 0

        synchronize_mirror.delay(since=since)

        print "Done"

########NEW FILE########
__FILENAME__ = trigger_bulk_sync
from django.core.management.base import BaseCommand

from pypi.tasks import bulk_synchronize


class Command(BaseCommand):

    def handle(self, *args, **options):
        bulk_synchronize.delay()
        print "Bulk Synchronize Triggered"

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = template2
from django.conf import settings

from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader(settings.JINJA_TEMPLATE_DIRS), auto_reload=settings.DEBUG)

########NEW FILE########
__FILENAME__ = pagination_utils
from django import template

register = template.Library()


@register.filter
def paginate_numbers(numbers, current_page, max_num=13):
    step = (max_num - 1) / 2
    start = numbers.index(current_page) - step

    if start < 0:
        end = numbers.index(current_page) + step + abs(start)
        start = 0
    else:
        end = numbers.index(current_page) + step
    return numbers[start:end + 1]

########NEW FILE########
__FILENAME__ = datatools
#
# Taken from http://justcramer.com/2010/12/06/tracking-changes-to-fields-in-django/
#

from django.db.models.signals import post_init

def track_data(*fields):
    """
    Tracks property changes on a model instance.

    The changed list of properties is refreshed on model initialization
    and save.

    >>> @track_data('name')
    >>> class Post(models.Model):
    >>>     name = models.CharField(...)
    >>>
    >>>     @classmethod
    >>>     def post_save(cls, sender, instance, created, **kwargs):
    >>>         if instance.has_changed('name'):
    >>>             print "Hooray!"
    """

    UNSAVED = dict()

    def _store(self):
        "Updates a local copy of attributes values"
        if self.id:
            self.__data = dict((f, getattr(self, f)) for f in fields)
        else:
            self.__data = UNSAVED

    def inner(cls):
        # contains a local copy of the previous values of attributes
        cls.__data = {}

        def has_changed(self, field):
            "Returns ``True`` if ``field`` has changed since initialization."
            if self.__data is UNSAVED:
                return False
            return self.__data.get(field) != getattr(self, field)
        cls.has_changed = has_changed

        def old_value(self, field):
            "Returns the previous value of ``field``"
            return self.__data.get(field)
        cls.old_value = old_value

        def whats_changed(self):
            "Returns a list of changed attributes."
            changed = {}
            if self.__data is UNSAVED:
                return changed
            for k, v in self.__data.iteritems():
                if v != getattr(self, k):
                    changed[k] = v
            return changed
        cls.whats_changed = whats_changed

        # Ensure we are updating local attributes on model init
        def _post_init(sender, instance, **kwargs):
            _store(instance)
        post_init.connect(_post_init, sender=cls, weak=False)

        # Ensure we are updating local attributes on model save
        def save(self, *args, **kwargs):
            save._original(self, *args, **kwargs)
            _store(self)
        save._original = cls.save
        cls.save = save
        return cls
    return inner

########NEW FILE########
__FILENAME__ = lock
import time

import redis

from django.conf import settings


class LockTimeout(BaseException):
    pass


class Lock(object):
    def __init__(self, key, expires=60, timeout=10):
        """
        Distributed locking using Redis SETNX and GETSET.

        Usage::

            with Lock('my_lock'):
                print "Critical section"

        :param  expires     We consider any existing lock older than
                            ``expires`` seconds to be invalid in order to
                            detect crashed clients. This value must be higher
                            than it takes the critical section to execute.
        :param  timeout     If another client has already obtained the lock,
                            sleep for a maximum of ``timeout`` seconds before
                            giving up. A value of 0 means we never wait.
        """

        self.key = "%s-lock" % key
        self.timeout = timeout
        self.expires = expires

        self.datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.LOCK_DATASTORE].items()]))

    def __enter__(self):
        timeout = self.timeout
        while timeout >= 0:
            expires = time.time() + self.expires + 1

            if self.datastore.setnx(self.key, expires):
                # We gained the lock; enter critical section
                return

            current_value = self.datastore.get(self.key)

            # We found an expired lock and nobody raced us to replacing it
            if current_value and float(current_value) < time.time() and \
                self.datastore.getset(self.key, expires) == current_value:
                    return

            timeout -= 1
            time.sleep(1)

        raise LockTimeout("Timeout whilst waiting for lock")

    def __exit__(self, exc_type, exc_value, traceback):
        self.datastore.delete(self.key)

########NEW FILE########
__FILENAME__ = views
from urlparse import urljoin

from django.conf import settings
from django.http import HttpResponseRedirect


def simple_redirect(request, path=None):
    host = settings.SIMPLE_API_URL

    if path is not None:
        if not path.startswith("/"):
            path = "/" + path

        redirect_to = urljoin(host, path)
    else:
        redirect_to = host
    return HttpResponseRedirect(redirect_to)

########NEW FILE########
__FILENAME__ = evaluators


class EvaluationSuite(object):

    def __init__(self):
        self.evaluators = []

    def register(self, cls):
        self.evaluators.append(cls)

    def unregister(self, cls):
        try:
            self.evaluators.remove(cls)
        except ValueError:
            pass

    def evaluate(self, obj):
        for test in self.evaluators:
            evaluator = test()
            result = evaluator.evaluate(obj)
            result.update({"evaluator": evaluator})
            yield result


suite = EvaluationSuite()

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = evaluators
from django import template

from evaluator import suite

register = template.Library()


@register.inclusion_tag("evaluator/report.html")
def evaluate(obj):
    return {"results": [result for result in suite.evaluate(obj)]}

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Favorite'
        db.create_table('favorites_favorite', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 2, 22, 13, 44, 28, 422790))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 2, 22, 13, 44, 28, 422903))),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('target_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('favorites', ['Favorite'])

    def backwards(self, orm):
        # Deleting model 'Favorite'
        db.delete_table('favorites_favorite')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 22, 13, 44, 28, 429039)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 22, 13, 44, 28, 428940)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'favorites.favorite': {
            'Meta': {'object_name': 'Favorite'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 22, 13, 44, 28, 427664)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 22, 13, 44, 28, 427759)'}),
            'target_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['favorites']
########NEW FILE########
__FILENAME__ = 0002_auto__del_field_favorite_target_id__del_field_favorite_content_type__a
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Favorite.target_id'
        db.delete_column('favorites_favorite', 'target_id')

        # Deleting field 'Favorite.content_type'
        db.delete_column('favorites_favorite', 'content_type_id')

        # Adding field 'Favorite.package'
        db.add_column('favorites_favorite', 'package',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Package'], null=True),
                      keep_default=False)

        # Adding unique constraint on 'Favorite', fields ['user', 'package']
        db.create_unique('favorites_favorite', ['user_id', 'package_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'Favorite', fields ['user', 'package']
        db.delete_unique('favorites_favorite', ['user_id', 'package_id'])


        # User chose to not deal with backwards NULL issues for 'Favorite.target_id'
        raise RuntimeError("Cannot reverse this migration. 'Favorite.target_id' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Favorite.content_type'
        raise RuntimeError("Cannot reverse this migration. 'Favorite.content_type' and its values cannot be restored.")
        # Deleting field 'Favorite.package'
        db.delete_column('favorites_favorite', 'package_id')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 20, 353210)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 20, 353119)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'favorites.favorite': {
            'Meta': {'unique_together': "(('user', 'package'),)", 'object_name': 'Favorite'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 20, 353609)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 20, 353704)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']", 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 20, 351398)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 20, 351741)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 20, 351514)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['favorites']
########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_favorite_package
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Favorite.package'
        db.alter_column('favorites_favorite', 'package_id', self.gf('django.db.models.fields.related.ForeignKey')(default=-1, to=orm['packages.Package']))
    def backwards(self, orm):

        # Changing field 'Favorite.package'
        db.alter_column('favorites_favorite', 'package_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Package'], null=True))
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 43, 872644)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 43, 872552)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'favorites.favorite': {
            'Meta': {'unique_together': "(('user', 'package'),)", 'object_name': 'Favorite'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 43, 873076)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 43, 873174)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 43, 871428)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 43, 871800)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 22, 14, 44, 43, 871542)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['favorites']
########NEW FILE########
__FILENAME__ = 0004_move_to_lists
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    depends_on = (
        ("lists", "0001_initial"),
    )

    def forwards(self, orm):
        favorite_lists = {}

        # Create a List for Everyone who has Favorited a Package
        for user in orm["favorites.Favorite"].objects.distinct("user").values_list("user", flat=True):
            u = orm["auth.User"].objects.get(pk=user)
            favorite_lists[user] = orm["lists.List"].objects.create(user=u, name="Favorites", private=True)

        for fav in orm["favorites.Favorite"].objects.all():
            favorite_lists[fav.user.pk].packages.add(fav.package)

    def backwards(self, orm):
        raise Exception("Cannot Go Backwards")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'favorites.favorite': {
            'Meta': {'unique_together': "(('user', 'package'),)", 'object_name': 'Favorite'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'lists.list': {
            'Meta': {'unique_together': "(('user', 'name'),)", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists', 'favorites']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0005_auto__del_favorite__del_unique_favorite_user_package
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Favorite', fields ['user', 'package']
        db.delete_unique('favorites_favorite', ['user_id', 'package_id'])

        # Deleting model 'Favorite'
        db.delete_table('favorites_favorite')

    def backwards(self, orm):
        # Adding model 'Favorite'
        db.create_table('favorites_favorite', (
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Package'])),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('favorites', ['Favorite'])

        # Adding unique constraint on 'Favorite', fields ['user', 'package']
        db.create_unique('favorites_favorite', ['user_id', 'package_id'])

    models = {
        
    }

    complete_apps = ['favorites']
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from favorites.views import ToggleFavorite, UserFavorites

urlpatterns = patterns("",
    url(r"^$", UserFavorites.as_view(), name="user_favorites"),
    url(r"^(?P<package>[^/]+)/$", ToggleFavorite.as_view(), name="toggle_favorite"),
)

########NEW FILE########
__FILENAME__ = views
import json

from django.core.cache import cache
from django.http import HttpResponse
from django.views.generic.base import View
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator

from django.contrib.auth.decorators import login_required

from favorites.models import Favorite
from packages.models import Package

FAVORITES_QUERYSET_KEY = "crate:favorites:user(%s):queryset"
FAVORITES_CACHE_VERSION = 2


class ToggleFavorite(View):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ToggleFavorite, self).dispatch(*args, **kwargs)

    def render_json(self, **data):
        return HttpResponse(json.dumps(data), mimetype="application/json")

    def post(self, request, *args, **kwargs):
        try:
            package = Package.objects.get(name=kwargs.get("package"))
        except Package.DoesNotExist:
            return self.render_json(package=kwargs.get("package"), success=False, message="Package does not exist")

        fav = Favorite.objects.filter(package=package, user=request.user)

        cache.delete(FAVORITES_QUERYSET_KEY % self.request.user.pk, version=FAVORITES_CACHE_VERSION)

        if fav:
            fav.delete()
            return self.render_json(package=package.name, success=True, action="unfavorite")
        else:
            Favorite.objects.create(package=package, user=request.user)
            return self.render_json(package=package.name, success=True, action="favorite")


class UserFavorites(ListView):

    queryset = Favorite.objects.all().select_related("package")
    template_name = "favorites/favorite_list.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(UserFavorites, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        cached = cache.get(FAVORITES_QUERYSET_KEY % self.request.user.pk, version=FAVORITES_CACHE_VERSION)

        if cached:
            return cached

        qs = super(UserFavorites, self).get_queryset()
        qs = qs.filter(user=self.request.user)

        qs = sorted(qs, key=lambda x: x.package.latest.created, reverse=True)

        cache.set(FAVORITES_QUERYSET_KEY % self.request.user.pk, qs, 60 * 60, version=FAVORITES_CACHE_VERSION)

        return qs

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url
from django.views.generic.simple import direct_to_template


urlpatterns = patterns("",
    url(r"^setting-up-pip/$", direct_to_template, {"template": "helpdocs/setting-up-pip.html"}, name="helpdocs_pip"),
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from history.models import Event


class EventAdmin(admin.ModelAdmin):
    list_display = ["package", "version", "action", "data", "created"]
    list_filter = ["action", "created"]
    search_fields = ["package", "version"]


admin.site.register(Event, EventAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Event'
        db.create_table('history_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('package', self.gf('django.db.models.fields.SlugField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('action', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('data', self.gf('jsonfield.fields.JSONField')()),
        ))
        db.send_create_signal('history', ['Event'])

    def backwards(self, orm):
        # Deleting model 'Event'
        db.delete_table('history_event')

    models = {
        'history.event': {
            'Meta': {'object_name': 'Event'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.SlugField', [], {'max_length': '150'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        }
    }

    complete_apps = ['history']
########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_event_data
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Event.data'
        db.alter_column('history_event', 'data', self.gf('jsonfield.fields.JSONField')(null=True))
    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Event.data'
        raise RuntimeError("Cannot reverse this migration. 'Event.data' and its values cannot be restored.")
    models = {
        'history.event': {
            'Meta': {'object_name': 'Event'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.SlugField', [], {'max_length': '150'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'})
        }
    }

    complete_apps = ['history']
########NEW FILE########
__FILENAME__ = 0003_convert_changelog_to_history
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    depends_on = (
        ("packages", "0019_auto__add_field_releasefile_hidden"),
    )

    def forwards(self, orm):
        for cl in orm["packages.ChangeLog"].objects.all().select_related("package", "version"):
            e = orm["history.Event"](created=cl.created, package=cl.package.name)

            if cl.type == "new":
                e.action = "package_create"
            else:
                e.action = "release_create"
                e.version = cl.release.version

            e.save()

    def backwards(self, orm):
        raise Exception("Cannot Go Backwards")

    models = {
        'history.event': {
            'Meta': {'object_name': 'Event'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.SlugField', [], {'max_length': '150'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'})
        },
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages', 'history']
    symmetrical = True

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from jsonfield import JSONField
from model_utils import Choices
from model_utils.models import TimeStampedModel

from packages.models import Package, Release, ReleaseFile


class Event(TimeStampedModel):

    ACTIONS = Choices(
            ("package_create", _("Package Created")),
            ("package_delete", _("Package Deleted")),
            ("release_create", _("Release Created")),
            ("release_delete", _("Release Deleted")),
            ("file_add", _("File Added")),
            ("file_remove", _("File Removed")),
        )

    package = models.SlugField(max_length=150)
    version = models.CharField(max_length=512, blank=True)

    action = models.CharField(max_length=25, choices=ACTIONS)

    data = JSONField(null=True, blank=True)


@receiver(post_save, sender=Package)
def history_package_create(instance, created, **kwargs):
    if created:
        Event.objects.create(
            package=instance.name,
            action=Event.ACTIONS.package_create
        )


@receiver(post_delete, sender=Package)
def history_package_delete(instance, **kwargs):
    Event.objects.create(
        package=instance.name,
        action=Event.ACTIONS.package_delete
    )


@receiver(post_save, sender=Release)
def history_release_update(instance, created, **kwargs):
    if created:
        Event.objects.create(
            package=instance.package.name,
            version=instance.version,
            action=Event.ACTIONS.release_create
        )

    if instance.has_changed("hidden"):
        if instance.hidden:
            Event.objects.create(
                package=instance.package.name,
                version=instance.version,
                action=Event.ACTIONS.release_delete
            )
        else:
            Event.objects.create(
                package=instance.package.name,
                version=instance.version,
                action=Event.ACTIONS.release_create
            )


@receiver(post_save, sender=ReleaseFile)
def history_releasefile_update(instance, created, **kwargs):
    e = None

    if instance.has_changed("hidden"):
        if instance.hidden:
            e = Event.objects.create(
                package=instance.release.package.name,
                version=instance.release.version,
                action=Event.ACTIONS.file_remove
            )

    if e is not None:
        e.data = {
            "filename": instance.filename,
            "digest": instance.digest,
            "uri": instance.get_absolute_url(),
        }
        e.save()

########NEW FILE########
__FILENAME__ = helpers
import re

from django.conf import settings
from django.utils.encoding import force_unicode
from django.utils.formats import number_format

import jinja2

from jingo import register


@register.filter
def intcomma(value, use_l10n=True):
    """
    Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    if settings.USE_L10N and use_l10n:
        try:
            if not isinstance(value, float):
                value = int(value)
        except (TypeError, ValueError):
            return intcomma(value, False)
        else:
            return jinja2.Markup(number_format(value, force_grouping=True))
    orig = force_unicode(value)
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    if orig == new:
        return jinja2.Markup(new)
    else:
        return intcomma(new, use_l10n)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = translate
from django.utils.translation import ugettext, ungettext
import jingo


class JinjaTranslations:
    def gettext(self, message):
        return ugettext(message)

    def ngettext(self, singular, plural, number):
        return ungettext(singular, plural, number)

def patch():
    jingo.env.install_gettext_translations(JinjaTranslations(), newstyle=True)

########NEW FILE########
__FILENAME__ = helpers
import time

from django.conf import settings
from django.utils import simplejson
from django.utils.hashcompat import sha_constructor

from jingo import register


@register.function
def intercom_data(user):
    if hasattr(settings, "INTERCOM_APP_ID") and user.is_authenticated():
        if hasattr(settings, "INTERCOM_USER_HASH_KEY"):
            user_hash = sha_constructor(settings.INTERCOM_USER_HASH_KEY + user.email).hexdigest()
        else:
            user_hash = None

        custom_data = {}
        for app in getattr(settings, "INTERCOM_APPS", []):
            m = __import__(app + ".intercom", globals(), locals(), ["intercom"])
            custom_data.update(m.custom_data(user))

        return {
            "app_id": settings.INTERCOM_APP_ID,
            "email": user.email,
            "user_hash": user_hash,
            "created_at": int(time.mktime(user.date_joined.timetuple())),
            "custom_data": simplejson.dumps(custom_data, ensure_ascii=False)
        }
    else:
        return {}

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = helpers
from django.conf import settings

from jingo import register


@register.function
def analytics():
    analytic_codes = {}

    for kind, codes in getattr(settings, "METRON_SETTINGS", {}).items():
        code = codes.get(settings.SITE_ID)
        if code is not None:
            analytic_codes[kind] = code

    return analytic_codes

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from lists.models import List


class PackageInline(admin.TabularInline):
    model = List.packages.through
    raw_id_fields = ["package"]
    extra = 0


class ListAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["name", "user__username", "packages__name"]
    raw_id_fields = ["user"]
    exclude = ["packages"]

    inlines = [
        PackageInline,
    ]

admin.site.register(List, ListAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms

from lists.models import List


class CreateListForm(forms.ModelForm):

    class Meta:
        model = List
        fields = ["name", "description", "private"]

    def __init__(self, *args, **kwargs):
        super(CreateListForm, self).__init__(*args, **kwargs)

        self.fields["description"].widget = forms.Textarea()

########NEW FILE########
__FILENAME__ = helpers
from jingo import register

from lists.forms import CreateListForm
from lists.models import List


@register.function
def lists_for_user(user):
    if user.is_authenticated():
        return List.objects.filter(user=user).prefetch_related("packages")

    return []

@register.function
def new_list_with_package_form():
    return CreateListForm()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'List'
        db.create_table('lists_list', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
            ('private', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('lists', ['List'])

        # Adding unique constraint on 'List', fields ['user', 'name']
        db.create_unique('lists_list', ['user_id', 'name'])

        # Adding M2M table for field packages on 'List'
        db.create_table('lists_list_packages', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('list', models.ForeignKey(orm['lists.list'], null=False)),
            ('package', models.ForeignKey(orm['packages.package'], null=False))
        ))
        db.create_unique('lists_list_packages', ['list_id', 'package_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'List', fields ['user', 'name']
        db.delete_unique('lists_list', ['user_id', 'name'])

        # Deleting model 'List'
        db.delete_table('lists_list')

        # Removing M2M table for field packages on 'List'
        db.delete_table('lists_list_packages')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lists.list': {
            'Meta': {'unique_together': "(('user', 'name'),)", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_list_slug__add_unique_list_user_slug
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'List.slug'
        db.add_column('lists_list', 'slug',
                      self.gf('django.db.models.fields.SlugField')(max_length=50, null=True),
                      keep_default=False)

        # Adding unique constraint on 'List', fields ['user', 'slug']
        db.create_unique('lists_list', ['user_id', 'slug'])

    def backwards(self, orm):
        # Removing unique constraint on 'List', fields ['user', 'slug']
        db.delete_unique('lists_list', ['user_id', 'slug'])

        # Deleting field 'List.slug'
        db.delete_column('lists_list', 'slug')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lists.list': {
            'Meta': {'unique_together': "[('user', 'name'), ('user', 'slug')]", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']
########NEW FILE########
__FILENAME__ = 0003_migrate_name_to_slug
# -*- coding: utf-8 -*-
from django.db.models import Q
from django.template.defaultfilters import slugify

from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        used = set()
        for l in orm["lists.List"].objects.filter(Q(slug=None) | Q(slug="")):
            slug = slugify(l.name)
            i = 1

            while (l.user, slug) in used:
                slug = slugify(u"%s %s" % (self.name, i))
                i += 1

            used.add((l.user, slug))

            l.slug = slug
            l.save()

    def backwards(self, orm):
        pass

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lists.list': {
            'Meta': {'unique_together': "[('user', 'name'), ('user', 'slug')]", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_list_slug
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'List.slug'
        db.alter_column('lists_list', 'slug', self.gf('django.db.models.fields.SlugField')(default='', max_length=50))
    def backwards(self, orm):

        # Changing field 'List.slug'
        db.alter_column('lists_list', 'slug', self.gf('django.db.models.fields.SlugField')(max_length=50, null=True))
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lists.list': {
            'Meta': {'unique_together': "[('user', 'name'), ('user', 'slug')]", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_list_description
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'List.description'
        db.add_column('lists_list', 'description',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=250, blank=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'List.description'
        db.delete_column('lists_list', 'description')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'lists.list': {
            'Meta': {'unique_together': "[('user', 'name'), ('user', 'slug')]", 'object_name': 'List'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '250', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'packages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['packages.Package']", 'symmetrical': 'False'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        }
    }

    complete_apps = ['lists']
########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models, IntegrityError
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel


class List(TimeStampedModel):
    user = models.ForeignKey("auth.User")
    # Translators: This is used to allow naming a specific list of packages.
    name = models.CharField(_("Name"), max_length=50, db_index=True)
    slug = models.SlugField(max_length=50)

    description = models.CharField(max_length=250, blank=True)

    private = models.BooleanField(_("Private List"), default=False, help_text=_("Private lists are visible only to you."))

    packages = models.ManyToManyField("packages.Package", verbose_name=_("Packages"))

    class Meta:
        unique_together = [
            ("user", "name"),
            ("user", "slug"),
        ]

    def save(self, *args, **kwargs):
        if not self.name:
            raise  IntegrityError("Name cannot be empty")

        if not self.slug:
            slug = slugify(self.name)
            i = 1

            while List.objects.filter(user=self.user, slug=slug).exists():
                slug = slugify(u"%s %s" % (self.name, i))
                i += 1

            self.slug = slug

        return super(List, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"%(username)s / %(listname)s" % {"username": self.user.username, "listname": self.name}

    def get_absolute_url(self):
        return reverse("lists_detail", kwargs={"username": self.user.username, "slug": self.slug})

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from lists.views import AddToList, AddToNewList, RemoveFromList, ListsList, ListDetail

urlpatterns = patterns("",
    url(r"^(?P<username>[^/]+)/lists/$", ListsList.as_view(), name="lists_list"),
    url(r"^(?P<username>[^/]+)/lists/(?P<slug>[^/]+)/$", ListDetail.as_view(), name="lists_detail"),

    url(r"^(?P<list>[^/]+)/(?P<package>[^/]+)/add/$", AddToList.as_view(), name="add_package_to_list"),
    url(r"^_/(?P<package>[^/]+)/new/$", AddToNewList.as_view(), name="add_package_to_new_list"),
    url(r"^(?P<list>[^/]+)/(?P<package>[^/]+)/remove/$", RemoveFromList.as_view(), name="remove_package_from_list"),
)

########NEW FILE########
__FILENAME__ = views
import json

from django.db.models import Q
from django.http import HttpResponse
from django.views.generic.base import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from lists.models import List
from packages.models import Package


class AddToList(View):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(AddToList, self).dispatch(*args, **kwargs)

    def render_json(self, **data):
        return HttpResponse(json.dumps(data), mimetype="application/json")

    def get_package(self, package):
        return next(iter(Package.objects.filter(name=package)[:1]), None)

    def get_list(self, list, user):
        return next(iter(List.objects.filter(name=list, user=user)[:1]), None)

    def get_message(self):
        return _("Successfully added %(package)s to %(list)s.") % self.kwargs

    def post(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

        package = self.get_package(self.kwargs.get("package"))

        if package is None:
            return self.render_json(
                        package=self.kwargs.get("package"),
                        list=self.kwargs.get("list"),
                        success=False,
                        message=_("Package does not exist")
                    )

        user_list = self.get_list(self.kwargs.get("list", None), user=request.user)

        if user_list is None:
            return self.render_json(
                        package=self.kwargs.get("package"),
                        list=self.kwargs.get("list"),
                        success=False,
                        message=_("List does not exist")
                    )

        user_list.packages.add(package)

        messages.success(request, self.get_message())

        return self.render_json(
                    package=self.kwargs.get("package"),
                    list=self.kwargs.get("list"),
                    success=True,
                    message=self.get_message()
                )


class AddToNewList(AddToList):

    def get_message(self):
        kw = self.kwargs.copy()
        kw.update({
            "list": self.request.POST.get("name"),
            })
        return _("Successfully added %(package)s to %(list)s.") % kw

    def get_list(self, list, user):
        if list is None:
            list = self.request.POST.get("name")

        defaults = {
            "private": self.request.POST.get("private", False),
            "description": self.request.POST.get("description", ""),
        }
        user_list, c = List.objects.get_or_create(user=user, name=list, defaults=defaults)

        if not c and user_list.private != self.request.POST.get("private", False):
            user_list.private = self.request.POST.get("private", False)
            user_list.save()

        if not c and user_list.description != self.request.POST.get("description", ""):
            user_list.description = self.request.POST.get("description", "")
            user_list.save()

        return user_list


class RemoveFromList(View):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(RemoveFromList, self).dispatch(*args, **kwargs)

    def render_json(self, **data):
        return HttpResponse(json.dumps(data), mimetype="application/json")

    def get_message(self):
        return _("Successfully removed %(package)s from %(list)s.") % self.kwargs

    def post(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

        try:
            package = Package.objects.get(name=kwargs.get("package"))
            user_list = List.objects.get(name=kwargs.get("list"), user=request.user)
        except Package.DoesNotExist:
            return self.render_json(package=kwargs.get("package"), list=kwargs.get("list"), success=False, message=_("Package does not exist"))
        except List.DoesNotExist:
            return self.render_json(package=kwargs.get("package"), list=kwargs.get("list"), success=False, message=_("List does not exist"))

        user_list.packages.remove(package)

        messages.success(request, self.get_message())

        return self.render_json(package=kwargs.get("package"), list=kwargs.get("list"), success=True, message=self.get_message())


class ListsList(ListView):

    queryset = List.objects.all().order_by("name")

    def get_queryset(self):
        qs = super(ListsList, self).get_queryset()
        qs = qs.filter(user__username=self.kwargs.get("username"))

        if self.request.user.is_authenticated():
            qs = qs.filter(Q(private=False) | Q(private=True, user=self.request.user))
        else:
            qs = qs.filter(private=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super(ListsList, self).get_context_data(**kwargs)

        ctx.update({
            "username": self.kwargs.get("username"),
        })

        return ctx


class ListDetail(DetailView):

    queryset = List.objects.all().select_related("packages")

    def get_queryset(self):
        qs = super(ListDetail, self).get_queryset()
        qs = qs.filter(user__username=self.kwargs.get("username"))

        if self.request.user.is_authenticated():
            qs = qs.filter(Q(private=False) | Q(private=True, user=self.request.user))
        else:
            qs = qs.filter(private=False)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super(ListDetail, self).get_context_data(**kwargs)

        ctx.update({
            "packages": self.object.packages.all().extra(select={"lower_name": "lower(name)"}).order_by("lower_name"),
        })

        return ctx

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from packages.models import Package, Release, ReleaseFile, TroveClassifier, PackageURI
from packages.models import ReleaseRequire, ReleaseProvide, ReleaseObsolete, ReleaseURI, ChangeLog
from packages.models import DownloadDelta, ReadTheDocsPackageSlug


class PackageURIAdmin(admin.TabularInline):
    model = PackageURI
    extra = 0


class PackageAdmin(admin.ModelAdmin):
    inlines = [PackageURIAdmin]
    list_display = ["name", "created", "modified", "downloads_synced_on"]
    list_filter = ["created", "modified", "downloads_synced_on"]
    search_fields = ["name"]


class ReleaseRequireInline(admin.TabularInline):
    model = ReleaseRequire
    extra = 0


class ReleaseProvideInline(admin.TabularInline):
    model = ReleaseProvide
    extra = 0


class ReleaseObsoleteInline(admin.TabularInline):
    model = ReleaseObsolete
    extra = 0


class ReleaseFileInline(admin.TabularInline):
    model = ReleaseFile
    extra = 0


class ReleaseURIInline(admin.TabularInline):
    model = ReleaseURI
    extra = 0


class ReleaseAdmin(admin.ModelAdmin):
    inlines = [ReleaseURIInline, ReleaseFileInline, ReleaseRequireInline, ReleaseProvideInline, ReleaseObsoleteInline]
    list_display = ["__unicode__", "package", "version", "summary", "author", "author_email", "maintainer", "maintainer_email", "created", "modified"]
    list_filter = ["created", "modified", "hidden"]
    search_fields = ["package__name", "version", "summary", "author", "author_email", "maintainer", "maintainer_email"]
    raw_id_fields = ["package"]


class TroveClassifierAdmin(admin.ModelAdmin):
    list_display = ["trove"]
    search_fields = ["trove"]


class ReleaseFileAdmin(admin.ModelAdmin):
    list_display = ["release", "type", "python_version", "downloads", "comment", "created", "modified"]
    list_filter = ["type", "created", "modified"]
    search_fields = ["release__package__name", "filename", "digest"]
    raw_id_fields = ["release"]


class DownloadDeltaAdmin(admin.ModelAdmin):
    list_display = ["file", "date", "delta"]
    list_filter = ["date"]
    search_fields = ["file__release__package__name", "file__filename"]
    raw_id_fields = ["file"]


class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ["package", "release", "type", "created", "modified"]
    list_filter = ["type", "created", "modified"]
    search_fields = ["package__name"]
    raw_id_fields = ["package", "release"]


class ReadTheDocsPackageSlugAdmin(admin.ModelAdmin):
    list_display = ["package", "slug"]
    search_fields = ["package__name", "slug"]
    raw_id_fields = ["package"]


admin.site.register(Package, PackageAdmin)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(ReleaseFile, ReleaseFileAdmin)
admin.site.register(TroveClassifier, TroveClassifierAdmin)
admin.site.register(DownloadDelta, DownloadDeltaAdmin)
admin.site.register(ChangeLog, ChangeLogAdmin)
admin.site.register(ReadTheDocsPackageSlug, ReadTheDocsPackageSlugAdmin)

########NEW FILE########
__FILENAME__ = api
from django.conf.urls import url

from tastypie import fields
from tastypie.bundle import Bundle
from tastypie.cache import SimpleCache
from tastypie.constants import ALL
from tastypie.resources import ModelResource
from tastypie.utils import trailing_slash

from packages.models import Package, Release, ReleaseFile, ReleaseURI, TroveClassifier
from packages.models import ReleaseRequire, ReleaseProvide, ReleaseObsolete


class InlineTroveClassifierResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["trove"]
        filtering = {
            "trove": ALL,
        }
        include_resource_uri = False
        ordering = ["trove"]
        queryset = TroveClassifier.objects.all()
        resource_name = "classifier"


class PackageResource(ModelResource):
    releases = fields.ToManyField("packages.api.ReleaseResource", "releases")
    downloads = fields.IntegerField("downloads")
    latest = fields.ToOneField("packages.api.InlineReleaseResource", "latest", full=True)

    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["created", "downloads_synced_on", "downloads", "name"]
        filtering = {
            "name": ALL,
            "created": ALL,
            "downloads_synced_on": ALL,
        }
        include_absolute_url = True
        ordering = ["created", "downloads_synced_on"]
        queryset = Package.objects.all()
        resource_name = "package"

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<name>[^/]+)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view("dispatch_detail"), name="api_dispatch_detail"),
        ]

    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            "resource_name": self._meta.resource_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs["name"] = bundle_or_obj.obj.name
        else:
            kwargs["name"] = bundle_or_obj.name

        if self._meta.api_name is not None:
            kwargs["api_name"] = self._meta.api_name

        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)


class InlineReleaseResource(ModelResource):
    files = fields.ToManyField("packages.api.ReleaseFileResource", "files", full=True)
    uris = fields.ToManyField("packages.api.ReleaseURIResource", "uris", full=True)
    classifiers = fields.ListField()
    requires = fields.ToManyField("packages.api.ReleaseRequireResource", "requires", full=True)
    provides = fields.ToManyField("packages.api.ReleaseProvideResource", "provides", full=True)
    obsoletes = fields.ToManyField("packages.api.ReleaseObsoleteResource", "obsoletes", full=True)
    downloads = fields.IntegerField("downloads")

    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = [
                    "author", "author_email", "created", "description", "download_uri", "downloads",
                    "license", "maintainer", "maintainer_email", "package", "platform", "classifiers",
                    "requires_python", "summary", "version"
                ]
        include_absolute_url = True
        include_resource_uri = False
        queryset = Release.objects.all()


class ReleaseResource(ModelResource):
    package = fields.ForeignKey(PackageResource, "package")
    files = fields.ToManyField("packages.api.ReleaseFileResource", "files", full=True)
    uris = fields.ToManyField("packages.api.ReleaseURIResource", "uris", full=True)
    classifiers = fields.ListField()
    requires = fields.ToManyField("packages.api.ReleaseRequireResource", "requires", full=True)
    provides = fields.ToManyField("packages.api.ReleaseProvideResource", "provides", full=True)
    obsoletes = fields.ToManyField("packages.api.ReleaseObsoleteResource", "obsoletes", full=True)
    downloads = fields.IntegerField("downloads")

    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = [
                    "author", "author_email", "created", "description", "download_uri", "downloads",
                    "license", "maintainer", "maintainer_email", "package", "platform", "classifiers",
                    "requires_python", "summary", "version"
                ]
        filtering = {
            "author": ALL,
            "author_email": ALL,
            "maintainer": ALL,
            "maintainer_email": ALL,
            "created": ALL,
            "license": ALL,
            "version": ALL,
        }
        include_absolute_url = True
        ordering = ["created", "license", "package", "version"]
        queryset = Release.objects.all()
        resource_name = "release"

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<package__name>[^/]+)-(?P<version>[^/]+)%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view("dispatch_detail"), name="api_dispatch_detail"),
        ]

    def get_resource_uri(self, bundle_or_obj):
        kwargs = {
            "resource_name": self._meta.resource_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs["package__name"] = bundle_or_obj.obj.package.name
            kwargs["version"] = bundle_or_obj.obj.version
        else:
            kwargs["name"] = bundle_or_obj.package.name
            kwargs["version"] = bundle_or_obj.version

        if self._meta.api_name is not None:
            kwargs["api_name"] = self._meta.api_name

        return self._build_reverse_url("api_dispatch_detail", kwargs=kwargs)

    def dehydrate_classifiers(self, bundle):
        return [c.trove for c in bundle.obj.classifiers.all()]


class ReleaseFileResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["comment", "created", "digest", "downloads", "file", "filename", "python_version", "type"]
        include_resource_uri = False
        queryset = ReleaseFile.objects.all()
        resource_name = "files"


class ReleaseURIResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["label", "uri"]
        include_resource_uri = False
        queryset = ReleaseURI.objects.all()
        resource_name = "uris"


class ReleaseRequireResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["kind", "name", "version", "environment"]
        include_resource_uri = False
        queryset = ReleaseRequire.objects.all()
        resource_name = "requires"


class ReleaseProvideResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["kind", "name", "version", "environment"]
        include_resource_uri = False
        queryset = ReleaseProvide.objects.all()
        resource_name = "provides"


class ReleaseObsoleteResource(ModelResource):
    class Meta:
        allowed_methods = ["get"]
        cache = SimpleCache()
        fields = ["kind", "name", "version", "environment"]
        include_resource_uri = False
        queryset = ReleaseObsolete.objects.all()
        resource_name = "obsoletes"

########NEW FILE########
__FILENAME__ = evaluators
import slumber

import jinja2

from slumber import exceptions

from django.core.cache import cache
from django.utils.translation import ugettext as _

from packages.utils import verlib


class ReleaseEvaluator(object):
    def evaluate(self, types=None):
        if types is None:
            types = ["pep386", "hosting", "documentation"]

        return [getattr(self, "evaluate_%s" % t)() for t in types]

    def evaluate_pep386(self):
        if not hasattr(self, "_evaluate_pep386"):
            normalized = verlib.suggest_normalized_version(self.version)

            evaluator = {
                "title": _("PEP386 Compatibility"),
                "message": jinja2.Markup(_("PEP386 defines a specific allowed syntax for Python package versions."
                                           "<br /><br />"
                                           "Previously it was impossible to accurately determine across any Python package what "
                                           "order the versions should go in, but with PEP386 we can now intelligently sort by version..."
                                           "<br /><br />"
                                           "But only if the version numbers are compatible!"))
            }

            if self.version == normalized:
                self._evaluate_pep386 = {
                    "level": "success",
                    "message": jinja2.Markup(_('Compatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
            elif normalized is not None:
                self._evaluate_pep386 = {
                    "level": None,
                    "message": jinja2.Markup(_('Almost Compatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_pep386 = {
                    "level": "error",
                    "message": jinja2.Markup(_('Incompatible with <a href="http://www.python.org/dev/peps/pep-0386/">PEP386</a>.')),
                    "evaluator": evaluator,
                }
        return self._evaluate_pep386

    def evaluate_hosting(self):
        if not hasattr(self, "_evaluate_hosting"):
            evaluator = {
                "title": _("Package Hosting"),
                "message": jinja2.Markup(
                    _("Did you know that packages listed on PyPI aren't required to host there?"
                      "<br /><br />"
                      "When your package manager tries to install a package from PyPI it looks in number "
                      "of locations, one such location is an author specified url of where the package can "
                      "be downloaded from."
                      "<br /><br />"
                      "Packages hosted by the author means that installing this package depends on the "
                      "authors server staying up, adding another link in the chain that can cause your "
                      "installation to fail")
                ),
            }

            if self.files.all().exists():
                self._evaluate_hosting = {
                    "level": "success",
                    "message": _("Package is hosted on PyPI"),
                    "evaluator": evaluator,
                }
            elif self.download_uri:
                self._evaluate_hosting = {
                    "level": "error",
                    "message": _("Package isn't hosted on PyPI"),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_hosting = {
                    "level": "error",
                    "message": _("No Package Hosting"),
                    "evaluator": evaluator,
                }
        return self._evaluate_hosting

    def evaluate_documentation(self):
        if not hasattr(self, "_evaluate_documentation"):
            evaluator = {
                "title": _("Documentation hosted on Read The Docs"),
                "message": jinja2.Markup(
                    _("Documentation can be one of the most important parts of any library. "
                      "Even more important than just having documentation, is making sure that people are "
                      "able to find it easily."
                      "<br /><br />"
                      "Read The Docs is an open source platform for hosting documentation generated by Sphinx."
                      "<br /><br />"
                      "Hosting your documentation on Read The Docs is easy (even if it's just an additional copy), and "
                      "it allows people who want to use your package the ability to locate your documentation in "
                      "what is quickly becoming a one stop shop for online open source documentation."
                      "<br /><br />"
                      "<small>If this says you aren't hosted on Read The Docs and you are please contact "
                      "<a href='mailto:support@crate.io'>support@crate.io</a></small>")
                ),
            }

            from packages.models import ReadTheDocsPackageSlug

            qs = ReadTheDocsPackageSlug.objects.filter(package=self.package)
            slug = qs[0].slug if qs else self.package.name

            key = "evaluate:rtd:%s" % slug

            if cache.get(key, version=4) is not None:
                hosted_on_rtd, url = cache.get(key, version=4)
            else:
                try:
                    api = slumber.API(base_url="http://readthedocs.org/api/v1/")
                    results = api.project.get(slug__iexact=slug)
                except exceptions.SlumberHttpBaseException:
                    return {
                        "level": "unknown",
                        "message": jinja2.Markup(_('There was an error with the <a href="http://readthedocs.org/">Read The Docs</a> API.')),
                        "evaluator": evaluator,
                    }

                if results["objects"]:
                    hosted_on_rtd = True
                    url = results["objects"][0]["subdomain"]
                else:
                    hosted_on_rtd = False
                    url = None

                cache.set(key, (hosted_on_rtd, url), 60 * 30, version=4)  # Cache This for 30 Minutes

            if hosted_on_rtd:
                self._evaluate_documentation = {
                    "level": "success",
                    "message": jinja2.Markup(_('Available on <a href="%s">Read The Docs</a>') % url),
                    "evaluator": evaluator,
                }
            else:
                self._evaluate_documentation = {
                    "level": "unknown",
                    "message": jinja2.Markup(_('Unavailable on <a href="http://readthedocs.org/">Read The Docs</a>')),
                    "evaluator": evaluator,
                }
        return self._evaluate_documentation

########NEW FILE########
__FILENAME__ = helpers
from django.db.models import Sum

from jingo import register
from packages.models import Package, ReleaseFile

@register.function
def package_information():
    return {
        "downloads": ReleaseFile.objects.all().aggregate(total_downloads=Sum("downloads")).get("total_downloads", 0),
        "packages": Package.objects.all().count(),
    }

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TroveClassifier'
        db.create_table('packages_troveclassifier', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trove', self.gf('django.db.models.fields.CharField')(unique=True, max_length=350)),
        ))
        db.send_create_signal('packages', ['TroveClassifier'])

        # Adding model 'Package'
        db.create_table('packages_package', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 227535))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 227680))),
            ('name', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=150)),
        ))
        db.send_create_signal('packages', ['Package'])

        # Adding model 'PackageURI'
        db.create_table('packages_packageuri', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(related_name='package_links', to=orm['packages.Package'])),
            ('uri', self.gf('django.db.models.fields.URLField')(max_length=400)),
        ))
        db.send_create_signal('packages', ['PackageURI'])

        # Adding unique constraint on 'PackageURI', fields ['package', 'uri']
        db.create_unique('packages_packageuri', ['package_id', 'uri'])

        # Adding model 'Release'
        db.create_table('packages_release', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 229663), db_index=True)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 229762))),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(related_name='releases', to=orm['packages.Package'])),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('platform', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('summary', self.gf('django.db.models.fields.TextField')()),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('keywords', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('license', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('author', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('author_email', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('maintainer', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('maintainer_email', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('requires_python', self.gf('django.db.models.fields.CharField')(max_length=25, blank=True)),
            ('download_uri', self.gf('django.db.models.fields.URLField')(max_length=1024, blank=True)),
            ('raw_data', self.gf('crate.fields.json.JSONField')(null=True, blank=True)),
        ))
        db.send_create_signal('packages', ['Release'])

        # Adding unique constraint on 'Release', fields ['package', 'version']
        db.create_unique('packages_release', ['package_id', 'version'])

        # Adding M2M table for field classifiers on 'Release'
        db.create_table('packages_release_classifiers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('release', models.ForeignKey(orm['packages.release'], null=False)),
            ('troveclassifier', models.ForeignKey(orm['packages.troveclassifier'], null=False))
        ))
        db.create_unique('packages_release_classifiers', ['release_id', 'troveclassifier_id'])

        # Adding model 'ReleaseFile'
        db.create_table('packages_releasefile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 228759), db_index=True)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 28, 13, 38, 31, 228860))),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='files', to=orm['packages.Release'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=512)),
            ('filename', self.gf('django.db.models.fields.CharField')(default=None, max_length=200, null=True, blank=True)),
            ('digest', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('python_version', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('downloads', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('packages', ['ReleaseFile'])

        # Adding unique constraint on 'ReleaseFile', fields ['release', 'type', 'python_version', 'filename']
        db.create_unique('packages_releasefile', ['release_id', 'type', 'python_version', 'filename'])

        # Adding model 'ReleaseURI'
        db.create_table('packages_releaseuri', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='uris', to=orm['packages.Release'])),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('uri', self.gf('django.db.models.fields.URLField')(max_length=500)),
        ))
        db.send_create_signal('packages', ['ReleaseURI'])

        # Adding model 'ReleaseRequire'
        db.create_table('packages_releaserequire', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='requires', to=orm['packages.Release'])),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('environment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('packages', ['ReleaseRequire'])

        # Adding model 'ReleaseProvide'
        db.create_table('packages_releaseprovide', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='provides', to=orm['packages.Release'])),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('environment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('packages', ['ReleaseProvide'])

        # Adding model 'ReleaseObsolete'
        db.create_table('packages_releaseobsolete', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='obsoletes', to=orm['packages.Release'])),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('environment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('packages', ['ReleaseObsolete'])

    def backwards(self, orm):
        # Removing unique constraint on 'ReleaseFile', fields ['release', 'type', 'python_version', 'filename']
        db.delete_unique('packages_releasefile', ['release_id', 'type', 'python_version', 'filename'])

        # Removing unique constraint on 'Release', fields ['package', 'version']
        db.delete_unique('packages_release', ['package_id', 'version'])

        # Removing unique constraint on 'PackageURI', fields ['package', 'uri']
        db.delete_unique('packages_packageuri', ['package_id', 'uri'])

        # Deleting model 'TroveClassifier'
        db.delete_table('packages_troveclassifier')

        # Deleting model 'Package'
        db.delete_table('packages_package')

        # Deleting model 'PackageURI'
        db.delete_table('packages_packageuri')

        # Deleting model 'Release'
        db.delete_table('packages_release')

        # Removing M2M table for field classifiers on 'Release'
        db.delete_table('packages_release_classifiers')

        # Deleting model 'ReleaseFile'
        db.delete_table('packages_releasefile')

        # Deleting model 'ReleaseURI'
        db.delete_table('packages_releaseuri')

        # Deleting model 'ReleaseRequire'
        db.delete_table('packages_releaserequire')

        # Deleting model 'ReleaseProvide'
        db.delete_table('packages_releaseprovide')

        # Deleting model 'ReleaseObsolete'
        db.delete_table('packages_releaseobsolete')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 248043)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 248163)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 250204)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 250319)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 249244)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 13, 38, 31, 249368)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_release_frequency
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.frequency'
        db.add_column('packages_release', 'frequency',
                      self.gf('django.db.models.fields.CharField')(default='hourly', max_length=25),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Release.frequency'
        db.delete_column('packages_release', 'frequency')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 359519)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 359624)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 354846)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'default': "'hourly'", 'max_length': '25'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 354960)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 356827)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 28, 21, 37, 17, 356937)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0004_auto__add_changelog
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ChangeLog'
        db.create_table('packages_changelog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 29, 4, 41, 10, 288146))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 29, 4, 41, 10, 288291))),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Package'])),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Release'], null=True, blank=True)),
        ))
        db.send_create_signal('packages', ['ChangeLog'])

    def backwards(self, orm):
        # Deleting model 'ChangeLog'
        db.delete_table('packages_changelog')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 329284)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 329489)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 331011)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 331123)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 332207)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'default': "'hourly'", 'max_length': '25'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 332320)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 335184)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 4, 41, 10, 335321)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_package_featured
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.featured'
        db.add_column('packages_package', 'featured',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Package.featured'
        db.delete_column('packages_package', 'featured')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 90400)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 90509)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 94873)'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 94977)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 90976)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'default': "'hourly'", 'max_length': '25'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 91115)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 93155)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 9, 18, 51, 93261)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0006_auto__del_field_release_frequency__del_field_package_featured
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Release.frequency'
        db.delete_column('packages_release', 'frequency')

        # Deleting field 'Package.featured'
        db.delete_column('packages_package', 'featured')

    def backwards(self, orm):
        # Adding field 'Release.frequency'
        db.add_column('packages_release', 'frequency',
                      self.gf('django.db.models.fields.CharField')(default='hourly', max_length=25),
                      keep_default=False)

        # Adding field 'Package.featured'
        db.add_column('packages_package', 'featured',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 976428)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 976528)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 971537)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 971657)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 974345)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 974459)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 972741)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 34, 34, 972865)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0007_auto__add_field_package_downloads_synced_on
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.downloads_synced_on'
        db.add_column('packages_package', 'downloads_synced_on',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2012, 1, 30, 3, 47, 32, 799896)),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Package.downloads_synced_on'
        db.delete_column('packages_package', 'downloads_synced_on')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 843206)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 843306)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 842257)'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 842520)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 842360)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 839741)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 839867)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 844278)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 30, 3, 47, 32, 844378)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0008_auto__add_readthedocspackageslug
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ReadTheDocsPackageSlug'
        db.create_table('packages_readthedocspackageslug', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.OneToOneField')(related_name='readthedocs_slug', unique=True, to=orm['packages.Package'])),
            ('slug', self.gf('django.db.models.fields.CharField')(unique=True, max_length=150)),
        ))
        db.send_create_signal('packages', ['ReadTheDocsPackageSlug'])

    def backwards(self, orm):
        # Deleting model 'ReadTheDocsPackageSlug'
        db.delete_table('packages_readthedocspackageslug')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 479069)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 479188)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 483204)'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 483465)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 483306)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 481670)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 481776)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 480473)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 3, 7, 25, 21, 480579)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0009_auto__add_field_release_deleted__add_field_package_deleted
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.deleted'
        db.add_column('packages_release', 'deleted',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Package.deleted'
        db.add_column('packages_package', 'deleted',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Release.deleted'
        db.delete_column('packages_release', 'deleted')

        # Deleting field 'Package.deleted'
        db.delete_column('packages_package', 'deleted')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 495558)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 495654)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 496243)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 496558)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 496340)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 493089)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 493188)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 491745)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 6, 21, 23, 491859)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0010_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'ChangeLog', fields ['type']
        db.create_index('packages_changelog', ['type'])

    def backwards(self, orm):
        # Removing index on 'ChangeLog', fields ['type']
        db.delete_index('packages_changelog', ['type'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 723563)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 723670)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 722995)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 723333)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 723104)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 725821)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 725927)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 724937)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 38, 46, 725040)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0011_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'ChangeLog', fields ['created']
        db.create_index('packages_changelog', ['created'])

    def backwards(self, orm):
        # Removing index on 'ChangeLog', fields ['created']
        db.delete_index('packages_changelog', ['created'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 169328)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 169451)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 173859)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 174181)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 173957)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 171815)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 171918)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 170942)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 17, 41, 16, 171053)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0012_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Release', fields ['order']
        db.create_index('packages_release', ['order'])

    def backwards(self, orm):
        # Removing index on 'Release', fields ['order']
        db.delete_index('packages_release', ['order'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 312737)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 312858)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 317211)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 317519)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 317305)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 315183)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 315281)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 314335)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 18, 46, 52, 314433)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0013_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Release', fields ['deleted']
        db.create_index('packages_release', ['deleted'])

        # Adding index on 'Package', fields ['deleted']
        db.create_index('packages_package', ['deleted'])

    def backwards(self, orm):
        # Removing index on 'Package', fields ['deleted']
        db.delete_index('packages_package', ['deleted'])

        # Removing index on 'Release', fields ['deleted']
        db.delete_index('packages_release', ['deleted'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 533082)', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 533182)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 531604)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 531942)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 531719)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 534759)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 534861)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 536366)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 19, 2, 46, 536468)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0014_delete_deleted
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    depends_on = (
        ("pypi", "0009_auto__del_downloadchange"),
    )

    def forwards(self, orm):
        for package in orm["packages.Package"].objects.filter(deleted=True):
            package.delete()

        for release in orm["packages.Release"].objects.filter(deleted=True):
            release.delete()

    def backwards(self, orm):
        pass

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'unique_together': "(('package', 'type'),)", 'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        }
    }

    complete_apps = ['packages']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0015_auto__del_field_release_deleted__del_field_package_deleted
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Release.deleted'
        db.delete_column('packages_release', 'deleted')

        # Deleting field 'Package.deleted'
        db.delete_column('packages_package', 'deleted')

    def backwards(self, orm):
        # Adding field 'Release.deleted'
        db.add_column('packages_release', 'deleted',
                      self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True),
                      keep_default=False)

        # Adding field 'Package.deleted'
        db.add_column('packages_package', 'deleted',
                      self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True),
                      keep_default=False)

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0016_auto__add_field_package_normalized_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Package.normalized_name'
        db.add_column('packages_package', 'normalized_name',
                      self.gf('django.db.models.fields.SlugField')(max_length=150, null=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Package.normalized_name'
        db.delete_column('packages_package', 'normalized_name')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'max_length': '150', 'null': 'True'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0017_normalize_names
# -*- coding: utf-8 -*-
import re
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        for package in orm["packages.Package"].objects.all():
            package.normalized_name = re.sub('[^A-Za-z0-9.]+', '-', package.name).lower()
            package.save()

    def backwards(self, orm):
        pass

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'max_length': '150', 'null': 'True'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0018_auto__chg_field_package_normalized_name__add_unique_package_normalized
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Package.normalized_name'
        db.alter_column('packages_package', 'normalized_name', self.gf('django.db.models.fields.SlugField')(default='', unique=True, max_length=150))

    def backwards(self, orm):
        # Changing field 'Package.normalized_name'
        db.alter_column('packages_package', 'normalized_name', self.gf('django.db.models.fields.SlugField')(max_length=150, null=True))

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']

########NEW FILE########
__FILENAME__ = 0019_auto__add_field_releasefile_hidden
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ReleaseFile.hidden'
        db.add_column('packages_releasefile', 'hidden',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'ReleaseFile.hidden'
        db.delete_column('packages_releasefile', 'hidden')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0020_auto__add_field_release_show_install_command
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.show_install_command'
        db.add_column('packages_release', 'show_install_command',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Release.show_install_command'
        db.delete_column('packages_release', 'show_install_command')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0021_migrate_plone
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        orm["packages.Release"].objects.filter(classifiers__trove="Framework :: Plone").update(show_install_command=False)

    def backwards(self, orm):
        pass

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0022_auto__add_downloaddelta
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DownloadDelta'
        db.create_table('packages_downloaddelta', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('file', self.gf('django.db.models.fields.related.ForeignKey')(related_name='download_deltas', to=orm['packages.ReleaseFile'])),
            ('date', self.gf('django.db.models.fields.DateField')(default=datetime.date.today)),
            ('delta', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('packages', ['DownloadDelta'])

    def backwards(self, orm):
        # Deleting model 'DownloadDelta'
        db.delete_table('packages_downloaddelta')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0023_auto__add_unique_downloaddelta_date_file
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'DownloadDelta', fields ['date', 'file']
        db.create_unique('packages_downloaddelta', ['date', 'file_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'DownloadDelta', fields ['date', 'file']
        db.delete_unique('packages_downloaddelta', ['date', 'file_id'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0024_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'DownloadDelta', fields ['date']
        db.create_index('packages_downloaddelta', ['date'])

    def backwards(self, orm):
        # Removing index on 'DownloadDelta', fields ['date']
        db.delete_index('packages_downloaddelta', ['date'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'db_index': 'True'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0025_auto__add_downloadstatscache
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DownloadStatsCache'
        db.create_table('packages_downloadstatscache', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['packages.Package'], unique=True)),
            ('data', self.gf('crate.fields.json.JSONField')()),
        ))
        db.send_create_signal('packages', ['DownloadStatsCache'])

    def backwards(self, orm):
        # Deleting model 'DownloadStatsCache'
        db.delete_table('packages_downloadstatscache')

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'db_index': 'True'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.downloadstatscache': {
            'Meta': {'object_name': 'DownloadStatsCache'},
            'data': ('crate.fields.json.JSONField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['packages.Package']", 'unique': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = 0026_auto__del_downloadstatscache
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'DownloadStatsCache'
        db.delete_table('packages_downloadstatscache')

    def backwards(self, orm):
        # Adding model 'DownloadStatsCache'
        db.create_table('packages_downloadstatscache', (
            ('data', self.gf('crate.fields.json.JSONField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['packages.Package'], unique=True)),
        ))
        db.send_create_signal('packages', ['DownloadStatsCache'])

    models = {
        'packages.changelog': {
            'Meta': {'object_name': 'ChangeLog'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25', 'db_index': 'True'})
        },
        'packages.downloaddelta': {
            'Meta': {'unique_together': "(('file', 'date'),)", 'object_name': 'DownloadDelta'},
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'db_index': 'True'}),
            'delta': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'download_deltas'", 'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.packageuri': {
            'Meta': {'unique_together': "(['package', 'uri'],)", 'object_name': 'PackageURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'package_links'", 'to': "orm['packages.Package']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '400'})
        },
        'packages.readthedocspackageslug': {
            'Meta': {'object_name': 'ReadTheDocsPackageSlug'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'readthedocs_slug'", 'unique': 'True', 'to': "orm['packages.Package']"}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.releaseobsolete': {
            'Meta': {'object_name': 'ReleaseObsolete'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'obsoletes'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseprovide': {
            'Meta': {'object_name': 'ReleaseProvide'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'provides'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaserequire': {
            'Meta': {'object_name': 'ReleaseRequire'},
            'environment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requires'", 'to': "orm['packages.Release']"}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'packages.releaseuri': {
            'Meta': {'object_name': 'ReleaseURI'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'uris'", 'to': "orm['packages.Release']"}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '500'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        }
    }

    complete_apps = ['packages']
########NEW FILE########
__FILENAME__ = models
import datetime
import os
import posixpath
import re
import urlparse
import uuid
import cStringIO
import sys

import bleach
import jinja2
import lxml.html

from docutils.core import publish_string, publish_parts
from docutils.utils import SystemMessage


from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.encoding import smart_str, force_unicode
from django.utils.importlib import import_module
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import TimeStampedModel

from crate.fields import JSONField
from crate.utils.datatools import track_data
from packages.evaluators import ReleaseEvaluator
from packages.utils import verlib

ALLOWED_TAGS = bleach.ALLOWED_TAGS + [
                    "br", "img", "span", "div", "pre", "p",
                    "dl", "dd", "dt", "tt", "cite",
                    "h1", "h2", "h3", "h4", "h5", "h6",
                    "table", "col", "tr", "td", "th", "tbody", "thead",
                    "colgroup",
                ]

ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES.items())
ALLOWED_ATTRIBUTES.update({
    "img": ["src"],
})

# Get the Storage Engine for Packages
if getattr(settings, "PACKAGE_FILE_STORAGE", None):
    mod_name, engine_name = settings.PACKAGE_FILE_STORAGE.rsplit(".", 1)
    mod = import_module(mod_name)
    package_storage = getattr(mod, engine_name)(**getattr(settings, "PACKAGE_FILE_STORAGE_OPTIONS", {}))
else:
    package_storage = None


def release_file_upload_to(instance, filename):
    dsplit = instance.digest.split("$")
    if len(dsplit) == 2:
        directory = dsplit[1]
    else:
        directory = str(uuid.uuid4()).replace("-", "")

    if getattr(settings, "PACKAGE_FILE_STORAGE_BASE_DIR", None):
        path_items = [settings.PACKAGE_FILE_STORAGE_BASE_DIR]
    else:
        path_items = []

    for char in directory[:4]:
        path_items.append(char)

    path_items += [directory, filename]

    return posixpath.join(*path_items)


# @@@ These are by Nature Hierarchical. Would we benefit from a tree structure?
class TroveClassifier(models.Model):
    trove = models.CharField(max_length=350, unique=True)

    def __unicode__(self):
        return self.trove


class Package(TimeStampedModel):
    name = models.SlugField(max_length=150, unique=True)
    normalized_name = models.SlugField(max_length=150, unique=True)
    downloads_synced_on = models.DateTimeField(default=now)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.normalized_name = re.sub('[^A-Za-z0-9.]+', '-', self.name).lower()
        return super(Package, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("package_detail", kwargs={"package": self.name})

    def get_simple_url(self):
        return reverse("simple_package_detail", kwargs={"slug": self.name})

    @property
    def downloads(self):
        KEY = "crate:packages:package:%s:downloads" % self.pk

        total_downloads = cache.get(KEY)
        if total_downloads is None:
            total_downloads = ReleaseFile.objects.filter(release__package=self).aggregate(total_downloads=Sum("downloads"))["total_downloads"]
            if total_downloads is None:
                total_downloads = 0

            cache.set(KEY, total_downloads)
        return total_downloads

    @property
    def latest(self):
        if not hasattr(self, "_latest_release"):
            releases = self.releases.filter(hidden=False).order_by("-order")[:1]
            if releases:
                self._latest_release = releases[0]
            else:
                self._latest_release = None
        return self._latest_release

    @property
    def install_command(self):
        return "pip install %(package)s" % {"package": self.name}

    @property
    def requirement_line(self):
        if self.latest is not None:
            return "%(package)s==%(version)s" % {"package": self.name, "version": self.latest.version}

    @property
    def history(self):
        from history.models import Event

        return Event.objects.filter(package=self.package.name).order_by("-created")


class PackageURI(models.Model):
    package = models.ForeignKey(Package, related_name="package_links")
    uri = models.URLField(max_length=400)

    class Meta:
        unique_together = ["package", "uri"]

    def __unicode__(self):
        return self.uri


@track_data("hidden")
class Release(models.Model, ReleaseEvaluator):

    created = AutoCreatedField("created", db_index=True)
    modified = AutoLastModifiedField("modified")

    package = models.ForeignKey(Package, related_name="releases")
    version = models.CharField(max_length=512)

    hidden = models.BooleanField(default=False)
    show_install_command = models.BooleanField(default=True)

    order = models.IntegerField(default=0, db_index=True)

    platform = models.TextField(blank=True)

    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)

    keywords = models.TextField(blank=True)

    license = models.TextField(blank=True)

    author = models.TextField(blank=True)
    author_email = models.TextField(blank=True)

    maintainer = models.TextField(blank=True)
    maintainer_email = models.TextField(blank=True)

    requires_python = models.CharField(max_length=25, blank=True)

    download_uri = models.URLField(max_length=1024, blank=True)

    classifiers = models.ManyToManyField(TroveClassifier, related_name="releases", blank=True)

    raw_data = JSONField(null=True, blank=True)

    class Meta:
        unique_together = ("package", "version")

    def __unicode__(self):
        return u"%(package)s %(version)s" % {"package": self.package.name, "version": self.version}

    def save(self, *args, **kwargs):
        # Update the Project's URIs
        docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})

        docutils_settings.update({"warning_stream": os.devnull})

        try:
            html_string = publish_string(source=smart_str(self.description), writer_name="html4css1", settings_overrides=docutils_settings)
            if html_string.strip():
                html = lxml.html.fromstring(html_string)

                for link in html.xpath("//a/@href"):
                    try:
                        if any(urlparse.urlparse(link)[:5]):
                            PackageURI.objects.get_or_create(package=self.package, uri=link)
                    except ValueError:
                        pass
        except Exception:
            # @@@ We Swallow Exceptions here, but it's the best way that I can think of atm.
            pass

        super(Release, self).save(*args, **kwargs)

        _current_show_install_command = self.show_install_command

        if self.classifiers.filter(trove="Framework :: Plone").exists():
            self.show_install_command = False
        else:
            self.show_install_command = True

        if _current_show_install_command != self.show_install_command:
            super(Release, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("package_detail", kwargs={"package": self.package.name, "version": self.version})

    @property
    def downloads(self):
        KEY = "crate:packages:release:%s:downloads" % self.pk

        total_downloads = cache.get(KEY)

        if total_downloads is None:
            total_downloads = self.files.aggregate(total_downloads=Sum("downloads"))["total_downloads"]
            if total_downloads is None:
                total_downloads = 0
            cache.set(KEY, total_downloads)

        return total_downloads

    @property
    def install_command(self):
        return "pip install %(package)s==%(version)s" % {"package": self.package.name, "version": self.version}

    @property
    def requirement_line(self):
        return "%(package)s==%(version)s" % {"package": self.package.name, "version": self.version}

    @property
    def description_html(self):
        if not hasattr(self, "_description_html"):
            # @@@ Consider Saving This to the DB
            docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})
            docutils_settings.update({
                            "raw_enabled": 0,  # no raw HTML code
                            "file_insertion_enabled": 0,  # no file/URL access
                            "halt_level": 2,  # at warnings or errors, raise an exception
                            "report_level": 5,  # never report problems with the reST code
                        })

            old_stderr = sys.stderr
            sys.stderr = s = cStringIO.StringIO()

            msg = ""

            try:
                bits = self.description.split(".. :changelog:", 1)
                description = bits[0]
                parts = publish_parts(source=smart_str(description), writer_name="html4css1", settings_overrides=docutils_settings)
            except SystemMessage:
                msg = None
            else:
                if parts is None or len(s.getvalue()) > 0:
                    msg = None
                else:
                    cnt = force_unicode(parts["fragment"])
                    cnt = bleach.clean(cnt, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
                    cnt = bleach.linkify(cnt, skip_pre=True, parse_email=True)

                    msg = jinja2.Markup(cnt)

            sys.stderr = old_stderr
            self._description_html = msg

        return self._description_html

    @property
    def changelog_html(self):
        if not hasattr(self, "_changelog_html"):
            docutils_settings = getattr(settings, "RESTRUCTUREDTEXT_FILTER_SETTINGS", {})
            docutils_settings.update({
                            "raw_enabled": 0,  # no raw HTML code
                            "file_insertion_enabled": 0,  # no file/URL access
                            "halt_level": 2,  # at warnings or errors, raise an exception
                            "report_level": 5,  # never report problems with the reST code
                        })

            old_stderr = sys.stderr
            sys.stderr = s = cStringIO.StringIO()

            msg = ""

            try:
                bits = self.description.split(".. :changelog:", 1)

                if len(bits) > 1:
                    changelog = bits[1]
                else:
                    self._changelog_html = None
                    return

                parts = publish_parts(source=smart_str(changelog), writer_name="html4css1", settings_overrides=docutils_settings)
            except SystemMessage:
                msg = None
            else:
                if parts is None or len(s.getvalue()) > 0:
                    msg = None
                else:
                    cnt = force_unicode(parts["fragment"])
                    cnt = bleach.clean(cnt, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
                    cnt = bleach.linkify(cnt, skip_pre=True, parse_email=True)

                    msg = jinja2.Markup(cnt)

            sys.stderr = old_stderr
            self._changelog_html = msg

        return self._changelog_html


@track_data("hidden")
class ReleaseFile(models.Model):

    TYPES = Choices(
        ("sdist", _("Source")),
        ("bdist_egg", "Egg"),
        ("bdist_msi", "MSI"),
        ("bdist_dmg", "DMG"),
        ("bdist_rpm", "RPM"),
        ("bdist_dumb", _("Dumb Binary Distribution")),
        ("bdist_wininst", _("Windows Installer Binary Distribution")),
    )

    created = AutoCreatedField("created", db_index=True)
    modified = AutoLastModifiedField("modified")

    hidden = models.BooleanField(default=False)

    release = models.ForeignKey(Release, related_name="files")

    type = models.CharField(max_length=25, choices=TYPES)
    file = models.FileField(upload_to=release_file_upload_to, storage=package_storage, max_length=512, blank=True)
    filename = models.CharField(max_length=200, help_text="This is the file name given to us by PyPI", blank=True, null=True, default=None)
    digest = models.CharField(max_length=512, blank=True)

    python_version = models.CharField(max_length=25)

    downloads = models.PositiveIntegerField(default=0)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("release", "type", "python_version", "filename")

    def __unicode__(self):
        return os.path.basename(self.file.name)

    def get_absolute_url(self):
        return self.file.url

    def get_python_version_display(self):
        if self.python_version.lower() == "source":
            return ""
        return self.python_version


class ReleaseURI(models.Model):
    release = models.ForeignKey(Release, related_name="uris")
    label = models.CharField(max_length=64)
    uri = models.URLField(max_length=500)


class ReleaseRequire(models.Model):

    KIND = Choices(
        ("requires", "Requirement"),
        ("requires_dist", "Dist Requirement"),
        ("external", "External Requirement"),
    )

    release = models.ForeignKey(Release, related_name="requires")

    kind = models.CharField(max_length=50, choices=KIND)
    name = models.CharField(max_length=150)
    version = models.CharField(max_length=50, blank=True)

    environment = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class ReleaseProvide(models.Model):

    KIND = Choices(
        ("provides", "Provides"),
        ("provides_dist", "Dist Provides"),
    )

    release = models.ForeignKey(Release, related_name="provides")

    kind = models.CharField(max_length=50, choices=KIND)
    name = models.CharField(max_length=150)
    version = models.CharField(max_length=50, blank=True)

    environment = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class ReleaseObsolete(models.Model):

    KIND = Choices(
        ("obsoletes", "Obsoletes"),
        ("obsoletes_dist", "Dist Obsoletes"),
    )

    release = models.ForeignKey(Release, related_name="obsoletes")

    kind = models.CharField(max_length=50, choices=KIND)
    name = models.CharField(max_length=150)
    version = models.CharField(max_length=50, blank=True)

    environment = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class DownloadDelta(models.Model):

    file = models.ForeignKey(ReleaseFile, related_name="download_deltas")
    date = models.DateField(default=datetime.date.today, db_index=True)
    delta = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Download Delta"
        verbose_name_plural = "Download Deltas"

        unique_together = ("file", "date")


class ChangeLog(models.Model):

    TYPES = Choices(
        ("new", "New"),
        ("updated", "Updated"),
    )

    created = AutoCreatedField("created", db_index=True)
    modified = AutoLastModifiedField("modified")

    type = models.CharField(max_length=25, choices=TYPES, db_index=True)
    package = models.ForeignKey(Package)
    release = models.ForeignKey(Release, blank=True, null=True)


class ReadTheDocsPackageSlug(models.Model):
    package = models.OneToOneField(Package, related_name="readthedocs_slug")
    slug = models.CharField(max_length=150, unique=True)

    def __unicode__(self):
        return u"%s" % self.slug


@receiver(post_save, sender=Release)
def version_ordering(sender, **kwargs):
    instance = kwargs.get("instance")
    if instance is not None:
        releases = Release.objects.filter(package__pk=instance.package.pk)

        versions = []
        dated = []

        for release in releases:
            normalized = verlib.suggest_normalized_version(release.version)
            if normalized is not None:
                versions.append(release)
            else:
                dated.append(release)

        versions.sort(key=lambda x: verlib.NormalizedVersion(verlib.suggest_normalized_version(x.version)))
        dated.sort(key=lambda x: x.created)

        for i, release in enumerate(dated + versions):
            if release.order != i:
                Release.objects.filter(pk=release.pk).update(order=i)


@receiver(post_save, sender=Package)
def update_packages(sender, **kwargs):
    instance = kwargs.get("instance")
    if instance is not None:
        if kwargs.get("created", False):
            ChangeLog.objects.create(type=ChangeLog.TYPES.new, package=instance)


@receiver(post_save, sender=Release)
def release_changelog(sender, **kwargs):
    instance = kwargs.get("instance")
    if instance is not None:
        if kwargs.get("created", False):
            diff = instance.created - instance.package.created
            if diff.days != 0 or diff.seconds > 600:
                ChangeLog.objects.create(type=ChangeLog.TYPES.updated, package=instance.package, release=instance)


@receiver(post_save, sender=Package)
@receiver(post_delete, sender=Package)
def regenerate_simple_index(sender, **kwargs):
    from packages.tasks import refresh_package_index_cache
    refresh_package_index_cache.delay()

########NEW FILE########
__FILENAME__ = search_indexes
from django.utils.translation import ugettext_noop as _

from haystack import indexes

from packages.models import Package
from search.indexes import PackageCelerySearchIndex

LICENSES = {
    "GNU General Public License (GPL)": "GPL",
    "GNU Library or Lesser General Public License (LGPL)": "LGPL",
    "GNU Affero General Public License v3": "Affero GPL",
    "Apache Software License": "Apache License",
    "ISC License (ISCL)": "ISC License",
    "Other/Proprietary License": _("Other/Proprietary"),
}


class PackageIndex(PackageCelerySearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr="name", boost=1.5)
    summary = indexes.CharField(null=True)
    description = indexes.CharField(null=True)
    author = indexes.CharField(null=True)
    maintainer = indexes.CharField(null=True)
    downloads = indexes.IntegerField(model_attr="downloads", indexed=False)
    url = indexes.CharField(model_attr="get_absolute_url", indexed=False)
    operating_systems = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    licenses = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    implementations = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    python_versions = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    versions = indexes.MultiValueField(null=True)
    release_count = indexes.IntegerField(default=0)

    def get_model(self):
        return Package

    def prepare(self, obj):
        data = super(PackageIndex, self).prepare(obj)

        # For ES, because it doesn't tokenize on ``_``, which causes problems
        # on lots of searches.
        if '_' in data['name']:
            data['name'] += ' ' + data['name'].replace('_', '-')

        if obj.latest:
            data["summary"] = obj.latest.summary
            data["author"] = obj.latest.author if obj.latest.author else None
            data["maintainer"] = obj.latest.maintainer if obj.latest.maintainer else None
            data["description"] = obj.latest.description if obj.latest.description else None

            operating_systems = []
            licenses = []
            implementations = []
            python_versions = []

            for classifier in obj.latest.classifiers.all():
                if classifier.trove.startswith("License ::"):
                    # We Have a License for This Project
                    licenses.append(classifier.trove.rsplit("::", 1)[1].strip())
                elif classifier.trove.startswith("Operating System ::"):
                    operating_systems.append(classifier.trove.rsplit("::", 1)[1].strip())
                elif classifier.trove.startswith("Programming Language :: Python :: Implementation ::"):
                    implementations.append(classifier.trove.rsplit("::", 1)[1].strip())
                elif classifier.trove.startswith("Programming Language :: Python ::"):
                    if classifier.trove == "Programming Language :: Python :: 2 :: Only":
                        python_versions.append("2.x")
                    elif classifier.trove.startswith("Programming Language :: Python :: 2"):
                        python_versions.append("2.x")
                    elif classifier.trove.startswith("Programming Language :: Python :: 3"):
                        python_versions.append("3.x")
                    else:
                        python_versions.append(classifier.trove.rsplit("::", 1)[1].strip())

            if not licenses:
                licenses = [_("Unknown")]

            licenses = [x for x in licenses if x not in ["OSI Approved"]]
            licenses = [LICENSES.get(x, x) for x in licenses]

            data["licenses"] = licenses

            if not operating_systems:
                operating_systems = [_("Unknown")]
            data["operating_systems"] = operating_systems

            if not implementations:
                implementations = [_("Unknown")]
            data["implementations"] = implementations

            if not python_versions:
                python_versions = [_("Unknown")]
            data["python_versions"] = python_versions

        # Pack in all the versions in decending order.
        releases = obj.releases.all().order_by("-order")
        data["versions"] = [release.version for release in releases if release.version]
        data["release_count"] = releases.count()

        # We want to scale the boost for this document based on how many downloads have
        #   been recorded for this package.
        # @@@ Might want to actually tier these values instead of percentage them.
        # Cap out downloads at 100k
        capped_downloads = min(data["downloads"], 10000)
        boost = capped_downloads / 10000.0
        data["_boost"] = 1.0 + boost

        return data

########NEW FILE########
__FILENAME__ = restricted_urls
from django.conf.urls import patterns, url

from packages.simple.views import PackageIndex, PackageDetail

handler404 = "packages.simple.views.not_found"

urlpatterns = patterns("",
    url(r"^$", PackageIndex.as_view(restricted=True), name="simple_package_index"),
    url(r"^(?P<slug>[^/]+)/(?:(?P<version>[^/]+)/)?$", PackageDetail.as_view(restricted=True), name="simple_package_detail"),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from packages.simple.views import PackageIndex, PackageDetail

handler404 = "packages.simple.views.not_found"

urlpatterns = patterns("",
    url(r"^$", PackageIndex.as_view(), name="simple_package_index"),
    url(r"^(?P<slug>[^/]+)/(?:(?P<version>[^/]+)/)?$", PackageDetail.as_view(), name="simple_package_detail"),
)

########NEW FILE########
__FILENAME__ = views
import re

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotFound, HttpResponsePermanentRedirect, Http404
from django.views.decorators.cache import cache_page
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _

from packages.models import Package


def not_found(request):
    return HttpResponseNotFound("Not Found")


class PackageIndex(ListView):

    restricted = False
    queryset = Package.objects.all().order_by("name")
    template_name = "packages/simple/package_list.html"

    @method_decorator(cache_page(60 * 15))
    def dispatch(self, *args, **kwargs):
        return super(PackageIndex, self).dispatch(*args, **kwargs)

    def get_queryset(self, force_uncached=False):
        cached = cache.get("crate:packages:simple:PackageIndex:queryset")

        if cached and not force_uncached:
            return cached

        qs = super(PackageIndex, self).get_queryset()
        cache.set("crate:packages:simple:PackageIndex:queryset", list(qs), 60 * 60 * 24 * 365)
        return qs


class PackageDetail(DetailView):

    restricted = False
    queryset = Package.objects.all().prefetch_related("releases__uris", "releases__files", "package_links")
    slug_field = "name__iexact"
    template_name = "packages/simple/package_detail.html"

    def get_object(self, queryset=None):
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError(u"Generic detail view %s must be called with "
                                 u"either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            obj = queryset.get()
        except ObjectDoesNotExist:
            try:
                queryset = self.get_queryset()
                queryset = queryset.filter(normalized_name=re.sub('[^A-Za-z0-9.]+', '-', slug).lower())
                obj = queryset.get()
            except ObjectDoesNotExist:
                raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})

        return obj

    def get_context_data(self, **kwargs):
        ctx = super(PackageDetail, self).get_context_data(**kwargs)

        releases = self.object.releases.all()

        if self.kwargs.get("version"):
            releases = releases.filter(version=self.kwargs["version"])
        else:
            releases = releases.filter(hidden=False)

        ctx.update({
            "releases": releases,
            "restricted": self.restricted,
            "show_hidden": True if self.kwargs.get("version") else False,
        })

        return ctx

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check that the case matches what it's supposed to be
        if self.object.name != self.kwargs.get(self.slug_url_kwarg, None):
            return HttpResponsePermanentRedirect(reverse("simple_package_detail", kwargs={"slug": self.object.name}))

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns("",
    url(r"^(?P<slug>[^/]+)/delta\.json$", "packages.stats.views.stats_delta", name="package_stats_delta"),
)

########NEW FILE########
__FILENAME__ = views
import collections
import json
import time

import isoweek

from django.http import HttpResponse
from django.views.decorators.cache import cache_page, cache_control
from django.shortcuts import get_object_or_404

from packages.models import Package, Release, DownloadDelta


def fetch_stats(package):
    releases = list(Release.objects.filter(package=package).only("version", "order").order_by("order"))
    specific_releases = set([x.version for x in releases[-8:]])

    deltas = list(DownloadDelta.objects.filter(file__release__in=releases).only("date", "delta", "file__release__version").order_by("date").select_related("file", "file__release"))

    # @@@ Sanity Checks
    if not deltas:
        return [{}]

    data = [{"name": "Other", "data": []}] + [{"name": release.version, "data": []} for release in releases if release.version in specific_releases]

    # Get First Week
    start_week = isoweek.Week.withdate(deltas[0].date)
    end_week = isoweek.Week.thisweek()

    current = isoweek.Week(start_week.year, start_week.week)

    while current.year <= end_week.year and current.week < end_week.week:
        for x in data:
            x["data"].append({"x": int(time.mktime(current.day(0).timetuple()))})
        current = isoweek.Week(current.year, current.week + 1)

    _data = collections.defaultdict(dict)

    for d in deltas:
        target = int(time.mktime(isoweek.Week.withdate(d.date).day(0).timetuple()))
        _data[d.file.release.version if d.file.release.version in specific_releases else "Other"][target] = d.delta

    for i in xrange(0, len(data)):
        for j in xrange(0, len(data[i]["data"])):
            data[i]["data"][j]["y"] = _data[data[i]["name"] if data[i]["name"] in specific_releases else "Other"].get(data[i]["data"][j]["x"], 0)

    return data


@cache_page(86400)
@cache_control(public=True, max_age=86400)
def stats_delta(request, slug):
    package = get_object_or_404(Package, name=slug)

    data = fetch_stats(package)

    return HttpResponse(json.dumps(data), mimetype="application/json")

########NEW FILE########
__FILENAME__ = tasks
from celery.task import task

from packages.simple.views import PackageIndex


@task
def refresh_package_index_cache():
    pi = PackageIndex()
    pi.get_queryset(force_uncached=True)

########NEW FILE########
__FILENAME__ = package_tags
from django import template
from django.core.cache import cache
from django.db.models import Sum

from packages.models import Package, Release, ReleaseFile, ChangeLog

register = template.Library()


@register.assignment_tag
def package_download_count(package_name=None):
    if package_name is None:
        cached = cache.get("crate:stats:download_count")

        if cached:
            return cached

        count = ReleaseFile.objects.all().aggregate(total_downloads=Sum("downloads")).get("total_downloads", 0)
        cache.set("crate:stats:download_count", count, 60 * 60)
        return count
    else:
        cached = cache.get("crate:stats:download_count:%s" % package_name)

        if cached:
            return cached

        count = ReleaseFile.objects.filter(
                    release__package__name=package_name
                ).aggregate(total_downloads=Sum("downloads")).get("total_downloads", 0)
        cache.set("crate:stats:download_count:%s" % package_name, count, 60 * 60 * 24)
        return count


@register.assignment_tag
def package_count():
    cached = cache.get("crate:stats:package_count")

    if cached:
        return cached

    count = Package.objects.all().count()
    cache.set("crate:stats:package_count", count, 60 * 60)
    return count


@register.assignment_tag
def get_oldest_package():
    cached = cache.get("crate:stats:oldest_package")

    if cached:
        return cached

    pkgs = Package.objects.all().order_by("created")[:1]

    if pkgs:
        cache.set("crate:stats:oldest_package", pkgs[0], 60 * 60 * 24 * 7)
        return pkgs[0]
    else:
        return None


@register.assignment_tag
def new_packages(num):
    return [
        x for
        x in ChangeLog.objects.filter(type=ChangeLog.TYPES.new).select_related("package", "release").prefetch_related("package__releases").order_by("-created")[:num * 3]
        if len(x.package.releases.all())
    ][:num]


@register.assignment_tag
def updated_packages(num):
    return ChangeLog.objects.filter(type=ChangeLog.TYPES.updated).select_related("package", "release", "release__package").order_by("-created")[:num]


@register.assignment_tag
def featured_packages(num):
    return Package.objects.filter(featured=True).order_by("?")[:num]


@register.assignment_tag
def random_packages(num):
    return Package.objects.exclude(releases=None).order_by("?")[:num]


@register.assignment_tag
def package_versions(package_name, num=None):
    KEY = "crate:packages:package_versions:%s" % package_name

    qs = cache.get(KEY)

    if qs is None:
        qs = Release.objects.filter(package__name=package_name).select_related("package").order_by("-order")
        cache.set(KEY, list(qs))

    if num is not None:
        qs = qs[:num]
    return qs


@register.assignment_tag
def package_version_count(package_name):
    return Release.objects.filter(package__name=package_name).count()

########NEW FILE########
__FILENAME__ = package_utils
import os

from django import template

register = template.Library()


@register.filter
def filename(value):
    return os.path.basename(value)


@register.filter
def digest_type(digest):
    return digest.split("$")[0]


@register.filter
def digest_value(digest):
    return digest.split("$")[1]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from packages.views import ReleaseDetail

urlpatterns = patterns("",
    url(r"^(?P<package>[^/]+)/(?:(?P<version>[^/]+)/)?$", ReleaseDetail.as_view(), name="package_detail"),
)

########NEW FILE########
__FILENAME__ = metadata
import collections
import email

from django.utils.encoding import force_unicode


def fix_encoding(s):
    return force_unicode(s, errors="ignore").encode("utf-8")


class ValidationError(Exception):
    """
        Raised When Meta Data doesn't validate
    """


class MetaData(object):
    """
        Takes a string representing a PKG-INFO file and validates it. The meta
        data is then available via the dict self.cleaned_data.
    """

    multiple_fields = set([
        "platform",
        "supported-platform",
        "classifier",
        "requires",
        "provides",
        "obsoletes",
        "requires-dist",
        "provides-dist",
        "obsoletes-dist",
        "requires-external",
        "project-url",
    ])

    def __init__(self, data):
        self.data = email.message_from_string(data.strip())
        self.errors = collections.defaultdict(set)

    def is_valid(self):
        if not hasattr(self, "_is_valid"):
            self.cleaned_data = {}

            for key in self.data.keys():
                try:
                    d = [getattr(self, "clean_%s" % key.lower(), lambda i: i)(x) for x in self.data.get_all(key)]
                    if len(d) > 1 and key.lower() not in self.multiple_fields:
                        raise ValidationError("%s has multiple values but that is not supported for this type." % key)

                    if key.lower() not in self.multiple_fields:
                        d = fix_encoding(d[0]) if len(d) else None
                    else:
                        d = [fix_encoding(x) for x in d]

                    self.cleaned_data[key.lower()] = d
                except ValidationError as e:
                    self.errors[key].add(e.message)

            if self.errors:
                self._is_valid = False
            else:
                self._is_valid = True

        return self._is_valid

########NEW FILE########
__FILENAME__ = verlib
"""
"Rational" version definition and parsing for DistutilsVersionFight
discussion at PyCon 2009.
"""

import re


class IrrationalVersionError(Exception):
    """This is an irrational version."""
    pass


class HugeMajorVersionNumError(IrrationalVersionError):
    """An irrational version because the major version number is huge
    (often because a year or date was used).

    See `error_on_huge_major_num` option in `NormalizedVersion` for details.
    This guard can be disabled by setting that option False.
    """
    pass

# A marker used in the second and third parts of the `parts` tuple, for
# versions that don't have those segments, to sort properly. An example
# of versions in sort order ('highest' last):
#   1.0b1                 ((1,0), ('b',1), ('f',))
#   1.0.dev345            ((1,0), ('f',),  ('dev', 345))
#   1.0                   ((1,0), ('f',),  ('f',))
#   1.0.post256.dev345    ((1,0), ('f',),  ('f', 'post', 256, 'dev', 345))
#   1.0.post345           ((1,0), ('f',),  ('f', 'post', 345, 'f'))
#                                   ^        ^                 ^
#   'b' < 'f' ---------------------/         |                 |
#                                            |                 |
#   'dev' < 'f' < 'post' -------------------/                  |
#                                                              |
#   'dev' < 'f' ----------------------------------------------/
# Other letters would do, but 'f' for 'final' is kind of nice.
FINAL_MARKER = ('f',)

VERSION_RE = re.compile(r'''
    ^
    (?P<version>\d+\.\d+)          # minimum 'N.N'
    (?P<extraversion>(?:\.\d+)*)   # any number of extra '.N' segments
    (?:
        (?P<prerel>[abc]|rc)       # 'a'=alpha, 'b'=beta, 'c'=release candidate
                                   # 'rc'= alias for release candidate
        (?P<prerelversion>\d+(?:\.\d+)*)
    )?
    (?P<postdev>(\.post(?P<post>\d+))?(\.dev(?P<dev>\d+))?)?
    $''', re.VERBOSE)


class NormalizedVersion(object):
    """A rational version.

    Good:
        1.2         # equivalent to "1.2.0"
        1.2.0
        1.2a1
        1.2.3a2
        1.2.3b1
        1.2.3c1
        1.2.3.4
        TODO: fill this out

    Bad:
        1           # mininum two numbers
        1.2a        # release level must have a release serial
        1.2.3b
    """
    def __init__(self, s, error_on_huge_major_num=True):
        """Create a NormalizedVersion instance from a version string.

        @param s {str} The version string.
        @param error_on_huge_major_num {bool} Whether to consider an
            apparent use of a year or full date as the major version number
            an error. Default True. One of the observed patterns on PyPI before
            the introduction of `NormalizedVersion` was version numbers like this:
                2009.01.03
                20040603
                2005.01
            This guard is here to strongly encourage the package author to
            use an alternate version, because a release deployed into PyPI
            and, e.g. downstream Linux package managers, will forever remove
            the possibility of using a version number like "1.0" (i.e.
            where the major number is less than that huge major number).
        """
        self._parse(s, error_on_huge_major_num)

    @classmethod
    def from_parts(cls, version, prerelease=FINAL_MARKER,
                   devpost=FINAL_MARKER):
        return cls(cls.parts_to_str((version, prerelease, devpost)))

    def _parse(self, s, error_on_huge_major_num=True):
        """Parses a string version into parts."""
        match = VERSION_RE.search(s)
        if not match:
            raise IrrationalVersionError(s)

        groups = match.groupdict()
        parts = []

        # main version
        block = self._parse_numdots(groups['version'], s, False, 2)
        extraversion = groups.get('extraversion')
        if extraversion not in ('', None):
            block += self._parse_numdots(extraversion[1:], s)
        parts.append(tuple(block))

        # prerelease
        prerel = groups.get('prerel')
        if prerel is not None:
            block = [prerel]
            block += self._parse_numdots(groups.get('prerelversion'), s,
                                         pad_zeros_length=1)
            parts.append(tuple(block))
        else:
            parts.append(FINAL_MARKER)

        # postdev
        if groups.get('postdev'):
            post = groups.get('post')
            dev = groups.get('dev')
            postdev = []
            if post is not None:
                postdev.extend([FINAL_MARKER[0], 'post', int(post)])
                if dev is None:
                    postdev.append(FINAL_MARKER[0])
            if dev is not None:
                postdev.extend(['dev', int(dev)])
            parts.append(tuple(postdev))
        else:
            parts.append(FINAL_MARKER)
        self.parts = tuple(parts)
        if error_on_huge_major_num and self.parts[0][0] > 1980:
            raise HugeMajorVersionNumError("huge major version number, %r, "
                "which might cause future problems: %r" % (self.parts[0][0], s))

    def _parse_numdots(self, s, full_ver_str, drop_trailing_zeros=True,
                       pad_zeros_length=0):
        """Parse 'N.N.N' sequences, return a list of ints.

        @param s {str} 'N.N.N..." sequence to be parsed
        @param full_ver_str {str} The full version string from which this
            comes. Used for error strings.
        @param drop_trailing_zeros {bool} Whether to drop trailing zeros
            from the returned list. Default True.
        @param pad_zeros_length {int} The length to which to pad the
            returned list with zeros, if necessary. Default 0.
        """
        nums = []
        for n in s.split("."):
            if len(n) > 1 and n[0] == '0':
                raise IrrationalVersionError("cannot have leading zero in "
                    "version number segment: '%s' in %r" % (n, full_ver_str))
            nums.append(int(n))
        if drop_trailing_zeros:
            while nums and nums[-1] == 0:
                nums.pop()
        while len(nums) < pad_zeros_length:
            nums.append(0)
        return nums

    def __str__(self):
        return self.parts_to_str(self.parts)

    @classmethod
    def parts_to_str(cls, parts):
        """Transforms a version expressed in tuple into its string
        representation."""
        # XXX This doesn't check for invalid tuples
        main, prerel, postdev = parts
        s = '.'.join(str(v) for v in main)
        if prerel is not FINAL_MARKER:
            s += prerel[0]
            s += '.'.join(str(v) for v in prerel[1:])
        if postdev and postdev is not FINAL_MARKER:
            if postdev[0] == 'f':
                postdev = postdev[1:]
            i = 0
            while i < len(postdev):
                if i % 2 == 0:
                    s += '.'
                s += str(postdev[i])
                i += 1
        return s

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self)

    def _cannot_compare(self, other):
        raise TypeError("cannot compare %s and %s"
                % (type(self).__name__, type(other).__name__))

    def __eq__(self, other):
        if not isinstance(other, NormalizedVersion):
            self._cannot_compare(other)
        return self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, NormalizedVersion):
            self._cannot_compare(other)
        return self.parts < other.parts

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)


def suggest_normalized_version(s):
    """Suggest a normalized version close to the given version string.

    If you have a version string that isn't rational (i.e. NormalizedVersion
    doesn't like it) then you might be able to get an equivalent (or close)
    rational version from this function.

    This does a number of simple normalizations to the given string, based
    on observation of versions currently in use on PyPI. Given a dump of
    those version during PyCon 2009, 4287 of them:
    - 2312 (53.93%) match NormalizedVersion without change
    - with the automatic suggestion
    - 3474 (81.04%) match when using this suggestion method

    @param s {str} An irrational version string.
    @returns A rational version string, or None, if couldn't determine one.
    """
    try:
        NormalizedVersion(s)
        return s   # already rational
    except IrrationalVersionError:
        pass

    rs = s.lower()

    # part of this could use maketrans
    for orig, repl in (('-alpha', 'a'), ('-beta', 'b'), ('alpha', 'a'),
                       ('beta', 'b'), ('rc', 'c'), ('-final', ''),
                       ('-pre', 'c'),
                       ('-release', ''), ('.release', ''), ('-stable', ''),
                       ('+', '.'), ('_', '.'), (' ', ''), ('.final', ''),
                       ('final', '')):
        rs = rs.replace(orig, repl)

    # if something ends with dev or pre, we add a 0
    rs = re.sub(r"pre$", r"pre0", rs)
    rs = re.sub(r"dev$", r"dev0", rs)

    # if we have something like "b-2" or "a.2" at the end of the
    # version, that is pobably beta, alpha, etc
    # let's remove the dash or dot
    rs = re.sub(r"([abc|rc])[\-\.](\d+)$", r"\1\2", rs)

    # 1.0-dev-r371 -> 1.0.dev371
    # 0.1-dev-r79 -> 0.1.dev79
    rs = re.sub(r"[\-\.](dev)[\-\.]?r?(\d+)$", r".\1\2", rs)

    # Clean: 2.0.a.3, 2.0.b1, 0.9.0~c1
    rs = re.sub(r"[.~]?([abc])\.?", r"\1", rs)

    # Clean: v0.3, v1.0
    if rs.startswith('v'):
        rs = rs[1:]

    # Clean leading '0's on numbers.
    #TODO: unintended side-effect on, e.g., "2003.05.09"
    # PyPI stats: 77 (~2%) better
    rs = re.sub(r"\b0+(\d+)(?!\d)", r"\1", rs)

    # Clean a/b/c with no version. E.g. "1.0a" -> "1.0a0". Setuptools infers
    # zero.
    # PyPI stats: 245 (7.56%) better
    rs = re.sub(r"(\d+[abc])$", r"\g<1>0", rs)

    # the 'dev-rNNN' tag is a dev tag
    rs = re.sub(r"\.?(dev-r|dev\.r)\.?(\d+)$", r".dev\2", rs)

    # clean the - when used as a pre delimiter
    rs = re.sub(r"-(a|b|c)(\d+)$", r"\1\2", rs)

    # a terminal "dev" or "devel" can be changed into ".dev0"
    rs = re.sub(r"[\.\-](dev|devel)$", r".dev0", rs)

    # a terminal "dev" can be changed into ".dev0"
    rs = re.sub(r"(?![\.\-])dev$", r".dev0", rs)

    # a terminal "final" or "stable" can be removed
    rs = re.sub(r"(final|stable)$", "", rs)

    # The 'r' and the '-' tags are post release tags
    #   0.4a1.r10       ->  0.4a1.post10
    #   0.9.33-17222    ->  0.9.3.post17222
    #   0.9.33-r17222   ->  0.9.3.post17222
    rs = re.sub(r"\.?(r|-|-r)\.?(\d+)$", r".post\2", rs)

    # Clean 'r' instead of 'dev' usage:
    #   0.9.33+r17222   ->  0.9.3.dev17222
    #   1.0dev123       ->  1.0.dev123
    #   1.0.git123      ->  1.0.dev123
    #   1.0.bzr123      ->  1.0.dev123
    #   0.1a0dev.123    ->  0.1a0.dev123
    # PyPI stats:  ~150 (~4%) better
    rs = re.sub(r"\.?(dev|git|bzr)\.?(\d+)$", r".dev\2", rs)

    # Clean '.pre' (normalized from '-pre' above) instead of 'c' usage:
    #   0.2.pre1        ->  0.2c1
    #   0.2-c1         ->  0.2c1
    #   1.0preview123   ->  1.0c123
    # PyPI stats: ~21 (0.62%) better
    rs = re.sub(r"\.?(pre|preview|-c)(\d+)$", r"c\g<2>", rs)

    # Tcl/Tk uses "px" for their post release markers
    rs = re.sub(r"p(\d+)$", r".post\1", rs)

    try:
        NormalizedVersion(rs)
        return rs   # already rational
    except IrrationalVersionError:
        pass
    return None

########NEW FILE########
__FILENAME__ = views
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.detail import DetailView

from history.models import Event
from packages.models import Release


class ReleaseDetail(DetailView):

    model = Release
    queryset = Release.objects.all().prefetch_related(
                                        "uris",
                                        "files",
                                        "requires",
                                        "provides",
                                        "obsoletes",
                                        "classifiers",
                                    )

    def get_context_data(self, **kwargs):
        ctx = super(ReleaseDetail, self).get_context_data(**kwargs)
        ctx.update({
            "release_files": [x for x in self.object.files.all() if not x.hidden],
            "version_specific": self.kwargs.get("version", None),
            "versions": Release.objects.filter(package=self.object.package).select_related("package").order_by("-order"),
            "history": Event.objects.filter(package=self.object.package.name).order_by("-created"),
        })
        return ctx

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        package = self.kwargs["package"]
        version = self.kwargs.get("version", None)

        queryset = queryset.filter(package__name=package)

        if version:
            queryset = queryset.filter(version=version)
        else:
            queryset = queryset.filter(hidden=False).order_by("-order")[:1]

        try:
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from pypi.models import PyPIMirrorPage, PyPIServerSigPage, PyPIIndexPage
from pypi.models import PyPIDownloadChange


class PyPIMirrorPageAdmin(admin.ModelAdmin):
    list_display = ["package", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["package__name", "content"]
    raw_id_fields = ["package"]


class PyPIServerSigPageAdmin(admin.ModelAdmin):
    list_display = ["package", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["package__name", "content"]
    raw_id_fields = ["package"]


class PyPIIndexPageAdmin(admin.ModelAdmin):
    list_display = ["created", "modified"]
    list_filter = ["created", "modified"]


class PyPIDownloadChangeAdmin(admin.ModelAdmin):
    list_display = ["file", "change", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["file__release__package__name"]
    raw_id_fields = ["file"]


admin.site.register(PyPIMirrorPage, PyPIMirrorPageAdmin)
admin.site.register(PyPIServerSigPage, PyPIServerSigPageAdmin)
admin.site.register(PyPIIndexPage, PyPIIndexPageAdmin)
admin.site.register(PyPIDownloadChange, PyPIDownloadChangeAdmin)

########NEW FILE########
__FILENAME__ = exceptions
class PackageHashMismatch(Exception):
    """
        The provided hash did not match what we downloaded.
    """

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ("packages", "0001_initial"),
    )

    def forwards(self, orm):
        # Adding model 'Log'
        db.create_table('pypi_log', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 8, 3, 18, 57, 369909))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 8, 3, 18, 57, 370030))),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('index', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('pypi', ['Log'])

        # Adding model 'ChangeLog'
        db.create_table('pypi_changelog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 8, 3, 18, 57, 370841))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 8, 3, 18, 57, 370939))),
            ('package', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('action', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('pypi', ['ChangeLog'])

        # Adding model 'PackageModified'
        db.create_table('pypi_packagemodified', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 8, 3, 18, 57, 374148))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 8, 3, 18, 57, 374251))),
            ('release_file', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['packages.ReleaseFile'])),
            ('url', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('last_modified', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('md5', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('pypi', ['PackageModified'])

    def backwards(self, orm):
        # Deleting model 'Log'
        db.delete_table('pypi_log')

        # Deleting model 'ChangeLog'
        db.delete_table('pypi_changelog')

        # Deleting model 'PackageModified'
        db.delete_table('pypi_packagemodified')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 379936)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 380034)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 380932)'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 381027)'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 382424)'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 382545)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 380316)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 380415)'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 379410)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 379522)'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.packagemodified': {
            'Meta': {'object_name': 'PackageModified'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 383311)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 8, 3, 18, 57, 383409)'}),
            'release_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['packages.ReleaseFile']"}),
            'url': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['pypi']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_changelog_handled
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ChangeLog.handled'
        db.add_column('pypi_changelog', 'handled',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'ChangeLog.handled'
        db.delete_column('pypi_changelog', 'handled')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 722721)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 722843)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 723760)'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 723859)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 726637)'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 726736)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 725391)'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 725501)'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 726086)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 726188)'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.packagemodified': {
            'Meta': {'object_name': 'PackageModified'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 723138)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 4, 53, 21, 723239)'}),
            'release_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['packages.ReleaseFile']"}),
            'url': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['pypi']

########NEW FILE########
__FILENAME__ = 0003_auto__add_tasklog
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TaskLog'
        db.create_table('pypi_tasklog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 23, 5, 18, 13, 579234))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 23, 5, 18, 13, 579336))),
            ('task_id', self.gf('uuidfield.fields.UUIDField')(unique=True, max_length=32)),
            ('status', self.gf('model_utils.fields.StatusField')(default='success', max_length=100, no_check_for_status=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('args', self.gf('django.db.models.fields.TextField')()),
            ('kwargs', self.gf('django.db.models.fields.TextField')()),
            ('worker', self.gf('django.db.models.fields.CharField')(max_length=300)),
        ))
        db.send_create_signal('pypi', ['TaskLog'])

    def backwards(self, orm):
        # Deleting model 'TaskLog'
        db.delete_table('pypi_tasklog')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 604913)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 605012)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 599975)'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 600073)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 603444)'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 603552)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 605301)'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 605399)'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 604367)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 604470)'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.packagemodified': {
            'Meta': {'object_name': 'PackageModified'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 599386)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 599489)'}),
            'release_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['packages.ReleaseFile']"}),
            'url': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        'pypi.tasklog': {
            'Meta': {'object_name': 'TaskLog'},
            'args': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 602660)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 18, 13, 602775)'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'status': ('model_utils.fields.StatusField', [], {'default': "'success'", 'max_length': '100', 'no_check_for_status': 'True'}),
            'task_id': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32'}),
            'worker': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        }
    }

    complete_apps = ['pypi']

########NEW FILE########
__FILENAME__ = 0004_auto__del_field_tasklog_worker__add_field_tasklog_exception
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'TaskLog.worker'
        db.delete_column('pypi_tasklog', 'worker')

        # Adding field 'TaskLog.exception'
        db.add_column('pypi_tasklog', 'exception',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'TaskLog.worker'
        raise RuntimeError("Cannot reverse this migration. 'TaskLog.worker' and its values cannot be restored.")
        # Deleting field 'TaskLog.exception'
        db.delete_column('pypi_tasklog', 'exception')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 991486)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 991590)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 988874)'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 988981)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 990532)'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 990635)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 993176)'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 993275)'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 991891)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 991988)'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.packagemodified': {
            'Meta': {'object_name': 'PackageModified'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 988118)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 988306)'}),
            'release_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['packages.ReleaseFile']"}),
            'url': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        'pypi.tasklog': {
            'Meta': {'object_name': 'TaskLog'},
            'args': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 992427)'}),
            'exception': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 23, 5, 26, 17, 992529)'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'status': ('model_utils.fields.StatusField', [], {'default': "'success'", 'max_length': '100', 'no_check_for_status': 'True'}),
            'task_id': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32'})
        }
    }

    complete_apps = ['pypi']

########NEW FILE########
__FILENAME__ = 0005_auto__add_downloadchange
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DownloadChange'
        db.create_table('pypi_downloadchange', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 1, 29, 3, 56, 35, 358127))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 1, 29, 3, 56, 35, 358227))),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Release'])),
            ('change', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('pypi', ['DownloadChange'])

    def backwards(self, orm):
        # Deleting model 'DownloadChange'
        db.delete_table('pypi_downloadchange')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 386489)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 386583)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 382977)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'frequency': ('django.db.models.fields.CharField', [], {'default': "'hourly'", 'max_length': '25'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 383074)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 385158)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 385257)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 382321)'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 382418)'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.downloadchange': {
            'Meta': {'object_name': 'DownloadChange'},
            'change': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 386039)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 386135)'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']"})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 381036)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 381150)'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.packagemodified': {
            'Meta': {'object_name': 'PackageModified'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 384564)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 384671)'}),
            'release_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['packages.ReleaseFile']"}),
            'url': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        'pypi.tasklog': {
            'Meta': {'object_name': 'TaskLog'},
            'args': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 381582)'}),
            'exception': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 1, 29, 3, 56, 35, 381677)'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'status': ('model_utils.fields.StatusField', [], {'default': "'success'", 'max_length': '100', 'no_check_for_status': 'True'}),
            'task_id': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32'})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0006_auto__add_pypimirrorpage__add_unique_pypimirrorpage_package_type
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PyPIMirrorPage'
        db.create_table('pypi_pypimirrorpage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Package'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('pypi', ['PyPIMirrorPage'])

        # Adding unique constraint on 'PyPIMirrorPage', fields ['package', 'type']
        db.create_unique('pypi_pypimirrorpage', ['package_id', 'type'])

    def backwards(self, orm):
        # Removing unique constraint on 'PyPIMirrorPage', fields ['package', 'type']
        db.delete_unique('pypi_pypimirrorpage', ['package_id', 'type'])

        # Deleting model 'PyPIMirrorPage'
        db.delete_table('pypi_pypimirrorpage')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 659925)'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 660167)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 660018)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 660937)', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 661030)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 657638)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 657739)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 658850)'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 658945)'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.downloadchange': {
            'Meta': {'object_name': 'DownloadChange'},
            'change': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 659485)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 659578)'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']"})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 657163)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 657254)'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.packagemodified': {
            'Meta': {'object_name': 'PackageModified'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 660372)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 660462)'}),
            'release_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['packages.ReleaseFile']"}),
            'url': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'unique_together': "(('package', 'type'),)", 'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'pypi.tasklog': {
            'Meta': {'object_name': 'TaskLog'},
            'args': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 656437)'}),
            'exception': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 18, 2, 48, 7, 656543)'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'status': ('model_utils.fields.StatusField', [], {'default': "'pending'", 'max_length': '100', 'no_check_for_status': 'True'}),
            'task_id': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32'})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0007_move_package_modified_into_redis
# -*- coding: utf-8 -*-
import redis

from django.conf import settings

from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))

        for package_modified in orm["pypi.PackageModified"].objects.all():
            datastore_key = "crate:pypi:download:%(url)s" % {"url": package_modified.url}

            datastore.hmset(datastore_key, {
                "md5": package_modified.md5,
                "modified": package_modified.last_modified,
            })

            datastore.expire(datastore_key, 31556926)

    def backwards(self, orm):
        datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))

        for key in datastore.keys("crate:pypi:download:*"):
            url = key.rsplit(":", 1)[1]
            data = datastore.hgetall("crate_pypi:download:%s" % url)

            defaults = {
                "md5": data["md5"],
                "last_modified": data["modified"],
            }

            pm, c = orm["pypi.PackageModified"].objects.get_or_create(url=url, defaults=defaults)

            if not c:
                pm.md5 = defaults["md5"]
                pm.last_modified = defaults["last_modified"]
                pm.save()

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 516258)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 516622)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 516386)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 518316)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 518416)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 516856)', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 516957)'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 520825)'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 520930)'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.downloadchange': {
            'Meta': {'object_name': 'DownloadChange'},
            'change': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 521504)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 521603)'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']"})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 517789)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 517890)'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.packagemodified': {
            'Meta': {'object_name': 'PackageModified'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 521976)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'md5': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 522074)'}),
            'release_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': "orm['packages.ReleaseFile']"}),
            'url': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'unique_together': "(('package', 'type'),)", 'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'pypi.tasklog': {
            'Meta': {'object_name': 'TaskLog'},
            'args': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 520036)'}),
            'exception': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.TextField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 27, 7, 520138)'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'status': ('model_utils.fields.StatusField', [], {'default': "'pending'", 'max_length': '100', 'no_check_for_status': 'True'}),
            'task_id': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32'})
        }
    }

    complete_apps = ['pypi']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0008_auto__del_tasklog__del_packagemodified
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'TaskLog'
        db.delete_table('pypi_tasklog')

        # Deleting model 'PackageModified'
        db.delete_table('pypi_packagemodified')

    def backwards(self, orm):
        # Adding model 'TaskLog'
        db.create_table('pypi_tasklog', (
            ('status', self.gf('model_utils.fields.StatusField')(default='pending', max_length=100, no_check_for_status=True)),
            ('exception', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('task_id', self.gf('uuidfield.fields.UUIDField')(max_length=32, unique=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 2, 20, 0, 27, 7, 520036))),
            ('kwargs', self.gf('django.db.models.fields.TextField')()),
            ('args', self.gf('django.db.models.fields.TextField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 2, 20, 0, 27, 7, 520138))),
        ))
        db.send_create_signal('pypi', ['TaskLog'])

        # Adding model 'PackageModified'
        db.create_table('pypi_packagemodified', (
            ('last_modified', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 2, 20, 0, 27, 7, 521976))),
            ('url', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('release_file', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', to=orm['packages.ReleaseFile'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 2, 20, 0, 27, 7, 522074))),
            ('md5', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('pypi', ['PackageModified'])

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 989261)'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 989593)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 989365)'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 990149)', 'db_index': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 990244)'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 988589)'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 988690)'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.downloadchange': {
            'Meta': {'object_name': 'DownloadChange'},
            'change': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 991858)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 991967)'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Release']"})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 992325)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime(2012, 2, 20, 0, 41, 57, 992418)'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'unique_together': "(('package', 'type'),)", 'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0009_auto__del_downloadchange
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'DownloadChange'
        db.delete_table('pypi_downloadchange')

    def backwards(self, orm):
        # Adding model 'DownloadChange'
        db.create_table('pypi_downloadchange', (
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime(2012, 2, 20, 0, 41, 57, 991858))),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime(2012, 2, 20, 0, 41, 57, 991967))),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Release'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('change', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('pypi', ['DownloadChange'])

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'unique_together': "(('package', 'type'),)", 'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0010_auto__add_pypiserversigpage
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PyPIServerSigPage'
        db.create_table('pypi_pypiserversigpage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('package', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.Package'])),
            ('content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('pypi', ['PyPIServerSigPage'])

    def backwards(self, orm):
        # Deleting model 'PyPIServerSigPage'
        db.delete_table('pypi_pypiserversigpage')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'unique_together': "(('package', 'type'),)", 'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'pypi.pypiserversigpage': {
            'Meta': {'object_name': 'PyPIServerSigPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0011_split_serversig
# -*- coding: utf-8 -*-
from south.v2 import DataMigration


class Migration(DataMigration):

    def forwards(self, orm):
        for pmp in orm["pypi.PyPIMirrorPage"].objects.filter(type="serversig"):
            orm["pypi.PyPIServerSigPage"].objects.create(package=pmp.package, content=pmp.content)
            pmp.delete()

    def backwards(self, orm):
        for pssp in orm["PyPIServerSigPage"].objects.all():
            orm["pypi.PyPIMirrorPage"].objects.create(package=pssp.package, content=pssp.content, type="simple")

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'unique_together': "(('package', 'type'),)", 'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'pypi.pypiserversigpage': {
            'Meta': {'object_name': 'PyPIServerSigPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        }
    }

    complete_apps = ['pypi']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0012_auto__del_field_pypimirrorpage_type__add_unique_pypimirrorpage_package
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'PyPIMirrorPage', fields ['type', 'package']
        db.delete_unique('pypi_pypimirrorpage', ['type', 'package_id'])

        # Deleting field 'PyPIMirrorPage.type'
        db.delete_column('pypi_pypimirrorpage', 'type')

        # Adding unique constraint on 'PyPIMirrorPage', fields ['package']
        db.create_unique('pypi_pypimirrorpage', ['package_id'])

    def backwards(self, orm):
        # Removing unique constraint on 'PyPIMirrorPage', fields ['package']
        db.delete_unique('pypi_pypimirrorpage', ['package_id'])


        # User chose to not deal with backwards NULL issues for 'PyPIMirrorPage.type'
        raise RuntimeError("Cannot reverse this migration. 'PyPIMirrorPage.type' and its values cannot be restored.")
        # Adding unique constraint on 'PyPIMirrorPage', fields ['type', 'package']
        db.create_unique('pypi_pypimirrorpage', ['type', 'package_id'])

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']", 'unique': 'True'})
        },
        'pypi.pypiserversigpage': {
            'Meta': {'object_name': 'PyPIServerSigPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0013_auto__add_field_pypimirrorpage_created__add_field_pypimirrorpage_modif
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'PyPIMirrorPage.created'
        db.add_column('pypi_pypimirrorpage', 'created',
                      self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now),
                      keep_default=False)

        # Adding field 'PyPIMirrorPage.modified'
        db.add_column('pypi_pypimirrorpage', 'modified',
                      self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now),
                      keep_default=False)

        # Adding field 'PyPIServerSigPage.created'
        db.add_column('pypi_pypiserversigpage', 'created',
                      self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now),
                      keep_default=False)

        # Adding field 'PyPIServerSigPage.modified'
        db.add_column('pypi_pypiserversigpage', 'modified',
                      self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'PyPIMirrorPage.created'
        db.delete_column('pypi_pypimirrorpage', 'created')

        # Deleting field 'PyPIMirrorPage.modified'
        db.delete_column('pypi_pypimirrorpage', 'modified')

        # Deleting field 'PyPIServerSigPage.created'
        db.delete_column('pypi_pypiserversigpage', 'created')

        # Deleting field 'PyPIServerSigPage.modified'
        db.delete_column('pypi_pypiserversigpage', 'modified')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']", 'unique': 'True'})
        },
        'pypi.pypiserversigpage': {
            'Meta': {'object_name': 'PyPIServerSigPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0014_auto__add_pypiindexpage
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PyPIIndexPage'
        db.create_table('pypi_pypiindexpage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('pypi', ['PyPIIndexPage'])

    def backwards(self, orm):
        # Deleting model 'PyPIIndexPage'
        db.delete_table('pypi_pypiindexpage')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'pypi.changelog': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'ChangeLog'},
            'action': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'handled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'})
        },
        'pypi.log': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Log'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'pypi.pypiindexpage': {
            'Meta': {'object_name': 'PyPIIndexPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']", 'unique': 'True'})
        },
        'pypi.pypiserversigpage': {
            'Meta': {'object_name': 'PyPIServerSigPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0015_auto__del_log__del_changelog__add_pypidownloadchange
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Log'
        db.delete_table('pypi_log')

        # Deleting model 'ChangeLog'
        db.delete_table('pypi_changelog')

        # Adding model 'PyPIDownloadChange'
        db.create_table('pypi_pypidownloadchange', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('file', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['packages.ReleaseFile'])),
            ('change', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('pypi', ['PyPIDownloadChange'])

    def backwards(self, orm):
        # Adding model 'Log'
        db.create_table('pypi_log', (
            ('index', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('pypi', ['Log'])

        # Adding model 'ChangeLog'
        db.create_table('pypi_changelog', (
            ('handled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('version', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('action', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('package', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('pypi', ['ChangeLog'])

        # Deleting model 'PyPIDownloadChange'
        db.delete_table('pypi_pypidownloadchange')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.pypidownloadchange': {
            'Meta': {'object_name': 'PyPIDownloadChange'},
            'change': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        },
        'pypi.pypiindexpage': {
            'Meta': {'object_name': 'PyPIIndexPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']", 'unique': 'True'})
        },
        'pypi.pypiserversigpage': {
            'Meta': {'object_name': 'PyPIServerSigPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0016_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'PyPIIndexPage', fields ['created']
        db.create_index('pypi_pypiindexpage', ['created'])

    def backwards(self, orm):
        # Removing index on 'PyPIIndexPage', fields ['created']
        db.delete_index('pypi_pypiindexpage', ['created'])

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.pypidownloadchange': {
            'Meta': {'object_name': 'PyPIDownloadChange'},
            'change': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        },
        'pypi.pypiindexpage': {
            'Meta': {'object_name': 'PyPIIndexPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']", 'unique': 'True'})
        },
        'pypi.pypiserversigpage': {
            'Meta': {'object_name': 'PyPIServerSigPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = 0017_auto__add_field_pypidownloadchange_integrated
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'PyPIDownloadChange.integrated'
        db.add_column('pypi_pypidownloadchange', 'integrated',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'PyPIDownloadChange.integrated'
        db.delete_column('pypi_pypidownloadchange', 'integrated')

    models = {
        'packages.package': {
            'Meta': {'object_name': 'Package'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'downloads_synced_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'}),
            'normalized_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '150'})
        },
        'packages.release': {
            'Meta': {'unique_together': "(('package', 'version'),)", 'object_name': 'Release'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'author_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'classifiers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'releases'", 'blank': 'True', 'to': "orm['packages.TroveClassifier']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'download_uri': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'license': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'maintainer_email': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['packages.Package']"}),
            'platform': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'raw_data': ('crate.fields.json.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'requires_python': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'show_install_command': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'packages.releasefile': {
            'Meta': {'unique_together': "(('release', 'type', 'python_version', 'filename'),)", 'object_name': 'ReleaseFile'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'digest': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '512', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'python_version': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'files'", 'to': "orm['packages.Release']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '25'})
        },
        'packages.troveclassifier': {
            'Meta': {'object_name': 'TroveClassifier'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trove': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '350'})
        },
        'pypi.pypidownloadchange': {
            'Meta': {'object_name': 'PyPIDownloadChange'},
            'change': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.ReleaseFile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'integrated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        },
        'pypi.pypiindexpage': {
            'Meta': {'object_name': 'PyPIIndexPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        },
        'pypi.pypimirrorpage': {
            'Meta': {'object_name': 'PyPIMirrorPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']", 'unique': 'True'})
        },
        'pypi.pypiserversigpage': {
            'Meta': {'object_name': 'PyPIServerSigPage'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'package': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['packages.Package']"})
        }
    }

    complete_apps = ['pypi']
########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import TimeStampedModel


class PyPIMirrorPage(TimeStampedModel):

    package = models.ForeignKey("packages.Package", unique=True)
    content = models.TextField()

    def __unicode__(self):
        return self.package.name

    def get_relative_url(self, current_url):
        absolute_url_split = reverse("pypi_package_detail", kwargs={"slug": self.package.name}).split("/")
        current_url_split = current_url.split("/")

        relative_url_split = absolute_url_split[:]
        for i, part in enumerate(absolute_url_split):
            if len(current_url_split) > i and part == current_url_split[i]:
                relative_url_split = relative_url_split[1:]

        return "/".join(relative_url_split)


class PyPIServerSigPage(TimeStampedModel):

    package = models.ForeignKey("packages.Package")
    content = models.TextField()

    def __unicode__(self):
        return self.package.name


class PyPIIndexPage(models.Model):

    created = AutoCreatedField("created", db_index=True)
    modified = AutoLastModifiedField("modified")

    content = models.TextField()

    def __unicode__(self):
        return "PyPI Index Page: %s" % self.created.isoformat()


class PyPIDownloadChange(TimeStampedModel):

    file = models.ForeignKey("packages.ReleaseFile")
    change = models.IntegerField(default=0)
    integrated = models.BooleanField(default=False)


@receiver(post_save, sender=PyPIMirrorPage)
@receiver(post_delete, sender=PyPIMirrorPage)
def regenerate_simple_index(sender, **kwargs):
    from pypi.tasks import refresh_pypi_package_index_cache
    refresh_pypi_package_index_cache.delay()

########NEW FILE########
__FILENAME__ = processor
import base64
import hashlib
import logging
import re
import urllib
import urlparse
import xmlrpclib

import redis
import requests
import lxml.html

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.timezone import utc

from history.models import Event
from packages.models import Package, Release, TroveClassifier
from packages.models import ReleaseRequire, ReleaseProvide, ReleaseObsolete, ReleaseURI, ReleaseFile
from pypi.exceptions import PackageHashMismatch
from pypi.models import PyPIMirrorPage, PyPIServerSigPage
from pypi.utils.serversigs import load_key, verify

logger = logging.getLogger(__name__)

INDEX_URL = "http://pypi.python.org/pypi"
SIMPLE_URL = "http://pypi.python.org/simple/"
SERVERSIG_URL = "http://pypi.python.org/serversig/"
SERVERKEY_URL = "http://pypi.python.org/serverkey"

SERVERKEY_KEY = "crate:pypi:serverkey"

_disutils2_version_capture = re.compile("^(.*?)(?:\(([^()]+)\))?$")
_md5_re = re.compile(r"(https?://pypi\.python\.org/packages/.+)#md5=([a-f0-9]+)")


def get_helper(data, key, default=None):
    if data.get(key) and data[key] != "UNKNOWN":
        return data[key]
    return "" if default is None else default


def split_meta(meta):
    meta_split = meta.split(";", 1)
    meta_name, meta_version = _disutils2_version_capture.search(meta_split[0].strip()).groups()
    meta_env = meta_split[1].strip() if len(meta_split) == 2 else ""

    return {
        "name": meta_name,
        "version": meta_version if meta_version is not None else "",
        "environment": meta_env,
    }


class PyPIPackage(object):

    def __init__(self, name, version=None):
        self.name = name
        self.version = version

        self.stored = False

        self.pypi = xmlrpclib.ServerProxy(INDEX_URL, use_datetime=True)
        self.datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))

    def process(self, bulk=False, download=True, skip_modified=True):
        self.bulk = bulk
        self.skip_modified = skip_modified

        self.fetch()
        self.build()

        with transaction.commit_on_success():
            self.store()

            if download:
                self.download()

    def delete(self):
        with transaction.commit_on_success():
            self.verify_and_sync_pages()

            if self.version is None:
                # Delete the entire package
                packages = Package.objects.filter(name=self.name).select_for_update()
                releases = Release.objects.filter(package__in=packages).select_for_update()

                for package in packages:
                    package.delete()
            else:
                # Delete only this release
                try:
                    package = Package.objects.get(name=self.name)
                except Package.DoesNotExist:
                    return

                releases = Release.objects.filter(package=package, version=self.version).select_for_update()

                for release in releases:
                    release.hidden = True
                    release.save()

    def remove_files(self, *files):
        self.verify_and_sync_pages()

        packages = Package.objects.filter(name=self.name)
        releases = Release.objects.filter(package__in=packages)

        for rf in ReleaseFile.objects.filter(release__in=releases, filename__in=files):
            rf.hidden = True
            rf.save()

    def fetch(self):
        logger.debug("[FETCH] %s%s" % (self.name, " %s" % self.version if self.version else ""))

        # Fetch meta data for this release
        self.releases = self.get_releases()
        self.release_data = self.get_release_data()
        self.release_url_data = self.get_release_urls()

    def build(self):
        logger.debug("[BUILD] %s%s" % (self.name, " %s" % self.version if self.version else ""))

        # Check to Make sure fetch has been ran
        if not hasattr(self, "releases") or not hasattr(self, "release_data") or not hasattr(self, "release_url_data"):
            raise Exception("fetch must be called prior to running build")  # @@@ Make a Custom Exception

        # Construct our representation of the releases
        self.data = {}
        for release in self.releases:
            data = {}

            data["package"] = self.name
            data["version"] = release

            data["author"] = get_helper(self.release_data[release], "author")
            data["author_email"] = get_helper(self.release_data[release], "author_email")

            data["maintainer"] = get_helper(self.release_data[release], "maintainer")
            data["maintainer_email"] = get_helper(self.release_data[release], "maintainer_email")

            data["summary"] = get_helper(self.release_data[release], "summary")
            data["description"] = get_helper(self.release_data[release], "description")

            data["license"] = get_helper(self.release_data[release], "license")
            data["keywords"] = get_helper(self.release_data[release], "keywords")  # @@@ Switch This to a List
            data["platform"] = get_helper(self.release_data[release], "platform")
            data["download_uri"] = get_helper(self.release_data[release], "download_url")  # @@@ Should This Go Under URI?
            data["requires_python"] = get_helper(self.release_data[release], "required_python")

            data["stable_version"] = get_helper(self.release_data[release], "stable_version")  # @@@ What Is This?

            data["classifiers"] = get_helper(self.release_data[release], "classifiers", [])

            # Construct the URIs
            data["uris"] = {}

            if get_helper(self.release_data[release], "home_page"):
                data["uris"]["Home Page"] = get_helper(self.release_data[release], "home_page")

            if get_helper(self.release_data[release], "bugtrack_url"):
                data["uris"]["Bug Tracker"] = get_helper(self.release_data[release], "bugtrack_url")

            for label, url in [x.split(",", 1) for x in get_helper(self.release_data[release], "project_url", [])]:
                data["uris"][label] = url

            # Construct Requires
            data["requires"] = []

            for kind in ["requires", "requires_dist", "requires_external"]:
                for require in get_helper(self.release_data[release], kind, []):
                    req = {"kind": kind if kind is not "requires_external" else "external"}
                    req.update(split_meta(require))
                    data["requires"].append(req)

            # Construct Provides
            data["provides"] = []

            for kind in ["provides", "provides_dist"]:
                for provides in get_helper(self.release_data[release], kind, []):
                    req = {"kind": kind}
                    req.update(split_meta(provides))
                    data["provides"].append(req)

            # Construct Obsoletes
            data["obsoletes"] = []

            for kind in ["obsoletes", "obsoletes_dist"]:
                for provides in get_helper(self.release_data[release], kind, []):
                    req = {"kind": kind}
                    req.update(split_meta(provides))
                    data["obsoletes"].append(req)

            # Construct Files
            data["files"] = []

            for url_data in self.release_url_data[release]:
                data["files"].append({
                    "comment": get_helper(url_data, "comment_text"),
                    "downloads": get_helper(url_data, "downloads", 0),
                    "file": get_helper(url_data, "url"),
                    "filename": get_helper(url_data, "filename"),
                    "python_version": get_helper(url_data, "python_version"),
                    "type": get_helper(url_data, "packagetype"),
                    "digests": {
                        "md5": url_data["md5_digest"].lower(),
                    }
                })
                if url_data.get("upload_time"):
                    data["files"][-1]["created"] = url_data["upload_time"].replace(tzinfo=utc)

            for file_data in data["files"]:
                if file_data.get("created"):
                    if data.get("created"):
                        if file_data["created"] < data["created"]:
                            data["created"] = file_data["created"]
                    else:
                        data["created"] = file_data["created"]

            self.data[release] = data

            logger.debug("[RELEASE BUILD DATA] %s %s %s" % (self.name, release, data))

    def store(self):
        package, _ = Package.objects.get_or_create(name=self.name)

        for data in self.data.values():
            try:
                release = Release.objects.get(package=package, version=data["version"])
            except Release.DoesNotExist:
                release = Release(package=package, version=data["version"])
                release.full_clean()
                release.save()

            # This is an extra database call but it should prevent ShareLocks
            Release.objects.filter(pk=release.pk).select_for_update()

            if release.hidden:
                release.hidden = False

            for key, value in data.iteritems():
                if key in ["package", "version"]:
                    # Short circuit package and version
                    continue

                if key == "uris":
                    ReleaseURI.objects.filter(release=release).delete()
                    for label, uri in value.iteritems():
                        try:
                            ReleaseURI.objects.get(release=release, label=label, uri=uri)
                        except ReleaseURI.DoesNotExist:
                            try:
                                release_uri = ReleaseURI(release=release, label=label, uri=uri)
                                release_uri.full_clean()
                                release_uri.save(force_insert=True)
                            except ValidationError:
                                logger.exception("%s, %s for %s-%s Invalid Data" % (label, uri, release.package.name, release.version))
                elif key == "classifiers":
                    release.classifiers.clear()
                    for classifier in value:
                        try:
                            trove = TroveClassifier.objects.get(trove=classifier)
                        except TroveClassifier.DoesNotExist:
                            trove = TroveClassifier(trove=classifier)
                            trove.full_clean()
                            trove.save(force_insert=True)
                        release.classifiers.add(trove)
                elif key in ["requires", "provides", "obsoletes"]:
                    model = {"requires": ReleaseRequire, "provides": ReleaseProvide, "obsoletes": ReleaseObsolete}.get(key)
                    model.objects.filter(release=release).delete()
                    for item in value:
                        try:
                            model.objects.get(release=release, **item)
                        except model.DoesNotExist:
                            m = model(release=release, **item)
                            m.full_clean()
                            m.save(force_insert=True)
                elif key == "files":
                    files = ReleaseFile.objects.filter(release=release)
                    filenames = dict([(x.filename, x) for x in files])

                    for f in value:
                        try:
                            rf = ReleaseFile.objects.get(
                                    release=release,
                                    type=f["type"],
                                    filename=f["filename"],
                                    python_version=f["python_version"],
                                )

                            for k, v in f.iteritems():
                                if k in ["digests", "file", "filename", "type", "python_version"]:
                                    continue
                                setattr(rf, k, v)

                            rf.hidden = False
                            rf.full_clean()
                            rf.save()

                        except ReleaseFile.DoesNotExist:
                            rf = ReleaseFile(
                                    release=release,
                                    type=f["type"],
                                    filename=f["filename"],
                                    python_version=f["python_version"],
                                    **dict([(k, v) for k, v in f.iteritems() if k not in ["digests", "file", "filename", "type", "python_version"]])
                                )

                            rf.hidden = False
                            rf.full_clean()
                            rf.save()

                        if f["filename"] in filenames.keys():
                            del filenames[f["filename"]]

                    if filenames:
                        for rf in ReleaseFile.objects.filter(pk__in=[f.pk for f in filenames.values()]):
                            rf.hidden = True
                            rf.save()
                else:
                    setattr(release, key, value)

            while True:
                try:
                    release.full_clean()
                except ValidationError as e:
                    if "download_uri" in e.message_dict:
                        release.download_uri = ""
                        logger.exception("%s-%s Release Validation Error %s" % (release.package.name, release.version, str(e.message_dict)))
                    else:
                        raise
                else:
                    break
            release.save()

        # Mark unsynced as deleted when bulk processing
        if self.bulk:
            for release in Release.objects.filter(package=package).exclude(version__in=self.data.keys()):
                release.hidden = True
                release.save()

        self.stored = True

    def download(self):
        # Check to Make sure fetch has been ran
        if not hasattr(self, "releases") or not hasattr(self, "release_data") or not hasattr(self, "release_url_data"):
            raise Exception("fetch and build must be called prior to running download")  # @@@ Make a Custom Exception

        # Check to Make sure build has been ran
        if not hasattr(self, "data"):
            raise Exception("build must be called prior to running download")  # @@@ Make a Custom Exception

        if not self.stored:
            raise Exception("package must be stored prior to downloading")  # @@@ Make a Custom Exception

        pypi_pages = self.verify_and_sync_pages()

        for data in self.data.values():
            try:
                if pypi_pages.get("has_sig"):
                    simple_html = lxml.html.fromstring(pypi_pages["simple"])
                    simple_html.make_links_absolute(urlparse.urljoin(SIMPLE_URL, data["package"]) + "/")

                    verified_md5_hashes = {}

                    for link in simple_html.iterlinks():
                            m = _md5_re.search(link[2])
                            if m:
                                url, md5_hash = m.groups()
                                verified_md5_hashes[url] = md5_hash

                package = Package.objects.get(name=data["package"])
                release = Release.objects.filter(package=package, version=data["version"]).select_for_update()

                for release_file in ReleaseFile.objects.filter(release=release, filename__in=[x["filename"] for x in data["files"]]).select_for_update():
                    file_data = [x for x in data["files"] if x["filename"] == release_file.filename][0]

                    if pypi_pages.get("has_sig"):
                        if verified_md5_hashes[file_data["file"]].lower() != file_data["digests"]["md5"].lower():
                            raise Exception("MD5 does not match simple API md5 [Verified by ServerSig]")  # @@@ Custom Exception

                    datastore_key = "crate:pypi:download:%(url)s" % {"url": file_data["file"]}
                    stored_file_data = self.datastore.hgetall(datastore_key)

                    headers = None

                    if stored_file_data and self.skip_modified:
                        # Stored data exists for this file
                        if release_file.file:
                            try:
                                release_file.file.read()
                            except IOError:
                                pass
                            else:
                                # We already have a file
                                if stored_file_data["md5"].lower() == file_data["digests"]["md5"].lower():
                                    # The supposed MD5 from PyPI matches our local
                                    headers = {
                                        "If-Modified-Since": stored_file_data["modified"],
                                    }

                    resp = requests.get(file_data["file"], headers=headers, prefetch=True)

                    if resp.status_code == 304:
                        logger.info("[DOWNLOAD] skipping %(filename)s because it has not been modified" % {"filename": release_file.filename})
                        return
                    logger.info("[DOWNLOAD] downloading %(filename)s" % {"filename": release_file.filename})

                    resp.raise_for_status()

                    # Make sure the MD5 of the file we receive matched what we were told it is
                    if hashlib.md5(resp.content).hexdigest().lower() != file_data["digests"]["md5"].lower():
                        raise PackageHashMismatch("%s does not match %s for %s %s" % (
                                                            hashlib.md5(resp.content).hexdigest().lower(),
                                                            file_data["digests"]["md5"].lower(),
                                                            file_data["type"],
                                                            file_data["filename"],
                                                        ))

                    release_file.digest = "$".join(["sha256", hashlib.sha256(resp.content).hexdigest().lower()])

                    release_file.full_clean()
                    release_file.file.save(file_data["filename"], ContentFile(resp.content), save=False)
                    release_file.save()

                    Event.objects.create(
                        package=release_file.release.package.name,
                        version=release_file.release.version,
                        action=Event.ACTIONS.file_add,
                        data={
                            "filename": release_file.filename,
                            "digest": release_file.digest,
                            "uri": release_file.get_absolute_url(),
                        }
                    )

                    # Store data relating to this file (if modified etc)
                    stored_file_data = {
                        "md5": file_data["digests"]["md5"].lower(),
                        "modified": resp.headers.get("Last-Modified"),
                    }

                    if resp.headers.get("Last-Modified"):
                        self.datastore.hmset(datastore_key, {
                            "md5": file_data["digests"]["md5"].lower(),
                            "modified": resp.headers["Last-Modified"],
                        })
                        # Set a year expire on the key so that stale entries disappear
                        self.datastore.expire(datastore_key, 31556926)
                    else:
                        self.datastore.delete(datastore_key)
            except requests.HTTPError:
                logger.exception("[DOWNLOAD ERROR]")

    def get_releases(self):
        if self.version is None:
            releases = self.pypi.package_releases(self.name, True)
        else:
            releases = [self.version]

        logger.debug("[RELEASES] %s%s [%s]" % (self.name, " %s" % self.version if self.version else "", ", ".join(releases)))

        return releases

    def get_release_data(self):
        release_data = []
        for release in self.releases:
            data = self.pypi.release_data(self.name, release)
            logger.debug("[RELEASE DATA] %s %s" % (self.name, release))
            release_data.append([release, data])
        return dict(release_data)

    def get_release_urls(self):
        release_url_data = []
        for release in self.releases:
            data = self.pypi.release_urls(self.name, release)
            logger.info("[RELEASE URL] %s %s" % (self.name, release))
            logger.debug("[RELEASE URL DATA] %s %s %s" % (self.name, release, data))
            release_url_data.append([release, data])
        return dict(release_url_data)

    def verify_and_sync_pages(self):
        # Get the Server Key for PyPI
        if self.datastore.get(SERVERKEY_KEY):
            key = load_key(self.datastore.get(SERVERKEY_KEY))
        else:
            serverkey = requests.get(SERVERKEY_URL, prefetch=True)
            key = load_key(serverkey.content)
            self.datastore.set(SERVERKEY_KEY, serverkey.content)

        try:
            # Download the "simple" page from PyPI for this package
            simple = requests.get(urlparse.urljoin(SIMPLE_URL, urllib.quote(self.name)), prefetch=True)
            simple.raise_for_status()
        except requests.HTTPError:
            if simple.status_code == 404:
                return {"has_sig": False}
            raise

        try:
            # Download the "serversig" page from PyPI for this package
            serversig = requests.get(urlparse.urljoin(SERVERSIG_URL, urllib.quote(self.name)), prefetch=True)
            serversig.raise_for_status()
        except requests.HTTPError:
            if serversig.status_code == 404:
                return {"has_sig": False}
            raise

        try:
            if not verify(key, simple.content, serversig.content):
                raise Exception("Simple API page does not match serversig")  # @@@ This Should be Custom Exception
        except (UnicodeDecodeError, UnicodeEncodeError, ValueError):
            logger.exception("Exception trying to verify %s" % self.name)  # @@@ Figure out a better way to handle this

        try:
            package = Package.objects.get(name=self.name)
        except Package.DoesNotExist:
            logger.exception("Error Trying To Verify %s (Querying Package)" % self.name)
            return

        simple_mirror, c = PyPIMirrorPage.objects.get_or_create(package=package, defaults={"content": simple.content})
        if not c and simple_mirror.content != simple.content:
            simple_mirror.content = simple.content
            simple_mirror.save()

        serversig_mirror, c = PyPIServerSigPage.objects.get_or_create(package=package, defaults={"content": serversig.content.encode("base64")})
        serversig_mirror.content = base64.b64encode(serversig.content)
        serversig_mirror.save()

        return {
            "simple": simple.content,
            "serversig": serversig.content,
            "has_sig": True,
        }

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from pypi.simple.views import PackageDetail, PackageServerSig

handler404 = "pypi.simple.views.not_found"

urlpatterns = patterns("",
    url(r"^$", "pypi.simple.views.simple_redirect"),
    url(r"^simple/$", "pypi.simple.views.package_index", name="pypi_package_index"),
    url(r"^simple/(?P<slug>[^/]+)/$", PackageDetail.as_view(), name="pypi_package_detail"),
    url(r"^packages/.+/(?P<filename>[^/]+)$", "pypi.simple.views.file_redirect", name="pypi_file_redirect"),
    url(r"^serversig/(?P<slug>[^/]+)/$", PackageServerSig.as_view(), name="pypi_package_serversig"),
    url(r"^last-modified/?$", "pypi.simple.views.last_modified"),
)

########NEW FILE########
__FILENAME__ = views
import base64
import datetime
import logging
import re

import redis
import requests

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseNotFound, HttpResponsePermanentRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_page
from django.views.generic.detail import DetailView

from packages.models import ReleaseFile
from pypi.models import PyPIMirrorPage, PyPIServerSigPage, PyPIIndexPage

PYPI_SINCE_KEY = "crate:pypi:since"

logger = logging.getLogger(__name__)


def not_found(request):
    return HttpResponseNotFound("Not Found")


class PackageDetail(DetailView):
    queryset = PyPIMirrorPage.objects.all()
    slug_field = "package__name__iexact"

    def get_object(self, queryset=None):
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError(u"Generic detail view %s must be called with "
                                 u"either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            obj = queryset.get()
        except ObjectDoesNotExist:
            try:
                queryset = self.get_queryset()
                queryset = queryset.filter(package__normalized_name=re.sub('[^A-Za-z0-9.]+', '-', slug).lower())
                obj = queryset.get()
            except ObjectDoesNotExist:
                raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})

        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check that the case matches what it's supposed to be
        if self.object.package.name != self.kwargs.get(self.slug_url_kwarg, None):
            return HttpResponsePermanentRedirect(reverse("pypi_package_detail", kwargs={"slug": self.object.package.name}))

        return HttpResponse(self.object.content)


class PackageServerSig(DetailView):
    queryset = PyPIServerSigPage.objects.all()
    slug_field = "package__name__iexact"

    def get_object(self, queryset=None):
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError(u"Generic detail view %s must be called with "
                                 u"either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            obj = queryset.get()
        except ObjectDoesNotExist:
            try:
                queryset = self.get_queryset()
                queryset = queryset.filter(package__normalized_name=re.sub('[^A-Za-z0-9.]+', '-', slug).lower())
                obj = queryset.get()
            except ObjectDoesNotExist:
                raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})

        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Check that the case matches what it's supposed to be
        if self.object.package.name != self.kwargs.get(self.slug_url_kwarg, None):
            return HttpResponsePermanentRedirect(reverse("pypi_package_serversig", kwargs={"slug": self.object.package.name}))

        return HttpResponse(base64.b64decode(self.object.content), mimetype="application/octet-stream")


@cache_page(60 * 15)
def package_index(request, force_uncached=False):
    idx = PyPIIndexPage.objects.all().order_by("-created")[:1]

    if idx and not force_uncached:
        return HttpResponse(idx[0].content)
    else:
        try:
            r = requests.get("http://pypi.python.org/simple/", prefetch=True)
            idx = PyPIIndexPage.objects.create(content=r.content)
            return HttpResponse(idx.content)
        except Exception:
            logger.exception("Error trying to Get New Simple Index")

            idx = PyPIIndexPage.objects.all().order_by("-created")[:1]

            if idx:
                return HttpResponse(idx[0].content)  # Serve Stale Cache
            raise


def last_modified(request):
    datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))
    ts = datastore.get(PYPI_SINCE_KEY)
    if ts is not None:
        dt = datetime.datetime.utcfromtimestamp(int(float(ts)))
        return HttpResponse(dt.isoformat(), mimetype="text/plain")
    else:
        return HttpResponseNotFound("Never Synced")


def file_redirect(request, filename):
    release_file = get_object_or_404(ReleaseFile, filename=filename)
    return HttpResponsePermanentRedirect(release_file.file.url)


def simple_redirect(request):
    return HttpResponsePermanentRedirect(reverse("pypi_package_index"))

########NEW FILE########
__FILENAME__ = tasks
import collections
import datetime
import hashlib
import logging
import re
import socket
import time
import xmlrpclib

import redis
import requests

from celery.task import task

from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from crate.utils.lock import Lock
from packages.models import Package, ReleaseFile, TroveClassifier, DownloadDelta
from pypi.models import PyPIIndexPage, PyPIDownloadChange
from pypi.processor import PyPIPackage

logger = logging.getLogger(__name__)

INDEX_URL = "http://pypi.python.org/pypi"

SERVERKEY_URL = "http://pypi.python.org/serverkey"
SERVERKEY_KEY = "crate:pypi:serverkey"

CLASSIFIER_URL = "http://pypi.python.org/pypi?%3Aaction=list_classifiers"

PYPI_SINCE_KEY = "crate:pypi:since"


def process(name, version, timestamp, action, matches):
    package = PyPIPackage(name, version)
    package.process()


def remove(name, version, timestamp, action, matches):
    package = PyPIPackage(name, version)
    package.delete()


def remove_file(name, version, timestamp, action, matches):
    package = PyPIPackage(name, version)
    package.remove_files(*matches.groups())


@task
def bulk_process(name, version, timestamp, action, matches):
    package = PyPIPackage(name)
    package.process(bulk=True)


@task
def bulk_synchronize():
    pypi = xmlrpclib.ServerProxy(INDEX_URL)

    names = set()

    for package in pypi.list_packages():
        names.add(package)
        bulk_process.delay(package, None, None, None, None)

    for package in Package.objects.exclude(name__in=names):
        package.delete()


@task
def synchronize(since=None):
    with Lock("synchronize", expires=60 * 5, timeout=30):
        datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))

        if since is None:
            s = datastore.get(PYPI_SINCE_KEY)
            if s is not None:
                since = int(float(s)) - 30

        current = time.mktime(datetime.datetime.utcnow().timetuple())

        pypi = xmlrpclib.ServerProxy(INDEX_URL)

        headers = datastore.hgetall(SERVERKEY_KEY + ":headers")
        sig = requests.get(SERVERKEY_URL, headers=headers, prefetch=True)

        if not sig.status_code == 304:
            sig.raise_for_status()

            if sig.content != datastore.get(SERVERKEY_KEY):
                logger.error("Key Rollover Detected")
                pypi_key_rollover.delay()
                datastore.set(SERVERKEY_KEY, sig.content)

        datastore.hmset(SERVERKEY_KEY + ":headers", {"If-Modified-Since": sig.headers["Last-Modified"]})

        if since is None:  # @@@ Should we do this for more than just initial?
            bulk_synchronize.delay()
        else:
            logger.info("[SYNCING] Changes since %s" % since)
            changes = pypi.changelog(since)

            for name, version, timestamp, action in changes:
                line_hash = hashlib.sha256(":".join([str(x) for x in (name, version, timestamp, action)])).hexdigest()
                logdata = {"action": action, "name": name, "version": version, "timestamp": timestamp, "hash": line_hash}

                if not datastore.exists("crate:pypi:changelog:%s" % line_hash):
                    logger.debug("[PROCESS] %(name)s %(version)s %(timestamp)s %(action)s" % logdata)
                    logger.debug("[HASH] %(name)s %(version)s %(hash)s" % logdata)

                    dispatch = collections.OrderedDict([
                        (re.compile("^create$"), process),
                        (re.compile("^new release$"), process),
                        (re.compile("^add [\w\d\.]+ file .+$"), process),
                        (re.compile("^remove$"), remove),
                        (re.compile("^remove file (.+)$"), remove_file),
                        (re.compile("^update [\w]+(, [\w]+)*$"), process),
                        #(re.compile("^docupdate$"), docupdate),  # @@@ Do Something
                        #(re.compile("^add (Owner|Maintainer) .+$"), add_user_role),  # @@@ Do Something
                        #(re.compile("^remove (Owner|Maintainer) .+$"), remove_user_role),  # @@@ Do Something
                    ])

                    # Dispatch Based on the action
                    for pattern, func in dispatch.iteritems():
                        matches = pattern.search(action)
                        if matches is not None:
                            func(name, version, timestamp, action, matches)
                            break
                    else:
                        logger.warn("[UNHANDLED] %(name)s %(version)s %(timestamp)s %(action)s" % logdata)

                    datastore.setex("crate:pypi:changelog:%s" % line_hash, 2629743, datetime.datetime.utcnow().isoformat())
                else:
                    logger.debug("[SKIP] %(name)s %(version)s %(timestamp)s %(action)s" % logdata)
                    logger.debug("[HASH] %(name)s %(version)s %(hash)s" % logdata)

        datastore.set(PYPI_SINCE_KEY, current)


@task
def synchronize_troves():
    resp = requests.get(CLASSIFIER_URL)
    resp.raise_for_status()

    current_troves = set(TroveClassifier.objects.all().values_list("trove", flat=True))
    new_troves = set([x.strip() for x in resp.content.splitlines()]) - current_troves

    with transaction.commit_on_success():
        for classifier in new_troves:
            TroveClassifier.objects.get_or_create(trove=classifier)


@task
def synchronize_downloads():
    for package in Package.objects.all().order_by("downloads_synced_on").prefetch_related("releases", "releases__files")[:150]:
        Package.objects.filter(pk=package.pk).update(downloads_synced_on=now())

        for release in package.releases.all():
            update_download_counts.delay(package.name, release.version, dict([(x.filename, x.pk) for x in release.files.all()]))


@task
def update_download_counts(package_name, version, files, index=None):
    try:
        pypi = xmlrpclib.ServerProxy(INDEX_URL)

        downloads = pypi.release_downloads(package_name, version)

        for filename, download_count in downloads:
            if filename in files:
                with transaction.commit_on_success():
                    for releasefile in ReleaseFile.objects.filter(pk=files[filename]).select_for_update():
                        old = releasefile.downloads
                        releasefile.downloads = download_count
                        releasefile.save()

                        change = releasefile.downloads - old
                        if change:
                            PyPIDownloadChange.objects.create(file=releasefile, change=change)
    except socket.error:
        logger.exception("[DOWNLOAD SYNC] Network Error")


@task
def pypi_key_rollover():
    datastore = redis.StrictRedis(**dict([(x.lower(), y) for x, y in settings.REDIS[settings.PYPI_DATASTORE].items()]))

    sig = requests.get(SERVERKEY_URL, prefetch=True)
    sig.raise_for_status()

    datastore.set(SERVERKEY_KEY, sig.content)

    for package in Package.objects.all():
        fetch_server_key.delay(package.name)


@task
def fetch_server_key(package):
    p = PyPIPackage(package)
    p.verify_and_sync_pages()


@task
def refresh_pypi_package_index_cache():
    r = requests.get("http://pypi.python.org/simple/", prefetch=True)
    PyPIIndexPage.objects.create(content=r.content)


@task
def integrate_download_deltas():
    with Lock("pypi-integrate-downloads", expires=60 * 5, timeout=30):
        count = 0

        for d in PyPIDownloadChange.objects.filter(integrated=False)[:1000]:
            with transaction.commit_on_success():
                dd, c = DownloadDelta.objects.get_or_create(file=d.file, date=d.created.date(), defaults={"delta": d.change})

                if not c:
                    DownloadDelta.objects.filter(pk=dd.pk).select_for_update()

                    dd.delta += d.change
                    dd.save()

                PyPIDownloadChange.objects.filter(pk=d.pk).update(integrated=True)
            count += 1

        return count

########NEW FILE########
__FILENAME__ = serversigs
# Distribute and use freely; there are no restrictions on further
# dissemination and usage except those imposed by the laws of your
# country of residence.  This software is provided "as is" without
# warranty of fitness for use or suitability for any purpose, express
# or implied. Use at your own risk or not at all.

"""Verify a DSA signature, for use with PyPI mirrors.

Verification should use the following steps:
1. Download the DSA key from http://pypi.python.org/serverkey, as key_string
2. key = load_key(key_string)
3. Download the package page, from <mirror>/simple/<package>/, as data
4. Download the package signature, from <mirror>/serversig/<package>, as sig
5. Check verify(key, data, sig)
"""


# DSA signature algorithm, taken from pycrypto 2.0.1
# The license terms are the same as the ones for this module.
def _inverse(u, v):
    """_inverse(u:long, u:long):long
    Return the inverse of u mod v.
    """
    u3, v3 = long(u), long(v)
    u1, v1 = 1L, 0L
    while v3 > 0:
        q = u3 / v3
        u1, v1 = v1, u1 - v1 * q
        u3, v3 = v3, u3 - v3 * q
    while u1 < 0:
        u1 = u1 + v
    return u1


def _verify(key, M, sig):
    p, q, g, y = key
    r, s = sig
    if r <= 0 or r >= q or s <= 0 or s >= q:
        return False
    w = _inverse(s, q)
    u1, u2 = (M * w) % q, (r * w) % q
    v1 = pow(g, u1, p)
    v2 = pow(y, u2, p)
    v = ((v1 * v2) % p)
    v = v % q
    return v == r

# END OF pycrypto


def _bytes2int(b):
    value = 0
    for c in b:
        value = value * 256 + ord(c)
    return value

_SEQUENCE = 0x30  # cons
_INTEGER = 2      # prim
_BITSTRING = 3    # prim
_OID = 6          # prim


def _asn1parse(string):
    #import pdb; pdb.set_trace()
    tag = ord(string[0])
    assert tag & 31 != 31  # only support one-byte tags
    length = ord(string[1])
    assert length != 128  # indefinite length not supported
    pos = 2
    if length > 128:
        # multi-byte length
        val = 0
        length -= 128
        val = _bytes2int(string[pos:pos + length])
        pos += length
        length = val
    data = string[pos:pos + length]
    rest = string[pos + length:]
    assert pos + length <= len(string)
    if tag == _SEQUENCE:
        result = []
        while data:
            value, data = _asn1parse(data)
            result.append(value)
    elif tag == _INTEGER:
        assert ord(data[0]) < 128  # negative numbers not supported
        result = 0
        for c in data:
            result = result * 256 + ord(c)
    elif tag == _BITSTRING:
        result = data
    elif tag == _OID:
        result = data
    else:
        raise ValueError("Unsupported tag %x" % tag)
    return (tag, result), rest


def load_key(string):
    """load_key(string) -> key

    Convert a PEM format public DSA key into
    an internal representation."""
    import base64
    lines = [line.strip() for line in string.splitlines()]
    assert lines[0] == "-----BEGIN PUBLIC KEY-----"
    assert lines[-1] == "-----END PUBLIC KEY-----"
    data = base64.decodestring(''.join(lines[1:-1]))
    spki, rest = _asn1parse(data)
    assert not rest
    # SubjectPublicKeyInfo  ::=  SEQUENCE  {
    #  algorithm            AlgorithmIdentifier,
    #  subjectPublicKey     BIT STRING  }
    assert spki[0] == _SEQUENCE
    algoid, key = spki[1]
    assert key[0] == _BITSTRING
    key = key[1]
    # AlgorithmIdentifier  ::=  SEQUENCE  {
    #  algorithm               OBJECT IDENTIFIER,
    #  parameters              ANY DEFINED BY algorithm OPTIONAL  }
    assert algoid[0] == _SEQUENCE
    algorithm, parameters = algoid[1]
    assert algorithm[0] == _OID and algorithm[1] == '*\x86H\xce8\x04\x01'  # dsaEncryption
    # Dss-Parms  ::=  SEQUENCE  {
    #  p             INTEGER,
    #  q             INTEGER,
    #  g             INTEGER  }
    assert parameters[0] == _SEQUENCE
    p, q, g = parameters[1]
    assert p[0] == q[0] == g[0] == _INTEGER
    p, q, g = p[1], q[1], g[1]
    # Parse bit string value as integer
    assert key[0] == '\0'  # number of bits multiple of 8
    y, rest = _asn1parse(key[1:])
    assert not rest
    assert y[0] == _INTEGER
    y = y[1]
    return p, q, g, y


def verify(key, data, sig):
    """verify(key, data, sig) -> bool

    Verify autenticity of the signature created by key for
    data. data is the bytes that got signed; signature is the
    bytes that represent the signature, using the sha1+DSA
    algorithm. key is an internal representation of the DSA key
    as returned from load_key."""
    import sha
    data = sha.new(data).digest()
    data = _bytes2int(data)
    # Dss-Sig-Value  ::=  SEQUENCE  {
    #      r       INTEGER,
    #      s       INTEGER  }
    sig, rest = _asn1parse(sig)
    assert not rest
    assert sig[0] == _SEQUENCE
    r, s = sig[1]
    assert r[0] == s[0] == _INTEGER
    sig = r[1], s[1]
    return _verify(key, data, sig)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext as _

from haystack.forms import SearchForm as HaystackSearchForm
from haystack.inputs import AutoQuery
from haystack.query import SQ


class SearchForm(HaystackSearchForm):
    has_releases = forms.BooleanField(label=_("Has Releases"), required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

        self.fields["q"].widget.attrs.update({
            "class": "span10",
            "placeholder": _("Search"),
        })

    def search(self):
        if not self.is_valid():
            return self.no_query_found()

        if not self.cleaned_data.get("q"):
            return self.no_query_found()

        sqs = self.searchqueryset.filter(
                SQ(content=AutoQuery(self.cleaned_data["q"])) |
                SQ(name=AutoQuery(self.cleaned_data["q"]))
            )

        if self.cleaned_data.get("has_releases"):
            sqs = sqs.filter(release_count__gt=0)

        if self.load_all:
            sqs = sqs.load_all()

        return sqs

########NEW FILE########
__FILENAME__ = helpers
from jingo import register


@register.function
def facet2short(facet):
    FACETS = {
        "python_versions": "python",
        "operating_systems": "os",
        "licenses": "license",
        "implementations": "implementation",
    }
    return FACETS.get(facet)

########NEW FILE########
__FILENAME__ = indexes
from django.db.models import signals

from celery_haystack.indexes import CelerySearchIndex as BaseCelerySearchIndex

from packages.models import Package, Release, ReleaseFile


class PackageCelerySearchIndex(BaseCelerySearchIndex):

    # We override the built-in _setup_* methods to connect the enqueuing
    # operation.
    def _setup_save(self, model=None):
        model = self.handle_model(model)
        signals.post_save.connect(self.enqueue_save, sender=model)
        signals.post_save.connect(self.enqueue_save_from_release, sender=Release)
        signals.post_save.connect(self.enqueue_save_from_releasefile, sender=ReleaseFile)

    def _setup_delete(self, model=None):
        model = self.handle_model(model)
        signals.post_delete.connect(self.enqueue_delete, sender=model)
        signals.post_delete.connect(self.enqueue_delete_from_release, sender=Release)
        signals.post_delete.connect(self.enqueue_delete_from_releasefile, sender=ReleaseFile)

    def _teardown_save(self, model=None):
        model = self.handle_model(model)
        signals.post_save.disconnect(self.enqueue_save, sender=model)
        signals.post_save.disconnect(self.enqueue_save_from_release, sender=Release)
        signals.post_save.disconnect(self.enqueue_save_from_releasefile, sender=ReleaseFile)

    def _teardown_delete(self, model=None):
        model = self.handle_model(model)
        signals.post_delete.disconnect(self.enqueue_delete, sender=model)
        signals.post_delete.disconnect(self.enqueue_delete_from_release, sender=Release)
        signals.post_delete.disconnect(self.enqueue_delete_from_releasefile, sender=ReleaseFile)

    def enqueue_save_from_release(self, instance, **kwargs):
        return self.enqueue('update', instance.package)

    def enqueue_delete_from_release(self, instance, **kwargs):
        try:
            return self.enqueue('update', instance.package)
        except Package.DoesNotExist:
            pass

    def enqueue_save_from_releasefile(self, instance, **kwargs):
        return self.enqueue('update', instance.release.package)

    def enqueue_delete_from_releasefile(self, instance, **kwargs):
        try:
            return self.enqueue('update', instance.release.package)
        except Release.DoesNotExist:
            pass

########NEW FILE########
__FILENAME__ = models
# Intentionally Left Blank

########NEW FILE########
__FILENAME__ = search_utils
from urllib import urlencode
from urlparse import urlparse, parse_qs, urlunparse

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


def re_qs(url, key, value):
    parsed = urlparse(url)
    data = parse_qs(parsed.query)
    if value is not None:
        data.update({
            key: [value],
        })
    else:
        if key in data:
            del data[key]

    _data = []
    for key, value in data.iteritems():
        for item in value:
            _data.append((key, item))

    return urlunparse([parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(_data), parsed.fragment])


@register.filter(name="repage")
@stringfilter
def repage(value, new_page):
    return re_qs(value, "page", new_page)


@register.filter(name="facet_python")
@stringfilter
def facet_python(value, new=None):
    return re_qs(value, "python", new)


@register.filter(name="facet_os")
@stringfilter
def facet_os(value, new=None):
    return re_qs(value, "os", new)


@register.filter(name="facet_license")
@stringfilter
def facet_license(value, new=None):
    return re_qs(value, "license", new)


@register.filter(name="facet_implementation")
@stringfilter
def facet_implementation(value, new=None):
    return re_qs(value, "implementation", new)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from search.views import Search


urlpatterns = patterns("",
    url(r"^$", Search.as_view(), name="search"),
)

########NEW FILE########
__FILENAME__ = views
import urllib
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.utils.translation import ugettext as _

from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.edit import FormMixin

from saved_searches.models import SavedSearch
from search.forms import SearchForm


class Search(TemplateResponseMixin, FormMixin, View):

    searchqueryset = None
    load_all = False
    paginate_by = None
    allow_empty = True
    form_class = SearchForm
    paginator_class = Paginator
    search_key = 'general_search'

    def get_template_names(self):
        if "q" in self.request.GET:
            return ["search/results.html"]
        return ["homepage.html"]

    def get_searchqueryset(self):
        return self.searchqueryset

    def get_load_all(self):
        return self.load_all

    def get_allow_empty(self):
        """
        Returns ``True`` if the view should display empty lists, and ``False``
        if a 404 should be raised instead.
        """
        return self.allow_empty

    def get_paginate_by(self):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        if self.paginate_by is None:
            return getattr(settings, "HAYSTACK_SEARCH_RESULTS_PER_PAGE", 20)
        return self.paginate_by

    def get_paginator(self, results, per_page, orphans=0, allow_empty_first_page=True):
        """
        Return an instance of the paginator for this view.
        """
        return self.paginator_class(results, per_page, orphans=orphans, allow_empty_first_page=allow_empty_first_page)

    def paginate_results(self, results, page_size):
        """
        Paginate the results, if needed.
        """
        paginator = self.get_paginator(results, page_size, allow_empty_first_page=self.get_allow_empty())
        page = self.kwargs.get("page") or self.request.GET.get("page") or 1
        try:
            page_number = int(page)
        except ValueError:
            if page == "last":
                page_number = paginator.num_pages
            else:
                raise Http404(_(u"Page is not 'last', nor can it be converted to an int."))
        try:
            page = paginator.page(page_number)
            return (paginator, page, page.object_list, page.has_other_pages())
        except InvalidPage:
            raise Http404(_(u"Invalid page (%(page_number)s)") % {
                                "page_number": page_number
            })

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instanciating the form.
        """
        kwargs = {
            "initial": self.get_initial(),
            "searchqueryset": self.get_searchqueryset(),
            "load_all": self.get_load_all(),
        }
        if "q" in self.request.GET:
            kwargs.update({
                "data": self.request.GET,
            })
        return kwargs

    def form_valid(self, form):
        query = form.cleaned_data["q"]
        results = form.search()
        narrow = []

        faceted_by = {
            "python": None,
            "os": None,
            "license": None,
            "implementation": None,
        }

        # Check for facets.
        if self.request.GET.get("python"):
            faceted_by["python"] = self.request.GET["python"]
            narrow.append("python_versions:%s" % self.request.GET["python"])

        if self.request.GET.get("os"):
            faceted_by["os"] = self.request.GET["os"]
            narrow.append("operating_systems:%s" % self.request.GET["os"])

        if self.request.GET.get("license"):
            faceted_by["license"] = self.request.GET["license"]
            narrow.append("licenses:%s" % self.request.GET.get("license"))

        if self.request.GET.get("implementation"):
            faceted_by["implementation"] = self.request.GET["implementation"]
            narrow.append("implementations:%s" % self.request.GET.get("implementation"))

        if len(narrow):
            results = results.narrow(" AND ".join(narrow))

        page_size = self.get_paginate_by()

        if page_size:
            facets = results.facet("python_versions").facet("operating_systems").facet("licenses").facet("implementations").facet_counts()
            paginator, page, results, is_paginated = self.paginate_results(results, page_size)

            # Save it!
            self.save_search(page, query, results)

            # Grumble.
            duped = self.request.GET.copy()
            try:
                del duped["page"]
            except KeyError:
                pass
            query_params = urllib.urlencode(duped, doseq=True)
        else:
            facets = {}
            query_params = ""
            paginator, page, is_paginated = None, None, False

        print faceted_by

        ctx = {
            "form": form,
            "query": query,
            "results": results,
            "page": page,
            "paginator": paginator,
            "is_paginated": is_paginated,
            "facets": facets,
            "faceted_by": faceted_by,
            "query_params": query_params,
        }

        return self.render_to_response(self.get_context_data(**ctx))

    # Copy-pasta from saved_searches with light modification...
    def save_search(self, page, query, results):
        """
        Only save the search if we're on the first page.
        This will prevent an excessive number of duplicates for what is
        essentially the same search.
        """
        if query and page.number == 1:
            # Save the search.
            saved_search = SavedSearch(
                search_key=self.search_key,
                user_query=query,
                result_count=len(results)
            )

            if hasattr(results, 'query'):
                query_seen = results.query.build_query()

                if isinstance(query_seen, basestring):
                    saved_search.full_query = query_seen

            if self.request.user.is_authenticated():
                saved_search.user = self.request.user

            saved_search.save()

    def get(self, request, *args, **kwargs):
        self.request = request

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if "q" in self.request.GET:
            if form.is_valid():
                return self.form_valid(form)
            else:
                self.form_invalid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

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

# django-compressor is turned off by default due to deployment overhead for
# most users. See <URL> for more information
COMPRESS = False

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
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("pt-br", "Portuguese (Brazil)"),
    ("ru", "Russian"),
    ("ko", "Korean"),
    # ("sv", "Swedish"),
)

MEDIA_ROOT = os.path.join(PROJECT_ROOT, "site_media", "media")
MEDIA_URL = "/site_media/media/"


STATIC_ROOT = os.path.join(PROJECT_ROOT, "site_media", "static")
STATIC_URL = "/site_media/static/"

ADMIN_MEDIA_PREFIX = posixpath.join(STATIC_URL, "admin/")

STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, "static"),
]

STATICFILES_FINDERS = [
    "staticfiles.finders.FileSystemFinder",
    "staticfiles.finders.AppDirectoriesFinder",
    "staticfiles.finders.LegacyAppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

COMPRESS_OUTPUT_DIR = "cache"

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
    "timezones",

    # Static Files
    "staticfiles",
    "compressor",

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
    "jhumanize",
    "jmetron",
    "jintercom",

    # project
    "core",
    "about",
    "aws_stats",
    "packages",
    "pypi",
    "search",
    "crate",
    "evaluator",
    "favorites",
    "history",
    "lists",
    "helpdocs",
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
    "core.social_auth.backends.OpenIDBackend",
    "social_auth.backends.contrib.github.GithubBackend",
    "social_auth.backends.contrib.bitbucket.BitbucketBackend",
]

SOCIAL_AUTH_PIPELINE = [
    "social_auth.backends.pipeline.social.social_auth_user",
    "core.social_auth.pipeline.associate.associate_by_email",
    "social_auth.backends.pipeline.user.get_username",
    "core.social_auth.pipeline.user.create_user",
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

ADMIN_TOOLS_INDEX_DASHBOARD = "crate.dashboard.CrateIndexDashboard"

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

SITE_ID = 3

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

SERVER_EMAIL = "server@crate.io"
DEFAULT_FROM_EMAIL = "support@crate.io"

PACKAGE_FILE_STORAGE = "storages.backends.s3boto.S3BotoStorage"
PACKAGE_FILE_STORAGE_OPTIONS = {
    "bucket": "crate-production",
    "custom_domain": "packages.crate-cdn.com",
}

DEFAULT_FILE_STORAGE = "storages.backends.s3boto.S3BotoStorage"
# STATICFILES_STORAGE = "storages.backends.s3boto.S3BotoStorage"

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

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": os.environ["HAYSTACK_DEFAULT_ENGINE"],
        "URL": os.environ["HAYSTACK_DEFAULT_URL"],
        "INDEX_NAME": os.environ["HAYSTACK_DEFAULT_INDEX_NAME"],
    },
}

INTERCOM_USER_HASH_KEY = os.environ["INTERCOM_USER_HASH_KEY"]

GITHUB_APP_ID = os.environ["GITHUB_APP_ID"]
GITHUB_API_SECRET = os.environ["GITHUB_API_SECRET"]

BITBUCKET_CONSUMER_KEY = os.environ["BITBUCKET_CONSUMER_KEY"]
BITBUCKET_CONSUMER_SECRET = os.environ["BITBUCKET_CONSUMER_SECRET"]

########NEW FILE########
__FILENAME__ = gondor
import os
import urlparse

from .base import *

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

if "GONDOR_REDIS_URL" in os.environ:
    urlparse.uses_netloc.append("redis")
    url = urlparse.urlparse(os.environ["GONDOR_REDIS_URL"])

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

MEDIA_ROOT = os.path.join(os.environ["GONDOR_DATA_DIR"], "site_media", "media")
STATIC_ROOT = os.path.join(os.environ["GONDOR_DATA_DIR"], "site_media", "static")

MEDIA_URL = "/site_media/media/"
STATIC_URL = "/site_media/static/"

FILE_UPLOAD_PERMISSIONS = 0640

########NEW FILE########
__FILENAME__ = hosts
from django.conf import settings

from django_hosts import patterns, host

host_patterns = patterns("",
    host(r"www", settings.ROOT_URLCONF, name="default"),
    host(r"simple", "packages.simple.urls", name="simple"),
    host(r"pypi", "pypi.simple.urls", name="pypi"),
    host(r"restricted", "packages.simple.restricted_urls", name="restricted"),
)

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import evaluator
evaluator.autodiscover

import ji18n.translate
ji18n.translate.patch()

from search.views import Search


handler500 = "pinax.views.server_error"


urlpatterns = patterns("",
    url(r"^$", Search.as_view(), name="home"),
    url(r"^admin/", include(admin.site.urls)),
    url(r"^about/", include("about.urls")),
    url(r"^account/", include("account.urls")),
    url(r"^account/", include("core.social_auth.urls")),
    url(r"^admin_tools/", include("admin_tools.urls")),
    url(
        r"^social-auth/disconnect/(?P<backend>[^/]+)/(?P<association_id>[^/]+)/$",
        "core.social_auth.views.disconnect",
    ),
    url(r"^social-auth/", include("social_auth.urls")),

    url(r"^users/", include("lists.urls")),

    url(r"^packages/", include("packages.urls")),

    url(r"^stats/", include("packages.stats.urls")),
    url(r"^help/", include("helpdocs.urls")),
    url(r"^api/", include("crateweb.api_urls")),

    url(r"^s/(?P<path>.+)?", "crate.views.simple_redirect", name="simple_redirect"),

    url(r"^", include("search.urls")),
)


if settings.SERVE_MEDIA:
    urlpatterns += patterns("",
        url(r"", include("staticfiles.urls")),
    )

########NEW FILE########
__FILENAME__ = wsgi
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "apps")))

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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "crateweb", "apps")))

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
