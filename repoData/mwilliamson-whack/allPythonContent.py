__FILENAME__ = args_test
import contextlib
import argparse
import os

from nose.tools import istest, assert_equal
import six

import whack.args

env_default = whack.args.env_default(prefix="WHACK")

@istest
def default_value_is_none_if_neither_environment_nor_cli_argument_is_set():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", action=env_default)
    args = parser.parse_args([])
    assert_equal(None, args.title)
    
@istest
def value_from_environment_is_used_if_cli_argument_not_set():
    with _updated_env({"WHACK_TITLE": "Hello!"}):
        parser = argparse.ArgumentParser()
        parser.add_argument("--title", action=env_default)
        args = parser.parse_args([])
    assert_equal("Hello!", args.title)
    
@istest
def value_from_environment_is_ignored_if_cli_argument_is_set():
    with _updated_env({"WHACK_TITLE": "Hello!"}):
        parser = argparse.ArgumentParser()
        parser.add_argument("--title", action=env_default)
        args = parser.parse_args(["--title", "Brilliant"])
    assert_equal("Brilliant", args.title)
    
@istest
def short_option_names_are_ignored_when_generating_environment_name():
    with _updated_env({"WHACK_TITLE": "Hello!"}):
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--title", action=env_default)
        args = parser.parse_args([])
    assert_equal("Hello!", args.title)
    
@istest
def additional_long_option_names_are_ignored_when_generating_environment_name():
    with _updated_env({"WHACK_THETITLE": "Hello!"}):
        parser = argparse.ArgumentParser()
        parser.add_argument("--title", "--thetitle", action=env_default)
        args = parser.parse_args([])
    assert_equal(None, args.title)
    
@istest
def hyphens_are_replaced_by_underscores_in_environment_variable_name():
    with _updated_env({"WHACK_THE_TITLE": "Hello!"}):
        parser = argparse.ArgumentParser()
        parser.add_argument("--the-title", action=env_default)
        args = parser.parse_args([])
    assert_equal("Hello!", args.the_title)


class Namespace(object):
    pass


@contextlib.contextmanager
def _updated_env(env):
    original_env = os.environ.copy()
    for key, value in six.iteritems(env):
        os.environ[key] = value
        
    yield
    
    for key in env:
        if key in original_env:
            os.environ[key] = original_env[value]
        else:
            del os.environ[key]

########NEW FILE########
__FILENAME__ = builder_tests
import contextlib
import json
import os

from nose.tools import istest, assert_equal
from catchy import NoCachingStrategy

from whack.tempdir import create_temporary_dir
from whack.files import sh_script_description, plain_file, read_file
from whack.sources import PackageSource
from whack.builder import Builder
from whack.packagerequests import create_package_request
from whack.errors import FileNotFoundError
from whack.downloads import Downloader
    

@istest
def build_uses_params_as_environment_variables_in_build():
    with _package_source("echo $VERSION > $1/version", {}) as package_source:
        with create_temporary_dir() as target_dir:
            build(create_package_request(package_source, {"version": "42"}), target_dir)
            assert_equal("42\n", read_file(os.path.join(target_dir, "version")))


@istest
def build_uses_default_value_for_param_if_param_not_explicitly_set():
    description = {"defaultParams": {"version": "42"}}
    with _package_source("echo $VERSION > $1/version", description) as package_source:
        with create_temporary_dir() as target_dir:
            build(create_package_request(package_source, {}), target_dir)
            assert_equal("42\n", read_file(os.path.join(target_dir, "version")))


@istest
def explicit_params_override_default_params():
    description = {"defaultParams": {"version": "42"}}
    with _package_source("echo $VERSION > $1/version", description) as package_source:
        with create_temporary_dir() as target_dir:
            build(create_package_request(package_source, {"version": "43"}), target_dir)
            assert_equal("43\n", read_file(os.path.join(target_dir, "version")))


@istest
def error_is_raised_if_build_script_is_missing():
    files = [
        plain_file("whack/whack.json", json.dumps({})),
    ]
    with create_temporary_dir(files) as package_source_dir:
        package_source = PackageSource.local(package_source_dir)
        request = create_package_request(package_source, {})
        with create_temporary_dir() as target_dir:
            assert_raises(
                FileNotFoundError,
                ("whack/build script not found in package source {0}".format(package_source_dir), ),
                lambda: build(request, target_dir),
            )

@contextlib.contextmanager
def _package_source(build_script, description):
    files = [
        plain_file("whack/whack.json", json.dumps(description)),
        sh_script_description("whack/build", build_script),
    ]
    with create_temporary_dir(files) as package_source_dir:
        yield PackageSource.local(package_source_dir)
        

def assert_raises(error_class, args, func):
    try:
        func()
        raise AssertionError("Expected exception {0}".format(error_class.__name__))
    except error_class as error:
        assert_equal(error.args, args)


def build(*args, **kwargs):
    cacher = NoCachingStrategy()
    builder = Builder(Downloader(cacher))
    return builder.build(*args, **kwargs)

########NEW FILE########
__FILENAME__ = deployer_tests
import os
import tempfile
import shutil

from nose.tools import istest, assert_equal

from whack.common import WHACK_ROOT
from whack.deployer import PackageDeployer
from whack.files import \
    write_files, sh_script_description, directory_description, plain_file, \
    symlink
from whack import local


@istest
def run_script_in_installation_mounts_whack_root_before_running_command():
    deployed_package = _deploy_package([
        plain_file("message", "Hello there"),
        sh_script_description("bin/hello", "cat {0}/message".format(WHACK_ROOT)),
    ])
    with deployed_package:
        command = [
            deployed_package.path("run"),
            deployed_package.path("bin/hello")
        ]
        _assert_output(command, b"Hello there")


@istest
def path_environment_variable_includes_bin_directory_under_whack_root():
    deployed_package = _deploy_package([
        sh_script_description("bin/hello", "echo Hello there"),
    ])
    with deployed_package:
        command = [deployed_package.path("run"), "hello"]
        _assert_output(command, b"Hello there\n")


@istest
def path_environment_variable_includes_sbin_directory_under_whack_root():
    deployed_package = _deploy_package([
        sh_script_description("sbin/hello", "echo Hello there"),
    ])
    with deployed_package:
        command = [deployed_package.path("run"), "hello"]
        _assert_output(command, b"Hello there\n")


@istest
def placing_executables_under_dot_bin_creates_directly_executable_files_under_bin():
    deployed_package = _deploy_package([
        plain_file("message", "Hello there"),
        sh_script_description(".bin/hello", "cat {0}/message".format(WHACK_ROOT)),
    ])
    with deployed_package:
        command = [deployed_package.path("bin/hello")]
        _assert_output(command, b"Hello there")
    
    
@istest
def placing_executables_under_dot_sbin_creates_directly_executable_files_under_sbin():
    deployed_package = _deploy_package([
        plain_file("message", "Hello there"),
        sh_script_description(".sbin/hello", "cat {0}/message".format(WHACK_ROOT)),
    ])
    with deployed_package:
        command = [deployed_package.path("sbin/hello")]
        _assert_output(command, b"Hello there")


@istest
def files_already_under_bin_are_not_replaced():
    deployed_package = _deploy_package([
        sh_script_description("bin/hello", "echo Hello from bin"),
        sh_script_description(".bin/hello", "echo Hello from .bin"),
    ])
    with deployed_package:
        command = [deployed_package.path("bin/hello")]
        _assert_output(command, b"Hello from bin\n")
    
    
@istest
def non_executable_files_under_dot_bin_are_not_created_in_bin():
    deployed_package = _deploy_package([
        plain_file(".bin/message", "Hello there"),
    ])
    with deployed_package:
        assert not os.path.exists(deployed_package.path("bin/message"))
    
    
@istest
def directories_under_dot_bin_are_not_created_in_bin():
    deployed_package = _deploy_package([
        directory_description(".bin/sub"),
    ])
    with deployed_package:
        assert not os.path.exists(deployed_package.path("bin/sub"))
    
    
@istest
def working_symlinks_in_dot_bin_to_files_under_whack_root_are_created_in_bin():
    deployed_package = _deploy_package([
        sh_script_description(".bin/hello", "echo Hello there"),
        symlink(".bin/hello-sym", os.path.join(WHACK_ROOT, ".bin/hello")),
        symlink(".bin/hello-borked", os.path.join(WHACK_ROOT, ".bin/hell")),
    ])
    with deployed_package:
        command = [deployed_package.path("bin/hello-sym")]
        _assert_output(command, b"Hello there\n")
        assert not os.path.exists(deployed_package.path("bin/hello-borked"))
    
    
@istest
def relative_symlinks_in_dot_bin_are_created_in_bin():
    deployed_package = _deploy_package([
        plain_file("message", "Hello there"),
        sh_script_description("sub/bin/hello", "cat {0}/message".format(WHACK_ROOT)),
        symlink(".bin", "sub/bin"),
    ])
    with deployed_package:
        command = [deployed_package.path("bin/hello")]
        _assert_output(command, b"Hello there")


@istest
def broken_symlinked_dot_bin_is_ignored():
    deployed_package = _deploy_package([
        sh_script_description("bin/hello", "echo Hello there"),
        symlink(".bin", "sub/binn"),
    ])
    with deployed_package:
        command = [deployed_package.path("bin/hello")]
        _assert_output(command, b"Hello there\n")


@istest
def placing_executables_under_symlinked_dot_bin_creates_directly_executable_files_under_bin():
    deployed_package = _deploy_package([
        plain_file("message", "Hello there"),
        sh_script_description("sub/bin/hello", "cat {0}/message".format(WHACK_ROOT)),
        symlink(".bin", os.path.join(WHACK_ROOT, "sub/bin")),
    ])
    with deployed_package:
        command = [deployed_package.path("bin/hello")]
        _assert_output(command, b"Hello there")


@istest
def whack_root_is_not_remounted_if_executing_scripts_under_whack_root():
    deployed_package = _deploy_package([
        sh_script_description(".bin/hello", "echo Hello there"),
        sh_script_description(".bin/hello2", "{0}/bin/hello".format(WHACK_ROOT)),
    ])
    with deployed_package:
        _add_echo_to_run_command(deployed_package)
        command = [deployed_package.path("bin/hello2")]
        _assert_output(command, b"Run!\nHello there\n")


@istest
def whack_root_is_remounted_if_in_different_whack_root():
    first_deployed_package = _deploy_package([
        plain_file("message", "Hello there"),
        sh_script_description(".bin/hello", "cat {0}/message".format(WHACK_ROOT)),
    ])
    with first_deployed_package:
        hello_path = first_deployed_package.path("bin/hello")
        second_deployed_package = _deploy_package([
            sh_script_description(".bin/hello2", "{0}".format(hello_path)),
        ])
        with second_deployed_package:
            _add_echo_to_run_command(first_deployed_package)
            _add_echo_to_run_command(second_deployed_package)
            command = [second_deployed_package.path("bin/hello2")]
            _assert_output(command, b"Run!\nRun!\nHello there")


def _add_echo_to_run_command(deployed_package):
    # This is a huge honking hack. I'm sorry.
    run_command_path = deployed_package.path("run")
    with open(run_command_path) as run_command_file:
        run_contents = run_command_file.read()
    run_contents = run_contents.replace("exec whack-run", "echo Run!; exec whack-run", 1)
    with open(run_command_path, "w") as run_command_file:
        run_command_file.write(run_contents)
    


def _deploy_package(file_descriptions):
    package_dir = tempfile.mkdtemp()
    try:
        write_files(package_dir, file_descriptions)
        deployer = PackageDeployer()
        deployer.deploy(package_dir)
        return DeployedPackage(package_dir)
    except:
        shutil.rmtree(package_dir)
        raise


def _assert_output(command, expected_output):
    output = local.run(command).output
    assert_equal(expected_output, output)


class DeployedPackage(object):
    def __init__(self, package_dir):
        self._package_dir = package_dir
        
    def path(self, path):
        return os.path.join(self._package_dir, path)
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        shutil.rmtree(self._package_dir)

########NEW FILE########
__FILENAME__ = downloads_test
import os

from nose.tools import istest, assert_equal
from catchy import NoCachingStrategy

from whack.downloads import read_downloads_string, Download, Downloader, DownloadError
from whack import files
from whack.tempdir import create_temporary_dir
from . import httpserver


@istest
def filename_of_download_uses_url_if_not_explicitly_set():
    download = Download("http://nginx.org/download/nginx-1.2.6.tar.gz")
    assert_equal("nginx-1.2.6.tar.gz", download.filename)

@istest
def empty_plain_text_file_has_no_downloads():
    assert_equal([], read_downloads_string(""))
    
@istest
def blank_lines_in_downloads_file_are_ignored():
    assert_equal([], read_downloads_string("\n\n   \n\n"))
    
@istest
def each_line_of_downloads_file_is_url_of_download():
    assert_equal(
        [Download("http://nginx.org/download/nginx-1.2.6.tar.gz")],
        read_downloads_string("http://nginx.org/download/nginx-1.2.6.tar.gz")
    )

@istest
def filename_can_be_explicitly_set_after_url():
    assert_equal(
        [Download("http://nginx.org/download/nginx-1.2.6.tar.gz", "nginx.tar.gz")],
        read_downloads_string("http://nginx.org/download/nginx-1.2.6.tar.gz nginx.tar.gz")
    )


@istest
def downloader_can_download_files_over_http():
    downloader = Downloader(NoCachingStrategy())
    
    with create_temporary_dir() as server_root:
        files.write_file(os.path.join(server_root, "hello"), "Hello there!")
        with httpserver.start_static_http_server(server_root) as http_server:
            with create_temporary_dir() as download_dir:
                download_path = os.path.join(download_dir, "file")
                url = http_server.static_url("hello")
                downloader.download(url, download_path)
                assert_equal("Hello there!", files.read_file(download_path))


@istest
def download_fails_if_http_request_returns_404():
    downloader = Downloader(NoCachingStrategy())
    
    with create_temporary_dir() as server_root:
        with httpserver.start_static_http_server(server_root) as http_server:
            with create_temporary_dir() as download_dir:
                download_path = os.path.join(download_dir, "file")
                url = http_server.static_url("hello")
                try:
                    downloader.download(url, download_path)
                    assert False
                except DownloadError as error:
                    pass

########NEW FILE########
__FILENAME__ = hashes_test
import os
import tempfile
import shutil
import uuid

import six
from nose.tools import istest, assert_equal, assert_not_equal

from whack.hashes import Hasher, integer_to_ascii


@istest
def hashing_the_same_single_value_gives_the_same_hash():
    def create_hash():
        hasher = Hasher()
        hasher.update("one")
        return hasher.ascii_digest()
    
    assert_equal(create_hash(), create_hash())

@istest
def hashing_multiple_values_in_the_same_order_gives_the_same_hash():
    def create_hash():
        hasher = Hasher()
        hasher.update("one")
        hasher.update("two")
        return hasher.ascii_digest()
    
    assert_equal(create_hash(), create_hash())
    
@istest
def hashing_multiple_values_in_different_order_gives_different_hash():
    first_hasher = Hasher()
    first_hasher.update("one")
    first_hasher.update("two")
    
    second_hasher = Hasher()
    second_hasher.update("two")
    second_hasher.update("one")
    
    assert_not_equal(first_hasher.ascii_digest(), second_hasher.ascii_digest())

@istest
def hash_of_directories_are_the_same_if_they_have_the_same_files():
    with TestRunner() as test_runner:
        first_hash = test_runner.hash_for_files({"hello": "Hello world!"})
        second_hash = test_runner.hash_for_files({"hello": "Hello world!"})
        
        assert_equal(first_hash, second_hash)
        
@istest
def hash_of_directories_are_different_if_they_have_different_file_names():
    with TestRunner() as test_runner:
        first_hash = test_runner.hash_for_files({"one": "Hello world!"})
        second_hash = test_runner.hash_for_files({"two": "Hello world!"})
        
        assert_not_equal(first_hash, second_hash)
        
@istest
def hash_of_directories_are_different_if_files_are_in_different_subdirectories():
    with TestRunner() as test_runner:
        first_hash = test_runner.hash_for_files({"one/hello": "Hello world!"})
        second_hash = test_runner.hash_for_files({"two/hello": "Hello world!"})
        
        assert_not_equal(first_hash, second_hash)
        
@istest
def hash_of_directories_are_different_if_they_have_different_file_contents():
    with TestRunner() as test_runner:
        first_hash = test_runner.hash_for_files({"hello": "Hello world!"})
        second_hash = test_runner.hash_for_files({"hello": "Goodbye world!"})
        
        assert_not_equal(first_hash, second_hash)


@istest
def integer_to_ascii_converts_integer_to_alphanumeric_string():
    cases = [
        (0, "0"),
        (4, "4"),
        (10, "a"),
        (35, "z"),
        (36, "10"),
        (1295, "zz"),
        (1296, "100"),
    ]
    
    for input_integer, expected_ascii in cases:
        assert_equal(integer_to_ascii(input_integer), expected_ascii)


class TestRunner(object):
    def __init__(self):
        self._test_dir = tempfile.mkdtemp()
    
    def hash_for_files(self, files):
        files_dir = self.create_files(files)
        
        hasher = Hasher()
        hasher.update_with_dir(files_dir)
        return hasher.ascii_digest()
    
    def create_files(self, files):
        root = os.path.join(self._test_dir, str(uuid.uuid4()))
        for name, contents in six.iteritems(files):
            path = os.path.join(root, name)
            parent_dir = os.path.dirname(path)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            open(path, "w").write(contents)
        return root
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        shutil.rmtree(self._test_dir)

########NEW FILE########
__FILENAME__ = httpserver
import threading

import starboard
from wsgiref.simple_server import make_server
from pyramid.config import Configurator

    
def start_static_http_server(root):
    port = starboard.find_local_free_tcp_port()
    config = Configurator()
    config.add_static_view('static', root, cache_max_age=3600)
    app = config.make_wsgi_app()
    
    server = make_server('0.0.0.0', port, app)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return Server(server, server_thread, root, port)


class Server(object):
    def __init__(self, server, thread, root, port):
        self.root = root
        self.port = port
        self._server = server
        self._thread = thread
    
    def static_url(self, path):
        return "http://localhost:{0}/static/{1}".format(self.port, path)
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self._server.shutdown()
        self._thread.join()

########NEW FILE########
__FILENAME__ = indexserver
import contextlib
import os
import shutil

from .httpserver import start_static_http_server
from whack.tempdir import create_temporary_dir
from whack.sources import create_source_tarball, PackageSource
from whack.files import write_file


@contextlib.contextmanager
def start_index_server():
    with create_temporary_dir() as server_root:
        with start_static_http_server(server_root) as http_server:
            yield IndexServer(http_server)
            
            
class IndexServer(object):
    def __init__(self, http_server):
        self._sources = []
        self._http_server = http_server
        self._root = http_server.root
        self._generate_index()
    
    def index_url(self):
        return self._http_server.static_url("packages.html")
        
    def add_source(self, source_dir):
        package_source = PackageSource.local(source_dir)
        source_tarball = create_source_tarball(package_source, self._root)
        source_filename = os.path.relpath(source_tarball.path, self._root)
        source_url = self._http_server.static_url(source_filename)
        self._sources.append((source_filename, source_url))
        self._generate_index()
        return source_tarball
        
    def add_package_tarball(self, package_tarball):
        package_filename = os.path.basename(package_tarball.path)
        server_path = os.path.join(self._root, package_filename)
        shutil.copyfile(package_tarball.path, server_path)
        package_url = self._http_server.static_url(package_filename)
        self._sources.append((package_filename, package_url))
        self._generate_index()
        
    def _generate_index(self):
        index_path = os.path.join(self._http_server.root, "packages.html")
        write_file(index_path, _html_for_index(self._sources))


def _html_for_index(packages):
    links = [
        '<a href="{0}">{1}</a>'.format(url, name)
        for name, url in packages
    ]
    return """
<!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
    {0}
  </body>
</html>
    """.format("".join(links))

########NEW FILE########
__FILENAME__ = indices_tests
from nose.tools import istest, assert_equal

from whack.indices import read_index_string
from whack.platform import Platform


@istest
def can_find_source_entry_if_link_text_is_exactly_desired_name():
    index = read_index_string(
        "http://example.com",
        _html('<a href="nginx.tar.gz">nginx.whack-source</a>')
    )
    index_entry = index.find_package_source_by_name("nginx")
    assert_equal("nginx.whack-source", index_entry.name)


@istest
def can_find_source_entry_if_href_is_exactly_desired_name():
    index = read_index_string(
        "http://example.com",
        _html('<a href="nginx.whack-source">n</a>')
    )
    index_entry = index.find_package_source_by_name("nginx")
    assert_equal("n", index_entry.name)


@istest
def can_find_source_entry_if_filename_of_href_is_exactly_desired_name():
    index = read_index_string(
        "http://example.com",
        _html('<a href="source/nginx.whack-source">n</a>')
    )
    index_entry = index.find_package_source_by_name("nginx")
    assert_equal("n", index_entry.name)


@istest
def find_by_name_returns_none_if_entry_cannot_be_found():
    index = read_index_string(
        "http://example.com",
        _html('<a href="nginx">nginx</a>')
    )
    index_entry = index.find_package_source_by_name("nginx")
    assert_equal(None, index_entry)


@istest
def empty_href_attributes_do_not_cause_error():
    index = read_index_string(
        "http://example.com",
        _html('<a href="">n</a>')
    )
    index_entry = index.find_package_source_by_name("nginx")
    assert_equal(None, index_entry)


@istest
def url_is_unchanged_if_href_is_absolute():
    index = read_index_string(
        "http://example.com",
        _html('<a href="http://example.net/nginx.whack-source">nginx.whack-source</a>')
    )
    index_entry = index.find_package_source_by_name("nginx")
    assert_equal("http://example.net/nginx.whack-source", index_entry.url)


@istest
def url_uses_domain_of_index_if_href_is_domain_relative():
    index = read_index_string(
        "http://example.com",
        _html('<a href="/nginx.whack-source">nginx.whack-source</a>')
    )
    index_entry = index.find_package_source_by_name("nginx")
    assert_equal("http://example.com/nginx.whack-source", index_entry.url)


@istest
def can_find_package_by_params_hash_and_platform():
    index = read_index_string(
        "http://example.com",
        _html('<a href="/nginx.whack-source">nginx_linux_x86-64_glibc-2.13_abc.whack-package</a>')
    )
    index_entry = index.find_package(params_hash="abc", platform=_platform)
    assert_equal("http://example.com/nginx.whack-source", index_entry.url)


@istest
def package_entry_is_not_match_if_os_does_not_match():
    index = read_index_string(
        "http://example.com",
        _html('<a href="/nginx.whack-source">nginx_cygwin_x86-64_glibc-2.13_abc.whack-package</a>')
    )
    index_entry = index.find_package(params_hash="abc", platform=_platform)
    assert_equal(None, index_entry)


@istest
def package_entry_is_not_match_if_architecture_does_not_match():
    index = read_index_string(
        "http://example.com",
        _html('<a href="/nginx.whack-source">nginx_linux_i686_glibc-2.13_abc.whack-package</a>')
    )
    index_entry = index.find_package(params_hash="abc", platform=_platform)
    assert_equal(None, index_entry)


@istest
def package_entry_is_not_match_if_libc_does_not_match():
    index = read_index_string(
        "http://example.com",
        _html('<a href="/nginx.whack-source">nginx_linux_x86-64_glibc-2.14_abc.whack-package</a>')
    )
    index_entry = index.find_package(params_hash="abc", platform=_platform)
    assert_equal(None, index_entry)


@istest
def earlier_glibc_can_be_used():
    index = read_index_string(
        "http://example.com",
        _html('<a href="/nginx.whack-source">nginx_linux_x86-64_glibc-2.12_abc.whack-package</a>')
    )
    index_entry = index.find_package(params_hash="abc", platform=_platform)
    assert_equal("nginx_linux_x86-64_glibc-2.12_abc.whack-package", index_entry.name)


@istest
def unrecognised_libc_requires_exact_match():
    index = read_index_string(
        "http://example.com",
        _html('<a href="/nginx.whack-source">nginx_linux_x86-64_xlibc-2.12_abc.whack-package</a>')
    )

    platform = Platform(
        os_name="linux",
        architecture="x86-64",
        libc="xlibc-2.13",
    )
    index_entry = index.find_package(params_hash="abc", platform=_platform)
    assert_equal(None, index_entry)


@istest
def package_entries_without_os_name_are_ignored():
    index = read_index_string(
        "http://example.com",
        _html('<a href="/nginx.whack-source">x86-64_xlibc-2.12_abc.whack-package</a>')
    )

    platform = Platform(
        os_name="linux",
        architecture="x86-64",
        libc="xlibc-2.13",
    )
    index_entry = index.find_package(params_hash="abc", platform=_platform)
    assert_equal(None, index_entry)


_platform = Platform(
    os_name="linux",
    architecture="x86-64",
    libc="glibc-2.13",
)


def _html(content):
    return """<!DOCTYPE html>
        <html>
        <head>
        </head>
        <body>
        {0}
        </body>
        </html>
    """.format(content)

########NEW FILE########
__FILENAME__ = operations_test
import os
import os.path
import contextlib

from nose.tools import istest, assert_equal

from whack.operations import Operations
from whack.sources import PackageSource
from whack.providers import create_package_provider
from whack.deployer import PackageDeployer
from . import testing
from whack.tempdir import create_temporary_dir
from whack.caching import NoCacheCachingFactory
from whack import local


test = istest


@test
def application_is_installed_by_running_build_with_install_dir_as_param():
    _BUILD = r"""#!/bin/sh
set -e
INSTALL_DIR=$1
mkdir -p $INSTALL_DIR/bin
cat > $INSTALL_DIR/bin/hello << EOF
#!/bin/sh
echo Hello there
EOF

chmod +x $INSTALL_DIR/bin/hello
"""
    with _temporary_install(_BUILD) as installation:
        output = _check_output(installation.install_path("bin/hello"))
        assert_equal(b"Hello there\n", output)


@test
def install_works_with_relative_path_for_install_dir():
    _BUILD = r"""#!/bin/sh
set -e
INSTALL_DIR=$1
mkdir -p $INSTALL_DIR/bin
cat > $INSTALL_DIR/bin/hello << EOF
#!/bin/sh
echo Hello there
EOF

chmod +x $INSTALL_DIR/bin/hello
"""

    with _temporary_package_source(_BUILD) as package_source_dir:
        with create_temporary_dir() as install_dir:
            with _change_dir(install_dir):
                _install(package_source_dir, ".")
    
            output = _check_output(os.path.join(install_dir, "bin/hello"))
            assert_equal(b"Hello there\n", output)
    

@test
def params_are_passed_as_uppercase_environment_variables_to_build_script():
    _BUILD = r"""#!/bin/sh
set -e
INSTALL_DIR=$1
mkdir -p $INSTALL_DIR/bin
cat > $INSTALL_DIR/bin/hello << EOF
#!/bin/sh
echo hello ${HELLO_VERSION}
EOF

chmod +x $INSTALL_DIR/bin/hello
"""
    with _temporary_install(_BUILD, params={"hello_version": 42}) as installation:
        output = _check_output(installation.install_path("bin/hello"))
    assert_equal(b"hello 42\n", output)


@test
def run_script_in_installation_mounts_whack_root_before_running_command():
    _BUILD = r"""#!/bin/sh
set -e
INSTALL_DIR=$1
mkdir -p $INSTALL_DIR/bin
echo 'Hello there' > $INSTALL_DIR/message
cat > $INSTALL_DIR/bin/hello << EOF
#!/bin/sh
cat $INSTALL_DIR/message
EOF

chmod +x $INSTALL_DIR/bin/hello
"""

    with _temporary_install(_BUILD) as installation:
        output = _check_output([
            installation.install_path("run"),
            installation.install_path("bin/hello"),
        ])
    assert_equal(b"Hello there\n", output)
    

@contextlib.contextmanager
def _temporary_install(build, params=None):
    with _temporary_package_source(build) as package_source_dir:
        with create_temporary_dir() as install_dir:
            _install(package_source_dir, install_dir, params=params)
            yield Installation(install_dir)


class SimplePackageSourceFetcher(object):
    def fetch(self, package_name):
        return PackageSource.local(package_name)


class Installation(object):
    def __init__(self, install_dir):
        self._install_dir = install_dir

    def install_path(self, path):
        return os.path.join(self._install_dir, path)


@contextlib.contextmanager
def _temporary_package_source(build):
    with create_temporary_dir() as package_source_dir:
        testing.write_package_source(package_source_dir, {"build": build})
        yield package_source_dir


def _install(*args, **kwargs):
    package_source_fetcher = SimplePackageSourceFetcher()
    package_provider = create_package_provider(NoCacheCachingFactory())
    deployer = PackageDeployer()
    operations = Operations(package_source_fetcher, package_provider, deployer)
    return operations.install(*args, **kwargs)


@contextlib.contextmanager
def _change_dir(new_dir):
    original_dir = os.getcwd()
    try:
        os.chdir(new_dir)
        yield
    finally:
        os.chdir(original_dir)


def _check_output(*args, **kwargs):
    return local.run(*args, **kwargs).output

########NEW FILE########
__FILENAME__ = packagerequests_tests
from nose.tools import istest, assert_equal

from whack.packagerequests import PackageRequest
from whack.sources import DictBackedPackageDescription


@istest
def package_source_is_passed_to_install_id_generator():
    package_source = PackageSource("/tmp/nginx-src", {})
    package_name_parts = _name_parts_for_package(package_source, {})
    assert_equal("install-id(/tmp/nginx-src, {})", package_name_parts[-1])


@istest
def params_are_passed_to_install_id_generator():
    package_source = PackageSource("/tmp/nginx-src", {})
    package_name_parts = _name_parts_for_package(package_source, {"version": "1.2"})
    assert_equal("install-id(/tmp/nginx-src, {'version': '1.2'})", package_name_parts[-1])
    

@istest
def first_name_part_is_name_of_package_if_present():
    package_source = PackageSource("/tmp/nginx-src", {"name": "nginx"})
    package_name_parts = _name_parts_for_package(package_source, {})
    assert_equal("nginx", package_name_parts[0])
    

@istest
def param_slug_is_included_if_present_in_description():
    description = {"name": "nginx", "paramSlug": "1.2"}
    package_source = PackageSource("/tmp/nginx-src", description)
    package_name_parts = _name_parts_for_package(package_source, {})
    assert_equal("1.2", package_name_parts[1])


@istest
def format_string_is_expanded_in_param_slug():
    description = {"name": "nginx", "paramSlug": "{nginx_version}"}
    package_source = PackageSource("/tmp/nginx-src", description)
    package_name_parts = _name_parts_for_package(package_source, {"nginx_version": "1.2"})
    assert_equal("1.2", package_name_parts[1])


@istest
def default_params_are_used_in_param_slug_if_param_not_explicitly_set():
    description = {
        "name": "nginx",
        "paramSlug": "{nginx_version}",
        "defaultParams": {"nginx_version": "1.2"},
    }
    package_source = PackageSource("/tmp/nginx-src", description)
    package_name_parts = _name_parts_for_package(package_source, {})
    assert_equal("1.2", package_name_parts[1])


def _name_parts_for_package(package_source, params):
    request = PackageRequest(package_source, params, _generate_install_id)
    return request.name().split("_")


def _generate_install_id(package_source, params):
    return "install-id({0}, {1})".format(package_source.path, params)


class PackageSource(object):
    def __init__(self, path, description):
        self.path = path
        self._description = description
        
    def name(self):
        return self.description().name()
        
    def description(self):
        return DictBackedPackageDescription(self._description)

########NEW FILE########
__FILENAME__ = platform_tests
from nose.tools import istest, assert_equal

from whack.platform import PlatformGenerator, Platform


@istest
def platform_os_name_is_lower_case_result_of_uname_kernel_name():
    platform = _generate_platform()
    assert_equal(platform.os_name, "linux")


@istest
def platform_architecture_is_derived_from_uname_machine():
    platform = _generate_platform()
    assert_equal(platform.architecture, "x86-64")


@istest
def libc_version_is_derived_from_getconf_gnu_libc_version():
    platform = _generate_platform()
    assert_equal(platform.libc, "glibc-2.13")


@istest
def can_use_other_glibc_if_minor_version_is_the_same():
    assert _platform_with_libc("glibc-2.13").can_use(_platform_with_libc("glibc-2.12"))


@istest
def can_use_other_glibc_if_minor_version_is_lower():
    assert _platform_with_libc("glibc-2.13").can_use(_platform_with_libc("glibc-2.12"))


@istest
def cannot_use_other_glibc_if_minor_version_is_higher():
    assert not _platform_with_libc("glibc-2.13").can_use(_platform_with_libc("glibc-2.14"))


@istest
def minor_version_comparison_is_numerical_rather_than_lexical():
    assert not _platform_with_libc("glibc-2.13").can_use(_platform_with_libc("glibc-2.101"))


@istest
def version_must_match_exactly_if_major_version_is_not_2():
    assert not _platform_with_libc("glibc-1.13").can_use(_platform_with_libc("glibc-1.12"))


@istest
def can_use_other_glibc_if_patch_version_is_the_same():
    assert _platform_with_libc("glibc-2.3.6").can_use(_platform_with_libc("glibc-2.3.6"))


@istest
def can_use_other_glibc_if_patch_version_is_lower():
    assert _platform_with_libc("glibc-2.3.5").can_use(_platform_with_libc("glibc-2.3.4"))


@istest
def cannot_use_other_glibc_if_patch_version_is_higher():
    assert not _platform_with_libc("glibc-2.3.5").can_use(_platform_with_libc("glibc-2.3.6"))


@istest
def patch_version_comparison_is_numerical_rather_than_lexical():
    assert not _platform_with_libc("glibc-2.3.5").can_use(_platform_with_libc("glibc-2.3.40"))


@istest
def minor_version_takes_precendence_over_patch_version():
    assert _platform_with_libc("glibc-2.3.5").can_use(_platform_with_libc("glibc-2.2.6"))
    assert not _platform_with_libc("glibc-2.2.6").can_use(_platform_with_libc("glibc-2.3.5"))


def _platform_with_libc(libc):
    return Platform(
        os_name="linux",
        architecture="x86-64",
        libc=libc,
    )


def _generate_platform():
    generator = PlatformGenerator(shell=Shell())
    return generator.platform()


class Shell(object):
    def __init__(self):
        self._results = {
            ("uname", "--kernel-name"): ExecutionResult(b"Linux\n"),
            ("uname", "--machine"): ExecutionResult(b"x86_64\n"),
            ("getconf", "GNU_LIBC_VERSION"): ExecutionResult(b"glibc 2.13"),
        }
        
    def run(self, command):
        return self._results[tuple(command)]


class ExecutionResult(object):
    def __init__(self, output):
        self.output = output

########NEW FILE########
__FILENAME__ = providers_test
import os
import os.path
import tempfile
import uuid

from nose.tools import istest, assert_equal

from whack.sources import PackageSource
from whack.providers import CachingPackageProvider
from catchy import DirectoryCacher
from whack.files import delete_dir
from whack.packagerequests import create_package_request
from whack.files import mkdir_p


@istest
class CachingProviderTests(object):
    def __init__(self):
        self._test_dir = tempfile.mkdtemp()
        self._cacher = DirectoryCacher(os.path.join(self._test_dir, "cache"))
        self._underlying_provider = FakeProvider()
        
    def teardown(self):
        delete_dir(self._test_dir)
        
    @istest
    def result_of_build_command_is_reused_when_no_params_are_set(self):
        self._get_package(params={})
        self._get_package(params={})
    
        assert_equal(1, self._number_of_builds())
        
    @istest
    def result_of_build_command_is_reused_when_params_are_the_same(self):
        self._get_package(params={"VERSION": "2.4"})
        self._get_package(params={"VERSION": "2.4"})
    
        assert_equal(1, self._number_of_builds())
        
    @istest
    def result_of_build_command_is_not_reused_when_params_are_not_the_same(self):
        self._get_package(params={"VERSION": "2.4"})
        self._get_package(params={"VERSION": "2.5"})
    
        assert_equal(2, self._number_of_builds())
    
    def _get_package(self, params):
        target_dir = os.path.join(self._test_dir, str(uuid.uuid4()))
        package_source_dir = os.path.join(self._test_dir, str(uuid.uuid4()))
        package_provider = CachingPackageProvider(
            cacher=self._cacher,
            underlying_provider=self._underlying_provider,
        )
        request = create_package_request(PackageSource.local(package_source_dir), params)
        package_provider.provide_package(request, target_dir)

    def _number_of_builds(self):
        return len(self._underlying_provider.requests)


class FakeProvider(object):
    def __init__(self):
        self.requests = []
    
    def provide_package(self, package_request, package_dir):
        mkdir_p(package_dir)
        self.requests.append(package_request)
        return True

########NEW FILE########
__FILENAME__ = sources_tests
import os
import subprocess
import json
import contextlib

from nose.tools import istest, assert_equal, assert_raises

from whack.sources import \
    PackageSourceFetcher, PackageSourceNotFound, SourceHashMismatch, \
    PackageSource, create_source_tarball
from whack.tempdir import create_temporary_dir
from whack.files import read_file, write_files, plain_file
from whack.tarballs import create_tarball
from whack.errors import FileNotFoundError
from .httpserver import start_static_http_server
from .indexserver import start_index_server


@istest
def can_fetch_package_source_from_source_control():
    def put_package_source_into_source_control(package_source_dir):
        _convert_to_git_repo(package_source_dir)
        return "git+file://{0}".format(package_source_dir)
        
    _assert_package_source_can_be_written_to_target_dir(
        put_package_source_into_source_control
    )


@istest
def can_fetch_package_source_from_local_dir():
    _assert_package_source_can_be_written_to_target_dir(
        lambda package_source_dir: package_source_dir
    )


@istest
def can_fetch_package_source_from_local_tarball():
    with create_temporary_dir() as temp_dir:
        def create_source(package_source_dir):
            tarball_path = os.path.join(temp_dir, "package.tar.gz")
            return create_tarball(tarball_path, package_source_dir)
        
        _assert_package_source_can_be_written_to_target_dir(create_source)


@istest
def can_fetch_package_source_from_tarball_on_http_server():
    with _temporary_static_server() as server:
        def create_source(package_source_dir):
            tarball_path = os.path.join(server.root, "package.tar.gz")
            create_tarball(tarball_path, package_source_dir)
            return server.static_url("package.tar.gz")
            
        _assert_package_source_can_be_written_to_target_dir(create_source)


@istest
def can_fetch_package_source_from_whack_source_uri():
    with _temporary_static_server() as server:
        def create_source(package_source_dir):
            package_source = PackageSource.local(package_source_dir)
            source_tarball = create_source_tarball(package_source, server.root)
            filename = os.path.relpath(source_tarball.path, server.root)
            return server.static_url(filename)
            
        _assert_package_source_can_be_written_to_target_dir(create_source)


@istest
def error_is_raised_if_hash_is_not_correct():
    with _temporary_static_server() as server:
        with _create_temporary_package_source_dir() as package_source_dir:
            tarball_path = os.path.join(server.root, "package-a452cd.whack-source")
            create_tarball(tarball_path, package_source_dir)
            package_uri = server.static_url("package-a452cd.whack-source")
            
            assert_raises(
                SourceHashMismatch,
                lambda: _fetch_source(package_uri)
            )


@istest
def can_fetch_package_source_using_url_from_html_index():
    with start_index_server() as index_server:
        
        def create_source(package_source_dir):
            source_tarball = index_server.add_source(package_source_dir)
            return source_tarball.full_name
            
        _assert_package_source_can_be_written_to_target_dir(
            create_source,
            indices=[index_server.index_url()]
        )
    

def _assert_package_source_can_be_written_to_target_dir(source_filter, indices=None):
    with _create_temporary_package_source_dir() as package_source_dir:
        package_source_name = source_filter(package_source_dir)
        
        with _fetch_source(package_source_name, indices) as package_source:
            with create_temporary_dir() as target_dir:
                package_source.write_to(target_dir)
                assert_equal(
                    "Bob",
                    read_file(os.path.join(target_dir, "whack/name"))
                )


@contextlib.contextmanager
def _create_temporary_package_source_dir():
    package_source_files = [plain_file("whack/name", "Bob")]
    with create_temporary_dir(package_source_files) as package_source_dir:
        yield package_source_dir


@istest
def writing_package_source_includes_files_specified_in_description():
    with create_temporary_dir() as package_source_dir:
        whack_description = {
            "sourcePaths": ["name"]
        }
        write_files(package_source_dir, [
            plain_file("whack/whack.json", json.dumps(whack_description)),
            plain_file("name", "Bob"),
        ])
        
        with _fetch_source(package_source_dir) as package_source:
            with create_temporary_dir() as target_dir:
                package_source.write_to(target_dir)
                assert_equal(
                    "Bob",
                    read_file(os.path.join(target_dir, "name"))
                )


@istest
def writing_package_source_includes_directories_specified_in_description():
    with create_temporary_dir() as package_source_dir:
        whack_description = {
            "sourcePaths": ["names"]
        }
        write_files(package_source_dir, [
            plain_file("whack/whack.json", json.dumps(whack_description)),
            plain_file("names/bob", "Bob"),
        ])
        
        with _fetch_source(package_source_dir) as package_source:
            with create_temporary_dir() as target_dir:
                package_source.write_to(target_dir)
                assert_equal(
                    "Bob",
                    read_file(os.path.join(target_dir, "names/bob"))
                )


@istest
def writing_source_raises_error_if_file_is_missing():
    with create_temporary_dir() as package_source_dir:
        whack_description = {
            "sourcePaths": ["name"]
        }
        write_files(package_source_dir, [
            plain_file("whack/whack.json", json.dumps(whack_description)),
        ])
        
        with _fetch_source(package_source_dir) as package_source:
            with create_temporary_dir() as target_dir:
                assert_raises(
                    FileNotFoundError,
                    lambda: package_source.write_to(target_dir)
                )


@istest
def error_is_raised_if_package_source_cannot_be_found():
    assert_raises(PackageSourceNotFound, lambda: _fetch_source("nginx/1"))
    

@istest
def name_is_stored_in_whack_json():
    with _source_package_with_description({"name": "nginx"}) as package_source:
        assert_equal("nginx", package_source.name())
    

@istest
def name_of_package_source_is_unknown_if_not_specified_in_whack_json():
    with _source_package_with_description({}) as package_source:
        assert_equal("unknown", package_source.name())
    

@istest
def name_of_package_source_is_unknown_if_whack_json_does_not_exist():
    with create_temporary_dir() as package_source_dir:
        package_source = PackageSource.local(package_source_dir)
        assert_equal("unknown", package_source.name())
    

@istest
def description_of_package_source_contains_param_slug():
    description = {"name": "nginx", "paramSlug": "$nginx_version"}
    with _source_package_with_description(description) as package_source:
        assert_equal("$nginx_version", package_source.description().param_slug())


def _convert_to_git_repo(cwd):
    def _git(command):
        subprocess.check_call(["git"] + command, cwd=cwd)
    _git(["init"])
    _git(["add", "."])
    _git(["commit", "-m", "Initial commit"])


def _fetch_source(package_source_uri, indices=None):
    source_fetcher = PackageSourceFetcher(indices=indices)
    return source_fetcher.fetch(package_source_uri)


@contextlib.contextmanager
def _temporary_static_server():
    with create_temporary_dir() as server_root:
        with start_static_http_server(server_root) as server:
            yield server


@contextlib.contextmanager
def _source_package_with_description(description):
    with create_temporary_dir() as package_source_dir:
        write_files(package_source_dir, [
            plain_file("whack/whack.json", json.dumps(description)),
        ])
        yield PackageSource.local(package_source_dir)

########NEW FILE########
__FILENAME__ = testing
import os
import os.path
import subprocess

import six

from whack.files import write_file


class HelloWorld(object):
    BUILD = r"""#!/bin/sh
set -e
cd $1

cat > hello << EOF
#!/bin/sh
echo Hello world!
EOF

chmod +x hello
    """

    EXPECTED_OUTPUT = b"Hello world!\n"

def write_package_source(package_dir, scripts):
    whack_dir = os.path.join(package_dir, "whack")
    os.makedirs(whack_dir)
    for name, contents in six.iteritems(scripts):
        _write_script(os.path.join(whack_dir, name), contents)

def _write_script(path, contents):
    write_file(path, contents)
    _make_executable(path)

def _make_executable(path):
    subprocess.check_call(["chmod", "u+x", path])

########NEW FILE########
__FILENAME__ = whack_cli_test
import os
import contextlib

from nose.tools import istest, assert_equal
import spur
import six

from whack import cli
from whack.sources import SourceTarball
from whack.errors import PackageNotAvailableError
from . import whack_test
from whack.operations import PackageTarball
from whack.testing import TestResult


@istest
def params_are_passed_to_install_command_as_dict():
    argv = [
        "whack", "install", "hello=1", "apps/hello",
        "-p", "version=1.2.4", "-p", "pcre_version=8.32"
    ]
    expected_params = {"version": "1.2.4", "pcre_version": "8.32"}
    _test_install_arg_parse(argv, params=expected_params)


@istest
def param_values_can_contain_equals_sign():
    argv = [
        "whack", "install", "hello=1", "apps/hello",
        "-p", "version_range===1.2.4"
    ]
    expected_params = {"version_range": "==1.2.4"}
    _test_install_arg_parse(argv, params=expected_params)
    
@istest
def param_without_equal_sign_has_value_of_empty_string():
    argv = [
        "whack", "install", "hello=1", "apps/hello",
        "-p", "verbose"
    ]
    expected_params = {"verbose": ""}
    _test_install_arg_parse(argv, params=expected_params)


def _test_install_arg_parse(argv, **expected_kwargs):
    args = cli.parse_args(argv)
    
    for key, value in six.iteritems(expected_kwargs):
        assert_equal(value, getattr(args, key))


class CliOperations(object):
    def __init__(self, indices=None, enable_build=True):
        self._indices = indices
        self._enable_build = enable_build
    
    def install(self, package_name, install_dir, params={}):
        self._command("install", package_name, install_dir, params)
        
    def get_package(self, package_name, target_dir, params={}):
        self._command("get-package", package_name, target_dir, params)
    
    def deploy(self, package_dir, target_dir=None):
        if target_dir is None:
            self._whack("deploy", package_dir, "--in-place")
        else:
            self._whack("deploy", package_dir, target_dir)
            
    def create_source_tarball(self, source_dir, tarball_dir):
        output = self._whack(
            "create-source-tarball",
            source_dir, tarball_dir,
        ).output
        full_name, path = output.strip().split("\n")
        return SourceTarball(full_name, path)
        
    def get_package_tarball(self, package_name, tarball_dir, params=None):
        output = self._whack(
            "get-package-tarball", package_name, tarball_dir, 
            *self._build_params_args(params)
        ).output
        return PackageTarball(output.strip())
        
    def test(self, source_name, params=None):
        try:
            self._whack("test", source_name, *self._build_params_args(params))
            return TestResult(passed=True)
        except spur.RunProcessError as process_error:
            return TestResult(passed=False)
    
    def _command(self, command_name, package_name, target_dir, params):
        params_args = self._build_params_args(params)
        try:
            self._whack(command_name, package_name, target_dir, *params_args)
        except spur.RunProcessError as process_error:
            package_not_available_prefix = "{0}:".format(
                PackageNotAvailableError.__name__
            )
            if process_error.stderr_output.decode("ascii").startswith(package_not_available_prefix):
                raise PackageNotAvailableError()
            else:
                raise
        
    def _whack(self, *args):
        local_shell = spur.LocalShell()
        indices_args = [
            "--add-index={0}".format(index)
            for index in (self._indices or [])
        ]
        extra_args = ["--disable-cache"] + indices_args
        if not self._enable_build:
            extra_args.append("--disable-build")
            
        result = local_shell.run(["whack"] + list(args) + extra_args)
        result.output = result.output.decode("ascii")
        return result
        
    def _build_params_args(self, params):
        return [
            "-p{0}={1}".format(key, value)
            for key, value in six.iteritems(params or {})
        ]
        
        


def _run_cli_operations_test(test_func):
    test_func(CliOperations)


WhackCliOperationsTest = whack_test.create(
    "WhackCliOperationsTest",
    _run_cli_operations_test,
)


@contextlib.contextmanager
def _updated_env(env):
    original_env = os.environ.copy()
    for key, value in six.iteritems(env):
        os.environ[key] = value
        
    yield
    
    for key in env:
        if key in original_env:
            os.environ[key] = original_env[value]
        else:
            del os.environ[key]

########NEW FILE########
__FILENAME__ = whack_test
import os
import functools
import contextlib
import json

import six
from nose.tools import assert_equal, assert_raises, nottest
from nose_test_sets import TestSetBuilder

from whack.common import WHACK_ROOT
from whack.errors import PackageNotAvailableError
import whack.operations
from whack.tempdir import create_temporary_dir
from whack.files import sh_script_description, plain_file, write_files
from . import testing
from .indexserver import start_index_server
from whack import local


test_set = TestSetBuilder()
create = test_set.create
test = test_set.add_test


@nottest
def test_with_operations(test_func):
    @test
    @functools.wraps(test_func)
    def run_test(create_operations):
        operations = create_operations()
        return test_func(operations)
    
    return run_test


@test_with_operations
def application_is_installed_by_running_build_script_and_copying_output(ops):
    test_install(
        ops,
        build=testing.HelloWorld.BUILD,
        params={},
        expected_output=testing.HelloWorld.EXPECTED_OUTPUT
    )


@test_with_operations
def params_are_passed_to_build_script_during_install(ops):
    _TEST_BUILDER_BUILD = r"""#!/bin/sh
set -e
cd $1
echo '#!/bin/sh' >> hello
echo echo ${VERSION} >> hello
chmod +x hello
"""

    test_install(
        ops,
        build=_TEST_BUILDER_BUILD,
        params={"version": "1"},
        expected_output=b"1\n"
    )


@test_with_operations
def getting_package_leaves_undeployed_build_in_target_directory(ops):
    with _package_source(testing.HelloWorld.BUILD) as package_source_dir:
        with create_temporary_dir() as target_dir:
            ops.get_package(package_source_dir, target_dir, params={})
        
            output = _check_output([os.path.join(target_dir, "hello")])
            assert_equal(testing.HelloWorld.EXPECTED_OUTPUT, output)
            assert not _is_deployed(target_dir)


@test_with_operations
def params_are_passed_to_build_script_during_get_package(ops):
    _TEST_BUILDER_BUILD = r"""#!/bin/sh
set -e
cd $1
echo '#!/bin/sh' >> hello
echo echo ${VERSION} >> hello
chmod +x hello
"""
    
    with _package_source(_TEST_BUILDER_BUILD) as package_source_dir:
        with create_temporary_dir() as target_dir:
            ops.get_package(package_source_dir, target_dir, params={"version": "1"})
        
            output = _check_output([os.path.join(target_dir, "hello")])
            assert_equal(b"1\n", output)


@test_with_operations
def built_package_can_be_deployed_to_different_directory(ops):
    package_files = [
        plain_file("message", "Hello there"),
        sh_script_description(".bin/hello", "cat {0}/message".format(WHACK_ROOT)),
    ]
    
    with create_temporary_dir(package_files) as package_dir:
        with create_temporary_dir() as install_dir:
            ops.deploy(package_dir, install_dir)
            output = _check_output([os.path.join(install_dir, "bin/hello")])
            assert_equal(b"Hello there", output)
            assert _is_deployed(install_dir)
            assert not _is_deployed(package_dir)
    


@test_with_operations
def directory_can_be_deployed_in_place(ops):
    package_files = [
        plain_file("message", "Hello there"),
        sh_script_description(".bin/hello", "cat {0}/message".format(WHACK_ROOT)),
    ]
    
    with create_temporary_dir(package_files) as package_dir:
        ops.deploy(package_dir)
        output = _check_output([os.path.join(package_dir, "bin/hello")])
        assert_equal(b"Hello there", output)
        assert _is_deployed(package_dir)


@test_with_operations
def source_tarballs_created_by_whack_can_be_installed(ops):
    with _package_source(testing.HelloWorld.BUILD) as package_source_dir:
        with create_temporary_dir() as tarball_dir:
            source_tarball = ops.create_source_tarball(
                package_source_dir,
                tarball_dir
            )
            with create_temporary_dir() as target_dir:
                ops.install(source_tarball.path, target_dir, params={})
            
                output = _check_output([os.path.join(target_dir, "hello")])
                assert_equal(testing.HelloWorld.EXPECTED_OUTPUT, output)


@test
def packages_can_be_installed_from_html_index(create_operations):
    with _package_source(testing.HelloWorld.BUILD) as package_source_dir:
        with start_index_server() as index_server:
            source = index_server.add_source(package_source_dir)
            with create_temporary_dir() as target_dir:
                operations = create_operations(indices=[index_server.index_url()])
                operations.install(source.full_name, target_dir, params={})
            
                output = _check_output([os.path.join(target_dir, "hello")])
                assert_equal(testing.HelloWorld.EXPECTED_OUTPUT, output)


@test
def error_is_raised_if_build_step_is_disabled_and_pre_built_package_cannot_be_found(create_operations):
    operations = create_operations(enable_build=False)
    with _package_source(testing.HelloWorld.BUILD) as package_source_dir:
        with create_temporary_dir() as target_dir:
            assert_raises(
                PackageNotAvailableError,
                lambda: operations.install(package_source_dir, target_dir)
            )


@test
def can_install_package_when_build_step_is_disabled_if_pre_built_package_can_be_found(create_operations):
    with _package_source(testing.HelloWorld.BUILD) as package_source_dir:
        with start_index_server() as index_server:
            indices = [index_server.index_url()]
            
            operations_for_build = create_operations(indices=indices)
            with create_temporary_dir() as temp_dir:
                package_tarball = operations_for_build.get_package_tarball(
                    package_source_dir,
                    temp_dir
                )
                index_server.add_package_tarball(package_tarball)
                
                with create_temporary_dir() as install_dir:
                    operations = create_operations(
                        enable_build=False,
                        indices=indices,
                    )
                    operations.install(package_source_dir, install_dir)
                
                    output = _check_output([
                        os.path.join(install_dir, "hello")
                    ])
                    assert_equal(testing.HelloWorld.EXPECTED_OUTPUT, output)
                

@test_with_operations
def whack_test_fails_if_test_is_not_set_in_whack_json(operations):
    source_files = [
        plain_file("whack/whack.json", json.dumps({})),
    ]
    with create_temporary_dir(source_files) as package_source_dir:
        test_result = operations.test(package_source_dir)
        assert_equal(False, test_result.passed)
                

@test_with_operations
def whack_test_fails_if_test_command_has_non_zero_return_code(operations):
    source_files = [
        plain_file("whack/whack.json", json.dumps({"test": "false"})),
    ]
    with create_temporary_dir(source_files) as package_source_dir:
        test_result = operations.test(package_source_dir)
        assert_equal(False, test_result.passed)
                

@test_with_operations
def whack_test_passes_if_test_command_has_zero_return_code(operations):
    source_files = [
        plain_file("whack/whack.json", json.dumps({"test": "true"})),
    ]
    with create_temporary_dir(source_files) as package_source_dir:
        test_result = operations.test(package_source_dir)
        assert_equal(True, test_result.passed)
                

@test_with_operations
def test_command_is_run_in_root_of_source_dir(operations):
    source_files = [
        plain_file("whack/whack.json", json.dumps({
            "test": "exit `cat zero || echo 1`",
            "sourcePaths": ["whack", "zero"],
        })),
        plain_file("zero", "0"),
    ]
    with create_temporary_dir(source_files) as package_source_dir:
        test_result = operations.test(package_source_dir)
        assert_equal(True, test_result.passed)
                

@test_with_operations
def parameters_are_passed_to_test_command_as_environment_variables(operations):
    source_files = [
        plain_file("whack/whack.json", json.dumps({
            "test": '[ "$VERSION" = "1" ]',
        })),
        plain_file("zero", "0"),
    ]
    with create_temporary_dir(source_files) as package_source_dir:
        test_result = operations.test(
            package_source_dir,
            params={"version": "1"}
        )
        assert_equal(True, test_result.passed)
        

@nottest
def test_install(ops, build, params, expected_output):
    with _package_source(build) as package_source_dir:
        with create_temporary_dir() as install_dir:
            ops.install(
                package_source_dir,
                install_dir,
                params=params,
            )
            
            output = _check_output([
                os.path.join(install_dir, "hello")
            ])
            assert_equal(expected_output, output)
            assert _is_deployed(install_dir)


def _run_test(test_func, caching_enabled):
    with _temporary_xdg_cache_dir():
        create_operations = functools.partial(
            whack.operations.create,
            caching_enabled
        )
        return test_func(create_operations)


def _is_deployed(package_dir):
    return os.path.exists(os.path.join(package_dir, "run"))


def _package_source(build):
    return create_temporary_dir([
        sh_script_description("whack/build", build),
    ])
    

def _check_output(*args, **kwargs):
    return local.run(*args, **kwargs).output


@contextlib.contextmanager
def _temporary_xdg_cache_dir():
    key = "XDG_CACHE_HOME"
    with create_temporary_dir() as cache_dir:
        with _updated_env({key: cache_dir}):
            yield


@contextlib.contextmanager
def _updated_env(env_updates):
    original_env = {}
    for key, updated_value in six.iteritems(env_updates):
        original_env[key] = os.environ.get(key)
    os.environ[key] = updated_value

    try:
        yield
    finally:
        for key, original_value in six.iteritems(original_env):
            if original_value is None:
                del os.environ[key]
            else:
                os.environ[key] = original_value


WhackNoCachingTests = test_set.create(
    "WhackNoCachingTests",
    functools.partial(_run_test, caching_enabled=False)
)


WhackCachingTests = test_set.create(
    "WhackCachingTests",
    functools.partial(_run_test, caching_enabled=True)
)

########NEW FILE########
__FILENAME__ = args
import argparse
import os

def env_default(prefix):
    class EnvDefault(argparse.Action):
        def __init__(self, required=False, **kwargs):
            option_string = self._find_long_option_string(kwargs["option_strings"])
            
            name = prefix + "_" + option_string[2:].upper().replace("-", "_")
            default = os.environ.get(name)
            
            if default is not None:
                required=False
                
            super(type(self), self).__init__(default=default, required=required, **kwargs)
        
        def _find_long_option_string(self, option_strings):
            for option_string in option_strings:
                if option_string.startswith("--"):
                    return option_string
        
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)
            
    return EnvDefault
            
    

########NEW FILE########
__FILENAME__ = builder
import os
import dodge

from .tempdir import create_temporary_dir
from .common import WHACK_ROOT
from .files import mkdir_p, write_file
from .errors import FileNotFoundError
from .env import params_to_env
from . import local


class Builder(object):
    def __init__(self, downloader):
        self._downloader = downloader
        
    def build(self, package_request, package_dir):
        with create_temporary_dir() as build_dir:
            self._build_in_dir(package_request, build_dir, package_dir)


    def _build_in_dir(self, package_request, build_dir, package_dir):
        params = package_request.params()
        
        package_request.write_source_to(build_dir)
        
        build_script = "whack/build"
        build_script_path = os.path.join(build_dir, build_script)
        if not os.path.exists(build_script_path):
            message = "{0} script not found in package source {1}".format(
                build_script, package_request.source_uri
            )
            raise FileNotFoundError(message)
        
        build_env = params_to_env(params)
        self._fetch_downloads(build_dir, build_env)
        mkdir_p(package_dir)
        build_command = [
            "whack-run",
            os.path.abspath(package_dir), # package_dir is mounted at WHACK_ROOT
            build_script_path, # build_script is executed
            WHACK_ROOT # WHACK_ROOT is passed as the first argument to build_script
        ]
        local.run(build_command, cwd=build_dir, update_env=build_env)
        write_file(
            os.path.join(package_dir, ".whack-package.json"),
            dodge.dumps(package_request.describe())
        )


    def _fetch_downloads(self, build_dir, build_env):
        downloads_file_path = os.path.join(build_dir, "whack/downloads")
        self._downloader.fetch_downloads(downloads_file_path, build_env, build_dir)

########NEW FILE########
__FILENAME__ = caching
import os

from catchy import xdg_directory_cacher, NoCachingStrategy


def create_cacher_factory(caching_enabled):
    if not caching_enabled:
        return NoCacheCachingFactory()
    else:
        return LocalCachingFactory()


class NoCacheCachingFactory(object):
    def create(self, name):
        return NoCachingStrategy()
        

class LocalCachingFactory(object):
    def create(self, name):
        return xdg_directory_cacher(os.path.join("whack", name))

########NEW FILE########
__FILENAME__ = cli
from __future__ import print_function

import argparse
import sys

import whack.args
from whack.errors import WhackUserError

env_default = whack.args.env_default(prefix="WHACK")


def main(argv, create_operations):
    args = parse_args(argv)
    operations = create_operations(
        caching_enabled=args.caching_enabled,
        indices=args.indices,
        enable_build=args.enable_build,
    )
    try:
        exit(args.func(operations, args))
    except WhackUserError as error:
        sys.stderr.write("{0}: {1}\n".format(type(error).__name__, error.message))
        exit(1)


def parse_args(argv):
    commands = [
        InstallCommand("install"),
        InstallCommand("get-package"),
        DeployCommand(),
        CreateSourceTarballCommand(),
        GetPackageTarballCommand(),
        TestCommand(),
    ]
    
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    
    for command in commands:
        subparser = subparsers.add_parser(command.name)
        _add_common_args(subparser)
        subparser.set_defaults(func=command.execute)
        command.create_parser(subparser)

    return parser.parse_args(argv[1:])


class KeyValueAction(argparse.Action):
    def __init__(self, default=None, **kwargs):
        if default is None:
            default = {}
            
        super(type(self), self).__init__(default=default, **kwargs)
    
    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, {})
        
        pairs = getattr(namespace, self.dest)
        if "=" in values:
            key, value = values.split("=", 1)
            pairs[key] = value
        else:
            pairs[values] = ""
        
        setattr(namespace, self.dest, pairs)


class InstallCommand(object):
    def __init__(self, name):
        self.name = name
    
    def create_parser(self, subparser):
        subparser.add_argument('package_source', metavar="package-source")
        subparser.add_argument('target_dir', metavar="target-dir")
        _add_build_params_args(subparser)
    
    def execute(self, operations, args):
        if self.name == "install":
            operation = operations.install
        elif self.name == "get-package":
            operation = operations.get_package
        else:
            raise Exception("Unrecognised operation")
            
        operation(args.package_source, args.target_dir, params=args.params)


class DeployCommand(object):
    name = "deploy"
    
    def create_parser(self, subparser):
        subparser.add_argument('package_dir', metavar="package-dir")
        
        target_group = subparser.add_mutually_exclusive_group(required=True)
        target_group.add_argument("--in-place", action="store_true")
        target_group.add_argument("target_dir", metavar="target-dir", nargs="?")

    def execute(self, operations, args):
        operations.deploy(args.package_dir, args.target_dir)


class CreateSourceTarballCommand(object):
    name = "create-source-tarball"
    
    def create_parser(self, subparser):
        subparser.add_argument('package_source', metavar="package-source")
        subparser.add_argument("source_tarball_dir", metavar="source-tarball-dir")
        
    def execute(self, operations, args):
        source_tarball = operations.create_source_tarball(
            args.package_source,
            args.source_tarball_dir
        )
        print(source_tarball.full_name)
        print(source_tarball.path)


class GetPackageTarballCommand(object):
    name = "get-package-tarball"
    
    def create_parser(self, subparser):
        subparser.add_argument("package")
        subparser.add_argument("package_tarball_dir", metavar="package-tarball-dir")
        _add_build_params_args(subparser)
        
    def execute(self, operations, args):
        package_tarball = operations.get_package_tarball(
            args.package,
            args.package_tarball_dir,
            params=args.params,
        )
        print(package_tarball.path)


class TestCommand(object):
    name = "test"
    
    def create_parser(self, subparser):
        subparser.add_argument('package_source', metavar="package-source")
        _add_build_params_args(subparser)
        
    def execute(self, operations, args):
        test_result = operations.test(args.package_source, params=args.params)
        if test_result.passed:
            return 0
        else:
            return 1


def _add_common_args(parser):
    _add_caching_args(parser)
    _add_index_args(parser)
    _add_build_args(parser)


def _add_caching_args(parser):
    parser.add_argument("--disable-cache", action="store_false", dest="caching_enabled")


def _add_index_args(parser):
    parser.add_argument(
        "--add-index",
        action="append",
        default=[],
        dest="indices",
        metavar="INDEX",
    )


def _add_build_args(parser):
    parser.add_argument("--disable-build", action="store_false", dest="enable_build")


def _add_build_params_args(parser):
    parser.add_argument(
        "--add-parameter", "-p",
        action=KeyValueAction,
        dest="params",
        metavar="KEY=VALUE",
    )

########NEW FILE########
__FILENAME__ = common
WHACK_ROOT = "/usr/local/whack"
SOURCE_URI_SUFFIX = ".whack-source"
PACKAGE_URI_SUFFIX = ".whack-package"

########NEW FILE########
__FILENAME__ = deployer
import os
import stat

from .common import WHACK_ROOT
from .files import copy_dir
from . import local


class PackageDeployer(object):
    def deploy(self, package_dir, target_dir=None):
        if target_dir is None:
            install_dir = package_dir
        else:
            install_dir = target_dir
            copy_dir(package_dir, install_dir)
        
        with open(os.path.join(install_dir, "run"), "w") as run_file:
            run_file.write(
                '#!/usr/bin/env sh\n\n' +
                'MY_ROOT=`readlink --canonicalize-missing "$(dirname $0)"`\n' +
                'if [ "$MY_ROOT" = "{0}" ]; then\n'.format(WHACK_ROOT) +
                '   exec "$@"\n' +
                'else\n' +
                '   PATH=$(dirname $0)/sbin:$(dirname $0)/bin:$PATH\n' +
                '   exec whack-run "$MY_ROOT" "$@"\n' +
                'fi\n'
            )
        local.run(["chmod", "+x", os.path.join(install_dir, "run")])
        
        _create_directly_executable_dir(install_dir, "bin")
        _create_directly_executable_dir(install_dir, "sbin")
        

def _create_directly_executable_dir(install_dir, bin_dir_name):
    def install_path(path):
        return os.path.join(install_dir, path)
    
    dot_bin_dir = install_path(".{0}".format(bin_dir_name))
    dot_bin_dir = _follow_symlinks_in_whack_root(install_dir, dot_bin_dir)
    bin_dir = install_path(bin_dir_name)
    if dot_bin_dir is not None and os.path.exists(dot_bin_dir):
        if not os.path.exists(bin_dir):
            os.mkdir(bin_dir)
        for bin_filename in _list_missing_executable_files(install_dir, dot_bin_dir, bin_dir):
            bin_file_path = os.path.join(bin_dir, bin_filename)
            with open(bin_file_path, "w") as bin_file:
                bin_file.write(
                    '#!/usr/bin/env sh\n\n' +
                    'MY_ROOT=`readlink --canonicalize-missing "$(dirname $0)/.."`\n' +
                    'TARGET="{0}/.{1}/{2}"\n'.format(WHACK_ROOT, bin_dir_name, bin_filename) +
                    'exec "$MY_ROOT/run" "$TARGET" "$@"\n'
                )
            os.chmod(bin_file_path, 0o755)

def _list_missing_executable_files(root_dir, dot_bin_dir, bin_dir):
    def is_missing(filename):
        return not os.path.exists(os.path.join(bin_dir, filename))
    return filter(is_missing, _list_executable_files(root_dir, dot_bin_dir))


def _list_executable_files(root_dir, dir_path):
    def is_executable_file(filename):
        path = os.path.join(dir_path, filename)
        return _is_executable_file_in_whack_root(root_dir, path)
            
    return filter(is_executable_file, os.listdir(dir_path))


def _is_executable_file_in_whack_root(root_dir, path):
    path = _follow_symlinks_in_whack_root(root_dir, path)
    
    if path is not None and os.path.exists(path):
        is_executable = stat.S_IXUSR & os.stat(path)[stat.ST_MODE]
        return not os.path.isdir(path) and is_executable
    else:
        return False


def _follow_symlinks_in_whack_root(root_dir, path):
    while os.path.islink(path):
        link_target = os.path.join(os.path.dirname(path), os.readlink(path))
        if os.path.exists(link_target):
            # Valid symlink
            path = link_target
        elif link_target.startswith("{0}/".format(WHACK_ROOT)):
            # Valid symlink, but whack root isn't mounted
            path = os.path.join(root_dir, link_target[len(WHACK_ROOT) + 1:])
        else:
            # Broken symlink
            return None
            
    return path

########NEW FILE########
__FILENAME__ = downloads
import os.path
import hashlib
import re
from six.moves.urllib.parse import urlparse

from .tempdir import create_temporary_dir
from .files import mkdir_p, copy_file
from . import local


class DownloadError(Exception):
    pass


class Downloader(object):
    def __init__(self, cacher):
        self._cacher = cacher
    
    def fetch_downloads(self, downloads_file_path, build_env, target_dir):
        downloads_file = _read_downloads_file(downloads_file_path, build_env)
        for download_line in downloads_file:
            self.download(
                download_line.url,
                os.path.join(target_dir, download_line.filename)
            )

    def download(self, url, destination):
        url_hash = hashlib.sha1(url.encode("utf8")).hexdigest()
        mkdir_p(os.path.dirname(destination))
        cache_result = self._cacher.fetch(url_hash, destination)
        if cache_result.cache_hit:
            return
        else:
            # TODO: writing directly to the cache would be quicker
            # Don't write directly to the destination to avoid any possible
            # modification
            with create_temporary_dir() as temp_dir:
                temp_file_path = os.path.join(temp_dir, url_hash)
                try:
                    local.run(["curl", url, "--output", temp_file_path, "--location", "--fail"])
                except local.RunProcessError as error:
                    if error.return_code == 22: # 404
                        raise DownloadError("File not found: {0}".format(url))
                    else:
                        raise
                    
                copy_file(temp_file_path, destination)
                self._cacher.put(url_hash, temp_file_path)
        

class Download(object):
    def __init__(self, url, filename=None):
        self.url = url
        self.filename = filename or _filename_from_url(url)
        
    def __eq__(self, other):
        return (self.url, self.filename) == (other.url, other.filename)
        
    def __neq__(self, other):
        return not (self == other)
        
    def __repr__(self):
        return "Download({0!r}, {1!r})".format(self.url, self.filename)


def _read_downloads_file(path, build_env):
    if os.path.exists(path):
        with open(path) as f:
            first_line = f.readline()
        if first_line.startswith("#!"):
            downloads_string = local.run([path], update_env=build_env).output
        else:
            with open(path) as f:
                downloads_string = f.read()
            
        return read_downloads_string(downloads_string)
    else:
        return []


def read_downloads_string(downloads_string):
    return [
        _read_download_line(line.strip())
        for line in downloads_string.split("\n")
        if line.strip()
    ]

def _read_download_line(line):
    result = re.match("^(\S+)\s+(.+)$", line)
    if result:
        return Download(result.group(1), result.group(2))
    else:
        return Download(line)
    

def _filename_from_url(url):
    return urlparse(url).path.rpartition("/")[2]

########NEW FILE########
__FILENAME__ = env
import six


def params_to_env(params):
    return dict(
        (name.upper(), str(value))
        for name, value in six.iteritems(params or {})
    )


########NEW FILE########
__FILENAME__ = errors
class WhackUserError(Exception):
    def __init__(self, message=None):
        Exception.__init__(self, message)
        self.message = message


class FileNotFoundError(WhackUserError):
    pass


class PackageNotAvailableError(WhackUserError):
    pass

########NEW FILE########
__FILENAME__ = files
import os
import errno
import shutil

from . import local


def read_file(path):
    with open(path) as f:
        return f.read()
        

def write_file(path, contents):
    with open(path, "w") as f:
        f.write(contents)


copy_file = shutil.copyfile


def copy_dir(source, destination):
    # TODO: should be pure Python, but there isn't a stdlib function
    # that allows the destination to already exist
    local.run(["cp", "-rT", source, destination])


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as error:
        if not (error.errno == errno.EEXIST and os.path.isdir(path)):
            raise


def delete_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def write_files(root_dir, file_descriptions):
    for file_description in file_descriptions:
        path = os.path.join(root_dir, file_description.path)
        if file_description.file_type == "dir":
            mkdir_p(path)
        elif file_description.file_type == "file":
            mkdir_p(os.path.dirname(path))
            write_file(path, file_description.contents)
            os.chmod(path, file_description.permissions)
        elif file_description.file_type == "symlink":
            os.symlink(file_description.contents, path)


def sh_script_description(path, contents):
    return FileDescription(path, "#!/bin/sh\n{0}".format(contents), 0o755, "file")


def directory_description(path):
    return FileDescription(path, None, permissions=None, file_type="dir")


def plain_file(path, contents):
    return FileDescription(path, contents, permissions=0o644, file_type="file")


def symlink(path, actual_path):
    return FileDescription(path, actual_path, permissions=None, file_type="symlink")


class FileDescription(object):
    def __init__(self, path, contents, permissions, file_type):
        self.path = path
        self.contents = contents
        self.permissions = permissions
        self.file_type = file_type

########NEW FILE########
__FILENAME__ = hashes
import os
import hashlib


class Hasher(object):
    def __init__(self):
        self._hash = hashlib.sha1()
    
    def update(self, arg):
        self._hash.update(_sha1(arg))
    
    def update_with_dir(self, dir_path):
        for file_path in _all_files(dir_path):
            self.update(os.path.relpath(file_path, dir_path))
            self.update(open(file_path).read())
    
    def ascii_digest(self):
        return integer_to_ascii(int(self._hash.hexdigest(), 16))


def integer_to_ascii(value):
    characters = "0123456789abcdefghijklmnopqrstuvwxyz"
    
    if value == 0:
        return characters[0]
    
    output = []
    remaining_value = value
    while remaining_value > 0:
        output.append(characters[remaining_value % len(characters)])
        remaining_value = remaining_value // len(characters)
    
    
    return "".join(reversed(output))


def _all_files(top):
    all_files = []
    
    for root, dirs, files in os.walk(top):
        for name in files:
            all_files.append(os.path.join(root, name))
    
    return sorted(all_files)
    

def _sha1(value):
    if not isinstance(value, bytes):
        value = value.encode("utf8")

    return hashlib.sha1(value).digest()

########NEW FILE########
__FILENAME__ = indices
from six.moves.urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import dodge

from .common import SOURCE_URI_SUFFIX, PACKAGE_URI_SUFFIX
from . import slugs
from .platform import Platform
from . import lists


def read_index(index_uri):
    index_response = requests.get(index_uri)
    if index_response.status_code != 200:
        # TODO: should we log and carry on? Definitely shouldn't swallow
        # silently
        raise Exception("Index {0} returned status code {1}".format(
            index_uri, index_response.status_code
        ))
    return read_index_string(index_uri, index_response.text)
    
    
def read_index_string(index_url, index_string):
    html_document = BeautifulSoup(index_string)
    
    def link_to_index_entry(link):
        url = urljoin(index_url, link.get("href"))
        link_text = link.get_text().strip()
        return IndexEntry(link_text, url)
    
    return Index(lists.map(link_to_index_entry, html_document.find_all("a")))
    

class Index(object):
    def __init__(self, entries):
        self._entries = entries
    
    def find_package_source_by_name(self, name):
        package_source_filename = name + SOURCE_URI_SUFFIX
        return self._find_by_name(package_source_filename)
        
    def find_package(self, params_hash, platform):
        def _is_package(entry_name):
            if entry_name.endswith(PACKAGE_URI_SUFFIX):
                package_name = entry_name[:-len(PACKAGE_URI_SUFFIX)]
                parts = slugs.split(package_name)
                if len(parts) < 4:
                    return False
                else:
                    entry_params_hash = parts[-1]
                    entry_platform = parts[-4:-1]
                    return (
                        entry_params_hash == params_hash and
                        platform.can_use(Platform.load_list(entry_platform))
                    )
            else:
                return False
        
        return self._find(_is_package)
    
    def _find_by_name(self, name):
        return self._find(lambda entry_name: entry_name == name)
        
    def _find(self, predicate):
        for entry in self._entries:
            print(entry.name)
            if predicate(entry.name):
                return entry
                
        for entry in self._entries:
            url_parts = entry.url.rsplit("/", 1)
            print(url_parts[-1])
            if predicate(url_parts[-1]):
                return entry
                
        return None


class IndexEntry(object):
    def __init__(self, name, url):
        self.name = name
        self.url = url

########NEW FILE########
__FILENAME__ = lists
import six

__all__ = ["map"]


_map = map

if six.PY3:
    def map(*args, **kwargs):
        return list(_map(*args, **kwargs))
else:
    map = _map

########NEW FILE########
__FILENAME__ = local
import spur


__all__ = ["run", "RunProcessError"]


local_shell = spur.LocalShell()

run = local_shell.run

RunProcessError = spur.RunProcessError

########NEW FILE########
__FILENAME__ = operations
import os
import sys

import dodge

from .sources import PackageSourceFetcher, create_source_tarball
from .providers import create_package_provider
from .deployer import PackageDeployer
from .tempdir import create_temporary_dir
from .files import read_file
from .tarballs import create_tarball
from .packagerequests import create_package_request, PackageDescription
from .caching import create_cacher_factory
from .testing import TestResult
from .env import params_to_env
from . import local
from .errors import PackageNotAvailableError


def create(caching_enabled, indices=None, enable_build=True):
    cacher_factory = create_cacher_factory(caching_enabled=caching_enabled)
    
    package_source_fetcher = PackageSourceFetcher(indices)
    package_provider = create_package_provider(
        cacher_factory,
        enable_build=enable_build,
        indices=indices,
    )
    deployer = PackageDeployer()
    
    return Operations(package_source_fetcher, package_provider, deployer)


class Operations(object):
    def __init__(self, package_source_fetcher, package_provider, deployer):
        self._package_source_fetcher = package_source_fetcher
        self._package_provider = package_provider
        self._deployer = deployer
        
    def install(self, source_name, install_dir, params=None):
        self.get_package(source_name, install_dir, params)
        self.deploy(install_dir)
        
    def get_package(self, source_name, install_dir, params=None):
        with self._package_source_fetcher.fetch(source_name) as package_source:
            request = create_package_request(package_source, params)
            if not self._package_provider.provide_package(request, install_dir):
                raise PackageNotAvailableError()
        
    def deploy(self, package_dir, target_dir=None):
        return self._deployer.deploy(package_dir, target_dir)
        
    def create_source_tarball(self, source_name, tarball_dir):
        with self._package_source_fetcher.fetch(source_name) as package_source:
            return create_source_tarball(package_source, tarball_dir)
        
    def get_package_tarball(self, package_name, tarball_dir, params=None):
        with create_temporary_dir() as package_dir:
            self.get_package(package_name, package_dir, params=params)
            package_description = dodge.loads(
                read_file(os.path.join(package_dir, ".whack-package.json")),
                PackageDescription
            )
            package_name = package_description.name
            package_filename = "{0}.whack-package".format(package_name)
            package_tarball_path = os.path.join(tarball_dir, package_filename)
            create_tarball(package_tarball_path, package_dir, rename_dir=package_name)
            return PackageTarball(package_tarball_path)
            
    def test(self, source_name, params=None):
        with self._package_source_fetcher.fetch(source_name) as package_source:
            description = package_source.description()
            test_command = description.test_command()
            if test_command is None:
                return TestResult(passed=False)
            else:
                return_code = local.run(
                    ["sh", "-c", test_command],
                    cwd=package_source.path,
                    update_env=params_to_env(params),
                    allow_error=True,
                    stdout=sys.stderr,
                    stderr=sys.stderr,
                ).return_code
                passed = return_code == 0
                return TestResult(passed=passed)


class PackageTarball(object):
    def __init__(self, path):
        self.path = path

########NEW FILE########
__FILENAME__ = packagerequests
import json

import dodge

from .hashes import Hasher
from . import local
from .platform import generate_platform, Platform
from . import slugs


def create_package_request(package_source, params=None):
    return PackageRequest(package_source, params)
    

class PackageRequest(object):
    def __init__(self, package_source, params=None, generate_package_hash=None):
        if params is None:
            params = {}
        if generate_package_hash is None:
            generate_package_hash = _generate_install_id_using_hash
            
        self._package_source = package_source
        self._params = params
        self._generate_package_hash = generate_package_hash
    
    @property
    def source_uri(self):
        return self._package_source.uri
    
    def write_source_to(self, *args, **kwargs):
        return self._package_source.write_to(*args, **kwargs)
    
    def params(self):
        default_params = self._package_source.description().default_params()
        params = default_params.copy()
        params.update(self._params)
        return params
        
    def params_hash(self):
        return self._generate_package_hash(self._package_source, self.params())
    
    def platform(self):
        return generate_platform()
    
    def _name_parts(self):
        params = self.params()
        source_name = self._package_source.name()
        
        param_slug = self._package_source.description().param_slug()
        param_part = self._generate_param_part(param_slug, params) or ""
        
        platform = self.platform()
        
        install_id = self.params_hash()
        
        return [source_name, param_part, platform.dumps(), install_id]
    
    def name(self):
        return slugs.join(self._name_parts())
        
    def describe(self):
        return PackageDescription(
            name=self.name(),
            source_name=self._package_source.name(),
            source_hash=self._package_source.source_hash(),
            params=self.params(),
            platform=generate_platform(),
        )
        
    def _generate_param_part(self, slug, params):
        if slug is None:
            return None
        else:
            return slug.format(**params)


def _generate_install_id_using_hash(package_source, params):
    hasher = Hasher()
    hasher.update(package_source.source_hash())
    hasher.update(json.dumps(params, sort_keys=True))
    return hasher.ascii_digest()


def _uname(arg):
    return local.run(["uname", arg]).output


PackageDescription = dodge.data_class("PackageDescription", [
    "name",
    "source_name",
    "source_hash",
    "params",
    dodge.field("platform", type=Platform),
])

########NEW FILE########
__FILENAME__ = platform
import re

import dodge

from .local import local_shell
from . import slugs


def generate_platform():
    generator = PlatformGenerator(local_shell)
    return generator.platform()


class PlatformGenerator(object):
    def __init__(self, shell):
        self._shell = shell
        
    def platform(self):
        os_name = self._uname("--kernel-name")
        architecture = self._uname("--machine")
        libc = self._run(["getconf", "GNU_LIBC_VERSION"])
        return Platform(os_name=os_name, architecture=architecture, libc=libc)
        
    def _uname(self, *args):
        return self._run(["uname"] + list(args))
        
    def _run(self, command):
        output =  self._shell.run(command).output.decode("ascii")
        return output.strip().lower().replace("_", "-").replace(" ", "-")


Platform = dodge.data_class("Platform", ["os_name", "architecture", "libc"])

Platform.dumps = lambda self: slugs.join(dodge.obj_to_flat_list(self))

Platform.load_list = staticmethod(lambda values: dodge.flat_list_to_obj(values, Platform))

def _platform_can_use(self, other):
    return (
        self.os_name == other.os_name and
        self.architecture == other.architecture and
        _libc_can_use(self.libc, other.libc)
    )
    
    
def _libc_can_use(first, second):
    first_version, second_version = map(_glibc_version, (first, second))
    if first_version is None or second_version is None:
        return first == second
    else:
        return first_version >= second_version
    

def _glibc_version(libc):
    result = re.match("^glibc-2.([0-9]+)(?:.([0-9]+))?$", libc)
    if result:
        if result.group(2) is None:
            patch_version = 0
        else:
            patch_version = int(result.group(2))
        return (int(result.group(1)), patch_version)
    else:
        return None


Platform.can_use = _platform_can_use

########NEW FILE########
__FILENAME__ = providers
from .builder import Builder
from .tarballs import extract_tarball
from .indices import read_index
from .downloads import Downloader
from . import lists


def create_package_provider(cacher_factory, enable_build=True, indices=None):
    if indices is None:
        indices = []
    
    underlying_providers = lists.map(IndexPackageProvider, indices)
    if enable_build:
        downloader = Downloader(cacher_factory.create("downloads"))
        underlying_providers.append(BuildingPackageProvider(Builder(downloader)))
    return CachingPackageProvider(
        cacher_factory.create("packages"),
        MultiplePackageProviders(underlying_providers),
    )


class IndexPackageProvider(object):
    def __init__(self, index_uri):
        self._index_uri = index_uri
        
    def provide_package(self, package_request, package_dir):
        index = read_index(self._index_uri)
        package_entry = index.find_package(package_request.params_hash(), package_request.platform())
        if package_entry is None:
            return None
        else:
            self._fetch_and_extract(package_entry.url, package_dir)
            return True
        
    def _fetch_and_extract(self, url, package_dir):
        extract_tarball(url, package_dir, strip_components=1)
        
        
class MultiplePackageProviders(object):
    def __init__(self, providers):
        self._providers = providers
        
    def provide_package(self, package_request, package_dir):
        for underlying_provider in self._providers:
            package = underlying_provider.provide_package(package_request, package_dir)
            if package:
                return package
        
        return None
        

class BuildingPackageProvider(object):
    def __init__(self, builder):
        self._builder = builder
    
    def provide_package(self, package_request, package_dir):
        self._builder.build(package_request, package_dir)
        return True


class CachingPackageProvider(object):
    def __init__(self, cacher, underlying_provider):
        self._cacher = cacher
        self._underlying_provider = underlying_provider
    
    def provide_package(self, package_request, package_dir):
        package_name = package_request.name()
        result = self._cacher.fetch(package_name, package_dir)
        
        if result.cache_hit:
            return True
        else:
            package = self._underlying_provider.provide_package(package_request, package_dir)
            if package:
                self._cacher.put(package_name, package_dir)
            return package

########NEW FILE########
__FILENAME__ = slugs
def join(parts):
    for part in parts:
        if part is None:
            raise ValueError("part is None")
            
    return "_".join(part for part in parts)


def split(string):
    return string.split("_")

########NEW FILE########
__FILENAME__ = sources
import os
import json
import tempfile
import uuid
import re
import errno

import mayo

from .hashes import Hasher
from .files import copy_dir, copy_file, delete_dir
from .tarballs import extract_tarball, create_tarball
from .indices import read_index
from .errors import FileNotFoundError, WhackUserError
from .tempdir import create_temporary_dir
from .uris import is_local_path, is_http_uri
from . import slugs
from .common import SOURCE_URI_SUFFIX
from . import lists


class PackageSourceNotFound(WhackUserError):
    def __init__(self, source_name):
        message = "Could not find package source: {0}".format(source_name)
        Exception.__init__(self, message)
        
        
class SourceHashMismatch(WhackUserError):
    def __init__(self, expected_hash, actual_hash):
        message = "Expected hash {0} but was {1}".format(
            expected_hash,
            actual_hash
        )
        Exception.__init__(self, message)


class PackageSourceFetcher(object):
    def __init__(self, indices=None):
        if indices is None:
            self._indices = []
        else:
            self._indices = indices
    
    def fetch(self, source_name):
        index_fetchers = lists.map(IndexFetcher, self._indices)
        fetchers = index_fetchers + [
            SourceControlFetcher(),
            HttpFetcher(),
            LocalPathFetcher(),
        ]
        for fetcher in fetchers:
            package_source = self._fetch_with_fetcher(fetcher, source_name)
            if package_source is not None:
                try:
                    self._verify(source_name, package_source)
                    return package_source
                except:
                    package_source.__exit__()
                    raise
        raise PackageSourceNotFound(source_name)
        
    def _fetch_with_fetcher(self, fetcher, source_name):
        if fetcher.can_fetch(source_name):
            return fetcher.fetch(source_name)
        else:
            return None
            
    def _verify(self, source_name, package_source):
        if source_name.endswith(SOURCE_URI_SUFFIX):
            full_name = source_name[:-len(SOURCE_URI_SUFFIX)]
            expected_hash = slugs.split(full_name)[-1]
            actual_hash = package_source.source_hash()
            if expected_hash != actual_hash:
                raise SourceHashMismatch(expected_hash, actual_hash)


class IndexFetcher(object):
    def __init__(self, index_uri):
        self._index_uri = index_uri
    
    def can_fetch(self, source_name):
        return re.match(r"^[a-z0-9\-_]+$", source_name)
        
    def fetch(self, source_name):
        index = read_index(self._index_uri)
        package_source_entry = index.find_package_source_by_name(source_name)
        if package_source_entry is None:
            return None
        else:
            return HttpFetcher().fetch(package_source_entry.url)
    

class SourceControlFetcher(object):
    def can_fetch(self, source_name):
        return mayo.is_source_control_uri(source_name)
        
    def fetch(self, source_name):
        def fetch_archive(destination_dir):
            mayo.archive(source_name, destination_dir)
        
        return _create_temporary_package_source(source_name, fetch_archive)
        
        
class LocalPathFetcher(object):
    def can_fetch(self, source_name):
        return is_local_path(source_name)
        
    def fetch(self, source_name):
        if os.path.isfile(source_name):
            return self._fetch_package_from_tarball(source_name)
        else:
            return PackageSource.local(source_name)
    
    def _fetch_package_from_tarball(self, tarball_path):
        def fetch_directory(destination_dir):
            extract_tarball(tarball_path, destination_dir, strip_components=1)
            return destination_dir
        
        return _create_temporary_package_source(tarball_path, fetch_directory)
        

class HttpFetcher(object):
    def can_fetch(self, source_name):
        return is_http_uri(source_name)
        
    def fetch(self, source_name):
        def fetch_directory(temp_dir):
            extract_tarball(source_name, temp_dir, strip_components=1)
            
        return _create_temporary_package_source(source_name, fetch_directory)


def _create_temporary_package_source(uri, fetch_package_source_dir):
    temp_dir = _temporary_path()
    try:
        fetch_package_source_dir(temp_dir)
        return PackageSource(temp_dir, uri, is_temp=True)
    except:
        delete_dir(temp_dir)
        raise


def _temporary_path():
    return os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))


def _is_tarball(path):
    return path.endswith(".tar.gz")


class PackageSource(object):
    @staticmethod
    def local(path):
        return PackageSource(path, path, is_temp=False)
    
    def __init__(self, path, uri, is_temp):
        self.path = path
        self.uri = uri
        self._description = _read_package_description(path)
        self._is_temp = is_temp
    
    def name(self):
        return self._description.name()
    
    def full_name(self):
        name = self.name()
        source_hash = self.source_hash()
        return slugs.join([name, source_hash])
    
    def source_hash(self):
        hasher = Hasher()
        for source_path in self._source_paths():
            absolute_source_path = os.path.join(self.path, source_path)
            hasher.update_with_dir(absolute_source_path)
        return hasher.ascii_digest()
    
    def write_to(self, target_dir):
        for source_dir in self._source_paths():
            target_sub_dir = os.path.join(target_dir, source_dir)
            try:
                _copy_dir_or_file(
                    os.path.join(self.path, source_dir),
                    target_sub_dir
                )
            except IOError as error:
                if error.errno == errno.ENOENT:
                    raise FileNotFoundError()
                else:
                    raise error
    
    def description(self):
        return self._description
    
    def _source_paths(self):
        return self._description.source_paths()
    
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        if self._is_temp:
            delete_dir(self.path)


def _copy_dir_or_file(source, destination):
    if os.path.isdir(source):
        copy_dir(source, destination)
    else:
        copy_file(source, destination)
        

def _read_package_description(package_src_dir):
    whack_json_path = os.path.join(package_src_dir, "whack/whack.json")
    if os.path.exists(whack_json_path):
        with open(whack_json_path, "r") as whack_json_file:
            whack_json = json.load(whack_json_file)
    else:
        whack_json = {}
    return DictBackedPackageDescription(whack_json)
        
        
class DictBackedPackageDescription(object):
    def __init__(self, values):
        self._values = values
        
    def name(self):
        return self._values.get("name", "unknown")
        
    def param_slug(self):
        return self._values.get("paramSlug", None)
        
    def source_paths(self):
        return self._values.get("sourcePaths", ["whack"])
        
    def default_params(self):
        return self._values.get("defaultParams", {})
        
    def test_command(self):
        return self._values.get("test", None)


def create_source_tarball(package_source, tarball_dir):
    with create_temporary_dir() as source_dir:
        package_source.write_to(source_dir)
        full_name = package_source.full_name()
        filename = "{0}{1}".format(full_name, SOURCE_URI_SUFFIX)
        path = os.path.join(tarball_dir, filename)
        create_tarball(path, source_dir)
        return SourceTarball(full_name, path)


class SourceTarball(object):
    def __init__(self, full_name, path):
        self.full_name = full_name
        self.path = path

########NEW FILE########
__FILENAME__ = tarballs
import os
import shutil

import requests

from .files import mkdir_p
from .tempdir import create_temporary_dir
from . import local
from .uris import is_http_uri


def extract_tarball(tarball_uri, destination_dir, strip_components):
    if is_http_uri(tarball_uri):
        with create_temporary_dir() as temp_dir:
            tarball_path = _download_tarball(tarball_uri, temp_dir)
            extract_tarball(tarball_path, destination_dir, strip_components)
    else:
        mkdir_p(destination_dir)
        local.run([
            "tar", "xzf", tarball_uri,
            "--directory", destination_dir,
            "--strip-components", str(strip_components)
        ])


def _download_tarball(url, tarball_dir):
    tarball_path = os.path.join(tarball_dir, "tarball.tar.gz")
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise Exception("Status code was: {0}".format(response.status_code))
    with open(tarball_path, "wb") as tarball_file:
        shutil.copyfileobj(response.raw, tarball_file)
    return tarball_path


def create_tarball(tarball_path, source, rename_dir=None):
    args = [
        "tar", "czf", tarball_path,
        "--directory", os.path.dirname(source),
        os.path.basename(source)
    ]
    if rename_dir is not None:
        args += [
            "--transform",
            "s/^{0}/{1}/".format(os.path.basename(source), rename_dir),
        ]
    local.run(args)
    return tarball_path

########NEW FILE########
__FILENAME__ = tempdir
import contextlib
import tempfile
import shutil

from .files import write_files


@contextlib.contextmanager
def create_temporary_dir(file_descriptions=None):
    temporary_dir = tempfile.mkdtemp()
    try:
        if file_descriptions:
            write_files(temporary_dir, file_descriptions)
        yield temporary_dir
    finally:
        shutil.rmtree(temporary_dir)

########NEW FILE########
__FILENAME__ = testing
class TestResult(object):
    def __init__(self, passed):
        self.passed = passed

########NEW FILE########
__FILENAME__ = uris
def is_local_path(path):
    return (
        path.startswith("/") or
        path.startswith("./") or
        path.startswith("../") or 
        path == "." or
        path == ".."
    )


def is_http_uri(uri):
    return uri.startswith("http://") or uri.startswith("https://")

########NEW FILE########
