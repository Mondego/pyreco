__FILENAME__ = actions
"""Vroom action parsing (actions are different types of vroom lines)."""
import vroom
import vroom.controls

ACTION = vroom.Specification(
    COMMENT='comment',
    PASS='pass',
    INPUT='input',
    COMMAND='command',
    TEXT='text',
    CONTINUATION='continuation',
    DIRECTIVE='directive',
    MESSAGE='message',
    SYSTEM='system',
    HIJACK='hijack',
    OUTPUT='output')

DIRECTIVE = vroom.Specification(
    CLEAR='clear',
    END='end',
    MESSAGES='messages',
    SYSTEM='system')

DIRECTIVE_PREFIX = '  @'
EMPTY_LINE_CHECK = '  &'

# The number of blank lines that equate to a @clear command.
# (Set to None to disable).
BLANK_LINE_CLEAR_COMBO = 3

UNCONTROLLED_LINE_TYPES = {
    ACTION.CONTINUATION: '  |',
}

DELAY_OPTIONS = (vroom.controls.OPTION.DELAY,)
MODE_OPTIONS = (vroom.controls.OPTION.MODE,)
BUFFER_OPTIONS = (vroom.controls.OPTION.BUFFER,)
HIJACK_OPTIONS = (vroom.controls.OPTION.OUTPUT_CHANNEL,)
OUTPUT_OPTIONS = (
    vroom.controls.OPTION.BUFFER,
    vroom.controls.OPTION.RANGE,
    vroom.controls.OPTION.MODE,
)

CONTROLLED_LINE_TYPES = {
    ACTION.INPUT: ('  > ', DELAY_OPTIONS),
    ACTION.TEXT: ('  % ', DELAY_OPTIONS),
    ACTION.COMMAND: ('  :', DELAY_OPTIONS),
    ACTION.MESSAGE: ('  ~ ', MODE_OPTIONS),
    ACTION.SYSTEM: ('  ! ', MODE_OPTIONS),
    ACTION.HIJACK: ('  $ ', HIJACK_OPTIONS),
    ACTION.OUTPUT: ('  & ', OUTPUT_OPTIONS),
}


def ActionLine(line):
  """Parses a single action line of a vroom file.

  >>> ActionLine('This is a comment.')
  ('comment', 'This is a comment.', {})
  >>> ActionLine('  > iHello, world!<ESC> (2s)')
  ('input', 'iHello, world!<ESC>', {'delay': 2.0})
  >>> ActionLine('  :wqa')
  ('command', 'wqa', {'delay': None})
  >>> ActionLine('  % Hello, world!')  # doctest: +ELLIPSIS
  ('text', 'Hello, world!', ...)
  >>> ActionLine('  |To be continued.')
  ('continuation', 'To be continued.', {})
  >>> ActionLine('  ~ ERROR(*): (glob)')
  ('message', 'ERROR(*):', {'mode': 'glob'})
  >>> ActionLine('  ! system says (regex)')
  ('system', 'system says', {'mode': 'regex'})
  >>> ActionLine('  $ I say...')  # doctest: +ELLIPSIS
  ('hijack', 'I say...', ...)
  >>> ActionLine('  $ I say... (stderr)')  # doctest: +ELLIPSIS
  ('hijack', 'I say...', ...)
  >>> ActionLine('  @clear')
  ('directive', 'clear', {})
  >>> ActionLine('  @nope')
  Traceback (most recent call last):
    ...
  ParseError: Unrecognized directive "nope"
  >>> ActionLine('  & Output!')  # doctest: +ELLIPSIS
  ('output', 'Output!', ...)
  >>> ActionLine('  Simpler output!')  # doctest: +ELLIPSIS
  ('output', 'Simpler output!', ...)

  Args:
    line: The line (string)
  Returns:
    (ACTION, line, controls) where line is the original line with the newline,
        action prefix ('  > ', etc.) and control block removed, and controls is
        a control dictionary.
  Raises:
    vroom.ParseError
  """
  line = line.rstrip('\n')

  # PASS is different from COMMENT in that PASS breaks up output blocks,
  # hijack continuations, etc.
  if not line:
    return (ACTION.PASS, line, {})

  if not line.startswith('  '):
    return (ACTION.COMMENT, line, {})

  # These lines do not use control blocks.
  # NOTE: We currently don't even check for control blocks on these line types,
  # preferring to trust the user. We should consider which scenario is more
  # common: People wanting a line ending in parentheses without escaping them,
  # and so using a continuation, versus people accidentally putting a control
  # block where they shouldn't and being surprised when it's ignored.
  # Data would be nice.
  for linetype, prefix in UNCONTROLLED_LINE_TYPES.items():
    if line.startswith(prefix):
      return (linetype, line[len(prefix):], {})

  # Directives must be parsed in two chunks, as some allow controls blocks and
  # some don't. This section is directives with no control blocks.
  if line.startswith(DIRECTIVE_PREFIX):
    directive = line[len(DIRECTIVE_PREFIX):]
    if directive == DIRECTIVE.CLEAR:
      return (ACTION.DIRECTIVE, directive, {})

  line, controls = vroom.controls.SplitLine(line)

  def Controls(options):
    return vroom.controls.Parse(controls or '', *options)

  # Here lie directives that have control blocks.
  if line.startswith(DIRECTIVE_PREFIX):
    directive = line[len(DIRECTIVE_PREFIX):]
    if directive == DIRECTIVE.END:
      return (ACTION.DIRECTIVE, directive, Controls(BUFFER_OPTIONS))
    elif directive == DIRECTIVE.MESSAGES:
      return (ACTION.DIRECTIVE, directive, Controls(
          (vroom.controls.OPTION.MESSAGE_STRICTNESS,)))
    elif directive == DIRECTIVE.SYSTEM:
      return (ACTION.DIRECTIVE, directive, Controls(
          (vroom.controls.OPTION.SYSTEM_STRICTNESS,)))
    # Non-controlled directives should be parsed before SplitLineControls.
    raise vroom.ParseError('Unrecognized directive "%s"' % directive)

  for linetype, (prefix, options) in CONTROLLED_LINE_TYPES.items():
    if line.startswith(prefix):
      return (linetype, line[len(prefix):], Controls(options))

  # Special output to match empty buffer lines without trailing whitespace.
  if line == EMPTY_LINE_CHECK:
    return (ACTION.OUTPUT, '', Controls(OUTPUT_OPTIONS))

  # Default
  return (ACTION.OUTPUT, line[2:], Controls(OUTPUT_OPTIONS))


def Parse(lines):
  """Parses a vroom file.

  Is actually a generator.

  Args:
    lines: An iterable of lines to parse. (A file handle will do.)
  Yields:
    (Number, ACTION, Line, Control Dictionary) where
        Number is the original line number (which may not be the same as the
            index in the list if continuation lines were used. It's the line
            number of the last relevant continuation.)
        ACTION is the ACTION (will never be COMMENT nor CONTINUATION)
        Line is the parsed line.
        Control Dictionary is the control data.
  Raises:
    vroom.ParseError with the relevant line number and an error message.
  """
  pending = None
  pass_count = 0
  for (lineno, line) in enumerate(lines):
    try:
      (linetype, line, control) = ActionLine(line)
    # Add line number context to all parse errors.
    except vroom.ParseError as e:
      e.SetLineNumber(lineno)
      raise
    # Ignore comments during vroom execution.
    if linetype == ACTION.COMMENT:
      # Comments break blank-line combos.
      pass_count = 0
      continue
    # Continuation actions are chained to the pending action.
    if linetype == ACTION.CONTINUATION:
      if pending is None:
        raise vroom.ConfigurationError('No command to continue', lineno)
      pending = (lineno, pending[1], pending[2] + line, pending[3])
      continue
    # Contiguous hijack commands are chained together by newline.
    if (pending is not None and
        pending[1] == ACTION.HIJACK and
        not control and
        linetype == ACTION.HIJACK):
      pending = (lineno, linetype, '\n'.join((pending[2], line)), pending[3])
      continue
    # Flush out any pending commands now that we know there's no continuations.
    if pending:
      yield pending
      pending = None
    action = (lineno, linetype, line, control)
    # PASS lines can't be continuated.
    if linetype == ACTION.PASS:
      pass_count += 1
      if pass_count == BLANK_LINE_CLEAR_COMBO:
        yield (lineno, ACTION.DIRECTIVE, DIRECTIVE.CLEAR, {})
      else:
        yield action
    else:
      pass_count = 0
    # Hold on to this line in case it's followed by a continuation.
    pending = action
  # Flush out any actions still in the queue.
  if pending:
    yield pending

########NEW FILE########
__FILENAME__ = args
"""Vroom command line arguments."""
import argparse
import glob
import itertools
import os.path
import sys

import vroom.color
import vroom.messages
import vroom.shell


parser = argparse.ArgumentParser(description='Vroom: launch your tests.')


class DirectoryArg(argparse.Action):
  """An argparse action for a valid directory path."""

  def __call__(self, _, namespace, values, option_string=None):
    if not os.path.isdir(values):
      raise argparse.ArgumentTypeError('Invalid directory "%s"' % values)
    if not os.access(values, os.R_OK):
      raise argparse.ArgumentTypeError('Cannot read directory "%s"' % values)
    setattr(namespace, self.dest, values)


#
# Ways to run vroom.

parser.add_argument(
    'filename',
    nargs='*',
    help="""
The vroom file(s) to run.
""")

parser.add_argument(
    '--crawl',
    action=DirectoryArg,
    nargs='?',
    const='.',
    default=None,
    metavar='DIR',
    help="""
Crawl [DIR] looking for vroom files.
if [DIR] is not given, the current directory is crawled.
""")

parser.add_argument(
    '--skip',
    nargs='+',
    default=[],
    metavar='PATH',
    help="""
Ignore PATH when using --crawl.
PATH may refer to a test or a directory containing tests.
PATH must be relative to the --crawl directory.
""")

management_group = parser.add_argument_group(
    'management',
    'Manage other running vroom processes')
management_group.add_argument(
    '--murder',
    action='store_true',
    default=False,
    help="""
Kill a running vroom test.
This will kill the first vroom (beside the current process) found.
If you want to kill a specific vroom, find the process number and kill it
yourself.
""")


#
# Vim configuration

parser.add_argument(
    '-s',
    '--servername',
    default='vroom',
    help="""
The vim servername (see :help clientserver).
Use this to help vroom differentiate between vims if you want to run multiple
vrooms at once.
""")

parser.add_argument(
    '-u',
    '--vimrc',
    default='NONE',
    help="""
vimrc file to use.
""")

parser.add_argument(
    '-i',
    '--interactive',
    action='store_true',
    help="""
Keeps vim open after a vroom failure, allowing you to inspect vim's state.
""")


#
# Timing

parser.add_argument(
    '-d',
    '--delay',
    type=float,
    default=0.09,
    metavar='DELAY',
    help="""
Delay after each vim command (in seconds).
""")

parser.add_argument(
    '--shell-delay',
    type=float,
    default=0.25,
    metavar='SHELL_DELAY',
    help="""
Extra delay after a vim command that's expected to trigger a shell command.
""")

parser.add_argument(
    '-t',
    '--startuptime',
    type=float,
    default=0.5,
    metavar='STARTUPTIME',
    help="""
How long to wait for vim to start (in seconds).
""")

#
# Output configuration

parser.add_argument(
    '-o',
    '--out',
    default=sys.stdout,
    type=argparse.FileType('w'),
    metavar='FILE',
    help="""
Write test output to [FILE] instead of STDOUT.
Vroom output should never be redirected, as vim will want to control stdout for
the duration of the testing.
""")

parser.add_argument(
    '-v',
    '--verbose',
    action='store_true',
    help="""
Increase the amount of test output.
""")

parser.add_argument(
    '--nocolor',
    dest='color',
    action='store_const',
    const=vroom.color.Colorless,
    default=vroom.color.Colored,
    help="""
Turn off color in output.
""")

parser.add_argument(
    '--dump-messages',
    nargs='?',
    const=True,
    default=None,
    type=argparse.FileType('w'),
    metavar='FILE',
    help="""
Dump a log of vim messages received during execution.
See :help messages in vim.
Logs are written to [FILE], or to the same place as --out if [FILE] is ommited.
""")

parser.add_argument(
    '--dump-commands',
    nargs='?',
    const=True,
    default=None,
    type=argparse.FileType('w'),
    metavar='FILE',
    help="""
Dump a list of command sent to vim during execution.
Logs are written to [FILE], or to the same place as --out if [FILE] is ommited.
""")


parser.add_argument(
    '--dump-syscalls',
    nargs='?',
    const=True,
    default=None,
    type=argparse.FileType('w'),
    metavar='FILE',
    help="""
Dump vim system call logs to [FILE].
Logs are written to [FILE], or to the same place as --out if [FILE] is ommited.
""")


#
# Strictness configuration

parser.add_argument(
    '--message-strictness',
    choices=vroom.messages.STRICTNESS.Values(),
    default=vroom.messages.STRICTNESS.ERRORS,
    help="""
How to deal with unexpected messages.
When STRICT, unexpected messages will be treated as errors.
When RELAXED, unexpected messages will be ignored.
When GUESS-ERRORS (default), unexpected messages will be ignored unless vroom
things they look suspicious. Suspicious messages include things formatted like
vim errors like "E86: Buffer 3 does not exist" and messages that start with
ERROR.
""")

parser.add_argument(
    '--system-strictness',
    choices=vroom.shell.STRICTNESS.Values(),
    default=vroom.shell.STRICTNESS.STRICT,
    help="""
How to deal with unexpected system calls.
When STRICT (default), unexpected system calls will be treated as errors.
When RELAXED, unexpected system calls will be ignored.
""")


#
# Environment configuration

parser.add_argument(
    '--shell',
    default='shell.vroomfaker',
    help="""
The dummy shell executable (either a path or something on the $PATH).
Defaults to the right thing if you installed vroom normally.
""")

parser.add_argument(
    '--responder',
    default='respond.vroomfaker',
    help="""
The dummy responder executable (either a path or something on the $PATH).
Defaults to the right thing if you installed vroom normally.
""")


def Parse(args):
  """Parse the given arguments.

  Does a bit of magic to make sure that color isn't printed when output is being
  piped to a file.

  Does a bit more magic so you can use that --dump-messages and its ilk follow
  --out by default, instead of always going to stdout.

  Expands the filename arguments and complains if they don't point to any real
  files (unless vroom's doing something else).

  Args:
    args: The arguments to parse
  Returns:
    argparse.Namespace of the parsed args.
  Raises:
    ValueError: If the args are bad.
  """
  args = parser.parse_args(args)

  if args.out != sys.stdout:
    args.color = vroom.color.Colorless

  for dumper in ('dump_messages', 'dump_commands', 'dump_syscalls'):
    if getattr(args, dumper) is True:
      setattr(args, dumper, args.out)

  args.filenames = list(itertools.chain(
      Crawl(args.crawl, args.skip),
      *map(Expand, args.filename)))
  if not args.filenames and not args.murder:
    raise ValueError('Nothing to do.')
  if args.murder and args.filenames:
    raise ValueError(
        'You may birth tests and you may end them, but not both at once!')

  return args


def Close(args):
  """Cleans up an argument namespace, closing files etc.

  Args:
    args: The argparse.Namespace to close.
  """
  optfiles = [args.dump_messages, args.dump_commands, args.dump_syscalls]
  for optfile in filter(bool, optfiles):
    optfile.close()
  args.out.close()


def Expand(filename):
  """Expands a filename argument into a list of relevant filenames.

  Args:
    filename: The filename to expand.
  Raises:
    ValueError: When filename is non-existent.
  Returns:
    All vroom files in the directory (if it's a directory) and all files
    matching the glob (if it's a glob).
  """
  if os.path.isdir(filename):
    return glob.glob(os.path.join(filename, '*.vroom'))
  files = list(glob.glob(filename))
  if not files and os.path.exists(filename + '.vroom'):
    files = [filename + '.vroom']
  elif not files and not glob.has_magic(filename):
    raise ValueError('File "%s" not found.' % filename)
  return files


def IgnoredPaths(directory, skipped):
  for path in skipped:
    # --skip paths must be relative to the --crawl directory.
    path = os.path.join(directory, path)
    # All ignored paths which do not end in '.vroom' are assumed to be
    # directories. We have to make sure they've got a trailing slash, or
    # --skip=foo will axe anything with a foo prefix (foo/, foobar/, etc.)
    if not path.endswith('.vroom'):
      path = os.path.join(path, '')
    yield path


def Crawl(directory, ignored):
  """Crawls a directory looking for vroom files.

  Args:
    directory: The directory to crawl, may be None.
    ignored: A list of paths (absolute or relative to crawl directory) that will
        be pruned from the crawl results.
  Yields:
    the vroom files.
  """
  if not directory:
    return

  ignored = list(IgnoredPaths(directory, ignored))

  for (dirpath, dirnames, filenames) in os.walk(directory):
    # Traverse directories in alphabetical order. Default order fine for fnames.
    dirnames.sort()
    for filename in filenames:
      fullpath = os.path.join(dirpath, filename)
      for ignore in ignored:
        shared = os.path.commonprefix([ignore, fullpath])
        if shared == ignore:
          break
      else:
        if filename.endswith('.vroom'):
          yield fullpath

########NEW FILE########
__FILENAME__ = buffer
"""Vroom buffer handling."""
import vroom.controls
import vroom.test

# Pylint is not smart enough to notice that all the exceptions here inherit from
# vroom.test.Failure, which is a standard Exception.
# pylint: disable-msg=nonstandard-exception


class Manager(object):
  """Manages the vim buffers."""

  def __init__(self, vim):
    self.vim = vim
    self.Unload()

  def Unload(self):
    """Unload the current buffer."""
    self._loaded = False
    self._buffer = None
    self._data = []
    self._line = None
    self._last_range = None

  def Load(self, buff):
    """Loads the requested buffer.

    If no buffer is loaded nor requested, the active buffer is used.
    Otherwise if no buffer is requested, the current buffer is used.
    Otherwise the requested buffer is loaded.

    Args:
      buff: The buffer to load.
    """
    if self._loaded and buff is None:
      return
    self.Unload()
    self._data = self.vim.GetBufferLines(buff)
    self._buffer = buff
    self._loaded = True

  def View(self, start, end):
    """A generator over given lines in a buffer.

    When vim messages are viewed in this fashion, the messenger object will be
    notified that those messages were not unexpected.

    Args:
      start: The beginning of the range.
      end: A function to get the end of the range.
    Yields:
      An iterable over the range.
    Raises:
      NotEnoughOutput: when the range exceeds the buffer.
    """
    # If no start line is given, we advance to the next line. Therefore, if the
    # buffer has not yet been inspected we want to start at one before line 0.
    self._line = -1 if self._line is None else self._line
    # Vim 1-indexes lines.
    if start == vroom.controls.SPECIAL_RANGE.CURRENT_LINE:
      start = self.vim.GetCurrentLine() - 1
    else:
      start = (self._line + 1) if start is None else (start - 1)

    # No need to decrement; vroom ranges are inclusive and vim 1-indexes.
    end = (start + 1) if end is None else end(start + 1)
    # End = 0 means check till end of buffer.
    end = len(self._data) if end is 0 else end
    # If there's an error, they'll want to know what we were looking at.
    self._last_range = (start, end)

    # Yield each relevant line in the range.
    for i in range(start, end):
      self._line = i
      if i < len(self._data):
        yield self._data[i]
      else:
        raise NotEnoughOutput(self.GetContext())

  # 'range' is the most descriptive name here. Putting 'range' in kwargs and
  # pulling it out obfuscates the code. Sorry, pylint. (Same goes for 'buffer'.)
  def Verify(  # pylint: disable-msg=redefined-builtin
      self, desired, buffer=None, range=None, mode=None):
    """Checks the contents of a vim buffer.

    Checks that all lines in the given range in the loaded buffer match the
    given line under the given mode.

    Args:
      desired: The line that everything should look like.
      buffer: The buffer to load.
      range: The range of lines to check.
      mode: The mode to match in.
    Raises:
      WrongOutput: if the output is wrong.
    """
    self.Load(buffer)
    start, end = range or (None, None)
    for actual in self.View(start, end):
      if not vroom.test.Matches(desired, mode, actual):
        raise WrongOutput(desired, mode, self.GetContext())

  # See self.Verify for the reasoning behind the pylint trump.
  def EnsureAtEnd(self, buffer):  # pylint: disable-msg=redefined-builtin
    """Ensures that the test has verified to the end of the loaded buffer.

    Args:
      buffer: The buffer to load.
    Raises:
      BadOutput: If the buffer is not in a state to have its end checked.
      WrongOutput: If the buffer is not at the end.
    """
    self.Load(buffer)
    self._last_range = (len(self._data), len(self._data))
    if not self._line:
      if self._data == [''] or not self._data:
        return
      msg = 'Misuse of @end: buffer has not been checked yet.'
      raise BadOutput(self.GetContext(), msg)
    if self._line != len(self._data) - 1:
      raise TooMuchOutput(self.GetContext())

  def GetContext(self):
    """Information about what part of the buffer was being looked at.

    Invaluable in exceptions.

    Returns:
      Dict containing 'buffer', 'data', 'line', 'start', and 'end'.
    """
    if (not self._loaded) or (self._last_range is None):
      return None
    (start, end) = self._last_range
    return {
        'buffer': self._buffer,
        'data': self._data,
        'line': self._line,
        'start': start,
        'end': end,
    }


class BadOutput(vroom.test.Failure):
  """Raised when vim's output is not the expected output."""
  DESCRIPTION = 'Output does not match expectation.'

  def __init__(self, context, message=None):
    self.context = context
    super(BadOutput, self).__init__(message or self.DESCRIPTION)


class WrongOutput(BadOutput):
  """Raised when a line fails to match the spec."""

  def __init__(self, line, mode, context):
    """Makes the exception.

    Args:
      line: The expected line.
      mode: The match mode.
      context: The buffer context.
    """
    self.context = context
    mode = mode or vroom.controls.DEFAULT_MODE
    msg = 'Expected "%s" in %s mode.' % (line, mode)
    super(WrongOutput, self).__init__(context, msg)


class TooMuchOutput(BadOutput):
  """Raised when vim has more output than a vroom test wants."""
  DESCRIPTION = 'Expected end of buffer.'


class NotEnoughOutput(BadOutput):
  """Raised when vim has less output than a vroom test wants."""
  DESCRIPTION = 'Unexpected end of buffer.'

########NEW FILE########
__FILENAME__ = color
"""Vroom terminal coloring."""
import subprocess

# Grab the colors from the system.
try:
  BOLD = subprocess.check_output(['tput', 'bold']).decode('utf-8')
  RED = subprocess.check_output(['tput', 'setaf', '1']).decode('utf-8')
  GREEN = subprocess.check_output(['tput', 'setaf', '2']).decode('utf-8')
  YELLOW = subprocess.check_output(['tput', 'setaf', '3']).decode('utf-8')
  BLUE = subprocess.check_output(['tput', 'setaf', '4']).decode('utf-8')
  VIOLET = subprocess.check_output(['tput', 'setaf', '5']).decode('utf-8')
  TEAL = subprocess.check_output(['tput', 'setaf', '6']).decode('utf-8')
  WHITE = subprocess.check_output(['tput', 'setaf', '7']).decode('utf-8')
  BLACK = subprocess.check_output(['tput', 'setaf', '8']).decode('utf-8')
  RESET = subprocess.check_output(['tput', 'sgr0']).decode('utf-8')
except subprocess.CalledProcessError:
  COLORED = False
else:
  COLORED = True


# We keep the unused argument for symmetry with Colored
def Colorless(text, *escapes):  # pylint: disable-msg=unused-argument
  """Idempotent.

  Args:
    text: The text to color.
    *escapes: Ignored.
  Returns:
    text
  """
  return text


def Colored(text, *escapes):
  """Prints terminal color escapes around the text.

  Args:
    text: The text to color.
    *escapes: The terminal colors to print.
  Returns:
    text surrounded by the right escapes.
  """
  if not COLORED:
    return text
  return '%s%s%s' % (''.join(escapes), text, RESET)

########NEW FILE########
__FILENAME__ = command
"""Vroom command blocks.

Vroom actions are written (by the user) out of order (from vroom's perspective).
Consider the following:

  :.!echo "Hi"
  $ Bye

Vroom must hijack the shell before the command is ever executed if the fake
shell is to know that to do when the system call comes down the line.

Thus, we need a Command object which is the combination of a command and all of
the checks and responses attached to it.
"""
import vroom.test


class Command(object):
  """Holds a vim command and records all checks requiring verification."""

  def __init__(self, command, lineno, delay, env):
    self.lineno = lineno
    self.env = env
    self.command = command
    self.delay = delay
    self.fakecmd = env.args.responder
    self._mexpectations = []
    self._syspectations = []

  def ExpectMessage(self, message, mode):
    self._mexpectations.append((message, mode))

  def ExpectSyscall(self, syscall, mode):
    if self._syspectations:
      self._syspectations[-1].closed = True
    self._syspectations.append(vroom.shell.Hijack(self.fakecmd, syscall, mode))

  def RespondToSyscall(self, response, **controls):
    if not self._syspectations or self._syspectations[-1].closed:
      self._syspectations.append(vroom.shell.Hijack(self.fakecmd))
    self._syspectations[-1].Respond(response, **controls)

  def LineBreak(self):
    if self._syspectations:
      self._syspectations[-1].closed = True

  def Execute(self):
    """Executes the command and verifies all checks."""
    if not any((self.command, self._mexpectations, self._syspectations)):
      return
    self.env.shell.Control(self._syspectations)
    oldmessages = self.env.vim.GetMessages()
    if self.lineno:
      self.env.writer.actions.ExecutedUpTo(self.lineno)
    if self.command:
      delay = self.delay
      if self._syspectations:
        delay += self.env.args.shell_delay
      self.env.vim.Communicate(self.command, delay)

    failures = []
    # Verify the message list.
    newmessages = self.env.vim.GetMessages()
    try:
      self.env.messenger.Verify(oldmessages, newmessages, self._mexpectations)
    # Don't worry, pylint. The exception will be re-raised. We need to make sure
    # that we catch code errors as well as test failures here. We don't catch
    # BaseException, so the program can still quit if it needs to.
    # pylint: disable-msg=broad-except
    except Exception as failure:
      failures.append(failure)
    # Verify the shell.
    try:
      self.env.shell.Verify()
    # See above.
    # pylint: disable-msg=broad-except
    except Exception as failure:
      failures.append(failure)
    # Wrap the list of failures in vroom.test.Failures and raise.
    if failures:
      raise vroom.test.Failures(failures)

########NEW FILE########
__FILENAME__ = controls
"""Vroom control block parsing."""
import re

import vroom

# Pylint is not smart enough to notice that all the exceptions here inherit from
# vroom.test.Failure, which is a standard Exception.
# pylint: disable-msg=nonstandard-exception

OPTION = vroom.Specification(
    BUFFER='buffer',
    RANGE='range',
    MODE='mode',
    DELAY='delay',
    MESSAGE_STRICTNESS='messages',
    SYSTEM_STRICTNESS='system',
    OUTPUT_CHANNEL='channel')

MODE = vroom.Specification(
    REGEX='regex',
    GLOB='glob',
    VERBATIM='verbatim')

SPECIAL_RANGE = vroom.Specification(
    CURRENT_LINE='.')

REGEX = vroom.Specification(
    BUFFER_NUMBER=re.compile(r'^(\d+)$'),
    RANGE=re.compile(r'^(\.|\d+)?(?:,(\+)?(\$|\d+)?)?$'),
    MODE=re.compile(r'^(%s)$' % '|'.join(MODE.Values())),
    DELAY=re.compile(r'^(\d+(?:\.\d+)?)s?$'),
    CONTROL_BLOCK=re.compile(r'(  .*) \(\s*([\w\d.+,$ ]*)\s*\)$'),
    ESCAPED_BLOCK=re.compile(r'(  .*) \(&([^)]+)\)$'))

DEFAULT_MODE = MODE.VERBATIM


def SplitLine(line):
  """Splits the line controls off of a line.

  >>> SplitLine('  > This is my line (2s)')
  ('  > This is my line', '2s')
  >>> SplitLine('  > This one has no controls')
  ('  > This one has no controls', None)
  >>> SplitLine('  > This has an escaped control (&see)')
  ('  > This has an escaped control (see)', None)
  >>> SplitLine('  world (20,)')
  ('  world', '20,')

  Args:
    line: The line to split
  Returns:
    (line, control string)
  """
  match = REGEX.CONTROL_BLOCK.match(line)
  if match:
    return match.groups()
  unescape = REGEX.ESCAPED_BLOCK.match(line)
  if unescape:
    return ('%s (%s)' % unescape.groups(), None)
  return (line, None)


def BufferWord(word):
  """Parses a buffer control word.

  >>> BufferWord('2')
  2
  >>> BufferWord('not-a-buffer')
  Traceback (most recent call last):
    ...
  UnrecognizedWord: Unrecognized control word "not-a-buffer"

  Args:
    word: The control string.
  Returns:
    An int.
  Raises:
    UnrecognizedWord: When the word is not a buffer word.
  """
  if REGEX.BUFFER_NUMBER.match(word):
    return int(word)
  raise UnrecognizedWord(word)


def RangeWord(word):
  """Parses a range control word.

  >>> RangeWord('.,')[0] == SPECIAL_RANGE.CURRENT_LINE
  True

  >>> RangeWord(',+10')[0] is None
  True
  >>> RangeWord(',+10')[1](3)
  13

  >>> RangeWord('2,$')[0]
  2
  >>> RangeWord('2,$')[1]('anything')
  0

  >>> RangeWord('8,10')[0]
  8
  >>> RangeWord('8,10')[1](8)
  10

  >>> RangeWord('20,')[0]
  20

  >>> RangeWord('farts')
  Traceback (most recent call last):
    ...
  UnrecognizedWord: Unrecognized control word "farts"

  Args:
    word: The word to parse.
  Returns:
    (start, start -> end)
  Raises:
    UnrecognizedWord: When the word is not a range word.
  """
  match = REGEX.RANGE.match(word)
  if not match:
    raise UnrecognizedWord(word)
  (start, operator, end) = match.groups()
  if start == '.':
    start = SPECIAL_RANGE.CURRENT_LINE
  elif start:
    start = int(start)
  if end is None and operator is None:
    getend = lambda x: x
  elif end == '$':
    getend = lambda x: 0
  elif operator == '+':
    getend = lambda x: x + int(end)
  else:
    getend = lambda x: int(end)
  return (start, getend)


def DelayWord(word):
  """Parses a delay control word.

  >>> DelayWord('4')
  4.0
  >>> DelayWord('4.1s')
  4.1
  >>> DelayWord('nope')
  Traceback (most recent call last):
    ...
  UnrecognizedWord: Unrecognized control word "nope"

  Args:
    word: The word to parse.
  Returns:
    The delay, in milliseconds (as a float)
  Raises:
    UnrecognizedWord: When the word is not a delay word.
  """
  match = REGEX.DELAY.match(word)
  if match:
    return float(match.groups()[0])
  raise UnrecognizedWord(word)


def ModeWord(word):
  """Parses a mode control word.

  >>> ModeWord('regex') == MODE.REGEX
  True
  >>> ModeWord('glob') == MODE.GLOB
  True
  >>> ModeWord('verbatim') == MODE.VERBATIM
  True
  >>> ModeWord('nope')
  Traceback (most recent call last):
    ...
  UnrecognizedWord: Unrecognized control word "nope"

  Args:
    word: The word to parse.
  Returns:
    The mode string, a member of MODE
  Raises:
    UnrecognizedWord: When the word is not a mode word.
  """
  match = REGEX.MODE.match(word)
  if match:
    return word
  raise UnrecognizedWord(word)


def MessageWord(word):
  """Parses a message strictness level.

  >>> import vroom.messages
  >>> MessageWord('STRICT') == vroom.messages.STRICTNESS.STRICT
  True
  >>> MessageWord('RELAXED') == vroom.messages.STRICTNESS.RELAXED
  True
  >>> MessageWord('GUESS-ERRORS') == vroom.messages.STRICTNESS.ERRORS
  True
  >>> MessageWord('nope')
  Traceback (most recent call last):
    ...
  UnrecognizedWord: Unrecognized control word "nope"

  Args:
    word: The word to parse.
  Returns:
    The strictness, a member of vroom.messages.STRICTNESS
  Raises:
    UnrecognizedWord: When the word is not a STRICTNESS.
  """
  # vroom.controls can't import vroom.messages, because that creates a circular
  # dependency both with itself (controls is imported for DEFAULT_MODE) and
  # vroom.test. Sorry, pylint
  # Pylint, brilliant as usual, thinks that this line redefines 'vroom'.
  # pylint: disable-msg=redefined-outer-name
  import vroom.messages  # pylint: disable-msg=g-import-not-at-top
  regex = re.compile(
      r'^(%s)$' % '|'.join(vroom.messages.STRICTNESS.Values()))
  match = regex.match(word)
  if match:
    return word
  raise UnrecognizedWord(word)


def SystemWord(word):
  """Parses a system strictness level.

  >>> import vroom.shell
  >>> SystemWord('STRICT') == vroom.shell.STRICTNESS.STRICT
  True
  >>> SystemWord('RELAXED') == vroom.shell.STRICTNESS.RELAXED
  True
  >>> SystemWord('nope')
  Traceback (most recent call last):
    ...
  UnrecognizedWord: Unrecognized control word "nope"

  Args:
    word: The word to parse.
  Returns:
    The strictness, a member of vroom.shell.STRICTNESS
  Raises:
    UnrecognizedWord: When the word is not a STRICTNESS.
  """
  # vroom.controls can't import vroom.shell, because that creates a circular
  # dependency both with itself (controls is imported for DEFAULT_MODE) and
  # vroom.test. Sorry, pylint.
  # Pylint, brilliant as usual, thinks that this line redefines 'vroom'.
  # pylint: disable-msg=redefined-outer-name
  import vroom.shell  # pylint: disable-msg=g-import-not-at-top
  regex = re.compile(
      r'^(%s)$' % '|'.join(vroom.shell.STRICTNESS.Values()))
  match = regex.match(word)
  if match:
    return word
  raise UnrecognizedWord(word)


def OutputChannelWord(word):
  """Parses a system output channel.

  >>> import vroom.shell
  >>> OutputChannelWord('stdout') == vroom.shell.OUTCHANNEL.STDOUT
  True
  >>> OutputChannelWord('stderr') == vroom.shell.OUTCHANNEL.STDERR
  True
  >>> OutputChannelWord('command') == vroom.shell.OUTCHANNEL.COMMAND
  True
  >>> OutputChannelWord('status') == vroom.shell.OUTCHANNEL.STATUS
  True
  >>> OutputChannelWord('nope')
  Traceback (most recent call last):
    ...
  UnrecognizedWord: Unrecognized control word "nope"

  Args:
    word: The word to parse.
  Returns:
    The output channel, a member of vroom.shell.OUTCHANNEL
  Raises:
    UnrecognizedWord: When the word is not an OUTCHANNEL.
  """
  # vroom.controls can't import vroom.shell, because that creates a circular
  # dependency both with itself (controls is imported for DEFAULT_MODE) and
  # vroom.test. Sorry, pylint
  # Pylint, brilliant as usual, thinks that this line redefines 'vroom'.
  # pylint: disable-msg=redefined-outer-name
  import vroom.shell  # pylint: disable-msg=g-import-not-at-top
  regex = re.compile(
      r'^(%s)$' % '|'.join(vroom.shell.OUTCHANNEL.Values()))
  match = regex.match(word)
  if match:
    return word
  raise UnrecognizedWord(word)


OPTION_PARSERS = {
    OPTION.BUFFER: BufferWord,
    OPTION.RANGE: RangeWord,
    OPTION.MODE: ModeWord,
    OPTION.DELAY: DelayWord,
    OPTION.MESSAGE_STRICTNESS: MessageWord,
    OPTION.SYSTEM_STRICTNESS: SystemWord,
    OPTION.OUTPUT_CHANNEL: OutputChannelWord,
}


def Parse(controls, *options):
  """Parses a control block.

  >>> controls = Parse('2 .,+2 regex 4.02s')
  >>> (controls['buffer'], controls['mode'], controls['delay'])
  (2, 'regex', 4.02)
  >>> (controls['range'][0], controls['range'][1](1))
  ('.', 3)

  >>> controls = Parse('1 2', OPTION.BUFFER, OPTION.DELAY)
  >>> (controls['buffer'], controls['delay'])
  (1, 2.0)

  >>> controls = Parse('1 2', OPTION.DELAY, OPTION.BUFFER)
  >>> (controls['buffer'], controls['delay'])
  (2, 1.0)

  >>> Parse('1 2 3', OPTION.DELAY, OPTION.BUFFER)
  Traceback (most recent call last):
    ...
  DuplicatedControl: Duplicated buffer control "3"

  >>> Parse('regex 4.02s', OPTION.MODE)
  Traceback (most recent call last):
    ...
  UnrecognizedWord: Unrecognized control word "4.02s"

  >>> Parse('STRICT', OPTION.MESSAGE_STRICTNESS)
  {'messages': 'STRICT'}
  >>> Parse('STRICT', OPTION.SYSTEM_STRICTNESS)
  {'system': 'STRICT'}

  Pass in members of OPTION to restrict what types of words are allowed and to
  control word precedence. If no options are passed in, all are allowed with
  precedence BUFFER, RANGE, MODE, DELAY

  Args:
    controls: The control string to parse.
    *options: The allowed OPTION type for each word (in order of precedence).
  Returns:
    A dict with the controls, with OPTION's values for keys. The keys will
    always exist, and will be None if the option was not present.
  Raises:
    ValueError: When the control can not be parsed.
  """
  if not options:
    options = [OPTION.BUFFER, OPTION.RANGE, OPTION.MODE, OPTION.DELAY]
  for option in [o for o in options if o not in OPTION_PARSERS]:
    raise ValueError("Can't parse unknown control word: %s" % option)
  parsers = [(o, OPTION_PARSERS.get(o)) for o in options]

  result = {o: None for o, _ in parsers}

  def Insert(key, val, word):
    if result[key] is not None:
      raise DuplicatedControl(option, word)
    result[key] = val

  error = None
  for word in controls.split():
    for option, parser in parsers:
      try:
        Insert(option, parser(word), word)
      except vroom.ParseError as e:
        error = e
      else:
        break
    else:
      raise error

  return result


class UnrecognizedWord(vroom.ParseError):
  """Raised when a control word is not recognized."""

  def __init__(self, word):
    msg = 'Unrecognized control word "%s"' % word
    super(UnrecognizedWord, self).__init__(msg)


class DuplicatedControl(vroom.ParseError):
  """Raised when a control word is duplicated."""

  def __init__(self, option, word):
    msg = 'Duplicated %s control "%s"' % (option, word)
    super(DuplicatedControl, self).__init__(msg)

########NEW FILE########
__FILENAME__ = environment
"""A vroom test execution environment.

This is an object with all of the vroom verifiers asked. Good for one file.
"""
import vroom.buffer
import vroom.messages
import vroom.output
import vroom.shell
import vroom.vim


class Environment(object):
  """The environment object.

  Sets up all the verifiers and managers and communicators you'll ever need.
  """

  def __init__(self, filename, args):
    self.args = args
    self.message_strictness = args.message_strictness
    self.system_strictness = args.system_strictness
    self.filename = filename
    self.writer = vroom.output.Writer(filename, args)
    self.shell = vroom.shell.Communicator(filename, self, self.writer)
    self.vim = vroom.vim.Communicator(args, self.shell.env, self.writer)
    self.buffer = vroom.buffer.Manager(self.vim)
    self.messenger = vroom.messages.Messenger(self.vim, self, self.writer)

########NEW FILE########
__FILENAME__ = messages
"""A module to keep track of vim messages."""

import re

import vroom
import vroom.controls
import vroom.test

# Pylint is not smart enough to notice that all the exceptions here inherit from
# vroom.test.Failure, which is a standard Exception.
# pylint: disable-msg=nonstandard-exception


ERROR_GUESS = re.compile(
    r'^(E\d+\b|ERR(OR)?\b|Error detected while processing .*)')
STRICTNESS = vroom.Specification(
    STRICT='STRICT',
    RELAXED='RELAXED',
    ERRORS='GUESS-ERRORS')
DEFAULT_MODE = vroom.controls.MODE.VERBATIM


def GuessNewMessages(old, new):
  """Guess which messages in a message list are new.

  >>> GuessNewMessages([1, 2, 3, 4], [1, 2, 3, 4, 5, 6, 7])
  [5, 6, 7]
  >>> GuessNewMessages([1, 2, 3, 4], [4, 5, 6, 7])
  [5, 6, 7]
  >>> GuessNewMessages([1, 2, 3, 4], [5, 6, 7])
  [5, 6, 7]
  >>> GuessNewMessages([1, 2, 3, 4], [4, 1, 2, 3])
  [1, 2, 3]

  Args:
    old: The old message list.
    new: The new message list.
  Returns:
    The new messages. Probably.
  """
  # This is made complicated by the fact that vim can drop messages, sometimes
  # after as few as 20 messages. When that's the case we have to guess a bit.
  # Technically, it's always possible to miss exactly [MESSAGE_MAX] messages
  # if you echo them out in a perfect cycle in one command. So it goes.
  # Message lists are straight from vim, so oldest is first.
  for i in range(len(old)):
    if old[i:] == new[:len(old) - i]:
      return new[len(old) - i:]
  return new[:]


def StartsWithBuiltinMessages(messages):
  """Whether the message list starts with the vim built in messages."""
  return len(messages) >= 2 and not messages[0] and messages[1] == (
      'Messages maintainer: Bram Moolenaar <Bram@vim.org>')


def StripBuiltinMessages(messages):
  """Strips the builtin messages."""
  assert len(messages) >= 2
  return messages[2:]


class Messenger(object):
  """Keeps an eye on vim, watching out for unexpected/error-like messages."""

  def __init__(self, vim, env, writer):
    """Creates the messenger.

    Args:
      vim: The vim handler.
      env: The vroom Environment object.
      writer: A place to log messages.
    """
    self.vim = vim
    self.env = env
    self.writer = writer.messages

  def Verify(self, old, new, expectations):
    """Verifies that the message state is OK.

    Args:
      old: What the messages were before the command.
      new: What the messages were after the command.
      expectations: What the command was supposed to message about.
    Raises:
      vroom.test.Failures: If an message-related failures were detected.
    """
    if StartsWithBuiltinMessages(old) and StartsWithBuiltinMessages(new):
      old = StripBuiltinMessages(old)
      new = StripBuiltinMessages(new)
    unread = GuessNewMessages(old, new)
    failures = []
    for message in unread:
      self.writer.Log(vroom.test.Received(message))
    for (desired, mode) in expectations:
      mode = mode or DEFAULT_MODE
      while True:
        try:
          message = unread.pop(0)
        except IndexError:
          expectation = '"%s" (%s mode)' % (desired, mode)
          failures.append(
              MessageNotReceived(expectation, new, self.vim.writer.Logs()))
          break
        if vroom.test.Matches(desired, mode, message):
          self.writer.Log(vroom.test.Matched(desired, mode))
          break
        try:
          self.Unexpected(message, new)
        except MessageFailure as e:
          failures.append(e)
    for remaining in unread:
      try:
        self.Unexpected(remaining, new)
      except MessageFailure as e:
        failures.append(e)

    if failures:
      raise vroom.test.Failures(failures)

  def Unexpected(self, message, new):
    """Handles an unexpected message."""
    self.writer.Log(vroom.test.Unexpected())
    if self.env.message_strictness == STRICTNESS.STRICT:
      raise UnexpectedMessage(message, new, self.vim.writer.Logs())
    elif self.env.message_strictness == STRICTNESS.ERRORS:
      if ERROR_GUESS.match(message):
        raise SuspectedError(message, new, self.vim.writer.Logs())


class MessageFailure(vroom.test.Failure):
  """For generic messaging troubles."""
  DESCRIPTION = 'Messaging failure.'
  CONTEXT = 12

  def __init__(self, message, messages, commands=None):
    self.messages = messages[-self.CONTEXT:]
    if commands:
      self.commands = commands[-self.CONTEXT:]
    msg = self.DESCRIPTION % {'message': message}
    super(MessageFailure, self).__init__(msg)


class MessageNotReceived(MessageFailure):
  """For when an expected message is never messaged."""
  DESCRIPTION = 'Expected message not received:\n%(message)s'


class UnexpectedMessage(MessageFailure):
  """For when an unexpected message is found."""
  DESCRIPTION = 'Unexpected message:\n%(message)s'


class SuspectedError(MessageFailure):
  """For when a message that looks like an error is found."""
  DESCRIPTION = 'Suspected error message:\n%(message)s'

########NEW FILE########
__FILENAME__ = output
"""Vroom output manager. It's harder than it looks."""
import sys
import traceback

import vroom
import vroom.buffer
import vroom.color
import vroom.controls
import vroom.messages
import vroom.shell
import vroom.test
import vroom.vim

# In lots of places in this file we use the name 'file' to mean 'a file'.
# We do this so that Logger.Print can have an interface consistent with
# python3's print.
# pylint: disable-msg=redefined-builtin


STATUS = vroom.Specification(
    PASS='PASS',
    ERROR='ERROR',
    FAIL='FAIL')


COLORS = {
    STATUS.PASS: vroom.color.GREEN,
    STATUS.ERROR: vroom.color.YELLOW,
    STATUS.FAIL: vroom.color.RED,
}


class Writer(object):
  """An output writer for a single vroom test file."""

  def __init__(self, filename, args):
    """Creatse the writer.

    Args:
      filename: The file to be tested.
      args: The command line arguments.
    """
    self.messages = MessageLogger(args.dump_messages, args.verbose, args.color)
    self.commands = CommandLogger(args.dump_commands, args.verbose, args.color)
    self.syscalls = SyscallLogger(args.dump_syscalls, args.verbose, args.color)
    self.actions = ActionLogger(args.out, args.verbose, args.color)
    self._filename = filename

  def Begin(self, lines):
    """Begins testing the file.

    Args:
      lines: The lines of the file.
    """
    self.actions.Open(lines)

  def Write(self, file=None):
    """Writes output for the file.

    Must be done after all tests are completed, because stdout will be used to
    run vim during the duration of the tests.

    Args:
      file: An alternate file handle to write to. Default None.
    """
    self.actions.Print(self._filename, color=(
        vroom.color.BOLD, vroom.color.TEAL), file=file)
    self.actions.Print('', verbose=True, file=file)
    self.actions.Write(self._filename, file=file)
    extra = self.messages.Write(self._filename, file=file)
    extra = self.commands.Write(self._filename, file=file) or extra
    extra = self.syscalls.Write(self._filename, file=file) or extra
    self.actions.Print('', file=file, verbose=None if extra else True)
    stats = self.Stats()
    plural = '' if stats['total'] == 1 else 's'
    self.actions.Print('Ran %d test%s in %s.' % (
        stats['total'], plural, self._filename), end=' ')
    self.actions.PutStat(stats, STATUS.PASS, '%d passing', file=file)
    self.actions.PutStat(stats, STATUS.ERROR, '%d errored', file=file)
    self.actions.PutStat(stats, STATUS.FAIL, '%d failed', file=file, end='.\n')
    if stats['total'] == 0:
      self.actions.Print(
          'WARNING', color=vroom.color.YELLOW, file=file, end=': ')
      self.actions.Print('NO TESTS RUN', file=file)

  def Stats(self):
    """Statistics on this test. Should be called after the test has completed.

    Returns:
      A dict containing STATUS fields.
    """
    if not hasattr(self, '_stats'):
      stats = self.actions.Results()
      stats['total'] = (
          stats[STATUS.PASS] + stats[STATUS.ERROR] + stats[STATUS.FAIL])
      self._stats = stats
    return self._stats

  def Status(self):
    """Returns the status of this test.

    Returns:
      PASS for Passed.
      ERROR for Errored (no failures).
      FAIL for Failure.
    """
    stats = self.Stats()
    if stats[STATUS.FAIL]:
      return STATUS.FAIL
    elif stats[STATUS.ERROR]:
      return STATUS.ERROR
    return STATUS.PASS


class Logger(object):
  """Generic writer sublogger.

  We can't use one logger because sometimes we have different writing components
  (system logs, message logs, command logs) that are all writing interleavedly
  but which should output in separate blocks. These Loggers handle one of those
  separate blocks.

  Thus, it must queue all messages and write them all at once at the end.
  """
  HEADER = None
  EMPTY = None

  def __init__(self, file, verbose, color):
    """Creates the logger.

    Args:
      file: The file to log to.
      verbose: Whether or not to write verbosely.
      color: A function used to color text.
    """
    self._verbose = verbose
    self._color = color
    self._file = file
    self._queue = []

  def Log(self, message):
    """Records a message.

    Args:
      message: The message to record.
    """
    self._queue.append(message)

  def Logs(self):
    """The currently recorded messages.

    Mostly used when exceptions try to
    figure out why they happened.

    Returns:
      A list of messages.
    """
    return self._queue

  def Print(self, message, verbose=None, color=None, end='\n', file=None):
    """Prints a message to the file.

    Args:
      message: The message to print.
      verbose: When verbose is not None, message is only printed if verbose is
          the same as --verbose.
      color: vroom.color escape code (or a tuple of the same) to color the
          message with.
      end: The line-end (use '' to suppress the default newline).
      file: Alternate file handle to use.
    """
    handle = file or self._file
    if (verbose is None) or (verbose == self._verbose):
      if handle == sys.stdout and color is not None:
        if not isinstance(color, tuple):
          color = (color,)
        message = self._color(message, *color)
      handle.write(message + end)

  def Write(self, filename, file=None):
    """Writes all messages.

    Args:
      filename: Vroom file that was tested, for use in the header.
      file: An alternate file to write to. Will only redirect to the
          alternate file if it was going to write to a file in the first place.
    Returns:
      Whether or not output was written.
    """
    if self._file is None:
      return False
    file = file or self._file
    lines = list(self.Finalize(self._queue))
    self.Print('', file=file)
    if lines:
      if self.HEADER:
        header = self.HEADER % {'filename': filename}
        self.Print(header, end=':\n', file=file)
      for line in lines:
        self.Print(line.rstrip('\n'), file=file)
    elif self.EMPTY:
      empty = self.EMPTY % {'filename': filename}
      self.Print(empty, end='.\n', file=file)
    return True

  def Finalize(self, queue):
    """Used to pre-process all messages after the the test and before display.

    Args:
      queue: The message queue
    Returns:
      The modified message queue.
    """
    return PrefixWithIndex(queue)


class MessageLogger(Logger):
  """A logger for vim messages."""

  HEADER = 'Vim messages during %(filename)s'
  EMPTY = 'There were no vim messages during %(filename)s'


class CommandLogger(Logger):
  """A logger for vim commands."""

  HEADER = 'Commands sent to vim during %(filename)s'
  EMPTY = 'No commands were sent to vim during %(filename)s'


class SyscallLogger(Logger):
  """A logger for vim system commands & calls."""

  HEADER = 'System call log during %(filename)s'
  EMPTY = 'No syscalls made by vim during %(filename)s'

  def Finalize(self, queue):
    return map(str, queue)


class ActionLogger(Logger):
  """A logger for the main test output.

  Prints the test file in verbose mode. Prints minimal pass/failure information
  otherwise.
  """

  def __init__(self, *args, **kwargs):
    self._opened = False
    super(ActionLogger, self).__init__(*args, **kwargs)

  def Open(self, lines):
    """Opens the action logger for a specific vroom file.

    Must be called before logging can begin.

    Args:
      lines: The file's lines.
    """
    self._lines = lines
    self._nextline = 0
    self._passed = 0
    self._errored = 0
    self._failed = 0
    self._opened = True

  def Write(self, filename, file=None):
    """Writes the test output. Should be called after vim has shut down.

    Args:
      filename: Used in the header.
      file: Alt file to redirect output to. Output will only be redirected
          if it was going to be output in the first place.
    Raises:
      NoTestRunning: if called too soon.
    """
    if not self._opened:
      raise NoTestRunning
    self.ExecutedUpTo(len(self._lines) - 1)
    for (line, args, kwargs) in self._queue:
      self.Print(line, *args, file=file, **kwargs)

  def PutStat(self, stats, stat, fmt, **kwargs):
    """Writes a stat to output.

    Will color the stat if the stat is non-zero and the output file is stdout.

    Args:
      stats: A dict with all the stats.
      stat: The STATUS to check.
      fmt: What to say about the stat.
      **kwargs: Passed on to print.
    """
    assert stat in stats and stat in COLORS
    num = stats[stat]
    kwargs.setdefault('end', ', ')
    if num:
      kwargs['color'] = COLORS[stat]
    self.Print(fmt % num, **kwargs)

  def Queue(self, message, *args, **kwargs):
    """Queues a single line for writing to the output file.

    Args:
      message: Will eventually be written.
      *args: Will be passed to Print.
      **kwargs: Will be passed to Print.
    """
    self._queue.append((message, args, kwargs))

  def Log(self, result, lineno, error=None):
    """Logs a test result.

    Args:
      result: The vroom.test.RESULT
      lineno: The line where the error occured.
      error: The exception if vroom.test.isBad(result)
    Raises:
      NoTestRunning: if called too soon.
    """
    self.Tally(result)
    self.ExecutedUpTo(lineno)
    if error is not None:
      self._Error(result, error, lineno)

  def Tally(self, result):
    """Tallies the result.

    Args:
      result: A vroom.test.result
    """
    if result == vroom.test.RESULT.PASSED:
      self._passed += 1
    if result == vroom.test.RESULT.ERROR:
      self._errored += 1
    if result == vroom.test.RESULT.FAILED:
      self._failed += 1

  def ExecutedUpTo(self, lineno):
    """Print output put to a given line number.

    This really only matters in --verbose mode where the file is printed as the
    tests run.

    Args:
      lineno: The line to print up to.
    """
    if self._verbose:
      for i, line in enumerate(self._lines[self._nextline:lineno + 1]):
        number = self.Lineno(self._nextline + i)
        self.Queue('%s %s' % (number, line.rstrip('\n')))
    self._nextline = lineno + 1

  def Lineno(self, lineno):
    """The string version of a line number, zero-padded as appropriate.

    Args:
      lineno: The line number
    Returns:
      The zero-padded string.
    """
    numberifier = '%%0%dd' % len(str(len(self._lines)))
    return numberifier % (lineno + 1)

  def Error(self, result, error):
    """Logs an error that didn't occur at a specific line.

    (Vim didn't start, etc.)

    Args:
      result: The vroom.test.RESULT.
      error: The exception.
    """
    self.Tally(result)
    self._Error(result, error)

  def _Error(self, result, error, lineno=None):
    """Prints an error message. Used by both Log and Error on bad results.

    Args:
      result: The vroom.test.RESULT.
      error: The execption.
      lineno: The place that the error occured, if known.
    """
    self.Queue('------------------------------------------------', verbose=True)
    if result == vroom.test.RESULT.ERROR:
      self.Queue(result.upper(), color=COLORS[STATUS.ERROR], end='')
    else:
      self.Queue(result.upper(), color=COLORS[STATUS.FAIL], end='')
    if lineno is not None:
      self.Queue(' on line %s' % self.Lineno(lineno), verbose=False, end='')
    self.Queue(': ', end='')
    self.Queue(str(error))
    # Print extra context about the error.
    # Python isinstance is freeking pathological: isinstance(foo, Foo) can
    # change depending upon how you import Foo.  Instead of dealing with that
    # mess, we ducktype exceptions.
    # Also, python can't do real closures, which is why contexted is a list.
    contexted = [False]

    def QueueContext(attr, writer, *args):
      value = None
      if hasattr(error, attr):
        value = getattr(error, attr)
      elif hasattr(error, 'GetFlattenedFailures'):
        for f in error.GetFlattenedFailures():
          if hasattr(f, attr):
            value = getattr(f, attr)
            break
      if value is None:
        return
      contexted[0] = True
      self.Queue('')
      writer(value, self.Queue, *args)

    QueueContext('messages', ErrorMessageContext)
    QueueContext('context', ErrorBufferContext)

    if lineno is not None:
      stripped = self._lines[lineno][2:]
      line = '\nFailed command on line %s:\n%s' % (
          self.Lineno(lineno), stripped)
      self.Queue(line, end='', verbose=False)

    QueueContext('expectations', ErrorShellQueue)
    QueueContext('syscalls', ErrorSystemCalls)
    QueueContext('commands', ErrorCommandContext)

    if contexted[0]:
      self.Queue('', verbose=False)
    self.Queue('------------------------------------------------', verbose=True)

  def Results(self):
    """The test results.

    Returns:
      A dict containing STATUS.PASS, STATUS.ERROR, and STATUS.FAIL.
    """
    return {
        STATUS.PASS: self._passed,
        STATUS.ERROR: self._errored,
        STATUS.FAIL: self._failed,
    }

  def Exception(self, exctype, exception, tb):
    """Prints out an unexpected exception with stack info.

    Should only be used when vroom encounters an error in its own programming.
    We don't ever want real users to see these.

    Args:
      exctype: The exception type.
      exception: The exception.
      tb: The traceback.
    """
    self.Tally(vroom.test.RESULT.ERROR)
    self.Queue('------------------------------------------------', verbose=True)
    self.Queue('')
    self.Queue('ERROR', color=COLORS[STATUS.ERROR], end='')
    self.Queue(': ', end='')
    self.Queue(''.join(traceback.format_exception(exctype, exception, tb)))
    self.Queue('')
    if hasattr(exception, 'shell_errors'):
      ErrorShellErrors(exception.shell_errors, self.Queue)
      self.Queue('')
    self.Queue('------------------------------------------------', verbose=True)


def WriteBackmatter(writers, args):
  """Writes the backmatter (# tests run, etc.) for a group of writers.

  Args:
    writers: The writers
    args: The command line args.
  """
  if len(writers) == 1:
    # No need to summarize, we'd be repeating ourselves.
    return
  count = 0
  total = 0
  passed = 0
  errored = 0
  args.out.write(args.color('\nVr', vroom.color.VIOLET))
  for writer in writers:
    count += 1
    total += writer.Stats()['total']
    status = writer.Status()
    if status == STATUS.PASS:
      passed += 1
    elif status == STATUS.ERROR:
      errored += 1
    args.out.write(args.color('o', COLORS[status]))
  args.out.write(args.color('m\n', vroom.color.VIOLET))
  plural = '' if total == 1 else 's'
  args.out.write('Ran %d test%s in %d files. ' % (total, plural, count))
  if passed == count:
    args.out.write('Everything is ')
    args.out.write(args.color('OK', COLORS[STATUS.PASS]))
    args.out.write('.')
  else:
    args.out.write(args.color('%d passed' % passed, COLORS[STATUS.PASS]))
    args.out.write(', ')
    args.out.write(args.color('%d errored' % errored, COLORS[STATUS.ERROR]))
    args.out.write(', ')
    failed = count - passed - errored
    args.out.write(args.color('%d failed' % failed, COLORS[STATUS.FAIL]))
  args.out.write('\n')


def PrefixWithIndex(logs):
  """Prefixes a bunch of lines with their index.

  Indicies are zero-padded so that everything aligns nicely.
  If there's a None log it's skipped and a linebreak is output.
  Trailing None logs are ignored.

  >>> list(PrefixWithIndex(['a', 'a']))
  ['1\\ta', '2\\ta']
  >>> list(PrefixWithIndex(['a' for _ in range(10)]))[:2]
  ['01\\ta', '02\\ta']
  >>> list(PrefixWithIndex(['a', None, 'a']))
  ['1\\ta', '', '2\\ta']

  Args:
    logs: The lines to index.
  Yields:
    The indexed lines.
  """
  # Makes sure we don't accidentally modify the real logs.
  # Also, makes the code not break if someone passes us a generator.
  logs = list(logs)
  while logs and logs[-1] is None:
    logs.pop()
  # Gods, I love this line. It creates a formatter that pads a number out to
  # match the largest number necessary to index all the non-null lines in logs.
  numberifier = '%%0%dd' % len(str(len(list(filter(bool, logs)))))
  adjustment = 0
  for (i, log) in enumerate(logs):
    if log is None:
      adjustment += 1
      yield ''
    else:
      index = numberifier % (i + 1 - adjustment)
      yield '%s\t%s' % (index, log)


def ErrorContextPrinter(header, empty, modifier=None, singleton=None):
  """Creates a function that prints extra error data.

  Args:
    header: What to print before the data.
    empty: What to print when there's no data.
    modifier: Optional, run on all the data before printing.
    singleton: Optional, what to print when there's only one datum.
  Returns:
    Function that takes (data, printer) and prints the data using the printer.
  """

  def WriteExtraData(data, printer):
    data = list(modifier(data) if modifier else data)
    if data:
      if not singleton or len(data) > 1:
        printer(header, end=':\n')
        for datum in data:
          if datum is None:
            printer('')
          else:
            printer(str(datum))
      else:
        printer(singleton % data[0])
    else:
      printer(empty)

  return WriteExtraData


# Pylint isn't smart enough to notice that these are all generated funtions.
ErrorMessageContext = ErrorContextPrinter(  # pylint: disable-msg=g-bad-name
    'Messages',
    'There were no messages.',
    modifier=None,
    singleton='Message was "%s"')

ErrorCommandContext = ErrorContextPrinter(  # pylint: disable-msg=g-bad-name
    'Last few commands (most recent last) were',
    'No relevant commands found.')

ErrorSystemCalls = ErrorContextPrinter(  # pylint: disable-msg=g-bad-name
    'Recent system logs are',
    'No system calls received. Perhaps your --shell is broken?')

ErrorShellQueue = ErrorContextPrinter(  # pylint: disable-msg=g-bad-name
    'Queued system controls are',
    'No system commands expected.')

ErrorShellErrors = ErrorContextPrinter(  # pylint: disable-msg=g-bad-name
    'Shell error list',
    'Shell had no chance to log errors.',
    modifier=PrefixWithIndex)


def ErrorBufferContext(context, printer):
  """Prints the buffer data relevant to an error.

  Args:
    context: The buffer context.
    printer: A function to do the printing.
  """
  if context is None:
    printer('No vim buffer was loaded.')
    return

  # Find out what buffer we're printing from.
  if context['buffer'] is None:
    printer('Checking the current buffer.', end='', verbose=True)
  else:
    printer('Checking buffer %s.' % context['buffer'], end='', verbose=True)
  printer(' Relevant buffer data:', verbose=True)
  printer('Found:', verbose=False)

  # Print the relevant buffer lines
  (start, end) = (context['start'], context['end'])
  # Empty buffer.
  if not context['data']:
    printer('An empty buffer.')
    return

  buflines = list(PrefixWithIndex(context['data']))
  # They're looking at a specific line.
  if end > start:
    for i, bufline in enumerate(buflines[start:end]):
      if context['line'] == i + start:
        printer(bufline + ' <<<<', color=vroom.color.BOLD)
      else:
        printer(bufline)
  # They're looking at the whole buffer.
  else:
    for bufline in buflines:
      printer(bufline)


class NoTestRunning(ValueError):
  """Raised when a logger is asked to log before the test begins."""

  def __init__(self):
    """Creates the exception."""
    super(NoTestRunning, self).__init__(
        'Please run a vroom test before outputting results.')

########NEW FILE########
__FILENAME__ = runner
"""The Vroom test runner. Does the heavy lifting."""
import sys

import vroom
import vroom.actions
import vroom.args
import vroom.buffer
import vroom.command
import vroom.environment
import vroom.output
import vroom.shell
import vroom.test
import vroom.vim

# Pylint is not smart enough to notice that all the exceptions here inherit from
# vroom.test.Failure, which is a standard Exception.
# pylint: disable-msg=nonstandard-exception


class Vroom(object):
  """Executes vroom tests."""

  def __init__(self, filename, args):
    """Creates the vroom test.

    Args:
      filename: The name of the file to execute.
      args: The vroom command line flags.
    """
    self._message_strictness = args.message_strictness
    self._system_strictness = args.system_strictness
    self._lineno = None
    # Whether this vroom instance has left the terminal in an unknown state.
    self.dirty = False
    self.env = vroom.environment.Environment(filename, args)
    self.ResetCommands()

  def ResetCommands(self):
    self._running_command = None
    self._command_queue = []

  def GetCommand(self):
    if not self._command_queue:
      self.PushCommand(None, None)
    return self._command_queue[-1]

  def PushCommand(self, line, delay=None):
    self._command_queue.append(
        vroom.command.Command(line, self._lineno, delay or 0, self.env))

  def ExecuteCommands(self):
    if not self._command_queue:
      return
    self.env.buffer.Unload()
    for self._running_command in self._command_queue:
      self._running_command.Execute()
    self.ResetCommands()

  def __call__(self, filehandle):
    """Runs vroom on a file.

    Args:
      filehandle: The open file to run on.
    Returns:
      A writer to write the test output later.
    """
    lines = list(filehandle)
    try:
      self.env.writer.Begin(lines)
      self.env.vim.Start()
      self.Run(lines)
    except vroom.ParseError as e:
      self.Record(vroom.test.RESULT.ERROR, e)
    except vroom.test.Failure as e:
      self.Record(vroom.test.RESULT.FAILED, e)
    except vroom.vim.Quit as e:
      # TODO(dbarnett): Revisit this when terminal reset is no longer necessary.
      if e.is_fatal:
        raise
      self.Record(vroom.test.RESULT.ERROR, e)
    except Exception:
      self.env.writer.actions.Exception(*sys.exc_info())
    finally:
      if not self.env.args.interactive:
        if not self.env.vim.Quit():
          self.dirty = True
          self.env.vim.Kill()
    status = self.env.writer.Status()
    if status != vroom.output.STATUS.PASS and self.env.args.interactive:
      self.env.vim.Output(self.env.writer)
      self.env.vim.process.wait()
    return self.env.writer

  def Record(self, result, error=None):
    """Add context to an error and log it.

    The current line number is added to the context when possible.

    Args:
      result: The log type, should be a member of vroom.test.RESULT
      error: The exception, if any.
    """
    # Figure out the line where the event happened.
    if self._running_command and self._running_command.lineno is not None:
      lineno = self._running_command.lineno
    elif self._lineno is not None:
      lineno = self._lineno
    else:
      lineno = getattr(error, 'lineno', None)
    if lineno is not None:
      self.env.writer.actions.Log(result, lineno, error)
    else:
      self.env.writer.actions.Error(result, error)

  def Test(self, function, *args, **kwargs):
    self.ExecuteCommands()
    function(*args, **kwargs)

  def Run(self, lines):
    """Runs a vroom file.

    Args:
      lines: List of lines in the file.
    """
    actions = list(vroom.actions.Parse(lines))
    for (self._lineno, action, line, controls) in actions:
      if action == vroom.actions.ACTION.PASS:
        # Line breaks send you back to the top of the buffer.
        self.env.buffer.Unload()
        # Line breaks distinguish between consecutive system hijacks.
        self.GetCommand().LineBreak()
      elif action == vroom.actions.ACTION.TEXT:
        self.PushCommand('i%s<ESC>' % line, **controls)
      elif action == vroom.actions.ACTION.COMMAND:
        self.PushCommand(':%s<CR>' % line, **controls)
      elif action == vroom.actions.ACTION.INPUT:
        self.PushCommand(line, **controls)
      elif action == vroom.actions.ACTION.MESSAGE:
        self.GetCommand().ExpectMessage(line, **controls)
      elif action == vroom.actions.ACTION.SYSTEM:
        self.GetCommand().ExpectSyscall(line, **controls)
      elif action == vroom.actions.ACTION.HIJACK:
        self.GetCommand().RespondToSyscall(line, **controls)
      elif action == vroom.actions.ACTION.DIRECTIVE:
        if line == vroom.actions.DIRECTIVE.CLEAR:
          self.ExecuteCommands()
          self.env.writer.actions.Log(vroom.test.RESULT.PASSED, self._lineno)
          self.env.vim.Clear()
        elif line == vroom.actions.DIRECTIVE.END:
          self.Test(self.env.buffer.EnsureAtEnd, **controls)
        elif line == vroom.actions.DIRECTIVE.MESSAGES:
          self.ExecuteCommands()
          strictness = controls.get('messages') or self._message_strictness
          self.env.message_strictness = strictness
        elif line == vroom.actions.DIRECTIVE.SYSTEM:
          self.ExecuteCommands()
          strictness = controls.get('system') or self._system_strictness
          self.env.system_strictness = strictness
        else:
          raise vroom.ConfigurationError('Unrecognized directive "%s"' % line)
      elif action == vroom.actions.ACTION.OUTPUT:
        self.Test(self.env.buffer.Verify, line, **controls)
      else:
        raise vroom.ConfigurationError('Unrecognized action "%s"' % action)
    self.ExecuteCommands()
    self.env.writer.actions.Log(vroom.test.RESULT.PASSED, self._lineno or 0)
    self.env.vim.Quit()

########NEW FILE########
__FILENAME__ = shell
"""Vroom fake shell bridge."""
import json
import os
import os.path
import pickle
import pipes
import re
import tempfile

import vroom
import vroom.controls
import vroom.test

# Pylint is not smart enough to notice that all the exceptions here inherit from
# vroom.test.Failure, which is a standard Exception.
# pylint: disable-msg=nonstandard-exception

VROOMFILE_VAR = 'VROOMFILE'
VROOMDIR_VAR = 'VROOMDIR'
LOG_FILENAME_VAR = 'VROOM_SHELL_LOGFILE'
CONTROL_FILENAME_VAR = 'VROOM_SHELL_CONTROLLFILE'
ERROR_FILENAME_VAR = 'VROOM_SHELL_ERRORFILE'

CONTROL = vroom.Specification(
    EXPECT='expect',
    RESPOND='respond')

STRICTNESS = vroom.Specification(
    STRICT='STRICT',
    RELAXED='RELAXED')

OUTCHANNEL = vroom.Specification(
    COMMAND='command',
    STDOUT='stdout',
    STDERR='stderr',
    STATUS='status')

DEFAULT_MODE = vroom.controls.MODE.REGEX


def Load(filename):
  """Loads a shell file into python space.

  Args:
    filename: The shell file to load.
  Returns:
    The file contents.
  Raises:
    FakeShellNotWorking
  """
  try:
    with open(filename, 'rb') as f:
      return pickle.load(f)
  except IOError:
    raise FakeShellNotWorking


def Send(filename, data):
  """Sends python data to a shell file.

  Args:
    filename: The shell file to send to.
    data: The python data to send.
  """
  with open(filename, 'wb') as f:
    pickle.dump(data, f)


class Communicator(object):
  """Object to communicate with the fake shell."""

  def __init__(self, filename, env, writer):
    self.vroom_env = env
    self.writer = writer.syscalls
    self.commands_writer = writer.commands

    _, self.control_filename = tempfile.mkstemp()
    _, self.log_filename = tempfile.mkstemp()
    _, self.error_filename = tempfile.mkstemp()
    Send(self.control_filename, [])
    Send(self.log_filename, [])
    Send(self.error_filename, [])

    self.env = os.environ.copy()
    self.env[VROOMFILE_VAR] = filename
    self.env[VROOMDIR_VAR] = os.path.dirname(filename) or '.'
    self.env[vroom.shell.LOG_FILENAME_VAR] = self.log_filename
    self.env[vroom.shell.CONTROL_FILENAME_VAR] = self.control_filename
    self.env[vroom.shell.ERROR_FILENAME_VAR] = self.error_filename

    self._copied_logs = 0

  def Control(self, hijacks):
    """Tell the shell the system control specifications."""
    existing = Load(self.control_filename)
    Send(self.control_filename, existing + hijacks)

  def Verify(self):
    """Checks that system output was caught and handled satisfactorily.

    Raises:
      FakeShellNotWorking: If it can't load the shell file.
      vroom.test.Failures: If there are other failures.
    """
    # Copy any new logs into the logger.
    logs = Load(self.log_filename)
    for log in logs[self._copied_logs:]:
      self.writer.Log(log)
    self._copied_logs = len(logs)

    failures = []

    # Check for shell errors.
    errors = Load(self.error_filename)
    if errors:
      failures.append(FakeShellNotWorking(errors))

    commands_logs = self.commands_writer.Logs()

    # Check that all controls have been handled.
    controls = Load(self.control_filename)
    if controls:
      Send(self.control_filename, [])
      missed = controls[0]
      if missed.expectation:
        failures.append(SystemNotCalled(logs, controls, commands_logs))
      failures.append(NoChanceForResponse(
          logs, missed, commands_logs))

    # Check for unexpected calls, if they user is into that.
    if self.vroom_env.system_strictness == STRICTNESS.STRICT:
      logs = self.writer.Logs()
      if [log for log in logs if log.TYPE == vroom.test.LOG.UNEXPECTED]:
        failures.append(UnexpectedSystemCalls(logs, commands_logs))

    if failures:
      raise vroom.test.Failures(failures)


class Hijack(object):
  """An object used to tell the fake shell what to do about system calls.

  It can contain a single expectation (of a system call) and any number of
  responses (text to return when the expected call is seen).

  If no expectation is given, it will match any command.
  If no responses are given, the command will be allowed through the fake shell.

  The Hijack can be 'Open' or 'Closed': we need a way to distinguish
  between this:

    $ One
    $ Two

  and this:

    $ One

    $ Two

  The former responds "One\\nTwo" to any command. The latter responds "One" to
  the first command, whatever it may be, and then "Two" to the next command.

  The solution is that line breaks "Close" an expectation. In this way, we can
  tell if a new respones should be part of the previous expectation or part of
  a new one.
  """

  def __init__(self, fakecmd, expectation=None, mode=None):
    self.closed = False
    self.fakecmd = fakecmd
    self.response = {}
    self.expectation = expectation
    self.mode = mode or DEFAULT_MODE

  def Response(self, command):
    """Returns the command that should be done in place of the true command.

    This will either be the original command or a call to respond.vroomfaker.

    Args:
      command: The vim-requested command.
    Returns:
      The user-specified command.
    """
    if self.expectation is not None:
      if not vroom.test.Matches(self.expectation, self.mode, command):
        return False

    # We don't want to do this on init because regexes don't repr() as nicely as
    # strings do.
    if self.expectation and self.mode == vroom.controls.MODE.REGEX:
      try:
        match_regex = re.compile(self.expectation)
      except re.error as e:
        raise vroom.ParseError("Can't match command. Invalid regex. %s'" % e)
    else:
      match_regex = re.compile(r'.*')

    # The actual response won't be exactly like the internal response, because
    # we've got to do some regex group binding magic.
    response = {}

    # Expand all of the responders that want to be bound to the regex.
    for channel in (
        OUTCHANNEL.COMMAND,
        OUTCHANNEL.STDOUT,
        OUTCHANNEL.STDERR):
      for line in self.response.get(channel, []):
        # We do an re.sub() regardless of whether the control was bound as
        # a regex: this forces you to escape consistently between all match
        # groups, which will help prevent your tests from breaking if you later
        # switch the command matching to regex from verbatim/glob.
        try:
          line = match_regex.sub(line, command)
        except re.error as e:
          # 'invalid group reference' is the expected message here.
          # Unfortunately the python re module doesn't differentiate its
          # exceptions well.
          if self.mode != vroom.controls.MODE.REGEX:
            raise vroom.ParseError(
                'Substitution error. '
                'Ensure that matchgroups (such as \\1) are escaped.')
          raise vroom.ParseError('Substitution error: %s.' % e)
        response.setdefault(channel, []).append(line)

    # The return status can't be regex-bound.
    if OUTCHANNEL.STATUS in self.response:
      response[OUTCHANNEL.STATUS] = self.response[OUTCHANNEL.STATUS]

    # If we actually want to do anything, call out to the responder.
    if response:
      return '%s %s' % (self.fakecmd, pipes.quote(json.dumps(response)))
    return command

  def Respond(self, line, channel=None):
    """Adds a response to this expectation.

    Args:
      line: The response to add.
      channel: The output channel to respond with 'line' in.
    """
    if channel is None:
      channel = OUTCHANNEL.STDOUT
    if channel == OUTCHANNEL.COMMAND:
      self.response.setdefault(OUTCHANNEL.COMMAND, []).append(line)
    elif channel == OUTCHANNEL.STDOUT:
      self.response.setdefault(OUTCHANNEL.STDOUT, []).append(line)
    elif channel == OUTCHANNEL.STDERR:
      self.response.setdefault(OUTCHANNEL.STDERR, []).append(line)
    elif channel == OUTCHANNEL.STATUS:
      if OUTCHANNEL.STATUS in self.response:
        raise vroom.ParseError('A system call cannot return two statuses!')
      try:
        status = int(line)
      except ValueError:
        raise vroom.ParseError('Returned status must be a number.')
      self.response[OUTCHANNEL.STATUS] = status
    else:
      assert False, 'Unrecognized output channel word.'

  def __repr__(self):
    return 'Hijack(%s, %s, %s)' % (self.expectation, self.mode, self.response)

  def __str__(self):
    out = ''
    # %07s pads things out to match  with "COMMAND:"
    if self.expectation is not None:
      out += ' EXPECT:\t%s (%s mode)\n' % (self.expectation, self.mode)
    rejoiner = '\n%07s\t' % ''
    if OUTCHANNEL.COMMAND in self.response:
      out += 'COMMAND:\t%s\n' % rejoiner.join(self.response[OUTCHANNEL.COMMAND])
    if OUTCHANNEL.STDOUT in self.response:
      out += ' STDOUT:\t%s\n' % rejoiner.join(self.response[OUTCHANNEL.STDOUT])
    if OUTCHANNEL.STDERR in self.response:
      out += ' STDERR:\t%s\n' % rejoiner.join(self.response[OUTCHANNEL.STDERR])
    if 'status' in self.response:
      out += ' STATUS:\t%s' % self.response['status']
    return out.rstrip('\n')


class FakeShellNotWorking(Exception):
  """Called when the fake shell is not working."""

  def __init__(self, errors):
    self.shell_errors = errors
    super(FakeShellNotWorking, self).__init__()

  def __str__(self):
    return 'The fake shell is not working as anticipated.'


class FakeShellFailure(vroom.test.Failure):
  """Generic fake shell error. Please raise its implementors."""
  DESCRIPTION = 'System failure'
  CONTEXT = 12

  def __init__(self, logs, commands, message=None):
    self.syscalls = logs[-self.CONTEXT:]
    self.commands = commands
    super(FakeShellFailure, self).__init__(message or self.DESCRIPTION)


class UnexpectedSystemCalls(FakeShellFailure):
  """Raised when a system call is made unexpectedly."""
  DESCRIPTION = 'Unexpected system call.'


class SystemNotCalled(FakeShellFailure):
  """Raised when an expected system call is not made."""
  DESCRIPTION = 'Expected system call not received.'

  def __init__(self, logs, expectations, commands):
    self.expectations = expectations
    super(SystemNotCalled, self).__init__(logs, commands)


class NoChanceForResponse(FakeShellFailure):
  """Raised when no system calls were made, but a response was specified."""
  DESCRIPTION = 'Got no chance to inject response: \n%s'

  def __init__(self, logs, response, commands):
    super(NoChanceForResponse, self).__init__(
        logs, commands, self.DESCRIPTION % response)

########NEW FILE########
__FILENAME__ = test
"""Vroom test utilities."""
import fnmatch
import re
import traceback

import vroom
import vroom.controls

RESULT = vroom.Specification(
    PASSED='passed',
    ERROR='error',
    FAILED='failed',
    SENT='sent')

LOG = vroom.Specification(
    RECEIVED='received',
    MATCHED='matched',
    RESPONDED='responded',
    UNEXPECTED='unexpected',
    ERROR='error')


def IsBad(result):
  """Whether or not a result is something to worry about.

  >>> IsBad(RESULT.PASSED)
  False
  >>> IsBad(RESULT.FAILED)
  True

  Args:
    result: The RESULT.
  Returns:
    Whether the result is bad.
  """
  return result in (RESULT.ERROR, RESULT.FAILED)


def Matches(request, mode, data):
  """Checks whether data matches the requested string under the given mode.

  >>> sentence = 'The quick brown fox jumped over the lazy dog.'
  >>> Matches(sentence, vroom.controls.MODE.VERBATIM, sentence)
  True
  >>> Matches('The * * fox * * the ???? *', vroom.controls.MODE.GLOB, sentence)
  True
  >>> Matches('The quick .*', vroom.controls.MODE.REGEX, sentence)
  True
  >>> Matches('Thy quick .*', vroom.controls.MODE.REGEX, sentence)
  False

  Args:
    request: The requested string (likely a line in a vroom file)
    mode: The match mode (regex|glob|verbatim)
    data: The data to verify
  Returns:
    Whether or not the data checks out.
  """
  if mode is None:
    mode = vroom.controls.DEFAULT_MODE
  if mode == vroom.controls.MODE.VERBATIM:
    return request == data
  elif mode == vroom.controls.MODE.GLOB:
    return fnmatch.fnmatch(data, request)
  else:
    return re.match(request + '$', data) is not None


class Failure(Exception):
  """Raised when a test fails."""


class Failures(Failure):
  """Raised when multiple Failures occur."""

  def __init__(self, failures):
    super(Failures, self).__init__()
    self.failures = failures

  def GetFlattenedFailures(self):
    flattened_failures = []
    for f in self.failures:
      if hasattr(f, 'GetFlattenedFailures'):
        flattened_failures.extend(f.GetFlattenedFailures())
      else:
        flattened_failures.append(f)
    return flattened_failures

  def __str__(self):
    flattened_failures = self.GetFlattenedFailures()
    if len(flattened_failures) == 1:
      return str(flattened_failures[0])
    assert len(flattened_failures) > 0
    return (
        'Multiple failures:\n' +
        '\n\n'.join(str(f) for f in flattened_failures))


class Log(object):
  """A generic log type."""
  TYPE_WIDTH = 10  # UNEXPECTED

  def __init__(self, message=''):
    self.message = message

  def __str__(self):
    # Makes every header be padded as much as the longest message.
    header = ('%%%ds' % self.TYPE_WIDTH) % self.TYPE.upper()
    leader = ('\n%%%ds ' % self.TYPE_WIDTH) % ''
    return ' '.join((header, leader.join(self.message.split('\n'))))


class Received(Log):
  """For received commands."""
  TYPE = LOG.RECEIVED


class Matched(Log):
  """For matched commands."""
  TYPE = LOG.MATCHED

  def __init__(self, line, mode):
    message = 'with "%s" (%s mode)' % (line, mode)
    super(Matched, self).__init__(message)


class Responded(Log):
  """For system responses."""
  TYPE = LOG.RESPONDED


class Unexpected(Log):
  """For unexpected entities."""
  TYPE = LOG.UNEXPECTED


class ErrorLog(Log):
  """For error logs."""
  TYPE = LOG.ERROR

  def __init__(self, extype, exval, tb):
    message = ''.join(traceback.format_exception(extype, exval, tb))
    super(ErrorLog, self).__init__(message)

########NEW FILE########
__FILENAME__ = vim
"""Vroom vim management."""
import json
# I'll make you a deal, pylint. I'll remove this if you upgrade to py3k.
# pylint: disable-msg=g-import-not-at-top
try:
  from StringIO import StringIO
except ImportError:
  from io import StringIO
import subprocess
import tempfile
import time


# Vroom has been written such that this data *could* go into a separate .vim
# file, and that would be great. However, python distutils (believe it or not)
# makes it extraordinarily tough to distribute custom files with your python
# modules. It's both difficult to know where they go and difficult to allow them
# to be read. If the user does a sudo install, distutils has no way to make the
# .vim file actually readable and vroom dies from permission errors.
# So screw you, python. I'll just hardcode it.
_, CONFIGFILE = tempfile.mkstemp()
with open(CONFIGFILE, 'w') as configfile:
  configfile.write("""
" Prevents your vroom tests from doing nasty things to your system.
set noswapfile

" Hidden function to execute a command and return the output.
" Useful for :messages
function! VroomExecute(command)
  redir => l:output
  silent! execute a:command
  redir end
  return l:output
endfunction

" Hidden function to reset a test.
function! VroomClear()
  stopinsert
  silent! bufdo! bdelete!
endfunction

" Hidden function to dump an error into vim.
function! VroomDie(output)
  let g:vroom_error = a:output
  let g:vroom_error .= "\\n:tabedit $VROOMFILE to edit the test file."
  let g:vroom_error .= "\\nThis output is saved in g:vroom_error."
  let g:vroom_error .= "\\nQuit vim when you're done."
  echo g:vroom_error
endfunction

" Hidden function to kill vim, independent of insert mode.
function! VroomEnd()
  qa!
endfunction
""")


class Communicator(object):
  """Object to communicate with a vim server."""

  def __init__(self, args, env, writer):
    self.writer = writer.commands
    self.args = args
    self.start_command = [
        'vim',
        '-u', args.vimrc,
        '--servername', args.servername,
        '-c', 'set shell=' + args.shell,
        '-c', 'source %s' % CONFIGFILE]
    self.env = env
    self._cache = {}

  def Start(self):
    """Starts vim."""
    if not self._IsCurrentDisplayUsable():
      # Try using explicit $DISPLAY value. This only affects vim's client/server
      # connections and not how console vim appears.
      original_display = self.env.get('DISPLAY')
      self.env['DISPLAY'] = ':0'
      if not self._IsCurrentDisplayUsable():
        # Restore original display value if ":0" doesn't work, either.
        if original_display is None:
          del self.env['DISPLAY']
        else:
          self.env['DISPLAY'] = original_display
      # TODO(dbarnett): Try all values from /tmp/.X11-unix/, etc.

    # We do this separately from __init__ so that if it fails, vroom.runner
    # still has a _vim attribute it can query for details.
    self.process = subprocess.Popen(self.start_command, env=self.env)
    time.sleep(self.args.startuptime)

  def _IsCurrentDisplayUsable(self):
    """Check whether vim fails using the current configured display."""
    try:
      self.Ask('1')
    except NoDisplay:
      return False
    except Quit:
      # Any other error means the display setting is fine (assuming vim didn't
      # fail before it checked the display).
      pass
    return True

  def Communicate(self, command, extra_delay=0):
    """Sends a command to vim & sleeps long enough for the command to happen.

    Args:
      command: The command to send.
      extra_delay: Delay in excess of --delay
    Raises:
      Quit: If vim quit unexpectedly.
    """
    self.writer.Log(command)
    self.TryToSay([
        'vim',
        '--servername', self.args.servername,
        '--remote-send', command])
    self._cache = {}
    time.sleep(self.args.delay + extra_delay)

  def Ask(self, expression):
    """Asks vim for the result of an expression.

    Args:
      expression: The expression to ask for.
    Returns:
      Vim's output (as a string).
    Raises:
      Quit: If vim quit unexpectedly.
    """
    try:
      return self.TryToSay([
          'vim',
          '--servername', self.args.servername,
          '--remote-expr', expression])
    except ErrorOnExit as e:
      if e.error_text.startswith('E449:'):  # Invalid expression received
        raise InvalidExpression(expression)
      raise

  def GetCurrentLine(self):
    """Figures out what line the cursor is on.

    Returns:
      The cursor's line.
    """
    if 'line' not in self._cache:
      lineno = self.Ask("line('.')")
      try:
        self._cache['line'] = int(lineno)
      except (ValueError, TypeError):
        raise ValueError("Vim lost the cursor, it thinks it's '%s'." % lineno)
    return self._cache['line']

  def GetBufferLines(self, number):
    """Gets the lines in the requesed buffer.

    Args:
      number: The buffer number to load. SHOULD NOT be a member of
          SpecialBuffer, use GetMessages if you want messages. Only works on
          real buffers.
    Returns:
      The buffer lines.
    """
    if number not in self._cache:
      num = "'%'" if number is None else number
      cmd = "getbufline(%s, 1, '$')" % num
      self._cache[number] = self.Ask(cmd).splitlines()
    return self._cache[number]

  def GetMessages(self):
    """Gets the vim message list.

    Returns:
      The message list.
    """
    # This prevents GetMessages() from being called twice in a row.
    # (When checking a (msg) output line, first we check the messages then we
    # load the buffer.) Cleans up --dump-commands a bit.
    if 'msg' not in self._cache:
      cmd = "VroomExecute('silent! messages')"
      self._cache['msg'] = self.Ask(cmd).splitlines()
    return self._cache['msg']

  def Clear(self):
    self.writer.Log(None)
    self.Ask('VroomClear()')
    self._cache = {}

  def Output(self, writer):
    """Send the writer output to the user."""
    if hasattr(self, 'process'):
      buf = StringIO()
      writer.Write(buf)
      self.Ask('VroomDie({})'.format(VimscriptString(buf.getvalue())))
      buf.close()

  def Quit(self):
    """Tries to cleanly quit the vim process.

    Returns:
      True if vim successfully quit or wasn't running, False otherwise.
    """
    # We might die before the process is even set up.
    if hasattr(self, 'process'):
      if self.process.poll() is None:
        # Evaluate our VroomEnd function as an expression instead of issuing a
        # command, which works even if vim isn't in normal mode.
        try:
          self.Ask('VroomEnd()')
        except Quit:
          # Probably failed to quit. If vim is still running, we'll return False
          # below.
          pass
      if self.process.poll() is None:
        return False
      else:
        del self.process
    return True

  def Kill(self):
    """Kills the vim process."""
    # We might die before the process is even set up.
    if hasattr(self, 'process'):
      if self.process.poll() is None:
        self.process.kill()
      del self.process

  def TryToSay(self, cmd):
    """Execute a given vim process.

    Args:
      cmd: The command to send.
    Returns:
      stdout from vim.
    Raises:
      Quit: If vim quits unexpectedly.
    """
    if hasattr(self, 'process') and self.process.poll() is not None:
      raise ServerQuit()

    # Override messages generated by the vim client process (in particular, the
    # "No display" message) to be in English so that we can recognise them.
    # We do this by setting both LC_ALL (per POSIX) and LANGUAGE (a GNU gettext
    # extension) to en_US.UTF-8.  (Setting LANG=C would disable localisation
    # entirely, but has the bad side-effect of also setting the character
    # encoding to ASCII, which breaks when the remote side sends a non-ASCII
    # character.)
    #
    # Note that this does not affect messages from the vim server process,
    # which should be matched using error codes as usual.
    env = dict(self.env.items() +
               [['LANGUAGE', 'en_US.UTF-8'], ['LC_ALL', 'en_US.UTF-8']])

    out, err = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env).communicate()
    if out is None:
      raise Quit('Vim could not respond to query "%s"' % ' '.join(cmd[3:]))
    if err:
      error_text = err.decode('utf-8').rstrip('\n')
      if error_text == 'No display: Send expression failed.':
        raise NoDisplay(self.env.get('DISPLAY'))
      else:
        raise ErrorOnExit(error_text)
    return out.decode('utf-8')


def VimscriptString(string):
  """Escapes & quotes a string for usage as a vimscript string literal.

  Escaped such that \\n will mean newline (in other words double-quoted
  vimscript strings are used).

  >>> VimscriptString('Then (s)he said\\n"Hello"')
  '"Then (s)he said\\\\n\\\\"Hello\\\\""'

  Args:
    string: The string to escape.
  Returns:
    The escaped string, in double quotes.
  """
  return json.dumps(string)


def SplitCommand(string):
  """Parse out the actual command from the shell command.

  Vim will say things like
  /path/to/$SHELL -c '(cmd args) < /tmp/in > /tmp/out'
  We want to parse out just the 'cmd args' part. This is a bit difficult,
  because we don't know precisely what vim's shellescaping will do.

  This is a rather simple parser that grabs the first parenthesis block
  and knows enough to avoid nested parens, escaped parens, and parens in
  strings.

  NOTE: If the user does :call system('echo )'), *vim will error*. This is
  a bug in vim. We do not need to be sane in this case.

  >>> cmd, rebuild = SplitCommand('ls')
  >>> cmd
  'ls'
  >>> rebuild('mycmd')
  'mycmd'
  >>> cmd, rebuild = SplitCommand('(echo ")") < /tmp/in > /tmp/out')
  >>> cmd
  'echo ")"'
  >>> rebuild('mycmd')
  '(mycmd) < /tmp/in > /tmp/out'
  >>> SplitCommand('(cat /foo/bar > /tmp/whatever)')[0]
  'cat /foo/bar > /tmp/whatever'
  >>> SplitCommand("(echo '()')")[0]
  "echo '()'"

  Args:
    string: The command string to parse.
  Returns:
    (relevant, rebuild): A tuple containing the actual command issued by the
    user and a function to rebuild the full command that vim wants to execute.
  """
  if string.startswith('('):
    stack = []
    for i, char in enumerate(string):
      if stack and stack[-1] == '\\':
        stack.pop()
      elif stack and stack[-1] == '"' and char == '"':
        stack.pop()
      elif stack and stack[-1] == "'" and char == "'":
        stack.pop()
      elif stack and stack[-1] == '(' and char == ')':
        stack.pop()
      elif char in '\\\'("':
        stack.append(char)
      if not stack:
        return (string[1:i], lambda cmd: (string[0] + cmd + string[i:]))
  return (string, lambda cmd: cmd)


class Quit(Exception):
  """Raised when vim seems to have quit unexpectedly."""

  # Whether vroom should exit immediately or finish running other tests.
  is_fatal = False


class ServerQuit(Quit):
  """Raised when the vim server process quits unexpectedly."""

  is_fatal = True

  def __str__(self):
    return 'Vim server process quit unexpectedly'


class ErrorOnExit(Quit):
  """Raised when a vim process unexpectedly prints to stderr."""

  def __init__(self, error_text):
    super(ErrorOnExit, self).__init__()
    self.error_text = error_text

  def __str__(self):
    return 'Vim quit unexpectedly, saying "{}"'.format(self.error_text)


class InvalidExpression(Quit):
  def __init__(self, expression):
    super(InvalidExpression, self).__init__()
    self.expression = expression

  def __str__(self):
    return 'Vim failed to evaluate expression "{}"'.format(self.expression)


class NoDisplay(Quit):
  """Raised when vim can't access the defined display properly."""

  def __init__(self, display_value):
    super(NoDisplay, self).__init__()
    self.display_value = display_value

  def __str__(self):
    if self.display_value is not None:
      display_context = 'display "{}"'.format(self.display_value)
    else:
      display_context = 'unspecified display'
    return 'Vim failed to access {}'.format(display_context)

########NEW FILE########
