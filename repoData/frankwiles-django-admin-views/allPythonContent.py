__FILENAME__ = admin
from django.contrib import admin
from django.conf.urls import *
from django.conf import settings
from django.contrib.auth.decorators import permission_required


ADMIN_URL_PREFIX = getattr(settings, 'ADMIN_VIEWS_URL_PREFIX', '/admin')


class AdminViews(admin.ModelAdmin):
    """
    Standard admin subclass to handle easily adding views to
    the Django admin for an app
    """

    def __init__(self, *args, **kwargs):
        super(AdminViews, self).__init__(*args, **kwargs)
        self.direct_links = []
        self.local_view_names = []
        self.output_urls = []

    def get_urls(self):
        original_urls = super(AdminViews, self).get_urls()
        added_urls = []

        for link in self.admin_views:
            if hasattr(self, link[1]):
                view_func = getattr(self, link[1])
                if len(link) == 3:
                    # View requires permission
                    view_func = permission_required(link[2], raise_exception=True)(view_func)
                added_urls.extend(
                    patterns('',
                        url(regex=r'%s' % link[1],
                            name=link[1],
                            view=self.admin_site.admin_view(view_func)
                        )
                    )
                )
                self.local_view_names.append(link[0])

                # Build URL from known info
                info = self.model._meta.app_label, self.model._meta.module_name
                self.output_urls.append((
                        'view',
                        link[0],
                        "/admin/%s/%s/%s" % (info[0], info[1], link[1]),
                        link[2] if len(link) == 3 else None,
                    )
                )
            else:
                self.direct_links.append(link)
                self.output_urls.append(('url', link[0], link[1], link[2] if len(link) == 3 else None))

        return added_urls + original_urls

########NEW FILE########
__FILENAME__ = admin_views_install_templates
import os
from shutil import copyfile

from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """ Install the changed admin index template """

    can_import_settings = True
    args = "/path/to/install/template"
    help = "Install the necessary changed admin template by providing it as an argument or at the prompt"

    def handle(self, *args, **options):
        current_dir = os.path.dirname(__file__)
        template_dirs = settings.TEMPLATE_DIRS

        if args:
            # Handle case where dir specified on commandline
            dest_dir = os.path.join(args[0], 'admin/')
        elif len(template_dirs) == 1:
            # Handle common case where only one template directory is defined
            dest_dir = os.path.join(template_dirs[0], 'admin/')
        else:
            # Give user the option of picking which directory from their list
            print "Which directory would you like the templates installed in?"
            print "NOTE: The first is *usually* the correct answer."
            print

            for i, dir in enumerate(template_dirs, start=1):
                print "    %d) %s" % (i, dir)

            print

            input = raw_input('Enter directory number: ')
            try:
                dir_num = int(input)
            except ValueError:
                print "ERROR: %r is not a number, please try again." % input
                return

            dest_dir = os.path.join(template_dirs[dir_num-1], 'admin/')

        print "Copying templates to '%s'" % dest_dir

        # Create the admin directory if necessary
        if not os.path.exists(dest_dir):
            print "Creating intermediate directories..."
            os.makedirs(dest_dir)

        copyfile(
                os.path.join(current_dir, "../../templates/admin/index.html"),
                os.path.join(dest_dir, "index.html")
            )

        print "Done."

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = admin_views
from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.admin import site

from ..admin import AdminViews

register = template.Library()

@register.simple_tag
def get_admin_views(app_name, perms):
    output = []
    STATIC_URL = settings.STATIC_URL

    for k, v in site._registry.items():
        if app_name.lower() not in str(k._meta):
            continue

        if isinstance(v, AdminViews):
            for type, name, link, perm in v.output_urls:
                if perm and not perm in perms:
                    continue
                if type == 'url':
                    img_url = "%sadmin_views/icons/link.png" % STATIC_URL
                    alt_text = "Link to '%s'" % name
                else:
                    img_url = "%sadmin_views/icons/view.png" % STATIC_URL
                    alt_text = "Custom admin view '%s'" % name

                output.append(
                        u"""<tr>
                              <th scope="row">
                                  <img src="%s" alt="%s" />
                                  <a href="%s">%s</a></th>
                              <td>&nbsp;</td>
                              <td>&nbsp;</td>
                           </tr>
                        """ % (img_url, alt_text, link, name)
                    )

    return "".join(output)


########NEW FILE########
__FILENAME__ = tests
import os
from shutil import rmtree
from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command

class AdminViewsTests(TestCase):
    """ Test django-admin-views """

    def setUp(self):
        # Create a superuser to login as
        self.superuser = User.objects.create_superuser('frank', 'frank@revsys.com', 'pass')
        self.TEMPLATE_DIR = settings.TEMPLATE_DIRS[0]

    def test_urls_showup(self):
        self.client.login(username='frank', password='pass')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

        # Make sure our links and images show up
        self.assertTrue('/static/admin_views/icons/view.png' in response.content)
        self.assertTrue('/static/admin_views/icons/link.png' in response.content)
        self.assertTrue('/admin/example_app/testmodel/process' in response.content)
        self.assertTrue('http://www.ljworld.com' in response.content)

        # Test that we can go to the URLs
        response = self.client.get('/admin/example_app/testmodel/process')
        self.assertEqual(response.status_code, 302)

    def test_management_command(self):
        call_command('admin_views_install_templates')
        self.assertTrue(os.path.exists(os.path.join(self.TEMPLATE_DIR, 'admin/index.html')))

    def test_management_command_with_args(self):
        call_command('admin_views_install_templates', os.path.join(self.TEMPLATE_DIR))
        self.assertTrue(os.path.exists(os.path.join(self.TEMPLATE_DIR, 'admin/index.html')))

    def tearDown(self):
        admin_subdir = os.path.join(self.TEMPLATE_DIR, 'admin/')

        if os.path.exists(admin_subdir):
            rmtree(admin_subdir)


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from admin_views.admin import AdminViews
from django.shortcuts import redirect

from example_project.example_app.models import TestModel

class TestAdmin(AdminViews):
    admin_views = (
            ('Process This', 'process'),              # Admin view
            ('Go to LJW', 'http://www.ljworld.com'),  # Direct URL
    )

    def process(self, *args, **kwargs):
        return redirect('http://www.cnn.com')

admin.site.register(TestModel, TestAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class TestModel(models.Model):
    name = models.CharField(max_length=50)


########NEW FILE########
__FILENAME__ = settings
# Django settings for example_project project.
import os

PROJECT_ROOT = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'foo.db',                      # Or path to database file if using sqlite3.
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
STATIC_ROOT = ''

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
SECRET_KEY = '-n8c&amp;*n6ohb8z*to2yqo$p1m-epe8qgg#d!k65ua8iiyt^*r)v'

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

ROOT_URLCONF = 'example_project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example_project.wsgi.application'

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
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'admin_views',
    'example_project.example_app',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

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
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'example_project.views.home', name='home'),
    # url(r'^example_project/', include('example_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example_project project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

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
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys
from os.path import dirname, abspath

from django.conf import settings


TEST_ROOT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.join(TEST_ROOT, '../../example_project/example_project/')

if not settings.configured:
    settings.configure(
        DATABASES = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': 'foo.db',
                }
        },
        SITE_ID = 1,
        COVERAGE_MODULE_EXCLUDES = [
            'tests$', 'settings$', 'urls$',
            'common.views.test', '__init__', 'django',
        ],
        ROOT_URLCONF = 'example_project.urls',
        WSGI_APPLICATION = 'example_project.wsgi.application',
        TEMPLATE_DIRS = (os.path.join(PROJECT_ROOT, "templates/"),),
        STATIC_URL='/static/',
        INSTALLED_APPS = [
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'django_coverage',
            'admin_views',
            'example_project.example_app',
            'django.contrib.admin',
        ],
    )

from django.test.simple import DjangoTestSuiteRunner
from django_coverage.coverage_runner import CoverageRunner

def runtests(*test_args):
    if not test_args:
        test_args = ['admin_views']
    parent = dirname(abspath(__file__))
    example_project = os.path.join(parent, 'example_project')
    sys.path.insert(0, example_project)
    runner = CoverageRunner()
    failures = runner.run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
