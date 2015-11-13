__FILENAME__ = admin
from datetime import datetime, date, time
from decimal import Decimal
from operator import itemgetter
import six

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import widgets
from django.contrib.admin.options import csrf_protect_m
from django.core.exceptions import PermissionDenied
from django.forms import fields
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.formats import localize
from django.utils.translation import ugettext as _

try:
    from django.conf.urls import patterns, url
except ImportError:  # Django < 1.4
    from django.conf.urls.defaults import patterns, url


from constance import config, settings


NUMERIC_WIDGET = forms.TextInput(attrs={'size': 10})

INTEGER_LIKE = (fields.IntegerField, {'widget': NUMERIC_WIDGET})
STRING_LIKE = (fields.CharField, {
    'widget': forms.Textarea(attrs={'rows': 3}),
    'required': False,
})

FIELDS = {
    bool: (fields.BooleanField, {'required': False}),
    int: INTEGER_LIKE,
    Decimal: (fields.DecimalField, {'widget': NUMERIC_WIDGET}),
    str: STRING_LIKE,
    list: STRING_LIKE,
    datetime: (fields.DateTimeField, {'widget': widgets.AdminSplitDateTime}),
    date: (fields.DateField, {'widget': widgets.AdminDateWidget}),
    time: (fields.TimeField, {'widget': widgets.AdminTimeWidget}),
    float: (fields.FloatField, {'widget': NUMERIC_WIDGET}),
}

if not six.PY3:
    FIELDS.update({
        long: INTEGER_LIKE,
        unicode: STRING_LIKE,
    })


class ConstanceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ConstanceForm, self).__init__(*args, **kwargs)
        for name, (default, help_text) in settings.CONFIG.items():
            field_class, kwargs = FIELDS[type(default)]
            self.fields[name] = field_class(label=name, **kwargs)

    def save(self):
        for name in self.cleaned_data:
            setattr(config, name, self.cleaned_data[name])


class ConstanceAdmin(admin.ModelAdmin):

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.module_name
        return patterns('',
            url(r'^$',
                self.admin_site.admin_view(self.changelist_view),
                name='%s_%s_changelist' % info),
            url(r'^$',
                self.admin_site.admin_view(self.changelist_view),
                name='%s_%s_add' % info),
        )

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        # First load a mapping between config name and default value
        if not self.has_change_permission(request, None):
            raise PermissionDenied
        default_initial = ((name, default)
            for name, (default, help_text) in settings.CONFIG.items())
        # Then update the mapping with actually values from the backend
        initial = dict(default_initial,
            **dict(config._backend.mget(settings.CONFIG.keys())))
        form = ConstanceForm(initial=initial)
        if request.method == 'POST':
            form = ConstanceForm(request.POST)
            if form.is_valid():
                form.save()
                # In django 1.5 this can be replaced with self.message_user
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    _('Live settings updated successfully.'),
                )
                return HttpResponseRedirect('.')
        context = {
            'config': [],
            'title': _('Constance config'),
            'app_label': 'constance',
            'opts': Config._meta,
            'form': form,
            'media': self.media + form.media,
        }
        for name, (default, help_text) in settings.CONFIG.items():
            # First try to load the value from the actual backend
            value = initial.get(name)
            # Then if the returned value is None, get the default
            if value is None:
                value = getattr(config, name)
            context['config'].append({
                'name': name,
                'default': localize(default),
                'help_text': _(help_text),
                'value': localize(value),
                'modified': value != default,
                'form_field': form[name],
            })
        context['config'].sort(key=itemgetter('name'))
        context_instance = RequestContext(request,
                                          current_app=self.admin_site.name)
        return render_to_response('admin/constance/change_list.html',
            context, context_instance=context_instance)

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, request, obj=None):
        if settings.SUPERUSER_ONLY:
            return request.user.is_superuser
        return super(ConstanceAdmin, self).has_change_permission(request, obj)


class Config(object):
    class Meta(object):
        app_label = 'constance'
        object_name = 'Config'
        model_name = module_name = 'config'
        verbose_name_plural = _('config')
        get_ordered_objects = lambda x: False
        abstract = False
        swapped = False

        def get_change_permission(self):
            return 'change_%s' % self.model_name

    _meta = Meta()


admin.site.register([Config], ConstanceAdmin)

########NEW FILE########
__FILENAME__ = apps
from django.apps import AppConfig
from constance.config import Config


class ConstanceConfig(AppConfig):
    name = 'constance'
    verbose_name = 'Constance'

    def ready(self):
        self.module.config = Config()

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Constance'
        db.create_table('constance_config', (
            ('id', self.gf('django.db.models.fields.AutoField')(
                primary_key=True)),
            ('key', self.gf('django.db.models.fields.TextField')()),
            ('value', self.gf('picklefield.fields.PickledObjectField')()),
        ))
        db.send_create_signal('database', ['Constance'])

    def backwards(self, orm):
        # Deleting model 'Constance'
        db.delete_table('constance_config')

    models = {
        'database.constance': {
            'Meta': {'object_name': 'Constance',
                     'db_table': "'constance_config'"},
            'id': ('django.db.models.fields.AutoField', [],
                   {'primary_key': 'True'}),
            'key': ('django.db.models.fields.TextField', [], {}),
            'value': ('picklefield.fields.PickledObjectField', [], {})
        }
    }

    complete_apps = ['database']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_constance_key__add_unique_constance_key
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Changing field 'Constance.key'
        db.alter_column('constance_config', 'key',
                        self.gf('django.db.models.fields.CharField')(
                            max_length=255))
        # Adding unique constraint on 'Constance', fields ['key']
        db.create_unique('constance_config', ['key'])

    def backwards(self, orm):
        # Removing unique constraint on 'Constance', fields ['key']
        db.delete_unique('constance_config', ['key'])

        # Changing field 'Constance.key'
        db.alter_column('constance_config', 'key',
                        self.gf('django.db.models.fields.TextField')())

    models = {
        'database.constance': {
            'Meta': {'object_name': 'Constance',
                     'db_table': "'constance_config'"},
            'id': ('django.db.models.fields.AutoField', [],
                   {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [],
                    {'unique': 'True', 'max_length': '255'}),
            'value': ('picklefield.fields.PickledObjectField', [], {})
        }
    }

    complete_apps = ['database']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.core.exceptions import ImproperlyConfigured

from django.utils.translation import ugettext_lazy as _

try:
    from picklefield import PickledObjectField
except ImportError:
    raise ImproperlyConfigured("Couldn't find the the 3rd party app "
                               "django-picklefield which is required for "
                               "the constance database backend.")


class Constance(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = PickledObjectField()

    class Meta:
        verbose_name = _('constance')
        verbose_name_plural = _('constances')
        db_table = 'constance_config'

    def __unicode__(self):
        return self.key

########NEW FILE########
__FILENAME__ = redisd
import six
from six.moves import zip

from django.core.exceptions import ImproperlyConfigured

from constance import settings, utils
from constance.backends import Backend

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps


class RedisBackend(Backend):

    def __init__(self):
        super(RedisBackend, self).__init__()
        self._prefix = settings.REDIS_PREFIX
        connection_cls = settings.CONNECTION_CLASS
        if connection_cls is not None:
            self._rd = utils.import_module_attr(connection_cls)()
        else:
            try:
                import redis
            except ImportError:
                raise ImproperlyConfigured(
                    "The Redis backend requires redis-py to be installed.")
            if isinstance(settings.REDIS_CONNECTION, six.string_types):
                self._rd = redis.from_url(settings.REDIS_CONNECTION)
            else:
                self._rd = redis.Redis(**settings.REDIS_CONNECTION)

    def add_prefix(self, key):
        return "%s%s" % (self._prefix, key)

    def get(self, key):
        value = self._rd.get(self.add_prefix(key))
        if value:
            return loads(value)
        return None

    def mget(self, keys):
        if not keys:
            return
        prefixed_keys = [self.add_prefix(key) for key in keys]
        for key, value in zip(keys, self._rd.mget(prefixed_keys)):
            if value:
                yield key, loads(value)

    def set(self, key, value):
        self._rd.set(self.add_prefix(key), dumps(value))

########NEW FILE########
__FILENAME__ = config
from constance import settings, utils


class Config(object):
    """
    The global config wrapper that handles the backend.
    """
    def __init__(self):
        super(Config, self).__setattr__('_backend',
            utils.import_module_attr(settings.BACKEND)())

    def __getattr__(self, key):
        try:
            default, help_text = settings.CONFIG[key]
        except KeyError:
            raise AttributeError(key)
        result = self._backend.get(key)
        if result is None:
            result = default
            setattr(self, key, default)
            return result
        return result

    def __setattr__(self, key, value):
        if key not in settings.CONFIG:
            raise AttributeError(key)
        self._backend.set(key, value)

    def __dir__(self):
        return settings.CONFIG.keys()

########NEW FILE########
__FILENAME__ = context_processors
import constance


def config(request):
    """
    Simple context processor that puts the config into every
    RequestContext. Just make sure you have a setting like this:

        TEMPLATE_CONTEXT_PROCESSORS = (
            # ...
            'constance.context_processors.config',
        )

    """
    return {"config": constance.config}

########NEW FILE########
__FILENAME__ = models
from django.db.models import signals


def create_perm(app, created_models, verbosity, db, **kwargs):
    """
    Creates a fake content type and permission
    to be able to check for permissions
    """
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    if ContentType._meta.installed and Permission._meta.installed:
        content_type, created = ContentType.objects.get_or_create(
            name='config',
            app_label='constance',
            model='config')

        permission, created = Permission.objects.get_or_create(
            name='Can change config',
            content_type=content_type,
            codename='change_config')


signals.post_syncdb.connect(create_perm, dispatch_uid="constance.create_perm")

########NEW FILE########
__FILENAME__ = settings
import os
from constance.utils import import_module_attr

settings = import_module_attr(
    os.getenv('CONSTANCE_SETTINGS_MODULE', 'django.conf.settings')
)

REDIS_PREFIX = getattr(settings, 'CONSTANCE_REDIS_PREFIX',
               getattr(settings, 'CONSTANCE_PREFIX', 'constance:'))

BACKEND = getattr(settings, 'CONSTANCE_BACKEND',
                  'constance.backends.redisd.RedisBackend')

CONFIG = getattr(settings, 'CONSTANCE_CONFIG', {})

CONNECTION_CLASS = getattr(settings, 'CONSTANCE_REDIS_CONNECTION_CLASS',
                   getattr(settings, 'CONSTANCE_CONNECTION_CLASS', None))

REDIS_CONNECTION = getattr(settings, 'CONSTANCE_REDIS_CONNECTION',
                   getattr(settings, 'CONSTANCE_CONNECTION', {}))

DATABASE_CACHE_BACKEND = getattr(settings, 'CONSTANCE_DATABASE_CACHE_BACKEND',
                                 None)

DATABASE_PREFIX = getattr(settings, 'CONSTANCE_DATABASE_PREFIX', '')

SUPERUSER_ONLY = getattr(settings, 'CONSTANCE_SUPERUSER_ONLY', True)

########NEW FILE########
__FILENAME__ = constance_tags
from __future__ import absolute_import
from django import template
from django.conf import settings
from django.core.files.storage import get_storage_class

try:
    from django.contrib.staticfiles.storage import staticfiles_storage
except ImportError:
    staticfiles_storage = get_storage_class(settings.STATICFILES_STORAGE)()

register = template.Library()


@register.simple_tag
def static(path):
    """
    A template tag that returns the URL to a file
    using staticfiles' storage backend
    """
    return staticfiles_storage.url(path)

########NEW FILE########
__FILENAME__ = utils
from django.utils.importlib import import_module


def import_module_attr(path):
    package, module = path.rsplit('.', 1)
    return getattr(import_module(package), module)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from cheeseshop.apps.catalog.models import Brand

admin.site.register(Brand)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Brand(models.Model):
    name = models.CharField(max_length=75)


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from cheeseshop.apps.storage.models import Shelf, Supply

admin.site.register(Shelf)
admin.site.register(Supply)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Shelf(models.Model):
    name = models.CharField(max_length=75)

    class Meta:
        verbose_name_plural = 'shelves'

class Supply(models.Model):
    name = models.CharField(max_length=75)

    class Meta:
        verbose_name_plural = 'supplies'


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
from datetime import datetime
from decimal import Decimal

# Django settings for cheeseshop project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/tmp/cheeseshop.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'hdx64#m+lnc_0ffoyehbk&7gk1&*9uar$pcfcm-%$km#p0$k=6'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'cheeseshop.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'cheeseshop.apps.catalog',
    'cheeseshop.apps.storage',
    'constance',
)

CONSTANCE_CONNECTION = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
}

CONSTANCE_CONFIG = {
	'BANNER': ('The National Cheese Emporium', 'name of the shop'),
    'OWNER': ('Mr. Henry Wensleydale', 'owner of the shop'),
    'MUSICIANS': (4, 'number of musicians inside the shop'),
    'DATE_ESTABLISHED': (datetime(1972, 11, 30), "the shop's first opening"),
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^cheeseshop/', include('cheeseshop.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = redis_mockup
class Connection(dict):
    def set(self, key, value):
        self[key] = value

    def mget(self, keys):
        values = []
        for key in keys:
            value = self.get(key, None)
            if value is not None:
                values.append(value)
        return values

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys
from django.core.management import call_command

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'


def main():
    result = call_command('test', 'tests', verbosity=2)
    sys.exit(result)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = settings
# -*- encoding: utf-8 -*-
import six
from datetime import datetime, date, time
from decimal import Decimal

TEST_RUNNER = 'discover_runner.DiscoverRunner'

SECRET_KEY = 'cheese'

DATABASE_ENGINE = 'sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'constance',
    'constance.backends.database',
)

ROOT_URLCONF = 'tests.urls'

CONSTANCE_CONNECTION_CLASS = 'tests.redis_mockup.Connection'

long_value = 123456

if not six.PY3:
    long_value = long(long_value)

CONSTANCE_CONFIG = {
    'INT_VALUE': (1, 'some int'),
    'LONG_VALUE': (long_value, 'some looong int'),
    'BOOL_VALUE': (True, 'true or false'),
    'STRING_VALUE': ('Hello world', 'greetings'),
    'UNICODE_VALUE': (six.u('Rivière-Bonjour'), 'greetings'),
    'DECIMAL_VALUE': (Decimal('0.1'), 'the first release version'),
    'DATETIME_VALUE': (datetime(2010, 8, 23, 11, 29, 24), 'time of the first commit'),
    'FLOAT_VALUE': (3.1415926536, 'PI'),
    'DATE_VALUE': (date(2010, 12, 24),  'Merry Chrismas'),
    'TIME_VALUE': (time(23, 59, 59),  'And happy New Year'),
}

DEBUG = True

STATIC_ROOT = './static/'

STATIC_URL = '/static/'

########NEW FILE########
__FILENAME__ = storage
# -*- encoding: utf-8 -*-
import sys
import six
from datetime import datetime, date, time
from decimal import Decimal

if six.PY3:
    def long(value):
        return value


class StorageTestsMixin(object):

    def test_store(self):
        # read defaults
        del sys.modules['constance']
        from constance import config
        self.assertEqual(config.INT_VALUE, 1)
        self.assertEqual(config.LONG_VALUE, long(123456))
        self.assertEqual(config.BOOL_VALUE, True)
        self.assertEqual(config.STRING_VALUE, 'Hello world')
        self.assertEqual(config.UNICODE_VALUE, six.u('Rivière-Bonjour'))
        self.assertEqual(config.DECIMAL_VALUE, Decimal('0.1'))
        self.assertEqual(config.DATETIME_VALUE, datetime(2010, 8, 23, 11, 29, 24))
        self.assertEqual(config.FLOAT_VALUE, 3.1415926536)
        self.assertEqual(config.DATE_VALUE, date(2010, 12, 24))
        self.assertEqual(config.TIME_VALUE, time(23, 59, 59))

        # set values
        config.INT_VALUE = 100
        config.LONG_VALUE = long(654321)
        config.BOOL_VALUE = False
        config.STRING_VALUE = 'Beware the weeping angel'
        config.UNICODE_VALUE = six.u('Québec')
        config.DECIMAL_VALUE = Decimal('1.2')
        config.DATETIME_VALUE = datetime(1977, 10, 2)
        config.FLOAT_VALUE = 2.718281845905
        config.DATE_VALUE = date(2001, 12, 20)
        config.TIME_VALUE = time(1, 59, 0)

        # read again
        self.assertEqual(config.INT_VALUE, 100)
        self.assertEqual(config.LONG_VALUE, long(654321))
        self.assertEqual(config.BOOL_VALUE, False)
        self.assertEqual(config.STRING_VALUE, 'Beware the weeping angel')
        self.assertEqual(config.UNICODE_VALUE, six.u('Québec'))
        self.assertEqual(config.DECIMAL_VALUE, Decimal('1.2'))
        self.assertEqual(config.DATETIME_VALUE, datetime(1977, 10, 2))
        self.assertEqual(config.FLOAT_VALUE, 2.718281845905)
        self.assertEqual(config.DATE_VALUE, date(2001, 12, 20))
        self.assertEqual(config.TIME_VALUE, time(1, 59, 0))

    def test_nonexistent(self):
        from constance import config
        try:
            config.NON_EXISTENT
        except Exception as e:
            self.assertEqual(type(e), AttributeError)

        try:
            config.NON_EXISTENT = 1
        except Exception as e:
            self.assertEqual(type(e), AttributeError)

    def test_missing_values(self):
        from constance import config

        # set some values and leave out others
        config.LONG_VALUE = long(654321)
        config.BOOL_VALUE = False
        config.UNICODE_VALUE = six.u('Québec')
        config.DECIMAL_VALUE = Decimal('1.2')
        config.DATETIME_VALUE = datetime(1977, 10, 2)
        config.DATE_VALUE = date(2001, 12, 20)
        config.TIME_VALUE = time(1, 59, 0)

        self.assertEqual(config.INT_VALUE, 1)  # this should be the default value
        self.assertEqual(config.LONG_VALUE, long(654321))
        self.assertEqual(config.BOOL_VALUE, False)
        self.assertEqual(config.STRING_VALUE, 'Hello world')  # this should be the default value
        self.assertEqual(config.UNICODE_VALUE, six.u('Québec'))
        self.assertEqual(config.DECIMAL_VALUE, Decimal('1.2'))
        self.assertEqual(config.DATETIME_VALUE, datetime(1977, 10, 2))
        self.assertEqual(config.FLOAT_VALUE, 3.1415926536)  # this should be the default value
        self.assertEqual(config.DATE_VALUE, date(2001, 12, 20))
        self.assertEqual(config.TIME_VALUE, time(1, 59, 0))

########NEW FILE########
__FILENAME__ = test_admin
from django.contrib import admin
from django.contrib.auth.models import User, Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase, RequestFactory

from constance.admin import settings, Config


class TestAdmin(TestCase):
    model = Config

    def setUp(self):
        self.rf = RequestFactory()
        self.superuser = User.objects.create_superuser('admin', 'nimda', 'a@a.cz')
        self.normaluser = User.objects.create_user('normal', 'nimda', 'b@b.cz')
        self.normaluser.is_staff = True
        self.normaluser.save()
        self.options = admin.site._registry[self.model]

    def test_changelist(self):
        self.client.login(username='admin', password='nimda')
        request = self.rf.get('/admin/constance/config/')
        request.user = self.superuser
        response = self.options.changelist_view(request, {})
        self.assertEqual(response.status_code, 200)

    def test_custom_auth(self):
        settings.SUPERUSER_ONLY = False
        self.client.login(username='normal', password='nimda')
        request = self.rf.get('/admin/constance/config/')
        request.user = self.normaluser
        self.assertRaises(PermissionDenied,
                          self.options.changelist_view,
                          request, {})
        self.assertFalse(request.user.has_perm('constance.change_config'))

        # reload user to reset permission cache
        request = self.rf.get('/admin/constance/config/')
        request.user = User.objects.get(pk=self.normaluser.pk)

        request.user.user_permissions.add(Permission.objects.get(codename='change_config'))
        self.assertTrue(request.user.has_perm('constance.change_config'))

        response = self.options.changelist_view(request, {})
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = test_database
import sys

from django.test import TestCase

from constance import settings
from constance.config import Config

from tests.storage import StorageTestsMixin


class TestDatabase(TestCase, StorageTestsMixin):

    def setUp(self):
        self.old_backend = settings.BACKEND
        settings.BACKEND = 'constance.backends.database.DatabaseBackend'

    def tearDown(self):
        del sys.modules['constance']
        settings.BACKEND = self.old_backend
        import constance
        constance.config = Config()

########NEW FILE########
__FILENAME__ = test_redis
import sys

from django.test import TestCase

from constance import settings
from constance.config import Config

from tests.storage import StorageTestsMixin


class TestRedis(TestCase, StorageTestsMixin):

    def setUp(self):
        self.old_backend = settings.BACKEND
        settings.BACKEND = 'constance.backends.redisd.RedisBackend'
        del sys.modules['constance']
        from constance import config
        config._backend._rd.clear()

    def tearDown(self):
        del sys.modules['constance']
        from constance import config
        config._backend._rd.clear()
        settings.BACKEND = self.old_backend
        import constance
        constance.config = Config()

########NEW FILE########
__FILENAME__ = urls
from django.contrib import admin

try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include


urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
