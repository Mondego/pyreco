__FILENAME__ = admin
from datetime import timedelta
from django.contrib import admin
from tracking.models import Visitor, Pageview
from tracking.settings import TRACK_PAGEVIEWS

class VisitorAdmin(admin.ModelAdmin):
    date_hierarchy = 'start_time'

    list_display = ('session_key', 'user', 'start_time', 'session_over',
        'pretty_time_on_site', 'ip_address', 'user_agent')
    list_filter = ('user', 'ip_address')

    def session_over(self, obj):
        return obj.session_ended() or obj.session_expired()
    session_over.boolean = True

    def pretty_time_on_site(self, obj):
        if obj.time_on_site is not None:
            return timedelta(seconds=obj.time_on_site)
    pretty_time_on_site.short_description = 'Time on site'


admin.site.register(Visitor, VisitorAdmin)


class PageviewAdmin(admin.ModelAdmin):
    date_hierarchy = 'view_time'

    list_display = ('url', 'view_time')


if TRACK_PAGEVIEWS:
    admin.site.register(Pageview, PageviewAdmin)

########NEW FILE########
__FILENAME__ = cache
# Inspired by http://eflorenzano.com/blog/2008/11/28/drop-dead-simple-django-caching/
from django.db import models
from django.core.cache import cache
from django.db.models.query import QuerySet

def instance_cache_key(instance):
    opts = instance._meta
    return '%s.%s:%s' % (opts.app_label, opts.module_name, instance.pk)

class CacheQuerySet(QuerySet):
    def filter(self, *args, **kwargs):
        pk = None
        for val in ('pk', 'pk__exact', 'id', 'id__exact'):
            if val in kwargs:
                pk = kwargs[val]
                break
        if pk is not None:
            opts = self.model._meta
            key = '%s.%s:%s' % (opts.app_label, opts.module_name, pk)
            obj = cache.get(key)
            if obj is not None:
                self._result_cache = [obj]
        return super(CacheQuerySet, self).filter(*args, **kwargs)


class CacheManager(models.Manager):
    def get_query_set(self):
        return CacheQuerySet(self.model)


########NEW FILE########
__FILENAME__ = compat
# Django 1.5 support, falls back to auth.User to transparently
# work with <1.5
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User

########NEW FILE########
__FILENAME__ = handlers
from datetime import datetime
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from tracking.models import Visitor
from tracking.cache import instance_cache_key

SESSION_COOKIE_AGE = getattr(settings, 'SESSION_COOKIE_AGE')

def track_ended_session(sender, request, user, **kwargs):
    try:
        visitor = Visitor.objects.get(pk=request.session.session_key)
    # This should rarely ever occur.. e.g. direct request to logout
    except Visitor.DoesNotExist:
        return

    # Explicitly end this session. This improves the accuracy of the stats.
    visitor.end_time = timezone.now()
    visitor.time_on_site = (visitor.end_time - visitor.start_time).seconds
    visitor.save()

    # Unset the cache since the user logged out, this particular visitor will
    # unlikely be accessed individually.
    cache.delete(instance_cache_key(visitor))

def post_save_cache(sender, instance, **kwargs):
    cache.set(instance_cache_key(instance), instance, SESSION_COOKIE_AGE)

########NEW FILE########
__FILENAME__ = managers
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db import models
from django.db.models import Count, Avg, Min, Max
from tracking.settings import TRACK_PAGEVIEWS, TRACK_ANONYMOUS_USERS
from tracking.cache import CacheManager
from .compat import User

def adjusted_date_range(start=None, end=None):
    today = date.today()
    if end:
        end = min(end, today) + timedelta(days=1)
    else:
        end = today
    return start, end

class VisitorManager(CacheManager):
    def active(self, registered_only=True):
        "Returns all active users, e.g. not logged and non-expired session."
        visitors = self.get_query_set().filter(expiry_time__gt=timezone.now(), end_time=None)
        if registered_only:
            visitors = visitors.filter(user__isnull=False)
        return visitors

    def registered(self):
        return self.get_query_set().filter(user__isnull=False)

    def guests(self):
        return self.get_query_set().filter(user__isnull=True)

    def tracked_dates(self):
        "Returns a date range of when tracking has occured."
        dates = self.get_query_set().aggregate(start_min=Min('start_time'), start_max=Max('start_time'))
        if dates:
            return [dates['start_min'].date(), dates['start_max'].date()]
        return []

    def stats(self, start_date=None, end_date=None, registered_only=False):
        """Returns a dictionary of visits including:

            * total visits
            * unique visits
            * return ratio
            * pages per visit (if pageviews are enabled)
            * time on site

        for all users, registered users and guests.
        """
        start_date, end_date = adjusted_date_range(start_date, end_date)

        kwargs = {'start_time__lt': end_date}
        if start_date:
            kwargs['start_time__gte'] = start_date

        stats = {
            'total': 0,
            'unique': 0,
            'return_ratio': 0,
        }

        # All visitors
        visitors = self.get_query_set().filter(**kwargs)
        stats['total'] = total_count = visitors.count()
        unique_count = 0

        # No visitors! Nothing more to do.
        if not total_count:
            return stats

        # Avg time on site
        total_time_on_site = visitors.aggregate(avg_tos=Avg('time_on_site'))['avg_tos']
        stats['time_on_site'] = timedelta(seconds=int(total_time_on_site))

        # Registered user sessions
        registered_visitors = visitors.filter(user__isnull=False)
        registered_total_count = registered_visitors.count()

        if registered_total_count:
            registered_unique_count = registered_visitors.values('user').distinct().count()
            # Avg time on site
            registered_time_on_site = registered_visitors.aggregate(avg_tos=Avg('time_on_site'))['avg_tos']

            # Update the total unique count..
            unique_count += registered_unique_count

            # Set the registered stats..
            stats['registered'] = {
                'total': registered_total_count,
                'unique': registered_unique_count,
                'return_ratio': float(registered_total_count - registered_unique_count) / registered_total_count * 100,
                'time_on_site': timedelta(seconds=int(registered_time_on_site)),
            }

        # Get stats for our guests..
        if TRACK_ANONYMOUS_USERS and not registered_only:
            guest_visitors = visitors.filter(user__isnull=True)
            guest_total_count = guest_visitors.count()

            if guest_total_count:
                guest_unique_count = guest_visitors.values('ip_address').distinct().count()
                # Avg time on site
                guest_time_on_site = guest_visitors.aggregate(avg_tos=Avg('time_on_site'))['avg_tos']

                # Update the total unique count...
                unique_count += guest_unique_count

                stats['guests'] = {
                    'total': guest_total_count,
                    'unique': guest_unique_count,
                    'return_ratio': float(guest_total_count - guest_unique_count) / guest_total_count * 100,
                    'time_on_site': timedelta(seconds=int(guest_time_on_site)),
                }

        # Finish setting the total visitor counts
        stats['unique'] = unique_count
        stats['return_ratio'] = float(total_count - unique_count) / total_count * 100

        # If pageviews are being tracked, add the aggregated pages-per-visit stat
        if TRACK_PAGEVIEWS:
            if 'registered' in stats:
                stats['registered']['pages_per_visit'] = registered_visitors\
                    .annotate(page_count=Count('pageviews')).filter(page_count__gt=0)\
                    .aggregate(pages_per_visit=Avg('page_count'))['pages_per_visit']

            if TRACK_ANONYMOUS_USERS and not registered_only:
                stats['guests']['pages_per_visit'] = guest_visitors\
                    .annotate(page_count=Count('pageviews')).filter(page_count__gt=0)\
                    .aggregate(pages_per_visit=Avg('page_count'))['pages_per_visit']

                total_per_visit = visitors.annotate(page_count=Count('pageviews'))\
                    .filter(page_count__gt=0).aggregate(pages_per_visit=Avg('page_count'))['pages_per_visit']
            else:
                if 'registered' in stats:
                    total_per_visit = stats['registered']['pages_per_visit']
                else:
                    total_per_visit = 0

            stats['pages_per_visit'] = total_per_visit

        return stats

    def user_stats(self, start_date=None, end_date=None):
        start_date, end_date = adjusted_date_range(start_date, end_date)
        user_kwargs = {
            'visit_history__start_time__lt': end_date,
        }
        visit_kwargs = {
            'start_time__lt': end_date,
        }
        if start_date:
            user_kwargs['visit_history__start_time__gte'] = start_date
            visit_kwargs['start_time__gte'] = start_date
        else:
            user_kwargs['visit_history__start_time__isnull'] = False
            visit_kwargs['start_time__isnull'] = False

        users = list(User.objects.filter(**user_kwargs).annotate(
            visit_count=Count('visit_history'),
            time_on_site=Avg('visit_history__time_on_site'),
        ).filter(visit_count__gt=0).order_by('-time_on_site'))

        # Aggregate pageviews per visit
        for user in users:
            user.pages_per_visit = user.visit_history.filter(**visit_kwargs)\
                .annotate(page_count=Count('pageviews')).filter(page_count__gt=0)\
                .aggregate(pages_per_visit=Avg('page_count'))['pages_per_visit']
            # Lop off the floating point, turn into timedelta
            user.time_on_site = timedelta(seconds=int(user.time_on_site))
        return users


class PageviewManager(models.Manager):
    def stats(self, start_date=None, end_date=None, registered_only=False):
        """Returns a dictionary of pageviews including:

            * total pageviews

        for all users, registered users and guests.
        """
        start_date, end_date = adjusted_date_range(start_date, end_date)

        kwargs = {
            'visitor__start_time__lt': end_date,
        }
        if start_date:
            kwargs['visitor__start_time__gte'] = start_date

        stats = {
            'total': 0,
            'unique': 0,
        }

        pageviews = self.get_query_set().filter(**kwargs).select_related('visitor')
        stats['total'] = total_views = pageviews.count()
        unique_count = 0

        if not total_views:
            return stats

        # Registered user sessions
        registered_pageviews = pageviews.filter(visitor__user__isnull=False)
        registered_count = registered_pageviews.count()

        if registered_count:
            registered_unique_count = registered_pageviews.values('visitor', 'url').distinct().count()

            # Update the total unique count...
            unique_count += registered_unique_count

            stats['registered'] = {
                'total': registered_count,
                'unique': registered_unique_count,
            }

        if TRACK_ANONYMOUS_USERS and not registered_only:
            guest_pageviews = pageviews.filter(visitor__user__isnull=True)
            guest_count = guest_pageviews.count()

            if guest_count:
                guest_unique_count = guest_pageviews.values('visitor', 'url').distinct().count()

                # Update the total unique count...
                unique_count += guest_unique_count

                stats['guests'] = {
                    'total': guest_count,
                    'unique': guest_unique_count,
                }

        # Finish setting the total visitor counts
        stats['unique'] = unique_count

        return stats


########NEW FILE########
__FILENAME__ = middleware
import re
import logging
from datetime import datetime
from django.utils import timezone
from tracking.models import Visitor, Pageview
from tracking.utils import get_ip_address
from tracking.settings import (TRACK_AJAX_REQUESTS,
    TRACK_ANONYMOUS_USERS, TRACK_PAGEVIEWS, TRACK_IGNORE_URLS, TRACK_IGNORE_STATUS_CODES)

TRACK_IGNORE_URLS = map(lambda x: re.compile(x), TRACK_IGNORE_URLS)

log = logging.getLogger(__file__)

class VisitorTrackingMiddleware(object):
    def process_response(self, request, response):
        # Session framework not installed, nothing to see here..
        if not hasattr(request, 'session'):
            return response

        # Do not track AJAX requests..
        if request.is_ajax() and not TRACK_AJAX_REQUESTS:
            return response

        # Do not track if HTTP HttpResponse status_code blacklisted
        if response.status_code in TRACK_IGNORE_STATUS_CODES:
            return response

        # If dealing with a non-authenticated user, we still should track the
        # session since if authentication happens, the `session_key` carries
        # over, thus having a more accurate start time of session
        user = getattr(request, 'user', None)

        # Check for anonymous users
        if not user or user.is_anonymous():
            if not TRACK_ANONYMOUS_USERS:
                return response
            user = None

        # Force a save to generate a session key if one does not exist
        if not request.session.session_key:
            request.session.save()

        # A Visitor row is unique by session_key
        session_key = request.session.session_key

        try:
            visitor = Visitor.objects.get(pk=session_key)
        except Visitor.DoesNotExist:
            # Log the ip address. Start time is managed via the
            # field `default` value
            visitor = Visitor(pk=session_key, ip_address=get_ip_address(request),
                user_agent=request.META.get('HTTP_USER_AGENT', None))

        # Update the user field if the visitor user is not set. This
        # implies authentication has occured on this request and now
        # the user is object exists. Check using `user_id` to prevent
        # a database hit.
        if user and not visitor.user_id:
            visitor.user = user

        visitor.expiry_age = request.session.get_expiry_age()
        visitor.expiry_time = request.session.get_expiry_date()

        # Be conservative with the determining time on site since simply
        # increasing the session timeout could greatly skew results. This
        # is the only time we can guarantee.
        now = timezone.now()
        time_on_site = 0
        if visitor.start_time:
            time_on_site = (now - visitor.start_time).seconds
        visitor.time_on_site = time_on_site

        visitor.save()

        if TRACK_PAGEVIEWS:
            # Match against `path_info` to not include the SCRIPT_NAME..
            path = request.path_info.lstrip('/')
            for url in TRACK_IGNORE_URLS:
                if url.match(path):
                    break
            else:
                pageview = Pageview(visitor=visitor, url=request.path,
                    view_time=now, method=request.method)
                pageview.save()

        return response

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from tracking.compat import User


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Visitor'
        db.create_table('tracking_visitor', (
            ('session_key', self.gf('django.db.models.fields.CharField')(max_length=40, primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='visit_history', null=True, to=User)),
            ('ip_address', self.gf('django.db.models.fields.CharField')(max_length=39)),
            ('user_agent', self.gf('django.db.models.fields.TextField')()),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('expiry_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('end_time', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal('tracking', ['Visitor'])


    def backwards(self, orm):
        
        # Deleting model 'Visitor'
        db.delete_table('tracking_visitor')


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
        'tracking.visitor': {
            'Meta': {'ordering': "('-start_time',)", 'object_name': 'Visitor'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expiry_time': ('django.db.models.fields.DateTimeField', [], {}),
            'ip_address': ('django.db.models.fields.CharField', [], {'max_length': '39'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'visit_history'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_agent': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['tracking']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_visitor_expiry_age
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Visitor.expiry_age'
        db.add_column('tracking_visitor', 'expiry_age', self.gf('django.db.models.fields.IntegerField')(default=1200), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Visitor.expiry_age'
        db.delete_column('tracking_visitor', 'expiry_age')


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
        'tracking.visitor': {
            'Meta': {'ordering': "('-start_time',)", 'object_name': 'Visitor'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expiry_age': ('django.db.models.fields.IntegerField', [], {}),
            'expiry_time': ('django.db.models.fields.DateTimeField', [], {}),
            'ip_address': ('django.db.models.fields.CharField', [], {'max_length': '39'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'visit_history'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_agent': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['tracking']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_visitor_time_on_site__chg_field_visitor_expiry_time__c
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Visitor.time_on_site'
        db.add_column('tracking_visitor', 'time_on_site', self.gf('django.db.models.fields.IntegerField')(null=True), keep_default=False)

        # Changing field 'Visitor.expiry_time'
        db.alter_column('tracking_visitor', 'expiry_time', self.gf('django.db.models.fields.DateTimeField')(null=True))

        # Changing field 'Visitor.expiry_age'
        db.alter_column('tracking_visitor', 'expiry_age', self.gf('django.db.models.fields.IntegerField')(null=True))


    def backwards(self, orm):
        
        # Deleting field 'Visitor.time_on_site'
        db.delete_column('tracking_visitor', 'time_on_site')

        # User chose to not deal with backwards NULL issues for 'Visitor.expiry_time'
        raise RuntimeError("Cannot reverse this migration. 'Visitor.expiry_time' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'Visitor.expiry_age'
        raise RuntimeError("Cannot reverse this migration. 'Visitor.expiry_age' and its values cannot be restored.")


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
        'tracking.visitor': {
            'Meta': {'ordering': "('-start_time',)", 'object_name': 'Visitor'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expiry_age': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'expiry_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'ip_address': ('django.db.models.fields.CharField', [], {'max_length': '39'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'time_on_site': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'visit_history'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_agent': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['tracking']

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_visitor_user_agent
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Visitor.user_agent'
        db.alter_column('tracking_visitor', 'user_agent', self.gf('django.db.models.fields.TextField')(null=True))


    def backwards(self, orm):
        
        # Changing field 'Visitor.user_agent'
        db.alter_column('tracking_visitor', 'user_agent', self.gf('django.db.models.fields.TextField')(default=''))


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
        'tracking.visitor': {
            'Meta': {'ordering': "('-start_time',)", 'object_name': 'Visitor'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expiry_age': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'expiry_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'ip_address': ('django.db.models.fields.CharField', [], {'max_length': '39'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'time_on_site': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'visit_history'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_agent': ('django.db.models.fields.TextField', [], {'null': 'True'})
        }
    }

    complete_apps = ['tracking']

########NEW FILE########
__FILENAME__ = 0005_auto__add_pageview
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Pageview'
        db.create_table('tracking_pageview', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('visitor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='pageviews', to=orm['tracking.Visitor'])),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('view_time', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('tracking', ['Pageview'])


    def backwards(self, orm):
        
        # Deleting model 'Pageview'
        db.delete_table('tracking_pageview')


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
        'tracking.pageview': {
            'Meta': {'object_name': 'Pageview'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'view_time': ('django.db.models.fields.DateTimeField', [], {}),
            'visitor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'pageviews'", 'to': "orm['tracking.Visitor']"})
        },
        'tracking.visitor': {
            'Meta': {'ordering': "('-start_time',)", 'object_name': 'Visitor'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expiry_age': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'expiry_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'ip_address': ('django.db.models.fields.CharField', [], {'max_length': '39'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'time_on_site': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'visit_history'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_agent': ('django.db.models.fields.TextField', [], {'null': 'True'})
        }
    }

    complete_apps = ['tracking']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_pageview_method
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Pageview.method'
        db.add_column(u'tracking_pageview', 'method',
                      self.gf('django.db.models.fields.CharField')(max_length=20, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Pageview.method'
        db.delete_column(u'tracking_pageview', 'method')


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
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'tracking.pageview': {
            'Meta': {'ordering': "('-view_time',)", 'object_name': 'Pageview'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'view_time': ('django.db.models.fields.DateTimeField', [], {}),
            'visitor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'pageviews'", 'to': u"orm['tracking.Visitor']"})
        },
        u'tracking.visitor': {
            'Meta': {'ordering': "('-start_time',)", 'object_name': 'Visitor'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expiry_age': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'expiry_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'ip_address': ('django.db.models.fields.CharField', [], {'max_length': '39'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'time_on_site': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'visit_history'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'user_agent': ('django.db.models.fields.TextField', [], {'null': 'True'})
        }
    }

    complete_apps = ['tracking']
########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_pageview_url
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Pageview.url'
        db.alter_column(u'tracking_pageview', 'url', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):

        # Changing field 'Pageview.url'
        db.alter_column(u'tracking_pageview', 'url', self.gf('django.db.models.fields.CharField')(max_length=500))

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
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'tracking.pageview': {
            'Meta': {'ordering': "('-view_time',)", 'object_name': 'Pageview'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {}),
            'view_time': ('django.db.models.fields.DateTimeField', [], {}),
            'visitor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'pageviews'", 'to': u"orm['tracking.Visitor']"})
        },
        u'tracking.visitor': {
            'Meta': {'ordering': "('-start_time',)", 'object_name': 'Visitor'},
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'expiry_age': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'expiry_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'ip_address': ('django.db.models.fields.CharField', [], {'max_length': '39'}),
            'session_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'time_on_site': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'visit_history'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'user_agent': ('django.db.models.fields.TextField', [], {'null': 'True'})
        }
    }

    complete_apps = ['tracking']
########NEW FILE########
__FILENAME__ = models
import logging
import traceback
from datetime import datetime
from django.utils import timezone
from django.contrib.gis.geoip import HAS_GEOIP
if HAS_GEOIP:
    from django.contrib.gis.geoip import GeoIP, GeoIPException
from django.db import models
from django.conf import settings
from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import post_save, pre_delete
from tracking.managers import VisitorManager, PageviewManager
from tracking.settings import TRACK_USING_GEOIP
from .compat import User

GEOIP_CACHE_TYPE = getattr(settings, 'GEOIP_CACHE_TYPE', 4)

log = logging.getLogger(__file__)

class Visitor(models.Model):
    session_key = models.CharField(max_length=40, primary_key=True)
    user = models.ForeignKey(User, related_name='visit_history',
        null=True, editable=False)
    # Update to GenericIPAddress in Django 1.4
    ip_address = models.CharField(max_length=39, editable=False)
    user_agent = models.TextField(null=True, editable=False)
    start_time = models.DateTimeField(default=timezone.now, editable=False)
    expiry_age = models.IntegerField(null=True, editable=False)
    expiry_time = models.DateTimeField(null=True, editable=False)
    time_on_site = models.IntegerField(null=True, editable=False)
    end_time = models.DateTimeField(null=True, editable=False)

    objects = VisitorManager()

    def session_expired(self):
        "The session has ended due to session expiration"
        if self.expiry_time:
            return self.expiry_time <= timezone.now()
        return False
    session_expired.boolean = True

    def session_ended(self):
        "The session has ended due to an explicit logout"
        return bool(self.end_time)
    session_ended.boolean = True

    @property
    def geoip_data(self):
        "Attempts to retrieve MaxMind GeoIP data based upon the visitor's IP"
        if not HAS_GEOIP or not TRACK_USING_GEOIP:
            return

        if not hasattr(self, '_geoip_data'):
            self._geoip_data = None
            try:
                gip = GeoIP(cache=GEOIP_CACHE_TYPE)
                self._geoip_data = gip.city(self.ip_address)
            except GeoIPException:
                log.error('Error getting GeoIP data for IP "%s": %s' % (self.ip_address, traceback.format_exc()))

        return self._geoip_data

    class Meta(object):
        ordering = ('-start_time',)
        permissions = (
            ('view_visitor', 'Can view visitor'),
        )


class Pageview(models.Model):
    visitor = models.ForeignKey(Visitor, related_name='pageviews')
    url = models.TextField(null=False, editable=False)
    method = models.CharField(max_length=20, null=True)
    view_time = models.DateTimeField()

    objects = PageviewManager()

    class Meta(object):
        ordering = ('-view_time',)


from tracking import handlers
user_logged_out.connect(handlers.track_ended_session)
post_save.connect(handlers.post_save_cache, sender=Visitor)

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

TRACK_AJAX_REQUESTS = getattr(settings, 'TRACK_AJAX_REQUESTS', False)
TRACK_ANONYMOUS_USERS = getattr(settings, 'TRACK_ANONYMOUS_USERS', True)

TRACK_PAGEVIEWS = getattr(settings, 'TRACK_PAGEVIEWS', False)

TRACK_IGNORE_URLS = getattr(settings, 'TRACK_IGNORE_URLS', (
    r'^(favicon\.ico|robots\.txt)$',
))

TRACK_IGNORE_STATUS_CODES = getattr(settings, 'TRACK_IGNORE_STATUS_CODES', [])

TRACK_USING_GEOIP = getattr(settings, 'TRACK_USING_GEOIP', False)
if hasattr(settings, 'TRACKING_USE_GEOIP'):
    raise DeprecationWarning('TRACKING_USE_GEOIP has been renamed to TRACK_USING_GEOIP')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

urlpatterns = patterns('tracking.views',
    url(r'^$', 'dashboard', name='tracking-dashboard'),
    url(r'^dashboard/$', 'stats'),
)

########NEW FILE########
__FILENAME__ = utils
import re

headers = ('HTTP_CLIENT_IP', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED',
    'HTTP_X_CLUSTERED_CLIENT_IP', 'HTTP_FORWARDED_FOR', 'HTTP_FORWARDED',
    'REMOTE_ADDR')

# Back ported from Django trunk
# This code was mostly based on ipaddr-py
# Copyright 2007 Google Inc. http://code.google.com/p/ipaddr-py/
# Licensed under the Apache License, Version 2.0 (the "License").
ipv4_re = re.compile(r'^(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}$')

def is_valid_ipv4_address(ip_str):
    return bool(ipv4_re.match(ip_str))


def is_valid_ipv6_address(ip_str):
    """
    Ensure we have a valid IPv6 address.

    Args:
        ip_str: A string, the IPv6 address.

    Returns:
        A boolean, True if this is a valid IPv6 address.

    """
    # We need to have at least one ':'.
    if ':' not in ip_str:
        return False

    # We can only have one '::' shortener.
    if ip_str.count('::') > 1:
        return False

    # '::' should be encompassed by start, digits or end.
    if ':::' in ip_str:
        return False

    # A single colon can neither start nor end an address.
    if ((ip_str.startswith(':') and not ip_str.startswith('::')) or
            (ip_str.endswith(':') and not ip_str.endswith('::'))):
        return False

    # We can never have more than 7 ':' (1::2:3:4:5:6:7:8 is invalid)
    if ip_str.count(':') > 7:
        return False

    # If we have no concatenation, we need to have 8 fields with 7 ':'.
    if '::' not in ip_str and ip_str.count(':') != 7:
        # We might have an IPv4 mapped address.
        if ip_str.count('.') != 3:
            return False

    ip_str = _explode_shorthand_ip_string(ip_str)

    # Now that we have that all squared away, let's check that each of the
    # hextets are between 0x0 and 0xFFFF.
    for hextet in ip_str.split(':'):
        if hextet.count('.') == 3:
            # If we have an IPv4 mapped address, the IPv4 portion has to
            # be at the end of the IPv6 portion.
            if not ip_str.split(':')[-1] == hextet:
                return False
            if not is_valid_ipv4_address(hextet):
                return False
        else:
            try:
                # a value error here means that we got a bad hextet,
                # something like 0xzzzz
                if int(hextet, 16) < 0x0 or int(hextet, 16) > 0xFFFF:
                    return False
            except ValueError:
                return False
    return True

def _sanitize_ipv4_mapping(ip_str):
    """
    Sanitize IPv4 mapping in a expanded IPv6 address.

    This converts ::ffff:0a0a:0a0a to ::ffff:10.10.10.10.
    If there is nothing to sanitize, returns an unchanged
    string.

    Args:
        ip_str: A string, the expanded IPv6 address.

    Returns:
        The sanitized output string, if applicable.
    """
    if not ip_str.lower().startswith('0000:0000:0000:0000:0000:ffff:'):
        # not an ipv4 mapping
        return ip_str

    hextets = ip_str.split(':')

    if '.' in hextets[-1]:
        # already sanitized
        return ip_str

    ipv4_address = "%d.%d.%d.%d" % (
        int(hextets[6][0:2], 16),
        int(hextets[6][2:4], 16),
        int(hextets[7][0:2], 16),
        int(hextets[7][2:4], 16),
    )

    result = ':'.join(hextets[0:6])
    result += ':' + ipv4_address

    return result

def _unpack_ipv4(ip_str):
    """
    Unpack an IPv4 address that was mapped in a compressed IPv6 address.

    This converts 0000:0000:0000:0000:0000:ffff:10.10.10.10 to 10.10.10.10.
    If there is nothing to sanitize, returns None.

    Args:
        ip_str: A string, the expanded IPv6 address.

    Returns:
        The unpacked IPv4 address, or None if there was nothing to unpack.
    """
    if not ip_str.lower().startswith('0000:0000:0000:0000:0000:ffff:'):
        return None

    hextets = ip_str.split(':')
    return hextets[-1]

def _explode_shorthand_ip_string(ip_str):
    """
    Expand a shortened IPv6 address.

    Args:
        ip_str: A string, the IPv6 address.

    Returns:
        A string, the expanded IPv6 address.

    """
    if not _is_shorthand_ip(ip_str):
        # We've already got a longhand ip_str.
        return ip_str

    new_ip = []
    hextet = ip_str.split('::')

    # If there is a ::, we need to expand it with zeroes
    # to get to 8 hextets - unless there is a dot in the last hextet,
    # meaning we're doing v4-mapping
    if '.' in ip_str.split(':')[-1]:
        fill_to = 7
    else:
        fill_to = 8

    if len(hextet) > 1:
        sep = len(hextet[0].split(':')) + len(hextet[1].split(':'))
        new_ip = hextet[0].split(':')

        for _ in xrange(fill_to - sep):
            new_ip.append('0000')
        new_ip += hextet[1].split(':')

    else:
        new_ip = ip_str.split(':')

    # Now need to make sure every hextet is 4 lower case characters.
    # If a hextet is < 4 characters, we've got missing leading 0's.
    ret_ip = []
    for hextet in new_ip:
        ret_ip.append(('0' * (4 - len(hextet)) + hextet).lower())
    return ':'.join(ret_ip)


def _is_shorthand_ip(ip_str):
    """Determine if the address is shortened.

    Args:
        ip_str: A string, the IPv6 address.

    Returns:
        A boolean, True if the address is shortened.

    """
    if ip_str.count('::') == 1:
        return True
    if filter(lambda x: len(x) < 4, ip_str.split(':')):
        return True
    return False

def get_ip_address(request):
    for header in headers:
        if request.META.get(header, None):
            ip = request.META[header].split(',')[0]
            if ':' in ip and is_valid_ipv6_address(ip) or is_valid_ipv4_address(ip):
                return ip


########NEW FILE########
__FILENAME__ = views
import logging
import calendar
from warnings import warn
from datetime import datetime, time
from datetime import date, timedelta
from django.db.models import Min
from django.shortcuts import render
from django.contrib.auth.decorators import permission_required
from django.utils.timezone import now
from tracking.models import Visitor, Pageview
from tracking.settings import TRACK_PAGEVIEWS

log = logging.getLogger(__file__)

def parse_partial_date(date_str, upper=False):
    if not date_str:
        return

    day = None
    toks = [int(x) for x in date_str.split('-')]

    if len(toks) > 3:
        return None

    if len(toks) == 3:
        year, month, day = toks
    # Nissing day
    elif len(toks) == 2:
        year, month = toks
    # Only year
    elif len(toks) == 1:
        year, = toks
        month = 1 if upper else 12

    if not day:
        day = calendar.monthrange(year, month)[0] if upper else 1

    return date(year, month, day)


@permission_required('tracking.view_visitor')
def dashboard(request):
    "Counts, aggregations and more!"
    errors = []
    start_date, end_date = None, None

    try:
        start_str = request.GET.get('start', None)
        start_date = parse_partial_date(start_str)
    except (ValueError, TypeError):
        errors.append('<code>{0}</code> is not a valid start date'.format(start_str))

    try:
        end_str = request.GET.get('end', None)
        end_date = parse_partial_date(end_str, upper=True)
    except (ValueError, TypeError):
        errors.append('<code>{0}</code> is not a valid end date'.format(end_str))

    user_stats = list(Visitor.objects.user_stats(start_date, end_date))

    track_start_time = Visitor.objects.order_by('start_time')[0].start_time
    # If the start_date is later than when tracking began, no reason
    # to warn about missing data
    if start_date and calendar.timegm(start_date.timetuple()) < calendar.timegm(track_start_time.timetuple()):
        warn_start_time = track_start_time
    else:
        warn_start_time = None
    context = {
        'errors': errors,
        'track_start_time': track_start_time,
        'warn_start_time': warn_start_time,
        'visitor_stats': Visitor.objects.stats(start_date, end_date),
        'user_stats': user_stats,
        'tracked_dates': Visitor.objects.tracked_dates(),
    }

    if TRACK_PAGEVIEWS:
        context['pageview_stats'] = Pageview.objects.stats(start_date, end_date)
    if not end_date:
        context['end_date'] = now()
    else:
        context['end_date'] = end_date
    if not start_date:
        context['start_date'] = track_start_time
    else:
        context['start_date'] = datetime.combine(start_date, time.min)

    return render(request, 'tracking/dashboard.html', context)


def stats(*args, **kwargs):
    warn('The stats view has been renamed to dashboard and the /dashboard/ URL has be moved to the root /', DeprecationWarning)
    return dashboard(*args, **kwargs)

########NEW FILE########
