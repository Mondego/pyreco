__FILENAME__ = config
###
# Copyright (c) 2009, Mike Mueller
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Do whatever you want
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Git', True)

Git = conf.registerPlugin('Git')

conf.registerGlobalValue(Git, 'configFile',
    registry.String('git.ini', """The path to the repository configuration
        file."""))

conf.registerGlobalValue(Git, 'repoDir',
    registry.String('git_repositories', """The path where local copies of
        repositories will be kept."""))

conf.registerGlobalValue(Git, 'pollPeriod',
    registry.NonNegativeInteger(120, """The frequency (in seconds) repositories
        will be polled for changes.  Set to zero to disable polling."""))

conf.registerGlobalValue(Git, 'maxCommitsAtOnce',
    registry.NonNegativeInteger(5, """How many commits are displayed at
        once from each repository."""))

conf.registerGlobalValue(Git, 'shaSnarfing',
    registry.Boolean(True, """Look for SHAs in user messages written to the
       channel, and reply with the commit description if one is found."""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = plugin
###
# Copyright (c) 2011-2012, Mike Mueller <mike.mueller@panopticdev.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Do whatever you want
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

"""
A Supybot plugin that monitors and interacts with git repositories.
"""

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.schedule as schedule
import supybot.log as log
import supybot.world as world

import ConfigParser
from functools import wraps
import os
import threading
import time
import traceback

# 'import git' is performed during plugin initialization.
#
# The GitPython library has different APIs depending on the version installed.
# (0.1.x, 0.3.x supported)
GIT_API_VERSION = -1

def log_info(message):
    log.info("Git: " + message)

def log_warning(message):
    log.warning("Git: " + message)

def log_error(message):
    log.error("Git: " + message)

def plural(count, singular, plural=None):
    if count == 1:
        return singular
    if plural:
        return plural
    if singular[-1] == 's':
        return singular + 'es'
    if singular[-1] == 'y':
        return singular[:-1] + 'ies'
    return singular + 's'

def synchronized(tlockname):
    """
    Decorates a class method (with self as the first parameter) to acquire the
    member variable lock with the given name (e.g. 'lock' ==> self.lock) for
    the duration of the function (blocking).
    """
    def _synched(func):
        @wraps(func)
        def _synchronizer(self, *args, **kwargs):
            tlock = self.__getattribute__(tlockname)
            tlock.acquire()
            try:
                return func(self, *args, **kwargs)
            finally:
                tlock.release()
        return _synchronizer
    return _synched

class Repository(object):
    "Represents a git repository being monitored."

    def __init__(self, repo_dir, long_name, options):
        """
        Initialize with a repository with the given name and dict of options
        from the config section.
        """
        if GIT_API_VERSION == -1:
            raise Exception("Git-python API version uninitialized.")

        # Validate configuration ("channel" allowed for backward compatibility)
        required_values = ['short name', 'url']
        optional_values = ['branch', 'channel', 'channels', 'commit link',
                           'commit message', 'commit reply']
        for name in required_values:
            if name not in options:
                raise Exception('Section %s missing required value: %s' %
                        (long_name, name))
        for name, value in options.items():
            if name not in required_values and name not in optional_values:
                raise Exception('Section %s contains unrecognized value: %s' %
                        (long_name, name))

        # Initialize
        self.branch = 'origin/' + options.get('branch', 'master')
        self.channels = options.get('channels', options.get('channel')).split()
        self.commit_link = options.get('commit link', '')
        self.commit_message = options.get('commit message', '[%s|%b|%a] %m')
        self.commit_reply = options.get('commit reply', '')
        self.errors = []
        self.last_commit = None
        self.lock = threading.RLock()
        self.long_name = long_name
        self.short_name = options['short name']
        self.repo = None
        self.url = options['url']

        if not os.path.exists(repo_dir):
            os.makedirs(repo_dir)
        self.path = os.path.join(repo_dir, self.short_name)

        # TODO: Move this to GitWatcher (separate thread)
        self.clone()

    @synchronized('lock')
    def clone(self):
        "If the repository doesn't exist on disk, clone it."
        if not os.path.exists(self.path):
            git.Git('.').clone(self.url, self.path, no_checkout=True)
        self.repo = git.Repo(self.path)
        self.last_commit = self.repo.commit(self.branch)

    @synchronized('lock')
    def fetch(self):
        "Contact git repository and update last_commit appropriately."
        self.repo.git.fetch()

    @synchronized('lock')
    def get_commit(self, sha):
        "Fetch the commit with the given SHA.  Returns None if not found."
        try:
            return self.repo.commit(sha)
        except ValueError: # 0.1.x
            return None
        except git.GitCommandError: # 0.3.x
            return None

    @synchronized('lock')
    def get_commit_id(self, commit):
        if GIT_API_VERSION == 1:
            return commit.id
        elif GIT_API_VERSION == 3:
            return commit.hexsha
        else:
            raise Exception("Unsupported API version: %d" % GIT_API_VERSION)

    @synchronized('lock')
    def get_new_commits(self):
        if GIT_API_VERSION == 1:
            result = self.repo.commits_between(self.last_commit, self.branch)
        elif GIT_API_VERSION == 3:
            rev = "%s..%s" % (self.last_commit, self.branch)
            # Workaround for GitPython bug:
            # https://github.com/gitpython-developers/GitPython/issues/61
            self.repo.odb.update_cache()
            result = self.repo.iter_commits(rev)
        else:
            raise Exception("Unsupported API version: %d" % GIT_API_VERSION)
        self.last_commit = self.repo.commit(self.branch)
        return list(result)

    @synchronized('lock')
    def get_recent_commits(self, count):
        if GIT_API_VERSION == 1:
            return self.repo.commits(start=self.branch, max_count=count)
        elif GIT_API_VERSION == 3:
            return list(self.repo.iter_commits(self.branch))[:count]
        else:
            raise Exception("Unsupported API version: %d" % GIT_API_VERSION)

    @synchronized('lock')
    def format_link(self, commit):
        "Return a link to view a given commit, based on config setting."
        result = ''
        escaped = False
        for c in self.commit_link:
            if escaped:
                if c == 'c':
                    result += self.get_commit_id(commit)[0:7]
                elif c == 'C':
                    result += self.get_commit_id(commit)
                else:
                    result += c
                escaped = False
            elif c == '%':
                escaped = True
            else:
                result += c
        return result

    @synchronized('lock')
    def format_message(self, commit, format_str=None):
        """
        Generate an formatted message for IRC from the given commit, using
        the format specified in the config. Returns a list of strings.
        """
        MODE_NORMAL = 0
        MODE_SUBST = 1
        MODE_COLOR = 2
        subst = {
            'a': commit.author.name,
            'b': self.branch[self.branch.rfind('/')+1:],
            'c': self.get_commit_id(commit)[0:7],
            'C': self.get_commit_id(commit),
            'e': commit.author.email,
            'l': self.format_link(commit),
            'm': commit.message.split('\n')[0],
            'n': self.long_name,
            's': self.short_name,
            'u': self.url,
            'r': '\x0f',
            '!': '\x02',
            '%': '%',
        }
        result = []
        if not format_str:
            format_str = self.commit_message
        lines = format_str.split('\n')
        for line in lines:
            mode = MODE_NORMAL
            outline = ''
            for c in line:
                if mode == MODE_SUBST:
                    if c in subst.keys():
                        outline += subst[c]
                        mode = MODE_NORMAL
                    elif c == '(':
                        color = ''
                        mode = MODE_COLOR
                    else:
                        outline += c
                        mode = MODE_NORMAL
                elif mode == MODE_COLOR:
                    if c == ')':
                        outline += '\x03' + color
                        mode = MODE_NORMAL
                    else:
                        color += c
                elif c == '%':
                    mode = MODE_SUBST
                else:
                    outline += c
            result.append(outline.encode('utf-8'))
        return result

    @synchronized('lock')
    def record_error(self, e):
        "Save the exception 'e' for future error reporting."
        self.errors.append(e)

    @synchronized('lock')
    def get_errors(self):
        "Return a list of exceptions that have occurred since last get_errors."
        result = self.errors
        self.errors = []
        return result

class Git(callbacks.PluginRegexp):
    "Please see the README file to configure and use this plugin."

    threaded = True
    unaddressedRegexps = [ '_snarf' ]

    def __init__(self, irc):
        self.init_git_python()
        self.__parent = super(Git, self)
        self.__parent.__init__(irc)
        # Workaround the fact that self.log already exists in plugins
        self.log = LogWrapper(self.log, Git._log.__get__(self))
        self.fetcher = None
        self._stop_polling()
        try:
            self._read_config()
        except Exception, e:
            if 'reply' in dir(irc):
                irc.reply('Warning: %s' % str(e))
            else:
                # During bot startup, there is no one to reply to.
                log_warning(str(e))
        self._schedule_next_event()

    def init_git_python(self):
        global GIT_API_VERSION, git
        try:
            import git
        except ImportError:
            raise Exception("GitPython is not installed.")
        if not git.__version__.startswith('0.'):
            raise Exception("Unsupported GitPython version.")
        GIT_API_VERSION = int(git.__version__[2])
        if not GIT_API_VERSION in [1, 3]:
            log_error('GitPython version %s unrecognized, using 0.3.x API.'
                    % git.__version__)
            GIT_API_VERSION = 3

    def die(self):
        self._stop_polling()
        self.__parent.die()

    def _log(self, irc, msg, args, channel, name, count):
        """<short name> [count]

        Display the last commits on the named repository. [count] defaults to
        1 if unspecified.
        """
        matches = filter(lambda r: r.short_name == name, self.repository_list)
        if not matches:
            irc.reply('No configured repository named %s.' % name)
            return
        # Enforce a modest privacy measure... don't let people probe the
        # repository outside the designated channel.
        repository = matches[0]
        if channel not in repository.channels:
            irc.reply('Sorry, not allowed in this channel.')
            return
        commits = repository.get_recent_commits(count)[::-1]
        self._reply_commits(irc, channel, repository, commits)
    _log = wrap(_log, ['channel', 'somethingWithoutSpaces',
                       optional('positiveInt', 1)])

    def rehash(self, irc, msg, args):
        """(takes no arguments)

        Reload the Git ini file and restart any period polling.
        """
        self._stop_polling()
        try:
            self._read_config()
            self._schedule_next_event()
            n = len(self.repository_list)
            irc.reply('Git reinitialized with %d %s.' %
                      (n, plural(n, 'repository')))
        except Exception, e:
            irc.reply('Warning: %s' % str(e))

    def repositories(self, irc, msg, args, channel):
        """(takes no arguments)

        Display the names of known repositories configured for this channel.
        """
        repositories = filter(lambda r: channel in r.channels,
                              self.repository_list)
        if not repositories:
            irc.reply('No repositories configured for this channel.')
            return
        for r in repositories:
            fmt = '\x02%(short_name)s\x02 (%(name)s, branch: %(branch)s)'
            irc.reply(fmt % {
                'branch': r.branch.split('/')[-1],
                'name': r.long_name,
                'short_name': r.short_name,
                'url': r.url,
            })
    repositories = wrap(repositories, ['channel'])

    def gitrehash(self, irc, msg, args):
        "Obsolete command, remove this function eventually."
        irc.reply('"gitrehash" is obsolete, please use "rehash".')

    def repolist(self, irc, msg, args):
        "Obsolete command, remove this function eventually."
        irc.reply('"repolist" is obsolete, please use "repositories".')

    def shortlog(self, irc, msg, args):
        "Obsolete command, remove this function eventually."
        irc.reply('"shortlog" is obsolete, please use "log".')

    # Overridden to hide the obsolete commands
    def listCommands(self, pluginCommands=[]):
        return ['log', 'rehash', 'repositories']

    def _display_commits(self, irc, channel, repository, commits):
        "Display a nicely-formatted list of commits in a channel."
        commits = list(commits)
        commits_at_once = self.registryValue('maxCommitsAtOnce')
        if len(commits) > commits_at_once:
            irc.queueMsg(ircmsgs.privmsg(channel,
                         "Showing latest %d of %d commits to %s..." %
                         (commits_at_once, len(commits), repository.long_name)))
        for commit in commits[-commits_at_once:]:
            lines = repository.format_message(commit)
            for line in lines:
                msg = ircmsgs.privmsg(channel, line)
                irc.queueMsg(msg)

    # Post commits to channel as a reply
    def _reply_commits(self, irc, channel, repository, commits):
        commits = list(commits)
        commits_at_once = self.registryValue('maxCommitsAtOnce')
        if len(commits) > commits_at_once:
            irc.reply("Showing latest %d of %d commits to %s..." %
                      (commits_at_once, len(commits), repository.long_name))
        format_str = repository.commit_reply or repository.commit_message
        for commit in commits[-commits_at_once:]:
            lines = repository.format_message(commit, format_str)
            map(irc.reply, lines)

    def _poll(self):
        # Note that polling happens in two steps:
        #
        # 1. The GitFetcher class, running its own poll loop, fetches
        #    repositories to keep the local copies up to date.
        # 2. This _poll occurs, and looks for new commits in those local
        #    copies.  (Therefore this function should be quick. If it is
        #    slow, it may block the entire bot.)
        try:
            for repository in self.repository_list:
                # Find the IRC/channel pairs to notify
                targets = []
                for irc in world.ircs:
                    for channel in repository.channels:
                        if channel in irc.state.channels:
                            targets.append((irc, channel))
                if not targets:
                    log_info("Skipping %s: not in configured channel(s)." %
                             repository.long_name)
                    continue

                # Manual non-blocking lock calls here to avoid potentially long
                # waits (if it fails, hope for better luck in the next _poll).
                if repository.lock.acquire(blocking=False):
                    try:
                        errors = repository.get_errors()
                        for e in errors:
                            log_error('Unable to fetch %s: %s' %
                                (repository.long_name, str(e)))
                        commits = repository.get_new_commits()[::-1]
                        for irc, channel in targets:
                            self._display_commits(irc, channel, repository,
                                                  commits)
                    except Exception, e:
                        log_error('Exception in _poll repository %s: %s' %
                                (repository.short_name, str(e)))
                    finally:
                        repository.lock.release()
                else:
                    log.info('Postponing repository read: %s: Locked.' %
                        repository.long_name)
            self._schedule_next_event()
        except Exception, e:
            log_error('Exception in _poll(): %s' % str(e))
            traceback.print_exc(e)

    def _read_config(self):
        self.repository_list = []
        repo_dir = self.registryValue('repoDir')
        config = self.registryValue('configFile')
        if not os.access(config, os.R_OK):
            raise Exception('Cannot access configuration file: %s' % config)
        parser = ConfigParser.RawConfigParser()
        parser.read(config)
        for section in parser.sections():
            options = dict(parser.items(section))
            self.repository_list.append(Repository(repo_dir, section, options))

    def _schedule_next_event(self):
        period = self.registryValue('pollPeriod')
        if period > 0:
            if not self.fetcher or not self.fetcher.isAlive():
                self.fetcher = GitFetcher(self.repository_list, period)
                self.fetcher.start()
            schedule.addEvent(self._poll, time.time() + period,
                              name=self.name())
        else:
            self._stop_polling()

    def _snarf(self, irc, msg, match):
        r"""\b(?P<sha>[0-9a-f]{6,40})\b"""
        if self.registryValue('shaSnarfing'):
            sha = match.group('sha')
            channel = msg.args[0]
            repositories = filter(lambda r: channel in r.channels,
                                  self.repository_list)
            for repository in repositories:
                commit = repository.get_commit(sha)
                if commit:
                    self._reply_commits(irc, channel, repository, [commit])
                    break

    def _stop_polling(self):
        # Never allow an exception to propagate since this is called in die()
        if self.fetcher:
            try:
                self.fetcher.stop()
                self.fetcher.join() # This might take time, but it's safest.
            except Exception, e:
                log_error('Stopping fetcher: %s' % str(e))
            self.fetcher = None
        try:
            schedule.removeEvent(self.name())
        except KeyError:
            pass
        except Exception, e:
            log_error('Stopping scheduled task: %s' % str(e))

class GitFetcher(threading.Thread):
    "A thread object to perform long-running Git operations."

    # I don't know of any way to shut down a thread except to have it
    # check a variable very frequently.
    SHUTDOWN_CHECK_PERIOD = 0.1 # Seconds

    # TODO: Wrap git fetch command and enforce a timeout.  Git will probably
    # timeout on its own in most cases, but I have actually seen it hang
    # forever on "fetch" before.

    def __init__(self, repositories, period, *args, **kwargs):
        """
        Takes a list of repositories and a period (in seconds) to poll them.
        As long as it is running, the repositories will be kept up to date
        every period seconds (with a git fetch).
        """
        super(GitFetcher, self).__init__(*args, **kwargs)
        self.repository_list = repositories
        self.period = period * 1.1 # Hacky attempt to avoid resonance
        self.shutdown = False

    def stop(self):
        """
        Shut down the thread as soon as possible. May take some time if
        inside a long-running fetch operation.
        """
        self.shutdown = True

    def run(self):
        "The main thread method."
        # Initially wait for half the period to stagger this thread and
        # the main thread and avoid lock contention.
        end_time = time.time() + self.period/2
        while not self.shutdown:
            try:
                for repository in self.repository_list:
                    if self.shutdown: break
                    if repository.lock.acquire(blocking=False):
                        try:
                            repository.fetch()
                        except Exception, e:
                            repository.record_error(e)
                        finally:
                            repository.lock.release()
                    else:
                        log_info('Postponing repository fetch: %s: Locked.' %
                                 repository.long_name)
            except Exception, e:
                log_error('Exception checking repository %s: %s' %
                          (repository.short_name, str(e)))
            # Wait for the next periodic check
            while not self.shutdown and time.time() < end_time:
                time.sleep(GitFetcher.SHUTDOWN_CHECK_PERIOD)
            end_time = time.time() + self.period

class LogWrapper(object):
    """
    Horrific workaround for the fact that PluginMixin has a member variable
    called 'log' -- wiping out my 'log' command.  Delegates all requests to
    the log, and when called as a function, performs the log command.
    """

    LOGGER_METHODS = [
        'debug',
        'info',
        'warning',
        'error',
        'critical',
        'exception',
    ]

    def __init__(self, log_object, log_command):
        "Construct the wrapper with the objects being wrapped."
        self.log_object = log_object
        self.log_command = log_command
        self.__doc__ = log_command.__doc__

    def __call__(self, *args, **kwargs):
        return self.log_command(*args, **kwargs)

    def __getattr__(self, name):
        if name in LogWrapper.LOGGER_METHODS:
            return getattr(self.log_object, name)
        else:
            return getattr(self.log_command, name)

# Because isCommandMethod() relies on inspection (whyyyy), I do this (gross)
import inspect
if 'git_orig_ismethod' not in dir(inspect):
    inspect.git_orig_ismethod = inspect.ismethod
    inspect.ismethod = \
        lambda x: type(x) == LogWrapper or inspect.git_orig_ismethod(x)

Class = Git

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
__FILENAME__ = test
# Copyright (c) 2011-2012, Mike Mueller
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Do whatever you want.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from supybot.test import *
from supybot import conf

from mock import Mock, patch
import git
import os
import time

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SRC_DIR, 'test-data')

# This timeout value works for me and keeps the tests snappy. If test queries
# are not getting responses, you may need to bump this higher.
LOOP_TIMEOUT = 0.1

# Global mocks
git.Git.clone = Mock()
git.Repo = Mock()

# A pile of commits for use wherever (most recent first)
COMMITS = [Mock(), Mock(), Mock(), Mock(), Mock()]
COMMITS[0].author.name = 'nstark'
COMMITS[0].hexsha = 'abcdefabcdefabcdefabcdefabcdefabcdefabcd'
COMMITS[0].message = 'Fix bugs.'
COMMITS[1].author.name = 'tlannister'
COMMITS[1].hexsha = 'abcdefabcdefabcdefabcdefabcdefabcdefabcd'
COMMITS[1].message = 'I am more long-winded\nand may even use newlines.'
COMMITS[2].author.name = 'tlannister'
COMMITS[2].hexsha = 'abcdefabcdefabcdefabcdefabcdefabcdefabcd'
COMMITS[2].message = 'Snarks and grumpkins'
COMMITS[3].author.name = 'jsnow'
COMMITS[3].hexsha = 'abcdefabcdefabcdefabcdefabcdefabcdefabcd'
COMMITS[3].message = "Finished brooding, think I'll go brood."
COMMITS[4].author.name = 'tlannister'
COMMITS[4].hexsha = 'deadbeefcdefabcdefabcdefabcdefabcdefabcd'
COMMITS[4].message = "I'm the only one getting things done."

# Workaround Supybot 0.83.4.1 bug with Owner treating 'log' as a command
conf.registerGlobalValue(conf.supybot.commands.defaultPlugins,
                         'log', registry.String('Git', ''))
conf.supybot.commands.defaultPlugins.get('log').set('Git')

# Pre-test checks
GIT_API_VERSION = int(git.__version__[2])
assert GIT_API_VERSION == 3, 'Tests only run against GitPython 0.3.x+ API.'

class PluginTestCaseUtilMixin(object):
    "Some additional utilities used in this plugin's tests."

    def _feedMsgLoop(self, query, timeout=None, **kwargs):
        "Send a message and wait for a list of responses instead of just one."
        if timeout is None:
            timeout = LOOP_TIMEOUT
        responses = []
        start = time.time()
        r = self._feedMsg(query, timeout=timeout, **kwargs)
        # Sleep off remaining time, then start sending empty queries until
        # the replies stop coming.
        remainder = timeout - (time.time() - start)
        time.sleep(remainder if remainder > 0 else 0)
        query = conf.supybot.reply.whenAddressedBy.chars()[0]
        while r:
            responses.append(r)
            r = self._feedMsg(query, timeout=0, **kwargs)
        return responses

    def assertResponses(self, query, expectedResponses, **kwargs):
        "Run a command and assert that it returns the given list of replies."
        responses = self._feedMsgLoop(query, **kwargs)
        responses = map(lambda m: m.args[1], responses)
        self.assertEqual(responses, expectedResponses,
                         '\nActual:\n%s\n\nExpected:\n%s' %
                         ('\n'.join(responses), '\n'.join(expectedResponses)))
        return responses

class GitRehashTest(PluginTestCase):
    plugins = ('Git',)

    def setUp(self):
        super(GitRehashTest, self).setUp()
        conf.supybot.plugins.Git.pollPeriod.setValue(0)

    def testRehashEmpty(self):
        conf.supybot.plugins.Git.configFile.setValue(DATA_DIR + '/empty.ini')
        self.assertResponse('rehash', 'Git reinitialized with 0 repositories.')

    def testRehashOne(self):
        conf.supybot.plugins.Git.configFile.setValue(DATA_DIR + '/one.ini')
        self.assertResponse('rehash', 'Git reinitialized with 1 repository.')

class GitRepositoryListTest(ChannelPluginTestCase, PluginTestCaseUtilMixin):
    channel = '#test'
    plugins = ('Git',)

    def setUp(self):
        super(GitRepositoryListTest, self).setUp()
        ini = os.path.join(DATA_DIR, 'multi-channel.ini')
        conf.supybot.plugins.Git.pollPeriod.setValue(0)
        conf.supybot.plugins.Git.configFile.setValue(ini)
        self.assertResponse('rehash', 'Git reinitialized with 3 repositories.')

    def testRepositoryList(self):
        expected = [
            '\x02test1\x02 (Test Repository 1, branch: master)',
            '\x02test2\x02 (Test Repository 2, branch: feature)',
        ]
        self.assertResponses('repositories', expected)

class GitNoAccessTest(ChannelPluginTestCase, PluginTestCaseUtilMixin):
    channel = '#unused'
    plugins = ('Git',)

    def setUp(self):
        super(GitNoAccessTest, self).setUp()
        ini = os.path.join(DATA_DIR, 'multi-channel.ini')
        conf.supybot.plugins.Git.configFile.setValue(ini)
        self.assertResponse('rehash', 'Git reinitialized with 3 repositories.')

    def testRepositoryListNoAccess(self):
        expected = ['No repositories configured for this channel.']
        self.assertResponses('repositories', expected)

    def testLogNoAccess(self):
        expected = ['Sorry, not allowed in this channel.']
        self.assertResponses('log test1', expected)

class GitLogTest(ChannelPluginTestCase, PluginTestCaseUtilMixin):
    channel = '#somewhere'
    plugins = ('Git',)

    def setUp(self):
        super(GitLogTest, self).setUp()
        self._metamock = patch('git.Repo')
        self.Repo = self._metamock.__enter__()
        self.Repo.return_value = self.Repo
        self.Repo.iter_commits.return_value = COMMITS
        ini = os.path.join(DATA_DIR, 'multi-channel.ini')
        conf.supybot.plugins.Git.pollPeriod.setValue(0)
        conf.supybot.plugins.Git.maxCommitsAtOnce.setValue(3)
        conf.supybot.plugins.Git.configFile.setValue(ini)
        self.assertResponse('rehash', 'Git reinitialized with 3 repositories.')

    def tearDown(self):
        del self.Repo
        self._metamock.__exit__()

    def testLogNonexistent(self):
        expected = ['No configured repository named nothing.']
        self.assertResponses('log nothing', expected)

    def testLogNotAllowed(self):
        expected = ['Sorry, not allowed in this channel.']
        self.assertResponses('log test1', expected)

    def testLogZero(self):
        expected = ['(\x02log <short name> [count]\x02) -- Display the last ' +
                    'commits on the named repository. [count] defaults to 1 ' +
                    'if unspecified.']
        self.assertResponses('log test2 0', expected)

    def testLogNegative(self):
        expected = ['(\x02log <short name> [count]\x02) -- Display the last ' +
                    'commits on the named repository. [count] defaults to 1 ' +
                    'if unspecified.']
        self.assertResponses('log test2 -1', expected)

    def testLogOne(self):
        expected = ['[test2|feature|nstark] Fix bugs.']
        self.assertResponses('log test2', expected)

    def testLogTwo(self):
        expected = [
            '[test2|feature|tlannister] I am more long-winded',
            '[test2|feature|nstark] Fix bugs.',
        ]
        self.assertResponses('log test2 2', expected)

    def testLogFive(self):
        expected = [
            'Showing latest 3 of 5 commits to Test Repository 2...',
            '[test2|feature|tlannister] Snarks and grumpkins',
            '[test2|feature|tlannister] I am more long-winded',
            '[test2|feature|nstark] Fix bugs.',
        ]
        self.assertResponses('log test2 5', expected)

    def testSnarf(self):
        self.Repo.commit.return_value = COMMITS[4]
        expected = [
            "[test2|feature|tlannister] I'm the only one getting things done.",
        ]
        self.assertResponses('who wants some deadbeef?', expected,
                             usePrefixChar=False)

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:

########NEW FILE########
