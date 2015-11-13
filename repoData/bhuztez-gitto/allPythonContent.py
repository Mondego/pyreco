__FILENAME__ = checker
import base64
import binascii

from twisted.conch.checkers import SSHPublicKeyDatabase


class GittoPublicKeyDatabase(SSHPublicKeyDatabase):

    def __init__(self, keyspath):
        self.keyspath = keyspath


    def getAuthorizedKeysFiles(self, credentials):
        return [self.keyspath.child(credentials.username)]


    def checkKey(self, credentials):
        for filepath in self.getAuthorizedKeysFiles(credentials):
            if not filepath.exists():
                continue

            for line in filepath.open():
                l2 = line.split()

                if len(l2) < 2:
                    continue

                try:
                    if base64.decodestring(l2[1]) == credentials.blob:
                        return True
                except binascii.Error:
                    continue

        return False

########NEW FILE########
__FILENAME__ = client
import argparse
import os.path
import os
import re
import sys
import ConfigParser

from .command import Command, argument


DATADIR = os.environ.get("GITTO_DATADIR", "data")
CONFDIR = ".config"
USER = os.environ.get("GITTO_USER", None)


NAME_RE = re.compile(r'[a-z0-9_][a-z0-9\.\-_]*')
GIT_DAEMON_EXPORT_OK = "git-daemon-export-ok"


def check_acl(basedir, perm):
    config = ConfigParser.SafeConfigParser(allow_no_value=True)

    try:
        f = open(os.path.join(basedir, CONFDIR, "acl.conf"), "r")
    except IOError:
        return False

    with f:
        try:
            config.readfp(f)
        except ConfigParser.Error:
            return False

    try:
        users = [u for u,_ in config.items(perm)]
    except ConfigParser.NoSectionError:
        return False

    return USER in users


def check_repo_basedir(project, *perms):
    dirpath = os.path.join(DATADIR, project)

    if project.startswith("~"):
        allowed = (project == "~"+USER)
    else:
        allowed = any(check_acl(dirpath, p) for p in perms)

    return allowed, dirpath


def get_repo_basedir(project, error_msg, *perms):
    allowed, dirpath = check_repo_basedir(project, *perms)

    if not allowed:
        print >>sys.stderr, "ERROR: You are not allowed to", error_msg % project
        exit(1)

    return dirpath


def get_config_basedir(dirname):
    if dirname == '':
        dirpath = DATADIR
    else:
        dirpath = os.path.join(DATADIR, dirname)

    if not check_acl(dirpath, "config"):
        print >>sys.stderr, "ERROR: You are not allowed to configure %s" % dirname
        exit(1)

    return dirpath


def valid_name(string):
    if not NAME_RE.match(string):
        raise argparse.ArgumentTypeError("'%s'" % string)
    return string


def valid_project_name(string):
    if string.startswith('~'):
        return '~' + valid_name(string[1:])
    return valid_name(string)


def sanitize_path(path):
    dirname, basename = os.path.split(path)

    if dirname == '':
        dirname = '~'+USER
    elif dirname == '/':
        dirname = ''
    else:
        while dirname.startswith("/"):
            dirname = dirname[1:]

        if not NAME_RE.match(dirname[dirname.startswith("~"):]):
            print >>sys.stderr, "ERROR: Invalid path '%s'" % path
            exit(1)

    if not dirname.startswith("~"):
        if basename == CONFDIR:
            return dirname, basename

    if not NAME_RE.match(basename):
        print >>sys.stderr, "ERROR: Invalid path '%s'" % path
        exit(1)

    return dirname, basename


def is_public(path):
    return os.path.exists(os.path.join(path, GIT_DAEMON_EXPORT_OK))


def listdir(path, public_only=True):
    try:
        names = os.listdir(path)
    except OSError:
        return

    for name in names:
        dirpath = os.path.join(path, name)

        if not NAME_RE.match(name):
            continue

        if os.path.isdir(dirpath):
            if public_only and not is_public(dirpath):
                continue

            print name


command = Command(description='Gitto SSH Command')


@command(argument("project", type=valid_name, help="Project name"))
def create(project):
    """create new project"""

    if not check_acl(DATADIR, "create-project"):
        print >>sys.stderr, "ERROR: You are not allowed to create new project."
        exit(1)

    os.execlp(sys.executable, "python", "-m", "gitto", "init-project", project, USER)


@command()
def projects():
    """list projects"""

    for d in os.listdir(DATADIR):
        dirpath = os.path.join(DATADIR, d)

        if not NAME_RE.match(d):
            continue

        if os.path.isdir(dirpath):
            print d


@command(argument("--public", action='store_true', help="publish repository"),
         argument("project", nargs="?", type=valid_name, help="Project name"),
         argument("repo", type=valid_name, help="Repository name")) # XXX: public
def init(public, repo, project="~"+USER):
    """init repositories"""

    get_repo_basedir(project, "create new repository under '%s' project.", "create-repo")

    args = ["python", "-m", "gitto", "init-repo"]

    if public:
        args += ["--public"]

    args += [project, repo]

    os.execvp(sys.executable, args)


@command(argument("project", nargs="?", type=valid_project_name, help="Project name or '~'"))
def ls(project="~"+USER):
    """list repositories"""

    allowed, dirpath = check_repo_basedir(project, "list-repo")
    listdir(dirpath, public_only=not allowed)


@command(argument("project", nargs="?", type=valid_name, help="Project name"),
         argument("repo", type=valid_name, help="Repository name"))
def publish_repo(repo, project="~"+USER):
    """Publish repository"""

    dirpath = get_repo_basedir(project, "publish repository under '%s' project.", "publish-repo")

    export = os.path.join(dirpath, repo, GIT_DAEMON_EXPORT_OK)

    try:
        open(export, "w").close()
    except IOError:
        if not os.path.exists(export):
            print >>sys.stderr, "ERROR: Failed to publish repo '%s'." % repo
            exit(1)


@command(argument("project", nargs="?", type=valid_name, help="Project name"),
         argument("name", type=valid_name, help="Repository name"))
def unpublish_repo(repo, project="~"+USER):
    "Unpublish repository"

    dirpath = get_repo_basedir(project, "publish repository under '%s' project.", "publish-repo")

    export = os.path.join(dirpath, repo, GIT_DAEMON_EXPORT_OK)

    try:
        os.remove(export)
    except OSError:
        if os.path.exists(export):
            print >>sys.stderr, "ERROR: Failed to unpublish repo '%s'." % repo
            exit(1)


@command(argument("directory", help="Repository directory"))
def git_upload_pack(directory):
    """git-upload-pack"""

    dirname, basename = sanitize_path(directory)

    if basename == CONFDIR:
        dirpath = get_config_basedir(dirname)
    elif dirname != '':
        allowed, dirpath = check_repo_basedir(dirname, "pull:"+basename, "pull:*")

        if not allowed:
            if not is_public(os.path.join(dirpath, basename)):
                print >>sys.stderr, "ERROR: You are not allowed to pull from '%s/%s'" % (dirname, basename)
                exit(1)
    else:
        print >>sys.stderr, "ERROR: Invalid path '%s'" % directory
        exit(1)

    os.execlp("git-upload-pack", "git-upload-pack", os.path.join(dirpath, basename))


@command(argument("directory", help="Repository directory"))
def git_receive_pack(directory):
    """git-receive-pack"""

    dirname, basename = sanitize_path(directory)

    if basename == CONFDIR:
        dirpath = get_config_basedir(dirname)
    elif dirname != '':
        dirpath = get_repo_basedir(dirname, "push to '%%s/%s'" % basename, "push:"+basename, "push:*")
    else:
        print >>sys.stderr, "ERROR: Invalid path '%s'" % directory
        exit(1)

    os.execlp("git-receive-pack", "git-receive-pack", os.path.join(dirpath, basename))


@command()
def help():
    """Print help message"""

    command.print_help()


if __name__ == '__main__':
    command.run()

########NEW FILE########
__FILENAME__ = command
import argparse
from functools import wraps


def argument(*args, **kwargs):
    return lambda parser: parser.add_argument(*args, **kwargs)


class Command(object):

    def __init__(self, *args, **kwargs):
        self._parser = argparse.ArgumentParser(*args, **kwargs)
        self._subparsers = self._parser.add_subparsers(dest="COMMAND")
        self._commands = {}


    def print_help(self):
        self._parser.print_help()


    def run(self):
        args = self._parser.parse_args()
        return self._commands[args.COMMAND](args)


    def __call__(self, *arguments):
        def decorator(func):
            name = func.__name__.replace("_", "-")

            subparser = self._subparsers.add_parser(name, help = func.__doc__)
            dests = [arg(subparser).dest for arg in arguments]

            @wraps(func)
            def wrapper(args):
                return func(**{d:getattr(args, d) for d in dests if getattr(args, d) is not None})

            self._commands[name] = wrapper
            return wrapper

        return decorator

########NEW FILE########
__FILENAME__ = session
import os
import os.path
import shlex
import sys

from twisted.cred.portal import IRealm
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.python import components

from twisted.conch.avatar import ConchUser
from twisted.conch.ssh.session import ISession, wrapProtocol, SSHSession

from zope.interface import implements



class DeafProtocol(Protocol):

    def __init__(self, datapath):
        self.datapath = datapath


    def connectionMade(self):
        banner = self.datapath.child('.config').child('BANNER')

        if banner.exists():
            with banner.open() as f:
                self.transport.write(f.read().replace('\n', '\r\n'))

        self.transport.loseConnection()



class DummyTransport:

    def loseConnection(self):
        pass



class GittoSession:
    implements(ISession)

    def __init__(self, avatar):
        self.avatar = avatar
        self.pty = None


    def getPty(self, term, windowSize, attrs):
        pass


    def closed(self):
        pass


    def eofReceived(self):
        if self.pty:
            self.pty.closeStdin()


    def _die(self, proto, message):
        proto.makeConnection(DummyTransport())
        proto.errReceived(message)
        proto.loseConnection()


    def _fail(self, fail, proto):
        self._die(proto, "ERROR: internal server error\n")


    def execCommand(self, proto, cmd):
        argv = shlex.split(cmd)
        environ = os.environ.copy()
        environ["GITTO_USER"] = self.avatar.username
        environ["GITTO_DATADIR"] = self.avatar.datapath.path

        self.pty = reactor.spawnProcess(
            proto,
            sys.executable,
            ['python', '-m', 'gitto.client'] + argv,
            env=environ)


    def openShell(self, trans):
        ep = DeafProtocol(self.avatar.datapath)
        ep.makeConnection(trans)
        trans.makeConnection(wrapProtocol(ep))



class GittoUser(ConchUser):

    def __init__(self, username, datapath):
        ConchUser.__init__(self)
        self.username = username
        self.datapath = datapath
        self.channelLookup["session"] = SSHSession


    def logout(self):
        pass


components.registerAdapter(GittoSession, GittoUser, ISession)


class GittoRealm:
    implements(IRealm)

    def __init__(self, datapath):
        self.datapath = datapath

    def requestAvatar(self, username, mind, *interfaces):
        user = GittoUser(username, self.datapath)
        return interfaces[0], user, user.logout

########NEW FILE########
__FILENAME__ = tap
from twisted.application import strports
from twisted.cred.portal import Portal
from twisted.python import usage
from twisted.python.filepath import FilePath

from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key

from .checker import GittoPublicKeyDatabase
from .session import GittoRealm


class Options(usage.Options):

    optParameters = [
        ["port",    "p", "tcp:22", "port of ssh server"],
        ["datadir", "d", "data",   "path to data directory"],
        ["key",     "k", "id_rsa", "path to private key of ssh server"]]


def makeService(config):
    key = Key.fromFile(config["key"])
    datapath = FilePath(config['datadir'])

    factory = SSHFactory()
    factory.publicKeys = factory.privateKeys = {key.sshType(): key}

    factory.portal = Portal(
        GittoRealm(datapath),
        [GittoPublicKeyDatabase(datapath.child(".config").child("keys"))])

    return strports.service(config['port'], factory)

########NEW FILE########
__FILENAME__ = __main__
import os
import os.path
import sys
import ConfigParser
import subprocess
import shutil
import stat

from .command import Command, argument


DATADIR = os.environ.get("GITTO_DATADIR", "data")
GIT_DAEMON_EXPORT_OK = "git-daemon-export-ok"
BANNER = '\n'.join([
r"""             _ __  __       """,
r"""      ____ _(_) /_/ /_____  """,
r"""     / __ `/ / __/ __/ __ \ """,
r"""    / /_/ / / /_/ /_/ /_/ / """,
r"""    \__, /_/\__/\__/\____/  """,
r"""   /____/                   """,
r"""""",
r"""You've successfully authenticated,""",
r"""but we provide no shell access""",
r""""""])


def config(*configs):
    conf = ConfigParser.SafeConfigParser(allow_no_value=True)

    for c in configs:
        if not conf.has_section(c[0]):
            conf.add_section(c[0])

        conf.set(*c)

    return conf


def write_config(path, *configs):
    conf = config(*configs)

    with open(path, "w") as f:
        conf.write(f)


def git(gitdir, *commands):
    p = subprocess.Popen(("git",)+commands, close_fds=True, cwd=gitdir)
    p.communicate()
    return p


def git_init(path, bare, *extra):
    if not bare:
        repopath = os.path.join(path, '.git')
    else:
        repopath = path

    write_config(
        os.path.join(repopath, "config"),
        ('core', 'repositoryformatversion', '0'),
        ('core', 'filemode', 'true'),
        ('core', 'bare', 'true' if bare else 'false'),
        *extra)

    with open(os.path.join(repopath, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    os.mkdir(os.path.join(repopath, "objects"))
    os.mkdir(os.path.join(repopath, "objects", "pack"))
    os.mkdir(os.path.join(repopath, "objects", "info"))
    os.mkdir(os.path.join(repopath, "refs"))
    os.mkdir(os.path.join(repopath, "refs", "heads"))
    os.mkdir(os.path.join(repopath, "refs", "tags"))


def config_repo_init(confdir, creator):
    git_init(confdir, False,
             ('user', 'name', creator),
             ('user', 'email', creator+"@gitto"),
             ('receive', 'denyCurrentBranch', 'ignore'))

    git(confdir, "add", ".")
    git(confdir, "commit", "-a", "-m", "Initial commit")


command = Command(description='Gitto Initialize Command')


@command(argument("username", help="name of superuser"),
         argument("pkey", help="path to superuser's pubkey"),
         argument("datadir", nargs='?', help="path to data directory, defaults to data"))
def init(username, pkey, datadir=DATADIR):
    """Initialize Gitto data directory"""

    try:
        os.mkdir(datadir)
    except OSError:
        assert os.path.exists(datadir), "Failed to create datadir"

    confdir = os.path.join(datadir, ".config")
    os.mkdir(confdir)
    os.mkdir(os.path.join(confdir, "keys"))
    os.mkdir(os.path.join(confdir, ".git"))

    shutil.copy(pkey, os.path.join(confdir, "keys", username))

    with open(os.path.join(confdir, "BANNER"), "w") as f:
        f.write(BANNER)

    write_config(
        os.path.join(confdir, "acl.conf"),
        ('config', username),
        ('create-project', username))

    os.mkdir(os.path.join(confdir, "hooks"))
    os.mkdir(os.path.join(confdir, "config-hooks"))
    post_receive = os.path.join(confdir, "config-hooks", "post-receive")
    with open(post_receive, "w") as f:
        f.write("#!/bin/sh\ncd ..\nenv -i - git reset --hard HEAD\n")

    os.chmod(post_receive, os.stat(post_receive)[0] | stat.S_IXUSR)

    config_repo_init(confdir, username)
    hooksdir = os.path.join("..", "config-hooks")
    os.symlink(hooksdir, os.path.join(confdir, ".git", "hooks"))


@command(argument("project", help="project name"),
         argument("creator", help="name of creator"),
         argument("datadir", nargs='?', help="path to data directory, defaults to data"))
def init_project(project, creator, datadir=DATADIR):
    """Initialize project"""

    dirpath = os.path.join(datadir, project)

    try:
        os.mkdir(dirpath)
    except OSError:
        print >>sys.stderr, "Failed to create project '%s'" % project
        exit(1)

    confdir = os.path.join(dirpath, ".config")
    os.mkdir(confdir)
    os.mkdir(os.path.join(confdir, ".git"))

    write_config(
        os.path.join(confdir, "acl.conf"),
        ('config', creator),
        ('create-repo', creator),
        ('list-repo', creator),
        ('push:*', creator),
        ('pull:*', creator))

    config_repo_init(confdir, creator)
    hooksdir = os.path.join("..", "..", "..", ".config", "config-hooks")
    os.symlink(hooksdir, os.path.join(confdir, ".git", "hooks"))


@command(argument("--public", action="store_true", help="publish repository"),
         argument("project", help="project name"),
         argument("repo", help="repository name"),
         argument("datadir", nargs='?', help="path to data directory, defaults to data"))
def init_repo(project, repo, public, datadir=DATADIR):
    """Initialize repository"""

    dirpath = os.path.join(datadir, project)

    if project.startswith("~"):
        try:
            os.mkdir(dirpath)
        except OSError:
            if not os.path.exists(dirpath):
                print >>sys.stderr, "Failed to initialize directory '%s'" % project
                exit(1)

    repopath = os.path.join(dirpath, repo)

    try:
        os.mkdir(repopath)
    except OSError:
        print >>sys.stderr, "Failed to create repository '%s'" % repo
        exit(1)

    git_init(repopath, True)
    hooksdir = os.path.join("..", "..", ".config", "hooks")
    os.symlink(hooksdir, os.path.join(repopath, "hooks"))

    if public:
        open(os.path.join(repopath, GIT_DAEMON_EXPORT_OK), "w").close()



if __name__ == '__main__':
    command.run()

########NEW FILE########
__FILENAME__ = gitto
from twisted.application.service import ServiceMaker

Gitto = ServiceMaker(
    "Gitto",
    "gitto.tap",
    "Poor man's git hosting",
    "gitto")

########NEW FILE########
