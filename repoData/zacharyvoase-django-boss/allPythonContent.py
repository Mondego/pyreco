__FILENAME__ = cli
# -*- coding: utf-8 -*-

import logging
import os
import sys
import textwrap

from django.utils.importlib import import_module

from djboss.commands import Command


class SettingsImportError(ImportError):
    pass


def get_settings():
    sys.path.append(os.getcwd())
    if 'DJANGO_SETTINGS_MODULE' in os.environ:
        try:
            return import_module(os.environ['DJANGO_SETTINGS_MODULE'])
        except ImportError, exc:
            raise SettingsImportError(textwrap.dedent("""\
                There was an error importing the module specified by the
                DJANGO_SETTINGS_MODULE environment variable. Make sure that it
                refers to a valid and importable Python module."""), exc)

    try:
        import settings
    except ImportError, exc:
        raise SettingsImportError(textwrap.dedent("""\
            Couldn't import a settings module. Make sure that a `settings.py`
            file exists in the current directory, and that it can be imported,
            or that the DJANGO_SETTINGS_MODULE environment variable points
            to a valid and importable Python module."""), exc)
    return settings


def find_commands(app):
    """Return a dict of `command_name: command_obj` for the given app."""

    commands = {}
    app_module = import_module(app) # Fail loudly if an app doesn't exist.
    try:
        commands_module = import_module(app + '.commands')
    except ImportError:
        pass
    else:
        for command in vars(commands_module).itervalues():
            if isinstance(command, Command):
                commands[command.name] = command
    return commands


def find_all_commands(apps):
    """Return a dict of `command_name: command_obj` for all the given apps."""

    commands = {}
    commands.update(find_commands('djboss'))
    for app in apps:
        commands.update(find_commands(app))
    return commands


def main():
    try:
        settings = get_settings()
    except SettingsImportError, exc:
        print >> sys.stderr, exc.args[0]
        print >> sys.stderr
        print >> sys.stderr, "The original exception was:"
        print >> sys.stderr, '\t' + str(exc.args[1])
        sys.exit(1)

    from django.core import management as mgmt
    mgmt.setup_environ(settings)

    commands = find_all_commands(settings.INSTALLED_APPS)

    from djboss.parser import PARSER

    PARSER.set_defaults(settings=settings)
    if settings.DEBUG:
        PARSER.set_defaults(log_level='DEBUG')
    else:
        PARSER.set_defaults(log_level='WARN')

    args = PARSER.parse_args()
    logging.root.setLevel(getattr(logging, args.log_level))

    # Call the command.
    commands[args.command](args)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = commands
# -*- coding: utf-8 -*-

import functools
import re
import sys

from djboss.parser import SUBPARSERS


__all__ = ['Command', 'command', 'argument', 'APP_LABEL', 'MODEL_LABEL']


class Command(object):

    """Wrapper to manage creation and population of sub-parsers on functions."""

    def __init__(self, function, **kwargs):
        self.function = function
        self.parser = self._make_parser(**kwargs)
        self._init_arguments()

    add_argument = property(lambda self: self.parser.add_argument)

    def __call__(self, args):
        return self.function(args)

    def name(self):
        """The name of this command."""

        if hasattr(self.function, 'djboss_name'):
            return self.function.djboss_name
        else:
            return self.function.__name__.replace('_', '-')
    name = property(name)

    def help(self):
        if hasattr(self.function, 'djboss_help'):
            return self.function.djboss_help
        elif getattr(self.function, '__doc__', None):
            # Just the first line of the docstring.
            return self.function.__doc__.splitlines()[0]
    help = property(help)

    def description(self):
        if hasattr(self.function, 'djboss_description'):
            return self.function.djboss_description
        elif getattr(self.function, '__doc__', None):
            return self.function.__doc__
    description = property(description)

    def _make_parser(self, **kwargs):
        """Create and register a subparser for this command."""

        kwargs.setdefault('help', self.help)
        kwargs.setdefault('description', self.description)
        return SUBPARSERS.add_parser(self.name, **kwargs)

    def _init_arguments(self):
        """Initialize the subparser with arguments stored on the function."""

        if hasattr(self.function, 'djboss_arguments'):
            while self.function.djboss_arguments:
                args, kwargs = self.function.djboss_arguments.pop()
                self.add_argument(*args, **kwargs)


def APP_LABEL(label=None, **kwargs):

    """
    argparse type to resolve arguments to Django apps.

    Example Usage:

    *   `@argument('app', type=APP_LABEL)`
    *   `@argument('app', type=APP_LABEL(empty=False))`
    *   `APP_LABEL('auth')` => `<module 'django.contrib.auth' ...>`
    """

    from django.db import models
    from django.conf import settings
    from django.utils.importlib import import_module

    if label is None:
        return functools.partial(APP_LABEL, **kwargs)

    # `get_app('auth')` will return the `django.contrib.auth.models` module.
    models_module = models.get_app(label, emptyOK=kwargs.get('empty', True))
    if models_module is None:
        for installed_app in settings.INSTALLED_APPS:
            # 'app' should resolve to 'path.to.app'.
            if installed_app.split('.')[-1] == label:
                return import_module(installed_app)
    else:
        # 'path.to.app.models' => 'path.to.app'
        return import_module(models_module.__name__.rsplit('.', 1)[0])


def MODEL_LABEL(label):

    """
    argparse type to resolve arguments to Django models.

    Example Usage:

    *   `@argument('app.model', type=MODEL_LABEL)
    *   `MODEL_LABEL('auth.user')` => `<class 'django.contrib.auth.models.User'>`
    """

    from django.db import models

    match = re.match(r'^([\w_]+)\.([\w_]+)$', label)
    if not match:
        raise TypeError

    model = models.get_model(*match.groups())
    if not model:
        raise ValueError
    return model


def command(*args, **kwargs):
    """Decorator to declare that a function is a command."""

    def decorator(function):
        return Command(function, **kwargs)

    if args:
        return decorator(*args)
    return decorator


def argument(*args, **kwargs):
    """Decorator to add an argument to a command."""

    def decorator(function):
        if isinstance(function, Command):
            func = function.function
        else:
            func = function

        if not hasattr(func, 'djboss_arguments'):
            func.djboss_arguments = []
        func.djboss_arguments.append((args, kwargs))

        return function
    return decorator


def manage(args):
    """Run native Django management commands under djboss."""

    from django.core import management as mgmt

    OldOptionParser = mgmt.LaxOptionParser
    class LaxOptionParser(mgmt.LaxOptionParser):
        def __init__(self, *args, **kwargs):
            kwargs['prog'] = 'djboss manage'
            OldOptionParser.__init__(self, *args, **kwargs)
    mgmt.LaxOptionParser = LaxOptionParser

    utility = mgmt.ManagementUtility(['djboss manage'] + args.args)
    utility.prog_name = 'djboss manage'
    utility.execute()

# `prefix_chars='\x00'` will stop argparse from interpreting the management
# sub-command options as options on this command. Unless, of course, those
# arguments begin with a null byte.
manage = Command(manage, add_help=False, prefix_chars='\x00')
manage.add_argument('args', nargs='*')

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-

import argparse

import djboss


PARSER = argparse.ArgumentParser(
    prog = 'djboss',
    description = "Run django-boss management commands.",
    epilog = """
    To discover sub-commands, djboss first finds and imports your Django
    settings. The DJANGO_SETTINGS_MODULE environment variable takes precedence,
    but if unspecified, djboss will look for a `settings` module in the current
    directory.

    Commands should be defined in a `commands` submodule of each app. djboss
    will search each of your INSTALLED_APPS for management commands.""",
)


PARSER.add_argument('--version', action='version', version=djboss.__version__)


PARSER.add_argument('-l', '--log-level', metavar='LEVEL',
    default='WARN', choices='DEBUG INFO WARN ERROR'.split(),
    help="Choose a log level from DEBUG, INFO, WARN or ERROR "
         "(default: %(default)s)")

SUBPARSERS = PARSER.add_subparsers(dest='command', title='commands', metavar='COMMAND')

########NEW FILE########
__FILENAME__ = commands
# -*- coding: utf-8 -*-

from djboss.commands import *
import sys


@command
@argument('-n', '--no-newline', action='store_true',
          help="Don't print a newline afterwards.")
@argument('words', nargs='*')
def echo(args):
    """Echo the arguments back to the console."""
    
    string = ' '.join(args.words)
    if args.no_newline:
        sys.stdout.write(string)
    else:
        print string


@command
def hello(args):
    """Print a cliche to the console."""
    
    print "Hello, World!"


@command
@argument('app', type=APP_LABEL)
def app_path(args):
    """Print a path to the specified app."""
    
    import os.path as p
    
    path, base = p.split(p.splitext(args.app.__file__)[0])
    if base == '__init__':
        print p.join(path, '')
    else:
        if p.splitext(args.app.__file__[-4:])[1] in ('.pyc', '.pyo'):
            print args.app.__file__[:-1]
        else:
            print args.app.__file__


@command
@argument('model', type=MODEL_LABEL)
def model_fields(args):
    """Print all the fields on a specified model."""
    
    justify = 1
    table = []
    for field in args.model._meta.fields:
        justify = max(justify, len(field.name))
        table.append((field.name, field.db_type()))
    
    for name, db_type in table:
        print (name + ':').ljust(justify + 1) + '\t' + db_type


########NEW FILE########
__FILENAME__ = models

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
__FILENAME__ = settings
# Django settings for example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Zachary Voase', 'zacharyvoase@me.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'dev.db'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-gb'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '8@+k3lm3=s+ml6_*(cnpbg1w=6k9xpk5f=irs+&j4_6i=62fy^'

# List of callables that know how to import templates from various sources.
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

ROOT_URLCONF = 'example.urls'

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
    'echoapp',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^example/', include('example.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
