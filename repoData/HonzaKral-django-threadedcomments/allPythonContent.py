__FILENAME__ = conf
extensions = ['sphinx.ext.autodoc']
templates_path = ['.templates']
source_suffix = '.txt'
master_doc = 'index'

# General information about the project.
project = u'Django threaded comments'


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from .models import Message


class MessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'text',)

admin.site.register(Message, MessageAdmin)

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db import models

class Message(models.Model):
    title   = models.CharField(max_length=140)
    text    = models.TextField()

    class Meta:
        verbose_name = "message"
        verbose_name_plural = "messages"

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('message_detail', args=(self.pk,))

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.views.decorators.csrf import csrf_protect
from .models import Message


def home(request):
    context = {
        'messages': Message.objects.all(),
    }
    return render_to_response('core/home.html', context, context_instance=RequestContext(request))


@csrf_protect
def message(request, id):
    context = {
        'message': get_object_or_404(Message, pk=id),
    }
    return render_to_response('core/message.html', context, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.
#
# These settings are pretty basic.
# The only relevent settings are the defaults are:
# - INSTALLED_APPS
# - COMMENTS_APP
#
# And the following are configured to sane defaults:
# - TEMPLATE_CONTEXT_PROCESSORS
# - STATIC_ROOT / STATIC_URL
# - MEDIA_ROOT / MEDIA_URL
#
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

#DEFAULT_FROM_EMAIL = 'your_email@domain.com'

# People who receive 404 errors
MANAGERS = ADMINS


## -- Server specific settings

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'sampledb.db'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}


# Make this unique, and don't share it with anybody.
SECRET_KEY = 'sfm=0t(!sqi&!y%66+e+#4m$1o&l%(l(w#vz$=_0c$5+#m*9yk'
SITE_ID = 1


## -- Internal Django config

# Language codes
TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Paths, using autodetection
PROJECT_DIR  = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')
STATIC_URL = '/static/'

ROOT_URLCONF = 'example.urls'

# Only included for Django 1.3 users:
ADMIN_MEDIA_PREFIX = '/static/admin/'


## -- Plugin components

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',    # Very useful to have, not found in default Django setup.
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

STATICFILES_DIRS = ()

TEMPLATE_DIRS = ()

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    # Messages setup:
    'core',
    'threadedcomments',
    'django.contrib.comments',
)


## --- App settings

COMMENTS_APP = 'threadedcomments'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin

# Enable the admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^comments/', include('django.contrib.comments.urls')),

    url(r'^$', 'core.views.home', name='homepage'),
    url(r'^message/(?P<id>.+)$', 'core.views.message', name='message_detail'),
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys
sys.path.insert(0, os.path.realpath("../"))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.comments.admin import CommentsAdmin

from threadedcomments.models import ThreadedComment

class ThreadedCommentsAdmin(CommentsAdmin):
    fieldsets = (
        (None,
           {'fields': ('content_type', 'object_pk', 'site')}
        ),
        (_('Content'),
           {'fields': ('user', 'user_name', 'user_email', 'user_url', 'title', 'comment')}
        ),
        (_('Hierarchy'),
           {'fields': ('parent',)}
        ),
        (_('Metadata'),
           {'fields': ('submit_date', 'ip_address', 'is_public', 'is_removed')}
        ),
    )

    list_display = ('name', 'title', 'content_type', 'object_pk', 'parent',
                    'ip_address', 'submit_date', 'is_public', 'is_removed')
    search_fields = ('title', 'comment', 'user__username', 'user_name',
                     'user_email', 'user_url', 'ip_address')
    raw_id_fields = ("parent",)

admin.site.register(ThreadedComment, ThreadedCommentsAdmin)


########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.comments.forms import CommentForm
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from threadedcomments.models import ThreadedComment

class ThreadedCommentForm(CommentForm):
    parent = forms.IntegerField(required=False, widget=forms.HiddenInput)

    def __init__(self, target_object, parent=None, data=None, initial=None):
        self.base_fields.insert(
            self.base_fields.keyOrder.index('comment'), 'title',
            forms.CharField(label=_('Title'), required=False, max_length=getattr(settings, 'COMMENTS_TITLE_MAX_LENGTH', 255))
        )
        self.parent = parent
        if initial is None:
            initial = {}
        initial.update({'parent': self.parent})
        super(ThreadedCommentForm, self).__init__(target_object, data=data, initial=initial)

    def get_comment_model(self):
        return ThreadedComment

    def get_comment_create_data(self):
        d = super(ThreadedCommentForm, self).get_comment_create_data()
        d['parent_id'] = self.cleaned_data['parent']
        d['title'] = self.cleaned_data['title']
        return d


########NEW FILE########
__FILENAME__ = migrate_comments
from django.core.management.base import NoArgsCommand
from django.db import transaction, connection
from django.conf import settings

PATH_DIGITS = getattr(settings, 'COMMENT_PATH_DIGITS', 10)

SQL = """
INSERT INTO threadedcomments_comment (
    comment_ptr_id, 
    parent_id, 
    last_child_id, 
    tree_path,
    title
) 
SELECT id as comment_ptr_id, 
       null as parent_id, 
       null as last_child_id, 
       (SELECT TO_CHAR(id, '%s')) AS tree_path,
       ''
FROM django_comments;
""" % ''.zfill(PATH_DIGITS)

class Command(NoArgsCommand):
    help = "Migrates from django.contrib.comments to django-threadedcomments"

    def handle(self, *args, **options):
        transaction.commit_unless_managed()
        transaction.enter_transaction_management()
        transaction.managed(True)

        cursor = connection.cursor()

        cursor.execute(SQL)

        transaction.commit()
        transaction.leave_transaction_management()

########NEW FILE########
__FILENAME__ = migrate_threaded_comments
from django.core.management.base import NoArgsCommand
from django.contrib.sites.models import Site
from django.db import transaction, connection
from django.conf import settings

from threadedcomments.models import ThreadedComment

USER_SQL = """
SELECT
    id,
    content_type_id,
    object_id,
    parent_id,
    user_id,
    date_submitted,
    date_modified,
    date_approved,
    comment,
    markup,
    is_public,
    is_approved,
    ip_address
FROM threadedcomments_threadedcomment ORDER BY id ASC
"""

FREE_SQL = """
SELECT
    id,
    content_type_id,
    object_id,
    parent_id,
    name,
    website,
    email,
    date_submitted,
    date_modified,
    date_approved,
    comment,
    markup,
    is_public,
    is_approved,
    ip_address
FROM threadedcomments_freethreadedcomment ORDER BY id ASC
"""

PATH_SEPARATOR = getattr(settings, 'COMMENT_PATH_SEPARATOR', '/')
PATH_DIGITS = getattr(settings, 'COMMENT_PATH_DIGITS', 10)

class Command(NoArgsCommand):
    help = "Migrates django-threadedcomments <= 0.5 to the new model structure"

    def handle(self, *args, **options):
        transaction.commit_unless_managed()
        transaction.enter_transaction_management()
        transaction.managed(True)

        site = Site.objects.all()[0]

        cursor = connection.cursor()
        cursor.execute(FREE_SQL)
        for row in cursor:
            (id, content_type_id, object_id, parent_id, name, website, email,
                date_submitted, date_modified, date_approved, comment, markup,
                is_public, is_approved, ip_address) = row
            tc = ThreadedComment(
                pk=id,
                content_type_id=content_type_id,
                object_pk=object_id,
                user_name=name,
                user_email=email,
                user_url=website,
                comment=comment,
                submit_date=date_submitted,
                ip_address=ip_address,
                is_public=is_public,
                is_removed=not is_approved,
                parent_id=parent_id,
                site=site,
            )

            tc.save(skip_tree_path=True)

        cursor = connection.cursor()
        cursor.execute(USER_SQL)
        for row in cursor:
            (id, content_type_id, object_id, parent_id, user_id, date_submitted,
                date_modified, date_approved, comment, markup, is_public,
                is_approved, ip_address) = row
            tc = ThreadedComment(
                pk=id,
                content_type_id=content_type_id,
                object_pk=object_id,
                user_id=user_id,
                comment=comment,
                submit_date=date_submitted,
                ip_address=ip_address,
                is_public=is_public,
                is_removed=not is_approved,
                parent_id=parent_id,
                site=site,
            )

            tc.save(skip_tree_path=True)

        for comment in ThreadedComment.objects.all():
            path = [str(comment.id).zfill(PATH_DIGITS)]
            current = comment
            while current.parent:
                current = current.parent
                path.append(str(current.id).zfill(PATH_DIGITS))
            comment.tree_path = PATH_SEPARATOR.join(reversed(path))
            comment.save(skip_tree_path=True)
            if comment.parent:
                ThreadedComment.objects.filter(pk=comment.parent.pk).update(
                    last_child=comment)

        transaction.commit()
        transaction.leave_transaction_management()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ThreadedComment'
        db.create_table('threadedcomments_comment', (
            ('comment_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['comments.Comment'], unique=True, primary_key=True)),
            ('title', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='children', null=True, blank=True, to=orm['threadedcomments.ThreadedComment'])),
            ('last_child', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['threadedcomments.ThreadedComment'], null=True, blank=True)),
            ('tree_path', self.gf('django.db.models.fields.TextField')(db_index=True)),
        ))
        db.send_create_signal('threadedcomments', ['ThreadedComment'])

    def backwards(self, orm):
        # Deleting model 'ThreadedComment'
        db.delete_table('threadedcomments_comment')

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
        'comments.comment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'Comment', 'db_table': "'django_comments'"},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '3000'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'content_type_set_for_comment'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_pk': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'comment_comments'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'user_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'user_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'threadedcomments.threadedcomment': {
            'Meta': {'ordering': "('tree_path',)", 'object_name': 'ThreadedComment', 'db_table': "'threadedcomments_comment'", '_ormbases': ['comments.Comment']},
            'comment_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['comments.Comment']", 'unique': 'True', 'primary_key': 'True'}),
            'last_child': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['threadedcomments.ThreadedComment']", 'null': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'children'", 'null': 'True', 'blank': 'True', 'to': "orm['threadedcomments.ThreadedComment']"}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'tree_path': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['threadedcomments']
########NEW FILE########
__FILENAME__ = 0002_set__last_child_id__on_delete__set_null
# -*- coding: utf-8 -*-
import datetime
import south
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'ThreadedComment.last_child'
        db.alter_column('threadedcomments_comment', 'last_child_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['threadedcomments.ThreadedComment'], null=True, on_delete=models.SET_NULL))
        if south.__version__ <= "0.7.4" and not db.dry_run:
            print " * WARNING: Your South version is not able to add ON DELETE SET NULL. Please fix this manually."

    def backwards(self, orm):

        # Changing field 'ThreadedComment.last_child'
        db.alter_column('threadedcomments_comment', 'last_child_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['threadedcomments.ThreadedComment'], null=True))

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
        'comments.comment': {
            'Meta': {'ordering': "('submit_date',)", 'object_name': 'Comment', 'db_table': "'django_comments'"},
            'comment': ('django.db.models.fields.TextField', [], {'max_length': '3000'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'content_type_set_for_comment'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_removed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'object_pk': ('django.db.models.fields.TextField', [], {}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'submit_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'comment_comments'", 'null': 'True', 'to': "orm['auth.User']"}),
            'user_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'user_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'user_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'threadedcomments.threadedcomment': {
            'Meta': {'ordering': "('tree_path',)", 'object_name': 'ThreadedComment', 'db_table': "'threadedcomments_comment'", '_ormbases': ['comments.Comment']},
            'comment_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['comments.Comment']", 'unique': 'True', 'primary_key': 'True'}),
            'last_child': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['threadedcomments.ThreadedComment']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'children'", 'null': 'True', 'blank': 'True', 'to': "orm['threadedcomments.ThreadedComment']"}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'tree_path': ('django.db.models.fields.TextField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['threadedcomments']
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.comments.models import Comment
from django.contrib.comments.managers import CommentManager
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

PATH_SEPARATOR = getattr(settings, 'COMMENT_PATH_SEPARATOR', '/')
PATH_DIGITS = getattr(settings, 'COMMENT_PATH_DIGITS', 10)

class ThreadedComment(Comment):
    title = models.TextField(_('Title'), blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, default=None, related_name='children', verbose_name=_('Parent'))
    last_child = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('Last child'))
    tree_path = models.TextField(_('Tree path'), editable=False, db_index=True)

    objects = CommentManager()

    @property
    def depth(self):
        return len(self.tree_path.split(PATH_SEPARATOR))

    @property
    def root_id(self):
        return int(self.tree_path.split(PATH_SEPARATOR)[0])

    @property
    def root_path(self):
        return ThreadedComment.objects.filter(pk__in=self.tree_path.split(PATH_SEPARATOR)[:-1])

    def save(self, *args, **kwargs):
        skip_tree_path = kwargs.pop('skip_tree_path', False)
        super(ThreadedComment, self).save(*args, **kwargs)
        if skip_tree_path:
            return None

        tree_path = unicode(self.pk).zfill(PATH_DIGITS)
        if self.parent:
            tree_path = PATH_SEPARATOR.join((self.parent.tree_path, tree_path))

            self.parent.last_child = self
            ThreadedComment.objects.filter(pk=self.parent_id).update(last_child=self)

        self.tree_path = tree_path
        ThreadedComment.objects.filter(pk=self.pk).update(tree_path=self.tree_path)

    def delete(self, *args, **kwargs):
        # Fix last child on deletion.
        if self.parent_id:
            try:
                prev_child_id = ThreadedComment.objects \
                                .filter(parent=self.parent_id) \
                                .exclude(pk=self.pk) \
                                .order_by('-submit_date') \
                                .values_list('pk', flat=True)[0]
            except IndexError:
                prev_child_id = None
            ThreadedComment.objects.filter(pk=self.parent_id).update(last_child=prev_child_id)
        super(ThreadedComment, self).delete(*args, **kwargs)

    class Meta(object):
        ordering = ('tree_path',)
        db_table = 'threadedcomments_comment'
        verbose_name = _('Threaded comment')
        verbose_name_plural = _('Threaded comments')

########NEW FILE########
__FILENAME__ = threadedcomments_tags
from django import template
from django.template.loader import render_to_string
from django.contrib.comments.templatetags.comments import BaseCommentNode
from django.contrib import comments
from threadedcomments.util import annotate_tree_properties, fill_tree as real_fill_tree

register = template.Library()

class BaseThreadedCommentNode(BaseCommentNode):
    def __init__(self, parent=None, flat=False, root_only=False, **kwargs):
        self.parent = parent
        self.flat = flat
        self.root_only = root_only
        super(BaseThreadedCommentNode, self).__init__(**kwargs)

    @classmethod
    def handle_token(cls, parser, token):
        tokens = token.contents.split()
        if len(tokens) > 2:
            if tokens[1] != 'for':
                raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        extra_kw = {}
        if tokens[-1] in ('flat', 'root_only'):
            extra_kw[str(tokens.pop())] = True

        if len(tokens) == 5:
            # {% get_whatever for obj as varname %}
            if tokens[3] != 'as':
                raise template.TemplateSyntaxError("Fourth argument in %r must be 'as'" % tokens[0])

            return cls(
                object_expr=parser.compile_filter(tokens[2]),
                as_varname=tokens[4],
                **extra_kw
            )
        elif len(tokens) == 6:
            # {% get_whatever for app.model pk as varname %}
            if tokens[4] != 'as':
                raise template.TemplateSyntaxError("Fourth argument in %r must be 'as'" % tokens[0])

            return cls(
                ctype=BaseThreadedCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3]),
                as_varname=tokens[5],
                **extra_kw
            )
        else:
            raise template.TemplateSyntaxError("%r tag takes either 5 or 6 arguments" % (tokens[0],))

    def get_query_set(self, context):
        qs = super(BaseThreadedCommentNode, self).get_query_set(context)
        if self.flat:
            qs = qs.order_by('-submit_date')
        elif self.root_only:
            qs = qs.exclude(parent__isnull=False).order_by('-submit_date')
        return qs


class CommentListNode(BaseThreadedCommentNode):
    """
    Insert a list of comments into the context.
    """
    def get_context_value_from_queryset(self, context, qs):
        return list(qs)


class CommentCountNode(CommentListNode):
    """
    Insert a count of comments into the context.
    """
    def get_context_value_from_queryset(self, context, qs):
        return qs.count()


class CommentFormNode(BaseThreadedCommentNode):
    """
    Insert a form for the comment model into the context.
    """
    @classmethod
    def handle_token(cls, parser, token):
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % (tokens[0],))

        if len(tokens) < 7:
            # Default get_comment_form code
            return super(CommentFormNode, cls).handle_token(parser, token)
        elif len(tokens) == 7:
            # {% get_comment_form for [object] as [varname] with [parent_id] %}
            if tokens[-2] != u'with':
                raise template.TemplateSyntaxError("%r tag must have a 'with' as the last but one argument." % (tokens[0],))
            return cls(
                object_expr=parser.compile_filter(tokens[2]),
                as_varname=tokens[4],
                parent=parser.compile_filter(tokens[6]),
            )
        elif len(tokens) == 8:
            # {% get_comment_form for [app].[model] [object_id] as [varname] with [parent_id] %}
            if tokens[-2] != u'with':
                raise template.TemplateSyntaxError("%r tag must have a 'with' as the last but one argument." % (tokens[0],))
            return cls(
                ctype=BaseThreadedCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3]),
                as_varname=tokens[5],
                parent=parser.compile_filter(tokens[7]),
            )

    def get_form(self, context):
        parent_id = None
        if self.parent:
            parent_id = self.parent.resolve(context, ignore_failures=True)

        obj = self.get_object(context)
        if obj:
            return comments.get_form()(obj, parent=parent_id)
        else:
            return None

    def get_object(self, context):
        if self.object_expr:
            try:
                return self.object_expr.resolve(context)
            except template.VariableDoesNotExist:
                return None
        else:
            object_pk = self.object_pk_expr.resolve(context, ignore_failures=True)
            return self.ctype.get_object_for_this_type(pk=object_pk)

    def render(self, context):
        context[self.as_varname] = self.get_form(context)
        return ''


class RenderCommentFormNode(CommentFormNode):
    @classmethod
    def handle_token(cls, parser, token):
        """
        Class method to parse render_comment_form and return a Node.
        """
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        if len(tokens) == 3:
            # {% render_comment_form for obj %}
            return cls(object_expr=parser.compile_filter(tokens[2]))
        elif len(tokens) == 4:
            # {% render_comment_form for app.model object_pk %}
            return cls(
                ctype=BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3])
            )
        elif len(tokens) == 5:
            # {% render_comment_form for obj with parent_id %}
            if tokens[-2] != u'with':
                raise template.TemplateSyntaxError("%r tag must have 'with' as the last but one argument" % (tokens[0],))
            return cls(
                object_expr=parser.compile_filter(tokens[2]),
                parent=parser.compile_filter(tokens[4])
            )
        elif len(tokens) == 6:
            # {% render_comment_form for app.model object_pk with parent_id %}
            if tokens[-2] != u'with':
                raise template.TemplateSyntaxError("%r tag must have 'with' as the last but one argument" % (tokens[0],))
            return cls(
                ctype=BaseThreadedCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3]),
                parent=parser.compile_filter(tokens[5])
            )
        else:
            raise template.TemplateSyntaxError("%r tag takes 2 to 5 arguments" % (tokens[0],))

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = (
                "comments/%s/%s/form.html" % (ctype.app_label, ctype.model),
                "comments/%s/form.html" % ctype.app_label,
                "comments/form.html",
            )
            context.push()
            form_str = render_to_string(
                template_search_list,
                {"form" : self.get_form(context)},
                context
            )
            context.pop()
            return form_str
        else:
            return ''


class RenderCommentListNode(CommentListNode):
    """
    Render the comments list.
    """
    # By having this class added, this module is a drop-in replacement for ``{% load comments %}``.

    @classmethod
    def handle_token(cls, parser, token):
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        extra_kw = {}
        if tokens[-1] in ('flat', 'root_only'):
            extra_kw[str(tokens.pop())] = True

        if len(tokens) == 3:
            # {% render_comment_list for obj %}
            return cls(
                object_expr=parser.compile_filter(tokens[2]),
                **extra_kw
            )
        elif len(tokens) == 4:
            # {% render_comment_list for app.models pk %}
            return cls(
                ctype = BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr = parser.compile_filter(tokens[3]),
                **extra_kw
            )
        else:
            raise template.TemplateSyntaxError("%r tag takes either 2 or 3 arguments" % (tokens[0],))

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "comments/%s/%s/list.html" % (ctype.app_label, ctype.model),
                "comments/%s/list.html" % ctype.app_label,
                "comments/list.html"
            ]
            qs = self.get_query_set(context)
            context.push()
            liststr = render_to_string(template_search_list, {
                "comment_list" : self.get_context_value_from_queryset(context, qs)
            }, context)
            context.pop()
            return liststr
        else:
            return ''


@register.tag
def get_comment_count(parser, token):
    """
    Gets the comment count for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_comment_count for [object] as [varname]  %}
        {% get_comment_count for [app].[model] [object_id] as [varname]  %}

    Example usage::

        {% get_comment_count for event as comment_count %}
        {% get_comment_count for calendar.event event.id as comment_count %}
        {% get_comment_count for calendar.event 17 as comment_count %}

    """
    return CommentCountNode.handle_token(parser, token)


@register.tag
def get_comment_list(parser, token):
    """
    Gets the list of comments for the given params and populates the template
    context with a variable containing that value, whose name is defined by the
    'as' clause.

    Syntax::

        {% get_comment_list for [object] as [varname] %}
        {% get_comment_list for [object] as [varname] [flat|root_only] %}
        {% get_comment_list for [app].[model] [object_id] as [varname] %}
        {% get_comment_list for [app].[model] [object_id] as [varname] [flat|root_only] %}

    Example usage::

        {% get_comment_list for event as comment_list %}
        {% for comment in comment_list %}
            ...
        {% endfor %}
        {% get_comment_list for event as comment_list flat %}

    """
    return CommentListNode.handle_token(parser, token)


@register.tag
def render_comment_list(parser, token):
    """
    Render the comment list (as returned by ``{% get_comment_list %}``)
    through the ``comments/list.html`` template

    Syntax::

        {% render_comment_list for [object] %}
        {% render_comment_list for [app].[model] [object_id] %}

        {% render_comment_list for [object] [flat|root_only] %}
        {% render_comment_list for [app].[model] [object_id] [flat|root_only] %}

    Example usage::

        {% render_comment_list for event %}

    """
    return RenderCommentListNode.handle_token(parser, token)


@register.tag
def get_comment_form(parser, token):
    """
    Get a (new) form object to post a new comment.

    Syntax::

        {% get_comment_form for [object] as [varname] %}
        {% get_comment_form for [object] as [varname] with [parent_id] %}
        {% get_comment_form for [app].[model] [object_id] as [varname] %}
        {% get_comment_form for [app].[model] [object_id] as [varname] with [parent_id] %}
    """
    return CommentFormNode.handle_token(parser, token)


@register.tag
def render_comment_form(parser, token):
    """
    Render the comment form (as returned by ``{% render_comment_form %}``) 
    through the ``comments/form.html`` template.

    Syntax::

        {% render_comment_form for [object] %}
        {% render_comment_form for [object] with [parent_id] %}
        {% render_comment_form for [app].[model] [object_id] %}
        {% render_comment_form for [app].[model] [object_id] with [parent_id] %}
    """
    return RenderCommentFormNode.handle_token(parser, token)


@register.filter
def annotate_tree(comments):
    """
    Add ``open``, ``close`` properties to the comments, to render the tree.

    Syntax::

        {% for comment in comment_list|annotate_tree %}
            {% ifchanged comment.parent_id %}{% else %}</li>{% endifchanged %}
            {% if not comment.open and not comment.close %}</li>{% endif %}
            {% if comment.open %}<ul>{% endif %}

            <li id="c{{ comment.id }}">
                ...
            {% for close in comment.close %}</li></ul>{% endfor %}
        {% endfor %}

    When the :func:`fill_tree` filter, place the ``annotate_tree`` code after it::

        {% for comment in comment_list|fill_tree|annotate_tree %}
            ...
        {% endfor %}
    """
    return annotate_tree_properties(comments)


@register.filter
def fill_tree(comments):
    """
    When paginating the comments, insert the parent nodes of the first comment.

    Syntax::

        {% for comment in comment_list|annotate_tree %}
            ...
        {% endfor %}
    """
    return real_fill_tree(comments)

########NEW FILE########
__FILENAME__ = tests
from unittest import TestCase

from django.test import TransactionTestCase
from django.contrib import comments
from django.contrib.sites.models import Site
from django.template import loader, TemplateSyntaxError
from django.conf import settings

from threadedcomments.util import annotate_tree_properties
from threadedcomments.templatetags import threadedcomments_tags as tags

PATH_SEPARATOR = getattr(settings, 'COMMENT_PATH_SEPARATOR', '/')
PATH_DIGITS = getattr(settings, 'COMMENT_PATH_DIGITS', 10)

def sanitize_html(html):
    return '\n'.join((i.strip() for i in html.split('\n') if i.strip() != ''))

class SanityTests(TransactionTestCase):
    BASE_DATA = {
        'name': u'Eric Florenzano',
        'email': u'floguy@gmail.com',
        'comment': u'This is my favorite Django app ever!',
    }

    def _post_comment(self, data=None, parent=None):
        Comment = comments.get_model()
        body = self.BASE_DATA.copy()
        if data:
            body.update(data)
        url = comments.get_form_target()
        args = [Site.objects.all()[0]]
        kwargs = {}
        if parent is not None:
            kwargs['parent'] = unicode(parent.pk)
            body['parent'] = unicode(parent.pk)
        form = comments.get_form()(*args, **kwargs)
        body.update(form.generate_security_data())
        self.client.post(url, body, follow=True)
        return Comment.objects.order_by('-id')[0]

    def test_post_comment(self):
        Comment = comments.get_model()
        self.assertEqual(Comment.objects.count(), 0)
        comment = self._post_comment()
        self.assertEqual(comment.tree_path, str(comment.pk).zfill(PATH_DIGITS))
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(comment.last_child, None)

    def test_post_comment_child(self):
        Comment = comments.get_model()
        comment = self._post_comment()
        self.assertEqual(comment.tree_path, str(comment.pk).zfill(PATH_DIGITS))
        child_comment = self._post_comment(data={'name': 'ericflo'}, parent=comment)
        comment_pk = str(comment.pk).zfill(PATH_DIGITS)
        child_comment_pk = str(child_comment.pk).zfill(PATH_DIGITS)
        self.assertEqual(child_comment.tree_path, PATH_SEPARATOR.join((comment.tree_path, child_comment_pk)))
        self.assertEqual(comment.pk, child_comment.parent.pk)
        comment = comments.get_model().objects.get(pk=comment.pk)
        self.assertEqual(comment.last_child, child_comment)


class HierarchyTest(TransactionTestCase):
    fixtures = ['simple_tree']

    EXPECTED_HTML_PARTIAL = sanitize_html('''
    <ul>
        <li>
            0000000001 ADDED
            <ul>
                <li class="last">
                    0000000001/0000000004 ADDED
                    <ul>
                        <li class="last">
                            0000000001/0000000004/0000000006
                        </li>
                    </ul>
                </li>
            </ul>
        </li>
    </ul>
    <ul>
        <li>
            0000000007
        </li>
    </ul>
    ''')
    EXPECTED_HTML_FULL = sanitize_html('''
    <ul>
        <li>
            0000000001
            <ul>
                <li>
                    0000000001/0000000002
                    <ul>
                        <li>
                            0000000001/0000000002/0000000003
                        </li>
                        <li class="last">
                            0000000001/0000000002/0000000005
                        </li>
                    </ul>
                </li>
                <li class="last">
                    0000000001/0000000004
                    <ul>
                        <li class="last">
                            0000000001/0000000004/0000000006
                        </li>
                    </ul>
                </li>
            </ul>
        </li>
    </ul>
    <ul>
        <li>
            0000000007
        </li>
    </ul>
    ''')

    def test_root_path_returns_empty_for_root_comments(self):
        c = comments.get_model().objects.get(pk=7)
        self.assertEqual([], [x.pk for x in c.root_path])

    def test_root_path_returns_only_correct_nodes(self):
        c = comments.get_model().objects.get(pk=6)
        self.assertEqual([1, 4], [x.pk for x in c.root_path])

    def test_root_id_returns_self_for_root_comments(self):
        c = comments.get_model().objects.get(pk=7)
        self.assertEqual(c.pk, c.root_id)

    def test_root_id_returns_root_for_replies(self):
        c = comments.get_model().objects.get(pk=6)
        self.assertEqual(1, c.root_id)

    def test_root_has_depth_1(self):
        c = comments.get_model().objects.get(pk=7)
        self.assertEqual(1, c.depth)

    def test_open_and_close_match(self):
        depth = 0
        for x in annotate_tree_properties(comments.get_model().objects.all()):
            depth += getattr(x, 'open', 0)
            self.assertEqual(x.depth, depth)
            depth -= len(getattr(x, 'close', []))

        self.assertEqual(0, depth)

    def test_last_flags_set_correctly_only_on_last_sibling(self):
        # construct the tree
        nodes = {}
        for x in comments.get_model().objects.all():
            nodes[x.pk] = (x, [])
            if x.parent_id:
                nodes[x.parent_id][1].append(x.pk)

        # check all the comments
        for x in annotate_tree_properties(comments.get_model().objects.all()):
            if getattr(x, 'last', False):
                # last comments have a parent
                self.assertTrue(x.parent_id)
                par, siblings = nodes[x.parent_id]

                # and ar last in their child list
                self.assertTrue(x.pk in siblings)
                self.assertEqual(len(siblings) - 1, siblings.index(x.pk))

    def test_rendering_of_partial_tree(self):
        output = loader.render_to_string('sample_tree.html', {'comment_list': comments.get_model().objects.all()[5:]})
        self.assertEqual(self.EXPECTED_HTML_PARTIAL, sanitize_html(output))

    def test_rendering_of_full_tree(self):
        output = loader.render_to_string('sample_tree.html', {'comment_list': comments.get_model().objects.all()})
        self.assertEqual(self.EXPECTED_HTML_FULL, sanitize_html(output))

    def test_last_child_properly_created(self):
        Comment = comments.get_model()
        new_child_comment = Comment(comment="Comment 8", site_id=1, content_type_id=7, object_pk=1, parent_id=1)
        new_child_comment.save()
        comment = Comment.objects.get(pk=1)
        self.assertEqual(comment.last_child, new_child_comment)

    def test_last_child_doesnt_delete_parent(self):
        Comment = comments.get_model()
        comment = Comment.objects.get(pk=1)
        new_child_comment = Comment(comment="Comment 9", site_id=1, content_type_id=7, object_pk=1, parent_id=comment.id)
        new_child_comment.save()
        new_child_comment.delete()
        comment = Comment.objects.get(pk=1)

    def test_deletion_of_last_child_marks_parent_as_childless(self):
        Comment = comments.get_model()
        c = Comment.objects.get(pk=6)
        c.delete()
        c = Comment.objects.get(pk=4)
        self.assertEqual(None, c.last_child)

    def test_last_child_repointed_correctly_on_delete(self):
        Comment = comments.get_model()
        comment = Comment.objects.get(pk=1)
        last_child = comment.last_child
        new_child_comment = Comment(comment="Comment 9", site_id=1, content_type_id=7, object_pk=1, parent_id=comment.id)

        new_child_comment.save()
        comment = Comment.objects.get(pk=1)
        self.assertEqual(comment.last_child, new_child_comment)
        new_child_comment.delete()
        comment = Comment.objects.get(pk=1)
        self.assertEqual(last_child, comment.last_child)



# Templatetags tests
##############################################################################

class MockParser(object):
    "Mock parser object for handle_token()"
    def compile_filter(self, var):
        return var
mock_parser = MockParser()

class MockToken(object):
    "Mock token object for handle_token()"
    def __init__(self, bits):
        self.contents = self
        self.bits = bits

    def split(self):
        return self.bits

class TestCommentListNode(TestCase):

    """
    {% get_comment_list for [object] as [varname] %}
    {% get_comment_list for [app].[model] [object_id] as [varname] %}
    """
    correct_ct_pk_params = ['get_comment_list', 'for', 'sites.site', '1', 'as', 'var']
    correct_var_params = ['get_comment_list', 'for', 'var', 'as', 'var']
    def test_parsing_fails_for_empty_token(self):
        self.assertRaises(TemplateSyntaxError, tags.get_comment_list, mock_parser, MockToken(['get_comment_list']))

    def test_parsing_fails_if_model_not_exists(self):
        params = self.correct_ct_pk_params[:]
        params[2] = 'not_app.not_model'
        self.assertRaises(TemplateSyntaxError, tags.get_comment_list, mock_parser, MockToken(params))

    def test_parsing_fails_if_object_not_exists(self):
        params = self.correct_ct_pk_params[:]
        params[2] = '1000'
        self.assertRaises(TemplateSyntaxError, tags.get_comment_list, mock_parser, MockToken(params))

    def test_parsing_works_for_ct_pk_pair(self):
        node = tags.get_comment_list(mock_parser, MockToken(self.correct_ct_pk_params))
        self.assertTrue(isinstance(node, tags.CommentListNode))

    def test_parsing_works_for_var(self):
        node = tags.get_comment_list(mock_parser, MockToken(self.correct_var_params))
        self.assertTrue(isinstance(node, tags.CommentListNode))

    def test_flat_parameter_is_passed_into_the_node_for_ct_pk_pair(self):
        params = self.correct_ct_pk_params[:]
        params.append(u'flat')
        node = tags.get_comment_list(mock_parser, MockToken(params))
        self.assertTrue(isinstance(node, tags.CommentListNode))
        self.assertTrue(node.flat)

    def test_flat_parameter_is_passed_into_the_node_for_var(self):
        params = self.correct_var_params[:]
        params.append(u'flat')
        node = tags.get_comment_list(mock_parser, MockToken(params))
        self.assertTrue(isinstance(node, tags.CommentListNode))
        self.assertTrue(node.flat)

    def test_root_only_parameter_is_passed_into_the_node_for_var(self):
        params = self.correct_var_params[:]
        params.append(u'root_only')
        node = tags.get_comment_list(mock_parser, MockToken(params))
        self.assertTrue(isinstance(node, tags.CommentListNode))
        self.assertTrue(node.root_only)

    def test_root_only_parameter_is_passed_into_the_node_for_ct_pk_pair(self):
        params = self.correct_ct_pk_params[:]
        params.append(u'root_only')
        node = tags.get_comment_list(mock_parser, MockToken(params))
        self.assertTrue(isinstance(node, tags.CommentListNode))
        self.assertTrue(node.root_only)


########NEW FILE########
__FILENAME__ = util
from itertools import chain, imap

__all__ = ['fill_tree', 'annotate_tree_properties', ]

def _mark_as_root_path(comment):
    """
    Mark on comment as Being added to fill the tree.
    """
    setattr(comment, 'added_path', True)
    return comment

def fill_tree(comments):
    """
    Insert extra comments in the comments list, so that the root path of the first comment is always visible.
    Use this in comments' pagination to fill in the tree information.

    The inserted comments have an ``added_path`` attribute.
    """
    if not comments:
        return

    it = iter(comments)
    first = it.next()
    extra_path_items = imap(_mark_as_root_path, first.root_path)
    return chain(extra_path_items, [first], it)

def annotate_tree_properties(comments):
    """
    iterate through nodes and adds some magic properties to each of them
    representing opening list of children and closing it
    """
    if not comments:
        return

    it = iter(comments)

    # get the first item, this will fail if no items !
    old = it.next()

    # first item starts a new thread
    old.open = True
    last = set()
    for c in it:
        # if this comment has a parent, store its last child for future reference
        if old.last_child_id:
            last.add(old.last_child_id)

        # this is the last child, mark it
        if c.pk in last:
            c.last = True

        # increase the depth
        if c.depth > old.depth:
            c.open = True

        else: # c.depth <= old.depth
            # close some depths
            old.close = range(old.depth - c.depth)

            # new thread
            if old.root_id != c.root_id:
                # close even the top depth
                old.close.append(len(old.close))
                # and start a new thread
                c.open = True
                # empty the last set
                last = set()
        # iterate
        yield old
        old = c

    old.close = range(old.depth)
    yield old

########NEW FILE########
