__FILENAME__ = errors
class NoSuchCommandError(OSError):
    def __init__(self, command):
        if "/" in command:
            message = "No such command: {0}".format(command)
        else:
            message = "Command not found: {0}. Check that {0} is installed and on $PATH".format(command)
        super(type(self), self).__init__(message)
        self.command = command

########NEW FILE########
__FILENAME__ = files
import os

class FileOperations(object):
    def __init__(self, shell):
        self._shell = shell
        
    def copy_file(self, source, destination=None, dir=None):
        if destination is None and dir is None:
            raise TypeError("Destination required for copy")
            
        if destination is not None:
            self._shell.run(["cp", "-T", source, destination])
        elif dir is not None:
            self._shell.run(["cp", source, "-t", dir])
            
    def write_file(self, path, contents):
        self._shell.run(["mkdir", "-p", os.path.dirname(path)])
        file = self._shell.open(path, "w")
        try:
            file.write(contents)
        finally:
            file.close()
        

########NEW FILE########
__FILENAME__ = io
import threading


class IoHandler(object):
    def __init__(self, in_out_pairs):
        self._handlers = [
            OutputHandler(file_in, file_out)
            for file_in, file_out
            in in_out_pairs
        ]
        
    def wait(self):
        return [handler.wait() for handler in self._handlers]
    

class OutputHandler(object):
    def __init__(self, file_in, file_out):
        self._file_in = file_in
        self._file_out = file_out
        self._output = ""
        
        self._thread = threading.Thread(target=self._capture_output)
        self._thread.daemon = True
        self._thread.start()

    def wait(self):
        self._thread.join()
        return self._output
    
    def _capture_output(self):
        if self._file_out is None:
            try:
                self._output = self._file_in.read()
            except IOError:
                # TODO: is there a more elegant fix?
                # Attempting to read from a pty master that has received nothing
                # seems to raise an IOError when reading
                # See: http://bugs.python.org/issue5380
                self._output = b""
        else:
            output_buffer = []
            while True:
                output = self._file_in.read(1)
                if output:
                    self._file_out.write(output)
                    output_buffer.append(output)
                else:
                    self._output = b"".join(output_buffer)
                    return

########NEW FILE########
__FILENAME__ = local
import os
import subprocess
import shutil
io = __import__("io")
import threading

try:
    import pty
except ImportError:
    pty = None

from spur.tempdir import create_temporary_dir
from spur.files import FileOperations
import spur.results
from .io import IoHandler
from .errors import NoSuchCommandError


class LocalShell(object):
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        pass
    
    def upload_dir(self, source, dest, ignore=None):
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns(*ignore))

    def upload_file(self, source, dest):
        shutil.copyfile(source, dest)
    
    def open(self, name, mode="r"):
        return open(name, mode)
    
    def write_file(self, remote_path, contents):
        subprocess.check_call(["mkdir", "-p", os.path.dirname(remote_path)])
        open(remote_path, "w").write(contents)

    def spawn(self, command, *args, **kwargs):
        stdout = kwargs.pop("stdout", None)
        stderr = kwargs.pop("stderr", None)
        allow_error = kwargs.pop("allow_error", False)
        store_pid = kwargs.pop("store_pid", False)
        use_pty = kwargs.pop("use_pty", False)
        if use_pty:
            if pty is None:
                raise ValueError("use_pty is not supported when the pty module cannot be imported")
            master, slave = pty.openpty()
            stdin_arg = slave
            stdout_arg = slave
            stderr_arg = subprocess.STDOUT
        else:
            stdin_arg = subprocess.PIPE
            stdout_arg = subprocess.PIPE
            stderr_arg = subprocess.PIPE
                
        try:
            process = subprocess.Popen(
                stdin=stdin_arg,
                stdout=stdout_arg,
                stderr=stderr_arg,
                bufsize=0,
                **self._subprocess_args(command, *args, **kwargs)
            )
        except OSError:
            raise NoSuchCommandError(command[0])
            
        if use_pty:
            # TODO: Should close master ourselves rather than relying on
            # garbage collection
            process_stdin = os.fdopen(os.dup(master), "wb", 0)
            process_stdout = os.fdopen(master, "rb", 0)
            process_stderr = io.BytesIO()
            
            def close_slave_on_exit():
                process.wait()
                os.close(slave)
            
            thread = threading.Thread(target=close_slave_on_exit)
            thread.daemon = True
            thread.start()
            
        else:
            process_stdin = process.stdin
            process_stdout = process.stdout
            process_stderr = process.stderr
            
        spur_process = LocalProcess(
            process,
            allow_error=allow_error,
            process_stdin=process_stdin,
            process_stdout=process_stdout,
            process_stderr=process_stderr,
            stdout=stdout,
            stderr=stderr
        )
        if store_pid:
            spur_process.pid = process.pid
        return spur_process
        
    def run(self, *args, **kwargs):
        return self.spawn(*args, **kwargs).wait_for_result()
        
    def temporary_dir(self):
        return create_temporary_dir()
    
    @property
    def files(self):
        return FileOperations(self)
    
    def _subprocess_args(self, command, cwd=None, update_env=None, new_process_group=False):
        kwargs = {
            "args": command,
            "cwd": cwd,
        }
        if update_env is not None:
            new_env = os.environ.copy()
            new_env.update(update_env)
            kwargs["env"] = new_env
        if new_process_group:
            kwargs["preexec_fn"] = os.setpgrp
        return kwargs
        

class LocalProcess(object):
    def __init__(self, subprocess, allow_error, process_stdin, process_stdout, process_stderr, stdout, stderr):
        self._subprocess = subprocess
        self._allow_error = allow_error
        self._process_stdin = process_stdin
        self._result = None
            
        self._io = IoHandler([
            (process_stdout, stdout),
            (process_stderr, stderr),
        ])
        
    def is_running(self):
        return self._subprocess.poll() is None
        
    def stdin_write(self, value):
        self._process_stdin.write(value)
        
    def send_signal(self, signal):
        self._subprocess.send_signal(signal)
        
    def wait_for_result(self):
        if self._result is None:
            self._result = self._generate_result()
            
        return self._result
        
    def _generate_result(self):
        output, stderr_output = self._io.wait()
        return_code = self._subprocess.wait()
        
        return spur.results.result(
            return_code,
            self._allow_error,
            output,
            stderr_output
        )


########NEW FILE########
__FILENAME__ = results
import locale


def result(return_code, allow_error, output, stderr_output):
    result = ExecutionResult(return_code, output, stderr_output)
    if return_code == 0 or allow_error:
        return result
    else:
        raise result.to_error()
        

class ExecutionResult(object):
    def __init__(self, return_code, output, stderr_output):
        self.return_code = return_code
        self.output = output
        self.stderr_output = stderr_output
        
    def to_error(self):
        return RunProcessError(
            self.return_code,
            self.output, 
            self.stderr_output
        )
        
        
class RunProcessError(RuntimeError):
    def __init__(self, return_code, output, stderr_output):
        message = "return code: {0}\noutput: {1}\nstderr output: {2}".format(
            return_code, _bytes_repr(output), _bytes_repr(stderr_output))
        super(type(self), self).__init__(message)
        self.return_code = return_code
        self.output = output
        self.stderr_output = stderr_output


def _bytes_repr(raw_bytes):
    result =  repr(raw_bytes)
    if result.startswith("b"):
        return result
    else:
        return "b" + result

########NEW FILE########
__FILENAME__ = ssh
from __future__ import unicode_literals

import subprocess
import os
import os.path
import shutil
import contextlib
import uuid
import socket
import traceback
import sys

import paramiko

from spur.tempdir import create_temporary_dir
from spur.files import FileOperations
import spur.results
from .io import IoHandler
from .errors import NoSuchCommandError


_ONE_MINUTE = 60


class ConnectionError(Exception):
    pass


class AcceptParamikoPolicy(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        return


class MissingHostKey(object):
    raise_error = paramiko.RejectPolicy()
    warn = paramiko.WarningPolicy()
    auto_add = paramiko.AutoAddPolicy()
    accept = AcceptParamikoPolicy()


class SshShell(object):
    def __init__(self,
            hostname,
            username=None,
            password=None,
            port=22,
            private_key_file=None,
            connect_timeout=None,
            missing_host_key=None):
        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password
        self._private_key_file = private_key_file
        self._client = None
        self._connect_timeout = connect_timeout if not None else _ONE_MINUTE
        self._closed = False
        
        if missing_host_key is None:
            self._missing_host_key = MissingHostKey.raise_error
        else:
            self._missing_host_key = missing_host_key

    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self._closed = True
        if self._client is not None:
            self._client.close()

    def run(self, *args, **kwargs):
        return self.spawn(*args, **kwargs).wait_for_result()
    
    def spawn(self, command, *args, **kwargs):
        stdout = kwargs.pop("stdout", None)
        stderr = kwargs.pop("stderr", None)
        allow_error = kwargs.pop("allow_error", False)
        store_pid = kwargs.pop("store_pid", False)
        use_pty = kwargs.pop("use_pty", False)
        command_in_cwd = self._generate_run_command(command, *args, store_pid=store_pid, **kwargs)
        try:
            channel = self._get_ssh_transport().open_session()
        except EOFError as error:
            raise self._connection_error(error)
        if use_pty:
            channel.get_pty()
        channel.exec_command(command_in_cwd)
        
        process_stdout = channel.makefile('rb')
        
        if store_pid:
            pid = _read_int_line(process_stdout)
            
        which_return_code = _read_int_line(process_stdout)
        
        if which_return_code != 0:
            raise NoSuchCommandError(command[0])
        
        process = SshProcess(
            channel,
            allow_error=allow_error,
            process_stdout=process_stdout,
            stdout=stdout,
            stderr=stderr,
            shell=self,
        )
        if store_pid:
            process.pid = pid
        
        return process
    
    @contextlib.contextmanager
    def temporary_dir(self):
        result = self.run(["mktemp", "--directory"])
        temp_dir = result.output.strip()
        try:
            yield temp_dir
        finally:
            self.run(["rm", "-rf", temp_dir])
    
    def _generate_run_command(self, command_args, store_pid,
            cwd=None, update_env={}, new_process_group=False):
        commands = []

        if store_pid:
            commands.append("echo $$")

        if cwd is not None:
            commands.append("cd {0}".format(escape_sh(cwd)))
        
        update_env_commands = [
            "export {0}={1}".format(key, escape_sh(value))
            for key, value in _iteritems(update_env)
        ]
        commands += update_env_commands
        commands.append(" || ".join(self._generate_which_commands(command_args[0])))
        commands.append("echo $?")
        
        command = " ".join(map(escape_sh, command_args))
        command = "exec {0}".format(command)
        if new_process_group:
            command = "setsid {0}".format(command)
            
        commands.append(command)
        return "; ".join(commands)
    
    def _generate_which_commands(self, command):
        which_commands = ["command -v {0}", "which {0}"]
        return (
            self._generate_which_command(which, command)
            for which in which_commands
        )
    
    def _generate_which_command(self, which, command):
        return which.format(escape_sh(command)) + " > /dev/null 2>&1"
    
    def upload_dir(self, local_dir, remote_dir, ignore):
        with create_temporary_dir() as temp_dir:
            content_tarball_path = os.path.join(temp_dir, "content.tar.gz")
            content_path = os.path.join(temp_dir, "content")
            shutil.copytree(local_dir, content_path, ignore=shutil.ignore_patterns(*ignore))
            subprocess.check_call(
                ["tar", "czf", content_tarball_path, "content"],
                cwd=temp_dir
            )
            with self._connect_sftp() as sftp:
                remote_tarball_path = "/tmp/{0}.tar.gz".format(uuid.uuid4())
                sftp.put(content_tarball_path, remote_tarball_path)
                self.run(["mkdir", "-p", remote_dir])
                self.run([
                    "tar", "xzf", remote_tarball_path,
                    "--strip-components", "1", "--directory", remote_dir
                ])
                    
                sftp.remove(remote_tarball_path)
                
    def open(self, name, mode="r"):
        sftp = self._open_sftp_client()
        return SftpFile(sftp, sftp.open(name, mode))
                
    @property
    def files(self):
        return FileOperations(self)
    
    def _get_ssh_transport(self):
        try:
            return self._connect_ssh().get_transport()
        except (socket.error, paramiko.SSHException, EOFError) as error:
            raise self._connection_error(error)
    
    def _connect_ssh(self):
        if self._client is None:
            if self._closed:
                raise RuntimeError("Shell is closed")
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(self._missing_host_key)
            client.connect(
                hostname=self._hostname,
                port=self._port,
                username=self._username,
                password=self._password,
                key_filename=self._private_key_file,
                timeout=self._connect_timeout
            )
            self._client = client
        return self._client
    
    @contextlib.contextmanager
    def _connect_sftp(self):
        sftp = self._open_sftp_client()
        try:
            yield sftp
        finally:
            sftp.close()
            
    def _open_sftp_client(self):
        return self._get_ssh_transport().open_sftp_client()
        
    def _connection_error(self, error):
        connection_error = ConnectionError(
            "Error creating SSH connection\n" +
            "Original error: {0}".format(error)
        )
        connection_error.original_error = error
        connection_error.original_traceback = traceback.format_exc()
        return connection_error


def _read_int_line(output_file):
    while True:
        line = output_file.readline().strip()
        if line:
            return int(line)


class SftpFile(object):
    def __init__(self, sftp, file):
        self._sftp = sftp
        self._file = file
    
    def __getattr__(self, key):
        if hasattr(self._file, key):
            return getattr(self._file, key)
        raise AttributeError
        
    def close(self):
        try:
            self._file.close()
        finally:
            self._sftp.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
        

def escape_sh(value):
    return "'" + value.replace("'", "'\\''") + "'"


class SshProcess(object):
    def __init__(self, channel, allow_error, process_stdout, stdout, stderr, shell):
        self._channel = channel
        self._allow_error = allow_error
        self._stdin = channel.makefile('wb')
        self._stdout = process_stdout
        self._stderr = channel.makefile_stderr('rb')
        self._shell = shell
        self._result = None
        
        self._io = IoHandler([
            (self._stdout, stdout),
            (self._stderr, stderr),
        ])
        
    def is_running(self):
        return not self._channel.exit_status_ready()
        
    def stdin_write(self, value):
        self._channel.sendall(value)
        
    def send_signal(self, signal):
        self._shell.run(["kill", "-{0}".format(signal), str(self.pid)])
        
    def wait_for_result(self):
        if self._result is None:
            self._result = self._generate_result()
            
        return self._result
        
    def _generate_result(self):
        output, stderr_output = self._io.wait()
        return_code = self._channel.recv_exit_status()
        
        return spur.results.result(
            return_code,
            self._allow_error,
            output,
            stderr_output
        )


if sys.version_info[0] < 3:
    _iteritems = lambda d: d.iteritems()
else:
    _iteritems = lambda d: d.items()

########NEW FILE########
__FILENAME__ = tempdir
import contextlib
import tempfile
import shutil

@contextlib.contextmanager
def create_temporary_dir():
    dir = tempfile.mkdtemp()
    try:
        yield dir
    finally:
        shutil.rmtree(dir)

########NEW FILE########
__FILENAME__ = local_tests
import spur

from . import open_test_set, process_test_set


def _run_local_test(test_func):
    with spur.LocalShell() as shell:
        test_func(shell)


LocalOpenTests = open_test_set.create("LocalOpenTests", _run_local_test)
LocalProcessTests = process_test_set.create("LocalProcessTests", _run_local_test)

########NEW FILE########
__FILENAME__ = open_test_set
import uuid

from nose.tools import assert_equal

from nose_test_sets import TestSetBuilder


__all__ = ["create"]


test_set_builder = TestSetBuilder()

create = test_set_builder.create

test = test_set_builder.add_test


    
@test
def can_write_to_files_opened_by_open(shell):
    path = "/tmp/{0}".format(uuid.uuid4())
    f = shell.open(path, "w")
    try:
        f.write("hello")
        f.flush()
        assert_equal(b"hello", shell.run(["cat", path]).output)
    finally:
        f.close()
        shell.run(["rm", path])
        
@test
def can_read_files_opened_by_open(shell):
    path = "/tmp/{0}".format(uuid.uuid4())
    shell.run(["sh", "-c", "echo hello > '{0}'".format(path)])
    f = shell.open(path)
    try:
        assert_equal("hello\n", f.read())
    finally:
        f.close()
        shell.run(["rm", path])
        
@test
def open_can_be_used_as_context_manager(shell):
    path = "/tmp/{0}".format(uuid.uuid4())
    shell.run(["sh", "-c", "echo hello > '{0}'".format(path)])
    with shell.open(path) as f:
        assert_equal("hello\n", f.read())

########NEW FILE########
__FILENAME__ = process_test_set
# coding=utf8

import io
import time
import signal
import sys

from nose.tools import assert_equal, assert_not_equal, assert_raises, assert_true

import spur
from nose_test_sets import TestSetBuilder


__all__ = ["create"]


test_set_builder = TestSetBuilder()

create = test_set_builder.create

test = test_set_builder.add_test


@test
def output_of_run_is_stored(shell):
    result = shell.run(["echo", "hello"])
    assert_equal(b"hello\n", result.output)
    
@test
def output_is_not_truncated_when_not_ending_in_a_newline(shell):
    result = shell.run(["echo", "-n", "hello"])
    assert_equal(b"hello", result.output)
    
@test
def trailing_newlines_are_not_stripped_from_run_output(shell):
    result = shell.run(["echo", "\n\n"])
    assert_equal(b"\n\n\n", result.output)

@test
def stderr_output_of_run_is_stored(shell):
    result = shell.run(["sh", "-c", "echo hello 1>&2"])
    assert_equal(b"hello\n", result.stderr_output)
    
@test
def cwd_of_run_can_be_set(shell):
    result = shell.run(["pwd"], cwd="/")
    assert_equal(b"/\n", result.output)

@test
def environment_variables_can_be_added_for_run(shell):
    result = shell.run(["sh", "-c", "echo $NAME"], update_env={"NAME": "Bob"})
    assert_equal(b"Bob\n", result.output)

@test
def exception_is_raised_if_return_code_is_not_zero(shell):
    assert_raises(spur.RunProcessError, lambda: shell.run(["false"]))

@test
def exception_has_output_from_command(shell):
    try:
        shell.run(["sh", "-c", "echo Hello world!; false"])
        assert_true(False)
    except spur.RunProcessError as error:
        assert_equal(b"Hello world!\n", error.output)

@test
def exception_has_stderr_output_from_command(shell):
    try:
        shell.run(["sh", "-c", "echo Hello world! 1>&2; false"])
        assert_true(False)
    except spur.RunProcessError as error:
        assert_equal(b"Hello world!\n", error.stderr_output)

@test
def exception_message_contains_return_code_and_all_output(shell):
    try:
        shell.run(["sh", "-c", "echo starting; echo failed! 1>&2; exit 1"])
        assert_true(False)
    except spur.RunProcessError as error:
        assert_equal(
            """return code: 1\noutput: b'starting\\n'\nstderr output: b'failed!\\n'""",
            error.args[0]
        )

@test
def exception_message_shows_unicode_bytes(shell):
    try:
        shell.run(["sh", "-c", _u("echo ‽; exit 1")])
        assert_true(False)
    except spur.RunProcessError as error:
        assert_equal(
            """return code: 1\noutput: b'\\xe2\\x80\\xbd\\n'\nstderr output: b''""",
            error.args[0]
        )

@test
def return_code_stored_if_errors_allowed(shell):
    result = shell.run(["sh", "-c", "exit 14"], allow_error=True)
    assert_equal(14, result.return_code)

@test
def can_get_result_of_spawned_process(shell):
    process = shell.spawn(["echo", "hello"])
    result = process.wait_for_result()
    assert_equal(b"hello\n", result.output)
    
@test
def calling_wait_for_result_is_idempotent(shell):
    process = shell.spawn(["echo", "hello"])
    process.wait_for_result()
    result = process.wait_for_result()
    assert_equal(b"hello\n", result.output)
    
@test
def wait_for_result_raises_error_if_return_code_is_not_zero(shell):
    process = shell.spawn(["false"])
    assert_raises(spur.RunProcessError, process.wait_for_result)

@test
def can_write_to_stdin_of_spawned_processes(shell):
    process = shell.spawn(["sh", "-c", "read value; echo $value"])
    process.stdin_write(b"hello\n")
    result = process.wait_for_result()
    assert_equal(b"hello\n", result.output)

@test
def can_tell_if_spawned_process_is_running(shell):
    process = shell.spawn(["sh", "-c", "echo after; read dont_care; echo after"])
    assert_equal(True, process.is_running())
    process.stdin_write(b"\n")
    _wait_for_assertion(lambda: assert_equal(False, process.is_running()))
    
@test
def can_write_stdout_to_file_object_while_process_is_executing(shell):
    output_file = io.BytesIO()
    process = shell.spawn(
        ["sh", "-c", "echo hello; read dont_care;"],
        stdout=output_file
    )
    _wait_for_assertion(lambda: assert_equal(b"hello\n", output_file.getvalue()))
    assert process.is_running()
    process.stdin_write(b"\n")
    assert_equal(b"hello\n", process.wait_for_result().output)
    
@test
def can_write_stderr_to_file_object_while_process_is_executing(shell):
    output_file = io.BytesIO()
    process = shell.spawn(
        ["sh", "-c", "echo hello 1>&2; read dont_care;"],
        stderr=output_file
    )
    _wait_for_assertion(lambda: assert_equal(b"hello\n", output_file.getvalue()))
    assert process.is_running()
    process.stdin_write(b"\n")
    assert_equal(b"hello\n", process.wait_for_result().stderr_output)
        
@test
def can_get_process_id_of_process_if_store_pid_is_true(shell):
    process = shell.spawn(["sh", "-c", "echo $$"], store_pid=True)
    result = process.wait_for_result()
    assert_equal(int(result.output.strip()), process.pid)
    
@test
def process_id_is_not_available_if_store_pid_is_not_set(shell):
    process = shell.spawn(["sh", "-c", "echo $$"])
    assert not hasattr(process, "pid")
        
@test
def can_send_signal_to_process_if_store_pid_is_set(shell):
    process = shell.spawn(["cat"], store_pid=True)
    assert process.is_running()
    process.send_signal(signal.SIGTERM)
    _wait_for_assertion(lambda: assert_equal(False, process.is_running()))
    
    
@test
def spawning_non_existent_command_raises_specific_no_such_command_exception(shell):
    try:
        shell.spawn(["bin/i-am-not-a-command"])
        # Expected exception
        assert False
    except spur.NoSuchCommandError as error:
        assert_equal("No such command: bin/i-am-not-a-command", error.args[0])
        assert_equal("bin/i-am-not-a-command", error.command)


@test
def spawning_command_that_uses_path_env_variable_asks_if_command_is_installed(shell):
    try:
        shell.spawn(["i-am-not-a-command"])
        # Expected exception
        assert False
    except spur.NoSuchCommandError as error:
        expected_message = (
            "Command not found: i-am-not-a-command." +
            " Check that i-am-not-a-command is installed and on $PATH"
        )
        assert_equal(expected_message, error.args[0])
        assert_equal("i-am-not-a-command", error.command)


@test
def commands_are_run_without_pseudo_terminal_by_default(shell):
    result = shell.run(["bash", "-c", "[ -t 0 ]"], allow_error=True)
    assert_not_equal(0, result.return_code)
    

@test
def command_can_be_explicitly_run_with_pseudo_terminal(shell):
    result = shell.run(["bash", "-c", "[ -t 0 ]"], allow_error=True, use_pty=True)
    assert_equal(0, result.return_code)
    

@test
def output_is_captured_when_using_pty(shell):
    result = shell.run(["echo", "-n", "hello"], use_pty=True)
    assert_equal(b"hello", result.output)
    

@test
def stderr_is_redirected_stdout_when_using_pty(shell):
    result = shell.run(["sh", "-c", "echo -n hello 1>&2"], use_pty=True)
    assert_equal(b"hello", result.output)
    assert_equal(b"", result.stderr_output)
    

@test
def can_write_to_stdin_of_spawned_process_when_using_pty(shell):
    process = shell.spawn(["sh", "-c", "read value; echo $value"], use_pty=True)
    process.stdin_write(b"hello\n")
    result = process.wait_for_result()
    # Get the output twice since the pty echoes input
    assert_equal(b"hello\r\nhello\r\n", result.output)


# TODO: timeouts in wait_for_result

def _wait_for_assertion(assertion):
    timeout = 1
    period = 0.01
    start = time.time()
    while True:
        try:
            assertion()
            return
        except AssertionError:
            if time.time() - start > timeout:
                raise
            time.sleep(period)

def _u(b):
    if isinstance(b, bytes):
        return b.decode("utf8")
    else:
        return b

########NEW FILE########
__FILENAME__ = ssh_tests
from nose.tools import istest, assert_raises

import spur
import spur.ssh
from .testing import create_ssh_shell
from . import open_test_set, process_test_set


def _run_ssh_test(test_func):
    with create_ssh_shell() as shell:
        test_func(shell)
        
        
SshOpenTests = open_test_set.create("SshOpenTests", _run_ssh_test)
SshProcessTests = process_test_set.create("SshProcessTests", _run_ssh_test)


@istest
def attempting_to_connect_to_wrong_port_raises_connection_error():
    def try_connection():
        shell = _create_shell_with_wrong_port()
        shell.run(["echo", "hello"])
        
    assert_raises(spur.ssh.ConnectionError, try_connection)


@istest
def connection_error_contains_original_error():
    try:
        shell = _create_shell_with_wrong_port()
        shell.run(["true"])
        # Expected error
        assert False
    except spur.ssh.ConnectionError as error:
        assert isinstance(error.original_error, IOError)


@istest
def connection_error_contains_traceback_for_original_error():
    try:
        shell = _create_shell_with_wrong_port()
        shell.run(["true"])
        # Expected error
        assert False
    except spur.ssh.ConnectionError as error:
        assert "Traceback (most recent call last):" in error.original_traceback


@istest
def missing_host_key_set_to_accept_allows_connection_with_missing_host_key():
    with create_ssh_shell(missing_host_key=spur.ssh.MissingHostKey.accept) as shell:
        shell.run(["true"])


@istest
def missing_host_key_set_to_warn_allows_connection_with_missing_host_key():
    with create_ssh_shell(missing_host_key=spur.ssh.MissingHostKey.warn) as shell:
        shell.run(["true"])


@istest
def missing_host_key_set_to_raise_error_raises_error_when_missing_host_key():
    with create_ssh_shell(missing_host_key=spur.ssh.MissingHostKey.raise_error) as shell:
        assert_raises(spur.ssh.ConnectionError, lambda: shell.run(["true"]))
        

@istest
def trying_to_use_ssh_shell_after_exit_results_in_error():
    with create_ssh_shell() as shell:
        pass
        
    assert_raises(Exception, lambda: shell.run(["true"]))


def _create_shell_with_wrong_port():
    return spur.SshShell(
        username="bob",
        password="password1",
        hostname="localhost",
        port=54321,
        missing_host_key=spur.ssh.MissingHostKey.accept,
    )

########NEW FILE########
__FILENAME__ = testing
import os

import spur
import spur.ssh


def create_ssh_shell(missing_host_key=None):
    port_var = os.environ.get("TEST_SSH_PORT")
    port = int(port_var) if port_var is not None else None
    return spur.SshShell(
        hostname=os.environ.get("TEST_SSH_HOSTNAME", "127.0.0.1"),
        username=os.environ["TEST_SSH_USERNAME"],
        password=os.environ["TEST_SSH_PASSWORD"],
        port=port,
        missing_host_key=(missing_host_key or spur.ssh.MissingHostKey.accept),
    )

########NEW FILE########
