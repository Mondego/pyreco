__FILENAME__ = adminx
import xadmin
from xadmin import views
from models import IDC, Host, MaintainLog, HostGroup, AccessRecord
from xadmin.layout import Main, TabHolder, Tab, Fieldset, Row, Col, AppendedText, Side
from xadmin.plugins.inline import Inline
from xadmin.plugins.batch import BatchChangeAction

class MainDashboard(object):
    widgets = [
        [
            {"type": "html", "title": "Test Widget", "content": "<h3> Welcome to Xadmin! </h3><p>Join Online Group: <br/>QQ Qun : 282936295</p>"},
            {"type": "chart", "model": "app.accessrecord", 'chart': 'user_count', 'params': {'_p_date__gte': '2013-01-08', 'p': 1, '_p_date__lt': '2013-01-29'}},
            {"type": "list", "model": "app.host", 'params': {
                'o':'-guarantee_date'}},
        ],
        [
            {"type": "qbutton", "title": "Quick Start", "btns": [{'model': Host}, {'model':IDC}, {'title': "Google", 'url': "http://www.google.com"}]},
            {"type": "addform", "model": MaintainLog},
        ]
    ]
xadmin.site.register(views.website.IndexView, MainDashboard)


class BaseSetting(object):
    enable_themes = True
    use_bootswatch = True
xadmin.site.register(views.BaseAdminView, BaseSetting)


class GlobalSetting(object):
    global_search_models = [Host, IDC]
    global_models_icon = {
        Host: 'fa fa-laptop', IDC: 'fa fa-cloud'
    }
    menu_style = 'default'#'accordion'
xadmin.site.register(views.CommAdminView, GlobalSetting)


class MaintainInline(object):
    model = MaintainLog
    extra = 1
    style = 'accordion'


class IDCAdmin(object):
    list_display = ('name', 'description', 'create_time')
    list_display_links = ('name',)
    wizard_form_list = [
        ('First\'s Form', ('name', 'description')),
        ('Second Form', ('contact', 'telphone', 'address')),
        ('Thread Form', ('customer_id',))
    ]

    search_fields = ['name']
    relfield_style = 'fk-ajax'
    reversion_enable = True

    actions = [BatchChangeAction, ]
    batch_fields = ('contact', 'create_time')


class HostAdmin(object):
    def open_web(self, instance):
        return "<a href='http://%s' target='_blank'>Open</a>" % instance.ip
    open_web.short_description = "Acts"
    open_web.allow_tags = True
    open_web.is_column = True

    list_display = ('name', 'idc', 'guarantee_date', 'service_type',
                    'status', 'open_web', 'description')
    list_display_links = ('name',)

    raw_id_fields = ('idc',)
    style_fields = {'system': "radio-inline"}

    search_fields = ['name', 'ip', 'description']
    list_filter = ['idc', 'guarantee_date', 'status', 'brand', 'model',
                   'cpu', 'core_num', 'hard_disk', 'memory', ('service_type',xadmin.filters.MultiSelectFieldListFilter)]
    
    list_quick_filter = ['service_type',{'field':'idc__name','limit':10}]
    list_bookmarks = [{'title': "Need Guarantee", 'query': {'status__exact': 2}, 'order': ('-guarantee_date',), 'cols': ('brand', 'guarantee_date', 'service_type')}]

    show_detail_fields = ('idc',)
    list_editable = (
        'name', 'idc', 'guarantee_date', 'service_type', 'description')
    save_as = True

    aggregate_fields = {"guarantee_date": "min"}
    grid_layouts = ('table', 'thumbnails')

    form_layout = (
        Main(
            TabHolder(
                Tab('Comm Fields',
                    Fieldset('Company data',
                             'name', 'idc',
                             description="some comm fields, required"
                             ),
                    Inline(MaintainLog),
                    ),
                Tab('Extend Fields',
                    Fieldset('Contact details',
                             'service_type',
                             Row('brand', 'model'),
                             Row('cpu', 'core_num'),
                             Row(AppendedText(
                                 'hard_disk', 'G'), AppendedText('memory', "G")),
                             'guarantee_date'
                             ),
                    ),
            ),
        ),
        Side(
            Fieldset('Status data',
                     'status', 'ssh_port', 'ip'
                     ),
        )
    )
    inlines = [MaintainInline]
    reversion_enable = True
    
    data_charts = {
        "host_service_type_counts": {'title': u"Host service type count", "x-field": "service_type", "y-field": ("service_type",), 
                              "option": {
                                         "series": {"bars": {"align": "center", "barWidth": 0.8,'show':True}}, 
                                         "xaxis": {"aggregate": "count", "mode": "categories"},
                                         },
                              },
    }
    
class HostGroupAdmin(object):
    list_display = ('name', 'description')
    list_display_links = ('name',)

    search_fields = ['name']
    style_fields = {'hosts': 'checkbox-inline'}


class MaintainLogAdmin(object):
    list_display = (
        'host', 'maintain_type', 'hard_type', 'time', 'operator', 'note')
    list_display_links = ('host',)

    list_filter = ['host', 'maintain_type', 'hard_type', 'time', 'operator']
    search_fields = ['note']

    form_layout = (
        Col("col2",
            Fieldset('Record data',
                     'time', 'note',
                     css_class='unsort short_label no_title'
                     ),
            span=9, horizontal=True
            ),
        Col("col1",
            Fieldset('Comm data',
                     'host', 'maintain_type'
                     ),
            Fieldset('Maintain details',
                     'hard_type', 'operator'
                     ),
            span=3
            )
    )
    reversion_enable = True


class AccessRecordAdmin(object):
    def avg_count(self, instance):
        return int(instance.view_count / instance.user_count)
    avg_count.short_description = "Avg Count"
    avg_count.allow_tags = True
    avg_count.is_column = True

    list_display = ('date', 'user_count', 'view_count', 'avg_count')
    list_display_links = ('date',)

    list_filter = ['date', 'user_count', 'view_count']
    actions = None
    aggregate_fields = {"user_count": "sum", 'view_count': "sum"}

    refresh_times = (3, 5, 10)
    data_charts = {
        "user_count": {'title': u"User Report", "x-field": "date", "y-field": ("user_count", "view_count"), "order": ('date',)},
        "avg_count": {'title': u"Avg Report", "x-field": "date", "y-field": ('avg_count',), "order": ('date',)},
        "per_month": {'title': u"Monthly Users", "x-field": "_chart_month", "y-field": ("user_count", ), 
                              "option": {
                                         "series": {"bars": {"align": "center", "barWidth": 0.8,'show':True}}, 
                                         "xaxis": {"aggregate": "sum", "mode": "categories"},
                                         },
                            },
    }
    
    def _chart_month(self,obj):
        return obj.date.strftime("%B")
        

xadmin.site.register(Host, HostAdmin)
xadmin.site.register(HostGroup, HostGroupAdmin)
xadmin.site.register(MaintainLog, MaintainLogAdmin)
xadmin.site.register(IDC, IDCAdmin)
xadmin.site.register(AccessRecord, AccessRecordAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models


SERVER_STATUS = (
    (0, u"Normal"),
    (1, u"Down"),
    (2, u"No Connect"),
    (3, u"Error"),
)
SERVICE_TYPES = (
    ('moniter', u"Moniter"),
    ('lvs', u"LVS"),
    ('db', u"Database"),
    ('analysis', u"Analysis"),
    ('admin', u"Admin"),
    ('storge', u"Storge"),
    ('web', u"WEB"),
    ('email', u"Email"),
    ('mix', u"Mix"),
)


class IDC(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField()

    contact = models.CharField(max_length=32)
    telphone = models.CharField(max_length=32)
    address = models.CharField(max_length=128)
    customer_id = models.CharField(max_length=128)

    create_time = models.DateField(auto_now=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u"IDC"
        verbose_name_plural = verbose_name


class Host(models.Model):
    idc = models.ForeignKey(IDC)
    name = models.CharField(max_length=64)
    nagios_name = models.CharField(u"Nagios Host ID", max_length=64, blank=True, null=True)
    ip = models.IPAddressField(blank=True, null=True)
    internal_ip = models.IPAddressField(blank=True, null=True)
    user = models.CharField(max_length=64)
    password = models.CharField(max_length=128)
    ssh_port = models.IntegerField(blank=True, null=True)
    status = models.SmallIntegerField(choices=SERVER_STATUS)

    brand = models.CharField(max_length=64, choices=[(i, i) for i in (u"DELL", u"HP", u"Other")])
    model = models.CharField(max_length=64)
    cpu = models.CharField(max_length=64)
    core_num = models.SmallIntegerField(choices=[(i * 2, "%s Cores" % (i * 2)) for i in range(1, 15)])
    hard_disk = models.IntegerField()
    memory = models.IntegerField()

    system = models.CharField(u"System OS", max_length=32, choices=[(i, i) for i in (u"CentOS", u"FreeBSD", u"Ubuntu")])
    system_version = models.CharField(max_length=32)
    system_arch = models.CharField(max_length=32, choices=[(i, i) for i in (u"x86_64", u"i386")])

    create_time = models.DateField()
    guarantee_date = models.DateField()
    service_type = models.CharField(max_length=32, choices=SERVICE_TYPES)
    description = models.TextField()

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u"Host"
        verbose_name_plural = verbose_name


class MaintainLog(models.Model):
    host = models.ForeignKey(Host)
    maintain_type = models.CharField(max_length=32)
    hard_type = models.CharField(max_length=16)
    time = models.DateTimeField()
    operator = models.CharField(max_length=16)
    note = models.TextField()

    def __unicode__(self):
        return '%s maintain-log [%s] %s %s' % (self.host.name, self.time.strftime('%Y-%m-%d %H:%M:%S'),
                                               self.maintain_type, self.hard_type)

    class Meta:
        verbose_name = u"Maintain Log"
        verbose_name_plural = verbose_name


class HostGroup(models.Model):

    name = models.CharField(max_length=32)
    description = models.TextField()
    hosts = models.ManyToManyField(
        Host, verbose_name=u'Hosts', blank=True, related_name='groups')

    class Meta:
        verbose_name = u"Host Group"
        verbose_name_plural = verbose_name

    def __unicode__(self):
        return self.name


class AccessRecord(models.Model):
    date = models.DateField()
    user_count = models.IntegerField()
    view_count = models.IntegerField()

    class Meta:
        verbose_name = u"Access Record"
        verbose_name_plural = verbose_name

    def __unicode__(self):
        return "%s Access Record" % self.date.strftime('%Y-%m-%d')

########NEW FILE########
__FILENAME__ = settings
# Django settings for wictrl project.

import sys
import os.path

reload(sys)
sys.setdefaultencoding('utf-8')
gettext = lambda s: s

PROJECT_ROOT = os.path.join(
    os.path.realpath(os.path.dirname(__file__)), os.pardir)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(PROJECT_ROOT, 'data.db'),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}
# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = '*'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

LANGUAGES = (
    ('en', gettext('English')),
    ('zh_CN', gettext('Chinese')),
)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = 'static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '5=!nss_+^nvyyc_j(tdcf!7(_una*3gtw+_8v5jaa=)j0g^d_2'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'demo.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'demo.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'xadmin',
    'crispy_forms',
    #'reversion',

    'app',
)

DATE_FORMAT = 'Y-m-d'
DATETIME_FORMAT = 'Y-m-d H:i'
TIME_FORMAT = 'H:i'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
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
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        # 'django.db.backends': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG',
        # }
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
import xadmin
xadmin.autodiscover()

# from xadmin.plugins import xversion
# xversion.register_models()

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include(xadmin.site.urls))
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for wictrl project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))
    sys.path.insert(0, os.path.join(PROJECT_ROOT, os.pardir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import shutil
import sys
import tempfile

TEST_ROOT = os.path.realpath(os.path.dirname(__file__))
RUNTESTS_DIR = os.path.join(TEST_ROOT, 'xtests')

sys.path.insert(0, os.path.join(TEST_ROOT, os.pardir))
sys.path.insert(0, RUNTESTS_DIR)

TEST_TEMPLATE_DIR = 'templates'
TEMP_DIR = tempfile.mkdtemp(prefix='django_')
os.environ['DJANGO_TEST_TEMP_DIR'] = TEMP_DIR

ALWAYS_INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'xadmin',
    'crispy_forms',
]

def get_test_modules():
    modules = []
    for f in os.listdir(RUNTESTS_DIR):
        if (f.startswith('__init__') or
            f.startswith('.') or
            f.startswith('sql') or not os.path.isdir(os.path.join(RUNTESTS_DIR, f))):
            continue
        modules.append(f)
    return modules

def setup(verbosity, test_labels):
    from django.conf import settings
    state = {
        'INSTALLED_APPS': settings.INSTALLED_APPS,
        'ROOT_URLCONF': getattr(settings, "ROOT_URLCONF", ""),
        'TEMPLATE_DIRS': settings.TEMPLATE_DIRS,
        'USE_I18N': settings.USE_I18N,
        'LOGIN_URL': settings.LOGIN_URL,
        'LANGUAGE_CODE': settings.LANGUAGE_CODE,
        'MIDDLEWARE_CLASSES': settings.MIDDLEWARE_CLASSES,
        'STATIC_URL': settings.STATIC_URL,
        'STATIC_ROOT': settings.STATIC_ROOT,
    }

    # Redirect some settings for the duration of these tests.
    settings.INSTALLED_APPS = ALWAYS_INSTALLED_APPS
    settings.ROOT_URLCONF = 'urls'
    settings.STATIC_URL = '/static/'
    settings.STATIC_ROOT = os.path.join(TEMP_DIR, 'static')
    settings.TEMPLATE_DIRS = (os.path.join(RUNTESTS_DIR, TEST_TEMPLATE_DIR),)
    settings.USE_I18N = True
    settings.LANGUAGE_CODE = 'en'
    settings.MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.common.CommonMiddleware',
    )
    settings.SITE_ID = 1
    # For testing comment-utils, we require the MANAGERS attribute
    # to be set, so that a test email is sent out which we catch
    # in our tests.
    settings.MANAGERS = ("admin@xadmin.io",)

    # Load all the ALWAYS_INSTALLED_APPS.
    # (This import statement is intentionally delayed until after we
    # access settings because of the USE_I18N dependency.)
    from django.db.models.loading import get_apps, load_app
    get_apps()

    # Load all the test model apps.
    test_labels_set = set([label.split('.')[0] for label in test_labels])
    test_modules = get_test_modules()

    for module_name in test_modules:
        module_label = '.'.join(['xtests', module_name])
        # if the module was named on the command line, or
        # no modules were named (i.e., run all), import
        # this module and add it to the list to test.
        if not test_labels or module_name in test_labels_set:
            if verbosity >= 2:
                print "Importing application %s" % module_name
            mod = load_app(module_label)
            if mod:
                if module_label not in settings.INSTALLED_APPS:
                    settings.INSTALLED_APPS.append(module_label)

    return state

def teardown(state):
    from django.conf import settings
    # Removing the temporary TEMP_DIR. Ensure we pass in unicode
    # so that it will successfully remove temp trees containing
    # non-ASCII filenames on Windows. (We're assuming the temp dir
    # name itself does not contain non-ASCII characters.)
    shutil.rmtree(unicode(TEMP_DIR))
    # Restore the old settings.
    for key, value in state.items():
        setattr(settings, key, value)

def django_tests(verbosity, interactive, failfast, test_labels):
    from django.conf import settings
    state = setup(verbosity, test_labels)
    extra_tests = []

    # Run the test suite, including the extra validation tests.
    from django.test.utils import get_runner
    if not hasattr(settings, 'TEST_RUNNER'):
        settings.TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner'
    TestRunner = get_runner(settings)

    test_runner = TestRunner(verbosity=verbosity, interactive=interactive,
        failfast=failfast)
    failures = test_runner.run_tests(test_labels or get_test_modules(), extra_tests=extra_tests)

    teardown(state)
    return failures

if __name__ == "__main__":
    from optparse import OptionParser
    usage = "%prog [options] [module module module ...]"
    parser = OptionParser(usage=usage)
    parser.add_option(
        '-v','--verbosity', action='store', dest='verbosity', default='1',
        type='choice', choices=['0', '1', '2', '3'],
        help='Verbosity level; 0=minimal output, 1=normal output, 2=all '
             'output')
    parser.add_option(
        '--noinput', action='store_false', dest='interactive', default=True,
        help='Tells Django to NOT prompt the user for input of any kind.')
    parser.add_option(
        '--failfast', action='store_true', dest='failfast', default=False,
        help='Tells Django to stop running the test suite after first failed '
             'test.')
    parser.add_option(
        '--settings',
        help='Python path to settings module, e.g. "myproject.settings". If '
             'this isn\'t provided, the DJANGO_SETTINGS_MODULE environment '
             'variable will be used.')
    parser.add_option(
        '--liveserver', action='store', dest='liveserver', default=None,
        help='Overrides the default address where the live server (used with '
             'LiveServerTestCase) is expected to run from. The default value '
             'is localhost:8081.'),
    options, args = parser.parse_args()
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    elif "DJANGO_SETTINGS_MODULE" not in os.environ:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    else:
        options.settings = os.environ['DJANGO_SETTINGS_MODULE']

    if options.liveserver is not None:
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = options.liveserver

    failures = django_tests(int(options.verbosity), options.interactive,
                            options.failfast, args)
    if failures:
        sys.exit(bool(failures))

########NEW FILE########
__FILENAME__ = settings
DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

# Required for Django 1.4+
STATIC_URL = '/static/'

# Required for Django 1.5+
SECRET_KEY = 'abc123'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include

urlpatterns = patterns('',
    (r'^view_base/', include('xtests.view_base.urls')),
)
########NEW FILE########
__FILENAME__ = base
from django.test import TestCase
from django.contrib.auth.models import User
from django.test.client import RequestFactory

class BaseTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _create_superuser(self, username):
        return User.objects.create(username=username, is_superuser=True)

    def _mocked_request(self, url, user='admin'):
        request = self.factory.get(url)
        request.user = isinstance(user, User) and user or self._create_superuser(user)
        request.session = {}
        return request
########NEW FILE########
__FILENAME__ = models
from django.db import models


class ModelA(models.Model):
    name = models.CharField(max_length=64)
########NEW FILE########
__FILENAME__ = tests
from django.http import HttpResponse

from xtests.base import BaseTest
from xadmin.sites import AdminSite
from xadmin.views import BaseAdminView, BaseAdminPlugin, ModelAdminView, filter_hook

from models import ModelA


class ModelAAdmin(object):
    pass


class TestAdminView(BaseAdminView):
    site_title = "TEST TITLE"

    @filter_hook
    def get_title(self):
        return self.site_title

    def get(self, request):
        return HttpResponse(self.site_title)


class TestOption(object):
    site_title = "TEST PROJECT"


class TestPlugin(BaseAdminPlugin):

    def get_title(self, title):
        return "%s PLUGIN" % title


class TestModelAdminView(ModelAdminView):

    def get(self, request, obj_id):
        return HttpResponse(str(obj_id))


class AdminSiteTest(BaseTest):

    def get_site(self):
        return AdminSite('test', 'test_app')

    def test_register_model(self):
        site = self.get_site()

        site.register(ModelA, ModelAAdmin)

        self.assertIn(ModelA, site._registry.keys())

    def test_unregister_model(self):
        site = self.get_site()

        site.register(ModelA, ModelAAdmin)
        site.unregister(ModelA)

        self.assertNotIn(ModelA, site._registry.keys())

    def test_viewoption(self):
        site = self.get_site()

        site.register_view(r"^test/$", TestAdminView, 'test')
        site.register(TestAdminView, TestOption)

        c = site.get_view_class(TestAdminView)
        self.assertEqual(c.site_title, "TEST PROJECT")

    def test_plugin(self):
        site = self.get_site()

        site.register_view(r"^test/$", TestAdminView, 'test')
        site.register_plugin(TestPlugin, TestAdminView)

        c = site.get_view_class(TestAdminView)
        self.assertIn(TestPlugin, c.plugin_classes)

        cv = c(self._mocked_request('test/'))

        self.assertEqual(cv.get_title(), "TEST TITLE PLUGIN")

    def test_get_urls(self):
        site = self.get_site()

        site.register(ModelA, ModelAAdmin)
        site.register_view(r"^test/$", TestAdminView, 'test')
        site.register_modelview(
            r'^(.+)/test/$', TestModelAdminView, name='%s_%s_test')

        urls, app_name, namespace = site.urls

        self.assertEqual(app_name, 'test_app')
        self.assertEqual(namespace, 'test')

########NEW FILE########
__FILENAME__ = adminx
from xadmin.sites import AdminSite
from xadmin.views import BaseAdminView, CommAdminView, ListAdminView
from models import ModelA, ModelB

site = AdminSite('views_base')

class ModelAAdmin(object):
    test_model_attr = 'test_model'
    model_icon = 'flag'

class TestBaseView(BaseAdminView):
    pass

class TestCommView(CommAdminView):
    global_models_icon = {ModelB: 'test'}

class TestAView(BaseAdminView):
    pass

class OptionA(object):
    option_attr = 'option_test'

site.register_modelview(r'^list$', ListAdminView, name='%s_%s_list')

site.register_view(r"^test/base$", TestBaseView, 'test')
site.register_view(r"^test/comm$", TestCommView, 'test_comm')
site.register_view(r"^test/a$", TestAView, 'test_a')

site.register(ModelA, ModelAAdmin)
site.register(ModelB)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class ModelA(models.Model):
    name = models.CharField(max_length=64)

class ModelB(models.Model):
    name = models.CharField(max_length=64)
########NEW FILE########
__FILENAME__ = tests

from django.contrib.auth.models import User

from xtests.base import BaseTest
from xadmin.views import BaseAdminView, BaseAdminPlugin, ModelAdminView, ListAdminView

from models import ModelA, ModelB
from adminx import site, ModelAAdmin, TestBaseView, TestCommView, TestAView, OptionA

class BaseAdminTest(BaseTest):

    def setUp(self):
        super(BaseAdminTest, self).setUp()
        self.test_view_class = site.get_view_class(TestBaseView)
        self.test_view = self.test_view_class(self._mocked_request('test/'))

    def test_get_view(self):
        test_a = self.test_view.get_view(TestAView, OptionA, opts={'test_attr': 'test'})

        self.assertTrue(isinstance(test_a, TestAView))
        self.assertTrue(isinstance(test_a, OptionA))

        self.assertEqual(test_a.option_attr, 'option_test')
        self.assertEqual(test_a.test_attr, 'test')

    def test_model_view(self):
        test_model = self.test_view.get_model_view(ListAdminView, ModelA)

        self.assertTrue(isinstance(test_model, ModelAAdmin))
        self.assertEqual(test_model.model, ModelA)
        self.assertEqual(test_model.test_model_attr, 'test_model')

    def test_admin_url(self):
        test_url = self.test_view.get_admin_url('test')
        self.assertEqual(test_url, '/view_base/test/base')

    def test_model_url(self):
        test_url = self.test_view.get_model_url(ModelA, 'list')
        self.assertEqual(test_url, '/view_base/view_base/modela/list')

    def test_has_model_perm(self):
        test_user = User.objects.create(username='test_user')

        self.assertFalse(self.test_view.has_model_perm(ModelA, 'change', test_user))

        # Admin User
        self.assertTrue(self.test_view.has_model_perm(ModelA, 'change'))


class CommAdminTest(BaseTest):

    def setUp(self):
        super(CommAdminTest, self).setUp()
        self.test_view_class = site.get_view_class(TestCommView)
        self.test_view = self.test_view_class(self._mocked_request('test/comm'))

    def test_model_icon(self):  
        self.assertEqual(self.test_view.get_model_icon(ModelA), 'flag')
        self.assertEqual(self.test_view.get_model_icon(ModelB), 'test')






########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include
from adminx import site

urlpatterns = patterns('',
    (r'', include(site.urls)),
)
########NEW FILE########
__FILENAME__ = adminx
import xadmin
from models import UserSettings
from xadmin.layout import *


class UserSettingsAdmin(object):
    model_icon = 'fa fa-cog'
    hidden_menu = True
xadmin.site.register(UserSettings, UserSettingsAdmin)

########NEW FILE########
__FILENAME__ = filters
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.template.loader import get_template
from django.template.context import Context
from django.utils.safestring import mark_safe
from django.utils.html import escape,format_html
from django.utils.text import Truncator
from django.core.cache import cache, get_cache

from xadmin.views.list import EMPTY_CHANGELIST_VALUE
import datetime

FILTER_PREFIX = '_p_'
SEARCH_VAR = '_q_'

from util import (get_model_from_relation,
    reverse_field_path, get_limit_choices_to_from_path, prepare_lookup_value)


class BaseFilter(object):
    title = None
    template = 'xadmin/filters/list.html'

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        pass

    def __init__(self, request, params, model, admin_view):
        self.used_params = {}
        self.request = request
        self.params = params
        self.model = model
        self.admin_view = admin_view

        if self.title is None:
            raise ImproperlyConfigured(
                "The filter '%s' does not specify "
                "a 'title'." % self.__class__.__name__)

    def query_string(self, new_params=None, remove=None):
        return self.admin_view.get_query_string(new_params, remove)

    def form_params(self):
        return self.admin_view.get_form_params(
            remove=map(lambda k: FILTER_PREFIX + k, self.used_params.keys()))

    def has_output(self):
        """
        Returns True if some choices would be output for this filter.
        """
        raise NotImplementedError

    @property
    def is_used(self):
        return len(self.used_params) > 0

    def do_filte(self, queryset):
        """
        Returns the filtered queryset.
        """
        raise NotImplementedError

    def get_context(self):
        return {'title': self.title, 'spec': self, 'form_params': self.form_params()}

    def __str__(self):
        tpl = get_template(self.template)
        return mark_safe(tpl.render(Context(self.get_context())))


class FieldFilterManager(object):
    _field_list_filters = []
    _take_priority_index = 0

    def register(self, list_filter_class, take_priority=False):
        if take_priority:
            # This is to allow overriding the default filters for certain types
            # of fields with some custom filters. The first found in the list
            # is used in priority.
            self._field_list_filters.insert(
                self._take_priority_index, list_filter_class)
            self._take_priority_index += 1
        else:
            self._field_list_filters.append(list_filter_class)
        return list_filter_class

    def create(self, field, request, params, model, admin_view, field_path):
        for list_filter_class in self._field_list_filters:
            if not list_filter_class.test(field, request, params, model, admin_view, field_path):
                continue
            return list_filter_class(field, request, params,
                                     model, admin_view, field_path=field_path)

manager = FieldFilterManager()


class FieldFilter(BaseFilter):

    lookup_formats = {}

    def __init__(self, field, request, params, model, admin_view, field_path):
        self.field = field
        self.field_path = field_path
        self.title = getattr(field, 'verbose_name', field_path)
        self.context_params = {}

        super(FieldFilter, self).__init__(request, params, model, admin_view)

        for name, format in self.lookup_formats.items():
            p = format % field_path
            self.context_params["%s_name" % name] = FILTER_PREFIX + p
            if p in params:
                value = prepare_lookup_value(p, params.pop(p))
                self.used_params[p] = value
                self.context_params["%s_val" % name] = value
            else:
                self.context_params["%s_val" % name] = ''

        map(lambda kv: setattr(
            self, 'lookup_' + kv[0], kv[1]), self.context_params.items())

    def get_context(self):
        context = super(FieldFilter, self).get_context()
        context.update(self.context_params)
        context['remove_url'] = self.query_string(
            {}, map(lambda k: FILTER_PREFIX + k, self.used_params.keys()))
        return context

    def has_output(self):
        return True

    def do_filte(self, queryset):
        return queryset.filter(**self.used_params)


class ListFieldFilter(FieldFilter):
    template = 'xadmin/filters/list.html'

    def get_context(self):
        context = super(ListFieldFilter, self).get_context()
        context['choices'] = list(self.choices())
        return context


@manager.register
class BooleanFieldListFilter(ListFieldFilter):
    lookup_formats = {'exact': '%s__exact', 'isnull': '%s__isnull'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return isinstance(field, (models.BooleanField, models.NullBooleanField))

    def choices(self):
        for lookup, title in (
                ('', _('All')),
                ('1', _('Yes')),
                ('0', _('No'))):
            yield {
                'selected': self.lookup_exact_val == lookup and not self.lookup_isnull_val,
                'query_string': self.query_string({
                self.lookup_exact_name: lookup,
                }, [self.lookup_isnull_name]),
                'display': title,
            }
        if isinstance(self.field, models.NullBooleanField):
            yield {
                'selected': self.lookup_isnull_val == 'True',
                'query_string': self.query_string({
                self.lookup_isnull_name: 'True',
                }, [self.lookup_exact_name]),
                'display': _('Unknown'),
            }


@manager.register
class ChoicesFieldListFilter(ListFieldFilter):
    lookup_formats = {'exact': '%s__exact'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return bool(field.choices)

    def choices(self):
        yield {
            'selected': self.lookup_exact_val is '',
            'query_string': self.query_string({}, [self.lookup_exact_name]),
            'display': _('All')
        }
        for lookup, title in self.field.flatchoices:
            yield {
                'selected': smart_unicode(lookup) == self.lookup_exact_val,
                'query_string': self.query_string({self.lookup_exact_name: lookup}),
                'display': title,
            }


@manager.register
class TextFieldListFilter(FieldFilter):
    template = 'xadmin/filters/char.html'
    lookup_formats = {'in': '%s__in','search': '%s__contains'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return (isinstance(field, models.CharField) and field.max_length > 20) or isinstance(field, models.TextField)


@manager.register
class NumberFieldListFilter(FieldFilter):
    template = 'xadmin/filters/number.html'
    lookup_formats = {'equal': '%s__exact', 'lt': '%s__lt', 'gt': '%s__gt',
                      'ne': '%s__ne', 'lte': '%s__lte', 'gte': '%s__gte',
                      }

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return isinstance(field, (models.DecimalField, models.FloatField, models.IntegerField))

    def do_filte(self, queryset):
        params = self.used_params.copy()
        ne_key = '%s__ne' % self.field_path
        if ne_key in params:
            queryset = queryset.exclude(
                **{self.field_path: params.pop(ne_key)})
        return queryset.filter(**params)


@manager.register
class DateFieldListFilter(ListFieldFilter):
    template = 'xadmin/filters/date.html'
    lookup_formats = {'since': '%s__gte', 'until': '%s__lt',
                      'year': '%s__year', 'month': '%s__month', 'day': '%s__day',
                      'isnull': '%s__isnull'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return isinstance(field, models.DateField)

    def __init__(self, field, request, params, model, admin_view, field_path):
        self.field_generic = '%s__' % field_path
        self.date_params = dict([(FILTER_PREFIX + k, v) for k, v in params.items()
                                 if k.startswith(self.field_generic)])

        super(DateFieldListFilter, self).__init__(
            field, request, params, model, admin_view, field_path)

        now = timezone.now()
        # When time zone support is enabled, convert "now" to the user's time
        # zone so Django's definition of "Today" matches what the user expects.
        if now.tzinfo is not None:
            current_tz = timezone.get_current_timezone()
            now = now.astimezone(current_tz)
            if hasattr(current_tz, 'normalize'):
                # available for pytz time zones
                now = current_tz.normalize(now)

        if isinstance(field, models.DateTimeField):
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:       # field is a models.DateField
            today = now.date()
        tomorrow = today + datetime.timedelta(days=1)

        self.links = (
            (_('Any date'), {}),
            (_('Has date'), {
                self.lookup_isnull_name: False
            }),
            (_('Has no date'), {
                self.lookup_isnull_name: 'True'
            }),
            (_('Today'), {
                self.lookup_since_name: str(today),
                self.lookup_until_name: str(tomorrow),
            }),
            (_('Past 7 days'), {
                self.lookup_since_name: str(today - datetime.timedelta(days=7)),
                self.lookup_until_name: str(tomorrow),
            }),
            (_('This month'), {
                self.lookup_since_name: str(today.replace(day=1)),
                self.lookup_until_name: str(tomorrow),
            }),
            (_('This year'), {
                self.lookup_since_name: str(today.replace(month=1, day=1)),
                self.lookup_until_name: str(tomorrow),
            }),
        )

    def get_context(self):
        context = super(DateFieldListFilter, self).get_context()
        context['choice_selected'] = bool(self.lookup_year_val) or bool(self.lookup_month_val) \
            or bool(self.lookup_day_val)
        return context

    def choices(self):
        for title, param_dict in self.links:
            yield {
                'selected': self.date_params == param_dict,
                'query_string': self.query_string(
                param_dict, [FILTER_PREFIX + self.field_generic]),
                'display': title,
            }


@manager.register
class RelatedFieldSearchFilter(FieldFilter):
    template = 'xadmin/filters/fk_search.html'

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        if not (hasattr(field, 'rel') and bool(field.rel) or isinstance(field, models.related.RelatedObject)):
            return False
        related_modeladmin = admin_view.admin_site._registry.get(
            get_model_from_relation(field))
        return related_modeladmin and getattr(related_modeladmin, 'relfield_style', None) == 'fk-ajax'

    def __init__(self, field, request, params, model, model_admin, field_path):
        other_model = get_model_from_relation(field)
        if hasattr(field, 'rel'):
            rel_name = field.rel.get_related_field().name
        else:
            rel_name = other_model._meta.pk.name

        self.lookup_formats = {'in': '%%s__%s__in' % rel_name,'exact': '%%s__%s__exact' % rel_name}
        super(RelatedFieldSearchFilter, self).__init__(
            field, request, params, model, model_admin, field_path)

        if hasattr(field, 'verbose_name'):
            self.lookup_title = field.verbose_name
        else:
            self.lookup_title = other_model._meta.verbose_name
        self.title = self.lookup_title
        self.search_url = model_admin.get_admin_url('%s_%s_changelist' % (
            other_model._meta.app_label, other_model._meta.module_name))
        self.label = self.label_for_value(other_model, rel_name, self.lookup_exact_val) if self.lookup_exact_val else ""
        self.choices = '?'
        if field.rel.limit_choices_to:
            for i in list(field.rel.limit_choices_to):
                self.choices += "&_p_%s=%s" % (i, field.rel.limit_choices_to[i])
            self.choices = format_html(self.choices)

    def label_for_value(self, other_model, rel_name, value):
        try:
            obj = other_model._default_manager.get(**{rel_name: value})
            return '%s' % escape(Truncator(obj).words(14, truncate='...'))
        except (ValueError, other_model.DoesNotExist):
            return ""

    def get_context(self):
        context = super(RelatedFieldSearchFilter, self).get_context()
        context['search_url'] = self.search_url
        context['label'] = self.label
        context['choices'] = self.choices
        return context


@manager.register
class RelatedFieldListFilter(ListFieldFilter):

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return (hasattr(field, 'rel') and bool(field.rel) or isinstance(field, models.related.RelatedObject))

    def __init__(self, field, request, params, model, model_admin, field_path):
        other_model = get_model_from_relation(field)
        if hasattr(field, 'rel'):
            rel_name = field.rel.get_related_field().name
        else:
            rel_name = other_model._meta.pk.name

        self.lookup_formats = {'in': '%%s__%s__in' % rel_name,'exact': '%%s__%s__exact' %
                               rel_name, 'isnull': '%s__isnull'}
        self.lookup_choices = field.get_choices(include_blank=False)
        super(RelatedFieldListFilter, self).__init__(
            field, request, params, model, model_admin, field_path)

        if hasattr(field, 'verbose_name'):
            self.lookup_title = field.verbose_name
        else:
            self.lookup_title = other_model._meta.verbose_name
        self.title = self.lookup_title

    def has_output(self):
        if (isinstance(self.field, models.related.RelatedObject)
                and self.field.field.null or hasattr(self.field, 'rel')
                and self.field.null):
            extra = 1
        else:
            extra = 0
        return len(self.lookup_choices) + extra > 1

    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]

    def choices(self):
        yield {
            'selected': self.lookup_exact_val == '' and not self.lookup_isnull_val,
            'query_string': self.query_string({},
                                              [self.lookup_exact_name, self.lookup_isnull_name]),
            'display': _('All'),
        }
        for pk_val, val in self.lookup_choices:
            yield {
                'selected': self.lookup_exact_val == smart_unicode(pk_val),
                'query_string': self.query_string({
                    self.lookup_exact_name: pk_val,
                }, [self.lookup_isnull_name]),
                'display': val,
            }
        if (isinstance(self.field, models.related.RelatedObject)
                and self.field.field.null or hasattr(self.field, 'rel')
                and self.field.null):
            yield {
                'selected': bool(self.lookup_isnull_val),
                'query_string': self.query_string({
                    self.lookup_isnull_name: 'True',
                }, [self.lookup_exact_name]),
                'display': EMPTY_CHANGELIST_VALUE,
            }

@manager.register
class MultiSelectFieldListFilter(ListFieldFilter):
    """ Delegates the filter to the default filter and ors the results of each
     
    Lists the distinct values of each field as a checkbox
    Uses the default spec for each 
     
    """
    template = 'xadmin/filters/checklist.html'
    lookup_formats = {'in': '%s__in'}
    cache_config = {'enabled':False,'key':'quickfilter_%s','timeout':3600,'cache':'default'}
 
    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return True
 
    def get_cached_choices(self):
        if not self.cache_config['enabled']:
            return None
        c = get_cache(self.cache_config['cache'])
        return c.get(self.cache_config['key']%self.field_path)
    
    def set_cached_choices(self,choices):
        if not self.cache_config['enabled']:
            return
        c = get_cache(self.cache_config['cache'])
        return c.set(self.cache_config['key']%self.field_path,choices)
    
    def __init__(self, field, request, params, model, model_admin, field_path,field_order_by=None,field_limit=None,sort_key=None,cache_config=None):
        super(MultiSelectFieldListFilter,self).__init__(field, request, params, model, model_admin, field_path)
        
        # Check for it in the cachce
        if cache_config is not None and type(cache_config)==dict:
            self.cache_config.update(cache_config)
        
        if self.cache_config['enabled']:
            self.field_path = field_path
            choices = self.get_cached_choices()
            if choices:
                self.lookup_choices = choices
                return
            
        # Else rebuild it
        queryset = self.admin_view.queryset().exclude(**{"%s__isnull"%field_path:True}).values_list(field_path, flat=True).distinct() 
        #queryset = self.admin_view.queryset().distinct(field_path).exclude(**{"%s__isnull"%field_path:True})
        
        if field_order_by is not None:
            # Do a subquery to order the distinct set
            queryset = self.admin_view.queryset().filter(id__in=queryset).order_by(field_order_by)
            
        if field_limit is not None and type(field_limit)==int and queryset.count()>field_limit:
            queryset = queryset[:field_limit]
        
        self.lookup_choices = [str(it) for it in queryset.values_list(field_path,flat=True) if str(it).strip()!=""]
        if sort_key is not None:
            self.lookup_choices = sorted(self.lookup_choices,key=sort_key)
        
        if self.cache_config['enabled']:
            self.set_cached_choices(self.lookup_choices) 

    def choices(self):
        self.lookup_in_val = (type(self.lookup_in_val) in (tuple,list)) and self.lookup_in_val or list(self.lookup_in_val)
        yield {
            'selected': len(self.lookup_in_val) == 0,
            'query_string': self.query_string({},[self.lookup_in_name]),
            'display': _('All'),
        }
        for val in self.lookup_choices:
            yield {
                'selected': smart_unicode(val) in self.lookup_in_val,
                'query_string': self.query_string({self.lookup_in_name: ",".join([val]+self.lookup_in_val),}),
                'remove_query_string': self.query_string({self.lookup_in_name: ",".join([v for v in self.lookup_in_val if v != val]),}),
                'display': val,
            }

@manager.register
class AllValuesFieldListFilter(ListFieldFilter):
    lookup_formats = {'exact': '%s__exact', 'isnull': '%s__isnull'}

    @classmethod
    def test(cls, field, request, params, model, admin_view, field_path):
        return True

    def __init__(self, field, request, params, model, admin_view, field_path):
        parent_model, reverse_path = reverse_field_path(model, field_path)
        queryset = parent_model._default_manager.all()
        # optional feature: limit choices base on existing relationships
        # queryset = queryset.complex_filter(
        #    {'%s__isnull' % reverse_path: False})
        limit_choices_to = get_limit_choices_to_from_path(model, field_path)
        queryset = queryset.filter(limit_choices_to)

        self.lookup_choices = (queryset
                               .distinct()
                               .order_by(field.name)
                               .values_list(field.name, flat=True))
        super(AllValuesFieldListFilter, self).__init__(
            field, request, params, model, admin_view, field_path)

    def choices(self):
        yield {
            'selected': (self.lookup_exact_val is '' and self.lookup_isnull_val is ''),
            'query_string': self.query_string({}, [self.lookup_exact_name, self.lookup_isnull_name]),
            'display': _('All'),
        }
        include_none = False
        for val in self.lookup_choices:
            if val is None:
                include_none = True
                continue
            val = smart_unicode(val)
            yield {
                'selected': self.lookup_exact_val == val,
                'query_string': self.query_string({self.lookup_exact_name: val},
                                                  [self.lookup_isnull_name]),
                'display': val,
            }
        if include_none:
            yield {
                'selected': bool(self.lookup_isnull_val),
                'query_string': self.query_string({self.lookup_isnull_name: 'True'},
                                                  [self.lookup_exact_name]),
                'display': EMPTY_CHANGELIST_VALUE,
            }
########NEW FILE########
__FILENAME__ = forms
from django import forms

from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm

from django.utils.translation import ugettext_lazy, ugettext as _

from xadmin.util import User

ERROR_MESSAGE = ugettext_lazy("Please enter the correct username and password "
                              "for a staff account. Note that both fields are case-sensitive.")


class AdminAuthenticationForm(AuthenticationForm):
    """
    A custom authentication form used in the admin app.

    """
    this_is_the_login_form = forms.BooleanField(
        widget=forms.HiddenInput, initial=1,
        error_messages={'required': ugettext_lazy("Please log in again, because your session has expired.")})

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        message = ERROR_MESSAGE

        if username and password:
            self.user_cache = authenticate(
                username=username, password=password)
            if self.user_cache is None:
                if u'@' in username:
                    # Mistakenly entered e-mail address instead of username? Look it up.
                    try:
                        user = User.objects.get(email=username)
                    except (User.DoesNotExist, User.MultipleObjectsReturned):
                        # Nothing to do here, moving along.
                        pass
                    else:
                        if user.check_password(password):
                            message = _("Your e-mail address is not your username."
                                        " Try '%s' instead.") % user.username
                raise forms.ValidationError(message)
            elif not self.user_cache.is_active or not self.user_cache.is_staff:
                raise forms.ValidationError(message)
        self.check_for_test_cookie()
        return self.cleaned_data

########NEW FILE########
__FILENAME__ = layout
from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import *
from crispy_forms.utils import render_field, flatatt

from crispy_forms import layout
from crispy_forms import bootstrap

import math


class Fieldset(layout.Fieldset):
    template = "xadmin/layout/fieldset.html"

    def __init__(self, legend, *fields, **kwargs):
        self.description = kwargs.pop('description', None)
        self.collapsed = kwargs.pop('collapsed', None)
        super(Fieldset, self).__init__(legend, *fields, **kwargs)


class Row(layout.Div):

    def __init__(self, *fields, **kwargs):
        css_class = 'form-inline form-group'
        new_fields = [self.convert_field(f, len(fields)) for f in fields]
        super(Row, self).__init__(css_class=css_class, *new_fields, **kwargs)

    def convert_field(self, f, counts):
        col_class = "col-sm-%d" % int(math.ceil(12 / counts))
        if not (isinstance(f, Field) or issubclass(f.__class__, Field)):
            f = layout.Field(f)
        if f.wrapper_class:
            f.wrapper_class += " %s" % col_class
        else:
            f.wrapper_class = col_class
        return f


class Col(layout.Column):

    def __init__(self, id, *fields, **kwargs):
        css_class = ['column', 'form-column', id, 'col col-sm-%d' %
                     kwargs.get('span', 6)]
        if kwargs.get('horizontal'):
            css_class.append('form-horizontal')
        super(Col, self).__init__(css_class=' '.join(css_class), *
                                  fields, **kwargs)


class Main(layout.Column):
    css_class = "column form-column main col col-sm-9 form-horizontal"


class Side(layout.Column):
    css_class = "column form-column sidebar col col-sm-3"


class Container(layout.Div):
    css_class = "form-container row clearfix"


# Override bootstrap3
class InputGroup(layout.Field):

    template = "xadmin/layout/input_group.html"

    def __init__(self, field, *args, **kwargs):
        self.field = field
        self.inputs = list(args)
        if '@@' not in args:
            self.inputs.append('@@')

        super(InputGroup, self).__init__(field, **kwargs)

    def render(self, form, form_style, context, template_pack='bootstrap'):
        classes = form.fields[self.field].widget.attrs.get('class', '')
        context.update(
            {'inputs': self.inputs, 'classes': classes.replace('form-control', '')})
        if hasattr(self, 'wrapper_class'):
            context['wrapper_class'] = self.wrapper_class
        return render_field(
            self.field, form, form_style, context, template=self.template,
            attrs=self.attrs, template_pack=template_pack)


class PrependedText(InputGroup):

    def __init__(self, field, text, **kwargs):
        super(PrependedText, self).__init__(field, text, '@@', **kwargs)


class AppendedText(InputGroup):

    def __init__(self, field, text, **kwargs):
        super(AppendedText, self).__init__(field, '@@', text, **kwargs)


class PrependedAppendedText(InputGroup):

    def __init__(self, field, prepended_text=None, appended_text=None, *args, **kwargs):
        super(PrependedAppendedText, self).__init__(
            field, prepended_text, '@@', appended_text, **kwargs)

########NEW FILE########
__FILENAME__ = models
import json
import django
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import ModelBase
from django.utils.encoding import smart_unicode

from django.db.models.signals import post_syncdb
from django.contrib.auth.models import Permission

import datetime
import decimal

if django.VERSION[1] > 4:
    AUTH_USER_MODEL = django.contrib.auth.get_user_model()
else:
    AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def add_view_permissions(sender, **kwargs):
    """
    This syncdb hooks takes care of adding a view permission too all our
    content types.
    """
    # for each of our content types
    for content_type in ContentType.objects.all():
        # build our permission slug
        codename = "view_%s" % content_type.model

        # if it doesn't exist..
        if not Permission.objects.filter(content_type=content_type, codename=codename):
            # add it
            Permission.objects.create(content_type=content_type,
                                      codename=codename,
                                      name="Can view %s" % content_type.name)
            #print "Added view permission for %s" % content_type.name

# check for all our view permissions after a syncdb
post_syncdb.connect(add_view_permissions)


class Bookmark(models.Model):
    title = models.CharField(_(u'Title'), max_length=128)
    user = models.ForeignKey(AUTH_USER_MODEL, verbose_name=_(u"user"), blank=True, null=True)
    url_name = models.CharField(_(u'Url Name'), max_length=64)
    content_type = models.ForeignKey(ContentType)
    query = models.CharField(_(u'Query String'), max_length=1000, blank=True)
    is_share = models.BooleanField(_(u'Is Shared'), default=False)

    @property
    def url(self):
        base_url = reverse(self.url_name)
        if self.query:
            base_url = base_url + '?' + self.query
        return base_url

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name = _(u'Bookmark')
        verbose_name_plural = _('Bookmarks')


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.date):
            return o.strftime('%Y-%m-%d')
        elif isinstance(o, datetime.datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, ModelBase):
            return '%s.%s' % (o._meta.app_label, o._meta.module_name)
        else:
            try:
                return super(JSONEncoder, self).default(o)
            except Exception:
                return smart_unicode(o)


class UserSettings(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL, verbose_name=_(u"user"))
    key = models.CharField(_('Settings Key'), max_length=256)
    value = models.TextField(_('Settings Content'))

    def json_value(self):
        return json.loads(self.value)

    def set_json(self, obj):
        self.value = json.dumps(obj, cls=JSONEncoder, ensure_ascii=False)

    def __unicode__(self):
        return "%s %s" % (self.user, self.key)

    class Meta:
        verbose_name = _(u'User Setting')
        verbose_name_plural = _('User Settings')


class UserWidget(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL, verbose_name=_(u"user"))
    page_id = models.CharField(_(u"Page"), max_length=256)
    widget_type = models.CharField(_(u"Widget Type"), max_length=50)
    value = models.TextField(_(u"Widget Params"))

    def get_value(self):
        value = json.loads(self.value)
        value['id'] = self.id
        value['type'] = self.widget_type
        return value

    def set_value(self, obj):
        self.value = json.dumps(obj, cls=JSONEncoder, ensure_ascii=False)

    def save(self, *args, **kwargs):
        created = self.pk is None
        super(UserWidget, self).save(*args, **kwargs)
        if created:
            try:
                portal_pos = UserSettings.objects.get(
                    user=self.user, key="dashboard:%s:pos" % self.page_id)
                portal_pos.value = "%s,%s" % (self.pk, portal_pos.value) if portal_pos.value else self.pk
                portal_pos.save()
            except Exception:
                pass

    def __unicode__(self):
        return "%s %s widget" % (self.user, self.widget_type)

    class Meta:
        verbose_name = _(u'User Widget')
        verbose_name_plural = _('User Widgets')

########NEW FILE########
__FILENAME__ = actions
from django import forms
from django.core.exceptions import PermissionDenied
from django.db import router
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.template.response import TemplateResponse
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _, ungettext
from django.utils.text import capfirst
from xadmin.sites import site
from xadmin.util import model_format_dict, get_deleted_objects, model_ngettext
from xadmin.views import BaseAdminPlugin, ListAdminView
from xadmin.views.base import filter_hook, ModelAdminView


ACTION_CHECKBOX_NAME = '_selected_action'
checkbox = forms.CheckboxInput({'class': 'action-select'}, lambda value: False)


def action_checkbox(obj):
    return checkbox.render(ACTION_CHECKBOX_NAME, force_unicode(obj.pk))
action_checkbox.short_description = mark_safe(
    '<input type="checkbox" id="action-toggle" />')
action_checkbox.allow_tags = True
action_checkbox.allow_export = False
action_checkbox.is_column = False


class BaseActionView(ModelAdminView):
    action_name = None
    description = None
    icon = 'fa fa-tasks'

    model_perm = 'change'

    @classmethod
    def has_perm(cls, list_view):
        return list_view.get_model_perms()[cls.model_perm]

    def init_action(self, list_view):
        self.list_view = list_view
        self.admin_site = list_view.admin_site

    @filter_hook
    def do_action(self, queryset):
        pass


class DeleteSelectedAction(BaseActionView):

    action_name = "delete_selected"
    description = _(u'Delete selected %(verbose_name_plural)s')

    delete_confirmation_template = None
    delete_selected_confirmation_template = None

    model_perm = 'delete'
    icon = 'fa fa-times'

    @filter_hook
    def delete_models(self, queryset):
        n = queryset.count()
        if n:
            queryset.delete()
            self.message_user(_("Successfully deleted %(count)d %(items)s.") % {
                "count": n, "items": model_ngettext(self.opts, n)
            }, 'success')

    @filter_hook
    def do_action(self, queryset):
        # Check that the user has delete permission for the actual model
        if not self.has_delete_permission():
            raise PermissionDenied

        using = router.db_for_write(self.model)

        # Populate deletable_objects, a data structure of all related objects that
        # will also be deleted.
        deletable_objects, perms_needed, protected = get_deleted_objects(
            queryset, self.opts, self.user, self.admin_site, using)

        # The user has already confirmed the deletion.
        # Do the deletion and return a None to display the change list view again.
        if self.request.POST.get('post'):
            if perms_needed:
                raise PermissionDenied
            self.delete_models(queryset)
            # Return None to display the change list page again.
            return None

        if len(queryset) == 1:
            objects_name = force_unicode(self.opts.verbose_name)
        else:
            objects_name = force_unicode(self.opts.verbose_name_plural)

        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": objects_name}
        else:
            title = _("Are you sure?")

        context = self.get_context()
        context.update({
            "title": title,
            "objects_name": objects_name,
            "deletable_objects": [deletable_objects],
            'queryset': queryset,
            "perms_lacking": perms_needed,
            "protected": protected,
            "opts": self.opts,
            "app_label": self.app_label,
            'action_checkbox_name': ACTION_CHECKBOX_NAME,
        })

        # Display the confirmation page
        return TemplateResponse(self.request, self.delete_selected_confirmation_template or
                                self.get_template_list('views/model_delete_selected_confirm.html'), context, current_app=self.admin_site.name)


class ActionPlugin(BaseAdminPlugin):

    # Actions
    actions = []
    actions_selection_counter = True
    global_actions = [DeleteSelectedAction]

    def init_request(self, *args, **kwargs):
        self.actions = self.get_actions()
        return bool(self.actions)

    def get_list_display(self, list_display):
        if self.actions:
            list_display.insert(0, 'action_checkbox')
            self.admin_view.action_checkbox = action_checkbox
        return list_display

    def get_list_display_links(self, list_display_links):
        if self.actions:
            if len(list_display_links) == 1 and list_display_links[0] == 'action_checkbox':
                return list(self.admin_view.list_display[1:2])
        return list_display_links

    def get_context(self, context):
        if self.actions and self.admin_view.result_count:
            av = self.admin_view
            selection_note_all = ungettext('%(total_count)s selected',
                                           'All %(total_count)s selected', av.result_count)

            new_context = {
                'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(av.result_list)},
                'selection_note_all': selection_note_all % {'total_count': av.result_count},
                'action_choices': self.get_action_choices(),
                'actions_selection_counter': self.actions_selection_counter,
            }
            context.update(new_context)
        return context

    def post_response(self, response, *args, **kwargs):
        request = self.admin_view.request
        av = self.admin_view

        # Actions with no confirmation
        if self.actions and 'action' in request.POST:
            action = request.POST['action']

            if action not in self.actions:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                av.message_user(msg)
            else:
                ac, name, description, icon = self.actions[action]
                select_across = request.POST.get('select_across', False) == '1'
                selected = request.POST.getlist(ACTION_CHECKBOX_NAME)

                if not selected and not select_across:
                    # Reminder that something needs to be selected or nothing will happen
                    msg = _("Items must be selected in order to perform "
                            "actions on them. No items have been changed.")
                    av.message_user(msg)
                else:
                    queryset = av.list_queryset._clone()
                    if not select_across:
                        # Perform the action only on the selected objects
                        queryset = av.list_queryset.filter(pk__in=selected)
                    response = self.response_action(ac, queryset)
                    # Actions may return an HttpResponse, which will be used as the
                    # response from the POST. If not, we'll be a good little HTTP
                    # citizen and redirect back to the changelist page.
                    if isinstance(response, HttpResponse):
                        return response
                    else:
                        return HttpResponseRedirect(request.get_full_path())
        return response

    def response_action(self, ac, queryset):
        if isinstance(ac, type) and issubclass(ac, BaseActionView):
            action_view = self.get_model_view(ac, self.admin_view.model)
            action_view.init_action(self.admin_view)
            return action_view.do_action(queryset)
        else:
            return ac(self.admin_view, self.request, queryset)

    def get_actions(self):
        if self.actions is None:
            return SortedDict()

        actions = [self.get_action(action) for action in self.global_actions]

        for klass in self.admin_view.__class__.mro()[::-1]:
            class_actions = getattr(klass, 'actions', [])
            if not class_actions:
                continue
            actions.extend(
                [self.get_action(action) for action in class_actions])

        # get_action might have returned None, so filter any of those out.
        actions = filter(None, actions)

        # Convert the actions into a SortedDict keyed by name.
        actions = SortedDict([
            (name, (ac, name, desc, icon))
            for ac, name, desc, icon in actions
        ])

        return actions

    def get_action_choices(self):
        """
        Return a list of choices for use in a form object.  Each choice is a
        tuple (name, description).
        """
        choices = []
        for ac, name, description, icon in self.actions.itervalues():
            choice = (name, description % model_format_dict(self.opts), icon)
            choices.append(choice)
        return choices

    def get_action(self, action):
        if isinstance(action, type) and issubclass(action, BaseActionView):
            if not action.has_perm(self.admin_view):
                return None
            return action, getattr(action, 'action_name'), getattr(action, 'description'), getattr(action, 'icon')

        elif callable(action):
            func = action
            action = action.__name__

        elif hasattr(self.admin_view.__class__, action):
            func = getattr(self.admin_view.__class__, action)

        else:
            return None

        if hasattr(func, 'short_description'):
            description = func.short_description
        else:
            description = capfirst(action.replace('_', ' '))

        return func, action, description, getattr(func, 'icon', 'tasks')

    # View Methods
    def result_header(self, item, field_name, row):
        if item.attr and field_name == 'action_checkbox':
            item.classes.append("action-checkbox-column")
        return item

    def result_item(self, item, obj, field_name, row):
        if item.field is None and field_name == u'action_checkbox':
            item.classes.append("action-checkbox")
        return item

    # Media
    def get_media(self, media):
        if self.actions and self.admin_view.result_count:
            media = media + self.vendor('xadmin.plugin.actions.js', 'xadmin.plugins.css')
        return media

    # Block Views
    def block_results_bottom(self, context, nodes):
        if self.actions and self.admin_view.result_count:
            nodes.append(loader.render_to_string('xadmin/blocks/model_list.results_bottom.actions.html', context_instance=context))


site.register_plugin(ActionPlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = aggregation
from django.db.models import FieldDoesNotExist, Avg, Max, Min, Count, Sum
from django.utils.translation import ugettext as _

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView

from xadmin.views.list import ResultRow, ResultItem
from xadmin.util import display_for_field

AGGREGATE_METHODS = {
    'min': Min, 'max': Max, 'avg': Avg, 'sum': Sum, 'count': Count
}
AGGREGATE_TITLE = {
    'min': _('Min'), 'max': _('Max'), 'avg': _('Avg'), 'sum': _('Sum'), 'count': _('Count')
}


class AggregationPlugin(BaseAdminPlugin):

    aggregate_fields = {}

    def init_request(self, *args, **kwargs):
        return bool(self.aggregate_fields)

    def _get_field_aggregate(self, field_name, obj, row):
        item = ResultItem(field_name, row)
        item.classes = ['aggregate', ]
        if field_name not in self.aggregate_fields:
            item.text = ""
        else:
            try:
                f = self.opts.get_field(field_name)
                agg_method = self.aggregate_fields[field_name]
                key = '%s__%s' % (field_name, agg_method)
                if key not in obj:
                    item.text = ""
                else:
                    item.text = display_for_field(obj[key], f)
                    item.wraps.append('%%s<span class="aggregate_title label label-info">%s</span>' % AGGREGATE_TITLE[agg_method])
                    item.classes.append(agg_method)
            except FieldDoesNotExist:
                item.text = ""

        return item

    def _get_aggregate_row(self):
        queryset = self.admin_view.list_queryset._clone()
        obj = queryset.aggregate(*[AGGREGATE_METHODS[method](field_name) for field_name, method in
                                   self.aggregate_fields.items() if method in AGGREGATE_METHODS])

        row = ResultRow()
        row['is_display_first'] = False
        row.cells = [self._get_field_aggregate(field_name, obj, row) for field_name in self.admin_view.list_display]
        row.css_class = 'info aggregate'
        return row

    def results(self, rows):
        if rows:
            rows.append(self._get_aggregate_row())
        return rows

    # Media
    def get_media(self, media):
        media.add_css({'screen': [self.static(
            'xadmin/css/xadmin.plugin.aggregation.css'), ]})
        return media


site.register_plugin(AggregationPlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = ajax
from django import forms
from django.utils.datastructures import SortedDict
from django.utils.html import escape
from django.utils.encoding import force_unicode
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView, ModelFormAdminView, DetailAdminView


NON_FIELD_ERRORS = '__all__'


class BaseAjaxPlugin(BaseAdminPlugin):

    def init_request(self, *args, **kwargs):
        return bool(self.request.is_ajax() or self.request.REQUEST.get('_ajax'))


class AjaxListPlugin(BaseAjaxPlugin):
    
    def get_list_display(self,list_display):
        list_fields = [field for field in self.request.GET.get('_fields',"").split(",") 
                                if field.strip() != ""]
        if list_fields:
            return list_fields
        return list_display

    def get_result_list(self, response):
        av = self.admin_view
        base_fields = self.get_list_display(av.base_list_display)
        headers = dict([(c.field_name, force_unicode(c.text)) for c in av.result_headers(
        ).cells if c.field_name in base_fields])

        objects = [dict([(o.field_name, escape(str(o.value))) for i, o in
                         enumerate(filter(lambda c:c.field_name in base_fields, r.cells))])
                   for r in av.results()]

        return self.render_response({'headers': headers, 'objects': objects, 'total_count': av.result_count, 'has_more': av.has_more})


class JsonErrorDict(forms.util.ErrorDict):

    def __init__(self, errors, form):
        super(JsonErrorDict, self).__init__(errors)
        self.form = form

    def as_json(self):
        if not self:
            return u''
        return [{'id': self.form[k].auto_id if k != NON_FIELD_ERRORS else NON_FIELD_ERRORS, 'name': k, 'errors': v} for k, v in self.items()]


class AjaxFormPlugin(BaseAjaxPlugin):

    def post_response(self, __):
        new_obj = self.admin_view.new_obj
        return self.render_response({
            'result': 'success',
            'obj_id': new_obj.pk,
            'obj_repr': str(new_obj),
            'change_url': self.admin_view.model_admin_url('change', new_obj.pk),
            'detail_url': self.admin_view.model_admin_url('detail', new_obj.pk)
        })

    def get_response(self, __):
        if self.request.method.lower() != 'post':
            return __()

        result = {}
        form = self.admin_view.form_obj
        if form.is_valid():
            result['result'] = 'success'
        else:
            result['result'] = 'error'
            result['errors'] = JsonErrorDict(form.errors, form).as_json()

        return self.render_response(result)


class AjaxDetailPlugin(BaseAjaxPlugin):

    def get_response(self, __):
        if self.request.GET.get('_format') == 'html':
            self.admin_view.detail_template = 'xadmin/views/quick_detail.html'
            return __()

        form = self.admin_view.form_obj
        layout = form.helper.layout

        results = []

        for p, f in layout.get_field_names():
            result = self.admin_view.get_field_result(f)
            results.append((result.label, result.val))

        return self.render_response(SortedDict(results))

site.register_plugin(AjaxListPlugin, ListAdminView)
site.register_plugin(AjaxFormPlugin, ModelFormAdminView)
site.register_plugin(AjaxDetailPlugin, DetailAdminView)

########NEW FILE########
__FILENAME__ = auth
# coding=utf-8
from django import forms
from django.contrib.auth.forms import (UserCreationForm, UserChangeForm,
                                       AdminPasswordChangeForm, PasswordChangeForm)
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.http import HttpResponseRedirect
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.views.decorators.debug import sensitive_post_parameters
from django.forms import ModelMultipleChoiceField
from xadmin.layout import Fieldset, Main, Side, Row, FormHelper
from xadmin.sites import site
from xadmin.util import unquote, User
from xadmin.views import BaseAdminPlugin, ModelFormAdminView, ModelAdminView, CommAdminView, csrf_protect_m


ACTION_NAME = {
    'add': _('Can add %s'),
    'change': _('Can change %s'),
    'edit': _('Can edit %s'),
    'delete': _('Can delete %s'),
    'view': _('Can view %s'),
}


def get_permission_name(p):
    action = p.codename.split('_')[0]
    if action in ACTION_NAME:
        return ACTION_NAME[action] % str(p.content_type)
    else:
        return p.name


class PermissionModelMultipleChoiceField(ModelMultipleChoiceField):

    def label_from_instance(self, p):
        return get_permission_name(p)


class GroupAdmin(object):
    search_fields = ('name',)
    ordering = ('name',)
    style_fields = {'permissions': 'm2m_transfer'}
    model_icon = 'fa fa-group'

    def get_field_attrs(self, db_field, **kwargs):
        attrs = super(GroupAdmin, self).get_field_attrs(db_field, **kwargs)
        if db_field.name == 'permissions':
            attrs['form_class'] = PermissionModelMultipleChoiceField
        return attrs


class UserAdmin(object):
    change_user_password_template = None
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    style_fields = {'user_permissions': 'm2m_transfer'}
    model_icon = 'fa fa-user'
    relfield_style = 'fk-ajax'

    def get_field_attrs(self, db_field, **kwargs):
        attrs = super(UserAdmin, self).get_field_attrs(db_field, **kwargs)
        if db_field.name == 'user_permissions':
            attrs['form_class'] = PermissionModelMultipleChoiceField
        return attrs

    def get_model_form(self, **kwargs):
        if self.org_obj is None:
            self.form = UserCreationForm
        else:
            self.form = UserChangeForm
        return super(UserAdmin, self).get_model_form(**kwargs)

    def get_form_layout(self):
        if self.org_obj:
            self.form_layout = (
                Main(
                    Fieldset('',
                             'username', 'password',
                             css_class='unsort no_title'
                             ),
                    Fieldset(_('Personal info'),
                             Row('first_name', 'last_name'),
                             'email'
                             ),
                    Fieldset(_('Permissions'),
                             'groups', 'user_permissions'
                             ),
                    Fieldset(_('Important dates'),
                             'last_login', 'date_joined'
                             ),
                ),
                Side(
                    Fieldset(_('Status'),
                             'is_active', 'is_staff', 'is_superuser',
                             ),
                )
            )
        return super(UserAdmin, self).get_form_layout()


class PermissionAdmin(object):

    def show_name(self, p):
        return get_permission_name(p)
    show_name.short_description = _('Permission Name')
    show_name.is_column = True

    model_icon = 'fa fa-lock'
    list_display = ('show_name', )

site.register(Group, GroupAdmin)
site.register(User, UserAdmin)
site.register(Permission, PermissionAdmin)


class UserFieldPlugin(BaseAdminPlugin):

    user_fields = []

    def get_field_attrs(self, __, db_field, **kwargs):
        if self.user_fields and db_field.name in self.user_fields:
            return {'widget': forms.HiddenInput}
        return __()

    def get_form_datas(self, datas):
        if self.user_fields and 'data' in datas:
            if hasattr(datas['data'],'_mutable') and not datas['data']._mutable:
                datas['data'] = datas['data'].copy()
            for f in self.user_fields:
                datas['data'][f] = self.user.id
        return datas

site.register_plugin(UserFieldPlugin, ModelFormAdminView)


class ModelPermissionPlugin(BaseAdminPlugin):

    user_can_access_owned_objects_only = False
    user_owned_objects_field = 'user'

    def queryset(self, qs):
        if self.user_can_access_owned_objects_only and \
                not self.user.is_superuser:
            filters = {self.user_owned_objects_field: self.user}
            qs = qs.filter(**filters)
        return qs


site.register_plugin(ModelPermissionPlugin, ModelAdminView)


class AccountMenuPlugin(BaseAdminPlugin):

    def block_top_account_menu(self, context, nodes):
        return '<li><a href="%s"><i class="fa fa-key"></i> %s</a></li>' % (self.get_admin_url('account_password'), _('Change Password'))

site.register_plugin(AccountMenuPlugin, CommAdminView)


class ChangePasswordView(ModelAdminView):
    model = User
    change_password_form = AdminPasswordChangeForm
    change_user_password_template = None

    @csrf_protect_m
    def get(self, request, object_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        self.obj = self.get_object(unquote(object_id))
        self.form = self.change_password_form(self.obj)

        return self.get_response()

    def get_media(self):
        media = super(ChangePasswordView, self).get_media()
        media = media + self.vendor('xadmin.form.css', 'xadmin.page.form.js') + self.form.media
        return media

    def get_context(self):
        context = super(ChangePasswordView, self).get_context()
        helper = FormHelper()
        helper.form_tag = False
        self.form.helper = helper
        context.update({
            'title': _('Change password: %s') % escape(unicode(self.obj)),
            'form': self.form,
            'has_delete_permission': False,
            'has_change_permission': True,
            'has_view_permission': True,
            'original': self.obj,
        })
        return context

    def get_response(self):
        return TemplateResponse(self.request, [
            self.change_user_password_template or
            'xadmin/auth/user/change_password.html'
        ], self.get_context(), current_app=self.admin_site.name)

    @method_decorator(sensitive_post_parameters())
    @csrf_protect_m
    def post(self, request, object_id):
        if not self.has_change_permission(request):
            raise PermissionDenied
        self.obj = self.get_object(unquote(object_id))
        self.form = self.change_password_form(self.obj, request.POST)

        if self.form.is_valid():
            self.form.save()
            self.message_user(_('Password changed successfully.'), 'success')
            return HttpResponseRedirect(self.model_admin_url('change', self.obj.pk))
        else:
            return self.get_response()


class ChangeAccountPasswordView(ChangePasswordView):
    change_password_form = PasswordChangeForm

    @csrf_protect_m
    def get(self, request):
        self.obj = self.user
        self.form = self.change_password_form(self.obj)

        return self.get_response()

    def get_context(self):
        context = super(ChangeAccountPasswordView, self).get_context()
        context.update({
            'title': _('Change password'),
            'account_view': True,
        })
        return context

    @method_decorator(sensitive_post_parameters())
    @csrf_protect_m
    def post(self, request):
        self.obj = self.user
        self.form = self.change_password_form(self.obj, request.POST)

        if self.form.is_valid():
            self.form.save()
            self.message_user(_('Password changed successfully.'), 'success')
            return HttpResponseRedirect(self.get_admin_url('index'))
        else:
            return self.get_response()

site.register_view(r'^auth/user/(.+)/update/password/$',
                   ChangePasswordView, name='user_change_password')
site.register_view(r'^account/password/$', ChangeAccountPasswordView,
                   name='account_password')

########NEW FILE########
__FILENAME__ = batch

import copy
from django import forms
from django.db import models
from django.core.exceptions import PermissionDenied
from django.forms.models import modelform_factory
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _, ugettext_lazy
from xadmin.layout import FormHelper, Layout, Fieldset, Container, Col
from xadmin.plugins.actions import BaseActionView, ACTION_CHECKBOX_NAME
from xadmin.util import model_ngettext, vendor
from xadmin.views.base import filter_hook
from xadmin.views.edit import ModelFormAdminView

BATCH_CHECKBOX_NAME = '_batch_change_fields'

class ChangeFieldWidgetWrapper(forms.Widget):

    def __init__(self, widget):
        self.is_hidden = widget.is_hidden
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.widget = widget

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.widget = copy.deepcopy(self.widget, memo)
        obj.attrs = self.widget.attrs
        memo[id(self)] = obj
        return obj

    @property
    def media(self):
        media = self.widget.media + vendor('xadmin.plugin.batch.js')
        return media

    def render(self, name, value, attrs=None):
        output = []
        is_required = self.widget.is_required
        output.append(u'<label class="btn btn-info btn-xs">'
            '<input type="checkbox" class="batch-field-checkbox" name="%s" value="%s"%s/> %s</label>' %
            (BATCH_CHECKBOX_NAME, name, (is_required and ' checked="checked"' or ''), _('Change this field')))
        output.extend([('<div class="control-wrap" style="margin-top: 10px;%s" id="id_%s_wrap_container">' %
            ((not is_required and 'display: none;' or ''), name)),
            self.widget.render(name, value, attrs), '</div>'])
        return mark_safe(u''.join(output))

    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        self.attrs = self.widget.build_attrs(extra_attrs=None, **kwargs)
        return self.attrs

    def value_from_datadict(self, data, files, name):
        return self.widget.value_from_datadict(data, files, name)

    def id_for_label(self, id_):
        return self.widget.id_for_label(id_)

class BatchChangeAction(BaseActionView):

    action_name = "change_selected"
    description = ugettext_lazy(
        u'Batch Change selected %(verbose_name_plural)s')

    batch_change_form_template = None

    model_perm = 'change'

    batch_fields = []

    def change_models(self, queryset, cleaned_data):
        n = queryset.count()

        data = {}
        for f in self.opts.fields:
            if not f.editable or isinstance(f, models.AutoField) \
                    or not f.name in cleaned_data:
                continue
            data[f] = cleaned_data[f.name]

        if n:
            for obj in queryset:
                for f, v in data.items():
                    f.save_form_data(obj, v)
                obj.save()
            self.message_user(_("Successfully change %(count)d %(items)s.") % {
                "count": n, "items": model_ngettext(self.opts, n)
            }, 'success')

    def get_change_form(self, is_post, fields):
        edit_view = self.get_model_view(ModelFormAdminView, self.model)

        def formfield_for_dbfield(db_field, **kwargs):
            formfield = edit_view.formfield_for_dbfield(db_field, required=is_post, **kwargs)
            formfield.widget = ChangeFieldWidgetWrapper(formfield.widget)
            return formfield

        defaults = {
            "form": edit_view.form,
            "fields": fields,
            "formfield_callback": formfield_for_dbfield,
        }
        return modelform_factory(self.model, **defaults)

    def do_action(self, queryset):
        if not self.has_change_permission():
            raise PermissionDenied

        change_fields = [f for f in self.request.POST.getlist(BATCH_CHECKBOX_NAME) if f in self.batch_fields]

        if change_fields and self.request.POST.get('post'):
            self.form_obj = self.get_change_form(True, change_fields)(
                data=self.request.POST, files=self.request.FILES)
            if self.form_obj.is_valid():
                self.change_models(queryset, self.form_obj.cleaned_data)
                return None
        else:
            self.form_obj = self.get_change_form(False, self.batch_fields)()

        helper = FormHelper()
        helper.form_tag = False
        helper.add_layout(Layout(Container(Col('full',
            Fieldset("", *self.form_obj.fields.keys(), css_class="unsort no_title"), horizontal=True, span=12)
        )))
        self.form_obj.helper = helper
        count = len(queryset)
        if count == 1:
            objects_name = force_unicode(self.opts.verbose_name)
        else:
            objects_name = force_unicode(self.opts.verbose_name_plural)

        context = self.get_context()
        context.update({
            "title": _("Batch change %s") % objects_name,
            'objects_name': objects_name,
            'form': self.form_obj,
            'queryset': queryset,
            'count': count,
            "opts": self.opts,
            "app_label": self.app_label,
            'action_checkbox_name': ACTION_CHECKBOX_NAME,
        })

        return TemplateResponse(self.request, self.batch_change_form_template or
                                self.get_template_list('views/batch_change_form.html'), context, current_app=self.admin_site.name)

    @filter_hook
    def get_media(self):
        media = super(BatchChangeAction, self).get_media()
        media = media + self.form_obj.media + self.vendor(
            'xadmin.page.form.js', 'xadmin.form.css')
        return media

########NEW FILE########
__FILENAME__ = bookmark

from django.template import loader
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.forms import ModelChoiceField
from django.http import QueryDict

from xadmin.sites import site
from xadmin.views import ModelAdminView, BaseAdminPlugin, ListAdminView
from xadmin.views.list import COL_LIST_VAR, ORDER_VAR
from xadmin.views.dashboard import widget_manager, BaseWidget, PartialBaseWidget
from xadmin.filters import FILTER_PREFIX, SEARCH_VAR
from xadmin.plugins.relate import RELATE_PREFIX

from xadmin.models import Bookmark

csrf_protect_m = method_decorator(csrf_protect)


class BookmarkPlugin(BaseAdminPlugin):

    # [{'title': "Female", 'query': {'gender': True}, 'order': ('-age'), 'cols': ('first_name', 'age', 'phones'), 'search': 'Tom'}]
    list_bookmarks = []
    show_bookmarks = True

    def has_change_permission(self, obj=None):
        if not obj or self.user.is_superuser:
            return True
        else:
            return obj.user == self.user

    def get_context(self, context):
        if not self.show_bookmarks:
            return context

        bookmarks = []

        current_qs = '&'.join(['%s=%s' % (k, v) for k, v in sorted(
            filter(lambda i: bool(i[1] and (i[0] in (COL_LIST_VAR, ORDER_VAR, SEARCH_VAR) or i[0].startswith(FILTER_PREFIX)
                                            or i[0].startswith(RELATE_PREFIX))), self.request.GET.items()))])

        model_info = (self.opts.app_label, self.opts.module_name)
        has_selected = False
        menu_title = _(u"Bookmark")
        list_base_url = reverse('xadmin:%s_%s_changelist' %
                                model_info, current_app=self.admin_site.name)

        # local bookmarks
        for bk in self.list_bookmarks:
            title = bk['title']
            params = dict(
                [(FILTER_PREFIX + k, v) for (k, v) in bk['query'].items()])
            if 'order' in bk:
                params[ORDER_VAR] = '.'.join(bk['order'])
            if 'cols' in bk:
                params[COL_LIST_VAR] = '.'.join(bk['cols'])
            if 'search' in bk:
                params[SEARCH_VAR] = bk['search']
            def check_item(i):
                return bool(i[1]) or i[1] == False
            bk_qs = '&'.join(['%s=%s' % (k, v) for k, v in sorted(filter(check_item, params.items()))])

            url = list_base_url + '?' + bk_qs
            selected = (current_qs == bk_qs)

            bookmarks.append(
                {'title': title, 'selected': selected, 'url': url})
            if selected:
                menu_title = title
                has_selected = True

        content_type = ContentType.objects.get_for_model(self.model)
        bk_model_info = (Bookmark._meta.app_label, Bookmark._meta.module_name)
        bookmarks_queryset = Bookmark.objects.filter(
            content_type=content_type,
            url_name='xadmin:%s_%s_changelist' % model_info
        ).filter(Q(user=self.user) | Q(is_share=True))

        for bk in bookmarks_queryset:
            selected = (current_qs == bk.query)

            if self.has_change_permission(bk):
                change_or_detail = 'change'
            else:
                change_or_detail = 'detail'

            bookmarks.append({'title': bk.title, 'selected': selected, 'url': bk.url, 'edit_url':
                              reverse('xadmin:%s_%s_%s' % (bk_model_info[0], bk_model_info[1], change_or_detail),
                                      args=(bk.id,))})
            if selected:
                menu_title = bk.title
                has_selected = True

        post_url = reverse('xadmin:%s_%s_bookmark' % model_info,
                           current_app=self.admin_site.name)

        new_context = {
            'bk_menu_title': menu_title,
            'bk_bookmarks': bookmarks,
            'bk_current_qs': current_qs,
            'bk_has_selected': has_selected,
            'bk_list_base_url': list_base_url,
            'bk_post_url': post_url,
            'has_add_permission_bookmark': self.admin_view.request.user.has_perm('xadmin.add_bookmark'),
            'has_change_permission_bookmark': self.admin_view.request.user.has_perm('xadmin.change_bookmark')
        }
        context.update(new_context)
        return context

    # Media
    def get_media(self, media):
        return media + self.vendor('xadmin.plugin.bookmark.js')

    # Block Views
    def block_nav_menu(self, context, nodes):
        if self.show_bookmarks:
            nodes.insert(0, loader.render_to_string('xadmin/blocks/model_list.nav_menu.bookmarks.html', context_instance=context))


class BookmarkView(ModelAdminView):

    @csrf_protect_m
    @transaction.commit_on_success
    def post(self, request):
        model_info = (self.opts.app_label, self.opts.module_name)
        url_name = 'xadmin:%s_%s_changelist' % model_info
        bookmark = Bookmark(
            content_type=ContentType.objects.get_for_model(self.model),
            title=request.POST[
                'title'], user=self.user, query=request.POST.get('query', ''),
            is_share=request.POST.get('is_share', 0), url_name=url_name)
        bookmark.save()
        content = {'title': bookmark.title, 'url': bookmark.url}
        return self.render_response(content)


class BookmarkAdmin(object):

    model_icon = 'fa fa-book'
    list_display = ('title', 'user', 'url_name', 'query')
    list_display_links = ('title',)
    user_fields = ['user']
    hidden_menu = True

    def queryset(self):
        if self.user.is_superuser:
            return Bookmark.objects.all()
        return Bookmark.objects.filter(Q(user=self.user) | Q(is_share=True))

    def get_list_display(self):
        list_display = super(BookmarkAdmin, self).get_list_display()
        if not self.user.is_superuser:
            list_display.remove('user')
        return list_display


    def has_change_permission(self, obj=None):
        if not obj or self.user.is_superuser:
            return True
        else:
            return obj.user == self.user


@widget_manager.register
class BookmarkWidget(PartialBaseWidget):
    widget_type = _('bookmark')
    widget_icon = 'fa fa-bookmark'
    description = _(
        'Bookmark Widget, can show user\'s bookmark list data in widget.')
    template = "xadmin/widgets/list.html"

    bookmark = ModelChoiceField(
        label=_('Bookmark'), queryset=Bookmark.objects.all(), required=False)

    def setup(self):
        BaseWidget.setup(self)

        bookmark = self.cleaned_data['bookmark']
        model = bookmark.content_type.model_class()
        data = QueryDict(bookmark.query)
        self.bookmark = bookmark

        if not self.title:
            self.title = unicode(bookmark)

        req = self.make_get_request("", data.items())
        self.list_view = self.get_view_class(
            ListAdminView, model, list_per_page=10, list_editable=[])(req)

    def has_perm(self):
        return True

    def context(self, context):
        list_view = self.list_view
        list_view.make_result_list()

        base_fields = list_view.base_list_display
        if len(base_fields) > 5:
            base_fields = base_fields[0:5]

        context['result_headers'] = [c for c in list_view.result_headers(
        ).cells if c.field_name in base_fields]
        context['results'] = [[o for i, o in
                               enumerate(filter(lambda c:c.field_name in base_fields, r.cells))]
                              for r in list_view.results()]
        context['result_count'] = list_view.result_count
        context['page_url'] = self.bookmark.url

site.register(Bookmark, BookmarkAdmin)
site.register_plugin(BookmarkPlugin, ListAdminView)
site.register_modelview(r'^bookmark/$', BookmarkView, name='%s_%s_bookmark')

########NEW FILE########
__FILENAME__ = chart

import datetime
import decimal
import calendar

from django.template import loader
from django.http import HttpResponseNotFound
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.utils.encoding import smart_unicode
from django.db import models
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _, ugettext

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView
from xadmin.views.dashboard import ModelBaseWidget, widget_manager
from xadmin.util import lookup_field, label_for_field, force_unicode, json


@widget_manager.register
class ChartWidget(ModelBaseWidget):
    widget_type = 'chart'
    description = _('Show models simple chart.')
    template = 'xadmin/widgets/chart.html'
    widget_icon = 'fa fa-bar-chart-o'

    def convert(self, data):
        self.list_params = data.pop('params', {})
        self.chart = data.pop('chart', None)

    def setup(self):
        super(ChartWidget, self).setup()

        self.charts = {}
        self.one_chart = False
        model_admin = self.admin_site._registry[self.model]
        chart = self.chart

        if hasattr(model_admin, 'data_charts'):
            if chart and chart in model_admin.data_charts:
                self.charts = {chart: model_admin.data_charts[chart]}
                self.one_chart = True
                if self.title is None:
                    self.title = model_admin.data_charts[chart].get('title')
            else:
                self.charts = model_admin.data_charts
                if self.title is None:
                    self.title = ugettext(
                        "%s Charts") % self.model._meta.verbose_name_plural

    def filte_choices_model(self, model, modeladmin):
        return bool(getattr(modeladmin, 'data_charts', None)) and \
            super(ChartWidget, self).filte_choices_model(model, modeladmin)

    def get_chart_url(self, name, v):
        return self.model_admin_url('chart', name) + "?" + urlencode(self.list_params)

    def context(self, context):
        context.update({
            'charts': [{"name": name, "title": v['title'], 'url': self.get_chart_url(name, v)} for name, v in self.charts.items()],
        })

    # Media
    def media(self):
        return self.vendor('flot.js', 'xadmin.plugin.charts.js')


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return calendar.timegm(o.timetuple()) * 1000
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            try:
                return super(JSONEncoder, self).default(o)
            except Exception:
                return smart_unicode(o)


class ChartsPlugin(BaseAdminPlugin):

    data_charts = {}

    def init_request(self, *args, **kwargs):
        return bool(self.data_charts)

    def get_chart_url(self, name, v):
        return self.admin_view.model_admin_url('chart', name) + self.admin_view.get_query_string()

    # Media
    def get_media(self, media):
        return media + self.vendor('flot.js', 'xadmin.plugin.charts.js')

    # Block Views
    def block_results_top(self, context, nodes):
        context.update({
            'charts': [{"name": name, "title": v['title'], 'url': self.get_chart_url(name, v)} for name, v in self.data_charts.items()],
        })
        nodes.append(loader.render_to_string('xadmin/blocks/model_list.results_top.charts.html', context_instance=context))


class ChartsView(ListAdminView):

    data_charts = {}

    def get_ordering(self):
        if 'order' in self.chart:
            return self.chart['order']
        else:
            return super(ChartsView, self).get_ordering()

    def get(self, request, name):
        if name not in self.data_charts:
            return HttpResponseNotFound()

        self.chart = self.data_charts[name]

        self.x_field = self.chart['x-field']
        y_fields = self.chart['y-field']
        self.y_fields = (
            y_fields,) if type(y_fields) not in (list, tuple) else y_fields

        datas = [{"data":[], "label": force_unicode(label_for_field(
            i, self.model, model_admin=self))} for i in self.y_fields]

        self.make_result_list()

        for obj in self.result_list:
            xf, attrs, value = lookup_field(self.x_field, obj, self)
            for i, yfname in enumerate(self.y_fields):
                yf, yattrs, yv = lookup_field(yfname, obj, self)
                datas[i]["data"].append((value, yv))

        option = {'series': {'lines': {'show': True}, 'points': {'show': False}},
                  'grid': {'hoverable': True, 'clickable': True}}
        try:
            xfield = self.opts.get_field(self.x_field)
            if type(xfield) in (models.DateTimeField, models.DateField, models.TimeField):
                option['xaxis'] = {'mode': "time", 'tickLength': 5}
                if type(xfield) is models.DateField:
                    option['xaxis']['timeformat'] = "%y/%m/%d"
                elif type(xfield) is models.TimeField:
                    option['xaxis']['timeformat'] = "%H:%M:%S"
                else:
                    option['xaxis']['timeformat'] = "%y/%m/%d %H:%M:%S"
        except Exception:
            pass

        option.update(self.chart.get('option', {}))

        content = {'data': datas, 'option': option}
        result = json.dumps(content, cls=JSONEncoder, ensure_ascii=False)

        return HttpResponse(result)

site.register_plugin(ChartsPlugin, ListAdminView)
site.register_modelview(r'^chart/(.+)/$', ChartsView, name='%s_%s_chart')

########NEW FILE########
__FILENAME__ = comments
import xadmin

from xadmin.layout import *
from xadmin.util import username_field

from django.conf import settings
from django.contrib.comments.models import Comment
from django.utils.translation import ugettext_lazy as _, ungettext
from django.contrib.comments import get_model
from django.contrib.comments.views.moderation import perform_flag, perform_approve, perform_delete

class UsernameSearch(object):
    """The User object may not be auth.User, so we need to provide
    a mechanism for issuing the equivalent of a .filter(user__username=...)
    search in CommentAdmin.
    """
    def __str__(self):
        return 'user__%s' % username_field


class CommentsAdmin(object):
    form_layout = (
        Main(
            Fieldset(None,
                'content_type', 'object_pk', 'site',
                css_class='unsort no_title'
            ),
            Fieldset('Content',
                'user', 'user_name', 'user_email', 'user_url', 'comment'
            ),
        ),
        Side(
            Fieldset(_('Metadata'),
                'submit_date', 'ip_address', 'is_public', 'is_removed'
            ),
        )
    )

    list_display = ('name', 'content_type', 'object_pk', 'ip_address', 'submit_date', 'is_public', 'is_removed')
    list_filter = ('submit_date', 'site', 'is_public', 'is_removed')
    ordering = ('-submit_date',)
    search_fields = ('comment', UsernameSearch(), 'user_name', 'user_email', 'user_url', 'ip_address')
    actions = ["flag_comments", "approve_comments", "remove_comments"]
    model_icon = 'fa fa-comment'

    def get_actions(self):
        actions = super(CommentsAdmin, self).get_actions()
        # Only superusers should be able to delete the comments from the DB.
        if not self.user.is_superuser and 'delete_selected' in actions:
            actions.pop('delete_selected')
        if not self.user.has_perm('comments.can_moderate'):
            if 'approve_comments' in actions:
                actions.pop('approve_comments')
            if 'remove_comments' in actions:
                actions.pop('remove_comments')
        return actions

    def flag_comments(self, request, queryset):
        self._bulk_flag(queryset, perform_flag,
                        lambda n: ungettext('flagged', 'flagged', n))
    flag_comments.short_description = _("Flag selected comments")
    flag_comments.icon = 'flag'

    def approve_comments(self, request, queryset):
        self._bulk_flag(queryset, perform_approve,
                        lambda n: ungettext('approved', 'approved', n))
    approve_comments.short_description = _("Approve selected comments")
    approve_comments.icon = 'ok'

    def remove_comments(self, request, queryset):
        self._bulk_flag(queryset, perform_delete,
                        lambda n: ungettext('removed', 'removed', n))
    remove_comments.short_description = _("Remove selected comments")
    remove_comments.icon = 'remove-circle'

    def _bulk_flag(self, queryset, action, done_message):
        """
        Flag, approve, or remove some comments from an admin action. Actually
        calls the `action` argument to perform the heavy lifting.
        """
        n_comments = 0
        for comment in queryset:
            action(self.request, comment)
            n_comments += 1

        msg = ungettext('1 comment was successfully %(action)s.',
                        '%(count)s comments were successfully %(action)s.',
                        n_comments)
        self.message_user(msg % {'count': n_comments, 'action': done_message(n_comments)}, 'success')

# Only register the default admin if the model is the built-in comment model
# (this won't be true if there's a custom comment app).
if 'django.contrib.comments' in settings.INSTALLED_APPS and (get_model() is Comment):
    xadmin.site.register(Comment, CommentsAdmin)

########NEW FILE########
__FILENAME__ = details


from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView


class DetailsPlugin(BaseAdminPlugin):

    show_detail_fields = []
    show_all_rel_details = True

    def result_item(self, item, obj, field_name, row):
        if (self.show_all_rel_details or (field_name in self.show_detail_fields)):
            rel_obj = None
            if hasattr(item.field, 'rel') and isinstance(item.field.rel, models.ManyToOneRel):
                rel_obj = getattr(obj, field_name)
            elif field_name in self.show_detail_fields:
                rel_obj = obj

            if rel_obj:
                if rel_obj.__class__ in site._registry:
                    try:
                        model_admin = site._registry[rel_obj.__class__]
                        has_view_perm = model_admin(self.admin_view.request).has_view_permission(rel_obj)
                        has_change_perm = model_admin(self.admin_view.request).has_change_permission(rel_obj)
                    except:
                        has_view_perm = self.admin_view.has_model_perm(rel_obj.__class__, 'view')
                        has_change_perm = self.has_model_perm(rel_obj.__class__, 'change')
                else:
                    has_view_perm = self.admin_view.has_model_perm(rel_obj.__class__, 'view')
                    has_change_perm = self.has_model_perm(rel_obj.__class__, 'change')

            if rel_obj and has_view_perm:
                opts = rel_obj._meta
                try:
                    item_res_uri = reverse(
                        '%s:%s_%s_detail' % (self.admin_site.app_name,
                                             opts.app_label, opts.module_name),
                        args=(getattr(rel_obj, opts.pk.attname),))
                    if item_res_uri:
                        if has_change_perm:
                            edit_url = reverse(
                                '%s:%s_%s_change' % (self.admin_site.app_name, opts.app_label, opts.module_name),
                                args=(getattr(rel_obj, opts.pk.attname),))
                        else:
                            edit_url = ''
                        item.btns.append('<a data-res-uri="%s" data-edit-uri="%s" class="details-handler" rel="tooltip" title="%s"><i class="fa fa-info-sign"></i></a>'
                                         % (item_res_uri, edit_url, _(u'Details of %s') % str(rel_obj)))
                except NoReverseMatch:
                    pass
        return item

    # Media
    def get_media(self, media):
        if self.show_all_rel_details or self.show_detail_fields:
            media = media + self.vendor('xadmin.plugin.details.js', 'xadmin.form.css')
        return media

site.register_plugin(DetailsPlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = editable
from django import forms
from django import template
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models, transaction
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponse
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from xadmin.plugins.ajax import JsonErrorDict
from xadmin.sites import site
from xadmin.util import lookup_field, display_for_field, label_for_field, unquote, boolean_icon
from xadmin.views import BaseAdminPlugin, ModelFormAdminView, ListAdminView
from xadmin.views.base import csrf_protect_m, filter_hook
from xadmin.views.edit import ModelFormAdminUtil
from xadmin.views.list import EMPTY_CHANGELIST_VALUE
from xadmin.layout import FormHelper


class EditablePlugin(BaseAdminPlugin):

    list_editable = []

    def __init__(self, admin_view):
        super(EditablePlugin, self).__init__(admin_view)
        self.editable_need_fields = {}

    def init_request(self, *args, **kwargs):
        active = bool(self.request.method == 'GET' and self.admin_view.has_change_permission() and self.list_editable)
        if active:
            self.model_form = self.get_model_view(ModelFormAdminUtil, self.model).form_obj
        return active

    def result_item(self, item, obj, field_name, row):
        if self.list_editable and item.field and item.field.editable and (field_name in self.list_editable):            
            pk = getattr(obj, obj._meta.pk.attname)
            field_label = label_for_field(field_name, obj,
                                          model_admin=self.admin_view,
                                          return_attr=False
                                          )

            item.wraps.insert(0, '<span class="editable-field">%s</span>')
            item.btns.append((
                '<a class="editable-handler" title="%s" data-editable-field="%s" data-editable-loadurl="%s">'+
                '<i class="fa fa-edit"></i></a>') %
                 (_(u"Enter %s") % field_label, field_name, self.admin_view.model_admin_url('patch', pk) + '?fields=' + field_name))

            if field_name not in self.editable_need_fields:
                self.editable_need_fields[field_name] = item.field
        return item

    # Media
    def get_media(self, media):
        if self.editable_need_fields:
            media = media + self.model_form.media + \
                self.vendor(
                    'xadmin.plugin.editable.js', 'xadmin.widget.editable.css')
        return media


class EditPatchView(ModelFormAdminView, ListAdminView):

    def init_request(self, object_id, *args, **kwargs):
        self.org_obj = self.get_object(unquote(object_id))

        # For list view get new field display html
        self.pk_attname = self.opts.pk.attname

        if not self.has_change_permission(self.org_obj):
            raise PermissionDenied

        if self.org_obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') %
                          {'name': force_unicode(self.opts.verbose_name), 'key': escape(object_id)})

    def get_new_field_html(self, f):
        result = self.result_item(self.org_obj, f, {'is_display_first':
                                  False, 'object': self.org_obj})
        return mark_safe(result.text) if result.allow_tags else conditional_escape(result.text)

    def _get_new_field_html(self, field_name):
        try:
            f, attr, value = lookup_field(field_name, self.org_obj, self)
        except (AttributeError, ObjectDoesNotExist):
            return EMPTY_CHANGELIST_VALUE
        else:
            allow_tags = False
            if f is None:
                allow_tags = getattr(attr, 'allow_tags', False)
                boolean = getattr(attr, 'boolean', False)
                if boolean:
                    allow_tags = True
                    text = boolean_icon(value)
                else:
                    text = smart_unicode(value)
            else:
                if isinstance(f.rel, models.ManyToOneRel):
                    field_val = getattr(self.org_obj, f.name)
                    if field_val is None:
                        text = EMPTY_CHANGELIST_VALUE
                    else:
                        text = field_val
                else:
                    text = display_for_field(value, f)
            return mark_safe(text) if allow_tags else conditional_escape(text)

    @filter_hook
    def get(self, request, object_id):
        model_fields = [f.name for f in self.opts.fields]
        fields = [f for f in request.GET['fields'].split(',') if f in model_fields]
        defaults = {
            "form": forms.ModelForm,
            "fields": fields,
            "formfield_callback": self.formfield_for_dbfield,
        }
        form_class = modelform_factory(self.model, **defaults)
        form = form_class(instance=self.org_obj)

        helper = FormHelper()
        helper.form_tag = False
        form.helper = helper

        s = '{% load i18n crispy_forms_tags %}<form method="post" action="{{action_url}}">{% crispy form %}'+ \
            '<button type="submit" class="btn btn-success btn-block btn-sm">{% trans "Apply" %}</button></form>'
        t = template.Template(s)
        c = template.Context({'form':form, 'action_url': self.model_admin_url('patch', self.org_obj.pk)})

        return HttpResponse(t.render(c))


    @filter_hook
    @csrf_protect_m
    @transaction.commit_on_success
    def post(self, request, object_id):
        model_fields = [f.name for f in self.opts.fields]
        fields = [f for f in request.POST.keys() if f in model_fields]
        defaults = {
            "form": forms.ModelForm,
            "fields": fields,
            "formfield_callback": self.formfield_for_dbfield,
        }
        form_class = modelform_factory(self.model, **defaults)
        form = form_class(
            instance=self.org_obj, data=request.POST, files=request.FILES)

        result = {}
        if form.is_valid():
            form.save(commit=True)
            result['result'] = 'success'
            result['new_data'] = form.cleaned_data
            result['new_html'] = dict(
                [(f, self.get_new_field_html(f)) for f in fields])
        else:
            result['result'] = 'error'
            result['errors'] = JsonErrorDict(form.errors, form).as_json()

        return self.render_response(result)

site.register_plugin(EditablePlugin, ListAdminView)
site.register_modelview(r'^(.+)/patch/$', EditPatchView, name='%s_%s_patch')

########NEW FILE########
__FILENAME__ = export
import StringIO
import datetime
import sys

from django.http import HttpResponse
from django.template import loader
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.utils.xmlutils import SimplerXMLGenerator
from django.db.models import BooleanField, NullBooleanField
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView
from xadmin.util import json
from xadmin.views.list import ALL_VAR

try:
    import xlwt
    has_xlwt = True
except:
    has_xlwt = False

try:
    import xlsxwriter
    has_xlsxwriter = True
except:
    has_xlsxwriter = False


class ExportMenuPlugin(BaseAdminPlugin):

    list_export = ('xlsx', 'xls', 'csv', 'xml', 'json')
    export_names = {'xlsx': 'Excel 2007', 'xls': 'Excel', 'csv': 'CSV',
                    'xml': 'XML', 'json': 'JSON'}

    def init_request(self, *args, **kwargs):
        self.list_export = [
            f for f in self.list_export
            if (f != 'xlsx' or has_xlsxwriter) and (f != 'xls' or has_xlwt)]

    def block_top_toolbar(self, context, nodes):
        if self.list_export:
            context.update({
                'show_export_all': self.admin_view.paginator.count > self.admin_view.list_per_page and not ALL_VAR in self.admin_view.request.GET,
                'form_params': self.admin_view.get_form_params({'_do_': 'export'}, ('export_type',)),
                'export_types': [{'type': et, 'name': self.export_names[et]} for et in self.list_export],
            })
            nodes.append(loader.render_to_string('xadmin/blocks/model_list.top_toolbar.exports.html', context_instance=context))


class ExportPlugin(BaseAdminPlugin):

    export_mimes = {'xlsx': 'application/vnd.ms-excel',
                    'xls': 'application/vnd.ms-excel', 'csv': 'text/csv',
                    'xml': 'application/xhtml+xml', 'json': 'application/json'}

    def init_request(self, *args, **kwargs):
        return self.request.GET.get('_do_') == 'export'

    def _format_value(self, o):
        if (o.field is None and getattr(o.attr, 'boolean', False)) or \
           (o.field and isinstance(o.field, (BooleanField, NullBooleanField))):
                value = o.value
        elif str(o.text).startswith("<span class='text-muted'>"):
            value = escape(str(o.text)[25:-7])
        else:
            value = escape(str(o.text))
        return value

    def _get_objects(self, context):
        headers = [c for c in context['result_headers'].cells if c.export]
        rows = context['results']

        return [dict([
            (force_unicode(headers[i].text), self._format_value(o)) for i, o in
            enumerate(filter(lambda c:getattr(c, 'export', False), r.cells))]) for r in rows]

    def _get_datas(self, context):
        rows = context['results']

        new_rows = [[self._format_value(o) for o in
            filter(lambda c:getattr(c, 'export', False), r.cells)] for r in rows]
        new_rows.insert(0, [force_unicode(c.text) for c in context['result_headers'].cells if c.export])
        return new_rows

    def get_xlsx_export(self, context):
        datas = self._get_datas(context)
        output = StringIO.StringIO()
        export_header = (
            self.request.GET.get('export_xlsx_header', 'off') == 'on')

        model_name = self.opts.verbose_name
        book = xlsxwriter.Workbook(output)
        sheet = book.add_worksheet(
            u"%s %s" % (_(u'Sheet'), force_unicode(model_name)))
        styles = {'datetime': book.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'}),
                  'date': book.add_format({'num_format': 'yyyy-mm-dd'}),
                  'time': book.add_format({'num_format': 'hh:mm:ss'}),
                  'header': book.add_format({'font': 'name Times New Roman', 'color': 'red', 'bold': 'on', 'num_format': '#,##0.00'}),
                  'default': book.add_format()}

        if not export_header:
            datas = datas[1:]
        for rowx, row in enumerate(datas):
            for colx, value in enumerate(row):
                if export_header and rowx == 0:
                    cell_style = styles['header']
                else:
                    if isinstance(value, datetime.datetime):
                        cell_style = styles['datetime']
                    elif isinstance(value, datetime.date):
                        cell_style = styles['date']
                    elif isinstance(value, datetime.time):
                        cell_style = styles['time']
                    else:
                        cell_style = styles['default']
                sheet.write(rowx, colx, value, cell_style)
        book.close()

        output.seek(0)
        return output.getvalue()

    def get_xls_export(self, context):
        datas = self._get_datas(context)
        output = StringIO.StringIO()
        export_header = (
            self.request.GET.get('export_xls_header', 'off') == 'on')

        model_name = self.opts.verbose_name
        book = xlwt.Workbook(encoding='utf8')
        sheet = book.add_sheet(
            u"%s %s" % (_(u'Sheet'), force_unicode(model_name)))
        styles = {'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
                  'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
                  'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
                  'header': xlwt.easyxf('font: name Times New Roman, color-index red, bold on', num_format_str='#,##0.00'),
                  'default': xlwt.Style.default_style}

        if not export_header:
            datas = datas[1:]
        for rowx, row in enumerate(datas):
            for colx, value in enumerate(row):
                if export_header and rowx == 0:
                    cell_style = styles['header']
                else:
                    if isinstance(value, datetime.datetime):
                        cell_style = styles['datetime']
                    elif isinstance(value, datetime.date):
                        cell_style = styles['date']
                    elif isinstance(value, datetime.time):
                        cell_style = styles['time']
                    else:
                        cell_style = styles['default']
                sheet.write(rowx, colx, value, style=cell_style)
        book.save(output)

        output.seek(0)
        return output.getvalue()

    def _format_csv_text(self, t):
        if isinstance(t, bool):
            return _('Yes') if t else _('No')
        t = t.replace('"', '""').replace(',', '\,')
        if isinstance(t, basestring):
            t = '"%s"' % t
        return t

    def get_csv_export(self, context):
        datas = self._get_datas(context)
        stream = []

        if self.request.GET.get('export_csv_header', 'off') != 'on':
            datas = datas[1:]

        for row in datas:
            stream.append(','.join(map(self._format_csv_text, row)))

        return '\r\n'.join(stream)

    def _to_xml(self, xml, data):
        if isinstance(data, (list, tuple)):
            for item in data:
                xml.startElement("row", {})
                self._to_xml(xml, item)
                xml.endElement("row")
        elif isinstance(data, dict):
            for key, value in data.iteritems():
                key = key.replace(' ', '_')
                xml.startElement(key, {})
                self._to_xml(xml, value)
                xml.endElement(key)
        else:
            xml.characters(smart_unicode(data))

    def get_xml_export(self, context):
        results = self._get_objects(context)
        stream = StringIO.StringIO()

        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()
        xml.startElement("objects", {})

        self._to_xml(xml, results)

        xml.endElement("objects")
        xml.endDocument()

        return stream.getvalue().split('\n')[1]

    def get_json_export(self, context):
        results = self._get_objects(context)
        return json.dumps({'objects': results}, ensure_ascii=False,
                          indent=(self.request.GET.get('export_json_format', 'off') == 'on') and 4 or None)

    def get_response(self, response, context, *args, **kwargs):
        file_type = self.request.GET.get('export_type', 'csv')
        response = HttpResponse(
            mimetype="%s; charset=UTF-8" % self.export_mimes[file_type])

        file_name = self.opts.verbose_name.replace(' ', '_')
        response['Content-Disposition'] = ('attachment; filename=%s.%s' % (
            file_name, file_type)).encode('utf-8')

        response.write(getattr(self, 'get_%s_export' % file_type)(context))
        return response

    # View Methods
    def get_result_list(self, __):
        if self.request.GET.get('all', 'off') == 'on':
            self.admin_view.list_per_page = sys.maxint
        return __()

    def result_header(self, item, field_name, row):
        item.export = not item.attr or field_name == '__str__' or getattr(item.attr, 'allow_export', True)
        return item

    def result_item(self, item, obj, field_name, row):
        item.export = item.field or field_name == '__str__' or getattr(item.attr, 'allow_export', True)
        return item


site.register_plugin(ExportMenuPlugin, ListAdminView)
site.register_plugin(ExportPlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = filters
import operator
from xadmin import widgets

from xadmin.util import get_fields_from_path, lookup_needs_distinct
from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured, ValidationError
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.db.models.related import RelatedObject
from django.db.models.sql.query import LOOKUP_SEP, QUERY_TERMS
from django.template import loader
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from xadmin.filters import manager as filter_manager, FILTER_PREFIX, SEARCH_VAR, DateFieldListFilter, RelatedFieldSearchFilter
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView


class IncorrectLookupParameters(Exception):
    pass


class FilterPlugin(BaseAdminPlugin):
    list_filter = ()
    search_fields = ()
    free_query_filter = True

    def lookup_allowed(self, lookup, value):
        model = self.model
        # Check FKey lookups that are allowed, so that popups produced by
        # ForeignKeyRawIdWidget, on the basis of ForeignKey.limit_choices_to,
        # are allowed to work.
        for l in model._meta.related_fkey_lookups:
            for k, v in widgets.url_params_from_lookup_dict(l).items():
                if k == lookup and v == value:
                    return True

        parts = lookup.split(LOOKUP_SEP)

        # Last term in lookup is a query term (__exact, __startswith etc)
        # This term can be ignored.
        if len(parts) > 1 and parts[-1] in QUERY_TERMS:
            parts.pop()

        # Special case -- foo__id__exact and foo__id queries are implied
        # if foo has been specificially included in the lookup list; so
        # drop __id if it is the last part. However, first we need to find
        # the pk attribute name.
        rel_name = None
        for part in parts[:-1]:
            try:
                field, _, _, _ = model._meta.get_field_by_name(part)
            except FieldDoesNotExist:
                # Lookups on non-existants fields are ok, since they're ignored
                # later.
                return True
            if hasattr(field, 'rel'):
                model = field.rel.to
                rel_name = field.rel.get_related_field().name
            elif isinstance(field, RelatedObject):
                model = field.model
                rel_name = model._meta.pk.name
            else:
                rel_name = None
        if rel_name and len(parts) > 1 and parts[-1] == rel_name:
            parts.pop()

        if len(parts) == 1:
            return True
        clean_lookup = LOOKUP_SEP.join(parts)
        return clean_lookup in self.list_filter

    def get_list_queryset(self, queryset):
        lookup_params = dict([(smart_str(k)[len(FILTER_PREFIX):], v) for k, v in self.admin_view.params.items()
                              if smart_str(k).startswith(FILTER_PREFIX) and v != ''])
        for p_key, p_val in lookup_params.iteritems():
            if p_val == "False":
                lookup_params[p_key] = False
        use_distinct = False

        # for clean filters
        self.admin_view.has_query_param = bool(lookup_params)
        self.admin_view.clean_query_url = self.admin_view.get_query_string(remove=
                                                                           [k for k in self.request.GET.keys() if k.startswith(FILTER_PREFIX)])

        # Normalize the types of keys
        if not self.free_query_filter:
            for key, value in lookup_params.items():
                if not self.lookup_allowed(key, value):
                    raise SuspiciousOperation(
                        "Filtering by %s not allowed" % key)

        self.filter_specs = []
        if self.list_filter:
            for list_filter in self.list_filter:
                if callable(list_filter):
                    # This is simply a custom list filter class.
                    spec = list_filter(self.request, lookup_params,
                                       self.model, self)
                else:
                    field_path = None
                    field_parts = []
                    if isinstance(list_filter, (tuple, list)):
                        # This is a custom FieldListFilter class for a given field.
                        field, field_list_filter_class = list_filter
                    else:
                        # This is simply a field name, so use the default
                        # FieldListFilter class that has been registered for
                        # the type of the given field.
                        field, field_list_filter_class = list_filter, filter_manager.create
                    if not isinstance(field, models.Field):
                        field_path = field
                        field_parts = get_fields_from_path(
                            self.model, field_path)
                        field = field_parts[-1]
                    spec = field_list_filter_class(
                        field, self.request, lookup_params,
                        self.model, self.admin_view, field_path=field_path)

                    if len(field_parts)>1:
                        # Add related model name to title
                        spec.title = "%s %s"%(field_parts[-2].name,spec.title)

                    # Check if we need to use distinct()
                    use_distinct = (use_distinct or
                                    lookup_needs_distinct(self.opts, field_path))
                if spec and spec.has_output():
                    try:
                        new_qs = spec.do_filte(queryset)
                    except ValidationError, e:
                        new_qs = None
                        self.admin_view.message_user(_("<b>Filtering error:</b> %s") % e.messages[0], 'error')
                    if new_qs is not None:
                        queryset = new_qs

                    self.filter_specs.append(spec)

        self.has_filters = bool(self.filter_specs)
        self.admin_view.filter_specs = self.filter_specs
        self.admin_view.used_filter_num = len(
            filter(lambda f: f.is_used, self.filter_specs))

        try:
            for key, value in lookup_params.items():
                use_distinct = (
                    use_distinct or lookup_needs_distinct(self.opts, key))
        except FieldDoesNotExist, e:
            raise IncorrectLookupParameters(e)

        try:
            queryset = queryset.filter(**lookup_params)
        except (SuspiciousOperation, ImproperlyConfigured):
            raise
        except Exception, e:
            raise IncorrectLookupParameters(e)

        query = self.request.GET.get(SEARCH_VAR, '')

        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        if self.search_fields and query:
            orm_lookups = [construct_search(str(search_field))
                           for search_field in self.search_fields]
            for bit in query.split():
                or_queries = [models.Q(**{orm_lookup: bit})
                              for orm_lookup in orm_lookups]
                queryset = queryset.filter(reduce(operator.or_, or_queries))
            if not use_distinct:
                for search_spec in orm_lookups:
                    if lookup_needs_distinct(self.opts, search_spec):
                        use_distinct = True
                        break
            self.admin_view.search_query = query

        if use_distinct:
            return queryset.distinct()
        else:
            return queryset

    # Media
    def get_media(self, media):
        if bool(filter(lambda s: isinstance(s, DateFieldListFilter), self.filter_specs)):
            media = media + self.vendor('datepicker.css', 'datepicker.js',
                                        'xadmin.widget.datetime.js')
        if bool(filter(lambda s: isinstance(s, RelatedFieldSearchFilter), self.filter_specs)):
            media = media + self.vendor(
                'select.js', 'select.css', 'xadmin.widget.select.js')
        return media + self.vendor('xadmin.plugin.filters.js')

    # Block Views
    def block_nav_menu(self, context, nodes):
        if self.has_filters:
            nodes.append(loader.render_to_string('xadmin/blocks/model_list.nav_menu.filters.html', context_instance=context))

    def block_nav_form(self, context, nodes):
        if self.search_fields:
            nodes.append(
                loader.render_to_string(
                    'xadmin/blocks/model_list.nav_form.search_form.html',
                    {'search_var': SEARCH_VAR,
                        'remove_search_url': self.admin_view.get_query_string(remove=[SEARCH_VAR]),
                        'search_form_params': self.admin_view.get_form_params(remove=[SEARCH_VAR])},
                    context_instance=context))

site.register_plugin(FilterPlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = images
from django.db import models
from django import forms
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ModelFormAdminView, DetailAdminView, ListAdminView


def get_gallery_modal():
    return """
        <!-- modal-gallery is the modal dialog used for the image gallery -->
        <div id="modal-gallery" class="modal modal-gallery fade" tabindex="-1">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h4 class="modal-title"></h4>
              </div>
              <div class="modal-body"><div class="modal-image"><h1 class="loader"><i class="fa-spinner fa-spin fa fa-large loader"></i></h1></div></div>
              <div class="modal-footer">
                  <a class="btn btn-info modal-prev"><i class="fa fa-arrow-left"></i> <span>%s</span></a>
                  <a class="btn btn-primary modal-next"><span>%s</span> <i class="fa fa-arrow-right"></i></a>
                  <a class="btn btn-success modal-play modal-slideshow" data-slideshow="5000"><i class="fa fa-play"></i> <span>%s</span></a>
                  <a class="btn btn-default modal-download" target="_blank"><i class="fa fa-download"></i> <span>%s</span></a>
              </div>
            </div><!-- /.modal-content -->
          </div><!-- /.modal-dialog -->
        </div>
    """ % (_('Previous'), _('Next'), _('Slideshow'), _('Download'))


class AdminImageField(forms.ImageField):

    def widget_attrs(self, widget):
        return {'label': self.label}


class AdminImageWidget(forms.FileInput):
    """
    A ImageField Widget that shows its current value if it has one.
    """
    def __init__(self, attrs={}):
        super(AdminImageWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        output = []
        if value and hasattr(value, "url"):
            label = self.attrs.get('label', name)
            output.append('<a href="%s" target="_blank" title="%s" data-gallery="gallery"><img src="%s" class="field_img"/></a><br/>%s ' %
                         (value.url, label, value.url, _('Change:')))
        output.append(super(AdminImageWidget, self).render(name, value, attrs))
        return mark_safe(u''.join(output))


class ModelDetailPlugin(BaseAdminPlugin):

    def __init__(self, admin_view):
        super(ModelDetailPlugin, self).__init__(admin_view)
        self.include_image = False

    def get_field_attrs(self, attrs, db_field, **kwargs):
        if isinstance(db_field, models.ImageField):
            attrs['widget'] = AdminImageWidget
            attrs['form_class'] = AdminImageField
            self.include_image = True
        return attrs

    def get_field_result(self, result, field_name):
        if isinstance(result.field, models.ImageField):
            if result.value:
                img = getattr(result.obj, field_name)
                result.text = mark_safe('<a href="%s" target="_blank" title="%s" data-gallery="gallery"><img src="%s" class="field_img"/></a>' % (img.url, result.label, img.url))
                self.include_image = True
        return result

    # Media
    def get_media(self, media):
        if self.include_image:
            media = media + self.vendor('image-gallery.js',
                                        'image-gallery.css')
        return media

    def block_before_fieldsets(self, context, node):
        if self.include_image:
            return '<div id="gallery" data-toggle="modal-gallery" data-target="#modal-gallery">'

    def block_after_fieldsets(self, context, node):
        if self.include_image:
            return "</div>"

    def block_extrabody(self, context, node):
        if self.include_image:
            return get_gallery_modal()


class ModelListPlugin(BaseAdminPlugin):

    list_gallery = False

    def init_request(self, *args, **kwargs):
        return bool(self.list_gallery)

    # Media
    def get_media(self, media):
        return media + self.vendor('image-gallery.js', 'image-gallery.css')

    def block_results_top(self, context, node):
        return '<div id="gallery" data-toggle="modal-gallery" data-target="#modal-gallery">'

    def block_results_bottom(self, context, node):
        return "</div>"

    def block_extrabody(self, context, node):
        return get_gallery_modal()


site.register_plugin(ModelDetailPlugin, DetailAdminView)
site.register_plugin(ModelDetailPlugin, ModelFormAdminView)
site.register_plugin(ModelListPlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = inline
import copy
import inspect
from django import forms
from django.forms.formsets import all_valid, DELETION_FIELD_NAME
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from django.contrib.contenttypes.generic import BaseGenericInlineFormSet, generic_inlineformset_factory
from django.template import loader
from django.template.loader import render_to_string
from xadmin.layout import FormHelper, Layout, flatatt, Container, Column, Field, Fieldset
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ModelFormAdminView, DetailAdminView, filter_hook


class ShowField(Field):
    template = "xadmin/layout/field_value.html"

    def __init__(self, admin_view, *args, **kwargs):
        super(ShowField, self).__init__(*args, **kwargs)
        self.admin_view = admin_view
        if admin_view.style == 'table':
            self.template = "xadmin/layout/field_value_td.html"

    def render(self, form, form_style, context):
        html = ''
        detail = form.detail
        for field in self.fields:
            if not isinstance(form.fields[field].widget, forms.HiddenInput):
                result = detail.get_field_result(field)
                html += loader.render_to_string(
                    self.template, {'field': form[field], 'result': result})
        return html


class DeleteField(Field):

    def render(self, form, form_style, context):
        if form.instance.pk:
            self.attrs['type'] = 'hidden'
            return super(DeleteField, self).render(form, form_style, context)
        else:
            return ""


class TDField(Field):
    template = "xadmin/layout/td-field.html"


class InlineStyleManager(object):
    inline_styles = {}

    def register_style(self, name, style):
        self.inline_styles[name] = style

    def get_style(self, name='stacked'):
        return self.inline_styles.get(name)

style_manager = InlineStyleManager()


class InlineStyle(object):
    template = 'xadmin/edit_inline/stacked.html'

    def __init__(self, view, formset):
        self.view = view
        self.formset = formset

    def update_layout(self, helper):
        pass

    def get_attrs(self):
        return {}
style_manager.register_style('stacked', InlineStyle)


class OneInlineStyle(InlineStyle):
    template = 'xadmin/edit_inline/one.html'
style_manager.register_style("one", OneInlineStyle)


class AccInlineStyle(InlineStyle):
    template = 'xadmin/edit_inline/accordion.html'
style_manager.register_style("accordion", AccInlineStyle)


class TabInlineStyle(InlineStyle):
    template = 'xadmin/edit_inline/tab.html'
style_manager.register_style("tab", TabInlineStyle)


class TableInlineStyle(InlineStyle):
    template = 'xadmin/edit_inline/tabular.html'

    def update_layout(self, helper):
        helper.add_layout(
            Layout(*[TDField(f) for f in self.formset[0].fields.keys()]))

    def get_attrs(self):
        fields = []
        readonly_fields = []
        if len(self.formset):
            fields = [f for k, f in self.formset[0].fields.items() if k != DELETION_FIELD_NAME]
            readonly_fields = [f for f in getattr(self.formset[0], 'readonly_fields', [])]
        return {
            'fields': fields,
            'readonly_fields': readonly_fields
        }
style_manager.register_style("table", TableInlineStyle)


def replace_field_to_value(layout, av):
    if layout:
        for i, lo in enumerate(layout.fields):
            if isinstance(lo, Field) or issubclass(lo.__class__, Field):
                layout.fields[i] = ShowField(av, *lo.fields, **lo.attrs)
            elif isinstance(lo, basestring):
                layout.fields[i] = ShowField(av, lo)
            elif hasattr(lo, 'get_field_names'):
                replace_field_to_value(lo, av)


class InlineModelAdmin(ModelFormAdminView):

    fk_name = None
    formset = BaseInlineFormSet
    extra = 3
    max_num = None
    can_delete = True
    fields = []
    admin_view = None
    style = 'stacked'

    def init(self, admin_view):
        self.admin_view = admin_view
        self.parent_model = admin_view.model
        self.org_obj = getattr(admin_view, 'org_obj', None)
        self.model_instance = self.org_obj or admin_view.model()

        return self

    @filter_hook
    def get_formset(self, **kwargs):
        """Returns a BaseInlineFormSet class for use in admin add/change views."""
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(self.get_readonly_fields())
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # InlineModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        # if exclude is an empty list we use None, since that's the actual
        # default
        exclude = exclude or None
        can_delete = self.can_delete and self.has_delete_permission()
        defaults = {
            "form": self.form,
            "formset": self.formset,
            "fk_name": self.fk_name,
            "exclude": exclude,
            "formfield_callback": self.formfield_for_dbfield,
            "extra": self.extra,
            "max_num": self.max_num,
            "can_delete": can_delete,
        }
        defaults.update(kwargs)
        return inlineformset_factory(self.parent_model, self.model, **defaults)

    @filter_hook
    def instance_form(self, **kwargs):
        formset = self.get_formset(**kwargs)
        attrs = {
            'instance': self.model_instance,
            'queryset': self.queryset()
        }
        if self.request_method == 'post':
            attrs.update({
                'data': self.request.POST, 'files': self.request.FILES,
                'save_as_new': "_saveasnew" in self.request.POST
            })
        instance = formset(**attrs)
        instance.view = self

        helper = FormHelper()
        helper.form_tag = False
        # override form method to prevent render csrf_token in inline forms, see template 'bootstrap/whole_uni_form.html'
        helper.form_method = 'get'

        style = style_manager.get_style(
            'one' if self.max_num == 1 else self.style)(self, instance)
        style.name = self.style

        if len(instance):
            layout = copy.deepcopy(self.form_layout)

            if layout is None:
                layout = Layout(*instance[0].fields.keys())
            elif type(layout) in (list, tuple) and len(layout) > 0:
                layout = Layout(*layout)

                rendered_fields = [i[1] for i in layout.get_field_names()]
                layout.extend([f for f in instance[0]
                              .fields.keys() if f not in rendered_fields])

            helper.add_layout(layout)
            style.update_layout(helper)

            # replace delete field with Dynamic field, for hidden delete field when instance is NEW.
            helper[DELETION_FIELD_NAME].wrap(DeleteField)

        instance.helper = helper
        instance.style = style

        readonly_fields = self.get_readonly_fields()
        if readonly_fields:
            for form in instance:
                form.readonly_fields = []
                inst = form.save(commit=False)
                if inst:
                    for readonly_field in readonly_fields:
                        value = None
                        label = None
                        if readonly_field in inst._meta.get_all_field_names():
                            label = inst._meta.get_field_by_name(readonly_field)[0].verbose_name
                            value = unicode(getattr(inst, readonly_field))
                        elif inspect.ismethod(getattr(inst, readonly_field, None)):
                            value = getattr(inst, readonly_field)()
                            label = getattr(getattr(inst, readonly_field), 'short_description', readonly_field)
                        elif inspect.ismethod(getattr(self, readonly_field, None)):
                            value = getattr(self, readonly_field)(inst)
                            label = getattr(getattr(self, readonly_field), 'short_description', readonly_field)
                        if value:
                            form.readonly_fields.append({'label': label, 'contents': value})
        return instance

    def has_auto_field(self, form):
        if form._meta.model._meta.has_auto_field:
            return True
        for parent in form._meta.model._meta.get_parent_list():
            if parent._meta.has_auto_field:
                return True
        return False

    def queryset(self):
        queryset = super(InlineModelAdmin, self).queryset()
        if not self.has_change_permission() and not self.has_view_permission():
            queryset = queryset.none()
        return queryset

    def has_add_permission(self):
        if self.opts.auto_created:
            return self.has_change_permission()
        return self.user.has_perm(
            self.opts.app_label + '.' + self.opts.get_add_permission())

    def has_change_permission(self):
        opts = self.opts
        if opts.auto_created:
            for field in opts.fields:
                if field.rel and field.rel.to != self.parent_model:
                    opts = field.rel.to._meta
                    break
        return self.user.has_perm(
            opts.app_label + '.' + opts.get_change_permission())

    def has_delete_permission(self):
        if self.opts.auto_created:
            return self.has_change_permission()
        return self.user.has_perm(
            self.opts.app_label + '.' + self.opts.get_delete_permission())


class GenericInlineModelAdmin(InlineModelAdmin):
    ct_field = "content_type"
    ct_fk_field = "object_id"

    formset = BaseGenericInlineFormSet

    def get_formset(self, **kwargs):
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(self.get_readonly_fields())
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # GenericInlineModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        exclude = exclude or None
        can_delete = self.can_delete and self.has_delete_permission()
        defaults = {
            "ct_field": self.ct_field,
            "fk_field": self.ct_fk_field,
            "form": self.form,
            "formfield_callback": self.formfield_for_dbfield,
            "formset": self.formset,
            "extra": self.extra,
            "can_delete": can_delete,
            "can_order": False,
            "max_num": self.max_num,
            "exclude": exclude
        }
        defaults.update(kwargs)
        return generic_inlineformset_factory(self.model, **defaults)


class InlineFormset(Fieldset):

    def __init__(self, formset, allow_blank=False, **kwargs):
        self.fields = []
        self.css_class = kwargs.pop('css_class', '')
        self.css_id = "%s-group" % formset.prefix
        self.template = formset.style.template
        self.inline_style = formset.style.name
        if allow_blank and len(formset) == 0:
            self.template = 'xadmin/edit_inline/blank.html'
            self.inline_style = 'blank'
        self.formset = formset
        self.model = formset.model
        self.opts = formset.model._meta
        self.flat_attrs = flatatt(kwargs)
        self.extra_attrs = formset.style.get_attrs()

    def render(self, form, form_style, context):
        return render_to_string(
            self.template, dict({'formset': self, 'prefix': self.formset.prefix, 'inline_style': self.inline_style}, **self.extra_attrs),
            context_instance=context)


class Inline(Fieldset):

    def __init__(self, rel_model):
        self.model = rel_model
        self.fields = []

    def render(self, form, form_style, context):
        return ""


def get_first_field(layout, clz):
    for layout_object in layout.fields:
        if issubclass(layout_object.__class__, clz):
            return layout_object
        elif hasattr(layout_object, 'get_field_names'):
            gf = get_first_field(layout_object, clz)
            if gf:
                return gf


def replace_inline_objects(layout, fs):
    if not fs:
        return
    for i, layout_object in enumerate(layout.fields):
        if isinstance(layout_object, Inline) and layout_object.model in fs:
            layout.fields[i] = fs.pop(layout_object.model)
        elif hasattr(layout_object, 'get_field_names'):
            replace_inline_objects(layout_object, fs)


class InlineFormsetPlugin(BaseAdminPlugin):
    inlines = []

    @property
    def inline_instances(self):
        if not hasattr(self, '_inline_instances'):
            inline_instances = []
            for inline_class in self.inlines:
                inline = self.admin_view.get_view(
                    (getattr(inline_class, 'generic_inline', False) and GenericInlineModelAdmin or InlineModelAdmin),
                    inline_class).init(self.admin_view)
                if not (inline.has_add_permission() or
                        inline.has_change_permission() or
                        inline.has_delete_permission() or
                        inline.has_view_permission()):
                    continue
                if not inline.has_add_permission():
                    inline.max_num = 0
                inline_instances.append(inline)
            self._inline_instances = inline_instances
        return self._inline_instances

    def instance_forms(self, ret):
        self.formsets = []
        for inline in self.inline_instances:
            if inline.has_change_permission():
                self.formsets.append(inline.instance_form())
            else:
                self.formsets.append(self._get_detail_formset_instance(inline))
        self.admin_view.formsets = self.formsets

    def valid_forms(self, result):
        return all_valid(self.formsets) and result

    def save_related(self):
        for formset in self.formsets:
            formset.instance = self.admin_view.new_obj
            formset.save()

    def get_context(self, context):
        context['inline_formsets'] = self.formsets
        return context

    def get_error_list(self, errors):
        for fs in self.formsets:
            errors.extend(fs.non_form_errors())
            for errors_in_inline_form in fs.errors:
                errors.extend(errors_in_inline_form.values())
        return errors

    def get_form_layout(self, layout):
        allow_blank = isinstance(self.admin_view, DetailAdminView)
        # fixed #176 bug, change dict to list
        fs = [(f.model, InlineFormset(f, allow_blank)) for f in self.formsets]
        replace_inline_objects(layout, fs)

        if fs:
            container = get_first_field(layout, Column)
            if not container:
                container = get_first_field(layout, Container)
            if not container:
                container = layout

            # fixed #176 bug, change dict to list
            for key, value in fs:
                container.append(value)

        return layout

    def get_media(self, media):
        for fs in self.formsets:
            media = media + fs.media
        if self.formsets:
            media = media + self.vendor(
                'xadmin.plugin.formset.js', 'xadmin.plugin.formset.css')
        return media

    def _get_detail_formset_instance(self, inline):
        formset = inline.instance_form(extra=0, max_num=0, can_delete=0)
        formset.detail_page = True
        if True:
            replace_field_to_value(formset.helper.layout, inline)
            model = inline.model
            opts = model._meta
            fake_admin_class = type(str('%s%sFakeAdmin' % (opts.app_label, opts.module_name)), (object, ), {'model': model})
            for form in formset.forms:
                instance = form.instance
                if instance.pk:
                    form.detail = self.get_view(
                        DetailAdminUtil, fake_admin_class, instance)
        return formset

class DetailAdminUtil(DetailAdminView):

    def init_request(self, obj):
        self.obj = obj
        self.org_obj = obj


class DetailInlineFormsetPlugin(InlineFormsetPlugin):

    def get_model_form(self, form, **kwargs):
        self.formsets = [self._get_detail_formset_instance(
            inline) for inline in self.inline_instances]
        return form

site.register_plugin(InlineFormsetPlugin, ModelFormAdminView)
site.register_plugin(DetailInlineFormsetPlugin, DetailAdminView)

########NEW FILE########
__FILENAME__ = language

from django.conf import settings
from django.template import loader, RequestContext

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, CommAdminView


class SetLangNavPlugin(BaseAdminPlugin):

    def block_top_navmenu(self, context, nodes):
        nodes.append(
            loader.render_to_string('xadmin/blocks/comm.top.setlang.html', {
                'redirect_to': self.request.get_full_path(),
            }, context_instance=RequestContext(self.request)))

if settings.LANGUAGES and 'django.middleware.locale.LocaleMiddleware' in settings.MIDDLEWARE_CLASSES:
    site.register_plugin(SetLangNavPlugin, CommAdminView)
    site.register_view(r'^i18n/', lambda site: 'django.conf.urls.i18n', 'i18n')

########NEW FILE########
__FILENAME__ = layout
# coding=utf-8
from django.template import loader
from django.utils.translation import ugettext_lazy as _

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView
from xadmin.util import label_for_field

LAYOUT_VAR = '_layout'

DEFAULT_LAYOUTS = {
    'table': {
        'key': 'table',
        'icon': 'fa fa-table',
        'name': _(u'Table'),
        'template': 'views/model_list.html',
    },
    'thumbnails': {
        'key': 'thumbnails',
        'icon': 'fa fa-th-large',
        'name': _(u'Thumbnails'),
        'template': 'grids/thumbnails.html',
    },
}


class GridLayoutPlugin(BaseAdminPlugin):

    grid_layouts = []

    _active_layouts = []
    _current_layout = None
    _current_icon = 'table'

    def get_layout(self, l):
        item = (type(l) is dict) and l or DEFAULT_LAYOUTS[l]
        return dict({'url': self.admin_view.get_query_string({LAYOUT_VAR: item['key']}), 'selected': False}, **item)

    def init_request(self, *args, **kwargs):
        active = bool(self.request.method == 'GET' and self.grid_layouts)
        if active:
            layouts = (type(self.grid_layouts) in (list, tuple)) and self.grid_layouts or (self.grid_layouts,)
            self._active_layouts = [self.get_layout(l) for l in layouts]
            self._current_layout = self.request.GET.get(LAYOUT_VAR, self._active_layouts[0]['key'])
            for layout in self._active_layouts:
                if self._current_layout == layout['key']:
                    self._current_icon = layout['icon']
                    layout['selected'] = True
                    self.admin_view.object_list_template = self.admin_view.get_template_list(layout['template'])
        return active

    def result_item(self, item, obj, field_name, row):
        if self._current_layout == 'thumbnails':
            if getattr(item.attr, 'is_column', True):
                item.field_label = label_for_field(
                    field_name, self.model,
                    model_admin=self.admin_view,
                    return_attr=False
                )
            if getattr(item.attr, 'thumbnail_img', False):
                setattr(item, 'thumbnail_hidden', True)
                row['thumbnail_img'] = item
            elif item.is_display_link:
                setattr(item, 'thumbnail_hidden', True)
                row['thumbnail_label'] = item

        return item

    # Block Views
    def block_top_toolbar(self, context, nodes):
        if len(self._active_layouts) > 1:
            context.update({
                'layouts': self._active_layouts,
                'current_icon': self._current_icon,
            })
            nodes.append(loader.render_to_string('xadmin/blocks/model_list.top_toolbar.layouts.html', context_instance=context))


site.register_plugin(GridLayoutPlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = mobile
#coding:utf-8
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, CommAdminView


class MobilePlugin(BaseAdminPlugin):

    def _test_mobile(self):
        try:
            return self.request.META['HTTP_USER_AGENT'].find('Android') >= 0 or \
                self.request.META['HTTP_USER_AGENT'].find('iPhone') >= 0
        except Exception:
            return False

    def init_request(self, *args, **kwargs):
        return self._test_mobile()

    def get_context(self, context):
        #context['base_template'] = 'xadmin/base_mobile.html'
        context['is_mob'] = True
        return context

    # Media
    # def get_media(self, media):
    #     return media + self.vendor('xadmin.mobile.css', )

    def block_extrahead(self, context, nodes):
        nodes.append('<script>window.__admin_ismobile__ = true;</script>')

site.register_plugin(MobilePlugin, CommAdminView)

########NEW FILE########
__FILENAME__ = multiselect
#coding:utf-8
from itertools import chain

import xadmin
from django import forms
from django.db.models import ManyToManyField
from django.forms.util import flatatt
from django.template import loader
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from xadmin.util import vendor
from xadmin.views import BaseAdminPlugin, ModelFormAdminView


class SelectMultipleTransfer(forms.SelectMultiple):

    @property
    def media(self):
        return vendor('xadmin.widget.select-transfer.js', 'xadmin.widget.select-transfer.css')

    def __init__(self, verbose_name, is_stacked, attrs=None, choices=()):
        self.verbose_name = verbose_name
        self.is_stacked = is_stacked
        super(SelectMultipleTransfer, self).__init__(attrs, choices)

    def render_opt(self, selected_choices, option_value, option_label):
        option_value = force_unicode(option_value)
        return u'<option value="%s">%s</option>' % (
            escape(option_value), conditional_escape(force_unicode(option_label))), bool(option_value in selected_choices)

    def render(self, name, value, attrs=None, choices=()):
        if attrs is None:
            attrs = {}
        attrs['class'] = ''
        if self.is_stacked:
            attrs['class'] += 'stacked'
        if value is None:
            value = []
        final_attrs = self.build_attrs(attrs, name=name)

        selected_choices = set(force_unicode(v) for v in value)
        available_output = []
        chosen_output = []

        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                available_output.append(u'<optgroup label="%s">' %
                                        escape(force_unicode(option_value)))
                for option in option_label:
                    output, selected = self.render_opt(
                        selected_choices, *option)
                    if selected:
                        chosen_output.append(output)
                    else:
                        available_output.append(output)
                available_output.append(u'</optgroup>')
            else:
                output, selected = self.render_opt(
                    selected_choices, option_value, option_label)
                if selected:
                    chosen_output.append(output)
                else:
                    available_output.append(output)

        context = {
            'verbose_name': self.verbose_name,
            'attrs': attrs,
            'field_id': attrs['id'],
            'flatatts': flatatt(final_attrs),
            'available_options': u'\n'.join(available_output),
            'chosen_options': u'\n'.join(chosen_output),
        }
        return mark_safe(loader.render_to_string('xadmin/forms/transfer.html', context))


class SelectMultipleDropdown(forms.SelectMultiple):

    @property
    def media(self):
        return vendor('multiselect.js', 'multiselect.css', 'xadmin.widget.multiselect.js')

    def render(self, name, value, attrs=None, choices=()):
        if attrs is None:
            attrs = {}
        attrs['class'] = 'selectmultiple selectdropdown'
        return super(SelectMultipleDropdown, self).render(name, value, attrs, choices)


class M2MSelectPlugin(BaseAdminPlugin):

    def init_request(self, *args, **kwargs):
        return hasattr(self.admin_view, 'style_fields') and \
            (
                'm2m_transfer' in self.admin_view.style_fields.values() or
                'm2m_dropdown' in self.admin_view.style_fields.values()
            )

    def get_field_style(self, attrs, db_field, style, **kwargs):
        if style == 'm2m_transfer' and isinstance(db_field, ManyToManyField):
            return {'widget': SelectMultipleTransfer(db_field.verbose_name, False), 'help_text': ''}
        if style == 'm2m_dropdown' and isinstance(db_field, ManyToManyField):
            return {'widget': SelectMultipleDropdown, 'help_text': ''}
        return attrs


xadmin.site.register_plugin(M2MSelectPlugin, ModelFormAdminView)

########NEW FILE########
__FILENAME__ = passwords
# coding=utf-8
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import password_reset_confirm
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _

from xadmin.sites import site
from xadmin.views.base import BaseAdminPlugin, BaseAdminView, csrf_protect_m
from xadmin.views.website import LoginView


class ResetPasswordSendView(BaseAdminView):

    need_site_permission = False

    password_reset_form = PasswordResetForm
    password_reset_template = 'xadmin/auth/password_reset/form.html'
    password_reset_done_template = 'xadmin/auth/password_reset/done.html'
    password_reset_token_generator = default_token_generator

    password_reset_from_email = None
    password_reset_email_template = 'xadmin/auth/password_reset/email.html'
    password_reset_subject_template = None

    def get(self, request, *args, **kwargs):
        context = super(ResetPasswordSendView, self).get_context()
        context['form'] = kwargs.get('form', self.password_reset_form())

        return TemplateResponse(request, self.password_reset_template, context,
                                current_app=self.admin_site.name)

    @csrf_protect_m
    def post(self, request, *args, **kwargs):
        form = self.password_reset_form(request.POST)

        if form.is_valid():
            opts = {
                'use_https': request.is_secure(),
                'token_generator': self.password_reset_token_generator,
                'email_template_name': self.password_reset_email_template,
                'request': request,
                'domain_override': request.get_host()
            }

            if self.password_reset_from_email:
                opts['from_email'] = self.password_reset_from_email
            if self.password_reset_subject_template:
                opts['subject_template_name'] = self.password_reset_subject_template

            form.save(**opts)
            context = super(ResetPasswordSendView, self).get_context()
            return TemplateResponse(request, self.password_reset_done_template, context,
                                current_app=self.admin_site.name)
        else:
            return self.get(request, form=form)

site.register_view(r'^xadmin/password_reset/$', ResetPasswordSendView, name='xadmin_password_reset')

class ResetLinkPlugin(BaseAdminPlugin):

    def block_form_bottom(self, context, nodes):
        reset_link = self.get_admin_url('xadmin_password_reset')
        return '<div class="text-info" style="margin-top:15px;"><a href="%s"><i class="fa fa-question-sign"></i> %s</a></div>' % (reset_link, _('Forgotten your password or username?'))

site.register_plugin(ResetLinkPlugin, LoginView)


class ResetPasswordComfirmView(BaseAdminView):

    need_site_permission = False

    password_reset_set_form = SetPasswordForm
    password_reset_confirm_template = 'xadmin/auth/password_reset/confirm.html'
    password_reset_token_generator = default_token_generator

    def do_view(self, request, uidb36, token, *args, **kwargs):
        context = super(ResetPasswordComfirmView, self).get_context()
        return password_reset_confirm(request, uidb36, token,
                   template_name=self.password_reset_confirm_template,
                   token_generator=self.password_reset_token_generator,
                   set_password_form=self.password_reset_set_form,
                   post_reset_redirect=self.get_admin_url('xadmin_password_reset_complete'),
                   current_app=self.admin_site.name, extra_context=context)

    def get(self, request, uidb36, token, *args, **kwargs):
        return self.do_view(request, uidb36, token)

    def post(self, request, uidb36, token, *args, **kwargs):
        return self.do_view(request, uidb36, token)

    def get_media(self):
        return super(ResetPasswordComfirmView, self).get_media() + \
            self.vendor('xadmin.page.form.js', 'xadmin.form.css')

site.register_view(r'^xadmin/password_reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
    ResetPasswordComfirmView, name='xadmin_password_reset_confirm')


class ResetPasswordCompleteView(BaseAdminView):

    need_site_permission = False

    password_reset_complete_template = 'xadmin/auth/password_reset/complete.html'

    def get(self, request, *args, **kwargs):
        context = super(ResetPasswordCompleteView, self).get_context()
        context['login_url'] = self.get_admin_url('index')

        return TemplateResponse(request, self.password_reset_complete_template, context,
                                current_app=self.admin_site.name)

site.register_view(r'^xadmin/password_reset/complete/$', ResetPasswordCompleteView, name='xadmin_password_reset_complete')


########NEW FILE########
__FILENAME__ = portal
#coding:utf-8
from xadmin.sites import site
from xadmin.models import UserSettings
from xadmin.views import BaseAdminPlugin, ModelFormAdminView, DetailAdminView
from xadmin.layout import Fieldset, Column


class BasePortalPlugin(BaseAdminPlugin):

    # Media
    def get_media(self, media):
        return media + self.vendor('xadmin.plugin.portal.js')


def get_layout_objects(layout, clz, objects):
    for i, layout_object in enumerate(layout.fields):
        if layout_object.__class__ is clz or issubclass(layout_object.__class__, clz):
            objects.append(layout_object)
        elif hasattr(layout_object, 'get_field_names'):
            get_layout_objects(layout_object, clz, objects)


class ModelFormPlugin(BasePortalPlugin):

    def _portal_key(self):
        return '%s_%s_editform_portal' % (self.opts.app_label, self.opts.module_name)

    def get_form_helper(self, helper):
        cs = []
        layout = helper.layout
        get_layout_objects(layout, Column, cs)
        for i, c in enumerate(cs):
            if not getattr(c, 'css_id', None):
                c.css_id = 'column-%d' % i

        # make fieldset index
        fs = []
        get_layout_objects(layout, Fieldset, fs)
        fs_map = {}
        for i, f in enumerate(fs):
            if not getattr(f, 'css_id', None):
                f.css_id = 'box-%d' % i
            fs_map[f.css_id] = f

        try:
            layout_pos = UserSettings.objects.get(
                user=self.user, key=self._portal_key()).value
            layout_cs = layout_pos.split('|')
            for i, c in enumerate(cs):
                c.fields = [fs_map.pop(j) for j in layout_cs[i].split(
                    ',') if j in fs_map] if len(layout_cs) > i else []
            if fs_map and cs:
                cs[0].fields.extend(fs_map.values())
        except Exception:
            pass

        return helper

    def block_form_top(self, context, node):
        # put portal key and submit url to page
        return "<input type='hidden' id='_portal_key' value='%s' />" % self._portal_key()


class ModelDetailPlugin(ModelFormPlugin):

    def _portal_key(self):
        return '%s_%s_detail_portal' % (self.opts.app_label, self.opts.module_name)

    def block_after_fieldsets(self, context, node):
        # put portal key and submit url to page
        return "<input type='hidden' id='_portal_key' value='%s' />" % self._portal_key()

site.register_plugin(ModelFormPlugin, ModelFormAdminView)
site.register_plugin(ModelDetailPlugin, DetailAdminView)

########NEW FILE########
__FILENAME__ = quickfilter
'''
Created on Mar 26, 2014

@author: LAB_ADM
'''
from django.utils.translation import ugettext_lazy as _
from xadmin.filters import manager,MultiSelectFieldListFilter
from xadmin.plugins.filters import *

@manager.register
class QuickFilterMultiSelectFieldListFilter(MultiSelectFieldListFilter):
    """ Delegates the filter to the default filter and ors the results of each
     
    Lists the distinct values of each field as a checkbox
    Uses the default spec for each 
     
    """
    template = 'xadmin/filters/quickfilter.html'

class QuickFilterPlugin(BaseAdminPlugin):
    """ Add a filter menu to the left column of the page """
    list_quick_filter = () # these must be a subset of list_filter to work
    quickfilter = {} 
    search_fields = ()
    free_query_filter = True
    
    def init_request(self, *args, **kwargs):
        menu_style_accordian = hasattr(self.admin_view,'menu_style') and self.admin_view.menu_style == 'accordion'
        return bool(self.list_quick_filter) and not menu_style_accordian
    
    # Media
    def get_media(self, media):
        return media + self.vendor('xadmin.plugin.quickfilter.js','xadmin.plugin.quickfilter.css')
    
    def lookup_allowed(self, lookup, value):
        model = self.model
        # Check FKey lookups that are allowed, so that popups produced by
        # ForeignKeyRawIdWidget, on the basis of ForeignKey.limit_choices_to,
        # are allowed to work.
        for l in model._meta.related_fkey_lookups:
            for k, v in widgets.url_params_from_lookup_dict(l).items():
                if k == lookup and v == value:
                    return True
 
        parts = lookup.split(LOOKUP_SEP)
 
        # Last term in lookup is a query term (__exact, __startswith etc)
        # This term can be ignored.
        if len(parts) > 1 and parts[-1] in QUERY_TERMS:
            parts.pop()
 
        # Special case -- foo__id__exact and foo__id queries are implied
        # if foo has been specificially included in the lookup list; so
        # drop __id if it is the last part. However, first we need to find
        # the pk attribute name.
        rel_name = None
        for part in parts[:-1]:
            try:
                field, _, _, _ = model._meta.get_field_by_name(part)
            except FieldDoesNotExist:
                # Lookups on non-existants fields are ok, since they're ignored
                # later.
                return True
            if hasattr(field, 'rel'):
                model = field.rel.to
                rel_name = field.rel.get_related_field().name
            elif isinstance(field, RelatedObject):
                model = field.model
                rel_name = model._meta.pk.name
            else:
                rel_name = None
        if rel_name and len(parts) > 1 and parts[-1] == rel_name:
            parts.pop()
 
        if len(parts) == 1:
            return True
        clean_lookup = LOOKUP_SEP.join(parts)
        return clean_lookup in self.list_quick_filter
 
    def get_list_queryset(self, queryset):
        lookup_params = dict([(smart_str(k)[len(FILTER_PREFIX):], v) for k, v in self.admin_view.params.items() if smart_str(k).startswith(FILTER_PREFIX) and v != ''])
        for p_key, p_val in lookup_params.iteritems():
            if p_val == "False":
                lookup_params[p_key] = False
        use_distinct = False
        
        if not hasattr(self.admin_view,'quickfilter'):
            self.admin_view.quickfilter = {}
 
        # for clean filters
        self.admin_view.quickfilter['has_query_param'] = bool(lookup_params)
        self.admin_view.quickfilter['clean_query_url'] = self.admin_view.get_query_string(remove=[k for k in self.request.GET.keys() if k.startswith(FILTER_PREFIX)])
 
        # Normalize the types of keys
        if not self.free_query_filter:
            for key, value in lookup_params.items():
                if not self.lookup_allowed(key, value):
                    raise SuspiciousOperation("Filtering by %s not allowed" % key)
 
        self.filter_specs = []
        if self.list_quick_filter:
            for list_quick_filter in self.list_quick_filter:
                field_path = None
                field_order_by = None
                field_limit = None
                field_parts = []
                sort_key = None 
                cache_config = None
                
                if type(list_quick_filter)==dict and 'field' in list_quick_filter:
                    field = list_quick_filter['field']
                    if 'order_by' in list_quick_filter:
                        field_order_by = list_quick_filter['order_by']
                    if 'limit' in list_quick_filter:
                        field_limit = list_quick_filter['limit']
                    if 'sort' in list_quick_filter and callable(list_quick_filter['sort']):
                        sort_key = list_quick_filter['sort']
                    if 'cache' in list_quick_filter and type(list_quick_filter)==dict:
                        cache_config = list_quick_filter['cache']
                        
                else:        
                    field = list_quick_filter # This plugin only uses MultiselectFieldListFilter
                
                if not isinstance(field, models.Field):
                    field_path = field
                    field_parts = get_fields_from_path(self.model, field_path)
                    field = field_parts[-1]
                spec = QuickFilterMultiSelectFieldListFilter(field, self.request, lookup_params,self.model, self.admin_view, field_path=field_path,field_order_by=field_order_by,field_limit=field_limit,sort_key=sort_key,cache_config=cache_config)
                 
                if len(field_parts)>1:
                    spec.title = "%s %s"%(field_parts[-2].name,spec.title) 
                 
                # Check if we need to use distinct()
                use_distinct = True#(use_distinct orlookup_needs_distinct(self.opts, field_path))
                if spec and spec.has_output():
                    try:
                        new_qs = spec.do_filte(queryset)
                    except ValidationError, e:
                        new_qs = None
                        self.admin_view.message_user(_("<b>Filtering error:</b> %s") % e.messages[0], 'error')
                    if new_qs is not None:
                        queryset = new_qs
 
                    self.filter_specs.append(spec)
 
        self.has_filters = bool(self.filter_specs)
        self.admin_view.quickfilter['filter_specs'] = self.filter_specs
        self.admin_view.quickfilter['used_filter_num'] = len(filter(lambda f: f.is_used, self.filter_specs))
 
        if use_distinct:
            return queryset.distinct()
        else:
            return queryset
    
    def block_left_navbar(self, context, nodes):
        nodes.append(loader.render_to_string('xadmin/blocks/modal_list.left_navbar.quickfilter.html',context))
        
site.register_plugin(QuickFilterPlugin, ListAdminView)
########NEW FILE########
__FILENAME__ = quickform
from django.db import models
from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.forms.models import modelform_factory
import copy
from xadmin.sites import site
from xadmin.util import get_model_from_relation, vendor
from xadmin.views import BaseAdminPlugin, ModelFormAdminView
from xadmin.layout import Layout


class QuickFormPlugin(BaseAdminPlugin):

    def init_request(self, *args, **kwargs):
        if self.request.method == 'GET' and self.request.is_ajax() or self.request.GET.get('_ajax'):
            self.admin_view.add_form_template = 'xadmin/views/quick_form.html'
            self.admin_view.change_form_template = 'xadmin/views/quick_form.html'
            return True
        return False

    def get_model_form(self, __, **kwargs):
        if '_field' in self.request.GET:
            defaults = {
                "form": self.admin_view.form,
                "fields": self.request.GET['_field'].split(','),
                "formfield_callback": self.admin_view.formfield_for_dbfield,
            }
            return modelform_factory(self.model, **defaults)
        return __()

    def get_form_layout(self, __):
        if '_field' in self.request.GET:
            return Layout(*self.request.GET['_field'].split(','))
        return __()

    def get_context(self, context):
        context['form_url'] = self.request.path
        return context


class RelatedFieldWidgetWrapper(forms.Widget):
    """
    This class is a wrapper to a given widget to add the add icon for the
    admin interface.
    """
    def __init__(self, widget, rel, add_url, rel_add_url):
        self.is_hidden = widget.is_hidden
        self.needs_multipart_form = widget.needs_multipart_form
        self.attrs = widget.attrs
        self.choices = widget.choices
        self.is_required = widget.is_required
        self.widget = widget
        self.rel = rel

        self.add_url = add_url
        self.rel_add_url = rel_add_url

    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        obj.widget = copy.deepcopy(self.widget, memo)
        obj.attrs = self.widget.attrs
        memo[id(self)] = obj
        return obj

    @property
    def media(self):
        media = self.widget.media + vendor('xadmin.plugin.quick-form.js')
        return media

    def render(self, name, value, *args, **kwargs):
        self.widget.choices = self.choices
        output = []
        if self.add_url:
            output.append(u'<a href="%s" title="%s" class="btn btn-primary btn-sm btn-ajax pull-right" data-for-id="id_%s" data-refresh-url="%s"><i class="fa fa-plus"></i></a>'
                          % (
                              self.add_url, (_('Create New %s') % self.rel.to._meta.verbose_name), name,
                              "%s?_field=%s&%s=" % (self.rel_add_url, name, name)))
        output.extend(['<div class="control-wrap" id="id_%s_wrap_container">' % name,
                  self.widget.render(name, value, *args, **kwargs), '</div>'])
        return mark_safe(u''.join(output))

    def build_attrs(self, extra_attrs=None, **kwargs):
        "Helper function for building an attribute dictionary."
        self.attrs = self.widget.build_attrs(extra_attrs=None, **kwargs)
        return self.attrs

    def value_from_datadict(self, data, files, name):
        return self.widget.value_from_datadict(data, files, name)

    def id_for_label(self, id_):
        return self.widget.id_for_label(id_)


class QuickAddBtnPlugin(BaseAdminPlugin):

    def formfield_for_dbfield(self, formfield, db_field, **kwargs):
        if formfield and self.model in self.admin_site._registry and isinstance(db_field, (models.ForeignKey, models.ManyToManyField)):
            rel_model = get_model_from_relation(db_field)
            if rel_model in self.admin_site._registry and self.has_model_perm(rel_model, 'add'):
                add_url = self.get_model_url(rel_model, 'add')
                formfield.widget = RelatedFieldWidgetWrapper(
                    formfield.widget, db_field.rel, add_url, self.get_model_url(self.model, 'add'))
        return formfield

site.register_plugin(QuickFormPlugin, ModelFormAdminView)
site.register_plugin(QuickAddBtnPlugin, ModelFormAdminView)

########NEW FILE########
__FILENAME__ = refresh
# coding=utf-8
from django.template import loader

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView

REFRESH_VAR = '_refresh'


class RefreshPlugin(BaseAdminPlugin):

    refresh_times = []

    # Media
    def get_media(self, media):
        if self.refresh_times and self.request.GET.get(REFRESH_VAR):
            media = media + self.vendor('xadmin.plugin.refresh.js')
        return media

    # Block Views
    def block_top_toolbar(self, context, nodes):
        if self.refresh_times:
            current_refresh = self.request.GET.get(REFRESH_VAR)
            context.update({
                'has_refresh': bool(current_refresh),
                'clean_refresh_url': self.admin_view.get_query_string(remove=(REFRESH_VAR,)),
                'current_refresh': current_refresh,
                'refresh_times': [{
                    'time': r,
                    'url': self.admin_view.get_query_string({REFRESH_VAR: r}),
                    'selected': str(r) == current_refresh,
                } for r in self.refresh_times],
            })
            nodes.append(loader.render_to_string('xadmin/blocks/model_list.top_toolbar.refresh.html', context_instance=context))


site.register_plugin(RefreshPlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = relate
# coding=UTF-8
from django.core.urlresolvers import reverse
from django.utils.encoding import force_unicode
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
from django.db.models.sql.query import LOOKUP_SEP
from django.db.models.related import RelatedObject
from django.utils.translation import ugettext as _
from django.db import models

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView, CreateAdminView, UpdateAdminView, DeleteAdminView

RELATE_PREFIX = '_rel_'


class RelateMenuPlugin(BaseAdminPlugin):

    related_list = []
    use_related_menu = True

    def get_related_list(self):
        if hasattr(self, '_related_acts'):
            return self._related_acts

        _related_acts = []
        for r in self.opts.get_all_related_objects() + self.opts.get_all_related_many_to_many_objects():
            if self.related_list and (r.get_accessor_name() not in self.related_list):
                continue
            if r.model not in self.admin_site._registry.keys():
                continue
            has_view_perm = self.has_model_perm(r.model, 'view')
            has_add_perm = self.has_model_perm(r.model, 'add')
            if not (has_view_perm or has_add_perm):
                continue

            _related_acts.append((r, has_view_perm, has_add_perm))

        self._related_acts = _related_acts
        return self._related_acts

    def related_link(self, instance):
        links = []
        for r, view_perm, add_perm in self.get_related_list():
            label = r.opts.app_label
            model_name = r.opts.module_name
            f = r.field
            rel_name = f.rel.get_related_field().name

            verbose_name = force_unicode(r.opts.verbose_name)
            lookup_name = '%s__%s__exact' % (f.name, rel_name)

            link = ''.join(('<li class="with_menu_btn">',

                            '<a href="%s?%s=%s" title="%s"><i class="icon fa fa-th-list"></i> %s</a>' %
                          (
                            reverse('%s:%s_%s_changelist' % (
                                    self.admin_site.app_name, label, model_name)),
                            RELATE_PREFIX + lookup_name, str(instance.pk), verbose_name, verbose_name) if view_perm else
                            '<a><span class="text-muted"><i class="icon fa fa-blank"></i> %s</span></a>' % verbose_name,

                            '<a class="add_link dropdown-menu-btn" href="%s?%s=%s"><i class="icon fa fa-plus pull-right"></i></a>' %
                          (
                            reverse('%s:%s_%s_add' % (
                                    self.admin_site.app_name, label, model_name)),
                            RELATE_PREFIX + lookup_name, str(
                instance.pk)) if add_perm else "",

                '</li>'))
            links.append(link)
        ul_html = '<ul class="dropdown-menu" role="menu">%s</ul>' % ''.join(
            links)
        return '<div class="dropdown related_menu pull-right"><a title="%s" class="relate_menu dropdown-toggle" data-toggle="dropdown"><i class="icon fa fa-list"></i></a>%s</div>' % (_('Related Objects'), ul_html)
    related_link.short_description = '&nbsp;'
    related_link.allow_tags = True
    related_link.allow_export = False
    related_link.is_column = False

    def get_list_display(self, list_display):
        if self.use_related_menu and len(self.get_related_list()):
            list_display.append('related_link')
            self.admin_view.related_link = self.related_link
        return list_display


class RelateObject(object):

    def __init__(self, admin_view, lookup, value):
        self.admin_view = admin_view
        self.org_model = admin_view.model
        self.opts = admin_view.opts
        self.lookup = lookup
        self.value = value

        parts = lookup.split(LOOKUP_SEP)
        field = self.opts.get_field_by_name(parts[0])[0]

        if not hasattr(field, 'rel') and not isinstance(field, RelatedObject):
            raise Exception(u'Relate Lookup field must a related field')

        if hasattr(field, 'rel'):
            self.to_model = field.rel.to
            self.rel_name = field.rel.get_related_field().name
            self.is_m2m = isinstance(field.rel, models.ManyToManyRel)
        else:
            self.to_model = field.model
            self.rel_name = self.to_model._meta.pk.name
            self.is_m2m = False

        to_qs = self.to_model._default_manager.get_query_set()
        self.to_objs = to_qs.filter(**{self.rel_name: value}).all()

        self.field = field

    def filter(self, queryset):
        return queryset.filter(**{self.lookup: self.value})

    def get_brand_name(self):
        if len(self.to_objs) == 1:
            to_model_name = str(self.to_objs[0])
        else:
            to_model_name = force_unicode(self.to_model._meta.verbose_name)

        return mark_safe(u"<span class='rel-brand'>%s <i class='fa fa-caret-right'></i></span> %s" % (to_model_name, force_unicode(self.opts.verbose_name_plural)))


class BaseRelateDisplayPlugin(BaseAdminPlugin):

    def init_request(self, *args, **kwargs):
        self.relate_obj = None
        for k, v in self.request.REQUEST.items():
            if smart_str(k).startswith(RELATE_PREFIX):
                self.relate_obj = RelateObject(
                    self.admin_view, smart_str(k)[len(RELATE_PREFIX):], v)
                break
        return bool(self.relate_obj)

    def _get_relate_params(self):
        return RELATE_PREFIX + self.relate_obj.lookup, self.relate_obj.value

    def _get_input(self):
        return '<input type="hidden" name="%s" value="%s" />' % self._get_relate_params()

    def _get_url(self, url):
        return url + ('&' if url.find('?') > 0 else '?') + ('%s=%s' % self._get_relate_params())


class ListRelateDisplayPlugin(BaseRelateDisplayPlugin):

    def get_list_queryset(self, queryset):
        if self.relate_obj:
            queryset = self.relate_obj.filter(queryset)
        return queryset

    def url_for_result(self, url, result):
        return self._get_url(url)

    def get_context(self, context):
        context['brand_name'] = self.relate_obj.get_brand_name()
        context['rel_objs'] = self.relate_obj.to_objs
        if 'add_url' in context:
            context['add_url'] = self._get_url(context['add_url'])
        return context

    def get_list_display(self, list_display):
        if not self.relate_obj.is_m2m:
            try:
                list_display.remove(self.relate_obj.field.name)
            except Exception:
                pass
        return list_display


class EditRelateDisplayPlugin(BaseRelateDisplayPlugin):

    def get_form_datas(self, datas):
        if self.admin_view.org_obj is None and self.admin_view.request_method == 'get':
            datas['initial'][
                self.relate_obj.field.name] = self.relate_obj.value
        return datas

    def post_response(self, response):
        if isinstance(response, basestring) and response != self.get_admin_url('index'):
            return self._get_url(response)
        return response

    def get_context(self, context):
        if 'delete_url' in context:
            context['delete_url'] = self._get_url(context['delete_url'])
        return context

    def block_after_fieldsets(self, context, nodes):
        return self._get_input()


class DeleteRelateDisplayPlugin(BaseRelateDisplayPlugin):

    def post_response(self, response):
        if isinstance(response, basestring) and response != self.get_admin_url('index'):
            return self._get_url(response)
        return response

    def block_form_fields(self, context, nodes):
        return self._get_input()

site.register_plugin(RelateMenuPlugin, ListAdminView)
site.register_plugin(ListRelateDisplayPlugin, ListAdminView)
site.register_plugin(EditRelateDisplayPlugin, CreateAdminView)
site.register_plugin(EditRelateDisplayPlugin, UpdateAdminView)
site.register_plugin(DeleteRelateDisplayPlugin, DeleteAdminView)

########NEW FILE########
__FILENAME__ = relfield
from django.db import models
from django.utils.html import escape, format_html
from django.utils.text import Truncator
from django.utils.translation import ugettext as _
from django import forms
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ModelFormAdminView
from xadmin.util import vendor


class ForeignKeySearchWidget(forms.TextInput):

    def __init__(self, rel, admin_view, attrs=None, using=None):
        self.rel = rel
        self.admin_view = admin_view
        self.db = using
        super(ForeignKeySearchWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        to_opts = self.rel.to._meta
        if attrs is None:
            attrs = {}
        if "class" not in attrs:
            attrs['class'] = 'select-search'
        else:
            attrs['class'] = attrs['class'] + ' select-search'
        attrs['data-search-url'] = self.admin_view.get_admin_url(
            '%s_%s_changelist' % (to_opts.app_label, to_opts.module_name))
        attrs['data-placeholder'] = _('Search %s') % to_opts.verbose_name
        attrs['data-choices'] = '?'
        if self.rel.limit_choices_to:
            for i in list(self.rel.limit_choices_to):
                attrs['data-choices'] += "&_p_%s=%s" % (i, self.rel.limit_choices_to[i])
            attrs['data-choices'] = format_html(attrs['data-choices'])
        if value:
            attrs['data-label'] = self.label_for_value(value)

        return super(ForeignKeySearchWidget, self).render(name, value, attrs)

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.to._default_manager.using(
                self.db).get(**{key: value})
            return '%s' % escape(Truncator(obj).words(14, truncate='...'))
        except (ValueError, self.rel.to.DoesNotExist):
            return ""

    @property
    def media(self):
        return vendor('select.js', 'select.css', 'xadmin.widget.select.js')


class RelateFieldPlugin(BaseAdminPlugin):

    def get_field_style(self, attrs, db_field, style, **kwargs):
        # search able fk field
        if style == 'fk-ajax' and isinstance(db_field, models.ForeignKey):
            if (db_field.rel.to in self.admin_view.admin_site._registry) and \
                    self.has_model_perm(db_field.rel.to, 'view'):
                db = kwargs.get('using')
                return dict(attrs or {}, widget=ForeignKeySearchWidget(db_field.rel, self.admin_view, using=db))
        return attrs

site.register_plugin(RelateFieldPlugin, ModelFormAdminView)

########NEW FILE########
__FILENAME__ = sitemenu

from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, CommAdminView

BUILDIN_STYLES = {
    'default': 'xadmin/includes/sitemenu_default.html',
    'accordion': 'xadmin/includes/sitemenu_accordion.html',
}


class SiteMenuStylePlugin(BaseAdminPlugin):

    menu_style = None

    def init_request(self, *args, **kwargs):
        return bool(self.menu_style) and self.menu_style in BUILDIN_STYLES

    def get_context(self, context):
        context['menu_template'] = BUILDIN_STYLES[self.menu_style]
        return context

site.register_plugin(SiteMenuStylePlugin, CommAdminView)

########NEW FILE########
__FILENAME__ = sortable
#coding:utf-8
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ListAdminView

SORTBY_VAR = '_sort_by'


class SortablePlugin(BaseAdminPlugin):

    sortable_fields = ['sort']

    # Media
    def get_media(self, media):
        if self.sortable_fields and self.request.GET.get(SORTBY_VAR):
            media = media + self.vendor('xadmin.plugin.sortable.js')
        return media

    # Block Views
    def block_top_toolbar(self, context, nodes):
        if self.sortable_fields:
            pass
            # current_refresh = self.request.GET.get(REFRESH_VAR)
            # context.update({
            #     'has_refresh': bool(current_refresh),
            #     'clean_refresh_url': self.admin_view.get_query_string(remove=(REFRESH_VAR,)),
            #     'current_refresh': current_refresh,
            #     'refresh_times': [{
            #         'time': r,
            #         'url': self.admin_view.get_query_string({REFRESH_VAR: r}),
            #         'selected': str(r) == current_refresh,
            #     } for r in self.refresh_times],
            # })
            # nodes.append(loader.render_to_string('xadmin/blocks/refresh.html', context_instance=context))


site.register_plugin(SortablePlugin, ListAdminView)

########NEW FILE########
__FILENAME__ = themes
#coding:utf-8
import urllib
from django.template import loader
from django.core.cache import cache
from django.utils.translation import ugettext as _
from xadmin.sites import site
from xadmin.models import UserSettings
from xadmin.views import BaseAdminPlugin, BaseAdminView
from xadmin.util import static, json

THEME_CACHE_KEY = 'xadmin_themes'


class ThemePlugin(BaseAdminPlugin):

    enable_themes = False
    # {'name': 'Blank Theme', 'description': '...', 'css': 'http://...', 'thumbnail': '...'}
    user_themes = None
    use_bootswatch = False
    default_theme = static('xadmin/css/themes/bootstrap-xadmin.css')
    bootstrap2_theme = static('xadmin/css/themes/bootstrap-theme.css')

    def init_request(self, *args, **kwargs):
        return self.enable_themes

    def _get_theme(self):
        if self.user:
            try:
                return UserSettings.objects.get(user=self.user, key="site-theme").value
            except Exception:
                pass
        if '_theme' in self.request.COOKIES:
            return urllib.unquote(self.request.COOKIES['_theme'])
        return self.default_theme

    def get_context(self, context):
        context['site_theme'] = self._get_theme()
        return context

    # Media
    def get_media(self, media):
        return media + self.vendor('jquery-ui-effect.js', 'xadmin.plugin.themes.js')

    # Block Views
    def block_top_navmenu(self, context, nodes):

        themes = [{'name': _(u"Default"), 'description': _(
            u"Default bootstrap theme"), 'css': self.default_theme},
            {'name': _(u"Bootstrap2"), 'description': _(u"Bootstrap 2.x theme"),
            'css': self.bootstrap2_theme}]
        select_css = context.get('site_theme', self.default_theme)

        if self.user_themes:
            themes.extend(self.user_themes)

        if self.use_bootswatch:
            ex_themes = cache.get(THEME_CACHE_KEY)
            if ex_themes:
                themes.extend(json.loads(ex_themes))
            else:
                ex_themes = []
                try:
                    watch_themes = json.loads(urllib.urlopen(
                        'http://api.bootswatch.com/3/').read())['themes']
                    ex_themes.extend([
                        {'name': t['name'], 'description': t['description'],
                            'css': t['cssMin'], 'thumbnail': t['thumbnail']}
                        for t in watch_themes])
                except Exception:
                    pass

                cache.set(THEME_CACHE_KEY, json.dumps(ex_themes), 24 * 3600)
                themes.extend(ex_themes)

        nodes.append(loader.render_to_string('xadmin/blocks/comm.top.theme.html', {'themes': themes, 'select_css': select_css}))


site.register_plugin(ThemePlugin, BaseAdminView)

########NEW FILE########
__FILENAME__ = topnav

from django.template import loader
from django.utils.text import capfirst
from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.translation import ugettext as _

from xadmin.sites import site
from xadmin.filters import SEARCH_VAR
from xadmin.views import BaseAdminPlugin, CommAdminView


class TopNavPlugin(BaseAdminPlugin):

    global_search_models = None
    global_add_models = None

    def get_context(self, context):
        return context

    # Block Views
    def block_top_navbar(self, context, nodes):
        search_models = []

        site_name = self.admin_site.name
        if self.global_search_models == None:
            models = self.admin_site._registry.keys()
        else:
            models = self.global_search_models

        for model in models:
            app_label = model._meta.app_label

            if self.has_model_perm(model, "view"):
                info = (app_label, model._meta.module_name)
                if getattr(self.admin_site._registry[model], 'search_fields', None):
                    try:
                        search_models.append({
                            'title': _('Search %s') % capfirst(model._meta.verbose_name_plural),
                            'url': reverse('xadmin:%s_%s_changelist' % info, current_app=site_name),
                            'model': model
                        })
                    except NoReverseMatch:
                        pass

        nodes.append(loader.render_to_string('xadmin/blocks/comm.top.topnav.html', {'search_models': search_models, 'search_name': SEARCH_VAR}))

    def block_top_navmenu(self, context, nodes):
        add_models = []

        site_name = self.admin_site.name

        if self.global_add_models == None:
            models = self.admin_site._registry.keys()
        else:
            models = self.global_add_models
        for model in models:
            app_label = model._meta.app_label

            if self.has_model_perm(model, "add"):
                info = (app_label, model._meta.module_name)
                try:
                    add_models.append({
                        'title': _('Add %s') % capfirst(model._meta.verbose_name),
                        'url': reverse('xadmin:%s_%s_add' % info, current_app=site_name),
                        'model': model
                    })
                except NoReverseMatch:
                    pass

        nodes.append(
            loader.render_to_string('xadmin/blocks/comm.top.topnav.html', {'add_models': add_models}))


site.register_plugin(TopNavPlugin, CommAdminView)

########NEW FILE########
__FILENAME__ = wizard
import re
from django import forms
from django.db import models
from django.template import loader
from django.contrib.formtools.wizard.storage import get_storage
from django.contrib.formtools.wizard.forms import ManagementForm
from django.contrib.formtools.wizard.views import StepsHelper
from django.utils.datastructures import SortedDict
from django.forms import ValidationError
from django.forms.models import modelform_factory
from xadmin.sites import site
from xadmin.views import BaseAdminPlugin, ModelFormAdminView


def normalize_name(name):
    new = re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', '_\\1', name)
    return new.lower().strip('_')


class WizardFormPlugin(BaseAdminPlugin):

    wizard_form_list = None
    wizard_for_update = False

    storage_name = 'django.contrib.formtools.wizard.storage.session.SessionStorage'
    form_list = None
    initial_dict = None
    instance_dict = None
    condition_dict = None
    file_storage = None

    def _get_form_prefix(self, step=None):
        if step is None:
            step = self.steps.current
        return 'step_%d' % self.get_form_list().keys().index(step)

    def get_form_list(self):
        if not hasattr(self, '_form_list'):
            init_form_list = SortedDict()

            assert len(
                self.wizard_form_list) > 0, 'at least one form is needed'

            for i, form in enumerate(self.wizard_form_list):
                init_form_list[unicode(form[0])] = form[1]

            self._form_list = init_form_list

        return self._form_list

    # Plugin replace methods
    def init_request(self, *args, **kwargs):
        if self.request.is_ajax() or ("_ajax" in self.request.GET) or not hasattr(self.request, 'session') or (args and not self.wizard_for_update):
            #update view
            return False
        return bool(self.wizard_form_list)

    def prepare_form(self, __):
        # init storage and step helper
        self.prefix = normalize_name(self.__class__.__name__)
        self.storage = get_storage(
            self.storage_name, self.prefix, self.request,
            getattr(self, 'file_storage', None))
        self.steps = StepsHelper(self)
        self.wizard_goto_step = False

        if self.request.method == 'GET':
            self.storage.reset()
            self.storage.current_step = self.steps.first

            self.admin_view.model_form = self.get_step_form()
        else:
            # Look for a wizard_goto_step element in the posted data which
            # contains a valid step name. If one was found, render the requested
            # form. (This makes stepping back a lot easier).
            wizard_goto_step = self.request.POST.get('wizard_goto_step', None)
            if wizard_goto_step and int(wizard_goto_step) < len(self.get_form_list()):
                self.storage.current_step = self.get_form_list(
                ).keys()[int(wizard_goto_step)]
                self.admin_view.model_form = self.get_step_form()
                self.wizard_goto_step = True
                return

            # Check if form was refreshed
            management_form = ManagementForm(
                self.request.POST, prefix=self.prefix)
            if not management_form.is_valid():
                raise ValidationError(
                    'ManagementForm data is missing or has been tampered.')

            form_current_step = management_form.cleaned_data['current_step']
            if (form_current_step != self.steps.current and
                    self.storage.current_step is not None):
                # form refreshed, change current step
                self.storage.current_step = form_current_step

            # get the form for the current step
            self.admin_view.model_form = self.get_step_form()

    def get_form_layout(self, __):
        attrs = self.get_form_list()[self.steps.current]
        if type(attrs) is dict and 'layout' in attrs:
            self.admin_view.form_layout = attrs['layout']
        else:
            self.admin_view.form_layout = None
        return __()

    def get_step_form(self, step=None):
        if step is None:
            step = self.steps.current
        attrs = self.get_form_list()[step]
        if type(attrs) in (list, tuple):
            return modelform_factory(self.model, form=forms.ModelForm,
                                     fields=attrs, formfield_callback=self.admin_view.formfield_for_dbfield)
        elif type(attrs) is dict:
            if attrs.get('fields', None):
                return modelform_factory(self.model, form=forms.ModelForm,
                                         fields=attrs['fields'], formfield_callback=self.admin_view.formfield_for_dbfield)
            if attrs.get('callback', None):
                callback = attrs['callback']
                if callable(callback):
                    return callback(self)
                elif hasattr(self.admin_view, str(callback)):
                    return getattr(self.admin_view, str(callback))(self)
        elif issubclass(attrs, forms.BaseForm):
            return attrs
        return None

    def get_step_form_obj(self, step=None):
        if step is None:
            step = self.steps.current
        form = self.get_step_form(step)
        return form(prefix=self._get_form_prefix(step),
                    data=self.storage.get_step_data(step),
                    files=self.storage.get_step_files(step))

    def get_form_datas(self, datas):
        datas['prefix'] = self._get_form_prefix()
        if self.request.method == 'POST' and self.wizard_goto_step:
            datas.update({
                'data': self.storage.get_step_data(self.steps.current),
                'files': self.storage.get_step_files(self.steps.current)
            })
        return datas

    def valid_forms(self, __):
        if self.wizard_goto_step:
            # goto get_response directly
            return False
        return __()

    def _done(self):
        cleaned_data = self.get_all_cleaned_data()
        exclude = self.admin_view.exclude

        opts = self.admin_view.opts
        instance = self.admin_view.org_obj or self.admin_view.model()

        file_field_list = []
        for f in opts.fields:
            if not f.editable or isinstance(f, models.AutoField) \
                    or not f.name in cleaned_data:
                continue
            if exclude and f.name in exclude:
                continue
            # Defer saving file-type fields until after the other fields, so a
            # callable upload_to can use the values from other fields.
            if isinstance(f, models.FileField):
                file_field_list.append(f)
            else:
                f.save_form_data(instance, cleaned_data[f.name])

        for f in file_field_list:
            f.save_form_data(instance, cleaned_data[f.name])

        instance.save()

        for f in opts.many_to_many:
            if f.name in cleaned_data:
                f.save_form_data(instance, cleaned_data[f.name])

        self.admin_view.new_obj = instance

    def save_forms(self, __):
        # if the form is valid, store the cleaned data and files.
        form_obj = self.admin_view.form_obj
        self.storage.set_step_data(self.steps.current, form_obj.data)
        self.storage.set_step_files(self.steps.current, form_obj.files)

        # check if the current step is the last step
        if self.steps.current == self.steps.last:
            # no more steps, render done view
            return self._done()

    def save_models(self, __):
        pass

    def save_related(self, __):
        pass

    def get_context(self, context):
        context.update({
            "show_save": False,
            "show_save_as_new": False,
            "show_save_and_add_another": False,
            "show_save_and_continue": False,
        })
        return context

    def get_response(self, response):
        self.storage.update_response(response)
        return response

    def post_response(self, __):
        if self.steps.current == self.steps.last:
            self.storage.reset()
            return __()

        # change the stored current step
        self.storage.current_step = self.steps.next

        self.admin_view.form_obj = self.get_step_form_obj()
        self.admin_view.setup_forms()

        return self.admin_view.get_response()

    def get_all_cleaned_data(self):
        """
        Returns a merged dictionary of all step cleaned_data dictionaries.
        If a step contains a `FormSet`, the key will be prefixed with formset
        and contain a list of the formset cleaned_data dictionaries.
        """
        cleaned_data = {}
        for form_key, attrs in self.get_form_list().items():
            form_obj = self.get_step_form_obj(form_key)
            if form_obj.is_valid():
                if type(attrs) is dict and 'convert' in attrs:
                    callback = attrs['convert']
                    if callable(callback):
                        callback(self, cleaned_data, form_obj)
                    elif hasattr(self.admin_view, str(callback)):
                        getattr(self.admin_view,
                                str(callback))(self, cleaned_data, form_obj)
                elif isinstance(form_obj.cleaned_data, (tuple, list)):
                    cleaned_data.update({
                        'formset-%s' % form_key: form_obj.cleaned_data
                    })
                else:
                    cleaned_data.update(form_obj.cleaned_data)
        return cleaned_data

    def get_cleaned_data_for_step(self, step):
        """
        Returns the cleaned data for a given `step`. Before returning the
        cleaned data, the stored values are being revalidated through the
        form. If the data doesn't validate, None will be returned.
        """
        if step in self.get_form_list():
            form_obj = self.get_step_form_obj(step)
            if form_obj.is_valid():
                return form_obj.cleaned_data
        return None

    def get_next_step(self, step=None):
        """
        Returns the next step after the given `step`. If no more steps are
        available, None will be returned. If the `step` argument is None, the
        current step will be determined automatically.
        """
        if step is None:
            step = self.steps.current
        form_list = self.get_form_list()
        key = form_list.keyOrder.index(step) + 1
        if len(form_list.keyOrder) > key:
            return form_list.keyOrder[key]
        return None

    def get_prev_step(self, step=None):
        """
        Returns the previous step before the given `step`. If there are no
        steps available, None will be returned. If the `step` argument is
        None, the current step will be determined automatically.
        """
        if step is None:
            step = self.steps.current
        form_list = self.get_form_list()
        key = form_list.keyOrder.index(step) - 1
        if key >= 0:
            return form_list.keyOrder[key]
        return None

    def get_step_index(self, step=None):
        """
        Returns the index for the given `step` name. If no step is given,
        the current step will be used to get the index.
        """
        if step is None:
            step = self.steps.current
        return self.get_form_list().keyOrder.index(step)

    def block_before_fieldsets(self, context, nodes):
        context.update(dict(self.storage.extra_data))
        context['wizard'] = {
            'steps': self.steps,
            'management_form': ManagementForm(prefix=self.prefix, initial={
                'current_step': self.steps.current,
            }),
        }
        nodes.append(loader.render_to_string('xadmin/blocks/model_form.before_fieldsets.wizard.html', context_instance=context))

    def block_submit_line(self, context, nodes):
        context.update(dict(self.storage.extra_data))
        context['wizard'] = {
            'steps': self.steps
        }
        nodes.append(loader.render_to_string('xadmin/blocks/model_form.submit_line.wizard.html', context_instance=context))

site.register_plugin(WizardFormPlugin, ModelFormAdminView)

########NEW FILE########
__FILENAME__ = xversion
from django.contrib.contenttypes.generic import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.related import RelatedObject
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from xadmin.layout import Field, render_field
from xadmin.plugins.inline import Inline
from xadmin.plugins.actions import BaseActionView
from xadmin.plugins.inline import InlineModelAdmin
from xadmin.sites import site
from xadmin.util import unquote, quote, model_format_dict
from xadmin.views import BaseAdminPlugin, ModelAdminView, CreateAdminView, UpdateAdminView, DetailAdminView, ModelFormAdminView, DeleteAdminView, ListAdminView
from xadmin.views.base import csrf_protect_m, filter_hook
from xadmin.views.detail import DetailAdminUtil
from reversion.models import Revision, Version
from reversion.revisions import default_revision_manager, RegistrationError
from functools import partial


def _autoregister(admin, model, follow=None):
    """Registers a model with reversion, if required."""
    if model._meta.proxy:
        raise RegistrationError("Proxy models cannot be used with django-reversion, register the parent class instead")
    if not admin.revision_manager.is_registered(model):
        follow = follow or []
        for parent_cls, field in model._meta.parents.items():
            follow.append(field.name)
            _autoregister(admin, parent_cls)
        admin.revision_manager.register(
            model, follow=follow, format=admin.reversion_format)


def _register_model(admin, model):
    if not hasattr(admin, 'revision_manager'):
        admin.revision_manager = default_revision_manager
    if not hasattr(admin, 'reversion_format'):
        admin.reversion_format = 'json'

    if not admin.revision_manager.is_registered(model):
        inline_fields = []
        for inline in getattr(admin, 'inlines', []):
            inline_model = inline.model
            if getattr(inline, 'generic_inline', False):
                ct_field = getattr(inline, 'ct_field', 'content_type')
                ct_fk_field = getattr(inline, 'ct_fk_field', 'object_id')
                for field in model._meta.many_to_many:
                    if isinstance(field, GenericRelation) and field.rel.to == inline_model and field.object_id_field_name == ct_fk_field and field.content_type_field_name == ct_field:
                        inline_fields.append(field.name)
                _autoregister(admin, inline_model)
            else:
                fk_name = getattr(inline, 'fk_name', None)
                if not fk_name:
                    for field in inline_model._meta.fields:
                        if isinstance(field, (models.ForeignKey, models.OneToOneField)) and issubclass(model, field.rel.to):
                            fk_name = field.name
                _autoregister(admin, inline_model, follow=[fk_name])
                if not inline_model._meta.get_field(fk_name).rel.is_hidden():
                    accessor = inline_model._meta.get_field(
                        fk_name).related.get_accessor_name()
                    inline_fields.append(accessor)
        _autoregister(admin, model, inline_fields)


def register_models(admin_site=None):
    if admin_site is None:
        admin_site = site

    for model, admin in admin_site._registry.items():
        if getattr(admin, 'reversion_enable', False):
            _register_model(admin, model)


class ReversionPlugin(BaseAdminPlugin):

    # The revision manager instance used to manage revisions.
    revision_manager = default_revision_manager

    # The serialization format to use when registering models with reversion.
    reversion_format = "json"

    # Whether to ignore duplicate revision data.
    ignore_duplicate_revisions = False

    reversion_enable = False

    def init_request(self, *args, **kwargs):
        return self.reversion_enable

    @property
    def revision_context_manager(self):
        """The revision context manager for this VersionAdmin."""
        return self.revision_manager._revision_context_manager

    def get_revision_instances(self, obj):
        """Returns all the instances to be used in the object's revision."""
        return [obj]

    def get_revision_data(self, obj, flag):
        """Returns all the revision data to be used in the object's revision."""
        return dict(
            (o, self.revision_manager.get_adapter(
                o.__class__).get_version_data(o, flag))
            for o in self.get_revision_instances(obj)
        )

    def save_revision(self, obj, tag, comment):
        self.revision_manager.save_revision(
            self.get_revision_data(obj, tag),
            user=self.user,
            comment=comment,
            ignore_duplicates=self.ignore_duplicate_revisions,
            db=self.revision_context_manager.get_db(),
        )

    def do_post(self, __):
        def _method():
            self.revision_context_manager.set_user(self.user)
            comment = ''
            admin_view = self.admin_view
            if isinstance(admin_view, CreateAdminView):
                comment = _(u"Initial version.")
            elif isinstance(admin_view, UpdateAdminView):
                comment = _(u"Change version.")
            elif isinstance(admin_view, RevisionView):
                comment = _(u"Revert version.")
            elif isinstance(admin_view, RecoverView):
                comment = _(u"Rercover version.")
            elif isinstance(admin_view, DeleteAdminView):
                comment = _(u"Deleted %(verbose_name)s.") % {
                    "verbose_name": self.opts.verbose_name}
            self.revision_context_manager.set_comment(comment)
            return __()
        return _method

    def post(self, __, request, *args, **kwargs):
        return self.revision_context_manager.create_revision(manage_manually=False)(self.do_post(__))()

    # def save_models(self, __):
    #     self.revision_context_manager.create_revision(manage_manually=True)(__)()

    #     if self.admin_view.org_obj is None:
    #         self.save_revision(self.admin_view.new_obj, VERSION_ADD, _(u"Initial version."))
    #     else:
    #         self.save_revision(self.admin_view.new_obj, VERSION_CHANGE, _(u"Change version."))

    # def save_related(self, __):
    #     self.revision_context_manager.create_revision(manage_manually=True)(__)()

    # def delete_model(self, __):
    #     self.save_revision(self.admin_view.obj, VERSION_DELETE, \
    #         _(u"Deleted %(verbose_name)s.") % {"verbose_name": self.opts.verbose_name})
    #     self.revision_context_manager.create_revision(manage_manually=True)(__)()

    # Block Views
    def block_top_toolbar(self, context, nodes):
        recoverlist_url = self.admin_view.model_admin_url('recoverlist')
        nodes.append(mark_safe('<div class="btn-group"><a class="btn btn-default btn-sm" href="%s"><i class="fa fa-trash-o"></i> %s</a></div>' % (recoverlist_url, _(u"Recover"))))

    def block_nav_toggles(self, context, nodes):
        obj = getattr(
            self.admin_view, 'org_obj', getattr(self.admin_view, 'obj', None))
        if obj:
            revisionlist_url = self.admin_view.model_admin_url(
                'revisionlist', quote(obj.pk))
            nodes.append(mark_safe('<a href="%s" class="navbar-toggle pull-right"><i class="fa fa-time"></i></a>' % revisionlist_url))

    def block_nav_btns(self, context, nodes):
        obj = getattr(
            self.admin_view, 'org_obj', getattr(self.admin_view, 'obj', None))
        if obj:
            revisionlist_url = self.admin_view.model_admin_url(
                'revisionlist', quote(obj.pk))
            nodes.append(mark_safe('<a href="%s" class="btn btn-default"><i class="fa fa-time"></i> <span>%s</span></a>' % (revisionlist_url, _(u'History'))))


class BaseReversionView(ModelAdminView):

    # The revision manager instance used to manage revisions.
    revision_manager = default_revision_manager

    # The serialization format to use when registering models with reversion.
    reversion_format = "json"

    # Whether to ignore duplicate revision data.
    ignore_duplicate_revisions = False

    # If True, then the default ordering of object_history and recover lists will be reversed.
    history_latest_first = False

    reversion_enable = False

    def init_request(self, *args, **kwargs):
        if not self.has_change_permission() and not self.has_add_permission():
            raise PermissionDenied

    def _order_version_queryset(self, queryset):
        """Applies the correct ordering to the given version queryset."""
        if self.history_latest_first:
            return queryset.order_by("-pk")
        return queryset.order_by("pk")


class RecoverListView(BaseReversionView):

    recover_list_template = None

    def get_context(self):
        context = super(RecoverListView, self).get_context()
        opts = self.opts
        deleted = self._order_version_queryset(
            self.revision_manager.get_deleted(self.model))
        context.update({
            "opts": opts,
            "app_label": opts.app_label,
            "module_name": capfirst(opts.verbose_name),
            "title": _("Recover deleted %(name)s") % {"name": force_unicode(opts.verbose_name_plural)},
            "deleted": deleted,
            "changelist_url": self.model_admin_url("changelist"),
        })
        return context

    @csrf_protect_m
    def get(self, request, *args, **kwargs):
        context = self.get_context()

        return TemplateResponse(
            request, self.recover_list_template or self.get_template_list(
                "views/recover_list.html"),
            context, current_app=self.admin_site.name)


class RevisionListView(BaseReversionView):

    object_history_template = None
    revision_diff_template = None

    def get_context(self):
        context = super(RevisionListView, self).get_context()

        opts = self.opts
        action_list = [
            {
                "revision": version.revision,
                "url": self.model_admin_url('revision', quote(version.object_id), version.id),
                "version": version
            }
            for version
            in self._order_version_queryset(self.revision_manager.get_for_object_reference(
                self.model,
                self.obj.pk,
            ).select_related("revision__user"))
        ]
        context.update({
            'title': _('Change history: %s') % force_unicode(self.obj),
            'action_list': action_list,
            'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
            'object': self.obj,
            'app_label': opts.app_label,
            "changelist_url": self.model_admin_url("changelist"),
            "update_url": self.model_admin_url("change", self.obj.pk),
            'opts': opts,
        })
        return context

    def get(self, request, object_id, *args, **kwargs):
        object_id = unquote(object_id)
        self.obj = self.get_object(object_id)

        if not self.has_change_permission(self.obj):
            raise PermissionDenied

        return self.get_response()

    def get_response(self):
        context = self.get_context()

        return TemplateResponse(self.request, self.object_history_template or
                                self.get_template_list('views/model_history.html'), context, current_app=self.admin_site.name)

    def get_version_object(self, version):
        obj_version = version.object_version
        obj = obj_version.object
        obj._state.db = self.obj._state.db

        for field_name, pks in obj_version.m2m_data.items():
            f = self.opts.get_field(field_name)
            if f.rel and isinstance(f.rel, models.ManyToManyRel):
                setattr(obj, f.name, f.rel.to._default_manager.get_query_set(
                ).filter(pk__in=pks).all())

        detail = self.get_model_view(DetailAdminUtil, self.model, obj)

        return obj, detail

    def post(self, request, object_id, *args, **kwargs):
        object_id = unquote(object_id)
        self.obj = self.get_object(object_id)

        if not self.has_change_permission(self.obj):
            raise PermissionDenied

        params = self.request.POST
        if 'version_a' not in params or 'version_b' not in params:
            self.message_user(_("Must select two versions."), 'error')
            return self.get_response()

        version_a_id = params['version_a']
        version_b_id = params['version_b']

        if version_a_id == version_b_id:
            self.message_user(
                _("Please select two different versions."), 'error')
            return self.get_response()

        version_a = get_object_or_404(Version, pk=version_a_id)
        version_b = get_object_or_404(Version, pk=version_b_id)

        diffs = []

        obj_a, detail_a = self.get_version_object(version_a)
        obj_b, detail_b = self.get_version_object(version_b)

        for f in (self.opts.fields + self.opts.many_to_many):
            if isinstance(f, RelatedObject):
                label = f.opts.verbose_name
            else:
                label = f.verbose_name

            value_a = f.value_from_object(obj_a)
            value_b = f.value_from_object(obj_b)
            is_diff = value_a != value_b

            if type(value_a) in (list, tuple) and type(value_b) in (list, tuple) \
                    and len(value_a) == len(value_b) and is_diff:
                is_diff = False
                for i in xrange(len(value_a)):
                    if value_a[i] != value_a[i]:
                        is_diff = True
                        break
            if type(value_a) is QuerySet and type(value_b) is QuerySet:
                is_diff = list(value_a) != list(value_b)

            diffs.append((label, detail_a.get_field_result(
                f.name).val, detail_b.get_field_result(f.name).val, is_diff))

        context = super(RevisionListView, self).get_context()
        context.update({
            'object': self.obj,
            'opts': self.opts,
            'version_a': version_a,
            'version_b': version_b,
            'revision_a_url': self.model_admin_url('revision', quote(version_a.object_id), version_a.id),
            'revision_b_url': self.model_admin_url('revision', quote(version_b.object_id), version_b.id),
            'diffs': diffs
        })

        return TemplateResponse(
            self.request, self.revision_diff_template or self.get_template_list('views/revision_diff.html'),
            context, current_app=self.admin_site.name)

    @filter_hook
    def get_media(self):
        return super(RevisionListView, self).get_media() + self.vendor('xadmin.plugin.revision.js', 'xadmin.form.css')


class BaseRevisionView(ModelFormAdminView):

    @filter_hook
    def get_revision(self):
        return self.version.field_dict

    @filter_hook
    def get_form_datas(self):
        datas = {"instance": self.org_obj, "initial": self.get_revision()}
        if self.request_method == 'post':
            datas.update(
                {'data': self.request.POST, 'files': self.request.FILES})
        return datas

    @filter_hook
    def get_context(self):
        context = super(BaseRevisionView, self).get_context()
        context.update({
            'object': self.org_obj
        })
        return context

    @filter_hook
    def get_media(self):
        return super(BaseRevisionView, self).get_media() + self.vendor('xadmin.plugin.revision.js')


class DiffField(Field):

    def render(self, form, form_style, context):
        html = ''
        for field in self.fields:
            html += ('<div class="diff_field" rel="tooltip"><textarea class="org-data" style="display:none;">%s</textarea>%s</div>' %
                    (_('Current: %s') % self.attrs.pop('orgdata', ''), render_field(field, form, form_style, context, template=self.template, attrs=self.attrs)))
        return html


class RevisionView(BaseRevisionView):

    revision_form_template = None

    def init_request(self, object_id, version_id):
        self.detail = self.get_model_view(
            DetailAdminView, self.model, object_id)
        self.org_obj = self.detail.obj
        self.version = get_object_or_404(
            Version, pk=version_id, object_id=unicode(self.org_obj.pk))

        self.prepare_form()

    def get_form_helper(self):
        helper = super(RevisionView, self).get_form_helper()
        diff_fields = {}
        version_data = self.version.field_dict
        for f in self.opts.fields:
            if f.value_from_object(self.org_obj) != version_data.get(f.name, None):
                diff_fields[f.name] = self.detail.get_field_result(f.name).val
        for k, v in diff_fields.items():
            helper[k].wrap(DiffField, orgdata=v)
        return helper

    @filter_hook
    def get_context(self):
        context = super(RevisionView, self).get_context()
        context["title"] = _(
            "Revert %s") % force_unicode(self.model._meta.verbose_name)
        return context

    @filter_hook
    def get_response(self):
        context = self.get_context()
        context.update(self.kwargs or {})

        form_template = self.revision_form_template
        return TemplateResponse(
            self.request, form_template or self.get_template_list(
                'views/revision_form.html'),
            context, current_app=self.admin_site.name)

    @filter_hook
    def post_response(self):
        self.message_user(_('The %(model)s "%(name)s" was reverted successfully. You may edit it again below.') %
                          {"model": force_unicode(self.opts.verbose_name), "name": unicode(self.new_obj)}, 'success')
        return HttpResponseRedirect(self.model_admin_url('change', self.new_obj.pk))


class RecoverView(BaseRevisionView):

    recover_form_template = None

    def init_request(self, version_id):
        if not self.has_change_permission() and not self.has_add_permission():
            raise PermissionDenied

        self.version = get_object_or_404(Version, pk=version_id)
        self.org_obj = self.version.object_version.object

        self.prepare_form()

    @filter_hook
    def get_context(self):
        context = super(RecoverView, self).get_context()
        context["title"] = _("Recover %s") % self.version.object_repr
        return context

    @filter_hook
    def get_response(self):
        context = self.get_context()
        context.update(self.kwargs or {})

        form_template = self.recover_form_template
        return TemplateResponse(
            self.request, form_template or self.get_template_list(
                'views/recover_form.html'),
            context, current_app=self.admin_site.name)

    @filter_hook
    def post_response(self):
        self.message_user(_('The %(model)s "%(name)s" was recovered successfully. You may edit it again below.') %
                          {"model": force_unicode(self.opts.verbose_name), "name": unicode(self.new_obj)}, 'success')
        return HttpResponseRedirect(self.model_admin_url('change', self.new_obj.pk))


class InlineDiffField(Field):

    def render(self, form, form_style, context):
        html = ''
        instance = form.instance
        if not instance.pk:
            return super(InlineDiffField, self).render(form, form_style, context)

        initial = form.initial
        opts = instance._meta
        detail = form.detail
        for field in self.fields:
            f = opts.get_field(field)
            f_html = render_field(field, form, form_style, context,
                                  template=self.template, attrs=self.attrs)
            if f.value_from_object(instance) != initial.get(field, None):
                current_val = detail.get_field_result(f.name).val
                html += ('<div class="diff_field" rel="tooltip"><textarea class="org-data" style="display:none;">%s</textarea>%s</div>'
                         % (_('Current: %s') % current_val, f_html))
            else:
                html += f_html
        return html

# inline hack plugin


class InlineRevisionPlugin(BaseAdminPlugin):

    def get_related_versions(self, obj, version, formset):
        """Retreives all the related Version objects for the given FormSet."""
        object_id = obj.pk
        # Get the fk name.
        try:
            fk_name = formset.fk.name
        except AttributeError:
            # This is a GenericInlineFormset, or similar.
            fk_name = formset.ct_fk_field.name
        # Look up the revision data.
        revision_versions = version.revision.version_set.all()
        related_versions = dict([(related_version.object_id, related_version)
                                 for related_version in revision_versions
                                 if ContentType.objects.get_for_id(related_version.content_type_id).model_class() == formset.model
                                 and unicode(related_version.field_dict[fk_name]) == unicode(object_id)])
        return related_versions

    def _hack_inline_formset_initial(self, revision_view, formset):
        """Hacks the given formset to contain the correct initial data."""
        # Now we hack it to push in the data from the revision!
        initial = []
        related_versions = self.get_related_versions(
            revision_view.org_obj, revision_view.version, formset)
        formset.related_versions = related_versions
        for related_obj in formset.queryset:
            if unicode(related_obj.pk) in related_versions:
                initial.append(
                    related_versions.pop(unicode(related_obj.pk)).field_dict)
            else:
                initial_data = model_to_dict(related_obj)
                initial_data["DELETE"] = True
                initial.append(initial_data)
        for related_version in related_versions.values():
            initial_row = related_version.field_dict
            pk_name = ContentType.objects.get_for_id(
                related_version.content_type_id).model_class()._meta.pk.name
            del initial_row[pk_name]
            initial.append(initial_row)
        # Reconstruct the forms with the new revision data.
        formset.initial = initial
        formset.forms = [formset._construct_form(
            n) for n in xrange(len(initial))]
        # Hack the formset to force a save of everything.

        def get_changed_data(form):
            return [field.name for field in form.fields]
        for form in formset.forms:
            form.has_changed = lambda: True
            form._get_changed_data = partial(get_changed_data, form=form)

        def total_form_count_hack(count):
            return lambda: count
        formset.total_form_count = total_form_count_hack(len(initial))

        if self.request.method == 'GET' and formset.helper and formset.helper.layout:
            helper = formset.helper
            helper.filter(basestring).wrap(InlineDiffField)
            fake_admin_class = type(str('%s%sFakeAdmin' % (self.opts.app_label, self.opts.module_name)), (object, ), {'model': self.model})
            for form in formset.forms:
                instance = form.instance
                if instance.pk:
                    form.detail = self.get_view(
                        DetailAdminUtil, fake_admin_class, instance)

    def instance_form(self, formset, **kwargs):
        admin_view = self.admin_view.admin_view
        if hasattr(admin_view, 'version') and hasattr(admin_view, 'org_obj'):
            self._hack_inline_formset_initial(admin_view, formset)
        return formset

# action revision


class ActionRevisionPlugin(BaseAdminPlugin):

    revision_manager = default_revision_manager
    reversion_enable = False

    def init_request(self, *args, **kwargs):
        return self.reversion_enable

    @property
    def revision_context_manager(self):
        return self.revision_manager._revision_context_manager

    def do_action_func(self, __):
        def _method():
            self.revision_context_manager.set_user(self.user)
            action_view = self.admin_view
            comment = action_view.description % model_format_dict(self.opts)

            self.revision_context_manager.set_comment(comment)
            return __()
        return _method

    def do_action(self, __, queryset):
        return self.revision_context_manager.create_revision(manage_manually=False)(self.do_action_func(__))()


class VersionInline(object):
    model = Version
    extra = 0
    style = 'accordion'

class ReversionAdmin(object):
    model_icon = 'fa fa-exchange'

    list_display = ('__str__', 'date_created', 'user', 'comment')
    list_display_links = ('__str__',)

    list_filter = ('date_created', 'user')
    inlines = [VersionInline]

site.register(Revision, ReversionAdmin)

site.register_modelview(
    r'^recover/$', RecoverListView, name='%s_%s_recoverlist')
site.register_modelview(
    r'^recover/([^/]+)/$', RecoverView, name='%s_%s_recover')
site.register_modelview(
    r'^([^/]+)/revision/$', RevisionListView, name='%s_%s_revisionlist')
site.register_modelview(
    r'^([^/]+)/revision/([^/]+)/$', RevisionView, name='%s_%s_revision')

site.register_plugin(ReversionPlugin, ListAdminView)
site.register_plugin(ReversionPlugin, ModelFormAdminView)
site.register_plugin(ReversionPlugin, DeleteAdminView)

site.register_plugin(InlineRevisionPlugin, InlineModelAdmin)
site.register_plugin(ActionRevisionPlugin, BaseActionView)

########NEW FILE########
__FILENAME__ = sites
import sys
from functools import update_wrapper
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django.views.decorators.cache import never_cache

reload(sys)
sys.setdefaultencoding("utf-8")


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class MergeAdminMetaclass(type):
    def __new__(cls, name, bases, attrs):
        return type.__new__(cls, str(name), bases, attrs)


class AdminSite(object):

    def __init__(self, name='xadmin'):
        self.name = name
        self.app_name = 'xadmin'

        self._registry = {}  # model_class class -> admin_class class
        self._registry_avs = {}  # admin_view_class class -> admin_class class
        self._registry_settings = {}  # settings name -> admin_class class
        self._registry_views = []
            # url instance contains (path, admin_view class, name)
        self._registry_modelviews = []
            # url instance contains (path, admin_view class, name)
        self._registry_plugins = {}  # view_class class -> plugin_class class

        self._admin_view_cache = {}

        self.check_dependencies()

        self.model_admins_order = 0

    def copy_registry(self):
        import copy
        return {
            'models': copy.copy(self._registry),
            'avs': copy.copy(self._registry_avs),
            'views': copy.copy(self._registry_views),
            'settings': copy.copy(self._registry_settings),
            'modelviews': copy.copy(self._registry_modelviews),
            'plugins': copy.copy(self._registry_plugins),
        }

    def restore_registry(self, data):
        self._registry = data['models']
        self._registry_avs = data['avs']
        self._registry_views = data['views']
        self._registry_settings = data['settings']
        self._registry_modelviews = data['modelviews']
        self._registry_plugins = data['plugins']

    def register_modelview(self, path, admin_view_class, name):
        from xadmin.views.base import BaseAdminView
        if issubclass(admin_view_class, BaseAdminView):
            self._registry_modelviews.append((path, admin_view_class, name))
        else:
            raise ImproperlyConfigured(u'The registered view class %s isn\'t subclass of %s' %
                                      (admin_view_class.__name__, BaseAdminView.__name__))

    def register_view(self, path, admin_view_class, name):
        self._registry_views.append((path, admin_view_class, name))

    def register_plugin(self, plugin_class, admin_view_class):
        from xadmin.views.base import BaseAdminPlugin
        if issubclass(plugin_class, BaseAdminPlugin):
            self._registry_plugins.setdefault(
                admin_view_class, []).append(plugin_class)
        else:
            raise ImproperlyConfigured(u'The registered plugin class %s isn\'t subclass of %s' %
                                      (plugin_class.__name__, BaseAdminPlugin.__name__))

    def register_settings(self, name, admin_class):
        self._registry_settings[name.lower()] = admin_class

    def register(self, model_or_iterable, admin_class=object, **options):
        from xadmin.views.base import BaseAdminView
        if isinstance(model_or_iterable, ModelBase) or issubclass(model_or_iterable, BaseAdminView):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if isinstance(model, ModelBase):
                if model._meta.abstract:
                    raise ImproperlyConfigured('The model %s is abstract, so it '
                                               'cannot be registered with admin.' % model.__name__)

                if model in self._registry:
                    raise AlreadyRegistered(
                        'The model %s is already registered' % model.__name__)

                # If we got **options then dynamically construct a subclass of
                # admin_class with those **options.
                if options:
                    # For reasons I don't quite understand, without a __module__
                    # the created class appears to "live" in the wrong place,
                    # which causes issues later on.
                    options['__module__'] = __name__

                admin_class = type(str("%s%sAdmin" % (model._meta.app_label, model._meta.module_name)), (admin_class,), options or {})
                admin_class.model = model
                admin_class.order = self.model_admins_order
                self.model_admins_order += 1
                self._registry[model] = admin_class
            else:
                if model in self._registry_avs:
                    raise AlreadyRegistered('The admin_view_class %s is already registered' % model.__name__)
                if options:
                    options['__module__'] = __name__
                    admin_class = type(str(
                        "%sAdmin" % model.__name__), (admin_class,), options)

                # Instantiate the admin class to save in the registry
                self._registry_avs[model] = admin_class

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        from xadmin.views.base import BaseAdminView
        if isinstance(model_or_iterable, (ModelBase, BaseAdminView)):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if isinstance(model, ModelBase):
                if model not in self._registry:
                    raise NotRegistered(
                        'The model %s is not registered' % model.__name__)
                del self._registry[model]
            else:
                if model not in self._registry_avs:
                    raise NotRegistered('The admin_view_class %s is not registered' % model.__name__)
                del self._registry_avs[model]

    def set_loginview(self, login_view):
        self.login_view = login_view

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        return request.user.is_active and request.user.is_staff

    def check_dependencies(self):
        """
        Check that all things needed to run the admin have been correctly installed.

        The default implementation checks that LogEntry, ContentType and the
        auth context processor are installed.
        """
        from django.contrib.contenttypes.models import ContentType

        if not ContentType._meta.installed:
            raise ImproperlyConfigured("Put 'django.contrib.contenttypes' in "
                                       "your INSTALLED_APPS setting in order to use the admin application.")
        if not ('django.contrib.auth.context_processors.auth' in settings.TEMPLATE_CONTEXT_PROCESSORS or
                'django.core.context_processors.auth' in settings.TEMPLATE_CONTEXT_PROCESSORS):
            raise ImproperlyConfigured("Put 'django.contrib.auth.context_processors.auth' "
                                       "in your TEMPLATE_CONTEXT_PROCESSORS setting in order to use the admin application.")

    def admin_view(self, view, cacheable=False):
        """
        Decorator to create an admin view attached to this ``AdminSite``. This
        wraps the view and provides permission checking by calling
        ``self.has_permission``.

        You'll want to use this from within ``AdminSite.get_urls()``:

            class MyAdminSite(AdminSite):

                def get_urls(self):
                    from django.conf.urls import patterns, url

                    urls = super(MyAdminSite, self).get_urls()
                    urls += patterns('',
                        url(r'^my_view/$', self.admin_view(some_view))
                    )
                    return urls

        By default, admin_views are marked non-cacheable using the
        ``never_cache`` decorator. If the view can be safely cached, set
        cacheable=True.
        """
        def inner(request, *args, **kwargs):
            if not self.has_permission(request) and getattr(view, 'need_site_permission', True):
                return self.create_admin_view(self.login_view)(request, *args, **kwargs)
            return view(request, *args, **kwargs)
        if not cacheable:
            inner = never_cache(inner)
        return update_wrapper(inner, view)

    def _get_merge_attrs(self, option_class, plugin_class):
        return dict([(name, getattr(option_class, name)) for name in dir(option_class)
                    if name[0] != '_' and not callable(getattr(option_class, name)) and hasattr(plugin_class, name)])

    def _get_settings_class(self, admin_view_class):
        name = admin_view_class.__name__.lower()

        if name in self._registry_settings:
            return self._registry_settings[name]
        elif name.endswith('admin') and name[0:-5] in self._registry_settings:
            return self._registry_settings[name[0:-5]]
        elif name.endswith('adminview') and name[0:-9] in self._registry_settings:
            return self._registry_settings[name[0:-9]]

        return None

    def _create_plugin(self, option_classes):
        def merge_class(plugin_class):
            if option_classes:
                attrs = {}
                bases = [plugin_class]
                for oc in option_classes:
                    attrs.update(self._get_merge_attrs(oc, plugin_class))
                    meta_class = getattr(oc, plugin_class.__name__, getattr(oc, plugin_class.__name__.replace('Plugin', ''), None))
                    if meta_class:
                        bases.insert(0, meta_class)
                if attrs:
                    plugin_class = MergeAdminMetaclass(
                        '%s%s' % (''.join([oc.__name__ for oc in option_classes]), plugin_class.__name__),
                        tuple(bases), attrs)
            return plugin_class
        return merge_class

    def get_plugins(self, admin_view_class, *option_classes):
        from xadmin.views import BaseAdminView
        plugins = []
        opts = [oc for oc in option_classes if oc]
        for klass in admin_view_class.mro():
            if klass == BaseAdminView or issubclass(klass, BaseAdminView):
                merge_opts = []
                reg_class = self._registry_avs.get(klass)
                if reg_class:
                    merge_opts.append(reg_class)
                settings_class = self._get_settings_class(klass)
                if settings_class:
                    merge_opts.append(settings_class)
                merge_opts.extend(opts)
                ps = self._registry_plugins.get(klass, [])
                plugins.extend(map(self._create_plugin(
                    merge_opts), ps) if merge_opts else ps)
        return plugins

    def get_view_class(self, view_class, option_class=None, **opts):
        merges = [option_class] if option_class else []
        for klass in view_class.mro():
            reg_class = self._registry_avs.get(klass)
            if reg_class:
                merges.append(reg_class)
            settings_class = self._get_settings_class(klass)
            if settings_class:
                merges.append(settings_class)
            merges.append(klass)
        new_class_name = ''.join([c.__name__ for c in merges])

        if new_class_name not in self._admin_view_cache:
            plugins = self.get_plugins(view_class, option_class)
            self._admin_view_cache[new_class_name] = MergeAdminMetaclass(
                new_class_name, tuple(merges),
                dict({'plugin_classes': plugins, 'admin_site': self}, **opts))

        return self._admin_view_cache[new_class_name]

    def create_admin_view(self, admin_view_class):
        return self.get_view_class(admin_view_class).as_view()

    def create_model_admin_view(self, admin_view_class, model, option_class):
        return self.get_view_class(admin_view_class, option_class).as_view()

    def get_urls(self):
        from django.conf.urls import patterns, url, include
        from xadmin.views.base import BaseAdminView

        if settings.DEBUG:
            self.check_dependencies()

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        # Admin-site-wide views.
        urlpatterns = patterns('',
                               url(r'^jsi18n/$', wrap(self.i18n_javascript,
                                                      cacheable=True), name='jsi18n')
                               )

        # Registed admin views
        urlpatterns += patterns('',
                                *[url(
                                  path, wrap(self.create_admin_view(clz_or_func)) if type(clz_or_func) == type and issubclass(clz_or_func, BaseAdminView) else include(clz_or_func(self)),
                                  name=name) for path, clz_or_func, name in self._registry_views]
                                )

        # Add in each model's views.
        for model, admin_class in self._registry.iteritems():
            view_urls = [url(
                path, wrap(
                    self.create_model_admin_view(clz, model, admin_class)),
                name=name % (model._meta.app_label, model._meta.module_name))
                for path, clz, name in self._registry_modelviews]
            urlpatterns += patterns('',
                                    url(
                                    r'^%s/%s/' % (
                                        model._meta.app_label, model._meta.module_name),
                                    include(patterns('', *view_urls)))
                                    )

        return urlpatterns

    @property
    def urls(self):
        return self.get_urls(), self.name, self.app_name

    def i18n_javascript(self, request):
        """
        Displays the i18n JavaScript that the Django admin requires.

        This takes into account the USE_I18N setting. If it's set to False, the
        generated JavaScript will be leaner and faster.
        """
        if settings.USE_I18N:
            from django.views.i18n import javascript_catalog
        else:
            from django.views.i18n import null_javascript_catalog as javascript_catalog
        return javascript_catalog(request, packages=['django.conf', 'xadmin'])

# This global object represents the default admin site, for the common case.
# You can instantiate AdminSite in your own code to create a custom admin site.
site = AdminSite()

########NEW FILE########
__FILENAME__ = xadmin_tags
from django.template import Library
from xadmin.util import static, vendor as util_vendor

register = Library()


@register.simple_tag(takes_context=True)
def view_block(context, block_name, *args, **kwargs):
    if 'admin_view' not in context:
        return ""

    admin_view = context['admin_view']
    nodes = []
    method_name = 'block_%s' % block_name

    for view in [admin_view] + admin_view.plugins:
        if hasattr(view, method_name) and callable(getattr(view, method_name)):
            block_func = getattr(view, method_name)
            result = block_func(context, nodes, *args, **kwargs)
            if result and type(result) in (str, unicode):
                nodes.append(result)
    if nodes:
        return ''.join(nodes)
    else:
        return ""


@register.filter
def admin_urlname(value, arg):
    return 'xadmin:%s_%s_%s' % (value.app_label, value.module_name, arg)

static = register.simple_tag(static)


@register.simple_tag(takes_context=True)
def vendor(context, *tags):
    return util_vendor(*tags).render()

########NEW FILE########
__FILENAME__ = util
import django
from django.db import models
from django.db.models.sql.query import LOOKUP_SEP
from django.db.models.deletion import Collector
from django.db.models.related import RelatedObject
from django.forms.forms import pretty_name
from django.utils import formats
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.encoding import force_unicode, smart_unicode, smart_str
from django.utils.translation import ungettext
from django.core.urlresolvers import reverse
from django.conf import settings
from django.forms import Media
from django.utils.translation import get_language
import datetime
import decimal

if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.templatetags.staticfiles import static
else:
    from django.templatetags.static import static

try:
    import json
except ImportError:
    from django.utils import simplejson as json

try:
    from django.utils.timezone import template_localtime as tz_localtime
except ImportError:
    from django.utils.timezone import localtime as tz_localtime

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    username_field = User.USERNAME_FIELD
except Exception:
    from django.contrib.auth.models import User
    username_field = 'username'


def xstatic(*tags):
    from vendors import vendors
    node = vendors

    fs = []
    lang = get_language()

    for tag in tags:
        try:
            for p in tag.split('.'):
                node = node[p]
        except Exception, e:
            if tag.startswith('xadmin'):
                file_type = tag.split('.')[-1]
                if file_type in ('css', 'js'):
                    node = "xadmin/%s/%s" % (file_type, tag)
                else:
                    raise e
            else:
                raise e

        if type(node) in (str, unicode):
            files = node
        else:
            mode = 'dev'
            if not settings.DEBUG:
                mode = getattr(settings, 'STATIC_USE_CDN',
                               False) and 'cdn' or 'production'

            if mode == 'cdn' and mode not in node:
                mode = 'production'
            if mode == 'production' and mode not in node:
                mode = 'dev'
            files = node[mode]

        files = type(files) in (list, tuple) and files or [files, ]
        fs.extend(files)

    return [f.startswith('http://') and f or static(f) for f in fs]


def vendor(*tags):
    media = Media()
    for tag in tags:
        file_type = tag.split('.')[-1]
        files = xstatic(tag)
        if file_type == 'js':
            media.add_js(files)
        elif file_type == 'css':
            media.add_css({'screen': files})
    return media


def lookup_needs_distinct(opts, lookup_path):
    """
    Returns True if 'distinct()' should be used to query the given lookup path.
    """
    field_name = lookup_path.split('__', 1)[0]
    field = opts.get_field_by_name(field_name)[0]
    if ((hasattr(field, 'rel') and
         isinstance(field.rel, models.ManyToManyRel)) or
        (isinstance(field, models.related.RelatedObject) and
         not field.field.unique)):
        return True
    return False


def prepare_lookup_value(key, value):
    """
    Returns a lookup value prepared to be used in queryset filtering.
    """
    # if key ends with __in, split parameter into separate values
    if key.endswith('__in'):
        value = value.split(',')
    # if key ends with __isnull, special case '' and false
    if key.endswith('__isnull') and type(value) == str:
        if value.lower() in ('', 'false'):
            value = False
        else:
            value = True
    return value


def quote(s):
    """
    Ensure that primary key values do not confuse the admin URLs by escaping
    any '/', '_' and ':' characters. Similar to urllib.quote, except that the
    quoting is slightly different so that it doesn't get automatically
    unquoted by the Web browser.
    """
    if not isinstance(s, basestring):
        return s
    res = list(s)
    for i in range(len(res)):
        c = res[i]
        if c in """:/_#?;@&=+$,"<>%\\""":
            res[i] = '_%02X' % ord(c)
    return ''.join(res)


def unquote(s):
    """
    Undo the effects of quote(). Based heavily on urllib.unquote().
    """
    if not isinstance(s, basestring):
        return s
    mychr = chr
    myatoi = int
    list = s.split('_')
    res = [list[0]]
    myappend = res.append
    del list[0]
    for item in list:
        if item[1:2]:
            try:
                myappend(mychr(myatoi(item[:2], 16)) + item[2:])
            except ValueError:
                myappend('_' + item)
        else:
            myappend('_' + item)
    return "".join(res)


def flatten_fieldsets(fieldsets):
    """Returns a list of field names from an admin fieldsets structure."""
    field_names = []
    for name, opts in fieldsets:
        for field in opts['fields']:
            # type checking feels dirty, but it seems like the best way here
            if type(field) == tuple:
                field_names.extend(field)
            else:
                field_names.append(field)
    return field_names


def get_deleted_objects(objs, opts, user, admin_site, using):
    """
    Find all objects related to ``objs`` that should also be deleted. ``objs``
    must be a homogenous iterable of objects (e.g. a QuerySet).

    Returns a nested list of strings suitable for display in the
    template with the ``unordered_list`` filter.

    """
    collector = NestedObjects(using=using)
    collector.collect(objs)
    perms_needed = set()

    def format_callback(obj):
        has_admin = obj.__class__ in admin_site._registry
        opts = obj._meta

        if has_admin:
            admin_url = reverse('%s:%s_%s_change'
                                % (admin_site.name,
                                   opts.app_label,
                                   opts.object_name.lower()),
                                None, (quote(obj._get_pk_val()),))
            p = '%s.%s' % (opts.app_label,
                           opts.get_delete_permission())
            if not user.has_perm(p):
                perms_needed.add(opts.verbose_name)
            # Display a link to the admin page.
            return mark_safe(u'<span class="label label-info">%s:</span> <a href="%s">%s</a>' %
                             (escape(capfirst(opts.verbose_name)),
                              admin_url,
                              escape(obj)))
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return mark_safe(u'<span class="label label-info">%s:</span> %s' %
                             (escape(capfirst(opts.verbose_name)),
                              escape(obj)))

    to_delete = collector.nested(format_callback)
    protected = [format_callback(obj) for obj in collector.protected]

    return to_delete, perms_needed, protected


class NestedObjects(Collector):
    def __init__(self, *args, **kwargs):
        super(NestedObjects, self).__init__(*args, **kwargs)
        self.edges = {}  # {from_instance: [to_instances]}
        self.protected = set()

    def add_edge(self, source, target):
        self.edges.setdefault(source, []).append(target)

    def collect(self, objs, source_attr=None, **kwargs):
        for obj in objs:
            if source_attr:
                self.add_edge(getattr(obj, source_attr), obj)
            else:
                self.add_edge(None, obj)
        try:
            return super(NestedObjects, self).collect(objs, source_attr=source_attr, **kwargs)
        except models.ProtectedError, e:
            self.protected.update(e.protected_objects)

    def related_objects(self, related, objs):
        qs = super(NestedObjects, self).related_objects(related, objs)
        return qs.select_related(related.field.name)

    def _nested(self, obj, seen, format_callback):
        if obj in seen:
            return []
        seen.add(obj)
        children = []
        for child in self.edges.get(obj, ()):
            children.extend(self._nested(child, seen, format_callback))
        if format_callback:
            ret = [format_callback(obj)]
        else:
            ret = [obj]
        if children:
            ret.append(children)
        return ret

    def nested(self, format_callback=None):
        """
        Return the graph as a nested list.

        """
        seen = set()
        roots = []
        for root in self.edges.get(None, ()):
            roots.extend(self._nested(root, seen, format_callback))
        return roots


def model_format_dict(obj):
    """
    Return a `dict` with keys 'verbose_name' and 'verbose_name_plural',
    typically for use with string formatting.

    `obj` may be a `Model` instance, `Model` subclass, or `QuerySet` instance.

    """
    if isinstance(obj, (models.Model, models.base.ModelBase)):
        opts = obj._meta
    elif isinstance(obj, models.query.QuerySet):
        opts = obj.model._meta
    else:
        opts = obj
    return {
        'verbose_name': force_unicode(opts.verbose_name),
        'verbose_name_plural': force_unicode(opts.verbose_name_plural)
    }


def model_ngettext(obj, n=None):
    """
    Return the appropriate `verbose_name` or `verbose_name_plural` value for
    `obj` depending on the count `n`.

    `obj` may be a `Model` instance, `Model` subclass, or `QuerySet` instance.
    If `obj` is a `QuerySet` instance, `n` is optional and the length of the
    `QuerySet` is used.

    """
    if isinstance(obj, models.query.QuerySet):
        if n is None:
            n = obj.count()
        obj = obj.model
    d = model_format_dict(obj)
    singular, plural = d["verbose_name"], d["verbose_name_plural"]
    return ungettext(singular, plural, n or 0)


def lookup_field(name, obj, model_admin=None):
    opts = obj._meta
    try:
        f = opts.get_field(name)
    except models.FieldDoesNotExist:
        # For non-field values, the value is either a method, property or
        # returned via a callable.
        if callable(name):
            attr = name
            value = attr(obj)
        elif (model_admin is not None and hasattr(model_admin, name) and
              not name == '__str__' and not name == '__unicode__'):
            attr = getattr(model_admin, name)
            value = attr(obj)
        else:
            attr = getattr(obj, name)
            if callable(attr):
                value = attr()
            else:
                value = attr
        f = None
    else:
        attr = None
        value = getattr(obj, name)
    return f, attr, value


def label_for_field(name, model, model_admin=None, return_attr=False):
    """
    Returns a sensible label for a field name. The name can be a callable or the
    name of an object attributes, as well as a genuine fields. If return_attr is
    True, the resolved attribute (which could be a callable) is also returned.
    This will be None if (and only if) the name refers to a field.
    """
    attr = None
    try:
        field = model._meta.get_field_by_name(name)[0]
        if isinstance(field, RelatedObject):
            label = field.opts.verbose_name
        else:
            label = field.verbose_name
    except models.FieldDoesNotExist:
        if name == "__unicode__":
            label = force_unicode(model._meta.verbose_name)
            attr = unicode
        elif name == "__str__":
            label = smart_str(model._meta.verbose_name)
            attr = str
        else:
            if callable(name):
                attr = name
            elif model_admin is not None and hasattr(model_admin, name):
                attr = getattr(model_admin, name)
            elif hasattr(model, name):
                attr = getattr(model, name)
            else:
                message = "Unable to lookup '%s' on %s" % (
                    name, model._meta.object_name)
                if model_admin:
                    message += " or %s" % (model_admin.__class__.__name__,)
                raise AttributeError(message)

            if hasattr(attr, "short_description"):
                label = attr.short_description
            elif callable(attr):
                if attr.__name__ == "<lambda>":
                    label = "--"
                else:
                    label = pretty_name(attr.__name__)
            else:
                label = pretty_name(name)
    if return_attr:
        return (label, attr)
    else:
        return label


def help_text_for_field(name, model):
    try:
        help_text = model._meta.get_field_by_name(name)[0].help_text
    except models.FieldDoesNotExist:
        help_text = ""
    return smart_unicode(help_text)


def admin_urlname(value, arg):
    return 'xadmin:%s_%s_%s' % (value.app_label, value.module_name, arg)


def boolean_icon(field_val):
    return mark_safe(u'<i class="%s" alt="%s"></i>' % (
        {True: 'fa fa-check-circle text-success', False: 'fa fa-times-circle text-error', None: 'fa fa-question-circle muted'}[field_val], field_val))


def display_for_field(value, field):
    from xadmin.views.list import EMPTY_CHANGELIST_VALUE

    if field.flatchoices:
        return dict(field.flatchoices).get(value, EMPTY_CHANGELIST_VALUE)
    # NullBooleanField needs special-case null-handling, so it comes
    # before the general null test.
    elif isinstance(field, models.BooleanField) or isinstance(field, models.NullBooleanField):
        return boolean_icon(value)
    elif value is None:
        return EMPTY_CHANGELIST_VALUE
    elif isinstance(field, models.DateTimeField):
        return formats.localize(tz_localtime(value))
    elif isinstance(field, (models.DateField, models.TimeField)):
        return formats.localize(value)
    elif isinstance(field, models.DecimalField):
        return formats.number_format(value, field.decimal_places)
    elif isinstance(field, models.FloatField):
        return formats.number_format(value)
    elif isinstance(field.rel, models.ManyToManyRel):
        return ', '.join([smart_unicode(obj) for obj in value.all()])
    else:
        return smart_unicode(value)


def display_for_value(value, boolean=False):
    from xadmin.views.list import EMPTY_CHANGELIST_VALUE

    if boolean:
        return boolean_icon(value)
    elif value is None:
        return EMPTY_CHANGELIST_VALUE
    elif isinstance(value, datetime.datetime):
        return formats.localize(tz_localtime(value))
    elif isinstance(value, (datetime.date, datetime.time)):
        return formats.localize(value)
    elif isinstance(value, (decimal.Decimal, float)):
        return formats.number_format(value)
    else:
        return smart_unicode(value)


class NotRelationField(Exception):
    pass


def get_model_from_relation(field):
    if isinstance(field, models.related.RelatedObject):
        return field.model
    elif getattr(field, 'rel'):  # or isinstance?
        return field.rel.to
    else:
        raise NotRelationField


def reverse_field_path(model, path):
    """ Create a reversed field path.

    E.g. Given (Order, "user__groups"),
    return (Group, "user__order").

    Final field must be a related model, not a data field.

    """
    reversed_path = []
    parent = model
    pieces = path.split(LOOKUP_SEP)
    for piece in pieces:
        field, model, direct, m2m = parent._meta.get_field_by_name(piece)
        # skip trailing data field if extant:
        if len(reversed_path) == len(pieces) - 1:  # final iteration
            try:
                get_model_from_relation(field)
            except NotRelationField:
                break
        if direct:
            related_name = field.related_query_name()
            parent = field.rel.to
        else:
            related_name = field.field.name
            parent = field.model
        reversed_path.insert(0, related_name)
    return (parent, LOOKUP_SEP.join(reversed_path))


def get_fields_from_path(model, path):
    """ Return list of Fields given path relative to model.

    e.g. (ModelX, "user__groups__name") -> [
        <django.db.models.fields.related.ForeignKey object at 0x...>,
        <django.db.models.fields.related.ManyToManyField object at 0x...>,
        <django.db.models.fields.CharField object at 0x...>,
    ]
    """
    pieces = path.split(LOOKUP_SEP)
    fields = []
    for piece in pieces:
        if fields:
            parent = get_model_from_relation(fields[-1])
        else:
            parent = model
        fields.append(parent._meta.get_field_by_name(piece)[0])
    return fields


def remove_trailing_data_field(fields):
    """ Discard trailing non-relation field if extant. """
    try:
        get_model_from_relation(fields[-1])
    except NotRelationField:
        fields = fields[:-1]
    return fields


def get_limit_choices_to_from_path(model, path):
    """ Return Q object for limiting choices if applicable.

    If final model in path is linked via a ForeignKey or ManyToManyField which
    has a `limit_choices_to` attribute, return it as a Q object.
    """

    fields = get_fields_from_path(model, path)
    fields = remove_trailing_data_field(fields)
    limit_choices_to = (
        fields and hasattr(fields[-1], 'rel') and
        getattr(fields[-1].rel, 'limit_choices_to', None))
    if not limit_choices_to:
        return models.Q()  # empty Q
    elif isinstance(limit_choices_to, models.Q):
        return limit_choices_to  # already a Q
    else:
        return models.Q(**limit_choices_to)  # convert dict to Q


def sortkeypicker(keynames):
    negate = set()
    for i, k in enumerate(keynames):
        if k[:1] == '-':
            keynames[i] = k[1:]
            negate.add(k[1:])
    def getit(adict):
        composite = [adict[k] for k in keynames]
        for i, (k, v) in enumerate(zip(keynames, composite)):
            if k in negate:
                composite[i] = -v
        return composite
    return getit

########NEW FILE########
__FILENAME__ = vendors

vendors = {
    "bootstrap": {
        'js': {
            'dev': 'xadmin/vendor/bootstrap/js/bootstrap.js',
            'production': 'xadmin/vendor/bootstrap/js/bootstrap.min.js',
            'cdn': 'http://netdna.bootstrapcdn.com/twitter-bootstrap/2.3.1/js/bootstrap.min.js'
        },
        'css': {
            'dev': 'xadmin/vendor/bootstrap/css/bootstrap.css',
            'production': 'xadmin/vendor/bootstrap/css/bootstrap.css',
            'cdn': 'http://netdna.bootstrapcdn.com/twitter-bootstrap/2.3.1/css/bootstrap-combined.min.css'
        },
        'responsive': {'css':{
                'dev': 'xadmin/vendor/bootstrap/bootstrap-responsive.css',
                'production': 'xadmin/vendor/bootstrap/bootstrap-responsive.css'
            }}
    },
    'jquery': {
        "js": {
            'dev': 'xadmin/vendor/jquery/jquery.js',
            'production': 'xadmin/vendor/jquery/jquery.min.js',
        }
    },
    'jquery-ui-effect': {
        "js": {
            'dev': 'xadmin/vendor/jquery-ui/jquery.ui.effect.js',
            'production': 'xadmin/vendor/jquery-ui/jquery.ui.effect.min.js'
        }
    },
    'jquery-ui-sortable': {
        "js": {
            'dev': ['xadmin/vendor/jquery-ui/jquery.ui.core.js', 'xadmin/vendor/jquery-ui/jquery.ui.widget.js',
                    'xadmin/vendor/jquery-ui/jquery.ui.mouse.js', 'xadmin/vendor/jquery-ui/jquery.ui.sortable.js'],
            'production': ['xadmin/vendor/jquery-ui/jquery.ui.core.min.js', 'xadmin/vendor/jquery-ui/jquery.ui.widget.min.js',
                           'xadmin/vendor/jquery-ui/jquery.ui.mouse.min.js', 'xadmin/vendor/jquery-ui/jquery.ui.sortable.min.js']
        }
    },
    "font-awesome": {
        "css": {
            'dev': 'xadmin/vendor/font-awesome/css/font-awesome.css',
            'production': 'xadmin/vendor/font-awesome/css/font-awesome.min.css',
        }
    },
    "timepicker": {
        "css": {
            'dev': 'xadmin/vendor/bootstrap-timepicker/css/bootstrap-timepicker.css',
            'production': 'xadmin/vendor/bootstrap-timepicker/css/bootstrap-timepicker.min.css',
        },
        "js": {
            'dev': 'xadmin/vendor/bootstrap-timepicker/js/bootstrap-timepicker.js',
            'production': 'xadmin/vendor/bootstrap-timepicker/js/bootstrap-timepicker.min.js',
        }
    },
    "datepicker": {
        "css": {
            'dev': 'xadmin/vendor/bootstrap-datepicker/css/datepicker.css'
        },
        "js": {
            'dev': 'xadmin/vendor/bootstrap-datepicker/js/bootstrap-datepicker.js',
        }
    },
    "flot": {
        "js": {
            'dev': ['xadmin/vendor/flot/jquery.flot.js', 'xadmin/vendor/flot/jquery.flot.pie.js', 'xadmin/vendor/flot/jquery.flot.time.js',
                    'xadmin/vendor/flot/jquery.flot.resize.js','xadmin/vendor/flot/jquery.flot.aggregate.js','xadmin/vendor/flot/jquery.flot.categories.js']
        }
    },
    "image-gallery": {
        "css": {
            'dev': 'xadmin/vendor/bootstrap-image-gallery/css/bootstrap-image-gallery.css',
            'production': 'xadmin/vendor/bootstrap-image-gallery/css/bootstrap-image-gallery.css',
        },
        "js": {
            'dev': ['xadmin/vendor/load-image/load-image.js', 'xadmin/vendor/bootstrap-image-gallery/js/bootstrap-image-gallery.js'],
            'production': ['xadmin/vendor/load-image/load-image.min.js', 'xadmin/vendor/bootstrap-image-gallery/js/bootstrap-image-gallery.js']
        }
    },
    "select": {
        "css": {
            'dev': ['xadmin/vendor/select2/select2.css', 'xadmin/vendor/selectize/selectize.css', 'xadmin/vendor/selectize/selectize.bootstrap3.css'],
        },
        "js": {
            'dev': ['xadmin/vendor/selectize/selectize.js', 'xadmin/vendor/select2/select2.js'],
            'production': ['xadmin/vendor/selectize/selectize.min.js', 'xadmin/vendor/select2/select2.min.js']
        }
    },
    "multiselect": {
        "css": {
            'dev': 'xadmin/vendor/bootstrap-multiselect/css/bootstrap-multiselect.css',
        },
        "js": {
            'dev': 'xadmin/vendor/bootstrap-multiselect/js/bootstrap-multiselect.js',
        }
    },
    "snapjs": {
        "css": {
            'dev': 'xadmin/vendor/snapjs/snap.css',
        },
        "js": {
            'dev': 'xadmin/vendor/snapjs/snap.js',
        }
    },
}

########NEW FILE########
__FILENAME__ = base
import sys
import copy
import functools
import datetime
import decimal
from functools import update_wrapper
from inspect import getargspec

from django import forms
from django.utils.encoding import force_unicode
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.template import Context, Template
from django.template.response import TemplateResponse
from django.utils.datastructures import SortedDict
from django.utils.decorators import method_decorator, classonlymethod
from django.utils.encoding import smart_unicode
from django.utils.http import urlencode
from django.utils.itercompat import is_iterable
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic import View
from xadmin.util import static, json, vendor, sortkeypicker


csrf_protect_m = method_decorator(csrf_protect)


class IncorrectPluginArg(Exception):
    pass


def filter_chain(filters, token, func, *args, **kwargs):
    if token == -1:
        return func()
    else:
        def _inner_method():
            fm = filters[token]
            fargs = getargspec(fm)[0]
            if len(fargs) == 1:
                # Only self arg
                result = func()
                if result is None:
                    return fm()
                else:
                    raise IncorrectPluginArg(u'Plugin filter method need a arg to receive parent method result.')
            else:
                return fm(func if fargs[1] == '__' else func(), *args, **kwargs)
        return filter_chain(filters, token - 1, _inner_method, *args, **kwargs)


def filter_hook(func):
    tag = func.__name__
    func.__doc__ = "``filter_hook``\n\n" + (func.__doc__ or "")

    @functools.wraps(func)
    def method(self, *args, **kwargs):

        def _inner_method():
            return func(self, *args, **kwargs)

        if self.plugins:
            filters = [(getattr(getattr(p, tag), 'priority', 10), getattr(p, tag))
                       for p in self.plugins if callable(getattr(p, tag, None))]
            filters = [f for p, f in sorted(filters, key=lambda x:x[0])]
            return filter_chain(filters, len(filters) - 1, _inner_method, *args, **kwargs)
        else:
            return _inner_method()
    return method


def inclusion_tag(file_name, context_class=Context, takes_context=False):
    def wrap(func):
        @functools.wraps(func)
        def method(self, context, nodes, *arg, **kwargs):
            _dict = func(self, context, nodes, *arg, **kwargs)
            from django.template.loader import get_template, select_template
            if isinstance(file_name, Template):
                t = file_name
            elif not isinstance(file_name, basestring) and is_iterable(file_name):
                t = select_template(file_name)
            else:
                t = get_template(file_name)
            new_context = context_class(_dict, **{
                'autoescape': context.autoescape,
                'current_app': context.current_app,
                'use_l10n': context.use_l10n,
                'use_tz': context.use_tz,
            })
            new_context['admin_view'] = context['admin_view']
            csrf_token = context.get('csrf_token', None)
            if csrf_token is not None:
                new_context['csrf_token'] = csrf_token
            nodes.append(t.render(new_context))

        return method
    return wrap


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.date):
            return o.strftime('%Y-%m-%d')
        elif isinstance(o, datetime.datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            try:
                return super(JSONEncoder, self).default(o)
            except Exception:
                return smart_unicode(o)


class BaseAdminObject(object):

    def get_view(self, view_class, option_class=None, *args, **kwargs):
        opts = kwargs.pop('opts', {})
        return self.admin_site.get_view_class(view_class, option_class, **opts)(self.request, *args, **kwargs)

    def get_model_view(self, view_class, model, *args, **kwargs):
        return self.get_view(view_class, self.admin_site._registry.get(model), *args, **kwargs)

    def get_admin_url(self, name, *args, **kwargs):
        return reverse('%s:%s' % (self.admin_site.app_name, name), args=args, kwargs=kwargs)

    def get_model_url(self, model, name, *args, **kwargs):
        return reverse(
            '%s:%s_%s_%s' % (self.admin_site.app_name, model._meta.app_label,
                             model._meta.module_name, name),
            args=args, kwargs=kwargs, current_app=self.admin_site.name)

    def get_model_perm(self, model, name):
        return '%s.%s_%s' % (model._meta.app_label, name, model._meta.module_name)

    def has_model_perm(self, model, name, user=None):
        user = user or self.user
        return user.has_perm(self.get_model_perm(model, name)) or (name == 'view' and self.has_model_perm(model, 'change', user))

    def get_query_string(self, new_params=None, remove=None):
        if new_params is None:
            new_params = {}
        if remove is None:
            remove = []
        p = dict(self.request.GET.items()).copy()
        for r in remove:
            for k in p.keys():
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v
        return '?%s' % urlencode(p)

    def get_form_params(self, new_params=None, remove=None):
        if new_params is None:
            new_params = {}
        if remove is None:
            remove = []
        p = dict(self.request.GET.items()).copy()
        for r in remove:
            for k in p.keys():
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v
        return mark_safe(''.join(
            '<input type="hidden" name="%s" value="%s"/>' % (k, v) for k, v in p.items() if v))

    def render_response(self, content, response_type='json'):
        if response_type == 'json':
            response = HttpResponse(mimetype="application/json; charset=UTF-8")
            response.write(
                json.dumps(content, cls=JSONEncoder, ensure_ascii=False))
            return response
        return HttpResponse(content)

    def template_response(self, template, context):
        return TemplateResponse(self.request, template, context, current_app=self.admin_site.name)

    def message_user(self, message, level='info'):
        """
        Send a message to the user. The default implementation
        posts a message using the django.contrib.messages backend.
        """
        if hasattr(messages, level) and callable(getattr(messages, level)):
            getattr(messages, level)(self.request, message)

    def static(self, path):
        return static(path)

    def vendor(self, *tags):
        return vendor(*tags)


class BaseAdminPlugin(BaseAdminObject):

    def __init__(self, admin_view):
        self.admin_view = admin_view
        self.admin_site = admin_view.admin_site

        if hasattr(admin_view, 'model'):
            self.model = admin_view.model
            self.opts = admin_view.model._meta

    def init_request(self, *args, **kwargs):
        pass


class BaseAdminView(BaseAdminObject, View):
    """ Base Admin view, support some comm attrs."""

    base_template = 'xadmin/base.html'
    need_site_permission = True

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.request_method = request.method.lower()
        self.user = request.user

        self.base_plugins = [p(self) for p in getattr(self,
                                                      "plugin_classes", [])]

        self.args = args
        self.kwargs = kwargs
        self.init_plugin(*args, **kwargs)
        self.init_request(*args, **kwargs)

    @classonlymethod
    def as_view(cls):
        def view(request, *args, **kwargs):
            self = cls(request, *args, **kwargs)

            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get

            if self.request_method in self.http_method_names:
                handler = getattr(
                    self, self.request_method, self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            return handler(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())
        view.need_site_permission = cls.need_site_permission

        return view

    def init_request(self, *args, **kwargs):
        pass

    def init_plugin(self, *args, **kwargs):
        plugins = []
        for p in self.base_plugins:
            p.request = self.request
            p.user = self.user
            p.args = self.args
            p.kwargs = self.kwargs
            result = p.init_request(*args, **kwargs)
            if result is not False:
                plugins.append(p)
        self.plugins = plugins

    @filter_hook
    def get_context(self):
        return {'admin_view': self, 'media': self.media, 'base_template': self.base_template}

    @property
    def media(self):
        return self.get_media()

    @filter_hook
    def get_media(self):
        return forms.Media()


class CommAdminView(BaseAdminView):

    base_template = 'xadmin/base_site.html'
    menu_template = 'xadmin/includes/sitemenu_default.html'

    site_title = None
    global_models_icon = {}
    default_model_icon = None
    apps_label_title = {}
    apps_icons = {}

    def get_site_menu(self):
        return None

    @filter_hook
    def get_nav_menu(self):
        site_menu = list(self.get_site_menu() or [])
        had_urls = []

        def get_url(menu, had_urls):
            if 'url' in menu:
                had_urls.append(menu['url'])
            if 'menus' in menu:
                for m in menu['menus']:
                    get_url(m, had_urls)
        get_url({'menus': site_menu}, had_urls)

        nav_menu = SortedDict()

        for model, model_admin in self.admin_site._registry.items():
            if getattr(model_admin, 'hidden_menu', False):
                continue
            app_label = model._meta.app_label
            app_icon = None
            model_dict = {
                'title': unicode(capfirst(model._meta.verbose_name_plural)),
                'url': self.get_model_url(model, "changelist"),
                'icon': self.get_model_icon(model),
                'perm': self.get_model_perm(model, 'view'),
                'order': model_admin.order,
            }
            if model_dict['url'] in had_urls:
                continue

            app_key = "app:%s" % app_label
            if app_key in nav_menu:
                nav_menu[app_key]['menus'].append(model_dict)
            else:
                # Find app title
                app_title = unicode(app_label.title())
                if app_label.lower() in self.apps_label_title:
                    app_title = self.apps_label_title[app_label.lower()]
                else:
                    mods = model.__module__.split('.')
                    if len(mods) > 1:
                        mod = '.'.join(mods[0:-1])
                        if mod in sys.modules:
                            mod = sys.modules[mod]
                            if 'verbose_name' in dir(mod):
                                app_title = getattr(mod, 'verbose_name')
                            elif 'app_title' in dir(mod):
                                app_title = getattr(mod, 'app_title')
                #find app icon
                if app_label.lower() in self.apps_icons:
                    app_icon = self.apps_icons[app_label.lower()]

                nav_menu[app_key] = {
                    'title': app_title,
                    'menus': [model_dict],
                }

            app_menu = nav_menu[app_key]
            if app_icon:
                app_menu['first_icon'] = app_icon
            elif ('first_icon' not in app_menu or
                    app_menu['first_icon'] == self.default_model_icon) and model_dict.get('icon'):
                app_menu['first_icon'] = model_dict['icon']

            if 'first_url' not in app_menu and model_dict.get('url'):
                app_menu['first_url'] = model_dict['url']

        for menu in nav_menu.values():
            menu['menus'].sort(key=sortkeypicker(['order', 'title']))

        nav_menu = nav_menu.values()
        nav_menu.sort(key=lambda x: x['title'])

        site_menu.extend(nav_menu)

        return site_menu

    @filter_hook
    def get_context(self):
        context = super(CommAdminView, self).get_context()

        if not settings.DEBUG and 'nav_menu' in self.request.session:
            nav_menu = json.loads(self.request.session['nav_menu'])
        else:
            menus = copy.copy(self.get_nav_menu())

            def check_menu_permission(item):
                need_perm = item.pop('perm', None)
                if need_perm is None:
                    return True
                elif callable(need_perm):
                    return need_perm(self.user)
                elif need_perm == 'super':
                    return self.user.is_superuser
                else:
                    return self.user.has_perm(need_perm)

            def filter_item(item):
                if 'menus' in item:
                    item['menus'] = [filter_item(
                        i) for i in item['menus'] if check_menu_permission(i)]
                return item

            nav_menu = [filter_item(item) for item in menus if check_menu_permission(item)]
            nav_menu = filter(lambda i: bool(i['menus']), nav_menu)

            if not settings.DEBUG:
                self.request.session['nav_menu'] = json.dumps(nav_menu)
                self.request.session.modified = True

        def check_selected(menu, path):
            selected = False
            if 'url' in menu:
                chop_index = menu['url'].find('?')
                if chop_index == -1:
                    selected = path.startswith(menu['url'])
                else:
                    selected = path.startswith(menu['url'][:chop_index])
            if 'menus' in menu:
                for m in menu['menus']:
                    _s = check_selected(m, path)
                    if _s:
                        selected = True
            if selected:
                menu['selected'] = True
            return selected
        for menu in nav_menu:
            check_selected(menu, self.request.path)

        context.update({
            'menu_template': self.menu_template,
            'nav_menu': nav_menu,
            'site_title': self.site_title or _(u'Django Xadmin'),
            'breadcrumbs': self.get_breadcrumb()
        })

        return context

    @filter_hook
    def get_model_icon(self, model):
        icon = self.global_models_icon.get(model)
        if icon is None and model in self.admin_site._registry:
            icon = getattr(self.admin_site._registry[model],
                           'model_icon', self.default_model_icon)
        return icon

    @filter_hook
    def get_breadcrumb(self):
        return [{
            'url': self.get_admin_url('index'),
            'title': _('Home')
            }]

class ModelAdminView(CommAdminView):

    fields = None
    exclude = None
    ordering = None
    model = None
    remove_permissions = []

    def __init__(self, request, *args, **kwargs):
        self.opts = self.model._meta
        self.app_label = self.model._meta.app_label
        self.module_name = self.model._meta.module_name
        self.model_info = (self.app_label, self.module_name)

        super(ModelAdminView, self).__init__(request, *args, **kwargs)

    @filter_hook
    def get_context(self):
        new_context = {
            "opts": self.opts,
            "app_label": self.app_label,
            "module_name": self.module_name,
            "verbose_name": force_unicode(self.opts.verbose_name),
            'model_icon': self.get_model_icon(self.model),
        }
        context = super(ModelAdminView, self).get_context()
        context.update(new_context)
        return context

    @filter_hook
    def get_breadcrumb(self):
        bcs = super(ModelAdminView, self).get_breadcrumb()
        item = {'title': self.opts.verbose_name_plural}
        if self.has_view_permission():
            item['url'] = self.model_admin_url('changelist')
        bcs.append(item)
        return bcs

    @filter_hook
    def get_object(self, object_id):
        """
        Get model object instance by object_id, used for change admin view
        """
        # first get base admin view property queryset, return default model queryset
        queryset = self.queryset()
        model = queryset.model
        try:
            object_id = model._meta.pk.to_python(object_id)
            return queryset.get(pk=object_id)
        except (model.DoesNotExist, ValidationError):
            return None

    @filter_hook
    def get_object_url(self, obj):
        if self.has_change_permission(obj):
            return self.model_admin_url("change", getattr(obj, self.opts.pk.attname))
        elif self.has_view_permission(obj):
            return self.model_admin_url("detail", getattr(obj, self.opts.pk.attname))
        else:
            return None

    def model_admin_url(self, name, *args, **kwargs):
        return reverse(
            "%s:%s_%s_%s" % (self.admin_site.app_name, self.opts.app_label,
            self.module_name, name), args=args, kwargs=kwargs)

    def get_model_perms(self):
        """
        Returns a dict of all perms for this model. This dict has the keys
        ``add``, ``change``, and ``delete`` mapping to the True/False for each
        of those actions.
        """
        return {
            'view': self.has_view_permission(),
            'add': self.has_add_permission(),
            'change': self.has_change_permission(),
            'delete': self.has_delete_permission(),
        }

    def get_template_list(self, template_name):
        opts = self.opts
        return (
            "xadmin/%s/%s/%s" % (
                opts.app_label, opts.object_name.lower(), template_name),
            "xadmin/%s/%s" % (opts.app_label, template_name),
            "xadmin/%s" % template_name,
        )

    def get_ordering(self):
        """
        Hook for specifying field ordering.
        """
        return self.ordering or ()  # otherwise we might try to *None, which is bad ;)

    def queryset(self):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        return self.model._default_manager.get_query_set()

    def has_view_permission(self, obj=None):
        return ('view' not in self.remove_permissions) and (self.user.has_perm('%s.view_%s' % self.model_info) or \
            self.user.has_perm('%s.change_%s' % self.model_info))

    def has_add_permission(self):
        return ('add' not in self.remove_permissions) and self.user.has_perm('%s.add_%s' % self.model_info)

    def has_change_permission(self, obj=None):
        return ('change' not in self.remove_permissions) and self.user.has_perm('%s.change_%s' % self.model_info)

    def has_delete_permission(self, obj=None):
        return ('delete' not in self.remove_permissions) and self.user.has_perm('%s.delete_%s' % self.model_info)

########NEW FILE########
__FILENAME__ = dashboard
from django import forms
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db import models
from django.db.models.base import ModelBase
from django.forms.forms import DeclarativeFieldsMetaclass
from django.forms.util import flatatt
from django.template import loader
from django.http import Http404
from django.template.context import RequestContext
from django.test.client import RequestFactory
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.http import urlencode, urlquote
from django.views.decorators.cache import never_cache
from xadmin import widgets as exwidgets
from xadmin.layout import FormHelper
from xadmin.models import UserSettings, UserWidget
from xadmin.sites import site
from xadmin.views.base import CommAdminView, ModelAdminView, filter_hook, csrf_protect_m
from xadmin.views.edit import CreateAdminView
from xadmin.views.list import ListAdminView
from xadmin.util import unquote
import copy


class WidgetTypeSelect(forms.Widget):

    def __init__(self, widgets, attrs=None):
        super(WidgetTypeSelect, self).__init__(attrs)
        self._widgets = widgets

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        final_attrs['class'] = 'nav nav-pills nav-stacked'
        output = [u'<ul%s>' % flatatt(final_attrs)]
        options = self.render_options(force_unicode(value), final_attrs['id'])
        if options:
            output.append(options)
        output.append(u'</ul>')
        output.append('<input type="hidden" id="%s_input" name="%s" value="%s"/>' %
                     (final_attrs['id'], name, force_unicode(value)))
        return mark_safe(u'\n'.join(output))

    def render_option(self, selected_choice, widget, id):
        if widget.widget_type == selected_choice:
            selected_html = u' class="active"'
        else:
            selected_html = ''
        return (u'<li%s><a onclick="' +
                'javascript:$(this).parent().parent().find(\'>li\').removeClass(\'active\');$(this).parent().addClass(\'active\');' +
                '$(\'#%s_input\').attr(\'value\', \'%s\')' % (id, widget.widget_type) +
                '"><h4><i class="%s"></i> %s</h4><p>%s</p></a></li>') % (
                    selected_html,
                    widget.widget_icon,
                    widget.widget_title or widget.widget_type,
                    widget.description)

    def render_options(self, selected_choice, id):
        # Normalize to strings.
        output = []
        for widget in self._widgets:
            output.append(self.render_option(selected_choice, widget, id))
        return u'\n'.join(output)


class UserWidgetAdmin(object):

    model_icon = 'fa fa-dashboard'
    list_display = ('widget_type', 'page_id', 'user')
    list_filter = ['user', 'widget_type', 'page_id']
    list_display_links = ('widget_type',)
    user_fields = ['user']
    hidden_menu = True

    wizard_form_list = (
        (_(u"Widget Type"), ('page_id', 'widget_type')),
        (_(u"Widget Params"), {'callback':
                               "get_widget_params_form", 'convert': "convert_widget_params"})
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'widget_type':
            widgets = widget_manager.get_widgets(self.request.GET.get('page_id', ''))
            form_widget = WidgetTypeSelect(widgets)
            return forms.ChoiceField(choices=[(w.widget_type, w.description) for w in widgets],
                                     widget=form_widget, label=_('Widget Type'))
        if 'page_id' in self.request.GET and db_field.name == 'page_id':
            kwargs['widget'] = forms.HiddenInput
        field = super(
            UserWidgetAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        return field

    def get_widget_params_form(self, wizard):
        data = wizard.get_cleaned_data_for_step(wizard.steps.first)
        widget_type = data['widget_type']
        widget = widget_manager.get(widget_type)
        fields = copy.deepcopy(widget.base_fields)
        if 'id' in fields:
            del fields['id']
        return DeclarativeFieldsMetaclass("WidgetParamsForm", (forms.Form,), fields)

    def convert_widget_params(self, wizard, cleaned_data, form):
        widget = UserWidget()
        value = dict([(f.name, f.value()) for f in form])
        widget.set_value(value)
        cleaned_data['value'] = widget.value
        cleaned_data['user'] = self.user

    def get_list_display(self):
        list_display = super(UserWidgetAdmin, self).get_list_display()
        if not self.user.is_superuser:
            list_display.remove('user')
        return list_display

    def queryset(self):
        if self.user.is_superuser:
            return super(UserWidgetAdmin, self).queryset()
        return UserWidget.objects.filter(user=self.user)

    def update_dashboard(self, obj):
        try:
            portal_pos = UserSettings.objects.get(
                user=obj.user, key="dashboard:%s:pos" % obj.page_id)
        except UserSettings.DoesNotExist:
            return
        pos = [[w for w in col.split(',') if w != str(
            obj.id)] for col in portal_pos.value.split('|')]
        portal_pos.value = '|'.join([','.join(col) for col in pos])
        portal_pos.save()

    def delete_model(self):
        self.update_dashboard(self.obj)
        super(UserWidgetAdmin, self).delete_model()

    def delete_models(self, queryset):
        for obj in queryset:
            self.update_dashboard(obj)
        super(UserWidgetAdmin, self).delete_models(queryset)


site.register(UserWidget, UserWidgetAdmin)


class WidgetManager(object):
    _widgets = None

    def __init__(self):
        self._widgets = {}

    def register(self, widget_class):
        self._widgets[widget_class.widget_type] = widget_class
        return widget_class

    def get(self, name):
        return self._widgets[name]

    def get_widgets(self, page_id):
        return self._widgets.values()

widget_manager = WidgetManager()


class WidgetDataError(Exception):

    def __init__(self, widget, errors):
        super(WidgetDataError, self).__init__(str(errors))
        self.widget = widget
        self.errors = errors


class BaseWidget(forms.Form):

    template = 'xadmin/widgets/base.html'
    description = 'Base Widget, don\'t use it.'
    widget_title = None
    widget_icon = 'fa fa-plus-square'
    widget_type = 'base'
    base_title = None

    id = forms.IntegerField(label=_('Widget ID'), widget=forms.HiddenInput)
    title = forms.CharField(label=_('Widget Title'), required=False, widget=exwidgets.AdminTextInputWidget)

    def __init__(self, dashboard, data):
        self.dashboard = dashboard
        self.admin_site = dashboard.admin_site
        self.request = dashboard.request
        self.user = dashboard.request.user
        self.convert(data)
        super(BaseWidget, self).__init__(data)

        if not self.is_valid():
            raise WidgetDataError(self, self.errors.as_text())

        self.setup()

    def setup(self):
        helper = FormHelper()
        helper.form_tag = False
        self.helper = helper

        self.id = self.cleaned_data['id']
        self.title = self.cleaned_data['title'] or self.base_title

        if not (self.user.is_superuser or self.has_perm()):
            raise PermissionDenied

    @property
    def widget(self):
        context = {'widget_id': self.id, 'widget_title': self.title, 'widget_icon': self.widget_icon,
            'widget_type': self.widget_type, 'form': self, 'widget': self}
        self.context(context)
        return loader.render_to_string(self.template, context, context_instance=RequestContext(self.request))

    def context(self, context):
        pass

    def convert(self, data):
        pass

    def has_perm(self):
        return False

    def save(self):
        value = dict([(f.name, f.value()) for f in self])
        user_widget = UserWidget.objects.get(id=self.id)
        user_widget.set_value(value)
        user_widget.save()

    def static(self, path):
        return self.dashboard.static(path)

    def vendor(self, *tags):
        return self.dashboard.vendor(*tags)

    def media(self):
        return forms.Media()


@widget_manager.register
class HtmlWidget(BaseWidget):
    widget_type = 'html'
    widget_icon = 'fa fa-file-o'
    description = _(
        u'Html Content Widget, can write any html content in widget.')

    content = forms.CharField(label=_(
        'Html Content'), widget=exwidgets.AdminTextareaWidget, required=False)

    def has_perm(self):
        return True

    def context(self, context):
        context['content'] = self.cleaned_data['content']


class ModelChoiceIterator(object):
    def __init__(self, field):
        self.field = field

    def __iter__(self):
        from xadmin import site as g_admin_site
        for m, ma in g_admin_site._registry.items():
            yield ('%s.%s' % (m._meta.app_label, m._meta.module_name),
                   m._meta.verbose_name)


class ModelChoiceField(forms.ChoiceField):

    def __init__(self, required=True, widget=None, label=None, initial=None,
                 help_text=None, *args, **kwargs):
        # Call Field instead of ChoiceField __init__() because we don't need
        # ChoiceField.__init__().
        forms.Field.__init__(self, required, widget, label, initial, help_text,
                             *args, **kwargs)
        self.widget.choices = self.choices

    def __deepcopy__(self, memo):
        result = forms.Field.__deepcopy__(self, memo)
        return result

    def _get_choices(self):
        return ModelChoiceIterator(self)

    choices = property(_get_choices, forms.ChoiceField._set_choices)

    def to_python(self, value):
        if isinstance(value, ModelBase):
            return value
        app_label, model_name = value.lower().split('.')
        return models.get_model(app_label, model_name)

    def prepare_value(self, value):
        if isinstance(value, ModelBase):
            value = '%s.%s' % (value._meta.app_label, value._meta.module_name)
        return value

    def valid_value(self, value):
        value = self.prepare_value(value)
        for k, v in self.choices:
            if value == smart_unicode(k):
                return True
        return False


class ModelBaseWidget(BaseWidget):

    app_label = None
    module_name = None
    model_perm = 'change'
    model = ModelChoiceField(label=_(u'Target Model'), widget=exwidgets.AdminSelectWidget)

    def __init__(self, dashboard, data):
        self.dashboard = dashboard
        super(ModelBaseWidget, self).__init__(dashboard, data)

    def setup(self):
        self.model = self.cleaned_data['model']
        self.app_label = self.model._meta.app_label
        self.module_name = self.model._meta.module_name

        super(ModelBaseWidget, self).setup()

    def has_perm(self):
        return self.dashboard.has_model_perm(self.model, self.model_perm)

    def filte_choices_model(self, model, modeladmin):
        return self.dashboard.has_model_perm(model, self.model_perm)

    def model_admin_url(self, name, *args, **kwargs):
        return reverse(
            "%s:%s_%s_%s" % (self.admin_site.app_name, self.app_label,
            self.module_name, name), args=args, kwargs=kwargs)


class PartialBaseWidget(BaseWidget):

    def get_view_class(self, view_class, model=None, **opts):
        admin_class = self.admin_site._registry.get(model) if model else None
        return self.admin_site.get_view_class(view_class, admin_class, **opts)

    def get_factory(self):
        return RequestFactory()

    def setup_request(self, request):
        request.user = self.user
        request.session = self.request.session
        return request

    def make_get_request(self, path, data={}, **extra):
        req = self.get_factory().get(path, data, **extra)
        return self.setup_request(req)

    def make_post_request(self, path, data={}, **extra):
        req = self.get_factory().post(path, data, **extra)
        return self.setup_request(req)


@widget_manager.register
class QuickBtnWidget(BaseWidget):
    widget_type = 'qbutton'
    description = _(u'Quick button Widget, quickly open any page.')
    template = "xadmin/widgets/qbutton.html"
    base_title = _(u"Quick Buttons")
    widget_icon = 'fa fa-caret-square-o-right'

    def convert(self, data):
        self.q_btns = data.pop('btns', [])

    def get_model(self, model_or_label):
        if isinstance(model_or_label, ModelBase):
            return model_or_label
        else:
            return models.get_model(*model_or_label.lower().split('.'))

    def context(self, context):
        btns = []
        for b in self.q_btns:
            btn = {}
            if 'model' in b:
                model = self.get_model(b['model'])
                if not self.user.has_perm("%s.view_%s" % (model._meta.app_label, model._meta.module_name)):
                    continue
                btn['url'] = reverse("%s:%s_%s_%s" % (self.admin_site.app_name, model._meta.app_label,
                                                      model._meta.module_name, b.get('view', 'changelist')))
                btn['title'] = model._meta.verbose_name
                btn['icon'] = self.dashboard.get_model_icon(model)
            else:
                try:
                    btn['url'] = reverse(b['url'])
                except NoReverseMatch:
                    btn['url'] = b['url']

            if 'title' in b:
                btn['title'] = b['title']
            if 'icon' in b:
                btn['icon'] = b['icon']
            btns.append(btn)

        context.update({'btns': btns})

    def has_perm(self):
        return True


@widget_manager.register
class ListWidget(ModelBaseWidget, PartialBaseWidget):
    widget_type = 'list'
    description = _(u'Any Objects list Widget.')
    template = "xadmin/widgets/list.html"
    model_perm = 'view'
    widget_icon = 'fa fa-align-justify'

    def convert(self, data):
        self.list_params = data.pop('params', {})
        self.list_count = data.pop('count', 10)

    def setup(self):
        super(ListWidget, self).setup()

        if not self.title:
            self.title = self.model._meta.verbose_name_plural

        req = self.make_get_request("", self.list_params)
        self.list_view = self.get_view_class(ListAdminView, self.model)(req)
        if self.list_count:
            self.list_view.list_per_page = self.list_count

    def context(self, context):
        list_view = self.list_view
        list_view.make_result_list()

        base_fields = list_view.base_list_display
        if len(base_fields) > 5:
            base_fields = base_fields[0:5]

        context['result_headers'] = [c for c in list_view.result_headers(
        ).cells if c.field_name in base_fields]
        context['results'] = [[o for i, o in
                               enumerate(filter(lambda c:c.field_name in base_fields, r.cells))]
                              for r in list_view.results()]
        context['result_count'] = list_view.result_count
        context['page_url'] = self.model_admin_url('changelist') + "?" + urlencode(self.list_params)


@widget_manager.register
class AddFormWidget(ModelBaseWidget, PartialBaseWidget):
    widget_type = 'addform'
    description = _(u'Add any model object Widget.')
    template = "xadmin/widgets/addform.html"
    model_perm = 'add'
    widget_icon = 'fa fa-plus'

    def setup(self):
        super(AddFormWidget, self).setup()

        if self.title is None:
            self.title = _('Add %s') % self.model._meta.verbose_name

        req = self.make_get_request("")
        self.add_view = self.get_view_class(
            CreateAdminView, self.model, list_per_page=10)(req)
        self.add_view.instance_forms()

    def context(self, context):
        helper = FormHelper()
        helper.form_tag = False

        context.update({
            'addform': self.add_view.form_obj,
            'addhelper': helper,
            'addurl': self.add_view.model_admin_url('add'),
            'model': self.model
        })

    def media(self):
        return self.add_view.media + self.add_view.form_obj.media + self.vendor('xadmin.plugin.quick-form.js')


class Dashboard(CommAdminView):

    widget_customiz = True
    widgets = []
    title = _(u"Dashboard")
    icon = None

    def get_page_id(self):
        return self.request.path

    def get_portal_key(self):
        return "dashboard:%s:pos" % self.get_page_id()

    @filter_hook
    def get_widget(self, widget_or_id, data=None):
        try:
            if isinstance(widget_or_id, UserWidget):
                widget = widget_or_id
            else:
                widget = UserWidget.objects.get(user=self.user, page_id=self.get_page_id(), id=widget_or_id)
            wid = widget_manager.get(widget.widget_type)

            class widget_with_perm(wid):
                def context(self, context):
                    super(widget_with_perm, self).context(context)
                    context.update({'has_change_permission': self.request.user.has_perm('xadmin.change_userwidget')})
            wid_instance = widget_with_perm(self, data or widget.get_value())
            return wid_instance
        except UserWidget.DoesNotExist:
            return None

    @filter_hook
    def get_init_widget(self):
        portal = []
        widgets = self.widgets
        for col in widgets:
            portal_col = []
            for opts in col:
                try:
                    widget = UserWidget(user=self.user, page_id=self.get_page_id(), widget_type=opts['type'])
                    widget.set_value(opts)
                    widget.save()
                    portal_col.append(self.get_widget(widget))
                except (PermissionDenied, WidgetDataError):
                    widget.delete()
                    continue
            portal.append(portal_col)

        UserSettings(
            user=self.user, key="dashboard:%s:pos" % self.get_page_id(),
            value='|'.join([','.join([str(w.id) for w in col]) for col in portal])).save()

        return portal

    @filter_hook
    def get_widgets(self):

        if self.widget_customiz:
            portal_pos = UserSettings.objects.filter(
                user=self.user, key=self.get_portal_key())
            if len(portal_pos):
                portal_pos = portal_pos[0].value
                widgets = []

                if portal_pos:
                    user_widgets = dict([(uw.id, uw) for uw in UserWidget.objects.filter(user=self.user, page_id=self.get_page_id())])
                    for col in portal_pos.split('|'):
                        ws = []
                        for wid in col.split(','):
                            try:
                                widget = user_widgets.get(int(wid))
                                if widget:
                                    ws.append(self.get_widget(widget))
                            except Exception, e:
                                import logging
                                logging.error(e, exc_info=True)
                        widgets.append(ws)

                return widgets

        return self.get_init_widget()

    @filter_hook
    def get_title(self):
        return self.title

    @filter_hook
    def get_context(self):
        new_context = {
            'title': self.get_title(),
            'icon': self.icon,
            'portal_key': self.get_portal_key(),
            'columns': [('col-sm-%d' % int(12 / len(self.widgets)), ws) for ws in self.widgets],
            'has_add_widget_permission': self.has_model_perm(UserWidget, 'add') and self.widget_customiz,
            'add_widget_url': self.get_admin_url('%s_%s_add' % (UserWidget._meta.app_label, UserWidget._meta.module_name)) +
            "?user=%s&page_id=%s&_redirect=%s" % (self.user.id, self.get_page_id(), urlquote(self.request.get_full_path()))
        }
        context = super(Dashboard, self).get_context()
        context.update(new_context)
        return context

    @never_cache
    def get(self, request, *args, **kwargs):
        self.widgets = self.get_widgets()
        return self.template_response('xadmin/views/dashboard.html', self.get_context())

    @csrf_protect_m
    def post(self, request, *args, **kwargs):
        if 'id' in request.POST:
            widget_id = request.POST['id']
            if request.POST.get('_delete', None) != 'on':
                widget = self.get_widget(widget_id, request.POST.copy())
                widget.save()
            else:
                try:
                    widget = UserWidget.objects.get(
                        user=self.user, page_id=self.get_page_id(), id=widget_id)
                    widget.delete()
                    try:
                        portal_pos = UserSettings.objects.get(user=self.user, key="dashboard:%s:pos" % self.get_page_id())
                        pos = [[w for w in col.split(',') if w != str(
                            widget_id)] for col in portal_pos.value.split('|')]
                        portal_pos.value = '|'.join([','.join(col) for col in pos])
                        portal_pos.save()
                    except Exception:
                        pass
                except UserWidget.DoesNotExist:
                    pass

        return self.get(request)

    @filter_hook
    def get_media(self):
        media = super(Dashboard, self).get_media() + \
            self.vendor('xadmin.page.dashboard.js', 'xadmin.page.dashboard.css')
        if self.widget_customiz:
            media = media + self.vendor('xadmin.plugin.portal.js')
        for ws in self.widgets:
            for widget in ws:
                media = media + widget.media()
        return media


class ModelDashboard(Dashboard, ModelAdminView):

    title = _(u"%s Dashboard")

    def get_page_id(self):
        return 'model:%s/%s' % self.model_info

    @filter_hook
    def get_title(self):
        return self.title % force_unicode(self.obj)

    def init_request(self, object_id, *args, **kwargs):
        self.obj = self.get_object(unquote(object_id))

        if not self.has_view_permission(self.obj):
            raise PermissionDenied

        if self.obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') %
                          {'name': force_unicode(self.opts.verbose_name), 'key': escape(object_id)})

    @filter_hook
    def get_context(self):
        new_context = {
            'has_change_permission': self.has_change_permission(self.obj),
            'object': self.obj,
        }
        context = Dashboard.get_context(self)
        context.update(ModelAdminView.get_context(self))
        context.update(new_context)
        return context

    @never_cache
    def get(self, request, *args, **kwargs):
        self.widgets = self.get_widgets()
        return self.template_response(self.get_template_list('views/model_dashboard.html'), self.get_context())

########NEW FILE########
__FILENAME__ = delete
from django.core.exceptions import PermissionDenied
from django.db import transaction, router
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.utils.translation import ugettext as _
from xadmin.util import unquote, get_deleted_objects

from xadmin.views.edit import UpdateAdminView
from xadmin.views.detail import DetailAdminView
from xadmin.views.base import ModelAdminView, filter_hook, csrf_protect_m


class DeleteAdminView(ModelAdminView):
    delete_confirmation_template = None

    def init_request(self, object_id, *args, **kwargs):
        "The 'delete' admin view for this model."
        self.obj = self.get_object(unquote(object_id))

        if not self.has_delete_permission(self.obj):
            raise PermissionDenied

        if self.obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(self.opts.verbose_name), 'key': escape(object_id)})

        using = router.db_for_write(self.model)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        (self.deleted_objects, self.perms_needed, self.protected) = get_deleted_objects(
            [self.obj], self.opts, self.request.user, self.admin_site, using)

    @csrf_protect_m
    @filter_hook
    def get(self, request, object_id):
        context = self.get_context()

        return TemplateResponse(request, self.delete_confirmation_template or
                                self.get_template_list("views/model_delete_confirm.html"), context, current_app=self.admin_site.name)

    @csrf_protect_m
    @transaction.commit_on_success
    @filter_hook
    def post(self, request, object_id):
        if self.perms_needed:
            raise PermissionDenied

        self.delete_model()

        response = self.post_response()
        if isinstance(response, basestring):
            return HttpResponseRedirect(response)
        else:
            return response

    @filter_hook
    def delete_model(self):
        """
        Given a model instance delete it from the database.
        """
        self.obj.delete()

    @filter_hook
    def get_context(self):
        if self.perms_needed or self.protected:
            title = _("Cannot delete %(name)s") % {"name":
                                                   force_unicode(self.opts.verbose_name)}
        else:
            title = _("Are you sure?")

        new_context = {
            "title": title,
            "object": self.obj,
            "deleted_objects": self.deleted_objects,
            "perms_lacking": self.perms_needed,
            "protected": self.protected,
        }
        context = super(DeleteAdminView, self).get_context()
        context.update(new_context)
        return context

    @filter_hook
    def get_breadcrumb(self):
        bcs = super(DeleteAdminView, self).get_breadcrumb()
        bcs.append({
            'title': force_unicode(self.obj),
            'url': self.get_object_url(self.obj)
        })
        item = {'title': _('Delete')}
        if self.has_delete_permission():
            item['url'] = self.model_admin_url('delete', self.obj.pk)
        bcs.append(item)

        return bcs

    @filter_hook
    def post_response(self):

        self.message_user(_('The %(name)s "%(obj)s" was deleted successfully.') %
                          {'name': force_unicode(self.opts.verbose_name), 'obj': force_unicode(self.obj)}, 'success')

        if not self.has_view_permission():
            return self.get_admin_url('index')
        return self.model_admin_url('changelist')

########NEW FILE########
__FILENAME__ = detail
import copy

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import models
from django.forms.models import modelform_factory
from django.http import Http404
from django.template import loader
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.html import conditional_escape
from xadmin.layout import FormHelper, Layout, Fieldset, Container, Column, Field, Col, TabHolder
from xadmin.util import unquote, lookup_field, display_for_field, boolean_icon, label_for_field

from base import ModelAdminView, filter_hook, csrf_protect_m

# Text to display within change-list table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = _('Null')


class ShowField(Field):
    template = "xadmin/layout/field_value.html"

    def __init__(self, callback, *args, **kwargs):
        super(ShowField, self).__init__(*args)

        if 'attrs' in kwargs:
            self.attrs = kwargs.pop('attrs')
        if 'wrapper_class' in kwargs:
            self.wrapper_class = kwargs.pop('wrapper_class')

        self.results = [(field, callback(field)) for field in self.fields]

    def render(self, form, form_style, context):
        if hasattr(self, 'wrapper_class'):
            context['wrapper_class'] = self.wrapper_class

        if self.attrs:
            if 'detail-class' in self.attrs:
                context['input_class'] = self.attrs['detail-class']
            elif 'class' in self.attrs:
                context['input_class'] = self.attrs['class']

        html = ''
        for field, result in self.results:
            context['result'] = result
            if field in form.fields:
                if form.fields[field].widget != forms.HiddenInput:
                    context['field'] = form[field]
                    html += loader.render_to_string(self.template, context)
            else:
                context['field'] = field
                html += loader.render_to_string(self.template, context)
        return html


class ResultField(object):

    def __init__(self, obj, field_name, admin_view=None):
        self.text = '&nbsp;'
        self.wraps = []
        self.allow_tags = False
        self.obj = obj
        self.admin_view = admin_view
        self.field_name = field_name
        self.field = None
        self.attr = None
        self.label = None
        self.value = None

        self.init()

    def init(self):
        self.label = label_for_field(self.field_name, self.obj.__class__,
                                     model_admin=self.admin_view,
                                     return_attr=False
                                     )
        try:
            f, attr, value = lookup_field(
                self.field_name, self.obj, self.admin_view)
        except (AttributeError, ObjectDoesNotExist):
            self.text
        else:
            if f is None:
                self.allow_tags = getattr(attr, 'allow_tags', False)
                boolean = getattr(attr, 'boolean', False)
                if boolean:
                    self.allow_tags = True
                    self.text = boolean_icon(value)
                else:
                    self.text = smart_unicode(value)
            else:
                if isinstance(f.rel, models.ManyToOneRel):
                    self.text = getattr(self.obj, f.name)
                else:
                    self.text = display_for_field(value, f)
            self.field = f
            self.attr = attr
            self.value = value

    @property
    def val(self):
        text = mark_safe(
            self.text) if self.allow_tags else conditional_escape(self.text)
        if force_unicode(text) == '' or text == 'None' or text == EMPTY_CHANGELIST_VALUE:
            text = mark_safe(
                '<span class="text-muted">%s</span>' % EMPTY_CHANGELIST_VALUE)
        for wrap in self.wraps:
            text = mark_safe(wrap % text)
        return text


def replace_field_to_value(layout, cb):
    for i, lo in enumerate(layout.fields):
        if isinstance(lo, Field) or issubclass(lo.__class__, Field):
            layout.fields[i] = ShowField(
                cb, *lo.fields, attrs=lo.attrs, wrapper_class=lo.wrapper_class)
        elif isinstance(lo, basestring):
            layout.fields[i] = ShowField(cb, lo)
        elif hasattr(lo, 'get_field_names'):
            replace_field_to_value(lo, cb)


class DetailAdminView(ModelAdminView):

    form = forms.ModelForm
    detail_layout = None
    detail_show_all = True
    detail_template = None
    form_layout = None

    def init_request(self, object_id, *args, **kwargs):
        self.obj = self.get_object(unquote(object_id))

        if not self.has_view_permission(self.obj):
            raise PermissionDenied

        if self.obj is None:
            raise Http404(
                _('%(name)s object with primary key %(key)r does not exist.') %
                {'name': force_unicode(self.opts.verbose_name), 'key': escape(object_id)})
        self.org_obj = self.obj

    @filter_hook
    def get_form_layout(self):
        layout = copy.deepcopy(self.detail_layout or self.form_layout)

        if layout is None:
            layout = Layout(Container(Col('full',
                                          Fieldset(
                                              "", *self.form_obj.fields.keys(),
                                              css_class="unsort no_title"), horizontal=True, span=12)
                                      ))
        elif type(layout) in (list, tuple) and len(layout) > 0:
            if isinstance(layout[0], Column):
                fs = layout
            elif isinstance(layout[0], (Fieldset, TabHolder)):
                fs = (Col('full', *layout, horizontal=True, span=12),)
            else:
                fs = (
                    Col('full', Fieldset("", *layout, css_class="unsort no_title"), horizontal=True, span=12),)

            layout = Layout(Container(*fs))

            if self.detail_show_all:
                rendered_fields = [i[1] for i in layout.get_field_names()]
                container = layout[0].fields
                other_fieldset = Fieldset(_(u'Other Fields'), *[
                                          f for f in self.form_obj.fields.keys() if f not in rendered_fields])

                if len(other_fieldset.fields):
                    if len(container) and isinstance(container[0], Column):
                        container[0].fields.append(other_fieldset)
                    else:
                        container.append(other_fieldset)

        return layout

    @filter_hook
    def get_model_form(self, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # ModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        # if exclude is an empty list we pass None to be consistant with the
        # default on modelform_factory
        exclude = exclude or None
        defaults = {
            "form": self.form,
            "fields": self.fields and list(self.fields) or None,
            "exclude": exclude,
        }
        defaults.update(kwargs)
        return modelform_factory(self.model, **defaults)

    @filter_hook
    def get_form_helper(self):
        helper = FormHelper()
        helper.form_tag = False
        layout = self.get_form_layout()
        replace_field_to_value(layout, self.get_field_result)
        helper.add_layout(layout)
        helper.filter(
            basestring, max_level=20).wrap(ShowField, admin_view=self)
        return helper

    @csrf_protect_m
    @filter_hook
    def get(self, request, *args, **kwargs):
        form = self.get_model_form()
        self.form_obj = form(instance=self.obj)
        helper = self.get_form_helper()
        if helper:
            self.form_obj.helper = helper

        return self.get_response()

    @filter_hook
    def get_context(self):
        new_context = {
            'title': _('%s Detail') % force_unicode(self.opts.verbose_name),
            'form': self.form_obj,

            'object': self.obj,

            'has_change_permission': self.has_change_permission(self.obj),
            'has_delete_permission': self.has_delete_permission(self.obj),

            'content_type_id': ContentType.objects.get_for_model(self.model).id,
        }

        context = super(DetailAdminView, self).get_context()
        context.update(new_context)
        return context

    @filter_hook
    def get_breadcrumb(self):
        bcs = super(DetailAdminView, self).get_breadcrumb()
        item = {'title': force_unicode(self.obj)}
        if self.has_view_permission():
            item['url'] = self.model_admin_url('detail', self.obj.pk)
        bcs.append(item)
        return bcs

    @filter_hook
    def get_media(self):
        media = super(DetailAdminView, self).get_media()
        media = media + self.form_obj.media
        media.add_css({'screen': [self.static('xadmin/css/xadmin.form.css')]})
        return media

    @filter_hook
    def get_field_result(self, field_name):
        return ResultField(self.obj, field_name, self)

    @filter_hook
    def get_response(self, *args, **kwargs):
        context = self.get_context()
        context.update(kwargs or {})

        return TemplateResponse(self.request, self.detail_template or
                                self.get_template_list(
                                    'views/model_detail.html'),
                                context, current_app=self.admin_site.name)


class DetailAdminUtil(DetailAdminView):

    def init_request(self, obj):
        self.obj = obj
        self.org_obj = obj

########NEW FILE########
__FILENAME__ = edit
import copy

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.template import loader
from django.utils.translation import ugettext as _
from xadmin import widgets
from xadmin.layout import FormHelper, Layout, Fieldset, TabHolder, Container, Column, Col, Field
from xadmin.util import unquote
from xadmin.views.detail import DetailAdminUtil

from base import ModelAdminView, filter_hook, csrf_protect_m


FORMFIELD_FOR_DBFIELD_DEFAULTS = {
    models.DateTimeField: {
        'form_class': forms.SplitDateTimeField,
        'widget': widgets.AdminSplitDateTime
    },
    models.DateField: {'widget': widgets.AdminDateWidget},
    models.TimeField: {'widget': widgets.AdminTimeWidget},
    models.TextField: {'widget': widgets.AdminTextareaWidget},
    models.URLField: {'widget': widgets.AdminURLFieldWidget},
    models.IntegerField: {'widget': widgets.AdminIntegerFieldWidget},
    models.BigIntegerField: {'widget': widgets.AdminIntegerFieldWidget},
    models.CharField: {'widget': widgets.AdminTextInputWidget},
    models.IPAddressField: {'widget': widgets.AdminTextInputWidget},
    models.ImageField: {'widget': widgets.AdminFileWidget},
    models.FileField: {'widget': widgets.AdminFileWidget},
    models.ForeignKey: {'widget': widgets.AdminSelectWidget},
    models.OneToOneField: {'widget': widgets.AdminSelectWidget},
    models.ManyToManyField: {'widget': widgets.AdminSelectMultiple},
}


class ReadOnlyField(Field):
    template = "xadmin/layout/field_value.html"

    def __init__(self, *args, **kwargs):
        self.detail = kwargs.pop('detail')
        super(ReadOnlyField, self).__init__(*args, **kwargs)

    def render(self, form, form_style, context):
        html = ''
        for field in self.fields:
            result = self.detail.get_field_result(field)
            field = {'auto_id': field}
            html += loader.render_to_string(
                self.template, {'field': field, 'result': result})
        return html


class ModelFormAdminView(ModelAdminView):
    form = forms.ModelForm
    formfield_overrides = {}
    readonly_fields = ()
    style_fields = {}
    exclude = None
    relfield_style = None

    save_as = False
    save_on_top = False

    add_form_template = None
    change_form_template = None

    form_layout = None

    def __init__(self, request, *args, **kwargs):
        overrides = FORMFIELD_FOR_DBFIELD_DEFAULTS.copy()
        overrides.update(self.formfield_overrides)
        self.formfield_overrides = overrides
        super(ModelFormAdminView, self).__init__(request, *args, **kwargs)

    @filter_hook
    def formfield_for_dbfield(self, db_field, **kwargs):
        # If it uses an intermediary model that isn't auto created, don't show
        # a field in admin.
        if isinstance(db_field, models.ManyToManyField) and not db_field.rel.through._meta.auto_created:
            return None

        attrs = self.get_field_attrs(db_field, **kwargs)
        return db_field.formfield(**dict(attrs, **kwargs))

    @filter_hook
    def get_field_style(self, db_field, style, **kwargs):
        if style in ('radio', 'radio-inline') and (db_field.choices or isinstance(db_field, models.ForeignKey)):
            attrs = {'widget': widgets.AdminRadioSelect(
                attrs={'inline': style == 'radio-inline'})}
            if db_field.choices:
                attrs['choices'] = db_field.get_choices(
                    include_blank=db_field.blank,
                    blank_choice=[('', _('Null'))]
                )
            return attrs

        if style in ('checkbox', 'checkbox-inline') and isinstance(db_field, models.ManyToManyField):
            return {'widget': widgets.AdminCheckboxSelect(attrs={'inline': style == 'checkbox-inline'}),
                    'help_text': None}

    @filter_hook
    def get_field_attrs(self, db_field, **kwargs):

        if db_field.name in self.style_fields:
            attrs = self.get_field_style(
                db_field, self.style_fields[db_field.name], **kwargs)
            if attrs:
                return attrs

        if hasattr(db_field, "rel") and db_field.rel:
            related_modeladmin = self.admin_site._registry.get(db_field.rel.to)
            if related_modeladmin and hasattr(related_modeladmin, 'relfield_style'):
                attrs = self.get_field_style(
                    db_field, related_modeladmin.relfield_style, **kwargs)
                if attrs:
                    return attrs

        if db_field.choices:
            return {'widget': widgets.AdminSelectWidget}

        for klass in db_field.__class__.mro():
            if klass in self.formfield_overrides:
                return self.formfield_overrides[klass].copy()

        return {}

    @filter_hook
    def prepare_form(self):
        self.model_form = self.get_model_form()

    @filter_hook
    def instance_forms(self):
        self.form_obj = self.model_form(**self.get_form_datas())

    def setup_forms(self):
        helper = self.get_form_helper()
        if helper:
            self.form_obj.helper = helper

    @filter_hook
    def valid_forms(self):
        return self.form_obj.is_valid()

    @filter_hook
    def get_model_form(self, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(self.get_readonly_fields())
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            # Take the custom ModelForm's Meta.exclude into account only if the
            # ModelAdmin doesn't define its own.
            exclude.extend(self.form._meta.exclude)
        # if exclude is an empty list we pass None to be consistant with the
        # default on modelform_factory
        exclude = exclude or None
        defaults = {
            "form": self.form,
            "fields": self.fields and list(self.fields) or None,
            "exclude": exclude,
            "formfield_callback": self.formfield_for_dbfield,
        }
        defaults.update(kwargs)
        return modelform_factory(self.model, **defaults)

    @filter_hook
    def get_form_layout(self):
        layout = copy.deepcopy(self.form_layout)
        fields = self.form_obj.fields.keys() + list(self.get_readonly_fields())

        if layout is None:
            layout = Layout(Container(Col('full',
                Fieldset("", *fields, css_class="unsort no_title"), horizontal=True, span=12)
            ))
        elif type(layout) in (list, tuple) and len(layout) > 0:
            if isinstance(layout[0], Column):
                fs = layout
            elif isinstance(layout[0], (Fieldset, TabHolder)):
                fs = (Col('full', *layout, horizontal=True, span=12),)
            else:
                fs = (Col('full', Fieldset("", *layout, css_class="unsort no_title"), horizontal=True, span=12),)

            layout = Layout(Container(*fs))

            rendered_fields = [i[1] for i in layout.get_field_names()]
            container = layout[0].fields
            other_fieldset = Fieldset(_(u'Other Fields'), *[f for f in fields if f not in rendered_fields])

            if len(other_fieldset.fields):
                if len(container) and isinstance(container[0], Column):
                    container[0].fields.append(other_fieldset)
                else:
                    container.append(other_fieldset)

        return layout

    @filter_hook
    def get_form_helper(self):
        helper = FormHelper()
        helper.form_tag = False
        helper.add_layout(self.get_form_layout())

        # deal with readonly fields
        readonly_fields = self.get_readonly_fields()
        if readonly_fields:
            detail = self.get_model_view(
                DetailAdminUtil, self.model, self.form_obj.instance)
            for field in readonly_fields:
                helper[field].wrap(ReadOnlyField, detail=detail)

        return helper

    @filter_hook
    def get_readonly_fields(self):
        """
        Hook for specifying custom readonly fields.
        """
        return self.readonly_fields

    @filter_hook
    def save_forms(self):
        self.new_obj = self.form_obj.save(commit=False)

    @filter_hook
    def save_models(self):
        self.new_obj.save()

    @filter_hook
    def save_related(self):
        self.form_obj.save_m2m()

    @csrf_protect_m
    @filter_hook
    def get(self, request, *args, **kwargs):
        self.instance_forms()
        self.setup_forms()

        return self.get_response()

    @csrf_protect_m
    @transaction.commit_on_success
    @filter_hook
    def post(self, request, *args, **kwargs):
        self.instance_forms()
        self.setup_forms()

        if self.valid_forms():
            self.save_forms()
            self.save_models()
            self.save_related()
            response = self.post_response()
            if isinstance(response, basestring):
                return HttpResponseRedirect(response)
            else:
                return response

        return self.get_response()

    @filter_hook
    def get_context(self):
        add = self.org_obj is None
        change = self.org_obj is not None

        new_context = {
            'form': self.form_obj,
            'original': self.org_obj,
            'show_delete': self.org_obj is not None,
            'add': add,
            'change': change,
            'errors': self.get_error_list(),

            'has_add_permission': self.has_add_permission(),
            'has_view_permission': self.has_view_permission(),
            'has_change_permission': self.has_change_permission(self.org_obj),
            'has_delete_permission': self.has_delete_permission(self.org_obj),

            'has_file_field': True,  # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'form_url': '',
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
        }

        # for submit line
        new_context.update({
            'onclick_attrib': '',
            'show_delete_link': (new_context['has_delete_permission']
                                 and (change or new_context['show_delete'])),
            'show_save_as_new': change and self.save_as,
            'show_save_and_add_another': new_context['has_add_permission'] and
                                (not self.save_as or add),
            'show_save_and_continue': new_context['has_change_permission'],
            'show_save': True
        })

        if self.org_obj and new_context['show_delete_link']:
            new_context['delete_url'] = self.model_admin_url(
                'delete', self.org_obj.pk)

        context = super(ModelFormAdminView, self).get_context()
        context.update(new_context)
        return context

    @filter_hook
    def get_error_list(self):
        errors = forms.util.ErrorList()
        if self.form_obj.is_bound:
            errors.extend(self.form_obj.errors.values())
        return errors

    @filter_hook
    def get_media(self):
        return super(ModelFormAdminView, self).get_media() + self.form_obj.media + \
            self.vendor('xadmin.page.form.js', 'xadmin.form.css')


class CreateAdminView(ModelFormAdminView):

    def init_request(self, *args, **kwargs):
        self.org_obj = None

        if not self.has_add_permission():
            raise PermissionDenied

        # comm method for both get and post
        self.prepare_form()

    @filter_hook
    def get_form_datas(self):
        # Prepare the dict of initial data from the request.
        # We have to special-case M2Ms as a list of comma-separated PKs.
        if self.request_method == 'get':
            initial = dict(self.request.GET.items())
            for k in initial:
                try:
                    f = self.opts.get_field(k)
                except models.FieldDoesNotExist:
                    continue
                if isinstance(f, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            return {'initial': initial}
        else:
            return {'data': self.request.POST, 'files': self.request.FILES}

    @filter_hook
    def get_context(self):
        new_context = {
            'title': _('Add %s') % force_unicode(self.opts.verbose_name),
        }
        context = super(CreateAdminView, self).get_context()
        context.update(new_context)
        return context

    @filter_hook
    def get_breadcrumb(self):
        bcs = super(ModelFormAdminView, self).get_breadcrumb()
        item = {'title': _('Add %s') % force_unicode(self.opts.verbose_name)}
        if self.has_add_permission():
            item['url'] = self.model_admin_url('add')
        bcs.append(item)
        return bcs

    @filter_hook
    def get_response(self):
        context = self.get_context()
        context.update(self.kwargs or {})

        return TemplateResponse(
            self.request, self.add_form_template or self.get_template_list(
                'views/model_form.html'),
            context, current_app=self.admin_site.name)

    @filter_hook
    def post_response(self):
        """
        Determines the HttpResponse for the add_view stage.
        """
        request = self.request

        msg = _(
            'The %(name)s "%(obj)s" was added successfully.') % {'name': force_unicode(self.opts.verbose_name),
                                                                 'obj': "<a class='alert-link' href='%s'>%s</a>" % (self.model_admin_url('change', self.new_obj._get_pk_val()), force_unicode(self.new_obj))}

        if "_continue" in request.REQUEST:
            self.message_user(
                msg + ' ' + _("You may edit it again below."), 'success')
            return self.model_admin_url('change', self.new_obj._get_pk_val())

        if "_addanother" in request.REQUEST:
            self.message_user(msg + ' ' + (_("You may add another %s below.") % force_unicode(self.opts.verbose_name)), 'success')
            return request.path
        else:
            self.message_user(msg, 'success')

            # Figure out where to redirect. If the user has change permission,
            # redirect to the change-list page for this object. Otherwise,
            # redirect to the admin index.
            if "_redirect" in request.REQUEST:
                return request.REQUEST["_redirect"]
            elif self.has_view_permission():
                return self.model_admin_url('changelist')
            else:
                return self.get_admin_url('index')


class UpdateAdminView(ModelFormAdminView):

    def init_request(self, object_id, *args, **kwargs):
        self.org_obj = self.get_object(unquote(object_id))

        if not self.has_change_permission(self.org_obj):
            raise PermissionDenied

        if self.org_obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') %
                          {'name': force_unicode(self.opts.verbose_name), 'key': escape(object_id)})

        # comm method for both get and post
        self.prepare_form()

    @filter_hook
    def get_form_datas(self):
        params = {'instance': self.org_obj}
        if self.request_method == 'post':
            params.update(
                {'data': self.request.POST, 'files': self.request.FILES})
        return params

    @filter_hook
    def get_context(self):
        new_context = {
            'title': _('Change %s') % force_unicode(self.org_obj),
            'object_id': str(self.org_obj.pk),
        }
        context = super(UpdateAdminView, self).get_context()
        context.update(new_context)
        return context

    @filter_hook
    def get_breadcrumb(self):
        bcs = super(ModelFormAdminView, self).get_breadcrumb()

        item = {'title': force_unicode(self.org_obj)}
        if self.has_change_permission():
            item['url'] = self.model_admin_url('change', self.org_obj.pk)
        bcs.append(item)

        return bcs

    @filter_hook
    def get_response(self, *args, **kwargs):
        context = self.get_context()
        context.update(kwargs or {})

        return TemplateResponse(
            self.request, self.change_form_template or self.get_template_list(
                'views/model_form.html'),
            context, current_app=self.admin_site.name)

    def post(self, request, *args, **kwargs):
        if "_saveasnew" in self.request.REQUEST:
            return self.get_model_view(CreateAdminView, self.model).post(request)
        return super(UpdateAdminView, self).post(request, *args, **kwargs)

    @filter_hook
    def post_response(self):
        """
        Determines the HttpResponse for the change_view stage.
        """
        opts = self.new_obj._meta
        obj = self.new_obj
        request = self.request
        verbose_name = opts.verbose_name

        pk_value = obj._get_pk_val()

        msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name':
                                                                       force_unicode(verbose_name), 'obj': force_unicode(obj)}
        if "_continue" in request.REQUEST:
            self.message_user(
                msg + ' ' + _("You may edit it again below."), 'success')
            return request.path
        elif "_addanother" in request.REQUEST:
            self.message_user(msg + ' ' + (_("You may add another %s below.")
                              % force_unicode(verbose_name)), 'success')
            return self.model_admin_url('add')
        else:
            self.message_user(msg, 'success')
            # Figure out where to redirect. If the user has change permission,
            # redirect to the change-list page for this object. Otherwise,
            # redirect to the admin index.
            if "_redirect" in request.REQUEST:
                return request.REQUEST["_redirect"]
            elif self.has_view_permission():
                change_list_url = self.model_admin_url('changelist')
                if 'LIST_QUERY' in self.request.session \
                and self.request.session['LIST_QUERY'][0] == self.model_info:
                    change_list_url += '?' + self.request.session['LIST_QUERY'][1]
                return change_list_url
            else:
                return self.get_admin_url('index')


class ModelFormAdminUtil(ModelFormAdminView):

    def init_request(self, obj=None):
        self.org_obj = obj
        self.prepare_form()
        self.instance_forms()

    @filter_hook
    def get_form_datas(self):
        return {'instance': self.org_obj}

########NEW FILE########
__FILENAME__ = form
import copy

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.template import loader
from django.utils.translation import ugettext as _
from xadmin import widgets
from xadmin.layout import FormHelper, Layout, Fieldset, TabHolder, Container, Column, Col, Field
from xadmin.util import unquote
from xadmin.views.detail import DetailAdminUtil

from base import CommAdminView, filter_hook, csrf_protect_m

class FormAdminView(CommAdminView):
    form = forms.ModelForm
    title = None
    readonly_fields = ()

    form_template = 'xadmin/views/form.html'

    form_layout = None

    def init_request(self, *args, **kwargs):
        # comm method for both get and post
        self.prepare_form()

    @filter_hook
    def prepare_form(self):
        self.view_form = self.form

    @filter_hook
    def instance_forms(self):
        self.form_obj = self.view_form(**self.get_form_datas())

    def setup_forms(self):
        helper = self.get_form_helper()
        if helper:
            self.form_obj.helper = helper

    @filter_hook
    def valid_forms(self):
        return self.form_obj.is_valid()

    @filter_hook
    def get_form_layout(self):
        layout = copy.deepcopy(self.form_layout)
        fields = self.form_obj.fields.keys()

        if layout is None:
            layout = Layout(Container(Col('full',
                Fieldset("", *fields, css_class="unsort no_title"), horizontal=True, span=12)
            ))
        elif type(layout) in (list, tuple) and len(layout) > 0:
            if isinstance(layout[0], Column):
                fs = layout
            elif isinstance(layout[0], (Fieldset, TabHolder)):
                fs = (Col('full', *layout, horizontal=True, span=12),)
            else:
                fs = (Col('full', Fieldset("", *layout, css_class="unsort no_title"), horizontal=True, span=12),)

            layout = Layout(Container(*fs))

            rendered_fields = [i[1] for i in layout.get_field_names()]
            container = layout[0].fields
            other_fieldset = Fieldset(_(u'Other Fields'), *[f for f in fields if f not in rendered_fields])

            if len(other_fieldset.fields):
                if len(container) and isinstance(container[0], Column):
                    container[0].fields.append(other_fieldset)
                else:
                    container.append(other_fieldset)

        return layout

    @filter_hook
    def get_form_helper(self):
        helper = FormHelper()
        helper.form_tag = False
        helper.add_layout(self.get_form_layout())

        return helper

    @filter_hook
    def save_forms(self):
        pass

    @csrf_protect_m
    @filter_hook
    def get(self, request, *args, **kwargs):
        self.instance_forms()
        self.setup_forms()

        return self.get_response()

    @csrf_protect_m
    @transaction.commit_on_success
    @filter_hook
    def post(self, request, *args, **kwargs):
        self.instance_forms()
        self.setup_forms()

        if self.valid_forms():
            self.save_forms()
            response = self.post_response()
            if isinstance(response, basestring):
                return HttpResponseRedirect(response)
            else:
                return response

        return self.get_response()

    @filter_hook
    def get_context(self):
        context = super(FormAdminView, self).get_context()
        context.update({
            'form': self.form_obj,
            'title': self.title,
        })
        return context

    @filter_hook
    def get_media(self):
        return super(FormAdminView, self).get_media() + self.form_obj.media + \
            self.vendor('xadmin.page.form.js', 'xadmin.form.css')

    def get_initial_data(self):
        return {}

    @filter_hook
    def get_form_datas(self):
        data = {'initial': self.get_initial_data()}
        if self.request_method == 'get':
            data['initial'].update(self.request.GET)
        else:
            data.update({'data': self.request.POST, 'files': self.request.FILES})
        return data

    @filter_hook
    def get_breadcrumb(self):
        bcs = super(FormAdminView, self).get_breadcrumb()
        bcs.append({'title': self.title})
        return bcs

    @filter_hook
    def get_response(self):
        context = self.get_context()
        context.update(self.kwargs or {})

        return TemplateResponse(
            self.request, self.form_template,
            context, current_app=self.admin_site.name)

    @filter_hook
    def post_response(self):
        request = self.request

        msg = _('The %s was changed successfully.') % self.title
        self.message_user(msg, 'success')

        if "_redirect" in request.REQUEST:
            return request.REQUEST["_redirect"]
        else:
            return self.get_redirect_url()

    @filter_hook
    def get_redirect_url(self):
        return self.get_admin_url('index')

########NEW FILE########
__FILENAME__ = list
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.paginator import InvalidPage, Paginator
from django.db import models
from django.http import HttpResponseRedirect
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape, conditional_escape
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from xadmin.util import lookup_field, display_for_field, label_for_field, boolean_icon

from base import ModelAdminView, filter_hook, inclusion_tag, csrf_protect_m

# List settings
ALL_VAR = 'all'
ORDER_VAR = 'o'
PAGE_VAR = 'p'
TO_FIELD_VAR = 't'
COL_LIST_VAR = '_cols'
ERROR_FLAG = 'e'

DOT = '.'

# Text to display within change-list table cells if the value is blank.
EMPTY_CHANGELIST_VALUE = _('Null')


class FakeMethodField(object):
    """
    This class used when a column is an model function, wrap function as a fake field to display in select columns.
    """
    def __init__(self, name, verbose_name):
        # Initial comm field attrs
        self.name = name
        self.verbose_name = verbose_name
        self.primary_key = False


class ResultRow(dict):
    pass


class ResultItem(object):

    def __init__(self, field_name, row):
        self.classes = []
        self.text = '&nbsp;'
        self.wraps = []
        self.tag = 'td'
        self.tag_attrs = []
        self.allow_tags = False
        self.btns = []
        self.menus = []
        self.is_display_link = False
        self.row = row
        self.field_name = field_name
        self.field = None
        self.attr = None
        self.value = None

    @property
    def label(self):
        text = mark_safe(
            self.text) if self.allow_tags else conditional_escape(self.text)
        if force_unicode(text) == '':
            text = mark_safe('&nbsp;')
        for wrap in self.wraps:
            text = mark_safe(wrap % text)
        return text

    @property
    def tagattrs(self):
        return mark_safe(
            '%s%s' % ((self.tag_attrs and ' '.join(self.tag_attrs) or ''),
            (self.classes and (' class="%s"' % ' '.join(self.classes)) or '')))


class ResultHeader(ResultItem):

    def __init__(self, field_name, row):
        super(ResultHeader, self).__init__(field_name, row)
        self.tag = 'th'
        self.tag_attrs = ['scope="col"']
        self.sortable = False
        self.allow_tags = True
        self.sorted = False
        self.ascending = None
        self.sort_priority = None
        self.url_primary = None
        self.url_remove = None
        self.url_toggle = None


class ListAdminView(ModelAdminView):
    """
    Display models objects view. this class has ordering and simple filter features.
    """
    list_display = ('__str__',)
    list_display_links = ()
    list_display_links_details = False
    list_select_related = None
    list_per_page = 50
    list_max_show_all = 200
    list_exclude = ()
    search_fields = ()
    paginator_class = Paginator
    ordering = None

    # Change list templates
    object_list_template = None

    def init_request(self, *args, **kwargs):

        if not self.has_view_permission():
            raise PermissionDenied

        request = self.request
        request.session['LIST_QUERY'] = (self.model_info, self.request.META['QUERY_STRING'])

        self.pk_attname = self.opts.pk.attname
        self.lookup_opts = self.opts
        self.list_display = self.get_list_display()
        self.list_display_links = self.get_list_display_links()

        # Get page number parameters from the query string.
        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 0))
        except ValueError:
            self.page_num = 0

        # Get params from request
        self.show_all = ALL_VAR in request.GET
        self.to_field = request.GET.get(TO_FIELD_VAR)
        self.params = dict(request.GET.items())

        if PAGE_VAR in self.params:
            del self.params[PAGE_VAR]
        if ERROR_FLAG in self.params:
            del self.params[ERROR_FLAG]

    @filter_hook
    def get_list_display(self):
        """
        Return a sequence containing the fields to be displayed on the list.
        """
        self.base_list_display = (COL_LIST_VAR in self.request.GET and self.request.GET[COL_LIST_VAR] != "" and \
            self.request.GET[COL_LIST_VAR].split('.')) or self.list_display
        return list(self.base_list_display)

    @filter_hook
    def get_list_display_links(self):
        """
        Return a sequence containing the fields to be displayed as links
        on the changelist. The list_display parameter is the list of fields
        returned by get_list_display().
        """
        if self.list_display_links or not self.list_display:
            return self.list_display_links
        else:
            # Use only the first item in list_display as link
            return list(self.list_display)[:1]

    def make_result_list(self):
        # Get search parameters from the query string.
        self.base_queryset = self.queryset()
        self.list_queryset = self.get_list_queryset()
        self.ordering_field_columns = self.get_ordering_field_columns()
        self.paginator = self.get_paginator()

        # Get the number of objects, with admin filters applied.
        self.result_count = self.paginator.count

        # Get the total number of objects, with no admin filters applied.
        # Perform a slight optimization: Check to see whether any filters were
        # given. If not, use paginator.hits to calculate the number of objects,
        # because we've already done paginator.hits and the value is cached.
        if not self.list_queryset.query.where:
            self.full_result_count = self.result_count
        else:
            self.full_result_count = self.base_queryset.count()

        self.can_show_all = self.result_count <= self.list_max_show_all
        self.multi_page = self.result_count > self.list_per_page

        # Get the list of objects to display on this page.
        if (self.show_all and self.can_show_all) or not self.multi_page:
            self.result_list = self.list_queryset._clone()
        else:
            try:
                self.result_list = self.paginator.page(
                    self.page_num + 1).object_list
            except InvalidPage:
                if ERROR_FLAG in self.request.GET.keys():
                    return SimpleTemplateResponse('xadmin/views/invalid_setup.html', {
                        'title': _('Database error'),
                    })
                return HttpResponseRedirect(self.request.path + '?' + ERROR_FLAG + '=1')
        self.has_more = self.result_count > (
            self.list_per_page * self.page_num + len(self.result_list))

    @filter_hook
    def get_result_list(self):
        return self.make_result_list()

    @filter_hook
    def post_result_list(self):
        return self.make_result_list()

    @filter_hook
    def get_list_queryset(self):
        """
        Get model queryset. The query has been filted and ordered.
        """
        # First, get queryset from base class.
        queryset = self.queryset()

        # Use select_related() if one of the list_display options is a field
        # with a relationship and the provided queryset doesn't already have
        # select_related defined.
        if not queryset.query.select_related:
            if self.list_select_related:
                queryset = queryset.select_related()
            elif self.list_select_related is None:
                related_fields = []
                for field_name in self.list_display:
                    try:
                        field = self.opts.get_field(field_name)
                    except models.FieldDoesNotExist:
                        pass
                    else:
                        if isinstance(field.rel, models.ManyToOneRel):
                            related_fields.append(field_name)
                if related_fields:
                    queryset = queryset.select_related(*related_fields)
            else:
                pass

        # Then, set queryset ordering.
        queryset = queryset.order_by(*self.get_ordering())

        # Return the queryset.
        return queryset

    # List ordering
    def _get_default_ordering(self):
        ordering = []
        if self.ordering:
            ordering = self.ordering
        elif self.opts.ordering:
            ordering = self.opts.ordering
        return ordering

    @filter_hook
    def get_ordering_field(self, field_name):
        """
        Returns the proper model field name corresponding to the given
        field_name to use for ordering. field_name may either be the name of a
        proper model field or the name of a method (on the admin or model) or a
        callable with the 'admin_order_field' attribute. Returns None if no
        proper model field name can be matched.
        """
        try:
            field = self.opts.get_field(field_name)
            return field.name
        except models.FieldDoesNotExist:
            # See whether field_name is a name of a non-field
            # that allows sorting.
            if callable(field_name):
                attr = field_name
            elif hasattr(self, field_name):
                attr = getattr(self, field_name)
            else:
                attr = getattr(self.model, field_name)
            return getattr(attr, 'admin_order_field', None)

    @filter_hook
    def get_ordering(self):
        """
        Returns the list of ordering fields for the change list.
        First we check the get_ordering() method in model admin, then we check
        the object's default ordering. Then, any manually-specified ordering
        from the query string overrides anything. Finally, a deterministic
        order is guaranteed by ensuring the primary key is used as the last
        ordering field.
        """
        ordering = list(super(ListAdminView, self).get_ordering()
                        or self._get_default_ordering())
        if ORDER_VAR in self.params and self.params[ORDER_VAR]:
            # Clear ordering and used params
            ordering = [pfx + self.get_ordering_field(field_name) for n, pfx, field_name in
                        map(
                        lambda p: p.rpartition('-'),
                        self.params[ORDER_VAR].split('.'))
                        if self.get_ordering_field(field_name)]

        # Ensure that the primary key is systematically present in the list of
        # ordering fields so we can guarantee a deterministic order across all
        # database backends.
        pk_name = self.opts.pk.name
        if not (set(ordering) & set(['pk', '-pk', pk_name, '-' + pk_name])):
            # The two sets do not intersect, meaning the pk isn't present. So
            # we add it.
            ordering.append('-pk')

        return ordering

    @filter_hook
    def get_ordering_field_columns(self):
        """
        Returns a SortedDict of ordering field column numbers and asc/desc
        """

        # We must cope with more than one column having the same underlying sort
        # field, so we base things on column numbers.
        ordering = self._get_default_ordering()
        ordering_fields = SortedDict()
        if ORDER_VAR not in self.params or not self.params[ORDER_VAR]:
            # for ordering specified on ModelAdmin or model Meta, we don't know
            # the right column numbers absolutely, because there might be more
            # than one column associated with that ordering, so we guess.
            for field in ordering:
                if field.startswith('-'):
                    field = field[1:]
                    order_type = 'desc'
                else:
                    order_type = 'asc'
                for attr in self.list_display:
                    if self.get_ordering_field(attr) == field:
                        ordering_fields[field] = order_type
                        break
        else:
            for p in self.params[ORDER_VAR].split('.'):
                none, pfx, field_name = p.rpartition('-')
                ordering_fields[field_name] = 'desc' if pfx == '-' else 'asc'
        return ordering_fields

    def get_check_field_url(self, f):
        """
        Return the select column menu items link.
        We must use base_list_display, because list_display maybe changed by plugins.
        """
        fields = [fd for fd in self.base_list_display if fd != f.name]
        if len(self.base_list_display) == len(fields):
            if f.primary_key:
                fields.insert(0, f.name)
            else:
                fields.append(f.name)
        return self.get_query_string({COL_LIST_VAR: '.'.join(fields)})

    def get_model_method_fields(self):
        """
        Return the fields info defined in model. use FakeMethodField class wrap method as a db field.
        """
        methods = []
        for name in dir(self):
            try:
                if getattr(getattr(self, name), 'is_column', False):
                    methods.append((name, getattr(self, name)))
            except:
                pass
        return [FakeMethodField(name, getattr(method, 'short_description', capfirst(name.replace('_', ' '))))
                for name, method in methods]

    @filter_hook
    def get_context(self):
        """
        Prepare the context for templates.
        """
        self.title = _('%s List') % force_unicode(self.opts.verbose_name)

        model_fields = [(f, f.name in self.list_display, self.get_check_field_url(f))
                        for f in (self.opts.fields + self.get_model_method_fields()) if f.name not in self.list_exclude]

        new_context = {
            'module_name': force_unicode(self.opts.verbose_name_plural),
            'title': self.title,
            'cl': self,
            'model_fields': model_fields,
            'clean_select_field_url': self.get_query_string(remove=[COL_LIST_VAR]),
            'has_add_permission': self.has_add_permission(),
            'app_label': self.app_label,
            'brand_name': self.opts.verbose_name_plural,
            'brand_icon': self.get_model_icon(self.model),
            'add_url': self.model_admin_url('add'),
            'result_headers': self.result_headers(),
            'results': self.results()
        }
        context = super(ListAdminView, self).get_context()
        context.update(new_context)
        return context

    @filter_hook
    def get_response(self, context, *args, **kwargs):
        pass

    @csrf_protect_m
    @filter_hook
    def get(self, request, *args, **kwargs):
        """
        The 'change list' admin view for this model.
        """
        response = self.get_result_list()
        if response:
            return response

        context = self.get_context()
        context.update(kwargs or {})

        response = self.get_response(context, *args, **kwargs)

        return response or TemplateResponse(request, self.object_list_template or
                                            self.get_template_list('views/model_list.html'), context, current_app=self.admin_site.name)

    @filter_hook
    def post_response(self, *args, **kwargs):
        pass

    @csrf_protect_m
    @filter_hook
    def post(self, request, *args, **kwargs):
        return self.post_result_list() or self.post_response(*args, **kwargs) or self.get(request, *args, **kwargs)

    @filter_hook
    def get_paginator(self):
        return self.paginator_class(self.list_queryset, self.list_per_page, 0, True)

    @filter_hook
    def get_page_number(self, i):
        if i == DOT:
            return mark_safe(u'<span class="dot-page">...</span> ')
        elif i == self.page_num:
            return mark_safe(u'<span class="this-page">%d</span> ' % (i + 1))
        else:
            return mark_safe(u'<a href="%s"%s>%d</a> ' % (escape(self.get_query_string({PAGE_VAR: i})), (i == self.paginator.num_pages - 1 and ' class="end"' or ''), i + 1))

    # Result List methods
    @filter_hook
    def result_header(self, field_name, row):
        ordering_field_columns = self.ordering_field_columns
        item = ResultHeader(field_name, row)
        text, attr = label_for_field(field_name, self.model,
                                     model_admin=self,
                                     return_attr=True
                                     )
        item.text = text
        item.attr = attr
        if attr and not getattr(attr, "admin_order_field", None):
            return item

        # OK, it is sortable if we got this far
        th_classes = ['sortable']
        order_type = ''
        new_order_type = 'desc'
        sort_priority = 0
        sorted = False
        # Is it currently being sorted on?
        if field_name in ordering_field_columns:
            sorted = True
            order_type = ordering_field_columns.get(field_name).lower()
            sort_priority = ordering_field_columns.keys().index(field_name) + 1
            th_classes.append('sorted %sending' % order_type)
            new_order_type = {'asc': 'desc', 'desc': 'asc'}[order_type]

        # build new ordering param
        o_list_asc = []  # URL for making this field the primary sort
        o_list_desc = []  # URL for making this field the primary sort
        o_list_remove = []  # URL for removing this field from sort
        o_list_toggle = []  # URL for toggling order type for this field
        make_qs_param = lambda t, n: ('-' if t == 'desc' else '') + str(n)

        for j, ot in ordering_field_columns.items():
            if j == field_name:  # Same column
                param = make_qs_param(new_order_type, j)
                # We want clicking on this header to bring the ordering to the
                # front
                o_list_asc.insert(0, j)
                o_list_desc.insert(0, '-' + j)
                o_list_toggle.append(param)
                # o_list_remove - omit
            else:
                param = make_qs_param(ot, j)
                o_list_asc.append(param)
                o_list_desc.append(param)
                o_list_toggle.append(param)
                o_list_remove.append(param)

        if field_name not in ordering_field_columns:
            o_list_asc.insert(0, field_name)
            o_list_desc.insert(0, '-' + field_name)

        item.sorted = sorted
        item.sortable = True
        item.ascending = (order_type == "asc")
        item.sort_priority = sort_priority

        menus = [
            ('asc', o_list_asc, 'caret-up', _(u'Sort ASC')),
            ('desc', o_list_desc, 'caret-down', _(u'Sort DESC')),
        ]
        if sorted:
            row['num_sorted_fields'] = row['num_sorted_fields'] + 1
            menus.append((None, o_list_remove, 'times', _(u'Cancel Sort')))
            item.btns.append('<a class="toggle" href="%s"><i class="fa fa-%s"></i></a>' % (
                self.get_query_string({ORDER_VAR: '.'.join(o_list_toggle)}), 'sort-up' if order_type == "asc" else 'sort-down'))

        item.menus.extend(['<li%s><a href="%s" class="active"><i class="fa fa-%s"></i> %s</a></li>' %
                         (
                             (' class="active"' if sorted and order_type == i[
                              0] else ''),
                           self.get_query_string({ORDER_VAR: '.'.join(i[1])}), i[2], i[3]) for i in menus])
        item.classes.extend(th_classes)

        return item

    @filter_hook
    def result_headers(self):
        """
        Generates the list column headers.
        """
        row = ResultRow()
        row['num_sorted_fields'] = 0
        row.cells = [self.result_header(
            field_name, row) for field_name in self.list_display]
        return row

    @filter_hook
    def result_item(self, obj, field_name, row):
        """
        Generates the actual list of data.
        """
        item = ResultItem(field_name, row)
        try:
            f, attr, value = lookup_field(field_name, obj, self)
        except (AttributeError, ObjectDoesNotExist):
            item.text = mark_safe("<span class='text-muted'>%s</span>" % EMPTY_CHANGELIST_VALUE)
        else:
            if f is None:
                item.allow_tags = getattr(attr, 'allow_tags', False)
                boolean = getattr(attr, 'boolean', False)
                if boolean:
                    item.allow_tags = True
                    item.text = boolean_icon(value)
                else:
                    item.text = smart_unicode(value)
            else:
                if isinstance(f.rel, models.ManyToOneRel):
                    field_val = getattr(obj, f.name)
                    if field_val is None:
                        item.text = mark_safe("<span class='text-muted'>%s</span>" % EMPTY_CHANGELIST_VALUE)
                    else:
                        item.text = field_val
                else:
                    item.text = display_for_field(value, f)
                if isinstance(f, models.DateField)\
                    or isinstance(f, models.TimeField)\
                        or isinstance(f, models.ForeignKey):
                    item.classes.append('nowrap')

            item.field = f
            item.attr = attr
            item.value = value

        # If list_display_links not defined, add the link tag to the first field
        if (item.row['is_display_first'] and not self.list_display_links) \
                or field_name in self.list_display_links:
            item.row['is_display_first'] = False
            item.is_display_link = True
            if self.list_display_links_details:
                item_res_uri = self.model_admin_url("detail", getattr(obj, self.pk_attname))
                if item_res_uri:
                    edit_url = self.model_admin_url("change", getattr(obj, self.pk_attname))
                    item.wraps.append('<a data-res-uri="%s" data-edit-uri="%s" class="details-handler" rel="tooltip" title="%s">%%s</a>'
                                     % (item_res_uri, edit_url, _(u'Details of %s') % str(obj)))
            else:
                url = self.url_for_result(obj)
                item.wraps.append(u'<a href="%s">%%s</a>' % url)

        return item

    @filter_hook
    def result_row(self, obj):
        row = ResultRow()
        row['is_display_first'] = True
        row['object'] = obj
        row.cells = [self.result_item(
            obj, field_name, row) for field_name in self.list_display]
        return row

    @filter_hook
    def results(self):
        results = []
        for obj in self.result_list:
            results.append(self.result_row(obj))
        return results

    @filter_hook
    def url_for_result(self, result):
        return self.get_object_url(result)

    # Media
    @filter_hook
    def get_media(self):
        media = super(ListAdminView, self).get_media() + self.vendor('xadmin.page.list.js', 'xadmin.page.form.js')
        if self.list_display_links_details:
            media += self.vendor('xadmin.plugin.details.js', 'xadmin.form.css')
        return media

    # Blocks
    @inclusion_tag('xadmin/includes/pagination.html')
    def block_pagination(self, context, nodes, page_type='normal'):
        """
        Generates the series of links to the pages in a paginated list.
        """
        paginator, page_num = self.paginator, self.page_num

        pagination_required = (
            not self.show_all or not self.can_show_all) and self.multi_page
        if not pagination_required:
            page_range = []
        else:
            ON_EACH_SIDE = {'normal': 5, 'small': 3}.get(page_type, 3)
            ON_ENDS = 2

            # If there are 10 or fewer pages, display links to every page.
            # Otherwise, do some fancy
            if paginator.num_pages <= 10:
                page_range = range(paginator.num_pages)
            else:
                # Insert "smart" pagination links, so that there are always ON_ENDS
                # links at either end of the list of pages, and there are always
                # ON_EACH_SIDE links at either end of the "current page" link.
                page_range = []
                if page_num > (ON_EACH_SIDE + ON_ENDS):
                    page_range.extend(range(0, ON_EACH_SIDE - 1))
                    page_range.append(DOT)
                    page_range.extend(
                        range(page_num - ON_EACH_SIDE, page_num + 1))
                else:
                    page_range.extend(range(0, page_num + 1))
                if page_num < (paginator.num_pages - ON_EACH_SIDE - ON_ENDS - 1):
                    page_range.extend(
                        range(page_num + 1, page_num + ON_EACH_SIDE + 1))
                    page_range.append(DOT)
                    page_range.extend(range(
                        paginator.num_pages - ON_ENDS, paginator.num_pages))
                else:
                    page_range.extend(range(page_num + 1, paginator.num_pages))

        need_show_all_link = self.can_show_all and not self.show_all and self.multi_page
        return {
            'cl': self,
            'pagination_required': pagination_required,
            'show_all_url': need_show_all_link and self.get_query_string({ALL_VAR: ''}),
            'page_range': map(self.get_page_number, page_range),
            'ALL_VAR': ALL_VAR,
            '1': 1,
        }

########NEW FILE########
__FILENAME__ = website
from django.utils.translation import ugettext as _
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.views.decorators.cache import never_cache
from django.contrib.auth.views import login
from django.contrib.auth.views import logout
from django.http import HttpResponse

from base import BaseAdminView, filter_hook
from dashboard import Dashboard
from xadmin.forms import AdminAuthenticationForm
from xadmin.models import UserSettings
from xadmin.layout import FormHelper


class IndexView(Dashboard):
    title = _("Main Dashboard")
    icon = "fa fa-dashboard"

    def get_page_id(self):
        return 'home'


class UserSettingView(BaseAdminView):

    @never_cache
    def post(self, request):
        key = request.POST['key']
        val = request.POST['value']
        us, created = UserSettings.objects.get_or_create(
            user=self.user, key=key)
        us.value = val
        us.save()
        return HttpResponse('')


class LoginView(BaseAdminView):

    title = _("Please Login")
    login_form = None
    login_template = None

    @filter_hook
    def update_params(self, defaults):
        pass

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        helper = FormHelper()
        helper.form_tag = False
        context.update({
            'title': self.title,
            'helper': helper,
            'app_path': request.get_full_path(),
            REDIRECT_FIELD_NAME: request.get_full_path(),
        })
        defaults = {
            'extra_context': context,
            'current_app': self.admin_site.name,
            'authentication_form': self.login_form or AdminAuthenticationForm,
            'template_name': self.login_template or 'xadmin/views/login.html',
        }
        self.update_params(defaults)
        return login(request, **defaults)

    @never_cache
    def post(self, request, *args, **kwargs):
        return self.get(request)


class LogoutView(BaseAdminView):

    logout_template = None
    need_site_permission = False

    @filter_hook
    def update_params(self, defaults):
        pass

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        defaults = {
            'extra_context': context,
            'current_app': self.admin_site.name,
            'template_name': self.logout_template or 'xadmin/views/logged_out.html',
        }
        if self.logout_template is not None:
            defaults['template_name'] = self.logout_template

        self.update_params(defaults)
        return logout(request, **defaults)

    @never_cache
    def post(self, request, *args, **kwargs):
        return self.get(request)

########NEW FILE########
__FILENAME__ = widgets
"""
Form Widget classes specific to the Django admin site.
"""
from itertools import chain
from django import forms
from django.forms.widgets import RadioFieldRenderer, RadioInput
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.utils.translation import ugettext as _

from util import vendor


class AdminDateWidget(forms.DateInput):

    @property
    def media(self):
        return vendor('datepicker.js', 'datepicker.css', 'xadmin.widget.datetime.js')

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'date-field', 'size': '10'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminDateWidget, self).__init__(attrs=final_attrs, format=format)

    def render(self, name, value, attrs=None):
        input_html = super(AdminDateWidget, self).render(name, value, attrs)
        return mark_safe('<div class="input-group date bootstrap-datepicker"><span class="input-group-addon"><i class="fa fa-calendar"></i></span>%s'
                         '<span class="input-group-btn"><button class="btn btn-default" type="button">%s</button></span></div>' % (input_html, _(u'Today')))


class AdminTimeWidget(forms.TimeInput):

    @property
    def media(self):
        return vendor('datepicker.js','timepicker.js', 'timepicker.css', 'xadmin.widget.datetime.js')

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'time-field', 'size': '8'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTimeWidget, self).__init__(attrs=final_attrs, format=format)

    def render(self, name, value, attrs=None):
        input_html = super(AdminTimeWidget, self).render(name, value, attrs)
        return mark_safe('<div class="input-group time bootstrap-timepicker"><span class="input-group-addon"><i class="fa fa-clock-o">'
                         '</i></span>%s<span class="input-group-btn"><button class="btn btn-default" type="button">%s</button></span></div>' % (input_html, _(u'Now')))


class AdminSelectWidget(forms.Select):

    @property
    def media(self):
        return vendor('select.js', 'select.css', 'xadmin.widget.select.js')


class AdminSplitDateTime(forms.SplitDateTimeWidget):
    """
    A SplitDateTime Widget that has some admin-specific styling.
    """
    def __init__(self, attrs=None):
        widgets = [AdminDateWidget, AdminTimeWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, widgets, attrs)

    def format_output(self, rendered_widgets):
        return mark_safe(u'<div class="datetime clearfix">%s%s</div>' %
                        (rendered_widgets[0], rendered_widgets[1]))


class AdminRadioInput(RadioInput):

    def render(self, name=None, value=None, attrs=None, choices=()):
        name = name or self.name
        value = value or self.value
        attrs = attrs or self.attrs
        attrs['class'] = attrs.get('class', '').replace('form-control', '')
        if 'id' in self.attrs:
            label_for = ' for="%s_%s"' % (self.attrs['id'], self.index)
        else:
            label_for = ''
        choice_label = conditional_escape(force_unicode(self.choice_label))
        if attrs.get('inline', False):
            return mark_safe(u'<label%s class="radio-inline">%s %s</label>' % (label_for, self.tag(), choice_label))
        else:
            return mark_safe(u'<div class="radio"><label%s>%s %s</label></div>' % (label_for, self.tag(), choice_label))


class AdminRadioFieldRenderer(RadioFieldRenderer):

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield AdminRadioInput(self.name, self.value, self.attrs.copy(), choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx]  # Let the IndexError propogate
        return AdminRadioInput(self.name, self.value, self.attrs.copy(), choice, idx)

    def render(self):
        return mark_safe(u'\n'.join([force_unicode(w) for w in self]))


class AdminRadioSelect(forms.RadioSelect):
    renderer = AdminRadioFieldRenderer


class AdminCheckboxSelect(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = []
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = forms.CheckboxInput(
                final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))

            if final_attrs.get('inline', False):
                output.append(u'<label%s class="checkbox-inline">%s %s</label>' % (label_for, rendered_cb, option_label))
            else:
                output.append(u'<div class="checkbox"><label%s>%s %s</label></div>' % (label_for, rendered_cb, option_label))
        return mark_safe(u'\n'.join(output))


class AdminSelectMultiple(forms.SelectMultiple):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'select-multi'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminSelectMultiple, self).__init__(attrs=final_attrs)


class AdminFileWidget(forms.ClearableFileInput):
    template_with_initial = (u'<p class="file-upload">%s</p>'
                             % forms.ClearableFileInput.template_with_initial)
    template_with_clear = (u'<span class="clearable-file-input">%s</span>'
                           % forms.ClearableFileInput.template_with_clear)


class AdminTextareaWidget(forms.Textarea):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'textarea-field'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTextareaWidget, self).__init__(attrs=final_attrs)


class AdminTextInputWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'text-field'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminTextInputWidget, self).__init__(attrs=final_attrs)


class AdminURLFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'url-field'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminURLFieldWidget, self).__init__(attrs=final_attrs)


class AdminIntegerFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'int-field'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminIntegerFieldWidget, self).__init__(attrs=final_attrs)


class AdminCommaSeparatedIntegerFieldWidget(forms.TextInput):
    def __init__(self, attrs=None):
        final_attrs = {'class': 'sep-int-field'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(AdminCommaSeparatedIntegerFieldWidget,
              self).__init__(attrs=final_attrs)

########NEW FILE########
