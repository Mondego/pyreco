__FILENAME__ = check_release_installation
TARGET_HOST = '192.168.56.101'

import nose
from nose.tools import assert_equals, assert_not_equals
from ssh import Connection

from trashcli.trash import version

def main():
    check_connection()
    check_installation(normal_installation)
    check_installation(easy_install_installation)

def check_installation(installation_method):
    tc = LinuxBox('root@' + TARGET_HOST, installation_method)
    print "== Cleaning any prior software installation"
    tc.clean_any_prior_installation()
    print "== Copying software"
    tc.copy_tarball()
    print "== Installing software"
    tc.install_software()
    print "== Checking all program were installed"
    tc.check_all_programs_are_installed()


class LinuxBox:
    def __init__(self, address, installation_method):
        self.ssh = Connection(address)
        self.executables = [
                'trash-put', 'trash-list', 'trash-rm', 'trash-empty',
                'trash-restore', 'trash']
        self.tarball="trash-cli-%s.tar.gz" % version
        self.installation_method = installation_method
    def clean_any_prior_installation(self):
        "clean any prior installation"
        for executable in self.executables:
            self._remove_executable(executable)
            self._assert_command_removed(executable)
    def _remove_executable(self, executable):
        self.ssh.run('rm -f $(which %s)' % executable).assert_succesful()
    def _assert_command_removed(self, executable):
        result = self.ssh.run('which %s' % executable)
        command_not_existent_exit_code_for_which = 1
        assert_equals(result.exit_code, command_not_existent_exit_code_for_which,
                      'Which returned: %s\n' % result.exit_code +
                      'and reported: %s' % result.stdout
                      )
    def copy_tarball(self):
        self.ssh.put('dist/%s' % self.tarball)
    def install_software(self):
        def run_checked(command):
            result = self.ssh.run(command)
            result.assert_succesful()
        self.installation_method(self.tarball, run_checked)
    def check_all_programs_are_installed(self):
        for command in self.executables:
            result = self.ssh.run('%(command)s --version' % locals())
            assert_not_equals(127, result.exit_code,
                    "Exit code was: %s, " % result.exit_code +
                    "Probably command not found, command: %s" % command)

def normal_installation(tarball, check_run):
    directory = strip_end(tarball, '.tar.gz')
    check_run('tar xfvz %s' % tarball)
    check_run('cd %s && '
              'python setup.py install' % directory)

def easy_install_installation(tarball, check_run):
    check_run('easy_install %s' % tarball)

def strip_end(text, suffix):
    if not text.endswith(suffix):
        return text
    return text[:-len(suffix)]

def check_connection():
    suite = nose.loader.TestLoader().loadTestsFromTestClass(TestConnection)
    nose.run(suite=suite)

class TestConnection:
    def __init__(self):
        self.ssh = Connection(TARGET_HOST)
    def test_should_report_stdout(self):
        result = self.ssh.run('echo', 'foo')
        assert_equals('foo\n', result.stdout)
    def test_should_report_stderr(self):
        result = self.ssh.run('echo bar 1>&2')
        assert_equals('bar\n', result.stderr)
    def test_should_report_exit_code(self):
        result = self.ssh.run("exit 134")
        assert_equals(134, result.exit_code)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = assert_equals_with_unidiff
# Copyright (C) 2009-2011 Andrea Francia Trivolzio(PV) Italy

def assert_equals_with_unidiff(expected, actual):
    def unidiff(expected, actual):
        import difflib
        expected=expected.splitlines(1)
        actual=actual.splitlines(1)

        diff=difflib.unified_diff(expected, actual,
                                 fromfile='Expected', tofile='Actual',
                                 lineterm='\n', n=10)

        return ''.join(diff)
    from nose.tools import assert_equals
    assert_equals(expected, actual,
                  "\n"
                  "Expected:%s\n" % repr(expected) +
                  "  Actual:%s\n" % repr(actual) +
                  unidiff(expected, actual))

########NEW FILE########
__FILENAME__ = describe_trash_list
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

import os
from trashcli.trash import ListCmd
from files import (write_file, require_empty_dir, make_sticky_dir,
                   make_unsticky_dir, make_unreadable_file, make_empty_file,
                   make_parent_for)
from nose.tools import istest
from .output_collector import OutputCollector
from trashinfo import (
        a_trashinfo,
        a_trashinfo_without_date,
        a_trashinfo_without_path,
        a_trashinfo_with_invalid_date)
from textwrap import dedent

class Setup(object):
    def setUp(self):
        require_empty_dir('XDG_DATA_HOME')
        require_empty_dir('topdir')

        self.user = TrashListUser(
                environ = {'XDG_DATA_HOME': 'XDG_DATA_HOME'})

        self.home_trashcan = FakeTrashDir('XDG_DATA_HOME/Trash')
        self.add_trashinfo = self.home_trashcan.add_trashinfo
    def when_dir_is_sticky(self, path):
        make_sticky_dir(path)
    def when_dir_exists_unsticky(self, path):
        make_unsticky_dir(path)


@istest
class describe_trash_list(Setup):

    @istest
    def should_output_the_help_message(self):

        self.user.run('trash-list', '--help')

        self.user.should_read_output(dedent("""\
            Usage: trash-list [OPTIONS...]

            List trashed files

            Options:
              --version   show program's version number and exit
              -h, --help  show this help message and exit

            Report bugs to http://code.google.com/p/trash-cli/issues
        """))

    @istest
    def should_output_nothing_when_trashcan_is_empty(self):

        self.user.run_trash_list()

        self.user.should_read_output('')

    @istest
    def should_output_deletion_date_and_path(self):
        self.add_trashinfo('/aboslute/path', '2001-02-03T23:55:59')

        self.user.run_trash_list()

        self.user.should_read_output( "2001-02-03 23:55:59 /aboslute/path\n")

    @istest
    def should_output_info_for_multiple_files(self):
        self.add_trashinfo("/file1", "2000-01-01T00:00:01")
        self.add_trashinfo("/file2", "2000-01-01T00:00:02")
        self.add_trashinfo("/file3", "2000-01-01T00:00:03")

        self.user.run_trash_list()

        self.user.should_read_output( "2000-01-01 00:00:01 /file1\n"
                                      "2000-01-01 00:00:02 /file2\n"
                                      "2000-01-01 00:00:03 /file3\n")

    @istest
    def should_output_unknown_dates_with_question_marks(self):

        self.home_trashcan.having_file(a_trashinfo_without_date())

        self.user.run_trash_list()

        self.user.should_read_output("????-??-?? ??:??:?? /path\n")

    @istest
    def should_output_invalid_dates_using_question_marks(self):
        self.home_trashcan.having_file(a_trashinfo_with_invalid_date())

        self.user.run_trash_list()

        self.user.should_read_output("????-??-?? ??:??:?? /path\n")

    @istest
    def should_warn_about_empty_trashinfos(self):
        self.home_trashcan.touch('empty.trashinfo')

        self.user.run_trash_list()

        self.user.should_read_error(
                "Parse Error: XDG_DATA_HOME/Trash/info/empty.trashinfo: "
                "Unable to parse Path.\n")

    @istest
    def should_warn_about_unreadable_trashinfo(self):
        self.home_trashcan.having_unreadable('unreadable.trashinfo')

        self.user.run_trash_list()

        self.user.should_read_error(
                "[Errno 13] Permission denied: "
                "'XDG_DATA_HOME/Trash/info/unreadable.trashinfo'\n")
    @istest
    def should_warn_about_unexistent_path_entry(self):
        self.home_trashcan.having_file(a_trashinfo_without_path())

        self.user.run_trash_list()

        self.user.should_read_error(
                "Parse Error: XDG_DATA_HOME/Trash/info/1.trashinfo: "
                "Unable to parse Path.\n")
        self.user.should_read_output('')

@istest
class with_a_top_trash_dir(Setup):
    def setUp(self):
        super(type(self),self).setUp()
        self.top_trashdir1 = FakeTrashDir('topdir/.Trash/123')
        self.user.set_fake_uid(123)
        self.user.add_volume('topdir')

    @istest
    def should_list_its_contents_if_parent_is_sticky(self):
        self.when_dir_is_sticky('topdir/.Trash')
        self.and_contains_a_valid_trashinfo()

        self.user.run_trash_list()

        self.user.should_read_output("2000-01-01 00:00:00 topdir/file1\n")

    @istest
    def and_should_warn_if_parent_is_not_sticky(self):
        self.when_dir_exists_unsticky('topdir/.Trash')
        self.and_dir_exists('topdir/.Trash/123')

        self.user.run_trash_list()

        self.user.should_read_error("TrashDir skipped because parent not sticky: topdir/.Trash/123\n")

    @istest
    def but_it_should_not_warn_when_the_parent_is_unsticky_but_there_is_no_trashdir(self):
        self.when_dir_exists_unsticky('topdir/.Trash')
        self.but_does_not_exists_any('topdir/.Trash/123')

        self.user.run_trash_list()

        self.user.should_read_error("")

    @istest
    def should_ignore_trash_from_a_unsticky_topdir(self):
        self.when_dir_exists_unsticky('topdir/.Trash')
        self.and_contains_a_valid_trashinfo()

        self.user.run_trash_list()

        self.user.should_read_output("")

    @istest
    def it_should_ignore_Trash_is_a_symlink(self):
        self.when_is_a_symlink_to_a_dir('topdir/.Trash')
        self.and_contains_a_valid_trashinfo()

        self.user.run_trash_list()

        self.user.should_read_output('')

    @istest
    def and_should_warn_about_it(self):
        self.when_is_a_symlink_to_a_dir('topdir/.Trash')
        self.and_contains_a_valid_trashinfo()

        self.user.run_trash_list()

        self.user.should_read_error('TrashDir skipped because parent not sticky: topdir/.Trash/123\n')
    def but_does_not_exists_any(self, path):
        assert not os.path.exists(path)
    def and_dir_exists(self, path):
        os.mkdir(path)
        assert os.path.isdir(path)
    def and_contains_a_valid_trashinfo(self):
        self.top_trashdir1.add_trashinfo('file1', '2000-01-01T00:00:00')
    def when_is_a_symlink_to_a_dir(self, path):
        dest = "%s-dest" % path
        os.mkdir(dest)
        rel_dest = os.path.basename(dest)
        os.symlink(rel_dest, path)

@istest
class describe_when_a_file_is_in_alternate_top_trashdir(Setup):
    @istest
    def should_list_contents_of_alternate_trashdir(self):
        self.user.set_fake_uid(123)
        self.user.add_volume('topdir')
        self.top_trashdir2 = FakeTrashDir('topdir/.Trash-123')
        self.top_trashdir2.add_trashinfo('file', '2000-01-01T00:00:00')

        self.user.run_trash_list()

        self.user.should_read_output("2000-01-01 00:00:00 topdir/file\n")

@istest
class describe_trash_list_with_raw_option:
    def setup(self):
        self.having_XDG_DATA_HOME('XDG_DATA_HOME')
        self.running('trash-list', '--raw')
    @istest
    def output_should_contains_trashinfo_paths(self):
        from nose import SkipTest; raise SkipTest()
        self.having_trashinfo('foo.trashinfo')
        self.output_should_contain_line(
            'XDG_DATA_HOME/Trash/info/foo.trashinfo')
    @istest
    def output_should_contains_backup_copy_paths(self):
        from nose import SkipTest; raise SkipTest()
        self.having_trashinfo('foo.trashinfo')
        self.output_should_contain_line(
            'XDG_DATA_HOME/Trash/files/foo')

    def having_XDG_DATA_HOME(self, value):
        self.XDG_DATA_HOME = value
    def running(self, *argv):
        user = TrashListUser( environ = {'XDG_DATA_HOME': self.XDG_DATA_HOME})
        user.run(argv)
        self.output = user.output()
    def output_should_contain_line(self, line):
        assert line in self.output_lines()
    def output_lines(self):
        return [line.rstrip('\n') for line in self.output.splitlines()]


class FakeTrashDir:
    def __init__(self, path):
        self.path = path + '/info'
        self.number = 1
    def touch(self, path_relative_to_info_dir):
        make_empty_file(self.join(path_relative_to_info_dir))
    def having_unreadable(self, path_relative_to_info_dir):
        path = self.join(path_relative_to_info_dir)
        make_unreadable_file(path)
    def join(self, path_relative_to_info_dir):
        import os
        return os.path.join(self.path, path_relative_to_info_dir)
    def having_file(self, contents):
        path = '%(info_dir)s/%(name)s.trashinfo' % { 'info_dir' : self.path,
                                                     'name'     : str(self.number)}
        make_parent_for(path)
        write_file(path, contents)

        self.number += 1
        self.path_of_last_file_added = path

    def add_trashinfo(self, escaped_path_entry, formatted_deletion_date):
        self.having_file(a_trashinfo(escaped_path_entry, formatted_deletion_date))

class TrashListUser:
    def __init__(self, environ={}):
        self.stdout      = OutputCollector()
        self.stderr      = OutputCollector()
        self.environ     = environ
        self.fake_getuid = self.error
        self.volumes     = []
    def run_trash_list(self):
        self.run('trash-list')
    def run(self,*argv):
        from trashcli.trash import FileSystemReader
        file_reader = FileSystemReader()
        file_reader.list_volumes = lambda: self.volumes
        ListCmd(
            out         = self.stdout,
            err         = self.stderr,
            environ     = self.environ,
            getuid      = self.fake_getuid,
            file_reader = file_reader,
            list_volumes = lambda: self.volumes,
        ).run(*argv)
    def set_fake_uid(self, uid):
        self.fake_getuid = lambda: uid
    def add_volume(self, mount_point):
        self.volumes.append(mount_point)
    def error(self):
        raise ValueError()
    def should_read_output(self, expected_value):
        self.stdout.assert_equal_to(expected_value)
    def should_read_error(self, expected_value):
        self.stderr.assert_equal_to(expected_value)
    def output(self):
        return self.stdout.getvalue()


########NEW FILE########
__FILENAME__ = files
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

from nose.tools import assert_equals
from trashcli.fs  import has_sticky_bit
import os, shutil

def having_file(path):
    dirname=os.path.dirname(path)
    if dirname != '': make_dirs(dirname)
    open(path,'w').close()
    assert os.path.isfile(path)
make_empty_file = having_file

def write_file(filename, contents=''):
    parent = os.path.dirname(filename)
    if not os.path.isdir(parent): os.makedirs(parent)
    file(filename, 'w').write(contents)
    assert_equals(file(filename).read(), contents)

def require_empty_dir(path):
    if os.path.exists(path): shutil.rmtree(path)
    make_dirs(path)
    assert os.path.isdir(path)
    assert_equals([], list(os.listdir(path)))

def having_empty_dir(path):
    require_empty_dir(path)

def make_dirs(path):
    if not os.path.isdir(path):
        os.makedirs(path)
    assert os.path.isdir(path)

def make_parent_for(path):
    parent = os.path.dirname(path)
    make_dirs(parent)

def make_sticky_dir(path):
    os.mkdir(path)
    set_sticky_bit(path)

def make_unsticky_dir(path):
    os.mkdir(path)
    unset_sticky_bit(path)

def make_dir_unsticky(path):
    assert_is_dir(path)
    unset_sticky_bit(path)

def assert_is_dir(path):
    assert os.path.isdir(path)

def set_sticky_bit(path):
    import stat
    os.chmod(path, os.stat(path).st_mode | stat.S_ISVTX)

def unset_sticky_bit(path):
    import stat
    os.chmod(path, os.stat(path).st_mode & ~ stat.S_ISVTX)
    assert not has_sticky_bit(path)

def touch(path):
    open(path,'a+').close()

def ensure_non_sticky_dir(path):
    import os
    assert os.path.isdir(path)
    assert not has_sticky_bit(path)

def make_unreadable_file(path):
    write_file(path, '')
    import os
    os.chmod(path, 0)
    from nose.tools import assert_raises
    with assert_raises(IOError):
        file(path).read()


########NEW FILE########
__FILENAME__ = output_collector
from assert_equals_with_unidiff import assert_equals_with_unidiff

class OutputCollector:
    def __init__(self):
        from StringIO import StringIO
        self.stream = StringIO()
        self.getvalue = self.stream.getvalue
    def write(self,data):
        self.stream.write(data)
    def assert_equal_to(self, expected):
        return self.should_be(expected)
    def should_be(self, expected):
        assert_equals_with_unidiff(expected, self.stream.getvalue())
    def should_match(self, regex):
        text = self.stream.getvalue()
        from nose.tools import assert_regexp_matches
        assert_regexp_matches(text, regex)


########NEW FILE########
__FILENAME__ = test_filesystem
# Copyright (C) 2008-2011 Andrea Francia Trivolzio(PV) Italy

from trashcli.trash import mkdirs, FileSystemReader
from trashcli.fs import has_sticky_bit

from .files import require_empty_dir, having_file, set_sticky_bit
import os

class TestWithInSandbox:
    def test_mkdirs_with_default_mode(self):

        mkdirs("sandbox/test-dir/sub-dir")

        assert os.path.isdir("sandbox/test-dir/sub-dir")

    def test_has_sticky_bit_returns_true(self):

        having_file( "sandbox/sticky")
        run('chmod +t sandbox/sticky')

        assert has_sticky_bit('sandbox/sticky')

    def test_has_sticky_bit_returns_false(self):

        having_file( "sandbox/non-sticky")
        run('chmod -t sandbox/non-sticky')

        assert not has_sticky_bit("sandbox/non-sticky")

    def setUp(self):
        require_empty_dir('sandbox')

is_sticky_dir=FileSystemReader().is_sticky_dir
class Test_is_sticky_dir:

    def test_dir_non_sticky(self):
        mkdirs('sandbox/dir'); assert not is_sticky_dir('sandbox/dir')

    def test_dir_sticky(self):
        mkdirs('sandbox/dir'); set_sticky_bit('sandbox/dir')
        assert is_sticky_dir('sandbox/dir')

    def test_non_dir_but_sticky(self):
        having_file('sandbox/dir');
        set_sticky_bit('sandbox/dir')
        assert not is_sticky_dir('sandbox/dir')

    def setUp(self):
        require_empty_dir('sandbox')

def run(command):
    import subprocess
    assert subprocess.call(command.split()) == 0


########NEW FILE########
__FILENAME__ = test_file_descriptions
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

from trashcli.put import describe
from .files import require_empty_dir, having_file
from nose.tools import assert_equals
import os

class TestDescritions:
    def setUp(self):
        require_empty_dir('sandbox')

    def test_on_directories(self):

        assert_equals("directory", describe('.'))
        assert_equals("directory", describe(".."))
        assert_equals("directory", describe("sandbox"))

    def test_on_dot_directories(self):

        assert_equals("`.' directory",  describe("sandbox/."))
        assert_equals("`.' directory",  describe("./."))

    def test_on_dot_dot_directories(self):

        assert_equals("`..' directory", describe("./.."))
        assert_equals("`..' directory", describe("sandbox/.."))

    def test_name_for_regular_files_non_empty_files(self):

        write_file("sandbox/non-empty", "contents")
        assert_equals("regular file", describe("sandbox/non-empty"))

    def test_name_for_empty_file(self):

        having_file('sandbox/empty')
        assert_equals("regular empty file", describe("sandbox/empty"))

    def test_name_for_symbolic_links(self):

        os.symlink('nowhere', "sandbox/symlink")

        assert_equals("symbolic link", describe("sandbox/symlink"))

    def test_name_for_non_existent_entries(self):

        assert not os.path.exists('non-existent')

        assert_equals("non existent", describe('non-existent'))

def write_file(path, contents):
    f = open(path, 'w')
    f.write(contents)
    f.close()


########NEW FILE########
__FILENAME__ = test_listing_all_trashinfo_in_a_trashdir
from trashcli.trash import TrashDirectory

from files import require_empty_dir
from files import write_file
from nose.tools import assert_equals, assert_items_equal
from mock import Mock

class TestWhenListingTrashinfo:
    def setUp(self):
        require_empty_dir('sandbox')
        self.trash_dir = TrashDirectory('sandbox', '/')
        self.logger = Mock()
        self.trash_dir.logger = self.logger


    def test_should_list_a_trashinfo(self):
        write_file('sandbox/info/foo.trashinfo')

        result = self.list_trashinfos()

        assert_equals(['sandbox/info/foo.trashinfo'], result)

    def test_should_list_multiple_trashinfo(self):
        write_file('sandbox/info/foo.trashinfo')
        write_file('sandbox/info/bar.trashinfo')
        write_file('sandbox/info/baz.trashinfo')

        result = self.list_trashinfos()

        assert_items_equal(['sandbox/info/foo.trashinfo',
                            'sandbox/info/baz.trashinfo',
                            'sandbox/info/bar.trashinfo'], result)

    def test_should_ignore_non_trashinfo(self):
        write_file('sandbox/info/not-a-trashinfo')

        result = self.list_trashinfos()

        assert_equals([], result)

    def test_non_trashinfo_should_reported_as_a_warn(self):
        write_file('sandbox/info/not-a-trashinfo')

        self.list_trashinfos()

        self.logger.warning.assert_called_with('Non .trashinfo file in info dir')

    def list_trashinfos(self):
        return list(self.trash_dir.all_info_files())



########NEW FILE########
__FILENAME__ = test_persist
# Copyright (C) 2008-2012 Andrea Francia Trivolzio(PV) Italy

import os

from nose.tools import assert_equals, assert_true

from integration_tests.files import require_empty_dir
from trashcli.put import TrashDirectoryForPut

join = os.path.join

class TestTrashDirectory_persit_trash_info:
    def setUp(self):
        self.trashdirectory_base_dir = os.path.realpath(
                "./sandbox/testTrashDirectory")
        require_empty_dir(self.trashdirectory_base_dir)

        self.instance = TrashDirectoryForPut(
                self.trashdirectory_base_dir,
                "/")

    def persist_trash_info(self, basename, content):
        return self.instance.persist_trash_info(
                self.instance.info_dir, basename,content)

    def test_persist_trash_info_first_time(self):

        trash_info_file = self.persist_trash_info('dummy-path', 'content')
        assert_equals(join(self.trashdirectory_base_dir,'info', 'dummy-path.trashinfo'), trash_info_file)

        assert_equals('content', read(trash_info_file))

    def test_persist_trash_info_first_100_times(self):
        self.test_persist_trash_info_first_time()

        for i in range(1,100) :
            content='trashinfo content'
            trash_info_file = self.persist_trash_info('dummy-path', content)

            assert_equals("dummy-path_%s.trashinfo" % i,
                    os.path.basename(trash_info_file))
            assert_equals('trashinfo content', read(trash_info_file))

    def test_persist_trash_info_other_times(self):
        self.test_persist_trash_info_first_100_times()

        for i in range(101,200) :
            trash_info_file = self.persist_trash_info('dummy-path','content')
            trash_info_id = os.path.basename(trash_info_file)
            assert_true(trash_info_id.startswith("dummy-path_"))
            assert_equals('content', read(trash_info_file))
    test_persist_trash_info_first_100_times.stress_test = True
    test_persist_trash_info_other_times.stress_test = True

def read(path):
    return file(path).read()


########NEW FILE########
__FILENAME__ = test_restore_trash
import os
from nose.tools import istest
from trashcli.trash import RestoreCmd

from .files import require_empty_dir
from .output_collector import OutputCollector
from trashinfo import a_trashinfo

@istest
class describe_restore_trash:
    @istest
    def it_should_do_nothing_when_no_file_have_been_found_in_current_dir(self):

        self.when_running_restore_trash()
        self.output_should_match('No files trashed from current dir.+')

    @istest
    def it_should_show_the_file_deleted_from_the_current_dir(self):

        self.having_a_trashed_file('/foo/bar')
        self.when_running_restore_trash(from_dir='/foo')
        self.output_should_match(
            '   0 2000-01-01 00:00:01 /foo/bar\n.*\n')
        self.error_should_be('')

    @istest
    def it_should_restore_the_file_selected_by_the_user(self):

        self.having_a_file_trashed_from_current_dir('foo')
        self.when_running_restore_trash(
                from_dir=os.getcwd(), 
                with_user_typing = '0')

        self.file_should_have_been_restored('foo')
    
    @istest
    def it_should_exit_gracefully_when_user_selects_nothing(self):

        self.having_a_trashed_file('/foo/bar')
        self.when_running_restore_trash( from_dir='/foo', 
                                         with_user_typing = '')
        self.output_should_match(
            '.*\nExiting\n')
        self.error_should_be('')

    @istest
    def it_should_refuse_overwriting_existing_file(self):

        self.having_a_file_trashed_from_current_dir('foo')
        file('foo', 'a+').close()
        os.chmod('foo', 000)
        self.when_running_restore_trash(from_dir=current_dir(),
                                        with_user_typing = '0')
        self.error_should_be('Refusing to overwrite existing file "foo".\n')

    def setUp(self):
        require_empty_dir('XDG_DATA_HOME')

        trashcan = TrashCan('XDG_DATA_HOME/Trash')
        self.having_a_trashed_file = trashcan.make_trashed_file

        out = OutputCollector()
        err = OutputCollector()
        self.when_running_restore_trash = RestoreTrashRunner(out, err,
                                                             'XDG_DATA_HOME')
        self.output_should_match = out.should_match
        self.error_should_be = err.should_be

    def having_a_file_trashed_from_current_dir(self, filename):
        self.having_a_trashed_file(os.path.join(os.getcwd(), filename))
        if os.path.exists(filename):
            os.remove(filename)
        assert not os.path.exists(filename)

    def file_should_have_been_restored(self, filename):
        assert os.path.exists(filename)

def current_dir():
    return os.getcwd()

class RestoreTrashRunner:
    def __init__(self, out, err, XDG_DATA_HOME):
        self.environ = {'XDG_DATA_HOME': XDG_DATA_HOME}
        self.out = out
        self.err = err
    def __call__(self, from_dir='/', with_user_typing=''):
        RestoreCmd(
            stdout  = self.out,
            stderr  = self.err,
            environ = self.environ,
            exit    = [].append,
            input   = lambda msg: with_user_typing,
            curdir  = lambda: from_dir
        ).run()

class TrashCan:
    def __init__(self, path):
        self.path = path
    def make_trashed_file(self, path):
        from .files import write_file
        write_file('%s/info/foo.trashinfo' % self.path, a_trashinfo(path))
        write_file('%s/files/foo' % self.path)


########NEW FILE########
__FILENAME__ = test_trash_empty
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

from nose.tools import (assert_equals,
                        assert_items_equal,
                        istest)
from trashcli.trash import EmptyCmd

from StringIO import StringIO
import os
from files import write_file, require_empty_dir, make_dirs, set_sticky_bit
from files import having_file
from mock import MagicMock

@istest
class WhenCalledWithoutArguments:

    def setUp(self):
        require_empty_dir('XDG_DATA_HOME')
        self.info_dir_path   = 'XDG_DATA_HOME/Trash/info'
        self.files_dir_path  = 'XDG_DATA_HOME/Trash/files'
        self.environ = {'XDG_DATA_HOME':'XDG_DATA_HOME'}
        now = MagicMock(side_effect=RuntimeError)
        self.empty_cmd = EmptyCmd(
            out = StringIO(),
            err = StringIO(),
            environ = self.environ,
            now = now,
            list_volumes = no_volumes,
        )

    def user_run_trash_empty(self):
        self.empty_cmd.run('trash-empty')

    @istest
    def it_should_remove_an_info_file(self):
        self.having_a_trashinfo_in_trashcan('foo.trashinfo')

        self.user_run_trash_empty()

        self.assert_dir_empty(self.info_dir_path)

    @istest
    def it_should_remove_all_the_infofiles(self):
        self.having_three_trashinfo_in_trashcan()

        self.user_run_trash_empty()

        self.assert_dir_empty(self.info_dir_path)

    @istest
    def it_should_remove_the_backup_files(self):
        self.having_one_trashed_file()

        self.user_run_trash_empty()

        self.assert_dir_empty(self.files_dir_path)

    @istest
    def it_should_keep_unknown_files_found_in_infodir(self):
        self.having_file_in_info_dir('not-a-trashinfo')

        self.user_run_trash_empty()

        self.assert_dir_contains(self.info_dir_path, 'not-a-trashinfo')

    @istest
    def but_it_should_remove_orphan_files_from_the_files_dir(self):
        self.having_orphan_file_in_files_dir()

        self.user_run_trash_empty()

        self.assert_dir_empty(self.files_dir_path)

    @istest
    def it_should_purge_also_directories(self):
        os.makedirs("XDG_DATA_HOME/Trash/files/a-dir")

        self.user_run_trash_empty()

    def assert_dir_empty(self, path):
        assert len(os.listdir(path)) == 0

    def assert_dir_contains(self, path, filename):
        assert os.path.exists(os.path.join(path, filename))

    def having_a_trashinfo_in_trashcan(self, basename_of_trashinfo):
        having_file(os.path.join(self.info_dir_path, basename_of_trashinfo))

    def having_three_trashinfo_in_trashcan(self):
        self.having_a_trashinfo_in_trashcan('foo.trashinfo')
        self.having_a_trashinfo_in_trashcan('bar.trashinfo')
        self.having_a_trashinfo_in_trashcan('baz.trashinfo')
        assert_items_equal(['foo.trashinfo',
                            'bar.trashinfo',
                            'baz.trashinfo'], os.listdir(self.info_dir_path))

    def having_one_trashed_file(self):
        self.having_a_trashinfo_in_trashcan('foo.trashinfo')
        having_file(self.files_dir_path +'/foo')
        self.files_dir_should_not_be_empty()

    def files_dir_should_not_be_empty(self):
        assert len(os.listdir(self.files_dir_path)) != 0

    def having_file_in_info_dir(self, filename):
        having_file(os.path.join(self.info_dir_path, filename))

    def having_orphan_file_in_files_dir(self):
        complete_path = os.path.join(self.files_dir_path,
                                     'a-file-without-any-associated-trashinfo')
        having_file(complete_path)
        assert os.path.exists(complete_path)

@istest
class When_invoked_with_N_days_as_argument:
    def setUp(self):
        require_empty_dir('XDG_DATA_HOME')
        self.xdg_data_home   = 'XDG_DATA_HOME'
        self.environ = {'XDG_DATA_HOME':'XDG_DATA_HOME'}
        self.now = MagicMock(side_effect=RuntimeError)
        self.empty_cmd=EmptyCmd(
            out = StringIO(),
            err = StringIO(),
            environ = self.environ,
            now = self.now,
            list_volumes = no_volumes,
        )

    def user_run_trash_empty(self, *args):
        self.empty_cmd.run('trash-empty', *args)

    def set_clock_at(self, yyyy_mm_dd):
        self.now.side_effect = lambda:date(yyyy_mm_dd)

        def date(yyyy_mm_dd):
            from datetime import datetime
            return datetime.strptime(yyyy_mm_dd, '%Y-%m-%d')

    @istest
    def it_should_keep_files_newer_than_N_days(self):
        self.having_a_trashed_file('foo', '2000-01-01')
        self.set_clock_at('2000-01-01')

        self.user_run_trash_empty('2')

        self.file_should_have_been_kept_in_trashcan('foo')

    @istest
    def it_should_remove_files_older_than_N_days(self):
        self.having_a_trashed_file('foo', '1999-01-01')
        self.set_clock_at('2000-01-01')

        self.user_run_trash_empty('2')

        self.file_should_have_been_removed_from_trashcan('foo')

    @istest
    def it_should_kept_files_with_invalid_deletion_date(self):
        self.having_a_trashed_file('foo', 'Invalid Date')
        self.set_clock_at('2000-01-01')

        self.user_run_trash_empty('2')

        self.file_should_have_been_kept_in_trashcan('foo')

    def having_a_trashed_file(self, name, date):
        contents = "DeletionDate=%sT00:00:00\n" % date
        write_file(self.trashinfo(name), contents)

    def trashinfo(self, name):
        return '%(dirname)s/Trash/info/%(name)s.trashinfo' % {
                    'dirname' : self.xdg_data_home,
                    'name'    : name }

    def file_should_have_been_kept_in_trashcan(self, trashinfo_name):
        assert os.path.exists(self.trashinfo(trashinfo_name))
    def file_should_have_been_removed_from_trashcan(self, trashinfo_name):
        assert not os.path.exists(self.trashinfo(trashinfo_name))

class TestEmptyCmdWithMultipleVolumes:
    def setUp(self):
        require_empty_dir('topdir')
        self.empty=EmptyCmd(
                out          = StringIO(),
                err          = StringIO(),
                environ      = {},
                getuid       = lambda: 123,
                list_volumes = lambda: ['topdir'],)

    def test_it_removes_trashinfos_from_method_1_dir(self):
        self.make_proper_top_trash_dir('topdir/.Trash')
        having_file('topdir/.Trash/123/info/foo.trashinfo')

        self.empty.run('trash-empty')

        assert not os.path.exists('topdir/.Trash/123/info/foo.trashinfo')
    def test_it_removes_trashinfos_from_method_2_dir(self):
        having_file('topdir/.Trash-123/info/foo.trashinfo')

        self.empty.run('trash-empty')

        assert not os.path.exists('topdir/.Trash-123/info/foo.trashinfo')

    def make_proper_top_trash_dir(self, path):
        make_dirs(path)
        set_sticky_bit(path)

from textwrap import dedent
class TestTrashEmpty_on_help:
    def test_help_output(self):
        err, out = StringIO(), StringIO()
        cmd = EmptyCmd(err = err,
                       out = out,
                       environ = {},
                       list_volumes = no_volumes,)
        cmd.run('trash-empty', '--help')
        assert_equals(out.getvalue(), dedent("""\
            Usage: trash-empty [days]

            Purge trashed files.

            Options:
              --version   show program's version number and exit
              -h, --help  show this help message and exit

            Report bugs to http://code.google.com/p/trash-cli/issues
            """))

class TestTrashEmpty_on_version():
    def test_it_print_version(self):
        err, out = StringIO(), StringIO()
        cmd = EmptyCmd(err = err,
                       out = out,
                       environ = {},
                       version = '1.2.3',
                       list_volumes = no_volumes,)
        cmd.run('trash-empty', '--version')
        assert_equals(out.getvalue(), dedent("""\
            trash-empty 1.2.3
            """))

class describe_trash_empty_command_line__on_invalid_options():
    def setUp(self):
        self.err, self.out = StringIO(), StringIO()
        self.cmd = EmptyCmd(
                       err = self.err,
                       out = self.out,
                       environ = {},
                       list_volumes = no_volumes)

    def it_should_fail(self):

        self.exit_code = self.cmd.run('trash-empty', '-2')

        exit_code_for_command_line_usage = 64
        assert_equals(exit_code_for_command_line_usage, self.exit_code)

    def it_should_complain_to_the_standard_error(self):

        self.exit_code = self.cmd.run('trash-empty', '-2')

        assert_equals(self.err.getvalue(), dedent("""\
                trash-empty: invalid option -- '2'
                """))

    def test_with_a_different_option(self):

        self.cmd.run('trash-empty', '-3')

        assert_equals(self.err.getvalue(), dedent("""\
                trash-empty: invalid option -- '3'
                """))

def no_volumes():
    return []


########NEW FILE########
__FILENAME__ = test_trash_put
# Copyright (C) 2009-2011 Andrea Francia Trivolzio(PV) Italy
from trashcli.put import TrashPutCmd

import os
from nose.tools import istest, assert_equals, assert_not_equals
from nose.tools import assert_in

from .files import having_file, require_empty_dir, having_empty_dir
from .files import make_sticky_dir
from trashcli.fstab import FakeFstab

class TrashPutTest:

    def setUp(self):
        self.prepare_fixture()
        self.setUp2()

    def setUp2(self):
        pass

    def prepare_fixture(self):
        require_empty_dir('sandbox')
        self.environ = {'XDG_DATA_HOME': 'sandbox/XDG_DATA_HOME' }

        from .output_collector import OutputCollector
        self.out     = OutputCollector()
        self.err     = OutputCollector()
        self.fstab   = FakeFstab()

        self.stderr_should_be = self.err.should_be
        self.output_should_be = self.out.should_be

    def run_trashput(self, *argv):
        cmd = TrashPutCmd(
            stdout  = self.out,
            stderr  = self.err,
            environ = self.environ,
            fstab   = self.fstab
        )
        self.exit_code = cmd.run(list(argv))
        self.stderr = self.err.getvalue()

@istest
class when_deleting_an_existing_file(TrashPutTest):
    def setUp2(self):
        having_file('sandbox/foo')
        self.run_trashput('trash-put', 'sandbox/foo')

    @istest
    def it_should_remove_the_file(self):
        file_should_have_been_deleted('sandbox/foo')

    @istest
    def it_should_remove_it_silently(self):
        self.output_should_be('')

    @istest
    def a_trashinfo_file_should_have_been_created(self):
        file('sandbox/XDG_DATA_HOME/Trash/info/foo.trashinfo').read()

@istest
class when_deleting_an_existing_file_in_verbose_mode(TrashPutTest):
    def setUp2(self):
        having_file('sandbox/foo')
        self.run_trashput('trash-put', '-v', 'sandbox/foo')

    @istest
    def should_tell_where_a_file_is_trashed(self):
        assert_in("trash-put: `sandbox/foo' trashed in sandbox/XDG_DATA_HOME/Trash",
                  self.stderr.splitlines())

    @istest
    def should_be_succesfull(self):
        assert_equals(0, self.exit_code)

@istest
class when_deleting_a_non_existing_file(TrashPutTest):
    def setUp2(self):
        self.run_trashput('trash-put', '-v', 'non-existent')

    @istest
    def should_be_succesfull(self):
        assert_not_equals(0, self.exit_code)

@istest
class when_fed_with_dot_arguments(TrashPutTest):

    def setUp2(self):
        having_empty_dir('sandbox/')
        having_file('other_argument')

    def test_dot_argument_is_skipped(self):

        self.run_trashput("trash-put", ".", "other_argument")

        # the dot directory shouldn't be operated, but a diagnostic message
        # shall be writtend on stderr
        self.stderr_should_be(
                "trash-put: cannot trash directory `.'\n")

        # the remaining arguments should be processed
        assert not exists('other_argument')

    def test_dot_dot_argument_is_skipped(self):

        self.run_trashput("trash-put", "..", "other_argument")

        # the dot directory shouldn't be operated, but a diagnostic message
        # shall be writtend on stderr
        self.stderr_should_be(
            "trash-put: cannot trash directory `..'\n")

        # the remaining arguments should be processed
        assert not exists('other_argument')

    def test_dot_argument_is_skipped_even_in_subdirs(self):

        self.run_trashput("trash-put", "sandbox/.", "other_argument")

        # the dot directory shouldn't be operated, but a diagnostic message
        # shall be writtend on stderr
        self.stderr_should_be(
            "trash-put: cannot trash `.' directory `sandbox/.'\n")

        # the remaining arguments should be processed
        assert not exists('other_argument')
        assert exists('sandbox')

    def test_dot_dot_argument_is_skipped_even_in_subdirs(self):

        self.run_trashput("trash-put", "sandbox/..", "other_argument")

        # the dot directory shouldn't be operated, but a diagnostic message
        # shall be writtend on stderr
        self.stderr_should_be(
            "trash-put: cannot trash `..' directory `sandbox/..'\n")

        # the remaining arguments should be processed
        assert not exists('other_argument')
        assert exists('sandbox')

from textwrap import dedent
@istest
class TestUnsecureTrashDirMessages(TrashPutTest):
    def setUp(self):
        TrashPutTest.setUp(self)
        having_empty_dir('fake-vol')
        self.fstab.add_mount('fake-vol')
        having_file('fake-vol/foo')

    @istest
    def when_is_unsticky(self):
        having_empty_dir('fake-vol/.Trash')

        self.run_trashput('trash-put', '-v', 'fake-vol/foo')

        assert_line_in_text(
                'trash-put: found unsecure .Trash dir (should be sticky): '
                'fake-vol/.Trash', self.stderr)

    @istest
    def when_it_is_not_a_dir(self):
        having_file('fake-vol/.Trash')

        self.run_trashput('trash-put', '-v', 'fake-vol/foo')

        assert_line_in_text(
                'trash-put: found unusable .Trash dir (should be a dir): '
                'fake-vol/.Trash', self.stderr)

    @istest
    def when_is_a_symlink(self):
        make_sticky_dir('fake-vol/link-destination')
        os.symlink('link-destination', 'fake-vol/.Trash')

        self.run_trashput('trash-put', '-v', 'fake-vol/foo')

        assert_line_in_text(
                'trash-put: found unsecure .Trash dir (should not be a symlink): '
                'fake-vol/.Trash', self.stderr)

def assert_line_in_text(line, text):
    assert_in(line, text.splitlines(), dedent('''\
            Line not found in text
            Line:

            %s

            Text:

            ---
            %s---''')
            %(repr(line), text))

def should_fail(func):
    from nose.tools import assert_raises
    with assert_raises(AssertionError):
        func()

def file_should_have_been_deleted(path):
    import os
    assert not os.path.exists('sandbox/foo')

exists = os.path.exists

########NEW FILE########
__FILENAME__ = test_trash_rm
from StringIO import StringIO
from mock import Mock, ANY
from nose.tools import assert_false, assert_raises

from files import require_empty_dir, write_file
from trashcli.rm import Main, ListTrashinfos
from trashinfo import a_trashinfo_with_path


class TestTrashRm:
    def test_integration(self):
        trash_rm = Main()
        trash_rm.environ = {'XDG_DATA_HOME':'sandbox/xdh'}
        trash_rm.list_volumes = lambda:[]
        trash_rm.getuid = 123
        trash_rm.stderr = StringIO()

        self.add_trashinfo_for(1, 'to/be/deleted')
        self.add_trashinfo_for(2, 'to/be/kept')

        trash_rm.run(['trash-rm', 'delete*'])

        self.assert_trashinfo_has_been_deleted(1)
    def setUp(self):
        require_empty_dir('sandbox/xdh')

    def add_trashinfo_for(self, index, path):
        write_file(self.trashinfo_from_index(index),
                   a_trashinfo_with_path(path))
    def trashinfo_from_index(self, index):
        return 'sandbox/xdh/Trash/info/%s.trashinfo' % index

    def assert_trashinfo_has_been_deleted(self, index):
        import os
        filename = self.trashinfo_from_index(index)
        assert_false(os.path.exists(filename),
                'File "%s" still exists' % filename)

class TestListing:
    def setUp(self):
        require_empty_dir('sandbox')
        self.out = Mock()
        self.listing = ListTrashinfos(self.out)
        self.index = 0

    def test_should_report_original_location(self):
        self.add_trashinfo('/foo')

        self.listing.list_from_home_trashdir('sandbox/Trash')

        self.out.assert_called_with('/foo', ANY)

    def test_should_report_trashinfo_path(self):
        self.add_trashinfo(trashinfo_path='sandbox/Trash/info/a.trashinfo')

        self.listing.list_from_home_trashdir('sandbox/Trash')

        self.out.assert_called_with(ANY, 'sandbox/Trash/info/a.trashinfo')

    def test_should_handle_volume_trashdir(self):
        self.add_trashinfo(trashinfo_path='sandbox/.Trash/123/info/a.trashinfo')

        self.listing.list_from_volume_trashdir('sandbox/.Trash/123',
                                               '/fake/vol')

        self.out.assert_called_with(ANY, 'sandbox/.Trash/123/info/a.trashinfo')

    def test_should_absolutize_relative_path_for_volume_trashdir(self):
        self.add_trashinfo(path='foo/bar', trashdir='sandbox/.Trash/501')

        self.listing.list_from_volume_trashdir('sandbox/.Trash/501',
                                               '/fake/vol')

        self.out.assert_called_with('/fake/vol/foo/bar', ANY)

    def add_trashinfo(self, path='unspecified/original/location',
                            trashinfo_path=None,
                            trashdir='sandbox/Trash'):
        trashinfo_path = trashinfo_path or self._trashinfo_path(trashdir)
        write_file(trashinfo_path, a_trashinfo_with_path(path))
    def _trashinfo_path(self, trashdir):
        path = '%s/info/%s.trashinfo' % (trashdir, self.index)
        self.index +=1
        return path




########NEW FILE########
__FILENAME__ = test_trash_rm_script
from nose.tools import istest, assert_equals, assert_in
import subprocess
from subprocess import STDOUT, PIPE, check_output, call, Popen
from assert_equals_with_unidiff import assert_equals_with_unidiff as assert_equals
from textwrap import dedent

from pprint import pprint

@istest
class WhenNoArgs:
    def setUp(self):
        process = Popen(['python', 'trashcli/rm.py'],
                    env={'PYTHONPATH':'.'},
                    stdin=None,
                    stdout=PIPE,
                    stderr=PIPE)

        (self.stdout, self.stderr) = process.communicate()
        process.wait()
        self.returncode = process.returncode

    def test_should_print_usage_on_standard_error(self):
        assert_in("Usage:", self.stderr.splitlines())


########NEW FILE########
__FILENAME__ = trashinfo
def a_trashinfo(escaped_path_entry,
                formatted_deletion_date = '2000-01-01T00:00:01'):
    return ("[Trash Info]\n"                          +
            "Path=%s\n"         % escaped_path_entry +
            "DeletionDate=%s\n" % formatted_deletion_date)

def a_trashinfo_without_date():
    return ("[Trash Info]\n"
            "Path=/path\n")

def a_trashinfo_with_invalid_date():
    return ("[Trash Info]\n"
            "Path=/path\n"
            "DeletionDate=Wrong Date")

def a_trashinfo_without_path():
    return ("[Trash Info]\n"
            "DeletionDate='2000-01-01T00:00:00'\n")

def a_trashinfo_with_date(date):
    return ("[Trash Info]\n"
            "DeletionDate=%s\n" % date)

def a_trashinfo_with_path(path):
    return ("[Trash Info]\n"
            "Path=%s\n" % path)

########NEW FILE########
__FILENAME__ = ssh
from nose.tools import assert_equals
import subprocess

class Connection:
    def __init__(self, target_host):
        self.target_host = target_host
    def run(self, *user_command):
        ssh_invocation = ['ssh', self.target_host, '-oVisualHostKey=false']
        command = ssh_invocation + list(user_command)
        exit_code, stderr, stdout = self._run_command(command)
        return self.ExecutionResult(stdout, stderr, exit_code)
    def put(self, source_file):
        scp_command = ['scp', source_file, self.target_host + ':']
        exit_code, stderr, stdout = self._run_command(scp_command)
        assert 0 == exit_code
    def _run_command(self, command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout,stderr = process.communicate()
        exit_code = process.poll()
        return exit_code, stderr, stdout
    class ExecutionResult:
        def __init__(self, stdout, stderr, exit_code):
            self.stdout = stdout
            self.stderr = stderr
            self.exit_code = exit_code
        def assert_no_err(self):
            assert_equals('', self.stderr)
        def assert_succesful(self):
            assert self.exit_code == 0



########NEW FILE########
__FILENAME__ = cmds
# Copyright (C) 2007-2011 Andrea Francia Trivolzio(PV) Italy

import sys,os

def restore():
    from trashcli.trash import RestoreCmd
    RestoreCmd(
        stdout  = sys.stdout,
        stderr  = sys.stderr,
        environ = os.environ,
        exit    = sys.exit,
        input   = raw_input
    ).run(sys.argv)

def empty():
    from trashcli.trash import EmptyCmd
    from trashcli.list_mount_points import mount_points
    return EmptyCmd(
        out          = sys.stdout,
        err          = sys.stderr,
        environ      = os.environ,
        list_volumes = mount_points,
    ).run(*sys.argv)


def list():
    from trashcli.trash import ListCmd
    from trashcli.list_mount_points import mount_points
    ListCmd(
        out          = sys.stdout,
        err          = sys.stderr,
        environ      = os.environ,
        getuid       = os.getuid,
        list_volumes = mount_points,
    ).run(*sys.argv)


########NEW FILE########
__FILENAME__ = fs
import os, shutil

class FileSystemListing:
    def entries_if_dir_exists(self, path):
        if os.path.exists(path):
            for entry in os.listdir(path):
                yield entry
    def exists(self, path):
        return os.path.exists(path)

class FileSystemReader(FileSystemListing):
    def is_sticky_dir(self, path):
        import os
        return os.path.isdir(path) and has_sticky_bit(path)
    def is_symlink(self, path):
        return os.path.islink(path)
    def contents_of(self, path):
        return file(path).read()

class FileRemover:
    def remove_file(self, path):
        try:
            return os.remove(path)
        except OSError:
            shutil.rmtree(path)
    def remove_file_if_exists(self,path):
        if os.path.exists(path): self.remove_file(path)

def contents_of(path): # TODO remove
    return FileSystemReader().contents_of(path)
def has_sticky_bit(path): # TODO move to FileSystemReader
    import os
    import stat
    return (os.stat(path).st_mode & stat.S_ISVTX) == stat.S_ISVTX

def parent_of(path):
    return os.path.dirname(path)

def remove_file(path):
    if(os.path.exists(path)):
        try:
            os.remove(path)
        except:
            return shutil.rmtree(path)

def move(path, dest) :
    return shutil.move(path, str(dest))

def list_files_in_dir(path):
    for entry in os.listdir(path):
        result = os.path.join(path, entry)
        yield result

def mkdirs(path):
    if os.path.isdir(path):
        return
    os.makedirs(path)

def atomic_write(filename, content):
    file_handle = os.open(filename, os.O_RDWR | os.O_CREAT | os.O_EXCL,
            0600)
    os.write(file_handle, content)
    os.close(file_handle)

def ensure_dir(path, mode):
    if os.path.isdir(path):
        os.chmod(path, mode)
        return
    os.makedirs(path, mode)

########NEW FILE########
__FILENAME__ = fstab
import os

def volume_of(path) :
    return Fstab().volume_of(path)

class AbstractFstab(object):
    def __init__(self, ismount):
        self.ismount = ismount
    def volume_of(self, path):
        volume_of = VolumeOf(ismount=self.ismount)
        return volume_of(path)
    def mount_points(self):
        return self.ismount.mount_points()

class Fstab(AbstractFstab):
    def __init__(self):
        AbstractFstab.__init__(self, OsIsMount())

class FakeFstab:
    def __init__(self):
        self.ismount = FakeIsMount()
        self.volume_of = VolumeOf(ismount = self.ismount)
        self.volume_of.abspath = os.path.normpath

    def mount_points(self):
        return self.ismount.mount_points()

    def volume_of(self, path):
        volume_of = VolumeOf(ismount=self.ismount)
        return volume_of(path)

    def add_mount(self, path):
        self.ismount.add_mount(path)

from trashcli.list_mount_points import mount_points as os_mount_points
class OsIsMount:
    def __call__(self, path):
        return os.path.ismount(path)
    def mount_points(self):
        return os_mount_points()

class FakeIsMount:
    def __init__(self):
        self.fakes = set(['/'])
    def add_mount(self, path):
        self.fakes.add(path)
    def __call__(self, path):
        if path == '/':
            return True
        path = os.path.normpath(path)
        if path in self.fakes:
            return True
        return False
    def mount_points(self):
        return self.fakes.copy()

class VolumeOf:
    def __init__(self, ismount):
        self._ismount = ismount
        import os
        self.abspath = os.path.abspath

    def __call__(self, path):
        path = self.abspath(path)
        while path != os.path.dirname(path):
            if self._ismount(path):
                break
            path = os.path.dirname(path)
        return path


########NEW FILE########
__FILENAME__ = list_mount_points
# Copyright (C) 2009-2011 Andrea Francia Trivolzio(PV) Italy

def mount_points():
    try:
	return list(mount_points_from_getmnt())
    except AttributeError:
        return mount_points_from_df()

def mount_points_from_getmnt():
    for elem in _mounted_filesystems_from_getmnt():
        yield elem.mount_dir

def mount_points_from_df():
    import subprocess
    df_output = subprocess.Popen(["df", "-P"], stdout=subprocess.PIPE).stdout
    return list(_mount_points_from_df_output(df_output))

def _mount_points_from_df_output(df_output):
    def skip_header():
	df_output.readline()
    def chomp(string):
	return string.rstrip('\n')

    skip_header()
    for line in df_output:
	line = chomp(line)
	yield line.split(None, 5)[-1]

def _mounted_filesystems_from_getmnt() :
    from ctypes import Structure, c_char_p, c_int, c_void_p, cdll, POINTER
    from ctypes.util import find_library
    import sys
    class Filesystem:
        def __init__(self, mount_dir, type, name) :
            self.mount_dir = mount_dir
            self.type = type
            self.name = name
    class mntent_struct(Structure):
        _fields_ = [("mnt_fsname", c_char_p),  # Device or server for
                                               # filesystem.
                    ("mnt_dir", c_char_p),     # Directory mounted on.
                    ("mnt_type", c_char_p),    # Type of filesystem: ufs,
                                               # nfs, etc.
                    ("mnt_opts", c_char_p),    # Comma-separated options
                                               # for fs.
                    ("mnt_freq", c_int),       # Dump frequency (in days).
                    ("mnt_passno", c_int)]     # Pass number for `fsck'.

    if sys.platform == "cygwin":
        libc_name = "cygwin1.dll"
    else:
        libc_name = find_library("c")

    if libc_name == None :
        libc_name="/lib/libc.so.6" # fix for my Gentoo 4.0

    libc = cdll.LoadLibrary(libc_name)
    libc.getmntent.restype = POINTER(mntent_struct)
    libc.fopen.restype = c_void_p

    f = libc.fopen("/proc/mounts", "r")
    if f==None:
        f = libc.fopen("/etc/mtab", "r")
        if f == None:
            raise IOError("Unable to open /proc/mounts nor /etc/mtab")

    while True:
        entry = libc.getmntent(f)
        if bool(entry) == False:
            libc.fclose(f)
            break
        yield Filesystem(entry.contents.mnt_dir,
                         entry.contents.mnt_type,
                         entry.contents.mnt_fsname)

########NEW FILE########
__FILENAME__ = put
import os
import sys

from .fs import parent_of
from .fstab import Fstab
from .trash import EX_OK, EX_IOERR
from .trash import TrashDirectories
from .trash import backup_file_path_from
from .trash import logger
from .trash import version
from datetime import datetime

def main():
    return TrashPutCmd(
        sys.stdout,
        sys.stderr
    ).run(sys.argv)

class TrashPutCmd:
    def __init__(self, stdout, stderr, environ = os.environ, fstab = Fstab()):
        self.stdout   = stdout
        self.stderr   = stderr
        self.environ  = environ
        self.fstab    = fstab #TODO
        self.logger   = MyLogger(self.stderr)
        self.reporter = TrashPutReporter(self.logger)

    def run(self, argv):
        program_name = os.path.basename(argv[0])
        self.logger.use_program_name(program_name)

        parser = self.get_option_parser(program_name)
        (options, args) = parser.parse_args(argv[1:])
        if options.verbose: self.logger.be_verbose()

        if len(args) <= 0:
            parser.error("Please specify the files to trash.")

        self.trashcan = GlobalTrashCan(
                reporter = self.reporter,
                volume_of = self.fstab.volume_of,
                environ = self.environ,
                fs = RealFs(),
                getuid = os.getuid,
                now = datetime.now)
        self.trash_all(args)

        return self.reporter.exit_code()

    def trash_all(self, args):
        for arg in args :
            self.trashcan.trash(arg)

    def get_option_parser(self, program_name):
        from optparse import OptionParser

        parser = OptionParser(prog=program_name,
                              usage="%prog [OPTION]... FILE...",
                              description="Put files in trash",
                              version="%%prog %s" % version,
                              formatter=NoWrapFormatter(),
                              epilog=epilog)
        parser.add_option("-d", "--directory", action="store_true",
                          help="ignored (for GNU rm compatibility)")
        parser.add_option("-f", "--force", action="store_true",
                          help="ignored (for GNU rm compatibility)")
        parser.add_option("-i", "--interactive", action="store_true",
                          help="ignored (for GNU rm compatibility)")
        parser.add_option("-r", "-R", "--recursive", action="store_true",
                          help="ignored (for GNU rm compatibility)")
        parser.add_option("-v", "--verbose", action="store_true",
                          help="explain what is being done", dest="verbose")
        def patched_print_help():
            encoding = parser._get_encoding(self.stdout)
            self.stdout.write(parser.format_help().encode(encoding, "replace"))
        def patched_error(msg):
            parser.print_usage(self.stderr)
            parser.exit(2, "%s: error: %s\n" % (program_name, msg))
        def patched_exit(status=0, msg=None):
            if msg: self.stderr.write(msg)
            import sys
            sys.exit(status)

        parser.print_help = patched_print_help
        parser.error = patched_error
        parser.exit = patched_exit
        return parser

epilog="""\
To remove a file whose name starts with a `-', for example `-foo',
use one of these commands:

    trash -- -foo

    trash ./-foo

Report bugs to http://code.google.com/p/trash-cli/issues"""

class MyLogger:
    def __init__(self, stderr):
        self.program_name = 'ERROR'
        self.stderr=stderr
        self.verbose = False
    def use_program_name(self, program_name):
        self.program_name = program_name
    def be_verbose(self):
        self.verbose = True
    def info(self,message):
        if self.verbose:
            self.emit(message)
    def warning(self,message):
        self.emit(message)
    def emit(self, message):
        self.stderr.write("%s: %s\n" % (self.program_name,message))

from optparse import IndentedHelpFormatter
class NoWrapFormatter(IndentedHelpFormatter) :
    def _format_text(self, text) :
        "[Does not] format a text, return the text as it is."
        return text

class NullObject:
    def __getattr__(self, name):
        return lambda *argl,**args:None

class TrashPutReporter:
    def __init__(self, logger = NullObject()):
        self.logger = logger
        self.some_file_has_not_be_trashed = False
        self.no_argument_specified = False
    def unable_to_trash_dot_entries(self,file):
        self.logger.warning("cannot trash %s `%s'" % (describe(file), file))
    def unable_to_trash_file(self,f):
        self.logger.warning("cannot trash %s `%s'" % (describe(f), f))
        self.some_file_has_not_be_trashed = True
    def file_has_been_trashed_in_as(self, trashee, trash_directory, destination):
        self.logger.info("`%s' trashed in %s" % (trashee,
                                                 shrinkuser(trash_directory)))
    def found_unsercure_trash_dir_symlink(self, trash_dir_path):
        self.logger.info("found unsecure .Trash dir (should not be a symlink): %s"
                % trash_dir_path)
    def invalid_top_trash_is_not_a_dir(self, trash_dir_path):
        self.logger.info("found unusable .Trash dir (should be a dir): %s"
                % trash_dir_path)
    def found_unsecure_trash_dir_unsticky(self, trash_dir_path):
        self.logger.info("found unsecure .Trash dir (should be sticky): %s"
                % trash_dir_path)
    def unable_to_trash_file_in_because(self,
                                        file_to_be_trashed,
                                        trash_directory, error):
        self.logger.info("Failed to trash %s in %s, because :%s" % (
           file_to_be_trashed, shrinkuser(trash_directory), error))
    def exit_code(self):
        if not self.some_file_has_not_be_trashed:
            return EX_OK
        else:
            return EX_IOERR

def describe(path):
    """
    Return a textual description of the file pointed by this path.
    Options:
     - "symbolic link"
     - "directory"
     - "`.' directory"
     - "`..' directory"
     - "regular file"
     - "regular empty file"
     - "non existent"
     - "entry"
    """
    if os.path.islink(path):
        return 'symbolic link'
    elif os.path.isdir(path):
        if path == '.':
            return 'directory'
        elif path == '..':
            return 'directory'
        else:
            if os.path.basename(path) == '.':
                return "`.' directory"
            elif os.path.basename(path) == '..':
                return "`..' directory"
            else:
                return 'directory'
    elif os.path.isfile(path):
        if os.path.getsize(path) == 0:
            return 'regular empty file'
        else:
            return 'regular file'
    elif not os.path.exists(path):
        return 'non existent'
    else:
        return 'entry'

class RealFs:
    def __init__(self):
        import os
        from . import fs
        self.move           = fs.move
        self.atomic_write   = fs.atomic_write
        self.remove_file    = fs.remove_file
        self.ensure_dir     = fs.ensure_dir
        self.isdir          = os.path.isdir
        self.islink         = os.path.islink
        self.has_sticky_bit = fs.has_sticky_bit

class GlobalTrashCan:
    class NullReporter:
        def __getattr__(self,name):
            return lambda *argl,**args:None
    def __init__(self, environ, volume_of, reporter, fs, getuid, now):
        self.getuid        = getuid
        self.reporter      = reporter
        self.volume_of     = volume_of
        self.now           = now
        self.fs            = fs
        self.trash_directories = TrashDirectories(
                self.volume_of, getuid, None, environ)

    def trash(self, file) :
        """
        Trash a file in the appropriate trash directory.
        If the file belong to the same volume of the trash home directory it
        will be trashed in the home trash directory.
        Otherwise it will be trashed in one of the relevant volume trash
        directories.

        Each volume can have two trash directories, they are
            - $volume/.Trash/$uid
            - $volume/.Trash-$uid

        Firstly the software attempt to trash the file in the first directory
        then try to trash in the second trash directory.
        """

        if self._should_skipped_by_specs(file):
            self.reporter.unable_to_trash_dot_entries(file)
            return

        candidates = PossibleTrashDirectories(self.fs)
        candidates = self._possible_trash_directories_for(file, candidates)
        file_has_been_trashed = False
        for trash_dir in candidates.trash_dirs:
            if self._is_trash_dir_secure(trash_dir):
                if self._file_could_be_trashed_in(file, trash_dir.path):
                    try:
                        trashed_file = trash_dir.trash(file)
                        self.reporter.file_has_been_trashed_in_as(
                            file,
                            trashed_file['trash_directory'],
                            trashed_file['where_file_was_stored'])
                        file_has_been_trashed = True

                    except (IOError, OSError), error:
                        self.reporter.unable_to_trash_file_in_because(
                                file, trash_dir.path, str(error))

            if file_has_been_trashed: break

        if not file_has_been_trashed:
            self.reporter.unable_to_trash_file(file)

    def _is_trash_dir_secure(self, trash_dir):
        class ValidationOutput:
            def __init__(self):
                self.valid = True
            def not_valid_should_be_a_dir(_):
                self.reporter.invalid_top_trash_is_not_a_dir(
                        os.path.dirname(trash_dir.path))
                self.valid = False
            def not_valid_parent_should_not_be_a_symlink(_):
                self.reporter.found_unsercure_trash_dir_symlink(
                        os.path.dirname(trash_dir.path))
                self.valid = False
            def not_valid_parent_should_be_sticky(_):
                self.reporter.found_unsecure_trash_dir_unsticky(
                        os.path.dirname(trash_dir.path))
                self.valid = False
            def is_valid(self):
                self.valid = True
        output = ValidationOutput()
        trash_dir.checker.fs = self.fs
        trash_dir.checker.valid_to_be_written(trash_dir.path, output)
        return output.valid

    def _should_skipped_by_specs(self, file):
        basename = os.path.basename(file)
        return (basename == ".") or (basename == "..")

    def _file_could_be_trashed_in(self,file_to_be_trashed,trash_dir_path):
        return self.volume_of(trash_dir_path) == self.volume_of_parent(file_to_be_trashed)

    def _possible_trash_directories_for(self, file, candidates):
        volume = self.volume_of_parent(file)

        self.trash_directories.home_trash_dir(
                candidates.add_home_trash)
        self.trash_directories.volume_trash_dir1(
                volume, candidates.add_top_trash_dir)
        self.trash_directories.volume_trash_dir2(
                volume, candidates.add_alt_top_trash_dir)

        return candidates

    def volume_of_parent(self, file):
        return self.volume_of(parent_of(file))

class PossibleTrashDirectories:
    def __init__(self, fs):
        self.trash_dirs = []
        self.fs = fs
    def add_home_trash(self, path, volume):
        trash_dir = self._make_trash_dir(path, volume)
        trash_dir.store_absolute_paths()
        self.trash_dirs.append(trash_dir)
    def add_top_trash_dir(self, path, volume):
        trash_dir = self._make_trash_dir(path, volume)
        trash_dir.store_relative_paths()
        trash_dir.checker = TopTrashDirWriteRules(None)
        self.trash_dirs.append(trash_dir)
    def add_alt_top_trash_dir(self, path, volume):
        trash_dir = self._make_trash_dir(path, volume)
        trash_dir.store_relative_paths()
        self.trash_dirs.append(trash_dir)
    def _make_trash_dir(self, path, volume):
        return TrashDirectoryForPut(path, volume, fs = self.fs)

class TrashDirectoryForPut:
    from datetime import datetime
    def __init__(self, path, volume, now = datetime.now, fs = RealFs(),
                 realpath = os.path.realpath):
        self.path      = os.path.normpath(path)
        self.volume    = volume
        self.logger    = logger
        self.info_dir  = os.path.join(self.path, 'info')
        self.files_dir = os.path.join(self.path, 'files')
        class all_is_ok_checker:
            def valid_to_be_written(self, a, b): pass
            def check(self, a):pass
        self.checker      = all_is_ok_checker()
        self.now          = now
        self.move         = fs.move
        self.atomic_write = fs.atomic_write
        self.remove_file  = fs.remove_file
        self.ensure_dir   = fs.ensure_dir
        self.realpath     = realpath

        self.path_for_trash_info = OriginalLocation(self.realpath)

    def store_absolute_paths(self):
        self.path_for_trash_info.make_absolutes_paths()

    def store_relative_paths(self):
        self.path_for_trash_info.make_paths_relatives_to(self.volume)

    def trash(self, path):
        path = os.path.normpath(path)

        original_location = self.path_for_trash_info.for_file(path)

        basename = os.path.basename(original_location)
        content = self.format_trashinfo(original_location, self.now())
        trash_info_file = self.persist_trash_info( self.info_dir, basename,
                content)

        where_to_store_trashed_file = backup_file_path_from(trash_info_file)

        self.ensure_files_dir_exists()

        try :
            self.move(path, where_to_store_trashed_file)
        except IOError as e :
            self.remove_file(trash_info_file)
            raise e
        result = dict()
        result['trash_directory'] = self.path
        result['where_file_was_stored'] = where_to_store_trashed_file
        return result

    def format_trashinfo(self, original_location, deletion_date):
        def format_date(deletion_date):
            return deletion_date.strftime("%Y-%m-%dT%H:%M:%S")
        def format_original_location(original_location):
            import urllib
            return urllib.quote(original_location,'/')
        content = ("[Trash Info]\n" +
                   "Path=%s\n" % format_original_location(original_location) +
                   "DeletionDate=%s\n" % format_date(deletion_date))
        return content

    def ensure_files_dir_exists(self):
        self.ensure_dir(self.files_dir, 0700)

    def persist_trash_info(self, info_dir, basename, content) :
        """
        Create a .trashinfo file in the $trash/info directory.
        returns the created TrashInfoFile.
        """

        self.ensure_dir(info_dir, 0700)

        # write trash info
        index = 0
        while True :
            if index == 0 :
                suffix = ""
            elif index < 100:
                suffix = "_%d" % index
            else :
                import random
                suffix = "_%d" % random.randint(0, 65535)

            base_id = basename
            trash_id = base_id + suffix
            trash_info_basename = trash_id+".trashinfo"

            dest = os.path.join(info_dir, trash_info_basename)
            try :
                self.atomic_write(dest, content)
                self.logger.debug(".trashinfo created as %s." % dest)
                return dest
            except OSError:
                self.logger.debug("Attempt for creating %s failed." % dest)

            index += 1

        raise IOError()

def shrinkuser(path, environ=os.environ):
    import posixpath
    import re
    try:
        home_dir = environ['HOME']
        home_dir = posixpath.normpath(home_dir)
        if home_dir != '':
            path = re.sub('^' + re.escape(home_dir + os.path.sep),
                            '~' + os.path.sep, path)
    except KeyError:
        pass
    return path

class TopTrashDirWriteRules:
    def __init__(self, fs):
        self.fs = fs

    def valid_to_be_written(self, trash_dir_path, output):
        parent = os.path.dirname(trash_dir_path)
        if not self.fs.isdir(parent):
            output.not_valid_should_be_a_dir()
            return
        if self.fs.islink(parent):
            output.not_valid_parent_should_not_be_a_symlink()
            return
        if not self.fs.has_sticky_bit(parent):
            output.not_valid_parent_should_be_sticky()
            return
        output.is_valid()

class OriginalLocation:
    def __init__(self, realpath):
        self.realpath = realpath
        self.make_absolutes_paths()

    def make_paths_relatives_to(self, topdir):
        self.topdir = topdir

    def make_absolutes_paths(self):
        self.topdir = None

    def for_file(self, path):
        self.normalized_path = os.path.normpath(path)

        basename = os.path.basename(self.normalized_path)
        parent   = self._real_parent()

        if self.topdir != None:
            if (parent == self.topdir) or parent.startswith(self.topdir+os.path.sep) :
                parent = parent[len(self.topdir+os.path.sep):]

        result   = os.path.join(parent, basename)
        return result

    def _real_parent(self):
        parent   = os.path.dirname(self.normalized_path)
        return self.realpath(parent)

########NEW FILE########
__FILENAME__ = rm
import fnmatch
import os, sys

from trashcli.trash import TrashDir, parse_path
from trashcli.trash import TrashDirs
from trashcli.trash import TopTrashDirRules
from trashcli.trash import CleanableTrashcan
from trashcli.fs import FileSystemReader
from trashcli.fs import FileRemover

class Main:
    def run(self, argv):
        args = argv[1:]
        self.exit_code = 0

        if not args:
            self.stderr.write('Usage:\n'
                              '    trash-rm PATTERN\n'
                              '\n'
                              'Please specify PATTERN\n')
            self.exit_code = 8
            return

        trashcan = CleanableTrashcan(FileRemover())
        cmd = Filter(trashcan.delete_trashinfo_and_backup_copy)
        cmd.use_pattern(args[0])
        file_reader = FileSystemReader()
        listing = ListTrashinfos(cmd.delete_if_matches)
        top_trashdir_rules = TopTrashDirRules(file_reader)
        trashdirs   = TrashDirs(self.environ, self.getuid,
                                list_volumes = self.list_volumes,
                                top_trashdir_rules = top_trashdir_rules)
        trashdirs.on_trash_dir_found = listing.list_from_volume_trashdir

        trashdirs.list_trashdirs()

def main():
    from trashcli.list_mount_points import mount_points
    main              = Main()
    main.environ      = os.environ
    main.getuid       = os.getuid
    main.list_volumes = mount_points
    main.stderr       = sys.stderr

    main.run(sys.argv)

    return main.exit_code

class Filter:
    def __init__(self, trashcan):
        self.delete = trashcan
    def use_pattern(self, pattern):
        self.pattern = pattern
    def delete_if_matches(self, original_location, info_file):
        basename = os.path.basename(original_location)
        if fnmatch.fnmatchcase(basename, self.pattern):
            self.delete(info_file)

class ListTrashinfos:
    def __init__(self, out):
        self.out = out
    def list_from_home_trashdir(self, trashdir_path):
        self.list_from_volume_trashdir(trashdir_path, '/')
    def list_from_volume_trashdir(self, trashdir_path, volume):
        self.volume = volume
        self.trashdir = TrashDir(FileSystemReader())
        self.trashdir.open(trashdir_path, volume)
        self.trashdir.each_trashinfo(self._report_original_location)
    def _report_original_location(self, trashinfo_path):
        file_reader = FileSystemReader()
        trashinfo = file_reader.contents_of(trashinfo_path)
        path = parse_path(trashinfo)
        complete_path = os.path.join(self.volume, path)
        self.out(complete_path, trashinfo_path)

if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = trash
# Copyright (C) 2007-2011 Andrea Francia Trivolzio(PV) Italy
from __future__ import absolute_import

version='0.12.10.3~'

import os
import logging
from .fstab import Fstab

logger=logging.getLogger('trashcli.trash')
logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler())

# Error codes (from os on *nix, hard coded for Windows):
EX_OK    = getattr(os, 'EX_OK'   ,  0)
EX_USAGE = getattr(os, 'EX_USAGE', 64)
EX_IOERR = getattr(os, 'EX_IOERR', 74)

from .fs import list_files_in_dir
import os
from .fs import remove_file
from .fs import move, mkdirs

class TrashDirectory:
    def __init__(self, path, volume):
        self.path      = os.path.normpath(path)
        self.volume    = volume
        self.logger    = logger
        self.info_dir  = os.path.join(self.path, 'info')
        self.files_dir = os.path.join(self.path, 'files')
        def warn_non_trashinfo():
            self.logger.warning("Non .trashinfo file in info dir")
        self.on_non_trashinfo_found = warn_non_trashinfo

    def trashed_files(self) :
        # Only used by trash-restore
        for info_file in self.all_info_files():
            try:
                yield self._create_trashed_file_from_info_file(info_file)
            except ValueError:
                self.logger.warning("Non parsable trashinfo file: %s" % info_file)
            except IOError as e:
                self.logger.warning(str(e))

    def all_info_files(self) :
        'Returns a generator of "Path"s'
        try :
            for info_file in list_files_in_dir(self.info_dir):
                if not os.path.basename(info_file).endswith('.trashinfo') :
                    self.on_non_trashinfo_found()
                else :
                    yield info_file
        except OSError: # when directory does not exist
            pass

    def _create_trashed_file_from_info_file(self, trashinfo_file_path):

        trash_info2 = LazyTrashInfoParser(
                lambda:contents_of(trashinfo_file_path), self.volume)

        original_location = trash_info2.original_location()
        deletion_date     = trash_info2.deletion_date()
        backup_file_path  = backup_file_path_from(trashinfo_file_path)

        return TrashedFile(original_location, deletion_date,
                trashinfo_file_path, backup_file_path, self)

def backup_file_path_from(trashinfo_file_path):
    trashinfo_basename = os.path.basename(trashinfo_file_path)
    backupfile_basename = trashinfo_basename[:-len('.trashinfo')]
    info_dir = os.path.dirname(trashinfo_file_path)
    trash_dir = os.path.dirname(info_dir)
    files_dir = os.path.join(trash_dir, 'files')
    return os.path.join(files_dir, backupfile_basename)

class HomeTrashCan:
    def __init__(self, environ):
        self.environ = environ
    def path_to(self, out):
        if 'XDG_DATA_HOME' in self.environ:
            out('%(XDG_DATA_HOME)s/Trash' % self.environ)
        elif 'HOME' in self.environ:
            out('%(HOME)s/.local/share/Trash' % self.environ)

class TrashDirectories:
    def __init__(self, volume_of, getuid, mount_points, environ):
        self.home_trashcan = HomeTrashCan(environ)
        self.volume_of = volume_of
        self.getuid = getuid
        self.mount_points = mount_points
    def all_trashed_files(self):
        for trash_dir in self.all_trash_directories():
            for trashedfile in trash_dir.trashed_files():
                yield trashedfile
    def all_trash_directories(self):
        collected = []
        def add_trash_dir(path, volume):
            collected.append(TrashDirectory(path, volume))

        self.home_trash_dir(add_trash_dir)
        for volume in self.mount_points:
            self.volume_trash_dir1(volume, add_trash_dir)
            self.volume_trash_dir2(volume, add_trash_dir)

        return collected
    def home_trash_dir(self, out) :
        self.home_trashcan.path_to(lambda path:
                out(path, self.volume_of(path)))
    def volume_trash_dir1(self, volume, out):
        out(
            path   = os.path.join(volume, '.Trash/%s' % self.getuid()),
            volume = volume)
    def volume_trash_dir2(self, volume, out):
        out(
            path   = os.path.join(volume, ".Trash-%s" % self.getuid()),
            volume = volume)

class TrashedFile:
    """
    Represent a trashed file.
    Each trashed file is persisted in two files:
     - $trash_dir/info/$id.trashinfo
     - $trash_dir/files/$id

    Properties:
     - path : the original path from where the file has been trashed
     - deletion_date : the time when the file has been trashed (instance of
                       datetime)
     - info_file : the file that contains information (instance of Path)
     - actual_path : the path where the trashed file has been placed after the
                     trash opeartion (instance of Path)
     - trash_directory :
    """
    def __init__(self, path, deletion_date, info_file, actual_path,
            trash_directory):
        self.path = path
        self.deletion_date = deletion_date
        self.info_file = info_file
        self.actual_path = actual_path
        self.trash_directory = trash_directory
        self.original_file = actual_path

    def restore(self, dest=None) :
        if dest is not None:
            raise NotImplementedError("not yet supported")
        if os.path.exists(self.path):
            raise IOError('Refusing to overwrite existing file "%s".' % os.path.basename(self.path))
        else:
            parent = os.path.dirname(self.path)
            mkdirs(parent)

        move(self.original_file, self.path)
        remove_file(self.info_file)

def getcwd_as_realpath(): return os.path.realpath(os.curdir)

import sys
class RestoreCmd:
    def __init__(self, stdout, stderr, environ, exit, input,
                 curdir = getcwd_as_realpath, version = version):
        self.out      = stdout
        self.err      = stderr
        self.exit     = exit
        self.input    = input
        fstab = Fstab()
        self.trashcan = TrashDirectories(
                volume_of     = fstab.volume_of,
                getuid        = os.getuid,
                mount_points  = fstab.mount_points(),
                environ       = environ)
        self.curdir   = curdir
        self.version = version
    def run(self, args = sys.argv):
        if '--version' in args[1:]:
            command = os.path.basename(args[0])
            self.println('%s %s' %(command, self.version))
            return

        trashed_files = []
        self.for_all_trashed_file_in_dir(trashed_files.append, self.curdir())

        if not trashed_files:
            self.report_no_files_found()
        else :
            for i, trashedfile in enumerate(trashed_files):
                self.println("%4d %s %s" % (i, trashedfile.deletion_date, trashedfile.path))
            index=self.input("What file to restore [0..%d]: " % (len(trashed_files)-1))
            if index == "" :
                self.println("Exiting")
            else :
                index = int(index)
                try:
                    trashed_files[index].restore()
                except IOError as e:
                    self.printerr(e)
                    self.exit(1)
    def for_all_trashed_file_in_dir(self, action, dir):
        def is_trashed_from_curdir(trashedfile):
            return trashedfile.path.startswith(dir + os.path.sep)
        for trashedfile in filter(is_trashed_from_curdir,
                                  self.trashcan.all_trashed_files()) :
            action(trashedfile)
    def report_no_files_found(self):
        self.println("No files trashed from current dir ('%s')" % self.curdir())
    def println(self, line):
        self.out.write(line + '\n')
    def printerr(self, msg):
        self.err.write('%s\n' % msg)

from .fs import FileSystemReader, contents_of, FileRemover

class ListCmd:
    def __init__(self, out, err, environ, list_volumes, getuid,
                 file_reader   = FileSystemReader(),
                 version       = version):

        self.output      = self.Output(out, err)
        self.err         = self.output.err
        self.contents_of = file_reader.contents_of
        self.version     = version
        top_trashdir_rules = TopTrashDirRules(file_reader)
        self.trashdirs = TrashDirs(environ, getuid,
                                   list_volumes = list_volumes,
                                   top_trashdir_rules=top_trashdir_rules)
        self.harvester = Harvester(file_reader)

    def run(self, *argv):
        parse=Parser()
        parse.on_help(PrintHelp(self.description, self.output.println))
        parse.on_version(PrintVersion(self.output.println, self.version))
        parse.as_default(self.list_trash)
        parse(argv)
    def list_trash(self):
        self.harvester.on_volume = self.output.set_volume_path
        self.harvester.on_trashinfo_found = self._print_trashinfo

        self.trashdirs.on_trashdir_skipped_because_parent_not_sticky = self.output.top_trashdir_skipped_because_parent_not_sticky
        self.trashdirs.on_trashdir_skipped_because_parent_is_symlink = self.output.top_trashdir_skipped_because_parent_is_symlink
        self.trashdirs.on_trash_dir_found = self.harvester._analize_trash_directory

        self.trashdirs.list_trashdirs()
    def _print_trashinfo(self, path):
        try:
            contents = self.contents_of(path)
        except IOError as e :
            self.output.print_read_error(e)
        else:
            deletion_date = parse_deletion_date(contents) or unknown_date()
            try:
                path = parse_path(contents)
            except ParseError:
                self.output.print_parse_path_error(path)
            else:
                self.output.print_entry(deletion_date, path)
    def description(self, program_name, printer):
        printer.usage('Usage: %s [OPTIONS...]' % program_name)
        printer.summary('List trashed files')
        printer.options(
           "  --version   show program's version number and exit",
           "  -h, --help  show this help message and exit")
        printer.bug_reporting()
    class Output:
        def __init__(self, out, err):
            self.out = out
            self.err = err
        def println(self, line):
            self.out.write(line+'\n')
        def error(self, line):
            self.err.write(line+'\n')
        def print_read_error(self, error):
            self.error(str(error))
        def print_parse_path_error(self, offending_file):
            self.error("Parse Error: %s: Unable to parse Path." % (offending_file))
        def top_trashdir_skipped_because_parent_not_sticky(self, trashdir):
            self.error("TrashDir skipped because parent not sticky: %s"
                    % trashdir)
        def top_trashdir_skipped_because_parent_is_symlink(self, trashdir):
            self.error("TrashDir skipped because parent is symlink: %s"
                    % trashdir)
        def set_volume_path(self, volume_path):
            self.volume_path = volume_path
        def print_entry(self, maybe_deletion_date, relative_location):
            import os
            original_location = os.path.join(self.volume_path, relative_location)
            self.println("%s %s" %(maybe_deletion_date, original_location))

def do_nothing(*argv, **argvk): pass
class Parser:
    def __init__(self):
        self.default_action = do_nothing
        self.argument_action = do_nothing
        self.short_options = ''
        self.long_options = []
        self.actions = dict()
        self._on_invalid_option = do_nothing

    def __call__(self, argv):
        program_name = argv[0]
        from getopt import getopt, GetoptError

        try:
            options, arguments = getopt(argv[1:],
                                        self.short_options,
                                        self.long_options)
        except GetoptError, e:
            invalid_option = e.opt
            self._on_invalid_option(program_name, invalid_option)
        else:
            for option, value in options:
                if option in self.actions:
                    self.actions[option](program_name)
                    return
            for argument in arguments:
                self.argument_action(argument)
            self.default_action()

    def on_invalid_option(self, action):
        self._on_invalid_option = action

    def on_help(self, action):
        self.add_option('help', action, 'h')

    def on_version(self, action):
        self.add_option('version', action)

    def add_option(self, long_option, action, short_aliases=''):
        self.long_options.append(long_option)
        self.actions['--' + long_option] = action
        for short_alias in short_aliases:
            self.add_short_option(short_alias, action)

    def add_short_option(self, short_option, action):
        self.short_options += short_option
        self.actions['-' + short_option] = action

    def on_argument(self, argument_action):
        self.argument_action = argument_action
    def as_default(self, default_action):
        self.default_action = default_action

class CleanableTrashcan:
    def __init__(self, file_remover):
        self._file_remover = file_remover
    def delete_orphan(self, path_to_backup_copy):
        self._file_remover.remove_file(path_to_backup_copy)
    def delete_trashinfo_and_backup_copy(self, trashinfo_path):
        backup_copy = self._path_of_backup_copy(trashinfo_path)
        self._file_remover.remove_file_if_exists(backup_copy)
        self._file_remover.remove_file(trashinfo_path)
    def _path_of_backup_copy(self, path_to_trashinfo):
        from os.path import dirname as parent_of, join, basename
        trash_dir = parent_of(parent_of(path_to_trashinfo))
        return join(trash_dir, 'files', basename(path_to_trashinfo)[:-len('.trashinfo')])

class ExpiryDate:
    def __init__(self, contents_of, now, trashcan):
        self._contents_of  = contents_of
        self._now          = now
        self._maybe_delete = self._delete_unconditionally
        self._trashcan = trashcan
    def set_max_age_in_days(self, arg):
        self.max_age_in_days = int(arg)
        self._maybe_delete = self._delete_according_date
    def delete_if_expired(self, trashinfo_path):
        self._maybe_delete(trashinfo_path)
    def _delete_according_date(self, trashinfo_path):
        contents = self._contents_of(trashinfo_path)
        ParseTrashInfo(
            on_deletion_date=IfDate(
                OlderThan(self.max_age_in_days, self._now),
                lambda: self._delete_unconditionally(trashinfo_path)
            ),
        )(contents)
    def _delete_unconditionally(self, trashinfo_path):
        self._trashcan.delete_trashinfo_and_backup_copy(trashinfo_path)

class TrashDirs:
    def __init__(self, environ, getuid, list_volumes, top_trashdir_rules):
        self.getuid             = getuid
        self.mount_points       = list_volumes
        self.top_trashdir_rules = top_trashdir_rules
        self.home_trashcan      = HomeTrashCan(environ)
        # events
        self.on_trash_dir_found                            = lambda trashdir, volume: None
        self.on_trashdir_skipped_because_parent_not_sticky = lambda trashdir: None
        self.on_trashdir_skipped_because_parent_is_symlink = lambda trashdir: None
    def list_trashdirs(self):
        self.emit_home_trashcan()
        self._for_each_volume_trashcan()
    def emit_home_trashcan(self):
        def return_result_with_volume(trashcan_path):
            self.on_trash_dir_found(trashcan_path, '/')
        self.home_trashcan.path_to(return_result_with_volume)
    def _for_each_volume_trashcan(self):
        for volume in self.mount_points():
            self.emit_trashcans_for(volume)
    def emit_trashcans_for(self, volume):
        self.emit_trashcan_1_for(volume)
        self.emit_trashcan_2_for(volume)
    def emit_trashcan_1_for(self,volume):
        top_trashdir_path = os.path.join(volume, '.Trash/%s' % self.getuid())
        class IsValidOutput:
            def not_valid_parent_should_not_be_a_symlink(_):
                self.on_trashdir_skipped_because_parent_is_symlink(top_trashdir_path)
            def not_valid_parent_should_be_sticky(_):
                self.on_trashdir_skipped_because_parent_not_sticky(top_trashdir_path)
            def is_valid(_):
                self.on_trash_dir_found(top_trashdir_path, volume)
        self.top_trashdir_rules.valid_to_be_read(top_trashdir_path, IsValidOutput())
    def emit_trashcan_2_for(self, volume):
        alt_top_trashdir = os.path.join(volume, '.Trash-%s' % self.getuid())
        self.on_trash_dir_found(alt_top_trashdir, volume)

from datetime import datetime
class EmptyCmd:
    def __init__(self, out, err, environ, list_volumes,
                 now           = datetime.now,
                 file_reader   = FileSystemReader(),
                 getuid        = os.getuid,
                 file_remover  = FileRemover(),
                 version       = version):

        self.out          = out
        self.err          = err
        self.file_reader  = file_reader
        top_trashdir_rules = TopTrashDirRules(file_reader)
        self.trashdirs = TrashDirs(environ, getuid,
                                   list_volumes = list_volumes,
                                   top_trashdir_rules = top_trashdir_rules)
        self.harvester = Harvester(file_reader)
        self.version      = version
        self._cleaning    = CleanableTrashcan(file_remover)
        self._expiry_date = ExpiryDate(file_reader.contents_of, now,
                                       self._cleaning)

    def run(self, *argv):
        self.exit_code     = EX_OK

        parse = Parser()
        parse.on_help(PrintHelp(self.description, self.println))
        parse.on_version(PrintVersion(self.println, self.version))
        parse.on_argument(self._expiry_date.set_max_age_in_days)
        parse.as_default(self._empty_all_trashdirs)
        parse.on_invalid_option(self.report_invalid_option_usage)

        parse(argv)

        return self.exit_code

    def report_invalid_option_usage(self, program_name, option):
        self.err.write(
            "{program_name}: invalid option -- '{option}'\n".format(**locals()))
        self.exit_code |= EX_USAGE

    def description(self, program_name, printer):
        printer.usage('Usage: %s [days]' % program_name)
        printer.summary('Purge trashed files.')
        printer.options(
           "  --version   show program's version number and exit",
           "  -h, --help  show this help message and exit")
        printer.bug_reporting()
    def _empty_all_trashdirs(self):
        self.harvester.on_trashinfo_found = self._expiry_date.delete_if_expired
        self.harvester.on_orphan_found = self._cleaning.delete_orphan
        self.trashdirs.on_trash_dir_found = self.harvester._analize_trash_directory
        self.trashdirs.list_trashdirs()
    def println(self, line):
        self.out.write(line + '\n')

class Harvester:
    def __init__(self, file_reader):
        self.file_reader = file_reader
        self.trashdir = TrashDir(self.file_reader)

        self.on_orphan_found                               = do_nothing
        self.on_trashinfo_found                            = do_nothing
        self.on_volume                                     = do_nothing
    def _analize_trash_directory(self, trash_dir_path, volume_path):
        self.on_volume(volume_path)
        self.trashdir.open(trash_dir_path, volume_path)
        self.trashdir.each_trashinfo(self.on_trashinfo_found)
        self.trashdir.each_orphan(self.on_orphan_found)

class IfDate:
    def __init__(self, date_criteria, then):
        self.date_criteria = date_criteria
        self.then          = then
    def __call__(self, date2):
        if self.date_criteria(date2):
            self.then()
class OlderThan:
    def __init__(self, days_ago, now):
        from datetime import timedelta
        self.limit_date = now() - timedelta(days=days_ago)
    def __call__(self, deletion_date):
        return deletion_date < self.limit_date

class PrintHelp:
    def __init__(self, description, println):
        class Printer:
            def __init__(self, println):
                self.println = println
            def usage(self, usage):
                self.println(usage)
                self.println('')
            def summary(self, summary):
                self.println(summary)
                self.println('')
            def options(self, *line_describing_option):
                self.println('Options:')
                for line in line_describing_option:
                    self.println(line)
                self.println('')
            def bug_reporting(self):
                self.println("Report bugs to http://code.google.com/p/trash-cli/issues")
        self.description  = description
        self.printer      = Printer(println)

    def __call__(self, program_name):
        self.description(program_name, self.printer)

class PrintVersion:
    def __init__(self, println, version):
        self.println      = println
        self.version      = version
    def __call__(self, program_name):
        self.println("%s %s" % (program_name, self.version))

class TopTrashDirRules:
    def __init__(self, fs):
        self.fs = fs

    def valid_to_be_read(self, path, output):
        parent_trashdir = os.path.dirname(path)
        if not self.fs.exists(path):
            return
        if not self.fs.is_sticky_dir(parent_trashdir):
            output.not_valid_parent_should_be_sticky()
            return
        if self.fs.is_symlink(parent_trashdir):
            output.not_valid_parent_should_not_be_a_symlink()
            return
        else:
            output.is_valid()

class Dir:
    def __init__(self, path, entries_if_dir_exists):
        self.path                  = path
        self.entries_if_dir_exists = entries_if_dir_exists
    def entries(self):
        return self.entries_if_dir_exists(self.path)
    def full_path(self, entry):
        return os.path.join(self.path, entry)

class TrashDir:
    def __init__(self, file_reader):
        self.file_reader    = file_reader
    def open(self, path, volume_path):
        self.trash_dir_path = path
        self.volume_path    = volume_path
        self.files_dir      = Dir(self._files_dir(),
                                  self.file_reader.entries_if_dir_exists)
    def each_orphan(self, action):
        for entry in self.files_dir.entries():
            trashinfo_path = self._trashinfo_path_from_file(entry)
            file_path = self.files_dir.full_path(entry)
            if not self.file_reader.exists(trashinfo_path): action(file_path)
    def _entries_if_dir_exists(self, path):
        return self.file_reader.entries_if_dir_exists(path)

    def each_trashinfo(self, action):
        for entry in self._trashinfo_entries():
            action(os.path.join(self._info_dir(), entry))
    def _info_dir(self):
        return os.path.join(self.trash_dir_path, 'info')
    def _trashinfo_path_from_file(self, file_entry):
        return os.path.join(self._info_dir(), file_entry + '.trashinfo')
    def _files_dir(self):
        return os.path.join(self.trash_dir_path, 'files')
    def _trashinfo_entries(self, on_non_trashinfo=do_nothing):
        for entry in self._entries_if_dir_exists(self._info_dir()):
            if entry.endswith('.trashinfo'):
                yield entry
            else:
                on_non_trashinfo()

class ParseError(ValueError): pass

class LazyTrashInfoParser:
    def __init__(self, contents, volume_path):
        self.contents    = contents
        self.volume_path = volume_path
    def deletion_date(self):
        return parse_deletion_date(self.contents())
    def _path(self):
        return parse_path(self.contents())
    def original_location(self):
        return os.path.join(self.volume_path, self._path())

def maybe_parse_deletion_date(contents):
    result = Basket(unknown_date())
    ParseTrashInfo(
            on_deletion_date = lambda date: result.collect(date),
            on_invalid_date = lambda: result.collect(unknown_date())
    )(contents)
    return result.collected

def unknown_date():
    return '????-??-?? ??:??:??'

class ParseTrashInfo:
    def __init__(self,
                 on_deletion_date = do_nothing,
                 on_invalid_date = do_nothing,
                 on_path = do_nothing):
        self.found_deletion_date = on_deletion_date
        self.found_invalid_date = on_invalid_date
        self.found_path = on_path
    def __call__(self, contents):
        from datetime import datetime
        import urllib
        for line in contents.split('\n'):
            if line.startswith('DeletionDate='):
                try:
                    date = datetime.strptime(line, "DeletionDate=%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    self.found_invalid_date()
                else:
                    self.found_deletion_date(date)

            if line.startswith('Path='):
                path=urllib.unquote(line[len('Path='):])
                self.found_path(path)

class Basket:
    def __init__(self, initial_value = None):
        self.collected = initial_value
    def collect(self, value):
        self.collected = value
def parse_deletion_date(contents):
    result = Basket()
    ParseTrashInfo(on_deletion_date=result.collect)(contents)
    return result.collected

def parse_path(contents):
    import urllib
    for line in contents.split('\n'):
        if line.startswith('Path='):
            return urllib.unquote(line[len('Path='):])
    raise ParseError('Unable to parse Path')


########NEW FILE########
__FILENAME__ = test_fake_fstab
from trashcli.fstab import FakeFstab

from nose.tools import assert_equals
from nose.tools import istest
from nose.tools import assert_items_equal

class TestFakeFstab:
    def setUp(self):
        self.fstab = FakeFstab()

    @istest
    def on_default(self):
        self.assert_mount_points_are('/')

    @istest
    def it_should_accept_fake_mount_points(self):
        self.fstab.add_mount('/fake')

        self.assert_mount_points_are('/', '/fake')

    @istest
    def root_is_not_duplicated(self):
        self.fstab.add_mount('/')

        self.assert_mount_points_are('/')

    @istest
    def test_something(self):
        fstab = FakeFstab()
        fstab.add_mount('/fake')
        assert_equals('/fake', fstab.volume_of('/fake/foo'))

    def assert_mount_points_are(self, *expected_mounts):
        expected_mounts = list(expected_mounts)
        actual_mounts = list(self.fstab.mount_points())
        assert_items_equal(expected_mounts, list(self.fstab.mount_points()),
                'Expected: %s\n'
                'Found: %s\n' % (expected_mounts, actual_mounts))


########NEW FILE########
__FILENAME__ = test_fake_ismount
from trashcli.fstab import FakeIsMount

from nose.tools import istest
from nose.tools import assert_false
from nose.tools import assert_true

@istest
class OnDefault:
    def setUp(self):
        self.ismount = FakeIsMount()

    @istest
    def by_default_root_is_mount(self):

        assert_true(self.ismount('/'))

    @istest
    def while_by_default_any_other_is_not_a_mount_point(self):

        assert_false(self.ismount('/any/other'))

@istest
class WhenOneFakeVolumeIsDefined:
    def setUp(self):
        self.ismount = FakeIsMount()
        self.ismount.add_mount('/fake-vol')

    @istest
    def accept_fake_mount_point(self):

        assert_true(self.ismount('/fake-vol'))

    @istest
    def other_still_are_not_mounts(self):

        assert_false(self.ismount('/other'))

    @istest
    def dont_get_confused_by_traling_slash(self):

        assert_true(self.ismount('/fake-vol/'))

@istest
class WhenMultipleFakesMountPoints:
    def setUp(self):
        self.ismount = FakeIsMount()
        self.ismount.add_mount('/vol1')
        self.ismount.add_mount('/vol2')

    @istest
    def recognize_both(self):
        assert_true(self.ismount('/vol1'))
        assert_true(self.ismount('/vol2'))
        assert_false(self.ismount('/other'))

@istest
def should_handle_relative_volumes():
    ismount = FakeIsMount()
    ismount.add_mount('fake-vol')
    assert_true(ismount('fake-vol'))

########NEW FILE########
__FILENAME__ = test_global_trashcan
from mock import Mock
from nose.tools import istest

from trashcli.put import GlobalTrashCan

class TestGlobalTrashCan:
    def setUp(self):
        self.reporter = Mock()
        self.fs = Mock()
        self.volume_of = Mock()
        self.volume_of.return_value = '/'

        self.trashcan = GlobalTrashCan(
                volume_of = self.volume_of,
                reporter = self.reporter,
                getuid = lambda:123,
                now = None,
                environ = dict(),
                fs = self.fs)

    @istest
    def should_report_when_trash_fail(self):
        self.fs.move.side_effect = IOError

        self.trashcan.trash('non-existent')

        self.reporter.unable_to_trash_file.assert_called_with('non-existent')

    @istest
    def should_not_delete_a_dot_entru(self):

        self.trashcan.trash('.')

        self.reporter.unable_to_trash_dot_entries.assert_called_with('.')

    @istest
    def bug(self):
        self.fs.mock_add_spec([
            'move',
            'atomic_write',
            'remove_file',
            'ensure_dir',

            'isdir',
            'islink',
            'has_sticky_bit',
            ], True)
        self.fs.islink.side_effect = (lambda path: { '/.Trash':False }[path])
        self.volume_of.side_effect = (lambda path: {
            '/foo': '/',
            '': '/',
            '/.Trash/123': '/',
            }[path])

        self.trashcan.trash('foo')

    def test_what_happen_when_trashing_with_trash_dir(self):
        from trashcli.put import TrashDirectoryForPut
        fs = Mock()
        now = Mock()
        fs.mock_add_spec([
            'move', 'atomic_write', 'remove_file', 'ensure_dir',
            ], True)

        from nose import SkipTest
        raise SkipTest()

        trash_dir = TrashDirectoryForPut('/path', '/volume', now, fs)

        trash_dir.trash('garbage')


########NEW FILE########
__FILENAME__ = test_home_fallback
from mock import Mock, call, ANY

from trashcli.fstab import FakeFstab
from trashcli.put import GlobalTrashCan
from nose.tools import assert_equals

class TestHomeFallback:
    def setUp(self):
        self.reporter = Mock()
        mount_points = ['/', 'sandbox/other_partition']
        self.fs = Mock()
        self.trashcan = GlobalTrashCan(
                reporter = self.reporter,
                getuid = lambda: 123,
                volume_of = self.fake_volume_of(mount_points),
                now = None,
                environ = dict(),
                fs = self.fs)

    def test_should_skip_top_trash_if_does_not_exists(self):
        self.fs.mock_add_spec(['isdir', 'islink', 'move', 'atomic_write',
            'remove_file', 'ensure_dir'])
        self.fs.isdir.side_effect = lambda x:['.Trash'][False]
        self.fs.islink.side_effect = lambda x:['.Trash'][False]

        self.trashcan.trash('sandbox/foo')

        assert_equals([
            call.isdir('.Trash'),
            call.islink('.Trash'),
            call.ensure_dir('.Trash/123/info', 448),
            call.atomic_write('.Trash/123/info/foo.trashinfo', ANY),
            call.ensure_dir('.Trash/123/files', 448),
            call.move('sandbox/foo', '.Trash/123/files/foo')
        ], self.fs.mock_calls)

    def fake_volume_of(self, volumes):
        fstab = FakeFstab()
        for vol in volumes:
            fstab.add_mount(vol)
        return fstab.volume_of

from trashcli.trash import TrashDirectories
class TestTrashDirectories:
    def test_list_all_directories(self):
        self.volume_of = Mock()
        self.getuid = lambda:123
        self.mount_points = ['/', '/mnt']
        self.environ = {'HOME': '~'}
        trash_dirs = TrashDirectories(
                volume_of    = self.volume_of,
                getuid       = self.getuid,
                mount_points = self.mount_points,
                environ      = self.environ)

        result = trash_dirs.all_trash_directories()
        paths = map(lambda td: td.path, result)

        assert_equals( ['~/.local/share/Trash',
                        '/.Trash/123',
                        '/.Trash-123',
                        '/mnt/.Trash/123',
                        '/mnt/.Trash-123'] , paths)


########NEW FILE########
__FILENAME__ = test_joining_paths
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

from nose.tools import assert_equals

def test_how_path_joining_works():
    from os.path import join
    assert_equals('/another-absolute', join('/absolute', '/another-absolute'))
    assert_equals('/absolute/relative', join('/absolute', 'relative'))
    assert_equals('/absolute', join('relative', '/absolute'))
    assert_equals('relative/relative', join('relative', 'relative'))
    assert_equals('/absolute', join('', '/absolute'))
    assert_equals('/absolute', join(None, '/absolute'))

########NEW FILE########
__FILENAME__ = test_list_all_trashinfo_contents
from mock import Mock, call
from nose.tools import assert_equals, assert_items_equal

class TestListing:
    def setUp(self):
        self.trashdir = Mock()
        self.trashinfo_reader = Mock()
        self.listing = Listing(self.trashdir, self.trashinfo_reader)

    def test_it_should_read_all_trashinfo_from_home_dir(self):

        self.listing.read_home_trashdir('/path/to/trash_dir')

        self.trashdir.list_trashinfos.assert_called_with(
                trashdir='/path/to/trash_dir',
                list_to=self.trashinfo_reader)

class TestTrashDirReader:
    def test_should_list_all_trashinfo_found(self):
        def files(path): yield 'file1'; yield 'file2'
        os_listdir = Mock(side_effect=files)
        trashdir = TrashDirReader(os_listdir)
        out = Mock()

        trashdir.list_trashinfos(trashdir='/path', list_to=out)

        assert_items_equal([call(trashinfo='/path/file1'),
                            call(trashinfo='/path/file2')], out.mock_calls)


class TrashDirReader:
    def __init__(self, os_listdir):
        self.os_listdir = os_listdir
    def list_trashinfos(self, trashdir, list_to):
        import os
        for entry in self.os_listdir(trashdir):
            full_path = os.path.join(trashdir, entry)
            list_to(trashinfo=full_path)

class Listing:
    def __init__(self, trashdir, trashinfo_reader):
        self.trashdir = trashdir
        self.trashinfo_reader = trashinfo_reader
    def read_home_trashdir(self, path):
        self.trashdir.list_trashinfos(trashdir=path,
                                      list_to=self.trashinfo_reader)

########NEW FILE########
__FILENAME__ = test_list_mount_points
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

import unittest
import StringIO
from trashcli.list_mount_points import _mount_points_from_df_output

class MountPointFromDirTest(unittest.TestCase):

    def test_should_skip_the_first_line(self):
	mount_points = _mount_points_from_df_output(StringIO.StringIO(
	'Filesystem         1024-blocks      Used Available Capacity Mounted on\n'
	))

	self.assertEquals([], list(mount_points))

    def test_should_return_the_first_mount_point(self):
	mount_points = _mount_points_from_df_output(StringIO.StringIO(
	'Filesystem         1024-blocks      Used Available Capacity Mounted on\n'
	'/dev/disk0s2         243862672 121934848 121671824      51% /\n'
	))

	self.assertEquals(['/'], list(mount_points))

    def test_should_return_multiple_mount_point(self):
	mount_points = _mount_points_from_df_output(StringIO.StringIO(
	'Filesystem         1024-blocks      Used Available Capacity Mounted on\n'
	'/dev/disk0s2         243862672 121934848 121671824      51% /\n'
	'/dev/disk1s1         156287996 123044260  33243736      79% /Volumes/DISK\n'
	))

	self.assertEquals(['/', '/Volumes/DISK'], list(mount_points))

    def test_should_return_mount_point_with_white_spaces(self):
	mount_points = _mount_points_from_df_output(StringIO.StringIO(
	'Filesystem         1024-blocks      Used Available Capacity Mounted on\n'
	'/dev/disk0s2         243862672 121934848 121671824      51% /\n'
	'/dev/disk1s1         156287996 123044260  33243736      79% /Volumes/with white spaces\n'
	))

	self.assertEquals(['/', '/Volumes/with white spaces'], list(mount_points))


########NEW FILE########
__FILENAME__ = test_make_script
from textwrap import dedent
from nose.tools import assert_equals
import mock
from mock import Mock
from setup import Scripts

class TestMakeScript:
    def setUp(self):
        self.make_file_executable = Mock()
        self.write_file = Mock()
        def capture(name, contents):
            self.name = name
            self.contents = contents
        self.write_file.side_effect = capture

        bindir = Scripts(
                make_file_executable = self.make_file_executable,
                write_file           = self.write_file)
        bindir.add_script('trash-put', 'trashcli.cmds', 'put')

    def test_should_set_executable_permission(self):
        self.make_file_executable.assert_called_with('trash-put')

    def test_should_write_the_script(self):
        self.write_file.assert_called_with( 'trash-put', mock.ANY)

    def test_the_script_should_call_the_right_function_from_the_right_module(self):
        args, kwargs = self.write_file.call_args
        (_, contents) = args
        expected = dedent("""\
            #!/usr/bin/env python
            from __future__ import absolute_import
            import sys
            from trashcli.cmds import put as main
            sys.exit(main())
            """)
        assert_equals(expected, contents,
                      "Expected:\n---\n%s---\n"
                      "Actual  :\n---\n%s---\n"
                      % (expected, contents))

class TestListOfCreatedScripts:
    def setUp(self):
        self.bindir = Scripts(
                make_file_executable = Mock(),
                write_file           = Mock())

    def test_is_empty_on_start_up(self):
        assert_equals(self.bindir.created_scripts, [])

    def test_collect_added_script(self):
        self.bindir.add_script('foo-command', 'foo-module', 'main')
        assert_equals(self.bindir.created_scripts, ['foo-command'])

########NEW FILE########
__FILENAME__ = test_method1_security_check
from mock import Mock

from integration_tests.files import require_empty_dir
from trashcli.put import TopTrashDirWriteRules

class TestMethod1VolumeTrashDirectory:
    def setUp(self):
        require_empty_dir('sandbox')
        self.fs = Mock()
        self.fs.isdir.return_value = True
        self.fs.islink.return_value = False
        self.fs.has_sticky_bit.return_value = True
        self.checker = TopTrashDirWriteRules(self.fs)
        self.out = Mock()

    def test_check_when_no_sticky_bit(self):
        self.fs.has_sticky_bit.return_value = False

        self.valid_to_be_written()

        self.out.not_valid_parent_should_be_sticky.assert_called_with()

    def test_check_when_no_dir(self):
        self.fs.isdir.return_value = False

        self.valid_to_be_written()

        self.out.not_valid_should_be_a_dir.assert_called_with()

    def test_check_when_is_symlink(self):
        self.fs.islink.return_value = True

        self.valid_to_be_written()

        self.out.not_valid_parent_should_not_be_a_symlink.assert_called_with()

    def test_check_pass(self):

        self.valid_to_be_written()

        self.out.is_valid()

    def valid_to_be_written(self):
        self.checker.valid_to_be_written('sandbox/trash-dir/123', self.out)

########NEW FILE########
__FILENAME__ = test_parser
from trashcli.trash import Parser
from mock import MagicMock
from nose.tools import istest

@istest
class describe_Parser():
    @istest
    def it_calls_the_actions_passing_the_program_name(self):
        on_raw = MagicMock()
        parser = Parser()
        parser.add_option('raw', on_raw)

        parser(['trash-list', '--raw'])

        on_raw.assert_called_with('trash-list')

    @istest
    def how_getopt_works_with_an_invalid_option(self):
        invalid_option_callback = MagicMock()
        parser = Parser()
        parser.on_invalid_option(invalid_option_callback)

        parser(['command-name', '-x'])

        invalid_option_callback.assert_called_with('command-name', 'x')

########NEW FILE########
__FILENAME__ = test_parsing_trashinfo_contents
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

from nose.tools import assert_equals, assert_raises
from nose.tools import istest

from datetime import datetime
from mock import MagicMock

from trashcli.trash import ParseTrashInfo

@istest
class describe_ParseTrashInfo2:
    @istest
    def it_should_parse_date(self):
        out = MagicMock()
        parse = ParseTrashInfo(on_deletion_date = out)

        parse('[Trash Info]\n'
              'Path=foo\n'
              'DeletionDate=1970-01-01T00:00:00\n')
        
        out.assert_called_with(datetime(1970,1,1,0,0,0))

    @istest
    def it_should_parse_path(self):
        out = MagicMock()
        self.parse = ParseTrashInfo(on_path = out)

        self.parse( '[Trash Info]\n'
                    'Path=foo\n'
                    'DeletionDate=1970-01-01T00:00:00\n')

        out.assert_called_with('foo')

from trashcli.trash import parse_deletion_date
from trashcli.trash import parse_path

def test_how_to_parse_date_from_trashinfo():
    from datetime import datetime
    assert_equals(datetime(2000,12,31,23,59,58), parse_deletion_date('DeletionDate=2000-12-31T23:59:58'))
    assert_equals(datetime(2000,12,31,23,59,58), parse_deletion_date('DeletionDate=2000-12-31T23:59:58\n'))
    assert_equals(datetime(2000,12,31,23,59,58), parse_deletion_date('[Trash Info]\nDeletionDate=2000-12-31T23:59:58'))

from trashcli.trash import maybe_parse_deletion_date

UNKNOWN_DATE='????-??-?? ??:??:??'
@istest
class describe_maybe_parse_deletion_date:
    @istest
    def on_trashinfo_without_date_parse_to_unknown_date(self):
        assert_equals(UNKNOWN_DATE, 
                      maybe_parse_deletion_date(a_trashinfo_without_deletion_date()))
    @istest
    def on_trashinfo_with_date_parse_to_date(self):
        from datetime import datetime
        example_date_as_string='2001-01-01T00:00:00'
        same_date_as_datetime=datetime(2001,1,1)
        assert_equals(same_date_as_datetime, 
                      maybe_parse_deletion_date(make_trashinfo(example_date_as_string)))
    @istest
    def on_trashinfo_with_invalid_date_parse_to_unknown_date(self):
        invalid_date='A long time ago'
        assert_equals(UNKNOWN_DATE,
                      maybe_parse_deletion_date(make_trashinfo(invalid_date)))

def test_how_to_parse_original_path():
    assert_equals('foo.txt',             parse_path('Path=foo.txt'))
    assert_equals('/path/to/be/escaped', parse_path('Path=%2Fpath%2Fto%2Fbe%2Fescaped'))


from trashcli.trash import LazyTrashInfoParser, ParseError

class TestParsing:
    def test_1(self):
        parser = LazyTrashInfoParser(lambda:("[Trash Info]\n"
                                             "Path=/foo.txt\n"), volume_path = '/')
        assert_equals('/foo.txt', parser.original_location())

class TestLazyTrashInfoParser_with_empty_trashinfo:
    def setUp(self):
        self.parser = LazyTrashInfoParser(contents=an_empty_trashinfo, volume_path='/')

    def test_it_raises_error_on_parsing_original_location(self):
        with assert_raises(ParseError):
            self.parser.original_location()

def a_trashinfo_without_deletion_date():
    return ("[Trash Info]\n"
            "Path=foo.txt\n")

def make_trashinfo(date):
    return ("[Trash Info]\n"
            "Path=foo.txt\n"
            "DeletionDate=%s" % date)
def an_empty_trashinfo():
    return ''




########NEW FILE########
__FILENAME__ = test_restore_cmd
from trashcli.trash import RestoreCmd
from nose.tools import assert_equals
from StringIO import StringIO

class TestTrashRestoreCmd:
    def test_should_print_version(self):
        stdout = StringIO()
        cmd = RestoreCmd(stdout=stdout,
                         stderr=None,
                         environ=None,
                         exit = None,
                         input=None,
                         version = '1.2.3')

        cmd.run(['trash-restore', '--version'])

        assert_equals('trash-restore 1.2.3\n', stdout.getvalue())


########NEW FILE########
__FILENAME__ = test_shrink_user
from nose.tools import assert_equals
from trashcli.put import shrinkuser

class TestTrashDirectoryName:
    def setUp(self):
        self.environ = {}

    def test_should_substitute_tilde_in_place_of_home_dir(self):
        self.environ['HOME']='/home/user'
        self.trash_dir = "/home/user/.local/share/Trash"
        self.assert_name_is('~/.local/share/Trash')

    def test_when_not_in_home_dir(self):
        self.environ['HOME']='/home/user'
        self.trash_dir = "/not-in-home/Trash"
        self.assert_name_is('/not-in-home/Trash')

    def test_tilde_works_also_with_trailing_slash(self):
        self.environ['HOME']='/home/user/'
        self.trash_dir = "/home/user/.local/share/Trash"
        self.assert_name_is('~/.local/share/Trash')

    def test_str_uses_tilde_with_many_slashes(self):
        self.environ['HOME']='/home/user////'
        self.trash_dir = "/home/user/.local/share/Trash"
        self.assert_name_is('~/.local/share/Trash')

    def test_dont_get_confused_by_empty_home_dir(self):
        self.environ['HOME']=''
        self.trash_dir = "/foo/Trash"
        self.assert_name_is('/foo/Trash')

    def assert_name_is(self, expected_name):
        shrinked = shrinkuser(self.trash_dir, self.environ)
        assert_equals(expected_name, shrinked)


########NEW FILE########
__FILENAME__ = test_storing_paths
from trashcli.put import TrashDirectoryForPut
from nose.tools import assert_equals
from mock import Mock

class TestHowOriginalLocationIsStored:
    def test_for_absolute_paths(self):
        fs = Mock()
        self.dir = TrashDirectoryForPut('/volume/.Trash', '/volume', fs = fs)
        self.dir.store_absolute_paths()

        self.assert_path_for_trashinfo_is('/file'            , '/file')
        self.assert_path_for_trashinfo_is('/file'            , '/dir/../file')
        self.assert_path_for_trashinfo_is('/outside/file'    , '/outside/file')
        self.assert_path_for_trashinfo_is('/volume/file'     , '/volume/file')
        self.assert_path_for_trashinfo_is('/volume/dir/file' , '/volume/dir/file')

    def test_for_relative_paths(self):
        self.dir = TrashDirectoryForPut('/volume/.Trash', '/volume')
        self.dir.store_relative_paths()

        self.assert_path_for_trashinfo_is('/file'         , '/file')
        self.assert_path_for_trashinfo_is('/file'         , '/dir/../file')
        self.assert_path_for_trashinfo_is('/outside/file' , '/outside/file')
        self.assert_path_for_trashinfo_is('file'          , '/volume/file')
        self.assert_path_for_trashinfo_is('dir/file'      , '/volume/dir/file')

    def assert_path_for_trashinfo_is(self, expected_value, file_to_be_trashed):
        result = self.dir.path_for_trash_info.for_file(file_to_be_trashed)
        assert_equals(expected_value, result)

########NEW FILE########
__FILENAME__ = test_trash
# Copyright (C) 2007-2011 Andrea Francia Trivolzio(PV) Italy

from __future__ import absolute_import

from trashcli.trash import TrashedFile
from integration_tests.files import write_file, require_empty_dir

import os
from unittest import TestCase

class TestTrashedFile(TestCase) :

    def test_restore_create_needed_directories(self):
        require_empty_dir('sandbox')

        write_file('sandbox/TrashDir/files/bar')
        instance = TrashedFile('sandbox/foo/bar',
                               'deletion_date', 'info_file',
                               'sandbox/TrashDir/files/bar', 'trash_dirctory')
        instance.restore()
        assert os.path.exists("sandbox/foo/bar")


########NEW FILE########
__FILENAME__ = test_trashdir
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

from nose.tools import assert_equals
from trashcli.trash import TrashDir
from trashcli.trash import TrashDirectory

class TestTrashDir:
    def test_path(self):
        trash_dir = TrashDirectory('/Trash-501', '/')
        assert_equals('/Trash-501', trash_dir.path)

class TestTrashDir_finding_orphans:
    def test(self):
        self.fs.create_fake_file('/info/foo.trashinfo')

        self.find_orphan()

        assert_equals([], self.orphan_found)

    def test2(self):
        self.fs.create_fake_file('/files/foo')

        self.find_orphan()

        assert_equals(['/files/foo'], self.orphan_found)

    def setUp(self):
        self.orphan_found=[]
        self.fs = FakeFileSystem()
        self.trashdir=TrashDir(self.fs)
        self.trashdir.open('/', None)

    def find_orphan(self):
        self.trashdir.each_orphan(self.orphan_found.append)

class FakeFileSystem:
    def __init__(self):
        self.files={}
        self.dirs={}
    def contents_of(self, path):
        return self.files[path]
    def exists(self, path):
        return path in self.files
    def entries_if_dir_exists(self, path):
        return self.dirs.get(path, [])
    def create_fake_file(self, path, contents=''):
        import os
        self.files[path] = contents
        self.create_fake_dir(os.path.dirname(path), os.path.basename(path))
    def create_fake_dir(self, dir_path, *dir_entries):
        self.dirs[dir_path] = dir_entries

class TestFakeFileSystem:
    def setUp(self):
        self.fs = FakeFileSystem()
    def test_you_can_read_from_files(self):
        self.fs.create_fake_file('/path/to/file', "file contents")
        assert_equals('file contents', self.fs.contents_of('/path/to/file'))
    def test_when_creating_a_fake_file_it_creates_also_the_dir(self):
        self.fs.create_fake_file('/dir/file')
        assert_equals(set(('file',)), set(self.fs.entries_if_dir_exists('/dir')))
    def test_you_can_create_multiple_fake_file(self):
        self.fs.create_fake_file('/path/to/file1', "one")
        self.fs.create_fake_file('/path/to/file2', "two")
        assert_equals('one', self.fs.contents_of('/path/to/file1'))
        assert_equals('two', self.fs.contents_of('/path/to/file2'))
    def test_no_file_exists_at_beginning(self):
        assert not self.fs.exists('/filename')
    def test_after_a_creation_the_file_exists(self):
        self.fs.create_fake_file('/filename')
        assert self.fs.exists('/filename')
    def test_create_fake_dir(self):
        self.fs.create_fake_dir('/etc', 'passwd', 'shadow', 'hosts')

        assert_equals(set(['passwd', 'shadow', 'hosts']),
                      set(self.fs.entries_if_dir_exists('/etc')))


########NEW FILE########
__FILENAME__ = test_trashdirs_how_to_list_them
from trashcli.trash import TrashDirs
from mock import Mock, call
from nose.tools import assert_equals

class TestListTrashinfo:
    def test_howto_list_trashdirs(self):
        out = Mock()
        environ = {'HOME':'/home/user'}
        trashdirs = TrashDirs(
                environ = environ,
                getuid = lambda:123,
                list_volumes = lambda:['/vol', '/vol2'],
                top_trashdir_rules = Mock(),
                )
        trashdirs.on_trash_dir_found = out
        trashdirs.list_trashdirs()

        assert_equals([call('/home/user/.local/share/Trash', '/'),
                       call('/vol/.Trash-123', '/vol'),
                       call('/vol2/.Trash-123', '/vol2')],
                      out.mock_calls)


########NEW FILE########
__FILENAME__ = test_trashing_a_file
from trashcli.put import TrashDirectoryForPut
from mock import Mock
from nose.tools import istest
from mock import ANY

class TestTrashing:
    def setUp(self):
        self.now = Mock()
        self.fs = Mock()
        self.trashdir = TrashDirectoryForPut('~/.Trash', '/',
                now = self.now,
                fs  = self.fs)
        self.trashdir.store_relative_paths()
        path_for_trash_info = Mock()
        path_for_trash_info.for_file.return_value = 'foo'
        self.trashdir.path_for_trash_info = path_for_trash_info

    @istest
    def the_file_should_be_moved_in_trash_dir(self):

        self.trashdir.trash('foo')

        self.fs.move.assert_called_with('foo', '~/.Trash/files/foo')

    @istest
    def test_should_create_a_trashinfo(self):

        self.trashdir.trash('foo')

        self.fs.atomic_write.assert_called_with('~/.Trash/info/foo.trashinfo', ANY)

    @istest
    def trashinfo_should_contains_original_location_and_deletion_date(self):
        from datetime import datetime

        self.now.return_value = datetime(2012, 9, 25, 21, 47, 39)
        self.trashdir.trash('foo')

        self.fs.atomic_write.assert_called_with(ANY,
                '[Trash Info]\n'
                'Path=foo\n'
                'DeletionDate=2012-09-25T21:47:39\n')

    @istest
    def should_rollback_trashinfo_creation_on_problems(self):
        self.fs.move.side_effect = IOError

        try: self.trashdir.trash('foo')
        except IOError: pass

        self.fs.remove_file.assert_called_with('~/.Trash/info/foo.trashinfo')

########NEW FILE########
__FILENAME__ = test_trash_dirs_listing
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

from trashcli.trash import TrashDirs
from nose.tools import istest, assert_in, assert_not_in
from mock import Mock

@istest
class TestTrashDirs_listing:
    @istest
    def the_method_2_is_always_in(self):
        self.uid = 123
        self.volumes = ['/usb']

        assert_in('/usb/.Trash-123', self.trashdirs())

    @istest
    def the_method_1_is_in_if_it_is_a_sticky_dir(self):
        self.uid = 123
        self.volumes = ['/usb']
        self.having_sticky_Trash_dir()

        assert_in('/usb/.Trash/123', self.trashdirs())

    @istest
    def the_method_1_is_not_considered_if_not_sticky_dir(self):
        self.uid = 123
        self.volumes = ['/usb']
        self.having_non_sticky_Trash_dir()

        assert_not_in('/usb/.Trash/123', self.trashdirs())

    @istest
    def should_return_home_trashcan_when_XDG_DATA_HOME_is_defined(self):
        self.environ['XDG_DATA_HOME'] = '~/.local/share'

        assert_in('~/.local/share/Trash', self.trashdirs())

    def trashdirs(self):
        result = []
        def append(trash_dir, volume):
            result.append(trash_dir)
        class FileReader:
            def is_sticky_dir(_, path):
                return self.Trash_dir_is_sticky
            def exists(_, path):
                return True
            def is_symlink(_, path):
                return False
        class FakeTopTrashDirRules:
            def valid_to_be_read(_, path, out):
                if self.Trash_dir_is_sticky:
                    out.is_valid()
                else:
                    out.not_valid_parent_should_be_sticky()
        trash_dirs = TrashDirs(
            environ=self.environ,
            getuid=lambda:self.uid,
            top_trashdir_rules = FakeTopTrashDirRules(),
            list_volumes = lambda: self.volumes,
        )
        trash_dirs.on_trash_dir_found = append
        trash_dirs.list_trashdirs()
        return result

    def setUp(self):
        self.uid = -1
        self.volumes = ()
        self.Trash_dir_is_sticky = not_important_for_now()
        self.environ = {}
    def having_sticky_Trash_dir(self): self.Trash_dir_is_sticky = True
    def having_non_sticky_Trash_dir(self): self.Trash_dir_is_sticky = False

def not_important_for_now(): None

from nose.tools import assert_equals
from mock import MagicMock
from trashcli.trash import TopTrashDirRules
@istest
class Describe_AvailableTrashDirs_when_parent_is_unsticky:
    def setUp(self):
        self.fs = MagicMock()
        self.dirs = TrashDirs(environ = {},
                              getuid = lambda:123,
                              top_trashdir_rules = TopTrashDirRules(self.fs),
                              list_volumes = lambda: ['/topdir'],
                              )
        self.dirs.on_trashdir_skipped_because_parent_not_sticky = Mock()
        self.dirs.on_trashdir_skipped_because_parent_is_symlink = Mock()
        self.fs.is_sticky_dir.side_effect = (
                lambda path: {'/topdir/.Trash':False}[path])

    def test_it_should_report_skipped_dir_non_sticky(self):
        self.fs.exists.side_effect = (
                lambda path: {'/topdir/.Trash/123':True}[path])

        self.dirs.list_trashdirs()

        (self.dirs.on_trashdir_skipped_because_parent_not_sticky.
                assert_called_with('/topdir/.Trash/123'))

    def test_it_shouldnot_care_about_non_existent(self):
        self.fs.exists.side_effect = (
                lambda path: {'/topdir/.Trash/123':False}[path])

        self.dirs.list_trashdirs()

        assert_equals([], self.dirs.on_trashdir_skipped_because_parent_not_sticky.mock_calls)

@istest
class Describe_AvailableTrashDirs_when_parent_is_symlink:
    def setUp(self):
        self.fs = MagicMock()
        self.dirs = TrashDirs(environ = {},
                              getuid = lambda:123,
                              top_trashdir_rules = TopTrashDirRules(self.fs),
                              list_volumes = lambda: ['/topdir'])
        self.fs.exists.side_effect = (lambda path: {'/topdir/.Trash/123':True}[path])
        self.symlink_error = Mock()
        self.dirs.on_trashdir_skipped_because_parent_is_symlink = self.symlink_error


    def test_it_should_skip_symlink(self):
        self.fs.is_sticky_dir.return_value = True
        self.fs.is_symlink.return_value    = True

        self.dirs.list_trashdirs()

        self.symlink_error.assert_called_with('/topdir/.Trash/123')


########NEW FILE########
__FILENAME__ = test_trash_put
# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy

from trashcli.put import TrashPutCmd

from nose.tools import istest, assert_in, assert_equals
from StringIO import StringIO
from integration_tests.assert_equals_with_unidiff import assert_equals_with_unidiff
from textwrap import dedent

class TrashPutTest:
    def run(self, *arg):
        self.stderr = StringIO()
        self.stdout = StringIO()
        args = ['trash-put'] + list(arg)
        cmd = TrashPutCmd(self.stdout, self.stderr)
        self._collect_exit_code(lambda:cmd.run(args))

    def _collect_exit_code(self, main_function):
        self.exit_code = 0
        try:
            result=main_function()
            if result is not None:
                self.exit_code=result
        except SystemExit, e:
            self.exit_code = e.code

    def stderr_should_be(self, expected_err):
        assert_equals_with_unidiff(expected_err, self._actual_stderr())

    def stdout_should_be(self, expected_out):
        assert_equals_with_unidiff(expected_out, self._actual_stdout())

    def _actual_stderr(self):
        return self.stderr.getvalue()

    def _actual_stdout(self):
        return self.stdout.getvalue()

class TestWhenNoArgs(TrashPutTest):
    def setUp(self):
        self.run()

    def test_should_report_usage(self):
        assert_line_in_text('Usage: trash-put [OPTION]... FILE...',
                            self.stderr.getvalue())
    def test_exit_code_should_be_not_zero(self):
        assert_equals(2, self.exit_code)


def assert_line_in_text(expected_line, text):
    assert_in(expected_line, text.splitlines(),
                'Line not found in text\n'
                'line: %s\n' % expected_line +
                'text:\n%s\n' % format(text.splitlines()))

@istest
class describe_TrashPutCmd(TrashPutTest):

    @istest
    def on_help_option_print_help(self):
        self.run('--help')
        self.stdout_should_be(dedent('''\
            Usage: trash-put [OPTION]... FILE...

            Put files in trash

            Options:
              --version            show program's version number and exit
              -h, --help           show this help message and exit
              -d, --directory      ignored (for GNU rm compatibility)
              -f, --force          ignored (for GNU rm compatibility)
              -i, --interactive    ignored (for GNU rm compatibility)
              -r, -R, --recursive  ignored (for GNU rm compatibility)
              -v, --verbose        explain what is being done

            To remove a file whose name starts with a `-', for example `-foo',
            use one of these commands:

                trash -- -foo

                trash ./-foo

            Report bugs to http://code.google.com/p/trash-cli/issues
            '''))

    @istest
    def it_should_skip_dot_entry(self):
        self.run('.')
        self.stderr_should_be("trash-put: cannot trash directory `.'\n")

    @istest
    def it_should_skip_dotdot_entry(self):
        self.run('..')
        self.stderr_should_be("trash-put: cannot trash directory `..'\n")

    @istest
    def it_should_print_usage_on_no_argument(self):
        self.run()
        self.stderr_should_be(
            'Usage: trash-put [OPTION]... FILE...\n'
            '\n'
            'trash-put: error: Please specify the files to trash.\n')
        self.stdout_should_be('')



########NEW FILE########
__FILENAME__ = test_trash_put_reporter
from nose.tools import assert_equals
from nose.tools import istest
from trashcli.put import TrashPutReporter

class TestTrashPutReporter:
    @istest
    def it_should_record_failures(self):

        reporter = TrashPutReporter()
        assert_equals(False, reporter.some_file_has_not_be_trashed)

        reporter.unable_to_trash_file('a file')
        assert_equals(True, reporter.some_file_has_not_be_trashed)


########NEW FILE########
__FILENAME__ = test_trash_rm
from nose.tools import istest, assert_items_equal
from mock import Mock, call

from trashcli.rm import Filter

class TestTrashRmCmd:
    @istest
    def a_star_matches_all(self):

        self.cmd.use_pattern('*')
        self.cmd.delete_if_matches('/foo', 'info/foo')
        self.cmd.delete_if_matches('/bar', 'info/bar')

        assert_items_equal([
            call('info/foo'),
            call('info/bar'),
            ], self.delete_trashinfo_and_backup_copy.mock_calls)

    @istest
    def basename_matches(self):

        self.cmd.use_pattern('foo')
        self.cmd.delete_if_matches('/foo', 'info/foo'),
        self.cmd.delete_if_matches('/bar', 'info/bar')

        assert_items_equal([
            call('info/foo'),
            ], self.delete_trashinfo_and_backup_copy.mock_calls)

    @istest
    def example_with_star_dot_o(self):

        self.cmd.use_pattern('*.o')
        self.cmd.delete_if_matches('/foo.h', 'info/foo.h'),
        self.cmd.delete_if_matches('/foo.c', 'info/foo.c'),
        self.cmd.delete_if_matches('/foo.o', 'info/foo.o'),
        self.cmd.delete_if_matches('/bar.o', 'info/bar.o')

        assert_items_equal([
            call('info/foo.o'),
            call('info/bar.o'),
            ], self.delete_trashinfo_and_backup_copy.mock_calls)

    def setUp(self):
        self.delete_trashinfo_and_backup_copy = Mock()
        self.cmd = Filter(self.delete_trashinfo_and_backup_copy)


########NEW FILE########
__FILENAME__ = test_volume_of
from trashcli.fstab import VolumeOf
from trashcli.fstab import FakeIsMount
from nose.tools import assert_equals, istest
import os

@istest
class TestVolumeOf:

    def setUp(self):
        self.ismount = FakeIsMount()
        self.volume_of = VolumeOf(ismount = self.ismount)
        self.volume_of.abspath = os.path.normpath

    @istest
    def return_the_containing_volume(self):
        self.ismount.add_mount('/fake-vol')
        assert_equals('/fake-vol', self.volume_of('/fake-vol/foo'))

    @istest
    def with_file_that_are_outside(self):
        self.ismount.add_mount('/fake-vol')
        assert_equals('/', self.volume_of('/foo'))

    @istest
    def it_work_also_with_relative_mount_point(self):
        self.ismount.add_mount('relative-fake-vol')
        assert_equals('relative-fake-vol', self.volume_of('relative-fake-vol/foo'))


########NEW FILE########
