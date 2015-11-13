__FILENAME__ = backends
from django.contrib.auth.backends import ModelBackend

from ratelimitbackend.backends import RateLimitMixin

from .profiles.models import User
from .utils import is_email


class CaseInsensitiveModelBackend(ModelBackend):
    def authenticate(self, username, password):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            return None
        else:
            if user.check_password(password):
                return user


class RateLimitMultiBackend(RateLimitMixin, CaseInsensitiveModelBackend):
    """A backend that allows login via username or email, rate-limited."""
    def authenticate(self, username=None, password=None, request=None):
        if is_email(username):
            try:
                username = User.objects.get(email__iexact=username).username
            except User.DoesNotExist:
                pass
        return super(RateLimitMultiBackend, self).authenticate(
            username=username,
            password=password,
            request=request,
        )

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME

from ratelimitbackend.views import login

from .profiles.forms import AuthForm


def login_required(view_callable):
    def check_login(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_callable(request, *args, **kwargs)

        assert hasattr(request, 'session'), "Session middleware needed."
        login_kwargs = {
            'extra_context': {
                REDIRECT_FIELD_NAME: request.get_full_path(),
                'from_decorator': True,
            },
            'authentication_form': AuthForm,
        }
        return login(request, **login_kwargs)
    return wraps(view_callable)(check_login)

########NEW FILE########
__FILENAME__ = admin
import json
import math

from django.conf.urls import url, patterns
from django.contrib.admin import widgets
from django.http import HttpResponse
from rache import scheduled_jobs
from ratelimitbackend import admin

from .fields import URLField
from .models import Category, UniqueFeed, Feed, Entry, Favicon
from ..utils import get_redis_connection


class URLOverrideMixin(object):
    formfield_overrides = {
        URLField: {'widget': widgets.AdminURLFieldWidget},
    }


class TabularInline(URLOverrideMixin, admin.TabularInline):
    pass


class ModelAdmin(URLOverrideMixin, admin.ModelAdmin):
    pass


class FeedInline(TabularInline):
    model = Feed
    raw_id_fields = ('user',)


class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {
            'fields': (('name', 'slug'), 'user', 'order'),
        }),
    )
    inlines = [FeedInline]
    raw_id_fields = ('user',)


class UniqueFeedAdmin(ModelAdmin):
    list_display = ('truncated_url', 'last_update', 'muted', 'error')
    list_filter = ('muted', 'error')
    search_fields = ('url',)

    class Media:
        js = (
            'feeds/js/d3.v3.min.js',
            'feeds/js/graph-scheduler.js',
        )

    def get_urls(self):
        return patterns(
            '',
            url(r'^graph/$', self.admin_site.admin_view(self.graph_data),
                name='graph-data'),
        ) + super(UniqueFeedAdmin, self).get_urls()

    def graph_data(self, request):
        jobs = list(scheduled_jobs(with_times=True,
                                   connection=get_redis_connection()))

        timespan = jobs[-1][1] - jobs[0][1]
        interval = math.ceil(timespan / 500)
        start = jobs[0][1]
        counts = [0]
        for _url, time in jobs:
            while len(counts) * interval < time - start:
                counts.append(0)
            counts[-1] += 1

        return HttpResponse(json.dumps({'max': max(counts),
                                        'counts': counts,
                                        'timespan': timespan}))


class FeedAdmin(ModelAdmin):
    list_display = ('name', 'category', 'unread_count', 'favicon_img')
    search_fields = ('name', 'url')
    raw_id_fields = ('category', 'user')


class EntryAdmin(ModelAdmin):
    list_display = ('title', 'date')
    search_fields = ('title', 'link')
    raw_id_fields = ('feed', 'user')


class FaviconAdmin(ModelAdmin):
    list_display = ('url', 'favicon_img')
    search_fields = ('url',)


admin.site.register(Category, CategoryAdmin)
admin.site.register(UniqueFeed, UniqueFeedAdmin)
admin.site.register(Feed, FeedAdmin)
admin.site.register(Entry, EntryAdmin)
admin.site.register(Favicon, FaviconAdmin)

########NEW FILE########
__FILENAME__ = fields
from django import forms
from django.db import models
from django.utils.translation import ugettext_lazy as _
from south.modelsinspector import add_introspection_rules


class URLField(models.TextField):
    description = _("URL")

    def formfield(self, **kwargs):
        defaults = {
            'form_class': forms.URLField,
            'widget': forms.TextInput,
        }
        defaults.update(kwargs)
        return super(URLField, self).formfield(**defaults)

add_introspection_rules([], ["^feedhq\.feeds\.fields\.URLField"])

########NEW FILE########
__FILENAME__ = forms
import contextlib
import json

from django.core.cache import cache
from django.forms.formsets import formset_factory
from django.utils.translation import ugettext_lazy as _
from lxml.etree import XMLSyntaxError
from six.moves.urllib import parse as urlparse

import feedparser
import floppyforms as forms
import opml
import requests

from .models import Category, Feed
from .utils import USER_AGENT, is_feed
from ..utils import get_redis_connection


@contextlib.contextmanager
def user_lock(cache_key, user_id, timeout=None):
    key = "lock:{0}:{1}".format(cache_key, user_id)

    redis = get_redis_connection()
    got_lock = redis.setnx(key, user_id)
    if timeout is not None and got_lock:
        redis.setex(key, timeout, user_id)
    if not got_lock:
        raise forms.ValidationError(
            _("This action can only be done one at a time."))
    try:
        yield
    finally:
        if got_lock:
            redis.delete(key)


class ColorWidget(forms.Select):
    template_name = 'forms/color_select.html'


class UserFormMixin(object):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(UserFormMixin, self).__init__(*args, **kwargs)


class CategoryForm(UserFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'color']
        widgets = {
            'color': ColorWidget,
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        existing = self.user.categories.filter(name=name)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError(
                _("A category with this name already exists."))
        return name

    def save(self, commit=True):
        category = super(CategoryForm, self).save(commit=False)
        category.user = self.user
        if commit:
            category.save(update_slug=True)
        return category


class FeedForm(UserFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FeedForm, self).__init__(*args, **kwargs)
        self.fields['category'].queryset = self.user.categories.all()

    class Meta:
        model = Feed
        fields = ('name', 'url', 'category')

    def clean_url(self):
        url = self.cleaned_data['url']
        parsed = urlparse.urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            raise forms.ValidationError(
                _("Invalid URL scheme: '%s'. Only HTTP and HTTPS are "
                  "supported.") % parsed.scheme)

        netloc = parsed.netloc.split(':')[0]
        if netloc in ['localhost', '127.0.0.1', '::1']:
            raise forms.ValidationError(_("Invalid URL."))

        existing = self.user.feeds.filter(url=url)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError(
                _("It seems you're already subscribed to this feed."))

        # Check this is actually a feed
        with user_lock("feed_check", self.user.pk, timeout=30):
            headers = {
                'User-Agent': USER_AGENT % 'checking feed',
                'Accept': feedparser.ACCEPT_HEADER,
            }
            try:
                response = requests.get(url, headers=headers, timeout=10)
            except Exception:
                raise forms.ValidationError(_("Error fetching the feed."))
            if response.status_code != 200:
                raise forms.ValidationError(_(
                    "Invalid response code from URL: "
                    "HTTP %s.") % response.status_code)
        try:
            parsed = feedparser.parse(response.content)
        except Exception:
            raise forms.ValidationError(_("Error parsing the feed."))
        if not is_feed(parsed):
            raise forms.ValidationError(
                _("This URL doesn't seem to be a valid feed."))
        self.cleaned_data['title'] = parsed.feed.title
        # Cache this in case update_favicon needs it and it's not in the
        # scheduler data yet.
        if hasattr(parsed.feed, 'link'):
            cache.set(u'feed_link:{0}'.format(url), parsed.feed.link, 600)
        return url

    def save(self, commit=True):
        feed = super(FeedForm, self).save(commit=False)
        feed.user = self.user
        if commit:
            feed.save()
        return feed


class OPMLField(forms.FileField):
    def to_python(self, data):
        f = super(OPMLField, self).to_python(data)
        if f is None:
            return

        if hasattr(data, 'read'):
            content = data.read()
        else:
            content = data['content']
        try:
            opml.from_string(content)
        except XMLSyntaxError:
            raise forms.ValidationError(
                _("This file doesn't seem to be a valid OPML file."))

        if hasattr(f, 'seek') and callable(f.seek):
            f.seek(0)
        return f


class OPMLImportForm(forms.Form):
    file = OPMLField()


class ActionForm(forms.Form):
    action = forms.ChoiceField(choices=(
        ('images', 'images'),
        ('unread', 'unread'),
        ('read_later', 'read_later'),
        ('star', 'star'),
        ('unstar', 'unstar'),
    ))


class ReadForm(forms.Form):
    READ_ALL = 'read-all'
    READ_PAGE = 'read-page'

    action = forms.ChoiceField(
        choices=(
            (READ_ALL, 'read all'),
            (READ_PAGE, 'read page'),
        ),
        widget=forms.HiddenInput,
        initial='read-all',
    )

    def __init__(self, entries=None, feed=None, category=None, user=None,
                 pages_only=False, *args, **kwargs):
        if entries is not None:
            entries = entries.filter(read=False)
        self.entries = entries
        self.feed = feed
        self.category = category
        self.user = user
        self.pages_only = pages_only
        super(ReadForm, self).__init__(*args, **kwargs)
        if self.pages_only:
            self.fields['entries'] = forms.CharField(widget=forms.HiddenInput)

    def clean_entries(self):
        return json.loads(self.cleaned_data['entries'])

    def save(self):
        if self.pages_only:
            # pages is a list of IDs to mark as read
            entries = self.user.entries.filter(
                pk__in=self.cleaned_data['entries'])
        else:
            entries = self.entries
        pks = list(entries.values_list('pk', flat=True))
        entries.update(read=True)
        if self.feed is not None:
            feeds = Feed.objects.filter(pk=self.feed.pk)
        elif self.category is not None:
            feeds = self.category.feeds.all()
        else:
            feeds = self.user.feeds.all()

        if self.pages_only:
            # TODO combine code with mark-all-as-read?
            for feed in feeds:
                Feed.objects.filter(pk=feed.pk).update(
                    unread_count=feed.entries.filter(read=False).count())
        else:
            feeds.update(unread_count=0)
        return pks


class UndoReadForm(forms.Form):
    action = forms.ChoiceField(
        choices=(
            ('undo-read', 'undo-read'),
        ),
        widget=forms.HiddenInput,
        initial='undo-read',
    )
    pks = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(UndoReadForm, self).__init__(*args, **kwargs)

    def clean_pks(self):
        return json.loads(self.cleaned_data['pks'])

    def save(self):
        self.user.entries.filter(pk__in=self.cleaned_data['pks']).update(
            read=False)
        return len(self.cleaned_data['pks'])


class SubscriptionForm(forms.Form):
    subscribe = forms.BooleanField(label=_('Subscribe?'), required=False)
    name = forms.CharField(label=_('Name'), required=False)
    url = forms.URLField(label=_('URL'))
    category = forms.ChoiceField(label=_('Category'), required=False)

    def clean_url(self):
        url = self.cleaned_data['url']
        if (
            self.cleaned_data.get('subscribe', False) and
            self.user.feeds.filter(url=url).exists()
        ):
            raise forms.ValidationError(
                _("You are already subscribed to this feed."))
        return url

    def clean_name(self):
        if (
            self.cleaned_data.get('subscribe', False) and
            not self.cleaned_data['name']
        ):
            raise forms.ValidationError(_('This field is required.'))
        return self.cleaned_data['name']

SubscriptionFormSet = formset_factory(SubscriptionForm, extra=0)

########NEW FILE########
__FILENAME__ = add_missing
from django.conf import settings

from ...models import Feed, UniqueFeed, enqueue_favicon
from . import SentryCommand


class Command(SentryCommand):
    """Updates the users' feeds"""

    def handle_sentry(self, *args, **kwargs):
        missing = Feed.objects.raw(
            """
            select f.id, f.url
            from
                feeds_feed f
                left join auth_user u on f.user_id = u.id
            where
                not exists (
                    select 1 from feeds_uniquefeed u where f.url = u.url
                ) and
                u.is_suspended = false
            """)
        urls = set([f.url for f in missing])
        UniqueFeed.objects.bulk_create([
            UniqueFeed(url=url) for url in urls
        ])

        if not settings.TESTS:
            missing_favicons = UniqueFeed.objects.raw(
                """
                select id, url from feeds_uniquefeed u
                where
                    u.url != '' and
                    not exists (
                        select 1 from feeds_favicon f
                        where f.url = u.url
                    )
                """)
            for feed in missing_favicons:
                enqueue_favicon(feed.url)

########NEW FILE########
__FILENAME__ = clean_rq
import datetime
import logging
import pytz

from dateutil import parser
from itertools import product

from . import SentryCommand
from ....utils import get_redis_connection

logger = logging.getLogger(__name__)


class Command(SentryCommand):
    def handle_sentry(self, **options):
        r = get_redis_connection()
        prefix = 'rq:job:'
        keys = (
            "".join(chars) for chars in product('0123456789abcdef', repeat=1)
        )
        delay = (
            datetime.datetime.utcnow().replace(tzinfo=pytz.utc) -
            datetime.timedelta(days=5)
        )
        count = 0
        for start in keys:
            prefix_keys = r.keys('{0}{1}*'.format(prefix, start))
            for key in prefix_keys:
                date = r.hget(key, 'created_at')
                if date is None:
                    continue
                date = parser.parse(date)
                if date < delay:
                    r.delete(key)
                    count += 1
        logger.info("Cleaned {0} jobs".format(count))

########NEW FILE########
__FILENAME__ = delete_old
from datetime import timedelta

from django.utils import timezone

from . import SentryCommand
from ....profiles.models import User


class Command(SentryCommand):
    def handle_sentry(self, **options):
        users = User.objects.filter(ttl__isnull=False)
        for user in users:
            limit = timezone.now() - timedelta(days=user.ttl)
            user.entries.filter(date__lte=limit).delete()

########NEW FILE########
__FILENAME__ = delete_unsubscribed
from ...models import UniqueFeed
from . import SentryCommand


class Command(SentryCommand):
    """Updates the users' feeds"""

    def handle_sentry(self, *args, **kwargs):
        unsubscribed = UniqueFeed.objects.raw(
            """
            select u.id from feeds_uniquefeed u where not exists (
                select 1
                from
                    feeds_feed f
                    left join auth_user a on f.user_id = a.id
                where
                    f.url = u.url and
                    a.is_suspended = false
            )
            """)
        pks = [u.pk for u in unsubscribed]
        UniqueFeed.objects.filter(pk__in=pks).delete()

########NEW FILE########
__FILENAME__ = favicons
from optparse import make_option

from ...models import UniqueFeed, enqueue_favicon
from . import SentryCommand


class Command(SentryCommand):
    """Fetches favicon updates and saves them if there are any"""
    option_list = SentryCommand.option_list + (
        make_option(
            '--all',
            action='store_true',
            dest='all',
            default=False,
            help='Force update of all existing favicons',
        ),
    )

    def handle_sentry(self, *args, **kwargs):
        urls = UniqueFeed.objects.filter(muted=False).values_list(
            'url', flat=True).distinct()
        for url in urls:
            enqueue_favicon(url, force_update=kwargs['all'])

########NEW FILE########
__FILENAME__ = rqworker
from optparse import make_option
import os

from raven import Client
from rq import Queue, Connection, Worker

from . import SentryCommand
from ....utils import get_redis_connection


def sentry_handler(job, *exc_info):
    if 'SENTRY_DSN' not in os.environ:
        # Use the next exception handler (send to failed queue)
        return True
    client = Client()
    client.captureException(
        exc_info=exc_info,
        extra={
            'job_id': job.id,
            'func': job.func,
            'args': job.args,
            'kwargs': job.kwargs,
            'description': job.description,
        },
    )
    return False


class Command(SentryCommand):
    args = '<queue1 queue2 ...>'
    option_list = SentryCommand.option_list + (
        make_option('--burst', action='store_true', dest='burst',
                    default=False, help='Run the worker in burst mode'),
    )
    help = "Run a RQ worker on selected queues."

    def handle_sentry(self, *args, **options):
        conn = get_redis_connection()
        with Connection(conn):
            queues = map(Queue, args)
            worker = Worker(queues, exc_handler=sentry_handler)
            worker.work(burst=options['burst'])

########NEW FILE########
__FILENAME__ = sync_pubsubhubbub
import logging
import os

from django.conf import settings
from django_push.subscriber.models import Subscription
from raven import Client

from . import SentryCommand

logger = logging.getLogger(__name__)


class Command(SentryCommand):
    """Updates PubSubHubbub subscriptions"""

    def handle_sentry(self, *args, **kwargs):
        extra = list(Subscription.objects.raw(
            """
            select * from subscriber_subscription s where not exists (
                select 1 from feeds_uniquefeed u
                where u.url = s.topic
            ) and s.lease_expiration >= current_timestamp
            """))
        if len(extra):
            logger.info("Unsubscribing from {0} feeds".format(len(extra)))
            for subscription in extra:
                try:
                    subscription.unsubscribe()
                except Exception:
                    if settings.DEBUG or 'SENTRY_DSN' not in os.environ:
                        raise
                    client = Client()
                    client.captureException()

########NEW FILE########
__FILENAME__ = sync_scheduler
import logging

from more_itertools import chunked
from rache import scheduled_jobs, delete_job

from . import SentryCommand
from ...models import UniqueFeed
from ....utils import get_redis_connection

logger = logging.getLogger(__name__)


class Command(SentryCommand):
    """Syncs the UniqueFeeds and the scheduler:

        - removes scheduled feeds which are missing from uniquefeeds
        - adds missing uniquefeeds to the scheduler
    """

    def handle_sentry(self, *args, **kwargs):
        connection = get_redis_connection()
        existing_jobs = set(scheduled_jobs(connection=connection))
        target = set(UniqueFeed.objects.filter(muted=False).values_list(
            'url', flat=True))

        to_delete = existing_jobs - target
        if to_delete:
            logger.info(
                "Deleting {0} jobs from the scheduler".format(len(to_delete)))
            for job_id in to_delete:
                delete_job(job_id, connection=connection)

        to_add = target - existing_jobs
        if to_add:
            logger.info("Adding {0} jobs to the scheduler".format(len(to_add)))
            for chunk in chunked(to_add, 10000):
                uniques = UniqueFeed.objects.filter(url__in=chunk)
                for unique in uniques:
                    unique.schedule()

########NEW FILE########
__FILENAME__ = updatefeeds
import logging

from rache import pending_jobs
from rq import Queue

from ....tasks import enqueue
from ....utils import get_redis_connection
from ...models import UniqueFeed
from ...tasks import update_feed
from . import SentryCommand

logger = logging.getLogger(__name__)


class Command(SentryCommand):
    """Updates the users' feeds"""

    def handle_sentry(self, *args, **kwargs):
        if args:
            pk = args[0]
            feed = UniqueFeed.objects.get(pk=pk)
            data = feed.job_details
            return update_feed(
                feed.url, etag=data.get('etag'), modified=data.get('modified'),
                subscribers=data['subscribers'],
                backoff_factor=data['backoff_factor'], error=data.get('error'),
                link=data.get('link'), title=data.get('title'),
                hub=data.get('hub'),
            )

        ratio = UniqueFeed.UPDATE_PERIOD // 5
        limit = max(
            1, UniqueFeed.objects.filter(muted=False).count() // ratio) * 2

        # Avoid queueing if the default or store queue is already full
        conn = get_redis_connection()
        for name in ['default', 'store']:
            queue = Queue(name=name, connection=conn)
            if queue.count > limit:
                logger.info(
                    "{0} queue longer than limit, skipping update "
                    "({1} > {2})".format(name, queue.count, limit))
                return

        jobs = pending_jobs(limit=limit,
                            reschedule_in=UniqueFeed.UPDATE_PERIOD * 60,
                            connection=get_redis_connection())
        for job in jobs:
            url = job.pop('id')
            job.pop('last_update', None)
            enqueue(update_feed, args=[url], kwargs=job,
                    timeout=UniqueFeed.TIMEOUT_BASE * job.get(
                        'backoff_factor', 1))

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Category'
        db.create_table(u'feeds_category', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=1023)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='categories', to=orm['auth.User'])),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('color', self.gf('django.db.models.fields.CharField')(default='dark-orange', max_length=50)),
        ))
        db.send_create_signal(u'feeds', ['Category'])

        # Adding model 'UniqueFeed'
        db.create_table(u'feeds_uniquefeed', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=1023)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=2048, blank=True)),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=2048, blank=True)),
            ('etag', self.gf('django.db.models.fields.CharField')(max_length=1023, null=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.CharField')(max_length=1023, null=True, blank=True)),
            ('last_update', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('muted', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('error', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, db_column='muted_reason', blank=True)),
            ('hub', self.gf('django.db.models.fields.URLField')(max_length=1023, null=True, blank=True)),
            ('backoff_factor', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('last_loop', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('subscribers', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True)),
        ))
        db.send_create_signal(u'feeds', ['UniqueFeed'])

        # Adding model 'Feed'
        db.create_table(u'feeds_feed', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=1023)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(related_name='feeds', to=orm['feeds.Category'])),
            ('unread_count', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('favicon', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True)),
            ('img_safe', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'feeds', ['Feed'])

        # Adding model 'Entry'
        db.create_table(u'feeds_entry', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('feed', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entries', to=orm['feeds.Feed'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('subtitle', self.gf('django.db.models.fields.TextField')()),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=1023)),
            ('permalink', self.gf('django.db.models.fields.URLField')(max_length=1023, blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entries', to=orm['auth.User'])),
            ('read', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('read_later_url', self.gf('django.db.models.fields.URLField')(max_length=1023, blank=True)),
            ('starred', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('broadcast', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
        ))
        db.send_create_signal(u'feeds', ['Entry'])

        # Adding model 'Favicon'
        db.create_table(u'feeds_favicon', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=2048, db_index=True)),
            ('favicon', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
        ))
        db.send_create_signal(u'feeds', ['Favicon'])


    def backwards(self, orm):
        # Deleting model 'Category'
        db.delete_table(u'feeds_category')

        # Deleting model 'UniqueFeed'
        db.delete_table(u'feeds_uniquefeed')

        # Deleting model 'Feed'
        db.delete_table(u'feeds_feed')

        # Deleting model 'Entry'
        db.delete_table(u'feeds_entry')

        # Deleting model 'Favicon'
        db.delete_table(u'feeds_favicon')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'red'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'permalink': ('django.db.models.fields.URLField', [], {'max_length': '1023', 'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('django.db.models.fields.URLField', [], {'max_length': '1023', 'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2048', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '1023'})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('django.db.models.fields.URLField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '2048', 'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '1023'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0002_url_text
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Feed.url'
        db.alter_column(u'feeds_feed', 'url', self.gf('feedhq.feeds.fields.URLField')())

        # Changing field 'Favicon.url'
        db.alter_column(u'feeds_favicon', 'url', self.gf('feedhq.feeds.fields.URLField')(unique=True))

        # Changing field 'Entry.permalink'
        db.alter_column(u'feeds_entry', 'permalink', self.gf('feedhq.feeds.fields.URLField')())

        # Changing field 'Entry.link'
        db.alter_column(u'feeds_entry', 'link', self.gf('feedhq.feeds.fields.URLField')())

        # Changing field 'Entry.read_later_url'
        db.alter_column(u'feeds_entry', 'read_later_url', self.gf('feedhq.feeds.fields.URLField')())

        # Changing field 'UniqueFeed.hub'
        db.alter_column(u'feeds_uniquefeed', 'hub', self.gf('feedhq.feeds.fields.URLField')(null=True))

        # Changing field 'UniqueFeed.url'
        db.alter_column(u'feeds_uniquefeed', 'url', self.gf('feedhq.feeds.fields.URLField')(unique=True))

        # Changing field 'UniqueFeed.link'
        db.alter_column(u'feeds_uniquefeed', 'link', self.gf('feedhq.feeds.fields.URLField')())

    def backwards(self, orm):

        # Changing field 'Feed.url'
        db.alter_column(u'feeds_feed', 'url', self.gf('django.db.models.fields.URLField')(max_length=1023))

        # Changing field 'Favicon.url'
        db.alter_column(u'feeds_favicon', 'url', self.gf('django.db.models.fields.URLField')(max_length=2048, unique=True))

        # Changing field 'Entry.permalink'
        db.alter_column(u'feeds_entry', 'permalink', self.gf('django.db.models.fields.URLField')(max_length=1023))

        # Changing field 'Entry.link'
        db.alter_column(u'feeds_entry', 'link', self.gf('django.db.models.fields.URLField')(max_length=1023))

        # Changing field 'Entry.read_later_url'
        db.alter_column(u'feeds_entry', 'read_later_url', self.gf('django.db.models.fields.URLField')(max_length=1023))

        # Changing field 'UniqueFeed.hub'
        db.alter_column(u'feeds_uniquefeed', 'hub', self.gf('django.db.models.fields.URLField')(max_length=1023, null=True))

        # Changing field 'UniqueFeed.url'
        db.alter_column(u'feeds_uniquefeed', 'url', self.gf('django.db.models.fields.URLField')(max_length=1023, unique=True))

        # Changing field 'UniqueFeed.link'
        db.alter_column(u'feeds_uniquefeed', 'link', self.gf('django.db.models.fields.URLField')(max_length=2048))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'pale-green'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {}),
            'permalink': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0003_auto__add_unique_category_user_slug__add_unique_category_user_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'Category', fields ['user', 'slug']
        db.create_unique(u'feeds_category', ['user_id', 'slug'])

        # Adding unique constraint on 'Category', fields ['user', 'name']
        db.create_unique(u'feeds_category', ['user_id', 'name'])


    def backwards(self, orm):
        # Removing unique constraint on 'Category', fields ['user', 'name']
        db.delete_unique(u'feeds_category', ['user_id', 'name'])

        # Removing unique constraint on 'Category', fields ['user', 'slug']
        db.delete_unique(u'feeds_category', ['user_id', 'slug'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'blue'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {}),
            'permalink': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0004_auto
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Category', fields ['name']
        db.create_index(u'feeds_category', ['name'])


    def backwards(self, orm):
        # Removing index on 'Category', fields ['name']
        db.delete_index(u'feeds_category', ['name'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'gray'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {}),
            'permalink': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_feed_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Feed.user'
        db.add_column(u'feeds_feed', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Feed.user'
        db.delete_column(u'feeds_feed', 'user_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'dark-red'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {}),
            'permalink': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0006_populate_feed_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for category in orm['feeds.Category'].objects.all():
            category.feeds.update(user=category.user)

    def backwards(self, orm):
        "Write your backwards methods here."

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'red'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {}),
            'permalink': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_feed_category__chg_field_feed_user__chg_field_entry_fe
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Feed.category'
        db.alter_column(u'feeds_feed', 'category_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['feeds.Category']))

        # Changing field 'Feed.user'
        db.alter_column(u'feeds_feed', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['auth.User']))

        # Changing field 'Entry.feed'
        db.alter_column(u'feeds_entry', 'feed_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['feeds.Feed']))

    def backwards(self, orm):

        # Changing field 'Feed.category'
        db.alter_column(u'feeds_feed', 'category_id', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['feeds.Category']))

        # Changing field 'Feed.user'
        db.alter_column(u'feeds_feed', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True))

        # Changing field 'Entry.feed'
        db.alter_column(u'feeds_entry', 'feed_id', self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['feeds.Feed']))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'dark-red'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {}),
            'permalink': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0008_auto__add_field_entry_author
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Entry.author'
        db.add_column(u'feeds_entry', 'author',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=1023, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Entry.author'
        db.delete_column(u'feeds_entry', 'author')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'blue'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {}),
            'permalink': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['auth.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0009_auto__del_field_entry_permalink
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Entry.permalink'
        db.delete_column(u'feeds_entry', 'permalink')


    def backwards(self, orm):
        # Adding field 'Entry.permalink'
        db.add_column(u'feeds_entry', 'permalink',
                      self.gf('feedhq.feeds.fields.URLField')(default='', blank=True),
                      keep_default=False)


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'army-green'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', 'title')", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['auth.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0010_auto__add_field_entry_guid
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Entry.guid'
        db.add_column(u'feeds_entry', 'guid',
                      self.gf('feedhq.feeds.fields.URLField')(db_index=True, null=True, blank=True),
                      keep_default=False)

        # Adding index on 'Entry', fields ['link']
        db.create_index(u'feeds_entry', ['link'])


    def backwards(self, orm):
        # Removing index on 'Entry', fields ['link']
        db.delete_index(u'feeds_entry', ['link'])

        # Deleting field 'Entry.guid'
        db.delete_column(u'feeds_entry', 'guid')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'orange'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', '-id')", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            'guid': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['auth.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0011_populate_guid
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        orm['feeds.Entry'].objects.update(guid='')

    def backwards(self, orm):
        "Write your backwards methods here."

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'pale-green'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', '-id')", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            'guid': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True', 'blank': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['auth.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0012_auto__chg_field_entry_guid
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Entry.guid'
        db.alter_column(u'feeds_entry', 'guid', self.gf('feedhq.feeds.fields.URLField')(default=''))

    def backwards(self, orm):

        # Changing field 'Entry.guid'
        db.alter_column(u'feeds_entry', 'guid', self.gf('feedhq.feeds.fields.URLField')(null=True))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'red'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', '-id')", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            'guid': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['auth.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0013_auto__chg_field_feed_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Feed.name'
        db.alter_column(u'feeds_feed', 'name', self.gf('django.db.models.fields.CharField')(max_length=1023))

    def backwards(self, orm):

        # Changing field 'Feed.name'
        db.alter_column(u'feeds_feed', 'name', self.gf('django.db.models.fields.CharField')(max_length=255))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'black'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['auth.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', '-id')", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            'guid': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['auth.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['auth.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['feeds']
########NEW FILE########
__FILENAME__ = 0014_auto__chg_field_feed_user__chg_field_entry_user__add_index_entry_date_
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Entry', fields ['date', 'user']
        db.create_index(u'feeds_entry', ['date', 'user_id'])

        # Adding index on 'Entry', fields ['read', 'user']
        db.create_index(u'feeds_entry', ['read', 'user_id'])

        # Adding index on 'Entry', fields ['starred', 'user']
        db.create_index(u'feeds_entry', ['starred', 'user_id'])

        # Adding index on 'Entry', fields ['broadcast', 'user']
        db.create_index(u'feeds_entry', ['broadcast', 'user_id'])


    def backwards(self, orm):
        # Removing index on 'Entry', fields ['broadcast', 'user']
        db.delete_index(u'feeds_entry', ['broadcast', 'user_id'])

        # Removing index on 'Entry', fields ['starred', 'user']
        db.delete_index(u'feeds_entry', ['starred', 'user_id'])

        # Removing index on 'Entry', fields ['read', 'user']
        db.delete_index(u'feeds_entry', ['read', 'user_id'])

        # Removing index on 'Entry', fields ['date', 'user']
        db.delete_index(u'feeds_entry', ['date', 'user_id'])

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'orange'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', '-id')", 'object_name': 'Entry', 'index_together': "(('user', 'date'), ('user', 'read'), ('user', 'starred'), ('user', 'broadcast'))"},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            'guid': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'backoff_factor': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'hub': ('feedhq.feeds.fields.URLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_loop': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'last_update': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'modified': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'null': 'True', 'blank': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subscribers': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2048', 'blank': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['feeds']

########NEW FILE########
__FILENAME__ = 0015_auto__del_field_uniquefeed_hub__del_field_uniquefeed_last_loop__del_fi
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from feedhq.utils import get_redis_connection
from rache import REDIS_KEY, job_key


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'UniqueFeed.hub'
        db.delete_column(u'feeds_uniquefeed', 'hub')

        # Deleting field 'UniqueFeed.last_loop'
        db.delete_column(u'feeds_uniquefeed', 'last_loop')

        # Deleting field 'UniqueFeed.backoff_factor'
        db.delete_column(u'feeds_uniquefeed', 'backoff_factor')

        # Deleting field 'UniqueFeed.link'
        db.delete_column(u'feeds_uniquefeed', 'link')

        # Deleting field 'UniqueFeed.etag'
        db.delete_column(u'feeds_uniquefeed', 'etag')

        # Deleting field 'UniqueFeed.subscribers'
        db.delete_column(u'feeds_uniquefeed', 'subscribers')

        # Deleting field 'UniqueFeed.title'
        db.delete_column(u'feeds_uniquefeed', 'title')

        # Deleting field 'UniqueFeed.modified'
        db.delete_column(u'feeds_uniquefeed', 'modified')

        # Deleting field 'UniqueFeed.last_update'
        db.delete_column(u'feeds_uniquefeed', 'last_update')

        redis = get_redis_connection()
        jobs = redis.zrange(REDIS_KEY, 0, -1)
        for job in jobs:
            redis.hdel(job_key(job.decode('utf-8')), 'request_timeout')


    def backwards(self, orm):
        # Adding field 'UniqueFeed.hub'
        db.add_column(u'feeds_uniquefeed', 'hub',
                      self.gf('feedhq.feeds.fields.URLField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'UniqueFeed.last_loop'
        db.add_column(u'feeds_uniquefeed', 'last_loop',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True),
                      keep_default=False)

        # Adding field 'UniqueFeed.backoff_factor'
        db.add_column(u'feeds_uniquefeed', 'backoff_factor',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1),
                      keep_default=False)

        # Adding field 'UniqueFeed.link'
        db.add_column(u'feeds_uniquefeed', 'link',
                      self.gf('feedhq.feeds.fields.URLField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'UniqueFeed.etag'
        db.add_column(u'feeds_uniquefeed', 'etag',
                      self.gf('django.db.models.fields.CharField')(max_length=1023, null=True, blank=True),
                      keep_default=False)

        # Adding field 'UniqueFeed.subscribers'
        db.add_column(u'feeds_uniquefeed', 'subscribers',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1, db_index=True),
                      keep_default=False)

        # Adding field 'UniqueFeed.title'
        db.add_column(u'feeds_uniquefeed', 'title',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=2048, blank=True),
                      keep_default=False)

        # Adding field 'UniqueFeed.modified'
        db.add_column(u'feeds_uniquefeed', 'modified',
                      self.gf('django.db.models.fields.CharField')(max_length=1023, null=True, blank=True),
                      keep_default=False)

        # Adding field 'UniqueFeed.last_update'
        db.add_column(u'feeds_uniquefeed', 'last_update',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True),
                      keep_default=False)


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'black'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', '-id')", 'object_name': 'Entry', 'index_together': "(('user', 'date'), ('user', 'read'), ('user', 'starred'), ('user', 'broadcast'))"},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            'guid': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'endless_pages': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'font': ('django.db.models.fields.CharField', [], {'default': "'palatino'", 'max_length': '75'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['feeds']

########NEW FILE########
__FILENAME__ = 0016_auto__add_index_feed_url
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Feed', fields ['url']
        db.commit_transaction()
        db.execute('CREATE INDEX CONCURRENTLY "feeds_feed_url" '
                   'ON "feeds_feed" ("url")')
        db.start_transaction()

    def backwards(self, orm):
        # Removing index on 'Feed', fields ['url']
        db.delete_index(u'feeds_feed', ['url'])

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'feeds.category': {
            'Meta': {'ordering': "('order', 'name', 'id')", 'unique_together': "(('user', 'slug'), ('user', 'name'))", 'object_name': 'Category'},
            'color': ('django.db.models.fields.CharField', [], {'default': "'pale-blue'", 'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'db_index': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'categories'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.entry': {
            'Meta': {'ordering': "('-date', '-id')", 'object_name': 'Entry', 'index_together': "(('user', 'date'), ('user', 'read'), ('user', 'starred'), ('user', 'broadcast'))"},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'broadcast': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': u"orm['feeds.Feed']"}),
            'guid': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'read_later_url': ('feedhq.feeds.fields.URLField', [], {'blank': 'True'}),
            'starred': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'subtitle': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.favicon': {
            'Meta': {'object_name': 'Favicon'},
            'favicon': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True', 'db_index': 'True'})
        },
        u'feeds.feed': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Feed'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'feeds'", 'null': 'True', 'to': u"orm['feeds.Category']"}),
            'favicon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'img_safe': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '1023'}),
            'unread_count': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'feeds'", 'to': u"orm['profiles.User']"})
        },
        u'feeds.uniquefeed': {
            'Meta': {'object_name': 'UniqueFeed'},
            'error': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'db_column': "'muted_reason'", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'muted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'url': ('feedhq.feeds.fields.URLField', [], {'unique': 'True'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'endless_pages': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'font': ('django.db.models.fields.CharField', [], {'default': "'pt-serif'", 'max_length': '75'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'ttl': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['feeds']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import base64
import bleach
import datetime
import feedparser
import hashlib
import json
import logging
import lxml.html
import magic
import random
import requests
import six
import socket
import struct
import time

from django.db import models
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse, reverse_lazy
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.encoding import force_bytes, python_2_unicode_compatible
from django.utils.html import format_html
from django.utils.text import unescape_entities
from django.utils.translation import ugettext_lazy as _, string_concat
from django_push.subscriber.signals import updated
from lxml.etree import ParserError
from rache import schedule_job, delete_job
from requests.exceptions import ConnectionError
from requests.packages.urllib3.exceptions import (LocationParseError,
                                                  DecodeError)
from requests_oauthlib import OAuth1
from six.moves.http_client import IncompleteRead
from six.moves.urllib import parse as urlparse

import pytz

from .fields import URLField
from .tasks import (update_feed, update_favicon, store_entries,
                    ensure_subscribed)
from .utils import (FAVICON_FETCHER, USER_AGENT, is_feed, epoch_to_utc,
                    get_job, JobNotFound)
from ..storage import OverwritingStorage
from ..tasks import enqueue
from ..utils import get_redis_connection

logger = logging.getLogger(__name__)

feedparser.PARSE_MICROFORMATS = False
feedparser.SANITIZE_HTML = False

COLORS = (
    ('red', _('Red')),
    ('dark-red', _('Dark Red')),
    ('pale-green', _('Pale Green')),
    ('green', _('Green')),
    ('army-green', _('Army Green')),
    ('pale-blue', _('Pale Blue')),
    ('blue', _('Blue')),
    ('dark-blue', _('Dark Blue')),
    ('orange', _('Orange')),
    ('dark-orange', _('Dark Orange')),
    ('black', _('Black')),
    ('gray', _('Gray')),
)


def random_color():
    return random.choice(COLORS)[0]


def timedelta_to_seconds(delta):
    return delta.days * 3600 * 24 + delta.seconds


def enqueue_favicon(url, force_update=False):
    enqueue(update_favicon, args=[url], kwargs={'force_update': force_update},
            queue='favicons')


class CategoryManager(models.Manager):
    def with_unread_counts(self):
        return self.values('id', 'name', 'slug', 'color').annotate(
            unread_count=models.Sum('feeds__unread_count'))


@python_2_unicode_compatible
class Category(models.Model):
    """Used to sort our feeds"""
    name = models.CharField(_('Name'), max_length=1023, db_index=True)
    slug = models.SlugField(_('Slug'), db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'),
                             related_name='categories')
    # Some day there will be drag'n'drop ordering
    order = models.PositiveIntegerField(blank=True, null=True)

    # Categories have nice cute colors
    color = models.CharField(_('Color'), max_length=50, choices=COLORS,
                             default=random_color)

    objects = CategoryManager()

    def __str__(self):
        return u'%s' % self.name

    class Meta:
        ordering = ('order', 'name', 'id')
        verbose_name_plural = 'categories'
        unique_together = (
            ('user', 'slug'),
            ('user', 'name'),
        )

    def get_absolute_url(self):
        return reverse('feeds:category', args=[self.slug])

    def save(self, *args, **kwargs):
        update_slug = kwargs.pop('update_slug', False)
        if not self.slug or update_slug:
            slug = slugify(self.name)
            if not slug:
                slug = 'unknown'
            valid = False
            candidate = slug
            num = 1
            while not valid:
                if candidate in ('add', 'import'):  # gonna conflict
                    candidate = '{0}-{1}'.format(slug, num)
                categories = self.user.categories.filter(slug=candidate)
                if self.pk is not None:
                    categories = categories.exclude(pk=self.pk)
                if categories.exists():
                    candidate = '{0}-{1}'.format(slug, num)
                    num += 1
                else:
                    valid = True
            self.slug = candidate
        return super(Category, self).save(*args, **kwargs)


class UniqueFeedManager(models.Manager):
    def update_feed(self, url, etag=None, last_modified=None, subscribers=1,
                    backoff_factor=1, previous_error=None, link=None,
                    title=None, hub=None):

        # Check if this domain has rate-limiting rules
        domain = urlparse.urlparse(url).netloc
        ratelimit_key = 'ratelimit:{0}'.format(domain)
        retry_at = cache.get(ratelimit_key)
        if retry_at:
            retry_in = (epoch_to_utc(retry_at) - timezone.now()).seconds
            schedule_job(url, schedule_in=retry_in,
                         connection=get_redis_connection())
            return

        if subscribers == 1:
            subscribers_text = '1 subscriber'
        else:
            subscribers_text = '{0} subscribers'.format(subscribers)

        headers = {
            'User-Agent': USER_AGENT % subscribers_text,
            'Accept': feedparser.ACCEPT_HEADER,
        }

        if last_modified:
            headers['If-Modified-Since'] = force_bytes(last_modified)
        if etag:
            headers['If-None-Match'] = force_bytes(etag)

        if settings.TESTS:
            # Make sure requests.get is properly mocked during tests
            if str(type(requests.get)) != "<class 'mock.MagicMock'>":
                raise ValueError("Not Mocked")

        start = datetime.datetime.now()
        error = None
        try:
            response = requests.get(
                url, headers=headers,
                timeout=UniqueFeed.request_timeout(backoff_factor))
        except (requests.RequestException, socket.timeout, socket.error,
                IncompleteRead, DecodeError) as e:
            logger.debug("Error fetching %s, %s" % (url, str(e)))
            if isinstance(e, IncompleteRead):
                error = UniqueFeed.CONNECTION_ERROR
            elif isinstance(e, DecodeError):
                error = UniqueFeed.DECODE_ERROR
            else:
                error = UniqueFeed.TIMEOUT
            self.backoff_feed(url, error, backoff_factor)
            return
        except LocationParseError:
            logger.debug(u"Failed to parse URL for {0}".format(url))
            self.mute_feed(url, UniqueFeed.PARSE_ERROR)
            return

        elapsed = (datetime.datetime.now() - start).seconds

        ctype = response.headers.get('Content-Type', None)
        if (response.history and
            url != response.url and ctype is not None and (
                ctype.startswith('application') or
                ctype.startswith('text/xml') or
                ctype.startswith('text/rss'))):
            redirection = None
            for index, redirect in enumerate(response.history):
                if redirect.status_code != 301:
                    break
                # Actual redirection is next request's url
                try:
                    redirection = response.history[index + 1].url
                except IndexError:  # next request is final request
                    redirection = response.url

            if redirection is not None and redirection != url:
                self.handle_redirection(url, redirection)

        update = {'last_update': int(time.time())}

        if response.status_code == 410:
            logger.debug(u"Feed gone, {0}".format(url))
            self.mute_feed(url, UniqueFeed.GONE)
            return

        elif response.status_code in [400, 401, 403, 404, 500, 502, 503]:
            self.backoff_feed(url, str(response.status_code), backoff_factor)
            return

        elif response.status_code not in [200, 204, 304]:
            logger.debug(u"{0} returned {1}".format(url, response.status_code))

            if response.status_code == 429:
                # Too Many Requests
                # Prevent next jobs from fetching the URL before retry-after
                retry_in = int(response.headers.get('Retry-After', 60))
                retry_at = timezone.now() + datetime.timedelta(
                    seconds=retry_in)
                cache.set(ratelimit_key,
                          int(retry_at.strftime('%s')),
                          retry_in)
                schedule_job(url, schedule_in=retry_in)
                return

        else:
            # Avoid going back to 1 directly if it isn't safe given the
            # actual response time.
            if previous_error and error is None:
                update['error'] = None
            backoff_factor = min(backoff_factor, self.safe_backoff(elapsed))
            update['backoff_factor'] = backoff_factor

        if response.status_code == 304:
            schedule_job(url,
                         schedule_in=UniqueFeed.delay(backoff_factor, hub),
                         connection=get_redis_connection(), **update)
            return

        if 'etag' in response.headers:
            update['etag'] = response.headers['etag']
        else:
            update['etag'] = None

        if 'last-modified' in response.headers:
            update['modified'] = response.headers['last-modified']
        else:
            update['modified'] = None

        try:
            if not response.content:
                content = ' '  # chardet won't detect encoding on empty strings
            else:
                content = response.content
        except socket.timeout:
            logger.debug(u'{0} timed out'.format(url))
            self.backoff_feed(url, UniqueFeed.TIMEOUT, backoff_factor)
            return

        parsed = feedparser.parse(content)

        if not is_feed(parsed):
            self.backoff_feed(url, UniqueFeed.NOT_A_FEED,
                              UniqueFeed.MAX_BACKOFF)
            return

        if 'link' in parsed.feed and parsed.feed.link != link:
            update['link'] = parsed.feed.link

        if 'title' in parsed.feed and parsed.feed.title != title:
            update['title'] = parsed.feed.title

        if 'links' in parsed.feed:
            for link in parsed.feed.links:
                if link.rel == 'hub':
                    update['hub'] = link.href
        if 'hub' not in update:
            update['hub'] = None
        else:
            subs_key = u'pshb:{0}'.format(url)
            enqueued = cache.get(subs_key)
            if not enqueued:
                cache.set(subs_key, True, 3600 * 24)
                enqueue(ensure_subscribed, args=[url, update['hub']],
                        queue='store')

        schedule_job(url,
                     schedule_in=UniqueFeed.delay(
                         update.get('backoff_factor', backoff_factor),
                         update['hub']),
                     connection=get_redis_connection(), **update)

        entries = list(filter(
            None,
            [self.entry_data(entry, parsed) for entry in parsed.entries]
        ))
        if len(entries):
            enqueue(store_entries, args=[url, entries], queue='store')

    @classmethod
    def entry_data(cls, entry, parsed):
        if 'link' not in entry:
            return
        title = entry.title if 'title' in entry else u''
        if len(title) > 255:  # FIXME this is gross
            title = title[:254] + u'…'
        entry_date, date_generated = cls.entry_date(entry)
        data = {
            'title': title,
            'link': entry.link,
            'date': entry_date,
            'author': entry.get('author', parsed.get('author', ''))[:1023],
            'guid': entry.get('id', entry.link),
            'date_generated': date_generated,
        }
        if not data['guid']:
            data['guid'] = entry.link
        if not data['guid']:
            data['guid'] = entry.title
        if not data['guid']:
            return
        if 'description' in entry:
            data['subtitle'] = entry.description
        if 'summary' in entry:
            data['subtitle'] = entry.summary
        if 'content' in entry:
            data['subtitle'] = ''

            # If there are several types, promote html. text items
            # can be duplicates.
            selected_type = None
            types = set([c['type'] for c in entry.content])
            if len(types) > 1 and 'text/html' in types:
                selected_type = 'text/html'
            for content in entry.content:
                if selected_type is None or content['type'] == selected_type:
                    data['subtitle'] += content.value
        if 'subtitle' in data:
            data['subtitle'] = u'<div>{0}</div>'.format(data['subtitle'])
        return data

    @classmethod
    def entry_date(cls, entry):
        date_generated = False
        if 'published_parsed' in entry and entry.published_parsed is not None:
            field = entry.published_parsed
        elif 'updated_parsed' in entry and entry.updated_parsed is not None:
            field = entry.updated_parsed
        else:
            field = None

        if field is None:
            entry_date = timezone.now()
            date_generated = True
        else:
            entry_date = timezone.make_aware(
                datetime.datetime(*field[:6]),
                pytz.utc,
            )
            # Sometimes entries are published in the future. If they're
            # published, it's probably safe to adjust the date.
            if entry_date > timezone.now():
                entry_date = timezone.now()
        return entry_date, date_generated

    def handle_redirection(self, old_url, new_url):
        logger.debug(u"{0} moved to {1}".format(old_url, new_url))
        Feed.objects.filter(url=old_url).update(url=new_url)
        unique, created = self.get_or_create(url=new_url)
        if created:
            unique.schedule()
            if not settings.TESTS:
                enqueue_favicon(new_url)
        self.filter(url=old_url).delete()
        delete_job(old_url, connection=get_redis_connection())

    def mute_feed(self, url, reason):
        delete_job(url, connection=get_redis_connection())
        self.filter(url=url).update(muted=True, error=reason)

    def backoff_feed(self, url, error, backoff_factor):
        if backoff_factor == UniqueFeed.MAX_BACKOFF - 1:
            logger.debug(u"{0} reached max backoff period ({1})".format(
                url, error,
            ))
        backoff_factor = min(UniqueFeed.MAX_BACKOFF, backoff_factor + 1)
        schedule_job(url, schedule_in=UniqueFeed.delay(backoff_factor),
                     error=error, backoff_factor=backoff_factor,
                     connection=get_redis_connection())

    def safe_backoff(self, response_time):
        """
        Returns the backoff factor that should be used to keep the feed
        working given the last response time. Keep a margin. Backoff time
        shouldn't increase, this is only used to avoid returning back to 10s
        if the response took more than that.
        """
        return int((response_time * 1.2) / 10) + 1


class JobDataMixin(object):
    @property
    def job_details(self):
        if hasattr(self, 'muted') and self.muted:
            return {}
        if not hasattr(self, '_job_details'):
            self._job_details = get_job(self.url)
        return self._job_details

    @property
    def safe_job_details(self):
        """
        For use in templates -- when raising JobNotFound is not
        acceptable.
        """
        try:
            return self.job_details
        except JobNotFound:
            return

    @property
    def scheduler_data(self):
        return json.dumps(self.job_details, indent=4, sort_keys=True)

    @property
    def next_update(self):
        return epoch_to_utc(self.job_details['schedule_at'])

    @property
    def last_update(self):
        try:
            update = self.job_details.get('last_update')
        except JobNotFound:
            return
        if update is not None:
            return epoch_to_utc(update)

    @property
    def link(self):
        try:
            return self.job_details.get('link', self.url)
        except JobNotFound:
            return self.url


@python_2_unicode_compatible
class UniqueFeed(JobDataMixin, models.Model):
    GONE = 'gone'
    TIMEOUT = 'timeout'
    PARSE_ERROR = 'parseerror'
    CONNECTION_ERROR = 'connerror'
    DECODE_ERROR = 'decodeerror'
    NOT_A_FEED = 'notafeed'
    HTTP_400 = '400'
    HTTP_401 = '401'
    HTTP_403 = '403'
    HTTP_404 = '404'
    HTTP_500 = '500'
    HTTP_502 = '502'
    HTTP_503 = '503'
    MUTE_CHOICES = (
        (GONE, 'Feed gone (410)'),
        (TIMEOUT, 'Feed timed out'),
        (PARSE_ERROR, 'Location parse error'),
        (CONNECTION_ERROR, 'Connection error'),
        (DECODE_ERROR, 'Decoding error'),
        (NOT_A_FEED, 'Not a valid RSS/Atom feed'),
        (HTTP_400, 'HTTP 400'),
        (HTTP_401, 'HTTP 401'),
        (HTTP_403, 'HTTP 403'),
        (HTTP_404, 'HTTP 404'),
        (HTTP_500, 'HTTP 500'),
        (HTTP_502, 'HTTP 502'),
        (HTTP_503, 'HTTP 503'),
    )
    MUTE_DICT = dict(MUTE_CHOICES)

    url = URLField(_('URL'), unique=True)
    muted = models.BooleanField(_('Muted'), default=False, db_index=True)
    error = models.CharField(_('Error'), max_length=50, null=True, blank=True,
                             choices=MUTE_CHOICES, db_column='muted_reason')

    objects = UniqueFeedManager()

    MAX_BACKOFF = 10  # Approx. 24 hours
    UPDATE_PERIOD = 60  # in minutes
    BACKOFF_EXPONENT = 1.5
    TIMEOUT_BASE = 20
    JOB_ATTRS = ['modified', 'etag', 'backoff_factor', 'error', 'link',
                 'title', 'hub', 'subscribers', 'last_update']

    def __str__(self):
        return u'%s' % self.url

    def truncated_url(self):
        if len(self.url) > 50:
            return self.url[:49] + u'…'
        return self.url
    truncated_url.short_description = _('URL')
    truncated_url.admin_order_field = 'url'

    @classmethod
    def request_timeout(cls, backoff_factor):
        return 10 * backoff_factor

    @classmethod
    def delay(cls, backoff_factor, hub=None):
        if hub is not None:
            backoff_factor = max(backoff_factor, 3)
        return datetime.timedelta(
            seconds=60 * cls.UPDATE_PERIOD *
            backoff_factor ** cls.BACKOFF_EXPONENT)

    @property
    def schedule_in(self):
        return (
            self.last_update + self.delay(self.job_details['backoff_factor'],
                                          self.job_details.get('hub'))
        ) - timezone.now()

    def schedule(self, schedule_in=None, **job):
        if hasattr(self, '_job_details'):
            del self._job_details
        connection = get_redis_connection()
        kwargs = {
            'subscribers': 1,
            'backoff_factor': 1,
            'last_update': int(time.time()),
        }
        kwargs.update(job)
        if schedule_in is None:
            try:
                for attr in self.JOB_ATTRS:
                    if attr in self.job_details:
                        kwargs[attr] = self.job_details[attr]
                schedule_in = self.schedule_in
            except JobNotFound:
                schedule_in = self.delay(kwargs['backoff_factor'])
        schedule_job(self.url, schedule_in=schedule_in,
                     connection=connection, **kwargs)


@python_2_unicode_compatible
class Feed(JobDataMixin, models.Model):
    """A URL and some extra stuff"""
    name = models.CharField(_('Name'), max_length=1023)
    url = URLField(_('URL'), db_index=True)
    category = models.ForeignKey(
        Category, verbose_name=_('Category'), related_name='feeds',
        help_text=string_concat('<a href="',
                                reverse_lazy('feeds:add_category'), '">',
                                _('Add a category'), '</a>'),
        null=True, blank=True,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'),
                             related_name='feeds')
    unread_count = models.PositiveIntegerField(_('Unread count'), default=0)
    favicon = models.ImageField(_('Favicon'), upload_to='favicons', null=True,
                                blank=True, storage=OverwritingStorage())
    img_safe = models.BooleanField(_('Display images by default'),
                                   default=False)

    def __str__(self):
        return u'%s' % self.name

    class Meta:
        ordering = ('name',)

    def get_absolute_url(self):
        return reverse('feeds:feed', args=[self.id])

    def save(self, *args, **kwargs):
        feed_created = self.pk is None
        super(Feed, self).save(*args, **kwargs)
        unique, created = UniqueFeed.objects.get_or_create(url=self.url)
        if feed_created or created:
            try:
                details = self.job_details
            except JobNotFound:
                details = {}
            enqueue(update_feed, kwargs={
                'url': self.url,
                'subscribers': details.get('subscribers', 1),
                'backoff_factor': details.get('backoff_factor', 1),
                'error': details.get('error'),
                'link': details.get('link'),
                'title': details.get('title'),
                'hub': details.get('hub'),
            }, queue='high', timeout=20)
            if not settings.TESTS:
                enqueue_favicon(unique.url)

    @property
    def media_safe(self):
        return self.img_safe

    def favicon_img(self):
        if not self.favicon:
            return ''
        return format_html(
            '<img src="{0}" width="16" height="16" />', self.favicon.url)

    def update_unread_count(self):
        self.unread_count = self.entries.filter(read=False).count()
        self.save(update_fields=['unread_count'])

    @property
    def color(self):
        md = hashlib.md5()
        md.update(self.url.encode('utf-8'))
        index = int(md.hexdigest()[0], 16)
        index = index * len(COLORS) // 16
        return COLORS[index][0]

    def error_display(self):
        if self.muted:
            key = self.error
        else:
            key = str(self.job_details['error'])
        return UniqueFeed.MUTE_DICT.get(key, _('Error'))


class EntryManager(models.Manager):
    def unread(self):
        return self.filter(read=False).count()


@python_2_unicode_compatible
class Entry(models.Model):
    """An entry is a cached feed item"""
    feed = models.ForeignKey(Feed, verbose_name=_('Feed'), null=True,
                             blank=True, related_name='entries')
    title = models.CharField(_('Title'), max_length=255)
    subtitle = models.TextField(_('Abstract'))
    link = URLField(_('URL'), db_index=True)
    author = models.CharField(_('Author'), max_length=1023, blank=True)
    date = models.DateTimeField(_('Date'), db_index=True)
    guid = URLField(_('GUID'), db_index=True, blank=True)
    # The User FK is redundant but this may be better for performance and if
    # want to allow user input.
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=(_('User')), related_name='entries')
    # Mark something as read or unread
    read = models.BooleanField(_('Read'), default=False, db_index=True)
    # Read later: store the URL
    read_later_url = URLField(_('Read later URL'), blank=True)
    starred = models.BooleanField(_('Starred'), default=False, db_index=True)
    broadcast = models.BooleanField(_('Broadcast'), default=False,
                                    db_index=True)

    objects = EntryManager()

    class Meta:
        # Display most recent entries first
        ordering = ('-date', '-id')
        verbose_name_plural = 'entries'
        index_together = (
            ('user', 'date'),
            ('user', 'read'),
            ('user', 'starred'),
            ('user', 'broadcast'),
        )

    ELEMENTS = (
        feedparser._HTMLSanitizer.acceptable_elements |
        feedparser._HTMLSanitizer.mathml_elements |
        feedparser._HTMLSanitizer.svg_elements |
        set(['iframe', 'object', 'embed', 'script'])
    ) - set(['font'])
    ATTRIBUTES = (
        feedparser._HTMLSanitizer.acceptable_attributes |
        feedparser._HTMLSanitizer.mathml_attributes |
        feedparser._HTMLSanitizer.svg_attributes
    ) - set(['id', 'class'])
    CSS_PROPERTIES = feedparser._HTMLSanitizer.acceptable_css_properties

    def __str__(self):
        return u'%s' % self.title

    @property
    def hex_pk(self):
        value = hex(struct.unpack("L", struct.pack("l", self.pk))[0])
        if value.endswith("L"):
            value = value[:-1]
        return value[2:].zfill(16)

    @property
    def base64_url(self):
        return base64.b64encode(self.link.encode('utf-8'))

    def sanitized_title(self):
        if self.title:
            return unescape_entities(bleach.clean(self.title, tags=[],
                                                  strip=True))
        return _('(No title)')

    @property
    def content(self):
        if not hasattr(self, '_content'):
            if self.subtitle:
                xml = lxml.html.fromstring(self.subtitle)
                try:
                    xml.make_links_absolute(self.feed.url)
                except ValueError as e:
                    if e.args[0] != 'Invalid IPv6 URL':
                        raise
                self._content = lxml.html.tostring(xml).decode('utf-8')
            else:
                self._content = self.subtitle
        return self._content

    def sanitized_content(self):
        return bleach.clean(
            self.content,
            tags=self.ELEMENTS,
            attributes=self.ATTRIBUTES,
            styles=self.CSS_PROPERTIES,
            strip=True,
        )

    def sanitized_nomedia_content(self):
        return bleach.clean(
            self.content,
            tags=self.ELEMENTS - set(['img', 'audio', 'video', 'iframe',
                                      'object', 'embed', 'script', 'source']),
            attributes=self.ATTRIBUTES,
            styles=self.CSS_PROPERTIES,
            strip=True,
        )

    def get_absolute_url(self):
        return reverse('feeds:item', args=[self.id])

    def link_domain(self):
        return urlparse.urlparse(self.link).netloc

    def read_later_domain(self):
        netloc = urlparse.urlparse(self.read_later_url).netloc
        return netloc.replace('www.', '')

    def tweet(self):
        return u"{title} — {link}".format(
            title=self.title, link=self.link)

    def read_later(self):
        """Adds this item to the user's read list"""
        user = self.user
        if not user.read_later:
            return
        getattr(self, 'add_to_%s' % self.user.read_later)()

    def add_to_readitlater(self):
        url = 'https://readitlaterlist.com/v2/add'
        data = json.loads(self.user.read_later_credentials)
        data.update({
            'apikey': settings.API_KEYS['readitlater'],
            'url': self.link,
            'title': self.title,
        })
        # The readitlater API doesn't return anything back
        requests.post(url, data=data)

    def add_to_pocket(self):
        url = 'https://getpocket.com/v3/add'
        data = json.loads(self.user.read_later_credentials)
        data.update({
            'consumer_key': settings.POCKET_CONSUMER_KEY,
            'url': self.link,
        })
        response = requests.post(url, data=json.dumps(data),
                                 headers={'Content-Type': 'application/json'})
        self.read_later_url = 'https://getpocket.com/a/read/{0}'.format(
            response.json()['item']['item_id']
        )
        self.save(update_fields=['read_later_url'])

    def add_to_readability(self):
        url = 'https://www.readability.com/api/rest/v1/bookmarks'
        auth = self.oauth_client('readability')
        response = requests.post(url, auth=auth, data={'url': self.link})
        response = requests.get(response.headers['location'], auth=auth)
        url = 'https://www.readability.com/articles/%s'
        self.read_later_url = url % response.json()['article']['id']
        self.save(update_fields=['read_later_url'])

    def add_to_instapaper(self):
        url = 'https://www.instapaper.com/api/1/bookmarks/add'
        auth = self.oauth_client('instapaper')
        response = requests.post(url, auth=auth, data={'url': self.link})
        url = 'https://www.instapaper.com/read/%s'
        url = url % response.json()[0]['bookmark_id']
        self.read_later_url = url
        self.save(update_fields=['read_later_url'])

    def oauth_client(self, service):
        service_settings = getattr(settings, service.upper())
        creds = json.loads(self.user.read_later_credentials)
        auth = OAuth1(service_settings['CONSUMER_KEY'],
                      service_settings['CONSUMER_SECRET'],
                      creds['oauth_token'],
                      creds['oauth_token_secret'])
        return auth

    def current_year(self):
        return self.date.year == timezone.now().year


def pubsubhubbub_update(notification, request, links, **kwargs):
    url = None
    # Try the header links first
    if links is not None:
        for link in links:
            if link['rel'] == 'self':
                url = link['url']
                break

    notification = feedparser.parse(notification)

    # Fallback to feed links if no header link found
    if url is None:
        for link in notification.feed.get('links', []):
            if link['rel'] == 'self':
                url = link['href']
                break

    if url is None:
        return

    entries = list(filter(
        None,
        [UniqueFeedManager.entry_data(
            entry, notification) for entry in notification.entries]
    ))
    if len(entries):
        enqueue(store_entries, args=[url, entries], queue='store')
updated.connect(pubsubhubbub_update)


class FaviconManager(models.Manager):
    def update_favicon(self, url, force_update=False):
        if not url:
            return
        parsed = list(urlparse.urlparse(url))
        if not parsed[0].startswith('http'):
            return
        favicon, created = self.get_or_create(url=url)
        feeds = Feed.objects.filter(url=url, favicon='')
        if (not created and not force_update) and favicon.favicon:
            # Still, add to existing
            favicon_urls = list(self.filter(url=url).exclude(
                favicon='').values_list('favicon', flat=True))
            if not favicon_urls:
                return favicon

            if not feeds.exists():
                return

            feeds.update(favicon=favicon_urls[0])
            return favicon

        ua = {'User-Agent': FAVICON_FETCHER}

        try:
            link = get_job(url).get('link')
        except JobNotFound:
            link = cache.get(u'feed_link:{0}'.format(url))

        if link is None:
            # TODO maybe re-fetch feed
            return favicon

        try:
            page = requests.get(link, headers=ua, timeout=10).content
        except (requests.RequestException, LocationParseError, socket.timeout,
                DecodeError, ConnectionError):
            return favicon
        if not page:
            return favicon

        try:
            if isinstance(page, six.text_type):
                page = page.encode('utf-8')
            icon_path = lxml.html.fromstring(page.lower()).xpath(
                '//link[@rel="icon" or @rel="shortcut icon"]/@href'
            )
        except ParserError:
            return favicon

        if not icon_path:
            parsed[2] = '/favicon.ico'  # 'path' element
            icon_path = [urlparse.urlunparse(parsed)]
        if not icon_path[0].startswith('http'):
            parsed[2] = icon_path[0]
            parsed[3] = parsed[4] = parsed[5] = ''
            icon_path = [urlparse.urlunparse(parsed)]
        try:
            response = requests.get(icon_path[0], headers=ua, timeout=10)
        except requests.RequestException:
            return favicon
        if response.status_code != 200:
            return favicon

        icon_file = ContentFile(response.content)
        icon_type = magic.from_buffer(response.content).decode('utf-8')
        if 'PNG' in icon_type:
            ext = 'png'
        elif ('MS Windows icon' in icon_type or
              'Claris clip art' in icon_type):
            ext = 'ico'
        elif 'GIF' in icon_type:
            ext = 'gif'
        elif 'JPEG' in icon_type:
            ext = 'jpg'
        elif 'PC bitmap' in icon_type:
            ext = 'bmp'
        elif 'TIFF' in icon_type:
            ext = 'tiff'
        elif icon_type == 'data':
            ext = 'ico'
        elif ('HTML' in icon_type or
              icon_type == 'empty' or
              'Photoshop' in icon_type or
              'ASCII' in icon_type or
              'XML' in icon_type or
              'Unicode text' in icon_type or
              'SGML' in icon_type or
              'PHP' in icon_type or
              'very short file' in icon_type or
              'gzip compressed data' in icon_type or
              'ISO-8859 text' in icon_type or
              'Lotus' in icon_type or
              'SVG' in icon_type or
              'Sendmail frozen' in icon_type or
              'GLS_BINARY_LSB_FIRST' in icon_type or
              'PDF' in icon_type or
              'PCX' in icon_type):
            logger.debug("Ignored content type for %s: %s" % (link, icon_type))
            return favicon
        else:
            logger.info("Unknown content type for %s: %s" % (link, icon_type))
            favicon.delete()
            return

        filename = '%s.%s' % (urlparse.urlparse(favicon.url).netloc, ext)
        favicon.favicon.save(filename, icon_file)

        for feed in feeds:
            feed.favicon.save(filename, icon_file)
        return favicon


@python_2_unicode_compatible
class Favicon(models.Model):
    url = URLField(_('URL'), db_index=True, unique=True)
    favicon = models.FileField(upload_to='favicons', blank=True,
                               storage=OverwritingStorage())

    objects = FaviconManager()

    def __str__(self):
        return u'Favicon for %s' % self.url

    def favicon_img(self):
        if not self.favicon:
            return '(None)'
        return '<img src="%s">' % self.favicon.url
    favicon_img.allow_tags = True

########NEW FILE########
__FILENAME__ = tasks
import logging
import requests

from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django_push.subscriber.models import Subscription
from rache import schedule_job
from rq.timeouts import JobTimeoutException

from ..utils import get_redis_connection
from ..profiles.models import User

logger = logging.getLogger(__name__)


# TODO remove unused request_timeout
def update_feed(url, etag=None, modified=None, subscribers=1,
                request_timeout=10, backoff_factor=1, error=None, link=None,
                title=None, hub=None):
    from .models import UniqueFeed
    try:
        UniqueFeed.objects.update_feed(
            url, etag=etag, last_modified=modified, subscribers=subscribers,
            backoff_factor=backoff_factor, previous_error=error, link=link,
            title=title, hub=hub)
    except JobTimeoutException:
        backoff_factor = min(UniqueFeed.MAX_BACKOFF,
                             backoff_factor + 1)
        logger.debug("Job timed out, backing off %s to %s" % (
            url, backoff_factor,
        ))
        schedule_job(url, schedule_in=UniqueFeed.delay(backoff_factor),
                     backoff_factor=backoff_factor,
                     connection=get_redis_connection())


def read_later(entry_pk):
    from .models import Entry
    Entry.objects.get(pk=entry_pk).read_later()


def update_favicon(feed_url, force_update=False):
    from .models import Favicon
    Favicon.objects.update_favicon(feed_url, force_update=force_update)


def ensure_subscribed(topic_url, hub_url):
    """Makes sure the PubSubHubbub subscription is verified"""
    if settings.TESTS:
        if str(type(requests.post)) != "<class 'mock.MagicMock'>":
            raise ValueError("Not Mocked")

    if hub_url is None:
        return

    call, args = None, ()
    try:
        s = Subscription.objects.get(topic=topic_url, hub=hub_url)
    except Subscription.DoesNotExist:
        logger.debug(u"Subscribing to {0} via {1}".format(topic_url, hub_url))
        call = Subscription.objects.subscribe
        args = topic_url, hub_url
    else:
        if (
            not s.verified or
            s.lease_expiration < timezone.now() + timedelta(days=1)
        ):
            logger.debug(u"Renewing subscription {0}".format(s.pk))
            call = s.subscribe
    if call is not None:
        call(*args)


def should_skip(date, ttl):
    delta = timedelta(days=ttl)
    return date + delta < timezone.now()


def store_entries(feed_url, entries):
    from .models import Entry, Feed
    guids = set([entry['guid'] for entry in entries])

    query = Q(feed__url=feed_url)

    # When we have dates, filter the query to avoid returning the whole dataset
    date_generated = any([e.pop('date_generated') for e in entries])
    if not date_generated:
        earliest = min([entry['date'] for entry in entries])
        query &= Q(date__gte=earliest - timedelta(days=1))

    filter_by_title = len(guids) == 1 and len(entries) > 1
    if filter_by_title:
        # All items have the same guid. Query by title instead.
        titles = set([entry['title'] for entry in entries])
        query &= Q(title__in=titles)
    else:
        query &= Q(guid__in=guids)
    existing = Entry.objects.filter(query).values('guid', 'title', 'feed_id')

    existing_guids = defaultdict(set)
    existing_titles = defaultdict(set)
    for entry in existing:
        existing_guids[entry['feed_id']].add(entry['guid'])
        if filter_by_title:
            existing_titles[entry['feed_id']].add(entry['title'])

    feeds = Feed.objects.select_related('user').filter(
        url=feed_url, user__is_suspended=False).values('pk', 'user_id',
                                                       'user__ttl')

    create = []
    update_unread_counts = set()
    refresh_updates = defaultdict(list)
    for feed in feeds:
        for entry in entries:
            if (
                not filter_by_title and
                entry['guid'] in existing_guids[feed['pk']]
            ):
                continue
            if (
                filter_by_title and
                entry['title'] in existing_titles[feed['pk']]
            ):
                continue
            if (
                feed['user__ttl'] and
                should_skip(entry['date'], feed['user__ttl'])
            ):
                continue
            create.append(Entry(user_id=feed['user_id'],
                                feed_id=feed['pk'], **entry))
            update_unread_counts.add(feed['pk'])
            refresh_updates[feed['user_id']].append(entry['date'])

    if create:
        Entry.objects.bulk_create(create)

    for pk in update_unread_counts:
        Feed.objects.filter(pk=pk).update(
            unread_count=Entry.objects.filter(feed_id=pk, read=False).count())

    redis = get_redis_connection()
    for user_id, dates in refresh_updates.items():
        user = User(pk=user_id)
        new_score = float(max(dates).strftime('%s'))
        current_score = redis.zscore(user.last_update_key, feed_url) or 0
        if new_score > current_score:
            redis.zadd(user.last_update_key, feed_url, new_score)

########NEW FILE########
__FILENAME__ = feeds_tags
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def smart_date(value):
    now = timezone.localtime(timezone.now(), value.tzinfo)
    if value.year == now.year:
        if value.month == now.month and value.day == now.day:
            return value.strftime('%H:%M')
        return value.strftime('%b %d')
    return value.strftime('%b %d, %Y')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.entries_list, name='home'),
    url(r'^(?P<page>\d+)/$', views.entries_list, name='home'),
    url(r'^unread/$', views.entries_list,
        {'only_unread': True}, name='unread'),
    url(r'^unread/(?P<page>\d+)/$', views.entries_list,
        {'only_unread': True}, name='unread'),

    url(r'^dashboard/$', views.dashboard, name='dashboard'),
    url(r'^dashboard/unread/$', views.dashboard,
        {'only_unread': True}, name='unread_dashboard'),

    url(r'^stars/$', views.entries_list,
        {'starred': True}, name='stars'),

    url(r'^stars/(?P<page>\d+)/$', views.entries_list,
        {'starred': True}, name='stars'),

    url(r'^manage/$', views.manage, name='manage'),

    url(r'^import/$', views.import_feeds, name='import_feeds'),
    url(r'^subscribe/$', views.subscribe, name='subscribe'),
    url(r'^keyboard/$', views.keyboard, name='keyboard'),

    # Categories
    url(r'^category/add/$', views.add_category, name='add_category'),
    url(r'^category/(?P<slug>[\w_-]+)/edit/$', views.edit_category,
        name='edit_category'),
    url(r'^category/(?P<slug>[\w_-]+)/delete/$', views.delete_category,
        name='delete_category'),

    url(r'^category/(?P<category>[\w_-]+)/$', views.entries_list,
        name='category'),

    url(r'^category/(?P<category>[\w_-]+)/(?P<page>\d+)/$',
        views.entries_list, name='category'),

    url(r'^category/(?P<category>[\w_-]+)/unread/$', views.entries_list,
        {'only_unread': True}, name='unread_category'),
    url(r'^category/(?P<category>[\w_-]+)/unread/(?P<page>\d+)/$',
        views.entries_list, {'only_unread': True}, name='unread_category'),

    # Feeds
    url(r'^feed/add/$', views.add_feed, name='add_feed'),
    url(r'^feed/(?P<feed>\d+)/edit/$', views.edit_feed, name='edit_feed'),
    url(r'^feed/(?P<feed>\d+)/delete/$', views.delete_feed,
        name='delete_feed'),

    url(r'^feed/(?P<feed>\d+)/$', views.entries_list, name='feed'),
    url(r'^feed/(?P<feed>\d+)/(?P<page>\d+)/$', views.entries_list,
        name='feed'),
    url(r'^feed/(?P<feed>\d+)/unread/$', views.entries_list,
        {'only_unread': True}, name='unread_feed'),
    url(r'^feed/(?P<feed>\d+)/unread/(?P<page>\d+)/$', views.entries_list,
        {'only_unread': True}, name='unread_feed'),

    # Entries
    url(r'^entries/(?P<entry_id>\d+)/$', views.item, name='item'),
)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
import datetime

from django.utils import timezone

from rache import job_key, job_details

from .. import __version__
from ..utils import get_redis_connection


USER_AGENT = (
    'FeedHQ/%s (https://github.com/feedhq/feedhq; %%s; https://github.com/'
    'feedhq/feedhq/wiki/fetcher; like FeedFetcher-Google)'
) % __version__
FAVICON_FETCHER = USER_AGENT % 'favicon fetcher'


def is_feed(parsed):
    return hasattr(parsed.feed, 'title')


def epoch_to_utc(value):
    """Converts epoch (in seconds) values to a timezone-aware datetime."""
    return timezone.make_aware(
        datetime.datetime.fromtimestamp(value), timezone.utc)


class JobNotFound(Exception):
    pass


def get_job(name):
    redis = get_redis_connection()
    key = job_key(name)
    if not redis.exists(key):
        raise JobNotFound
    return job_details(name, connection=redis)

########NEW FILE########
__FILENAME__ = views
import json
import logging
import opml
import re

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader, RequestContext
from django.template.defaultfilters import slugify
from django.utils.html import format_html
from django.utils.translation import ugettext as _, ungettext
from django.views import generic

from ..decorators import login_required
from ..tasks import enqueue
from .models import Category, Entry, UniqueFeed
from .forms import (CategoryForm, FeedForm, OPMLImportForm, ActionForm,
                    ReadForm, SubscriptionFormSet, UndoReadForm, user_lock)
from .tasks import read_later

"""
Each view displays a list of entries, with a level of filtering:
    - home: all entries
    - category: entries in a specific category
    - feed: entries for a specific feed
    - item: a single entry

Entries are paginated.
"""

logger = logging.getLogger(__name__)

MEDIA_RE = re.compile(
    r'.*<(img|audio|video|iframe|object|embed|script|source)\s+.*',
    re.UNICODE | re.DOTALL)


class Keyboard(generic.TemplateView):
    template_name = 'feeds/keyboard.html'
keyboard = Keyboard.as_view()


def paginate(object_list, page=1, nb_items=25, force_count=None):
    """
    Simple generic paginator for all the ``Entry`` lists
    """
    if force_count is not None:
        object_list.count = lambda x: force_count

    paginator = Paginator(object_list, nb_items)

    try:
        paginated = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paginated = paginator.page(paginator.num_pages)

    return paginated, paginator._count


@login_required
def entries_list(request, page=1, only_unread=False, category=None, feed=None,
                 starred=False):
    """
    Displays a paginated list of entries.

    ``page``: the page number
    ``only_unread``: filters the list to display only the new entries
    ``category``: (slug) if set, will filter the entries of this category
    ``feed``: (object_id) if set, will filter the entries of this feed

    Note: only set category OR feed. Not both at the same time.
    """
    user = request.user
    categories = user.categories.with_unread_counts()

    if category is not None:
        category = get_object_or_404(user.categories.all(), slug=category)
        entries = user.entries.filter(feed__category=category)
        all_url = reverse('feeds:category', args=[category.slug])
        unread_url = reverse('feeds:unread_category', args=[category.slug])

    if feed is not None:
        feed = get_object_or_404(user.feeds.select_related('category'),
                                 pk=feed)
        entries = feed.entries.all()
        all_url = reverse('feeds:feed', args=[feed.id])
        unread_url = reverse('feeds:unread_feed', args=[feed.id])
        category = feed.category

    if starred is True:
        entries = user.entries.filter(starred=True)
        all_url = reverse('feeds:stars')
        unread_url = None

    if feed is None and category is None and starred is not True:
        entries = user.entries.all()
        all_url = reverse('feeds:home')
        unread_url = reverse('feeds:unread')

    entries = entries.select_related('feed', 'feed__category')
    if user.oldest_first:
        entries = entries.order_by('date', 'id')

    if request.method == 'POST':
        if request.POST['action'] in (ReadForm.READ_ALL, ReadForm.READ_PAGE):
            pages_only = request.POST['action'] == ReadForm.READ_PAGE
            form = ReadForm(entries, feed, category, user,
                            pages_only=pages_only, data=request.POST)
            if form.is_valid():
                pks = form.save()
                undo_form = loader.render_to_string('feeds/undo_read.html', {
                    'form': UndoReadForm(initial={
                        'pks': json.dumps(pks, separators=(',', ':'))}),
                    'action': request.get_full_path(),
                }, context_instance=RequestContext(request))
                message = ungettext(
                    '1 entry has been marked as read.',
                    '%(value)s entries have been marked as read.',
                    'value') % {'value': len(pks)}
                messages.success(request,
                                 format_html(u"{0} {1}", message, undo_form))

        elif request.POST['action'] == 'undo-read':
            form = UndoReadForm(user, data=request.POST)
            if form.is_valid():
                count = form.save()
                messages.success(
                    request, ungettext(
                        '1 entry has been marked as unread.',
                        '%(value)s entries have been marked as unread.',
                        'value') % {'value': count})

        if only_unread:
            return redirect(unread_url)
        else:
            return redirect(all_url)

    unread_count = entries.filter(read=False).count()

    # base_url is a variable that helps the paginator a lot. The drawback is
    # that the paginator can't use reversed URLs.
    base_url = all_url
    if only_unread:
        total_count = entries.count()
        entries = entries.filter(read=False)
        base_url = unread_url
        entries, foo = paginate(entries, page=page,
                                force_count=unread_count,
                                nb_items=request.user.entries_per_page)
    else:
        entries, total_count = paginate(entries, page=page,
                                        nb_items=request.user.entries_per_page)

    request.session['back_url'] = request.get_full_path()
    context = {
        'categories': categories,
        'category': category,
        'feed': feed,
        'entries': entries,
        'only_unread': only_unread,
        'unread_count': unread_count,
        'total_count': total_count,
        'all_url': all_url,
        'unread_url': unread_url,
        'base_url': base_url,
        'stars': starred,
        'entries_template': 'feeds/entries_include.html',
    }
    if unread_count:
        context['read_all_form'] = ReadForm()
        context['read_page_form'] = ReadForm(pages_only=True, initial={
            'action': ReadForm.READ_PAGE,
            'pages': json.dumps([int(page)]),
        })
        context['action'] = request.get_full_path()
    if entries.paginator.count == 0 and request.user.feeds.count() == 0:
        context['noob'] = True

    if request.is_ajax():
        template_name = context['entries_template']
    else:
        template_name = 'feeds/entries_list.html'

    return render(request, template_name, context)


class SuccessMixin(object):
    success_message = None

    def get_success_message(self):
        return self.success_message

    def form_valid(self, form):
        response = super(SuccessMixin, self).form_valid(form)
        msg = self.get_success_message()
        if msg is not None:
            messages.success(self.request, msg)
        return response


class CategoryMixin(SuccessMixin):
    form_class = CategoryForm
    success_url = reverse_lazy('feeds:manage')

    def get_form_kwargs(self):
        kwargs = super(CategoryMixin, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_object(self):
        return get_object_or_404(self.request.user.categories,
                                 slug=self.kwargs['slug'])


class AddCategory(CategoryMixin, generic.CreateView):
    template_name = 'feeds/category_form.html'
add_category = login_required(AddCategory.as_view())


class EditCategory(CategoryMixin, generic.UpdateView):
    template_name = 'feeds/edit_category.html'

    def get_success_message(self):
        return _('%(category)s has been successfully '
                 'updated') % {'category': self.object}
edit_category = login_required(EditCategory.as_view())


class DeleteCategory(CategoryMixin, generic.DeleteView):
    success_url = reverse_lazy('feeds:manage')

    def get_success_message(self):
        return _('%(category)s has been successfully '
                 'deleted') % {'category': self.object}

    def get_context_data(self, **kwargs):
        kwargs.update({
            'entry_count': Entry.objects.filter(
                feed__category=self.object,
            ).count(),
            'feed_count': self.object.feeds.count(),
        })
        return super(DeleteCategory, self).get_context_data(**kwargs)
delete_category = login_required(DeleteCategory.as_view())


class FeedMixin(SuccessMixin):
    form_class = FeedForm
    success_url = reverse_lazy('feeds:manage')

    def get_form_kwargs(self):
        kwargs = super(FeedMixin, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_object(self):
        return get_object_or_404(self.request.user.feeds,
                                 pk=self.kwargs['feed'])


class AddFeed(FeedMixin, generic.CreateView):
    template_name = 'feeds/feed_form.html'

    def get_success_message(self):
        return _('%(feed)s has been successfully '
                 'added') % {'feed': self.object.name}

    def get_initial(self):
        initial = super(AddFeed, self).get_initial()
        if 'feed' in self.request.GET:
            initial['url'] = self.request.GET['feed']
        if 'name' in self.request.GET:
            initial['name'] = self.request.GET['name']
        return initial
add_feed = login_required(AddFeed.as_view())


class EditFeed(FeedMixin, generic.UpdateView):
    template_name = 'feeds/edit_feed.html'

    def get_success_message(self):
        return _('%(feed)s has been successfully '
                 'updated') % {'feed': self.object.name}
edit_feed = login_required(EditFeed.as_view())


class DeleteFeed(FeedMixin, generic.DeleteView):
    def get_success_message(self):
        return _('%(feed)s has been successfully '
                 'deleted') % {'feed': self.object.name}

    def get_context_data(self, **kwargs):
        kwargs['entry_count'] = self.object.entries.count()
        return super(DeleteFeed, self).get_context_data(**kwargs)
delete_feed = login_required(DeleteFeed.as_view())


@login_required
def item(request, entry_id):
    qs = Entry.objects.filter(user=request.user).select_related(
        'feed', 'feed__category',
    )
    entry = get_object_or_404(qs, pk=entry_id)
    if not entry.read:
        entry.read = True
        entry.save(update_fields=['read'])
        entry.feed.update_unread_count()

    back_url = request.session.get('back_url',
                                   default=entry.feed.get_absolute_url())

    # Depending on the list used to access to this page, we try to find in an
    # intelligent way which is the previous and the next item in the list.

    # This way the user has nice 'previous' and 'next' buttons that are
    # dynamically changed
    only_unread = False
    bits = back_url.split('/')
    # FIXME: The kw thing currently doesn't work with paginated content.
    kw = {'user': request.user}

    if bits[1] == '':
        # this is the homepage
        kw = {'user': request.user}

    elif bits[1] == 'unread':
        # Homepage too, but only unread
        kw = {'user': request.user, 'read': False}
        only_unread = True

    elif bits[1] == 'feed':
        # Entries in self.feed
        kw = {'feed': entry.feed}

    elif bits[1] == 'category':
        # Entries in self.feed.category
        category_slug = bits[2]
        category = Category.objects.get(slug=category_slug, user=request.user)
        kw = {'feed__category': category}

    elif bits[1] == 'stars':
        kw = {'user': request.user, 'starred': True}

    if len(bits) > 3 and bits[3] == 'unread':
        kw['read'] = False
        only_unread = True

    # The previous is actually the next by date, and vice versa
    try:
        previous = entry.get_next_by_date(**kw).get_absolute_url()
    except entry.DoesNotExist:
        previous = None
    try:
        next = entry.get_previous_by_date(**kw).get_absolute_url()
    except entry.DoesNotExist:
        next = None

    if request.user.oldest_first:
        previous, next = next, previous

    # if there is an image in the entry, don't show it. We need user
    # intervention to display the image.
    has_media = media_safe = False
    if MEDIA_RE.match(entry.subtitle):
        has_media = True

    if request.method == 'POST':
        form = ActionForm(data=request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            if action == 'images':
                if 'never' in request.POST:
                    entry.feed.img_safe = False
                    entry.feed.save(update_fields=['img_safe'])
                elif 'once' in request.POST:
                    media_safe = True
                elif 'always' in request.POST:
                    entry.feed.img_safe = True
                    entry.feed.save(update_fields=['img_safe'])
            elif action == 'unread':
                entry.read = False
                entry.save(update_fields=['read'])
                entry.feed.update_unread_count()
                return redirect(back_url)
            elif action == 'read_later':
                enqueue(read_later, args=[entry.pk], timeout=20, queue='high')
                messages.success(
                    request,
                    _('Article successfully added to your reading list'),
                )
            elif action in ['star', 'unstar']:
                entry.starred = action == 'star'
                entry.save(update_fields=['starred'])

    context = {
        'category': entry.feed.category,
        'categories': request.user.categories.with_unread_counts(),
        'back_url': back_url,
        'only_unread': only_unread,
        'previous': previous,
        'next': next,
        'has_media': has_media,
        'media_safe': media_safe,
        'object': entry,
    }
    return render(request, 'feeds/entry_detail.html', context)


def truncate(value, length):
    if len(value) > length - 3:
        value = value[:length - 3] + '...'
    return value


def save_outline(user, category, outline, existing):
    count = 0
    try:
        opml_tag = outline._tree.getroot().tag == 'opml'
    except AttributeError:
        opml_tag = False
    if (
        not hasattr(outline, 'xmlUrl') and
        hasattr(outline, 'title') and
        outline._outlines
    ):
        if opml_tag:
            cat = None
            created = False
        else:
            slug = slugify(outline.title)
            if not slug:
                slug = 'unknown'
            title = truncate(outline.title, 1023)
            slug = slug[:50]
            cat, created = user.categories.get_or_create(
                slug=slug, defaults={'name': title},
            )
        for entry in outline._outlines:
            count += save_outline(user, cat, entry, existing)
        if created and cat.feeds.count() == 0:
            cat.delete()

    for entry in outline:
        count += save_outline(user, category, entry, existing)

    if (hasattr(outline, 'xmlUrl')):
        if outline.xmlUrl not in existing:
            existing.add(outline.xmlUrl)
            title = getattr(outline, 'title',
                            getattr(outline, 'text', _('No title')))
            title = truncate(title, 1023)
            user.feeds.create(category=category, url=outline.xmlUrl,
                              name=title)
            count += 1
    return count


@login_required
@transaction.atomic
def import_feeds(request):
    """Import feeds from an OPML source"""
    if request.method == 'POST':
        form = OPMLImportForm(request.POST, request.FILES)
        if form.is_valid():
            # get the list of existing feeds
            existing_feeds = set(request.user.feeds.values_list('url',
                                                                flat=True))

            entries = opml.parse(request.FILES['file'])
            try:
                with user_lock('opml_import', request.user.pk, timeout=30):
                    imported = save_outline(request.user, None, entries,
                                            existing_feeds)
            except ValidationError:
                logger.info("Prevented duplicate import for user {0}".format(
                    request.user.pk))
            else:
                message = " ".join([ungettext(
                    u'%s feed has been imported.',
                    u'%s feeds have been imported.',
                    imported) % imported,
                    _('New content will appear in a moment when you refresh '
                      'the page.')
                ])
                messages.success(request, message)
                return redirect('feeds:home')

    else:
        form = OPMLImportForm()

    context = {
        'form': form,
    }
    return render(request, 'feeds/import_feeds.html', context)


@login_required
def dashboard(request, only_unread=False):
    categories = request.user.categories.prefetch_related(
        'feeds',
    ).annotate(unread_count=Sum('feeds__unread_count'))

    if only_unread:
        categories = categories.filter(unread_count__gt=0)

    if only_unread:
        uncategorized = request.user.feeds.filter(category__isnull=True,
                                                  unread_count__gt=0)
    else:
        uncategorized = request.user.feeds.filter(category__isnull=True)

    has_orphans = bool(len(uncategorized))

    total = len(uncategorized) + sum(
        (len(c.feeds.all()) for c in categories)
    )

    if has_orphans:
        categories = [
            {'feeds': uncategorized}
        ] + list(categories)

    col_size = total / 3
    col_1 = None
    col_2 = None
    done = len(uncategorized)
    for index, cat in enumerate(categories[has_orphans:]):
        if col_1 is None and done > col_size:
            col_1 = index + 1
        if col_2 is None and done > 2 * col_size:
            col_2 = index + 1
        done += len(cat.feeds.all())

    context = {
        'categories': categories,
        'breaks': [col_1, col_2],
        'only_unread': only_unread,
    }
    return render(request, 'feeds/dashboard.html', context)


class Subscribe(generic.FormView):
    form_class = SubscriptionFormSet
    template_name = 'feeds/subscribe.html'

    def get_initial(self):
        urls = [l for l in self.request.GET.get('feeds', '').split(',') if l]
        self.feed_count = len(urls)

        self.existing = self.request.user.feeds.filter(url__in=urls)

        existing_urls = set([e.url for e in self.existing])

        new_urls = [url for url in urls if url not in existing_urls]
        name_prefill = {}
        if new_urls:
            uniques = UniqueFeed.objects.filter(
                url__in=new_urls)
            for unique in uniques:
                name_prefill[unique.url] = unique.job_details.get('title')

        return [{
            'name': name_prefill.get(url),
            'url': url,
            'subscribe': True,
        } for url in new_urls]

    def get_form(self, form_class):
        formset = super(Subscribe, self).get_form(form_class)
        cats = [['', '-----']] + [
            (str(c.pk), c.name) for c in self.request.user.categories.all()
        ]
        for form in formset:
            form.fields['category'].choices = cats
            form.user = self.request.user
        return formset

    def get_context_data(self, **kwargs):
        ctx = super(Subscribe, self).get_context_data(**kwargs)
        ctx['site_url'] = self.request.GET.get('url')
        return ctx

    def form_valid(self, formset):
        created = 0
        for form in formset:
            if form.cleaned_data['subscribe']:
                if form.cleaned_data['category']:
                    category = self.request.user.categories.get(
                        pk=form.cleaned_data['category'],
                    )
                else:
                    category = None
                self.request.user.feeds.create(
                    name=form.cleaned_data['name'],
                    url=form.cleaned_data['url'],
                    category=category,
                )
                created += 1
        if created == 1:
            message = _('1 feed has been added')
        else:
            message = _('%s feeds have been added') % created
        messages.success(self.request, message)
        return redirect(reverse('feeds:home'))
subscribe = login_required(Subscribe.as_view())


class ManageFeeds(generic.TemplateView):
    template_name = 'feeds/manage_feeds.html'

    def get_context_data(self, **kwargs):
        ctx = super(ManageFeeds, self).get_context_data(**kwargs)
        feeds = self.request.user.feeds.select_related('category').order_by(
            'category__name', 'category__id', 'name',
        ).extra(select={
            'muted': """
                select muted from feeds_uniquefeed
                where feeds_uniquefeed.url = feeds_feed.url
            """,
            'error': """
                select muted_reason from feeds_uniquefeed
                where feeds_uniquefeed.url = feeds_feed.url
            """,
        })

        ctx['feeds'] = feeds
        return ctx
manage = login_required(ManageFeeds.as_view())

########NEW FILE########
__FILENAME__ = admin
from ratelimitbackend import admin

from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.utils.translation import ugettext_lazy as _

from .models import User


class ProfileUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


class ProfileUserAdmin(UserAdmin):
    form = ProfileUserChangeForm
    fieldsets = UserAdmin.fieldsets + (
        (_('FeedHQ'), {'fields': ('is_suspended', 'timezone',
                                  'entries_per_page',
                                  'read_later', 'read_later_credentials',
                                  'sharing_twitter', 'sharing_gplus',
                                  'sharing_email', 'ttl')}),
    )
    list_display = ('username', 'email', 'is_staff', 'is_suspended')
    list_filter = UserAdmin.list_filter + ('is_suspended',)


admin.site.register(User, ProfileUserAdmin)

########NEW FILE########
__FILENAME__ = forms
import json
import requests

from requests_oauthlib import OAuth1
from six.moves.urllib import parse as urlparse

from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _

import floppyforms as forms

from ratelimitbackend.forms import AuthenticationForm

from .models import User


class AuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AuthForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = _('Username or Email')


class ProfileForm(forms.ModelForm):
    success_message = _('Your profile was updated successfully')

    class Meta:
        model = User
        fields = ['username', 'timezone', 'entries_per_page', 'font',
                  'endless_pages', 'oldest_first', 'allow_media', 'ttl']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.exclude(pk=self.instance.pk).filter(
            username__iexact=username,
        ).exists():
            raise forms.ValidationError(_('This username is already taken.'))
        return username

    def clean_ttl(self):
        try:
            ttl = int(self.cleaned_data['ttl'])
        except ValueError:
            raise forms.ValidationError(_('Please enter an integer value.'))
        if ttl > 365 or ttl < 2:
            raise forms.ValidationError(
                _('Please enter a value between 2 and 365.'))
        return ttl


class SharingForm(forms.ModelForm):
    success_message = _('Your sharing preferences were updated successfully')

    class Meta:
        model = User
        fields = ['sharing_twitter', 'sharing_gplus', 'sharing_email']


class ChangePasswordForm(forms.Form):
    success_message = _('Your password was changed successfully')
    current_password = forms.CharField(label=_('Current password'),
                                       widget=forms.PasswordInput)
    new_password = forms.CharField(label=_('New password'),
                                   widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_('New password (confirm)'),
                                    widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('instance')
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data['current_password']
        if not self.user.check_password(password):
            raise forms.ValidationError(_('Incorrect password'))
        return password

    def clean_new_password2(self):
        password_1 = self.cleaned_data.get('new_password', '')
        if self.cleaned_data['new_password2'] != password_1:
            raise forms.ValidationError(_("The two passwords didn't match"))
        return password_1

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()


class ServiceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.service = kwargs.pop('service')
        self.request = kwargs.pop('request')
        super(ServiceForm, self).__init__(*args, **kwargs)

    def clean(self):
        getattr(self, 'check_%s' % self.service)()
        return self.cleaned_data

    def save(self):
        self.user.read_later = '' if self.service == 'none' else self.service
        self.user.save()

    def check_none(self):
        self.user.read_later_credentials = ''


class PocketForm(ServiceForm):
    def check_pocket(self):
        url = 'https://getpocket.com/v3/oauth/request'
        redirect_uri = self.request.build_absolute_uri(
            reverse('pocket_return'))
        data = {
            'consumer_key': settings.POCKET_CONSUMER_KEY,
            'redirect_uri': redirect_uri,
        }
        response = requests.post(url, data=json.dumps(data),
                                 headers={'Content-Type': 'application/json',
                                          'X-Accept': 'application/json'})
        print(response, response.text)
        code = response.json()['code']
        self.request.session['pocket_code'] = code
        self.response = redirect(
            'https://getpocket.com/auth/authorize?{0}'.format(
                urlparse.urlencode({'request_token': code,
                                    'redirect_uri': redirect_uri})))


class WallabagForm(ServiceForm):
    url = forms.URLField(
        label=_('Wallabag URL'),
        help_text=_('Your Wallabag URL, e.g. '
                    'https://www.framabag.org/u/username'))

    def check_wallabag(self):
        self.user.read_later_credentials = json.dumps({
            'wallabag_url': self.cleaned_data['url'],
        })


class CredentialsForm(ServiceForm):
    """A form that checks an external service using Basic Auth on a URL"""
    username = forms.CharField(label=_('Username'))
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super(CredentialsForm, self).__init__(*args, **kwargs)
        if self.service == 'instapaper':
            self.fields['username'].help_text = _('Your Instapaper username '
                                                  'is an email address.')

    def check_readitlater(self):
        """Checks that the readitlater credentials are valid"""
        data = self.cleaned_data
        data['apikey'] = settings.API_KEYS['readitlater']
        response = requests.get('https://readitlaterlist.com/v2/auth',
                                params=data)
        if response.status_code != 200:
            raise forms.ValidationError(
                _('Unable to verify your readitlaterlist credentials. Please '
                  'double-check and try again.')
            )
        self.user.read_later_credentials = json.dumps(self.cleaned_data)

    def check_instapaper(self):
        """Get an OAuth token using xAuth from Instapaper"""
        self.check_xauth(
            settings.INSTAPAPER['CONSUMER_KEY'],
            settings.INSTAPAPER['CONSUMER_SECRET'],
            'https://www.instapaper.com/api/1/oauth/access_token',
        )

    def check_readability(self):
        """Get an OAuth token using the Readability API"""
        self.check_xauth(
            settings.READABILITY['CONSUMER_KEY'],
            settings.READABILITY['CONSUMER_SECRET'],
            'https://www.readability.com/api/rest/v1/oauth/access_token/',
        )

    def check_xauth(self, key, secret, token_url):
        """Check a generic xAuth provider"""
        auth = OAuth1(key, secret)
        params = {
            'x_auth_username': self.cleaned_data['username'],
            'x_auth_password': self.cleaned_data['password'],
            'x_auth_mode': 'client_auth',
        }
        response = requests.post(token_url, auth=auth, data=params)
        if response.status_code != 200:
            raise forms.ValidationError(
                _("Unable to verify your %s credentials. Please double-check "
                  "and try again") % self.service,
            )
        request_token = dict(urlparse.parse_qsl(response.text))
        self.user.read_later_credentials = json.dumps(request_token)


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label=_('Password'),
        help_text=_('Please enter your password to confirm your ownership '
                    'of this account.')
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(DeleteAccountForm, self).__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data['password']
        correct = self.user.check_password(password)
        if not correct:
            raise forms.ValidationError(_('The password you entered was '
                                          'incorrect.'))
        return password

    def save(self):
        self.user.delete()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        
    }

    complete_apps = ['profiles']
########NEW FILE########
__FILENAME__ = 0002_auto__add_user
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'User'
        db.create_table('auth_user', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('is_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=75)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=75)),
            ('is_staff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('timezone', self.gf('django.db.models.fields.CharField')(default='UTC', max_length=75)),
            ('entries_per_page', self.gf('django.db.models.fields.IntegerField')(default=50)),
            ('read_later', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('read_later_credentials', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('sharing_twitter', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('sharing_gplus', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('sharing_email', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'profiles', ['User'])

        # Adding M2M table for field groups on 'User'
        m2m_table_name = db.shorten_name('auth_user_groups')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'profiles.user'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'User'
        m2m_table_name = db.shorten_name('auth_user_user_permissions')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('user', models.ForeignKey(orm[u'profiles.user'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique(m2m_table_name, ['user_id', 'permission_id'])


    def backwards(self, orm):
        assert False


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_user_allow_media
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'User.allow_media'
        db.add_column('auth_user', 'allow_media',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'User.allow_media'
        db.delete_column('auth_user', 'allow_media')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_user_oldest_first
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'User.oldest_first'
        db.add_column('auth_user', 'oldest_first',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'User.oldest_first'
        db.delete_column('auth_user', 'oldest_first')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']
########NEW FILE########
__FILENAME__ = 0005_auto__add_field_user_is_suspended
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'User.is_suspended'
        db.add_column('auth_user', 'is_suspended',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'User.is_suspended'
        db.delete_column('auth_user', 'is_suspended')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_user_font
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'User.font'
        db.add_column('auth_user', 'font',
                      self.gf('django.db.models.fields.CharField')(default='palatino', max_length=75),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'User.font'
        db.delete_column('auth_user', 'font')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'font': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '75'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_user_endless_pages
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'User.endless_pages'
        db.add_column('auth_user', 'endless_pages',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'User.endless_pages'
        db.delete_column('auth_user', 'endless_pages')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'endless_pages': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']
########NEW FILE########
__FILENAME__ = 0008_auto__add_field_user_ttl
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'User.ttl'
        db.add_column('auth_user', 'ttl',
                      self.gf('django.db.models.fields.PositiveIntegerField')(null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'User.ttl'
        db.delete_column('auth_user', 'ttl')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'endless_pages': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'font': ('django.db.models.fields.CharField', [], {'default': "'pt-serif'", 'max_length': '75'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'ttl': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']

########NEW FILE########
__FILENAME__ = 0009_auto__add_index_user_is_suspended
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'User', fields ['is_suspended']
        db.commit_transaction()
        db.execute('CREATE INDEX CONCURRENTLY "auth_user_is_suspended" ON '
                   '"auth_user" ("is_suspended")')
        db.start_transaction()

    def backwards(self, orm):
        # Removing index on 'User', fields ['is_suspended']
        db.delete_index('auth_user', ['is_suspended'])

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'endless_pages': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'font': ('django.db.models.fields.CharField', [], {'default': "'pt-serif'", 'max_length': '75'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'ttl': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']

########NEW FILE########
__FILENAME__ = 0010_auto__chg_field_user_ttl
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'User.ttl'
        db.alter_column('auth_user', 'ttl', self.gf('django.db.models.fields.PositiveIntegerField')(default=365))

    def backwards(self, orm):

        # Changing field 'User.ttl'
        db.alter_column('auth_user', 'ttl', self.gf('django.db.models.fields.PositiveIntegerField')(null=True))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'endless_pages': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'font': ('django.db.models.fields.CharField', [], {'default': "'pt-serif'", 'max_length': '75'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_suspended': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'ttl': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        }
    }

    complete_apps = ['profiles']
########NEW FILE########
__FILENAME__ = models
import json
import pytz

from django.contrib.auth.models import (AbstractBaseUser, UserManager,
                                        PermissionsMixin)
from django.db import models
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from ..utils import get_redis_connection

TIMEZONES = [
    (tz, _(tz)) for tz in pytz.common_timezones
]

ENTRIES_PER_PAGE = (
    (25, 25),
    (50, 50),
    (100, 100),
)


class User(PermissionsMixin, AbstractBaseUser):
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    NONE = ''
    READABILITY = 'readability'
    READITLATER = 'readitlater'
    INSTAPAPER = 'instapaper'
    WALLABAG = 'wallabag'
    POCKET = 'pocket'
    READ_LATER_SERVICES = (
        (NONE, _('None')),
        (READABILITY, u'Readability'),
        (READITLATER, u'Read it later'),
        (INSTAPAPER, u'Instapaper'),
        (WALLABAG, u'Wallabag'),
        (POCKET, u'Pocket'),
    )

    FONT_DROID_SANS = 'droid-sans'
    FONT_DROID_SERIF = 'droid-serif'
    FONT_GENTIUM_BASIC = 'gentium-basic'
    FONT_MERRIWEATHER = 'merriweather'
    FONT_PALATINO = 'palatino'
    FONT_POLY = 'poly'
    FONT_PT_SERIF = 'pt-serif'
    FONT_ABEL = 'abel'
    FONT_HELVETICA = 'helvetica'
    FONT_MULI = 'muli'
    FONT_OPEN_SANS = 'open-sans'
    FONT_PT_SANS = 'pt-sans'
    FONT_UBUNTU_CONDENSED = 'ubuntu-condensed'
    FONT_SOURCE_SANS_PRO = 'source-sans-pro'

    FONTS = (
        (
            _('Serif'), (
                (FONT_DROID_SERIF, 'Droid Serif'),
                (FONT_GENTIUM_BASIC, 'Gentium Basic'),
                (FONT_MERRIWEATHER, 'Merriweather'),
                (FONT_PALATINO, _('Palatino (system font)')),
                (FONT_POLY, 'Poly'),
                (FONT_PT_SERIF, 'PT Serif'),
            )
        ), (
            _('Sans Serif'), (
                (FONT_ABEL, 'Abel'),
                (FONT_DROID_SANS, 'Droid Sans'),
                (FONT_HELVETICA, _('Helvetica (system font)')),
                (FONT_MULI, 'Muli'),
                (FONT_OPEN_SANS, 'Open Sans'),
                (FONT_PT_SANS, 'PT Sans'),
                (FONT_UBUNTU_CONDENSED, 'Ubuntu Condensed'),
                (FONT_SOURCE_SANS_PRO, 'Source Sans Pro'),
            )
        )
    )

    username = models.CharField(max_length=75, unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.CharField(max_length=75)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False, db_index=True)
    date_joined = models.DateTimeField(default=timezone.now)
    timezone = models.CharField(_('Time zone'), max_length=75,
                                choices=TIMEZONES, default='UTC')
    entries_per_page = models.IntegerField(_('Entries per page'), default=50,
                                           choices=ENTRIES_PER_PAGE)
    endless_pages = models.BooleanField(
        _('Endless pages'), default=True,
        help_text=_("Check this box if you'd like to use a 'load more' "
                    "button instead of the page links."))

    oldest_first = models.BooleanField(
        _('Oldest entries first'), default=False,
        help_text=_("Check this box if you'd like to have the oldest "
                    "entries appear first."))
    read_later = models.CharField(_('Read later service'), blank=True,
                                  choices=READ_LATER_SERVICES, max_length=50)
    read_later_credentials = models.TextField(_('Read later credentials'),
                                              blank=True)

    sharing_twitter = models.BooleanField(_('Enable tweet button'),
                                          default=False)
    sharing_gplus = models.BooleanField(_('Enable +1 button (Google+)'),
                                        default=False)
    sharing_email = models.BooleanField(_('Enable Mail button'), default=False)

    allow_media = models.BooleanField(_('Automatically allow external media'),
                                      default=False)

    font = models.CharField(
        _('Text font'), max_length=75, choices=FONTS, default=FONT_PT_SERIF,
        help_text=_('Non-system fonts are served by Google Web Fonts.'),
    )

    ttl = models.PositiveIntegerField(
        _('Retention days'), default=30,
        help_text=_('Number of days after which entries are deleted. The more '
                    'history you keep, the less snappy FeedHQ becomes.'))

    objects = UserManager()

    class Meta:
        db_table = 'auth_user'

    def get_short_name(self):
        return self.username

    @property
    def last_update_key(self):
        return 'user:{0}:updates'.format(self.pk)

    @property
    def wallabag_url(self):
        return json.loads(self.read_later_credentials)['wallabag_url']

    def last_updates(self):
        redis = get_redis_connection()
        values = redis.zrange(self.last_update_key, 0, 10**11, withscores=True)
        updates = {}
        for url, timestamp in values:
            updates[url.decode('utf-8')] = int(timestamp)
        return updates

    def refresh_updates(self):
        redis = get_redis_connection()
        last_updates = self.last_updates()
        urls = self.feeds.values_list('pk', 'url')
        for pk, url in urls:
            if url in last_updates:
                continue
            value = self.entries.filter(feed_id=pk).aggregate(
                date=Max('date'))['date']
            value = float(value.strftime('%s')) if value else 0
            redis.zadd(self.last_update_key, url, value)
        return self.last_updates()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns, include

from . import views

urlpatterns = patterns(
    '',
    url(r'^stats/$', views.stats, name='stats'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^sharing/$', views.sharing, name='sharing'),
    url(r'^bookmarklet/$', views.bookmarklet, name='bookmarklet'),
    url(r'^password/$', views.password, name='password'),
    url(r'^export/$', views.export, name='export'),
    url(r'^readlater/(?P<service>readability|readitlater|instapaper|'
        r'pocket|wallabag|none)/$',
        views.services, name='services'),
    url(r'^readlater/pocket/return/$', views.pocket, name='pocket_return'),
    url(r'^readlater/$', views.read_later, name='read_later'),
    url(r'^destroy/$', views.destroy, name='destroy_account'),
    url(r'^destroy/done/$', views.destroy_done, name='destroy_done'),
    url(r'^recover/$', views.recover, name='password_reset_recover'),
    url(r'^', include('password_reset.urls')),
)

########NEW FILE########
__FILENAME__ = views
import json
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.sites.models import RequestSite
from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.views import generic

from password_reset import views

from .forms import (ChangePasswordForm, ProfileForm, CredentialsForm,
                    ServiceForm, WallabagForm, DeleteAccountForm, SharingForm,
                    PocketForm)
from ..decorators import login_required


class UserMixin(object):
    success_url = reverse_lazy('profile')

    def get_object(self):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super(UserMixin, self).get_form_kwargs()
        kwargs.update({
            'instance': self.request.user,
        })
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, form.success_message)
        return super(UserMixin, self).form_valid(form)


class Stats(UserMixin, generic.DetailView):
    def get_context_data(self, **kwargs):
        ctx = super(Stats, self).get_context_data(**kwargs)
        ctx.update({
            'categories': self.request.user.categories.count(),
            'feeds': self.request.user.feeds.count(),
            'entries': self.request.user.entries.count(),
        })
        return ctx
stats = login_required(Stats.as_view())


class ReadLater(UserMixin, generic.TemplateView):
    template_name = 'profiles/read_later.html'
read_later = login_required(ReadLater.as_view())


class PasswordView(UserMixin, generic.FormView):
    template_name = 'profiles/change_password.html'
    form_class = ChangePasswordForm
password = login_required(PasswordView.as_view())


class ProfileView(UserMixin, generic.FormView):
    form_class = ProfileForm
    template_name = 'profiles/edit_profile.html'

    def get_initial(self):
        return {'ttl': self.request.user.ttl or 365}
profile = login_required(ProfileView.as_view())


class Sharing(UserMixin, generic.FormView):
    form_class = SharingForm
    template_name = 'profiles/sharing.html'
    success_url = reverse_lazy('sharing')
sharing = login_required(Sharing.as_view())


class Export(UserMixin, generic.TemplateView):
    template_name = 'profiles/export.html'
export = login_required(Export.as_view())


class ServiceView(generic.FormView):
    FORMS = {
        'readability': CredentialsForm,
        'readitlater': CredentialsForm,
        'instapaper': CredentialsForm,
        'pocket': PocketForm,
        'wallabag': WallabagForm,
        'none': ServiceForm,
    }
    success_url = reverse_lazy('read_later')

    def get_template_names(self):
        return ['profiles/services/%s.html' % self.kwargs['service']]

    def get_form_kwargs(self):
        kwargs = super(ServiceView, self).get_form_kwargs()
        kwargs.update({
            'request': self.request,
            'user': self.request.user,
            'service': self.kwargs['service'],
        })
        return kwargs

    def get_form_class(self):
        return self.FORMS[self.kwargs['service']]

    def form_valid(self, form):
        form.save()
        if hasattr(form, 'response'):
            return form.response
        if form.user.read_later:
            messages.success(
                self.request,
                _('You have successfully added %s as your reading list '
                  'service.') % form.user.get_read_later_display(),
            )
        else:
            messages.success(
                self.request,
                _('You have successfully disabled reading list integration.'),
            )
        return super(ServiceView, self).form_valid(form)
services = login_required(ServiceView.as_view())


class PocketReturn(generic.RedirectView):
    def get_redirect_url(self):
        response = requests.post(
            'https://getpocket.com/v3/oauth/authorize',
            data=json.dumps({'consumer_key': settings.POCKET_CONSUMER_KEY,
                             'code': self.request.session['pocket_code']}),
            headers={'Content-Type': 'application/json',
                     'X-Accept': 'application/json'})
        self.request.user.read_later_credentials = json.dumps(response.json())
        self.request.user.read_later = self.request.user.POCKET
        self.request.user.save(update_fields=['read_later',
                                              'read_later_credentials'])
        del self.request.session['pocket_code']
        messages.success(
            self.request,
            _('You have successfully added Pocket as your reading list '
              'service.'))
        return reverse('read_later')
pocket = PocketReturn.as_view()


class Recover(views.Recover):
    search_fields = ['email']
recover = Recover.as_view()


class Destroy(generic.FormView):
    success_url = reverse_lazy('destroy_done')
    form_class = DeleteAccountForm
    template_name = 'profiles/user_confirm_delete.html'

    def get_form_kwargs(self):
        kwargs = super(Destroy, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return redirect(self.get_success_url())
destroy = login_required(Destroy.as_view())


class DestroyDone(generic.TemplateView):
    template_name = 'profiles/account_delete_done.html'
destroy_done = DestroyDone.as_view()


class Bookmarklet(generic.TemplateView):
    template_name = 'profiles/bookmarklet.html'

    def get_context_data(self, **kwargs):
        ctx = super(Bookmarklet, self).get_context_data(**kwargs)
        ctx['site'] = RequestSite(self.request)
        ctx['scheme'] = 'https' if self.request.is_secure() else 'http'
        return ctx
bookmarklet = login_required(Bookmarklet.as_view())

########NEW FILE########
__FILENAME__ = admin
from ratelimitbackend import admin

from .models import AuthToken


class AuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_created', 'preview', 'user_pk',
                    'cache_value')
    raw_id_fields = ('user',)
    list_filter = ['client']

admin.site.register(AuthToken, AuthTokenAdmin)

########NEW FILE########
__FILENAME__ = api_urls
from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^token$', views.token, name='token'),

    url(r'^user-info$', views.user_info, name='user_info'),

    url(r'^unread-count$', views.unread_count, name='unread_count'),

    url(r'^disable-tag$', views.disable_tag, name='disable_tag'),

    url(r'^rename-tag$', views.rename_tag, name='rename_tag'),

    url(r'^subscription/list$', views.subscription_list,
        name='subscription_list'),

    url(r'^subscription/edit$', views.edit_subscription,
        name='subscription_edit'),

    url(r'^subscription/quickadd$', views.quickadd_subscription,
        name='subscription_quickadd'),

    url(r'^subscription/export$', views.export_subscriptions,
        name='subscription_export'),

    url(r'^subscription/import$', views.import_subscriptions,
        name='subscription_import'),

    url(r'^subscribed$', views.subscribed, name='subscribed'),

    url(r'^stream/contents/(?P<content_id>.+)?$', views.stream_contents,
        name='stream_contents'),

    url(r'^stream/items/ids$', views.stream_items_ids,
        name='stream_items_ids'),

    url(r'^stream/items/count$', views.stream_items_count,
        name='stream_items_count'),

    url(r'^stream/items/contents$', views.stream_items_contents,
        name='stream_items_contents'),

    url(r'^tag/list$', views.tag_list,
        name='tag_list'),

    url(r'^edit-tag$', views.edit_tag,
        name='edit_tag'),

    url(r'^mark-all-as-read$', views.mark_all_as_read,
        name='mark_all_as_read'),

    url(r'^preference/list$', views.preference_list, name='preference_list'),

    url(r'^preference/stream/list$', views.stream_preference,
        name='stream_preference'),

    url(r'^friend/list$', views.friend_list, name='friend_list'),
)

"""
Missing URLS:

    /related/list

    /stream
        /details

    /item
        /edit
        /delete
        /likers

    /friend
        /groups
        /acl
        /edit
        /feeds

    /people
        /search
        /suggested
        /profile

    /comment/edit
    /conversation/edit
    /shorten-url

    /preference
        /set
        /stream/set

    /search/items/ids

    /recommendation
        /edit
        /list

    /list-user-bundle
    /edit-bundle
    /get-bundle
    /delete-bundle
    /bundles
    /list-friends-bundle
    /list-featured-bundle
"""

########NEW FILE########
__FILENAME__ = authentication
from django.core.cache import cache
from rest_framework.authentication import (BaseAuthentication,
                                           get_authorization_header)

from ..profiles.models import User
from .exceptions import PermissionDenied
from .models import check_auth_token


class GoogleLoginAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return 'GoogleLogin'

    def authenticate(self, request):
        """GoogleLogin auth=<token>"""
        auth = get_authorization_header(request).decode('utf-8').split()

        if not auth or auth[0].lower() != 'googlelogin':
            raise PermissionDenied()

        if len(auth) == 1:
            raise PermissionDenied()

        if not auth[1].startswith('auth='):
            raise PermissionDenied()

        token = auth[1].split('auth=', 1)[1]
        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        user_id = check_auth_token(token)
        if user_id is False:
            raise PermissionDenied()
        cache_key = 'reader_user:{0}'.format(user_id)
        user = cache.get(cache_key)
        if user is None:
            try:
                user = User.objects.get(pk=user_id, is_active=True)
            except User.DoesNotExist:
                raise PermissionDenied()
            cache.set(cache_key, user, 5*60)
        return user, token

########NEW FILE########
__FILENAME__ = exceptions
from rest_framework import exceptions, status


class ReaderException(exceptions.APIException):
    pass


class PermissionDenied(ReaderException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Error=BadAuthentication'


class BadToken(ReaderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid POST token'

########NEW FILE########
__FILENAME__ = delete_expired_tokens
from datetime import timedelta

from django.utils import timezone

from ...models import AuthToken, AUTH_TOKEN_DAYS
from ....feeds.management.commands import SentryCommand


class Command(SentryCommand):
    """Updates the users' feeds"""

    def handle_sentry(self, *args, **kwargs):
        threshold = timezone.now() - timedelta(days=AUTH_TOKEN_DAYS)
        AuthToken.objects.filter(date_created__lte=threshold).delete()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AuthToken'
        db.create_table(u'reader_authtoken', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='auth_tokens', to=orm['auth.User'])),
            ('token', self.gf('django.db.models.fields.CharField')(default=u'VQnsWk6jSERysKWsV9iuzkcDIw28Qb4tapRkKSppUDMkSO1m1xJOFhVinPWqCWkF6XmlY0ETCAhuj3rK0KnnSKoLlHxYprrh6yrVBnQkbKWz4I6ha36GgJkrM6oiPYV5CJvdsVRPz2RMg5gBDAkfm86OYqZOX0Lsb0CtHW0pR7MIEHcrc0FXDdNJwMVjfZi0DqNucGXwvfxP4dUTHpu3e3i9fuUfVbMvh6ugfMR0md0bbieVU71WfLzNX1rQC1ODxw9Px7QLi3w', max_length=300, db_index=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'reader', ['AuthToken'])


    def backwards(self, orm):
        # Deleting model 'AuthToken'
        db.delete_table(u'reader_authtoken')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'reader.authtoken': {
            'Meta': {'object_name': 'AuthToken'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'default': "u'VQnsWk6jSERysKWsV9iuzkcDIw28Qb4tapRkKSppUDMkSO1m1xJOFhVinPWqCWkF6XmlY0ETCAhuj3rK0KnnSKoLlHxYprrh6yrVBnQkbKWz4I6ha36GgJkrM6oiPYV5CJvdsVRPz2RMg5gBDAkfm86OYqZOX0Lsb0CtHW0pR7MIEHcrc0FXDdNJwMVjfZi0DqNucGXwvfxP4dUTHpu3e3i9fuUfVbMvh6ugfMR0md0bbieVU71WfLzNX1rQC1ODxw9Px7QLi3w'", 'max_length': '300', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'auth_tokens'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['reader']
########NEW FILE########
__FILENAME__ = 0002_auto__add_unique_authtoken_token
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'AuthToken', fields ['token']
        db.create_unique(u'reader_authtoken', ['token'])


    def backwards(self, orm):
        # Removing unique constraint on 'AuthToken', fields ['token']
        db.delete_unique(u'reader_authtoken', ['token'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'reader.authtoken': {
            'Meta': {'object_name': 'AuthToken'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'default': "u'KnXZU6XVslJJBRBi3dniQqNzGBxgaGanUS9xBtDOuEolrUtaSOqK06qsDKa7LgmOOpYHc4HGf8dTpgTdsoRc62duPArLk9AJeYCfnsEJFdo3lyer1mAxwZeetCKXsIrIT0gdPtnDEy8CUVUILGaOE76jrU9yxxOmhPuRStxbquRQ3xC34gPIz84vE4HcSkIzq6e0uvUYgglKMWEgmVQrebubRNnUCx2mO8kT4v9d5mEYRgN301XtRjQIIHy3NqJMj811GpqDOVP'", 'unique': 'True', 'max_length': '300', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'auth_tokens'", 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['reader']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_authtoken_client__add_field_authtoken_user_agent__chg_
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'AuthToken.client'
        db.add_column(u'reader_authtoken', 'client',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=1023, blank=True),
                      keep_default=False)

        # Adding field 'AuthToken.user_agent'
        db.add_column(u'reader_authtoken', 'user_agent',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


        # Changing field 'AuthToken.user'
        db.alter_column(u'reader_authtoken', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['profiles.User']))

    def backwards(self, orm):
        # Deleting field 'AuthToken.client'
        db.delete_column(u'reader_authtoken', 'client')

        # Deleting field 'AuthToken.user_agent'
        db.delete_column(u'reader_authtoken', 'user_agent')


        # Changing field 'AuthToken.user'
        db.alter_column(u'reader_authtoken', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User']))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'"},
            'allow_media': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'entries_per_page': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'oldest_first': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'read_later': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'read_later_credentials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sharing_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_gplus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sharing_twitter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timezone': ('django.db.models.fields.CharField', [], {'default': "'UTC'", 'max_length': '75'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75'})
        },
        u'reader.authtoken': {
            'Meta': {'ordering': "('-date_created',)", 'object_name': 'AuthToken'},
            'client': ('django.db.models.fields.CharField', [], {'max_length': '1023', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'default': "u'x6zQyPtU4lYXTuplsLR57NBTWhjct4suFbUgGlPOfmCFFE1dcuAdazhrOYWNWn91AanAMrRrpozrLIsM6LlZK0Ho0VdhhLWnxXRSfnqz7bkHOzB0hdLfogjnpYTyB2cUTV94dRnQB0TS7CXSy4uAH90mVLBQ0MOqnGR216yjJmGTc4EL1Sow9FJxaW3Fi9SL3dyIudbSvrrByzL43SVL51qKeCfSAMs8CpwVNPSvCjwLblE42B2bcI8cX3sL9SzIfO7rRW9cUiH'", 'unique': 'True', 'max_length': '300', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'auth_tokens'", 'to': u"orm['profiles.User']"}),
            'user_agent': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['reader']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


POST_TOKEN_DURATION = 60 * 30  # 30 minutes
AUTH_TOKEN_DAYS = 7  # 1 week
AUTH_TOKEN_TIMEOUT = 3600 * 24 * AUTH_TOKEN_DAYS

AUTH_TOKEN_LENGTH = 267
POST_TOKEN_LENGTH = 57


def check_auth_token(token):
    key = 'reader_auth_token:{0}'.format(token)
    value = cache.get(key)
    if value is None:
        try:
            token = AuthToken.objects.get(token=token)
        except AuthToken.DoesNotExist:
            return False
        value = token.user_id
        cache.set(key, value, AUTH_TOKEN_TIMEOUT)
    return int(value)


def check_post_token(token):
    key = 'reader_post_token:{0}'.format(token)
    value = cache.get(key)
    if value is None:
        return False
    return int(value)


def generate_auth_token(user, client='', user_agent=''):
    token = user.auth_tokens.create(client=client, user_agent=user_agent)
    key = 'reader_auth_token:{0}'.format(token.token)
    cache.set(key, user.pk, AUTH_TOKEN_TIMEOUT)
    return token.token


def generate_post_token(user):
    token = get_random_string(POST_TOKEN_LENGTH)
    key = 'reader_post_token:{0}'.format(token)
    cache.set(key, user.pk, POST_TOKEN_DURATION)
    return token


@python_2_unicode_compatible
class AuthToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'),
                             related_name='auth_tokens')
    token = models.CharField(
        _('Token'), max_length=300, db_index=True, unique=True,
        default=lambda: get_random_string(AUTH_TOKEN_LENGTH))
    date_created = models.DateTimeField(_('Creation date'),
                                        default=timezone.now)
    client = models.CharField(_('Client'), max_length=1023, blank=True)
    user_agent = models.TextField(_('User-Agent'), blank=True)

    def __str__(self):
        return u'Token for {0}'.format(self.user)

    class Meta:
        ordering = ('-date_created',)

    def delete(self):
        super(AuthToken, self).delete()
        cache.delete(self.cache_key)

    @property
    def cache_key(self):
        return 'reader_auth_token:{0}'.format(self.token)

    @property
    def user_pk(self):
        return self.user_id

    @property
    def cache_value(self):
        return cache.get(self.cache_key)

    @property
    def preview(self):
        return u'{0}…'.format(self.token[:8])

########NEW FILE########
__FILENAME__ = renderers
import datetime
import six

from django.utils.xmlutils import SimplerXMLGenerator
from rest_framework.compat import StringIO
from rest_framework.renderers import BaseRenderer, XMLRenderer


def timestamp_to_iso(value):
    return datetime.datetime.fromtimestamp(
        value).strftime("%Y-%m-%dT%H:%M:%SZ")


class PlainRenderer(BaseRenderer):
    media_type = 'text/plain'
    format = '*'

    def render(self, data, *args, **kwargs):
        if (isinstance(data, dict) and list(data.keys()) == ['detail']):
            return data['detail']
        return data


class BaseXMLRenderer(XMLRenderer):
    strip_declaration = True

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return ''

        stream = StringIO()
        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()

        self._to_xml(xml, data)

        xml.endDocument()
        response = stream.getvalue()

        if self.strip_declaration:
            declaration = '<?xml version="1.0" encoding="utf-8"?>'
            if response.startswith(declaration):
                response = response[len(declaration):]
        return response.strip()


class GoogleReaderXMLRenderer(BaseXMLRenderer):
    def _to_xml(self, xml, data):
        """
        Renders *data* into serialized XML, google-reader style.
        """
        if isinstance(data, dict) and data:
            xml.startElement("object", {})
            for key, value in data.items():
                if isinstance(value, six.string_types) and value.isdigit():
                    value = int(value)
                if isinstance(value, (list, tuple)):
                    xml.startElement("list", {'name': key})
                    for item in value:
                        self._to_xml(xml, item)
                    xml.endElement("list")
                elif isinstance(value, int):
                    xml.startElement("number", {'name': key})
                    xml.characters(str(value))
                    xml.endElement("number")
                elif isinstance(value, six.string_types):
                    xml.startElement("string", {'name': key})
                    xml.characters(value)
                    xml.endElement("string")
                elif isinstance(value, dict):
                    xml.startElement("object", {'name': key})
                    self._to_xml(xml, value)
                    xml.endElement("object")
            xml.endElement("object")
        elif data == {}:
            pass
        elif isinstance(data, six.string_types):
            xml.startElement("string", {})
            xml.characters(data)
            xml.endElement("string")
        else:  # Unhandled case
            assert False, data


class AtomRenderer(BaseXMLRenderer):
    media_type = 'text/xml'
    format = 'atom'
    strip_declaration = False

    def _to_xml(self, xml, data):
        if list(data.keys()) == ['detail']:
            xml.startElement('error', {})
            xml.characters(data['detail'])
            xml.endElement('error')
            return
        xml.startElement('feed', {
            'xmlns:media': 'http://search.yahoo.com/mrss/',
            'xmlns:gr': 'http://www.google.com/schemas/reader/atom/',
            'xmlns:idx': 'urn:atom-extension:indexing',
            'xmlns': 'http://www.w3.org/2005/Atom',
            'idx:index': 'no',
            'gr:dir': data['direction'],
        })

        xml.startElement('generator', {'uri': 'https://feedhq.org'})
        xml.characters('FeedHQ')
        xml.endElement('generator')

        xml.startElement('id', {})
        xml.characters(u'tag:google.com,2005:reader/{0}'.format(data['id']))
        xml.endElement('id')

        xml.startElement('title', {})
        xml.characters(data['title'])
        xml.endElement('title')

        if 'continuation' in data:
            xml.startElement('gr:continuation', {})
            xml.characters(data['continuation'])
            xml.endElement('gr:continuation')

        xml.startElement('link', {'rel': 'self',
                                  'href': data['self'][0]['href']})
        xml.endElement('link')

        if 'alternate' in data:
            xml.startElement('link', {'rel': 'alternate', 'type': 'text/html',
                                      'href': data['alternate'][0]['href']})
            xml.endElement('link')

        xml.startElement('updated', {})
        xml.characters(timestamp_to_iso(data['updated']))
        xml.endElement('updated')

        for entry in data['items']:
            xml.startElement('entry', {
                'gr:crawl-timestamp-msec': entry['crawlTimeMsec']})

            xml.startElement('id', {})
            xml.characters(entry['id'])
            xml.endElement('id')

            for category in entry['categories']:
                xml.startElement('category', {
                    'term': category,
                    'scheme': 'http://www.google.com/reader/',
                    'label': category.rsplit('/', 1)[1]})
                xml.endElement('category')

            xml.startElement('title', {'type': 'html'})
            xml.characters(entry['title'])
            xml.endElement('title')

            xml.startElement('published', {})
            xml.characters(timestamp_to_iso(entry['updated']))
            xml.endElement('published')

            xml.startElement('updated', {})
            xml.characters(timestamp_to_iso(entry['updated']))
            xml.endElement('updated')

            xml.startElement('link', {'rel': 'alternate', 'type': 'text/html',
                                      'href': entry['alternate'][0]['href']})
            xml.endElement('link')

            xml.startElement('content',
                             {'type': 'html',
                              'xml:base': entry['origin']['htmlUrl']})
            xml.characters(entry['content']['content'])
            xml.endElement('content')

            if entry.get('author'):
                xml.startElement('author', {})
                xml.startElement('name', {})
                xml.characters(entry['author'])
                xml.endElement('name')
                xml.endElement('author')

            xml.startElement('source', {
                'gr:stream-id': entry['origin']['streamId']})

            xml.startElement('id', {})
            xml.characters(entry['id'])
            xml.endElement('id')

            xml.startElement('title', {'type': 'html'})
            xml.characters(entry['origin']['title'])
            xml.endElement('title')

            xml.startElement('link', {'rel': 'alternate',
                                      'type': 'text/html',
                                      'href': entry['origin']['htmlUrl']})
            xml.endElement('link')
            xml.endElement('source')

            xml.endElement('entry')

        xml.endElement('feed')


class AtomHifiRenderer(AtomRenderer):
    format = 'atom-hifi'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include

from . import views


urlpatterns = patterns(
    '',
    url(r'^accounts/ClientLogin$', views.login, name='login'),
    url(r'^reader/api/0/', include('feedhq.reader.api_urls')),
    url(r'^reader/atom/(?P<content_id>.+)?$', views.stream_contents,
        {'output': 'atom'}, name='atom_contents'),

)

########NEW FILE########
__FILENAME__ = views
import json
import logging
import re
import struct

from datetime import timedelta

import opml

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Sum, Q
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from lxml.etree import XMLSyntaxError

from rest_framework import exceptions
from rest_framework.authentication import SessionAuthentication
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.parsers import XMLParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from six.moves.urllib import parse as urlparse

from ..feeds.forms import FeedForm, user_lock
from ..feeds.models import Feed, UniqueFeed, Category
from ..feeds.utils import epoch_to_utc
from ..feeds.views import save_outline
from ..profiles.models import User
from ..utils import is_email
from .authentication import GoogleLoginAuthentication
from .exceptions import PermissionDenied, BadToken
from .models import generate_auth_token, generate_post_token, check_post_token
from .renderers import (PlainRenderer, GoogleReaderXMLRenderer, AtomRenderer,
                        AtomHifiRenderer)


logger = logging.getLogger(__name__)

MISSING_SLASH_RE = re.compile("^(https?:\/)[^\/]")


def item_id(value):
    """
    Converts an input to a proper (integer) item ID.
    """
    if value.startswith('tag:google.com'):
        try:
            value = int(value.split('/')[-1], 16)
            value = struct.unpack("l", struct.pack("L", value))[0]
        except (ValueError, IndexError):
            raise exceptions.ParseError(
                "Unrecognized item. Must be of the form "
                "'tag:google.com,2005:reader/item/<item_id>'")
    elif value.isdigit():
        value = int(value)
    else:
        raise exceptions.ParseError(
            "Unrecognized item. Must be of the form "
            "'tag:google.com,2005:reader/item/<item_id>'")
    return value


def tag_value(tag):
    try:
        return tag.rsplit('/', 1)[1]
    except IndexError:
        raise exceptions.ParseError(
            "Bad tag format. Must be of the form "
            "'user/-/state/com.google/<tag>'. Allowed tags: 'read', "
            "'kept-unread', 'starred', 'broadcast'.")


def is_stream(value, user_id):
    stream_prefix = "user/-/state/com.google/"
    stream_user_prefix = "user/{0}/state/com.google/".format(user_id)
    if value.startswith((stream_prefix, stream_user_prefix)):
        if value.startswith(stream_prefix):
            prefix = stream_prefix
        else:
            prefix = stream_user_prefix
        return value[len(prefix):]
    return False


def is_label(value, user_id):
    label_prefix = "user/-/label/"
    label_user_prefix = "user/{0}/label/".format(user_id)
    if value.startswith((label_prefix, label_user_prefix)):
        if value.startswith(label_prefix):
            prefix = label_prefix
        else:
            prefix = label_user_prefix
        return value[len(prefix):]
    return False


def feed_url(stream):
    url = stream[len('feed/'):]
    missing_slash = MISSING_SLASH_RE.match(url)
    if missing_slash:
        start = missing_slash.group(1)
        url = u'{0}/{1}'.format(start, url[len(start):])
    return url


class ForceNegotiation(DefaultContentNegotiation):
    """
    Forces output even if ?output= is wrong when we have
    only one renderer.
    """
    def __init__(self, force_format=None):
        self.force_format = force_format
        super(ForceNegotiation, self).__init__()

    def select_renderer(self, request, renderers, format_suffix=None):
        if self.force_format is not None:
            format_suffix = self.force_format
        return super(ForceNegotiation, self).select_renderer(
            request, renderers, format_suffix)

    def filter_renderers(self, renderers, format):
        if len(renderers) == 1:
            return renderers
        renderers = [r for r in renderers if r.format == format]
        if not renderers:
            raise Http404
        return renderers


class Login(APIView):
    http_method_names = ['get', 'post']
    renderer_classes = [PlainRenderer]

    def handle_exception(self, exc):
        if isinstance(exc, PermissionDenied):
            return Response(exc.detail, status=exc.status_code)
        return super(Login, self).handle_exception(exc)

    def initial(self, request, *args, **kwargs):
        if request.method == 'POST':
            querydict = request.DATA
        elif request.method == 'GET':
            querydict = request.GET
        if 'Email' not in querydict or 'Passwd' not in querydict:
            raise PermissionDenied()
        self.querydict = querydict

    def post(self, request, *args, **kwargs):
        if is_email(self.querydict['Email']):
            clause = Q(email__iexact=self.querydict['Email'])
        else:
            clause = Q(username__iexact=self.querydict['Email'])
        clause = clause & Q(is_active=True)
        try:
            user = User.objects.get(clause)
        except User.DoesNotExist:
            raise PermissionDenied()
        if not user.check_password(self.querydict['Passwd']):
            raise PermissionDenied()
        client = request.GET.get('client', request.DATA.get('client', ''))
        token = generate_auth_token(
            user,
            client=client,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        return Response("SID={t}\nLSID={t}\nAuth={t}".format(t=token))
    get = post
login = Login.as_view()


class ReaderView(APIView):
    authentication_classes = [SessionAuthentication,
                              GoogleLoginAuthentication]
    renderer_classes = [JSONRenderer, GoogleReaderXMLRenderer]
    content_negotiation_class = ForceNegotiation
    require_post_token = True

    def initial(self, request, *args, **kwargs):
        super(ReaderView, self).initial(request, *args, **kwargs)
        if request.method == 'POST' and self.require_post_token:
            token = request.DATA.get('T', request.GET.get('T', None))
            if token is None:
                logger.info(
                    u"Missing POST token, {0}".format(request.DATA.dict())
                )
                raise exceptions.ParseError("Missing 'T' POST token")
            user_id = check_post_token(token)
            if not user_id == request.user.pk:
                raise BadToken

    def handle_exception(self, exc):
        if isinstance(exc, BadToken):
            self.headers['X-Reader-Google-Bad-Token'] = "true"
        return super(ReaderView, self).handle_exception(exc)

    def label(self, value):
        if not is_label(value, self.request.user.pk):
            raise exceptions.ParseError("Unknown label: {0}".format(value))
        return value.split('/')[-1]

    def get_content_negotiator(self):
        if not getattr(self, '_negotiator', None):
            force_format = self.kwargs.get('output')
            self._negotiator = self.content_negotiation_class(force_format)
        return self._negotiator


class TokenView(ReaderView):
    http_method_names = ['get', 'post']
    renderer_classes = [PlainRenderer]
    require_post_token = False

    def get(self, request, *args, **kwargs):
        token = generate_post_token(request.user)
        return Response(token)
    post = get
token = TokenView.as_view()


class UserInfo(ReaderView):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        return Response({
            "userName": request.user.username,
            "userEmail": request.user.email,
            "userId": str(request.user.pk),
            "userProfileId": str(request.user.pk),
            "isBloggerUser": False,
            "signupTimeSec": int(request.user.date_joined.strftime("%s")),
            "isMultiLoginEnabled": False,
        })
user_info = UserInfo.as_view()


class StreamPreference(ReaderView):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        return Response({"streamprefs": {}})
stream_preference = StreamPreference.as_view()


class PreferenceList(ReaderView):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        return Response({"prefs": [{
            "id": "lhn-prefs",
            "value": json.dumps({"subscriptions": {"ssa": "true"}},
                                separators=(',', ':')),
        }]})
preference_list = PreferenceList.as_view()


class UnreadCount(ReaderView):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        feeds = request.user.feeds.filter(unread_count__gt=0)
        last_updates = request.user.last_updates()
        unread_counts = []
        forced = False
        for feed in feeds:
            if feed.url not in last_updates and not forced:
                last_updates = request.user.refresh_updates()
                forced = True
            feed_data = {
                "id": u"feed/{0}".format(feed.url),
                "count": feed.unread_count,
            }
            ts = last_updates[feed.url]
            if ts:
                feed_data['newestItemTimestampUsec'] = '{0}000000'.format(ts)
            unread_counts.append(feed_data)

        # We can't annotate with Max('feeds__entries__date') when fetching the
        # categories since it creates duplicates and returns wrong counts.
        cat_ts = {}
        for feed in feeds:
            if feed.category_id in cat_ts and last_updates[feed.url]:
                cat_ts[feed.category_id] = max(cat_ts[feed.category_id],
                                               last_updates[feed.url])
            elif last_updates[feed.url]:
                cat_ts[feed.category_id] = last_updates[feed.url]
        categories = request.user.categories.annotate(
            unread_count=Sum('feeds__unread_count'),
        ).filter(unread_count__gt=0)
        for cat in categories:
            info = {
                "id": label_key(request, cat),
                "count": cat.unread_count,
            }
            if cat.pk in cat_ts:
                info["newestItemTimestampUsec"] = '{0}000000'.format(
                    cat_ts[cat.pk])
            unread_counts.append(info)

        # Special items:
        # reading-list is the global counter
        if cat_ts.values():
            unread_counts += [{
                "id": "user/{0}/state/com.google/reading-list".format(
                    request.user.pk),
                "count": sum([f.unread_count for f in feeds]),
                "newestItemTimestampUsec": '{0}000000'.format(max(
                    cat_ts.values())),
            }]
        return Response({
            "max": 1000,
            "unreadcounts": unread_counts,
        })
unread_count = UnreadCount.as_view()


class DisableTag(ReaderView):
    http_method_names = ['post']
    renderer_classes = [PlainRenderer]

    def post(self, request, *args, **kwargs):
        if 's' not in request.DATA and 't' not in request.DATA:
            raise exceptions.ParseError("Missing required 's' parameter")

        if 's' in request.DATA:
            name = is_label(request.DATA['s'], request.user.pk)
        else:
            name = request.DATA['t']

        try:
            category = request.user.categories.get(name=name)
        except Category.DoesNotExist:
            raise exceptions.ParseError(
                "Tag '{0}' does not exist".format(name))

        category.feeds.update(category=None)
        category.delete()
        return Response("OK")
disable_tag = DisableTag.as_view()


class RenameTag(ReaderView):
    http_method_names = ['post']
    renderer_classes = [PlainRenderer]

    def post(self, request, *args, **kwargs):
        if 's' not in request.DATA and 't' not in request.DATA:
            raise exceptions.ParseError("Missing required 's' parameter")

        if 'dest' not in request.DATA:
            raise exceptions.ParseError("Missing required 'dest' parameter")

        new_name = is_label(request.DATA['dest'], request.user.pk)
        if not new_name:
            raise exceptions.ParseError("Invalid 'dest' parameter")

        if 's' in request.DATA:
            name = is_label(request.DATA['s'], request.user.pk)
        else:
            name = request.DATA['t']

        try:
            category = request.user.categories.get(name=name)
        except Category.DoesNotExist:
            raise exceptions.ParseError(
                "Tag '{0}' does not exist".format(name))

        category.name = new_name
        category.save()

        return Response("OK")
rename_tag = RenameTag.as_view()


class TagList(ReaderView):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        tags = [{
            "id": "user/{0}/state/com.google/starred".format(request.user.pk),
            "sortid": "A0000001",
        }, {
            "id": "user/{0}/states/com.google/broadcast".format(
                request.user.pk),
            "sortid": "A0000002",
        }]
        index = 3
        for cat in request.user.categories.order_by('name'):
            tags.append({
                "id": label_key(request, cat),
                "sortid": "A{0}".format(str(index).zfill(7)),
            })
            index += 1
        return Response({'tags': tags})
tag_list = TagList.as_view()


class SubscriptionList(ReaderView):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        feeds = request.user.feeds.select_related('category',).order_by(
            'category__name', 'name')
        uniques = UniqueFeed.objects.filter(url__in=[f.url for f in feeds])
        unique_map = {}
        for unique in uniques:
            if unique.link:
                unique_map[unique.url] = unique.link

        subscriptions = []
        for index, feed in enumerate(feeds):
            subscription = {
                "id": u"feed/{0}".format(feed.url),
                "title": feed.name,
                "categories": [],
                "sortid": "B{0}".format(str(index).zfill(7)),
                "htmlUrl": unique_map.get(feed.url, feed.url),
                "firstitemmsec": (timezone.now() - timedelta(
                    days=request.user.ttl or 365)).strftime("%s000"),
            }
            if feed.category is not None:
                subscription['categories'].append({
                    "id": label_key(request, feed.category),
                    "label": feed.category.name,
                })
            subscriptions.append(subscription)
        return Response({
            "subscriptions": subscriptions
        })
subscription_list = SubscriptionList.as_view()


class EditSubscription(ReaderView):
    http_method_names = ['post']
    renderer_classes = [PlainRenderer]

    def post(self, request, *args, **kwargs):
        action = request.DATA.get('ac')
        if action is None:
            raise exceptions.ParseError("Missing 'ac' parameter")

        if 's' not in request.DATA:
            raise exceptions.ParseError("Missing 's' parameter")

        if not request.DATA['s'].startswith('feed/'):
            raise exceptions.ParseError(
                u"Unrecognized stream: {0}".format(request.DATA['s']))
        url = feed_url(request.DATA['s'])

        if action == 'subscribe':
            form = FeedForm(data={'url': url}, user=request.user)
            if not form.is_valid():
                errors = dict(form._errors)
                if 'url' in errors:
                    raise exceptions.ParseError(errors['url'][0])

            if 'a' in request.DATA:
                name = self.label(request.DATA['a'])
                category, created = request.user.categories.get_or_create(
                    name=name)
            else:
                category = None

            request.user.feeds.create(
                url=url,
                name=request.DATA.get('t', form.cleaned_data['title']),
                category=category)

        elif action == 'unsubscribe':
            request.user.feeds.filter(url=url).delete()
        elif action == 'edit':
            qs = request.user.feeds.filter(url=url)
            query = {}
            if 'r' in request.DATA:
                name = self.label(request.DATA['r'])
                qs = qs.filter(category__name=name)
                query['category'] = None
            if 'a' in request.DATA:
                name = self.label(request.DATA['a'])
                category, created = request.user.categories.get_or_create(
                    name=name)
                query['category'] = category
            if 't' in request.DATA:
                query['name'] = request.DATA['t']
            if query:
                qs.update(**query)
        else:
            msg = u"Unrecognized action: {0}".format(action)
            logger.info(msg)
            raise exceptions.ParseError(msg)
        return Response("OK")
edit_subscription = EditSubscription.as_view()


class QuickAddSubscription(ReaderView):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        if 'quickadd' not in request.DATA:
            raise exceptions.ParseError("Missing 'quickadd' parameter")

        url = request.DATA['quickadd']
        if url.startswith('feed/'):
            url = feed_url(url)

        form = FeedForm(data={'url': url}, user=request.user)
        if not form.is_valid():
            errors = dict(form._errors)
            if 'url' in errors:
                raise exceptions.ParseError(errors['url'][0])

        name = form.cleaned_data['title']
        if not name:
            name = urlparse.urlparse(url).netloc
        request.user.feeds.create(name=name, url=url)
        return Response({
            "numResults": 1,
            "query": url,
            "streamId": u"feed/{0}".format(url),
        })
quickadd_subscription = QuickAddSubscription.as_view()


class Subscribed(ReaderView):
    http_method_names = ['get']
    renderer_classes = [PlainRenderer]

    def get(self, request, *args, **kwargs):
        if 's' not in request.GET:
            raise exceptions.ParseError("Missing 's' parameter")
        feed = request.GET['s']
        if not feed.startswith('feed/'):
            raise exceptions.ParseError(
                "Unrecognized feed format. Use 'feed/<url>'")
        url = feed_url(feed)
        return Response(str(
            request.user.feeds.filter(url=url).exists()
        ).lower())
subscribed = Subscribed.as_view()


def get_q(stream, user_id, exception=False):
    """Given a stream ID, returns a Q object for this stream."""
    stream_q = None
    if stream.startswith("feed/"):
        url = feed_url(stream)
        stream_q = Q(feed__url=url)
    elif is_stream(stream, user_id):
        state = is_stream(stream, user_id)
        if state == 'read':
            stream_q = Q(read=True)
        elif state == 'kept-unread':
            stream_q = Q(read=False)
        elif state in ['broadcast', 'broadcast-friends']:
            stream_q = Q(broadcast=True)
        elif state == 'reading-list':
            stream_q = Q()
        elif state == 'starred':
            stream_q = Q(starred=True)
    elif is_label(stream, user_id):
        name = is_label(stream, user_id)
        stream_q = Q(feed__category__name=name)
    else:
        msg = u"Unrecognized stream: {0}".format(stream)
        logger.info(msg)
        if exception:
            raise exceptions.ParseError(msg)
    return stream_q


def get_stream_q(streams, user_id, exclude=None, include=None, limit=None,
                 offset=None):
    """
    Returns a Q object that can be used to filter a queryset of entries.

    streams: list of streams to include
    exclude: stream to exclude
    limit: unix timestamp from which to consider entries
    offset: unix timestamp to which to consider entries
    """
    q = None
    if streams.startswith('splice/'):
        streams = streams[len('splice/'):].split('|')
    else:
        streams = [streams]

    for stream in streams:
        stream_q = get_q(stream, user_id, exception=True)
        if stream_q is not None:
            if q is None:
                q = stream_q
            else:
                q |= stream_q

    # ?it=user/stuff or feed/stuff to only include something from the query
    if include is not None:
        for inc in include:
            include_q = get_q(inc, user_id)
            if include_q is not None and q is not None:
                q &= include_q

    # ?xt=user/stuff or feed/stuff to exclude something from the query
    if exclude is not None:
        for ex in exclude:
            exclude_q = get_q(ex, user_id)
            if exclude_q is not None and q is not None:
                q &= ~exclude_q

    # ?ot=<timestamp> for limiting in time
    if limit is not None:
        try:
            timestamp = int(limit)
        except ValueError:
            raise exceptions.ParseError(
                "Malformed 'ot' parameter. Must be a unix timstamp")
        else:
            limit = epoch_to_utc(timestamp)
            if q is not None:
                q &= Q(date__gte=limit)
    # ?nt=<timestamp>
    if offset is not None:
        try:
            timestamp = int(offset)
        except ValueError:
            raise exceptions.ParseError(
                "Malformed 'nt' parameter. Must be a unix timstamp")
        else:
            offset = epoch_to_utc(timestamp)
            if q is not None:
                q &= Q(date__lte=offset)
    if q is None:
        return Q(pk__lte=0)
    return q


def pagination(entries, n=None, c=None):
    # ?n=20 (default), ?c=<continuation> for offset
    if n is None:
        n = 20
    if c is None:
        c = 'page1'
    try:
        pagination_by = int(n)
    except ValueError:
        raise exceptions.ParseError("'n' must be an integer")
    try:
        page = int(c[4:])
    except ValueError:
        raise exceptions.ParseError("Invalid 'c' continuation string")

    continuation = None
    if page * pagination_by < entries.count():
        continuation = 'page{0}'.format(page + 1)

    start = max(0, (page - 1) * pagination_by)
    end = page * pagination_by
    return start, end, continuation


def label_key(request, label):
    return u"user/{0}/label/{1}".format(request.user.pk, label.name)


def serialize_entry(request, entry, uniques):
    reading_list = "user/{0}/state/com.google/reading-list".format(
        request.user.pk)
    read = "user/{0}/state/com.google/read".format(request.user.pk)
    starred = "user/{0}/state/com.google/starred".format(request.user.pk)
    broadcast = "user/{0}/state/com.google/broadcast".format(request.user.pk)

    item = {
        "crawlTimeMsec": entry.date.strftime("%s000"),
        "timestampUsec": entry.date.strftime("%s000000"),
        "id": "tag:google.com,2005:reader/item/{0}".format(entry.hex_pk),
        "categories": [reading_list],
        "title": entry.title,
        "published": int(entry.date.strftime("%s")),
        "updated": int(entry.date.strftime("%s")),
        "alternate": [{
            "href": entry.link,
            "type": "text/html",
        }],
        "content": {
            "direction": "ltr",
            "content": entry.subtitle,
        },
        "origin": {
            "streamId": u"feed/{0}".format(entry.feed.url),
            "title": entry.feed.name,
            "htmlUrl": uniques.get(entry.feed.url, entry.feed.url),
        },
    }
    if entry.feed.category is not None:
        item['categories'].append(
            label_key(request, entry.feed.category))
    if entry.read:
        item['categories'].append(read)
    if entry.starred:
        item['categories'].append(starred)
    if entry.broadcast:
        item['categories'].append(broadcast)
    if entry.author:
        item['author'] = entry.author
    return item


def get_unique_map(user, force=False):
    cache_key = 'reader:unique_map:{0}'.format(user.pk)
    value = cache.get(cache_key)
    if value is None or force:
        unique = UniqueFeed.objects.raw(
            "select id, url, muted from feeds_uniquefeed u "
            "where exists ("
            "select 1 from feeds_feed f "
            "left join auth_user s "
            "on f.user_id = s.id "
            "where f.url = u.url and f.user_id = %s)", [user.pk])
        value = {}
        for u in unique:
            value[u.url] = u.link
        cache.set(cache_key, value, 60)
    return value


class StreamContents(ReaderView):
    http_method_names = ['get']
    renderer_classes = ReaderView.renderer_classes + [AtomRenderer,
                                                      AtomHifiRenderer]

    def get(self, request, *args, **kwargs):
        content_id = kwargs['content_id']
        if content_id is None:
            content_id = 'user/-/state/com.google/reading-list'
        base = {
            "direction": "ltr",
            "id": content_id,
            "self": [{
                "href": request.build_absolute_uri(request.path),
            }],
            "author": request.user.username,
            "updated": int(timezone.now().strftime("%s")),
            "items": [],
        }

        if content_id.startswith("feed/"):
            url = feed_url(content_id)
            feeds = request.user.feeds.filter(url=url).order_by('pk')[:1]
            if len(feeds) == 0:
                raise Http404
            feed = feeds[0]
            base.update({
                'title': feed.name,
                'description': feed.name,
            })
            try:
                unique = UniqueFeed.objects.get(url=url)
                uniques = {url: unique.link}
            except UniqueFeed.DoesNotExist:
                uniques = {url: url}
                base.update({
                    'alternate': [{
                        'href': url,
                        'type': 'text/html',
                    }],
                })
            else:
                base.update({
                    'alternate': [{
                        'href': unique.link,
                        'type': 'text/html',
                    }],
                })
                updated = unique.last_update
                if updated is None:
                    updated = timezone.now() - timedelta(days=7)
                base['updated'] = int(updated.strftime('%s'))

        elif is_stream(content_id, request.user.pk):
            uniques = get_unique_map(request.user)

            state = is_stream(content_id, request.user.pk)
            base['id'] = 'user/{0}/state/com.google/{1}'.format(
                request.user.pk, state)
            if state == 'reading-list':
                base['title'] = u"{0}'s reading list on FeedHQ".format(
                    request.user.username)

            elif state == 'kept-unread':
                base['title'] = u"{0}'s unread items on FeedHQ".format(
                    request.user.username)

            elif state == 'starred':
                base["title"] = "Starred items on FeedHQ"

            elif state in ['broadcast', 'broadcast-friends']:
                base["title"] = "Broadcast items on FeedHQ"

        elif is_label(content_id, request.user.pk):
            name = is_label(content_id, request.user.pk)
            base['title'] = u'"{0}" via {1} on FeedHQ'.format(
                name, request.user.username)
            base['id'] = u'user/{0}/label/{1}'.format(request.user.pk, name)
            uniques = get_unique_map(request.user)
        else:
            msg = u"Unknown stream id: {0}".format(content_id)
            logger.info(msg)
            raise exceptions.ParseError(msg)

        entries = request.user.entries.filter(
            get_stream_q(content_id, request.user.pk,
                         exclude=request.GET.getlist('xt'),
                         include=request.GET.getlist('it'),
                         limit=request.GET.get('ot'),
                         offset=request.GET.get('nt')),
        ).select_related('feed', 'feed__category')

        # Ordering
        # ?r=d|n last entry first (default), ?r=o oldest entry first
        ordering = 'date' if request.GET.get('r', 'd') == 'o' else '-date'

        start, end, continuation = pagination(entries, n=request.GET.get('n'),
                                              c=request.GET.get('c'))

        qs = {}
        if start > 0:
            qs['c'] = request.GET['c']

        if 'output' in request.GET:
            qs['output'] = request.GET['output']

        if qs:
            base['self'][0]['href'] += '?{0}'.format(urlparse.urlencode(qs))

        if continuation:
            base['continuation'] = continuation

        forced = False  # Make at most 1 full refetch
        for entry in entries.order_by(ordering)[start:end]:
            if entry.feed.url not in uniques and not forced:
                uniques = get_unique_map(request.user, force=True)
                forced = True
            item = serialize_entry(request, entry, uniques)
            base['items'].append(item)
        return Response(base)
stream_contents = StreamContents.as_view()


class StreamItemsIds(ReaderView):
    http_method_names = ['get', 'post']
    require_post_token = False

    def get(self, request, *args, **kwargs):
        if 'n' not in request.GET:
            raise exceptions.ParseError("Required 'n' parameter")
        if 's' not in request.GET:
            raise exceptions.ParseError("Required 's' parameter")
        entries = request.user.entries.filter(
            get_stream_q(
                request.GET['s'], request.user.pk,
                exclude=request.GET.getlist('xt'),
                include=request.GET.getlist('it'),
                limit=request.GET.get('ot'),
                offset=request.GET.get('nt'))).order_by('date')

        start, end, continuation = pagination(entries, n=request.GET.get('n'),
                                              c=request.GET.get('c'))

        data = {}
        if continuation:
            data['continuation'] = continuation

        if request.GET.get("includeAllDirectStreamIds") == 'true':
            entries = entries.select_related('feed').values('pk', 'date',
                                                            'feed__url')
            item_refs = [{
                'id': str(e['pk']),
                'directStreamIds': [
                    u'feed/{0}'.format(e['feed__url']),
                ],
                'timestampUsec': e['date'].strftime("%s000000"),
            } for e in entries[start:end]]
        else:
            entries = entries.values('pk', 'date')
            item_refs = [{
                'id': str(e['pk']),
                'directStreamIds': [],
                'timestampUsec': e['date'].strftime("%s000000"),
            } for e in entries[start:end]]
        data['itemRefs'] = item_refs
        return Response(data)
    post = get
stream_items_ids = StreamItemsIds.as_view()


class StreamItemsCount(ReaderView):
    renderer_classes = [PlainRenderer]

    def get(self, request, *args, **kwargs):
        if 's' not in request.GET:
            raise exceptions.ParseError("Missing 's' parameter")
        entries = request.user.entries.filter(get_stream_q(request.GET['s'],
                                                           request.user.pk))
        data = str(entries.count())
        if request.GET.get('a') == 'true':
            data = '{0}#{1}'.format(
                data, entries.order_by('-date')[0].date.strftime("%B %d, %Y"))
        return Response(data)
stream_items_count = StreamItemsCount.as_view()


class StreamItemsContents(ReaderView):
    http_method_names = ['get', 'post']
    renderer_classes = ReaderView.renderer_classes + [AtomRenderer,
                                                      AtomHifiRenderer]
    require_post_token = False

    def get(self, request, *args, **kwargs):
        items = request.GET.getlist('i', request.DATA.getlist('i'))
        if len(items) == 0:
            raise exceptions.ParseError(
                "Required 'i' parameter: items IDs to send back")

        ids = map(item_id, items)

        entries = request.user.entries.filter(pk__in=ids).select_related(
            'feed', 'feed__category')

        if not entries:
            raise exceptions.ParseError("No items found")

        uniques = get_unique_map(request.user)
        items = []
        for e in entries:
            if e.feed.url not in uniques:
                uniques = get_unique_map(request.user, force=True)
            items.append(serialize_entry(request, e, uniques))

        base = {
            'direction': 'ltr',
            'id': u'feed/{0}'.format(entries[0].feed.url),
            'title': entries[0].feed.name,
            'self': [{
                'href': request.build_absolute_uri(),
            }],
            'alternate': [{
                'href': uniques.get(entries[0].feed.url, entries[0].feed.url),
                'type': 'text/html',
            }],
            'updated': int(timezone.now().strftime("%s")),
            'items': items,
            'author': request.user.username,
        }
        return Response(base)
    post = get
stream_items_contents = StreamItemsContents.as_view()


class EditTag(ReaderView):
    http_method_names = ['post']
    renderer_classes = [PlainRenderer]

    def post(self, request, *args, **kwargs):
        if 'i' not in request.DATA:
            raise exceptions.ParseError(
                "Missing 'i' in request data. "
                "'tag:gogle.com,2005:reader/item/<item_id>'")
        entry_ids = list(map(item_id, request.DATA.getlist('i')))
        add = 'a' in request.DATA
        remove = 'r' in request.DATA
        if not add and not remove:
            raise exceptions.ParseError(
                "Specify a tag to add or remove. Add: 'a' parameter, "
                "remove: 'r' parameter.")

        to_add = []
        if add:
            to_add = list(map(tag_value, request.DATA.getlist('a')))

        to_remove = []
        if remove:
            to_remove = list(map(tag_value, request.DATA.getlist('r')))

        query = {}
        for tag in to_add:
            if tag == 'kept-unread':
                query['read'] = False

            elif tag in ['starred', 'broadcast', 'read']:
                query[tag] = True

            elif tag.startswith('tracking-'):
                # There is no tracking. Carry on :)
                # More context: http://googlesystem.blogspot.ch/2008/03/explore-your-interactions-with-google.html  # noqa
                # FeedHQ doesn't have that historical data.
                continue

            else:
                logger.info(u"Unhandled tag {0}".format(tag))
                raise exceptions.ParseError(
                    "Unrecognized tag: {0}".format(tag))

        for tag in to_remove:
            if tag == 'kept-unread':
                query['read'] = True

            elif tag in ['starred', 'broadcast', 'read']:
                query[tag] = False

            elif tag.startswith('tracking-'):
                # There is no tracking. Carry on :)
                continue

            else:
                logger.info(u"Unhandled tag {0}".format(tag))
                raise exceptions.ParseError(
                    "Unrecognized tag: {0}".format(tag))

        request.user.entries.filter(pk__in=entry_ids).update(**query)
        merged = to_add + to_remove
        if 'read' in merged or 'kept-unread' in merged:
            feeds = Feed.objects.filter(
                pk__in=request.user.entries.filter(
                    pk__in=entry_ids).values_list('feed_id', flat=True))
            for feed in feeds:
                feed.update_unread_count()
        return Response("OK")
edit_tag = EditTag.as_view()


class MarkAllAsRead(ReaderView):
    http_method_names = ['post']
    renderer_classes = [PlainRenderer]

    def post(self, request, *args, **kwargs):
        if 's' not in request.DATA:
            raise exceptions.ParseError("Missing 's' parameter")
        entries = request.user.entries
        limit = None
        if 'ts' in request.DATA:
            try:
                timestamp = int(request.DATA['ts'])
            except ValueError:
                raise exceptions.ParseError(
                    "Invalid 'ts' parameter. Must be a number of microseconds "
                    "since epoch.")
            limit = epoch_to_utc(timestamp / 1000000)  # microseconds -> secs
            entries = entries.filter(date__lte=limit)

        stream = request.DATA['s']

        if stream.startswith('feed/'):
            url = feed_url(stream)
            entries = entries.filter(feed__url=url)
        elif is_label(stream, request.user.pk):
            name = is_label(stream, request.user.pk)
            entries = entries.filter(
                feed__category=request.user.categories.get(name=name),
            )
        elif is_stream(stream, request.user.pk):
            state = is_stream(stream, request.user.pk)
            if state == 'read':  # mark read items as read yo
                return Response("OK")
            elif state in ['kept-unread', 'reading-list']:
                pass
            elif state in ['starred', 'broadcast']:
                entries = entries.filter(**{state: True})
            else:
                logger.info(u"Unknown state: {0}".format(state))
                return Response("OK")
        else:
            logger.info(u"Unknown stream: {0}".format(stream))
            return Response("OK")

        entries.filter(read=False).update(read=True)

        cursor = connection.cursor()
        cursor.execute("""
            update feeds_feed f set unread_count = (
                select count(*) from feeds_entry e
                where e.feed_id = f.id and read = false
            ) where f.user_id = %s
        """, [request.user.pk])
        return Response("OK")
mark_all_as_read = MarkAllAsRead.as_view()


class FriendList(ReaderView):
    def get(self, request, *args, **kwargs):
        return Response({
            'friends': [{
                'userIds': [str(request.user.pk)],
                'profileIds': [str(request.user.pk)],
                'contactId': '-1',
                'stream': u"user/{0}/state/com.google/broadcast".format(
                    request.user.pk),
                'flags': 1,
                'displayName': request.user.username,
                'givenName': request.user.username,
                'n': '',
                'p': '',
                'hasSharedItemsOnProfile': False,  # TODO handle broadcast
            }]
        })
friend_list = FriendList.as_view()


class OPMLExport(ReaderView):
    def get(self, request, *args, **kwargs):
        response = render(
            request, 'profiles/opml_export.opml',
            {'categories': request.user.categories.all(),
             'orphan_feeds': request.user.feeds.filter(category__isnull=True)})
        response['Content-Disposition'] = (
            'attachment; filename=feedhq-export.opml'
        )
        response['Content-Type'] = 'text/xml; charset=utf-8'
        return response
export_subscriptions = OPMLExport.as_view()


class OPMLImport(ReaderView):
    http_method_names = ['post']
    renderer_classes = [PlainRenderer]
    parser_classes = [XMLParser]
    require_post_token = False

    def post(self, request, *args, **kwargs):
        try:
            entries = opml.from_string(request.body)
        except XMLSyntaxError:
            raise exceptions.ParseError(
                "This file doesn't seem to be a valid OPML file.")

        existing_feeds = set(request.user.feeds.values_list('url', flat=True))
        try:
            with user_lock('opml_import', request.user.pk, timeout=30):
                imported = save_outline(request.user, None, entries,
                                        existing_feeds)
        except ValidationError:
            raise exceptions.ParseError(
                "Another concurrent OPML import is happening "
                "for this user.")
        return Response("OK: {0}".format(imported))
import_subscriptions = OPMLImport.as_view()

########NEW FILE########
__FILENAME__ = settings
import dj_database_url
import os

from six.moves.urllib import parse as urlparse

from django.core.urlresolvers import reverse_lazy

BASE_DIR = os.path.dirname(__file__)

DEBUG = os.environ.get('DEBUG', False)
TEMPLATE_DEBUG = DEBUG

# Are we running the tests or a real server?
TESTS = False

ADMINS = MANAGERS = ()

DATABASES = {
    'default': dj_database_url.config(
        default='postgres://postgres@localhost:5432/feedhq',
    ),
}

TIME_ZONE = 'UTC'

LANGUAGE_CODE = 'en-us'

USE_I18N = True
USE_L10N = True
USE_TZ = True

SITE_ID = 1

MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))
MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')

STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR, 'static'))
STATIC_URL = os.environ.get('STATIC_URL', '/static/')

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split()
PUSH_DOMAIN = ALLOWED_HOSTS[0]

WSGI_APPLICATION = 'feedhq.wsgi.application'

if not DEBUG:
    STATICFILES_STORAGE = ('django.contrib.staticfiles.storage.'
                           'CachedStaticFilesStorage')


def parse_email_url():
    parsed = urlparse.urlparse(os.environ['EMAIL_URL'])
    if '?' in parsed.path:
        querystring = urlparse.parse_qs(parsed.path.split('?', 1)[1])
    elif parsed.query:
        querystring = urlparse.parse_qs(parsed.query)
    else:
        querystring = {}
    if querystring:
        for key in querystring.keys():
            querystring[key] = querystring[key][0]
    if '@' in parsed.netloc:
        creds, at, netloc = parsed.netloc.partition('@')
        username, colon, password = creds.partition(':')
        host, colon, port = netloc.partition(':')
    else:
        username = password = None
        host, colon, port = parsed.netloc.partition(':')
    # Django defaults
    config = {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'HOST': 'localhost',
        'USER': '',
        'PASSWORD': '',
        'PORT': 25,
        'SUBJECT_PREFIX': '[FeedHQ] ',
        'USE_TLS': False,
    }
    if host:
        config['HOST'] = host
    if username:
        config['USER'] = username
    if password:
        config['PASSWORD'] = password
    if port:
        config['PORT'] = int(port)
    if 'subject_prefix' in querystring:
        config['SUBJECT_PREFIX'] = querystring['subject_prefix'][0]
    if 'backend' in querystring:
        config['BACKEND'] = querystring['backend']
    if 'use_tls' in querystring:
        config['USE_TLS'] = True
    return config

DEFAULT_FROM_EMAIL = SERVER_EMAIL = os.environ['FROM_EMAIL']

if 'EMAIL_URL' in os.environ:
    email_config = parse_email_url()
    EMAIL_BACKEND = email_config['BACKEND']
    EMAIL_HOST = email_config['HOST']
    EMAIL_HOST_PASSWORD = email_config['PASSWORD']
    EMAIL_HOST_USER = email_config['USER']
    EMAIL_PORT = email_config['PORT']
    EMAIL_SUBJECT_PREFIX = email_config.get('SUBJECT_PREFIX', '[FeedHQ] ')
    EMAIL_USE_TLS = email_config['USE_TLS']
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

AUTHENTICATION_BACKENDS = (
    'feedhq.backends.RateLimitMultiBackend',
)

AUTH_USER_MODEL = 'profiles.User'

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)
if DEBUG:
    TEMPLATE_LOADERS = TEMPLATE_LOADERS[0][1]

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'sekizai.context_processors.sekizai',
)


def parse_redis_url():
    config = {
        'host': 'localhost',
        'port': 6379,
        'password': None,
        'db': 0,
    }
    parsed_redis = urlparse.urlparse(os.environ['REDIS_URL'])
    if '?' in parsed_redis.path and not parsed_redis.query:
        # Bug in python 2.7.3, fixed in 2.7.4
        path, q, querystring = parsed_redis.path.partition('?')
    else:
        path, q, querystring = parsed_redis.path, None, parsed_redis.query  # noqa

    querystring = urlparse.parse_qs(querystring)
    for key in querystring.keys():
        querystring[key] = querystring[key][0]
    for key in config.keys():
        querystring.pop(key, None)

    if parsed_redis.netloc.endswith('unix'):
        del config['port']
        del config['host']
        # the last item of the path could also be just part of the socket path
        try:
            config['db'] = int(os.path.split(path)[-1])
        except ValueError:
            pass
        else:
            path = os.path.join(*os.path.split(path)[:-1])
        config['unix_socket_path'] = path
        if parsed_redis.password:
            config['password'] = parsed_redis.password
    else:
        if path[1:]:
            config['db'] = int(path[1:])
        if parsed_redis.password:
            config['password'] = parsed_redis.password
        if parsed_redis.port:
            config['port'] = int(parsed_redis.port)
        if parsed_redis.hostname:
            config['host'] = parsed_redis.hostname

    return config, True if 'eager' in querystring else False

REDIS, RQ_EAGER = parse_redis_url()
RQ = REDIS
location = REDIS.get('unix_socket_path', '{host}:{port}'.format(**REDIS))

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': location,
        'OPTIONS': {
            'DB': REDIS['db'],
            'PASSWORD': REDIS['password'],
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
    },
}

MESSAGE_STORAGE = 'django.contrib.messages.storage.fallback.FallbackStorage'
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'feedhq.urls'

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.messages',

    'django_push.subscriber',
    'floppyforms',
    'sekizai',
    'django_rq_dashboard',
    'south',

    'feedhq.core',
    'feedhq.profiles',
    'feedhq.feeds',
    'feedhq.reader',

    'password_reset',
)

if 'SENTRY_DSN' in os.environ:
    INSTALLED_APPS += (
        'raven.contrib.django',
    )

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('feeds:home')

DATE_FORMAT = 'M j, H:i'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(levelname)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'sentry': {
            'level': 'INFO',
            'class': 'raven.contrib.django.handlers.SentryHandler',
        },
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'feedhq': {
            'handlers': ['console', 'sentry'],
            'level': 'DEBUG',
        },
        'ratelimitbackend': {
            'handlers': ['console', 'sentry'],
            'level': 'WARNING',
        },
        'rq.worker': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'bleach': {
            'handlers': ['null'],
        },
        'django_push': {
            'handlers': ['console', 'sentry'],
            'level': 'DEBUG',
        },
        'raven': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'sentry.errors': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

REST_FRAMEWORK = {
    "URL_FORMAT_OVERRIDE": "output",
}

if 'READITLATER_API_KEY' in os.environ:
    API_KEYS = {
        'readitlater': os.environ['READITLATER_API_KEY']
    }

if 'INSTAPAPER_CONSUMER_KEY' in os.environ:
    INSTAPAPER = {
        'CONSUMER_KEY': os.environ['INSTAPAPER_CONSUMER_KEY'],
        'CONSUMER_SECRET': os.environ['INSTAPAPER_CONSUMER_SECRET'],
    }

if 'READABILITY_CONSUMER_KEY' in os.environ:
    READABILITY = {
        'CONSUMER_KEY': os.environ['READABILITY_CONSUMER_KEY'],
        'CONSUMER_SECRET': os.environ['READABILITY_CONSUMER_SECRET'],
    }

if 'POCKET_CONSUMER_KEY' in os.environ:
    POCKET_CONSUMER_KEY = os.environ['POCKET_CONSUMER_KEY']

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_PATH = os.environ.get('SESSION_COOKIE_PATH', '/')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

if 'HTTPS' in os.environ:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    PUSH_SSL_CALLBACK = True

try:
    import debug_toolbar  # noqa
except ImportError:
    pass
else:
    INSTALLED_APPS += (
        'debug_toolbar',
    )

########NEW FILE########
__FILENAME__ = storage
import tempfile
import os
import errno

from django.conf import settings
from django.core.files import locks
from django.core.files.move import file_move_safe
from django.utils.text import get_valid_filename
from django.core.files.storage import FileSystemStorage


class OverwritingStorage(FileSystemStorage):
    """
    File storage that allows overwriting of stored files.
    """

    def get_available_name(self, name):
        return name

    def _save(self, name, content):
        """
        Lifted partially from django/core/files/storage.py
        """
        full_path = self.path(name)

        directory = os.path.dirname(full_path)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
        if not os.path.isdir(directory):
            raise IOError("%s exists and is not a directory." % directory)

        # This file has a file path that we can move.
        if hasattr(content, 'temporary_file_path'):
            temp_data_location = content.temporary_file_path()
        else:
            tmp_prefix = "tmp_%s" % (get_valid_filename(name), )
            temp_data_location = tempfile.mktemp(prefix=tmp_prefix,
                                                 dir=self.location)
            try:
                # This is a normal uploadedfile that we can stream.
                # This fun binary flag incantation makes os.open throw an
                # OSError if the file already exists before we open it.
                fd = os.open(temp_data_location,
                             os.O_WRONLY | os.O_CREAT |
                             os.O_EXCL | getattr(os, 'O_BINARY', 0))
                locks.lock(fd, locks.LOCK_EX)
                for chunk in content.chunks():
                    os.write(fd, chunk)
                locks.unlock(fd)
                os.close(fd)
            except Exception:
                if os.path.exists(temp_data_location):
                    os.remove(temp_data_location)
                raise

        file_move_safe(temp_data_location, full_path, allow_overwrite=True)
        content.close()

        if settings.FILE_UPLOAD_PERMISSIONS is not None:
            os.chmod(full_path, settings.FILE_UPLOAD_PERMISSIONS)
        return name

########NEW FILE########
__FILENAME__ = tasks
"""
Generic helpers for RQ task execution
"""
from __future__ import absolute_import

import rq

from django.conf import settings

from .utils import get_redis_connection


def enqueue(function, args=None, kwargs=None, timeout=None, queue='default'):
    async = not settings.RQ_EAGER

    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}

    conn = get_redis_connection()
    queue = rq.Queue(queue, connection=conn, async=async)
    return queue.enqueue_call(func=function, args=tuple(args), kwargs=kwargs,
                              timeout=timeout)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import url, patterns, include
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from ratelimitbackend import admin
admin.autodiscover()

from . import views
from .profiles.forms import AuthForm


urlpatterns = patterns(
    '',
    (r'^admin/rq/', include('django_rq_dashboard.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^subscriber/', include('django_push.subscriber.urls')),
    url(r'^robots.txt$', views.robots),
    url(r'^humans.txt$', views.humans),
    url(r'^favicon.ico$', views.favicon),
    url(r'^apple-touch-icon-precomposed.png$', views.touch_icon),
    url(r'^apple-touch-icon.png$', views.touch_icon),
    (r'^', include('feedhq.reader.urls', namespace='reader')),
    (r'^accounts/', include('feedhq.profiles.urls')),
    (r'^', include('feedhq.feeds.urls', namespace='feeds')),
)

urlpatterns += patterns(
    'ratelimitbackend.views',
    url(r'^login/$', 'login', {'authentication_form': AuthForm}, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
)

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.validators import EmailValidator, ValidationError

import redis


def get_redis_connection():
    """
    Helper used for obtain a raw redis client.
    """
    from redis_cache.cache import pool
    connection_pool = pool.get_connection_pool(
        parser_class=redis.connection.HiredisParser,
        connection_pool_class=redis.ConnectionPool,
        connection_pool_class_kwargs={},
        **settings.REDIS)
    return redis.Redis(connection_pool=connection_pool, **settings.REDIS)


def is_email(value):
    try:
        EmailValidator()(value)
    except ValidationError:
        return False
    else:
        return True

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.views import logout as do_logout
from django.http import (HttpResponse, HttpResponsePermanentRedirect,
                         HttpResponseNotAllowed)


robots = lambda _: HttpResponse('User-agent: *\nDisallow:\n',
                                mimetype='text/plain')

humans = lambda _: HttpResponse(u"""/* TEAM */
    Main developer: Bruno Renié
    Contact: contact [at] feedhq.org
    Twitter: @brutasse, @FeedHQ
    From: Switzerland

/* SITE */
    Language: English
    Backend: Django, PostgreSQL, Redis
    Frontend: SCSS, Compass, Iconic
""", mimetype='text/plain; charset=UTF-8')

favicon = lambda _: HttpResponsePermanentRedirect(
    '%score/img/icon-rss.png' % settings.STATIC_URL
)

touch_icon = lambda _: HttpResponsePermanentRedirect(
    '%sfeeds/img/touch-icon-114.png' % settings.STATIC_URL
)


def logout(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(["POST"], "Logout via POST only")
    return do_logout(request)

########NEW FILE########
__FILENAME__ = wsgi
import os

from django.core.wsgi import get_wsgi_application
from raven import Client
from raven.middleware import Sentry


application = get_wsgi_application()
if 'SENTRY_DSN' in os.environ:
    application = Sentry(application, Client())

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

import envdir


if __name__ == "__main__":
    if 'test' in sys.argv:
        env_dir = os.path.join('tests', 'envdir')
    else:
        env_dir = 'envdir'
    envdir.read(os.path.join(os.path.dirname(__file__), env_dir))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = factories
# -*- coding: utf-8 -*-
import datetime
import random

from django.utils import timezone
from django.utils.text import slugify, force_text
from factory import (DjangoModelFactory as Factory, SubFactory, Sequence,
                     lazy_attribute)

from feedhq.feeds.models import Category, Feed, Entry
from feedhq.profiles.models import User


class UserFactory(Factory):
    FACTORY_FOR = User

    username = Sequence(lambda n: u'ùser{0}'.format(n))
    password = 'test'

    @lazy_attribute
    def email(self):
        return u"{0}@example.com".format(slugify(force_text(self.username)))

    @classmethod
    def _prepare(cls, create, **kwargs):
        if create:
            return User.objects.create_user(**kwargs)
        else:
            return super(UserFactory, cls)._prepare(create, **kwargs)


class CategoryFactory(Factory):
    FACTORY_FOR = Category

    name = Sequence(lambda n: u'Categorỳ {0}'.format(n))
    user = SubFactory(UserFactory)

    @lazy_attribute
    def slug(self):
        return slugify(self.name)


class FeedFactory(Factory):
    FACTORY_FOR = Feed

    name = Sequence(lambda n: u'Feèd {0}'.format(n))
    url = Sequence(lambda n: u'http://example.com/feèds/{0}'.format(n))
    category = SubFactory(CategoryFactory)
    user = SubFactory(UserFactory)


class EntryFactory(Factory):
    FACTORY_FOR = Entry

    feed = SubFactory(FeedFactory)
    title = Sequence(lambda n: u'Entrỳ {0}'.format(n))
    subtitle = 'dùmmy content'
    link = Sequence(lambda n: u'https://example.com/entrỳ/{0}'.format(n))
    user = SubFactory(UserFactory)

    @lazy_attribute
    def date(self):
        minutes = random.randint(0, 60*24*2)  # 2 days
        return timezone.now() - datetime.timedelta(minutes=minutes)

########NEW FILE########
__FILENAME__ = hashers
from django.contrib.auth.hashers import BasePasswordHasher


class NotHashingHasher(BasePasswordHasher):
    """
    A hasher that does not hash.
    """
    algorithm = 'plain'

    def encode(self, password, salt):
        return '{0}${1}'.format(self.algorithm, password)

    def salt(self):
        return None

    def verify(self, password, encoded):
        algo, decoded = encoded.split('$', 1)
        return password == decoded

########NEW FILE########
__FILENAME__ = settings
import sys
import warnings
warnings.simplefilter('always')

from feedhq.settings import *  # noqa

SECRET_KEY = 'test secret key'

TESTS = True

PASSWORD_HASHERS = [
    'tests.hashers.NotHashingHasher',
]

RQ_EAGER = True

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

EMAIL_HOST = 'dummy'

API_KEYS = {
    'readitlater': 'test read it later API key',
}

INSTAPAPER = READABILITY = {
    'CONSUMER_KEY': 'consumer key',
    'CONSUMER_SECRET': 'consumer secret',
}

# Silencing log calls
if '-v2' not in sys.argv:
    LOGGING['loggers']['ratelimitbackend']['level'] = 'ERROR'
    LOGGING['loggers']['feedhq']['level'] = 'ERROR'

MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')

########NEW FILE########
__FILENAME__ = test_backend
import warnings

from django.test import TestCase
from django.contrib.auth import authenticate

from .factories import UserFactory


class BackendTest(TestCase):
    def test_case_insensitive_username(self):
        user = UserFactory.create(username='TeSt')

        with warnings.catch_warnings(record=True) as w:
            self.assertEqual(authenticate(username='TeSt', password='test').pk,
                             user.pk)

            self.assertEqual(authenticate(username='test', password='test').pk,
                             user.pk)

            self.assertEqual(authenticate(username=user.email.lower(),
                                          password='test').pk, user.pk)

            self.assertEqual(authenticate(username=user.email.upper(),
                                          password='test').pk, user.pk)
            self.assertEqual(len(w), 4)

########NEW FILE########
__FILENAME__ = test_favicons
from django.test import TestCase
from mock import patch

from feedhq.feeds.models import Favicon, Feed

from .factories import FeedFactory
from . import responses


class FaviconTests(TestCase):
    @patch("requests.get")
    def test_existing_favicon_new_feed(self, get):
        get.return_value = responses(304)
        FeedFactory.create(url='http://example.com/feed')
        self.assertEqual(Feed.objects.values_list('favicon', flat=True)[0], '')

        # Simulate a 1st call of update_favicon which creates a Favicon entry
        Favicon.objects.create(url='http://example.com/feed',
                               favicon='favicons/example.com.ico')

        Favicon.objects.update_favicon('http://example.com/feed')
        self.assertEqual(Feed.objects.values_list('favicon', flat=True)[0],
                         'favicons/example.com.ico')

########NEW FILE########
__FILENAME__ = test_feeds
# -*- coding: utf-8 -*-
import feedparser
import json

from datetime import timedelta

from django.core.urlresolvers import reverse
from django.utils import timezone
from django_push.subscriber.signals import updated
from django_webtest import WebTest
from mock import patch
from rache import schedule_job

from feedhq.feeds.models import Category, Feed, Entry, UniqueFeed
from feedhq.feeds.tasks import update_feed
from feedhq.feeds.templatetags.feeds_tags import smart_date
from feedhq.feeds.utils import USER_AGENT
from feedhq.profiles.models import User
from feedhq.utils import get_redis_connection
from feedhq.wsgi import application  # noqa

from .factories import UserFactory, CategoryFactory, FeedFactory, EntryFactory
from . import data_file, responses, patch_job


class WebBaseTests(WebTest):
    @patch('requests.get')
    def test_welcome_page(self, get):
        get.return_value = responses(304)

        self.user = User.objects.create_user('testuser',
                                             'foo@example.com',
                                             'pass')
        user = UserFactory.create()
        url = reverse('feeds:home')
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Getting started')
        FeedFactory.create(category__user=user, user=user)
        response = self.app.get(url)
        self.assertNotContains(response, 'Getting started')

    def test_login_required(self):
        url = reverse('feeds:home')
        response = self.app.get(url, headers={'Accept': 'text/*'})
        self.assertEqual(response.status_code, 200)

    def test_homepage(self):
        """The homepage from a logged in user"""
        user = UserFactory.create()
        response = self.app.get(reverse('feeds:home'),
                                user=user)
        self.assertContains(response, 'Home')
        self.assertContains(response, user.username)

    def test_unauth_homepage(self):
        """The home page from a logged-out user"""
        response = self.app.get(reverse('feeds:home'))
        self.assertContains(response, 'Sign in')  # login required

    def test_paginator(self):
        user = UserFactory.create()
        response = self.app.get(reverse('feeds:home', args=[5]),
                                user=user)
        self.assertContains(response, 'Home')

    def test_category(self):
        user = UserFactory.create()
        CategoryFactory.create(user=user, name=u'Cat yo')
        url = reverse('feeds:category', args=['cat-yo'])
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Cat yo')

    @patch("requests.get")
    def test_only_unread(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        category = CategoryFactory.create(user=user)
        FeedFactory.create(category=category, user=user)
        url = reverse('feeds:unread_category', args=[category.slug])
        response = self.app.get(url, user=user)

        self.assertContains(response, category.name)
        self.assertContains(response, 'all <span class="ct">')

    def test_add_category(self):
        user = UserFactory.create()
        url = reverse('feeds:add_category')
        response = self.app.get(url, user=user)

        form = response.forms['category']
        response = form.submit()
        self.assertFormError(response, 'form', 'name',
                             ['This field is required.'])

        form['name'] = 'New Name'
        form['color'] = 'red'
        response = form.submit()
        self.assertRedirects(response, '/manage/')

        # Re-submitting the same name fails
        response = form.submit()
        self.assertFormError(response, 'form', 'name',
                             ['A category with this name already exists.'])

        # Adding a category with a name generating the same slug.
        # The slug will be different
        form['name'] = 'New  Name'
        response = form.submit()
        user.categories.get(slug='new-name-1')
        self.assertRedirects(response, '/manage/')

        # Now we add a category named 'add', which is a conflicting URL
        form['name'] = 'add'
        response = form.submit()
        user.categories.get(slug='add-1')
        self.assertRedirects(response, '/manage/')

        # Add a category with non-ASCII names, slugify should cope
        form['name'] = u'北京'
        response = form.submit()
        user.categories.get(slug='unknown')
        self.assertRedirects(response, '/manage/')
        form['name'] = u'北'
        response = form.submit()
        user.categories.get(slug='unknown-1')
        self.assertRedirects(response, '/manage/')
        form['name'] = u'京'
        response = form.submit()
        user.categories.get(slug='unknown-2')
        self.assertRedirects(response, '/manage/')

    def test_delete_category(self):
        user = UserFactory.create()
        category = CategoryFactory.create(user=user)
        url = reverse('feeds:delete_category', args=[category.slug])
        response = self.app.get(url, user=user)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Category.objects.count(), 1)
        form = response.forms['delete']
        response = form.submit().follow()
        self.assertEqual(Category.objects.count(), 0)

    @patch("requests.get")
    def test_feed(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        feed = FeedFactory.create(category__user=user, user=user)
        url = reverse('feeds:feed', args=[feed.pk])
        response = self.app.get(url, user=user)

        expected = (
            '<a href="{0}unread/">unread <span class="ct">0</span></a>'
        ).format(feed.get_absolute_url())
        self.assertContains(response, expected)

    def test_edit_category(self):
        user = UserFactory.create()
        category = CategoryFactory.create(user=user)
        url = reverse('feeds:edit_category', args=[category.slug])
        response = self.app.get(url, user=user)
        self.assertContains(response, u'Edit {0}'.format(category.name))

        form = response.forms['category']
        form['name'] = 'New Name'
        form['color'] = 'blue'

        response = form.submit().follow()
        self.assertContains(response,
                            'New Name has been successfully updated')

    @patch('requests.get')
    def test_add_feed(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        category = CategoryFactory.create(user=user)

        url = reverse('feeds:add_feed')
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Add a feed')

        form = response.forms['feed']
        form['name'] = 'Lulz'
        response = form.submit()  # there is no URL
        self.assertFormError(response, 'form', 'url',
                             ['This field is required.'])

        form['name'] = 'Bobby'
        form['url'] = 'http://example.com/feed.xml'
        form['category'] = category.pk
        response = form.submit()
        self.assertFormError(response, 'form', 'url', [
            "Invalid response code from URL: HTTP 304.",
        ])
        get.return_value = responses(200, 'categories.opml')
        response = form.submit()
        self.assertFormError(response, 'form', 'url', [
            "This URL doesn't seem to be a valid feed.",
        ])

        get.return_value = responses(200, 'bruno.im.png')
        response = form.submit()
        self.assertFormError(response, 'form', 'url', [
            "This URL doesn't seem to be a valid feed.",
        ])

        cache_key = "lock:feed_check:{0}".format(user.pk)
        redis = get_redis_connection()
        redis.set(cache_key, user.pk)
        response = form.submit()
        self.assertFormError(response, 'form', 'url', [
            "This action can only be done one at a time.",
        ])
        redis.delete(cache_key)

        get.return_value = responses(200, 'brutasse.atom')
        response = form.submit()
        self.assertRedirects(response, '/manage/')
        response.follow()

        response = form.submit()
        self.assertFormError(
            response, 'form', 'url',
            ["It seems you're already subscribed to this feed."])

        # Provide initial params via ?feed=foo&name=bar
        response = self.app.get(url, {'feed': 'https://example.com/blog/atom',
                                      'name': 'Some Example Blog'})
        self.assertContains(response, 'value="https://example.com/blog/atom"')
        self.assertContains(response, 'value="Some Example Blog"')

        get.side_effect = ValueError
        user.feeds.all().delete()
        response = form.submit()
        self.assertFormError(response, 'form', 'url',
                             ['Error fetching the feed.'])

    def test_feed_url_validation(self):
        user = UserFactory.create()
        category = CategoryFactory.create(user=user)
        url = reverse('feeds:add_feed')
        response = self.app.get(url, user=user)

        form = response.forms['feed']
        form['name'] = 'Test'
        form['url'] = 'ftp://example.com'
        form['category'] = category.pk

        response = form.submit()
        self.assertFormError(
            response, 'form', 'url',
            "Invalid URL scheme: 'ftp'. Only HTTP and HTTPS are supported.",
        )

        for invalid_url in ['http://localhost:8000', 'http://localhost',
                            'http://127.0.0.1']:
            form['url'] = invalid_url
            response = form.submit()
            self.assertFormError(response, 'form', 'url', "Invalid URL.")

    @patch("requests.get")
    def test_edit_feed(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        feed = FeedFactory.create(user=user)
        url = reverse('feeds:edit_feed', args=[feed.pk])
        response = self.app.get(url, user=user)
        self.assertContains(response, feed.name)

        form = response.forms['feed']

        form['name'] = 'New Name'
        form['url'] = 'http://example.com/newfeed.xml'
        get.return_value = responses(200, 'brutasse.atom')
        response = form.submit().follow()
        self.assertContains(response, 'New Name has been successfully updated')

        cat = CategoryFactory.create(user=user)
        response = self.app.get(url, user=user)
        form = response.forms['feed']
        form['category'] = cat.pk
        response = form.submit().follow()
        self.assertContains(response, 'New Name has been successfully updated')
        self.assertEqual(Feed.objects.get().category_id, cat.pk)

    @patch("requests.get")
    def test_delete_feed(self, get):
        get.return_value = responses(304)

        user = UserFactory.create()
        feed = FeedFactory.create(category__user=user, user=user)
        url = reverse('feeds:delete_feed', args=[feed.pk])
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Delete')
        self.assertContains(response, feed.name)

        self.assertEqual(Feed.objects.count(), 1)
        response = response.forms['delete'].submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Feed.objects.count(), 0)
        # Redirects to home so useless to test

    @patch("requests.get")
    def test_invalid_page(self, get):
        get.return_value = responses(304)
        # We need more than 25 entries
        user = UserFactory.create()
        FeedFactory.create(category__user=user, user=user)
        url = reverse('feeds:home', args=[12000])  # that page doesn't exist
        response = self.app.get(url, user=user)
        self.assertContains(response, '<a href="/" class="current">')

    # This is called by other tests
    def _test_entry(self, from_url, user):
        self.assertEqual(self.app.get(
            from_url, user=user).status_code, 200)

        e = Entry.objects.get(title="jacobian's django-deployment-workshop")
        url = reverse('feeds:item', args=[e.pk])
        response = self.app.get(url, user=user)
        self.assertContains(response, "jacobian's django-deployment-workshop")

    @patch('requests.get')
    def test_entry(self, get):
        user = UserFactory.create(ttl=99999)
        get.return_value = responses(200, 'sw-all.xml')
        feed = FeedFactory.create(category__user=user, user=user)

        url = reverse('feeds:home')
        self._test_entry(url, user)

        url = reverse('feeds:unread')
        self._test_entry(url, user)

        url = reverse('feeds:stars')
        self._test_entry(url, user)

        url = reverse('feeds:category', args=[feed.category.slug])
        self._test_entry(url, user)

        url = reverse('feeds:unread_category', args=[feed.category.slug])
        self._test_entry(url, user)

        url = reverse('feeds:feed', args=[feed.pk])
        self._test_entry(url, user)

        url = reverse('feeds:unread_feed', args=[feed.pk])
        self._test_entry(url, user)

        feed.category = None
        feed.save()
        self._test_entry(url, user)

    @patch('requests.get')
    def test_custom_ordering(self, get):
        user = UserFactory.create()
        get.return_value = responses(200, 'sw-all.xml')
        FeedFactory.create(user=user, category__user=user)

        url = reverse('feeds:unread')
        response = self.app.get(url, user=user)
        first_title = response.context['entries'].object_list[0].title
        last_title = response.context['entries'].object_list[-1].title

        user.oldest_first = True
        user.save()
        response = self.app.get(url, user=user)
        self.assertEqual(response.context['entries'].object_list[0].title,
                         last_title)
        self.assertEqual(response.context['entries'].object_list[-1].title,
                         first_title)

    @patch('requests.get')
    def test_last_entry(self, get):
        user = UserFactory.create()
        get.return_value = responses(200, 'sw-all.xml')
        feed = FeedFactory.create(category__user=user, user=user)

        with self.assertNumQueries(2):
            update_feed(feed.url)
        self.assertEqual(Feed.objects.get().unread_count,
                         user.entries.filter(read=False).count())

        last_item = user.entries.order_by('date')[0]
        url = reverse('feeds:item', args=[last_item.pk])
        response = self.app.get(url, user=user)
        self.assertNotContains(response, 'Next →')

    def test_not_mocked(self):
        with self.assertRaises(ValueError):
            FeedFactory.create()

    @patch("requests.get")
    def test_img(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        feed = FeedFactory.create(category__user=user, url='http://exmpl.com',
                                  user=user)
        entry = Entry.objects.create(
            feed=feed,
            title="Random title",
            subtitle='<img src="/favicon.png">',
            link='http://example.com',
            date=timezone.now(),
            user=user,
        )
        url = reverse('feeds:item', args=[entry.pk])
        response = self.app.get(url, user=user)
        self.assertContains(response, 'External media is hidden')
        self.assertNotContains(response,
                               '<img src="http://exmpl.com/favicon.png">')
        self.assertEqual(Feed.objects.get(pk=feed.pk).media_safe, False)

        form = response.forms['images']
        response = form.submit(name='once')
        self.assertContains(response, 'Always display external media')
        self.assertContains(response,
                            '<img src="http://exmpl.com/favicon.png">')
        self.assertEqual(Feed.objects.get(pk=feed.pk).media_safe, False)
        form = response.forms['images']
        response = form.submit(name='always')
        self.assertContains(response, 'Disable external media')
        self.assertContains(response,
                            '<img src="http://exmpl.com/favicon.png">')
        self.assertEqual(Feed.objects.get(pk=feed.pk).media_safe, True)
        form = response.forms['images']
        response = form.submit(name='never')
        self.assertNotContains(response, 'Disable external media')
        self.assertEqual(Feed.objects.get(pk=feed.pk).media_safe, False)

        user.allow_media = True
        user.save(update_fields=['allow_media'])
        response = form.submit(name='never')
        self.assertFalse('images' in response.forms)
        self.assertContains(response,
                            '<img src="http://exmpl.com/favicon.png">')

    @patch("requests.get")
    def test_actions(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        feed = FeedFactory.create(category__user=user, url='http://exmpl.com',
                                  user=user)
        entry = Entry.objects.create(
            feed=feed,
            title="Random title",
            subtitle='Foo bar content',
            link='http://example.com',
            date=timezone.now(),
            user=user,
        )
        url = reverse('feeds:item', args=[entry.pk])
        response = self.app.get(url, user=user)
        token = response.forms['unread'].fields['csrfmiddlewaretoken'][0].value
        response = self.app.post(url, {'action': 'invalid',
                                       'csrfmiddlewaretoken': token},
                                 user=user)

        form = response.forms['star']
        response = form.submit()
        self.assertTrue(Entry.objects.get().starred)
        form = response.forms['star']
        response = form.submit()
        self.assertFalse(Entry.objects.get().starred)

        user.oldest_first = True
        user.save(update_fields=['oldest_first'])

        form = response.forms['unread']
        response = form.submit()
        self.assertFalse(Entry.objects.get().read)

    @patch('requests.get')
    def test_opml_import(self, get):
        user = UserFactory.create()
        url = reverse('feeds:import_feeds')
        response = self.app.get(url, user=user)

        get.return_value = responses(304)
        form = response.forms['import']

        with open(data_file('sample.opml'), 'rb') as opml_file:
            form['file'] = 'sample.opml', opml_file.read()
        response = form.submit().follow()

        self.assertContains(response, '2 feeds have been imported')

        # Re-import
        with open(data_file('sample.opml'), 'rb') as opml_file:
            form['file'] = 'sample.opml', opml_file.read()
        response = form.submit().follow()
        self.assertContains(response, '0 feeds have been imported')

        # Import an invalid thing
        form['file'] = 'invalid', b"foobar"
        response = form.submit()
        self.assertFormError(response, 'form', 'file', [
            "This file doesn't seem to be a valid OPML file."
        ])

        # Empty file
        form['file'] = 'name', b""
        response = form.submit()
        self.assertFormError(response, 'form', 'file', [
            "The submitted file is empty."
        ])

    @patch('requests.get')
    def test_greader_opml_import(self, get):
        user = UserFactory.create()
        url = reverse('feeds:import_feeds')
        response = self.app.get(url, user=user)

        get.return_value = responses(304)
        form = response.forms['import']

        with open(data_file('google-reader-subscriptions.xml'),
                  'rb') as opml_file:
            form['file'] = 'sample.opml', opml_file.read()
        response = form.submit().follow()

        self.assertContains(response, '1 feed has been imported')
        self.assertEqual(Category.objects.count(), 0)

    @patch('requests.get')
    def test_categories_in_opml(self, get):
        user = UserFactory.create()
        url = reverse('feeds:import_feeds')
        response = self.app.get(url, user=user)
        self.assertEqual(response.status_code, 200)

        get.return_value = responses(304)

        form = response.forms["import"]

        with open(data_file('categories.opml'), 'rb') as opml_file:
            form['file'] = 'categories.opml', opml_file.read()

        response = form.submit().follow()
        self.assertContains(response, '20 feeds have been imported')
        self.assertEqual(user.categories.count(), 6)
        with self.assertRaises(Category.DoesNotExist):
            user.categories.get(name='Imported')
        with self.assertRaises(Feed.DoesNotExist):
            Feed.objects.get(
                category__in=user.categories.all(),
                name='No title',
            )

        for c in Category.objects.all():
            c.get_absolute_url()

    @patch('requests.get')
    def test_dashboard(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        url = reverse('feeds:dashboard')
        FeedFactory.create(category=None, user=user)
        for i in range(5):
            FeedFactory.create(category__user=user, user=user)
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Dashboard')

    @patch('requests.get')
    def test_unread_dashboard(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        url = reverse('feeds:unread_dashboard')
        FeedFactory.create(category=None, user=user)
        for i in range(5):
            FeedFactory.create(category__user=user, user=user)
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Dashboard')

    @patch('requests.get')
    def test_unread_count(self, get):
        """Unread feed count everywhere"""
        user = UserFactory.create(ttl=99999)
        url = reverse('profile')
        response = self.app.get(url, user=user)
        self.assertContains(
            response,
            '<a class="unread" title="Unread entries" href="/unread/">0</a>'
        )

        get.return_value = responses(200, 'sw-all.xml')
        FeedFactory.create(category__user=user, user=user)

        response = self.app.get(url, user=user)
        self.assertContains(
            response,
            '<a class="unread" title="Unread entries" href="/unread/">30</a>'
        )

    @patch('requests.get')
    def test_mark_as_read(self, get):
        get.return_value = responses(304)
        user = UserFactory.create(ttl=99999)
        feed = FeedFactory.create(category__user=user, user=user)
        url = reverse('feeds:unread')
        response = self.app.get(url, user=user)
        self.assertNotContains(response, '"Mark all as read"')

        get.return_value = responses(200, 'sw-all.xml')
        update_feed(feed.url)

        response = self.app.get(url, user=user)
        self.assertContains(response, '"Mark all as read"')

        form = response.forms['read-all']
        response = form.submit()
        self.assertRedirects(response, url)
        response = response.follow()
        self.assertContains(response, '30 entries have been marked as read')

        self.assertEqual(user.entries.filter(read=False).count(), 0)
        self.assertEqual(user.entries.filter(read=True).count(), 30)

        form = response.forms['undo']
        response = form.submit()
        self.assertRedirects(response, url)
        response = response.follow()
        self.assertContains(response, "30 entries have been marked as unread")

        self.assertEqual(user.entries.filter(read=False).count(), 30)
        self.assertEqual(user.entries.filter(read=True).count(), 0)

        form = response.forms['read-page']
        some_entries = user.entries.all()[:5].values_list('pk', flat=True)
        form['entries'] = json.dumps(list(some_entries))
        response = form.submit()
        self.assertRedirects(response, url)
        response = response.follow()
        self.assertContains(response, "5 entries have been marked as read")

    @patch('requests.get')
    def test_promote_html_content_type(self, get):
        get.return_value = responses(200, 'content-description.xml')
        feed = FeedFactory.create(user__ttl=99999)
        self.assertEqual(
            len(feed.entries.all()[0].content.split('F&#233;vrier 1953')), 2)

    @patch('requests.get')
    @patch('requests.post')
    def test_add_to_readability(self, post, get):  # noqa
        post.return_value = responses(202, headers={
            'location': 'https://www.readability.com/api/rest/v1/bookmarks/19',
        })

        user = UserFactory.create(
            read_later='readability',
            read_later_credentials=json.dumps({
                'oauth_token': 'token',
                'oauth_token_secret': 'token secret',
            }),
        )

        get.return_value = responses(200, 'sw-all.xml')
        feed = FeedFactory.create(category__user=user, user=user)
        get.assert_called_once_with(
            feed.url,
            headers={'User-Agent': USER_AGENT % '1 subscriber',
                     'Accept': feedparser.ACCEPT_HEADER}, timeout=10)

        get.reset_mock()
        get.return_value = responses(200, data=json.dumps(
            {'article': {'id': 'foo'}}))

        entry_pk = Entry.objects.all()[0].pk
        url = reverse('feeds:item', args=[entry_pk])
        response = self.app.get(url, user=user)
        self.assertContains(response, "Add to Readability")

        form = response.forms['read-later']
        response = form.submit()
        self.assertEqual(len(post.call_args_list), 1)
        self.assertEqual(len(get.call_args_list), 1)
        args, kwargs = post.call_args
        self.assertEqual(
            args, ('https://www.readability.com/api/rest/v1/bookmarks',))
        self.assertEqual(kwargs['data'], {
            'url': 'http://simonwillison.net/2010/Mar/12/re2/'})
        args, kwargs = get.call_args
        self.assertEqual(
            args, ('https://www.readability.com/api/rest/v1/bookmarks/19',))
        self.assertEqual(Entry.objects.get(pk=entry_pk).read_later_url,
                         'https://www.readability.com/articles/foo')
        response = self.app.get(url, user=user)
        self.assertNotContains(response, "Add to Instapaper")

    @patch("requests.get")
    @patch('requests.post')
    def test_add_to_instapaper(self, post, get):  # noqa
        post.return_value = responses(200, data=json.dumps([{
            'type': 'bookmark', 'bookmark_id': 12345,
            'title': 'Some bookmark',
            'url': 'http://example.com/some-bookmark',
        }]))

        user = UserFactory.create(
            read_later='instapaper',
            read_later_credentials=json.dumps({
                'oauth_token': 'token',
                'oauth_token_secret': 'token secret',
            }),
        )
        get.return_value = responses(304)
        feed = FeedFactory.create(category__user=user, user=user)

        get.reset_mock()
        get.return_value = responses(200, 'sw-all.xml')

        update_feed(feed.url)
        get.assert_called_once_with(
            feed.url,
            headers={'User-Agent': USER_AGENT % '1 subscriber',
                     'Accept': feedparser.ACCEPT_HEADER}, timeout=10)

        entry_pk = Entry.objects.all()[0].pk
        url = reverse('feeds:item', args=[entry_pk])
        response = self.app.get(url, user=user)
        self.assertContains(response, "Add to Instapaper")

        form = response.forms['read-later']
        response = form.submit()
        self.assertEqual(len(post.call_args_list), 1)
        args, kwargs = post.call_args
        self.assertEqual(args,
                         ('https://www.instapaper.com/api/1/bookmarks/add',))
        self.assertEqual(kwargs['data'],
                         {'url': 'http://simonwillison.net/2010/Mar/12/re2/'})
        self.assertEqual(Entry.objects.get(pk=entry_pk).read_later_url,
                         'https://www.instapaper.com/read/12345')
        response = self.app.get(url, user=user)
        self.assertNotContains(response, "Add to Instapaper")

    @patch('requests.get')
    @patch('requests.post')
    def test_add_to_readitlaterlist(self, post, get):
        user = UserFactory.create(
            read_later='readitlater',
            read_later_credentials=json.dumps({'username': 'foo',
                                               'password': 'bar'}),
        )

        get.return_value = responses(200, 'sw-all.xml')
        feed = FeedFactory.create(category__user=user, user=user)
        get.assert_called_with(
            feed.url,
            headers={'User-Agent': USER_AGENT % '1 subscriber',
                     'Accept': feedparser.ACCEPT_HEADER}, timeout=10)

        url = reverse('feeds:item', args=[Entry.objects.all()[0].pk])
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Add to Read it later')
        form = response.forms['read-later']
        response = form.submit()
        # Read it Later doesn't provide the article URL so we can't display a
        # useful link
        self.assertContains(response, "added to your reading list")
        post.assert_called_with(
            'https://readitlaterlist.com/v2/add',
            data={u'username': u'foo',
                  'url': u'http://simonwillison.net/2010/Mar/12/re2/',
                  'apikey': 'test read it later API key',
                  u'password': u'bar',
                  'title': (u'RE2: a principled approach to regular '
                            u'expression matching')},
        )

    @patch('requests.get')
    def test_pubsubhubbub_handling(self, get):
        user = UserFactory.create(ttl=99999)
        url = 'http://bruno.im/atom/tag/django-community/'
        get.return_value = responses(304)
        feed = FeedFactory.create(url=url, category__user=user, user=user)
        get.assert_called_with(
            url, headers={'User-Agent': USER_AGENT % '1 subscriber',
                          'Accept': feedparser.ACCEPT_HEADER},
            timeout=10)

        self.assertEqual(feed.entries.count(), 0)
        path = data_file('bruno.im.atom')
        with open(path, 'r') as f:
            data = f.read()
        updated.send(sender=None, notification=data, request=None, links=None)
        self.assertEqual(feed.entries.count(), 5)

        # Check content handling
        for entry in feed.entries.all():
            self.assertTrue(len(entry.subtitle) > 2400)

        # Check date handling
        self.assertEqual(feed.entries.filter(date__year=2011).count(), 3)
        self.assertEqual(feed.entries.filter(date__year=2012).count(), 2)

    @patch('requests.get')
    def test_missing_links(self, get):
        path = data_file('no-rel.atom')
        with open(path, 'r') as f:
            data = f.read()
        updated.send(sender=None, notification=data, request=None, links=None)

    @patch('requests.get')
    def test_link_headers(self, get):
        user = UserFactory.create(ttl=99999)
        url = 'foo'
        get.return_value = responses(304)
        feed = FeedFactory.create(url=url, category__user=user, user=user)

        path = data_file('no-rel.atom')
        with open(path, 'r') as f:
            data = f.read()
        updated.send(sender=None, notification=data, request=None,
                     links=[{'url': 'foo', 'rel': 'self'}])
        self.assertEqual(feed.entries.count(), 1)

    @patch('requests.get')
    def test_subscribe_url(self, get):
        get.return_value = responses(304)

        user = UserFactory.create()
        c = CategoryFactory.create(user=user)

        url = reverse('feeds:subscribe')
        response = self.app.get(url, {'feeds': "http://bruno.im/atom/latest/"},
                                user=user)

        self.assertContains(response, 'value="http://bruno.im/atom/latest/"')
        form = response.forms['subscribe']

        response = form.submit()
        self.assertContains(response, 'This field is required.', 1)

        form['form-0-name'] = "Bruno's awesome blog"
        form['form-0-category'] = c.pk

        self.assertEqual(Feed.objects.count(), 0)
        response = form.submit().follow()
        self.assertEqual(Feed.objects.count(), 1)

        form['form-0-name'] = ""
        form['form-0-category'] = ""
        form['form-0-subscribe'] = False
        response = form.submit().follow()
        self.assertContains(response, '0 feeds have been added')

        form['form-0-name'] = 'Foo'
        form['form-0-category'] = c.pk
        form['form-0-subscribe'] = True
        response = form.submit()
        self.assertContains(response, "already subscribed")

        u = UniqueFeed.objects.create(url='http://example.com/feed')
        u.schedule()
        patch_job(u.url, title='Awesome')
        response = self.app.get(
            url, {'feeds': ",".join(['http://bruno.im/atom/latest/',
                                     'http://example.com/feed'])})
        form = response.forms['subscribe']
        self.assertEqual(form['form-0-name'].value, 'Awesome')
        response = form.submit().follow()
        self.assertEqual(Feed.objects.count(), 2)

    def test_bookmarklet_no_feed(self):
        user = UserFactory.create()
        url = reverse('feeds:subscribe')
        response = self.app.get(url, {'url': 'http://isitbeeroclock.com/'},
                                user=user)
        self.assertContains(
            response, ('it looks like there are no feeds available on '
                       '<a href="http://isitbeeroclock.com/">'))

    @patch("requests.get")
    def test_relative_links(self, get):
        get.return_value = responses(200, path='brutasse.atom')

        user = UserFactory.create(ttl=99999)
        FeedFactory.create(category__user=user, user=user,
                           url='https://github.com/brutasse.atom')
        entry = user.entries.all()[0]

        self.assertTrue('<a href="/brutasse"' in entry.subtitle)
        self.assertFalse('<a href="/brutasse"' in entry.content)
        self.assertTrue(
            '<a href="https://github.com/brutasse"' in entry.content)

        feed = Feed(url='http://standblog.org/blog/feed/rss2')
        e = Entry(feed=feed, subtitle=(
            ' <p><img alt=":-)" class="smiley"'
            'src="/dotclear2/themes/default/smilies/smile.png" /> . </p>'
        ))
        self.assertTrue(('src="http://standblog.org/dotclear2/themes/'
                         'default/smilies/smile.png"') in e.content)

    @patch('requests.get')
    def test_empty_subtitle(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        entry = EntryFactory(user=user, feed__category__user=user, subtitle='')
        url = reverse('feeds:item', args=[entry.pk])
        self.app.get(url, user=user)

    def test_smart_date(self):
        now = timezone.now()
        self.assertEqual(len(smart_date(now)), 5)

        if now.day != 1 and now.month != 1:  # Can't test this on Jan 1st :)
            now = now - timedelta(days=1)
            self.assertEqual(len(smart_date(now)), 6)

        now = now - timedelta(days=366)
        self.assertEqual(len(smart_date(now)), 12)

    @patch('requests.get')
    def test_manage_feed(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        url = reverse('feeds:manage')
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Manage feeds')

        FeedFactory.create(user=user, category=None)
        FeedFactory.create(user=user, category=None)
        FeedFactory.create(user=user, category=None)
        unique = UniqueFeed.objects.all()[0]
        schedule_job(unique.url, schedule_in=0, backoff_factor=10,
                     error=UniqueFeed.NOT_A_FEED,
                     connection=get_redis_connection())

        response = self.app.get(url, user=user)
        self.assertContains(response, 'Not a valid RSS/Atom feed')

        schedule_job(unique.url, schedule_in=0, error='blah',
                     connection=get_redis_connection())
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Error')

        unique.muted = True
        unique.save()
        response = self.app.get(url, user=user)
        self.assertContains(response, 'Error')

########NEW FILE########
__FILENAME__ = test_fetching
import feedparser
import socket

from django.core.management import call_command
from django.utils import timezone
from django_push.subscriber.models import Subscription
from mock import patch, PropertyMock
from rache import job_details, schedule_job
from requests import RequestException
from requests.packages.urllib3.exceptions import (LocationParseError,
                                                  DecodeError)
from rq.timeouts import JobTimeoutException
from six.moves.http_client import IncompleteRead

from feedhq.feeds.models import Favicon, UniqueFeed, Feed, Entry
from feedhq.feeds.tasks import update_feed
from feedhq.feeds.utils import FAVICON_FETCHER, USER_AGENT, epoch_to_utc
from feedhq.utils import get_redis_connection

from .factories import FeedFactory
from .test_feeds import data_file, responses
from . import ClearRedisTestCase, patch_job


class UpdateTests(ClearRedisTestCase):
    @patch("requests.get")
    def test_parse_error(self, get):
        get.side_effect = LocationParseError("Failed to parse url")
        FeedFactory.create()
        unique = UniqueFeed.objects.get()
        self.assertTrue(unique.muted)
        self.assertEqual(unique.error, UniqueFeed.PARSE_ERROR)

    @patch("requests.get")
    def test_decode_error(self, get):
        get.side_effect = DecodeError("Received response with content-encoding"
                                      ": gzip, but failed to decode it.")
        FeedFactory.create()
        unique = UniqueFeed.objects.get()
        data = job_details(unique.url, connection=get_redis_connection())
        self.assertEqual(data['backoff_factor'], 2)
        self.assertEqual(data['error'], UniqueFeed.DECODE_ERROR)

    @patch("requests.get")
    def test_incomplete_read(self, get):
        get.side_effect = IncompleteRead("0 bytes read")
        FeedFactory.create()
        f = UniqueFeed.objects.get()
        self.assertFalse(f.muted)
        data = job_details(f.url, connection=get_redis_connection())
        self.assertEqual(data['error'], f.CONNECTION_ERROR)

    @patch("requests.get")
    def test_socket_timeout(self, get):
        m = get.return_value
        type(m).content = PropertyMock(side_effect=socket.timeout)
        FeedFactory.create()
        f = UniqueFeed.objects.get()
        self.assertFalse(f.muted)
        data = job_details(f.url, connection=get_redis_connection())
        self.assertEqual(data['error'], f.TIMEOUT)

    @patch('requests.get')
    def test_ctype(self, get):
        # Updatefeed doesn't fail if content-type is missing
        get.return_value = responses(200, 'sw-all.xml', headers={})
        feed = FeedFactory.create()
        update_feed(feed.url)
        get.assert_called_with(
            feed.url,
            headers={'User-Agent': USER_AGENT % '1 subscriber',
                     'Accept': feedparser.ACCEPT_HEADER}, timeout=10)

        get.return_value = responses(200, 'sw-all.xml',
                                     headers={'Content-Type': None})
        update_feed(feed.url)
        get.assert_called_with(
            feed.url,
            headers={'User-Agent': USER_AGENT % '1 subscriber',
                     'Accept': feedparser.ACCEPT_HEADER}, timeout=10)

    @patch('requests.get')
    def test_permanent_redirects(self, get):
        """Updating the feed if there's a permanent redirect"""
        get.return_value = responses(
            301, redirection='permanent-atom10.xml',
            headers={'Content-Type': 'application/rss+xml'})
        feed = FeedFactory.create()
        feed = Feed.objects.get(pk=feed.id)
        self.assertEqual(feed.url, 'permanent-atom10.xml')

    @patch('requests.get')
    def test_temporary_redirect(self, get):
        """Don't update the feed if the redirect is not 301"""
        get.return_value = responses(
            302, redirection='atom10.xml',
            headers={'Content-Type': 'application/rss+xml'})
        feed = FeedFactory.create()
        get.assert_called_with(
            feed.url, timeout=10,
            headers={'User-Agent': USER_AGENT % '1 subscriber',
                     'Accept': feedparser.ACCEPT_HEADER},
        )
        feed = Feed.objects.get(pk=feed.id)
        self.assertNotEqual(feed.url, 'atom10.xml')

    @patch('requests.get')
    def test_content_handling(self, get):
        """The content section overrides the subtitle section"""
        get.return_value = responses(200, 'atom10.xml')
        FeedFactory.create(name='Content', url='atom10.xml', user__ttl=99999)
        entry = Entry.objects.get()
        self.assertEqual(entry.sanitized_content(),
                         "<div>Watch out for <span> nasty tricks</span></div>")

        self.assertEqual(entry.author, 'Mark Pilgrim (mark@example.org)')

    @patch('requests.get')
    def test_gone(self, get):
        """Muting the feed if the status code is 410"""
        get.return_value = responses(410)
        FeedFactory.create(url='gone.xml')
        feed = UniqueFeed.objects.get(url='gone.xml')
        self.assertTrue(feed.muted)

    @patch('requests.get')
    def test_errors(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create()

        for code in [400, 401, 403, 404, 500, 502, 503]:
            get.return_value = responses(code)
            feed = UniqueFeed.objects.get(url=feed.url)
            self.assertFalse(feed.muted)
            self.assertEqual(feed.job_details.get('error'), None)
            self.assertEqual(feed.job_details['backoff_factor'], 1)
            feed.schedule()
            data = job_details(feed.url, connection=get_redis_connection())

            update_feed(feed.url, backoff_factor=data['backoff_factor'])

            feed = UniqueFeed.objects.get(url=feed.url)
            self.assertFalse(feed.muted)
            data = job_details(feed.url, connection=get_redis_connection())
            self.assertEqual(data['error'], code)
            self.assertEqual(data['backoff_factor'], 2)

            # Restore status for next iteration
            schedule_job(feed.url, backoff_factor=1, error=None, schedule_in=0)

    @patch('requests.get')
    def test_too_many_requests(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create()

        get.return_value = responses(429)
        update_feed(feed.url, backoff_factor=1)
        data = job_details(feed.url, connection=get_redis_connection())
        # retry in 1 min
        self.assertTrue(
            58 <
            (epoch_to_utc(data['schedule_at']) - timezone.now()).seconds <
            60
        )

    @patch('requests.get')
    def test_too_many_requests_retry(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create()

        get.return_value = responses(429, headers={'Retry-After': '3600'})
        update_feed(feed.url, backoff_factor=1)
        data = job_details(feed.url, connection=get_redis_connection())
        # Retry in 1 hour
        self.assertTrue(
            3590 <
            (epoch_to_utc(data['schedule_at']) - timezone.now()).seconds <
            3600
        )

        # Other requests to same domain
        get.reset_mock()
        get.assert_not_called()
        update_feed(feed.url, backoff_factor=1)
        get.assert_not_called()

    @patch('requests.get')
    def test_backoff(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create()
        feed = UniqueFeed.objects.get(url=feed.url)
        detail = feed.job_details
        self.assertFalse('error' in detail)
        self.assertEqual(detail['backoff_factor'], 1)
        feed.schedule()
        data = job_details(feed.url, connection=get_redis_connection())

        get.return_value = responses(502)
        for i in range(12):
            update_feed(feed.url, backoff_factor=data['backoff_factor'])
            feed = UniqueFeed.objects.get(url=feed.url)
            self.assertFalse(feed.muted)
            data = job_details(feed.url, connection=get_redis_connection())
            self.assertEqual(data['error'], 502)
            self.assertEqual(data['backoff_factor'], min(i + 2, 10))

        get.side_effect = RequestException
        feed = UniqueFeed.objects.get()
        patch_job(feed.url, error=None, backoff_factor=1)
        data = job_details(feed.url, connection=get_redis_connection())

        for i in range(12):
            update_feed(feed.url, backoff_factor=data['backoff_factor'])
            feed = UniqueFeed.objects.get(url=feed.url)
            self.assertFalse(feed.muted)
            data = job_details(feed.url, connection=get_redis_connection())
            self.assertEqual(data['error'], 'timeout')
            self.assertEqual(data['backoff_factor'], min(i + 2, 10))

    @patch("requests.get")
    def test_etag_modified(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create()
        update_feed(feed.url, etag='etag', modified='1234', subscribers=2)
        get.assert_called_with(
            feed.url,
            headers={
                'User-Agent': USER_AGENT % '2 subscribers',
                'Accept': feedparser.ACCEPT_HEADER,
                'If-None-Match': b'etag',
                'If-Modified-Since': b'1234',
            }, timeout=10)

    @patch("requests.get")
    def test_restore_backoff(self, get):
        get.return_value = responses(304)
        FeedFactory.create()
        feed = UniqueFeed.objects.get()
        feed.error = 'timeout'
        feed.backoff_factor = 5
        feed.save()
        update_feed(feed.url, error=feed.error,
                    backoff_factor=feed.backoff_factor)

        data = job_details(feed.url, connection=get_redis_connection())
        self.assertEqual(data['backoff_factor'], 1)
        self.assertTrue('error' not in data)

    @patch('requests.get')
    def test_no_date_and_304(self, get):
        """If the feed does not have a date, we'll have to find one.
        Also, since we update it twice, the 2nd time it's a 304 response."""
        get.return_value = responses(200, 'no-date.xml')
        feed = FeedFactory.create()

        # Update the feed twice and make sure we don't index the content twice
        update_feed(feed.url)
        feed1 = Feed.objects.get(pk=feed.id)
        count1 = feed1.entries.count()

        update_feed(feed1.url)
        feed2 = Feed.objects.get(pk=feed1.id)
        count2 = feed2.entries.count()

        self.assertEqual(count1, count2)

    @patch("requests.get")
    def test_uniquefeed_deletion(self, get):
        get.return_value = responses(304)
        f = UniqueFeed.objects.create(url='example.com')
        self.assertEqual(UniqueFeed.objects.count(), 1)
        call_command('delete_unsubscribed')
        UniqueFeed.objects.update_feed(f.url)
        self.assertEqual(UniqueFeed.objects.count(), 0)

    @patch('requests.get')
    def test_no_link(self, get):
        get.return_value = responses(200, 'rss20.xml')
        feed = FeedFactory.create(user__ttl=99999)
        update_feed(feed.url)
        self.assertEqual(Entry.objects.count(), 1)

        get.return_value = responses(200, 'no-link.xml')
        feed.url = 'no-link.xml'
        feed.save(update_fields=['url'])
        update_feed(feed.url)
        self.assertEqual(Entry.objects.count(), 1)

    @patch('requests.get')
    def test_task_timeout_handling(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create()
        get.side_effect = JobTimeoutException
        self.assertEqual(
            UniqueFeed.objects.get().job_details['backoff_factor'], 1)
        update_feed(feed.url)
        data = job_details(feed.url, connection=get_redis_connection())
        self.assertEqual(data['backoff_factor'], 2)

    @patch('requests.post')
    def test_sync_pubsub(self, post):
        post.return_value = responses(202, 'sw-all.xml')
        call_command('sync_pubsubhubbub')
        post.assert_not_called()

        u = UniqueFeed.objects.create(url='http://example.com')
        Subscription.objects.create(topic=u.url,
                                    hub='http://hub.example.com',
                                    verified=True,
                                    lease_expiration=timezone.now())

        call_command('sync_pubsubhubbub')
        post.assert_called()
        post.reset()

        u.delete()
        call_command('sync_pubsubhubbub')
        post.assert_called()
        post.reset()

        call_command('sync_pubsubhubbub')
        post.assert_not_called()


class FaviconTests(ClearRedisTestCase):
    @patch("requests.get")
    def test_declared_favicon(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create(url='http://example.com/feed')
        patch_job(feed.url, link='http://example.com')

        with open(data_file('bruno.im.png'), 'rb') as f:
            fav = f.read()

        class Response:
            status_code = 200
            content = fav
            headers = {'foo': 'bar'}
        get.reset_mock()
        get.return_value = Response()
        Favicon.objects.update_favicon(feed.url)
        get.assert_called_with(
            'http://example.com/favicon.ico',
            headers={'User-Agent': FAVICON_FETCHER},
            timeout=10,
        )

    @patch("requests.get")
    def test_favicon_empty_document(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create(url='http://example.com/feed')
        patch_job(feed.url, link='http://example.com')

        class Response:
            status_code = 200
            content = '<?xml version="1.0" encoding="iso-8859-1"?>'
            headers = {}
        get.return_value = Response()
        Favicon.objects.update_favicon(feed.url)

    @patch("requests.get")
    def test_favicon_parse_error(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create(url='http://example.com/feed')
        patch_job(feed.url, link='http://example.com')

        get.side_effect = LocationParseError("Failed to parse url")
        Favicon.objects.update_favicon(feed.url)

########NEW FILE########
__FILENAME__ = test_models
# -*- coding: utf-8 -*-
from datetime import timedelta
from django.utils import timezone
from mock import patch
from rache import job_details, schedule_job

from feedhq.feeds.models import (Category, Feed, UniqueFeed, Entry, Favicon,
                                 UniqueFeedManager)
from feedhq.feeds.tasks import update_feed
from feedhq.utils import get_redis_connection

from .factories import CategoryFactory, FeedFactory
from . import responses, ClearRedisTestCase


class ModelTests(ClearRedisTestCase):
    def test_category_model(self):
        """Behaviour of the ``Category`` model"""
        cat = CategoryFactory.create(name='New Cat', slug='new-cat')

        cat_from_db = Category.objects.get(pk=cat.id)

        # __unicode__
        self.assertEqual('%s' % cat_from_db, 'New Cat')

        # get_absolute_url()
        self.assertEqual('/category/new-cat/', cat_from_db.get_absolute_url())

    @patch('requests.get')
    def test_feed_model(self, get):
        """Behaviour of the ``Feed`` model"""
        get.return_value = responses(200, 'rss20.xml')
        feed = FeedFactory.create(name='RSS test', url='rss20.xml',
                                  user__ttl=99999)
        feed.save()

        feed_from_db = Feed.objects.get(pk=feed.id)

        # __unicode__
        self.assertEqual('%s' % feed_from_db, 'RSS test')

        # get_absolute_url()
        self.assertEqual('/feed/%s/' % feed.id, feed.get_absolute_url())

        # update()
        update_feed(feed.url)

        data = job_details(feed.url, connection=get_redis_connection())

        self.assertEqual(data['title'], 'Sample Feed')
        self.assertEqual(data['link'], 'http://example.org/')

        feed = Feed.objects.get(pk=feed.id)
        self.assertEqual(feed.entries.count(), 1)
        self.assertEqual(feed.entries.all()[0].title, 'First item title')

        self.assertEqual(feed.favicon_img(), '')
        feed.favicon = 'fav.png'
        self.assertEqual(feed.favicon_img(),
                         '<img src="/media/fav.png" width="16" height="16" />')

    @patch('requests.get')
    def test_entry_model(self, get):
        get.return_value = responses(200, 'sw-all.xml')
        feed = FeedFactory.create()
        update_feed(feed.url)
        title = 'RE2: a principled approach to regular expression matching'
        entry = Entry.objects.get(title=title)

        # __unicode__
        self.assertEqual('%s' % entry, title)

        entry.title = ''
        self.assertEqual(entry.sanitized_title(), '(No title)')

        entry.title = 'Foo'
        entry.link = 'http://example.com/foo'
        self.assertEqual(entry.tweet(),
                         u'Foo — http://example.com/foo')

    @patch('requests.get')
    def test_uniquefeed_model(self, get):
        get.return_value = responses(304)
        FeedFactory.create(url='http://example.com/' + 'foo/' * 200)
        unique = UniqueFeed.objects.get()
        self.assertEqual(len(unique.truncated_url()), 50)

        unique.delete()

        FeedFactory.create(url='http://example.com/foo/')
        unique = UniqueFeed.objects.get()
        self.assertEqual(len(unique.truncated_url()), len(unique.url))

        unique = UniqueFeed(url='http://foo.com')
        self.assertEqual('%s' % unique, 'http://foo.com')

        self.assertIs(UniqueFeedManager.entry_data({}, None), None)

        unique.schedule()
        details = unique.job_details
        at = details.pop('schedule_at')
        details.pop('last_update')
        self.assertEqual(details, {
            u"backoff_factor": 1,
            u"subscribers": 1,
            u"id": "http://foo.com",
        })
        details['schedule_at'] = at
        self.assertEqual(unique.job_details['id'], "http://foo.com")

        self.assertTrue(unique.scheduler_data.startswith("{\n"))

        self.assertTrue(unique.next_update > timezone.now())
        self.assertTrue(unique.next_update <
                        timezone.now() + timedelta(seconds=60 * 61))

        schedule_job(unique.url, title='Lol', schedule_in=0)
        del unique._job_details
        details = unique.job_details
        details.pop('schedule_at')
        details.pop('last_update')
        self.assertEqual(details, {
            u"title": u"Lol",
            u"backoff_factor": 1,
            u"subscribers": 1,
            u"id": "http://foo.com",
        })

    def test_favicon_model(self):
        fav = Favicon(url='http://example.com/')
        self.assertEqual('%s' % fav, 'Favicon for http://example.com/')
        self.assertEqual(fav.favicon_img(), '(None)')
        fav.favicon = 'foo.png'
        self.assertEqual(fav.favicon_img(), '<img src="/media/foo.png">')

    @patch("requests.get")
    def test_entry_model_behaviour(self, get):
        """Behaviour of the `Entry` model"""
        get.return_value = responses(304)
        feed = FeedFactory.create()
        entry = feed.entries.create(title='My title',
                                    user=feed.category.user,
                                    date=timezone.now())
        # __unicode__
        self.assertEqual('%s' % entry, 'My title')

        # get_absolute_url()
        self.assertEqual('/entries/%s/' % entry.id, entry.get_absolute_url())

    @patch("requests.get")
    def test_handle_etag(self, get):
        get.return_value = responses(200, 'sw-all.xml',
                                     headers={'etag': 'foo',
                                              'last-modified': 'bar'})
        FeedFactory.create()
        data = job_details(UniqueFeed.objects.get().url,
                           connection=get_redis_connection())
        self.assertEqual(data['etag'], 'foo')
        self.assertEqual(data['modified'], 'bar')

    @patch('requests.get')
    def test_invalid_content(self, get):
        """Behaviour of the ``Feed`` model"""
        get.return_value = responses(304)
        feed = Feed(url='http://example.com/')
        entry = Entry(
            feed=feed,
            subtitle='<a href="http://mozillaopennews.org]/">OpenNews</a>')
        self.assertEqual(
            entry.content,
            '<a href="http://mozillaopennews.org%5D/">OpenNews</a>')

    def test_not_scheduled_last_update(self):
        u = UniqueFeed('ĥttp://example.com')
        self.assertIsNone(u.last_update)

########NEW FILE########
__FILENAME__ = test_profiles
import json

from django.core.urlresolvers import reverse

from django_webtest import WebTest
from mock import patch

from feedhq.profiles.models import User

from . import responses


class ProfilesTest(WebTest):
    def setUp(self):  # noqa
        self.user = User.objects.create_user('test', 'test@example.com',
                                             'pass')

    def test_profile(self):
        url = reverse('stats')
        response = self.app.get(url, user='test')
        self.assertContains(response, 'Stats')
        self.assertContains(response, '0 feeds')

    def test_change_password(self):
        url = reverse('password')
        response = self.app.get(url, user='test')
        self.assertContains(response, 'Change your password')

        form = response.forms['password']

        data = {
            'current_password': 'lol',
            'new_password': 'foo',
            'new_password2': 'bar',
        }
        for key, value in data.items():
            form[key] = value
        response = form.submit()
        self.assertFormError(response, 'form', 'current_password',
                             'Incorrect password')
        self.assertFormError(response, 'form', 'new_password2',
                             "The two passwords didn't match")

        form['current_password'] = 'pass'
        form['new_password2'] = 'foo'

        response = form.submit().follow()
        self.assertContains(response, 'Your password was changed')

    def test_change_profile(self):
        url = reverse('profile')
        response = self.app.get(url, user='test')
        self.assertContains(response, 'Edit your profile')
        self.assertContains(response,
                            '<option value="UTC" selected="selected">')
        form = response.forms['profile']
        data = {
            'username': 'test',
            'entries_per_page': 25,
        }
        for key, value in data.items():
            form[key] = value
        form['timezone'].force_value('Foo/Bar')
        response = form.submit()
        self.assertFormError(
            response, 'form', 'timezone', (
                'Select a valid choice. Foo/Bar is not one of the '
                'available choices.'),
        )

        form['timezone'] = 'Europe/Paris'
        response = form.submit().follow()
        self.assertEqual(User.objects.get().timezone, 'Europe/Paris')

        form['entries_per_page'].force_value(12)
        response = form.submit()
        self.assertFormError(
            response, 'form', 'entries_per_page', (
                'Select a valid choice. 12 is not one of the '
                'available choices.'),
        )
        form['entries_per_page'] = 50
        response = form.submit().follow()
        self.assertEqual(User.objects.get().entries_per_page, 50)

        # changing a username
        new = User.objects.create_user('foobar', 'foo@bar.com', 'pass')

        form['username'] = 'foobar'
        response = form.submit()
        self.assertFormError(response, 'form', 'username',
                             'This username is already taken.')

        new.username = 'lol'
        new.save()

        self.assertEqual(User.objects.get(pk=self.user.pk).username, 'test')
        response = form.submit()
        self.assertEqual(User.objects.get(pk=self.user.pk).username, 'foobar')

    def test_read_later(self):
        url = reverse('read_later')
        response = self.app.get(url, user='test')

        self.assertContains(
            response,
            "You don't have any read-it-later service configured yet."
        )

    def test_sharing(self):
        url = reverse('sharing')
        response = self.app.get(url, user='test')
        form = response.forms['sharing']
        form['sharing_twitter'] = True
        response = form.submit().follow()
        self.assertTrue(User.objects.get().sharing_twitter)

    @patch("requests.get")
    def test_valid_readitlater_credentials(self, get):
        url = reverse('services', args=['readitlater'])
        response = self.app.get(url, user='test')
        self.assertContains(response, 'Read It Later')

        form = response.forms['readitlater']
        form['username'] = 'example'
        form['password'] = 'samplepassword'

        get.return_value.status_code = 200
        response = form.submit().follow()
        get.assert_called_with(
            'https://readitlaterlist.com/v2/auth',
            params={'username': u'example',
                    'apikey': 'test read it later API key',
                    'password': u'samplepassword'},
        )

        self.assertContains(response, ' as your reading list service')
        self.assertContains(response, ('Your current read-it-later service '
                                       'is: <strong>Read it later</strong>'))

        user = User.objects.get()
        self.assertEqual(user.read_later, 'readitlater')
        self.assertTrue(len(user.read_later_credentials) > 20)

    @patch("requests.get")
    def test_invalid_readitlater_credentials(self, get):
        url = reverse("services", args=['readitlater'])
        response = self.app.get(url, user='test')
        form = response.forms['readitlater']

        form['username'] = 'example'
        form['password'] = 'wrong password'

        get.return_value.status_code = 401
        response = form.submit()
        self.assertContains(
            response,
            'Unable to verify your readitlaterlist credentials',
        )

    @patch("requests.post")
    def test_valid_oauth_credentials(self, post):  # noqa
        post.return_value = responses(
            200, data="oauth_token=aabbccdd&oauth_token_secret=efgh1234")

        url = reverse("services", args=['readability'])
        response = self.app.get(url, user='test')
        form = response.forms['readability']
        form['username'] = 'example'
        form['password'] = 'correct password'
        response = form.submit().follow()
        self.assertContains(
            response,
            "You have successfully added Readability",
        )

        self.assertEqual(len(post.call_args_list), 1)
        args, kwargs = post.call_args
        self.assertEqual(kwargs['data'], {
            'x_auth_username': 'example',
            'x_auth_password': 'correct password',
            'x_auth_mode': 'client_auth'})

        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.read_later, 'readability')
        self.assertEqual(json.loads(user.read_later_credentials), {
            "oauth_token": "aabbccdd",
            "oauth_token_secret": "efgh1234",
        })

    @patch("requests.post")
    def test_invalid_oauth_credentials(self, post):
        post.return_value = responses(401, data='xAuth error')

        url = reverse("services", args=['instapaper'])
        response = self.app.get(url, user='test')
        form = response.forms['instapaper']
        data = {
            'username': 'example',
            'password': 'incorrect password',
        }
        for key, value in data.items():
            form[key] = value
        response = form.submit()
        self.assertContains(response, "Unable to verify")
        self.assertEqual(len(post.call_args_list), 1)
        args, kwargs = post.call_args
        self.assertEqual(kwargs['data'], {
            'x_auth_password': 'incorrect password',
            'x_auth_username': 'example',
            'x_auth_mode': 'client_auth'})

    def test_disable_read_later(self):
        """Removing read later credentials"""
        self.user.read_later = 'readability'
        self.user.read_later_credentials = '{"foo":"bar","baz":"bah"}'
        self.user.save()

        response = self.app.get(reverse('read_later'), user='test')
        url = reverse('services', args=['none'])
        self.assertContains(response, url)

        response = self.app.get(url, user='test')
        self.assertEqual(response.status_code, 200)
        form = response.forms['disable']
        response = form.submit().follow()
        self.assertContains(response, "disabled reading list integration")
        self.assertNotContains(response, url)

        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.read_later, '')
        self.assertEqual(user.read_later_credentials, '')

    def test_delete_account(self):
        self.assertEqual(User.objects.count(), 1)
        url = reverse('destroy_account')
        response = self.app.get(url, user='test')
        self.assertContains(response, 'Delete your account')

        form = response.forms['delete']
        form['password'] = 'test'
        response = form.submit()
        self.assertContains(response, 'The password you entered was incorrect')

        form['password'] = 'pass'
        response = form.submit().follow()
        self.assertContains(response, "Good bye")

    def test_login_via_username_or_email(self):
        url = reverse('login')

        response = self.app.get(url)
        self.assertContains(response, 'Username or Email')
        form = response.forms['login']

        form['username'] = 'test'
        form['password'] = 'pass'
        response = form.submit()
        self.assertRedirects(response, '/')

        self.renew_app()
        response = self.app.get(url)
        form = response.forms['login']

        form['username'] = 'test@example.com'
        form['password'] = 'pass'
        response = form.submit()
        self.assertRedirects(response, '/')

        self.renew_app()
        response = self.app.get(reverse('feeds:unread'))
        self.assertContains(response, 'Username or Email')

    def test_register_subtome(self):
        url = reverse('bookmarklet')
        response = self.app.get(url, user='test')
        self.assertContains(response, 'Subtome')
        self.assertContains(response, 'iframe')

########NEW FILE########
__FILENAME__ = test_reader_api
import json
import time

from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from django.utils import timezone
from mock import patch
from six.moves.urllib.parse import urlencode

from feedhq.feeds.models import Feed, Entry, UniqueFeed
from feedhq.reader.models import AuthToken
from feedhq.reader.views import GoogleReaderXMLRenderer, item_id
from feedhq.utils import get_redis_connection

from .factories import UserFactory, CategoryFactory, FeedFactory, EntryFactory
from . import responses, data_file


def clientlogin(token):
    """
    Authorization: header to pass to self.client.{get,post}() calls::

        self.client.post(url, data, **clientlogin(token))
    """
    return {'HTTP_AUTHORIZATION': 'GoogleLogin auth={0}'.format(token)}


class ApiClient(Client):
    def request(self, **request):
        response = super(ApiClient, self).request(**request)
        if response['Content-Type'] == 'application/json':
            response.json = json.loads(response.content.decode('utf-8'))
        return response


class ApiTest(TestCase):
    client_class = ApiClient

    def setUp(self):  # noqa
        super(ApiTest, self).setUp()
        cache.clear()

    def auth_token(self, user):
        url = reverse('reader:login')
        response = self.client.post(url, {'Email': user.email,
                                          'Passwd': 'test'})
        for line in response.content.decode('utf-8').splitlines():
            key, value = line.split('=', 1)
            if key == 'Auth':
                return value

    def post_token(self, auth_token):
        url = reverse('reader:token')
        response = self.client.get(url, **clientlogin(auth_token))
        self.assertEqual(response.status_code, 200)
        return response.content.decode('utf-8')


class AuthTest(ApiTest):
    def test_client_login_anon(self):
        url = reverse('reader:login')
        for response in (self.client.get(url), self.client.post(url)):
            self.assertContains(response, "Error=BadAuthentication",
                                status_code=403)

    def test_bad_auth_header(self):
        url = reverse('reader:tag_list')
        response = self.client.get(url, HTTP_AUTHORIZATION="GoogleLogin")
        self.assertEqual(response.status_code, 403)
        response = self.client.get(
            url, HTTP_AUTHORIZATION="GoogleLogin token=whatever")
        self.assertEqual(response.status_code, 403)

    def tests_client_login(self):
        url = reverse('reader:login')
        params = {
            'Email': 'test@example.com',
            'Passwd': 'brah',
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 403)

        user = UserFactory.create()
        params['Email'] = user.email
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 403)

        params['Passwd'] = 'test'
        params['client'] = 'Test Client'
        response = self.client.get(url, params,
                                   HTTP_USER_AGENT='testclient/1.0')
        self.assertContains(response, 'Auth=')

        token = user.auth_tokens.get()
        self.assertEqual(token.client, 'Test Client')
        self.assertEqual(token.user_agent, 'testclient/1.0')

        response = self.client.post(url, params)
        self.assertContains(response, 'Auth=')

        # Usernames are also accepted
        params['Email'] = user.username
        response = self.client.post(url, params)
        self.assertContains(response, 'Auth=')

        # Case-insensitivity
        params['Email'] = user.username.upper()
        response = self.client.post(url, params)
        self.assertContains(response, 'Auth=')

        for line in response.content.decode('utf-8').splitlines():
            key, value = line.split('=', 1)
            self.assertEqual(len(value), 267)

    def test_post_token(self):
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:token')
        self.assertEqual(self.client.get(url).status_code, 403)

        response = self.client.get(url, **clientlogin("bad token"))
        self.assertEqual(response.status_code, 403)

        # First fetch puts the user in the cache
        with self.assertNumQueries(1):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.content), 57)

        # Subsequent fetches use the cached user
        with self.assertNumQueries(0):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.content), 57)

        cache.delete('reader_auth_token:{0}'.format(token))
        with self.assertNumQueries(1):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.status_code, 200)

        user.auth_tokens.get().delete()  # deletes from cache as well
        with self.assertNumQueries(1):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.status_code, 403)

    def test_delete_expired_tokens(self):
        user = UserFactory.create()
        token1 = self.auth_token(user)
        token2 = self.auth_token(user)
        self.assertEqual(AuthToken.objects.count(), 2)
        AuthToken.objects.filter(token=token1).update(
            date_created=timezone.now() - timedelta(days=8))
        call_command('delete_expired_tokens')
        self.assertEqual(AuthToken.objects.get().token, token2)


class SerializerTest(ApiTest):
    def test_serializer(self):
        serializer = GoogleReaderXMLRenderer()
        self.assertEqual(serializer.render(None), '')

        serializer.render({'wat': {'of': 'dict'}})
        serializer.render({'stuff': ({'foo': 'bar'}, {'baz': 'blah'})})
        serializer.render({})
        serializer.render({'list': ('of', 'strings')})
        with self.assertRaises(AssertionError):
            serializer.render(12.5)


@patch('requests.get')
class ReaderApiTest(ApiTest):
    def test_user_info(self, get):
        url = reverse('reader:user_info')

        # Test bad authentication once and for all GET requests
        response = self.client.get(url)
        self.assertContains(response, "Error=BadAuthentication",
                            status_code=403)

        user = UserFactory.create()
        token = self.auth_token(user)
        response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.json, {
            u"userName": user.username,
            u"userEmail": user.email,
            u"userId": str(user.pk),
            u"userProfileId": str(user.pk),
            u"isBloggerUser": False,
            u"signupTimeSec": int(user.date_joined.strftime("%s")),
            u"isMultiLoginEnabled": False,
        })

    def test_content_negociation(self, get):
        url = reverse('reader:user_info')
        user = UserFactory.create()
        token = self.auth_token(user)
        response = self.client.get(url, {'output': 'json'},
                                   **clientlogin(token))
        self.assertEqual(response['Content-Type'],
                         'application/json')

        response = self.client.get(url, {'output': 'xml'},
                                   **clientlogin(token))
        self.assertEqual(response['Content-Type'],
                         'application/xml; charset=utf-8')

    def test_subscriptions_list(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)

        url = reverse("reader:subscription_list")
        response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.json, {"subscriptions": []})

        feed = FeedFactory.create(category__user=user, user=user)
        EntryFactory.create(feed=feed, user=user,
                            date=timezone.now() - timedelta(days=365 * 150))
        with self.assertNumQueries(2):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(len(response.json['subscriptions']), 1)
        self.assertEqual(response.json['subscriptions'][0]['categories'][0], {
            "id": u"user/{0}/label/{1}".format(user.pk, feed.category.name),
            "label": feed.category.name,
        })

        FeedFactory.create(category__user=user, user=user)
        FeedFactory.create(category=feed.category, user=user)
        FeedFactory.create(category=None, user=user)
        with self.assertNumQueries(2):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(len(response.json['subscriptions']), 4)

    def test_subscribed(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:subscribed')

        response = self.client.get(url, **clientlogin(token))
        self.assertContains(response, "Missing 's' parameter", status_code=400)

        response = self.client.get(url, {'s': 'foo/bar'}, **clientlogin(token))
        self.assertContains(response, "Unrecognized feed format",
                            status_code=400)

        feed_url = 'http://example.com/subscribed-feed'
        response = self.client.get(url, {'s': 'feed/{0}'.format(feed_url)},
                                   **clientlogin(token))
        self.assertContains(response, 'false')

        FeedFactory.create(url=feed_url, category__user=user, user=user)
        response = self.client.get(url, {'s': 'feed/{0}'.format(feed_url)},
                                   **clientlogin(token))
        self.assertContains(response, 'true')

        # Bogus URL with one slash
        feed_url = 'http:/example.com/subscribed-feed'
        response = self.client.get(url, {'s': 'feed/{0}'.format(feed_url)},
                                   **clientlogin(token))
        self.assertContains(response, 'true')

    def test_edit_tag(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:edit_tag')
        response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.status_code, 405)

        response = self.client.post(url, **clientlogin(token))
        self.assertContains(response, "Missing 'T' POST token",
                            status_code=400)

        response = self.client.post(url, {'T': 'no'}, **clientlogin(token))
        self.assertContains(response, "Invalid POST token",
                            status_code=401)
        self.assertEqual(response['X-Reader-Google-Bad-Token'], 'true')

        token_url = reverse('reader:token')
        post_token = self.client.post(
            token_url, **clientlogin(token)).content.decode('utf-8')

        data = {
            'T': post_token,
        }
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Missing 'i' in request data",
                            status_code=400)

        data['i'] = 'tag:google.com,2005:reader/item/foobar'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Unrecognized item",
                            status_code=400)

        data['i'] = 'brah'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Unrecognized item",
                            status_code=400)

        entry = EntryFactory.create(user=user, feed__category__user=user)
        data['i'] = 'tag:google.com,2005:reader/item/{0}'.format(entry.hex_pk)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Specify a tag to add or remove",
                            status_code=400)

        data['r'] = 'unknown'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Bad tag format", status_code=400)

        # a and r at the same time
        data['a'] = 'user/-/state/com.google/starred'
        data['r'] = 'user/{0}/state/com.google/kept-unread'.format(user.pk)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK", status_code=200)
        e = user.entries.get()
        self.assertTrue(e.starred)
        self.assertTrue(e.read)

        del data['a']

        # Mark as read: remove "kept-unread" or add "read"
        self.assertFalse(entry.read)
        data['r'] = 'user/-/state/com.google/kept-unread'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        entry = Entry.objects.get()
        self.assertTrue(entry.read)

        entry.read = False
        entry.save(update_fields=['read'])
        del data['r']
        data['a'] = 'user/-/state/com.google/read'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        entry = Entry.objects.get()
        self.assertTrue(entry.read)

        # Mark as unread: add "kept-unread" or remove "read"
        data['a'] = 'user/-/state/com.google/kept-unread'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        entry = Entry.objects.get()
        self.assertFalse(entry.read)

        entry.read = True
        entry.save(update_fields=['read'])
        del data['a']
        data['r'] = 'user/-/state/com.google/read'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        entry = Entry.objects.get()
        self.assertFalse(entry.read)

        # Star / unstar, broadcast / unbroadcast
        for tag in ['starred', 'broadcast']:
            del data['r']
            data['a'] = 'user/-/state/com.google/{0}'.format(tag)
            response = self.client.post(url, data, **clientlogin(token))
            self.assertContains(response, "OK")
            entry = Entry.objects.get()
            self.assertTrue(getattr(entry, tag))

            data['r'] = data['a']
            del data['a']
            response = self.client.post(url, data, **clientlogin(token))
            self.assertContains(response, "OK")
            entry = Entry.objects.get()
            self.assertFalse(getattr(entry, tag))

        data['r'] = 'user/-/state/com.google/tracking-foo-bar'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        data['a'] = data['r']
        del data['r']
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")

        # Batch edition
        entry2 = EntryFactory.create(user=user, feed=entry.feed)
        self.assertEqual(user.entries.filter(broadcast=True).count(), 0)
        response = self.client.post(url, {
            'i': [entry.pk, entry2.pk],
            'a': 'user/-/state/com.google/broadcast',
            'T': post_token,
        }, **clientlogin(token))
        self.assertEqual(user.entries.filter(broadcast=True).count(), 2)

    def test_hex_item_ids(self, get):
        entry = Entry(pk=162170919393841362)
        self.assertEqual(entry.hex_pk, "024025978b5e50d2")
        entry.pk = -355401917359550817
        self.assertEqual(entry.hex_pk, "fb115bd6d34a8e9f")

        self.assertEqual(
            item_id("tag:google.com,2005:reader/item/fb115bd6d34a8e9f"),
            -355401917359550817
        )
        self.assertEqual(
            item_id("tag:google.com,2005:reader/item/024025978b5e50d2"),
            162170919393841362
        )

    def test_tag_list(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:tag_list')

        response = self.client.get(url, **clientlogin(token))
        self.assertEqual(len(response.json['tags']), 2)

        CategoryFactory.create(user=user)
        with self.assertNumQueries(1):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(len(response.json['tags']), 3)

    def test_unread_count(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:unread_count')

        response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.json, {'max': 1000, 'unreadcounts': []})

        feed = FeedFactory.create(category__user=user, user=user)
        for i in range(5):
            EntryFactory.create(feed=feed, read=False, user=user)
        feed2 = FeedFactory.create(category=None, user=user)
        EntryFactory.create(feed=feed2, read=False, user=user)
        feed.update_unread_count()
        feed2.update_unread_count()

        # need to populate last updates, extra queries required
        with self.assertNumQueries(5):
            response = self.client.get(url, **clientlogin(token))

        with self.assertNumQueries(2):
            response = self.client.get(url, **clientlogin(token))

        # 3 elements: reading-list, label and feed
        self.assertEqual(len(response.json['unreadcounts']), 4)

        for count in response.json['unreadcounts']:
            if count['id'].endswith(feed2.url):
                self.assertEqual(count['count'], 1)
            elif count['id'].endswith(feed.category.name):
                self.assertEqual(count['count'], 5)
            elif count['id'].endswith('reading-list'):
                self.assertEqual(count['count'], 6)
            else:
                self.assertEqual(count['count'], 5)

    def test_stream_content(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:stream_contents',
                      args=['user/-/state/com.google/reading-list'])

        # 2 are warmup queries, cached in following calls
        with self.assertNumQueries(4):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.json['author'], user.username)
        self.assertEqual(len(response.json['items']), 0)
        self.assertFalse('continuation' in response.json)

        # GET parameters validation
        response = self.client.get(url, {'ot': 'foo'}, **clientlogin(token))
        self.assertEqual(response.status_code, 400)
        response = self.client.get(url, {'ot': '13'}, **clientlogin(token))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url, {'nt': 'foo'}, **clientlogin(token))
        self.assertEqual(response.status_code, 400)
        response = self.client.get(url, {'nt': '13'}, **clientlogin(token))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {'r': 12, 'output': 'json'},
                                   **clientlogin(token))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url, {'r': 'o'}, **clientlogin(token))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {'n': 'foo'}, **clientlogin(token))
        self.assertEqual(response.status_code, 400)

        response = self.client.get(url, {'c': 'pageone'}, **clientlogin(token))
        response = self.client.get(url, {'c': 'a'}, **clientlogin(token))

        feed = FeedFactory.create(category__user=user, user=user)
        FeedFactory.create(category=feed.category, user=user, url=feed.url)

        Entry.objects.bulk_create([
            EntryFactory.build(user=user, feed=feed, read=False)
            for i in range(15)
        ] + [
            EntryFactory.build(user=user, feed=feed, read=True)
            for i in range(4)
        ] + [
            EntryFactory.build(user=user, feed=feed, read=False, starred=True)
            for i in range(10)
        ] + [
            EntryFactory.build(user=user, feed=feed, read=True, broadcast=True)
        ])

        # Warm up the uniques map cache
        with self.assertNumQueries(3):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.json['continuation'], 'page2')
        self.assertEqual(len(response.json['items']), 20)

        # ?xt= excludes stuff
        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'xt': 'user/-/state/com.google/starred', 'n': 40},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 20)

        # Multiple ?xt= is valid.
        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'xt': [
                    'user/-/state/com.google/starred',
                    'user/-/state/com.google/broadcast-friends',
                    'user/-/state/com.google/lol',
                ], 'n': 40},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 19)

        # ?it= includes stuff
        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'it': 'user/-/state/com.google/starred', 'n': 40},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 10)

        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'xt': 'user/-/state/com.google/broadcast', 'n': 40},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 29)

        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'xt': 'user/-/state/com.google/kept-unread', 'n': 40},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 5)

        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'xt': 'user/-/state/com.google/read', 'n': 40},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 25)

        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'xt': u'feed/{0}'.format(feed.url)},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 0)

        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'xt': u'user/-/label/{0}'.format(feed.category.name)},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 0)

        with self.assertNumQueries(2):
            response = self.client.get(url, {'c': 'page2'},
                                       **clientlogin(token))
        self.assertEqual(len(response.json['items']), 10)
        self.assertFalse('continuation' in response.json)
        self.assertTrue(response.json['self'][0]['href'].endswith(
            'reading-list?c=page2'))

        with self.assertNumQueries(2):
            response = self.client.get(url, {'n': 40}, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 30)
        self.assertFalse('continuation' in response.json)

        with self.assertNumQueries(2):
            response = self.client.get(url, {
                'n': 100,
                'ot': int(time.time()) - 3600 * 24 * 2},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 30)

        with self.assertNumQueries(2):
            response = self.client.get(url, {
                'n': 10,
                'ot': int(time.time()) - 3600 * 24 * 2},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 10)

        with self.assertNumQueries(2):
            response = self.client.get(url, {
                'n': 100,
                'ot': int(time.time()) + 1},
                **clientlogin(token))
        self.assertEqual(len(response.json['items']), 0)

        url = reverse('reader:stream_contents',
                      args=['user/-/state/com.google/starred'])
        with self.assertNumQueries(2):
            response = self.client.get(url, {'n': 40}, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 10)

        url = reverse('reader:stream_contents',
                      args=['user/-/state/com.google/broadcast-friends'])
        with self.assertNumQueries(2):
            response = self.client.get(url, {'n': 40, 'output': 'atom'},
                                       **clientlogin(token))
        self.assertEqual(response.status_code, 200)

        url = reverse('reader:stream_contents',
                      args=[u'user/-/label/{0}'.format(feed.category.name)])
        with self.assertNumQueries(2):
            response = self.client.get(url, {'n': 40}, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 30)

        url = reverse('reader:stream_contents',
                      args=[u'feed/{0}'.format(feed.url)])
        with self.assertNumQueries(4):
            response = self.client.get(url, {'n': 40}, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 30)

        url = reverse('reader:stream_contents',
                      args=['user/-/state/com.google/broadcast'])
        with self.assertNumQueries(2):
            response = self.client.get(url, {'n': 40}, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 1)

        url = reverse('reader:stream_contents',
                      args=['user/-/state/com.google/broadcast'])
        with self.assertNumQueries(2):
            response = self.client.get(url, {'ot': 12}, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 1)

        url = reverse('reader:stream_contents',
                      args=['user/-/state/com.google/kept-unread'])
        with self.assertNumQueries(2):
            response = self.client.get(url, {'n': 40}, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 25)

        url = reverse('reader:stream_contents')  # defaults to reading-list
        with self.assertNumQueries(2):
            response = self.client.get(url, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 20)

        url = reverse('reader:stream_contents', args=['unknown'])
        response = self.client.get(url, **clientlogin(token))
        self.assertContains(response, "Unknown stream", status_code=400)

        response = self.client.get(
            reverse('reader:stream_contents',
                    args=['feed/http://inexisting.com/feed']),
            **clientlogin(token))
        self.assertEqual(response.status_code, 404)

        url = reverse('reader:stream_contents',
                      args=['user/-/state/com.google/like'])
        with self.assertNumQueries(2):
            response = self.client.get(url, {'n': 40}, **clientlogin(token))
        self.assertEqual(len(response.json['items']), 0)

        UniqueFeed.objects.all().delete()
        feed_url = user.feeds.all()[0].url
        url = reverse('reader:stream_contents',
                      args=[u'feed/{0}'.format(feed_url)])
        with self.assertNumQueries(4):
            response = self.client.get(url, {'n': 40, 'output': 'atom'},
                                       **clientlogin(token))
            self.assertEqual(response.status_code, 200)

        feed_url = feed_url.replace('://', ':/')
        url = reverse('reader:stream_contents',
                      args=[u'feed/{0}'.format(feed_url)])
        with self.assertNumQueries(4):
            response = self.client.get(url, {'n': 40, 'output': 'atom'},
                                       **clientlogin(token))
            self.assertEqual(response.status_code, 200)

    def test_stream_atom(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:atom_contents',
                      args=['user/-/state/com.google/reading-list'])

        # 2 are warmup queries, cached in following calls
        with self.assertNumQueries(4):
            response = self.client.get(url, **clientlogin(token))
        self.assertTrue(response['Content-Type'].startswith("text/xml"))

        response = self.client.get(url, {'output': 'json'},
                                   **clientlogin(token))
        self.assertTrue(response['Content-Type'].startswith("text/xml"))

    def test_stream_items_ids(self, get):
        get.return_value = responses(304)
        url = reverse("reader:stream_items_ids")
        user = UserFactory.create()
        token = self.auth_token(user)
        feed = FeedFactory.create(category__user=user, user=user)
        for i in range(5):
            EntryFactory.create(feed=feed, user=user, broadcast=True)
        for i in range(5):
            EntryFactory.create(feed=feed, user=user, starred=True, read=True)

        response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.status_code, 400)

        response = self.client.get(url, {'n': 'a'}, **clientlogin(token))
        self.assertEqual(response.status_code, 400)

        response = self.client.get(url, {'n': 10, 's': 'foo'},
                                   **clientlogin(token))
        self.assertEqual(response.status_code, 400)

        with self.assertNumQueries(2):
            response = self.client.post('{0}?{1}'.format(url, urlencode({
                'n': 5, 's': 'user/-/state/com.google/reading-list',
                'includeAllDirectStreamIds': 'true'})),
                **clientlogin(token))
        self.assertEqual(len(response.json['itemRefs']), 5)
        self.assertEqual(response.json['continuation'], 'page2')

        with self.assertNumQueries(2):
            response = self.client.post('{0}?{1}'.format(url, urlencode({
                'n': 5, 's': 'user/{0}/state/com.google/reading-list'.format(
                    user.pk),
                'includeAllDirectStreamIds': 'true'})),
                **clientlogin(token))
        self.assertEqual(len(response.json['itemRefs']), 5)
        self.assertEqual(response.json['continuation'], 'page2')

        with self.assertNumQueries(2):
            response = self.client.get(url, {
                'n': 5, 's': 'splice/user/-/state/com.google/reading-list',
                'includeAllDirectStreamIds': 'true'},
                **clientlogin(token))
        self.assertEqual(len(response.json['itemRefs']), 5)
        self.assertEqual(response.json['continuation'], 'page2')

        with self.assertNumQueries(2):
            response = self.client.get(url, {
                'n': 5,
                's': 'splice/user/{0}/state/com.google/reading-list'.format(
                    user.pk),
                'includeAllDirectStreamIds': 'true'},
                **clientlogin(token))
        self.assertEqual(len(response.json['itemRefs']), 5)
        self.assertEqual(response.json['continuation'], 'page2')

        with self.assertNumQueries(2):
            response = self.client.get(url, {
                'n': 5, 's': 'splice/user/-/state/com.google/reading-list',
                'c': 'page2', 'includeAllDirectStreamIds': 'true'},
                **clientlogin(token))
        self.assertEqual(len(response.json['itemRefs']), 5)
        self.assertFalse('continuation' in response.json)

        with self.assertNumQueries(2):
            response = self.client.get(url, {
                'n': 50, 's': (
                    'splice/user/-/state/com.google/broadcast|'
                    'user/{0}/state/com.google/read').format(user.pk),
                'includeAllDirectStreamIds': 'no'},
                **clientlogin(token))
        self.assertEqual(len(response.json['itemRefs']), 10)

    def test_stream_items_count(self, get):
        get.return_value = responses(304)
        url = reverse("reader:stream_items_count")
        user = UserFactory.create()
        token = self.auth_token(user)

        response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.status_code, 400)

        response = self.client.get(
            url, {'s': 'user/-/state/com.google/reading-list'},
            **clientlogin(token))
        self.assertEqual(response.content, b'0')

        response = self.client.get(
            url, {'s': 'user/{0}/state/com.google/reading-list'.format(
                user.pk)},
            **clientlogin(token))
        self.assertEqual(response.content, b'0')

        feed = FeedFactory.create(category__user=user, user=user)
        for i in range(6):
            EntryFactory.create(feed=feed, user=user, read=True)
        for i in range(4):
            EntryFactory.create(feed=feed, user=user)

        response = self.client.get(
            url, {'s': 'user/-/state/com.google/kept-unread'},
            **clientlogin(token))
        self.assertEqual(response.content, b'4')

        response = self.client.get(
            url, {'s': 'user/-/state/com.google/read'},
            **clientlogin(token))
        self.assertEqual(response.content, b'6')

        response = self.client.get(
            url, {'s': 'user/{0}/state/com.google/read'.format(user.pk)},
            **clientlogin(token))
        self.assertEqual(response.content, b'6')

        response = self.client.get(
            url, {'s': 'user/-/state/com.google/kept-unread', 'a': 'true'},
            **clientlogin(token))
        self.assertTrue(response.content.startswith(b'4#'))

    def test_stream_items_contents(self, get):
        get.return_value = responses(304)
        url = reverse('reader:stream_items_contents')
        user = UserFactory.create()
        token = self.auth_token(user)

        response = self.client.get(url, **clientlogin(token))
        self.assertContains(response, "Required 'i' parameter",
                            status_code=400)

        response = self.client.get(url, {'i': 12}, **clientlogin(token))
        self.assertContains(response, "No items found", status_code=400)

        response = self.client.get(url, {'i': 12, 'output': 'atom'},
                                   **clientlogin(token))
        self.assertContains(response, "No items found", status_code=400)

        feed1 = FeedFactory.create(category__user=user, user=user)
        feed2 = FeedFactory.create(category__user=user, user=user)
        entry1 = EntryFactory.create(user=user, feed=feed1)
        entry2 = EntryFactory.create(user=user, feed=feed2)

        with self.assertNumQueries(2):
            response = self.client.get(url, {'i': [entry1.pk, entry2.pk]},
                                       **clientlogin(token))
            self.assertEqual(len(response.json['items']), 2)

        with self.assertNumQueries(1):
            response = self.client.get(url, {'i': [
                'tag:google.com,2005:reader/item/{0}'.format(entry1.hex_pk),
                entry2.pk]}, **clientlogin(token))
            self.assertEqual(len(response.json['items']), 2)

        with self.assertNumQueries(1):
            response = self.client.get(url, {'i': [
                'tag:google.com,2005:reader/item/{0}'.format(entry1.hex_pk),
                'tag:google.com,2005:reader/item/{0}'.format(entry2.hex_pk),
            ]}, **clientlogin(token))
            self.assertEqual(len(response.json['items']), 2)

        with self.assertNumQueries(1):
            response = self.client.get(url, {'i': [entry1.pk, entry2.pk],
                                             'output': 'atom'},
                                       **clientlogin(token))
            self.assertEqual(response.status_code, 200)

        with self.assertNumQueries(1):
            ids = ["tag:google.com,2005:reader/item/{0}".format(pk)
                   for pk in [entry1.hex_pk, entry2.hex_pk]]
            response = self.client.get(url, {'i': ids, 'output': 'atom'},
                                       **clientlogin(token))
            self.assertEqual(response.status_code, 200)

        feed3 = FeedFactory.create(category__user=user, user=user)
        entry3 = EntryFactory.create(user=user, feed=feed3)
        with self.assertNumQueries(2):
            response = self.client.get(
                url, {'i': [entry1.pk, entry2.pk, entry3.pk],
                      'output': 'atom-hifi'}, **clientlogin(token))
            self.assertEqual(response.status_code, 200)

        with self.assertNumQueries(1):
            response = self.client.post(
                url, {'i': [entry1.pk, entry2.pk, entry3.pk],
                      'output': 'atom-hifi'}, **clientlogin(token))
            self.assertEqual(response.status_code, 200)

    def test_mark_all_as_read(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:mark_all_as_read')

        token_url = reverse('reader:token')
        post_token = self.client.post(
            token_url, **clientlogin(token)).content.decode('utf-8')

        feed = FeedFactory.create(category__user=user, user=user)
        for i in range(4):
            EntryFactory.create(feed=feed, user=user)
        EntryFactory.create(feed=feed, user=user, starred=True)
        EntryFactory.create(feed=feed, user=user, broadcast=True)

        feed2 = FeedFactory.create(category__user=user, user=user)
        entry = EntryFactory.create(feed=feed2, user=user)
        EntryFactory.create(feed=feed2, user=user, starred=True)
        EntryFactory.create(feed=feed2, user=user, starred=True)
        EntryFactory.create(feed=feed2, user=user, broadcast=True)

        data = {'T': post_token}
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Missing 's' parameter", status_code=400)

        response = self.client.post(url + '?T={0}'.format(post_token), {},
                                    **clientlogin(token))
        self.assertContains(response, "Missing 's' parameter", status_code=400)

        data['s'] = u'feed/{0}'.format(feed2.url)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, 'OK')
        self.assertEqual(Entry.objects.filter(read=True).count(), 4)
        self.assertEqual(Feed.objects.get(pk=feed2.pk).unread_count, 0)

        for f in Feed.objects.all():
            self.assertEqual(f.entries.filter(read=False).count(),
                             f.unread_count)

        entry.read = False
        entry.save(update_fields=['read'])
        feed2.update_unread_count()
        self.assertEqual(Feed.objects.get(pk=feed2.pk).unread_count, 1)

        data['s'] = u'user/-/label/{0}'.format(feed2.category.name)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, 'OK')
        self.assertEqual(Entry.objects.filter(read=True).count(), 4)
        self.assertEqual(Feed.objects.get(pk=feed2.pk).unread_count, 0)

        for f in Feed.objects.all():
            self.assertEqual(f.entries.filter(read=False).count(),
                             f.unread_count)

        data['s'] = u'user/{0}/label/{1}'.format(user.pk, feed2.category.name)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, 'OK')
        self.assertEqual(Entry.objects.filter(read=True).count(), 4)
        self.assertEqual(Feed.objects.get(pk=feed2.pk).unread_count, 0)

        for f in Feed.objects.all():
            self.assertEqual(f.entries.filter(read=False).count(),
                             f.unread_count)

        data['s'] = 'user/-/state/com.google/starred'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, 'OK')
        self.assertEqual(Entry.objects.filter(read=True).count(), 5)
        self.assertEqual(Feed.objects.get(pk=feed.pk).unread_count, 5)
        self.assertEqual(Entry.objects.filter(starred=True,
                                              read=False).count(), 0)

        for feed in Feed.objects.all():
            self.assertEqual(feed.entries.filter(read=False).count(),
                             feed.unread_count)

        data['s'] = 'user/-/state/com.google/reading-list'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, 'OK')
        self.assertEqual(Entry.objects.filter(read=False).count(), 0)
        for feed in Feed.objects.all():
            self.assertEqual(feed.unread_count, 0)
            self.assertEqual(feed.entries.filter(read=False).count(), 0)

        data['s'] = 'user/-/state/com.google/read'  # yo dawg
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, 'OK')
        self.assertEqual(Entry.objects.filter(read=False).count(), 0)

        data['s'] = 'user/{0}/state/com.google/read'.format(user.pk)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, 'OK')
        self.assertEqual(Entry.objects.filter(read=False).count(), 0)

        Entry.objects.update(read=False)
        for feed in Feed.objects.all():
            feed.update_unread_count()

        data['ts'] = int(time.mktime(
            list(Entry.objects.all()[:5])[-1].date.timetuple()
        )) * 1000000
        data['s'] = 'user/-/state/com.google/reading-list'
        with self.assertNumQueries(2):
            self.client.post(url, data, **clientlogin(token))
        self.assertEqual(Entry.objects.filter(read=False).count(), 5)
        for feed in Feed.objects.all():
            self.assertEqual(feed.entries.filter(read=False).count(),
                             feed.unread_count)

        data['ts'] = 'foo'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Invalid 'ts' parameter",
                            status_code=400)

    def test_stream_prefs(self, get):
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:stream_preference')
        response = self.client.get(url, **clientlogin(token))
        self.assertContains(response, "streamprefs")

    def test_preference_list(self, get):
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:preference_list')
        response = self.client.get(url, **clientlogin(token))
        self.assertContains(response, "prefs")

    def test_edit_subscription(self, get):
        get.return_value = responses(304)

        user = UserFactory.create()
        token = self.auth_token(user)
        post_token = self.post_token(token)
        category = CategoryFactory.create(user=user)
        feed = FeedFactory.build(category=category, user=user)

        url = reverse('reader:subscription_edit')
        data = {'T': post_token}
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Missing 'ac' parameter",
                            status_code=400)

        data['ac'] = 'subscribe'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Missing 's' parameter", status_code=400)

        data['s'] = u'{0}'.format(feed.url)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Unrecognized stream", status_code=400)

        data['s'] = u'feed/{0}'.format(feed.url)

        data['a'] = 'user/-/label/foo'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "HTTP 304", status_code=400)

        data['t'] = 'Testing stuff'
        data['a'] = 'userlabel/foo'
        get.return_value = responses(200, 'brutasse.atom')
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Unknown label", status_code=400)

        data['s'] = 'feed/foo bar'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Enter a valid URL", status_code=400)

        data['a'] = 'user/-/label/foo'
        data['s'] = u'feed/{0}'.format(feed.url)
        self.assertEqual(Feed.objects.count(), 0)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")

        self.assertEqual(Feed.objects.count(), 1)
        feed = Feed.objects.get()
        self.assertEqual(feed.name, 'Testing stuff')

        Feed.objects.get().delete()
        del data['t']  # extract title from feed now
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        self.assertEqual(Feed.objects.count(), 1)
        feed = Feed.objects.get()
        self.assertEqual(feed.name, "brutasse's Activity")

        # Allow adding to no category
        Feed.objects.get().delete()
        del data['a']
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        self.assertEqual(Feed.objects.count(), 1)
        feed = Feed.objects.get()
        self.assertIs(feed.category, None)

        # Re-submit: existing
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "already subscribed", status_code=400)

        # Editing that
        data = {'T': post_token,
                'ac': 'edit',
                's': u'feed/{0}'.format(feed.url),
                'a': 'user/{0}/label/known'.format(user.pk)}
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        cat = user.categories.get(name='known')
        self.assertEqual(cat.slug, 'known')
        self.assertEqual(Feed.objects.get().category_id, cat.pk)

        data = {'T': post_token,
                'ac': 'edit',
                's': u'feed/{0}'.format(feed.url),
                't': 'Hahaha'}
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        self.assertEqual(Feed.objects.get().name, "Hahaha")

        feed2 = FeedFactory.create(user=user, category=cat)
        # Moving to top folder
        data = {
            'T': post_token,
            'ac': 'edit',
            's': data['s'],
            't': 'Woo',
            'r': 'user/{0}/label/{1}'.format(user.pk, cat.name),
        }
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        feed = Feed.objects.get(pk=feed.pk)
        self.assertEqual(feed.name, "Woo")
        self.assertIsNone(feed.category)

        feed2 = Feed.objects.get(pk=feed2.pk)
        self.assertIsNotNone(feed2.category)
        feed2.delete()

        # Unsubscribing
        data = {
            'T': post_token,
            'ac': 'unsubscribe',
            's': u'feed/{0}'.format(feed.url),
        }
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        self.assertEqual(Feed.objects.count(), 0)

        data['ac'] = 'test'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Unrecognized action", status_code=400)

    def test_quickadd_subscription(self, get):
        get.return_value = responses(304)

        user = UserFactory.create()
        token = self.auth_token(user)
        post_token = self.post_token(token)
        url = reverse('reader:subscription_quickadd')
        data = {
            'T': post_token,
        }
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Missing 'quickadd' parameter",
                            status_code=400)

        data['quickadd'] = 'foo bar'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Enter a valid URL",
                            status_code=400)

        feed = FeedFactory.build()
        data['quickadd'] = feed.url
        get.return_value = responses(200, 'brutasse.atom')
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "streamId")

        data['quickadd'] = u'feed/{0}'.format(feed.url)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "already subscribed", status_code=400)

        feed = Feed.objects.get()
        self.assertEqual(feed.name, "brutasse's Activity")

    def test_disable_tag(self, get):
        get.return_value = responses(304)

        user = UserFactory.create()
        token = self.auth_token(user)
        post_token = self.post_token(token)

        url = reverse('reader:disable_tag')
        data = {'T': post_token}
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "required 's'", status_code=400)

        data['t'] = 'test'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "does not exist", status_code=400)

        CategoryFactory.create(user=user, name=u'test')
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        self.assertEqual(user.categories.count(), 0)

        cat = CategoryFactory.create(user=user, name=u'Other Cat')
        FeedFactory.create(user=user, category=cat)
        del data['t']
        data['s'] = 'user/{0}/label/Other Cat'.format(user.pk)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        self.assertEqual(user.categories.count(), 0)
        self.assertEqual(user.feeds.count(), 1)

    def test_rename_tag(self, get):
        user = UserFactory.create()
        token = self.auth_token(user)
        post_token = self.post_token(token)

        url = reverse('reader:rename_tag')

        data = {'T': post_token}
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Missing required 's'", status_code=400)

        data['t'] = 'test'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Missing required 'dest'",
                            status_code=400)

        data['dest'] = 'yolo'
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Invalid 'dest' parameter",
                            status_code=400)

        data['dest'] = 'user/{0}/label/yolo'.format(user.pk)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "Tag 'test' does not exist",
                            status_code=400)

        cat = CategoryFactory.create(user=user)
        data['t'] = cat.name
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        self.assertEqual(user.categories.get().name, 'yolo')

        data['s'] = 'user/{0}/label/yolo'.format(user.pk)
        del data['t']
        data['dest'] = 'user/{0}/label/Yo lo dawg'.format(user.pk)
        response = self.client.post(url, data, **clientlogin(token))
        self.assertContains(response, "OK")
        self.assertEqual(user.categories.get().name, 'Yo lo dawg')

    def test_friends_list(self, get):
        user = UserFactory.create()
        token = self.auth_token(user)

        url = reverse('reader:friend_list')
        response = self.client.get(url, **clientlogin(token))
        self.assertEqual(response.status_code, 200)

    def test_api_export(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:subscription_export')
        response = self.client.get(url, **clientlogin(token))
        self.assertContains(response, 'FeedHQ Feed List Export')
        self.assertTrue('attachment' in response['Content-Disposition'])

        for i in range(7):
            FeedFactory.create(user=user, category__user=user)
        for i in range(3):
            FeedFactory.create(user=user, category=None)
        response = self.client.get(url, **clientlogin(token))
        for feed in user.feeds.all():
            self.assertContains(response, u'title="{0}"'.format(feed.name))
            self.assertContains(response, u'xmlUrl="{0}"'.format(feed.url))
        for category in user.categories.all():
            self.assertContains(response, u'title="{0}"'.format(category.name))

    def test_api_import(self, get):
        get.return_value = responses(304)
        user = UserFactory.create()
        token = self.auth_token(user)
        url = reverse('reader:subscription_import')
        with open(data_file('sample.opml'), 'rb') as f:
            response = self.client.post(
                url, f.read(), content_type='application/xml',
                **clientlogin(token))
        self.assertContains(response, "OK: 2")

        response = self.client.post(
            url, b"foobar", content_type='application/xml',
            **clientlogin(token))
        self.assertContains(response, "doesn't seem to be a valid OPML file",
                            status_code=400)

        redis = get_redis_connection()
        redis.set('lock:opml_import:{0}'.format(user.pk), True)
        with open(data_file('sample.opml'), 'rb') as f:
            response = self.client.post(
                url, f.read(), content_type='application/xml',
                **clientlogin(token))
        self.assertContains(response, "concurrent OPML import",
                            status_code=400)

########NEW FILE########
__FILENAME__ = test_settings
import os

from django.test import TestCase

from feedhq.settings import parse_redis_url, parse_email_url


class SettingsTests(TestCase):
    def test_redis_url(self):
        os.environ['REDIS_URL'] = 'redis://:password@domain:12/44'
        self.assertEqual(parse_redis_url(), ({
            'host': 'domain',
            'port': 12,
            'password': 'password',
            'db': 44,
        }, False))

        os.environ['REDIS_URL'] = 'redis://domain:6379/44?eager=True'
        self.assertEqual(parse_redis_url(), ({
            'host': 'domain',
            'port': 6379,
            'password': None,
            'db': 44,
        }, True))

        os.environ['REDIS_URL'] = (
            'redis://domain:6379/44?eager=True&foo=bar&port=stuff'
        )
        self.assertEqual(parse_redis_url(), ({
            'host': 'domain',
            'port': 6379,
            'password': None,
            'db': 44,
        }, True))

        os.environ['REDIS_URL'] = (
            'redis://unix/some/path/44?eager=True'
        )
        self.assertEqual(parse_redis_url(), ({
            'unix_socket_path': '/some/path',
            'password': None,
            'db': 44,
        }, True))

        os.environ['REDIS_URL'] = (
            'redis://unix/some/other/path'
        )
        self.assertEqual(parse_redis_url(), ({
            'unix_socket_path': '/some/other/path',
            'password': None,
            'db': 0,
        }, False))

        os.environ['REDIS_URL'] = (
            'redis://:123456@unix/some/path/10'
        )
        self.assertEqual(parse_redis_url(), ({
            'unix_socket_path': '/some/path',
            'password': '123456',
            'db': 10,
        }, False))

    def test_email_url(self):
        os.environ['EMAIL_URL'] = (
            'smtp://bruno:test1234@example.com:587'
            '?use_tls=True&backend=custom.backend.EmailBackend'
        )
        self.assertEqual(parse_email_url(), {
            'BACKEND': 'custom.backend.EmailBackend',
            'HOST': 'example.com',
            'PORT': 587,
            'USE_TLS': True,
            'USER': 'bruno',
            'PASSWORD': 'test1234',
            'SUBJECT_PREFIX': '[FeedHQ] ',
        })

########NEW FILE########
__FILENAME__ = test_update_queue
import time

from datetime import timedelta
from mock import patch

import feedparser
import times

from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from django_push.subscriber.models import Subscription
from rache import pending_jobs, delete_job

from feedhq.feeds.models import UniqueFeed, timedelta_to_seconds
from feedhq.feeds.tasks import store_entries
from feedhq.feeds.utils import USER_AGENT
from feedhq.profiles.models import User
from feedhq.utils import get_redis_connection

from .factories import FeedFactory, UserFactory
from . import responses, ClearRedisTestCase, data_file, patch_job


class UpdateTests(ClearRedisTestCase):
    def test_update_feeds(self):
        u = UniqueFeed.objects.create(
            url='http://example.com/feed0',
        )
        u.schedule()
        patch_job(
            u.url,
            last_update=(timezone.now() - timedelta(hours=1)).strftime('%s')
        )
        u.schedule()
        UniqueFeed.objects.create(
            url='http://example.com/feed1',
        ).schedule()
        with self.assertNumQueries(0):
            jobs = list(pending_jobs(
                limit=5, reschedule_in=UniqueFeed.UPDATE_PERIOD * 60,
                connection=get_redis_connection()))
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]['id'], u.url)

        u.delete()
        delete_job(u.url, connection=get_redis_connection())
        with self.assertNumQueries(0):
            urls = list(pending_jobs(
                limit=5, reschedule_in=UniqueFeed.UPDATE_PERIOD * 60,
                connection=get_redis_connection()))
            self.assertEqual(len(urls), 0)

        u = UniqueFeed.objects.create(
            url='http://example.com/backoff',
        )
        u.schedule()
        patch_job(
            u.url, backoff_factor=10,
            last_update=(timezone.now() - timedelta(hours=28)).strftime('%s')
        )
        u.schedule()
        with self.assertNumQueries(0):
            jobs = list(pending_jobs(
                limit=5, reschedule_in=UniqueFeed.UPDATE_PERIOD * 60,
                connection=get_redis_connection()))
            self.assertEqual(len(jobs), 0)
        patch_job(u.url, backoff_factor=9)
        u.schedule()
        with self.assertNumQueries(0):
            jobs = list(pending_jobs(
                limit=5, reschedule_in=UniqueFeed.UPDATE_PERIOD * 60,
                connection=get_redis_connection()))
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]['id'], u.url)
            self.assertEqual(
                UniqueFeed.TIMEOUT_BASE * jobs[0]['backoff_factor'], 180)

        patch_job(u.url, last_update=int(time.time()))
        u.schedule()
        with self.assertNumQueries(0):
            jobs = list(pending_jobs(
                limit=5, reschedule_in=UniqueFeed.UPDATE_PERIOD * 60,
                connection=get_redis_connection()))
            self.assertEqual(len(jobs), 0)

        UniqueFeed.objects.create(
            url='http://example.com/lol',
        )

        for u in UniqueFeed.objects.all():
            patch_job(u.url, last_update=(
                timezone.now() - timedelta(hours=54)).strftime('%s'))

        # No subscribers -> deletion
        with self.assertNumQueries(2):
            call_command('delete_unsubscribed')
        self.assertEqual(UniqueFeed.objects.count(), 0)

        u = UniqueFeed.objects.create(
            url='http://example.com/foo',
        )
        u.schedule()
        patch_job(
            u.url,
            last_update=(timezone.now() - timedelta(hours=2)).strftime('%s'))
        u.schedule()
        u = UniqueFeed.objects.create(
            url='http://example.com/bar',
        )
        u.schedule()
        patch_job(
            u.url,
            last_update=(timezone.now() - timedelta(hours=2)).strftime('%s'))
        u.schedule()
        jobs = list(pending_jobs(
            limit=5, reschedule_in=UniqueFeed.UPDATE_PERIOD * 60,
            connection=get_redis_connection()))
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]['id'], 'http://example.com/bar')
        self.assertEqual(jobs[1]['id'], 'http://example.com/foo')

    @patch("requests.get")
    def test_update_call(self, get):
        u = User.objects.create_user('foo', 'foo@example.com', 'pass')
        c = u.categories.create(name='foo', slug='foo')
        get.return_value = responses(304)
        c.feeds.create(url='http://example.com/test', user=c.user)

        self.assertEqual(UniqueFeed.objects.count(), 1)
        get.assert_called_with(
            'http://example.com/test',
            headers={'Accept': feedparser.ACCEPT_HEADER,
                     'User-Agent': USER_AGENT % '1 subscriber'},
            timeout=10)

        call_command('delete_unsubscribed')
        self.assertEqual(UniqueFeed.objects.count(), 1)

    @patch("requests.get")
    def test_add_missing(self, get):
        get.return_value = responses(304)

        feed = FeedFactory.create()
        FeedFactory.create(url=feed.url)
        FeedFactory.create(url=feed.url)
        FeedFactory.create()

        UniqueFeed.objects.all().delete()
        with self.assertNumQueries(2):
            call_command('add_missing')

        with self.assertNumQueries(1):
            call_command('add_missing')

    @patch("requests.get")
    def test_updatefeeds_queuing(self, get):
        get.return_value = responses(304)

        for i in range(24):
            f = FeedFactory.create()
            patch_job(f.url, last_update=(
                timezone.now() - timedelta(hours=10)).strftime('%s'))
            UniqueFeed.objects.get(url=f.url).schedule()

        unique = UniqueFeed.objects.all()[0]
        with self.assertNumQueries(1):
            # Select
            call_command('updatefeeds', unique.pk)

        with self.assertNumQueries(1):
            # single select, already scheduled
            call_command('sync_scheduler')

        with self.assertNumQueries(1):
            # count()
            call_command('updatefeeds')

    @patch('requests.get')
    def test_suspending_user(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create(user__is_suspended=True)
        call_command('delete_unsubscribed')
        self.assertEqual(UniqueFeed.objects.count(), 0)

        parsed = feedparser.parse(data_file('sw-all.xml'))
        data = list(filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        ))

        with self.assertNumQueries(2):  # no insert
            store_entries(feed.url, data)

        last_updates = feed.user.last_updates()
        self.assertEqual(last_updates, {})

        feed2 = FeedFactory.create(url=feed.url, user__ttl=99999)
        self.assertEqual(UniqueFeed.objects.count(), 1)
        call_command('delete_unsubscribed')
        self.assertEqual(UniqueFeed.objects.count(), 1)

        data = list(filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        ))
        with self.assertNumQueries(5):  # insert
            store_entries(feed.url, data)

        self.assertEqual(feed.entries.count(), 0)
        self.assertEqual(feed2.entries.count(), 30)
        last_updates = feed2.user.last_updates()
        self.assertEqual(list(last_updates.keys()), [feed2.url])

    @patch('requests.get')
    def test_same_guids(self, get):
        get.return_value = responses(304)
        feed = FeedFactory.create(user__ttl=99999)

        parsed = feedparser.parse(data_file('aldaily-06-27.xml'))
        data = list(filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        ))

        with self.assertNumQueries(5):
            store_entries(feed.url, data)
        self.assertEqual(feed.entries.count(), 4)

        data = list(filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        ))
        with self.assertNumQueries(2):
            store_entries(feed.url, data)
        self.assertEqual(feed.entries.count(), 4)

        parsed = feedparser.parse(data_file('aldaily-06-30.xml'))
        data = list(filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        ))

        with self.assertNumQueries(5):
            store_entries(feed.url, data)
        self.assertEqual(feed.entries.count(), 10)

    @patch("requests.get")
    def test_empty_guid(self, get):
        get.return_value = responses(304)

        parsed = feedparser.parse(data_file('no-guid.xml'))
        data = list(filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        ))
        feed = FeedFactory.create(user__ttl=99999)
        with self.assertNumQueries(5):
            store_entries(feed.url, data)
        self.assertTrue(feed.entries.get().guid)

        feed.entries.all().delete()

        parsed = feedparser.parse(data_file('no-link-guid.xml'))
        data = list(filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        ))
        feed = FeedFactory.create(user__ttl=99999)
        with self.assertNumQueries(5):
            store_entries(feed.url, data)
        self.assertTrue(feed.entries.get().guid)

    @patch("requests.get")
    def test_ttl(self, get):
        get.return_value = responses(304)
        user = UserFactory.create(ttl=3)
        feed = FeedFactory.create(user=user, category__user=user)

        parsed = feedparser.parse(data_file('bruno.im.atom'))
        data = list(filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        ))
        with self.assertNumQueries(2):
            store_entries(feed.url, data)
        self.assertEqual(feed.entries.count(), 0)

    @patch("requests.get")
    def test_no_content(self, get):
        get.return_value = responses(304)
        parsed = feedparser.parse(data_file('no-content.xml'))
        data = filter(
            None,
            [UniqueFeed.objects.entry_data(
                entry, parsed) for entry in parsed.entries]
        )
        self.assertEqual(list(data), [])

    @patch("requests.get")
    def test_schedule_in(self, get):
        get.return_value = responses(304)

        f = FeedFactory.create()
        secs = timedelta_to_seconds(UniqueFeed.objects.get().schedule_in)
        self.assertTrue(3598 <= secs < 3600)

        patch_job(f.url, backoff_factor=2)
        secs = timedelta_to_seconds(UniqueFeed.objects.get().schedule_in)
        self.assertTrue(secs > 10000)

    def test_clean_rq(self):
        r = get_redis_connection()
        self.assertEqual(len(r.keys('rq:job:*')), 0)
        r.hmset('rq:job:abc', {'bar': 'baz'})
        r.hmset('rq:job:def', {'created_at': times.format(times.now(), 'UTC')})
        r.hmset('rq:job:123', {
            'created_at': times.format(
                times.now() - timedelta(days=10), 'UTC')})
        self.assertEqual(len(r.keys('rq:job:*')), 3)
        call_command('clean_rq')
        self.assertEqual(len(r.keys('rq:job:*')), 2)

    @patch('requests.post')
    @patch('requests.get')
    def test_ensure_subscribed(self, get, post):
        get.return_value = responses(200, 'hub.atom')
        post.return_value = responses(202)

        feed = FeedFactory.create()
        subscription = Subscription.objects.get()
        post.assert_called_with(
            u'http://pubsubhubbub.appspot.com/',
            data={
                u'hub.callback': u'http://localhost/subscriber/{0}/'.format(
                    subscription.pk),
                u'hub.verify': [u'sync', u'async'],
                u'hub.topic': feed.url,
                u'hub.mode': u'subscribe'},
            timeout=None,
            auth=None)
        self.assertEqual(feed.url, subscription.topic)

        post.reset_mock()
        self.assertFalse(post.called)
        subscription.lease_expiration = timezone.now()
        subscription.save()

        feed.delete()
        cache.delete(u'pshb:{0}'.format(feed.url))
        feed = FeedFactory.create(url=feed.url)
        post.assert_called_with(
            u'http://pubsubhubbub.appspot.com/',
            data={
                u'hub.callback': u'http://localhost/subscriber/{0}/'.format(
                    subscription.pk),
                u'hub.verify': [u'sync', u'async'],
                u'hub.topic': feed.url,
                u'hub.mode': u'subscribe'},
            timeout=None,
            auth=None)

        post.reset_mock()
        self.assertFalse(post.called)
        subscription.lease_expiration = timezone.now() + timedelta(days=5)
        subscription.save()
        feed.delete()
        cache.delete(u'pshb:{0}'.format(feed.url))
        feed = FeedFactory.create(url=feed.url)
        post.assert_called_with(
            u'http://pubsubhubbub.appspot.com/',
            data={
                u'hub.callback': u'http://localhost/subscriber/{0}/'.format(
                    subscription.pk),
                u'hub.verify': [u'sync', u'async'],
                u'hub.topic': feed.url,
                u'hub.mode': u'subscribe'},
            timeout=None,
            auth=None)

        post.reset_mock()
        self.assertFalse(post.called)
        subscription.verified = True
        subscription.save()
        feed.delete()
        cache.delete(u'pshb:{0}'.format(feed.url))
        feed = FeedFactory.create(url=feed.url)
        self.assertFalse(post.called)

########NEW FILE########
