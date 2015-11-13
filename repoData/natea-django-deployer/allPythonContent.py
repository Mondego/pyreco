__FILENAME__ = fabfile
from django_deployer.tasks import *

########NEW FILE########
__FILENAME__ = helpers
import os
import re
import yaml

from fabric.colors import green, red, yellow


DEPLOY_YAML = os.path.join(os.getcwd(), 'deploy.yml')


#
# Helpers
#

def _create_deploy_yaml(site):
    _green("Creating a deploy.yml with your app's deploy info...")
    _write_file(DEPLOY_YAML, yaml.safe_dump(site, default_flow_style=False))
    _green("Created %s" % DEPLOY_YAML)


def _validate_django_settings(django_settings):
    django_settings_regex = r"^[\d\w_.]+$"

    pattern = re.compile(django_settings_regex)
    if not pattern.match(django_settings):
        raise ValueError(red("You must enter a valid dotted module path to continue!"))

    django_settings_path = django_settings.replace('.', '/') + '.py'
    if not os.path.exists(django_settings_path):
        raise ValueError(red(
            "Couldn't find a settings file at that dotted path.\n"
            "Make sure you're using django-deployer from your project root."
        ))

    return django_settings


def _validate_project_name(project_name):
    project_name_regex = r"^.+$"

    pattern = re.compile(project_name_regex)
    if not pattern.match(project_name):
        raise ValueError(red("You must enter a project name to continue!"))

    if not os.path.exists(os.path.join(os.getcwd(), project_name)):
        raise ValueError(red(
            "Couldn't find that directory name under the current directory.\n"
            "Make sure you're using django-deployer from your project root."
        ))

    return project_name


def _validate_requirements(requirements):

    if not requirements.endswith(".txt"):
        raise ValueError(red("Requirements file must end with .txt"))

    if not os.path.exists(os.path.join(os.getcwd(), requirements)):
        raise ValueError(red(
            "Couldn't find requirements.txt at the path you gave.\n"
            "Make sure you're using django-deployer from your project root."
        ))

    return requirements


def _validate_managepy(managepy):
    managepy_regex = r"^.+manage.py$"

    pattern = re.compile(managepy_regex)
    if not pattern.match(managepy):
        raise ValueError(red(
            "Couldn't find manage.py at the path you gave.\n"
            "You must enter the relative path to your manage.py file to continue!"
        ))

    if not os.path.exists(os.path.join(os.getcwd(), managepy)):
        raise ValueError(red(
            "Couldn't find manage.py at the path you gave.\n"
            "Make sure you're using django-deployer from your project root."
        ))

    return managepy


def _validate_admin_password(admin_password):
    password_regex = r"[A-Za-z0-9@#$%^&+=]{6,}"

    pattern = re.compile(password_regex)
    if not pattern.match(admin_password):
        raise ValueError(red(
            "The password must be at least 6 characters and contain only the following characters:\n"
            "A-Za-z0-9@#$%^&+="
        ))

    return admin_password


def _validate_providers(provider):
    providers = ['stackato', 'dotcloud', 'appengine', 'openshift']

    if provider not in providers:
        raise ValueError(red(
            "Invalid provider. You must choose one of these providers:\n"
            "%s" % providers
        ))

    return provider


#
# Utils
#

def _write_file(path, contents):
    file = open(path, 'w')
    file.write(contents)
    file.close()


def _read_file(path):
    file = open(path, 'r')
    contents = file.read()
    file.close()
    return contents


def _join(*args):
    """
    Convenience wrapper around os.path.join to make the rest of our
    functions more readable.
    """
    return os.path.join(*args)


#
# Pretty colors
#

def _green(text):
    print green(text)


def _red(text):
    print red(text)


def _yellow(text):
    print yellow(text)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

import os
import shutil



PACKAGE_ROOT = os.path.dirname(__file__)


def add_fabfile():
    """
    Copy the base fabfile.py to the current working directory.
    """
    fabfile_src  = os.path.join(PACKAGE_ROOT, 'fabfile.py')
    fabfile_dest = os.path.join(os.getcwd(), 'fabfile_deployer.py')

    if os.path.exists(fabfile_dest):
        print "`fabfile.py` exists in the current directory. " \
              "Please remove or rename it and try again."
        return

    shutil.copyfile(fabfile_src, fabfile_dest)

########NEW FILE########
__FILENAME__ = settings_appengine
try:
    import dev_appserver
    dev_appserver.fix_sys_path()
except:
    pass


import os
import sys

PROJECT_ROOT = os.path.dirname(__file__)

on_appengine = os.getenv('SERVER_SOFTWARE','').startswith('Google App Engine')

# insert libraries
REQUIRE_LIB_PATH = os.path.join(os.path.dirname(__file__), '..', 'site-packages')

lib_to_insert = [REQUIRE_LIB_PATH]
map(lambda path: sys.path.insert(0, path), lib_to_insert)

# settings need to be after insertion of libraries' location
from settings import *

# use cloudsql while on the production
if (on_appengine or
    os.getenv('SETTINGS_MODE') == 'prod'):
    # here must use 'SETTINGS_MODE' == 'prod', it's not included in rocket_engine.on_appengine
    # Running on production App Engine, so use a Google Cloud SQL database.
    DATABASES = {
        'default': {
            'ENGINE': 'google.appengine.ext.django.backends.rdbms',
            'INSTANCE': '{{ instancename }}',
            'NAME': '{{ databasename }}',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'django_deployer_default',
            'USER': '',
            'PASSWORD': '',
        }
    }

# Installed apps for django-deployer
PAAS_INSTALLED_APPS = (
    'rocket_engine',
)

INSTALLED_APPS = tuple(list(INSTALLED_APPS) + list(PAAS_INSTALLED_APPS))

# django email backend for appengine
EMAIL_BACKEND = 'rocket_engine.mail.EmailBackend'
DEFAULT_FROM_EMAIL='example@example.com'
#NOTICE: DEFAULT_FROM_EMAIL need to be authorized beforehand in AppEngine console, you must be verified with the permission to access that mail address.
#Steps:
#1. Change DEFAULT_FROM_EMAIL above to an valid email address and you have the permission to access it.
#2. Log in to your Google App Engine Account.
#3. Under Administration, click Permissions, and add the email address.
#4. Log out, and check for the validation email.

# use Blob datastore for default file storage
DEFAULT_FILE_STORAGE = 'django-google-storage.storage.GoogleStorage'
GS_ACCESS_KEY_ID = '<fill-your-own>'
GS_SECRET_ACCESS_KEY = '<fill-your-own>'
GS_STORAGE_BUCKET_NAME = '<fill-your-own>'

if not (GS_ACCESS_KEY_ID and GS_SECRET_ACCESS_KEY and GS_STORAGE_BUCKET_NAME):
    print 'Warning: no correct settings for Google Storage, please provide it in settings_appengine.py'

# static_url
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# media url
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')

# use overwriting urls
ROOT_URLCONF = "{{ project_name }}.urls_appengine"

########NEW FILE########
__FILENAME__ = urls_appengine
from urls import *

urlpatterns += patterns(
    url(r'^media/(?P<filename>.*)/$','rocket_engine.views.file_serve'),
)

########NEW FILE########
__FILENAME__ = createdb
import os
import time

import MySQLdb
import psycopg2
import _mysql_exceptions
from wsgi import *


def create_dbs():
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            print("create_dbs: let's go.")
            django_settings = __import__(os.environ['DJANGO_SETTINGS_MODULE'], fromlist='DATABASES')
            print("create_dbs: got settings.")
            databases = django_settings.DATABASES
            for name, db in databases.iteritems():
                host = db['HOST']
                user = db['USER']
                password = db['PASSWORD']
                port = db['PORT']
                db_name = db['NAME']
                db_type = db['ENGINE']
                # see if it is mysql
                if db_type.endswith('mysql'):
                    print 'creating database %s on %s' % (db_name, host)
                    db = MySQLdb.connect(user=user,
                                         passwd=password,
                                         host=host,
                                         port=port)
                    cur = db.cursor()
                    print("Check if database is already there.")
                    cur.execute("""SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA
                                 WHERE SCHEMA_NAME = %s""", (db_name,))
                    results = cur.fetchone()
                    if not results:
                        print("Database %s doesn't exist, lets create it." % db_name)
                        sql = """CREATE DATABASE IF NOT EXISTS %s """ % (db_name,)
                        print("> %s" % sql)
                        cur.execute(sql)
                        print(".....")
                    else:
                        print("database already exists, moving on to next step.")
                    exit(0)
                # see if it is postgresql
                elif db_type.endswith('postgresql_psycopg2'):
                    print 'creating database %s on %s' % (db_name, host)
                    con = psycopg2.connect(host=host, user=user, password=password, port=port, database='postgres')
                    con.set_isolation_level(0)
                    cur = con.cursor()
                    try:
                        cur.execute('CREATE DATABASE %s' % db_name)
                    except psycopg2.ProgrammingError as detail:
                        print detail
                        print 'moving right along...'
                    exit(0)
                else:
                    print("ERROR: {0} is not supported by this script, you will need to create your database by hand.".format(db_type))
                    exit(1)
        except psycopg2.OperationalError:
            print "Could not connect to database. Waiting a little bit."
            time.sleep(10)
        except _mysql_exceptions.OperationalError:
            print "Could not connect to database. Waiting a little bit."
            time.sleep(10)

    print 'Could not connect to database after 1 minutes. Something is wrong.'
    exit(1)

if __name__ == '__main__':
    import sys
    print("create_dbs start")
    create_dbs()
    print("create_dbs all done")

########NEW FILE########
__FILENAME__ = mkadmin
#!/usr/bin/env python
from wsgi import *
from django.contrib.auth.models import User
u, created = User.objects.get_or_create(username='admin')
if created:
    u.set_password('{{ admin_password }}')
    u.is_superuser = True
    u.is_staff = True
    u.save()
########NEW FILE########
__FILENAME__ = settings_dotcloud
import json

with open('/home/dotcloud/environment.json') as f:
    env = json.load(f)

from .settings import *

STATIC_ROOT = '/home/dotcloud/volatile/static/'
STATIC_URL = '{{ static_url }}'

MEDIA_ROOT = '/home/dotcloud/data/media/'
MEDIA_URL = '{{ media_url }}'

if 'DOTCLOUD_DATA_MYSQL_HOST' in env:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env['DOTCLOUD_PROJECT'],
            'USER': env['DOTCLOUD_DATA_MYSQL_LOGIN'],
            'PASSWORD': env['DOTCLOUD_DATA_MYSQL_PASSWORD'],
            'HOST': env['DOTCLOUD_DATA_MYSQL_HOST'],
            'PORT': int(env['DOTCLOUD_DATA_MYSQL_PORT']),
        }
    }
elif 'DOTCLOUD_DB_SQL_HOST' in env:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': env['DOTCLOUD_PROJECT'],
            'USER': env['DOTCLOUD_DB_SQL_LOGIN'],
            'PASSWORD': env['DOTCLOUD_DB_SQL_PASSWORD'],
            'HOST': env['DOTCLOUD_DB_SQL_HOST'],
            'PORT': int(env['DOTCLOUD_DB_SQL_PORT']),
        }
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple"
        }
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.request": {
            "propagate": True,
        },
    }
}
########NEW FILE########
__FILENAME__ = wsgi
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),'{{ project_name }}')))
os.environ['DJANGO_SETTINGS_MODULE'] = '{{ django_settings }}_{{ provider }}'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
########NEW FILE########
__FILENAME__ = settings_gondor
import os

import dj_database_url

from .settings import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    "default": dj_database_url.config(env="GONDOR_DATABASE_URL"),
}

MEDIA_ROOT = os.path.join(os.environ["GONDOR_DATA_DIR"], "site_media", "media")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple"
        }
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.request": {
            "propagate": True,
        },
    }
}
########NEW FILE########
__FILENAME__ = settings_stackato
import os
import dj_database_url

from .settings import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    "default": dj_database_url.config(env["DATABASE_URL"]),
}

MEDIA_ROOT = os.environ['STACKATO_FILESYSTEM']

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple"
        }
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.request": {
            "propagate": True,
        },
    }
}
########NEW FILE########
__FILENAME__ = wsgi
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),'{{ project_name }}')))
os.environ['DJANGO_SETTINGS_MODULE'] = '{{ django_settings }}_{{ provider }}'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
########NEW FILE########
__FILENAME__ = providers
# -*- coding: utf-8 -*-
import os

from jinja2 import Environment, PackageLoader

from django_deployer.helpers import _write_file
from django_deployer import utils

from fabric.operations import local
from fabric.context_managers import shell_env


template_env = Environment(loader=PackageLoader('django_deployer', 'paas_templates'))

def run_hooks(script_name):
    HOOKS_FOLDER = 'deployer_hooks'
    local('bash %s/%s' % (HOOKS_FOLDER, script_name) )


class PaaSProvider(object):
    """
    Base PaasProvider class. PaaS providers should inherit from this
    class and override all methods.
    """

    # Subclasses should override these
    name = ""
    setup_instructions = ""
    PYVERSIONS = {}
    provider_yml_name = "%s.yml" % name
    git_template = False
    git_template_url = ""

    @classmethod
    def init(cls, site):
        """
        put site settings in the header of the script
        """
        bash_header = ""
        for k,v in site.items():
            bash_header += "%s=%s" % (k.upper(), v)
            bash_header += '\n'
        site['bash_header'] = bash_header

        # TODO: execute before_deploy
        # P.S. running init_before seems like impossible, because the file hasn't been rendered.
        if cls.git_template:
            # do render from git repo
            print "Cloning template files..."
            repo_local_copy = utils.clone_git_repo(cls.git_template_url)
            print "Rendering files from templates..."
            target_path = os.getcwd()
            settings_dir = '/'.join(site['django_settings'].split('.')[:-1])
            site['project_name'] = settings_dir.replace('/', '.')
            settings_dir_path = target_path
            if settings_dir:
                settings_dir_path +=  '/' + settings_dir
            utils.render_from_repo(repo_local_copy, target_path, site, settings_dir_path)
        else:
            cls._create_configs(site)
        print cls.setup_instructions
        # TODO: execute after_deploy
        run_hooks('init_after')

    @classmethod
    def deploy(cls):
        run_hooks('deploy_before')
        run_hooks('deploy')
        run_hooks('deploy_after')

    @classmethod
    def delete(cls):
        raise NotImplementedError()

    @classmethod
    def _create_configs(cls, site):
        """
        This is going to generate the following configuration:
        * wsgi.py
        * <provider>.yml
        * settings_<provider>.py
        """
        provider = cls.name

        cls._render_config('wsgi.py', 'wsgi.py', site)

        # create yaml file
        yaml_template_name = os.path.join(provider, cls.provider_yml_name)
        cls._render_config(cls.provider_yml_name, yaml_template_name, site)

        # create requirements file
        # don't do anything if the requirements file is called requirements.txt and in the root of the project
        requirements_filename = "requirements.txt"
        if site['requirements'] != requirements_filename:   # providers expect the file to be called requirements.txt
            requirements_template_name = os.path.join(provider, requirements_filename)
            cls._render_config(requirements_filename, requirements_template_name, site)

        # create settings file
        settings_template_name = os.path.join(provider, 'settings_%s.py' % provider)
        settings_path = site['django_settings'].replace('.', '/') + '_%s.py' % provider
        cls._render_config(settings_path, settings_template_name, site)

    @classmethod
    def _render_config(cls, dest, template_name, template_args):
        """
        Renders and writes a template_name to a dest given some template_args.

        This is for platform-specific configurations
        """
        template_args = template_args.copy()

        # Substitute values here
        pyversion = template_args['pyversion']
        template_args['pyversion'] = cls.PYVERSIONS[pyversion]

        template = template_env.get_template(template_name)
        contents = template.render(**template_args)
        _write_file(dest, contents)


class Stackato(PaaSProvider):
    """
    ActiveState Stackato PaaSProvider.
    """
    name = "stackato"

    PYVERSIONS = {
        "Python2.7": "python27",
        "Python3.2": "python32",
    }

    setup_instructions = """
Just a few more steps before you're ready to deploy your app!

1. Go to http://www.activestate.com/stackato/download_client to download
   the Stackato client, and then add the executable somewhere in your PATH.
   If you're not sure where to place it, you can simply drop it in your
   project's root directory (the same directory as the fabfile.py created
   by django-deployer).

2. Once you've done that, target the stackato api with:

       $ stackato target api.stacka.to

   and then login. You can find your sandbox password at
   https://account.activestate.com, which you'll need when
   using the command:

       $ stackato login --email <email>

3. You can push your app the first time with:

       $ stackato push -n

   and make subsequent updates with:

       $ stackato update

"""

    provider_yml_name = "stackato.yml"

    def init():
        pass

    def deploy():
        pass

    def delete():
        pass


class DotCloud(PaaSProvider):
    """
    Dotcloud PaaSProvider.
    """

    name = "dotcloud"

    PYVERSIONS = {
        "Python2.6": "v2.6",
        "Python2.7": "v2.7",
        "Python3.2": "v3.2",
    }

    setup_instructions = """
        Just a few more steps before you're ready to deploy your app!

        1. Install the dotcloud command line tool with:

                $ pip install dotcloud

        2. Once you've done that, setup your Dotcloud environment for the first time:

                $ dotcloud setup
                dotCloud username or email: appsembler
                Password:
                ==> dotCloud authentication is complete! You are recommended to run `dotcloud check` now.

                $ dotcloud check
                ==> Checking the authentication status
                ==> Client is authenticated as appsembler

        3. You can create the app with:

               $ dotcloud create myapp

           and deploy it with:

               $ dotcloud push

        """

    provider_yml_name = "dotcloud.yml"

    @classmethod
    def init(cls, site):
        super(DotCloud, cls).init(site)

        # config_list: files to put in project folder, django_config_list: files to put in django project folder
        config_list = [
            'createdb.py',
            'mkadmin.py',
            'nginx.conf',
            'postinstall',
            'wsgi.py',
        ]

        # for rendering configs under root
        get_config = lambda filename: cls._render_config(filename, os.path.join(cls.name, filename), site)
        map(get_config, config_list)

    def deploy():
        pass

    def delete():
        pass


class AppEngine(PaaSProvider):
    """
    AppEngine PaaSProvider
    """

    name = 'appengine'

    PYVERSIONS = {
        "Python2.7": "v2.7"
    }

    setup_instructions = """
Just a few more steps before you're ready to deploy your app!

1. Run this command to create the virtualenv with all the packages and deploy:

        $ fab -f fabfile_deployer.py deploy

2. Create and sync the db on the Cloud SQL:

        $ sh manage.sh cloudcreatedb
        $ sh manage.sh cloudsyncdb

3. Everything is set up now, you can run other commands that will execute on your remotely deployed app, such as:

        $ sh manage.sh dbshell

"""

    provider_yml_name = "app.yaml"

    # switch to the git repo
    git_template = True
    git_template_url = "git@github.com:littleq0903/django-deployer-template-appengine.git"

    @classmethod
    def init(cls, site):
        super(AppEngine, cls).init(site)


    def delete():
        pass

class OpenShift(PaaSProvider):
    """
    OpenShift PaaSProvider
    """
    name = 'openshift'

    PYVERSIONS = {
        "Python2.6": "v2.6"
        }

    setup_instructions = ""
    git_template = True
    git_template_url = "git@github.com:littleq0903/django-deployer-template-openshift-experiment.git"

    @classmethod
    def init(cls, site):
        super(OpenShift, cls).init(site)

        #set git url to rhc

        # the first time deployment need to do "git push rhc --force"



PROVIDERS = {
    'stackato': Stackato,
    'dotcloud': DotCloud,
    'openshift': OpenShift,
    'appengine': AppEngine
}

########NEW FILE########
__FILENAME__ = tasks
import os
import yaml

from fabric.api import prompt

from django_deployer.helpers import (
    DEPLOY_YAML,
    _create_deploy_yaml,
    _validate_django_settings,
    _validate_project_name,
    _validate_managepy,
    _validate_requirements,
    _validate_admin_password,
    _validate_providers,
    _read_file,
    _green,
    _yellow,
    _red,
)

from .providers import PROVIDERS


def init(provider=None):
    """
    Runs through a questionnaire to set up your project's deploy settings
    """
    if os.path.exists(DEPLOY_YAML):
        _yellow("\nIt looks like you've already gone through the questionnaire.")
        cont = prompt("Do you want to go through it again and overwrite the current one?", default="No")

        if cont.strip().lower() == "no":
            return None
    _green("\nWelcome to the django-deployer!")
    _green("\nWe need to ask a few questions in order to set up your project to be deployed to a PaaS provider.")

    # TODO: identify the project dir based on where we find the settings.py or urls.py

    django_settings = prompt(
        "* What is your Django settings module?",
        default="settings",
        validate=_validate_django_settings
    )

    managepy = prompt(
        "* Where is your manage.py file?",
        default="./manage.py",
        validate=_validate_managepy
    )

    requirements = prompt(
        "* Where is your requirements.txt file?",
        default="requirements.txt",
        validate=_validate_requirements
    )
    # TODO: confirm that the file exists
    # parse the requirements file and warn the user about best practices:
    #   Django==1.4.1
    #   psycopg2 if they selected PostgreSQL
    #   MySQL-python if they selected MySQL
    #   South for database migrations
    #   dj-database-url

    pyversion = prompt("* What version of Python does your app need?", default="Python2.7")

    # TODO: get these values by reading the settings.py file
    static_url = prompt("* What is your STATIC_URL?", default="/static/")
    media_url = prompt("* What is your MEDIA_URL?", default="/media/")

    if not provider:
        provider = prompt("* Which provider would you like to deploy to (dotcloud, appengine, stackato, openshift)?",
                          validate=_validate_providers)

    # Where to place the provider specific questions
    site = {}
    additional_site = {}

    if provider == "appengine":
        applicationid = prompt("* What's your Google App Engine application ID (see https://appengine.google.com/)?", validate=r'.+')
        instancename = prompt("* What's the full instance ID of your Cloud SQL instance\n"
                              "(should be in format \"projectid:instanceid\" found at https://code.google.com/apis/console/)?", validate=r'.+:.+')
        databasename = prompt("* What's your database name?", validate=r'.+')
        sdk_location = prompt("* Where is your Google App Engine SDK location?",
                              default="/usr/local/google_appengine",
                              validate=r'.+'  # TODO: validate that this path exists
                              )

        additional_site.update({
            # quotes for the yaml issue
            'application_id': applicationid,
            'instancename': instancename,
            'databasename': databasename,
            'sdk_location': sdk_location,
        })

        # only option with Google App Engine is MySQL, so we'll just hardcode it
        site = {
            'database': 'MySQL'
        }

    elif provider == "openshift":
        application_name = prompt("* What is your openshift application name?")

        site = {
            'application_name': application_name
        }

    else:
        database = prompt("* What database does your app use?", default="PostgreSQL")
        site = {
            'database': database,
        }

    # TODO: add some validation that the admin password is valid
    # TODO: let the user choose the admin username instead of hardcoding it to 'admin'
    admin_password = prompt("* What do you want to set as the admin password?",
                            validate=_validate_admin_password
                            )

    import random
    SECRET_KEY = ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    SECRET_KEY = "'" + SECRET_KEY + "'"

    site.update({
        'pyversion': pyversion,
        'django_settings': django_settings,
        'managepy': managepy,
        'requirements': requirements,
        'static_url': static_url,
        'media_url': media_url,
        'provider': provider,
        'admin_password': admin_password,
        'secret_key': SECRET_KEY,
    })

    site.update(additional_site)

    _create_deploy_yaml(site)

    return site


def setup(provider=None):
    """
    Creates the provider config files needed to deploy your project
    """
    site = init(provider)
    if not site:
        site = yaml.safe_load(_read_file(DEPLOY_YAML))

    provider_class = PROVIDERS[site['provider']]
    provider_class.init(site)


def deploy(provider=None):
    """
    Deploys your project
    """
    if os.path.exists(DEPLOY_YAML):
        site = yaml.safe_load(_read_file(DEPLOY_YAML))

    provider_class = PROVIDERS[site['provider']]
    provider_class.deploy()

########NEW FILE########
__FILENAME__ = utils
import git
import uuid
import os
from jinja2 import Template

def clone_git_repo(repo_url):
    """
    input: repo_url
    output: path of the cloned repository
    steps:
        1. clone the repo
        2. parse 'site' into for templating

    assumptions:
        repo_url = "git@github.com:littleq0903/django-deployer-template-openshift-experiment.git"
        repo_local_location = "/tmp/djangodeployer-cache-xxxx" # xxxx here will be some short uuid for identify different downloads
    """
    REPO_PREFIX = "djangodeployer-cache-"
    REPO_POSTFIX_UUID = str(uuid.uuid4()).split('-')[-1]
    REPO_CACHE_NAME = REPO_PREFIX + REPO_POSTFIX_UUID
    REPO_CACHE_LOCATION = '/tmp/%s' % REPO_CACHE_NAME

    repo = git.Repo.clone_from(repo_url, REPO_CACHE_LOCATION)
    return REPO_CACHE_LOCATION

def get_template_filelist(repo_path, ignore_files=[], ignore_folders=[]):
    """
    input: local repo path
    output: path list of files which need to be rendered
    """

    default_ignore_files = ['.gitignore']
    default_ignore_folders = ['.git']

    ignore_files += default_ignore_files
    ignore_folders += default_ignore_folders

    filelist = []

    for root, folders, files in os.walk(repo_path):
        for ignore_file in ignore_files:
            if ignore_file in files:
                files.remove(ignore_file)

        for ignore_folder in ignore_folders:
            if ignore_folder in folders:
                folders.remove(ignore_folder)

        for file_name in files:
            filelist.append( '%s/%s' % (root, file_name))

    return filelist


def render_from_repo(repo_path, to_path, template_params, settings_dir):
    """
    rendering all files into the target directory
    """
    TEMPLATE_PROJECT_FOLDER_PLACEHOLDER_NAME = 'deployer_project'

    repo_path = repo_path.rstrip('/')
    to_path = to_path.rstrip('/')
    files_to_render = get_template_filelist(repo_path, ignore_folders=[TEMPLATE_PROJECT_FOLDER_PLACEHOLDER_NAME])


    # rendering generic deploy files
    for single_file_path in files_to_render:
        source_file_path = single_file_path
        dest_file_path = source_file_path.replace(repo_path, to_path)

        render_from_single_file(source_file_path, dest_file_path, template_params)

    settings_template_dir = os.path.join(repo_path, TEMPLATE_PROJECT_FOLDER_PLACEHOLDER_NAME)
    settings_files = get_template_filelist(settings_template_dir)

    # rendering settings file
    for single_file_path in settings_files:
        source = single_file_path
        dest = single_file_path.replace(settings_template_dir, settings_dir)
        render_from_single_file(source, dest, template_params)



def render_from_single_file(file_path, dest_file_path, template_params):

    dest_dirname = os.path.dirname(dest_file_path)

    if not os.path.exists(dest_dirname):
        os.makedirs(dest_dirname)

    with open(file_path) as source_file_p:
        template = Template(source_file_p.read())
        rendered_content = template.render(**template_params)

    with open(dest_file_path, 'w') as dest_file_p:
        dest_file_p.write(rendered_content)



########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-deployer documentation build configuration file, created by
# sphinx-quickstart on Mon Mar 18 10:06:23 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

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
project = u'django-deployer'
copyright = u'2013, Nate Aune'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

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
exclude_patterns = ['_build']

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
htmlhelp_basename = 'django-deployerdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-deployer.tex', u'django-deployer Documentation',
   u'Nate Aune', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-deployer', u'django-deployer Documentation',
     [u'Nate Aune'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-deployer', u'django-deployer Documentation',
   u'Nate Aune', 'django-deployer', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
