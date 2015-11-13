__FILENAME__ = app
import datetime
from fabric.api import *
from fabric.contrib.files import exists
import os
from .tasks import restart
from .utils import upload_dir

__all__ = ['deploy', 'build', 'upload', 'versions', 'update_version']

# The definition of your apps as a dictionary. This can have four keys:
#
# - repo (required): A Git URL of the repo that contains your app
# - role (required): The role of the hosts that this app will be uploaded to
# - build: A script to run locally before uploading (e.g. to build static assets)
# - init: The name of the upstart script to start/restart after uploading
#
# Example:
#
# env.app_root = "/apps"
# env.apps['api'] = {
#   "repo": "https://user:pass@github.com/mycompany/mycompany-api.git",
#   "role": "api",
#   "build": "script/build",
#   "init": "api",
# }
env.apps = {}

# The directory that contains your apps
env.app_root = '/home/ubuntu'

@task
def deploy(app, commit='origin/master'):
    """
    Build and upload an app.
    """
    kwargs = {}
    # If no hosts have been set by the user, default to this app's role
    if not env.hosts:
        kwargs['role'] = env.apps[app]['role']

    execute(build, app, commit)
    version = datetime.datetime.now().replace(microsecond=0).isoformat().replace(':', '-')
    execute(upload, app, version, **kwargs) 
    execute(update_version, app, version, **kwargs)

@task
@runs_once
def build(app, commit='origin/master'):
    """
    Build the code for an app locally
    """
    # Set up build directory
    if not os.path.exists('build'):
        local('mkdir build')
    path = 'build/%s' % app

    # Fetch or clone repo
    if os.path.exists(path):
        with lcd(path):
            local('git fetch')
    else:
        local('git clone "%s" "build/%s"' % (env.apps[app]['repo'], app))
    with lcd(path):
        local('git checkout %s' % commit)

    # Run build command (e.g., "script/build")
    if env.apps[app].get('build'):
        with lcd(path):
            local(env.apps[app]['build'])

def _versions(app):
    return sudo('ls "%s"' % os.path.join(env.app_root, app+'-versions')).split()

def _current_version_path(app):
    return sudo('readlink "%s"' % os.path.join(env.app_root, app))

@task
def versions(app):
    """
    Print the versions of an app that are available
    """
    print '\n'.join(_versions(app))

@task
def update_version(app, version):
    """
    Switch the symlink for an app to point at a new version and restart its init script
    """
    symlink = os.path.join(env.app_root, app)
    version_path = os.path.join(env.app_root, app+'-versions', version)
    sudo('ln -sfn "%s" "%s"' % (version_path, symlink))

    # Restart with upstart
    if env.apps[app].get('init'):
        restart(env.apps[app]['init'])

@task
@parallel
def upload(app, version):
    """
    Upload the code for a version
    """
    all_versions_path = os.path.join(env.app_root, app+'-versions')
    current_version_path = _current_version_path(app)
    version_path = os.path.join(all_versions_path, version)

    if not exists(all_versions_path):
        sudo('mkdir "%s"' % all_versions_path)

    # Copy existing code if it exists
    if exists(os.path.join(env.app_root, app)):
        sudo('cp -a "%s" "%s"' % (current_version_path, version_path))

    # Upload new code
    upload_dir('build/%s/*' % app, version_path, use_sudo=True)

    # Run post-upload
    if env.apps[app].get('post-upload'):
        with cd(version_path):
            sudo(env.apps[app].get('post-upload'))




########NEW FILE########
__FILENAME__ = config
from fabric.api import env, run, settings, hide

# Default system user
env.user = 'ubuntu'

# Default puppet environment
env.environment = 'prod'

# Default puppet module directory
env.puppet_module_dir = 'modules/'

# Default puppet version
# If loom_puppet_version is None, loom installs the latest version
env.loom_puppet_version = '3.1.1'

# Default librarian version
# If loom_librarian_version is None, loom installs the latest version
env.loom_librarian_version = '0.9.9'


def host_roles(host_string):
    """
    Returns the role of a given host string.
    """
    roles = set()
    for role, hosts in env.roledefs.items():
        if host_string in hosts:
            roles.add(role)
    return list(roles)


def current_roles():
    return host_roles(env.host_string)


def has_puppet_installed():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        result = run('which puppet')
    return result.succeeded


def has_librarian_installed():
    with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
        librarian = run('which librarian-puppet')
    return librarian.succeeded

########NEW FILE########
__FILENAME__ = decorators
from fabric.api import abort, env
from functools import wraps
from .config import has_puppet_installed, has_librarian_installed


REQUIRES_GEM = 'Host "{host}" does not have {gem} installed. Try "fab puppet.install".'


def requires_puppet(func):

    @wraps(func)
    def _requires_puppet(*args, **kwargs):
        if not has_puppet_installed():
            abort(REQUIRES_GEM.format(host=env.host_string, gem='puppet'))
        if not has_librarian_installed():
            abort(REQUIRES_GEM.format(host=env.host_string, gem='librarian-puppet'))
        func(*args, **kwargs)

    return _requires_puppet

########NEW FILE########
__FILENAME__ = puppet
from fabric.api import env, abort, put, cd, sudo, task, execute
from fabric.contrib.files import upload_template
from StringIO import StringIO
import os
from .config import current_roles, has_puppet_installed, has_librarian_installed
from .decorators import requires_puppet
from .tasks import restart
from .utils import upload_dir

__all__ = ['update', 'update_configs', 'install', 'install_master', 'install_agent', 'apply', 'force']

files_path = os.path.join(os.path.dirname(__file__), 'files')


def get_puppetmaster_host():
    if env.get('puppetmaster_host'):
        return env['puppetmaster_host']
    if 'puppetmaster' in env.roledefs and env.roledefs['puppetmaster']:
        return env.roledefs['puppetmaster'][0]


def generate_site_pp():
    site = ''.join('include "roles::%s"\n' % role for role in sorted(current_roles()))
    return site


@task
@requires_puppet
def update():
    """
    Upload puppet modules
    """
    if not current_roles():
        abort('Host "%s" has no roles. Does it exist in this environment?' % env.host_string)

    # Install local modules
    module_dir = env.get('puppet_module_dir', 'modules/')
    if not module_dir.endswith('/'): module_dir+='/'
    upload_dir(module_dir, '/etc/puppet/modules', use_sudo=True)

    # Install vendor modules
    put('Puppetfile', '/etc/puppet/Puppetfile', use_sudo=True)
    with cd('/etc/puppet'):
        sudo('librarian-puppet install --path /etc/puppet/vendor')

    # Install site.pp
    sudo('mkdir -p /etc/puppet/manifests')
    put(StringIO(generate_site_pp()), '/etc/puppet/manifests/site.pp', use_sudo=True)


@task
def update_configs():
    """
    Upload puppet configs and manifests
    """
    sudo('mkdir -p /etc/puppet')
    # Allow the puppet master to automatically sign certificates
    if env.get('loom_puppet_autosign'):
        put(StringIO('*'), '/etc/puppet/autosign.conf', use_sudo=True)
    else:
        put(StringIO(''), '/etc/puppet/autosign.conf', use_sudo=True)

    # Upload Puppet configs
    upload_template(os.path.join(files_path, 'puppet/puppet.conf'), '/etc/puppet/puppet.conf', {
        'server': get_puppetmaster_host() or '',
        'certname': get_puppetmaster_host() or '',
        'dns_alt_names': get_puppetmaster_host() or '',
        'environment': env.environment,
    }, use_sudo=True)
    put(os.path.join(files_path, 'puppet/auth.conf'), '/etc/puppet/auth.conf', use_sudo=True)
    put(os.path.join(files_path, 'puppet/hiera.yaml'), '/etc/puppet/hiera.yaml', use_sudo=True)


def _gem_install(gem, version=None):
    version = '-v {version}'.format(version=version) if version else ''
    return ' '.join('gem install {gem} {version} --no-ri --no-rdoc'.format(gem=gem, version=version).split())

@task
def install():
    """
    Install Puppet and its configs without any agent or master.
    """
    sudo('apt-get update -qq')
    sudo('apt-get -y -q install rubygems git')

    puppet_version = env.get('loom_puppet_version')
    sudo(_gem_install('puppet', version=puppet_version))

    librarian_version = env.get('loom_librarian_version')
    sudo(_gem_install('librarian-puppet', version=librarian_version))

    # http://docs.puppetlabs.com/guides/installation.html
    sudo('puppet resource group puppet ensure=present')
    sudo("puppet resource user puppet ensure=present gid=puppet shell='/sbin/nologin'")
    execute(update_configs)


@task
def install_master():
    """
    Install puppetmaster, update its modules and install agent.
    """
    execute(install_agent)
    execute(update)
    put(os.path.join(files_path, 'init/puppetmaster.conf'), '/etc/init/puppetmaster.conf', use_sudo=True)
    restart('puppetmaster')


@task
def install_agent():
    """
    Install the puppet agent.
    """
    execute(install)
    put(os.path.join(files_path, 'init/puppet.conf'), '/etc/init/puppet.conf', use_sudo=True)
    restart('puppet')


@task
@requires_puppet
def apply():
    """
    Apply puppet locally
    """

    sudo('HOME=/root puppet apply /etc/puppet/manifests/site.pp')


@task
@requires_puppet
def force():
    """
    Force puppet agent run
    """

    sudo('HOME=/root puppet agent --onetime --no-daemonize --verbose --waitforcert 5')

########NEW FILE########
__FILENAME__ = tasks
from fabric.api import *
from fabric.network import parse_host_string
import os
import subprocess

__all__ = ['ssh', 'all', 'uptime', 'upgrade', 'restart', 'reboot']

@task
def all():
    """
    Select all hosts
    """
    host_set = set()
    for hosts in env.roledefs.values():
        host_set.update(hosts)
    # remove dupes
    env.hosts = list(host_set)

@task
def uptime():
    run('uptime')

@task
def upgrade(non_interactive=False):
    """
    Upgrade apt packages
    """
    with settings(hide('stdout'), show('running')):
        sudo('apt-get update')
    upgrade_command = ['apt-get', 'upgrade']
    if non_interactive:
        upgrade_command.append('-y')
    sudo(' '.join(upgrade_command))

@task
def ssh(*cmd):
    """
    Open an interactive ssh session
    """
    run = ['ssh', '-A', '-t']
    if env.key_filename:
        if isinstance(env.key_filename, list):
            key_filename = env.key_filename[0]
        else:
            key_filename = env.key_filename
        run.extend(["-i", os.path.expanduser(key_filename)])
    parsed = parse_host_string(env.host_string)
    if parsed['port']:
        run.extend(['-p', parsed['port']])
    else:
        run.extend(['-p', unicode(env.port)])
    user = parsed['user'] if parsed['user'] else env.user
    run.append('%s@%s' % (parsed['user'] if parsed['user'] else env.user, parsed['host']))
    run += cmd
    subprocess.call(run)

@task
def restart(service):
    """
    Restart or start an upstart service
    """
    with settings(warn_only=True):
        result = sudo('restart %s' % service)
    if result.failed:
        sudo('start %s' % service)

@task
def reboot():
    """
    Reboot a host
    """
    sudo('reboot')



########NEW FILE########
__FILENAME__ = utils
from fabric.api import *
from fabric.contrib.project import rsync_project

def upload_dir(src, dest, use_sudo=False):
    """
    Fabric's rsync_project with some sane settings
    """
    extra_opts = ['--exclude=".git*"', '--copy-links']
    if use_sudo:
        extra_opts.append('--rsync-path="sudo rsync"')
    rsync_project(
        local_dir=src,
        remote_dir=dest,
        delete=True,
        extra_opts=' '.join(extra_opts),
        ssh_opts='-oStrictHostKeyChecking=no'
    )




########NEW FILE########
__FILENAME__ = config_spec
from pspec import describe
from attest import assert_hook
from fabric.api import env
from loom.config import host_roles, current_roles

with describe('loom.config.host_roles'):
    def it_returns_the_role_for_a_host_with_a_single_role():
        env.roledefs = {'app': 'app.example.com'}
        assert host_roles('app.example.com') == ['app']

    def it_returns_the_roles_for_a_host_with_multiple_roles():
        env.roledefs = {
            'app': 'server.example.com',
            'db': 'server.example.com',
        }
        assert host_roles('server.example.com') == ['app', 'db']

    def it_returns_the_role_for_multiple_hosts_with_a_single_role():
        env.roledefs = {'app': ['app1.example.com', 'app2.example.com']}
        assert host_roles('app1.example.com') == ['app']
        assert host_roles('app2.example.com') == ['app']

    def it_returns_the_role_for_multiple_hosts_with_multiple_roles():
        env.roledefs = {
            'app': ['app1.example.com', 'app2.example.com'],
            'db': ['app1.example.com', 'app2.example.com']
        }
        assert host_roles('app1.example.com') == ['app', 'db']
        assert host_roles('app2.example.com') == ['app', 'db']


with describe('loom.config.current_roles'):
    def it_returns_the_roles_for_the_current_host():
        env.roledefs = {'app': 'app.example.com'}
        env.host_string = 'app.example.com'
        assert current_roles() == ['app']



########NEW FILE########
__FILENAME__ = decorators_spec
from pspec import describe
from loom.decorators import requires_puppet, REQUIRES_GEM
from mock import patch
from fabric.api import env

with describe('loom.decorations.requires_puppet'):
    @patch('loom.decorators.has_librarian_installed')
    @patch('loom.decorators.has_puppet_installed')
    def it_does_not_do_anything_if_puppet_and_librarian_are_installed(puppet_mock, librarian_mock):
        env.host_string = 'app.example.com'
        puppet_mock.return_value = True
        librarian_mock.return_value = True

        requires_puppet(lambda: 1)()

        assert puppet_mock.called
        assert librarian_mock.called

    @patch('loom.decorators.has_librarian_installed')
    @patch('loom.decorators.has_puppet_installed')
    @patch('loom.decorators.abort')
    def it_aborts_if_puppet_is_not_installed(abort_mock, puppet_mock, librarian_mock):
        env.host_string = 'app.example.com'
        puppet_mock.return_value = False
        librarian_mock.return_value = True

        requires_puppet(lambda: 1)()

        assert puppet_mock.called
        assert REQUIRES_GEM.format(host=env.host_string, gem='puppet') == abort_mock.call_args[0][0]

    @patch('loom.decorators.has_librarian_installed')
    @patch('loom.decorators.has_puppet_installed')
    @patch('loom.decorators.abort')
    def it_aborts_if_librarian_is_not_installed(abort_mock, puppet_mock, librarian_mock):
        env.host_string = 'app.example.com'
        puppet_mock.return_value = True
        librarian_mock.return_value = False

        requires_puppet(lambda: 1)()

        assert puppet_mock.called
        assert librarian_mock.called
        assert REQUIRES_GEM.format(host=env.host_string, gem='librarian-puppet') == abort_mock.call_args[0][0]



########NEW FILE########
__FILENAME__ = puppet_spec
from pspec import describe
from attest import assert_hook
from fabric.api import env
from loom.puppet import generate_site_pp, get_puppetmaster_host, _gem_install, generate_site_pp
from mock import patch

with describe('loom.puppet.get_puppetmaster_host'):
    def it_returns_env_puppetmaster_host_when_it_is_defined():
        newenv = {'puppetmaster_host': 'master.example.com'}
        with patch.dict('fabric.api.env', newenv):
            assert 'master.example.com' == get_puppetmaster_host()

    def it_returns_the_host_in_the_puppetmaster_role():
        newenv = {'roledefs':
            {'puppetmaster': ['master.example.com']}
        }
        with patch.dict('fabric.api.env', newenv):
            assert 'master.example.com' == get_puppetmaster_host()

    def it_returns_the_first_puppetmaster_host_when_multiple_are_defined():
        newenv = {'roledefs':
            {'puppetmaster': ['master.example.com', 'master2.example.com']}
        }
        with patch.dict('fabric.api.env', newenv):
            assert 'master.example.com' == get_puppetmaster_host()

    def it_returns_none_when_no_puppetmaster_is_defined():
        newenv = {'roledefs':
            {'puppetmaster': []}
        }
        with patch.dict('fabric.api.env', newenv):
            assert None == get_puppetmaster_host()

    def it_returns_none_when_no_roles_are_defined():
        newenv = {'roledefs':{}}
        with patch.dict('fabric.api.env', newenv):
            assert None == get_puppetmaster_host()


with describe('loom.puppet._gem_install'):
    def it_generates_a_gem_install_command_without_a_version():
        assert 'gem install mygem --no-ri --no-rdoc' == _gem_install('mygem')

    def it_generates_a_gem_install_comamnd_with_a_version():
        assert 'gem install mygem -v 3.2.1 --no-ri --no-rdoc' == _gem_install('mygem', '3.2.1')


with describe('loom.puppet.generate_site_pp'):
    def it_creates_an_include_statement_for_each_role_sorted():
        env.roledefs = {
            'app': 'server.example.com',
            'db': 'server.example.com',
            'zapp': 'server.example.com',
        }
        env.host_string = 'server.example.com'

        expected = 'include "roles::app"\ninclude "roles::db"\ninclude "roles::zapp"\n'
        assert generate_site_pp() == expected




########NEW FILE########
__FILENAME__ = tasks_spec
from fabric.api import env
from pspec import describe
from loom.tasks import all, ssh, upgrade
from mock import patch, call

with describe('loom.tasks.all'):
    def it_sets_env_hsots_to_contain_all_hosts_in_roledefs():
        env.roledefs = {
            'app1': ['app1.com', 'app2.com'],
            'app2': ['app1.com', 'app2.com'],
            'db': ['db.com']
        }

        all()

        assert set(['app1.com', 'app2.com', 'db.com']) == set(env.hosts)


with describe('loom.tasks.ssh'):
    @patch('loom.tasks.subprocess')
    def it_calls_ssh(mock):
        env.user = 'user'
        env.host_string = 'example.com'
        env.key_filename = None
        ssh()

        expected = [call('ssh -A -t user@example.com'.split())]
        assert mock.call.call_args_list == expected

    @patch('loom.tasks.subprocess')
    def it_calls_ssh_with_a_key_filename(mock):
        env.user = 'user'
        env.host_string = 'example.com'
        env.key_filename = 'test.pem'
        ssh()

        expected = [call('ssh -A -t -i test.pem user@example.com'.split())]
        assert mock.call.call_args_list == expected

    @patch('loom.tasks.subprocess')
    def it_calls_ssh_with_a_key_filename_list(mock):
        env.user = 'user'
        env.host_string = 'example.com'
        env.key_filename = ['test.pem']
        ssh()

        expected = [call('ssh -A -t -i test.pem user@example.com'.split())]
        assert mock.call.call_args_list == expected

    @patch('loom.tasks.subprocess')
    def it_calls_ssh_with_a_complex_host(mock):
        env.host_string = 'test@example.com:9999'
        env.key_filename = None
        ssh()

        expected = [call('ssh -A -t -p 9999 test@example.com'.split())]
        print mock.call.call_args_list
        assert mock.call.call_args_list == expected


with describe('loom.tasks.upgrade'):
    @patch('loom.tasks.sudo')
    def it_calls_apt_get_upgrade(sudo_mock):

        upgrade()

        expected = [call('apt-get update'), call('apt-get upgrade')]
        assert sudo_mock.call_args_list == expected

    @patch('loom.tasks.sudo')
    def it_calls_apt_get_upgrade_without_prompting_for_confirmation(sudo_mock):

        upgrade(True)

        expected = [call('apt-get update'), call('apt-get upgrade -y')]
        assert sudo_mock.call_args_list == expected



########NEW FILE########
