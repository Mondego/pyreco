__FILENAME__ = settings
# Django settings for demoproject project.

import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

APPLICATION_DIR = os.path.dirname(globals()['__file__'])

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."),
)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'demoproject.db',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

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
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
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
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'djangobower.finders.BowerFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'sq)9^f#mf444c(#om$zpo0v!%y=%pqem*9s_qav93fwr_&x40u'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
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

ROOT_URLCONF = 'demoproject.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'demoproject.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(APPLICATION_DIR, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_nvd3',
    'djangobower',
    'demoproject',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# Django extensions
try:
    import django_extensions
except ImportError:
    pass
else:
    INSTALLED_APPS = INSTALLED_APPS + ('django_extensions',)

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


# Django-bower
# ------------

# Specifie path to components root (you need to use absolute path)
BOWER_COMPONENTS_ROOT = os.path.join(PROJECT_ROOT, 'components')

BOWER_PATH = '/usr/local/bin/bower'

BOWER_INSTALLED_APPS = (
    'd3#3.3.6',
    'nvd3#1.1.12-beta',
)

#IMPORT LOCAL SETTINGS
#=====================
try:
    from settings_local import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = demo_tags
#from django import template
from django.template.defaultfilters import register


@register.filter
def demo(value):
    return value + 'demo'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('demoproject.views',
    # Examples:
    url(r'^$', 'home', name='home'),
    url(r'^piechart/', 'demo_piechart', name='demo_piechart'),
    url(r'^linechart/', 'demo_linechart', name='demo_linechart'),
    url(r'^linechart_without_date/', 'demo_linechart_without_date', name='demo_linechart_without_date'),
    url(r'^linewithfocuschart/', 'demo_linewithfocuschart', name='demo_linewithfocuschart'),
    url(r'^multibarchart/', 'demo_multibarchart', name='demo_multibarchart'),
    url(r'^stackedareachart/', 'demo_stackedareachart', name='demo_stackedareachart'),
    url(r'^multibarhorizontalchart/', 'demo_multibarhorizontalchart', name='demo_multibarhorizontalchart'),
    url(r'^lineplusbarchart/', 'demo_lineplusbarchart', name='demo_lineplusbarchart'),
    url(r'^cumulativelinechart/', 'demo_cumulativelinechart', name='demo_cumulativelinechart'),
    url(r'^discretebarchart/', 'demo_discretebarchart', name='demo_discretebarchart'),
    url(r'^discretebarchart_with_date/', 'demo_discretebarchart_with_date', name='demo_discretebarchart_date'),
    url(r'^scatterchart/', 'demo_scatterchart', name='demo_scatterchart'),
    url(r'^linechart_with_ampm/', 'demo_linechart_with_ampm', name='demo_linechart_with_ampm'),
    url(r'^lineplusbarwithfocuschart/', 'demo_lineplusbarwithfocuschart', name='demo_lineplusbarwithfocuschart'),
    url(r'^lineplusbarwithfocuschart_without_date/', 'demo_lineplusbarwithfocuschart_without_date', name='demo_lineplusbarwithfocuschart_without_date'),
    # url(r'^demoproject/', include('demoproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
#from django.template.context import RequestContext
import random
import datetime
import time


def home(request):
    """
    home page
    """
    return render_to_response('home.html')


def demo_piechart(request):
    """
    pieChart page
    """
    xdata = ["Apple", "Apricot", "Avocado", "Banana", "Boysenberries",
             "Blueberries", "Dates", "Grapefruit", "Kiwi", "Lemon"]
    ydata = [52, 48, 160, 94, 75, 71, 490, 82, 46, 17]

    color_list = ['#5d8aa8', '#e32636', '#efdecd', '#ffbf00', '#ff033e', '#a4c639',
                  '#b2beb5', '#8db600', '#7fffd4', '#ff007f', '#ff55a3', '#5f9ea0']
    extra_serie = {
        "tooltip": {"y_start": "", "y_end": " cal"},
        "color_list": color_list
    }
    chartdata = {'x': xdata, 'y1': ydata, 'extra1': extra_serie}
    charttype = "pieChart"
    chartcontainer = 'piechart_container'  # container name

    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': '',
            'tag_script_js': True,
            'jquery_on_ready': False,
        }
    }
    return render_to_response('piechart.html', data)


def demo_linechart(request):
    """
    lineChart page
    """
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    nb_element = 150
    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_serie1 = {
        "tooltip": {"y_start": "", "y_end": " cal"},
        "date_format": tooltip_date,
        'color': '#a4c639'
    }
    extra_serie2 = {
        "tooltip": {"y_start": "", "y_end": " cal"},
        "date_format": tooltip_date,
        'color': '#FF8aF8'
    }
    chartdata = {'x': xdata,
                 'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie1,
                 'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie2}

    charttype = "lineChart"
    chartcontainer = 'linechart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': True,
            'x_axis_format': '%d %b %Y %H',
            'tag_script_js': True,
            'jquery_on_ready': False,
        }
    }
    return render_to_response('linechart.html', data)


def demo_linechart_without_date(request):
    """
    lineChart page
    """
    extra_serie = {}
    xdata = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    ydata = [3, 5, 7, 8, 3, 5, 3, 5, 7, 6, 3, 1]
    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie,
    }
    charttype = "lineChart"
    chartcontainer = 'linechart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': '',
            'tag_script_js': True,
            'jquery_on_ready': False,
        }
    }
    return render_to_response('linechart.html', data)


def demo_linewithfocuschart(request):
    """
    linewithfocuschart page
    """
    nb_element = 100
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)

    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)
    ydata3 = map(lambda x: x * 3, ydata)
    ydata4 = map(lambda x: x * 4, ydata)

    tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"},
                   "date_format": tooltip_date}

    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie,
        'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie,
        'name3': 'series 3', 'y3': ydata3, 'extra3': extra_serie,
        'name4': 'series 4', 'y4': ydata4, 'extra4': extra_serie
    }
    charttype = "lineWithFocusChart"
    chartcontainer = 'linewithfocuschart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': True,
            'x_axis_format': '%d %b %Y %H',
            'tag_script_js': True,
            'jquery_on_ready': True,
        }
    }
    return render_to_response('linewithfocuschart.html', data)


def demo_multibarchart(request):
    """
    multibarchart page
    """
    nb_element = 10
    xdata = range(nb_element)
    ydata = [random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)
    ydata3 = map(lambda x: x * 3, ydata)
    ydata4 = map(lambda x: x * 4, ydata)

    extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"}}

    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie,
        'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie,
        'name3': 'series 3', 'y3': ydata3, 'extra3': extra_serie,
        'name4': 'series 4', 'y4': ydata4, 'extra4': extra_serie
    }

    nb_element = 100
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_serie = {"tooltip": {"y_start": "There are ", "y_end": " calls"},
                   "date_format": tooltip_date}

    date_chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie,
        'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie,
    }

    charttype = "multiBarChart"
    chartcontainer = 'multibarchart_container'  # container name
    chartcontainer_with_date = 'date_multibarchart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': '',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
        'chartdata_with_date': date_chartdata,
        'chartcontainer_with_date': chartcontainer_with_date,
        'extra_with_date': {
            'name': chartcontainer_with_date,
            'x_is_date': True,
            'x_axis_format': '%d %b %Y',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('multibarchart.html', data)


def demo_stackedareachart(request):
    """
    stackedareachart page
    """
    nb_element = 100
    xdata = range(nb_element)
    xdata = map(lambda x: 100 + x, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    extra_serie1 = {"tooltip": {"y_start": "", "y_end": " balls"}}
    extra_serie2 = {"tooltip": {"y_start": "", "y_end": " calls"}}

    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie1,
        'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie2,
    }
    charttype = "stackedAreaChart"
    chartcontainer = 'stackedareachart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': '',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('stackedareachart.html', data)


def demo_multibarhorizontalchart(request):
    """
    multibarhorizontalchart page
    """
    nb_element = 10
    xdata = range(nb_element)
    ydata = [i + random.randint(-10, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    extra_serie = {"tooltip": {"y_start": "", "y_end": " mins"}}

    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie,
        'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie,
    }

    charttype = "multiBarHorizontalChart"
    chartcontainer = 'multibarhorizontalchart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': '',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('multibarhorizontalchart.html', data)


def demo_lineplusbarchart(request):
    """
    lineplusbarchart page
    """
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    nb_element = 100
    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = [i + random.randint(1, 10) for i in reversed(range(nb_element))]
    kwargs1 = {}
    kwargs1['bar'] = True

    tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_serie1 = {"tooltip": {"y_start": "$ ", "y_end": ""},
                    "date_format": tooltip_date}
    extra_serie2 = {"tooltip": {"y_start": "", "y_end": " min"},
                    "date_format": tooltip_date}

    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie1, 'kwargs1': kwargs1,
        'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie2,
    }

    charttype = "linePlusBarChart"
    chartcontainer = 'lineplusbarchart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': True,
            'x_axis_format': '%d %b %Y %H',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('lineplusbarchart.html', data)


def demo_cumulativelinechart(request):
    """
    cumulativelinechart page
    """
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    nb_element = 100
    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_serie1 = {"tooltip": {"y_start": "", "y_end": " calls"},
                    "date_format": tooltip_date}
    extra_serie2 = {"tooltip": {"y_start": "", "y_end": " min"},
                    "date_format": tooltip_date}

    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie1,
        'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie2,
    }

    charttype = "cumulativeLineChart"
    chartcontainer = 'cumulativelinechart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': True,
            'x_axis_format': '%d %b %Y %H',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('cumulativelinechart.html', data)


def demo_discretebarchart(request):
    """
    discretebarchart page
    """
    xdata = ["A", "B", "C", "D", "E", "F", "G"]
    ydata = [3, 12, -10, 5, 35, -7, 2]

    extra_serie1 = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartdata = {
        'x': xdata, 'name1': '', 'y1': ydata, 'extra1': extra_serie1,
    }
    charttype = "discreteBarChart"
    chartcontainer = 'discretebarchart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': '',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('discretebarchart.html', data)


def demo_discretebarchart_with_date(request):
    """
    discretebarchart page
    """
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    nb_element = 10

    xdata = list(range(nb_element))
    xdata = [start_time + x * 1000000000 for x in xdata]
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]

    extra_serie1 = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartdata = {
        'x': xdata, 'name1': '', 'y1': ydata, 'extra1': extra_serie1,
    }
    charttype = "discreteBarChart"
    chartcontainer = 'discretebarchart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': True,
            'x_axis_format': '%d-%b',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('discretebarchart_with_date.html', data)


def demo_scatterchart(request):
    """
    scatterchart page
    """
    nb_element = 50
    xdata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata1 = [i * random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata1)
    ydata3 = map(lambda x: x * 5, ydata1)

    kwargs1 = {'shape': 'circle'}
    kwargs2 = {'shape': 'cross'}
    kwargs3 = {'shape': 'triangle-up'}

    extra_serie1 = {"tooltip": {"y_start": "", "y_end": " balls"}}

    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata1, 'kwargs1': kwargs1, 'extra1': extra_serie1,
        'name2': 'series 2', 'y2': ydata2, 'kwargs2': kwargs2, 'extra2': extra_serie1,
        'name3': 'series 3', 'y3': ydata3, 'kwargs3': kwargs3, 'extra3': extra_serie1
    }
    charttype = "scatterChart"
    chartcontainer = 'scatterchart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': True,
            'x_axis_format': '%d-%b',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('scatterchart.html', data)


def demo_linechart_with_ampm(request):
    """
    lineChart page
    """
    xdata = []
    ydata = []
    ydata2 = []

    ydata = [0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 4, 3, 3, 5, 7, 5, 3, 16, 6, 9, 15, 4, 12]
    ydata2 = [9, 8, 11, 8, 3, 7, 10, 8, 6, 6, 9, 6, 5, 4, 3, 10, 0, 6, 3, 1, 0, 0, 0, 1]

    for i in range(0, 24):
        xdata.append(i)

    #tooltip_date = ""  # "%d %b %Y %H:%M:%S %p"
    extra_serie = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartdata = {'x': xdata,
                 'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie,
                 'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie}
    charttype = "lineChart"
    chartcontainer = 'linechart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': 'AM_PM',
            'tag_script_js': True,
            'jquery_on_ready': True,
        }
    }
    return render_to_response('linechart_with_ampm.html', data)


def demo_lineplusbarwithfocuschart(request):
    """
    lineplusbarwithfocuschart page
    """
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    nb_element = 100

    xdata = list(range(nb_element))
    xdata = [start_time + x * 1000000000 for x in xdata]
    ydata = [i + random.randint(-10, 10) for i in range(nb_element)]
    ydata2 = [200 - i + random.randint(-10, 10) for i in range(nb_element)]

    kwargs1 = {}
    kwargs1['bar'] = True

    tooltip_date = "%d %b %Y %H:%M:%S %p"
    extra_serie1 = {"tooltip": {"y_start": "$ ", "y_end": ""},
                    "date_format": tooltip_date}
    extra_serie2 = {"tooltip": {"y_start": "", "y_end": " min"},
                    "date_format": tooltip_date}

    chartdata = {
        'x': xdata,
        'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie1, 'kwargs1': kwargs1,
        'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie2,
    }

    charttype = "linePlusBarWithFocusChart"
    chartcontainer = 'lineplusbarwithfocuschart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': True,
            'x_axis_format': '%d %b %Y %H',
            'tag_script_js': True,
            'jquery_on_ready': True,
        },
    }
    return render_to_response('lineplusbarwithfocuschart.html', data)


def demo_lineplusbarwithfocuschart_without_date(request):
    """
    lineplusbarwithfocuschart_without_date page
    """
    xdata = []
    ydata = []
    ydata2 = []

    ydata = [0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 4, 3, 3, 5, 7, 5, 3, 16, 6, 9, 15, 4, 12]
    ydata2 = [9, 8, 11, 8, 3, 7, 10, 8, 6, 6, 9, 6, 5, 4, 3, 10, 0, 6, 3, 1, 0, 0, 0, 1]
    ydata3 = [9, 8, 15, 8, 4, 7, 20, 8, 4, 6, 0, 4, 5, 7, 3, 15, 30, 6, 3, 1, 0, 0, 0, 1]
    ydata4 = [2, 7, 13, 0, 8, 7, 20, 8, 7, 5, 2, 4, 5, 7, 1, 11, 10, 6, 3, 1, 0, 0, 0, 1]

    for i in range(0, 24):
        xdata.append(i)
    kwargs = {"bar": "true"}
    #tooltip_date = ""  # "%d %b %Y %H:%M:%S %p"
    extra_serie = {"tooltip": {"y_start": "", "y_end": " cal"}}
    chartdata = {'x': xdata,
                 'name1': 'series 1', 'y1': ydata, 'extra1': extra_serie, 'kwargs1': kwargs,
                 'name2': 'series 2', 'y2': ydata2, 'extra2': extra_serie,
                 'name3': 'series 3', 'y3': ydata3, 'extra3': extra_serie,
                 'name4': 'series 4', 'y4': ydata4, 'extra4': extra_serie,
                }

    charttype = "linePlusBarWithFocusChart"
    chartcontainer = 'lineplusbarwithfocuschart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': 'AM_PM',
            'tag_script_js': True,
            'jquery_on_ready': True,
        }
    }
    return render_to_response('lineplusbarwithfocuschart_with_ampm.html', data)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for demoproject project.

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

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "demoproject.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

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
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = nvd3_tags
from django.template.defaultfilters import register
from django.utils.safestring import mark_safe
from django.conf import settings
from nvd3.NVD3Chart import NVD3Chart
from nvd3 import lineWithFocusChart, lineChart, \
    multiBarChart, pieChart, stackedAreaChart, \
    multiBarHorizontalChart, linePlusBarChart, \
    cumulativeLineChart, discreteBarChart, scatterChart, linePlusBarWithFocusChart


@register.simple_tag
def load_chart(chart_type, series, container, kw_extra, *args, **kwargs):
    """Loads the Chart objects in the container.

    **usage**:

        {% load_chart "lineWithFocusChart" data_set "div_lineWithFocusChart" %}

    **Arguments**:

        * ``chart_type`` - Give chart type name eg. lineWithFocusChart/pieChart
        * ``series`` - Data set which are going to be plotted in chart.
        * ``container`` - Chart holder in html page.

    **kw_extra settings**::
        * ``x_is_date`` - if enabled the x-axis will be display as date format
        * ``x_axis_format`` - set the x-axis date format, ie. "%d %b %Y"
        * ``tag_script_js`` - if enabled it will add the javascript tag '<script>'
        * ``jquery_on_ready`` - if enabled it will load the javascript only when page is loaded
            this will use jquery library, so make sure to add jquery to the template.
        * ``color_category`` - Define color category (eg. category10, category20, category20c)
        * ``chart_attr`` - Custom chart attributes
    """
    if not chart_type:
        return False

    if not 'x_is_date' in kw_extra:
        kw_extra['x_is_date'] = False
    if not 'x_axis_format' in kw_extra:
        kw_extra['x_axis_format'] = "%d %b %Y"
    if not 'color_category' in kw_extra:
        kw_extra['color_category'] = "category20"
    if not 'tag_script_js' in kw_extra:
        kw_extra['tag_script_js'] = True
    if not 'chart_attr' in kw_extra:
        kw_extra['chart_attr'] = {}
    # set the container name
    kw_extra['name'] = unicode(container)

    # Build chart
    chart = eval(chart_type)(**kw_extra)

    xdata = series['x']
    y_axis_list = [k for k in series.keys() if k.startswith('y')]
    if len(y_axis_list) > 1:
        # Ensure numeric sorting
        y_axis_list = sorted(y_axis_list, key=lambda x: int(x[1:]))

    for key in y_axis_list:
        ydata = series[key]
        axis_no = key.split('y')[1]

        name = series['name' + axis_no] if series.get('name' + axis_no) else None
        extra = series['extra' + axis_no] if series.get('extra' + axis_no) else {}
        kwargs = series['kwargs' + axis_no] if series.get('kwargs' + axis_no) else {}

        chart.add_serie(name=name, y=ydata, x=xdata, extra=extra, **kwargs)

    chart.display_container = False
    chart.buildcontent()

    html_string = chart.htmlcontent + '\n'
    return mark_safe(html_string)


@register.simple_tag
def include_container(include_container, height=400, width=600):
    """
    Include the html for the chart container and css for nvd3
    This will include something similar as :
        <div id="containername"><svg style="height:400px;width:600px;"></svg></div>

    **usage**:

        {% include_container "lineWithFocusChart" 400 400 %}

    **Arguments**:

        * ``include_container`` - container_name
        * ``height`` - Chart height
        * ``width`` - Chart width
    """
    chart = NVD3Chart()
    chart.name = unicode(include_container)
    chart.set_graph_height(height)
    chart.set_graph_width(width)
    chart.buildcontainer()

    return mark_safe(chart.container + '\n')


@register.simple_tag
def include_chart_jscss(static_dir=''):
    """
    Include the html for the chart container and css for nvd3
    This will include something similar as :

        <link media="all" href="/static/nvd3/src/nv.d3.css" type="text/css" rel="stylesheet" />
        <script src="/static/d3/d3.min.js" type="text/javascript"></script>
        <script src="/static/nvd3/nv.d3.min.js" type="text/javascript"></script>

    **usage**:

        {% include_chart_jscss 'newfies' %}

    **Arguments**:

        * ``static_dir`` -
    """
    if static_dir:
        static_dir += '/'

    chart = NVD3Chart()
    chart.header_css = [
        '<link media="all" href="%s" type="text/css" rel="stylesheet" />\n' % h for h in
        (
            "%s%snvd3/src/nv.d3.css" % (settings.STATIC_URL, static_dir),
        )
    ]

    chart.header_js = [
        '<script src="%s" type="text/javascript"></script>\n' % h for h in
        (
            "%s%sd3/d3.min.js" % (settings.STATIC_URL, static_dir),
            "%s%snvd3/nv.d3.min.js" % (settings.STATIC_URL, static_dir)
        )
    ]
    chart.buildhtmlheader()
    return mark_safe(chart.htmlheader + '\n')

########NEW FILE########
__FILENAME__ = tests
from templatetags.nvd3_tags import load_chart, include_container
import unittest


class NVD3TemplateTagsTestCase(unittest.TestCase):

    def testPiechart(self):
        xdata = ["Apple", "Apricot", "Avocado", "Banana", "Boysenberries", "Blueberries",
                 "Dates", "Grapefruit", "Kiwi", "Lemon"]
        ydata = [52, 48, 160, 94, 75, 71, 490, 82, 46, 17]
        chartdata = {'x': xdata, 'y': ydata}
        charttype = "pieChart"
        extra = {'y_is_date': False}

        self.assertTrue(load_chart(charttype, chartdata, 'container', extra))
        self.assertTrue(include_container('container', height=400, width=600))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-nvd3 documentation build configuration file, created by
# sphinx-quickstart on Thu Dec  8 12:55:34 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

#import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-nvd3'
copyright = u'2013-2014, Arezqui Belaid'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.7.2'
# The full version, including alpha/beta/rc tags.
#release = '0.6.1'
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-nvd3doc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'django-nvd3.tex', u'django-nvd3 Documentation',
     u'Arezqui Belaid', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-nvd3', u'django-nvd3 Documentation',
     [u'Arezqui Belaid'], 1)
]

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for demoproject project.

import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

APPLICATION_DIR = os.path.dirname(globals()['__file__'])

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'demoproject.db',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

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
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
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
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'sq)9^f#mf444c(#om$zpo0v!%y=%pqem*9s_qav93fwr_&x40u'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
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

ROOT_URLCONF = 'demoproject.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'demoproject.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(APPLICATION_DIR, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_nvd3',
    'demoproject',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# Django extensions
try:
    import django_extensions
except ImportError:
    pass
else:
    INSTALLED_APPS = INSTALLED_APPS + ('django_extensions',)

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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('demoproject.views',
    # Examples:
    url(r'^$', 'home', name='home'),
    url(r'^piechart/', 'demo_piechart', name='demo_piechart'),
    url(r'^linechart/', 'demo_linechart', name='demo_linechart'),
    url(r'^linewithfocuschart/', 'demo_linewithfocuschart', name='demo_linewithfocuschart'),
    url(r'^multibarchart/', 'demo_multibarchart', name='demo_multibarchart'),
    url(r'^stackedareachart/', 'demo_stackedareachart', name='demo_stackedareachart'),
    url(r'^multibarhorizontalchart/', 'demo_multibarhorizontalchart', name='demo_multibarhorizontalchart'),
    url(r'^lineplusbarchart/', 'demo_lineplusbarchart', name='demo_lineplusbarchart'),
    url(r'^cumulativelinechart/', 'demo_cumulativelinechart', name='demo_cumulativelinechart'),
    url(r'^discretebarchart/', 'demo_discretebarchart', name='demo_discretebarchart'),
    url(r'^scatterchart/', 'demo_scatterchart', name='demo_scatterchart'),
    # url(r'^demoproject/', include('demoproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
#from django.template.context import RequestContext
import random
import datetime
import time


def home(request):
    """
    home page
    """

    return render_to_response('home.html')


def demo_piechart(request):
    """
    pieChart page
    """
    color_list = ['orange', 'yellow', '#C5E946',
                  '#95b43f', 'red', '#FF2259',
                  '#F6A641', '#95b43f', '#FF2259', 'yellow']
    extra_serie = {"color_list": color_list}
    xdata = ["Apple", "Apricot", "Avocado", "Banana", "Boysenberries", "Blueberries", "Dates", "Grapefruit", "Kiwi", "Lemon"]
    ydata = [52, 48, 160, 94, 75, 71, 490, 82, 46, 17]
    chartdata = {'x': xdata, 'y': ydata, 'extra': extra_serie}
    charttype = "pieChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata
    }
    return render_to_response('piechart.html', data)


def demo_linechart(request):
    """
    lineChart page
    """
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    nb_element = 100
    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    chartdata = {'x': xdata, 'y1': ydata, 'y2': ydata2}
    charttype = "lineChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata
    }
    return render_to_response('linechart.html', data)


def demo_linewithfocuschart(request):
    """
    linewithfocuschart page
    """
    nb_element = 100
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)

    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)
    ydata3 = map(lambda x: x * 3, ydata)
    ydata4 = map(lambda x: x * 4, ydata)

    chartdata = {'x': xdata, 'y1': ydata, 'y2': ydata2, 'y3': ydata3, 'y4': ydata4}
    charttype = "lineWithFocusChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata
    }
    return render_to_response('linewithfocuschart.html', data)


def demo_multibarchart(request):
    """
    multibarchart page
    """
    nb_element = 10
    xdata = range(nb_element)
    ydata = [random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)
    ydata3 = map(lambda x: x * 3, ydata)
    ydata4 = map(lambda x: x * 4, ydata)

    chartdata = {'x': xdata, 'y1': ydata, 'y2': ydata2, 'y3': ydata3, 'y4': ydata4}
    charttype = "multiBarChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata
    }
    return render_to_response('multibarchart.html', data)


def demo_stackedareachart(request):
    """
    stackedareachart page
    """
    nb_element = 100
    xdata = range(nb_element)
    xdata = map(lambda x: 100 + x, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    chartdata = {'x': xdata, 'y1': ydata, 'y2': ydata2}
    charttype = "stackedAreaChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata
    }
    return render_to_response('stackedareachart.html', data)


def demo_multibarhorizontalchart(request):
    """
    multibarhorizontalchart page
    """
    nb_element = 10
    xdata = range(nb_element)
    ydata = [i + random.randint(-10, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    chartdata = {'x': xdata, 'y1': ydata, 'y2': ydata2}
    charttype = "multiBarHorizontalChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata
    }
    return render_to_response('multibarhorizontalchart.html', data)


def demo_lineplusbarchart(request):
    """
    lineplusbarchart page
    """
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    nb_element = 100
    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = [i + random.randint(1, 10) for i in reversed(range(nb_element))]
    kwargs1 = {}
    kwargs1['bar'] = True

    chartdata = {'x': xdata, 'y1': ydata, 'kwargs1': kwargs1, 'y2': ydata2}
    charttype = "linePlusBarChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
    }
    return render_to_response('lineplusbarchart.html', data)


def demo_cumulativelinechart(request):
    """
    cumulativelinechart page
    """
    start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
    nb_element = 100
    xdata = range(nb_element)
    xdata = map(lambda x: start_time + x * 1000000000, xdata)
    ydata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata)

    chartdata = {'x': xdata, 'y1': ydata, 'y2': ydata2}
    charttype = "cumulativeLineChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
    }
    return render_to_response('cumulativelinechart.html', data)


def demo_discretebarchart(request):
    """
    discretebarchart page
    """
    xdata = ["A", "B", "C", "D", "E", "F", "G"]
    ydata = [3, 12, -10, 5, 35, -7, 2]

    chartdata = {'x': xdata, 'y1': ydata}
    charttype = "discreteBarChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
    }
    return render_to_response('discretebarchart.html', data)


def demo_scatterchart(request):
    """
    scatterchart page
    """
    nb_element = 50
    xdata = [i + random.randint(1, 10) for i in range(nb_element)]
    ydata1 = [i * random.randint(1, 10) for i in range(nb_element)]
    ydata2 = map(lambda x: x * 2, ydata1)
    ydata3 = map(lambda x: x * 5, ydata1)

    kwargs1 = {'shape': 'circle'}
    kwargs2 = {'shape': 'cross'}
    kwargs3 = {'shape': 'triangle-up'}

    chartdata = {'x': xdata,
                 'y1': ydata1, 'kwargs1': kwargs1,
                 'y2': ydata2, 'kwargs2': kwargs2,
                 'y3': ydata3, 'kwargs3': kwargs3}
    charttype = "scatterChart"
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
    }
    return render_to_response('scatterchart.html', data)
########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for demoproject project.

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

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "demoproject.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/python
# -*- coding: utf-8 -*-
from nvd3 import lineChart
from nvd3 import lineWithFocusChart
from nvd3 import stackedAreaChart
from nvd3 import multiBarHorizontalChart
from nvd3 import linePlusBarChart
from nvd3 import cumulativeLineChart
from nvd3 import scatterChart
from nvd3 import discreteBarChart
from nvd3 import pieChart
from nvd3 import multiBarChart

import random
import unittest
import datetime
import time


class ChartTest(unittest.TestCase):

    def test_lineWithFocusChart(self):
        """Test Line With Focus Chart"""
        type = "lineWithFocusChart"
        chart = lineWithFocusChart(name=type, date=True, height=350)
        nb_element = 100
        xdata = range(nb_element)
        xdata = map(lambda x: 1365026400000 + x * 100000, xdata)
        ydata = [i + random.randint(-10, 10) for i in range(nb_element)]
        ydata2 = map(lambda x: x * 2, ydata)
        chart.add_serie(y=ydata, x=xdata)
        chart.add_serie(y=ydata2, x=xdata)
        chart.buildhtml()

    def test_lineChart(self):
        """Test Line Chart"""
        type = "lineChart"
        chart = lineChart(name=type, date=True, height=350)
        nb_element = 100
        xdata = range(nb_element)
        xdata = map(lambda x: 1365026400000 + x * 100000, xdata)
        ydata = [i + random.randint(1, 10) for i in range(nb_element)]
        ydata2 = map(lambda x: x * 2, ydata)

        chart.add_serie(y=ydata, x=xdata)
        chart.add_serie(y=ydata2, x=xdata)
        chart.buildhtml()

    def test_linePlusBarChart(self):
        """Test line Plus Bar Chart"""
        type = "linePlusBarChart"
        chart = linePlusBarChart(name=type, date=True, height=350)
        start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
        nb_element = 100
        xdata = range(nb_element)
        xdata = map(lambda x: start_time + x * 1000000000, xdata)
        ydata = [i + random.randint(1, 10) for i in range(nb_element)]
        ydata2 = [i + random.randint(1, 10) for i in reversed(range(nb_element))]
        kwargs = {}
        kwargs['bar'] = True
        chart.add_serie(y=ydata, x=xdata, **kwargs)
        chart.add_serie(y=ydata2, x=xdata)
        chart.buildhtml()

    def test_stackedAreaChart(self):
        """Test Stacked Area Chart"""
        type = "stackedAreaChart"
        chart = stackedAreaChart(name=type, height=400)
        nb_element = 100
        xdata = range(nb_element)
        xdata = map(lambda x: 100 + x, xdata)
        ydata = [i + random.randint(1, 10) for i in range(nb_element)]
        ydata2 = map(lambda x: x * 2, ydata)
        chart.add_serie(y=ydata, x=xdata)
        chart.add_serie(y=ydata2, x=xdata)
        chart.buildhtml()

    def test_MultiBarChart(self):
        """Test Multi Bar Chart"""
        type = "MultiBarChart"
        chart = multiBarChart(name=type, height=400)
        nb_element = 10
        xdata = range(nb_element)
        ydata = [random.randint(1, 10) for i in range(nb_element)]
        chart.add_serie(y=ydata, x=xdata)
        chart.buildhtml()

    def test_multiBarHorizontalChart(self):
        """Test multi Bar Horizontal Chart"""
        type = "multiBarHorizontalChart"
        chart = multiBarHorizontalChart(name=type, height=350)
        nb_element = 10
        xdata = range(nb_element)
        ydata = [random.randint(-10, 10) for i in range(nb_element)]
        ydata2 = map(lambda x: x * 2, ydata)
        chart.add_serie(y=ydata, x=xdata)
        chart.add_serie(y=ydata2, x=xdata)
        chart.buildhtml()

    def test_cumulativeLineChart(self):
        """Test Cumulative Line Chart"""
        type = "cumulativeLineChart"
        chart = cumulativeLineChart(name=type, height=400)
        start_time = int(time.mktime(datetime.datetime(2012, 6, 1).timetuple()) * 1000)
        nb_element = 100
        xdata = range(nb_element)
        xdata = map(lambda x: start_time + x * 1000000000, xdata)
        ydata = [i + random.randint(1, 10) for i in range(nb_element)]
        ydata2 = map(lambda x: x * 2, ydata)
        chart.add_serie(y=ydata, x=xdata)
        chart.add_serie(y=ydata2, x=xdata)
        chart.buildhtml()

    def test_scatterChart(self):
        """Test Scatter Chart"""
        type = "scatterChart"
        chart = scatterChart(name=type, date=True, height=350)
        nb_element = 100
        xdata = [i + random.randint(1, 10) for i in range(nb_element)]
        ydata = [i * random.randint(1, 10) for i in range(nb_element)]
        ydata2 = map(lambda x: x * 2, ydata)
        ydata3 = map(lambda x: x * 5, ydata)

        kwargs1 = {'shape': 'circle'}
        kwargs2 = {'shape': 'cross'}
        kwargs3 = {'shape': 'triangle-up'}
        chart.add_serie(y=ydata, x=xdata, **kwargs1)
        chart.add_serie(y=ydata2, x=xdata, **kwargs2)
        chart.add_serie(y=ydata3, x=xdata, **kwargs3)
        chart.buildhtml()

    def test_discreteBarChart(self):
        """Test discrete Bar Chart"""
        type = "discreteBarChart"
        chart = discreteBarChart(name=type, date=True, height=350)
        xdata = ["A", "B", "C", "D", "E", "F", "G"]
        ydata = [3, 12, -10, 5, 35, -7, 2]

        chart.add_serie(y=ydata, x=xdata)
        chart.buildhtml()

    def test_pieChart(self):
        """Test Pie Chart"""
        type = "pieChart"
        chart = pieChart(name=type, height=400, width=400)
        xdata = ["Orange", "Banana", "Pear", "Kiwi", "Apple", "Strawberry", "Pineapple"]
        ydata = [3, 4, 0, 1, 5, 7, 3]
        chart.add_serie(y=ydata, x=xdata)
        chart.buildhtml()


if __name__ == '__main__':
    unittest.main()

# > python tests.py -v
########NEW FILE########
