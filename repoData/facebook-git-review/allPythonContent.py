__FILENAME__ = args
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
from exceptions import *
import command
import tokenize


class ParsedArgs(object):
    pass


class ArgCommand(command.Command):
    def __init__(self, args, help):
        self.argTypes = args
        self.helpText = help

    def run(self, cli_obj, name, args, line):
        args = args[1:]
        num_args = len(args)
        num_arg_types = len(self.argTypes)

        if num_args > num_arg_types:
            trailing_args = args[num_arg_types:]
            msg = 'trailing arguments: ' + tokenize.escape_args(trailing_args)
            raise CommandArgumentsError(msg)

        parsed_args = ParsedArgs()
        for n in range(num_args):
            arg_type = self.argTypes[n]
            value = arg_type.parse(cli_obj, args[n])
            setattr(parsed_args, arg_type.getName(), value)

        if num_args < num_arg_types:
            # Make sure the remaining options are optional
            # (The next argument must be marked as optional.
            # The optional flag on arguments after this doesn't matter.)
            arg_type = self.argTypes[num_args]
            if not arg_type.isOptional():
                msg = 'missing %s' % (arg_type.getHrName(),)
                raise CommandArgumentsError(msg)

        for n in range(num_args, num_arg_types):
            arg_type = self.argTypes[n]
            setattr(parsed_args, arg_type.getName(), arg_type.getDefaultValue())

        return self.runParsed(cli_obj, name, parsed_args)

    def help(self, cli_obj, name, args, line):
        args = args[1:]
        syntax = name
        end = ''
        for arg in self.argTypes:
            if arg.isOptional():
                syntax += ' [<%s>' % (arg.getName(),)
                end += ']'
            else:
                syntax += ' <%s>' % (arg.getName(),)
        syntax += end

        cli_obj.output(syntax)
        if not self.helpText:
            return

        # FIXME: do nicer formatting of the help message
        cli_obj.output()
        cli_obj.output(self.helpText)

    def complete(self, cli_obj, name, args, text):
        args = args[1:]
        index = len(args)
        try:
            arg_type = self.argTypes[index]
        except IndexError:
            return []

        return arg_type.complete(cli_obj, text)


class Argument(object):
    def __init__(self, name, **kwargs):
        self.name = name
        self.hrName = name
        self.default = None
        self.optional = False

        for (kwname, kwvalue) in kwargs.items():
            if kwname == 'default':
                self.default = kwvalue
            elif kwname == 'hr_name':
                self.hrName = kwvalue
            elif kwname == 'optional':
                self.optional = kwvalue
            else:
                raise TypeError('unknown keyword argument %r' % (kwname,))

    def getName(self):
        return self.name

    def getHrName(self):
        """
        arg.getHrName() --> string

        Get the human-readable name.
        """
        return self.hrName

    def isOptional(self):
        return self.optional

    def getDefaultValue(self):
        return self.default

    def complete(self, cli_obj, text):
        return []


class StringArgument(Argument):
    def parse(self, cli_obj, arg):
        return arg


class IntArgument(Argument):
    def __init__(self, name, **kwargs):
        self.min = None
        self.max = None

        arg_kwargs = {}
        for (kwname, kwvalue) in kwargs.items():
            if kwname == 'min':
                self.min = kwvalue
            elif kwname == 'max':
                self.max = max
            else:
                arg_kwargs[kwname] = kwvalue

        Argument.__init__(self, name, **arg_kwargs)

    def parse(self, cli_obj, arg):
        try:
            value = int(arg)
        except ValueError:
            msg = '%s must be an integer' % (self.getHrName(),)
            raise CommandArgumentsError(msg)

        if self.min != None and value < self.min:
            msg = '%s must be greater than %s' % (self.getHrName(), self.min)
            raise CommandArgumentsError(msg)
        if self.max != None and value > self.max:
            msg = '%s must be less than %s' % (self.getHrName(), self.max)
            raise CommandArgumentsError(msg)

        return value

########NEW FILE########
__FILENAME__ = command
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
from exceptions import *


class Command(object):
    def run(self, cli, name, args, line):
        raise NotImplementedError('subclasses of Command must implement run()')

    def help(self, cli, name, args, line):
        raise NotImplementedError('subclasses of Command must implement help()')

    def complete(self, cli, name, args, text):
        # By default, no completion is performed
        return []


class HelpCommand(Command):
    def run(self, cli_obj, name, args, line):
        if len(args) < 2:
            for cmd_name in cli_obj.commands:
                cli_obj.output(cmd_name)
        else:
            cmd_name = args[1]
            try:
                cmd = cli_obj.getCommand(cmd_name)
                cmd.help(cli_obj, cmd_name, args[1:], line)
            except (NoSuchCommandError, AmbiguousCommandError), ex:
                cli_obj.outputError(ex)

    def help(self, cli_obj, name, args, line):
        cli_obj.output('%s [<command>]' % (args[0],))
        cli_obj.output()
        cli_obj.output('Display help')

    def complete(self, cli_obj, name, args, text):
        if len(args) == 1:
            return cli_obj.completeCommand(text, add_space=True)
        return []

########NEW FILE########
__FILENAME__ = exceptions
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
class CLIError(Exception):
    pass


class NoSuchCommandError(CLIError):
    def __init__(self, cmd_name):
        CLIError.__init__(self, 'no such command %r' % (cmd_name,))
        self.cmd = cmd_name


class AmbiguousCommandError(CLIError):
    def __init__(self, cmd_name, matches):
        msg = 'ambiguous command %r: possible matches: %r' % \
                (cmd_name, matches)
        CLIError.__init__(self, msg)
        self.cmd = cmd_name
        self.matches = matches


class CommandArgumentsError(CLIError):
    pass

########NEW FILE########
__FILENAME__ = tokenize
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import re

class TokenizationError(Exception):
    pass


class PartialTokenError(TokenizationError):
    def __init__(self, token, msg):
        TokenizationError.__init__(self, msg)
        self.token = token
        self.error = msg


class State(object):
    def handleChar(self, tokenizer, char):
        raise NotImplementedError()

    def handleEnd(self, tokenizer):
        raise NotImplementedError()


class EscapeState(State):
    def handleChar(self, tokenizer, char):
        tokenizer.addToToken(char)
        tokenizer.popState()

    def handleEnd(self, tokenizer):
        # XXX: We could treat this as an indication to continue on to the next
        # line.
        msg = 'unterminated escape sequence'
        raise PartialTokenError(tokenizer.getPartialToken(), msg)


class QuoteState(State):
    def __init__(self, quote_char, escape_chars = '\\'):
        State.__init__(self)
        self.quote = quote_char
        self.escapeChars = escape_chars

    def handleChar(self, tokenizer, char):
        if char == self.quote:
            tokenizer.popState()
        elif char in self.escapeChars:
            tokenizer.pushState(EscapeState())
        else:
            tokenizer.addToToken(char)

    def handleEnd(self, tokenizer):
        msg = 'unterminated quote'
        raise PartialTokenError(tokenizer.getPartialToken(), msg)


class NormalState(State):
    def __init__(self):
        State.__init__(self)
        self.quoteChars = '"\''
        self.escapeChars = '\\'
        self.delimChars = ' \t\n'

    def handleChar(self, tokenizer, char):
        if char in self.escapeChars:
            tokenizer.pushState(EscapeState())
        elif char in self.quoteChars:
            tokenizer.addToToken('')
            tokenizer.pushState(QuoteState(char, self.escapeChars))
        elif char in self.delimChars:
            tokenizer.endToken()
        else:
            tokenizer.addToToken(char)

    def handleEnd(self, tokenizer):
        tokenizer.endToken()


class Tokenizer(object):
    """
    A class for tokenizing strings.

    It isn't particularly efficient.  Performance-wise, it is probably quite
    slow.  However, it is intended to be very customizable.  It provides many
    hooks to allow subclasses to override and extend its behavior.
    """
    STATE_NORMAL        = 0
    STATE_IN_QUOTE      = 1

    def __init__(self, state, value):
        self.value = value
        self.index = 0
        self.end = len(self.value)

        if isinstance(state, list):
            self.stateStack = state[:]
        else:
            self.stateStack = [state]

        self.currentToken = None
        self.tokens = []

        self.__processedEnd = False

    def getTokens(self, stop_at_end=True):
        tokens = []

        while True:
            token = self.getNextToken(stop_at_end)
            if token == None:
                break
            tokens.append(token)

        return tokens

    def getNextToken(self, stop_at_end=True):
        # If we don't currently have any tokens to process,
        # call self.processNextChar()
        while not self.tokens:
            if (not stop_at_end) and self.index >= self.end:
                # If stop_at_end is True, we let processNextChar()
                # handle the end of string as normal.  However, if stop_at_end
                # is False, the string value we have received so far is partial
                # (the caller might append more to it later), so return None
                # here without handling the end of the string.
                return None
            if self.__processedEnd:
                # If there are no more tokens and we've already reached
                # the end of the string, return None
                return None
            self.processNextChar()

        return self.__popToken()

    def __popToken(self):
        token = self.tokens[0]
        del self.tokens[0]
        return token

    def getPartialToken(self):
        return self.currentToken

    def processNextChar(self):
        if self.index >= self.end:
            if self.__processedEnd:
                raise IndexError()
            self.__processedEnd = True
            state = self.stateStack[-1]
            state.handleEnd(self)
            return

        char = self.value[self.index]
        self.index += 1

        state = self.stateStack[-1]
        state.handleChar(self, char)

    def pushState(self, state):
        self.stateStack.append(state)

    def popState(self):
        self.stateStack.pop()
        if not self.stateStack:
            raise Exception('cannot pop last state')

    def addToToken(self, char):
        if self.currentToken == None:
            self.currentToken = char
        else:
            self.currentToken += char

    def endToken(self):
        if self.currentToken == None:
            return

        self.tokens.append(self.currentToken)
        self.currentToken = None


class SimpleTokenizer(Tokenizer):
    def __init__(self, value):
        Tokenizer.__init__(self, [NormalState()], value)


def escape_arg(arg):
    """
    escape_arg(arg) --> escaped_arg

    This performs string escaping that can be used with SimpleTokenizer.
    (It isn't sufficient for passing strings to a shell.)
    """
    if arg.find('"') >= 0:
        if arg.find("'") >= 0:
            s = re.sub(r'\\', r'\\\\', arg)
            s = re.sub("'", "\\'", s)
            return "'%s'" % (s,)
        else:
            return "'%s'" % (arg,)
    elif arg.find("'") >= 0:
        return '"%s"' % (arg,)
    else:
        return arg


def escape_args(args):
    return ' '.join([escape_arg(a) for a in args])

########NEW FILE########
__FILENAME__ = commit
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import datetime
import os
import time

import gitreview.proc as proc

from exceptions import *
import constants
import obj as git_obj


class GitTimezone(datetime.tzinfo):
    """
    This class represents the timezone part of a git timestamp.
    Timezones are represented as "-HHMM" or "+HHMM".
    """
    def __init__(self, tz_str):
        self.name = tz_str

        tz = int(tz_str)
        min_offset = tz % 100
        hour_offset = tz / 100
        self.offset = datetime.timedelta(hours = hour_offset,
                                         minutes = min_offset)

    def utcoffset(self, dt):
        return self.offset

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return self.name


class AuthorInfo(object):
    """
    An AuthorInfo object represents the committer or author information
    associated with a commit.  It contains a name, email address, and
    timestamp.
    """
    def __init__(self, real_name, email, timestamp):
        self.realName = real_name
        self.email = email
        self.timestamp = timestamp

    def __str__(self):
        return '%s <%s> %s' % (self.realName, self.email, self.timestamp)


class Commit(git_obj.Object):
    """
    This class represents a git commit.

    Commit objects always contain fully parsed commit information.
    """
    def __init__(self, repo, sha1, tree, parents, author, committer, comment):
        git_obj.Object.__init__(self, repo, sha1, constants.OBJ_COMMIT)
        self.tree = tree
        self.parents = parents
        self.author = author
        self.committer = committer
        self.comment = comment

    def __str__(self):
        return str(self.sha1)

    def __eq__(self, other):
        if isinstance(other, Commit):
            # If other is a Commit object, compare the SHA1 hashes
            return self.sha1 == other.sha1
        elif isinstance(other, str):
            # If other is a Commit string, it should be a SHA1 hash
            # XXX: In the future, we could also check to see if the string
            # is a ref name, and compare using that.
            return self.sha1 == other
        return False

    def getSha1(self):
        return self.sha1

    def getTree(self):
        return self.tree

    def getParents(self):
        return self.parents

    def getAuthor(self):
        return self.author

    def getCommitter(self):
        return self.committer

    def getComment(self):
        return self.comment

    def getSummary(self):
        return self.comment.split('\n', 1)[0]


def _parse_timestamp(value):
    # Note: we may raise ValueError to the caller
    (timestamp_str, tz_str) = value.split(' ', 1)

    timestamp = int(timestamp_str)
    tz = GitTimezone(tz_str)

    return datetime.datetime.fromtimestamp(timestamp, tz)


def _parse_author(commit_name, value, type):
    try:
        (real_name, rest) = value.split(' <', 1)
    except ValueError:
        msg = 'error parsing %s: no email address found' % (type,)
        raise BadCommitError(commit_name, msg)

    try:
        (email, rest) = rest.split('> ', 1)
    except ValueError:
        msg = 'error parsing %s: unterminated email address' % (type,)
        raise BadCommitError(commit_name, msg)

    try:
        timestamp = _parse_timestamp(rest)
    except ValueError:
        msg = 'error parsing %s: malformatted timestamp' % (type,)
        raise BadCommitError(commit_name, msg)

    return AuthorInfo(real_name, email, timestamp)


def _parse_header(commit_name, header):
    tree = None
    parents = []
    author = None
    committer = None

    # We accept the headers in any order.
    # git itself requires them to be tree, parents, author, committer
    for line in header.split('\n'):
        try:
            (name, value) = line.split(' ', 1)
        except ValueError:
            msg = 'bad commit header line %r' % (line)
            raise BadCommitError(commit_name, msg)

        if name == 'tree':
            if tree:
                msg = 'multiple trees specified'
                raise BadCommitError(commit_name, msg)
            tree = value
        elif name == 'parent':
            parents.append(value)
        elif name == 'author':
            if author:
                msg = 'multiple authors specified'
                raise BadCommitError(commit_name, msg)
            author = _parse_author(commit_name, value, name)
        elif name == 'committer':
            if committer:
                msg = 'multiple committers specified'
                raise BadCommitError(commit_name, msg)
            committer = _parse_author(commit_name, value, name)
        else:
            msg = 'unknown header field %r' % (name,)
            raise BadCommitError(commit_name, msg)

    if not tree:
        msg = 'no tree specified'
        raise BadCommitError(commit_name, msg)
    if not author:
        msg = 'no author specified'
        raise BadCommitError(commit_name, msg)
    if not committer:
        msg = 'no committer specified'
        raise BadCommitError(commit_name, msg)

    return (tree, parents, author, committer)


def _get_current_tzinfo():
    if time.daylight:
        tz_sec = time.altzone
    else:
        tz_sec = time.daylight
    tz_min = (abs(tz_sec) / 60) % 60
    tz_hour = abs(tz_sec) / 3600
    if tz_sec > 0:
        tz_hour *= -1
    tz_str = '%+02d%02d' % (tz_hour, tz_min)
    return GitTimezone(tz_str)


def _get_bogus_author():
    # we could use datetime.datetime.now(),
    # but this way we don't get microseconds, so it looks more like a regular
    # git timestamp
    now = time.localtime()
    current_tz = _get_current_tzinfo()
    timestamp = datetime.datetime(now.tm_year, now.tm_mon, now.tm_mday,
                                  now.tm_hour, now.tm_min, now.tm_sec, 0,
                                  current_tz)

    return AuthorInfo('No Author Yet', 'nobody@localhost', timestamp)


def get_index_commit(repo):
    """
    get_index_commit(repo) --> commit

    Get a fake Commit object representing the changes currently in the index.
    """
    tree = os.path.join(repo.getGitDir(), 'index')
    parents = [constants.COMMIT_HEAD]
    author = _get_bogus_author()
    committer = _get_bogus_author()
    comment = 'Uncommitted changes in the index'
    # XXX: it might be better to define a separate class for this
    return Commit(repo, constants.COMMIT_INDEX, tree, parents,
                  author, committer, comment)


def get_working_dir_commit(repo):
    """
    get_working_dir_commit(repo) --> commit

    Get a fake Commit object representing the changes currently in the working
    directory.
    """
    tree = repo.getWorkingDir()
    if not tree:
        tree = '<none>'
    parents = [constants.COMMIT_INDEX]
    author = _get_bogus_author()
    committer = _get_bogus_author()
    comment = 'Uncomitted changes in the working directory'
    # XXX: it might be better to define a separate class for this
    return Commit(repo, constants.COMMIT_WD, tree, parents, author, committer,
                  comment)


def get_commit(repo, name):
    # Handle the special internal commit names COMMIT_INDEX and COMMIT_WD
    if name == constants.COMMIT_INDEX:
        return get_index_commit(repo)
    elif name == constants.COMMIT_WD:
        return get_working_dir_commit(repo)

    # Get the SHA1 value for this commit.
    sha1 = repo.getCommitSha1(name)

    # Run "git cat-file commit <name>"
    cmd = ['cat-file', 'commit', str(name)]
    out = repo.runSimpleGitCmd(cmd)

    # Split the header and body
    try:
        (header, body) = out.split('\n\n', 1)
    except ValueError:
        # split() resulted in just one value
        # Treat it as headers, with an empty body
        header = out
        if header and header[-1] == '\n':
            header = header[:-1]
        body = ''

    # Parse the header
    (tree, parents, author, committer) = _parse_header(name, header)

    return Commit(repo, sha1, tree, parents, author, committer, body)


def split_rev_name(name):
    """
      Split a revision name into a ref name and suffix.

      The suffix starts at the first '^' or '~' character.  These characters
      may not be part of a ref name.  See git-rev-parse(1) for full details.

      For example:
          split_ref_name('HEAD^^') --> ('HEAD', '^^')
          split_ref_name('HEAD~10') --> ('HEAD', '~')
          split_ref_name('master') --> ('master', '')
          split_ref_name('master^{1}') --> ('master', '^{1}')
    """
    # This command shouldn't be called with commit ranges.
    if name.find('..') > 0:
        raise BadRevisionNameError(name, 'specifies a commit range, '
                                   'not a single commit')

    caret_idx = name.find('^')
    tilde_idx = name.find('~')
    if caret_idx < 0:
        if tilde_idx < 0:
            # No suffix
            return (name, '')
        else:
            idx = tilde_idx
    else:
        if tilde_idx < 0:
            idx = caret_idx
        else:
            idx = min(caret_idx, tilde_idx)

    return (name[:idx], name[idx:])

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import gitreview.proc as proc

from exceptions import *
import constants


class Config(object):
    def __init__(self):
        self.__contents = {}

    def get(self, name, default=NoSuchConfigError):
        try:
            value_list = self.__contents[name]
        except KeyError:
            if default == NoSuchConfigError:
                raise NoSuchConfigError(name)
            return default

        if len(value_list) != 1:
            # self.__contents shouldn't contain any empty value lists,
            # so we assume the problem is that there is more than 1 value
            raise MultipleConfigError(name)

        return value_list[0]

    def getAll(self, name):
        try:
            return self.__contents[name]
        except KeyError:
            raise NoSuchConfigError(name)

    def getBool(self, name, default=NoSuchConfigError):
        try:
            # Don't pass default to self.get()
            # If name isn't present, we want to return default as-is,
            # rather without trying to convert it to a bool below.
            value = self.get(name)
        except NoSuchConfigError:
            if default == NoSuchConfigError:
                raise # re-raise the original error
            return default

        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False

        try:
            int_value = int(value)
        except ValueError:
            raise BadConfigError(name, value)

        if int_value == 1:
            return True
        elif int_value == 0:
            return False

        raise BadConfigError(name, value)

    def set(self, name, value):
        self.__contents[name] = [value]

    def add(self, name, value):
        if self.__contents.has_key(name):
            self.__contents[name].append(value)
        else:
            self.__contents[name] = [value]



def parse(config_output):
    config = Config()

    lines = config_output.split('\n')
    for line in lines:
        if not line:
            continue
        (name, value) = line.split('=', 1)
        config.add(name, value)

    return config


def _load(where):
    cmd = [constants.GIT_EXE, where, 'config', '--list']
    cmd_out = proc.run_simple_cmd(cmd)
    return parse(cmd_out)


def load(git_dir):
    # This will return the merged configuration from the specified repository,
    # as well as the user's global config and the system config
    where = '--git-dir=' + str(git_dir)
    return _load(where)


def load_file(path):
    where = '--file=' + str(path)
    return _load(where)


def load_global(path):
    where = '--global'
    return _load(where)


def load_system(path):
    where = '--system'
    return _load(where)

########NEW FILE########
__FILENAME__ = constants
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

GIT_EXE = 'git'

# Constants for commit names
COMMIT_HEAD = 'HEAD'
# COMMIT_WORKING_DIR is not supported by git; it is used only
# internally by our code.
COMMIT_WORKING_DIR = COMMIT_WD = ':wd'
# COMMIT_INDEX is not supported by git; it is used only
# internally by our code.
COMMIT_INDEX = ':0'

# Object types
OBJ_COMMIT      = 'commit'
OBJ_TREE        = 'tree'
OBJ_BLOB        = 'blob'
OBJ_TAG         = 'tag'

########NEW FILE########
__FILENAME__ = diff
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import re
import UserDict

import gitreview.proc as proc

from exceptions import *
import constants


class Status(object):
    ADDED               = 'A'
    COPIED              = 'C'
    DELETED             = 'D'
    MODIFIED            = 'M'
    RENAMED             = 'R'
    TYPE_CHANGED        = 'T'
    UNMERGED            = 'U'
    # internally, git also defines 'X' for unknown

    def __init__(self, str_value):
        if str_value == 'A':
            self.status = self.ADDED
        elif str_value.startswith('C'):
            self.status = self.COPIED
            self.similarityIndex = self.__parseSimIndex(str_value[1:])
        elif str_value == 'D':
            self.status = self.DELETED
        elif str_value == 'M':
            self.status = self.MODIFIED
        elif str_value.startswith('R'):
            self.status = self.RENAMED
            self.similarityIndex = self.__parseSimIndex(str_value[1:])
        elif str_value == 'T':
            self.status = self.TYPE_CHANGED
        elif str_value == 'U':
            self.status = self.UNMERGED
        else:
            raise ValueError('unknown status type %r' % (str_value))

    def __parseSimIndex(self, sim_index_str):
        similarity_index = int(sim_index_str)
        if similarity_index < 0 or similarity_index > 100:
            raise ValueError('invalid similarity index %r' % (sim_index_str))
        return similarity_index

    def getChar(self):
        """
        Get the single character representation of this status.
        """
        return self.status

    def getDescription(self):
        """
        Get the text description of this status.
        """
        if self.status == self.ADDED:
            return 'added'
        elif self.status == self.COPIED:
            return 'copied'
        elif self.status == self.DELETED:
            return 'deleted'
        elif self.status == self.MODIFIED:
            return 'modified'
        elif self.status == self.RENAMED:
            return 'renamed'
        elif self.status == self.TYPE_CHANGED:
            return 'type changed'
        elif self.status == self.UNMERGED:
            return 'unmerged'

        raise ValueError(self.status)

    def __str__(self):
        if self.status == self.RENAMED or self.status == self.COPIED:
            return '%s%03d' % (self.status, self.similarityIndex)
        return self.status

    def __repr__(self):
        return 'Status(%s)' % (self,)

    def __eq__(self, other):
        if isinstance(other, Status):
            # Note: we ignore the similarty index for renames and copies
            return self.status == other.status
        # Compare self.status to other.
        # This allows (status_obj == Status.RENAMED) to work
        return self.status == other


class BlobInfo(object):
    """Info about a git blob"""
    def __init__(self, sha1, path, mode):
        self.sha1 = sha1
        self.path = path
        self.mode = mode


class DiffEntry(object):
    def __init__(self, old_mode, new_mode, old_sha1, new_sha1, status,
                 old_path, new_path):
        self.old = BlobInfo(old_sha1, old_path, old_mode)
        self.new = BlobInfo(new_sha1, new_path, new_mode)
        self.status = status

    def __str__(self):
        if self.status == Status.RENAMED or self.status == Status.COPIED:
            return 'DiffEntry(%s: %s --> %s)' % \
                    (self.status, self.old.path, self.new.path)
        else:
            return 'DiffEntry(%s: %s)' % (self.status, self.getPath())

    def reverse(self):
        tmp_info = self.old
        self.old = self.new
        self.new = tmp_info

        if self.status == Status.ADDED:
            self.status = Status(Status.DELETED)
        elif self.status == Status.COPIED:
            self.status = Status(Status.DELETED)
            self.new = BlobInfo('0000000000000000000000000000000000000000',
                                None, '000000')
        elif self.status == Status.DELETED:
            # Note: we have no way to tell if the file deleted is similar to
            # an existing file, so we can't tell if the reversed operation
            # should be Status.COPIED or Status.ADDED.  This shouldn't really
            # be a big issue in practice, however.  Needing to reverse info
            # should be rare, and failing to detect a copy isn't a big deal.
            self.status = Status(Status.ADDED)

    def getPath(self):
        if self.new.path:
            return self.new.path
        # new.path is None when the status is Status.DELETED,
        # so return old.path
        return self.old.path


class DiffFileList(UserDict.DictMixin):
    def __init__(self, parent, child):
        self.parent = parent
        self.child = child
        self.entries = {}

    def add(self, entry):
        path = entry.getPath()
        if self.entries.has_key(path):
            # For unmerged files, "git diff --raw" will output a "U"
            # line, with the SHA1 IDs set to all 0.
            # Depending on how the file was changed, it will usually also
            # output a normal "M" line, too.
            #
            # For unmerged entries, merge these two entries.
            old_entry = self.entries[path]
            if entry.status == Status.UNMERGED:
                # Just update the status on the old_entry to UNMERGED.
                # Keep all other data from the old entry.
                old_entry.status = Status.UNMERGED
                return
            elif old_entry.status == Status.UNMERGED:
                # Update the new entry's status to Status.UNMERGED, then
                # fall through and overwrite the old, unmerged entry
                entry.status = old_entry.status
                pass
            else:
                # We don't expect duplicate entries in any other case.
                msg = 'diff list already contains an entry for %s' % (path,)
                raise GitError(msg)
        self.entries[path] = entry

    def __repr__(self):
        return 'DiffFileList(' + repr(self.entries) + ')'

    def __getitem__(self, key):
        return self.entries[key]

    def keys(self):
        return self.entries.keys()

    def __delitem__(self, key):
        raise TypeError('DiffFileList is non-modifiable')

    def __setitem__(self, key, value):
        raise TypeError('DiffFileList is non-modifiable')

    def __iter__(self):
        # By default, iterate over the values instead of the keys
        # XXX: This violates the standard pythonic dict-like behavior
        return self.entries.itervalues()

    def iterkeys(self):
        # UserDict.DictMixin implements iterkeys() using __iter__
        # Our __iter__ implementation iterates over values, though,
        # so we need to redefine iterkeys()
        return self.entries.iterkeys()

    def __len__(self):
        return len(self.entries)

    def __nonzero__(self):
        return bool(self.entries)


def get_diff_list(repo, parent, child, paths=None):
    # Compute the args to specify the commits to 'git diff'
    reverse = False
    if parent == constants.COMMIT_WD:
        if child == constants.COMMIT_WD:
            # No diffs
            commit_args = None
        elif child == constants.COMMIT_INDEX:
            commit_args = []
            reverse = True
        else:
            commit_args = [str(child)]
            reverse = True
    elif parent == constants.COMMIT_INDEX:
        if child == constants.COMMIT_WD:
            commit_args = []
        elif child == constants.COMMIT_INDEX:
            # No diffs
            commit_args = None
        else:
            commit_args = ['--cached', str(child)]
            reverse = True
    elif child == constants.COMMIT_WD:
        commit_args = [str(parent)]
    elif child == constants.COMMIT_INDEX:
        commit_args = ['--cached', str(parent)]
    else:
        commit_args = [str(parent), str(child)]

    # The arguments to select by path
    if paths == None:
        path_args = []
    elif not paths:
        # If paths is the empty list, there is nothing to diff
        path_args = None
    else:
        path_args = paths

    if commit_args == None or path_args == None:
        # No diffs
        out = ''
    else:
        cmd = ['diff', '--raw', '--abbrev=40', '-z', '-C'] + \
                commit_args + ['--'] + path_args
        try:
            out = repo.runSimpleGitCmd(cmd)
        except proc.CmdFailedError, ex:
            match = re.search("bad revision '(.*)'\n", ex.stderr)
            if match:
                bad_rev = match.group(1)
                raise NoSuchCommitError(bad_rev)
            raise

    fields = out.split('\0')
    # When the diff is non-empty, it will have a terminating '\0'
    # Remove the empty field after the last '\0'
    if fields and not fields[-1]:
        del fields[-1]
    num_fields = len(fields)

    entries = DiffFileList(parent, child)

    n = 0
    while n < num_fields:
        field = fields[n]
        # The field should start with ':'
        if not field or field[0] != ':':
            msg = 'unexpected output from git diff: ' \
                    'missing : at start of field %d (%r)' % \
                    (n, field)
            raise GitError(msg)

        # Split the field into its components
        parts = field.split(' ')
        try:
            (old_mode_str, new_mode_str,
             old_sha1, new_sha1, status_str) = parts
            # Strip the leading ':' from old_mode_str
            old_mode_str = old_mode_str[1:]
        except ValueError:
            msg = 'unexpected output from git diff: ' \
                    'unexpected number of components in field %d (%r)' % \
                    (n, field)
            raise GitError(msg)

        # Parse the mode fields
        try:
            old_mode = int(old_mode_str, 8)
        except ValueError:
            msg = 'unexpected output from git diff: ' \
                    'invalid old mode %r in field %d' % (old_mode_str, n)
            raise GitError(msg)
        try:
            new_mode = int(new_mode_str, 8)
        except ValueError:
            msg = 'unexpected output from git diff: ' \
                    'invalid new mode %r in field %d' % (new_mode_str, n)
            raise GitError(msg)

        # Parse the status
        try:
            status = Status(status_str)
        except ValueError:
            msg = 'unexpected output from git diff: ' \
                    'invalid status %r in field %d' % (status_str, n)
            raise GitError(msg)

        # Advance n to read the first file name
        n += 1
        if n >= num_fields:
            msg = 'unexpected output from git diff: ' \
                    'missing file name for field %d' % (n - 1,)
            raise GitError(msg)

        # Read the file name(s)
        if status == Status.RENAMED or status == Status.COPIED:
            old_name = fields[n]
            # Advance n to read the second file name
            n += 1
            if n >= num_fields:
                msg = 'unexpected output from git diff: ' \
                        'missing second file name for field %d' % (n,)
                raise GitError(msg)
            new_name = fields[n]
        else:
            name = fields[n]
            if status == Status.DELETED:
                old_name = name
                new_name = None
            elif status == Status.ADDED:
                old_name = None
                new_name = name
            else:
                old_name = name
                new_name = name

        # Create the DiffEntry
        entry = DiffEntry(old_mode, new_mode, old_sha1, new_sha1,
                          status, old_name, new_name)
        if reverse:
            entry.reverse()
        entries.add(entry)

        # Advance n, to prepare for the next iteration around the loop
        n += 1

    return entries

########NEW FILE########
__FILENAME__ = exceptions
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
class GitError(Exception):
    pass


class NotARepoError(GitError):
    def __init__(self, repo):
        msg = 'not a git repository: %s' % (repo,)
        GitError.__init__(self, msg)
        self.repo = repo


class NoWorkingDirError(GitError):
    def __init__(self, repo, msg=None):
        if msg is None:
            msg = '%s does not have a working directory' % (repo,)
        GitError.__init__(self, msg)
        self.repo = repo


class NoSuchConfigError(GitError):
    def __init__(self, name):
        msg = 'no config value set for "%s"' % (name,)
        GitError.__init__(self, msg)
        self.name = name


class BadConfigError(GitError):
    def __init__(self, name, value=None):
        if value is None:
            msg = 'bad config value for "%s"' % (name,)
        else:
            msg = 'bad config value for "%s": "%s"' % (name, value)
        GitError.__init__(self, msg)
        self.name = name
        self.value = value


class MultipleConfigError(GitError):
    def __init__(self, name):
        msg = 'multiple config values set for "%s"' % (name,)
        GitError.__init__(self, msg)
        self.name = name


class BadCommitError(GitError):
    def __init__(self, commit_name, msg):
        GitError.__init__(self, 'bad commit %r: %s' % (commit_name, msg))
        self.commit = commit_name
        self.msg = msg


class NoSuchObjectError(GitError):
    def __init__(self, name, type='object'):
        GitError.__init__(self)
        self.type = type
        self.name = name

    def __str__(self):
        return 'no such %s %r' % (self.type, self.name)


class NoSuchCommitError(NoSuchObjectError):
    def __init__(self, name):
        NoSuchObjectError.__init__(self, name, 'commit')


class NoSuchBlobError(NoSuchObjectError):
    def __init__(self, name):
        NoSuchObjectError.__init__(self, name, 'blob')


class NotABlobError(GitError):
    def __init__(self, name):
        GitError.__init__(self, '%r does not refer to a blob' % (name))
        self.name = name

class BadRevisionNameError(GitError):
    def __init__(self, name, msg):
        GitError.__init__(self, 'bad revision name %r: %s' % (name, msg))
        self.name = name
        self.msg = msg


class AmbiguousArgumentError(GitError):
    def __init__(self, arg_name, reason):
        GitError.__init__(self, 'ambiguous argument %r: %s' %
                          (arg_name, reason))
        self.argName = arg_name
        self.reason = reason


class PatchFailedError(GitError):
    def __init__(self, msg):
        full_msg = 'failed to apply patch'
        if msg:
            full_msg = ':\n  '.join([full_msg] + msg.splitlines())
        GitError.__init__(self, full_msg)
        self.msg = msg

########NEW FILE########
__FILENAME__ = obj
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

class Object(object):
    def __init__(self, repo, sha1, type):
        self.repo = repo
        self.sha1 = sha1
        self.type = type


# A tree entry isn't really an object as far as git is concerned,
# but there doesn't seem to be a better location to define this class.
class TreeEntry(object):
    def __init__(self, name, mode, type, sha1):
        self.name = name
        self.mode = mode
        self.type = type
        self.sha1 = sha1

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'TreeEntry(%r, %r, %r, %r)' % (self.name, self.mode, self.type,
                                              self.sha1)


# An index entry isn't really an object as far as git is concerned,
# but there doesn't seem to be a better location to define this class.
class IndexEntry(object):
    def __init__(self, path, mode, sha1, stage):
        self.path = path
        self.mode = mode
        self.sha1 = sha1
        self.stage = stage

    def __str__(self):
        return self.path

    def __repr__(self):
        return 'IndexEntry(%r, %r, %r, %r)' % (self.path, self.mode, self.sha1,
                                              self.stage)

########NEW FILE########
__FILENAME__ = repo
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import operator
import os
import stat
import subprocess
import tempfile

import gitreview.proc as proc

from exceptions import *
import constants
import commit as git_commit
import diff as git_diff
import obj as git_obj


class Repository(object):
    def __init__(self, git_dir, working_dir, config):
        self.gitDir = git_dir
        self.workingDir = working_dir
        self.config = config

        self.__gitCmdEnv = os.environ.copy()
        self.__gitCmdEnv['GIT_DIR'] = self.gitDir
        if self.workingDir:
            self.__gitCmdCwd = self.workingDir
            self.__gitCmdEnv['GIT_WORK_TREE'] = self.workingDir
        else:
            self.__gitCmdCwd = self.gitDir
            if self.__gitCmdEnv.has_key('GIT_WORK_TREE'):
                del(self.__gitCmdEnv['GIT_WORK_TREE'])

    def __str__(self):
        if self.workingDir:
            return self.workingDir
        return self.gitDir

    def getGitDir(self):
        """
        repo.getGitDir() --> path

        Returns the path to the repository's git directory.
        """
        return self.gitDir

    def getWorkingDir(self):
        """
        repo.getWorkingDir() --> path or Nonea

        Returns the path to the repository's working directory, or None if
        the working directory path is not known.
        """
        return self.workingDir

    def hasWorkingDirectory(self):
        """
        repo.hasWorkingDirectory() --> bool

        Return true if we know the working directory for this repository.
        (Note that this may return false even for non-bare repositories in some
        cases.  Notably, this returns False if the git command was invoked from
        within the .git directory itself.)
        """
        return bool(self.workingDir)

    def isBare(self):
        """
        repo.isBare() --> bool

        Returns true if this is a bare repository.

        This returns the value of the core.bare configuration setting, if it is
        present.  If it is not present, the result of
        self.hasWorkingDirectory() is returned.

        hasWorkingDirectory() may be a more useful function in practice.  Most
        operations care about whether or not we actually have a working
        directory, rather than if the repository is marked bare or not.
        """
        return self.config.getBool('core.bare', self.hasWorkingDirectory())

    def __getCmdEnv(self, extra_env=None):
        if not extra_env:
            return self.__gitCmdEnv

        env = self.__gitCmdEnv.copy()
        for (name, value) in extra_env.items():
            env[name] = value
        return env

    def popenGitCmd(self, args, extra_env=None, stdin='/dev/null',
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
        cmd = [constants.GIT_EXE] + args
        env = self.__getCmdEnv(extra_env)
        return proc.popen_cmd(cmd, cwd=self.__gitCmdCwd, env=env,
                              stdin=stdin, stdout=stdout, stderr=stderr)

    def runGitCmd(self, args, expected_rc=0, expected_sig=None,
                  stdout=subprocess.PIPE, extra_env=None):
        cmd = [constants.GIT_EXE] + args
        env = self.__getCmdEnv(extra_env)
        return proc.run_cmd(cmd, cwd=self.__gitCmdCwd, env=env,
                            expected_rc=expected_rc, expected_sig=expected_sig,
                            stdout=stdout)

    def runSimpleGitCmd(self, args, stdout=subprocess.PIPE, extra_env=None):
        cmd = [constants.GIT_EXE] + args
        env = self.__getCmdEnv(extra_env)
        return proc.run_simple_cmd(cmd, cwd=self.__gitCmdCwd, env=env,
                                   stdout=stdout)

    def runOnelineCmd(self, args, extra_env=None):
        cmd = [constants.GIT_EXE] + args
        env = self.__getCmdEnv(extra_env)
        return proc.run_oneline_cmd(cmd, cwd=self.__gitCmdCwd, env=env)

    def runCmdWithInput(self, args, input, stdout=subprocess.PIPE,
                        extra_env=None):
        """
        Run a git command and write data to its stdin.

        The contents of the string input will be written to the command on
        stdin.

        Note: currently this code attempts to write the entire input buffer
        before reading any data from the commands stdout or stderr pipes.  This
        can cause deadlock if the command outputs a non-trivial amount data
        before it finishes reading stdin.  This function currently shouldn't be
        used unless you know the command behavior will not cause deadlock.
        """
        p = self.popenGitCmd(args, extra_env=extra_env,
                             stdin=subprocess.PIPE, stdout=stdout,
                             stderr=subprocess.PIPE)

        # Write the data to the commands' stdin.
        # TODO: We really should select() on stdin, stdout, and stderr all at
        # the same time, so we don't deadlock if the command attempts to write
        # a large amount of data to stdout or stderr before reading stdin.
        # This currently isn't a big problem, since most git commands don't
        # behave that way.
        p.stdin.write(input)

        # Read all data from stdout and stderr
        (cmd_out, cmd_err) = p.communicate()

        # Check the command's exit code
        status = p.wait()
        proc.check_status(args, status, cmd_err=cmd_err)

        return cmd_out

    def getDiff(self, parent, child, paths=None):
        return git_diff.get_diff_list(self, parent, child, paths=paths)

    def getCommit(self, name):
        return git_commit.get_commit(self, name)

    def getCommitSha1(self, name, extra_args=None):
        """
        repo.getCommitSha1(name) --> sha1

        Get the SHA1 ID of the commit associated with the specified ref name.
        If the ref name refers to a tag object, this returns the SHA1 of the
        underlying commit object referred to in the tag.  (Use getSha1() if
        you want to get the SHA1 of the tag object itself.)
        """
        # Note: 'git rev-list' returns the SHA1 value of the commit,
        # even if "name" refers to a tag object.
        cmd = ['rev-list', '-1']
        if extra_args is not None:
          cmd.extend(extra_args)
        cmd.append(name)
        try:
            sha1 = self.runOnelineCmd(cmd)
        except proc.CmdFailedError, ex:
            if ex.stderr.find('unknown revision') >= 0:
                raise NoSuchCommitError(name)
            raise
        return sha1

    def getSha1(self, name):
        """
        repo.getSha1(name) --> sha1

        Get the SHA1 ID of the specified object.  name may be a ref name, tree
        name, blob name etc.
        """
        cmd = ['rev-parse', '--verify', name]
        try:
            sha1 = self.runOnelineCmd(cmd)
        except proc.CmdFailedError, ex:
            if ex.stderr.find('Needed a single revision') >= 0:
                raise NoSuchObjectError(name)
            raise
        return sha1

    def getObjectType(self, name):
        cmd = ['cat-file', '-t', name]
        try:
            return self.runOnelineCmd(cmd)
        except proc.CmdExitCodeError, ex:
            if ex.stderr.find('Not a valid object name') >= 0:
                raise NoSuchObjectError(name)
            raise

    def isRevision(self, name):
        # Handle our special commit names
        if name == constants.COMMIT_INDEX or name == constants.COMMIT_WD:
            return True

        # We also need to handle the other index stage names, since
        # getObjectType() will fail on them too, even though we want to treat
        # them as revisions.
        if name == ':1' or name == ':2' or name == ':3':
            return True

        try:
            type = self.getObjectType(name)
        except NoSuchObjectError:
            return False

        # tag objects can be treated as commits
        if type == 'commit' or type == 'tag':
            return True
        return False

    def isRevisionOrPath(self, name):
        """
        Determine if name refers to a revision or a path.

        This behaves similarly to "git log <name>".

        Returns True if name is a revision name, False if it is a path name,
        or raises AmbiguousArgumentError if the name is ambiguous.
        """
        is_rev = self.isRevision(name)
        if self.hasWorkingDirectory():
            # git only checks the working directory for path names in this
            # situation.  We'll do the same.
            is_path = os.path.exists(os.path.join(self.workingDir, name))
        else:
            is_path = False

        if is_rev and is_path:
            reason = 'both revision and filename'
            raise AmbiguousArgumentError(name, reason)
        elif is_rev:
            return True
        elif is_path:
            return False
        else:
            reason = 'unknown revision or path not in the working tree'
            raise AmbiguousArgumentError(name, reason)

    def getBlobContents(self, name, outfile=None):
        """
        Get the contents of a blob object.

        If outfile is None (the default), the contents of the blob are
        returned.  Otherwise, the contents of the blob will be written to the
        file specified by outfile.  outfile may be a file object, file
        descriptor, or file name.

        A NoSuchBlobError error will be raised if name does not refer to a
        valid object.  A NotABlobError will be raised if name refers to an
        object that is not a blob.
        """
        if outfile is None:
            stdout = subprocess.PIPE
        else:
            stdout = outfile

        cmd = ['cat-file', 'blob', name]
        try:
            out = self.runSimpleGitCmd(cmd, stdout=stdout)
        except proc.CmdFailedError, ex:
            if ex.stderr.find('Not a valid object name') >= 0:
                raise NoSuchBlobError(name)
            elif ex.stderr.find('bad file') >= 0:
                raise NotABlobError(name)
            raise

        # Note: the output might not include a trailing newline if the blob
        # itself doesn't have one
        return out

    def __revList(self, options):
        """
        repo.__revList(options) --> commit names

        Run 'git rev-list' with the specified options.

        Warning: not all options are safe.  Don't use options that alter the
        output format, such as --pretty, --header, --graph, etc.

        Generally, the safe options are those that only affect the list of
        commits returned.  These include commit names, path names (it is
        recommended to precede these with the '--' option), sorting options,
        grep options, etc.
        """
        args = ['rev-list'] + options
        cmd_out = self.runSimpleGitCmd(args)
        lines = cmd_out.split('\n')
        while lines and not lines[-1]:
            del lines[-1]
        return lines

    def getCommitRangeNames(self, parent, child):
        """
        repo.getCommitRangeNames(parent, child) --> commit names

        Get the names of all commits that are included in child, but that are
        not included in parent.  (The resulting list will never include the
        commit referred to by parent.  It will include the commit referred to
        by child, as long is child is not equal to or an ancestor of parent.)
        """
        # If the parent is COMMIT_WD or COMMIT_INDEX, we don't need
        # to run rev-list at all.
        if parent == constants.COMMIT_WD:
            return []
        elif parent == constants.COMMIT_INDEX:
            if child == constants.COMMIT_WD:
                return [constants.COMMIT_WD]
            else:
                return []

        # If the child is COMMIT_WD or COMMIT_INDEX, we need to
        # manually add these to the return list, and run rev-list from HEAD
        if child == constants.COMMIT_WD:
            extra_commits = [constants.COMMIT_WD, constants.COMMIT_INDEX]
            rev_list_start = constants.COMMIT_HEAD
        elif child == constants.COMMIT_INDEX:
            extra_commits = [constants.COMMIT_INDEX]
            rev_list_start = constants.COMMIT_HEAD
        else:
            extra_commits = []
            rev_list_start = str(child)

        rev_list_args = ['^' + str(parent), rev_list_start]
        commits = self.revList(rev_list_args)
        return extra_commits + commits

    def getRefs(self, glob=None):
        """
        repo.getRefNames(glob=None) --> dict of "ref name --> SHA1" keys

        List the refs in the repository.

        If glob is specified, only refs whose name matches that glob pattern
        are returned.  glob may also be a list of patterns, in which case all
        refs matching at least one of the patterns will be returned.
        """
        cmd = ['ls-remote', '.']
        if glob is not None:
            if isinstance(glob, list):
                cmd += glob
            else:
                cmd.append(glob)

        refs = {}
        cmd_out = self.runSimpleGitCmd(cmd)
        for line in cmd_out.split('\n'):
            if not line:
                continue
            try:
                (sha1, ref_name) = line.split(None, 1)
            except ValueError:
                msg = 'unexpected output from git ls-remote: %r' % (line,)
                args = [constants.GIT_EXE] + cmd
                raise proc.CmdFailedError(args, msg)
            refs[ref_name] = sha1

        return refs

    def getRefNames(self, glob=None):
        """
        repo.getRefNames(glob=None) --> ref names

        List the ref names in the repository.

        If glob is specified, only ref names matching that glob pattern
        are returned.  glob may also be a list of patterns, in which case all
        refs matching at least one of the patterns will be returned.
        """
        ref_dict = self.getRefs(glob)
        return sorted(ref_dict.iterkeys())

    def applyPatch(self, patch, tree='HEAD', strip=1, prefix=None,
                   context=None):
        """
        Apply a patch onto a tree, creating a new tree object.

        This operation does not modify the index or working directory.

        Arguments:
          patch - A string containing the patch to be applied.
          tree - A tree-ish indicating the tree to which the patch should be
                 applied.  Defaults to "HEAD" if not specified.

        Returns the SHA1 of the new tree object.
        """
        # Allow the tree argument to be either a string or a Commit object
        if isinstance(tree, git_commit.Commit):
            tree = tree.sha1

        # Read the parent tree into a new temporary index file
        tmp_index = tempfile.NamedTemporaryFile(dir=self.gitDir,
                                                prefix='apply-patch.index.')
        args = ['read-tree', tree, '--index-output=%s' % (tmp_index.name,)]
        self.runSimpleGitCmd(args)

        # Construct the git-apply command.
        # We patch the temporary index file rather than the real one.
        extra_env = { 'GIT_INDEX_FILE' : tmp_index.name }
        args = ['apply', '--cached', '-p%d' % (strip,)]
        if prefix is not None:
            args.append('--directory=%s' % (prefix,))
        if context is not None:
            args.append('-C%d' % (context,))

        # Run the apply patch command
        try:
            self.runCmdWithInput(args, input=patch, extra_env=extra_env)
        except proc.CmdExitCodeError, ex:
            # If the patch failed to apply, re-raise the error as a
            # PatchFailedError.
            if (ex.stderr.find('patch does not apply') >= 0 or
                ex.stderr.find('does not exist in index')):
                raise PatchFailedError(ex.stderr)
            # Re-raise all other errors as-is.
            raise

        # Now write a tree object from the temporary index file
        tree_sha1 = self.runOnelineCmd(['write-tree'], extra_env=extra_env)

        # Close the temporary file (this also deletes it).
        # This would also happen automatically when tmp_index is garbage
        # collected, but we do it here anyway.
        tmp_index.close()

        return tree_sha1

    def commitTree(self, tree, parents, msg, author_name=None,
                   author_email=None, author_date=None,
                   committer_name=None, committer_email=None,
                   committer_date=None):
        """
        Create a commit from a tree object, with the specified parents and
        commit message.

        Returns the SHA1 of the new commit.
        """
        # If specified by the caller, set the author and
        # committer information via the environment
        extra_env = {}
        if author_name is not None:
            extra_env['GIT_AUTHOR_NAME'] = author_name
        if author_email is not None:
            extra_env['GIT_AUTHOR_EMAIL'] = author_email
        if author_date is not None:
            extra_env['GIT_AUTHOR_DATE'] = author_date
        if committer_name is not None:
            extra_env['GIT_COMMITTER_NAME'] = committer_name
        if committer_email is not None:
            extra_env['GIT_COMMITTER_EMAIL'] = committer_email
        if committer_date is not None:
            extra_env['GIT_COMMITTER_DATE'] = committer_date

        # Allow the caller to pass in a single parent as a string
        # instead of a list
        if isinstance(parents, str):
            parents = [parents]

        # Run git commit-tree
        args = ['commit-tree', tree]
        for parent in parents:
            args += ['-p', parent]

        commit_out = self.runCmdWithInput(args, input=msg, extra_env=extra_env)
        commit_sha1 = commit_out.strip()
        return commit_sha1

    def listTree(self, commit, dirname=None):
        if commit == constants.COMMIT_WD:
            return self.__listWorkingDir(dirname)
        elif commit == constants.COMMIT_INDEX:
            return self.__listIndexTree(dirname)

        entries = []
        cmd = ['ls-tree', '-z', commit, '--']
        if dirname is not None:
            cmd.append(dirname)
        cmd_out = self.runSimpleGitCmd(cmd)
        for line in cmd_out.split('\0'):
            if not line:
                continue

            try:
                (info, name) = line.split('\t', 1)
            except ValueError:
                msg = 'unexpected output from git ls-tree: %r' % (line,)
                args = [constants.GIT_EXE] + cmd
                raise proc.CmdFailedError(args, msg)
            try:
                (mode_str, type, sha1) = info.split(' ')
                mode = int(mode_str, 0)
            except ValueError:
                msg = 'unexpected output from git ls-tree: %r' % (line,)
                args = [constants.GIT_EXE] + cmd
                raise proc.CmdFailedError(args, msg)
            # Return only the basename,
            # not the full path from the root of the repository
            name = os.path.basename(name)
            entry = git_obj.TreeEntry(name, mode, type, sha1)
            entries.append(entry)

        return entries

    def listIndex(self, dirname=None):
        """
        List the files in the index, optionally restricting output
        to a specific directory.
        """
        if not self.hasWorkingDirectory():
            raise NoWorkingDirError(self)

        # Run "git ls-files -s" to get the contents of the index
        cmd = ['ls-files', '-s', '-z', '--']
        if dirname:
            dirname = os.path.normpath(dirname)
            prefix = dirname + os.sep
            cmd.append(dirname)
        else:
            prefix = ''
        cmd_out = self.runSimpleGitCmd(cmd)

        tree_entries = {}
        entries = []
        for line in cmd_out.split('\0'):
            if not line:
                continue

            try:
                (info, name) = line.split('\t', 1)
            except ValueError:
                msg = 'unexpected output from git ls-files: %r' % (line,)
                args = [constants.GIT_EXE] + cmd
                raise proc.CmdFailedError(args, msg)
            try:
                (mode_str, sha1, stage_str) = info.split(' ')
                mode = int(mode_str, 8)
                stage = int(stage_str, 0)
            except ValueError:
                msg = 'unexpected output from git ls-files: %r' % (line,)
                args = [constants.GIT_EXE] + cmd
                raise proc.CmdFailedError(args, msg)

            # Strip off dirname from the start of name
            if not name.startswith(prefix):
                msg = 'unexpected output from git ls-files: %r does ' \
                        'not start with %r' % (name, prefix)
                args = [constants.GIT_EXE] + cmd
                raise proc.CmdFailedError(args, msg)
            name = name[len(prefix):]

            entries.append(git_obj.IndexEntry(name, mode, sha1, stage))

        return entries

    def __listIndexTree(self, dirname):
        index_entries = self.listIndex(dirname)
        return self.__convertIndexToTree(index_entries)

    def __listWorkingDir(self, dirname):
        if not self.hasWorkingDirectory():
            raise NoWorkingDirError(self)

        if not dirname:
            paths = None
            strip_prefix = ''
        else:
            paths = [dirname]
            strip_prefix = os.path.normpath(dirname) + os.sep

        # We could attempt to just read the working directory,
        # but then we wouldn't have sha1 values for unmodified files,
        # and processing .gitignore information would be complicated
        #
        # Instead, read the index, then run 'git diff' to determine the
        # changes between the index and the working directory.
        index_entries = self.listIndex(dirname)
        diff = self.getDiff(constants.COMMIT_INDEX, constants.COMMIT_WD, paths)

        ie_by_path = {}
        for ie in index_entries:
            ie_by_path[ie.path] = ie

        for de in diff:
            if de.status == git_diff.Status.ADDED or \
                    de.status == git_diff.Status.RENAMED or \
                    de.status == git_diff.Status.COPIED:
                # The diff shouldn't have any renamed, copied, or new files.
                # New files in the working directory are ignored until they
                # are added to the index.  Files that have been renamed in the
                # working directory and not updated in the index just show up
                # as the old path having been deleted.
                msg = 'unexpected status %s for %r in working directory ' \
                        'diff' % (de.status, de.getPath(),)
                raise GitError(msg)

            path = de.old.path
            if not path.startswith(strip_prefix):
                msg = 'unexpected path %r in diff output: does not start ' \
                        'with %r' % (path, strip_prefix)
                raise GitError(msg)
            path = path[len(strip_prefix):]

            # Update the entry as appropriate
            if de.status == git_diff.Status.DELETED:
                try:
                    del ie_by_path[path]
                except KeyError:
                    msg = 'path %r in diff output, but not in index' % (path,)
                    raise GitError(msg)
            else:
                try:
                    ie = ie_by_path[path]
                except KeyError:
                    msg = 'path %r in diff output, but not in index' % (path,)
                    raise GitError(msg)
                # Since there are no renames or copies,
                # the new name should be the same as the old name
                assert de.new.path == de.old.path
                ie.mode = de.new.mode
                # Use all zeros for the SHA1 hash.
                # If we really wanted, we could use 'git hash-object'
                # to compute what the has would be, and optionally create
                # an actual blob object.
                ie.sha1 = '0000000000000000000000000000000000000000'

        # Now convert all of the IndexEntry objects into TreeEntries
        return self.__convertIndexToTree(ie_by_path.values())

    def __convertIndexToTree(self, index_entries):
        blob_entries = []
        tree_entries = {}
        for ie in index_entries:
            sep_idx = ie.path.find(os.sep)
            if sep_idx >= 0:
                # This is file in a subdirectory
                # Add an tree entry for the subdirectory, if we don't already
                # have one.
                name = ie.path[:sep_idx]
                mode = 040000
                type = 'tree'
                # There are no tree objects for the index.
                # If the caller really wants tree objects, we could
                # use 'git write-tree' to create the tree, or
                # 'git hash-object' to determine what the SHA1 would
                # be for this tree, without actually creating it.
                sha1 = '0000000000000000000000000000000000000000'
                entry = git_obj.TreeEntry(name, mode, type, sha1)
                tree_entries[name] = entry
                continue

            # Normally, stage is 0
            # Unmerged files don't have stage 0, but have stage
            # 1 for the ancestor, 2 for the first parent,
            # 3 for the second parent.  (There is no stage 4 or higher,
            # even for octopus merges.)
            #
            # For unmerged files, use the first parent's version (stage 2).
            # Ignore other versions.
            if not (ie.stage == 0 or ie.stage == 2):
                continue

            entry = git_obj.TreeEntry(ie.path, ie.mode, 'blob', ie.sha1)
            blob_entries.append(entry)

        # Combine the results, and sort them for consistent ordering
        entries = blob_entries
        entries.extend(tree_entries.values())
        entries.sort(key = operator.attrgetter('name'))
        return entries

########NEW FILE########
__FILENAME__ = svn
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import re

from exceptions import *
import commit as git_commit

__all__ = ['GitSvnError', 'get_svn_info', 'get_svn_url']


class GitSvnError(GitError):
    pass


def _parse_svn_info(commit_msg):
    # This pattern is the same one used by the perl git-svn code
    m = re.search(r'^\s*git-svn-id:\s+(.*)@(\d+)\s([a-f\d\-]+)$',
                  commit_msg, re.MULTILINE)
    if not m:
        raise GitSvnError('failed to parse git-svn-id from commit message')

    url = m.group(1)
    revision = m.group(2)
    uuid = m.group(3)
    return (url, revision, uuid)


def get_svn_info(commit):
    """
    Parse the SVN URL, revision number, and UUID out of a git commit's message.
    """
    return _parse_svn_info(commit.message)


def get_svn_url(repo, commit=None):
    """
    Get the SVN URL for a repository.

    This looks backwards through the commit history to find a commit with SVN
    information in the commit message.  It starts searching at the specified
    commit, or HEAD if not specified.
    """
    if commit is None:
        commit = 'HEAD'
    elif isinstance(commit, git_commit.Commit):
        # Since we already have this commit's message,
        # try to parse it first.  If it contains a git-svn-id,
        # we will have avoided making an external call to git.
        try:
            (url, rev, uuid) = _parse_svn_info(commit.message)
            return url
        except GitSvnError:
            # It probably doesn't have a git-svn-id in the message.
            # Oh well.  Fall through to our normal processing below.
            pass
        commit = commit.sha1

    # Look through the commit history for a commit with a git-svn-id
    # in the commit message
    args = ['log', '-1', '--no-color', '--first-parent', '--pretty=medium',
            '--grep=^git-svn-id: ', commit]
    out = repo.runSimpleGitCmd(args)

    (url, rev, uuid) = _parse_svn_info(out)
    return url

########NEW FILE########
__FILENAME__ = proc
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
"""
Utility wrapper functions around Python's subprocess module.
"""

import subprocess
import types

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT

"""
DEVNULL can be used for stdin, to indicate that stdin should be
redirected from /dev/null.

We use subprocess.STDOUT here to guarantee that we will avoid collisions
with subprocess.PIPE and any other constants defined by subprocess in the
future.
"""
DEVNULL = subprocess.STDOUT


"""
ANY can be passed as the expected_rc or expected_sig argument,
to indicate that any exit code or signal should be allowed.
"""
ANY = -1


class ProcError(Exception):
    pass


class CmdFailedError(ProcError):
    def __init__(self, args, msg, cmd_err=None):
        msg = 'command %s %s' % (args, msg)
        if cmd_err:
            indented_err = '  ' + '\n  '.join(cmd_err.splitlines())
            msg = msg + '\nstderr:\n' + indented_err
        ProcError.__init__(self, msg)
        # Note: don't call this self.args
        # The builtin Exception class uses self.args for its own data
        self.cmd = args
        self.stderr = cmd_err


class CmdExitCodeError(CmdFailedError):
    def __init__(self, args, exit_code, expected_rc=None, cmd_err=None):
        # XXX: might be nicer to join args together.
        # We should ideally perform some quoting, then, however
        msg = 'exited with exit code %s' % (exit_code,)
        CmdFailedError.__init__(self, args, msg, cmd_err)
        self.exitCode = exit_code
        self.expectedExitCode = expected_rc


class CmdTerminatedError(CmdFailedError):
    def __init__(self, args, signum, expected_sig=None, cmd_err=None):
        # XXX: might be nicer to join args together.
        # We should ideally perform some quoting, then, however
        msg = 'was terminated by signal %s' % (signum,)
        CmdFailedError.__init__(self, args, msg, cmd_err)
        self.signal = signum
        self.expectedSignal = expected_sig



def _check_result(args, result, expected, cmd_err, ex_class):
    if expected == ANY:
        return

    if expected == None:
        raise ex_class(args, result, expected, cmd_err)

    if isinstance(expected, (list, tuple)):
        if not result in expected:
            raise ex_class(args, result, expected, cmd_err)
    else:
        if result != expected:
            raise ex_class(args, result, expected, cmd_err)


def check_exit_code(args, exit_code, expected_rc, cmd_err):
    return _check_result(args, exit_code, expected_rc, cmd_err,
                         CmdExitCodeError)


def check_signal(args, signum, expected_sig, cmd_err):
    return _check_result(args, signum, expected_sig, cmd_err,
                         CmdTerminatedError)


def check_status(args, status, expected_rc=0, expected_sig=None, cmd_err=None):
    if status >= 0:
        check_exit_code(args, status, expected_rc, cmd_err)
    else:
        check_signal(args, -status, expected_sig, cmd_err)


def popen_cmd(args, cwd=None, env=None, stdin='/dev/null',
              stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    Wrapper around subprocess.Popen() that also accepts filenames
    for stdin/stdout/stderr.
    """
    if isinstance(stdin, types.StringTypes):
        stdin = file(stdin, 'r')
    if isinstance(stdout, types.StringTypes):
        stdout = file(stdout, 'w')
    if isinstance(stderr, types.StringTypes):
        stderr = file(stderr, 'w')

    # close_fds=True is always a good thing
    p = subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=stderr,
                         cwd=cwd, env=env, close_fds=True)
    return p


def run_cmd(args, cwd=None, env=None, expected_rc=0, expected_sig=None,
            stdin='/dev/null', stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    run_cmd(args, cwd=None, env=None, expected_rc=0, expected_sig=None) -->
                (exit_code, stdoutdata, stderrdata)

    If the process was terminated via a signal, exit_code will be a negative
    number, whose absolute value is the signal number.

    expected_rc may be ANY, None, an integer value, or a list of integer
    values.  If the command exits with an return code not in expected_rc, a
    CmdFailedError will be raised.

    expected_sig may be ANY, None, an integer value, or a list of integer
    values.  If the command is terminated with a signal not in expected_sig, a
    CmdTerminatedError will be raised.
    """
    p = popen_cmd(args, cwd=cwd, env=env, stdin=stdin, stdout=stdout,
                  stderr=stderr)
    (cmd_out, cmd_err) = p.communicate()

    status = p.wait()
    check_status(args, status, expected_rc, expected_sig, cmd_err)
    return (status, cmd_out, cmd_err)


def run_simple_cmd(args, cwd=None, env=None, stdout=subprocess.PIPE):
    """
    run_simple_cmd(args, cwd=None, env=None) --> stdoutdata

    Wrapper around run_cmd() that expects the command to exit with a return
    value of 0, and output no data on stderr.  If any of these conditions fail,
    a CmdFailedError is raised.
    """
    (exit_code, cmd_out, cmd_err) = \
            run_cmd(args, cwd=cwd, env=env, expected_rc=0, expected_sig=None,
                    stdout=stdout)

    # exit_code is guaranteed to be 0, since we set expected_rc to 0
    # We only have to check if anything was output on stderr
    if cmd_err:
        msg = 'printed error message on stderr'
        raise CmdFailedError(args, msg, cmd_err)

    return cmd_out


def run_oneline_cmd(args, cwd=None, env=None):
    """
    run_oneline_cmd(args, cwd=None, env=None) --> line

    Wrapper around run_simple_cmd() that also expects the command to print
    exactly one line (terminated with a newline) to stdout.  If the command
    does not print a single line, a CmdFailedError is raised.

    Returns the command output, with the terminating newline removed.
    """
    cmd_out = run_simple_cmd(args, cwd=cwd, env=env)

    if not cmd_out:
        msg = 'did not print any output'
        raise CmdFailedError(args, msg)

    lines = cmd_out.split('\n')
    num_lines = len(lines)
    if num_lines < 2:
        # XXX: It would be nice to include cmd_out in the exception
        msg = 'did not print a terminating newline'
        raise CmdFailedError(args, msg)
    elif num_lines > 2 or lines[1]:
        # XXX: It would be nice to include cmd_out in the exception
        msg = 'printed more than one line of output'
        raise CmdFailedError(args, msg)

    return lines[0]

########NEW FILE########
__FILENAME__ = cli_reviewer
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import os
import subprocess

import gitreview.cli as cli
import gitreview.git as git

from exceptions import *


class FileIndexArgument(cli.Argument):
    def parse(self, cli_obj, arg):
        try:
            value = int(arg)
        except ValueError:
            return self.__parsePath(cli_obj, arg)

        if value < 0:
            msg = 'file index may not be negative'
            raise cli.CommandArgumentsError(msg)
        if value >= cli_obj.review.getNumEntries():
            msg = 'file index must be less than %s' % \
                    (cli_obj.review.getNumEntries())
            raise cli.CommandArgumentsError(msg)

        return value

    def __parsePath(self, cli_obj, arg):
        basename_matches = []
        basename_partial_matches = []
        endswith_matches = []

        n = -1
        for entry in cli_obj.review.getEntries():
            n += 1
            path = entry.getPath()
            if arg == path:
                # If this exactly matches the full path of one of the entries,
                # use it.
                return n

            basename = os.path.basename(path)
            if arg == basename:
                basename_matches.append(n)

            if basename.startswith(arg):
                basename_partial_matches.append(n)

            if path.endswith(arg):
                endswith_matches.append(n)

        if basename_matches:
            matches = basename_matches
        elif basename_partial_matches:
            matches = basename_partial_matches
        elif endswith_matches:
            matches = endswith_matches
        else:
            msg = 'unknown file %r' % (arg)
            raise cli.CommandArgumentsError(msg)

        if len(matches) > 1:
            if len(basename_matches) > 1:
                paths = [cli_obj.review.getEntry(n).getPath()
                         for n in basename_matches]
                msg = 'ambiguous path name:\n  ' + '\n  '.join(paths)
                raise cli.CommandArgumentsError(msg)

        return matches[0]

    def complete(self, cli_obj, text):
        matches = []

        for entry in cli_obj.review.getEntries():
            path = entry.getPath()
            basename = os.path.basename(path)
            if path.startswith(text):
                matches.append(path)
            if basename.startswith(text):
                matches.append(basename)

        return matches


class AliasArgument(cli.Argument):
    """
    An argument representing a commit alias name.
    """
    def parse(self, cli_obj, arg):
        return arg

    def complete(self, cli_obj, text):
        # Compute the list of aliases that match
        matches = [alias for alias in cli_obj.review.commitAliases
                   if alias.startswith(text)]

        # If only 1 alias matches, append a space
        if len(matches) == 1:
            return [matches[0] + ' ']

        return matches

class CommitArgument(cli.Argument):
    """
    An argument representing a commit name.
    """
    def parse(self, cli_obj, arg):
        return arg

    def complete(self, cli_obj, text):
        return cli_obj.completeCommit(text)


class CommitFileArgument(cli.Argument):
    """
    An argument representing a path to a file, optionally within a specified
    commit.

    Examples:
        path/to/some/file
        trunk:path/to/some/file
        mybranch^^:path/to/some/file

    When parsed, returns a tuple of (commit, path).
    """
    def __init__(self, name, **kwargs):
        self.defaultCommit = None
        passthrough_args = {}
        for kwname, kwvalue in kwargs.items():
            if kwname == 'default_commit':
                self.defaultCommit = kwvalue
            else:
                passthrough_args[kwname] = kwvalue
        cli.Argument.__init__(self, name, **passthrough_args)

    def parse(self, cli_obj, arg):
        parts = self.__splitArg(cli_obj, arg)
        if len(parts) == 1:
            # This could either be a commit name (in which case it means the
            # path from the current entry in the specified commit), or a path
            # name (in whic case it refers to the specified path in the default
            # commit).
            #
            # If this appears to be a commit name, assume it is one.
            if cli_obj.review.isRevisionOrPath(parts[0]):
                # Treat the path as the name of the current entry
                # TODO: we need a better way of handling the exception if
                # there is no current entry..  Currently raising an exception
                # from parse() results in the full error traceback being
                # printed to the user.
                current_entry = cli_obj.review.getCurrentEntry()
                commit = parts[0]
                if (cli_obj.review.expandCommitName(commit) ==
                    cli_obj.review.expandCommitName('parent')):
                    # If the commit name is the parent, use the old path.
                    path = current_entry.old.path
                elif (cli_obj.review.expandCommitName(commit) ==
                    cli_obj.review.expandCommitName('child')):
                    # If the commit name is the child, use the new path.
                    path = current_entry.new.path
                else:
                    # Otherwise, default to the new path, unless it is None
                    if current_entry.new.path is not None:
                        path = current_entry.new.path
                    else:
                        path = current_entry.old.path
                return (commit, path)
            else:
                # This is not a commit.
                # Assume it is a path in the default commit.
                return (self.defaultCommit, parts[0])

        return parts

    def complete(self, cli_obj, text):
        # Split the string into a commit name and path name.
        parts = self.__splitArg(cli_obj, text)

        if len(parts) == 1:
            # We just have one component.
            # It may be the start of a commit name.
            #
            # Since a pathname may come after the commit, append ':' instead of
            # a space when we have only 1 match.  Only append ':' if the match
            # is exact.  This way hitting tab once will append to just the
            # commit name without the colon, in case the user wants to supply
            # just the commit name with no path.  Hitting tab again will then
            # add the colon.
            matches = cli_obj.completeCommit(parts[0], append=':',
                                             append_exact=True)

            # It also might be the start of a path name in the default commit.
            if self.defaultCommit:
                file_matches = cli_obj.completeFilename(self.defaultCommit,
                                                        parts[0])
                matches += file_matches

            return matches
        else:
            # We have two components.  The first is a commit name/alias.
            # The second is the start of a path within that commit.
            matches = cli_obj.completeFilename(parts[0], parts[1])
            return [parts[0] + ':' + m for m in matches]

    def __splitArg(self, cli_obj, text):
        if not text:
            # Empty string
            return ('',)
        else:
            # The commit name is separated from the path name with a colon
            parts = text.split(':', 1)
            if len(parts) == 1:
                # There was no colon at all
                return (parts[0],)
            elif not parts[0]:
                # There was nothing before the colon.  Since an empty commit
                # string is invalid, this must be one of the special commit
                # names that start with a leading colon.  (E.g.,
                # git.COMMIT_INDEX, git.COMMIT_WD, or the stage numbers)
                #
                # Split again on the next colon to recompute the parts.
                new_parts = parts[1].split(':', 1)
                if len(new_parts) == 1:
                    # No additional colon
                    return (':' + new_parts[0],)
                else:
                    return (':' + new_parts[0], new_parts[1])
            return parts


class ExitCommand(cli.ArgCommand):
    def __init__(self):
        help = 'Exit'
        args = [cli.IntArgument('exit_code', hr_name='exit code',
                            default=0, min=0, max=255, optional=True)]
        cli.ArgCommand.__init__(self, args, help)

    def runParsed(self, cli_obj, name, args):
        cli_obj.stop = True
        return args.exit_code


class ListCommand(cli.ArgCommand):
    def __init__(self):
        help = 'Show the file list'
        args = []
        cli.ArgCommand.__init__(self, args, help)

    def runParsed(self, cli_obj, name, args):
        entries = cli_obj.review.getEntries()

        # Compute the width needed for the index field
        num_entries = len(entries)
        max_index = num_entries - 1
        index_width = len(str(max_index))

        # List the entries
        n = 0
        for entry in entries:
            msg = '%*s: %s ' % (index_width, n, entry.status.getChar())
            if entry.status == git.diff.Status.RENAMED or \
                    entry.status == git.diff.Status.COPIED:
                msg += '%s\n%*s    --> %s' % (entry.old.path, index_width, '',
                                              entry.new.path)
            else:
                msg += entry.getPath()
            cli_obj.output(msg)
            n += 1


class NextCommand(cli.ArgCommand):
    def __init__(self):
        help = 'Move to the next file'
        args = []
        cli.ArgCommand.__init__(self, args, help)

    def runParsed(self, cli_obj, name, args):
        try:
            cli_obj.review.next()
        except IndexError:
            cli_obj.outputError('no more files')

        cli_obj.indexUpdated()


class PrevCommand(cli.ArgCommand):
    def __init__(self):
        help = 'Move to the previous file'
        args = []
        cli.ArgCommand.__init__(self, args, help)

    def runParsed(self, cli_obj, name, args):
        try:
            cli_obj.review.prev()
        except IndexError:
            cli_obj.outputError('no more files')

        cli_obj.indexUpdated()


class GotoCommand(cli.ArgCommand):
    def __init__(self):
        help = 'Go to the specified file'
        args = [FileIndexArgument('index', hr_name='index or path')]
        cli.ArgCommand.__init__(self, args, help)

    def runParsed(self, cli_obj, name, args):
        try:
            cli_obj.review.goto(args.index)
        except IndexError:
            cli_obj.outputError('invalid index %s' % (args.index,))

        cli_obj.indexUpdated()


class DiffCommand(cli.ArgCommand):
    def __init__(self):
        help = 'Diff the specified files'
        args = \
        [
            CommitFileArgument('path1', optional=True, default=None,
                               default_commit='parent'),
            CommitFileArgument('path2', optional=True, default=None,
                               default_commit='child'),
            CommitFileArgument('path3', optional=True, default=None,
                               default_commit='child'),
        ]
        cli.ArgCommand.__init__(self, args, help)

    def __getDiffFiles(self, cli_obj, args):
        if args.path3 is not None:
            # 3 arguments were specified.
            # Diff those files
            file1 = cli_obj.review.getFile(*args.path1)
            file2 = cli_obj.review.getFile(*args.path2)
            file3 = cli_obj.review.getFile(*args.path3)
            return (file1, file2, file3)

        if args.path2 is not None:
            # 2 arguments were specified.
            # Diff those files
            file1 = cli_obj.review.getFile(*args.path1)
            file2 = cli_obj.review.getFile(*args.path2)
            return (file1, file2)

        # If we're still here, 0 or 1 arguments were specified.
        # We're going to need the current entry to figure out what to do.
        current_entry = cli_obj.review.getCurrentEntry()

        if args.path1 is not None:
            # 1 argument was specified.
            # This normally means diff the specified file against the
            # 'child' version of the current file.
            if current_entry.status == git.diff.Status.DELETED:
                # Raise an error if this file doesn't exist in the child.
                name = 'child:%s' % (current_entry.old.path,)
                raise git.NoSuchBlobError(name)
            file1 = cli_obj.review.getFile(*args.path1)
            file2 = cli_obj.review.getFile('child', current_entry.new.path)
            return (file1, file2)

        # If we're still here, no arguments were specified.
        if current_entry.status == git.diff.Status.DELETED:
            # If the current file is a deleted file,
            # diff the file in the parent against /dev/null
            file1 = cli_obj.review.getFile('parent',
                                           current_entry.old.path)
            file2 = '/dev/null'
            return (file1, file2)
        elif current_entry.status == git.diff.Status.ADDED:
            # If the current file is a new file, diff /dev/null
            # against the file in the child.
            file1 = '/dev/null'
            file2 = cli_obj.review.getFile('child', current_entry.new.path)
            return (file1, file2)
        else:
            # Diff the parent file against the child file
            file1 = cli_obj.review.getFile('parent', current_entry.old.path)
            file2 = cli_obj.review.getFile('child', current_entry.new.path)
            return (file1, file2)

    def runParsed(self, cli_obj, name, args):
        try:
            files = self.__getDiffFiles(cli_obj, args)
        except NoCurrentEntryError, ex:
            cli_obj.outputError(ex)
            return 1
        except git.NoSuchBlobError, ex:
            # Convert the "blob" error message to "file", just to be more
            # user-friendly for developers who aren't familiar with git
            # terminology.
            cli_obj.outputError('no such file %r' % (ex.name,))
            return 1
        except git.NotABlobError, ex:
            cli_obj.outputError('not a file %r' % (ex.name,))
            return 1

        cmd = cli_obj.getDiffCommand(*files)
        try:
            p = subprocess.Popen(cmd)
        except OSError, ex:
            cli_obj.outputError('failed to invoke %r: %s' % (cmd[0], ex))
            return 1

        ret = p.wait()
        cli_obj.setSuggestedCommand('next')
        return ret


class ViewCommand(cli.ArgCommand):
    def __init__(self):
        help = 'View the specified file'
        args = [CommitFileArgument('path', optional=True, default=None,
                                   default_commit='child')]
        cli.ArgCommand.__init__(self, args, help)

    def runParsed(self, cli_obj, name, args):
        if args.path is None:
            # If no path was specified, pick the path from the current entry
            try:
                current_entry = cli_obj.review.getCurrentEntry()
            except NoCurrentEntryError, ex:
                cli_obj.outputError(ex)
                return 1

            # If this is a deleted file, view the old version
            # Otherwise, view the new version
            if current_entry.status == git.diff.Status.DELETED:
                commit = 'parent'
                path = current_entry.old.path
            else:
                commit = 'child'
                path = current_entry.new.path
        else:
            commit, path = args.path

        try:
            file = cli_obj.review.getFile(commit, path)
        except git.NoSuchBlobError, ex:
            # Convert the "blob" error message to "file", just to be more
            # user-friendly for developers who aren't familiar with git
            # terminology.
            cli_obj.outputError('no such file %r' % (ex.name,))
            return 1
        except git.NotABlobError, ex:
            cli_obj.outputError('not a file %r' % (ex.name,))
            return 1

        cmd = cli_obj.getViewCommand(file)
        try:
            p = subprocess.Popen(cmd)
        except OSError, ex:
            cli_obj.outputError('failed to invoke %r: %s' % (cmd[0], ex))
            return 1

        ret = p.wait()
        cli_obj.setSuggestedCommand('next')
        return ret


class AliasCommand(cli.ArgCommand):
    def __init__(self):
        help = 'View or set a commit alias'
        args = [AliasArgument('alias', optional=True),
                CommitArgument('commit', optional=True)]
        cli.ArgCommand.__init__(self, args, help)

    def runParsed(self, cli_obj, name, args):
        if args.alias is None:
            # Show all aliases
            sorted_aliases = sorted(cli_obj.review.commitAliases.iteritems(),
                                    key=lambda x: x[0])
            for (alias, commit) in sorted_aliases:
                cli_obj.output('%s: %s'% (alias, commit))
        elif args.commit is None:
            # Show the specified alias
            try:
                commit = cli_obj.review.commitAliases[args.alias]
                cli_obj.output('%s: %s'% (args.alias, commit))
            except KeyError:
                cli_obj.outputError('unknown alias %r' % (args.alias,))
                return 1
        else:
            # Set the specified alias
            try:
                cli_obj.review.setCommitAlias(args.alias, args.commit)
            except git.NoSuchObjectError, ex:
                cli_obj.outputError(ex)
                return 1

        return 0


class UnaliasCommand(cli.ArgCommand):
    def __init__(self):
        help = 'Unset a commit alias'
        args = [AliasArgument('alias')]
        cli.ArgCommand.__init__(self, args, help)

    def runParsed(self, cli_obj, name, args):
        try:
            cli_obj.review.unsetCommitAlias(args.alias)
        except KeyError:
            cli_obj.outputError('unknown alias %r' % (args.alias,))
            return 1
        return 0


class RepoCache(object):
    """
    A wrapper around a Repository object that caches the results from
    some git commands.

    This is used mainly to speed up command line completion; which would
    otherwise run the same getRefNames() and listTree() multiple times while
    the user is tab completing a commit/path.
    """
    def __init__(self, repo):
        self.__repo = repo
        self.clearCaches()

    def getRefNames(self):
        if self.__refNames is None:
            self.__refNames = self.__repo.getRefNames()
        return self.__refNames[:]

    def listTree(self, commit, dirname=None):
        key = (commit, dirname)
        try:
            return self.__treeCache[key]
        except KeyError:
            result = self.__repo.listTree(commit, dirname=dirname)
            self.__treeCache[key] = result
            return result

    def clearCaches(self):
        self.__refNames = None
        self.__treeCache = {}


class CliReviewer(cli.CLI):
    def __init__(self, review):
        cli.CLI.__init__(self)

        # Internal state
        self.review = review
        self.repoCache = RepoCache(self.review.repo)
        self.configureCommands()

        # Commands
        self.addCommand('exit', ExitCommand())
        self.addCommand('quit', ExitCommand())
        self.addCommand('list', ListCommand())
        self.addCommand('files', ListCommand())
        self.addCommand('next', NextCommand())
        self.addCommand('prev', PrevCommand())
        self.addCommand('goto', GotoCommand())
        self.addCommand('diff', DiffCommand())
        self.addCommand('view', ViewCommand())
        self.addCommand('alias', AliasCommand())
        self.addCommand('unalias', UnaliasCommand())
        self.addCommand('help', cli.HelpCommand())
        self.addCommand('?', cli.HelpCommand())

        self.indexUpdated()

    def configureCommands(self):
        # TODO: It would be nice to support a ~/.gitreviewrc file, too, or
        # maybe even storing configuration via git-config.

        # Check the following environment variables
        # to see which program we should use to view files.
        viewer_str = None
        if os.environ.has_key('GIT_REVIEW_VIEW'):
            viewer_str = os.environ['GIT_REVIEW_VIEW']
        elif os.environ.has_key('GIT_EDITOR'):
            viewer_str = os.environ['GIT_EDITOR']
        elif os.environ.has_key('VISUAL'):
            viewer_str = os.environ['VISUAL']
        elif os.environ.has_key('EDITOR'):
            viewer_str = os.environ['EDITOR']

        if viewer_str is None:
            self.viewCommand = ['vi']
        else:
            tokenizer = cli.tokenize.SimpleTokenizer(viewer_str)
            self.viewCommand = tokenizer.getTokens()

        # Check the following environment variables
        # to see which program we should use to view files.
        if os.environ.has_key('GIT_REVIEW_DIFF'):
            diff_str = os.environ['GIT_REVIEW_DIFF']
            tokenizer = cli.tokenize.SimpleTokenizer(diff_str)
            self.diffCommand = tokenizer.getTokens()
        elif os.environ.has_key('DISPLAY'):
            # If the user appears to be using X, default to tkdiff
            self.diffCommand = ['tkdiff']
        else:
            # vimdiff is very convenient for viewing
            # side-by-side diffs in a terminal.
            #
            # We could default to plain old 'diff' if people don't like
            # vimdiff.  However, I figure most people will configure their
            # preferred diff program with GIT_REVIEW_DIFF.
            self.diffCommand = ['vimdiff', '-R']

    def invokeCommand(self, cmd_name, args, line):
        # Before every command, clear our repository cache
        self.repoCache.clearCaches()

        # Invoke CLI.invokeCommand() to perform the real work
        cli.CLI.invokeCommand(self, cmd_name, args, line)

    def handleEmptyLine(self):
        self.runCommand(self.suggestedCommand)

    def setSuggestedCommand(self, mode):
        if mode == 'lint':
            # TODO: once we support lint, set the suggested command to 'lint'
            # for files that we know how to run lint on.
            # self.suggestedCommand = 'lint'
            self.setSuggestedCommand('review')
        elif mode == 'review':
            entry = self.review.getCurrentEntry()
            if entry.status == git.diff.Status.DELETED:
                self.setSuggestedCommand('next')
            elif entry.status == git.diff.Status.ADDED:
                self.suggestedCommand = 'view'
            elif entry.status == git.diff.Status.UNMERGED:
                # TODO: We could probably do better here.
                if self.review.diff.parent == git.COMMIT_INDEX:
                    # Suggest a 3-way diff between the ancestor and the
                    # 2 sides of the merge.  This won't work if the user's diff
                    # command doesn's support 3-way diffs.  It also breaks if
                    # the file only exists on one side of the merge.
                    self.suggestedCommand = 'diff :1 :2 :3'
                else:
                    # Suggest a 3-way diff between the parent and the
                    # 2 sides of the merge.  This won't work if the user's diff
                    # command doesn's support 3-way diffs.  It also breaks if
                    # the file only exists on one side of the merge.
                    self.suggestedCommand = 'diff parent :2 :3'
            else:
                self.suggestedCommand = 'diff'
        elif mode == 'next':
            if self.review.hasNext():
                self.suggestedCommand = 'next'
            else:
                self.setSuggestedCommand('quit')
        elif mode == 'quit':
            self.suggestedCommand = 'quit'
        else:
            assert False

        self.updatePrompt()

    def indexUpdated(self):
        try:
            entry = self.review.getCurrentEntry()
        except NoCurrentEntryError:
            # Should only happen when there are no files to review.
            msg = 'No files to review'
            self.setSuggestedCommand('quit')
            return

        msg = 'Now processing %s file ' % (entry.status.getDescription(),)
        if entry.status == git.diff.Status.RENAMED or \
                entry.status == git.diff.Status.COPIED:
            msg += '%s\n--> %s' % (entry.old.path, entry.new.path)
        else:
            msg += entry.getPath()
        self.output(msg)
        # setSuggestedCommand() will automatically update the prompt
        self.setSuggestedCommand('lint')

    def updatePrompt(self):
        try:
            path = self.review.getCurrentEntry().getPath()
            basename = os.path.basename(path)
            self.prompt = '%s [%s]> ' % (basename, self.suggestedCommand)
        except NoCurrentEntryError:
            self.prompt = '[%s]> ' % (self.suggestedCommand)

    def getViewCommand(self, path):
        return self.viewCommand + [str(path)]

    def getDiffCommand(self, path1, path2, path3=None):
        cmd = self.diffCommand + [str(path1), str(path2)]
        if path3 != None:
            cmd.append(str(path3))
        return cmd

    def run(self):
        return self.loop()

    def completeCommit(self, text, append=' ', append_exact=False):
        """
        Complete a commit name or commit alias.
        """
        matches = []
        ref_names = self.repoCache.getRefNames()
        # Also match against the special COMMIT_WD and COMMIT_INDEX names.
        ref_names.extend([git.COMMIT_INDEX, git.COMMIT_WD])
        for ref in ref_names:
            # Match against any trailing part of the ref name
            # for example, if the ref is "refs/heads/foo",
            # first try to match against the whole thing, then against
            # "heads/foo", then just "foo"
            while True:
                if ref.startswith(text):
                    matches.append(ref)
                parts = ref.split('/', 1)
                if len(parts) < 2:
                    break
                ref = parts[1]

        for alias in self.review.getCommitAliases():
            if alias.startswith(text):
                matches.append(alias)

        if append and len(matches) == 1:
            # If there is only 1 match, check to see if we should append
            # the string specified by append.
            #
            # If append_exact is true, only append if the text matches
            # the full commit name.
            if (not append_exact) or (matches[0] == text):
                matches[0] += append

        return matches

    def completeFilename(self, commit, text):
        """
        Complete a filename within the given commit.
        """
        # Don't use os.path.split() or dirname() here, since that performs
        # some canonicalization like stripping out extra slashes.  We need to
        # return matches that with the exact text specified.
        idx = text.rfind(os.path.sep)
        if idx < 0:
            dirname = ''
            basename = text
        else:
            dirname = text[:idx+1]
            basename = text[idx+1:]

        # Expand commit name aliases
        commit = self.review.expandCommitName(commit)
        matches = []
        try:
            tree_entries = self.repoCache.listTree(commit, dirname)
        except OSError, ex:
            return []

        for entry in tree_entries:
            if entry.name.startswith(basename):
                matches.append(entry)

        # If there is only 1 match, and it is a blob, add a space
        # TODO: It would be nicer to honor user's inputrc settings
        if len(matches) == 1 and matches[0].type == git.OBJ_BLOB:
            return [dirname + matches[0].name + ' ']

        string_matches = []
        for entry in matches:
            full_match = dirname + entry.name
            if entry.type == git.OBJ_TREE:
                full_match += os.path.sep
            string_matches.append(full_match)

        return string_matches

########NEW FILE########
__FILENAME__ = exceptions
#!/usr/bin/python -tt
#
# Copyright 2009-2010 Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
class ReviewError(Exception):
    pass


class NoCurrentEntryError(ReviewError):
    def __init__(self):
        ReviewError.__init__(self, 'no current entry to process')

########NEW FILE########
