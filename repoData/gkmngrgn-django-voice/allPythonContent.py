__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.
import os

ROOT = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ROOT, 'demo.db')
    }
}

TIME_ZONE = 'America/Chicago'

ugettext = lambda s: s
LANGUAGES = (
    ('en', ugettext("English")),
    ('fi', ugettext("Finnish")),
    ('tr', ugettext("Turkish")))
LANGUAGE_CODE = LANGUAGES[0][0]

SITE_ID = 1

USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

STATIC_ROOT = ''

STATIC_URL = '/static/'

ADMIN_MEDIA_PREFIX = '/static/admin/'

STATICFILES_DIRS = ()

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'as@ec+-63@fjydh*8kawri_)$wrxcwb$zuphifex#m79=y4z-6'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_DIRS = (os.path.join(ROOT, '..', 'templates'),)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'
)

ROOT_URLCONF = 'demo.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.comments',
    'qhonuskan_votes',
    'djangovoice',
    'south',
    'demo'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
            },
        }
}

LOGIN_URL = "/admin/login"

VOICE_ALLOW_ANONYMOUS_USER_SUBMIT = True
VOICE_BRAND_VIEW = 'home'

########NEW FILE########
__FILENAME__ = tests
from django.core.urlresolvers import reverse
from django.test import Client, TestCase

from djangovoice.models import *


class DjangoVoiceTestCase(TestCase):
    fixtures = ['initial_data']


class ViewTestCase(DjangoVoiceTestCase):
    def setUp(self):
        self.client = Client()

    def test_feedback_list_page(self):
        # user is not logged in, but it can see feedback list:
        response = self.client.get(reverse('djangovoice_home'))
        self.assertEqual(response.status_code, 200)


class StatusTestCase(DjangoVoiceTestCase):
    def setUp(self):
        self.in_progress = Status.objects.create(
            title='In progress', slug='in_progress', default=False)
        self.need_to_test = Status.objects.create(
            title='Need to test', slug='need_to_test', default=True)

    def testSpeaking(self):
        self.assertEqual(self.in_progress.status, 'open')
        self.assertEqual(self.need_to_test.default, True)


class TypeTestCase(DjangoVoiceTestCase):
    def setUp(self):
        self.bug = Type.objects.create(title='Bug', slug='bug')
        self.betterment = Type.objects.create(title='Betterment',
                                              slug='betterment')

    def testSpeaking(self):
        self.assertEqual(self.bug.slug, 'bug')
        self.assertEqual(self.betterment.title, 'Betterment')


class FeedbackTestCase(DjangoVoiceTestCase):
    def setUp(self):
        feedback_type = Type.objects.create(title='Bug', slug='bug')
        feedback_user = User.objects.create_user(
            username='djangovoice', email='django@voice.com')
        self.login_form_does_not_work = Feedback.objects.create(
            type=feedback_type,
            title='Login form does not work.',
            description='What a fucking test...',
            anonymous=False,
            private=True,
            user=feedback_user)

    def testSpeaking(self):
        default_status = Status.objects.get(default=True)
        self.assertEqual(self.login_form_does_not_work.status, default_status)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import TemplateView

admin.autodiscover()

urlpatterns = patterns(
    '',

    url(r'^$',
        view=TemplateView.as_view(template_name='home.html'),
        name='home'),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^comments/', include('django.contrib.comments.urls')),
    url(r'^feedback/', include('djangovoice.urls')),
    url(r'^auth/', include('django.contrib.auth.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
)

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
__FILENAME__ = admin
from django.contrib import admin
from djangovoice.models import Feedback, Status, Type


class SlugFieldAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}


class FeedbackAdmin(admin.ModelAdmin):
    list_display = [
        '__unicode__', 'type', 'status', 'duplicate', 'anonymous', 'private',
        'user', 'email']
    list_filter = ['type', 'status', 'anonymous', 'private']
    list_editable = ['type', 'status', 'anonymous', 'private']


admin.site.register(Feedback, FeedbackAdmin)
admin.site.register([Status, Type], SlugFieldAdmin)

########NEW FILE########
__FILENAME__ = compat
import urllib
from django import VERSION as DJANGO_VERSION
from django.conf import settings
from hashlib import md5

if DJANGO_VERSION >= (1, 5):
    # Django 1.5+ compatibility
    from django.contrib.auth import get_user_model
    User = get_user_model()

else:
    from django.contrib.auth.models import User


if 'gravatar' in settings.INSTALLED_APPS:
    from gravatar.templatetags.gravatar_tags import gravatar_for_user

else:
    gravatar_url = 'http://www.gravatar.com/'

    def gravatar_for_user(user, size=80):
        size_param = urllib.urlencode({'s': str(size)})
        email = md5(user.email).hexdigest()
        url = '%savatar/%s/?%s' % (gravatar_url, email, size_param)

        return url

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from djangovoice.models import Feedback


class LatestFeedback(Feed):
    title = "Feedback"
    link = "/feedback/"
    description = "Latest feedback"

    def items(self):
        return Feedback.objects.filter(private=False).order_by('-created')[:10]

########NEW FILE########
__FILENAME__ = forms
from django import forms
from djangovoice.models import Feedback


class WidgetForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = (
            'email', 'type', 'anonymous', 'private', 'title', 'description')


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        exclude = ('status', 'user', 'slug', 'duplicate')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(FeedbackForm, self).__init__(*args, **kwargs)

        # add class to fix width of title input and textarea:
        for field_name in ['title', 'description']:
            field = self.fields[field_name]
            field.widget.attrs.update({'class': 'input-block-level'})

        # change form fields for user authentication status:
        if self.user is not None and self.user.is_authenticated():
            deleted_fields = ['email']
        else:
            deleted_fields = ['anonymous', 'private']

        for field_name in deleted_fields:
            del self.fields[field_name]

        # add tabindex attribute to fields:
        for index, field in enumerate(self.fields.values(), 1):
            field.widget.attrs.update({'tabindex': index})

    def clean(self):
        cleaned_data = super(FeedbackForm, self).clean()

        return cleaned_data

    def clean_email(self):
        field = self.cleaned_data.get('email')

        if field is None and self.user is not None:
            field = self.user.email

        return field

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Status'
        db.create_table('djangovoice_status', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=500, db_index=True)),
            ('default', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('status', self.gf('django.db.models.fields.CharField')(default='open', max_length=10)),
        ))
        db.send_create_signal('djangovoice', ['Status'])

        # Adding model 'Type'
        db.create_table('djangovoice_type', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=500, db_index=True)),
        ))
        db.send_create_signal('djangovoice', ['Type'])

        # Adding model 'Feedback'
        db.create_table('djangovoice_feedback', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangovoice.Type'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('anonymous', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('private', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangovoice.Status'])),
            ('duplicate', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangovoice.Feedback'], null=True, blank=True)),
        ))
        db.send_create_signal('djangovoice', ['Feedback'])


    def backwards(self, orm):
        
        # Deleting model 'Status'
        db.delete_table('djangovoice_status')

        # Deleting model 'Type'
        db.delete_table('djangovoice_type')

        # Deleting model 'Feedback'
        db.delete_table('djangovoice_feedback')


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
        'djangovoice.feedback': {
            'Meta': {'object_name': 'Feedback'},
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'duplicate': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Feedback']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Status']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Type']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'djangovoice.status': {
            'Meta': {'object_name': 'Status'},
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '500', 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'open'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'djangovoice.type': {
            'Meta': {'object_name': 'Type'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '500', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        }
    }

    complete_apps = ['djangovoice']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_feedback_email__add_field_feedback_slug
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Feedback.email'
        db.add_column('djangovoice_feedback', 'email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True), keep_default=False)

        # Adding field 'Feedback.slug'
        db.add_column('djangovoice_feedback', 'slug', self.gf('django.db.models.fields.SlugField')(max_length=10, null=True, db_index=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Feedback.email'
        db.delete_column('djangovoice_feedback', 'email')

        # Deleting field 'Feedback.slug'
        db.delete_column('djangovoice_feedback', 'slug')


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
        'djangovoice.feedback': {
            'Meta': {'object_name': 'Feedback'},
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'duplicate': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Feedback']", 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '10', 'null': 'True', 'db_index': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Status']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Type']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'djangovoice.status': {
            'Meta': {'object_name': 'Status'},
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '500', 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'open'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'djangovoice.type': {
            'Meta': {'object_name': 'Type'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '500', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        }
    }

    complete_apps = ['djangovoice']

########NEW FILE########
__FILENAME__ = 0003_auto__add_feedbackvote
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'FeedbackVote'
        db.create_table('djangovoice_feedbackvote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('voter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('value', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('object', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djangovoice.Feedback'])),
        ))
        db.send_create_signal('djangovoice', ['FeedbackVote'])


    def backwards(self, orm):
        # Deleting model 'FeedbackVote'
        db.delete_table('djangovoice_feedbackvote')


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
        'djangovoice.feedback': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Feedback'},
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'duplicate': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Feedback']", 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'private': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Status']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Type']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'djangovoice.feedbackvote': {
            'Meta': {'ordering': "('date',)", 'object_name': 'FeedbackVote'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['djangovoice.Feedback']"}),
            'value': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'voter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djangovoice.status': {
            'Meta': {'object_name': 'Status'},
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '500'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'open'", 'max_length': '10'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        'djangovoice.type': {
            'Meta': {'object_name': 'Type'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '500'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        }
    }

    complete_apps = ['djangovoice']
########NEW FILE########
__FILENAME__ = mixins
from django.contrib.sites.models import get_current_site
from settings import BRAND_VIEW

class VoiceMixin(object):
    def get_context_data(self, **kwargs):
        context = super(VoiceMixin, self).get_context_data(**kwargs)
        context.update({
            'site': get_current_site(self.request),
            'brand_view': BRAND_VIEW
        })

        return context

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import pgettext
from django.utils.translation import ugettext_lazy as _
from djangovoice.compat import User
from djangovoice.model_managers import StatusManager
from qhonuskan_votes.models import VotesField
from qhonuskan_votes.models import ObjectsWithScoresManager

STATUS_CHOICES = (
    ('open', pgettext('status', "Open")),
    ('closed', pgettext('status', "Closed")),
)


class Status(models.Model):
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500)
    default = models.BooleanField(
        blank=True,
        help_text=_("New feedback will have this status"))
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])

    objects = StatusManager()

    def save(self, **kwargs):
        if self.default:
            try:
                default_project = Status.objects.get(default=True)
                default_project.default = False
                default_project.save()

            except Status.DoesNotExist:
                pass

        super(Status, self).save(**kwargs)

    def __unicode__(self):
        return unicode(self.title)

    class Meta:
        verbose_name = _("status")
        verbose_name_plural = _("statuses")


class Type(models.Model):
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500)

    def __unicode__(self):
        return self.title


class Feedback(models.Model):
    title = models.CharField(max_length=500, verbose_name=_("Title"))
    description = models.TextField(
        blank=True, verbose_name=_("Description"),
        help_text=_(
            "This will be viewable by other people - do not include any "
            "private details such as passwords or phone numbers here."))
    type = models.ForeignKey(Type, verbose_name=_("Type"))
    anonymous = models.BooleanField(
        blank=True, verbose_name=_("Anonymous"),
        help_text=_("Do not show who sent this"))
    private = models.BooleanField(
        verbose_name=_("Private"), blank=True,
        help_text=_(
            "Hide from public pages. Only site administrators will be able to "
            "view and respond to this"))
    user = models.ForeignKey(
        User, blank=True, null=True, verbose_name=_("User"))
    email = models.EmailField(
        blank=True, null=True, verbose_name=_('E-mail'),
        help_text=_(
            "You must provide your e-mail so we can answer to you. "
            "Alternatively you can bookmark next page and check out for an "
            "answer later."))
    slug = models.SlugField(max_length=10, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    status = models.ForeignKey(Status, verbose_name=_('Status'))
    duplicate = models.ForeignKey(
        'self', null=True, blank=True, verbose_name=_("Duplicate"))
    votes = VotesField()
    objects = ObjectsWithScoresManager()

    def save(self, **kwargs):
        if self.status_id is None:
            self.status = Status.objects.get_default()

        super(Feedback, self).save(**kwargs)

    @models.permalink
    def get_absolute_url(self):
        return 'djangovoice_item', [self.id]

    def __unicode__(self):
        return unicode(self.title)

    class Meta:
        verbose_name = _("feedback")
        verbose_name_plural = _("feedback")
        ordering = ('-created',)
        get_latest_by = 'created'

########NEW FILE########
__FILENAME__ = model_managers
from django.db import models


class StatusManager(models.Manager):
    def get_default(self):
        if not self.count():
            default_status = None
        elif self.filter(default=True).exists():
            default_status = self.filter(default=True)[0]
        else:
            default_status = Status.objects.all()[0]

        return default_status

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

BRAND_VIEW = getattr(settings, 'VOICE_BRAND_VIEW', 'djangovoice_home')
ALLOW_ANONYMOUS_USER_SUBMIT = getattr(
    settings, 'VOICE_ALLOW_ANONYMOUS_USER_SUBMIT', False)

########NEW FILE########
__FILENAME__ = djangovoice_tags
from django.template import Library, Node, Variable, TemplateSyntaxError
from djangovoice.compat import gravatar_for_user
from djangovoice.models import Type, Status

register = Library()


class TypeListNode(Node):
    def render(self, context):
        context['type_list'] = Type.objects.all()
        return ''


def build_type_list(parser, token):
    """
    {% get_type_list %}
    """
    return TypeListNode()

register.tag('get_type_list', build_type_list)


class StatusListNode(Node):
    def __init__(self, list_type):
        self.list_type = Variable(list_type)

    def render(self, context):
        list_type = self.list_type.resolve(context)
        status_list = Status.objects.all()

        if list_type in ['open', 'closed']:
            status = list_type  # values are same.
            status_list = status_list.filter(status=status)

        context['status_list'] = status_list
        return ''


def build_status_list(parser, token):
    """
    {% get_status_list %}
    """
    bits = token.contents.split()

    if len(bits) != 2:
        msg = "'%s' tag takes exactly 1 arguments" % bits[0]
        raise TemplateSyntaxError(msg)

    return StatusListNode(bits[1])

register.tag('get_status_list', build_status_list)


@register.filter
def display_name(user):
    """
    If user has full name, get user's full name, else username.
    """
    full_name = user.get_full_name()
    if not full_name:
        return user.username

    return full_name


@register.inclusion_tag('djangovoice/tags/widget.html', takes_context=True)
def djangovoice_widget(context):
    arguments = {'STATIC_URL': context.get('STATIC_URL')}

    return arguments


@register.simple_tag
def get_user_image(user, size=80):
    url = gravatar_for_user(user, size)
    return '<img src="%s" alt="%s" height="%s" width="%s" />' % (
        url, user.username, size, size)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import include, patterns, url
from django.contrib.auth.views import login
from djangovoice.models import Feedback
from djangovoice.views import (
    FeedbackListView, FeedbackWidgetView, FeedbackSubmitView,
    FeedbackDetailView, FeedbackEditView, FeedbackDeleteView)
from djangovoice.feeds import LatestFeedback
from djangovoice.settings import BRAND_VIEW

feedback_list_regex = '^(?P<list>all|open|closed|mine)'
feedback_dict = {
    'model': Feedback,
    'template_object_name': 'feedback'
}

urlpatterns = patterns(
    '',

    url(r'^$',
        view=FeedbackListView.as_view(),
        name='djangovoice_home'),

    url(r'%s/$' % feedback_list_regex,
        view=FeedbackListView.as_view(),
        name='djangovoice_list'),

    url(r'%s/(?P<type>[-\w]+)/$' % feedback_list_regex,
        view=FeedbackListView.as_view(),
        name='djangovoice_list_type'),

    url(
        r'%s/(?P<type>[-\w]+)/(?P<status>[-\w]+)/$' % feedback_list_regex,
        view=FeedbackListView.as_view(),
        name='djangovoice_list_type_status'),

    url(r'^widget/$',
        view=FeedbackWidgetView.as_view(),
        name='djangovoice_widget'),

    url(r'^submit/$',
        view=FeedbackSubmitView.as_view(),
        name='djangovoice_submit'),

    # override login template
    url(r'^signin/$',
        view=login,
        name='djangovoice_signin',
        kwargs={
            'template_name': 'djangovoice/signin.html',
            'extra_context': {'brand_view': BRAND_VIEW}
        }),

    url(r'^(?P<pk>\d+)/$',
        view=FeedbackDetailView.as_view(),
        name='djangovoice_item'),

    url(r'^(?P<slug>\w+)/$',
        view=FeedbackDetailView.as_view(),
        name='djangovoice_slug_item'),

    url(r'^(?P<pk>\d+)/edit/$',
        view=FeedbackEditView.as_view(),
        name='djangovoice_edit'),

    url(r'^(?P<pk>\d+)/delete/$',
        view=FeedbackDeleteView.as_view(),
        name='djangovoice_delete'),

    url(r'^feeds/latest/$',
        view=LatestFeedback(),
        name='feeds_latest'),

    url(r'^votes/', include('qhonuskan_votes.urls'))
)

########NEW FILE########
__FILENAME__ = views
import uuid
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.views.generic import DeleteView, DetailView, FormView, ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from djangovoice.models import Feedback, Type
from djangovoice.forms import WidgetForm, FeedbackForm
from djangovoice.mixins import VoiceMixin
from djangovoice.settings import ALLOW_ANONYMOUS_USER_SUBMIT


class FeedbackDetailView(VoiceMixin, DetailView):
    template_name = 'djangovoice/detail.html'
    model = Feedback

    def get(self, request, *args, **kwargs):
        feedback = self.get_object()

        if feedback.private:
            # Anonymous private feedback can be only accessed with slug
            if (not request.user.is_staff
                    and not 'slug' in kwargs
                    and feedback.user is None):
                raise PermissionDenied

            if (not request.user.is_staff
                    and request.user != feedback.user
                    and feedback.user is not None):
                raise PermissionDenied

        return super(FeedbackDetailView, self).get(request, *args, **kwargs)


class FeedbackListView(VoiceMixin, ListView):
    template_name = 'djangovoice/list.html'
    model = Feedback
    paginate_by = 10

    def get_queryset(self):
        f_list = self.kwargs.get('list', 'open')
        f_type = self.kwargs.get('type', 'all')
        f_status = self.kwargs.get('status', 'all')
        f_filters = {}
        # Tag to display also user's private discussions
        f_showpriv = False

        # add filter for list value, and define title.
        if f_list in ['open', 'closed']:
            f_filters.update(dict(status__status=f_list))

        elif f_list == 'mine':
            f_filters.update(user=self.request.user)

        # add filter for feedback type.
        if f_type != 'all':
            f_filters.update(dict(type__slug=f_type))

        # add filter for feedback status.
        if f_status != 'all':
            f_filters.update(dict(status__slug=f_status))

        # If user is checking his own feedback, do not filter by private
        # for everyone's discussions but add user's private feedback
        if not self.request.user.is_staff and f_list != 'mine':
            f_filters.update({'private': False})
            f_showpriv = True

        if f_showpriv and self.request.user.is_authenticated():
            # Show everyone's public discussions and user's own private
            # discussions
            queryset = self.model.objects.filter(
                Q(**f_filters) | Q(user=self.request.user, private=True))
        else:
            queryset = self.model.objects.filter(**f_filters)

        queryset = queryset.order_by('-vote_score', '-created')

        return queryset

    def get_context_data(self, **kwargs):
        f_list = self.kwargs.get('list', 'open')
        f_type = self.kwargs.get('type', 'all')
        f_status = self.kwargs.get('status', 'all')

        title = _("Feedback")

        if f_list == 'open':
            title = _("Open Feedback")

        elif f_list == 'closed':
            title = _("Closed Feedback")

        elif f_list == 'mine':
            title = _("My Feedback")

        # update context data
        data = super(FeedbackListView, self).get_context_data(**kwargs)
        data.update({
            'list': f_list,
            'status': f_status,
            'type': f_type,
            'navigation_active': f_list,
            'title': title
        })

        return data

    def get(self, request, *args, **kwargs):
        f_list = kwargs.get('list')

        if f_list == 'mine' and not request.user.is_authenticated():
            to_url = (
                reverse('django.contrib.auth.views.login') +
                '?next=%s' % request.path)

            return redirect(to_url)

        return super(FeedbackListView, self).get(request, *args, **kwargs)


class FeedbackWidgetView(FormView):
    template_name = 'djangovoice/widget.html'
    form_class = WidgetForm

    def get(self, request, *args, **kwargs):
        return super(FeedbackWidgetView, self).get(request, *args, **kwargs)

    def get_initial(self):
        return {'type': Type.objects.get(pk=1)}

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        return super(FeedbackWidgetView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        feedback = form.save(commit=False)
        if form.cleaned_data.get('anonymous') != 'on':
            feedback.user = self.request.user
        feedback.save()

        messages.add_message(
            self.request, messages.SUCCESS, _("Thanks for feedback."))

        return redirect('djangovoice_widget')

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR,
                             _("Form is invalid."))

        return super(FeedbackWidgetView, self).form_invalid(form)


class FeedbackSubmitView(VoiceMixin, FormView):
    template_name = 'djangovoice/form.html'
    form_class = FeedbackForm

    def get_context_data(self, **kwargs):
        return super(FeedbackSubmitView, self).get_context_data(**kwargs)

    def dispatch(self, request, *args, **kwargs):
        # if project doesn't allow anonymous user submission, check
        # authentication:
        if (not ALLOW_ANONYMOUS_USER_SUBMIT
                and not request.user.is_authenticated()):
            login_url = reverse('django.contrib.auth.views.login')
            return redirect(login_url + '?next=%s' % request.path)

        return super(FeedbackSubmitView, self).dispatch(
            request, *args, **kwargs)

    def get_form_kwargs(self):
        # define user in form, some form data return fields for user
        # authentication.
        kwargs = super(FeedbackSubmitView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})

        return kwargs

    def form_valid(self, form):
        feedback = form.save(commit=False)

        if self.request.user.is_anonymous() and ALLOW_ANONYMOUS_USER_SUBMIT:
            feedback.private = True
            feedback.anonymous = True

        elif not form.cleaned_data.get('anonymous', False):
            feedback.user = self.request.user

        if not feedback.user:
            feedback.slug = uuid.uuid1().hex[:10]

        feedback.save()

        # If there is no user, show the feedback with slug
        if not feedback.user:
            response = redirect('djangovoice_slug_item', slug=feedback.slug)

        else:
            response = redirect(feedback)

        return response


class FeedbackEditView(FeedbackSubmitView):
    template_name = 'djangovoice/form.html'
    form_class = FeedbackForm

    def get_object(self):
        return Feedback.objects.get(pk=self.kwargs.get('pk'))

    def get_form_kwargs(self):
        kwargs = super(FeedbackEditView, self).get_form_kwargs()
        kwargs.update({'instance': self.get_object()})

        return kwargs

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        if not form_class:
            raise HttpResponseNotFound

        return super(FeedbackEditView, self).get(request, *args, **kwargs)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        return super(FeedbackEditView, self).post(request, *args, **kwargs)


class FeedbackDeleteView(VoiceMixin, DeleteView):
    template_name = 'djangovoice/delete.html'

    def get_object(self):
        return Feedback.objects.get(pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        return super(FeedbackDeleteView, self).get_context_data(**kwargs)

    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        # FIXME: should feedback user have delete permissions?
        feedback = self.get_object()
        if not request.user.is_staff and request.user != feedback.user:
            raise HttpResponseNotFound

        return super(FeedbackDeleteView, self).get(request, *args, **kwargs)

    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        feedback = self.get_object()
        feedback.delete()

        return redirect('djangovoice_home')

########NEW FILE########
