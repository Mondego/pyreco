__FILENAME__ = aws
"""Methods for interacting with Amazon's cloud servers. Uses the boto library to
connect to their API.
"""
from fabric.api import require, env
from fabric.decorators import runs_once

from buedafab.operations import exists
from buedafab.utils import sha_for_file

def collect_load_balanced_instances():
    """Return the fully-qualified domain names of the servers attached to an
    Elastic Load Balancer.

    Requires the env keys:
        
        load_balancer -- the ID of the load balancer, typically a chosen name
        ec2_connection -- an instance of boto.ec2.EC2Connection (set by default
                            if your shell environment has an AWS_ACCESS_KEY_ID
                            and AWS_SECRET_ACCESS_KEY defined
        elb_connection -- an instance of boto.ec2.elb.ELBConnection (again, set
                            by default if you have the right shell variables)
        env.ssh_port -- the SSH port used by the servers (has a default)
    """

    require('load_balancer')
    require('ec2_connection')
    require('elb_connection')
    instance_states = env.elb_connection.describe_instance_health(
            env.load_balancer)
    ids = []
    for instance in instance_states:
        print("Adding instance %s" % instance.instance_id)
        ids.append(instance.instance_id)
    instances = None
    instance_fqdns = []
    if ids:
        instances = env.ec2_connection.get_all_instances(instance_ids=ids)
        for instance in instances:
            if (instance.instances[0].update() == 'running'
                    and instance.instances[0].dns_name):
                instance_fqdns.append(
                    '%s:%d' % (instance.instances[0].dns_name, env.ssh_port))
    print("Found instances %s behind load balancer" % instance_fqdns)
    return instance_fqdns

@runs_once
def elb_add(instance=None):
    """Attach the instance defined by the provided instance ID (e.g. i-34927a9)
    to the application's Elastic Load Balancer.

    Requires the env keys:

        load_balancer -- the ID of the load balancer, typically a chosen name
        elb_connection -- an instance of boto.ec2.elb.ELBConnection (set
                            by default if you have the AWS shell variables)
    """
    require('load_balancer')
    require('elb_connection')
    status = env.elb_connection.register_instances(
            env.load_balancer, [instance])
    print("Status of attaching %s to load balancer %s was %s"
            % (instance, env.load_balancer, status))

@runs_once
def elb_remove(instance=None):
    """Detach the instance defined by the provided instance ID (e.g. i-34927a9)
    to the application's Elastic Load Balancer.

    Requires the env keys:

        load_balancer -- the ID of the load balancer, typically a chosen name
        elb_connection -- an instance of boto.ec2.elb.ELBConnection (set
                            by default if you have the AWS shell variables)
    """
    require('load_balancer')
    require('elb_connection')
    status = env.elb_connection.deregister_instances(
            env.load_balancer, [instance])
    print("Status of detaching %s from load balancer %s was %s"
            % (instance, env.load_balancer, status))

@runs_once
def conditional_s3_get(key, filename, sha=None):
    """Download a file from S3 to the local machine. Don't re-download if the
    sha matches (uses sha256).
    """
    sha_matches = False
    if exists(filename) and sha:
        sha_matches = sha_for_file(filename).startswith(sha)
        
    if not exists(filename) or not sha_matches:
        env.s3_key.key = key
        env.s3_key.get_contents_to_filename(filename)

########NEW FILE########
__FILENAME__ = celery
"""Utilities for configuring and managing celeryd processes on a remote
server.
"""
from fabric.api import require, env
from fabric.contrib.files import upload_template
import os

from buedafab.operations import chmod, sudo

def update_and_restart_celery():
    """Render a celeryd init.d script template and upload it to the remote
    server, then restart the celeryd process to reload the configuration.

    In addition to any env keys required by the celeryd template, requires:

        celeryd -- relateive path to the celeryd init.d script template from the
                    project root
        unit -- project's brief name, used to give each celeryd script and
                process a unique name, if more than one are running on the same
                host
        deployment_type -- app environment, to differentiate between celeryd
                processes for the same app in different environments on the
                same host (e.g. if staging and development run on the same
                physical server)

    The template is uploaded to: 

        /etc/init.d/celeryd-%(unit)s_%(deployment_type)s

    which in final form might look like:

        /etc/init.d/celeryd-five_DEV
    """

    require('path')
    require('celeryd')
    require('unit')
    require('deployment_type')
    if env.celeryd:
        celeryd_path = os.path.join(env.root_dir, env.celeryd)
        celeryd_remote_path = (
                '/etc/init.d/celeryd-%(unit)s_%(deployment_type)s' % env)
        upload_template(celeryd_path, celeryd_remote_path, env, use_sudo=True)

        # Wipe the -B option so it only happens once
        env.celeryd_beat_option = ""

        chmod(celeryd_remote_path, 'u+x')
        sudo(celeryd_remote_path + ' restart')

########NEW FILE########
__FILENAME__ = db
"""Utilities for updating schema and loading data into a database (all Django
specific at the moment.
"""
from fabric.api import require, env
from fabric.contrib.console import confirm
from fabric.decorators import runs_once
from fabric.colors import yellow

from buedafab.django.management import django_manage_run

@runs_once
def load_data():
    """Load extra fixtures into the database.

    Requires the env keys:

        release_path -- remote path of the deployed app
        deployment_type -- app environment to set before loading the data (i.e.
                            which database should it be loaded into)
        virtualenv -- path to this app's virtualenv (required to grab the
                        correct Python executable)
        extra_fixtures -- a list of names of fixtures to load (empty by default)
    """
    require('release_path')
    require('deployment_type')
    require('virtualenv')
    if env.migrated or env.updated_db:
        for fixture in env.extra_fixtures:
            django_manage_run("loaddata %s" % fixture)

@runs_once
def migrate(deployed=False):
    """Migrate the database to the currently deployed version using South. If
    the app wasn't deployed (e.g. we are redeploying the same version for some
    reason, this command will prompt the user to confirm that they want to
    migrate.

    Requires the env keys:

        release_path -- remote path of the deployed app
        deployment_type -- app environment to set before loading the data (i.e.
                            which database should it be loaded into)
        virtualenv -- path to this app's virtualenv (required to grab the
                        correct Python executable)
    """
    require('release_path')
    require('deployment_type')
    require('virtualenv')
    if (env.migrate and
            (deployed or confirm(yellow("Migrate database?"), default=True))):
        django_manage_run("migrate")
        env.migrated = True

@runs_once
def update_db(deployed=False):
    """Update the database to the currently deployed version using syncdb. If
    the app wasn't deployed (e.g. we are redeploying the same version for some
    reason, this command will prompt the user to confirm that they want to
    update.

    Requires the env keys:

        release_path -- remote path of the deployed app
        deployment_type -- app environment to set before loading the data (i.e.
                            which database should it be loaded into)
        virtualenv -- path to this app's virtualenv (required to grab the
                        correct Python executable)
    """
    require('deployment_type')
    require('virtualenv')
    require('release_path')
    if deployed or confirm(yellow("Update database?"), default=True):
        django_manage_run("syncdb --noinput")
        env.updated_db = True

########NEW FILE########
__FILENAME__ = defaults
"""Set sane default values for many of the keys required by buedafab's commands
and utilities. Any of these can be overridden by setting a custom value in a
project's fabfile that uses buedafab.
"""
from fabric.api import env, warn
import datetime
import os

env.time_now = datetime.datetime.now().strftime("%H%M%S-%d%m%Y")
env.version_pattern = r'^v\d+(\.\d+)+?$'
env.pip_install_command = 'pip install -i http://d.pypi.python.org/simple'

# Within the target directory on the remote server, subdirectory for the a/b
# releases directory.
env.releases_root = 'releases'

# Name of the symlink to the current release
env.current_release_symlink = 'current'
env.current_release_path = os.path.join(env.releases_root,
        env.current_release_symlink)

# Names of the directories to alternate between in the releases directory
env.release_paths = ('a', 'b',)

# Name of the virtualenv to create within each release directory
env.virtualenv = 'env'

# Default SSH port for all servers
env.ssh_port = 1222

# Default commit ID to deploy if none is specificed, e.g. fab development deploy
env.default_revision = 'HEAD'

# User and group that owns the deployed files - you probably want to change this
env.deploy_user = 'deploy'
env.deploy_group = 'bueda'

env.master_remote = 'origin'
env.settings = "settings.py"
env.extra_fixtures = ["permissions"]

# To avoid using hasattr(env, 'the_attr') everywhere, set some blank defaults
env.private_requirements = []
env.package_installation_scripts = []
env.crontab = None
env.updated_db = False
env.migrated = False
env.celeryd = None
env.celeryd_beat_option = "-B"
env.celeryd_options = "-E"
env.hoptoad_api_key = None
env.campfire_token = None
env.sha_url_template = None
env.deployed_version = None
env.scm_url_template = None
env.extra_deploy_tasks = []
env.extra_setup_tasks = []

# TODO open source the now deleted upload_to_s3 utils
if 'AWS_ACCESS_KEY_ID' in os.environ and 'AWS_SECRET_ACCESS_KEY' in os.environ:
    try:
        import boto.ec2
        import boto.ec2.elb
        import boto.s3
        import boto.s3.connection
        import boto.s3.key
    except ImportError:
        warn('boto not installed -- required to use S3 or EC2. '
                'Try running "fab setup" from the root of the ops repo')
    else:
        env.aws_access_key = os.environ['AWS_ACCESS_KEY_ID']
        env.aws_secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
        env.elb_connection = boto.ec2.elb.ELBConnection(
                env.aws_access_key, env.aws_secret_key)
        env.ec2_connection = boto.ec2.EC2Connection(
                    env.aws_access_key, env.aws_secret_key)
        # TODO this recently became required as a workaround?
        env.ec2_connection.SignatureVersion = '1'
        _s3_connection = boto.s3.connection.S3Connection(env.aws_access_key,
                env.aws_secret_key)

        env.s3_bucket_name = 'bueda.deploy'
        _bucket = _s3_connection.get_bucket(env.s3_bucket_name)
        env.s3_key = boto.s3.connection.Key(_bucket)
else:
    warn('No S3 key set. To use S3 or EC2 for deployment, '
        'you will need to set one -- '
        'see https://github.com/bueda/buedaweb/wikis/deployment-with-fabric')

########NEW FILE########
__FILENAME__ = cron
"""Utilities to manage crontabs on a remote server.

These aren't used at Bueda anymore, since migrating to celery's scheduled tasks.
"""
from fabric.operations import sudo
import os

from buedafab.operations import exists

def conditional_install_crontab(base_path, crontab, user):
    """If the project specifies a crontab, install it for the specified user on
    the remote server.
    """
    if crontab:
        crontab_path = os.path.join(base_path, crontab)
        if crontab and exists(crontab_path):
            sudo('crontab -u %s %s' % (user, crontab_path))


########NEW FILE########
__FILENAME__ = packages
"""Utilities to install Python package dependencies."""
from fabric.api import warn, cd, require, local, env, settings
from fabric.contrib.console import confirm
from fabric.colors import yellow
import os

from buedafab.operations import run, exists, put
from buedafab import deploy

def _read_private_requirements():
    for private_requirements in env.private_requirements:
        with open(os.path.join(env.root_dir, private_requirements), 'r') as f:
            for requirement in f:
                yield requirement.strip().split('==')

def _install_private_package(package, scm=None, release=None):
    env.scratch_path = os.path.join('/tmp', '%s-%s' % (package, env.time_now))
    archive_path = '%s.tar.gz' % env.scratch_path

    if not scm:
        require('s3_key')
        env.s3_key.key = '%s.tar.gz' % package
        env.s3_key.get_contents_to_filename(archive_path)
    else:
        if 'release' not in env:
            env.release = release
        release = release or 'HEAD'
        if 'pretty_release' in env:
            original_pretty_release = env.pretty_release
        else:
            original_pretty_release = None
        if 'archive' in env:
            original_archive = env.archive
        else:
            original_archive = None
        with settings(unit=package, scm=scm, release=release):
            if not os.path.exists(env.scratch_path):
                local('git clone %(scm)s %(scratch_path)s' % env)
            deploy.utils.make_archive()
            local('mv %s %s' % (os.path.join(env.scratch_path, env.archive),
                    archive_path))
        if original_pretty_release:
            env.pretty_release = original_pretty_release
        if original_archive:
            env.archive = original_archive
    put(archive_path, '/tmp')
    if env.virtualenv is not None:
        require('release_path')
        require('path')
        with cd(env.release_path):
            run('%s -E %s -s %s'
                    % (env.pip_install_command, env.virtualenv, archive_path))
    else:
        run('%s -s %s' % (env.pip_install_command, archive_path))

def _install_manual_packages(path=None):
    require('virtualenv')
    if not env.package_installation_scripts:
        return

    if not path:
        require('release_path')
        path = env.release_path
    with cd(path):
        for script in env.package_installation_scripts:
            run('./%s %s' % (script, local("echo $VIRTUAL_ENV")
                    or env.virtualenv))

def _install_pip_requirements(path=None):
    require('virtualenv')
    require('pip_requirements')
    if not path:
        require('release_path')
        path = env.release_path
    if not env.pip_requirements:
        warn("No pip requirements files found -- %(pip_requirements)s"
                % env)
        return
    with cd(path):
        for requirements_file in env.pip_requirements:
            run('%s -E %s -s -r %s' % (env.pip_install_command,
                    env.virtualenv, requirements_file))

def install_requirements(deployed=False):
    """Install the pip packages listed in the project's requirements files,
    private packages, as well as manual installation scripts.

    Installation scripts defined by env.package_installation_scripts will be
    provided the path to the virtualenv if one exists as the first argument.

    Requires the env keys:

        release_path -- remote path of the deployed app
        virtualenv -- path to this app's virtualenv (required to grab the
                        correct Python executable)
    """
    require('release_path')
    require('virtualenv')

    with settings(cd(env.release_path), warn_only=True):
        virtualenv_exists = exists('%(virtualenv)s' % env)
    if (deployed or not virtualenv_exists or
            confirm(yellow("Reinstall Python dependencies?"), default=True)):
        _install_pip_requirements()
        for package in _read_private_requirements():
            _install_private_package(*package)
        _install_manual_packages()
        return True
    return False

########NEW FILE########
__FILENAME__ = release
"""Utilities to determine the proper identifier for a deploy."""
from fabric.api import cd, require, local, env, prompt, settings, abort
from fabric.contrib.console import confirm
from fabric.decorators import runs_once
from fabric.colors import green, yellow
import os
import re

from buedafab.operations import (run, exists, conditional_mkdir,
        conditional_rm, chmod)
from buedafab import utils

def bootstrap_release_folders():
    """Create the target deploy directories if they don't exist and clone a
    fresh copy of the project's repository into each of the release directories.
    """
    require('path')
    require('deploy_group')
    conditional_mkdir(os.path.join(env.path, env.releases_root),
            env.deploy_group, 'g+w', use_sudo=True)
    with cd(os.path.join(env.path, env.releases_root)):
        first_exists = exists(env.release_paths[0])
        if not first_exists:
            run('git clone %s %s' % (env.scm, env.release_paths[0]),
                    forward_agent=True)
    with cd(os.path.join(env.path, env.releases_root)):
        if not exists(env.release_paths[1]):
            run('cp -R %s %s' % (env.release_paths[0], env.release_paths[1]))
    chmod(os.path.join(env.path, env.releases_root), 'g+w', use_sudo=True)

def make_pretty_release():
    """Assigns env.pretty_release to the commit identifier returned by 'git
    describe'.

    Requires the env keys:
        release -
        unit -
    """
    require('release')
    env.pretty_release = local('git describe %(release)s' % env, capture=True
            ).rstrip('\n')
    env.archive = '%(pretty_release)s-%(unit)s.tar' % env

def make_head_commit():
    """Assigns the commit SHA of the current git HEAD to env.head_commit.

    Requires the env keys:
        default_revision - the commit ref for HEAD
    """
    revision = local('git rev-list %(default_revision)s '
            '-n 1 --abbrev-commit --abbrev=7' % env, capture=True)
    env.head_commit = revision.rstrip('\n')

@runs_once
def make_release(release=None):
    """Based on the deployment type and any arguments from the command line,
    determine the proper identifier for the commit to deploy.

    If a tag is required (e.g. when in the production app environment), the
    deploy must be coming from the master branch, and cannot proceed without
    either creating a new tag or specifing and existing one.

    Requires the env keys:
        allow_no_tag - whether or not to require the release to be tagged in git
        default_revision - the commit ref for HEAD
    """
    require('allow_no_tag')
    require('default_revision')

    env.release = release
    env.tagged = False
    if not env.release or env.release == 'latest_tag':
        if not env.allow_no_tag:
            branch = utils.branch()
            if branch != "master":
                abort("Make sure to checkout the master branch and merge in the"
                        " development branch before deploying to production.")
            local('git checkout master', capture=True)
        description = local('git describe master' % env, capture=True
                ).rstrip('\n')
        if '-' in description:
            env.latest_tag = description[:description.find('-')]
        else:
            env.latest_tag = description
        if not re.match(env.version_pattern, env.latest_tag):
            env.latest_tag = None
        env.release = env.release or env.latest_tag
        env.commit = 'HEAD'
        if not env.allow_no_tag:
            if confirm(yellow("Tag this release?"), default=False):
                require('master_remote')
                from prettyprint import pp
                print(green("The last 5 tags were: "))
                tags = local('git tag | tail -n 20', capture=True)
                pp(sorted(tags.split('\n'), utils.compare_versions,
                        reverse=True))
                prompt("New release tag in the format vX.Y[.Z]?",
                        'tag',
                        validate=env.version_pattern)
                require('commit')
                local('git tag -s %(tag)s %(commit)s' % env)
                local('git push --tags %(master_remote)s' % env, capture=True)
                env.tagged = True
                env.release = env.tag
                local('git fetch --tags %(master_remote)s' % env, capture=True)
            else:
                print(green("Using latest tag %(latest_tag)s" % env))
                env.release = env.latest_tag
        else:
            make_head_commit()
            env.release = env.head_commit
            print(green("Using the HEAD commit %s" % env.head_commit))
    else:
        local('git checkout %s' % env.release, capture=True)
        env.tagged = re.match(env.version_pattern, env.release)
    make_pretty_release()

def conditional_symlink_current_release(deployed=False):
    """Swap the 'current' symlink to point to the new release if it doesn't
    point there already.

    Requires the env keys:
        pretty_release - set by make_pretty_release(), a commit identifier
        release_path - root target directory on the remote server
    """
    current_version = None
    if exists(utils.absolute_release_path()):
        with settings(cd(utils.absolute_release_path()), warn_only=True):
            current_version = run('git describe')
    if (not exists(utils.absolute_release_path())
            or deployed or current_version != env.pretty_release):
        _symlink_current_release(env.release_path)

def alternative_release_path():
    """Determine the release directory that is not currently in use.

    For example if the 'current' symlink points to the 'a' release directory,
    this method returns 'b'.

    Requires the env keys:
        release_paths - a tuple of length 2 with the release directory names
                            (defaults to 'a' and 'b')
    """

    if exists(utils.absolute_release_path()):
        current_release_path = run('readlink %s'
                % utils.absolute_release_path())
        if os.path.basename(current_release_path) == env.release_paths[0]:
            alternative = env.release_paths[1]
        else:
            alternative = env.release_paths[0]
        return alternative
    else:
        return env.release_paths[0]

def _symlink_current_release(next_release_path):
    with cd(os.path.join(env.path, env.releases_root)):
        conditional_rm(env.current_release_symlink)
        run('ln -fs %s %s' % (next_release_path, env.current_release_symlink))

########NEW FILE########
__FILENAME__ = types
"""Deploy commands for applications following Bueda's boilerplate layouts."""
from fabric.api import warn, cd, require, local, env, settings, abort
from fabric.colors import green, red
import os

from buedafab.operations import run, put, chmod
from buedafab import celery, db, tasks, notify, testing, utils
from buedafab import deploy

def _git_deploy(release, skip_tests):
    starting_branch = utils.branch()
    print(green("Deploying from git branch '%s'" % starting_branch))
    # Ideally, tests would run on the version you are deploying exactly.
    # There is no easy way to require that without allowing users to go
    # through the entire tagging process before failing tests.
    if not skip_tests and testing.test():
        abort(red("Unit tests did not pass -- must fix before deploying"))

    local('git push %(master_remote)s' % env, capture=True)
    deploy.release.make_release(release)

    require('pretty_release')
    require('path')
    require('hosts')

    print(green("Deploying version %s" % env.pretty_release))
    put(os.path.join(os.path.abspath(os.path.dirname(__file__)),
            '..', 'files', 'ssh_config'), '.ssh/config')

    deployed = False
    hard_reset = False
    deployed_versions = {}
    deploy.release.bootstrap_release_folders()
    for release_path in env.release_paths:
        with cd(os.path.join(env.path, env.releases_root, release_path)):
            deployed_versions[run('git describe')] = release_path
    print(green("The host '%s' currently has the revisions: %s"
        % (env.host, deployed_versions)))
    if env.pretty_release not in deployed_versions:
        env.release_path = os.path.join(env.path, env.releases_root,
                deploy.release.alternative_release_path())
        with cd(env.release_path):
            run('git fetch %(master_remote)s' % env, forward_agent=True)
            run('git reset --hard %(release)s' % env)
        deploy.cron.conditional_install_crontab(env.release_path, env.crontab,
                env.deploy_user)
        deployed = True
    else:
        warn(red("%(pretty_release)s is already deployed" % env))
        env.release_path = os.path.join(env.path, env.releases_root,
                deployed_versions[env.pretty_release])
    with cd(env.release_path):
        run('git submodule update --init --recursive', forward_agent=True)
    hard_reset = deploy.packages.install_requirements(deployed)
    deploy.utils.run_extra_deploy_tasks(deployed)
    local('git checkout %s' % starting_branch, capture=True)
    chmod(os.path.join(env.path, env.releases_root), 'g+w', use_sudo=True)
    return deployed, hard_reset

def default_deploy(release=None, skip_tests=None):
    """Deploy a project according to the methodology defined in the README."""
    require('hosts')
    require('path')
    require('unit')

    env.test_runner = testing.webpy_test_runner

    utils.store_deployed_version()
    deployed, hard_reset = _git_deploy(release, skip_tests)
    deploy.release.conditional_symlink_current_release(deployed)
    tasks.restart_webserver(hard_reset)
    with settings(warn_only=True):
        notify.hoptoad_deploy(deployed)
        notify.campfire_notify(deployed)

webpy_deploy = default_deploy
tornado_deploy = default_deploy

def django_deploy(release=None, skip_tests=None):
    """Deploy a Django project according to the methodology defined in the
    README.

    Beyond the default_deploy(), this also updates and migrates the database,
    loads extra database fixtures, installs an optional crontab as well as
    celeryd.
    """
    require('hosts')
    require('path')
    require('unit')
    require('migrate')
    require('root_dir')

    env.test_runner = testing.django_test_runner

    utils.store_deployed_version()
    deployed, hard_reset = _git_deploy(release, skip_tests)
    db.update_db(deployed)
    db.migrate(deployed)
    db.load_data()
    deploy.release.conditional_symlink_current_release(deployed)
    celery.update_and_restart_celery()
    tasks.restart_webserver(hard_reset)
    notify.hoptoad_deploy(deployed)
    notify.campfire_notify(deployed)
    print(green("%(pretty_release)s is now deployed to %(deployment_type)s"
        % env))

########NEW FILE########
__FILENAME__ = utils
"""General deployment utilities (not Fabric commands)."""
from fabric.api import cd, require, local, env

from buedafab import deploy

def make_archive():
    """Create a compressed archive of the project's repository, complete with
    submodules.

    TODO We used to used git-archive-all to archive the submodules as well,
    since 'git archive' doesn't touch them. We reverted back at some point and
    stopped using archives in our deployment strategy, so this may not work with
    submodules.
    """
    require('release')
    require('scratch_path')
    with cd(env.scratch_path):
        deploy.release.make_pretty_release()
        local('git checkout %(release)s' % env, capture=True)
        local('git submodule update --init', capture=True)
        local('git archive --prefix=%(unit)s/ --format tar '
                '%(release)s | gzip > %(scratch_path)s/%(archive)s' % env,
                capture=True)

def run_extra_deploy_tasks(deployed=False):
    """Run arbitrary functions listed in env.package_installation_scripts.

    Each function must accept a single parameter (or just kwargs) that will
    indicates if the app was deployed or already existed.

    """
    require('release_path')
    if not env.extra_deploy_tasks:
        return

    with cd(env.release_path):
        for task in env.extra_deploy_tasks:
            task(deployed=deployed)

########NEW FILE########
__FILENAME__ = management
from fabric.api import require, prefix, env
from fabric.decorators import runs_once

from buedafab.operations import virtualenv_run
from buedafab.utils import absolute_release_path

def django_manage_run(cmd):
    require('deployment_type')
    with prefix("export DEPLOYMENT_TYPE='%(deployment_type)s'" % env):
        virtualenv_run("./manage.py %s" % cmd, env.release_path)

@runs_once
def shell():
    env.release_path = absolute_release_path()
    django_manage_run('shell')

########NEW FILE########
__FILENAME__ = environments
"""Application environments, which determine the servers, database and other
conditions for deployment.
"""
from fabric.api import require, env
import os

from buedafab import aws

def _not_localhost():
    """All non-localhost environments need to install the "production" pip
    requirements, which typically includes the Python database bindings.
    """
    if (hasattr(env, 'pip_requirements')
            and hasattr(env, 'pip_requirements_production')):
        env.pip_requirements += env.pip_requirements_production

def development():
    """[Env] Development server environment

    - Sets the hostname of the development server (using the default ssh port)
    - Sets the app environment to "DEV"
    - Permits developers to deploy without creating a tag in git
    """
    _not_localhost()
    if len(env.hosts) == 0:
        env.hosts = ['dev.bueda.com:%(ssh_port)d' % env]
    env.allow_no_tag = True
    env.deployment_type = "DEV"
    if (hasattr(env, 'pip_requirements')
            and hasattr(env, 'pip_requirements_dev')):
        env.pip_requirements += env.pip_requirements_dev

def staging():
    """[Env] Staging server environment

    - Sets the hostname of the staging server (using the default ssh port)
    - Sets the app environment to "STAGING"
    - Permits developers to deploy without creating a tag in git
    - Appends "-staging" to the target directory to allow development and
        staging servers to be the same machine
    """
    _not_localhost()
    if len(env.hosts) == 0:
        env.hosts = ['dev.bueda.com:%(ssh_port)d' % env]
    env.allow_no_tag = True
    env.deployment_type = "STAGING"
    env.path += '-staging'

def production():
    """[Env] Production servers. Stricter requirements.

    - Collects production servers from the Elastic Load Balancer specified by
        the load_balancer env attribute
    - Sets the app environment to "PRODUCTION"
    - Requires that developers deploy from the 'master' branch in git
    - Requires that developers tag the commit in git before deploying
    """
    _not_localhost()
    env.allow_no_tag = False
    env.deployment_type = "PRODUCTION"
    if hasattr(env, 'load_balancer'):
        if len(env.hosts) == 0:
            env.hosts = aws.collect_load_balanced_instances()
    env.default_revision = '%(master_remote)s/master' % env

def localhost(deployment_type=None):
    """[Env] Bootstrap the localhost - can be either dev, production or staging.

    We don't really use this anymore except for 'fab setup', and even there it
    may not be neccessary. It was originally intended for deploying
    automatically with Chef, but we moved away from that approach.
    """
    require('root_dir')
    if len(env.hosts) == 0:
        env.hosts = ['localhost']
    env.allow_no_tag = True
    env.deployment_type = deployment_type
    env.virtualenv = os.environ.get('VIRTUAL_ENV', 'env')
    if deployment_type is None:
        deployment_type = "SOLO"
    env.deployment_type = deployment_type
    if env.deployment_type == "STAGING":
        env.path += '-staging'
    if (hasattr(env, 'pip_requirements')
            and hasattr(env, 'pip_requirements_dev')):
        env.pip_requirements += env.pip_requirements_dev

def django_development():
    """[Env] Django development server environment

    In addition to everything from the development() task, also:

        - loads any database fixtures named "dev"
        - loads a crontab from the scripts directory (deprecated at Bueda)
    """
    development()
    env.extra_fixtures += ["dev"]
    env.crontab = os.path.join('scripts', 'crontab', 'development')

def django_staging():
    """[Env] Django staging server environment

    In addition to everything from the staging() task, also:

        - loads a production crontab from the scripts directory (deprecated at
                Bueda)
    """
    staging()
    env.crontab = os.path.join('scripts', 'crontab', 'production')

def django_production():
    """[Env] Django production server environment

    In addition to everything from the production() task, also:

        - loads a production crontab from the scripts directory (deprecated at
                Bueda)
    """
    production()
    env.crontab = os.path.join('scripts', 'crontab', 'production')

########NEW FILE########
__FILENAME__ = notify
"""Deploy notification hooks for third party services like Campfire and Hoptoad.
"""
from fabric.api import env, require, local
from fabric.decorators import runs_once
import os

from buedafab import utils

@runs_once
def hoptoad_deploy(deployed=False):
    """Notify Hoptoad of the time and commit SHA of an app deploy.

    Requires the hoppy Python package and the env keys:

        hoptoad_api_key - as it sounds.
        deployment_type - app environment
        release - the commit SHA or git tag of the deployed version
        scm - path to the remote git repository
    """
    require('hoptoad_api_key')
    require('deployment_type')
    require('release')
    require('scm')
    if deployed and env.hoptoad_api_key:
        commit = local('git rev-parse --short %(release)s' % env,
                capture=True)
        import hoppy.deploy
        hoppy.api_key = env.hoptoad_api_key
        try:
            hoppy.deploy.Deploy().deploy(
                env=env.deployment_type,
                scm_revision=commit,
                scm_repository=env.scm,
                local_username=os.getlogin())
        except Exception, e:
            print ("Couldn't notify Hoptoad of the deploy, but continuing "
                    "anyway: %s" % e)
        else:
            print ('Hoptoad notified of deploy of %s@%s to %s environment by %s'
                    % (env.scm, commit, env.deployment_type, os.getlogin()))

@runs_once
def campfire_notify(deployed=False):
    """Hop in Campfire and notify your developers of the time and commit SHA of
    an app deploy.

    Requires the pinder Python package and the env keys:

        deployment_type - app environment
        release - the commit SHA or git tag of the deployed version
        scm_http_url - path to an HTTP view of the remote git repository
        campfire_subdomain - subdomain of your Campfire account
        campfire_token - API token for Campfire
        campfire_room - the room to join and notify (the string name, e.g.
                        "Developers")
    """
    require('deployment_type')
    require('release')

    if (deployed and env.campfire_subdomain and env.campfire_token
            and env.campfire_room):
        from pinder import Campfire
        deploying = local('git rev-list --abbrev-commit %s | head -n 1' %
                env.release, capture=True)
        branch = utils.branch(env.release)

        if env.tagged:
            require('release')
            branch = env.release

        name = env.unit
        deployer = os.getlogin()
        deployed = env.deployed_version
        target = env.deployment_type.lower()
        source_repo_url = env.scm_http_url
        compare_url = ('%s/compare/%s...%s' % (source_repo_url, deployed,
                deploying))

        campfire = Campfire(env.campfire_subdomain, env.campfire_token,
                ssl=True)
        room = campfire.find_room_by_name(env.campfire_room)
        room.join()
        if deployed:
            message = ('%s is deploying %s %s (%s..%s) to %s %s'
                % (deployer, name, branch, deployed, deploying, target,
                    compare_url))
        else:
            message = ('%s is deploying %s %s to %s' % (deployer, name,
                branch, target))
        room.speak(message)
        print 'Campfire notified that %s' % message


########NEW FILE########
__FILENAME__ = operations
"""Lower-level Fabric extensions for common tasks. None of these are ready-to-go
Fabric commands.
"""
from fabric.api import (run as fabric_run, local, sudo as fabric_sudo, hide,
        put as fabric_put, settings, env, require, abort, cd)
from fabric.contrib.files import (exists as fabric_exists, sed as fabric_sed)
import os

from buedafab.utils import absolute_release_path

def chmod(path, mode, recursive=True, use_sudo=False):
    cmd = 'chmod %(mode)s %(path)s' % locals()
    if recursive:
        cmd += ' -R'
    _conditional_sudo(cmd, use_sudo)

def chgrp(path, group, recursive=True, use_sudo=False):
    cmd = 'chgrp %(group)s %(path)s' % locals()
    if recursive:
        cmd += ' -R'
    _conditional_sudo(cmd, use_sudo)

def chown(path, user, recursive=True, use_sudo=False):
    cmd = 'chown %(user)s %(path)s' % locals()
    if recursive:
        cmd += ' -R'
    _conditional_sudo(cmd, use_sudo)

def _conditional_sudo(cmd, use_sudo):
    if use_sudo:
        sudo(cmd)
    else:
        run(cmd)

def put(local_path, remote_path, mode=None, **kwargs):
    """If the host is localhost, puts the file without requiring SSH."""
    require('hosts')
    if 'localhost' in env.hosts:
        if (os.path.isdir(remote_path) and
                (os.path.join(remote_path, os.path.basename(local_path)))
                == local_path):
            return 0
        result = local('cp -R %s %s' % (local_path, remote_path))
        if mode:
            local('chmod -R %o %s' % (mode, remote_path))
        return result
    else:
        return fabric_put(local_path, remote_path, mode, **kwargs)

def run(command, forward_agent=False, use_sudo=False, **kwargs):
    require('hosts')
    if 'localhost' in env.hosts:
        return local(command)
    elif forward_agent:
        if not env.host:
            abort("At least one host is required")
        return sshagent_run(command, use_sudo=use_sudo)
    else:
        return fabric_run(command, **kwargs)

def virtualenv_run(command, path=None):
    path = path or absolute_release_path()
    with cd(path):
        run("%s/bin/python %s" % (env.virtualenv, command))

def sshagent_run(command, use_sudo=False):
    """
    Helper function.
    Runs a command with SSH agent forwarding enabled.

    Note:: Fabric (and paramiko) can't forward your SSH agent.
    This helper uses your system's ssh to do so.
    """

    if use_sudo:
        command = 'sudo %s' % command

    cwd = env.get('cwd', '')
    if cwd:
        cwd = 'cd %s && ' % cwd
    real_command = cwd + command

    with settings(cwd=''):
        if env.port:
            port = env.port
            host = env.host
        else:
            try:
                # catch the port number to pass to ssh
                host, port = env.host.split(':')
            except ValueError:
                port = None
                host = env.host

        if port:
            local('ssh -p %s -A %s "%s"' % (port, host, real_command))
        else:
            local('ssh -A %s "%s"' % (env.host, real_command))

def sudo(command, shell=True, user=None, pty=False):
    """If the host is localhost, runs without requiring SSH."""
    require('hosts')
    if 'localhost' in env.hosts:
        command = 'sudo %s' % command
        return local(command, capture=False)
    else:
        return fabric_sudo(command, shell, user, pty)

def exists(path, use_sudo=False, verbose=False):
    require('hosts')
    if 'localhost' in env.hosts:
        capture = not verbose
        command = 'test -e "%s"' % path
        func = use_sudo and sudo or run
        with settings(hide('everything'), warn_only=True):
            return not func(command, capture=capture).failed
    else:
        return fabric_exists(path, use_sudo, verbose)

def sed(filename, before, after, limit='', use_sudo=False, backup='.bak'):
    require('hosts')
    if 'localhost' in env.hosts:
        # Code copied from Fabric - is there a better way to have Fabric's sed()
        # use our sudo and run functions?
        expr = r"sed -i%s -r -e '%ss/%s/%s/g' %s"
        # Characters to be escaped in both
        for char in "/'":
            before = before.replace(char, r'\%s' % char)
            after = after.replace(char, r'\%s' % char)
        # Characters to be escaped in replacement only (they're useful in
        # regexe in the 'before' part)
        for char in "()":
            after = after.replace(char, r'\%s' % char)
        if limit:
            limit = r'/%s/ ' % limit
        command = expr % (backup, limit, before, after, filename)
        func = use_sudo and sudo or run
        return func(command)
    else:
        return fabric_sed(filename, before, after, limit, use_sudo, backup)

def conditional_mv(source, destination):
    if exists(source):
        run('mv %s %s' % (source, destination))

def conditional_rm(path, recursive=False):
    if exists(path):
        cmd = 'rm'
        if recursive:
            cmd += ' -rf'
        run('%s %s' % (cmd, path))

def conditional_mkdir(path, group=None, mode=None, user=None, use_local=False,
        use_sudo=False):
    cmd = 'mkdir -p %s' % path
    if not exists(path):
        if use_local:
            local(cmd)
        else:
            _conditional_sudo(cmd, use_sudo)
    if group:
        chgrp(path, group, use_sudo=True)
    if user:
        chown(path, user, use_sudo=True)
    if mode:
        chmod(path, mode, use_sudo=True)

########NEW FILE########
__FILENAME__ = tasks
"""Relatively self-contained, simple Fabric commands."""
from fabric.api import require, env, local, warn, settings, cd
import os

from buedafab.operations import run, exists, conditional_rm, sed, sudo
from buedafab import environments, deploy, utils

def setup():
    """A shortcut to bootstrap or update a virtualenv with the dependencies for
    this project. Installs the `common.txt` and `dev.txt` pip requirements and
    initializes/updates any git submodules.

    setup() also supports the concept of "private packages" - i.e. Python
    packages that are not available on PyPi but require some local compilation
    and thus don't work well as git submodules. It can either download a tar
    file of the package from S3 or clone a git repository, build and install the
    package.

    Any arbitrary functions in env.extra_setup_tasks will also be run from
    env.root_dir.
    """

    environments.localhost()
    with settings(virtualenv=None):
        for package in deploy.packages._read_private_requirements():
            deploy.packages._install_private_package(*package)
    deploy.packages._install_manual_packages(env.root_dir)
    deploy.packages._install_pip_requirements(env.root_dir)

    with cd(env.root_dir):
        local('git submodule update --init --recursive')
        for task in env.extra_setup_tasks:
            task()


def enable():
    """Toggles a value True. Used in 'toggle' commands such as
    maintenancemode().
    """
    env.toggle = True

def disable():
    """Toggles a value False. Used in 'toggle' commands such as
    maintenancemode().
    """
    env.toggle = False

def maintenancemode():
    """If using the maintenancemode app
    (https://github.com/jezdez/django-maintenancemode), this command will toggle
    it on and off. It finds the `MAINTENANCE_MODE` variable in your
    `settings.py` on the remote server, toggles its value and restarts the web
    server.

    Requires the env keys:

        toggle - set by enable() or disable(), indicates whether we should turn
                    maintenance mode on or off.
        settings - relative path from the project root to the settings.py file
        current_release_path - path to the current release on the remote server
    """
    require('toggle', provided_by=[enable, disable])
    require('settings')
    require('current_release_path')

    settings_file = os.path.join(utils.absolute_release_path(), env.settings)
    if exists(settings_file):
        sed(settings_file, '(MAINTENANCE_MODE = )(False|True)',
                '\\1%(toggle)s' % env)
        restart_webserver()
    else:
        warn('Settings file %s could not be found' % settings_file)

def rollback():
    """Swaps the deployed version of the app to the previous version.

    Requires the env keys:

        path - root deploy target for this app
        releases_root - subdirectory that stores the releases
        current_release_symlink - name of the symlink pointing to the currently
                                    deployed version
        Optional:

        crontab - relative path from the project root to a crontab to install
        deploy_user - user that should run the crontab
    """
    require('path')
    require('releases_root')
    require('current_release_symlink')
    require('crontab')
    require('deploy_user')
    with cd(os.path.join(env.path, env.releases_root)):
        previous_link = deploy.release.alternative_release_path()
        conditional_rm(env.current_release_symlink)
        run('ln -fs %s %s' % (previous_link, env.current_release_symlink))
    deploy.cron.conditional_install_crontab(utils.absolute_release_path(),
            env.crontab, env.deploy_user)
    restart_webserver()

def restart_webserver(hard_reset=False):
    """Restart the Gunicorn application webserver.

    Requires the env keys:

        unit - short name of the app, assuming /etc/sv/%(unit)s is the
                runit config path
    """
    require('unit')
    with settings(warn_only=True):
        sudo('/etc/init.d/%(unit)s restart' % env)

def rechef():
    """Run the latest Chef cookbooks on all servers."""
    sudo('chef-client')

def _package_installed(package):
    with settings(warn_only=True):
        virtualenv_exists = exists('%(virtualenv)s' % env)
        if virtualenv_exists:
            installed = run('%s/bin/python -c "import %s"'
                    % (env.virtualenv, package))
        else:
            installed = run('python -c "import %s"' % package)
    return installed.return_code == 0

def install_jcc(**kwargs):
    if not _package_installed('jcc'):
        run('git clone git://gist.github.com/729451.git build-jcc')
        run('VIRTUAL_ENV=%s build-jcc/install_jcc.sh'
                % env.virtualenv)
        run('rm -rf build-jcc')

def install_pylucene(**kwargs):
    if not _package_installed('lucene'):
        run('git clone git://gist.github.com/728598.git build-pylucene')
        run('VIRTUAL_ENV=%s build-pylucene/install_pylucene.sh'
                % env.virtualenv)
        run('rm -rf build-pylucene')

########NEW FILE########
__FILENAME__ = testing
"""Code style and unit testing utilities."""
from fabric.api import env, require, cd, runs_once, local, settings
import os

@runs_once
def lint():
    """Run pylint on the project, including the packages in `apps/`, `lib/` and
    `vendor/`, and using the `.pylintrc` file in the project's root.

    Requires the env keys:
        root_dir - root of the project, where the fabfile resides
    """
    require('root_dir')
    env.python_path_extensions = '%(root_dir)s/lib:%(root_dir)s/apps' % env
    for directory in os.listdir(os.path.join(env.root_dir, 'vendor')):
        full_path = os.path.join(env.root_dir, 'vendor', directory)
        if os.path.isdir(full_path):
            env.python_path_extensions += ':' + full_path
    with cd(env.root_dir):
        local('PYTHONPATH=$PYTHONPATH:%(python_path_extensions)s '
            'pylint %(root_dir)s --rcfile=.pylintrc 2>/dev/null' % env)

@runs_once
def test(dir=None, deployment_type=None):
    """Run the test suite for this project. There are current test runners defined for
    Django, Tornado, and general nosetests suites. Just set `env.test_runner` to the
    appropriate method (or write your own).

    Requires the env keys:
        root_dir - root of the project, where the fabfile resides
        test_runner - a function expecting the deployment_type as a parameter
                    that runs the test suite for this project
    """
    require('root_dir')
    require('test_runner')
    with settings(root_dir=(dir or env.root_dir), warn_only=True):
        return env.test_runner(deployment_type)

@runs_once
def nose_test_runner(deployment_type=None):
    """Basic nosetests suite runner."""
    return local('nosetests').return_code

@runs_once
def webpy_test_runner(deployment_type=None):
    # TODO
    #import manage
    #import nose
    #return nose.run()
    pass

@runs_once
def tornado_test_runner(deployment_type=None):
    """Tornado test suite runner - depends on using Bueda's tornado-boilerplate
    app layout."""
    return local('tests/run_tests.py').return_code

@runs_once
def django_test_runner(deployment_type=None):
    """Django test suite runer."""
    command = './manage.py test'
    if deployment_type:
        command = 'DEPLOYMENT_TYPE=%s ' % deployment_type + command
    return local(command).return_code

########NEW FILE########
__FILENAME__ = utils
"""Lower-level utilities, including some git helpers."""
from fabric.api import env, local, require, settings
from fabric.colors import green
import os

def compare_versions(x, y):
    """
    Expects 2 strings in the format of 'X.Y.Z' where X, Y and Z are
    integers. It will compare the items which will organize things
    properly by their major, minor and bugfix version.
    ::

        >>> my_list = ['v1.13', 'v1.14.2', 'v1.14.1', 'v1.9', 'v1.1']
        >>> sorted(my_list, cmp=compare_versions)
        ['v1.1', 'v1.9', 'v1.13', 'v1.14.1', 'v1.14.2']

    """
    def version_to_tuple(version):
        # Trim off the leading v
        version_list = version[1:].split('.', 2)
        if len(version_list) <= 3:
            [version_list.append(0) for _ in range(3 - len(version_list))]
        try:
            return tuple((int(version) for version in version_list))
        except ValueError: # not an integer, so it goes to the bottom
            return (0, 0, 0)

    x_major, x_minor, x_bugfix = version_to_tuple(x)
    y_major, y_minor, y_bugfix = version_to_tuple(y)
    return (cmp(x_major, y_major) or cmp(x_minor, y_minor)
            or cmp(x_bugfix, y_bugfix))

def store_deployed_version():
    if env.sha_url_template:
        env.deployed_version = None
        with settings(warn_only=True):
            env.deployed_version = local('curl -s %s' % sha_url(), capture=True
                    ).strip('"')
        if env.deployed_version and len(env.deployment_type) > 10:
            env.deployed_version = None
        else:
            print(green("The currently deployed version is %(deployed_version)s"
                % env))

def sha_url():
    require('sha_url_template')
    if env.deployment_type == 'PRODUCTION':
        subdomain = 'www.'
    else:
        subdomain = env.deployment_type.lower() + '.'
    return env.sha_url_template % subdomain

def absolute_release_path():
    require('path')
    require('current_release_path')
    return os.path.join(env.path, env.current_release_path)

def branch(ref=None):
    """Return the name of the current git branch."""
    ref = ref or "HEAD"
    return local("git symbolic-ref %s 2>/dev/null | awk -F/ {'print $NF'}"
            % ref, capture=True)

def sha_for_file(input_file, block_size=2**20):
    import hashlib
    sha = hashlib.sha256()
    with open(input_file, 'rb') as f:
        for chunk in iter(lambda: f.read(block_size), ''):
            sha.update(chunk)
        return sha.hexdigest()

########NEW FILE########
__FILENAME__ = fabfile
#!/usr/bin/env python
import os
from fabric.api import *

from buedafab.test import test, django_test_runner as _django_test_runner, lint
from buedafab.deploy.types import django_deploy as deploy
from buedafab.environments import (django_development as development,
        django_production as production, django_localhost as localhost,
        django_staging as staging)
from buedafab.tasks import (setup, restart_webserver, rollback, enable,
        disable, maintenancemode, rechef)

# A short name for the app, used in folder names
env.unit = "five"

# Deploy target on remote server
env.path = "/var/webapps/%(unit)s" % env

# git-compatible path to remote repository
env.scm = "git@github.com:bueda/%(unit)s.git" % env

# HTTP-compatible path to the remote repository
# This is optional, and is used only to link Hoptoad deploys to source code
env.scm_http_url = "http://github.com/bueda/%(unit)s" % env

# The root directory of the project (where this fabfile.py resides)
env.root_dir = os.path.abspath(os.path.dirname(__file__))

# Paths to Python package requirements files for pip
# pip_requirements are installed in all environments
env.pip_requirements = ["requirements/common.txt",]
# pip_requirements_dev are installed only in the development environment
env.pip_requirements_dev = ["requirements/dev.txt",]
# pip_requirements_production are installed only in the production environment
env.pip_requirements_production = ["requirements/production.txt",]

# A Django-specific for projects using the South database migration app
env.migrate = True

# For projects using celery, the path to the system service script for celeryd
env.celeryd = 'scripts/init.d/celeryd'

# Name of the Amazon Elastic Load Balancer instance that sits in front of the
# app servers for this project - this is used to find all of the production
# servers for the app when re-deploying.
env.load_balancer = 'web'

# The test runner to use before deploying, and also when running 'fab test'
# Test runners are defined for Django, Tornado, web.py and general nosetests
# test suites. To define a custome test runner, just write a method and assign
# it to env.test_runner.
env.test_runner = _django_test_runner

# URL that returns the current git commit SHA this app is running
# This current must have a single string format parameter that is replaced by
# "dev." or "staging." or "www." depending on the environment - kind of a weird,
# strict requirement that should be re-worked.
env.sha_url_template = 'http://%sfivebybueda.com/version/'

# API key for the Hoptoad account associated with this project. Will report a
# deployment to Hoptoad to help keep track of resolved errors.
env.hoptoad_api_key = 'your-hoptoad-api-key'

# Campfire chat room information - will notify whenever someone deploys the app
env.campfire_subdomain = 'bueda'
env.campfire_room = 'YourRoom'
env.campfire_token = 'your-api-key'

########NEW FILE########
__FILENAME__ = fabfile
"""
Fabfile for deploying instances with Chef to EC2.
"""
#!/usr/bin/env python
import os
import time
from fabric.api import env, require, runs_once

import opsfab.defaults
from opsfab.types import *
from opsfab.environments import *
from fab_shared import local, put, sudo, rechef, setup

env.root_dir = os.path.abspath(os.path.dirname(__file__))
env.pip_requirements = ["pip-requirements.txt",]

@runs_once
def spawn(ami=None, region=None, chef_roles=None):
    """ Create a new server instance, which will bootstrap itself with Chef. """
    require('ami', provided_by=[small, large, extra_large, extra_large_mem,
            double_extra_large_mem, quadruple_extra_large_mem, medium_cpu,
            extra_large_cpu])
    require('instance_type')
    require('region')
    require('security_groups')
    require('key_name')
    require('ec2_connection')

    env.ami = ami or env.ami
    env.region = region or env.region

    role_string = ""
    if chef_roles:
        env.chef_roles.extend(chef_roles.split('-'))
    for role in env.chef_roles:
        role_string += "role[%s] " % role

    local('ssh-add ~/.ssh/%(key_name)s.pem' % env)

    command = 'knife ec2 server create %s ' % role_string
    command += '-Z %(region)s ' % env
    command += '-f %(instance_type)s -i %(ami)s ' % env
    command += '-G %s ' % ','.join(env.security_groups)
    command += '-S %(key_name)s ' % env
    command += '-x ubuntu '

    print "Run this command to spawn the server:\n"
    print command

########NEW FILE########
__FILENAME__ = fab_shared
"""
Included for legacy support of fabfiles depending on a one-file fab_shared.
"""
import buedafab
from buedafab.aws import *
from buedafab.celery import *
from buedafab.tasks import *
from buedafab.db import *
from buedafab.environments import *
from buedafab.notify import *
from buedafab.operations import *
from buedafab.testing import *
from buedafab.utils import *

import buedafab.deploy
from buedafab.deploy.cron import *
from buedafab.deploy.packages import *
from buedafab.deploy.release import *
from buedafab.deploy.types import *
from buedafab.deploy.utils import *

########NEW FILE########
__FILENAME__ = defaults
"""
Environment defaults for ops deployment fabfile.
"""
#!/usr/bin/env python
from fabric.api import env

env.unit = "chef"
env.scm = "git@github.com:bueda/chef"

env.security_groups = ["temporary", "ssh"]
env.key_name = "temporary"
env.region = 'us-east-1b'
env.chef_roles = ["base"]

########NEW FILE########
__FILENAME__ = environments
"""
Definitions of available server environments.
"""
#!/usr/bin/env python
from fabric.api import env

from fab_shared import (development as shared_development,
        production as shared_production)

def development():
    """ Sets roles for development server. """
    shared_development()
    env.security_groups = ["development", "ssh"]
    env.key_name = "development"
    env.chef_roles = ["dev"]

def production():
    """ Sets roles for production servers behind load balancer. """
    shared_production()
    env.security_groups = ["ssh", "database-client"]
    env.key_name = "production"
    env.chef_roles = ["production"]

def web():
    production()
    env.chef_roles.append("app_server")
    env.security_groups.extend(["web"])

def support():
    production()
    env.chef_roles.append("support_server")
    env.security_groups.extend(["support"])

########NEW FILE########
__FILENAME__ = types
"""
Definitions of available EC2 server types.
"""
#!/usr/bin/env python
from fabric.api import env

def _32bit():
    """ Ubuntu Maverick 10.10 32-bit """
    env.ami = "ami-a6f504cf"

def _32bit_ebs():
    """ Ubuntu Maverick 10.10 32-bit """
    env.ami = "ami-ccf405a5"

def _64bit_ebs():
    """ Ubuntu Maverick 10.10 64-bit """
    env.ami = "ami-cef405a7"

def _64bit():
    """ Ubuntu Maverick 10.10 64-bit """
    env.ami = "ami-08f40561"

def micro():
    """ Micro instance, 613MB, up to 2 CPU (64-bit) """
    _64bit_ebs()
    env.instance_type = 't1.micro'

def small():
    """ Small Instance, 1.7GB, 1 CPU (32-bit) """
    _32bit()
    env.instance_type = 'm1.small'

def large():
    """ Large Instance, 7.5GB, 4 CPU (64-bit) """
    _64bit()
    env.instance_type = 'm1.large'

def extra_large():
    """ Extra Large Instance, 16GB, 8 CPU (64-bit) """
    _64bit()
    env.instance_type = 'm1.xlarge'

def extra_large_mem():
    """ High-Memory Extra Large Instance, 17.1GB, 6.5 CPU (64-bit) """
    _64bit()
    env.instance_type = 'm2.xlarge'

def double_extra_large_mem():
    """ High-Memory Double Extra Large Instance, 34.2GB, 13 CPU (64-bit) """
    _64bit()
    env.instance_type = 'm2.2xlarge'

def quadruple_extra_large_mem():
    """ High-Memory Quadruple Extra Large Instance, 68.4GB, 26 CPU (64-bit) """
    _64bit()
    env.instance_type = 'm2.4xlarge'

def medium_cpu():
    """ High-CPU Medium Instance, 1.7GB, 5 CPU (32-bit) """
    _32bit()
    env.instance_type = 'c1.medium'

def extra_large_cpu():
    """ High-CPU Extra Large Instance, 7GB, 20 CPU (64-bit) """
    _64bit()
    env.instance_type = 'c1.xlarge'


########NEW FILE########
