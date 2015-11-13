__FILENAME__ = hellodolly
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

from flashbake.plugins import AbstractMessagePlugin

class HelloDolly(AbstractMessagePlugin):
    """ Sample plugin. """

    def addcontext(self, message_file, config):
        """ Stub. """

        message_file.write('Hello, dolly.\n')

########NEW FILE########
__FILENAME__ = commit
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''  commit.py - Parses a project's control file and wraps git operations, calling the context
script to build automatic commit messages as needed.'''

import context
import datetime
import git
import logging
import os
import re
import sys



DELETED_RE = re.compile('#\s*deleted:.*')

def commit(control_config, hot_files, quiet_mins):
    # change to the project directory, necessary to find the .flashbake file and
    # to correctly refer to the project files by relative paths
    os.chdir(hot_files.project_dir)

    git_obj = git.Git(hot_files.project_dir, control_config.git_path)

    # the wrapper object ensures git is on the path
    # get the git status for the project
    git_status = git_obj.status()

    _handle_fatal(hot_files, git_status)

    # in particular find the existing entries that need a commit
    pending_re = re.compile('#\s*(renamed|copied|modified|new file):.*')

    now = datetime.datetime.today()
    quiet_period = datetime.timedelta(minutes=quiet_mins)

    to_commit = list()
    # first look in the files git already knows about
    logging.debug("Examining git status.")
    for line in git_status.splitlines():
        if pending_re.match(line):
            pending_file = _trimgit(line)

            # not in the dot-control file, skip it
            if not (hot_files.contains(pending_file)):
                continue

            logging.debug('Parsing status line %s to determine commit action' % line)

            # remove files that will be considered for commit
            hot_files.remove(pending_file)

            # check the quiet period against mtime
            last_mod = os.path.getmtime(pending_file)
            pending_mod = datetime.datetime.fromtimestamp(last_mod)
            pending_mod += quiet_period

            # add the file to the list to include in the commit
            if pending_mod < now:
                to_commit.append(pending_file)
                logging.debug('Flagging file, %s, for commit.' % pending_file)
            else:
                logging.debug('Change for file, %s, is too recent.' % pending_file)
        _capture_deleted(hot_files, line)

    logging.debug('Examining unknown or unchanged files.')

    hot_files.warnproblems()

    # figure out what the status of the remaining files is
    for control_file in hot_files.control_files:
        # this shouldn't happen since HotFiles.addfile uses glob.iglob to expand
        # the original file lines which does so based on what is in project_dir
        if not os.path.exists(control_file):
            logging.debug('%s does not exist yet.' % control_file)
            hot_files.putabsent(control_file)
            continue

        status_output = git_obj.status(control_file)

        # needed for git >= 1.7.0.4
        if status_output.find('Untracked files') > 0:
            hot_files.putneedsadd(control_file)
            continue
        if status_output.startswith('error'):
            # needed for git < 1.7.0.4
            if status_output.find('did not match') > 0:
                hot_files.putneedsadd(control_file)
                logging.debug('%s exists but is unknown by git.' % control_file)
            else:
                logging.error('Unknown error occurred!')
                logging.error(status_output)
            continue
        # use a regex to match so we can enforce whole word rather than
        # substring matchs, otherwise 'foo.txt~' causes a false report of an
        # error
        control_re = re.compile('\<' + re.escape(control_file) + '\>')
        if control_re.search(status_output) == None:
            logging.debug('%s has no uncommitted changes.' % control_file)
        # if anything hits this block, we need to figure out why
        else:
            logging.error('%s is in the status message but failed other tests.' % control_file)
            logging.error('Try \'git status "%s"\' for more info.' % control_file)

    hot_files.addorphans(git_obj, control_config)

    for plugin in control_config.file_plugins:
        plugin.post_process(to_commit, hot_files, control_config)

    if len(to_commit) > 0:
        logging.info('Committing changes to known files, %s.' % to_commit)
        message_file = context.buildmessagefile(control_config)
        if not control_config.dry_run:
            # consolidate the commit to be friendly to how git normally works
            commit_output = git_obj.commit(message_file, to_commit)
            logging.debug(commit_output)
        os.remove(message_file)
        _send_commit_notice(control_config, hot_files, to_commit)
        logging.info('Commit for known files complete.')
    else:
        logging.info('No changes to known files found to commit.')

    if hot_files.needs_warning():
        _send_warning(control_config, hot_files)
    else:
        logging.info('No missing or untracked files found, not sending warning notice.')

def purge(control_config, hot_files):
    # change to the project directory, necessary to find the .flashbake file and
    # to correctly refer to the project files by relative paths
    os.chdir(hot_files.project_dir)

    git_obj = git.Git(hot_files.project_dir, control_config.git_path)

    # the wrapper object ensures git is on the path
    git_status = git_obj.status()

    _handle_fatal(hot_files, git_status)

    logging.debug("Examining git status.")
    for line in git_status.splitlines():
        _capture_deleted(hot_files, line)

    if len(hot_files.deleted) > 0:
        logging.info('Committing removal of known files, %s.' % hot_files.deleted)
        message_file = context.buildmessagefile(control_config)
        if not control_config.dry_run:
            # consolidate the commit to be friendly to how git normally works
            commit_output = git_obj.commit(message_file, hot_files.deleted)
            logging.debug(commit_output)
        os.remove(message_file)
        logging.info('Commit for deleted files complete.')
    else:
        logging.info('No deleted files to purge')


def _capture_deleted(hot_files, line):
    if DELETED_RE.match(line):
        deleted_file = _trimgit(line)
        # remove files that will are known to have been deleted
        hot_files.remove(deleted_file)
        hot_files.put_deleted(deleted_file)


def _handle_fatal(hot_files, git_status):
    if git_status.startswith('fatal'):
        logging.error('Fatal error from git.')
        if 'fatal: Not a git repository' == git_status:
            logging.error('Make sure "git init" was run in %s'
                % os.path.realpath(hot_files.project_dir))
        else:
            logging.error(git_status)
        sys.exit(1)


def _trimgit(status_line):
    if status_line.find('->') >= 0:
        tokens = status_line.split('->')
        return tokens[1].strip()

    tokens = status_line.split(':')
    return tokens[1].strip()


def _send_warning(control_config, hot_files):
    if (len(control_config.notify_plugins) == 0
            and not control_config.dry_run):
        logging.info('Skipping notice, no notify plugins configured.')
        return

    for plugin in control_config.notify_plugins:
        plugin.warn(hot_files, control_config)


def _send_commit_notice(control_config, hot_files, to_commit):
    if (len(control_config.notify_plugins) == 0
            and not control_config.dry_run):
        logging.info('Skipping notice, no notify plugins configured.')
        return

    for plugin in control_config.notify_plugins:
        plugin.notify_commit(to_commit, hot_files, control_config)

########NEW FILE########
__FILENAME__ = compat
#    copyright 2009-2011 Thomas Gideon, Jason Penney
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.


'''   compat.py - compatability layer for different versions of python '''

import os.path
import __builtin__
import sys

__all__ = [ 'relpath', 'next_', 'iglob', 'MIMEText' ]

relpath = None
next_ = None

try:
    from glob import iglob
except ImportError:
    from glob import glob as iglob

try:
    import cPickle as pickle
except ImportError:
    import pickle

# Import the email modules we'll need
if sys.hexversion < 0x2050000:
    from email.MIMEText import MIMEText #@UnusedImport
else:
    from email.mime.text import MIMEText #@Reimport

def __fallback_relpath(path, start='.'):
    """Returns a relative version of the path."""
    path = os.path.realpath(path)
    start = os.path.realpath(start)
    if not path.startswith(start):
        raise Exception("unable to calculate paths")
    if os.path.samefile(path, start):
        return "."

    if not start.endswith(os.path.sep):
        start += os.path.sep
    return path[len(start):]

def __fallback_next(*args):
    """next_(iterator[, default])
    
    Return the next item from the iterator. If default is given and 
    the iterator is exhausted, it is returned instead of 
    raising StopIteration."""

    args_len = len(args)
    if (args_len < 1):
        raise TypeError("expected at least 1 argument, got %d" %
                        args_len)
    if (args_len > 2):
        raise TypeError("expected at most 2 arguments, got %d" %
                        args_len)
    iterator = args[0]

    try:
        if hasattr(iterator, '__next__'):
            return iterator.__next__()
        elif hasattr(iterator, 'next'):
            return iterator.next()
        else:
            raise TypeError('%s object is not an iterator' 
                            % type(iterator).__name__)
    except StopIteration:
        if args_len == 2:
            return args[1]
        raise

# relpath
if hasattr(os.path, "relpath"):
    relpath = os.path.relpath
else:
    try:
        import pathutils #@UnresolvedImport
        relpath = pathutils.relative
    except:
        relpath = __fallback_relpath
    
#next_
if hasattr(__builtin__, 'next'):
    next_=__builtin__.next
else:
    next_ = __fallback_next


########NEW FILE########
__FILENAME__ = console
#!/usr/bin/env python

'''  flashbake - wrapper script that will get installed by setup.py into the execution path '''

#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.


from flashbake import commit, context, control
from flashbake.plugins import PluginError, PLUGIN_ERRORS
from optparse import OptionParser
from os.path import join, realpath
import flashbake.git
import fnmatch
import logging
import os.path
import sys

VERSION = flashbake.__version__
pattern = '.flashbake'


def main():
    ''' Entry point used by the setup.py installation script. '''
    # handle options and arguments
    parser = _build_main_parser()

    (options, args) = parser.parse_args()

    if options.quiet and options.verbose:
        parser.error('Cannot specify both verbose and quiet')

    # configure logging
    level = logging.INFO
    if options.verbose:
        level = logging.DEBUG

    if options.quiet:
        level = logging.ERROR

    logging.basicConfig(level=level,
            format='%(message)s')

    home_dir = os.path.expanduser('~')

    # look for plugin directory
    _load_plugin_dirs(options, home_dir)

    if len(args) < 1:
        parser.error('Must specify project directory.')
        sys.exit(1)

    project_dir = args[0]

    # look for user's default control file
    hot_files, control_config = _load_user_control(home_dir, project_dir, options)

    # look for project control file
    control_file = _find_control(parser, project_dir)
    if None == control_file:
        sys.exit(1)

    # emit the context message and exit
    if options.context_only:
        sys.exit(_context_only(options, project_dir, control_file, control_config, hot_files))

    quiet_period = 0
    if len(args) == 2:
        try:
            quiet_period = int(args[1])
        except:
            parser.error('Quiet minutes, "%s", must be a valid number.' % args[1])
            sys.exit(1)
    try:
        (hot_files, control_config) = control.parse_control(project_dir, control_file, control_config, hot_files)
        control_config.context_only = options.context_only
        control_config.dry_run = options.dryrun
        if (options.dryrun):
            logging.info('========================================')
            logging.info('!!! Running in dry run mode.         !!!')
            logging.info('!!! No changes will be committed.    !!!')
            logging.info('========================================\n\n')
        (hot_files, control_config) = control.prepare_control(hot_files, control_config)
        if options.purge:
            commit.purge(control_config, hot_files)
        else:
            commit.commit(control_config, hot_files, quiet_period)
        if (options.dryrun):
            logging.info('\n\n========================================')
            logging.info('!!! Running in dry run mode.         !!!')
            logging.info('!!! No changes will be committed.    !!!')
            logging.info('========================================')
    except (flashbake.git.VCError, flashbake.ConfigError), error:
        logging.error('Error: %s' % str(error))
        sys.exit(1)
    except PluginError, error:
        _handle_bad_plugin(error)
        sys.exit(1)


def multiple_projects():
    parser = _build_multi_parser()
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error('Must specify root search directory.')
        sys.exit(1)

    flashbake_opts = options.flashbake_options.split()

    # verify --options will pass to main flashbake program
    test_argv = sys.argv[0:1] + flashbake_opts + ['.'] + args[1:]
    main_parser = _build_main_parser()
    main_parser.suppress_exit = True

    try:
        (test_options, test_args) = main_parser.parse_args(test_argv)
    except ParserError, err:
        msg = "error with arguments passed to main flashbake: %s\n%s" % (
            "'" + "' '".join(
                flashbake_opts + ['<project_dir>'] + args[1:]) + "'",
            err.msg.replace(parser.get_prog_name() + ':', '> '))
        parser.exit(err.code, msg)
    exit_code = 0
    for project in _locate_projects(args[0]):
        print "project: %s" % project
        sys.argv = sys.argv[0:1] + flashbake_opts + [project] + args[1:]
        try:
            main()
        except SystemExit, err:
            if err.code != 0:
                exit_code = err.code
            logging.error("Error: 'flashbake' had an error for '%s'"
                          % project)
    sys.exit(exit_code)


def _locate_projects(root):
    for path, dirs, files in os.walk(root): #@UnusedVariable
        for project_path in (
            os.path.normpath(path) for filename in files \
                if fnmatch.fnmatch(filename, pattern)):
            yield project_path


class ParserError(RuntimeError):

    def __init__(self, code=0, msg=''):
        RuntimeError.__init__(self, code, msg)

    def _get_msg(self):
        return self.args[1]

    def _get_code(self):
        return self.args[0]

    msg = property(_get_msg)
    code = property(_get_code)


class FlashbakeOptionParser(OptionParser):

    def __init__(self, *args, **kwargs):
        OptionParser.__init__(self, *args, **kwargs)
        self.suppress_exit = False

    def print_usage(self, file=None):
        if not self.suppress_exit:
            OptionParser.print_usage(self, file)

    def exit(self, status=0, msg=None):
        if self.suppress_exit:
            raise ParserError(status, msg)
        else:
            OptionParser.exit(self, status, msg)


def _build_main_parser():
    usage = "usage: %prog [options] <project_dir> [quiet_min]"

    parser = FlashbakeOptionParser(
        usage=usage, version='%s %s' % ('%prog', VERSION))
    parser.add_option('-c', '--context', dest='context_only',
            action='store_true', default=False,
            help='just generate and show the commit message, don\'t check for changes')
    parser.add_option('-v', '--verbose', dest='verbose',
            action='store_true', default=False,
            help='include debug information in the output')
    parser.add_option('-q', '--quiet', dest='quiet',
            action='store_true', default=False,
            help='disable all output excepts errors')
    parser.add_option('-d', '--dryrun', dest='dryrun',
            action='store_true', default=False,
            help='execute a dry run')
    parser.add_option('-p', '--plugins', dest='plugin_dir',
            action='store', type='string', metavar='PLUGIN_DIR',
            help='specify an additional location for plugins')
    parser.add_option('-r', '--purge', dest='purge',
            action='store_true', default=False,
            help='purge any files that have been deleted from source control')
    return parser


def _build_multi_parser():
    usage = "usage: %prog [options] <search_root> [quiet_min]"
    parser = FlashbakeOptionParser(
        usage=usage, version='%s %s' % ('%prog', VERSION))
    parser.add_option('-o', '--options', dest='flashbake_options', default='',
                      action='store', type='string', metavar='FLASHBAKE_OPTS',
                      help=("options to pass through to the 'flashbake' "
                            "command. Use quotes to pass multiple arguments."))
    return parser


def _load_plugin_dirs(options, home_dir):
    plugin_dir = join(home_dir, '.flashbake', 'plugins')
    if os.path.exists(plugin_dir):
        real_plugin_dir = realpath(plugin_dir)
        logging.debug('3rd party plugin directory exists, adding: %s' % real_plugin_dir)
        sys.path.insert(0, real_plugin_dir)
    else:
        logging.debug('3rd party plugin directory doesn\'t exist, skipping.')
        logging.debug('Only stock plugins will be available.')

    if options.plugin_dir != None:
        if os.path.exists(options.plugin_dir):
            logging.debug('Adding plugin directory, %s.' % options.plugin_dir)
            sys.path.insert(0, realpath(options.plugin_dir))
        else:
            logging.warn('Plugin directory, %s, doesn\'t exist.' % options.plugin_dir)



def _load_user_control(home_dir, project_dir, options):
    control_file = join(home_dir, '.flashbake', 'config')
    if os.path.exists(control_file):
        (hot_files, control_config) = control.parse_control(project_dir, control_file)
        control_config.context_only = options.context_only
    else:
        hot_files = None
        control_config = None
    return hot_files, control_config


def _find_control(parser, project_dir):
    control_file = join(project_dir, '.flashbake')

    # look for .control for backwards compatibility
    if not os.path.exists(control_file):
        control_file = join(project_dir, '.control')

    if not os.path.exists(control_file):
        parser.error('Could not find .flashbake or .control file in directory, "%s".' % project_dir)
        return None
    else:
        return control_file


def _context_only(options, project_dir, control_file, control_config, hot_files):
    try:
        (hot_files, control_config) = control.parse_control(project_dir, control_file, control_config, hot_files)
        control_config.context_only = options.context_only
        (hot_files, control_config) = control.prepare_control(hot_files, control_config)

        msg_filename = context.buildmessagefile(control_config)
        message_file = open(msg_filename, 'r')

        try:
            for line in message_file:
                print line.strip()
        finally:
            message_file.close()
            os.remove(msg_filename)
        return 0
    except (flashbake.git.VCError, flashbake.ConfigError), error:
        logging.error('Error: %s' % str(error))
        return 1
    except PluginError, error:
        _handle_bad_plugin(error)
        return 1


def _handle_bad_plugin(plugin_error):
    logging.debug('Plugin error, %s.' % plugin_error)
    if plugin_error.reason == PLUGIN_ERRORS.unknown_plugin or plugin_error.reason == PLUGIN_ERRORS.invalid_plugin: #@UndefinedVariable
        logging.error('Cannot load plugin, %s.' % plugin_error.plugin_spec)
        return

    if plugin_error.reason == PLUGIN_ERRORS.missing_attribute: #@UndefinedVariable
        logging.error('Plugin, %s, doesn\'t have the needed plugin attribute, %s.' \
                % (plugin_error.plugin_spec, plugin_error.name))
        return

    if plugin_error.reason == PLUGIN_ERRORS.invalid_attribute: #@UndefinedVariable
        logging.error('Plugin, %s, has an invalid plugin attribute, %s.' \
                % (plugin_error.plugin_spec, plugin_error.name))
        return

    if plugin_error.reason == PLUGIN_ERRORS.missing_property:
        logging.error('Plugin, %s, requires the config option, %s, but it was missing.' \
                % (plugin_error.plugin_spec, plugin_error.name))
        return

########NEW FILE########
__FILENAME__ = context
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''  context.py - Build up some descriptive context for automatic commit to git'''

import os.path
import random



def buildmessagefile(config):
    """ Build a commit message that uses the provided ControlConfig object and
        return a reference to the resulting file. """
    config.init()

    msg_filename = '/tmp/git_msg_%d' % random.randint(0,1000)

    # try to avoid clobbering another process running this script
    while os.path.exists(msg_filename):
        msg_filename = '/tmp/git_msg_%d' % random.randint(0,1000)

    connectable = False
    connected = False

    message_file = open(msg_filename, 'w')
    try:
        for plugin in config.msg_plugins:
            plugin_success = plugin.addcontext(message_file, config)
            # let each plugin say which ones attempt network connections
            if plugin.connectable:
                connectable = True
                connected = connected or plugin_success
        if connectable and not connected:
            message_file.write('All of the plugins that use the network failed.\n')
            message_file.write('Your computer may not be connected to the network.')
    finally:
        message_file.close()
    return msg_filename

########NEW FILE########
__FILENAME__ = control
'''
Created on Aug 3, 2009

control.py - control file parsing and preparation.

@author: cmdln
'''
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.
import flashbake
import logging



def parse_control(project_dir, control_file, config=None, results=None):
    """ Parse the dot-control file to get config options and hot files. """

    logging.debug('Checking %s' % control_file)

    if None == results:
        hot_files = flashbake.HotFiles(project_dir)
    else:
        hot_files = results

    if None == config:
        control_config = flashbake.ControlConfig()
    else:
        control_config = config

    control_file = open(control_file, 'r')
    try:
        for line in control_file:
            # skip anything else if the config consumed the line
            if control_config.capture(line):
                continue

            hot_files.addfile(line.strip())
    finally:
        control_file.close()

    return (hot_files, control_config)

def prepare_control(hot_files, control_config):
    control_config.init()
    logging.debug("loading file plugins")
    for plugin in control_config.file_plugins:
        logging.debug("running plugin %s" % plugin)
        plugin.pre_process(hot_files, control_config)
    return (hot_files, control_config)


########NEW FILE########
__FILENAME__ = git
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''  git.py - Wrap the call outs to git, adding sanity checks and environment set up if
needed.'''

import logging
import os
import subprocess



class VCError(Exception):
    """ Error when the version control wrapper object cannot be set up. """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Git:
    def __init__(self, cwd, git_path=None):
        # look for git in the environment's PATH var
        path_env = os.getenv('PATH')
        if (len(path_env) == 0):
            path_env = os.defpath
        path_tokens = path_env.split(os.pathsep)
        git_exists = False
        # if there is a git_path option, that takes precedence
        if git_path != None:
            if git_path.endswith('git'):
                git_path = os.path.dirname(git_path)
            if os.path.exists(os.path.join(git_path, 'git')):
                git_exists = True
        else:
            for path_token in path_tokens:
                if os.path.exists(os.path.join(path_token, 'git')):
                    git_exists = True
        # fail much sooner and more quickly then if git calls are made later,
        # naively assuming it is available
        if not git_exists:
            raise VCError('Could not find git executable on PATH.')
        # set up an environment mapping suitable for use with the subprocess
        # module
        self.__init_env(git_path)
        self.__cwd = cwd

    def status(self, filename=None):
        """ Get the git status for the specified files, or the entire current
            directory. """
        if filename != None:
            files = list()
            files.append(filename)
            return self.__run('status', files=files)
        else:
            return self.__run('status')

    def add(self, file):
        """ Add an unknown but existing file. """
        files = [ file ]
        return self.__run('add', files=files)

    def commit(self, messagefile, files):
        """ Commit a list of files, the files should be strings and quoted. """
        options = ['-F', messagefile]
        return self.__run('commit', options, files)

    def __run(self, cmd, options=None, files=None):
        cmds = list()
        cmds.append('git')
        cmds.append(cmd)
        if options != None:
            cmds += options
        if files != None:
            cmds += files
        proc = subprocess.Popen(cmds, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=self.__cwd, env=self.env)
        return proc.communicate()[0]

    def __init_env(self, git_path):
        self.env = dict()
        self.env.update(os.environ)
        if git_path != None:
            new_path = self.env['PATH']
            new_path = '%s%s%s' % (git_path, os.pathsep, new_path)
            self.env['PATH'] = new_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
            format='%(message)s')
    git = Git('../foo', '/opt/local/bin')
    try:
        git = Git('../foo')
    except VCError, e:
        logging.info(e)
    os.chdir('../foo')
    logging.info(git.status())

########NEW FILE########
__FILENAME__ = default
#    copyright 2010 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''  default.py - Stock plugin to add in some statically configured text into a commit message.'''

from flashbake.plugins import AbstractMessagePlugin
import flashbake


class Default(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, False)
        self.define_property('message')

    def addcontext(self, message_file, config):
        """ Add a static message to the commit context. """

        if self.message is not None:
            message_file.write('%s\n' % self.message)

        return True

########NEW FILE########
__FILENAME__ = feed
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''  feed.py - Stock plugin that pulls latest n items from a feed by a given author. '''

import feedparser
import logging
from urllib2 import HTTPError, URLError
from flashbake.plugins import AbstractMessagePlugin



class Feed(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, True)
        self.define_property('url', required=True)
        self.define_property('author')
        self.define_property('limit', int, False, 5)

    def addcontext(self, message_file, config):
        """ Add the matching items to the commit context. """

        # last n items for m creator
        (title, last_items) = self.__fetchfeed()

        if len(last_items) > 0:
            if self.author == None:
                message_file.write('Last %(item_count)d entries from %(feed_title)s:\n'\
                    % {'item_count' : len(last_items), 'feed_title' : title})
            else:
                message_file.write('Last %(item_count)d entries from %(feed_title)s by %(author)s:\n'\
                    % {'item_count' : len(last_items), 'feed_title' : title, 'author': self.author})
            for item in last_items:
                # edit the '%s' if you want to add a label, like 'Title %s' to the output
                message_file.write('%s\n' % item['title'])
                message_file.write('%s\n' % item['link'])
        else:
            message_file.write('Couldn\'t fetch entries from feed, %s.\n' % self.url)

        return len(last_items) > 0

    def __fetchfeed(self):
        """ Fetch up to the limit number of items from the specified feed with the specified
            creator. """

        try:
            feed = feedparser.parse(self.url)

            if not 'title' in feed.feed:
                logging.info('Feed title is empty, feed is either malformed or unavailable.')
                return (None, {})

            feed_title = feed.feed.title

            by_creator = []
            for entry in feed.entries:
                if self.author != None and entry.author != self.author:
                    continue
                title = entry.title
                title = title.encode('ascii', 'replace')
                link = entry.link
                by_creator.append({"title" : title, "link" : link})
                if self.limit <= len(by_creator):
                    break

            return (feed_title, by_creator)
        except HTTPError, e:
            logging.error('Failed with HTTP status code %d' % e.code)
            return (None, {})
        except URLError, e:
            logging.error('Plugin, %s, failed to connect with network.' % self.__class__)
            logging.debug('Network failure reason, %s.' % e.reason)
            return (None, {})

########NEW FILE########
__FILENAME__ = growl
#    copyright 2009 Jason Penney
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

# growl.py - Growl notification flashbake plugin

from flashbake import plugins
import flashbake
import logging
import os
import re
import subprocess



class Growl(plugins.AbstractNotifyPlugin):
    def __init__(self, plugin_spec):
        plugins.AbstractPlugin.__init__(self, plugin_spec)
        self.define_property('host')
        self.define_property('port')
        self.define_property('password')
        self.define_property('growlnotify')
        self.define_property('title_prefix', default='fb:')
            
    def init(self, config):
        if self.growlnotify == None:
            self.growlnotify = flashbake.find_executable('growlnotify')

        if self.growlnotify == None:
            raise plugins.PluginError(plugins.PLUGIN_ERRORS.ignorable_error, #@UndefinedVariable
                                      self.plugin_spec,
                                      'Could not find command, growlnotify.')
        
    # TODO: use netgrowl.py (or wait for GNTP support to be finalized
    # so it will support Growl for Windows as well)
    def growl_notify(self, title, message):
        args = [ self.growlnotify, '--name', 'flashbake' ]
        if self.host != None:
            args += [ '--udp', '--host', self.host]
        if self.port != None:
            args += [ '--port', self.port ]
        if self.password != None:
            args += [ '--password', self.password ]

        title = ' '.join([self.title_prefix, title])
        args += ['--message', message, '--title', title]
        subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             close_fds=True)

    def warn(self, hot_files, config):
        ''' Emits one message per file, with less explanation than the email plugin.
            The most common case is that one or two files will be off, a large number
            of them can be considered pathological, e.g. someone who didn't read the
            documentation about lack of support for symlinks, for instance. '''
        # if calling growl locally, then the current user must be logged into the console
        if self.host == None and not self.__active_console():
            logging.debug('Current user does not have console access.')
            return

        logging.debug('Trying to warn via growl.')
        project_name = os.path.basename(hot_files.project_dir)

        [self.growl_notify('Missing in project, %s' % project_name,
                          'The file, "%s", is missing.' % file)
         for file in hot_files.not_exists]

        [self.growl_notify('Deleted in project, %s' % project_name,
                          'The file, "%s", has been deleted from version control.' % file)
         for file in hot_files.deleted]

        [self.growl_notify('Link in project, %s' % project_name,
                          'The file, "%s", is a link.' % file)
         for (file, link) in hot_files.linked_files.iteritems()
         if file == link]
        
        [self.growl_notify('Link in project, %s' % project_name,
                          'The file, "%s", is a link to %s.' % (link, file))
         for (file, link) in hot_files.linked_files.iteritems()
         if file != link]


        [self.growl_notify('External file in project, %s' % project_name,
                           'The file, "%s", exists outside of the project directory.' % file)
        for file in hot_files.outside_files]

    def notify_commit(self, to_commit, hot_files, config):
        logging.debug('Trying to notify via growl.')
        self.growl_notify(os.path.basename(hot_files.project_dir),
                          'Tracking changes to:\n' + '\n'.join(to_commit))

    def __whoami(self):
        cmd = flashbake.find_executable('whoami')
        if cmd:
            proc = subprocess.Popen([cmd], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            return proc.communicate()[0].strip()
        else:
            return None
    
    def __active_console(self):
        user = self.__whoami()
        if not user:
            return False
        cmd = flashbake.find_executable('who')
        if not cmd:
            return False
        proc = subprocess.Popen([cmd], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        active = False
        for line in proc.communicate()[0].splitlines():
            m = re.match('^%s\s+console.*$' % user, line)
            if m:
                active = True
                break
        return active


########NEW FILE########
__FILENAME__ = lastfm
#    copyright 2011 Og Maciel
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''  lastfm.py - Plugin that pulls latest n items from your last.fm account. '''

import logging
import urllib
import json
from flashbake.plugins import AbstractMessagePlugin



LASTFM = "http://ws.audioscrobbler.com/2.0/?method="
PLUGIN_SPEC = 'flashbake.plugins.lastfm:LastFM'

class LastFM(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, True)
        self.define_property('user_name', required=True)
        self.define_property('api_key', required=True)
        self.define_property('limit', int, False, 5)

    def addcontext(self, message_file, config):
        """ Add the matching items to the commit context. """

        # last n items for m creator
        url = "%suser.getrecentTracks&user=%s&api_key=%s&limit=%s&format=json" % (LASTFM, self.user_name, self.api_key, self.limit)
        logging.info('API call: %s' % url)
        raw_data = self._fetch_data(url)

        tracks = raw_data['recenttracks']['track']
        if not type(tracks) == list:
            tracks = [tracks]
        for trackdic in tracks:
            track = unicode(trackdic['name']).encode("utf-8")
            artist = unicode(trackdic['artist']['#text']).encode("utf-8")
            message_file.write("Track from Last.fm: %s by %s\n" % (track, artist))

    def _fetch_data(self, url):
        raw_data = urllib.urlopen(url)
        data = json.loads(raw_data.read())

        return data

########NEW FILE########
__FILENAME__ = location
#  location.py
#  Net location plugin.
#
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

from flashbake.plugins import AbstractMessagePlugin
from urllib2 import HTTPError, URLError
from xml.dom import minidom
import logging
import os.path
import re
import urllib
import urllib2



class Location(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, True)
        self.share_property('location_location')

    def addcontext(self, message_file, config):
        ip_addr = self.__get_ip()
        if ip_addr == None:
            message_file.write('Failed to get public IP for geo location.\n')
            return False
        location = self.__locate_ip(ip_addr)
        if len(location) == 0:
            message_file.write('Failed to parse location data for IP address.\n')
            return False

        logging.debug(location)
        location_str = '%(cityName)s, %(regionName)s' % location
        config.location_location = location_str
        message_file.write('Current location is %s based on IP %s.\n' % (location_str, ip_addr))
        return True

    def __locate_ip(self, ip_addr):
        cached = self.__load_cache()
        if cached.get('ip_addr','') == ip_addr:
            del cached['ip_addr']
            return cached
        base_url = 'http://api.ipinfodb.com/v3/ip-city/?'
        for_ip = base_url + urllib.urlencode({'key': 'd2e4d26478b0759c225fd4b9113240e1ab7c1bf4f8fb673cba0a2ed52a351916',
                                              'ip': ip_addr,
                                              'format': 'xml'})

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())

        try:
            logging.debug('Requesting page for %s.' % for_ip)

            # open the location API page
            location_xml = opener.open(urllib2.Request(for_ip)).read()

            # the weather API returns some nice, parsable XML
            location_dom = minidom.parseString(location_xml)

            # just interested in the conditions at the moment
            response = location_dom.getElementsByTagName("Response")

            if response == None or len(response) == 0:
                return dict()

            location = dict()
            for child in response[0].childNodes:
                if child.localName == None:
                    continue
                key = child.localName
                key = key.encode('ASCII', 'replace')
                location[key] = self.__get_text(child.childNodes)
            self.__save_cache(ip_addr, location)
            return location
        except HTTPError, e:
            logging.error('Failed with HTTP status code %d' % e.code)
            return {}
        except URLError, e:
            logging.error('Plugin, %s, failed to connect with network.' % self.__class__)
            logging.debug('Network failure reason, %s.' % e.reason)
            return {}

    def __load_cache(self):
        home_dir = os.path.expanduser('~')
        # look for flashbake directory
        fb_dir = os.path.join(home_dir, '.flashbake')
        cache = dict()
        if not os.path.exists(fb_dir):
            return cache
        cache_name = os.path.join(fb_dir, 'ip_cache')
        if not os.path.exists(cache_name):
            return cache
        cache_file = open(cache_name, 'r')
        try:
            for line in cache_file:
                tokens = line.split(':')
                key = tokens[0]
                value = tokens[1].strip()
                if key.startswith('location.'):
                    key = key.replace('location.', '')
                cache[key] = value
            logging.debug('Loaded cache %s' % cache)
        finally:
            cache_file.close()
        return cache

    def __save_cache(self, ip_addr, location):
        home_dir = os.path.expanduser('~')
        # look for flashbake directory
        fb_dir = os.path.join(home_dir, '.flashbake')
        if not os.path.exists(fb_dir):
            os.mkdir(fb_dir)
        cache_file = open(os.path.join(fb_dir, 'ip_cache'), 'w')
        try:
            cache_file.write('ip_addr:%s\n' % ip_addr)
            for key in location.iterkeys():
                cache_file.write('location.%s:%s\n' % (key, location[key]))
        finally:
            cache_file.close()

    def __get_text(self, node_list):
        text_value = ''
        for node in node_list:
            if node.nodeType != node.TEXT_NODE:
                continue;
            text_value += node.data
        return text_value

    def __get_ip(self):
        no_reply = 'http://www.noreply.org'
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())

        try:
            # open the weather API page
            ping_reply = opener.open(urllib2.Request(no_reply)).read()
            hello_line = None
            for line in ping_reply.split('\n'):
                if line.find('Hello') > 0:
                    hello_line = line.strip()
                    break
            if hello_line is None:
                logging.error('Failed to parse Hello with public IP address.')
                return None
            logging.debug(hello_line)
            m = re.search('([0-9]+\.){3}([0-9]+){1}', hello_line)
            if m is None:
                logging.error('Failed to parse Hello with public IP address.')
                return None
            ip_addr = m.group(0)
            return ip_addr
        except HTTPError, e:
            logging.error('Failed with HTTP status code %d' % e.code)
            return None
        except URLError, e:
            logging.error('Plugin, %s, failed to connect with network.' % self.__class__)
            logging.debug('Network failure reason, %s.' % e.reason)
            return None

########NEW FILE########
__FILENAME__ = mail
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''
Created on Jul 23, 2009

mail.py - plug-in to send notices via smtp.

@author: cmdln
'''

from flashbake import plugins
from flashbake.compat import MIMEText
import logging
import os
import smtplib
import sys


class Email(plugins.AbstractNotifyPlugin):
    def __init__(self, plugin_spec):
        plugins.AbstractPlugin.__init__(self, plugin_spec)
        self.define_property('notice_to', required=True)
        self.define_property('notice_from')
        self.define_property('smtp_host', default='localhost')
        self.define_property('smtp_port', int, default=25)

    def init(self, config):
        if self.notice_from == None:
            self.notice_from = self.notice_to

    def warn(self, hot_files, control_config):
        body = ''

        if len(hot_files.not_exists) > 0:
            body += '\nThe following files do not exist:\n\n'

            for file in hot_files.not_exists:
                body += '\t' + file + '\n'

            body += '\nMake sure there is not a typo in .flashbake and that you created/saved the file.\n'

        if len(hot_files.deleted) > 0:
            body += '\nThe following files have been deleted from version control:\n\n'

            for file in hot_files.deleted:
                body += '\t' + file + '\n'

            body += '\nYou may restore these files or remove them from .flashbake after running flashbake --purge '
            body += 'in your project directory.\n'

        if len(hot_files.linked_files) > 0:
            body += '\nThe following files in .flashbake are links or have a link in their directory path.\n\n'

            for (file, link) in hot_files.linked_files.iteritems():
                if file == link:
                    body += '\t' + file + ' is a link\n'
                else:
                    body += '\t' + link + ' is a link on the way to ' + file + '\n'

            body += '\nMake sure the physical file and its parent directories reside in the project directory.\n'

        if len(hot_files.outside_files) > 0:
            body += '\nThe following files in .flashbake are not in the project directory.\n\n'

            for file in hot_files.outside_files:
                body += '\t' + file + '\n'

            body += '\nOnly files in the project directory can be tracked and committed.\n'


        if control_config.dry_run:
            logging.debug(body)
            if self.notice_to != None:
                logging.info('Dry run, skipping email notice.')
            return

        # Create a text/plain message
        msg = MIMEText(body, 'plain')

        msg['Subject'] = ('Some files in %s do not exist'
                % os.path.realpath(hot_files.project_dir))
        msg['From'] = self.notice_from
        msg['To'] = self.notice_to

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        logging.debug('\nConnecting to SMTP on host %s, port %d'
                % (self.smtp_host, self.smtp_port))

        try:
            s = smtplib.SMTP()
            s.connect(host=self.smtp_host, port=self.smtp_port)
            logging.info('Sending notice to %s.' % self.notice_to)
            logging.debug(body)
            s.sendmail(self.notice_from, [self.notice_to], msg.as_string())
            logging.info('Notice sent.')
            s.close()
        except Exception, e:
            logging.error('Couldn\'t connect, will send later.')
            logging.debug("SMTP Error:\n" + str(e));

########NEW FILE########
__FILENAME__ = microblog
#    copyright 2009 Ben Snider (bensnider.com), Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.
'''  microblog.py - microblog plugins by Ben Snider, bensnider.com '''

from flashbake.plugins import AbstractMessagePlugin
from urllib2 import HTTPError, URLError
from xml.etree.ElementTree import ElementTree
import logging
import urllib



class Twitter(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, True)
        self.service_url = 'http://twitter.com'
        self.optional_field_info = { \
            'source':{'path':'source', 'transform':propercase}, \
            'location':{'path':'user/location', 'transform':propercase}, \
            'favorited':{'path':'favorited', 'transform':propercase}, \
            'tweeted_on': {'path':'created_at', 'transform':utc_to_local}, \
        }
        self.define_property('user', required=True)
        self.define_property('limit', int, False, 5)
        self.define_property('optional_fields')

    def init(self, config):
        if self.limit > 200:
            logging.warn('Please use a limit <= 200.');
            self.limit = 200

        self.__setoptionalfields(config)

        # simple user xml feed
        self.twitter_url = '%(url)s/statuses/user_timeline/%(user)s.xml?count=%(limit)d' % {
            'url':self.service_url,
            'user':self.user,
            'limit':self.limit}

    def __setoptionalfields(self, config):
        # We don't have to worry about a KeyError here since this property
        # should have been set to None by self.setoptionalproperty.
        if (self.optional_fields == None):
            self.optional_fields = []
        else:
            # get the optional fields, split on commas
            fields = self.optional_fields.strip().split(',')
            newFields = []
            for field in fields:
                field = field.strip()
                # check if they are allowed and not a dupe
                if (field in self.optional_field_info and field not in newFields):
                    # if so we push them onto the optional fields array, otherwise ignore
                    newFields.append(field)
            # finally sort the list so its the same each run, provided the config is the same
            newFields.sort()
            self.optional_fields = newFields

    def addcontext(self, message_file, config):
        (title, last_tweets) = self.__fetchitems(config)

        if (len(last_tweets) > 0 and title != None):
            to_file = ('Last %(item_count)d %(service_name)s messages from %(twitter_title)s:\n' \
                % {'item_count' : len(last_tweets), 'twitter_title' : title, 'service_name':self.service_name})

            i = 1
            for item in last_tweets:
                to_file += ('%d) %s\n' % (i, item['tweet']))
                for field in self.optional_fields:
                    to_file += ('\t%s: %s\n' % (propercase(field), item[field]))
                i += 1

            logging.debug(to_file.encode('UTF-8'))
            message_file.write(to_file.encode('UTF-8'))
        else:
            message_file.write('Couldn\'t fetch entries from feed, %s.\n' % self.twitter_url)

        return len(last_tweets) > 0

    def __fetchitems(self, config):
        ''' We fetch the tweets from the configured url in self.twitter_url,
        and return a list containing the formatted title and an array of
        tweet dictionaries that contain at least the 'tweet' key along with
        any optional fields. The 
        '''
        results = [None, []]

        try:
            twitter_xml = urllib.urlopen(self.twitter_url)
        except HTTPError, e:
            logging.error('Failed with HTTP status code %d' % e.code)
            return results
        except URLError, e:
            logging.error('Plugin, %s, failed to connect with network.' % self.__class__)
            logging.debug('Network failure reason, %s.' % e.reason)
            return results
        except IOError:
            logging.error('Plugin, %s, failed to connect with network.' % self.__class__)
            logging.debug('Socket error.')
            return results

        tree = ElementTree()
        tree.parse(twitter_xml)

        status = tree.find('status')
        if (status == None):
            return results
        # after this point we are pretty much guaranteed that we won't get an
        # exception or None value, provided the twitter xml stays the same
        results[0] = propercase(status.find('user/name').text)

        for status in tree.findall('status'):
            tweet = {}
            tweet['tweet'] = status.find('text').text
            for field in self.optional_fields:
                tweet[field] = status.find(self.optional_field_info[field]['path']).text
                if ('transform' in self.optional_field_info[field]):
                    tweet[field] = self.optional_field_info[field]['transform'](tweet[field])
            results[1].append(tweet)

        return results


class Identica(Twitter):

    def __init__(self, plugin_spec):
        Twitter.__init__(self, plugin_spec)
        self.service_url = 'http://identi.ca/api'
        self.optional_field_info['created_on'] = self.optional_field_info['tweeted_on']
        del self.optional_field_info['tweeted_on']


def propercase(string):
    ''' Returns the string with _ replaced with spaces and the whole string
    should be title cased. '''
    string = string.replace('_', ' ')
    string = string.title()
    return string


def utc_to_local(t):
    ''' ganked from http://feihonghsu.blogspot.com/2008/02/converting-from-local-time-to-utc.html '''
    import calendar, datetime
    # Discard the timezone, python dont like it, and it seems to always be
    # set to UTC, even if the user has their timezone set.
    t = t.replace('+0000 ', '')
    # might asplode
    return datetime.datetime.fromtimestamp((calendar.timegm(datetime.datetime.strptime(t, '%a %b %d %H:%M:%S %Y').timetuple()))).strftime("%A, %b. %d, %Y at %I:%M%p %z")

########NEW FILE########
__FILENAME__ = music
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.
#
# the iTunes class is based on the itunes.py by Andrew Wheiss, originally
# licensed under an MIT License

'''  music.py - Plugin for gathering last played tracks from music player. '''

from flashbake.plugins import AbstractMessagePlugin
import flashbake
import logging
import os.path
import sqlite3
import subprocess
import time



class Banshee(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        """ Add an optional property for specifying a different location for the
            Banshee database. """
        AbstractMessagePlugin.__init__(self, plugin_spec)
        self.define_property('db', default=os.path.join(os.path.expanduser('~'), '.config', 'banshee-1', 'banshee.db'))
        self.define_property('limit', int, default=3)
        self.define_property('last_played_format')

    def addcontext(self, message_file, config):
        """ Open the Banshee database and query for the last played tracks. """
        query = """\
select t.Title, a.Name, t.LastPlayedStamp
from CoreTracks t
join CoreArtists a on t.ArtistID = a.ArtistID
order by LastPlayedStamp desc
limit %d"""
        query = query.strip() % self.limit
        conn = sqlite3.connect(self.db)
        try:
            cursor = conn.cursor()
            logging.debug('Executing %s' % query)
            cursor.execute(query)
            results = cursor.fetchall()
            message_file.write('Last %d track(s) played in Banshee:\n' % len(results))
            for result in results:
                last_played = time.localtime(result[2])
                if self.last_played_format != None:
                    logging.debug('Using format %s' % self.last_played_format)
                    last_played = time.strftime(self.last_played_format,
                            last_played)
                else:
                    last_played = time.ctime(result[2])
                message_file.write('"%s", by %s (%s)' %
                        (result[0], result[1], last_played))
                message_file.write('\n')
        except Exception, error:
            logging.error(error)
            conn.close()

        return True


class iTunes(AbstractMessagePlugin):
    ''' Based on Andrew Heiss' plugin which is MIT licensed which should be compatible. '''
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec)
        self.define_property('osascript')
        
    def init(self, config):
        if self.osascript is None:
            self.osascript = flashbake.find_executable('osascript')

    def addcontext(self, message_file, config):
        """ Get the track info and write it to the commit message """

        info = self.trackinfo()

        if info is None:
            message_file.write('Couldn\'t get current track.\n')
        else:
            message_file.write('Currently playing in iTunes:\n%s' % info)

        return True

    def trackinfo(self):
        ''' Call the AppleScript file. '''
        if self.osascript is None:
            return None
        directory = os.path.dirname(__file__)
        script_path = os.path.join(directory, 'current_track.scpt')

        args = [self.osascript, script_path]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             close_fds=True)

        return proc.communicate()[0]

########NEW FILE########
__FILENAME__ = scrivener
#    copyright 2009-2011 Thomas Gideon, Jason Penney
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''   scrivener.py - Scrivener flashbake plugin
by Jason Penney, jasonpenney.net'''

from flashbake.plugins import (
    AbstractFilePlugin, AbstractMessagePlugin, PluginError,
    PLUGIN_ERRORS)

import flashbake #@UnusedImport
import fnmatch
import glob
import logging
import os
import os.path
import subprocess
import string
import re

from flashbake.compat import relpath, pickle

def find_scrivener_projects(hot_files, config, flush_cache=False):
    if flush_cache:
        config.scrivener_projects = None

    if config.scrivener_projects == None:
        scrivener_projects = list()
        for f in hot_files.control_files:
            if fnmatch.fnmatch(f, '*.scriv'):
                scrivener_projects.append(f)

        config.scrivener_projects = scrivener_projects

    return config.scrivener_projects


def find_scrivener_project_contents(hot_files, scrivener_project):
    for path, dirs, files in os.walk(os.path.join(  # @UnusedVariable
            hot_files.project_dir, scrivener_project)):
        rpath = relpath(path, hot_files.project_dir)
        for filename in files:
            yield os.path.join(rpath, filename)


def get_logfile_name(scriv_proj_dir):
    return os.path.join(os.path.dirname(scriv_proj_dir),
                        ".%s.flashbake.wordcount" % os.path.basename(
                            scriv_proj_dir))


## TODO: deal with deleted files
class ScrivenerFile(AbstractFilePlugin):

    def __init__(self, plugin_spec):
        AbstractFilePlugin.__init__(self, plugin_spec)
        self.share_property('scrivener_projects')

    def pre_process(self, hot_files, config):
        for f in find_scrivener_projects(hot_files, config):
            logging.debug("ScrivenerFile: adding '%s'" % f)
            for hotfile in find_scrivener_project_contents(hot_files, f):
                #logging.debug(" - %s" % hotfile)
                hot_files.control_files.add(hotfile)

    def post_process(self, to_commit, hot_files, config):
        flashbake.commit.purge(config, hot_files)


class ScrivenerWordcountFile(AbstractFilePlugin):
    """ Record Wordcount for Scrivener Files """

    def __init__(self, plugin_spec):
        AbstractFilePlugin.__init__(self, plugin_spec)

        self.define_property('use_textutil', type=bool, default=False)

        self.share_property('scrivener_projects')
        self.share_property('scrivener_project_count')

    def init(self, config):
        self.get_count = self._get_count_python
        if self.use_textutil:
            if flashbake.executable_available('textutil'):
                self.get_count = self._get_count_textutil
            else:
                logging.warn("unable to find textutil, will use python "
                             "wordcount calculation")

    def pre_process(self, hot_files, config):
        config.scrivener_project_count = dict()
        for f in find_scrivener_projects(hot_files, config):
            scriv_proj_dir = os.path.join(hot_files.project_dir, f)
            hot_logfile = get_logfile_name(f)
            logfile = os.path.join(hot_files.project_dir, hot_logfile)

            if os.path.exists(logfile):
                logging.debug("logifile exists %s" % logfile)
                log = open(logfile, 'r')
                oldCount = pickle.load(log)
                log.close()
            else:
                oldCount = {
                    'Content': 0,
                    'Synopsis': 0,
                    'Notes': 0,
                    'All': 0}

            search_path = os.path.join(scriv_proj_dir, 'Files', 'Docs')
            if os.path.exists(os.path.join(search_path)):
                newCount = {
                    'Content': self.get_count(search_path, ["*[0-9].rtf"]),
                    'Synopsis': self.get_count(
                        search_path, ['*_synopsis.txt']),
                    'Notes': self.get_count(
                        search_path, ['*_notes.rtf']),
                    'All': self.get_count(
                        search_path, ['*.rtf', '*.txt'])}

            else:
                newCount = {
                    'Content': self.get_count(scriv_proj_dir, ["*[0-9].rtfd"]),
                    'Synopsis': self.get_count(
                        scriv_proj_dir, ['*_synopsis.txt']),
                    'Notes': self.get_count(
                        scriv_proj_dir, ['*_notes.rtfd']),
                    'All': self.get_count(
                        scriv_proj_dir, ['*.rtfd', '*.txt'])}

            config.scrivener_project_count[f] = {
                'old': oldCount,
                'new': newCount}

            if not config.context_only:
                log = open(logfile, 'w')
                pickle.dump(config.scrivener_project_count[f]['new'], log)
                log.close()
                if not hot_logfile in hot_files.control_files:
                    hot_files.control_files.add(logfile)

    RTF_RE = re.compile('(\{[^}]+\}|\\\\\\\\END_SCRV[^\}]+\}|'
                        '\\\\\'\d+|\\\\(\\\\|[-=A-Za-z0-9\.])*|\}$|'
                        '\W[%s]\W)' % (re.escape(string.punctuation)),
                        re.MULTILINE | re.IGNORECASE)

    def _get_count_python(self, file, matches):
        count = 0
        for match in matches:
            for f in glob.glob(os.path.normpath(os.path.join(file, match))):
                if f.endswith('.rtfd'):
                    new_f = os.path.join(f, 'TXT.rtf')
                    if os.path.exists(new_f):
                        f = new_f

                if f.endswith('.txt'):
                    count += len(open(f).read().split(None))
                elif f.endswith('.rtf'):
                    words = self.RTF_RE.sub('', open(f).read()).split(None)
                    count += len(words)
                else:
                    raise PluginError(
                        PLUGIN_ERRORS.ignorable_error,
                        self.plugin_spec,
                        'Unsupported file type: %s' % f)
        return count

    def _get_count_textutil(self, file, matches):
        count = 0
        args = ['textutil', '-stdout', '-cat', 'txt']
        do_count = False
        for match in matches:
            for f in glob.glob(os.path.normpath(os.path.join(file, match))):
                do_count = True
                args.append(f)

        if do_count:
            p = subprocess.Popen(args, stdout=subprocess.PIPE,
                             close_fds=True)
            count += len(p.stdout.read().split(None))

        return count


class ScrivenerWordcountMessage(AbstractMessagePlugin):
    """ Display Wordcount for Scrivener Files """

    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, False)
        self.share_property('scrivener_project_count')

    def addcontext(self, message_file, config):
        to_file = ''
        if 'scrivener_project_count' in config.__dict__:
            for proj in config.scrivener_project_count:
                to_file += "Wordcount: %s\n" % proj
                for key in ['Content', 'Synopsis', 'Notes', 'All']:
                    new = config.scrivener_project_count[proj]['new'][key]
                    old = config.scrivener_project_count[proj]['old'][key]
                    diff = new - old
                    to_file += "- " + key.ljust(10, ' ') + str(new).rjust(20)
                    if diff != 0:
                        to_file += " (%+d)" % (new - old)
                    to_file += "\n"

            message_file.write(to_file)

########NEW FILE########
__FILENAME__ = timezone
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.


'''  timezone.py - Stock plugin to find the system's time zone add to the commit message.'''

from flashbake.plugins import AbstractMessagePlugin
import logging
import os



PLUGIN_SPEC = 'flashbake.plugins.timezone:TimeZone'

class TimeZone(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, False)
        self.share_property('tz', plugin_spec=PLUGIN_SPEC)

    def addcontext(self, message_file, config):
        """ Add the system's time zone to the commit context. """

        zone = findtimezone(config)

        if zone == None:
            message_file.write('Couldn\'t determine time zone.\n')
        else:
            message_file.write('Current time zone is %s\n' % zone)

        return True

def findtimezone(config):
    # check the environment for the zone value
    zone = os.environ.get("TZ")

    logging.debug('Zone from env is %s.' % zone)

    # some desktops don't set the env var but /etc/timezone should
    # have the value regardless
    if None != zone:
        logging.debug('Returning env var value.')
        return zone

    # this is common on many *nix variatns
    logging.debug('Checking /etc/timezone')
    if os.path.exists('/etc/timezone'):
        zone_file = open('/etc/timezone')

        try:
            zone = zone_file.read()
        finally:
            zone_file.close()
        zone = zone.replace("\n", "")
        return zone

    # this is specific to OS X
    logging.debug('Checking /etc/localtime')
    if os.path.exists('/etc/localtime'):
        zone = os.path.realpath('/etc/localtime')
        (zone, city) = os.path.split(zone);
        (zone, continent) = os.path.split(zone);
        zone = os.path.join(continent, city)
        return zone

    logging.debug('Checking .flashbake')
    if 'timezone' in config.__dict__:
        zone = config.timezone
        return zone

    logging.warn('Could not get TZ from env var, /etc/timezone, or .flashbake.')
    zone = None

    return zone

########NEW FILE########
__FILENAME__ = uptime
#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''  uptime.py - Stock plugin to calculate the system's uptime and add to the commit message.'''

from flashbake.plugins import AbstractMessagePlugin
from subprocess import Popen, PIPE
import flashbake
import logging
import os.path



class UpTime(AbstractMessagePlugin):
    def addcontext(self, message_file, config):
        """ Add the system's up time to the commit context. """

        uptime = self.__calcuptime()

        if uptime == None:
            message_file.write('Couldn\'t determine up time.\n')
        else:
            message_file.write('System has been up %s\n' % uptime)

        return True

    def __calcuptime(self):
        """ copied with blanket permission from
            http://thesmithfam.org/blog/2005/11/19/python-uptime-script/ """

        if not os.path.exists('/proc/uptime'):
            return self.__run_uptime()

        f = open("/proc/uptime")
        try:
            contents = f.read().split()
        except:
            return None
        finally:
            f.close()

        total_seconds = float(contents[0])

        # Helper vars:
        MINUTE = 60
        HOUR = MINUTE * 60
        DAY = HOUR * 24

        # Get the days, hours, etc:
        days = int(total_seconds / DAY)
        hours = int((total_seconds % DAY) / HOUR)
        minutes = int((total_seconds % HOUR) / MINUTE)
        seconds = int(total_seconds % MINUTE)

        # Build up the pretty string (like this: "N days, N hours, N minutes, N seconds")
        string = ""
        if days > 0:
            string += str(days) + " " + (days == 1 and "day" or "days") + ", "
        if len(string) > 0 or hours > 0:
            string += str(hours) + " " + (hours == 1 and "hour" or "hours") + ", "
        if len(string) > 0 or minutes > 0:
            string += str(minutes) + " " + (minutes == 1 and "minute" or "minutes") + ", "
        string += str(seconds) + " " + (seconds == 1 and "second" or "seconds")

        return string

    def __run_uptime(self):
        """ For OSes that don't provide procfs, then try to use the updtime command.
        
            Thanks to Tony Giunta for this contribution. """
        if not flashbake.executable_available('uptime'):
            return None

        # Try to capture output of 'uptime' command, 
        # if not found, catch OSError, log and return None
        try:
            output = Popen("uptime", stdout=PIPE).communicate()[0].split()
        except OSError:
            logging.warn("Can't find 'uptime' command in $PATH")
            return None

        # Parse uptime output string
        # if len == 10 or 11, uptime is less than a day
        if len(output) in [10, 11]:
            days = "00"
            hours_and_minutes = output[2].strip(",")
        elif len(output) == 12:
            days = output[2]
            hours_and_minutes = output[4].strip(",")
        else:
            return None

        # If time is exactly x hours/mins, no ":" in "hours_and_minutes" 
        # and the interpreter will throw a ValueError
        try:
            hours, minutes = hours_and_minutes.split(":")
        except ValueError:
            if output[3].startswith("hr"):
                hours = hours_and_minutes
                minutes = "00"
            elif output[3].startwwith("min"):
                hours = "00"
                minutes = hours_and_minutes
            else:
                return None

        # Build up output string, might require Python 2.5+
        uptime = (days + (" day, " if days == "1" else " days, ") + 
                hours + (" hour, " if hours == "1" else " hours, ") + 
                minutes + (" minute" if minutes == "1" else " minutes"))

        return uptime


########NEW FILE########
__FILENAME__ = weather
#    copyright 2009 Thomas Gideon
#    Modified 2013 Bryan Fordham <bfordham@gmail.com>
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''  weather.py - Stock plugin for adding weather information to context, must have TZ or
 /etc/localtime available to determine city from ISO ID. '''

from flashbake.plugins import AbstractMessagePlugin
from flashbake.plugins.timezone import findtimezone
from flashbake.plugins import timezone
from urllib2 import HTTPError, URLError
import json
import logging
import re
import urllib
import urllib2



class Weather(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, True)
        self.define_property('city')
        self.define_property('units', required=False, default='imperial')
        self.share_property('tz', plugin_spec=timezone.PLUGIN_SPEC)
        ## plugin uses location_location from Location plugin
        self.share_property('location_location')

    def addcontext(self, message_file, config):
        """ Add weather information to the commit message. Looks for
            weather_city: first in the config information but if that is not
            set, will try to use the system time zone to identify a city. """
        if config.location_location == None and self.city == None:
            zone = findtimezone(config)
            if zone == None:
                city = None
            else:
                city = self.__parsecity(zone)
        else:
            if config.location_location == None:
                city = self.city
            else:
                city = config.location_location

        if None == city:
            message_file.write('Couldn\'t determine city to fetch weather.\n')
            return False

        # call the open weather map API with the city
        weather = self.__getweather(city, self.units)

        if len(weather) > 0:
            message_file.write('Current weather for %(city)s: %(description)s. %(temp)i%(temp_units)s. %(humidity)s%% humidity\n'
                    % weather)
        else:
            message_file.write('Couldn\'t fetch current weather for city, %s.\n' % city)
        return len(weather) > 0

    def __getweather(self, city, units='imperial'):
        """ This relies on Open Weather Map's API which may change without notice. """

        baseurl = 'http://api.openweathermap.org/data/2.5/weather?'
        # encode the parameters
        for_city = baseurl + urllib.urlencode({'q': city, 'units': units})

        try:
            logging.debug('Requesting page for %s.' % for_city)
            
            # Get the json-encoded string
            raw = urllib2.urlopen(for_city).read()
        
            # Convert it to something usable
            data = json.loads(raw)

            # Grab the information we want
            weather = dict()
            
            for k,v in (data['weather'][0]).items():
              weather[k] = v

            for k,v in data['main'].items():
              weather[k] = v

            weather['city'] = city
            
            if units == 'imperial':
              weather['temp_units'] = 'F'
            elif units == 'metric':
              weather['temp_units'] = 'C'
            else:
              weather['temp_units'] = 'K'

            return weather
        except HTTPError, e:
            logging.error('Failed with HTTP status code %d' % e.code)
            return {}
        except URLError, e:
            logging.error('Plugin, %s, failed to connect with network.' % self.__class__)
            logging.debug('Network failure reason, %s.' % e.reason)
            return {}

    def __parsecity(self, zone):
        if None == zone:
            return None
        tokens = zone.split("/")
        if len(tokens) != 2:
            logging.warning('Zone id, "%s", doesn''t appear to contain a city.' % zone)
            # return non-zero so calling shell script can catch
            return None

        city = tokens[1]
        # ISO id's have underscores, convert to spaces for the Google API
        return city.replace("_", " ")

########NEW FILE########
__FILENAME__ = config
from flashbake import ControlConfig
from flashbake.plugins import PluginError
import unittest


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.config = ControlConfig()

    def testinvalidspec(self):
        try:
            self.config.create_plugin('test.foo')
            self.fail('Should not be able to use unknown')
        except PluginError, error:
            self.assertEquals(str(error.reason), 'invalid_plugin',
                    'Should not be able to load invalid plugin.')

    def testnoplugin(self):
        try:
            self.config.create_plugin('test.foo:Foo')
            self.fail('Should not be able to use unknown')
        except PluginError, error:
            self.assertEquals(str(error.reason), 'unknown_plugin',
                    'Should not be able to load unknown plugin.')

    def testmissingparent(self):
        try:
            plugin_name = 'test.plugins:MissingParent'
            self.config.create_plugin(plugin_name)
            self.fail('Should not have initialized plugin, %s' % plugin_name)
        except PluginError, error:
            reason = 'invalid_type'
            self.assertEquals(str(error.reason), reason,
                    'Error should specify failure reason, %s.' % reason)

    def testnoconnectable(self):
        self.__testattr('test.plugins:NoConnectable', 'connectable', 'missing_attribute')

    def testwrongconnectable(self):
        self.__testattr('test.plugins:WrongConnectable', 'connectable', 'invalid_attribute')

    def testnoaddcontext(self):
        try:
            self.config.plugin_names = ['test.plugins:NoAddContext']
            from flashbake.context import buildmessagefile
            buildmessagefile(self.config)
            self.fail('Should raise a NotImplementedError.')
        except NotImplementedError:
            pass

    def testwrongaddcontext(self):
        self.__testattr('test.plugins:WrongAddContext', 'addcontext', 'invalid_attribute')

    def teststockplugins(self):
        self.config.extra_props['feed_url'] = "http://random.com/feed"

        plugins = ('flashbake.plugins.weather:Weather',
                'flashbake.plugins.uptime:UpTime',
                'flashbake.plugins.timezone:TimeZone',
                'flashbake.plugins.feed:Feed')
        for plugin_name in plugins:
            plugin = self.config.create_plugin(plugin_name)
            plugin.capture_properties(self.config)
            plugin.init(self.config)

    def testnoauthorfail(self):
        """Ensure that accessing feeds with no entry.author doesn't cause failures if the
        feed_author config property isn't set."""
        self.config.plugin_names = ['flashbake.plugins.feed:Feed']
        self.config.extra_props['feed_url'] = "http://twitter.com/statuses/user_timeline/704593.rss"
        from flashbake.context import buildmessagefile
        buildmessagefile(self.config)

    def testfeedfail(self):
        try:
            plugin = self.config.create_plugin('flashbake.plugins.feed:Feed')
            plugin.capture_properties(self.config)
            self.fail('Should not be able to initialize without full plugin props.')
        except PluginError, error:
            self.assertEquals(str(error.reason), 'missing_property',
                    'Feed plugin should fail missing property.')
            self.assertEquals(error.name, 'feed_url',
                    'Missing property should be feed.')

        self.config.extra_props['feed_url'] = "http://random.com/feed"

        try:
            plugin = self.config.create_plugin('flashbake.plugins.feed:Feed')
            plugin.capture_properties(self.config)
        except PluginError, error:
            self.fail('Should be able to initialize with just the url.')

    def __testattr(self, plugin_name, name, reason):
        try:
            plugin = self.config.create_plugin(plugin_name)
            plugin.capture_properties(self.config)
            plugin.init(self.config)
            self.fail('Should not have initialized plugin, %s' % plugin_name)
        except PluginError, error:
            self.assertEquals(str(error.reason), reason,
                    'Error should specify failure reason, %s.' % reason)
            self.assertEquals(error.name, name,
                    'Error should specify failed name, %s' % name)

########NEW FILE########
__FILENAME__ = files
import commands
import flashbake
import os.path
import unittest

class FilesTestCase(unittest.TestCase):
    def setUp(self):
        test_dir = os.path.join(os.getcwd(), 'test')
        test_zip = os.path.join(test_dir, 'project.zip')
        commands.getoutput('unzip -d %s %s' % (test_dir, test_zip))
        self.files = flashbake.HotFiles(os.path.join(test_dir, 'project'))
        self.project_files = [ 'todo.txt', 'stickies.txt', 'my stuff.txt',
        'bar/novel.txt', 'baz/novel.txt', 'quux/novel.txt' ]

    def tearDown(self):
        commands.getoutput('rm -rf %s' % self.files.project_dir)

    def testrelative(self):
        for file in self.project_files:
            self.files.addfile(file)
            self.assertTrue(file in self.files.control_files,
                    'Should contain relative file, %s' % file)
        count = len(self.files.control_files)
        self.files.addfile('*add*')
        self.assertEquals(len(self.files.control_files), count + 3,
                'Should have expanded glob.')

    def testabsolute(self):
        for file in self.project_files:
            abs_file = os.path.join(self.files.project_dir, file)
            self.files.addfile(abs_file)
            self.assertTrue(file in self.files.control_files,
                    'Should contain absolute file, %s, as relative path, %s.'
                    % (abs_file, file))
        count = len(self.files.control_files)
        self.files.addfile(os.path.join(self.files.project_dir, '*add*'))
        self.assertEquals(len(self.files.control_files), count + 3,
                'Should have expanded glob.')

    def testabsent(self):
        self.files.addfile('does not exist.txt')
        self.files.addfile('doesn\'t exist.txt')
        self.files.addfile('does{not}exist.txt')
        self.assertEquals(len(self.files.not_exists), 3,
                'None of the provided files should exist')

    def testoutside(self):
        self.files.addfile('/tmp')
        self.assertEquals(len(self.files.outside_files), 1,
                'Outside files should get caught')

    def testlinks(self):
        self.files.addfile('link/novel.txt')
        self.assertEquals(len(self.files.linked_files.keys()), 1,
                'Linked files should get caught')

########NEW FILE########
__FILENAME__ = plugins
from flashbake import ControlConfig
import flashbake.plugins
import logging
import unittest



class FilesTestCase(unittest.TestCase):
    def setUp(self):
        self.config = ControlConfig()

    def testrelative(self):
        pass

class MissingParent():
    def __init__(self, plugin_spec):
        pass

    def addcontext(self, message_file, control_config):
        logging.debug('do nothing')

class NoConnectable(flashbake.plugins.AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        pass

    def addcontext(self, message_file, control_config):
        logging.debug('do nothing')

class NoAddContext(flashbake.plugins.AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        flashbake.plugins.AbstractMessagePlugin.__init__(self, plugin_spec, True)

class WrongConnectable(flashbake.plugins.AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        self.connectable = 1

    def addcontext(self, message_file, control_config):
        logging.debug('do nothing')

class WrongAddContext(flashbake.plugins.AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        self.connectable = True
        self.addcontext = 1

class Plugin1(flashbake.plugins.AbstractMessagePlugin):
    """ Sample plugin. """

    def addcontext(self, message_file, config):
        """ Stub. """
        pass

class Plugin2(flashbake.plugins.AbstractMessagePlugin):
    """ Sample plugin. """
    
    def dependencies(self):
        return ['test.plugins:Plugin1']

    def addcontext(self, message_file, config):
        """ Stub. """
        pass

class Plugin3(flashbake.plugins.AbstractMessagePlugin):
    """ Sample plugin. """
    
    def dependencies(self):
        return ['test.plugins:Plugin1', 'text.plugins:Plugin2']

    def addcontext(self, message_file, config):
        """ Stub. """
        pass

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python

'''  test -  test runner script '''

#    copyright 2009 Thomas Gideon
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

import sys
from os.path import join, realpath, abspath
import unittest
import logging



# just provide the command line hook into the tests
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
            format='%(message)s')

    LAUNCH_DIR = abspath(sys.path[0])
    flashbake_dir = join(LAUNCH_DIR, "..")

    sys.path.insert(0, realpath(flashbake_dir))
    try:
        from flashbake.commit import commit #@UnusedImport
        from flashbake.control import parse_control #@UnusedImport
        from flashbake.context import buildmessagefile #@UnusedImport
        import test.config
        import test.files
    finally:
        del sys.path[0]

    # combine classes into single suite
    config_suite = unittest.TestLoader().loadTestsFromTestCase(test.config.ConfigTestCase)
    files_suite = unittest.TestLoader().loadTestsFromTestCase(test.files.FilesTestCase)
    suite = unittest.TestSuite([config_suite, files_suite])
    unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
