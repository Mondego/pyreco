__FILENAME__ = herokuapp_startproject
import sys, os, stat, os.path, getpass, subprocess, argparse

from django.core import management


parser = argparse.ArgumentParser(
    description = "Start a new herokuapp Django project.",
)
parser.add_argument("project_name",
    help = "The name of the project to create.",
)
parser.add_argument("dest_dir",
    default = ".",
    nargs = "?",
    help = "The destination dir for the created project.",
)
parser.add_argument("-a", "--app",
    default = None,
    dest = "app",
    required = False,
    help = "The name of the Heroku app. Defaults to the project name, with underscores replaced by hyphens.",
)
parser.add_argument("--noinput", 
    action = "store_false",
    default = True,
    dest = "interactive",
    help = "Tells Django to NOT prompt the user for input of any kind.",
)


def make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main():
    args = parser.parse_args()
    # Generate Heroku app name.
    app_name = args.app or args.project_name.replace("_", "-")
    # Create the project.
    try:
        os.makedirs(args.dest_dir)
    except OSError:
        pass
    management.call_command("startproject",
        args.project_name,
        args.dest_dir,
        template = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "project_template")),
        extensions = ("py", "txt", "slugignore", "conf", "gitignore", "sh",),
        app_name = app_name,
        user = getpass.getuser(),
    )
    # Make management scripts executable.
    make_executable(os.path.join(args.dest_dir, "manage.py"))
    make_executable(os.path.join(args.dest_dir, "deploy.sh"))
    # Audit and configure the project for Heroku.
    audit_args = ["python", os.path.join(args.dest_dir, "manage.py"), "heroku_audit", "--fix"]
    if not args.interactive:
        audit_args.append("--noinput")
    audit_returncode = subprocess.call(audit_args)
    if audit_returncode != 0:
        sys.exit(audit_returncode)
    # Give some help to the user.
    print "Heroku project created."
    print "Deploy to Heroku with `./deploy.sh`"

########NEW FILE########
__FILENAME__ = commands
import re, os
from collections import Counter
from functools import partial

import sh

from django.core.management import CommandError
from django.utils.encoding import force_text


RE_PS = re.compile("^(\w+)\.")

RE_POSTGRES = re.compile("^HEROKU_POSTGRESQL_\w+?_URL$")


def parse_shell(lines):
    return dict(
        line.strip().split("=", 1)
        for line
        in lines.split()
    )


def format_command(prefix, args, kwargs):
    return u"COMMAND: {prefix} {args} {kwargs}".format(
        prefix = prefix,
        args = u" ".join(map(force_text, args)),
        kwargs = u" ".join(
            u"--{key}={value}".format(
                key = key.replace("_", "-"),
                value = value,
            )
            for key, value
            in kwargs.items()
        )
    )


class HerokuCommandError(CommandError):

    pass


class HerokuCommand(object):

    def __init__(self, app, cwd, stdout=None, stderr=None, dry_run=False):
        # Store the dry run state.
        self.dry_run = dry_run
        self._stdout = stdout
        # Check that the heroku command is available.
        if hasattr(sh, "heroku"):
            heroku_command = sh.heroku
        else:
            raise HerokuCommandError("Heroku toolbelt is not installed. Install from https://toolbelt.heroku.com/")
        # Create the Heroku command wrapper.
        self._heroku = partial(heroku_command,
            _cwd = cwd,
            _out = stdout,
            _err = stderr,
        )  # Not using bake(), as it gets the command order wrong.
        if app:
            self._heroku = partial(self._heroku, app=app)
        # Ensure that the user is logged in.
        def auth_token_interact(line, stdin, process):
            if line == "\n":
                stdin.put("\n")
        try:
            self("auth:token", _force_live_run=True, _in=None, _tty_in=True, _out=auth_token_interact, _out_bufsize=0).wait()
        except sh.ErrorReturnCode:
            raise HerokuCommandError("Please log in to the Heroku Toolbelt using `heroku auth:login`.")

    def __call__(self, *args, **kwargs):
        # Allow dry run to be overridden for selective (non-mutating) commands.
        force_live_run = kwargs.pop("_force_live_run", False)
        # Run the command.
        if self.dry_run and not force_live_run:
            # Allow a dry run to be processed.
            self._stdout.write(format_command("heroku", args, kwargs) + "\n")
        else:
            # Call a live command.
            try:
                return self._heroku(*args, **kwargs)
            except sh.ErrorReturnCode as ex:
                raise HerokuCommandError(str(ex))

    def config_set(self, **kwargs):
        return self("config:set", *[
            "{key}={value}".format(
                key = key,
                value = value,
            )
            for key, value
            in kwargs.items()
        ], _out=None)

    def config_get(self, name=None):
        if name:
            return str(self("config:get", name, _out=None, _force_live_run=True)).strip()
        return parse_shell(self("config", shell=True, _out=None))

    def ps(self):
        counter = Counter()
        for line in self("ps", _out=None, _iter=True, _force_live_run=True):
            match = RE_PS.match(line)
            if match:
                process_name = match.group(1)
                if process_name not in ("run"):
                    counter[process_name] += 1
        return counter

    def scale(self, **kwargs):
        return self("ps:scale", *[
            "{name}={count}".format(
                name = name,
                count = count,
            )
            for name, count
            in kwargs.items()
        ])

    def postgres_url(self):
        for line in self("config", shell=True, _out=None, _force_live_run=True):
            key = line.split("=", 1)[0]
            if RE_POSTGRES.match(key):
                return key

########NEW FILE########
__FILENAME__ = env
import os, os.path

from herokuapp.commands import HerokuCommand, HerokuCommandError


def load_env(entrypoint, app=None):
    try:
        heroku = HerokuCommand(
            app = app,
            cwd = os.path.dirname(entrypoint),
        )
        heroku_config = heroku.config_get()
    except HerokuCommandError:
        pass
    else:
        for key, value in heroku_config.items():
            os.environ.setdefault(key, value)

########NEW FILE########
__FILENAME__ = introspection
from django.db.models import get_models
from django.db import connections, transaction
from django.db.utils import DatabaseError

from south import migration
from south.models import MigrationHistory


def model_installed(connection, tables, model):
    """
    Returns whether the model has been stored in the given
    db connection.

    Shamelessly stolen from the django syncdb management command.
    """
    opts = model._meta
    converter = connection.introspection.table_name_converter
    return ((converter(opts.db_table) in tables) or
        (opts.auto_created and converter(opts.auto_created._meta.db_table) in tables))


def has_pending_syncdb():
    """
    Returns whether any models need to be created via python manage.py syncdb.

    This will be the case if any of the models tables are not present
    in any of the database connections.
    """
    db_tables = dict(
        (connections[alias], frozenset(connections[alias].introspection.table_names()))
        for alias
        in connections
    )
    # Determine if any models have not been synced.
    for model in get_models(include_auto_created=True):
        if not any(
            model_installed(connection, tables, model)
            for connection, tables
            in db_tables.items()
        ):
            return True
    # No pending syncdb.
    return False


def has_pending_migrations():
    """
    Returns whether any models need to be migrated via python manage.py migrate.

    This will be the case if any migrations are present in apps, but not
    in the database.

    Shamelessly stolen from http://stackoverflow.com/questions/7089969/programmatically-check-whether-there-are-django-south-migrations-that-need-to-be
    """
    apps  = list(migration.all_migrations())
    try:
        applied_migrations = list(MigrationHistory.objects.filter(app_name__in=[app.app_label() for app in apps]))
    except DatabaseError:
        transaction.rollback_unless_managed()
        return True  # The table has not been created yet.
    applied_migrations = ['%s.%s' % (mi.app_name,mi.migration) for mi in applied_migrations]
    for app in apps:
        for app_migration in app:
            if app_migration.app_label() + "." + app_migration.name() not in applied_migrations:
                return True
    # No pending migrations.
    return False

########NEW FILE########
__FILENAME__ = base
from __future__ import absolute_import

from optparse import make_option

from django.utils.functional import cached_property
from django.conf import settings
from django.core.management import call_command

from herokuapp.commands import HerokuCommand, format_command
from herokuapp.settings import HEROKU_APP_NAME


class HerokuCommandMixin(object):
    
    option_list = (
        make_option("-a",  "--app",
            default = HEROKU_APP_NAME,
            dest = "app",
            help = "The name of the Heroku app to use. Defaults to HEROKU_APP_NAME.",
        ),
        make_option("--dry-run",
            action = "store_true",
            default = False,
            dest = "dry_run",
            help = "Outputs the heroku and django managment commands that will be run, but doesn't execute them.",
        ),
    )
    
    def call_command(self, *args, **kwargs):
        """
        Calls the given management command, but only if it's not a dry run.

        If it's a dry run, then a notice about the command will be printed.
        """
        if self.dry_run:
            self.stdout.write(format_command("python manage.py", args, kwargs))
        else:
            call_command(*args, **kwargs)

    @cached_property
    def heroku(self):
        return HerokuCommand(
            app = self.app,
            cwd = settings.BASE_DIR,
            stdout = self.stdout._out,
            stderr = self.stderr._out,
            dry_run = self.dry_run,
        )

########NEW FILE########
__FILENAME__ = heroku_audit
from __future__ import absolute_import

import os, os.path, sys
from optparse import make_option

import sh

from django.conf import settings
from django.core.management.base import NoArgsCommand, BaseCommand
from django.utils.crypto import get_random_string
from django.core.files.storage import default_storage

from storages.backends.s3boto import S3BotoStorage

from herokuapp.commands import HerokuCommandError
from herokuapp.management.commands.base import HerokuCommandMixin


class Command(HerokuCommandMixin, NoArgsCommand):
    
    help = "Tests this app for common Heroku deployment issues."
    
    option_list = BaseCommand.option_list + (
        make_option("--noinput",
            action = "store_false",
            default = True,
            dest = "interactive",
            help = "Tells Django to NOT prompt the user for input of any kind.",
        ),
        make_option("--fix",
            action = "store_true",
            default = False,
            dest = "fix",
            help = "If specified, then the user will be prompted to fix problems as they are found. Combine with --noinput to auto-fix problems.",
        ),
    ) + HerokuCommandMixin.option_list
    
    def exit_with_error(self, error):
        self.stderr.write(error)
        self.stderr.write("Heroku audit aborted.")
        self.stderr.write("Run `python manage.py heroku_audit --fix` to fix problems.")
        sys.exit(1)

    def prompt_for_fix(self, error, message):
        if self.fix:
            self.stdout.write(error)
            if self.interactive:
                # Ask to fix the issue.
                answer = ""
                while not answer in ("y", "n"):
                    answer = raw_input("{message} (y/n) > ".format(
                        message = message,
                    )).lower().strip()
                answer_bool = answer == "y"
            else:
                # Attempt to auto-fix the issue.
                answer_bool = True
        else:
            answer_bool = False
        # Exit if no fix provided.
        if not answer_bool:
            self.exit_with_error(error)

    def read_string(self, message, default):
        if self.interactive:
            answer = ""
            while not answer:
                answer = raw_input("{message} {default}> ".format(
                    message = message,
                    default = "({default}) ".format(
                        default = default,
                    ) if default else ""
                )).strip() or default
            return answer
        else:
            return default

    def handle(self, **kwargs):
        self.app = kwargs["app"]
        self.dry_run = kwargs["dry_run"]
        self.interactive = kwargs["interactive"]
        self.fix = kwargs["fix"]
        # Check app exists.
        try:
            self.heroku("apps:info")
        except HerokuCommandError:
            self.prompt_for_fix("No Heroku app named '{app}' detected.".format(app=self.app), "Create app?")
            self.heroku("apps:create", self.app)
            self.stdout.write("Heroku app created.")
        # Check that Amazon S3 is being used for media.
        default_storage._setup()
        if not isinstance(default_storage._wrapped, S3BotoStorage):
            self.exit_with_error("settings.DEFAULT_FILE_STORAGE should be set to a subclass of `storages.backends.s3boto.S3BotoStorage`.")
        # Check for AWS access details.
        if not self.heroku.config_get("AWS_ACCESS_KEY_ID"):
            self.prompt_for_fix("Amazon S3 access details not present in Heroku config.", "Setup now?")
            aws_env = {}
            aws_env["AWS_ACCESS_KEY_ID"] = self.read_string("AWS access key", os.environ.get("AWS_ACCESS_KEY_ID"))
            aws_env["AWS_SECRET_ACCESS_KEY"] = self.read_string("AWS access secret", os.environ.get("AWS_SECRET_ACCESS_KEY"))
            aws_env["AWS_STORAGE_BUCKET_NAME"] = self.read_string("S3 bucket name", self.app)
            # Save Heroku config.
            self.heroku.config_set(**aws_env)
            self.stdout.write("Amazon S3 config written to Heroku config.")
        # Check for SendGrid settings.
        if settings.EMAIL_HOST == "smtp.sendgrid.net" and not self.heroku.config_get("SENDGRID_USERNAME"):
            self.prompt_for_fix("SendGrid addon not installed.", "Provision SendGrid starter addon (free)?")
            self.heroku("addons:add", "sendgrid:starter")
            self.stdout.write("SendGrid addon provisioned.")
        # Check for promoted database URL.
        if not self.heroku.config_get("DATABASE_URL"):
            database_url = self.heroku.postgres_url()
            if not database_url:
                self.prompt_for_fix("Database URL not present in Heroku config.", "Provision Heroku Postgres dev addon (free)?")
                self.heroku("addons:add", "heroku-postgresql")
                self.heroku("pg:wait")
                self.stdout.write("Heroku Postgres addon provisioned.")
                # Load the new database URL.
                database_url = self.heroku.postgres_url()
            # Promote the database URL.
            self.prompt_for_fix("No primary database URL set.", "Promote {database_url}?".format(database_url=database_url))
            self.heroku("pg:promote", database_url)
            self.stdout.write("Heroku primary database URL set.")
        # Check for secret key.
        heroku_secret_key = self.heroku.config_get("SECRET_KEY")
        if not heroku_secret_key:
            self.prompt_for_fix("Secret key not set in Heroku config.", "Generate now?")
            self.heroku.config_set(SECRET_KEY=get_random_string(50, "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"))
            self.stdout.write("Secret key written to Heroku config. Ensure your settings file is configured to read the secret key: https://github.com/etianen/django-herokuapp#improving-site-security")
        # Check for Python hash seed.
        if not self.heroku.config_get("PYTHONHASHSEED"):
            self.prompt_for_fix("Python hash seed not set in Heroku config.", "Set now?")
            self.heroku.config_set(PYTHONHASHSEED="random")
            self.stdout.write("Python hash seed written to Heroku config.")
        # Check for SSL header settings.
        if not getattr(settings, "SECURE_PROXY_SSL_HEADER", None) == ("HTTP_X_FORWARDED_PROTO", "https"):
            self.exit_with_error("Missing SECURE_PROXY_SSL_HEADER settings. Please add `SECURE_PROXY_SSL_HEADER = (\"HTTP_X_FORWARDED_PROTO\", \"https\")` to your settings.py file.")
        # Check for Procfile.
        procfile_path = os.path.join(settings.BASE_DIR, "Procfile")
        if not os.path.exists(procfile_path):
            self.prompt_for_fix("Procfile must to be created to deploy to Heroku.", "Create now?")
            with open(procfile_path, "wb") as procfile_handle:
                procfile_handle.write("web: waitress-serve --port=$PORT {project_name}.wsgi:application\n".format(
                    project_name = os.environ["DJANGO_SETTINGS_MODULE"].split(".", 1)[0],
                ))
            self.stdout.write("Default Procfile generated.")
        # Check for requirements.txt.
        requirements_path = os.path.join(settings.BASE_DIR, "requirements.txt")
        if not os.path.exists(requirements_path):
            self.prompt_for_fix("A requirements.txt file must be created to deploy to Heroku.", "Generate now?")
            sh.pip.freeze(_out=requirements_path)
            self.stdout.write("Dependencies frozen to requirements.txt.")

########NEW FILE########
__FILENAME__ = heroku_deploy
from __future__ import absolute_import

from itertools import repeat
from optparse import make_option

from django.core.management.base import NoArgsCommand, BaseCommand

from herokuapp.management.commands.base import HerokuCommandMixin
from herokuapp.introspection import has_pending_syncdb, has_pending_migrations
from herokuapp import settings


class Command(HerokuCommandMixin, NoArgsCommand):
    
    help = "Deploys this app to the Heroku platform."
    
    option_list = BaseCommand.option_list + (
        make_option("-S", "--no-staticfiles",
            action = "store_false",
            default = True,
            dest = "deploy_staticfiles",
            help = "If specified, then deploying static files will be skipped.",
        ),
        make_option("-A", "--no-app",
            action = "store_false",
            default = True,
            dest = "deploy_app",
            help = "If specified, then pushing the latest version of the app will be skipped.",
        ),
        make_option("-D", "--no-db",
            action = "store_false",
            default = True,
            dest = "deploy_database",
            help = "If specified, then running database migrations will be skipped.",
        ),
        make_option("--force-db",
            action = "store_true",
            default = False,
            dest = "force_database",
            help = "If specified, then database migrations will be run, even if django-herokuapp doesn't think they need running.",
        ),
    ) + HerokuCommandMixin.option_list

    def handle(self, **kwargs):
        self.app = kwargs["app"]
        self.dry_run = kwargs["dry_run"]
        # Do we need to syncdb?
        requires_syncdb = kwargs["force_database"] or has_pending_syncdb()
        requires_migrate = kwargs["force_database"] or has_pending_migrations()
        deploy_database = (requires_syncdb or requires_migrate) and kwargs["deploy_database"]
        # Build app code.
        if kwargs["deploy_app"]:
            self.stdout.write("Building app...")
            # Install the anvil plugin.
            self.heroku("plugins:install", "https://github.com/ddollar/heroku-anvil")
            # Build the slug.
            heroku_build_kwargs = {
                "pipeline": True,
                "_out": None,
            }
            if settings.HEROKU_BUILDPACK_URL:
                heroku_build_kwargs["buildpack"] = settings.HEROKU_BUILDPACK_URL
            app_slug = self.heroku("build", **heroku_build_kwargs)
        # Deploy static asssets.
        if kwargs["deploy_staticfiles"]:
            self.stdout.write("Deploying static files...")
            self.call_command("collectstatic", interactive=False)
        # Store a snapshot of the running processes.
        heroku_ps = self.heroku.ps()
        # Enter maintenance mode, if required.
        if deploy_database:
            self.heroku("maintenance:on")
            # Turn off all dynos.
            if heroku_ps:
                self.heroku.scale(**dict(zip(heroku_ps.keys(), repeat(0))))
        # Deploy app code.
        if kwargs["deploy_app"]:
            self.stdout.write("Deploying latest version of app to Heroku...")
            # Deploy app.
            self.heroku("release", app_slug)
        # Deploy migrations.
        if deploy_database:
            self.stdout.write("Deploying database...")
            if requires_syncdb:
                self.call_command("syncdb", interactive=False)
            if requires_migrate:
                self.call_command("migrate", interactive=False)
        # Restart the app if required.
        if kwargs["deploy_staticfiles"] and not (kwargs["deploy_app"] or deploy_database):
            self.heroku("restart")
        # Prepare to scale the app back to the original state.
        if deploy_database or not heroku_ps:
            # Ensure at least one web dyno will be started.
            heroku_ps.setdefault("web", 1)
            # Restore running dyno state.
            self.heroku.scale(**heroku_ps)
        # Exit maintenance mode, if required.
        if deploy_database:
            # Disable maintenance mode.
            self.heroku("maintenance:off")

########NEW FILE########
__FILENAME__ = middleware
from django.shortcuts import redirect
from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings

from herokuapp.settings import SITE_DOMAIN


class CanonicalDomainMiddleware(object):
    
    """Middleware that redirects to a canonical domain."""
    
    def __init__(self):
        if settings.DEBUG or not SITE_DOMAIN:
            raise MiddlewareNotUsed
    
    def process_request(self, request):
        """If the request domain is not the canonical domain, redirect."""
        hostname = request.get_host().split(":", 1)[0]
        # Don't perform redirection for testing or local development.
        if hostname in ("testserver", "localhost", "127.0.0.1"):
            return
        # Check against the site domain.
        canonical_hostname = SITE_DOMAIN.split(":", 1)[0]
        if hostname != canonical_hostname:
            if request.is_secure():
                canonical_url = "https://"
            else:
                canonical_url = "http://"
            canonical_url += SITE_DOMAIN + request.get_full_path()
            return redirect(canonical_url, permanent=True)
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    
    # Load the Heroku environment.
    from herokuapp.env import load_env
    load_env(__file__, "{{ app_name }}")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = local
"""
Settings for local development.

These settings are not fast or efficient, but allow local servers to be run
using the django-admin.py utility.

This file should be excluded from version control to keep the settings local.
"""

import os.path

from production import BASE_DIR


# Run in debug mode.

DEBUG = True

TEMPLATE_DEBUG = DEBUG


# Serve staticfiles locally for development.

STATICFILES_STORAGE = "require.storage.OptimizedCachedStaticFilesStorage"

STATIC_URL = "/static/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")


# Use local server.

SITE_DOMAIN = "localhost:8000"

PREPEND_WWW = False

ALLOWED_HOSTS = ("*",)


# Disable the template cache for development.

TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
)


# Local database settings. These should work well with http://postgresapp.com/.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": "localhost",
        "NAME": "{{ project_name }}",
        "USER": "{{ user }}",
        "PASSWORD": "",
    },
}

########NEW FILE########
__FILENAME__ = production
"""
Django settings for bar project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

import os
import dj_database_url
from django.utils.crypto import get_random_string


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BASE_DIR = os.path.abspath(os.path.join(SITE_ROOT, ".."))


# Heroku platform settings.

HEROKU_APP_NAME = "{{ app_name }}"

HEROKU_BUILDPACK_URL = "https://github.com/heroku/heroku-buildpack-python.git"


# The name and domain of this site.

SITE_NAME = "Example"

SITE_DOMAIN = "{{ app_name }}.herokuapp.com"

PREPEND_WWW = False


# Security settings.

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ALLOWED_HOSTS = (
    SITE_DOMAIN,
    "{HEROKU_APP_NAME}.herokuapp.com".format(
        HEROKU_APP_NAME = HEROKU_APP_NAME,
    ),
)


# Database settings.

DATABASES = {
    "default": dj_database_url.config(default="postgresql://"),
}


# Use Amazon S3 for storage for uploaded media files.

DEFAULT_FILE_STORAGE = "storages.backends.s3boto.S3BotoStorage"


# Use Amazon S3 and RequireJS for static files storage.

STATICFILES_STORAGE = "require_s3.storage.OptimizedCachedStaticFilesStorage"


# Amazon S3 settings.

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")

AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")

AWS_AUTO_CREATE_BUCKET = True

AWS_HEADERS = {
    "Cache-Control": "public, max-age=86400",
}

AWS_S3_FILE_OVERWRITE = False

AWS_QUERYSTRING_AUTH = False

AWS_S3_SECURE_URLS = True

AWS_REDUCED_REDUNDANCY = False

AWS_IS_GZIPPED = False

STATIC_URL = "https://{bucket_name}.s3.amazonaws.com/".format(
    bucket_name = AWS_STORAGE_BUCKET_NAME,
)


# Email settings.

EMAIL_HOST = "smtp.sendgrid.net"

EMAIL_HOST_USER = os.environ.get("SENDGRID_USERNAME")

EMAIL_HOST_PASSWORD = os.environ.get("SENDGRID_PASSWORD")

EMAIL_PORT = 25

EMAIL_USE_TLS = False

SERVER_EMAIL = u"{name} <notifications@{domain}>".format(
    name = SITE_NAME,
    domain = SITE_DOMAIN,
)

DEFAULT_FROM_EMAIL = SERVER_EMAIL

EMAIL_SUBJECT_PREFIX = "[%s] " % SITE_NAME


# Error reporting settings.  Use these to set up automatic error notifications.

ADMINS = ()

MANAGERS = ()

SEND_BROKEN_LINK_EMAILS = False


# Locale settings.

TIME_ZONE = "UTC"

LANGUAGE_CODE = "en-gb"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# A list of additional installed applications.

INSTALLED_APPS = (
    "django.contrib.sessions",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "south",
    "herokuapp",
)


# Additional static file locations.

STATICFILES_DIRS = (
    os.path.join(SITE_ROOT, "static"),
)


# Dispatch settings.

MIDDLEWARE_CLASSES = (
    "django.middleware.gzip.GZipMiddleware",
    "herokuapp.middleware.CanonicalDomainMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

ROOT_URLCONF = "{{ project_name }}.urls"

WSGI_APPLICATION = "{{ project_name }}.wsgi.application"

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

SITE_ID = 1


# Absolute path to the directory where templates are stored.

TEMPLATE_DIRS = (
    os.path.join(SITE_ROOT, "templates"),
)

TEMPLATE_LOADERS = (
    ("django.template.loaders.cached.Loader", (
        "django.template.loaders.filesystem.Loader",
        "django.template.loaders.app_directories.Loader",
    )),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
#    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
)


# Namespace for cache keys, if using a process-shared cache.

CACHE_MIDDLEWARE_KEY_PREFIX = "{{ project_name }}"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    # Long cache timeout for staticfiles, since this is used heavily by the optimizing storage.
    "staticfiles": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": 60 * 60 * 24 * 365,
        "LOCATION": "staticfiles",
    },
}


# A secret key used for cryptographic algorithms.

SECRET_KEY = os.environ.get("SECRET_KEY", get_random_string(50, "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"))


# Logging configuration.

LOGGING = {
    "version": 1,
    # Don't throw away default loggers.
    "disable_existing_loggers": False,
    "handlers": {
        # Redefine console logger to run in production.
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        # Redefine django logger to use redefined console logging.
        "django": {
            "handlers": ["console"],
        }
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.views import generic


admin.autodiscover()


urlpatterns = patterns("",

    # Admin URLs.
    url(r"^admin/", include(admin.site.urls)),
    
    # There's no favicon here!
    url(r"^favicon.ico$", generic.RedirectView.as_view()),
    
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for {{ project_name }} project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/{{ docs_version }}/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = settings
"""Settings used by django-herokuapp."""

from django.conf import settings


# The name of the app on the Heroku platform.
HEROKU_APP_NAME = getattr(settings, "HEROKU_APP_NAME", None)

# The optional explicit buildpack URL.
HEROKU_BUILDPACK_URL = getattr(settings, "HEROKU_BUILDPACK_URL", None)

# The canonical site domain.
SITE_DOMAIN = getattr(settings, "SITE_DOMAIN", None)

########NEW FILE########
__FILENAME__ = tests
import unittest, tempfile, shutil, httplib, os.path, string, time, re, os
from contextlib import closing, contextmanager
from itertools import izip_longest
from functools import partial

import sh

from django.utils.crypto import get_random_string

from herokuapp.commands import HerokuCommand, HerokuCommandError


RE_COMMAND_LOG = re.compile("^COMMAND:\s*(.+?)\s*$", re.MULTILINE)


class HerokuappTest(unittest.TestCase):

    def setUp(self):
        self.app = "django-herokuapp-{random}".format(
            random = get_random_string(10, string.digits + string.ascii_lowercase),
        )
        # Create a temp dir.
        self.dir = tempfile.mkdtemp()
        # Add an dummy requirements file, to prevent massive requirements bloat
        # in an unpredictable testing environment.
        with open(os.path.join(self.dir, "requirements.txt"), "wb") as requirements_handle:
            requirements_handle.write("\n".join(["django",
                "django-herokuapp",
                "pytz",
                "waitress",
                "dj-database-url",
                "psycopg2",
                "south",
                "django-require-s3",
                "boto",
                "sh",
            ]))
        # Enable verbose output.
        self.error_return_code_truncate_cap = sh.ErrorReturnCode.truncate_cap
        sh.ErrorReturnCode.truncate_cap = 999999
        # Create the test project.
        self.start_project()

    def sh(self, name):
        return partial(getattr(sh, name), _cwd=self.dir)

    @property
    def heroku(self):
        return HerokuCommand(
            app = self.app,
            cwd = self.dir,
        )

    def start_project(self):
        # Run the start project command.
        self.sh("herokuapp_startproject.py")("django_herokuapp_test", noinput=True, app=self.app)
        # Create an app.
        self.sh(os.path.join(self.dir, "manage.py"))("startapp", "django_herokuapp_test_app")
        with open(os.path.join(self.dir, "django_herokuapp_test", "settings", "production.py"), "ab") as production_settings_handle:
            production_settings_handle.write("\nINSTALLED_APPS += ('django_herokuapp_test_app',)\n")
        with open(os.path.join(self.dir, "django_herokuapp_test_app", "models.py"), "ab") as app_models_handle:
            app_models_handle.write("\nclass TestModel(models.Model):\n    pass")
        self.sh(os.path.join(self.dir, "manage.py"))("schemamigration", "django_herokuapp_test_app", initial=True)

    def assert_app_running(self):
        time.sleep(30)  # Wait to app to initialize.
        domain = "{app}.herokuapp.com".format(app=self.app)
        with closing(httplib.HTTPConnection(domain)) as connection:
            connection.request("HEAD", "/admin/")
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 200)

    def test_config_commands(self):
        self.heroku.config_set(FOO="BAR")
        self.assertEqual(self.heroku.config_get("FOO"), "BAR")
        self.heroku.config_set(FOO="BAR2")
        self.assertEqual(self.heroku.config_get("FOO"), "BAR2")
        # Test multi-config get.
        self.assertEqual(self.heroku.config_get()["FOO"], "BAR2")

    def test_postgres_command(self):
        self.assertTrue(self.heroku.postgres_url())

    def assert_deploy_workflow(self, expected_workflow, **kwargs):
        env = os.environ.copy()
        env.update({
            "DJANGO_SETTINGS_MODULE": "django_herokuapp_test.settings.production",
        })
        dry_run_output = self.sh(os.path.join(self.dir, "manage.py"))("heroku_deploy", dry_run=True, _env=env, **kwargs)
        workflow = RE_COMMAND_LOG.findall(str(dry_run_output))
        for command, expected_command in izip_longest(workflow, expected_workflow, fillvalue=""):
            self.assertTrue(command.startswith(expected_command), msg="Expected command {expected_commands!r} to be run, got {commands!r} instead.".format(
                commands = workflow,
                expected_commands = list(expected_workflow),
            ))

    @contextmanager
    def standardise_dynos(self):
        # Snapshot running dynos.
        heroku_ps = self.heroku.ps()
        if heroku_ps:
            # Turn off dynos for a consistent workflow.
            self.heroku.scale(web=0)
            try:
                yield
            finally:
                self.heroku.scale(**heroku_ps)
        else:
            yield

    def assert_complete_deploy_workflow(self, **kwargs):
        with self.standardise_dynos():
            self.assert_deploy_workflow((
                "heroku plugins:install",
                "heroku build",
                "python manage.py collectstatic",
                "heroku maintenance:on",
                "heroku release",
                "python manage.py syncdb",
                "python manage.py migrate",
                "heroku ps:scale web=1",
                "heroku maintenance:off",
            ), **kwargs)

    def assert_no_db_deploy_workflow(self, **kwargs):
        with self.standardise_dynos():
            self.assert_deploy_workflow((
                "heroku plugins:install",
                "heroku build",
                "python manage.py collectstatic",
                "heroku release",
                "heroku ps:scale web=1",
            ), **kwargs)

    def test_complete_deploy_workflow(self):
        self.assert_complete_deploy_workflow()

    def test_no_db_deploy_workflow(self):
        self.assert_no_db_deploy_workflow(no_db=True)

    def test_no_staticfiles_deploy_workflow(self):
        self.assert_deploy_workflow((
            "heroku plugins:install",
            "heroku build",
            "heroku maintenance:on",
            "heroku release",
            "python manage.py syncdb",
            "python manage.py migrate",
            "heroku ps:scale web=1",
            "heroku maintenance:off",
        ), no_staticfiles=True)

    def test_no_app_deploy_workflow(self):
        self.assert_deploy_workflow((
            "python manage.py collectstatic",
            "heroku maintenance:on",
            "python manage.py syncdb",
            "python manage.py migrate",
            "heroku ps:scale web=1",
            "heroku maintenance:off",
        ), no_app=True)

    def test_no_db_no_staticfiles_deploy_workflow(self):
        self.assert_deploy_workflow((
            "heroku plugins:install",
            "heroku build",
            "heroku release",
            "heroku ps:scale web=1",
        ), no_db=True, no_staticfiles=True)

    def test_no_db_no_app_deploy_workflow(self):
        self.assert_deploy_workflow((
            "python manage.py collectstatic",
            "heroku restart",
            "heroku ps:scale web=1",
        ), no_db=True, no_app=True)

    def test_no_staticfiles_no_app_deploy_workflow(self):
        self.assert_deploy_workflow((
            "heroku maintenance:on",
            "python manage.py syncdb",
            "python manage.py migrate",
            "heroku ps:scale web=1",
            "heroku maintenance:off",
        ), no_staticfiles=True, no_app=True)

    def test_empty_deploy_workflow(self):
        self.assert_deploy_workflow((
        ), no_staticfiles=True, no_app=True, no_db=True)

    def test_deploy(self):
        # Make sure that a dry run will deploy the database and static files.
        self.assert_complete_deploy_workflow()
        # Deploy the site.
        self.sh(os.path.join(self.dir, "deploy.sh"))()
        # Ensure that the app is running.
        self.assert_app_running()
        # Make sure that the database was synced.
        self.assert_no_db_deploy_workflow()
        # Make sure that we can still force-deploy the db.
        self.assert_complete_deploy_workflow(force_db=True)
        # Add another migration.
        self.sh(os.path.join(self.dir, "manage.py"))("datamigration", "django_herokuapp_test_app", "test_migration")
        # Make sure that the deploy includes a migrate.
        self.assert_deploy_workflow((
            "heroku plugins:install",
            "heroku build",
            "python manage.py collectstatic",
            "heroku maintenance:on",
            "heroku ps:scale web=0",
            "heroku release",
            "python manage.py migrate",
            "heroku ps:scale web=1",
            "heroku maintenance:off",
        ))
        # Test redeploy.
        self.sh(os.path.join(self.dir, "deploy.sh"))()
        # Ensure that the app is still running.
        self.assert_app_running()
        # Make sure that the database was synced.
        self.assert_no_db_deploy_workflow()
        # Check that the shortcut deploy with no scaling happens.
        self.assert_deploy_workflow((
            "heroku plugins:install",
            "heroku build",
            "python manage.py collectstatic",
            "heroku release",
        ))

    def tearDown(self):
        pass
        # Delete the app, if it exists.
        try:
            self.heroku("apps:delete", self.app, confirm=self.app)
        except HerokuCommandError:
            pass
        # Remove the temp dir.
        shutil.rmtree(self.dir)
        # Disable verbose output.
        sh.ErrorReturnCode.truncate_cap = self.error_return_code_truncate_cap

########NEW FILE########
