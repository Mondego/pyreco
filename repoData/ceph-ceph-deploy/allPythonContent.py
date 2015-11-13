__FILENAME__ = admin
import logging

from cStringIO import StringIO

from ceph_deploy import exc
from ceph_deploy import conf
from ceph_deploy.cliutil import priority
from ceph_deploy import hosts

LOG = logging.getLogger(__name__)


def admin(args):
    cfg = conf.ceph.load(args)
    conf_data = StringIO()
    cfg.write(conf_data)

    try:
        with file('%s.client.admin.keyring' % args.cluster, 'rb') as f:
            keyring = f.read()
    except:
        raise RuntimeError('%s.client.admin.keyring not found' %
                           args.cluster)

    errors = 0
    for hostname in args.client:
        LOG.debug('Pushing admin keys and conf to %s', hostname)
        try:
            distro = hosts.get(hostname, username=args.username)
            hostname = distro.conn.remote_module.shortname()

            distro.conn.remote_module.write_conf(
                args.cluster,
                conf_data.getvalue(),
                args.overwrite_conf,
            )

            distro.conn.remote_module.write_file(
                '/etc/ceph/%s.client.admin.keyring' % args.cluster,
                keyring
            )

            distro.conn.exit()

        except RuntimeError as e:
            LOG.error(e)
            errors += 1

    if errors:
        raise exc.GenericError('Failed to configure %d admin hosts' % errors)


@priority(70)
def make(parser):
    """
    Push configuration and client.admin key to a remote host.
    """
    parser.add_argument(
        'client',
        metavar='HOST',
        nargs='*',
        help='host to configure for ceph administration',
        )
    parser.set_defaults(
        func=admin,
        )

########NEW FILE########
__FILENAME__ = calamari
import errno
import logging
import os
from ceph_deploy import hosts, exc
from ceph_deploy.lib.remoto import process


LOG = logging.getLogger(__name__)


def distro_is_supported(distro_name):
    """
    An enforcer of supported distros that can differ from what ceph-deploy
    supports.
    """
    supported = ['centos', 'redhat', 'ubuntu', 'debian']
    if distro_name in supported:
        return True
    return False


def connect(args):
    cd_conf = getattr(args, 'cd_conf', None)
    if not cd_conf:
        raise RuntimeError(
            'a ceph-deploy configuration is required but was not found'
        )

    repo_name = args.release or 'calamari-minion'
    has_minion_repo = cd_conf.has_section(repo_name)

    if not has_minion_repo:
        raise RuntimeError('no calamari-minion repo found')

    # We rely on the default for repo installs that does not
    # install ceph unless specified otherwise
    options = dict(cd_conf.items(repo_name))

    for hostname in args.hosts:
        distro = hosts.get(hostname, username=args.username)
        if not distro_is_supported(distro.normalized_name):
            raise exc.UnsupportedPlatform(
                distro.distro_name,
                distro.codename,
                distro.release
            )

        LOG.info(
            'Distro info: %s %s %s',
            distro.name,
            distro.release,
            distro.codename
        )
        rlogger = logging.getLogger(hostname)
        if distro.name in ('debian', 'ubuntu'):
            rlogger.info('ensuring proxy is disabled for calamari minions repo')
            distro.conn.remote_module.write_file(
                '/etc/apt/apt.conf.d/99ceph',
                'Acquire::http::Proxy::%s DIRECT;' % args.master,
            )
        rlogger.info('installing calamari-minion package on %s' % hostname)
        rlogger.info('adding custom repository file')
        try:
            distro.repo_install(
                distro,
                repo_name,
                options.pop('baseurl'),
                options.pop('gpgkey', ''),  # will probably not use a gpgkey
                **options
            )
        except KeyError as err:
            raise RuntimeError(
                'missing required key: %s in config section: %s' % (
                    err,
                    repo_name
                )
            )

        # Emplace minion config prior to installation so that it is present
        # when the minion first starts.
        minion_config_dir = os.path.join('/etc/salt/', 'minion.d')
        minion_config_file = os.path.join(minion_config_dir, 'calamari.conf')

        rlogger.debug('creating config dir: %s' % minion_config_dir)
        distro.conn.remote_module.makedir(minion_config_dir, [errno.EEXIST])

        rlogger.debug(
            'creating the calamari salt config: %s' % minion_config_file
        )
        distro.conn.remote_module.write_file(
            minion_config_file,
            'master: %s\n' % args.master
        )

        distro.pkg.install(distro, 'salt-minion')

        # redhat/centos need to get the service started
        if distro.normalized_name in ['redhat', 'centos']:
            process.run(
                distro.conn,
                ['chkconfig', 'salt-minion', 'on']
            )

            process.run(
                distro.conn,
                ['service', 'salt-minion', 'start']
            )

        distro.conn.exit()


def calamari(args):
    if args.subcommand == 'connect':
        connect(args)


def make(parser):
    """
    Install and configure Calamari nodes
    """
    parser.add_argument(
        'subcommand',
        choices=[
            'connect',
            ],
        )

    parser.add_argument(
        '--release',
        nargs='?',
        metavar='CODENAME',
        help="Use a given release from repositories\
                defined in ceph-deploy's configuration. Defaults to\
                'calamari-minion'",

    )

    parser.add_argument(
        '--master',
        nargs='?',
        metavar='MASTER SERVER',
        help="The domain for the Calamari master server"
    )

    parser.add_argument(
        'hosts',
        nargs='+',
    )

    parser.set_defaults(
        func=calamari,
    )

########NEW FILE########
__FILENAME__ = cli
import pkg_resources
import argparse
import logging
import textwrap
import os
import sys
from string import join

import ceph_deploy
from ceph_deploy import exc, validate
from ceph_deploy.util import log
from ceph_deploy.util.decorators import catches

LOG = logging.getLogger(__name__)


__header__ = textwrap.dedent("""
    -^-
   /   \\
   |O o|  ceph-deploy v%s
   ).-.(
  '/|||\`
  | '|` |
    '|`
""" % ceph_deploy.__version__)


def get_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Easy Ceph deployment\n\n%s' % __header__,
        )
    verbosity = parser.add_mutually_exclusive_group(required=False)
    verbosity.add_argument(
        '-v', '--verbose',
        action='store_true', dest='verbose', default=False,
        help='be more verbose',
        )
    verbosity.add_argument(
        '-q', '--quiet',
        action='store_true', dest='quiet',
        help='be less verbose',
        )
    parser.add_argument(
        '--version',
        action='version',
        version='%s' % ceph_deploy.__version__,
        help='the current installed version of ceph-deploy',
        )
    parser.add_argument(
        '--username',
        help='the username to connect to the remote host',
        )
    parser.add_argument(
        '--overwrite-conf',
        action='store_true',
        help='overwrite an existing conf file on remote host (if present)',
        )
    parser.add_argument(
        '--cluster',
        metavar='NAME',
        help='name of the cluster',
        type=validate.alphanumeric,
        )
    sub = parser.add_subparsers(
        title='commands',
        metavar='COMMAND',
        help='description',
        )
    entry_points = [
        (ep.name, ep.load())
        for ep in pkg_resources.iter_entry_points('ceph_deploy.cli')
        ]
    entry_points.sort(
        key=lambda (name, fn): getattr(fn, 'priority', 100),
        )
    for (name, fn) in entry_points:
        p = sub.add_parser(
            name,
            description=fn.__doc__,
            help=fn.__doc__,
            )
        # ugly kludge but i really want to have a nice way to access
        # the program name, with subcommand, later
        p.set_defaults(prog=p.prog)
        if not os.environ.get('CEPH_DEPLOY_TEST'):
            p.set_defaults(cd_conf=ceph_deploy.conf.cephdeploy.load())

        fn(p)
    parser.set_defaults(
        # we want to hold on to this, for later
        prog=parser.prog,
        cluster='ceph',
        )

    return parser


@catches((KeyboardInterrupt, RuntimeError, exc.DeployError,))
def main(args=None, namespace=None):
    parser = get_parser()

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit()
    else:
        args = parser.parse_args(args=args, namespace=namespace)

    console_loglevel = logging.DEBUG  # start at DEBUG for now
    if args.quiet:
        console_loglevel = logging.WARNING
    if args.verbose:
        console_loglevel = logging.DEBUG

    # Console Logger
    sh = logging.StreamHandler()
    sh.setFormatter(log.color_format())
    sh.setLevel(console_loglevel)

    # File Logger
    fh = logging.FileHandler('{cluster}.log'.format(cluster=args.cluster))
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(log.BASE_FORMAT))

    # because we're in a module already, __name__ is not the ancestor of
    # the rest of the package; use the root as the logger for everyone
    root_logger = logging.getLogger()

    # allow all levels at root_logger, handlers control individual levels
    root_logger.setLevel(logging.DEBUG)

    root_logger.addHandler(sh)
    root_logger.addHandler(fh)

    # Reads from the config file and sets values for the global
    # flags and the given sub-command
    # the one flag that will never work regardless of the config settings is
    # logging because we cannot set it before hand since the logging config is
    # not ready yet. This is the earliest we can do.
    args = ceph_deploy.conf.cephdeploy.set_overrides(args)

    LOG.info("Invoked (%s): %s" % (
        ceph_deploy.__version__,
        join(sys.argv, " "))
    )

    return args.func(args)

########NEW FILE########
__FILENAME__ = cliutil
def priority(num):
    """
    Decorator to add a `priority` attribute to the function.
    """
    def add_priority(fn):
        fn.priority = num
        return fn
    return add_priority

########NEW FILE########
__FILENAME__ = ceph
import ConfigParser
import contextlib

from ceph_deploy import exc


class _TrimIndentFile(object):
    def __init__(self, fp):
        self.fp = fp

    def readline(self):
        line = self.fp.readline()
        return line.lstrip(' \t')


class CephConf(ConfigParser.RawConfigParser):
    def optionxform(self, s):
        s = s.replace('_', ' ')
        s = '_'.join(s.split())
        return s

    def safe_get(self, section, key):
        """
        Attempt to get a configuration value from a certain section
        in a ``cfg`` object but returning None if not found. Avoids the need
        to be doing try/except {ConfigParser Exceptions} every time.
        """
        try:
            #Use full parent function so we can replace it in the class
            # if desired
            return ConfigParser.RawConfigParser.get(self, section, key)
        except (ConfigParser.NoSectionError,
                ConfigParser.NoOptionError):
            return None


def parse(fp):
    cfg = CephConf()
    ifp = _TrimIndentFile(fp)
    cfg.readfp(ifp)
    return cfg


def load(args):
    path = '{cluster}.conf'.format(cluster=args.cluster)
    try:
        f = file(path)
    except IOError as e:
        raise exc.ConfigError(
            "%s; has `ceph-deploy new` been run in this directory?" % e
        )
    else:
        with contextlib.closing(f):
            return parse(f)


def load_raw(args):
    """
    Read the actual file *as is* without parsing/modifiying it
    so that it can be written maintaining its same properties.
    """
    path = '{cluster}.conf'.format(cluster=args.cluster)
    try:
        with open(path) as ceph_conf:
            return ceph_conf.read()
    except (IOError, OSError) as e:
        raise exc.ConfigError(
            "%s; has `ceph-deploy new` been run in this directory?" % e
        )


def write_conf(cluster, conf, overwrite):
    """ write cluster configuration to /etc/ceph/{cluster}.conf """
    import os

    path = '/etc/ceph/{cluster}.conf'.format(cluster=cluster)
    tmp = '{path}.{pid}.tmp'.format(path=path, pid=os.getpid())

    if os.path.exists(path):
        with file(path, 'rb') as f:
            old = f.read()
            if old != conf and not overwrite:
                raise RuntimeError('config file %s exists with different content; use --overwrite-conf to overwrite' % path)
    with file(tmp, 'w') as f:
        f.write(conf)
        f.flush()
        os.fsync(f)
    os.rename(tmp, path)

########NEW FILE########
__FILENAME__ = cephdeploy
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError
import logging
import os
from os import path
import re

logger = logging.getLogger('ceph_deploy.conf')

cd_conf_template = """
#
# ceph-deploy configuration file
#

[ceph-deploy-global]
# Overrides for some of ceph-deploy's global flags, like verbosity or cluster
# name

[ceph-deploy-install]
# Overrides for some of ceph-deploy's install flags, like version of ceph to
# install


#
# Repositories section
#

# yum repos:
# [myrepo]
# baseurl = https://user:pass@example.org/rhel6
# gpgurl = https://example.org/keys/release.asc
# default = True
# extra-repos = cephrepo  # will install the cephrepo file too
#
# [cephrepo]
# name=ceph repo noarch packages
# baseurl=http://ceph.com/rpm-emperor/el6/noarch
# enabled=1
# gpgcheck=1
# type=rpm-md
# gpgkey=https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/autobuild.asc

# apt repos:
# [myrepo]
# baseurl = https://user:pass@example.org/
# gpgurl = https://example.org/keys/release.asc
# default = True
# extra-repos = cephrepo  # will install the cephrepo file too
#
# [cephrepo]
# baseurl=http://ceph.com/rpm-emperor/el6/noarch
# gpgkey=https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/autobuild.asc
"""


def location():
    """
    Find and return the location of the ceph-deploy configuration file. If this
    file does not exist, create one in a default location.
    """
    return _locate_or_create()


def load():
    parser = Conf()
    parser.read(location())
    return parser


def _locate_or_create():
    home_config = path.expanduser('~/.cephdeploy.conf')
    # With order of importance
    locations = [
        path.join(os.getcwd(), 'cephdeploy.conf'),
        home_config,
    ]

    for location in locations:
        if path.exists(location):
            logger.debug('found configuration file at: %s' % location)
            return location
    logger.info('could not find configuration file, will create one in $HOME')
    create_stub(home_config)
    return home_config


def create_stub(_path=None):
    _path = _path or path.expanduser('~/.cephdeploy.conf')
    logger.debug('creating new configuration file: %s' % _path)
    with open(_path, 'w') as cd_conf:
        cd_conf.write(cd_conf_template)


def set_overrides(args, _conf=None):
    """
    Read the configuration file and look for ceph-deploy sections
    to set flags/defaults from the values found. This will alter the
    ``args`` object that is created by argparse.
    """
    # Get the subcommand name to avoid overwritting values from other
    # subcommands that are not going to be used
    subcommand = args.func.__name__
    command_section = 'ceph-deploy-%s' % subcommand
    conf = _conf or load()
    for section_name in conf.sections():
        if section_name in ['ceph-deploy-global', command_section]:
            override_subcommand(
                section_name,
                conf.items(section_name),
                args
            )
    return args


def override_subcommand(section_name, section_items, args):
    """
    Given a specific section in the configuration file that maps to
    a subcommand (except for the global section) read all the keys that are
    actual argument flags and slap the values for that one subcommand.

    Return the altered ``args`` object at the end.
    """
    # XXX We are not coercing here any int-like values, so if ArgParse
    # does that in the CLI we are totally non-compliant with that expectation
    for k, v, in section_items:
        setattr(args, k, v)
    return args


class Conf(SafeConfigParser):
    """
    Subclasses from SafeConfigParser to give a few helpers for the ceph-deploy
    configuration. Specifically, it addresses the need to work with custom
    sections that signal the usage of custom repositories.
    """

    reserved_sections = ['ceph-deploy-global', 'ceph-deploy-install']

    def get_safe(self, section, key, default=None):
        """
        Attempt to get a configuration value from a certain section
        in a ``cfg`` object but returning None if not found. Avoids the need
        to be doing try/except {ConfigParser Exceptions} every time.
        """
        try:
            return self.get(section, key)
        except (NoSectionError, NoOptionError):
            return default

    def get_repos(self):
        """
        Return all the repo sections from the config, excluding the ceph-deploy
        reserved sections.
        """
        return [
            section for section in self.sections()
            if section not in self.reserved_sections
        ]

    @property
    def has_repos(self):
        """
        boolean to reflect having (or not) any repository sections
        """
        for section in self.sections():
            if section not in self.reserved_sections:
                return True
        return False

    def get_list(self, section, key):
        """
        Assumes that the value for a given key is going to be a list
        separated by commas. It gets rid of trailing comments.
        If just one item is present it returns a list with a single item, if no
        key is found an empty list is returned.
        """
        value = self.get_safe(section, key, [])
        if value == []:
            return value

        # strip comments
        value = re.split(r'\s+#', value)[0]

        # split on commas
        value = value.split(',')

        # strip spaces
        return [x.strip() for x in value]

    def get_default_repo(self):
        """
        Go through all the repositories defined in the config file and search
        for a truthy value for the ``default`` key. If there isn't any return
        None.
        """
        for repo in self.get_repos():
            if self.get_safe(repo, 'default') and self.getboolean(repo, 'default'):
                return repo
        return False

########NEW FILE########
__FILENAME__ = config
import logging
import os.path

from ceph_deploy import exc
from ceph_deploy import conf
from ceph_deploy.cliutil import priority
from ceph_deploy import hosts

LOG = logging.getLogger(__name__)


def config_push(args):
    conf_data = conf.ceph.load_raw(args)

    errors = 0
    for hostname in args.client:
        LOG.debug('Pushing config to %s', hostname)
        try:
            distro = hosts.get(hostname, username=args.username)

            distro.conn.remote_module.write_conf(
                args.cluster,
                conf_data,
                args.overwrite_conf,
            )

            distro.conn.exit()

        except RuntimeError as e:
            LOG.error(e)
            errors += 1

    if errors:
        raise exc.GenericError('Failed to config %d hosts' % errors)


def config_pull(args):

    topath = '{cluster}.conf'.format(cluster=args.cluster)
    frompath = '/etc/ceph/{cluster}.conf'.format(cluster=args.cluster)

    errors = 0
    for hostname in args.client:
        try:
            LOG.debug('Checking %s for %s', hostname, frompath)
            distro = hosts.get(hostname, username=args.username)
            conf_file_contents = distro.conn.remote_module.get_file(frompath)

            if conf_file_contents is not None:
                LOG.debug('Got %s from %s', frompath, hostname)
                if os.path.exists(topath):
                    with file(topath, 'rb') as f:
                        existing = f.read()
                        if existing != conf_file_contents and not args.overwrite_conf:
                            LOG.error('local config file %s exists with different content; use --overwrite-conf to overwrite' % topath)
                            raise

                with file(topath, 'w') as f:
                    f.write(conf_file_contents)
                return
            distro.conn.exit()
            LOG.debug('Empty or missing %s on %s', frompath, hostname)
        except:
            LOG.error('Unable to pull %s from %s', frompath, hostname)
        finally:
            errors += 1

    raise exc.GenericError('Failed to fetch config from %d hosts' % errors)


def config(args):
    if args.subcommand == 'push':
        config_push(args)
    elif args.subcommand == 'pull':
        config_pull(args)
    else:
        LOG.error('subcommand %s not implemented', args.subcommand)


@priority(70)
def make(parser):
    """
    Push configuration file to a remote host.
    """
    parser.add_argument(
        'subcommand',
        metavar='SUBCOMMAND',
        choices=[
            'push',
            'pull',
            ],
        help='push or pull',
        )
    parser.add_argument(
        'client',
        metavar='HOST',
        nargs='*',
        help='host to push/pull the config to/from',
        )
    parser.set_defaults(
        func=config,
        )

########NEW FILE########
__FILENAME__ = connection
import getpass
import socket
from ceph_deploy.lib.remoto import Connection


def get_connection(hostname, username, logger, threads=5, use_sudo=None):
    """
    A very simple helper, meant to return a connection
    that will know about the need to use sudo.
    """
    if use_sudo is None:
        use_sudo = needs_sudo()
    if username:
        hostname = "%s@%s" % (username, hostname)
    try:
        conn = Connection(
            hostname,
            logger=logger,
            sudo=use_sudo,
            threads=threads,
        )

        # Set a timeout value in seconds to disconnect and move on
        # if no data is sent back.
        conn.global_timeout = 300
        logger.debug("connected to host: %s " % hostname)
        return conn

    except Exception as error:
        msg = "connecting to host: %s " % hostname
        errors = "resulted in errors: %s %s" % (error.__class__.__name__, error)
        raise RuntimeError(msg + errors)


def get_local_connection(logger, use_sudo=False):
    """
    Helper for local connections that are sometimes needed to operate
    on local hosts
    """
    return get_connection(
        socket.gethostname(),  # cannot rely on 'localhost' here
        None,
        logger=logger,
        threads=1,
        use_sudo=use_sudo
    )


def needs_sudo():
    if getpass.getuser() == 'root':
        return False
    return True

########NEW FILE########
__FILENAME__ = exc
class DeployError(Exception):
    """
    Unknown deploy error
    """

    def __str__(self):
        doc = self.__doc__.strip()
        return ': '.join([doc] + [str(a) for a in self.args])


class UnableToResolveError(DeployError):
    """
    Unable to resolve host
    """


class ClusterExistsError(DeployError):
    """
    Cluster config exists already
    """


class ConfigError(DeployError):
    """
    Cannot load config
    """


class NeedHostError(DeployError):
    """
    No hosts specified to deploy to.
    """


class NeedMonError(DeployError):
    """
    Cannot find nodes with ceph-mon.
    """


class NeedDiskError(DeployError):
    """
    Must supply disk/path argument
    """


class UnsupportedPlatform(DeployError):
    """
    Platform is not supported
    """
    def __init__(self, distro, codename, release):
        self.distro = distro
        self.codename = codename
        self.release = release

    def __str__(self):
        return '{doc}: {distro} {codename} {release}'.format(
            doc=self.__doc__.strip(),
            distro=self.distro,
            codename=self.codename,
            release=self.release,
        )


class MissingPackageError(DeployError):
    """
    A required package or command is missing
    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class GenericError(DeployError):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

########NEW FILE########
__FILENAME__ = forgetkeys
import logging
import errno

from .cliutil import priority


LOG = logging.getLogger(__name__)


def forgetkeys(args):
    import os
    for f in [
        'mon',
        'client.admin',
        'bootstrap-osd',
        'bootstrap-mds',
        ]:
        try:
            os.unlink('{cluster}.{what}.keyring'.format(
                    cluster=args.cluster,
                    what=f,
                    ))
        except OSError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise

@priority(100)
def make(parser):
    """
    Remove authentication keys from the local directory.
    """
    parser.set_defaults(
        func=forgetkeys,
        )

########NEW FILE########
__FILENAME__ = gatherkeys
import os.path
import logging

from .cliutil import priority
from . import hosts


LOG = logging.getLogger(__name__)


def fetch_file(args, frompath, topath, _hosts):
    if os.path.exists(topath):
        LOG.debug('Have %s', topath)
        return True
    else:
        for hostname in _hosts:
            LOG.debug('Checking %s for %s', hostname, frompath)
            distro = hosts.get(hostname, username=args.username)
            key = distro.conn.remote_module.get_file(
                frompath.format(hostname=hostname)
            )

            if key is not None:
                LOG.debug('Got %s key from %s.', topath, hostname)
                with file(topath, 'w') as f:
                    f.write(key)
                    return True
            distro.conn.exit()
    LOG.warning('Unable to find %s on %s', frompath, _hosts)
    return False


def gatherkeys(args):
    ret = 0

    # client.admin
    r = fetch_file(
        args=args,
        frompath='/etc/ceph/{cluster}.client.admin.keyring'.format(
            cluster=args.cluster),
        topath='{cluster}.client.admin.keyring'.format(
            cluster=args.cluster),
        _hosts=args.mon,
        )
    if not r:
        ret = 1

    # mon.
    r = fetch_file(
        args=args,
        frompath='/var/lib/ceph/mon/%s-{hostname}/keyring' % args.cluster,
        topath='{cluster}.mon.keyring'.format(cluster=args.cluster),
        _hosts=args.mon,
        )
    if not r:
        ret = 1

    # bootstrap
    for what in ['osd', 'mds']:
        r = fetch_file(
            args=args,
            frompath='/var/lib/ceph/bootstrap-{what}/{cluster}.keyring'.format(
                cluster=args.cluster,
                what=what),
            topath='{cluster}.bootstrap-{what}.keyring'.format(
                cluster=args.cluster,
                what=what),
            _hosts=args.mon,
            )
        if not r:
            ret = 1

    return ret


@priority(40)
def make(parser):
    """
    Gather authentication keys for provisioning new nodes.
    """
    parser.add_argument(
        'mon',
        metavar='HOST',
        nargs='+',
        help='monitor host to pull keys from',
        )
    parser.set_defaults(
        func=gatherkeys,
        )

########NEW FILE########
__FILENAME__ = install
from ceph_deploy.util import pkg_managers, templates
from ceph_deploy.lib.remoto import process


def install(distro, version_kind, version, adjust_repos):
    release = distro.release
    machine = distro.machine_type

    pkg_managers.yum_clean(distro.conn)

    # Even before EPEL, make sure we have `wget`
    pkg_managers.yum(distro.conn, 'wget')

    # Get EPEL installed before we continue:
    if adjust_repos:
        install_epel(distro)
    if version_kind in ['stable', 'testing']:
        key = 'release'
    else:
        key = 'autobuild'

    if adjust_repos:
        process.run(
            distro.conn,
            [
                'rpm',
                '--import',
                "https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/{key}.asc".format(key=key)
            ]
        )

        if version_kind == 'stable':
            url = 'http://ceph.com/rpm-{version}/el6/'.format(
                version=version,
                )
        elif version_kind == 'testing':
            url = 'http://ceph.com/rpm-testing/el6/'
        elif version_kind == 'dev':
            url = 'http://gitbuilder.ceph.com/ceph-rpm-centos{release}-{machine}-basic/ref/{version}/'.format(
                release=release.split(".",1)[0],
                machine=machine,
                version=version,
                )

        process.run(
            distro.conn,
            [
                'rpm',
                '-Uvh',
                '--replacepkgs',
                '{url}noarch/ceph-release-1-0.el6.noarch.rpm'.format(url=url),
            ],
        )

    process.run(
        distro.conn,
        [
            'yum',
            '-y',
            '-q',
            'install',
            'ceph',
        ],
    )


def install_epel(distro):
    """
    CentOS and Scientific need the EPEL repo, otherwise Ceph cannot be
    installed.
    """
    if distro.name.lower() in ['centos', 'scientific']:
        distro.conn.logger.info('adding EPEL repository')
        if float(distro.release) >= 6:
            process.run(
                distro.conn,
                ['wget', 'http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm'],
            )
            pkg_managers.rpm(
                distro.conn,
                [
                    '--replacepkgs',
                    'epel-release-6*.rpm',
                ],
            )
        else:
            process.run(
                distro.conn,
                ['wget', 'http://dl.fedoraproject.org/pub/epel/5/x86_64/epel-release-5-4.noarch.rpm'],
            )
            pkg_managers.rpm(
                distro.conn,
                [
                    '--replacepkgs',
                    'epel-release-5*.rpm'
                ],
            )


def mirror_install(distro, repo_url, gpg_url, adjust_repos):
    repo_url = repo_url.strip('/')  # Remove trailing slashes
    gpg_url_path = gpg_url.split('file://')[-1]  # Remove file if present

    pkg_managers.yum_clean(distro.conn)

    if adjust_repos:
        process.run(
            distro.conn,
            [
                'rpm',
                '--import',
                gpg_url_path,
            ]
        )

        ceph_repo_content = templates.ceph_repo.format(
            repo_url=repo_url,
            gpg_url=gpg_url
        )

        distro.conn.remote_module.write_yum_repo(ceph_repo_content)

    # Before any install, make sure we have `wget`
    pkg_managers.yum(distro.conn, 'wget')

    pkg_managers.yum(distro.conn, 'ceph')


def repo_install(distro, repo_name, baseurl, gpgkey, **kw):
    # Get some defaults
    name = kw.get('name', '%s repo' % repo_name)
    enabled = kw.get('enabled', 1)
    gpgcheck = kw.get('gpgcheck', 1)
    install_ceph = kw.pop('install_ceph', False)
    proxy = kw.get('proxy', '')
    _type = 'repo-md'
    baseurl = baseurl.strip('/')  # Remove trailing slashes

    pkg_managers.yum_clean(distro.conn)

    if gpgkey:
        process.run(
            distro.conn,
            [
                'rpm',
                '--import',
                gpgkey,
            ]
        )

    repo_content = templates.custom_repo.format(
        repo_name=repo_name,
        name = name,
        baseurl = baseurl,
        enabled = enabled,
        gpgcheck = gpgcheck,
        _type = _type,
        gpgkey = gpgkey,
        proxy = proxy,
    )

    distro.conn.remote_module.write_yum_repo(
        repo_content,
        "%s.repo" % repo_name
    )

    # Some custom repos do not need to install ceph
    if install_ceph:
        # Before any install, make sure we have `wget`
        pkg_managers.yum(distro.conn, 'wget')

        pkg_managers.yum(distro.conn, 'ceph')

########NEW FILE########
__FILENAME__ = create
from ceph_deploy.hosts import common
from ceph_deploy.lib.remoto import process


def create(distro, args, monitor_keyring):
    hostname = distro.conn.remote_module.shortname()
    common.mon_create(distro, args, monitor_keyring, hostname)
    service = distro.conn.remote_module.which_service()

    process.run(
        distro.conn,
        [
            service,
            'ceph',
            '-c',
            '/etc/ceph/{cluster}.conf'.format(cluster=args.cluster),
            'start',
            'mon.{hostname}'.format(hostname=hostname)
        ],
        timeout=7,
    )

########NEW FILE########
__FILENAME__ = pkg
from ceph_deploy.util import pkg_managers


def install(distro, packages):
    return pkg_managers.yum(
        distro.conn,
        packages
    )


def remove(distro, packages):
    return pkg_managers.yum_remove(
        distro.conn,
        packages
    )

########NEW FILE########
__FILENAME__ = uninstall
from ceph_deploy.util import pkg_managers


def uninstall(conn, purge=False):
    packages = [
        'ceph',
        'ceph-release',
        ]

    pkg_managers.yum_remove(
        conn,
        packages,
    )

    pkg_managers.yum_clean(conn)

########NEW FILE########
__FILENAME__ = common
from ceph_deploy.util import paths
from ceph_deploy import conf
from ceph_deploy.lib.remoto import process
from StringIO import StringIO


def ceph_version(conn):
    """
    Log the remote ceph-version by calling `ceph --version`
    """
    return process.run(conn, ['ceph', '--version'])


def mon_create(distro, args, monitor_keyring, hostname):
    logger = distro.conn.logger
    logger.debug('remote hostname: %s' % hostname)
    path = paths.mon.path(args.cluster, hostname)
    done_path = paths.mon.done(args.cluster, hostname)
    init_path = paths.mon.init(args.cluster, hostname, distro.init)

    configuration = conf.ceph.load(args)
    conf_data = StringIO()
    configuration.write(conf_data)

    # write the configuration file
    distro.conn.remote_module.write_conf(
        args.cluster,
        conf_data.getvalue(),
        args.overwrite_conf,
    )

    # if the mon path does not exist, create it
    distro.conn.remote_module.create_mon_path(path)

    logger.debug('checking for done path: %s' % done_path)
    if not distro.conn.remote_module.path_exists(done_path):
        logger.debug('done path does not exist: %s' % done_path)
        if not distro.conn.remote_module.path_exists(paths.mon.constants.tmp_path):
            logger.info('creating tmp path: %s' % paths.mon.constants.tmp_path)
            distro.conn.remote_module.makedir(paths.mon.constants.tmp_path)
        keyring = paths.mon.keyring(args.cluster, hostname)

        logger.info('creating keyring file: %s' % keyring)
        distro.conn.remote_module.write_monitor_keyring(
            keyring,
            monitor_keyring,
        )

        process.run(
            distro.conn,
            [
                'ceph-mon',
                '--cluster', args.cluster,
                '--mkfs',
                '-i', hostname,
                '--keyring', keyring,
            ],
        )

        logger.info('unlinking keyring file %s' % keyring)
        distro.conn.remote_module.unlink(keyring)

    # create the done file
    distro.conn.remote_module.create_done_path(done_path)

    # create init path
    distro.conn.remote_module.create_init_path(init_path)


def mon_add(distro, args, monitor_keyring):
    hostname = distro.conn.remote_module.shortname()
    logger = distro.conn.logger
    path = paths.mon.path(args.cluster, hostname)
    monmap_path = paths.mon.monmap(args.cluster, hostname)
    done_path = paths.mon.done(args.cluster, hostname)
    init_path = paths.mon.init(args.cluster, hostname, distro.init)

    configuration = conf.ceph.load(args)
    conf_data = StringIO()
    configuration.write(conf_data)

    # write the configuration file
    distro.conn.remote_module.write_conf(
        args.cluster,
        conf_data.getvalue(),
        args.overwrite_conf,
    )

    # if the mon path does not exist, create it
    distro.conn.remote_module.create_mon_path(path)

    logger.debug('checking for done path: %s' % done_path)
    if not distro.conn.remote_module.path_exists(done_path):
        logger.debug('done path does not exist: %s' % done_path)
        if not distro.conn.remote_module.path_exists(paths.mon.constants.tmp_path):
            logger.info('creating tmp path: %s' % paths.mon.constants.tmp_path)
            distro.conn.remote_module.makedir(paths.mon.constants.tmp_path)
        keyring = paths.mon.keyring(args.cluster, hostname)

        logger.info('creating keyring file: %s' % keyring)
        distro.conn.remote_module.write_monitor_keyring(
            keyring,
            monitor_keyring,
        )

        # get the monmap
        process.run(
            distro.conn,
            [
                'ceph',
                'mon',
                'getmap',
                '-o',
                monmap_path,
            ],
        )

        # now use it to prepare the monitor's data dir
        process.run(
            distro.conn,
            [
                'ceph-mon',
                '--cluster', args.cluster,
                '--mkfs',
                '-i', hostname,
                '--monmap',
                monmap_path,
                '--keyring', keyring,
            ],
        )

        # add it
        process.run(
            distro.conn,
            [
                'ceph',
                'mon',
                'add',
                hostname,
                args.address,
            ],
        )

        logger.info('unlinking keyring file %s' % keyring)
        distro.conn.remote_module.unlink(keyring)

    # create the done file
    distro.conn.remote_module.create_done_path(done_path)

    # create init path
    distro.conn.remote_module.create_init_path(init_path)

    # start the mon using the address
    process.run(
        distro.conn,
        [
            'ceph-mon',
            '-i',
            hostname,
            '--public-addr',
            args.address,
        ],
    )

########NEW FILE########
__FILENAME__ = install
from ceph_deploy.lib.remoto import process
from ceph_deploy.util import pkg_managers


def install(distro, version_kind, version, adjust_repos):
    codename = distro.codename
    machine = distro.machine_type

    if version_kind in ['stable', 'testing']:
        key = 'release'
    else:
        key = 'autobuild'

    # Make sure ca-certificates is installed
    process.run(
        distro.conn,
        [
            'env',
            'DEBIAN_FRONTEND=noninteractive',
            'apt-get',
            '-q',
            'install',
            '--assume-yes',
            'ca-certificates',
        ]
    )

    if adjust_repos:
        process.run(
            distro.conn,
            [
                'wget',
                '-O',
                '{key}.asc'.format(key=key),
                'https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/{key}.asc'.format(key=key),
            ],
            stop_on_nonzero=False,
        )

        process.run(
            distro.conn,
            [
                'apt-key',
                'add',
                '{key}.asc'.format(key=key)
            ]
        )

        if version_kind == 'stable':
            url = 'http://ceph.com/debian-{version}/'.format(
                version=version,
                )
        elif version_kind == 'testing':
            url = 'http://ceph.com/debian-testing/'
        elif version_kind == 'dev':
            url = 'http://gitbuilder.ceph.com/ceph-deb-{codename}-{machine}-basic/ref/{version}'.format(
                codename=codename,
                machine=machine,
                version=version,
                )
        else:
            raise RuntimeError('Unknown version kind: %r' % version_kind)

        distro.conn.remote_module.write_sources_list(url, codename)

    process.run(
        distro.conn,
        ['apt-get', '-q', 'update'],
        )

    # TODO this does not downgrade -- should it?
    process.run(
        distro.conn,
        [
            'env',
            'DEBIAN_FRONTEND=noninteractive',
            'DEBIAN_PRIORITY=critical',
            'apt-get',
            '-q',
            '-o', 'Dpkg::Options::=--force-confnew',
            '--no-install-recommends',
            '--assume-yes',
            'install',
            '--',
            'ceph',
            'ceph-mds',
            'ceph-common',
            'ceph-fs-common',
            # ceph only recommends gdisk, make sure we actually have
            # it; only really needed for osds, but minimal collateral
            'gdisk',
            ],
        )


def mirror_install(distro, repo_url, gpg_url, adjust_repos):
    repo_url = repo_url.strip('/')  # Remove trailing slashes
    gpg_path = gpg_url.split('file://')[-1]

    if adjust_repos:
        if not gpg_url.startswith('file://'):
            process.run(
                distro.conn,
                [
                    'wget',
                    '-O',
                    'release.asc',
                    gpg_url,
                ],
                stop_on_nonzero=False,
            )

        gpg_file = 'release.asc' if not gpg_url.startswith('file://') else gpg_path
        process.run(
            distro.conn,
            [
                'apt-key',
                'add',
                gpg_file,
            ]
        )

        distro.conn.remote_module.write_sources_list(repo_url, distro.codename)

    # Before any install, make sure we have `wget`
    pkg_managers.apt_update(distro.conn)
    packages = (
        'ceph',
        'ceph-mds',
        'ceph-common',
        'ceph-fs-common',
        # ceph only recommends gdisk, make sure we actually have
        # it; only really needed for osds, but minimal collateral
        'gdisk',
    )

    pkg_managers.apt(distro.conn, packages)
    pkg_managers.apt(distro.conn, 'ceph')


def repo_install(distro, repo_name, baseurl, gpgkey, **kw):
    # Get some defaults
    safe_filename = '%s.list' % repo_name.replace(' ', '-')
    install_ceph = kw.pop('install_ceph', False)
    baseurl = baseurl.strip('/')  # Remove trailing slashes

    if gpgkey:
        process.run(
            distro.conn,
            [
                'wget',
                '-O',
                'release.asc',
                gpgkey,
            ],
            stop_on_nonzero=False,
        )

    process.run(
        distro.conn,
        [
            'apt-key',
            'add',
            'release.asc'
        ]
    )

    distro.conn.remote_module.write_sources_list(
        baseurl,
        distro.codename,
        safe_filename
    )

    # repo is not operable until an update
    pkg_managers.apt_update(distro.conn)

    if install_ceph:
        # Before any install, make sure we have `wget`
        packages = (
            'ceph',
            'ceph-mds',
            'ceph-common',
            'ceph-fs-common',
            # ceph only recommends gdisk, make sure we actually have
            # it; only really needed for osds, but minimal collateral
            'gdisk',
        )

        pkg_managers.apt(distro.conn, packages)
        pkg_managers.apt(distro.conn, 'ceph')

########NEW FILE########
__FILENAME__ = create
from ceph_deploy.hosts import common
from ceph_deploy.lib.remoto import process


def create(distro, args, monitor_keyring):
    logger = distro.conn.logger
    hostname = distro.conn.remote_module.shortname()
    common.mon_create(distro, args, monitor_keyring, hostname)
    service = distro.conn.remote_module.which_service()

    if not service:
        logger.warning('could not find `service` executable')

    if distro.init == 'upstart':  # Ubuntu uses upstart
        process.run(
            distro.conn,
            [
                'initctl',
                'emit',
                'ceph-mon',
                'cluster={cluster}'.format(cluster=args.cluster),
                'id={hostname}'.format(hostname=hostname),
            ],
            timeout=7,
        )

    elif distro.init == 'sysvinit':  # Debian uses sysvinit

        process.run(
            distro.conn,
            [
                service,
                'ceph',
                '-c',
                '/etc/ceph/{cluster}.conf'.format(cluster=args.cluster),
                'start',
                'mon.{hostname}'.format(hostname=hostname)
            ],
            timeout=7,
        )
    else:
        raise RuntimeError('create cannot use init %s' % distro.init)

########NEW FILE########
__FILENAME__ = pkg
from ceph_deploy.util import pkg_managers


def install(distro, packages):
    return pkg_managers.apt(
        distro.conn,
        packages
    )


def remove(distro, packages):
    return pkg_managers.apt_remove(
        distro.conn,
        packages
    )

########NEW FILE########
__FILENAME__ = uninstall
from ceph_deploy.util import pkg_managers
from ceph_deploy.lib.remoto import process


def uninstall(conn, purge=False):
    packages = [
        'ceph',
        'ceph-mds',
        'ceph-common',
        'ceph-fs-common',
        ]
    pkg_managers.apt_remove(
        conn,
        packages,
        purge=purge,
    )

########NEW FILE########
__FILENAME__ = install
from ceph_deploy.util import pkg_managers, templates
from ceph_deploy.lib.remoto import process
from ceph_deploy.hosts.centos.install import repo_install, mirror_install  # noqa


def install(distro, version_kind, version, adjust_repos):
    release = distro.release
    machine = distro.machine_type

    if version_kind in ['stable', 'testing']:
        key = 'release'
    else:
        key = 'autobuild'

    if adjust_repos:
        process.run(
            distro.conn,
            [
                'rpm',
                '--import',
                "https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/{key}.asc".format(key=key)
            ]
        )

        if version_kind == 'stable':
            url = 'http://ceph.com/rpm-{version}/fc{release}/'.format(
                version=version,
                release=release,
                )
        elif version_kind == 'testing':
            url = 'http://ceph.com/rpm-testing/fc{release}'.format(
                release=release,
                )
        elif version_kind == 'dev':
            url = 'http://gitbuilder.ceph.com/ceph-rpm-fc{release}-{machine}-basic/ref/{version}/'.format(
                release=release.split(".", 1)[0],
                machine=machine,
                version=version,
                )

        process.run(
            distro.conn,
            [
                'rpm',
                '-Uvh',
                '--replacepkgs',
                '--force',
                '--quiet',
                '{url}noarch/ceph-release-1-0.fc{release}.noarch.rpm'.format(
                    url=url,
                    release=release,
                    ),
            ]
        )

    process.run(
        distro.conn,
        [
            'yum',
            '-y',
            '-q',
            'install',
            'ceph',
        ],
    )

########NEW FILE########
__FILENAME__ = create
from ceph_deploy.hosts import common
from ceph_deploy.lib.remoto import process


def create(distro, args, monitor_keyring):
    hostname = distro.conn.remote_module.shortname()
    common.mon_create(distro, args, monitor_keyring, hostname)
    service = distro.conn.remote_module.which_service()

    process.run(
        distro.conn,
        [
            service,
            'ceph',
            '-c',
            '/etc/ceph/{cluster}.conf'.format(cluster=args.cluster),
            'start',
            'mon.{hostname}'.format(hostname=hostname)
        ],
        timeout=7,
    )

########NEW FILE########
__FILENAME__ = uninstall
from ceph_deploy.util import pkg_managers


def uninstall(conn, purge=False):
    packages = [
        'ceph',
        ]

    pkg_managers.yum_remove(
        conn,
        packages,
    )


########NEW FILE########
__FILENAME__ = remotes
import errno
import socket
import os
import shutil
import tempfile
import platform


def platform_information(_linux_distribution=None):
    """ detect platform information from remote host """
    linux_distribution = _linux_distribution or platform.linux_distribution
    distro, release, codename = linux_distribution()
    if not codename and 'debian' in distro.lower():  # this could be an empty string in Debian
        debian_codenames = {
            '8': 'jessie',
            '7': 'wheezy',
            '6': 'squeeze',
        }
        major_version = release.split('.')[0]
        codename = debian_codenames.get(major_version, '')

        # In order to support newer jessie/sid or wheezy/sid strings we test this
        # if sid is buried in the minor, we should use sid anyway.
        if not codename and '/' in release:
            major, minor = release.split('/')
            if minor == 'sid':
                codename = minor
            else:
                codename = major

    return (
        str(distro).rstrip(),
        str(release).rstrip(),
        str(codename).rstrip()
    )


def machine_type():
    """ detect machine type """
    return platform.machine()


def write_sources_list(url, codename, filename='ceph.list'):
    """add deb repo to sources.list"""
    repo_path = os.path.join('/etc/apt/sources.list.d', filename)
    with file(repo_path, 'w') as f:
        f.write('deb {url} {codename} main\n'.format(
                url=url,
                codename=codename,
                ))


def write_yum_repo(content, filename='ceph.repo'):
    """set the contents of repo file to /etc/yum.repos.d/"""
    repo_path = os.path.join('/etc/yum.repos.d', filename)
    write_file(repo_path, content)


def write_conf(cluster, conf, overwrite):
    """ write cluster configuration to /etc/ceph/{cluster}.conf """
    path = '/etc/ceph/{cluster}.conf'.format(cluster=cluster)
    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    err_msg = 'config file %s exists with different content; use --overwrite-conf to overwrite' % path

    if os.path.exists(path):
        with file(path, 'rb') as f:
            old = f.read()
            if old != conf and not overwrite:
                raise RuntimeError(err_msg)
        tmp_file.write(conf)
        tmp_file.close()
        shutil.move(tmp_file.name, path)
        os.chmod(path, 0644)
        return
    if os.path.exists('/etc/ceph'):
        with open(path, 'w') as f:
            f.write(conf)
        os.chmod(path, 0644)
    else:
        err_msg = '/etc/ceph/ does not exist - could not write config'
        raise RuntimeError(err_msg)


def write_keyring(path, key):
    """ create a keyring file """
    # Note that we *require* to avoid deletion of the temp file
    # otherwise we risk not being able to copy the contents from
    # one file system to the other, hence the `delete=False`
    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    tmp_file.write(key)
    tmp_file.close()
    shutil.move(tmp_file.name, path)


def create_mon_path(path):
    """create the mon path if it does not exist"""
    if not os.path.exists(path):
        os.makedirs(path)


def create_done_path(done_path):
    """create a done file to avoid re-doing the mon deployment"""
    with file(done_path, 'w'):
        pass


def create_init_path(init_path):
    """create the init path if it does not exist"""
    if not os.path.exists(init_path):
        with file(init_path, 'w'):
            pass


def append_to_file(file_path, contents):
    """append contents to file"""
    with open(file_path, 'a') as f:
        f.write(contents)


def readline(path):
    with open(path) as _file:
        return _file.readline().strip('\n')

def path_exists(path):
    return os.path.exists(path)


def get_realpath(path):
    return os.path.realpath(path)


def listdir(path):
    return os.listdir(path)


def makedir(path, ignored=None):
    ignored = ignored or []
    try:
        os.makedirs(path)
    except OSError as error:
        if error.errno in ignored:
            pass
        else:
            # re-raise the original exception
            raise


def unlink(_file):
    os.unlink(_file)


def write_monitor_keyring(keyring, monitor_keyring):
    """create the monitor keyring file"""
    write_file(keyring, monitor_keyring)


def write_file(path, content):
    with file(path, 'w') as f:
        f.write(content)


def touch_file(path):
    with file(path, 'wb') as f:  # noqa
        pass


def get_file(path):
    """ fetch remote file """
    try:
        with file(path, 'rb') as f:
            return f.read()
    except IOError:
        pass


def shortname():
    """get remote short hostname"""
    return socket.gethostname().split('.', 1)[0]


def which_service():
    """ locating the `service` executable... """
    # XXX This should get deprecated at some point. For now
    # it just bypasses and uses the new helper.
    return which('service')


def which(executable):
    """find the location of an executable"""
    locations = (
        '/usr/local/bin',
        '/bin',
        '/usr/bin',
        '/usr/local/sbin',
        '/usr/sbin',
        '/sbin',
    )

    for location in locations:
        executable_path = os.path.join(location, executable)
        if os.path.exists(executable_path):
            return executable_path


def make_mon_removed_dir(path, file_name):
    """ move old monitor data """
    try:
        os.makedirs('/var/lib/ceph/mon-removed')
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise
    shutil.move(path, os.path.join('/var/lib/ceph/mon-removed/', file_name))


def safe_mkdir(path):
    """ create path if it doesn't exist """
    try:
        os.mkdir(path)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise


def zeroing(dev):
    """ zeroing last few blocks of device """
    # this kills the crab
    #
    # sgdisk will wipe out the main copy of the GPT partition
    # table (sorry), but it doesn't remove the backup copies, and
    # subsequent commands will continue to complain and fail when
    # they see those.  zeroing the last few blocks of the device
    # appears to do the trick.
    lba_size = 4096
    size = 33 * lba_size
    return True
    with file(dev, 'wb') as f:
        f.seek(-size, os.SEEK_END)
        f.write(size*'\0')


# remoto magic, needed to execute these functions remotely
if __name__ == '__channelexec__':
    for item in channel:  # noqa
        channel.send(eval(item))  # noqa

########NEW FILE########
__FILENAME__ = install
from ceph_deploy.util import templates, pkg_managers
from ceph_deploy.lib.remoto import process
import logging
LOG = logging.getLogger(__name__)


def install(distro, version_kind, version, adjust_repos):
    release = distro.release
    machine = distro.machine_type

    if version_kind in ['stable', 'testing']:
        key = 'release'
    else:
        key = 'autobuild'


    distro_name = None
    if distro.codename == 'Mantis':
        distro_name = 'opensuse12.2'

    if (distro.name == "SUSE Linux Enterprise Server") and (str(distro.release) == "11"):
        distro_name = 'sles11'

    if distro_name == None:
        LOG.warning('Untested version of %s: assuming compatible with SUSE Linux Enterprise Server 11', distro.name)
        distro_name = 'sles11'


    if adjust_repos:
        # Work around code due to bug in SLE 11
        # https://bugzilla.novell.com/show_bug.cgi?id=875170
        protocol = "https"
        if distro_name == 'sles11':
            protocol = "http"
        process.run(
            distro.conn,
            [
                'rpm',
                '--import',
                "{protocol}://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/{key}.asc".format(
                    key=key,
                    protocol=protocol)
            ]
        )

        if version_kind == 'stable':
            url = 'http://ceph.com/rpm-{version}/{distro}/'.format(
                version=version,
                distro=distro_name,
                )
        elif version_kind == 'testing':
            url = 'http://ceph.com/rpm-testing/{distro}/'.format(distro=distro_name)
        elif version_kind == 'dev':
            url = 'http://gitbuilder.ceph.com/ceph-rpm-{distro}{release}-{machine}-basic/ref/{version}/'.format(
                distro=distro_name,
                release=release.split(".", 1)[0],
                machine=machine,
                version=version,
                )

        process.run(
            distro.conn,
            [
                'rpm',
                '-Uvh',
                '--replacepkgs',
                '--force',
                '--quiet',
                '{url}ceph-release-1-0.noarch.rpm'.format(
                    url=url,
                    ),
                ]
            )

    process.run(
        distro.conn,
        [
            'zypper',
            '--non-interactive',
            '--quiet',
            'install',
            'ceph',
            ],
        )


def mirror_install(distro, repo_url, gpg_url, adjust_repos):
    repo_url = repo_url.strip('/')  # Remove trailing slashes
    gpg_url_path = gpg_url.split('file://')[-1]  # Remove file if present

    if adjust_repos:
        process.run(
            distro.conn,
            [
                'rpm',
                '--import',
                gpg_url_path,
            ]
        )

        ceph_repo_content = templates.ceph_repo.format(
            repo_url=repo_url,
            gpg_url=gpg_url
        )

        distro.conn.remote_module.write_yum_repo(ceph_repo_content)

    process.run(
        distro.conn,
        [
            'zypper',
            '--non-interactive',
            '--quiet',
            'install',
            'ceph',
            ],
        )


def repo_install(distro, repo_name, baseurl, gpgkey, **kw):
    # Get some defaults
    name = kw.get('name', '%s repo' % repo_name)
    enabled = kw.get('enabled', 1)
    gpgcheck = kw.get('gpgcheck', 1)
    install_ceph = kw.pop('install_ceph', False)
    _type = 'repo-md'
    baseurl = baseurl.strip('/')  # Remove trailing slashes

    if gpgkey:
        process.run(
            distro.conn,
            [
                'rpm',
                '--import',
                gpgkey,
            ]
        )

    repo_content = templates.custom_repo.format(
        repo_name=repo_name,
        name = name,
        baseurl = baseurl,
        enabled = enabled,
        gpgcheck = gpgcheck,
        _type = _type,
        gpgkey = gpgkey,
    )

    distro.conn.remote_module.write_yum_repo(
        repo_content,
        "%s.repo" % repo_name
    )

    # Some custom repos do not need to install ceph
    if install_ceph:
        # Before any install, make sure we have `wget`
        pkg_managers.zypper(distro.conn, 'wget')

        pkg_managers.zypper(distro.conn, 'ceph')

########NEW FILE########
__FILENAME__ = create
from ceph_deploy.hosts import common
from ceph_deploy.lib.remoto import process


def create(distro, args, monitor_keyring):
    hostname = distro.conn.remote_module.shortname()
    common.mon_create(distro, args, monitor_keyring, hostname)

    process.run(
        distro.conn,
        [
            'rcceph',
            '-c',
            '/etc/ceph/{cluster}.conf'.format(cluster=args.cluster),
            'start',
            'mon.{hostname}'.format(hostname=hostname)
        ],
        timeout=7,
    )

########NEW FILE########
__FILENAME__ = pkg
from ceph_deploy.util import pkg_managers


def install(distro, packages):
    return pkg_managers.zypper(
        distro.conn,
        packages
    )


def remove(distro, packages):
    return pkg_managers.zypper_remove(
        distro.conn,
        packages
    )

########NEW FILE########
__FILENAME__ = uninstall
from ceph_deploy.lib.remoto import process


def uninstall(conn, purge=False):
    packages = [
        'ceph',
        'libcephfs1',
        'librados2',
        'librbd1',
        ]
    cmd = [
        'zypper',
        '--non-interactive',
        '--quiet',
        'remove',
        ]

    cmd.extend(packages)
    process.run(conn, cmd)

########NEW FILE########
__FILENAME__ = install
import argparse
import logging
import os

from ceph_deploy import hosts
from ceph_deploy.cliutil import priority
from ceph_deploy.lib.remoto import process, rsync


LOG = logging.getLogger(__name__)


def install(args):
    # XXX This whole dance is because --stable is getting deprecated
    if args.stable is not None:
        LOG.warning('the --stable flag is deprecated, use --release instead')
        args.release = args.stable
    if args.version_kind == 'stable':
        version = args.release
    else:
        version = getattr(args, args.version_kind)
    # XXX Tango ends here.

    version_str = args.version_kind

    if version:
        version_str += ' version {version}'.format(version=version)
    LOG.debug(
        'Installing %s on cluster %s hosts %s',
        version_str,
        args.cluster,
        ' '.join(args.host),
    )

    for hostname in args.host:
        LOG.debug('Detecting platform for host %s ...', hostname)
        distro = hosts.get(hostname, username=args.username)
        LOG.info(
            'Distro info: %s %s %s',
            distro.name,
            distro.release,
            distro.codename
        )

        if distro.init == 'sysvinit' and args.cluster != 'ceph':
            LOG.error('refusing to install on host: %s, with custom cluster name: %s' % (
                    hostname,
                    args.cluster,
                )
            )
            LOG.error('custom cluster names are not supported on sysvinit hosts')
            continue

        rlogger = logging.getLogger(hostname)
        rlogger.info('installing ceph on %s' % hostname)

        cd_conf = getattr(args, 'cd_conf', None)

        # custom repo arguments
        repo_url = os.environ.get('CEPH_DEPLOY_REPO_URL') or args.repo_url
        gpg_url = os.environ.get('CEPH_DEPLOY_GPG_URL') or args.gpg_url
        gpg_fallback = 'https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc'

        if gpg_url is None and repo_url:
            LOG.warning('--gpg-url was not used, will fallback')
            LOG.warning('using GPG fallback: %s', gpg_fallback)
            gpg_url = gpg_fallback

        if args.local_mirror:
            rsync(hostname, args.local_mirror, '/opt/ceph-deploy/repo', distro.conn.logger, sudo=True)
            repo_url = 'file:///opt/ceph-deploy/repo'
            gpg_url = 'file:///opt/ceph-deploy/repo/release.asc'

        if repo_url:  # triggers using a custom repository
            # the user used a custom repo url, this should override anything
            # we can detect from the configuration, so warn about it
            if cd_conf:
                if cd_conf.get_default_repo():
                    rlogger.warning('a default repo was found but it was \
                        overridden on the CLI')
                if args.release in cd_conf.get_repos():
                    rlogger.warning('a custom repo was found but it was \
                        overridden on the CLI')

            rlogger.info('using custom repository location: %s', repo_url)
            distro.mirror_install(
                distro,
                repo_url,
                gpg_url,
                args.adjust_repos
            )

        # Detect and install custom repos here if needed
        elif should_use_custom_repo(args, cd_conf, repo_url):
            LOG.info('detected valid custom repositories from config file')
            custom_repo(distro, args, cd_conf, rlogger)

        else:  # otherwise a normal installation
            distro.install(
                distro,
                args.version_kind,
                version,
                args.adjust_repos
            )

        # Check the ceph version we just installed
        hosts.common.ceph_version(distro.conn)
        distro.conn.exit()


def should_use_custom_repo(args, cd_conf, repo_url):
    """
    A boolean to determine the logic needed to proceed with a custom repo
    installation instead of cramming everything nect to the logic operator.
    """
    if repo_url:
        # repo_url signals a CLI override, return False immediately
        return False
    if cd_conf:
        if cd_conf.has_repos:
            has_valid_release = args.release in cd_conf.get_repos()
            has_default_repo = cd_conf.get_default_repo()
            if has_valid_release or has_default_repo:
                return True
    return False


def custom_repo(distro, args, cd_conf, rlogger):
    """
    A custom repo install helper that will go through config checks to retrieve
    repos (and any extra repos defined) and install those

    ``cd_conf`` is the object built from argparse that holds the flags and
    information needed to determine what metadata from the configuration to be
    used.
    """
    default_repo = cd_conf.get_default_repo()
    if args.release in cd_conf.get_repos():
        LOG.info('will use repository from conf: %s' % args.release)
        default_repo = args.release
    elif default_repo:
        LOG.info('will use default repository: %s' % default_repo)

    # At this point we know there is a cd_conf and that it has custom
    # repos make sure we were able to detect and actual repo
    if not default_repo:
        LOG.warning('a ceph-deploy config was found with repos \
            but could not default to one')
    else:
        options = dict(cd_conf.items(default_repo))
        options['install_ceph'] = True
        extra_repos = cd_conf.get_list(default_repo, 'extra-repos')
        rlogger.info('adding custom repository file')
        try:
            distro.repo_install(
                distro,
                default_repo,
                options.pop('baseurl'),
                options.pop('gpgkey'),
                **options
            )
        except KeyError as err:
            raise RuntimeError('missing required key: %s in config section: %s' % (err, default_repo))

        for xrepo in extra_repos:
            rlogger.info('adding extra repo file: %s.repo' % xrepo)
            options = dict(cd_conf.items(xrepo))
            try:
                distro.repo_install(
                    distro,
                    xrepo,
                    options.pop('baseurl'),
                    options.pop('gpgkey'),
                    **options
                )
            except KeyError as err:
                raise RuntimeError('missing required key: %s in config section: %s' % (err, xrepo))


def uninstall(args):
    LOG.info('note that some dependencies *will not* be removed because they can cause issues with qemu-kvm')
    LOG.info('like: librbd1 and librados2')
    LOG.debug(
        'Uninstalling on cluster %s hosts %s',
        args.cluster,
        ' '.join(args.host),
        )

    for hostname in args.host:
        LOG.debug('Detecting platform for host %s ...', hostname)

        distro = hosts.get(hostname, username=args.username)
        LOG.info('Distro info: %s %s %s', distro.name, distro.release, distro.codename)
        rlogger = logging.getLogger(hostname)
        rlogger.info('uninstalling ceph on %s' % hostname)
        distro.uninstall(distro.conn)
        distro.conn.exit()


def purge(args):
    LOG.info('note that some dependencies *will not* be removed because they can cause issues with qemu-kvm')
    LOG.info('like: librbd1 and librados2')

    LOG.debug(
        'Purging from cluster %s hosts %s',
        args.cluster,
        ' '.join(args.host),
        )

    for hostname in args.host:
        LOG.debug('Detecting platform for host %s ...', hostname)

        distro = hosts.get(hostname, username=args.username)
        LOG.info('Distro info: %s %s %s', distro.name, distro.release, distro.codename)
        rlogger = logging.getLogger(hostname)
        rlogger.info('purging host ... %s' % hostname)
        distro.uninstall(distro.conn, purge=True)
        distro.conn.exit()


def purgedata(args):
    LOG.debug(
        'Purging data from cluster %s hosts %s',
        args.cluster,
        ' '.join(args.host),
        )

    installed_hosts = []
    for hostname in args.host:
        distro = hosts.get(hostname, username=args.username)
        ceph_is_installed = distro.conn.remote_module.which('ceph')
        if ceph_is_installed:
            installed_hosts.append(hostname)
        distro.conn.exit()

    if installed_hosts:
        LOG.error("ceph is still installed on: %s", installed_hosts)
        raise RuntimeError("refusing to purge data while ceph is still installed")

    for hostname in args.host:
        distro = hosts.get(hostname, username=args.username)
        LOG.info(
            'Distro info: %s %s %s',
            distro.name,
            distro.release,
            distro.codename
        )

        rlogger = logging.getLogger(hostname)
        rlogger.info('purging data on %s' % hostname)

        # Try to remove the contents of /var/lib/ceph first, don't worry
        # about errors here, we deal with them later on
        process.check(
            distro.conn,
            [
                'rm', '-rf', '--one-file-system', '--', '/var/lib/ceph',
            ]
        )

        # If we failed in the previous call, then we probably have OSDs
        # still mounted, so we unmount them here
        if distro.conn.remote_module.path_exists('/var/lib/ceph'):
            rlogger.warning(
                'OSDs may still be mounted, trying to unmount them'
            )
            process.run(
                distro.conn,
                [
                    'find', '/var/lib/ceph',
                    '-mindepth', '1',
                    '-maxdepth', '2',
                    '-type', 'd',
                    '-exec', 'umount', '{}', ';',
                ]
            )

            # And now we try again to remove the contents, since OSDs should be
            # unmounted, but this time we do check for errors
            process.run(
                distro.conn,
                [
                    'rm', '-rf', '--one-file-system', '--', '/var/lib/ceph',
                ]
            )

        process.run(
            distro.conn,
            [
                'rm', '-rf', '--one-file-system', '--', '/etc/ceph/',
            ]
        )

        distro.conn.exit()


class StoreVersion(argparse.Action):
    """
    Like ``"store"`` but also remember which one of the exclusive
    options was set.

    There are three kinds of versions: stable, testing and dev.
    This sets ``version_kind`` to be the right one of the above.

    This kludge essentially lets us differentiate explicitly set
    values from defaults.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        if self.dest == 'release':
            self.dest = 'stable'
        namespace.version_kind = self.dest


@priority(20)
def make(parser):
    """
    Install Ceph packages on remote hosts.
    """

    version = parser.add_mutually_exclusive_group()

    # XXX deprecated in favor of release
    version.add_argument(
        '--stable',
        nargs='?',
        action=StoreVersion,
        metavar='CODENAME',
        help='[DEPRECATED] install a release known as CODENAME\
                (done by default) (default: %(default)s)',
    )

    version.add_argument(
        '--release',
        nargs='?',
        action=StoreVersion,
        metavar='CODENAME',
        help='install a release known as CODENAME\
                (done by default) (default: %(default)s)',
    )

    version.add_argument(
        '--testing',
        nargs=0,
        action=StoreVersion,
        help='install the latest development release',
    )

    version.add_argument(
        '--dev',
        nargs='?',
        action=StoreVersion,
        const='master',
        metavar='BRANCH_OR_TAG',
        help='install a bleeding edge build from Git branch\
                or tag (default: %(default)s)',
    )

    version.add_argument(
        '--adjust-repos',
        dest='adjust_repos',
        action='store_true',
        help='install packages modifying source repos',
    )

    version.add_argument(
        '--no-adjust-repos',
        dest='adjust_repos',
        action='store_false',
        help='install packages without modifying source repos',
    )

    version.set_defaults(
        func=install,
        stable=None,  # XXX deprecated in favor of release
        release='firefly',
        dev='master',
        version_kind='stable',
        adjust_repos=True,
    )

    parser.add_argument(
        'host',
        metavar='HOST',
        nargs='+',
        help='hosts to install on',
    )

    parser.add_argument(
        '--local-mirror',
        nargs='?',
        const='PATH',
        default=None,
        help='Fetch packages and push them to hosts for a local repo mirror',
    )

    parser.add_argument(
        '--repo-url',
        nargs='?',
        dest='repo_url',
        help='specify a repo URL that mirrors/contains ceph packages',
    )

    parser.add_argument(
        '--gpg-url',
        nargs='?',
        dest='gpg_url',
        help='specify a GPG key URL to be used with custom repos\
                (defaults to ceph.com)'
    )

    parser.set_defaults(
        func=install,
    )


@priority(80)
def make_uninstall(parser):
    """
    Remove Ceph packages from remote hosts.
    """
    parser.add_argument(
        'host',
        metavar='HOST',
        nargs='+',
        help='hosts to uninstall Ceph from',
        )
    parser.set_defaults(
        func=uninstall,
        )


@priority(80)
def make_purge(parser):
    """
    Remove Ceph packages from remote hosts and purge all data.
    """
    parser.add_argument(
        'host',
        metavar='HOST',
        nargs='+',
        help='hosts to purge Ceph from',
        )
    parser.set_defaults(
        func=purge,
        )


@priority(80)
def make_purge_data(parser):
    """
    Purge (delete, destroy, discard, shred) any Ceph data from /var/lib/ceph
    """
    parser.add_argument(
        'host',
        metavar='HOST',
        nargs='+',
        help='hosts to purge Ceph data from',
        )
    parser.set_defaults(
        func=purgedata,
        )

########NEW FILE########
__FILENAME__ = mds
from cStringIO import StringIO
import errno
import logging
import os

from ceph_deploy import conf
from ceph_deploy import exc
from ceph_deploy import hosts
from ceph_deploy.lib.remoto import process
from ceph_deploy.cliutil import priority


LOG = logging.getLogger(__name__)


def get_bootstrap_mds_key(cluster):
    """
    Read the bootstrap-mds key for `cluster`.
    """
    path = '{cluster}.bootstrap-mds.keyring'.format(cluster=cluster)
    try:
        with file(path, 'rb') as f:
            return f.read()
    except IOError:
        raise RuntimeError('bootstrap-mds keyring not found; run \'gatherkeys\'')


def create_mds(conn, name, cluster, init):

    path = '/var/lib/ceph/mds/{cluster}-{name}'.format(
        cluster=cluster,
        name=name
        )

    conn.remote_module.safe_mkdir(path)

    bootstrap_keyring = '/var/lib/ceph/bootstrap-mds/{cluster}.keyring'.format(
        cluster=cluster
        )

    keypath = os.path.join(path, 'keyring')

    stdout, stderr, returncode = process.check(
        conn,
        [
            'ceph',
            '--cluster', cluster,
            '--name', 'client.bootstrap-mds',
            '--keyring', bootstrap_keyring,
            'auth', 'get-or-create', 'mds.{name}'.format(name=name),
            'osd', 'allow rwx',
            'mds', 'allow',
            'mon', 'allow profile mds',
            '-o',
            os.path.join(keypath),
        ]
    )
    if returncode > 0 and returncode != errno.EACCES:
        for line in stderr:
            conn.logger.error(line)
        for line in stdout:
            # yes stdout as err because this is an error
            conn.logger.error(line)
        conn.logger.error('exit code from command was: %s' % returncode)
        raise RuntimeError('could not create mds')

        process.check(
            conn,
            [
                'ceph',
                '--cluster', cluster,
                '--name', 'client.bootstrap-mds',
                '--keyring', bootstrap_keyring,
                'auth', 'get-or-create', 'mds.{name}'.format(name=name),
                'osd', 'allow *',
                'mds', 'allow',
                'mon', 'allow rwx',
                '-o',
                os.path.join(keypath),
            ]
        )

    conn.remote_module.touch_file(os.path.join(path, 'done'))
    conn.remote_module.touch_file(os.path.join(path, init))

    if init == 'upstart':
        process.run(
            conn,
            [
                'initctl',
                'emit',
                'ceph-mds',
                'cluster={cluster}'.format(cluster=cluster),
                'id={name}'.format(name=name),
            ],
            timeout=7
        )
    elif init == 'sysvinit':
        process.run(
            conn,
            [
                'service',
                'ceph',
                'start',
                'mds.{name}'.format(name=name),
            ],
            timeout=7
        )


def mds_create(args):
    cfg = conf.ceph.load(args)
    LOG.debug(
        'Deploying mds, cluster %s hosts %s',
        args.cluster,
        ' '.join(':'.join(x or '' for x in t) for t in args.mds),
        )

    if not args.mds:
        raise exc.NeedHostError()

    key = get_bootstrap_mds_key(cluster=args.cluster)

    bootstrapped = set()
    errors = 0
    for hostname, name in args.mds:
        try:
            distro = hosts.get(hostname, username=args.username)
            rlogger = distro.conn.logger
            LOG.info(
                'Distro info: %s %s %s',
                distro.name,
                distro.release,
                distro.codename
            )
            LOG.debug('remote host will use %s', distro.init)

            if hostname not in bootstrapped:
                bootstrapped.add(hostname)
                LOG.debug('deploying mds bootstrap to %s', hostname)
                conf_data = StringIO()
                cfg.write(conf_data)
                distro.conn.remote_module.write_conf(
                    args.cluster,
                    conf_data.getvalue(),
                    args.overwrite_conf,
                )

                path = '/var/lib/ceph/bootstrap-mds/{cluster}.keyring'.format(
                    cluster=args.cluster,
                )

                if not distro.conn.remote_module.path_exists(path):
                    rlogger.warning('mds keyring does not exist yet, creating one')
                    distro.conn.remote_module.write_keyring(path, key)

            create_mds(distro.conn, name, args.cluster, distro.init)
            distro.conn.exit()
        except RuntimeError as e:
            LOG.error(e)
            errors += 1

    if errors:
        raise exc.GenericError('Failed to create %d MDSs' % errors)


def mds(args):
    if args.subcommand == 'create':
        mds_create(args)
    else:
        LOG.error('subcommand %s not implemented', args.subcommand)


def colon_separated(s):
    host = s
    name = s
    if s.count(':') == 1:
        (host, name) = s.split(':')
    return (host, name)


@priority(30)
def make(parser):
    """
    Deploy ceph MDS on remote hosts.
    """
    parser.add_argument(
        'subcommand',
        metavar='SUBCOMMAND',
        choices=[
            'create',
            'destroy',
            ],
        help='create or destroy',
        )
    parser.add_argument(
        'mds',
        metavar='HOST[:NAME]',
        nargs='*',
        type=colon_separated,
        help='host (and optionally the daemon name) to deploy on',
        )
    parser.set_defaults(
        func=mds,
        )

########NEW FILE########
__FILENAME__ = misc

def mon_hosts(mons):
    """
    Iterate through list of MON hosts, return tuples of (name, host).
    """
    for m in mons:
        if m.count(':'):
            (name, host) = m.split(':')
        else:
            name = m
            host = m
            if name.count('.') > 0:
                name = name.split('.')[0]
        yield (name, host)

def remote_shortname(socket):
    """
    Obtains remote hostname of the socket and cuts off the domain part
    of its FQDN.
    """
    return socket.gethostname().split('.', 1)[0]


########NEW FILE########
__FILENAME__ = mon
import argparse
import json
import logging
import re
import os
from textwrap import dedent
import time

from ceph_deploy import conf, exc, admin
from ceph_deploy.cliutil import priority
from ceph_deploy.util import paths, net
from ceph_deploy.lib.remoto import process
from ceph_deploy import hosts
from ceph_deploy.misc import mon_hosts
from ceph_deploy.connection import get_connection
from ceph_deploy import gatherkeys


LOG = logging.getLogger(__name__)


def mon_status_check(conn, logger, hostname, args):
    """
    A direct check for JSON output on the monitor status.

    For newer versions of Ceph (dumpling and newer) a new mon_status command
    was added ( `ceph daemon mon mon_status` ) and should be revisited if the
    output changes as this check depends on that availability.

    """
    asok_path = paths.mon.asok(args.cluster, hostname)

    out, err, code = process.check(
        conn,
        [
            'ceph',
            '--cluster={cluster}'.format(cluster=args.cluster),
            '--admin-daemon',
            asok_path,
            'mon_status',
        ],
    )

    for line in err:
        logger.error(line)

    try:
        return json.loads(''.join(out))
    except ValueError:
        return {}


def catch_mon_errors(conn, logger, hostname, cfg, args):
    """
    Make sure we are able to catch up common mishaps with monitors
    and use that state of a monitor to determine what is missing
    and warn apropriately about it.
    """
    monmap = mon_status_check(conn, logger, hostname, args).get('monmap', {})
    mon_initial_members = cfg.safe_get('global', 'mon_initial_members')
    public_addr = cfg.safe_get('global', 'public_addr')
    public_network = cfg.safe_get('global', 'public_network')
    mon_in_monmap = [
        mon.get('name')
        for mon in monmap.get('mons', [{}])
        if mon.get('name') == hostname
    ]
    if mon_initial_members is None or not hostname in mon_initial_members:
            logger.warning('%s is not defined in `mon initial members`', hostname)
    if not mon_in_monmap:
        logger.warning('monitor %s does not exist in monmap', hostname)
        if not public_addr and not public_network:
            logger.warning('neither `public_addr` nor `public_network` keys are defined for monitors')
            logger.warning('monitors may not be able to form quorum')


def mon_status(conn, logger, hostname, args, silent=False):
    """
    run ``ceph daemon mon.`hostname` mon_status`` on the remote end and provide
    not only the output, but be able to return a boolean status of what is
    going on.
    ``False`` represents a monitor that is not doing OK even if it is up and
    running, while ``True`` would mean the monitor is up and running correctly.
    """
    mon = 'mon.%s' % hostname

    try:
        out = mon_status_check(conn, logger, hostname, args)
        if not out:
            logger.warning('monitor: %s, might not be running yet' % mon)
            return False

        if not silent:
            logger.debug('*'*80)
            logger.debug('status for monitor: %s' % mon)
            for line in json.dumps(out, indent=2, sort_keys=True).split('\n'):
                logger.debug(line)
            logger.debug('*'*80)
        if out['rank'] >= 0:
            logger.info('monitor: %s is running' % mon)
            return True
        logger.info('monitor: %s is not running' % mon)
        return False
    except RuntimeError:
        logger.info('monitor: %s is not running' % mon)
        return False


def mon_add(args):
    cfg = conf.ceph.load(args)

    if not args.mon:
        raise exc.NeedHostError()
    mon_host = args.mon[0]
    try:
        with file('{cluster}.mon.keyring'.format(cluster=args.cluster),
                  'rb') as f:
            monitor_keyring = f.read()
    except IOError:
        raise RuntimeError(
            'mon keyring not found; run \'new\' to create a new cluster'
        )

    LOG.info('ensuring configuration of new mon host: %s', mon_host)
    args.client = [mon_host]
    admin.admin(args)
    LOG.debug(
        'Adding mon to cluster %s, host %s',
        args.cluster,
        mon_host,
    )

    mon_section = 'mon.%s' % mon_host
    cfg_mon_addr = cfg.safe_get(mon_section, 'mon addr')

    if args.address:
        LOG.debug('using mon address via --address %s' % args.address)
        mon_ip = args.address
    elif cfg_mon_addr:
        LOG.debug('using mon address via configuration: %s' % cfg_mon_addr)
        mon_ip = cfg_mon_addr
    else:
        mon_ip = net.get_nonlocal_ip(mon_host)
        LOG.debug('using mon address by resolving host: %s' % mon_ip)

    try:
        LOG.debug('detecting platform for host %s ...', mon_host)
        distro = hosts.get(mon_host, username=args.username)
        LOG.info('distro info: %s %s %s', distro.name, distro.release, distro.codename)
        rlogger = logging.getLogger(mon_host)

        # ensure remote hostname is good to go
        hostname_is_compatible(distro.conn, rlogger, mon_host)
        rlogger.debug('adding mon to %s', mon_host)
        args.address = mon_ip
        distro.mon.add(distro, args, monitor_keyring)

        # tell me the status of the deployed mon
        time.sleep(2)  # give some room to start
        catch_mon_errors(distro.conn, rlogger, mon_host, cfg, args)
        mon_status(distro.conn, rlogger, mon_host, args)
        distro.conn.exit()

    except RuntimeError as e:
        LOG.error(e)
        raise exc.GenericError('Failed to add monitor to host:  %s' % mon_host)


def mon_create(args):

    cfg = conf.ceph.load(args)
    if not args.mon:
        mon_initial_members = cfg.safe_get('global', 'mon_initial_members')
        args.mon = re.split(r'[,\s]+', mon_initial_members)

    if not args.mon:
        raise exc.NeedHostError()

    try:
        with file('{cluster}.mon.keyring'.format(cluster=args.cluster),
                  'rb') as f:
            monitor_keyring = f.read()
    except IOError:
        raise RuntimeError('mon keyring not found; run \'new\' to create a new cluster')

    LOG.debug(
        'Deploying mon, cluster %s hosts %s',
        args.cluster,
        ' '.join(args.mon),
        )

    errors = 0
    for (name, host) in mon_hosts(args.mon):
        try:
            # TODO add_bootstrap_peer_hint
            LOG.debug('detecting platform for host %s ...', name)
            distro = hosts.get(host, username=args.username)
            LOG.info('distro info: %s %s %s', distro.name, distro.release, distro.codename)
            rlogger = logging.getLogger(name)

            # ensure remote hostname is good to go
            hostname_is_compatible(distro.conn, rlogger, name)
            rlogger.debug('deploying mon to %s', name)
            distro.mon.create(distro, args, monitor_keyring)

            # tell me the status of the deployed mon
            time.sleep(2)  # give some room to start
            mon_status(distro.conn, rlogger, name, args)
            catch_mon_errors(distro.conn, rlogger, name, cfg, args)
            distro.conn.exit()

        except RuntimeError as e:
            LOG.error(e)
            errors += 1

    if errors:
        raise exc.GenericError('Failed to create %d monitors' % errors)


def hostname_is_compatible(conn, logger, provided_hostname):
    """
    Make sure that the host that we are connecting to has the same value as the
    `hostname` in the remote host, otherwise mons can fail not reaching quorum.
    """
    logger.debug('determining if provided host has same hostname in remote')
    remote_hostname = conn.remote_module.shortname()
    if remote_hostname == provided_hostname:
        return
    logger.warning('*'*80)
    logger.warning('provided hostname must match remote hostname')
    logger.warning('provided hostname: %s' % provided_hostname)
    logger.warning('remote hostname: %s' % remote_hostname)
    logger.warning('monitors may not reach quorum and create-keys will not complete')
    logger.warning('*'*80)


def destroy_mon(conn, cluster, hostname):
    import datetime
    import time
    retries = 5

    path = paths.mon.path(cluster, hostname)

    if conn.remote_module.path_exists(path):
        # remove from cluster
        process.run(
            conn,
            [
                'ceph',
                '--cluster={cluster}'.format(cluster=cluster),
                '-n', 'mon.',
                '-k', '{path}/keyring'.format(path=path),
                'mon',
                'remove',
                hostname,
            ],
            timeout=7,
        )

        # stop
        if conn.remote_module.path_exists(os.path.join(path, 'upstart')):
            status_args = [
                'initctl',
                'status',
                'ceph-mon',
                'cluster={cluster}'.format(cluster=cluster),
                'id={hostname}'.format(hostname=hostname),
            ]

        elif conn.remote_module.path_exists(os.path.join(path, 'sysvinit')):
            status_args = [
                'service',
                'ceph',
                'status',
                'mon.{hostname}'.format(hostname=hostname),
            ]

        while retries:
            conn.logger.info('polling the daemon to verify it stopped')
            if is_running(conn, status_args):
                time.sleep(5)
                retries -= 1
                if retries <= 0:
                    raise RuntimeError('ceph-mon deamon did not stop')
            else:
                break

        # archive old monitor directory
        fn = '{cluster}-{hostname}-{stamp}'.format(
            hostname=hostname,
            cluster=cluster,
            stamp=datetime.datetime.utcnow().strftime("%Y-%m-%dZ%H:%M:%S"),
            )

        process.run(
            conn,
            [
                'mkdir',
                '-p',
                '/var/lib/ceph/mon-removed',
            ],
        )

        conn.remote_module.make_mon_removed_dir(path, fn)


def mon_destroy(args):
    errors = 0
    for (name, host) in mon_hosts(args.mon):
        try:
            LOG.debug('Removing mon from %s', name)

            distro = hosts.get(host, username=args.username)
            hostname = distro.conn.remote_module.shortname()

            destroy_mon(
                distro.conn,
                args.cluster,
                hostname,
            )
            distro.conn.exit()

        except RuntimeError as e:
            LOG.error(e)
            errors += 1

    if errors:
        raise exc.GenericError('Failed to destroy %d monitors' % errors)


def mon_create_initial(args):
    cfg = conf.ceph.load(args)
    cfg_initial_members = cfg.safe_get('global', 'mon_initial_members')
    if cfg_initial_members is None:
        raise RuntimeError('No `mon initial members` defined in config')
    mon_initial_members = re.split(r'[,\s]+', cfg_initial_members)

    # create them normally through mon_create
    mon_create(args)

    # make the sets to be able to compare late
    mon_in_quorum = set([])
    mon_members = set([host for host in mon_initial_members])

    for host in mon_initial_members:
        mon_name = 'mon.%s' % host
        LOG.info('processing monitor %s', mon_name)
        sleeps = [20, 20, 15, 10, 10, 5]
        tries = 5
        rlogger = logging.getLogger(host)
        rconn = get_connection(host, username=args.username, logger=rlogger)
        while tries:
            status = mon_status_check(rconn, rlogger, host, args)
            has_reached_quorum = status.get('state', '') in ['peon', 'leader']
            if not has_reached_quorum:
                LOG.warning('%s monitor is not yet in quorum, tries left: %s' % (mon_name, tries))
                tries -= 1
                sleep_seconds = sleeps.pop()
                LOG.warning('waiting %s seconds before retrying', sleep_seconds)
                time.sleep(sleep_seconds)  # Magic number
            else:
                mon_in_quorum.add(host)
                LOG.info('%s monitor has reached quorum!', mon_name)
                break
        rconn.exit()

    if mon_in_quorum == mon_members:
        LOG.info('all initial monitors are running and have formed quorum')
        LOG.info('Running gatherkeys...')
        gatherkeys.gatherkeys(args)
    else:
        LOG.error('Some monitors have still not reached quorum:')
        for host in mon_members - mon_in_quorum:
            LOG.error('%s', host)
        raise SystemExit('cluster may not be in a healthy state')


def mon(args):
    if args.subcommand == 'create':
        mon_create(args)
    elif args.subcommand == 'add':
        mon_add(args)
    elif args.subcommand == 'destroy':
        mon_destroy(args)
    elif args.subcommand == 'create-initial':
        mon_create_initial(args)
    else:
        LOG.error('subcommand %s not implemented', args.subcommand)


@priority(30)
def make(parser):
    """
    Deploy ceph monitor on remote hosts.
    """
    sub_command_help = dedent("""
    Subcommands:

    create-initial
      Will deploy for monitors defined in `mon initial members`, wait until
      they form quorum and then gatherkeys, reporting the monitor status along
      the process. If monitors don't form quorum the command will eventually
      time out.

    create
      Deploy monitors by specifying them like:

        ceph-deploy mon create node1 node2 node3

      If no hosts are passed it will default to use the `mon initial members`
      defined in the configuration.

    add
      Add a monitor to an existing cluster:

        ceph-deploy mon add node1

      Or:

        ceph-deploy mon add node1 --address 192.168.1.10

      If the section for the monitor exists and defines a `mon addr` that
      will be used, otherwise it will fallback by resolving the hostname to an
      IP. If `--address` is used it will override all other options.

    destroy
      Completely remove monitors on a remote host. Requires hostname(s) as
      arguments.
    """)
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = sub_command_help

    parser.add_argument(
        'subcommand',
        choices=[
            'add',
            'create',
            'create-initial',
            'destroy',
            ],
        )

    parser.add_argument(
        '--address',
        nargs='?',
        dest='address',
    )

    parser.add_argument(
        'mon',
        nargs='*',
    )

    parser.set_defaults(
        func=mon,
    )

#
# Helpers
#


def is_running(conn, args):
    """
    Run a command to check the status of a mon, return a boolean.

    We heavily depend on the format of the output, if that ever changes
    we need to modify this.
    Check daemon status for 3 times
    output of the status should be similar to::

        mon.mira094: running {"version":"0.61.5"}

    or when it fails::

        mon.mira094: dead {"version":"0.61.5"}
        mon.mira094: not running {"version":"0.61.5"}
    """
    stdout, stderr, _ = process.check(
        conn,
        args
    )
    result_string = ' '.join(stdout)
    for run_check in [': running', ' start/running']:
        if run_check in result_string:
            return True
    return False

########NEW FILE########
__FILENAME__ = new
import errno
import logging
import os
import uuid
import struct
import time
import base64
import socket

from ceph_deploy.cliutil import priority
from ceph_deploy import conf, hosts, exc
from ceph_deploy.util import arg_validators, ssh, net
from ceph_deploy.misc import mon_hosts
from ceph_deploy.lib.remoto import process
from ceph_deploy.connection import get_local_connection


LOG = logging.getLogger(__name__)


def generate_auth_key():
    key = os.urandom(16)
    header = struct.pack(
        '<hiih',
        1,                 # le16 type: CEPH_CRYPTO_AES
        int(time.time()),  # le32 created: seconds
        0,                 # le32 created: nanoseconds,
        len(key),          # le16: len(key)
    )
    return base64.b64encode(header + key)


def ssh_copy_keys(hostname, username=None):
    LOG.info('making sure passwordless SSH succeeds')
    if ssh.can_connect_passwordless(hostname):
        return

    LOG.warning('could not connect via SSH')

    # Create the key if it doesn't exist:
    id_rsa_pub_file = os.path.expanduser(u'~/.ssh/id_rsa.pub')
    id_rsa_file = id_rsa_pub_file.split('.pub')[0]
    if not os.path.exists(id_rsa_file):
        LOG.info('creating a passwordless id_rsa.pub key file')
        with get_local_connection(LOG) as conn:
            process.run(
                conn,
                [
                    'ssh-keygen',
                    '-t',
                    'rsa',
                    '-N',
                    "",
                    '-f',
                    id_rsa_file,
                ]
            )

    # Get the contents of id_rsa.pub and push it to the host
    LOG.info('will connect again with password prompt')
    distro = hosts.get(hostname, username)  # XXX Add username
    auth_keys_path = '.ssh/authorized_keys'
    if not distro.conn.remote_module.path_exists(auth_keys_path):
        distro.conn.logger.warning(
            '.ssh/authorized_keys does not exist, will skip adding keys'
        )
    else:
        LOG.info('adding public keys to authorized_keys')
        with open(os.path.expanduser('~/.ssh/id_rsa.pub'), 'r') as id_rsa:
            contents = id_rsa.read()
        distro.conn.remote_module.append_to_file(
            auth_keys_path,
            contents
        )
    distro.conn.exit()


def new(args):
    LOG.debug('Creating new cluster named %s', args.cluster)
    cfg = conf.ceph.CephConf()
    cfg.add_section('global')

    fsid = uuid.uuid4()
    cfg.set('global', 'fsid', str(fsid))

    mon_initial_members = []
    mon_host = []

    for (name, host) in mon_hosts(args.mon):
        LOG.debug('Resolving host %s', host)
        ip = net.get_nonlocal_ip(host)
        LOG.debug('Monitor %s at %s', name, ip)
        mon_initial_members.append(name)
        try:
            socket.inet_pton(socket.AF_INET6, ip)
            mon_host.append("[" + ip + "]")
            LOG.info('Monitors are IPv6, binding Messenger traffic on IPv6')
            cfg.set('global', 'ms bind ipv6', 'true')
        except socket.error:
            mon_host.append(ip)

        if args.ssh_copykey:
            ssh_copy_keys(host, args.username)

    LOG.debug('Monitor initial members are %s', mon_initial_members)
    LOG.debug('Monitor addrs are %s', mon_host)

    cfg.set('global', 'mon initial members', ', '.join(mon_initial_members))
    # no spaces here, see http://tracker.newdream.net/issues/3145
    cfg.set('global', 'mon host', ','.join(mon_host))

    # override undesirable defaults, needed until bobtail

    # http://tracker.ceph.com/issues/6788
    cfg.set('global', 'auth cluster required', 'cephx')
    cfg.set('global', 'auth service required', 'cephx')
    cfg.set('global', 'auth client required', 'cephx')

    # http://tracker.newdream.net/issues/3138
    cfg.set('global', 'filestore xattr use omap', 'true')

    path = '{name}.conf'.format(
        name=args.cluster,
        )

    # FIXME: create a random key
    LOG.debug('Creating a random mon key...')
    mon_keyring = '[mon.]\nkey = %s\ncaps mon = allow *\n' % generate_auth_key()

    keypath = '{name}.mon.keyring'.format(
        name=args.cluster,
        )

    LOG.debug('Writing initial config to %s...', path)
    tmp = '%s.tmp' % path
    with file(tmp, 'w') as f:
        cfg.write(f)
    try:
        os.rename(tmp, path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            raise exc.ClusterExistsError(path)
        else:
            raise

    LOG.debug('Writing monitor keyring to %s...', keypath)
    tmp = '%s.tmp' % keypath
    with file(tmp, 'w') as f:
        f.write(mon_keyring)
    try:
        os.rename(tmp, keypath)
    except OSError as e:
        if e.errno == errno.EEXIST:
            raise exc.ClusterExistsError(keypath)
        else:
            raise


@priority(10)
def make(parser):
    """
    Start deploying a new cluster, and write a CLUSTER.conf and keyring for it.
    """
    parser.add_argument(
        'mon',
        metavar='MON',
        nargs='+',
        help='initial monitor hostname, fqdn, or hostname:fqdn pair',
        type=arg_validators.Hostname(),
        )
    parser.add_argument(
        '--no-ssh-copykey',
        dest='ssh_copykey',
        action='store_false',
        default=True,
        help='do not attempt to copy SSH keys',
    )

    parser.set_defaults(
        func=new,
        )

########NEW FILE########
__FILENAME__ = osd
import argparse
import json
import logging
import os
import re
import sys
import time
from textwrap import dedent

from cStringIO import StringIO

from ceph_deploy import conf, exc, hosts
from ceph_deploy.util import constants
from ceph_deploy.cliutil import priority
from ceph_deploy.lib.remoto import process


LOG = logging.getLogger(__name__)


def get_bootstrap_osd_key(cluster):
    """
    Read the bootstrap-osd key for `cluster`.
    """
    path = '{cluster}.bootstrap-osd.keyring'.format(cluster=cluster)
    try:
        with file(path, 'rb') as f:
            return f.read()
    except IOError:
        raise RuntimeError('bootstrap-osd keyring not found; run \'gatherkeys\'')


def create_osd(conn, cluster, key):
    """
    Run on osd node, writes the bootstrap key if not there yet.
    """
    logger = conn.logger
    path = '/var/lib/ceph/bootstrap-osd/{cluster}.keyring'.format(
        cluster=cluster,
        )
    if not conn.remote_module.path_exists(path):
        logger.warning('osd keyring does not exist yet, creating one')
        conn.remote_module.write_keyring(path, key)

    return process.run(
        conn,
        [
            'udevadm',
            'trigger',
            '--subsystem-match=block',
            '--action=add',
        ],
    )


def osd_tree(conn, cluster):
    """
    Check the status of an OSD. Make sure all are up and in

    What good output would look like::

        {
            "epoch": 8,
            "num_osds": 1,
            "num_up_osds": 1,
            "num_in_osds": "1",
            "full": "false",
            "nearfull": "false"
        }

    Note how the booleans are actually strings, so we need to take that into
    account and fix it before returning the dictionary. Issue #8108
    """
    command = [
        'ceph',
        '--cluster={cluster}'.format(cluster=cluster),
        'osd',
        'tree',
        '--format=json',
    ]

    out, err, code = process.check(
        conn,
        command,
    )

    try:
        loaded_json = json.loads(''.join(out))
        # convert boolean strings to actual booleans because
        # --format=json fails to do this properly
        for k, v in loaded_json.items():
            if v == 'true':
                loaded_json[k] = True
            elif v == 'false':
                loaded_json[k] = False
        return loaded_json
    except ValueError:
        return {}


def osd_status_check(conn, cluster):
    """
    Check the status of an OSD. Make sure all are up and in

    What good output would look like::

        {
            "epoch": 8,
            "num_osds": 1,
            "num_up_osds": 1,
            "num_in_osds": "1",
            "full": "false",
            "nearfull": "false"
        }

    Note how the booleans are actually strings, so we need to take that into
    account and fix it before returning the dictionary. Issue #8108
    """
    command = [
        'ceph',
        '--cluster={cluster}'.format(cluster=cluster),
        'osd',
        'stat',
        '--format=json',
    ]

    try:
        out, err, code = process.check(
            conn,
            command,
        )
    except TypeError:
        # XXX This is a bug in remoto. If the other end disconnects with a timeout
        # it will return a None, and here we are expecting a 3 item tuple, not a None
        # so it will break with a TypeError. Once remoto fixes this, we no longer need
        # this try/except.
        return {}

    try:
        loaded_json = json.loads(''.join(out))
        # convert boolean strings to actual booleans because
        # --format=json fails to do this properly
        for k, v in loaded_json.items():
            if v == 'true':
                loaded_json[k] = True
            elif v == 'false':
                loaded_json[k] = False
        return loaded_json
    except ValueError:
        return {}


def catch_osd_errors(conn, logger, args):
    """
    Look for possible issues when checking the status of an OSD and
    report them back to the user.
    """
    logger.info('checking OSD status...')
    status = osd_status_check(conn, args.cluster)
    osds = int(status.get('num_osds', 0))
    up_osds = int(status.get('num_up_osds', 0))
    in_osds = int(status.get('num_in_osds', 0))
    full = status.get('full', False)
    nearfull = status.get('nearfull', False)

    if osds > up_osds:
        difference = osds - up_osds
        logger.warning('there %s %d OSD%s down' % (
            ['is', 'are'][difference != 1],
            difference,
            "s"[difference == 1:])
        )

    if osds > in_osds:
        difference = osds - in_osds
        logger.warning('there %s %d OSD%s out' % (
            ['is', 'are'][difference != 1],
            difference,
            "s"[difference == 1:])
        )

    if full:
        logger.warning('OSDs are full!')

    if nearfull:
        logger.warning('OSDs are near full!')


def prepare_disk(
        conn,
        cluster,
        disk,
        journal,
        activate_prepared_disk,
        zap,
        fs_type,
        dmcrypt,
        dmcrypt_dir):
    """
    Run on osd node, prepares a data disk for use.
    """
    args = [
        'ceph-disk-prepare',
        ]
    if zap:
        args.append('--zap-disk')
    if fs_type:
        if fs_type not in ('btrfs', 'ext4', 'xfs'):
            raise argparse.ArgumentTypeError(
                "FS_TYPE must be one of 'btrfs', 'ext4' or 'xfs'")
        args.extend(['--fs-type', fs_type])
    if dmcrypt:
        args.append('--dmcrypt')
        if dmcrypt_dir is not None:
            args.append('--dmcrypt-key-dir')
            args.append(dmcrypt_dir)
    args.extend([
        '--cluster',
        cluster,
        '--',
        disk,
    ])

    if journal is not None:
        args.append(journal)

    process.run(
        conn,
        args
    )

    if activate_prepared_disk:
        return process.run(
            conn,
            [
                'udevadm',
                'trigger',
                '--subsystem-match=block',
                '--action=add',
            ],
        )


def prepare(args, cfg, activate_prepared_disk):
    LOG.debug(
        'Preparing cluster %s disks %s',
        args.cluster,
        ' '.join(':'.join(x or '' for x in t) for t in args.disk),
        )

    key = get_bootstrap_osd_key(cluster=args.cluster)

    bootstrapped = set()
    errors = 0
    for hostname, disk, journal in args.disk:
        try:
            if disk is None:
                raise exc.NeedDiskError(hostname)

            distro = hosts.get(hostname, username=args.username)
            LOG.info(
                'Distro info: %s %s %s',
                distro.name,
                distro.release,
                distro.codename
            )

            if hostname not in bootstrapped:
                bootstrapped.add(hostname)
                LOG.debug('Deploying osd to %s', hostname)

                conf_data = StringIO()
                cfg.write(conf_data)
                distro.conn.remote_module.write_conf(
                    args.cluster,
                    conf_data.getvalue(),
                    args.overwrite_conf
                )

                create_osd(distro.conn, args.cluster, key)

            LOG.debug('Preparing host %s disk %s journal %s activate %s',
                      hostname, disk, journal, activate_prepared_disk)

            prepare_disk(
                distro.conn,
                cluster=args.cluster,
                disk=disk,
                journal=journal,
                activate_prepared_disk=activate_prepared_disk,
                zap=args.zap_disk,
                fs_type=args.fs_type,
                dmcrypt=args.dmcrypt,
                dmcrypt_dir=args.dmcrypt_key_dir,
            )

            # give the OSD a few seconds to start
            time.sleep(5)
            catch_osd_errors(distro.conn, distro.conn.logger, args)
            LOG.debug('Host %s is now ready for osd use.', hostname)
            distro.conn.exit()

        except RuntimeError as e:
            LOG.error(e)
            errors += 1

    if errors:
        raise exc.GenericError('Failed to create %d OSDs' % errors)


def activate(args, cfg):
    LOG.debug(
        'Activating cluster %s disks %s',
        args.cluster,
        # join elements of t with ':', t's with ' '
        # allow None in elements of t; print as empty
        ' '.join(':'.join((s or '') for s in t) for t in args.disk),
        )

    for hostname, disk, journal in args.disk:

        distro = hosts.get(hostname, username=args.username)
        LOG.info(
            'Distro info: %s %s %s',
            distro.name,
            distro.release,
            distro.codename
        )

        LOG.debug('activating host %s disk %s', hostname, disk)
        LOG.debug('will use init type: %s', distro.init)

        process.run(
            distro.conn,
            [
                'ceph-disk-activate',
                '--mark-init',
                distro.init,
                '--mount',
                disk,
            ],
        )
        # give the OSD a few seconds to start
        time.sleep(5)
        catch_osd_errors(distro.conn, distro.conn.logger, args)
        distro.conn.exit()


def disk_zap(args):
    cfg = conf.ceph.load(args)

    for hostname, disk, journal in args.disk:
        if not disk or not hostname:
            raise RuntimeError('zap command needs both HOSTNAME and DISK but got "%s %s"' % (hostname, disk))
        LOG.debug('zapping %s on %s', disk, hostname)
        distro = hosts.get(hostname, username=args.username)
        LOG.info(
            'Distro info: %s %s %s',
            distro.name,
            distro.release,
            distro.codename
        )

        # NOTE: this mirrors ceph-disk-prepare --zap-disk DEV
        # zero the device
        distro.conn.remote_module.zeroing(disk)

        process.run(
            distro.conn,
            [
                'sgdisk',
                '--zap-all',
                '--clear',
                '--mbrtogpt',
                '--',
                disk,
            ],
        )
        distro.conn.exit()


def disk_list(args, cfg):
    for hostname, disk, journal in args.disk:
        distro = hosts.get(hostname, username=args.username)
        LOG.info(
            'Distro info: %s %s %s',
            distro.name,
            distro.release,
            distro.codename
        )

        LOG.debug('Listing disks on {hostname}...'.format(hostname=hostname))
        process.run(
            distro.conn,
            [
                'ceph-disk',
                'list',
            ],
        )
        distro.conn.exit()


def osd_list(args, cfg):
    # FIXME: this portion should probably be abstracted. We do the same in
    # mon.py
    cfg = conf.ceph.load(args)
    mon_initial_members = cfg.safe_get('global', 'mon_initial_members')
    monitors = re.split(r'[,\s]+', mon_initial_members)

    if not monitors:
        raise exc.NeedHostError(
            'could not find `mon initial members` defined in ceph.conf'
        )

    # get the osd tree from a monitor host
    mon_host = monitors[0]
    distro = hosts.get(mon_host, username=args.username)
    tree = osd_tree(distro.conn, args.cluster)
    distro.conn.exit()

    interesting_files = ['active', 'magic', 'whoami', 'journal_uuid']

    for hostname, disk, journal in args.disk:
        distro = hosts.get(hostname, username=args.username)
        remote_module = distro.conn.remote_module
        osds = distro.conn.remote_module.listdir(constants.osd_path)

        output, err, exit_code = process.check(
            distro.conn,
            [
                'ceph-disk',
                'list',
            ]
        )

        for _osd in osds:
            osd_path = os.path.join(constants.osd_path, _osd)
            journal_path = os.path.join(osd_path, 'journal')
            _id = int(_osd.split('-')[-1])  # split on dash, get the id
            osd_name = 'osd.%s' % _id
            metadata = {}
            json_blob = {}

            # piggy back from ceph-disk and get the mount point
            device = get_osd_mount_point(output, osd_name)
            if device:
                metadata['device'] = device

            # read interesting metadata from files
            for f in interesting_files:
                osd_f_path = os.path.join(osd_path, f)
                if remote_module.path_exists(osd_f_path):
                    metadata[f] = remote_module.readline(osd_f_path)

            # do we have a journal path?
            if remote_module.path_exists(journal_path):
                metadata['journal path'] = remote_module.get_realpath(journal_path)

            # is this OSD in osd tree?
            for blob in tree['nodes']:
                if blob.get('id') == _id:  # matches our OSD
                    json_blob = blob

            print_osd(
                distro.conn.logger,
                hostname,
                osd_path,
                json_blob,
                metadata,
            )

        distro.conn.exit()


def get_osd_mount_point(output, osd_name):
    """
    piggy back from `ceph-disk list` output and get the mount point
    by matching the line where the partition mentions the OSD name

    For example, if the name of the osd is `osd.1` and the output from
    `ceph-disk list` looks like this::

        /dev/sda :
         /dev/sda1 other, ext2, mounted on /boot
         /dev/sda2 other
         /dev/sda5 other, LVM2_member
        /dev/sdb :
         /dev/sdb1 ceph data, active, cluster ceph, osd.1, journal /dev/sdb2
         /dev/sdb2 ceph journal, for /dev/sdb1
        /dev/sr0 other, unknown
        /dev/sr1 other, unknown

    Then `/dev/sdb1` would be the right mount point. We piggy back like this
    because ceph-disk does *a lot* to properly calculate those values and we
    don't want to re-implement all the helpers for this.

    :param output: A list of lines from stdout
    :param osd_name: The actual osd name, like `osd.1`
    """
    for line in output:
        line_parts = re.split(r'[,\s]+', line)
        for part in line_parts:
            mount_point = line_parts[1]
            if osd_name == part:
                return mount_point


def print_osd(logger, hostname, osd_path, json_blob, metadata, journal=None):
    """
    A helper to print OSD metadata
    """
    logger.info('-'*40)
    logger.info('%s' % osd_path.split('/')[-1])
    logger.info('-'*40)
    logger.info('%-14s %s' % ('Path', osd_path))
    logger.info('%-14s %s' % ('ID', json_blob.get('id')))
    logger.info('%-14s %s' % ('Name', json_blob.get('name')))
    logger.info('%-14s %s' % ('Status', json_blob.get('status')))
    logger.info('%-14s %s' % ('Reweight', json_blob.get('reweight')))
    if journal:
        logger.info('Journal: %s' % journal)
    for k, v in metadata.items():
        #logger.info("%s: %-8s" % (k.capitalize(), v))
        logger.info("%-13s  %s" % (k.capitalize(), v))

    logger.info('-'*40)


def osd(args):
    cfg = conf.ceph.load(args)

    if args.subcommand == 'list':
        osd_list(args, cfg)
    elif args.subcommand == 'prepare':
        prepare(args, cfg, activate_prepared_disk=False)
    elif args.subcommand == 'create':
        prepare(args, cfg, activate_prepared_disk=True)
    elif args.subcommand == 'activate':
        activate(args, cfg)
    else:
        LOG.error('subcommand %s not implemented', args.subcommand)
        sys.exit(1)


def disk(args):
    cfg = conf.ceph.load(args)

    if args.subcommand == 'list':
        disk_list(args, cfg)
    elif args.subcommand == 'prepare':
        prepare(args, cfg, activate_prepared_disk=False)
    elif args.subcommand == 'activate':
        activate(args, cfg)
    elif args.subcommand == 'zap':
        disk_zap(args)
    else:
        LOG.error('subcommand %s not implemented', args.subcommand)
        sys.exit(1)


def colon_separated(s):
    journal = None
    disk = None
    host = None
    if s.count(':') == 2:
        (host, disk, journal) = s.split(':')
    elif s.count(':') == 1:
        (host, disk) = s.split(':')
    elif s.count(':') == 0:
        (host) = s
    else:
        raise argparse.ArgumentTypeError('must be in form HOST:DISK[:JOURNAL]')

    if disk:
        # allow just "sdb" to mean /dev/sdb
        disk = os.path.join('/dev', disk)
        if journal is not None:
            journal = os.path.join('/dev', journal)

    return (host, disk, journal)


@priority(50)
def make(parser):
    """
    Prepare a data disk on remote host.
    """
    sub_command_help = dedent("""
    Manage OSDs by preparing a data disk on remote host.

    For paths, first prepare and then activate:

        ceph-deploy osd prepare {osd-node-name}:/path/to/osd
        ceph-deploy osd activate {osd-node-name}:/path/to/osd

    For disks or journals the `create` command will do prepare and activate
    for you.
    """
    )
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = sub_command_help

    parser.add_argument(
        'subcommand',
        metavar='SUBCOMMAND',
        choices=[
            'list',
            'create',
            'prepare',
            'activate',
            'destroy',
            ],
        help='list, create (prepare+activate), prepare, activate, or destroy',
        )
    parser.add_argument(
        'disk',
        nargs='+',
        metavar='HOST:DISK[:JOURNAL]',
        type=colon_separated,
        help='host and disk to prepare',
        )
    parser.add_argument(
        '--zap-disk',
        action='store_true', default=None,
        help='destroy existing partition table and content for DISK',
        )
    parser.add_argument(
        '--fs-type',
        metavar='FS_TYPE',
        default='xfs',
        help='filesystem to use to format DISK (xfs, btrfs or ext4)',
        )
    parser.add_argument(
        '--dmcrypt',
        action='store_true', default=None,
        help='use dm-crypt on DISK',
        )
    parser.add_argument(
        '--dmcrypt-key-dir',
        metavar='KEYDIR',
        default='/etc/ceph/dmcrypt-keys',
        help='directory where dm-crypt keys are stored',
        )
    parser.set_defaults(
        func=osd,
        )


@priority(50)
def make_disk(parser):
    """
    Manage disks on a remote host.
    """
    parser.add_argument(
        'subcommand',
        metavar='SUBCOMMAND',
        choices=[
            'list',
            'prepare',
            'activate',
            'zap',
            ],
        help='list, prepare, activate, zap',
        )
    parser.add_argument(
        'disk',
        nargs='+',
        metavar='HOST:DISK',
        type=colon_separated,
        help='host and disk (or path)',
        )
    parser.add_argument(
        '--zap-disk',
        action='store_true', default=None,
        help='destroy existing partition table and content for DISK',
        )
    parser.add_argument(
        '--fs-type',
        metavar='FS_TYPE',
        default='xfs',
        help='filesystem to use to format DISK (xfs, btrfs or ext4)'
        )
    parser.add_argument(
        '--dmcrypt',
        action='store_true', default=None,
        help='use dm-crypt on DISK',
        )
    parser.add_argument(
        '--dmcrypt-key-dir',
        metavar='KEYDIR',
        default='/etc/ceph/dmcrypt-keys',
        help='directory where dm-crypt keys are stored',
        )
    parser.set_defaults(
        func=disk,
        )

########NEW FILE########
__FILENAME__ = pkg
import logging
from . import hosts


LOG = logging.getLogger(__name__)


def install(args):
    packages = args.install.split(',')
    for hostname in args.hosts:
        distro = hosts.get(hostname, username=args.username)
        LOG.info(
            'Distro info: %s %s %s',
            distro.name,
            distro.release,
            distro.codename
        )
        rlogger = logging.getLogger(hostname)
        rlogger.info('installing packages on %s' % hostname)
        distro.pkg.install(distro, packages)
        distro.conn.exit()


def remove(args):
    packages = args.remove.split(',')
    for hostname in args.hosts:
        distro = hosts.get(hostname, username=args.username)
        LOG.info(
            'Distro info: %s %s %s',
            distro.name,
            distro.release,
            distro.codename
        )

        rlogger = logging.getLogger(hostname)
        rlogger.info('removing packages from %s' % hostname)
        distro.pkg.remove(distro, packages)
        distro.conn.exit()


def pkg(args):
    if args.install:
        install(args)
    elif args.remove:
        remove(args)


def make(parser):
    """
    Manage packages on remote hosts.
    """

    parser.add_argument(
        '--install',
        nargs='?',
        metavar='PKG(s)',
        help='Comma-separated package(s) to install',
    )

    parser.add_argument(
        '--remove',
        nargs='?',
        metavar='PKG(s)',
        help='Comma-separated package(s) to remove',
    )

    parser.add_argument(
        'hosts',
        nargs='+',
    )

    parser.set_defaults(
        func=pkg,
    )

########NEW FILE########
__FILENAME__ = conftest
import logging
import os
import subprocess
import sys


LOG = logging.getLogger(__name__)


def _prepend_path(env):
    """
    Make sure the PATH contains the location where the Python binary
    lives. This makes sure cli tools installed in a virtualenv work.
    """
    if env is None:
        env = os.environ
    env = dict(env)
    new = os.path.dirname(sys.executable)
    path = env.get('PATH')
    if path is not None:
        new = new + ':' + path
    env['PATH'] = new
    return env


class CLIFailed(Exception):
    """CLI tool failed"""

    def __init__(self, args, status):
        self.args = args
        self.status = status

    def __str__(self):
        return '{doc}: {args}: exited with status {status}'.format(
            doc=self.__doc__,
            args=self.args,
            status=self.status,
            )


class CLIProcess(object):
    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        try:
            self.p = subprocess.Popen(**self.kw)
        except OSError as e:
            raise AssertionError(
                'CLI tool {args!r} does not work: {err}'.format(
                    args=self.kw['args'],
                    err=e,
                    ),
                )
        else:
            return self.p

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.p.wait()
        if self.p.returncode != 0:
            err = CLIFailed(
                args=self.kw['args'],
                status=self.p.returncode,
                )
            if exc_type is None:
                # nothing else raised, so we should complain; if
                # something else failed, we'll just log
                raise err
            else:
                LOG.error(str(err))


class CLITester(object):
    # provide easy way for caller to access the exception class
    # without importing us
    Failed = CLIFailed

    def __init__(self, tmpdir):
        self.tmpdir = tmpdir

    def __call__(self, **kw):
        kw.setdefault('cwd', str(self.tmpdir))
        kw['env'] = _prepend_path(kw.get('env'))
        kw['env']['COLUMNS'] = '80'
        return CLIProcess(**kw)


def pytest_funcarg__cli(request):
    """
    Test command line behavior.
    """

    # the tmpdir here will be the same value as the test function
    # sees; we rely on that to let caller prepare and introspect
    # any files the cli tool will read or create
    tmpdir = request.getfuncargvalue('tmpdir')

    return CLITester(tmpdir=tmpdir)

########NEW FILE########
__FILENAME__ = directory
import contextlib
import os


@contextlib.contextmanager
def directory(path):
    prev = os.open('.', os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.chdir(path)
        yield
    finally:
        os.fchdir(prev)
        os.close(prev)

########NEW FILE########
__FILENAME__ = fakes
from mock import MagicMock


def fake_getaddrinfo(*a, **kw):
    return_host = kw.get('return_host', 'host1')
    return [[0,0,0,0, return_host]]


def mock_open(mock=None, data=None):
    """
    Fake the behavior of `open` when used as a context manager
    """
    if mock is None:
        mock = MagicMock(spec=file)

    handle = MagicMock(spec=file)
    handle.write.return_value = None
    if data is None:
        handle.__enter__.return_value = handle
    else:
        handle.__enter__.return_value = data
    mock.return_value = handle
    return mock




########NEW FILE########
__FILENAME__ = test_cli
import pytest
import subprocess


def test_help(tmpdir, cli):
    with cli(
        args=['ceph-deploy', '--help'],
        stdout=subprocess.PIPE,
        ) as p:
        result = p.stdout.read()
        assert 'usage: ceph-deploy' in result
        assert 'optional arguments:' in result
        assert 'commands:' in result


def test_bad_command(tmpdir, cli):
    with pytest.raises(cli.Failed) as err:
        with cli(
            args=['ceph-deploy', 'bork'],
            stderr=subprocess.PIPE,
            ) as p:
            result = p.stderr.read()
    assert 'usage: ceph-deploy' in result
    assert err.value.status == 2
    assert [p.basename for p in tmpdir.listdir()] == []


def test_bad_cluster(tmpdir, cli):
    with pytest.raises(cli.Failed) as err:
        with cli(
            args=['ceph-deploy', '--cluster=/evil-this-should-not-be-created', 'new'],
            stderr=subprocess.PIPE,
            ) as p:
            result = p.stderr.read()
    assert 'usage: ceph-deploy' in result
    assert err.value.status == 2
    assert [p.basename for p in tmpdir.listdir()] == []

########NEW FILE########
__FILENAME__ = test_cli_install
import argparse
import collections
import mock
import pytest
import subprocess

from ..cli import main
from .. import install

from .directory import directory


def test_help(tmpdir, cli):
    with cli(
        args=['ceph-deploy', 'install', '--help'],
        stdout=subprocess.PIPE,
        ) as p:
        result = p.stdout.read()
    assert 'usage: ceph-deploy' in result
    assert 'positional arguments:' in result
    assert 'optional arguments:' in result


def test_bad_no_host(tmpdir, cli):
    with pytest.raises(cli.Failed) as err:
        with cli(
            args=['ceph-deploy', 'install'],
            stderr=subprocess.PIPE,
            ) as p:
            result = p.stderr.read()
    assert 'usage: ceph-deploy install' in result
    assert 'too few arguments' in result
    assert err.value.status == 2

########NEW FILE########
__FILENAME__ = test_cli_mon
import argparse
import collections
import mock
import pytest
import subprocess

from ..cli import main
from .. import mon

from .directory import directory
from .fakes import fake_getaddrinfo

def test_help(tmpdir, cli):
    with cli(
        args=['ceph-deploy', 'mon', '--help'],
        stdout=subprocess.PIPE,
        ) as p:
        result = p.stdout.read()
    assert 'usage: ceph-deploy' in result
    assert 'positional arguments:' in result
    assert 'optional arguments:' in result


def test_bad_no_conf(tmpdir, cli):
    with pytest.raises(cli.Failed) as err:
        with cli(
            args=['ceph-deploy', 'mon'],
            stderr=subprocess.PIPE,
            ) as p:
            result = p.stderr.read()
    assert 'usage: ceph-deploy' in result
    assert 'too few arguments' in result
    assert err.value.status == 2


def test_bad_no_mon(tmpdir, cli):
    with tmpdir.join('ceph.conf').open('w'):
        pass
    with pytest.raises(cli.Failed) as err:
        with cli(
            args=['ceph-deploy', 'mon'],
            stderr=subprocess.PIPE,
            ) as p:
            result = p.stderr.read()
    assert 'usage: ceph-deploy mon' in result
    assert 'too few arguments' in result
    assert err.value.status == 2


def test_simple(tmpdir, capsys):
    with tmpdir.join('ceph.conf').open('w') as f:
        f.write("""\
[global]
fsid = 6ede5564-3cf1-44b5-aa96-1c77b0c3e1d0
mon initial members = host1
""")

    ns = argparse.Namespace()
    ns.pushy = mock.Mock()
    conn = mock.NonCallableMock(name='PushyClient')
    ns.pushy.return_value = conn

    mock_compiled = collections.defaultdict(mock.Mock)
    conn.compile.side_effect = mock_compiled.__getitem__

    MON_SECRET = 'AQBWDj5QAP6LHhAAskVBnUkYHJ7eYREmKo5qKA=='

    def _create_mon(cluster, get_monitor_secret):
        secret = get_monitor_secret()
        assert secret == MON_SECRET

    try:
        with mock.patch('ceph_deploy.new.net.get_nonlocal_ip', lambda x: '10.0.0.1'):
            with mock.patch('ceph_deploy.new.arg_validators.Hostname', lambda: lambda x: x):
                with directory(str(tmpdir)):
                    main(
                        args=['-v', 'new', 'host1'],
                        namespace=ns,
                        )
                    main(
                        args=['-v', 'mon', 'create', 'host1'],
                        namespace=ns,
                        )
    except SystemExit as e:
        raise AssertionError('Unexpected exit: %s', e)
    out, err = capsys.readouterr()
    err = err.lower()
    assert 'creating new cluster named ceph' in err
    assert 'monitor host1 at 10.0.0.1' in err
    assert 'resolving host host1' in err
    assert "monitor initial members are ['host1']" in err
    assert "monitor addrs are ['10.0.0.1']" in err

########NEW FILE########
__FILENAME__ = test_cli_new
from mock import patch
import re
import subprocess
import uuid

from .. import conf
from ..cli import main
from .directory import directory
from .fakes import fake_getaddrinfo


def test_help(tmpdir, cli):
    with cli(
        args=['ceph-deploy', 'new', '--help'],
        stdout=subprocess.PIPE,
        ) as p:
        result = p.stdout.read()
    assert 'usage: ceph-deploy new' in result
    assert 'positional arguments' in result
    assert 'optional arguments' in result


def test_write_global_conf_section(tmpdir, cli):
    with patch('ceph_deploy.new.net.get_nonlocal_ip', lambda x: '10.0.0.1'):
        with patch('ceph_deploy.new.arg_validators.Hostname', lambda: lambda x: x):
            with directory(str(tmpdir)):
                main(args=['new', 'host1'])
    with tmpdir.join('ceph.conf').open() as f:
        cfg = conf.ceph.parse(f)
    assert cfg.sections() == ['global']


def pytest_funcarg__newcfg(request):
    tmpdir = request.getfuncargvalue('tmpdir')
    cli = request.getfuncargvalue('cli')

    def new(*args):
        with patch('ceph_deploy.new.net.get_nonlocal_ip', lambda x: '10.0.0.1'):
            with patch('ceph_deploy.new.arg_validators.Hostname', lambda: lambda x: x):
                with directory(str(tmpdir)):
                    main( args=['new'] + list(args))
                    with tmpdir.join('ceph.conf').open() as f:
                        cfg = conf.ceph.parse(f)
                    return cfg
    return new


def test_uuid(newcfg):
    cfg = newcfg('host1')
    fsid = cfg.get('global', 'fsid')
    # make sure it's a valid uuid
    uuid.UUID(hex=fsid)
    # make sure it looks pretty, too
    UUID_RE = re.compile(
        r'^[0-9a-f]{8}-'
        + r'[0-9a-f]{4}-'
        # constant 4 here, we want to enforce randomness and not leak
        # MACs or time
        + r'4[0-9a-f]{3}-'
        + r'[0-9a-f]{4}-'
        + r'[0-9a-f]{12}$',
        )
    assert UUID_RE.match(fsid)


def test_mons(newcfg):
    cfg = newcfg('node01', 'node07', 'node34')
    mon_initial_members = cfg.get('global', 'mon_initial_members')
    assert mon_initial_members == 'node01, node07, node34'


def test_defaults(newcfg):
    cfg = newcfg('host1')
    assert cfg.get('global', 'auth cluster required') == 'cephx'
    assert cfg.get('global', 'auth service required') == 'cephx'
    assert cfg.get('global', 'auth client required') == 'cephx'
    assert cfg.get('global', 'filestore_xattr_use_omap') == 'true'

########NEW FILE########
__FILENAME__ = test_cli_osd
import argparse
import collections
import mock
import pytest
import subprocess

from ..cli import main
from .. import osd

from .directory import directory


def test_help(tmpdir, cli):
    with cli(
        args=['ceph-deploy', 'osd', '--help'],
        stdout=subprocess.PIPE,
        ) as p:
        result = p.stdout.read()
    assert 'usage: ceph-deploy osd' in result
    assert 'positional arguments' in result
    assert 'optional arguments' in result


def test_bad_no_conf(tmpdir, cli):
    with pytest.raises(cli.Failed) as err:
        with cli(
            args=['ceph-deploy', 'osd', 'fakehost:/does-not-exist'],
            stderr=subprocess.PIPE,
            ) as p:
            result = p.stderr.read()
    assert 'ceph-deploy osd: error' in result
    assert 'invalid choice' in result
    assert err.value.status == 2


def test_bad_no_disk(tmpdir, cli):
    with tmpdir.join('ceph.conf').open('w'):
        pass
    with pytest.raises(cli.Failed) as err:
        with cli(
            args=['ceph-deploy', 'osd'],
            stderr=subprocess.PIPE,
            ) as p:
            result = p.stderr.read()
    assert 'usage: ceph-deploy osd' in result
    assert err.value.status == 2

########NEW FILE########
__FILENAME__ = test_conf
from cStringIO import StringIO
from ceph_deploy import conf


def test_simple():
    f = StringIO("""\
[foo]
bar = baz
""")
    cfg = conf.ceph.parse(f)
    assert cfg.get('foo', 'bar') == 'baz'


def test_indent_space():
    f = StringIO("""\
[foo]
        bar = baz
""")
    cfg = conf.ceph.parse(f)
    assert cfg.get('foo', 'bar') == 'baz'


def test_indent_tab():
    f = StringIO("""\
[foo]
\tbar = baz
""")
    cfg = conf.ceph.parse(f)
    assert cfg.get('foo', 'bar') == 'baz'


def test_words_underscore():
    f = StringIO("""\
[foo]
bar_thud = baz
""")
    cfg = conf.ceph.parse(f)
    assert cfg.get('foo', 'bar_thud') == 'baz'
    assert cfg.get('foo', 'bar thud') == 'baz'


def test_words_space():
    f = StringIO("""\
[foo]
bar thud = baz
""")
    cfg = conf.ceph.parse(f)
    assert cfg.get('foo', 'bar_thud') == 'baz'
    assert cfg.get('foo', 'bar thud') == 'baz'


def test_words_many():
    f = StringIO("""\
[foo]
bar__ thud   quux = baz
""")
    cfg = conf.ceph.parse(f)
    assert cfg.get('foo', 'bar_thud_quux') == 'baz'
    assert cfg.get('foo', 'bar thud quux') == 'baz'

def test_write_words_underscore():
    cfg = conf.ceph.CephConf()
    cfg.add_section('foo')
    cfg.set('foo', 'bar thud quux', 'baz')
    f = StringIO()
    cfg.write(f)
    f.reset()
    assert f.readlines() == ['[foo]\n', 'bar_thud_quux = baz\n','\n']

########NEW FILE########
__FILENAME__ = test_mon
from ceph_deploy import mon
from ceph_deploy.conf.ceph import CephConf
from mock import Mock


def make_fake_conf():
    return CephConf()

# NOTE: If at some point we re-use this helper, move it out
# and make it even more generic

def make_fake_conn(receive_returns=None):
    receive_returns = receive_returns or (['{}'], '', 0)
    conn = Mock()
    conn.return_value = conn
    conn.execute = conn
    conn.receive = Mock(return_value=receive_returns)
    conn.result = Mock(return_value=conn)
    return conn


class TestCatchCommonErrors(object):

    def setup(self):
        self.logger = Mock()

    def assert_logger_message(self, logger, msg):
        calls = logger.call_args_list
        for log_call in calls:
            if msg in log_call[0][0]:
                return True
        raise AssertionError('"%s" was not found in any of %s' % (msg, calls))

    def test_warn_if_no_intial_members(self):
        fake_conn = make_fake_conn()
        cfg = make_fake_conf()
        mon.catch_mon_errors(fake_conn, self.logger, 'host', cfg, Mock())
        expected_msg = 'is not defined in `mon initial members`'
        self.assert_logger_message(self.logger.warning, expected_msg)

    def test_warn_if_host_not_in_intial_members(self):
        fake_conn = make_fake_conn()
        cfg = make_fake_conf()
        cfg.add_section('global')
        cfg.set('global', 'mon initial members', 'AAAA')
        mon.catch_mon_errors(fake_conn, self.logger, 'host', cfg, Mock())
        expected_msg = 'is not defined in `mon initial members`'
        self.assert_logger_message(self.logger.warning, expected_msg)

    def test_warn_if_not_mon_in_monmap(self):
        fake_conn = make_fake_conn()
        cfg = make_fake_conf()
        mon.catch_mon_errors(fake_conn, self.logger, 'host', cfg, Mock())
        expected_msg = 'does not exist in monmap'
        self.assert_logger_message(self.logger.warning, expected_msg)

    def test_warn_if_not_public_addr_and_not_public_netw(self):
        fake_conn = make_fake_conn()
        cfg = make_fake_conf()
        cfg.add_section('global')
        mon.catch_mon_errors(fake_conn, self.logger, 'host', cfg, Mock())
        expected_msg = 'neither `public_addr` nor `public_network`'
        self.assert_logger_message(self.logger.warning, expected_msg)

########NEW FILE########
__FILENAME__ = test_remotes
from mock import patch
from ceph_deploy.hosts import remotes
from ceph_deploy.hosts.remotes import platform_information

class FakeExists(object):

    def __init__(self, existing_paths):
        self.existing_paths = existing_paths

    def __call__(self, path):
        for existing_path in self.existing_paths:
            if path == existing_path:
                return path


class TestWhich(object):

    def setup(self):
        self.exists_module = 'ceph_deploy.hosts.remotes.os.path.exists'

    def test_finds_absolute_paths(self):
        exists = FakeExists(['/bin/ls'])
        with patch(self.exists_module, exists):
            path = remotes.which('ls')
        assert path == '/bin/ls'

    def test_does_not_find_executable(self):
        exists = FakeExists(['/bin/foo'])
        with patch(self.exists_module, exists):
            path = remotes.which('ls')
        assert path is None

class TestPlatformInformation(object):
    """ tests various inputs that remotes.platform_information handles

    you can test your OS string by comparing the results with the output from:
      python -c "import platform; print platform.linux_distribution()"
    """

    def setup(self):
        pass

    def test_handles_deb_version_num(self):
        def fake_distro(): return ('debian', '8.4', '')
        distro, release, codename = platform_information(fake_distro)
        assert distro == 'debian'
        assert release == '8.4'
        assert codename == 'jessie'

    def test_handles_deb_version_slash(self):
        def fake_distro(): return ('debian', 'wheezy/something', '')
        distro, release, codename = platform_information(fake_distro)
        assert distro == 'debian'
        assert release == 'wheezy/something'
        assert codename == 'wheezy'

    def test_handles_deb_version_slash_sid(self):
        def fake_distro(): return ('debian', 'jessie/sid', '')
        distro, release, codename = platform_information(fake_distro)
        assert distro == 'debian'
        assert release == 'jessie/sid'
        assert codename == 'sid'

    def test_handles_no_codename(self):
        def fake_distro(): return ('SlaOS', '99.999', '')
        distro, release, codename = platform_information(fake_distro)
        assert distro == 'SlaOS'
        assert release == '99.999'
        assert codename == ''

    # Normal distro strings
    def test_hanles_centos_64(self):
        def fake_distro(): return ('CentOS', '6.4', 'Final')
        distro, release, codename = platform_information(fake_distro)
        assert distro == 'CentOS'
        assert release == '6.4'
        assert codename == 'Final'


    def test_handles_ubuntu_percise(self):
        def fake_distro(): return ('Ubuntu', '12.04', 'precise')
        distro, release, codename = platform_information(fake_distro)
        assert distro == 'Ubuntu'
        assert release == '12.04'
        assert codename == 'precise'

########NEW FILE########
__FILENAME__ = test_hosts
from pytest import raises
from mock import Mock, patch

from ceph_deploy import exc
from ceph_deploy import hosts


class TestNormalized(object):

    def test_get_debian(self):
        result = hosts._normalized_distro_name('Debian')
        assert result == 'debian'

    def test_get_ubuntu(self):
        result = hosts._normalized_distro_name('Ubuntu')
        assert result == 'ubuntu'

    def test_get_suse(self):
        result = hosts._normalized_distro_name('SUSE LINUX')
        assert result == 'suse'

    def test_get_redhat(self):
        result = hosts._normalized_distro_name('RedHatEnterpriseLinux')
        assert result == 'redhat'


class TestHostGet(object):

    def make_fake_connection(self, platform_information=None):
        get_connection = Mock()
        get_connection.return_value = get_connection
        get_connection.remote_module.platform_information = Mock(
            return_value=platform_information)
        return get_connection

    def test_get_unsupported(self):
        fake_get_connection = self.make_fake_connection(('Solaris Enterprise', '', ''))
        with patch('ceph_deploy.hosts.get_connection', fake_get_connection):
            with raises(exc.UnsupportedPlatform):
                hosts.get('myhost')

    def test_get_unsupported_message(self):
        fake_get_connection = self.make_fake_connection(('Solaris Enterprise', '', ''))
        with patch('ceph_deploy.hosts.get_connection', fake_get_connection):
            with raises(exc.UnsupportedPlatform) as error:
                hosts.get('myhost')

        assert error.value.__str__() == 'Platform is not supported: Solaris Enterprise  '

    def test_get_unsupported_message_release(self):
        fake_get_connection = self.make_fake_connection(('Solaris', 'Tijuana', '12'))
        with patch('ceph_deploy.hosts.get_connection', fake_get_connection):
            with raises(exc.UnsupportedPlatform) as error:
                hosts.get('myhost')

        assert error.value.__str__() == 'Platform is not supported: Solaris 12 Tijuana'



class TestGetDistro(object):

    def test_get_debian(self):
        result = hosts._get_distro('Debian')
        assert result.__name__.endswith('debian')

    def test_get_ubuntu(self):
        # Ubuntu imports debian stuff
        result = hosts._get_distro('Ubuntu')
        assert result.__name__.endswith('debian')

    def test_get_centos(self):
        result = hosts._get_distro('CentOS')
        assert result.__name__.endswith('centos')

    def test_get_scientific(self):
        result = hosts._get_distro('Scientific')
        assert result.__name__.endswith('centos')

    def test_get_redhat(self):
        result = hosts._get_distro('RedHat')
        assert result.__name__.endswith('centos')

    def test_get_redhat_whitespace(self):
        result = hosts._get_distro('Red Hat Enterprise Linux')
        assert result.__name__.endswith('centos')

    def test_get_uknown(self):
        assert hosts._get_distro('Solaris') is None

    def test_get_fallback(self):
        result = hosts._get_distro('Solaris', 'Debian')
        assert result.__name__.endswith('debian')

########NEW FILE########
__FILENAME__ = test_calamari
import pytest
from ceph_deploy import calamari


class TestDistroIsSupported(object):

    @pytest.mark.parametrize(
        "distro_name",
        ['centos', 'redhat', 'ubuntu', 'debian'])
    def test_distro_is_supported(self, distro_name):
        assert calamari.distro_is_supported(distro_name) is True

    @pytest.mark.parametrize(
        "distro_name",
        ['fedora', 'mandriva', 'darwin', 'windows'])
    def test_distro_is_not_supported(self, distro_name):
        assert calamari.distro_is_supported(distro_name) is False

########NEW FILE########
__FILENAME__ = test_conf
from cStringIO import StringIO
from textwrap import dedent
from mock import Mock, patch
from ceph_deploy import conf
from ceph_deploy.tests import fakes


class TestLocateOrCreate(object):

    def setup(self):
        self.fake_write = Mock(name='fake_write')
        self.fake_file = fakes.mock_open(data=self.fake_write)
        self.fake_file.readline.return_value = self.fake_file

    def test_no_conf(self):
        fake_path = Mock()
        fake_path.exists = Mock(return_value=False)
        with patch('__builtin__.open', self.fake_file):
            with patch('ceph_deploy.conf.cephdeploy.path', fake_path):
                conf.cephdeploy.location()

        assert self.fake_file.called is True
        assert self.fake_file.call_args[0][0].endswith('/.cephdeploy.conf')

    def test_cwd_conf_exists(self):
        fake_path = Mock()
        fake_path.join = Mock(return_value='/srv/cephdeploy.conf')
        fake_path.exists = Mock(return_value=True)
        with patch('ceph_deploy.conf.cephdeploy.path', fake_path):
            result = conf.cephdeploy.location()

        assert result == '/srv/cephdeploy.conf'

    def test_home_conf_exists(self):
        fake_path = Mock()
        fake_path.expanduser = Mock(return_value='/home/alfredo/.cephdeploy.conf')
        fake_path.exists = Mock(side_effect=[False, True])
        with patch('ceph_deploy.conf.cephdeploy.path', fake_path):
            result = conf.cephdeploy.location()

        assert result == '/home/alfredo/.cephdeploy.conf'


class TestConf(object):

    def test_has_repos(self):
        cfg = conf.cephdeploy.Conf()
        cfg.sections = lambda: ['foo']
        assert cfg.has_repos is True

    def test_has_no_repos(self):
        cfg = conf.cephdeploy.Conf()
        cfg.sections = lambda: ['ceph-deploy-install']
        assert cfg.has_repos is False

    def test_get_repos_is_empty(self):
        cfg = conf.cephdeploy.Conf()
        cfg.sections = lambda: ['ceph-deploy-install']
        assert cfg.get_repos() == []

    def test_get_repos_is_not_empty(self):
        cfg = conf.cephdeploy.Conf()
        cfg.sections = lambda: ['ceph-deploy-install', 'foo']
        assert cfg.get_repos() == ['foo']

    def test_get_safe_not_empty(self):
        cfg = conf.cephdeploy.Conf()
        cfg.get = lambda section, key: True
        assert cfg.get_safe(1, 2) is True

    def test_get_safe_empty(self):
        cfg = conf.cephdeploy.Conf()
        assert cfg.get_safe(1, 2) is None


class TestConfGetList(object):

    def test_get_list_empty(self):
        cfg = conf.cephdeploy.Conf()
        conf_file = StringIO(dedent("""
        [foo]
        key =
        """))
        cfg.readfp(conf_file)
        assert cfg.get_list('foo', 'key') == ['']

    def test_get_list_empty_when_no_key(self):
        cfg = conf.cephdeploy.Conf()
        conf_file = StringIO(dedent("""
        [foo]
        """))
        cfg.readfp(conf_file)
        assert cfg.get_list('foo', 'key') == []

    def test_get_list_if_value_is_one_item(self):
        cfg = conf.cephdeploy.Conf()
        conf_file = StringIO(dedent("""
        [foo]
        key = 1
        """))
        cfg.readfp(conf_file)
        assert cfg.get_list('foo', 'key') == ['1']

    def test_get_list_with_mutltiple_items(self):
        cfg = conf.cephdeploy.Conf()
        conf_file = StringIO(dedent("""
        [foo]
        key = 1, 3, 4
        """))
        cfg.readfp(conf_file)
        assert cfg.get_list('foo', 'key') == ['1', '3', '4']

    def test_get_rid_of_comments(self):
        cfg = conf.cephdeploy.Conf()
        conf_file = StringIO(dedent("""
        [foo]
        key = 1, 3, 4 # this is a wonderful comment y'all
        """))
        cfg.readfp(conf_file)
        assert cfg.get_list('foo', 'key') == ['1', '3', '4']

    def test_get_rid_of_whitespace(self):
        cfg = conf.cephdeploy.Conf()
        conf_file = StringIO(dedent("""
        [foo]
        key = 1,   3     ,        4
        """))
        cfg.readfp(conf_file)
        assert cfg.get_list('foo', 'key') == ['1', '3', '4']

    def test_get_default_repo(self):
        cfg = conf.cephdeploy.Conf()
        conf_file = StringIO(dedent("""
        [foo]
        default = True
        """))
        cfg.readfp(conf_file)
        assert cfg.get_default_repo() == 'foo'

    def test_get_default_repo_fails_non_truthy(self):
        cfg = conf.cephdeploy.Conf()
        conf_file = StringIO(dedent("""
        [foo]
        default = 0
        """))
        cfg.readfp(conf_file)
        assert cfg.get_default_repo() is False


class TestSetOverrides(object):

    def setup(self):
        self.args = Mock()
        self.args.func.__name__ = 'foo'
        self.conf = Mock()

    def test_override_global(self):
        self.conf.sections = Mock(return_value=['ceph-deploy-global'])
        self.conf.items = Mock(return_value=(('foo', 1),))
        arg_obj = conf.cephdeploy.set_overrides(self.args, self.conf)
        assert arg_obj.foo == 1

    def test_override_foo_section(self):
        self.conf.sections = Mock(
            return_value=['ceph-deploy-global', 'ceph-deploy-foo']
        )
        self.conf.items = Mock(return_value=(('bar', 1),))
        arg_obj = conf.cephdeploy.set_overrides(self.args, self.conf)
        assert arg_obj.bar == 1

########NEW FILE########
__FILENAME__ = test_mon
import sys
import py.test
from mock import Mock, MagicMock, patch, call
from ceph_deploy import mon
from ceph_deploy.tests import fakes
from ceph_deploy.hosts.common import mon_create
from ceph_deploy.misc import mon_hosts, remote_shortname


def path_exists(target_paths=None):
    """
    A quick helper that enforces a check for the existence of a path. Since we
    are dealing with fakes, we allow to pass in a list of paths that are OK to
    return True, otherwise return False.
    """
    target_paths = target_paths or []

    def exists(path):
        return path in target_paths
    return exists


@py.test.mark.skipif(reason='failing due to removal of pushy')
class TestCreateMon(object):

    def setup(self):
        # this setup is way more verbose than normal
        # but we are forced to because this function needs a lot
        # passed in for remote execution. No other way around it.
        self.socket = Mock()
        self.socket.gethostname.return_value = 'hostname'
        self.fake_write = Mock(name='fake_write')
        self.fake_file = fakes.mock_open(data=self.fake_write)
        self.fake_file.readline.return_value = self.fake_file
        self.fake_file.readline.lstrip.return_value = ''
        self.distro = Mock()
        self.sprocess = Mock()
        self.paths = Mock()
        self.paths.mon.path = Mock(return_value='/cluster-hostname')
        self.logger = Mock()
        self.logger.info = self.logger.debug = lambda x: sys.stdout.write(str(x) + "\n")

    def test_create_mon_tmp_path_if_nonexistent(self):
        self.distro.sudo_conn.modules.os.path.exists = Mock(
            side_effect=path_exists(['/cluster-hostname']))
        self.paths.mon.constants.tmp_path = '/var/lib/ceph/tmp'
        args = Mock(return_value=['cluster', '1234', 'initd'])
        args.cluster = 'cluster'
        with patch('ceph_deploy.hosts.common.conf.load'):
            mon_create(self.distro, args, Mock(), 'hostname')

        result = self.distro.conn.remote_module.create_mon_path.call_args_list[-1]
        assert result == call('/var/lib/ceph/mon/cluster-hostname')

    def test_write_keyring(self):
        self.distro.sudo_conn.modules.os.path.exists = Mock(
            side_effect=path_exists(['/']))
        args = Mock(return_value=['cluster', '1234', 'initd'])
        args.cluster = 'cluster'
        with patch('ceph_deploy.hosts.common.conf.load'):
            with patch('ceph_deploy.hosts.common.remote') as fake_remote:
                mon_create(self.distro, self.logger, args, Mock(), 'hostname')

        # the second argument to `remote()` should be the write func
        result = fake_remote.call_args_list[1][0][-1].__name__
        assert result == 'write_monitor_keyring'

    def test_write_done_path(self):
        self.distro.sudo_conn.modules.os.path.exists = Mock(
            side_effect=path_exists(['/']))
        args = Mock(return_value=['cluster', '1234', 'initd'])
        args.cluster = 'cluster'

        with patch('ceph_deploy.hosts.common.conf.load'):
            with patch('ceph_deploy.hosts.common.remote') as fake_remote:
                mon_create(self.distro, self.logger, args, Mock(), 'hostname')

        # the second to last argument to `remote()` should be the done path
        # write
        result = fake_remote.call_args_list[-2][0][-1].__name__
        assert result == 'create_done_path'

    def test_write_init_path(self):
        self.distro.sudo_conn.modules.os.path.exists = Mock(
            side_effect=path_exists(['/']))
        args = Mock(return_value=['cluster', '1234', 'initd'])
        args.cluster = 'cluster'

        with patch('ceph_deploy.hosts.common.conf.load'):
            with patch('ceph_deploy.hosts.common.remote') as fake_remote:
                mon_create(self.distro, self.logger, args, Mock(), 'hostname')

        result = fake_remote.call_args_list[-1][0][-1].__name__
        assert result == 'create_init_path'

    def test_mon_hosts(self):
        hosts = Mock()
        for (name, host) in mon_hosts(('name1', 'name2.localdomain',
                    'name3:1.2.3.6', 'name4:localhost.localdomain')):
            hosts.get(name, host)

        expected = [call.get('name1', 'name1'),
                    call.get('name2', 'name2.localdomain'),
                    call.get('name3', '1.2.3.6'),
                    call.get('name4', 'localhost.localdomain')]
        result = hosts.mock_calls
        assert result == expected

    def test_remote_shortname_fqdn(self):
        socket = Mock()
        socket.gethostname.return_value = 'host.f.q.d.n'
        assert remote_shortname(socket) == 'host'

    def test_remote_shortname_host(self):
        socket = Mock()
        socket.gethostname.return_value = 'host'
        assert remote_shortname(socket) == 'host'


@py.test.mark.skipif(reason='failing due to removal of pushy')
class TestIsRunning(object):

    def setup(self):
        self.fake_popen = Mock()
        self.fake_popen.return_value = self.fake_popen

    def test_is_running_centos(self):
        centos_out = ['', "mon.mire094: running {'version': '0.6.15'}"]
        self.fake_popen.communicate = Mock(return_value=centos_out)
        with patch('ceph_deploy.mon.subprocess.Popen', self.fake_popen):
            result = mon.is_running(['ceph', 'status'])
        assert result is True

    def test_is_not_running_centos(self):
        centos_out = ['', "mon.mire094: not running {'version': '0.6.15'}"]
        self.fake_popen.communicate = Mock(return_value=centos_out)
        with patch('ceph_deploy.mon.subprocess.Popen', self.fake_popen):
            result = mon.is_running(['ceph', 'status'])
        assert result is False

    def test_is_dead_centos(self):
        centos_out = ['', "mon.mire094: dead {'version': '0.6.15'}"]
        self.fake_popen.communicate = Mock(return_value=centos_out)
        with patch('ceph_deploy.mon.subprocess.Popen', self.fake_popen):
            result = mon.is_running(['ceph', 'status'])
        assert result is False

    def test_is_running_ubuntu(self):
        ubuntu_out = ['', "ceph-mon (ceph/mira103) start/running, process 5866"]
        self.fake_popen.communicate = Mock(return_value=ubuntu_out)
        with patch('ceph_deploy.mon.subprocess.Popen', self.fake_popen):
            result = mon.is_running(['ceph', 'status'])
        assert result is True

    def test_is_not_running_ubuntu(self):
        ubuntu_out = ['', "ceph-mon (ceph/mira103) start/dead, process 5866"]
        self.fake_popen.communicate = Mock(return_value=ubuntu_out)
        with patch('ceph_deploy.mon.subprocess.Popen', self.fake_popen):
            result = mon.is_running(['ceph', 'status'])
        assert result is False

    def test_is_dead_ubuntu(self):
        ubuntu_out = ['', "ceph-mon (ceph/mira103) stop/not running, process 5866"]
        self.fake_popen.communicate = Mock(return_value=ubuntu_out)
        with patch('ceph_deploy.mon.subprocess.Popen', self.fake_popen):
            result = mon.is_running(['ceph', 'status'])
        assert result is False

########NEW FILE########
__FILENAME__ = test_osd
from ceph_deploy import osd


class TestMountPoint(object):

    def setup(self):
        self.osd_name = 'osd.1'

    def test_osd_name_not_found(self):
        output = [
            '/dev/sda :',
            ' /dev/sda1 other, ext2, mounted on /boot',
            ' /dev/sda2 other',
            ' /dev/sda5 other, LVM2_member',
        ]
        assert osd.get_osd_mount_point(output, self.osd_name) is None

    def test_osd_name_is_found(self):
        output = [
            '/dev/sda :',
            ' /dev/sda1 other, ext2, mounted on /boot',
            ' /dev/sda2 other',
            ' /dev/sda5 other, LVM2_member',
            '/dev/sdb :',
            ' /dev/sdb1 ceph data, active, cluster ceph, osd.1, journal /dev/sdb2',
        ]
        result = osd.get_osd_mount_point(output, self.osd_name)
        assert result == '/dev/sdb1'

    def test_osd_name_not_found_but_contained_in_output(self):
        output = [
            '/dev/sda :',
            ' /dev/sda1 otherosd.1, ext2, mounted on /boot',
            ' /dev/sda2 other',
            ' /dev/sda5 other, LVM2_member',
        ]
        assert osd.get_osd_mount_point(output, self.osd_name) is None

########NEW FILE########
__FILENAME__ = test_arg_validators
import socket
from mock import Mock
from argparse import ArgumentError
from pytest import raises

from ceph_deploy.util import arg_validators


class TestRegexMatch(object):

    def test_match_raises(self):
        validator = arg_validators.RegexMatch(r'\d+')
        with raises(ArgumentError):
            validator('1')

    def test_match_passes(self):
        validator = arg_validators.RegexMatch(r'\d+')
        assert validator('foo') == 'foo'

    def test_default_error_message(self):
        validator = arg_validators.RegexMatch(r'\d+')
        with raises(ArgumentError) as error:
            validator('1')
        message = error.value.message
        assert message == 'must match pattern \d+'

    def test_custom_error_message(self):
        validator = arg_validators.RegexMatch(r'\d+', 'wat')
        with raises(ArgumentError) as error:
            validator('1')
        message = error.value.message
        assert message == 'wat'


class TestHostName(object):

    def setup(self):
        self.fake_sock = Mock()
        self.fake_sock.gaierror = socket.gaierror
        self.fake_sock.getaddrinfo.side_effect = socket.gaierror

    def test_hostname_is_not_resolvable(self):
        hostname = arg_validators.Hostname(self.fake_sock)
        with raises(ArgumentError) as error:
            hostname('unresolvable')
        message = error.value.message
        assert 'is not resolvable' in message

    def test_hostname_with_name_is_not_resolvable(self):
        hostname = arg_validators.Hostname(self.fake_sock)
        with raises(ArgumentError) as error:
            hostname('name:foo')
        message = error.value.message
        assert 'foo is not resolvable' in message

    def test_ip_is_allowed_when_paired_with_host(self):
        self.fake_sock = Mock()
        self.fake_sock.gaierror = socket.gaierror

        def side_effect(*args):
                # First call passes, second call raises socket.gaierror
                self.fake_sock.getaddrinfo.side_effect = socket.gaierror

        self.fake_sock.getaddrinfo.side_effect = side_effect
        hostname = arg_validators.Hostname(self.fake_sock)
        result = hostname('name:192.168.1.111')
        assert result == 'name:192.168.1.111'

    def test_ipv6_is_allowed_when_paired_with_host(self):
        self.fake_sock = Mock()
        self.fake_sock.gaierror = socket.gaierror

        def side_effect(*args):
                # First call passes, second call raises socket.gaierror
                self.fake_sock.getaddrinfo.side_effect = socket.gaierror

        self.fake_sock.getaddrinfo.side_effect = side_effect
        hostname = arg_validators.Hostname(self.fake_sock)
        result = hostname('name:2001:0db8:85a3:0000:0000:8a2e:0370:7334')
        assert result == 'name:2001:0db8:85a3:0000:0000:8a2e:0370:7334'

    def test_host_is_resolvable(self):
        self.fake_sock = Mock()
        self.fake_sock.gaierror = socket.gaierror

        def side_effect(*args):
                # First call passes, second call raises socket.gaierror
                self.fake_sock.getaddrinfo.side_effect = socket.gaierror

        self.fake_sock.getaddrinfo.side_effect = side_effect
        hostname = arg_validators.Hostname(self.fake_sock)
        result = hostname('name:example.com')
        assert result == 'name:example.com'

    def test_hostname_must_be_an_ip(self):
        self.fake_sock.getaddrinfo = Mock()
        hostname = arg_validators.Hostname(self.fake_sock)
        with raises(ArgumentError) as error:
            hostname('0')
        message = error.value.message
        assert '0 must be a hostname' in message

########NEW FILE########
__FILENAME__ = test_constants
from ceph_deploy.util import constants


class TestPaths(object):

    def test_mon_path(self):
        assert constants.mon_path.startswith('/')
        assert constants.mon_path.endswith('/mon')

    def test_mds_path(self):
        assert constants.mds_path.startswith('/')
        assert constants.mds_path.endswith('/mds')

    def test_tmp_path(self):
        assert constants.tmp_path.startswith('/')
        assert constants.tmp_path.endswith('/tmp')

########NEW FILE########
__FILENAME__ = test_paths
from ceph_deploy.util import paths


class TestMonPaths(object):

    def test_base_path(self):
        result = paths.mon.base('mycluster')
        assert result.endswith('/mycluster-')

    def test_path(self):
        result = paths.mon.path('mycluster', 'myhostname')
        assert result.startswith('/')
        assert result.endswith('/mycluster-myhostname')

    def test_done(self):
        result = paths.mon.done('mycluster', 'myhostname')
        assert result.startswith('/')
        assert result.endswith('mycluster-myhostname/done')

    def test_init(self):
        result = paths.mon.init('mycluster', 'myhostname', 'init')
        assert result.startswith('/')
        assert result.endswith('mycluster-myhostname/init')

    def test_keyring(self):
        result = paths.mon.keyring('mycluster', 'myhostname')
        assert result.startswith('/')
        assert result.endswith('tmp/mycluster-myhostname.mon.keyring')

    def test_asok(self):
        result = paths.mon.asok('mycluster', 'myhostname')
        assert result.startswith('/')
        assert result.endswith('mycluster-mon.myhostname.asok')

    def test_monmap(self):
        result = paths.mon.monmap('mycluster', 'myhostname')
        assert result.startswith('/')
        assert result.endswith('tmp/mycluster.myhostname.monmap')

########NEW FILE########
__FILENAME__ = test_pkg_managers
from mock import patch, Mock
from ceph_deploy.util import pkg_managers


class TestRPM(object):

    def setup(self):
        self.to_patch = 'ceph_deploy.util.pkg_managers.process.run'

    def test_normal_flags(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.rpm(Mock())
            result = fake_run.call_args_list[-1]
        assert result[0][-1] == ['rpm', '-Uvh']

    def test_extended_flags(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.rpm(
                Mock(),
                ['-f', 'vim'])
            result = fake_run.call_args_list[-1]
        assert result[0][-1] == ['rpm', '-Uvh', '-f', 'vim']


class TestApt(object):

    def setup(self):
        self.to_patch = 'ceph_deploy.util.pkg_managers.process.run'

    def test_install_single_package(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.apt(Mock(), 'vim')
            result = fake_run.call_args_list[-1]
        assert 'install' in result[0][-1]
        assert result[0][-1][-1] == 'vim'

    def test_install_multiple_packages(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.apt(Mock(), ['vim', 'zsh'])
            result = fake_run.call_args_list[-1]
        assert 'install' in result[0][-1]
        assert result[0][-1][-2:] == ['vim', 'zsh']

    def test_remove_single_package(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.apt_remove(Mock(), 'vim')
            result = fake_run.call_args_list[-1]
        assert 'remove' in result[0][-1]
        assert result[0][-1][-1] == 'vim'

    def test_remove_multiple_packages(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.apt_remove(Mock(), ['vim', 'zsh'])
            result = fake_run.call_args_list[-1]
        assert 'remove' in result[0][-1]
        assert result[0][-1][-2:] == ['vim', 'zsh']


class TestYum(object):

    def setup(self):
        self.to_patch = 'ceph_deploy.util.pkg_managers.process.run'

    def test_install_single_package(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.yum(Mock(), 'vim')
            result = fake_run.call_args_list[-1]
        assert 'install' in result[0][-1]
        assert result[0][-1][-1] == 'vim'

    def test_install_multiple_packages(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.yum(Mock(), ['vim', 'zsh'])
            result = fake_run.call_args_list[-1]
        assert 'install' in result[0][-1]
        assert result[0][-1][-2:] == ['vim', 'zsh']

    def test_remove_single_package(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.yum_remove(Mock(), 'vim')
            result = fake_run.call_args_list[-1]
        assert 'remove' in result[0][-1]
        assert result[0][-1][-1] == 'vim'

    def test_remove_multiple_packages(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.yum_remove(Mock(), ['vim', 'zsh'])
            result = fake_run.call_args_list[-1]
        assert 'remove' in result[0][-1]
        assert result[0][-1][-2:] == ['vim', 'zsh']


class TestZypper(object):

    def setup(self):
        self.to_patch = 'ceph_deploy.util.pkg_managers.process.run'

    def test_install_single_package(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.zypper(Mock(), 'vim')
            result = fake_run.call_args_list[-1]
        assert 'install' in result[0][-1]
        assert result[0][-1][-1] == 'vim'

    def test_install_multiple_packages(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.zypper(Mock(), ['vim', 'zsh'])
            result = fake_run.call_args_list[-1]
        assert 'install' in result[0][-1]
        assert result[0][-1][-2:] == ['vim', 'zsh']

    def test_remove_single_package(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.zypper_remove(Mock(), 'vim')
            result = fake_run.call_args_list[-1]
        assert 'remove' in result[0][-1]
        assert result[0][-1][-1] == 'vim'

    def test_remove_multiple_packages(self):
        fake_run = Mock()
        with patch(self.to_patch, fake_run):
            pkg_managers.zypper_remove(Mock(), ['vim', 'zsh'])
            result = fake_run.call_args_list[-1]
        assert 'remove' in result[0][-1]
        assert result[0][-1][-2:] == ['vim', 'zsh']


########NEW FILE########
__FILENAME__ = arg_validators
import socket
import argparse
import re


class RegexMatch(object):
    """
    Performs regular expression match on value.
    If the regular expression pattern matches it will it will return an error
    message that will work with argparse.
    """

    def __init__(self, pattern, statement=None):
        self.string_pattern = pattern
        self.pattern = re.compile(pattern)
        self.statement = statement
        if not self.statement:
            self.statement = "must match pattern %s" % self.string_pattern

    def __call__(self, string):
        match = self.pattern.search(string)
        if match:
            raise argparse.ArgumentError(None, self.statement)
        return string


class Hostname(object):
    """
    Checks wether a given hostname is resolvable in DNS, otherwise raising and
    argparse error.
    """

    def __init__(self, _socket=None):
        self.socket = _socket or socket  # just used for testing

    def __call__(self, string):
        parts = string.split(':', 1)
        name = parts[0]
        host = parts[-1]
        try:
            self.socket.getaddrinfo(host, 0)
        except self.socket.gaierror:
            msg = "hostname: %s is not resolvable" % host
            raise argparse.ArgumentError(None, msg)

        try:
            self.socket.getaddrinfo(name, 0, 0, 0, 0, self.socket.AI_NUMERICHOST)
        except self.socket.gaierror:
            return string  # not an IP
        else:
            msg = '%s must be a hostname not an IP' % name
            raise argparse.ArgumentError(None, msg)

        return string

########NEW FILE########
__FILENAME__ = constants
from os.path import join

# Base Path for ceph
base_path = '/var/lib/ceph'

# Base run Path
base_run_path = '/var/run/ceph'

tmp_path = join(base_path, 'tmp')

mon_path = join(base_path, 'mon')

mds_path = join(base_path, 'mds')

osd_path = join(base_path, 'osd')

########NEW FILE########
__FILENAME__ = decorators
import logging
import sys
from functools import wraps


def catches(catch=None, handler=None, exit=True):
    """
    Very simple decorator that tries any of the exception(s) passed in as
    a single exception class or tuple (containing multiple ones) returning the
    exception message and optionally handling the problem if it raises with the
    handler if it is provided.

    So instead of doing something like this::

        def bar():
            try:
                some_call()
                print "Success!"
            except TypeError, exc:
                print "Error while handling some call: %s" % exc
                sys.exit(1)

    You would need to decorate it like this to have the same effect::

        @catches(TypeError)
        def bar():
            some_call()
            print "Success!"

    If multiple exceptions need to be caught they need to be provided as a
    tuple::

        @catches((TypeError, AttributeError))
        def bar():
            some_call()
            print "Success!"

    If adding a handler, it should accept a single argument, which would be the
    exception that was raised, it would look like::

        def my_handler(exc):
            print 'Handling exception %s' % str(exc)
            raise SystemExit

        @catches(KeyboardInterrupt, handler=my_handler)
        def bar():
            some_call()

    Note that the handler needs to raise its SystemExit if it wants to halt
    execution, otherwise the decorator would continue as a normal try/except
    block.

    """
    catch = catch or Exception
    logger = logging.getLogger('ceph_deploy')

    def decorate(f):

        @wraps(f)
        def newfunc(*a, **kw):
            try:
                return f(*a, **kw)
            except catch as e:
                if handler:
                    return handler(e)
                else:
                    logger.error(make_exception_message(e))
                    if exit:
                        sys.exit(1)
        return newfunc

    return decorate

#
# Decorator helpers
#


def make_exception_message(exc):
    """
    An exception is passed in and this function
    returns the proper string depending on the result
    so it is readable enough.
    """
    if str(exc):
        return '%s: %s\n' % (exc.__class__.__name__, exc)
    else:
        return '%s\n' % (exc.__class__.__name__)


########NEW FILE########
__FILENAME__ = log
import logging
import sys

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': RED,
    'ERROR': RED,
    'FATAL': RED,
}

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

BASE_COLOR_FORMAT = "[$BOLD%(name)s$RESET][%(color_levelname)-17s] %(message)s"
BASE_FORMAT = "[%(name)s][%(levelname)-6s] %(message)s"


def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.
    """
    unsupported_platform = (sys.platform in ('win32', 'Pocket PC'))
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    if unsupported_platform or not is_a_tty:
        return False
    return True


def color_message(message):
    message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    return message


class ColoredFormatter(logging.Formatter):
    """
    A very basic logging formatter that not only applies color to the levels of
    the ouput but will also truncate the level names so that they do not alter
    the visuals of logging when presented on the terminal.
    """

    def __init__(self, msg):
        logging.Formatter.__init__(self, msg)

    def format(self, record):
        levelname = record.levelname
        truncated_level = record.levelname[:6]
        levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + truncated_level + RESET_SEQ
        record.color_levelname = levelname_color
        return logging.Formatter.format(self, record)


def color_format():
    """
    Main entry point to get a colored formatter, it will use the
    BASE_FORMAT by default and fall back to no colors if the system
    does not support it
    """
    str_format = BASE_COLOR_FORMAT if supports_color() else BASE_FORMAT
    color_format = color_message(str_format)
    return ColoredFormatter(color_format)

########NEW FILE########
__FILENAME__ = net
from ceph_deploy import exc
import socket


def get_nonlocal_ip(host):
    """
    Search result of getaddrinfo() for a non-localhost-net address
    """
    try:
        ailist = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise exc.UnableToResolveError(host)
    for ai in ailist:
        # an ai is a 5-tuple; the last element is (ip, port)
        ip = ai[4][0]
        if not ip.startswith('127.'):
            return ip
    raise exc.UnableToResolveError(host)

########NEW FILE########
__FILENAME__ = mon
"""
Common paths for mon, based on the constant file paths defined in
``ceph_deploy.util.constants``.
All functions return a string representation of the absolute path
construction.
"""
from os.path import join

from ceph_deploy.util import constants


def base(cluster):
    cluster = "%s-" % cluster
    return join(constants.mon_path, cluster)


def path(cluster, hostname):
    """
    Example usage::

        >>> mon.path('mycluster', 'hostname')
        /var/lib/ceph/mon/mycluster-myhostname
    """
    return "%s%s" % (base(cluster), hostname)


def done(cluster, hostname):
    """
    Example usage::

        >>> mon.done('mycluster', 'hostname')
        /var/lib/ceph/mon/mycluster-myhostname/done
    """
    return join(path(cluster, hostname), 'done')


def init(cluster, hostname, init):
    """
    Example usage::

        >>> mon.init('mycluster', 'hostname', 'init')
        /var/lib/ceph/mon/mycluster-myhostname/init
    """
    return join(path(cluster, hostname), init)


def keyring(cluster, hostname):
    """
    Example usage::

        >>> mon.keyring('mycluster', 'myhostname')
        /var/lib/ceph/tmp/mycluster-myhostname.mon.keyring
    """
    keyring_file = '%s-%s.mon.keyring' % (cluster, hostname)
    return join(constants.tmp_path, keyring_file)


def asok(cluster, hostname):
    """
    Example usage::

        >>> mon.asok('mycluster', 'myhostname')
        /var/run/ceph/mycluster-mon.myhostname.asok
    """
    asok_file = '%s-mon.%s.asok' % (cluster, hostname)
    return join(constants.base_run_path, asok_file)


def monmap(cluster, hostname):
    """
    Example usage::

        >>> mon.monmap('mycluster', 'myhostname')
        /var/lib/ceph/tmp/mycluster.myhostname.monmap
    """
    monmap
    mon_map_file = '%s.%s.monmap' % (cluster, hostname)
    return join(constants.tmp_path, mon_map_file)

########NEW FILE########
__FILENAME__ = osd
"""
Comosd paths for osd, based on the constant file paths defined in
``ceph_deploy.util.constants``.
All functions return a string representation of the absolute path
construction.
"""
from os.path import join
from ceph_deploy.util import constants


def base(cluster):
    cluster = "%s-" % cluster
    return join(constants.osd_path, cluster)

########NEW FILE########
__FILENAME__ = pkg_managers
from ceph_deploy.lib.remoto import process


def apt(conn, packages, *a, **kw):
    if isinstance(packages, str):
        packages = [packages]
    cmd = [
        'env',
        'DEBIAN_FRONTEND=noninteractive',
        'apt-get',
        'install',
        '--assume-yes',
    ]
    cmd.extend(packages)
    return process.run(
        conn,
        cmd,
        *a,
        **kw
    )


def apt_remove(conn, packages, *a, **kw):
    if isinstance(packages, str):
        packages = [packages]

    purge = kw.pop('purge', False)
    cmd = [
        'apt-get',
        '-q',
        'remove',
        '-f',
        '-y',
        '--force-yes',
    ]
    if purge:
        cmd.append('--purge')
    cmd.extend(packages)

    return process.run(
        conn,
        cmd,
        *a,
        **kw
    )


def apt_update(conn):
    cmd = [
        'apt-get',
        '-q',
        'update',
    ]
    return process.run(
        conn,
        cmd,
    )


def yum(conn, packages, *a, **kw):
    if isinstance(packages, str):
        packages = [packages]

    cmd = [
        'yum',
        '-y',
        'install',
    ]
    cmd.extend(packages)
    return process.run(
        conn,
        cmd,
        *a,
        **kw
    )


def yum_remove(conn, packages, *a, **kw):
    cmd = [
        'yum',
        '-y',
        '-q',
        'remove',
    ]
    if isinstance(packages, str):
        cmd.append(packages)
    else:
        cmd.extend(packages)
    return process.run(
        conn,
        cmd,
        *a,
        **kw
    )


def yum_clean(conn, item=None):
    item = item or 'all'
    cmd = [
        'yum',
        'clean',
        item,
    ]

    return process.run(
        conn,
        cmd,
    )


def rpm(conn, rpm_args=None, *a, **kw):
    """
    A minimal front end for ``rpm`. Extra flags can be passed in via
    ``rpm_args`` as an iterable.
    """
    rpm_args = rpm_args or []
    cmd = [
        'rpm',
        '-Uvh',
    ]
    cmd.extend(rpm_args)
    return process.run(
        conn,
        cmd,
        *a,
        **kw
    )


def zypper(conn, packages, *a, **kw):
    if isinstance(packages, str):
        packages = [packages]

    cmd = [
        'zypper',
        '--non-interactive',
        'install',
    ]

    cmd.extend(packages)
    return process.run(
        conn,
        cmd,
        *a,
        **kw
    )


def zypper_remove(conn, packages, *a, **kw):
    cmd = [
        'zypper',
        '--non-interactive',
        '--quiet',
        'remove',
        ]

    if isinstance(packages, str):
        cmd.append(packages)
    else:
        cmd.extend(packages)
    return process.run(
        conn,
        cmd,
        *a,
        **kw
    )

########NEW FILE########
__FILENAME__ = ssh
import logging
from ceph_deploy.lib.remoto import process
from ceph_deploy.lib.remoto.connection import needs_ssh
from ceph_deploy.connection import get_local_connection


def can_connect_passwordless(hostname):
    """
    Ensure that current host can SSH remotely to the remote
    host using the ``BatchMode`` option to prevent a password prompt.

    That attempt will error with an exit status of 255 and a ``Permission
    denied`` message.
    """
    # Ensure we are not doing this for local hosts
    if not needs_ssh(hostname):
        return True

    logger = logging.getLogger(hostname)
    with get_local_connection(logger) as conn:
        # Check to see if we can login, disabling password prompts
        command = ['ssh', '-CT', '-o', 'BatchMode=yes', hostname]
        out, err, retval = process.check(conn, command, stop_on_error=False)
        expected_error = 'Permission denied '
        has_key_error = False
        for line in err:
            if expected_error in line:
                has_key_error = True

        if retval == 255 and has_key_error:
            return False
    return True

########NEW FILE########
__FILENAME__ = templates


ceph_repo = """
[ceph]
name=Ceph packages for $basearch
baseurl={repo_url}/$basearch
enabled=1
gpgcheck=1
type=rpm-md
gpgkey={gpg_url}

[ceph-noarch]
name=Ceph noarch packages
baseurl={repo_url}/noarch
enabled=1
gpgcheck=1
type=rpm-md
gpgkey={gpg_url}

[ceph-source]
name=Ceph source packages
baseurl={repo_url}/SRPMS
enabled=0
gpgcheck=1
type=rpm-md
gpgkey={gpg_url}
"""

custom_repo = """
[{repo_name}]
name={name}
baseurl={baseurl}
enabled={enabled}
gpgcheck={gpgcheck}
type={_type}
gpgkey={gpgkey}
proxy={proxy}
"""

########NEW FILE########
__FILENAME__ = validate
import argparse
import re


ALPHANUMERIC_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9]*$')


def alphanumeric(s):
    """
    Enforces string to be alphanumeric with leading alpha.
    """
    if not ALPHANUMERIC_RE.match(s):
        raise argparse.ArgumentTypeError(
            'argument must start with a letter and contain only letters and numbers',
            )
    return s

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# ceph-deploy documentation build configuration file, created by
# sphinx-quickstart on Mon Oct 21 09:32:42 2013.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('_themes'))
sys.path.insert(0, os.path.abspath('..'))
import ceph_deploy

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'contents'

# General information about the project.
project = u'ceph-deploy'
copyright = u'2013, Inktank'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = ceph_deploy.__version__
# The full version, including alpha/beta/rc tags.
release = ceph_deploy.__version__

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
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'ceph'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

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
htmlhelp_basename = 'ceph-deploydoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'ceph-deploy.tex', u'ceph-deploy Documentation',
   u'Inktank', 'manual'),
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


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'ceph-deploy', u'ceph-deploy Documentation',
     [u'Inktank'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'ceph-deploy', u'ceph-deploy Documentation',
   u'Inktank', 'ceph-deploy', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# XXX Uncomment when we are ready to link to ceph docs
# Example configuration for intersphinx: refer to the Python standard library.
#intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = vendor
import subprocess
import os
from os import path
import traceback
import sys


error_msg = """
This library depends on sources fetched when packaging that failed to be
retrieved.

This means that it will *not* work as expected. Errors encountered:
"""


def run(cmd):
    print '[vendoring] Running command: %s' % ' '.join(cmd)
    try:
        result = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
    except Exception:
        # if building with python2.5 this makes it compatible
        _, error, _ = sys.exc_info()
        print_error([], traceback.format_exc(error).split('\n'))
        raise SystemExit(1)

    if result.wait():
        print_error(result.stdout.readlines(), result.stderr.readlines())


def print_error(stdout, stderr):
    print '*'*80
    print error_msg
    for line in stdout:
        print line
    for line in stderr:
        print line
    print '*'*80


def vendor_library(name, version):
    this_dir = path.dirname(path.abspath(__file__))
    vendor_dest = path.join(this_dir, 'ceph_deploy/lib/%s' % name)
    vendor_src = path.join(this_dir, name)
    vendor_module = path.join(vendor_src, name)
    current_dir = os.getcwd()

    if path.exists(vendor_src):
        run(['rm', '-rf', vendor_src])

    if path.exists(vendor_dest):
        module = __import__('ceph_deploy.lib.remoto', globals(), locals(), ['__version__'])
        if module.__version__ != version:
            run(['rm', '-rf', vendor_dest])

    if not path.exists(vendor_dest):
        run(['git', 'clone', 'git://ceph.com/%s' % name])
        os.chdir(vendor_src)
        run(['git', 'checkout', version])
        run(['mv', vendor_module, vendor_dest])
    os.chdir(current_dir)


def vendorize(vendor_requirements):
    """
    This is the main entry point for vendorizing requirements. It expects
    a list of tuples that should contain the name of the library and the
    version.

    For example, a library ``foo`` with version ``0.0.1`` would look like::

        vendor_requirements = [
            ('foo', '0.0.1'),
        ]
    """

    for library in vendor_requirements:
        name, version = library
        vendor_library(name, version)

########NEW FILE########
