__FILENAME__ = fabfile
from fabric.api import task, local
from fabric.contrib.console import confirm


pylint_disable = ",".join(["R0903", "C0103", "R0903", "F0401", "C0301"])
pep8_disable = ",".join(["E501"])


@task
def pyflakes():
    local("pyflakes .")


@task
def pep8():
    local("python tools/pep8.py --ignore={pep8_disable} --repeat *.py tvnamer/*.py tests/*.py".format(pep8_disable = pep8_disable))


@task
def pylint():
    local("pylint --reports=n --disable-msg={pylint_disable} *.py tvnamer/*.py tests/*.py".format(pylint_disable = pylint_disable))


@task(default=True)
def test():
    local("nosetests")


@task
def topypi():
    import sys
    sys.path.insert(0, ".")
    import tvnamer
    version = tvnamer.__version__
    tvnamer_version = ".".join(str(x) for x in version)

    msg = "Upload tvnamer {0} to PyPi?".format(tvnamer_version)
    if not confirm(msg, default = False):
        print "Cancelled"
        return

    local("python setup.py sdist register upload")

########NEW FILE########
__FILENAME__ = functional_runner
#!/usr/bin/env python

"""Functional-test runner for use in other tests

Useful functions are run_tvnamer and verify_out_data.

Simple example test:

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = None,
        with_input = "1\ny\n")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)

This runs tvnamer with no custom config (can be a string). It then
sends "1[return]y[return]" to the console UI, and verifies the file was
created correctly, in a way that nosetest displays useful info when an
expected file is not found.
"""

import os
import sys
import shutil
import tempfile
import subprocess

from tvnamer.unicode_helper import p, unicodify


try:
    # os.path.relpath was added in 2.6, use custom implimentation if not found
    relpath = os.path.relpath
except AttributeError:

    def relpath(path, start=None):
        """Return a relative version of a path"""

        if start is None:
            start = os.getcwd()

        start_list = os.path.abspath(start).split(os.path.sep)
        path_list = os.path.abspath(path).split(os.path.sep)

        # Work out how much of the filepath is shared by start and path.
        i = len(os.path.commonprefix([start_list, path_list]))

        rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
        if not rel_list:
            return os.getcwd()
        return os.path.join(*rel_list)


def make_temp_config(config):
    """Creates a temporary file containing the supplied config (string)
    """
    (fhandle, fname) = tempfile.mkstemp()
    f = open(fname, 'w+')
    f.write(config)
    f.close()

    return fname


def get_tvnamer_path():
    """Gets the path to tvnamer/main.py
    """
    cur_location, _ = os.path.split(os.path.abspath(sys.path[0]))
    for cdir in [".", ".."]:
        tvnamer_location = os.path.abspath(
            os.path.join(cur_location, cdir, "tvnamer", "main.py"))

        if os.path.isfile(tvnamer_location):
            return tvnamer_location
        else:
            p(tvnamer_location)
    else:
        raise IOError("tvnamer/main.py could not be found in . or ..")


def make_temp_dir():
    """Creates a temp folder and returns the path
    """
    return tempfile.mkdtemp()


def make_dummy_files(files, location):
    """Creates dummy files at location.
    """
    dummies = []
    for f in files:
        # Removing leading slash to prevent files being created outside
        # location. This is necessary because..
        # os.path.join('tempdir', '/otherpath/example.avi)
        # ..will return '/otherpath/example.avi'
        if f.startswith("/"):
            f = f.replace("/", "", 1)

        floc = os.path.join(location, f)

        dirnames, _ = os.path.split(floc)
        try:
            os.makedirs(dirnames)
        except OSError, e:
            if e.errno != 17:
                raise

        open(floc, "w").close()
        dummies.append(floc)

    return dummies


def clear_temp_dir(location):
    """Removes file or directory at specified location
    """
    p("Clearing %s" % unicode(location))
    shutil.rmtree(location)


def run_tvnamer(with_files, with_flags = None, with_input = "", with_config = None, run_on_directory = False):
    """Runs tvnamer on list of file-names in with_files.
    with_files is a list of strings.
    with_flags is a list of command line arguments to pass to tvnamer.
    with_input is the sent to tvnamer's stdin
    with_config is a string containing the tvnamer to run tvnamer with.

    Returns a dict with stdout, stderr and a list of files created
    """
    # Create dummy files (config and episodes)
    tvnpath = get_tvnamer_path()
    episodes_location = make_temp_dir()
    dummy_files = make_dummy_files(with_files, episodes_location)

    if with_config is not None:
        configfname = make_temp_config(with_config)
        conf_args = ['-c', configfname]
    else:
        conf_args = []

    if with_flags is None:
        with_flags = []

    if run_on_directory:
        files = [episodes_location]
    else:
        files = dummy_files

    # Construct command
    cmd = [sys.executable, tvnpath] + conf_args + with_flags + files
    p("Running command:")
    p(" ".join(cmd))


    proc = subprocess.Popen(
        cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT, # All stderr to stdout
        stdin = subprocess.PIPE)

    proc.stdin.write(with_input)
    output, _ = proc.communicate()
    output = unicodify(output)

    created_files = []
    for walkroot, walkdirs, walkfiles in os.walk(unicode(episodes_location)):
        curlist = [os.path.join(walkroot, name) for name in walkfiles]

        # Remove episodes_location from start of path
        curlist = [relpath(x, episodes_location) for x in curlist]

        created_files.extend(curlist)

    # Clean up dummy files and config
    clear_temp_dir(episodes_location)
    if with_config is not None:
        os.unlink(configfname)

    return {
        'output': output,
        'files': created_files,
        'returncode': proc.returncode}


def verify_out_data(out_data, expected_files, expected_returncode = 0):
    """Verifies the out_data from run_tvnamer contains the expected files.

    Prints the stdout/stderr/files, then asserts all files exist.
    If an assertion fails, nosetest will handily print the stdout/etc.
    """

    p("Return code: %d" % out_data['returncode'])

    p("Expected files:", expected_files)
    p("Got files:     ", [x for x in out_data['files']])

    p("\n" + "*" * 20 + "\n")
    p("output:\n")
    p(out_data['output'])

    # Check number of files
    if len(expected_files) != len(out_data['files']):
        raise AssertionError("Expected %d files, but got %d" % (
            len(expected_files),
            len(out_data['files'])))

    # Check all files were created
    for cur in expected_files:
        if cur not in out_data['files']:
            raise AssertionError("File named %r not created" % (cur))

    # Check exit code is zero
    if out_data['returncode'] != expected_returncode:
        raise AssertionError("Exit code was %d, not %d" % (out_data['returncode'], expected_returncode))

########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/env python

"""Helper functions for use in tests
"""

import os
import functools


def assertEquals(a, b):
    assert a == b, "Error, %r not equal to %r" % (a, b)


def assertType(obj, type):
    assert isinstance(obj, type), "Expecting %s, got %r" % (
        type(obj),
        type)


def expected_failure(test):
    """Used as a decorator on a test function. Skips the test if it
    fails, or fails the test if it passes (so the decorator can be
    removed)

    Kind of like the SkipTest nose plugin, but avoids tests being
    skipped quietly if they are fixed "accidentally"

    http://stackoverflow.com/q/9613932/745
    """

    @functools.wraps(test)
    def inner(*args, **kwargs):
        try:
            test(*args, **kwargs)
        except AssertionError:
            from nose.plugins.skip import SkipTest
            raise SkipTest("Expected failure failed, as expected")
        else:
            raise AssertionError('Failure expected')

    return inner


def expected_failure_travisci(test):
    """Like expected_failure, but only expects a failure when the
    env-var TRAVIS is "true"
    """

    @functools.wraps(test)
    def inner(*args, **kwargs):
        if os.getenv("TRAVIS", "false") == "true":
            try:
                test(*args, **kwargs)
            except AssertionError:
                from nose.plugins.skip import SkipTest
                raise SkipTest("Expected failure failed, as expected on Travis-CI")
            else:
                raise AssertionError('Failure expected on Travis-CI')

        else:
            return test(*args, **kwargs)

    return inner

########NEW FILE########
__FILENAME__ = test_absolute_number_ambiguity
#!/usr/bin/env python

"""Test ability to set the series name by series id
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_ambiguity_fix():
    """Test amiguous eisode number fix
    """

    conf = """
    {"always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['[ANBU-AonE]_Naruto_43_[3811CBB5].avi'],
        with_config = conf,
        with_flags = [],
        with_input = "")

    expected_files = ['[ANBU-AonE] Naruto - 43 - Killer Kunoichi and a Shaky Shikamaru [3811CBB5].avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_anime_filenames
#!/usr/bin/env python

"""Tests anime filename output
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_group():
    """Anime filename [#100]
    """
    out_data = run_tvnamer(
        with_files = ['[Some Group] Scrubs - 01 [A1B2C3].avi'],
        with_config = """
{
    "always_rename": true,
    "select_first": true,

    "filename_anime_with_episode": "[%(group)s] %(seriesname)s - %(episodenumber)s - %(episodename)s [%(crc)s]%(ext)s"
}
""")

    expected_files = ['[Some Group] Scrubs - 01 - My First Day [A1B2C3].avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_group_no_epname():
    """Anime filename, on episode with no name [#100]
    """
    out_data = run_tvnamer(
        with_files = ['[Some Group] Somefakeseries - 01 [A1B2C3].avi'],
        with_config = """
{
    "always_rename": true,
    "select_first": true,

    "filename_anime_without_episode": "[%(group)s] %(seriesname)s - %(episodenumber)s [%(crc)s]%(ext)s"
}
""")

    expected_files = ['[Some Group] Somefakeseries - 01 [A1B2C3].avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_configfunctional
#!/usr/bin/env python

"""Tests various configs load correctly
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr
from helpers import expected_failure


@attr("functional")
def test_batchconfig():
    """Test configured batch mode works
    """

    conf = """
    {"always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_skip_file_on_error():
    """Test the "skip file on error" config option works
    """

    conf = """
    {"skip_file_on_error": true,
    "always_rename": true}
    """

    out_data = run_tvnamer(
        with_files = ['a.fake.episode.s01e01.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['a.fake.episode.s01e01.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_do_not_skip_file_on_error():
    """Test setting "skip file on error" config option to False
    """

    conf = """
    {"skip_file_on_error": false,
    "always_rename": true}
    """

    out_data = run_tvnamer(
        with_files = ['a.fake.episode.s01e01.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['a fake episode - [01x01].avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_lowercase_names():
    """Test setting "lowercase_filename" config option
    """

    conf = """
    {"lowercase_filename": true,
    "always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['scrubs - [01x01] - my first day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replace_with_underscore():
    """Test custom blacklist to replace " " with "_"
    """

    conf = """
    {"custom_filename_character_blacklist": " ",
    "replace_blacklisted_characters_with": "_",
    "always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['Scrubs_-_[01x01]_-_My_First_Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
@expected_failure
def test_abs_epnmber():
    """Ensure the absolute episode number is available for custom
    filenames in config
    """


    conf = """
    {"filename_with_episode": "%(seriesname)s - %(absoluteepisode)s%(ext)s",
    "always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['Scrubs - 01.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_resolve_absoloute_episode():
    """Test resolving by absolute episode number
    """

    conf = """
    {"always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['[Bleachverse]_BLEACH_310.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['[Bleachverse] Bleach - 310 - Ichigo\'s Resolution.avi']

    verify_out_data(out_data, expected_files)

    print "Checking output files are re-parsable"
    out_data = run_tvnamer(
        with_files = expected_files,
        with_config = conf,
        with_input = "")

    expected_files = ['[Bleachverse] Bleach - 310 - Ichigo\'s Resolution.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_valid_extension_recursive():
    """When using valid_extensions in a custom config file, recursive search doesn't work. Github issue #36
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "valid_extensions": ["avi","mp4","m4v","wmv","mkv","mov","srt"],
    "recursive": true}
    """

    out_data = run_tvnamer(
        with_files = ['nested/dir/scrubs.s01e01.avi'],
        with_config = conf,
        with_input = "",
        run_on_directory = True)

    expected_files = ['nested/dir/Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replace_ands():
    """Test replace "and" "&"
    """

    conf = r"""
    {"always_rename": true,
    "select_first": true,
    "input_filename_replacements": [
        {"is_regex": true,
        "match": "(\\Wand\\W| & )",
        "replacement": " "}
    ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['Brothers.and.Sisters.S05E16.HDTV.XviD-LOL.avi'],
        with_config = conf,
        with_input = "",
        run_on_directory = True)

    expected_files = ['Brothers & Sisters - [05x16] - Home Is Where The Fort Is.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replace_ands_in_output_also():
    """Test replace "and" "&" for search, and replace & in output filename
    """

    conf = r"""
    {"always_rename": true,
    "select_first": true,
    "input_filename_replacements": [
        {"is_regex": true,
        "match": "(\\Wand\\W| & )",
        "replacement": " "}
    ],
    "output_filename_replacements": [
        {"is_regex": true,
        "match": " & ",
        "replacement": " and "}
    ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['Brothers.and.Sisters.S05E16.HDTV.XviD-LOL.avi'],
        with_config = conf,
        with_input = "",
        run_on_directory = True)

    expected_files = ['Brothers and Sisters - [05x16] - Home Is Where The Fort Is.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_force_overwrite_enabled():
    """Tests forcefully overwritting existing filenames
    """

    conf = r"""
    {"always_rename": true,
    "select_first": true,
    "overwrite_destination_on_rename": true
    }
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'Scrubs - [01x01] - My First Day.avi'],
        with_config = conf,
        with_input = "",
        run_on_directory = True)

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_force_overwrite_disabled():
    """Explicitly disabling forceful-overwrite
    """

    conf = r"""
    {"always_rename": true,
    "select_first": true,
    "overwrite_destination_on_rename": false
    }
    """

    out_data = run_tvnamer(
        with_files = ['Scrubs - [01x01] - My First Day.avi', 'scrubs - [01x01].avi'],
        with_config = conf,
        with_input = "",
        run_on_directory = True)

    expected_files = ['Scrubs - [01x01] - My First Day.avi', 'scrubs - [01x01].avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_force_overwrite_default():
    """Forceful-overwrite should be disabled by default
    """

    conf = r"""
    {"always_rename": true,
    "select_first": true
    }
    """

    out_data = run_tvnamer(
        with_files = ['Scrubs - [01x01] - My First Day.avi', 'scrubs - [01x01].avi'],
        with_config = conf,
        with_input = "",
        run_on_directory = True)

    expected_files = ['Scrubs - [01x01] - My First Day.avi', 'scrubs - [01x01].avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_titlecase():
    """Tests Title Case Option To Make Episodes Like This
    """

    conf = r"""
    {"always_rename": true,
    "select_first": true,
    "skip_file_on_error": false,
    "titlecase_filename": true
    }
    """

    out_data = run_tvnamer(
        with_files = ['this.is.a.fake.episode.s01e01.avi'],
        with_config = conf,
        with_input = "",
        run_on_directory = True)

    expected_files = ['This Is a Fake Episode - [01x01].avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_custom_replacement
#!/usr/bin/env python

"""Tests custom replacements on input/output files
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_simple_input_replacements():
    """Tests replacing strings in input files
    """
    out_data = run_tvnamer(
        with_files = ['scruuuuuubs.s01e01.avi'],
        with_config = """
{
    "input_filename_replacements": [
        {"is_regex": false,
        "match": "uuuuuu",
        "replacement": "u"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_simple_output_replacements():
    """Tests replacing strings in input files
    """
    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = """
{
    "output_filename_replacements": [
        {"is_regex": false,
        "match": "u",
        "replacement": "v"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrvbs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_regex_input_replacements():
    """Tests regex replacement in input files
    """
    out_data = run_tvnamer(
        with_files = ['scruuuuuubs.s01e01.avi'],
        with_config = """
{
    "input_filename_replacements": [
        {"is_regex": true,
        "match": "[u]+",
        "replacement": "u"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_regex_output_replacements():
    """Tests regex replacement in output files
    """
    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = """
{
    "output_filename_replacements": [
        {"is_regex": true,
        "match": "[ua]+",
        "replacement": "v"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrvbs - [01x01] - My First Dvy.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replacing_spaces():
    """Tests more practical use of replacements, removing spaces
    """
    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = """
{
    "output_filename_replacements": [
        {"is_regex": true,
        "match": "[ ]",
        "replacement": "."}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrubs.-.[01x01].-.My.First.Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replacing_ands():
    """Tests removind "and" and "&" from input files
    """
    out_data = run_tvnamer(
        with_files = ['Law & Order s01e01.avi'],
        with_config = """
{
    "input_filename_replacements": [
        {"is_regex": true,
        "match": "( and | & )",
        "replacement": " "}
    ],
    "output_filename_replacements": [
        {"is_regex": false,
        "match": " & ",
        "replacement": " and "}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Law and Order - [01x01] - Prescription for Death.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_multiple_replacements():
    """Tests multiple replacements on one file
    """
    out_data = run_tvnamer(
    with_files = ['scrubs.s01e01.avi'],
    with_config = """
{
    "output_filename_replacements": [
        {"is_regex": true,
        "match": "[ua]+",
        "replacement": "v"},
        {"is_regex": false,
        "match": "v",
        "replacement": "_"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scr_bs - [01x01] - My First D_y.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_fullpath_replacements():
    """Tests replacing strings in output path
    """
    out_data = run_tvnamer(
    with_files = ['scrubs.s01e01.avi'],
    with_config = """
{
    "move_files_enable": true,
    "move_files_destination": "%(seriesname)s",
    "move_files_fullpath_replacements": [
        {"is_regex": true,
        "match": "Scr.*?s",
        "replacement": "A Test"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['A Test/A Test - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_restoring_dot():
    """Test replace the parsed "Tosh 0" with "Tosh.0"
    """
    out_data = run_tvnamer(
        with_files = ['tosh.0.s03.e02.avi'],
        with_config = """
{
    "input_filename_replacements": [
        {"is_regex": false,
        "match": "tosh.0",
        "replacement": "tosh0"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Tosh.0 - [03x02] - Brian Atene.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replacement_order():
    """Ensure output replacements happen before the valid filename function is run
    """
    out_data = run_tvnamer(
        with_files = ['24.s03.e02.avi'],
        with_config = """
{
    "output_filename_replacements": [
        {"is_regex": false,
        "match": ":",
        "replacement": "-"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['24 - [03x02] - Day 3- 2-00 P.M.-3-00 P.M..avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replacement_preserve_extension():
    """Ensure with_extension replacement option defaults to preserving extension
    """
    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = """
{
    "output_filename_replacements": [
        {"is_regex": false,
        "match": "avi",
        "replacement": "ohnobroken"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replacement_including_extension():
    """Option to allow replacement search/replace to include file extension
    """
    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = """
{
    "output_filename_replacements": [
        {"is_regex": false,
        "with_extension": true,
        "match": "Day.avi",
        "replacement": "Day.nl.avi"}
    ],
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrubs - [01x01] - My First Day.nl.avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_datestamp_episode
#!/usr/bin/env python

"""Tests episodes based on dates, not season/episode numbers
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr
from nose.plugins.skip import SkipTest


@attr("functional")
def test_issue_56_dated_episode():
    """Season and episode should set correctly for date-parsed episodes
    """

    conf = """
    {"batch": true,
    "select_first": true,
    "filename_with_episode":  "%(seriesname)s %(date)s - %(episodename)s%(ext)s"}
    """

    out_data = run_tvnamer(
        with_files = ['tonight.show.conan.2009.06.05.hdtv.blah.avi'],
        with_config = conf)

    expected_files = ['The Tonight Show with Conan O\'Brien - [2009-06-05] - Ryan Seacrest, Patton Oswalt, Chickenfoot.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_date_in_s01e01_out():
    """File with date-stamp, outputs s01e01-ish name
    """


    raise SkipTest("Not yet done")


    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_with_episode": "%(seriesname)s - [%(seasonnumber)02dx%(episode)s] - %(episodename)s%(ext)s"}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.2001.10.02.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


def test_issue_31_twochar_year():
    """Fix for parsing rather ambigious dd.mm.yy being parsed as "0011"
    """

    from tvnamer.utils import handleYear

    assert handleYear("99") == 1999
    assert handleYear("79") == 1979

    assert handleYear("00") == 2000
    assert handleYear("20") == 2020

########NEW FILE########
__FILENAME__ = test_extension_pattern
#!/usr/bin/env python

"""Tests multi-episode filename generation
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_extension_pattern_default():
    """Test default extension handling, no language codes
    """

    conf = r"""
    {"extension_pattern": "(\\.[a-zA-Z0-9]+)$",
    "batch": true,
    "valid_extensions": ["avi", "srt"]}
    """

    input_files = [
        "scrubs.s01e01.hdtv.fake.avi",
        "scrubs.s01e01.hdtv.fake.srt",
        "my.name.is.earl.s01e01.fake.avi",
        "my.name.is.earl.s01e01.some.other.fake.eng.srt",
    ]
    expected_files = [
        "Scrubs - [01x01] - My First Day.avi",
        "Scrubs - [01x01] - My First Day.srt",
        "My Name Is Earl - [01x01] - Pilot.avi",
        "My Name Is Earl - [01x01] - Pilot.srt",
    ]

    out_data = run_tvnamer(
        with_files = input_files,
        with_config = conf,
        with_input = "")

    verify_out_data(out_data, expected_files)

@attr("functional")
def test_extension_pattern_custom():
    """Test custom extension pattern, multiple language codes
    """

    conf = r"""
    {"extension_pattern": "((\\.|-)(eng|cze|EN|CZ)(?=\\.(sub|srt)))?(\\.[a-zA-Z0-9]+)$",
    "batch": true,
    "valid_extensions": ["avi", "srt"]}
    """

    input_files = [
        "scrubs.s01e01.hdtv.fake.avi",
        "scrubs.s01e01.hdtv.fake.srt",
        "scrubs.s01e01.hdtv.fake-CZ.srt",
        "scrubs.s01e01.hdtv.fake-EN.srt",
        "my.name.is.earl.s01e01.fake.avi",
        "my.name.is.earl.s01e01.some.other.fake.eng.srt",
        "my.name.is.earl.s01e01.fake.cze.srt",
    ]
    expected_files = [
        "Scrubs - [01x01] - My First Day.avi",
        "Scrubs - [01x01] - My First Day.srt",
        "Scrubs - [01x01] - My First Day-CZ.srt",
        "Scrubs - [01x01] - My First Day-EN.srt",
        "My Name Is Earl - [01x01] - Pilot.avi",
        "My Name Is Earl - [01x01] - Pilot.eng.srt",
        "My Name Is Earl - [01x01] - Pilot.cze.srt",
    ]

    out_data = run_tvnamer(
        with_files = input_files,
        with_config = conf,
        with_input = "")

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_filename_blacklist
#!/usr/bin/env python

"""Tests ignoreing files by regexp (e.g. all files with "sample" in the name)
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_no_blacklist():
    """Tests empty list of filename regexps is parsed as expected
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": []}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s01e02.avi'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'Scrubs - [01x02] - My Mentor.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_partial_blacklist_using_simple_match():
    """Tests single match of filename blacklist using a simple match
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
        {"is_regex": false,
         "match": "s02e01"}
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s02e01.avi', 'scrubs.s02e02.avi'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'scrubs.s02e01.avi',
        'Scrubs - [02x02] - My Nightingale.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_partial_blacklist_using_regex():
    """Tests single match of filename blacklist using a regex match
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
        {"is_regex": true,
         "match": ".*s02e01.*"}
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s02e01.avi', 'scrubs.s02e02.avi'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'scrubs.s02e01.avi',
        'Scrubs - [02x02] - My Nightingale.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_partial_blacklist_using_mix():
    """Tests single match of filename blacklist using a mix of regex and simple match
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
        {"is_regex": true,
         "match": ".*s02e01.*"},
        {"is_regex": false,
         "match": "s02e02"}
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s02e01.avi', 'scrubs.s02e02.avi'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'scrubs.s02e01.avi',
        'scrubs.s02e02.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_full_blacklist():
    """Tests complete blacklist of all filenames with a regex
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
        {"is_regex": true,
         "match": ".*"}
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s02e01.avi', 'scrubs.s02e02.avi'],
        with_config = conf)

    expected_files = ['scrubs.s01e01.avi', 'scrubs.s02e01.avi', 'scrubs.s02e02.avi']

    verify_out_data(out_data, expected_files, expected_returncode = 2)


@attr("functional")
def test_dotfiles():
    """Tests blacklisting filename beginning with "."
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
        {"is_regex": true,
         "match": "^\\\\..*"}
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['.scrubs.s01e01.avi', 'scrubs.s02e02.avi'],
        with_config = conf)

    expected_files = ['.scrubs.s01e01.avi', 'Scrubs - [02x02] - My Nightingale.avi']

    verify_out_data(out_data, expected_files, expected_returncode = 0)


@attr("functional")
def test_blacklist_fullpath():
    """Blacklist against full path
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
        {"is_regex": true,
         "full_path": true,
         "match": ".*/subdir/.*"}
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['subdir/scrubs.s01e01.avi'],
        with_config = conf)

    expected_files = ['subdir/scrubs.s01e01.avi']

    verify_out_data(out_data, expected_files, expected_returncode = 2)


@attr("functional")
def test_blacklist_exclude_extension():
    """Blacklist against full path
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
        {"is_regex": true,
         "full_path": true,
         "exclude_extension": true,
         "match": "\\\\.avi"}
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf)

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files, expected_returncode = 0)


@attr("functional")
def test_simple_blacklist():
    """Blacklist with simple strings
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
            "scrubs.s02e01.avi"
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s02e01.avi', 'scrubs.s02e02.avi'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'scrubs.s02e01.avi',
        'Scrubs - [02x02] - My Nightingale.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_simple_blacklist_mixed():
    """Blacklist with simple strings, mixed with the more complex dict
    option (which allows regexs and matching against extension)
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "filename_blacklist": [
            "scrubs.s02e01.avi",
            {"is_regex": true,
             "match": ".*s\\\\d+e02.*"}
        ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s02e01.avi', 'scrubs.s02e02.avi'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'scrubs.s02e01.avi',
        'scrubs.s02e02.avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_fileparse_api
#!/usr/bin/env python

"""Tests the FileParser API
"""

from tvnamer.utils import FileParser, EpisodeInfo, DatedEpisodeInfo, NoSeasonEpisodeInfo
from helpers import assertType, assertEquals


def test_episodeinfo():
    """Parsing a s01e01 episode should return EpisodeInfo class
    """
    p = FileParser("scrubs.s01e01.avi").parse()
    assertType(p, EpisodeInfo)


def test_datedepisodeinfo():
    """Parsing a 2009.06.05 episode should return DatedEpisodeInfo class
    """
    p = FileParser("scrubs.2009.06.05.avi").parse()
    assertType(p, DatedEpisodeInfo)


def test_noseasonepisodeinfo():
    """Parsing a e23 episode should return NoSeasonEpisodeInfo class
    """
    p = FileParser("scrubs - e23.avi").parse()
    assertType(p, NoSeasonEpisodeInfo)


def test_episodeinfo_naming():
    """Parsing a s01e01 episode should return EpisodeInfo class
    """
    p = FileParser("scrubs.s01e01.avi").parse()
    assertType(p, EpisodeInfo)
    assertEquals(p.generateFilename(), "scrubs - [01x01].avi")


def test_datedepisodeinfo_naming():
    """Parsing a 2009.06.05 episode should return DatedEpisodeInfo class
    """
    p = FileParser("scrubs.2009.06.05.avi").parse()
    assertType(p, DatedEpisodeInfo)
    assertEquals(p.generateFilename(), "scrubs - [2009-06-05].avi")


def test_noseasonepisodeinfo_naming():
    """Parsing a e23 episode should return NoSeasonEpisodeInfo class
    """
    p = FileParser("scrubs - e23.avi").parse()
    assertType(p, NoSeasonEpisodeInfo)
    assertEquals(p.generateFilename(), "scrubs - [23].avi")

########NEW FILE########
__FILENAME__ = test_files
#!/usr/bin/env python

"""Test file names for tvnamer
"""

import datetime


files = {}

files['default_format'] = [
    {'input': 'Scrubs - [04x19] - My Best Laid Plans',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 4, 'episodenumbers': [19],
    'episodenames': ['My Best Laid Plans']},

    {'input': 'Scrubs - [02x11]',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 2, 'episodenumbers': [11],
    'episodenames': ['My Sex Buddy']},

    {'input': 'Scrubs - [04X19] - My Best Laid Plans',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 4, 'episodenumbers': [19],
    'episodenames': ['My Best Laid Plans']},
]

files['s01e01_format'] = [
    {'input': 'scrubs.s01e01',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': 'my.name.is.earl.s01e01',
    'parsedseriesname': 'my name is earl',
    'correctedseriesname': 'My Name Is Earl',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['Pilot']},

    {'input': 'scrubs.s01e24.blah.fake',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [24],
    'episodenames': ['My Last Day']},

    {'input': 'dexter.s04e05.720p.blah',
    'parsedseriesname': 'dexter',
    'correctedseriesname': 'Dexter',
    'seasonnumber': 4, 'episodenumbers': [5],
    'episodenames': ['Dirty Harry']},

    {'input': 'QI.S04E01.2006-09-29.blah',
    'parsedseriesname': 'QI',
    'correctedseriesname': 'QI',
    'seasonnumber': 4, 'episodenumbers': [1],
    'episodenames': ['Danger']},

    {'input': 'The Wire s05e10 30.mp4',
    'parsedseriesname': 'The Wire',
    'correctedseriesname': 'The Wire',
    'seasonnumber': 5, 'episodenumbers': [10],
    'episodenames': ['-30-']},

    {'input': 'Arrested Development - S2 E 02 - Dummy Ep Name.blah',
    'parsedseriesname': 'Arrested Development',
    'correctedseriesname': 'Arrested Development',
    'seasonnumber': 2, 'episodenumbers': [2],
    'episodenames': ['The One Where They Build a House']},

    {'input': 'Horizon - s2008e02 - Total Isolation.avi',
    'parsedseriesname': 'Horizon',
    'correctedseriesname': 'Horizon',
    'seasonnumber': 2008, 'episodenumbers': [2],
    'episodenames': ['Total Isolation']},

    {'input': 'Horizon.s2008e02.Total Isolation.avi',
    'parsedseriesname': 'Horizon',
    'correctedseriesname': 'Horizon',
    'seasonnumber': 2008, 'episodenumbers': [2],
    'episodenames': ['Total Isolation']},

    {'input': 'Horizon - [2008x03] - Total Isolation.avi',
    'parsedseriesname': 'Horizon',
    'correctedseriesname': 'Horizon',
    'seasonnumber': 2008, 'episodenumbers': [3],
    'episodenames': ['What on Earth is Wrong With Gravity?']},

    {'input': 'Scrubs.0101.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': 'Scrubs 1x01-720p.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': 'Scrubs - [s01e01].avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': 'Scrubs - [01.01].avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': '30 Rock [2.10] Episode 210.avi',
    'parsedseriesname': '30 Rock',
    'correctedseriesname': '30 Rock',
    'seasonnumber': 2, 'episodenumbers': [10],
    'episodenames': ['Episode 210']},

    {'input': 'scrubs.s01_e01.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': 'scrubs - s01 - e02 - something.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [2],
    'episodenames': ['My Mentor']},
]

files['misc'] = [
    {'input': 'Six.Feet.Under.S0201.test_testing-yay',
    'parsedseriesname': 'Six Feet Under',
    'correctedseriesname': 'Six Feet Under',
    'seasonnumber': 2, 'episodenumbers': [1],
    'episodenames': ['In the Game']},

    {'input': 'Sid.The.Science.Kid.E11.The.Itchy.Tag.WS.ABC.DeF-HIJK',
    'parsedseriesname': 'Sid The Science Kid',
    'correctedseriesname': 'Sid the Science Kid',
    'seasonnumber': None, 'episodenumbers': [11],
    'episodenames': ['The Itchy Tag']},

    {'input': 'Total Access - [01x01]',
    'parsedseriesname': 'total access',
    'correctedseriesname': 'Total Access 24/7',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['Episode #1']},

    {'input': 'Neighbours - Episode 5824 [S 6 - Ep 003] - Fri 15 Jan 2010 [KCRT].avi',
    'parsedseriesname': 'Neighbours',
    'correctedseriesname': 'Neighbours',
    'seasonnumber': 6, 'episodenumbers': [3],
    'episodenames': ['Episode 1350']},

    {'input': 'Scrubs Season 01 Episode 01 - The Series Title.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},
]

files['multiple_episodes'] = [
    {'input': 'Scrubs - [01x01-02-03]',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1, 2, 3],
    'episodenames': ['My First Day', 'My Mentor', 'My Best Friend\'s Mistake']},

    {'input': 'scrubs.s01e23e24',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [23, 24],
    'episodenames': ['My Hero', 'My Last Day']},

    {'input': 'scrubs.01x23x24',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [23, 24],
    'episodenames': ['My Hero', 'My Last Day']},

    {'input': 'scrubs.01x23-24',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [23, 24],
    'episodenames': ['My Hero', 'My Last Day']},

    {'input': 'Stargate SG-1 - [01x01-02]',
    'parsedseriesname': 'Stargate SG-1',
    'correctedseriesname': 'Stargate SG-1',
    'seasonnumber': 1, 'episodenumbers': [1, 2],
    'episodenames': ['Children of the Gods (1)', 'Children of the Gods (2)']},

    {'input': '[Lunar] Bleach - 11-12 [B937F496]',
    'parsedseriesname': 'Bleach',
    'correctedseriesname': 'Bleach',
    'seasonnumber': None, 'episodenumbers': [11, 12],
    'episodenames': ['The Legendary Quincy', 'A Gentle Right Arm']},

    {'input': 'scrubs.s01e01e02e03',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1, 2, 3],
    'episodenames': ['My First Day', 'My Mentor', 'My Best Friend\'s Mistake']},

    {'input': 'Scrubs - [02x01-03]',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 2, 'episodenumbers': [1, 2, 3],
    'episodenames': ['My Overkill', 'My Nightingale', 'My Case Study']},

    {'input': 'Scrubs - [02x01+02]',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 2, 'episodenumbers': [1, 2],
    'episodenames': ['My Overkill', 'My Nightingale']},

    {'input': 'Scrubs 2x01+02',
    'parsedseriesname': 'scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 2, 'episodenumbers': [1, 2],
    'episodenames': ['My Overkill', 'My Nightingale']},

    {'input': 'Flight.of.the.Conchords.S01E01-02.An.Ep.name.avi',
    'parsedseriesname': 'Flight of the Conchords',
    'correctedseriesname': 'Flight of the Conchords',
    'seasonnumber': 1, 'episodenumbers': [1, 2],
    'episodenames': ['Sally', 'Bret Gives Up the Dream']},

    {'input': 'Flight.of.the.Conchords.S01E02e01.An.Ep.name.avi',
    'parsedseriesname': 'Flight of the Conchords',
    'correctedseriesname': 'Flight of the Conchords',
    'seasonnumber': 1, 'episodenumbers': [1, 2],
    'episodenames': ['Sally', 'Bret Gives Up the Dream']},

    {'input': 'Scrubs s01e22 s01e23 s01e24.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [22, 23, 24],
    'episodenames': ['My Occurrence', 'My Hero', 'My Last Day']},

    {'input': 'Scrubs s01e22 s01e23.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [22, 23],
    'episodenames': ['My Occurrence', 'My Hero']},

    {'input': 'Scrubs - 01x22 01x23.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [22, 23],
    'episodenames': ['My Occurrence', 'My Hero']},

    {'input': 'Scrubs.01x22.01x23.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [22, 23],
    'episodenames': ['My Occurrence', 'My Hero']},

    {'input': 'Scrubs 1x22 1x23.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [22, 23],
    'episodenames': ['My Occurrence', 'My Hero']},

    {'input': 'Scrubs.S01E01-E04.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1, 2, 3, 4],
    'episodenames': ['My First Day', 'My Mentor', 'My Best Friend\'s Mistake', 'My Old Lady']},

]

files['unicode'] = [
    {'input': u'Carniv\xe0le 1x11 - The Day of the Dead',
    'parsedseriesname': u'Carniv\xe0le',
    'correctedseriesname': u'Carniv\xe0le',
    'seasonnumber': 1, 'episodenumbers': [11],
    'episodenames': ['The Day of the Dead']},

    {'input': u'T\xecnh Ng\u01b0\u1eddi Hi\u1ec7n \u0110\u1ea1i - [01x01]',
    'parsedseriesname': u'T\xecnh Ng\u01b0\u1eddi Hi\u1ec7n \u0110\u1ea1i',
    'correctedseriesname': u'Virtues Of Harmony II',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': [u'T\xecnh Ng\u01b0\u1eddi Hi\u1ec7n \u0110\u1ea1i - Virtues Of Harmony II']},

    {'input': u'The Big Bang Theory - S02E07 - The Panty Pi\xf1ata Polarization.avi',
    'parsedseriesname': u'The Big Bang Theory',
    'correctedseriesname': u'The Big Bang Theory',
    'seasonnumber': 2, 'episodenumbers': [7],
    'episodenames': [u'The Panty Pi\xf1ata Polarization']},

    {'input': u'NCIS - 1x16.avi',
    'parsedseriesname': u'NCIS',
    'correctedseriesname': u'NCIS',
    'seasonnumber': 1, 'episodenumbers': [16],
    'episodenames': [u'B\xeate Noire']},
]

files['anime'] = [
    {'input': '[Eclipse] Fullmetal Alchemist Brotherhood - 02 (1280x720 h264) [8452C4BF].mkv',
    'parsedseriesname': 'Fullmetal Alchemist Brotherhood',
    'correctedseriesname': 'Fullmetal Alchemist: Brotherhood',
    'seasonnumber': None, 'episodenumbers': [2],
    'episodenames': ['The First Day']},

    {'input': '[Shinsen-Subs] Armored Trooper Votoms - 01 [9E3F1D1C].mkv',
    'parsedseriesname': 'armored trooper votoms',
    'correctedseriesname': 'Armored Trooper VOTOMS',
    'seasonnumber': None, 'episodenumbers': [1],
    'episodenames': ['War\'s End']},

    {'input': '[Shinsen-Subs] Beet - 19 [24DAB497].mkv',
    'parsedseriesname': 'beet',
    'correctedseriesname': 'Beet the Vandel Buster',
    'seasonnumber': None, 'episodenumbers': [19],
    'episodenames': ['Threat of the Planet Earth']},

    {'input': '[AG-SHS]Victory_Gundam-03_DVD[FC6E3A6F].mkv',
    'parsedseriesname': 'victory gundam',
    'correctedseriesname': 'Mobile Suit Victory Gundam',
    'seasonnumber': None, 'episodenumbers': [3],
    'episodenames': ['Uso\'s Fight']},

    {'input': '[YuS-SHS]Gintama-24(H264)_[52CA4F8B].mkv',
    'parsedseriesname': 'gintama',
    'correctedseriesname': 'Gintama',
    'seasonnumber': None, 'episodenumbers': [24],
    'episodenames': ['Cute Faces Are Always Hiding Something']},

    {'input': '[Shinsen-Subs] True Mazinger - 07 [848x480 H.264 Vorbis][787D0074].mkv',
    'parsedseriesname': 'True Mazinger',
    'correctedseriesname': 'True Mazinger: Shocking! Z Chapter',
    'seasonnumber': None, 'episodenumbers': [7],
    'episodenames': ['Legend! The Mechanical Beasts of Bardos!']},

    {'input': '[BSS]_Tokyo_Magnitude_8.0_-_02_[0E5C4A40].mkv',
    'parsedseriesname': 'tokyo magnitude 8.0',
    'correctedseriesname': 'Tokyo Magnitude 8.0',
    'seasonnumber': None, 'episodenumbers': [2],
    'episodenames': ['Broken World']},

    {'input': 'Bleach - [310] - Ichigo\'s Resolution.avi',
    'parsedseriesname': 'Bleach',
    'correctedseriesname': 'Bleach',
    'seasonnumber': None, 'episodenumbers': [310],
    'episodenames': ['Ichigo\'s Resolution']},
]

files['date_based'] = [
    {'input': 'Scrubs.2001-10-02.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'episodenumbers': [datetime.date(2001, 10, 2)],
    'episodenames': ['My First Day']},

    {'input': 'Scrubs - 2001-10-02 - Old Episode Title.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'episodenumbers': [datetime.date(2001, 10, 2)],
    'episodenames': ['My First Day']},

    {'input': 'Scrubs - 2001.10.02 - Old Episode Title.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'episodenumbers': [datetime.date(2001, 10, 2)],
    'episodenames': ['My First Day']},

    {'input': 'yes.we.canberra.2010.08.18.pdtv.xvid',
    'parsedseriesname': 'yes we canberra',
    'correctedseriesname': 'Yes We Canberra',
    'episodenumbers': [datetime.date(2010, 8, 18)],
    'episodenames': ['Episode 4']},
]

files['x_of_x'] = [
    {'input': 'Scrubs.1of5.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': None, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': 'Scrubs part 1.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': None, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': 'Scrubs part 1 of 10.avi', # only one episode, as it's not "1 to 10"
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': None, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': 'Scrubs part 1 and part 2.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': None, 'episodenumbers': [1, 2],
    'episodenames': ['My First Day', 'My Mentor']},

    {'input': 'Scrubs part 1 to part 3.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': None, 'episodenumbers': [1, 2, 3],
    'episodenames': ['My First Day', 'My Mentor', 'My Best Friend\'s Mistake']},

    {'input': 'Scrubs part 1 to 4.avi',
    'parsedseriesname': 'Scrubs',
    'correctedseriesname': 'Scrubs',
    'seasonnumber': None, 'episodenumbers': [1, 2, 3, 4],
    'episodenames': ['My First Day', 'My Mentor', 'My Best Friend\'s Mistake', 'My Old Lady']},

]


files['no_series_name'] = [
    {'input': 's01e01.avi',
    'force_name': 'Scrubs',
    'parsedseriesname': None,
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},

    {'input': '[01x01].avi',
    'force_name': 'Scrubs',
    'parsedseriesname': None,
    'correctedseriesname': 'Scrubs',
    'seasonnumber': 1, 'episodenumbers': [1],
    'episodenames': ['My First Day']},
]


def test_verify_test_data_sanity():
    """Checks all test data is consistent.

    Keys within each test category must be consistent, but keys can vary
    category to category. E.g date-based episodes do not have a season number
    """
    from helpers import assertEquals

    for test_category, testcases in files.items():
        keys = [ctest.keys() for ctest in testcases]
        for k1 in keys:
            for k2 in keys:
                assertEquals(sorted(k1), sorted(k2))

########NEW FILE########
__FILENAME__ = test_force_series
#!/usr/bin/env python

"""Test ability to set the series name by series id
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_series_id():
    """Test --series-id argument
    """

    conf = """
    {"always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['whatever.s01e01.avi'],
        with_config = conf,
        with_flags = ["--series-id", '76156'],
        with_input = "")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_series_id_with_nameless_series():
    """Test --series-id argument with '6x17.etc.avi' type filename
    """

    conf = """
    {"always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['s01e01.avi'],
        with_config = conf,
        with_flags = ["--series-id", '76156'],
        with_input = "")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_functional
#!/usr/bin/env python

"""Functional tests for tvnamer tests
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr
from helpers import expected_failure_travisci


@attr("functional")
def test_simple_single_file():
    """Test most simple usage
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_input = "1\ny\n")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_simple_multiple_files():
    """Tests simple interactive usage with multiple files
    """

    input_files = [
        'scrubs.s01e01.hdtv.fake.avi',
        'my.name.is.earl.s01e01.fake.avi',
        'a.fake.show.s12e24.fake.avi',
        'total.access.s01e01.avi']

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'My Name Is Earl - [01x01] - Pilot.avi',
        'a fake show - [12x24].avi',
         'Total Access 24_7 - [01x01] - Episode #1.avi']

    out_data = run_tvnamer(
        with_files = input_files,
        with_input = "y\n1\ny\n1\ny\n1\ny\ny\n")

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_simple_batch_functionality():
    """Tests renaming single files at a time, in batch mode
    """

    tests = [
        {'in':'scrubs.s01e01.hdtv.fake.avi',
        'expected':'Scrubs - [01x01] - My First Day.avi'},
        {'in':'my.name.is.earl.s01e01.fake.avi',
        'expected':'My Name Is Earl - [01x01] - Pilot.avi'},
        {'in':'a.fake.show.s12e24.fake.avi',
        'expected':'a.fake.show.s12e24.fake.avi'},
        {'in': 'total.access.s01e01.avi',
        'expected': 'Total Access 24_7 - [01x01] - Episode #1.avi'},
    ]

    for curtest in tests:

        def _the_test():
            out_data = run_tvnamer(
                with_files = [curtest['in'], ],
                with_flags = ['--batch'],
            )
            verify_out_data(out_data, [curtest['expected'], ])

        _the_test.description = "test_simple_functionality_%s" % curtest['in']
        yield _the_test


@attr("functional")
def test_interactive_always_option():
    """Tests the "a" always rename option in interactive UI
    """

    input_files = [
        'scrubs.s01e01.hdtv.fake.avi',
        'my.name.is.earl.s01e01.fake.avi',
        'a.fake.show.s12e24.fake.avi',
        'total.access.s01e01.avi']

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'My Name Is Earl - [01x01] - Pilot.avi',
        'a fake show - [12x24].avi',
         'Total Access 24_7 - [01x01] - Episode #1.avi']

    out_data = run_tvnamer(
        with_files = input_files,
        with_flags = ["--selectfirst"],
        with_input = "a\n")

    verify_out_data(out_data, expected_files)


@attr("functional")
@expected_failure_travisci
def test_unicode_in_inputname():
    """Tests parsing a file with unicode in the input filename
    """
    input_files = [
        u'The Big Bang Theory - S02E07 - The Panty Pin\u0303ata Polarization.avi']

    expected_files = [
        u'The Big Bang Theory - [02x07] - The Panty Pin\u0303ata Polarization.avi']

    out_data = run_tvnamer(
        with_files = input_files,
        with_flags = ["--batch"])

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_unicode_in_search_results():
    """Show with unicode in search results
    """
    input_files = [
        'psych.s04e11.avi']

    expected_files = [
        'Psych - [04x11] - Thrill Seekers & Hell Raisers.avi']

    out_data = run_tvnamer(
        with_files = input_files,
        with_input = '1\ny\n')

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_renaming_always_doesnt_overwrite():
    """If trying to rename a file that exists, should not create new file
    """
    input_files = [
        'Scrubs.s01e01.avi',
        'Scrubs - [01x01] - My First Day.avi']

    expected_files = [
        'Scrubs.s01e01.avi',
        'Scrubs - [01x01] - My First Day.avi']

    out_data = run_tvnamer(
        with_files = input_files,
        with_flags = ['--batch'])

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_not_overwritting_unicode_filename():
    """Test no error occurs when warning about a unicode filename being overwritten
    """
    return
    input_files = [
        u'The Big Bang Theory - S02E07.avi',
        u'The Big Bang Theory - [02x07] - The Panty Pin\u0303ata Polarization.avi']

    expected_files = [
        u'The Big Bang Theory - S02E07.avi',
        u'The Big Bang Theory - [02x07] - The Panty Pin\u0303ata Polarization.avi']

    out_data = run_tvnamer(
        with_files = input_files,
        with_flags = ['--batch'])

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_not_recursive():
    """Tests the nested files aren't found when not recursive
    """
    input_files = [
        'Scrubs.s01e01.avi',
        'nested/subdir/Scrubs.s01e02.avi']

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'nested/subdir/Scrubs.s01e02.avi']

    out_data = run_tvnamer(
        with_files = input_files,
        with_flags = ['--not-recursive', '--batch'],
        run_on_directory = True)

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_correct_filename():
    """If the filename is already correct, don't prompt
    """

    out_data = run_tvnamer(
        with_files = ['Scrubs - [01x01] - My First Day.avi'],
        with_input = "1\ny\n")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_filename_already_exists():
    """If the filename is already correct, don't prompt
    """

    out_data = run_tvnamer(
        with_files = ['Scrubs - [01x01] - My First Day.avi', 'scrubs.s01e01.avi'],
        with_input = "1\ny\n")

    expected_files = ['Scrubs - [01x01] - My First Day.avi', 'scrubs.s01e01.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_no_seasonnumber():
    """Test episode with no series number
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.e01.avi'],
        with_flags = ['--batch'])

    expected_files = ['Scrubs - [01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_skipping_after_replacements():
    """When custom-replacement is specified, should still skip file if name is correct
    """

    conf = """
    {"select_first": true,
    "input_filename_replacements": [
        {"is_regex": false,
        "match": "v",
        "replacement": "u"}
    ],
    "output_filename_replacements": [
        {"is_regex": false,
        "match": "u",
        "replacement": "v"}
    ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['Scrvbs - [01x01] - My First Day.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['Scrvbs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_invalid_files
#!/usr/bin/env python

"""Ensure that invalid files (non-episodes) are not renamed
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_simple_single_file():
    """Boring example
    """

    out_data = run_tvnamer(
        with_files = ['Some File.avi'],
        with_flags = ["--batch"])

    expected_files = ['Some File.avi']

    verify_out_data(out_data, expected_files, expected_returncode = 2)


@attr("functional")
def test_no_series_name():
    """File without series name should be skipped (unless '--name=MySeries' arg is supplied)
    """

    out_data = run_tvnamer(
        with_files = ['s01e01 Some File.avi'],
        with_flags = ["--batch"])

    expected_files = ['s01e01 Some File.avi']

    verify_out_data(out_data, expected_files, expected_returncode = 2)

########NEW FILE########
__FILENAME__ = test_limit_by_extension
#!/usr/bin/env python

"""Tests the valid_extensions config option
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_no_extensions():
    """Tests empty list of extensions is parsed as expected
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "valid_extensions": []}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s01e02.mkv'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'Scrubs - [01x02] - My Mentor.mkv']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_single_extensions():
    """Tests one valid extension with multiple files
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "valid_extensions": ["mkv"]}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s01e02.mkv'],
        with_config = conf)

    expected_files = [
        'scrubs.s01e01.avi',
        'Scrubs - [01x02] - My Mentor.mkv']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_single_extension_with_subdirs():
    """Tests one valid extension recursing into sub-dirs
    """

    conf = """
    {"always_rename": true,
    "select_first": true,
    "valid_extensions": ["avi"],
    "recursive": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'testdir/scrubs.s01e02.mkv', 'testdir/scrubs.s01e04.avi'],
        with_config = conf,
        run_on_directory = True)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'testdir/scrubs.s01e02.mkv',
        'testdir/Scrubs - [01x04] - My Old Lady.avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_movingfiles
#!/usr/bin/env python

"""Tests moving renamed files
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_simple_realtive_move():
    """Move file to simple relative static dir
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "test/",
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['test/Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_dynamic_destination():
    """Move file to simple relative static dir
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "tv/%(seriesname)s/season %(seasonnumber)d/",
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf)

    expected_files = ['tv/Scrubs/season 1/Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_cli_destination():
    """Tests specifying the destination via command line argument
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_flags = ['--batch', '--move', '--movedestination=season %(seasonnumber)d/'])

    expected_files = ['season 1/Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_interactive_allyes():
    """Tests interactive UI for moving all files
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "test",
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s01e02.avi'],
        with_config = conf,
        with_input = "y\ny\ny\ny\n")

    expected_files = ['test/Scrubs - [01x01] - My First Day.avi',
        'test/Scrubs - [01x02] - My Mentor.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_interactive_allno():
    """Tests interactive UI allows not moving any files
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "test",
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s01e02.avi'],
        with_config = conf,
        with_input = "y\nn\ny\nn\n")

    expected_files = ['Scrubs - [01x01] - My First Day.avi',
        'Scrubs - [01x02] - My Mentor.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_interactive_somefiles():
    """Tests interactive UI allows not renaming some files, renaming/moving others

    Rename and move first file, don't rename second file (so no move), and
    rename but do not move last file (Input is: y/y, n, y/n)
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "test",
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s01e02.avi', 'scrubs.s01e03.avi'],
        with_config = conf,
        with_input = "y\ny\nn\ny\nn\n")

    expected_files = ['test/Scrubs - [01x01] - My First Day.avi',
        'scrubs.s01e02.avi',
        'Scrubs - [01x03] - My Best Friend\'s Mistake.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_with_invalid_seriesname():
    """Tests series name containing invalid filename characters
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "%(seriesname)s",
    "batch": true,
    "windows_safe_filenames": true}
    """

    out_data = run_tvnamer(
        with_files = ['csi.miami.s01e01.avi'],
        with_config = conf)

    expected_files = ['CSI_ Miami/CSI_ Miami - [01x01] - Golden Parachute.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_with_invalid_seriesname_test2():
    """Another test for series name containing invalid filename characters
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "%(seriesname)s",
    "batch": true,
    "move_files_fullpath_replacements": [
         {"is_regex": true,
          "match": "CSI_ Miami",
          "replacement": "CSI"}],
    "windows_safe_filenames": true}
    """

    out_data = run_tvnamer(
        with_files = ['csi.miami.s01e01.avi'],
        with_config = conf)

    expected_files = ['CSI/CSI - [01x01] - Golden Parachute.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_files_lowercase_destination():
    """Test move_files_lowercase_destination configuration option.
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "Test/This/%(seriesname)s/S%(seasonnumber)02d",
    "move_files_lowercase_destination": true,
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.This.Is.a.Test.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['Test/This/scrubs/S01/Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_date_based_episode():
    """Moving a date-base episode (lighthouse ticket #56)
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination_date": "Test/%(seriesname)s/%(year)s/%(month)s/%(day)s",
    "move_files_lowercase_destination": true,
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['The Colbert Report - 2011-09-28 Ken Burns.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['Test/The Colbert Report/2011/9/28/The Colbert Report - [2011-09-28] - Ken Burns.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_files_full_filepath_simple():
    """Moving file destination including a fixed filename
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "TestDir/%(seriesname)s/season %(seasonnumber)02d/%(episodenumbers)s/SpecificName.avi",
    "move_files_destination_is_filepath": true,
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e02.avi'],
        with_config = conf,
        with_input = "")

    expected_files = ['TestDir/Scrubs/season 01/02/SpecificName.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_files_full_filepath_with_origfilename():
    """Moving file destination including a filename
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "TestDir/%(seriesname)s/season %(seasonnumber)02d/%(episodenumbers)s/%(originalfilename)s",
    "move_files_destination_is_filepath": true,
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs.s01e02.avi'],
        with_config = conf,
        with_input = "")

    expected_files = [
        'TestDir/Scrubs/season 01/01/scrubs.s01e01.avi',
        'TestDir/Scrubs/season 01/02/scrubs.s01e02.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_with_correct_name():
    """Files with correct name should still be moved
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "SubDir",
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['Scrubs - [01x02] - My Mentor.avi'],
        with_config = conf,
        with_input = "y\n")

    expected_files = ['SubDir/Scrubs - [01x02] - My Mentor.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_no_season():
    """Files with no season number should moveable [#94]
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "SubDir",
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['Scrubs - [02] - My Mentor.avi'],
        with_config = conf,
        with_input = "y\n")

    expected_files = ['SubDir/Scrubs - [02] - My Mentor.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_move_files_only():
    """With parameter move_files_only set to true files should be moved and not renamed
    """

    conf = """
    {"move_files_only": true,
    "move_files_enable": true,
    "move_files_destination": "tv/%(seriesname)s/season %(seasonnumber)d/",
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf)

    expected_files = ['tv/Scrubs/season 1/scrubs.s01e01.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_forcefully_moving_enabled():
    """Forcefully moving files, overwriting destination
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "tv/%(seriesname)s/season %(seasonnumber)d/",
    "batch": true,
    "overwrite_destination_on_move": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'Scrubs - [01x01] - My First Day.avi'],
        with_config = conf)

    expected_files = ['tv/Scrubs/season 1/Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_forcefully_moving_disabled():
    """Explicitly disable forcefully moving files
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "tv/%(seriesname)s/season %(seasonnumber)d/",
    "batch": true,
    "overwrite_destination_on_move": false}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs - [01x01].avi'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'tv/Scrubs/season 1/Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_forcefully_moving_default():
    """Ensure default is not overwrite destination
    """

    conf = """
    {"move_files_enable": true,
    "move_files_destination": "tv/%(seriesname)s/season %(seasonnumber)d/",
    "batch": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi', 'scrubs - [01x01].avi'],
        with_config = conf)

    expected_files = [
        'Scrubs - [01x01] - My First Day.avi',
        'tv/Scrubs/season 1/Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_multiepisode_filenames
#!/usr/bin/env python

"""Tests multi-episode filename generation
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_multiep_different_names():
    """Default config - two different names are joined with 'multiep_join_name_with', 'multiep_format' doesn't matter
    """

    conf = """
    {
    "output_filename_replacements": [
        {"is_regex": false,
        "match": ":",
        "replacement": " -"}
    ],

    "multiep_join_name_with": ", ",
    "batch": true,
    "multiep_format": "%(foo)s"}
    """

    out_data = run_tvnamer(
        with_files = ["star.trek.enterprise.s01e03e04.avi"],
        with_config = conf,
        with_input = "")

    expected_files = ['Star Trek - Enterprise - [01x03-04] - Fight or Flight, Strange New World.avi']

    verify_out_data(out_data, expected_files)

@attr("functional")
def test_multiep_same_names():
    """Default config - same names, format according to 'multiep_format', 'multiep_join_name_with' doesn't matter
    """

    conf = """
    {
    "output_filename_replacements": [
        {"is_regex": false,
        "match": ":",
        "replacement": " -"}
    ],
    "multiep_join_name_with": ", ",
    "batch": true,
    "multiep_format": "%(epname)s (%(episodemin)s-%(episodemax)s)"}
    """

    out_data = run_tvnamer(
        with_files = ["star.trek.enterprise.s01e01e02.avi"],
        with_config = conf,
        with_input = "")

    expected_files = ['Star Trek - Enterprise - [01x01-02] - Broken Bow (1-2).avi']

    verify_out_data(out_data, expected_files)

@attr("functional")
def test_multiep_same_names_without_number():
    """Default config - same names, ensure that missing number doesn't matter
    """

    conf = """
    {
    "output_filename_replacements": [
        {"is_regex": false,
        "match": ":",
        "replacement": " -"}
    ],

    "multiep_join_name_with": ", ",
    "batch": true,
    "multiep_format": "%(epname)s (Parts %(episodemin)s-%(episodemax)s)"}
    """

    out_data = run_tvnamer(
        with_files = ["star.trek.deep.space.nine.s01e01e02.avi"],
        with_config = conf,
        with_input = "")

    expected_files = ['Star Trek - Deep Space Nine - [01x01-02] - Emissary (Parts 1-2).avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_name_generation
#!/usr/bin/env python

"""Test tvnamer's EpisodeInfo file name generation
"""

import datetime

from helpers import assertEquals

from tvnamer.utils import (EpisodeInfo, DatedEpisodeInfo, NoSeasonEpisodeInfo)
from test_files import files

from tvdb_api import Tvdb


def verify_name_gen(curtest, tvdb_instance):
    if "seasonnumber" in curtest:
        ep = EpisodeInfo(
            seriesname = curtest['parsedseriesname'],
            seasonnumber = curtest['seasonnumber'],
            episodenumbers = curtest['episodenumbers'])
    elif any([isinstance(x, datetime.date) for x in curtest['episodenumbers']]):
        ep = DatedEpisodeInfo(
            seriesname = curtest['parsedseriesname'],
            episodenumbers = curtest['episodenumbers'])
    else:
        ep = NoSeasonEpisodeInfo(
            seriesname = curtest['parsedseriesname'],
            episodenumbers = curtest['episodenumbers'])

    ep.populateFromTvdb(tvdb_instance, force_name = curtest.get("force_name"))

    assert ep.seriesname is not None, "Corrected series name was none"
    assert ep.episodename is not None, "Episode name was None"

    assertEquals(ep.seriesname, curtest['correctedseriesname'])
    assertEquals(ep.episodename, curtest['episodenames'])


def test_name_generation_on_testfiles():
    # Test data stores episode names in English, language= is normally set
    # via the configuration, same with search_all_languages.
    tvdb_instance = Tvdb(search_all_languages=True, language='en')
    for category, testcases in files.items():
        for testindex, curtest in enumerate(testcases):
            cur_tester = lambda x: verify_name_gen(x, tvdb_instance)
            cur_tester.description = 'test_name_generation_%s_%d: %r' % (
                category, testindex, curtest['input'])
            yield (cur_tester, curtest)


def test_single_episode():
    """Simple episode name, with show/season/episode/name/filename
    """

    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = 'My Mentor',
        filename = 'scrubs.example.file.avi')

    assertEquals(
        ep.generateFilename(),
        'Scrubs - [01x02] - My Mentor.avi')


def test_multi_episodes_continuous():
    """A two-part episode should not have the episode name repeated
    """
    ep = EpisodeInfo(
        seriesname = 'Stargate SG-1',
        seasonnumber = 1,
        episodenumbers = [1, 2],
        episodename = [
            'Children of the Gods (1)',
            'Children of the Gods (2)'],
        filename = 'stargate.example.file.avi')

    assertEquals(
        ep.generateFilename(),
        'Stargate SG-1 - [01x01-02] - Children of the Gods (1-2).avi')


def test_episode_numeric_title():
    """An episode with a name starting with a number should not be
    detected as a range
    """
    
    ep = EpisodeInfo(
        seriesname = 'Star Trek TNG',
        seasonnumber = 1,
        episodenumbers = [15],
        episodename = [
            '11001001'
        ],
        filename = 'STTNG-S01E15-11001001.avi')

    assertEquals(
        ep.generateFilename(),
        'Star Trek TNG - [01x15] - 11001001.avi')


def test_multi_episodes_seperate():
    """File with two episodes, but with different names
    """
    ep = EpisodeInfo(
        seriesname = 'Stargate SG-1',
        seasonnumber = 1,
        episodenumbers = [2, 3],
        episodename = [
            'Children of the Gods (2)',
            'The Enemy Within'],
        filename = 'stargate.example.file.avi')

    assertEquals(
        ep.generateFilename(),
        'Stargate SG-1 - [01x02-03] - Children of the Gods (2), The Enemy Within.avi')


def test_simple_no_ext():
    """Simple episode with out extension
    """
    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = 'My Mentor',
        filename = None)

    assertEquals(
        ep.generateFilename(),
        'Scrubs - [01x02] - My Mentor')


def test_no_name():
    """Episode without a name
    """
    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = None,
        filename = 'scrubs.example.file.avi')

    assertEquals(
        ep.generateFilename(),
        'Scrubs - [01x02].avi')


def test_episode_no_name_no_ext():
    """EpisodeInfo with no name or extension
    """
    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = None,
        filename = None)

    assertEquals(
        ep.generateFilename(),
        'Scrubs - [01x02]')


def test_noseason_no_name_no_ext():
    """NoSeasonEpisodeInfo with no name or extension
    """
    ep = NoSeasonEpisodeInfo(
        seriesname = 'Scrubs',
        episodenumbers = [2],
        episodename = None,
        filename = None)

    assertEquals(
        ep.generateFilename(),
        'Scrubs - [02]')


def test_datedepisode_no_name_no_ext():
    """DatedEpisodeInfo with no name or extension
    """
    ep = DatedEpisodeInfo(
        seriesname = 'Scrubs',
        episodenumbers = [datetime.date(2010, 11, 23)],
        episodename = None,
        filename = None)

    assertEquals(
        ep.generateFilename(),
        'Scrubs - [2010-11-23]')


def test_no_series_number():
    """Episode without season number
    """
    ep = NoSeasonEpisodeInfo(
        seriesname = 'Scrubs',
        episodenumbers = [2],
        episodename = 'My Mentor',
        filename = None)

    assertEquals(
        ep.generateFilename(),
        'Scrubs - [02] - My Mentor')


def test_downcase():
    """Simple episode name, converted to lowercase
    """

    ep = EpisodeInfo(
        seriesname = 'Scrubs',
        seasonnumber = 1,
        episodenumbers = [2],
        episodename = 'My Mentor',
        filename = 'scrubs.example.file.avi')

    assertEquals(
        ep.generateFilename(lowercase = True),
        'scrubs - [01x02] - my mentor.avi')

########NEW FILE########
__FILENAME__ = test_no_series_in_filename
#!/usr/bin/env python

"""Ensure that invalid files (non-episodes) are not renamed
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_simple_single_file():
    """Files without series name should be skipped, unless --name=MySeries is specified
    """

    out_data = run_tvnamer(
        with_files = ['S01E02 - Some File.avi'],
        with_flags = ["--batch"])

    expected_files = ['S01E02 - Some File.avi']

    verify_out_data(out_data, expected_files, expected_returncode = 2)


@attr("functional")
def test_simple_single_file_with_forced_seriesnames():
    """Specifying 's01e01.avi' should parse when --name=SeriesName arg is specified
    """

    out_data = run_tvnamer(
        with_files = ['S01E02 - Some File.avi'],
        with_flags = ["--batch", '--name', 'Scrubs'])

    expected_files = ['Scrubs - [01x02] - My Mentor.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_name_arg_skips_replacements():
    """Should not apply input_filename_replacements to --name=SeriesName arg value
    """

    conf = r"""
    {"always_rename": true,
    "select_first": true,

    "force_name": "Scrubs",

    "input_filename_replacements": [
        {"is_regex": true,
        "match": "Scrubs",
        "replacement": "Blahblahblah"}
    ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['S01E02 - Some File.avi'],
        with_config = conf)

    expected_files = ['Scrubs - [01x02] - My Mentor.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replacements_applied_before_force_name():
    """input_filename_replacements apply to filename, before --name=SeriesName takes effect
    """

    conf = r"""
    {"always_rename": true,
    "select_first": true,

    "force_name": "Scrubs",

    "input_filename_replacements": [
        {"is_regex": true,
        "match": "S01E02 - ",
        "replacement": ""}
    ]
    }
    """

    out_data = run_tvnamer(
        with_files = ['S01E02 - Some File.avi'],
        with_config = conf)

    expected_files = ['S01E02 - Some File.avi']

    verify_out_data(out_data, expected_files, expected_returncode = 2)

########NEW FILE########
__FILENAME__ = test_override_seriesname
#!/usr/bin/env python

"""Test ability to override the series name
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_temp_override():
    """Test --name argument
    """

    conf = """
    {"always_rename": true,
    "select_first": true}
    """

    out_data = run_tvnamer(
        with_files = ['scrubs.s01e01.avi'],
        with_config = conf,
        with_flags = ["--name", "lost"],
        with_input = "")

    expected_files = ['Lost - [01x01] - Pilot (1).avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_parsing
#!/usr/bin/env python

"""Test tvnamer's filename parser
"""

from helpers import assertEquals

from tvnamer.utils import (FileParser, DatedEpisodeInfo, NoSeasonEpisodeInfo)

from test_files import files


def test_autogen_names():
    """Tests set of standard filename formats with various data
    """

    """Mostly based on scene naming standards:
    http://tvunderground.org.ru/forum/index.php?showtopic=8488

    %(seriesname)s becomes the seriesname,
    %(seasno)s becomes the season number,
    %(epno)s becomes the episode number.

    Each is string-formatted with seasons from 0 to 10, and ep 0 to 10
    """

    name_formats = [
        '%(seriesname)s.s%(seasno)de%(epno)d.dsr.nf.avi',                 # seriesname.s01e02.dsr.nf.avi
        '%(seriesname)s.S%(seasno)dE%(epno)d.PROPER.dsr.nf.avi',          # seriesname.S01E02.PROPER.dsr.nf.avi
        '%(seriesname)s.s%(seasno)d.e%(epno)d.avi',                       # seriesname.s01.e02.avi
        '%(seriesname)s-s%(seasno)de%(epno)d.avi',                        # seriesname-s01e02.avi
        '%(seriesname)s-s%(seasno)de%(epno)d.the.wrong.ep.name.avi',      # seriesname-s01e02.the.wrong.ep.name.avi
        '%(seriesname)s - [%(seasno)dx%(epno)d].avi',                     # seriesname - [01x02].avi
        '%(seriesname)s - [%(seasno)dx0%(epno)d].avi',                    # seriesname - [01x002].avi
        '%(seriesname)s-[%(seasno)dx%(epno)d].avi',                       # seriesname-[01x02].avi
        '%(seriesname)s [%(seasno)dx%(epno)d].avi',                       # seriesname [01x02].avi
        '%(seriesname)s [%(seasno)dx%(epno)d] the wrong ep name.avi',     # seriesname [01x02] epname.avi
        '%(seriesname)s [%(seasno)dx%(epno)d] - the wrong ep name.avi',   # seriesname [01x02] - the wrong ep name.avi
        '%(seriesname)s - [%(seasno)dx%(epno)d] - the wrong ep name.avi', # seriesname - [01x02] - the wrong ep name.avi
        '%(seriesname)s.%(seasno)dx%(epno)d.The_Wrong_ep_name.avi',       # seriesname.01x02.epname.avi
        '%(seriesname)s.%(seasno)d%(epno)02d.The Wrong_ep.names.avi',     # seriesname.102.epname.avi
        '%(seriesname)s_s%(seasno)de%(epno)d_The_Wrong_ep_na-me.avi',     # seriesname_s1e02_epname.avi
        '%(seriesname)s - s%(seasno)de%(epno)d - dsr.nf.avi',             # seriesname - s01e02 - dsr.nf.avi
        '%(seriesname)s - s%(seasno)de%(epno)d - the wrong ep name.avi',  # seriesname - s01e02 - the wrong ep name.avi
        '%(seriesname)s - s%(seasno)de%(epno)d - the wrong ep name.avi',  # seriesname - s01e02 - the_wrong_ep_name!.avi
    ]

    test_data = [
    {'name': 'test_name_parser_unicode',
    'description': 'Tests parsing show containing unicode characters',
    'name_data': {'seriesname': 'T\xc3\xacnh Ng\xc6\xb0\xe1\xbb\x9di Hi\xe1\xbb\x87n \xc4\x90\xe1\xba\xa1i'}},

    {'name': 'test_name_parser_basic',
    'description': 'Tests most basic filename (simple seriesname)',
    'name_data': {'seriesname': 'series name'}},

    {'name': 'test_name_parser_showdashname',
    'description': 'Tests with dash in seriesname',
    'name_data': {'seriesname': 'S-how name'}},

    {'name': 'test_name_parser_exclaim',
    'description': 'Tests parsing show with exclamation mark',
    'name_data': {'seriesname': 'Show name!'}},

    {'name': 'test_name_parser_shownumeric',
    'description': 'Tests with numeric show name',
    'name_data': {'seriesname': '123'}},

    {'name': 'test_name_parser_shownumericspaces',
    'description': 'Tests with numeric show name, with spaces',
    'name_data': {'seriesname': '123 2008'}},
    ]

    for cdata in test_data:
        # Make new wrapped function
        def cur_test():
            for seas in xrange(1, 11):
                for ep in xrange(1, 11):

                    name_data = cdata['name_data']

                    name_data['seasno'] = seas
                    name_data['epno'] = ep

                    names = [x % name_data for x in name_formats]

                    for cur in names:
                        p = FileParser(cur).parse()

                        assertEquals(p.episodenumbers, [name_data['epno']])
                        assertEquals(p.seriesname, name_data['seriesname'])
                        # Only EpisodeInfo has seasonnumber
                        if not isinstance(p, (DatedEpisodeInfo, NoSeasonEpisodeInfo)):
                            assertEquals(p.seasonnumber, name_data['seasno'])
        #end cur_test

        cur_test.description = cdata['description']
        yield cur_test


def check_case(curtest):
    """Runs test case, used by test_parsing_generator
    """
    parser = FileParser(curtest['input'])
    theep = parser.parse()

    if theep.seriesname is None and curtest['parsedseriesname'] is None:
        pass # allow for None seriesname
    else:
        assert theep.seriesname.lower() == curtest['parsedseriesname'].lower(), "%s == %s" % (
            theep.seriesname.lower(),
            curtest['parsedseriesname'].lower())

    assertEquals(theep.episodenumbers, curtest['episodenumbers'])
    if not isinstance(theep, (DatedEpisodeInfo, NoSeasonEpisodeInfo)):
        assertEquals(theep.seasonnumber, curtest['seasonnumber'])


def test_parsing_generator():
    """Generates test for each test case in test_files.py
    """
    for category, testcases in files.items():
        for testindex, curtest in enumerate(testcases):
            cur_tester = lambda x: check_case(x)
            cur_tester.description = 'test_parsing_%s_%d: %r' % (
                category, testindex, curtest['input'])
            yield (cur_tester, curtest)


if __name__ == '__main__':
    import nose
    nose.main()

########NEW FILE########
__FILENAME__ = test_safefilename
#!/usr/bin/env python

"""Test the function to create safe filenames
"""

import platform

from helpers import assertEquals

from tvnamer.utils import makeValidFilename


def test_basic():
    """Test makeValidFilename does not mess up simple filenames
    """
    assertEquals(makeValidFilename("test.avi"), "test.avi")
    assertEquals(makeValidFilename("Test File.avi"), "Test File.avi")
    assertEquals(makeValidFilename("Test"), "Test")


def test_dirseperators():
    """Tests makeValidFilename removes directory separators
    """
    assertEquals(makeValidFilename("Test/File.avi"), "Test_File.avi")
    assertEquals(makeValidFilename("Test/File"), "Test_File")


def test_windowsfilenames():
    """Tests makeValidFilename windows_safe flag makes Windows-safe filenames
    """
    assertEquals(makeValidFilename("Test/File.avi", windows_safe = True), "Test_File.avi")
    assertEquals(makeValidFilename("\\/:*?<Evil>|\"", windows_safe = True), "______Evil___")
    assertEquals(makeValidFilename("COM2.txt", windows_safe = True), "_COM2.txt")
    assertEquals(makeValidFilename("COM2", windows_safe = True), "_COM2")


def test_dotfilenames():
    """Tests makeValidFilename on filenames only consisting of .
    """
    assertEquals(makeValidFilename("."), "_.")
    assertEquals(makeValidFilename(".."), "_..")
    assertEquals(makeValidFilename("..."), "_...")
    assertEquals(makeValidFilename(".test.rc"), "_.test.rc")


def test_customblacklist():
    """Test makeValidFilename custom_blacklist feature
    """
    assertEquals(makeValidFilename("Test.avi", custom_blacklist="e"), "T_st.avi")


def test_replacewith():
    """Tests replacing blacklisted character with custom characters
    """
    assertEquals(makeValidFilename("My Test File.avi", custom_blacklist=" ", replace_with="."), "My.Test.File.avi")


def _test_truncation(max_len, windows_safe):
    """Tests truncation works correctly.
    Called with different parameters for both Windows and Darwin/Linux.
    """
    assertEquals(makeValidFilename("a" * 300, windows_safe = windows_safe), "a" * max_len)
    assertEquals(makeValidFilename("a" * 255 + ".avi", windows_safe = windows_safe), "a" * (max_len-4) + ".avi")
    assertEquals(makeValidFilename("a" * 251 + "b" * 10 + ".avi", windows_safe = windows_safe), "a" * (max_len-4) + ".avi")
    assertEquals(makeValidFilename("test." + "a" * 255, windows_safe = windows_safe), "test." + "a" * (max_len-5))


def test_truncation_darwinlinux():
    """Tests makeValidFilename truncates filenames to valid length
    """

    if platform.system() not in ['Darwin', 'Linux']:
        import nose
        raise nose.SkipTest("Test only valid on Darwin and Linux platform")

    _test_truncation(254, windows_safe = False)


def test_truncation_windows():
    """Tests truncate works on Windows (using windows_safe=True)
    """
    _test_truncation(max_len = 254, windows_safe = True)

########NEW FILE########
__FILENAME__ = test_series_replacement
#!/usr/bin/env python

"""Tests custom replacements on input/output files
"""

from functional_runner import run_tvnamer, verify_out_data
from nose.plugins.attrib import attr


@attr("functional")
def test_replace_input():
    """Tests replacing strings in input files
    """
    out_data = run_tvnamer(
        with_files = ['scruuuuuubs.s01e01.avi'],
        with_config = """
{
    "input_series_replacements": {
        "scru*bs": "scrubs"},
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replace_input_with_id():
    """Map from a series name to a numberic TVDB ID
    """

    out_data = run_tvnamer(
        with_files = ['seriesnamegoeshere.s01e01.avi'],
        with_config = """
{
    "input_series_replacements": {
        "seriesnamegoeshere": 76156},
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Scrubs - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)


@attr("functional")
def test_replace_output():
    """Tests replacing strings in input files
    """
    out_data = run_tvnamer(
        with_files = ['Scrubs.s01e01.avi'],
        with_config = """
{
    "output_series_replacements": {
        "Scrubs": "Replacement Series Name"},
    "always_rename": true,
    "select_first": true
}
""")

    expected_files = ['Replacement Series Name - [01x01] - My First Day.avi']

    verify_out_data(out_data, expected_files)

########NEW FILE########
__FILENAME__ = test_system
#!/usr/bin/env python

"""Tests the current system for things that might cause problems
"""

import os


def test_nosavedconfig():
    """A config at ~/.tvnamer.json could cause problems with some tests
    """
    assert not os.path.isfile(os.path.expanduser("~/.tvnamer.json")), "~/.tvnamer.json exists, which could cause problems with some tests"

########NEW FILE########
__FILENAME__ = pep8
#!/usr/bin/python
# pep8.py - Check Python source code formatting, according to PEP 8
# Copyright (C) 2006 Johann C. Rocholl <johann@browsershots.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Check Python source code formatting, according to PEP 8:
http://www.python.org/dev/peps/pep-0008/

For usage and a list of options, try this:
$ python pep8.py -h

This program and its regression test suite live here:
http://svn.browsershots.org/trunk/devtools/pep8/
http://trac.browsershots.org/browser/trunk/devtools/pep8/

Groups of errors and warnings:
E errors
W warnings
100 indentation
200 whitespace
300 blank lines
400 imports
500 line length
600 deprecation
700 statements

You can add checks to this program by writing plugins. Each plugin is
a simple function that is called for each line of source code, either
physical or logical.

Physical line:
- Raw line of text from the input file.

Logical line:
- Multi-line statements converted to a single line.
- Stripped left and right.
- Contents of strings replaced with 'xxx' of same length.
- Comments removed.

The check function requests physical or logical lines by the name of
the first argument:

def maximum_line_length(physical_line)
def extraneous_whitespace(logical_line)
def blank_lines(logical_line, blank_lines, indent_level, line_number)

The last example above demonstrates how check plugins can request
additional information with extra arguments. All attributes of the
Checker object are available. Some examples:

lines: a list of the raw lines from the input file
tokens: the tokens that contribute to this logical line
line_number: line number in the input file
blank_lines: blank lines before this one
indent_char: first indentation character in this file (' ' or '\t')
indent_level: indentation (with tabs expanded to multiples of 8)
previous_indent_level: indentation on previous line
previous_logical: previous logical line

The docstring of each check function shall be the relevant part of
text from PEP 8. It is printed if the user enables --show-pep8.

"""

import os
import sys
import re
import time
import inspect
import tokenize
from optparse import OptionParser
from keyword import iskeyword
from fnmatch import fnmatch

__version__ = '0.2.0'
__revision__ = '$Rev$'

default_exclude = '.svn,CVS,*.pyc,*.pyo'

indent_match = re.compile(r'([ \t]*)').match
raise_comma_match = re.compile(r'raise\s+\w+\s*(,)').match

operators = """
+  -  *  /  %  ^  &  |  =  <  >  >>  <<
+= -= *= /= %= ^= &= |= == <= >= >>= <<=
!= <> :
in is or not and
""".split()

options = None
args = None


##############################################################################
# Plugins (check functions) for physical lines
##############################################################################


def tabs_or_spaces(physical_line, indent_char):
    """
    Never mix tabs and spaces.

    The most popular way of indenting Python is with spaces only.  The
    second-most popular way is with tabs only.  Code indented with a mixture
    of tabs and spaces should be converted to using spaces exclusively.  When
    invoking the Python command line interpreter with the -t option, it issues
    warnings about code that illegally mixes tabs and spaces.  When using -tt
    these warnings become errors.  These options are highly recommended!
    """
    indent = indent_match(physical_line).group(1)
    for offset, char in enumerate(indent):
        if char != indent_char:
            return offset, "E101 indentation contains mixed spaces and tabs"


def tabs_obsolete(physical_line):
    """
    For new projects, spaces-only are strongly recommended over tabs.  Most
    editors have features that make this easy to do.
    """
    indent = indent_match(physical_line).group(1)
    if indent.count('\t'):
        return indent.index('\t'), "W191 indentation contains tabs"


def trailing_whitespace(physical_line):
    """
    JCR: Trailing whitespace is superfluous.
    """
    physical_line = physical_line.rstrip('\n') # chr(10), newline
    physical_line = physical_line.rstrip('\r') # chr(13), carriage return
    physical_line = physical_line.rstrip('\x0c') # chr(12), form feed, ^L
    stripped = physical_line.rstrip()
    if physical_line != stripped:
        return len(stripped), "W291 trailing whitespace"


def trailing_blank_lines(physical_line, lines, line_number):
    """
    JCR: Trailing blank lines are superfluous.
    """
    if physical_line.strip() == '' and line_number == len(lines):
        return 0, "W391 blank line at end of file"


def missing_newline(physical_line):
    """
    JCR: The last line should have a newline.
    """
    if physical_line.rstrip() == physical_line:
        return len(physical_line), "W292 no newline at end of file"


def maximum_line_length(physical_line):
    """
    Limit all lines to a maximum of 79 characters.

    There are still many devices around that are limited to 80 character
    lines; plus, limiting windows to 80 characters makes it possible to have
    several windows side-by-side.  The default wrapping on such devices looks
    ugly.  Therefore, please limit all lines to a maximum of 79 characters.
    For flowing long blocks of text (docstrings or comments), limiting the
    length to 72 characters is recommended.
    """
    length = len(physical_line.rstrip())
    if length > 79:
        return 79, "E501 line too long (%d characters)" % length


##############################################################################
# Plugins (check functions) for logical lines
##############################################################################


def blank_lines(logical_line, blank_lines, indent_level, line_number,
                previous_logical):
    """
    Separate top-level function and class definitions with two blank lines.

    Method definitions inside a class are separated by a single blank line.

    Extra blank lines may be used (sparingly) to separate groups of related
    functions.  Blank lines may be omitted between a bunch of related
    one-liners (e.g. a set of dummy implementations).

    Use blank lines in functions, sparingly, to indicate logical sections.
    """
    if line_number == 1:
        return # Don't expect blank lines before the first line
    if previous_logical.startswith('@'):
        return # Don't expect blank lines after function decorator
    if (logical_line.startswith('def ') or
        logical_line.startswith('class ') or
        logical_line.startswith('@')):
        if indent_level > 0 and blank_lines != 1:
            return 0, "E301 expected 1 blank line, found %d" % blank_lines
        if indent_level == 0 and blank_lines != 2:
            return 0, "E302 expected 2 blank lines, found %d" % blank_lines
    if blank_lines > 2:
        return 0, "E303 too many blank lines (%d)" % blank_lines


def extraneous_whitespace(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately inside parentheses, brackets or braces.

    - Immediately before a comma, semicolon, or colon.
    """
    line = logical_line
    for char in '([{':
        found = line.find(char + ' ')
        if found > -1:
            return found + 1, "E201 whitespace after '%s'" % char
    for char in '}])':
        found = line.find(' ' + char)
        if found > -1 and line[found - 1] != ',':
            return found, "E202 whitespace before '%s'" % char
    for char in ',;:':
        found = line.find(' ' + char)
        if found > -1:
            return found, "E203 whitespace before '%s'" % char


def missing_whitespace(logical_line):
    """
    JCR: Each comma, semicolon or colon should be followed by whitespace.
    """
    line = logical_line
    for index in range(len(line) - 1):
        char = line[index]
        if char in ',;:' and line[index + 1] != ' ':
            before = line[:index]
            if char == ':' and before.count('[') > before.count(']'):
                continue # Slice syntax, no space required
            return index, "E231 missing whitespace after '%s'" % char


def indentation(logical_line, previous_logical, indent_char,
                indent_level, previous_indent_level):
    """
    Use 4 spaces per indentation level.

    For really old code that you don't want to mess up, you can continue to
    use 8-space tabs.
    """
    if indent_char == ' ' and indent_level % 4:
        return 0, "E111 indentation is not a multiple of four"
    indent_expect = previous_logical.endswith(':')
    if indent_expect and indent_level <= previous_indent_level:
        return 0, "E112 expected an indented block"
    if indent_level > previous_indent_level and not indent_expect:
        return 0, "E113 unexpected indentation"


def whitespace_before_parameters(logical_line, tokens):
    """
    Avoid extraneous whitespace in the following situations:

    - Immediately before the open parenthesis that starts the argument
      list of a function call.

    - Immediately before the open parenthesis that starts an indexing or
      slicing.
    """
    prev_type = tokens[0][0]
    prev_text = tokens[0][1]
    prev_end = tokens[0][3]
    for index in range(1, len(tokens)):
        token_type, text, start, end, line = tokens[index]
        if (token_type == tokenize.OP and
            text in '([' and
            start != prev_end and
            prev_type == tokenize.NAME and
            (index < 2 or tokens[index - 2][1] != 'class') and
            (not iskeyword(prev_text))):
            return prev_end, "E211 whitespace before '%s'" % text
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_operator(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.
    """
    line = logical_line
    for operator in operators:
        found = line.find('  ' + operator)
        if found > -1:
            return found, "E221 multiple spaces before operator"
        found = line.find(operator + '  ')
        if found > -1:
            return found, "E222 multiple spaces after operator"
        found = line.find('\t' + operator)
        if found > -1:
            return found, "E223 tab before operator"
        found = line.find(operator + '\t')
        if found > -1:
            return found, "E224 tab after operator"


def whitespace_around_comma(logical_line):
    """
    Avoid extraneous whitespace in the following situations:

    - More than one space around an assignment (or other) operator to
      align it with another.

    JCR: This should also be applied around comma etc.
    """
    line = logical_line
    for separator in ',;:':
        found = line.find(separator + '  ')
        if found > -1:
            return found + 1, "E241 multiple spaces after '%s'" % separator
        found = line.find(separator + '\t')
        if found > -1:
            return found + 1, "E242 tab after '%s'" % separator


def imports_on_separate_lines(logical_line):
    """
    Imports should usually be on separate lines.
    """
    line = logical_line
    if line.startswith('import '):
        found = line.find(',')
        if found > -1:
            return found, "E401 multiple imports on one line"


def compound_statements(logical_line):
    """
    Compound statements (multiple statements on the same line) are
    generally discouraged.
    """
    line = logical_line
    found = line.find(':')
    if -1 < found < len(line) - 1:
        before = line[:found]
        if (before.count('{') <= before.count('}') and # {'a': 1} (dict)
            before.count('[') <= before.count(']') and # [1:2] (slice)
            not re.search(r'\blambda\b', before)):     # lambda x: x
            return found, "E701 multiple statements on one line (colon)"
    found = line.find(';')
    if -1 < found:
        return found, "E702 multiple statements on one line (semicolon)"


def python_3000_has_key(logical_line):
    """
    The {}.has_key() method will be removed in the future version of
    Python. Use the 'in' operation instead, like:
    d = {"a": 1, "b": 2}
    if "b" in d:
        print d["b"]
    """
    pos = logical_line.find('.has_key(')
    if pos > -1:
        return pos, "W601 .has_key() is deprecated, use 'in'"


def python_3000_raise_comma(logical_line):
    """
    When raising an exception, use "raise ValueError('message')"
    instead of the older form "raise ValueError, 'message'".

    The paren-using form is preferred because when the exception arguments
    are long or include string formatting, you don't need to use line
    continuation characters thanks to the containing parentheses.  The older
    form will be removed in Python 3000.
    """
    match = raise_comma_match(logical_line)
    if match:
        return match.start(1), "W602 deprecated form of raising exception"


##############################################################################
# Helper functions
##############################################################################


def expand_indent(line):
    """
    Return the amount of indentation.
    Tabs are expanded to the next multiple of 8.

    >>> expand_indent('    ')
    4
    >>> expand_indent('\\t')
    8
    >>> expand_indent('    \\t')
    8
    >>> expand_indent('       \\t')
    8
    >>> expand_indent('        \\t')
    16
    """
    result = 0
    for char in line:
        if char == '\t':
            result = result / 8 * 8 + 8
        elif char == ' ':
            result += 1
        else:
            break
    return result


##############################################################################
# Framework to run all checks
##############################################################################


def message(text):
    """Print a message."""
    # print >> sys.stderr, options.prog + ': ' + text
    # print >> sys.stderr, text
    print text


def find_checks(argument_name):
    """
    Find all globally visible functions where the first argument name
    starts with argument_name.
    """
    checks = []
    function_type = type(find_checks)
    for name, function in globals().iteritems():
        if type(function) is function_type:
            args = inspect.getargspec(function)[0]
            if len(args) >= 1 and args[0].startswith(argument_name):
                checks.append((name, function, args))
    checks.sort()
    return checks


def mute_string(text):
    """
    Replace contents with 'xxx' to prevent syntax matching.

    >>> mute_string('"abc"')
    '"xxx"'
    >>> mute_string("'''abc'''")
    "'''xxx'''"
    >>> mute_string("r'abc'")
    "r'xxx'"
    """
    start = 1
    end = len(text) - 1
    # String modifiers (e.g. u or r)
    if text.endswith('"'):
        start += text.index('"')
    elif text.endswith("'"):
        start += text.index("'")
    # Triple quotes
    if text.endswith('"""') or text.endswith("'''"):
        start += 2
        end -= 2
    return text[:start] + 'x' * (end - start) + text[end:]


class Checker:
    """
    Load a Python source file, tokenize it, check coding style.
    """

    def __init__(self, filename):
        self.filename = filename
        self.lines = file(filename).readlines()
        self.physical_checks = find_checks('physical_line')
        self.logical_checks = find_checks('logical_line')
        options.counters['physical lines'] = \
            options.counters.get('physical lines', 0) + len(self.lines)

    def readline(self):
        """
        Get the next line from the input buffer.
        """
        self.line_number += 1
        if self.line_number > len(self.lines):
            return ''
        return self.lines[self.line_number - 1]

    def readline_check_physical(self):
        """
        Check and return the next physical line. This method can be
        used to feed tokenize.generate_tokens.
        """
        line = self.readline()
        if line:
            self.check_physical(line)
        return line

    def run_check(self, check, argument_names):
        """
        Run a check plugin.
        """
        arguments = []
        for name in argument_names:
            arguments.append(getattr(self, name))
        return check(*arguments)

    def check_physical(self, line):
        """
        Run all physical checks on a raw input line.
        """
        self.physical_line = line
        if self.indent_char is None and len(line) and line[0] in ' \t':
            self.indent_char = line[0]
        for name, check, argument_names in self.physical_checks:
            result = self.run_check(check, argument_names)
            if result is not None:
                offset, text = result
                self.report_error(self.line_number, offset, text, check)

    def build_tokens_line(self):
        """
        Build a logical line from tokens.
        """
        self.mapping = []
        logical = []
        length = 0
        previous = None
        for token in self.tokens:
            token_type, text = token[0:2]
            if token_type in (tokenize.COMMENT, tokenize.NL,
                              tokenize.INDENT, tokenize.DEDENT,
                              tokenize.NEWLINE):
                continue
            if token_type == tokenize.STRING:
                text = mute_string(text)
            if previous:
                end_line, end = previous[3]
                start_line, start = token[2]
                if end_line != start_line: # different row
                    if self.lines[end_line - 1][end - 1] not in '{[(':
                        logical.append(' ')
                        length += 1
                elif end != start: # different column
                    fill = self.lines[end_line - 1][end:start]
                    logical.append(fill)
                    length += len(fill)
            self.mapping.append((length, token))
            logical.append(text)
            length += len(text)
            previous = token
        self.logical_line = ''.join(logical)
        assert self.logical_line.lstrip() == self.logical_line
        assert self.logical_line.rstrip() == self.logical_line

    def check_logical(self):
        """
        Build a line from tokens and run all logical checks on it.
        """
        options.counters['logical lines'] = \
            options.counters.get('logical lines', 0) + 1
        self.build_tokens_line()
        first_line = self.lines[self.mapping[0][1][2][0] - 1]
        indent = first_line[:self.mapping[0][1][2][1]]
        self.previous_indent_level = self.indent_level
        self.indent_level = expand_indent(indent)
        if options.verbose >= 2:
            print self.logical_line[:80].rstrip()
        for name, check, argument_names in self.logical_checks:
            if options.verbose >= 3:
                print '   ', name
            result = self.run_check(check, argument_names)
            if result is not None:
                offset, text = result
                if type(offset) is tuple:
                    original_number, original_offset = offset
                else:
                    for token_offset, token in self.mapping:
                        if offset >= token_offset:
                            original_number = token[2][0]
                            original_offset = (token[2][1]
                                               + offset - token_offset)
                self.report_error(original_number, original_offset,
                                  text, check)
        self.previous_logical = self.logical_line

    def check_all(self):
        """
        Run all checks on the input file.
        """
        self.file_errors = 0
        self.line_number = 0
        self.indent_char = None
        self.indent_level = 0
        self.previous_logical = ''
        self.blank_lines = 0
        self.tokens = []
        parens = 0
        for token in tokenize.generate_tokens(self.readline_check_physical):
            # print tokenize.tok_name[token[0]], repr(token)
            self.tokens.append(token)
            token_type, text = token[0:2]
            if token_type == tokenize.OP and text in '([{':
                parens += 1
            if token_type == tokenize.OP and text in '}])':
                parens -= 1
            if token_type == tokenize.NEWLINE and not parens:
                self.check_logical()
                self.blank_lines = 0
                self.tokens = []
            if token_type == tokenize.NL and not parens:
                self.blank_lines += 1
                self.tokens = []
            if token_type == tokenize.COMMENT:
                source_line = token[4]
                token_start = token[2][1]
                if source_line[:token_start].strip() == '':
                    self.blank_lines = 0
        return self.file_errors

    def report_error(self, line_number, offset, text, check):
        """
        Report an error, according to options.
        """
        if options.quiet == 1 and not self.file_errors:
            message(self.filename)
        self.file_errors += 1
        code = text[:4]
        options.counters[code] = options.counters.get(code, 0) + 1
        options.messages[code] = text[5:]
        if options.quiet:
            return
        if options.testsuite:
            base = os.path.basename(self.filename)[:4]
            if base == code:
                return
            if base[0] == 'E' and code[0] == 'W':
                return
        if ignore_code(code):
            return
        if options.counters[code] == 1 or options.repeat:
            message("%s:%s:%d: %s" %
                    (self.filename, line_number, offset + 1, text))
            if options.show_source:
                line = self.lines[line_number - 1]
                message(line.rstrip())
                message(' ' * offset + '^')
            if options.show_pep8:
                message(check.__doc__.lstrip('\n').rstrip())


def input_file(filename):
    """
    Run all checks on a Python source file.
    """
    if excluded(filename) or not filename_match(filename):
        return {}
    if options.verbose:
        message('checking ' + filename)
    options.counters['files'] = options.counters.get('files', 0) + 1
    errors = Checker(filename).check_all()
    if options.testsuite and not errors:
        message("%s: %s" % (filename, "no errors found"))


def input_dir(dirname):
    """
    Check all Python source files in this directory and all subdirectories.
    """
    dirname = dirname.rstrip('/')
    if excluded(dirname):
        return
    for root, dirs, files in os.walk(dirname):
        if options.verbose:
            message('directory ' + root)
        options.counters['directories'] = \
            options.counters.get('directories', 0) + 1
        dirs.sort()
        for subdir in dirs:
            if excluded(subdir):
                dirs.remove(subdir)
        files.sort()
        for filename in files:
            input_file(os.path.join(root, filename))


def excluded(filename):
    """
    Check if options.exclude contains a pattern that matches filename.
    """
    basename = os.path.basename(filename)
    for pattern in options.exclude:
        if fnmatch(basename, pattern):
            # print basename, 'excluded because it matches', pattern
            return True


def filename_match(filename):
    """
    Check if options.filename contains a pattern that matches filename.
    If options.filename is unspecified, this always returns True.
    """
    if not options.filename:
        return True
    for pattern in options.filename:
        if fnmatch(filename, pattern):
            return True


def ignore_code(code):
    """
    Check if options.ignore contains a prefix of the error code.
    """
    for ignore in options.ignore:
        if code.startswith(ignore):
            return True


def get_error_statistics():
    """Get error statistics."""
    return get_statistics("E")


def get_warning_statistics():
    """Get warning statistics."""
    return get_statistics("W")


def get_statistics(prefix=''):
    """
    Get statistics for message codes that start with the prefix.

    prefix='' matches all errors and warnings
    prefix='E' matches all errors
    prefix='W' matches all warnings
    prefix='E4' matches all errors that have to do with imports
    """
    stats = []
    keys = options.messages.keys()
    keys.sort()
    for key in keys:
        if key.startswith(prefix):
            stats.append('%-7s %s %s' %
                         (options.counters[key], key, options.messages[key]))
    return stats


def print_statistics(prefix=''):
    """Print overall statistics (number of errors and warnings)."""
    for line in get_statistics(prefix):
        print line


def print_benchmark(elapsed):
    """
    Print benchmark numbers.
    """
    print '%-7.2f %s' % (elapsed, 'seconds elapsed')
    keys = ['directories', 'files',
            'logical lines', 'physical lines']
    for key in keys:
        if key in options.counters:
            print '%-7d %s per second (%d total)' % (
                options.counters[key] / elapsed, key,
                options.counters[key])


def process_options(arglist=None):
    """
    Process options passed either via arglist or via command line args.
    """
    global options, args
    usage = "%prog [options] input ..."
    parser = OptionParser(usage)
    parser.add_option('-v', '--verbose', default=0, action='count',
                      help="print status messages, or debug with -vv")
    parser.add_option('-q', '--quiet', default=0, action='count',
                      help="report only file names, or nothing with -qq")
    parser.add_option('--exclude', metavar='patterns', default=default_exclude,
                      help="skip matches (default %s)" % default_exclude)
    parser.add_option('--filename', metavar='patterns',
                      help="only check matching files (e.g. *.py)")
    parser.add_option('--ignore', metavar='errors', default='',
                      help="skip errors and warnings (e.g. E4,W)")
    parser.add_option('--repeat', action='store_true',
                      help="show all occurrences of the same error")
    parser.add_option('--show-source', action='store_true',
                      help="show source code for each error")
    parser.add_option('--show-pep8', action='store_true',
                      help="show text of PEP 8 for each error")
    parser.add_option('--statistics', action='store_true',
                      help="count errors and warnings")
    parser.add_option('--benchmark', action='store_true',
                      help="measure processing speed")
    parser.add_option('--testsuite', metavar='dir',
                      help="run regression tests from dir")
    parser.add_option('--doctest', action='store_true',
                      help="run doctest on myself")
    options, args = parser.parse_args(arglist)
    if options.testsuite:
        args.append(options.testsuite)
    if len(args) == 0:
        parser.error('input not specified')
    options.prog = os.path.basename(sys.argv[0])
    options.exclude = options.exclude.split(',')
    for index in range(len(options.exclude)):
        options.exclude[index] = options.exclude[index].rstrip('/')
    if options.filename:
        options.filename = options.filename.split(',')
    if options.ignore:
        options.ignore = options.ignore.split(',')
    else:
        options.ignore = []
    options.counters = {}
    options.messages = {}

    return options, args


def _main():
    """
    Parse options and run checks on Python source.
    """
    options, args = process_options()
    if options.doctest:
        import doctest
        return doctest.testmod()
    start_time = time.time()
    for path in args:
        if os.path.isdir(path):
            input_dir(path)
        else:
            input_file(path)
    elapsed = time.time() - start_time
    if options.statistics:
        print_statistics()
    if options.benchmark:
        print_benchmark(elapsed)


if __name__ == '__main__':
    _main()

########NEW FILE########
__FILENAME__ = cliarg_parser
#!/usr/bin/env python

"""Constructs command line argument parser for tvnamer
"""

from __future__ import with_statement
import sys
import optparse


class Group(object):
    """Simple helper context manager to add a group to an OptionParser
    """

    def __init__(self, parser, name):
        self.parser = parser
        self.name = name
        self.group = optparse.OptionGroup(self.parser, name)

    def __enter__(self):
        return self.group

    def __exit__(self, *k, **kw):
        self.parser.add_option_group(self.group)


def getCommandlineParser(defaults):
    parser = optparse.OptionParser(usage = "%prog [options] <files>", add_help_option = False)

    if sys.version_info < (2, 6, 5):
        # Hacky workaround to avoid bug in Python 2.6.1 triggered by use of builtin json module in 2.6
        # http://bugs.python.org/issue4978
        # http://bugs.python.org/issue2646

        #TODO: Remove this at some point
        defaults = dict([(str(k), v) for k, v in defaults.items()])

    parser.set_defaults(**defaults)

    # Console output
    with Group(parser, "Console output") as g:
        g.add_option("-v", "--verbose", action="store_true", dest="verbose", help = "show debugging info")
        g.add_option("-q", "--not-verbose", action="store_false", dest="verbose", help = "no verbose output (useful to override 'verbose':true in config file)")


    # Batch options
    with Group(parser, "Batch options") as g:
        g.add_option("-a", "--always", action="store_true", dest="always_rename", help = "Always renames files (but prompt for correct series)")
        g.add_option("--not-always", action="store_true", dest="always_rename", help = "Overrides --always")

        g.add_option("-f", "--selectfirst", action="store_true", dest="select_first", help = "Select first series search result automatically")
        g.add_option("--not-selectfirst", action="store_false", dest="select_first", help = "Overrides --selectfirst")

        g.add_option("-b", "--batch", action="store_true", dest = "batch", help = "Rename without human intervention, same as --always and --selectfirst combined")
        g.add_option("--not-batch", action="store_false", dest = "batch", help = "Overrides --batch")


    # Config options
    with Group(parser, "Config options") as g:
        g.add_option("-c", "--config", action = "store", dest = "loadconfig", help = "Load config from this file")
        g.add_option("-s", "--save", action = "store", dest = "saveconfig", help = "Save configuration to this file and exit")
        g.add_option("-p", "--preview-config", action = "store_true", dest = "showconfig", help = "Show current config values and exit")

    # Override values
    with Group(parser, "Override values") as g:
        g.add_option("-n", "--name", action="store", dest = "force_name", help = "override the parsed series name with this (applies to all files)")
        g.add_option("--series-id", action="store", dest = "series_id", help = "explicitly set the show id for TVdb to use (applies to all files)")

    # Misc
    with Group(parser, "Misc") as g:
        g.add_option("-r", "--recursive", action="store_true", dest = "recursive", help = "Descend more than one level directories supplied as arguments")
        g.add_option("--not-recursive", action="store_false", dest = "recursive", help = "Only descend one level into directories")

        g.add_option("-m", "--move", action="store_true", dest="move_files_enable", help = "Move files to destination specified in config or with --movedestination argument")
        g.add_option("--not-move", action="store_false", dest="move_files_enable", help = "Files will remain in current directory")

        g.add_option("-d", "--movedestination", action="store", dest = "move_files_destination", help = "Destination to move files to. Variables: %(seriesname)s %(seasonnumber)d %(episodenumbers)s")

        g.add_option("-h", "--help", action="help", help = "show this help message and exit")


    return parser


if __name__ == '__main__':

    def main():
        p = getCommandlineParser({'recursive': True})
        print p.parse_args()

    main()

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python

"""Holds Config singleton
"""

from config_defaults import defaults

Config = dict(defaults)

########NEW FILE########
__FILENAME__ = config_defaults
#!/usr/bin/env python

"""Holds default config values
"""

defaults = {
    # Select first series search result
    'select_first': False,

    # Always rename files
    'always_rename': False,

    # Batch (same as select_first and always_rename)
    'batch': False,

    # Fail if error finding show data (thetvdb.com is down etc)
    # Only functions when always_rename is True
    'skip_file_on_error': True,

    # Forcefully overwrite existing files when renaming or
    # moving. This potentially destroys the old file. Default is False
    'overwrite_destination_on_rename': False,
    'overwrite_destination_on_move': False,

    # Verbose mode (debugging info)
    'verbose': False,

    # Recurse more than one level into folders. When False, only
    # desends one level.
    'recursive': False,

    # When non-empty, only look for files with this extension.
    # No leading dot, for example: ['avi', 'mkv', 'mp4']
    'valid_extensions': [],

    # Pattern for splitting filenames into basename and extension.
    # Useful for matching subtitles with language codes, for example
    # "extension_pattern": "(\.(eng|cze))?(\.[a-zA-Z0-9]+)$" will split "foo.eng.srt"
    # into "foo" and ".eng.srt".
    # Note that extensions still pass 'valid_extensions' filter, '.eng.srt' passes
    # when 'srt' is specified in 'valid_extensions'.
    'extension_pattern': '(\.[a-zA-Z0-9]+)$',

    # When non-empty, filter out filenames that match these expressions. Either simple
    # matches or regexs can be used. The following are near enough equivalent:
    # [{"is_regex": true, "match": ".*sample.*"}, {"is_regex": false, "match": "sample"}]
    'filename_blacklist': [],

    # Force Windows safe filenames (always True on Windows)
    'windows_safe_filenames': False,

    # Replace accented unicode characters with ASCII equivalents,
    # removing characters than can't be translated.
    'normalize_unicode_filenames': False,

    # Convert output filenames to lower case (applied after replacements)
    'lowercase_filename': False,

    # Convert output filenames to 'Title Case' (applied after replacements)
    'titlecase_filename': False,

    # Extra characters to consider invalid in output filenames (which are
    # replaced by the character in replace_invalid_characters_with)
    'custom_filename_character_blacklist': '',

    # Replacement characters for invalid filename characters
    'replace_invalid_characters_with': '_',

    # Replacements performed on input file before parsing.
    'input_filename_replacements': [
    ],

    # Replacements performed on files after the new name is generated.
    'output_filename_replacements': [
    ],

    # Replacements are performed on the full path used by move_files feature,
    # including the filename
    'move_files_fullpath_replacements': [
    ],

    # Language to (try) and retrieve episode data in
    'language': 'en',

    # Search in all possible languages
    'search_all_languages': True,

    # Move renamed files to directory?
    'move_files_enable': False,

    # Separate confirmation of moving or copying renamed file?  If
    # False, will move files when renaming. In batch mode, will never
    # prompt.
    'move_files_confirmation': True,

    # If true, convert the variable/dynamic parts of the destination
    # to lower case. Does not affect the static parts; for example,
    # if move_files_destination is set to
    # '/Foo/Bar/%(seriesname)s/Season %(seasonnumber)d'
    # then only the series name will be converted to lower case.
    'move_files_lowercase_destination': False,

    # If True, the destination path includes the destination filename,
    # for example: '/example/tv/%(seriesname)s/season %(seasonnumber)d/%(originalfilename)'
    'move_files_destination_is_filepath': False,

    # Destination to move files to. Trailing slash is not necessary.
    # Use forward slashes, even on Windows. Realtive paths are realtive to
    # the existing file's path (not current working dir). A value of '.' will
    # not move the file anywhere.
    #
    # Use Python's string formatting to add dynamic paths. Available variables:
    # - %(seriesname)s
    # - %(seasonnumber)d
    # - %(episodenumbers)s (Note: this is a string, formatted with config
    #                       variable episode_single and joined with episode_separator)
    'move_files_destination': '.',

    # Same as above, only for date-numbered episodes. The following
    # variables are available:
    # - %(seriesname)s
    # - %(year)s
    # - %(month)s
    # - %(day)s
    'move_files_destination_date': '.',

    # Force the move-files feature to always move the file.
    #
    # If False, when a file is moved between partitions (or from a
    # network volume), the original is left untouched (i.e it is
    # copied).  If True, this will delete the file from the original
    # volume, after the copy has complete.
    'always_move': False,

    # Whenever a file is moved leave a symlink to the new file behind, named
    # after the original file.
    'leave_symlink': False,

    # Allow user to copy files to specified move location without renaming files.
    'move_files_only': False,

    # Patterns to parse input filenames with
    'filename_patterns': [
        # [group] Show - 01-02 [crc]
        '''^\[(?P<group>.+?)\][ ]?               # group name, captured for [#100]
        (?P<seriesname>.*?)[ ]?[-_][ ]?          # show name, padding, spaces?
        (?P<episodenumberstart>\d+)              # first episode number
        ([-_]\d+)*                               # optional repeating episodes
        [-_](?P<episodenumberend>\d+)            # last episode number
        (?=                                      # Optional group for crc value (non-capturing)
          .*                                     # padding
          \[(?P<crc>.+?)\]                       # CRC value
        )?                                       # End optional crc group
        [^\/]*$''',

        # [group] Show - 01 [crc]
        '''^\[(?P<group>.+?)\][ ]?               # group name, captured for [#100]
        (?P<seriesname>.*)                       # show name
        [ ]?[-_][ ]?                             # padding and seperator
        (?P<episodenumber>\d+)                   # episode number
        (?=                                      # Optional group for crc value (non-capturing)
          .*                                     # padding
          \[(?P<crc>.+?)\]                       # CRC value
        )?                                       # End optional crc group
        [^\/]*$''',

        # foo s01e23 s01e24 s01e25 *
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        [Ss](?P<seasonnumber>[0-9]+)             # s01
        [\.\- ]?                                 # separator
        [Ee](?P<episodenumberstart>[0-9]+)       # first e23
        ([\.\- ]+                                # separator
        [Ss](?P=seasonnumber)                    # s01
        [\.\- ]?                                 # separator
        [Ee][0-9]+)*                             # e24 etc (middle groups)
        ([\.\- ]+                                # separator
        [Ss](?P=seasonnumber)                    # last s01
        [\.\- ]?                                 # separator
        [Ee](?P<episodenumberend>[0-9]+))        # final episode number
        [^\/]*$''',

        # foo.s01e23e24*
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        [Ss](?P<seasonnumber>[0-9]+)             # s01
        [\.\- ]?                                 # separator
        [Ee](?P<episodenumberstart>[0-9]+)       # first e23
        ([\.\- ]?                                # separator
        [Ee][0-9]+)*                             # e24e25 etc
        [\.\- ]?[Ee](?P<episodenumberend>[0-9]+) # final episode num
        [^\/]*$''',

        # foo.1x23 1x24 1x25
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        (?P<seasonnumber>[0-9]+)                 # first season number (1)
        [xX](?P<episodenumberstart>[0-9]+)       # first episode (x23)
        ([ \._\-]+                               # separator
        (?P=seasonnumber)                        # more season numbers (1)
        [xX][0-9]+)*                             # more episode numbers (x24)
        ([ \._\-]+                               # separator
        (?P=seasonnumber)                        # last season number (1)
        [xX](?P<episodenumberend>[0-9]+))        # last episode number (x25)
        [^\/]*$''',

        # foo.1x23x24*
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        (?P<seasonnumber>[0-9]+)                 # 1
        [xX](?P<episodenumberstart>[0-9]+)       # first x23
        ([xX][0-9]+)*                            # x24x25 etc
        [xX](?P<episodenumberend>[0-9]+)         # final episode num
        [^\/]*$''',

        # foo.s01e23-24*
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        [Ss](?P<seasonnumber>[0-9]+)             # s01
        [\.\- ]?                                 # separator
        [Ee](?P<episodenumberstart>[0-9]+)       # first e23
        (                                        # -24 etc
             [\-]
             [Ee]?[0-9]+
        )*
             [\-]                                # separator
             [Ee]?(?P<episodenumberend>[0-9]+)   # final episode num
        [\.\- ]                                  # must have a separator (prevents s01e01-720p from being 720 episodes)
        [^\/]*$''',

        # foo.1x23-24*
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        (?P<seasonnumber>[0-9]+)                 # 1
        [xX](?P<episodenumberstart>[0-9]+)       # first x23
        (                                        # -24 etc
             [\-+][0-9]+
        )*
             [\-+]                               # separator
             (?P<episodenumberend>[0-9]+)        # final episode num
        ([\.\-+ ].*                              # must have a separator (prevents 1x01-720p from being 720 episodes)
        |
        $)''',

        # foo.[1x09-11]*
        '''^(?P<seriesname>.+?)[ \._\-]          # show name and padding
        \[                                       # [
            ?(?P<seasonnumber>[0-9]+)            # season
        [xX]                                     # x
            (?P<episodenumberstart>[0-9]+)       # episode
            ([\-+] [0-9]+)*
        [\-+]                                    # -
            (?P<episodenumberend>[0-9]+)         # episode
        \]                                       # \]
        [^\\/]*$''',

        # foo - [012]
        '''^((?P<seriesname>.+?)[ \._\-])?       # show name and padding
        \[                                       # [ not optional (or too ambigious)
        (?P<episodenumber>[0-9]+)                # episode
        \]                                       # ]
        [^\\/]*$''',
        # foo.s0101, foo.0201
        '''^(?P<seriesname>.+?)[ \._\-]
        [Ss](?P<seasonnumber>[0-9]{2})
        [\.\- ]?
        (?P<episodenumber>[0-9]{2})
        [^0-9]*$''',

        # foo.1x09*
        '''^((?P<seriesname>.+?)[ \._\-])?       # show name and padding
        \[?                                      # [ optional
        (?P<seasonnumber>[0-9]+)                 # season
        [xX]                                     # x
        (?P<episodenumber>[0-9]+)                # episode
        \]?                                      # ] optional
        [^\\/]*$''',

        # foo.s01.e01, foo.s01_e01, "foo.s01 - e01"
        '''^((?P<seriesname>.+?)[ \._\-])?
        \[?
        [Ss](?P<seasonnumber>[0-9]+)[ ]?[\._\- ]?[ ]?
        [Ee]?(?P<episodenumber>[0-9]+)
        \]?
        [^\\/]*$''',

        # foo.2010.01.02.etc
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        (?P<year>\d{4})                          # year
        [ \._\-]                                 # separator
        (?P<month>\d{2})                         # month
        [ \._\-]                                 # separator
        (?P<day>\d{2})                           # day
        [^\/]*$''',

        # foo - [01.09]
        '''^((?P<seriesname>.+?))                # show name
        [ \._\-]?                                # padding
        \[                                       # [
        (?P<seasonnumber>[0-9]+?)                # season
        [.]                                      # .
        (?P<episodenumber>[0-9]+?)               # episode
        \]                                       # ]
        [ \._\-]?                                # padding
        [^\\/]*$''',

        # Foo - S2 E 02 - etc
        '''^(?P<seriesname>.+?)[ ]?[ \._\-][ ]?
        [Ss](?P<seasonnumber>[0-9]+)[\.\- ]?
        [Ee]?[ ]?(?P<episodenumber>[0-9]+)
        [^\\/]*$''',

        # Show - Episode 9999 [S 12 - Ep 131] - etc
        '''
        (?P<seriesname>.+)                       # Showname
        [ ]-[ ]                                  # -
        [Ee]pisode[ ]\d+                         # Episode 1234 (ignored)
        [ ]
        \[                                       # [
        [sS][ ]?(?P<seasonnumber>\d+)            # s 12
        ([ ]|[ ]-[ ]|-)                          # space, or -
        ([eE]|[eE]p)[ ]?(?P<episodenumber>\d+)   # e or ep 12
        \]                                       # ]
        .*$                                      # rest of file
        ''',

        # show name 2 of 6 - blah
        '''^(?P<seriesname>.+?)                  # Show name
        [ \._\-]                                 # Padding
        (?P<episodenumber>[0-9]+)                # 2
        of                                       # of
        [ \._\-]?                                # Padding
        \d+                                      # 6
        ([\._ -]|$|[^\\/]*$)                     # More padding, then anything
        ''',

        # Show.Name.Part.1.and.Part.2
        '''^(?i)
        (?P<seriesname>.+?)                        # Show name
        [ \._\-]                                   # Padding
        (?:part|pt)?[\._ -]
        (?P<episodenumberstart>[0-9]+)             # Part 1
        (?:
          [ \._-](?:and|&|to)                        # and
          [ \._-](?:part|pt)?                        # Part 2
          [ \._-](?:[0-9]+))*                        # (middle group, optional, repeating)
        [ \._-](?:and|&|to)                        # and
        [ \._-]?(?:part|pt)?                       # Part 3
        [ \._-](?P<episodenumberend>[0-9]+)        # last episode number, save it
        [\._ -][^\\/]*$                            # More padding, then anything
        ''',

        # Show.Name.Part1
        '''^(?P<seriesname>.+?)                  # Show name\n
        [ \\._\\-]                               # Padding\n
        [Pp]art[ ](?P<episodenumber>[0-9]+)      # Part 1\n
        [\\._ -][^\\/]*$                         # More padding, then anything\n
        ''',

        # show name Season 01 Episode 20
        '''^(?P<seriesname>.+?)[ ]?               # Show name
        [Ss]eason[ ]?(?P<seasonnumber>[0-9]+)[ ]? # Season 1
        [Ee]pisode[ ]?(?P<episodenumber>[0-9]+)   # Episode 20
        [^\\/]*$''',                              # Anything

        # foo.103*
        '''^(?P<seriesname>.+)[ \._\-]
        (?P<seasonnumber>[0-9]{1})
        (?P<episodenumber>[0-9]{2})
        [\._ -][^\\/]*$''',

        # foo.0103*
        '''^(?P<seriesname>.+)[ \._\-]
        (?P<seasonnumber>[0-9]{2})
        (?P<episodenumber>[0-9]{2,3})
        [\._ -][^\\/]*$''',

        # show.name.e123.abc
        '''^(?P<seriesname>.+?)                  # Show name
        [ \._\-]                                 # Padding
        [Ee](?P<episodenumber>[0-9]+)            # E123
        [\._ -][^\\/]*$                          # More padding, then anything
        ''',
    ],

    # Formats for renamed files. Variations for with/without episode,
    # and with/without season number.
    'filename_with_episode':
     '%(seriesname)s - [%(seasonnumber)02dx%(episode)s] - %(episodename)s%(ext)s',
    'filename_without_episode':
     '%(seriesname)s - [%(seasonnumber)02dx%(episode)s]%(ext)s',

    # Seasonless filenames.
    'filename_with_episode_no_season':
      '%(seriesname)s - [%(episode)s] - %(episodename)s%(ext)s',
    'filename_without_episode_no_season':
     '%(seriesname)s - [%(episode)s]%(ext)s',

    # Date based filenames.
    # Series - [2012-01-24] - Ep name.ext
    'filename_with_date_and_episode':
     '%(seriesname)s - [%(episode)s] - %(episodename)s%(ext)s',
    'filename_with_date_without_episode':
     '%(seriesname)s - [%(episode)s]%(ext)s',

    # Anime filenames.
    # [AGroup] Series - 02 - Some Ep Name [CRC1234].ext
    # [AGroup] Series - 02 [CRC1234].ext
    'filename_anime_with_episode':
     '[%(group)s] %(seriesname)s - %(episode)s - %(episodename)s [%(crc)s]%(ext)s',

    'filename_anime_without_episode':
     '[%(group)s] %(seriesname)s - %(episode)s [%(crc)s]%(ext)s',

    # Same, without CRC value
    'filename_anime_with_episode_without_crc':
     '[%(group)s] %(seriesname)s - %(episode)s - %(episodename)s%(ext)s',

    'filename_anime_without_episode_without_crc':
     '[%(group)s] %(seriesname)s - %(episode)s%(ext)s',



    # Used to join multiple episode names together (only when episode names are different)
    'multiep_join_name_with': ', ',

    # Format for multi-episode names (only when episode names are the same)
    # Formats mapping key 'episodename' (used in variables 'filename_with_episode' etc.)
    'multiep_format': '%(epname)s (%(episodemin)s-%(episodemax)s)',

    # Format for numbers (python string format), %02d does 2-digit padding, %d will cause no padding
    'episode_single': '%02d',

    # String to join multiple numbers in mapping key 'episode' (used in variables 'filename_with_episode' etc.)
    'episode_separator': '-',

    # Series ID to use instead of searching if the value is set
    #'series_id': None,

    # Forced Name to use
    #'forced_name': None,

    # replace series names before/after passing to TVDB
    # input replacements are regular expressions for the series as parsed from
    # filenames, for instance adding or removing the year, or expanding abbreviations
    'input_series_replacements': {},

    # output replacements are for transforms of the TVDB series names
    # since these are perfectly predictable, they are simple strings
    # not regular expressions
    'output_series_replacements': {},
}

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

"""Main tvnamer utility functionality
"""

import os
import sys
import logging
import warnings

try:
    import readline
except ImportError:
    pass

try:
    import json
except ImportError:
    import simplejson as json

from tvdb_api import Tvdb

import cliarg_parser
from config_defaults import defaults

from unicode_helper import p
from utils import (Config, FileFinder, FileParser, Renamer, warn,
applyCustomInputReplacements, formatEpisodeNumbers, makeValidFilename,
DatedEpisodeInfo, NoSeasonEpisodeInfo)

from tvnamer_exceptions import (ShowNotFound, SeasonNotFound, EpisodeNotFound,
EpisodeNameNotFound, UserAbort, InvalidPath, NoValidFilesFoundError,
InvalidFilename, DataRetrievalError)


def log():
    """Returns the logger for current file
    """
    return logging.getLogger(__name__)


def getMoveDestination(episode):
    """Constructs the location to move/copy the file
    """

    #TODO: Write functional test to ensure this valid'ifying works
    def wrap_validfname(fname):
        """Wrap the makeValidFilename function as it's called twice
        and this is slightly long..
        """
        if Config['move_files_lowercase_destination']:
            fname = fname.lower()
        return makeValidFilename(
            fname,
            normalize_unicode = Config['normalize_unicode_filenames'],
            windows_safe = Config['windows_safe_filenames'],
            custom_blacklist = Config['custom_filename_character_blacklist'],
            replace_with = Config['replace_invalid_characters_with'])


    # Calls makeValidFilename on series name, as it must valid for a filename
    if isinstance(episode, DatedEpisodeInfo):
        print Config['move_files_destination_date']
        destdir = Config['move_files_destination_date'] % {
            'seriesname': makeValidFilename(episode.seriesname),
            'year': episode.episodenumbers[0].year,
            'month': episode.episodenumbers[0].month,
            'day': episode.episodenumbers[0].day,
            'originalfilename': episode.originalfilename,
            }
    elif isinstance(episode, NoSeasonEpisodeInfo):
        destdir = Config['move_files_destination'] % {
            'seriesname': wrap_validfname(episode.seriesname),
            'episodenumbers': wrap_validfname(formatEpisodeNumbers(episode.episodenumbers)),
            'originalfilename': episode.originalfilename,
            }
    else:
        destdir = Config['move_files_destination'] % {
            'seriesname': wrap_validfname(episode.seriesname),
            'seasonnumber': episode.seasonnumber,
            'episodenumbers': wrap_validfname(formatEpisodeNumbers(episode.episodenumbers)),
            'originalfilename': episode.originalfilename,
            }
    return destdir


def doRenameFile(cnamer, newName):
    """Renames the file. cnamer should be Renamer instance,
    newName should be string containing new filename.
    """
    try:
        cnamer.newPath(new_fullpath = newName, force = Config['overwrite_destination_on_rename'], leave_symlink = Config['leave_symlink'])
    except OSError, e:
        warn(e)


def doMoveFile(cnamer, destDir = None, destFilepath = None, getPathPreview = False):
    """Moves file to destDir, or to destFilepath
    """

    if (destDir is None and destFilepath is None) or (destDir is not None and destFilepath is not None):
        raise ValueError("Specify only destDir or destFilepath")

    if not Config['move_files_enable']:
        raise ValueError("move_files feature is disabled but doMoveFile was called")

    if Config['move_files_destination'] is None:
        raise ValueError("Config value for move_files_destination cannot be None if move_files_enabled is True")

    try:
        return cnamer.newPath(
            new_path = destDir,
            new_fullpath = destFilepath,
            always_move = Config['always_move'],
            leave_symlink = Config['leave_symlink'],
            getPathPreview = getPathPreview,
            force = Config['overwrite_destination_on_move'])

    except OSError, e:
        warn(e)


def confirm(question, options, default = "y"):
    """Takes a question (string), list of options and a default value (used
    when user simply hits enter).
    Asks until valid option is entered.
    """
    # Highlight default option with [ ]
    options_str = []
    for x in options:
        if x == default:
            x = "[%s]" % x
        if x != '':
            options_str.append(x)
    options_str = "/".join(options_str)

    while True:
        p(question)
        p("(%s) " % (options_str), end="")
        try:
            ans = raw_input().strip()
        except KeyboardInterrupt, errormsg:
            p("\n", errormsg)
            raise UserAbort(errormsg)

        if ans in options:
            return ans
        elif ans == '':
            return default


def processFile(tvdb_instance, episode):
    """Gets episode name, prompts user for input
    """
    p("#" * 20)
    p("# Processing file: %s" % episode.fullfilename)

    if len(Config['input_filename_replacements']) > 0:
        replaced = applyCustomInputReplacements(episode.fullfilename)
        p("# With custom replacements: %s" % (replaced))

    # Use force_name option. Done after input_filename_replacements so
    # it can be used to skip the replacements easily
    if Config['force_name'] is not None:
        episode.seriesname = Config['force_name']

    p("# Detected series: %s (%s)" % (episode.seriesname, episode.number_string()))

    try:
        episode.populateFromTvdb(tvdb_instance, force_name=Config['force_name'], series_id=Config['series_id'])
    except (DataRetrievalError, ShowNotFound), errormsg:
        if Config['always_rename'] and Config['skip_file_on_error'] is True:
            warn("Skipping file due to error: %s" % errormsg)
            return
        else:
            warn(errormsg)
    except (SeasonNotFound, EpisodeNotFound, EpisodeNameNotFound), errormsg:
        # Show was found, so use corrected series name
        if Config['always_rename'] and Config['skip_file_on_error']:
            warn("Skipping file due to error: %s" % errormsg)
            return

        warn(errormsg)

    cnamer = Renamer(episode.fullpath)


    shouldRename = False

    if Config["move_files_only"]:

        newName = episode.fullfilename
        shouldRename = True

    else:
        newName = episode.generateFilename()
        if newName == episode.fullfilename:
            p("#" * 20)
            p("Existing filename is correct: %s" % episode.fullfilename)
            p("#" * 20)

            shouldRename = True

        else:
            p("#" * 20)
            p("Old filename: %s" % episode.fullfilename)

            if len(Config['output_filename_replacements']) > 0:
                # Show filename without replacements
                p("Before custom output replacements: %s" % (episode.generateFilename(preview_orig_filename = False)))

            p("New filename: %s" % newName)

            if Config['always_rename']:
                doRenameFile(cnamer, newName)
                if Config['move_files_enable']:
                    if Config['move_files_destination_is_filepath']:
                        doMoveFile(cnamer = cnamer, destFilepath = getMoveDestination(episode))
                    else:
                        doMoveFile(cnamer = cnamer, destDir = getMoveDestination(episode))
                return

            ans = confirm("Rename?", options = ['y', 'n', 'a', 'q'], default = 'y')

            if ans == "a":
                p("Always renaming")
                Config['always_rename'] = True
                shouldRename = True
            elif ans == "q":
                p("Quitting")
                raise UserAbort("User exited with q")
            elif ans == "y":
                p("Renaming")
                shouldRename = True
            elif ans == "n":
                p("Skipping")
            else:
                p("Invalid input, skipping")

            if shouldRename:
                doRenameFile(cnamer, newName)

    if shouldRename and Config['move_files_enable']:
        newPath = getMoveDestination(episode)
        if Config['move_files_destination_is_filepath']:
            doMoveFile(cnamer = cnamer, destFilepath = newPath, getPathPreview = True)
        else:
            doMoveFile(cnamer = cnamer, destDir = newPath, getPathPreview = True)

        if not Config['batch'] and Config['move_files_confirmation']:
            ans = confirm("Move file?", options = ['y', 'n', 'q'], default = 'y')
        else:
            ans = 'y'

        if ans == 'y':
            p("Moving file")
            doMoveFile(cnamer, newPath)
        elif ans == 'q':
            p("Quitting")
            raise UserAbort("user exited with q")


def findFiles(paths):
    """Takes an array of paths, returns all files found
    """
    valid_files = []

    for cfile in paths:
        cur = FileFinder(
            cfile,
            with_extension = Config['valid_extensions'],
            filename_blacklist = Config["filename_blacklist"],
            recursive = Config['recursive'])

        try:
            valid_files.extend(cur.findFiles())
        except InvalidPath:
            warn("Invalid path: %s" % cfile)

    if len(valid_files) == 0:
        raise NoValidFilesFoundError()

    # Remove duplicate files (all paths from FileFinder are absolute)
    valid_files = list(set(valid_files))

    return valid_files


def tvnamer(paths):
    """Main tvnamer function, takes an array of paths, does stuff.
    """

    p("#" * 20)
    p("# Starting tvnamer")

    episodes_found = []

    for cfile in findFiles(paths):
        parser = FileParser(cfile)
        try:
            episode = parser.parse()
        except InvalidFilename, e:
            warn("Invalid filename: %s" % e)
        else:
            if episode.seriesname is None and Config['force_name'] is None and Config['series_id'] is None:
                warn("Parsed filename did not contain series name (and --name or --series-id not specified), skipping: %s" % cfile)

            else:
                episodes_found.append(episode)

    if len(episodes_found) == 0:
        raise NoValidFilesFoundError()

    p("# Found %d episode" % len(episodes_found) + ("s" * (len(episodes_found) > 1)))

    # Sort episodes by series name, season and episode number
    episodes_found.sort(key = lambda x: x.sortable_info())

    tvdb_instance = Tvdb(
        interactive = not Config['select_first'],
        search_all_languages = Config['search_all_languages'],
        language = Config['language'])

    for episode in episodes_found:
        processFile(tvdb_instance, episode)
        p('')

    p("#" * 20)
    p("# Done")


def main():
    """Parses command line arguments, displays errors from tvnamer in terminal
    """
    opter = cliarg_parser.getCommandlineParser(defaults)

    opts, args = opter.parse_args()

    if opts.verbose:
        logging.basicConfig(
            level = logging.DEBUG,
            format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    else:
        logging.basicConfig()

    # If a config is specified, load it, update the defaults using the loaded
    # values, then reparse the options with the updated defaults.
    default_configuration = os.path.expanduser("~/.tvnamer.json")

    if opts.loadconfig is not None:
        # Command line overrides loading ~/.tvnamer.json
        configToLoad = opts.loadconfig
    elif os.path.isfile(default_configuration):
        # No --config arg, so load default config if it exists
        configToLoad = default_configuration
    else:
        # No arg, nothing at default config location, don't load anything
        configToLoad = None

    if configToLoad is not None:
        p("Loading config: %s" % (configToLoad))
        try:
            loadedConfig = json.load(open(os.path.expanduser(configToLoad)))
        except ValueError, e:
            p("Error loading config: %s" % e)
            opter.exit(1)
        else:
            # Config loaded, update optparser's defaults and reparse
            defaults.update(loadedConfig)
            opter = cliarg_parser.getCommandlineParser(defaults)
            opts, args = opter.parse_args()

    # Decode args using filesystem encoding (done after config loading
    # as the args are reparsed when the config is loaded)
    args = [x.decode(sys.getfilesystemencoding()) for x in args]

    # Save config argument
    if opts.saveconfig is not None:
        p("Saving config: %s" % (opts.saveconfig))
        configToSave = dict(opts.__dict__)
        del configToSave['saveconfig']
        del configToSave['loadconfig']
        del configToSave['showconfig']
        json.dump(
            configToSave,
            open(os.path.expanduser(opts.saveconfig), "w+"),
            sort_keys=True,
            indent=4)

        opter.exit(0)

    # Show config argument
    if opts.showconfig:
        print json.dumps(opts.__dict__, sort_keys=True, indent=2)
        return

    # Process values
    if opts.batch:
        opts.select_first = True
        opts.always_rename = True

    # Update global config object
    Config.update(opts.__dict__)

    if Config["move_files_only"] and not Config["move_files_enable"]:
        p("#" * 20)
        p("Parameter move_files_enable cannot be set to false while parameter move_only is set to true.")
        p("#" * 20)
        opter.exit(0)

    if Config['titlecase_filename'] and Config['lowercase_filename']:
        warnings.warn("Setting 'lowercase_filename' clobbers 'titlecase_filename' option")

    if len(args) == 0:
        opter.error("No filenames or directories supplied")

    try:
        tvnamer(paths = sorted(args))
    except NoValidFilesFoundError:
        opter.error("No valid files were supplied")
    except UserAbort, errormsg:
        opter.error(errormsg)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tvnamer_exceptions
#!/usr/bin/env python

"""Exceptions used through-out tvnamer
"""


class BaseTvnamerException(Exception):
    """Base exception all tvnamers exceptions inherit from
    """
    pass


class InvalidPath(BaseTvnamerException):
    """Raised when an argument is a non-existent file or directory path
    """
    pass


class NoValidFilesFoundError(BaseTvnamerException):
    """Raised when no valid files are found. Effectively exits tvnamer
    """
    pass


class InvalidFilename(BaseTvnamerException):
    """Raised when a file is parsed, but no episode info can be found
    """
    pass


class UserAbort(BaseTvnamerException):
    """Base exception for config errors
    """
    pass


class BaseConfigError(BaseTvnamerException):
    """Base exception for config errors
    """
    pass


class ConfigValueError(BaseConfigError):
    """Raised if the config file is malformed or unreadable
    """
    pass


class DataRetrievalError(BaseTvnamerException):
    """Raised when an error (such as a network problem) prevents tvnamer
    from being able to retrieve data such as episode name
    """


class ShowNotFound(DataRetrievalError):
    """Raised when a show cannot be found
    """
    pass


class SeasonNotFound(DataRetrievalError):
    """Raised when requested season cannot be found
    """
    pass


class EpisodeNotFound(DataRetrievalError):
    """Raised when episode cannot be found
    """
    pass


class EpisodeNameNotFound(DataRetrievalError):
    """Raised when the name of the episode cannot be found
    """
    pass

########NEW FILE########
__FILENAME__ = unicode_helper
#!/usr/bin/env python

"""Helpers to deal with strings, unicode objects and terminal output
"""

import sys


def unicodify(obj, encoding = "utf-8"):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def p(*args, **kw):
    """Rough implementation of the Python 3 print function,
    http://www.python.org/dev/peps/pep-3105/

    def print(*args, sep=' ', end='\n', file=None)

    """
    kw.setdefault('encoding', 'utf-8')
    kw.setdefault('sep', ' ')
    kw.setdefault('end', '\n')
    kw.setdefault('file', sys.stdout)

    new_args = []
    for x in args:
        if not isinstance(x, basestring):
            new_args.append(repr(x))
        else:
            if kw['encoding'] is not None:
                new_args.append(x.encode(kw['encoding']))
            else:
                new_args.append(x)

    out = kw['sep'].join(new_args)

    kw['file'].write(out + kw['end'])

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python

"""Utilities for tvnamer, including filename parsing
"""

import datetime
import os
import re
import sys
import shutil
import logging
import platform
import errno

from tvdb_api import (tvdb_error, tvdb_shownotfound, tvdb_seasonnotfound,
tvdb_episodenotfound, tvdb_attributenotfound, tvdb_userabort)

from unicode_helper import p

from config import Config
from tvnamer_exceptions import (InvalidPath, InvalidFilename,
ShowNotFound, DataRetrievalError, SeasonNotFound, EpisodeNotFound,
EpisodeNameNotFound, ConfigValueError, UserAbort)


def log():
    """Returns the logger for current file
    """
    return logging.getLogger(__name__)


def warn(text):
    """Displays message to sys.stderr
    """
    p(text, file = sys.stderr)


def split_extension(filename):
    base = re.sub(Config["extension_pattern"], "", filename)
    ext = filename.replace(base, "")
    return base, ext


def _applyReplacements(cfile, replacements):
    """Applies custom replacements.

    Argument cfile is string.

    Argument replacements is a list of dicts, with keys "match",
    "replacement", and (optional) "is_regex"
    """
    for rep in replacements:
        if not rep.get('with_extension', False):
            # By default, preserve extension
            cfile, cext = split_extension(cfile)
        else:
            cfile = cfile
            cext = ""

        if 'is_regex' in rep and rep['is_regex']:
            cfile = re.sub(rep['match'], rep['replacement'], cfile)
        else:
            cfile = cfile.replace(rep['match'], rep['replacement'])

        # Rejoin extension (cext might be empty-string)
        cfile = cfile + cext

    return cfile


def applyCustomInputReplacements(cfile):
    """Applies custom input filename replacements, wraps _applyReplacements
    """
    return _applyReplacements(cfile, Config['input_filename_replacements'])


def applyCustomOutputReplacements(cfile):
    """Applies custom output filename replacements, wraps _applyReplacements
    """
    return _applyReplacements(cfile, Config['output_filename_replacements'])


def applyCustomFullpathReplacements(cfile):
    """Applies custom replacements to full path, wraps _applyReplacements
    """
    return _applyReplacements(cfile, Config['move_files_fullpath_replacements'])


def cleanRegexedSeriesName(seriesname):
    """Cleans up series name by removing any . and _
    characters, along with any trailing hyphens.

    Is basically equivalent to replacing all _ and . with a
    space, but handles decimal numbers in string, for example:

    >>> cleanRegexedSeriesName("an.example.1.0.test")
    'an example 1.0 test'
    >>> cleanRegexedSeriesName("an_example_1.0_test")
    'an example 1.0 test'
    """
    # TODO: Could this be made to clean "Hawaii.Five-0.2010" into "Hawaii Five-0 2010"?
    seriesname = re.sub("(\D)[.](\D)", "\\1 \\2", seriesname)
    seriesname = re.sub("(\D)[.]", "\\1 ", seriesname)
    seriesname = re.sub("[.](\D)", " \\1", seriesname)
    seriesname = seriesname.replace("_", " ")
    seriesname = re.sub("-$", "", seriesname)
    return seriesname.strip()


def replaceInputSeriesName(seriesname):
    """allow specified replacements of series names

    in cases where default filenames match the wrong series,
    e.g. missing year gives wrong answer, or vice versa

    This helps the TVDB query get the right match.
    """
    for pat, replacement in Config['input_series_replacements'].iteritems():
        if re.match(pat, seriesname, re.IGNORECASE|re.UNICODE):
            return replacement
    return seriesname


def replaceOutputSeriesName(seriesname):
    """transform TVDB series names

    after matching from TVDB, transform the series name for desired abbreviation, etc.

    This affects the output filename.
    """

    return Config['output_series_replacements'].get(seriesname, seriesname)


def handleYear(year):
    """Handle two-digit years with heuristic-ish guessing

    Assumes 50-99 becomes 1950-1999, and 0-49 becomes 2000-2049

    ..might need to rewrite this function in 2050, but that seems like
    a reasonable limitation
    """

    year = int(year)

    # No need to guess with 4-digit years
    if year > 999:
        return year

    if year < 50:
        return 2000 + year
    else:
        return 1900 + year


class FileFinder(object):
    """Given a file, it will verify it exists. Given a folder it will descend
    one level into it and return a list of files, unless the recursive argument
    is True, in which case it finds all files contained within the path.

    The with_extension argument is a list of valid extensions, without leading
    spaces. If an empty list (or None) is supplied, no extension checking is
    performed.

    The filename_blacklist argument is a list of regexp strings to match against
    the filename (minus the extension). If a match is found, the file is skipped
    (e.g. for filtering out "sample" files). If [] or None is supplied, no
    filtering is done
    """

    def __init__(self, path, with_extension = None, filename_blacklist = None, recursive = False):
        self.path = path
        if with_extension is None:
            self.with_extension = []
        else:
            self.with_extension = with_extension
        if filename_blacklist is None:
            self.with_blacklist = []
        else:
            self.with_blacklist = filename_blacklist
        self.recursive = recursive

    def findFiles(self):
        """Returns list of files found at path
        """
        if os.path.isfile(self.path):
            path = os.path.abspath(self.path)
            if self._checkExtension(path) and not self._blacklistedFilename(path):
                return [path]
            else:
                return []
        elif os.path.isdir(self.path):
            return self._findFilesInPath(self.path)
        else:
            raise InvalidPath("%s is not a valid file/directory" % self.path)

    def _checkExtension(self, fname):
        """Checks if the file extension is blacklisted in valid_extensions
        """
        if len(self.with_extension) == 0:
            return True

        # don't use split_extension here (otherwise valid_extensions is useless)!
        _, extension = os.path.splitext(fname)
        for cext in self.with_extension:
            cext = ".%s" % cext
            if extension == cext:
                return True
        else:
            return False

    def _blacklistedFilename(self, filepath):
        """Checks if the filename (optionally excluding extension)
        matches filename_blacklist

        self.with_blacklist should be a list of strings and/or dicts:

        a string, specifying an exact filename to ignore
        "filename_blacklist": [".DS_Store", "Thumbs.db"],

        a dictionary, where each dict contains:

        Key 'match' - (if the filename matches the pattern, the filename
        is blacklisted)

        Key 'is_regex' - if True, the pattern is treated as a
        regex. If False, simple substring check is used (if
        cur['match'] in filename). Default is False

        Key 'full_path' - if True, full path is checked. If False, only
        filename is checked. Default is False.

        Key 'exclude_extension' - if True, the extension is removed
        from the file before checking. Default is False.
        """

        if len(self.with_blacklist) == 0:
            return False

        fdir, fullname = os.path.split(filepath)
        fname, fext = split_extension(fullname)

        for fblacklist in self.with_blacklist:
            if isinstance(fblacklist, basestring):
                if fullname == fblacklist:
                    return True
                else:
                    continue

            if "full_path" in fblacklist and fblacklist["full_path"]:
                to_check = filepath
            else:
                if fblacklist.get("exclude_extension", False):
                    to_check = fname
                else:
                    to_check = fullname

            if fblacklist.get("is_regex", False):
                m = re.match(fblacklist["match"], to_check)
                if m is not None:
                    return True
            else:
                m = fblacklist["match"] in to_check
                if m:
                    return True
        else:
            return False

    def _findFilesInPath(self, startpath):
        """Finds files from startpath, could be called recursively
        """
        allfiles = []
        if not os.access(startpath, os.R_OK):
            log().info("Skipping inaccessible path %s" % startpath)
            return allfiles

        for subf in os.listdir(unicode(startpath)):
            newpath = os.path.join(startpath, subf)
            newpath = os.path.abspath(newpath)
            if os.path.isfile(newpath):
                if not self._checkExtension(subf):
                    continue
                elif self._blacklistedFilename(subf):
                    continue
                else:
                    allfiles.append(newpath)
            else:
                if self.recursive:
                    allfiles.extend(self._findFilesInPath(newpath))
                #end if recursive
            #end if isfile
        #end for sf
        return allfiles


class FileParser(object):
    """Deals with parsing of filenames
    """

    def __init__(self, path):
        self.path = path
        self.compiled_regexs = []
        self._compileRegexs()

    def _compileRegexs(self):
        """Takes episode_patterns from config, compiles them all
        into self.compiled_regexs
        """
        for cpattern in Config['filename_patterns']:
            try:
                cregex = re.compile(cpattern, re.VERBOSE)
            except re.error, errormsg:
                warn("WARNING: Invalid episode_pattern (error: %s)\nPattern:\n%s" % (
                    errormsg, cpattern))
            else:
                self.compiled_regexs.append(cregex)

    def parse(self):
        """Runs path via configured regex, extracting data from groups.
        Returns an EpisodeInfo instance containing extracted data.
        """
        _, filename = os.path.split(self.path)

        filename = applyCustomInputReplacements(filename)

        for cmatcher in self.compiled_regexs:
            match = cmatcher.match(filename)
            if match:
                namedgroups = match.groupdict().keys()

                if 'episodenumber1' in namedgroups:
                    # Multiple episodes, have episodenumber1 or 2 etc
                    epnos = []
                    for cur in namedgroups:
                        epnomatch = re.match('episodenumber(\d+)', cur)
                        if epnomatch:
                            epnos.append(int(match.group(cur)))
                    epnos.sort()
                    episodenumbers = epnos

                elif 'episodenumberstart' in namedgroups:
                    # Multiple episodes, regex specifies start and end number
                    start = int(match.group('episodenumberstart'))
                    end = int(match.group('episodenumberend'))
                    if end - start > 5:
                        warn("WARNING: %s episodes detected in file: %s, confused by numeric episode name, using first match: %s" %(end - start, filename, start))
                        episodenumbers = [start]
                    elif start > end:
                        # Swap start and end
                        start, end = end, start
                        episodenumbers = range(start, end + 1)
                    else:
                        episodenumbers = range(start, end + 1)

                elif 'episodenumber' in namedgroups:
                    episodenumbers = [int(match.group('episodenumber')), ]

                elif 'year' in namedgroups or 'month' in namedgroups or 'day' in namedgroups:
                    if not all(['year' in namedgroups, 'month' in namedgroups, 'day' in namedgroups]):
                        raise ConfigValueError(
                            "Date-based regex must contain groups 'year', 'month' and 'day'")
                    match.group('year')

                    year = handleYear(match.group('year'))

                    episodenumbers = [datetime.date(year,
                                                    int(match.group('month')),
                                                    int(match.group('day')))]

                else:
                    raise ConfigValueError(
                        "Regex does not contain episode number group, should"
                        "contain episodenumber, episodenumber1-9, or"
                        "episodenumberstart and episodenumberend\n\nPattern"
                        "was:\n" + cmatcher.pattern)

                if 'seriesname' in namedgroups:
                    seriesname = match.group('seriesname')
                else:
                    raise ConfigValueError(
                        "Regex must contain seriesname. Pattern was:\n" + cmatcher.pattern)

                if seriesname != None:
                    seriesname = cleanRegexedSeriesName(seriesname)
                    seriesname = replaceInputSeriesName(seriesname)

                extra_values = match.groupdict()

                if 'seasonnumber' in namedgroups:
                    seasonnumber = int(match.group('seasonnumber'))

                    episode = EpisodeInfo(
                        seriesname = seriesname,
                        seasonnumber = seasonnumber,
                        episodenumbers = episodenumbers,
                        filename = self.path,
                        extra = extra_values)
                elif 'year' in namedgroups and 'month' in namedgroups and 'day' in namedgroups:
                    episode = DatedEpisodeInfo(
                        seriesname = seriesname,
                        episodenumbers = episodenumbers,
                        filename = self.path,
                        extra = extra_values)
                elif 'group' in namedgroups:
                    episode = AnimeEpisodeInfo(
                        seriesname = seriesname,
                        episodenumbers = episodenumbers,
                        filename = self.path,
                        extra = extra_values)
                else:
                    # No season number specified, usually for Anime
                    episode = NoSeasonEpisodeInfo(
                        seriesname = seriesname,
                        episodenumbers = episodenumbers,
                        filename = self.path,
                        extra = extra_values)

                return episode
        else:
            emsg = "Cannot parse %r" % self.path
            if len(Config['input_filename_replacements']) > 0:
                emsg += " with replacements: %r" % filename
            raise InvalidFilename(emsg)


def formatEpisodeName(names, join_with, multiep_format):
    """
    Takes a list of episode names, formats them into a string.

    If two names are supplied, such as "Pilot (1)" and "Pilot (2)", the
    returned string will be "Pilot (1-2)". Note that the first number
    is not required, for example passing "Pilot" and "Pilot (2)" will
    also result in returning "Pilot (1-2)".

    If two different episode names are found, such as "The first", and
    "Something else" it will return "The first, Something else"
    """
    if len(names) == 1:
        return names[0]

    found_name = ""
    numbers = []
    for cname in names:
        match = re.match("(.*) \(([0-9]+)\)$", cname)
        if found_name != "" and (not match or epname != found_name):
            # An episode didn't match
            return join_with.join(names)

        if match:
            epname, epno = match.group(1), match.group(2)
        else: # assume that this is the first episode, without number
            epname = cname
            epno = 1
        found_name = epname
        numbers.append(int(epno))

    return multiep_format % {'epname': found_name, 'episodemin': min(numbers), 'episodemax': max(numbers)}


def makeValidFilename(value, normalize_unicode = False, windows_safe = False, custom_blacklist = None, replace_with = "_"):
    """
    Takes a string and makes it into a valid filename.

    normalize_unicode replaces accented characters with ASCII equivalent, and
    removes characters that cannot be converted sensibly to ASCII.

    windows_safe forces Windows-safe filenames, regardless of current platform

    custom_blacklist specifies additional characters that will removed. This
    will not touch the extension separator:

        >>> makeValidFilename("T.est.avi", custom_blacklist=".")
        'T_est.avi'
    """

    if windows_safe:
        # Allow user to make Windows-safe filenames, if they so choose
        sysname = "Windows"
    else:
        sysname = platform.system()

    # If the filename starts with a . prepend it with an underscore, so it
    # doesn't become hidden.

    # This is done before calling splitext to handle filename of ".", as
    # splitext acts differently in python 2.5 and 2.6 - 2.5 returns ('', '.')
    # and 2.6 returns ('.', ''), so rather than special case '.', this
    # special-cases all files starting with "." equally (since dotfiles have
    # no extension)
    if value.startswith("."):
        value = "_" + value

    # Treat extension seperatly
    value, extension = split_extension(value)

    # Remove any null bytes
    value = value.replace("\0", "")

    # Blacklist of characters
    if sysname == 'Darwin':
        # : is technically allowed, but Finder will treat it as / and will
        # generally cause weird behaviour, so treat it as invalid.
        blacklist = r"/:"
    elif sysname in ['Linux', 'FreeBSD']:
        blacklist = r"/"
    else:
        # platform.system docs say it could also return "Windows" or "Java".
        # Failsafe and use Windows sanitisation for Java, as it could be any
        # operating system.
        blacklist = r"\/:*?\"<>|"

    # Append custom blacklisted characters
    if custom_blacklist is not None:
        blacklist += custom_blacklist

    # Replace every blacklisted character with a underscore
    value = re.sub("[%s]" % re.escape(blacklist), replace_with, value)

    # Remove any trailing whitespace
    value = value.strip()

    # There are a bunch of filenames that are not allowed on Windows.
    # As with character blacklist, treat non Darwin/Linux platforms as Windows
    if sysname not in ['Darwin', 'Linux']:
        invalid_filenames = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2",
        "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1",
        "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]
        if value in invalid_filenames:
            value = "_" + value

    # Replace accented characters with ASCII equivalent
    if normalize_unicode:
        import unicodedata
        value = unicode(value) # cast data to unicode
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')

    # Truncate filenames to valid/sane length.
    # NTFS is limited to 255 characters, HFS+ and EXT3 don't seem to have
    # limits, FAT32 is 254. I doubt anyone will take issue with losing that
    # one possible character, and files over 254 are pointlessly unweidly
    max_len = 254

    if len(value + extension) > max_len:
        if len(extension) > len(value):
            # Truncate extension instead of filename, no extension should be
            # this long..
            new_length = max_len - len(value)
            extension = extension[:new_length]
        else:
            # File name is longer than extension, truncate filename.
            new_length = max_len - len(extension)
            value = value[:new_length]

    return value + extension


def formatEpisodeNumbers(episodenumbers):
    """Format episode number(s) into string, using configured values
    """
    if len(episodenumbers) == 1:
        epno = Config['episode_single'] % episodenumbers[0]
    else:
        epno = Config['episode_separator'].join(
            Config['episode_single'] % x for x in episodenumbers)

    return epno


class EpisodeInfo(object):
    """Stores information (season, episode number, episode name), and contains
    logic to generate new name
    """

    CFG_KEY_WITH_EP = "filename_with_episode"
    CFG_KEY_WITHOUT_EP = "filename_without_episode"

    def __init__(self,
        seriesname,
        seasonnumber,
        episodenumbers,
        episodename = None,
        filename = None,
        extra = None):

        self.seriesname = seriesname
        self.seasonnumber = seasonnumber
        self.episodenumbers = episodenumbers
        self.episodename = episodename
        self.fullpath = filename
        if filename is not None:
            # Remains untouched, for use when renaming file
            self.originalfilename = os.path.basename(filename)
        else:
            self.originalfilename = None

        if extra is None:
            extra = {}
        self.extra = extra

    def fullpath_get(self):
        return self._fullpath

    def fullpath_set(self, value):
        self._fullpath = value
        if value is None:
            self.filename, self.extension = None, None
        else:
            self.filepath, self.filename = os.path.split(value)
            self.filename, self.extension = split_extension(self.filename)

    fullpath = property(fullpath_get, fullpath_set)

    @property
    def fullfilename(self):
        return u"%s%s" % (self.filename, self.extension)

    def sortable_info(self):
        """Returns a tuple of sortable information
        """
        return (self.seriesname, self.seasonnumber, self.episodenumbers)

    def number_string(self):
        """Used in UI
        """
        return "season: %s, episode: %s" % (
            self.seasonnumber,
            ", ".join([str(x) for x in self.episodenumbers]))

    def populateFromTvdb(self, tvdb_instance, force_name=None, series_id=None):
        """Queries the tvdb_api.Tvdb instance for episode name and corrected
        series name.
        If series cannot be found, it will warn the user. If the episode is not
        found, it will use the corrected show name and not set an episode name.
        If the site is unreachable, it will warn the user. If the user aborts
        it will catch tvdb_api's user abort error and raise tvnamer's
        """
        try:
            if series_id is None:
                show = tvdb_instance[force_name or self.seriesname]
            else:
                series_id = int(series_id)
                tvdb_instance._getShowData(series_id, Config['language'])
                show = tvdb_instance[series_id]
        except tvdb_error, errormsg:
            raise DataRetrievalError("Error with www.thetvdb.com: %s" % errormsg)
        except tvdb_shownotfound:
            # No such series found.
            raise ShowNotFound("Show %s not found on www.thetvdb.com" % self.seriesname)
        except tvdb_userabort, error:
            raise UserAbort(unicode(error))
        else:
            # Series was found, use corrected series name
            self.seriesname = replaceOutputSeriesName(show['seriesname'])

        if isinstance(self, DatedEpisodeInfo):
            # Date-based episode
            epnames = []
            for cepno in self.episodenumbers:
                try:
                    sr = show.airedOn(cepno)
                    if len(sr) > 1:
                        raise EpisodeNotFound(
                            "Ambigious air date %s, there were %s episodes on that day" % (
                            cepno, len(sr)))
                    epnames.append(sr[0]['episodename'])
                except tvdb_episodenotfound:
                    raise EpisodeNotFound(
                        "Episode that aired on %s could not be found" % (
                        cepno))
            self.episodename = epnames
            return

        if not hasattr(self, "seasonnumber") or self.seasonnumber is None:
            # Series without concept of seasons have all episodes in season 1
            seasonnumber = 1
        else:
            seasonnumber = self.seasonnumber

        epnames = []
        for cepno in self.episodenumbers:
            try:
                episodeinfo = show[seasonnumber][cepno]

            except tvdb_seasonnotfound:
                raise SeasonNotFound(
                    "Season %s of show %s could not be found" % (
                    seasonnumber,
                    self.seriesname))

            except tvdb_episodenotfound:
                # Try to search by absolute_number
                sr = show.search(cepno, "absolute_number")
                if len(sr) > 1:
                    # For multiple results try and make sure there is a direct match
                    unsure = True
                    for e in sr:
                        if int(e['absolute_number']) == cepno:
                            epnames.append(e['episodename'])
                            unsure = False
                    # If unsure error out
                    if unsure:
                        raise EpisodeNotFound(
                            "No episode actually matches %s, found %s results instead" % (cepno, len(sr)))
                elif len(sr) == 1:
                    epnames.append(sr[0]['episodename'])
                else:
                    raise EpisodeNotFound(
                        "Episode %s of show %s, season %s could not be found (also tried searching by absolute episode number)" % (
                            cepno,
                            self.seriesname,
                            seasonnumber))

            except tvdb_attributenotfound:
                raise EpisodeNameNotFound(
                    "Could not find episode name for %s" % cepno)
            else:
                epnames.append(episodeinfo['episodename'])

        self.episodename = epnames

    def getepdata(self):
        """
        Uses the following config options:
        filename_with_episode # Filename when episode name is found
        filename_without_episode # Filename when no episode can be found
        episode_single # formatting for a single episode number
        episode_separator # used to join multiple episode numbers
        """
        # Format episode number into string, or a list
        epno = formatEpisodeNumbers(self.episodenumbers)

        # Data made available to config'd output file format
        if self.extension is None:
            prep_extension = ''
        else:
            prep_extension = self.extension

        epdata = {
            'seriesname': self.seriesname,
            'seasonno': self.seasonnumber, # TODO: deprecated attribute, make this warn somehow
            'seasonnumber': self.seasonnumber,
            'episode': epno,
            'episodename': self.episodename,
            'ext': prep_extension}

        return epdata

    def generateFilename(self, lowercase = False, preview_orig_filename = False):
        epdata = self.getepdata()

        # Add in extra dict keys, without clobbering existing values in epdata
        extra = self.extra.copy()
        extra.update(epdata)
        epdata = extra

        if self.episodename is None:
            fname = Config[self.CFG_KEY_WITHOUT_EP] % epdata
        else:
            if isinstance(self.episodename, list):
                epdata['episodename'] = formatEpisodeName(
                    self.episodename,
                    join_with = Config['multiep_join_name_with'],
                    multiep_format = Config['multiep_format'])
            fname = Config[self.CFG_KEY_WITH_EP] % epdata

        if Config['titlecase_filename']:
            from _titlecase import titlecase
            fname = titlecase(fname)

        if lowercase or Config['lowercase_filename']:
            fname = fname.lower()

        if preview_orig_filename:
            # Return filename without custom replacements or filesystem-validness
            return fname

        if len(Config['output_filename_replacements']) > 0:
            fname = applyCustomOutputReplacements(fname)

        return makeValidFilename(
            fname,
            normalize_unicode = Config['normalize_unicode_filenames'],
            windows_safe = Config['windows_safe_filenames'],
            custom_blacklist = Config['custom_filename_character_blacklist'],
            replace_with = Config['replace_invalid_characters_with'])

    def __repr__(self):
        return u"<%s: %r>" % (
            self.__class__.__name__,
            self.generateFilename())


class DatedEpisodeInfo(EpisodeInfo):
    CFG_KEY_WITH_EP = "filename_with_date_and_episode"
    CFG_KEY_WITHOUT_EP = "filename_with_date_without_episode"

    def __init__(self,
        seriesname,
        episodenumbers,
        episodename = None,
        filename = None,
        extra = None):

        self.seriesname = seriesname
        self.episodenumbers = episodenumbers
        self.episodename = episodename
        self.fullpath = filename

        if filename is not None:
            # Remains untouched, for use when renaming file
            self.originalfilename = os.path.basename(filename)
        else:
            self.originalfilename = None

        if filename is not None:
            # Remains untouched, for use when renaming file
            self.originalfilename = os.path.basename(filename)
        else:
            self.originalfilename = None

        if extra is None:
            extra = {}
        self.extra = extra

    def sortable_info(self):
        """Returns a tuple of sortable information
        """
        return (self.seriesname, self.episodenumbers)

    def number_string(self):
        """Used in UI
        """
        return "episode: %s" % (
            ", ".join([str(x) for x in self.episodenumbers]))

    def getepdata(self):
        # Format episode number into string, or a list
        dates = str(self.episodenumbers[0])
        if isinstance(self.episodename, list):
            prep_episodename = formatEpisodeName(
                self.episodename,
                join_with = Config['multiep_join_name_with'],
                multiep_format = Config['multiep_format'])
        else:
            prep_episodename = self.episodename

        # Data made available to config'd output file format
        if self.extension is None:
            prep_extension = ''
        else:
            prep_extension = self.extension

        epdata = {
            'seriesname': self.seriesname,
            'episode': dates,
            'episodename': prep_episodename,
            'ext': prep_extension}

        return epdata


class NoSeasonEpisodeInfo(EpisodeInfo):
    CFG_KEY_WITH_EP = "filename_with_episode_no_season"
    CFG_KEY_WITHOUT_EP = "filename_without_episode_no_season"

    def __init__(self,
        seriesname,
        episodenumbers,
        episodename = None,
        filename = None,
        extra = None):

        self.seriesname = seriesname
        self.episodenumbers = episodenumbers
        self.episodename = episodename
        self.fullpath = filename

        if filename is not None:
            # Remains untouched, for use when renaming file
            self.originalfilename = os.path.basename(filename)
        else:
            self.originalfilename = None

        if extra is None:
            extra = {}
        self.extra = extra

    def sortable_info(self):
        """Returns a tuple of sortable information
        """
        return (self.seriesname, self.episodenumbers)

    def number_string(self):
        """Used in UI
        """
        return "episode: %s" % (
            ", ".join([str(x) for x in self.episodenumbers]))

    def getepdata(self):
        epno = formatEpisodeNumbers(self.episodenumbers)

        # Data made available to config'd output file format
        if self.extension is None:
            prep_extension = ''
        else:
            prep_extension = self.extension

        epdata = {
            'seriesname': self.seriesname,
            'episode': epno,
            'episodename': self.episodename,
            'ext': prep_extension}

        return epdata


class AnimeEpisodeInfo(NoSeasonEpisodeInfo):
    CFG_KEY_WITH_EP = "filename_anime_with_episode"
    CFG_KEY_WITHOUT_EP = "filename_anime_without_episode"

    CFG_KEY_WITH_EP_NO_CRC = "filename_anime_with_episode_without_crc"
    CFG_KEY_WITHOUT_EP_NO_CRC = "filename_anime_without_episode_without_crc"

    def generateFilename(self, lowercase = False, preview_orig_filename = False):
        epdata = self.getepdata()

        # Add in extra dict keys, without clobbering existing values in epdata
        extra = self.extra.copy()
        extra.update(epdata)
        epdata = extra

        # Get appropriate config key, depending on if episode name was
        # found, and if crc value was found
        if self.episodename is None:
            if self.extra.get('crc') is None:
                cfgkey = self.CFG_KEY_WITHOUT_EP_NO_CRC
            else:
                # Have crc, but no ep name
                cfgkey = self.CFG_KEY_WITHOUT_EP
        else:
            if self.extra.get('crc') is None:
                cfgkey = self.CFG_KEY_WITH_EP_NO_CRC
            else:
                cfgkey = self.CFG_KEY_WITH_EP

        if self.episodename is not None:
            if isinstance(self.episodename, list):
                epdata['episodename'] = formatEpisodeName(
                    self.episodename,
                    join_with = Config['multiep_join_name_with'],
                    multiep_format = Config['multiep_format'])

        fname = Config[cfgkey] % epdata


        if lowercase or Config['lowercase_filename']:
            fname = fname.lower()

        if preview_orig_filename:
            # Return filename without custom replacements or filesystem-validness
            return fname

        if len(Config['output_filename_replacements']) > 0:
            fname = applyCustomOutputReplacements(fname)

        return makeValidFilename(
            fname,
            normalize_unicode = Config['normalize_unicode_filenames'],
            windows_safe = Config['windows_safe_filenames'],
            custom_blacklist = Config['custom_filename_character_blacklist'],
            replace_with = Config['replace_invalid_characters_with'])


def same_partition(f1, f2):
    """Returns True if both files or directories are on the same partition
    """
    return os.stat(f1).st_dev == os.stat(f2).st_dev


def delete_file(fpath):
    """On OS X: Trashes a path using the Finder, via OS X's Scripting Bridge.

    On other platforms: unlinks file.
    """

    try:
        from AppKit import NSURL
        from ScriptingBridge import SBApplication
    except ImportError:
        log().debug("Deleting %r" % fpath)
        os.unlink(fpath)
    else:
        log().debug("Trashing %r" % fpath)
        targetfile = NSURL.fileURLWithPath_(fpath)
        finder = SBApplication.applicationWithBundleIdentifier_("com.apple.Finder")
        items = finder.items().objectAtLocation_(targetfile)
        items.delete()


def rename_file(old, new):
    p("rename %s to %s" % (old, new))
    stat = os.stat(old)
    os.rename(old, new)
    try:
        os.utime(new, (stat.st_atime, stat.st_mtime))
    except OSError, ex:
        if ex.errno == errno.EPERM:
            warn("WARNING: Could not preserve times for %s "
                 "(owner UID mismatch?)" % new)
        else:
            raise

def copy_file(old, new):
    p("copy %s to %s" % (old, new))
    shutil.copyfile(old, new)
    shutil.copystat(old, new)


def symlink_file(target, name):
    p("symlink %s to %s" % (name, target))
    os.symlink(target, name)


class Renamer(object):
    """Deals with renaming of files
    """

    def __init__(self, filename):
        self.filename = os.path.abspath(filename)

    def newPath(self, new_path = None, new_fullpath = None, force = False, always_copy = False, always_move = False, leave_symlink = False, create_dirs = True, getPathPreview = False):
        """Moves the file to a new path.

        If it is on the same partition, it will be moved (unless always_copy is True)
        If it is on a different partition, it will be copied, and the original
        only deleted if always_move is True.
        If the target file already exists, it will raise OSError unless force is True.
        If it was moved, a symlink will be left behind with the original name
        pointing to the file's new destination if leave_symlink is True.
        """

        if always_copy and always_move:
            raise ValueError("Both always_copy and always_move cannot be specified")

        if (new_path is None and new_fullpath is None) or (new_path is not None and new_fullpath is not None):
            raise ValueError("Specify only new_dir or new_fullpath")

        old_dir, old_filename = os.path.split(self.filename)
        if new_path is not None:
            # Join new filepath to old one (to handle realtive dirs)
            new_dir = os.path.abspath(os.path.join(old_dir, new_path))

            # Join new filename onto new filepath
            new_fullpath = os.path.join(new_dir, old_filename)

        else:
            # Join new filepath to old one (to handle realtive dirs)
            new_fullpath = os.path.abspath(os.path.join(old_dir, new_fullpath))

            new_dir = os.path.dirname(new_fullpath)


        if len(Config['move_files_fullpath_replacements']) > 0:
            p("Before custom full path replacements: %s" % (new_fullpath))
            new_fullpath = applyCustomFullpathReplacements(new_fullpath)
            new_dir = os.path.dirname(new_fullpath)

        p("New path: %s" % new_fullpath)

        if getPathPreview:
            return new_fullpath

        if create_dirs:
            try:
                os.makedirs(new_dir)
            except OSError, e:
                if e.errno != 17:
                    raise
            else:
                p("Created directory %s" % new_dir)


        if os.path.isfile(new_fullpath):
            # If the destination exists, raise exception unless force is True
            if not force:
                raise OSError("File %s already exists, not forcefully moving %s" % (
                    new_fullpath, self.filename))

        if same_partition(self.filename, new_dir):
            if always_copy:
                # Same partition, but forced to copy
                copy_file(self.filename, new_fullpath)
            else:
                # Same partition, just rename the file to move it
                rename_file(self.filename, new_fullpath)

                # Leave a symlink behind if configured to do so
                if leave_symlink:
                    symlink_file(new_fullpath, self.filename)
        else:
            # File is on different partition (different disc), copy it
            copy_file(self.filename, new_fullpath)
            if always_move:
                # Forced to move file, we just trash old file
                p("Deleting %s" % (self.filename))
                delete_file(self.filename)

                # Leave a symlink behind if configured to do so
                if leave_symlink:
                    symlink_file(new_fullpath, self.filename)

        self.filename = new_fullpath

########NEW FILE########
__FILENAME__ = _titlecase
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Original Perl version by: John Gruber http://daringfireball.net/ 10 May 2008
Python version by Stuart Colville http://muffinresearch.co.uk
License: http://www.opensource.org/licenses/mit-license.php
"""

import re

__all__ = ['titlecase']
__version__ = '0.5.2'

SMALL = 'a|an|and|as|at|but|by|en|for|if|in|of|on|or|the|to|v\.?|via|vs\.?'
PUNCT = r"""!"#$%&'‘()*+,\-./:;?@[\\\]_`{|}~"""

SMALL_WORDS = re.compile(r'^(%s)$' % SMALL, re.I)
INLINE_PERIOD = re.compile(r'[a-z][.][a-z]', re.I)
UC_ELSEWHERE = re.compile(r'[%s]*?[a-zA-Z]+[A-Z]+?' % PUNCT)
CAPFIRST = re.compile(r"^[%s]*?([A-Za-z])" % PUNCT)
SMALL_FIRST = re.compile(r'^([%s]*)(%s)\b' % (PUNCT, SMALL), re.I)
SMALL_LAST = re.compile(r'\b(%s)[%s]?$' % (SMALL, PUNCT), re.I)
SUBPHRASE = re.compile(r'([:.;?!][ ])(%s)' % SMALL)
APOS_SECOND = re.compile(r"^[dol]{1}['‘]{1}[a-z]+$", re.I)
ALL_CAPS = re.compile(r'^[A-Z\s%s]+$' % PUNCT)
UC_INITIALS = re.compile(r"^(?:[A-Z]{1}\.{1}|[A-Z]{1}\.{1}[A-Z]{1})+$")
MAC_MC = re.compile(r"^([Mm]a?c)(\w+)")


def titlecase(text):
    """
    Titlecases input text

    This filter changes all words to Title Caps, and attempts to be clever
    about *un*capitalizing SMALL words like a/an/the in the input.

    The list of "SMALL words" which are not capped comes from
    the New York Times Manual of Style, plus 'vs' and 'v'.

    """

    lines = re.split('[\r\n]+', text)
    processed = []
    for line in lines:
        all_caps = ALL_CAPS.match(line)
        words = re.split('[\t ]', line)
        tc_line = []
        for word in words:
            if all_caps:
                if UC_INITIALS.match(word):
                    tc_line.append(word)
                    continue
                else:
                    word = word.lower()

            if APOS_SECOND.match(word):
                word = word.replace(word[0], word[0].upper())
                word = word.replace(word[2], word[2].upper())
                tc_line.append(word)
                continue
            if INLINE_PERIOD.search(word) or UC_ELSEWHERE.match(word):
                tc_line.append(word)
                continue
            if SMALL_WORDS.match(word):
                tc_line.append(word.lower())
                continue

            match = MAC_MC.match(word)
            if match:
                tc_line.append("%s%s" % (match.group(1).capitalize(),
                                      match.group(2).capitalize()))
                continue

            if "/" in word and not "//" in word:
                slashed = []
                for item in word.split('/'):
                    slashed.append(CAPFIRST.sub(lambda m: m.group(0).upper(), item))
                tc_line.append("/".join(slashed))
                continue

            hyphenated = []
            for item in word.split('-'):
                hyphenated.append(CAPFIRST.sub(lambda m: m.group(0).upper(), item))
            tc_line.append("-".join(hyphenated))

        result = " ".join(tc_line)

        result = SMALL_FIRST.sub(lambda m: '%s%s' % (
            m.group(1),
            m.group(2).capitalize()
        ), result)

        result = SMALL_LAST.sub(lambda m: m.group(0).capitalize(), result)

        result = SUBPHRASE.sub(lambda m: '%s%s' % (
            m.group(1),
            m.group(2).capitalize()
        ), result)

        processed.append(result)

    return "\n".join(processed)

########NEW FILE########
