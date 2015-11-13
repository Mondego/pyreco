__FILENAME__ = deployment
import imp
import os
import sys
import hashlib
import getpass

def bootstrap_script(path, project_path_components):
    project_path = os.path.join(find_parent_path(path, project_path_components), *project_path_components)
    bootstrap(project_path)

def bootstrap(path):
    path = find_settings_path(path)

    from django.core import management
    try:
        settings = imp.load_source('settings', os.path.join(path, 'settings.py'))
    except ImportError:
        sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
        sys.exit(1)

    management.setup_environ(settings)

def find_settings_path(path):
    """Legacy support."""
    return find_parent_path(path, ['settings.py'])

def find_parent_path(path, child_path_components):
    """Retrieve the path of the provided file in the closest parent path from the provided path. (This can be passed into django_utils.bootstrap). You can pass in the __file__ variable, or an absolute path, and it will find the closest file."""
    if os.path.isfile(path):
        path = os.path.dirname(path)

    path = os.path.abspath(path)
    parent_path = os.path.abspath(os.path.join(path, '..'))
    target_path = os.path.join(path, *child_path_components)

    if os.path.exists(target_path):
        return path
    elif path != parent_path:
        return find_parent_path(parent_path, child_path_components)
    else:
        raise Exception('Could not find file path.')

def get_config_identifiers(path):
    config_dir = os.path.join(find_settings_path(path), 'config')
    files = list(os.walk(config_dir))
    if not files:
        sys.stderr.write("Your django application does not appear to have been setup with switchable configurations.\n")
        sys.exit(0)

    files = files[0][2] + files[0][1]
    identifiers = map(lambda name: name.split('.', 1)[0], filter(lambda name: ('.' not in name or name.endswith(".py")) and name not in ('__init__.py', 'base.py',), files))
    return [ (i + 1, x) for i, x in enumerate(identifiers) ]

def setup_environment(path):
    IDENTIFIERS = get_config_identifiers(path)
    CONFIG_IDENTIFIER = os.environ.get('CONFIG_IDENTIFIER', '')

    # If we are trying to use runserver, then look for existing configuration so that auto reload does not keep propmpting for the configuration file.
    if len(sys.argv) >= 2 and sys.argv[1] in ('runserver', 'runserver_plus',):
        if 'CONFIG_IDENTIFIER' in os.environ and CONFIG_IDENTIFIER in [name for id, name in IDENTIFIERS]:
            bootstrap(path)
            return

    IDENTIFIERS_LOOKUP = dict(IDENTIFIERS)
    IDENTIFIERS_REVERSE_LOOKUP = dict([[ name, id ] for id, name in IDENTIFIERS ])

    CONFIG_IDENTIFIER_ID = IDENTIFIERS_REVERSE_LOOKUP.get(CONFIG_IDENTIFIER, '')
    CONFIG_IDENTIFIER_INTERACTIVE = os.environ.get('CONFIG_IDENTIFIER_INTERACTIVE', 'True')

    if CONFIG_IDENTIFIER and CONFIG_IDENTIFIER_INTERACTIVE == 'False':
        print "WARNING: Forced to run environment with %s configuration." % CONFIG_IDENTIFIER.upper()
        return bootstrap(path)

    while True:
        print "Please select your config identifier."
        for id, name in IDENTIFIERS:
            print "   %s) %s" % (id, name)

        try:
            selection = raw_input("What config identifier would you like to use? [%s] " % CONFIG_IDENTIFIER_ID)
        except:
            # Capture if they hard escape during the getpass prompt. Clear the newline, and exit.
            print ''
            sys.exit(0)

        selection = selection.isdigit() and int(selection) or (selection and selection or CONFIG_IDENTIFIER_ID)

        if selection and IDENTIFIERS_LOOKUP.has_key(selection):
            identifier = dict(IDENTIFIERS).get(int(selection))

            # We need to load up the selected settings environment to see if we need to double check for security purposes.
            # If the database_host is not empty (not a local database) then we need to confirm that the user REALLY wants
            # to run the command on a potentially production database.
            settings_path = find_settings_path(path)


            # Set the config identifier to the selected one, so that the correct configuration gets loaded up.
            os.environ['CONFIG_IDENTIFIER'] = identifier
            os.putenv('CONFIG_IDENTIFIER', identifier)

            # Import the settings file into local scope.
            settings = imp.load_source('settings', os.path.join(settings_path, 'settings.py'))

            # Reset the config identifier and system path to what they were before.
            os.putenv('CONFIG_IDENTIFIER', CONFIG_IDENTIFIER)
            os.environ['CONFIG_IDENTIFIER'] = CONFIG_IDENTIFIER

            # If the database host for the selected configuration is not empty (not a local database). Prompt for password.
            if getattr(settings, 'ENABLE_PASSWORD', False) and getattr(settings, 'PASSWORD_DIGEST', ''):
                try:
                    password = getpass.getpass('Please enter the password to load <%s>: ' % identifier)
                except:
                    # Capture if they hard escape during the getpass prompt. Clear the newline, and exit.
                    print ''
                    sys.exit(0)
                else:
                    if hashlib.md5(password).hexdigest() != settings.PASSWORD_DIGEST:
                        print 'Invalid password.'
                        continue


            CONFIG_IDENTIFIER = identifier
            break

    # Update the current config identifier.
    os.environ['CONFIG_IDENTIFIER'] = CONFIG_IDENTIFIER
    os.putenv('CONFIG_IDENTIFIER', CONFIG_IDENTIFIER)

    # Now that we have setup our identifier, initialize our django project.
    bootstrap(path)

########NEW FILE########
__FILENAME__ = base
# Django settings for flyingcircus project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = False

MEDIA_ROOT = ''
MEDIA_URL = ''

ADMIN_MEDIA_PREFIX = '/media/'

SECRET_KEY = '6%9(uekw#juzbfebfhtl=m@u08@w#g0bx)%z@bc0cu-(*cq1o('

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'flyingcircus.urls'

TEMPLATE_DIRS = (
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'flyingcircus'
)

########NEW FILE########
__FILENAME__ = local
ADMINS = (('Django User', 'djuser@djangoproject.com'),)

# Database Configuration

DATABASE_ENGINE = 'mysql'
DATABASE_NAME = 'configdemo'
DATABASE_USER = 'root'
DATABASE_PASSWORD = ''
DATABASE_HOST = 'localhost'
DATABASE_PORT = '3306'
DEFAULT_CHARSET = 'utf-8'
DATABASE_OPTIONS = {
    'sql_mode': 'TRADITIONAL,STRICT_ALL_TABLES,ANSI',
    'charset': 'utf8',
    'init_command': 'SET storage_engine=INNODB',
}

########NEW FILE########
__FILENAME__ = monty
ADMINS = (('Monty Python', 'mpython@djangoproject.com'),)

# Database Configuration

import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'db'))

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '%s/monty.db' % db_path
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''
DATABASE_OPTIONS = {
}

ENABLE_PASSWORD = True
PASSWORD_DIGEST = '97e43572f170e47d0df46fad5a3fe7d9'

########NEW FILE########
__FILENAME__ = testing
ADMINS = (('Project Tester', 'ptester@djangoproject.com'),)

# Database Configuration

import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'db'))

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '%s/testing.db' % db_path
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''
DATABASE_OPTIONS = {
}

TEST_DATABASE_NAME = '%s/testing.db' % db_path

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import sys
import os

from djangoconfig import setup_environment

try:
    setup_environment(__file__)
except KeyboardInterrupt:
    print ""
    print "Exiting script."
    sys.exit(0)

import settings
from django.core import management

if __name__ == "__main__":
    management.execute_manager(settings)

########NEW FILE########
__FILENAME__ = models
from django.db import models

class FlyingCircus(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = settings
"""
Django-config settings loader.
"""

import os

CONFIG_IDENTIFIER = os.getenv("CONFIG_IDENTIFIER")

# Import defaults
from flyingcircus.config.base import *

# Import overrides
overrides = __import__(
    "flyingcircus.config." + CONFIG_IDENTIFIER,
    globals(),
    locals(),
    ["flyingcircus.config"]
)

# Apply imported overrides
for attribute in dir(overrides):
    # We only want to import settings (which have to be variables in ALLCAPS)
    if attribute.isupper():
        # Update our scope with the imported variables. We use globals() instead of locals()
        # Because locals() is readonly and it returns a copy of itself upon assignment.
        globals()[attribute] = getattr(overrides, attribute)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import url, include, patterns, handler404, handler500

from flyingcircus import views

urlpatterns = patterns('',
    url('^$', views.index, name='index'),
)
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings

def index(request):
    return render_to_response('flyingcircus/index.html', {
        'settings': settings,
        }, context_instance=RequestContext(request))

########NEW FILE########
