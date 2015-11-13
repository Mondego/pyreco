__FILENAME__ = access
import os, logging
from ConfigParser import NoSectionError, NoOptionError

from gitosis import group

def haveAccess(config, user, mode, path):
    """
    Map request for write access to allowed path.

    Note for read-only access, the caller should check for write
    access too.

    Returns ``None`` for no access, or a tuple of toplevel directory
    containing repositories and a relative path to the physical repository.
    """
    log = logging.getLogger('gitosis.access.haveAccess')

    log.debug(
        'Access check for %(user)r as %(mode)r on %(path)r...'
        % dict(
        user=user,
        mode=mode,
        path=path,
        ))

    basename, ext = os.path.splitext(path)
    if ext == '.git':
        log.debug(
            'Stripping .git suffix from %(path)r, new value %(basename)r'
            % dict(
            path=path,
            basename=basename,
            ))
        path = basename

    for groupname in group.getMembership(config=config, user=user):
        try:
            repos = config.get('group %s' % groupname, mode)
        except (NoSectionError, NoOptionError):
            repos = []
        else:
            repos = repos.split()

        mapping = None

        if path in repos:
            log.debug(
                'Access ok for %(user)r as %(mode)r on %(path)r'
                % dict(
                user=user,
                mode=mode,
                path=path,
                ))
            mapping = path
        else:
            try:
                mapping = config.get('group %s' % groupname,
                                     'map %s %s' % (mode, path))
            except (NoSectionError, NoOptionError):
                pass
            else:
                log.debug(
                    'Access ok for %(user)r as %(mode)r on %(path)r=%(mapping)r'
                    % dict(
                    user=user,
                    mode=mode,
                    path=path,
                    mapping=mapping,
                    ))

        if mapping is not None:
            prefix = None
            try:
                prefix = config.get(
                    'group %s' % groupname, 'repositories')
            except (NoSectionError, NoOptionError):
                try:
                    prefix = config.get('gitosis', 'repositories')
                except (NoSectionError, NoOptionError):
                    prefix = 'repositories'

            log.debug(
                'Using prefix %(prefix)r for %(path)r'
                % dict(
                prefix=prefix,
                path=mapping,
                ))
            return (prefix, mapping)

########NEW FILE########
__FILENAME__ = app
import os
import sys
import logging
import optparse
import errno
import ConfigParser

log = logging.getLogger('gitosis.app')

class CannotReadConfigError(Exception):
    """Unable to read config file"""

    def __str__(self):
        return '%s: %s' % (self.__doc__, ': '.join(self.args))

class ConfigFileDoesNotExistError(CannotReadConfigError):
    """Configuration does not exist"""

class App(object):
    name = None

    def run(class_):
        app = class_()
        return app.main()
    run = classmethod(run)

    def main(self):
        self.setup_basic_logging()
        parser = self.create_parser()
        (options, args) = parser.parse_args()
        cfg = self.create_config(options)
        try:
            self.read_config(options, cfg)
        except CannotReadConfigError, e:
            log.error(str(e))
            sys.exit(1)
        self.setup_logging(cfg)
        self.handle_args(parser, cfg, options, args)

    def setup_basic_logging(self):
        logging.basicConfig()

    def create_parser(self):
        parser = optparse.OptionParser()
        parser.set_defaults(
            config=os.path.expanduser('~/.gitosis.conf'),
            )
        parser.add_option('--config',
                          metavar='FILE',
                          help='read config from FILE',
                          )

        return parser

    def create_config(self, options):
        cfg = ConfigParser.RawConfigParser()
        return cfg

    def read_config(self, options, cfg):
        try:
            conffile = file(options.config)
        except (IOError, OSError), e:
            if e.errno == errno.ENOENT:
                # special case this because gitosis-init wants to
                # ignore this particular error case
                raise ConfigFileDoesNotExistError(str(e))
            else:
                raise CannotReadConfigError(str(e))
        try:
            cfg.readfp(conffile)
        finally:
            conffile.close()

    def setup_logging(self, cfg):
        try:
            loglevel = cfg.get('gitosis', 'loglevel')
        except (ConfigParser.NoSectionError,
                ConfigParser.NoOptionError):
            pass
        else:
            try:
                symbolic = logging._levelNames[loglevel]
            except KeyError:
                log.warning(
                    'Ignored invalid loglevel configuration: %r',
                    loglevel,
                    )
            else:
                logging.root.setLevel(symbolic)

    def handle_args(self, parser, cfg, options, args):
        if args:
            parser.error('not expecting arguments')

########NEW FILE########
__FILENAME__ = gitdaemon
import errno
import logging
import os

from ConfigParser import NoSectionError, NoOptionError

log = logging.getLogger('gitosis.gitdaemon')

from gitosis import util

def export_ok_path(repopath):
    p = os.path.join(repopath, 'git-daemon-export-ok')
    return p

def allow_export(repopath):
    p = export_ok_path(repopath)
    file(p, 'a').close()

def deny_export(repopath):
    p = export_ok_path(repopath)
    try:
        os.unlink(p)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise

def _extract_reldir(topdir, dirpath):
    if topdir == dirpath:
        return '.'
    prefix = topdir + '/'
    assert dirpath.startswith(prefix)
    reldir = dirpath[len(prefix):]
    return reldir

def set_export_ok(config):
    repositories = util.getRepositoryDir(config)

    try:
        global_enable = config.getboolean('gitosis', 'daemon')
    except (NoSectionError, NoOptionError):
        global_enable = False
    log.debug(
        'Global default is %r',
        {True: 'allow', False: 'deny'}.get(global_enable),
        )

    def _error(e):
        if e.errno == errno.ENOENT:
            pass
        else:
            raise e

    for (dirpath, dirnames, filenames) \
            in os.walk(repositories, onerror=_error):
        # oh how many times i have wished for os.walk to report
        # topdir and reldir separately, instead of dirpath
        reldir = _extract_reldir(
            topdir=repositories,
            dirpath=dirpath,
            )

        log.debug('Walking %r, seeing %r', reldir, dirnames)

        to_recurse = []
        repos = []
        for dirname in dirnames:
            if dirname.endswith('.git'):
                repos.append(dirname)
            else:
                to_recurse.append(dirname)
        dirnames[:] = to_recurse

        for repo in repos:
            name, ext = os.path.splitext(repo)
            if reldir != '.':
                name = os.path.join(reldir, name)
            assert ext == '.git'
            try:
                enable = config.getboolean('repo %s' % name, 'daemon')
            except (NoSectionError, NoOptionError):
                enable = global_enable

            if enable:
                log.debug('Allow %r', name)
                allow_export(os.path.join(dirpath, repo))
            else:
                log.debug('Deny %r', name)
                deny_export(os.path.join(dirpath, repo))

########NEW FILE########
__FILENAME__ = gitweb
"""
Generate ``gitweb`` project list based on ``gitosis.conf``.

To plug this into ``gitweb``, you have two choices.

- The global way, edit ``/etc/gitweb.conf`` to say::

	$projects_list = "/path/to/your/projects.list";

  Note that there can be only one such use of gitweb.

- The local way, create a new config file::

	do "/etc/gitweb.conf" if -e "/etc/gitweb.conf";
	$projects_list = "/path/to/your/projects.list";
        # see ``repositories`` in the ``gitosis`` section
        # of ``~/.gitosis.conf``; usually ``~/repositories``
        # but you need to expand the tilde here
	$projectroot = "/path/to/your/repositories";

   Then in your web server, set environment variable ``GITWEB_CONFIG``
   to point to this file.

   This way allows you have multiple separate uses of ``gitweb``, and
   isolates the changes a bit more nicely. Recommended.
"""

import os, urllib, logging

from ConfigParser import NoSectionError, NoOptionError

from gitosis import util

def _escape_filename(s):
    s = s.replace('\\', '\\\\')
    s = s.replace('$', '\\$')
    s = s.replace('"', '\\"')
    return s

def generate_project_list_fp(config, fp):
    """
    Generate projects list for ``gitweb``.

    :param config: configuration to read projects from
    :type config: RawConfigParser

    :param fp: writable for ``projects.list``
    :type fp: (file-like, anything with ``.write(data)``)
    """
    log = logging.getLogger('gitosis.gitweb.generate_projects_list')

    repositories = util.getRepositoryDir(config)

    try:
        global_enable = config.getboolean('gitosis', 'gitweb')
    except (NoSectionError, NoOptionError):
        global_enable = False

    for section in config.sections():
        l = section.split(None, 1)
        type_ = l.pop(0)
        if type_ != 'repo':
            continue
        if not l:
            continue

        try:
            enable = config.getboolean(section, 'gitweb')
        except (NoSectionError, NoOptionError):
            enable = global_enable

        if not enable:
            continue

        name, = l

        if not os.path.exists(os.path.join(repositories, name)):
            namedotgit = '%s.git' % name
            if os.path.exists(os.path.join(repositories, namedotgit)):
                name = namedotgit
            else:
                log.warning(
                    'Cannot find %(name)r in %(repositories)r'
                    % dict(name=name, repositories=repositories))

        response = [name]
        try:
            owner = config.get(section, 'owner')
        except (NoSectionError, NoOptionError):
            pass
        else:
            response.append(owner)

        line = ' '.join([urllib.quote_plus(s) for s in response])
        print >>fp, line

def generate_project_list(config, path):
    """
    Generate projects list for ``gitweb``.

    :param config: configuration to read projects from
    :type config: RawConfigParser

    :param path: path to write projects list to
    :type path: str
    """
    tmp = '%s.%d.tmp' % (path, os.getpid())

    f = file(tmp, 'w')
    try:
        generate_project_list_fp(config=config, fp=f)
    finally:
        f.close()

    os.rename(tmp, path)


def set_descriptions(config):
    """
    Set descriptions for gitweb use.
    """
    log = logging.getLogger('gitosis.gitweb.set_descriptions')

    repositories = util.getRepositoryDir(config)

    for section in config.sections():
        l = section.split(None, 1)
        type_ = l.pop(0)
        if type_ != 'repo':
            continue
        if not l:
            continue

        try:
            description = config.get(section, 'description')
        except (NoSectionError, NoOptionError):
            continue

        if not description:
            continue

        name, = l

        if not os.path.exists(os.path.join(repositories, name)):
            namedotgit = '%s.git' % name
            if os.path.exists(os.path.join(repositories, namedotgit)):
                name = namedotgit
            else:
                log.warning(
                    'Cannot find %(name)r in %(repositories)r'
                    % dict(name=name, repositories=repositories))
                continue

        path = os.path.join(
            repositories,
            name,
            'description',
            )
        tmp = '%s.%d.tmp' % (path, os.getpid())
        f = file(tmp, 'w')
        try:
            print >>f, description
        finally:
            f.close()
        os.rename(tmp, path)

########NEW FILE########
__FILENAME__ = group
import logging
from ConfigParser import NoSectionError, NoOptionError

def _getMembership(config, user, seen):
    log = logging.getLogger('gitosis.group.getMembership')

    for section in config.sections():
        GROUP_PREFIX = 'group '
        if not section.startswith(GROUP_PREFIX):
            continue
        group = section[len(GROUP_PREFIX):]
        if group in seen:
            continue

        try:
            members = config.get(section, 'members')
        except (NoSectionError, NoOptionError):
            members = []
        else:
            members = members.split()

        # @all is the only group where membership needs to be
        # bootstrapped like this, anything else gets started from the
        # username itself
        if (user in members
            or '@all' in members):
            log.debug('found %(user)r in %(group)r' % dict(
                user=user,
                group=group,
                ))
            seen.add(group)
            yield group

            for member_of in _getMembership(
                config, '@%s' % group, seen,
                ):
                yield member_of


def getMembership(config, user):
    """
    Generate groups ``user`` is member of, according to ``config``

    :type config: RawConfigParser
    :type user: str
    :param _seen: internal use only
    """

    seen = set()
    for member_of in _getMembership(config, user, seen):
        yield member_of

    # everyone is always a member of group "all"
    yield 'all'


########NEW FILE########
__FILENAME__ = init
"""
Initialize a user account for use with gitosis.
"""

import errno
import logging
import os
import sys

from pkg_resources import resource_filename
from cStringIO import StringIO
from ConfigParser import RawConfigParser

from gitosis import repository
from gitosis import run_hook
from gitosis import ssh
from gitosis import util
from gitosis import app

log = logging.getLogger('gitosis.init')

def read_ssh_pubkey(fp=None):
    if fp is None:
        fp = sys.stdin
    line = fp.readline()
    return line

class InsecureSSHKeyUsername(Exception):
    """Username contains not allowed characters"""

    def __str__(self):
        return '%s: %s' % (self.__doc__, ': '.join(self.args))

def ssh_extract_user(pubkey):
    _, user = pubkey.rsplit(None, 1)
    if ssh.isSafeUsername(user):
        return user
    else:
        raise InsecureSSHKeyUsername(repr(user))

def initial_commit(git_dir, cfg, pubkey, user):
    repository.fast_import(
        git_dir=git_dir,
        commit_msg='Automatic creation of gitosis repository.',
        committer='Gitosis Admin <%s>' % user,
        files=[
            ('keydir/%s.pub' % user, pubkey),
            ('gitosis.conf', cfg),
            ],
        )

def symlink_config(git_dir):
    dst = os.path.expanduser('~/.gitosis.conf')
    tmp = '%s.%d.tmp' % (dst, os.getpid())
    try:
        os.unlink(tmp)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise
    os.symlink(
        os.path.join(git_dir, 'gitosis.conf'),
        tmp,
        )
    os.rename(tmp, dst)

def init_admin_repository(
    git_dir,
    pubkey,
    user,
    ):
    repository.init(
        path=git_dir,
        template=resource_filename('gitosis.templates', 'admin')
        )
    repository.init(
        path=git_dir,
        )
    if not repository.has_initial_commit(git_dir):
        log.info('Making initial commit...')
        # ConfigParser does not guarantee order, so jump through hoops
        # to make sure [gitosis] is first
        cfg_file = StringIO()
        print >>cfg_file, '[gitosis]'
        print >>cfg_file
        cfg = RawConfigParser()
        cfg.add_section('group gitosis-admin')
        cfg.set('group gitosis-admin', 'members', user)
        cfg.set('group gitosis-admin', 'writable', 'gitosis-admin')
        cfg.write(cfg_file)
        initial_commit(
            git_dir=git_dir,
            cfg=cfg_file.getvalue(),
            pubkey=pubkey,
            user=user,
            )

class Main(app.App):
    def create_parser(self):
        parser = super(Main, self).create_parser()
        parser.set_usage('%prog [OPTS]')
        parser.set_description(
            'Initialize a user account for use with gitosis')
        return parser

    def read_config(self, *a, **kw):
        # ignore errors that result from non-existent config file
        try:
            super(Main, self).read_config(*a, **kw)
        except app.ConfigFileDoesNotExistError:
            pass

    def handle_args(self, parser, cfg, options, args):
        super(Main, self).handle_args(parser, cfg, options, args)

        os.umask(0022)

        log.info('Reading SSH public key...')
        pubkey = read_ssh_pubkey()
        user = ssh_extract_user(pubkey)
        if user is None:
            log.error('Cannot parse user from SSH public key.')
            sys.exit(1)
        log.info('Admin user is %r', user)
        log.info('Creating generated files directory...')
        generated = util.getGeneratedFilesDir(config=cfg)
        util.mkdir(generated)
        log.info('Creating repository structure...')
        repositories = util.getRepositoryDir(cfg)
        util.mkdir(repositories)
        admin_repository = os.path.join(repositories, 'gitosis-admin.git')
        init_admin_repository(
            git_dir=admin_repository,
            pubkey=pubkey,
            user=user,
            )
        log.info('Running post-update hook...')
        util.mkdir(os.path.expanduser('~/.ssh'), 0700)
        run_hook.post_update(cfg=cfg, git_dir=admin_repository)
        log.info('Symlinking ~/.gitosis.conf to repository...')
        symlink_config(git_dir=admin_repository)
        log.info('Done.')

########NEW FILE########
__FILENAME__ = repository
import errno
import os
import re
import subprocess
import sys

from gitosis import util

class GitError(Exception):
    """git failed"""

    def __str__(self):
        return '%s: %s' % (self.__doc__, ': '.join(self.args))

class GitInitError(Exception):
    """git init failed"""

def init(
    path,
    template=None,
    _git=None,
    ):
    """
    Create a git repository at C{path} (if missing).

    Leading directories of C{path} must exist.

    @param path: Path of repository create.

    @type path: str

    @param template: Template directory, to pass to C{git init}.

    @type template: str
    """
    if _git is None:
        _git = 'git'

    util.mkdir(path, 0750)
    args = [
        _git,
        '--git-dir=.',
        'init',
        ]
    if template is not None:
        args.append('--template=%s' % template)
    returncode = subprocess.call(
        args=args,
        cwd=path,
        stdout=sys.stderr,
        close_fds=True,
        )
    if returncode != 0:
        raise GitInitError('exit status %d' % returncode)


class GitFastImportError(GitError):
    """git fast-import failed"""
    pass

def fast_import(
    git_dir,
    commit_msg,
    committer,
    files,
    parent=None,
    ):
    """
    Create an initial commit.
    """
    child = subprocess.Popen(
        args=[
            'git',
            '--git-dir=.',
            'fast-import',
            '--quiet',
            '--date-format=now',
            ],
        cwd=git_dir,
        stdin=subprocess.PIPE,
        close_fds=True,
        )
    files = list(files)
    for index, (path, content) in enumerate(files):
        child.stdin.write("""\
blob
mark :%(mark)d
data %(len)d
%(content)s
""" % dict(
            mark=index+1,
            len=len(content),
            content=content,
            ))
    child.stdin.write("""\
commit refs/heads/master
committer %(committer)s now
data %(commit_msg_len)d
%(commit_msg)s
""" % dict(
            committer=committer,
            commit_msg_len=len(commit_msg),
            commit_msg=commit_msg,
            ))
    if parent is not None:
        assert not parent.startswith(':')
        child.stdin.write("""\
from %(parent)s
""" % dict(
                parent=parent,
                ))
    for index, (path, content) in enumerate(files):
        child.stdin.write('M 100644 :%d %s\n' % (index+1, path))
    child.stdin.close()
    returncode = child.wait()
    if returncode != 0:
        raise GitFastImportError(
            'git fast-import failed', 'exit status %d' % returncode)

class GitExportError(GitError):
    """Export failed"""
    pass

class GitReadTreeError(GitExportError):
    """git read-tree failed"""

class GitCheckoutIndexError(GitExportError):
    """git checkout-index failed"""

def export(git_dir, path):
    try:
        os.mkdir(path)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise
    returncode = subprocess.call(
        args=[
            'git',
            '--git-dir=%s' % git_dir,
            'read-tree',
            'HEAD',
            ],
        close_fds=True,
        )
    if returncode != 0:
        raise GitReadTreeError('exit status %d' % returncode)
    # jumping through hoops to be compatible with git versions
    # that don't have --work-tree=
    env = {}
    env.update(os.environ)
    env['GIT_WORK_TREE'] = '.'
    returncode = subprocess.call(
        args=[
            'git',
            '--git-dir=%s' % os.path.abspath(git_dir),
            'checkout-index',
            '-a',
            '-f',
            ],
        cwd=path,
        close_fds=True,
        env=env,
        )
    if returncode != 0:
        raise GitCheckoutIndexError('exit status %d' % returncode)

class GitHasInitialCommitError(GitError):
    """Check for initial commit failed"""

class GitRevParseError(GitError):
    """rev-parse failed"""

def has_initial_commit(git_dir):
    child = subprocess.Popen(
        args=[
            'git',
            '--git-dir=.',
            'rev-parse',
            'HEAD',
            ],
        cwd=git_dir,
        stdout=subprocess.PIPE,
        close_fds=True,
        )
    got = child.stdout.read()
    returncode = child.wait()
    if returncode != 0:
        raise GitRevParseError('exit status %d' % returncode)
    if got == 'HEAD\n':
        return False
    elif re.match('^[0-9a-f]{40}\n$', got):
        return True
    else:
        raise GitHasInitialCommitError('Unknown git HEAD: %r' % got)

########NEW FILE########
__FILENAME__ = run_hook
"""
Perform gitosis actions for a git hook.
"""

import errno
import logging
import os
import sys
import shutil

from gitosis import repository
from gitosis import ssh
from gitosis import gitweb
from gitosis import gitdaemon
from gitosis import app
from gitosis import util

def post_update(cfg, git_dir):
    export = os.path.join(git_dir, 'gitosis-export')
    try:
        shutil.rmtree(export)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise
    repository.export(git_dir=git_dir, path=export)
    os.rename(
        os.path.join(export, 'gitosis.conf'),
        os.path.join(export, '..', 'gitosis.conf'),
        )
    # re-read config to get up-to-date settings
    cfg.read(os.path.join(export, '..', 'gitosis.conf'))
    gitweb.set_descriptions(
        config=cfg,
        )
    generated = util.getGeneratedFilesDir(config=cfg)
    gitweb.generate_project_list(
        config=cfg,
        path=os.path.join(generated, 'projects.list'),
        )
    gitdaemon.set_export_ok(
        config=cfg,
        )
    authorized_keys = util.getSSHAuthorizedKeysPath(config=cfg)
    ssh.writeAuthorizedKeys(
        path=authorized_keys,
        keydir=os.path.join(export, 'keydir'),
        )

class Main(app.App):
    def create_parser(self):
        parser = super(Main, self).create_parser()
        parser.set_usage('%prog [OPTS] HOOK')
        parser.set_description(
            'Perform gitosis actions for a git hook')
        return parser

    def handle_args(self, parser, cfg, options, args):
        try:
            (hook,) = args
        except ValueError:
            parser.error('Missing argument HOOK.')

        log = logging.getLogger('gitosis.run_hook')
        os.umask(0022)

        git_dir = os.environ.get('GIT_DIR')
        if git_dir is None:
            log.error('Must have GIT_DIR set in enviroment')
            sys.exit(1)

        if hook == 'post-update':
            log.info('Running hook %s', hook)
            post_update(cfg, git_dir)
            log.info('Done.')
        else:
            log.warning('Ignoring unknown hook: %r', hook)

########NEW FILE########
__FILENAME__ = serve
"""
Enforce git-shell to only serve allowed by access control policy.
directory. The client should refer to them without any extra directory
prefix. Repository names are forced to match ALLOW_RE.
"""

import logging

import sys, os, re

from gitosis import access
from gitosis import repository
from gitosis import gitweb
from gitosis import gitdaemon
from gitosis import app
from gitosis import util

log = logging.getLogger('gitosis.serve')

ALLOW_RE = re.compile("^'/*(?P<path>[a-zA-Z0-9][a-zA-Z0-9@._-]*(/[a-zA-Z0-9][a-zA-Z0-9@._-]*)*)'$")

COMMANDS_READONLY = [
    'git-upload-pack',
    'git upload-pack',
    ]

COMMANDS_WRITE = [
    'git-receive-pack',
    'git receive-pack',
    ]

class ServingError(Exception):
    """Serving error"""

    def __str__(self):
        return '%s' % self.__doc__

class CommandMayNotContainNewlineError(ServingError):
    """Command may not contain newline"""

class UnknownCommandError(ServingError):
    """Unknown command denied"""

class UnsafeArgumentsError(ServingError):
    """Arguments to command look dangerous"""

class AccessDenied(ServingError):
    """Access denied to repository"""

class WriteAccessDenied(AccessDenied):
    """Repository write access denied"""

class ReadAccessDenied(AccessDenied):
    """Repository read access denied"""

def serve(
    cfg,
    user,
    command,
    ):
    if '\n' in command:
        raise CommandMayNotContainNewlineError()

    try:
        verb, args = command.split(None, 1)
    except ValueError:
        # all known "git-foo" commands take one argument; improve
        # if/when needed
        raise UnknownCommandError()

    if verb == 'git':
        try:
            subverb, args = args.split(None, 1)
        except ValueError:
            # all known "git foo" commands take one argument; improve
            # if/when needed
            raise UnknownCommandError()
        verb = '%s %s' % (verb, subverb)

    if (verb not in COMMANDS_WRITE
        and verb not in COMMANDS_READONLY):
        raise UnknownCommandError()

    match = ALLOW_RE.match(args)
    if match is None:
        raise UnsafeArgumentsError()

    path = match.group('path')

    # write access is always sufficient
    newpath = access.haveAccess(
        config=cfg,
        user=user,
        mode='writable',
        path=path)

    if newpath is None:
        # didn't have write access; try once more with the popular
        # misspelling
        newpath = access.haveAccess(
            config=cfg,
            user=user,
            mode='writeable',
            path=path)
        if newpath is not None:
            log.warning(
                'Repository %r config has typo "writeable", '
                +'should be "writable"',
                path,
                )

    if newpath is None:
        # didn't have write access

        newpath = access.haveAccess(
            config=cfg,
            user=user,
            mode='readonly',
            path=path)

        if newpath is None:
            raise ReadAccessDenied()

        if verb in COMMANDS_WRITE:
            # didn't have write access and tried to write
            raise WriteAccessDenied()

    (topdir, relpath) = newpath
    assert not relpath.endswith('.git'), \
           'git extension should have been stripped: %r' % relpath
    repopath = '%s.git' % relpath
    fullpath = os.path.join(topdir, repopath)
    if not os.path.exists(fullpath):
        # it doesn't exist on the filesystem, but the configuration
        # refers to it, we're serving a write request, and the user is
        # authorized to do that: create the repository on the fly

        # create leading directories
        p = topdir
        for segment in repopath.split(os.sep)[:-1]:
            p = os.path.join(p, segment)
            util.mkdir(p, 0750)

        repository.init(path=fullpath)
        gitweb.set_descriptions(
            config=cfg,
            )
        generated = util.getGeneratedFilesDir(config=cfg)
        gitweb.generate_project_list(
            config=cfg,
            path=os.path.join(generated, 'projects.list'),
            )
        gitdaemon.set_export_ok(
            config=cfg,
            )

    # put the verb back together with the new path
    newcmd = "%(verb)s '%(path)s'" % dict(
        verb=verb,
        path=fullpath,
        )
    return newcmd

class Main(app.App):
    def create_parser(self):
        parser = super(Main, self).create_parser()
        parser.set_usage('%prog [OPTS] USER')
        parser.set_description(
            'Allow restricted git operations under DIR')
        return parser

    def handle_args(self, parser, cfg, options, args):
        try:
            (user,) = args
        except ValueError:
            parser.error('Missing argument USER.')

        main_log = logging.getLogger('gitosis.serve.main')
        os.umask(0022)

        cmd = os.environ.get('SSH_ORIGINAL_COMMAND', None)
        if cmd is None:
            main_log.error('Need SSH_ORIGINAL_COMMAND in environment.')
            sys.exit(1)

        main_log.debug('Got command %(cmd)r' % dict(
            cmd=cmd,
            ))

        os.chdir(os.path.expanduser('~'))

        try:
            newcmd = serve(
                cfg=cfg,
                user=user,
                command=cmd,
                )
        except ServingError, e:
            main_log.error('%s', e)
            sys.exit(1)

        main_log.debug('Serving %s', newcmd)
        os.execvp('git', ['git', 'shell', '-c', newcmd])
        main_log.error('Cannot execute git-shell.')
        sys.exit(1)

########NEW FILE########
__FILENAME__ = ssh
import os, errno, re
import logging

log = logging.getLogger('gitosis.ssh')

_ACCEPTABLE_USER_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_.-]*(@[a-zA-Z][a-zA-Z0-9.-]*)?$')

def isSafeUsername(user):
    match = _ACCEPTABLE_USER_RE.match(user)
    return (match is not None)

def readKeys(keydir):
    """
    Read SSH public keys from ``keydir/*.pub``
    """
    for filename in os.listdir(keydir):
        if filename.startswith('.'):
            continue
        basename, ext = os.path.splitext(filename)
        if ext != '.pub':
            continue

        if not isSafeUsername(basename):
            log.warn('Unsafe SSH username in keyfile: %r', filename)
            continue

        path = os.path.join(keydir, filename)
        f = file(path)
        for line in f:
            line = line.rstrip('\n')
            yield (basename, line)
        f.close()

COMMENT = '### autogenerated by gitosis, DO NOT EDIT'

def generateAuthorizedKeys(keys):
    TEMPLATE=('command="gitosis-serve %(user)s",no-port-forwarding,'
              +'no-X11-forwarding,no-agent-forwarding,no-pty %(key)s')

    yield COMMENT
    for (user, key) in keys:
        yield TEMPLATE % dict(user=user, key=key)

_COMMAND_RE = re.compile('^command="(/[^ "]+/)?gitosis-serve [^"]+",no-port-forw'
                         +'arding,no-X11-forwarding,no-agent-forwardi'
                         +'ng,no-pty .*')

def filterAuthorizedKeys(fp):
    """
    Read lines from ``fp``, filter out autogenerated ones.

    Note removes newlines.
    """

    for line in fp:
        line = line.rstrip('\n')
        if line == COMMENT:
            continue
        if _COMMAND_RE.match(line):
            continue
        yield line

def writeAuthorizedKeys(path, keydir):
    tmp = '%s.%d.tmp' % (path, os.getpid())
    try:
        in_ = file(path)
    except IOError, e:
        if e.errno == errno.ENOENT:
            in_ = None
        else:
            raise

    try:
        out = file(tmp, 'w')
        try:
            if in_ is not None:
                for line in filterAuthorizedKeys(in_):
                    print >>out, line

            keygen = readKeys(keydir)
            for line in generateAuthorizedKeys(keygen):
                print >>out, line

            os.fsync(out)
        finally:
            out.close()
    finally:
        if in_ is not None:
            in_.close()
    os.rename(tmp, path)

########NEW FILE########
__FILENAME__ = test_access
from nose.tools import eq_ as eq

import logging
from ConfigParser import RawConfigParser

from gitosis import access

def test_write_no_simple():
    cfg = RawConfigParser()
    eq(access.haveAccess(config=cfg, user='jdoe', mode='writable', path='foo/bar'),
       None)

def test_write_yes_simple():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'writable', 'foo/bar')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='writable', path='foo/bar'),
       ('repositories', 'foo/bar'))

def test_write_no_simple_wouldHaveReadonly():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'readonly', 'foo/bar')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='writable', path='foo/bar'),
       None)

def test_write_yes_map():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'map writable foo/bar', 'quux/thud')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='writable', path='foo/bar'),
       ('repositories', 'quux/thud'))

def test_write_no_map_wouldHaveReadonly():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'map readonly foo/bar', 'quux/thud')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='writable', path='foo/bar'),
       None)

def test_read_no_simple():
    cfg = RawConfigParser()
    eq(access.haveAccess(config=cfg, user='jdoe', mode='readonly', path='foo/bar'),
       None)

def test_read_yes_simple():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'readonly', 'foo/bar')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='readonly', path='foo/bar'),
       ('repositories', 'foo/bar'))

def test_read_yes_simple_wouldHaveWritable():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'writable', 'foo/bar')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='readonly', path='foo/bar'),
       None)

def test_read_yes_map():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'map readonly foo/bar', 'quux/thud')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='readonly', path='foo/bar'),
       ('repositories', 'quux/thud'))

def test_read_yes_map_wouldHaveWritable():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'map writable foo/bar', 'quux/thud')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='readonly', path='foo/bar'),
       None)

def test_read_yes_all():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', '@all')
    cfg.set('group fooers', 'readonly', 'foo/bar')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='readonly', path='foo/bar'),
       ('repositories', 'foo/bar'))

def test_base_global_absolute():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', '/a/leading/path')
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'map writable foo/bar', 'baz/quux/thud')
    eq(access.haveAccess(
        config=cfg, user='jdoe', mode='writable', path='foo/bar'),
       ('/a/leading/path', 'baz/quux/thud'))

def test_base_global_relative():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', 'some/relative/path')
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'map writable foo/bar', 'baz/quux/thud')
    eq(access.haveAccess(
        config=cfg, user='jdoe', mode='writable', path='foo/bar'),
       ('some/relative/path', 'baz/quux/thud'))

def test_base_global_relative_simple():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', 'some/relative/path')
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'readonly', 'foo xyzzy bar')
    eq(access.haveAccess(
        config=cfg, user='jdoe', mode='readonly', path='xyzzy'),
       ('some/relative/path', 'xyzzy'))

def test_base_global_unset():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'readonly', 'foo xyzzy bar')
    eq(access.haveAccess(
        config=cfg, user='jdoe', mode='readonly', path='xyzzy'),
       ('repositories', 'xyzzy'))

def test_base_local():
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'repositories', 'some/relative/path')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'map writable foo/bar', 'baz/quux/thud')
    eq(access.haveAccess(
        config=cfg, user='jdoe', mode='writable', path='foo/bar'),
       ('some/relative/path', 'baz/quux/thud'))

def test_dotgit():
    # a .git extension is always allowed to be added
    cfg = RawConfigParser()
    cfg.add_section('group fooers')
    cfg.set('group fooers', 'members', 'jdoe')
    cfg.set('group fooers', 'writable', 'foo/bar')
    eq(access.haveAccess(config=cfg, user='jdoe', mode='writable', path='foo/bar.git'),
       ('repositories', 'foo/bar'))

########NEW FILE########
__FILENAME__ = test_gitdaemon
from nose.tools import eq_ as eq

import os
from ConfigParser import RawConfigParser

from gitosis import gitdaemon
from gitosis.test.util import maketemp, writeFile

def exported(path):
    assert os.path.isdir(path)
    p = gitdaemon.export_ok_path(path)
    return os.path.exists(p)

def test_git_daemon_export_ok_repo_missing():
    # configured but not created yet; before first push
    tmp = maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'daemon', 'yes')
    gitdaemon.set_export_ok(config=cfg)
    assert not os.path.exists(os.path.join(tmp, 'foo'))
    assert not os.path.exists(os.path.join(tmp, 'foo.git'))

def test_git_daemon_export_ok_repo_missing_parent():
    # configured but not created yet; before first push
    tmp = maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo/bar')
    cfg.set('repo foo/bar', 'daemon', 'yes')
    gitdaemon.set_export_ok(config=cfg)
    assert not os.path.exists(os.path.join(tmp, 'foo'))

def test_git_daemon_export_ok_allowed():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'daemon', 'yes')
    gitdaemon.set_export_ok(config=cfg)
    eq(exported(path), True)

def test_git_daemon_export_ok_allowed_already():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    writeFile(gitdaemon.export_ok_path(path), '')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'daemon', 'yes')
    gitdaemon.set_export_ok(config=cfg)
    eq(exported(path), True)

def test_git_daemon_export_ok_denied():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    writeFile(gitdaemon.export_ok_path(path), '')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'daemon', 'no')
    gitdaemon.set_export_ok(config=cfg)
    eq(exported(path), False)

def test_git_daemon_export_ok_denied_already():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'daemon', 'no')
    gitdaemon.set_export_ok(config=cfg)
    eq(exported(path), False)

def test_git_daemon_export_ok_subdirs():
    tmp = maketemp()
    foo = os.path.join(tmp, 'foo')
    os.mkdir(foo)
    path = os.path.join(foo, 'bar.git')
    os.mkdir(path)
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo/bar')
    cfg.set('repo foo/bar', 'daemon', 'yes')
    gitdaemon.set_export_ok(config=cfg)
    eq(exported(path), True)

def test_git_daemon_export_ok_denied_default():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    writeFile(gitdaemon.export_ok_path(path), '')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    gitdaemon.set_export_ok(config=cfg)
    eq(exported(path), False)

def test_git_daemon_export_ok_denied_even_not_configured():
    # repositories not mentioned in config also get touched; this is
    # to avoid security trouble, otherwise we might expose (or
    # continue to expose) old repositories removed from config
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    os.mkdir(path)
    writeFile(gitdaemon.export_ok_path(path), '')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    gitdaemon.set_export_ok(config=cfg)
    eq(exported(path), False)

def test_git_daemon_export_ok_allowed_global():
    tmp = maketemp()

    for repo in [
        'foo.git',
        'quux.git',
        'thud.git',
        ]:
        path = os.path.join(tmp, repo)
        os.mkdir(path)

    # try to provoke an invalid allow
    writeFile(gitdaemon.export_ok_path(os.path.join(tmp, 'thud.git')), '')

    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.set('gitosis', 'daemon', 'yes')
    cfg.add_section('repo foo')
    cfg.add_section('repo quux')
    # same as default, no effect
    cfg.set('repo quux', 'daemon', 'yes')
    cfg.add_section('repo thud')
    # this is still hidden
    cfg.set('repo thud', 'daemon', 'no')
    gitdaemon.set_export_ok(config=cfg)
    eq(exported(os.path.join(tmp, 'foo.git')), True)
    eq(exported(os.path.join(tmp, 'quux.git')), True)
    eq(exported(os.path.join(tmp, 'thud.git')), False)

########NEW FILE########
__FILENAME__ = test_gitweb
from nose.tools import eq_ as eq

import os
from ConfigParser import RawConfigParser
from cStringIO import StringIO

from gitosis import gitweb
from gitosis.test.util import mkdir, maketemp, readFile, writeFile

def test_projectsList_empty():
    cfg = RawConfigParser()
    got = StringIO()
    gitweb.generate_project_list_fp(
        config=cfg,
        fp=got)
    eq(got.getvalue(), '''\
''')

def test_projectsList_repoDenied():
    cfg = RawConfigParser()
    cfg.add_section('repo foo/bar')
    got = StringIO()
    gitweb.generate_project_list_fp(
        config=cfg,
        fp=got)
    eq(got.getvalue(), '''\
''')

def test_projectsList_noOwner():
    cfg = RawConfigParser()
    cfg.add_section('repo foo/bar')
    cfg.set('repo foo/bar', 'gitweb', 'yes')
    got = StringIO()
    gitweb.generate_project_list_fp(
        config=cfg,
        fp=got)
    eq(got.getvalue(), '''\
foo%2Fbar
''')

def test_projectsList_haveOwner():
    cfg = RawConfigParser()
    cfg.add_section('repo foo/bar')
    cfg.set('repo foo/bar', 'gitweb', 'yes')
    cfg.set('repo foo/bar', 'owner', 'John Doe')
    got = StringIO()
    gitweb.generate_project_list_fp(
        config=cfg,
        fp=got)
    eq(got.getvalue(), '''\
foo%2Fbar John+Doe
''')

def test_projectsList_multiple():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.add_section('repo foo/bar')
    cfg.set('repo foo/bar', 'owner', 'John Doe')
    cfg.set('repo foo/bar', 'gitweb', 'yes')
    cfg.add_section('repo quux')
    cfg.set('repo quux', 'gitweb', 'yes')
    got = StringIO()
    gitweb.generate_project_list_fp(
        config=cfg,
        fp=got)
    eq(got.getvalue(), '''\
quux
foo%2Fbar John+Doe
''')

def test_projectsList_multiple_globalGitwebYes():
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'gitweb', 'yes')
    cfg.add_section('repo foo/bar')
    cfg.set('repo foo/bar', 'owner', 'John Doe')
    cfg.add_section('repo quux')
    # same as default, no effect
    cfg.set('repo quux', 'gitweb', 'yes')
    cfg.add_section('repo thud')
    # this is still hidden
    cfg.set('repo thud', 'gitweb', 'no')
    got = StringIO()
    gitweb.generate_project_list_fp(
        config=cfg,
        fp=got)
    eq(got.getvalue(), '''\
quux
foo%2Fbar John+Doe
''')

def test_projectsList_reallyEndsWithGit():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    mkdir(path)
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'gitweb', 'yes')
    got = StringIO()
    gitweb.generate_project_list_fp(
        config=cfg,
        fp=got)
    eq(got.getvalue(), '''\
foo.git
''')

def test_projectsList_path():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    mkdir(path)
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'gitweb', 'yes')
    projects_list = os.path.join(tmp, 'projects.list')
    gitweb.generate_project_list(
        config=cfg,
        path=projects_list)
    got = readFile(projects_list)
    eq(got, '''\
foo.git
''')

def test_description_none():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    mkdir(path)
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'description', 'foodesc')
    gitweb.set_descriptions(
        config=cfg,
        )
    got = readFile(os.path.join(path, 'description'))
    eq(got, 'foodesc\n')

def test_description_repo_missing():
    # configured but not created yet; before first push
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'description', 'foodesc')
    gitweb.set_descriptions(
        config=cfg,
        )
    assert not os.path.exists(os.path.join(tmp, 'foo'))
    assert not os.path.exists(os.path.join(tmp, 'foo.git'))

def test_description_repo_missing_parent():
    # configured but not created yet; before first push
    tmp = maketemp()
    path = os.path.join(tmp, 'foo/bar.git')
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'description', 'foodesc')
    gitweb.set_descriptions(
        config=cfg,
        )
    assert not os.path.exists(os.path.join(tmp, 'foo'))

def test_description_default():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    mkdir(path)
    writeFile(
        os.path.join(path, 'description'),
        'Unnamed repository; edit this file to name it for gitweb.\n',
        )
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'description', 'foodesc')
    gitweb.set_descriptions(
        config=cfg,
        )
    got = readFile(os.path.join(path, 'description'))
    eq(got, 'foodesc\n')

def test_description_not_set():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    mkdir(path)
    writeFile(
        os.path.join(path, 'description'),
        'i was here first\n',
        )
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    gitweb.set_descriptions(
        config=cfg,
        )
    got = readFile(os.path.join(path, 'description'))
    eq(got, 'i was here first\n')

def test_description_again():
    tmp = maketemp()
    path = os.path.join(tmp, 'foo.git')
    mkdir(path)
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'description', 'foodesc')
    gitweb.set_descriptions(
        config=cfg,
        )
    gitweb.set_descriptions(
        config=cfg,
        )
    got = readFile(os.path.join(path, 'description'))
    eq(got, 'foodesc\n')

########NEW FILE########
__FILENAME__ = test_group
from nose.tools import eq_ as eq, assert_raises

from ConfigParser import RawConfigParser

from gitosis import group

def test_no_emptyConfig():
    cfg = RawConfigParser()
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_no_emptyGroup():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_no_notListed():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_simple():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_leading():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'jdoe wsmith')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_trailing():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_middle():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith jdoe danny')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_one():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith @smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', 'danny jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_one_ordering():
    cfg = RawConfigParser()
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', 'danny jdoe')
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith @smackers')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_three():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', 'wsmith @smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', 'danny @snackers')
    cfg.add_section('group snackers')
    cfg.set('group snackers', 'members', '@whackers foo')
    cfg.add_section('group whackers')
    cfg.set('group whackers', 'members', 'jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'whackers')
    eq(gen.next(), 'snackers')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_junk():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', '@notexist @smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', 'jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_yes_recurse_loop():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', '@smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', '@hackers jdoe')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'smackers')
    eq(gen.next(), 'hackers')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

def test_no_recurse_loop():
    cfg = RawConfigParser()
    cfg.add_section('group hackers')
    cfg.set('group hackers', 'members', '@smackers')
    cfg.add_section('group smackers')
    cfg.set('group smackers', 'members', '@hackers')
    gen = group.getMembership(config=cfg, user='jdoe')
    eq(gen.next(), 'all')
    assert_raises(StopIteration, gen.next)

########NEW FILE########
__FILENAME__ = test_init
from nose.tools import eq_ as eq
from gitosis.test.util import assert_raises, maketemp

import os
from ConfigParser import RawConfigParser

from gitosis import init
from gitosis import repository

from gitosis.test import util

def test_ssh_extract_user_simple():
    got = init.ssh_extract_user(
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@fakehost')
    eq(got, 'fakeuser@fakehost')

def test_ssh_extract_user_domain():
    got = init.ssh_extract_user(
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@fakehost.example.com')
    eq(got, 'fakeuser@fakehost.example.com')

def test_ssh_extract_user_domain_dashes():
    got = init.ssh_extract_user(
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@ridiculously-long.example.com')
    eq(got, 'fakeuser@ridiculously-long.example.com')

def test_ssh_extract_user_underscore():
    got = init.ssh_extract_user(
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fake_user@example.com')
    eq(got, 'fake_user@example.com')

def test_ssh_extract_user_dot():
    got = init.ssh_extract_user(
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fake.u.ser@example.com')
    eq(got, 'fake.u.ser@example.com')

def test_ssh_extract_user_dash():
    got = init.ssh_extract_user(
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fake.u-ser@example.com')
    eq(got, 'fake.u-ser@example.com')

def test_ssh_extract_user_no_at():
    got = init.ssh_extract_user(
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser')
    eq(got, 'fakeuser')

def test_ssh_extract_user_caps():
    got = init.ssh_extract_user(
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= Fake.User@Domain.Example.Com')
    eq(got, 'Fake.User@Domain.Example.Com')

def test_ssh_extract_user_bad():
    e = assert_raises(
        init.InsecureSSHKeyUsername,
        init.ssh_extract_user,
        'ssh-somealgo AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= ER3%#@e%')
    eq(str(e), "Username contains not allowed characters: 'ER3%#@e%'")

def test_init_admin_repository():
    tmp = maketemp()
    admin_repository = os.path.join(tmp, 'admin.git')
    pubkey = (
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@fakehost')
    user = 'jdoe'
    init.init_admin_repository(
        git_dir=admin_repository,
        pubkey=pubkey,
        user=user,
        )
    eq(os.listdir(tmp), ['admin.git'])
    hook = os.path.join(
        tmp,
        'admin.git',
        'hooks',
        'post-update',
        )
    util.check_mode(hook, 0755, is_file=True)
    got = util.readFile(hook).splitlines()
    assert 'gitosis-run-hook post-update' in got
    export_dir = os.path.join(tmp, 'export')
    repository.export(git_dir=admin_repository,
                      path=export_dir)
    eq(sorted(os.listdir(export_dir)),
       sorted(['gitosis.conf', 'keydir']))
    eq(os.listdir(os.path.join(export_dir, 'keydir')),
       ['jdoe.pub'])
    got = util.readFile(
        os.path.join(export_dir, 'keydir', 'jdoe.pub'))
    eq(got, pubkey)
    # the only thing guaranteed of initial config file ordering is
    # that [gitosis] is first
    got = util.readFile(os.path.join(export_dir, 'gitosis.conf'))
    got = got.splitlines()[0]
    eq(got, '[gitosis]')
    cfg = RawConfigParser()
    cfg.read(os.path.join(export_dir, 'gitosis.conf'))
    eq(sorted(cfg.sections()),
       sorted([
        'gitosis',
        'group gitosis-admin',
        ]))
    eq(cfg.items('gitosis'), [])
    eq(sorted(cfg.items('group gitosis-admin')),
       sorted([
        ('writable', 'gitosis-admin'),
        ('members', 'jdoe'),
        ]))

########NEW FILE########
__FILENAME__ = test_repository
from nose.tools import eq_ as eq

import os
import subprocess
import random

from gitosis import repository

from gitosis.test.util import (
    mkdir,
    maketemp,
    readFile,
    writeFile,
    check_mode,
    assert_raises,
    )

def check_bare(path):
    # we want it to be a bare repository
    assert not os.path.exists(os.path.join(path, '.git'))

def test_init_simple():
    tmp = maketemp()
    path = os.path.join(tmp, 'repo.git')
    repository.init(path)
    check_mode(path, 0750, is_dir=True)
    check_bare(path)

def test_init_exist_dir():
    tmp = maketemp()
    path = os.path.join(tmp, 'repo.git')
    mkdir(path, 0710)
    check_mode(path, 0710, is_dir=True)
    repository.init(path)
    # my weird access mode is preserved
    check_mode(path, 0710, is_dir=True)
    check_bare(path)

def test_init_exist_git():
    tmp = maketemp()
    path = os.path.join(tmp, 'repo.git')
    repository.init(path)
    repository.init(path)
    check_mode(path, 0750, is_dir=True)
    check_bare(path)

def test_init_templates():
    tmp = maketemp()
    path = os.path.join(tmp, 'repo.git')
    templatedir = os.path.join(
        os.path.dirname(__file__),
        'mocktemplates',
        )
    repository.init(path, template=templatedir)
    repository.init(path)
    got = readFile(os.path.join(path, 'no-confusion'))
    eq(got, 'i should show up\n')
    check_mode(
        os.path.join(path, 'hooks', 'post-update'),
        0755,
        is_file=True,
        )
    got = readFile(os.path.join(path, 'hooks', 'post-update'))
    eq(got, '#!/bin/sh\n# i can override standard templates\n')
    # standard templates are there, too
    assert (
        # compatibility with git <1.6.0
        os.path.isfile(os.path.join(path, 'hooks', 'pre-rebase'))
        # for git >=1.6.0
        or os.path.isfile(os.path.join(path, 'hooks', 'pre-rebase.sample'))
        )

def test_init_environment():
    tmp = maketemp()
    path = os.path.join(tmp, 'repo.git')
    mockbindir = os.path.join(tmp, 'mockbin')
    os.mkdir(mockbindir)
    mockgit = os.path.join(mockbindir, 'git')
    writeFile(mockgit, '''\
#!/bin/sh
set -e
# git wrapper for gitosis unit tests
printf '%s' "$GITOSIS_UNITTEST_COOKIE" >"$(dirname "$0")/../cookie"

# strip away my special PATH insert so system git will be found
PATH="${PATH#*:}"

exec git "$@"
''')
    os.chmod(mockgit, 0755)
    magic_cookie = '%d' % random.randint(1, 100000)
    good_path = os.environ['PATH']
    try:
        os.environ['PATH'] = '%s:%s' % (mockbindir, good_path)
        os.environ['GITOSIS_UNITTEST_COOKIE'] = magic_cookie
        repository.init(path)
    finally:
        os.environ['PATH'] = good_path
        os.environ.pop('GITOSIS_UNITTEST_COOKIE', None)
    eq(
        sorted(os.listdir(tmp)),
        sorted([
                'mockbin',
                'cookie',
                'repo.git',
                ]),
        )
    got = readFile(os.path.join(tmp, 'cookie'))
    eq(got, magic_cookie)

def test_fast_import_environment():
    tmp = maketemp()
    path = os.path.join(tmp, 'repo.git')
    repository.init(path=path)
    mockbindir = os.path.join(tmp, 'mockbin')
    os.mkdir(mockbindir)
    mockgit = os.path.join(mockbindir, 'git')
    writeFile(mockgit, '''\
#!/bin/sh
set -e
# git wrapper for gitosis unit tests
printf '%s' "$GITOSIS_UNITTEST_COOKIE" >"$(dirname "$0")/../cookie"

# strip away my special PATH insert so system git will be found
PATH="${PATH#*:}"

exec git "$@"
''')
    os.chmod(mockgit, 0755)
    magic_cookie = '%d' % random.randint(1, 100000)
    good_path = os.environ['PATH']
    try:
        os.environ['PATH'] = '%s:%s' % (mockbindir, good_path)
        os.environ['GITOSIS_UNITTEST_COOKIE'] = magic_cookie
        repository.fast_import(
            git_dir=path,
            commit_msg='foo initial bar',
            committer='Mr. Unit Test <unit.test@example.com>',
            files=[
                ('foo', 'bar\n'),
                ],
            )
    finally:
        os.environ['PATH'] = good_path
        os.environ.pop('GITOSIS_UNITTEST_COOKIE', None)
    eq(
        sorted(os.listdir(tmp)),
        sorted([
                'mockbin',
                'cookie',
                'repo.git',
                ]),
        )
    got = readFile(os.path.join(tmp, 'cookie'))
    eq(got, magic_cookie)

def test_export_simple():
    tmp = maketemp()
    git_dir = os.path.join(tmp, 'repo.git')
    repository.init(path=git_dir)
    repository.fast_import(
        git_dir=git_dir,
        committer='John Doe <jdoe@example.com>',
        commit_msg="""\
Reverse the polarity of the neutron flow.

Frobitz the quux and eschew obfuscation.
""",
        files=[
            ('foo', 'content'),
            ('bar/quux', 'another'),
            ],
        )
    export = os.path.join(tmp, 'export')
    repository.export(git_dir=git_dir, path=export)
    eq(sorted(os.listdir(export)),
       sorted(['foo', 'bar']))
    eq(readFile(os.path.join(export, 'foo')), 'content')
    eq(os.listdir(os.path.join(export, 'bar')), ['quux'])
    eq(readFile(os.path.join(export, 'bar', 'quux')), 'another')
    child = subprocess.Popen(
        args=[
            'git',
            '--git-dir=%s' % git_dir,
            'cat-file',
            'commit',
            'HEAD',
            ],
        cwd=git_dir,
        stdout=subprocess.PIPE,
        close_fds=True,
        )
    got = child.stdout.read().splitlines()
    returncode = child.wait()
    if returncode != 0:
        raise RuntimeError('git exit status %d' % returncode)
    eq(got[0].split(None, 1)[0], 'tree')
    eq(got[1].rsplit(None, 2)[0],
       'author John Doe <jdoe@example.com>')
    eq(got[2].rsplit(None, 2)[0],
       'committer John Doe <jdoe@example.com>')
    eq(got[3], '')
    eq(got[4], 'Reverse the polarity of the neutron flow.')
    eq(got[5], '')
    eq(got[6], 'Frobitz the quux and eschew obfuscation.')
    eq(got[7:], [])

def test_export_environment():
    tmp = maketemp()
    git_dir = os.path.join(tmp, 'repo.git')
    mockbindir = os.path.join(tmp, 'mockbin')
    os.mkdir(mockbindir)
    mockgit = os.path.join(mockbindir, 'git')
    writeFile(mockgit, '''\
#!/bin/sh
set -e
# git wrapper for gitosis unit tests
printf '%s\n' "$GITOSIS_UNITTEST_COOKIE" >>"$(dirname "$0")/../cookie"

# strip away my special PATH insert so system git will be found
PATH="${PATH#*:}"

exec git "$@"
''')
    os.chmod(mockgit, 0755)
    repository.init(path=git_dir)
    repository.fast_import(
        git_dir=git_dir,
        committer='John Doe <jdoe@example.com>',
        commit_msg="""\
Reverse the polarity of the neutron flow.

Frobitz the quux and eschew obfuscation.
""",
        files=[
            ('foo', 'content'),
            ('bar/quux', 'another'),
            ],
        )
    export = os.path.join(tmp, 'export')
    magic_cookie = '%d' % random.randint(1, 100000)
    good_path = os.environ['PATH']
    try:
        os.environ['PATH'] = '%s:%s' % (mockbindir, good_path)
        os.environ['GITOSIS_UNITTEST_COOKIE'] = magic_cookie
        repository.export(git_dir=git_dir, path=export)
    finally:
        os.environ['PATH'] = good_path
        os.environ.pop('GITOSIS_UNITTEST_COOKIE', None)
    got = readFile(os.path.join(tmp, 'cookie'))
    eq(
        got,
        # export runs git twice
        '%s\n%s\n' % (magic_cookie, magic_cookie),
        )

def test_has_initial_commit_fail_notAGitDir():
    tmp = maketemp()
    e = assert_raises(
        repository.GitRevParseError,
        repository.has_initial_commit,
        git_dir=tmp)
    eq(str(e), 'rev-parse failed: exit status 128')

def test_has_initial_commit_no():
    tmp = maketemp()
    repository.init(path=tmp)
    got = repository.has_initial_commit(git_dir=tmp)
    eq(got, False)

def test_has_initial_commit_yes():
    tmp = maketemp()
    repository.init(path=tmp)
    repository.fast_import(
        git_dir=tmp,
        commit_msg='fakecommit',
        committer='John Doe <jdoe@example.com>',
        files=[],
        )
    got = repository.has_initial_commit(git_dir=tmp)
    eq(got, True)

def test_has_initial_commit_environment():
    tmp = maketemp()
    git_dir = os.path.join(tmp, 'repo.git')
    mockbindir = os.path.join(tmp, 'mockbin')
    os.mkdir(mockbindir)
    mockgit = os.path.join(mockbindir, 'git')
    writeFile(mockgit, '''\
#!/bin/sh
set -e
# git wrapper for gitosis unit tests
printf '%s' "$GITOSIS_UNITTEST_COOKIE" >"$(dirname "$0")/../cookie"

# strip away my special PATH insert so system git will be found
PATH="${PATH#*:}"

exec git "$@"
''')
    os.chmod(mockgit, 0755)
    repository.init(path=tmp)
    repository.fast_import(
        git_dir=tmp,
        commit_msg='fakecommit',
        committer='John Doe <jdoe@example.com>',
        files=[],
        )
    magic_cookie = '%d' % random.randint(1, 100000)
    good_path = os.environ['PATH']
    try:
        os.environ['PATH'] = '%s:%s' % (mockbindir, good_path)
        os.environ['GITOSIS_UNITTEST_COOKIE'] = magic_cookie
        got = repository.has_initial_commit(git_dir=tmp)
    finally:
        os.environ['PATH'] = good_path
        os.environ.pop('GITOSIS_UNITTEST_COOKIE', None)
    eq(got, True)
    got = readFile(os.path.join(tmp, 'cookie'))
    eq(got, magic_cookie)

def test_fast_import_parent():
    tmp = maketemp()
    path = os.path.join(tmp, 'repo.git')
    repository.init(path=path)
    repository.fast_import(
        git_dir=path,
        commit_msg='foo initial bar',
        committer='Mr. Unit Test <unit.test@example.com>',
        files=[
            ('foo', 'bar\n'),
            ],
        )
    repository.fast_import(
        git_dir=path,
        commit_msg='another',
        committer='Sam One Else <sam@example.com>',
        parent='refs/heads/master^0',
        files=[
            ('quux', 'thud\n'),
            ],
        )
    export = os.path.join(tmp, 'export')
    repository.export(
        git_dir=path,
        path=export,
        )
    eq(sorted(os.listdir(export)),
       sorted(['foo', 'quux']))

########NEW FILE########
__FILENAME__ = test_run_hook
from nose.tools import eq_ as eq

import os
from ConfigParser import RawConfigParser
from cStringIO import StringIO

from gitosis import init, repository, run_hook
from gitosis.test.util import maketemp, readFile

def test_post_update_simple():
    tmp = maketemp()
    repos = os.path.join(tmp, 'repositories')
    os.mkdir(repos)
    admin_repository = os.path.join(repos, 'gitosis-admin.git')
    pubkey = (
        'ssh-somealgo '
        +'0123456789ABCDEFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        +'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= fakeuser@fakehost')
    user = 'theadmin'
    init.init_admin_repository(
        git_dir=admin_repository,
        pubkey=pubkey,
        user=user,
        )
    repository.init(path=os.path.join(repos, 'forweb.git'))
    repository.init(path=os.path.join(repos, 'fordaemon.git'))
    repository.fast_import(
        git_dir=admin_repository,
        committer='John Doe <jdoe@example.com>',
        commit_msg="""\
stuff
""",
        parent='refs/heads/master^0',
        files=[
            ('gitosis.conf', """\
[gitosis]

[group gitosis-admin]
members = theadmin
writable = gitosis-admin

[repo fordaemon]
daemon = yes

[repo forweb]
gitweb = yes
owner = John Doe
description = blah blah
"""),
            ('keydir/jdoe.pub',
             'ssh-somealgo '
             +'0123456789ABCDEFBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB'
             +'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB'
             +'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB'
             +'BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB= jdoe@host.example.com'),
            ],
        )
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', repos)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    ssh = os.path.join(tmp, 'ssh')
    os.mkdir(ssh)
    cfg.set(
        'gitosis',
        'ssh-authorized-keys-path',
        os.path.join(ssh, 'authorized_keys'),
        )
    run_hook.post_update(
        cfg=cfg,
        git_dir=admin_repository,
        )
    got = readFile(os.path.join(repos, 'forweb.git', 'description'))
    eq(got, 'blah blah\n')
    got = os.listdir(generated)
    eq(got, ['projects.list'])
    got = readFile(os.path.join(generated, 'projects.list'))
    eq(
        got,
        """\
forweb.git John+Doe
""",
        )
    got = os.listdir(os.path.join(repos, 'fordaemon.git'))
    assert 'git-daemon-export-ok' in got, \
        "git-daemon-export-ok not created: %r" % got
    got = os.listdir(ssh)
    eq(got, ['authorized_keys'])
    got = readFile(os.path.join(ssh, 'authorized_keys')).splitlines(True)
    assert 'command="gitosis-serve jdoe",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-somealgo 0123456789ABCDEFBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB= jdoe@host.example.com\n' in got, \
        "SSH authorized_keys line for jdoe not found: %r" % got

########NEW FILE########
__FILENAME__ = test_serve
from nose.tools import eq_ as eq
from gitosis.test.util import assert_raises

import logging
import os
from cStringIO import StringIO
from ConfigParser import RawConfigParser

from gitosis import serve
from gitosis import repository

from gitosis.test import util

def test_bad_newLine():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.CommandMayNotContainNewlineError,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command='ev\nil',
        )
    eq(str(e), 'Command may not contain newline')
    assert isinstance(e, serve.ServingError)

def test_bad_dash_noargs():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.UnknownCommandError,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command='git-upload-pack',
        )
    eq(str(e), 'Unknown command denied')
    assert isinstance(e, serve.ServingError)

def test_bad_space_noargs():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.UnknownCommandError,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command='git upload-pack',
        )
    eq(str(e), 'Unknown command denied')
    assert isinstance(e, serve.ServingError)

def test_bad_command():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.UnknownCommandError,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="evil 'foo'",
        )
    eq(str(e), 'Unknown command denied')
    assert isinstance(e, serve.ServingError)

def test_bad_unsafeArguments_notQuoted():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.UnsafeArgumentsError,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git-upload-pack foo",
        )
    eq(str(e), 'Arguments to command look dangerous')
    assert isinstance(e, serve.ServingError)

def test_bad_unsafeArguments_badCharacters():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.UnsafeArgumentsError,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git-upload-pack 'ev!l'",
        )
    eq(str(e), 'Arguments to command look dangerous')
    assert isinstance(e, serve.ServingError)

def test_bad_unsafeArguments_dotdot():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.UnsafeArgumentsError,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git-upload-pack 'something/../evil'",
        )
    eq(str(e), 'Arguments to command look dangerous')
    assert isinstance(e, serve.ServingError)

def test_bad_forbiddenCommand_read_dash():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.ReadAccessDenied,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git-upload-pack 'foo'",
        )
    eq(str(e), 'Repository read access denied')
    assert isinstance(e, serve.AccessDenied)
    assert isinstance(e, serve.ServingError)

def test_bad_forbiddenCommand_read_space():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.ReadAccessDenied,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git upload-pack 'foo'",
        )
    eq(str(e), 'Repository read access denied')
    assert isinstance(e, serve.AccessDenied)
    assert isinstance(e, serve.ServingError)

def test_bad_forbiddenCommand_write_noAccess_dash():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.ReadAccessDenied,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo'",
        )
    # error message talks about read in an effort to make it more
    # obvious that jdoe doesn't have *even* read access
    eq(str(e), 'Repository read access denied')
    assert isinstance(e, serve.AccessDenied)
    assert isinstance(e, serve.ServingError)

def test_bad_forbiddenCommand_write_noAccess_space():
    cfg = RawConfigParser()
    e = assert_raises(
        serve.ReadAccessDenied,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git receive-pack 'foo'",
        )
    # error message talks about read in an effort to make it more
    # obvious that jdoe doesn't have *even* read access
    eq(str(e), 'Repository read access denied')
    assert isinstance(e, serve.AccessDenied)
    assert isinstance(e, serve.ServingError)

def test_bad_forbiddenCommand_write_readAccess_dash():
    cfg = RawConfigParser()
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'readonly', 'foo')
    e = assert_raises(
        serve.WriteAccessDenied,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo'",
        )
    eq(str(e), 'Repository write access denied')
    assert isinstance(e, serve.AccessDenied)
    assert isinstance(e, serve.ServingError)

def test_bad_forbiddenCommand_write_readAccess_space():
    cfg = RawConfigParser()
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'readonly', 'foo')
    e = assert_raises(
        serve.WriteAccessDenied,
        serve.serve,
        cfg=cfg,
        user='jdoe',
        command="git receive-pack 'foo'",
        )
    eq(str(e), 'Repository write access denied')
    assert isinstance(e, serve.AccessDenied)
    assert isinstance(e, serve.ServingError)

def test_simple_read_dash():
    tmp = util.maketemp()
    repository.init(os.path.join(tmp, 'foo.git'))
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'readonly', 'foo')
    got = serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-upload-pack 'foo'",
        )
    eq(got, "git-upload-pack '%s/foo.git'" % tmp)

def test_simple_read_space():
    tmp = util.maketemp()
    repository.init(os.path.join(tmp, 'foo.git'))
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'readonly', 'foo')
    got = serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git upload-pack 'foo'",
        )
    eq(got, "git upload-pack '%s/foo.git'" % tmp)

def test_read_inits_if_needed():
    # a clone of a non-existent repository (but where config
    # authorizes you to do that) will create the repository on the fly
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'readonly', 'foo')
    got = serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-upload-pack 'foo'",
        )
    eq(got, "git-upload-pack '%s/foo.git'" % repositories)
    eq(os.listdir(repositories), ['foo.git'])
    assert os.path.isfile(os.path.join(repositories, 'foo.git', 'HEAD'))

def test_simple_write_dash():
    tmp = util.maketemp()
    repository.init(os.path.join(tmp, 'foo.git'))
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    got = serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo'",
        )
    eq(got, "git-receive-pack '%s/foo.git'" % tmp)

def test_simple_write_space():
    tmp = util.maketemp()
    repository.init(os.path.join(tmp, 'foo.git'))
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    got = serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git receive-pack 'foo'",
        )
    eq(got, "git receive-pack '%s/foo.git'" % tmp)

def test_push_inits_if_needed():
    # a push to a non-existent repository (but where config authorizes
    # you to do that) will create the repository on the fly
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo'",
        )
    eq(os.listdir(repositories), ['foo.git'])
    assert os.path.isfile(os.path.join(repositories, 'foo.git', 'HEAD'))

def test_push_inits_if_needed_haveExtension():
    # a push to a non-existent repository (but where config authorizes
    # you to do that) will create the repository on the fly
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo.git'",
        )
    eq(os.listdir(repositories), ['foo.git'])
    assert os.path.isfile(os.path.join(repositories, 'foo.git', 'HEAD'))

def test_push_inits_subdir_parent_missing():
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo/bar')
    serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo/bar.git'",
        )
    eq(os.listdir(repositories), ['foo'])
    foo = os.path.join(repositories, 'foo')
    util.check_mode(foo, 0750, is_dir=True)
    eq(os.listdir(foo), ['bar.git'])
    assert os.path.isfile(os.path.join(repositories, 'foo', 'bar.git', 'HEAD'))

def test_push_inits_subdir_parent_exists():
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    foo = os.path.join(repositories, 'foo')
    # silly mode on purpose; not to be touched
    os.mkdir(foo, 0751)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo/bar')
    serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo/bar.git'",
        )
    eq(os.listdir(repositories), ['foo'])
    util.check_mode(foo, 0751, is_dir=True)
    eq(os.listdir(foo), ['bar.git'])
    assert os.path.isfile(os.path.join(repositories, 'foo', 'bar.git', 'HEAD'))

def test_push_inits_if_needed_existsWithExtension():
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    os.mkdir(os.path.join(repositories, 'foo.git'))
    serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo'",
        )
    eq(os.listdir(repositories), ['foo.git'])
    # it should *not* have HEAD here as we just mkdirred it and didn't
    # create it properly, and the mock repo didn't have anything in
    # it.. having HEAD implies serve ran git init, which is supposed
    # to be unnecessary here
    eq(os.listdir(os.path.join(repositories, 'foo.git')), [])

def test_push_inits_no_stdout_spam():
    # git init has a tendency to spew to stdout, and that confuses
    # e.g. a git push
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    old_stdout = os.dup(1)
    try:
        new_stdout = os.tmpfile()
        os.dup2(new_stdout.fileno(), 1)
        serve.serve(
            cfg=cfg,
            user='jdoe',
            command="git-receive-pack 'foo'",
            )
    finally:
        os.dup2(old_stdout, 1)
        os.close(old_stdout)
    new_stdout.seek(0)
    got = new_stdout.read()
    new_stdout.close()
    eq(got, '')
    eq(os.listdir(repositories), ['foo.git'])
    assert os.path.isfile(os.path.join(repositories, 'foo.git', 'HEAD'))

def test_push_inits_sets_description():
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'description', 'foodesc')
    serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo'",
        )
    eq(os.listdir(repositories), ['foo.git'])
    path = os.path.join(repositories, 'foo.git', 'description')
    assert os.path.exists(path)
    got = util.readFile(path)
    eq(got, 'foodesc\n')

def test_push_inits_updates_projects_list():
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'gitweb', 'yes')
    os.mkdir(os.path.join(repositories, 'gitosis-admin.git'))
    serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo'",
        )
    eq(
        sorted(os.listdir(repositories)),
        sorted(['foo.git', 'gitosis-admin.git']),
        )
    path = os.path.join(generated, 'projects.list')
    assert os.path.exists(path)
    got = util.readFile(path)
    eq(got, 'foo.git\n')

def test_push_inits_sets_export_ok():
    tmp = util.maketemp()
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    repositories = os.path.join(tmp, 'repositories')
    os.mkdir(repositories)
    cfg.set('gitosis', 'repositories', repositories)
    generated = os.path.join(tmp, 'generated')
    os.mkdir(generated)
    cfg.set('gitosis', 'generate-files-in', generated)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writable', 'foo')
    cfg.add_section('repo foo')
    cfg.set('repo foo', 'daemon', 'yes')
    serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-receive-pack 'foo'",
        )
    eq(os.listdir(repositories), ['foo.git'])
    path = os.path.join(repositories, 'foo.git', 'git-daemon-export-ok')
    assert os.path.exists(path)

def test_absolute():
    # as the only convenient way to use non-standard SSH ports with
    # git is via the ssh://user@host:port/path syntax, and that syntax
    # forces absolute urls, just force convert absolute paths to
    # relative paths; you'll never really want absolute paths via
    # gitosis, anyway.
    tmp = util.maketemp()
    repository.init(os.path.join(tmp, 'foo.git'))
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'readonly', 'foo')
    got = serve.serve(
        cfg=cfg,
        user='jdoe',
        command="git-upload-pack '/foo'",
        )
    eq(got, "git-upload-pack '%s/foo.git'" % tmp)

def test_typo_writeable():
    tmp = util.maketemp()
    repository.init(os.path.join(tmp, 'foo.git'))
    cfg = RawConfigParser()
    cfg.add_section('gitosis')
    cfg.set('gitosis', 'repositories', tmp)
    cfg.add_section('group foo')
    cfg.set('group foo', 'members', 'jdoe')
    cfg.set('group foo', 'writeable', 'foo')
    log = logging.getLogger('gitosis.serve')
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    log.addHandler(handler)
    try:
        got = serve.serve(
            cfg=cfg,
            user='jdoe',
            command="git-receive-pack 'foo'",
            )
    finally:
        log.removeHandler(handler)
    eq(got, "git-receive-pack '%s/foo.git'" % tmp)
    handler.flush()
    eq(
        buf.getvalue(),
        "Repository 'foo' config has typo \"writeable\", shou"
        +"ld be \"writable\"\n",
        )

########NEW FILE########
__FILENAME__ = test_ssh
from nose.tools import eq_ as eq, assert_raises

import os
from cStringIO import StringIO

from gitosis import ssh
from gitosis.test.util import mkdir, maketemp, writeFile, readFile

def _key(s):
    return ''.join(s.split('\n')).strip()

KEY_1 = _key("""
ssh-rsa +v5XLsUrLsHOKy7Stob1lHZM17YCCNXplcKfbpIztS2PujyixOaBev1ku6H6ny
gUXfuYVzY+PmfTLviSwD3UETxEkR/jlBURACDQARJdUxpgt9XG2Lbs8bhOjonAPapxrH0o
9O8R0Y6Pm1Vh+H2U0B4UBhPgEframpeJYedijBxBV5aq3yUvHkXpcjM/P0gsKqr036k= j
unk@gunk
""")

KEY_2 = _key("""
ssh-rsa 4BX2TxZoD3Og2zNjHwaMhVEa5/NLnPcw+Z02TDR0IGJrrqXk7YlfR3oz+Wb/Eb
Ctli20SoWY0Ur8kBEF/xR4hRslZ2U8t0PAJhr8cq5mifhok/gAdckmSzjD67QJ68uZbga8
ZwIAo7y/BU7cD3Y9UdVZykG34NiijHZLlCBo/TnobXjFIPXvFbfgQ3y8g+akwocFVcQ= f
roop@snoop
""")

class ReadKeys_Test(object):
    def test_empty(self):
        tmp = maketemp()
        empty = os.path.join(tmp, 'empty')
        mkdir(empty)
        gen = ssh.readKeys(keydir=empty)
        assert_raises(StopIteration, gen.next)

    def test_ignore_dot(self):
        tmp = maketemp()
        keydir = os.path.join(tmp, 'ignore_dot')
        mkdir(keydir)
        writeFile(os.path.join(keydir, '.jdoe.pub'), KEY_1+'\n')
        gen = ssh.readKeys(keydir=keydir)
        assert_raises(StopIteration, gen.next)

    def test_ignore_nonpub(self):
        tmp = maketemp()
        keydir = os.path.join(tmp, 'ignore_dot')
        mkdir(keydir)
        writeFile(os.path.join(keydir, 'jdoe.xub'), KEY_1+'\n')
        gen = ssh.readKeys(keydir=keydir)
        assert_raises(StopIteration, gen.next)

    def test_one(self):
        tmp = maketemp()
        keydir = os.path.join(tmp, 'one')
        mkdir(keydir)
        writeFile(os.path.join(keydir, 'jdoe.pub'), KEY_1+'\n')

        gen = ssh.readKeys(keydir=keydir)
        eq(gen.next(), ('jdoe', KEY_1))
        assert_raises(StopIteration, gen.next)

    def test_two(self):
        tmp = maketemp()
        keydir = os.path.join(tmp, 'two')
        mkdir(keydir)
        writeFile(os.path.join(keydir, 'jdoe.pub'), KEY_1+'\n')
        writeFile(os.path.join(keydir, 'wsmith.pub'), KEY_2+'\n')

        gen = ssh.readKeys(keydir=keydir)
        got = frozenset(gen)

        eq(got,
           frozenset([
            ('jdoe', KEY_1),
            ('wsmith', KEY_2),
            ]))

    def test_multiple_lines(self):
        tmp = maketemp()
        keydir = os.path.join(tmp, 'keys')
        mkdir(keydir)
        writeFile(os.path.join(keydir, 'jd"oe.pub'), KEY_1+'\n')

        gen = ssh.readKeys(keydir=keydir)
        got = frozenset(gen)
        eq(got, frozenset([]))

    def test_bad_filename(self):
        tmp = maketemp()
        keydir = os.path.join(tmp, 'two')
        mkdir(keydir)
        writeFile(os.path.join(keydir, 'jdoe.pub'), KEY_1+'\n'+KEY_2+'\n')

        gen = ssh.readKeys(keydir=keydir)
        got = frozenset(gen)

        eq(got,
           frozenset([
            ('jdoe', KEY_1),
            ('jdoe', KEY_2),
            ]))

class GenerateAuthorizedKeys_Test(object):
    def test_simple(self):
        def k():
            yield ('jdoe', KEY_1)
            yield ('wsmith', KEY_2)
        gen = ssh.generateAuthorizedKeys(k())
        eq(gen.next(), ssh.COMMENT)
        eq(gen.next(), (
            'command="gitosis-serve jdoe",no-port-forwarding,no-X11-f'
            +'orwarding,no-agent-forwarding,no-pty %s' % KEY_1))
        eq(gen.next(), (
            'command="gitosis-serve wsmith",no-port-forwarding,no-X11'
            +'-forwarding,no-agent-forwarding,no-pty %s' % KEY_2))
        assert_raises(StopIteration, gen.next)


class FilterAuthorizedKeys_Test(object):
    def run(self, s):
        f = StringIO(s)
        lines = ssh.filterAuthorizedKeys(f)
        got = ''.join(['%s\n' % line for line in lines])
        return got

    def check_no_change(self, s):
        got = self.run(s)
        eq(got, s)

    def test_notFiltered_comment(self):
        self.check_no_change('#comment\n')

    def test_notFiltered_junk(self):
        self.check_no_change('junk\n')

    def test_notFiltered_key(self):
        self.check_no_change('%s\n' % KEY_1)

    def test_notFiltered_keyWithCommand(self):
        s = '''\
command="faketosis-serve wsmith",no-port-forwarding,no-X11-forwardin\
g,no-agent-forwarding,no-pty %(key_1)s
''' % dict(key_1=KEY_1)
        self.check_no_change(s)


    def test_filter_autogeneratedComment_backwardsCompat(self):
        got = self.run('### autogenerated by gitosis, DO NOT EDIT\n')
        eq(got, '')

    def test_filter_autogeneratedComment_current(self):
        got = self.run(ssh.COMMENT+'\n')
        eq(got, '')

    def test_filter_simple(self):
        s = '''\
command="gitosis-serve wsmith",no-port-forwarding,no-X11-forwardin\
g,no-agent-forwarding,no-pty %(key_1)s
''' % dict(key_1=KEY_1)
        got = self.run(s)
        eq(got, '')

    def test_filter_withPath(self):
        s = '''\
command="/foo/bar/baz/gitosis-serve wsmith",no-port-forwarding,no-X11-forwardin\
g,no-agent-forwarding,no-pty %(key_1)s
''' % dict(key_1=KEY_1)
        got = self.run(s)
        eq(got, '')


class WriteAuthorizedKeys_Test(object):
    def test_simple(self):
        tmp = maketemp()
        path = os.path.join(tmp, 'authorized_keys')
        f = file(path, 'w')
        try:
            f.write('''\
# foo
bar
### autogenerated by gitosis, DO NOT EDIT
command="/foo/bar/baz/gitosis-serve wsmith",no-port-forwarding,\
no-X11-forwarding,no-agent-forwarding,no-pty %(key_2)s
baz
''' % dict(key_2=KEY_2))
        finally:
            f.close()
        keydir = os.path.join(tmp, 'one')
        mkdir(keydir)
        writeFile(os.path.join(keydir, 'jdoe.pub'), KEY_1+'\n')

        ssh.writeAuthorizedKeys(
            path=path, keydir=keydir)

        got = readFile(path)
        eq(got, '''\
# foo
bar
baz
### autogenerated by gitosis, DO NOT EDIT
command="gitosis-serve jdoe",no-port-forwarding,\
no-X11-forwarding,no-agent-forwarding,no-pty %(key_1)s
''' % dict(key_1=KEY_1))

########NEW FILE########
__FILENAME__ = util
from nose.tools import eq_ as eq

import errno
import os
import shutil
import stat
import sys

def mkdir(*a, **kw):
    try:
        os.mkdir(*a, **kw)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

def maketemp():
    tmp = os.path.join(os.path.dirname(__file__), 'tmp')
    mkdir(tmp)

    caller = sys._getframe(1)
    name = '%s.%s' % (
        sys._getframe(1).f_globals['__name__'],
        caller.f_code.co_name,
        )
    tmp = os.path.join(tmp, name)
    try:
        shutil.rmtree(tmp)
    except OSError, e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise
    os.mkdir(tmp)
    return tmp

def writeFile(path, content):
    tmp = '%s.tmp' % path
    f = file(tmp, 'w')
    try:
        f.write(content)
    finally:
        f.close()
    os.rename(tmp, path)

def readFile(path):
    f = file(path)
    try:
        data = f.read()
    finally:
        f.close()
    return data

def assert_raises(excClass, callableObj, *args, **kwargs):
    """
    Like unittest.TestCase.assertRaises, but returns the exception.
    """
    try:
        callableObj(*args, **kwargs)
    except excClass, e:
        return e
    else:
        if hasattr(excClass,'__name__'): excName = excClass.__name__
        else: excName = str(excClass)
        raise AssertionError("%s not raised" % excName)

def check_mode(path, mode, is_file=None, is_dir=None):
    st = os.stat(path)
    if is_dir:
        assert stat.S_ISDIR(st.st_mode)
    if is_file:
        assert stat.S_ISREG(st.st_mode)

    got = stat.S_IMODE(st.st_mode)
    eq(got, mode, 'File mode %04o!=%04o for %s' % (got, mode, path))

########NEW FILE########
__FILENAME__ = util
import errno
import os
from ConfigParser import NoSectionError, NoOptionError

def mkdir(*a, **kw):
    try:
        os.mkdir(*a, **kw)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

def getRepositoryDir(config):
    repositories = os.path.expanduser('~')
    try:
        path = config.get('gitosis', 'repositories')
    except (NoSectionError, NoOptionError):
        repositories = os.path.join(repositories, 'repositories')
    else:
        repositories = os.path.join(repositories, path)
    return repositories

def getGeneratedFilesDir(config):
    try:
        generated = config.get('gitosis', 'generate-files-in')
    except (NoSectionError, NoOptionError):
        generated = os.path.expanduser('~/gitosis')
    return generated

def getSSHAuthorizedKeysPath(config):
    try:
        path = config.get('gitosis', 'ssh-authorized-keys-path')
    except (NoSectionError, NoOptionError):
        path = os.path.expanduser('~/.ssh/authorized_keys')
    return path

########NEW FILE########
