__FILENAME__ = populatedb
from datetime import datetime
from django.core.management.base import NoArgsCommand
from django.db.transaction import commit_on_success
from main.models import Payment
from random import randrange, uniform
from time import mktime

def any_amount():
    return str(uniform(2., 8.))

foo = mktime(datetime(2011, 1, 1).timetuple())
bar = mktime(datetime(2011, 4, 1).timetuple())

def any_datetime():
    return datetime.fromtimestamp(foo + randrange(bar - foo))

class Command(NoArgsCommand):
    @commit_on_success
    def handle_noargs(self, **options):
        for i in xrange(2400):
            Payment(amount=any_amount(), datetime=any_datetime()).save()
            self.stdout.write('.')
            self.stdout.flush()
        self.stdout.write('\n')

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Payment(models.Model):
    amount = models.DecimalField(max_digits=11, decimal_places=4)
    datetime = models.DateTimeField()

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Avg
from django.shortcuts import render_to_response
from django.template import RequestContext
from main.models import Payment
from qsstats import QuerySetStats

def time_series(queryset, date_field, interval, func=None):
    qsstats = QuerySetStats(queryset, date_field, func)
    return qsstats.time_series(*interval)

def home(request):
    series = {'count': [], 'total': []}
    queryset = Payment.objects.all()
    y = 2011
    for m in range(1, 4):
        start = datetime(y, m, 1)
        end = start + relativedelta(months=1)
        series['count'].append(time_series(queryset, 'datetime', [start, end]))
        series['total'].append(time_series(queryset, 'datetime', [start, end], func=Sum('amount')))

    start = datetime(y, 1, 1)
    end = start + relativedelta(months=3)
    series['count_3'] = time_series(queryset, 'datetime', [start, end])
    series['total_3'] = time_series(queryset, 'datetime', [start, end], func=Avg('amount'))

    return render_to_response('home.html', {'series': series},
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for googlecharts project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/googlecharts',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Antarctica/Vostok'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'ru-RU'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = False

import os
OUR_ROOT = os.path.realpath(os.path.dirname(__file__))

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(OUR_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(OUR_ROOT, 'static')

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
SECRET_KEY = 'lhwo(xs0n8_q(c0j_3ewk!z=jks&6m*&^0k1td+f65is&rj^gw'

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

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = os.path.join(OUR_ROOT, 'templates')

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'googlecharts',
    'main',
)

GOOGLECHARTS_API = '1.1'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
import main

urlpatterns = patterns(None,
    url(r'^$', main.home, name='home'),
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = googlecharts
from django import template
from django.conf import settings

register = template.Library()

# {% googlecharts %}...{% endgooglecharts %}

_api = getattr(settings, 'GOOGLECHARTS_API', '1.1')

class GooglechartsNode(template.Node):
    def __init__(self, nodelist):
        self._nodelist = nodelist

    def render_template(self, template, **kwargs):
        from django.template.loader import render_to_string
        return render_to_string(template, kwargs)

    def render(self, context):
        js = self._nodelist.render(context)
        return self.render_template('googlecharts/googlecharts.html', googlecharts_js=js, api=_api)

@register.tag
def googlecharts(parser, token):
    nodelist = parser.parse(['endgooglecharts'])
    parser.delete_first_token()
    return GooglechartsNode(nodelist)

# {% data series "name" %}...{% enddata %}

def _remove_quotes(s):
    if s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s

class DataNode(template.Node):
    def __init__(self, nodelist, name, series):
        self._nodelist = nodelist
        self._name = name
        self._series = template.Variable(series)

    def render(self, context):
        '''
        var googlecharts_data_%(name)s = [
            %(data)s
            null // fix trailing comma
        ];
        googlecharts_data_%(name)s.pop();
        googlecharts_data_%(name)s._cl = [%(cl)s];
        '''
        series = self._series.resolve(context)
        nodelist = self._nodelist.get_nodes_by_type(ColNode)
        data = []
        for row in series:
            data.append([node.render(context, row[i]) for i, node in enumerate(nodelist)])
        data_str = ''.join(['[%s],' % ','.join(r) for r in data])
        cl = ','.join(['["%s","%s"]' % (c._typename, c._label) for c in nodelist])
        return self.render.__doc__ % {'name': self._name, 'data': data_str, 'cl': cl}

@register.tag
def data(parser, token):
    args = token.split_contents()
    if len(args) < 2:
        raise template.TemplateSyntaxError('%r tag requires at least one argument' % args[0])
    while len(args) < 3:
        args.append('default')
    _, series, name = args
    name = _remove_quotes(name)
    nodelist = parser.parse(['enddata'])
    parser.delete_first_token()
    return DataNode(nodelist, name=name, series=series)

# {% col "type" "label" %}...{% endcol %}

class ColNode(template.Node):
    def __init__(self, nodelist, typename, label):
        self._nodelist = nodelist
        self._typename = typename
        self._label = label

    def render(self, context, val):
        context['val'] = val
        return self._nodelist.render(context)

@register.tag
def col(parser, token):
    args = token.split_contents()
    if len(args) < 2:
        raise template.TemplateSyntaxError('%r tag requires at least one argument' % args[0])
    while len(args) < 3:
        args.append('')
    _, typename, label = [_remove_quotes(s) for s in args]
    nodelist = parser.parse(['endcol'])
    parser.delete_first_token()
    return ColNode(nodelist, typename=typename, label=label)

# {% options "name" %}...{% endoptions %}

class OptionsNode(template.Node):
    def __init__(self, nodelist, name):
        self._nodelist = nodelist
        self._name = name

    def render(self, context):
        '''
        var googlecharts_options_%(name)s = {
            %(data)s
        };
        '''
        return self.render.__doc__ % {'name': self._name, 'data': self._nodelist.render(context)}

@register.tag
def options(parser, token):
    try:
        _, name = token.split_contents()
        name = _remove_quotes(name)
    except ValueError:
        name = 'default'
    nodelist = parser.parse(['endoptions'])
    parser.delete_first_token()
    return OptionsNode(nodelist, name=name)

# {% graph "container" "data" "options" %}

class GraphNode(template.Node):
    def __init__(self, **kwargs):
        self._args = kwargs

    def render(self, context):
        '''
        opt = _clone(googlecharts_options_%(options)s);
        opt.container = "%(container)s";
        opt.rows = googlecharts_data_%(data)s;
        googlecharts.push(opt);
        '''
        return self.render.__doc__ % self._args

@register.tag
def graph(parser, token):
    args = token.split_contents()
    if len(args) < 2:
        raise template.TemplateSyntaxError('%r tag requires at least one argument' % args[0])
    while len(args) < 4:
        args.append('default')
    _, container, data, options = [_remove_quotes(s) for s in args]
    return GraphNode(container=container, data=data, options=options)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
