__FILENAME__ = addr2lines
import subprocess
import re

from . import ARM_CS_TOOLS

class LineReader(object):
    def __init__(self, elf_path):
        self.elf = elf_path

    def _exec_tool(self):
        return subprocess.check_output([ARM_CS_TOOLS + "arm-none-eabi-objdump", "--dwarf=decodedline", self.elf])

    def get_line_listing(self):
        decoded = self._exec_tool()

        # Hack: assume that any line some text ending in .c, followed by a
        # decimal integer and a hex integer is location information.

        lines = [
            {'file': x.group(1), 'line': int(x.group(2)), 'address': int(x.group(3), 16)}
            for x in re.finditer(r"(.*\.c)\s+(\d+)\s+(0x[0-9a-f]+)", decoded, re.MULTILINE)
        ]

        files = [x.group(1) for x in re.finditer(r"^CU: (?:.*/)?(.*?\.c):$", decoded, re.MULTILINE)]

        return files, lines

    def get_compact_listing(self):
        files, lines = self.get_line_listing()

        # Now compact this into a handy compact listing (to save on file size)
        file_id_lookup = {files[x]: x for x in xrange(len(files))}

        compact_lines = [(x['address'], file_id_lookup[x['file']], x['line']) for x in lines]

        compact_lines.sort(key=lambda x: x[0])

        return {'files': files, 'lines': compact_lines}

class FunctionRange(object):
    def __init__(self, name, start, end, line=None):
        """
        Creates a representation of a function.

        @type name str
        @type start int
        @type end int
        @type line int
        """
        self.name = name
        self.start = start
        self.end = end
        self.line = line

    def __repr__(self):
        return "addr2lines.FunctionRange('%s', %s, %s, %s)" % (self.name, self.start, self.end, self.line)

class FunctionReader(object):
    """
    hello world
    """

    def __init__(self, elf_path):
        self.elf = elf_path

    def _exec_tool(self):
        return subprocess.check_output([ARM_CS_TOOLS + "arm-none-eabi-objdump", "--dwarf=info", self.elf])

    def _decode_info_fields(self, content):
        """
        Takes a string of newline separated output of a single segment
        from objdump --dwarf=info and returns a dictionary of values for
        that segment.

        @type content str
        """
        lines = content.split("\n")
        keys = {}
        for line in lines:
            line_parts = re.split(r"\s+", line.strip(), 3)
            if len(line_parts) < 4:
                continue
            keys[line_parts[1]] = line_parts[3]
        return keys


    def iter_info_groups(self):
        content = self._exec_tool()
        for match in re.finditer(r"<1><[0-9a-f]+>: Abbrev Number: \d+ \(DW_TAG_subprogram\)(.*?)<\d><[0-9a-f]+>", content, re.DOTALL):
            fields = self._decode_info_fields(match.group(1))
            if 'DW_AT_low_pc' not in fields or 'DW_AT_high_pc' not in fields or 'DW_AT_name' not in fields:
                continue
            fn_name = fields['DW_AT_name'].split(' ')[-1] # Function name is the last word in this line.
            fn_start = int(fields['DW_AT_low_pc'], 16)
            fn_end = int(fields['DW_AT_high_pc'], 16)
            fn_line = int(fields['DW_AT_decl_line']) if 'DW_AT_decl_line' in fields else None
            yield FunctionRange(fn_name, fn_start, fn_end, fn_line)

    def get_info_groups(self):
        return list(self.iter_info_groups())

def create_coalesced_group(elf):
    dict = LineReader(elf).get_compact_listing()
    dict['functions'] = sorted([(x.start, x.end, x.name, x.line) for x in FunctionReader(elf).iter_info_groups()], key=lambda x: x[0])
    return dict

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = pebble
from social.backends.oauth import BaseOAuth2
from django.conf import settings
from ide.models.user import UserGithub
from ide.models.project import Project


class PebbleOAuth2(BaseOAuth2):
    name = 'pebble'
    AUTHORIZATION_URL = '{0}/oauth/authorize'.format(settings.SOCIAL_AUTH_PEBBLE_ROOT_URL)
    ACCESS_TOKEN_URL = '{0}/oauth/token'.format(settings.SOCIAL_AUTH_PEBBLE_ROOT_URL)
    ACCESS_TOKEN_METHOD = 'POST'
    STATE_PARAMETER = 'state'
    DEFAULT_SCOPE = ['public']

    def get_user_details(self, response):
        return {
            'email': response.get('email'),
            'fullname': response.get('name'),
            'username': response.get('email'),
        }

    def user_data(self, access_token, *args, **kwargs):
        url = '{0}/api/v1/me.json'.format(settings.SOCIAL_AUTH_PEBBLE_ROOT_URL)
        return self.get_json(
            url,
            headers={'Authorization': 'Bearer {0}'.format(access_token)}
        )

def merge_user(strategy, uid, user=None, *args, **kwargs):
    provider = strategy.backend.name
    social = strategy.storage.user.get_social_auth(provider, uid)
    if social:
        if user and social.user != user:
            # msg = 'This {0} account is already in use.'.format(provider)
            # raise AuthAlreadyAssociated(strategy.backend, msg)
            # Try merging the users.
            # Do this first, simply because it's both most important and most likely to fail.
            Project.objects.filter(owner=social.user).update(owner=user)
            # If one user has GitHub settings and the other doesn't, use them.
            try:
                github = UserGithub.objects.get(user=social.user)
                if github:
                    if UserGithub.objects.filter(user=user).count() == 0:
                        github.user = user
                        github.save()
            except UserGithub.DoesNotExist:
                pass
            # Delete our old social user.
            social.user.delete()
            social = None

        elif not user:
            user = social.user
    return {'social': social,
            'user': user,
            'is_new': user is None,
            'new_association': False}

def clear_old_login(strategy, uid, user=None, *args, **kwargs):
    provider = strategy.backend.name
    social = strategy.storage.user.get_social_auth(provider, uid)
    if user and social and user == social.user:
        if user.has_usable_password():
            user.set_unusable_password()

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
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.conf import settings

from auth import views

reg_view = views.IdeRegistrationMissingView.as_view() if settings.SOCIAL_AUTH_PEBBLE_REQUIRED else views.IdeRegistrationView.as_view()

urlpatterns = patterns(
    '',
    url(r'^register/?$', reg_view, name="registration_register"),
    url(r'^logout/?$', views.logout_view, name="logout"),
    url(r'^api/login$', views.login_action, name="login"),
    url(r'', include('registration.backends.simple.urls'))
)

########NEW FILE########
__FILENAME__ = views
from registration.backends.simple.views import RegistrationView
from django.contrib.auth import logout, login, authenticate
from django.views.generic import View
from django.shortcuts import render, redirect
from django.http.response import Http404
from django.conf import settings
from ide.api import json_failure, json_response


class IdeRegistrationView(RegistrationView):
    def get_success_url(self, *args, **kwargs):
        return "/ide/"


class IdeRegistrationMissingView(View):
    def get(self, request, *args, **kwargs):
        raise Http404()


def logout_view(request):
    logout(request)
    return redirect("/")


def login_action(request):
    username = request.REQUEST['username']
    password = request.REQUEST['password']
    user = authenticate(username=username, password=password)
    if user is None:
        return json_failure("Invalid username or password")

    if not user.is_active:
        return json_failure("Account disabled.")

    login(request, user)
    return json_response()

########NEW FILE########
__FILENAME__ = settings
# Django settings for cloudpebble project.

import os
import dj_database_url
_environ = os.environ

DEBUG = _environ.get('DEBUG', '') != ''
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Administrator', 'example@example.com'),
)

DEFAULT_FROM_EMAIL = _environ.get('FROM_EMAIL', 'CloudPebble <cloudpebble@example.com>')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

MANAGERS = ADMINS

if 'DATABASE_URL' not in _environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': os.getcwd() + '/dev.db',                      # Or path to database file if using sqlite3.
            # The following settings are not used with sqlite3:
            'USER': '',
            'PASSWORD': '',
            'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
            'PORT': '',                      # Set to empty string for default.
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config()
    }

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__)) + '/../'


TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "social.apps.django_app.context_processors.backends",
    "social.apps.django_app.context_processors.login_redirect",
)

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/New_York'

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
MEDIA_ROOT = os.getcwd() + '/user_data/build_results/'

SIMPLYJS_ROOT = os.getcwd() + '/ext/simplyjs/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = _environ.get('MEDIA_URL', 'http://localhost:8001/builds/')

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = 'staticfiles'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

PUBLIC_URL = _environ.get('PUBLIC_URL', 'http://localhost:8000/') # This default is completely useless.

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
SECRET_KEY = _environ.get('SECRET_KEY', 'y_!-!-i!_txo$v5j(@c7m4uk^jyg)l4bf*0yqrztmax)l2027j')

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

if not DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.CachedStaticFilesStorage'


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'auth.pebble.PebbleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'auth.pebble.merge_user', # formerly social.pipeline.social_auth.social_user
    'social.pipeline.user.get_username',
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'auth.pebble.clear_old_login',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details'
)

SOCIAL_AUTH_PEBBLE_KEY = _environ.get('PEBBLE_AUTH_KEY', 'bab3e760ede6e592517682837a054beff83c8a80725d8e13fa122e8e87e99c20')
SOCIAL_AUTH_PEBBLE_SECRET = _environ.get('PEBBLE_AUTH_SECRET', '7bf8b96fd736f3a2ac12d472b0703d44503441913626deed86180c0f47dcbb08')

SOCIAL_AUTH_PEBBLE_ROOT_URL = _environ.get('PEBBLE_AUTH_URL', 'http://10.0.0.201:3000/')
PEBBLE_AUTH_ADMIN_TOKEN = _environ.get('PEBBLE_AUTH_ADMIN_TOKEN', None)

SOCIAL_AUTH_PEBBLE_REQUIRED = 'PEBBLE_AUTH_REQUIRED' in _environ

ROOT_URLCONF = 'cloudpebble.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'cloudpebble.wsgi.application'

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
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    #'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'social.apps.django_app.default',
    'ide',
    'auth',
    'root',
    'qr',
    'south',
    'djcelery',
    'registration'
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

BROKER_URL = _environ.get('CLOUDAMQP_URL', 'amqp://guest:guest@localhost:5672/')

BROKER_POOL_LIMIT = int(_environ.get('BROKER_POOL_LIMIT', 10))

LOGIN_REDIRECT_URL = '/ide/'

LOGIN_URL = '/#login'

FILE_STORAGE = os.getcwd() + '/user_data/'

CHROOT_JAIL = None

CHROOT_ROOT = None

DEFAULT_TEMPLATE = None

EXPORT_DIRECTORY = os.getcwd() + '/user_data/export/'

EXPORT_ROOT = _environ.get('EXPORT_ROOT', 'http://localhost:8001/export/')

GITHUB_CLIENT_ID = _environ.get('GITHUB_ID', '15c3418f8f5c0f956ed8')
GITHUB_CLIENT_SECRET = _environ.get('GITHUB_SECRET', '06e9f765f00016a79a38599fbd858990b23b8afe')

GITHUB_HOOK_TEMPLATE = _environ.get('GITHUB_HOOK', 'http://example.com/ide/project/%(project)d/github/push_hook?key=%(key)s')

SDK1_ROOT = '/home/vagrant/sdk1/Pebble/sdk'
PEBBLE_TOOL = _environ.get('PEBBLE_TOOL', 'pebble')

ARM_CS_TOOLS = _environ.get('ARM_CS_TOOLS', '/home/vagrant/arm-cs-tools/bin/')

KEEN_PROJECT_ID = _environ.get('KEEN_PROJECT_ID', None)
KEEN_WRITE_KEY = _environ.get('KEEN_WRITE_KEY', None)
KEEN_ENABLED = 'ENABLE_KEEN' in _environ

AWS_ENABLED = 'AWS_ENABLED' in _environ
AWS_ACCESS_KEY_ID = _environ.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = _environ.get('AWS_SECRET_ACCESS_KEY', None)

AWS_S3_SOURCE_BUCKET = _environ.get('AWS_S3_SOURCE_BUCKET', None)
AWS_S3_BUILDS_BUCKET = _environ.get('AWS_S3_BUILDS_BUCKET', None)
AWS_S3_EXPORT_BUCKET = _environ.get('AWS_S3_EXPORT_BUCKET', None)

REDIS_URL = _environ.get('REDISCLOUD_URL', 'redis://localhost:6379/')

import djcelery
djcelery.setup_loader()

# import local settings
try:
    from settings_local import *
except ImportError:
    print "No local settings overrides."
    pass

# Don't keep these hanging around in the environment.
for key in _environ.keys():
    # We need these ones to run.
    if key in {'PATH', 'TZ', 'RUN_MAIN', 'CELERY_LOADER', 'DJANGO_SETTINGS_MODULE'}:
        continue
    del _environ[key]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'cloudpebble.views.home', name='home'),
    # url(r'^cloudpebble/', include('cloudpebble.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
     #url(r'^admin/', include(admin.site.urls)),
     url(r'^ide/', include('ide.urls', namespace='ide')),
     url(r'^accounts/', include('auth.urls')), # Namespacing this breaks things.
     url(r'^qr/', include('qr.urls', namespace='qr')),
     url(r'^$', include('root.urls', namespace='root')),
     url(r'', include('social.apps.django_app.urls', namespace='social'))
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for cloudpebble project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "cloudpebble.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudpebble.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
from dj_static import Cling
application = Cling(get_wsgi_application())

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import *
from fabric.contrib.console import confirm

env.hosts = ['app.cloudpebble.net']
env.project_root = '/home/cloudpebble/web/cloudpebble'
env.virtualenv = '/home/cloudpebble/virtualenv'
env.app_user = 'cloudpebble'


def check_updated():
    local("git status")
    if not confirm("Are you ready to deploy?"):
        abort("Not ready.")


def update_remote():
    with cd(env.project_root), settings(sudo_user=env.app_user):
        sudo("git pull")
        sudo("git submodule update --init --recursive")


def update_django():
    with cd(env.project_root), settings(sudo_user=env.app_user):
        with prefix(". %s/bin/activate" % env.virtualenv):
            sudo("python manage.py syncdb")
            sudo("python manage.py migrate")
            sudo("python manage.py collectstatic --noinput")


def update_modules():
    with cd(env.project_root), settings(sudo_user=env.app_user):
        with prefix(". %s/bin/activate" % env.virtualenv):
            sudo("pip install -q --exists-action i -r requirements.txt")


def restart_servers():
    sudo("supervisorctl restart cloudpebble cloudpebble_celery")


def deploy():
    check_updated()
    update_remote()
    update_modules()
    update_django()

    restart_servers()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from ide.models import Project

admin.site.register(Project)

########NEW FILE########
__FILENAME__ = git
import uuid
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from github import UnknownObjectException
from ide.api import json_response, json_failure
import ide.git
from ide.models.project import Project
from ide.tasks.git import do_github_push, do_github_pull
from utils.keen_helper import send_keen_event

__author__ = 'katharine'


@login_required
@require_POST
def github_push(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    commit_message = request.POST['commit_message']
    task = do_github_push.delay(project.id, commit_message)
    return json_response({'task_id': task.task_id})


@login_required
@require_POST
def github_pull(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    task = do_github_pull.delay(project.id)
    return json_response({'task_id': task.task_id})


@login_required
@require_POST
def set_project_repo(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    repo = request.POST['repo']
    branch = request.POST['branch']
    auto_pull = bool(int(request.POST['auto_pull']))
    auto_build = bool(int(request.POST['auto_build']))

    repo = ide.git.url_to_repo(repo)
    if repo is None:
        return json_failure("Invalid repo URL.")
    repo = '%s/%s' % repo

    g = ide.git.get_github(request.user)
    try:
        g_repo = g.get_repo(repo)
    except UnknownObjectException:
        return json_response({'exists': False, 'access': False, 'updated': False, 'branch_exists': False})

    # TODO: Validate the branch...give user option to create one?

    with transaction.commit_on_success():
        if repo != project.github_repo:
            if project.github_hook_uuid:
                try:
                    remove_hooks(g.get_repo(project.github_repo), project.github_hook_uuid)
                except:
                    pass

            # Just clear the repo if none specified.
            if repo == '':
                project.github_repo = None
                project.github_branch = None
                project.github_last_sync = None
                project.github_last_commit = None
                project.github_hook_uuid = None
                project.save()
                return json_response({'exists': True, 'access': True, 'updated': True, 'branch_exists': True})

            if not ide.git.git_verify_tokens(request.user):
                return json_failure("No GitHub tokens on file.")

            try:
                has_access = ide.git.check_repo_access(request.user, repo)
            except UnknownObjectException:
                return json_response({'exists': False, 'access': False, 'updated': False, 'branch_exists': False})

            if has_access:
                project.github_repo = repo
                project.github_branch = branch
                project.github_last_sync = None
                project.github_last_commit = None
                project.github_hook_uuid = None
            else:
                return json_response({'exists': True, 'access': True, 'updated': True, 'branch_exists': True})

        if branch != project.github_branch:
            project.github_branch = branch

        if auto_pull and project.github_hook_uuid is None:
            # Generate a new hook UUID
            project.github_hook_uuid = uuid.uuid4().hex
            # Set it up
            try:
                g_repo.create_hook('web', {'url': settings.GITHUB_HOOK_TEMPLATE % {'project': project.id, 'key': project.github_hook_uuid}, 'content_type': 'form'}, ['push'], True)
            except Exception as e:
                return json_failure(str(e))
        elif not auto_pull:
            if project.github_hook_uuid is not None:
                try:
                    remove_hooks(g_repo, project.github_hook_uuid)
                except:
                    pass
                project.github_hook_uuid = None

        project.github_hook_build = auto_build

        project.save()

    send_keen_event('cloudpebble', 'cloudpebble_project_github_linked', project=project, request=request, data={
        'data': {
            'repo': project.github_repo,
            'branch': project.github_branch
        }
    })

    return json_response({'exists': True, 'access': True, 'updated': True, 'branch_exists': True})


@login_required
@require_POST
def create_project_repo(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    repo = request.POST['repo']
    description = request.POST['description']
    try:
        repo = ide.git.create_repo(request.user, repo, description)
    except Exception as e:
        return json_failure(str(e))
    else:
        project.github_repo = repo.full_name
        project.github_branch = "master"
        project.github_last_sync = None
        project.github_last_commit = None
        project.save()

    send_keen_event('cloudpebble', 'cloudpebble_created_github_repo', project=project, request=request, data={
        'data': {
            'repo': project.github_repo
        }
    })

    return json_response({"repo": repo.html_url})


def remove_hooks(repo, s):
    hooks = list(repo.get_hooks())
    for hook in hooks:
        if hook.name != 'web':
            continue
        if s in hook.config['url']:
            hook.delete()
########NEW FILE########
__FILENAME__ = phone
import uuid
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import simplejson as json, simplejson
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe, require_POST
import requests
from ide.api import json_failure, json_response
from utils.redis_helper import redis_client


@login_required
@require_safe
def list_phones(request):
    user_key = request.user.social_auth.get(provider='pebble').extra_data['access_token']

    response = requests.get(
        '{0}/api/v1/me.json'.format(settings.SOCIAL_AUTH_PEBBLE_ROOT_URL),
        headers={'Authorization': 'Bearer {0}'.format(user_key)},
        params={'client_id': settings.SOCIAL_AUTH_PEBBLE_KEY})

    if response.status_code != 200:
        return json_failure(response.reason)
    else:
        devices = response.json()['devices']
        return json_response({'devices': devices})


@login_required
@require_POST
def ping_phone(request):
    user_id = request.user.social_auth.get(provider='pebble').uid
    device = request.POST['device']

    check_token = uuid.uuid4().hex

    requests.post(
        '{0}/api/v1/users/{1}/devices/{2}/push'.format(settings.SOCIAL_AUTH_PEBBLE_ROOT_URL, user_id, device),
        params={
            'admin_token': settings.PEBBLE_AUTH_ADMIN_TOKEN,
            # 'silent': True,
            'message': "Tap to enable developer mode and install apps from CloudPebble.",
            'custom': json.dumps({
                'action': 'sdk_connect',
                'token': check_token,
                'url': '{0}/ide/update_phone'.format(settings.PUBLIC_URL)
            })
        }
    )

    return json_response({'token': check_token})


@login_required
@require_safe
def check_phone(request, request_id):
    ip = redis_client.get('phone-ip-{0}'.format(request_id))
    if ip is None:
        return json_response({'pending': True})
    else:
        return json_response({'pending': False, 'response': json.loads(ip)})


@require_POST
@csrf_exempt
def update_phone(request):
    data = json.loads(request.body)
    redis_client.set('phone-ip-{0}'.format(data['token']), request.body, ex=120)
    return json_response({})
########NEW FILE########
__FILENAME__ = project
import os
import re
import tempfile
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_safe, require_POST
from ide.api import json_response, json_failure
from ide.models.build import BuildResult
from ide.models.project import Project, TemplateProject
from ide.models.files import SourceFile, ResourceFile
from ide.tasks.archive import create_archive, do_import_archive
from ide.tasks.build import run_compile
from ide.tasks.gist import import_gist
from ide.tasks.git import do_import_github
from utils.keen_helper import send_keen_event

__author__ = 'katharine'


@require_safe
@login_required
def project_info(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    source_files = SourceFile.objects.filter(project=project)
    resources = ResourceFile.objects.filter(project=project)
    output = {
        'type': project.project_type,
        'success': True,
        'name': project.name,
        'last_modified': str(project.last_modified),
        'version_def_name': project.version_def_name,
        'app_uuid': project.app_uuid or '',
        'app_company_name': project.app_company_name,
        'app_short_name': project.app_short_name,
        'app_long_name': project.app_long_name,
        'app_version_code': project.app_version_code,
        'app_version_label': project.app_version_label,
        'app_is_watchface': project.app_is_watchface,
        'app_capabilities': project.app_capabilities,
        'app_jshint': project.app_jshint,
        'menu_icon': project.menu_icon.id if project.menu_icon else None,
        'sdk_version': project.sdk_version,
        'source_files': [{'name': f.file_name, 'id': f.id} for f in source_files],
        'resources': [{
            'id': x.id,
            'file_name': x.file_name,
            'kind': x.kind,
            'identifiers': [y.resource_id for y in x.identifiers.all()],
        } for x in resources],
        'github': {
            'repo': "github.com/%s" % project.github_repo if project.github_repo is not None else None,
            'branch': project.github_branch if project.github_branch is not None else None,
            'last_sync': str(project.github_last_sync) if project.github_last_sync is not None else None,
            'last_commit': project.github_last_commit,
            'auto_build': project.github_hook_build,
            'auto_pull': project.github_hook_uuid is not None
        }
    }

    return json_response(output)


@require_POST
@login_required
def compile_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    build = BuildResult.objects.create(project=project)
    task = run_compile.delay(build.id)
    return json_response({"build_id": build.id, "task_id": task.task_id})


@require_safe
@login_required
def last_build(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    try:
        build = project.builds.order_by('-started')[0]
    except (IndexError, BuildResult.DoesNotExist):
        return json_response({"build": None})
    else:
        b = {
            'uuid': build.uuid,
            'state': build.state,
            'started': str(build.started),
            'finished': str(build.finished) if build.finished else None,
            'id': build.id,
            'pbw': build.pbw_url,
            'log': build.build_log_url,
            'size': {
                'total': build.total_size,
                'binary': build.binary_size,
                'resources': build.resource_size
            }
        }
        return json_response({"build": b})


@require_safe
@login_required
def build_history(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    try:
        builds = project.builds.order_by('-started')[:10]
    except (IndexError, BuildResult.DoesNotExist):
        return json_response({"build": None})
    else:
        out = []
        for build in builds:
            out.append({
                'uuid': build.uuid,
                'state': build.state,
                'started': str(build.started),
                'finished': str(build.finished) if build.finished else None,
                'id': build.id,
                'pbw': build.pbw_url,
                'log': build.build_log_url,
                'debug': build.debug_info_url,
                'size': {
                    'total': build.total_size,
                    'binary': build.binary_size,
                    'resources': build.resource_size
                }
            })
        return json_response({"builds": out})


@require_safe
@login_required
def build_log(request, project_id, build_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    build = get_object_or_404(BuildResult, project=project, pk=build_id)
    try:
        log = build.read_build_log()
    except Exception as e:
        return json_failure(str(e))

    send_keen_event('cloudpebble', 'cloudpebble_view_build_log', data={
        'data': {
            'build_state': build.state
        }
    }, project=project, request=request)

    return json_response({"log": log})


@require_POST
@login_required
def create_project(request):
    name = request.POST['name']
    template_id = request.POST.get('template', None)
    project_type = request.POST.get('type', 'native')
    try:
        with transaction.commit_on_success():
            project = Project.objects.create(
                name=name,
                owner=request.user,
                sdk_version=2,
                app_company_name=request.user.username,
                app_short_name=name,
                app_long_name=name,
                app_version_code=1,
                app_version_label='1.0',
                app_is_watchface=False,
                app_capabilities='',
                project_type=project_type
            )
            if template_id is not None and int(template_id) != 0:
                template = TemplateProject.objects.get(pk=int(template_id))
                template.copy_into_project(project)
            elif project_type == 'simplyjs':
                f = SourceFile.objects.create(project=project, file_name="app.js")
                f.save_file(open('{}/src/html/demo.js'.format(settings.SIMPLYJS_ROOT)).read())
    except IntegrityError as e:
        return json_failure(str(e))
    else:

        send_keen_event('cloudpebble', 'cloudpebble_create_project', project=project, request=request)

        return json_response({"id": project.id})


@require_POST
@login_required
def save_project_settings(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    try:
        with transaction.commit_on_success():
            sdk_version = int(request.POST['sdk_version'])
            project.name = request.POST['name']
            project.sdk_version = sdk_version
            if sdk_version == 1:
                project.version_def_name = request.POST['version_def_name']
            elif sdk_version > 1:
                project.app_uuid = request.POST['app_uuid']
                project.app_company_name = request.POST['app_company_name']
                project.app_short_name = request.POST['app_short_name']
                project.app_long_name = request.POST['app_long_name']
                project.app_version_code = int(request.POST['app_version_code'])
                project.app_version_label = request.POST['app_version_label']
                project.app_is_watchface = bool(int(request.POST['app_is_watchface']))
                project.app_capabilities = request.POST['app_capabilities']
                project.app_keys = request.POST['app_keys']
                project.app_jshint = bool(int(request.POST['app_jshint']))

                menu_icon = request.POST['menu_icon']
                if menu_icon != '':
                    menu_icon = int(menu_icon)
                    old_icon = project.menu_icon
                    if old_icon is not None:
                        old_icon.is_menu_icon = False
                        old_icon.save()
                    icon_resource = project.resources.filter(id=menu_icon)[0]
                    icon_resource.is_menu_icon = True
                    icon_resource.save()

            project.save()
    except IntegrityError as e:
        return json_failure(str(e))
    else:
        send_keen_event('cloudpebble', 'cloudpebble_save_project_settings', project=project, request=request)

        return json_response({})


@require_POST
@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    if not bool(request.POST.get('confirm', False)):
        return json_failure("Not confirmed")
    try:
        project.delete()
    except Exception as e:
        return json_failure(str(e))
    else:
        send_keen_event('cloudpebble', 'cloudpebble_delete_project', project=project, request=request)
        return json_response({})


@login_required
@require_POST
def begin_export(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    result = create_archive.delay(project.id)
    return json_response({'task_id': result.task_id})


@login_required
@require_POST
def import_zip(request):
    zip_file = request.FILES['archive']
    name = request.POST['name']
    try:
        project = Project.objects.create(owner=request.user, name=name)
    except IntegrityError as e:
        return json_failure(str(e))
    task = do_import_archive.delay(project.id, zip_file.read(), delete_project=True)

    return json_response({'task_id': task.task_id, 'project_id': project.id})


@login_required
@require_POST
def import_github(request):
    name = request.POST['name']
    repo = request.POST['repo']
    branch = request.POST['branch']
    match = re.match(r'^(?:https?://|git@|git://)?(?:www\.)?github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git|/|$)', repo)
    if match is None:
        return HttpResponse(json.dumps({"success": False, 'error': "Invalid GitHub URL."}),
                            content_type="application/json")
    github_user = match.group(1)
    github_project = match.group(2)

    try:
        project = Project.objects.create(owner=request.user, name=name)
    except IntegrityError as e:
        return json_failure(str(e))

    task = do_import_github.delay(project.id, github_user, github_project, branch, delete_project=True)
    return json_response({'task_id': task.task_id, 'project_id': project.id})


@login_required
@require_POST
def do_import_gist(request):
    task = import_gist.delay(request.user.id, request.POST['gist_id'])
    return json_response({'task_id': task.task_id})

########NEW FILE########
__FILENAME__ = resource
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST, require_safe
from ide.api import json_failure, json_response
from ide.models.project import Project
from ide.models.files import ResourceFile, ResourceIdentifier
from utils.keen_helper import send_keen_event
import utils.s3 as s3

__author__ = 'katharine'


@require_POST
@login_required
def create_resource(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    kind = request.POST['kind']
    resource_ids = json.loads(request.POST['resource_ids'])
    file_name = request.FILES['file'].name
    resources = []
    try:
        with transaction.commit_on_success():
            rf = ResourceFile.objects.create(project=project, file_name=file_name, kind=kind)
            for r in resource_ids:
                regex = r['regex'] if 'regex' in r else None
                tracking = int(r['tracking']) if 'tracking' in r else None
                resources.append(ResourceIdentifier.objects.create(resource_file=rf, resource_id=r['id'],
                                                                   character_regex=regex, tracking=tracking))
            rf.save_file(request.FILES['file'], request.FILES['file'].size)


    except Exception as e:
        return json_failure(str(e))
    else:
        send_keen_event('cloudpebble', 'cloudpebble_create_file', data={
            'data': {
                'filename': file_name,
                'kind': 'resource',
                'resource-kind': kind
            }
        }, project=project, request=request)

        return json_response({"file": {
            "id": rf.id,
            "kind": rf.kind,
            "file_name": rf.file_name,
            "resource_ids": [{'id': x.resource_id, 'regex': x.character_regex} for x in resources],
            "identifiers": [x.resource_id for x in resources]
        }})


@require_safe
@login_required
def resource_info(request, project_id, resource_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    resource = get_object_or_404(ResourceFile, pk=resource_id)
    resources = resource.get_identifiers()

    send_keen_event('cloudpebble', 'cloudpebble_open_file', data={
        'data': {
            'filename': resource.file_name,
            'kind': 'resource',
            'resource-kind': resource.kind
        }
    }, project=project, request=request)

    return json_response({
        'resource': {
            'resource_ids': [{
                                 'id': x.resource_id,
                                 'regex': x.character_regex,
                                 'tracking': x.tracking
                             } for x in resources],
            'id': resource.id,
            'file_name': resource.file_name,
            'kind': resource.kind
        }
    })


@require_POST
@login_required
def delete_resource(request, project_id, resource_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    resource = get_object_or_404(ResourceFile, pk=resource_id, project=project)
    try:
        resource.delete()
    except Exception as e:
        return json_failure(str(e))
    else:
        send_keen_event('cloudpebble', 'cloudpebble_delete_file', data={
            'data': {
                'filename': resource.file_name,
                'kind': 'resource',
                'resource-kind': resource.kind
            }
        }, project=project, request=request)

        return json_response({})


@require_POST
@login_required
def update_resource(request, project_id, resource_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    resource = get_object_or_404(ResourceFile, pk=resource_id, project=project)
    resource_ids = json.loads(request.POST['resource_ids'])
    try:
        with transaction.commit_on_success():
            # Lazy approach: delete all the resource_ids and recreate them.
            # We could do better.
            resources = []
            ResourceIdentifier.objects.filter(resource_file=resource).delete()
            for r in resource_ids:
                regex = r['regex'] if 'regex' in r else None
                tracking = int(r['tracking']) if 'tracking' in r else None
                resources.append(ResourceIdentifier.objects.create(resource_file=resource, resource_id=r['id'], character_regex=regex, tracking=tracking))

            if 'file' in request.FILES:
                resource.save_file(request.FILES['file'], request.FILES['file'].size)
    except Exception as e:
        return json_failure(str(e))
    else:
        send_keen_event('cloudpebble', 'cloudpebble_save_file', data={
            'data': {
                'filename': resource.file_name,
                'kind': 'source'
            }
        }, project=project, request=request)

        return json_response({"file": {
            "id": resource.id,
            "kind": resource.kind,
            "file_name": resource.file_name,
            "resource_ids": [{'id': x.resource_id, 'regex': x.character_regex} for x in resources],
            "identifiers": [x.resource_id for x in resources]
        }})


@require_safe
@login_required
def show_resource(request, project_id, resource_id):
    resource = get_object_or_404(ResourceFile, pk=resource_id, project__owner=request.user)
    content_types = {
        u'png': 'image/png',
        u'png-trans': 'image/png',
        u'font': 'application/octet-stream',
        u'raw': 'application/octet-stream'
    }
    content_disposition = "attachment; filename=\"%s\"" % resource.file_name
    content_type = content_types[resource.kind]
    if settings.AWS_ENABLED:
        headers = {
            'response-content-disposition': content_disposition,
            'Content-Type': content_type
        }
        return HttpResponseRedirect(s3.get_signed_url('source', resource.s3_path, headers=headers))
    else:
        response = HttpResponse(open(resource.local_filename), content_type=content_type)
        response['Content-Disposition'] = content_disposition
        return response

########NEW FILE########
__FILENAME__ = source
import datetime
import time
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_safe
from ide.api import json_failure, json_response
from ide.models.project import Project
from ide.models.files import SourceFile
from utils.keen_helper import send_keen_event

__author__ = 'katharine'


@require_POST
@login_required
def create_source_file(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    try:
        f = SourceFile.objects.create(project=project, file_name=request.POST['name'])
        f.save_file('')
    except IntegrityError as e:
        return json_failure(str(e))
    else:
        send_keen_event('cloudpebble', 'cloudpebble_create_file', data={
            'data': {
                'filename': request.POST['name'],
                'kind': 'source'
            }
        }, project=project, request=request)

        return json_response({"file": {"id": f.id, "name": f.file_name}})


@require_safe
@csrf_protect
@login_required
def load_source_file(request, project_id, file_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    source_file = get_object_or_404(SourceFile, pk=file_id, project=project)
    try:
        content = source_file.get_contents()

        send_keen_event('cloudpebble', 'cloudpebble_open_file', data={
            'data': {
                'filename': source_file.file_name,
                'kind': 'source'
            }
        }, project=project, request=request)

    except Exception as e:
        return json_failure(str(e))
    else:
        return json_response({
            "success": True,
            "source": content,
            "modified": time.mktime(source_file.last_modified.utctimetuple())
        })


@require_safe
@csrf_protect
@login_required
def source_file_is_safe(request, project_id, file_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    source_file = get_object_or_404(SourceFile, pk=file_id, project=project)
    client_modified = datetime.datetime.fromtimestamp(int(request.GET['modified']))
    server_modified = source_file.last_modified.replace(tzinfo=None, microsecond=0)
    is_safe = client_modified >= server_modified
    return json_response({'safe': is_safe})


@require_POST
@login_required
def save_source_file(request, project_id, file_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    source_file = get_object_or_404(SourceFile, pk=file_id, project=project)
    try:
        expected_modification_time = datetime.datetime.fromtimestamp(int(request.POST['modified']))
        if source_file.last_modified.replace(tzinfo=None, microsecond=0) > expected_modification_time:
            send_keen_event('cloudpebble', 'cloudpebble_save_abort_unsafe', data={
                'data': {
                    'filename': source_file.file_name,
                    'kind': 'source'
                }
            }, project=project, request=request)
            raise Exception("Could not save: file has been modified since last save.")
        source_file.save_file(request.POST['content'])


    except Exception as e:
        return json_failure(str(e))
    else:
        send_keen_event('cloudpebble', 'cloudpebble_save_file', data={
            'data': {
                'filename': source_file.file_name,
                'kind': 'source'
            }
        }, project=project, request=request)

        return json_response({"modified": time.mktime(source_file.last_modified.utctimetuple())})


@require_POST
@login_required
def delete_source_file(request, project_id, file_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    source_file = get_object_or_404(SourceFile, pk=file_id, project=project)
    try:
        source_file.delete()
    except Exception as e:
        return json_failure(str(e))
    else:
        send_keen_event('cloudpebble', 'cloudpebble_delete_file', data={
            'data': {
                'filename': source_file.file_name,
                'kind': 'source'
            }
        }, project=project, request=request)
        return json_response({})
########NEW FILE########
__FILENAME__ = user
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from ide.api import json_response
from ide.tasks.archive import export_user_projects
from utils.keen_helper import send_keen_event
from ide.utils.whatsnew import get_new_things

__author__ = 'katharine'


@login_required
@require_POST
def transition_accept(request):
    user_settings = request.user.settings
    user_settings.accepted_terms = True
    user_settings.save()
    send_keen_event('cloudpebble', 'cloudpebble_ownership_transition_accepted', request=request)
    return json_response({})


@login_required
@require_POST
def transition_export(request):
    task = export_user_projects.delay(request.user.id)
    return json_response({"task_id": task.task_id})


@login_required
@require_POST
def transition_delete(request):
    send_keen_event('cloudpebble', 'cloudpebble_ownership_transition_declined', request=request)
    request.user.delete()
    return json_response({})

def whats_new(request):
    # Unauthenticated users never have anything new.
    if not request.user.is_authenticated():
        return json_response({'new': []})

    return json_response({'new': get_new_things(request.user)})

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm, Select

from ide.models.user import UserSettings


class SettingsForm(ModelForm):
    class Meta:
        model = UserSettings
        exclude = ('user', 'accepted_terms', 'whats_new')
        widgets = {
            'use_spaces': Select
        }

########NEW FILE########
__FILENAME__ = git
from ide.models.user import UserGithub

from github import Github, BadCredentialsException, UnknownObjectException
from github.NamedUser import NamedUser
from django.conf import settings
import base64
import json
import urllib2
import re


def git_auth_check(f):
    def g(user, *args, **kwargs):
        if not git_verify_tokens(user):
            raise Exception("Invalid user GitHub tokens.")
        try:
            return f(user, *args, **kwargs)
        except BadCredentialsException:
            # Bad credentials; remove the user's auth data.
            try:
                print "Bad credentials; revoking user's github tokens."
                github = user.github
                github.delete()
            except:
                pass
            raise
    return g


def git_verify_tokens(user):
    try:
        token = user.github.token
    except UserGithub.DoesNotExist:
        return False
    if token is None:
        return False

    auth_string = base64.encodestring('%s:%s' %
                                      (settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET)).replace('\n', '')
    r = urllib2.Request('https://api.github.com/applications/%s/tokens/%s' % (settings.GITHUB_CLIENT_ID, token))
    r.add_header("Authorization", "Basic %s" % auth_string)
    try:
        json.loads(urllib2.urlopen(r).read())
    except urllib2.HTTPError as e:
        # No such token
        if e.getcode() == 404:
            github = user.github
            github.delete()
        return False
    return True


def get_github(user):
    return Github(user.github.token, client_id=settings.GITHUB_CLIENT_ID, client_secret=settings.GITHUB_CLIENT_SECRET)


def check_repo_access(user, repo):
    g = get_github(user)
    try:
        repo = g.get_repo(repo)
    except UnknownObjectException:
        raise

    return repo.has_in_collaborators(NamedUser(None, {'login': user.github.username}, False))


def url_to_repo(url):
    match = re.match(r'^(?:https?://|git@|git://)?(?:www\.)?github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git|/|$)', url)
    if match is None:
        return None
    else:
        return match.group(1), match.group(2)


@git_auth_check
def create_repo(user, repo_name, description):
    g = get_github(user)
    user = g.get_user()
    return user.create_repo(repo_name, description=description, auto_init=True)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Project'
        db.create_table(u'ide_project', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('version_def_name', self.gf('django.db.models.fields.CharField')(default='APP_RESOURCES', max_length=50)),
        ))
        db.send_create_signal(u'ide', ['Project'])

        # Adding unique constraint on 'Project', fields ['owner', 'name']
        db.create_unique(u'ide_project', ['owner_id', 'name'])

        # Adding model 'TemplateProject'
        db.create_table(u'ide_templateproject', (
            (u'project_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['ide.Project'], unique=True, primary_key=True)),
            ('template_kind', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
        ))
        db.send_create_signal(u'ide', ['TemplateProject'])

        # Adding model 'BuildResult'
        db.create_table(u'ide_buildresult', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='builds', to=orm['ide.Project'])),
            ('uuid', self.gf('django.db.models.fields.CharField')(default='8277f892d4d84a69ba21c3989a02c61c', max_length=32)),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('started', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('finished', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'ide', ['BuildResult'])

        # Adding model 'ResourceFile'
        db.create_table(u'ide_resourcefile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='resources', to=orm['ide.Project'])),
            ('file_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=9)),
        ))
        db.send_create_signal(u'ide', ['ResourceFile'])

        # Adding unique constraint on 'ResourceFile', fields ['project', 'file_name']
        db.create_unique(u'ide_resourcefile', ['project_id', 'file_name'])

        # Adding model 'ResourceIdentifier'
        db.create_table(u'ide_resourceidentifier', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('resource_file', self.gf('django.db.models.fields.related.ForeignKey')(related_name='identifiers', to=orm['ide.ResourceFile'])),
            ('resource_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('character_regex', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'ide', ['ResourceIdentifier'])

        # Adding unique constraint on 'ResourceIdentifier', fields ['resource_file', 'resource_id']
        db.create_unique(u'ide_resourceidentifier', ['resource_file_id', 'resource_id'])

        # Adding model 'SourceFile'
        db.create_table(u'ide_sourcefile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='source_files', to=orm['ide.Project'])),
            ('file_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'ide', ['SourceFile'])

        # Adding unique constraint on 'SourceFile', fields ['project', 'file_name']
        db.create_unique(u'ide_sourcefile', ['project_id', 'file_name'])


    def backwards(self, orm):
        # Removing unique constraint on 'SourceFile', fields ['project', 'file_name']
        db.delete_unique(u'ide_sourcefile', ['project_id', 'file_name'])

        # Removing unique constraint on 'ResourceIdentifier', fields ['resource_file', 'resource_id']
        db.delete_unique(u'ide_resourceidentifier', ['resource_file_id', 'resource_id'])

        # Removing unique constraint on 'ResourceFile', fields ['project', 'file_name']
        db.delete_unique(u'ide_resourcefile', ['project_id', 'file_name'])

        # Removing unique constraint on 'Project', fields ['owner', 'name']
        db.delete_unique(u'ide_project', ['owner_id', 'name'])

        # Deleting model 'Project'
        db.delete_table(u'ide_project')

        # Deleting model 'TemplateProject'
        db.delete_table(u'ide_templateproject')

        # Deleting model 'BuildResult'
        db.delete_table(u'ide_buildresult')

        # Deleting model 'ResourceFile'
        db.delete_table(u'ide_resourcefile')

        # Deleting model 'ResourceIdentifier'
        db.delete_table(u'ide_resourceidentifier')

        # Deleting model 'SourceFile'
        db.delete_table(u'ide_sourcefile')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'7d2901ebedec4f708e706c6424a71e73'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0002_auto__add_usersettings
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserSettings'
        db.create_table(u'ide_usersettings', (
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, primary_key=True)),
            ('autocomplete', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('keybinds', self.gf('django.db.models.fields.CharField')(default='default', max_length=20)),
            ('theme', self.gf('django.db.models.fields.CharField')(default='monokai', max_length=50)),
        ))
        db.send_create_signal(u'ide', ['UserSettings'])


    def backwards(self, orm):
        # Deleting model 'UserSettings'
        db.delete_table(u'ide_usersettings')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'60ecc2bfee1b46df8898ee12cf459c82'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0003_auto__add_field_resourceidentifier_tracking
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ResourceIdentifier.tracking'
        db.add_column(u'ide_resourceidentifier', 'tracking',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ResourceIdentifier.tracking'
        db.delete_column(u'ide_resourceidentifier', 'tracking')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'2765898af0814777b244dd8a12be1b2c'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0004_auto__add_usergithub
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserGithub'
        db.create_table(u'ide_usergithub', (
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='github', unique=True, primary_key=True, to=orm['auth.User'])),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('nonce', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('username', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('avatar', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
        ))
        db.send_create_signal(u'ide', ['UserGithub'])


    def backwards(self, orm):
        # Deleting model 'UserGithub'
        db.delete_table(u'ide_usergithub')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'e8c9ae7f6653478c824b5538d1ef0da4'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0005_auto__add_project_github_fields
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.github_repo'
        db.add_column(u'ide_project', 'github_repo',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.github_last_sync'
        db.add_column(u'ide_project', 'github_last_sync',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.github_last_commit'
        db.add_column(u'ide_project', 'github_last_commit',
                      self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.github_repo'
        db.delete_column(u'ide_project', 'github_repo')

        # Deleting field 'Project.github_last_sync'
        db.delete_column(u'ide_project', 'github_last_sync')

        # Deleting field 'Project.github_last_commit'
        db.delete_column(u'ide_project', 'github_last_commit')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'1d0871da2d19428ea6bac6d927cc9a2a'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_project_github_hook
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.github_hook_uuid'
        db.add_column(u'ide_project', 'github_hook_uuid',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.github_hook_build'
        db.add_column(u'ide_project', 'github_hook_build',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.github_hook_uuid'
        db.delete_column(u'ide_project', 'github_hook_uuid')

        # Deleting field 'Project.github_hook_build'
        db.delete_column(u'ide_project', 'github_hook_build')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'96fee97157464b319c41c43fb8607009'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0007_auto__add_field_project_optimisation
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.optimisation'
        db.add_column(u'ide_project', 'optimisation',
                      self.gf('django.db.models.fields.CharField')(default='0', max_length=1),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.optimisation'
        db.delete_column(u'ide_project', 'optimisation')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'e3737ad854eb41dcaa581678c7f0d68d'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'0'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0008_auto__add_field_buildresult_sizes
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'BuildResult.total_size'
        db.add_column(u'ide_buildresult', 'total_size',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'BuildResult.binary_size'
        db.add_column(u'ide_buildresult', 'binary_size',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'BuildResult.resource_size'
        db.add_column(u'ide_buildresult', 'resource_size',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'BuildResult.total_size'
        db.delete_column(u'ide_buildresult', 'total_size')

        # Deleting field 'BuildResult.binary_size'
        db.delete_column(u'ide_buildresult', 'binary_size')

        # Deleting field 'BuildResult.resource_size'
        db.delete_column(u'ide_buildresult', 'resource_size')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'8bf5c1508e8a44ac830ad715728940cf'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'0'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0009_auto__add_field_project_sdk_version__add_field_project_app_uuid__add_f
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.sdk_version'
        db.add_column(u'ide_project', 'sdk_version',
                      self.gf('django.db.models.fields.CharField')(default='1', max_length=10),
                      keep_default=False)

        # Adding field 'Project.app_uuid'
        db.add_column(u'ide_project', 'app_uuid',
                      self.gf('django.db.models.fields.CharField')(max_length=36, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.app_company_name'
        db.add_column(u'ide_project', 'app_company_name',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.app_short_name'
        db.add_column(u'ide_project', 'app_short_name',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.app_long_name'
        db.add_column(u'ide_project', 'app_long_name',
                      self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.app_version_code'
        db.add_column(u'ide_project', 'app_version_code',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.app_version_label'
        db.add_column(u'ide_project', 'app_version_label',
                      self.gf('django.db.models.fields.CharField')(max_length=40, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Project.app_is_watchface'
        db.add_column(u'ide_project', 'app_is_watchface',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Project.app_capabilities'
        db.add_column(u'ide_project', 'app_capabilities',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.sdk_version'
        db.delete_column(u'ide_project', 'sdk_version')

        # Deleting field 'Project.app_uuid'
        db.delete_column(u'ide_project', 'app_uuid')

        # Deleting field 'Project.app_company_name'
        db.delete_column(u'ide_project', 'app_company_name')

        # Deleting field 'Project.app_short_name'
        db.delete_column(u'ide_project', 'app_short_name')

        # Deleting field 'Project.app_long_name'
        db.delete_column(u'ide_project', 'app_long_name')

        # Deleting field 'Project.app_version_code'
        db.delete_column(u'ide_project', 'app_version_code')

        # Deleting field 'Project.app_version_label'
        db.delete_column(u'ide_project', 'app_version_label')

        # Deleting field 'Project.app_is_watchface'
        db.delete_column(u'ide_project', 'app_is_watchface')

        # Deleting field 'Project.app_capabilities'
        db.delete_column(u'ide_project', 'app_capabilities')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'ef048180d22c4383bcd64b1379f1aa5c'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0010_auto__add_field_project_app_keys
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.app_keys'
        db.add_column(u'ide_project', 'app_keys',
                      self.gf('django.db.models.fields.TextField')(default='{}'),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.app_keys'
        db.delete_column(u'ide_project', 'app_keys')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'3982c9ed238c4ab198b4fe7fafff3bf2'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'70478186-d93e-48e7-9a18-f27f500fe400'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0011_auto__add_field_resourcefile_is_menu_icon
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ResourceFile.is_menu_icon'
        db.add_column(u'ide_resourcefile', 'is_menu_icon',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ResourceFile.is_menu_icon'
        db.delete_column(u'ide_resourcefile', 'is_menu_icon')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'8c6875613b36479990c41871fbd5f2d2'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'c43d4d1a-9d25-4849-871f-ed840e962cc2'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0012_auto__add_field_usersettings_accepted_terms
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserSettings.accepted_terms'
        db.add_column(u'ide_usersettings', 'accepted_terms',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserSettings.accepted_terms'
        db.delete_column(u'ide_usersettings', 'accepted_terms')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'a38444b9-0c81-46ac-86d8-6e7f429b3cd5'", 'max_length': '32'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'7ff27d43-a881-41a6-a309-b153d3d411bd'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0013_auto__chg_field_buildresult_uuid__chg_field_usergithub_nonce__chg_fiel
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'BuildResult.uuid'
        db.alter_column(u'ide_buildresult', 'uuid', self.gf('django.db.models.fields.CharField')(max_length=36))

        # Changing field 'UserGithub.nonce'
        db.alter_column(u'ide_usergithub', 'nonce', self.gf('django.db.models.fields.CharField')(max_length=36, null=True))

        # Changing field 'Project.github_hook_uuid'
        db.alter_column(u'ide_project', 'github_hook_uuid', self.gf('django.db.models.fields.CharField')(max_length=36, null=True))

    def backwards(self, orm):

        # Changing field 'BuildResult.uuid'
        db.alter_column(u'ide_buildresult', 'uuid', self.gf('django.db.models.fields.CharField')(max_length=32))

        # Changing field 'UserGithub.nonce'
        db.alter_column(u'ide_usergithub', 'nonce', self.gf('django.db.models.fields.CharField')(max_length=32, null=True))

        # Changing field 'Project.github_hook_uuid'
        db.alter_column(u'ide_project', 'github_hook_uuid', self.gf('django.db.models.fields.CharField')(max_length=32, null=True))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'53ef7f12-c535-405b-981b-4ea8fa271e49'", 'max_length': '36'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'6cacf52d-f151-4e94-8707-654b1305c3eb'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0014_auto__add_field_project_app_jshint
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.app_jshint'
        db.add_column(u'ide_project', 'app_jshint',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.app_jshint'
        db.delete_column(u'ide_project', 'app_jshint')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'df1dbda5-d688-4b2d-998a-a6e445c589af'", 'max_length': '36'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_jshint': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'783f4370-3a43-4ac3-9efb-a9b679d17d5e'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0015_auto__add_field_project_github_branch
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.github_branch'
        db.add_column(u'ide_project', 'github_branch',
              self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True),
              keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.github_branch'
        db.delete_column(u'ide_project', 'github_branch')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'df1dbda5-d688-4b2d-998a-a6e445c589af'", 'max_length': '36'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_jshint': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'783f4370-3a43-4ac3-9efb-a9b679d17d5e'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'github_branch': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0016_auto__add_field_usersettings_use_spaces__add_field_usersettings_tab_wi
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserSettings.use_spaces'
        db.add_column(u'ide_usersettings', 'use_spaces',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'UserSettings.tab_width'
        db.add_column(u'ide_usersettings', 'tab_width',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=2),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserSettings.use_spaces'
        db.delete_column(u'ide_usersettings', 'use_spaces')

        # Deleting field 'UserSettings.tab_width'
        db.delete_column(u'ide_usersettings', 'tab_width')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'cc341e50-d269-47fc-b028-93b32b2a409d'", 'max_length': '36'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_jshint': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'55824e27-33c7-4cd9-a616-89697f55467f'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_branch': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'tab_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'use_spaces': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0017_auto__add_field_sourcefile_last_modified
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'SourceFile.last_modified'
        db.add_column(u'ide_sourcefile', 'last_modified',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'SourceFile.last_modified'
        db.delete_column(u'ide_sourcefile', 'last_modified')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': u"orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'16fddb3b-a6cf-48b8-ac6e-6e14c05096ab'", 'max_length': '36'})
        },
        u'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_jshint': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'37b188aa-2388-4c97-9c26-260e4976ff4a'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_branch': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        u'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': u"orm['ide.Project']"})
        },
        u'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': u"orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': u"orm['ide.Project']"})
        },
        u'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': [u'ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        u'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'tab_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'use_spaces': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0018_auto__add_field_project_project_type
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Project.project_type'
        db.add_column(u'ide_project', 'project_type',
                      self.gf('django.db.models.fields.CharField')(default='native', max_length=10),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Project.project_type'
        db.delete_column(u'ide_project', 'project_type')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': "orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'b84e091c-1712-4e5d-973b-e37323897fd8'", 'max_length': '36'})
        },
        'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_jshint': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'4b4975dc-0fca-43d1-b212-dc2f4209c8b2'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_branch': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'default': "'native'", 'max_length': '10'}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': "orm['ide.Project']"})
        },
        'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': "orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': "orm['ide.Project']"})
        },
        'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': ['ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'tab_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'use_spaces': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0019_auto__add_field_usersettings_whats_new
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserSettings.whats_new'
        db.add_column(u'ide_usersettings', 'whats_new',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserSettings.whats_new'
        db.delete_column(u'ide_usersettings', 'whats_new')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': "orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'37a2b468-46d7-40b4-8c99-e964e2c5b8ea'", 'max_length': '36'})
        },
        'ide.project': {
            'Meta': {'unique_together': "(('owner', 'name'),)", 'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_jshint': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'42e4b2a4-218a-4535-90be-679476384dd1'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_branch': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'default': "'native'", 'max_length': '10'}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': "orm['ide.Project']"})
        },
        'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': "orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': "orm['ide.Project']"})
        },
        'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': ['ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'tab_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'use_spaces': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'whats_new': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = 0020_auto__del_unique_project_owner_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Project', fields ['owner', 'name']
        db.delete_unique(u'ide_project', ['owner_id', 'name'])


    def backwards(self, orm):
        # Adding unique constraint on 'Project', fields ['owner', 'name']
        db.create_unique(u'ide_project', ['owner_id', 'name'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ide.buildresult': {
            'Meta': {'object_name': 'BuildResult'},
            'binary_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'builds'", 'to': "orm['ide.Project']"}),
            'resource_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'total_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'default': "'995830db-5a29-4dc4-9ee6-13cb114e67ec'", 'max_length': '36'})
        },
        'ide.project': {
            'Meta': {'object_name': 'Project'},
            'app_capabilities': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'app_company_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_is_watchface': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'app_jshint': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app_keys': ('django.db.models.fields.TextField', [], {'default': "'{}'"}),
            'app_long_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_short_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'app_uuid': ('django.db.models.fields.CharField', [], {'default': "'385ee8f4-632c-4c04-9616-51a8fffdd0e7'", 'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'app_version_code': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'app_version_label': ('django.db.models.fields.CharField', [], {'default': "'1.0'", 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_branch': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'github_hook_build': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_hook_uuid': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'github_last_commit': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'github_last_sync': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'github_repo': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'optimisation': ('django.db.models.fields.CharField', [], {'default': "'s'", 'max_length': '1'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'project_type': ('django.db.models.fields.CharField', [], {'default': "'native'", 'max_length': '10'}),
            'sdk_version': ('django.db.models.fields.CharField', [], {'default': "'1'", 'max_length': '10'}),
            'version_def_name': ('django.db.models.fields.CharField', [], {'default': "'APP_RESOURCES'", 'max_length': '50'})
        },
        'ide.resourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'ResourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_menu_icon': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'resources'", 'to': "orm['ide.Project']"})
        },
        'ide.resourceidentifier': {
            'Meta': {'unique_together': "(('resource_file', 'resource_id'),)", 'object_name': 'ResourceIdentifier'},
            'character_regex': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_file': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identifiers'", 'to': "orm['ide.ResourceFile']"}),
            'resource_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'tracking': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'ide.sourcefile': {
            'Meta': {'unique_together': "(('project', 'file_name'),)", 'object_name': 'SourceFile'},
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_files'", 'to': "orm['ide.Project']"})
        },
        'ide.templateproject': {
            'Meta': {'object_name': 'TemplateProject', '_ormbases': ['ide.Project']},
            u'project_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ide.Project']", 'unique': 'True', 'primary_key': 'True'}),
            'template_kind': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'})
        },
        'ide.usergithub': {
            'Meta': {'object_name': 'UserGithub'},
            'avatar': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'nonce': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'github'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['auth.User']"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        'ide.usersettings': {
            'Meta': {'object_name': 'UserSettings'},
            'accepted_terms': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'autocomplete': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'keybinds': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '20'}),
            'tab_width': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'}),
            'theme': ('django.db.models.fields.CharField', [], {'default': "'monokai'", 'max_length': '50'}),
            'use_spaces': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'whats_new': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'})
        }
    }

    complete_apps = ['ide']
########NEW FILE########
__FILENAME__ = build
import uuid
import json
import shutil
import os
import os.path
from django.conf import settings
from django.db import models
from ide.models.project import Project

from ide.models.meta import IdeModel

import utils.s3 as s3
__author__ = 'katharine'


class BuildResult(IdeModel):

    STATE_WAITING = 1
    STATE_FAILED = 2
    STATE_SUCCEEDED = 3
    STATE_CHOICES = (
        (STATE_WAITING, 'Pending'),
        (STATE_FAILED, 'Failed'),
        (STATE_SUCCEEDED, 'Succeeded')
    )

    project = models.ForeignKey(Project, related_name='builds')
    uuid = models.CharField(max_length=36, default=lambda:str(uuid.uuid4()))
    state = models.IntegerField(choices=STATE_CHOICES, default=STATE_WAITING)
    started = models.DateTimeField(auto_now_add=True, db_index=True)
    finished = models.DateTimeField(blank=True, null=True)

    total_size = models.IntegerField(blank=True, null=True)
    binary_size = models.IntegerField(blank=True, null=True)
    resource_size = models.IntegerField(blank=True, null=True)

    def _get_dir(self):
        if settings.AWS_ENABLED:
            return '%s/' % self.uuid
        else:
            path = '%s%s/%s/%s/' % (settings.MEDIA_ROOT, self.uuid[0], self.uuid[1], self.uuid)
            if not os.path.exists(path):
                os.makedirs(path)
            return path

    def get_url(self):
        if settings.AWS_ENABLED:
            return "%s%s/" % (settings.MEDIA_URL, self.uuid)
        else:
            return '%s%s/%s/%s/' % (settings.MEDIA_URL, self.uuid[0], self.uuid[1], self.uuid)

    def get_pbw_filename(self):
        return '%swatchface.pbw' % self._get_dir()

    def get_build_log(self):
        return '%sbuild_log.txt' % self._get_dir()

    def get_pbw_url(self):
        return '%swatchface.pbw' % self.get_url()

    def get_build_log_url(self):
        return '%sbuild_log.txt' % self.get_url()

    def get_debug_info_filename(self):
        return '%sdebug_info.json' % self._get_dir()

    def get_debug_info_url(self):
        return '%sdebug_info.json' % self.get_url()

    def get_simplyjs(self):
        return '%ssimply.js' % self._get_dir()

    def get_simplyjs_url(self):
        return '%ssimply.js' % self.get_url()

    def save_build_log(self, text):
        if not settings.AWS_ENABLED:
            with open(self.build_log, 'w') as f:
                f.write(text)
        else:
            s3.save_file('builds', self.build_log, text, public=True, content_type='text/plain')

    def read_build_log(self):
        if not settings.AWS_ENABLED:
            with open(self.build_log, 'w') as f:
                return f.read()
        else:
            return s3.read_file('builds', self.build_log)

    def save_debug_info(self, json_info):
        text = json.dumps(json_info)
        if not settings.AWS_ENABLED:
            with open(self.debug_info, 'w') as f:
                f.write(text)
        else:
            s3.save_file('builds', self.debug_info, text, public=True, content_type='application/json')

    def save_pbw(self, pbw_path):
        if not settings.AWS_ENABLED:
            shutil.move(pbw_path, self.pbw)
        else:
            s3.upload_file('builds', self.pbw, pbw_path, public=True, download_filename='%s.pbw' % self.project.app_short_name.replace('/','-'))

    def save_simplyjs(self, javascript):
        if not settings.AWS_ENABLED:
            with open(self.simplyjs, 'w') as f:
                f.write(javascript)
        else:
            s3.save_file('builds', self.simplyjs, javascript, public=True, content_type='text/javascript')

    pbw = property(get_pbw_filename)
    build_log = property(get_build_log)

    pbw_url = property(get_pbw_url)
    build_log_url = property(get_build_log_url)

    debug_info = property(get_debug_info_filename)
    debug_info_url = property(get_debug_info_url)

    simplyjs = property(get_simplyjs)
    simplyjs_url = property(get_simplyjs_url)

########NEW FILE########
__FILENAME__ = files
import os
import shutil
from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.timezone import now
import utils.s3 as s3

from ide.models.meta import IdeModel

__author__ = 'katharine'


class ResourceFile(IdeModel):
    project = models.ForeignKey('Project', related_name='resources')
    RESOURCE_KINDS = (
        ('raw', 'Binary blob'),
        ('png', '1-bit PNG'),
        ('png-trans', '1-bit PNG with transparency'),
        ('font', 'True-Type Font')
    )

    file_name = models.CharField(max_length=100)
    kind = models.CharField(max_length=9, choices=RESOURCE_KINDS)
    is_menu_icon = models.BooleanField(default=False)

    def get_local_filename(self, create=False):
        padded_id = '%05d' % self.id
        filename = '%sresources/%s/%s/%s' % (settings.FILE_STORAGE, padded_id[0], padded_id[1], padded_id)
        if create:
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
        return filename

    def get_s3_path(self):
        return 'resources/%s' % self.id

    local_filename = property(get_local_filename)
    s3_path = property(get_s3_path)

    def save_file(self, stream, file_size=0):
        if file_size > 5*1024*1024:
            raise Exception("Uploaded file too big.");
        if not settings.AWS_ENABLED:
            if not os.path.exists(os.path.dirname(self.local_filename)):
                os.makedirs(os.path.dirname(self.local_filename))
            with open(self.local_filename, 'wb') as out:
                out.write(stream.read())
        else:
            s3.save_file('source', self.s3_path, stream.read())

        self.project.last_modified = now()
        self.project.save()

    def save_string(self, string):
        if not settings.AWS_ENABLED:
            if not os.path.exists(os.path.dirname(self.local_filename)):
                os.makedirs(os.path.dirname(self.local_filename))
            with open(self.local_filename, 'wb') as out:
                out.write(string)
        else:
            s3.save_file('source', self.s3_path, string)

    def get_contents(self):
        if not settings.AWS_ENABLED:
            return open(self.local_filename).read()
        else:
            return s3.read_file('source', self.s3_path)

    def get_identifiers(self):
        return ResourceIdentifier.objects.filter(resource_file=self)

    def copy_to_path(self, path):
        if not settings.AWS_ENABLED:
            shutil.copy(self.local_filename, path)
        else:
            s3.read_file_to_filesystem('source', self.s3_path, path)

    def save(self, *args, **kwargs):
        self.project.last_modified = now()
        self.project.save()
        super(ResourceFile, self).save(*args, **kwargs)

    DIR_MAP = {
        'png': 'images',
        'png-trans': 'images',
        'font': 'fonts',
        'raw': 'data'
    }

    def get_path(self):
        return '%s/%s' % (self.DIR_MAP[self.kind], self.file_name)

    path = property(get_path)

    class Meta(IdeModel.Meta):
        unique_together = (('project', 'file_name'),)


class ResourceIdentifier(IdeModel):
    resource_file = models.ForeignKey(ResourceFile, related_name='identifiers')
    resource_id = models.CharField(max_length=100)
    character_regex = models.CharField(max_length=100, blank=True, null=True)
    tracking = models.IntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.resource_file.project.last_modified = now()
        self.resource_file.project.save()
        super(ResourceIdentifier, self).save(*args, **kwargs)

    class Meta(IdeModel.Meta):
        unique_together = (('resource_file', 'resource_id'),)


class SourceFile(IdeModel):
    project = models.ForeignKey('Project', related_name='source_files')
    file_name = models.CharField(max_length=100)
    last_modified = models.DateTimeField(blank=True, null=True, auto_now=True)

    def get_local_filename(self):
        padded_id = '%05d' % self.id
        return '%ssources/%s/%s/%s' % (settings.FILE_STORAGE, padded_id[0], padded_id[1], padded_id)

    def get_s3_path(self):
        return 'sources/%d' % self.id

    def get_contents(self):
        if not settings.AWS_ENABLED:
            try:
                return open(self.local_filename).read()
            except IOError:
                return ''
        else:
            return s3.read_file('source', self.s3_path)

    def save_file(self, content):
        if not settings.AWS_ENABLED:
            if not os.path.exists(os.path.dirname(self.local_filename)):
                os.makedirs(os.path.dirname(self.local_filename))
            open(self.local_filename, 'w').write(content.encode('utf-8'))
        else:
            s3.save_file('source', self.s3_path, content.encode('utf-8'))

        self.save()

    def copy_to_path(self, path):
        if not settings.AWS_ENABLED:
            try:
                shutil.copy(self.local_filename, path)
            except IOError as err:
                if err.errno == 2:
                    open(path, 'w').close()  # create the file if it's missing.
                else:
                    raise
        else:
            s3.read_file_to_filesystem('source', self.s3_path, path)

    def save(self, *args, **kwargs):
        self.project.last_modified = now()
        self.project.save()
        super(SourceFile, self).save(*args, **kwargs)

    local_filename = property(get_local_filename)
    s3_path = property(get_s3_path)

    class Meta(IdeModel.Meta):
        unique_together = (('project', 'file_name'))


@receiver(post_delete)
def delete_file(sender, instance, **kwargs):
    if sender == SourceFile or sender == ResourceFile:
        try:
            os.unlink(instance.local_filename)
        except OSError:
            pass
########NEW FILE########
__FILENAME__ = meta
from django.db import models

class IdeModel(models.Model):
    class Meta:
        abstract = True
        app_label = "ide"

########NEW FILE########
__FILENAME__ = project
import shutil
import uuid

from django.contrib.auth.models import User
from django.db import models

from ide.models.files import ResourceFile, ResourceIdentifier, SourceFile
from ide.utils import generate_half_uuid

from ide.models.meta import IdeModel

__author__ = 'katharine'

class Project(IdeModel):
    owner = models.ForeignKey(User)
    name = models.CharField(max_length=50)
    last_modified = models.DateTimeField(auto_now_add=True)
    version_def_name = models.CharField(max_length=50, default="APP_RESOURCES")
    SDK_VERSIONS = (
        ('1', '1.1.2'),
        ('2', '2.0')
    )
    sdk_version = models.CharField(max_length=10, choices=SDK_VERSIONS, default='1')

    PROJECT_TYPES = (
        ('native', 'Native SDK'),
        ('simplyjs', 'Simply.JS')
    )
    project_type = models.CharField(max_length=10, choices=PROJECT_TYPES, default='native')

    # New settings for 2.0
    app_uuid = models.CharField(max_length=36, blank=True, null=True, default=generate_half_uuid)
    app_company_name = models.CharField(max_length=100, blank=True, null=True)
    app_short_name = models.CharField(max_length=100, blank=True, null=True)
    app_long_name = models.CharField(max_length=100, blank=True, null=True)
    app_version_code = models.IntegerField(blank=True, null=True, default=1)
    app_version_label = models.CharField(max_length=40, blank=True, null=True, default='1.0')
    app_is_watchface = models.BooleanField(default=False)
    app_capabilities = models.CharField(max_length=255, blank=True, null=True)
    app_keys = models.TextField(default="{}")
    app_jshint = models.BooleanField(default=True)

    app_capability_list = property(lambda self: self.app_capabilities.split(','))

    OPTIMISATION_CHOICES = (
        ('0', 'None'),
        ('1', 'Limited'),
        ('s', 'Prefer smaller'),
        ('2', 'Prefer faster'),
        ('3', 'Aggressive (faster, bigger)'),
    )

    optimisation = models.CharField(max_length=1, choices=OPTIMISATION_CHOICES, default='s')

    github_repo = models.CharField(max_length=100, blank=True, null=True)
    github_branch = models.CharField(max_length=100, blank=True, null=True)
    github_last_sync = models.DateTimeField(blank=True, null=True)
    github_last_commit = models.CharField(max_length=40, blank=True, null=True)
    github_hook_uuid = models.CharField(max_length=36, blank=True, null=True)
    github_hook_build = models.BooleanField(default=False)

    def get_last_build(self):
        try:
            return self.builds.order_by('-id')[0]
        except IndexError:
            return None

    def get_menu_icon(self):
        try:
            return self.resources.filter(is_menu_icon=True)[0]
        except IndexError:
            return None

    last_build = property(get_last_build)
    menu_icon = property(get_menu_icon)

    def __unicode__(self):
        return u"%s" % self.name



class TemplateProject(Project):
    KIND_TEMPLATE = 1
    KIND_SDK_DEMO = 2
    KIND_EXAMPLE = 3
    KIND_CHOICES = (
        (KIND_TEMPLATE, 'Template'),
        (KIND_SDK_DEMO, 'SDK Demo'),
        (KIND_EXAMPLE, 'Example')
    )

    template_kind = models.IntegerField(choices=KIND_CHOICES, db_index=True)

    def copy_into_project(self, project):
        uuid_string = ", ".join(["0x%02X" % ord(b) for b in uuid.uuid4().bytes])
        for resource in self.resources.all():
            new_resource = ResourceFile.objects.create(project=project, file_name=resource.file_name, kind=resource.kind)
            new_resource.save_string(resource.get_contents())
            for i in resource.identifiers.all():
                ResourceIdentifier.objects.create(resource_file=new_resource, resource_id=i.resource_id, character_regex=i.character_regex)

        for source_file in self.source_files.all():
            new_file = SourceFile.objects.create(project=project, file_name=source_file.file_name)
            new_file.save_file(source_file.get_contents().replace("__UUID_GOES_HERE__", uuid_string))

        # Copy over relevant project properties.
        # NOTE: If new, relevant properties are added, they must be copied here.
        # todo: can we do better than that? Maybe we could reuse the zip import mechanism or something...
        if self.sdk_version != '1':
            project.app_capabilities = self.app_capabilities
            project.app_is_watchface = self.app_is_watchface
            project.app_keys = self.app_keys
            project.app_jshint = self.app_jshint
            project.save()
########NEW FILE########
__FILENAME__ = user
from django.contrib.auth.models import User
from django.db import models

from ide.models.meta import IdeModel
from ide.utils.whatsnew import count_things

__author__ = 'katharine'


class UserSettings(IdeModel):
    user = models.OneToOneField(User, primary_key=True)

    AUTOCOMPLETE_ALWAYS = 1
    AUTOCOMPLETE_EXPLICIT = 2
    AUTOCOMPLETE_NEVER = 3
    AUTOCOMPLETE_CHOICES = (
        (AUTOCOMPLETE_ALWAYS, 'As-you-type'),
        (AUTOCOMPLETE_EXPLICIT, 'When pressing Ctrl-Space'),
        (AUTOCOMPLETE_NEVER, 'Never')
    )

    KEYBIND_STANDARD = 'default'
    KEYBIND_VIM = 'vim'
    KEYBIND_EMACS = 'emacs'
    KEYBIND_CHOICES = (
        (KEYBIND_STANDARD, 'Standard'),
        (KEYBIND_VIM, 'vim-like'),
        (KEYBIND_EMACS, 'emacs-like')
    )

    THEME_CHOICES = (
        ('cloudpebble', 'CloudPebble'),
        ('monokai', 'Monokai (Sublime Text)'),
        ('blackboard', 'Blackboard (TextMate)'),
        ('eclipse', 'Eclipse'),
        ('solarized light', 'Solarized (light)'),
        ('solarized dark', 'Solarized (dark)'),
    )

    USE_SPACES_CHOICES = (
        (True, 'Using spaces'),
        (False, 'Using tabs')
    )

    def __unicode__(self):
        return self.user.name

    autocomplete = models.IntegerField(choices=AUTOCOMPLETE_CHOICES, default=AUTOCOMPLETE_ALWAYS)
    keybinds = models.CharField(max_length=20, choices=KEYBIND_CHOICES, default=KEYBIND_STANDARD)
    theme = models.CharField(max_length=50, choices=THEME_CHOICES, default='cloudpebble')
    use_spaces = models.BooleanField(default=True, verbose_name="Indents", choices=USE_SPACES_CHOICES)
    tab_width = models.PositiveSmallIntegerField(default=2)

    # Used for the Pebble ownership transition, when it was set to False.
    accepted_terms = models.BooleanField(default=True)

    # What "what's new" prompt have they seen?
    whats_new = models.PositiveIntegerField(default=count_things)

User.settings = property(lambda self: UserSettings.objects.get_or_create(user=self)[0])


class UserGithub(IdeModel):
    user = models.OneToOneField(User, primary_key=True, related_name='github')
    token = models.CharField(max_length=50, null=True, blank=True)
    nonce = models.CharField(max_length=36, null=True, blank=True)
    username = models.CharField(max_length=50, null=True, blank=True)
    avatar = models.CharField(max_length=255, null=True, blank=True)
########NEW FILE########
__FILENAME__ = archive
import os
import re
import shutil
import tempfile
import uuid
import zipfile
import json
from celery import task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from ide.utils.project import find_project_root
from ide.utils.sdk import generate_resource_map, generate_v2_manifest, generate_wscript_file, generate_jshint_file, \
    dict_to_pretty_json
from utils.keen_helper import send_keen_event

from ide.models.files import SourceFile, ResourceFile, ResourceIdentifier
from ide.models.project import Project
import utils.s3 as s3

__author__ = 'katharine'


def add_project_to_archive(z, project, prefix=''):
    source_files = SourceFile.objects.filter(project=project)
    resources = ResourceFile.objects.filter(project=project)
    prefix += re.sub(r'[^\w]+', '_', project.name).strip('_').lower()

    for source in source_files:
        z.writestr('%s/src/%s' % (prefix, source.file_name), source.get_contents())

    for resource in resources:
        res_path = 'resources/src' if project.sdk_version == '1' else 'resources'
        z.writestr('%s/%s/%s' % (prefix, res_path, resource.path), resource.get_contents())

    if project.sdk_version == '1':
        resource_map = generate_resource_map(project, resources)
        z.writestr('%s/resources/src/resource_map.json' % prefix, resource_map)
    else:
        manifest = generate_v2_manifest(project, resources)
        z.writestr('%s/appinfo.json' % prefix, manifest)
        # This file is always the same, but needed to build.
        z.writestr('%s/wscript' % prefix, generate_wscript_file(project, for_export=True))
        z.writestr('%s/jshintrc' % prefix, generate_jshint_file(project))


@task(acks_late=True)
def create_archive(project_id):
    project = Project.objects.get(pk=project_id)
    prefix = re.sub(r'[^\w]+', '_', project.name).strip('_').lower()
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp:
        filename = temp.name
        with zipfile.ZipFile(filename, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            add_project_to_archive(z, project)

        # Generate a URL
        u = uuid.uuid4().hex

        send_keen_event('cloudpebble', 'cloudpebble_export_project', project=project)

        if not settings.AWS_ENABLED:
            outfile = '%s%s/%s.zip' % (settings.EXPORT_DIRECTORY, u, prefix)
            os.makedirs(os.path.dirname(outfile), 0755)
            shutil.copy(filename, outfile)
            os.chmod(outfile, 0644)
            return '%s%s/%s.zip' % (settings.EXPORT_ROOT, u, prefix)
        else:
            outfile = '%s/%s.zip' % (u, prefix)
            s3.upload_file('export', outfile, filename, public=True, content_type='application/zip')
            return '%s%s' % (settings.EXPORT_ROOT, outfile)




@task(acks_late=True)
def export_user_projects(user_id):
    user = User.objects.get(pk=user_id)
    projects = Project.objects.filter(owner=user)
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp:
        filename = temp.name
        with zipfile.ZipFile(filename, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for project in projects:
                add_project_to_archive(z, project, prefix='cloudpebble-export/')

        # Generate a URL
        u = uuid.uuid4().hex
        outfile = '%s%s/%s.zip' % (settings.EXPORT_DIRECTORY, u, 'cloudpebble-export')
        os.makedirs(os.path.dirname(outfile), 0755)
        shutil.copy(filename, outfile)
        os.chmod(outfile, 0644)

        send_keen_event('cloudpebble', 'cloudpebble_export_all_projects', user=user)
        return '%s%s/%s.zip' % (settings.EXPORT_ROOT, u, 'cloudpebble-export')


@task(acks_late=True)
def do_import_archive(project_id, archive, delete_project=False):
    project = Project.objects.get(pk=project_id)
    try:
        with tempfile.NamedTemporaryFile(suffix='.zip') as archive_file:
            archive_file.write(archive)
            archive_file.flush()
            with zipfile.ZipFile(str(archive_file.name), 'r') as z:
                contents = z.infolist()
                # Requirements:
                # - Find the folder containing the project. This may or may not be at the root level.
                # - Read in the source files, resources and resource map.
                # Observations:
                # - Legal projects must keep their source in a directory called 'src' containing at least one *.c file.
                # - Legal projects must have a resource map at resources/src/resource_map.json
                # Strategy:
                # - Find the shortest common prefix for 'resources/src/resource_map.json' and 'src/'.
                #   - This is taken to be the project directory.
                # - Import every file in 'src/' with the extension .c or .h as a source file
                # - Parse resource_map.json and import files it references
                RESOURCE_MAP = 'resources/src/resource_map.json'
                MANIFEST = 'appinfo.json'
                SRC_DIR = 'src/'
                if len(contents) > 200:
                    raise Exception("Too many files in zip file.")
                file_list = [x.filename for x in contents]

                version, base_dir = find_project_root(file_list)
                dir_end = len(base_dir)
                project.sdk_version = version

                # Now iterate over the things we found
                with transaction.commit_on_success():
                    for entry in contents:
                        filename = entry.filename
                        if filename[:dir_end] != base_dir:
                            continue
                        filename = filename[dir_end:]
                        if filename == '':
                            continue
                        if not os.path.normpath('/SENTINEL_DO_NOT_ACTUALLY_USE_THIS_NAME/%s' % filename).startswith('/SENTINEL_DO_NOT_ACTUALLY_USE_THIS_NAME/'):
                            raise SuspiciousOperation("Invalid zip file contents.")
                        if entry.file_size > 5242880:  # 5 MB
                            raise Exception("Excessively large compressed file.")

                        if (filename == RESOURCE_MAP and version == '1') or (filename == MANIFEST and version == '2'):
                            # We have a resource map! We can now try importing things from it.
                            with z.open(entry) as f:
                                m = json.loads(f.read())

                            if version == '1':
                                project.version_def_name = m['versionDefName']
                                media_map = m['media']
                            elif version == '2':
                                project.app_uuid = m['uuid']
                                project.app_short_name = m['shortName']
                                project.app_long_name = m['longName']
                                project.app_company_name = m['companyName']
                                project.app_version_code = m['versionCode']
                                project.app_version_label = m['versionLabel']
                                project.app_is_watchface = m.get('watchapp', {}).get('watchface', False)
                                project.app_capabilities = ','.join(m.get('capabilities', []))
                                project.app_keys = dict_to_pretty_json(m.get('appKeys', {}))
                                media_map = m['resources']['media']

                            resources = {}
                            for resource in media_map:
                                kind = resource['type']
                                def_name = resource['defName'] if version == '1' else resource['name']
                                file_name = resource['file']
                                regex = resource.get('characterRegex', None)
                                tracking = resource.get('trackingAdjust', None)
                                is_menu_icon = resource.get('menuIcon', False)
                                if file_name not in resources:
                                    resources[file_name] = ResourceFile.objects.create(project=project, file_name=os.path.basename(file_name), kind=kind, is_menu_icon=is_menu_icon)
                                    res_path = 'resources/src' if version == '1' else 'resources'
                                    resources[file_name].save_file(z.open('%s%s/%s' % (base_dir, res_path, file_name)))
                                ResourceIdentifier.objects.create(
                                    resource_file=resources[file_name],
                                    resource_id=def_name,
                                    character_regex=regex,
                                    tracking=tracking
                                )

                        elif filename.startswith(SRC_DIR):
                            if (not filename.startswith('.')) and (filename.endswith('.c') or filename.endswith('.h') or filename.endswith('.js')):
                                base_filename = os.path.basename(filename) if not filename.endswith('js/pebble-js-app.js') else 'js/pebble-js-app.js'
                                source = SourceFile.objects.create(project=project, file_name=base_filename)
                                with z.open(entry.filename) as f:
                                    source.save_file(f.read().decode('utf-8'))
                    project.save()
                    send_keen_event('cloudpebble', 'cloudpebble_zip_import_succeeded', project=project)

        # At this point we're supposed to have successfully created the project.
        return True
    except Exception as e:
        if delete_project:
            try:
                Project.objects.get(pk=project_id).delete()
            except:
                pass
        send_keen_event('cloudpebble', 'cloudpebble_zip_import_failed', user=project.owner, data={
            'data': {
                'reason': e.message
            }
        })
        raise


class NoProjectFoundError(Exception):
    pass
########NEW FILE########
__FILENAME__ = build
import os
import shutil
import subprocess
import tempfile
import traceback
import zipfile
import json
import resource

from celery import task

from django.conf import settings
from django.utils.timezone import now

import apptools.addr2lines
from ide.utils.sdk import generate_wscript_file, generate_jshint_file, generate_v2_manifest_dict, \
    generate_simplyjs_manifest_dict
from utils.keen_helper import send_keen_event

from ide.models.build import BuildResult
from ide.models.files import SourceFile, ResourceFile
from ide.utils.prepreprocessor import process_file as check_preprocessor_directives

__author__ = 'katharine'


def _set_resource_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20)) # 20 seconds of CPU time
    resource.setrlimit(resource.RLIMIT_NOFILE, (100, 100)) # 100 open files
    resource.setrlimit(resource.RLIMIT_RSS, (20 * 1024 * 1024, 20 * 1024 * 1024)) # 20 MB of memory
    resource.setrlimit(resource.RLIMIT_FSIZE, (5 * 1024 * 1024, 5 * 1024 * 1024)) # 5 MB output files.


@task(ignore_result=True, acks_late=True)
def run_compile(build_result):
    build_result = BuildResult.objects.get(pk=build_result)
    project = build_result.project
    source_files = SourceFile.objects.filter(project=project)
    resources = ResourceFile.objects.filter(project=project)

    if project.sdk_version == '1':
        build_result.state = BuildResult.STATE_FAILED
        build_result.finished = now()
        build_result.save()
        return

    # Assemble the project somewhere
    base_dir = tempfile.mkdtemp(dir=os.path.join(settings.CHROOT_ROOT, 'tmp') if settings.CHROOT_ROOT else None)

    try:
        if project.project_type == 'native':
            # Create symbolic links to the original files
            # Source code
            src_dir = os.path.join(base_dir, 'src')
            os.mkdir(src_dir)
            for f in source_files:
                abs_target = os.path.abspath(os.path.join(src_dir, f.file_name))
                if not abs_target.startswith(src_dir):
                    raise Exception("Suspicious filename: %s" % f.file_name)
                abs_target_dir = os.path.dirname(abs_target)
                if not os.path.exists(abs_target_dir):
                    os.makedirs(abs_target_dir)
                f.copy_to_path(abs_target)
                # Make sure we don't duplicate downloading effort; just open the one we created.
                with open(abs_target) as f:
                    check_preprocessor_directives(f.read())

            # Resources
            resource_root = 'resources'
            os.makedirs(os.path.join(base_dir, resource_root, 'images'))
            os.makedirs(os.path.join(base_dir, resource_root, 'fonts'))
            os.makedirs(os.path.join(base_dir, resource_root, 'data'))

            manifest_dict = generate_v2_manifest_dict(project, resources)
            open(os.path.join(base_dir, 'appinfo.json'), 'w').write(json.dumps(manifest_dict))

            for f in resources:
                target_dir = os.path.abspath(os.path.join(base_dir, resource_root, ResourceFile.DIR_MAP[f.kind]))
                abs_target = os.path.abspath(os.path.join(target_dir, f.file_name))
                if not abs_target.startswith(target_dir):
                    raise Exception("Suspicious filename: %s" % f.file_name)
                f.copy_to_path(abs_target)

            # Reconstitute the SDK
            open(os.path.join(base_dir, 'wscript'), 'w').write(generate_wscript_file(project))
            open(os.path.join(base_dir, 'pebble-jshintrc'), 'w').write(generate_jshint_file(project))
        elif project.project_type == 'simplyjs':
            os.rmdir(base_dir)  # This is not intuitive behaviour.
            shutil.copytree(settings.SIMPLYJS_ROOT, base_dir)
            manifest_dict = generate_simplyjs_manifest_dict(project)

            js = '\n\n'.join(x.get_contents() for x in source_files if x.file_name.endswith('.js'))
            escaped_js = json.dumps(js)
            build_result.save_simplyjs(js)

            open(os.path.join(base_dir, 'appinfo.json'), 'w').write(json.dumps(manifest_dict))
            open(os.path.join(base_dir, 'src', 'js', 'zzz_userscript.js'), 'w').write("""
            (function() {
                simply.mainScriptSource = %s;
            })();
            """ % escaped_js)

        # Build the thing
        cwd = os.getcwd()
        success = False
        output = 'Failed to get output'
        try:
            if settings.CHROOT_JAIL is not None:
                output = subprocess.check_output(
                    [settings.CHROOT_JAIL, project.sdk_version, base_dir[len(settings.CHROOT_ROOT):]],
                    stderr=subprocess.STDOUT)
            else:
                os.chdir(base_dir)
                output = subprocess.check_output([settings.PEBBLE_TOOL, "build"], stderr=subprocess.STDOUT, preexec_fn=_set_resource_limits)
        except subprocess.CalledProcessError as e:
            output = e.output
            print output
            success = False
        else:
            success = True
            temp_file = os.path.join(base_dir, 'build', '%s.pbw' % os.path.basename(base_dir))
            if not os.path.exists(temp_file):
                success = False
                print "Success was a lie."
        finally:
            os.chdir(cwd)

            if success:
                # Try reading file sizes out of it first.
                try:
                    s = os.stat(temp_file)
                    build_result.total_size = s.st_size
                    # Now peek into the zip to see the component parts
                    with zipfile.ZipFile(temp_file, 'r') as z:
                        build_result.binary_size = z.getinfo('pebble-app.bin').file_size
                        build_result.resource_size = z.getinfo('app_resources.pbpack').file_size
                except Exception as e:
                    print "Couldn't extract filesizes: %s" % e
                # Try pulling out debug information.
                elf_file = os.path.join(base_dir, 'build', 'pebble-app.elf')
                if os.path.exists(elf_file):
                    try:
                        debug_info = apptools.addr2lines.create_coalesced_group(elf_file)
                    except:
                        print traceback.format_exc()
                    else:
                        build_result.save_debug_info(debug_info)

                build_result.save_pbw(temp_file)
                send_keen_event(['cloudpebble', 'sdk'], 'app_build_succeeded', data={
                    'data': {
                        'cloudpebble_build_id': build_result.id
                    }
                }, project=project)
            else:
                send_keen_event(['cloudpebble', 'sdk'], 'app_build_failed', data={
                    'data': {
                        'cloudpebble_build_id': build_result.id
                    }
                }, project=project)
            build_result.save_build_log(output)
            build_result.state = BuildResult.STATE_SUCCEEDED if success else BuildResult.STATE_FAILED
            build_result.finished = now()
            build_result.save()
    except Exception as e:
        print "Build failed due to internal error: %s" % e
        traceback.print_exc()
        build_result.state = BuildResult.STATE_FAILED
        build_result.finished = now()
        try:
            build_result.save_build_log("Something broke:\n%s" % e)
        except:
            pass
        build_result.save()
    finally:
        shutil.rmtree(base_dir)

########NEW FILE########
__FILENAME__ = gist
import json

from celery import task
import github

from django.db import transaction
from ide.models.user import User
from ide.models.project import Project
from ide.models.files import SourceFile
from ide.utils.sdk import dict_to_pretty_json
from ide.utils import generate_half_uuid
from utils.keen_helper import send_keen_event

@task(acks_late=True)
def import_gist(user_id, gist_id):
    user = User.objects.get(pk=user_id)
    g = github.Github()

    try:
        gist = g.get_gist(gist_id)
    except github.UnknownObjectException:
        send_keen_event('cloudpebble', 'cloudpebble_gist_not_found', user=user, data={'data': {'gist_id': gist_id}})
        raise Exception("Couldn't find gist to import.")

    files = gist.files
    default_name = gist.description or 'Sample project'

    is_native = True

    if 'appinfo.json' in files:
        settings = json.loads(files['appinfo.json'].content)
        if len(files) == 2 and 'simply.js' in files:
            is_native = False
    else:
        settings = {}
        if len(files) == 1 and 'simply.js' in files:
            is_native = False

    project_settings = {
        'name': settings.get('longName', default_name),
        'owner': user,
        'sdk_version': 2,
        'app_uuid':  generate_half_uuid(),
        'app_short_name': settings.get('shortName', default_name),
        'app_long_name': settings.get('longName', default_name),
        'app_company_name': settings.get('companyName', user.username),
        'app_version_code': 1,
        'app_version_label': settings.get('versionLabel', '1.0'),
        'app_is_watchface': settings.get('watchapp', {}).get('watchface', False),
        'app_capabilities': ','.join(settings.get('capabilities', [])),
        'app_keys': dict_to_pretty_json(settings.get('appKeys', {})),
        'project_type': 'native' if is_native else 'simplyjs'
    }

    with transaction.commit_on_success():
        project = Project.objects.create(**project_settings)

        if is_native:
            for filename in gist.files:
                if filename.endswith('.c') or filename.endswith('.h') or filename == 'pebble-js-app.js':
                    # Because gists can't have subdirectories.
                    if filename == 'pebble-js-app.js':
                        cp_filename = 'js/pebble-js-app.js'
                    else:
                        cp_filename = filename
                    source_file = SourceFile.objects.create(project=project, file_name=cp_filename)
                    source_file.save_file(gist.files[filename].content)
        else:
            source_file = SourceFile.objects.create(project=project, file_name='app.js')
            source_file.save_file(gist.files['simply.js'].content)

    send_keen_event('cloudpebble', 'cloudpebble_gist_import', project=project, data={'data': {'gist_id': gist_id}})
    return project.id

########NEW FILE########
__FILENAME__ = git
import base64
import shutil
import tempfile
import urllib2
import json
from celery import task
from django.conf import settings
from django.utils.timezone import now
from github.GithubObject import NotSet
from github import Github, GithubException, InputGitTreeElement
from ide.git import git_auth_check, get_github
from ide.models.build import BuildResult
from ide.models.project import Project
from ide.tasks import do_import_archive, run_compile
from ide.utils.git import git_sha, git_blob
from ide.utils.project import find_project_root
from ide.utils.sdk import generate_resource_dict, generate_v2_manifest_dict, dict_to_pretty_json, generate_v2_manifest,\
    generate_wscript_file
from utils.keen_helper import send_keen_event

__author__ = 'katharine'


@task(acks_late=True)
def do_import_github(project_id, github_user, github_project, github_branch, delete_project=False):
    try:
        url = "https://github.com/%s/%s/archive/%s.zip" % (github_user, github_project, github_branch)
        if file_exists(url):
            u = urllib2.urlopen(url)
            return do_import_archive(project_id, u.read())
        else:
            raise Exception("The branch '%s' does not exist." % github_branch)
    except Exception as e:
        try:
            project = Project.objects.get(pk=project_id)
            user = project.owner
        except:
            project = None
            user = None
        if delete_project and project is not None:
            try:
                project.delete()
            except:
                pass
        send_keen_event('cloudpebble', 'cloudpebble_github_import_failed', user=user, data={
            'data': {
                'reason': e.message,
                'github_user': github_user,
                'github_project': github_project,
                'github_branch': github_branch
            }
        })
        raise


def file_exists(url):
    request = urllib2.Request(url)
    request.get_method = lambda: 'HEAD'
    try:
        urllib2.urlopen(request)
    except:
        return False
    else:
        return True


# SDK2 support has made this function a huge, unmaintainable mess.
@git_auth_check
def github_push(user, commit_message, repo_name, project):
    g = Github(user.github.token, client_id=settings.GITHUB_CLIENT_ID, client_secret=settings.GITHUB_CLIENT_SECRET)
    repo = g.get_repo(repo_name)
    try:
        branch = repo.get_branch(project.github_branch or repo.master_branch)
    except GithubException:
        raise Exception("Unable to get branch.")
    commit = repo.get_git_commit(branch.commit.sha)
    tree = repo.get_git_tree(commit.tree.sha, recursive=True)

    paths = [x.path for x in tree.tree]

    next_tree = {x.path: InputGitTreeElement(path=x.path, mode=x.mode, type=x.type, sha=x.sha) for x in tree.tree}

    try:
        remote_version, root = find_project_root(paths)
    except:
        remote_version, root = project.sdk_version, ''

    src_root = root + 'src/'
    project_sources = project.source_files.all()
    has_changed = False
    for source in project_sources:
        repo_path = src_root + source.file_name
        if repo_path not in next_tree:
            has_changed = True
            next_tree[repo_path] = InputGitTreeElement(path=repo_path, mode='100644', type='blob',
                                                       content=source.get_contents())
            print "New file: %s" % repo_path
        else:
            sha = next_tree[repo_path]._InputGitTreeElement__sha
            our_content = source.get_contents()
            expected_sha = git_sha(our_content)
            if expected_sha != sha:
                print "Updated file: %s" % repo_path
                next_tree[repo_path]._InputGitTreeElement__sha = NotSet
                next_tree[repo_path]._InputGitTreeElement__content = our_content
                has_changed = True

    expected_source_files = [src_root + x.file_name for x in project_sources]
    for path in next_tree.keys():
        if not path.startswith(src_root):
            continue
        if path not in expected_source_files:
            del next_tree[path]
            print "Deleted file: %s" % path
            has_changed = True

    # Now try handling resource files.

    resources = project.resources.all()

    old_resource_root = root + ("resources/src/" if remote_version == '1' else 'resources/')
    new_resource_root = root + ("resources/src/" if project.sdk_version == '1' else 'resources/')

    # Migrate all the resources so we can subsequently ignore the issue.
    if old_resource_root != new_resource_root:
        print "moving resources"
        new_next_tree = next_tree.copy()
        for path in next_tree:
            if path.startswith(old_resource_root) and not path.endswith('resource_map.json'):
                new_path = new_resource_root + path[len(old_resource_root):]
                print "moving %s to %s" % (path, new_path)
                next_tree[path]._InputGitTreeElement__path = new_path
                new_next_tree[new_path] = next_tree[path]
                del new_next_tree[path]
        next_tree = new_next_tree

    for res in resources:
        repo_path = new_resource_root + res.path
        if repo_path in next_tree:
            content = res.get_contents()
            if git_sha(content) != next_tree[repo_path]._InputGitTreeElement__sha:
                print "Changed resource: %s" % repo_path
                has_changed = True
                blob = repo.create_git_blob(base64.b64encode(content), 'base64')
                print "Created blob %s" % blob.sha
                next_tree[repo_path]._InputGitTreeElement__sha = blob.sha
        else:
            print "New resource: %s" % repo_path
            blob = repo.create_git_blob(base64.b64encode(res.get_contents()), 'base64')
            print "Created blob %s" % blob.sha
            next_tree[repo_path] = InputGitTreeElement(path=repo_path, mode='100644', type='blob', sha=blob.sha)

    # Both of these are used regardless of version
    remote_map_path = root + 'resources/src/resource_map.json'
    remote_manifest_path = root + 'appinfo.json'
    remote_wscript_path = root + 'wscript'

    if remote_version == '1':
        remote_map_sha = next_tree[remote_map_path]._InputGitTreeElement__sha if remote_map_path in next_tree else None
        if remote_map_sha is not None:
            their_res_dict = json.loads(git_blob(repo, remote_map_sha))
        else:
            their_res_dict = {'friendlyVersion': 'VERSION', 'versionDefName': '', 'media': []}
        their_manifest_dict = {}
    else:
        remote_manifest_sha = next_tree[remote_manifest_path]._InputGitTreeElement__sha if remote_map_path in next_tree else None
        if remote_manifest_sha is not None:
            their_manifest_dict = json.loads(git_blob(repo, remote_manifest_sha))
            their_res_dict = their_manifest_dict['resources']
        else:
            their_manifest_dict = {}
            their_res_dict = {'media': []}

    if project.sdk_version == '1':
        our_res_dict = generate_resource_dict(project, resources)
    else:
        our_manifest_dict = generate_v2_manifest_dict(project, resources)
        our_res_dict = our_manifest_dict['resources']

    if our_res_dict != their_res_dict:
        print "Resources mismatch."
        has_changed = True
        # Try removing things that we've deleted, if any
        to_remove = set(x['file'] for x in their_res_dict['media']) - set(x['file'] for x in our_res_dict['media'])
        for path in to_remove:
            repo_path = new_resource_root + path
            if repo_path in next_tree:
                print "Deleted resource: %s" % repo_path
                del next_tree[repo_path]

        # Update the stored resource map, if applicable.
        if project.sdk_version == '1':
            if remote_map_path in next_tree:
                next_tree[remote_map_path]._InputGitTreeElement__sha = NotSet
                next_tree[remote_map_path]._InputGitTreeElement__content = dict_to_pretty_json(our_res_dict)
            else:
                next_tree[remote_map_path] = InputGitTreeElement(path=remote_map_path, mode='100644', type='blob',
                                                                 content=dict_to_pretty_json(our_res_dict))
            # Delete the v2 manifest, if one exists
            if remote_manifest_path in next_tree:
                del next_tree[remote_manifest_path]
    # This one is separate because there's more than just the resource map changing.
    if project.sdk_version == '2' and their_manifest_dict != our_manifest_dict:
        if remote_manifest_path in next_tree:
            next_tree[remote_manifest_path]._InputGitTreeElement__sha = NotSet
            next_tree[remote_manifest_path]._InputGitTreeElement__content = generate_v2_manifest(project, resources)
        else:
            next_tree[remote_manifest_path] = InputGitTreeElement(path=remote_manifest_path, mode='100644', type='blob',
                                                                  content=generate_v2_manifest(project, resources))
        # Delete the v1 manifest, if one exists
        if remote_map_path in next_tree:
            del next_tree[remote_map_path]

    if project.sdk_version == '2':
        if remote_wscript_path not in next_tree:
            next_tree[remote_wscript_path] = InputGitTreeElement(path=remote_wscript_path, mode='100644', type='blob',
                                                                 content=generate_wscript_file(project, True))
            has_changed = True
    else:
        del next_tree[remote_wscript_path]

    # Commit the new tree.
    if has_changed:
        print "Has changed; committing"
        # GitHub seems to choke if we pass the raw directory nodes off to it,
        # so we delete those.
        for x in next_tree.keys():
            if next_tree[x]._InputGitTreeElement__mode == '040000':
                del next_tree[x]
                print "removing subtree node %s" % x

        print [x._InputGitTreeElement__mode for x in next_tree.values()]
        git_tree = repo.create_git_tree(next_tree.values())
        print "Created tree %s" % git_tree.sha
        git_commit = repo.create_git_commit(commit_message, git_tree, [commit])
        print "Created commit %s" % git_commit.sha
        git_ref = repo.get_git_ref('heads/%s' % (project.github_branch or repo.master_branch))
        git_ref.edit(git_commit.sha)
        print "Updated ref %s" % git_ref.ref
        project.github_last_commit = git_commit.sha
        project.github_last_sync = now()
        project.save()
        return True

    send_keen_event('cloudpebble', 'cloudpebble_github_push', user=user, data={
        'data': {
            'repo': project.github_repo
        }
    })

    return False


@git_auth_check
def github_pull(user, project):
    g = get_github(user)
    repo_name = project.github_repo
    if repo_name is None:
        raise Exception("No GitHub repo defined.")
    repo = g.get_repo(repo_name)
    # If somehow we don't have a branch set, this will use the "master_branch"
    branch_name = project.github_branch or repo.master_branch
    try:
        branch = repo.get_branch(branch_name)
    except GithubException:
        raise Exception("Unable to get the branch.")

    if project.github_last_commit == branch.commit.sha:
        # Nothing to do.
        return False

    commit = repo.get_git_commit(branch.commit.sha)
    tree = repo.get_git_tree(commit.tree.sha, recursive=True)

    paths = {x.path: x for x in tree.tree}

    version, root = find_project_root(paths)

    # First try finding the resource map so we don't fail out part-done later.
    # TODO: transaction support for file contents would be nice...
    # SDK2

    if version == '2':
        resource_root = root + 'resources/'
        manifest_path = root + 'appinfo.json'
        if manifest_path in paths:
            manifest_sha = paths[manifest_path].sha
            manifest = json.loads(git_blob(repo, manifest_sha))
            media = manifest.get('resources', {}).get('media', [])
        else:
            raise Exception("appinfo.json not found")
    else:
        # SDK1
        resource_root = root + 'resources/src/'
        remote_map_path = resource_root + 'resource_map.json'
        if remote_map_path in paths:
            remote_map_sha = paths[remote_map_path].sha
            remote_map = json.loads(git_blob(repo, remote_map_sha))
            media = remote_map['media']
        else:
            raise Exception("resource_map.json not found.")

    for resource in media:
        path = resource_root + resource['file']
        if path not in paths:
            raise Exception("Resource %s not found in repo." % path)

    # Now we grab the zip.
    zip_url = repo.get_archive_link('zipball', branch_name)
    u = urllib2.urlopen(zip_url)

    # And wipe the project!
    project.source_files.all().delete()
    project.resources.all().delete()

    # This must happen before do_import_archive or we'll stamp on its results.
    project.github_last_commit = branch.commit.sha
    project.github_last_sync = now()
    project.save()

    import_result = do_import_archive(project.id, u.read())

    send_keen_event('cloudpebble', 'cloudpebble_github_pull', user=user, data={
        'data': {
            'repo': project.github_repo
        }
    })

    return import_result


@task
def do_github_push(project_id, commit_message):
    project = Project.objects.select_related('owner__github').get(pk=project_id)
    return github_push(project.owner, commit_message, project.github_repo, project)


@task
def do_github_pull(project_id):
    project = Project.objects.select_related('owner__github').get(pk=project_id)
    return github_pull(project.owner, project)


@task
def hooked_commit(project_id, target_commit):
    project = Project.objects.select_related('owner__github').get(pk=project_id)
    did_something = False
    print "Comparing %s versus %s" % (project.github_last_commit, target_commit)
    if project.github_last_commit != target_commit:
        github_pull(project.owner, project)
        did_something = True

    if project.github_hook_build:
        build = BuildResult.objects.create(project=project)
        run_compile(build.id)
        did_something = True

    return did_something
########NEW FILE########
__FILENAME__ = keen_task
from celery import task
from django.conf import settings
from keen import KeenClient

__author__ = 'katharine'


@task(ignore_result=True)
def keen_add_events(events):
    KeenClient(project_id=settings.KEEN_PROJECT_ID, write_key=settings.KEEN_WRITE_KEY).add_events(events)
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
__FILENAME__ = urls
from django.conf.urls import patterns, url

from ide.api import proxy_keen, check_task, get_shortlink, heartbeat
from ide.api.git import github_push, github_pull, set_project_repo, create_project_repo
from ide.api.phone import ping_phone, check_phone, list_phones, update_phone
from ide.api.project import project_info, compile_project, last_build, build_history, build_log, create_project, \
    save_project_settings, delete_project, begin_export, import_zip, import_github, do_import_gist
from ide.api.resource import create_resource, resource_info, delete_resource, update_resource, show_resource
from ide.api.source import create_source_file, load_source_file, source_file_is_safe, save_source_file, \
    delete_source_file
from ide.api.user import transition_accept, transition_export, transition_delete, whats_new
from ide.views.index import index
from ide.views.project import view_project, github_hook, build_status, import_gist
from ide.views.settings import settings_page, start_github_auth, remove_github_auth, complete_github_auth

urlpatterns = patterns(
    '',
    url(r'^$', index, name='index'),
    url(r'^project/create', create_project, name='create_project'),
    url(r'^project/(?P<project_id>\d+)$', view_project, name='project'),
    url(r'^project/(?P<project_id>\d+)/info', project_info, name='project_info'),
    url(r'^project/(?P<project_id>\d+)/save_settings', save_project_settings, name='save_project_settings'),
    url(r'^project/(?P<project_id>\d+)/delete', delete_project, name='delete_project'),
    url(r'^project/(?P<project_id>\d+)/create_source_file', create_source_file, name='create_source_file'),
    url(r'^project/(?P<project_id>\d+)/source/(?P<file_id>\d+)/load', load_source_file, name='load_source_file'),
    url(r'^project/(?P<project_id>\d+)/source/(?P<file_id>\d+)/save', save_source_file, name='save_source_file'),
    url(r'^project/(?P<project_id>\d+)/source/(?P<file_id>\d+)/is_safe', source_file_is_safe, name='source_file_is_safe'),
    url(r'^project/(?P<project_id>\d+)/source/(?P<file_id>\d+)/delete', delete_source_file, name='delete_source_file'),
    url(r'^project/(?P<project_id>\d+)/create_resource', create_resource, name='create_resource'),
    url(r'^project/(?P<project_id>\d+)/resource/(?P<resource_id>\d+)/info', resource_info, name='resource_info'),
    url(r'^project/(?P<project_id>\d+)/resource/(?P<resource_id>\d+)/delete', delete_resource, name='delete_resource'),
    url(r'^project/(?P<project_id>\d+)/resource/(?P<resource_id>\d+)/update', update_resource, name='update_resource'),
    url(r'^project/(?P<project_id>\d+)/resource/(?P<resource_id>\d+)/get', show_resource, name='show_resource'),
    url(r'^project/(?P<project_id>\d+)/build/run', compile_project, name='compile_project'),
    url(r'^project/(?P<project_id>\d+)/build/last', last_build, name='get_last_build'),
    url(r'^project/(?P<project_id>\d+)/build/history', build_history, name='get_build_history'),
    url(r'^project/(?P<project_id>\d+)/analytics', proxy_keen, name='proxy_analytics'),
    url(r'^project/(?P<project_id>\d+)/build/(?P<build_id>\d+)/log', build_log, name='get_build_log'),
    url(r'^project/(?P<project_id>\d+)/export', begin_export, name='begin_export'),
    url(r'^project/(?P<project_id>\d+)/github/repo$', set_project_repo, name='set_project_repo'),
    url(r'^project/(?P<project_id>\d+)/github/repo/create$', create_project_repo, name='create_project_repo'),
    url(r'^project/(?P<project_id>\d+)/github/commit$', github_push, name='github_push'),
    url(r'^project/(?P<project_id>\d+)/github/pull$', github_pull, name='github_pull'),
    url(r'^project/(?P<project_id>\d+)/github/push_hook$', github_hook, name='github_hook'),
    url(r'^project/(?P<project_id>\d+)/status\.png$', build_status, name='build_status'),
    url(r'^task/(?P<task_id>[0-9a-f-]{32,36})', check_task, name='check_task'),
    url(r'^shortlink$', get_shortlink, name='get_shortlink'),
    url(r'^settings$', settings_page, name='settings'),
    url(r'^settings/github/start$', start_github_auth, name='start_github_auth'),
    url(r'^settings/github/callback$', complete_github_auth, name='complete_github_auth'),
    url(r'^settings/github/unlink$', remove_github_auth, name='remove_github_auth'),
    url(r'^import/zip', import_zip, name='import_zip'),
    url(r'^import/github', import_github, name='import_github'),
    url(r'^import/gist', do_import_gist, name='import_gist'),
    url(r'^transition/accept', transition_accept, name='transition_accept'),
    url(r'^transition/export', transition_export, name='transition_export'),
    url(r'^transition/delete', transition_delete, name='transition_delete'),
    url(r'^ping_phone$', ping_phone),
    url(r'^check_phone/(?P<request_id>[0-9a-f-]+)$', check_phone),
    url(r'^update_phone$', update_phone),
    url(r'^list_phones$', list_phones),
    url(r'^whats_new', whats_new, name='whats_new'),
    url(r'^gist/(?P<gist_id>[0-9a-f]+)$', import_gist),
    url(r'^heartbeat$', heartbeat)
)

########NEW FILE########
__FILENAME__ = git
import base64
import hashlib

__author__ = 'katharine'


def git_sha(content):
    return hashlib.sha1('blob %d\x00%s' % (len(content), content)).hexdigest()


def git_blob(repo, sha):
    return base64.b64decode(repo.get_git_blob(sha).content)
########NEW FILE########
__FILENAME__ = prepreprocessor
import re
import uuid
import os.path

def fix_newlines(source):
    return re.sub(r'\r\n|\r|\n', '\n', source)


def merge_newlines(source):
    return source.replace('\\\n', '')


def remove_comments(source):
    no_mutiline = re.sub(r'/\*.*?\*/', ' ', source, flags=re.DOTALL|re.MULTILINE)
    no_single_line = re.sub(r'//.*$', ' ', no_mutiline, flags=re.MULTILINE)
    return no_single_line


def extract_includes(source):
    return re.findall(r'^#\s*include\s*[<"](.+)[">]\s*$', source, flags=re.MULTILINE)


def check_include_legal(include):
    prefix = '/%s/' % uuid.uuid4()
    path = os.path.normpath(os.path.join(prefix, include))
    if not path.startswith(prefix):
        raise Exception("Illegal include '%s' -> '%s'" % (include, path))
    return True


def process_file(source):
    processed_text = remove_comments(merge_newlines(fix_newlines(source)))
    includes = extract_includes(processed_text)

    for include in includes:
        check_include_legal(include)



########NEW FILE########
__FILENAME__ = project
__author__ = 'katharine'


def find_project_root(contents):
    RESOURCE_MAP = 'resources/src/resource_map.json'
    MANIFEST = 'appinfo.json'
    SRC_DIR = 'src/'
    version = None
    for base_dir in contents:
        version = None
        print base_dir
        # Try finding v2
        try:
            dir_end = base_dir.index(MANIFEST)
            print dir_end
        except ValueError:
            # Try finding v1
            try:
                dir_end = base_dir.index(RESOURCE_MAP)
            except ValueError:
                continue
            else:
                if dir_end + len(RESOURCE_MAP) != len(base_dir):
                    continue
                version = '1'
        else:
            if dir_end + len(MANIFEST) != len(base_dir):
                print 'failed'
                continue
            version = '2'

        base_dir = base_dir[:dir_end]
        print base_dir
        for source_dir in contents:
            if source_dir[:dir_end] != base_dir:
                continue
            if source_dir[-2:] != '.c':
                continue
            if source_dir[dir_end:dir_end+len(SRC_DIR)] != SRC_DIR:
                continue
            break
        else:
            continue
        break
    else:
        raise Exception("No project root found.")
    return version, base_dir

########NEW FILE########
__FILENAME__ = sdk
import json

__author__ = 'katharine'


def generate_wscript_file(project, for_export=False):
    jshint = project.app_jshint
    wscript = """
#
# This file is the default set of rules to compile a Pebble project.
#
# Feel free to customize this to your needs.
#

try:
    from sh import CommandNotFound, jshint, cat, ErrorReturnCode_2
    hint = jshint
except (ImportError, CommandNotFound):
    hint = None

top = '.'
out = 'build'

def options(ctx):
    ctx.load('pebble_sdk')

def configure(ctx):
    ctx.load('pebble_sdk')
    global hint
    if hint is not None:
        hint = hint.bake(['--config', 'pebble-jshintrc'])

def build(ctx):
    if {{jshint}} and hint is not None:
        try:
            hint([node.abspath() for node in ctx.path.ant_glob("src/**/*.js")], _tty_out=False) # no tty because there are none in the cloudpebble sandbox.
        except ErrorReturnCode_2 as e:
            ctx.fatal("\\nJavaScript linting failed (you can disable this in Project Settings):\\n" + e.stdout)

    # Concatenate all our JS files (but not recursively), and only if any JS exists in the first place.
    ctx.path.make_node('src/js/').mkdir()
    js_paths = [node.abspath() for node in ctx.path.ant_glob("src/*.js")]
    if js_paths:
        ctx.exec_command(['cat'] + js_paths, stdout=open('src/js/pebble-js-app.js', 'a'))

    ctx.load('pebble_sdk')

    ctx.pbl_program(source=ctx.path.ant_glob('src/**/*.c'),
                    target='pebble-app.elf')

    ctx.pbl_bundle(elf='pebble-app.elf',
                   js=ctx.path.ant_glob('src/js/**/*.js'))

"""
    return wscript.replace('{{jshint}}', 'True' if jshint and not for_export else 'False')


def generate_jshint_file(project):
    return """
/*
 * Example jshint configuration file for Pebble development.
 *
 * Check out the full documentation at http://www.jshint.com/docs/options/
 */
{
  // Declares the existence of the globals available in PebbleKit JS.
  "globals": {
    "Pebble": true,
    "console": true,
    "XMLHttpRequest": true,
    "navigator": true, // For navigator.geolocation
    "localStorage": true,
    "setTimeout": true
  },

  // Do not mess with standard JavaScript objects (Array, Date, etc)
  "freeze": true,

  // Do not use eval! Keep this warning turned on (ie: false)
  "evil": false,

  /*
   * The options below are more style/developer dependent.
   * Customize to your liking.
   */

  // All variables should be in camelcase - too specific for CloudPebble builds to fail
  // "camelcase": true,

  // Do not allow blocks without { } - too specific for CloudPebble builds to fail.
  // "curly": true,

  // Prohibits the use of immediate function invocations without wrapping them in parentheses
  "immed": true,

  // Don't enforce indentation, because it's not worth failing builds over
  // (especially given our somewhat lacklustre support for it)
  "indent": false,

  // Do not use a variable before it's defined
  "latedef": "nofunc",

  // Spot undefined variables
  "undef": "true",

  // Spot unused variables
  "unused": "true"
}
"""


def generate_v2_manifest(project, resources):
    return dict_to_pretty_json(generate_v2_manifest_dict(project, resources))


def generate_v2_manifest_dict(project, resources):
    manifest = {
        'uuid': str(project.app_uuid),
        'shortName': project.app_short_name,
        'longName': project.app_long_name,
        'companyName': project.app_company_name,
        'versionCode': project.app_version_code,
        'versionLabel': project.app_version_label,
        'watchapp': {
            'watchface': project.app_is_watchface
        },
        'appKeys': json.loads(project.app_keys),
        'resources': generate_resource_dict(project, resources),
        'capabilities': project.app_capabilities.split(',')
    }
    return manifest


def generate_resource_map(project, resources):
    return dict_to_pretty_json(generate_resource_dict(project, resources))


def dict_to_pretty_json(d):
    return json.dumps(d, indent=4, separators=(',', ': ')) + "\n"


def generate_resource_dict(project, resources):
    resource_map = {'media': []}
    if project.sdk_version == '1':
        resource_map['friendlyVersion'] = 'VERSION'
        resource_map['versionDefName'] = project.version_def_name

    if project.sdk_version == '1' and len(resources) == 0:
        print "No resources; adding dummy."
        resource_map['media'].append({"type": "raw", "defName": "DUMMY", "file": "resource_map.json"})
    else:
        for resource in resources:
            for resource_id in resource.get_identifiers():
                d = {
                    'type': resource.kind,
                    'file': resource.path
                }
                if project.sdk_version == '1':
                    d['defName'] = resource_id.resource_id
                else:
                    d['name'] = resource_id.resource_id
                if resource_id.character_regex:
                    d['characterRegex'] = resource_id.character_regex
                if resource_id.tracking:
                    d['trackingAdjust'] = resource_id.tracking
                if resource.is_menu_icon:
                    d['menuIcon'] = True
                resource_map['media'].append(d)
    return resource_map


def generate_simplyjs_manifest_dict(project):
    manifest = {
        "uuid": project.app_uuid,
        "shortName": project.app_short_name,
        "longName": project.app_long_name,
        "companyName": project.app_company_name,
        "versionCode": project.app_version_code,
        "versionLabel": project.app_version_label,
        "capabilities": project.app_capabilities.split(','),
        "watchapp": {
            "watchface": project.app_is_watchface
        },
        "appKeys": {},
        "resources": {
            "media": [
                {
                    "menuIcon": True,
                    "type": "png",
                    "name": "IMAGE_MENU_ICON",
                    "file": "images/menu_icon.png"
                }, {
                    "type": "png",
                    "name": "IMAGE_LOGO_SPLASH",
                    "file": "images/logo_splash.png"
                }, {
                    "type": "font",
                    "name": "MONO_FONT_14",
                    "file": "fonts/UbuntuMono-Regular.ttf"
                }
            ]
        }
    }
    return manifest

########NEW FILE########
__FILENAME__ = whatsnew
NEW_THINGS = [
    ["You will now be alerted to new features on your first visit to the site after they're added. For instance, this one."],
    ["CloudPebble now lets you create appications using pure JavaScript! <a href='https://developer.getpebble.com/blog/2014/03/14/CloudPebble-now-supports-Simplyjs/' target='_blank'>Check out our blog post!</a>"],
    ["A longstanding issue preventing iOS users from installing apps larger than 64k has been resolved in iOS app 2.1.1."],
    ["iOS users can now more easily install apps on their phones by selecting it from a list!",
     "This requires iOS app 2.1.1. If you have 2.1.1 and your phone doesn't appear in the list, try killing and restarting the Pebble app.",
     "<a href='https://developer.getpebble.com/blog/2014/04/04/Easier-app-deployment-from-Cloudpebble/' target='_blank'>See the blog post!</a>"],
    ["You can now view the API documentation right in CloudPebble!",
     "Alt-click on any API function in your code for a pop-up explaining it. You can dismiss it by clicking or hitting esc.",
     "You can also view the pop-up for the name your editor cursor is in by pressing cmd-ctrl-shift-/ (Mac) or ctrl-alt-shift-/ (Windows)." +
     " (On some keyboard layouts, that is cmd-ctrl-? or ctrl-alt-?)",
     "Short summaries now also appear at the bottom of the autocomplete popup."],
    ["CloudPebble is now running Pebble SDK 2.1. See the <a href='https://developer.getpebble.com/2/changelog-2.1.html'>full release notes</a>.",
     "<strong>Warning:</strong> Apps that incorrectly free the same memory twice will now crash immediately instead of carrying on but potentially silently corrupting memory.",
     "Apps built on CloudPebble now require you to <a href='https://developer.getpebble.com/2/getting-started/'>update to Pebble OS 2.1</a> to run your apps."],
]


def get_new_things(user):
    user_settings = user.settings
    what = user_settings.whats_new

    if what < len(NEW_THINGS):
        user_settings.whats_new = len(NEW_THINGS)
        user_settings.save()

        return NEW_THINGS[what:][::-1]
    else:
        return []


def count_things():
    return len(NEW_THINGS)

########NEW FILE########
__FILENAME__ = index
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe
from ide.models.project import Project, TemplateProject
from utils.keen_helper import send_keen_event

__author__ = 'katharine'


@require_safe
@login_required
@ensure_csrf_cookie
def index(request):
    user = request.user
    my_projects = Project.objects.filter(owner=user).order_by('-last_modified')
    if not user.settings.accepted_terms:
        # Screw it.
        # user_settings = user.settings
        # user_settings.accepted_terms = True
        # user_settings.save()

        return render(request, 'ide/new-owner.html', {
            'my_projects': my_projects
        })
    elif settings.SOCIAL_AUTH_PEBBLE_REQUIRED and user.social_auth.filter(provider='pebble').count() == 0:
        return render(request, 'registration/merge_account.html')
    else:
        send_keen_event('cloudpebble', 'cloudpebble_project_list', request=request)
        return render(request, 'ide/index.html', {
            'my_projects': my_projects,
            'sdk_templates': TemplateProject.objects.filter(template_kind=TemplateProject.KIND_TEMPLATE),
            'example_templates': TemplateProject.objects.filter(template_kind=TemplateProject.KIND_EXAMPLE),
            'demo_templates': TemplateProject.objects.filter(template_kind=TemplateProject.KIND_SDK_DEMO),
            'default_template_id': settings.DEFAULT_TEMPLATE
        })

########NEW FILE########
__FILENAME__ = project
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_safe, require_POST
from ide.models.build import BuildResult
from ide.models.project import Project
from ide.tasks.git import hooked_commit
from ide.utils import generate_half_uuid
from utils.keen_helper import send_keen_event

__author__ = 'katharine'


@require_safe
@login_required
@ensure_csrf_cookie
def view_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    if project.app_uuid is None:
        project.app_uuid = generate_half_uuid()
    if project.app_company_name is None:
        project.app_company_name = request.user.username
    if project.app_short_name is None:
        project.app_short_name = project.name
    if project.app_long_name is None:
        project.app_long_name = project.app_short_name
    if project.app_version_code is None:
        project.app_version_code = 1
    if project.app_version_label is None:
        project.app_version_label = '1.0'
    send_keen_event('cloudpebble', 'cloudpebble_open_project', request=request, project=project)
    app_keys = json.loads(project.app_keys).iteritems()
    return render(request, 'ide/project.html', {'project': project, 'app_keys': app_keys})


@csrf_exempt
@require_POST
def github_hook(request, project_id):
    hook_uuid = request.GET['key']
    project = get_object_or_404(Project, pk=project_id, github_hook_uuid=hook_uuid)

    push_info = json.loads(request.POST['payload'])
    if push_info['ref'] == 'refs/heads/%s' % (project.github_branch or push_info['repository']['master_branch']):
        hooked_commit.delay(project_id, push_info['after'])

    return HttpResponse('ok')


@require_safe
def build_status(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    try:
        last_build = BuildResult.objects.order_by('-id').filter(~Q(state=BuildResult.STATE_WAITING), project=project)[0]
    except IndexError:
        return HttpResponseRedirect(settings.STATIC_URL + '/ide/img/status/error.png')
    if last_build.state == BuildResult.STATE_SUCCEEDED:
        return HttpResponseRedirect(settings.STATIC_URL + '/ide/img/status/passing.png')
    else:
        return HttpResponseRedirect(settings.STATIC_URL + '/ide/img/status/failing.png')


@require_safe
@login_required
@ensure_csrf_cookie
def import_gist(request, gist_id):
    send_keen_event('cloudpebble', 'cloudpebble_gist_landing', request=request, data={'data': {'gist_id': gist_id}})
    return render(request, 'ide/gist-import.html', {
        'gist_id': gist_id,
        'blurb': request.GET.get('blurb', None)
    })

########NEW FILE########
__FILENAME__ = settings
import base64
import urllib
import urllib2
import uuid
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_safe, require_POST
from ide.forms import SettingsForm
from ide.models.user import UserGithub
from utils.keen_helper import send_keen_event

__author__ = 'katharine'


@login_required
def settings_page(request):
    user_settings = request.user.settings
    try:
        github = request.user.github
    except UserGithub.DoesNotExist:
        github = None

    if request.method == 'POST':
        form = SettingsForm(request.POST, instance=user_settings)
        if form.is_valid():
            form.save()
            send_keen_event('cloudpebble', 'cloudpebble_change_user_settings', request=request)
            return render(request, 'ide/settings.html', {'form': form, 'saved': True, 'github': github})

    else:
        form = SettingsForm(instance=user_settings)

    send_keen_event('cloudpebble', 'cloudpebble_view_user_settings', request=request)

    return render(request, 'ide/settings.html', {'form': form, 'saved': False, 'github': github})


@login_required
@require_safe
def start_github_auth(request):
    nonce = uuid.uuid4().hex
    try:
        user_github = request.user.github
    except UserGithub.DoesNotExist:
        user_github = UserGithub.objects.create(user=request.user)
    user_github.nonce = nonce
    user_github.save()
    send_keen_event('cloudpebble', 'cloudpebble_github_started', request=request)
    return HttpResponseRedirect('https://github.com/login/oauth/authorize?client_id=%s&scope=repo&state=%s' %
                                (settings.GITHUB_CLIENT_ID, nonce))


@login_required
@require_POST
def remove_github_auth(request):
    try:
        user_github = request.user.github
        user_github.delete()
    except UserGithub.DoesNotExist:
        pass
    send_keen_event('cloudpebble', 'cloudpebble_github_revoked', request=request)
    return HttpResponseRedirect('/ide/settings')


@login_required
@require_safe
def complete_github_auth(request):
    if 'error' in request.GET:
        return HttpResponseRedirect('/ide/settings')
    nonce = request.GET['state']
    code = request.GET['code']
    user_github = request.user.github
    if user_github.nonce is None or nonce != user_github.nonce:
        return HttpResponseBadRequest('nonce mismatch.')
    # This probably shouldn't be in a view. Oh well.
    params = urllib.urlencode({
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'code': code
    })
    r = urllib2.Request('https://github.com/login/oauth/access_token', params, headers={'Accept': 'application/json'})
    result = json.loads(urllib2.urlopen(r).read())
    user_github = request.user.github
    user_github.token = result['access_token']
    user_github.nonce = None
    # Try and figure out their username.
    auth_string = base64.encodestring('%s:%s' %
                                      (settings.GITHUB_CLIENT_ID, settings.GITHUB_CLIENT_SECRET)).replace('\n', '')

    r = urllib2.Request('https://api.github.com/applications/%s/tokens/%s' %
                        (settings.GITHUB_CLIENT_ID, user_github.token))

    r.add_header("Authorization", "Basic %s" % auth_string)
    result = json.loads(urllib2.urlopen(r).read())
    user_github.username = result['user']['login']
    user_github.avatar = result['user']['avatar_url']

    user_github.save()

    send_keen_event('cloudpebble', 'cloudpebble_github_linked', request=request, data={
        'data': {'username': user_github.username}
    })

    return HttpResponseRedirect('/ide/settings')
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cloudpebble.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

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
__FILENAME__ = urls
from django.conf.urls import patterns, url

from qr import views

urlpatterns = patterns(
    '',
    url('$^', views.render, name='render')
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

from StringIO import StringIO
import qrcode


def render(request):
    value = request.GET.get('v', '')
    size = int(request.GET.get('s', 4))
    border = int(request.GET.get('b', 2))
    qr = qrcode.QRCode(box_size=size, border=border, error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(value)
    img = qr.make_image()
    s = StringIO()
    img.save(s, kind='png')
    s.seek(0)
    return HttpResponse(s, content_type='image/png')

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

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
__FILENAME__ = urls
from django.conf.urls import patterns, url

from root import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render, redirect
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def index(request):
    if request.user.is_authenticated():
        return redirect("/ide/")
    else:
        return render(request, 'root/index.html', {'sso_root': settings.SOCIAL_AUTH_PEBBLE_ROOT_URL})

########NEW FILE########
__FILENAME__ = keen_helper
from ide.tasks.keen_task import keen_add_events

__author__ = 'katharine'

from django.conf import settings

import keen
import keen.scoped_keys


# WARNING: Keen does not appear to respect the filters on scoped write keys.
# Don't use this function.
def generate_scoped_key(user):
    uid = user.social_auth.get(provider='pebble').uid
    filters = [{
        'property_name': 'identity.user',
        'operator': 'eq',
        'property_value': uid
    }]

    return keen.scoped_keys.encrypt(settings.KEEN_API_KEY, {'filters': filters, 'allowed_operations': ['write']})


def send_keen_event(collections, event, data=None, request=None, project=None, user=None):
    if not settings.KEEN_ENABLED:
        return

    data = data.copy() if data is not None else {}
    data['event'] = event
    data['cloudpebble'] = {}

    if user is None:
        if request is not None and request.user.is_authenticated():
            user = request.user
        elif project is not None:
            user = project.owner

    if user is not None:
        data['identity'] = {'cloudpebble_uid': user.id}
        try:
            data['identity']['user'] = user.social_auth.get(provider='pebble').uid
        except:
            pass

    if project is not None:
        data['cloudpebble']['project'] = {
            'id': project.id,
            'name': project.name,
            'uuid': project.app_uuid,
            'app_name': project.app_long_name,
            'sdk': project.sdk_version,
            'is_watchface': project.app_is_watchface,
            'jshint': project.app_jshint,
            'type': project.project_type,
        }

    data['platform'] = 'cloudpebble'
    if request is not None:
        data['web'] = {
            'referrer': request.META.get('HTTP_REFERER'),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'path': request.path,
            'ip': request.META['REMOTE_ADDR'],
            'url': request.build_absolute_uri(),
        }

    keen_request = {"events": [data]}

    if not hasattr(collections, '__iter__'):
        collections = [collections]

    for collection in collections:
        keen_request[collection] = [data]

    # keen.add_events(keen_request) # probably don't want to block while this processes...
    keen_add_events.delay(keen_request)

########NEW FILE########
__FILENAME__ = redis_helper
__author__ = 'katharine'

import redis
from django.conf import settings

redis_client = redis.from_url(settings.REDIS_URL)

########NEW FILE########
__FILENAME__ = s3
import boto
from boto.s3.key import Key
from django.conf import settings
import urllib

if settings.AWS_ENABLED:
    _s3 = boto.connect_s3(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)

    _buckets = {
        'source': _s3.get_bucket(settings.AWS_S3_SOURCE_BUCKET),
        'export': _s3.get_bucket(settings.AWS_S3_EXPORT_BUCKET),
        'builds': _s3.get_bucket(settings.AWS_S3_BUILDS_BUCKET),
    }
else:
    _s3 = None
    _buckets = None


def _requires_aws(fn):
    if settings.AWS_ENABLED:
        return fn
    else:
        def complain(*args, **kwargs):
            raise Exception("AWS_ENABLED must be True to call %s" % fn.__name__)
        return complain


@_requires_aws
def read_file(bucket_name, path):
    bucket = _buckets[bucket_name]
    key = bucket.get_key(path)
    return key.get_contents_as_string()


@_requires_aws
def read_file_to_filesystem(bucket_name, path, destination):
    bucket = _buckets[bucket_name]
    key = bucket.get_key(path)
    key.get_contents_to_filename(destination)


@_requires_aws
def save_file(bucket_name, path, value, public=False, content_type='application/octet-stream'):
    bucket = _buckets[bucket_name]
    key = Key(bucket)
    key.key = path

    if public:
        policy = 'public-read'
    else:
        policy = 'private'

    key.set_contents_from_string(value, policy=policy, headers={'Content-Type': content_type})


@_requires_aws
def upload_file(bucket_name, dest_path, src_path, public=False, content_type='application/octet-stream', download_filename=None):
    bucket = _buckets[bucket_name]
    key = Key(bucket)
    key.key = dest_path

    if public:
        policy = 'public-read'
    else:
        policy = 'private'

    headers = {
        'Content-Type': content_type
    }

    if download_filename is not None:
        headers['Content-Disposition'] = 'attachment;filename="%s"' % download_filename.replace(' ','_')

    key.set_contents_from_filename(src_path, policy=policy, headers=headers)


@_requires_aws
def get_signed_url(bucket_name, path, headers=None):
    bucket = _buckets[bucket_name]
    key = bucket.get_key(path)
    url = key.generate_url(3600, response_headers=headers)
    # hack to avoid invalid SSL certs.
    if '.cloudpebble.' in url:
        url = url.replace('.s3.amazonaws.com', '')
    return url

########NEW FILE########
