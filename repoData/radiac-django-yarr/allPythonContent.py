__FILENAME__ = runtests
#!/usr/bin/env python

import sys
import os

from django.conf import settings


def configure_django():
    installed_apps = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
        'yarr',
    )
    if os.environ.get('USE_SOUTH', ''):
        installed_apps += ('south',)

    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        ROOT_URLCONF='yarr.urls',
        USE_TZ=False,
        INSTALLED_APPS=installed_apps,
    )

if __name__ == '__main__':
    configure_django()

    import django
    from django.core.management import execute_from_command_line

    # Test discovery changed in Django 1.6 to require a full import path rather
    # than an app label.
    if django.VERSION >= (1, 6):
        args = ['yarr.tests']
    else:
        args = ['yarr']

    execute_from_command_line(sys.argv[0:1] + ['test'] + args)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from yarr import models


class FeedAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'is_active', 'user', 'next_check', 'error',
    ]
    list_filter = ['is_active', 'user']
    search_fields = ['title', 'feed_url', 'site_url']
    actions = ['deactivate', 'clear_error']
    
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)
    deactivate.short_description = 'Deactivate feed'
    
    def clear_error(self, request, queryset):
        queryset.update(is_active=True, error='')
    clear_error.short_description = "Clear error and reactivate feed"

admin.site.register(models.Feed, FeedAdmin)


class EntryAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'date', 'state', 'feed',
    ]
    list_select_related = True
    search_fields = ['title', 'content',]

admin.site.register(models.Entry, EntryAdmin)

########NEW FILE########
__FILENAME__ = constants
"""
Yarr constants
"""

# Entry state - must be also defined in yarr.js
ENTRY_UNREAD = 0
ENTRY_READ = 1
ENTRY_SAVED = 2

ORDER_ASC = 'asc'
ORDER_DESC = 'desc'

########NEW FILE########
__FILENAME__ = decorators
from yarr import settings

def with_socket_timeout(fn):
    """
    Call a function while the global socket timeout is ``YARR_SOCKET_TIMEOUT``
    
    The socket timeout value is set before calling the function, then reset to
    the original timeout value afterwards
    
    Note: This is not thread-safe.
    """
    def wrap(*args, **kwargs):
        # Set global socket
        import socket
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(settings.SOCKET_TIMEOUT)
        
        # Call fn
        r = fn(*args, **kwargs)
        
        # Reset global socket
        socket.setdefaulttimeout(old_timeout)
        
        return r
    
    return wrap

########NEW FILE########
__FILENAME__ = forms
from django import forms

from yarr import settings, models

class AddFeedForm(forms.ModelForm):
    required_css_class = 'required'
    class Meta:
        model = models.Feed
        fields = ['feed_url']
        widgets = {
            'feed_url':     forms.TextInput(),
        }

def _build_frequency_choices():
    """
    Build a choices list of frequencies
    This will be removed when Yarr moves to automated frequencies
    """
    choices = []
    current = settings.MAXIMUM_INTERVAL
    HOUR = 60
    DAY = 60 * 24
    MIN = settings.MINIMUM_INTERVAL
    while current >= MIN:
        # Create humanised relative time
        # There are many ways to do this, but to avoid introducing a dependency
        # only to remove it again a few releases later, we'll do this by hand
        dd = 0
        hh = 0
        mm = current
        parts = []
        
        if mm > DAY:
            dd = mm / DAY
            mm = mm % DAY
            parts.append('%s day%s' % (dd, 's' if dd > 1 else ''))
            
        if mm > HOUR:
            hh = mm / HOUR
            mm = mm % HOUR
            parts.append('%s hour%s' % (hh, 's' if hh > 1 else ''))
        
        if mm > 0:
            parts.append('%s minute%s' % (mm, 's' if mm > 1 else ''))
        
        if len(parts) == 3:
            human = '%s, %s and %s' % tuple(parts)
        elif len(parts) == 2:
            human = '%s and %s' % tuple(parts)
        else:
            human = parts[0]
        
        choices.append((current, human))
        
        old = current
        current = int(current / 2)
        if old > MIN and current < MIN:
            current = MIN
    
    return choices

class EditFeedForm(forms.ModelForm):
    required_css_class = 'required'
    check_frequency = forms.ChoiceField(
        widget=forms.Select,
        choices=_build_frequency_choices(),
        label='Frequency',
        help_text=u'How often to check the feed for changes',
    )
    class Meta:
        model = models.Feed
        fields = ['text', 'feed_url', 'is_active', 'check_frequency']
        widgets = {
            'text':    forms.TextInput(),
            'feed_url': forms.TextInput(),
            'title':    forms.TextInput(),
        }

########NEW FILE########
__FILENAME__ = check_feeds
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand

from yarr import models
from yarr.decorators import with_socket_timeout


# Supress feedparser's DeprecationWarning in production environments - we don't
# care about the changes to updated and published, we're already doing it right
if not settings.DEBUG:
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning) 


class Command(BaseCommand):
    help = 'Check feeds for updates'
    option_list = BaseCommand.option_list + (
        make_option(
            '--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force all feeds to update',
        ),
        make_option(
            '--read',
            action='store_true',
            dest='read',
            default=False,
            help='Any new items will be marked as read; useful when importing',
        ),
        make_option(
            '--purge',
            action='store_true',
            dest='purge',
            default=False,
            help='Purge current entries and reset feed counters',
        ),
        make_option(
            '--verbose',
            action='store_true',
            dest='verbose',
            default=False,
            help='Print information to the console',
        ),
        make_option(
            '--url',
            dest='url',
            help='Specify the URL to update',
        ),
    )
    
    @with_socket_timeout
    def handle(self, *args, **options):
        # Apply url filter
        entries = models.Entry.objects.all()
        feeds = models.Feed.objects.all()
        if options['url']:
            feeds = feeds.filter(feed_url=options['url'])
            if feeds.count() == 0:
                raise ValueError('Specified URL must be a known feed')
            entries = entries.filter(feed=feeds)
        
        # Purge current entries
        if options['purge']:
            entries.delete()
            feeds.update(
                last_updated=None,
                last_checked=None,
                next_check=None,
            )
        
        # Check feeds for updates
        feeds.check(
            force=options['force'],
            read=options['read'],
            logfile=self.stdout if options['verbose'] else None,
        )

########NEW FILE########
__FILENAME__ = import_opml
from optparse import make_option
import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from yarr import models
from yarr.utils import import_opml


class Command(BaseCommand):
    help = 'Import subscriptions from an OPML file'

    option_list = BaseCommand.option_list + (
        make_option(
            '--purge',
            action='store_true',
            dest='purge',
            default=False,
            help='Purge current feeds for this user',
        ),
    )

    def handle(self, subscription_file, username, *args, **options):
        # Get subscriptions
        if not os.path.exists(subscription_file):
            raise CommandError(
                'Subscription file "%s" does not exist' % subscription_file
            )

        # Look up user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError('User "%s" does not exist' % username)

        # Purge current entries
        if options['purge']:
            print(("Purging feeds for %s..." % user))
            models.Feed.objects.filter(user=user).delete()

        # Parse subscription
        print("Importing feeds...")
        new_count, old_count = import_opml(
            subscription_file,
            user,
            options['purge']
        )

        print(("Imported %s new feeds and %s already existed for %s" % (new_count, old_count, user)))

########NEW FILE########
__FILENAME__ = yarr_clean
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand

from yarr import models
from yarr.decorators import with_socket_timeout


class Command(BaseCommand):
    help = 'Yarr cleaning tool'
    option_list = BaseCommand.option_list + (
        make_option(
            '--delete_read',
            action='store_true',
            dest='delete_read',
            default=False,
            help='Delete all read (unsaved) entries',
        ),
        make_option(
            '--update_cache',
            action='store_true',
            dest='update_cache',
            default=False,
            help='Update cache values',
        ),
    )
    
    @with_socket_timeout
    def handle(self, *args, **options):
        # Delete all read entries - useful for upgrades to 0.3.12
        if options['delete_read']:
            feeds = models.Feed.objects.filter(is_active=False)
            for feed in feeds:
                feed.entries.read().delete()
                feed.save()
        
        # Update feed unread and total counts
        if options['update_cache']:
            models.Feed.objects.update_count_unread().update_count_total()
        
########NEW FILE########
__FILENAME__ = managers
"""
Yarr model managers
"""
import datetime
import time

from django.db import connection, models, transaction

import bleach

from yarr import settings
from yarr.constants import ENTRY_UNREAD, ENTRY_READ, ENTRY_SAVED


###############################################################################
#                                                               Feed model

class FeedQuerySet(models.query.QuerySet):
    def active(self):
        "Filter to active feeds"
        return self.filter(is_active=True)
        
    def check(self, force=False, read=False, logfile=None):
        "Check active feeds for updates"
        for feed in self.active():
            feed.check(force, read, logfile)
        
        # Update the total and unread counts
        self.update_count_unread()
        self.update_count_total()
        
        return self
    
    def _do_update(self, extra):
        "Perform the update for update_count_total and update_count_unread"
        # Get IDs for current queries
        ids = self.values_list('id', flat=True)
        
        # If no IDs, no sense trying to do anything
        if not ids:
            return self
        
        # Prepare query options
        # IDs and states should only ever be ints, but force them to
        # ints to be sure we don't introduce injection vulns
        opts = {
            'feed':     models.loading.get_model('yarr', 'Feed')._meta.db_table,
            'entry':    models.loading.get_model('yarr', 'Entry')._meta.db_table,
            'ids':      ','.join([str(int(id)) for id in ids]),
            
            # Fields which should be set in extra
            'field':    '',
            'where':    '',
        }
        opts.update(extra)
        
        # Uses raw query so we can update in a single call to avoid race condition
        cursor = connection.cursor()
        cursor.execute(
            """UPDATE %(feed)s
                SET %(field)s=COALESCE(
                    (
                        SELECT COUNT(1)
                            FROM %(entry)s
                            WHERE %(feed)s.id=feed_id%(where)s
                            GROUP BY feed_id
                    ), 0
                )
                WHERE id IN (%(ids)s)
            """ % opts
        )
        
        # Ensure changes are committed in Django 1.5 or earlier
        transaction.commit_unless_managed()
        
        return self
    
    def update_count_total(self):
        "Update the cached total counts"
        return self._do_update({
            'field':    'count_total',
        })
        
    def update_count_unread(self):
        "Update the cached unread counts"
        return self._do_update({
            'field':    'count_unread',
            'where':    ' AND state=%s' % ENTRY_UNREAD,
        })
    
    def count_unread(self):
        "Get a dict of unread counts, with feed pks as keys"
        return dict(self.values_list('pk', 'count_unread'))
    
    
class FeedManager(models.Manager):
    def active(self):
        "Active feeds"
        return self.get_query_set().active()
        
    def check(self, force=False, read=False, logfile=None):
        "Check all active feeds for updates"
        return self.get_query_set().check(force, read, logfile)
        
    def update_count_total(self):
        "Update the cached total counts"
        return self.get_query_set().update_count_total()
    
    def update_count_unread(self):
        "Update the cached unread counts"
        return self.get_query_set().update_count_unread()
    
    def count_unread(self):
        "Get a dict of unread counts, with feed pks as keys"
        return self.get_query_set().count_unread()
        
    def get_query_set(self):
        "Return a FeedQuerySet"
        return FeedQuerySet(self.model)



###############################################################################
#                                                               Entry model

class EntryQuerySet(models.query.QuerySet):
    def user(self, user):
        "Filter by user"
        return self.filter(feed__user=user)
        
    def read(self):
        "Filter to read entries"
        return self.filter(state=ENTRY_READ)
        
    def unread(self):
        "Filter to unread entries"
        return self.filter(state=ENTRY_UNREAD)
        
    def saved(self):
        "Filter to saved entries"
        return self.filter(state=ENTRY_SAVED)
    
    def set_state(self, state, count_unread=False):
        """
        Set a new state for these entries
        If count_unread=True, returns a dict of the new unread count for the
        affected feeds, {feed_pk: unread_count, ...}; if False, returns nothing
        """
        # Get list of feed pks before the update changes this queryset
        feed_pks = list(self.feeds().values_list('pk', flat=True))
        
        # Update the state
        self.update(state=state)
        
        # Look up affected feeds
        feeds = models.loading.get_model('yarr', 'Feed').objects.filter(
            pk__in=feed_pks
        )
        
        # Update the unread counts for affected feeds
        feeds.update_count_unread()
        if count_unread:
            return feeds.count_unread()
        
    def feeds(self):
        "Get feeds associated with entries"
        return models.loading.get_model('yarr', 'Feed').objects.filter(
            entries__in=self
        ).distinct()
        
    def set_expiry(self):
        "Ensure selected entries are set to expire"
        return self.filter(
            expires__isnull=True
        ).update(
            expires=datetime.datetime.now() + datetime.timedelta(
                days=settings.ITEM_EXPIRY,
            )
        )
    
    def clear_expiry(self):
        "Ensure selected entries will not expire"
        return self.exclude(
            expires__isnull=True
        ).update(expires=None)
        
    def update_feed_unread(self):
        "Update feed read count cache"
        return self.feeds().update_count_unread()

    
class EntryManager(models.Manager):
    def user(self, user):
        "Filter by user"
        return self.get_query_set().user(user)
    
    def read(self):
        "Get read entries"
        return self.get_query_set().read()
        
    def unread(self):
        "Get unread entries"
        return self.get_query_set().unread()
        
    def saved(self):
        "Get saved entries"
        return self.get_query_set().saved()
        
    def set_state(self, state):
        "Set a new state for these entries, and update unread count"
        return self.get_query_set().set_state(state)
    
    def update_feed_unread(self):
        "Update feed read count cache"
        return self.get_query_set().update_feed_unread()
        
    def from_feedparser(self, raw):
        """
        Create an Entry object from a raw feedparser entry
        
        Arguments:
            raw         The raw feedparser entry
        
        Returns:
            entry       An Entry instance (not saved)
        
        # ++ TODO: tags
        Any tags will be stored on _tags, to be moved to tags field after save
        
        The content field must be sanitised HTML of the entry's content, or
        failing that its sanitised summary or description.
        
        The date field should use the entry's updated date, then its published
        date, then its created date. If none of those are present, it will fall
        back to the current datetime when it is first saved.
        
        The guid is either the guid according to the feed, or the entry link.
    
        Currently ignoring the following feedparser attributes:
            author_detail
            contributors
            created
            enclosures
            expired
            license
            links
            publisher
            source
            summary_detail
            title_detail
            vcard
            xfn
        """
        # Create a new entry
        entry = self.model()
        
        # Get the title and content
        entry.title = raw.get('title', '')
        content = raw.get('content', [{'value': ''}])[0]['value']
        if not content:
            content = raw.get('description', '')
        
        # Sanitise the content
        entry.content = bleach.clean(
            content,
            tags=settings.ALLOWED_TAGS,
            attributes=settings.ALLOWED_ATTRIBUTES,
            styles=settings.ALLOWED_STYLES,
            strip=True,
        )
        
        # Order: updated, published, created
        # If not provided, needs to be None for update comparison
        # Will default to current time when saved
        date = raw.get(
            'updated_parsed', raw.get(
                'published_parsed', raw.get(
                    'created_parsed', None
                )
            )
        )
        if date is not None:
            entry.date = datetime.datetime.fromtimestamp(
                time.mktime(date)
            )
        
        entry.url = raw.get('link', '')
        entry.guid = raw.get('guid', entry.url)
        
        entry.author = raw.get('author', '')
        entry.comments_url = raw.get('comments', '')
        
        # ++ TODO: tags
        """
        tags = raw.get('tags', None)
        if tags is not None:
            entry._tags = tags
        """
        
        return entry
        
    def get_query_set(self):
        """
        Return an EntryQuerySet
        """
        return EntryQuerySet(self.model)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Feed'
        db.create_table('yarr_feed', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('feed_url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('site_url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('added', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('check_frequency', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_checked', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('next_check', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('error', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal('yarr', ['Feed'])

        # Adding model 'Entry'
        db.create_table('yarr_entry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('feed', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entries', to=orm['yarr.Feed'])),
            ('read', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('saved', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('author', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('comments_url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('guid', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal('yarr', ['Entry'])


    def backwards(self, orm):
        # Deleting model 'Feed'
        db.delete_table('yarr_feed')

        # Deleting model 'Entry'
        db.delete_table('yarr_entry')


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
        'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'comments_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'saved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_feed_title__chg_field_entry_author__chg_field_entry_ti
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Feed.title'
        db.alter_column(u'yarr_feed', 'title', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Entry.author'
        db.alter_column(u'yarr_entry', 'author', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Entry.title'
        db.alter_column(u'yarr_entry', 'title', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Entry.guid'
        db.alter_column(u'yarr_entry', 'guid', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):

        # Changing field 'Feed.title'
        db.alter_column(u'yarr_feed', 'title', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Entry.author'
        db.alter_column(u'yarr_entry', 'author', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Entry.title'
        db.alter_column(u'yarr_entry', 'title', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Entry.guid'
        db.alter_column(u'yarr_entry', 'guid', self.gf('django.db.models.fields.CharField')(max_length=255))

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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'saved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_feed_feed_url__chg_field_feed_site_url__chg_field_entr
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Feed.feed_url'
        db.alter_column(u'yarr_feed', 'feed_url', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Feed.site_url'
        db.alter_column(u'yarr_feed', 'site_url', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Entry.comments_url'
        db.alter_column(u'yarr_entry', 'comments_url', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Entry.url'
        db.alter_column(u'yarr_entry', 'url', self.gf('django.db.models.fields.TextField')())

    def backwards(self, orm):

        # Changing field 'Feed.feed_url'
        db.alter_column(u'yarr_feed', 'feed_url', self.gf('django.db.models.fields.URLField')(max_length=200))

        # Changing field 'Feed.site_url'
        db.alter_column(u'yarr_feed', 'site_url', self.gf('django.db.models.fields.URLField')(max_length=200))

        # Changing field 'Entry.comments_url'
        db.alter_column(u'yarr_entry', 'comments_url', self.gf('django.db.models.fields.URLField')(max_length=200))

        # Changing field 'Entry.url'
        db.alter_column(u'yarr_entry', 'url', self.gf('django.db.models.fields.URLField')(max_length=200))

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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'saved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
########NEW FILE########
__FILENAME__ = 0004_auto__add_field_feed_count_unread__add_field_feed_count_total__add_fie
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Feed.count_unread'
        db.add_column(u'yarr_feed', 'count_unread',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Feed.count_total'
        db.add_column(u'yarr_feed', 'count_total',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Entry.expires'
        db.add_column(u'yarr_entry', 'expires',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Feed.count_unread'
        db.delete_column(u'yarr_feed', 'count_unread')

        # Deleting field 'Feed.count_total'
        db.delete_column(u'yarr_feed', 'count_total')

        # Deleting field 'Entry.expires'
        db.delete_column(u'yarr_entry', 'expires')


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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'saved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_unread': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
########NEW FILE########
__FILENAME__ = 0005_populate_feed_cache
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Populate the cached feed counts"
        # Change this without using model methods or custom managers, in case
        # they change in future versions and break migrations
        for feed in orm.Feed.objects.all():
            feed.count_unread = feed.entries.filter(read=False).count()
            feed.count_total = feed.entries.count()
            feed.save()

    def backwards(self, orm):
        # Cached data will be discarded
        pass

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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'saved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_unread': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_entry_state
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Entry.state'
        db.add_column(u'yarr_entry', 'state',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Entry.state'
        db.delete_column(u'yarr_entry', 'state')


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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'saved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_unread': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
########NEW FILE########
__FILENAME__ = 0007_entry_state
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

# Entry state from models.py
ENTRY_UNREAD = 0
ENTRY_READ = 1
ENTRY_SAVED = 2

class Migration(DataMigration):

    def forwards(self, orm):
        "Set entry state based on read and saved flags"
        for entry in orm['yarr.Entry'].objects.all():
            if entry.saved:
                entry.state = ENTRY_SAVED
            elif entry.read:
                entry.state = ENTRY_READ
            else:
                entry.state = ENTRY_UNREAD
            entry.save()

    def backwards(self, orm):
        "Set read and saved flags based on entry state"
        for entry in orm['yarr.Entry'].objects.all():
            if entry.state == ENTRY_SAVED:
                entry.read = False
                entry.saved = True
            elif entry.state == ENTRY_READ:
                entry.read = True
                entry.saved = False
            else:
                entry.read = False
                entry.saved = False
            entry.save()

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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'read': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'saved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_unread': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0008_auto__del_field_entry_read__del_field_entry_saved
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Entry.read'
        db.delete_column(u'yarr_entry', 'read')

        # Deleting field 'Entry.saved'
        db.delete_column(u'yarr_entry', 'saved')


    def backwards(self, orm):
        # Adding field 'Entry.read'
        db.add_column(u'yarr_entry', 'read',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Entry.saved'
        db.add_column(u'yarr_entry', 'saved',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_unread': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
########NEW FILE########
__FILENAME__ = 0009_auto__add_field_feed_text
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Feed.text'
        db.add_column(u'yarr_feed', 'text',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Feed.text'
        db.delete_column(u'yarr_feed', 'text')


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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('text', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_unread': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
########NEW FILE########
__FILENAME__ = 0010_no_null_cache
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):
    
    def forwards(self, orm):
        "Ensure no null cache values"
        orm['yarr.Feed'].objects.filter(
            count_unread__isnull=True).update(count_unread=0
        )
        orm['yarr.Feed'].objects.filter(
            count_total__isnull=True).update(count_total=0
        )
        
    def backwards(self, orm):
        "No action required"


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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_total': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_unread': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0011_auto__chg_field_feed_count_unread__chg_field_feed_count_total
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Feed.count_unread'
        db.alter_column(u'yarr_feed', 'count_unread', self.gf('django.db.models.fields.IntegerField')())

        # Changing field 'Feed.count_total'
        db.alter_column(u'yarr_feed', 'count_total', self.gf('django.db.models.fields.IntegerField')())

    def backwards(self, orm):

        # Changing field 'Feed.count_unread'
        db.alter_column(u'yarr_feed', 'count_unread', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'Feed.count_total'
        db.alter_column(u'yarr_feed', 'count_total', self.gf('django.db.models.fields.IntegerField')(null=True))

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
        u'yarr.entry': {
            'Meta': {'ordering': "('-date',)", 'object_name': 'Entry'},
            'author': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comments_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': u"orm['yarr.Feed']"}),
            'guid': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'yarr.feed': {
            'Meta': {'ordering': "('title', 'added')", 'object_name': 'Feed'},
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'check_frequency': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'count_total': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'count_unread': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'error': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'next_check': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.TextField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['yarr']
########NEW FILE########
__FILENAME__ = models
"""
Yarr models
"""

import datetime
import time
import urllib2

from django.core.validators import URLValidator
from django.db import models

import feedparser
# ++ TODO: tags

from yarr import settings, managers
from yarr.constants import ENTRY_UNREAD, ENTRY_READ, ENTRY_SAVED


###############################################################################
#                                                               Setup

# Disable feedparser's sanitizer - FeedManager will be using bleach instead
feedparser.SANITIZE_HTML = 0

class NullFile(object):
    """Fake file object for disabling logging in Feed.check"""
    def write(self, str):
        pass
nullfile = NullFile()


###############################################################################
#                                                               Exceptions

class FeedError(Exception):
    """
    An error occurred when fetching the feed
    
    If it was parsed despite the error, the feed and entries will be available:
        e.feed      None if not parsed
        e.entries   Empty list if not parsed
    """
    def __init__(self, *args, **kwargs):
        self.feed = kwargs.pop('feed', None)
        self.entries = kwargs.pop('entries', [])
        super(FeedError, self).__init__(*args, **kwargs)

class InactiveFeedError(FeedError):
    pass
    
class EntryError(Exception):
    """
    An error occurred when processing an entry
    """
    pass



###############################################################################
#                                                               Feed model

class Feed(models.Model):
    """
    A feed definition
    
    The last_updated field is either the updated or published date of the feed,
    or if neither are set, the feed parser's best guess.
    
    Currently ignoring the following feedparser attributes:
        author
        author_detail
        cloud
        contributors
        docs
        errorreportsto
        generator
        generator_detail
        icon
        id
        image
        info
        info_detail
        language
        license
        links
        logo
        publisher
        rights
        subtitle
        tags
        textinput
        title
        ttl
    """
    # Compulsory data fields
    title = models.TextField(help_text="Published title of the feed")
    feed_url = models.TextField("Feed URL",
        validators=[URLValidator()], help_text="URL of the RSS feed",
    )
    text = models.TextField(
        "Custom title",
        blank=True,
        help_text="Custom title for the feed - defaults to feed title above",
    )
    
    # Optional data fields
    site_url = models.TextField("Site URL",
        validators=[URLValidator()], help_text="URL of the HTML site",
    )
    
    # Internal fields
    user = models.ForeignKey('auth.User')
    added = models.DateTimeField(
        auto_now_add=True, help_text="Date this feed was added",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="A feed will become inactive when a permanent error occurs",
    )
    check_frequency = models.IntegerField(
        blank=True, null=True,
        help_text="How often to check the feed for changes, in minutes",
    )
    last_updated = models.DateTimeField(
        blank=True, null=True, help_text="Last time the feed says it changed",
    )
    last_checked = models.DateTimeField(
        blank=True, null=True, help_text="Last time the feed was checked",
    )
    next_check = models.DateTimeField(
        blank=True, null=True, help_text="When the next feed check is due",
    )
    error = models.CharField(
        blank=True, max_length=255, help_text="When a problem occurs",
    )
    
    # Cached data
    count_unread = models.IntegerField(
        default=0, help_text="Cache of number of unread items",
    )
    count_total = models.IntegerField(
        default=0, help_text="Cache of total number of items",
    )
    
    objects = managers.FeedManager()
    
    def __unicode__(self):
        return self.text or self.title
    
    def update_count_unread(self):
        """Update the cached unread count"""
        self.count_unread = self.entries.unread().count()
        
    def update_count_total(self):
        """Update the cached total item count"""
        self.count_total = self.entries.count()
    
    def _fetch_feed(self, url_history=None):
        """
        Internal method to get the feed from the specified URL
        Follows good practice
        Returns:
            feed    Feed data, or None if there was a temporary error
            entries List of entries
        Raises:
            FetchError  Feed fetch suffered permanent failure
        """
        # Request and parse the feed
        d = feedparser.parse(self.feed_url)
        status  = d.get('status', 200)
        feed    = d.get('feed', None)
        entries = d.get('entries', [])
        
        # Handle certain feedparser exceptions (bozo):
        #   URLError    The server wasn't found
        # Other exceptions will raise a FeedError, but the feed may have been
        # parsed anyway, so feed and entries will be available on the exception
        if d.get('bozo') == 1:
            bozo = d['bozo_exception']
            if isinstance(bozo, urllib2.URLError):
                raise FeedError('URL error: %s' % bozo)
                
            # Unrecognised exception
            # Most of these will be SAXParseException, which doesn't convert
            # to a string cleanly, so explicitly mention the exception class
            raise FeedError(
                'Feed error: %s - %s' % (bozo.__class__.__name__, bozo),
                feed=feed, entries=entries,
            )
            
        # Accepted status:
        #   200 OK
        #   302 Temporary redirect
        #   304 Not Modified
        #   307 Temporary redirect
        if status in (200, 302, 304, 307):
            # Check for valid feed
            if (
                feed is None
                or 'title' not in feed
                or 'link' not in feed
            ):
                raise FeedError('Feed parsed but with invalid contents')
            
            # OK
            return feed, entries
        
        # Temporary errors:
        #   404 Not Found
        #   500 Internal Server Error
        #   502 Bad Gateway
        #   503 Service Unavailable
        #   504 Gateway Timeout
        if status in (404, 500, 502, 503, 504):
            raise FeedError('Temporary error %s' % status)
        
        # Follow permanent redirection
        if status == 301:
            # Log url
            if url_history is None:
                url_history = []
            url_history.append(self.feed_url)
            
            # Avoid circular redirection
            self.feed_url = d.get('href', self.feed_url)
            if self.feed_url in url_history:
                raise InactiveFeedError('Circular redirection found')
            
            # Update feed and try again
            self.save()
            return self._fetch_feed(url_history)
        
        # Feed gone
        if status == 410:
            raise InactiveFeedError('Feed has gone')
        
        # Unknown status
        raise FeedError('Unrecognised HTTP status %s' % status)
    
    def check(self, force=False, read=False, logfile=None):
        """
        Check the feed for updates
        
        Optional arguments:
            force       Force an update
            read        Mark new entries as read
            logfile     Logfile to print report data
        
        It will update if:
        * ``force==True``
        * it has never been updated
        * it was due for an update in the past
        * it is due for an update in the next ``MINIMUM_INTERVAL`` minutes
        
        Note: because feedparser refuses to support timeouts, this method could
        block on an unresponsive connection.
        
        The official feedparser solution is to set the global socket timeout,
        but that is not thread safe, so has not been done here in case it
        affects the use of sockets in other installed django applications.
        
        New code which calls this method directly must use the decorator
        ``yarr.decorators.with_socket_timeout`` to avoid blocking requests.
        
        For this reason, and the fact that it could take a relatively long time
        to parse a feed, this method should never be called as a direct result
        of a web request.
        
        Note: after this is called, feed unread and total count caches will be
        incorrect, and must be recalculated with the appropriate management
        commands.
        """
        # Call _do_check and save if anything has changed
        changed = self._do_check(force, read, logfile)
        if changed:
            self.save()
        
        # Remove expired entries
        self.entries.filter(expires__lte=datetime.datetime.now()).delete()
        
    def _do_check(self, force, read, logfile):
        """
        Perform the actual check from ``check``
        
        Takes the same arguments as ``check``, but returns True if something
        in the Feed object has changed, and False if it has not.
        """
        # Ensure logfile is valid
        if logfile is None:
            logfile = nullfile
        
        # Report
        logfile.write("[%s] %s" % (self.pk, self.feed_url))
        
        # Check it's due for a check before the next poll
        now = datetime.datetime.now()
        next_poll = now + datetime.timedelta(minutes=settings.MINIMUM_INTERVAL)
        if (
            not force
            and self.next_check is not None
            and self.next_check >= next_poll
        ):
            logfile.write('Not due yet')
            # Return False, because nothing has changed yet
            return False
        
        # We're about to check, update the counters
        self.last_checked = now
        self.next_check = now + datetime.timedelta(
            minutes=self.check_frequency or settings.FREQUENCY,
        )
        # Note: from now on always return True, because something has changed
        
        # Fetch feed
        logfile.write('Fetching...')
        try:
            feed, entries = self._fetch_feed()
        except FeedError, e:
            logfile.write('Error: %s' % e)
                
            # Update model to reflect the error
            if isinstance(e, InactiveFeedError):
                logfile.write('Deactivating feed')
                self.is_active = False
            self.error = str(e)
            
            # Check for a valid feed despite error
            if e.feed is None or len(e.entries) == 0:
                logfile.write('No valid feed')
                return True
            logfile.write('Valid feed found')
            feed = e.feed
            entries = e.entries
            
        else:
            # Success
            logfile.write('Feed fetched')
                
            # Clear error if necessary
            if self.error != '':
                self.error = ''
        
        # Try to find the updated time
        updated = feed.get(
            'updated_parsed',
            feed.get('published_parsed', None),
        ) 
        if updated:
            updated = datetime.datetime.fromtimestamp(
                time.mktime(updated)
            )
        
        # Stop if we now know it hasn't updated recently
        if (
            not force
            and updated
            and self.last_updated
            and updated <= self.last_updated
        ):
            logfile.write('Has not updated')
            return True
            
        # Add or update any entries, and get latest timestamp
        try:
            latest = self._update_entries(entries, read)
        except EntryError, e:
            if self.error:
                self.error += '. '
            self.error += "Entry error: %s" % e
            return True
        
        # Update last_updated
        if not updated:
            # If no feed pub date found, use latest entry
            updated = latest
        self.last_updated = updated
            
        # Update feed fields
        title = feed.get('title', None)
        site_url = feed.get('link', None)
        if title:
            self.title = title
        if site_url:
            self.site_url = site_url
        
        logfile.write('Feed updated')
        
        return True
    
    def _update_entries(self, entries, read):
        """
        Add or update feedparser entries, and return latest timestamp
        """
        latest = None
        found = []
        for raw_entry in entries:
            # Create Entry and set feed
            entry = Entry.objects.from_feedparser(raw_entry)
            
            entry.feed = self
            entry.state = ENTRY_READ if read else ENTRY_UNREAD
            
            # Try to match by guid, then link, then title and date
            if entry.guid:
                query = {
                    'guid': entry.guid,
                }
            elif entry.url:
                query = {
                    'url': entry.url,
                }
            elif entry.title and entry.date:
                # If title and date provided, this will match
                query = {
                    'title':    entry.title,
                    'date':     entry.date,
                }
            else:
                # No guid, no link, no title and date - no way to match
                # Can never de-dupe this entry, so to avoid the risk of adding
                # it more than once, declare this feed invalid
                raise EntryError(
                    'No guid, link, and title or date; cannot import'
                )
                
            # Update existing, or delete old
            try:
                existing = self.entries.get(**query)
            except self.entries.model.DoesNotExist:
                # New entry, save
                entry.save()
            else:
                # Existing entry
                if entry.date is not None and entry.date > existing.date:
                    # Changes - update entry
                    existing.update(entry)
            
            # Note that we found this
            found.append(entry.pk)
            
            # Update latest tracker
            if latest is None or (
                entry.date is not None and entry.date > latest
            ):
                latest = entry.date
        
        # Mark entries for expiry if:
        #   ITEM_EXPIRY is set to expire entries
        #   they weren't found in the feed
        #   they have been read (excludes those saved)
        if settings.ITEM_EXPIRY >= 0:
            self.entries.exclude(pk__in=found).read().set_expiry()
            
        return latest
    
    class Meta:
        ordering = ('title', 'added',)



###############################################################################
#                                                               Entry model

class Entry(models.Model):
    """
    A cached entry
    
    If creating from a feedparser entry, use Entry.objects.from_feedparser()
    
    # ++ TODO: tags
    To add tags for an entry before saving, add them to _tags, and they will be
    set by save().
    """
    # Internal fields
    feed = models.ForeignKey(Feed, related_name='entries')
    state = models.IntegerField(default=ENTRY_UNREAD, choices=(
        (ENTRY_UNREAD,  'Unread'),
        (ENTRY_READ,    'Read'),
        (ENTRY_SAVED,   'Saved'),
    ))
    expires = models.DateTimeField(
        blank=True, null=True, help_text="When the entry should expire",
    )
    
    # Compulsory data fields
    title = models.TextField(blank=True)
    content = models.TextField(blank=True)
    date = models.DateTimeField(
        help_text="When this entry says it was published",
    )
    
    # Optional data fields
    author = models.TextField(blank=True)
    url = models.TextField(
        blank=True,
        validators=[URLValidator()],
        help_text="URL for the HTML for this entry",
    )
    
    comments_url = models.TextField(
        blank=True,
        validators=[URLValidator()],
        help_text="URL for HTML comment submission page",
    )
    guid = models.TextField(
        blank=True,
        help_text="GUID for the entry, according to the feed",
    )
    
    # ++ TODO: tags
    
    objects = managers.EntryManager()
    
    def __unicode__(self):
        return self.title
        
    def update(self, entry):
        """
        An old entry has been re-published; update with new data
        """
        fields = [
            'title', 'content', 'date', 'author', 'url', 'comments_url',
            'guid',
        ]
        for field in fields:
            setattr(self, field, getattr(entry, field))
        # ++ Should we mark as unread? Leaving it as is for now.
        self.save()
        
    def save(self, *args, **kwargs):
        # Default the date
        if self.date is None:
            self.date = datetime.datetime.now()
        
        # Save
        super(Entry, self).save(*args, **kwargs)
        
        # ++ TODO: tags
        """
        # Add any tags
        if hasattr(self, '_tags'):
            self.tags = self._tags
            delattr(self, '_tags')
        """
        
    class Meta:
        ordering = ('-date',)
        verbose_name_plural = 'entries'

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

import bleach


#
# To manage the web interface
#

# Page to open at Yarr root url (resolved using reverse)
HOME = getattr(settings, 'YARR_HOME', 'yarr-list_unread')

# Pagination limits
PAGE_LENGTH = getattr(settings, 'YARR_PAGE_LENGTH', 25)
API_PAGE_LENGTH = getattr(settings, 'YARR_API_PAGE_LENGTH', 5)

# If true, fix the layout elements at the top of the screen when scrolling down
# Disable if using a custom layout
LAYOUT_FIXED = getattr(settings, 'YARR_LAYOUT_FIXED', True)

# If true, add jQuery to the page when required
ADD_JQUERY = getattr(settings, 'YARR_ADD_JQUERY', True)

# Template string for document title (shown on the browser window and tabs).
# If set, used to update the title when changing feeds in list view.
# Use ``%(feed)s`` as a placeholder for the feed title (case sensitive)
TITLE_TEMPLATE = getattr(settings, 'YARR_TITLE_TEMPLATE', '%(feed)s') or ''

# jQuery Selector for page title (an element in your page template)
# If set, this element's content will be replaced with the feed title when
# changing feeds in list view.
TITLE_SELECTOR = getattr(settings, 'YARR_TITLE_SELECTOR', '') or ''


#
# To control feed updates
#

# Socket timeout, in seconds
# Highly recommended that this is **not** set to ``None``, which would block
# Note: this sets the global socket timeout, which is not thread-safe; it is
# therefore set explicitly when checking feeds, and reset after feeds have been
# updated (see ``yarr.decorators.with_socket_timeout`` for more details).
SOCKET_TIMEOUT = getattr(settings, 'YARR_SOCKET_TIMEOUT', 15)

# Minimum and maximum interval for checking a feed, in minutes
# The minimum interval must match the interval that the cron job runs at,
# otherwise some feeds may not get checked on time
MINIMUM_INTERVAL = getattr(settings, 'YARR_MINIMUM_INTERVAL', 60)
MAXIMUM_INTERVAL = getattr(settings, 'YARR_MAXIMUM_INTERVAL', 24 * 60)

# Default frequency to check a feed, in minutes
# Defaults to just under 24 hours (23:45) to avoid issues with slow responses
# Note: this will be removed in a future version
FREQUENCY = getattr(settings, 'YARR_FREQUENCY', 24 * 60)

# Number of days to keep a read item which is no longer in the feed
# Set this to 0 to expire immediately, -1 to never expire
ITEM_EXPIRY = getattr(settings, 'YARR_ITEM_EXPIRY', 1)


#
# Bleach settings for Yarr
#

# HTML whitelist for bleach
# This default list is roughly the same as the WHATWG sanitization rules
# <http://wiki.whatwg.org/wiki/Sanitization_rules>, but without form elements.
# A few common HTML 5 elements have been added as well.
ALLOWED_TAGS = getattr(
    settings, 'YARR_ALLOWED_TAGS',
    [
        'a',
        'abbr',
        'acronym',
        'aside',
        'b',
        'bdi',
        'bdo',
        'blockquote',
        'br',
        'code',
        'data',
        'dd',
        'del',
        'dfn',
        'div',  # Why not?
        'dl',
        'dt',
        'em',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'hr',
        'i',
        'img',
        'ins',
        'kbd',
        'li',
        'ol',
        'p',
        'pre',
        'q',
        's',
        'samp',
        'small',  # Now a semantic tag in HTML5!
        'span',
        'strike',
        'strong',
        'sub', 'sup',
        'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr',
        'time',
        'tt',  # Obsolete, but docutils likes to generate these.
        'u',
        'var',
        'wbr',
        'ul',
    ]
)
ALLOWED_ATTRIBUTES = getattr(
    settings, 'YARR_ALLOWED_ATTRIBUTES',
    {
        '*':        ['lang', 'dir'],  # lang is necessary for hyphentation.
        'a':        ['href', 'title'],
        'abbr':     ['title'],
        'acronym':  ['title'],
        'data':     ['value'],
        'dfn':      ['title'],
        'img':      ['src', 'alt', 'width', 'height', 'title'],
        'li':       ['value'],
        'ol':       ['reversed', 'start', 'type'],
        'td':       ['align', 'valign', 'width', 'colspan', 'rowspan'],
        'th':       ['align', 'valign', 'width', 'colspan', 'rowspan'],
        'time':     ['datetime'],
    }
)
ALLOWED_STYLES = getattr(
    settings, 'YARR_ALLOWED_STYLES', bleach.ALLOWED_STYLES,
)

########NEW FILE########
__FILENAME__ = opml
import difflib
from xml.dom import minidom
from xml.etree import ElementTree

from django.contrib.auth.models import User
from django.test import TestCase

from yarr.utils import export_opml


class ExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'test', 'test@example.com', 'test',
        )

    def test_empty(self):
        """
        An empty OPML document is generated for a user with no feeds.
        """
        expected = (
            '<opml version="1.0">'
                '<head>'
                    '<title>test subscriptions</title>'
                '</head>'
                '<body/>'
            '</opml>'
        )
        self.assert_equal_xml(expected, export_opml(self.user))

    def test_single_feed(self):
        self.user.feed_set.create(title=u'Feed 1',
                                  feed_url='http://example.com/feed.xml')
        expected = (
            '<opml version="1.0">'
                '<head>'
                    '<title>test subscriptions</title>'
                '</head>'
                '<body>'
                    '<outline type="rss" xmlUrl="http://example.com/feed.xml"'
                        ' title="Feed 1" text="Feed 1" />'
                '</body>'
            '</opml>'
        )
        self.assert_equal_xml(expected, export_opml(self.user))

    def test_unicode_title(self):
        self.user.feed_set.create(title=u'\u2042',
                                  feed_url='http://example.com/feed.xml')
        expected = (
            u'<opml version="1.0">'
                '<head>'
                    '<title>test subscriptions</title>'
                '</head>'
                '<body>'
                    '<outline type="rss" xmlUrl="http://example.com/feed.xml"'
                        u' title="\u2042" text="\u2042" />'
                '</body>'
            '</opml>'
        ).encode('utf-8')
        self.assert_equal_xml(expected, export_opml(self.user))

    def test_site_url(self):
        self.user.feed_set.create(title=u'Example',
                                  feed_url='http://example.com/feed.xml',
                                  site_url='http://example.com/')
        expected = (
            '<opml version="1.0">'
                '<head>'
                    '<title>test subscriptions</title>'
                '</head>'
                '<body>'
                    '<outline type="rss" xmlUrl="http://example.com/feed.xml"'
                        ' htmlUrl="http://example.com/"'
                        ' title="Example" text="Example" />'
                '</body>'
            '</opml>'
        )
        self.assert_equal_xml(expected, export_opml(self.user))

    def assert_equal_xml(self, a, b):
        """
        Poor man's XML differ.
        """
        a_el = ElementTree.fromstring(a)
        b_el = ElementTree.fromstring(b)
        if not etree_equal(a_el, b_el):
            a_str = pretty_etree(a_el).splitlines()
            b_str = pretty_etree(b_el).splitlines()
            diff = difflib.unified_diff(a_str, b_str, fromfile='a', tofile='b')
            full_diff = u'\n'.join(diff).encode('utf-8')
            self.fail('XML not equivalent:\n\n{}'.format(full_diff))


def pretty_etree(e):
    s = ElementTree.tostring(e, 'utf-8')
    return minidom.parseString(s).toprettyxml(indent="    ")


def etree_equal(a, b):
    """
    Determine whether two :class:`xml.etree.ElementTree.Element` trees are
    equivalent.

    >>> from xml.etree.ElementTree import Element, SubElement as SE, fromstring
    >>> a = fromstring('<root/>')
    >>> b = fromstring('<root/>')
    >>> etree_equal(a, a), etree_equal(a, b)
    (True, True)
    >>> c = fromstring('<root attrib="value" />')
    >>> d = fromstring('<root attrib="value" />')
    >>> etree_equal(a, c), etree_equal(c, d)
    (False, True)
    """
    return (a.tag == b.tag
            and a.text == b.text
            and a.tail == b.tail
            and a.attrib == b.attrib
            and len(a) == len(b)
            and all(etree_equal(x, y) for (x, y) in zip(a, b)))

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls.defaults import patterns, url
except ImportError:
    from django.conf.urls import patterns, url

from yarr.constants import ENTRY_UNREAD, ENTRY_READ, ENTRY_SAVED

urlpatterns = patterns('yarr.views',
    url(r'^$', 'home',
        name="yarr-home"
    ),
    url(r'^all/$', 'list_entries',
        name="yarr-list_all",
    ),
    url(r'^unread/$', 'list_entries',
        {'state': ENTRY_UNREAD},
        name="yarr-list_unread",
    ),
    url(r'^saved/$', 'list_entries',
        {'state': ENTRY_SAVED},
        name="yarr-list_saved",
    ),
    
    # Feed views
    url(r'^all/(?P<feed_pk>\d+)/$', 'list_entries',
        name="yarr-list_all",
    ),
    url(r'^unread/(?P<feed_pk>\d+)/$', 'list_entries',
        {'state': ENTRY_UNREAD},
        name="yarr-list_unread"
    ),
    url(r'^saved/(?P<feed_pk>\d+)/$', 'list_entries',
        {'state': ENTRY_SAVED},
        name="yarr-list_saved",
    ),
    
    # Feed management
    url(r'^feeds/$', 'feeds',
        name="yarr-feeds"
    ),
    url(r'^feeds/add/$', 'feed_form',
        name="yarr-feed_add",
    ),
    url(r'^feeds/(?P<feed_pk>\d+)/$', 'feed_form',
        name="yarr-feed_edit",
    ),
    url(r'^feeds/(?P<feed_pk>\d+)/delete/$', 'feed_delete',
        name="yarr-feed_delete",
    ),
    url(r'^feeds/export/$', 'feeds_export',
        name="yarr-feeds_export",
    ),

    # Flag management without javascript
    url(r'^state/read/all/$', 'entry_state',
        {'state': ENTRY_READ, 'if_state': ENTRY_UNREAD},
        name="yarr-mark_all_read",
    ),
    url(r'^state/read/feed/(?P<feed_pk>\d+)/$', 'entry_state',
        {'state': ENTRY_READ},
        name="yarr-mark_feed_read"
    ),
    url(r'^state/read/entry/(?P<entry_pk>\d+)/$', 'entry_state',
        {'state': ENTRY_READ},
        name="yarr-mark_read"
    ),
    
    url(r'^state/unread/entry/(?P<entry_pk>\d+)/$', 'entry_state',
        {'state': ENTRY_UNREAD},
        name="yarr-mark_unread",
    ),
    url(r'^state/save/entry/(?P<entry_pk>\d+)/$', 'entry_state',
        {'state': ENTRY_SAVED},
        name="yarr-mark_saved"
    ),
    
    
    #
    # JSON API
    #
    
    url(r'^api/$', 'api_base', name='yarr-api_base'),
    url(r'^api/feed/get/$', 'api_feed_get', name='yarr-api_feed_get'),
    url(r'^api/feed/pks/$', 'api_feed_pks_get', name='yarr-api_feed_pks_get'),
    url(r'^api/entry/get/$', 'api_entry_get', name='yarr-api_entry_get'),
    url(r'^api/entry/set/$', 'api_entry_set', name='yarr-api_entry_set'),
    
)


########NEW FILE########
__FILENAME__ = utils
"""
Utils for yarr
"""
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, ElementTree
from cStringIO import StringIO

from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

# ++ Can remove this try/except when Yarr's min req is Django 1.5
try:
    import json
except ImportError:
   from django.utils import simplejson as json

from yarr import settings
from yarr import models


def paginate(request, qs, adjacent_pages=3):
    """
    Paginate a querystring and prepare an object for building links in template
    Returns:
        paginated   Paginated items
        pagination  Info for template
    """
    paginator = Paginator(qs, settings.PAGE_LENGTH)
    try:
        page = int(request.GET.get('p', '1'))
    except ValueError:
        page = 1
    try:
        paginated = paginator.page(page)
    except (EmptyPage, InvalidPage):
        paginated = paginator.page(paginator.num_pages)

    # Prep pagination vars
    total_pages = paginator.num_pages
    start_page = max(paginated.number - adjacent_pages, 1)
    if start_page <= 3:
        start_page = 1

    end_page = paginated.number + adjacent_pages + 1
    if end_page >= total_pages - 1:
        end_page = total_pages + 1

    def page_dict(number):
        """
        A dictionary which describes a page of the given number.  Includes
        a version of the current querystring, replacing only the "p" parameter
        so nothing else is clobbered.
        """
        query = request.GET.copy()
        query['p'] = str(number)
        return {
            'number': number,
            'query': query.urlencode(),
            'current': number == paginated.number,
        }

    page_numbers = [
        n for n in range(start_page, end_page) if n > 0 and n <= total_pages
    ]

    if 1 not in page_numbers:
        first = page_dict(1)
    else:
        first = None

    if total_pages not in page_numbers:
        last = page_dict(total_pages)
    else:
        last = None

    pagination = {
        'has_next':     paginated.has_next(),
        'next':         page_dict(paginated.next_page_number()) if paginated.has_next() else None,

        'has_previous': paginated.has_previous(),
        'previous':     page_dict(paginated.previous_page_number()) if paginated.has_previous() else None,

        'show_first':   first is not None,
        'first':        first,
        'pages':        [page_dict(n) for n in page_numbers],
        'show_last':    last is not None,
        'last':         last,
    }

    return paginated, pagination


def jsonEncode(data):
    return json.dumps(data, cls=DjangoJSONEncoder)

def jsonResponse(data):
    """
    Return a JSON HttpResponse
    """
    return HttpResponse(jsonEncode(data), mimetype='application/json')

def import_opml(file_path, user, purge=False):
    if purge:
        models.Feed.objects.filter(user=user).delete()

    xmldoc = minidom.parse(file_path)

    new = []
    existing = []
    for node in xmldoc.getElementsByTagName('outline'):
        url_node = node.attributes.get('xmlUrl', None)
        if url_node is None:
            continue
        url = url_node.value

        title_node = node.attributes.get('title', None)
        title = title_node.value if title_node else url
        site_node = node.attributes.get('htmlUrl', None)
        site_url = site_node.value if site_node else ''

        try:
            feed = models.Feed.objects.get(
                title=title,
                feed_url=url,
                site_url=site_url,
                user=user
            )
            existing.append(feed)
        except ObjectDoesNotExist:
            feed = models.Feed(
                title=title,
                feed_url=url,
                site_url=site_url,
                user=user
            )
            new.append(feed)

    models.Feed.objects.bulk_create(new)
    return len(new), len(existing)


def export_opml(user):
    """
    Generate a minimal OPML export of the user's feeds.

    :param user: Django User object
    :param stream: writable file-like object to which the XML is written
    """
    root = Element('opml', {'version': '1.0'})

    head = SubElement(root, 'head')
    title = SubElement(head, 'title')
    title.text = u'{0} subscriptions'.format(user.username)

    body = SubElement(root, 'body')

    for feed in user.feed_set.all():
        item = SubElement(body, 'outline', {
            'type': 'rss',
            'text': feed.title,
            'title': feed.title,
            'xmlUrl': feed.feed_url,
        })
        if feed.site_url:
            item.set('htmlUrl', feed.site_url)

    buf = StringIO()
    ElementTree(root).write(buf, encoding="UTF-8")
    return buf.getvalue()

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import models as django_models
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template import loader, Context
from django.utils.html import escape

from yarr import constants, settings, utils, models, forms
from yarr.constants import (
    ENTRY_UNREAD, ENTRY_READ, ENTRY_SAVED, ORDER_ASC, ORDER_DESC,
)


@login_required
def home(request):
    if settings.HOME == 'yarr-home':
        raise Http404
    return HttpResponseRedirect(reverse(settings.HOME))


def get_entries(request, feed_pk, state):
    """
    Internal function to filter the entries
    """
    # Start building querystring
    qs = models.Entry.objects.select_related()
    
    # Look up feed
    feed = None
    if feed_pk is None:
        qs = qs.filter(feed__user=request.user)
    else:
        feed = get_object_or_404(models.Feed, pk=feed_pk, user=request.user)
        qs = qs.filter(feed=feed)
        
    # Filter further
    if state == ENTRY_UNREAD:
        qs = qs.unread()
    elif state == ENTRY_READ:
        qs = qs.read()
    elif state == ENTRY_SAVED:
        qs = qs.saved()
        
    return qs, feed
    
@login_required
def list_entries(
    request, feed_pk=None, state=None, template="yarr/list_entries.html",
):
    """
    Display a list of entries
    Takes optional arguments to determine which entries to list:
        feed_pk     Primary key for a Feed
        state       The state of entries to list; one of:
                    None            All entries
                    ENTRY_UNREAD    Unread entries
                    ENTRY_SAVED     Saved entries

    Takes a single querystring argument:
        order       If "asc", order chronologically (otherwise
                    reverse-chronologically).

    Note: no built-in url calls this with state == ENTRY_READ, but support
    exists for a custom url.
    """
    # Get entries queryset
    qs, feed = get_entries(request, feed_pk, state)
    
    order = request.GET.get('order', ORDER_DESC)
    if order == ORDER_ASC:
        qs = qs.order_by('date')
    else:
        qs = qs.order_by('-date')

    # Make list of available pks for this page
    available_pks = list(qs.values_list('pk', flat=True))
    
    # Paginate
    entries, pagination = utils.paginate(request, qs)
    
    # Base title
    if state is None:
        title = 'All items'
    elif state == ENTRY_UNREAD:
        title = 'Unread items'
    elif state == ENTRY_SAVED:
        title = 'Saved items'
    else:
        raise ValueError('Cannot list entries in unknown state')
        
    # Add tag feed to title
    if feed:
        title = '%s - %s' % (feed.title, title)
    
    # Get list of feeds for feed list
    feeds = models.Feed.objects.filter(user=request.user)
    
    # Determine current view for reverse
    if state is None:
        current_view = 'yarr-list_all'
    elif state == ENTRY_UNREAD:
        current_view = 'yarr-list_unread'
    elif state == ENTRY_SAVED:
        current_view = 'yarr-list_saved'
    
    return render(request, template, {
        'title':    title,
        'entries':  entries,
        'pagination': pagination,
        'feed':     feed,
        'feeds':    feeds,
        'state':    state,
        'order_asc':    order == ORDER_ASC,
        'constants':    constants,
        'current_view': current_view,
        'yarr_settings': {
            'add_jquery':       settings.ADD_JQUERY,
            # JavaScript YARR_CONFIG variables
            'config':   utils.jsonEncode({
                'api':  reverse('yarr-api_base'),
                'con':  '#yarr_con',
                'initial_state':    state,
                'initial_order':    order,
                'initial_feed':     feed_pk,
                'layout_fixed':     settings.LAYOUT_FIXED,
                'api_page_length':  settings.API_PAGE_LENGTH,
                'title_template':   settings.TITLE_TEMPLATE,
                'title_selector':   settings.TITLE_SELECTOR,
                'available_pks':    available_pks,
                'url_all': {
                    None:           reverse('yarr-list_all'),
                    ENTRY_UNREAD:   reverse('yarr-list_unread'),
                    ENTRY_SAVED:    reverse('yarr-list_saved'),
                },
                'url_feed': {
                    None:           reverse('yarr-list_all', kwargs={'feed_pk':'00'}),
                    ENTRY_UNREAD:   reverse('yarr-list_unread', kwargs={'feed_pk':'00'}),
                    ENTRY_SAVED:    reverse('yarr-list_saved', kwargs={'feed_pk':'00'}),
                }
            }),
        },
    })
    
    
@login_required
def entry_state(
    request, feed_pk=None, entry_pk=None, state=None, if_state=None,
    template="yarr/confirm.html",
):
    """
    Change entry state for an entry, a feed, or all entries
    """
    # Filter entries by selection
    qs = models.Entry.objects.user(request.user)
    if entry_pk is not None:
        # Changing specific entry
        qs = qs.filter(pk=entry_pk)
        
    elif state == ENTRY_READ:
        if feed_pk is not None:
            # Changing all entries in a feed
            qs = qs.filter(feed__pk=feed_pk)
            
        # Only mark unread as read - don't change saved
        qs = qs.unread()
        
    else:
        # Either unknown state, or trying to bulk unread/save
        messages.error(request, 'Cannot perform this operation')
        return HttpResponseRedirect(reverse(home))
        
    # Check for if_state
    if if_state is not None:
        if if_state == ENTRY_UNREAD:
            qs = qs.unread()
        elif if_state == ENTRY_READ:
            qs = qs.read()
        elif if_state == ENTRY_SAVED:
            qs = qs.saved()
        else:
            messages.error(request, 'Unknown condition')
            return HttpResponseRedirect(reverse(home))
        
    # Check there's something to change
    count = qs.count()
    if count == 0:
        messages.error(request, 'No entries found to change')
        return HttpResponseRedirect(reverse(home))
    
    # Process
    if request.POST:
        # Change state and update unread count
        qs.set_state(state)
        
        # If they're not marked as read, they can't ever expire
        # If they're marked as read, they will be given an expiry date
        # when Feed._update_entries determines they can expire
        if state != ENTRY_READ:
            qs.clear_expiry()
        
        if state is ENTRY_UNREAD:
            messages.success(request, 'Marked as unread')
        elif state is ENTRY_READ:
            messages.success(request, 'Marked as read')
        elif state is ENTRY_SAVED:
            messages.success(request, 'Saved')
        return HttpResponseRedirect(reverse(home))
    
    # Prep messages
    op_text = {
        'verb': 'mark',
        'desc': '',
    }
    if state is ENTRY_UNREAD:
        op_text['desc'] = ' as unread'
    elif state is ENTRY_READ:
        op_text['desc'] = ' as read'
    elif state is ENTRY_SAVED:
        op_text['verb'] = 'save'
        
    if entry_pk:
        title = '%(verb)s item%(desc)s'
        msg = 'Are you sure you want to %(verb)s this item%(desc)s?'
    elif feed_pk:
        title = '%(verb)s feed%(desc)s'
        msg = 'Are you sure you want to %(verb)s all items in the feed%(desc)s?'
    else:
        title = '%(verb)s all items%(desc)s'
        msg = 'Are you sure you want to %(verb)s all items in every feed%(desc)s?'
    
    title = title % op_text
    title = title[0].upper() + title[1:]
    
    return render(request, template, {
        'title':    title,
        'message':  msg % op_text,
        'submit_label': title,
    })
    

    
@login_required
def feeds(request, template="yarr/feeds.html"):
    """
    Mark entries as saved
    Arguments:
        entry_pk    Primary key for an Entry (required)
        is_saved    If True, mark as saved
                    If False, unmark as saved
    """
    # Get list of feeds for feed list
    feeds = models.Feed.objects.filter(user=request.user)
    
    add_form = forms.AddFeedForm()
    
    return render(request, template, {
        'title':    'Manage feeds',
        'feed_form': add_form,
        'feeds':    feeds,
        'yarr_settings': {
            'add_jquery':       settings.ADD_JQUERY,
            # JavaScript YARR_CONFIG variables
            'config':   utils.jsonEncode({
                'api':  reverse('yarr-api_base'),
            }),
        },
    })
    

@login_required
def feed_form(
    request, feed_pk=None, template_add="yarr/feed_add.html",
    template_edit="yarr/feed_edit.html", success_url=None,
):
    """
    Add or edit a feed
    """
    # Detect whether it's add or edit
    if feed_pk is None:
        is_add = True
        form_class = forms.AddFeedForm
        feed = models.Feed()
        title = "Add feed"
        template = template_add
    else:
        is_add = False
        form_class = forms.EditFeedForm
        feed = get_object_or_404(models.Feed, user=request.user, pk=feed_pk)
        title = "Edit feed"
        template = template_edit
    
    # Process request
    if request.POST:
        feed_form = form_class(request.POST, instance=feed)
        
        if feed_form.is_valid():
            # Save changes
            if is_add:
                # Save feed
                # ++ Really we would like to get the feed at this point, to
                # ++ fill out the name and other feed details, and grab initial
                # ++ entries. However, feedparser isn't thread-safe yet, so for
                # ++ now we just have to wait for the next scheduled check
                feed = feed_form.save(commit=False)
                feed.title = feed.feed_url
                feed.user = request.user
                feed.save()
            else:
                feed = feed_form.save()
            
            # Report and redirect
            if success_url is None:
                messages.success(
                    request,
                    'Feed added.' if is_add else 'Changes saved',
                )
            return HttpResponseRedirect(
                reverse('yarr-feeds') if success_url is None else success_url
            )
    elif 'feed_url' in request.GET:
        feed_form = form_class(request.GET, instance=feed)
    else:
        feed_form = form_class(instance=feed)
    
    return render(request, template, {
        'title':    title,
        'feed_form': feed_form,
        'feed':     feed,
    })
    
    
@login_required
def feed_delete(request, feed_pk, template="yarr/confirm.html"):
    """
    Delete a feed (and its entries)
    Arguments:
        feed_pk     Primary key for the Feed (required)
    """
    # Look up entry
    feed = get_object_or_404(models.Feed, pk=feed_pk, user=request.user)
    
    # Update entry
    if request.POST:
        feed.delete()
        messages.success(request, 'Feed deleted')
        return HttpResponseRedirect(reverse(home))
    
    return render(request, template, {
        'title':    'Delete feed',
        'message':  'Are you sure you want to delete the feed "%s"?' % feed.title,
        'submit_label': 'Delete feed',
    })


@login_required
def feeds_export(request):
    """
    Export the user's feed list as OPML.
    """
    response = HttpResponse(
        utils.export_opml(request.user),
        mimetype='application/xml',
    )
    response['Content-Disposition'] = 'attachment; filename="feeds.opml"'
    return response


@login_required
def api_base(request):
    """
    Base API URL
    Currently just used to reverse for JavaScript
    """
    raise Http404


@login_required
def api_feed_get(request):
    """
    JSON API to get feed data
    
    Arguments passed on GET:
        feed_pks    List of feeds to get information about
        fields      List of model fields to get
                    If not provided, returns all fields
                    Excluded fields: id, user, all related fields
                    The pk (id) is provided as the key
    
    Returns in JSON format:
        success     Boolean indicating success
        feeds       Object with feed pk as key, feed data as object in value
    """
    # Get feeds queryset
    pks = request.GET.get('feed_pks', '')
    if pks:
        success = True
        feeds = models.Feed.objects.filter(
            user=request.user, pk__in=pks.split(','),
        )
    else:
        success = False
        feeds = models.Feed.objects.none()
    
    # Get safe list of attributes
    fields_available = [
        field.name for field in models.Feed._meta.fields
        if field.name not in [
            'id', 'user'
        ]
    ]
    fields_request = request.GET.get('fields', '')
    if fields_request:
        fields = [
            field_name for field_name in fields_request.split(',')
            if field_name in fields_available
        ]
    else:
        fields = fields_available
    
    # Prep list of safe fields which don't need to be escaped
    safe_fields = [
        field.name for field in models.Feed._meta.fields if (
            field.name in fields
            and isinstance(field, (
                django_models.DateTimeField,
                django_models.IntegerField,
            ))
        )
    ]
    
    # Get data
    data = {}
    for feed in feeds.values('pk', *fields):
        # Escape values as necessary, and add to the response dict under the pk
        data[feed.pop('pk')] = dict([
            (key, val if key in safe_fields else escape(val))
            for key, val in feed.items()
        ])
    
    # Respond
    return utils.jsonResponse({
        'success':  success,
        'feeds':    data,
    })
    
    
@login_required
def api_feed_pks_get(request):
    """
    JSON API to get entry pks for given feeds
    
    Arguments passed on GET:
        feed_pks    List of feeds to get entry pks for about
                    If none, returns entry pks for all feeds
        state       The state of entries to read
        order       The order to sort entries in
                    Defaults to ORDER_DESC
    
    Returns in JSON format:
        success     Boolean indicating success
        pks         Object with feed pk as key, list of entry pks as list value
        feed_unread Unread counts as dict, { feed.pk: feed.count_unread, ... }
    """
    feed_pks = request.GET.get('feed_pks', '')
    state = GET_state(request, 'state')
    order = request.GET.get('order', ORDER_DESC)
    
    # Get entries queryset, filtered by user and feed
    entries = models.Entry.objects.filter(feed__user=request.user)
    if feed_pks:
        try:
            entries = entries.filter(feed__pk__in=feed_pks.split(','))
        except Exception:
            return utils.jsonResponse({
                'success':  False,
                'msg':      'Invalid request',
            })
    
    # Filter by state
    if state == ENTRY_UNREAD:
        entries = entries.unread()
    elif state == ENTRY_READ:
        entries = entries.read()
    elif state == ENTRY_SAVED:
        entries = entries.saved()
    
    # Order them
    if order == ORDER_ASC:
        entries = entries.order_by('date')
    else:
        entries = entries.order_by('-date')
    
    # Get a list of remaining pks
    pks = list(entries.values_list('pk', flat=True))
    
    # Get unread counts for feeds in this response
    feed_unread = {}
    for feed in entries.feeds():
        feed_unread[str(feed.pk)] = feed.count_unread
        
    # Respond
    return utils.jsonResponse({
        'success':  True,
        'pks':      pks,
        'feed_unread': feed_unread,
    })
        
    
@login_required
def api_entry_get(request, template="yarr/include/entry.html"):
    """
    JSON API to get entry data
    
    Arguments passed on GET:
        entry_pks   List of entries to get
        order       Order to send them back in
                    Defaults to ORDER_DESC
        
    Returns in JSON format:
        success     Boolean indicating success
        entries     List of entries, rendered entry as object in value:
                    html    Entry rendered as HTML using template
    """
    pks = request.GET.get('entry_pks', '')
    order = request.GET.get('order', ORDER_DESC)
    
    # Get entries queryset
    if pks:
        success = True
        entries = models.Entry.objects.filter(
            feed__user=request.user, pk__in=pks.split(','),
        )
    else:
        success = False
        entries = models.Entry.objects.none()
    
    # Order them
    if order == ORDER_ASC:
        entries = entries.order_by('date')
    else:
        entries = entries.order_by('-date')
    
    # Render
    data = []
    compiled = loader.get_template(template)
    for entry in entries:
        data.append({
            'pk':       entry.pk,
            'feed':     entry.feed_id,
            'state':    entry.state,
            'html':     compiled.render(Context({
                'constants':    constants,
                'entry':        entry,
            }))
        })
    
    # Respond
    return utils.jsonResponse({
        'success':  success,
        'entries':  data,
    })
    

def GET_state(request, param):
    """
    Return an entry state constant or None
    """
    state = request.GET.get(param, '')
    if state == '':
        return None
    return int(state)

@login_required
def api_entry_set(request):
    """
    JSON API to set entry data
    
    Arguments passed on GET:
        entry_pks   List of entries to update
        state       New state
    
    Returns in JSON format:
        success     Boolean
        msg         Error message, if success == False
        feed_unread Unread counts as dict, { feed.pk: feed.count_unread, ... }
    """
    # Start assuming success
    success = True
    msg = ''
    feed_unread = {}
    
    # Get entries queryset
    pks = request.GET.get('entry_pks', '')
    if pks:
        pks = pks.split(',')
        entries = models.Entry.objects.filter(
            feed__user=request.user, pk__in=pks,
        )
    else:
        success = False
        msg = 'No entries found'
    
    
    # Check for if_state
    if_state = GET_state(request, 'if_state')
    if success and if_state is not None:
        if_state = int(if_state)
        if if_state == ENTRY_UNREAD:
            entries = entries.unread()
        elif if_state == ENTRY_READ:
            entries = entries.read()
        elif if_state == ENTRY_SAVED:
            entries = entries.saved()
        else:
            success = False
            msg = 'Unknown condition'
            
    
    # Update new state
    state = GET_state(request, 'state')
    if success:
        if state in (ENTRY_UNREAD, ENTRY_READ, ENTRY_SAVED):
            # Change state and get updated unread count
            feed_unread = entries.set_state(state, count_unread=True)
            
            # If they're not marked as read, they can't ever expire
            # If they're marked as read, they will be given an expiry date
            # when Feed._update_entries determines they can expire
            if state != ENTRY_READ:
                entries.clear_expiry()
            
            # Decide message
            if state == ENTRY_UNREAD:
                msg = 'Marked as unread'
            elif state == ENTRY_READ:
                msg = 'Marked as read'
            elif state == ENTRY_SAVED:
                msg = 'Saved'
    
        else:
            success = False
            msg = 'Unknown operation'
        
    # Respond
    return utils.jsonResponse({
        'success':  success,
        'msg':      msg,
        'feed_unread': feed_unread,
    })

########NEW FILE########
