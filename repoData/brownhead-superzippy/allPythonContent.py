__FILENAME__ = main
#!/usr/env/bin python

from clint.textui import puts, colored
import sys

def foo():
    puts(colored.red("I am a mighty foo function!"))
    sys.exit(0)

def bar():
    puts(colored.blue("Nice to meet you, I am bar."))
    sys.exit(1)

if __name__ == "__main__":
    puts("Running as a script!")
    sys.exit(2)

########NEW FILE########
__FILENAME__ = bootstrapper
#!/usr/bin/env python

# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import zipsite
import superconfig
import module_locator
import os.path

zipsite.addsitedir(
	os.path.abspath(os.path.join(
		module_locator.module_path(), "site-packages"
	)),
	prepend_mode = True
)

if len(sys.argv) == 2 and sys.argv[1] == "--superzippy-debug-console":
	# Pulled from http://stackoverflow.com/a/5597918/1989056
	import readline
	import code
	vars = globals().copy()
	vars.update(locals())
	shell = code.InteractiveConsole(vars)
	shell.interact()

# Entry point is expected to be in the form module:function
load_module, run_func = superconfig.entry_point.split(":")

module = __import__(load_module, fromlist = [run_func])

getattr(module, run_func)()

########NEW FILE########
__FILENAME__ = module_locator
# This file contains code primarily found from stack overflow, see there for
# licensing terms.

"""
Module for finding out where the current script is being executed from.

.. author: Daniel Stutzbach, http://stackoverflow.com/a/2632297/1989056

"""

import os, os.path
import sys


try:
    unicode
except NameError:
    unicode = str


def we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")

def module_path():
    encoding = sys.getfilesystemencoding()
    if we_are_frozen():
        try:
            filename = unicode(sys.executable, encoding)
        except TypeError:
            filename = sys.executable
    else:
        try:
            filename = unicode(__file__, encoding)
        except TypeError:
            filename = __file__
    return os.path.dirname(filename)

########NEW FILE########
__FILENAME__ = zipsite
# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import with_statement
from __future__ import print_function
import site as _site
from site import *


from contextlib import closing
import zipfile
import os
import traceback

def get_path_parts(path):
    """
    Splits a path up into its parts.

    :param path: A path (may be any valid file path, ie: relative, windows,
            linux, absolute, etc.).
    :returns: A list containing the parts, in order, of the path. See examples
            below.

    >>> zipsite.get_path_parts("delicious/apple/sauce")
    ['delicious', 'apple', 'sauce']
    >>> zipsite.get_path_parts("/")
    ['/']
    >>> zipsite.get_path_parts("/foo/bar/")
    ['/', 'foo', 'bar', '']
    >>> zipsite.get_path_parts("/foo/bar")
    ['/', 'foo', 'bar']

    .. note::

        This function was adapted from John Machin's Stack Overflow post
        `here <http://stackoverflow.com/a/4580931/1989056>`_.

    """

    parts = []

    # Cut the end off the path repeatedly and add it to parts.
    while True:
        remaining, tail = os.path.split(path)

        # If there's nothing else to cut off
        if remaining == path:
            if path:
                parts.append(path)

            break
        else:
            path = remaining

        parts.append(tail)

    parts.reverse()

    return parts

def split_zip_path(path):
    """
    Takes a path that includes at most a single zip file as a directory and
    splits the path between what's outside of the zip file and what's inside.

    :param path: The path.
    :returns: ``(first_path, second_part)``

    >>> zipsite.split_zip_path("/tmp/testing/stuff.zip/hi/bar")
    ('/tmp/testing/stuff.zip', 'hi/bar')
    >>> zipsite.split_zip_path("/tmp/testing/stuff.zip")
    ('/tmp/testing/stuff.zip', '')
    >>> zipsite.split_zip_path("/tmp/testing/stuff.zip/")
    ('/tmp/testing/stuff.zip', '')

    """

    drive, path = os.path.splitdrive(path)
    path_parts = get_path_parts(path)

    for i in range(len(path_parts)):
        front = os.path.join(drive, *path_parts[:i + 1])

        if path_parts[i + 1:]:
            tail = os.path.join(*path_parts[i + 1:])
        else:
            tail = ""

        if zipfile.is_zipfile(front):
            return front, tail

    return None, path

def exists(path):
    # Figure out what (if any) part of the path is a zip archive.
    archive_path, file_path = split_zip_path(path)

    # If the user is not trying to check a zip file, just use os.path...
    if not archive_path:
        return os.path.exists(path)

    # otherwise check the zip file.
    with closing(zipfile.ZipFile(archive_path, mode = "r")) as archive:
        try:
            archive.getinfo(file_path)
        except KeyError:
            try:
                archive.getinfo(file_path + "/")
            except KeyError:
                return False

        return True

def addsitedir(sitedir, known_paths = None, prepend_mode = False):
    # We need to return exactly what they gave as known_paths, so don't touch
    # it.
    effective_known_paths = \
        known_paths if known_paths is not None else _site._init_pathinfo()

    # Figure out what (if any) part of the path is a zip archive.
    archive_path, site_path = split_zip_path(sitedir)
    if not site_path.endswith("/"):
        site_path = site_path + "/"

    # If the user is not trying to add a directory in a zip file, just use
    # the standard function.
    if not archive_path:
        return old_addsitedir(sitedir, effective_known_paths)

    # Add the site directory itself
    if prepend_mode:
        sys.path.insert(0, sitedir)
    else:
        sys.path.append(sitedir)

    with closing(zipfile.ZipFile(archive_path, mode = "r")) as archive:
        # Go trhough everything in the archive...
        for i in archive.infolist():
            # and grab all the .pth files.
            if os.path.dirname(i.filename) == os.path.dirname(site_path) and \
                    i.filename.endswith(os.extsep + "pth"):
                addpackage(
                    os.path.join(archive_path, site_path),
                    os.path.basename(i.filename),
                    effective_known_paths,
                    prepend_mode = prepend_mode
                )

    return known_paths

old_addsitedir = _site.addsitedir
_site.addsitedir = addsitedir

def addpackage(sitedir, name, known_paths, prepend_mode = False):
    effective_known_paths = \
        known_paths if known_paths is not None else _site._init_pathinfo()

    fullname = os.path.join(sitedir, name)

    # Figure out if we're dealing with a zip file.
    archive_path, pth_file = split_zip_path(fullname)
    archive = None
    if not archive_path:
        f = open(pth_file, mode)
    else:
        archive = zipfile.ZipFile(archive_path)
        f = archive.open(pth_file, "r")

    # Parse through the .pth file
    for n, line in enumerate(f):
        # Ignore comments
        if line.startswith(b"#"):
            continue

        try:
            # Execute any lines starting with import
            if line.startswith((b"import ", b"import\t")):
                exec(line)
            else:
                line = line.rstrip()
                dir, dircase = makepath(sitedir, line.decode('utf-8'))
                if not dircase in known_paths and exists(dir):
                    #Handy debug statement: print "added", dir
                    if prepend_mode:
                        sys.path.insert(0, dir)
                    else:
                        sys.path.append(dir)
                    effective_known_paths.add(dircase)
        except Exception:
            print("Error processing line {:d} of {}:\n".format(n + 1, fullname), file=sys.stderr)

            # Pretty print the exception info
            for record in traceback.format_exception(*sys.exc_info()):
                for line in record.splitlines():
                    print("  " + line, file=sys.stderr)

            print("\nRemainder of file ignored", file=sys.stderr)

            break

    f.close()
    if archive is not None:
        archive.close()

    return known_paths

########NEW FILE########
__FILENAME__ = packaging
#!/usr/bin/env python

# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# future
from __future__ import with_statement

# stdlib
from optparse import OptionParser, make_option
import subprocess
import logging
import sys
import tempfile
import os
import pkg_resources
import shutil
import shlex
import errno
import re

# internal
from . import  zipdir

DEVNULL = open(os.devnull, "w")

_dirty_files = []
def destroy_dirty_files():
    global _dirty_files

    log = logging.getLogger("superzippy")

    for i in _dirty_files:
        log.debug("Deleting %s.", i)
        shutil.rmtree(i)

    _dirty_files = []

def parse_arguments(args = sys.argv[1:]):
    option_list = [
        make_option(
            "-v", "--verbose", action = "count", default=0,
            help =
                "May be specified thrice. If specified once, INFO messages "
                "and above are output. If specified twice, DEBUG messages and "
                "above are output. If specified thrice, DEBUG messages and "
                "above are output, along with the output from any invoked "
                "programs. By default, only WARN messages and above are "
                "output."
        ),
        make_option(
            "-q", "--quiet", action = "store_true",
            help = "Only CRITICAL log messages will be output."
        ),
        make_option(
            "-o", "--output", action = "store", default = None,
            help =
                "The name of the output file. Defaults to the name of the "
                "last package specified on the command line."
        ),
        make_option(
            "-r", "--requirements", action = "append", default = [],
            help =
                "A path to a requirements.txt file to parse and install from. "
                "This option may be specified multiple times."
        ),
        make_option(
            "-c", "--raw-copy", action = "append", default = [],
            dest = "raw_copy",
            help =
                "A path to a file or directory to copy into the created "
                "executable directly. Useful when you don't have a setup.py "
                "for your project."
        ),
        make_option(
            "--raw-copy-rename", action = "append", default = [],
            dest = "raw_copy_rename",
            help =
                "Takes 2 arguments, first a path to a file or directory to "
                "copy into the zuper zip directly, and second the name that "
                "file should have (this name will be importable from within "
                "the executable."
        )
    ]

    parser = OptionParser(
        usage = "usage: %prog [options] [PACKAGE1 PACKAGE2 ...] [ENTRY POINT]",
        description =
            "Zips up a package and adds superzippy's super bootstrap logic to "
            "it. ENTRY POINT should be in the format module:function. Just "
            "like the entry_point option for distutils. Each PACKAGE string "
            "will be passed directly to pip so you may use options and expect "
            "normal results (ex: 'PyYAML --without-libyaml').",
        option_list = option_list
    )

    options, args = parser.parse_args(args)

    if len(args) < 1:
        parser.error("1 or more arguments must be supplied.")

    return (options, args)

def setup_logging(options, args):
    if options.verbose >= 2:
        log_level = logging.DEBUG
    elif options.verbose == 1:
        log_level = logging.INFO
    elif options.quiet:
        log_level = logging.CRITICAL
    else:
        log_level = logging.WARN

    format = "[%(levelname)s] %(message)s"

    logging.basicConfig(level = log_level, format = format)

    logging.getLogger("superzippy").debug("Logging initialized.")

def main(options, args):
    log = logging.getLogger("superzippy")

    packages = args[0:-1]
    entry_point = args[-1]

    # Append any requirements.txt files to the packages list.
    packages += ["-r %s" % i for i in options.requirements]

    # Create the virtualenv directory
    virtualenv_dir = tempfile.mkdtemp()
    _dirty_files.append(virtualenv_dir)

    #### Create virtual environment

    log.debug("Creating virtual environment at %s.", virtualenv_dir)
    output_target = None if options.verbose >= 3 else DEVNULL

    return_value = subprocess.call(
        ["virtualenv", virtualenv_dir],
        stdout = output_target,
        stderr = subprocess.STDOUT
    )

    if return_value != 0:
        log.critical(
            "virtualenv returned non-zero exit status (%d).", return_value
        )
        return 1

    ##### Install package and dependencies

    pip_path = os.path.join(virtualenv_dir, "bin", "pip")

    for i in packages:
        log.debug("Installing package with `pip install %s`.", i)

        command = [pip_path, "install"] + shlex.split(i)
        return_value = subprocess.call(
            command,
            stdout = output_target,
            stderr = subprocess.STDOUT
        )

        if return_value != 0:
            log.critical("pip returned non-zero exit status (%d).", return_value)
            return 1

    if not packages:
        log.warn("No packages specified.")

    #### Uninstall extraneous packages (pip and setuptools)
    return_value = subprocess.call(
        [pip_path, "uninstall", "--yes", "pip", "setuptools"],
        stdout = output_target,
        stderr = subprocess.STDOUT
    )

    if return_value != 0:
        log.critical("pip returned non-zero exit status (%d).",
            return_value)
        return 1

    #### Move site packages over to build directory

    # TODO: We should look at pip's source code and figure out how it decides
    # where site-packages is and use the same algorithm.

    build_dir = tempfile.mkdtemp()
    _dirty_files.append(build_dir)

    site_package_dir = None
    for root, dirs, files in os.walk(virtualenv_dir):
        if "site-packages" in dirs:
            found = os.path.join(root, "site-packages")

            # We'll only use the first one, but we want to detect them all.
            if site_package_dir is not None:
                log.warn(
                    "Multiple site-packages directories found. `%s` will be "
                    "used. `%s` was found afterwards.",
                    site_package_dir,
                    found
                )
            else:
                site_package_dir = found

    # A couple .pth files are consistently left over from the previous step,
    # delete them.
    extraneous_pth_files = ["easy-install.pth", "setuptools.pth"]
    for i in extraneous_pth_files:
        path = os.path.join(site_package_dir, i)
        if os.path.exists(path):
            os.remove(path)

    shutil.move(site_package_dir, build_dir)

    #### Perform any necessary raw copies.
    raw_copies = options.raw_copy_rename

    for i in options.raw_copy:
        if i[-1] == "/":
            i = i[0:-1]

        raw_copies.append((i, os.path.basename(i)))

    for file_path, dest_name in raw_copies:
        log.debug(
            "Performing raw copy of `%s`, destination name: `%s`.",
            file_path,
            dest_name
        )

        dest = os.path.join(build_dir, "site-packages", dest_name)

        try:
            shutil.copytree(file_path, dest)
        except OSError as e:
            if e.errno == errno.ENOTDIR:
                shutil.copy(file_path, dest)
            else:
                raise

    ##### Install bootstrapper

    log.debug("Adding bootstrapper to the archive.")

    bootstrap_files = {
        "__init__.py": "__init__.py",
        "bootstrapper.py": "__main__.py",
        "zipsite.py": "zipsite.py",
        "module_locator.py": "module_locator.py"
    }

    for k, v in bootstrap_files.items():
        source = pkg_resources.resource_stream("superzippy.bootstrapper", k)
        dest = open(os.path.join(build_dir, v), "wb")

        shutil.copyfileobj(source, dest)

        source.close()
        dest.close()

    ##### Install configuration

    log.debug("Adding configuration file to archive.")

    with open(os.path.join(build_dir, "superconfig.py"), "w") as f:
        f.write("entry_point = '%s'" % entry_point)

    ##### Zip everything up into final file

    log.debug("Zipping up %s.", build_dir)

    if options.output:
        output_file = options.output
    elif packages:
        last_package = shlex.split(packages[-1])[0]

        if os.path.isdir(last_package):
            # Figure out the name of the package the user pointed at on their
            # system.
            setup_program = subprocess.Popen(["/usr/bin/env", "python",
                os.path.join(last_package, "setup.py"), "--name"],
                stdout = subprocess.PIPE, stderr = DEVNULL)
            if setup_program.wait() != 0:
                log.critical("Could not determine name of package at %s.",
                    last_package)
                return 1

            # Grab the output of the setup program
            package_name_raw = setup_program.stdout.read()

            # Decode the output into text. Whatever our encoding is is
            # probably the same as what the setup.py program spat out.
            package_name_txt = package_name_raw.decode(
                sys.stdout.encoding or "UTF-8")

            # Strip any leading and trailing whitespace
            package_name = package_name_txt.strip()

            # Verify that what we got was a valid package name (this handles
            # most cases where an error occurs in the setup.py program).
            if re.match("[A-Za-z0-9_-]+", package_name) is None:
                log.critical("Could nto determine name of package. setup.py "
                    "is reporting an illegal name of %s", package_name)
                return 1

            output_file = package_name + ".sz"
        else:
            # Just use the name of a package we're going to pull down from
            # the cheese shop, but cut off any versioning information (ex:
            # bla==2.3 will become bla).
            for k, c in enumerate(last_package):
                if c in ("=", ">", "<"):
                    output_file = last_package[0:k] + ".sz"
                    break
            else:
                output_file = last_package + ".sz"

    else:
        log.critical("No output file or packages specified.")
        return 1

    try:
        zipdir.zip_directory(build_dir, output_file)
    except IOError:
        log.critical(
            "Could not write to output file at '%s'.",
            output_file,
            exc_info = sys.exc_info()
        )
        return 1

    #### Make that file executable

    with open(output_file, "rb") as f:
        data = f.read()

    with open(output_file, "wb") as f:
        f.write(b"#!/usr/bin/env python\n" + data)

    os.chmod(output_file, 0o755)

    return 0

def run():
    options, args = parse_arguments()
    setup_logging(options, args)
    try:
        main(options, args)
    finally:
        destroy_dirty_files()

if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = main
#!/usr/env/bin python

from yaml import load, dump
try:
    # We want this to error because a Super Zip can't have shared libs in it.
    from yaml import CLoader as Loader, CDumper as Dumper
    assert False, "Should not be able to access shared libraries."
except ImportError:
    from yaml import Loader, Dumper

try:
    unicode
except NameError:
    unicode = str

import sys

def parse_list():
    data = load(sys.argv[1])
    for i in data:
        sys.stdout.write(str(i) + "\n")

def parse_tuple_list():
    data = load(sys.argv[1])
    for k, v in data:
        sys.stdout.write(str(k) + " " + str(v) + "\n")

if __name__ == "__main__":
    if sys.argv[2] == "list":
        parse_list()
    else:
        parse_dict()
    sys.exit(1)

########NEW FILE########
__FILENAME__ = main
#!/usr/env/bin python

from clint.textui import puts, colored
import sys

def foo():
    puts(colored.red("I am a mighty foo function!"))
    sys.exit(0)

def bar():
    puts(colored.blue("Nice to meet you, I am bar."))
    sys.exit(1)

if __name__ == "__main__":
    puts("Running as a script!")
    sys.exit(2)

########NEW FILE########
__FILENAME__ = main
#!/usr/env/bin python

from clint.textui import puts, colored
import sys

def foo():
    puts(colored.red("I am a mighty foo function!"))
    sys.exit(0)

def bar():
    puts(colored.blue("Nice to meet you, I am bar."))
    sys.exit(1)

if __name__ == "__main__":
    puts("Running as a script!")
    sys.exit(2)

########NEW FILE########
__FILENAME__ = main
#!/usr/env/bin python

import sys

def main():
    sys.stdout.write("Hello world!\n")

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = sample_info
# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# stdlib
import pkg_resources
import os
import re
try:
    import ConfigParser as configparser # Python 2.x
except ImportError:
    import configparser # Python 3.x

def get_sample_dir(name = None):
    """
    Returns a path containing the sample ``name``. Will extract the sample
    directory if necessary (if we're in a zip file). If ``None`` is given for
    ``name``, a path to the ``samples/`` directory will be returned.

    """

    samples_dir = pkg_resources.resource_filename(
        "superzippy.tests.acceptance", "samples")
    if not os.path.exists(samples_dir):
        raise RuntimeError("Could not retrieve samples directory.")

    if name is None:
        return samples_dir
    else:
        result = os.path.join(samples_dir, name)
        if not os.path.exists(result):
            raise ValueError("Could not find sample %s." % (name, ))

        return result

def list_samples():
    """
    Returns a list of all of the samples available.

    >>> list_samples()
    ["simple", "readme"]

    """

    samples_dir = get_sample_dir()

    def is_sample(name):
        "Returns True if name is a valid sample."

        return (os.path.isdir(os.path.join(samples_dir, name)) and
            os.path.isfile(os.path.join(samples_dir, name, "testing.ini")))

    open("/tmp/outputbla.txt", "w").write(
        str(os.listdir(samples_dir)) + "\n" + str(filter(is_sample, os.listdir(samples_dir))))

    return filter(is_sample, os.listdir(samples_dir))

class SampleConfig:
    def __init__(self, sample_name, parser):
        self.sample_name = sample_name
        self._parser = parser

    def get_package_name(self):
        return self._parser.get("info", "name")

    def is_python_supported(self, version_string):
        try:
            regex = self._parser.get("info", "supports_python")
        except:
            return True

        return re.match(regex, version_string) is not None

    class EntryPoint:
        def __init__(self, name, expected_output, options):
            self.name = name
            self.expected_output = expected_output
            self.options = options

    def get_entry_points(self):
        sections = [i for i in self._parser.sections() if
            i.startswith("entry_point")]

        result = []
        for i in sections:
            try:
                expected_output = eval(self._parser.get(i, "expected_output"))
            except configparser.NoOptionError:
                expected_output = []

            try:
                options = eval(self._parser.get(i, "options"))
            except configparser.NoOptionError:
                options = []

            result.append(SampleConfig.EntryPoint(
                name = self._parser.get(i, "name"),
                expected_output = expected_output,
                options = options
            ))

        return result

def get_sample_config(name):
    """
    Returns a dict containing the configuration of the given sample project.
    The configuration will be pulled from the sample's ``testing.ini`` file.

    """

    parser = configparser.SafeConfigParser()
    parser.read(os.path.join(get_sample_dir(name), "testing.ini"))

    return SampleConfig(name, parser)

########NEW FILE########
__FILENAME__ = test_basic
# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module tests basic functionality of Super Zippy (ie: can it make a Super
Zip from a simple pure-Python project with no dependencies?).

"""

# stdlib
import subprocess
import tempfile
import shutil
import os
import sys

# external
import pytest

# internal
from . import sample_info

# Support Pythons without unicode support
try:
    unicode
except NameError:
    unicode = str

@pytest.mark.parametrize("sample", sample_info.list_samples())
def test_sample(sample):
    """
    Initiates testing on all of the samples.

    """

    sample_dir = sample_info.get_sample_dir(sample)
    config = sample_info.get_sample_config(sample)

    python_version = ".".join(str(i) for i in sys.version_info)
    if not config.is_python_supported(python_version):
        pytest.skip("Test not supported in this Python.")

    for i in config.get_entry_points():
        temp_dir = tempfile.mkdtemp()
        try:
            superzip_path = \
                os.path.join(temp_dir, config.get_package_name()) + ".sz"

            zip_process = subprocess.Popen(
                ["superzippy", "-o", superzip_path, "-vvv"] + i.options +
                [sample_dir, i.name],
                cwd = sample_dir
            )
            zip_process.wait()

            assert os.path.exists(superzip_path), \
                "%s doesn't exist" % (superzip_path, )

            assert os.access(superzip_path, os.X_OK), \
                "%s is not executable" % (superzip_path, )

            # Check that we get the right output
            for args, output, returncode in i.expected_output:
                test_process = subprocess.Popen(
                    [superzip_path] + args,
                    stdout = subprocess.PIPE,
                    cwd = temp_dir
                )
                test_process.wait()

                decoded_output = test_process.stdout.read()
                decoded_output = \
                    decoded_output.decode(sys.stdout.encoding or "UTF-8")

                assert decoded_output == output
                assert test_process.returncode == returncode
        finally:
            shutil.rmtree(temp_dir)

########NEW FILE########
__FILENAME__ = file_utilities
# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# futures
from __future__ import with_statement

# stdlib
import shutil
import tempfile
import os.path
import random
import string

try:
    unicode
except NameError:
    unicode = str

try:
    xrange
except NameError:
    xrange = range

def create_test_directory(tree):
    """
    Creates a temporary directory with the given file tree in it.

    :param tree: A list of strings and tuples where each string is a path to
        a directory that should exist within the temporary directory (relative
        to the root of the directory) and each tuple is a file that should
        exist within the temporary directory represented as ``(path, size)``,
        the file will be created and filled with ``size`` bytes of data.
    :returns: A path to the temporary directory.

    .. note::

        The files and directories are created in the order they appear in the
        list. If a file is specfied in a directory that has not previously been
        created an exception will be thrown.

    >>> create_test_directory(["a", ("a/bla", 12)])
    "/tmp/asdf"
    >>> print list(os.walk("/tmp/asdf"))

    """

    # Note: This will create a directory with permissions 0o700
    temp_dir = tempfile.mkdtemp()

    resolve_path = lambda x: os.path.join(temp_dir, x)

    for i in tree:
        if isinstance(i, str) or isinstance(i, unicode):
            os.mkdir(resolve_path(i), 0o700)
        elif isinstance(i, tuple) and len(i) == 2:
            path, size = i
            with open(resolve_path(path), "w") as f:
                symbols = string.ascii_letters + string.digits
                for i in xrange(size):
                    f.write(random.choice(symbols))
        else:
            raise TypeError("All items in list must be string or two-tuple.")

    return temp_dir

def get_files(path):
    """
    Returns a list of all the files under the given directory. Directories are
    not marked by a trailing slash (so the directory `bar/` would be listed as
    `bar`).

    For example, given a directory tree as below.

    .. code-block::

        + path/
        |    + foo.txt
        |    + bar/
        |        + baz.txt
        |        + qux.txt

    >>> get_files("path")
    ["foo.txt", "bar", "bar/baz.txt", "bar/qux.txt"]

    """

    if not os.path.isdir(path):
        raise TypeError("%s is not a directory." % (path, ))

    test_files = []
    for dir_path, dir_names, file_names in os.walk(path):
        # Iterate through every file and directory in dir_path
        for i in file_names + dir_names:
            # Figure out the full path of i
            cur_path = os.path.join(dir_path, i)

            # Cut off the first part of it (that includes path). So if path
            # is foo, then `foo/bla.txt` becomes `bla.txt`.
            cur_path = os.path.relpath(cur_path, path)

            test_files.append(cur_path)
    return test_files

########NEW FILE########
__FILENAME__ = test_file_utilities
# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module tests the file_utilities module which is itself used only in other
tests.

"""

# futures
from __future__ import with_statement

# test helpers
import superzippy.tests.file_utilities as file_utilities

# external
import pytest

# stdlib
import sys
import os
import os.path
import shutil
import tempfile

class TestGetFiles:
    def test_basic(self):
        """
        Create a directory tree and make sure we get the right result.

        """

        temp_dir = tempfile.mkdtemp()
        resolve = lambda *x: os.path.join(temp_dir, *x)
        try:
            os.mkdir(resolve("a"))
            os.mkdir(resolve("b"))
            open(resolve("a", "foo"), "w").close()
            open(resolve("a", "bar"), "w").close()
            desired_tree = set(["a", "b", "a/foo", "a/bar"])

            assert set(file_utilities.get_files(temp_dir)) == desired_tree
        finally:
            shutil.rmtree(temp_dir)

class TestCreateTestDirectory:
    good_cases = [
        ["a", "b", "c", ("a/foo", 1000), ("a/bar", 1000)],
        ["a", ("a/foo", 0)],
        [("bar", 1000)],
        ["bar"]
    ]

    @pytest.mark.parametrize("test_case", good_cases)
    def test_existence(self, test_case):
        """
        Ensure that all the files that were supposed to get created are there,
        and ensure that none were created that weren't supposed to be.

        """

        test_dir = file_utilities.create_test_directory(test_case)
        try:
            real_contents = file_utilities.get_files(test_dir)
            expected_contents = \
                [(i[0] if isinstance(i, tuple) else i) for i in test_case]

            sys.stdout.write("real_contents = %s\n" % (real_contents, ))
            sys.stdout.write(
                "expected_contents = %s\n" % (expected_contents, ))

            assert set(real_contents) == set(expected_contents)
        finally:
            shutil.rmtree(test_dir)

    @pytest.mark.parametrize("test_case", good_cases)
    def test_files_sizes(self, test_case):
        """
        Ensures that the files created are the correct size.

        """

        test_dir = file_utilities.create_test_directory(test_case)
        try:
            for i in test_case:
                if isinstance(i, tuple):
                    sys.stdout.write("checking size of %s\n" % (i[0], ))
                    file_size = os.stat(
                        os.path.join(test_dir, i[0])).st_size
                    assert file_size == i[1]
        finally:
            shutil.rmtree(test_dir)


########NEW FILE########
__FILENAME__ = test_zipdir
# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# futures
from __future__ import with_statement

# test helpers
from . import file_utilities

# external
import pytest

# internal
from .. import zipdir

# stdlib
from contextlib import closing
import zipfile
import tempfile
import shutil
import os
import sys

class TestZipDir:
    good_cases = [
        ["a", "b", ("a/foo", 1000), ("a/bar", 1000), ("b/baz", 1000)],
        ["a", ("a/foo", 0)],
        [("bar", 1000)]
    ]

    @pytest.fixture
    def zip_tree(self, request, test_case):
        try:
            # We must create these variables up front for our finally
            # statement to work correctly.
            test_dir = zip_file = unzip_dir = None

            # Create some files and directories to zip up
            test_dir = file_utilities.create_test_directory(test_case)

            # Get a temporary file that will become our zip file
            zip_file_handle = tempfile.NamedTemporaryFile(delete = False)
            zip_file_handle.close()
            zip_file = zip_file_handle.name

            # Zip up our directory tree
            zipdir.zip_directory(test_dir, zip_file)

            # Unzip our directory tree
            unzip_dir = tempfile.mkdtemp()
            with closing(zipfile.ZipFile(zip_file, "r")) as f:
                f.extractall(unzip_dir)
        except:
            if test_dir is not None:
                shutil.rmtree(test_dir)

            if zip_file is not None:
                os.remove(zip_file)

            if unzip_dir is not None:
                shutil.rmtree(unzip_dir)

            raise

        def cleanup():
            shutil.rmtree(test_dir)
            os.remove(zip_file)
            shutil.rmtree(unzip_dir)
        request.addfinalizer(cleanup)

        return test_dir, zip_file, unzip_dir

    @pytest.mark.parametrize("test_case", good_cases)
    def test_existence(self, zip_tree, test_case):
        """
        Ensure that all the files that were supposed to get zipped up make it
        it into the archive, and ensure that none got in that were not
        supposed to.

        """

        test_dir, zip_file, unzip_dir = zip_tree

        real_contents = file_utilities.get_files(unzip_dir)
        expected_contents = file_utilities.get_files(test_dir)

        sys.stdout.write("real_contents = %s\n" % (str(real_contents), ))
        sys.stdout.write(
            "expected_contents = %s\n" % (str(expected_contents), ))

        assert set(real_contents) == set(expected_contents)


    @pytest.mark.parametrize("test_case", good_cases)
    def test_files_sizes(self, zip_tree, test_case):
        """
        Ensures that the files created are the correct size.

        """

        test_dir, zip_file, unzip_dir = zip_tree

        for i in test_case:
            if isinstance(i, tuple):
                sys.stdout.write("checking size of %s\n" % (i[0], ))
                file_size = os.stat(
                    os.path.join(test_dir, i[0])).st_size
                assert file_size == i[1]

########NEW FILE########
__FILENAME__ = zipdir
# Copyright (c) 2013 John Sullivan
# Copyright (c) 2013 Other contributers as noted in the CONTRIBUTERS file
#
# This file is part of superzippy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Module that provides a useful function that can be used to zip up an entire
directory.

"""

# future
from __future__ import with_statement

# stdlib
from contextlib import closing
import zipfile
import os

def zip_directory(path, output_file, compression = zipfile.ZIP_DEFLATED):
    """
    Compresses the directory at ``path`` into a zip file at ``output_file``.

    .. note::

        Empty directories are not added to the zip file.

    .. note::

        Creating empty zip files is not supported on version < 2.7.1.

    """

    with closing(zipfile.ZipFile(output_file, "w", compression)) as f:
        for dir_path, dir_names, file_names in os.walk(path):
            for i in file_names:
                file_path = os.path.join(dir_path, i)
                f.write(file_path, os.path.relpath(file_path, path))

########NEW FILE########
