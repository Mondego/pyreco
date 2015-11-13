__FILENAME__ = django-mason
#!/usr/bin/env python

"""Django Mason

Usage:
  django-mason generate <target> [--template=<default>]
  django-mason startproject <target> [--template=<default>]
  django-mason (-h | --help)
  django-mason --version

Options:
  --template=<default>  Project template [default: default].
  -h --help             Show this screen.
  --version             Show version.
"""
from importlib import import_module
from os.path import join, abspath, dirname
from docopt import docopt

from mason import generate, startproject

from mason.conf import PLUGINS


def get_plugin_class(plugin_path):
    try:
        module, classname = plugin_path.rsplit('.', 1)
    except ValueError:
        raise Exception('%s isn\'t a middleware module' % plugin_path)
    try:
        mod = import_module(module)
    except ImportError as e:
        raise Exception('Error importing middleware %s: "%s"' % (module, e))
    try:
        klass = getattr(mod, classname)
    except AttributeError:
        raise Exception('Middleware module "%s" does not define a "%s" class' % (module, classname))
    return klass


if __name__ == '__main__':

    kwargs = docopt(__doc__, version='Django Mason 0.1')
    templates_dir = join(abspath(dirname(generate.__file__)), 'templates', kwargs['--template'])
    kwargs['template'] = templates_dir
    kwargs['extensions'] = ['py', 'txt', 'yml']
    kwargs['plugins'] = []
    kwargs['plugin_names'] = []

    for plugin_path in PLUGINS:
        PluginClass = get_plugin_class(plugin_path)
        plugin = PluginClass()
        should_enable = plugin.ask()
        if should_enable:
            kwargs['plugins'].append(plugin)
            kwargs['plugin_names'].append(plugin.name)
            for k, v in plugin.get_context().iteritems():
                if v is not None:
                    if k in kwargs and type(v) == list:
                        kwargs[k].extend(v)
                    else:
                        kwargs[k] = v

    target = "%s_template" % kwargs['<target>']
    args = (target, )
    generate.Command().execute(*args, **kwargs)

    if 'startproject' in kwargs:
        args = kwargs['<target>']
        kwargs = {'template': target}
        startproject.Command().execute(args, **kwargs)

########NEW FILE########
__FILENAME__ = admin
from mason.bricks.base import BaseBrick


class Admin(BaseBrick):

    name = "Admin"
    description = "Enables Django Admin"
    installed_apps = ['django.contrib.admin']
    urls = ["url(r'^admin/', include(admin.site.urls))"]

########NEW FILE########
__FILENAME__ = base
from os.path import join, abspath, dirname


class BaseBrick(object):

    name = ""
    description = ""

    installed_apps = None
    dependencies = None
    middleware_classes = None
    settings = None
    files = None
    urls = None

    def get_context(self):
        context = {
            'installed_apps': self.installed_apps,
            'dependencies': self.dependencies,
            'middleware_classes': self.middleware_classes,
            'settings': self.settings,
            'urls': self.urls,
        }
        return context

    def ask(self):
        answer = raw_input('%s :: %s | Enable? (Y/n) ' % (self.name, self.description))
        if not answer:
            return True
        return True if answer.lower() == 'y' else False

    def get_files_path(self):
        return join(abspath(dirname(__file__)), self.files)

########NEW FILE########
__FILENAME__ = celery
from mason.bricks.base import BaseBrick


class Celery(BaseBrick):

    name = "Celery"
    description = "Configures django-celery"
    installed_apps = ['djcelery', ]
    dependencies = ['django-celery==3.0.17', ]

    settings = {
        'BROKER_URL':  '"django://"',
        '_RAW': "import djcelery\ndjcelery.setup_loader()"
    }

    def ask(self):
        answer = raw_input('%s :: %s | Enable? (Y/n) ' % (self.name, self.description))
        if not answer or answer.lower() == 'y':
            print "Please enter celery details"
            print "\n"
            broker_url = raw_input("Celery Broker URL [django://]: ")
            if broker_url:
                self.settings['BROKER_URL'] = '"%s"' % broker_url
            return True
        return False

########NEW FILE########
__FILENAME__ = crispy_forms
from mason.bricks.base import BaseBrick


class CrispyForms(BaseBrick):

    name = "Django Crispy Forms"
    description = "Configures Django Crispy Forms"

    installed_apps = ['crispy_forms', ]
    dependencies = ['django-crispy-forms', ]

########NEW FILE########
__FILENAME__ = database
from mason.bricks.base import BaseBrick


class Database(BaseBrick):

    name = "Database"
    description = "Configure the database"

    def ask(self):
        self.databases = {'default': {
            'ENGINE': '',
            'NAME': '',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }}
        answer = raw_input('%s :: %s | Enable? (Y/n) ' % (self.name, self.description))
        if not answer or answer.lower() == 'y':
            print "Please enter database details"
            print "\n"
            self.databases['default']['ENGINE'] = raw_input("ENGINE, enter any one: 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle': ")
            self.databases['default']['NAME'] = raw_input("NAME (path to database file if using sqlite): ")
            if self.databases['default']['ENGINE'] != 'sqlite3':
                self.databases['default']['USER'] = raw_input("USER: ")
                self.databases['default']['PASSWORD'] = raw_input("PASSWORD: ")
                self.databases['default']['HOST'] = raw_input("HOST: ")
                self.databases['default']['PORT'] = raw_input("PORT: ")
            return True
        return False

    def get_context(self):
        context = super(Database, self).get_context()
        context['databases'] = self.databases
        return context

########NEW FILE########
__FILENAME__ = debug_toolbar
from mason.bricks.base import BaseBrick


class DebugToolbar(BaseBrick):

    name = "Django Debug Toolbar"
    description = "Configures Django Debug Toolbar"

    installed_apps = ['debug_toolbar', ]
    dependencies = ['django-debug-toolbar', ]
    middleware_classes = ['debug_toolbar.middleware.DebugToolbarMiddleware', ]

    settings = {
        'INTERNAL_IPS': ('127.0.0.1', )
    }

########NEW FILE########
__FILENAME__ = disqus
from mason.bricks.base import BaseBrick


class Disqus(BaseBrick):

    name = "Django Disqus"
    description = "Configures Django Disqus"
    installed_apps = ['disqus', ]
    dependencies = ['django-disqus', ]

    settings = {
        'DISQUS_API_KEY': None,
        'DISQUS_WEBSITE_SHORTNAME': None,
    }

    def ask(self):
        answer = raw_input('%s :: %s | Enable? (Y/n) ' % (self.name, self.description))
        if not answer or answer.lower() == 'y':
            print "Please enter Disqus API key\n"
            self.settings['DISQUS_API_KEY'] = raw_input("API KEY: ")

            print "Please enter Disqus website shortname\n"
            self.settings['DISQUS_WEBSITE_SHORTNAME'] = raw_input("Short Name: ")
            return True
        return False


########NEW FILE########
__FILENAME__ = fabfile
from os.path import join, abspath, dirname

from mason.bricks.base import BaseBrick


class Fabfile(BaseBrick):

    name = "Fabfile"
    description = "Adds a fabfile to your project root"

    dependencies = ['Fabric']

    files = join(abspath(dirname(__file__)), 'files')

########NEW FILE########
__FILENAME__ = fabfile
import os
import re
import sys
from functools import wraps
from getpass import getpass, getuser
from glob import glob
from contextlib import contextmanager

from fabric.api import env, cd, prefix, sudo as _sudo, run as _run, hide, task
from fabric.contrib.files import exists, upload_template
from fabric.colors import yellow, green, blue, red


################
# Config setup #
################

conf = {}
if sys.argv[0].split(os.sep)[-1] == "fab":
    # Ensure we import settings from the current dir
    try:
        conf = __import__("settings", globals(), locals(), [], 0).FABRIC
        try:
            conf["HOSTS"][0]
        except (KeyError, ValueError):
            raise ImportError
    except (ImportError, AttributeError):
        print "Aborting, no hosts defined."
        exit()

env.db_pass = conf.get("DB_PASS", None)
env.admin_pass = conf.get("ADMIN_PASS", None)
env.user = conf.get("SSH_USER", getuser())
env.password = conf.get("SSH_PASS", None)
env.key_filename = conf.get("SSH_KEY_PATH", None)
env.hosts = conf.get("HOSTS", [])

env.proj_name = conf.get("PROJECT_NAME", os.getcwd().split(os.sep)[-1])
env.venv_home = conf.get("VIRTUALENV_HOME", "/home/%s" % env.user)
env.venv_path = "%s/%s" % (env.venv_home, env.proj_name)
env.proj_dirname = "project"
env.proj_path = "%s/%s" % (env.venv_path, env.proj_dirname)
env.manage = "%s/bin/python %s/project/manage.py" % (env.venv_path,
                                                     env.venv_path)
env.live_host = conf.get("LIVE_HOSTNAME", env.hosts[0] if env.hosts else None)
env.repo_url = conf.get("REPO_URL", "")
env.git = env.repo_url.startswith("git") or env.repo_url.endswith(".git")
env.reqs_path = conf.get("REQUIREMENTS_PATH", None)
env.gunicorn_port = conf.get("GUNICORN_PORT", 8000)
env.locale = conf.get("LOCALE", "en_US.UTF-8")


##################
# Template setup #
##################

# Each template gets uploaded at deploy time, only if their
# contents has changed, in which case, the reload command is
# also run.

templates = {
    "nginx": {
        "local_path": "deploy/nginx.conf",
        "remote_path": "/etc/nginx/sites-enabled/%(proj_name)s.conf",
        "reload_command": "service nginx restart",
    },
    "supervisor": {
        "local_path": "deploy/supervisor.conf",
        "remote_path": "/etc/supervisor/conf.d/%(proj_name)s.conf",
        "reload_command": "supervisorctl reload",
    },
    "cron": {
        "local_path": "deploy/crontab",
        "remote_path": "/etc/cron.d/%(proj_name)s",
        "owner": "root",
        "mode": "600",
    },
    "gunicorn": {
        "local_path": "deploy/gunicorn.conf.py",
        "remote_path": "%(proj_path)s/gunicorn.conf.py",
    },
    "settings": {
        "local_path": "deploy/live_settings.py",
        "remote_path": "%(proj_path)s/local_settings.py",
    },
}


######################################
# Context for virtualenv and project #
######################################

@contextmanager
def virtualenv():
    """
    Runs commands within the project's virtualenv.
    """
    with cd(env.venv_path):
        with prefix("source %s/bin/activate" % env.venv_path):
            yield


@contextmanager
def project():
    """
    Runs commands within the project's directory.
    """
    with virtualenv():
        with cd(env.proj_dirname):
            yield


@contextmanager
def update_changed_requirements():
    """
    Checks for changes in the requirements file across an update,
    and gets new requirements if changes have occurred.
    """
    reqs_path = os.path.join(env.proj_path, env.reqs_path)
    get_reqs = lambda: run("cat %s" % reqs_path, show=False)
    old_reqs = get_reqs() if env.reqs_path else ""
    yield
    if old_reqs:
        new_reqs = get_reqs()
        if old_reqs == new_reqs:
            # Unpinned requirements should always be checked.
            for req in new_reqs.split("\n"):
                if req.startswith("-e"):
                    if "@" not in req:
                        # Editable requirement without pinned commit.
                        break
                elif req.strip() and not req.startswith("#"):
                    if not set(">=<") & set(req):
                        # PyPI requirement without version.
                        break
            else:
                # All requirements are pinned.
                return
        pip("-r %s/%s" % (env.proj_path, env.reqs_path))


###########################################
# Utils and wrappers for various commands #
###########################################

def _print(output):
    print
    print output
    print


def print_command(command):
    _print(blue("$ ", bold=True) +
           yellow(command, bold=True) +
           red(" ->", bold=True))


@task
def run(command, show=True):
    """
    Runs a shell comand on the remote server.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _run(command)


@task
def sudo(command, show=True):
    """
    Runs a command as sudo.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _sudo(command)


def log_call(func):
    @wraps(func)
    def logged(*args, **kawrgs):
        header = "-" * len(func.__name__)
        _print(green("\n".join([header, func.__name__, header]), bold=True))
        return func(*args, **kawrgs)
    return logged


def get_templates():
    """
    Returns each of the templates with env vars injected.
    """
    injected = {}
    for name, data in templates.items():
        injected[name] = dict([(k, v % env) for k, v in data.items()])
    return injected


def upload_template_and_reload(name):
    """
    Uploads a template only if it has changed, and if so, reload a
    related service.
    """
    template = get_templates()[name]
    local_path = template["local_path"]
    remote_path = template["remote_path"]
    reload_command = template.get("reload_command")
    owner = template.get("owner")
    mode = template.get("mode")
    remote_data = ""
    if exists(remote_path):
        with hide("stdout"):
            remote_data = sudo("cat %s" % remote_path, show=False)
    with open(local_path, "r") as f:
        local_data = f.read()
        # Escape all non-string-formatting-placeholder occurrences of '%':
        local_data = re.sub(r"%(?!\(\w+\)s)", "%%", local_data)
        if "%(db_pass)s" in local_data:
            env.db_pass = db_pass()
        local_data %= env
    clean = lambda s: s.replace("\n", "").replace("\r", "").strip()
    if clean(remote_data) == clean(local_data):
        return
    upload_template(local_path, remote_path, env, use_sudo=True, backup=False)
    if owner:
        sudo("chown %s %s" % (owner, remote_path))
    if mode:
        sudo("chmod %s %s" % (mode, remote_path))
    if reload_command:
        sudo(reload_command)


def db_pass():
    """
    Prompts for the database password if unknown.
    """
    if not env.db_pass:
        env.db_pass = getpass("Enter the database password: ")
    return env.db_pass


@task
def apt(packages):
    """
    Installs one or more system packages via apt.
    """
    return sudo("apt-get install -y -q " + packages)


@task
def pip(packages):
    """
    Installs one or more Python packages within the virtual environment.
    """
    with virtualenv():
        return sudo("pip install %s" % packages)


def postgres(command):
    """
    Runs the given command as the postgres user.
    """
    show = not command.startswith("psql")
    return run("sudo -u root sudo -u postgres %s" % command, show=show)


@task
def psql(sql, show=True):
    """
    Runs SQL against the project's database.
    """
    out = postgres('psql -c "%s"' % sql)
    if show:
        print_command(sql)
    return out


@task
def backup(filename):
    """
    Backs up the database.
    """
    return postgres("pg_dump -Fc %s > %s" % (env.proj_name, filename))


@task
def restore(filename):
    """
    Restores the database.
    """
    return postgres("pg_restore -c -d %s %s" % (env.proj_name, filename))


@task
def python(code, show=True):
    """
    Runs Python code in the project's virtual environment, with Django loaded.
    """
    setup = "import os; os.environ[\'DJANGO_SETTINGS_MODULE\']=\'settings\';"
    full_code = 'python -c "%s%s"' % (setup, code.replace("`", "\\\`"))
    with project():
        result = run(full_code, show=False)
        if show:
            print_command(code)
    return result


def static():
    """
    Returns the live STATIC_ROOT directory.
    """
    return python("from django.conf import settings;"
                  "print settings.STATIC_ROOT").split("\n")[-1]


@task
def manage(command):
    """
    Runs a Django management command.
    """
    return run("%s %s" % (env.manage, command))


#########################
# Install and configure #
#########################

@task
@log_call
def install():
    """
    Installs the base system and Python requirements for the entire server.
    """
    locale = "LC_ALL=%s" % env.locale
    with hide("stdout"):
        if locale not in sudo("cat /etc/default/locale"):
            sudo("update-locale %s" % locale)
            run("exit")
    sudo("apt-get update -y -q")
    apt("nginx libjpeg-dev python-dev python-setuptools git-core "
        "postgresql libpq-dev memcached supervisor")
    sudo("easy_install pip")
    sudo("pip install virtualenv mercurial")


@task
@log_call
def create():
    """
    Create a new virtual environment for a project.
    Pulls the project's repo from version control, adds system-level
    configs for the project, and initialises the database with the
    live host.
    """

    # Create virtualenv
    with cd(env.venv_home):
        if exists(env.proj_name):
            prompt = raw_input("\nVirtualenv exists: %s\nWould you like "
                               "to replace it? (yes/no) " % env.proj_name)
            if prompt.lower() != "yes":
                print "\nAborting!"
                return False
            remove()
        run("virtualenv %s --distribute" % env.proj_name)
        vcs = "git" if env.git else "hg"
        run("%s clone %s %s" % (vcs, env.repo_url, env.proj_path))

    # Create DB and DB user.
    pw = db_pass()
    user_sql_args = (env.proj_name, pw.replace("'", "\'"))
    user_sql = "CREATE USER %s WITH ENCRYPTED PASSWORD '%s';" % user_sql_args
    psql(user_sql, show=False)
    shadowed = "*" * len(pw)
    print_command(user_sql.replace("'%s'" % pw, "'%s'" % shadowed))
    psql("CREATE DATABASE %s WITH OWNER %s ENCODING = 'UTF8' "
         "LC_CTYPE = '%s' LC_COLLATE = '%s' TEMPLATE template0;" %
         (env.proj_name, env.proj_name, env.locale, env.locale))

    # Set up SSL certificate.
    conf_path = "/etc/nginx/conf"
    if not exists(conf_path):
        sudo("mkdir %s" % conf_path)
    with cd(conf_path):
        crt_file = env.proj_name + ".crt"
        key_file = env.proj_name + ".key"
        if not exists(crt_file) and not exists(key_file):
            try:
                crt_local, = glob(os.path.join("deploy", "*.crt"))
                key_local, = glob(os.path.join("deploy", "*.key"))
            except ValueError:
                parts = (crt_file, key_file, env.live_host)
                sudo("openssl req -new -x509 -nodes -out %s -keyout %s "
                     "-subj '/CN=%s' -days 3650" % parts)
            else:
                upload_template(crt_local, crt_file, use_sudo=True)
                upload_template(key_local, key_file, use_sudo=True)

    # Set up project.
    upload_template_and_reload("settings")
    with project():
        if env.reqs_path:
            pip("-r %s/%s" % (env.proj_path, env.reqs_path))
        pip("gunicorn setproctitle south psycopg2 "
            "django-compressor python-memcached")
        manage("createdb --noinput --nodata")
        python("from django.conf import settings;"
               "from django.contrib.sites.models import Site;"
               "site, _ = Site.objects.get_or_create(id=settings.SITE_ID);"
               "site.domain = '" + env.live_host + "';"
               "site.save();")
        if env.admin_pass:
            pw = env.admin_pass
            user_py = ("from mezzanine.utils.models import get_user_model;"
                       "User = get_user_model();"
                       "u, _ = User.objects.get_or_create(username='admin');"
                       "u.is_staff = u.is_superuser = True;"
                       "u.set_password('%s');"
                       "u.save();" % pw)
            python(user_py, show=False)
            shadowed = "*" * len(pw)
            print_command(user_py.replace("'%s'" % pw, "'%s'" % shadowed))

    return True


@task
@log_call
def remove():
    """
    Blow away the current project.
    """
    if exists(env.venv_path):
        sudo("rm -rf %s" % env.venv_path)
    for template in get_templates().values():
        remote_path = template["remote_path"]
        if exists(remote_path):
            sudo("rm %s" % remote_path)
    psql("DROP DATABASE %s;" % env.proj_name)
    psql("DROP USER %s;" % env.proj_name)


##############
# Deployment #
##############

@task
@log_call
def restart():
    """
    Restart gunicorn worker processes for the project.
    """
    pid_path = "%s/gunicorn.pid" % env.proj_path
    if exists(pid_path):
        sudo("kill -HUP `cat %s`" % pid_path)
    else:
        start_args = (env.proj_name, env.proj_name)
        sudo("supervisorctl start %s:gunicorn_%s" % start_args)


@task
@log_call
def deploy():
    """
    Deploy latest version of the project.
    Check out the latest version of the project from version
    control, install new requirements, sync and migrate the database,
    collect any new static assets, and restart gunicorn's work
    processes for the project.
    """
    if not exists(env.venv_path):
        prompt = raw_input("\nVirtualenv doesn't exist: %s\nWould you like "
                           "to create it? (yes/no) " % env.proj_name)
        if prompt.lower() != "yes":
            print "\nAborting!"
            return False
        create()
    for name in get_templates():
        upload_template_and_reload(name)
    with project():
        backup("last.db")
        static_dir = static()
        if exists(static_dir):
            run("tar -cf last.tar %s" % static_dir)
        git = env.git
        last_commit = "git rev-parse HEAD" if git else "hg id -i"
        run("%s > last.commit" % last_commit)
        with update_changed_requirements():
            run("git pull origin master -f" if git else "hg pull && hg up -C")
        manage("collectstatic -v 0 --noinput")
        manage("syncdb --noinput")
        manage("migrate --noinput")
    restart()
    return True


@task
@log_call
def rollback():
    """
    Reverts project state to the last deploy.
    When a deploy is performed, the current state of the project is
    backed up. This includes the last commit checked out, the database,
    and all static files. Calling rollback will revert all of these to
    their state prior to the last deploy.
    """
    with project():
        with update_changed_requirements():
            update = "git checkout" if env.git else "hg up -C"
            run("%s `cat last.commit`" % update)
        with cd(os.path.join(static(), "..")):
            run("tar -xf %s" % os.path.join(env.proj_path, "last.tar"))
        restore("last.db")
    restart()


@task
@log_call
def all():
    """
    Installs everything required on a new system and deploy.
    From the base software, up to the deployed project.
    """
    install()
    if create():
        deploy()

########NEW FILE########
__FILENAME__ = grappelli
from mason.bricks.admin import Admin


class Grappelli(Admin):

    name = "Django Grappelli"
    description = "Configures Django Grappelli"

    installed_apps = ['grappelli'] + Admin.installed_apps
    dependencies = ['django-grappelli', ]

    urls = Admin.urls + ["(r'^grappelli/', include('grappelli.urls'))"]

########NEW FILE########
__FILENAME__ = guardian
from mason.bricks.base import BaseBrick


class Guardian(BaseBrick):

    name = "Django Guardian"
    description = "Configures Django Guardian"

    installed_apps = ['guardian', ]
    dependencies = ['django-guardian', ]

    settings = {
        'ANONYMOUS_USER_ID': -1,
        'AUTHENTICATION_BACKENDS': (
            'django.contrib.auth.backends.ModelBackend', # default
            'guardian.backends.ObjectPermissionBackend',
        )
    }

########NEW FILE########
__FILENAME__ = parsley
from mason.bricks.base import BaseBrick


class Parsley(BaseBrick):

    name = "Parsley"
    description = "Enables Parsley"

    installed_apps = ['parsley', ]
    dependencies = ['django-parsley', ]

########NEW FILE########
__FILENAME__ = sentry
from mason.bricks.base import BaseBrick


class Sentry(BaseBrick):

    name = "Sentry"
    description = "Configures sentry"
    installed_apps = ['raven.contrib.django.raven_compat']
    dependencies = ['raven']

    settings = {
        'RAVEN_CONFIG': {'dsn': None}
    }

    def ask(self):
        answer = raw_input('%s :: %s | Enable? (Y/n) ' % (self.name, self.description))
        if not answer or answer.lower() == 'y':
            print "Please enter sentry details"
            print "\n"
            self.settings['RAVEN_CONFIG']['dsn'] = raw_input("Sentry DSN: ")
            return True
        return False

########NEW FILE########
__FILENAME__ = south
from mason.bricks.base import BaseBrick


class South(BaseBrick):

    name = "South"
    description = "Enables south"

    installed_apps = ['south', ]
    dependencies = ['south', ]

########NEW FILE########
__FILENAME__ = travis
from os.path import join, abspath, dirname

from mason.bricks.base import BaseBrick


class Travis(BaseBrick):

    name = "Travis"
    description = "Configure travis CI integration"
    files = join(abspath(dirname(__file__)), 'files')

    def ask(self):
        self.travis = {
            'script': 'python manage.py test',
            'install': 'pip install -r requirements.txt'
        }
        answer = raw_input('%s :: %s | Enable? (Y/n) ' % (self.name, self.description))
        if not answer or answer.lower() == 'y':
            print "Please enter travis CI details"
            print "\n"
            script = raw_input("script - Command to run the tests [python manage.py test]: ")
            if script:
                self.travis['script'] = script
            install = raw_input("install - Command to install dependencies [pip install -r requirements]: ")
            if install:
                self.travis['install'] = install
            return True
        return False

    def get_context(self):
        context = super(Travis, self).get_context()
        context['travis'] = self.travis
        return context

########NEW FILE########
__FILENAME__ = conf
PLUGINS = (
    'mason.bricks.database.Database',
    'mason.bricks.admin.Admin',
    'mason.bricks.grappelli.Grappelli',
    'mason.bricks.guardian.Guardian',
    'mason.bricks.south.South',
    'mason.bricks.debug_toolbar.DebugToolbar',
    'mason.bricks.fabfile.fabfile.Fabfile',
    'mason.bricks.sentry.Sentry',
    'mason.bricks.parsley.Parsley',
    'mason.bricks.travis.travis.Travis',
    'mason.bricks.crispy_forms.CrispyForms',
    'mason.bricks.disqus.Disqus',
    'mason.bricks.celery.Celery',
)

########NEW FILE########
__FILENAME__ = generate
import cgi
import errno
import mimetypes
import os
import posixpath
import re
import shutil
import stat
import sys
import tempfile
try:
    from urllib.request import urlretrieve
except ImportError:     # Python 2
    from urllib import urlretrieve

from optparse import make_option
from optparse import OptionParser, NO_DEFAULT
from os import path

from mako.template import Template
from mako import exceptions

import django
from django.utils import archive
from django.utils._os import rmtree_errorhandler
from django.utils.crypto import get_random_string
from django.utils.importlib import import_module
from django.core.management.base import BaseCommand, CommandError
from django.core.management.commands.makemessages import handle_extensions


_drive_re = re.compile('^([a-z]):', re.I)
_url_drive_re = re.compile('^([a-z])[:|]', re.I)


class TemplateCommand(BaseCommand):
    """
    Copies either a Django application layout template or a Django project
    layout template into the specified directory.

    :param style: A color style object (see django.core.management.color).
    :param app_or_project: The string 'app' or 'project'.
    :param name: The name of the application or project.
    :param directory: The directory to which the template should be copied.
    :param options: The additional variables passed to project or app templates
    """
    args = "[name] [optional destination directory]"
    option_list = BaseCommand.option_list + (
        make_option('--template',
                    action='store', dest='template',
                    help='The dotted import path to load the template from.'),
        make_option('--extension', '-e', dest='extensions',
                    action='append', default=['py'],
                    help='The file extension(s) to render (default: "py"). '
                         'Separate multiple extensions with commas, or use '
                         '-e multiple times.'),
        make_option('--name', '-n', dest='files',
                    action='append', default=[],
                    help='The file name(s) to render. '
                         'Separate multiple extensions with commas, or use '
                         '-n multiple times.')
        )
    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = False
    # The supported URL schemes
    url_schemes = ['http', 'https', 'ftp']

    def handle(self, app_or_project, target=None, **options):
        self.app_or_project = app_or_project
        self.paths_to_remove = []
        self.verbosity = int(options.get('verbosity'))

        top_dir = path.join(os.getcwd(), target)
        try:
            os.makedirs(top_dir)
        except OSError as e:
            if e.errno == errno.EEXIST:
                message = "'%s' already exists" % top_dir
            else:
                message = e
            raise CommandError(message)

        extensions = tuple(
            handle_extensions(options.get('extensions'), ignored=()))
        extra_files = []
        for file in options.get('files'):
            extra_files.extend(map(lambda x: x.strip(), file.split(',')))
        if self.verbosity >= 2:
            self.stdout.write("Rendering %s template files with "
                              "extensions: %s\n" %
                              (app_or_project, ', '.join(extensions)))
            self.stdout.write("Rendering %s template files with "
                              "filenames: %s\n" %
                              (app_or_project, ', '.join(extra_files)))

        base_subdir = '%s_template' % app_or_project
        base_directory = '%s_directory' % app_or_project

        context = dict(options, **{
            base_directory: top_dir,
        })

        # Setup a stub settings environment for template rendering
        from django.conf import settings
        if not settings.configured:
            settings.configure()

        project_template_dir = self.handle_template(options.get('template'),
                                            base_subdir)
        plugins = options.get('plugins')
        plugin_dirs = [plugin.files for plugin in plugins if plugin.files]
        template_dirs = [project_template_dir] + plugin_dirs
        for template_dir in template_dirs:
            for root, dirs, files in os.walk(template_dir):

                prefix_length = len(template_dir) + 1
                path_rest = root[prefix_length:]
                relative_dir = path_rest
                if relative_dir:
                    target_dir = path.join(top_dir, relative_dir)
                    if not path.exists(target_dir):
                        os.mkdir(target_dir)

                for dirname in dirs[:]:
                    if dirname.startswith('.') or dirname == '__pycache__':
                        dirs.remove(dirname)

                for filename in files:
                    if filename.endswith(('.pyo', '.pyc', '.py.class')):
                        # Ignore some files as they cause various breakages.
                        continue
                    old_path = path.join(root, filename)
                    new_path = path.join(top_dir, relative_dir, filename)
                    if path.exists(new_path):
                        raise CommandError("%s already exists, overlaying a "
                                        "project or app into an existing "
                                        "directory won't replace conflicting "
                                        "files" % new_path)

                    # Only render the Python files, as we don't want to
                    # accidentally render Django templates files
                    with open(old_path, 'rb') as template_file:
                        content = template_file.read()
                    if filename.endswith(extensions) or filename in extra_files:
                        content = content.decode('utf-8')
                        template = Template(content)
                        try:
                            content = template.render(**context)
                        except:
                            print exceptions.text_error_template().render()
                        content = content.encode('utf-8')
                    with open(new_path, 'wb') as new_file:
                        new_file.write(content)

                    if self.verbosity >= 2:
                        self.stdout.write("Creating %s\n" % new_path)
                    try:
                        shutil.copymode(old_path, new_path)
                        self.make_writeable(new_path)
                    except OSError:
                        self.stderr.write(
                            "Notice: Couldn't set permission bits on %s. You're "
                            "probably using an uncommon filesystem setup. No "
                            "problem." % new_path, self.style.NOTICE)

        if self.paths_to_remove:
            if self.verbosity >= 2:
                self.stdout.write("Cleaning up temporary files.\n")
            for path_to_remove in self.paths_to_remove:
                if path.isfile(path_to_remove):
                    os.remove(path_to_remove)
                else:
                    shutil.rmtree(path_to_remove,
                                  onerror=rmtree_errorhandler)

    def handle_template(self, template, subdir):
        """
        Determines where the app or project templates are.
        Use django.__path__[0] as the default because we don't
        know into which directory Django has been installed.
        """
        if template is None:
            return path.join(django.__path__[0], 'conf', subdir)
        else:
            if template.startswith('file://'):
                template = template[7:]
            expanded_template = path.expanduser(template)
            expanded_template = path.normpath(expanded_template)
            if path.isdir(expanded_template):
                return expanded_template
            if self.is_url(template):
                # downloads the file and returns the path
                absolute_path = self.download(template)
            else:
                absolute_path = path.abspath(expanded_template)
            if path.exists(absolute_path):
                return self.extract(absolute_path)

        raise CommandError("couldn't handle %s template %s." %
                           (self.app_or_project, template))

    def download(self, url):
        """
        Downloads the given URL and returns the file name.
        """
        def cleanup_url(url):
            tmp = url.rstrip('/')
            filename = tmp.split('/')[-1]
            if url.endswith('/'):
                display_url  = tmp + '/'
            else:
                display_url = url
            return filename, display_url

        prefix = 'django_%s_template_' % self.app_or_project
        tempdir = tempfile.mkdtemp(prefix=prefix, suffix='_download')
        self.paths_to_remove.append(tempdir)
        filename, display_url = cleanup_url(url)

        if self.verbosity >= 2:
            self.stdout.write("Downloading %s\n" % display_url)
        try:
            the_path, info = urlretrieve(url, path.join(tempdir, filename))
        except IOError as e:
            raise CommandError("couldn't download URL %s to %s: %s" %
                               (url, filename, e))

        used_name = the_path.split('/')[-1]

        # Trying to get better name from response headers
        content_disposition = info.get('content-disposition')
        if content_disposition:
            _, params = cgi.parse_header(content_disposition)
            guessed_filename = params.get('filename') or used_name
        else:
            guessed_filename = used_name

        # Falling back to content type guessing
        ext = self.splitext(guessed_filename)[1]
        content_type = info.get('content-type')
        if not ext and content_type:
            ext = mimetypes.guess_extension(content_type)
            if ext:
                guessed_filename += ext

        # Move the temporary file to a filename that has better
        # chances of being recognnized by the archive utils
        if used_name != guessed_filename:
            guessed_path = path.join(tempdir, guessed_filename)
            shutil.move(the_path, guessed_path)
            return guessed_path

        # Giving up
        return the_path

    def splitext(self, the_path):
        """
        Like os.path.splitext, but takes off .tar, too
        """
        base, ext = posixpath.splitext(the_path)
        if base.lower().endswith('.tar'):
            ext = base[-4:] + ext
            base = base[:-4]
        return base, ext

    def extract(self, filename):
        """
        Extracts the given file to a temporarily and returns
        the path of the directory with the extracted content.
        """
        prefix = 'django_%s_template_' % self.app_or_project
        tempdir = tempfile.mkdtemp(prefix=prefix, suffix='_extract')
        self.paths_to_remove.append(tempdir)
        if self.verbosity >= 2:
            self.stdout.write("Extracting %s\n" % filename)
        try:
            archive.extract(filename, tempdir)
            return tempdir
        except (archive.ArchiveException, IOError) as e:
            raise CommandError("couldn't extract file %s to %s: %s" %
                               (filename, tempdir, e))

    def is_url(self, template):
        """
        Returns True if the name looks like a URL
        """
        if ':' not in template:
            return False
        scheme = template.split(':', 1)[0].lower()
        return scheme in self.url_schemes

    def make_writeable(self, filename):
        """
        Make sure that the file is writeable.
        Useful if our source is read-only.
        """
        if sys.platform.startswith('java'):
            # On Jython there is no os.access()
            return
        if not os.access(filename, os.W_OK):
            st = os.stat(filename)
            new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
            os.chmod(filename, new_permissions)


class Command(TemplateCommand):
    help = ("Creates a Django project directory structure for the given "
            "project name in the current directory or optionally in the "
            "given directory.")

    def handle(self, target=None, *args, **options):
        defaults = {}
        for opt in self.option_list:
            if opt.default is NO_DEFAULT:
                defaults[opt.dest] = None
            else:
                defaults[opt.dest] = opt.default
        defaults.update(options)
        super(Command, self).handle('project', target, **defaults)

########NEW FILE########
__FILENAME__ = startproject
from optparse import NO_DEFAULT

from django.core.management.commands.startproject import Command as StartProjectCommand


class Command(StartProjectCommand):

    def handle(self, target=None, *args, **options):
        defaults = {}
        for opt in self.option_list:
            if opt.default is NO_DEFAULT:
                defaults[opt.dest] = None
            else:
                defaults[opt.dest] = opt.default
        defaults.update(options)
        super(Command, self).handle(project_name=target, **defaults)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for {{ project_name }} project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    % if databases is UNDEFINED:
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
    % else:
    'default': {
        'ENGINE': 'django.db.backends.${databases['default']['ENGINE']}',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '${databases['default']['NAME']}',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '${databases['default']['USER']}',
        'PASSWORD': '${databases['default']['PASSWORD']}',
        'HOST': '${databases['default']['HOST']}',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '${databases['default']['PORT']}',                      # Set to empty string for default.
    }
    % endif
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
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '{{ secret_key }}'

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
    % if middleware_classes is not UNDEFINED:
    % for klass in middleware_classes:
    '${klass}',
    % endfor
    % endif
)

ROOT_URLCONF = '{{ project_name }}.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = '{{ project_name }}.wsgi.application'

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
    % if installed_apps is not UNDEFINED:
    % for app in installed_apps:
    '${app}',
    % endfor
    % endif
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

% if settings is not UNDEFINED and settings:
% for key, value in settings.items():
% if key == "_RAW":
${value}
% else:
${key} = ${value}
% endif
% endfor
% endif

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

% if 'Admin' in plugin_names or 'Django Grappelli' in plugin_names:
from django.contrib import admin
admin.autodiscover()
% endif

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', '{{ project_name }}.views.home', name='home'),
    # url(r'^{{ project_name }}/', include('{{ project_name }}.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),

    % if not urls is UNDEFINED:
    % for url in urls:
    ${url},
    % endfor
    % endif
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for {{ project_name }} project.

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
# os.environ["DJANGO_SETTINGS_MODULE"] = "{{ project_name }}.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = foobar
from mason.bricks.base import BaseBrick


class FooBarBrick(BaseBrick):

    name = "FooBar"
    description = "Configures FooBar"

    installed_apps = ["foobar"]
    dependencies = ["foobar"]
    middleware_classes = ["foobar.middleware.FooBar"]
    settings = {"FOO": "bar"}
    files = "foobar_files"
    urls = ["url(r'^admin/', include(admin.site.urls))"]

########NEW FILE########
__FILENAME__ = test_base
from mason.tests.bricks.foobar import FooBarBrick


class TestBaseBrick:

    def setup_method(self, method):
        self.brick = FooBarBrick()

    def test_context(self):
        assert self.brick.get_context() == {
            'dependencies': ['foobar'],
            'installed_apps': ['foobar'],
            'middleware_classes': ['foobar.middleware.FooBar'],
            'settings': {'FOO': 'bar'},
            'urls': ["url(r'^admin/', include(admin.site.urls))"]
        }

    def test_files_path(self):
        assert self.brick.get_files_path().endswith('foobar_files')

########NEW FILE########
