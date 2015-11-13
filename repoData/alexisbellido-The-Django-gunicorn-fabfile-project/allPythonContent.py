__FILENAME__ = settings
# Django settings for django_gunicorn_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
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
SECRET_KEY = 's%-6o6w(#ri@dw*apwb2#2uxjl@sttnr7cs0kl&amp;ugi5%_y-0!*'

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

ROOT_URLCONF = 'django_gunicorn_project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'django_gunicorn_project.wsgi.application'

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
    # 'django.contrib.admin',
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

# Use local_settings.py to override settings.
# This file should be outside of control version. 
# Copy local_settings_template.py as a starting point.
try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'django_gunicorn_project.views.home', name='home'),
    # url(r'^django_gunicorn_project/', include('django_gunicorn_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for django_gunicorn_project project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_gunicorn_project.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = fabconfig
#### START OF FABRIC CONFIGURATION ####

# Use local_settings.py to override settings.
# This file should be outside of control version. 
# Copy local_settings_template.py as a starting point.
try:
    from local_settings import *
except ImportError:
    pass

# DO NOT USE TRAILING SLASH AND USE UNDERSCORES IN DIRECTORIES TO MIMIC django-admin.py starproject.
PROJECT_USER = 'user'

PROJECT_NAME = 'django_gunicorn_project' # Used for upstart script and virtualenv
PROJECT_DESCRIPTIVE_NAME = 'The Django gunicorn project' # Used as description in upstart script

# with the new Django 1.4 project layout there's an inner project directory at PROJECT_DIR/PROJECT_INNER_DIR
PROJECT_DIR = '/home/user/django_gunicorn_project'
PROJECT_INNER_DIR = 'django_gunicorn_project'
PROJECT_LOGDIR = '/home/alexis/logs/django_gunicorn_project'
PROJECT_SCRIPT_NAME = 'run-' + PROJECT_NAME

PROJECT_DOMAIN = 'example.com'
PROJECT_DOMAIN_STAGING = 'staging.example.com'
PROJECT_DOMAIN_DEVELOPMENT = 'development.example.com'

# This will be in local, outside of version control, and should use DEBUG conditionals for switching between development/staging and production settings,
# see local_settings_template.py (which is not used by the project) for example.
PROJECT_SETTINGS_PATH = '/home/user/djsettings/django_gunicorn_project_local_settings.py'

PROJECT_GUNICORN_LOGLEVEL = 'info'
PROJECT_GUNICORN_NUM_WORKERS = 3
PROJECT_GUNICORN_BIND_IP = '127.0.0.1'
PROJECT_GUNICORN_BIND_PORT = '8000'

PROJECT_NGINX_IP = '192.168.0.185'
PROJECT_NGINX_PORT = '80'

PROJECT_NGINX_IP_STAGING = '192.168.0.185'
PROJECT_NGINX_PORT_STAGING = '81'

PROJECT_NGINX_IP_DEVELOPMENT = '192.168.0.185'
PROJECT_NGINX_PORT_DEVELOPMENT = '82'

# Some of these values are shared by development when not specified here, update build_projects_var function if needed
PROJECT_GUNICORN_LOGLEVEL_STAGING = 'debug'
PROJECT_GUNICORN_NUM_WORKERS_STAGING = 3
PROJECT_GUNICORN_BIND_IP_STAGING = '127.0.0.1'
PROJECT_GUNICORN_BIND_PORT_STAGING = '8001'

PROJECT_GUNICORN_BIND_PORT_DEVELOPMENT = '8002'

PROJECT_LOG_GUNICORN = 'gunicorn.log'
PROJECT_LOG_NGINX_ACCESS = 'nginx-access.log'
PROJECT_LOG_NGINX_ERROR = 'nginx-error.log'

PROJECT_REPO_TYPE = 'git'
PROJECT_REPO_URL = 'git@github.com:user/My-Project.git'

EXTRA_APPS = (
    {
        'name': 'someapp', 
        'production':  {'type': 'git', 
                        'source': 'git+ssh://user@host/home/user/someapp.git', 
                        'dir': '/home/user/djapps/someapp',
                       },
        'staging':     {'type': 'git', 
                        'source': 'git+ssh://user@host/home/user/someapp.git', 
                        'dir': '/home/user/djapps/someapp_staging',
                       },
        'development': {'type': 'git', 
                        'source': 'git+ssh://user@host/home/user/someapp.git', 
                        'dir': '/home/user/djapps/someapp_development',
                       },
    },
    {
        'name': 'anotherapp', 
        'production':  {'type': 'editable', 
                        'source': '/home/user/django_gunicorn_project/django-someapp',
                        'dir': '/home/user/django_gunicorn_project/django-someapp',
                       },
        'staging':     {'type': 'editable', 
                        'source': '/home/user/django_gunicorn_project_staging/django-someapp',
                        'dir': '/home/user/django_gunicorn_project_staging/django-someapp',
                       },
        'development': {'type': 'editable', 
                        'source': '/home/user/django_gunicorn_project_development/django-someapp',
                        'dir': '/home/user/django_gunicorn_project_development/django-someapp',
                       },
    },
)

# Web servers should be setup one by one.
# Public ip and port to be used by Nginx will be passed for each web server in setup_nginx.

UBUNTU_PACKAGES=('man',
                 'manpages',
                 'git-core',
                 'nginx',
                 'python-pip',
                 'postgresql-server-dev-9.1',
                 'postgresql-client-9.1',
                 'sqlite3',
                 'python-dev'
                )

PIP_PACKAGES=('virtualenv',
              'virtualenvwrapper',
              'Fabric',
             )

PIP_VENV_PACKAGES=('psycopg2',
                   'ipython',
                   'yolk',
                   'Django==1.4',
                   'gunicorn',
                   'Fabric',
                   'South',
                   'Sphinx',
                   'docutils',
                  )

MIRROR_URL = '-i http://d.pypi.python.org/simple'

#### END OF CONFIGURATION ####

########NEW FILE########
__FILENAME__ = fabfile
"""
This Fabric script allows you setup an Ubuntu 11.10 server to run a Django project with Nginx and gunicorn.

How to use
===============

1. This step is optional. If you still haven't created a user to run the project you can start with an existing user to create one.
$ fab -H existing_user@host add_user:user
That will create user with a random password and sudo permissions.

2. Fill configuration details in settings.py.

3. Run setup to install the server applications, create virtualenvs, install basic Python packages and configuration files for one or more environments.
Start creating a development environment on the development box.
Then create a staging environment, ideally on one of the production boxes, as it will be used to get code from repositories and then rsync to production.
$ fab -H user@host setup:production,staging,development,mirror=y

4. Install or update project and apps for one environment.
$ fab -H user@host update_site:env=production,update_settings=y,upgrade_apps=y

5. To start, stop or restart the site on one environment.
$ fab -H user@host start_site:env=production
$ fab -H user@host stop_site:env=production
$ fab -H user@host restart_site:env=production

6. Work on the development environment and use this to commit from time to time.

$ fab -H user@host commit:env=development,message='commit message and escaping comma\, this way',push=n,test=y

7. To run setup, update_site and start_site all in one step.

$ fab -H user@host quickstart:development,update_settings=y

Parameters:
env: 'production', 'staging', 'development'.
mirror: 'y', 'n'. Default: 'n'.

Development can be accessed at http://PROJECT_DOMAIN_DEVELOPMENT:development_port
Staging can be accessed at http://PROJECT_DOMAIN_STAGING:staging_port
Production can be accessed at http://PROJECT_DOMAIN:port

For more detailed instructions see README in The-Django-gunicorn-fabfile-project.
https://github.com/alexisbellido/The-Django-gunicorn-fabfile-project
"""

from fabric.api import run, sudo, hosts, settings, abort, warn, cd, local, put, get, env
from fabric.contrib.files import exists, sed, comment, contains
from fabric.contrib.files import append as fabappend
from fabric.contrib.console import confirm
from fabric.utils import warn
from fabric.context_managers import hide
from fabric.contrib import django

import string, random

def build_projects_vars():
    project_settings = get_settings()
    projects = {'production': {}, 'staging': {}, 'development': {}}

    projects['production']['user'] = projects['staging']['user'] = projects['development']['user'] = project_settings.PROJECT_USER
    projects['production']['inner_dir'] = projects['staging']['inner_dir'] = projects['development']['inner_dir'] = project_settings.PROJECT_INNER_DIR
    projects['production']['repo_url'] = projects['staging']['repo_url'] = projects['development']['repo_url'] = project_settings.PROJECT_REPO_URL

    projects['production']['settings_path'] = projects['staging']['settings_path'] = projects['development']['settings_path'] = project_settings.PROJECT_SETTINGS_PATH

    projects['production']['domain'] = project_settings.PROJECT_DOMAIN
    projects['staging']['domain'] = project_settings.PROJECT_DOMAIN_STAGING
    projects['development']['domain'] = project_settings.PROJECT_DOMAIN_DEVELOPMENT

    projects['production']['gunicorn_loglevel'] = project_settings.PROJECT_GUNICORN_LOGLEVEL
    projects['staging']['gunicorn_loglevel'] = projects['development']['gunicorn_loglevel'] = project_settings.PROJECT_GUNICORN_LOGLEVEL_STAGING

    projects['production']['gunicorn_num_workers'] = project_settings.PROJECT_GUNICORN_NUM_WORKERS
    projects['staging']['gunicorn_num_workers'] = projects['development']['gunicorn_num_workers'] = project_settings.PROJECT_GUNICORN_NUM_WORKERS_STAGING

    projects['production']['gunicorn_bind_ip'] = project_settings.PROJECT_GUNICORN_BIND_IP
    projects['staging']['gunicorn_bind_ip'] = projects['development']['gunicorn_bind_ip'] = project_settings.PROJECT_GUNICORN_BIND_IP_STAGING

    projects['production']['gunicorn_bind_port'] = project_settings.PROJECT_GUNICORN_BIND_PORT
    projects['staging']['gunicorn_bind_port'] = project_settings.PROJECT_GUNICORN_BIND_PORT_STAGING
    projects['development']['gunicorn_bind_port'] = project_settings.PROJECT_GUNICORN_BIND_PORT_DEVELOPMENT

    for key in projects.keys():
        projects[key]['name'] = suffix(project_settings.PROJECT_NAME, key)
        projects[key]['descriptive_name'] = suffix(project_settings.PROJECT_DESCRIPTIVE_NAME, key)
        projects[key]['dir'] = suffix(project_settings.PROJECT_DIR, key)
        projects[key]['run-project'] = suffix('run-project', key)
        projects[key]['django-project'] = suffix('django-project', key)
        projects[key]['logdir'] = suffix(project_settings.PROJECT_LOGDIR, key)
        projects[key]['log_gunicorn'] = project_settings.PROJECT_LOG_GUNICORN
        projects[key]['log_nginx_access'] = project_settings.PROJECT_LOG_NGINX_ACCESS
        projects[key]['log_nginx_error'] = project_settings.PROJECT_LOG_NGINX_ERROR
        projects[key]['script_name'] = suffix(project_settings.PROJECT_SCRIPT_NAME, key)
        projects[key]['gunicorn_bind_address'] = '%s:%s' % (projects[key]['gunicorn_bind_ip'], projects[key]['gunicorn_bind_port'])

        if key == 'production':
            projects[key]['ip'] = project_settings.PROJECT_NGINX_IP
            projects[key]['port'] = project_settings.PROJECT_NGINX_PORT

        if key == 'staging':
            projects[key]['ip'] = project_settings.PROJECT_NGINX_IP_STAGING
            projects[key]['port'] = project_settings.PROJECT_NGINX_PORT_STAGING

        if key == 'development':
            projects[key]['ip'] = project_settings.PROJECT_NGINX_IP_DEVELOPMENT
            projects[key]['port'] = project_settings.PROJECT_NGINX_PORT_DEVELOPMENT

    return projects

def build_parameters_list(projects, key):
    """
    Choose a key and create a list containing the value for that key for the development, staging and production keys
    on the projects dictionary.
    """
    seq = []
    projects = build_projects_vars()
    for project in projects.values():
        seq.append(project[key])
    return seq

def suffix(string, suffix, sep = '_'):
    """
    Adds a suffix to staging and development values.
    Example: if dir_name is the value for production then dir_name_staging and dir_name_development will
    be used for staging and development.
    """
    if suffix == 'production':
        suffixed = string
    else:
        suffixed = string + sep + suffix
    return suffixed

def debug(x=''):
    """
    Simple debugging of some functions
    """
    project_settings = get_settings()
    print project_settings.EXTRA_APPS

def get_settings():
    import os
    import sys

    root_dir = os.path.dirname(__file__)
    sys.path.insert(0, root_dir)

    import fabconfig
    return fabconfig

def add_user(user):
    sudo('useradd %s -s /bin/bash -m' % user)
    sudo('echo "%s ALL=(ALL) ALL" >> /etc/sudoers' % user)
    password = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8))
    sudo('echo "%s:%s" | chpasswd' % (user, password))
    print "Password for %s is %s" % (user, password)

def fix_venv_permission():
    projects = build_projects_vars()
    project = projects['development'] # could use any environment as key user is always the same
    with settings(hide('warnings'), warn_only=True):
        sudo('chown -R %(user)s:%(user)s /home/%(user)s/.virtualenvs' % {'user': project['user']})

def setup_server(mirror=''):
    project_settings = get_settings()
    projects = build_projects_vars()
    project = projects['development'] # could use any environment as key user is always the same

    if mirror == 'y':
        mirror_url = project_settings.MIRROR_URL
    else:
        mirror_url = ''

    for p in project_settings.UBUNTU_PACKAGES:
        sudo('apt-get -y install %s' % p)

    sudo('pip install pip --upgrade %s' % mirror_url)
    
    for p in project_settings.PIP_PACKAGES:
        sudo('sudo pip install %s %s' % (p, mirror_url))

    # fixes Warning: cannot find svn location for distribute==0.6.16dev-r0
    sudo('pip install distribute --upgrade %s' % mirror_url)

    fix_venv_permission()

    for file in ('.bash_profile', '.bashrc'):
        if not contains('/home/%s/%s' % (project['user'], file), 'export WORKON_HOME'):
            run('echo "export WORKON_HOME=$HOME/.virtualenvs" >> /home/%s/%s' % (project['user'], file))
        if not contains('/home/%s/%s' % (project['user'], file), 'source /usr/local/bin/virtualenvwrapper.sh'):
            run('echo "source /usr/local/bin/virtualenvwrapper.sh" >> /home/%s/%s' % (project['user'], file))

def setup_django(*args, **kwargs):
    project_settings = get_settings()
    projects = build_projects_vars()
    mirror = kwargs.get('mirror','n')
    if mirror == 'y':
        mirror_url = project_settings.MIRROR_URL
    else:
        mirror_url = ''

    for key in args:
        if not exists(projects[key]['logdir']):
            run('mkdir -p %s' % projects[key]['logdir'])
            # these need to be created by the user to avoid permission problems when running Nginx and gunicorn
            run('touch %s/%s' % (projects[key]['logdir'], projects[key]['log_gunicorn']))
            run('touch %s/%s' % (projects[key]['logdir'], projects[key]['log_nginx_access']))
            run('touch %s/%s' % (projects[key]['logdir'], projects[key]['log_nginx_error']))

        run('mkvirtualenv %s' % projects[key]['name'])

        for p in project_settings.PIP_VENV_PACKAGES:
            run('workon %s && pip install %s %s' % (projects[key]['name'], p, mirror_url))

def put_settings_files(env='development'):
    """
    Only used when called explicitly, we don't want to change settings by default
    """
    projects = build_projects_vars()
    project = projects[env]
    if exists('%(dir)s/%(inner_dir)s' % project):
        put(project['settings_path'], '%(dir)s/%(inner_dir)s/local_settings.py' % project)
        if env == 'production':
            with cd('%(dir)s/%(inner_dir)s' % project):
                sed('local_settings.py', '^DEBUG = True$', 'DEBUG = False') 

# TODO revisit how the apps are committed and update from production, it may be safer using different
# repositories or probably branches.

def update_apps(env='development', upgrade_apps='n'):
    """
    Install the project related apps. It can use pip install from a repository or use the editable option to install from a source directory.
    Examples of commands generated:
    pip install git+ssh://user@githost/home/user/someapp.git
    pip install -e /home/user/anotherapp/
    """

    project_settings = get_settings()
    projects = build_projects_vars()
    project = projects[env]

    for app in project_settings.EXTRA_APPS:
        option = ''
        if app[env]['type'] == 'git' and upgrade_apps == 'y':
            option = '--upgrade'
        if app[env]['type'] == 'editable':
            option = '-e'

        run('workon %(name)s && pip install %(option)s %(source)s' % {'name': project['name'], 'option': option, 'source': app[env]['source']})

def update_project(env='development', update_settings='n'):
    projects = build_projects_vars()
    project = projects[env]

    # TODO check if previous setup steps done, optional to avoid following the correct order manually
    # TODO check that staging env is set before running for production, optional to avoid following the correct order manually

    if env == 'production':
        if exists(projects['staging']['dir']):
            run('rsync -az --delete-after --exclude=.git --exclude=.gitignore --exclude=deploy --exclude=local_settings*  --exclude=*.pyc --exclude=*.pyo %s/ %s' % (projects['staging']['dir'], project['dir']))
        else:
            print "Staging environment doesn't exist. Please create it before running update_project for production on this host."
    else:
        if exists(project['dir']):
            run('cd %(dir)s && git pull' % project)
        else:
            run('git clone %(repo_url)s %(dir)s' % project)

    if not exists('%(dir)s/static' % project):
        run('mkdir -p %(dir)s/static' % project)

    if not exists('%(dir)s/static/admin' % project):
        run('ln -s /home/%(user)s/.virtualenvs/%(name)s/lib/python2.7/site-packages/django/contrib/admin/static/admin/ %(dir)s/static/admin' % project)

    if update_settings == 'y':
        put_settings_files(env)

def put_config_files(*args):
    """
    Call with the names of the enviroments where you want to put the config files, for example:
    fab -H user@host put_config_files:production,staging,development
    """
    # fix for nginx: Starting nginx: nginx: [emerg] could not build the types_hash, you should increase either types_hash_max_size: 1024 or types_hash_bucket_size: 32
    sed('/etc/nginx/nginx.conf', '# types_hash_max_size.*', 'types_hash_max_size 2048;', use_sudo=True) 
    # fix for nginx: [emerg] could not build the server_names_hash, you should increase server_names_hash_bucket_size: 32
    sed('/etc/nginx/nginx.conf', '# server_names_hash_bucket_size.*', 'server_names_hash_bucket_size 64;', use_sudo=True) 
    put('deploy', '/tmp/')
    projects = build_projects_vars()

    for key in args:
        """
        Copy basic configuration files, this has to be done first for all environments to avoid changing the original contents
        required by sed on the next loop.
        """
        with cd('/tmp/deploy/'):
            print "COPYING CONFIGURATION FILES FOR  %s..." % key
            if key != 'production':
                run('cp run-project %(run-project)s' % projects[key])
                run('cp etc/nginx/sites-available/django-project etc/nginx/sites-available/%(django-project)s' % projects[key])
                run('cp etc/init/django-project.conf etc/init/%(django-project)s.conf' % projects[key])

    for key in args:
        """
        Loop over the original configuration files, make changes with sed and then copy to final locations.
        """
        with cd('/tmp/deploy/'):
            print "SETTING UP CONFIGURATION FILES FOR %s..." % key
            sed(projects[key]['run-project'], '^LOGFILE.*', 'LOGFILE=%(logdir)s/%(log_gunicorn)s' % projects[key]) 
            sed(projects[key]['run-project'], '^LOGLEVEL.*', 'LOGLEVEL=%(gunicorn_loglevel)s' % projects[key]) 
            sed(projects[key]['run-project'], '^NUM_WORKERS.*', 'NUM_WORKERS=%(gunicorn_num_workers)s' % projects[key]) 
            sed(projects[key]['run-project'], '^BIND_ADDRESS.*', 'BIND_ADDRESS=%(gunicorn_bind_ip)s:%(gunicorn_bind_port)s' % projects[key]) 
            sed(projects[key]['run-project'], '^USER.*', 'USER=%(user)s' % projects[key]) 
            sed(projects[key]['run-project'], '^GROUP.*', 'GROUP=%(user)s' % projects[key]) 
            sed(projects[key]['run-project'], '^PROJECTDIR.*', 'PROJECTDIR=%(dir)s' % projects[key]) 
            sed(projects[key]['run-project'], '^PROJECTENV.*', 'PROJECTENV=/home/%(user)s/.virtualenvs/%(name)s' % projects[key]) 

            # TODO figure out how to handle redirection from non-www to www versions passing the port, if needed.
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'listen.*', 'listen %(ip)s:%(port)s;' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'proxy_pass http.*', 'proxy_pass http://%(gunicorn_bind_ip)s:%(gunicorn_bind_port)s/;' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'example\.com', '%(domain)s' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'root.*', 'root %(dir)s;' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'access_log.*', 'access_log %(logdir)s/%(log_nginx_access)s;' % projects[key]) 
            sed('etc/nginx/sites-available/%(django-project)s' % projects[key], 'error_log.*', 'error_log %(logdir)s/%(log_nginx_error)s;' % projects[key]) 

            sed('etc/init/%(django-project)s.conf' % projects[key], '^description.*', 'description "%(descriptive_name)s"' % projects[key]) 
            sed('etc/init/%(django-project)s.conf' % projects[key], '^exec.*', 'exec /home/%(user)s/%(script_name)s' % projects[key]) 

            fix_venv_permission()
            run('cp %(run-project)s /home/%(user)s/%(script_name)s' % projects[key])
            run('chmod u+x /home/%(user)s/%(script_name)s' % projects[key]) 
            sudo('cp etc/nginx/sites-available/%(django-project)s /etc/nginx/sites-available/%(name)s' % projects[key])
            sudo('cp etc/init/%(django-project)s.conf /etc/init/%(name)s.conf' % projects[key])

            if not exists('/etc/nginx/sites-enabled/%(name)s' % projects[key]):
            	sudo('ln -s /etc/nginx/sites-available/%(name)s /etc/nginx/sites-enabled/%(name)s' % projects[key])
            
            if not exists('/etc/init.d/%(name)s' % projects[key]):
            	sudo('ln -s /lib/init/upstart-job /etc/init.d/%(name)s' % projects[key])

    with settings(hide('warnings'), warn_only=True):
        fix_venv_permission()
        sudo('rm /etc/nginx/sites-enabled/default')
        run('rm -rf /tmp/deploy')

def clean(*args, **kwargs):
    """
    Clean before reinstalling. It can be called for multiple environments and there's an optional clean_nginx argument at the end.
    fab -H user@host clean:production,staging,development,clean_nginx=y
    """

    project_settings = get_settings()
    projects = build_projects_vars()

    with settings(hide('warnings'), warn_only=True):
        sudo('service nginx stop')
        for key in args:
            print "CLEANING CONFIGURATION FILES AND STOPPING SERVICES FOR %s..." % key
            result = sudo('service %(name)s stop' % projects[key])
            if result.failed:
                warn( "%(name)s was not running." % projects[key])

            for app in project_settings.EXTRA_APPS:
                run('workon %s && pip uninstall -y %s' % (projects[key]['name'], app['name']))

            sudo('rm -rf %(dir)s' % projects[key])
            sudo('rm -rf %(logdir)s' % projects[key])
            sudo('rmvirtualenv %(name)s' % projects[key])
            sudo('rm /home/%(user)s/%(script_name)s' % projects[key])
            sudo('rm /etc/nginx/sites-enabled/%(name)s' % projects[key])
            sudo('rm /etc/nginx/sites-available/%(name)s' % projects[key])
            sudo('rm /etc/init/%(name)s.conf' % projects[key])
            sudo('rm /etc/init.d/%(name)s' % projects[key])

    if kwargs.get('clean_nginx','n') == 'y':
        sed('/etc/nginx/nginx.conf', 'types_hash_max_size.*', '# types_hash_max_size 2048;', use_sudo=True) 
        sed('/etc/nginx/nginx.conf', 'server_names_hash_bucket_size.*', '# server_names_hash_bucket_size 64;', use_sudo=True) 

    fix_venv_permission()

def quickstart(*args, **kwargs):
    """
    Run everything in one step, from empty server to running site.
    """

    setup(*args, **kwargs)
    update_site(*args, **kwargs)
    restart_site(*args, **kwargs)

def setup(*args, **kwargs):
    """
    Call with the names of the enviroments to setup and optionally add the mirror keyword argument.
    fab -H user@host setup:production,staging,development,mirror=y
    """

    mirror = kwargs.get('mirror','n')
    setup_server(mirror)
    setup_django(*args, **kwargs)
    put_config_files(*args)

def update_site(env='development', update_settings='n', upgrade_apps='n'):
    """
    Update files for the project and its companion apps.
    """
    update_project(env, update_settings)
    update_apps(env, upgrade_apps)

def start_site(env='development', **kwargs):
    sudo('service nginx start')

    projects = build_projects_vars()
    project = projects[env]

    with settings(hide('warnings'), warn_only=True):
        result = sudo('service %s start' % project['name'])
    if result.failed:
        warn( "%s already running." % project['name'])

    print "Site ready to rock at http://%s:%s" % (project['domain'], project['port'])

def stop_site(env='development', **kwargs):
    sudo('service nginx stop')

    projects = build_projects_vars()
    project = projects[env]

    with settings(hide('warnings'), warn_only=True):
        result = sudo('service %s stop' % project['name'])
    if result.failed:
        warn( "%s was not running." % project['name'])

def restart_site(env='development', **kwargs):
    stop_site(env)
    start_site(env)

def commit(env='development', message='', push='n', test='y'):
    """
    Run tests, add, commit and push files for the project and extra apps.
    Notice this adds all changed files to git index. This can e replaced by manual git commands if more granularity is needed.
    """

    project_settings = get_settings()
    projects = build_projects_vars()
    project = projects[env]

    if env != 'production':
        print "========================================================"
        print "COMMIT IN %s..." % env.upper()
        # TODO testing before committing
        #run_tests(env)
        for app in project_settings.EXTRA_APPS:
            if app[env]['dir'][:len(project['dir'])] == project['dir']:
                print "\nThe application %s is inside the project directory, no need to commit separately." % app['name']
            else:
                with settings(hide('warnings'), warn_only=True):
                    print "\nCommitting changes for application %s in %s." % (app['name'], app[env]['dir'])
                    local("cd %s && git add . && git commit -m '%s'" % (app[env]['dir'], message))
                    if push == 'y':
                        local("cd %s && git push" % app[env]['dir'])

        with settings(hide('warnings'), warn_only=True):
            print "\nCommitting changes in the directory project %s." % project['dir']
            local("cd %s && git add . && git commit -m '%s'" % (project['dir'], message))
            if push == 'y':
                local("cd %s && git push" % project['dir'])
        print "========================================================"

def run_tests(env='development'):
    # TODO test on development, staging and production? I think so
    # TODO allow testing per app, use a parameter
    #run("./manage.py test my_app")
    projects = build_projects_vars()
    project = projects[env]
    with cd(project['dir']):
        run('workon %s && python manage.py test' % project['dir'])

def deploy(env='development', update_settings='n', upgrade_apps='n'):
    """
    Run update the site and then restart it for the specified environment. Run after successful test and commit.
    """
    update_site(env, update_settings, upgrade_apps)
    restart_site(env)

########NEW FILE########
__FILENAME__ = local_settings_template
DEBUG = True

#if DEBUG:
#	# add my apps to PYTHONPATH, ideally in production these apps should installed in the virtualenv via pip
#    import os
#    import sys
#    I can add a list of paths and add them to sys.path in one command
#    sys.path.insert(0, "/app-parent-dir")

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': '',                      # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': '',                      # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

STATIC_ROOT = ''
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'REPLACE-THIS-IS-A-PLACEHOLDER-KEY-$xy*t!si3gfl60o9^-*a3(hz0r%572t25mo5o8&vx99fbfp*+-'

#MIDDLEWARE_CLASSES = (
#    'middleware.DeleteSessionOnLogoutMiddleware', # Varnish http://ghughes.com/blog/2011/11/11/using-varnish-with-django-for-high-performance-caching/
#    'django.middleware.common.CommonMiddleware',
#    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
#)

ROOT_URLCONF = 'urls' # no need to include project name

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
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'gunicorn', # you need this one to launch the Django project with gunicorn
)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_gunicorn_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
