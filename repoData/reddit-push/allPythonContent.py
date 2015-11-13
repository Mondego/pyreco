__FILENAME__ = args
import sys
import argparse
import itertools
import collections

import push.hosts
import push.utils


__all__ = ["parse_args", "ArgumentError"]


class MutatingAction(argparse.Action):
    def __init__(self, *args, **kwargs):
        self.type_to_mutate = kwargs.pop("type_to_mutate")
        argparse.Action.__init__(self, *args, **kwargs)

    def get_attr_to_mutate(self, namespace):
        o = getattr(namespace, self.dest, None)
        if not o:
            o = self.type_to_mutate()
            setattr(namespace, self.dest, o)
        return o


class SetAddConst(MutatingAction):
    "Action that adds a constant to a set."
    def __init__(self, *args, **kwargs):
        kwargs["nargs"] = 0
        MutatingAction.__init__(self, *args,
                                type_to_mutate=collections.OrderedDict,
                                **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        s = self.get_attr_to_mutate(namespace)

        if hasattr(self.const, "__iter__"):
            for x in self.const:
                s[x] = ""
        else:
            s[self.const] = ""


class SetAddValues(MutatingAction):
    "Action that adds values to a set."
    def __init__(self, *args, **kwargs):
        MutatingAction.__init__(self, *args,
                                type_to_mutate=collections.OrderedDict,
                                **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        s = self.get_attr_to_mutate(namespace)

        for x in values:
            s[x] = ""


class DictAdd(MutatingAction):
    "Action that adds an argument to a dict with a constant key."
    def __init__(self, *args, **kwargs):
        MutatingAction.__init__(self, *args, type_to_mutate=dict, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        d = self.get_attr_to_mutate(namespace)
        key, value = values
        d[key] = value


class RestartCommand(MutatingAction):
    """Makes a deploy command out of -r (graceful restart) options."""

    def __init__(self, *args, **kwargs):
        MutatingAction.__init__(self, *args, type_to_mutate=list, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        command_list = self.get_attr_to_mutate(namespace)
        command_list.append(["restart", values[0]])


class KillCommand(MutatingAction):
    """Makes a deploy command out of -k (kill) options."""

    def __init__(self, *args, **kwargs):
        MutatingAction.__init__(self, *args, type_to_mutate=list, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        command_list = self.get_attr_to_mutate(namespace)
        command_list.append(["kill", values[0]])


class StoreIfHost(argparse.Action):
    "Stores value if it is a known host."
    def __init__(self, *args, **kwargs):
        self.all_hosts = kwargs.pop("all_hosts")
        argparse.Action.__init__(self, *args, **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):
        if value not in self.all_hosts:
            raise argparse.ArgumentError(self, 'unknown host "%s"' % value)
        setattr(namespace, self.dest, value)


class ArgumentError(Exception):
    "Exception raised when there's something wrong with the arguments."
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ArgumentParser(argparse.ArgumentParser):
    """Custom argument parser that raises an exception rather than exiting
    the program"""

    def error(self, message):
        raise ArgumentError(message)


def _parse_args(config):
    parser = ArgumentParser(description="Deploy stuff to servers.",
                            epilog="To deploy all code: push -h apps "
                                   "-pc -dc -r all --shuffle",
                            add_help=False)

    parser.add_argument("-h", dest="host_refs", metavar="HOST", required=True,
                        action="append", nargs="+",
                        help="hosts or groups to execute commands on")
    parser.add_argument("--sleeptime", dest="sleeptime", nargs="?",
                        type=int, default=config.defaults.sleeptime,
                        metavar="SECONDS",
                        help="time in seconds to sleep between hosts")
    parser.add_argument("--startat", dest="start_at",
                        action="store", nargs='?', metavar="HOST",
                        help="skip to this position in the host list")
    parser.add_argument("--seed", dest="seed", action="store",
                        nargs="?", metavar="WORD", default=None,
                        help="name of push to copy the shuffle-order of")
    parser.add_argument("--shuffle", dest="shuffle",
                        default=config.defaults.shuffle,
                        action="store_true", help="shuffle host list")
    parser.add_argument("--no-shuffle", dest="shuffle",
                        action="store_false",
                        help="don't shuffle host list")
    parser.add_argument("--skip", dest="skip_one",
                        action="store_true", default=False,
                        help="skip the first host in the list (obeying startat first)")
    parser.add_argument("--list", dest="list_hosts",
                        action="store_true", default=False,
                        help="print the host list to stdout and exit")

    flags_group = parser.add_argument_group("flags")
    flags_group.add_argument("-t", dest="testing", action="store_true",
                             help="testing: print but don't execute")
    flags_group.add_argument("-q", dest="quiet", action="store_true",
                             help="quiet: no output except errors. implies "
                                  "--no-input")
    flags_group.add_argument("--no-irc", dest="notify_irc",
                             action="store_false",
                             help="don't announce actions in irc")
    flags_group.add_argument("--no-static", dest="build_static",
                             action="store_false",
                             help="don't build static files")
    flags_group.add_argument("--no-input", dest="auto_continue",
                             action="store_true",
                             help="don't wait for input after deploy")

    parser.add_argument("--help", action="help", help="display this help")

    deploy_group = parser.add_argument_group("deploy")
    deploy_group.add_argument("-p", dest="fetches", default=set(),
                              action=SetAddValues, nargs="+",
                              metavar="REPO",
                              help="git-fetch the specified repo(s)")
    deploy_group.add_argument("-pc", dest="fetches",
                              action=SetAddConst, const=["public", "private"],
                              help="short for -p public private")
    deploy_group.add_argument("-ppr", dest="fetches",
                              action=SetAddConst, const=["private"],
                              help="short for -p private")

    deploy_group.add_argument("-d", dest="deploys", default=set(),
                              action=SetAddValues, nargs="+",
                              metavar="REPO",
                              help="deploy the specified repo(s)")
    deploy_group.add_argument("-dc", dest="deploys",
                              action=SetAddConst, const=["public", "private"],
                              help="short for -d public private")
    deploy_group.add_argument("-dpr", dest="deploys",
                              action=SetAddConst, const=["private"],
                              help="short for -d private")
    deploy_group.add_argument("-rev", dest="revisions", default={},
                              metavar=("REPO", "REF"), action=DictAdd,
                              nargs=2,
                              help="revision to deploy for specified repo")

    parser.add_argument("-c", dest="deploy_commands", nargs="+",
                        metavar=("COMMAND", "ARG"), action="append",
                        help="deploy command to run on the host",
                        default=[])
    parser.add_argument("-r", dest="deploy_commands", nargs=1,
                        metavar="COMMAND", action=RestartCommand,
                        help="whom to (gracefully) restart on the host")
    parser.add_argument("-k", dest="deploy_commands", nargs=1,
                        action=KillCommand, choices=["all", "apps"],
                        help="whom to kill on the host")

    if len(sys.argv) == 1:
        parser.print_help()

    return parser.parse_args()


def build_command_line(config, args):
    "Given a configured environment, build a canonical command line for it."
    components = []

    components.append("-h")
    components.extend(itertools.chain.from_iterable(args.host_refs))

    if args.start_at:
        components.append("--startat=%s" % args.start_at)

    if args.fetches:
        components.append("-p")
        components.extend(args.fetches)

    if args.deploys:
        components.append("-d")
        components.extend(args.deploys)

    commands = dict(restart="-r",
                    kill="-k")
    for command in args.deploy_commands:
        special_command = commands.get(command[0])
        if special_command:
            components.append(special_command)
            command = command[1:]
        else:
            components.append("-c")

        components.extend(command)

    for repo, rev in args.revisions.iteritems():
        components.extend(("-rev", repo, rev))

    if not args.build_static:
        components.append("--no-static")

    if args.auto_continue:
        components.append("--no-input")

    if not args.notify_irc:
        components.append("--no-irc")

    if args.quiet:
        components.append("--quiet")

    if args.testing:
        components.append("-t")

    if args.shuffle:
        components.append("--shuffle")

    if args.seed:
        components.append("--seed=%s" % args.seed)

    if args.skip_one:
        components.append("--skip")

    components.append("--sleeptime=%d" % args.sleeptime)

    return " ".join(components)


def parse_args(config, host_source):
    args = _parse_args(config)

    # give the push a unique name
    args.push_id = push.utils.get_random_word(config)

    # quiet implies autocontinue
    if args.quiet:
        args.auto_continue = True

    # dereference the host lists
    all_hosts, aliases = push.hosts.get_hosts_and_aliases(config, host_source)
    args.hosts = []
    queue = collections.deque(args.host_refs)
    while queue:
        host_or_alias = queue.popleft()

        # individual instances of -h append a list to the list. flatten
        if hasattr(host_or_alias, "__iter__"):
            queue.extend(host_or_alias)
            continue

        # backwards compatibility with perl version
        if " " in host_or_alias:
            queue.extend(x.strip() for x in host_or_alias.split())
            continue

        if host_or_alias in all_hosts:
            args.hosts.append(host_or_alias)
        elif host_or_alias in aliases:
            args.hosts.extend(aliases[host_or_alias])
        else:
            raise ArgumentError('-h: unknown host or alias "%s"' %
                                host_or_alias)

    # make sure the startat is in the dereferenced host list
    if args.start_at and args.start_at not in args.hosts:
        raise ArgumentError('--startat: host "%s" not in host list.' %
                            args.start_at)

    # it really doesn't make sense to start-at while shufflin' w/o a seed
    if args.start_at and args.shuffle and not args.seed:
        raise ArgumentError("--startat: doesn't make sense "
                            "while shuffling without a seed")

    # do the shuffle!
    if args.shuffle:
        seed = args.seed or args.push_id
        push.utils.seeded_shuffle(seed, args.hosts)

    # build a psuedo-commandline out of args and defaults
    args.command_line = build_command_line(config, args)

    return args

########NEW FILE########
__FILENAME__ = cli
import sys
import tty
import time
import termios
import signal

import push.deploy


SIGNAL_MESSAGES = {signal.SIGINT: "received SIGINT",
                   signal.SIGHUP: "received SIGHUP. tsk tsk."}


def read_character():
    "Read a single character from the terminal without echoing it."
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def wait_for_input(log, deployer):
    """Wait for the user's choice of whether or not to continue the push.
    Return whether or not to auto-continue after further hosts."""

    print >> log, ('Press "x" to abort, "c" to go to the next host, or '
                   '"a" to continue automatically.')

    while True:
        c = read_character()
        if c == "a":
            print >> log, "Continuing automatically. Press ^C to abort."
            return True
        elif c == "x":
            deployer.cancel_push('"x" pressed')
        elif c == "c":
            return False


def sleep_with_countdown(log, sleeptime):
    if sleeptime == 0:
        return

    print >> log, "Sleeping...",
    log.flush()

    for i in xrange(sleeptime, 0, -1):
        print >> log, " %d..." % i,
        log.flush()
        time.sleep(1)

    print >> log, ""


def register(config, args, deployer, log):
    def sighandler(sig, stack):
        reason = SIGNAL_MESSAGES[sig]
        deployer.cancel_push(reason)

    @deployer.push_began
    def on_push_began(deployer):
        signal.signal(signal.SIGINT, sighandler)
        signal.signal(signal.SIGHUP, sighandler)

        if args.testing:
            log.warning("*** Testing mode. No commands will be run. ***")

        log.notice("*** Beginning push. ***")
        log.notice("Log available at %s", log.log_path)

    @deployer.synchronize_began
    def on_sync_began(deployer):
        log.notice("Synchronizing build repos with GitHub...")

    @deployer.resolve_refs_began
    def on_resolve_refs_began(deployer):
        log.notice("Resolving refs...")

    @deployer.deploy_to_build_host_began
    def on_deploy_to_build_host_began(deployer):
        log.notice("Deploying to build host...")

    @deployer.build_static_began
    def on_build_static_began(deployer):
        log.notice("Building static files...")

    @deployer.process_host_began
    def on_process_host_began(deployer, host):
        log.notice('Starting host "%s"...', host)

    @deployer.process_host_ended
    def on_process_host_ended(deployer, host):
        host_index = args.hosts.index(host) + 1
        host_count = len(args.hosts)
        percentage = int((float(host_index) / host_count) * 100)
        log.notice('Host "%s" done (%d of %d -- %d%% done).',
                   host, host_index, host_count, percentage)

        if args.hosts[-1] == host:
            pass
        elif args.auto_continue:
            sleep_with_countdown(log, args.sleeptime)
        else:
            args.auto_continue = wait_for_input(log, deployer)

    @deployer.push_ended
    def on_push_ended(deployer):
        log.notice("*** Push complete! ***")

    @deployer.push_aborted
    def on_push_aborted(deployer, exception):
        if isinstance(exception, push.deploy.PushAborted):
            log.critical("\n*** Push cancelled (%s) ***", exception)

    def host_error_prompt(host, exception):
        log.critical("Encountered error on %s: %s", host, exception)
        print >> log, 'Press "x" to abort, "c" to skip to the next host'

        while True:
            c = read_character()
            if c == "x":
                return False
            elif c == "c":
                return True
    deployer.host_error_prompt = host_error_prompt

########NEW FILE########
__FILENAME__ = config
from __future__ import absolute_import

import os
import collections
import ConfigParser


NoDefault = object()
SECTIONS = collections.OrderedDict()


class attrdict(dict):
    "A dict whose keys can be accessed as attributes."
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class ConfigurationError(Exception):
    "Exception to raise when there's a problem with the configuration file."
    def __init__(self, section, name, message):
        self.section = section
        self.name = name
        self.message = message

    def __str__(self):
        return 'section "%s": option "%s": %s' % (self.section,
                                                  self.name,
                                                  self.message)


def boolean(input):
    """Converter that takes a string and tries to divine if it means
    true or false"""
    if input.lower() in ("true", "on"):
        return True
    elif input.lower() in ("false", "off"):
        return False
    else:
        raise ValueError('"%s" not boolean' % input)


class Option(object):
    "Declarative explanation of a configuration option."
    def __init__(self, convert, default=NoDefault, validator=None):
        self.convert = convert
        self.default = default
        self.validator = validator


def _make_extractor(cls, prefix="", required=True):
    section_name = cls.__name__[:-len("config")].lower()
    if prefix:
        section_name = prefix + ":" + section_name

    def config_extractor(parser):
        section = attrdict()
        for name, option_def in vars(cls).iteritems():
            if not isinstance(option_def, Option):
                continue

            try:
                value = parser.get(section_name, name)
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                if option_def.default is NoDefault:
                    raise ConfigurationError(section_name, name,
                                             "required but not present")
                value = option_def.default
            else:
                try:
                    value = option_def.convert(value)
                except Exception, e:
                    raise ConfigurationError(section_name, name, e)

            section[name] = value
        return section

    config_extractor.required = required
    config_extractor.prefix = prefix
    SECTIONS[section_name] = config_extractor


def config_section(*args, **kwargs):
    if len(args) == 1 and not kwargs:
        # bare decorator "@config_section" style
        return _make_extractor(args[0])

    def config_decorator(cls):
        return _make_extractor(cls, **kwargs)
    return config_decorator


@config_section
class SshConfig(object):
    user = Option(str)
    key_filename = Option(str, default=None)
    strict_host_key_checking = Option(boolean, default=True)
    timeout = Option(int, default=30)


@config_section
class DeployConfig(object):
    build_host = Option(str)
    deploy_binary = Option(str)
    build_binary = Option(str)


@config_section
class PathsConfig(object):
    log_root = Option(str)
    wordlist = Option(str, default="/usr/share/dict/words")


@config_section
class SyslogConfig(object):
    def syslog_enum(value):
        import syslog
        value = "LOG_" + value
        return getattr(syslog, value)

    ident = Option(str, default="deploy")
    facility = Option(syslog_enum)
    priority = Option(syslog_enum)


@config_section
class HostsConfig(object):
    def valid_host_source(value):
        try:
            section = SECTIONS["hosts:" + value]
        except KeyError:
            raise ValueError("invalid host source: %r" % value)
        section.required = True
        return value
    source = Option(valid_host_source)


@config_section(prefix="hosts", required=False)
class DnsConfig(object):
    domain = Option(str)


@config_section(prefix="hosts", required=False)
class MockConfig(object):
    host_count = Option(int)


@config_section(prefix="hosts", required=False)
class ZooKeeperConfig(object):
    connection_string = Option(str)
    username = Option(str)
    password = Option(str)


@config_section
class DefaultsConfig(object):
    sleeptime = Option(int, default=5)
    shuffle = Option(boolean, default=False)


def alias_parser(parser):
    aliases = {}
    if parser.has_section("aliases"):
        for key, value in parser.items("aliases"):
            aliases[key] = [glob.strip() for glob in value.split(' ')]
    return aliases
SECTIONS["aliases"] = alias_parser


def default_ref_parser(parser):
    default_refs = {}
    if parser.has_section("default_refs"):
        default_refs.update(parser.items("default_refs"))
    return default_refs
SECTIONS["default_refs"] = default_ref_parser


def parse_config():
    """Loads the configuration files and parses them according to the
    section parsers in SECTIONS."""
    parser = ConfigParser.RawConfigParser()
    parser.read(["/opt/push/etc/push.ini", os.path.expanduser("~/.push.ini")])

    config = attrdict()
    for name, section_parser in SECTIONS.iteritems():
        is_required = getattr(section_parser, "required", True)
        if is_required or parser.has_section(name):
            prefix = getattr(section_parser, "prefix", None)
            parsed = section_parser(parser)
            if not prefix:
                config[name] = parsed
            else:
                unprefixed = name[len(prefix) + 1:]
                config.setdefault(prefix, attrdict())[unprefixed] = parsed

    return config

########NEW FILE########
__FILENAME__ = deploy
import push.ssh

auto_events = []


class PushAborted(Exception):
    "Raised when the deploy is cancelled."
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason


class Event(object):
    """An event that can have an arbitrary number of listeners that get called
    when the event fires."""
    def __init__(self, parent):
        self.parent = parent
        self.listeners = set()

    def register_listener(self, callable):
        self.listeners.add(callable)
        return callable

    def fire(self, *args, **kwargs):
        for listener in self.listeners:
            listener(self.parent, *args, **kwargs)

    __call__ = register_listener


def event_wrapped(fn):
    """Wraps a function "fn" and fires the "fn_began" event before entering
    the function, "fn_ended" after succesfully returning, and "fn_aborted"
    on exception."""
    began_name = fn.__name__ + "_began"
    ended_name = fn.__name__ + "_ended"
    aborted_name = fn.__name__ + "_aborted"
    auto_events.extend((began_name, ended_name, aborted_name))

    def proxy(self, *args, **kwargs):
        getattr(self, began_name).fire(*args, **kwargs)
        try:
            result = fn(self, *args, **kwargs)
        except Exception, e:
            getattr(self, aborted_name).fire(e)
            raise
        else:
            getattr(self, ended_name).fire(*args, **kwargs)
            return result

    return proxy


class Deployer(object):
    def __init__(self, config, args, log, host_source):
        self.config = config
        self.args = args
        self.log = log
        self.host_source = host_source
        self.deployer = push.ssh.SshDeployer(config, args, log)
        self.host_error_prompt = None

        for event_name in auto_events:
            setattr(self, event_name, Event(self))

    def _run_fetch_on_host(self, host, origin="origin"):
        for repo in self.args.fetches:
            self.deployer.run_deploy_command(host, "fetch", repo, origin)

    def _deploy_to_host(self, host):
        for repo in self.args.deploys:
            self.deployer.run_deploy_command(host, "deploy", repo,
                                             self.args.revisions[repo])

    @event_wrapped
    def synchronize(self):
        for repo in self.args.fetches:
            self.deployer.run_build_command("synchronize", repo)

        self._run_fetch_on_host(self.config.deploy.build_host)

    @event_wrapped
    def resolve_refs(self):
        for repo in self.args.deploys:
            default_ref = self.config.default_refs.get(repo, "origin/master")
            ref_to_deploy = self.args.revisions.get(repo, default_ref)
            revision = self.deployer.run_build_command("get-revision", repo,
                                                       ref_to_deploy,
                                                       display_output=False)
            self.args.revisions[repo] = revision.strip()

    @event_wrapped
    def build_static(self):
        self.deployer.run_build_command("build-static")

    @event_wrapped
    def deploy_to_build_host(self):
        self._deploy_to_host(self.config.deploy.build_host)

    @event_wrapped
    def process_host(self, host):
        self._run_fetch_on_host(host)
        self._deploy_to_host(host)

        for command in self.args.deploy_commands:
            self.deployer.run_deploy_command(host, *command)

    def needs_static_build(self, repo):
        try:
            self.deployer.run_build_command("needs-static-build", repo,
                                            display_output=False)
        except push.ssh.SshError:
            return False
        else:
            return True

    @event_wrapped
    def push(self):
        try:
            self._push()
        finally:
            self.deployer.shutdown()

    @event_wrapped
    def prompt_error(self, host, error):
        return self.host_error_prompt(host, error)

    def _push(self):
        if self.args.fetches:
            self.synchronize()

        if self.args.deploys:
            self.resolve_refs()
            self.deploy_to_build_host()

        if self.args.build_static:
            build_static = False
            for repo in self.args.deploys:
                if repo == "public" or self.needs_static_build(repo):
                    build_static = True
                    break

            if build_static:
                self.build_static()
                self.args.deploy_commands.append(["fetch-names"])

        for host in self.args.hosts:
            # skip hosts until we get the one to start at
            if self.args.start_at:
                if host == self.args.start_at:
                    self.args.start_at = None
                else:
                    continue

            # skip one host
            if self.args.skip_one:
                self.args.skip_one = False
                continue

            try:
                self.process_host(host)
            except (push.ssh.SshError, IOError) as e:
                if self.host_source.should_host_be_alive(host):
                    if self.host_error_prompt and self.prompt_error(host, e):
                        continue
                    raise
                else:
                    self.log.warning("Host %r appears to have been terminated."
                                     " ignoring errors and continuing." % host)


    def cancel_push(self, reason):
        raise PushAborted(reason)

########NEW FILE########
__FILENAME__ = dns
from __future__ import absolute_import

import dns.name
import dns.zone
import dns.query
import dns.exception
import dns.resolver
import dns.rdtypes

from push.hosts import HostSource, HostLookupError


class DnsHostSource(HostSource):
    def __init__(self, config):
        self.domain = config.hosts.dns.domain

    def get_all_hosts(self):
        """Pull all hosts from DNS by doing a zone transfer."""

        try:
            soa_answer = dns.resolver.query(self.domain, "SOA", tcp=True)
            soa_host = soa_answer[0].mname

            master_answer = dns.resolver.query(soa_host, "A", tcp=True)
            master_addr = master_answer[0].address

            xfr_answer = dns.query.xfr(master_addr, self.domain)
            zone = dns.zone.from_xfr(xfr_answer)
            return [name.to_text()
                    for name, ttl, rdata in zone.iterate_rdatas("A")]
        except dns.exception.DNSException, e:
            raise HostLookupError("host lookup by dns failed: %r" % e)

########NEW FILE########
__FILENAME__ = mock
from push.hosts import HostSource


class MockHostSource(HostSource):
    def __init__(self, config):
        self.host_count = config.hosts.mock.host_count

    def get_all_hosts(self):
        return ["app-%02d" % i for i in xrange(self.host_count)]

########NEW FILE########
__FILENAME__ = zookeeper
from kazoo.client import KazooClient
from kazoo.exceptions import KazooException, NoNodeException
from kazoo.retry import KazooRetry

from push.hosts import HostSource, HostLookupError


class ZookeeperHostSource(HostSource):
    def __init__(self, config):
        self.zk = KazooClient(config.hosts.zookeeper.connection_string)
        self.zk.start()
        credentials = ":".join((config.hosts.zookeeper.username,
                                config.hosts.zookeeper.password))
        self.zk.add_auth("digest", credentials)
        self.retry = KazooRetry(max_tries=3)

    def get_all_hosts(self):
        try:
            return self.retry(self.zk.get_children, "/server")
        except KazooException as e:
            raise HostLookupError("zk host enumeration failed: %r", e)

    def should_host_be_alive(self, host_name):
        try:
            host_root = "/server/" + host_name

            state = self.retry(self.zk.get, host_root + "/state")[0]
            if state in ("kicking", "unhealthy"):
                return False

            is_autoscaled = self.retry(self.zk.exists, host_root + "/asg")
            is_running = self.retry(self.zk.exists, host_root + "/running")
            return not is_autoscaled or is_running
        except NoNodeException:
            return False
        except KazooException as e:
            raise HostLookupError("zk host aliveness check failed: %r", e)

    def shut_down(self):
        self.zk.stop()

########NEW FILE########
__FILENAME__ = irc
import wessex
import getpass


def register(config, args, deployer, log):
    if not args.notify_irc:
        return

    harold = wessex.connect_harold()
    monitor = harold.get_deploy(args.push_id)

    def log_exception_and_continue(fn):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception, e:
                log.warning("Harold error: %s", e)
        return wrapper

    @deployer.push_began
    @log_exception_and_continue
    def on_push_began(deployer):
        monitor.begin(getpass.getuser(), args.command_line,
                      log.log_path, len(args.hosts))

    @deployer.process_host_ended
    @log_exception_and_continue
    def on_process_host_ended(deployer, host):
        index = args.hosts.index(host) + 1
        monitor.progress(host, index)

    @deployer.push_ended
    @log_exception_and_continue
    def on_push_ended(deployer):
        monitor.end()

    @deployer.push_aborted
    @log_exception_and_continue
    def on_push_aborted(deployer, e):
        monitor.abort(str(e))

    @deployer.prompt_error_began
    @log_exception_and_continue
    def on_prompt_error_began(deployer, host, error):
        monitor.error(str(error))

########NEW FILE########
__FILENAME__ = log
import os
import sys
import codecs
import getpass
import datetime


__all__ = ["Log", "register"]


RED = 31
GREEN = 32
YELLOW = 33
BLUE = 34
MAGENTA = 35
CYAN = 36
WHITE = 37


def colorize(text, color, bold):
    if color:
        boldizer = "1;" if bold else ""
        start_color = "\033[%s%dm" % (boldizer, color)
        end_color = "\033[0m"
        return "".join((start_color, text, end_color))
    else:
        return text


class Log(object):
    def __init__(self, config, args):
        self.args = args

        # generate a unique id for the push
        self.push_id = args.push_id

        # build the path for the logfile
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H:%M:%S")
        log_name = "-".join((timestamp, self.push_id)) + ".log"
        self.log_path = os.path.join(config.paths.log_root, log_name)

        # open the logfile
        self.logfile = codecs.open(self.log_path, "w", "utf-8")

    def write(self, text, color=None, bold=False, newline=False, stdout=True):
        suffix = "\n" if newline else ""
        self.logfile.write(text + suffix)
        if stdout:
            sys.stdout.write(colorize(text, color, bold) + suffix)
        self.flush()

    def flush(self):
        self.logfile.flush()
        sys.stdout.flush()

    def debug(self, message, *args):
        self.write(message % args,
                   newline=True,
                   color=GREEN,
                   stdout=not self.args.quiet)

    def info(self, message, *args):
        self.write(message % args,
                   newline=True,
                   stdout=not self.args.quiet)

    def notice(self, message, *args):
        self.write(message % args,
                   newline=True,
                   color=BLUE,
                   bold=True,
                   stdout=not self.args.quiet)

    def warning(self, message, *args):
        self.write(message % args,
                   newline=True,
                   color=YELLOW,
                   bold=True)

    def critical(self, message, *args):
        self.write(message % args,
                   newline=True,
                   color=RED,
                   bold=True)

    def close(self):
        self.logfile.close()


def register(config, args, deployer, log):
    @deployer.push_began
    def on_push_began(deployer):
        user = getpass.getuser()
        time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        log.write("Push started by %s at %s "
                  "UTC with args: %s" % (user, time, args.command_line),
                  newline=True, stdout=False)

########NEW FILE########
__FILENAME__ = main
import sys
import os.path

import push.config
import push.args
import push.log
import push.deploy
import push.syslog
import push.irc
import push.cli


def main():
    host_source = None

    try:
        # read in the various configs and arguments and get ready
        try:
            config = push.config.parse_config()
            host_source = push.hosts.make_host_source(config)
            args = push.args.parse_args(config, host_source)

            if args.list_hosts:
                for host in args.hosts:
                    print host
                return 0

            log = push.log.Log(config, args)
        except (push.config.ConfigurationError, push.args.ArgumentError,
                push.hosts.HostOrAliasError, push.hosts.HostLookupError), e:
            print >> sys.stderr, "%s: %s" % (os.path.basename(sys.argv[0]), e)
            return 1
        else:
            deployer = push.deploy.Deployer(config, args, log, host_source)

        # set up listeners
        push.log.register(config, args, deployer, log)
        push.syslog.register(config, args, deployer, log)
        push.irc.register(config, args, deployer, log)
        push.cli.register(config, args, deployer, log)

        # go
        try:
            deployer.push()
        except push.deploy.PushAborted:
            pass
        except Exception, e:
            log.critical("Push failed: %s", e)
            return 1
        finally:
            log.close()

        return 0
    finally:
        if host_source:
            host_source.shut_down()

if __name__ == "__main__":
    sys.exit(main())

########NEW FILE########
__FILENAME__ = ssh
import select
import getpass
import paramiko


# hack to add paramiko support for AES encrypted private keys
if "AES-128-CBC" not in paramiko.PKey._CIPHER_TABLE:
    from Crypto.Cipher import AES
    paramiko.PKey._CIPHER_TABLE["AES-128-CBC"] = dict(cipher=AES, keysize=16, blocksize=16, mode=AES.MODE_CBC)


class SshError(Exception):
    def __init__(self, code):
        self.code = code

    def __str__(self):
        return "remote command exited with code %d" % self.code


class SshConnection(object):
    def __init__(self, config, log, host):
        self.config = config
        self.log = log
        self.host = host

        self.client = paramiko.SSHClient()
        if not config.ssh.strict_host_key_checking:
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host,
                            username=config.ssh.user,
                            timeout=config.ssh.timeout,
                            pkey=config.ssh.pkey)

    def execute_command(self, command, display_output=False):
        transport = self.client.get_transport()
        channel = transport.open_session()
        channel.settimeout(self.config.ssh.timeout)
        channel.set_combine_stderr(True)
        channel.exec_command(command)
        channel.shutdown_write()

        output = []
        while True:
            readable = select.select([channel], [], [])[0]

            if not readable:
                continue

            received = channel.recv(1024)
            if not received:
                break

            received = unicode(received, "utf-8")

            output.append(received)

            if display_output:
                self.log.write(received, newline=False)

        status_code = channel.recv_exit_status()
        if status_code != 0:
            raise SshError(status_code)

        return "".join(output)

    def close(self):
        self.client.close()


class SshDeployer(object):
    """Executes deploy commands on remote systems using SSH. If multiple
    commands are run on the same host in succession, the same connection is
    reused for each."""

    def __init__(self, config, args, log):
        self.config = config
        self.args = args
        self.log = log
        self.current_connection = None

        config.ssh.pkey = None
        if not config.ssh.key_filename:
            return

        key_classes = (paramiko.RSAKey, paramiko.DSSKey)
        for key_class in key_classes:
            try:
                config.ssh.pkey = key_class.from_private_key_file(
                                                config.ssh.key_filename)
            except paramiko.PasswordRequiredException:
                need_password = True
                break
            except paramiko.SSHException:
                continue
            else:
                need_password = False
                break
        else:
            raise SshError("invalid key file %s" % config.ssh.key_filename)

        tries_remaining = 3
        while need_password and tries_remaining:
            password = getpass.getpass("password for %s: " %
                                       config.ssh.key_filename)

            try:
                config.ssh.pkey = key_class.from_private_key_file(
                                                config.ssh.key_filename,
                                                password=password)
                need_password = False
            except paramiko.SSHException:
                tries_remaining -= 1

        if need_password and not tries_remaining:
            raise SshError("invalid password.")

    def shutdown(self):
        if self.current_connection:
            self.current_connection.close()
            self.current_connection = None

    def _get_connection(self, host):
        if self.current_connection and self.current_connection.host != host:
            self.current_connection.close()
            self.current_connection = None
        self.current_connection = SshConnection(self.config, self.log, host)
        return self.current_connection

    def _run_command(self, host, binary, *args, **kwargs):
        command = " ".join(("/usr/bin/sudo", binary) + args)
        self.log.debug(command)

        if not self.args.testing:
            conn = self._get_connection(host)
            display_output = kwargs.get("display_output", True)
            return conn.execute_command(command, display_output=display_output)
        else:
            return "TESTING"

    def run_build_command(self, *args, **kwargs):
        return self._run_command(self.config.deploy.build_host,
                                 self.config.deploy.build_binary,
                                 *args, **kwargs)

    def run_deploy_command(self, host, *args, **kwargs):
        return self._run_command(host,
                                 self.config.deploy.deploy_binary,
                                 *args, **kwargs)

########NEW FILE########
__FILENAME__ = syslog
from __future__ import absolute_import

import syslog
import getpass


def register(config, args, deployer, log):
    def write_syslog(message):
        syslog.syslog(config.syslog.priority, message.encode('utf-8'))

    syslog.openlog(ident=config.syslog.ident, facility=config.syslog.facility)

    @deployer.push_began
    def on_push_began(deployer):
        user = getpass.getuser()
        write_syslog('Push %s started by '
                     '%s with args "%s"' % (args.push_id, user,
                                            args.command_line))

    @deployer.push_ended
    def on_push_ended(deployer):
        write_syslog("Push %s complete!" % args.push_id)

    @deployer.push_aborted
    def on_push_aborted(deployer, exception):
        write_syslog("Push %s aborted (%s)" % (args.push_id, exception))

########NEW FILE########
__FILENAME__ = utils
import hashlib
import os
import random


def get_random_word(config):
    file_size = os.path.getsize(config.paths.wordlist)
    word = ""

    with open(config.paths.wordlist, "r") as wordlist:
        while not word.isalpha() or not word.islower() or len(word) < 5:
            position = random.randint(1, file_size)
            wordlist.seek(position)
            wordlist.readline()
            word = unicode(wordlist.readline().rstrip("\n"), 'utf-8')

    return word


def seeded_shuffle(seedword, list):
    list.sort(key=lambda h: hashlib.md5(seedword + h).hexdigest())

########NEW FILE########
