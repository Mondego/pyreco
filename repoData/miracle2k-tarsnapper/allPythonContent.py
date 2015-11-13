__FILENAME__ = simulate
#!/usr/bin/env python

import sys
from os import path
sys.path.insert(0, path.join(path.dirname(__file__), 'src'))

from datetime import timedelta

from tarsnapper.test import BackupSimulator
from tarsnapper.config import parse_deltas


def main(argv):
    s = BackupSimulator(parse_deltas('1d 7d 30d'))

    until = s.now + timedelta(days=17)
    while s.now <= until:
        s.go_by(timedelta(days=1))
        s.backup()

    for name, date in s.backups.iteritems():
        print name


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
########NEW FILE########
__FILENAME__ = config
"""Deal with jobs defined in a config file. The format is YAML that looks
like this:

    # Global values, valid for all jobs unless overridden:
    deltas: 1d 7d 30d
    target: /localmachine/$name-$date

    jobs:
      images:
        source: /home/michael/Images

      some-other-job:
        sources:
          - /var/dir/1
          - /etc/google
        target: /custom-target-$date.zip
        deltas: 1h 6h 1d 7d 24d 180d

"""

from datetime import timedelta
from string import Template
import yaml


__all__ = ('Job', 'load_config', 'load_config_from_file', 'ConfigError',)


class ConfigError(Exception):
    pass


class Job(object):
    """Represent a single backup job.
    """

    def __init__(self, **initial):
        self.name = initial.get('name')
        self.aliases = initial.get('aliases')
        self.target = initial.get('target')
        self.dateformat = initial.get('dateformat')
        self.deltas = initial.get('deltas')
        self.sources = initial.get('sources')
        self.excludes = initial.get('excludes', [])
        self.force = initial.get('force')
        self.exec_before = initial.get('exec_before')
        self.exec_after = initial.get('exec_after')


def require_placeholders(text, placeholders, what):
    """Ensure that ``text`` contains the given placeholders.

    Raises a ``ConfigError`` using ``what`` in the message, or returns
    the unmodified text.
    """
    if not text is None:
        for var in placeholders:
            if Template(text).safe_substitute({var: 'foo'}) == text:
                raise ConfigError(('%s must make use of the following '
                                   'placeholders: %s') % (
                                       what, ", ".join(placeholders)))
    return text


def str_to_timedelta(text):
    """Parse a string to a timedelta value.
    """
    if text.endswith('s'):
        return timedelta(seconds=int(text[:-1]))
    elif text.endswith('h'):
        return timedelta(seconds=int(text[:-1]) * 3600)
    elif text.endswith('d'):
        return timedelta(days=int(text[:-1]))
    raise ValueError(text)


def parse_deltas(delta_string):
    """Parse the given string into a list of ``timedelta`` instances.
    """
    if delta_string is None:
        return None

    deltas = []
    for item in delta_string.split(' '):
        item = item.strip()
        if not item:
            continue
        try:
            deltas.append(str_to_timedelta(item))
        except ValueError, e:
            raise ConfigError('Not a valid delta: %s' % e)

    if deltas and len(deltas) < 2:
        raise ConfigError('At least two deltas are required')

    return deltas


def load_config(text):
    """Load the config file and return a dict of jobs, with the local
    and global configurations merged.
    """
    config = yaml.load(text)

    default_dateformat = config.pop('dateformat', None)
    default_deltas = parse_deltas(config.pop('deltas', None))
    default_target = require_placeholders(config.pop('target', None),
                                          ['name', 'date'], 'The global target')

    read_jobs = {}
    jobs_section = config.pop('jobs')
    if not jobs_section:
        raise ConfigError('config must define at least one job')
    for job_name, job_dict in jobs_section.iteritems():
        job_dict = job_dict or {}
        # sources
        if 'sources' in job_dict and 'source' in job_dict:
            raise ConfigError(('%s: Use either the "source" or "sources" '+
                              'option, not both') % job_name)
        if 'source' in job_dict:
            sources = [job_dict.pop('source')]
        else:
            sources = job_dict.pop('sources', None)
        # aliases
        if 'aliases' in job_dict and 'alias' in job_dict:
            raise ConfigError(('%s: Use either the "alias" or "aliases" '+
                              'option, not both') % job_name)
        if 'alias' in job_dict:
            aliases = [job_dict.pop('alias')]
        else:
            aliases = job_dict.pop('aliases', None)
        # excludes
        if 'excludes' in job_dict and 'exclude' in job_dict:
            raise ConfigError(('%s: Use either the "excludes" or "exclude" '+
                              'option, not both') % job_name)
        if 'exclude' in job_dict:
            excludes = [job_dict.pop('exclude')]
        else:
            excludes = job_dict.pop('excludes', [])
        new_job = Job(**{
            'name': job_name,
            'sources': sources,
            'aliases': aliases,
            'excludes': excludes,
            'target': job_dict.pop('target', default_target),
            'force': job_dict.pop('force', False),
            'deltas': parse_deltas(job_dict.pop('deltas', None)) or default_deltas,
            'dateformat': job_dict.pop('dateformat', default_dateformat),
            'exec_before': job_dict.pop('exec_before', None),
            'exec_after': job_dict.pop('exec_after', None),
        })
        if not new_job.target:
            raise ConfigError('%s does not have a target name' % job_name)
        # Note: It's ok to define jobs without sources or deltas. Those
        # can only be used for selected commands, then.
        require_placeholders(new_job.target, ['date'], '%s: target')
        if job_dict:
            raise ConfigError('%s has unsupported configuration values: %s' % (
                job_name, ", ".join(job_dict.keys())))

        read_jobs[job_name] = new_job

    # Return jobs, and all global keys not popped
    return read_jobs, config


def load_config_from_file(filename):
    f = open(filename, 'rb')
    try:
        return load_config(f.read())
    finally:
        f.close()

########NEW FILE########
__FILENAME__ = expire
import operator
from datetime import datetime, timedelta


__all__ = ('expire',)


def timedelta_div(td1, td2):
    """http://stackoverflow.com/questions/865618/how-can-i-perform-divison-on-a-datetime-timedelta-in-python
    """
    us1 = td1.microseconds + 1000000 * (td1.seconds + 86400 * td1.days)
    us2 = td2.microseconds + 1000000 * (td2.seconds + 86400 * td2.days)
    return float(us1) / us2


def expire(backups, deltas):
    """Given a dict of backup name => backup timestamp pairs in
    ``backups``, and a list of ``timedelta`` objects in ``deltas`` defining
    the generations, will decide which of the backups can be deleted using
    a grandfather-father-son backup strategy.

    The approach chosen tries to achieve the following:

    * Do not require backup names to include information on which generation
      a backup belongs to, like for example ``tarsnap-generations`` does.
      That is, you can create your backups anyway you wish, and simply use
      this utility to delete old backups.

    * Do not use any fixed generations (weekly, monthly etc), but freeform
      timespans.

    * Similarily, do not make any assumptions about when or if backup jobs
      have actually run or will run, but try to match the given deltas as
      closely as possible.

    What the code actually does is, for each generation, start at a fixed
    point in time determined by the most recent backup (which is always
    kept) plus the parent generation's delta and then repeatedly stepping
    the generation's delta forwards in time, chosing a backup that fits
    best which will then be kept.

    Returned is a list of backup names.
    """

    # Deal with some special cases
    assert len(deltas) >= 2, "At least two deltas are required"
    if not backups:
        return []

    # First, sort the backups with most recent one first
    backups = [(name, time) for name, time in backups.items()]
    backups.sort(cmp=lambda x, y: -cmp(x[1], y[1]))
    old_backups = backups[:]

    # Also make sure that we have the deltas in ascending order
    deltas = list(deltas[:])
    deltas.sort()

    # Always keep the most recent backup
    most_recent_backup = backups[0][1]
    to_keep = set([backups[0][0]])

    # Then, for each delta/generation, determine which backup to keep
    last_delta = deltas.pop()
    while deltas:
        current_delta = deltas.pop()

        # (1) Start from the point in time where the current generation ends.
        dt_pointer = most_recent_backup - last_delta
        last_selected = None
        while dt_pointer < most_recent_backup:
            # (2) Find the backup that matches the current position best.
            # We have different options here: Take the closest older backup,
            # take the closest newer backup, or just take the closest backup
            # in general. We do the latter. The difference is merely in how
            # long the oldest backup in each generation should be kept, that
            # is, how the given deltas should be interpreted.
            by_dist = sorted([(bn, bd, abs(bd - dt_pointer)) for bn, bd in backups], key=operator.itemgetter(2))
            if by_dist:
                if by_dist[0][0] == last_selected:
                    # If the time diff between two backups is larger than
                    # the delta, it can happen that multiple iterations of
                    # this loop determine the same backup to be closest.
                    # In this case, to avoid looping endlessly, we need to
                    # force the date pointer to move forward.
                    dt_pointer += current_delta
                else:
                    last_selected = by_dist[0][0]
                    to_keep.add(by_dist[0][0])
                    # (3) Proceed forward in time, jumping by the current
                    # generation's delta.
                    dt_pointer = by_dist[0][1] + current_delta
            else:
                # No more backups found in this generation.
                break

        last_delta = current_delta

    return list(to_keep)

########NEW FILE########
__FILENAME__ = script
import json
import sys, os
from os import path
import urllib2
import uuid
import subprocess
from StringIO import StringIO
import re
from string import Template
from datetime import datetime, timedelta
import logging
import argparse

import expire, config
from config import Job


class ArgumentError(Exception):
    pass


class TarsnapError(Exception):
    pass


class TarsnapBackend(object):
    """The code that calls the tarsnap executable.

    One of the reasons this is designed as a class is to allow the backend
    to mimimize the calls to "tarsnap --list-archives" by caching the result.
    """

    def __init__(self, log, options, dryrun=False):
        """
        ``options`` - options to pass to each tarsnap call
        (a list of key value pairs).

        In ``dryrun`` mode, will class will only pretend to make and/or
        delete backups. This is a global option rather than a method
        specific one, because once the cached list of archives is tainted
        with simulated data, you don't really want to run in non-dry mode.
        """
        self.log = log
        self.options = options
        self.dryrun = dryrun
        self._queried_archives = None
        self._known_archives = []

    def call(self, *arguments):
        """
        ``arguments`` is a single list of strings.
        """
        call_with = ['tarsnap']
        for option in self.options:
            key = option[0]
            pre = "-" if len(key) == 1 else "--"
            call_with.append("%s%s" % (pre, key))
            for value in option[1:]:
                call_with.append(value)
        call_with.extend(arguments)
        return self._exec_tarsnap(call_with)

    def _exec_tarsnap(self, args):
        self.log.debug("Executing: %s" % " ".join(args))
        p = subprocess.Popen(args, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        if p.returncode != 0:
            raise TarsnapError('%s' % stderr)
        return stdout

    def _exec_util(self, cmdline, shell=False):
        # TODO: can this be merged with _exec_tarsnap into something generic?
        self.log.debug("Executing: %s" % cmdline)
        p = subprocess.Popen(cmdline, shell=True)
        p.communicate()
        if p.returncode:
            raise RuntimeError('%s failed with exit code %s' % (
                cmdline, p.returncode))

    def _add_known_archive(self, name):
        """If we make a backup, store it's name in a separate list.

        This list can be combined with the one read from the server. This
        means that when we create a new backup, we subsequently don't need
        to requery the server.
        """
        self._known_archives.append(name)

    def get_archives(self):
        """A list of archives as returned by --list-archives. Queried
        the first time it is accessed, and then subsequently cached.
        """
        if self._queried_archives is None:
            response = StringIO(self.call('--list-archives'))
            self._queried_archives = [l.rstrip() for l in response.readlines()]
        return self._queried_archives + self._known_archives
    archives = property(get_archives)

    def get_backups(self, job):
        """Return a dict of backups that exist for the given job, by
        parsing the list of archives.
        """
        # Assemble regular expressions that matche the job's target
        # filenames, including those based on it's aliases.
        unique = uuid.uuid4().hex
        regexes = []
        for possible_name in [job.name] + (job.aliases or []):
            target = Template(job.target).substitute(
                {'name': possible_name, 'date': unique})
            regexes.append(re.compile("^%s$" %
                        re.escape(target).replace(unique, '(?P<date>.*?)')))

        backups = {}
        for backup_path in self.get_archives():
            match = None
            for regex in regexes:
                match = regex.match(backup_path)
                if match:
                    break
            else:
                # Not one of the regexes matched.
                continue
            try:
                date = parse_date(match.groupdict()['date'], job.dateformat)
            except ValueError, e:
                # This can occasionally happen when multiple archives
                # share a prefix, say for example you have "windows-$date"
                # and "windows-data-$date". Since we have to use a generic
                # .* regex to capture the date part, when processing the
                # "windows-$date" targets, we'll stumble over entries where
                # we try to parse "data-$date" as a date. Make sure we
                # only print a warning, rather than crashing.
                # TODO: It'd take some work, but we could build a proper
                # regex based on any given date format string, thus avoiding
                # the issue for most cases.
                self.log.error("Ignoring '%s': %s" % (backup_path, e))
            else:
                backups[backup_path] = date

        return backups

    def expire(self, job):
        """Have tarsnap delete those archives which we need to expire
        according to the deltas defined.

        If a dry run is wanted, set ``dryrun`` to a dict of the backups to
        pretend that exist (they will always be used, and not matched).
        """

        backups = self.get_backups(job)
        self.log.info('%d backups are matching' % len(backups))

        # Determine which backups we need to get rid of, which to keep
        to_keep = expire.expire(backups, job.deltas)
        self.log.info('%d of those can be deleted' % (len(backups)-len(to_keep)))

        # Delete all others
        for name, _ in backups.items():
            if not name in to_keep:
                self.log.info('Deleting %s' % name)
                if not self.dryrun:
                    self.call('-d', '-f', name)
                self.archives.remove(name)
            else:
                self.log.debug('Keeping %s' % name)

    def make(self, job):
        now = datetime.utcnow()
        date_str = now.strftime(job.dateformat or DEFAULT_DATEFORMAT)
        target = Template(job.target).safe_substitute(
            {'date': date_str, 'name': job.name})

        if job.name:
            self.log.info('Creating backup %s: %s' % (job.name, target))
        else:
            self.log.info('Creating backup: %s' % target)

        if not self.dryrun:
            args = ['-c']
            [args.extend(['--exclude', e]) for e in job.excludes]
            args.extend(['-f', target])
            args.extend(job.sources)
            self.call(*args)
        # Add the new backup the list of archives, so we have an up-to-date
        # list without needing to query again.
        self._add_known_archive(target)

        return target, now


DEFAULT_DATEFORMAT = '%Y%m%d-%H%M%S'

DATE_FORMATS = (
    DEFAULT_DATEFORMAT,
    '%Y%m%d-%H%M',
)


def parse_date(string, dateformat=None):
    """Parse a date string using either a list of builtin formats,
    or the given one.
    """
    for to_try in ([dateformat] if dateformat else DATE_FORMATS):
        try:
            return datetime.strptime(string, to_try)
        except ValueError:
            pass
    else:
        raise ValueError('"%s" is not a supported date format' % string)


def timedelta_string(value):
    """Parse a string to a timedelta value.
    """
    try:
        return config.str_to_timedelta(value)
    except ValueError, e:
        raise argparse.ArgumentTypeError('invalid delta value: %r (suffix d, s allowed)' % e)


class XpectIOPlugin(object):
    """Integrates with xpect.io.
    """

    def __init__(self):
        # get access key from ENV
        self.env_key = os.environ.get('XPECTIO_ACCESS_KEY', None)

    def setup_arg_parser(self, parser):
        parser.add_argument('--xpect', help='xpect.io url')
        parser.add_argument('--xpect-key', help='xpect.io access key')

    def all_jobs_done(self, args, config, cmd):
        if not cmd in (MakeCommand, ExpireCommand):
            return

        access_key = config.get('xpect-key', args.xpect_key or self.env_key)
        url = config.get('xpect', args.xpect)

        if url:
            if not access_key:
                raise RuntimeError('Cannot notify xpect.io, no access key set')

            urllib2.urlopen(
                urllib2.Request(
                    url=url,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Access-Key': access_key,
                    },
                    data=json.dumps({
                        'action': 'eventSuccess'
                    })
                )
            )


class Command(object):

    BackendClass = TarsnapBackend

    def __init__(self, args, log, backend_class=None):
        self.args = args
        self.log = log
        self.backend = (backend_class or self.BackendClass)(
            self.log, self.args.tarsnap_options,
            dryrun=getattr(self.args, 'dryrun', False))

    @classmethod
    def setup_arg_parser(self, parser):
        pass

    @classmethod
    def validate_args(self, args):
        pass

    def run(self, job):
        raise NotImplementedError()


class ListCommand(Command):

    help = 'list all the existing backups'
    description = 'For each job, output a sorted list of existing backups.'

    def run(self, job):
        backups = self.backend.get_backups(job)

        self.log.info('%s' % job.name)

        # Sort backups by time
        # TODO: This duplicates code from the expire module. Should
        # the list of backups always be returned sorted instead?
        backups = [(name, time) for name, time in backups.items()]
        backups.sort(cmp=lambda x, y: -cmp(x[1], y[1]))
        for backup, _ in backups:
            print "  %s" % backup


class ExpireCommand(Command):

    help = 'delete old backups, but don\'t create a new one'
    description = 'For each job defined, determine which backups can ' \
                  'be deleted according to the deltas, and then delete them.'

    @classmethod
    def setup_arg_parser(self, parser):
        parser.add_argument('--dry-run', dest='dryrun', action='store_true',
                            help='only simulate, don\'t delete anything')

    def expire(self, job):
        if not job.deltas:
            self.log.info(("Skipping '%s', does not define deltas") % job.name)
            return

        self.backend.expire(job)

    def run(self, job):
        self.expire(job)


class MakeCommand(ExpireCommand):

    help = 'create a new backup, and afterwards expire old backups'
    description = 'For each job defined, make a new backup, then ' \
                  'afterwards delete old backups no longer required. '\
                  'If you need only the latter, see the separate ' \
                  '"expire" command.'

    @classmethod
    def setup_arg_parser(self, parser):
        parser.add_argument('--dry-run', dest='dryrun', action='store_true',
                            help='only simulate, make no changes',)
        parser.add_argument('--no-expire', dest='no_expire',
                            action='store_true', default=None,
                            help='don\'t expire, only make backups')

    @classmethod
    def validate_args(self, args):
        if not args.config and not args.target:
            raise ArgumentError('Since you are not using a config file, '\
                                'you need to give --target')
        if not args.config and not args.deltas and not args.no_expire:
            raise ArgumentError('Since you are not using a config file, and '\
                                'have not specified --no-expire, you will '
                                'need to give --deltas')
        if not args.config and not args.sources:
            raise ArgumentError('Since you are not using a config file, you '
                                'need to specify at least one source path '
                                'using --sources')

    def run(self, job):
        if not job.sources:
            self.log.info(("Skipping '%s', does not define sources") % job.name)
            return

        if job.exec_before:
            self.backend._exec_util(job.exec_before)

        # Determine whether we can run this job. If any of the sources
        # are missing, or any source directory is empty, we skip this job.
        sources_missing = False
        if not job.force:
            for source in job.sources:
                if not path.exists(source):
                    sources_missing = True
                    break
                if path.isdir(source) and not os.listdir(source):
                    # directory is empty
                    sources_missing = True
                    break

        # Do a new backup
        skipped = False

        if sources_missing:
            if job.name:
                self.log.info(("Not backing up '%s', because not all given "
                               "sources exist") % job.name)
            else:
                self.log.info("Not making backup, because not all given "
                              "sources exist")
            skipped = True
        else:
            try:
                self.backend.make(job)
            except Exception:
                self.log.exception(("Something went wrong with backup job: '%s'")
                               % job.name)

        if job.exec_after:
            self.backend._exec_util(job.exec_after)

        # Expire old backups, but only bother if either we made a new
        # backup, or if expire was explicitly requested.
        if not skipped and not self.args.no_expire:
            self.expire(job)


COMMANDS = {
    'make': MakeCommand,
    'expire': ExpireCommand,
    'list': ListCommand,
}


PLUGINS = [
    XpectIOPlugin()
]


def parse_args(argv):
    """Parse the command line.
    """
    parser = argparse.ArgumentParser(
        description='An interface to tarsnap to manage backups.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-q', action='store_true', dest='quiet', help='be quiet')
    group.add_argument('-v', action='store_true', dest='verbose', help='be verbose')
    # We really want nargs=(1,2), but since this isn't available, we can
    # just asl well support an arbitrary number of values for each -o.
    parser.add_argument('-o', metavar=('name', 'value'), nargs='+',
                        dest='tarsnap_options', default=[], action='append',
                        help='option to pass to tarsnap',)
    parser.add_argument('--config', '-c', help='use the given config file')

    group = parser.add_argument_group(
        description='Instead of using a configuration file, you may define '\
                    'a single job on the command line:')
    group.add_argument('--target', help='target filename for the backup')
    group.add_argument('--sources', nargs='+', help='paths to backup',
                        default=[])
    group.add_argument('--deltas', '-d', metavar='DELTA',
                        type=timedelta_string,
                        help='generation deltas', nargs='+')
    group.add_argument('--dateformat', '-f', help='dateformat')

    for plugin in PLUGINS:
        plugin.setup_arg_parser(parser)

    # This will allow the user to break out of an nargs='*' to start
    # with the subcommand. See http://bugs.python.org/issue9571.
    parser.add_argument('-', dest='__dummy', action="store_true",
                        help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(
        title="commands", description="commands may offer additional options")
    for cmd_name, cmd_klass in COMMANDS.iteritems():
        subparser = subparsers.add_parser(cmd_name, help=cmd_klass.help,
                                          description=cmd_klass.description,
                                          add_help=False)
        subparser.set_defaults(command=cmd_klass)
        group = subparser.add_argument_group(
            title="optional arguments for this command")
        # We manually add the --help option so that we can have a
        # custom group title, but only show a single group.
        group.add_argument('-h', '--help', action='help',
                           default=argparse.SUPPRESS,
                           help='show this help message and exit')
        cmd_klass.setup_arg_parser(group)

        # Unfortunately, we need to redefine the jobs argument for each
        # command, rather than simply having it once, globally.
        subparser.add_argument(
            'jobs', metavar='job', nargs='*',
            help='only process the given job as defined in the config file')

    # This would be in a group automatically, but it would be shown as
    # the very first thing, while it really should be the last (which
    # explicitly defining the group causes to happen).
    #
    # Also, note that we define this argument for each command as well,
    # and the command specific one will actually be parsed. This is
    # because while argparse allows us to *define* this argument globally,
    # and renders the usage syntax correctly as well, it isn't actually
    # able to parse the thing it correctly (see
    # http://bugs.python.org/issue9540).
    group = parser.add_argument_group(title='positional arguments')
    group.add_argument(
        '__not_used', metavar='job', nargs='*',
        help='only process the given job as defined in the config file')

    args = parser.parse_args(argv)

    # Do some argument validation that would be to much to ask for
    # argparse to handle internally.
    if args.config and (args.target or args.dateformat or args.deltas or
                        args.sources):
        raise ArgumentError('If --config is used, then --target, --deltas, '
                            '--sources and --dateformat are not available')
    if args.jobs and not args.config:
        raise ArgumentError(('Specific jobs (%s) can only be given if a '
                            'config file is used') % ", ".join(args.jobs))
    # The command may want to do some validation regarding it's own options.
    args.command.validate_args(args)

    return args


def main(argv):
    try:
        args = parse_args(argv)
    except ArgumentError, e:
        print "Error: %s" % e
        return 1

    # Setup logging
    level = logging.WARNING if args.quiet else (
        logging.DEBUG if args.verbose else logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(message)s"))
    log = logging.getLogger()
    log.setLevel(level)
    log.addHandler(ch)

    # Build a list of jobs, process them.
    if args.config:
        try:
            jobs, global_config = config.load_config_from_file(args.config)
        except config.ConfigError, e:
            log.fatal('Error loading config file: %s' % e)
            return 1
    else:
        # Only a single job, as given on the command line
        jobs = {None: Job(**{'target': args.target, 'dateformat': args.dateformat,
                             'deltas': args.deltas, 'sources': args.sources})}
        global_config = {}

    # Validate the requested list of jobs to run
    if args.jobs:
        unknown = set(args.jobs) - set(jobs.keys())
        if unknown:
            log.fatal('Error: not defined in the config file: %s' % ", ".join(unknown))
            return 1
        jobs_to_run = dict([(n, j) for n, j in jobs.iteritems() if n in args.jobs])
    else:
        jobs_to_run = jobs

    command = args.command(args, log)
    try:
        for job in jobs_to_run.values():
            command.run(job)

        for plugin in PLUGINS:
            plugin.all_jobs_done(args, global_config, args.command)
    except TarsnapError, e:
        log.fatal("tarsnap execution failed:\n%s" % e)
        return 1


def run():
    sys.exit(main(sys.argv[1:]) or 0)


if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = test
from datetime import datetime
from expire import expire as default_expire_func
from config import parse_deltas


__all__ = ('BackupSimulator',)


try:
    from collections import OrderedDict    # Python 2.7
except ImportError:
    # Install from: http://pypi.python.org/pypi/ordereddict
    from ordereddict import OrderedDict


class BackupSimulator(object):
    """Helper to simulate making backups, and expire old ones, at
    various points in time.
    """

    def __init__(self, deltas, expire_func=default_expire_func):
        if isinstance(deltas, basestring):
            deltas = parse_deltas(deltas)
        self.deltas = deltas
        self.expire_func = expire_func
        self.now = datetime.now()
        self.backups = OrderedDict()

    def add(self, backups):
        for dt in backups:
            if isinstance(dt, basestring):
                dt = datetime.strptime(dt, "%Y%m%d-%H%M%S")
            self.backups[str(dt)] = dt

    def go_to(self, dt):
        self.now = dt

    def go_by(self, td):
        self.now += td

    def backup(self, expire=True):
        self.add([self.now])
        if expire:
            return self.expire()

    def expire(self):
        keep = self.expire_func(self.backups, self.deltas)
        deleted = []
        for key in self.backups.keys():
            if not key in keep:
                deleted.append(key)
                del self.backups[key]
        return deleted, keep

########NEW FILE########
__FILENAME__ = test_config
from tarsnapper.config import load_config, ConfigError
from nose.tools import assert_raises


def test_empty_config():
    assert_raises(ConfigError, load_config, """
    deltas: 1d 2d
    jobs:
    """)
    assert_raises(ConfigError, load_config, """
    deltas: 1d 2d
    """)


def test_aliases():
    """Loading of the "alias" option."""
    assert load_config("""
    jobs:
      foo:
        target: foo-$date
        alias: foo
    """)['foo'].aliases == ['foo']
    assert load_config("""
    jobs:
      foo:
        target: foo-$date
        aliases:
          - foo
    """)['foo'].aliases == ['foo']


def test_excludes():
    """Loading of the "excludes" option."""
    assert load_config("""
    jobs:
      foo:
        target: foo-$date
        exclude: foo
    """)['foo'].excludes == ['foo']
    assert load_config("""
    jobs:
      foo:
        target: foo-$date
        excludes:
          - foo
    """)['foo'].excludes == ['foo']


def test_no_sources():
    # It's ok to load a backup job file without sources
    load_config("""
    jobs:
      foo:
        deltas: 1d 2d 3d
        target:  $date
    """)


def test_no_target():
    assert_raises(ConfigError, load_config, """
    jobs:
      foo:
        deltas: 1d 2d 3d
        sources: /etc
    """)


def test_global_target():
    assert load_config("""
    target: $name-$date
    jobs:
      foo:
        deltas: 1d 2d 3d
        sources: sdf
    """)['foo'].target == '$name-$date'


def test_empty_job():
    """An empty job may be valid in some cases."""
    assert load_config("""
    target: $name-$date
    jobs:
      foo:
    """)['foo']


def test_no_deltas():
    # It's ok to load a job without deltas
    load_config("""
    jobs:
      foo:
        sources: /etc
        target:  $date
    """)


def test_global_deltas():
    assert len(load_config("""
    deltas: 1d 2d 3d
    jobs:
      foo:
        sources: /etc
        target: $date
    """)['foo'].deltas) == 3


def test_target_has_name():
    assert_raises(ConfigError, load_config, """
    target: $date
    jobs:
      foo:
        sources: /etc
        deltas: 1d 2d
    """)

    # A job-specific target does not need a name placeholder
    load_config("""
    jobs:
      foo:
        sources: /etc
        deltas: 1d 2d
        target: $date
    """)


def test_target_has_date():
    assert_raises(ConfigError, load_config, """
    target: $name
    jobs:
      foo:
        sources: /etc
        deltas: 1d 2d
    """)
    assert_raises(ConfigError, load_config, """
    jobs:
      foo:
        target: $name
        sources: /etc
        deltas: 1d 2d
    """)


def test_dateformat_inheritance():
    r = load_config("""
    dateformat: ABC
    target: $name-$date
    deltas: 1d 2d
    jobs:
      foo:
        sources: /etc
      bar:
        sources: /usr
        dateformat: "123"
    """)
    assert r['foo'].dateformat == 'ABC'
    assert r['bar'].dateformat == '123'


def test_unsupported_keys():
    assert_raises(ConfigError, load_config, """
    jobs:
      foo:
        target: $date
        sources: /etc
        deltas: 1d 2d
        UNSUPPORTED: 123
    """)


def test_single_source():
    assert load_config("""
    target: $name-$date
    deltas: 1d 2d
    jobs:
      foo:
        source: /etc
    """)['foo'].sources == ['/etc']


def test_source_and_sources():
    """You can't use both options at the same time."""
    assert_raises(ConfigError, load_config, """
    target: $name-$date
    deltas: 1d 2d
    jobs:
      foo:
        source: /etc
        sources:
          /usr
          /var
    """)

def test_alias_and_aliases():
    """You can't use both options at the same time."""
    assert_raises(ConfigError, load_config, """
    target: $name-$date
    deltas: 1d 2d
    jobs:
      foo:
        alias: doo
        aliases:
          loo
          moo
    """)

def test_exclude_and_excludes():
    """You can't use both options at the same time."""
    assert_raises(ConfigError, load_config, """
    target: $name-$date
    deltas: 1d 2d
    jobs:
      foo:
        exclude: doo
        excludes:
          loo
          moo
    """)
########NEW FILE########
__FILENAME__ = test_expire
"""
XXX: How should test this? What exactly should be tested?
- Backups are deleted past the last generation
- At the end of each generation, most backups are deleted, but some
  are persisted. Try to write this as a test.
- Jumping a long time into the future -> stuff should be deleted.
"""

from tarsnapper.test import BackupSimulator

def test_failing_keep():
    """This used to delete backup B, because we were first looking
    for a seven day old backup, finding A, then looking for a six day
    old backup, finding A again (it is closer to six days old then B)
    and then stopping the search, assuming after two identical matches
    that there are no more.
    """
    s = BackupSimulator('1d 7d')
    s.add([
        '20100615-000000',   # A
        '20100619-000000',   # B
        '20100620-000000',   # C
    ])
    delete, keep = s.expire()
    assert not delete
########NEW FILE########
__FILENAME__ = test_script
from StringIO import StringIO
from os import path
import re
import shutil
import tempfile
import logging
import argparse
from datetime import datetime
from tarsnapper.script import (
    TarsnapBackend, MakeCommand, ListCommand, ExpireCommand, parse_args,
    DEFAULT_DATEFORMAT)
from tarsnapper.config import Job, parse_deltas, str_to_timedelta


class FakeBackend(TarsnapBackend):

    def __init__(self, *a, **kw):
        TarsnapBackend.__init__(self, *a, **kw)
        self.calls = []
        self.fake_archives = []

    def _exec_tarsnap(self, args):
        self.calls.append(args[1:])  # 0 is "tarsnap"
        if '--list-archives' in args:
            return StringIO("\n".join(self.fake_archives))

    def _exec_util(self, cmdline):
        self.calls.append(cmdline)

    def match(self, expect_calls):
        """Compare the calls we have captured with what the list of
        regexes in ``expect``.
        """
        print expect_calls, '==', self.calls
        if not len(expect_calls) == len(self.calls):
            return False
        for args, expected_args in zip(self.calls, expect_calls):
            # Each call has multiple arguments
            if not len(args) == len(expected_args):
                return False
            for actual, expected_re in zip(args, expected_args):
                if not re.match(expected_re, actual):
                    return False
        return True


class BaseTest(object):

    def setup(self):
        self.log = logging.getLogger("test_script")
        self._tmpdir = tempfile.mkdtemp()
        # We need at least a file for tarsnapper to consider a source
        # to "exist".
        open(path.join(self._tmpdir, '.placeholder'), 'w').close()
        self.now = datetime.utcnow()

    def teardown(self):
        shutil.rmtree(self._tmpdir)

    def run(self, jobs, archives, **args):
        final_args = {
            'tarsnap_options': (),
            'no_expire': False,
        }
        final_args.update(args)
        cmd = self.command_class(argparse.Namespace(**final_args),
                                 self.log, backend_class=FakeBackend)
        cmd.backend.fake_archives = archives
        for job in (jobs if isinstance(jobs, list) else [jobs]):
            cmd.run(job)
        return cmd

    def job(self, deltas='1d 2d', name='test', **kwargs):
        """Make a job object.
        """
        opts = dict(
            target="$name-$date",
            deltas=parse_deltas(deltas),
            name=name,
            sources=[self._tmpdir])
        opts.update(kwargs)
        return Job(**opts)

    def filename(self, delta, name='test', fmt='%s-%s'):
        return fmt % (
            name,
            (self.now - str_to_timedelta(delta)).strftime(DEFAULT_DATEFORMAT))


class TestTarsnapOptions(BaseTest):

    command_class = ExpireCommand

    def tset_parse(self):
        parse_args(['-o', 'name', 'foo', '-', 'list'])
        parse_args(['-o', 'name', '-', 'list'])
        parse_args(['-o', 'name', 'sdf', 'sdf', '-', 'list'])

    def test_pass_along(self):
        # Short option
        cmd = self.run(self.job(), [], tarsnap_options=(('o', '1'),))
        assert cmd.backend.match([('-o', '1', '--list-archives')])

        # Long option
        cmd = self.run(self.job(), [], tarsnap_options=(('foo', '1'),))
        assert cmd.backend.match([('--foo', '1', '--list-archives')])

        # No value
        cmd = self.run(self.job(), [], tarsnap_options=(('foo',),))
        assert cmd.backend.match([('--foo', '--list-archives')])

        # Multiple values
        cmd = self.run(self.job(), [], tarsnap_options=(('foo', '1', '2'),))
        assert cmd.backend.match([('--foo', '1', '2', '--list-archives')])


class TestMake(BaseTest):

    command_class = MakeCommand

    def test(self):
        cmd = self.run(self.job(), [])
        assert cmd.backend.match([
            ('-c', '-f', 'test-.*', '.*'),
            ('--list-archives',)
        ])

    def test_no_sources(self):
        """If no sources are defined, the job is skipped."""
        cmd = self.run(self.job(sources=None), [])
        assert cmd.backend.match([])

    def test_excludes(self):
        cmd = self.run(self.job(excludes=['foo']), [])
        assert cmd.backend.match([
            ('-c', '--exclude', 'foo', '-f', 'test-.*', '.*'),
            ('--list-archives',)
        ])

    def test_no_expire(self):
        cmd = self.run(self.job(), [], no_expire=True)
        assert cmd.backend.match([
            ('-c', '-f', 'test-.*', '.*'),
        ])

    def test_exec(self):
        """Test ``exec_before`` and ``exec_after`` options.
        """
        cmd = self.run(self.job(exec_before="echo begin", exec_after="echo end"),
                       [], no_expire=True)
        assert cmd.backend.match([
            ('echo begin'),
            ('-c', '-f', 'test-.*', '.*'),
            ('echo end'),
        ])


class TestExpire(BaseTest):

    command_class = ExpireCommand

    def test_nothing_to_do(self):
        cmd = self.run(self.job(deltas='1d 10d'), [
            self.filename('1d'),
            self.filename('5d'),
        ])
        assert cmd.backend.match([
            ('--list-archives',)
        ])

    def test_no_deltas(self):
        """If a job does not define deltas, we skip it."""
        cmd = self.run(self.job(deltas=None), [
            self.filename('1d'),
            self.filename('5d'),
        ])
        assert cmd.backend.match([])


    def test_something_to_expire(self):
        cmd = self.run(self.job(deltas='1d 2d'), [
            self.filename('1d'),
            self.filename('5d'),
        ])
        assert cmd.backend.match([
            ('--list-archives',),
            ('-d', '-f', 'test-.*'),
        ])

    def test_aliases(self):
        cmd = self.run(self.job(deltas='1d 2d', aliases=['alias']), [
            self.filename('1d'),
            self.filename('5d', name='alias'),
        ])
        assert cmd.backend.match([
            ('--list-archives',),
            ('-d', '-f', 'alias-.*'),
        ])

    def test_date_name_mismatch(self):
        """Make sure that when processing a target "home-$date",
        we won't stumble over "home-dev-$date". This can be an issue
        due to the way we try to parse the dates in filenames.
        """
        cmd = self.run(self.job(name="home"), [
            self.filename('1d', name="home-dev"),
        ])


class TestList(BaseTest):

    command_class = ListCommand

    def test(self):
        cmd = self.run([self.job(), self.job(name='foo')], [
            self.filename('1d'),
            self.filename('5d'),
            self.filename('1d', name='foo'),
            self.filename('1d', name='something-else'),
        ])
        # We ask to list two jobs, but only one --list-archives call is
        # necessary.
        assert cmd.backend.match([
            ('--list-archives',)
        ])
########NEW FILE########
