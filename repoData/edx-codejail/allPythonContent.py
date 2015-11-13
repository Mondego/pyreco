__FILENAME__ = django_integration
"""Django integration for codejail.

Code to glue codejail into a Django environment.

"""

from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings

import codejail.jail_code


class ConfigureCodeJailMiddleware(object):
    """
    Middleware to configure codejail on startup.

    This is a Django idiom to have code run once on server startup: put the
    code in the `__init__` of some middleware, and have it do the work, then
    raise `MiddlewareNotUsed` to disable the middleware.

    """
    def __init__(self):
        python_bin = settings.CODE_JAIL.get('python_bin')
        if python_bin:
            user = settings.CODE_JAIL['user']
            codejail.jail_code.configure("python", python_bin, user=user)
        limits = settings.CODE_JAIL.get('limits', {})
        for name, value in limits.items():
            codejail.jail_code.set_limit(name, value)
        raise MiddlewareNotUsed

########NEW FILE########
__FILENAME__ = jail_code
"""Run code in a jail."""

import logging
import os
import os.path
import resource
import shutil
import subprocess
import sys
import threading
import time

from .util import temp_directory

log = logging.getLogger(__name__)

# TODO: limit too much stdout data?

# Configure the commands

# COMMANDS is a map from an abstract command name to a list of command-line
# pieces, such as subprocess.Popen wants.
COMMANDS = {}


def configure(command, bin_path, user=None):
    """
    Configure a command for `jail_code` to use.

    `command` is the abstract command you're configuring, such as "python" or
    "node".  `bin_path` is the path to the binary.  `user`, if provided, is
    the user name to run the command under.

    """
    cmd_argv = [bin_path]

    # Command-specific arguments
    if command == "python":
        # -E means ignore the environment variables PYTHON*
        # -B means don't try to write .pyc files.
        cmd_argv.extend(['-E', '-B'])

    COMMANDS[command] = {
        # The start of the command line for this program.
        'cmdline_start': cmd_argv,
        # The user to run this as, perhaps None.
        'user': user,
    }


def is_configured(command):
    """
    Has `jail_code` been configured for `command`?

    Returns true if the abstract command `command` has been configured for use
    in the `jail_code` function.

    """
    return command in COMMANDS

# By default, look where our current Python is, and maybe there's a
# python-sandbox alongside.  Only do this if running in a virtualenv.
if hasattr(sys, 'real_prefix'):
    if os.path.isdir(sys.prefix + "-sandbox"):
        configure("python", sys.prefix + "-sandbox/bin/python", "sandbox")


# Configurable limits

LIMITS = {
    # CPU seconds, defaulting to 1.
    "CPU": 1,
    # Real time, defaulting to 1 second.
    "REALTIME": 1,
    # Total process virutal memory, in bytes, defaulting to unlimited.
    "VMEM": 0,
    # Size of files creatable, in bytes, defaulting to nothing can be written.
    "FSIZE": 0,
}


def set_limit(limit_name, value):
    """
    Set a limit for `jail_code`.

    `limit_name` is a string, the name of the limit to set. `value` is the
    value to use for that limit.  The type, meaning, default, and range of
    accepted values depend on `limit_name`.

    These limits are available:

        * `"CPU"`: the maximum number of CPU seconds the jailed code can use.
            The value is an integer, defaulting to 1.

        * `"REALTIME"`: the maximum number of seconds the jailed code can run,
            in real time.  The default is 1 second.

        * `"VMEM"`: the total virtual memory available to the jailed code, in
            bytes.  The default is 0 (no memory limit).

        * `"FSIZE"`: the maximum size of files creatable by the jailed code,
            in bytes.  The default is 0 (no files may be created).

    Limits are process-wide, and will affect all future calls to jail_code.
    Providing a limit of 0 will disable that limit.

    """
    LIMITS[limit_name] = value


class JailResult(object):
    """
    A passive object for us to return from jail_code.
    """
    def __init__(self):
        self.stdout = self.stderr = self.status = None


def jail_code(command, code=None, files=None, extra_files=None, argv=None,
              stdin=None, slug=None):
    """
    Run code in a jailed subprocess.

    `command` is an abstract command ("python", "node", ...) that must have
    been configured using `configure`.

    `code` is a string containing the code to run.  If no code is supplied,
    then the code to run must be in one of the `files` copied, and must be
    named in the `argv` list.

    `files` is a list of file paths, they are all copied to the jailed
    directory.  Note that no check is made here that the files don't contain
    sensitive information.  The caller must somehow determine whether to allow
    the code access to the files.  Symlinks will be copied as symlinks.  If the
    linked-to file is not accessible to the sandbox, the symlink will be
    unreadable as well.

    `extra_files` is a list of pairs, each pair is a filename and a bytestring
    of contents to write into that file.  These files will be created in the
    temp directory and cleaned up automatically.  No subdirectories are
    supported in the filename.

    `argv` is the command-line arguments to supply.

    `stdin` is a string, the data to provide as the stdin for the process.

    `slug` is an arbitrary string, a description that's meaningful to the
    caller, that will be used in log messages.

    Return an object with:

        .stdout: stdout of the program, a string
        .stderr: stderr of the program, a string
        .status: exit status of the process: an int, 0 for success

    """
    if not is_configured(command):
        raise Exception("jail_code needs to be configured for %r" % command)

    # We make a temp directory to serve as the home of the sandboxed code.
    # It has a writable "tmp" directory within it for temp files.

    with temp_directory() as homedir:

        # Make directory readable by other users ('sandbox' user needs to be
        # able to read it).
        os.chmod(homedir, 0775)

        # Make a subdir to use for temp files, world-writable so that the
        # sandbox user can write to it.
        tmptmp = os.path.join(homedir, "tmp")
        os.mkdir(tmptmp)
        os.chmod(tmptmp, 0777)

        argv = argv or []

        # All the supporting files are copied into our directory.
        for filename in files or ():
            dest = os.path.join(homedir, os.path.basename(filename))
            if os.path.islink(filename):
                os.symlink(os.readlink(filename), dest)
            elif os.path.isfile(filename):
                shutil.copy(filename, homedir)
            else:
                shutil.copytree(filename, dest, symlinks=True)

        # Create the main file.
        if code:
            with open(os.path.join(homedir, "jailed_code"), "wb") as jailed:
                jailed.write(code)

            argv = ["jailed_code"] + argv

        # Create extra files requested by the caller:
        for name, content in extra_files or ():
            with open(os.path.join(homedir, name), "wb") as extra:
                extra.write(content)

        cmd = []

        # Build the command to run.
        user = COMMANDS[command]['user']
        if user:
            # Run as the specified user
            cmd.extend(['sudo', '-u', user])

        # Point TMPDIR at our temp directory.
        cmd.extend(['TMPDIR=tmp'])
        # Start with the command line dictated by "python" or whatever.
        cmd.extend(COMMANDS[command]['cmdline_start'])
        # Add the code-specific command line pieces.
        cmd.extend(argv)

        # Run the subprocess.
        subproc = subprocess.Popen(
            cmd, preexec_fn=set_process_limits, cwd=homedir, env={},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        if slug:
            log.info("Executing jailed code %s in %s, with PID %s", slug, homedir, subproc.pid)

        # Start the time killer thread.
        realtime = LIMITS["REALTIME"]
        if realtime:
            killer = ProcessKillerThread(subproc, limit=realtime)
            killer.start()

        result = JailResult()
        result.stdout, result.stderr = subproc.communicate(stdin)
        result.status = subproc.returncode

    return result


def set_process_limits():       # pragma: no cover
    """
    Set limits on this process, to be used first in a child process.
    """
    # Set a new session id so that this process and all its children will be
    # in a new process group, so we can kill them all later if we need to.
    os.setsid()

    # No subprocesses.
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))

    # CPU seconds, not wall clock time.
    cpu = LIMITS["CPU"]
    if cpu:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))

    # Total process virtual memory.
    vmem = LIMITS["VMEM"]
    if vmem:
        resource.setrlimit(resource.RLIMIT_AS, (vmem, vmem))

    # Size of written files.  Can be zero (nothing can be written).
    fsize = LIMITS["FSIZE"]
    resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))


class ProcessKillerThread(threading.Thread):
    """
    A thread to kill a process after a given time limit.
    """
    def __init__(self, subproc, limit):
        super(ProcessKillerThread, self).__init__()
        self.subproc = subproc
        self.limit = limit

    def run(self):
        start = time.time()
        while (time.time() - start) < self.limit:
            time.sleep(.25)
            if self.subproc.poll() is not None:
                # Process ended, no need for us any more.
                return

        if self.subproc.poll() is None:
            # Can't use subproc.kill because we launched the subproc with sudo.
            pgid = os.getpgid(self.subproc.pid)
            log.warning(
                "Killing process %r (group %r), ran too long: %.1fs",
                self.subproc.pid, pgid, time.time() - start
            )
            subprocess.call(["sudo", "pkill", "-9", "-g", str(pgid)])

########NEW FILE########
__FILENAME__ = safe_exec
"""Safe execution of untrusted Python code."""

import logging
import os.path
import shutil
import sys
import textwrap

try:
    import simplejson as json
except ImportError:
    import json

from codejail import jail_code
from codejail.util import temp_directory, change_directory

log = logging.getLogger(__name__)


# Flags to let developers temporarily change some behavior in this file.

# Set this to True to log all the code and globals being executed.
LOG_ALL_CODE = False
# Set this to True to use the unsafe code, so that you can debug it.
ALWAYS_BE_UNSAFE = False


class SafeExecException(Exception):
    """
    Python code running in the sandbox has failed.

    The message will be the stdout of the sandboxed process, which will usually
    contain the original exception message.

    """
    pass


def safe_exec(code, globals_dict, files=None, python_path=None, slug=None):
    """
    Execute code as "exec" does, but safely.

    `code` is a string of Python code.  `globals_dict` is used as the globals
    during execution.  Modifications the code makes to `globals_dict` are
    reflected in the dictionary on return.

    `files` is a list of file paths, either files or directories.  They will be
    copied into the temp directory used for execution.  No attempt is made to
    determine whether the file is appropriate or safe to copy.  The caller must
    determine which files to provide to the code.

    `python_path` is a list of directory paths.  They will be copied just as
    `files` are, but will also be added to `sys.path` so that modules there can
    be imported.

    `slug` is an arbitrary string, a description that's meaningful to the
    caller, that will be used in log messages.

    Returns None.  Changes made by `code` are visible in `globals_dict`.  If
    the code raises an exception, this function will raise `SafeExecException`
    with the stderr of the sandbox process, which usually includes the original
    exception message and traceback.

    """
    the_code = []
    files = list(files or ())

    the_code.append(textwrap.dedent(
        """
        import sys
        try:
            import simplejson as json
        except ImportError:
            import json
        """
        # We need to prevent the sandboxed code from printing to stdout,
        # or it will pollute the json we print there.  This isn't a
        # security concern (they can put any values in the json output
        # anyway, either by writing to sys.__stdout__, or just by defining
        # global values), but keeps accidents from happening.
        """
        class DevNull(object):
            def write(self, *args, **kwargs):
                pass
        sys.stdout = DevNull()
        """
        # Read the code and the globals from the stdin.
        """
        code, g_dict = json.load(sys.stdin)
        """))

    for pydir in python_path or ():
        pybase = os.path.basename(pydir)
        the_code.append("sys.path.append(%r)\n" % pybase)
        files.append(pydir)

    the_code.append(textwrap.dedent(
        # Execute the sandboxed code.
        """
        exec code in g_dict
        """
        # Clean the globals for sending back as JSON over stdout.
        """
        ok_types = (
            type(None), int, long, float, str, unicode, list, tuple, dict
        )
        bad_keys = ("__builtins__",)
        def jsonable(v):
            if not isinstance(v, ok_types):
                return False
            try:
                json.dumps(v)
            except Exception:
                return False
            return True
        g_dict = {
            k:v
            for k,v in g_dict.iteritems()
            if jsonable(v) and k not in bad_keys
        }
        """
        # Write the globals back to the calling process.
        """
        json.dump(g_dict, sys.__stdout__)
        """))

    stdin = json.dumps([code, json_safe(globals_dict)])
    jailed_code = "".join(the_code)

    # Turn this on to see what's being executed.
    if LOG_ALL_CODE:        # pragma: no cover
        log.debug("Jailed code: %s", jailed_code)
        log.debug("Exec: %s", code)
        log.debug("Stdin: %s", stdin)

    res = jail_code.jail_code(
        "python", code=jailed_code, stdin=stdin, files=files, slug=slug,
    )
    if res.status != 0:
        raise SafeExecException(
            "Couldn't execute jailed code: %s" % res.stderr
        )
    globals_dict.update(json.loads(res.stdout))


def json_safe(d):
    """
    Return only the JSON-safe part of d.

    Used to emulate reading data through a serialization straw.

    """
    ok_types = (type(None), int, long, float, str, unicode, list, tuple, dict)
    bad_keys = ("__builtins__",)
    jd = {}
    for k, v in d.iteritems():
        if not isinstance(v, ok_types):
            continue
        if k in bad_keys:
            continue
        try:
            # Python's JSON encoder will produce output that
            # the JSON decoder cannot parse if the input string
            # contains unicode "unpaired surrogates" (only on Linux)
            # To test for this, we try decoding the output and check
            # for a ValueError
            json.loads(json.dumps(v))

            # Also ensure that the keys encode/decode correctly
            json.loads(json.dumps(k))
        except (TypeError, ValueError):
            continue
        else:
            jd[k] = v
    return json.loads(json.dumps(jd))


def not_safe_exec(code, globals_dict, files=None, python_path=None, slug=None):
    """
    Another implementation of `safe_exec`, but not safe.

    This can be swapped in for debugging problems in sandboxed Python code.

    This is not thread-safe, due to temporarily changing the current directory
    and modifying sys.path.

    """
    g_dict = json_safe(globals_dict)

    with temp_directory() as tmpdir:
        with change_directory(tmpdir):
            # Copy the files here.
            for filename in files or ():
                dest = os.path.join(tmpdir, os.path.basename(filename))
                shutil.copyfile(filename, dest)

            original_path = sys.path
            if python_path:
                sys.path.extend(python_path)
            try:
                exec code in g_dict
            except Exception as e:
                # Wrap the exception in a SafeExecException, but we don't
                # try here to include the traceback, since this is just a
                # substitute implementation.
                msg = "{0.__class__.__name__}: {0!s}".format(e)
                raise SafeExecException(msg)
            finally:
                sys.path = original_path

    globals_dict.update(json_safe(g_dict))


# If the developer wants us to be unsafe (ALWAYS_BE_UNSAFE), or if there isn't
# a configured jail for Python, then we'll be UNSAFE.
UNSAFE = ALWAYS_BE_UNSAFE or not jail_code.is_configured("python")

if UNSAFE:   # pragma: no cover
    # Make safe_exec actually call not_safe_exec, but log that we're doing so.

    def safe_exec(*args, **kwargs):                 # pylint: disable=E0102
        """An actually-unsafe safe_exec, that warns it's being used."""

        # Because it would be bad if this function were used in production,
        # let's log a warning when it is used.  Developers can live with
        # one more log line.
        slug = kwargs.get('slug', None)
        log.warning("Using codejail/safe_exec.py:not_safe_exec for %s", slug)

        return not_safe_exec(*args, **kwargs)

########NEW FILE########
__FILENAME__ = doit
import sys

print "This is doit.py!"
print "My args are %r" % (sys.argv,)

########NEW FILE########
__FILENAME__ = module
const = 42

########NEW FILE########
__FILENAME__ = test_jail_code
"""Test jail_code.py"""

import os
import os.path
import shutil
import textwrap
import tempfile
import unittest

from nose.plugins.skip import SkipTest

from codejail.jail_code import jail_code, is_configured, set_limit, LIMITS


def jailpy(code=None, *args, **kwargs):
    """Run `jail_code` on Python."""
    if code:
        code = textwrap.dedent(code)
    return jail_code("python", code, *args, **kwargs)


def file_here(fname):
    """Return the full path to a file alongside this code."""
    return os.path.join(os.path.dirname(__file__), fname)


class JailCodeHelpers(object):
    """Assert helpers for jail_code tests."""
    def setUp(self):
        super(JailCodeHelpers, self).setUp()
        if not is_configured("python"):
            raise SkipTest

    def assertResultOk(self, res):
        """Assert that `res` exited well (0), and had no stderr output."""
        if res.stderr:
            print "---- stderr:\n%s" % res.stderr
        self.assertEqual(res.stderr, "")        # pylint: disable=E1101
        self.assertEqual(res.status, 0)         # pylint: disable=E1101


class TestFeatures(JailCodeHelpers, unittest.TestCase):
    """Test features of how `jail_code` runs Python."""

    def test_hello_world(self):
        res = jailpy(code="print 'Hello, world!'")
        self.assertResultOk(res)
        self.assertEqual(res.stdout, 'Hello, world!\n')

    def test_argv(self):
        res = jailpy(
            code="import sys; print ':'.join(sys.argv[1:])",
            argv=["Hello", "world", "-x"],
            slug="a/useful/slug",
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, "Hello:world:-x\n")

    def test_ends_with_exception(self):
        res = jailpy(code="""raise Exception('FAIL')""")
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "")
        self.assertEqual(res.stderr, textwrap.dedent("""\
            Traceback (most recent call last):
              File "jailed_code", line 1, in <module>
                raise Exception('FAIL')
            Exception: FAIL
            """))

    def test_stdin_is_provided(self):
        res = jailpy(
            code="import json,sys; print sum(json.load(sys.stdin))",
            stdin="[1, 2.5, 33]"
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, "36.5\n")

    def test_files_are_copied(self):
        res = jailpy(
            code="print 'Look:', open('hello.txt').read()",
            files=[file_here("hello.txt")]
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, 'Look: Hello there.\n\n')

    def test_directories_are_copied(self):
        res = jailpy(
            code="""\
                import os
                res = []
                for path, dirs, files in os.walk("."):
                    res.append((path, sorted(dirs), sorted(files)))
                for row in sorted(res):
                    print row
                """,
            files=[file_here("hello.txt"), file_here("pylib")]
        )
        self.assertResultOk(res)
        self.assertEqual(res.stdout, textwrap.dedent("""\
            ('.', ['pylib', 'tmp'], ['hello.txt', 'jailed_code'])
            ('./pylib', [], ['module.py', 'module.pyc'])
            ('./tmp', [], [])
            """))

    def test_executing_a_copied_file(self):
        res = jailpy(
            files=[file_here("doit.py")],
            argv=["doit.py", "1", "2", "3"]
        )
        self.assertResultOk(res)
        self.assertEqual(
            res.stdout,
            "This is doit.py!\nMy args are ['doit.py', '1', '2', '3']\n"
        )

    def test_executing_extra_files(self):
        res = jailpy(
            extra_files=[
                ("run.py", textwrap.dedent("""\
                            import os
                            print os.listdir('.')
                            print open('also.txt').read()
                            """)),
                # This file has some non-ASCII, non-UTF8, just binary data.
                ("also.txt", "also here\xff\x00\xab"),
            ],
            argv=["run.py"],
        )
        self.assertResultOk(res)
        self.assertEqual(
            res.stdout,
            "['tmp', 'also.txt', 'run.py']\nalso here\xff\x00\xab\n"
        )


class TestLimits(JailCodeHelpers, unittest.TestCase):
    """Tests of the resource limits, and changing them."""

    def setUp(self):
        super(TestLimits, self).setUp()
        self.old_limits = dict(LIMITS)

    def tearDown(self):
        for name, value in self.old_limits.items():
            set_limit(name, value)
        super(TestLimits, self).tearDown()

    def test_cant_use_too_much_memory(self):
        # This will fail after setting the limit to 30Mb.
        set_limit('VMEM', 30000000)
        res = jailpy(code="print len(bytearray(40000000))")
        self.assertEqual(res.stdout, "")
        self.assertNotEqual(res.status, 0)

    def test_changing_vmem_limit(self):
        # Up the limit, it will succeed.
        set_limit('VMEM', 80000000)
        res = jailpy(code="print len(bytearray(40000000))")
        self.assertEqual(res.stderr, "")
        self.assertEqual(res.stdout, "40000000\n")
        self.assertEqual(res.status, 0)

    def test_disabling_vmem_limit(self):
        # Disable the limit, it will succeed.
        set_limit('VMEM', 0)
        res = jailpy(code="print len(bytearray(50000000))")
        self.assertEqual(res.stderr, "")
        self.assertEqual(res.stdout, "50000000\n")
        self.assertEqual(res.status, 0)

    def test_cant_use_too_much_cpu(self):
        res = jailpy(code="print sum(xrange(2**31-1))")
        self.assertEqual(res.stdout, "")
        self.assertNotEqual(res.status, 0)

    def test_cant_use_too_much_time(self):
        # Default time limit is 1 second.  Sleep for 1.5 seconds.
        res = jailpy(code="import time; time.sleep(1.5); print 'Done!'")
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "")

    def test_changing_realtime_limit(self):
        # Change time limit to 2 seconds, sleeping for 1.5 will be fine.
        set_limit('REALTIME', 2)
        res = jailpy(code="import time; time.sleep(1.5); print 'Done!'")
        self.assertResultOk(res)
        self.assertEqual(res.stdout, "Done!\n")

    def test_disabling_realtime_limit(self):
        # Disable the time limit, sleeping for 1.5 will be fine.
        set_limit('REALTIME', 0)
        res = jailpy(code="import time; time.sleep(1.5); print 'Done!'")
        self.assertResultOk(res)
        self.assertEqual(res.stdout, "Done!\n")

    def test_cant_write_files(self):
        res = jailpy(code="""\
                print "Trying"
                with open("mydata.txt", "w") as f:
                    f.write("hello")
                with open("mydata.txt") as f2:
                    print "Got this:", f2.read()
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "Trying\n")
        self.assertIn("ermission denied", res.stderr)

    def test_can_write_temp_files(self):
        set_limit('FSIZE', 1000)
        res = jailpy(code="""\
                import os, tempfile
                print "Trying mkstemp"
                f, path = tempfile.mkstemp()
                os.close(f)
                with open(path, "w") as f1:
                    f1.write("hello")
                with open(path) as f2:
                    print "Got this:", f2.read()
                """)
        self.assertResultOk(res)
        self.assertEqual(res.stdout, "Trying mkstemp\nGot this: hello\n")

    def test_cant_write_large_temp_files(self):
        set_limit('FSIZE', 1000)
        res = jailpy(code="""\
                import os, tempfile
                print "Trying mkstemp"
                f, path = tempfile.mkstemp()
                os.close(f)
                with open(path, "w") as f1:
                    try:
                        f1.write(".".join("%05d" % i for i in xrange(1000)))
                    except IOError as e:
                        print "Expected exception: %s" % e
                    else:
                        with open(path) as f2:
                            print "Got this:", f2.read()
                """)
        self.assertResultOk(res)
        self.assertIn("Expected exception", res.stdout)

    def test_cant_write_many_small_temp_files(self):
        # We would like this to fail, but there's nothing that checks total
        # file size written, so the sandbox does not prevent it yet.
        raise SkipTest("There's nothing checking total file size yet.")
        set_limit('FSIZE', 1000)
        res = jailpy(code="""\
                import os, tempfile
                print "Trying mkstemp 250"
                for i in range(250):
                    f, path = tempfile.mkstemp()
                    os.close(f)
                    with open(path, "w") as f1:
                        f1.write("hello")
                    with open(path) as f2:
                        assert f2.read() == "hello"
                print "Finished 250"
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "Trying mkstemp 250\n")
        self.assertIn("IOError", res.stderr)

    def test_cant_use_network(self):
        res = jailpy(code="""\
                import urllib
                print "Reading google"
                u = urllib.urlopen("http://google.com")
                google = u.read()
                print len(google)
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "Reading google\n")
        self.assertIn("IOError", res.stderr)

    def test_cant_use_raw_network(self):
        res = jailpy(code="""\
                import urllib
                print "Reading example.com"
                u = urllib.urlopen("http://93.184.216.119")
                example = u.read()
                print len(example)
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "Reading example.com\n")
        self.assertIn("IOError", res.stderr)

    def test_cant_fork(self):
        res = jailpy(code="""\
                import os
                print "Forking"
                child_ppid = os.fork()
                """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "Forking\n")
        self.assertIn("OSError", res.stderr)

    def test_cant_see_environment_variables(self):
        os.environ['HONEY_BOO_BOO'] = 'Look!'
        res = jailpy(code="""\
                import os
                for name, value in os.environ.items():
                    print "%s: %r" % (name, value)
                """)
        self.assertResultOk(res)
        self.assertNotIn("HONEY", res.stdout)

    def test_reading_dev_random(self):
        # We can read 10 bytes just fine.
        res = jailpy(code="x = open('/dev/random').read(10); print len(x)")
        self.assertResultOk(res)
        self.assertEqual(res.stdout, "10\n")

        # If we try to read all of it, we'll be killed by the real-time limit.
        res = jailpy(code="x = open('/dev/random').read(); print 'Done!'")
        self.assertNotEqual(res.status, 0)


class TestSymlinks(JailCodeHelpers, unittest.TestCase):
    """Testing symlink behavior."""

    def setUp(self):
        # Make a temp dir, and arrange to have it removed when done.
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir)

        # Make a directory that won't be copied into the sandbox.
        self.not_copied = os.path.join(tmp_dir, "not_copied")
        os.mkdir(self.not_copied)
        self.linked_txt = os.path.join(self.not_copied, "linked.txt")
        with open(self.linked_txt, "w") as linked:
            linked.write("Hi!")

        # Make a directory that will be copied into the sandbox, with a
        # symlink to a file we aren't copying in.
        self.copied = os.path.join(tmp_dir, "copied")
        os.mkdir(self.copied)
        self.here_txt = os.path.join(self.copied, "here.txt")
        with open(self.here_txt, "w") as here:
            here.write("012345")
        self.link_txt = os.path.join(self.copied, "link.txt")
        os.symlink(self.linked_txt, self.link_txt)
        self.herelink_txt = os.path.join(self.copied, "herelink.txt")
        os.symlink("here.txt", self.herelink_txt)

    def test_symlinks_in_directories_wont_copy_data(self):
        # Run some code in the sandbox, with a copied directory containing
        # the symlink.
        res = jailpy(
            code="""\
                print open('copied/here.txt').read()        # can read
                print open('copied/herelink.txt').read()    # can read
                print open('copied/link.txt').read()        # can't read
                """,
            files=[self.copied],
        )
        self.assertEqual(res.stdout, "012345\n012345\n")
        self.assertIn("ermission denied", res.stderr)

    def test_symlinks_wont_copy_data(self):
        # Run some code in the sandbox, with a copied file which is a symlink.
        res = jailpy(
            code="""\
                print open('here.txt').read()       # can read
                print open('herelink.txt').read()   # can read
                print open('link.txt').read()       # can't read
                """,
            files=[self.here_txt, self.herelink_txt, self.link_txt],
        )
        self.assertEqual(res.stdout, "012345\n012345\n")
        self.assertIn("ermission denied", res.stderr)


class TestMalware(JailCodeHelpers, unittest.TestCase):
    """Tests that attempt actual malware against the interpreter or system."""

    def test_crash_cpython(self):
        # http://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        res = jailpy(code="""\
            import new, sys
            bad_code = new.code(0,0,0,0,"KABOOM",(),(),(),"","",0,"")
            crash_me = new.function(bad_code, {})
            print "Here we go..."
            sys.stdout.flush()
            crash_me()
            print "The afterlife!"
            """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "Here we go...\n")
        self.assertEqual(res.stderr, "")

    def test_read_etc_passwd(self):
        res = jailpy(code="""\
            bytes = len(open('/etc/passwd').read())
            print 'Gotcha', bytes
            """)
        self.assertNotEqual(res.status, 0)
        self.assertEqual(res.stdout, "")
        self.assertIn("ermission denied", res.stderr)

    def test_find_other_sandboxes(self):
        res = jailpy(code="""
            import os
            places = [
                "..", "/tmp", "/", "/home", "/etc", "/var"
                ]
            for place in places:
                try:
                    files = os.listdir(place)
                except Exception:
                    # darn
                    pass
                else:
                    print "Files in %r: %r" % (place, files)
            print "Done."
            """)
        self.assertResultOk(res)
        self.assertEqual(res.stdout, "Done.\n")

########NEW FILE########
__FILENAME__ = test_json_safe
"""
Test JSON serialization straw
"""

import unittest
from codejail.safe_exec import json_safe


class JsonSafeTest(unittest.TestCase):
    """
    Test JSON serialization straw
    """

    # Unicode surrogate values
    SURROGATE_RANGE = range(0xD800, 0xE000)

    def test_unicode(self):
        # Test that json_safe() handles non-surrogate unicode values.

        # Try a few non-ascii UTF-16 characters
        for unicode_char in [unichr(512), unichr(2**8-1), unichr(2**16-1)]:

            # Try it as a dictionary value
            result = json_safe({'test': unicode_char})
            self.assertEqual(result.get('test', None), unicode_char)

            # Try it as a dictionary key
            result = json_safe({unicode_char: 'test'})
            self.assertEqual(result.get(unicode_char, None), 'test')

    def test_surrogate_unicode_values(self):
        # Test that json_safe() excludes surrogate unicode values.

        # Try surrogate unicode values
        for code in self.SURROGATE_RANGE:
            unicode_char = unichr(code)

            # Try it as a dictionary value
            json_safe({'test': unicode_char})
            # Different json libraries treat these bad Unicode characters
            # differently. All we care about is that no error is raised from
            # json_safe.

    def test_surrogate_unicode_keys(self):
        # Test that json_safe() excludes surrogate unicode keys.

        # Try surrogate unicode values
        for code in self.SURROGATE_RANGE:
            unicode_char = unichr(code)

            # Try it is a dictionary key
            json_safe({unicode_char: 'test'})
            # Different json libraries treat these bad Unicode characters
            # differently. All we care about is that no error is raised from
            # json_safe.

########NEW FILE########
__FILENAME__ = test_safe_exec
"""Test safe_exec.py"""

import os.path
import textwrap
import unittest
from nose.plugins.skip import SkipTest

from codejail import safe_exec


class SafeExecTests(unittest.TestCase):
    """The tests for `safe_exec`, to be mixed into specific test classes."""

    # SafeExecTests is a TestCase so pylint understands the methods it can
    # call, but it's abstract, so stop nose from running the tests.
    __test__ = False

    def safe_exec(self, *args, **kwargs):
        """The function under test.

        This class will be mixed into subclasses that implement `safe_exec` to
        give the tests something to test.

        """
        raise NotImplementedError       # pragma: no cover

    def test_set_values(self):
        globs = {}
        self.safe_exec("a = 17", globs)
        self.assertEqual(globs['a'], 17)

    def test_files_are_copied(self):
        globs = {}
        self.safe_exec(
            "a = 'Look: ' + open('hello.txt').read()", globs,
            files=[os.path.dirname(__file__) + "/hello.txt"]
        )
        self.assertEqual(globs['a'], 'Look: Hello there.\n')

    def test_python_path(self):
        globs = {}
        self.safe_exec(
            "import module; a = module.const", globs,
            python_path=[os.path.dirname(__file__) + "/pylib"]
        )
        self.assertEqual(globs['a'], 42)

    def test_functions_calling_each_other(self):
        globs = {}
        self.safe_exec(textwrap.dedent("""\
            def f():
                return 1723
            def g():
                return f()
            x = g()
            """), globs)
        self.assertEqual(globs['x'], 1723)

    def test_printing_stuff_when_you_shouldnt(self):
        globs = {}
        self.safe_exec("a = 17; print 'hi!'", globs)
        self.assertEqual(globs['a'], 17)

    def test_importing_lots_of_crap(self):
        globs = {}
        self.safe_exec(textwrap.dedent("""\
            from numpy import *
            a = 1723
            """), globs)
        self.assertEqual(globs['a'], 1723)

    def test_raising_exceptions(self):
        globs = {}
        with self.assertRaises(safe_exec.SafeExecException) as what_happened:
            self.safe_exec(textwrap.dedent("""\
                raise ValueError("That's not how you pour soup!")
                """), globs)
        msg = str(what_happened.exception)
        self.assertIn("ValueError: That's not how you pour soup!", msg)


class TestSafeExec(SafeExecTests, unittest.TestCase):
    """Run SafeExecTests, with the real safe_exec."""

    __test__ = True

    def safe_exec(self, *args, **kwargs):
        safe_exec.safe_exec(*args, **kwargs)


class TestNotSafeExec(SafeExecTests, unittest.TestCase):
    """Run SafeExecTests, with not_safe_exec."""

    __test__ = True

    def setUp(self):
        # If safe_exec is actually an alias to not_safe_exec, then there's no
        # point running these tests.
        if safe_exec.UNSAFE:                    # pragma: no cover
            raise SkipTest

    def safe_exec(self, *args, **kwargs):
        safe_exec.not_safe_exec(*args, **kwargs)

########NEW FILE########
__FILENAME__ = util
"""Helpers for codejail."""

import contextlib
import os
import shutil
import tempfile


@contextlib.contextmanager
def temp_directory():
    """
    A context manager to make and use a temp directory.
    The directory will be removed when done.
    """
    temp_dir = tempfile.mkdtemp(prefix="codejail-")
    try:
        yield temp_dir
    finally:
        # if this errors, something is genuinely wrong, so don't ignore errors.
        shutil.rmtree(temp_dir)


@contextlib.contextmanager
def change_directory(new_dir):
    """
    A context manager to change the directory, and then change it back.
    """
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield new_dir
    finally:
        os.chdir(old_dir)

########NEW FILE########
