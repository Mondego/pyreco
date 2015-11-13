__FILENAME__ = admin
from django.contrib import admin
from django.db.models import Q

from flother.apps.blog.models import Entry


class EntryAdmin(admin.ModelAdmin):

    """
    Class for specifiying the options for administering the
    flother.apps.blog.models.Entry model via the Django admin.
    """

    date_hierarchy = 'published_at'
    exclude = ('copy_html',)
    list_display = ('title', 'author', 'published_at', 'status', 'allow_new_comment')
    list_filter = ('published_at', 'author', 'status')
    prepopulated_fields = {'slug': ('title',)}
    radio_fields = {'status': admin.HORIZONTAL}
    search_fields = ('title', 'standfirst', 'copy')

    class Media:
        css = {
            'all': ('apps/files/css/files.css',),
        }
        js = (
            'core/js/jquery.js', 'apps/files/js/fancyzoom/fancyzoom.js',
            'apps/files/js/fieldselection.js', 'apps/files/js/files.js'
        )

    def queryset(self, request):
        """
        Return the queryset to use in the admin list view.  Superusers
        can see all entries, other users can see all their own entries
        and all entries by other authors with a status other than
        private.
        """
        if request.user.is_superuser:
            return Entry.objects.all()
        return Entry.objects.filter(
            Q(author=request.user) | Q(status=Entry.DRAFT_STATUS))


admin.site.register(Entry, EntryAdmin)

########NEW FILE########
__FILENAME__ = context_processors
from flother.apps.blog.models import Entry


def latest_entries(request):
    """Return the three latest published entries."""
    return {
        'latest_entries': Entry.objects.published()[:3]
    }

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.sites.models import Site
from django.contrib.syndication.feeds import Feed
from django.core.urlresolvers import reverse
from django.utils.feedgenerator import Atom1Feed

from flother.apps.blog.models import Entry


site = Site.objects.get_current()


class LatestEntries(Feed):
    """An Atom 1.0 feed of the latest ten public entries from the blog."""

    feed_type = Atom1Feed
    title = u'%s: latest entries' % site.name
    subtitle = 'More than a hapax legomenon.'
    title_template = 'feeds/latest_title.html'
    description_template = 'feeds/latest_description.html'

    def link(self):
        from flother.apps.blog.views import entry_index
        return reverse(entry_index)

    def items(self):
        return Entry.objects.published().select_related()[:10]

    def item_author_name(self, item):
        return item.author.first_name or item.author.username

    def item_pubdate(self, item):
        return item.published_at

########NEW FILE########
__FILENAME__ = publishnewentries
import datetime

from django.core.management.base import NoArgsCommand

from flother.apps.blog.models import Entry
from flother.apps.blog.signals import delete_blog_index


class Command(NoArgsCommand):

    """
    Because the site is heavily cached (it's served as static HTML
    files), any entry published in the future will only actually appear
    once the cache is flushed, not once its publishing date has passed.
    To ensure the entry appears as expected, this command will check for
    entries whose ``published_at`` field is within the last hour.  If
    there are any, the cache will be cleared.

    This command should be run as an hourly cron job.
    """

    help = "Clears the cache if any entries were published within the last hour."

    def handle_noargs(self, **options):
        """
        Delete the cache for any blog entries published within the last
        hour.
        """
        verbosity = int(options.get('verbosity', 1))

        one_hour_ago = datetime.datetime.now() - datetime.timedelta(minutes=62)
        if verbosity == 2:
            print "Looking for entries published before %s." % (
                one_hour_ago.strftime('%H:%M:%S on %d %B %Y'))
        new_entries = Entry.objects.published(published_at__gte=one_hour_ago)
        if verbosity == 2:
            print "Found %d entries." % len(new_entries)

        if new_entries:
            for entry in new_entries:
                if verbosity >= 1:
                    print "Deleting cache for entry '%s'." % entry.title
                delete_blog_index(Entry, entry)

########NEW FILE########
__FILENAME__ = managers
import datetime
from django.db.models import Manager


class EntryManager(Manager):

    """
    Django model manager for the Entry model. Overrides the default
    latest() method so it returns the latest published entry, and adds a
    published() method that returns only published entries.
    """

    def latest(self, field_name=None):
        """Return the latest published entry."""
        return self.published().latest(field_name)

    def published(self, **kwargs):
        """
        Return a QuerySet that contains only those entries deemed fit
        to publish, i.e. entries with a status of "published" and a
        created_at date earlier than now.
        """
        from flother.apps.blog.models import Entry
        return self.get_query_set().filter(status=Entry.PUBLISHED_STATUS,
            published_at__lte=datetime.datetime.now, **kwargs)

########NEW FILE########
__FILENAME__ = 0001_Entry
import django
from django.db import models
from south.db import db

from flother.apps.blog.models import Entry


class Migration:
    def forwards(self, orm):
        """Add model ``Entry``."""
        db.create_table('blog_entry', (
            ('standfirst', orm['blog.Entry:standfirst']),
            ('status', orm['blog.Entry:status']),
            ('author', orm['blog.Entry:author']),
            ('created_at', orm['blog.Entry:created_at']),
            ('title', orm['blog.Entry:title']),
            ('updated_at', orm['blog.Entry:updated_at']),
            ('id', orm['blog.Entry:id']),
            ('published_at', orm['blog.Entry:published_at']),
            ('number_of_views', orm['blog.Entry:number_of_views']),
            ('copy', orm['blog.Entry:copy']),
            ('slug', orm['blog.Entry:slug']),
        ))
        db.send_create_signal('blog', ['Entry'])

    def backwards(self, orm):
        """Delete model ``Entry``."""
        db.delete_table('blog_entry')

    models = {
        'blog.entry': {
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'copy': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True', 'blank': 'True'}),
            'number_of_views': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'standfirst': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'auth.user': {
            '_stub': True,
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['blog']

########NEW FILE########
__FILENAME__ = 0002_add_entry_enable_comments_field
import django
from django.db import models
from south.db import db

from flother.apps.blog.models import Entry


class Migration:

    """Add the field ``enable_comments`` to the ``Entry`` model."""

    def forwards(self, orm):
        """Add field ``Entry.enable_comments``."""
        db.add_column('blog_entry', 'enable_comments', orm['blog.Entry:enable_comments'])

    def backwards(self, orm):
        """Delete field ``Entry.enable_comments``."""
        db.delete_column('blog_entry', 'enable_comments')

    models = {
        'blog.entry': {
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'copy': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'enable_comments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True', 'blank': 'True'}),
            'number_of_views': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 6, 29, 14, 50, 25, 986127)'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'standfirst': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'auth.user': {
            '_stub': True,
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['blog']

########NEW FILE########
__FILENAME__ = 0003_add_tagging
from django.db import models
from south.db import db

from flother.apps.blog.models import Entry


class Migration:
    def forwards(self, orm):
        """
        Add a CharField named tags that allows the Entry model to use
        the Django Tagging app.
        """
        # Adding field 'Entry.tags'
        db.add_column('blog_entry', 'tags', models.CharField(max_length=255, default=''))

    def backwards(self, orm):
        """Remove Django Tagging support from the Entry model."""
        # Deleting field 'Entry.tags'
        db.delete_column('blog_entry', 'tags')

    models = {
        'blog.entry': {
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'copy': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'enable_comments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number_of_views': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'standfirst': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'tags': ('django.db.models.fields.CharField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['blog']

########NEW FILE########
__FILENAME__ = 0004_remove_tagging
from django.db import models
from south.db import db

from flother.apps.blog.models import Entry

class Migration:
    def forwards(self, orm):
        """Remove tagging completely."""
        db.delete_column('blog_entry', 'tags')

    def backwards(self, orm):
        """Add tagging to the blog Entry model"""
        db.add_column('blog_entry', 'tags', models.CharField(max_length=255, default=''))

    models = {
        'blog.entry': {
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'copy': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'enable_comments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number_of_views': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 25, 12, 26, 17, 391325)'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'standfirst': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 25, 12, 26, 17, 490561)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 25, 12, 26, 17, 490437)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        }
    }

    complete_apps = ['blog']

########NEW FILE########
__FILENAME__ = 0005_add_copy_html_field
from django.db import models
from south.db import db

from flother.apps.blog.models import Entry


class Migration:
    def forwards(self, orm):
        """Add field ``Entry.copy_html``."""
        db.add_column('blog_entry', 'copy_html', models.TextField(blank=True, default=''))

    def backwards(self, orm):
        """Deleting field ``Entry.copy_html``."""
        db.delete_column('blog_entry', 'copy_html')

    models = {
        'blog.entry': {
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'copy': ('django.db.models.fields.TextField', [], {}),
            'copy_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'enable_comments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number_of_views': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 25, 13, 0, 2, 933914)'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'standfirst': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 25, 13, 0, 3, 32776)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 25, 13, 0, 3, 32647)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['blog']

########NEW FILE########
__FILENAME__ = 0006_remove_number_of_views_from_entry
from django.db import models
from south.db import db

from flother.apps.blog.models import *


class Migration:
    def forwards(self, orm):
        """Delete field ``Entry.number_of_views``."""
        db.delete_column('blog_entry', 'number_of_views')

    def backwards(self, orm):
        """Add field ``Entry.number_of_views``."""
        db.add_column('blog_entry', 'number_of_views', orm['blog.entry:number_of_views'])

    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'blog.entry': {
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'copy': ('django.db.models.fields.TextField', [], {}),
            'copy_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'enable_comments': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'standfirst': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['blog']

########NEW FILE########
__FILENAME__ = models
import datetime
import unicodedata
import urllib2

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.comments.moderation import CommentModerator, moderator
from django.core.mail import mail_managers
from django.db import models
from django.db.models import permalink
from django.db.models import signals
from django.template.loader import render_to_string

from flother.apps.blog.managers import EntryManager
from flother.apps.blog.signals import delete_blog_index,\
    clear_stagnant_cache_on_comment_change
from flother.utils.akismet import Akismet


class Entry(models.Model):

    """An individual entry in the blog."""

    DRAFT_STATUS = 1
    PUBLISHED_STATUS = 2
    PRIVATE_STATUS = 3
    STATUS_CHOICES = ((DRAFT_STATUS, 'Draft'), (PUBLISHED_STATUS, 'Published'),
        (PRIVATE_STATUS, 'Private'))

    DAYS_COMMENTS_ENABLED = 30

    title = models.CharField(max_length=128)
    slug = models.SlugField(unique_for_year='published_at')
    standfirst = models.CharField(max_length=256, blank=True)
    copy = models.TextField()
    copy_html = models.TextField(blank=True)
    author = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True,
        verbose_name='date_created')
    published_at = models.DateTimeField(default=datetime.datetime.now,
        verbose_name='date published')
    updated_at = models.DateTimeField(auto_now=True,
        verbose_name='date updated')
    status = models.SmallIntegerField(choices=STATUS_CHOICES,
        default=DRAFT_STATUS)
    enable_comments = models.BooleanField(default=False)

    objects = EntryManager()

    class Meta:
        get_latest_by = 'published_at'
        ordering = ('-published_at',)
        verbose_name_plural = 'entries'

    def __unicode__(self):
        return self.title

    def save(self, force_insert=False, force_update=False):
        """
        Use Markdown to convert the ``copy`` field from plain-text to
        HTMl.  Smartypants is also used to bring in curly quotes.
        """
        from markdown import markdown
        from smartypants import smartyPants
        self.copy_html = smartyPants(markdown(self.copy, ['abbr',
            'headerid(level=2)']))
        super(Entry, self).save(force_insert=False, force_update=False)

    @permalink
    def get_absolute_url(self):
        """Return the canonical URL for a blog entry."""
        from flother.apps.blog.views import entry_detail
        return (entry_detail, (self.published_at.year, self.slug))

    def is_published(self):
        """
        Return true if this entry is published on the site, -- that is,
        the status is "published" and the publishing date is today or
        earlier.
        """
        return (self.status == self.PUBLISHED_STATUS and
            self.published_at <= datetime.datetime.now())

    def allow_new_comment(self):
        """
        Return True if a new comment can be posted for this entry, False
        otherwise.  Comments can be posted if the entry is published
        (i.e. ``status`` isn't draft or private), the
        ``enable_comments`` field is True, the final date for for
        comments has not yet been reached, and the post's published date
        has passed.
        """
        date_for_comments = self.published_at + datetime.timedelta(
            days=Entry.DAYS_COMMENTS_ENABLED)
        return (self.is_published() and self.enable_comments and
            datetime.datetime.now() <= date_for_comments)
    allow_new_comment.short_description = 'Comments allowed'
    allow_new_comment.boolean = True

    def get_previous_published_entry(self):
        """
        Return the previous public entry published before the current
        time and date.
        """
        return self.get_previous_by_published_at(status=self.PUBLISHED_STATUS,
            published_at__lte=datetime.datetime.now)

    def get_next_published_entry(self):
        """
        Return the next public entry published before the current time
        and date.
        """
        return self.get_next_by_published_at(status=self.PUBLISHED_STATUS,
            published_at__lte=datetime.datetime.now)


class EntryModerator(CommentModerator):

    """
    Comment moderation for the Entry model.  An email is sent once a
    comment is submitted.  Comments are automatically rejected sixty
    days after the blog post was published.
    """

    auto_close_field = 'published_at'
    close_after = Entry.DAYS_COMMENTS_ENABLED
    email_notification = True

    def allow(self, comment, content_object, request):
        """
        Only allow the comment if the entry's ``enable_comments`` field
        is set to True and the entry is published (i.e. not draft or
        private).
        """
        return (content_object.enable_comments and
            content_object.status == Entry.PUBLISHED_STATUS)

    def moderate(self, comment, content_object, request):
        """
        Return True or False, True indicating that the Akismet
        spam-checking service thinks the comment is spam.  As the
        Akismet library doesn't handle Unicode all user-input is
        converted to ASCII before it's passed to the library.
        """
        api = Akismet(key=settings.AKISMET_API_KEY)
        for k in comment.userinfo:
            comment.userinfo[k] = unicodedata.normalize('NFKD',
                comment.userinfo[k]).encode('ascii', 'ignore')
        comment_data = {
            'user_ip': comment.ip_address,
            'user_agent': '',
            'comment_author': comment.userinfo['name'],
            'comment_author_url': comment.userinfo['url'],
            'permalink': comment.get_absolute_url(),
        }
        try:
            return api.comment_check(unicodedata.normalize('NFKD',
                comment.comment).encode('ascii', 'ignore'), comment_data)
        except (urllib2.HTTPError, urllib2.URLError):
            # If Akismet is down the safest option is to assume the
            # comment needs moderating.
            return True

    def email(self, comment, content_object, request):
        """
        Email the details of the newly-submitted comment to the site
        managers.  An email is only sent if the comments ``is_public``
        field is set to True (i.e. not spam).
        """
        if comment.is_public:
            context = {
                'comment': comment,
                'entry': content_object,
            }
            email_body = render_to_string('blog/new_comment_email.txt', context)
            mail_managers(u'Comment on "%s"' % content_object, email_body)


signals.post_delete.connect(delete_blog_index, sender=Entry)
signals.post_save.connect(delete_blog_index, sender=Entry)
signals.post_delete.connect(clear_stagnant_cache_on_comment_change,
    sender=Comment)
signals.post_save.connect(clear_stagnant_cache_on_comment_change,
    sender=Comment)
moderator.register(Entry, EntryModerator)

########NEW FILE########
__FILENAME__ = signals
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from staticgenerator import quick_delete


def delete_blog_index(sender, instance, **kwargs):
    """
    Delete all files in the StaticGenerator cache that will be
    out-of-date after a blog entry is saved.  These are:

      * About page (it has links to the three most-recent entries)
      * Blog index
      * Archive page for the year the entry was published
      * Admin users' preview page
      * Blog Atom 1.0 feed
      * Page for the blog entry itself
      * Previously published entry's page
      * Next published entry's page
    """
    stagnant_cache_urls = [
        '/about/',
        reverse('blog_entry_index'),
        reverse('blog_entry_archive_year', args=[instance.published_at.year]),
        reverse('blog_entry_preview', args=[instance.published_at.year,
            instance.slug]),
        reverse('blog_feeds', args=['latest']),
        instance.get_absolute_url(),
    ]
    try:
        stagnant_cache_urls.append(instance.get_next_published_entry())
    except ObjectDoesNotExist:
        pass
    try:
        stagnant_cache_urls.append(instance.get_previous_published_entry())
    except ObjectDoesNotExist:
        pass
    quick_delete(*stagnant_cache_urls)


def clear_stagnant_cache_on_comment_change(sender, instance, **kwargs):
    """
    Delete the files in the StaticGenerator cache that will be
    out-of-date after a comment is saved or deleted.  These are:

      * Blog index (if this is dealing with the most recent entry)
      * Blog entry page

    Note however that if this is a new comment marked as spam (i.e. the
    ``is_public`` field is False) the cache will not be deleted
    """
    created = kwargs.get('created', False)
    if (not created) or (created and instance.is_public):
        stagnant_cache_urls = [instance.content_object.get_absolute_url()]
        try:
            instance.content_object.get_next_published_entry()
        except ObjectDoesNotExist:
            # This is the most recent entry in the blog so the blog
            # index will need to be removed from the cache.
            stagnant_cache_urls.append(reverse('blog_entry_index'))
        quick_delete(*stagnant_cache_urls)

########NEW FILE########
__FILENAME__ = sitemaps
from django.contrib.sitemaps import Sitemap

from flother.apps.blog.models import Entry


class EntrySitemap(Sitemap):
    """Sitemap for the blog's Entry model."""

    def items(self):
        """Return the Entry objects to appear in the sitemap."""
        return Entry.objects.published()

    def lastmod(self, obj):
        """Return the last modified date for a given Entry object."""
        return obj.updated_at

########NEW FILE########
__FILENAME__ = blogutils
import re

from django import template
from django.conf import settings
from django.utils.html import escape
from django.utils.hashcompat import md5_constructor


register = template.Library()


DEFAULT_GRAVATAR_IMAGE = '%score/img/avatar.png' % settings.MEDIA_URL
GRAVATAR_RATING = 'r'
PULLQUOTE_RE = re.compile(r'<blockquote\sclass="pullquote">.+?</blockquote>',
    re.UNICODE)


@register.simple_tag
def gravatarimg(email, size=32):
    email_hash = md5_constructor(email).hexdigest()
    url = 'http://www.gravatar.com/avatar/%s?s=%d&r=%s&d=%s' % (email_hash,
        size, GRAVATAR_RATING, DEFAULT_GRAVATAR_IMAGE)
    return '<img alt="Gravatar" height="%s" src="%s" width="%s" />' % (size,
        escape(url), size)


@register.filter
def strip_pullquotes(copy):
    """
    Strip pullquotes from the given blog entry copy.  This is used
    in the Atom feed template, as the pullquotes are confusing and out
    of place without CSS applied.

    As an example, given the string::

    >>> s = '<p>Lorem <a href="#">ipsum</a>.</p><blockquote class="pullquote"><p>Dolor sit amet</p></blockquote><p>consectetur adipisicing elit</p>'
    >>> strip_pullquotes(s)
    '<p>Lorem <a href="#">ipsum</a>.</p><p>consectetur adipisicing elit</p>'
    >>> s = '<blockquote><p>Lorem ipsum</p></blockquote><blockquote class="pullquote"><p>Dolor sit amet</p></blockquote><blockquote><p>consectetur adipisicing elit</p></blockquote>'
    >>> strip_pullquotes(s)
    '<blockquote><p>Lorem ipsum</p></blockquote><blockquote><p>consectetur adipisicing elit</p></blockquote>'
    """
    return PULLQUOTE_RE.sub('', copy)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from django.contrib.syndication.views import feed

from flother.apps.blog import views
from flother.apps.blog.feeds import LatestEntries


feeds = {
    'latest': LatestEntries,
}


urlpatterns = patterns('',
    url(r'^$', views.entry_index, name='blog_entry_index'),
    url(r'^(?P<year>\d{4})/$', views.entry_archive_year,
        name='blog_entry_archive_year'),
    url(r'^(?P<year>\d{4})/(?P<slug>[a-z0-9\-]+)/$', views.entry_detail,
        name='blog_entry_detail'),
    url(r'^(?P<year>\d{4})/(?P<slug>[a-z0-9\-]+)/preview/$', views.entry_preview,
        name='blog_entry_preview'),
    url(r'^feeds/(.*)/$', feed, {'feed_dict': feeds}, name='blog_feeds'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import permission_required

from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template import RequestContext

from flother.apps.blog.models import Entry


def entry_index(request):
    """
    Output the latest eleven published blog entries, with the most recent
    of those output in full.
    """
    latest_entry = Entry.objects.latest()
    recent_entries = Entry.objects.published().exclude(id=latest_entry.id)[:10]
    years_with_entries = Entry.objects.published().dates('published_at', 'year')
    context = {
        'latest_entry': latest_entry,
        'recent_entries': recent_entries,
        'years_with_entries': years_with_entries,
    }
    return render_to_response('blog/entry_index.html', context,
        RequestContext(request))


def entry_archive_year(request, year):
    """Output the published blog entries for a given year."""
    entries = get_list_or_404(Entry.objects.published(), published_at__year=year)
    years_with_entries = Entry.objects.published().dates('published_at', 'year')
    entries_by_month = dict.fromkeys(range(1, 13), 0)
    for entry in entries:
        entries_by_month[entry.published_at.month] += 1
    context = {
        'year': year,
        'entries': entries,
        'entries_by_month': entries_by_month,
        'max_entries_per_month': max(entries_by_month.values()),
        'years_with_entries': years_with_entries,
    }
    return render_to_response('blog/entry_archive_year.html', context,
        RequestContext(request))


def entry_detail(request, year, slug):
    """
    Output a full individual entry; this is the view for an entry's
    permalink.
    """
    entry = get_object_or_404(Entry.objects.published(), published_at__year=year,
        slug=slug)
    context = {'entry': entry}
    return render_to_response('blog/entry_detail.html', context,
        RequestContext(request))


@permission_required('blog.change_entry', '/admin/')
def entry_preview(request, year, slug):
    """
    Allows draft entries to be viewed as if they were publicly available
    on the site.  Draft entries with a ``published_at`` date in the
    future are visible too.  The same template as the ``entry_detail``
    view is used.
    """
    entry = get_object_or_404(Entry.objects.filter(status=Entry.DRAFT_STATUS),
        published_at__year=year, slug=slug)
    context = {'entry': entry}
    return render_to_response('blog/entry_detail.html', context,
        RequestContext(request))

########NEW FILE########
__FILENAME__ = forms
import time

from django.contrib.comments.forms import CommentForm
from django import forms
from django.forms.util import ErrorDict


class CommentFormForCaching(CommentForm):

    """
    Django's CommentForm class minus the security fields.

    Because the site is heavily cached the security fields won't work
    as they're based on a timestamp that will go out-of-date very
    quickly on a cached page.
    """

    def clean_timestamp(self):
        """
        Return the timestamp without throwing an error.  Because blog
        entries are heavily cached the forms timestamp will be
        out-of-date almost all the time, so there's no point in
        checking.  Akismet can handle spam.
        """
        return self.cleaned_data["timestamp"]

    def security_errors(self):
        """Return just those errors associated with security."""
        errors = ErrorDict()
        if 'honeypot' in self.errors:
            errors['honeypot'] = self.errors['honeypot']
        return errors

    def generate_security_hash(self, content_type, object_pk, timestamp):
        """Generate a SHA1 security hash."""
        return 'ce7501007f04a6529e650f1f1b3fc0586d1d94eb'

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from flother.apps.contact.models import Message


class MessageAdmin(admin.ModelAdmin):
    actions = None
    date_hierarchy = 'created_at'
    list_display = ('sender_name', 'sender_email', 'body_teaser', 'created_at',
        'is_spam')
    list_filter = ('created_at', 'is_spam',)
    search_fields = ('sender_name', 'sender_email', 'body')

admin.site.register(Message, MessageAdmin)

########NEW FILE########
__FILENAME__ = forms
import os
import unicodedata
import urllib2

from django.conf import settings
from django import forms

from flother.utils.akismet import Akismet


class MessageForm(forms.Form):

    """A form to handle messages submitted through the web site."""

    sender_name = forms.CharField(max_length=64, label='Your name')
    sender_email = forms.EmailField(label='Your email address')
    body = forms.CharField(label='Your message', widget=forms.Textarea)

    def is_spam(self):
        try:
            api = Akismet(key=settings.AKISMET_API_KEY)
            data = {
                "user_ip": os.environ.get('REMOTE_ADDR', '127.0.0.1'),
                "user_agent": os.environ.get('HTTP_USER_AGENT', 'Unknown'),
            }
            return api.comment_check(unicodedata.normalize('NFKD',
                self.cleaned_data["body"]).encode('ascii', 'ignore'), data)
        except (urllib2.HTTPError, urllib2.URLError):
            # TODO: Do better than simply assume the message is OK if Akismet
            # is down.
            return False

########NEW FILE########
__FILENAME__ = 0001_initial
import django
from django.db import models
from south.db import db

from flother.apps.contact.models import *


class Migration:
    def forwards(self, orm):
        """Add model ``Message``."""
        db.create_table('contact_message', (
            ('body', orm['contact.Message:body']),
            ('sender_name', orm['contact.Message:sender_name']),
            ('created_at', orm['contact.Message:created_at']),
            ('updated_at', orm['contact.Message:updated_at']),
            ('sender_email', orm['contact.Message:sender_email']),
            ('id', orm['contact.Message:id']),
            ('is_spam', orm['contact.Message:is_spam']),
        ))
        db.send_create_signal('contact', ['Message'])

    def backwards(self, orm):
        """Delete model ``Message``."""
        db.delete_table('contact_message')

    models = {
        'contact.message': {
            'body': ('django.db.models.fields.TextField', [], {}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True', 'blank': 'True'}),
            'is_spam': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'sender_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'sender_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['contact']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.text import truncate_words


class Message(models.Model):

    """A message sent to me through the web site."""

    sender_name = models.CharField(max_length=64)
    sender_email = models.EmailField()
    body = models.TextField()
    is_spam = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,
        verbose_name='date sent')
    updated_at = models.DateTimeField(auto_now=True,
        verbose_name='date updated')

    class Meta:
        get_latest_by = 'created_at'
        ordering = ('-created_at',)

    def __unicode__(self):
        return u'%s: %s' % (self.sender_name, self.body_teaser())

    def body_teaser(self):
        return truncate_words(self.body, 10)
    body_teaser.short_description = 'body'
    
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from flother.apps.contact import views


urlpatterns = patterns('',
    url(r'^$', views.send_message, name='contact_send_message'),
)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.core.mail import mail_managers
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from flother.apps.contact.models import Message
from flother.apps.contact.forms import MessageForm


def send_message(request):
    """
    On a get request, show a form to allow visitors to send me a
    message.  On a post request, save the message in the database and
    send me an email if Akismet doesn't consider the message to be spam.
    """
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = Message(sender_name=form.cleaned_data['sender_name'],
                sender_email=form.cleaned_data['sender_email'],
                body=form.cleaned_data['body'])
            if form.is_spam():
                message.is_spam = True
            else:
                message_body = "%s (%s) said:\n\n%s\n" % (
                    form.cleaned_data['sender_name'],
                    form.cleaned_data['sender_email'],
                    form.cleaned_data['body'])
                mail_managers('Flother.com contact message', message_body)
            message.save()
            return HttpResponseRedirect('%s?sent' % reverse(send_message))
    else:
        form = MessageForm()
    context = {
        'form': form,
        'sent': request.GET.has_key('sent'),
    }
    return render_to_response('contact/send_message.html', context,
        context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from flother.apps.files.models import File


class FileAdmin(admin.ModelAdmin):

    """
    Class for specifiying the options for administering the
    flother.apps.blog.models.File model via the Django admin.
    """

    date_hierarchy = 'uploaded_at'
    list_display = ('thumbnail_html', 'title', 'uploaded_at', 'is_visible')
    list_display_links = ('thumbnail_html', 'title')
    list_filter = ('uploaded_at', 'is_visible',)
    search_fields = ('title',)

admin.site.register(File, FileAdmin)

########NEW FILE########
__FILENAME__ = managers
from django.db.models import Manager


class FileManager(Manager):

    """
    Django model manager for the File model. Overrides the default
    latest() method so it returns the latest visible file, and adds a
    visible() method that returns only visible files.
    """

    def latest(self, field_name=None):
        """Return the latest visible file."""
        return self.visible().latest(field_name)

    def visible(self, **kwargs):
        """
        Return a QuerySet that contains only those files that are 
        visible, i.e. files with a status of "visible".
        """
        from flother.apps.files.models import File
        return self.get_query_set().filter(is_visible=True, **kwargs)

########NEW FILE########
__FILENAME__ = models
import datetime
import mimetypes
import os

from django.conf import settings
from django.db import models
from django.utils.html import escape
from PIL import Image

from flother.apps.files.managers import FileManager
from flother.utils.image import create_thumbnail


class File(models.Model):

    """An individual file and its metadata."""

    THUMBNAIL_SIZE = (80, 80)
    IMAGE_FRAME_FILE = 'core/img/frame.png'
    DEFAULT_ICON_FILE = 'core/img/document.png'
    FILE_UPLOAD_DIRECTORY = 'apps/files/uploads/originals'
    THUMBNAIL_UPLOAD_DIRECTORY = 'apps/files/uploads/thumbnails'

    title = models.CharField(max_length=64)
    item = models.FileField(upload_to=FILE_UPLOAD_DIRECTORY,
        verbose_name='file')
    uploaded_at = models.DateTimeField(default=datetime.datetime.now,
        editable=False, verbose_name='date uploaded')
    updated_at = models.DateTimeField(auto_now=True, editable=False,
        verbose_name='date updated')
    is_visible = models.BooleanField(default=True, verbose_name="visible")
    thumbnail = models.ImageField(upload_to=THUMBNAIL_UPLOAD_DIRECTORY,
        editable=False)

    objects = FileManager()

    class Meta:
        get_latest_by = 'uploaded_at'
        ordering = ('-uploaded_at', 'title',)
        permissions = (('can_use', 'Can use files'),)

    def __unicode__(self):
        return self.title

    def save(self, force_insert=False, force_update=False):
        """
        Save a thumbnail for the uploaded file.  If it's an image the
        thumbnail contains a crop of the image itself, framed within a
        pretty border.  Any file other than an image just gets a default
        icon.
        """
        # The file model object needs to be saved first before the file 
        # itself can be accessed.
        super(File, self).save(force_insert, force_update)
        # If the uploaded file is an image, create a thumbnail based on
        # the image itself.  If it's not an image, use the default
        # thumbnail.
        try:
            # Open the uploaded image and create a thumbnail.
            im = Image.open(self.item.path)
            thumbnail_image = create_thumbnail(im, File.THUMBNAIL_SIZE)
            thumbnail_basename = "%d.png" % self.id
            # Create a new image the same size as the frame image, with
            # the thumbnail centred within it.
            image_frame = Image.open(os.path.join(settings.MEDIA_ROOT,
                File.IMAGE_FRAME_FILE))
            thumbnail_layer = Image.new('RGBA', image_frame.size)
            vertical_pos = (image_frame.size[0] - thumbnail_image.size[0]) / 2
            horizontal_pos = (image_frame.size[1] - thumbnail_image.size[1]) / 2
            thumbnail_layer.paste(thumbnail_image, (vertical_pos,
                horizontal_pos))
            # Layer the thumbnail underneath the frame image.
            thumbnail = Image.composite(image_frame, thumbnail_layer,
                image_frame)
            thumbnail.save(os.path.join(settings.MEDIA_ROOT,
                File.THUMBNAIL_UPLOAD_DIRECTORY, thumbnail_basename),
                format="PNG", optimize=True)
            self.thumbnail = os.path.join(File.THUMBNAIL_UPLOAD_DIRECTORY,
                thumbnail_basename)
        except IOError:
            # The uploaded file isn't an image format supported by PIL.
            self.thumbnail = File.DEFAULT_ICON_FILE
        super(File, self).save(force_insert, force_update)

    def get_absolute_url(self):
        return self.item.url

    def thumbnail_html(self):
        """Return an XHTML image element for the file's thumbnail."""
        im = Image.open(self.thumbnail.path)
        return '<img alt="%s" height="%s" src="%s" width="%s" />' % (
            escape(self.title), im.size[1], escape(self.thumbnail.url),
            im.size[0])
    thumbnail_html.short_description = 'Thumbnail'
    thumbnail_html.allow_tags = True

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from flother.apps.files import views


urlpatterns = patterns('',
    # Some URL namespacing here: site the JSON view within the admin.
    url(r'^admin/files/json/$', views.files_list, name='files_file_list'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.utils import simplejson

from flother.apps.files.models import File


@permission_required('files.can_use', '/admin/')
def files_list(request):
    """
    Return a list of available files as a JSON object.  This is used
    only in the admin to allow files to be inserted into Markdown-based
    textareas.
    """
    files = [{
        'id': f.id,
        'title': f.title,
        'url': f.get_absolute_url(),
        'uploaded_at': f.uploaded_at.isoformat(),
        'thumbnail_html': f.thumbnail_html()
    } for f in File.objects.visible()]
    return HttpResponse(simplejson.dumps(files), 'application/json')

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from flother.apps.photos import models


class PhotoAdmin(admin.ModelAdmin):

    """Django model admin for ``flother.apps.photos.models.Photo``."""

    date_hierarchy = 'taken_at'
    fieldsets = (
        (None, {
            'fields': (
                'title', 'slug', 'original', 'photographer', 'description'
            )
        }),
        ('Metadata', {
            'fields': (
                'taken_at', 'point', 'exposure', 'aperture', 'focal_length',
                'iso_speed', 'status', 'camera'
            )
        }),
        ('Relationships', {
            'fields': (
                'collections',
            ),
            'classes': (
                'collapse',
            )
        }),
    )
    filter_horizontal = ('collections',)
    list_display = ('thumbnail_html', 'title', 'photographer', 'taken_at',
        'location', 'status')
    list_display_links = ('thumbnail_html', 'title')
    list_filter = ('photographer', 'status', 'camera')
    prepopulated_fields = {'slug': ('title',)}
    radio_fields = {'status': admin.HORIZONTAL}
    search_fields = ('title', 'description', 'exposure', 'aperture',
        'focal_length', 'iso_speed')

    def queryset(self, request):
        """
        Return the queryset to use in the admin list view.  Superusers
        can see all photos, other users can see only their own photos.
        """
        if request.user.is_superuser:
            return models.Photo.objects.all()
        return models.Photo.objects.filter(photographer=request.user)


class CollectionAdmin(admin.ModelAdmin):

    """Django model admin for ``flother.apps.photos.models.Collection``."""

    exclude = ('description_html',)
    list_display = ('title', 'number_of_photos')
    list_select_related = True
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title',)


class CameraAdmin(admin.ModelAdmin):

    """Django model admin for ``flother.apps.photos.models.Camera``."""

    exclude = ('description_html',)
    list_display = ('name', 'number_of_photos')
    list_select_related = True
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


admin.site.register(models.Photo, PhotoAdmin)
admin.site.register(models.Collection, CollectionAdmin)
admin.site.register(models.Camera, CameraAdmin)

########NEW FILE########
__FILENAME__ = import_from_flickr
import datetime
import os
import unicodedata
import urllib2

from django.conf import settings
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.core.management.base import NoArgsCommand
from django.utils import simplejson
import Flickr.API

from flother.apps.photos.models import Photo, FlickrPhoto, Camera
from flother.apps.places.models import Point, Location, Country
from flother.utils import geonames


class Command(NoArgsCommand):
    help = "Imports photos from Flickr."
    api = None
    default_args = {'format': 'json', 'nojsoncallback': 1}

    def __init__(self):
        self.photographer = User.objects.get(id=1)
        self.api = Flickr.API.API(settings.FLICKR_API_KEY,
            secret=settings.FLICKR_API_SECRET)

    def handle_noargs(self, **options):
        """
        Import photos from a Flickr account and store them and their
        metadata in this site's database.
        """
        verbosity = int(options.get('verbosity', 1))
        page = 0
        last_page = 1
        new_photo_on_this_page = True
        while page < last_page and (new_photo_on_this_page or page == 1):
            # Loop through all the pages in the API results from Flickr.
            # The script will stop before the end if a page has no new
            # photos.
            new_photo_on_this_page = False
            page = page + 1
            photos_json = self.call(method='flickr.people.getPublicPhotos',
                args={'user_id': settings.FLICKR_NSID, 'page': page}).read()
            photos = simplejson.loads(photos_json)
            last_page = photos['photos']['pages']
            for photo_data in photos['photos']['photo']:
                # Does the photo exist?
                flickr_photo, created = FlickrPhoto.objects.select_related().get_or_create(
                    flickr_id=photo_data['id'])
                if created:
                    # It's a new photo!  Let's grab all the metadata.
                    photo_info = simplejson.loads(self.call(
                        method='flickr.photos.getInfo',
                        args={'photo_id': photo_data['id']}).read())
                    photo = Photo()
                    # Because we've found at least one new photo on this
                    # page of results, we'll check the next page too.
                    new_photo_on_this_page = True
                    photo_exif = simplejson.loads(self.call(
                            method='flickr.photos.getExif',
                            args={'photo_id': photo_data['id']}).read())

                    # Add all the metadata to this ``Photo`` model.
                    photo.title = photo_info['photo']['title']['_content'][:128]
                    photo.slug = slugify(photo.title[:50])
                    photo.original = self._save_photo(
                        self._get_photo_data(photo_info), '%s.%s' % (
                        photo_info['photo']['id'],
                        photo_info['photo']['originalformat']))
                    photo.description = photo_info['photo']['description']['_content']
                    photo.photographer = self.photographer
                    photo.exposure = self._get_exif(photo_exif, 'Exposure')[:64]
                    photo.aperture = self._get_exif(photo_exif, 'Aperture')[:64]
                    photo.focal_length = self._get_exif(photo_exif, 'Focal Length')[:64]
                    photo.iso_speed = self._get_exif(photo_exif, 'ISO Speed')[:64]
                    photo.taken_at = self._convert_time(photo_info['photo']['dates']['taken'])
                    photo.uploaded_at = self._convert_time(photo_info['photo']['dateuploaded'])
                    photo.point = self._get_or_create_point(photo_data)
                    # Create a ``Camera`` model for the camera used to
                    # take this photo if it doesnt exist already.
                    camera = self._get_exif(photo_exif, 'Model')[:64]
                    if camera:
                        photo.camera, camera_created = Camera.objects.get_or_create(
                            name=camera, slug=slugify(camera[:50]))
                    photo.save()
                    new_photo_on_this_page = True
                    if not flickr_photo.photo:
                        flickr_photo.photo = photo
                        flickr_photo.save()
                    print unicodedata.normalize('NFKD', unicode(photo.title)).encode(
                        'ascii', 'ignore')

    def call(self, method, args={}, sign=False):
        args.update(self.default_args)
        return self.api.execute_method(method=method, args=args, sign=sign)

    def _convert_time(self, time):
        """
        Convert the date/time string returned by Flickr into a
        ``datetime`` object.
        """
        try:
            converted_time = int(time)
        except ValueError:
            converted_time = datetime.datetime.strptime(time,
                '%Y-%m-%d %H:%M:%S')
        return converted_time

    def _get_exif(self, photo_info, exif_name):
        """
        Return the data stored in an EXIF field, or a blank string if it
        doesn't exist.
        """
        for exif in photo_info['photo']['exif']:
            if exif['label'] == exif_name:
                return exif['raw']['_content']
        return ''

    def _get_or_create_point(self, photo_data):
        """
        Create a ``Point`` model object for use with a newly-imported
        photo.  Creating a point will also create ``Location`` and
        ``Country`` objects as required, and link the ``Point`` to both.
        """
        latlon = simplejson.loads(self.call(
            method='flickr.photos.geo.getLocation',
            args={'photo_id': photo_data['id']}).read())
        if latlon['stat'] == 'ok':
            try:
                point = Point.objects.get(
                    latitude=str('%3.5f' % float(latlon['photo']['location']['latitude'])),
                    longitude=str('%3.5f' % float(latlon['photo']['location']['longitude'])))
                created = False
            except Point.DoesNotExist:
                point = Point(
                    latitude=str('%3.5f' % float(latlon['photo']['location']['latitude'])),
                    longitude=str('%3.5f' % float(latlon['photo']['location']['longitude'])),
                    accuracy=latlon['photo']['location']['accuracy'])
                created = True
            if created:
                # Create location and country.
                try:
                    place = geonames.findNearbyPlaceName(float(point.latitude),
                        float(point.longitude)).geoname[0]
                except AttributeError:
                    return None
                country, created = Country.objects.get_or_create(
                    name=place.countryName, country_code=place.countryCode)
                location, created = Location.objects.get_or_create(
                    name=place.name, slug=slugify(place.name[:50]),
                    country=country)
                location.country = country
                location.save()
                point.location = location
                point.save()
            return point
        return None

    def _get_photo_url(self, photo_info):
        """Return the Flickr URL for a photo."""
        return "http://farm%s.static.flickr.com/%s/%s_%s_o.%s" % (
            photo_info['photo']['farm'], photo_info['photo']['server'],
            photo_info['photo']['id'], photo_info['photo']['originalsecret'],
            photo_info['photo']['originalformat'])

    def _get_photo_data(self, photo_info):
        """Return the raw image (JPEG, GIF, PNG) data from a Flickr."""
        url = self._get_photo_url(photo_info)
        response = urllib2.urlopen(url)
        data = response.read()
        return data

    def _save_photo(self, photo_data, basename):
        """Save the raw photo data taken from Flickr as a file on disk."""
        filename = os.path.join(settings.MEDIA_ROOT,
            Photo.ORIGINAL_UPLOAD_DIRECTORY, basename)
        fh = open(filename, 'w')
        fh.write(photo_data)
        fh.close()
        return os.path.join(Photo.ORIGINAL_UPLOAD_DIRECTORY, basename)

########NEW FILE########
__FILENAME__ = 0001_initial
import datetime

from django.db import models
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Photo'
        db.create_table('photos_photo', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('original', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('medium', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('listing', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('thumbnail', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('description_html', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('photographer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('status', self.gf('django.db.models.fields.SmallIntegerField')(default=2)),
            ('exposure', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('aperture', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('focal_length', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('iso_speed', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('taken_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('uploaded_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_landscape', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
            ('point', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['places.Point'], null=True, blank=True)),
            ('camera', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['photos.Camera'], null=True, blank=True)),
        ))
        db.send_create_signal('photos', ['Photo'])

        # Adding M2M table for field collections on 'Photo'
        db.create_table('photos_photo_collections', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('photo', models.ForeignKey(orm['photos.photo'], null=False)),
            ('collection', models.ForeignKey(orm['photos.collection'], null=False))
        ))
        db.create_unique('photos_photo_collections', ['photo_id', 'collection_id'])

        # Adding model 'Collection'
        db.create_table('photos_collection', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, unique=True, db_index=True)),
            ('key_photo', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('description_html', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('photos', ['Collection'])

        # Adding model 'Camera'
        db.create_table('photos_camera', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, unique=True, db_index=True)),
            ('icon', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('description_html', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('photos', ['Camera'])

        # Adding model 'FlickrPhoto'
        db.create_table('photos_flickrphoto', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('photo', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['photos.Photo'], null=True, blank=True)),
            ('flickr_id', self.gf('django.db.models.fields.TextField')(max_length=128, db_index=True)),
        ))
        db.send_create_signal('photos', ['FlickrPhoto'])


    def backwards(self, orm):
        # Deleting model 'Photo'
        db.delete_table('photos_photo')

        # Removing M2M table for field collections on 'Photo'
        db.delete_table('photos_photo_collections')

        # Deleting model 'Collection'
        db.delete_table('photos_collection')

        # Deleting model 'Camera'
        db.delete_table('photos_camera')

        # Deleting model 'FlickrPhoto'
        db.delete_table('photos_flickrphoto')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'photos.camera': {
            'Meta': {'object_name': 'Camera'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'unique': 'True', 'db_index': 'True'})
        },
        'photos.collection': {
            'Meta': {'object_name': 'Collection'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key_photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'unique': 'True', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'photos.flickrphoto': {
            'Meta': {'object_name': 'FlickrPhoto'},
            'flickr_id': ('django.db.models.fields.TextField', [], {'max_length': '128', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'photo': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['photos.Photo']", 'null': 'True', 'blank': 'True'})
        },
        'photos.photo': {
            'Meta': {'object_name': 'Photo'},
            'aperture': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'camera': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['photos.Camera']", 'null': 'True', 'blank': 'True'}),
            'collections': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['photos.Collection']", 'symmetrical': 'False', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'exposure': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'focal_length': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_landscape': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'iso_speed': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'listing': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'medium': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'original': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'photographer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'point': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['places.Point']", 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '2'}),
            'taken_at': ('django.db.models.fields.DateTimeField', [], {}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'places.country': {
            'Meta': {'object_name': 'Country'},
            'country_code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'unique': 'True'}),
            'flag': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'formal_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'places.location': {
            'Meta': {'unique_together': "(('slug', 'country'),)", 'object_name': 'Location'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['places.Country']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'places.point': {
            'Meta': {'unique_together': "(('longitude', 'latitude', 'accuracy'),)", 'object_name': 'Point'},
            'accuracy': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'latitude': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '5'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['places.Location']"}),
            'longitude': ('django.db.models.fields.DecimalField', [], {'max_digits': '8', 'decimal_places': '5'})
        }
    }

    complete_apps = ['photos']

########NEW FILE########
__FILENAME__ = models
import os
import hashlib

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import permalink
from django.utils.html import escape
from PIL import Image, ImageFile

from flother.apps.places.models import Point
from flother.utils.image import create_thumbnail


class Photo(models.Model):

    """A photograph in various sizes along with its metadata."""

    MEDIUM_LANDSCAPE_SIZE = [606, 404]
    MEDIUM_PORTRAIT_SIZE = [404, 606]
    LISTING_SIZE = (300, 200)
    THUMBNAIL_SIZE = (128, 128)
    ORIGINAL_UPLOAD_DIRECTORY = 'apps/photos/originals'
    MEDIUM_UPLOAD_DIRECTORY = 'apps/photos/medium'
    LISTING_UPLOAD_DIRECTORY = 'apps/photos/listing'
    THUMBNAIL_UPLOAD_DIRECTORY = 'apps/photos/thumbnails'

    PUBLISHED_STATUS = 2
    PRIVATE_STATUS = 3
    STATUS_CHOICES = ((PUBLISHED_STATUS, 'Published'),
        (PRIVATE_STATUS, 'Private'))

    title = models.CharField(max_length=128)
    slug = models.SlugField(unique_for_year='taken_at')
    original = models.ImageField(upload_to=ORIGINAL_UPLOAD_DIRECTORY,
        verbose_name='image')
    medium = models.ImageField(upload_to=MEDIUM_UPLOAD_DIRECTORY, blank=True)
    listing = models.ImageField(upload_to=LISTING_UPLOAD_DIRECTORY, blank=True)
    thumbnail = models.ImageField(upload_to=THUMBNAIL_UPLOAD_DIRECTORY,
        blank=True)
    description = models.TextField(blank=True)
    description_html = models.TextField(blank=True)
    photographer = models.ForeignKey(User)
    status = models.SmallIntegerField(choices=STATUS_CHOICES,
        default=PUBLISHED_STATUS)
    exposure = models.CharField(max_length=64, blank=True)
    aperture = models.CharField(max_length=64, blank=True)
    focal_length = models.CharField(max_length=64, blank=True)
    iso_speed = models.CharField(max_length=64, verbose_name='ISO speed',
        blank=True)
    taken_at = models.DateTimeField(verbose_name='date taken')
    uploaded_at = models.DateTimeField(auto_now_add=True,
        verbose_name='date uploaded')
    updated_at = models.DateTimeField(auto_now=True,
        verbose_name='date updated')
    is_landscape = models.BooleanField(default=True)
    collections = models.ManyToManyField('Collection', blank=True, null=True)
    point = models.ForeignKey(Point, blank=True, null=True)
    camera = models.ForeignKey('Camera', blank=True, null=True)

    class Meta:
        get_latest_by = 'taken_at'
        ordering = ('-taken_at',)

    def __unicode__(self):
        return self.title

    @permalink
    def get_absolute_url(self):
        """Return the canonical URL for a photo."""
        from flother.apps.photos.views import photo_detail
        return (photo_detail, (self.taken_at.year, self.slug))

    def save(self, force_insert=False, force_update=False):
        """
        Save the photo.  Overrides the model's default ``save`` method
        to save the original photo in various dimensions.  Each size is
        used in different parts of the site.  The original photo is also
        kept.
        """
        super(Photo, self).save(force_insert, force_update)

        self._set_orientation()
        medium_size = Photo.MEDIUM_LANDSCAPE_SIZE
        if not self.is_landscape:
            medium_size = Photo.MEDIUM_PORTRAIT_SIZE
        image_basename = '%s.jpg' % hashlib.sha1(str(self.id)).hexdigest()
        im = Image.open(self.original.path)
        # Workaround for a problem in the PIL JPEG library:
        # http://mail.python.org/pipermail/image-sig/1999-August/000816.html.
        ImageFile.MAXBLOCK = 1000000

        image_presets = {
            'medium': {'field': self.medium, 'size': medium_size,
                'upload_directory': Photo.MEDIUM_UPLOAD_DIRECTORY},
            'listing': {'field': self.listing, 'size': Photo.LISTING_SIZE,
                'upload_directory': Photo.LISTING_UPLOAD_DIRECTORY},
            'thumbnail': {'field': self.thumbnail, 'size': Photo.THUMBNAIL_SIZE,
                'upload_directory': Photo.THUMBNAIL_UPLOAD_DIRECTORY},
        }
        for preset_name, preset in image_presets.items():
            if preset_name == 'medium':
                image = im
                image.thumbnail(preset['size'], Image.ANTIALIAS)
            else:
                image = create_thumbnail(im, preset['size'])
            image.save(os.path.join(settings.MEDIA_ROOT,
                preset['upload_directory'], image_basename), format="JPEG",
                quality=85, optimize=True)
            preset['file'] = os.path.join(preset['upload_directory'],
                image_basename)

        self.medium = image_presets['medium']['file']
        self.listing = image_presets['listing']['file']
        self.thumbnail = image_presets['thumbnail']['file']

        super(Photo, self).save(force_insert, force_update)

    def is_published(self):
        """
        Returns a boolean denoting whether the photo is publicly
        available.
        """
        return self.status == self.PUBLISHED_STATUS

    def get_previous_published_photo(self):
        """Return the previously published photo by date."""
        return self.get_previous_by_taken_at(status=self.PUBLISHED_STATUS,
            taken_at__lte=datetime.datetime.now)

    def get_next_published_photo(self):
        """Return the next published photo by date."""
        return self.get_next_by_taken_at(status=self.PUBLISHED_STATUS,
            taken_at__lte=datetime.datetime.now)

    def thumbnail_html(self):
        """Return an XHTML image element for the file's thumbnail."""
        return '<img alt="%s" height="%s" src="%s" width="%s" />' % (
            escape(self.title), Photo.THUMBNAIL_SIZE[1],
            escape(self.thumbnail.url),  Photo.THUMBNAIL_SIZE[0])
    thumbnail_html.short_description = 'Thumbnail'
    thumbnail_html.allow_tags = True

    def location(self):
        """Return the linked ``Location`` for this photo."""
        return self.point.location

    def _set_orientation(self):
        """
        Set a boolean denoting whther this photo is landscape or
        portrait.
        """
        fp = open(self.original.path, 'rb')
        im = Image.open(fp)
        im.load()
        fp.close()
        if (im.size[1] / float(im.size[0])) > 1:
            self.is_landscape = False
        else:
            self.is_landscape = True


class Collection(models.Model):

    """A collection, or set, of photos."""

    KEY_PHOTO_UPLOAD_DIRECTORY = 'apps/photos/collections'
    KEY_PHOTO_SIZE = (293, 195)

    title = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)
    key_photo = models.ImageField(upload_to=KEY_PHOTO_UPLOAD_DIRECTORY)
    description = models.TextField(blank=True)
    description_html = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        get_latest_by = 'created_at'
        ordering = ('-created_at',)

    def __unicode__(self):
        return self.title

    def save(self, force_insert=False, force_update=False):
        """
        Save the collection.  Overrides the model's default ``save``
        method to save the key photo for the collection at the correct
        size.
        """
        super(Collection, self).save(force_insert, force_update)
        im = Image.open(self.key_photo.path)
        if not im.size == Collection.KEY_PHOTO_SIZE:
            image = create_thumbnail(im, Collection.KEY_PHOTO_SIZE)
            image.save(self.key_photo.path, format="JPEG", quality=85,
                optimize=True)
        super(Collection, self).save(force_insert, force_update)

    def number_of_photos(self):
        """Returns the number of photos linked to this collection."""
        return self.photo_set.count()


class Camera(models.Model):

    """A photographic camera used to take the photos on the site."""

    ICON_UPLOAD_DIRECTORY = 'apps/photos/cameras'

    name = models.CharField(max_length=64)
    slug = models.SlugField(unique=True)
    icon = models.ImageField(upload_to=ICON_UPLOAD_DIRECTORY, blank=True)
    description = models.TextField(blank=True)
    description_html = models.TextField(blank=True)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def number_of_photos(self):
        """Returns the number of photos linked to this camera."""
        return self.photo_set.count()


class FlickrPhoto(models.Model):

    """
    A private model used to track which photos have been imported to the
    site from Flickr.  This model is only for use by the
    ``import_from_flickr`` management command.
    """

    photo = models.ForeignKey(Photo, blank=True, null=True)
    flickr_id = models.TextField(max_length=128, db_index=True)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from flother.apps.photos import views


urlpatterns = patterns('',
    url(r'^archive/(?P<year>\d{4})/(?P<slug>[a-z0-9\-]+)/$',
        views.photo_detail, name='photos_photo_detail'),
)

########NEW FILE########
__FILENAME__ = views
def photo_detail(request, year, slug):
    pass

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from flother.apps.places import models


class PointAdmin(admin.ModelAdmin):

    """Django model admin for ``flother.apps.places.models.Point``."""

    fieldsets = ((None, {'fields': (('longitude', 'latitude'), 'location')}),)
    list_display = ('__unicode__', 'longitude', 'latitude', 'location',
        'number_of_photos')
    list_editable = ('longitude', 'latitude', 'location',)
    list_select_related = True
    list_filter = ('location',)


class LocationAdmin(admin.ModelAdmin):

    """Django model admin for ``flother.apps.places.models.Location``."""

    list_display = ('name', 'country', 'number_of_photos')
    list_filter = ('country',)
    list_select_related = True
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class CountryAdmin(admin.ModelAdmin):

    """Django model admin for ``flother.apps.places.models.Country``."""

    list_display = ('name', 'formal_name', 'country_code', 'number_of_photos')
    list_editable = ('formal_name',)
    list_select_related = True
    search_fields = ('name', 'formal_name')


admin.site.register(models.Point, PointAdmin)
admin.site.register(models.Location, LocationAdmin)
admin.site.register(models.Country, CountryAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Point(models.Model):

    """
    A geographical position specified by a longitude and latitude point.
    It's linked to a ``Location`` model object which is a human name for
    the town or area.  The ``accuracy`` field stores the level of detail
    for the point.
    """

    longitude = models.DecimalField(max_digits=8, decimal_places=5)
    latitude = models.DecimalField(max_digits=8, decimal_places=5)
    accuracy = models.SmallIntegerField(blank=True, null=True)
    location = models.ForeignKey('Location')

    class Meta:
        unique_together = ('longitude', 'latitude', 'accuracy')
        ordering = ('location', 'longitude', 'latitude')

    def __unicode__(self):
        return unicode(self.location)

    def number_of_photos(self):
        """Returns the number of photos linked to this point."""
        return self.photo_set.count()


class Location(models.Model):

    """A town or city within a particular country."""

    name = models.CharField(max_length=64)
    slug = models.SlugField()
    country = models.ForeignKey('Country')

    class Meta:
        unique_together = ('slug', 'country')
        ordering = ('country__name', 'name')

    def __unicode__(self):
        return "%s, %s" % (self.name, self.country)

    def number_of_photos(self):
        """Returns the number of photos linked to this location."""
        from flother.apps.photos.models import Photo
        return Photo.objects.filter(point__location=self).count()


class Country(models.Model):

    """A country.  It's fairly obvious."""

    FLAG_UPLOAD_DIRECTORY = 'apps/places/flags'

    name = models.CharField(max_length=32)
    country_code = models.CharField(max_length=2, unique=True)
    formal_name = models.CharField(max_length=128, blank=True)
    flag = models.ImageField(upload_to=FLAG_UPLOAD_DIRECTORY, blank=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'countries'

    def __unicode__(self):
        return self.name

    def number_of_photos(self):
        """Returns the number of photos linked to this country."""
        from flother.apps.photos.models import Photo
        return Photo.objects.filter(point__location__country=self).count()

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from flother.apps.search import views


urlpatterns = patterns('',
    url(r'^$', views.search_results, name='search_search_results'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
import urllib
import urllib2

from django.contrib.sites.models import Site
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import simplejson


def search_results(request):
    """Return a list of pages that contain the given search term"""
    search_query = request.GET.get('q')
    try:
        page = int(request.GET.get('p', 1))
    except ValueError:
        page = 1
    search_results = []
    total_pages = 0
    current_page = False
    next_page = False
    previous_page = False
    if search_query:
        # Get the current site and build the Google Ajax search URL.
        site = Site.objects.get_current()
        query_param = 'site:%s %s' % (site.domain, search_query)
        params = {
            'v': '1.0',
            'rsz': 'large',
            'start': (page - 1) * 8,
            'q': query_param,
        }
        base_search_url = 'http://www.google.com/uds/GwebSearch'
        search_url = '?'.join([base_search_url,
            urllib.urlencode(params.items())])
        # Build a request and get the JSON search results from Google.
        search_request = urllib2.Request(search_url)
        search_request.add_header('User-Agent', '%s (%s)' % (site.name,
            site.domain))
        opener = urllib2.build_opener()
        # Get all the useful 
        try:
            json = simplejson.loads(opener.open(search_request).read())
            raw_search_results = json['responseData']['results']
            total_pages = len(json['responseData']['cursor']['pages'])
            current_page = json['responseData']['cursor']['currentPageIndex'] + 1
            next_page = current_page + 1 if current_page != total_pages else False
            previous_page = current_page - 1 if current_page > 1 else False
        except (urllib2.HTTPError, KeyError):
            raw_search_results = {}
        # Loop through each result and strip ' — Flother' from the titles.
        for result in raw_search_results:
            title = result['titleNoFormatting'].rsplit(u'—', 1)[0].strip()
            search_results.append({'title': title, 'url': result['url'],
                'content': result['content']})
    context = {
        'search_query': search_query,
        'search_results': search_results,
        'first_result': ((page - 1) * 8) + 1,
        'total_pages': total_pages,
        'current_page': current_page,
        'next_page': next_page,
        'previous_page': previous_page,
    }
    return render_to_response('search/search_results.html', context,
        context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = common
import os
import sys


SITE_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')

MEDIA_ROOT = os.path.join(SITE_ROOT, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = MEDIA_URL + 'admin/'

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = False
DATE_FORMAT = 'l, jS F Y'
TIME_FORMAT = 'P'
DATETIME_FORMAT = ', '.join([TIME_FORMAT, DATE_FORMAT])
MONTH_DAY_FORMAT = 'j F'

ROOT_URLCONF = 'flother.urls'

SEND_BROKEN_LINK_EMAILS = True

COMMENTS_HIDE_REMOVED = False

SOUTH_AUTO_FREEZE_APP = True

COMPRESS_VERSION = True
COMPRESS_AUTO = False
COMPRESS_CSS = {
    'flother': {
        'source_filenames': ('core/css/reset.css', 'core/css/structure.css',
            'core/css/typography.css', 'core/css/sections.css'),
        'output_filename': 'core/css/flother.r?.css',
        'extra_context': {
            'media': 'screen,projection',
        },
    },
}
COMPRESS_JS = {}
CSSTIDY_ARGUMENTS = '--preserve_css=true --remove_last_\;=true --lowercase_s=true --sort_properties=true --template=highest'

STATIC_GENERATOR_URLS = (
    r'^/(blog|about)',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.media',
    'flother.apps.blog.context_processors.latest_entries',
    'flother.utils.context_processors.section',
    'flother.utils.context_processors.current_year',
)
TEMPLATE_DIRS = (
    os.path.join(SITE_ROOT, 'templates'),
)
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)
 
MIDDLEWARE_CLASSES = (
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'staticgenerator.middleware.StaticGeneratorMiddleware',
    'flother.utils.middleware.http.SetRemoteAddrFromForwardedFor',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.comments',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.redirects',

    'south',
    'compress',
    'participationgraphs',
    'typogrify',

    'flother.apps.blog',
    'flother.apps.comments',
    'flother.apps.photos',
    'flother.apps.places',
    'flother.apps.files',
    'flother.apps.contact',
    'flother.apps.search',
)

COMMENTS_APP = 'flother.apps.comments'

########NEW FILE########
__FILENAME__ = urls
import datetime

from django.conf import settings
from django.conf.urls.defaults import url, include, patterns, handler404, \
    handler500
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.views.generic.simple import direct_to_template, redirect_to

import flother
from flother.apps.blog.sitemaps import EntrySitemap


sitemaps = {
    'blog': EntrySitemap,
}
admin.autodiscover()


urlpatterns = patterns('',
    (r'^$', redirect_to, {'url': '/blog/', 'permanent': False}),
    (r'^blog/', include('flother.apps.blog.urls')),
    (r'^photos/', include('flother.apps.photos.urls')),
    (r'^contact/', include('flother.apps.contact.urls')),
    (r'^search/', include('flother.apps.search.urls')),
    (r'^comments/', include('django.contrib.comments.urls')),
    url(r'^about/$', direct_to_template, {'template': 'about.html',
        'extra_context': {'birthday': datetime.date(1979, 8, 19),
        'version': flother.version()}}, name='about'),
    (r'^sitemap/$', sitemap, {'sitemaps': sitemaps}),
    (r'^admin/', include(admin.site.urls)),
    (r'^', include('flother.apps.files.urls')),
)


if settings.DEBUG:
    from django.views.static import serve
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', serve, {'document_root':
            settings.MEDIA_ROOT}),
    )

########NEW FILE########
__FILENAME__ = akismet
# Version 0.2.0
# 2009/06/18

# Copyright Michael Foord 2005-2009
# akismet.py
# Python interface to the akismet API
# E-mail fuzzyman@voidspace.org.uk

# http://www.voidspace.org.uk/python/modules.shtml
# http://akismet.com

# Released subject to the BSD License
# See http://www.voidspace.org.uk/python/license.shtml


"""
A python interface to the `Akismet <http://akismet.com>`_ API.
This is a web service for blocking SPAM comments to blogs - or other online 
services.

You will need a Wordpress API key, from `wordpress.com <http://wordpress.com>`_.

You should pass in the keyword argument 'agent' to the name of your program,
when you create an Akismet instance. This sets the ``user-agent`` to a useful
value.

The default is : ::

    Python Interface by Fuzzyman | akismet.py/0.2.0

Whatever you pass in, will replace the *Python Interface by Fuzzyman* part.
**0.2.0** will change with the version of this interface.

Usage example::
    
    from akismet import Akismet
    
    api = Akismet(agent='Test Script')
    # if apikey.txt is in place,
    # the key will automatically be set
    # or you can call api.setAPIKey()
    #
    if api.key is None:
        print "No 'apikey.txt' file."
    elif not api.verify_key():
        print "The API key is invalid."
    else:
        # data should be a dictionary of values
        # They can all be filled in with defaults
        # from a CGI environment
        if api.comment_check(comment, data):
            print 'This comment is spam.'
        else:
            print 'This comment is ham.'
"""


import os, sys
from urllib import urlencode

import socket
if hasattr(socket, 'setdefaulttimeout'):
    # Set the default timeout on sockets to 5 seconds
    socket.setdefaulttimeout(5)

__version__ = '0.2.0'

__all__ = (
    '__version__',
    'Akismet',
    'AkismetError',
    'APIKeyError',
    )

__author__ = 'Michael Foord <fuzzyman AT voidspace DOT org DOT uk>'

__docformat__ = "restructuredtext en"

user_agent = "%s | akismet.py/%s"
DEFAULTAGENT = 'Python Interface by Fuzzyman/%s'

isfile = os.path.isfile

urllib2 = None
try:
    from google.appengine.api import urlfetch
except ImportError:
    import urllib2

if urllib2 is None:
    def _fetch_url(url, data, headers):
        req = urlfetch.fetch(url=url, payload=data, method=urlfetch.POST, headers=headers)
        if req.status_code == 200:
            return req.content
        raise Exception('Could not fetch Akismet URL: %s Response code: %s' % 
                        (url, req.status_code))
else:
    def _fetch_url(url, data, headers):
        req = urllib2.Request(url, data, headers)
        h = urllib2.urlopen(req)
        resp = h.read()
        return resp


class AkismetError(Exception):
    """Base class for all akismet exceptions."""

class APIKeyError(AkismetError):
    """Invalid API key."""

class Akismet(object):
    """A class for working with the akismet API"""

    baseurl = 'rest.akismet.com/1.1/'

    def __init__(self, key=None, blog_url=None, agent=None):
        """Automatically calls ``setAPIKey``."""
        if agent is None:
            agent = DEFAULTAGENT % __version__
        self.user_agent = user_agent % (agent, __version__)
        self.setAPIKey(key, blog_url)


    def _getURL(self):
        """
        Fetch the url to make requests to.
        
        This comprises of api key plus the baseurl.
        """
        return 'http://%s.%s' % (self.key, self.baseurl)
    
    
    def _safeRequest(self, url, data, headers):
        try:
            resp = _fetch_url(url, data, headers)
        except Exception, e:
            raise AkismetError(str(e))
        return resp


    def setAPIKey(self, key=None, blog_url=None):
        """
        Set the wordpress API key for all transactions.
        
        If you don't specify an explicit API ``key`` and ``blog_url`` it will
        attempt to load them from a file called ``apikey.txt`` in the current
        directory.
        
        This method is *usually* called automatically when you create a new
        ``Akismet`` instance.
        """
        if key is None and isfile('apikey.txt'):
            the_file = [l.strip() for l in open('apikey.txt').readlines()
                if l.strip() and not l.strip().startswith('#')]
            try:
                self.key = the_file[0]
                self.blog_url = the_file[1]
            except IndexError:
                raise APIKeyError("Your 'apikey.txt' is invalid.")
        else:
            self.key = key
            self.blog_url = blog_url


    def verify_key(self):
        """
        This equates to the ``verify-key`` call against the akismet API.
        
        It returns ``True`` if the key is valid.
        
        The docs state that you *ought* to call this at the start of the
        transaction.
        
        It raises ``APIKeyError`` if you have not yet set an API key.
        
        If the connection to akismet fails, it allows the normal ``HTTPError``
        or ``URLError`` to be raised.
        (*akismet.py* uses `urllib2 <http://docs.python.org/lib/module-urllib2.html>`_)
        """
        if self.key is None:
            raise APIKeyError("Your have not set an API key.")
        data = { 'key': self.key, 'blog': self.blog_url }
        # this function *doesn't* use the key as part of the URL
        url = 'http://%sverify-key' % self.baseurl
        # we *don't* trap the error here
        # so if akismet is down it will raise an HTTPError or URLError
        headers = {'User-Agent' : self.user_agent}
        resp = self._safeRequest(url, urlencode(data), headers)
        if resp.lower() == 'valid':
            return True
        else:
            return False

    def _build_data(self, comment, data):
        """
        This function builds the data structure required by ``comment_check``,
        ``submit_spam``, and ``submit_ham``.
        
        It modifies the ``data`` dictionary you give it in place. (and so
        doesn't return anything)
        
        It raises an ``AkismetError`` if the user IP or user-agent can't be
        worked out.
        """
        data['comment_content'] = comment
        if not 'user_ip' in data:
            try:
                val = os.environ['REMOTE_ADDR']
            except KeyError:
                raise AkismetError("No 'user_ip' supplied")
            data['user_ip'] = val
        if not 'user_agent' in data:
            try:
                val = os.environ['HTTP_USER_AGENT']
            except KeyError:
                raise AkismetError("No 'user_agent' supplied")
            data['user_agent'] = val
        #
        data.setdefault('referrer', os.environ.get('HTTP_REFERER', 'unknown'))
        data.setdefault('permalink', '')
        data.setdefault('comment_type', 'comment')
        data.setdefault('comment_author', '')
        data.setdefault('comment_author_email', '')
        data.setdefault('comment_author_url', '')
        data.setdefault('SERVER_ADDR', os.environ.get('SERVER_ADDR', ''))
        data.setdefault('SERVER_ADMIN', os.environ.get('SERVER_ADMIN', ''))
        data.setdefault('SERVER_NAME', os.environ.get('SERVER_NAME', ''))
        data.setdefault('SERVER_PORT', os.environ.get('SERVER_PORT', ''))
        data.setdefault('SERVER_SIGNATURE', os.environ.get('SERVER_SIGNATURE',
            ''))
        data.setdefault('SERVER_SOFTWARE', os.environ.get('SERVER_SOFTWARE',
            ''))
        data.setdefault('HTTP_ACCEPT', os.environ.get('HTTP_ACCEPT', ''))
        data.setdefault('blog', self.blog_url)


    def comment_check(self, comment, data=None, build_data=True, DEBUG=False):
        """
        This is the function that checks comments.
        
        It returns ``True`` for spam and ``False`` for ham.
        
        If you set ``DEBUG=True`` then it will return the text of the response,
        instead of the ``True`` or ``False`` object.
        
        It raises ``APIKeyError`` if you have not yet set an API key.
        
        If the connection to Akismet fails then the ``HTTPError`` or
        ``URLError`` will be propogated.
        
        As a minimum it requires the body of the comment. This is the
        ``comment`` argument.
        
        Akismet requires some other arguments, and allows some optional ones.
        The more information you give it, the more likely it is to be able to
        make an accurate diagnosise.
        
        You supply these values using a mapping object (dictionary) as the
        ``data`` argument.
        
        If ``build_data`` is ``True`` (the default), then *akismet.py* will
        attempt to fill in as much information as possible, using default
        values where necessary. This is particularly useful for programs
        running in a {acro;CGI} environment. A lot of useful information
        can be supplied from evironment variables (``os.environ``). See below.
        
        You *only* need supply values for which you don't want defaults filled
        in for. All values must be strings.
        
        There are a few required values. If they are not supplied, and
        defaults can't be worked out, then an ``AkismetError`` is raised.
        
        If you set ``build_data=False`` and a required value is missing an
        ``AkismetError`` will also be raised.
        
        The normal values (and defaults) are as follows : ::
        
            'user_ip':          os.environ['REMOTE_ADDR']       (*)
            'user_agent':       os.environ['HTTP_USER_AGENT']   (*)
            'referrer':         os.environ.get('HTTP_REFERER', 'unknown') [#]_
            'permalink':        ''
            'comment_type':     'comment' [#]_
            'comment_author':   ''
            'comment_author_email': ''
            'comment_author_url': ''
            'SERVER_ADDR':      os.environ.get('SERVER_ADDR', '')
            'SERVER_ADMIN':     os.environ.get('SERVER_ADMIN', '')
            'SERVER_NAME':      os.environ.get('SERVER_NAME', '')
            'SERVER_PORT':      os.environ.get('SERVER_PORT', '')
            'SERVER_SIGNATURE': os.environ.get('SERVER_SIGNATURE', '')
            'SERVER_SOFTWARE':  os.environ.get('SERVER_SOFTWARE', '')
            'HTTP_ACCEPT':      os.environ.get('HTTP_ACCEPT', '')
        
        (*) Required values
        
        You may supply as many additional 'HTTP_*' type values as you wish.
        These should correspond to the http headers sent with the request.
        
        .. [#] Note the spelling "referrer". This is a required value by the
            akismet api - however, referrer information is not always
            supplied by the browser or server. In fact the HTTP protocol
            forbids relying on referrer information for functionality in 
            programs.
        .. [#] The `API docs <http://akismet.com/development/api/>`_ state that this value
            can be " *blank, comment, trackback, pingback, or a made up value*
            *like 'registration'* ".
        """
        if self.key is None:
            raise APIKeyError("Your have not set an API key.")
        if data is None:
            data = {}
        if build_data:
            self._build_data(comment, data)
        if 'blog' not in data:
            data['blog'] = self.blog_url
        url = '%scomment-check' % self._getURL()
        # we *don't* trap the error here
        # so if akismet is down it will raise an HTTPError or URLError
        headers = {'User-Agent' : self.user_agent}
        resp = self._safeRequest(url, urlencode(data), headers)
        if DEBUG:
            return resp
        resp = resp.lower()
        if resp == 'true':
            return True
        elif resp == 'false':
            return False
        else:
            # NOTE: Happens when you get a 'howdy wilbur' response !
            raise AkismetError('missing required argument.')


    def submit_spam(self, comment, data=None, build_data=True):
        """
        This function is used to tell akismet that a comment it marked as ham,
        is really spam.
        
        It takes all the same arguments as ``comment_check``, except for
        *DEBUG*.
        """
        if self.key is None:
            raise APIKeyError("Your have not set an API key.")
        if data is None:
            data = {}
        if build_data:
            self._build_data(comment, data)
        url = '%ssubmit-spam' % self._getURL()
        # we *don't* trap the error here
        # so if akismet is down it will raise an HTTPError or URLError
        headers = {'User-Agent' : self.user_agent}
        self._safeRequest(url, urlencode(data), headers)


    def submit_ham(self, comment, data=None, build_data=True):
        """
        This function is used to tell akismet that a comment it marked as spam,
        is really ham.
        
        It takes all the same arguments as ``comment_check``, except for
        *DEBUG*.
        """
        if self.key is None:
            raise APIKeyError("Your have not set an API key.")
        if data is None:
            data = {}
        if build_data:
            self._build_data(comment, data)
        url = '%ssubmit-ham' % self._getURL()
        # we *don't* trap the error here
        # so if akismet is down it will raise an HTTPError or URLError
        headers = {'User-Agent' : self.user_agent}
        self._safeRequest(url, urlencode(data), headers)

########NEW FILE########
__FILENAME__ = timeoutsocket

####
# Copyright 2000,2001 by Timothy O'Malley <timo@alum.mit.edu>
# 
#                All Rights Reserved
# 
# Permission to use, copy, modify, and distribute this software
# and its documentation for any purpose and without fee is hereby
# granted, provided that the above copyright notice appear in all
# copies and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Timothy O'Malley  not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission. 
# 
# Timothy O'Malley DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS, IN NO EVENT SHALL Timothy O'Malley BE LIABLE FOR
# ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE. 
#
####

"""Timeout Socket

This module enables a timeout mechanism on all TCP connections.  It
does this by inserting a shim into the socket module.  After this module
has been imported, all socket creation goes through this shim.  As a
result, every TCP connection will support a timeout.

The beauty of this method is that it immediately and transparently
enables the entire python library to support timeouts on TCP sockets.
As an example, if you wanted to SMTP connections to have a 20 second
timeout:

    import timeoutsocket
    import smtplib
    timeoutsocket.setDefaultSocketTimeout(20)


The timeout applies to the socket functions that normally block on
execution:  read, write, connect, and accept.  If any of these 
operations exceeds the specified timeout, the exception Timeout
will be raised.

The default timeout value is set to None.  As a result, importing
this module does not change the default behavior of a socket.  The
timeout mechanism only activates when the timeout has been set to
a numeric value.  (This behavior mimics the behavior of the
select.select() function.)

This module implements two classes: TimeoutSocket and TimeoutFile.

The TimeoutSocket class defines a socket-like object that attempts to
avoid the condition where a socket may block indefinitely.  The
TimeoutSocket class raises a Timeout exception whenever the
current operation delays too long. 

The TimeoutFile class defines a file-like object that uses the TimeoutSocket
class.  When the makefile() method of TimeoutSocket is called, it returns
an instance of a TimeoutFile.

Each of these objects adds two methods to manage the timeout value:

    get_timeout()   -->  returns the timeout of the socket or file
    set_timeout()   -->  sets the timeout of the socket or file


As an example, one might use the timeout feature to create httplib
connections that will timeout after 30 seconds:

    import timeoutsocket
    import httplib
    H = httplib.HTTP("www.python.org")
    H.sock.set_timeout(30)

Note:  When used in this manner, the connect() routine may still
block because it happens before the timeout is set.  To avoid
this, use the 'timeoutsocket.setDefaultSocketTimeout()' function.

Good Luck!

"""

__version__ = "$Revision: 1.23 $"
__author__  = "Timothy O'Malley <timo@alum.mit.edu>"

#
# Imports
#
import select, string
import socket
if not hasattr(socket, "_no_timeoutsocket"):
    _socket = socket.socket
else:
    _socket = socket._no_timeoutsocket


#
# Set up constants to test for Connected and Blocking operations.
# We delete 'os' and 'errno' to keep our namespace clean(er).
# Thanks to Alex Martelli and G. Li for the Windows error codes.
#
import os
if os.name == "nt":
    _IsConnected = ( 10022, 10056 )
    _ConnectBusy = ( 10035, )
    _AcceptBusy  = ( 10035, )
else:
    import errno
    _IsConnected = ( errno.EISCONN, )
    _ConnectBusy = ( errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK )
    _AcceptBusy  = ( errno.EAGAIN, errno.EWOULDBLOCK )
    del errno
del os


#
# Default timeout value for ALL TimeoutSockets
#
_DefaultTimeout = None
def setDefaultSocketTimeout(timeout):
    global _DefaultTimeout
    _DefaultTimeout = timeout
def getDefaultSocketTimeout():
    return _DefaultTimeout

#
# Exceptions for socket errors and timeouts
#
Error = socket.error
class Timeout(Exception):
    pass


#
# Factory function
#
from socket import AF_INET, SOCK_STREAM
def timeoutsocket(family=AF_INET, type=SOCK_STREAM, proto=None):
    if family != AF_INET or type != SOCK_STREAM:
        if proto:
            return _socket(family, type, proto)
        else:
            return _socket(family, type)
    return TimeoutSocket( _socket(family, type), _DefaultTimeout )
# end timeoutsocket

#
# The TimeoutSocket class definition
#
class TimeoutSocket:
    """TimeoutSocket object
    Implements a socket-like object that raises Timeout whenever
    an operation takes too long.
    The definition of 'too long' can be changed using the
    set_timeout() method.
    """

    _copies = 0
    _blocking = 1
    
    def __init__(self, sock, timeout):
        self._sock     = sock
        self._timeout  = timeout
    # end __init__

    def __getattr__(self, key):
        return getattr(self._sock, key)
    # end __getattr__

    def get_timeout(self):
        return self._timeout
    # end set_timeout

    def set_timeout(self, timeout=None):
        self._timeout = timeout
    # end set_timeout

    def setblocking(self, blocking):
        self._blocking = blocking
        return self._sock.setblocking(blocking)
    # end set_timeout

    def connect_ex(self, addr):
        errcode = 0
        try:
            self.connect(addr)
        except Error, why:
            errcode = why[0]
        return errcode
    # end connect_ex
        
    def connect(self, addr, port=None, dumbhack=None):
        # In case we were called as connect(host, port)
        if port != None:  addr = (addr, port)

        # Shortcuts
        sock    = self._sock
        timeout = self._timeout
        blocking = self._blocking

        # First, make a non-blocking call to connect
        try:
            sock.setblocking(0)
            sock.connect(addr)
            sock.setblocking(blocking)
            return
        except Error, why:
            # Set the socket's blocking mode back
            sock.setblocking(blocking)
            
            # If we are not blocking, re-raise
            if not blocking:
                raise
            
            # If we are already connected, then return success.
            # If we got a genuine error, re-raise it.
            errcode = why[0]
            if dumbhack and errcode in _IsConnected:
                return
            elif errcode not in _ConnectBusy:
                raise
            
        # Now, wait for the connect to happen
        # ONLY if dumbhack indicates this is pass number one.
        #   If select raises an error, we pass it on.
        #   Is this the right behavior?
        if not dumbhack:
            r,w,e = select.select([], [sock], [], timeout)
            if w:
                return self.connect(addr, dumbhack=1)

        # If we get here, then we should raise Timeout
        raise Timeout("Attempted connect to %s timed out." % str(addr) )
    # end connect

    def accept(self, dumbhack=None):
        # Shortcuts
        sock     = self._sock
        timeout  = self._timeout
        blocking = self._blocking

        # First, make a non-blocking call to accept
        #  If we get a valid result, then convert the
        #  accept'ed socket into a TimeoutSocket.
        # Be carefult about the blocking mode of ourselves.
        try:
            sock.setblocking(0)
            newsock, addr = sock.accept()
            sock.setblocking(blocking)
            timeoutnewsock = self.__class__(newsock, timeout)
            timeoutnewsock.setblocking(blocking)
            return (timeoutnewsock, addr)
        except Error, why:
            # Set the socket's blocking mode back
            sock.setblocking(blocking)

            # If we are not supposed to block, then re-raise
            if not blocking:
                raise
            
            # If we got a genuine error, re-raise it.
            errcode = why[0]
            if errcode not in _AcceptBusy:
                raise
            
        # Now, wait for the accept to happen
        # ONLY if dumbhack indicates this is pass number one.
        #   If select raises an error, we pass it on.
        #   Is this the right behavior?
        if not dumbhack:
            r,w,e = select.select([sock], [], [], timeout)
            if r:
                return self.accept(dumbhack=1)

        # If we get here, then we should raise Timeout
        raise Timeout("Attempted accept timed out.")
    # end accept

    def send(self, data, flags=0):
        sock = self._sock
        if self._blocking:
            r,w,e = select.select([],[sock],[], self._timeout)
            if not w:
                raise Timeout("Send timed out")
        return sock.send(data, flags)
    # end send

    def recv(self, bufsize, flags=0):
        sock = self._sock
        if self._blocking:
            r,w,e = select.select([sock], [], [], self._timeout)
            if not r:
                raise Timeout("Recv timed out")
        return sock.recv(bufsize, flags)
    # end recv

    def makefile(self, flags="r", bufsize=-1):
        self._copies = self._copies +1
        return TimeoutFile(self, flags, bufsize)
    # end makefile

    def close(self):
        if self._copies <= 0:
            self._sock.close()
        else:
            self._copies = self._copies -1
    # end close

# end TimeoutSocket


class TimeoutFile:
    """TimeoutFile object
    Implements a file-like object on top of TimeoutSocket.
    """
    
    def __init__(self, sock, mode="r", bufsize=4096):
        self._sock          = sock
        self._bufsize       = 4096
        if bufsize > 0: self._bufsize = bufsize
        if not hasattr(sock, "_inqueue"): self._sock._inqueue = ""

    # end __init__

    def __getattr__(self, key):
        return getattr(self._sock, key)
    # end __getattr__

    def close(self):
        self._sock.close()
        self._sock = None
    # end close
    
    def write(self, data):
        self.send(data)
    # end write

    def read(self, size=-1):
        _sock = self._sock
        _bufsize = self._bufsize
        while 1:
            datalen = len(_sock._inqueue)
            if datalen >= size >= 0:
                break
            bufsize = _bufsize
            if size > 0:
                bufsize = min(bufsize, size - datalen )
            buf = self.recv(bufsize)
            if not buf:
                break
            _sock._inqueue = _sock._inqueue + buf
        data = _sock._inqueue
        _sock._inqueue = ""
        if size > 0 and datalen > size:
            _sock._inqueue = data[size:]
            data = data[:size]
        return data
    # end read

    def readline(self, size=-1):
        _sock = self._sock
        _bufsize = self._bufsize
        while 1:
            idx = string.find(_sock._inqueue, "\n")
            if idx >= 0:
                break
            datalen = len(_sock._inqueue)
            if datalen >= size >= 0:
                break
            bufsize = _bufsize
            if size > 0:
                bufsize = min(bufsize, size - datalen )
            buf = self.recv(bufsize)
            if not buf:
                break
            _sock._inqueue = _sock._inqueue + buf

        data = _sock._inqueue
        _sock._inqueue = ""
        if idx >= 0:
            idx = idx + 1
            _sock._inqueue = data[idx:]
            data = data[:idx]
        elif size > 0 and datalen > size:
            _sock._inqueue = data[size:]
            data = data[:size]
        return data
    # end readline

    def readlines(self, sizehint=-1):
        result = []
        data = self.read()
        while data:
            idx = string.find(data, "\n")
            if idx >= 0:
                idx = idx + 1
                result.append( data[:idx] )
                data = data[idx:]
            else:
                result.append( data )
                data = ""
        return result
    # end readlines

    def flush(self):  pass

# end TimeoutFile


#
# Silently replace the socket() builtin function with
# our timeoutsocket() definition.
#
if not hasattr(socket, "_no_timeoutsocket"):
    socket._no_timeoutsocket = socket.socket
    socket.socket = timeoutsocket
del socket
socket = timeoutsocket
# Finis

########NEW FILE########
__FILENAME__ = image
from PIL.Image import ANTIALIAS


def create_thumbnail(im, size, image_filter=ANTIALIAS):
    """
    Modify the given image to be a thumbnail of exactly the size given.
    This is different to the built-in im.thumbnail() method, which only
    approximates the thumbnail size.
    """
    input_image_size = float(im.size[0]), float(im.size[1])
    input_aspect_ratio = input_image_size[0] / input_image_size[1]
    output_aspect_ratio = float(size[0]) / float(size[1])

    # Work out what to crop to fit the image into the new dimensions.
    if input_aspect_ratio >= output_aspect_ratio:
        # Input image is wider than required; crop the sides.
        crop_width = int(output_aspect_ratio * input_image_size[1] + 0.5)
        crop_height = int(input_image_size[1])
    else:
        # Input image taller than required; crop the top and bottom.
        crop_width = int(input_image_size[0])
        crop_height = int(input_image_size[0] / output_aspect_ratio + 0.5)

    # Crop the image.
    left_side = int((input_image_size[0] - crop_width) * 0.50)
    if left_side < 0:
        left_side = 0
    top_side = int((input_image_size[1] - crop_height) * 0.50)
    if top_side < 0:
        top_side = 0
    output_image = im.crop((left_side, top_side, left_side + crop_width,
        top_side + crop_height))

    return output_image.resize(size, image_filter)

########NEW FILE########
__FILENAME__ = http
class SetRemoteAddrFromForwardedFor(object):
    """
    Middleware that sets REMOTE_ADDR based on HTTP_X_FORWARDED_FOR, if
    the latter is set. This is useful if you're sitting behind a reverse
    proxy that causes each request's REMOTE_ADDR to be set to 127.0.0.1.

    Note that this does NOT validate HTTP_X_FORWARDED_FOR. If you're not
    behind a reverse proxy that sets HTTP_X_FORWARDED_FOR automatically,
    do not use this middleware. Anybody can spoof the value of
    HTTP_X_FORWARDED_FOR, and because this sets REMOTE_ADDR based on
    HTTP_X_FORWARDED_FOR, that means anybody can "fake" their IP
    address. Only use this when you can absolutely trust the value of
    HTTP_X_FORWARDED_FOR.

    This is a copy of the middleware that was removed from Django 1.1.
    See the following for details:

    http://code.djangoproject.com/browser/django/trunk/django/middleware/http.py?rev=11000#L33
    http://code.djangoproject.com/browser/django/trunk/django/middleware/http.py
    http://docs.djangoproject.com/en/dev/releases/1.1/#id1
    """
    def process_request(self, request):
        try:
            real_ip = request.META['HTTP_X_FORWARDED_FOR']
        except KeyError:
            return None
        else:
            # HTTP_X_FORWARDED_FOR can be a comma-separated list of IPs. The
            # client's IP will be the first one.
            real_ip = real_ip.split(",")[0].strip()
            request.META['REMOTE_ADDR'] = real_ip
########NEW FILE########
