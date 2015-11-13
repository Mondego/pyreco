__FILENAME__ = models

########NEW FILE########
__FILENAME__ = panels
import re

try:
    from tidylib import tidy_document
except ImportError:
    raise ImportError("""Please, make sure that PyTidyLib
        module installed - it's required for HTMLValidationDebugPanel""")

from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from debug_toolbar.panels import DebugPanel


class HTMLTidyDebugPanel(DebugPanel):
    name = "HTMLTidy"
    has_content = True

    log_data = None
    errors_count = 0
    warns_count = 0
    src_content = ''

    def nav_title(self):
        return _("HTML Validator")

    def nav_subtitle(self):
        return mark_safe(_(u"Tidy Errors: %(errors_cnt)d "\
                            u"Warnings: %(warns_cnt)d") % {
            'errors_cnt': self.errors_count,
            'warns_cnt': self.warns_count,
            })

    def title(self):
        return _("HTML Validator")

    def url(self):
        return ''

    def process_response(self, request, response):
        document, errors = tidy_document(response.content,
                                         options={'numeric-entities': 1})
        self.log_data = (document, errors)
        self.src_content = response.content
        errors_list = errors.split('\n')
        self.errors_count = len([err for err in errors_list \
                                if 'error:' in err.lower()])
        self.warns_count = len([err for err in errors_list \
                                if 'warning:' in err.lower()])

        return response

    def appearance(self, errors):
        replacements = [
            (re.compile(r'\<([^\>]*)\>'), \
                '<strong class="code">&lt;\\1&gt;</strong>'),
            (re.compile(r'(line[^\-]*)(.*)'), \
                u'<td><pre class="handle-position">\\1</pre></td><td class="tidy-msg">\\2<td>'),
            (re.compile(r'\s*\-\s+(Error\:|Warning\:)', re.I), \
                        u'<i>\\1</i>'),
        ]

        for rx, rp in replacements:
            errors = re.sub(rx, rp, errors)

        errors_list = errors.split('\n')
        errors_rt = []
        # mark lines with error with validation-error class
        for err in errors_list:
            if 'error:' in err.lower():
                err = err.replace('<td>', '<td class="validation-error">')
                errors_rt.append(err)
                continue
            errors_rt.append(err)

        return errors_rt

    def content(self):
        context = self.context.copy()

        document, errors = self.log_data
        lines = self.src_content.split("\n")

        context.update({
        'document': document,
        'lines': zip(range(1, len(lines) + 1), lines),
        'errors': self.appearance(errors),
        })

        return render_to_string(\
                    'debug_toolbar_htmltidy/htmltidy.html', context)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django.contrib.admin',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',

            'debug_toolbar',
            'debug_toolbar_htmltidy',
            'debug_toolbar_htmltidy.tests',
        ],
        ROOT_URLCONF='debug_toolbar_htmltidy.tests.urls',
        MIDDLEWARE_CLASSES=[
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'debug_toolbar.middleware.DebugToolbarMiddleware',
        ],
        TEMPLATE_DEBUG=True,
        DEBUG=True,
        SITE_ID=1,
        
    )

from django.test.simple import run_tests


def runtests(*test_args):
    if not test_args:
        test_args = ['debug_toolbar_htmltidy']
    parent = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        #"..",
    )
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=2, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = tests
from debug_toolbar.toolbar.loader import DebugToolbar
from debug_toolbar_htmltidy.panels import HTMLTidyDebugPanel

from django.conf import settings
from django.test import TestCase

from dingus import Dingus

import os


class Settings(object):
    """Allows you to define settings that are required
    for this function to work"""

    NotDefined = object()

    def __init__(self, **overrides):
        self.overrides = overrides
        self._orig = {}

    def __enter__(self):
        for k, v in self.overrides.iteritems():
            self._orig[k] = getattr(settings, k, self.NotDefined)
            setattr(settings, k, v)

    def __exit__(self, exc_type, exc_value, traceback):
        for k, v in self._orig.iteritems():
            if v is self.NotDefined:
                delattr(settings, k)
            else:
                setattr(settings, k, v)


class BaseTestCase(TestCase):
    def setUp(self):
        self.OLD_DEBUG = settings.DEBUG
        self.OLD_DEBUG_TOOLBAR_PANELS = settings.DEBUG_TOOLBAR_PANELS
        self.OLD_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        self.OLD_MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES
        
        settings.DEBUG = True
        settings.DEBUG_TOOLBAR_PANELS = self.panels_list
        settings.TEMPLATE_DIRS = (
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'templates/'),
                )
        settings.MIDDLEWARE_CLASSES = (
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        )

        request = Dingus('request')
        toolbar = DebugToolbar(request)
        toolbar.load_panels()

        self.request = request
        self.toolbar = toolbar
        
    def tearDown(self):
        settings.DEBUG = self.OLD_DEBUG
        settings.DEBUG_TOOLBAR_PANELS = self.OLD_DEBUG_TOOLBAR_PANELS
        settings.TEMPLATE_DIRS = self.TEMPLATE_DIRS
        settings.MIDDLEWARE_CLASSES = self.OLD_MIDDLEWARE_CLASSES

    def panel(self):
        for panel in self.toolbar.panels:
            if panel.__class__ == self.panel_class:
                return panel

        return None


class ViewBasedTestCase(BaseTestCase):
    urls = 'debug_toolbar_htmltidy.tests.urls'
    panel_class = None
    view_url = None

    def fetch_view(self):
        # basic case
        with Settings(DEBUG=True):
            resp = self.client.get(self.view_url)

        return resp


class HTMLValidationDebugPanelTestCase(ViewBasedTestCase):
    urls = 'debug_toolbar_htmltidy.tests.urls'
    panel_class = HTMLTidyDebugPanel
    panels_list = (
    'debug_toolbar_htmltidy.panels.HTMLTidyDebugPanel',)

    view_url = '/'

    def panel(self):
        panel = super(self.__class__, self).panel()

        self.assertEquals(panel.errors_count, 0)
        self.assertEquals(panel.warns_count, 0)

        return panel

    def test_validator_counters(self):
        panel = self.panel()
        resp = self.fetch_view()

        # process response by hand
        panel.process_response(self.request, resp)

        self.assertEqual(panel.errors_count, 1)
        self.assertEqual(panel.warns_count, 6)

    def test_apperance_builder(self):
        panel = self.panel()
        resp = self.fetch_view()

        # process response by hand
        panel.process_response(self.request, resp)
        document, errors = panel.log_data

        builded_errors = panel.appearance(errors)

        self.assertEqual("".join(builded_errors).count('validation-error'), 2)
        self.assertEqual(len(builded_errors), 8)

    def test_media(self):
        resp = self.fetch_view()
        panel = self.panel()
        panel.process_response(self.request, resp)
        html = panel.content()

        self.assertTrue('/__htmltidy_debug__/m/js/htmltidypanel.min.js' \
                        in html)
        self.assertTrue('/__htmltidy_debug__/m/css/htmltidypanel.min.css' \
                        in html)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url, include
from django.views.generic.simple import direct_to_template


urlpatterns = patterns('',
    url(r'^$', direct_to_template, {
    'template': 'htmlvalidator.html',
    }),
    url(r'^', include('debug_toolbar_htmltidy.urls'))
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns
from django.conf import settings

_PREFIX = '__htmltidy_debug__'

urlpatterns = patterns('',
    url(r'^%s/m/(.*)$' % _PREFIX, 'debug_toolbar_htmltidy.views.debug_media'),
)

########NEW FILE########
__FILENAME__ = views
import os
from django.conf import settings
from django.views.static import serve


def debug_media(request, path):
    """View to serve media for debug_toolbar_Htmltidy"""
    root = getattr(settings, 'DEBUG_TOOLBAR_HTMLTIDY_MEDIA_ROOT', None)
    if root is None:
        parent = os.path.abspath(os.path.dirname(__file__))
        root = os.path.join(parent, 'static', 'debug_toolbar_htmltidy')
    return serve(request, path, root)

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
__FILENAME__ = models
from django.db import models


class Sample(models.Model):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = settings
import os
import sys

PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))

sys.path.append(os.path.join(PROJECT_PATH, '..'))

ADMIN_MEDIA_PREFIX = '/admin_media/'
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'example.db'
DEBUG = True
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'debug_toolbar',
    'debug_toolbar_htmltidy',
    'example_htmltidy',
)
INTERNAL_IPS = ('127.0.0.1',)
MEDIA_ROOT = os.path.join(PROJECT_PATH, 'media')
MEDIA_URL = '/media'
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)
ROOT_URLCONF = 'example_htmltidy.urls'
SECRET_KEY = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcd'
SITE_ID = 1
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)
TEMPLATE_DEBUG = DEBUG
TEMPLATE_DIRS = (os.path.join(PROJECT_PATH, 'templates'))

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    #'debug_toolbar.panels.cache.CacheDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    'debug_toolbar_htmltidy.panels.HTMLTidyDebugPanel',
)
########NEW FILE########
__FILENAME__ = urls
from django.conf import settings

from django.views.generic.simple import direct_to_template
from django.conf.urls.defaults import patterns, url, include


#from django.views.generic.simple import direct_to_template


urlpatterns = patterns('',
    url(r'^$', direct_to_template, {
        'template': 'index.html'}),
    url(r'^', include('debug_toolbar_htmltidy.urls'))
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }))

########NEW FILE########
__FILENAME__ = views
from django.views.generic.simple import direct_to_template
from django.contrib.auth.models import User

from models import Sample


def update_object(request, template=''):
    # create  object
    obj = Sample.objects.create(name='test')
    obj = Sample.objects.all().order_by('?')[0]

    # update objec
    obj.name = 'test1'
    obj.save()

    # update objec
    obj.name = 'test2'
    obj.save()

    # delete object
    obj.delete()

    obj2 = Sample.objects.create(name='test2')

    user, created = User.objects.get_or_create(username='admin', defaults={
    'username': 'admin',
    'email': 'test@test.com',
    'first_name': 'admin',
    'last_name': 'admin',
    })
    user.last_name = 'test'
    user.save()
    return direct_to_template(request, template=template)

########NEW FILE########
