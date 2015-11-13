__FILENAME__ = run_redisboard
#!/bin/sh -ex
bogus=''' '
export PYTHONPATH=.
export DJANGO_SETTINGS_MODULE=run_redisboard
secret() {
    tr -cd "[:alnum:]" < /dev/urandom | head -c ${1:-8}
}
chmod +x run_redisboard.py
if [ ! -e .redisboard.venv ]; then
    virtualenv .redisboard.venv
    .redisboard.venv/bin/pip install Django django-redisboard
fi
. .redisboard.venv/bin/activate
if [ ! -e .redisboard.secret ]; then
    echo $(secret 32) > .redisboard.secret
fi
python run_redisboard.py $*
exit
'''

import os
import sys
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '.redisboard.sqlite',
    }
}
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'redisboard',
)
MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)
SECRET_KEY = open('.redisboard.secret').read().strip()
ROOT_URLCONF = 'run_redisboard'
STATIC_URL = '/static/'
ALLOWED_HOSTS = ['*']
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s | %(name)s - %(message)s',
            'datefmt': "%d/%b/%Y %H:%M:%S",
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        "": {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}
from django.conf import settings
if not settings.configured:
    settings.configure(**{k: v for k, v in globals().items() if k.isupper()})

from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()
urlpatterns = patterns("",
    url(r"^static/(?P<path>.*)$", 'django.contrib.staticfiles.views.serve', {'insecure': True}),
    url(r"^", include(admin.site.urls)),
)


if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    if not os.path.exists('.redisboard.sqlite'):
        execute_from_command_line(['run_redisboard', 'syncdb', '--noinput'])
        from django.contrib.auth.models import User
        u = User.objects.create(username='redisboard', is_superuser=True, is_staff=True, is_active=True)
        pwd = os.urandom(8).encode('hex')
        u.set_password(pwd)
        u.save()
        print "="*80
        print """   Credentials:
            USERNAME: redisboard
            PASSWORD: %s""" % pwd
        print "="*80
        from redisboard.models import RedisServer
        RedisServer.objects.create(label="localhost", hostname="127.0.0.1")
    execute_from_command_line(['run_redisboard', 'runserver', '--noreload'] + (sys.argv[1:] if len(sys.argv) > 1 else ['0:8000']))

########NEW FILE########
__FILENAME__ = admin
from functools import update_wrapper

from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.contrib import admin

from .models import RedisServer
from .views import inspect

class RedisServerAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('redisboard/admin.css',)
        }
    list_display = (
        '__unicode__', 'status', 'memory', 'clients', 'details', 'tools'
    )
    list_filter = 'label', 'hostname'
    ordering = ('hostname', 'port')
    def status(self, obj):
        return obj.stats['status']
    status.long_description = _("Status")

    def memory(self, obj):
        return obj.stats['memory']
    memory.long_description = _("Memory")

    def clients(self, obj):
        return obj.stats['clients']
    clients.long_description = _("Clients")

    def tools(self, obj):
        return '<a href="%s">%s</a>' % (
            reverse("admin:redisboard_redisserver_inspect", args=(obj.id,)),
            unicode(_("Inspect"))
        )
    tools.allow_tags = True
    tools.long_description = _("Tools")

    def details(self, obj):
        return '<table class="details">%s</table>' % ''.join(
            "<tr><td>%s</td><td>%s</td></tr>" % i for i in
                obj.stats['brief_details'].items()
        )
    details.allow_tags = True
    details.long_description = _("Details")

    def get_urls(self):
        urlpatterns = super(RedisServerAdmin, self).get_urls()
        try:
            from django.conf.urls import patterns, url
        except ImportError:
            from django.conf.urls.defaults import patterns, url
    
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        return patterns('',
            url(r'^(\d+)/inspect/$',
                wrap(self.inspect_view),
                name='redisboard_redisserver_inspect'),
        ) + urlpatterns

    def inspect_view(self, request, server_id):
        server = get_object_or_404(RedisServer, id=server_id)
        if self.has_change_permission(request, server) and request.user.has_perm('redisboard.can_inspect'):
            return inspect(request, server)
        else:
            return HttpResponseForbidden("You can't inspect this server.")

admin.site.register(RedisServer, RedisServerAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'RedisServer'
        db.create_table('redisboard_redisserver', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('port', self.gf('django.db.models.fields.IntegerField')(default=6379)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=250, null=True, blank=True)),
        ))
        db.send_create_signal('redisboard', ['RedisServer'])


    def backwards(self, orm):
        
        # Deleting model 'RedisServer'
        db.delete_table('redisboard_redisserver')


    models = {
        'redisboard.redisserver': {
            'Meta': {'object_name': 'RedisServer'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '6379'})
        }
    }

    complete_apps = ['redisboard']

########NEW FILE########
__FILENAME__ = 0002_auto__add_unique_redisserver_hostname_port
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'RedisServer', fields ['hostname', 'port']
        db.create_unique('redisboard_redisserver', ['hostname', 'port'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'RedisServer', fields ['hostname', 'port']
        db.delete_unique('redisboard_redisserver', ['hostname', 'port'])


    models = {
        'redisboard.redisserver': {
            'Meta': {'unique_together': "(('hostname', 'port'),)", 'object_name': 'RedisServer'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '6379'})
        }
    }

    complete_apps = ['redisboard']

########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_redisserver_port
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'RedisServer.port'
        db.alter_column('redisboard_redisserver', 'port', self.gf('django.db.models.fields.IntegerField')(null=True))


    def backwards(self, orm):
        
        # Changing field 'RedisServer.port'
        db.alter_column('redisboard_redisserver', 'port', self.gf('django.db.models.fields.IntegerField')())


    models = {
        'redisboard.redisserver': {
            'Meta': {'unique_together': "(('hostname', 'port'),)", 'object_name': 'RedisServer'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '6379', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['redisboard']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_redisserver_sampling_threshold__add_field_redisserver_
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'RedisServer.sampling_threshold'
        db.add_column('redisboard_redisserver', 'sampling_threshold', self.gf('django.db.models.fields.IntegerField')(default=1000), keep_default=False)

        # Adding field 'RedisServer.sampling_size'
        db.add_column('redisboard_redisserver', 'sampling_size', self.gf('django.db.models.fields.IntegerField')(default=200), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'RedisServer.sampling_threshold'
        db.delete_column('redisboard_redisserver', 'sampling_threshold')

        # Deleting field 'RedisServer.sampling_size'
        db.delete_column('redisboard_redisserver', 'sampling_size')


    models = {
        'redisboard.redisserver': {
            'Meta': {'unique_together': "(('hostname', 'port'),)", 'object_name': 'RedisServer'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '6379', 'null': 'True', 'blank': 'True'}),
            'sampling_size': ('django.db.models.fields.IntegerField', [], {'default': '200'}),
            'sampling_threshold': ('django.db.models.fields.IntegerField', [], {'default': '1000'})
        }
    }

    complete_apps = ['redisboard']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_redisserver_label
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'RedisServer.label'
        db.add_column('redisboard_redisserver', 'label', self.gf('django.db.models.fields.CharField')(default='', max_length=50, blank=True))


    def backwards(self, orm):
        
        # Deleting field 'RedisServer.label'
        db.delete_column('redisboard_redisserver', 'label')


    models = {
        'redisboard.redisserver': {
            'Meta': {'unique_together': "(('hostname', 'port'),)", 'object_name': 'RedisServer'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '6379', 'null': 'True', 'blank': 'True'}),
            'sampling_size': ('django.db.models.fields.IntegerField', [], {'default': '200'}),
            'sampling_threshold': ('django.db.models.fields.IntegerField', [], {'default': '1000'})
        }
    }

    complete_apps = ['redisboard']

########NEW FILE########
__FILENAME__ = 0006_auto__chg_field_redisserver_label
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'RedisServer.label'
        db.alter_column('redisboard_redisserver', 'label', self.gf('django.db.models.fields.CharField')(max_length=50, null=True))


    def backwards(self, orm):
        
        # Changing field 'RedisServer.label'
        db.alter_column('redisboard_redisserver', 'label', self.gf('django.db.models.fields.CharField')(max_length=50))


    models = {
        'redisboard.redisserver': {
            'Meta': {'unique_together': "(('hostname', 'port'),)", 'object_name': 'RedisServer'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {'default': '6379', 'null': 'True', 'blank': 'True'}),
            'sampling_size': ('django.db.models.fields.IntegerField', [], {'default': '200'}),
            'sampling_threshold': ('django.db.models.fields.IntegerField', [], {'default': '1000'})
        }
    }

    complete_apps = ['redisboard']

########NEW FILE########
__FILENAME__ = models
import re
from datetime import datetime, timedelta
import redis

from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings

from .utils import cached_property

REDISBOARD_DETAIL_FILTERS = [re.compile(name) for name in getattr(settings, 'REDISBOARD_DETAIL_FILTERS', (
    'aof_enabled', 'bgrewriteaof_in_progress', 'bgsave_in_progress',
    'changes_since_last_save', 'db.*', 'last_save_time', 'multiplexing_api',
    'total_commands_processed', 'total_connections_received', 'uptime_in_days',
    'uptime_in_seconds', 'vm_enabled', 'redis_version'
))]
REDISBOARD_DETAIL_TIMESTAMP_KEYS = getattr(settings, 'REDISBOARD_DETAIL_TIMESTAMP_KEYS', (
    'last_save_time',
))
REDISBOARD_DETAIL_SECONDS_KEYS = getattr(settings, 'REDISBOARD_DETAIL_SECONDS_KEYS', (
    'uptime_in_seconds',
))

def prettify(key, value):
    if key in REDISBOARD_DETAIL_SECONDS_KEYS:
        return key, timedelta(seconds=value)
    elif key in REDISBOARD_DETAIL_TIMESTAMP_KEYS:
        return key, datetime.fromtimestamp(value)
    else:
        return key, value

class RedisServer(models.Model):
    class Meta:
        unique_together = ('hostname', 'port')
        verbose_name = _("Redis Server")
        verbose_name_plural = _("Redis Servers")
        permissions = (
            ("can_inspect", "Can inspect redis servers"),
        )

    label = models.CharField(
        _('Label'),
        max_length = 50,
        blank = True,
        null = True,
    )

    hostname = models.CharField(
        _("Hostname"),
        max_length = 250,
        help_text = _('This can also be the absolute path to a redis socket')
    )

    port = models.IntegerField(_("Port"), validators=[
        MaxValueValidator(65535), MinValueValidator(1)
    ], default=6379, blank=True, null=True)
    password = models.CharField(_("Password"), max_length=250,
                                null=True, blank=True)

    sampling_threshold = models.IntegerField(
        _("Sampling threshold"),
        default = 1000,
        help_text = _("Number of keys after which only a sample (of random keys) is shown on the inspect page.")
    )
    sampling_size = models.IntegerField(
        _("Sampling size"),
        default = 200,
        help_text = _("Number of random keys shown when sampling is used. Note that each key translates to a RANDOMKEY call in redis.")
    )

    def clean(self):
        if not self.hostname.startswith('/') and not self.port:
            raise ValidationError(_('Please provide either a hostname AND a port or the path to a redis socket'))


    @cached_property
    def connection(self):
        if self.hostname.startswith('/'):
            unix_socket_path = self.hostname
            hostname = None
        else:
            hostname = self.hostname
            unix_socket_path = None
        return redis.Redis(
            host = hostname,
            port = self.port,
            password = self.password,
            unix_socket_path=unix_socket_path,
        )

    @connection.deleter
    def connection(self, value):
        value.connection_pool.disconnect()

    @cached_property
    def stats(self):
        try:
            info = self.connection.info()
            return {
                'status': 'UP',
                'details': info,
                'memory': "%s (peak: %s)" % (
                    info['used_memory_human'],
                    info.get('used_memory_peak_human', 'n/a')
                ),
                'clients': info['connected_clients'],
                'brief_details': SortedDict(
                    prettify(k, v)
                    for k, v in sorted(info.items(), key=lambda (k,v): k)
                    if any(name.match(k) for name in REDISBOARD_DETAIL_FILTERS)
                )
            }
        except redis.exceptions.ConnectionError:
            return {
                'status': 'DOWN',
                'clients': 'n/a',
                'memory': 'n/a',
                'details': {},
                'brief_details': {},
            }
        except redis.exceptions.ResponseError, e:
            return {
                'status': 'ERROR: %s' % e.args,
                'clients': 'n/a',
                'memory': 'n/a',
                'details': {},
                'brief_details': {},
            }


    def __unicode__(self):
        if self.label:
            label = '%s (%%s)' % self.label
        else:
            label = '%s'

        if self.port:
            label = label % ('%s:%s' % (self.hostname, self.port))
        else:
            label = label % self.hostname

        return label

########NEW FILE########
__FILENAME__ = utils
# shamelessly taken from kombu.utils

class LazySlicingIterable(object):
    def __init__(self, length_getter, items_getter):
        self.length_getter = length_getter
        self.items_getter = items_getter

    def __len__(self):
        return self.length_getter()

    def __getitem__(self, k):
        if isinstance(k, int):
            return self.items_getter(k, k)
        elif isinstance(k, slice):
            if k.step:
                raise RuntimeError("Can't use steps for slicing.")
            return self.items_getter(k.start, k.stop)
        else:
            raise TypeError("Must be int or slice.")

class cached_property(object):
    """Property descriptor that caches the return value
    of the get function.

    *Examples*

    .. code-block:: python

        @cached_property
        def connection(self):
            return Connection()

        @connection.setter  # Prepares stored value
        def connection(self, value):
            if value is None:
                raise TypeError("Connection must be a connection")
            return value

        @connection.deleter
        def connection(self, value):
            # Additional action to do at del(self.attr)
            if value is not None:
                print("Connection %r deleted" % (value, ))

    """

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.__get = fget
        self.__set = fset
        self.__del = fdel
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        try:
            return obj.__dict__[self.__name__]
        except KeyError:
            value = obj.__dict__[self.__name__] = self.__get(obj)
            return value

    def __set__(self, obj, value):
        if obj is None:
            return self
        if self.__set is not None:
            value = self.__set(obj, value)
        obj.__dict__[self.__name__] = value

    def __delete__(self, obj):
        if obj is None:
            return self
        try:
            value = obj.__dict__.pop(self.__name__)
        except KeyError:
            pass
        else:
            if self.__del is not None:
                self.__del(obj, value)

    def setter(self, fset):
        return self.__class__(self.__get, fset, self.__del)

    def deleter(self, fdel):
        return self.__class__(self.__get, self.__set, fdel)

########NEW FILE########
__FILENAME__ = views
from logging import getLogger
logger = getLogger(__name__)

from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils.datastructures import SortedDict
from django.conf import settings
from django.utils.functional import curry
from django.http import HttpResponseNotFound

from redis.exceptions import ResponseError

from .utils import LazySlicingIterable

REDISBOARD_ITEMS_PER_PAGE = getattr(settings, 'REDISBOARD_ITEMS_PER_PAGE', 100)

def safeint(value):
    try:
        return int(value)
    except ValueError:
        return value

def _fixup_pair((a, b)):
    return a, safeint(b)

LENGTH_GETTERS = {
    'list': lambda conn, key: conn.llen(key),
    'string': lambda conn, key: conn.strlen(key),
    'set': lambda conn, key: conn.scard(key),
    'zset': lambda conn, key: conn.zcount(key, '-inf', '+inf'),
    'hash': lambda conn, key: conn.hlen(key),
}

def _get_key_info(conn, key):
    try:
        details = conn.execute_command('DEBUG', 'OBJECT', key)
        obj_type = conn.type(key)
        obj_length = LENGTH_GETTERS[obj_type](conn, key)
        return {
            'type': conn.type(key),
            'name': key,
            'details': details if isinstance(details, dict) else dict(
                _fixup_pair(i.split(':')) for i in details.split() if ':' in i
            ),
            'length': obj_length,
            'ttl': conn.ttl(key),
        }
    except ResponseError, e:
        logger.exception("Failed to get details for key %r", key)
        return {
            'type': "n/a",
            'length': "n/a",
            'name': key,
            'details': {},
            'error': str(e),
            'ttl': "n/a",
        }

VALUE_GETTERS = {
    'list': lambda conn, key, start=0, end=-1: [(pos+start, val) for pos, val in enumerate(conn.lrange(key, start, end))],
    'string': lambda conn, key, *args: [('string', conn.get(key))],
    'set': lambda conn, key, *args: list(enumerate(conn.smembers(key))),
    'zset': lambda conn, key, start=0, end=-1: [(pos+start, val) for pos, val in enumerate(conn.zrange(key, start, end))],
    'hash': lambda conn, key, *args: conn.hgetall(key).items(),
    'n/a': lambda conn, key, *args: (),
}

def _get_key_details(conn, db, key, page):
    conn.execute_command('SELECT', db)
    details = _get_key_info(conn, key)
    details['db'] = db
    if details['type'] in ('list', 'zset'):
        details['data'] = Paginator(
            LazySlicingIterable(
                lambda: details['length'],
                curry(VALUE_GETTERS[details['type']], conn, key)
            ),
            REDISBOARD_ITEMS_PER_PAGE
        ).page(page)
    else:
        details['data'] = VALUE_GETTERS[details['type']](conn, key)


    return details

def _get_db_summary(server, db):
    conn = server.connection
    conn.execute_command('SELECT', db)
    return dict(size=conn.dbsize())

def _get_db_details(server, db):
    conn = server.connection
    conn.execute_command('SELECT', db)
    size = conn.dbsize()
    keys = conn.keys()
    key_details = {}
    if size > server.sampling_threshold:
        sampling = True
        for _ in xrange(server.sampling_size):
            key = conn.randomkey()
            key_details[key] = _get_key_info(conn, key)
    else:
        sampling = False
        for key in keys:
            key_details[key] = _get_key_info(conn, key)
    return dict(
        keys = key_details,
        sampling = sampling,
    )



def inspect(request, server):
    stats = server.stats
    conn = server.connection
    database_details = SortedDict()
    key_details = None

    if stats['status'] == 'UP':
        if 'key' in request.GET:
            key = request.GET['key']
            db = request.GET.get('db', 0)
            page = request.GET.get('page', 1)
            key_details = _get_key_details(conn, db, key, page)
        else:
            databases = sorted(name[2:] for name in conn.info() if name.startswith('db'))
            total_size = 0
            for db in databases:
                database_details[db] = summary = _get_db_summary(server, db)
                total_size += summary['size']
            if total_size < server.sampling_threshold:
                for db in databases:
                    database_details[db].update(
                        _get_db_details(server, db),
                        active = True,
                    )
            else:
                if 'db' in request.GET:
                    db = request.GET['db']
                    if db in database_details:
                        database_details[db].update(
                            _get_db_details(server, db),
                            active = True,
                        )
                    else:
                        return HttpResponseNotFound("Unknown database.")
    return render(request, "redisboard/inspect.html", {
        'databases': database_details,
        'key_details': key_details,
        'original': server,
        'stats': stats,
        'app_label': 'redisboard',
    })

########NEW FILE########
