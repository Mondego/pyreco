__FILENAME__ = admin
from django.contrib import admin as django_admin
from django.contrib.admin.sites import AdminSite

from session_csrf import anonymous_csrf


class SessionCsrfAdminSite(AdminSite):
    """Custom admin site that handles login with session_csrf."""

    def login(self, request, extra_context=None):
        @anonymous_csrf
        def call_parent_login(request, extra_context):
            return super(SessionCsrfAdminSite, self).login(request,
                                                           extra_context)

        return call_parent_login(request, extra_context)


# This is for sites that import this file directly.
site = SessionCsrfAdminSite()


def monkeypatch():
    django_admin.site = site

########NEW FILE########
__FILENAME__ = cmd
"""
Installs a skeleton Django app based on Mozilla's Playdoh.

1. Clones the Playdoh repo
2. Renames the project module to your custom package name
3. Creates a virtualenv
4. Installs/compiles the requirements
5. Creates a local settings file
Read more about it here: http://playdoh.readthedocs.org/
"""
from contextlib import contextmanager
from datetime import datetime
import logging
import optparse
import os
import re
import shutil
import subprocess
import sys
import textwrap


allow_user_input = True
verbose = True
log = logging.getLogger(__name__)


def clone_repo(pkg, dest, repo, repo_dest, branch):
    """Clone the Playdoh repo into a custom path."""
    git(['clone', '--recursive', '-b', branch, repo, repo_dest])


def init_pkg(pkg, repo_dest):
    """
    Initializes a custom named package module.

    This works by replacing all instances of 'project' with a custom module
    name.
    """
    vars = {'pkg': pkg}
    with dir_path(repo_dest):
        patch("""\
        diff --git a/manage.py b/manage.py
        index 40ebb0a..cdfe363 100755
        --- a/manage.py
        +++ b/manage.py
        @@ -3,7 +3,7 @@ import os
         import sys

         # Edit this if necessary or override the variable in your environment.
        -os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
        +os.environ.setdefault('DJANGO_SETTINGS_MODULE', '%(pkg)s.settings')

         try:
             # For local development in a virtualenv:
        diff --git a/project/settings/base.py b/project/settings/base.py
        index 312f280..c75e673 100644
        --- a/project/settings/base.py
        +++ b/project/settings/base.py
        @@ -7,7 +7,7 @@ from funfactory.settings_base import *
         # If you did not install Playdoh with the funfactory installer script
         # you may need to edit this value. See the docs about installing from a
         # clone.
        -PROJECT_MODULE = 'project'
        +PROJECT_MODULE = '%(pkg)s'

         # Bundles is a dictionary of two dictionaries, css and js, which list css files
         # and js files that can be bundled together by the minify app.
        diff --git a/setup.py b/setup.py
        index 58dbd93..9a38628 100644
        --- a/setup.py
        +++ b/setup.py
        @@ -3,7 +3,7 @@ import os
         from setuptools import setup, find_packages


        -setup(name='project',
        +setup(name='%(pkg)s',
               version='1.0',
               description='Django application.',
               long_description='',
        """ % vars)

        git(['mv', 'project', pkg])
        git(['commit', '-a', '-m', 'Renamed project module to %s' % pkg])


def generate_key(byte_length):
    """Return a true random ascii string containing byte_length of randomness.

    The resulting key is suitable for cryptogrpahy.
    The key will be hex encoded which means it will be twice as long
    as byte_length, i.e. 40 random bytes yields an 80 byte string.

    byte_length must be at least 32.
    """
    if byte_length < 32:  # at least 256 bit
        raise ValueError('um, %s is probably not long enough for cryptography'
                         % byte_length)
    return os.urandom(byte_length).encode('hex')


def create_settings(pkg, repo_dest, db_user, db_name, db_password, db_host,
                    db_port):
    """
    Creates a local settings file out of the distributed template.

    This also fills in database settings and generates a secret key, etc.
    """
    vars = {'pkg': pkg,
            'db_user': db_user,
            'db_name': db_name,
            'db_password': db_password or '',
            'db_host': db_host or '',
            'db_port': db_port or '',
            'hmac_date': datetime.now().strftime('%Y-%m-%d'),
            'hmac_key': generate_key(32),
            'secret_key': generate_key(32)}
    with dir_path(repo_dest):
        shutil.copyfile('%s/settings/local.py-dist' % pkg,
                        '%s/settings/local.py' % pkg)
        patch("""\
            --- a/%(pkg)s/settings/local.py
            +++ b/%(pkg)s/settings/local.py
            @@ -9,11 +9,11 @@ from . import base
             DATABASES = {
                 'default': {
                     'ENGINE': 'django.db.backends.mysql',
            -        'NAME': 'playdoh_app',
            -        'USER': 'root',
            -        'PASSWORD': '',
            -        'HOST': '',
            -        'PORT': '',
            +        'NAME': '%(db_name)s',
            +        'USER': '%(db_user)s',
            +        'PASSWORD': '%(db_password)s',
            +        'HOST': '%(db_host)s',
            +        'PORT': '%(db_port)s',
                     'OPTIONS': {
                         'init_command': 'SET storage_engine=InnoDB',
                         'charset' : 'utf8',
            @@ -51,14 +51,14 @@ DEV = True
             # Playdoh ships with Bcrypt+HMAC by default because it's the most secure.
             # To use bcrypt, fill in a secret HMAC key. It cannot be blank.
             HMAC_KEYS = {
            -    #'2012-06-06': 'some secret',
            +    '%(hmac_date)s': '%(hmac_key)s',
             }

             from django_sha2 import get_password_hashers
             PASSWORD_HASHERS = get_password_hashers(base.BASE_PASSWORD_HASHERS, HMAC_KEYS)

             # Make this unique, and don't share it with anybody.  It cannot be blank.
            -SECRET_KEY = ''
            +SECRET_KEY = '%(secret_key)s'

             # Uncomment these to activate and customize Celery:
             # CELERY_ALWAYS_EAGER = False  # required to activate celeryd
            """ % vars)


def create_virtualenv(pkg, repo_dest, python):
    """Creates a virtualenv within which to install your new application."""
    workon_home = os.environ.get('WORKON_HOME')
    venv_cmd = find_executable('virtualenv')
    python_bin = find_executable(python)
    if not python_bin:
        raise EnvironmentError('%s is not installed or not '
                               'available on your $PATH' % python)
    if workon_home:
        # Can't use mkvirtualenv directly here because relies too much on
        # shell tricks. Simulate it:
        venv = os.path.join(workon_home, pkg)
    else:
        venv = os.path.join(repo_dest, '.virtualenv')
    if venv_cmd:
        if not verbose:
            log.info('Creating virtual environment in %r' % venv)
        args = ['--python', python_bin, venv]
        if not verbose:
            args.insert(0, '-q')
        subprocess.check_call([venv_cmd] + args)
    else:
        raise EnvironmentError('Could not locate the virtualenv. Install with '
                               'pip install virtualenv.')
    return venv


def install_reqs(venv, repo_dest):
    """Installs all compiled requirements that can't be shipped in vendor."""
    with dir_path(repo_dest):
        args = ['-r', 'requirements/compiled.txt']
        if not verbose:
            args.insert(0, '-q')
        subprocess.check_call([os.path.join(venv, 'bin', 'pip'), 'install'] +
                              args)


def find_executable(name):
    """
    Finds the actual path to a named command.

    The first one on $PATH wins.
    """
    for pt in os.environ.get('PATH', '').split(':'):
        candidate = os.path.join(pt, name)
        if os.path.exists(candidate):
            return candidate


def patch(hunk):
    args = ['-p1', '-r', '.']
    if not verbose:
        args.insert(0, '--quiet')
    ps = subprocess.Popen(['patch'] + args, stdin=subprocess.PIPE)
    ps.stdin.write(textwrap.dedent(hunk))
    ps.stdin.close()
    rs = ps.wait()
    if rs != 0:
        raise RuntimeError('patch %s returned non-zeo exit '
                           'status %s' % (file, rs))


@contextmanager
def dir_path(dir):
    """with dir_path(path) to change into a directory."""
    old_dir = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(old_dir)


def git(cmd_args):
    args = ['git']
    cmd = cmd_args.pop(0)
    args.append(cmd)
    if not verbose:
        if cmd != 'mv':  # doh
            args.append('--quiet')
    args.extend(cmd_args)
    if verbose:
        log.info(' '.join(args))
    subprocess.check_call(args)


def resolve_opt(opt, prompt):
    if not opt:
        if not allow_user_input:
            raise ValueError('%s (value was not set, using --no-input)'
                             % prompt)
        opt = raw_input(prompt)
    return opt


def main():
    global allow_user_input, verbose
    ps = optparse.OptionParser(usage='%prog [options]\n' + __doc__)
    ps.add_option('-p', '--pkg', help='Name of your top level project package.')
    ps.add_option('-d', '--dest',
                  help='Destination dir to put your new app. '
                       'Default: %default',
                  default=os.getcwd())
    ps.add_option('-r', '--repo',
                  help='Playdoh repository to clone. Default: %default',
                  default='git://github.com/mozilla/playdoh.git')
    ps.add_option('-b', '--branch',
                  help='Repository branch to clone. Default: %default',
                  default='master')
    ps.add_option('--repo-dest',
                  help='Clone repository into this directory. '
                       'Default: DEST/PKG')
    ps.add_option('--venv',
                  help='Path to an existing virtualenv you want to use. '
                       'Otherwise, a new one will be created for you.')
    ps.add_option('-P', '--python',
                  help='Python interpreter to use in your virtualenv. '
                       'Default: which %default',
                  default='python')
    ps.add_option('--db-user',
                  help='Database user of your new app. Default: %default',
                  default='root')
    ps.add_option('--db-name',
                  help='Database name for your new app. Default: %default',
                  default='playdoh_app')
    ps.add_option('--db-password',
                  help='Database user password. Default: %default',
                  default=None)
    ps.add_option('--db-host',
                  help='Database connection host. Default: %default',
                  default=None)
    ps.add_option('--db-port',
                  help='Database connection port. Default: %default',
                  default=None)
    ps.add_option('--no-input', help='Never prompt for user input',
                  action='store_true', default=False)
    ps.add_option('-q', '--quiet', help='Less output',
                  action='store_true', default=False)
    (options, args) = ps.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s",
                        stream=sys.stdout)
    allow_user_input = not options.no_input
    verbose = not options.quiet
    options.pkg = resolve_opt(options.pkg, 'Top level package name: ')
    if not re.match('[a-zA-Z0-9_]+', options.pkg):
        ps.error('Package name %r can only contain letters, numbers, and '
                 'underscores' % options.pkg)
    if not find_executable('mysql_config'):
        ps.error('Cannot find mysql_config. Please install MySQL!')
    if not options.repo_dest:
        options.repo_dest = os.path.abspath(os.path.join(options.dest,
                                                         options.pkg))
    clone_repo(options.pkg, options.dest, options.repo, options.repo_dest,
               options.branch)
    if options.venv:
        venv = options.venv
    elif os.environ.get('VIRTUAL_ENV'):
        venv = os.environ['VIRTUAL_ENV']
        log.info('Using existing virtualenv in %s' % venv)
    else:
        venv = create_virtualenv(options.pkg, options.repo_dest, options.python)
    install_reqs(venv, options.repo_dest)
    init_pkg(options.pkg, options.repo_dest)
    create_settings(options.pkg, options.repo_dest, options.db_user,
                    options.db_name, options.db_password, options.db_host,
                    options.db_port)
    if verbose:
        log.info('')
        log.info('Aww yeah. Just installed you some Playdoh.')
        log.info('')
        log.info('cd %s' % options.repo_dest)
        if os.environ.get('WORKON_HOME'):
            log.info('workon %s' % options.pkg)
        else:
            log.info('source %s/bin/activate'
                     % venv.replace(options.repo_dest, '.'))
        log.info('python manage.py runserver')
        log.info('')


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings
from django.utils import translation


def i18n(request):
    return {'LANGUAGES': settings.LANGUAGES,
            'LANG': settings.LANGUAGE_URL_MAP.get(translation.get_language())
                    or translation.get_language(),
            'DIR': 'rtl' if translation.get_language_bidi() else 'ltr',
            }


def globals(request):
    return {'request': request,
            'settings': settings}

########NEW FILE########
__FILENAME__ = helpers
import datetime
import urllib
import urlparse

from django.contrib.staticfiles.storage import staticfiles_storage
from django.template import defaultfilters
from django.utils.encoding import smart_str
from django.utils.html import strip_tags

from jingo import register
import jinja2

from .urlresolvers import reverse

# Yanking filters from Django.
register.filter(strip_tags)
register.filter(defaultfilters.timesince)
register.filter(defaultfilters.truncatewords)


@register.function
def thisyear():
    """The current year."""
    return jinja2.Markup(datetime.date.today().year)


@register.function
def url(viewname, *args, **kwargs):
    """Helper for Django's ``reverse`` in templates."""
    return reverse(viewname, args=args, kwargs=kwargs)


@register.filter
def urlparams(url_, hash=None, **query):
    """Add a fragment and/or query paramaters to a URL.

    New query params will be appended to exising parameters, except duplicate
    names, which will be replaced.
    """
    url = urlparse.urlparse(url_)
    fragment = hash if hash is not None else url.fragment

    # Use dict(parse_qsl) so we don't get lists of values.
    q = url.query
    query_dict = dict(urlparse.parse_qsl(smart_str(q))) if q else {}
    query_dict.update((k, v) for k, v in query.items())

    query_string = _urlencode([(k, v) for k, v in query_dict.items()
                               if v is not None])
    new = urlparse.ParseResult(url.scheme, url.netloc, url.path, url.params,
                               query_string, fragment)
    return new.geturl()


def _urlencode(items):
    """A Unicode-safe URLencoder."""
    try:
        return urllib.urlencode(items)
    except UnicodeEncodeError:
        return urllib.urlencode([(k, smart_str(v)) for k, v in items])


@register.filter
def urlencode(txt):
    """Url encode a path."""
    if isinstance(txt, unicode):
        txt = txt.encode('utf-8')
    return urllib.quote_plus(txt)


@register.function
def static(path):
    return staticfiles_storage.url(path)

########NEW FILE########
__FILENAME__ = log
import logging

from django.conf import settings
from django.http import HttpRequest

import commonware


class AreciboHandler(logging.Handler):
    """An exception log handler that sends tracebacks to Arecibo."""
    def emit(self, record):
        arecibo = getattr(settings, 'ARECIBO_SERVER_URL', '')

        if arecibo and hasattr(record, 'request'):
            if getattr(settings, 'ARECIBO_USES_CELERY', False):
                from django_arecibo.tasks import post
            else:
                from django_arecibo.wrapper import post
            post(record.request, 500)


def log_cef(name, severity=logging.INFO, env=None, username='none',
            signature=None, **kwargs):
    """
    Wraps cef logging function so we don't need to pass in the config
    dictionary every time. See bug 707060. ``env`` can be either a request
    object or just the request.META dictionary.
    """

    cef_logger = commonware.log.getLogger('cef')

    c = {'product': settings.CEF_PRODUCT,
         'vendor': settings.CEF_VENDOR,
         'version': settings.CEF_VERSION,
         'device_version': settings.CEF_DEVICE_VERSION}

    # The CEF library looks for some things in the env object like
    # REQUEST_METHOD and any REMOTE_ADDR stuff.  Django not only doesn't send
    # half the stuff you'd expect, but it specifically doesn't implement
    # readline on its FakePayload object so these things fail.  I have no idea
    # if that's outdated code in Django or not, but andym made this
    # <strike>awesome</strike> less crappy so the tests will actually pass.
    # In theory, the last part of this if() will never be hit except in the
    # test runner.  Good luck with that.
    if isinstance(env, HttpRequest):
        r = env.META.copy()
    elif isinstance(env, dict):
        r = env
    else:
        r = {}

    # Drop kwargs into CEF config array, then log.
    c['environ'] = r
    c.update({
        'username': username,
        'signature': signature,
        'data': kwargs,
    })

    cef_logger.log(severity, name, c)

########NEW FILE########
__FILENAME__ = log_settings
import logging
import logging.handlers
import socket

from django.conf import settings

import commonware.log
import cef
import dictconfig


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


base_fmt = ('%(name)s:%(levelname)s %(message)s '
            ':%(pathname)s:%(lineno)s')
use_syslog = settings.HAS_SYSLOG and not settings.DEBUG

if use_syslog:
    hostname = socket.gethostname()
else:
    hostname = 'localhost'

cfg = {
    'version': 1,
    'filters': {},
    'formatters': {
        'debug': {
            '()': commonware.log.Formatter,
            'datefmt': '%H:%M:%s',
            'format': '%(asctime)s ' + base_fmt,
        },
        'prod': {
            '()': commonware.log.Formatter,
            'datefmt': '%H:%M:%s',
            'format': '%s %s: [%%(REMOTE_ADDR)s] %s' % (hostname,
                                                        settings.SYSLOG_TAG,
                                                        base_fmt),
        },
        'cef': {
            '()': cef.SysLogFormatter,
            'datefmt': '%H:%M:%s',
        },
    },
    'handlers': {
        'console': {
            '()': logging.StreamHandler,
            'formatter': 'debug',
        },
        'syslog': {
            '()': logging.handlers.SysLogHandler,
            'facility': logging.handlers.SysLogHandler.LOG_LOCAL7,
            'formatter': 'prod',
        },
        'arecibo': {
            'level': 'ERROR',
            'class': 'funfactory.log.AreciboHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'cef_syslog': {
            '()': logging.handlers.SysLogHandler,
            'facility': logging.handlers.SysLogHandler.LOG_LOCAL4,
            'formatter': 'cef',
        },
        'cef_console': {
            '()': logging.StreamHandler,
            'formatter': 'cef',
        },
        'null': {
            '()': NullHandler,
        }
    },
    'loggers': {
        'django.request': {
            # 'handlers': ['mail_admins', 'arecibo'],
            'handlers': ['mail_admins', 'arecibo'],
            'level': 'ERROR',
            'propagate': False,
        },
        'cef': {
            'handlers': ['cef_syslog' if use_syslog else 'cef_console'],
        }
    },
    'root': {},
}

for key, value in settings.LOGGING.items():
    cfg[key].update(value)

# Set the level and handlers for all loggers.
for logger in cfg['loggers'].values() + [cfg['root']]:
    if 'handlers' not in logger:
        logger['handlers'] = ['syslog' if use_syslog else 'console']
    if 'level' not in logger:
        logger['level'] = settings.LOG_LEVEL
    if logger is not cfg['root'] and 'propagate' not in logger:
        logger['propagate'] = False

dictconfig.dictConfig(cfg)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import logging
import os
import site
import sys
import warnings


current_settings = None
execute_manager = None
log = logging.getLogger(__name__)
ROOT = None


def path(*a):
    if ROOT is None:
        _not_setup()
    return os.path.join(ROOT, *a)


def setup_environ(manage_file, settings=None, more_pythonic=False):
    """Sets up a Django app within a manage.py file.

    Keyword Arguments

    **settings**
        An imported settings module. Without this, playdoh tries to import
        these modules (in order): DJANGO_SETTINGS_MODULE, settings

    **more_pythonic**
        When True, does not do any path hackery besides adding the vendor dirs.
        This requires a newer Playdoh layout without top level apps, lib, etc.
    """
    # sys is global to avoid undefined local
    global sys, current_settings, execute_manager, ROOT

    ROOT = os.path.dirname(os.path.abspath(manage_file))

    # Adjust the python path and put local packages in front.
    prev_sys_path = list(sys.path)

    # Make root application importable without the need for
    # python setup.py install|develop
    sys.path.append(ROOT)

    if not more_pythonic:
        warnings.warn("You're using an old-style Playdoh layout with a top "
                      "level __init__.py and apps directories. This is error "
                      "prone and fights the Zen of Python. "
                      "See http://playdoh.readthedocs.org/en/latest/"
                      "getting-started/upgrading.html")
        # Give precedence to your app's parent dir, which contains __init__.py
        sys.path.append(os.path.abspath(os.path.join(ROOT, os.pardir)))

        site.addsitedir(path('apps'))
        site.addsitedir(path('lib'))

    # Local (project) vendor library
    site.addsitedir(path('vendor-local'))
    site.addsitedir(path('vendor-local/lib/python'))

    # Global (upstream) vendor library
    site.addsitedir(path('vendor'))
    site.addsitedir(path('vendor/lib/python'))

    # Move the new items to the front of sys.path. (via virtualenv)
    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path

    from django.core.management import execute_manager  # noqa
    if not settings:
        if 'DJANGO_SETTINGS_MODULE' in os.environ:
            settings = import_mod_by_name(os.environ['DJANGO_SETTINGS_MODULE'])
        elif os.path.isfile(os.path.join(ROOT, 'settings_local.py')):
            import settings_local as settings
            warnings.warn("Using settings_local.py is deprecated. See "
                          "http://playdoh.readthedocs.org/en/latest/upgrading.html",
                          DeprecationWarning)
        else:
            import settings
    current_settings = settings
    validate_settings(settings)


def validate_settings(settings):
    """
    Raise an error in prod if we see any insecure settings.

    This used to warn during development but that was changed in
    71718bec324c2561da6cc3990c927ee87362f0f7
    """
    from django.core.exceptions import ImproperlyConfigured
    if settings.SECRET_KEY == '':
        msg = 'settings.SECRET_KEY cannot be blank! Check your local settings'
        if not settings.DEBUG:
            raise ImproperlyConfigured(msg)

    if getattr(settings, 'SESSION_COOKIE_SECURE', None) is None:
        msg = ('settings.SESSION_COOKIE_SECURE should be set to True; '
               'otherwise, your session ids can be intercepted over HTTP!')
        if not settings.DEBUG:
            raise ImproperlyConfigured(msg)

    hmac = getattr(settings, 'HMAC_KEYS', {})
    if not len(hmac.keys()):
        msg = 'settings.HMAC_KEYS cannot be empty! Check your local settings'
        if not settings.DEBUG:
            raise ImproperlyConfigured(msg)


def import_mod_by_name(target):
    # stolen from mock :)
    components = target.split('.')
    import_path = components.pop(0)
    thing = __import__(import_path)

    for comp in components:
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


def _dot_lookup(thing, comp, import_path):
    try:
        return getattr(thing, comp)
    except AttributeError:
        __import__(import_path)
        return getattr(thing, comp)


def _not_setup():
    raise EnvironmentError(
            'setup_environ() has not been called for this process')


def main():
    if current_settings is None:
        _not_setup()
    execute_manager(current_settings)

########NEW FILE########
__FILENAME__ = middleware
"""
Taken from zamboni.amo.middleware.

This is django-localeurl, but with mozilla style capital letters in
the locale codes.
"""

import urllib
from warnings import warn

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.encoding import smart_str

import tower

from . import urlresolvers
from .helpers import urlparams


class LocaleURLMiddleware(object):
    """
    1. Search for the locale.
    2. Save it in the request.
    3. Strip them from the URL.
    """

    def __init__(self):
        if not settings.USE_I18N or not settings.USE_L10N:
            warn("USE_I18N or USE_L10N is False but LocaleURLMiddleware is "
                 "loaded. Consider removing funfactory.middleware."
                 "LocaleURLMiddleware from your MIDDLEWARE_CLASSES setting.")

        self.exempt_urls = getattr(settings, 'FF_EXEMPT_LANG_PARAM_URLS', ())

    def _is_lang_change(self, request):
        """Return True if the lang param is present and URL isn't exempt."""
        if 'lang' not in request.GET:
            return False

        return not any(request.path.endswith(url) for url in self.exempt_urls)

    def process_request(self, request):
        prefixer = urlresolvers.Prefixer(request)
        urlresolvers.set_url_prefix(prefixer)
        full_path = prefixer.fix(prefixer.shortened_path)

        if self._is_lang_change(request):
            # Blank out the locale so that we can set a new one. Remove lang
            # from the query params so we don't have an infinite loop.
            prefixer.locale = ''
            new_path = prefixer.fix(prefixer.shortened_path)
            query = dict((smart_str(k), request.GET[k]) for k in request.GET)
            query.pop('lang')
            return HttpResponsePermanentRedirect(urlparams(new_path, **query))

        if full_path != request.path:
            query_string = request.META.get('QUERY_STRING', '')
            full_path = urllib.quote(full_path.encode('utf-8'))

            if query_string:
                full_path = '%s?%s' % (full_path, query_string)

            response = HttpResponsePermanentRedirect(full_path)

            # Vary on Accept-Language if we changed the locale
            old_locale = prefixer.locale
            new_locale, _ = urlresolvers.split_path(full_path)
            if old_locale != new_locale:
                response['Vary'] = 'Accept-Language'

            return response

        request.path_info = '/' + prefixer.shortened_path
        request.locale = prefixer.locale
        tower.activate(prefixer.locale)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = monkeypatches
import logging
from django.conf import settings


__all__ = ['patch']


# Idempotence! http://en.wikipedia.org/wiki/Idempotence
_has_patched = False


def patch():
    global _has_patched
    if _has_patched:
        return

    # Import for side-effect: configures logging handlers.
    # pylint: disable-msg=W0611
    import log_settings  # noqa

    # Monkey-patch django forms to avoid having to use Jinja2's |safe
    # everywhere.
    try:
        import jingo.monkey
        jingo.monkey.patch()
    except ImportError:
        # If we can't import jingo.monkey, then it's an older jingo,
        # so we go back to the old ways.
        import safe_django_forms
        safe_django_forms.monkeypatch()

    # Monkey-patch Django's csrf_protect decorator to use session-based CSRF
    # tokens:
    if 'session_csrf' in settings.INSTALLED_APPS:
        import session_csrf
        session_csrf.monkeypatch()
        from . import admin
        admin.monkeypatch()

    if 'compressor' in settings.INSTALLED_APPS:
        import jingo
        from compressor.contrib.jinja2ext import CompressorExtension
        jingo.env.add_extension(CompressorExtension)

    logging.debug("Note: funfactory monkey patches executed in %s" % __file__)

    # prevent it from being run again later
    _has_patched = True

########NEW FILE########
__FILENAME__ = settings_base
# Django settings file for a project based on the playdoh template.
# import * into your settings_local.py
import logging
import os
import socket

from django.utils.functional import lazy

from .manage import ROOT, path


# For backwards compatability, (projects built based on cloning playdoh)
# we still have to have a ROOT_URLCONF.
# For new-style playdoh projects this will be overridden automatically
# by the new installer
ROOT_URLCONF = '%s.urls' % os.path.basename(ROOT)

# Is this a dev instance?
DEV = False

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {}  # See settings_local.

SLAVE_DATABASES = []

DATABASE_ROUTERS = ('multidb.PinningMasterSlaveRouter',)

# Site ID is used by Django's Sites framework.
SITE_ID = 1

## Logging
LOG_LEVEL = logging.INFO
HAS_SYSLOG = True
SYSLOG_TAG = "http_app_playdoh"  # Change this after you fork.
LOGGING_CONFIG = None
LOGGING = {}

# CEF Logging
CEF_PRODUCT = 'Playdoh'
CEF_VENDOR = 'Mozilla'
CEF_VERSION = '0'
CEF_DEVICE_VERSION = '0'


## Internationalization.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Gettext text domain
TEXT_DOMAIN = 'messages'
STANDALONE_DOMAINS = [TEXT_DOMAIN, 'javascript']
TOWER_KEYWORDS = {'_lazy': None}
TOWER_ADD_HEADERS = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-US'

## Accepted locales

# Tells the product_details module where to find our local JSON files.
# This ultimately controls how LANGUAGES are constructed.
PROD_DETAILS_DIR = path('lib/product_details_json')

# On dev instances, the list of accepted locales defaults to the contents of
# the `locale` directory within a project module or, for older Playdoh apps,
# the root locale directory.  A localizer can add their locale in the l10n
# repository (copy of which is checked out into `locale`) in order to start
# testing the localization on the dev server.
import glob
import itertools
DEV_LANGUAGES = None
try:
    DEV_LANGUAGES = [
        os.path.basename(loc).replace('_', '-')
        for loc in itertools.chain(glob.iglob(ROOT + '/locale/*'),  # old style
                                   glob.iglob(ROOT + '/*/locale/*'))
        if (os.path.isdir(loc) and os.path.basename(loc) != 'templates')
    ]
except OSError:
    pass

# If the locale/ directory isn't there or it's empty, we make sure that
# we always have at least 'en-US'.
if not DEV_LANGUAGES:
    DEV_LANGUAGES = ('en-US',)

# On stage/prod, the list of accepted locales is manually maintained.  Only
# locales whose localizers have signed off on their work should be listed here.
PROD_LANGUAGES = (
    'en-US',
)


def lazy_lang_url_map():
    from django.conf import settings
    langs = settings.DEV_LANGUAGES if settings.DEV else settings.PROD_LANGUAGES
    return dict([(i.lower(), i) for i in langs])

LANGUAGE_URL_MAP = lazy(lazy_lang_url_map, dict)()


# Override Django's built-in with our native names
def lazy_langs():
    from django.conf import settings
    from product_details import product_details
    langs = DEV_LANGUAGES if settings.DEV else settings.PROD_LANGUAGES
    return dict([(lang.lower(), product_details.languages[lang]['native'])
                 for lang in langs if lang in product_details.languages])

LANGUAGES = lazy(lazy_langs, dict)()

# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
DOMAIN_METHODS = {
    'messages': [
        # Searching apps dirs only exists for historic playdoh apps.
        # See playdoh's base settings for how message paths are set.
        ('apps/**.py',
            'tower.management.commands.extract.extract_tower_python'),
        ('apps/**/templates/**.html',
            'tower.management.commands.extract.extract_tower_template'),
        ('templates/**.html',
            'tower.management.commands.extract.extract_tower_template'),
    ],
}

# Paths that don't require a locale code in the URL.
SUPPORTED_NONLOCALES = ['media', 'static', 'admin']


## Media and templates.

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = path('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = path('static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
# Set this in your local settings which is not committed to version control.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'session_csrf.context_processor',
    'django.contrib.messages.context_processors.messages',
    'funfactory.context_processors.i18n',
    'funfactory.context_processors.globals',
    #'jingo_minify.helpers.build_ids',
)


def get_template_context_processors(exclude=(), append=(),
                        current={'processors': TEMPLATE_CONTEXT_PROCESSORS}):
    """
    Returns TEMPLATE_CONTEXT_PROCESSORS without the processors listed in
    exclude and with the processors listed in append.

    The use of a mutable dict is intentional, in order to preserve the state of
    the TEMPLATE_CONTEXT_PROCESSORS tuple across multiple settings files.
    """

    current['processors'] = tuple(
        [p for p in current['processors'] if p not in exclude]
    ) + tuple(append)

    return current['processors']


TEMPLATE_DIRS = (
    path('templates'),
)

# Storage of static files
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_CSS_FILTERS = (
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter'
)
COMPRESS_PRECOMPILERS = (
    #('text/coffeescript', 'coffee --compile --stdio'),
    ('text/less', 'lessc {infile} {outfile}'),
    #('text/x-sass', 'sass {infile} {outfile}'),
    #('text/x-scss', 'sass --scss {infile} {outfile}'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)


def JINJA_CONFIG():
    # import jinja2
    # from django.conf import settings
    # from caching.base import cache
    config = {'extensions': ['tower.template.i18n', 'jinja2.ext.do',
                             'jinja2.ext.with_', 'jinja2.ext.loopcontrols'],
              'finalize': lambda x: x if x is not None else ''}
#    if 'memcached' in cache.scheme and not settings.DEBUG:
        # We're passing the _cache object directly to jinja because
        # Django can't store binary directly; it enforces unicode on it.
        # Details: http://jinja.pocoo.org/2/documentation/api#bytecode-cache
        # and in the errors you get when you try it the other way.
#        bc = jinja2.MemcachedBytecodeCache(cache._cache,
#                                           "%sj2:" % settings.CACHE_PREFIX)
#        config['cache_size'] = -1 # Never clear the cache
#        config['bytecode_cache'] = bc
    return config


## Middlewares, apps, URL configs.

MIDDLEWARE_CLASSES = (
    'funfactory.middleware.LocaleURLMiddleware',
    'multidb.middleware.PinningRouterMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware',  # Must be after auth middleware.
    'django.contrib.messages.middleware.MessageMiddleware',
    'commonware.middleware.FrameOptionsHeader',
    'mobility.middleware.DetectMobileMiddleware',
    'mobility.middleware.XMobileMiddleware',
)


def get_middleware(exclude=(), append=(),
                   current={'middleware': MIDDLEWARE_CLASSES}):
    """
    Returns MIDDLEWARE_CLASSES without the middlewares listed in exclude and
    with the middlewares listed in append.

    The use of a mutable dict is intentional, in order to preserve the state of
    the MIDDLEWARE_CLASSES tuple across multiple settings files.
    """

    current['middleware'] = tuple(
        [m for m in current['middleware'] if m not in exclude]
    ) + tuple(append)
    return current['middleware']


INSTALLED_APPS = (
    # Local apps
    'funfactory',  # Content common to most playdoh-based apps.
    'compressor',

    'tower',  # for ./manage.py extract (L10n)
    'cronjobs',  # for ./manage.py cron * cmd line tasks
    'django_browserid',


    # Django contrib apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    # 'django.contrib.sites',
    # 'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    # Third-party apps, patches, fixes
    'commonware.response.cookies',
    'djcelery',
    'django_nose',
    'session_csrf',

    # L10n
    'product_details',
)


def get_apps(exclude=(), append=(), current={'apps': INSTALLED_APPS}):
    """
    Returns INSTALLED_APPS without the apps listed in exclude and with the apps
    listed in append.

    The use of a mutable dict is intentional, in order to preserve the state of
    the INSTALLED_APPS tuple across multiple settings files.
    """

    current['apps'] = tuple(
        [a for a in current['apps'] if a not in exclude]
    ) + tuple(append)
    return current['apps']

# Path to Java. Used for compress_assets.
JAVA_BIN = '/usr/bin/java'

# Sessions
#
# By default, be at least somewhat secure with our session cookies.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True

## Auth
# The first hasher in this list will be used for new passwords.
# Any other hasher in the list can be used for existing passwords.
# Playdoh ships with Bcrypt+HMAC by default because it's the most secure.
# To use bcrypt, fill in a secret HMAC key in your local settings.
BASE_PASSWORD_HASHERS = (
    'django_sha2.hashers.BcryptHMACCombinedPasswordVerifier',
    'django_sha2.hashers.SHA512PasswordHasher',
    'django_sha2.hashers.SHA256PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
)
HMAC_KEYS = {  # for bcrypt only
    #'2012-06-06': 'cheesecake',
}

from django_sha2 import get_password_hashers
PASSWORD_HASHERS = get_password_hashers(BASE_PASSWORD_HASHERS, HMAC_KEYS)

## Tests
TEST_RUNNER = 'test_utils.runner.RadicalTestSuiteRunner'

## Celery

# True says to simulate background tasks without actually using celeryd.
# Good for local development in case celeryd is not running.
CELERY_ALWAYS_EAGER = True

BROKER_CONNECTION_TIMEOUT = 0.1
CELERY_RESULT_BACKEND = 'amqp'
CELERY_IGNORE_RESULT = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Time in seconds before celery.exceptions.SoftTimeLimitExceeded is raised.
# The task can catch that and recover but should exit ASAP.
CELERYD_TASK_SOFT_TIME_LIMIT = 60 * 2

## Arecibo
# when ARECIBO_SERVER_URL is set, it can use celery or the regular wrapper
ARECIBO_USES_CELERY = True

# For absolute urls
try:
    DOMAIN = socket.gethostname()
except socket.error:
    DOMAIN = 'localhost'
PROTOCOL = "http://"
PORT = 80

## django-mobility
MOBILE_COOKIE = 'mobile'

########NEW FILE########
__FILENAME__ = urlresolvers
from threading import local

from django.conf import settings
from django.core.urlresolvers import reverse as django_reverse
from django.utils.encoding import iri_to_uri
from django.utils.functional import lazy
from django.utils.translation.trans_real import parse_accept_lang_header


# Thread-local storage for URL prefixes. Access with (get|set)_url_prefix.
_local = local()


def set_url_prefix(prefix):
    """Set the ``prefix`` for the current thread."""
    _local.prefix = prefix


def get_url_prefix():
    """Get the prefix for the current thread, or None."""
    return getattr(_local, 'prefix', None)


def reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None):
    """Wraps Django's reverse to prepend the correct locale."""
    prefixer = get_url_prefix()

    if prefixer:
        prefix = prefix or '/'
    url = django_reverse(viewname, urlconf, args, kwargs, prefix)
    if prefixer:
        url = prefixer.fix(url)

    # Ensure any unicode characters in the URL are escaped.
    return iri_to_uri(url)


reverse_lazy = lazy(reverse, str)


def find_supported(test):
    return [settings.LANGUAGE_URL_MAP[x] for
            x in settings.LANGUAGE_URL_MAP if
            x.split('-', 1)[0] == test.lower().split('-', 1)[0]]


def split_path(path_):
    """
    Split the requested path into (locale, path).

    locale will be empty if it isn't found.
    """
    path = path_.lstrip('/')

    # Use partitition instead of split since it always returns 3 parts
    first, _, rest = path.partition('/')

    lang = first.lower()
    if lang in settings.LANGUAGE_URL_MAP:
        return settings.LANGUAGE_URL_MAP[lang], rest
    else:
        supported = find_supported(first)
        if len(supported):
            return supported[0], rest
        else:
            return '', path


class Prefixer(object):

    def __init__(self, request):
        self.request = request
        split = split_path(request.path_info)
        self.locale, self.shortened_path = split

    def get_language(self):
        """
        Return a locale code we support on the site using the
        user's Accept-Language header to determine which is best. This
        mostly follows the RFCs but read bug 439568 for details.
        """
        if 'lang' in self.request.GET:
            lang = self.request.GET['lang'].lower()
            if lang in settings.LANGUAGE_URL_MAP:
                return settings.LANGUAGE_URL_MAP[lang]

        if self.request.META.get('HTTP_ACCEPT_LANGUAGE'):
            best = self.get_best_language(
                self.request.META['HTTP_ACCEPT_LANGUAGE'])
            if best:
                return best
        return settings.LANGUAGE_CODE

    def get_best_language(self, accept_lang):
        """Given an Accept-Language header, return the best-matching language."""
        LUM = settings.LANGUAGE_URL_MAP
        langs = dict(LUM)
        langs.update((k.split('-')[0], v) for k, v in LUM.items() if
                     k.split('-')[0] not in langs)
        try:
            ranked = parse_accept_lang_header(accept_lang)
        except ValueError:  # see https://code.djangoproject.com/ticket/21078
            return
        else:
            for lang, _ in ranked:
                lang = lang.lower()
                if lang in langs:
                    return langs[lang]
                pre = lang.split('-')[0]
                if pre in langs:
                    return langs[pre]

    def fix(self, path):
        path = path.lstrip('/')
        url_parts = [self.request.META['SCRIPT_NAME']]

        if path.partition('/')[0] not in settings.SUPPORTED_NONLOCALES:
            locale = self.locale if self.locale else self.get_language()
            url_parts.append(locale)

        url_parts.append(path)

        return '/'.join(url_parts)

########NEW FILE########
__FILENAME__ = utils
import logging

from django.conf import settings


log = logging.getLogger('funfactory')


def absolutify(url):
    """Takes a URL and prepends the SITE_URL"""
    site_url = getattr(settings, 'SITE_URL', False)

    # If we don't define it explicitly
    if not site_url:
        protocol = settings.PROTOCOL
        hostname = settings.DOMAIN
        port = settings.PORT
        if (protocol, port) in (('https://', 443), ('http://', 80)):
            site_url = ''.join(map(str, (protocol, hostname)))
        else:
            site_url = ''.join(map(str, (protocol, hostname, ':', port)))

    return site_url + url

########NEW FILE########
__FILENAME__ = run_tests
import os
import sys

import nose


__test__ = False  # Not a test to be collected by Nose itself.


if __name__ == '__main__':
    sys.path.append(os.getcwd())  # Simulate running nosetests from the root.
    from tests import FunFactoryTests
    nose.main(addplugins=[FunFactoryTests()])

########NEW FILE########
__FILENAME__ = test_accepted_locales
import os
import shutil

from django.conf import settings
import test_utils

from funfactory.manage import path


class AcceptedLocalesTest(test_utils.TestCase):
    """Test lazy evaluation of locale related settings.

    Verify that some localization-related settings are lazily evaluated based 
    on the current value of the DEV variable.  Depending on the value, 
    DEV_LANGUAGES or PROD_LANGUAGES should be used.

    """
    locale = path('project/locale')
    locale_bkp = path('project/locale_bkp')

    @classmethod
    def setup_class(cls):
        """Create a directory structure for locale/.

        Back up the existing project/locale/ directory and create the following
        hierarchy in its place:

            - project/locale/en-US/LC_MESSAGES
            - project/locale/fr/LC_MESSAGES
            - project/locale/templates/LC_MESSAGES
            - project/locale/empty_file

        Also, set PROD_LANGUAGES to ('en-US',).

        """
        if os.path.exists(cls.locale_bkp):
            raise Exception('A backup of locale/ exists at %s which might '
                            'mean that previous tests didn\'t end cleanly. '
                            'Skipping the test suite.' % cls.locale_bkp)
        cls.DEV = settings.DEV
        cls.PROD_LANGUAGES = settings.PROD_LANGUAGES
        cls.DEV_LANGUAGES = settings.DEV_LANGUAGES
        settings.PROD_LANGUAGES = ('en-US',)
        os.rename(cls.locale, cls.locale_bkp)
        for loc in ('en-US', 'fr', 'templates'):
            os.makedirs(os.path.join(cls.locale, loc, 'LC_MESSAGES'))
        open(os.path.join(cls.locale, 'empty_file'), 'w').close()

    @classmethod
    def teardown_class(cls):
        """Remove the testing locale/ dir and bring back the backup."""

        settings.DEV = cls.DEV
        settings.PROD_LANGUAGES = cls.PROD_LANGUAGES
        settings.DEV_LANGUAGES = cls.DEV_LANGUAGES
        shutil.rmtree(cls.locale)
        os.rename(cls.locale_bkp, cls.locale)

    def test_build_dev_languages(self):
        """Test that the list of dev locales is built properly.

        On dev instances, the list of accepted locales should correspond to 
        the per-locale directories in locale/.

        """
        settings.DEV = True
        assert (settings.DEV_LANGUAGES == ['en-US', 'fr'] or
                settings.DEV_LANGUAGES == ['fr', 'en-US']), \
                'DEV_LANGUAGES do not correspond to the contents of locale/.'

    def test_dev_languages(self):
        """Test the accepted locales on dev instances.

        On dev instances, allow locales defined in DEV_LANGUAGES.

        """
        settings.DEV = True
        # simulate the successful result of the DEV_LANGUAGES list 
        # comprehension defined in settings.
        settings.DEV_LANGUAGES = ['en-US', 'fr']
        assert settings.LANGUAGE_URL_MAP == {'en-us': 'en-US', 'fr': 'fr'}, \
               ('DEV is True, but DEV_LANGUAGES are not used to define the '
                'allowed locales.')

    def test_prod_languages(self):
        """Test the accepted locales on prod instances.

        On stage/prod instances, allow locales defined in PROD_LANGUAGES.

        """
        settings.DEV = False
        assert settings.LANGUAGE_URL_MAP == {'en-us': 'en-US'}, \
               ('DEV is False, but PROD_LANGUAGES are not used to define the '
                'allowed locales.')

########NEW FILE########
__FILENAME__ = test_admin
from django.conf import settings
from django.conf.urls.defaults import patterns
from django.contrib import admin
import django.contrib.admin.sites
from django.template.loader import BaseLoader
from django.test import TestCase

from mock import patch, Mock
from session_csrf import ANON_COOKIE


urlpatterns = None


def setup():
    global urlpatterns
    urlpatterns = patterns('',
        (r'^admin/$', admin.site.urls),
    )


class FakeLoader(BaseLoader):
    """
    Gets around TemplateNotFound errors by always returning an empty string as
    the template.
    """
    is_usable = True

    def load_template_source(self, template_name, template_dirs=None):
        return ('', 'FakeLoader')


@patch.object(settings, 'TEMPLATE_LOADERS', ['tests.test_admin.FakeLoader'])
class SessionCsrfAdminTests(TestCase):
    urls = 'tests.test_admin'

    @patch.object(django.contrib.admin.sites, 'reverse')
    def test_login_has_csrf(self, reverse):
        reverse = Mock()
        self.client.get('admin/', follow=True)
        assert self.client.cookies.get(ANON_COOKIE), (
            "Anonymous CSRF Cookie not set.")

########NEW FILE########
__FILENAME__ = test_context_processors
import jingo
import jinja2
from nose.tools import eq_
from django.test import TestCase, RequestFactory

from mock import patch

import funfactory.context_processors


class TestContext(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def render(self, content, request=None):
        if not request:
            request = self.factory.get('/')
        tpl = jinja2.Template(content)
        return jingo.render_to_string(request, tpl)

    def test_request(self):
        eq_(self.render('{{ request.path }}'), '/')

    def test_settings(self):
        eq_(self.render('{{ settings.SITE_ID }}'), '1')

    def test_languages(self):
        eq_(self.render("{{ LANGUAGES['en-us'] }}"), 'English (US)')

    @patch.object(funfactory.context_processors, 'translation')
    def test_languages(self, translation):
        translation.get_language.return_value = 'en-US'
        eq_(self.render("{{ LANG }}"), 'en-US')

    def test_lang_dir(self):
        eq_(self.render("{{ DIR }}"), 'ltr')

########NEW FILE########
__FILENAME__ = test_helpers
from nose.tools import eq_, ok_
from django.test import TestCase
import jingo


def render(s, context={}):
    t = jingo.env.from_string(s)
    return t.render(context)


class HelpersTests(TestCase):

    def test_urlencode_with_unicode(self):
        template = '<a href="?var={{ key|urlencode }}">'
        context = {'key': '?& /()'}
        eq_(render(template, context), '<a href="?var=%3F%26+%2F%28%29">')
        # non-ascii
        context = {'key': u'\xe4'}
        eq_(render(template, context), '<a href="?var=%C3%A4">')

########NEW FILE########
__FILENAME__ = test_install
import sys
import subprocess
from subprocess import Popen
import unittest

from nose.tools import eq_

from tests import PLAYDOH


class TestInstall(unittest.TestCase):

    def test(self):
        # sys.executable is our tox virtualenv that includes
        # compiled/dev modules.
        p = Popen([sys.executable, 'manage.py', 'test'],
                   stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
                   cwd=PLAYDOH)
        print p.stdout.read()
        eq_(p.wait(), 0)

########NEW FILE########
__FILENAME__ = test_manage
import smtplib
import xml.dom
import unittest

from nose.tools import eq_, raises

from funfactory.manage import import_mod_by_name


class TestImporter(unittest.TestCase):

    def test_single_mod(self):
        eq_(import_mod_by_name('smtplib'), smtplib)

    def test_mod_attr(self):
        eq_(import_mod_by_name('smtplib.SMTP'), smtplib.SMTP)

    def test_multiple_attrs(self):
        eq_(import_mod_by_name('smtplib.SMTP.connect'),
            smtplib.SMTP.connect)

    def test_multiple_mods(self):
        eq_(import_mod_by_name('xml.dom'), xml.dom)

    @raises(ImportError)
    def test_unknown_mod(self):
        import_mod_by_name('notthenameofamodule')

########NEW FILE########
__FILENAME__ = test_middleware
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings

from funfactory.middleware import LocaleURLMiddleware


class TestLocaleURLMiddleware(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.middleware = LocaleURLMiddleware()

    @override_settings(DEV_LANGUAGES=('de', 'fr'),
                       FF_EXEMPT_LANG_PARAM_URLS=())
    def test_redirects_to_correct_language(self):
        """Should redirect to lang prefixed url."""
        path = '/the/dude/'
        req = self.rf.get(path, HTTP_ACCEPT_LANGUAGE='de')
        resp = LocaleURLMiddleware().process_request(req)
        self.assertEqual(resp['Location'], '/de' + path)

    @override_settings(DEV_LANGUAGES=('es', 'fr'),
                       LANGUAGE_CODE='en-US',
                       FF_EXEMPT_LANG_PARAM_URLS=())
    def test_redirects_to_default_language(self):
        """Should redirect to default lang if not in settings."""
        path = '/the/dude/'
        req = self.rf.get(path, HTTP_ACCEPT_LANGUAGE='de')
        resp = LocaleURLMiddleware().process_request(req)
        self.assertEqual(resp['Location'], '/en-US' + path)

    @override_settings(DEV_LANGUAGES=('de', 'fr'),
                       FF_EXEMPT_LANG_PARAM_URLS=('/other/',))
    def test_redirects_lang_param(self):
        """Middleware should remove the lang param on redirect."""
        path = '/fr/the/dude/'
        req = self.rf.get(path, {'lang': 'de'})
        resp = LocaleURLMiddleware().process_request(req)
        self.assertEqual(resp['Location'], '/de/the/dude/')

    @override_settings(DEV_LANGUAGES=('de', 'fr'),
                       FF_EXEMPT_LANG_PARAM_URLS=('/dude/',))
    def test_no_redirect_lang_param(self):
        """Middleware should not redirect when exempt."""
        path = '/fr/the/dude/'
        req = self.rf.get(path, {'lang': 'de'})
        resp = LocaleURLMiddleware().process_request(req)
        self.assertIs(resp, None)  # no redirect

########NEW FILE########
__FILENAME__ = test_migrations
import re
from os import listdir
from os.path import join

from django.test import TestCase

from funfactory.manage import path


class MigrationTests(TestCase):
    """Sanity checks for the SQL migration scripts."""

    @staticmethod
    def _migrations_path():
        """Return the absolute path to the migration script folder."""
        return path('migrations')

    def test_unique(self):
        """Assert that the numeric prefixes of the DB migrations are unique."""
        leading_digits = re.compile(r'^\d+')
        seen_numbers = set()
        path = self._migrations_path()
        for filename in listdir(path):
            match = leading_digits.match(filename)
            if match:
                number = match.group()
                if number in seen_numbers:
                    self.fail('There is more than one migration #%s in %s.' %
                              (number, path))
                seen_numbers.add(number)

    def test_innodb_and_utf8(self):
        """Make sure each created table uses the InnoDB engine and UTF-8."""
        # Heuristic: make sure there are at least as many "ENGINE=InnoDB"s as
        # "CREATE TABLE"s. (There might be additional "InnoDB"s in ALTER TABLE
        # statements, which are fine.)
        path = self._migrations_path()
        for filename in sorted(listdir(path)):
            with open(join(path, filename)) as f:
                contents = f.read()
            creates = contents.count('CREATE TABLE')
            engines = contents.count('ENGINE=InnoDB')
            encodings = (contents.count('CHARSET=utf8') +
                         contents.count('CHARACTER SET utf8'))
            assert engines >= creates, ("There weren't as many "
                'occurrences of "ENGINE=InnoDB" as of "CREATE TABLE" in '
                'migration %s.' % filename)
            assert encodings >= creates, ("There weren't as many "
                'UTF-8 declarations as "CREATE TABLE" occurrences in '
                'migration %s.' % filename)

########NEW FILE########
__FILENAME__ = test_settings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from mock import Mock, patch
from nose.tools import eq_, raises

from funfactory.manage import validate_settings
from funfactory.settings_base import (get_apps, get_middleware,
    get_template_context_processors)


@patch.object(settings, 'DEBUG', True)
@patch.object(settings, 'HMAC_KEYS', {'2012-06-06': 'secret'})
@patch.object(settings, 'SECRET_KEY', 'any random value')
@patch.object(settings, 'SESSION_COOKIE_SECURE', False)
def test_insecure_session_cookie_for_dev():
    validate_settings(settings)


@raises(ImproperlyConfigured)
@patch.object(settings, 'DEBUG', False)
@patch.object(settings, 'HMAC_KEYS', {'2012-06-06': 'secret'})
@patch.object(settings, 'SECRET_KEY', '')
@patch.object(settings, 'SESSION_COOKIE_SECURE', True)
def test_empty_secret_key_for_prod():
    validate_settings(settings)


@patch.object(settings, 'DEBUG', False)
@patch.object(settings, 'HMAC_KEYS', {'2012-06-06': 'secret'})
@patch.object(settings, 'SECRET_KEY', 'any random value')
@patch.object(settings, 'SESSION_COOKIE_SECURE', True)
def test_secret_key_ok():
    """Validate required security-related settings.

    Don't raise exceptions when required settings are set properly."""
    validate_settings(settings)


@raises(ImproperlyConfigured)
@patch.object(settings, 'DEBUG', False)
@patch.object(settings, 'HMAC_KEYS', {'2012-06-06': 'secret'})
@patch.object(settings, 'SECRET_KEY', 'any random value')
@patch.object(settings, 'SESSION_COOKIE_SECURE', None)
def test_session_cookie_ok():
    """Raise an exception if session cookies aren't secure in production."""
    validate_settings(settings)


@patch.object(settings, 'DEBUG', True)
@patch.object(settings, 'HMAC_KEYS', {})
@patch.object(settings, 'SESSION_COOKIE_SECURE', False)
def test_empty_hmac_in_dev():
    # Should not raise an exception.
    validate_settings(settings)


@raises(ImproperlyConfigured)
@patch.object(settings, 'DEBUG', False)
@patch.object(settings, 'HMAC_KEYS', {})
@patch.object(settings, 'SESSION_COOKIE_SECURE', False)
def test_empty_hmac_in_prod():
    validate_settings(settings)


def test_get_apps():
    eq_(get_apps(exclude=('chico',),
        current={'apps': ('groucho', 'harpo', 'chico')}),
        ('groucho', 'harpo'))
    eq_(get_apps(append=('zeppo',),
        current={'apps': ('groucho', 'harpo', 'chico')}),
        ('groucho', 'harpo', 'chico', 'zeppo'))
    eq_(get_apps(exclude=('harpo', 'zeppo'), append=('chico',),
        current={'apps': ('groucho', 'harpo', 'zeppo')}),
        ('groucho', 'chico'))
    eq_(get_apps(exclude=('funfactory'), append=('gummo',)), get_apps())


def test_get_middleware():
    eq_(get_middleware(exclude=['larry', 'moe'],
        current={'middleware': ('larry', 'curly', 'moe')}),
        ('curly',))
    eq_(get_middleware(append=('shemp', 'moe'),
        current={'middleware': ('larry', 'curly')}),
        ('larry', 'curly', 'shemp', 'moe'))
    eq_(get_middleware(exclude=('curly'), append=['moe'],
        current={'middleware': ('shemp', 'curly', 'larry')}),
        ('shemp', 'larry', 'moe'))
    eq_(get_middleware(append=['emil']), get_middleware())


def test_get_processors():
    eq_(get_template_context_processors(exclude=('aramis'),
        current={'processors': ('athos', 'porthos', 'aramis')}),
        ('athos', 'porthos'))
    eq_(get_template_context_processors(append=("d'artagnan",),
        current={'processors': ('athos', 'porthos')}),
        ('athos', 'porthos', "d'artagnan"))
    eq_(get_template_context_processors(exclude=['athos'], append=['aramis'],
        current={'processors': ('athos', 'porthos', "d'artagnan")}),
        ('porthos', "d'artagnan", 'aramis'))
    eq_(get_template_context_processors(append=['richelieu']),
        get_template_context_processors())

########NEW FILE########
__FILENAME__ = test_urlresolvers
# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings

from funfactory.urlresolvers import reverse, split_path, Prefixer
from mock import patch, Mock
from nose.tools import eq_, ok_


# split_path tests use a test generator, which cannot be used inside of a
# TestCase class
def test_split_path():
    testcases = [
        # Basic
        ('en-US/some/action', ('en-US', 'some/action')),
        # First slash doesn't matter
        ('/en-US/some/action', ('en-US', 'some/action')),
        # Nor does capitalization
        ('En-uS/some/action', ('en-US', 'some/action')),
        # Unsupported languages return a blank language
        ('unsupported/some/action', ('', 'unsupported/some/action')),
        ]

    for tc in testcases:
        yield check_split_path, tc[0], tc[1]


def check_split_path(path, result):
    res = split_path(path)
    eq_(res, result)


# Test urlpatterns
urlpatterns = patterns('',
    url(r'^test/$', lambda r: None, name='test.view')
)


class FakePrefixer(object):
    def __init__(self, fix):
        self.fix = fix


@patch('funfactory.urlresolvers.get_url_prefix')
class TestReverse(TestCase):
    urls = 'tests.test_urlresolvers'

    def test_unicode_url(self, get_url_prefix):
        # If the prefixer returns a unicode URL it should be escaped and cast
        # as a str object.
        get_url_prefix.return_value = FakePrefixer(lambda p: u'/Françoi%s' % p)
        result = reverse('test.view')

        # Ensure that UTF-8 characters are escaped properly.
        self.assertEqual(result, '/Fran%C3%A7oi/test/')
        self.assertEqual(type(result), str)


class TestPrefixer(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(LANGUAGE_CODE='en-US')
    def test_get_language_default_language_code(self):
        """
        Should return default set by settings.LANGUAGE_CODE if no 'lang'
        url parameter and no Accept-Language header
        """
        request = self.factory.get('/')
        self.assertFalse('lang' in request.GET)
        self.assertFalse(request.META.get('HTTP_ACCEPT_LANGUAGE'))
        prefixer = Prefixer(request)
        eq_(prefixer.get_language(), 'en-US')

    @override_settings(LANGUAGE_URL_MAP={'en-us': 'en-US', 'de': 'de'})
    def test_get_language_valid_lang_param(self):
        """
        Should return lang param value if it is in settings.LANGUAGE_URL_MAP
        """
        request = self.factory.get('/?lang=de')
        eq_(request.GET.get('lang'), 'de')
        ok_('de' in settings.LANGUAGE_URL_MAP)
        prefixer = Prefixer(request)
        eq_(prefixer.get_language(), 'de')

    @override_settings(LANGUAGE_CODE='en-US',
                       LANGUAGE_URL_MAP={'en-us': 'en-US'})
    def test_get_language_invalid_lang_param(self):
        """
        Should return default set by settings.LANGUAGE_CODE if lang
        param value is not in settings.LANGUAGE_URL_MAP
        """
        request = self.factory.get('/?lang=de')
        ok_('lang' in request.GET)
        self.assertFalse('de' in settings.LANGUAGE_URL_MAP)
        prefixer = Prefixer(request)
        eq_(prefixer.get_language(), 'en-US')

    def test_get_language_returns_best(self):
        """
        Should pass Accept-Language header value to get_best_language
        and return result
        """
        request = self.factory.get('/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'de, es' 
        prefixer = Prefixer(request)
        prefixer.get_best_language = Mock(return_value='de')
        eq_(prefixer.get_language(), 'de')
        prefixer.get_best_language.assert_called_once_with('de, es')

    @override_settings(LANGUAGE_CODE='en-US')
    def test_get_language_no_best(self):
        """
        Should return default set by settings.LANGUAGE_CODE if
        get_best_language return value is None
        """
        request = self.factory.get('/')
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'de, es' 
        prefixer = Prefixer(request)
        prefixer.get_best_language = Mock(return_value=None)
        eq_(prefixer.get_language(), 'en-US')
        prefixer.get_best_language.assert_called_once_with('de, es')

    @override_settings(LANGUAGE_URL_MAP={'en-us': 'en-US', 'de': 'de'})
    def test_get_best_language_exact_match(self):
        """
        Should return exact match if it is in settings.LANGUAGE_URL_MAP
        """
        request = self.factory.get('/')
        prefixer = Prefixer(request)
        eq_(prefixer.get_best_language('de, es'), 'de')

    @override_settings(LANGUAGE_URL_MAP={'en-us': 'en-US', 'es-ar': 'es-AR'})
    def test_get_best_language_prefix_match(self):
        """
        Should return a language with a matching prefix from
        settings.LANGUAGE_URL_MAP if it exists but no exact match does
        """
        request = self.factory.get('/')
        prefixer = Prefixer(request)
        eq_(prefixer.get_best_language('es-CL'), 'es-AR')

    @override_settings(LANGUAGE_URL_MAP={'en-us': 'en-US'})
    def test_get_best_language_no_match(self):
        """
        Should return None if there is no exact match or matching
        prefix
        """
        request = self.factory.get('/')
        prefixer = Prefixer(request)
        eq_(prefixer.get_best_language('de'), None)

    @override_settings(LANGUAGE_URL_MAP={'en-us': 'en-US'})
    def test_get_best_language_handles_parse_accept_lang_header_error(self):
        """
        Should return None despite error raised by bug described in
        https://code.djangoproject.com/ticket/21078
        """
        request = self.factory.get('/')
        prefixer = Prefixer(request)
        eq_(prefixer.get_best_language('en; q=1,'), None)

########NEW FILE########
__FILENAME__ = test__utils
from django.conf import settings

from mock import patch
from nose.tools import eq_
from django.test import TestCase

import funfactory.utils as utils


@patch.object(settings, 'DOMAIN', 'test.mo.com')
class AbsolutifyTests(TestCase):
    ABS_PATH = '/some/absolute/path'

    def test_basic(self):
        url = utils.absolutify(AbsolutifyTests.ABS_PATH)
        eq_('%s/some/absolute/path' % settings.SITE_URL, url)

    @patch.object(settings, 'PROTOCOL', 'https://')
    @patch.object(settings, 'PORT', 443)
    def test_https(self):
        url = utils.absolutify(AbsolutifyTests.ABS_PATH)
        eq_('%s/some/absolute/path' % settings.SITE_URL, url)

    @patch.object(settings, 'SITE_URL', '')
    @patch.object(settings, 'PORT', 8009)
    def test_with_port(self):
        url = utils.absolutify(AbsolutifyTests.ABS_PATH)
        eq_('http://test.mo.com:8009/some/absolute/path', url)

########NEW FILE########
