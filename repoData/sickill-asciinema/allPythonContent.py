__FILENAME__ = asciicast
import os
import subprocess
import time


class Asciicast(object):

    def __init__(self, env=os.environ):
        self.command = None
        self.title = None
        self.shell = env.get('SHELL', '/bin/sh')
        self.term = env.get('TERM')
        self.username = env.get('USER')

    @property
    def meta_data(self):
        lines = int(get_command_output(['tput', 'lines']))
        columns = int(get_command_output(['tput', 'cols']))

        return {
            'username'   : self.username,
            'duration'   : self.duration,
            'title'      : self.title,
            'command'    : self.command,
            'shell'      : self.shell,
            'term'       : {
                'type'   : self.term,
                'lines'  : lines,
                'columns': columns
            }
        }


def get_command_output(args):
    process = subprocess.Popen(args, stdout=subprocess.PIPE)
    return process.communicate()[0].strip()

########NEW FILE########
__FILENAME__ = auth
class AuthCommand(object):

    def __init__(self, api_url, api_token):
        self.api_url = api_url
        self.api_token = api_token

    def execute(self):
        url = '%s/connect/%s' % (self.api_url, self.api_token)
        print('Open the following URL in your browser to register your API ' \
                'token and assign any recorded asciicasts to your profile:\n' \
                '%s' % url)

########NEW FILE########
__FILENAME__ = builder
import getopt

from .error import ErrorCommand
from .record import RecordCommand
from .auth import AuthCommand
from .help import HelpCommand
from .version import VersionCommand


def get_command(argv, config):
    try:
        opts, commands = getopt.getopt(argv, 'c:t:ihvy', ['help', 'version'])
    except getopt.error as msg:
        return ErrorCommand(msg)

    if len(commands) > 1:
        return ErrorCommand('Too many arguments')

    if len(commands) == 0:
        command = 'rec'
    elif len(commands) == 1:
        command = commands[0]

    cmd = None
    title = None
    skip_confirmation = False

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            return HelpCommand()
        elif opt in('-v', '--version'):
            return VersionCommand()
        elif opt == '-c':
            cmd = arg
        elif opt == '-t':
            title = arg
        elif opt == '-y':
            skip_confirmation = True

    if command == 'rec':
        return RecordCommand(config.api_url, config.api_token, cmd, title,
                             skip_confirmation)
    elif command == 'auth':
        return AuthCommand(config.api_url, config.api_token)

    return ErrorCommand("'%s' is not an asciinema command" % command)

########NEW FILE########
__FILENAME__ = error
import sys


class ErrorCommand(object):

    def __init__(self, message):
        self.message = message

    def execute(self):
        print("asciinema: %s. See 'asciinema --help'." % self.message)
        sys.exit(1)

########NEW FILE########
__FILENAME__ = help
class HelpCommand(object):

    def execute(self):
        print(HELP_TEXT)


HELP_TEXT = '''usage: asciinema [-h] [-y] [-c <command>] [-t <title>] [action]

Asciicast recorder+uploader.

Actions:
 rec              record asciicast (this is the default when no action given)
 auth             authenticate and/or claim recorded asciicasts

Optional arguments:
 -c command       run specified command instead of shell ($SHELL)
 -t title         specify title of recorded asciicast
 -y               don't prompt for confirmation
 -h, --help       show this help message and exit
 -v, --version    show version information'''

########NEW FILE########
__FILENAME__ = record
import sys
import subprocess

from asciinema.recorder import Recorder
from asciinema.uploader import Uploader, ServerMaintenanceError, ResourceNotFoundError
from asciinema.confirmator import Confirmator


class RecordCommand(object):

    def __init__(self, api_url, api_token, cmd, title, skip_confirmation,
                 recorder=None, uploader=None, confirmator=None):
        self.api_url = api_url
        self.api_token = api_token
        self.cmd = cmd
        self.title = title
        self.skip_confirmation = skip_confirmation
        self.recorder = recorder if recorder is not None else Recorder()
        self.uploader = uploader if uploader is not None else Uploader()
        self.confirmator = confirmator if confirmator is not None else Confirmator()

    def execute(self):
        asciicast = self._record_asciicast()
        self._upload_asciicast(asciicast)

    def _record_asciicast(self):
        self._reset_terminal()
        print('~ Asciicast recording started.')

        if not self.cmd:
            print('~ Hit ctrl+d or type "exit" to finish.')

        print('')

        asciicast = self.recorder.record(self.cmd, self.title)

        self._reset_terminal()
        print('~ Asciicast recording finished.')

        return asciicast

    def _upload_asciicast(self, asciicast):
        if self._upload_confirmed():
            print('~ Uploading...')
            try:
                url = self.uploader.upload(self.api_url, self.api_token, asciicast)
                print(url)
            except ServerMaintenanceError:
                print('~ Upload failed: The server is down for maintenance. Try again in a minute.')
                sys.exit(1)
            except ResourceNotFoundError:
                print('~ Upload failed: Your client version is no longer supported. Please upgrade to the latest version.')
                sys.exit(1)

    def _upload_confirmed(self):
        if self.skip_confirmation:
            return True

        return self.confirmator.confirm("~ Do you want to upload it? [Y/n] ")

    def _reset_terminal(self):
        subprocess.call(["reset"])
        pass

########NEW FILE########
__FILENAME__ = version
from asciinema import __version__


class VersionCommand(object):

    def execute(self):
        print('asciinema %s' % __version__)

########NEW FILE########
__FILENAME__ = config
import os
import sys

try:
    from ConfigParser import RawConfigParser, ParsingError, NoOptionError
except ImportError:
    from configparser import RawConfigParser, ParsingError, NoOptionError

import uuid


DEFAULT_CONFIG_FILE_PATH = "~/.asciinema/config"
DEFAULT_API_URL = 'https://asciinema.org'

class Config:

    def __init__(self, path=DEFAULT_CONFIG_FILE_PATH, overrides=None):
        self.path = os.path.expanduser(path)
        self.overrides = overrides if overrides is not None else os.environ

        self._parse_config_file()

    def _parse_config_file(self):
        config = RawConfigParser()
        config.add_section('user')
        config.add_section('api')

        try:
            config.read(self.path)
        except ParsingError:
            print('Config file %s contains syntax errors' % self.path)
            sys.exit(2)

        self.config = config

    @property
    def api_url(self):
        try:
            api_url = self.config.get('api', 'url')
        except NoOptionError:
            api_url = DEFAULT_API_URL

        api_url = self.overrides.get('ASCIINEMA_API_URL', api_url)

        return api_url

    @property
    def api_token(self):
        try:
            return self._get_api_token()
        except NoOptionError:
            try:
                return self._get_user_token()
            except NoOptionError:
                return self._create_api_token()

    def _ensure_base_dir(self):
        dir = os.path.dirname(self.path)

        if not os.path.isdir(dir):
            os.mkdir(dir)

    def _get_api_token(self):
        return self.config.get('api', 'token')

    def _get_user_token(self):
        return self.config.get('user', 'token')

    def _create_api_token(self):
        api_token = str(uuid.uuid1())
        self.config.set('api', 'token', api_token)

        self._ensure_base_dir()
        with open(self.path, 'w') as f:
            self.config.write(f)

        return api_token

########NEW FILE########
__FILENAME__ = confirmator
from __future__ import print_function
import sys


class Confirmator(object):

    def confirm(self, text):
        print(text, end='')
        sys.stdout.flush()
        answer = sys.stdin.readline().strip()
        return answer == 'y' or answer == 'Y' or answer == ''

########NEW FILE########
__FILENAME__ = pty_recorder
import os
import pty
import signal
import tty
import array
import fcntl
import termios
import select
import io
import shlex

from .stdout import Stdout


class PtyRecorder(object):

    def record_command(self, command, output=None):
        command = shlex.split(command)
        output = output if output is not None else Stdout()
        master_fd = None

        def _set_pty_size():
            '''
            Sets the window size of the child pty based on the window size
            of our own controlling terminal.
            '''

            # Get the terminal size of the real terminal, set it on the pseudoterminal.
            if os.isatty(pty.STDOUT_FILENO):
                buf = array.array('h', [0, 0, 0, 0])
                fcntl.ioctl(pty.STDOUT_FILENO, termios.TIOCGWINSZ, buf, True)
                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)
            else:
                buf = array.array('h', [24, 80, 0, 0])
                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)

        def _signal_winch(signal, frame):
            '''Signal handler for SIGWINCH - window size has changed.'''

            _set_pty_size()

        def _write_stdout(data):
            '''Writes to stdout as if the child process had written the data.'''

            os.write(pty.STDOUT_FILENO, data)

        def _handle_master_read(data):
            '''Handles new data on child process stdout.'''

            _write_stdout(data)
            output.write(data)

        def _write_master(data):
            '''Writes to the child process from its controlling terminal.'''

            while data:
                n = os.write(master_fd, data)
                data = data[n:]

        def _handle_stdin_read(data):
            '''Handles new data on child process stdin.'''

            _write_master(data)

        def _copy():
            '''Main select loop.

            Passes control to _master_read() or _stdin_read()
            when new data arrives.
            '''

            while 1:
                try:
                    rfds, wfds, xfds = select.select([master_fd, pty.STDIN_FILENO], [], [])
                except select.error as e:
                    if e[0] == 4:   # Interrupted system call.
                        continue

                if master_fd in rfds:
                    data = os.read(master_fd, 1024)

                    if len(data) == 0:
                        break

                    _handle_master_read(data)

                if pty.STDIN_FILENO in rfds:
                    data = os.read(pty.STDIN_FILENO, 1024)
                    _handle_stdin_read(data)


        pid, master_fd = pty.fork()

        if pid == pty.CHILD:
            os.execlp(command[0], *command)

        old_handler = signal.signal(signal.SIGWINCH, _signal_winch)

        try:
            mode = tty.tcgetattr(pty.STDIN_FILENO)
            tty.setraw(pty.STDIN_FILENO)
            restore = 1
        except tty.error: # This is the same as termios.error
            restore = 0

        _set_pty_size()

        try:
            _copy()
        except (IOError, OSError):
            if restore:
                tty.tcsetattr(pty.STDIN_FILENO, tty.TCSAFLUSH, mode)

        os.close(master_fd)
        signal.signal(signal.SIGWINCH, old_handler)

        return output

########NEW FILE########
__FILENAME__ = recorder
import os
from . import timer

from .asciicast import Asciicast
from .pty_recorder import PtyRecorder


class Recorder(object):

    def __init__(self, pty_recorder=None, env=None):
        self.pty_recorder = pty_recorder if pty_recorder is not None else PtyRecorder()
        self.env = env if env is not None else os.environ

    def record(self, cmd, title):
        duration, stdout = timer.timeit(self.pty_recorder.record_command,
                                        cmd or self.env.get('SHELL', '/bin/sh'))

        asciicast = Asciicast()
        asciicast.title = title
        asciicast.command = cmd
        asciicast.stdout = stdout
        asciicast.duration = duration

        return asciicast

########NEW FILE########
__FILENAME__ = requests_http_adapter
import requests


class RequestsHttpAdapter(object):

    def post(self, url, fields={}, files={}, headers={}):
        response = requests.post(url, data=fields, files=files, headers=headers)

        status  = response.status_code
        headers = response.headers
        body    = response.text

        return (status, headers, body)

########NEW FILE########
__FILENAME__ = stdout
import time
import io


class StdoutTiming(object):

    def __init__(self):
        self._items = []

    def append(self, item):
        self._items.append(item)

    def __str__(self):
        lines = ["%f %d" % (item[0], item[1]) for item in self._items]
        return "\n".join(lines)


class Stdout(object):

    def __init__(self, timing=None):
        self._data = io.BytesIO()
        self._timing = timing if timing is not None else StdoutTiming()

        self._start_timing()

    @property
    def data(self):
        return self._data.getvalue()

    @property
    def timing(self):
        return str(self._timing).encode()

    def write(self, data):
        now = time.time()
        delta = now - self._prev_time
        self._prev_time = now

        self._data.write(data)
        self._timing.append([delta, len(data)])

    def close(self):
        self._data.close()

    def _start_timing(self):
        self._prev_time = time.time()

########NEW FILE########
__FILENAME__ = timer
import time


def timeit(callable, *args):
    start_time = time.time()
    ret = callable(*args)
    end_time = time.time()
    duration = end_time - start_time

    return (duration, ret)

########NEW FILE########
__FILENAME__ = uploader
import json
import bz2
import platform
import re

from asciinema import __version__
from .requests_http_adapter import RequestsHttpAdapter


class ResourceNotFoundError(Exception):
    pass


class ServerMaintenanceError(Exception):
    pass


class Uploader(object):

    def __init__(self, http_adapter=None):
        self.http_adapter = http_adapter if http_adapter is not None else RequestsHttpAdapter()

    def upload(self, api_url, api_token, asciicast):
        url = '%s/api/asciicasts' % api_url
        files = self._asciicast_files(asciicast, api_token)
        headers = self._headers()

        status, headers, body = self.http_adapter.post(url, files=files,
                                                            headers=headers)

        if status == 503:
            raise ServerMaintenanceError()

        if status == 404:
            raise ResourceNotFoundError()

        return body

    def _asciicast_files(self, asciicast, api_token):
        return {
            'asciicast[stdout]': self._stdout_data_file(asciicast.stdout),
            'asciicast[stdout_timing]': self._stdout_timing_file(asciicast.stdout),
            'asciicast[meta]': self._meta_file(asciicast, api_token)
        }

    def _headers(self):
        return { 'User-Agent': self._user_agent() }

    def _stdout_data_file(self, stdout):
        return ('stdout', bz2.compress(stdout.data))

    def _stdout_timing_file(self, stdout):
        return ('stdout.time', bz2.compress(stdout.timing))

    def _meta_file(self, asciicast, api_token):
        return ('meta.json', self._meta_json(asciicast, api_token))

    def _meta_json(self, asciicast, api_token):
        meta_data = asciicast.meta_data
        auth_data = { 'user_token': api_token }
        data = dict(list(meta_data.items()) + list(auth_data.items()))

        return json.dumps(data)

    def _user_agent(self):
        os = re.sub('([^-]+)-(.*)', '\\1/\\2', platform.platform())

        return 'asciinema/%s %s/%s %s' % (__version__,
            platform.python_implementation(), platform.python_version(), os)

########NEW FILE########
__FILENAME__ = __main__
import sys

from .config import Config
from .commands.builder import get_command

def main():
    get_command(sys.argv[1:], Config()).execute()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = auth_command_test
import re

from asciinema.commands.auth import AuthCommand
from .test_helper import assert_printed, Test


class TestAuthCommand(Test):

    def test_execute(self):
        command = AuthCommand('http://the/url', 'a1b2c3')

        command.execute()

        assert_printed('http://the/url/connect/a1b2c3')

########NEW FILE########
__FILENAME__ = builder_test
from nose.tools import assert_equal

from asciinema.commands.builder import get_command
from asciinema.commands.error import ErrorCommand
from asciinema.commands.record import RecordCommand
from asciinema.commands.auth import AuthCommand
from asciinema.commands.help import HelpCommand
from asciinema.commands.version import VersionCommand


class Config(object):

    def api_url(self):
        return 'http://api/url'

    def api_token(self):
        return 'a-toh-can'


class TestGetCommand(object):

    def setUp(self):
        self.config = Config()

    def test_get_command_when_cmd_is_absent(self):
        command = get_command([], self.config)

        assert_equal(RecordCommand, type(command))

    def test_get_command_when_cmd_is_rec(self):
        command = get_command(['rec'], self.config)

        assert_equal(RecordCommand, type(command))
        assert_equal(self.config.api_url, command.api_url)
        assert_equal(self.config.api_token, command.api_token)
        assert_equal(None, command.cmd)
        assert_equal(None, command.title)
        assert_equal(False, command.skip_confirmation)

    def test_get_command_when_cmd_is_rec_and_options_given(self):
        argv = ['-c', '/bin/bash -l', '-t', "O'HAI LOL", '-y', 'rec']
        command = get_command(argv, self.config)

        assert_equal(RecordCommand, type(command))
        assert_equal(self.config.api_url, command.api_url)
        assert_equal(self.config.api_token, command.api_token)
        assert_equal('/bin/bash -l', command.cmd)
        assert_equal("O'HAI LOL", command.title)
        assert_equal(True, command.skip_confirmation)

    def test_get_command_when_cmd_is_auth(self):
        command = get_command(['auth'], self.config)

        assert_equal(AuthCommand, type(command))
        assert_equal(self.config.api_url, command.api_url)
        assert_equal(self.config.api_token, command.api_token)

    def test_get_command_when_options_include_h(self):
        command = get_command(['-h'], self.config)

        assert_equal(HelpCommand, type(command))

    def test_get_command_when_options_include_help(self):
        command = get_command(['--help'], self.config)

        assert_equal(HelpCommand, type(command))

    def test_get_command_when_options_include_v(self):
        command = get_command(['-v'], self.config)

        assert_equal(VersionCommand, type(command))

    def test_get_command_when_options_include_version(self):
        command = get_command(['--version'], self.config)

        assert_equal(VersionCommand, type(command))

    def test_get_command_when_cmd_is_unknown(self):
        command = get_command(['foobar'], self.config)

        assert_equal(ErrorCommand, type(command))
        assert_equal("'foobar' is not an asciinema command", command.message)

    def test_get_command_when_too_many_cmds(self):
        command = get_command(['foo', 'bar'], self.config)

        assert_equal(ErrorCommand, type(command))
        assert_equal("Too many arguments", command.message)

########NEW FILE########
__FILENAME__ = config_test
from nose.tools import assert_equal

import os
import tempfile
import re

from asciinema.config import Config


def create_config(content=None, overrides={}):
    dir = tempfile.mkdtemp()
    path = dir + '/config'

    if content:
        with open(path, 'w') as f:
            f.write(content)

    return Config(path, overrides)


class TestConfig(object):

    def test_api_url_when_no_file_and_no_override_set(self):
        config = create_config()
        assert_equal('https://asciinema.org', config.api_url)

    def test_api_url_when_no_url_set_and_no_override_set(self):
        config = create_config('')
        assert_equal('https://asciinema.org', config.api_url)

    def test_api_url_when_url_set_and_no_override_set(self):
        config = create_config("[api]\nurl = http://the/url")
        assert_equal('http://the/url', config.api_url)

    def test_api_url_when_url_set_and_override_set(self):
        config = create_config("[api]\nurl = http://the/url", {
            'ASCIINEMA_API_URL': 'http://the/url2' })
        assert_equal('http://the/url2', config.api_url)

    def test_api_token_when_no_file(self):
        config = create_config()

        assert re.match('^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}', config.api_token)
        assert os.path.isfile(config.path)

    def test_api_token_when_no_dir(self):
        config = create_config()
        dir = os.path.dirname(config.path)
        os.rmdir(dir)

        assert re.match('^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}', config.api_token)
        assert os.path.isfile(config.path)

    def test_api_token_when_no_api_token_set(self):
        config = create_config('')
        assert re.match('^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}', config.api_token)

    def test_api_token_when_api_token_set(self):
        token = 'foo-bar-baz'
        config = create_config("[api]\ntoken = %s" % token)
        assert re.match(token, config.api_token)

    def test_api_token_when_api_token_set_as_user_token(self):
        token = 'foo-bar-baz'
        config = create_config("[user]\ntoken = %s" % token)
        assert re.match(token, config.api_token)

    def test_api_token_when_api_token_set_and_user_token_set(self):
        user_token = 'foo'
        api_token = 'bar'
        config = create_config("[user]\ntoken = %s\n[api]\ntoken = %s" %
                               (user_token, api_token))
        assert re.match(api_token, config.api_token)

########NEW FILE########
__FILENAME__ = confirmator_test
import sys

from asciinema.confirmator import Confirmator
from .test_helper import assert_printed, assert_not_printed, Test


class FakeStdin(object):

    def set_line(self, line):
        self.line = line

    def readline(self):
        return self.line


class TestConfirmator(Test):

    def setUp(self):
        Test.setUp(self)
        self.real_stdin = sys.stdin
        sys.stdin = self.stdin = FakeStdin()

    def tearDown(self):
        Test.tearDown(self)
        sys.stdin = self.real_stdin

    def test_confirm_when_y_entered(self):
        confirmator = Confirmator()
        self.stdin.set_line("y\n")

        assert confirmator.confirm('Wanna?')
        assert_printed('Wanna?')

    def test_confirm_when_Y_entered(self):
        confirmator = Confirmator()
        self.stdin.set_line("Y\n")

        assert confirmator.confirm('Wanna?')
        assert_printed('Wanna?')

    def test_confirm_when_enter_hit(self):
        confirmator = Confirmator()
        self.stdin.set_line("\n")

        assert confirmator.confirm('Wanna?')
        assert_printed('Wanna?')

    def test_confirm_when_spaces_entered(self):
        confirmator = Confirmator()
        self.stdin.set_line("  \n")

        assert confirmator.confirm('Wanna?')
        assert_printed('Wanna?')

    def test_confirm_when_n_entered(self):
        confirmator = Confirmator()
        self.stdin.set_line("n\n")

        assert not confirmator.confirm('Wanna?')
        assert_printed('Wanna?')

    def test_confirm_when_foo_entered(self):
        confirmator = Confirmator()
        self.stdin.set_line("foo\n")

        assert not confirmator.confirm('Wanna?')
        assert_printed('Wanna?')

########NEW FILE########
__FILENAME__ = error_command_test
from nose.tools import assert_raises

from asciinema.commands.error import ErrorCommand
from .test_helper import assert_printed, Test


class TestErrorCommand(Test):

    def test_execute(self):
        command = ErrorCommand('foo')

        assert_raises(SystemExit, command.execute)
        assert_printed('foo')

########NEW FILE########
__FILENAME__ = help_command_test
from asciinema.commands.help import HelpCommand
from .test_helper import assert_printed, Test


class TestHelpCommand(Test):

    def test_execute(self):
        command = HelpCommand()

        command.execute()

        assert_printed('asciinema')
        assert_printed('usage')
        assert_printed('rec')
        assert_printed('auth')

########NEW FILE########
__FILENAME__ = pty_recorder_test
import os
import pty

from nose.tools import assert_equal
from .test_helper import Test

from asciinema.stdout import Stdout
from asciinema.pty_recorder import PtyRecorder


class FakeStdout(object):

    def __init__(self):
        self.data = []
        self.closed = False

    def write(self, data):
        self.data.append(data)


class TestPtyRecorder(Test):

    def setUp(self):
        self.real_os_write = os.write
        os.write = self.os_write

    def tearDown(self):
        os.write = self.real_os_write

    def os_write(self, fd, data):
        if fd != pty.STDOUT_FILENO:
            self.real_os_write(fd, data)

    def test_record_command_returns_stdout_instance(self):
        pty_recorder = PtyRecorder()

        output = pty_recorder.record_command('ls -l')

        assert_equal(Stdout, type(output))

    def test_record_command_writes_to_stdout(self):
        pty_recorder = PtyRecorder()
        output = FakeStdout()

        command = 'python -c "import sys, time; sys.stdout.write(\'foo\'); ' \
                  'sys.stdout.flush(); time.sleep(0.01); sys.stdout.write(\'bar\')"'
        pty_recorder.record_command(command, output)

        assert_equal([b'foo', b'bar'], output.data)

########NEW FILE########
__FILENAME__ = recorder_test
from nose.tools import assert_equal

from .test_helper import Test
from asciinema.recorder import Recorder
import asciinema.timer


class FakePtyRecorder(object):

    class Stdout(object):
        pass

    def __init__(self):
        self.stdout = self.Stdout()
        self.command = None

    def record_command(self, *args):
        self.call_args = args

        return self.stdout

    def record_call_args(self):
        return self.call_args


class TestRecorder(Test):

    def setUp(self):
        Test.setUp(self)
        self.pty_recorder = FakePtyRecorder()
        self.real_timeit = asciinema.timer.timeit
        asciinema.timer.timeit = lambda c, *args: (123.45, c(*args))

    def tearDown(self):
        asciinema.timer.timeit = self.real_timeit

    def test_record_when_title_and_command_given(self):
        recorder = Recorder(self.pty_recorder)

        asciicast = recorder.record('ls -l', 'the title')

        assert_equal('the title', asciicast.title)
        assert_equal('ls -l', asciicast.command)
        assert_equal(('ls -l',), self.pty_recorder.record_call_args())
        assert_equal(123.45, asciicast.duration)
        assert_equal(self.pty_recorder.stdout, asciicast.stdout)

    def test_record_when_no_title_nor_command_given(self):
        env = { 'SHELL': '/bin/blush' }
        recorder = Recorder(self.pty_recorder, env)

        asciicast = recorder.record(None, None)

        assert_equal(None, asciicast.title)
        assert_equal(None, asciicast.command)
        assert_equal(('/bin/blush',), self.pty_recorder.record_call_args())
        assert_equal(123.45, asciicast.duration)
        assert_equal(self.pty_recorder.stdout, asciicast.stdout)

########NEW FILE########
__FILENAME__ = record_command_test
import sys
import subprocess

from nose.tools import assert_equal, assert_raises
from asciinema.commands.record import RecordCommand
from asciinema.uploader import ServerMaintenanceError, ResourceNotFoundError
from .test_helper import assert_printed, assert_not_printed, Test, FakeAsciicast


class FakeRecorder(object):

    def __init__(self):
        self.asciicast = None

    def record(self, cmd, title):
        self.asciicast = FakeAsciicast(cmd, title)
        return self.asciicast


class FakeUploader(object):

    def __init__(self, error_to_raise=None):
        self.uploaded = None
        self.error_to_raise = error_to_raise

    def upload(self, api_url, api_token, asciicast):
        if self.error_to_raise:
            raise self.error_to_raise

        self.uploaded = [api_url, api_token, asciicast]
        return 'http://asciicast/url'


class FakeConfirmator(object):

    def __init__(self):
        self.text = ''
        self.success = True

    def confirm(self, text):
        self.text = text
        return self.success


class TestRecordCommand(Test):

    def setUp(self):
        Test.setUp(self)
        self.recorder = FakeRecorder()
        self.uploader = FakeUploader()
        self.confirmator = FakeConfirmator()
        self.real_subprocess_call = subprocess.call
        subprocess.call = lambda *args: None

    def tearDown(self):
        subprocess.call = self.real_subprocess_call

    def create_command(self, skip_confirmation):
        return RecordCommand('http://the/url', 'a1b2c3', 'ls -l', 'the title',
                             skip_confirmation, self.recorder, self.uploader,
                             self.confirmator)

    def test_execute_when_upload_confirmation_skipped(self):
        command = self.create_command(True)
        self.confirmator.success = False

        command.execute()

        assert 'Do you want to upload' not in self.confirmator.text
        self.assert_recorded_and_uploaded()

    def test_execute_when_upload_confirmed(self):
        command = self.create_command(False)
        self.confirmator.success = True

        command.execute()

        assert 'Do you want to upload' in self.confirmator.text
        self.assert_recorded_and_uploaded()

    def test_execute_when_upload_rejected(self):
        command = self.create_command(False)
        self.confirmator.success = False

        command.execute()

        assert 'Do you want to upload' in self.confirmator.text
        self.assert_recorded_but_not_uploaded()

    def test_execute_when_uploader_raises_not_found_error(self):
        self.uploader = FakeUploader(ResourceNotFoundError())
        command = self.create_command(True)

        assert_raises(SystemExit, command.execute)
        assert_printed('upgrade')

    def test_execute_when_uploader_raises_maintenance_error(self):
        self.uploader = FakeUploader(ServerMaintenanceError())
        command = self.create_command(True)

        assert_raises(SystemExit, command.execute)
        assert_printed('maintenance')

    def assert_recorded_but_not_uploaded(self):
        asciicast = self.recorder.asciicast
        assert asciicast, 'asciicast not recorded'
        assert_not_printed('Uploading...')
        assert_equal(None, self.uploader.uploaded)

    def assert_recorded_and_uploaded(self):
        asciicast = self.recorder.asciicast
        assert asciicast, 'asciicast not recorded'
        assert_equal('ls -l', asciicast.cmd)
        assert_equal('the title', asciicast.title)
        assert_printed('Uploading...')
        assert_equal(['http://the/url', 'a1b2c3', asciicast], self.uploader.uploaded)
        assert_printed('http://asciicast/url')

########NEW FILE########
__FILENAME__ = requests_http_adapter_test
import requests
from nose.tools import assert_equal
from .test_helper import Test
from asciinema.requests_http_adapter import RequestsHttpAdapter


class FakeResponse(object):

    def __init__(self, status=200, headers={}, body=''):
        self.status_code = status
        self.headers = headers
        self.text = body


class TestRequestsHttpAdapter(Test):

    def setUp(self):
        Test.setUp(self)
        self._real_requests_post = requests.post
        requests.post = self._fake_post

    def tearDown(self):
        Test.tearDown(self)
        requests.post = self._real_requests_post

    def test_post(self):
        adapter = RequestsHttpAdapter()

        status, headers, body = adapter.post(
            'http://the/url',
            { 'field': 'value' },
            { 'file': ('name.txt', b'contents') },
            { 'foo': 'bar' }
        )

        assert_equal('http://the/url', self._post_args['url'])
        assert_equal({ 'field': 'value' }, self._post_args['data'])
        assert_equal({ 'file': ('name.txt', b'contents') }, self._post_args['files'])
        assert_equal({ 'foo': 'bar' }, self._post_args['headers'])

        assert_equal(200, status)
        assert_equal({ 'Content-type': 'text/plain' }, headers)
        assert_equal('body', body)

    def _fake_post(self, url, data={}, files={}, headers={}):
        self._post_args = { 'url': url, 'data': data, 'files': files,
                            'headers': headers }

        return FakeResponse(200, { 'Content-type': 'text/plain' }, 'body' )

########NEW FILE########
__FILENAME__ = stdout_test
import time

from nose.tools import assert_equal, assert_raises
from .test_helper import Test, FakeClock
from asciinema.stdout import Stdout, StdoutTiming


class TestStdoutTiming(Test):

    def test_append(self):
        timing = StdoutTiming()

        timing.append([0.123, 100])
        timing.append([1234.56, 33])

        assert_equal('0.123000 100\n1234.560000 33', str(timing))


class TestStdout(Test):

    def setUp(self):
        Test.setUp(self)
        self.real_time = time.time
        time.time = FakeClock([1, 3, 10]).time

    def tearDown(self):
        time.time = self.real_time

    def test_write(self):
        timing = []
        stdout = Stdout(timing)

        stdout.write(b'foo')
        stdout.write(b'barbaz')

        assert_equal(b'foobarbaz', stdout.data)
        assert_equal([[2, 3], [7, 6]], timing)

    def test_close(self):
        stdout = Stdout()

        stdout.close()

        assert_raises(ValueError, stdout.write, 'qux')

########NEW FILE########
__FILENAME__ = test_helper
import sys
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


stdout = None


def assert_printed(expected):
    success = expected in stdout.getvalue()
    assert success, 'expected text "%s" not printed' % expected


def assert_not_printed(expected):
    success = expected not in stdout.getvalue()
    assert success, 'not expected text "%s" printed' % expected


class Test(object):

    def setUp(self):
        global stdout
        self.real_stdout = sys.stdout
        sys.stdout = stdout = StringIO()

    def tearDown(self):
        sys.stdout = self.real_stdout


class FakeClock(object):

    def __init__(self, values):
        self.values = values
        self.n = 0

    def time(self):
        value = self.values[self.n]
        self.n += 1

        return value


class FakeAsciicast(object):

    def __init__(self, cmd=None, title=None, stdout=None, meta_data=None):
        self.cmd = cmd
        self.title = title
        self.stdout = stdout
        self.meta_data = meta_data or {}

########NEW FILE########
__FILENAME__ = timer_test
import time

from nose.tools import assert_equal
from .test_helper import Test, FakeClock
from asciinema.timer import timeit


class TestTimer(Test):

    def setUp(self):
        self.real_time = time.time
        time.time = FakeClock([10.0, 24.57]).time

    def tearDown(self):
        time.time = self.real_time

    def test_timeit(self):
        duration, return_value = timeit(lambda *args: args, 1, 'two', True)

        assert_equal(14.57, duration)
        assert_equal((1, 'two', True), return_value)

########NEW FILE########
__FILENAME__ = uploader_test
import json
import bz2
import platform
from nose.tools import assert_equal, assert_raises
from .test_helper import Test, FakeAsciicast
from asciinema import __version__
from asciinema.uploader import Uploader, ServerMaintenanceError, ResourceNotFoundError


class FakeHttpAdapter(object):

    def __init__(self, status):
        self.status = status
        self.url = None
        self.files = None
        self.headers = None

    def post(self, url, files, headers):
        self.url = url
        self.files = files
        self.headers = headers

        return (self.status, { 'Content-type': 'text/plain' }, b'success!')


class FakeStdout(object):

    def __init__(self, data=None, timing=None):
        self.data = data or b''
        self.timing = timing or b''


class TestUploader(Test):

    def setUp(self):
        Test.setUp(self)
        self.stdout = FakeStdout(b'data123', b'timing456')
        self.asciicast = FakeAsciicast(cmd='ls -l', title='tit',
                stdout=self.stdout, meta_data={ 'shell': '/bin/sh' })
        self.real_platform = platform.platform
        platform.platform = lambda: 'foo-bar-baz-qux-quux'

    def tearDown(self):
        Test.tearDown(self)
        platform.platform = self.real_platform

    def test_upload_when_status_201_returned(self):
        http_adapter = FakeHttpAdapter(201)
        uploader = Uploader(http_adapter)

        response_body = uploader.upload('http://api/url', 'a1b2c3', self.asciicast)

        assert_equal(b'success!', response_body)
        assert_equal('http://api/url/api/asciicasts', http_adapter.url)
        assert_equal(self._expected_files(), http_adapter.files)
        assert_equal(self._expected_headers(), http_adapter.headers)

    def test_upload_when_status_503_returned(self):
        http_adapter = FakeHttpAdapter(503)
        uploader = Uploader(http_adapter)

        assert_raises(ServerMaintenanceError, uploader.upload,
                      'http://api/url', 'a1b2c3', self.asciicast)

    def test_upload_when_status_404_returned(self):
        http_adapter = FakeHttpAdapter(404)
        uploader = Uploader(http_adapter)

        assert_raises(ResourceNotFoundError, uploader.upload,
                      'http://api/url', 'a1b2c3', self.asciicast)

    def _expected_files(self):
        return {
            'asciicast[meta]':
                ('meta.json', json.dumps({ 'shell': '/bin/sh',
                                           'user_token': 'a1b2c3' })),
            'asciicast[stdout]':
                ('stdout', bz2.compress(b'data123')),
            'asciicast[stdout_timing]':
                ('stdout.time', bz2.compress(b'timing456'))
        }

    def _expected_headers(self):
        return { 'User-Agent': 'asciinema/%s %s/%s %s' %
               (__version__, platform.python_implementation(),
                   platform.python_version(), 'foo/bar-baz-qux-quux') }

########NEW FILE########
__FILENAME__ = version_command_test
from asciinema.commands.version import VersionCommand
from asciinema import __version__
from .test_helper import assert_printed, Test


class TestVersionCommand(Test):

    def test_execute(self):
        command = VersionCommand()

        command.execute()

        assert_printed('asciinema %s' % __version__)

########NEW FILE########
